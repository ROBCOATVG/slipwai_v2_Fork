---
name: add-language
description: Publish a slipwai language package — a family, its first backend, and the protocol members the registry asks. Use when adding support for a language slipwai cannot generate yet.
---

# Adding a language

A language is a **package**: its own repository, its own release, installed from the chandlery. The keel
ships none, so nothing here touches this repository — you are writing something that stands beside it.

## What you are actually providing

The keel knows how to write a project. It does not know what a Go project looks like. A language package
answers that, one member at a time, and the registry asks the questions:

- a **family** — the language, as a person names it: `go`, `python`, `rust`;
- one or more **backends** — a family plus the framework that owns startup: `go-gin`, `java-quarkus`. A
  family with one backend and no framework is fine;
- for each backend, what it answers on each **axis** the catalogue declares — where events live, what
  accepts HTTP, who authenticates — and which **targets** it can be deployed to.

Read `docs/backend-protocol.md` in the keel for the member table. It lists every member at once on purpose:
a member that appeared later would be a contract that moved under somebody.

## Start it

```sh
slipwai package new rust --kind language
cd rust
```

That writes a package that already loads: `language.json` declaring the keel schema *this* copy speaks, a
`VERSION`, the Python module the loader imports, a `Makefile` with the three targets, and CI that calls the
keel's reusable workflow. Every decision you have to make is a `TODO` in it.

## Fill it in, smallest first

1. **One backend, no axes, target `none`.** Get `slipwai package check .` to pass with a backend that
   generates a project that builds and whose tests run. Everything else is additive.
2. **`slipwai generate --backend rust` into a scratch directory, and run its `make verify`.** This is the
   only thing that tells you whether your answers produce a project rather than a plausible-looking tree.
3. **Then one axis at a time.** Each answer is files under your package's `assets/`, and the pruner takes
   out what a project did not choose. A backend that answers an axis it has no files for is the failure
   the conformance suite catches first.
4. **Then a target.** A backend that declares `aws` is promising its skeleton deploys there.

## What the suite is for

```sh
make check          # slipwai package check . — every required member, both profiles, every target
```

It generates projects and holds each to its own native gate. **It is slow and it is the point**: a language
package's whole job is that what it generates works, and nothing short of generating it says so.

The generated-variant matrix is opt-in, because it builds images and starts containers:

```sh
gh workflow run package.yml -R <you>/<repo> -f matrix=true
```

## Publishing

```sh
make release                              # the file, its digest, its index entry under dist/
make register CHANNEL=../slipwai-index    # both, into a channel checkout, and its index rebuilt
```

Then a pull request to that channel, which CI holds to `slipwai channel check`. A name belongs to its
first publisher, and a release is immutable once anybody has installed it.

## The two mistakes worth naming

**Answering a member with what a framework's tutorial does.** The generated project is somebody's
production repository on day two. If the tutorial puts the database URL in the source, your package should
not.

**Pinning nothing.** A package that resolves "latest" at generation makes two projects generated a week
apart different projects, and the difference surfaces as a failure in the second one that nobody changed.
