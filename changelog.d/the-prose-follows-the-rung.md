MINOR

**Every generated page now describes the rung each service is actually on, and a mixed project's pages
carry both.** The last change made the keel *give* each service the files its write model names. This is the
other half: what the pages then say, which is the half a person and an agent act on. A service handed a
repository port and a versioned state table was no better off while `AGENTS.md` told whoever worked in it
that the event store is a driven port, `docs/architecture.md` promised a replay, and
`docs/event-modeling-to-code.md` showed one table — the first service's — for the whole project.

`docs/event-modeling-to-code.md` is now a section per service. The event-sourced one keeps the table it
had, with a Decider row made explicit; the state-stored one says a load through the repository port, a pure
decide over current state and a save at the version that was read, gives `stream` as the row one
transaction locks, and refuses `guard` and `folds` by name with the reason, so the first slice written
against that service finds out here rather than at a gate. `README.md`, `AGENTS.md`,
`docs/architecture.md`, `docs/whats-included.md`, `docs/gates.md`, the `/gaps`, `/adversary` and
`/constitution-coverage` command pages, `/sail`'s event-model rung and the pull-request template all read
the same way, and the store's own sections say which race their project's Postgres can actually lose — a
`(stream_id, version)` constraint on the log, a save at the version the state was read at on a row.

**Catch-up:** `slipwai migrate` rewrites these pages, and a project whose services are all event-sourced —
which is every modelled project generated before `write-model` existed — gets back what it had, bar two
sentences that stopped being true when the profile stopped deciding the rung. A project on the standard
profile gains nothing here: it has no model and therefore none of these pages.
