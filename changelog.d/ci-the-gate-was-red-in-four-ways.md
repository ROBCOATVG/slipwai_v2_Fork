PATCH

**Four faults that only CI could see, and one of them was a real bug on Windows.** The keel's gate had been
red on every push for a day while it was green on a laptop every time — which is the failure mode the two
gates exist to prevent, so each is now checked where it broke.

- **`fleet list` and a second `fleet start` killed what they asked about on Windows.** `os.kill(pid, 0)` is
  a signal on Unix and `TerminateProcess` on Windows, where the signal number is the exit code and 0 is as
  fatal as any other. So the liveness check ended every process it was asked about and then reported that
  nothing was running. Windows is asked through the process handle now, and a test that starts a real
  process and asks twice runs on every platform.
- **The harbourmaster could not merge in a repository with no `user.name`.** A rebase that replays a commit
  writes one, and writing one needs a committer. It now says exactly that, with the `git config` that fixes
  it, instead of relaying nine lines of git's advice inside a refusal about something else.
- **PyYAML was never pinned.** Four tests read workflow YAML and three more read a chart or a model; they
  passed on a laptop that happened to have it and errored in CI. It is in `requirements-dev.txt`, and
  `make test` puts the pinned tooling on the path beside `src`.
- **`make model` needs a Chromium that will start.** The renderer's own sandbox cannot initialise on a
  runner, so `make test-docs` now *skips that one command with the reason* rather than failing — and CI
  passes `MERMAID_PUPPETEER_CONFIG` so it is checked rather than skipped.

**Catch-up:** `slipwai migrate` carries the Windows fix into a project's `scripts/agents/fleet.py`. On
Windows, `slipwai fleet` was reporting a run it had just stopped.
