# Slipwai 2: the plan

This document is the plan for version 2 of slipwai. Slipwai is a tool that generates a product repository
and then runs a delivery loop in it with coding agents. Say the name as "slipway".

The plan was written on 2026-10-06 and revised the same day. Its sources are this fork, the experiment in the
`slipwai-cruise-2` checkout, GitHub issues #26, #30, #32, #27 and #29 on `ROBCOATVG/slipwai`, and an
unposted write-up of a five-berth run on a product called MANDA.

The document has eleven sections:

1. The words this plan uses.
2. Where things stand today.
3. What the first attempt taught.
4. The five themes of version 2.
5. The delivery loop, drawn for both profiles.
6. How a project built on version 1 moves to version 2.
7. The order of work.
8. The rules for doing the work.
9. Decisions taken, and decisions still open.
10. The gaps review log.
11. The implementation plan.

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
| **Chandlery** | The index of packages that slipwai can install: languages and extensions, each with a version, a compatibility range, a checksum, a publisher and a one-line description. `slipwai search <term>` finds packages across every channel; `slipwai show <name>` describes one; `slipwai install <name>` installs it | "marketplace", "index" |
| **Slice** | One unit of product work that an actor can use when it is done. Unchanged from version 1 | Same word |
| **Fairway** | One bounded context's slices, in split order, with one release flag and one holder. The fairway is the unit of scope, of ownership and of release. Several fairways run side by side into the same harbour. A vessel keeps to its own fairway | "value stream", "workstream" |
| **Berth** | The provisioned place where one captain works: a sandbox or container, a git worktree, environment variables, an allocated block of ports, a database, and scratch directories. A berth holds no cloud or forge credential. `slipwai berth add`, `slipwai berth status` and `slipwai berth remove` manage berths | "workstation", "lane" |
| **Captain** | The outer loop for one fairway, in both modes. The captain reads the logs, works out the state of the fairway from the logs and trunk, gives clearance, claims a slice, dispatches an iteration, enforces every stage boundary, and appends to the deck log. There is one captain per fairway. Under `/drive` the captain brings every question and demo to the person. Under `/cruise` the skipper answers and the hand demos | "runner", `cruise.py run` |
| **Harbourmaster** | The part the captains share, one process per harbour. It allocates berths, is the only writer of the harbour log, draws the fleet board and the bridge, holds the flags, and answers the telegraph. Under `/drive` it runs inside the person's session; under `/cruise` it runs on its own. It is not a merge queue | "integrator" |
| **Deck log** | A fairway's own append-only log at `.slipwai/logs/<feature>/<fairway>.jsonl`, ignored by git and written only by that fairway's captain. The harbourmaster syncs it between machines through the ref `refs/slipwai/logs`, never through trunk. Its lines are: claimed, mark set, demo, accepted, merged, decision, told, read, heartbeat, stowed, parked | "stream log" |
| **Harbour log** | The one append-only log at `.slipwai/logs/harbour.jsonl`, ignored by git, that every fairway reads and only the harbourmaster writes. Its lines are: mark set, flag hoisted, berth allocated, fires banked, park for a person, telegraph rung. A captain never appends to it; the harbourmaster copies what other fairways need from each deck log | "cross-stream log" |
| **Chart** | The contracts, written before the split, as one committed file per feature: `specs/<feature>/chart.yaml`. The chart names the fairways, the marks each slice sets, the marks each slice steers by, and the paths each fairway owns. On the event-modelling profile `make chart` renders it from the event model and `check-chart` fails when the two disagree. On the standard profile a `/chart` stage writes it | "contract map", "streams manifest" |
| **Mark** | One published contract that another slice steers by: an event, a route, a schema or a port, typed. An event or a schema is typed with JSON Schema; a route is an OpenAPI operation; a port is a name with typed inputs and outputs. A mark is set once and never moved. The files that hold marks only grow | "contract entry" |
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
| **Skiff, liner** | The two shapes of a cloud target. A skiff is one environment on the smallest managed compute and database, for a staff tool. A liner is today's full stack, for a product. Theme E defines both | one stack for every project |
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

### The problem in one line

Version 1 delivers one product well with one runner, and gets no faster when people or machines join; its
gate grows with every language. The cost of doing nothing is the experiment's own numbers: 104 hours and 180
million input tokens per accepted slice at the median, and a gate that nobody runs locally.

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
- **The import surface is part of the schema.** A package may import exactly twenty keel modules. In the
  experiment the list lived in a prose contract that the gate parsed; in version 2 it is `import-surface.txt`
  at the repository root, which `check-structure` holds in both directions — a package that imports off the
  list fails, and a line naming a module the keel does not have fails too. This is what makes a change to
  the keel safe.
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
- **Packages had no release tool** (decision D112). Releases were cut by hand. Version 2 makes the whole path
  four verbs: `slipwai package new`, `check`, `release` and `register`.
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

**How a package is linked at usage time.** A user never touches a package repository. The link is the chandlery
index and the installed directory:

1. `slipwai install java-quarkus` asks the chandlery for the index (`index.json`, served from the public channel,
   or from the organisation's own channel when `SLIPWAI_LANGUAGE_INDEX` names one). The index lists each
   package's releases: name, version, the keel range it fits, the framework's family range, a URL for the
   release file, its sha256, and the publisher's signature.
2. The keel picks the newest release that fits this keel, resolves the family first (`java`), downloads each
   release file, checks its sha256, stages it, and renames it into `~/.slipwai/packages/<name>/`. A package is
   whole in that directory or not there.
3. From then on the loader reads the directory. It merges each `language.json` into the catalogue, imports each
   package's `LANGUAGE` object, and answers every question about that backend from it. The keel never names a
   language in its own code.
4. A generated project records what it was made with in `project.json`: `generator.generatedWith` for the keel
   and `generator.languages` for family and framework, with versions. On another machine, `./init` reads that
   record and says what to install; `slipwai migrate` installs it. The repository the package came from is not
   recorded anywhere a user reads.

**The two kinds of package.** A package is a language or an extension. Both are found, signed, installed,
loaded and released the same way. They differ in what they declare, and in when the keel asks them anything.

| | Language | Extension |
|---|---|---|
| Manifest | `language.json`: the backends it provides, the axis options each answers, its targets, and the family it belongs to | `extension.json`: version 1's catalogue entry (`name`, `description`, and `ignore`, the gitignore lines its local state needs) plus the keel range, the publisher and tags |
| Executable half | a `LANGUAGE` object keyed by `Member` constants, family resolved before framework | `init.py`, with the `project_guidance()` and the `check-<key>.py` gate that `docs/extensions.md` already specifies |
| When the keel asks it | at `slipwai generate`, to write the skeleton | at `./init`, after the skeleton exists. An extension never changes generated code |
| What conformance proves | every `Member` the manifest claims is answered, and the matrix is green | the six obligations of `docs/extensions.md`: replaceably idempotent; installs what it needs and is non-fatal when it cannot; projects a marker-fenced block into `AGENTS.md`; gates whatever state can go stale; names the recovery command on every failure path; and merges rather than overwrites a file a person hand-edits |

The loader does one merge into two destinations: `language.json` into the backends catalogue, `extension.json`
into the catalogue's `extensions` map, which is what `./init`'s extension menu already reads. Because the two
kinds sit beside each other on disk, the installed directory is `~/.slipwai/packages/<name>/`. It is not
called `languages/`, as the experiment's was: a directory of that name holding `codegraph` is the sort of
small lie that costs an hour later. `slipwai migrate` moves an install made before the rename. Decided
2026-10-06.

**How a package is linked at development time: it is not.** There is one link between a keel and a
package and it is made when a project is generated or migrated — the chandlery index, a download, a
checksum, a directory under `~/.slipwai/packages/`. There is no second link at build time. The keel's
repository pins no package, holds no submodule, and its gate never reads one.

This is the whole of theme A's goal, and it is easy to lose. The first instinct is to pin the first-party
packages so the keel's gate can prove them, and the experiment did exactly that: its CI could not load the
`go` submodule without a token and a person, and its root matrix regenerated every language's variants on
every commit, which is the ten minutes theme A is trying to buy back. Making the repositories public fixes
the token. It does not fix the shape. A keel whose gate checks seven packages is a keel that cannot be
changed without them, which is the coupling the packages were split out to remove.

So the work is divided by who owns the failure:

| Who | Proves | When |
|---|---|---|
| The keel's gate | That the conformance suite and the matrix work, against one toy package held in-tree as a fixture | Every commit. It is one package, and it is the keel's own |
| Each package's CI | That *that* package passes the suite against a pinned keel, and imports nothing off the surface | Every commit to that package, on its own schedule |
| The keel's release | That the published packages still pass against the keel about to ship | Once, at release (phase 8), never per commit |

A keel change that breaks a package is found by that package's CI, which is the Maven arrangement this
design keeps invoking: Central does not test every artefact that depends on it. The release job is the
backstop, and it runs once. Decided 2026-10-06, on the objection that a build-time link is a link theme A
exists to remove.

Publishing is `slipwai package release` in the package repository, which tags, builds the release file,
signs it and uploads it as a release asset, followed by `slipwai package register`, which adds the release
to a channel's index.

**Trust: an open channel, signed releases, and a publisher confirmed once.** Anyone may publish a language or
an extension; the ecosystem is open or it is not one. Loading a package runs its Python, so the keel will not
install anything it cannot attribute. Three rules make both true at once.

1. **Every release is signed by the identity that publishes it.** Sigstore keyless signing from the package's
   CI binds the release file to the repository and workflow that built it; a publisher without CI uses a
   minisign key. The index entry names the publisher identity, and the keel refuses a release whose signature
   does not match it. Nobody can publish as someone else.
2. **The public channel takes contributions by pull request.** A contributor makes the package with `slipwai
   package new`, cuts a signed release with `slipwai package release`, and opens the pull request that adds the
   entry to the public `index.json` with `slipwai package register`. The
   channel's CI checks that the signature matches the publisher, that the package passes the conformance suite
   against the keel range it claims, and that its name does not collide. Merged means listed. No approval by a
   person at `ROBCOATVG` is needed beyond the merge, and the checks are the same for a first-party package.
3. **A person confirms a new publisher once.** `slipwai install` shows a publisher it has not seen before, the
   repository behind the identity, and what the package will answer for, and asks once. The answer goes to
   `~/.slipwai/trust.json`, and every later release from that publisher installs without a question, the way
   an SSH host key or a Homebrew tap works. `ROBCOATVG` is in the file from the start, and nothing else is.
   `slipwai chandlery` marks each entry `first-party`, `confirmed` or `new to you`. An organisation can pre-seed
   the file for its machines, and can pin its channel to publishers it has reviewed.

This costs the keel nothing at build time. Like Maven shipping Central's address and a trust store and resolving
artefacts at run time, the keel reads the index when a person installs, verifies the signature then, and from
then on loads whatever is whole in `~/.slipwai/packages/`. A package placed there by hand, as a developer does
with `SLIPWAI_LANGUAGES`, loads without a signature and is shown as `unsigned` by `slipwai list`, so a machine
never mistakes a development copy for a release. Decided 2026-10-06.

**Which languages 2.0.0 ships with.** All six from the experiment: `typescript`, `python`, `go`, `java`,
`java-quarkus` and `java-spring`, each passing the conformance suite and its own matrix against the 2.0.0 keel.
Parity with 1.5, with `java-spring` needing its real repository first (phase 2). Decided 2026-10-06.

**Where the first-party packages live.** Under `ROBCOATVG`, beside the keel, public from the start, moved
before phase 2. Public so that a contributor can read one without being given access, and so each
package's own CI is free on Actions. Not so that the keel's CI can read them: it does not read them at
all, and the submodule the experiment could not load without a token is gone rather than unlocked
(theme A). Decided 2026-10-06 (section 10).

**What version 2 builds.**

1. The keel is brought back one module at a time, in the order of the import surface (section 7). Each module
   asks the registry from its first commit. Nothing is inverted afterwards.
2. The chart points at the six packages. The real `java-spring` repository is created. The six are rebuilt
   onto the template that `slipwai package new` writes, so a first-party package and a contributor's are the
   same shape.
3. Extensions become packages on the same loader, in the shape above. `codegraph`, `uipro` and `ux-gates`
   move out of the keel and out of `assets/toolkit/scripts/extensions/`. What stays in the keel is the
   `./init --extension` flag, the menu, the election record in `.slipwai/extensions.json` and the projection
   pass: the keel names no extension in its own code, exactly as it names no language.
4. The chandlery: one `index.json` per channel. It lists languages and extensions alike, each with a version, a
   compatibility range, a checksum, a publisher, a one-line description and tags. An organisation can run a
   private chandlery.
5. **Search from the command line.** `slipwai search <term>` reads every configured channel and matches the
   term against name, description, tags, family, framework and the axis options a package answers, and prints
   one line per match: name, kind (language or extension), latest version that fits this keel, publisher
   status (`first-party`, `confirmed`, `new to you`), installed or not, and the description. `slipwai search
   --kind extension`, `--family java` and `--answers http=fastapi` narrow it. `slipwai search` with no term
   lists everything. `slipwai show <name>` prints one package in full: what it answers, which targets, which
   frameworks, the keel range, the publisher and its repository, the release history, and the install command.
   The same search runs inside `generate` when an answer names something not installed, so the interview can
   say "three packages answer that; install one?" instead of refusing.
6. When nothing is installed, `slipwai generate` names what to install and offers to do it. The standalone
   executable bundles no language: it is the keel alone, the same as the wheel, so there is one artefact to
   build and sign and no bundled copy to drift from the chandlery's. Decided 2026-10-06.
7. **Making a package is a verb, not a fork of the template.** `slipwai package` is `generate` for packages,
   with the same shape as the product path:
   - `slipwai package new <name>` asks what the product interview asks, for a package. The first question is
     the kind, and it decides the rest. For a **language**: family, or framework of which family; which
     backends it provides and which axis options each answers; which targets. It writes `language.json`
     filled in, the `LANGUAGE` object as a skeleton with one `Member` per answer and a failing test per
     Member, and the matrix. For an **extension**: what the tool is and what it installs; where its state
     goes and what to add to `.gitignore`; which capability it waits for, if any; and whether it leaves state
     that can go stale. It writes `extension.json` filled in, `init.py` as a skeleton with `main()` and
     `project_guidance()`, `ready()` and `installed()` where it waits, a `check-<key>.py` where it leaves
     stale state, and a failing test per obligation. Either kind also gets the conformance suite wired into
     `make verify`, a CI workflow that runs it against the pinned keel and signs a release with Sigstore,
     `make release`, and a `README` that says what is left to write. Like `generate`, it makes one commit on
     `main`, and like `./init` it offers to create the repository on the forge and push.
   - `slipwai package check` runs the conformance suite locally against the installed keel, with the matrix
     where the package is a language, and prints the same lines the channel's CI will.
   - `slipwai package release` tags, builds the release file, signs it, and uploads it as a release asset. It
     refuses when `check` is red or the version is not new.
   - `slipwai package register [--channel <url>]` opens the pull request that adds the entry to the channel's
     index, with the entry generated from the release. For a private channel it pushes the entry directly.
   The `add-language`, `add-framework` and `add-extension` skills become the prose around these four commands, which is slice 9.5. In version 1 they are 1,368 lines in `.claude/skills/` describing a manual procedure — fork the template, fill in `language.json` by hand, wire the matrix, remember the release — and almost every line of that is a verb's job now.

**What stays in the keel.** Profiles, targets, frontends, axes, adoption, and the toolkit. This is the line that
issue #26 drew.

**Done when.** The keel's `make verify` runs in under ten minutes with no language present. A new language or
extension is one repository made by `slipwai package new`, with no change to the keel.

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

1. **The chart is written before the split, on both profiles, as one committed file**, `specs/<feature>/chart.yaml`,
   so captains and gates read one thing on either profile and a change to it shows in a diff. On the
   event-modelling profile `make chart` renders it from `model.yaml`, which already names each slice's context,
   service, typed events, and what the slice produces and reads; `check-chart` fails when the rendered file and
   the model disagree, the way `check-drawio` holds the canvas today. On the standard profile, a `/chart` stage
   writes it: the fairways, and for each slice the routes, schemas and ports it sets and steers by. Marks are
   typed: an event or a schema with JSON Schema, a route as an OpenAPI operation (the keel already generates
   OpenAPI), a port as a name with typed inputs and outputs. `check-chart` holds the chart the way `check-model`
   holds the model.
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
stage that has wedged. It appends every result to its own deck log, and to nothing else.

**The harbourmaster.** One process per harbour; the only writer of the harbour log. It reads every deck log
after each fetch and copies into the harbour log what other fairways need: a mark set, a park, a flag change,
a telegraph change. Captains read the harbour log and never write it, so the one shared log has one writer and
never conflicts. It allocates berths. It computes the fleet board and the bridge. It holds the flags. It answers
the telegraph. Under `/drive` it runs inside the person's session. Under `/cruise` it is a process of its own,
on one machine; captains on other machines reach it through the forge, by fetch and push, the way they reach
trunk. A person speaks to a captain through the log: `tell` appends a message, the captain
appends `read` at its next boundary, and a message older than N minutes forces a boundary.

**The delegates.** The skipper, the hand and the bosun stay as they are inside an iteration.

**Reused without change.** The stop table, the ladder in `drive.md`, the benchmark bracket, the stop hook, the
harness registry, and the control-file guard (the rule that an iteration never edits a gate, a `Makefile`, CI, or
a hook).

**Permissions and credentials.** A captain runs unattended with edits accepted and nothing more. Every berth
is a sandbox or a container that the berth provisioning creates, and the captain inside it holds no credential
for the forge, the cloud or the chandlery. Anything that needs one goes through the harbourmaster: the push of
a slice branch, the merge to `main`, a deploy, a flag change, a publish. The harbourmaster holds the credentials,
checks each request against the list of things a run never does (destroy data or history, release what nobody
asked for, spend money, expose a secret, weaken security, discard a person's commits, change a gate to make it
pass), and refuses with the reason. Under `/drive` the person's session is the harbourmaster, so the person's
own credentials are used and never copied into a berth. Version 1's `--sandbox` flag, which let a run bypass
permissions, does not exist in version 2: the sandbox is the berth, not a flag.

**Platforms.** Version 2 runs where version 1 runs: macOS, Linux, WSL and native Windows, where a project's
scripts run under Git Bash as today. The sandbox-per-berth rule has a Windows answer: on native Windows a berth
is a container under Docker Desktop, or a Windows Sandbox instance where Docker is not available, and the keel's
own verbs (`generate`, `adopt`, `install`, `bridge`) run natively. Every captain control is proven on all four
before 2.0.0, which puts a Windows job and a WSL job in the keel's CI beside the Linux one, as version 1's
cross-platform proof already does for the installer.

**Harnesses.** Version 2 supports every agent harness that Spec Kit supports, and at least Claude Code, Codex,
Cursor, Gemini CLI, OpenCode and Kiro. The harness registry stays the mechanism: one row per harness that says
how it is invoked headless, whether it has a hook that fires when a turn ends and can refuse the end, whether it
has a hook before an editing tool, and what the projection into its settings file looks like. The captain's
controls are designed so that none of them depends on a hook: the captain reads the last line of every
iteration itself, compares the controlled files before and after, and owns the waits. Where a harness has a
hook, the hook is a second belt. A harness is listed as supported when the captain has run one feature end to
end on it; until then its row says `unproven`, and `slipwai` says so when it is chosen.

#### Ids and shared files

The experiment and MANDA paid 54 renumbering commits in one night. The cause: every berth took the next number
after the last one in its own checkout, and every berth appended to the same `decisions.md`. A claimed range of
numbers would only shrink the window. Version 2 removes both the counter and the shared file.

- Every id carries its fairway: `D-ORD-07`, `A-BIL-03`, `ADR-ORD-2026-10-06-event-store`. Two fairways cannot
  mint the same id. Nothing is ever renumbered. A citation never goes stale. When a reader wants a global order,
  the log's timestamps give it.
- Every append-only artefact is per fairway: `fairways/<name>/decisions.md`, `adversary-log.md`,
  `benchmark.jsonl`, the register, and the deck log. Two fairways never touch one file. The logs themselves are
  not committed: they live under `.slipwai/logs/`, which `.gitignore` lists, because heartbeat and token lines
  arrive every few seconds and have no place in trunk's history. The harbourmaster pushes and fetches them
  through the ref `refs/slipwai/logs`, so a captain on another machine reads the same lines without a commit
  on `main`. What is committed is what the logs render: the decisions, the register, the chart fragments. Every log line
  carries `v: 1`; a reader refuses a line from a newer format and names the upgrade that reads it. The logs are
  kept for the life of the feature and archived into the feature's directory, compressed, when it closes, so the
  bill and the decisions stay auditable after the berths are gone. The feature-level
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
- The harbour log is shared for reading and has one writer, the harbourmaster. That is how it keeps the rule.
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

- **The numbers underneath, and fine tuning.** `boilers`, `fanout`, the model role per stage (the existing
  `models.json` table), `bunker_per_slice`, `bunker_per_day`, and the stage budgets from theme B. `slipwai
  telegraph half-ahead` sets them as a group. Each can be set alone afterwards: `slipwai telegraph --set
  boilers=2 fanout=1 bunker_per_day=120M`, and `/model-delegation-settings` for the roles, the same checked
  edit the version 1 settings commands make. A position with a changed number shows on the fleet board as
  `half-ahead, adjusted`, and ringing a position again resets every number to that position's group. The
  bridge's local copy has the same controls: a fine-tune panel under the speed setting for boilers, delegates
  per captain, the role per stage, and the two budgets.
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
on every harbour log line. A push notification on parks, banked fires and stalls reaches a person who is not looking: through the harness's
own notification hook where it has one, and otherwise through a webhook URL in `harbour.json`, which covers
Slack, Teams and a phone.

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
- **It is the same page under `/drive` and under `/cruise`, and it comes in two copies.** `slipwai bridge`
  serves the page on localhost from the harbourmaster's seat. That copy has the controls: a person answers a
  question, hoists or strikes a flag, accepts an ADR, rings the telegraph or tunes a number from the page, and
  each click is a request to the local server, which appends the `told` line, syncs the logs, and re-renders.
  The copy on the project's Pages site, next to the event model that the `event-model.yml` workflow already
  renders, is the same page without the controls: read-only, for a stakeholder with no checkout. Under
  `/drive` the person's session is the server; under `/cruise` the harbourmaster process is. Nothing on either
  copy is state of its own.
- **It is for the owner of one product.** The fleet board is for whoever runs the harbour, and it may show many
  products. The bridge never shows another product. An organisation that wants both opens both.

For an adopted repository, the bridge gains one instrument: the convergence map, with each axis at its current
rung and the rung the strategy aims at.

A mockup of the bridge and the fleet board, with example data for a product called Ledger, is at
`docs/mockups/ledger-bridge.html`. Open it in a browser. A published copy is at
https://claude.ai/artifact/AX1ehrF1s3AmEouGxW7LBx and the plan itself at https://claude.ai/artifact/717r1H4WSJAP5b7DmiWmou.

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

**The shape of the target, decided by the same facts.** Today a project that answers `aws` or `azure` gets
one stack whatever it is: on AWS, a Fargate service per application deployed blue/green behind its own load
balancer and a CloudFront distribution, RDS, Cognito pools, two environments and a bootstrap with an OIDC
role; on Azure, Container Apps, a Flexible Server, Entra, two environments. That is the right stack for a
product with customers. It is too much for a staff tool with twelve users, and the idle bill (about $40 a
month per service on AWS across two environments) says so. Version 2 gives each target two shapes, and the
interview chooses one from the product state and one more question: who uses it, and what happens when it is
down.

| Shape | For | What it is on AWS | What it is on Azure | What it drops |
|---|---|---|---|---|
| **Skiff** | A staff or internal tool: the team, or named colleagues; an outage is an inconvenience | One environment. A Lightsail container service from the same image, with the smallest RDS or an Aurora Serverless v2 instance at its floor, staff identity through Cognito, flags through SSM, no CloudFront unless there is a site, no load balancer, rolling deploys | One environment. One Container App that scales to zero, the smallest Flexible Server, Entra app roles | The second environment, the per-service balancer, blue/green, CloudFront for an API, the customer identity pool. Roughly a third of the idle bill |
| **Liner** | A product with customers, or anything whose outage is an incident | Today's stack, unchanged | Today's stack, unchanged | Nothing |

Rules that hold the shapes to the same bar:

- The shape is recorded in `project.json` beside the target. It defaults from the product state: `slipway`
  gives a skiff, `in service` gives a liner, and the interview's question decides sea trials. A person can
  override it either way at generation.
- **Moving up is a step, not a rewrite.** `slipwai converge --shape liner` regenerates the target's module
  for the liner shape, keeps the database and its data, writes the runbook for the one step a person does by
  hand (the DNS move), and records the change in the convergence map's platform axis. Nothing moves a project
  down a shape without a person asking.
- **The skiff's compute is a row, because managed services get retired.** Version 2's skiff was written
  around AWS App Runner. App Runner is being sunsetted, and the first real project generated on the shape —
  warbook — had to be moved to Lightsail before version 2 had built any of it. The lesson is not that
  Lightsail is the right answer forever; it is that the answer has a shelf life. So the compute a skiff
  runs on is one named row in the target's table and one stack file, never a choice spread through the
  infrastructure, the deploy pipeline and the docs. Replacing it should cost a day, not a phase. The same
  holds for the liner. Decided 2026-10-06, on warbook's evidence.

- **The same gate, the same flags, the same images.** A skiff runs the same `make verify`, the same release
  modes, the same flag reader and the same images as a liner; languages answer nothing new. Only the
  infrastructure module and the pipeline differ, which is what keeps the shape a target decision and not a
  language one.
- **The bridge shows the shape and the idle cost.** Beside the product state, so the owner sees what they are
  paying for the stage they are at.
- A heavier shape than today's (own VPC, multi-AZ database, WAF, alarms and a runbook for on-call) is a later
  row, after 2.0.0, when a product asks for it.

**Done when.** A product on the slipway runs the whole loop with no flag reader generated and no release park.
A product in service keeps every guarantee it has in version 1. In every mode, the number of release-stage stops
per slice is zero. A staff tool on AWS costs a third of what it costs today at idle, with the same gate.

## 5. The delivery loop, drawn

The three figures below draw the new loop. The first two use the same grid, one per profile. Their geometry is
identical. The highlighted boxes are the only places where the two profiles differ, and every difference is one
question: where does a fairway's chart come from, and who holds it? The SVG files are in `docs/images/`.

**Two things are the same in both profiles, and neither is optional.**

1. **Example mapping opens every slice.** A slice begins by turning its story into rules, an example per
   rule, and the questions it cannot answer. Nothing is implemented before that, in either profile. The
   profiles differ only in where the examples come from: the event profile derives them from the model's
   given/when/then, and the standard profile writes them from the chart and the story. They do not differ
   in whether there are any. A slice with no examples has nothing for the hand to demo and nothing for a
   test to be about, and the demo stage in both figures says "the hand walks the examples" — in version 2
   that sentence is true because a stage put them there.
2. **The implement stage is red, green, refactor.** The ladder's `Implement` box is not "write the code":
   it is the `tdd` skill's cycle, with `make unit`, lint and types as the green step's gate. The mutation
   gate later is evidence the tests were real; it is not what makes anyone write one first.

   **How wide a cycle is, and how much one delegate takes, are settings — version 1's, carried forward.**
   `.specify/drive.json` holds two: `delegate`, which is `story` (every rule of one user story, each rule
   its own cycle, one context), `rule` (one rule with its examples) or `task` (one task as the tasks stage
   cut it); and `cycle`, which is `rule` (a rule's examples written together, each failing for its own
   stated reason, then the code) or `example` (one failing test, then the code that passes it). The
   defaults are `delegate=story`, `cycle=rule`.

   Two rules come with them and both matter more than the defaults. **A story is never a cycle unit** —
   every rule of a story red before any is implemented is a batch, and `cycle=rule` is the widest cycle
   there is; the setting refuses `story` rather than accepting it. And the settings **fall back rather
   than fail**: on a slice whose tasks carry no story tag, `story` falls to `rule`; on a map that does not
   number its rules, the boundary falls to `task` and the cycle to `example`. A slice that cannot support
   the configured width runs narrower, and says so.

   This is why the figures say "one cycle per the setting" rather than naming a width. Version 2 adds one
   thing: the setting is read and shown by the telegraph alongside the model roles and the budgets (slice
   7.3), because how wide a cycle is belongs with the other dials that trade speed against care.

Version 1 had both — the `tdd` and `testing` skills are in the toolkit, and the event profile's example map
is a stage — but the standard profile had no example-mapping stage at all, so it reached a demo of examples
nothing had written, and neither profile's loop named the inner cycle, so `Implement` read as a black box.
Both are stages in the figures now. Noticed 2026-10-06.

**Two refactors, and they are not the same one.** The one inside `Implement` is the third beat of each
cycle: the code just made green, tidied before the next example. The one at `Review + reshape` is the
slice's whole diff, after the demo, with a fresh-context reviewer on it — the shape of what was built
rather than the shape of one cycle's code. Collapsing them loses the small one, which is the one that
stops the big one being needed.

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
the slice that sets the mark is planned, not when it is merged. The setting captain writes `mark-set` to its
deck log; the harbourmaster copies the line into the harbour log; the other captain reads it there. The steering slice seeds its tests from the
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
And an example-mapping stage of its own: the event profile derives its examples from the model, and a
profile with no model has to write them, which is why this is the profile that needs the stage most rather
than the one that can do without it.

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
| `specs/<feature>/story-split.md` with a slice graph and no fairways | It proposes fairways on both profiles and marks them proposed. Event profile: one fairway per context, from each slice's `context` in `model.yaml`. Standard profile: one fairway per context it can read from the slices' plans (the Structure Decision names the service and context) and from each service's `contexts` in `project.json`; a slice whose plan names no context goes into a fairway called `unplaced`. A person confirms the proposal, edits it, or runs `/chart`. No slice is claimed while its fairway is proposed. A project where every slice lands in one context gets one fairway and sees no change |
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

**How phases 1 to 4 are driven.** No slipwai loop runs on the fork before phase 5: no `/drive`, no captain, no
adoption of the fork by 1.5.2. Plain agent sessions work from this plan and from the rules in section 8, and
people merge. The quality bar comes from the toolkit's skills, not from the ladder: all 53 skills under
upstream's `assets/toolkit/skills` are copied into the fork's `.claude/skills/` as part of phase 0, unchanged,
so that `testing`, `tdd`, `codebase-design`, `hexagonal-architecture`, `cli-design`, `refactoring`,
`find-gaps`, `acceptance-review`, `adversarial-testing`, `architecture-decisions`, `technical-writing` and `wtf`
are available to every session from the first commit. Phase 5 brings the toolkit back properly, renamed, and
replaces this copy. Decided 2026-10-06 in the gaps review (section 10).

**Where version 2 lives.** Everything for version 2 is on GitHub: this fork, the six package repositories,
the public chandlery channel as a GitHub Pages site, and CI on GitHub Actions. Actions is free for public
repositories, so the fork and the packages are public from phase 2, when the first gate runs there. Version 1's
canonical home on the Gitea instance at `git.treyco.dev` is untouched until the merge back; at phase 8 a person
decides whether Gitea stays canonical with GitHub as the mirror, as today, or GitHub becomes canonical. The
runner topology notes for the Gitea instance stay valid for version 1 in the meantime. Decided 2026-10-06
(section 10), on the condition that Actions stays free for public repositories; if it does not, packages and the
chandlery stay on GitHub and the keel keeps today's split.

**Phase 1. The keel's gate.** Bring back `pyproject.toml`, `VERSION` at `2.0.0.dev0`, a `Makefile` whose
`verify` target runs lint, typecheck, `check-structure` and test, `scripts/check-structure.py` with its tiers and
with the import surface as a tier, and CI with the fast jobs only. Source: upstream. Done when the gate is green
on an empty `src/`.

**Phase 2. The registry and the chart.** Bring back `registry.py`, `loaded.py`, `catalog_merge.py`,
`language_directory.py`, `language_shape.py`, `conformance/`, `matrix/`, and their tests. Source:
`slipwai-cruise-2`. Bring back the keel's `catalog.json` with no backends in it. Create the real `java-spring`
repository first. The keel pins none of them: the link between a keel and a package is made when a project
is generated, not when the keel is built (theme A). Done when the catalogue, the package directory and the
loader build a registry on an empty keel, before any scaffold exists.

**Phase 3. The scaffold pipeline.** Grow `assets.py` into the asset trees, bring back `toolkit.py`, `manifest/`, `scaffold.py`, and then the
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

**Phase 6. The chandlery.** Extensions become packages, with a manifest and an entry point of their own and a conformance profile that holds the obligations `docs/extensions.md` already sets. The index gains publishers and checksums.
`slipwai install` handles both kinds. An organisation can run a private chandlery. `generate` offers to install
what the answers need.

**Phase 7. Captains and the harbourmaster.** First, define the deck log and harbour log formats, the fleet
board and the bridge, and have the phase 5 loop write them, so they are proven before anything depends on them. Then build the
captain as the outer loop per fairway. Then retire the runner, once a captain has run one feature with two
fairways from start to finish.

**Phase 8. 2.0.0.** The working contract comes back for the merge: the rules in `AGENTS.md`, `changelog.d/`, one
2.0.0 changelog entry written from the fork's history, `migrate` from 1.5.x to 2.0 as section 6 describes and as
`make test-migration` proves, the CI proposal applied, and the four `slipwai package` verbs proven on a
first-party package. Then the fork merges back
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
- **One figure that answers "where does a slice come from?"** The README's hardest question is not
  what a verb does, it is how a spec becomes work somebody is doing. Section 5's figures start at a
  claimed slice and the reader has to take the chart on trust; the fleet board and the bridge show a run
  already going. So phase 9 draws the step before: a single feature from its specification through the
  model or the chart, the split into slices, the example map that turns one slice into rules and
  examples, clearance, the claim, and the handoff to a delegate at the `delegate` and `cycle` widths.
  One figure per profile, the same geometry, with the two boxes that differ highlighted the way section
  5's pair already does — because the point is that the loop is one loop and the profiles differ in
  where the examples come from, not in what happens to them. Drawn rather than captured: it is the shape
  of the method, not a screenshot of one run. Slice 9.6.

- **The contributor path is documentation too.** The five maintainer skills in `.claude/skills/` —
  `add-language`, `add-framework`, `add-extension`, `add-target` and `add-backing-service`, 1,891 lines
  between them — are the only part of version 1 that version 2 neither brought back nor replaced. Each
  describes a procedure that has changed. The first three are replaced by `slipwai package new`, `check`,
  `release` and `register` and by the two package shapes in theme A. `add-target` walks the catalogue's
  targets block and `project/infra.py`, and now has two shapes to cover rather than one, the skiff and the
  liner. `add-backing-service` walks `catalog.json`, `prune.py`'s tables and the `src/slipwai/` wiring, and
  the catalogue it describes no longer holds backends at all. They are rewritten here, last, because a
  skill that describes a verb has to be written against the verb that shipped. Slice 9.5.

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
- **The executable bundles no language; `generate` offers to install.** Theme A, item 5.
- **Nothing ships on the 1.x line.** The `slipwai-workstreams` commit is salvaged into slice 5.3 and not released on its own; version 1 users get a final 1.5.x that points at 2.0 (slice 8.6).
- **An open public channel: anyone publishes by pull request, every release is signed by its publisher, and a person confirms a new publisher once at first install.** Theme A, "Trust".
- **The six package repositories move under `ROBCOATVG`, public, before phase 2.** Theme A, "Where the first-party packages live".

### Still open

None. Every decision this plan needed on 2026-10-06 is taken. New ones go to the deck logs' `decision` lines
and, where a person must take them, to the bridge's inbox.

## 10. Gaps review, 2026-10-06

The plan was reviewed with the toolkit's `find-gaps` skill: the Plans checklist (scope, prerequisites,
sequencing, failure and recovery, state and data, observability, security, testing, unstated knowledge),
cross-checked against the dashboard mockup. 4 blockers, 10 should-address, 6 nice-to-have were found. Each
answer is written into the section it belongs to; this section is the log.

Resolved:

- [Blocker → section 7, "How phases 1 to 4 are driven"] What runs the ladder on the fork before it has a
  toolkit. Answer: nothing does; plain sessions with the toolkit's skills copied in, people merge.
- [Blocker → section 1, theme D] Who writes the harbour log. Answer: only the harbourmaster, one process per
  harbour; captains write their deck log and nothing else; the harbourmaster copies across what others need.
- [Blocker → theme A, "Where the first-party packages live"] Where the package repositories live and how a
  package is linked at usage time. Answer: under `ROBCOATVG`, public, before phase 2; at usage time the link is
  the chandlery index and `~/.slipwai/packages/`, never a repository.
- [Should → section 6] How fairways are worked out when a version 1 project migrates. Answer: `migrate`
  proposes them on both profiles from the model or from the plans and `project.json`, marks them proposed, and
  claims nothing until a person confirms.
- [Should → theme D, "Harnesses"] Which harnesses version 2 supports. Answer: every one Spec Kit supports, at
  least Claude Code, Codex, Cursor, Gemini CLI, OpenCode and Kiro; the captain's controls depend on no hook;
  a harness is `unproven` until a captain has run a feature on it.
- [Should → section 7, "Where version 2 lives"] Which forge runs version 2's CI and the chandlery. Answer:
  GitHub for everything, public, because Actions is free for public repositories; Gitea's role is decided at the
  merge back.
- [Should → section 1, theme D, "Permissions and credentials"] Unattended permissions and credentials.
  Answer: a sandbox per berth with no credentials in it; every credentialed action goes through the
  harbourmaster, which holds the keys and the refusal list.
- [Should → theme D, "Platforms"] Which platforms version 2 supports. Answer: the same four as version 1,
  native Windows included; a Windows berth is a Docker Desktop container or a Windows Sandbox instance; all
  four are in CI before 2.0.0.
- [Should → section 1, theme C] Whether the chart is a committed file, and what a typed mark is on the
  standard profile. Answer: one committed `chart.yaml` per feature on both profiles, rendered from the model
  on the event profile; events and schemas typed with JSON Schema, routes as OpenAPI operations, ports as
  names with typed inputs and outputs.
- [Should → theme E, "The shape of the target"] One stack for every AWS or Azure project is too much for an
  internal tool. Answer: two shapes per target, skiff and liner, chosen from the product state and who uses
  it; moving up is a converge step; today's stack is the liner and stays as it is for products.
- [Should → theme A, "Which languages 2.0.0 ships with"] Which languages must exist at 2.0.0. Answer: all six.
- [Should → section 11] Effort per phase, the first dogfood product, the out-of-scope list and the token
  baseline. Answer: sizes in slices in the implementation plan; no real product is migrated before 2.0.0, the
  fixtures prove section 6 and a two-context greenfield at phase 7 is the first measured product; the
  out-of-scope list and the baseline are written in section 11.
- [Blocker → theme D, "The bridge"] How a click on the dashboard becomes a `told` line. Answer: `slipwai
  bridge` serves the page locally from the harbourmaster's seat and its controls post to it; the Pages copy is
  the same page without controls.
- [Should → section 1, theme D] Where the logs live. Answer: `.slipwai/logs/`, git-ignored, synced by the
  harbourmaster through `refs/slipwai/logs`; only what they render is committed.
- [Should → theme D, "The telegraph"] Whether the numbers under a position can be tuned alone. Answer: yes,
  `slipwai telegraph --set` and `/model-delegation-settings`; the board shows the position as adjusted.
- [Nice → section 2, "The problem in one line"] A one-line problem statement: version 1 delivers one product well with one
  runner, and gets no faster when people or machines join; its gate grows with every language. The cost of
  doing nothing is the experiment's numbers: 104 hours and 180M tokens per accepted slice at the median, and a
  gate nobody runs locally.
- [Nice → theme D, "Ids and shared files"] Log lines carry `v: 1`; a reader refuses a line from a newer format and names the
  upgrade. Logs under `.slipwai/logs/` are kept for the life of the feature and archived into the feature's
  directory when it closes, compressed, so the bill and the decisions stay auditable.
- [Nice → theme D, "The fleet board"] The push for parks, banked fires and stalls uses the harness's own notification
  hook where it has one, and otherwise a webhook URL in `harbour.json`, which covers Slack, Teams and a phone.
- [Nice → section 11, slice 1.6] Section 1 of this plan is extracted into `GLOSSARY.md` at the repository root
  in phase 1, so the `wtf` skill and every session read one glossary.
- [Nice → section 11, slice 8.6] Version 1 users hear about version 2 from the 2.0.0 changelog entry, the README
  rewrite, and a final 1.5.x release whose `slipwai upgrade --check` names 2.0.0 and its migration page.
- [Nice → section 11, "Who does the work"] The plan assumes one person with agents, and a second person or machine
  joining from phase 5 to prove the fairways. The slice sizes are for that team; a larger one shortens the
  calendar, not the slice.

All six nice-to-haves were accepted as written on 2026-10-06 and moved into the sections they name.

Open: none. Every blocker, should-address and nice-to-have found on 2026-10-06 is closed. Section 9 has no
open decision left either.

## 11. The implementation plan

**Progress: 26 of 83 slices done** — phase 1 6/6, phase 2 7/9, phase 3 13/19, phase 4 0/7, phase 5 0/17, phase 6 0/6, phase 7 0/7, phase 8 0/6, phase 9 0/6. Written by `scripts/progress.py` from the history; run `make progress` after a slice merges.

This section turns section 7's phases into slices. A slice here is one pull request to the fork's `main`: a few
hours of work, one module or one skill, reviewed and refactored before it merges, with the fast checks per
increment and the full gate before the merge (section 8). Every slice names the commit it comes from:
upstream `main` at `e1a9e43` (1.5.2.dev0) or `slipwai-cruise-2` `main` at `c6f1e74`. "New" means written for
version 2.

**Who does the work.** The plan assumes one person with agents, and a second person or machine joining
from phase 5 to prove the fairways. The slice sizes are for that team; a larger team shortens the calendar,
not the slice.

**Sizes are estimates, not commitments.** A slice is sized S (a session), M (a day), or L (two to three days,
and a candidate for splitting). The first two phases calibrate the rest: after phase 2, replace the sizes below
with the measured median, and keep doing so.

### Out of scope for 2.0.0

- New targets (nothing beyond AWS, Azure and `none`), new frontends, new axes, new profiles.
- A hosted service of any kind. The bridge's writable copy is a local server; the chandlery is static files.
- Mobile or native clients for the bridge.
- Replacing Spec Kit. Version 2 pins it as version 1 does.
- Forges other than GitHub and Gitea for the harbourmaster's push and fetch.
- Signing packages with anything beyond the trust model decided in section 9.
- Any change to what a generated project's `make verify` checks, beyond `make unit` and the two-gate split.

### The first products

- **No real product is migrated before 2.0.0.** Decided 2026-10-06. Section 6 is proven by the generated
  fixtures in `make test-migration` only: every profile and backend, a split, two slices implemented, one
  claimed, flags in both states, and the adopted fixtures. The first real migration happens after the release,
  and MANDA (37 slices, five lanes, event profile) is the natural first candidate then.
- **The first greenfield is a small product generated with the 2.0.0 keel at phase 7**, two bounded contexts
  by design, so that two captains on two machines can be proven on a product that was never version 1.
- **The fork itself is not driven by the loop** (section 7). It is a dogfood for the keel's verbs and the
  skills, not for the captain.

### The baseline

The token target in theme B, half the experiment's median per accepted slice, needs a baseline measured the
same way the fleet board will measure it. The baseline is the experiment's own `benchmark.md`, recomputed in
phase 1 on 2026-10-06:

| | Input tokens per slice |
|---|---|
| Median, the 18 accepted slices of 19 | **128.6M** |
| Mean, the same 18 | 140.0M |
| Range | 34.3M (S18) to 323.2M (S10) |
| All nineteen slices together | 2.66B |

So the 2.0.0 target is **a median at or below 64M input tokens per accepted slice**. Input here is prompt
plus cache read plus cache creation, which is what the experiment counted and what the fleet board will
count, so the two numbers are comparable. Three cautions on the baseline. Eight of the nineteen slices have
an unread session, so their figures are floors and the true median is higher than 128.6M — the target is
conservative by however much that is. S08, the one slice never accepted, is left out, and it is also the
largest-scoped: excluding it flatters the baseline slightly. And a token is not a price; the model mix
moves, and the comparison is like-for-like only against a run that counts the same way.

The first measured comparison is the phase 7 greenfield, two bounded contexts by design. Until then the
numbers come from the benchmark bracket version 1 already writes, on whatever generated project phase 5 runs
against.

### Phase 1. The keel's gate

| Slice | What | From | Size | Done when | Status |
|---|---|---|---|---|---|
| 1.1 | `pyproject.toml`, `VERSION` at `2.0.0.dev0`, `requirements-dev.txt`, the `slipwai` launcher, and `src/slipwai/` as `__init__`, `__main__` and a `cli.py` that answers `--version` | upstream | S | A checkout, an editable install and a built wheel all print `2.0.0.dev0` through `slipwai`, `python -m slipwai` and `./slipwai`; ruff, mypy and `tests/test_cli.py` are green | done |
| 1.2 | `Makefile` with `lint`, `typecheck`, `unit`, `test` and `verify`, and `scripts/verify` behind them; `verify` is lint, typecheck and test, and `unit` is the fast half, named by a `SLOW` list | upstream, `unit` new | S | `make verify` green from a clean checkout, `.python-tools` installed on demand; `make unit` runs the fast tests alone | done |
| 1.3 | `scripts/check-structure.py` with its tiers, `import-surface.txt` as the list it reads, and `check-structure` added to the `Makefile` and to `verify` | cruise-2 | M | The gate refuses an import against the direction, a cycle, an oversized module, a missing docstring, a keel import of a package and a package import off the surface, each proven by a test; the surface list is empty and held | done |
| 1.4 | CI: `verify.yml` with lint, typecheck, structure and the suite on Linux, macOS and Windows, plus an install-and-ask-its-version smoke on each; no matrix, no languages. WSL is deferred — see below | upstream, cut down | M | Green on the fork under Actions, on all three platforms | done |
| 1.5 | `AGENTS.md` for the fork: section 8's rules, the two-gate table, how to bring a module back, and nothing about versioning yet; `tests/test_agents.py` holds it to section 8 | new | S | A session reads it and knows the rules; a rule added to the plan and not to the page fails the gate | done |
| 1.6 | `GLOSSARY.md` at the repository root, written from section 1 by `scripts/glossary.py`, with `make glossary` and a `--check` the suite runs | new | S | The `wtf` skill and every session read one glossary, and it cannot drift from the plan without the gate saying so | done |

Depends on: the fork public (section 7). Phase 5 may start when 1.2 is green.

**WSL, and why 1.4 leaves it out.** Running the gate inside real WSL under Actions needs a third-party
action to install a distribution, and what it would then prove is Linux, which the Linux leg already
proves. The thing that is actually particular to WSL is path translation: a checkout on the Windows side
read through `/mnt/c`, where a path is a Windows path to some tools and a Linux path to others. The keel
has nothing that translates a path yet. WSL gets its own job in phase 3, with `./init` and the generated
launcher — the first code where the distinction can go wrong. Decided 2026-10-06.

### Phase 2. The registry and the chart

| Slice | What | From | Size | Done when | Status |
|---|---|---|---|---|---|
| 2.1 | The seven package repositories under `ROBCOATVG`, public, each with its history; `slipwai-language-java-spring` built from the experiment's `slice/S10-java-spring` lineage rather than the empty placeholder | cruise-2 | M | Seven public repositories, each with its history, each secret-scanned in tree and in history | done |
| 2.2 | `assets.py` as the path head, `registry.py`, `family_only.py`, `docs/backend-protocol.md` and their tests | cruise-2 | M | The registry answers Members for a fake package in tests, and the contract page and `PROTOCOL` cannot drift | done |
| 2.3 | `catalog.json` with no backends, `catalog_merge.py`, `catalog.py` split into what the catalogue is and `catalog_checks.py` for what makes one valid, the `Fault` boundary, and `assets/targets/` so the managed targets have the infrastructure the catalogue claims | cruise-2 | L | A fragment merges; a duplicate backend is refused with one line; the shipped catalogue validates with nothing installed | done |
| 2.4 | `versions.py`, `language_shape.py`, `language_directory.py`: the package directory, read and admitted in two phases | cruise-2 | L | A package directory loads whole or not at all; a bad one reports every fault in one line | done |
| 2.5 | *Moved to phase 3 as 3.9 — see below.* | | |  |
| 2.6 | *Moved to phase 3 as 3.8 — see below.* | | |  |
| 2.8 | The catalogue's validators, which `catalog.py` reads: `features.py`, `targets.py`, `extensions.py`, `axes.py`, and `assets/backing-services/prune.py`, the one asset tree the keel reads for itself | cruise-2 | L | Each refuses a malformed option, entry or extension, named by axis and option; nothing in them names a language. The whole-catalogue checks are 2.3's, with the `catalog.json` they mirror | done |
| 2.9 | `loaded.py`, `registry()`, and `inside`/`located` in `assets.py` so a package reads its own `assets/` and nothing else | cruise-2 | M | `registry()` builds once per process and is empty with nothing installed; a faulty package is a line and not a crash | done |
| 2.7 | The one refusal shape: `errors.py` with `Fault`, `Refusal` and `refuse`. **Runs before 2.3 and 2.4**, not after them | new + upstream | M | Every refusal in 2.3 and 2.4 goes through it; the experiment's nine wording-test files collapse to one table | done |

Depends on: phase 1. 2.1 can start on day one.

**How phase 3's slices are cut, and why not by assembly order.** `docs/bring-back.tsv` records what
every module of the experiment imports and which asset trees it reads; `make next` reads it against this
keel and says what is buildable. Run on 2026-10-06 with phase 2 complete, it gives 157 modules in
fourteen waves, and it contradicted two slices outright. 3.1 bundled `layout.py`, which waits on nothing,
with `toolkit.py`, which is ten waves later and needs two asset trees. 3.2 paired `services.py` with
`scaffold.py`: `services` is in the first wave and `scaffold` imports forty modules and is in the last
but four. Assembly order — the order `scaffold.project_files` puts a project together in — is not
dependency order, and cutting slices by it is what produced those two.

So the slices are cut against the waves, and `make next` is how the next one is chosen. The ledger is
data, re-read rather than remembered: `scripts/bring-back.py --check` runs in the gate and fails when the
keel holds a module the ledger does not know, so the next reading is never stale.

**What 3.9 can and cannot prove, and why that is right.** The conformance suite runs against the toy
on every commit, which is the keel's half of the bargain: a package's own CI is then running something
known to work. Two of its seven checks are generation probes and stay red until `generate` exists at
4.1, which is honest — the suite is reporting that this keel cannot yet generate, because it cannot.
The matrix cannot run against the toy at all: the toy answers no HTTP option but `none`, so there are
no variants to generate and nothing to run a native gate against. That is the toy being inert by
design, not a gap. The matrix is proven in a package's own CI, which slice 3.7 already owns, and its
refusal now names the toy's missing transport and points at the suite that does hold a package like it.

**Why 3.8 runs before 3.4.** It was last in the phase, after the targets and the frontends. By the end
of 3.3z thirty-one tests were skipped on it, nearly all of them the suites that generate a project —
the keel could assemble one and nothing had watched it do so. Pulling it forward cost an afternoon and
found three things the same day: `assets/backing-services/` had come in with only its pruner, so a
generated project had no `docker-compose.yml`; every `skipUnless(pinned())` became true at once, which
is a guard that stops guarding exactly when a package arrives; and four of this repository's own tests
asserted "with nothing installed" rather than an invariant. None of those would have been cheaper after
three more slices had been built on top. Decided 2026-10-06.

**Why 2.5 moved to phase 3.** The conformance suite proves a package by generating a project with it:
`conformance/generation.py` reads `images` and `project.flag_route`, `probe.py` reads `examples`,
`rows.py` reads `services` and `project.backing_services`, `version_rule.py` reads `changelog`, and
`matrix/plan.py` reads `probes`. Six keel modules, all of them phase 3's. Its own done-when says it runs
against the template's toy package, and running against a package means generating with it. The harness
half — the entry points, the case classes, the runner — would build today, but shipping half a suite is
the carried gap rule 5 exists to stop. It becomes 3.9, after the parts land. Found on 2026-10-06 while
doing the slice, which closes phase 2 at seven slices rather than eight.

**Why 2.3 carries `assets/targets/` too.** `validate_targets` refuses a managed target with no
`assets/targets/<name>/` behind it — a catalogue entry with nothing behind it generates projects claiming
a destination they cannot reach. The first attempt was to ship the catalogue with only `none` and
`existing` and let 3.4 add the managed rows, which is the rule read straight. It does not work: the
pruner's tables name `aws` and `azure` per option, and the catalogue is held to the pruner, so trimming
the catalogue means trimming an asset that ships verbatim into every generated project and untrimming it
later. Copying the two target trees in — 47 files, unchanged — costs nothing and keeps both files whole.
3.4's work is their stacks, their docs and their validation tests, which is what its done-when always
said.

**Why 2.8 carries an asset, and why two of its checks are 2.3's.** `axes.py` and `targets.py` hold the
catalogue's tables against `assets/backing-services/prune.py` — the same tables kept in two places,
because a generated project prunes itself with the second and two implementations of one prune would be
two sets of bugs. So the keel's own copy of the pruner is a phase 2 dependency, not a phase 3 asset, and
it comes in verbatim; slice 3.6 reworks how its rows get there. The mirror also means `validate_axes` and
`validate_targets` cannot be tested against a catalogue built in a test — a synthetic one fails on the
mirror before it reaches the rule under test — so those two are tested in 2.3, against the `catalog.json`
they mirror. Found on 2026-10-06 while doing the slice.

**The order inside phase 2, which is not the order of the numbers.** Slice numbers are append-only
here — renumbering is what version 2 exists partly to stop — so the sequence is written out instead:

```
2.1  the repositories          2.7  the refusal shape       2.2  the registry
  └─► 2.4  versions, language_shape, language_directory
        └─► 2.8  features, targets, extensions, axes
              └─► 2.3  catalog.json, catalog_merge, catalog
                    └─► 2.9  loaded, registry()
                          └─► 2.5  conformance, matrix        then 3.8  the toy fixture
```

This was computed from the imports rather than guessed, on 2026-10-06, after 2.3 turned out to be
unbuildable in its written position for the third time in a phase: `catalog.py` reads `axes`, `targets`,
`extensions` and `catalog_merge`, `catalog_merge` reads `language_directory`, and `language_directory`
reads `language_shape` and `versions`. The catalogue is near the top of the graph, not the bottom. The
four validators had no slice at all — `catalog.py` imports them and nothing brought them back — so 2.8 is
new, and 2.9 takes `loaded.py` back off 2.4, where the previous correction had put it: `loaded` reads the
catalogue, so it cannot land with the directory.

**Why 2.6 moved to phase 3, and then stopped being about submodules.** Pinning the packages as
submodules makes `check-structure` read them,
and it refuses every import that is not on the surface. The six packages import 46 names across exactly
twenty keel modules — which is where the plan's "exactly twenty" comes from, read off them on 2026-10-06 —
and in phase 2 the keel has three of those twenty. Pinning them any earlier means either a red gate or a
surface that promises modules the keel has not got, and the gate refuses that too, by design. It becomes
3.8, after the parts land. `import-surface.txt` carries the other seventeen as comments meanwhile, so the
contract is visible before it is enforceable.

And 3.8 is no longer a pin. The keel reads one package — the template's toy, in-tree as a fixture — and
no first-party package at all, because a keel whose gate checks seven packages is a keel that cannot be
changed without them. The surface is still held in both directions: the toy proves the gate can read a
package, each package's own CI proves that package, and the keel proves every line of the surface names
a module it has.

**Why 2.1 no longer asks for CI.** Its done-when said "each with a green CI of its own". None of the seven
has a workflow: they were built inside the experiment, whose CI ran conformance over them as submodules.
Giving each its own CI needs `python -m slipwai.conformance` to exist, which is 2.5, and the packages
rebuilt onto the version 2 template, which is phase 2's build list. Slice 3.7 already owns per-package CI,
so 2.1 was holding a requirement that belonged to another slice and could not be met where it stood.

**Why 2.7 runs first.** Its own done-when says every refusal in 2.3 and 2.4 goes through the fault type,
which cannot be true if the fault type arrives after them. It is written before them and the numbering is
left alone: renumbering a slice is the thing version 2 exists partly to stop doing.

**Why 2.2 is not what it first said.** It named `registry.py`, `loaded.py` and `manifest/` as one slice.
They cannot be one: `loaded.py` imports `catalog`, `catalog_merge` and `language_directory`, which are 2.3
and 2.4, and `manifest/` imports `services`, `selection`, `versions` and `origin`, which are phase 3. So
`loaded.py` joins 2.4, where the loader it is part of lives, and `manifest/` moves to phase 3, with the
modules it reads. 2.2 instead brings `assets.py` — only its path head, because `registry.py` resolves a
package's root through it and nothing else in the keel can — and `family_only.py`, which `registry.load`
refuses by and which nothing else imports. Found on 2026-10-06 while doing the slice.

### Phase 3. The scaffold pipeline

| Slice | What | From | Size | Done when | Status |
|---|---|---|---|---|---|
| 3.1 | The parts that wait on nothing: `backends.py`, `naming.py`, `probes.py`, `layout.py`, `selection.py`, `origin.py`, `ecosystems.py`, `npm_workspace.py`, `changelog.py`, then `services.py` | upstream + cruise-2 | L | `make next` shows the first wave empty; each module is in a tier and the gate is green after every one | done |
| 3.2 | `assets.py` grown to the asset trees, `examples.py`, `tooling.py`, `capabilities.py` and `toolkit.py`: the first slice that reads an asset tree | upstream | L | Toolkit files materialise for both profiles | done |
| 3.3 | The `project/*.py` parts, cut against `make next` rather than against assembly order. Each group below is one slice, and the groups are named as they are reached rather than guessed in advance — what is ready changes as modules land | upstream | 5 × M | After each group, `make starters` diffs empty against cruise-2 for the variants that group touches |  |
| 3.3a | The parts that write pieces of a repository: `project/`, `pruner`, `flags`, `flag_route`, `entry_stores`, `shared_packages`, `compose`, `ci_services`, `provisioning`, `repository`, `rules` | upstream | M | Each holds its mechanism with no language named; the `E501` ignore for embedded file content is back | done |
| 3.3b | The parts that write the ladder into a project: `drive_settings`, `demo_stop`, `adversary`, `mutation`, `benchmark`, `converge_stage`, `design_stage`, `docs_index`, `evolving`, `parallel_slices`, `agent_targets`, `model_targets`, `model_to_code` | upstream | M | The two widths are written and checked: `delegate` is story, rule or task, `cycle` is rule or example, and `story` is never a cycle | done |
| 3.3c | The parts that write `/cruise` into a project, and the ones `./init` writes: the seat commands, the stop table, the unblock section, `whats_next`, `where_are_we`, `init_languages`, `init_production`, `native_commands`, `languages` | upstream | M | The harness output is repeated verbatim rather than summarised; nothing catastrophic is missing from the page that forbids it; a managed target adds stops an unmanaged one has not | done |
| 3.3d | The parts that wire a project together: `composition`, `openapi`, `renovate`, `pins`, `agent_settings`, `adopted_ci`, `adopted_targets`, `backing_service_prose`, `catch_up_command`, `run_skill`, `add_commands` | upstream | M | Every pin is a tag and not a range; nothing is both allowed and denied in a generated project's permissions | done |
| 3.3e | The parts that write how a project is run: `cruise`, `ci_workflows`, `init_script`, `backing_services`, `design_page`, `drive_adoption`, `existing`, `integration`, `pin_commands` | upstream | M | Every line the runner parses is declared in one place; a value with a quote in it cannot close the quote around it in `./init` | done |
| 3.3f | The rest of the parts the ledger unlocks: `stage_models`, `agents`, `commands`, `docs`, `adopted`, `decisions`, `guidance`, `event_model`, `frontend`, `gitignore`, `biome`, `skills_page` | upstream | M | Every rung section 5 draws is in `STAGES`; a read-only stage writes nothing; the skipper has a role of its own | done |
| 3.3g | The answers tier: `convergence`, `delivery_facts`, `images`, `programme`, `quick_wins`, `uncommitted`, `unlabel`, `wrappers`, `preflight`, `upgrade` | upstream | M | Every reader of a repository the keel did not make has a nothing case; every builder and index is pinned and https | done |
| 3.3h | The last of the parts: the target docs and stacks, `makefile`, `readme`, `production`, `deploy_workflow`, `infra`, `ground_command`, `structure_page`, `strangle_command`, and `strategy`, `survey`, `structure`, `next_steps` beside them | upstream | M | `make next` lists no `project.*` module as waiting | done |
| 3.3z | `scaffold.py`, last of the parts and not first: it imports forty of them. With `manifest/`, `adopt_report`, the `cli_*` prompts and `tests/support.py` | upstream + cruise-2 | L | `project_files()` is importable and the suites that generate a project are in the tree, skipped on the one thing they still lack | done |
| 3.8 | The template's toy package in-tree as the one fixture the keel's own gate reads, and the import surface filled in to the twenty modules a package imports (was 2.6) | cruise-2 | L | `check-structure` reads the toy and finds no import off the surface; the surface is twenty lines and every one names a module the keel has; the keel pins no package; and every suite that generates a project runs against the toy — `test_services`, `test_layout`, `test_toolkit`, `test_harness`, `test_npm_workspace`, the flag gate and the prune rows | done |
| 3.4 | Targets `aws` and `azure`, their stacks and docs, as the **liner** shape | upstream | L | Stack validation tests green |  |
| 3.4b | The **skiff** shape for both targets: a Lightsail container service and a scale-to-zero Container App, one environment, the shape question in the interview, `converge --shape`; the compute named in one row of the target's table, not spread through its stack | new | L | Both shapes validate against the real providers; a slipway project generates a skiff by default; changing a skiff's compute is one row and its stack file |  |
| 3.5 | Frontends and backing services, the `react-vite` npm-workspace contract | upstream + cruise-2 | M | The frontend variants match |  |
| 3.6 | The pruner with rows emitted as data | cruise-2 | S | `scripts/backing-services.py` in a generated project carries no language name |  |
| 3.7 | `make starters`, and the full matrix per package run from each package's CI against a pinned keel, never from the keel's | cruise-2 | M | The keel's gate stays under ten minutes and reads one package, the toy; each package's CI proves its own variants |  |
| 3.9 | `conformance/` and `matrix/` as `python -m` entry points (was 2.5) | cruise-2 | L | `python -m slipwai.conformance packages toy` runs in the gate and its five static checks pass; the matrix refuses the toy by name and says what to run instead. The two generation probes need the `generate` verb and light up at 4.1 | done |

Depends on: phase 2.

### Phase 4. The verbs

| Slice | What | From | Size | Done when | Status |
|---|---|---|---|---|---|
| 4.1 | `generate` and the interview, menus from the registry, the offer to install | upstream + new | M | A fresh project from an empty machine with one answer sequence |  |
| 4.2 | `adopt`, the survey, `converge` | upstream | L | The adopted fixtures survey as before |  |
| 4.3 | `add-service`, `add-frontend`, `describe-service` | upstream | M | Mid-flight additions match cruise-2 |  |
| 4.4 | `./init` and the installer, with the language record read and reported | upstream + cruise-2 | M | A clone with a missing language is told what to install |  |
| 4.5 | `slipwai list`, `slipwai search`, `slipwai show`, `slipwai install`, `language upgrade / remove`, the index client | cruise-2 + new | M | Search and install from a local index end to end; `search` with no term lists every channel |  |
| 4.6 | `upgrade` without its 1.x paths | upstream | S | The keel upgrades itself from the index |  |
| 4.7 | The standalone executable, bundling no language | upstream | M | `make test-executable` green on four platforms |  |

Depends on: phase 3.

### Phase 5. The toolkit and the loop

| Slice | What | From | Size | Done when | Status |
|---|---|---|---|---|---|
| 5.1 | The skills, renamed to the vocabulary where a name changed, `docs/rename.json` begun | upstream | M | Every skill present; the rename table has a row per rename |  |
| 5.2 | The commands and agents, the ladder in `drive.md`, the stop table, and `.specify/drive.json`: the `delegate` and `cycle` widths, the refusal of `story` as a cycle unit, and the fallbacks that run a slice narrower than the setting asks | upstream | L | `/drive` runs one slice to a demo on a generated project, red-green-refactor per the configured width, and a slice with no story tag falls to `rule` rather than failing |  |
| 5.3 | Fairways: the `## Fairways` table in the split, `/drive fairway=<name>`, the boards grouped by fairway | `slipwai-workstreams` | M | Two fairways on one machine, merges independent |  |
| 5.4 | The chart: `chart.yaml` schema, `make chart` on the event profile, `/chart` on the standard profile, `check-chart` | new | L | Both profiles produce a chart a reader can diff |  |
| 5.5 | Clearance and the one-setter-per-mark rule in `check-model` and `check-chart`; typed attributes and `examples.md` at the split | new (#32) | M | A fresh fairway fans out on its first iteration |  |
| 5.6 | `check-slice-scope` reads the chart for owned paths on both profiles | upstream + new | M | The standard profile holds a context boundary |  |
| 5.7 | Two gates: `make unit` in generated projects, the ladder's fast checks per increment, the full gate before `main` | new | M | A slice's increments never run the full suite |  |
| 5.8 | Review and refactor as a ladder stage, with a review role in the model table | new | M | A slice merges with review findings closed |  |
| 5.9 | Adversary once with a bar, mutation as a gate, stage budgets, stow, the careen | new (#29) | L | A stage over budget stows; CRITICAL never does |  |
| 5.10 | Ids with the fairway in them; per-fairway `decisions.md`, adversary log, register; rendered aggregates on `main` | new | L | Two fairways decide in parallel and nothing renumbers |  |
| 5.11 | Composition root rendered from the chart; one file per event with a rendered index | new | M | Two slices add an event each and merge without touching one line |  |
| 5.12 | The four release modes, the product state in `project.json`, the shape beside the target, flags at the entry wiring only, the hygiene gate | new | L | A slipway product runs the loop with no flag reader; an in-service one keeps every guarantee |  |
| 5.13 | The deck log and harbour log formats, written by `/drive`; `.slipwai/logs/` ignored; `refs/slipwai/logs` sync | new | M | A run's status is answerable from the logs after the fact |  |
| 5.14 | Berths: `slipwai berth add / status / remove`, allocation policy, the sandbox | new | L | Two berths on one machine do not collide on ports or databases |  |
| 5.15 | The decision ceiling, bounded waits, the inbox read at every boundary with receipts | new | M | A message is read within one boundary or forces one |  |
| 5.16 | Domain knowledge for the skipper | new (#27) | M | A fact in `.specify/domain/` is cited, not guessed |  |
| 5.17 | Example mapping as a stage of **both** profiles: `example-map` moves out of `assets/profiles/event-modelling/commands/` into the toolkit, deriving its examples from the model on the event profile and writing them from the chart and the story on the standard one; the demo stage reads what it wrote | upstream + new | M | A standard-profile slice reaches its demo with examples a stage produced, and `/drive` refuses to implement a slice whose map is empty |  |

Depends on: 1.2 for 5.1 and 5.2; phase 4 for a generated project to run against. 5.3 to 5.16 are the slices
most worth running in two fairways themselves, once 5.3 exists.

### Phase 6. The chandlery

| Slice | What | From | Size | Done when | Status |
|---|---|---|---|---|---|
| 6.1 | The extension package shape: `extension.json`, `init.py` as the entry point, and the conformance profile for the six obligations of `docs/extensions.md`; `codegraph`, `uipro` and `ux-gates` out of the keel | new | L | `./init --extension codegraph` installs from a directory package, and the keel names no extension in its own code |  |
| 6.2 | The index schema with publishers, checksums, the signature field, descriptions and tags; the public channel as a Pages site | cruise-2 + new | M | `slipwai search` and `slipwai install` read it for both kinds |  |
| 6.3 | A private channel per organisation, `SLIPWAI_LANGUAGE_INDEX` generalised to `SLIPWAI_CHANDLERY` | cruise-2 | S | An organisation's index serves its own packages |  |
| 6.4 | `slipwai package new / check / release / register`, branching on the kind answer, and `make release` in the template behind them | new | L | One language package and one extension package, each made by `new` on an empty machine, pass `check`, release, and register into a local channel without a hand edit |  |
| 6.5 | Signed releases and the trust store: Sigstore or minisign verification, `trust.json`, the `ROBCOATVG` root, the confirm-once prompt, `unsigned` in `slipwai list` | new | M | A new publisher is confirmed once and then installs silently; a mismatched signature is refused; a hand-placed package loads and says `unsigned` |  |
| 6.6 | The public channel's contribution path, which `slipwai package register` targets: the index repository, its CI (signature matches publisher, conformance passes, no name collision), and the contributor page | new | M | A package from outside `ROBCOATVG` is listed by a merged pull request and installs with one confirmation |  |

Depends on: phase 4. Runs beside phase 7.

### Phase 7. Captains and the harbourmaster

| Slice | What | From | Size | Done when | Status |
|---|---|---|---|---|---|
| 7.1 | The harbourmaster process: the only writer of the harbour log, the log sync, berth allocation, credentials | new | L | Two captains' marks reach each other through the harbour log |  |
| 7.2 | The captain: the outer loop for one fairway, clearance, claim, dispatch, boundaries, heartbeat, ending a wedged stage | new + `cruise.py` | L | One fairway runs unattended for a day with every line in its deck log |  |
| 7.3 | The telegraph: positions, `harbour.json`, `--set` for the numbers, `/model-delegation-settings` for the model role per stage, the `delegate` and `cycle` widths from `.specify/drive.json` shown and set alongside them, banking the fires in order | new | M | Over budget, the run slows in the fixed order before it stops; every number and role the telegraph groups can also be set alone |  |
| 7.4 | The fleet board: `slipwai fleet`, `fleet watch`, the rendered page | new | M | Every column folds from the logs; a stalled berth is told from a finished one |  |
| 7.5 | The bridge: `slipwai bridge` local server with controls, the read-only Pages copy | new | L | A question answered from the page becomes a `told` line |  |
| 7.6 | The harness registry rows for Claude Code, Codex, Cursor, Gemini CLI, OpenCode and Kiro; `unproven` until run | upstream + new | M | Each row says how it is invoked and which hooks it has |  |
| 7.7 | Retire `cruise.py`; `/cruise` starts captains | new | S | No runner left in the toolkit |  |

Depends on: 5.13 and 5.14. 7.1 first, then 7.2, then the rest in any order.

### Phase 8. 2.0.0

| Slice | What | From | Size | Done when | Status |
|---|---|---|---|---|---|
| 8.1 | `AGENTS.md`'s versioning rules, `changelog.d/`, `make release`, `make changelog`, and `requirements-build.txt` and `requirements-publish.txt`, which come back with the machinery that proves them rather than sitting unused from phase 1 | upstream | M | The fork's own release machinery is green |  |
| 8.2 | One 2.0.0 changelog entry written from the fork's history | new | M | Every user-visible change since 1.5.2 is in it, with its catch-up |  |
| 8.3 | `migrate`: base from an installed 1.x, languages first, the rename table, in-flight work as data (section 6) | upstream + cruise-2 + new | L | `make test-migration` green for every profile and backend and the adopted fixtures |  |
| 8.4 | The release backstop: one job that runs the matrix across the published packages against the keel about to ship, and the root matrix retired | cruise-2 + new | M | A keel release is refused when a published package fails against it; no per-commit job reads a package |  |
| 8.5 | `make release` to 2.0.0; the merge back to upstream; the Gitea decision | new | M | `v2.0.0` tagged, published, and upstream `main` is version 2 |  |
| 8.6 | A final 1.5.x release whose `slipwai upgrade --check` names 2.0.0 and its migration page | upstream | S | A version 1 user is told where version 2 is and what moving costs |  |

Depends on: everything before it.

### Phase 9. The README and the docs

| Slice | What | Size | Done when | Status |
|---|---|---|---|---|
| 9.1 | The five pages of section 7, phase 9, written from a real session transcript | L | A first-time reader reaches a demoed slice in fifteen minutes following them |  |
| 9.2 | The reference pages under `docs/reference/` | L | Every rule the plan names has a page |  |
| 9.3 | The captures: the bridge, the fleet board, a demo-stop board, a `/chart` output | S | From real runs, not drawn |  |
| 9.6 | **From a spec to a delegate**: one figure per profile following a single feature all the way down — spec, model or chart, split into slices, example-mapped into rules and examples, cleared, claimed, and handed to a delegate at the configured width. Drawn, not captured | new | M | A reader who has never used slipwai can point at where a slice comes from and at what one delegate is handed; both profiles are the same figure with two boxes different |  |
| 9.4 | `make test-docs`: every command in the first three pages run against a fresh generation | M | The README cannot drift |  |
| 9.5 | The five maintainer skills in `.claude/skills/`, rewritten for version 2's shape: `add-language`, `add-framework` and `add-extension` as prose around the four `slipwai package` verbs and the two package shapes; `add-target` for the skiff and the liner; `add-backing-service` for a catalogue that no longer holds backends | new | L | A contributor who has not seen this repository publishes a package by following one skill; no skill names a step a verb already does; none describes a file version 2 does not have |  |

### Order, and what runs in parallel

```
Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4 ──► Phase 6 ──┐
   │                                       │              ├──► Phase 8 ──► Phase 9
   └──► Phase 5 (toolkit, from 1.2) ───────┴──► Phase 7 ──┘
```

Phase 5 starts as soon as 1.2 is green and runs beside phases 2 to 4 on the toolkit assets, which do not import
the scaffold; its slices from 5.3 on need a generated project, so they wait for 4.1. Phases 6 and 7 run beside
each other. Nothing in phase 8 starts before phases 6 and 7 are done. Phase 9 is last.

### Risks the plan carries, and where each is caught

| Risk | Caught by |
|---|---|
| The scaffold parts drift from cruise-2's output as they come back one by one | 3.3's `make starters` diff after every group |
| The two-gate split hides a failure until the merge | 5.7's rule that the full gate runs on the rebased branch, plus CI |
| Sandbox per berth on native Windows is harder than it reads | 5.14 proves it on all four platforms before 7.2 depends on it |
| The chart on the standard profile is a design nobody has used | 5.4 is sized L and lands before 5.5 and 5.6 build on it; MANDA (event profile) does not depend on it |
| The migration of in-flight work meets a case section 6 did not foresee | `make test-migration`'s fixtures carry a claimed slice and both flag states; the first real migration is after 2.0.0, on a branch, with `--check` first |
| The token target is missed | The baseline above, measured at 7.x on the greenfield, with time to tune the telegraph positions |
