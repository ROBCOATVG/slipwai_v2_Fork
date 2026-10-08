MINOR

**The two identity questions are now `Internal authentication` and `External authentication`.** They were
*Staff* and *Customer*, which read as a guess about who uses the product: plenty of projects authenticate
operators, partners or agents rather than staff, and plenty have members or citizens rather than customers.
Internal and external say the thing that actually differs — which side of the organisation the account is on
— and that is the distinction the two axes have always been about.

Everything the keel says follows: the interview's two questions, every option's description, the generated
`README.md` and the cloud architecture pages, the Keycloak notes, `.env.example`, and the browser app's own
comments.

**What did not change, and why.** The axis keys are still `auth` and `users`, the capabilities are still
`auth-*` and `users-*`, the Keycloak realms are still `app` and `customers`, and `OIDC_*` / `USERS_OIDC_*`
are untouched — those are identifiers a running service and a generated project already read, and renaming
one is a migration rather than a rename. The two cloud stacks keep `staff` and `customers` in their
terraform for the same reason, and more sharply: renaming `aws_cognito_user_pool.staff` without a `moved`
block destroys the pool and every account in it. They are renamed in phase 10, where the packages are
rewritten and the `moved` blocks go in with them.

**Catch-up:** nothing. No file a project owns changed its name or its keys.
