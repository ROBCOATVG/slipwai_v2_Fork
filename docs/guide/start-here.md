# Start here

**Fifteen minutes from nothing to a product repository with one slice demoed.** This page is the first
ten of them: install the command, answer its questions, and watch the gate go green. The next page,
[your first feature](first-feature.md), is the other five.

You need Python 3.10 or newer, Git, and — for a TypeScript or JavaScript project — Node. Nothing else has
to be set up first.

---

## 1. Install the command

```sh
uv tool install slipwai
```

`pipx install slipwai` and `pip install --user slipwai` work too. There is also a standalone executable on
the releases page for a machine with no Python toolchain, which scaffolds with Git alone.

Check it arrived:

```console
$ slipwai --version
slipwai 2.0.0
```

## 2. Get a language

The command itself knows how to scaffold a repository. It does not know TypeScript, or Python, or Go —
those come from the **chandlery**, which is the index of packages it can install from. Look in it:

```console
$ slipwai search
  go            language  1.0.0         available  backends: go
  java          language  1.0.0         available  no description
  java-quarkus  language  1.0.0         available  backends: java-quarkus
  java-spring   language  1.0.0         available  backends: java-spring
  python        language  1.0.0         installed  backends: python
  typescript    language  1.0.0         available  backends: typescript
```

The last column is what each package *answers*, and `slipwai search postgres` searches that rather than the
name — which is usually the search you want: you know you need something that will talk to Postgres for
you, not what it is called.

Install one:

```sh
slipwai install typescript
```

It says where the package came from, which version, who published it, and whether their signature is one
you have trusted. The first time you install from a publisher you have not met you are asked once, and the
answer is remembered; everything after that is silent. The file's checksum is checked against what the
index listed every time, whoever published it.

## 3. Generate the repository

```sh
slipwai generate
```

It asks one question at a time and shows a default for each, so Enter all the way through is a working
project. These are the questions, in the order they come:

```console
$ slipwai generate
Create a new product monorepo. Press Enter to accept a shown default.
Project name: bookings

Delivery foundation:
  event-modelling — Event Modeling — everything above, plus events as the source of truth, built one
    stamped slice at a time. Cost per slice stays flat as the system grows…
  standard — Standard — walking skeleton, executable test and the CD gate, over state-stored
    persistence. The cheaper start and the irreversible one…
Use Event Modeling? [Y/n]:

Production target:
  none — Local only — nothing is deployed anywhere; `make verify` is the end of the road
  aws — one ECS service per app, blue/green, RDS Postgres, Cognito, S3 + CloudFront, by OpenTofu
  azure — one Container App per app, PostgreSQL Flexible Server, Entra ID, Static Web Apps
  existing — this project deploys to infrastructure it does not own
Choose (none/aws/azure/existing) [none]:

Language (typescript) [typescript]:
Service name [service]: bookings
What does bookings own? (a sentence or two; Enter to decide later): Taking and changing a reservation.
Bounded contexts bookings holds, comma-separated [bookings]: booking, availability
Frontend (none/react-vite) [react-vite]:
Browser app name [web]:

Event store:
  Where events live. Every answer is an append-only log behind one port…

  memory — In-memory — zero infrastructure, loses all truth on restart…
  postgres — Postgres — append-only table, unique (stream, version) as the concurrency control
Choose (memory/postgres) [postgres]: memory

Staff authentication:
  …
Choose (none/keycloak) [none]:

Customer authentication:
  …
Choose (none/keycloak) [none]:

Output parent [~/code]:
created: /Users/you/code/bookings
```

A question with nothing to explain is the one-line form — `Language (typescript) [typescript]:`. One where
the answers need describing prints them first and then asks, which is why `Event store` and the two
authentication questions look different. In a terminal all of them are a list you move through with the
arrow keys; the typed form above is what you get in a pipe, a script, or a terminal that cannot be put into
raw mode.

**The first question is the one that matters, and it is the only one that is hard to undo.** An event log
folds down into tables whenever you decide it should, so a project can stop being event-sourced. State
cannot be turned back into history it never recorded, so "start standard and adopt events later where a
subdomain earns it" is an option that mostly does not exist. Every other answer here is a directory you
can regenerate, a service you can add, or an axis you can converge later.

Everything you were asked is written down in `project.json`, and nothing else keeps a second copy of it:
the Makefile, `docker-compose.yml`, the CI workflow and the gate scripts all read that one file.

## 4. Start the repository

```sh
cd bookings
./init
make verify
```

`./init` installs Spec Kit for whichever coding agent you use, and wires in the skills, commands and agent
types the profile needs. It reaches the network once, here, and never again.

`make verify` is the whole gate — lint, types, tests, the architecture checks, the model and the chart.
It is what CI runs, and it is green on a repository nobody has written a line in yet:

```console
$ make verify

verify: all gates passed
```

**That green is the point of the first ten minutes.** You now have a repository where the gate is a fact
rather than an aspiration, which is the only state from which "keep the main branch releasable" means
anything.

---

## What you just got

```
bookings/
  apps/bookings/        the service: domain, ports, adapters, tests
  apps/web/             the browser app
  docs/event-model/     model.yaml, and the diagrams and page rendered from it
  specs/                one directory per feature: spec, mock-ups, chart, slices
  scripts/              the gates, the agents, the event-model renderer
  skills/ commands/     what the coding agent is given to work with
  project.json          every answer you gave, read by everything above
  Makefile              make help lists the lot
```

`make help` lists every target with a sentence each. You do not need to read it yet.

## Next

→ **[Your first feature](first-feature.md)** — a specification, a model, a chart, a slice, and a demo you
watch happen.

Other pages: [a second person joins](a-second-person.md) · [let it sail](let-it-sail.md) ·
[bring an existing codebase](adopt.md) · [the vocabulary](../../GLOSSARY.md)
