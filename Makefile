# The keel's own local and CI entry points. There are two gates, not one, and this file is where the
# difference is spelled: `make unit` with `make lint` and `make typecheck` is what an increment inside a
# slice runs, and `make verify` is what runs once on the rebased branch before `main` and again in CI.
# Never the full gate in the inner loop — that rule cost the first attempt more than any other.
.DEFAULT_GOAL := help

.PHONY: help
help: ## Show the available targets
	@grep -hE '^[a-z][a-zA-Z0-9_-]*:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{ printf "  %-18s %s\n", $$1, $$2 }'

.PHONY: install
install: ## Install the pinned development tooling into .python-tools
	./scripts/verify --install-only

.PHONY: lint
lint: ## Run ruff over the keel's own source, scripts and tests
	./scripts/verify --lint-only

.PHONY: typecheck
typecheck: ## Byte-compile everything, then type-check it with mypy
	python3 -m compileall -q src scripts tests
	./scripts/verify --typecheck-only

# The suite, or a slice of it: `TESTS="test_registry test_cli"` runs those modules, `SKIP="test_registry"`
# every module but those. CI holds the gate in parallel jobs this way; `make verify` still runs the whole
# suite.
ALL_TESTS := $(patsubst tests/%.py,%,$(wildcard tests/test_*.py))
TESTS ?= $(if $(SKIP),$(filter-out $(SKIP),$(ALL_TESTS)),)
.PHONY: test
test: ## Run the keel's test suite, or a slice: TESTS="test_a test_b", or SKIP="test_a"
	$(if $(TESTS),PYTHONPATH=src:tests python3 -m unittest -v $(TESTS),PYTHONPATH=src python3 -m unittest discover -s tests -v)

# The fast half of the suite: everything that does not generate a project, shell out, or reach the network.
# A slice that adds a test of that kind adds its module to SLOW in the same commit, because the value of
# this target is entirely in it staying quick — an increment that waits on the full suite stops being run.
SLOW := test_generated test_chart test_chart_render test_slice_scope
UNIT_TESTS := $(filter-out $(SLOW),$(ALL_TESTS))
.PHONY: unit
unit: ## The fast tests only — the per-increment gate, with the slow modules left out
	$(if $(UNIT_TESTS),PYTHONPATH=src:tests python3 -m unittest $(UNIT_TESTS),@echo 'unit: no test modules yet')

.PHONY: glossary
glossary: ## Rewrite GLOSSARY.md from the plan's vocabulary (tests/test_glossary.py holds them in step)
	python3 scripts/glossary.py

.PHONY: skills
skills: ## Copy the toolkit's skills into .claude/skills for this checkout's own sessions (ignored by git)
	python3 -c "import pathlib, shutil; d = pathlib.Path('.claude/skills'); shutil.rmtree(d, ignore_errors=True); shutil.copytree('assets/toolkit/skills', d)"
	@echo "skills: .claude/skills written from assets/toolkit/skills — edit the toolkit, never this copy"

.PHONY: progress
progress: ## Tick off in the plan the slices the history says are done
	python3 scripts/progress.py

.PHONY: next
next: ## What can be brought back next, and what each remaining module waits on
	python3 scripts/bring-back.py

.PHONY: executable
executable: ## Build the standalone slipwai executable
	./scripts/build-executable

.PHONY: test-executable
test-executable: executable ## Build it, then prove it scaffolds with Git alone
	python3 scripts/smoke-executable.py dist/slipwai$(if $(filter Windows_NT,$(OS)),.exe,)

.PHONY: starters
starters: ## Materialise every starter combination under build/ for inspection
	python3 scripts/regenerate-starters.py

.PHONY: check-structure
check-structure: ## Fail when a module imports against the declared direction, cycles, or outgrows its budget
	python3 scripts/check-structure.py
	python3 scripts/bring-back.py --check

.PHONY: verify
verify: lint typecheck check-structure test ## Full local gate — the same one CI runs
	@echo
	@echo 'verify: all gates passed'
