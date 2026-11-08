"""Opt-in, inspectable boolean helper adaptation of ordinary model formulas.

Apply to a separately loaded adjusted model. Original serialized model files
are never written. This overlay changes authoring syntax; its receipt is not a
claim that every changed expression has obtained native compiler coverage.
"""
import ast
import builtins
import hashlib

from .typed_inputs import all_true, any_true


_HELPERS = {'all': ('all_true', all_true), 'any': ('any_true', any_true)}


def _digest(source):
    return hashlib.sha256(source.encode('utf-8')).hexdigest()


def _rewrite(source, available):
    tree = ast.parse(source)
    if any(isinstance(n, (ast.ClassDef, ast.AsyncFunctionDef)) for n in ast.walk(tree)):
        return source, ()
    # Avoid moving builtin facts into a lexical scope which binds that name.
    # Declining is deliberately conservative, including comprehension bindings.
    bound = {n.id for n in ast.walk(tree)
             if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del))}
    bound.update(n.arg for n in ast.walk(tree) if isinstance(n, ast.arg))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            bound.update(node.names)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, ast.alias):
            bound.add(node.asname or node.name.split('.')[0])
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
    available = set(available) - bound
    # A nested function may receive a different global environment on export.
    functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.Lambda))]
    if len(functions) != 1:
        return source, ()
    used = set()

    class Rewrite(ast.NodeTransformer):
        def visit_Call(self, node):
            self.generic_visit(node)
            if (isinstance(node.func, ast.Name) and node.func.id in available
                    and len(node.args) == 1 and not node.keywords
                    and not isinstance(node.args[0], ast.Starred)):
                used.add(node.func.id)
                node.func.id = _HELPERS[node.func.id][0]
            return node

    Rewrite().visit(tree)
    return (ast.unparse(tree) + '\n', tuple(sorted(used))) if used else (source, ())


def apply_generators(model):
    """Bind existing all_true/any_true helpers and adapt builtin boolean calls.

    Return per-Cell before/after sources and hashes for review and provenance.
    Existing Cells/References named all/any prevent that adaptation; a conflicting
    all_true/any_true binding also prevents it. Do not infer immutability of other
    model References or report native coverage from this authoring adjustment.
    """
    receipt = []

    def visit(space):
        available = []
        for name, (helper, function) in _HELPERS.items():
            if name in space.cells:
                continue
            current = getattr(space, name, getattr(builtins, name))
            existing = getattr(space, helper, function)
            if current is getattr(builtins, name) and existing is function:
                available.append(name)
        for cell in list(space.cells.values()):
            if cell.formula is None:
                continue
            before = cell.formula.source
            after, used = _rewrite(before, available)
            if not used:
                continue
            for name in used:
                helper, function = _HELPERS[name]
                setattr(space, helper, function)
            doc = cell.doc
            cell.formula = after
            if doc:
                cell.doc = doc
            receipt.append({'cell': cell.fullname, 'before': before, 'after': after,
                            'before_sha256': _digest(before), 'after_sha256': _digest(after),
                            'helpers': [_HELPERS[name][0] for name in used],
                            'native_coverage': 'UNQUALIFIED'})
        for child in list(space.spaces.values()):
            visit(child)

    for space in list(model.spaces.values()):
        visit(space)
    return receipt
