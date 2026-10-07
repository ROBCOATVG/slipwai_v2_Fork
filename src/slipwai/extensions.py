"""What an extension is: an optional dev-tooling hook `./init --extension <key>` can run.

Unlike an axis, an extension is not a product-architecture choice — it never changes the generated
skeleton's code, so it carries none of an axis's per-backend or per-target matrix. It is answered later than
generation too: at `./init` time, the same moment a Spec Kit agent integration is chosen, rather than baked
into `apps`/`Selection` at `slipwai generate` time. A second extension is a package of its own — an
`extension.json` and the files its hooks name, installed into the package directory and folded in here —
rather than a row in the keel's own `catalog.json`. The keel
ships none: an extension that lived in the keel would be a dev tool every project carries the description of
whether or not anyone wanted it, and version 1's three were exactly that. See `docs/extensions.md` for the
six obligations an entry point meets, and `extension_shape.py` for what the manifest declares.
"""
from __future__ import annotations

from .extension_directory import Extension, refusal

REQUIRED = ("name", "description")
OPTIONAL_STRINGS = ("ignore",)


def validate_extensions(catalog: dict) -> None:
    """Every extension declares a name and a description; `ignore`, if present, is gitignore text."""
    extensions = catalog.get("extensions", {})
    if not isinstance(extensions, dict):
        raise ValueError("catalog extensions must be an object")
    for key, spec in extensions.items():
        if not isinstance(spec, dict):
            raise ValueError(f"extensions/{key} must be an object")
        for field in REQUIRED:
            if not isinstance(spec.get(field), str) or not spec[field]:
                raise ValueError(f"extensions/{key} must declare a non-empty {field}")
        for field in OPTIONAL_STRINGS:
            if field in spec and not isinstance(spec[field], str):
                raise ValueError(f"extensions/{key}.{field} must be a string")
        unknown = set(spec) - set(REQUIRED) - set(OPTIONAL_STRINGS)
        if unknown:
            raise ValueError(f"extensions/{key} declares unknown field(s): {', '.join(sorted(unknown))}")


def known_extensions(catalog: dict) -> dict:
    """The catalog's `extensions`, keyed the way `init_script.py`/`gitignore.py` read them."""
    return catalog.get("extensions", {})


def merge_packages(catalog: dict, extensions: list[Extension]) -> list[str]:
    """Fold each installed extension's catalogue entry into `catalog`, and return a line for each refused.

    The one thing refused here rather than in the manifest is a key something already holds. A manifest is
    right or wrong on its publisher's machine; a collision is a fact about this machine, and it is refused
    rather than resolved because either order of "last one wins" means a project generated today differs
    from one generated yesterday for a reason nobody wrote down.
    """
    block = catalog.setdefault("extensions", {})
    refusals: list[str] = []
    for extension in extensions:
        if extension.name in block:
            refusals.append(refusal(extension.name, extension.root,
                                    f"is already loaded; two packages cannot both be `{extension.name}`"))
            continue
        block[extension.name] = extension.entry
    return refusals
