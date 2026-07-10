#!/usr/bin/env python3
"""
check_doc_index.py -- part of at_have_ryggen_fri.

Two related but distinct checks:

1. REPO-WIDE BROKEN LINKS: every git-tracked *.md file in the whole repo
   (not just docs/ -- ansible/README.md, ansible/playbooks/*/README.md,
   etc. all have their own relative markdown links, never checked before
   2026-07-10) is scanned for `[text](relative/path)` links, resolved
   relative to that file's own directory, and confirmed to point at a
   real file. Always a failure -- a dangling link is always a bug (a
   move/rename that didn't update the link), regardless of which file
   it's in. Uses `git ls-files`, not a directory walk, so it only checks
   tracked files and automatically covers new ones anywhere in the repo.

2. docs/INDEX.md COMPLETENESS: docs/INDEX.md is specifically the
   estate-wide documentation catalogue -- every real doc under docs/ is
   supposed to be listed there with a stable Doc ID. This is docs/-
   specific curation, not a general repo-wide concept, so it stays a
   separate check: a 2026-07-09 manual audit found 35 real doc files not
   listed at all. Reported as a warning, not a failure -- some files are
   deliberately excluded (meta files, archived docs under an old/
   subdirectory) and a human needs to triage, not autofail a fresh clone.

Exit code: 0 unless there's at least one broken link (category 1). Category
2 (unindexed files) never affects the exit code.
"""
import re
import subprocess
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


def git_tracked_markdown_files():
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "-z", "--", "*.md"],
        capture_output=True, check=True,
    )
    return [REPO_ROOT / p for p in result.stdout.decode("utf-8").split("\0") if p]


def extract_relative_links(md_path):
    text = md_path.read_text(encoding="utf-8", errors="replace")
    links = []
    for m in LINK_RE.finditer(text):
        target = urllib.parse.unquote(m.group(2))
        if target.startswith(("http://", "https://", "#", "mailto:")):
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
    md_files = git_tracked_markdown_files()

    # --- 1. repo-wide broken links ---------------------------------------
    broken = []
    total_links = 0
    for md_path in md_files:
        for link in extract_relative_links(md_path):
            total_links += 1
            if not (md_path.parent / link).exists():
                rel_source = md_path.relative_to(REPO_ROOT)
                broken.append((str(rel_source), link))

    print(f"Scanned {len(md_files)} git-tracked *.md file(s) repo-wide; "
          f"{total_links} relative link(s) checked.")

    # --- 2. docs/INDEX.md completeness (docs/-specific, warning only) ----
    index_links = set(extract_relative_links(INDEX_MD))
    real_docs = set(find_real_docs())
    unindexed = sorted(real_docs - index_links)

    print(f"docs/INDEX.md specifically: {len(index_links)} link(s); "
          f"{len(real_docs)} real .md/.pdf file(s) under docs/ (excluding meta/archived).")

    if unindexed:
        print(f"\n{len(unindexed)} file(s) under docs/ not linked from docs/INDEX.md:")
        for u in unindexed:
            print(f"  - {u}")

    if broken:
        print(f"\n{len(broken)} BROKEN link(s) (target doesn't exist):")
        for source, link in broken:
            print(f"  [{source}] -> \"{link}\"")
        return 1

    print("\nNo broken links anywhere in the repo." if not unindexed else
          "\nNo broken links anywhere in the repo (unindexed files above are a warning, not a failure).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
