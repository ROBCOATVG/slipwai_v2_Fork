"""The tool names an extension needs a headless session to be allowed to call.

The third thing an `extension.json` declares, beside `hooks` and `guards`, and the smallest. A hook is
something the extension runs; a guard is something it may refuse; a tool is something *the agent* calls that
belongs to the extension — `codegraph`'s MCP server, read as `mcp__codegraph__*` — and a headless session
started under an allow-list that does not name it cannot reach the extension at all.

It is here rather than in the harness registry because of what 6.1c is about. `registry.json` is the keel's
catalogue of coding agents, and it carried `mcp__codegraph__*` in Claude Code's allow-list: every project
the keel generated was handed one extension's tool name whether it had elected that extension or not, and a
project that elected none still shipped a file naming one. The fact belongs to whoever brings the tool.

Nothing is validated against a harness. A pattern is a string the harness will read in its own spelling, and
a keel that checked them would be a keel that has to be released before an extension can use a tool it
invented. What is held here is that the declaration is a list of non-empty strings, which is the shape every
reader of it assumes.
"""
from __future__ import annotations

#: The manifest key, and the file the generator writes the merged declarations to is named for it.
BLOCK = "tools"


def declared(manifest: dict) -> tuple[str, ...]:
    """An extension's tool patterns, in the order it declared them, or `()` where it declares none.

    Order is kept rather than sorted: an extension that names a broad pattern after a narrow one meant
    something by it, and a harness that reads the list in order would be given a different list.
    """
    block = manifest.get(BLOCK)
    if block is None:
        return ()
    if not isinstance(block, list) or not all(isinstance(name, str) and name.strip() for name in block):
        raise ValueError(f"{BLOCK} is a list of tool names, each a non-empty string")
    return tuple(name.strip() for name in block)
