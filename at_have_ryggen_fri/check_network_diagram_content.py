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

Four invariants, all from docs/network-diagram.md's Visual Standard section:
  1. FSMO roles / health / low-disk-space annotations never appear inside a
     New Network block (they're old-infra-only, per Robert's 2026-07-13
     instruction -- see docs/network-cutover.md and network-inventory.md's DC
     Summary table for where that data actually lives).
  2. Every node inside a New Network block uses the single uniform rect shape
     ("[...]") AND has a leading emoji symbol (see TYPE_SYMBOLS in
     generate_network_diagrams.py) -- catches silent drift from the
     documented standard, e.g. a hand-edit that reintroduces one of the old
     5-shape wrappers, or adds a device type with no symbol.
  3. Every topology-style device box (T_-prefixed node, excluding the
     "☁️ ..." cloud/fabric root nodes) is a multi-line <br/> label
     -- Robert, 2026-07-31: single-line boxes read "crowded"; the generator
     (_topology_label()/_topology_other_group_label() in
     generate_network_diagrams.py) always produces hostname/description/IP
     on three separate lines now, so a single-line one is drift, not a
     style choice.
  4. No topology device box shows a bare octet or octet-range ("· .70"
     or "· .70-.73") as its IP line -- ambiguous about which subnet,
     the exact bug Robert flagged 2026-07-31 ("omitted the subnet, which
     is a big no no"). Full IP (optionally with a compact trailing range,
     e.g. "192.168.76.70-73") or the literal "No IP Address" only.

Exit code: 0 if all four invariants hold everywhere, 1 otherwise.
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs" / "network-diagram"

# Matches both the original flat-box marker (GENERATED:NEW-NETWORK, orange, octet-only labels)
# and the topology-sketch marker (GENERATED:TOPOLOGY, black/white, full IPs, right-angle edges --
# rolled out to every site 2026-07-30). Both wrap real device content the same two invariants
# below apply to; TOPOLOGY_SITES in generate_network_diagrams.py deliberately keeps a site
# revertible to the flat-box style individually, so this check can't assume only one marker kind
# will ever be present.
GENERATED_BLOCK_RE = re.compile(
    r'%% GENERATED:(?:NEW-NETWORK|TOPOLOGY):(\w+):START\n(.*?)\n\s*%% GENERATED:(?:NEW-NETWORK|TOPOLOGY):\1:END',
    re.DOTALL,
)

BANNED_TERMS = re.compile(r'FSMO|DFSR|low disk|OOS \d|EOL\b|UNHEALTHY|out of sync', re.IGNORECASE)

# Every real device node: ID["<emoji> EXA...<hostname text>..."]. Non-ASCII/emoji range check
# rather than an explicit symbol list -- TYPE_SYMBOLS changes over time, this just needs "starts
# with something that isn't plain ASCII text."
NODE_LINE_RE = re.compile(r'^\s*(\w+)\["(.*)"\]\s*$')
LEADING_EMOJI_RE = re.compile(r'^[^\x00-\x7F]')
# subgraph/end/style/classDef/class -- the flat-box format's own structural lines. graph/%%{init --
# topology blocks' own header (graph TD, the stepAfter curve directive). Edge lines (T_A --> T_B,
# possibly chained A --> B --> C, or invisible T_A ~~~ T_B ranking hints) -- topology blocks' own
# connections, which the flat-box format never had at all (no edges, just a flat node list).
NON_NODE_LINE_RE = re.compile(
    r'^\s*(subgraph|end|style|classDef|class|graph)\b|^\s*%%|^\s*$|-->|~~~',
)
PLACEHOLDER_NODE_RE = re.compile(r'^\s*N_EMPTY\[')

# Invariants 3/4 (topology-style boxes only, T_-prefixed node IDs) -- the "☁️ ..." cloud/fabric
# root nodes (T_VRK, T_<SITE> for VRK/FRD) are structurally different (a network segment, not a
# device) and stay single-line by design, so they're excluded via CLOUD_ROOT_RE rather than
# expected to follow the three-line device-box convention.
CLOUD_ROOT_RE = re.compile(r'^☁️')
# Matches a <br/>-delimited segment that is JUST a bare octet or octet-range ("· .70", "· .70-.73")
# -- the exact "omitted the subnet" shape, not a false-positive on a full IP that merely ends in a
# multi-digit octet.
BARE_OCTET_LINE_RE = re.compile(r'(?:^|<br/>)\.\d+(?:-\.\d+)?(?=<br/>|$)')


def main():
    blocks = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for site, body in GENERATED_BLOCK_RE.findall(text):
            blocks.append((path.name, site, body))

    if not blocks:
        print(f"No generated diagram blocks found under {DOCS_DIR.relative_to(REPO_ROOT)}/ -- "
              f"check the marker regex against the current file format.")
        return 1

    banned_hits = []
    bad_shapes = []
    style_issues = []

    for fname, site, body in blocks:
        if BANNED_TERMS.search(body):
            hit = BANNED_TERMS.search(body).group(0)
            banned_hits.append(f"{fname}/{site}: found banned term {hit!r} inside its generated diagram block")

        for line in body.splitlines():
            if NON_NODE_LINE_RE.search(line) or PLACEHOLDER_NODE_RE.match(line):
                continue
            m = NODE_LINE_RE.match(line)
            if not m:
                bad_shapes.append(f"{fname}/{site}: line does not use the uniform rect shape -- {line.strip()!r}")
                continue
            if not LEADING_EMOJI_RE.match(m.group(2)):
                bad_shapes.append(f"{fname}/{site}: node has no leading emoji symbol -- {line.strip()!r}")

            node_id, label = m.group(1), m.group(2)
            if node_id.startswith("T_") and not CLOUD_ROOT_RE.match(label):
                if "<br/>" not in label:
                    style_issues.append(
                        f"{fname}/{site}: topology device box isn't the three-line <br/> style -- {line.strip()!r}")
                if BARE_OCTET_LINE_RE.search(label):
                    style_issues.append(
                        f"{fname}/{site}: topology device box has a bare octet instead of a full IP -- {line.strip()!r}")

    print(f"Checked {len(blocks)} generated diagram block(s) across {DOCS_DIR.relative_to(REPO_ROOT)}/ "
          f"for banned FSMO/health terms, shape/symbol-convention compliance, and topology box style.")

    if banned_hits or bad_shapes or style_issues:
        if banned_hits:
            print(f"\n{len(banned_hits)} banned-term violation(s):")
            for h in banned_hits:
                print(f"  - {h}")
        if bad_shapes:
            print(f"\n{len(bad_shapes)} shape/symbol-convention violation(s):")
            for b in bad_shapes:
                print(f"  - {b}")
        if style_issues:
            print(f"\n{len(style_issues)} topology box style violation(s):")
            for s in style_issues:
                print(f"  - {s}")
        return 1

    print("No banned FSMO/health terms found; every node uses the uniform shape with a leading "
          "emoji; every topology device box is three-line with a full IP or 'No IP Address'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
