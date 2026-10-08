"""The commands a person types beside a fleet that is running — `/cruise-watch`, `/cruise-status`,
`/cruise-stop`, `/cruise-tell` — and the watch seat itself, whose words `commands/cruise.md` also renders.

Each is a shell command and the rule for what to do with what it printed. The rule matters more than the
command: a harness folds a command's output to a few lines, so a status or a feed reaches a person only through
the reply, and each of these says so in the same words the watch seat uses.

**All four used to speak to the runner**, which held the state of the run in its own files — a pid, a feed, an
inbox, a cursor — and could therefore only ever report one machine's work. They speak to the logs now. The
difference shows in what each command can be asked while nothing is running: `tell` writes a line a captain
reads whenever one is next lit, `watch` sits on files rather than on a process, and `status` says which
processes are up without pretending that is the same question as what the work is doing.
"""
from __future__ import annotations

from ..layout import AT_ROOT, Layout
from .cruise_agents import DECISIONS
from .cruise_record import CONFIG, SCRIPT
from .cruise_told import seat_queues, seat_stands

#: The script that starts, stops, watches and tells — everything about the fleet that is not a setting.
FLEET = "scripts/agents/fleet.py"
#: What a person reads to see one stream's own lines, rather than every stream's as they arrive.
INBOX_SCRIPT = "scripts/agents/inbox.py"
# The rule every seat command shares: the harness folds a command's output, so the reply carries it.
VERBATIM = ("Put every line it printed in your reply, unchanged, in a fenced block, before anything else: the harness "
            "folds a command's output, so what it said reaches a person only through your reply.")


def cruise_status_command(layout: Layout = AT_ROOT) -> str:
    """`/cruise-status`: what is running, and — separately — what the work is doing."""
    return f"""---
description: Say what the fleet is doing — every stream, what it is on, what is waiting on a person — and which processes are up
argument-hint: [stream]
---

# Cruise status

Where the run stands, folded from the logs. Reading only; nothing here changes anything.

```sh
slipwai fleet $ARGUMENTS
python3 {FLEET} list
```

{VERBATIM} **The two commands answer two different questions and the order matters.** The first is the work:
one row per stream, what it is on, when it last wrote a line, whether it is running, stalled or waiting on
somebody — and with a stream named as the argument, that stream's own lines instead. The second is only the
processes: which captains and which harbourmaster are up, by pid, and which were started and are not.

A stream can be running with nothing happening and a captain can be gone with the work finished, so never
report one as if it answered the other. Where a stream is **stalled**, say so first and say for how long; that
is the one state a board exists to make impossible to miss. Where something is **waiting on a person**, repeat
what it is waiting for, and say that `/cruise-tell <stream>` answers it. To watch the lines as they arrive,
`/cruise-watch`. To end the run, `/cruise-stop`.
"""


def cruise_stop_command(layout: Layout = AT_ROOT) -> str:
    """`/cruise-stop`: ask every captain to stop at its next boundary."""
    return f"""---
description: Ask the harbourmaster and every captain to stop; each stops at its next boundary with its work committed
---

# Cruise stop

A person's stop. Every captain is asked, and each stops **at its next boundary** — it finishes the stage in
hand, writes its lines, commits what is green, and ends. Nothing is killed mid-stage, because a stage ended
halfway leaves a berth whose state nobody can read; a boundary is the point at which stopping costs nothing.

```sh
python3 {FLEET} stop
```

{VERBATIM} It names each process it asked and says which were already gone — a captain that exited on its own
is a fact worth seeing, and a `stop` that pretended to tidy it is how a person stops believing the output.
Then say that stopping is not undoing: every slice already merged stays merged, every berth stays where it is,
and `{layout.make} cruise` casts off again from exactly here. Where nothing was running, the script says so
and nothing is written.
"""


def cruise_tell_command(layout: Layout = AT_ROOT) -> str:
    """`/cruise-tell`: write one `told` line into a stream's deck log."""
    return f"""---
description: Tell one stream something — a steer, a fact it lacked, an answer to what it parked on — which its captain reads at its next boundary
argument-hint: <stream> <what it should know or do next>
---

# Cruise tell

A person's word to a stream that is already going. It is written as a `told` line into **that stream's own
deck log**, which is the file its captain reads at every boundary; the captain answers with a `read` line
carrying the `told`'s own timestamp, so the receipt is evidence somebody was told rather than an assertion
that somebody looked.

```sh
python3 {FLEET} tell <<'EOF'
$ARGUMENTS
EOF
```

The first word is the stream and the rest is the message, which goes in as written — the quoted heredoc is so
a quote or a `$` inside it never reaches the shell. {VERBATIM}

**The stream is required and the command refuses without one**, naming the streams there are. That is
deliberate: there is no single run to talk to any more, and four captains each somewhere different in their
work are rarely all meant to hear the same thing. `--everyone` as the first word is the deliberate broadcast.

Nothing has to be running for this. A `told` is a line in a log, not a signal to a process, so one written
while the fleet is stopped is read by whatever is lit next — `/cruise-status` says which streams have a
captain. A message is not a setting: `/cruise-settings` is still how a rule of the run changes, and say so
where somebody asks for one through here. `{layout.make} cruise-tell STREAM=<name> MSG="…"` is the same from
a terminal.
"""


def under_cruise_section() -> str:
    """The section `/where-are-we` and `/whats-next` end with: how the answer changes while a fleet is going,
    and — where none is — how it does not change at all."""
    return f"""## Under a fleet

Run `slipwai fleet` first. It folds the logs, changes nothing, and prints **nothing but an empty board where
no stream has written a line** — then everything above stands exactly as written, and this section does not
apply. Where it printed rows, captains are at work. {VERBATIM}

Then the answer changes in one place: for every slice a captain holds, the step for a person — **Run:** here,
the board's ➡️ *Next* row there — is not a command to type, because a captain is on it, at the slice and stage
the row names. Say so, and say what a person can do from here: `/cruise-watch` watches the lines arrive,
`/cruise-tell <stream>` steers one, `/cruise-stop` ends the run. Where a row says a stream is **waiting on
you**, the step is what it is waiting for, and `/cruise-tell` with it is what resumes that stream.

Nothing else changes, and one thing specifically does not: the board is read from the same artifacts as ever,
so a slice no captain holds is a slice a person may take, in this session, now. A fleet running on four
streams does not make the fifth somebody else's.
"""


def watch_seat_body(layout: Layout = AT_ROOT) -> str:
    """The watch seat's rules: what the seat prints, when it watches again, when it ends the turn, and how a
    person typing there is answered. One text, so `commands/cruise.md` — which leads into it after casting
    off — and `/cruise-watch` — the seat on its own — cannot say two different things."""
    return f"""run `python3 {FLEET} watch`. It prints every stream's
lines as they are written — one line per claim, mark, demo, merge, park and message, each saying which stream
wrote it — and returns after a minute and a half, whether or not anything arrived. **Put every line it printed
in your reply, unchanged, in a fenced block, before anything else** — the harness folds a command's output, so
the feed reaches a person only through your reply — **and then run `watch` again at once**, unless a person
has typed something or the fleet has stopped.

What watching is not: it is not how the run continues. Every captain runs in its own process and reads its own
log; this session is a window, and closing it stops nothing. So a watch the harness cut short is watched again
rather than asked about, and a turn that ends here ends nothing — which is also why watching is never a reason
to run a stage of the ladder in this session. Where the harness can run a command in the background and
re-invoke this session with its output, run `watch` that way, so the turn ends between watches and a person
can type in the gap.

**Nothing arriving is a thing to report, not a thing to wait through.** Where two watches in a row print no
lines, say so and run `slipwai fleet` once: a stream that has written nothing for a while is either thinking
or stalled, and only the board tells them apart. Where it says stalled, say which stream, for how long, and
what its last line was.

**A person typing here is talking to you, not stopping the run.** Answer them — what the feed shows, what
`{CONFIG}` says (`python3 {SCRIPT}` prints every setting and what it controls), what `slipwai fleet` says,
what `{DECISIONS}` records — and change a setting through `/cruise-settings` where they ask; a captain reads
it at its next boundary. {seat_queues(FLEET)} Then watch again. Only `python3 {FLEET} stop` or
`{layout.make} cruise-stop` ends the run, and only when they ask for that. {seat_stands()}"""


def cruise_watch_command(layout: Layout = AT_ROOT) -> str:
    """`/cruise-watch`: the watch seat on its own, without starting anything."""
    return f"""---
description: Take the watch seat beside a running fleet — print each stream's lines as they are written, watch again, answer a person typing here — without starting anything
---
# Cruise watch

The watch seat on its own. `/cruise` takes it after casting off, and a `/cruise-status` between reads the board
once and stops; this sits back down on the logs, in this session, and starts nothing. Where nothing is running
it still works — the logs are there either way — and prints nothing until something writes a line, which is
what `/cruise-status` is for telling apart from a fleet that is merely quiet.
`{layout.make} cruise-watch` is the same seat from a terminal. To take it: {watch_seat_body(layout)}
"""
