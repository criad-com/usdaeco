"""Sweep owned files without descending into submodules."""
from pathlib import Path
import re
import subprocess

from usdaeco_suite.checkout import modules


def expected_url(name):
    if name in {"usdSolid", "usdSolidOcct"}:
        return "../../" + "Cr" + "iad" + f"/{name}.git"
    return f"../{name}.git"


def repository_files(root):
    root = Path(root)
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--cached", "--others",
         "--exclude-standard"], capture_output=True, check=True,
    )
    return [root / name.decode() for name in sorted(set(result.stdout.split(b"\0")))
            if name and ((root / name.decode()).is_file() or (root / name.decode()).is_symlink())]


def text_findings(text, *, suffix="", extra_patterns=()):
    """Return line numbers only; sensitive matches never enter diagnostics."""
    from usdaeco_check.structure import TERM_PATTERNS, public_org_text

    patterns = [*TERM_PATTERNS, r"\b[u]v\b", r"\bfor[u]m-1\b", r"\bfam[i]ly\b",
                r"\bF[A]M[-][A-Z0-9]+\b",
                r"\bhttps?://[\w-]+(?=[:/\s]|$)",
                r"file[:][/][/]", r"/(?:opt|private|tmp|var|mnt|media)/[^\s\"']+",
                r"(?<![\w])~[/]", r"\b[A-Z]:[/\\]"]
    regexes = [re.compile(p, re.I) for p in patterns]
    extras = [re.compile(p, re.I) for p in extra_patterns]
    result = []
    for number, line in enumerate(text.splitlines(), 1):
        public_line = public_org_text(line)
        if suffix == ".css":
            public_line = re.sub(r"\bfont-fam[i]ly(?=\s*:)", "font-face", public_line)
        if suffix == ".html":
            # Preserve the imported font-service query parameter, never prose.
            public_line = re.sub(r"(?<=[?&])fam[i]ly=", "font=", public_line)
        if any(p.search(public_line) for p in regexes) or any(p.search(line) for p in extras):
            result.append(number)
    return result


def sweep(root, *, extra_patterns=()):
    root = Path(root)
    findings = []
    declared = modules(root)
    for path, url in declared.items():
        if url != expected_url(Path(path).name):
            findings.append(".gitmodules: invalid relative URL")
    text_count = 0
    for path in repository_files(root):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            findings.append(f"{relative}: symlink is outside the owned-file contract")
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        text_count += 1
        if path.name == ".gitmodules":
            # Exempt only the two exact, required owner-relative URL values.
            for name in ("usdSolid", "usdSolidOcct"):
                content = re.sub(r"(?m)^(\s*url\s*=\s*)" + re.escape(expected_url(name)) + r"\s*$",
                                 rf"\g<1>../../kit-owner/{name}.git", content)
        findings += [f"{relative}:{line}" for line in
                     text_findings(content, suffix=path.suffix, extra_patterns=extra_patterns)]
    return text_count, findings
