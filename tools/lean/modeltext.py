"""Read a modelx model folder as source text: its spaces, cells and References."""

import ast
import pathlib

from srcedit import Source


class SpaceText:
    """One space's ``__init__.py``: cells (top-level defs) and References (assignments)."""

    def __init__(self, name, path, text):
        self.name = name
        self.path = path
        self.src = Source(text)
        self.tree = ast.parse(text)
        self.cells = {}
        self.refs = {}
        self.space_refs = {}
        for node in self.tree.body:
            if isinstance(node, ast.FunctionDef):
                self.cells[node.name] = node
            elif (isinstance(node, ast.Assign) and len(node.targets) == 1
                  and isinstance(node.targets[0], ast.Name)):
                name = node.targets[0].id
                self.refs[name] = node
                value = node.value
                if (isinstance(value, ast.Tuple) and value.elts
                        and isinstance(value.elts[0], ast.Constant)
                        and value.elts[0].value == "Interface"):
                    target = value.elts[1]
                    if isinstance(target, ast.Tuple) and len(target.elts) == 2:
                        self.space_refs[name] = target.elts[1].value

    @property
    def text(self):
        return self.src.text

    def pickled_refs(self):
        """Names of References stored as ``("Pickle", n)``."""
        out = {}
        for name, node in self.refs.items():
            v = node.value
            if (isinstance(v, ast.Tuple) and len(v.elts) == 2
                    and isinstance(v.elts[0], ast.Constant) and v.elts[0].value == "Pickle"):
                out[name] = v.elts[1].value
        return out


class ModelText:
    def __init__(self, folder, texts=None):
        """``texts``: optional {space: text} overriding what is on disk."""
        self.folder = pathlib.Path(folder)
        init = (self.folder / "__init__.py").read_text(encoding="utf-8")
        tree = ast.parse(init)
        names = []
        for node in tree.body:
            if (isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id == "_spaces"):
                names = [e.value for e in node.value.elts]
        self.init_text = init
        self.spaces = {}
        for name in names:
            path = self.folder / name / "__init__.py"
            text = texts[name] if texts and name in texts else path.read_text(encoding="utf-8")
            self.spaces[name] = SpaceText(name, path, text)

    def callee(self, space, call):
        """(space, cell) of a call to a cell, or None."""
        f = call.func
        sp = self.spaces[space]
        if isinstance(f, ast.Name) and f.id in sp.cells:
            return (space, f.id)
        if (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)
                and f.value.id in sp.space_refs):
            target = sp.space_refs[f.value.id]
            if target in self.spaces and f.attr in self.spaces[target].cells:
                return (target, f.attr)
        return None

    def params(self, key):
        space, cell = key
        fn = self.spaces[space].cells[cell]
        return [a.arg for a in fn.args.posonlyargs + fn.args.args]

    def defaults(self, key):
        """{param name: default node}"""
        space, cell = key
        fn = self.spaces[space].cells[cell]
        args = fn.args.posonlyargs + fn.args.args
        d = fn.args.defaults
        return {a.arg: dn for a, dn in zip(args[len(args) - len(d):], d)}
