"""Label families over a model's formulas: inference, and the lean rewrite.

Vocabulary
----------
family      An IntEnum class of the full conversion (``PolsTiming``) whose members stand for
            the string labels of upstream text (``"BEF_DECR"``).
typed       A parameter, local name, Reference or cell result whose value is a member of a
            family.  Parameters are typed by position: ``P[(space, cell)][i] = family``.
label site  A string constant that stands where a typed value is expected: an argument at a
            typed position, an operand compared with a typed value (``==``, ``!=``, ``in``,
            ``not in``), a source of a typed local (``k = "X"``, ``for k in ("A", "B")``), or
            a value returned by a typed cell.  Each label site becomes ``Family.MEMBER``.
value use   Any other use of a typed value (a table key, a column label, an f-string): it is
            spelled ``x.name``, which is the upstream string, so upstream table loaders and
            string-keyed tables keep working unchanged.

The same inference runs over the full conversion's text (``mode="ref"``, where members are
already spelled ``F.M`` and the map is *derived*) and over upstream text (``mode="lean"``,
where the map from the reference seeds the types and the rewrite is computed).
"""

import ast
import keyword

OPAQUE = object()


def bound_names(target):
    """Names a target binds: a Name, or Names inside Tuple/List/Starred (not subscripts)."""
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        return [n for e in target.elts for n in bound_names(e)]
    if isinstance(target, ast.Starred):
        return bound_names(target.value)
    return []


class IterOf:
    """The elements of a call's result, as the source of a loop variable."""

    def __init__(self, call):
        self.call = call


def is_label(node):
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def is_label_expr(node):
    """A label, or a conditional expression whose branches are all labels."""
    if isinstance(node, ast.IfExp):
        return is_label_expr(node.body) and is_label_expr(node.orelse)
    return is_label(node)


class GenerationError(Exception):
    pass


class Fn:
    """One cell's formula: parameters, local bindings and a parent map."""

    def __init__(self, model, space, name, node):
        self.model = model
        self.space = space
        self.name = name
        self.key = (space, name)
        self.node = node
        args = node.args.posonlyargs + node.args.args
        self.params = [a.arg for a in args]
        self.parent = {}
        for p in ast.walk(node):
            for c in ast.iter_child_nodes(p):
                self.parent[c] = p
        # Local bindings, keyed by scope: a function-level name is its own key, a
        # comprehension target is ``name@<id of the comprehension>`` (Python scopes it so).
        self.bindings = {}            # key -> list of source nodes (OPAQUE, IterOf)
        self.comp_targets = {}        # id(comprehension expr) -> set of names
        for p in ast.walk(node):
            if isinstance(p, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
                names = set()
                for g in p.generators:
                    names.update(bound_names(g.target))
                self.comp_targets[id(p)] = names
                for g in p.generators:
                    self._bind_loop(g.target, g.iter, lambda n, p=p: "%s@%d" % (n, id(p)))
        for p in ast.walk(node):
            if isinstance(p, ast.Assign):
                for t in p.targets:
                    if isinstance(t, ast.Name):
                        self.bindings.setdefault(t.id, []).append(p.value)
                    else:
                        for n in bound_names(t):
                            self.bindings.setdefault(n, []).append(OPAQUE)
            elif isinstance(p, (ast.AugAssign, ast.AnnAssign)):
                if isinstance(p.target, ast.Name):
                    self.bindings.setdefault(p.target.id, []).append(OPAQUE)
            elif isinstance(p, ast.For):
                self._bind_loop(p.target, p.iter, lambda n: n)
            elif isinstance(p, (ast.NamedExpr,)):
                self.bindings.setdefault(p.target.id, []).append(p.value)
        for prm in self.params:
            self.bindings.pop(prm, None)
        self.local_fam = {}

    def _bind_loop(self, target, it, key):
        if isinstance(target, ast.Name):
            k = key(target.id)
            if isinstance(it, (ast.Tuple, ast.List, ast.Set)):
                self.bindings.setdefault(k, []).extend(it.elts)
            elif isinstance(it, ast.Call):
                self.bindings.setdefault(k, []).append(IterOf(it))
            else:
                self.bindings.setdefault(k, []).append(OPAQUE)
        else:
            for n in bound_names(target):
                self.bindings.setdefault(key(n), []).append(OPAQUE)

    def key_of(self, name_node):
        """The binding key of a Name read at this node (comprehension scopes first)."""
        name = name_node.id
        cur = name_node
        while cur in self.parent:
            cur = self.parent[cur]
            names = self.comp_targets.get(id(cur))
            if names and name in names:
                return "%s@%d" % (name, id(cur))
        return name

    def returns(self):
        out = []
        for p in ast.walk(self.node):
            if isinstance(p, ast.Return) and p.value is not None:
                out.append(p)
        return out


class Typing:
    """The family map of one model, and the fixpoint that completes it."""

    def __init__(self, model, families, mode, params=None, returns=None,
                 member_refs=None, ref_returns=None, seq_returns=None):
        self.model = model
        self.families = families                       # {F: [members]}
        self.mode = mode
        self.P = {k: dict(v) for k, v in (params or {}).items()}
        self.R = dict(returns or {})                   # cells returning a member
        self.ref_returns = dict(ref_returns or {})     # cells returning a member in the reference
        self.MR = dict(member_refs or {})              # References holding a member
        self.seq_returns = dict(seq_returns or {})     # cells returning a sequence of members
        self.notes = []
        self.fns = {}
        for sname, sp in model.spaces.items():
            for cname, node in sp.cells.items():
                self.fns[(sname, cname)] = Fn(model, sname, cname, node)

    # -- the type of an expression ---------------------------------------------------

    def fam(self, fn, node):
        if isinstance(node, IterOf):
            key = self.model.callee(fn.space, node.call)
            return self.seq_returns.get(key) if key else None
        if isinstance(node, ast.Name):
            k = fn.key_of(node)
            if k in fn.local_fam:
                return fn.local_fam[k]
            if k in fn.bindings:
                return None
            if node.id in fn.params:
                i = fn.params.index(node.id)
                return self.P.get(fn.key, {}).get(i)
            return self.MR.get((fn.space, node.id))
        if isinstance(node, ast.Call):
            key = self.model.callee(fn.space, node)
            if key is None:
                return None
            if key in self.R:
                return self.R[key]
            if self.mode == "ref":
                return self.ref_returns.get(key)
            return None
        if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                and node.value.id in self.families):
            return node.value.id
        if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name)
                and node.value.id in self.families):
            return node.value.id
        if isinstance(node, ast.IfExp):
            a, b = self.fam(fn, node.body), self.fam(fn, node.orelse)
            if a and (b == a or (b is None and (is_label(node.orelse)))):
                return a
            if b and a is None and is_label(node.body):
                return b
        return None

    # -- call arguments by position ------------------------------------------------

    def call_args(self, fn, call):
        """[(position, arg node)] of a call to a cell; keywords mapped to positions."""
        key = self.model.callee(fn.space, call)
        if key is None:
            return None, []
        params = self.model.params(key)
        out = [(i, a) for i, a in enumerate(call.args) if not isinstance(a, ast.Starred)]
        for kw in call.keywords:
            if kw.arg in params:
                out.append((params.index(kw.arg), kw.value))
        return key, out

    def set_param(self, key, pos, F, why):
        cur = self.P.setdefault(key, {}).get(pos)
        if cur is None:
            self.P[key][pos] = F
            return True
        if cur != F:
            self.notes.append("conflict: %s.%s arg %d is %s and %s (%s)"
                              % (key[0], key[1], pos, cur, F, why))
        return False

    def type_local(self, fn, node, F):
        """Type a local by use (``node``: a Name read), when all its sources are labels."""
        k = fn.key_of(node)
        if k not in fn.bindings or k in fn.local_fam:
            return False
        srcs = fn.bindings[k]
        if all(s is not OPAQUE and (is_label_expr(s) or self.fam(fn, s) == F) for s in srcs):
            fn.local_fam[k] = F
            return True
        return False

    def other_sides(self, cmp):
        """Pairs (a, op, b) of a comparison chain."""
        ops = [cmp.left] + cmp.comparators
        return [(ops[i], cmp.ops[i], ops[i + 1]) for i in range(len(cmp.ops))]

    def solve(self, propagate=True):
        changed = True
        rounds = 0
        while changed:
            rounds += 1
            if rounds > 50:
                raise GenerationError("no fixpoint")
            changed = False
            for fn in self.fns.values():
                # locals typed by their sources
                for name, srcs in fn.bindings.items():
                    if name in fn.local_fam or any(s is OPAQUE for s in srcs):
                        continue
                    fams = {self.fam(fn, s) for s in srcs}
                    if None in fams:
                        if not all(self.fam(fn, s) or is_label_expr(s) for s in srcs):
                            continue
                        fams.discard(None)
                    if len(fams) == 1:
                        fn.local_fam[name] = fams.pop()
                        changed = True
                for node in ast.walk(fn.node):
                    if isinstance(node, ast.Call):
                        key, args = self.call_args(fn, node)
                        if key is None:
                            continue
                        for pos, a in args:
                            Fa = self.fam(fn, a)
                            Fp = self.P.get(key, {}).get(pos)
                            if Fa and propagate and Fp is None:
                                changed |= self.set_param(key, pos, Fa, "argument")
                            elif Fa and Fp and Fa != Fp:
                                self.notes.append("conflict: %s passes %s to %s.%s arg %d typed %s"
                                                  % (fn.name, Fa, key[0], key[1], pos, Fp))
                            if Fp and isinstance(a, ast.Name):
                                changed |= self.type_local(fn, a, Fp)
                                # a parameter passed on to a typed position is typed
                                if (a.id in fn.params and Fa is None
                                        and fn.key_of(a) not in fn.bindings):
                                    changed |= self.set_param(
                                        fn.key, fn.params.index(a.id), Fp, "passed on")
                    elif isinstance(node, ast.Compare):
                        for a, op, b in self.other_sides(node):
                            for x, y in ((a, b), (b, a)):
                                Fy = self.fam(fn, y)
                                if Fy is None and isinstance(y, (ast.Tuple, ast.List, ast.Set)):
                                    fs = {self.fam(fn, e) for e in y.elts} - {None}
                                    Fy = fs.pop() if len(fs) == 1 else None
                                if Fy is None:
                                    continue
                                if isinstance(x, ast.Name):
                                    if (self.mode == "ref" and x.id in fn.params
                                            and fn.key_of(x) not in fn.bindings
                                            and self.fam(fn, x) is None):
                                        changed |= self.set_param(
                                            fn.key, fn.params.index(x.id), Fy, "compared")
                                    changed |= self.type_local(fn, x, Fy)
                # locals returned by a typed cell
                F = self.R.get(fn.key)
                if F:
                    for r in fn.returns():
                        for v in self._branches(r.value):
                            if isinstance(v, ast.Name):
                                changed |= self.type_local(fn, v, F)
        return self

    @staticmethod
    def _branches(node):
        if isinstance(node, ast.IfExp):
            return Typing._branches(node.body) + Typing._branches(node.orelse)
        return [node]

    # -- reference mode: the attribute cells whose result is passed on ---------------

    def derive_ref_returns(self):
        """Cells of the reference whose every return is a member of one family."""
        for fn in self.fns.values():
            fams = set()
            ok = True
            rets = fn.returns()
            for r in rets:
                for v in self._branches(r.value):
                    F = self.fam(fn, v)
                    if F is None:
                        ok = False
                    fams.add(F)
            fams.discard(None)
            if rets and ok and len(fams) == 1:
                self.ref_returns[fn.key] = fams.pop()

    def derive_seq_returns(self):
        """Cells of the reference whose every return is a tuple or list of one family."""
        for fn in self.fns.values():
            fams, ok, rets = set(), True, fn.returns()
            for r in rets:
                for v in self._branches(r.value):
                    if isinstance(v, (ast.Tuple, ast.List)) and v.elts:
                        fs = {self.fam(fn, e) for e in v.elts}
                        if None in fs or len(fs) != 1:
                            ok = False
                        fams |= fs
                    else:
                        ok = False
            if rets and ok and len(fams) == 1:
                self.seq_returns[fn.key] = fams.pop()

    def needed_returns(self):
        """Cells (of ``ref_returns``) whose result reaches a typed argument position."""
        need = {}
        stack = []

        def sources(fn, node, seen):
            if isinstance(node, ast.IfExp):
                return sources(fn, node.body, seen) + sources(fn, node.orelse, seen)
            if isinstance(node, ast.Call):
                key = self.model.callee(fn.space, node)
                return [key] if key in self.ref_returns else []
            if isinstance(node, ast.Name) and fn.key_of(node) in fn.bindings \
                    and fn.key_of(node) not in seen:
                k = fn.key_of(node)
                out = []
                for s in fn.bindings[k]:
                    if s is not OPAQUE and not isinstance(s, IterOf):
                        out += sources(fn, s, seen | {k})
                return out
            return []

        for fn in self.fns.values():
            for node in ast.walk(fn.node):
                if isinstance(node, ast.Call):
                    key, args = self.call_args(fn, node)
                    if key is None:
                        continue
                    for pos, a in args:
                        if self.P.get(key, {}).get(pos):
                            stack += sources(fn, a, frozenset())
        while stack:
            key = stack.pop()
            if key in need:
                continue
            need[key] = self.ref_returns[key]
            fn = self.fns[key]
            for r in fn.returns():
                stack += sources(fn, r.value, frozenset())
        return need


def ident(label):
    return label.isidentifier() and not keyword.iskeyword(label)
