#!/usr/bin/env python3
"""
check_mermaid.py -- part of at_have_ryggen_fri.

Every ```mermaid fenced code block in every git-tracked *.md file in the
repo is POSTed to kroki.io (https://kroki.io/mermaid/svg) and confirmed
to actually render, not just parse-checked locally (no local mermaid
parser is vendored here, and mermaid's grammar has genuine gotchas --
literal \\n instead of <br/> for line breaks, backslash-escaped quotes,
unquoted parens inside pipe-delimited edge labels -- that only surface as
a real parse failure, not something a naive "do the brackets balance"
check would catch). Found the hard way, 2026-07-12: three separate real
syntax bugs across 49 diagrams in this repo, none of which any other
check here would have caught.

THE ONE EXCEPTION TO THIS HARNESS'S "no network beyond localhost" RULE.
Every other check promises to run on any clone, any time, no network
needed -- this one genuinely needs to reach kroki.io. Handled accordingly:
a network/connection failure is reported and, by default, treated as
informational (matching check 3's drop-in-binary precedent) -- --strict
promotes it to a real failure. A genuine syntax error from kroki (HTTP 400
with a parse error) is ALWAYS a hard failure, regardless of --strict --
that's a real, unambiguous bug in the diagram, same tier as check 3's
broken file references.

Results are cached by content hash in reports/.mermaid_cache.json
(gitignored) -- kroki.io is a free public service, and re-submitting all
49+ diagrams on every single harness run when almost none of them changed
is both slow and inconsiderate. Only new/changed diagram content actually
hits the network; unchanged content reuses its last known-good result.

Exit code: 0 if every diagram renders (or the only issues are network
failures and --strict wasn't passed), 1 if any diagram has a genuine
syntax error, or (with --strict) if kroki.io was unreachable for any
diagram never previously cached.
"""
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE_FILE = Path(__file__).resolve().parent / "reports" / ".mermaid_cache.json"
KROKI_URL = "https://kroki.io/mermaid/svg"

MERMAID_BLOCK_RE = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)


def git_tracked_markdown_files():
    # -z (NUL-terminated, raw filenames) -- without it, git quotes/octal-escapes
    # any filename containing non-ASCII or special characters (several docs in
    # this repo have em-dashes in their names), which then fails to open.
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "-z", "--", "*.md"],
        capture_output=True, text=True, timeout=30,
    ).stdout
    return [line for line in out.split("\0") if line]


def load_cache():
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_cache(cache):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, indent=2, sort_keys=True))


def render_via_kroki(diagram_text):
    """Returns (ok, detail). ok=True means it rendered. ok=False + detail
    distinguishes a genuine syntax error from a network failure via the
    detail string's own 'NETWORK:' prefix."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-w", "\n%{http_code}", "--max-time", "20",
             "-H", "Content-Type: text/plain",
             "--data-binary", "@-",
             KROKI_URL],
            input=diagram_text, capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"NETWORK: curl failed to run ({exc})"

    if result.returncode != 0:
        return False, f"NETWORK: curl exited {result.returncode} -- kroki.io likely unreachable"

    body, _, code = result.stdout.rpartition("\n")
    if code == "200":
        return True, ""
    if code in ("", "000"):
        return False, "NETWORK: no HTTP response -- kroki.io likely unreachable"
    # A real HTTP error from kroki itself -- genuine syntax problem, not a network issue.
    return False, body.strip() or f"HTTP {code} with no error body"


def main():
    strict = "--strict" in sys.argv

    cache = load_cache()
    diagrams = []  # (rel_path, index_in_file, content, content_hash)
    for rel_path in git_tracked_markdown_files():
        path = REPO_ROOT / rel_path
        text = path.read_text(encoding="utf-8", errors="replace")
        for i, block in enumerate(MERMAID_BLOCK_RE.findall(text)):
            h = hashlib.sha256(block.encode("utf-8")).hexdigest()
            diagrams.append((rel_path, i, block, h))

    print(f"Found {len(diagrams)} mermaid diagram(s) across {len(git_tracked_markdown_files())} tracked markdown file(s).")

    syntax_errors = []
    network_issues = []
    checked_live = 0

    for rel_path, i, block, h in diagrams:
        if h in cache and cache[h] == "ok":
            continue
        ok, detail = render_via_kroki(block)
        checked_live += 1
        time.sleep(0.3)  # be a considerate citizen of a free public service
        if ok:
            cache[h] = "ok"
        elif detail.startswith("NETWORK:"):
            network_issues.append((rel_path, i, detail))
            # Don't cache network failures -- worth retrying next run.
        else:
            syntax_errors.append((rel_path, i, detail))
            cache[h] = f"error: {detail.splitlines()[0][:200]}"

    save_cache(cache)

    print(f"Checked {checked_live} diagram(s) live against kroki.io; {len(diagrams) - checked_live} unchanged since last known-good check (cached).")

    if syntax_errors:
        print(f"\n{len(syntax_errors)} diagram(s) with a genuine syntax error (kroki.io could not render them):")
        for rel_path, i, detail in syntax_errors:
            print(f"  {rel_path} (diagram #{i}):")
            for line in detail.splitlines()[:6]:
                print(f"      {line}")

    if network_issues:
        print(f"\n{len(network_issues)} diagram(s) could not be checked -- kroki.io unreachable:")
        for rel_path, i, detail in network_issues:
            print(f"  {rel_path} (diagram #{i}): {detail}")

    if syntax_errors:
        return 1
    if network_issues and strict:
        return 1
    print("\nAll mermaid diagrams render successfully (or unreachable diagrams are informational only -- see above).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
