---
description: Turn one slice into concrete rules, examples, and the questions nobody here can answer
argument-hint: [slice-id]
---

# Example map

Every slice begins here, on either profile. A slice with no examples has nothing for a test to be about and
nothing for the hand to walk at its demo, and the stage that follows this one will say so rather than
guessing. Work with four items: the story, the rules, a concrete example per rule, and the questions this
session cannot answer.

**Never invent a fact to close a question.** An event, a field, a command, a stream identity, a route, a
policy, a price, a limit: if the answer is not in the artefacts named below, it goes under `## Questions`
and into the inbox for a person. A map that reads complete because a gap was filled from context is worse
than one that is visibly short, because only one of the two gets asked about.

## Where the inputs come from, which is the only thing the two profiles differ on

**On the event-modelling profile**, the slice is already modelled, so this stage *derives* rather than
invents. Read the slice in `docs/event-model/model.yaml` with `skills/event-modeling/SKILL.md`: its
commands, events, read models and actors are the vocabulary, and its `gwt` already points at the
Given/When/Then this map is the long form of. Write the agreed scenarios, link their path from the slice's
`gwt` field, and keep the Event Modeling and event-sourcing contract as one unit. A rule here is a rule the
model already implies; finding one it does not is a finding, and it goes to the model before it comes back
here.

**On the standard profile**, nothing has written the examples yet, and this stage writes them from scratch.
Read two things. The slice's story and acceptance criteria in `specs/<feature>/spec.md` say what the actor
is trying to do. The slice's row in `specs/<feature>/chart.yaml` says what it publishes: the routes,
schemas and ports it sets, and the marks it steers by, each typed and each pointing at a file. The marks
are the contract the examples are written against, so an example that asserts a field no mark declares is
an example about something this slice does not own. Where the chart names a mark another slice sets, write
the example against that mark's schema rather than against a guess at the other slice's behaviour.

Everything from here is the same on both.

## One shape, whichever profile wrote it

Both profiles write `specs/<feature>/slices/<id>/examples.md`, and the stages after this one read that one
path and that one shape. A numbered rule, its examples beneath it, each example on one line that a test can
be named after.

## Rules own their examples

Write the map as numbered rules, `R1`…`Rn`, each heading carrying its own examples and their scenarios —
not every rule in one section and every scenario in another. The rule is the unit of a RED-GREEN-REFACTOR
increment (Principle V), so the grouping here is the boundary the tasks are cut on and the verdicts cite:
without a stated grouping there is no agreed rule boundary, and whoever writes the tasks invents one.

```markdown
## Story
Buyer places an order for the items in their cart and gets a confirmation.

## R1 — An order cannot be placed from an empty cart
- empty cart → rejected, nothing recorded

### Scenario: Cannot place order with empty cart (CS-1)
**Given** CartCreated { cartId: "CART-001" } · **When** PlaceOrder { cartId: "CART-001" } ·
**Then** error "cart CART-001 contains no items", no events

## R2 — The order total is the sum of the cart's line totals at the moment it is placed
- 2 x £29.99 → order total £59.98, and later price changes do not move it

### Scenario: Successfully place an order (CS-2)
…

## Questions
- Does a cart expire, and if so does expiry reject or silently empty it? → for the product owner
```

On the standard profile the scenario block is the same shape without the event vocabulary: the **Given** is
the state the request arrives into, the **When** is the call the actor makes, and the **Then** is what comes
back and what changed. One example per rule is the floor, not the target — a rule worth stating usually has
a boundary on each side of it.

Never renumber a rule once a task or a verdict cites it: a new rule takes the next number, and a dropped one
keeps its number with a line saying it was dropped and why. Do not retrofit this shape onto a map that is
already agreed and implemented — the format applies from the next slice mapped, and an older map is read
as it stands.

## An empty map stops the slice

`/drive` will not run its implementation rung against a slice whose `examples.md` has no example under any
rule. That is a refusal and not a warning, because the alternative is a slice implemented against whatever
the implementing session inferred, and then demoed against the same inference. If the examples cannot be
written, the reason is a product question, and a product question is a stop with a name rather than an
empty file: put it under `## Questions`, send it to the inbox, and say which rule is waiting on it.
