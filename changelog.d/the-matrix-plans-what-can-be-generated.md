PATCH

**The matrix no longer plans a row that generation will refuse.** Its store, identity and production rows
were written out for every backend, and every real language implements both stores, Keycloak and a cloud
target — so nothing noticed. A package that implements none of them had four rows planned against it whose
own refusals read *a half-ported version is deliberately not emitted*.

A row is planned only where every answer it names is implemented for that backend and offered under that
target — the same two questions generation already asks before it refuses. A row that cannot generate is
not a failing matrix; it is a matrix written down wrong, and the two look identical in a CI log.

Also: an image builder whose tool a package names itself — `image_builder`'s `tool` is the package's own
word — is skipped with the tool named, rather than ending the run in `KeyError`.

**Catch-up:** nothing. A package that implements fewer options than the published six now gets a shorter
matrix instead of a red one.
