"""The `toy` family's rows for the generated pruning script (`prune_rows`).

`./init` prunes what these rows name when a project drops a feature. The toy's one prunable feature is `postgres` (the
in-memory store is always there, and nothing prunes it), whose two placeholder adapters it owns; it marks no region,
adds no package and has no manifest. A real language names, per feature it offers, the files that feature writes
(`owned_files`), the files carrying a marked region (`marked_files`), the packages it adds (`package_edits`) and the
manifest those live in (`manifest`). The conformance suite's `prune rows` check holds the first two to what the layout
writes.
"""
from __future__ import annotations

PRUNE_ROWS = {
    "marked_files": (),
    "owned_files": {"postgres": ("adapters/event_store_postgres.txt", "adapters/checkpoint_store_postgres.txt")},
    "package_edits": {},
    "manifest": None,
}
