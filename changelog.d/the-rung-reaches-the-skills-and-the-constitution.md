MINOR

**Event sourcing is the default and the recommendation, and the prompt now says so.** Phase 15 split the
model from the log so that a product wanting one without the other could be generated at all. Nothing in
that split makes the two rungs equals at the question, and the prose had drifted into presenting them as
if it did. They are not equals, and the reason is not storage: the log is the contract between slices, so
a later slice reads an event without asking the service that wrote it and without the two being planned
together — which is what makes a slice independently deliverable — and a read model nobody thought of is
a replay away rather than a migration, which is what keeps a design reversible after it turns out wrong.

So `--write-model events` is stated as the recommendation wherever the question is asked: the axis's own
prompt and both option labels, `docs/guide/start-here.md`, and `docs/event-model/README.md`. `state` is
named for what it is for — a small supporting domain, a context that honestly is field updates, a service
whose past nobody will ask about — and is to be recorded with its reason, because a rung nobody justified
is the default. The default answer itself has not moved: Enter has always given `events`.

**A state-stored project stops receiving the event-sourcing skill.** `event-sourcing/SKILL.md`,
`event-modeling/SKILL.md` and `global-event-model/SKILL.md` each declared both `event-modelling` and
`event-sourcing`, and `serves()` is any-match, so all three shipped to every modelled project. The
sourcing skill declares `event-sourcing` alone now and the two modelling skills declare `event-modelling`
alone, so a project whose every service keeps current state gets the model and not a guide to rehydrating
a Decider from a log it has not got. A mixed project still gets all three: one service on the log is
enough for the project to carry the capability.

**The `event-modelling` constitution's Principle III is about the rung.** It was *Event-Sourced Core with
the Decider Pattern* and read as though every service were on that rung; it is *The Rung Is Recorded Per
Service, and Event Sourcing Is the Default*. The recommendation is stated as the recommendation, the
exception is named and has to carry a reason, and both rungs' rules are written out — including that a
slice on a state-stored service may name no `guard` and no `folds`, which is what `make check-model`
already refuses, so the constitution and the gate say one thing rather than two. Principle II's *a
command MUST check the event stream* reads *the write model*, which is the rule it always meant.

**The Foundational tasks branch on the rung.** T017, T019 and T022–T027 are the event-sourced rung's, and
each has a state-stored twin beside it: a repository port returning the version it read, a state table
whose `version` column is the concurrency control, an adapter turning a zero-row update into a conflict,
the same shared contract suite, and the same real-store race. T023's twin is the one that is not a
mirror — there is no append-only trigger on a table updated in place, and what goes in its place is the
outbox write in the same transaction as the state write, because the events a state-stored service raises
are lost otherwise on exactly the failure that matters. The plan template names the rung in its own field
rather than assuming it in *Storage*.

**And the modelling skill writes a role catalogue.** `docs/event-model/actors.yaml`, in Phase 1, for
every project: each human role and system actor with what it does and — the part nothing else records —
what it **cannot** do. A slice's `actor` says who acts; there was nowhere to say who may not, and a
negative permission is the first thing both a security pass and an access classification ask for.

**Catch-up:** `slipwai migrate` rewrites the constitution template and the presets. A project whose every
service is event-sourced keeps every obligation it had, with Principle III saying more than it did; one
with a state-stored service gains the rules that service was always subject to and nothing had written
down.
