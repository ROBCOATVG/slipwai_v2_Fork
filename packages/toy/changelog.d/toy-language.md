MINOR

**The language template ships: `toy`, an inert language package the conformance suite passes.** It is the smallest
package slipwai's suite accepts — family `toy` and its backend `toy-plain`, the `none` target, the in-memory and Postgres event stores
as placeholder files, every protocol member answered with a placeholder, and a placeholder snippet for every example
marker of both profiles — so a language author copies it, renames it and replaces each answer with their language's
own. A project it generates builds nothing: its commands only say what a real language would run. It declares the
catalog schema it loads on, `core >=9.0,<10`, in `language.json`.
