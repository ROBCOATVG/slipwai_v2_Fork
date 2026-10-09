MINOR

**On the state-stored rung an event is modelled always and published only where something reads it.** The
rung shipped telling every state-stored service to build an outbox in the write's own transaction, which
is real infrastructure erected to notify nobody in exactly the case the rung exists for: a small
supporting domain, a context that is genuinely field updates.

Three things were being carried under one word. An event as **notation** — a fact on the timeline — is how
a slice is found at all, costs nothing at runtime, and belongs on both rungs. An event as **truth** is the
log, which is the other rung by definition. An event as a **published contract** is machinery, and it is
earned by a subscriber: a `reads` from another service, or a read model whose `materialisation` is `async`.

So T023's state twin is now skipped until one of those exists, `docs/event-modeling-to-code.md` says the
same of `evt`, and the `pcr` row says what it always should have: with no stream to subscribe to, two
slices in one state-stored service are linked by a call the use case makes. Principle III carries both
rules. And where the project already publishes somehow — an outbox, a bus, change data capture — the slice
uses that one and records it, rather than adding a second way of doing what the codebase already does.

Nothing changes on the event-sourced rung, and nothing changes about the timeline: every `evt` is still a
fact the model names.

**Catch-up:** nothing. A project that already built an outbox has one that works; this changes what the
next slice is told to build.
