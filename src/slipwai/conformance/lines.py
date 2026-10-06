"""The one line a finding is: whatever a package's files said, folded to a single line and cut to `LIMIT`."""
from __future__ import annotations

LIMIT = 200


def one_line(text: str, limit: int = LIMIT) -> str:
    """`text` on one line, its runs of whitespace (newlines included) folded to a space, and at most `limit` long."""
    folded = " ".join(text.split())
    return folded if len(folded) <= limit else folded[: limit - 1] + "…"
