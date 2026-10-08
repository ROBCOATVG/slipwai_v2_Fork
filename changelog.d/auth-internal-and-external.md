MINOR

**The two identity questions are now `Internal authentication` and `External authentication`.** They were
*Staff* and *Customer*, which read as a guess about who uses the product: plenty of projects authenticate
operators, partners or agents rather than staff, and plenty have members or citizens rather than customers.
Internal and external say the thing that actually differs — which side of the organisation the account is on
— and that is the distinction the two axes have always been about.

Everything the keel says follows: the interview's two questions, every option's description, the generated
`README.md` and the cloud architecture pages, the Keycloak notes, `.env.example`, and the browser app's own
comments.

**The two cloud stacks are renamed too, and this is the part to read before you deploy.** A terraform
resource address is state, not a name: `aws_cognito_user_pool.staff` becoming `.internal` is, to terraform,
one resource destroyed and another created — which for a user pool is every account in it gone. So every
renamed address ships with a `moved` block, which tells `tofu plan` to move the state instead. The files are
renamed with them: `cognito_staff.tf` → `cognito_internal.tf`, `cognito_customers.tf` →
`cognito_external.tf`, `entra_staff.tf` → `entra_internal.tf`.

**What did not change.** The axis keys are still `auth` and `users`, the capabilities are still `auth-*` and
`users-*`, the Keycloak realms are still `app` and `customers`, and `OIDC_*` / `USERS_OIDC_*` are untouched.
Those are identifiers a running service and a generated project already read, and renaming one is a
migration rather than a rename.

**Catch-up — do not apply before you have read a plan.** On a project with an AWS or Azure stack that has
already been applied:

```sh
slipwai migrate          # brings the renamed files and their `moved` blocks in
cd infra/service && tofu plan
```

**Read that plan and do not apply until it says no resource will be destroyed.** The `moved` blocks are
what make it say that; a plan that still shows a destroy means one address was missed, and applying it would
take the pool, the app registration or the connection with it. Report the address and nothing is lost.

Your `*.tfvars` need the two renamed variables: `staff_callback_urls` is `internal_callback_urls`,
`customer_callback_urls` is `external_callback_urls`, and the `auth0_` forms of both the same way. A
variable is not state, so that is a rename and not a migration — but `tofu plan` refuses an undeclared one,
which is the gate that stops you missing it.

A project with no cloud target has nothing to do.
