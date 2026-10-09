MINOR

**The page a reader starts on now shows the two questions it always meant to ask, and says which of them
cannot be walked back.** `docs/guide/start-here.md` showed one interview with one storage question on it —
`Event store` — under a profile prompt whose own paragraph said *the first question is the one that
matters, and it is the only one that is hard to undo.* That was true while choosing Event Modeling chose
the log with it. It is not true now: `Use Event Modeling?` decides whether the workflow is drawn before it
is built and can be answered later, and `Write model` is the storage decision, asked per service, and the
one that cannot be reversed. The transcript shows both questions with the words the interview actually
prints, and the paragraph underneath names the irreversible one.

**A package built before the rung was an axis is read onto the rung it was built for.** Renaming
`event-store` to `persistence` was only half the courtesy. `write-model` has `state` as its `absent`, and
an axis no loaded backend answers falls to its absent — so a language package that knew only `event-store`
would have gone on shipping event-store adapters while every project generated with it recorded
`eventSourced: false`. It is now read as answering `write-model: events`, and only that rung; the
state-stored rows are what a package adds when it is rebuilt on the protocol that has them.

**`/run` describes the store the service was actually given.** Its *Seed it* paragraph was keyed on the
store alone, so a state-stored Postgres service was told to migrate its event store and a state-stored
SQLite one was told that deleting the file deletes the entire truth of the system. It is keyed on the store
*and* the rung now: two services on one store and one rung still say it once, two services on one store and
two rungs say it twice, and `make migrate`'s comment names no rung, because it is one target applying
whichever migrations the rung put there. The `sqlite` block of `.env.example`, `/ready`'s readiness line
and the integration-test comment in the Makefile read the same way.

**Catch-up:** `slipwai migrate` rewrites these pages. A project whose every service is event-sourced gets
back what it had, bar the sentences that stopped being true when the profile stopped deciding the rung. The
`persistence` prompt's SQLite and Postgres labels say what each store is on each rung, and
`assets/targets/{aws,azure}/service/main.tf` stop telling a reader to run `./init --event-store memory`, a
flag that was renamed with the axis.
