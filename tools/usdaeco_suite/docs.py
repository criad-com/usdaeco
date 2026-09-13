"""Resolve local documentation links and fragments without network access."""
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.targets = []
        self.anchors = set()

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if value is None:
                continue
            if key in {"href", "src", "xlink:href"}:
                self.targets.append(value)
            if key == "id" or (tag == "a" and key == "name"):
                self.anchors.add(value)


def parse(path):
    text = path.read_text(encoding="utf-8")
    parser = Links()
    parser.feed(text)
    if path.suffix == ".md":
        # The documentation contract uses inline Markdown links and headings.
        parser.targets += re.findall(r"\[[^\]\n]*\]\(<?([^\s)>]+)>?(?:\s+\"[^\"]*\")?\)", text)
        counts = {}
        for heading in re.findall(r"(?m)^#{1,6}\s+(.+?)\s*#*\s*$", text):
            slug = re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
            count = counts.get(slug, 0)
            counts[slug] = count + 1
            parser.anchors.add(f"{slug}-{count}" if count else slug)
    if path.suffix == ".css":
        parser.targets += re.findall(r"url\(['\"]?([^)'\"]+)['\"]?\)", text)
    return parser


def check_links(root):
    root = Path(root).resolve()
    pages = sorted(p for p in (root / "docs").rglob("*") if p.suffix in {".html", ".md", ".css"})
    parsed = {p: parse(p) for p in pages}
    failures = []
    local = external = 0
    for page in pages:
        for target in parsed[page].targets:
            url = urlsplit(target)
            if url.scheme in {"http", "https", "mailto", "data"} or url.netloc:
                external += 1
                continue
            local += 1
            destination = (page.parent / unquote(url.path)).resolve() if url.path else page
            if url.scheme or not destination.is_relative_to(root) or not destination.exists():
                failures.append(f"{page.relative_to(root)}: unresolved local link")
                continue
            if url.fragment:
                if destination.suffix not in {".html", ".md"} or not destination.is_file():
                    failures.append(f"{page.relative_to(root)}: fragment target is not a page")
                    continue
                if destination not in parsed:
                    parsed[destination] = parse(destination)
                if unquote(url.fragment) not in parsed[destination].anchors:
                    failures.append(f"{page.relative_to(root)}: unresolved fragment")
    return len(pages), local, external, failures
