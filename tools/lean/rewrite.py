"""The lean rewrite of one model's upstream text, from its family map.

Rules (see GENERATOR.md for the owner's wording):

K1  label sites of a typed position become ``Family.MEMBER``; ``kind=None`` defaults whose
    family has a member that upstream never spells (``ALL``) lose the default, ``kind is
    None`` becomes ``kind == Family.ALL`` and a call that omits the argument passes
    ``Family.ALL``; value uses of a typed value are spelled ``x.name``; a cell whose result
    is passed on as an argument returns ``Family[...]`` of its upstream value.
K2  the listed vector cells build lists where upstream builds tuples.
Everything else is upstream text, byte for byte.
"""

import ast

from engine import OPAQUE, GenerationError, Typing, is_label


def in_raise(fn, node):
    cur = node
    while cur in fn.parent:
        cur = fn.parent[cur]
        if isinstance(cur, ast.Raise):
            return True
    return False


class Rewriter:
    def __init__(self, model, families, refmap, overrides):
        self.model = model
        self.families = {F: [m for m, _ in ms] for F, ms in families.items()}
        self.refmap = refmap
        self.ov = overrides
        self.notes = []
        self.used = {}            # space -> set of families spelled there
        params = {}
        for s, cells in refmap["params"].items():
            for c, d in cells.items():
                if s in model.spaces and c in model.spaces[s].cells:
                    up_names = model.params((s, c))
                    for i, (F, name) in d.items():
                        i = int(i)
                        if i >= len(up_names):
                            self.notes.append("param %s.%s[%d] of the reference is gone" % (s, c, i))
                            continue
                        if up_names[i] != name:
                            self.notes.append("param %s.%s[%d] is %r upstream and %r in the "
                                              "reference; typed by position" % (s, c, i, up_names[i], name))
                        params.setdefault((s, c), {})[i] = F
        for s, cells in overrides.get("params", {}).items():
            for c, d in cells.items():
                for i, F in d.items():
                    if F is None:
                        params.get((s, c), {}).pop(int(i), None)
                    else:
                        params.setdefault((s, c), {})[int(i)] = F
        ref_returns = {(s, c): F for s, d in refmap["ref_returns"].items() for c, F in d.items()
                       if s in model.spaces and c in model.spaces[s].cells}
        mr = {(s, n): F for s, d in refmap["member_refs"].items() for n, F in d.items()}
        seq = {(s, c): F for s, d in refmap.get("seq_returns", {}).items() for c, F in d.items()
               if s in model.spaces and c in model.spaces[s].cells}
        self.typing = Typing(model, self.families, "lean", params=params,
                             member_refs=mr, ref_returns=ref_returns, seq_returns=seq)
        # Cells whose result is passed on: those of the reference, plus any upstream flow
        # from a reference member-returning cell into a typed position.
        self.typing.solve(propagate=True)
        for _ in range(10):
            need = self.typing.needed_returns()
            for k in list(self.typing.R):
                if k not in need:
                    pass
            new = {k: F for k, F in need.items() if k not in self.typing.R}
            if not new:
                break
            self.typing.R.update(new)
            self.typing.solve(propagate=True)
        for s, d in overrides.get("returns", {}).items():
            for c, F in d.items():
                if F is None:
                    self.typing.R.pop((s, c), None)
                else:
                    self.typing.R[(s, c)] = F
        self.typing.solve(propagate=True)
        self.notes += self.typing.notes

    # ------------------------------------------------------------------------------

    def member(self, F, label, where):
        aliases = self.ov.get("labels", {}).get(F, {})
        name = aliases.get(label, label)
        if name not in self.families[F]:
            raise GenerationError("%s: label %r is not a member of %s %s"
                                  % (where, label, F, self.families[F]))
        return name

    def run(self):
        T = self.typing
        conv = []          # (space, node, F, label, where)  label sites
        vals = []          # (space, node)  value uses -> .name
        wraps = []         # (space, node, F)  return wrapped F[...]
        nones = []         # (space, cmp node, F, key, pos)
        none_args = []     # (space, call, key, pos)
        missing = []       # (space, call, key, pos)
        for fn in T.fns.values():
            sp = fn.space
            where = "%s.%s" % (sp, fn.name)
            label_ctx = {}           # id(node) -> F for constants at label sites
            allowed = set()          # id(node) of typed exprs in an allowed context

            def site(node, F):
                for b in Typing._branches(node):
                    if is_label(b):
                        label_ctx[id(b)] = (b, F)
                    elif T.fam(fn, b) == F:
                        allowed.add(id(b))
                    elif isinstance(b, ast.Constant) and b.value is None:
                        pass
                if isinstance(node, ast.IfExp):
                    allowed.add(id(node))

            # sources of typed locals
            for name, F in fn.local_fam.items():
                for s in fn.bindings.get(name, []):
                    if isinstance(s, ast.AST):
                        site(s, F)
            for node in ast.walk(fn.node):
                if isinstance(node, ast.Call):
                    key, args = T.call_args(fn, node)
                    if key is None:
                        continue
                    typed = T.P.get(key, {})
                    given = {pos for pos, _ in args}
                    for pos, a in args:
                        F = typed.get(pos)
                        if F is None:
                            continue
                        if isinstance(a, ast.Constant) and a.value is None:
                            none_args.append((sp, a, key, pos, F))
                            continue
                        site(a, F)
                        for b in Typing._branches(a):
                            if not (is_label(b) or T.fam(fn, b) == F):
                                # a label computed from text: looked up by name
                                wraps.append((sp, b, F))
                                allowed.add(id(b))
                                self.notes.append("%s: %s passed to %s.%s is looked up as %s[...]"
                                                  % (where, ast.unparse(b), key[0], key[1], F))
                    for pos, F in typed.items():
                        if pos not in given and not any(isinstance(a, ast.Starred) for a in node.args):
                            missing.append((sp, node, key, pos, F))
                elif isinstance(node, ast.Compare):
                    for a, op, b in T.other_sides(node):
                        for x, y in ((a, b), (b, a)):
                            Fx = T.fam(fn, x)
                            if Fx is None:
                                continue
                            Fy = T.fam(fn, y)
                            if isinstance(op, (ast.Is, ast.IsNot)) and isinstance(y, ast.Constant) \
                                    and y.value is None:
                                allowed.add(id(x))
                                nones.append((sp, node, Fx, fn, x, op))
                            elif isinstance(op, (ast.In, ast.NotIn)) and isinstance(
                                    y, (ast.Tuple, ast.List, ast.Set)):
                                allowed.add(id(x))
                                for e in y.elts:
                                    site(e, Fx)
                            elif isinstance(op, (ast.Eq, ast.NotEq, ast.Is, ast.IsNot)) and (
                                    is_label(y) or Fy == Fx or isinstance(y, ast.IfExp)):
                                allowed.add(id(x))
                                site(y, Fx)
                            elif isinstance(op, (ast.Eq, ast.NotEq, ast.In, ast.NotIn)) and Fy is None:
                                # compared with a string from data: compare the label
                                self.notes.append("%s: %s compared with %s -> %s.name" % (
                                    where, ast.unparse(x), ast.unparse(y), ast.unparse(x)))
                            else:
                                raise GenerationError("%s: %s (%s) used with %s %s" % (
                                    where, ast.unparse(x), Fx, type(op).__name__, ast.unparse(y)))
            # returns of member-returning cells
            F = T.R.get(fn.key)
            if F:
                for r in fn.returns():
                    for b in Typing._branches(r.value):
                        if is_label(b):
                            label_ctx[id(b)] = (b, F)
                        elif T.fam(fn, b) == F:
                            allowed.add(id(b))
                        else:
                            wraps.append((sp, b, F))
                    if isinstance(r.value, ast.IfExp):
                        allowed.add(id(r.value))
            # cells returning a sequence of members (``opt_legs``)
            F = T.seq_returns.get(fn.key)
            if F:
                for r in fn.returns():
                    for b in Typing._branches(r.value):
                        if isinstance(b, (ast.Tuple, ast.List)):
                            for e in b.elts:
                                if is_label(e):
                                    label_ctx[id(e)] = (e, F)
                                elif T.fam(fn, e) != F:
                                    raise GenerationError("%s: %s in a sequence of %s"
                                                          % (where, ast.unparse(e), F))
            # local assignments of typed values
            for node in ast.walk(fn.node):
                if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                        and isinstance(node.targets[0], ast.Name) \
                        and node.targets[0].id in fn.local_fam:
                    for b in Typing._branches(node.value):
                        allowed.add(id(b))
                    allowed.add(id(node.value))
            # call arguments already typed
            for node in ast.walk(fn.node):
                if isinstance(node, ast.Call):
                    key, args = T.call_args(fn, node)
                    for pos, a in args:
                        if key and T.P.get(key, {}).get(pos):
                            for b in Typing._branches(a):
                                allowed.add(id(b))
                            allowed.add(id(a))
            # value uses: typed expressions anywhere else
            for node in ast.walk(fn.node):
                if id(node) in allowed:
                    continue
                if isinstance(node, (ast.Name, ast.Call)) and T.fam(fn, node):
                    if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Load):
                        continue
                    par = fn.parent.get(node)
                    if isinstance(par, ast.IfExp) and id(par) in allowed:
                        continue
                    if in_raise(fn, node):
                        continue        # upstream's raise ValueError(...) stays as upstream
                    if isinstance(par, ast.Return) and T.R.get(fn.key):
                        continue
                    vals.append((sp, node))
                    self.notes.append("%s: value use %s -> %s.name" % (
                        where, ast.unparse(node), ast.unparse(node)))
            for _, (b, F) in label_ctx.items():
                conv.append((sp, b, F, b.value, where))

        # members that upstream never spells stand for a None default (``Kind.ALL``)
        spelled = {}
        for sp, b, F, label, where in conv:
            spelled.setdefault(F, set()).add(self.ov.get("labels", {}).get(F, {}).get(label, label))
        none_member = dict(self.ov.get("none_member", {}))

        def nm(F, where):
            if F in none_member:
                return none_member[F]
            extra = [m for m in self.families[F] if m not in spelled.get(F, set())]
            if len(extra) != 1:
                raise GenerationError("%s: cannot tell which %s member stands for None "
                                      "(unspelled: %s)" % (where, F, extra))
            none_member[F] = extra[0]
            return extra[0]

        edits = {}           # space -> Source
        for s, spc in self.model.spaces.items():
            edits[s] = spc.src
        for sp, b, F, label, where in conv:
            edits[sp].replace(b, "%s.%s" % (F, self.member(F, label, where)))
            self.used.setdefault(sp, set()).add(F)
        for sp, node in vals:
            edits[sp].insert_after(node, ".name")
        for sp, node, F in wraps:
            edits[sp].insert_before(node, F + "[")
            edits[sp].insert_after(node, "]")
            self.used.setdefault(sp, set()).add(F)
        for sp, cmp, F, fn, x, op in nones:
            m = nm(F, "%s.%s" % (sp, fn.name))
            text = "%s %s %s.%s" % (edits[sp].segment(x), "==" if isinstance(op, ast.Is) else "!=", F, m)
            if len(cmp.ops) != 1:
                raise GenerationError("chained None comparison in %s" % fn.name)
            edits[sp].replace(cmp, text)
            self.used.setdefault(sp, set()).add(F)
        for sp, a, key, pos, F in none_args:
            edits[sp].replace(a, "%s.%s" % (F, nm(F, "%s.%s" % key)))
            self.used.setdefault(sp, set()).add(F)
        # defaults: ``kind=None`` of a typed parameter is dropped
        dropped = set()
        self.default_member = {}
        for key, typed in T.P.items():
            if key not in T.fns:
                continue
            defaults = self.model.defaults(key)
            names = self.model.params(key)
            fnode = T.fns[key].node
            for pos, F in typed.items():
                d = defaults.get(names[pos])
                if d is None:
                    continue
                if isinstance(d, ast.Constant) and d.value is None:
                    self.default_member[(key, pos)] = nm(F, "%s.%s" % key)
                elif is_label(d):
                    self.default_member[(key, pos)] = self.member(F, d.value, "%s.%s" % key)
                else:
                    raise GenerationError("%s.%s: typed parameter %s has default %s"
                                          % (key[0], key[1], names[pos], ast.unparse(d)))
                arg = (fnode.args.posonlyargs + fnode.args.args)[pos]
                src = edits[key[0]]
                start, _ = src.span(arg)
                _, end = src.span(d)
                src.replace_span(start, end, names[pos])
                dropped.add((key, pos))
        for sp, call, key, pos, F in missing:
            if (key, pos) not in dropped:
                raise GenerationError("%s: call to %s.%s omits typed argument %d"
                                      % (sp, key[0], key[1], pos))
            n = len(call.args) + len(call.keywords)
            if pos != n:
                raise GenerationError("call to %s.%s omits argument %d out of order" % (key + (pos,)))
            m = self.default_member[(key, pos)]
            last = (call.args + [k.value for k in call.keywords])[-1] if n else None
            if last is None:
                src = edits[sp]
                _, end = src.span(call.func)
                paren = src.text.index("(", end)
                src.replace_span(paren + 1, paren + 1, "%s.%s" % (F, m))
            else:
                edits[sp].insert_after(last, ", %s.%s" % (F, m))
            self.used.setdefault(sp, set()).add(F)
        self.none_member = none_member
        self.k2(edits)
        return {s: edits[s].apply() for s in edits}

    # -- K2 ---------------------------------------------------------------------------

    def k2(self, edits):
        cells = {}
        for s, cs in self.refmap.get("list_cells", {}).items():
            cells.setdefault(s, set()).update(cs)
        for s, cs in self.ov.get("list_cells", {}).items():
            cells.setdefault(s, set()).update(cs)
        for s, names in cells.items():
            sp = self.model.spaces[s]
            for c in sorted(names):
                if c not in sp.cells:
                    self.notes.append("K2: %s.%s is not in upstream" % (s, c))
                    continue
                fn = self.typing.fns[(s, c)]
                done = set()
                for r in fn.returns():
                    self._listify(fn, r.value, edits[s], done, top=True)

    def _listify(self, fn, node, src, done, top=False):
        if id(node) in done:
            return
        done.add(id(node))
        text = src.segment(node)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "tuple":
            if len(node.args) == 1 and isinstance(node.args[0], ast.GeneratorExp):
                assert text.startswith("tuple(") and text.endswith(")"), text
                src.replace(node, "[" + text[len("tuple("):-1] + "]")
            else:
                src.replace(node, "list" + text[len("tuple"):])
        elif isinstance(node, ast.Tuple):
            if text.startswith("(") and text.endswith(")"):
                inner = text[1:-1]
                if len(node.elts) == 1 and inner.rstrip().endswith(","):
                    inner = inner.rstrip()[:-1]
                src.replace(node, "[" + inner + "]")
            elif top:
                for e in node.elts:          # ``return a, b, c``: several vectors
                    self._listify(fn, e, src, done)
        elif isinstance(node, ast.BinOp):
            self._listify(fn, node.left, src, done)
            self._listify(fn, node.right, src, done)
        elif isinstance(node, ast.IfExp):
            self._listify(fn, node.body, src, done, top)
            self._listify(fn, node.orelse, src, done, top)
        elif isinstance(node, ast.Name):
            for s in fn.bindings.get(fn.key_of(node), []):
                if isinstance(s, ast.AST):
                    self._listify(fn, s, src, done)
