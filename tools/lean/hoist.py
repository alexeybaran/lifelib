"""The optional ``hoists`` override: adopt hoisted cells of the full conversion.

Off by default.  ``hoists = {Projection = ["cost_row"]}`` in a model's overrides file
inserts the reference's ``cost_row`` before the first cell that uses it and replaces each
user cell's upstream text with the reference's text of that cell.  Policy-attribute
families, which the lean text keeps as strings, are spelled back as upstream labels
(``SurplusUse.bonus`` -> ``"bonus"``, ``Sex[x]`` -> ``x``); argument families stay members
and the lean rewrite then treats the adopted text like any other.
"""

import ast

from srcedit import Source


def despell(text, families, keep):
    """Undo the reference's spelling of the families not in ``keep``."""
    tree = ast.parse(text)
    src = Source(text)
    for node in ast.walk(tree):
        if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                and node.value.id in families and node.value.id not in keep):
            src.replace(node, '"%s"' % node.attr)
        elif (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name)
                and node.value.id in families and node.value.id not in keep):
            src.replace(node, src.segment(node.slice))
    return src.apply()


def adopt(texts, model, refmap, hoists, keep):
    """Return the space texts with the requested hoists applied."""
    fams = refmap["families"]
    for space, names in hoists.items():
        sources = refmap["hoist_sources"].get(space, {})
        users = set()
        for h in names:
            users.update(refmap["hoists"][space][h])
        text = texts[space]
        tree = ast.parse(text)
        src = Source(text)
        cells = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
        inserted = set()
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef) or node.name not in users:
                continue
            new = despell(sources[node.name], fams, keep)
            before = ""
            for h in names:
                if h not in inserted and node.name in refmap["hoists"][space][h]:
                    before += despell(sources[h], fams, keep) + "\n\n\n"
                    inserted.add(h)
            src.replace(node, before + new)
        missing = set(names) - inserted
        if missing:
            raise ValueError("hoists %s: no user cell in upstream text" % sorted(missing))
        texts[space] = src.apply()
    return texts
