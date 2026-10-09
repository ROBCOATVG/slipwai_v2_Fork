MINOR

**Whether a service's truth is its log is now that service's own answer.** `project.json` has recorded
`eventSourced` per deployable since it was written, but the keel set it from the profile — so every
service of a modelled project claimed the log and no service of a standard one could, however the product
was actually built. `write-model` became an axis in the last change; this is the keel reading it.
`eventSourced` is now `write-model: events` for the service that was asked, `state` for one that never was,
and `false` for a browser app and for an application the keel did not make — never `events` by detection
alone, because a log nobody vouched for is a guess wearing a fact's clothes.

What a service is *given* follows the same answer. A backend declares its event-store rows as it always
has, and the state-stored rung's rows — the repository port, its adapters, the migration for a versioned
state table — under one `state` key beside them, so a service answered `state` is given those instead. A
backend that has written no `state` block answers such a service with nothing, which `slipwai package check`
is what names.

**Catch-up:** nothing for a project whose services are all on one rung, which is every project generated
before this: the default answers still generate what they generated. `slipwai migrate` rewrites
`project.json` either way, and a mixed project is a thing you can now ask for.
