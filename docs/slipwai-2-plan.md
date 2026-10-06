# Slipwai 2: the plan

This document is the plan for version 2 of slipwai. Slipwai is a tool that generates a product repository
and then runs a delivery loop in it with coding agents. Say the name as "slipway".

The plan was written on 2026-10-06 and revised the same day. Its sources are this fork, the experiment in the
`slipwai-cruise-2` checkout, GitHub issues #26, #30, #32, #27 and #29 on `ROBCOATVG/slipwai`, and an
unposted write-up of a five-berth run on a product called MANDA.

The document has nine sections:

1. The words this plan uses.
2. Where things stand today.
3. What the first attempt taught.
4. The five themes of version 2.
5. The delivery loop, drawn for both profiles.
6. How a project built on version 1 moves to version 2.
7. The order of work.
8. The rules for doing the work.
9. Decisions taken, and decisions still open.

## 1. The words this plan uses

Every name in slipwai comes from the slipway and the harbour. This section is the glossary for the rest of the
document. Read it first. Later sections use these words without explaining them again.

Nothing in version 2 is called a workstation, a workstream, a lane or a runner. Where this document describes
version 1, it uses version 1's own names and says so.

| Word | Meaning | Version 1 name, where one existed |
|---|---|---|
| **Keel** | The core of slipwai: the questions it asks, the code that writes a project, the toolkit, the adoption path, and the delivery loop. Every package attaches to the keel | "core", "core driver" |
| **Language** | A package that holds every answer for one language family, with a thin framework package for each framework of that family. Example: `java` is a family, `java-quarkus` is a framework of it | Same word |
| **Extension** | A package of developer tooling that a project chooses to add. Example: `codegraph` | Same word |
| **Chandlery** | The index of packages that slipwai can install: languages and extensions, each with a version, a compatibility range, a checksum and a publisher. `slipwai chandlery` lists it. `slipwai install <name>` installs from it | "marketplace", "index" |
| **Slice** | One unit of product work that an actor can use when it is done. Unchanged from version 1 | Same word |
| **Fairway** | One bounded context's slices, in split order, with one release flag and one holder. The fairway is the unit of scope, of ownership and of release. Several fairways run side by side into the same harbour. A vessel keeps to its own fairway | "value stream", "workstream" |
| **Berth** | The provisioned place where one captain works: a git worktree, environment variables, an allocated block of ports, a database, and scratch directories. `slipwai berth add`, `slipwai berth status` and `slipwai berth remove` manage berths | "workstation", "lane" |
| **Captain** | The outer loop for one fairway, in both modes. The captain reads the logs, works out the state of the fairway from the logs and trunk, gives clearance, claims a slice, dispatches an iteration, enforces every stage boundary, and appends to the deck log. There is one captain per fairway. Under `/drive` the captain brings every question and demo to the person. Under `/cruise` the skipper answers and the hand demos | "runner", `cruise.py run` |
| **Harbourmaster** | The part the captains share. It allocates berths, keeps the harbour log, draws the fleet board, holds the flags, and answers the telegraph. It is not a merge queue | "integrator" |
| **Deck log** | A fairway's own append-only log, committed with the work. Its lines are: claimed, mark set, demo, accepted, merged, decision, told, read, heartbeat, stowed, parked | "stream log" |
| **Harbour log** | The one append-only log that every fairway reads. Its lines are: mark set, flag hoisted, berth allocated, fires banked, park for a person | "cross-stream log" |
| **Chart** | The contracts, written before the split. The chart names the fairways, the marks each slice sets, the marks each slice steers by, and the paths each fairway owns. On the event-modelling profile the chart is derived from the event model. On the standard profile a `/chart` stage writes it | "contract map", "streams manifest" |
| **Mark** | One published contract that another slice steers by: an event, a route, a schema or a port. A mark is set once and never moved. The files that hold marks only grow | "contract entry" |
| **Clearance** | The rule that lets a slice start. A slice has clearance when every mark it steers by has been set by a slice that is planned or implemented. A slice sets its own marks itself, as its first stage, in its own worktree | "consumption gate" (issue #32) |
| **Careen** | One hardening slice per fairway. It holds the findings below the severity bar and the work that stages stowed. It runs before the fairway's flag is hoisted. Its demo is: the findings are closed | "hardening slice" |
| **Stow** | What a stage does with its open work when it runs out of budget: it moves the work into the careen. Work is never dropped. A CRITICAL finding is never stowed | "backload" |
| **Telegraph** | The dial between speed and cost: the engine order telegraph on the bridge. A person rings it; the engine room answers by raising or lowering steam. Its positions are `full-ahead`, `half-ahead`, `slow-ahead`, `dead-slow` and `stop`. Each position sets, as a group, how many boilers are lit, how many delegates a captain may run at once, which model role each stage uses, and the bunker per slice and per day. `slipwai telegraph half-ahead` rings it. Each number underneath can also be set alone | "concurrency setting", "cost cap", "trim" |
| **Boiler** | One berth under steam. A lit boiler is a captain working. The telegraph says how many may be lit at once | "max concurrency" |
| **Bunker** | The coal store: the token budget, per slice and per day. Tokens are the coal. The pressure gauge on the fleet board shows the rate they burn at | "token budget", "cost cap" |
| **Bank the fires** | What the harbourmaster does when the bunker runs down faster than the telegraph position allows: optional stages stowed into the careen, fewer delegates, cheaper model roles, then one boiler put out. Each step is a line in the harbour log. A person stokes the fires back up | "throttle", "reef" |
| **Hoist, strike** | To hoist a flag is to turn a release flag on for real actors. To strike a flag is to remove it after it has been on everywhere for long enough. Only a person hoists | "turn on", "remove the flag" |
| **Slipway, sea trials, in service** | The three states of a product, recorded once in `project.json`. Slipway: no production yet. Sea trials: a production with a known set of pilot actors. In service: real actors. The release mode defaults from this state | "pre-launch", "beta", "GA" |
| **Release mode** | How dark a merge is. One of: open, keystone, flagged, promoted. Section 4, theme E, defines each | `release: flagged` |
| **Skipper, hand, bosun** | The three delegates inside one iteration. The skipper decides product questions. The hand runs the demo. The bosun works round a block. Unchanged from version 1 | Same words |
| **Fleet board** | Every view of the harbour, meaning the agents at work: the berth table, the slice graph by fairway, the swimlanes with cost, the event feed, the pressure gauge and the bunker, and the inbox. Every view is computed from the logs and from `git rev-list`. The fleet board keeps no state of its own. `slipwai fleet` prints it. `slipwai fleet watch` keeps it live. The harbourmaster also renders it as a page | "fleet view", "multi-lane status", "dashboard" |
| **Bridge** | One product's own dashboard, as distinct from the fleet board, which is the harbour's view of the agents. The bridge shows where the product is (slipway, sea trials, in service), the release mode, how far along each fairway is, which flags are hoisted and where, what is deployed to each environment, what is waiting on a person, and what the product has cost so far. `slipwai bridge` prints it. The harbourmaster renders it to the project's Pages site next to the event model | `/where-are-we`, the demo stop's progress board, the event-model page |
| **Drive, cruise** | `/drive` is the main mode: a person is present, the whole fleet fans out across fairways, and every product question, park and demo comes back to that person through the inbox. `/cruise` is the same fleet with nobody at the keyboard: the skipper answers the questions and the hand runs the demos. Nothing else differs | Same words, but in version 1 only `/cruise` fanned out across a product |
| **The ladder** | The ordered stages of `/drive`. Section 5 draws it | Same word |

Two version 1 terms appear in this document when it describes version 1:

- **The runner** is version 1's `scripts/agents/cruise.py`. It starts one iteration after another in a fresh
  session. The captain replaces it.
- **The integrator** is the one person who, in version 1's generated `workstations.md`, merges every accepted
  slice to `main`. Version 2 has no integrator.

## 2. Where things stand today

### The checkouts

| Checkout | What it is | State on 2026-10-06 |
|---|---|---|
| `slipwai_v2_Fork` | This repository, `github.com/ROBCOATVG/slipwai_v2_Fork`. It was a clone of upstream `main` | Cleared (see section 7, phase 0). Before the clearing it was 1.5.2.dev0 and identical to upstream |
| `slipwai-cruise-2` | The experiment. Slipwai 1.3.0 was adopted onto its own repository, and `/cruise` was run against issue #26 | 641 commits past 1.3.0. `VERSION` reads 2.0.0.dev0. Working tree clean. Last commit by the loop 2026-10-03. One commit by hand 2026-10-05 |
| `slipwai-workstreams` | One local commit on top of 1.5.2.dev0: the MINOR change for issue #30 | 18 files changed, 322 lines added, with tests. Not merged anywhere |
| Six package repositories | `luke-gee/slipwai-language-go`, `-python`, `-typescript`, `-java`, `-java-quarkus`, and `luke-gee/slipwai-language-template`. All private | Pinned as git submodules under `languages/` and `templates/language` in `slipwai-cruise-2` |

### What the experiment delivered

The experiment's own checkpoint file is stale, so this list comes from git, not from the checkpoint.

- 20 of 24 slices merged. Slices S01 to S19 have a row in the register. Slices S20 and S23 are merged through
  the branch `integ/iter19` with accepted demos, but they have no register row. Slice S21 has a gaps file only.
  Slices S22 and S24 were never started.
- The keel now loads languages as packages from the directory in `$SLIPWAI_LANGUAGES`. It merges each
  package's `language.json` into the catalogue. The catalogue's `schemaVersion` is now `"9.0"` and a package
  declares a compatibility range against it. The verbs `slipwai list`, `slipwai language list`, `slipwai language
  install`, `slipwai language upgrade` and `slipwai language remove` exist. `project.json` records
  `generator.languages`. `slipwai migrate` moves a 1.x project to 2.0. A conformance suite and a per-package test
  matrix exist. A list of 20 keel modules that a package may import is held by `check-structure`.
- 24 changelog fragments exist: 8 MAJOR, 3 MINOR, 13 PATCH. Together they describe a 2.0.0 release.
- The runner stopped at iteration 2. The stop file `cruise.stop` is empty, so no reason is recorded.
  Iterations 3 to 19 ran from interactive sessions. They wrote no run log, no stream and no line in
  `cruise-log.jsonl`. The checkpoint still says "iteration 2". This is why nobody could know the status without
  reading git.

### What the experiment lists as blocking 2.0.0

The file `specs/001-slipwai-2-language-addons/cruise-report.md` in `slipwai-cruise-2` lists these:

- The image probes for `java-quarkus` and `java-spring` never passed. Ten decisions (D25, D32, D36, D48, D54,
  D69, D78, D86, D94, D105) ruled them environmental again and again. They need one green run with real network
  access.
- The submodule `languages/java-spring` points at `slipwai-cruise-2` itself, pinned to the branch
  `slice/S10-java-spring`. The run could not create the real repository (decision D62).
- CI cannot load the `go` submodule. The edits are written in `ci-proposal.md`. They need a token and a person.
- The root CI matrix still generates every language's variants. The edit that retires it is in `ci-proposal.md`
  (slice S14, decision D100).
- `check-slice-scope` refused every path under `src/` and `tests/` for the whole run, because the factory's own
  `project.json` declares no deployable (decision D30). Every slice merged with that check red.
- 8 architecture decision records (ADRs) are at the status Proposed. About 105 of 125 decisions were never
  reviewed by a person.
- Slice S20 has five open tasks and a mutation run that stopped at 135 of 207 mutants. Slice S23 has eight open
  tasks, one of them handed back.

### The gate on the experiment

On 2026-10-06, `make verify` on `slipwai-cruise-2`'s `main` passed on this machine: every gate green, with
7 tests skipped. The run took longer than ten minutes because it builds the Java variants locally. The two image
probes listed above still need a run where they are not skipped.

### The salvage measurement

On 2026-10-06 a trial merge was run in a scratch clone. Nothing in any real checkout was touched. The merge
brought upstream's changes from 1.3.0 to 1.5.2 into `slipwai-cruise-2`'s `main`. Upstream changed 130 files.
35 of them conflict: `cli.py`, `scaffold.py`, `catalog.py`, `migrate.py`, `toolkit.py`, the three language
modules that became packages, `prune.py`, and some docs. That is about one day of work. The reverse, rebasing
641 commits onto upstream, is not worth attempting. Section 9 records that neither route was chosen.

## 3. What the first attempt taught

### Design decisions that held

Version 2 keeps these decisions from the experiment.

- **The keel owns the questions. A language owns its answers.** The `Registry` holds one object per backend,
  keyed by `Member` constants rather than strings. A framework inherits from its family. `None` is a valid
  answer; what matters is whether an answer is present. Before this change a new backend touched seventeen files
  in the keel. After it, a new backend is one package.
- **A family is a dependency. A framework is what gets installed.** This two-layer split matched what was
  already on disk.
- **Packages load from a directory, not from Python entry points.** A frozen executable cannot run `pip
  install` into itself. One directory loader serves the wheel, the executable and a checkout alike.
- **Compatibility is a range that the package declares.** It is not an equality test on `schemaVersion`.
- **The import surface is part of the schema.** A package may import exactly twenty keel modules.
  `check-structure` holds that list, by file and by line. This is what makes a change to the keel safe.
- **A package is either whole in its directory or not there.** Installation stages the files, checks the
  sha256, and renames the directory atomically.
- **Every refusal ends with the command that fixes it.** The idea is right. The cost is described below.
- **Conformance and the test matrix are exports of the keel that each package runs.** A package proves itself
  without the keel's CI.

### Design debts that version 2 pays down

- **The wording of refusals became the main source of complexity.** Decisions D116, D117, D122 and D124 are
  pages about what single error lines say. Slice S20 changed no behaviour and still took three quality rounds.
  Version 2 has one refusal shape. The shape is generated from the fault, and the fixing command is data.
- **The contract files also served as the specification.** They grew a Status column that slices changed.
  Version 2 writes the contracts first, freezes them, and keeps the specification separate.
- **Packages had no release tool** (decision D112). Releases were cut by hand. Version 2 ships a publish verb,
  or the package template carries a `make release` that mirrors the keel's.
- **Tables keyed by HTTP option stayed in the keel** (decision D39). A language that brings a new HTTP framework
  still edits the keel. Version 2 moves those tables behind the protocol.
- **Loading a package runs its Python code**, both at install and in the conformance probe. There is no sandbox.
  Version 2 states this up front as the trust model of the chandlery: an entry is signed, or it is not listed.

### Process findings

These findings matter more than the design ones. The evidence is in `benchmark.md`, `adversary-log.md`,
`decisions.md` and the cruise log in `slipwai-cruise-2`, and in the MANDA run.

| Finding | Evidence | What version 2 does |
|---|---|---|
| Mutation and conformance gaps were carried forward, not closed | 18 gaps moved from S08 to S09, 31 from S09 to S13, 46 from S12 to S13. Two whole slices (S13, S17) existed only to collect that debt | A slice does not merge with open gaps. If that makes the slice too big, the slice was too big |
| The adversary loop never converged | 129 findings over 21 rounds. 64 were LOW, most about wording. S20 still ended with 5 open LOWs | One adversary round per slice. Findings below a stated bar go to the careen. A demo verdict of `behaviour` is a defect in the specification, and is fixed there |
| Environment problems were decided ten times | The two Java image probes, decisions D25 to D105 | Prove the gate green in the target environment on day zero, or exclude the test once, in writing |
| Decisions outran review | 125 decisions, 105 unreviewed, 8 ADRs still Proposed | The captain holds a ceiling on unreviewed decisions and parks when the count passes it |
| Large architectural slices blew their budgets | S08 took 20 hours. S01 took 14 hours. S09 used 291 million input tokens. S02 took 2 hours 22 minutes and S18 took 31 minutes, and both were fine | Make every slice the size of S02. Never the size of S08 |
| Every merge was dark on a product that nobody used | `release: flagged` is absolute. MANDA ran five berths behind flags with no actor. A slice with nothing holding it back parked | A release mode per product state: open, keystone, flagged, promoted |
| Every increment paid for the full gate | One `make verify` runs lint, typecheck, structure and the whole test suite. The owner's own note in the experiment was "use full verify sparingly, it's heavy" | Fast checks per increment. The full gate once, before `main` |
| Integration was re-cut again and again | 18 `integ/*` branches for 19 iterations, with `a`, `b`, `c` retries | Merge to trunk per slice, dark according to the release mode. No integration branches. The two files that every slice touched become generated or split |
| The repository split happened mid-flight | S08 to S10 extracted six repositories while slices were running. `java-spring` is still a stub | The split is its own completed step. Push credentials are proven first |
| The factory tripped over itself when run on itself | `check-slice-scope` was red all run. `AGENTS.md` pointed at a script that did not exist. The code index was dead from iteration 2 | Declare the factory as a deployable in its own `project.json`. Verify its own tooling on itself before any run |
| Instructions written in command prose did not hold under load | Rebase at start, close browser sessions, bound every wait, read the inbox between stages. All were documented. All failed in MANDA | Anything the ladder relies on every time belongs to the captain, not to the agent's memory |
| The runner was the only source of status, and it died | 17 of 19 iterations have no log. In MANDA, `model.yaml` said `planned` for eight slices that were built and merged | The log is the control plane. No log line means no progress |
| Shared ids collided across berths | 54 renumbering commits in 20 hours. One renumber touched 91 citations | Every id carries its fairway. Every append-only file is per fairway. Feature-level views are rendered, never edited |

## 4. The five themes of version 2

### Theme A. The keel and the chandlery

**Goal.** The keel is small and fast to verify. Languages, and then extensions, are packages found in the
chandlery, installed into slipwai, versioned and released on their own. Adding one touches nothing in the keel.

**What already exists.** From the experiment: the registry, the loader, the index contract, the verbs, the
conformance suite, the test matrix, the template, and six packages. The design is in
`specs/001-slipwai-2-language-addons/contracts/*.md` in `slipwai-cruise-2`.

**How the pieces link.** The figure shows the four parts and what crosses each boundary: a product repository,
the keel, the chandlery, and the packages, with the publishers below them. Nothing crosses the package boundary
except data and a protocol. The keel never names a language.

![How packages, the chandlery, the keel and a product repository link](images/ecosystem.svg)

**What version 2 builds.**

1. The keel is brought back one module at a time, in the order of the import surface (section 7). Each module
   asks the registry from its first commit. Nothing is inverted afterwards.
2. The chart points at the six packages. The real `java-spring` repository is created. A package release tool
   exists.
3. Extensions become packages on the same loader. `codegraph`, `uipro` and `ux-gates` move out of the keel.
4. The chandlery: one `index.json` per channel. It lists languages and extensions alike, each with a version, a
   compatibility range, a checksum and a publisher. An organisation can run a private chandlery.
5. When nothing is installed, `slipwai generate` names what to install and offers to do it.

**What stays in the keel.** Profiles, targets, frontends, axes, adoption, and the toolkit. This is the line that
issue #26 drew.

**Done when.** The keel's `make verify` runs in under ten minutes with no language present. A new language or
extension is one repository made from the template, with no change to the keel.

### Theme B. A leaner loop

**Goal.** The ladder spends its budget where the budget changes the outcome. Hardening is bounded, can be stowed,
and is scoped to a fairway.

1. **Stage budgets and a kill switch per stage** (issue #29). When a stage runs over its budget, the captain
   alerts, stows the open work, or parks. A CRITICAL finding is never stowed.
2. **Gap analysis runs once per fairway**, at the fairway's first clearance, and again when a mark changes. The
   completion audit runs per fairway, then across fairways.
3. **Adversary review runs once per slice**, with a severity bar. It runs once more per fairway, in the careen,
   before the flag is hoisted. Findings below the bar go to the careen.
4. **Mutation testing is a gate, not a backlog.** A slice merges at its threshold or does not merge.
5. **A ceiling on unreviewed decisions.** The captain holds it.
6. **The captain owns every wait.** A background gate gets a timeout from the captain. A delegate writes no
   polling loop of its own.
7. **Domain knowledge for the skipper** (issue #27), so it parks less and guesses less.
8. **Review and refactor before the merge.** After the demo is accepted, and before adversary review, a reviewer
   with a fresh context reads the slice's diff against the chart, the constitution and the slice's own examples.
   The reviewer looks for correctness, for reuse of what the keel or the service already has, for
   simplification, and for the hexagon being kept. The reviewer never edits. The slice's delegate fixes the
   findings. Then a refactor pass runs, with the fast checks green after each step. This is one round, with a
   budget, on the model table's review role. In the experiment, adversary review found 64 LOW findings that a
   review would have found for a fraction of the tokens.
9. **Two gates, not one.** In version 1, one `make verify` does everything, and every increment pays for lint,
   typecheck, structure and the whole suite. In version 2, only the fast checks run per increment inside a
   slice: `make unit`, lint, typecheck, and the slice's own tests, each bounded. The full `make verify` runs
   once, on the rebased branch, before the merge to `main`, and again in CI. The ladder, the captain and the
   generated `Makefile` all say which gate a stage runs. The full gate is never part of the inner loop.

**Done when.** Wall time and tokens per accepted slice are half of the experiment's median. No slice merges with
carried gaps.

### Theme C. Fairways, and the chart before the split

**Goal.** A fairway plans, builds, merges and releases on its own. Fairways share nothing but marks.

1. **The chart is written before the split, on both profiles.** On the event-modelling profile, the chart is
   derived from `model.yaml`, which already names each slice's context, service, typed events, and what the
   slice produces and reads. On the standard profile, a `/chart` stage names the fairways, and for each slice the
   routes, schemas and ports it sets and steers by. A gate called `check-chart` holds the chart, the way
   `check-model` holds the model.
2. **Clearance replaces the version 1 rule** "its own contract is settled" (issue #32). A second rule comes with
   it: no two slices set the same mark.
3. **The split writes typed attributes and a minimal `examples.md` for every slice.** Slices then arrive in the
   state `planned`, and the first iteration can fan out. The experiment proved the shape: decision D10 let slices
   S02 to S06 run at the same time against a protocol that S01 had written whole.
4. **`check-slice-scope` reads the chart for the paths a fairway owns**, on both profiles. The boundary holds
   with or without a model.
5. **Berths**, with the allocation policy (ports, database names) in the factory, not in each operator's head.
6. **Each fairway merges its own accepted slices to trunk.** Merges are in split order within a fairway and in
   order of arrival across fairways. Before each merge: rebase, then run the full gate. The merge is as dark as
   the release mode says. A slice with nothing holding it back parks for a person. The issue #30 work on the
   `slipwai-workstreams` checkout is the first version of this, and is renamed as it comes in.

**Done when.** Two fairways on two machines deliver with lead times that do not depend on each other. The board,
the berth list and the merge rules that the MANDA operator wrote by hand are generated.

### Theme D. Captains, the harbourmaster, and the logs

**Goal.** One captain per fairway replaces the single runner. Captains coordinate through the deck logs and the
harbour log. The logs are the source of truth for claims, marks, decisions, ids, messages and merges. Nothing a
captain relies on is held in an agent's memory. The captain reads the logs at every stage boundary, and the
captain enforces that read.

**Why replace the runner rather than extend it.** The runner is 1,742 lines of Python. It runs one iteration per
checkout. It trusts the iteration to read its inbox, to write its checkpoint, and to end on one line. Every
failure in the experiment and in MANDA was the runner trusting the iteration. The log inverts that: an iteration
that wrote no line made no progress.

**The captain runs in both modes.** `/drive` is the main mode. A person is present, and the fleet still fans out: one captain per fairway, as many boilers as the telegraph allows. Every product question, every park and every demo stop comes back to the person through the inbox, with the fairway and slice it belongs to, and the person answers from one seat. `/cruise` is the same fleet with nobody at the keyboard. The only differences are who answers and who demos: the skipper decides the product questions, and the hand walks the examples. Version 1 could fan out across a product only under `/cruise`; version 2 does it under both.

**What a captain does.** It fetches trunk and reads both logs. It works out the fairway's state from the logs plus trunk,
never from the `status` field in `model.yaml`. It gives clearance. It claims `slice/<id>`. It dispatches the
iteration with the stage budgets. It enforces an inbox read at every boundary. It writes a heartbeat. It ends a
stage that has wedged. It appends every result to the deck log.

**The harbourmaster.** It allocates berths. It keeps the harbour log. It computes the fleet board. It holds the
flags. It answers the telegraph. A person speaks to a captain through the log: `tell` appends a message, the captain
appends `read` at its next boundary, and a message older than N minutes forces a boundary.

**The delegates.** The skipper, the hand and the bosun stay as they are inside an iteration.

**Reused without change.** The stop table, the ladder in `drive.md`, the benchmark bracket, the stop hook, the
harness registry, and the control-file guard (the rule that an iteration never edits a gate, a `Makefile`, CI, or
a hook).

#### Ids and shared files

The experiment and MANDA paid 54 renumbering commits in one night. The cause: every berth took the next number
after the last one in its own checkout, and every berth appended to the same `decisions.md`. A claimed range of
numbers would only shrink the window. Version 2 removes both the counter and the shared file.

- Every id carries its fairway: `D-ORD-07`, `A-BIL-03`, `ADR-ORD-2026-10-06-event-store`. Two fairways cannot
  mint the same id. Nothing is ever renumbered. A citation never goes stale. When a reader wants a global order,
  the log's timestamps give it.
- Every append-only artefact is per fairway: `fairways/<name>/decisions.md`, `adversary-log.md`,
  `benchmark.jsonl`, the register, and the deck log. Two fairways never touch one file. The feature-level
  `decisions.md`, adversary log and register are rendered from the fairway files on `main` by the
  harbourmaster. They are never edited by hand. This is the same pattern as `make model`, which renders the
  diagrams.
- The chart is frozen before any slice starts. When a slice needs the chart changed, it writes a fragment under
  `fairways/<name>/chart.d/`. The harbourmaster folds the fragments on `main`. Amendments to `spec.md` work the
  same way. This is the pattern that `changelog.d/` already uses.
- Two code files that every slice touched in version 1 become generated or split. The composition root is
  rendered from the chart, one line per use case; `model_to_code` already knows the mapping, so a merge becomes
  a regeneration. The events module becomes one file per event, with a generated index, so two additions never
  meet on one line. On the standard profile, `contracts/` is already one file per entry.
- `main` itself stays shared. The rule for it stands: rebase, run the full gate, push. A real conflict in a mark
  is a contract change. It stops both fairways for the host.

#### The telegraph

The experiment spent 104 hours, and at its worst hundreds of millions of input tokens per slice. MANDA put five
runners on one machine until the load average reached 198. Fan-out without a budget turns a factory into a
bill. On a steamship the bridge does not shovel coal; it rings the engine order telegraph, and the engine room
raises the pressure to match. The person holds the telegraph. The harbourmaster is the engine room.

- **The positions.** Each one is a named group of numbers in `harbour.json`.

| Position | Boilers lit (captains at once) | Delegates per captain | Model roles | Bunker | When |
|---|---|---|---|---|---|
| `full-ahead` | Every fairway with clearance | The ladder's full fan-out | The strongest the table maps | Large per slice and per day | A person has chosen speed and watched the gauge |
| `half-ahead` | Up to half the fairways, at least two | Two | The table as mapped | Moderate | **The default.** Where a new project starts |
| `slow-ahead` | One | Two | The table as mapped | Moderate | One fairway at a time, inside it still parallel |
| `dead-slow` | One | One | The cheapest mapped role for every stage | Small | Version 1's `/drive` behaviour, on a budget |
| `stop` | None | None | — | — | Every captain parks at its next boundary. A person rings it, or the bunker is empty |

- **The numbers underneath.** `boilers`, `fanout`, the model role per stage (the existing `models.json`
  table), `bunker_per_slice`, `bunker_per_day`, and the stage budgets from theme B. `slipwai telegraph
  half-ahead` sets them as a group. Each can be set alone, and the fleet board then shows the position as
  `half-ahead, adjusted`.
- **The gauges.** The benchmark bracket already records tokens and wall time per stage. The captain appends them
  to the deck log. The harbourmaster sums them at every boundary into two readings on the fleet board: the
  pressure gauge, which is tokens per hour now, per fairway and in total; and the bunker, which is what is left
  of today's and each slice's budget.
- **Banking the fires.** When the bunker runs down faster than the position allows, the harbourmaster banks the
  fires in a fixed order before it rings `stop`. First it stows the optional stages into the careen: the second
  gaps pass, adversary findings below HIGH, mutation above the threshold. Then it drops the delegates per captain
  to one. Then it drops the skipper and implement roles one rung on the model table. Then it puts out one boiler.
  Each step is a line in the harbour log and a column on the fleet board, so a person sees the run slowing before
  it stops. A person stokes the fires back up by ringing the telegraph again.
- **What the plan is measured by.** Tokens and wall time per accepted slice are the last two columns of the fleet
  board. Theme B's acceptance, half of the experiment's median, is read from them.
- **The default is `half-ahead`, not `full-ahead`.** Full ahead is something a person rings, having looked at the
  gauge. Nobody rings full ahead into an ice field.

#### The fleet board

The MANDA operator wrote a status sweep by hand every few minutes, because nothing showed five berths at once.
The experiment's `watch` seat shows one runner's feed. Tools that watch agents at work have settled on a few
kinds of view. The fleet board takes one thing from each.

| View that the field uses | Where it is seen | What the fleet board takes from it |
|---|---|---|
| A status table, one row per agent, with liveness | Multiplexed terminal panes and process tables in multi-agent orchestrators. Cloud task lists with the states queued, running, needs review | The berth row: fairway, holder, stage, slice, idle time, live work, age, commits behind and ahead of trunk, undelivered messages, tokens today, fires banked or not, flag state. A finished fairway looks different from a stalled one |
| A task board by state | Kanban views of agent tasks, with diffs attached | The slice graph by fairway, coloured from the deck log: cleared, claimed, demoed, reviewed, merged, careened. It is rendered from the chart, the way `make model` renders the diagrams |
| A trace or swimlane timeline, with durations and cost | Tracing tools for agent runs: one waterfall of stages per run, with tokens and wall time on each span | One swimlane per berth over the day. Stages are spans from the deck log's heartbeat and stage lines, with tokens on each. The benchmark bracket already holds this data |
| A live event feed | Append-only logs tailed in a pane. The version 1 `watch` seat | The harbour log and every deck log merged by time, filterable by fairway. This is the one view that needs no computation |
| A burn meter against a budget | Cost dashboards in the hosted agent products | The pressure gauge (tokens per hour now) and the bunker (what is left of the budget), per fairway and in total. Each banking of the fires is marked on it |
| An approval inbox | Human-in-the-loop queues: everything waiting on a person, oldest first | Parks, open questions, flags ready to hoist, decisions past the ceiling, messages not yet read. Each with its age and the command that answers it |

One source, three renderings, plus a push. Every view is computed from the deck logs, the harbour log and
`git rev-list` per berth. The fleet board keeps no state of its own, so it cannot lie the way the `status` field
in `model.yaml` did. `slipwai fleet` prints the berth table and the inbox in the terminal. `slipwai fleet watch`
keeps that live, with the feed beneath it. The harbourmaster renders the full board (swimlanes, slice graph, pressure
gauge and bunker, inbox) to a static page on the project's existing Pages site, next to the event model, and refreshes it
on every harbour log line. A push notification on parks, banked fires and stalls reaches a person who is not looking.

**Under `/drive` and under `/cruise`.** The data is the same. Who refreshes it, and who answers it, differ.

- Under `/drive`, the person's session is the harbourmaster's seat. Captains run for every fairway the telegraph
  allows, in their own berths. Every question, park and demo stop from every captain lands in the person's
  inbox, oldest first, each naming its fairway and slice and the command that answers it. The person answers from
  that one seat; the answer is a `told` line, and the captain picks it up at its next boundary. The board the
  person sees is the fleet board: the demo stop's progress board and `/where-are-we` are two of its views. A
  fairway the person wants to drive by hand is a berth held by a person; its idle time is not a stall.
- Under `/cruise`, the same captains run, and the skipper and the hand take the person's two seats: the skipper
  answers the product questions and the hand runs the demos. Nobody is looking, so the inbox is pushed. The
  harbourmaster acts on what it is allowed to act on: it ends a stall, it banks the fires when the bunker runs down, and it forces a message
  through at the message's age bound. What it may not do stays in the inbox for a person: hoist a flag, accept an
  ADR, answer a park that the bosun could not move.
- The mixed case works too: a person drives one fairway by hand while captains run the rest, or a cruise runs
  overnight and the person takes the seat back in the morning. The board shows which berths have a person. A
  captain's clearance never takes a slice from a fairway that a person holds.

#### The bridge

The fleet board answers "what are the agents doing?" A product also needs an answer to "where is this
vessel?", for the person who owns it and for anyone they show it to. Version 1 scatters that answer across
`/where-are-we`, the demo stop's progress board, the rendered event-model page, `project.json`, the flag file
and the forge's pipeline page. The bridge is one page that gathers them, and it is the page a README screenshot
shows.

| Instrument | What it shows | Where the data already is |
|---|---|---|
| Position | The product state (slipway, sea trials, in service) and the release mode | `project.json` |
| Heading | The feature in flight, its fairways, and for each: slices accepted of total, the next cleared slice, the holder, and the flag that covers it | The chart, the deck logs, trunk |
| The chart itself | The event model or the standard-profile chart, rendered, with each slice coloured by its deck log state | `model.yaml` or `contracts/`, the deck logs. `make model` already renders the first |
| Flags | Every release flag: its capability, where it is hoisted, when, and whether it is due to be struck | The flag file, the harbour log |
| Deployed | What commit each environment runs, and the pipeline's state for trunk | The forge's pipeline API, the target's deploy record |
| Waiting on a person | Parks, questions, decisions past the ceiling, ADRs at Proposed, flags ready to hoist, oldest first | The harbour log, `decisions.md`, `docs/adr/` |
| The bill | Tokens and wall time to date, per fairway and in total, and per accepted slice | The deck logs' benchmark lines |
| The log | The last twenty lines of the harbour log and of each deck log, merged by time | The logs |

Three rules hold the bridge to the same standard as the fleet board.

- **It is computed, never written.** Every instrument folds from files that the loop already writes. The bridge
  keeps no state. If the bridge disagrees with trunk, trunk is right and the bridge is a bug.
- **It is the same page under `/drive` and under `/cruise`.** Under `/drive`, the person's session refreshes it
  at every demo stop and on `slipwai bridge`. Under `/cruise`, the harbourmaster refreshes it on every harbour
  log line. Under both, it is published to the project's existing Pages site, next to the event model that the
  `event-model.yml` workflow already renders, so a stakeholder with no checkout can read it.
- **It is for the owner of one product.** The fleet board is for whoever runs the harbour, and it may show many
  products. The bridge never shows another product. An organisation that wants both opens both.

For an adopted repository, the bridge gains one instrument: the convergence map, with each axis at its current
rung and the rung the strategy aims at.

A mockup of the bridge and the fleet board, with example data for a product called Ledger, is at
`docs/mockups/ledger-bridge.html`. Open it in a browser.

**Done when.** A run's status can be answered from the logs alone, after the fact, for every iteration. A
stopped run records why it stopped. Two captains on one feature never renumber a decision. The ids make
renumbering impossible, not merely unlikely. A person who owns a product can see its position, heading, flags,
deployments, waiting items and bill on one page without a checkout.

### Theme E. Releasing: how dark, decided by where the product is

**The problem.** In version 1, the setting `release` is either `flagged` or `park`. `flagged` is absolute: every
slice continues or opens a flag seeded off; `check-flags` demands that the flag is declared, read, and tested on
one path; and a slice with nothing holding it back parks for a person. When a product is in service, that is
exactly right: merging is not releasing. When a product is on the slipway, with no production and no actor but
the team, it is pure drag: a reader to call, two test paths, a key to hoist before every demo, and a park
whenever a slice is simply visible. MANDA ran five berths under it on a product that nobody used yet.

**Four release modes.** The mode is chosen by where the product is, not by a run setting. The ladder's
release-constraint stage becomes a lookup against the chart, not a question asked of every slice.

| Mode | When | What a merge means | What the factory does |
|---|---|---|---|
| **Open** | On the slipway: no production, or a production that only the team sees | The change is visible at once. Trunk is the demo | No flags, no reader, `check-flags` off. The demo is the release. The gate is `make verify` plus the hand's verdict |
| **Keystone** | Sea trials, or the first capability of any fairway | Dark by omission. Every slice lands except the entry point. The route, menu item or API that exposes the capability is the last task of the fairway's last slice. (This is Fowler's keystone interface pattern) | The chart names the keystone per capability. `check-slice-scope` refuses the entry wiring until the capability's other slices are implemented. Demos of the intermediate slices run at the `http` or `cli` rung, which the hand already knows. No flag in domain code. No two-path tests |
| **Flagged** | In service: real actors use what trunk deploys | Dark behind a key that is seeded off. A person hoists it | Version 1's behaviour, with the three changes below |
| **Promoted** | Teams whose production is a promoted build, not every push | Visible on trunk and in preview. Production receives only what passes the promotion gate | Pairs with the ephemeral pre-production environments and the staging-to-production gate already filed as issues #2, #4 and #5. Flags are optional |

The mode is recorded once in `project.json`, next to the product state (slipway, sea trials, in service). It
defaults from that state. A person changes it with an ADR. `/cruise` never changes it. A product moves from open
to keystone when its first pilot actor appears, and to flagged when it has actors it cannot surprise.

**Three changes to flagged, so that it costs less when it is the right mode.**

1. **One flag per fairway capability, named on the chart.** The stage already says that one flag covers a
   capability. Naming the flag at the split removes a stop from every slice, and removes the park for "nothing
   holds it back".
2. **Flags live at the entry wiring only.** A release flag is one `if` at the route or the menu. It is never
   inside a decider or a use case. The version 1 `flag_route` module and the entry-wiring table already point
   there. The rule and the scope gate make it the only place. The two-path test becomes the route's test.
3. **Environment defaults.** The flag reader resolves to on in local development and in preview. The production
   seed is off. A demo never needs a hoist.

**Kinds of flag, kept apart.** Hodgson's taxonomy names four kinds. Release flags are short-lived and per
capability, and they are the only kind the ladder opens. Operations flags (kill switches), permission flags (per
tenant or cohort) and experiment flags belong to the service. They are declared in their own section, never
seeded by a slice, and exempt from the strike rule below.

**Hygiene as a gate.** Every release flag records when it was hoisted everywhere. `check-flags` fails on a flag
that is older than N days after that date. The careen carries the task that strikes it. The fleet board shows,
per fairway, the flags hoisted and the flags waiting to be struck. A flag that is never struck is the debt that
every flag system accumulates. The factory refuses to accumulate it.

**Done when.** A product on the slipway runs the whole loop with no flag reader generated and no release park.
A product in service keeps every guarantee it has in version 1. In every mode, the number of release-stage stops
per slice is zero.

## 5. The delivery loop, drawn

The three figures below draw the new loop. The first two use the same grid, one per profile. Their geometry is
identical. The highlighted boxes are the only places where the two profiles differ, and every difference is one
question: where does a fairway's chart come from, and who holds it? The SVG files are in `docs/images/`.

### The event-modelling profile

One artefact answers every question. The model names each slice's context and service. It types the slice's
events. It says what the slice produces and reads. It carries the slice's status. Both `check-model` and
`check-slice-scope` read it. A fairway is one context's slices, derived from the model. It is never a second
field.

![The event-modelling loop](images/loop-event-modelling.svg)

### The standard profile

The loop is the same, but three of its inputs do not exist in version 1 and must be built. Contexts are recorded
on services in `project.json`, but a slice's context is only named at plan time, after the split. The contract is
Spec Kit's `contracts/` directory, written by the slice's own plan, so nothing says which slice steers by which
contract. The scope gate finds no model, so it holds no context boundary at all.

![The standard-profile loop](images/loop-standard.svg)

### The hop between fairways

This figure shows why neither fairway waits for the other. The slice that steers by a mark gets clearance when
the slice that sets the mark is planned, not when it is merged. The steering slice seeds its tests from the
schema. On the standard profile, the same hop carries a route, a schema or a port instead of an event.

![A mark set in one fairway clears a slice in another](images/mark-hop.svg)

### Where each mechanism comes from, in version 1 and in version 2

| Mechanism | Event-modelling profile, version 1 | Standard profile, version 1 | Version 2, both profiles |
|---|---|---|---|
| Which context owns a slice | `context` and `service` on the slice's block in `model.yaml`. When there is more than one context, `check-model` refuses a placed slice that names none | The plan's Structure Decision, written per slice after the split. `project.json` lists each service's `contexts`, but nothing ties a slice to a context until planning | The chart names it for every slice. The event profile derives it from the model. The standard profile writes it at the `/chart` stage, and the plan repeats it |
| What the contract is | The event frames: typed `attributes`, a `stream` or a `guard`, and `gwt` pointing at `examples.md` | "Entries in `contracts/` exist", plus a gaps review of the acceptance criteria. Spec Kit's Phase 1 writes the directory. There is no schema and no checker | A mark: one typed entry per published thing (event, route, schema or port). The event profile already has it. The standard profile gets the chart and `check-chart` |
| Who sets it, and when | The slice itself, at its example map, which moves it from `modelled` to `planned`. In version 1 this happens in the host before fan-out | The slice's own plan, inside its worktree. A sibling cannot build against it until the setting slice has planned | The slice that owns the mark sets it as its first stage, in its worktree. A `mark-set` line in the harbour log is what other fairways read |
| Clearance to run alongside siblings | Its own status is `planned`. This serialises a fresh fairway: every slice needs a host example map first | Its own `contracts/` entries exist. The same serialisation, and no record of what a slice steers by | Every mark it steers by is set by a slice that is planned or implemented. Its own marks it sets itself. On the event profile, `reads` already holds the data. On the standard profile, the chart holds it |
| One setter per mark | Not held. `check-model` checks that `reads` names an earlier setter. It does not check that one event has one setter | Not held | Held by `check-model` and `check-chart`: no two slices set the same mark |
| What "share nothing but" means | The context's events module, which only grows. The scope gate counts deletions in `domain/**/events*` | Undefined. Standard-profile contexts share routes and schemas, not events, and nothing keeps them additive | The fairway's marks, set and never moved. Event profile: one file per event, with a rendered index. Standard profile: the context's entries under `contracts/`, one file each |
| What `check-slice-scope` holds | The slice's own model block, the owning service, the context's layer directories, the events module as additive, new migrations only, and the composition root | With no model it finds no service and no context, so any code in any deployable passes. Only the cross-deployable rule and the migration rule still bite | It reads the chart for the paths a fairway owns, on both profiles. The boundary holds with or without a model |
| The done marker | `status: implemented` in the model. It is written at plan time and never reconciled, so in MANDA it was wrong for eight slices | A row in `specs/<feature>/slices/README.md` | The deck log's `merged` line plus trunk. The model's status and the register are rendered from the log, never written by hand |
| Where the fairway is recorded | Derived: the slice's `context`, or its `service` where that service holds one context (the issue #30 branch) | A Workstream column in the slice graph (the issue #30 branch). The scope gate does not read it | The chart: fairway, context, service, owned paths, marks set, marks steered by, holder. One file that captains and gates both read |
| Verification inside the loop | One `make verify` does everything, on every increment and before every merge | The same | Fast checks per increment: `make unit`, lint, typecheck, the slice's own tests. The full `make verify` once, on the rebased branch, before the merge to `main`, and in CI |
| Review before the merge | None. Convergence is the slice judging itself. Adversary review comes after the demo | The same | A fresh-context review of the slice's diff, then a refactor pass, between the accepted demo and adversary review |
| Merge and release | Split order across the whole feature. One `main`. Phase 4 per slice. The integrator merges | The same | Split order within a fairway, order of arrival across fairways. Each fairway merges as dark as the release mode says. The careen runs before the flag is hoisted. Nobody is a merge queue |
| Ids shared across fairways | The next number after the last one in the checkout. 54 renumbering commits in one night | The same | Every id carries its fairway (`D-ORD-07`). Every append-only file is per fairway. Feature-level views are rendered on `main`. Nothing is ever renumbered |

**The one design move that makes both profiles the same loop.** Give the standard profile what the event profile
already has: a chart written before the split, and a gate that reads it. Everything downstream (clearance, the
scope check, the deck log, the captain) then works on both profiles without a profile switch.

**What the event profile still needs.** Clearance and the one-setter-per-mark rule (issue #32); `reads` and the
setter frames are already in the model, and the function `depends_on_findings` already walks them. Setting the
marks inside the delegate rather than in the host; the example map stays the stage, only who runs it changes.
Rendering `status` from the deck log rather than writing it.

**What the standard profile needs.** A `/chart` stage before the split; it names the contexts per service, and
for each slice the routes, schemas and ports it sets and steers by, typed; it is the standard profile's stage 3.
`check-chart`: marks are typed, every mark steered by has a setter, each mark has one setter, deletions are
refused. Owned paths on the chart, so that `check-slice-scope` can hold a context boundary without a model.

## 6. How a project built on version 1 moves to version 2

A project that version 1 generated or adopted records which factory made it, in the field
`generator.generatedWith` of `project.json`. Version 1's `slipwai migrate` already carries such a project
forward. It regenerates the project at the recorded version with the recorded answers. It regenerates the
project at the new version. It merges the two against the working tree, three ways. It copies the catch-up
paragraphs from the changelog into `.slipwai/catch-up.md`, and `/catch-up` finishes what the merge could not.

Version 2 keeps that mechanism and changes four things about it. The migration is built in phase 8 (section
7), when the working contract returns. Phase 5 records what the migration needs as it renames files.

**Change 1. The base comes from version 1 itself, not from code that version 2 carries.** `migrate` reads
`generatedWith`. It installs that exact release of `slipwai` into a throwaway environment, the way
`make test-migration` already does from the last tag. It generates the base there. Version 2 never reproduces
version 1's output, and carries none of its generator. When the recorded version is a snapshot, for example
`1.5.2.dev4`, the base is the nearest release below it, and the difference is reported.

**Change 2. Languages are installed before the replay, never refused after it.** The project's backends name the
languages it needs. `migrate --check` lists them against the chandlery. `migrate` installs them (the
experiment's decision D23). If a backend has no compatible package, `migrate` refuses before it writes anything.
Afterwards `generator.languages` records both layers, family and framework.

**Change 3. The rename is a table that the merge applies, not a note for a person.** As phase 5 brings the
toolkit back, it produces `docs/rename.json`: every file, `Makefile` target, command, setting key and
`project.json` field whose name changed between version 1 and version 2, old name to new name. `migrate`
applies the table to the base before the three-way merge. A person's edits to `cruise.py` therefore land in the
file that replaced it, and `cruise.json` keys become `harbour.json` keys without a conflict. The catch-up page
still lists every rename once, for reading.

**Change 4. Work in flight is migrated as data, by rule, and never rewritten.** Version 1 has no shape for
this. The table says what happens to each thing.

| In the version 1 project | What `migrate` does |
|---|---|
| `specs/<feature>/story-split.md` with a slice graph and no fairways | Event profile: it renders one fairway per context from each slice's `context`, into the chart, for a person to confirm. Standard profile: it creates one fairway named `main`, puts the whole split in it, and adds a catch-up task to run `/chart` before the next slice is claimed |
| `decisions.md` with `D1` to `Dn`, `adversary-log.md` with `A1` to `An`, and numbered ADRs | It freezes them where they are, as the files of the `main` fairway. Existing ids stay valid and keep resolving. Every new id carries its fairway. Nothing is renumbered, including by the migration |
| The `status` fields in `model.yaml` | It reconciles them against trunk once, which MANDA showed they need. A slice whose code is on `main` is `implemented`, whatever the field said. It seeds the deck log with one `merged` line per such slice. From then on `status` is rendered |
| Open `slice/<id>` claims | If a claim branch is ahead of `main`, `migrate` refuses and names the branches: finish or merge them first. With `--with-claims`, it migrates `main` and leaves each claim to rebase, with the rename table applied to the claim's branch too |
| `infra/service/flags.auto.tfvars` seeded off, the flag reader, and `check-flags` | It sets the release mode from what the project has: a production target gives `flagged`, the target `none` gives `open`. It sets the product state to `in service` if any flag has ever been on, otherwise to `slipway`. It writes both to `project.json` for a person to correct. It gives every existing flag a `hoisted` date of the migration day, so the strike rule starts counting |
| `cruise.json`, `models.json`, the stop hook, and the inbox | It writes `harbour.json` with the telegraph at `half-ahead`. The model table gains the review role as `null` until a person maps it. It reads the runner's state files once into the deck log, so a run that stopped under version 1 reads as parked under version 2, with its reason |
| The `.specify/` presets and templates | Spec Kit itself stays pinned as recorded. The overlays are replayed like every other toolkit file |
| A repository adopted with `layout.delivery` | Everything above happens under the `<delivery>/` directory. The survey runs again, read-only, and its rows are kept. The convergence map gains a release-mode row |

**What a person does.** Read `.slipwai/catch-up.md`. Confirm the fairways and the release mode. On a
standard-profile project, run `/chart`. Run the full gate. A green `make verify` on the migrated tree is the end
of the migration. The migration is one commit on a branch of its own.

**How it is proven.** The keel's `make test-migration` generates a project with the last version 1 release from
PyPI, for every profile and backend, with a feature split, two slices implemented, one slice still claimed, and
flags in both states. It migrates the project at HEAD. It holds the result to the project's own gate, to the
rendered fairways, and to the grandfathered ids. The adopted fixtures do the same under `<delivery>/`. 2.0.0
cannot be cut without this test passing.

## 7. The order of work

Three decisions shape the order (section 9). First, the fork is cleared and rebuilt in version 2 shape, one
module at a time. Second, nothing in the fork maintains version 1's working contract until 2.0.0 is cut: no
`migrate`, no catch-up notes, no changelog fragments, no bump arithmetic. Third, the fork merges back to upstream
as version 2 once, when it is complete.

Every module comes back from one of two sources, by name: upstream `main` at 1.5.2.dev0 (commit `e1a9e43`) or
`slipwai-cruise-2` `main` (commit `c6f1e74`). Each module is renamed to the vocabulary as it lands. Nothing
comes back by bulk copy.

**Phase 0. Clear the deck.** Remove the fork's tracked tree, except `LICENSE`, `NOTICE` and `.gitignore`. Add a
short `README.md` that says what this repository is and points at this plan. Make one commit. Do not push it
until phase 1 has a green gate. The history stays: `git log` still reaches 1.5.2.dev0 and every upstream commit.
This phase was done on 2026-10-06. The real README is phase 9's.

**Phase 1. The keel's gate.** Bring back `pyproject.toml`, `VERSION` at `2.0.0.dev0`, a `Makefile` whose
`verify` target runs lint, typecheck, `check-structure` and test, `scripts/check-structure.py` with its tiers and
with the import surface as a tier, and CI with the fast jobs only. Source: upstream. Done when the gate is green
on an empty `src/`.

**Phase 2. The registry and the chart.** Bring back `registry.py`, `loaded.py`, `manifest/`, `catalog_merge.py`,
`language_directory.py`, `language_shape.py`, `conformance/`, `matrix/`, and their tests. Source:
`slipwai-cruise-2`. Bring back the keel's `catalog.json` with no backends in it. Create the real `java-spring`
repository first, then pin the six packages as submodules under `languages/`. Done when the gate loads every
package and runs the conformance suite, before any scaffold exists.

**Phase 3. The scaffold pipeline.** Bring back `assets.py`, `toolkit.py`, `scaffold.py`, and then the
`project/*.py` parts, one module at a time, in the order that `scaffold.project_files` assembles them. Source:
upstream. Each module lands already asking the registry for what the experiment's protocol moved. After each
part lands, `make starters` must produce the same tree as `slipwai-cruise-2` for every variant. Targets,
frontends and backing services come in here, from upstream.

**Phase 4. The verbs.** Bring back `generate`, `adopt`, `add-service`, `add-frontend`, `describe-service`,
`./init`, and `slipwai list`. Bring back the language verbs from `slipwai-cruise-2`: `cli_language.py`,
`language_index.py`, `language_install.py`, `language_plan.py`, `language_upkeep.py`, `language_release.py`.
Bring back `upgrade` without its version 1 paths. Do not bring back `migrate`.

**Phase 5. The toolkit and the loop.** Bring back the skills, commands, agents, the ladder, and the delivery
docs. Source: upstream and the `slipwai-workstreams` checkout. Rename each to the vocabulary as it lands, and
record each rename in `docs/rename.json`. Build the changes of themes B, C and E in here, not as migrations
afterwards: the `/chart` stage, clearance, the one-setter-per-mark rule, typed attributes at the split,
`check-chart`, `check-slice-scope` reading the chart, berths, stage budgets, stow and the careen, the review and
refactor stage, the two gates, the ceiling on decisions, bounded waits, the inbox at every boundary, the four
release modes, and the flag hygiene gate.

**Phase 6. The chandlery.** Extensions become packages. The index gains publishers and checksums.
`slipwai install` handles both kinds. An organisation can run a private chandlery. `generate` offers to install
what the answers need.

**Phase 7. Captains and the harbourmaster.** First, define the deck log and harbour log formats, the fleet
board and the bridge, and have the phase 5 loop write them, so they are proven before anything depends on them. Then build the
captain as the outer loop per fairway. Then retire the runner, once a captain has run one feature with two
fairways from start to finish.

**Phase 8. 2.0.0.** The working contract comes back for the merge: the rules in `AGENTS.md`, `changelog.d/`, one
2.0.0 changelog entry written from the fork's history, `migrate` from 1.5.x to 2.0 as section 6 describes and as
`make test-migration` proves, the CI proposal applied, and the package release tool. Then the fork merges back
to upstream as version 2.

**Phase 9. The README and the docs, rewritten for a first-time reader.** This is the last phase, after everything
it describes exists. Version 1's README is 34 kilobytes that explain the factory. The rewrite shows the experience
of using it, in the order a person meets it, and moves every explanation to a reference page that it links to.

- **Open on one session, shown rather than described.** `uv tool install slipwai`, `slipwai generate`, the
  questions as they appear, the first `make verify`, the first `/drive`, and the first demo stop with its board.
  Use a real terminal transcript, trimmed to what the person sees at each step. Target: fifteen minutes to a
  running product with one slice demoed.
- **Progressive disclosure.** Five pages, each ending where the next begins: start here; your first feature (the
  chart, the split, one slice through its demo); a second person joins (fairways, berths, the fleet board); let it
  sail (captains, the telegraph, the inbox, and what a person still decides); bring an existing codebase (adopt). A
  reader stops when they have what they came for.
- **Every verb shown as an experience, once.** Each page has the command, its output, and the one decision the
  person makes there. The vocabulary is introduced by use, with a glossary page behind it. The vocabulary is
  never a table first.
- **The reference moves out.** Axes, backend obligations, the package contract, the chart schema, the release
  modes, the gates, and `harbour.json` each get a page under `docs/reference/`, written for someone who already
  uses the tool and needs the exact rule.
- **Pictures where words cannot carry the point.** The bridge and the fleet board rendered from a real run, the
  loop diagrams from section 5, one demo-stop board, and one `/chart` output. Where a capture exists, use the capture, not a
  drawing.
- **Proven like code.** `make test-docs` runs every command in the first three pages against a fresh generation,
  and checks that the shown output is current. The README then cannot drift the way the experiment's `AGENTS.md`
  did.

Phases 6 and 7 can run at the same time. Phase 5 can start as soon as phase 1's gate is green, on the toolkit
assets alone, because the toolkit does not import the scaffold.

## 8. The rules for doing the work

The first attempt paid for these rules. They apply from phase 1, inside the fork.

1. **Chart first.** Do not claim a slice until the marks it sets and the marks it steers by are on the chart.
2. **One slice is one pull request, a few hours, one module or one skill.** S02 is the model. S08 is the
   anti-model.
3. **Fast checks inside the slice. The full gate before `main`.** Run `make unit` and lint per increment. Run
   `make verify` once, on the rebased branch, before the merge, and in CI.
4. **Review and refactor before `main`.** A fresh-context review of the slice's diff and a refactor pass are
   stages of the ladder, not favours. A slice merges with its review findings closed.
5. **Nothing merges red. Nothing merges with carried gaps.** Grant no standing exemption for an environment
   problem. Fix the environment, or exclude the test once, in writing.
6. **One adversary round. One convergence round beyond the first.** LOW findings go to the careen.
7. **Every stop records a reason. Every iteration writes to the log.** If a checkpoint is older than the last
   commit, delete it. Do not trust it.
8. **Declare the fork as a deployable in its own `project.json`** before any run of the factory on itself.
9. **Review decisions weekly.** The count of unreviewed decisions is a hard ceiling.
10. **People hold the merge to trunk** until phase 5's captain-enforced controls exist.
11. **Bring back. Never bulk copy.** Each module comes in by name, from a named source commit. Read it, rename
    it, and test it before the next one.

## 9. Decisions

### Settled on 2026-10-06

- **Salvage route: clear the deck and rebuild.** Pull from `slipwai-cruise-2` and from upstream, one module at a
  time. Do not merge the two trees (section 2 measured that route at 35 conflicts; it was not chosen).
- **All version 2 work happens in this fork.** No 1.x MINOR releases go to upstream in the meantime. The fork
  merges back as version 2 once, when complete. No working contract is maintained until phase 8.
- **Naming is nautical throughout.** Section 1 is the vocabulary. Nothing is called a workstation, a workstream,
  a lane or a runner.
- **No shared counters and no shared append-only files across fairways.** Theme D, "Ids and shared files".
- **A dial between speed and cost.** Theme D, "The telegraph".
- **Fast checks inside the slice, the full gate before `main`.** Theme B, item 9.
- **A review and refactor stage before the merge.** Theme B, item 8.
- **Four release modes, chosen by product state.** Theme E.
- **The README rewrite is the last phase.** Phase 9.

### Still open

1. **The package repositories.** They are private under `luke-gee`. Recommended: move them under `ROBCOATVG`,
   next to the keel, before phase 2, so that CI tokens and publishing have one owner.
2. **The trust model of the chandlery.** Signed entries from named publishers, or a list of allowed chandlery
   URLs. Decide before phase 6 writes the index schema.
3. **Whether the standalone executable bundles any language.** Issue #26 left it open. The experiment chose none
   (decision D5). Recommended: none, with `generate` offering to install.
4. **Whether issues #30, #32 and #29 also ship on 1.x**, for users who will not wait for 2.0. Under the second
   settled decision above, the default answer is no.
