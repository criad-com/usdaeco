"""Inspect pins, or explicitly restore clean submodules to their recorded tags."""
import argparse
import configparser
from pathlib import Path, PurePosixPath
import re
import subprocess


def git(root, *args):
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True,
        check=False, timeout=120,
    )
    if result.returncode:
        raise ValueError(f"git {args[0]} failed (exit {result.returncode})")
    return result.stdout.strip()


def modules(root):
    """Read strict, unique submodule names and portable paths."""
    parser = configparser.ConfigParser(interpolation=None)
    parser.read_string((Path(root) / ".gitmodules").read_text())
    result = {}
    for section in parser.sections():
        match = re.fullmatch(r'submodule "([^"]+)"', section)
        if not match or set(parser[section]) != {"path", "url"}:
            raise ValueError("invalid .gitmodules entry")
        path = parser[section]["path"]
        parts = PurePosixPath(path).parts
        if (len(parts) != 2 or any(p in {".", ".."} for p in parts)
                or str(PurePosixPath(path)) != path or "\\" in path
                or PurePosixPath(path).is_absolute() or path != match[1]
                or path in result):
            raise ValueError("invalid or duplicate submodule path")
        result[path] = parser[section]["url"]
    if not result:
        raise ValueError("no submodules declared")
    return result


def gitlinks(root):
    """Return the full commit IDs recorded in the superproject index."""
    result = {}
    for record in git(root, "ls-files", "--stage", "-z").split("\0"):
        if not record:
            continue
        fields, path = record.split("\t", 1)
        mode, commit, stage = fields.split()
        if mode == "160000":
            if stage != "0" or not re.fullmatch(r"[a-f0-9]{40}", commit):
                raise ValueError("unmerged or invalid gitlink")
            result[path] = commit
    return result


def require_checkout(root):
    root = Path(root).resolve()
    if not (root / ".git").exists() or Path(git(root, "rev-parse", "--show-toplevel")) != root:
        raise ValueError("submodule is not initialized; run git submodule update --init")


def tag_commit(root, tag):
    if not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
        raise ValueError("an exact release tag is required")
    require_checkout(root)
    return git(root, "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}")


def restore(root, document, *, apply=False):
    """Preflight the whole selection before changing any HEAD; never fetch."""
    from usdaeco_suite.pins import pin_target
    declared = modules(root)
    planned = []
    for repo in document["repos"]:
        path = repo["path"]
        if path not in declared:
            raise ValueError("pin path is not a declared submodule")
        checkout = Path(root) / path
        target = pin_target(root, repo.get("name", Path(path).name), repo["tag"])
        current = git(checkout, "rev-parse", "HEAD")
        dirty = bool(git(checkout, "status", "--porcelain", "--untracked-files=all"))
        if apply and dirty:
            raise ValueError(f"{path}: local changes; no submodules changed")
        planned.append((checkout, path, repo["tag"], target, current, dirty))
    rows = []
    for checkout, path, tag, target, current, dirty in planned:
        if apply and current != target:
            git(checkout, "checkout", "--detach", target)
        state = "dirty" if dirty else "pinned" if current == target or apply else "differs"
        rows.append(f"{path} {tag} {target} {state}")
    return rows


def main(argv=None):
    from usdaeco_suite.pins import read_json, validate_document

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--apply", action="store_true", help="restore clean submodules; default only reports")
    args = parser.parse_args(argv)
    try:
        document = read_json(args.root / "suite.json")
        validate_document(document)
        print("== stage: checkout", flush=True)
        for row in restore(args.root, document, apply=args.apply):
            print(row)
    except (ValueError, OSError, configparser.Error, subprocess.TimeoutExpired) as exc:
        detail = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        print(f"FAIL checkout: {detail}")
        return 1
    return 0


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    raise SystemExit(main())
