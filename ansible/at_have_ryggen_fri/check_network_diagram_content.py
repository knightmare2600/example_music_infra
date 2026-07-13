#!/usr/bin/env python3
"""
check_network_diagram_content.py -- part of at_have_ryggen_fri.

check_network_diagram_freshness.py (check 14) verifies committed New Network
blocks match a fresh regeneration -- but that's only as good as
generate_network_diagrams.py's own in-process guards (BANNED_TERMS, shape_wrap's
ValueError on an unmapped type), which never actually run against the COMMITTED
file, only against whatever the generator produces in memory. This is the
independent check: it re-derives both invariants by scanning the committed
docs/network-diagram.md text directly, the same "don't just re-run the same
code and call it verified" principle check_facts.py and check_site_data.py
already follow.

Two invariants, both from docs/network-diagram.md's Visual Standard section:
  1. FSMO roles / health / low-disk-space annotations never appear inside a
     New Network block (they're old-infra-only, per Robert's 2026-07-13
     instruction -- see docs/network-cutover.md and network-inventory.md's DC
     Summary table for where that data actually lives).
  2. Every node inside a New Network block uses one of the five approved shape
     wrappers (hexagon/cylinder/circle/stadium/asymmetric-flag) -- catches
     silent drift from the documented standard, e.g. a hand-edit that adds a
     plain rectangle node instead of picking a real shape.

Exit code: 0 if both invariants hold everywhere, 1 otherwise.
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_FILE = REPO_ROOT / "docs" / "network-diagram.md"

NEW_NETWORK_BLOCK_RE = re.compile(
    r'%% GENERATED:NEW-NETWORK:(\w+):START\n(.*?)\n\s*%% GENERATED:NEW-NETWORK:\1:END',
    re.DOTALL,
)

BANNED_TERMS = re.compile(r'FSMO|DFSR|low disk|OOS \d|EOL\b|UNHEALTHY|out of sync', re.IGNORECASE)

# Same five shapes as docs/network-diagram.md's Visual Standard section and
# generate_network_diagrams.py's shape_wrap() -- a node line inside a New
# Network block must open with one of these. subgraph/end/style/class lines,
# and the "no confirmed devices" placeholder, are not device nodes and are
# skipped explicitly rather than matched against the shape patterns.
SHAPE_PATTERNS = [
    re.compile(r'^\s*\w+\{\{"'),      # hexagon
    re.compile(r'^\s*\w+\[\("'),      # cylinder
    re.compile(r'^\s*\w+\(\("'),      # circle
    re.compile(r'^\s*\w+\(\["'),      # stadium
    re.compile(r'^\s*\w+>"'),         # asymmetric flag
]
NON_NODE_LINE_RE = re.compile(r'^\s*(subgraph|end|style|classDef|class)\b|^\s*$')
PLACEHOLDER_NODE_RE = re.compile(r'^\s*N_EMPTY\[')


def main():
    text = DOCS_FILE.read_text(encoding="utf-8")
    blocks = NEW_NETWORK_BLOCK_RE.findall(text)

    if not blocks:
        print("No New Network blocks found -- check the marker regex against the current file format.")
        return 1

    banned_hits = []
    bad_shapes = []

    for site, body in blocks:
        if BANNED_TERMS.search(body):
            hit = BANNED_TERMS.search(body).group(0)
            banned_hits.append(f"{site}: found banned term {hit!r} inside its New Network block")

        for line in body.splitlines():
            if NON_NODE_LINE_RE.match(line) or PLACEHOLDER_NODE_RE.match(line):
                continue
            if not any(p.match(line) for p in SHAPE_PATTERNS):
                bad_shapes.append(f"{site}: line does not use an approved shape -- {line.strip()!r}")

    print(f"Checked {len(blocks)} New Network block(s) in {DOCS_FILE.relative_to(REPO_ROOT)} "
          f"for banned FSMO/health terms and shape-convention compliance.")

    if banned_hits or bad_shapes:
        if banned_hits:
            print(f"\n{len(banned_hits)} banned-term violation(s):")
            for h in banned_hits:
                print(f"  - {h}")
        if bad_shapes:
            print(f"\n{len(bad_shapes)} shape-convention violation(s):")
            for b in bad_shapes:
                print(f"  - {b}")
        return 1

    print("No banned FSMO/health terms found; every node uses an approved shape.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
