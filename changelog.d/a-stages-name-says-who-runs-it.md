MINOR

**A stage's name now says who runs it, and that is how you can tell it has a delegate at all.** `/drive`'s
ladder has twenty-one stages and ten of them are sent to a fresh context with a scope the harness enforces;
the other eleven stay with you. Nothing in the name said which was which. `writes` and `commands` said it,
two columns further along, in a table nobody reads at three in the morning — and the only part of it a
person editing `.specify/models.json` ever sees is the key.

So every delegable stage is named for its purpose and then for the crew member who does it, and every stage
that stays on the host keeps the work's own name:

| Was | Is | Its delegate |
|---|---|---|
| `gaps` | `gaps-lookout` | reports what is missing and touches nothing |
| `tasks` | `tasks-quartermaster` | issues the stores in order |
| `implement` | `implement-shipwright` | builds to a plan that is already complete |
| `converge` | `converge-navigator` | says whether the course was held |
| `review` | `review-mate` | reads the work and signs nothing off |
| `adversary` | `adversary-privateer` | attacks under letters of marque, never repairs |
| `mutation` | `mutation-shipworm` | bores holes on purpose to see whether the hull leaks |
| `skipper` | `decide-skipper` | decides one product question as the owner would |
| `hand` | `demo-hand` | runs the demo as the actor |
| `bosun` | `unblock-bosun` | gets a blocked run moving |

The types in `agents/` take the same names (`drive-implement-shipwright`), and the whole-slice delegate is
`drive-slice-watch`. The purpose leads rather than the crew member, for two reasons: a delegate reads its own
job in the first word of its name, and the name a stage had before is still the start of the name it has now
— so `/drive`'s rungs still match the words the method uses for them.

Rung titles are untouched. **Implementation** is still **Implementation**; a title names the work and the key
now names who does it. The commands are untouched too: `/gaps`, `/adversary` and `/mutation` are what you
type, and Spec Kit still owns the plan, tasks and implement commands the ladder runs.

**Catch-up:** nothing you must do. A `.specify/models.json` still keyed `implement` is read under that name
and says so, `scripts/agents/models.py --set implement=fast` resolves to the new key, and a benchmark record
written before today is counted as the stage it was. `slipwai migrate` rewrites the table and the agent
files; the roles you mapped survive it, as every edit to a generated file does.
