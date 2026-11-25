"""Write a lean model folder: rewritten spaces, the stored enums module and its pickles.

The enums travel with the model (modelx ``new_module``, stored as ``ModuleData``):

``<Model>/enums.py``            the argument families, members and values of the reference
``<Model>/_data/iospecs.py``    ``(1, 'ModuleData', 1, 'enums.py', {}, {})``
``<Model>/_data/data.pickle``   ``{n: <class or member>}``, each class pickled as the
                                persistent id ``("ModuleAttr", 1, "<Family>")`` that modelx
                                resolves against the module loaded from the folder
``<Model>/__init__.py``         gains ``enums = ("IOSpec", 1)``
``<Space>/__init__.py``         gains ``<Family> = ("Pickle", n)`` for each family it spells

The pickle is written with the standard library; its content is the one modelx's own
``ModelPickler`` writes for the same References (see the modelx S4 notes).
"""

import io
import pickle

SPEC_ID = 1


class _Attr:
    """A class of the stored module, pickled by persistent id."""

    def __init__(self, name):
        self.name = name

    def __call__(self, *args):          # pickle requires a callable in a reduce tuple
        raise TypeError("placeholder")


class _Member:
    """A member, pickled as ``Family(value)`` with the class by persistent id."""

    def __init__(self, cls, value):
        self.cls = cls
        self.value = value

    def __reduce__(self):
        return (self.cls, (self.value,))


class _Pickler(pickle.Pickler):
    def persistent_id(self, obj):
        if isinstance(obj, _Attr):
            return ("ModuleAttr", SPEC_ID, obj.name)
        return None


def data_pickle(entries):
    """``entries``: {id: ("class", F) | ("member", F, value)} -> bytes."""
    attrs = {}

    def cls(F):
        return attrs.setdefault(F, _Attr(F))

    obj = {}
    for n in sorted(entries):
        e = entries[n]
        obj[n] = cls(e[1]) if e[0] == "class" else _Member(cls(e[1]), e[2])
    buf = io.BytesIO()
    _Pickler(buf, protocol=4).dump(obj)
    return buf.getvalue()


BY_TEXT = '''
class Text(str):
    """A label that is not a member: upstream's text, which also reads as ``.name``."""

    @property
    def name(self):
        return str(self)


class ByText(EnumType):
    """``Family[text]`` of a text that is not a member gives the text itself.

    A family the formulas look up by text (a label read from data or built from text)
    uses this: an unknown label then takes upstream's path, to upstream's own check
    (``raise ValueError("invalid credit_method")``) or upstream's failed table lookup.
    """

    def __getitem__(cls, text):
        member = cls._member_map_.get(text)
        if member is not None:
            return member
        return Text(text) if isinstance(text, str) else text
'''


def enums_module(model, families, keep, by_text=()):
    """The model's ``enums.py``; the families in ``by_text`` take the ``ByText`` lookup."""
    by_text = [F for F in families if F in keep and F in by_text]
    lines = ['"""IntEnum families passed as cell arguments in %s, stored with the model."""'
             % model, "", ("from enum import EnumType, IntEnum" if by_text else
                           "from enum import IntEnum"), ""]
    if by_text:
        lines += BY_TEXT.split("\n")
    for F, members in families.items():
        if F not in keep:
            continue
        lines += ["", "class %s(IntEnum%s):" % (F, ", metaclass=ByText" if F in by_text else "")]
        lines += ["    %s = %d" % (m, v) for m, v in members]
        lines.append("")
    return "\n".join(lines)


IOSPECS = "# modelx: iospecs\n# (key, class, version, path, io_args, spec_args)\n(1, 'ModuleData', 1, 'enums.py', {}, {})\n"

MODEL_REF = ("\n\n# ---------------------------------------------------------------------------\n"
             "# References\n\nenums = (\"IOSpec\", 1)  # ModuleData path='enums.py'\n")


def append_refs(text, refs):
    """Append ``name = ("Pickle", n)`` References at the end of a space's text."""
    if not refs:
        return text
    final = text.endswith("\n")         # keep upstream's final-newline state
    text = text.rstrip("\n") + "\n"
    for name, n in refs:
        text += '\n%s = ("Pickle", %d)\n' % (name, n)
    return text if final else text.rstrip("\n")
