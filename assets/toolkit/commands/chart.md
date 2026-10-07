---
description: Name this feature's fairways and type the contracts every one of them steers by, before the work is split
argument-hint: [feature]
---

# Chart

Run this once per feature, after the mock-up review and **before** the split. A person is present.

This is the standard profile's answer to what the event model is on the other one. The event profile has a
single artefact that names each slice's context and service, types its events, and says what it reads, so
its chart is rendered with `make chart` and never written. This profile has no such artefact, so the chart
is written here, and `make check-chart` holds it afterwards either way.

The file is `specs/<feature>/chart.yaml`.

## It is written in two passes, and nothing is claimed until both are done

The chart names fairways, marks and slices, and the slices do not exist yet when this stage runs. So:

- **This stage writes `fairways` and `marks`.** Those are the decisions that have to be taken before the
  work is cut up, because the way the work is cut up depends on them.
- **The split writes `slices`.** For each slice it has cut: the fairway it belongs to, the capability it is
  part of, the marks it sets and the marks it steers by.

"Before the split" means no slice is claimed until the whole chart is there. Both passes are before that,
and `check-chart` is what says the chart is whole.

## Pass one, here: the fairways

A **fairway** is one bounded context's slices, with one holder. Ask, and write down:

1. **Which bounded contexts does this feature touch?** A bounded context is a part of the product with its
   own vocabulary, where the same word means something different from what it means next door. Read the
   specification's vocabulary the way `skills/domain-driven-design/resources/bounded-contexts.md` describes
   under *The Language Test*: the same word meaning two things, qualifiers creeping in like "billing
   customer" and "shipping customer", rules that change for different reasons.
2. **Which service holds each one?** From `project.json`'s `deployables`. Record it on the service too, with
   `slipwai describe-service <name> --context <context>`, once per context.
3. **What does each fairway own?** The paths no other fairway writes. A service holding one context owns all
   of it; a service holding several gives each context its own directory.

## Pass one, here: the marks

A **mark** is one published contract another slice steers by. Four kinds, each typed in a file the mark
names, because a contract a reader cannot open is not a contract:

| Kind | What it is | What it names |
|---|---|---|
| `event` | Something that happened, which other slices fold | a JSON Schema |
| `schema` | A shape published for others to read or write | a JSON Schema |
| `route` | An HTTP operation this feature publishes | an OpenAPI operation, as `contracts/openapi.yaml#/paths/...` |
| `port` | A named capability another context calls through | two JSON Schemas, its inputs and its outputs |

Write the file as well as the entry. A mark naming a file nobody wrote is a promise that gets discovered at
the far end, by the fairway that believed it, and `check-chart` refuses it here instead.

**A mark is set once and never moved.** That is why this stage is a stop and not a form: every one of these
is a commitment another fairway builds against, and withdrawing one later is taken out of whoever steered
by it. `check-chart` refuses a deletion; an amendment is additive and goes in `fairways/<name>/chart.d/`.

## Pass two, at the split: the slices

The split fills in, per slice:

- `fairway` — which one of the fairways above it belongs to.
- `capability` — the chunk of work this slice is part of, the thing a person's demo is of. A capability is
  usually several slices. It is a product judgement and this is the moment to take it, because a person is
  here and will not reliably be later. `check-chart` refuses a slice without one.
- `sets` — the marks this slice publishes, from the `marks` block. One mark has exactly one setter.
- `steers_by` — the marks it builds against, which some other slice sets.

## The shape

```yaml
v: 1
feature: ordering
fairways:
  ordering: {context: ordering, service: apps/orders, owns: [apps/orders/**]}
  billing:  {context: billing,  service: apps/billing, owns: [apps/billing/**]}
marks:
  OrderPlaced:  {kind: event, schema: contracts/events/OrderPlaced.json}
  POST /orders: {kind: route, operation: contracts/openapi.yaml#/paths/~1orders/post}
  PricingPort:  {kind: port,  inputs: contracts/ports/PricingPort.in.json, outputs: contracts/ports/PricingPort.out.json}
slices:
  ORD-01: {fairway: ordering, capability: place-an-order, sets: [OrderPlaced, POST /orders], steers_by: []}
  BIL-01: {fairway: billing,  capability: bill-an-order,  sets: [InvoiceRaised], steers_by: [OrderPlaced]}
```

## Facing a person

Name everything twice the first time it comes up: the slipwai word and the ordinary one. "A fairway, which
is this bounded context's slices." "A mark, which is a contract another part of the work builds against."
"A capability, which is the chunk of work we would demo in one go." Nobody should have to learn a
vocabulary to answer a question about their own product.

## When it is done

`make check-chart` passes. That means every mark is typed and its file is in the tree, every mark steered by
has a setter, no mark has two, nothing has been withdrawn, and every slice names its capability.
