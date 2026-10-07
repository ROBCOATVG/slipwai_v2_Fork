---
name: add-framework
description: Add a framework to a language family somebody already published — a second backend in the same family, held to that family's VERSION. Use when the language exists and the framework does not.
---

# Adding a framework

A framework is a **backend in a family somebody else already published**. `java-quarkus` beside
`java-spring`, `python-litestar` beside `python-fastapi`. It is a package of its own, so it releases on its
own day, and it is not a fork of the family's package.

Read `add-language` first if the family does not exist yet. Everything there applies; this is the narrower
case and it has three rules of its own.

## It requires its family, and says so

```json
{
  "name": "java-quarkus",
  "family": "java",
  "requires": { "java": ">=2.0,<3" }
}
```

`requires` is what makes it a framework rather than a family claiming a name. The loader refuses it where
the family is not installed, names what is missing, and installs the family with it when you ask for the
framework by name — so a person types one thing.

## It is held to the family's VERSION

Not to the family's `core` range: to the version actually installed. The family owns the layout, the
toolchain and the prune rows; a framework that drifted from them would generate a project where half the
files are one package's idea and half the other's. When the family releases, you release.

## It declares one backend and no family

```json
{ "backends": { "java-quarkus": { "framework": "quarkus", "label": "Quarkus — …" } } }
```

Its `LANGUAGE` declares the same one backend and **no** `Family`. A framework package that declared its
family would be two packages claiming `java`, and the merge refuses that by name.

## What you actually write

Only what differs. The family answers the toolchain, the layout, the lint and the test runner; you answer
what startup looks like, what the HTTP axis resolves to, and the files your framework needs under your own
`assets/`. A framework package that is as large as its family is a framework package that has copied it.

```sh
slipwai package new java-quarkus --kind language    # then add `requires` by hand; the scaffold writes a family
make check
```

## The mistake worth naming

**Answering an axis the family already answers, differently.** Two backends in one family that store events
two ways is two projects a team cannot move between. If the family's answer is wrong for your framework,
that is a conversation with the family's publisher, not a second answer.
