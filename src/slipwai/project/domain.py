"""`.specify/domain/`: what is true about this domain, as distinct from what this product chose.

Issue #27. In the experiment the skipper parked on questions a written fact would have answered, and guessed
at others it should have parked on — and the two look identical from outside, because neither one says what
it was decided from. The missing thing was never judgement. It was a place for facts.

**A domain fact is not a product decision, and keeping them apart is the whole point.** The constitution says
what must never be violated. The specification says what to build. The owner brief says what the owner
prefers. None of those is the place for *a settlement window is two business days* or *a seat is held for
fifteen minutes or released* — those are true whether or not this product exists, and they are what a
person would otherwise be interrupted for again and again.

**A fact here is cited, never summarised.** The skipper's entry names the file and heading it turned on and
quotes the sentence. A paraphrase is the fact as somebody understood it, which is exactly the thing a reader
needs to check, and a reader who cannot find the original has to take the paraphrase on trust. Where nothing
here answers a question, the entry says `Cites: none` and what it decided from instead — because an absent
citation and an unnecessary one look the same afterwards, and only one of them is fine.

It ships with one page explaining itself and no facts, because a template fact is a fact nobody wrote.
"""
from __future__ import annotations

DOMAIN = ".specify/domain"


def domain_readme() -> str:
    """`.specify/domain/README.md`: what belongs here, what does not, and the shape a fact takes."""
    return """# Domain knowledge

What is **true about this domain**, as distinct from what this product has chosen. One file per area, with
`## ` headings a decision can cite by anchor.

## What belongs here

- **The glossary.** What a word means in this business, especially where it means two things next door.
- **Invariants.** Things that are true of the world and must stay true of the system: a seat is held or it
  is free, a ledger balances, an order cannot be placed from an empty cart.
- **Rules somebody else imposes.** Regulation, a standard, a partner's contract, a published API's limits —
  with where each is written down, because that is what makes it checkable rather than remembered.
- **Numbers with units and sources.** A settlement window of two business days; a retention period of seven
  years; a rate limit of 100 a minute. The source matters more than the number, because the number changes.

## What does not

- **What this product decided.** That is the constitution (what must never be violated), the specification
  (what to build) or the owner brief (what the owner prefers).
- **How anything is implemented.** A domain fact outlives three rewrites. A schema does not.
- **Anything nobody has checked.** A fact here is read as true. One that was somebody's impression should
  say so, or stay out — a wrong fact confidently filed is worse than a missing one, because a missing one
  gets asked about and a wrong one gets cited.

## The shape

```markdown
## Settlement window
Funds settle two business days after capture (T+2). Source: the acquirer's merchant agreement, §4.2,
version of 2026-03-01. Changes with the scheme, not with us.
```

A heading, the fact in a sentence or two, and where it came from. The heading is the anchor a decision
cites, so renaming one breaks every citation of it: add a new heading and leave the old one with a line
saying what replaced it, the same rule the decision ids follow.

## How it is used

`/cruise`'s skipper reads this before deciding a product question and cites what it turned on — the file,
the heading and the sentence. Where this directory answers nothing, the decision says `Cites: none` and
what it decided from instead. The point is not that a run knows the domain. It is that a question answered
from a written fact can be checked, and one answered from a guess cannot be told apart from it.

**It ships empty on purpose.** A template fact is a fact nobody wrote, and the first reader would not know
which of these were real.
"""


def domain_files() -> dict[str, str]:
    """The page, keyed by its path in the project."""
    return {f"{DOMAIN}/README.md": domain_readme()}
