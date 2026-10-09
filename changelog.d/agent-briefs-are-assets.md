PATCH

**The eleven agent briefs are assets now, and the scope they are held to is still generated.** Each type's
standing brief was a Python string literal, so `agents.py` reached its 350-line budget and was cut at a
paragraph boundary: `cruise_agents.py` exists because three more briefs would not fit, and the bosun's words
have been living in a file named for the cruise, where nobody reading about the bosun would look. They are
`assets/toolkit/agents/sail-*.md` now — one file per type, beside the skills and the commands, edited like
any other prose this repository ships.

What did not move is the frontmatter. `name`, `stage`, `writes` and `commands` are still generated from
`stage_models.STAGES`, because they are the scope every harness projection enforces: a brief that wrote
`writes: none` for itself could disagree with the table, and the harness would enforce whichever it was
handed. A brief that names one of those four fields is refused rather than merged.

This is also the first templated asset the keel has — everything else under `assets/` is copied byte for
byte — so it comes with the gate for that. A brief interpolates eleven named values and no others
(`{{make}}`, the paths the `/cruise` delegates read, two passages the ladder owns), the substitution is a
closed set rather than `str.format` so that a `${VAR}` or a JSON example in a brief is never an escaping
question for the person writing it, and `make verify` holds both directions: every token an asset names is
provided, and every value provided is named by some asset. An unresolved `{{make}}` shipped into somebody's
repository would read as a typo in the method, in a file that is valid markdown either way.

Nothing a project receives changed. The eleven generated files are byte-for-byte what they were, proved
against digests taken from the generator at the commit before the move and kept in
`tests/fixtures/agent-briefs.sha256`.

**Catch-up:** nothing. `agents/sail-*.md` in a generated project is the same text it was; regenerate or
not, as you like.
