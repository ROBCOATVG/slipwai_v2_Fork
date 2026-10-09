"""The two probes every generated service answers, and what each is for.

They answer two different questions, and the whole point of there being two is that a platform asks them of
different things.

**Liveness** — `HEALTH_PATH` — is "this process is up and answering". It asks nothing of any dependency, on
purpose: a liveness probe that goes red because a database is unreachable gets the process *restarted*,
turning somebody else's outage into a crash loop of this project's.

**Readiness** — `ready_path`, per backend — is "send me traffic". It runs a trivial query through the
store port — the event store on the `events` rung, the repository on `state` — so a service whose store has
gone away is taken out of the pool rather than left serving
failures. Everything that gates traffic waits on this one: the Compose healthcheck, the ALB target group,
the Container Apps readiness probe, and `make smoke` against a deployed environment.

A separate module from `backends.py` because both paths and the liveness body are read by the parts that
write Compose, the infrastructure variables, the docs and the run skill. Each backend's readiness path and
liveness body are answers in its own `LANGUAGE` object (`project/languages/`), read here through the
registry; why a framework-owning backend answers differently is written beside those answers.
"""
from __future__ import annotations

from .registry import HEALTH_BODY, READY_PATH, registry

# The liveness probe every backend agrees on, for the same reason the port is named once: `make demo`
# prints it, `skills/run-the-app` tells the reader to curl it and quotes what comes back, and on a platform
# that asks liveness separately it is the path that decides a restart. Several literals in several files
# was one contract nobody could see, and the first backend to disagree with it would have disagreed
# silently.
HEALTH_PATH = "/health"


def ready_path(backend: str) -> str:
    """Where this backend answers "send me traffic" — what Compose, the ALB and the App Service wait on."""
    return registry().answer(backend, READY_PATH)


def health_body(backend: str) -> str:
    """What this backend's liveness probe answers with, for prose that quotes it."""
    return registry().answer(backend, HEALTH_BODY)
