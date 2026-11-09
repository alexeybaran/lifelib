"""Opt-in, inspectable boolean helper adaptation of ordinary model formulas.

Apply to a separately loaded adjusted model. Original serialized model files
are never written. This overlay changes authoring syntax; its receipt is not a
claim that every changed expression has obtained native compiler coverage.
"""
import builtins
import hashlib

import libcst as cst
from libcst.metadata import ScopeProvider

from .typed_inputs import all_true, any_true
from . import typed_inputs as _operations


_HELPERS = {'all': ('all_true', all_true), 'any': ('any_true', any_true)}
_NAMESPACE = 'generators'


def _digest(source):
    return hashlib.sha256(source.encode('utf-8')).hexdigest()


def _rewrite(source, available):
    wrapper, bound, functions, unsupported = _lexical_source(source)
    if unsupported:
        return source, ()
    available = set(available) - bound
    if _NAMESPACE in bound:
        return source, ()
    # A nested function may receive a different global environment on export.
    if functions != 1:
        return source, ()
    used = set()

    class Rewrite(cst.CSTTransformer):
        def leave_Call(self, before, node):
            if (isinstance(node.func, cst.Name) and node.func.value in available
                    and len(node.args) == 1 and not node.args[0].keyword
                    and not node.args[0].star):
                used.add(node.func.value)
                return node.with_changes(func=cst.Attribute(cst.Name(_NAMESPACE),
                                          cst.Name(_HELPERS[node.func.value][0])))
            return node

    result = wrapper.module.visit(Rewrite()).code
    return (result, tuple(sorted(used))) if used else (source, ())


def _lexical_source(source):
    wrapper = cst.MetadataWrapper(cst.parse_module(source))
    scopes = set(wrapper.resolve(ScopeProvider).values())
    bound = {assignment.name for scope in scopes for assignment in scope.assignments}
    class Declarations(cst.CSTVisitor):
        functions = 0
        unsupported = False
        def visit_FunctionDef(self, node):
            self.functions += 1
            self.unsupported |= node.asynchronous is not None
        def visit_Lambda(self, node): self.functions += 1
        def visit_ClassDef(self, node): self.unsupported = True
    declarations = Declarations()
    wrapper.module.visit(declarations)
    return wrapper, bound, declarations.functions, declarations.unsupported


def _rewrite_streams(source):
    """Offline authoring adjustment, never part of compiler recognition.

    Concrete syntax preserves surrounding formatting. Unsupported lexical
    captures stay untouched for explicit review; no alternative interpreter is
    installed in the model or compiler.
    """
    wrapper, bound, _, unsupported = _lexical_source(source)
    if unsupported or bound & {'over', 'flatten'}:
        return source, ()
    used = set()

    class Rewrite(cst.CSTTransformer):
        def __init__(self):
            self.used_before = []
        def visit_GeneratorExp(self, node):
            self.used_before.append(set(used))
        def leave_GeneratorExp(self, before, node):
            previous = self.used_before.pop()
            def decline():
                used.clear()
                used.update(previous)
                return before
            class Safety(cst.CSTVisitor):
                unsupported = False
                def visit_NamedExpr(self, node): self.unsupported = True
                def visit_Lambda(self, node): self.unsupported = True
                def visit_CompFor(self, node):
                    self.unsupported |= node.asynchronous is not None
            safety = Safety()
            before.visit(safety)
            if safety.unsupported:
                return decline()
            def produce(comp, payload):
                if isinstance(comp.target, cst.Name):
                    names = [comp.target.value]
                    unpack = False
                elif isinstance(comp.target, (cst.Tuple, cst.List)) and all(
                        isinstance(element, cst.Element) and isinstance(element.value, cst.Name)
                        for element in comp.target.elements):
                    names = [element.value.value for element in comp.target.elements]
                    unpack = True
                else:
                    raise ValueError('unsupported generator target')
                nested = comp.inner_for_in is not None
                if nested:
                    payload = produce(comp.inner_for_in, payload)
                parameters = cst.Parameters(params=tuple(cst.Param(cst.Name(name)) for name in names))
                arguments = [cst.Arg(comp.iter), cst.Arg(cst.Lambda(parameters, payload))]
                if comp.ifs:
                    condition = comp.ifs[0].test
                    for item in comp.ifs[1:]:
                        condition = cst.BooleanOperation(condition.with_changes(
                            lpar=(cst.LeftParen(),), rpar=(cst.RightParen(),)), cst.And(),
                            item.test.with_changes(lpar=(cst.LeftParen(),), rpar=(cst.RightParen(),)))
                    arguments.append(cst.Arg(cst.Lambda(parameters, condition), keyword=cst.Name('where')))
                if unpack:
                    arguments.append(cst.Arg(cst.Integer(str(len(names))), keyword=cst.Name('unpack')))
                result = cst.Call(cst.Name('over'), tuple(arguments))
                used.add('over')
                if nested:
                    result = cst.Call(cst.Name('flatten'), (cst.Arg(result),))
                    used.add('flatten')
                return result
            try:
                return produce(node.for_in, node.elt)
            except ValueError:
                return decline()

    result = wrapper.module.visit(Rewrite()).code
    return (result, tuple(sorted(used))) if used else (source, ())


def apply_streams(model):
    """Make an inspectable explicit-stream source proposal on a loaded model.

    Consumers, including ordinary sums, are unchanged. This does not activate
    sum_float's distinct numeric contract. Function References preserve normal
    model pickle behavior. The receipt never asserts native qualification.
    """
    from . import expression_streams as streams
    receipt = []
    def visit(space):
        if any(name in space.cells or getattr(space, name, getattr(streams, name)) is not getattr(streams, name)
               for name in ('over', 'flatten')):
            return
        for cell in list(space.cells.values()):
            if cell.formula is None:
                continue
            before = cell.formula.source
            after, used = _rewrite_streams(before)
            if not used:
                continue
            for name in used:
                setattr(space, name, getattr(streams, name))
            doc = cell.doc
            cell.formula = after
            if doc:
                cell.doc = doc
            receipt.append({'cell': cell.fullname, 'before': before, 'after': after,
                'before_sha256': _digest(before), 'after_sha256': _digest(after),
                'helpers': list(used), 'native_coverage': 'UNQUALIFIED'})
        for child in list(space.spaces.values()):
            visit(child)
    for space in list(model.spaces.values()):
        visit(space)
    return receipt


def apply_generators(model):
    """Bind existing all_true/any_true helpers and adapt builtin boolean calls.

    Return per-Cell before/after sources and hashes for review and provenance.
    Existing Cells/References named all/any prevent that adaptation; a conflicting
    generators namespace also prevents it. The module Reference serializes as an
    import, preserving formulas-only folders without embedded function pickles.
    Do not infer immutability of other
    model References or report native coverage from this authoring adjustment.
    """
    receipt = []

    def visit(space):
        available = []
        namespace = getattr(space, _NAMESPACE, _operations)
        if namespace is not _operations:
            return
        for name, (helper, function) in _HELPERS.items():
            if name in space.cells:
                continue
            current = getattr(space, name, getattr(builtins, name))
            if current is getattr(builtins, name) and getattr(_operations, helper) is function:
                available.append(name)
        for cell in list(space.cells.values()):
            if cell.formula is None:
                continue
            before = cell.formula.source
            after, used = _rewrite(before, available)
            if not used:
                continue
            setattr(space, _NAMESPACE, _operations)
            doc = cell.doc
            cell.formula = after
            if doc:
                cell.doc = doc
            receipt.append({'cell': cell.fullname, 'before': before, 'after': after,
                            'before_sha256': _digest(before), 'after_sha256': _digest(after),
                            'helpers': [_NAMESPACE + '.' + _HELPERS[name][0] for name in used],
                            'native_coverage': 'UNQUALIFIED'})
        for child in list(space.spaces.values()):
            visit(child)

    for space in list(model.spaces.values()):
        visit(space)
    return receipt
