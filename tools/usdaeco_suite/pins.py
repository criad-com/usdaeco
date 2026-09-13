"""Generate suite.json, matching flake inputs and the documentation map."""
import argparse
import configparser
import json
from pathlib import Path
import re
import sys
import subprocess

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from usdaeco_suite.checkout import git, modules, tag_commit

TIERS = {
    "core": ("usdaeco-core",),
    "section": ("usdaeco-axis", "usdaeco-buildup"),
    "kind": ("usdaeco-wall", "usdaeco-pipe", "usdaeco-cctv", "usdaeco-clash",
             "usdaeco-plan", "usdaeco-repeat", "usdaeco-compliance", "usdaeco-solid"),
    "record": ("usdaeco-sync",),
    "hosts": ("usdaeco-ifc", "usdaeco-revit", "usdaeco-bonsai"),
    "kits": ("usdaeco-toolchain", "aeco-toolchain", "usdaeco-cctv-exec", "usdSolid", "usdSolidOcct"),
    "data": ("usdaeco-datacentre",),
    "gate": ("usdaeco-scenarios",),
}
LAYOUT = {name: f"{tier}/{name}" for tier, names in TIERS.items() for name in names}
FLAKE_REPOS = {"aeco-toolchain", "usdaeco-toolchain"}
FIELDS = {"name", "path", "tier", "kind", "library", "tag", "requires"}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, document):
    Path(path).write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def release_index(root):
    """Discover the scenarios release index by its data contract."""
    matches = []
    for path in (Path(root) / LAYOUT["usdaeco-scenarios"]).glob("*.json"):
        data = read_json(path)
        if (isinstance(data, dict) and isinstance(data.get("train"), str)
                and isinstance(data.get("repos"), list) and data["repos"]
                and all(isinstance(p, dict) and "released" in p for p in data["repos"])):
            matches.append(data)
    if len(matches) != 1:
        raise ValueError("expected one scenarios release index")
    data = matches[0]
    released = {p["name"]: p for p in data["repos"] if p["released"] is not None}
    if len(released) != sum(p["released"] is not None for p in data["repos"]):
        raise ValueError("duplicate released repository")
    if not set(LAYOUT) <= set(released):
        raise ValueError("release index is missing public suite repositories")
    return data["train"], {name: released[name] for name in LAYOUT}


def overrides(root):
    """Explicit suite advances beyond the baseline train, with revision evidence."""
    path = Path(root) / "suite-overrides.json"
    data = read_json(path) if path.exists() else {}
    for name, item in data.items():
        if (name not in LAYOUT or set(item) != {"tag", "revision", "status", "reason"}
                or not re.fullmatch(r"v\d+\.\d+\.\d+", item["tag"])
                or not re.fullmatch(r"[a-f0-9]{40}", item["revision"])
                or item["status"] not in {"released", "awaiting-tag"} or not item["reason"]):
            raise ValueError("invalid suite override")
    return data


def pin_target(root, name, tag):
    item = overrides(root).get(name)
    checkout = Path(root) / LAYOUT[name]
    if item and item["tag"] != tag:
        raise ValueError("override tag differs from pin")
    if item and item["status"] == "awaiting-tag":
        try:
            released = tag_commit(checkout, tag)
        except ValueError:
            return git(checkout, "rev-parse", "--verify", item["revision"] + "^{commit}")
        if released != item["revision"]:
            raise ValueError("release arrived; refresh the temporary revision pin")
        return released
    target = tag_commit(checkout, tag)
    if item and target != item["revision"]:
        raise ValueError("override release revision differs")
    return target


def validate_document(document):
    if set(document) != {"train", "repos"} or not isinstance(document["train"], str):
        raise ValueError("invalid suite document")
    repos = document["repos"]
    if not isinstance(repos, list) or len(repos) != len(LAYOUT):
        raise ValueError("invalid suite repository count")
    names = []
    for repo in repos:
        if set(repo) != FIELDS:
            raise ValueError("invalid suite entry fields")
        name = repo["name"]
        if name not in LAYOUT or repo["path"] != LAYOUT[name]:
            raise ValueError("invalid repository name or tier path")
        if repo["tier"] != repo["path"].split("/")[0]:
            raise ValueError("tier differs from layout")
        if not isinstance(repo["tag"], str) or not re.fullmatch(r"v\d+\.\d+\.\d+", repo["tag"]):
            raise ValueError("invalid release tag")
        if not isinstance(repo["requires"], dict) or not isinstance(repo["kind"], str):
            raise ValueError("invalid repository metadata")
        if repo["library"] is not None and not isinstance(repo["library"], str):
            raise ValueError("invalid schema domain name")
        names.append(name)
    if set(names) != set(LAYOUT) or len(set(names)) != len(names):
        raise ValueError("duplicate or missing suite repository")


def generate(root):
    root = Path(root)
    declared = modules(root)
    if set(declared) != set(LAYOUT.values()):
        raise ValueError("submodule paths differ from the tier layout")
    train, released = release_index(root)
    repos = []
    for tier, names in TIERS.items():
        for name in names:
            path = LAYOUT[name]
            checkout = root / path
            card = released[name]
            manifest_path = checkout / "library.json"
            if manifest_path.is_file():
                metadata = read_json(manifest_path)
                tag = "v" + metadata["version"]
                library = metadata["name"] if metadata["name"].startswith("usd") and not metadata["name"].startswith("usdaeco-") else None
            elif name == "aeco-toolchain":
                # This released kit predates root metadata; the index is authoritative.
                metadata = card
                library = card["library"]
                tag = card["released"]
            else:
                raise ValueError(f"{path}: missing library.json")
            if git(checkout, "rev-parse", "HEAD") != pin_target(root, name, tag):
                raise ValueError(f"{path}: HEAD differs from the metadata release tag")
            if git(checkout, "status", "--porcelain", "--untracked-files=all"):
                raise ValueError(f"{path}: local changes prevent pin generation")
            repos.append(dict(name=name, path=path, tier=tier, kind=metadata["kind"],
                              library=library, tag=tag, requires=metadata["requires"]))
    document = dict(train=train, repos=repos)
    validate_document(document)
    return document


def flake_inputs(document):
    lines = []
    for repo in document["repos"]:
        name, tag = repo["name"], repo["tag"]
        lines.append(f'    {name}.url = "github:criad-com/{name}?ref={tag}";')
        if name not in FLAKE_REPOS:
            lines.append(f"    {name}.flake = false;")
    lines += [
        '    usdaeco-toolchain.inputs.aeco-toolchain.follows = "aeco-toolchain";',
        '    usdaeco-toolchain.inputs.core.follows = "usdaeco-core";',
        '    nixpkgs.follows = "aeco-toolchain/nixpkgs";',
    ]
    return "\n".join(lines) + "\n"


def render_flake(root, document):
    text = (Path(root) / "flake.nix").read_text()
    before, rest = text.split("    # BEGIN GENERATED INPUTS\n", 1)
    _, after = rest.split("    # END GENERATED INPUTS\n", 1)
    return before + "    # BEGIN GENERATED INPUTS\n" + flake_inputs(document) + "    # END GENERATED INPUTS\n" + after


def render_map(document):
    lines = ["# usdAECO suite map", "", f"Release train: `{document['train']}`.", "",
             "Each repository is a submodule at the tag shown. Paths are relative to this checkout.",
             "See the [HTML guide](index.html), [Working with the integrated stage](stage/index.html)",
             "and [stage setup and reproduction](../stage/README.md).", ""]
    for tier in TIERS:
        lines += [f"## {tier}", ""]
        for repo in document["repos"]:
            if repo["tier"] == tier:
                name, path, tag = repo["name"], repo["path"], repo["tag"]
                lines.append(f"- [{name}](../{path}/README.md) · [docs](../{path}/docs/) · `{tag}`")
        lines.append("")
    return "\n".join(lines)


def generated_files(root, document):
    return {
        "suite.json": json.dumps(document, indent=2) + "\n",
        "flake.nix": render_flake(root, document),
        "docs/suite.md": render_map(document),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--check", action="store_true", help="verify freshness without writing")
    args = parser.parse_args(argv)
    print("== stage: pins", flush=True)
    try:
        document = generate(args.root)
        files = generated_files(args.root, document)
        stale = [path for path, content in files.items()
                 if not (args.root / path).is_file() or (args.root / path).read_text() != content]
        if args.check and stale:
            print("FAIL stale generated files: " + ", ".join(stale))
            return 1
        if not args.check:
            for path, content in files.items():
                (args.root / path).write_text(content, encoding="utf-8")
        print(f"{len(document['repos'])} pins, {len(files)} generated files " + ("verified" if args.check else "written"))
    except (ValueError, OSError, KeyError, TypeError, configparser.Error, subprocess.TimeoutExpired) as exc:
        detail = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        print(f"FAIL pins: {detail}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
