MAJOR

**`/drive` is `/sail`.** One command runs the whole ladder, and the word for it is now the word the rest of
the vocabulary is in: a harbour, fairways, marks, berths, a captain, a telegraph — and a car.

```
/sail                     every ready slice of every fairway nobody holds
/sail fairway=booking     one lane
/sail BOK-01              one slice
```

`/sail` and `/cruise` are a pair, and the pair is the point: somebody is at the wheel, or nobody is.
Everything named for the old word follows it — `commands/sail.md`, `commands/sail-settings.md`,
`.specify/sail.json`, `scripts/agents/sail.py`, the eleven standing briefs (`sail-decide-skipper` and the
rest), and `SLIPWAI_SAIL`, which still replaces the whole command and still takes `<slice> <fairway>`.

The guide page about running unattended was called *Let it sail*, which would now name the mode it is not
about. It is **Let it cruise**, after the command it actually opens with.

There is no alias. A command with two names is two things to keep in step, and the whole of version 2 is a
break anyway — the one release where a rename costs nothing beyond reading this line.

**Catch-up:** `slipwai migrate` writes the renamed files and removes the old ones. A project that scripted
`SLIPWAI_DRIVE` renames the variable; nothing else in a generated project refers to the old name.
