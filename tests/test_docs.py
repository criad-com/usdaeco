import pytest

from usdaeco_suite.docs import check_links


def test_links_resolve_paths_encoded_names_fragments_and_css(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.html").write_text('<a href="next%20page.html#there">next</a><img src="image.png"><a href="https://example.org/">external</a>')
    (docs / "next page.html").write_text('<h1 id="there">There</h1>')
    (docs / "readme.md").write_text("# A heading\n\n[local](#a-heading)\n[index](index.html)\n")
    (docs / "image.png").write_bytes(b"fixture")
    (docs / "style.css").write_text('a { background: url("image.png"); }')
    assert check_links(tmp_path) == (4, 5, 1, [])


@pytest.mark.parametrize("target", ["missing.html", "index.html#missing", "../../outside.html"])
def test_links_reject_missing_files_fragments_and_escapes(tmp_path, target):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.html").write_text(f'<a href="{target}">broken</a>')
    assert len(check_links(tmp_path)[3]) == 1
