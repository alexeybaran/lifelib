"""Write a lean model folder: rewritten spaces, the stored enums module and its pickles.

The enums travel with the model (modelx ``new_module``, stored as ``ModuleData``):

``<Model>/enums.py``            the argument families and members of the reference, as
                                StrEnum classes whose values are upstream's label text
``<Model>/_data/iospecs.py``    ``(1, 'ModuleData', 1, 'enums.py', {}, {})``
``<Model>/_data/data.pickle``   ``{n: <class>}``, each class pickled as the
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


class _Pickler(pickle.Pickler):
    def persistent_id(self, obj):
        if isinstance(obj, _Attr):
            return ("ModuleAttr", SPEC_ID, obj.name)
        return None


def data_pickle(entries):
    """``entries``: {id: family name} -> bytes."""
    obj = {n: _Attr(entries[n]) for n in sorted(entries)}
    buf = io.BytesIO()
    _Pickler(buf, protocol=4).dump(obj)
    return buf.getvalue()


def enums_module(model, families, keep, labels=None, drop=None):
    """The text of ``enums.py``: one StrEnum per family, each member's value its label.

    ``labels``: {F: {label: member}} where a label is not spelled like its member;
    ``drop``: {F: member} members not emitted (the reference's stand-in for ``None``).
    """
    labels = labels or {}
    drop = drop or {}
    lines = ['"""Label families passed as cell arguments in %s, stored with the model.' % model,
             "",
             "Each member's value is upstream's label text: a member equals, hashes and prints",
             'as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""',
             "", "from enum import StrEnum", ""]
    for F, members in families.items():
        if F not in keep:
            continue
        text = {m: lab for lab, m in labels.get(F, {}).items()}
        lines += ["", "class %s(StrEnum):" % F]
        for m, _ in members:
            if m == drop.get(F):
                continue
            label = text.get(m, m)
            assert '"' not in label and "\\" not in label, label
            lines.append('    %s = "%s"' % (m, label))
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
