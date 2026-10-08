# Captures

From real runs, not drawn. Every file here came out of a project slipwai generated and a loop that was
actually driven in it — which is the point: a screenshot of something that has never run is a drawing with
extra steps, and it goes stale without anybody noticing.

How each was made, so the next person can remake them rather than touch them up.

| File | What it is | Made by |
| --- | --- | --- |
| `channel.png` | The published chandlery's front page | `https://robcoatvg.github.io/slipwai-index/` |
| `event-model.png` | An event model with its timeline and swimlanes | `make model` in a generated project |
| `bridge.png` | The bridge: what is waiting on a person, the streams, the speed | `slipwai bridge` |
| `bridge-header.png` | The mark and the theme toggle | the same page |
| `fleet-board.txt` | The board, folded from the logs | `slipwai fleet` |
| `stream-log.txt` | One stream's own log, said a line at a time | `slipwai fleet ordering` |
| `chart-and-clearance.txt` | The chart's gate, and what may start | `check-chart.py`, `clearance.py` |
| `chandlery-search.txt` | What the published chandlery offers | `SLIPWAI_INDEX=https://robcoatvg.github.io/slipwai-index slipwai search` |

## The run behind them

A project generated with the TypeScript package installed from the chandlery, on the event-modelling
profile. Three slices across two streams: `ORD-01` places an order and sets `OrderPlaced`, `ORD-02` shows
one, and `BIL-01` charges for one and steers by `OrderPlaced`.

`ORD-01` was driven first. Its `mark-set` line was carried to the harbour log, and **`BIL-01` — in a
different stream — was cleared by that, with nothing merged.** That is the claim version 2 rests on, and
`fleet-board.txt` and `chart-and-clearance.txt` are what it looked like.

What the captures also show honestly: `merged 0`. On the day of that run the harbourmaster granted a merge
and nothing performed one — section 14 of the plan, link 3. **Slice 7.9 closed that on 2026-10-08**, so a
run today reaches trunk; these files are left as they were taken, because a capture edited to say what the
code does now is a drawing again.

## Why `chandlery-search.txt` names its index

`slipwai search` with no `SLIPWAI_INDEX` reaches the index the keel ships as its default, and nothing is
published there yet — so the capture was taken against the index that is. `make test-docs` holds
`docs/guide/start-here.md` to this file rather than to a live search, because that page must be right for a
reader whose machine has no network and no chandlery account.
