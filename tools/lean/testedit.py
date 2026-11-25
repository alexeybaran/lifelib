"""The mechanical test edits the lean text requires.

A test calls the model's cells on an ItemSpace (``p.claims(t, "DEATH")``).  Where the lean
text types that argument, the test passes the member instead (``Kind.DEATH``); a call that
omits a dropped ``kind=None`` argument passes the ``None`` member; a test that compares a
member-returning cell's result with a string label compares it with the member.  Loops
over label tuples whose variable reaches a typed argument become loops over members.

The families come from the model folder's own ``enums.py``, loaded by the library's test
registry (``model_enums``), never from the lifelib package.  IntEnum members compare and
hash as their integers, so a member of the test's copy of the class finds the same cache
entry as the model's own member.
"""

import ast

from engine import OPAQUE, is_label
from srcedit import Source

MEMBERS = object()      # a source that already holds members

REGISTRY_HELPER = '''

def model_enums(name, *families):
    """The IntEnum families stored in model ``name``'s folder, in the order asked.

    The lean conversion keeps a model's label families in ``<model>/enums.py``, a module
    stored with the model; tests load that file rather than import it from lifelib.
    """
    import importlib.util
    path = model_path(name) / "enums.py"
    spec = importlib.util.spec_from_file_location("_enums_" + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return tuple(getattr(module, f) for f in families)
'''


class TestEditor:
    def __init__(self, text, typed, returns, families, none_member, member_refs=None):
        """typed: {cell: {pos: F}}; returns: {cell: F} (by cell name, any receiver)."""
        self.src = Source(text)
        self.tree = ast.parse(text)
        self.typed = typed
        self.returns = returns
        self.families = families
        self.none_member = none_member
        self.member_refs = member_refs or {}
        self.seq_returns = {}
        self.used = set()
        self.count = 0
        self.unhandled = []
        self.kept = []
        self._seen = set()

    def member(self, F, label):
        if label not in self.families[F]:
            raise ValueError("test label %r is not a member of %s" % (label, F))
        self.used.add(F)
        self.count += 1
        return "%s.%s" % (F, label)

    def cell_of(self, call):
        f = call.func
        if isinstance(f, ast.Attribute) and f.attr in self.typed:
            return f.attr
        # a bare call inside a function the test installs as a formula
        if isinstance(f, ast.Name) and f.id in self.typed and f.id not in self.module_names:
            return f.id
        return None

    def run(self):
        self.parent = {}
        for p in ast.walk(self.tree):
            for c in ast.iter_child_nodes(p):
                self.parent[c] = p
        self.module_names = set()
        for n in ast.walk(self.tree):
            if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
                self.module_names.add(n.name)
            elif isinstance(n, (ast.Import, ast.ImportFrom)):
                self.module_names.update((a.asname or a.name).split(".")[0] for a in n.names)
        self._seq_loops()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):
                cell = self.cell_of(node)
                if cell is None:
                    continue
                for pos, F in self.typed[cell].items():
                    if pos < len(node.args):
                        self._label_site(node.args[pos], F)
                    else:
                        kw = [k for k in node.keywords if k.arg and k.arg == self._pname(cell, pos)]
                        if kw:
                            self._label_site(kw[0].value, F)
                        elif pos in self.none_member.get(cell, {}) and pos == len(node.args) \
                                and not node.keywords and node.args:
                            m = self.none_member[cell][pos]
                            self.src.insert_after(node.args[-1], ", " + self.member(F, m))
            elif isinstance(node, ast.Assign) and len(node.targets) == 1 \
                    and isinstance(node.targets[0], ast.Attribute) \
                    and node.targets[0].attr in self.member_refs:
                self._label_site(node.value, self.member_refs[node.targets[0].attr])
            elif isinstance(node, ast.Compare):
                sides = [node.left] + node.comparators
                pairs = []
                for i, op in enumerate(node.ops):
                    a, b = sides[i], sides[i + 1]
                    pairs.append((a, op, b))
                    if isinstance(op, (ast.Eq, ast.NotEq)) and isinstance(a, ast.Tuple) \
                            and isinstance(b, ast.Tuple) and len(a.elts) == len(b.elts):
                        pairs += [(x, op, y) for x, y in zip(a.elts, b.elts)]
                for a, op, b in pairs:
                    for x, y in ((a, b), (b, a)):
                        F = None
                        if isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) \
                                and x.func.attr in self.returns:
                            F = self.returns[x.func.attr]
                        elif isinstance(x, ast.Attribute) and x.attr in self.member_refs:
                            F = self.member_refs[x.attr]
                        elif isinstance(x, ast.Subscript) and is_label(x.slice) \
                                and x.slice.value in self.member_refs:
                            F = self.member_refs[x.slice.value]     # space.refs["ref_sex"]
                        elif isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) \
                                and x.func.attr in self.seq_returns \
                                and isinstance(y, (ast.Tuple, ast.List)):
                            for e in y.elts:            # p.opt_legs() == ("ATM_CALL", ...)
                                self._label_site(e, self.seq_returns[x.func.attr])
                            continue
                        if F:
                            if isinstance(y, (ast.Tuple, ast.List)) and isinstance(op, (ast.In, ast.NotIn)):
                                for e in y.elts:
                                    self._label_site(e, F)
                            else:
                                self._label_site(y, F)
        return self.src.apply()

    def _sources(self, name, node):
        """The values a Name can hold where it is read: the nearest binding scope."""
        cur = node
        while cur in self.parent:
            par = self.parent[cur]
            gens = []
            if isinstance(par, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
                gens = par.generators
            elif isinstance(par, ast.For) and cur is not par.iter:
                gens = [par]
            for g in gens:
                if isinstance(g.target, ast.Name) and g.target.id == name:
                    self._scope = par
                    if isinstance(g.iter, (ast.Tuple, ast.List)):
                        return list(g.iter.elts)
                    if self._is_seq_call(g.iter):
                        return [MEMBERS]
                    return [OPAQUE]
            if isinstance(par, (ast.FunctionDef, ast.Module)):
                self._scope = par
                out = []
                for p in ast.walk(par):
                    if isinstance(p, ast.Assign) and any(
                            isinstance(t, ast.Name) and t.id == name for t in p.targets):
                        out.append(p.value)
                    elif isinstance(p, ast.For) and isinstance(p.target, ast.Name) \
                            and p.target.id == name:
                        out += (list(p.iter.elts) if isinstance(p.iter, (ast.Tuple, ast.List))
                                else [MEMBERS] if self._is_seq_call(p.iter) else [OPAQUE])
                    elif isinstance(p, ast.arg) and p.arg == name:
                        out.append(OPAQUE)
                return out
            cur = par
        return []

    def _is_seq_call(self, node):
        return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in self.seq_returns)

    def _seq_loops(self):
        """A loop over a cell that returns members holds members: a use as a string
        (a dict key, a label in a message) reads ``.name``."""
        for p in ast.walk(self.tree):
            loops = []
            if isinstance(p, ast.For):
                loops = [(p.target, p.iter, p)]
            elif isinstance(p, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
                loops = [(g.target, g.iter, p) for g in p.generators]
            for target, it, scope in loops:
                if not (isinstance(target, ast.Name) and isinstance(it, ast.Call)
                        and isinstance(it.func, ast.Attribute)
                        and it.func.attr in self.seq_returns):
                    continue
                for n in ast.walk(scope):
                    if not (isinstance(n, ast.Name) and n.id == target.id
                            and isinstance(n.ctx, ast.Load)):
                        continue
                    par = self.parent.get(n)
                    if isinstance(par, ast.Call) and n in par.args and self.cell_of(par):
                        continue                # a typed argument: the member itself
                    if isinstance(par, ast.Call) and n in par.args and \
                            isinstance(par.func, ast.Attribute):
                        continue                # passed to a cell: leave it
                    if isinstance(par, ast.Dict) and n in par.keys or \
                            isinstance(par, ast.Subscript) and par.slice is n or \
                            isinstance(par, ast.DictComp) and par.key is n or \
                            isinstance(par, ast.FormattedValue):
                        if id(n) not in self._seen:
                            self._seen.add(id(n))
                            self.src.insert_after(n, ".name")
                            self.count += 1

    def _only_typed_uses(self, name, scope):
        """Every read of ``name`` in ``scope`` is a typed argument of a cell call."""
        if scope is None:
            return True
        for n in ast.walk(scope):
            if isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, ast.Load):
                par = self.parent.get(n)
                if isinstance(par, ast.keyword):
                    par = self.parent.get(par)
                ok = False
                if isinstance(par, ast.Call):
                    cell = self.cell_of(par)
                    if cell is not None:
                        typed = self.typed[cell]
                        for pos in typed:
                            if pos < len(par.args) and par.args[pos] is n:
                                ok = True
                        for k in par.keywords:
                            if k.value is n and k.arg in [self._pname(cell, p) for p in typed]:
                                ok = True
                if not ok:
                    return False
        return True

    def _pname(self, cell, pos):
        names = getattr(self, "pnames", {}).get(cell, [])
        return names[pos] if pos < len(names) else None

    def _label_site(self, a, F):
        if is_label(a) and a.value not in self.families[F]:
            # an invalid label a test passes on purpose: it still raises, left as it is
            self.kept.append("%s (line %d)" % (a.value, a.lineno))
        elif is_label(a):
            if id(a) not in self._seen:
                self._seen.add(id(a))
                self.src.replace(a, self.member(F, a.value))
        elif isinstance(a, ast.IfExp):
            self._label_site(a.body, F)
            self._label_site(a.orelse, F)
        elif isinstance(a, ast.Name):
            self._scope = None
            srcs = self._sources(a.id, a)
            if srcs and all(x is MEMBERS for x in srcs):
                return                          # a loop over a member-returning cell
            if srcs and all(s is not OPAQUE and is_label(s) for s in srcs) \
                    and self._only_typed_uses(a.id, self._scope):
                for s in srcs:
                    self._label_site(s, F)
            elif srcs and all(s is not OPAQUE and is_label(s) for s in srcs):
                # the labels are also used as strings (a dict key): look up at the call
                if id(a) not in self._seen:
                    self._seen.add(id(a))
                    self.src.replace(a, "%s[%s]" % (F, a.id))
                    self.used.add(F)
                    self.count += 1
            elif any(s is not OPAQUE and is_label(s) for s in srcs):
                self.unhandled.append("mixed sources for %s (line %d)" % (a.id, a.lineno))
            elif id(a) not in self._seen:
                # a label held by a test parameter or a loop over a table: looked up by name
                self._seen.add(id(a))
                self.src.replace(a, "%s[%s]" % (F, a.id))
                self.used.add(F)
                self.count += 1
        elif isinstance(a, ast.Constant) and a.value is None:
            self.unhandled.append("None passed at a typed position (line %d)" % a.lineno)


def add_import(text, registry, model, families):
    """Insert ``from <registry> import model_enums`` and the families after the imports."""
    tree = ast.parse(text)
    last = None
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            last = node
        elif last is not None:
            break
    src = Source(text)
    line = ("\nfrom %s import model_enums\n%s = model_enums(\"%s\", %s)"
            % (registry, ", ".join(families) + ("," if len(families) == 1 else ""), model,
               ", ".join('"%s"' % f for f in families)))
    src.insert_after(last, line)
    return src.apply()
