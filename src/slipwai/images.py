"""How each backend's production image is built, how its migrations run inside one, and what it is told there.

The production target deploys one image per service, built by the ecosystem's own builder rather than by a
Dockerfile — for the reason Compose already runs the checkout: nothing to keep in step with the app's layout.
ko for Go, Jib through Quarkus's own extension, `spring-boot:build-image` for Spring, and Paketo buildpacks for
Node and Python. Each backend answers how it becomes an image on its own object, as the protocol's
`image_builder` (`registry.py`, `project/languages/`), and the keel asks the registry: the Makefile, the deploy
workflow and the infrastructure all have to agree about how a service becomes an image and how its schema is
applied once it is one, and three copies of that answer are three places for it to drift. The same holds for
how its migrations run in one (`migrations_in_production`). What stays here is the keel's: the recipe vocabulary
below, the pins, the managed-database kinds with the measurements behind every backend's TLS answer, the
repository-root upload list, and the readers.

Every recipe a backend answers is a Make recipe line: `__APP__` is the service's directory (`backends.APP`),
`__IMAGE__` the image reference the recipe builds, `__REPOSITORY__` the same reference without its tag (ko
wants the two apart), and `$(PLATFORM)` / `$(GIT_SHA)` are the generated Makefile's own variables.

The third question — what a backend is *told* in production and nowhere else — is each backend's
`postgres_sslmode` and the `environment` key of its `migrations_in_production`. Both are read by
`project.infra`, which merges them into the one `environment` map the stack puts on both task definitions;
neither reaches a laptop, where the Compose Postgres has no TLS and no framework migrates as it starts.
"""
from __future__ import annotations

from typing import Any

from .backends import APP, NODE_MAJOR, PYTHON_VERSION
from .registry import IMAGE_BUILDER, MIGRATIONS_IN_PRODUCTION, registry

IMAGE = "__IMAGE__"
REPOSITORY = "__REPOSITORY__"

# The pins. Searched and chosen once; a generated project reads them out of its own Makefile and pom.
PACK_VERSION = "v0.40.9"
KO_VERSION = "v0.19.1"
# Paketo's multi-architecture Ubuntu 24.04 builder — Node.js and Python buildpacks, no C libraries — and the
# Java one Spring's `build-image` is pointed at. Both publish amd64 and arm64, which is what lets `make build`
# on a laptop produce an image the laptop can run while the pipeline builds for Fargate's x86_64.
PAKETO_BUILDER = "paketobuildpacks/ubuntu-noble-builder:0.0.174"
PAKETO_JAVA_BUILDER = "paketobuildpacks/builder-noble-java-tiny:0.0.176"
NODE_VERSION = f"{NODE_MAJOR}.*"
CPYTHON_VERSION = f"{PYTHON_VERSION}.*"
# Jib's base for the Quarkus image: the same Temurin 25 the CI image and `actions/setup-java` install, rather
# than Quarkus's Red Hat UBI default, so one JDK vendor appears everywhere a generated Java project runs.
JIB_BASE_IMAGE = "eclipse-temurin:25-jre-noble"

# The Paketo invocation shared by the two buildpack-built backends. `--publish` when a registry is named,
# because pack then pushes straight from the build container without exporting to the local daemon — the
# path CI takes, and the one that also works on a Docker daemon using the containerd image store, where
# the daemon export fails (buildpacks/pack#2272). Without a registry the image lands in the daemon, for
# `make smoke-image`. `--platform` because a laptop is usually arm64 and Fargate is x86_64. `$(PACK_FLAGS)`
# comes last in every recipe, so a flag it repeats — `--pull-policy always`, when the daemon holds the builder
# for the other platform and `if-not-present` would hand pack that one — is the value pack takes.
PACK = (
    f"pack build {IMAGE} $(if $(IMAGE_REGISTRY),--publish,) --builder {PAKETO_BUILDER} "
    "--platform $(PLATFORM) --pull-policy if-not-present"
)

MAVEN = f"cd {APP} && ./mvnw -B -q -DskipTests"


# What each backend's Postgres client has to be told before it will encrypt its connection, for the one
# deployment where the server insists on it: a managed Postgres. RDS's `default.postgres17` parameter group
# has carried `rds.force_ssl = 1` since Postgres 15, so an unencrypted connection is refused outright — the
# server answers SQLSTATE `28000`, `no pg_hba.conf entry for host "…", user "app", database "app", no
# encryption`, and the migrate task exits 1 before a single statement runs. Nothing the keel emitted
# asked for encryption, so this was every generated project's first deploy, not one project's accident.
#
# Each backend answers it as its `postgres_sslmode` (`registry.py`, `project/languages/`), one value per kind
# below; the measurements behind every answer are written here, once, because they are one argument about
# drivers against a managed Postgres rather than five. Read per service by
# `project.infra.production_environment` and set in the container environment. Not set locally: the Compose
# Postgres runs without TLS, so a laptop has nothing to negotiate with.
#
# **Three answers, not one**, which is why the backend answers it and the keel does not. Every answer was
# settled by running the driver against a Postgres configured exactly as RDS is — `ssl=on` with a
# self-signed certificate and `hostnossl … reject`, which is what `rds.force_ssl = 1` amounts to — rather
# than from the documentation, because two of the three answers are not what the documentation would lead
# you to expect.
#
# - `typescript` → `no-verify`. `node-postgres` reads `PGSSLMODE` with its own vocabulary rather than
#   libpq's (`pg@8.23.0/lib/connection-parameters.js:34-35`, and again at :93-95): `require` there means
#   *verify* the server certificate against Node's bundled CA store, and RDS's certificate chains to
#   Amazon's private RDS root CA, which is not in that store. Measured: unset fails with `28000`,
#   `require` fails with `DEPTH_ZERO_SELF_SIGNED_CERT`, `no-verify` connects over TLSv1.3. This is the
#   only backend whose default is no TLS at all, and therefore the only one that was actually broken.
# - `python`, `go` → `require`. psycopg (libpq) and pgx (its own libpq-compatible parsing) both honour the
#   variable with libpq's semantics, where `require` already *is* "encrypt, do not verify". Measured for
#   both: `require` connects over TLSv1.3, and `disable` is refused with `28000` — which is what proves the
#   variable is read rather than merely harmless. Their default is libpq's `prefer`, so they would have
#   reached RDS anyway; `require` is what stops a silent fall back to plaintext against a server that ever
#   permits it.
# - `java-quarkus`, `java-spring` → **nothing, deliberately**. The PostgreSQL JDBC driver does not read
#   `PGSSLMODE`: the string appears nowhere in `postgresql-42.7.13.jar`, whose `PGEnvironment` reads only
#   `PGPASSFILE`, `PGSERVICEFILE` and `PGSYSCONFDIR`. Measured: with `PGSSLMODE=disable` exported, pgjdbc
#   still connects over TLSv1.3 — the variable is ignored in both directions. Setting it here would be a
#   setting with nothing behind it, which is the one thing an answer here must not be. pgjdbc's own default
#   is `prefer`, so both Java backends already negotiate TLS and never verify — the same posture as the
#   other three — and the server-side `rds.force_ssl = 1` in `rds.tf` is what makes "prefer" mean "always".
#   Stating it on the client for Java needs a JDBC-side knob (`sslmode` as a datasource property), whose
#   env-var spelling differs per framework and which nothing here can prove without a TLS Postgres and a
#   built application; `docs/aws-target.md` records that as the follow-up it is.
#
# Same posture on all five — encrypted, unverified — reached by three different routes because that is how
# many the drivers actually offer.
#
# `DATABASE_URL` is deliberately left alone, and that is the other half of the decision. It is one
# libpq-style string shared by all five backends (see the `java` family's `tooling` answer, `migrate`, for what that
# already costs Java), and an `sslmode` inside it would mean three different things at once:
# `pg-connection-string@2.14.0:77-79` turns *any* `sslmode` into TLS with Node's default
# `rejectUnauthorized: true` unless the non-libpq keyword `uselibpqcompat=true` is also in the string — and
# libpq rejects that keyword, so it cannot go in a URL the other backends read; and
# `pg@8.23.0/lib/connection-parameters.js:85` lets what it parsed from the string override `PGSSLMODE`
# outright, which would close off this route as well. So the URL stays the address and the credentials, and
# how the connection is protected is said once per backend, in its `postgres_sslmode`.
#
# Real verification — `verify-full` with an `sslrootcert` — is the better end state and is not this member's
# job: the RDS CA bundle has to reach every image by a path that differs per builder (`/workspace/…` for
# Paketo, `$KO_DATA_PATH` for ko's distroless Go images) while the secret is shared by all of them. That is
# a decision with an ADR behind it, not a value here; the generated
# `docs/adr/0002-production-target.md` says as much where a reader will hit it.
#
# `None` is an answer, written out rather than left as a missing key: "this driver ignores the variable, and
# that was checked" is what the next reader needs, and an absent key would read as a kind nobody got to.
#
# The key is what the target *provisions the store as* rather than the target itself, because every reason
# above is a property of the managed Postgres and not of the cloud around it: `no-verify` is RDS's private
# Amazon root not being in Node's bundle, and a second cloud whose certificate chains to a root Node does
# bundle would answer differently for the same driver. So a second managed Postgres is a second kind below,
# with every backend's answer for it measured the same way, and never assumed from this one. The catalog's
# `postgres` option says what each target provisions it as, and `tests/test_backend_obligations.py` holds
# this tuple to that, and every backend's answer to this tuple.
#
# **`flexible-server` is not measured, and every answer to it is deliberately the conservative copy of
# `rds`'s.** Azure Database for PostgreSQL Flexible Server also refuses an unencrypted connection —
# `require_secure_transport` is on by default — so every backend needs the same posture; what is not
# established is whether TypeScript could have a *stronger* one there. RDS forced `no-verify` because its
# certificate chains to a private Amazon root Node does not bundle; Flexible Server's chains to DigiCert
# Global Root G2 and Microsoft RSA Root CA 2017, which Node does, so `require` — which node-postgres reads as
# *verify* — may well connect and verify. That is a hypothesis about a certificate chain, not a fact about a
# driver, and no answer here has ever been one of those.
#
# Every answer is safe as it stands: `no-verify` and `require` both encrypt, and neither can fail where the
# other succeeds. What is owed is one run of node-postgres against a real Flexible Server. If `require`
# connects, TypeScript's `flexible-server` answer says `require` and the ADR loses a paragraph; until somebody
# has run it, it says what is known to work.
POSTGRES_SSLMODE_KINDS: tuple[str, ...] = ("rds", "flexible-server")


# `project.toml` at the repository root, read by `pack build --path .`: what stays out of the upload. The
# machine's `node_modules` is the machine's — the image installs its own from the lockfile, for its own
# platform — and `.git` is history the image has no use for. `.build/` is deliberately not excluded: `make
# build` compiles before packing, and the compiled entry point is what the image runs.
WORKSPACE_DESCRIPTOR = """# Read by `pack build --path .` (`make build`): what the upload leaves out. `node_modules` is
# this machine's; the image installs its own from the lockfile, for its own platform — uploaded, the
# buildpack would rebuild this one instead, and the compiler for the image's platform is not in it.
# `.build/` is not excluded: `make build` compiles before packing, and that is what the image runs.
[_]
schema-version = "0.2"

[io.buildpacks]
exclude = ["node_modules", ".git"]
"""


# How a service's migrations are applied once it is an image, which each backend answers as its
# `migrations_in_production` — each in the shape its ecosystem already has, and none by a step written twice.
#
# - `command`: run the service's image once more as a one-off task with this command; the same migrate the
#   Makefile runs locally, spelled inside the image. `cwd` is where the buildpack put the code.
# - `image`: a second image built from another entry point — Go's `cmd/migrate` — because ko builds one
#   binary per image, and the one-off task runs that image with its own entry point.
# - `environment`: the framework migrates the schema itself as the service starts, switched on by this
#   environment in production only; locally the default stays off, for the reasons the properties file
#   gives. Flyway holds a lock, so two replicas starting at once take turns rather than colliding.
def migrations_in_production(backend: str) -> dict[str, Any]:
    """How this backend's migrations run once it is an image: its own `migrations_in_production` answer."""
    return registry().answer(backend, MIGRATIONS_IN_PRODUCTION)


def image_builder(backend: str) -> dict[str, Any]:
    """How a service on this backend becomes an image: the backend's own `image_builder` answer."""
    return registry().answer(backend, IMAGE_BUILDER)


def tools_needed(backends: list[str]) -> list[str]:
    """The image-building tools the deploy workflow installs beyond each family's toolchain, once each."""
    tools = (image_builder(backend)["tool"] for backend in backends)
    return list(dict.fromkeys(tool for tool in tools if tool))


def spelled(text: str, path: str, image: str, repository: str) -> str:
    """One recipe, for one service and one image reference."""
    return text.replace(APP, path).replace(IMAGE, image).replace(REPOSITORY, repository)
