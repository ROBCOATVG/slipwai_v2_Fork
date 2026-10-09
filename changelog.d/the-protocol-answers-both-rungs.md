MINOR

**A language now answers both rungs, and the suite makes it prove it.** The keel has been giving a
state-stored service the rows under a backend's `state` key since the rung became an axis; what was missing
was the other half — the page that says what a backend owes, and the check that says when it has not paid.

- `write_side_files` and `read_side_files` are contracted with their `state` block: the repository port,
  its adapters per store, and the migration for a versioned state table, keyed by the same features as the
  rows above them, because the rung does not settle which store was chosen.
- `event_store_directory` is now `persistence_directory`. The store on the state rung holds current state,
  so the old name sent a reader of the generated prose looking for a log. Both names are read, the new one
  first, until 2.1 — a package answering only the old one loads, generates and passes its suite.
- `event_model_paths` answers `repository` beside `events`, `domain`, `usecase` and `test`: the port a
  state-stored service loads and saves through. Unanswered, the keel fills it from the decision's own path
  for one MINOR rather than leaving a hole in `docs/event-modeling-to-code.md`.
- `service_files`'s `event` parameter is deprecated. It says the project is on the modelled profile, which
  was all a backend had to go on when Event Modeling and event sourcing were one answer; the write model is
  per service and is `selection.option("write-model")`. The signature does not change.

`slipwai package check` generates the richest profile once more at `--write-model state`, so a `state` block
naming an asset the package never committed is a finding rather than a project with a hole in it, and names
the gap per store where a backend has written no block at all.

**Catch-up:** nothing to do in a project. For a language: rename the one answer, add the `state` rows and the
`repository` path, and run the suite — it names each of the three if you miss one.
