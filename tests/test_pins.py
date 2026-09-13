from copy import deepcopy
from pathlib import Path

import pytest

from usdaeco_suite import checks
from usdaeco_suite.pins import read_json, validate_document, write_json

ROOT = Path(__file__).resolve().parents[1]


def test_pin_document_roundtrip(tmp_path):
    path = tmp_path / "suite.json"
    document = {"train": "aeco-0.8.1", "repos": []}
    write_json(path, document)
    assert read_json(path) == document
    first = path.read_bytes()
    write_json(path, read_json(path))
    assert path.read_bytes() == first


@pytest.mark.parametrize("defect", ["duplicate", "path", "tier", "tag", "fields", "count"])
def test_document_rejects_pin_defects(defect):
    document = deepcopy(read_json(ROOT / "suite.json"))
    if defect == "duplicate":
        document["repos"][1] = document["repos"][0]
    elif defect == "path":
        document["repos"][0]["path"] = "../outside"
    elif defect == "tier":
        document["repos"][0]["tier"] = "kind"
    elif defect == "tag":
        document["repos"][0]["tag"] = "main"
    elif defect == "fields":
        document["repos"][0]["extra"] = True
    else:
        document["repos"].pop()
    with pytest.raises(ValueError):
        validate_document(document)


@pytest.mark.parametrize("defect", ["tag", "owner", "source_flag", "duplicate", "extra_url"])
def test_flake_rejects_input_drift(tmp_path, defect):
    (tmp_path / "suite.json").write_bytes((ROOT / "suite.json").read_bytes())
    text = (ROOT / "flake.nix").read_text()
    if defect == "tag":
        text = text.replace("?ref=v0.9.5", "?ref=v0.9.4", 1)
    elif defect == "owner":
        text = text.replace("github:criad-com/usdaeco-core", "github:example/usdaeco-core", 1)
    elif defect == "source_flag":
        text = text.replace("usdaeco-core.flake = false", "usdaeco-core.flake = true", 1)
    elif defect == "duplicate":
        text += '\nusdaeco-core.url = "github:criad-com/usdaeco-core?ref=v0.9.5";\n'
    else:
        text += '\nextra = { url = "github:example/extra?ref=v1.0.0"; };\n'
    (tmp_path / "flake.nix").write_text(text)
    with pytest.raises(ValueError):
        checks.flake(tmp_path)
