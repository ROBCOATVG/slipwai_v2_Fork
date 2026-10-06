"""Reading `project.json` back, and the language record in its `generator`: the package's two modules, by name.

`reading` turns the written manifest back into the list of applications and refuses one this keel does not
understand; `languages` is the record of the packages that wrote the project (ADR 0005) and what holds it to what is
installed. Every reader imports from here.
"""
from ..origin import ORIGINS, origin_of
from .languages import (
    answering,
    generator,
    languages_record,
    loaded_versions,
    package_version,
    recorded_languages,
    refuse_older,
    wrote_here,
)
from .reading import (
    MANIFEST_SCHEMA,
    PROVENANCES,
    REQUIRED,
    apps_from_manifest,
    check_known,
    read_manifest,
    recorded_contexts,
    refuse_missing_languages,
    refuse_outside,
)

__all__ = [
    "MANIFEST_SCHEMA", "ORIGINS", "PROVENANCES", "REQUIRED", "answering", "apps_from_manifest", "check_known",
    "generator", "languages_record", "loaded_versions", "origin_of", "package_version", "read_manifest",
    "recorded_contexts", "recorded_languages", "refuse_missing_languages", "refuse_older", "refuse_outside",
    "wrote_here",
]
