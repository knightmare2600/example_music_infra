#!/usr/bin/env python3
"""
check_network_diagram_content.py -- part of at_have_ryggen_fri.

check_network_diagram_freshness.py (check 14) verifies committed New Network
blocks match a fresh regeneration -- but that's only as good as
generate_network_diagrams.py's own in-process guards (BANNED_TERMS, node_box's
caller raising on an unmapped type), which never actually run against the
COMMITTED files, only against whatever the generator produces in memory. This
is the independent check: it re-derives both invariants by scanning every
committed docs/network-diagram/*.md file directly, the same "don't just
re-run the same code and call it verified" principle check_facts.py and
check_site_data.py already follow.

Two invariants, both from docs/network-diagram.md's Visual Standard section:
  1. FSMO roles / health / low-disk-space annotations never appear inside a
     New Network block (they're old-infra-only, per Robert's 2026-07-13
     instruction -- see docs/network-cutover.md and network-inventory.md's DC
     Summary table for where that data actually lives).
  2. Every node inside a New Network block uses the single uniform rect shape
     ("[...]") AND has a leading emoji symbol (see TYPE_SYMBOLS in
     generate_network_diagrams.py) -- catches silent drift from the
     documented standard, e.g. a hand-edit that reintroduces one of the old
     5-shape wrappers, or adds a device type with no symbol.

Exit code: 0 if both invariants hold everywhere, 1 otherwise.
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs" / "network-diagram"

NEW_NETWORK_BLOCK_RE = re.compile(
    r'%% GENERATED:NEW-NETWORK:(\w+):START\n(.*?)\n\s*%% GENERATED:NEW-NETWORK:\1:END',
    re.DOTALL,
)

BANNED_TERMS = re.compile(r'FSMO|DFSR|low disk|OOS \d|EOL\b|UNHEALTHY|out of sync', re.IGNORECASE)

# Every real device node: ID["<emoji> EXA...<hostname text>..."]. Non-ASCII/emoji range check
# rather than an explicit symbol list -- TYPE_SYMBOLS changes over time, this just needs "starts
# with something that isn't plain ASCII text."
NODE_LINE_RE = re.compile(r'^\s*(\w+)\["(.*)"\]\s*$')
LEADING_EMOJI_RE = re.compile(r'^[^\x00-\x7F]')
NON_NODE_LINE_RE = re.compile(r'^\s*(subgraph|end|style|classDef|class)\b|^\s*$')
PLACEHOLDER_NODE_RE = re.compile(r'^\s*N_EMPTY\[')


def main():
    blocks = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for site, body in NEW_NETWORK_BLOCK_RE.findall(text):
            blocks.append((path.name, site, body))

    if not blocks:
        print(f"No New Network blocks found under {DOCS_DIR.relative_to(REPO_ROOT)}/ -- "
              f"check the marker regex against the current file format.")
        return 1

    banned_hits = []
    bad_shapes = []

    for fname, site, body in blocks:
        if BANNED_TERMS.search(body):
            hit = BANNED_TERMS.search(body).group(0)
            banned_hits.append(f"{fname}/{site}: found banned term {hit!r} inside its New Network block")

        for line in body.splitlines():
            if NON_NODE_LINE_RE.match(line) or PLACEHOLDER_NODE_RE.match(line):
                continue
            m = NODE_LINE_RE.match(line)
            if not m:
                bad_shapes.append(f"{fname}/{site}: line does not use the uniform rect shape -- {line.strip()!r}")
                continue
            if not LEADING_EMOJI_RE.match(m.group(2)):
                bad_shapes.append(f"{fname}/{site}: node has no leading emoji symbol -- {line.strip()!r}")

    print(f"Checked {len(blocks)} New Network block(s) across {DOCS_DIR.relative_to(REPO_ROOT)}/ "
          f"for banned FSMO/health terms and shape/symbol-convention compliance.")

    if banned_hits or bad_shapes:
        if banned_hits:
            print(f"\n{len(banned_hits)} banned-term violation(s):")
            for h in banned_hits:
                print(f"  - {h}")
        if bad_shapes:
            print(f"\n{len(bad_shapes)} shape/symbol-convention violation(s):")
            for b in bad_shapes:
                print(f"  - {b}")
        return 1

    print("No banned FSMO/health terms found; every node uses the uniform shape with a leading emoji.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
