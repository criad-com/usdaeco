import pytest

from usdaeco_suite.sweep import expected_url, sweep, text_findings


@pytest.mark.parametrize("text", [
    ".".join(("10", "1", "2", "3")), ".".join(("100", "64", "2", "3")),
    ":".join(("ab", "cd", "ef", "01", "23", "45")),
    "/".join(("", "Users", "example", "checkout")),
    "example." + "local", "https://" + "private-node" + "/repo",
    "fel" + "ix", "u" + "v", "for" + "um-1", "fam" + "ily",
])
def test_sensitive_text_is_rejected_without_echo(text):
    assert text_findings("safe\n" + text + "\n") == [2]


def test_public_org_and_technical_font_syntax_have_narrow_exceptions():
    assert text_findings("https://github.com/criad-com/usdaeco") == []
    token = "fam" + "ily"
    assert text_findings(f"font-{token}: sans-serif;", suffix=".css") == []
    assert text_findings(f"?{token}=Lato&{token}=Roboto", suffix=".html") == []
    assert text_findings(f"/* {token} */", suffix=".css") == [1]
    assert text_findings(f"<p>{token}</p>", suffix=".html") == [1]
    assert text_findings("criad-com", extra_patterns=["criad-com"]) == [1]


def test_exact_relative_kit_urls_are_allowed_but_adjacent_terms_are_scanned(tmp_path):
    import subprocess

    subprocess.run(["git", "-C", str(tmp_path), "init"], check=True, capture_output=True)
    config = tmp_path / ".gitmodules"
    config.write_text('[submodule "kits/usdSolid"]\npath = kits/usdSolid\nurl = ' + expected_url("usdSolid") + "\n")
    assert sweep(tmp_path)[1] == []
    config.write_text(config.read_text() + "# " + ("fel" + "ix") + "\n")
    assert sweep(tmp_path)[1] == [".gitmodules:4"]


def test_tracked_ignored_text_is_scanned(tmp_path):
    import subprocess

    subprocess.run(["git", "-C", str(tmp_path), "init"], check=True, capture_output=True)
    (tmp_path / ".gitmodules").write_text('[submodule "core/usdaeco-core"]\npath = core/usdaeco-core\nurl = ../usdaeco-core.git\n')
    (tmp_path / ".gitignore").write_text("ignored.txt\n")
    (tmp_path / "ignored.txt").write_text("for" + "um-1\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-f", "ignored.txt"], check=True, capture_output=True)
    assert sweep(tmp_path)[1] == ["ignored.txt:1"]
