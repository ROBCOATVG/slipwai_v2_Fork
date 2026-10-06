"""`python -m slipwai.conformance <language-dir> <package>`: the suite from a shell, as a language author runs it.

One line per check, `ok` or `FAILED` with each finding indented under it, or `not run` with the reason, and a last
line saying whether the package passed. Exit 0 when it did, 1 when it did not, 2 for a usage error, and 3 when the
suite itself could not run — never a traceback for any of them.
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

from ..assets import VERSION
from .run import CHECKS, Report, check, require_package_name


def lines(report: Report) -> list[str]:
    """The report as the command line prints it."""
    said = [f"conformance: {report.package} in {report.directory}, against slipwai {VERSION}"]
    for name in CHECKS:
        if name in report.not_run:
            said.append(f"  {name:<11} not run: {report.not_run[name]}")
        elif name in report.findings:
            found = report.findings[name]
            said += [f"  {name:<11} {'FAILED' if found else 'ok'}", *(f"    {finding}" for finding in found)]
    count = report.count()
    verdict = "passed" if report.passed else f"failed, {count} finding{'' if count == 1 else 's'}"
    return [*said, f"conformance: {report.package} {verdict}"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m slipwai.conformance",
        description="Check a language package against this slipwai: every protocol member, every example marker, "
        "both profiles, every declared target, its prune rows and its version rule.",
    )
    parser.add_argument("language_dir", metavar="language-dir", type=Path,
                        help="the directory holding the package (and, for a framework, its family)")
    parser.add_argument("package", help="the package's directory name in it, e.g. go or java-quarkus")
    args = parser.parse_args(argv)
    if not args.language_dir.is_dir():
        parser.error(f"{args.language_dir} is not a directory")
    try:
        require_package_name(args.package)
    except ValueError as error:
        parser.error(str(error))
    # A path that is not text, or a stream that cannot encode it, is printed escaped and never a traceback.
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(errors="backslashreplace")
    try:
        report = check(args.language_dir, args.package)
    except (OSError, RuntimeError) as error:
        print(f"conformance: the suite could not run: {error}", file=sys.stderr)
        return 3
    print("\n".join(lines(report)))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
