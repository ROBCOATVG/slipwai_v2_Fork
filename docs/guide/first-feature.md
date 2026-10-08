# Your first feature

**Five minutes from a green gate to one slice demoed.** You have a repository and `make verify` passes;
this page is one feature, from a sentence you type to a working thing you watch a person accept.

The commands with a slash — `/speckit-specify`, `/chart`, `/drive` — are run inside your coding agent, not
in the shell. `./init` installed them.

**The short route is one command.** `/drive` walks the whole ladder below, enters at the first stage whose
artefact is missing, and runs that one and every stage after it. So you can type `/drive booking` now and
read the rest of this page as a description of what it is doing. The steps are shown separately here
because the first time through you want to see each artefact appear, and because three of the stages stop
for you.

---

## 1. Say what you are building

```
/speckit-specify  Guests book a table. A guest picks a time, we hold it, and the
                  restaurant sees it on tonight's list.
```

This writes `specs/booking/spec.md` — the product, in the language of the people who want it, with no
technology in it. Then:

```
/gaps
```

which reads the specification back and asks what it did not say. Who cancels a booking? What happens when
two guests take the last table? Answer them now, in the specification, because every one of them becomes a
slice later and a question answered here costs a sentence.

## 2. Model it

```
model this feature using skills/event-modeling/SKILL.md
```

Modelling is a skill rather than a command, because it is a conversation: you and the agent name the
commands, events and read models together. On the event-modelling profile it writes
`docs/event-model/model.yaml`: the commands somebody issues, the events that are the record of what happened, the read models the screens are built from, and which slice
each belongs to. One file, and everything downstream is rendered from it.

```console
$ make model
  wrote docs/event-model/model.svg
  wrote docs/event-model/slices/BOK-01.mmd
  wrote docs/event-model/model.html
  wrote README.md (event-model block)

model: 3 slices rendered. Open docs/event-model/model.html to browse it.
```

Open it. You get the timeline with a swimlane per context, each slice as a vertical stripe through it, and
every command, event and read model in its place:

![An event model with its timeline and swimlanes](../captures/event-model.png)

## 3. Chart the fairways

A **fairway** is a lane of work that one worker owns at a time; a **mark** is a typed contract — an event,
a read model, a route — that one fairway sets and others steer by. The **chart** names them, and it is
written before the work is cut up, because how you cut the work up depends on it.

On the event profile you do not write the chart. The model already says each slice's context, the events
it produces and what it reads, so the chart is rendered:

```console
$ make chart
chart: specs/booking/chart.yaml written from the model — 2 fairways, 2 marks, 3 slices
$ make check-chart
check-chart: 1 chart(s), 2 marks, one setter each, every slice in a capability
```

On the standard profile there is no such artefact, so `/chart` writes it with a person present. Either way
`make check-chart` holds it afterwards, and it refuses the two mistakes that cost the most: a mark nobody
typed, and a mark two slices both set.

**One setter per mark.** That rule is the whole reason the rest of this works. If exactly one fairway sets
`BookingHeld`, then everyone else can be told the moment it exists and can start — without waiting for a
branch to merge, and without a second definition of it appearing anywhere.

## 4. Split it

```
/story-splitting
```

One feature becomes slices, each a thin vertical cut that is demoable on its own, and each one writes its
own row into the chart: the fairway it belongs to, the capability it is part of, the marks it sets, the
marks it steers by.

```console
$ python3 scripts/agents/clearance.py
clearance: 1 of 3 slices cleared in booking
  BOK-01
```

**Cleared** means every mark this slice steers by has been set. Nothing has been set yet, so only the slice
that waits for nothing may start. A slice that is not cleared names what it is waiting for and who is
setting it, so "blocked" is never a mood — it is a mark with an owner.

## 5. Drive one

```
/drive BOK-01
```

This is the ladder: principles, specification, mock-ups approved one at a time, model, chart, split,
example map, implementation under TDD, the review and refactor stage, both gates, and a **demo** — an
actor-visible run of the thing, stopped in front of a person.

You watch it. At the demo stop it shows you what a guest would see and waits:

```
demo of BOK-01 — a guest holds 19:30 for four

  POST /bookings  { "at": "19:30", "covers": 4 }  →  201  held until 19:45
  the restaurant's list now shows it

accept this? [y/n/notes]
```

Say yes and the line goes in the log. Say no with notes and they go back into the slice.

```console
$ slipwai fleet booking
booking: the last 5 line(s) its captain wrote
  2026-10-08T09:14:48Z  claimed BOK-01
  2026-10-08T09:14:48Z  set BookingHeld — BOK-01
  2026-10-08T09:14:49Z  still going, 42k spent
  2026-10-08T09:14:49Z  demo of BOK-01: accepted
  2026-10-08T09:14:50Z  asked to merge: merge slice/BOK-01 into trunk after the full gate
```

The timestamps are that run's; yours will be your own.

**That is the fifteen minutes.** One slice, specified, modelled, charted, built, and accepted by a person
who watched it work.

---

## The one thing worth understanding before you go further

Look at the second line of that log. `set BookingHeld` was written when the slice **started**, in its own
worktree, before anything merged. Run clearance again and the slice in the other fairway that steers by
`BookingHeld` is now cleared:

```console
$ python3 scripts/agents/clearance.py
clearance: 3 of 3 slices cleared in booking
  AVA-01
  BOK-01
  BOK-02
```

One line in a log, and two more slices may start. **Nothing merged.** A second fairway can start on the
strength of a contract that exists and has one owner, which is why two people — or two agents — are not
queueing behind each other's branches. That is the claim
version 2 is built on, and the next page is what it looks like with more than one of you.

## Next

→ **[A second person joins](a-second-person.md)** — fairways, berths, and the board that shows both.

Other pages: [start here](start-here.md) · [let it sail](let-it-sail.md) ·
[bring an existing codebase](adopt.md) · [the vocabulary](../../GLOSSARY.md)
