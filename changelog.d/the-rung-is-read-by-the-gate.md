MINOR

**`make check-model` reads the rung the slice's service is on, so a state-stored service is held to the
write model it actually has.** The gate had one reading of a slice's write side, and it was the
event-sourced one: a planned state change named `stream` *or* `guard`, `folds` was the history a Decider
rehydrates from, and a `live` state-view owed a `liveBudget`. On a service that keeps current state, two of
those describe machinery it was never given and one bounds a fold it does not do. The first slice written
against such a service found that out at a gate, or did not find it out at all.

Both halves of the gate now read `eventSourced` off `project.json` per deployable — `check.py`, which
`make check-model` runs, and `validate.ts`, which the render pipeline runs — and give identical verdicts:

- **`stream` is required at `planned` on both rungs**, and means the row or aggregate one transaction
  locks, with its version, where it meant the stream an append carries an expected version of.
- **`guard` is refused by name** (`guard-needs-a-log`): a boundary drawn over a tag query needs a log to
  query, and the refusal names `stream` as what this service's boundary is instead.
- **`folds` is refused by name** (`folds-need-a-log`): there is nothing to replay, and the refusal says
  what the decision does instead — loads what the service holds, decides, saves at the version it read.
- **`liveBudget` is not asked**, there being no fold to bound. `materialisation` keeps all three words.
- `model-matches-code` is unchanged. An event is a file on either rung.

A service the manifest says nothing about reads as state-stored, which is the `write-model` axis's own
`absent` and the honest reading of a service nobody vouched for.

**Two naming rules, on either rung.** `event-is-not-crud` refuses `Created`, `Updated`, `Deleted`,
`Changed` and `Modified` as the verb of an event — it names what the table did, not what happened, which
Dudycz calls *property sourcing* and which is the way a reverse-engineered model most often goes wrong.
The refusal proposes the shape of a better name. A frame that honestly is a field update — a CMS page, a
setting — says `crud: true` with a `because`, and the `because` is required, because unstated it is the
exemption everything gets. `event-is-not-negative` refuses `OrderNotShipped` for the failure underneath it
(`ShipmentFailed`, with a `reason` attribute), and is written to leave `UserNotified`, `AccountUnlocked`
and `ItemUnpacked` alone. The Good / Bad / Why tables behind both are in
`skills/event-modeling/references/naming.md`.

**The rung stays invisible to the division of work.** `chart.py` names none of the fields that move, and
`tests/test_rung_gate.py` holds it to that: the rendered chart of a two-slice model is the same whichever
rung either slice is on. `docs/event-model/README.md` gains the table saying which three fields those are.

**Catch-up:** a project whose every service is event-sourced is held to exactly what it was, bar the two
naming rules — which are new on both rungs, and which an existing model may fail. A failing name is a
rename of an event the model has, and on the event-sourced rung an event already raised keeps the name it
was raised under: the new name goes on new events.
