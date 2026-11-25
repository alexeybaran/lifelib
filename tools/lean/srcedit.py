"""Text edits addressed by ``ast`` node positions.

``ast`` gives columns as UTF-8 byte offsets; the model sources hold non-ASCII text, so
every position is converted to a character offset in the decoded source before an edit
is applied.  Edits are collected first and applied in one pass, last first, so that one
edit never shifts the position of another; overlapping edits are an error.
"""


class Source:
    """A module's text with ``ast``-position helpers and a list of pending edits."""

    def __init__(self, text):
        self.text = text
        self.lines = text.splitlines(keepends=True)
        self.starts = [0]
        for line in self.lines:
            self.starts.append(self.starts[-1] + len(line))
        self.edits = []          # (start, end, replacement)

    def offset(self, lineno, col_byte):
        line = self.lines[lineno - 1]
        return self.starts[lineno - 1] + len(line.encode("utf-8")[:col_byte].decode("utf-8"))

    def span(self, node):
        return (self.offset(node.lineno, node.col_offset),
                self.offset(node.end_lineno, node.end_col_offset))

    def segment(self, node):
        start, end = self.span(node)
        return self.text[start:end]

    def replace(self, node, text):
        start, end = self.span(node)
        self.edits.append((start, end, text))

    def replace_span(self, start, end, text):
        self.edits.append((start, end, text))

    def insert_before(self, node, text):
        start, _ = self.span(node)
        self.edits.append((start, start, text))

    def insert_after(self, node, text):
        _, end = self.span(node)
        self.edits.append((end, end, text))

    def apply(self):
        # stable: edits at one offset apply in the order they were made
        seen, uniq = set(), []
        for e in self.edits:
            if e not in seen:
                seen.add(e)
                uniq.append(e)
        edits = sorted(uniq, key=lambda e: (e[0], e[1]))
        out = []
        pos = 0
        last_end = -1
        for start, end, text in edits:
            if start < last_end:
                raise ValueError("overlapping edits at offset %d: %r" % (start, edits))
            out.append(self.text[pos:start])
            out.append(text)
            pos = end
            last_end = end
        out.append(self.text[pos:])
        return "".join(out)
