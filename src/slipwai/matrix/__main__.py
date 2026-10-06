"""`python -m slipwai.matrix <language-dir> <package>`: a package's matrix from a shell, as its maintainer runs it.

The plan first — one line per row, the `slipwai generate` it stands for, and one per image — then every test of the
package's matrix cases, opted in, as `unittest` reports them, then `matrix: <package> passed` or `… failed`, with
`(N skipped)` where any test skipped. `--list` prints the plan and runs nothing. Exit 0 when it passed or there was
nothing to run, 1 when it failed, 2 for a usage error, 3 when the matrix could not be planned, and 130 or 143 when
Ctrl-C or SIGTERM stopped it, every project it generated removed — never a traceback for any of them.
"""
from __future__ import annotations

import argparse
import signal
import sys
import unittest
from pathlib import Path

from ..assets import VERSION
from ..conformance.run import require_package_name
from .case import Stopped
from .run import Plan, plan
from .suite import cases, suite


def lines(planned: Plan) -> list[str]:
    """The plan as the command line prints it."""
    said = [f"matrix: {planned.package} in {planned.directory}, against slipwai {VERSION}"]
    if not planned.backends:
        return [*said, f"matrix: {planned.package} owns no backend of its own, so it has no rows: the matrices of the "
                       "frameworks beside it generate it"]
    said += [f"  {row.name}: slipwai generate {row.name} {' '.join(row.arguments())}" for row in planned.rows]
    return said + [f"  {image.row.name}: image ({image.tool or 'maven'}), answers {image.ready}"
                   for image in planned.images]


def verdict(package: str, result: unittest.TestResult) -> str:
    """The run's last line: `passed` or `failed`, with how many tests skipped where any did."""
    said = f"matrix: {package} {'passed' if result.wasSuccessful() else 'failed'}"
    return f"{said} ({len(result.skipped)} skipped)" if result.skipped else said


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m slipwai.matrix",
        description="Generate every native-gate variant of a language package's backends and hold each to its own "
        "`make verify`; build and start each backend's image where Docker is here.",
    )
    parser.add_argument("language_dir", metavar="language-dir", type=Path,
                        help="the directory holding the package (and, for a framework, its family)")
    parser.add_argument("package", help="the package's directory name in it, e.g. go or java-quarkus")
    parser.add_argument("--list", action="store_true", help="print the rows and run nothing")
    args = parser.parse_args(argv)
    if not args.language_dir.is_dir():
        parser.error(f"{args.language_dir} is not a directory")
    try:
        require_package_name(args.package)
    except ValueError as error:
        parser.error(str(error))
    previous = signal.signal(signal.SIGTERM, stop)
    try:
        return matrix(args.language_dir, args.package, args.list)
    except KeyboardInterrupt as error:
        # Every project the run generated is removed by the case's cleanups before the interrupt reaches here.
        how, number = ("stopped by SIGTERM", signal.SIGTERM) if isinstance(error, Stopped) else ("interrupted",
                                                                                                 signal.SIGINT)
        print(f"\nmatrix: {args.package} {how}; what it generated is removed", file=sys.stderr)
        return 128 + number
    finally:
        signal.signal(signal.SIGTERM, previous)


def stop(_number: int, _frame: object) -> None:
    """A SIGTERM (CI cancelling a job, `timeout`) ends the run as an interrupt, so what it generated is removed."""
    raise Stopped


def matrix(language_dir: Path, package: str, listed: bool) -> int:
    """Plan `package`'s matrix in `language_dir`, print the plan, and run it unless `listed`: the exit code."""
    try:
        planned = plan(language_dir, package)
        found = cases(language_dir, package)
    except RuntimeError as error:
        print(f"matrix: {error}", file=sys.stderr)
        return 3
    except OSError as error:
        print(f"matrix: the matrix for {package} could not be planned: {error}", file=sys.stderr)
        return 3
    print("\n".join(lines(planned)), flush=True)
    if listed or not planned.backends:
        return 0
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite(found))
    print(verdict(package, result))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
