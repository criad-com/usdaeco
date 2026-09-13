"""Suite adaptations of the repository skeleton and offline acceptance checks."""
import hashlib
from pathlib import Path
import re
import tomllib

from usdaeco_suite.checkout import git, gitlinks, modules, tag_commit
from usdaeco_suite.docs import check_links
from usdaeco_suite.pins import (
    FLAKE_REPOS, LAYOUT, generate, generated_files, read_json, release_index, validate_document,
    overrides, pin_target,
)
from usdaeco_suite.sweep import expected_url, repository_files, sweep


def require(ok, detail):
    if not ok:
        raise ValueError(detail)


def root_files(root):
    from usdaeco_check.licences import check_licence

    required = ("README.md LICENSE CHANGELOG.md library.json suite.json flake.nix check.py build.sh "
                "pyproject.toml stage/README.md docs/suite.md testenv/smoke.py tests/conftest.py").split()
    require(all((root / path).is_file() for path in required), "missing skeleton file")
    detail = check_licence(root, read_json(root / "library.json"), repository_files(root))
    return f"{len(required)} required files; {detail}"


def readme(root):
    text = (root / "README.md").read_text()
    require(re.findall(r"(?m)^# (.+)$", text) == ["usdaeco — the usdAECO suite"], "README title differs")
    require(re.findall(r"(?m)^## (.+)$", text) == [
        "Use case", "The schema on an index card", "The example", "Build and check",
        "Suite", "Layout", "Status", "Licence"], "README heading order differs")
    return "suite vocabulary; eight sections"


def metadata(root):
    data = read_json(root / "library.json")
    require(data.keys() == {"name", "version", "kind", "tier", "requires", "licence"}, "suite metadata fields differ")
    require(data["name"] == "usdaeco" and data["kind"] == data["tier"] == "suite"
            and data["requires"] == {} and data["licence"] == "MIT", "suite metadata differs")
    require(bool(re.fullmatch(r"\d+\.\d+\.\d+", data["version"])), "invalid semantic version")
    return "suite kind and tier; MIT; no schema requirements"


def inventory(root):
    document = read_json(root / "suite.json")
    validate_document(document)
    declared = modules(root)
    links = gitlinks(root)
    paths = {repo["path"] for repo in document["repos"]}
    require(paths == set(links) == set(declared) == set(LAYOUT.values()), "submodule sets differ")
    require(all(url == expected_url(Path(path).name) for path, url in declared.items()), "relative submodule URLs differ")
    train, released = release_index(root)
    require(train == document["train"], "train name differs from the scenarios index")
    expected = {name: p["released"] for name, p in released.items()}
    expected.update({name: p["tag"] for name, p in overrides(root).items()})
    require({p["name"]: p["tag"] for p in document["repos"]} == expected,
            "pins differ from the baseline and explicit suite advances")
    return f"{len(paths)} gitlinks = suite entries = module declarations = released repositories"


def flake(root):
    document = read_json(root / "suite.json")
    text = re.sub(r"(?m)^\s*#.*$", "", (root / "flake.nix").read_text())
    urls = re.findall(r'([\w-]+)\.url\s*=\s*"([^"]+)"\s*;', text)
    expected = {p["name"]: f"github:criad-com/{p['name']}?ref={p['tag']}" for p in document["repos"]}
    require(len(urls) == len(expected) and dict(urls) == expected, "flake input URLs differ from pins")
    require(len(re.findall(r'\burl\s*=', text)) == len(expected), "unexpected flake URL declaration")
    flags = re.findall(r'([\w-]+)\.flake\s*=\s*(true|false)\s*;', text)
    require(len(flags) == len(expected) - len(FLAKE_REPOS)
            and dict(flags) == {name: "false" for name in expected if name not in FLAKE_REPOS},
            "flake source flags differ")
    require('nixpkgs.follows = "aeco-toolchain/nixpkgs";' in text, "toolchain nixpkgs follow missing")
    require("pins = assert pinsAgree;" in text and "usdaeco-toolchain.packages.${system}.pythonEnv" in text,
            "pin assertion or toolchain Python shell missing")
    return f"{len(urls)} matching public tag URLs; 21 source inputs; 2 toolchain flakes"


def pin(root, repo):
    path = repo["path"]
    tag = repo["tag"]
    checkout = root / path
    target = pin_target(root, repo["name"], tag)
    require(git(checkout, "rev-parse", "HEAD") == target == gitlinks(root)[path],
            "HEAD, resolved release tag and recorded gitlink differ")
    require(not git(checkout, "status", "--porcelain", "--untracked-files=all"), "submodule has local changes")
    return f"{tag} {target}; clean"


def fresh(root):
    document = generate(root)
    for path, content in generated_files(root, document).items():
        require((root / path).read_text() == content, f"{path}: stale generated content")
    return "23 metadata/tag entries; 3 generated files fresh; 1 documented legacy kit metadata source"


def versions(root):
    version = read_json(root / "library.json")["version"]
    heads = re.findall(r"(?m)^## (\d+\.\d+\.\d+)\b", (root / "CHANGELOG.md").read_text())
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    require(heads and heads[0] == version == project["version"], "version headings differ")
    return f"library.json = CHANGELOG head = pyproject.toml = {version}"


def docs(root):
    pages, local, external, failures = check_links(root)
    require(not failures, "; ".join(failures[:20]))
    return f"{pages} documents; {local} local links/fragments resolved; {external} external links not fetched"


def site(root):
    from PIL import Image, ImageStat

    record = read_json(root / "docs/site.json")
    expected = {"index.html", "stage/index.html", "schemas/usdAeco/overview.html", "_static/aeco.css", "schemas/usdAeco/usdAecoExample.png"}
    require(set(record["files"]) == expected, "site inventory differs")
    total = 0
    for path, entry in record["files"].items():
        content = (root / "docs" / path).read_bytes()
        require(len(content) == entry["bytes"] and hashlib.sha256(content).hexdigest() == entry["sha256"],
                f"{path}: site content differs from site inventory")
        total += len(content)
    png = root / "docs/schemas/usdAeco/usdAecoExample.png"
    with Image.open(png) as image:
        image.load()
        require(image.format == "PNG" and max(image.size) <= 1600 and png.stat().st_size <= 400000,
                "site PNG format or caps differ")
        require(max(ImageStat.Stat(image.convert("RGB")).var) > 0, "site PNG is uniform")
        dimensions = f"{image.width}x{image.height}"
    return f"{len(expected)} site assets, {total} bytes; PNG {dimensions}, non-uniform"


def terms(root, extra_patterns=()):
    count, findings = sweep(root, extra_patterns=extra_patterns)
    require(not findings, "term sweep: " + ", ".join(findings[:20]))
    return f"{count} owned text files; 0 findings; 23 relative URLs"
