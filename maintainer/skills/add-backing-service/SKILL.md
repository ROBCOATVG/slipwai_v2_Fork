---
name: add-backing-service
description: Add an answer to an axis — a second event store, another OIDC issuer — across the catalogue, the backends that implement it and the targets that provision it. Use when adding infrastructure a project can choose, not a language.
---

# Adding a backing service

An **axis** is one role asked as one question. There are five:

| Axis | The question |
| --- | --- |
| `write-model` | How a service records a write — the rung, and not infrastructure at all |
| `persistence` | How a service keeps its data |
| `http` | What accepts inbound HTTP — inferred from the backend, never asked |
| `auth` | Who authenticates staff |
| `users` | Who authenticates the product's users |

An option is an **answer to one of them**. You are adding an option, not an axis: the set of axes is fixed
in `catalog.json`, and adding one is a change to what a project is, which is a plan conversation.

Four of the five are infrastructure, and this skill is about those. `write-model` is the odd one: its
answers own no files, need no container and provision nothing, because the rung is a reading of a
service's write side rather than a thing to install. Nothing below applies to it.

## The axis names a role, never a product and never a protocol

This is the rule the whole design rests on. `postgres` and `keycloak` stop being alternatives on one menu
because they answer unrelated questions. Every `auth` answer is an OIDC issuer, which is exactly why that
axis is not called `oidc`: naming the protocol would have made a second OIDC issuer look like a different
kind of thing.

If your option does not answer one of the infrastructure questions above as a *role*, you have not got an option —
you have got something that wants its own axis, or that is not infrastructure.

## Four places it has to appear, and they are checked against each other

1. **`catalog.json`** — the option under its axis, with the backends that implement it, the targets it is
   offered under, and the feature that owns its files.
2. **Each backend that implements it** — in that language package, not here. A backend that lists an
   option it has no files for is the first thing the conformance suite catches.
3. **Each target that provisions it** — the stack that creates the real thing, and the prune row that
   removes it when a project chose otherwise.
4. **The local backing service** — what `docker compose` starts so a project runs with no cloud at all.

`validate_axes` holds all four together: an option no backend implements is invisible, and a default that
resolves to nothing for a backend that could have been given something is refused.

## The absent option is not a special case

Every axis has one — `none`, `memory` — and it is an option like any other, offered wherever a project can
do without. A target may *require* an axis, which is what `aws` does with `http`: a deploy of nothing is
not a deploy.

## The gate

```sh
make verify
```

`catalog_checks` and `axes` refuse a catalogue that cannot produce a working project, before any generation
rather than half-way through one.

## The mistake worth naming

**Adding the option and not the prune row.** The project generates, the gate is green, and every project
that chose something else carries files for a service it does not have — which nobody notices until
somebody reads them and believes them.
