import json
import configparser
import subprocess

import pytest

from usdaeco_suite import checks
from usdaeco_suite.checkout import git, modules, restore, tag_commit
from usdaeco_suite.pins import LAYOUT


def command(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def commit(root, message):
    command(root, "add", ".")
    command(root, "-c", "user.name=Suite Tests", "-c", "user.email=suite@example.invalid",
            "commit", "-m", message)


@pytest.fixture
def checkout(tmp_path):
    command(tmp_path, "init", "-b", "main")
    repos = []
    config = []
    for path in ("core/usdaeco-core", "section/usdaeco-axis"):
        repo = tmp_path / path
        repo.mkdir(parents=True)
        command(repo, "init", "-b", "main")
        (repo / "source.txt").write_text("released\n")
        commit(repo, "Release fixture")
        command(repo, "tag", "v1.0.0")
        released = git(repo, "rev-parse", "HEAD")
        (repo / "source.txt").write_text("next\n")
        commit(repo, "Next fixture")
        command(repo, "-c", "user.name=Suite Tests", "-c", "user.email=suite@example.invalid",
                "tag", "-a", "v1.1.0", "-m", "Annotated fixture")
        config += [f'[submodule "{path}"]', f'  path = {path}', f'  url = ../{repo.name}.git']
        repos.append({"name": repo.name, "path": path, "tag": "v1.0.0", "released": released})
    (tmp_path / ".gitmodules").write_text("\n".join(config) + "\n")
    command(tmp_path, "add", ".")
    return tmp_path, {"repos": repos}


def test_restore_is_read_only_by_default_and_apply_uses_tags(checkout):
    root, document = checkout
    before = [git(root / p["path"], "rev-parse", "HEAD") for p in document["repos"]]
    assert all(row.endswith("differs") for row in restore(root, document))
    assert before == [git(root / p["path"], "rev-parse", "HEAD") for p in document["repos"]]
    assert all(row.endswith("pinned") for row in restore(root, document, apply=True))
    assert [p["released"] for p in document["repos"]] == [git(root / p["path"], "rev-parse", "HEAD") for p in document["repos"]]


def test_dirty_later_submodule_prevents_all_checkout_changes(checkout):
    root, document = checkout
    before = [git(root / p["path"], "rev-parse", "HEAD") for p in document["repos"]]
    later = root / document["repos"][1]["path"]
    (later / "untracked.txt").write_text("preserve this\n")
    with pytest.raises(ValueError, match="local changes"):
        restore(root, document, apply=True)
    assert before == [git(root / p["path"], "rev-parse", "HEAD") for p in document["repos"]]
    assert (later / "untracked.txt").read_text() == "preserve this\n"


def test_annotated_tag_resolves_to_commit(checkout):
    root, document = checkout
    repo = root / document["repos"][0]["path"]
    assert tag_commit(repo, "v1.1.0") == git(repo, "rev-parse", "HEAD")
    assert tag_commit(repo, "v1.1.0") != git(repo, "rev-parse", "refs/tags/v1.1.0")


def test_uninitialized_submodule_cannot_resolve_superproject_tag(checkout):
    root, _ = checkout
    empty = root / "data/empty"
    empty.mkdir(parents=True)
    with pytest.raises(ValueError, match="not initialized"):
        tag_commit(empty, "v1.0.0")


def test_gate_rejects_head_and_gitlink_drift(checkout):
    root, document = checkout
    index = root / LAYOUT["usdaeco-scenarios"]
    index.mkdir(parents=True)
    (index / "releases.json").write_text(json.dumps({
        "train": "test-1.0.0", "repos": [{"name": name, "released": "v1.0.0"} for name in LAYOUT],
    }))
    pin = document["repos"][0]
    with pytest.raises(ValueError, match="gitlink differ"):
        checks.pin(root, pin)
    restore(root, document, apply=True)
    # HEAD now matches the tag, but the index still records the later commit.
    with pytest.raises(ValueError, match="gitlink differ"):
        checks.pin(root, pin)
    command(root, "add", pin["path"])
    assert "v1.0.0" in checks.pin(root, pin)


@pytest.mark.parametrize("defect", ["escape", "duplicate", "branch"])
def test_modules_reject_unsafe_or_ambiguous_declarations(checkout, defect):
    root, _ = checkout
    path = root / ".gitmodules"
    text = path.read_text()
    if defect == "escape":
        text = text.replace("core/usdaeco-core", "../outside")
    elif defect == "duplicate":
        text += text
    else:
        text += "  branch = main\n"
    path.write_text(text)
    with pytest.raises((ValueError, configparser.Error)):
        modules(root)
