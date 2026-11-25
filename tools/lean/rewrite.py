"""The lean rewrite of one model's upstream text, from its family map.

Rules (see GENERATOR.md for the owner's wording):

K1  label sites of a typed position become ``Family.MEMBER``.  Families are StrEnum
    classes whose member values are upstream's label text, so a member equals, hashes and
    prints as its label: every other use of a typed value (a table key, a column label,
    an f-string, a comparison with text from data) stays as upstream writes it, and so do
    defaults (``kind=None``, ``kind is None``, calls that omit the argument), tuples and
    References.  A label computed from text at a typed position, and the result of a
    policy-attribute cell that is passed on as a cell argument, is converted once by
    name, ``Family[...]`` (an unknown label raises ``KeyError``).
Everything else is upstream text, byte for byte.
"""

import ast

from engine import GenerationError, Typing, is_label


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
        wraps = []         # (space, node, F)  return wrapped F[...]
        nones = []         # (space, cmp node, F, key, pos)
        none_args = []     # (space, call, key, pos)
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
                                # compared with a string from data: a member is its label
                                self.notes.append("%s: %s compared with text %s" % (
                                    where, ast.unparse(x), ast.unparse(y)))
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
            for _, (b, F) in label_ctx.items():
                conv.append((sp, b, F, b.value, where))

        # A member that upstream never spells and that the reference used for a None
        # default (``Kind.ALL``) is not emitted: upstream's ``kind=None`` stays as it is.
        spelled = {}
        for sp, b, F, label, where in conv:
            spelled.setdefault(F, set()).add(self.ov.get("labels", {}).get(F, {}).get(label, label))
        none_member = dict(self.ov.get("none_member", {}))

        def nm(F, where):
            if F in none_member:
                return none_member[F]
            extra = [m for m in self.families[F] if m not in spelled.get(F, set())]
            if len(extra) == 1:
                none_member[F] = extra[0]
                return extra[0]
            return None

        edits = {}           # space -> Source
        for s, spc in self.model.spaces.items():
            edits[s] = spc.src
        for sp, b, F, label, where in conv:
            edits[sp].replace(b, "%s.%s" % (F, self.member(F, label, where)))
            self.used.setdefault(sp, set()).add(F)
        for sp, node, F in wraps:
            edits[sp].insert_before(node, F + "[")
            edits[sp].insert_after(node, "]")
            self.used.setdefault(sp, set()).add(F)
        for sp, cmp, F, fn, x, op in nones:
            nm(F, "%s.%s" % (sp, fn.name))
        for sp, a, key, pos, F in none_args:
            nm(F, "%s.%s" % key)
        # defaults stay as upstream writes them (``kind=None``, ``weighting="count"``);
        # a text default must still be a label of the family
        for key, typed in T.P.items():
            if key not in T.fns:
                continue
            defaults = self.model.defaults(key)
            names = self.model.params(key)
            for pos, F in typed.items():
                d = defaults.get(names[pos])
                if d is None:
                    continue
                if isinstance(d, ast.Constant) and d.value is None:
                    nm(F, "%s.%s" % key)
                elif is_label(d):
                    self.member(F, d.value, "%s.%s" % key)
                else:
                    raise GenerationError("%s.%s: typed parameter %s has default %s"
                                          % (key[0], key[1], names[pos], ast.unparse(d)))
        self.none_member = {F: m for F, m in none_member.items()
                            if m is not None and m not in spelled.get(F, set())}
        self.tuples(edits)
        return {s: edits[s].apply() for s in edits}

    # -- sequences of numbers are tuples ---------------------------------------------

    def tuples(self, edits):
        """``tuple_cells``: cells upstream returns a list from, made to return a tuple.

        Each returned list becomes a tuple of the same values: ``[f(z) for z in zs]`` ->
        ``tuple(f(z) for z in zs)``, ``list(x)`` -> ``tuple(x)``, ``[0.0] * n`` ->
        ``(0.0,) * n``, a list display -> a tuple display, any other expression (a local
        list) -> ``tuple(x)``; ``return a, b`` converts each element.
        """
        for s, names in self.ov.get("tuple_cells", {}).items():
            sp = self.model.spaces[s]
            for c in names:
                if c not in sp.cells:
                    raise GenerationError("tuple_cells: %s.%s is not in upstream" % (s, c))
                fn = self.typing.fns[(s, c)]
                for r in fn.returns():
                    v = r.value
                    for e in (v.elts if isinstance(v, ast.Tuple) else [v]):
                        self._tuplify(e, edits[s])

    def _tuplify(self, node, src):
        text = src.segment(node)
        if isinstance(node, ast.ListComp):
            src.replace(node, "tuple(" + text[1:-1] + ")")
        elif isinstance(node, ast.List):
            inner = text[1:-1].rstrip()
            if len(node.elts) == 1 and not inner.endswith(","):
                inner += ","
            src.replace(node, "(" + inner + ")")
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult) \
                and isinstance(node.left, ast.List):
            self._tuplify(node.left, src)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id == "list":
            src.replace(node.func, "tuple")
        elif isinstance(node, ast.Tuple):
            raise GenerationError("tuple_cells: a nested tuple %s" % text[:40])
        else:
            src.replace(node, "tuple(%s)" % text)

