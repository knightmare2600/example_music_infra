#!/usr/bin/env python3
"""
check_doc_index.py -- part of at_have_ryggen_fri.

docs/INDEX.md is the estate-wide documentation catalogue -- every real doc
under docs/ is supposed to be listed there, with a stable Doc ID, and every
link in it is supposed to point at a real file. Neither direction was ever
checked mechanically before; a 2026-07-09 manual audit found a broken link
(pointing at a directory the file had moved out of) and 35 real doc files
not listed at all. This makes both checks repeatable.

Two categories, reported separately:
  - BROKEN LINKS: docs/INDEX.md links to a file that doesn't exist. This is
    always a bug (a move/rename without updating the index) -- fails the
    check.
  - UNINDEXED FILES: a real file under docs/ that no link in docs/INDEX.md
    points at. Not necessarily a bug -- some files are deliberately excluded
    (meta files like README.md/INDEX.md itself, archived docs under an
    old/ subdirectory, templates). Reported as a warning, not a failure,
    so a human can triage and either index them or explicitly note them as
    excluded -- see EXCLUDED below, which grows as that triage happens.

Exit code: 0 unless there's at least one broken link.
"""
import re
import sys
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
INDEX_MD = DOCS_DIR / "INDEX.md"

# Files deliberately not expected to appear as a docs/INDEX.md link target.
# Add to this list (with a reason) as unindexed files are triaged, rather
# than silently ignoring them.
EXCLUDED = {
    "README.md",         # meta, not a catalogued doc
    "INDEX.md",           # this file, self-referential
}
# Whole subdirectories excluded by prefix (path relative to docs/), e.g.
# archived/superseded docs kept for history but not part of the live catalogue.
EXCLUDED_PREFIXES = (
    "inventory/old/",
)

LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def find_links():
    text = INDEX_MD.read_text(encoding="utf-8")
    links = []
    for m in LINK_RE.finditer(text):
        target = urllib.parse.unquote(m.group(2))
        if target.startswith(("http://", "https://", "#")):
            continue
        if not target.endswith((".md", ".pdf", ".sh", ".py")):
            continue
        links.append(target)
    return links


def find_real_docs():
    exts = (".md", ".pdf")
    docs = []
    for p in DOCS_DIR.rglob("*"):
        if not p.is_file() or p.suffix not in exts:
            continue
        rel = p.relative_to(DOCS_DIR).as_posix()
        if rel in EXCLUDED or any(rel.startswith(pfx) for pfx in EXCLUDED_PREFIXES):
            continue
        docs.append(rel)
    return docs


def main():
    links = find_links()
    real_docs = set(find_real_docs())

    broken = []
    for link in links:
        if not (DOCS_DIR / link).exists():
            broken.append(link)

    linked_targets = {link for link in links}
    unindexed = sorted(real_docs - linked_targets)

    print(f"docs/INDEX.md has {len(links)} file link(s); "
          f"{len(real_docs)} real .md/.pdf file(s) under docs/ (excluding meta/archived).")

    if unindexed:
        print(f"\n{len(unindexed)} file(s) under docs/ not linked from docs/INDEX.md:")
        for u in unindexed:
            print(f"  - {u}")

    if broken:
        print(f"\n{len(broken)} BROKEN link(s) in docs/INDEX.md (target doesn't exist):")
        for b in sorted(set(broken)):
            print(f"  - {b}")
        return 1

    print("\nNo broken links in docs/INDEX.md." if not unindexed else
          "\nNo broken links in docs/INDEX.md (unindexed files above are a warning, not a failure).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
