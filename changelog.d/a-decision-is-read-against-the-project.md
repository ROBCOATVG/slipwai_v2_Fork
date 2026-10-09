MINOR

**A decision is read against what the project already does, and the record says which authority answered.**
`/cruise` named three things a question could be settled by without spending a delegate: the standing
entries, the specification, the constitution. All three are documents this method owns.

A generated project ten slices in, and an adopted repository on its first day, both hold conventions that
none of them names — how this codebase already publishes, how one handler reaches the next, how a migration
is named. A decision taken without those is how a codebase ends up with two ways of doing one thing, each
defensible on its own. So the project's own grain is the fourth authority, the host may settle a question it
answers, and the procedure says where to find it: `docs/architecture.md` and the code itself in a generated
project, `structure.md` and the survey in an adopted one.

Every decision entry's **Why** now carries `Read against:` — which of the four answered, or `the method's
default` where none did. It is a clause inside the field rather than a tenth bullet, so an entry already
written is still the right shape, and `make check-decisions` asks for it.

**Catch-up:** `slipwai migrate` brings the command and the gate. An entry written before this has no
`Read against:` and the gate will name it; add the clause, or say `the method's default` where that is the
honest answer.
