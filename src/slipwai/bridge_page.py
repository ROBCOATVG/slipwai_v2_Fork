"""The bridge's page: the board as HTML, in the words a person uses rather than the method's.

The nautical names are the method's — they make a dozen scattered ideas into one picture, and that is worth
having in a plan and in a log. They are not the dashboard's. Somebody looking at this page wants to know
what is running, what is waiting on them, and how fast it is going; `boilers` and `fanout` cost them a
glossary to find out.

So every label here is plain, and `PLAIN` is the one table that says which is which. The mockup
(`docs/mockups/ledger-bridge.html`) decided this and the rule is its, not this module's.

**The page is rendered, not templated over the mockup.** The mockup is 44KB of hand-written markup with its
example data in the rows; replacing a "data section" in it would mean parsing somebody's HTML and hoping. So
the look is the mockup's — its tokens, its type, its light and dark — and the markup is written from the
board. What the mockup is for is the design, and that is what is carried across.

**Nothing here reaches the network and nothing is cached.** The page is a render of `fleet.board`, which is
a fold of the logs, so a reload is a re-fold. That is the same rule the board has and for the same reason.
"""
from __future__ import annotations

import html
import json

from .fleet import NOTHING
from .telegraph import MEANS, POSITIONS

#: The method's word, and the word on the page. The page never shows the left-hand column.
PLAIN = {
    "boilers": "Captains at once",
    "fanout": "Delegates per captain",
    "bunker_per_slice": "Budget per slice (k tokens)",
    "bunker_per_day": "Budget per day (k tokens)",
    "stage_scale": "Stage budgets ×",
    "bar": "Stop a merge at or above",
    "decision_ceiling": "Unread decisions allowed",
    "wait_bound": "Longest wait (minutes)",
    "fairway": "Stream",
    "berth": "Workspace",
    "slice": "Piece of work",
    "capability": "Capability",
}
#: How a position reads on the dial. Sentence case, as the mockup has it.
DIAL = {name: name.replace("-", " ").capitalize() for name in POSITIONS}
#: What each state means in a word a reader does not have to be told. `stalled` stays `stalled`: it is the
#: one that has to be noticed, and a gentler word for it would be the dashboard hiding something.
STATES = {"working": "running", "stalled": "stalled", "parked": "waiting on you",
          "finished": "done", "not started": "not started"}

STYLE = """
:root{--ground:#f1f3f4;--paper:#fcfcfb;--ink:#172129;--ink-2:#4a5862;--ink-3:#7a8891;--rule:#d9e0e4;
--rule-2:#e9eef1;--teal:#0f6b6b;--teal-soft:#dcecea;--brass:#8a6d24;--brass-soft:#f1e9d2;--good:#0ca30c;
--warn:#fab219;--serious:#ec835a;--critical:#d03b3b;
--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;
--sans:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",Arial,sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--ground:#10171c;--paper:#1a1a19;
--ink:#e6ecef;--ink-2:#b6c1c8;--ink-3:#808e97;--rule:#2c3840;--rule-2:#222c33;--teal:#5fc1bb;
--teal-soft:#15302f;--brass:#d2b465;--brass-soft:#2e2814}}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);font-family:var(--sans);font-size:14px;
line-height:1.45;padding-inline:20px;padding-block:0 60px}
.wrap{max-width:1200px;margin:0 auto}
code,.mono{font-family:var(--mono);font-size:.92em}
h1{font-size:1.35rem;font-weight:600;margin:0}
.sub{color:var(--ink-3);font-size:.85rem;margin-top:3px}
.top{padding-block:22px 14px;border-bottom:1px solid var(--rule)}
.card{background:var(--paper);border:1px solid var(--rule);border-radius:10px;padding:16px;margin-top:18px}
.card h2{font-size:.95rem;font-weight:600;margin:0 0 10px}
table{width:100%;border-collapse:collapse;font-size:.9rem}
th{text-align:left;font-weight:500;color:var(--ink-3);font-size:.78rem;text-transform:uppercase;
letter-spacing:.05em;padding:0 10px 6px 0;border-bottom:1px solid var(--rule-2)}
td{padding:8px 10px 8px 0;border-bottom:1px solid var(--rule-2);vertical-align:top}
.chip{display:inline-block;font-size:.76rem;padding:2px 8px;border-radius:999px;background:var(--rule-2);
color:var(--ink-2)}
.chip.running{background:var(--teal-soft);color:var(--teal)}
.chip.stalled{background:#fbe1d7;color:var(--critical)}
.chip[data-state="waiting on you"]{background:var(--brass-soft);color:var(--brass)}
.dial{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}
.dial button,.dial span{font:inherit;font-size:.85rem;padding:7px 14px;border-radius:7px;cursor:pointer;
border:1px solid var(--rule);background:var(--paper);color:var(--ink-2)}
.dial .now{background:var(--teal);border-color:var(--teal);color:#fff;cursor:default}
.ask{display:flex;gap:8px;margin-top:8px}
.ask input{flex:1;font:inherit;padding:7px 10px;border:1px solid var(--rule);border-radius:7px;
background:var(--paper);color:var(--ink)}
button.go{font:inherit;padding:7px 14px;border-radius:7px;border:1px solid var(--teal);background:var(--teal);
color:#fff;cursor:pointer}
dl{display:grid;grid-template-columns:1fr auto;gap:6px 16px;margin:0;font-size:.88rem}
dt{color:var(--ink-2)}
dd{margin:0;text-align:right}
dd input{font:inherit;width:110px;padding:4px 8px;border:1px solid var(--rule);border-radius:6px;
background:var(--paper);color:var(--ink);text-align:right}
.empty{color:var(--ink-3);font-size:.9rem}
.feed{font-family:var(--mono);font-size:.78rem;color:var(--ink-2);margin:0;padding:0;list-style:none}
.feed li{padding:2px 0}
@media (max-width:600px){dl{grid-template-columns:1fr}dd{text-align:left}}
"""

SCRIPT = """
async function send(path, body){
  const answer = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'},
                                    body: JSON.stringify(body)});
  if (answer.ok) location.reload();
  else alert(await answer.text());
}
document.addEventListener('click', event => {
  const dial = event.target.closest('[data-ring]');
  if (dial) send('/ring', {position: dial.dataset.ring});
  const say = event.target.closest('[data-tell]');
  if (say) {
    const box = document.getElementById('tell-' + say.dataset.tell);
    if (box && box.value.trim()) send('/tell', {fairway: say.dataset.tell, message: box.value.trim()});
  }
  if (event.target.id === 'apply') {
    const pairs = [...document.querySelectorAll('[data-number]')]
      .map(one => one.dataset.number + '=' + one.value);
    send('/set', {pairs});
  }
});
"""


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def berth_rows(rows: list[dict]) -> str:
    if not rows:
        return '<p class="empty">No stream has written a line yet.</p>'
    head = ("<tr><th>Stream</th><th>Feature</th><th>Piece of work</th><th>State</th>"
            "<th>Last line</th><th>Tokens</th><th>Merged</th></tr>")
    body = "".join(
        f"<tr><td><b>{esc(row['fairway'])}</b></td><td>{esc(row['feature'])}</td>"
        f"<td class=\"mono\">{esc(row['slice'])}</td>"
        f"<td><span class=\"chip {esc(STATES.get(str(row['state']), ''))}\" "
        f"data-state=\"{esc(STATES.get(str(row['state']), row['state']))}\">"
        f"{esc(STATES.get(str(row['state']), row['state']))}</span></td>"
        f"<td>{esc(row['last'])}</td><td>{esc(row['tokens'])}</td><td>{esc(row['merged'])}</td></tr>"
        for row in rows)
    return f"<table>{head}{body}</table>"


def inbox_rows(rows: list[dict], controls: bool) -> str:
    if not rows:
        return '<p class="empty">Nothing is waiting on you.</p>'
    said = []
    for row in rows:
        said.append(f"<tr><td><b>{esc(row['fairway'])}</b></td><td>{esc(row['kind'])}</td>"
                    f"<td>{esc(row['what'])}</td><td class=\"mono\">{esc(row['t'])}</td></tr>")
    return f"<table>{''.join(said)}</table>"


def answer_boxes(rows: list[dict]) -> str:
    """One box per stream that has written a line. An answer typed here becomes a `told` in its deck log,
    which is the whole point: a person answers from one seat instead of finding the right terminal."""
    streams = sorted({str(row["fairway"]) for row in rows})
    if not streams:
        return ""
    boxes = "".join(
        f'<div class="ask"><input id="tell-{esc(one)}" placeholder="Tell {esc(one)} something…">'
        f'<button class="go" data-tell="{esc(one)}">Send</button></div>' for one in streams)
    return f'<div class="card"><h2>Say something to a stream</h2>{boxes}</div>'


def dial(position: str, controls: bool) -> str:
    buttons = []
    for name in POSITIONS:
        if name == position:
            buttons.append(f'<span class="now">{esc(DIAL[name])}</span>')
        elif controls:
            buttons.append(f'<button data-ring="{esc(name)}">{esc(DIAL[name])}</button>')
        else:
            buttons.append(f"<span>{esc(DIAL[name])}</span>")
    return f'<div class="dial">{"".join(buttons)}</div>'


def tune(config: dict, controls: bool) -> str:
    """The fine-tune panel, in plain words. Writes `harbour.json` through the same code the verb uses."""
    rows = []
    for name in MEANS:
        value = config.get(name, NOTHING)
        cell = (f'<input data-number="{esc(name)}" value="{esc(value)}">' if controls else esc(value))
        rows.append(f"<dt>{esc(PLAIN.get(name, name))}</dt><dd>{cell}</dd>")
    apply = '<div class="ask"><button class="go" id="apply">Apply</button></div>' if controls else ""
    return f'<div class="card"><h2>Fine tune</h2><dl>{"".join(rows)}</dl>{apply}</div>'


def page(found: dict, config: dict, controls: bool = True, title: str = "Bridge") -> str:
    """The whole page. `controls` off is the read-only copy, which is the same page with nothing to press."""
    berths = found["berths"]
    waiting = found["inbox"]
    pressure = found["pressure"]
    bunker = found["bunker"]
    spent = bunker["spent"]
    stalled = [row for row in berths if row["state"] == "stalled"]
    sub = (f"{len(waiting)} waiting on you · {len(berths)} stream(s)"
           + (f" · {len(stalled)} stalled" if stalled else "")
           + f" · {spent if spent is not None else NOTHING}/{bunker['allowed']}k today")
    banked = f'<p class="empty">{esc(pressure["banked"])}</p>' if pressure["banked"] else ""
    feed = "".join(f"<li>{esc(w)}  {esc(who)}  {esc(kind)}</li>" for w, who, kind in found["feed"][-15:])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><style>{STYLE}</style></head>
<body><div class="wrap">
<div class="top"><h1>{esc(title)}</h1><div class="sub">{esc(sub)}</div></div>
<div class="card"><h2>Waiting on you</h2>{inbox_rows(waiting, controls)}</div>
{answer_boxes(berths) if controls else ""}
<div class="card"><h2>Streams</h2>{berth_rows(berths)}</div>
<div class="card"><h2>Speed</h2>{dial(str(pressure["position"]), controls)}{banked}</div>
{tune(config, controls)}
<div class="card"><h2>Last lines</h2><ul class="feed">{feed or "<li>nothing yet</li>"}</ul></div>
</div>{"<script>" + SCRIPT + "</script>" if controls else ""}</body></html>
"""


def read_only(found: dict, config: dict, title: str = "Bridge") -> str:
    """The published copy: the same page with nothing to press, which is what Pages serves."""
    return page(found, config, controls=False, title=title)


def payload(found: dict) -> str:
    """The board as JSON, for anything that would rather read it than look at it."""
    return json.dumps(found, indent=2, ensure_ascii=False, default=str)
