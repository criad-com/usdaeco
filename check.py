"""Offline suite gate; summary contract: N checks, M failed."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "kits/usdaeco-toolchain/tools"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--term-pattern", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        from usdaeco_check.report import Report
        from usdaeco_check.structure import check_structure
        from usdaeco_suite import checks
        from usdaeco_suite.pins import read_json
    except ImportError:
        print("FAIL bootstrap: initialize submodules; use Python 3.11+ with Pillow and pytest")
        print("1 checks, 1 failed")
        return 1

    report = Report()

    def run(name, function, *arguments):
        try:
            detail = function(ROOT, *arguments)
            report.check(name, True, detail)
        except Exception as exc:
            # Diagnostics must not expose a deployment path or matched private text.
            detail = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
            detail = detail.replace(str(ROOT), "<repo>")
            report.check(name, False, detail)

    print("== stage: suite structure", flush=True)
    adaptations = {
        1: checks.root_files, 2: checks.readme, 3: checks.metadata,
        4: checks.inventory, 5: checks.flake, 25: lambda root: checks.terms(root, args.term_pattern),
    }
    shared = {result.name: result for result in check_structure(
        ROOT, only={f"S{number:02d}" for number in range(1, 30) if number not in adaptations})}
    for number in range(1, 30):
        name = f"S{number:02d}"
        if number in adaptations:
            run(name, adaptations[number])
        else:
            report.add(shared[name])

    print("== stage: released submodules", flush=True)
    try:
        repos = read_json(ROOT / "suite.json")["repos"]
    except (OSError, ValueError, KeyError):
        repos = []
        report.check("pins", False, "suite.json unavailable")
    for repo in repos:
        run("pin " + repo.get("name", "invalid"), checks.pin, repo)

    print("== stage: generated files and documentation", flush=True)
    for name, function in (("generated", checks.fresh), ("versions", checks.versions),
                           ("docs links", checks.docs), ("site assets", checks.site)):
        run(name, function)
    return report.finish()


if __name__ == "__main__":
    raise SystemExit(main())
