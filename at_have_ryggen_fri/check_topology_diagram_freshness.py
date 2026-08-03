#!/usr/bin/env python3
"""
check_topology_diagram_freshness.py -- part of at_have_ryggen_fri.

benarbejde/generate_network_diagrams.py's render_topology_block() is the
single source of truth for the "Topology sketch" mermaid diagram in every
site's own docs/network-diagram/*.md section (TOPOLOGY_SITES), wrapped in
"%% GENERATED:TOPOLOGY:<SITE>:START/END" marker comments -- the sibling
generator to render_new_network_block()'s flat "New Network" box, which
check_network_diagram_freshness.py (check 14) already covers.

Found live 2026-08-04: check 14 only ever called insert_into_docs() (the
flat box). insert_topology_into_docs() has its own separate regeneration
path and nothing verified it stayed in sync -- devices.csv changed
repeatedly this session (a DCS->DCR rename among them) with nothing
re-running it. Confirmed real damage from the gap: 22 sites' *current*
topology sketches were showing the stale, pre-rename `EXADCR<SITE>001`
hostname mislabeled as "DCS 1" -- the legacy/pending-decommission DC's
hostname displayed as if it were the real current domain controller --
until caught by hand while adding CLD's real switch vendor and manually
regenerating to check the result. This check exists so that class of
silent drift can't happen again unnoticed.

Same regeneration-into-scratch-copy-and-diff technique as check 14, just
calling insert_topology_into_docs() instead of insert_into_docs().

Exit code: 0 if every region file matches a fresh regeneration, 1 if any
has drifted.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BENARBEJDE = REPO_ROOT / "benarbejde"
GENERATOR = BENARBEJDE / "generate_network_diagrams.py"
DOCS_DIR = REPO_ROOT / "docs" / "network-diagram"


def main():
    with tempfile.TemporaryDirectory(prefix="ryggen_fri_topology_freshness_") as tmp:
        scratch_dir = Path(tmp) / "network-diagram"
        shutil.copytree(DOCS_DIR, scratch_dir)

        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, sys.argv[1]); import generate_network_diagrams as gnd; "
             "from pathlib import Path; "
             "inserted, replaced, missing = gnd.insert_topology_into_docs(docs_dir=Path(sys.argv[2])); "
             "print(f'inserted={len(inserted)} replaced={len(replaced)} missing={missing}')",
             str(BENARBEJDE), str(scratch_dir)],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        if result.returncode != 0:
            print("generate_network_diagrams.py failed to regenerate:")
            print(result.stderr)
            return 1

        drifted = []
        for committed_path in sorted(DOCS_DIR.glob("*.md")):
            fresh_path = scratch_dir / committed_path.name
            if not fresh_path.exists():
                drifted.append(f"{committed_path.name}: regeneration did not produce this file at all")
                continue
            committed_text = committed_path.read_text(encoding="utf-8")
            fresh_text = fresh_path.read_text(encoding="utf-8")
            if committed_text != fresh_text:
                committed_lines = committed_text.splitlines()
                fresh_lines = fresh_text.splitlines()
                first_diff = next(
                    (i for i, (a, b) in enumerate(zip(committed_lines, fresh_lines)) if a != b),
                    min(len(committed_lines), len(fresh_lines)),
                )
                drifted.append(f"{committed_path.name}: differs from a fresh regeneration (first difference around line {first_diff + 1})")

    print(f"Regenerated every site's Topology sketch block from benarbejde/sites.csv+devices.csv"
          f"+address_policy.csv into a scratch copy of {DOCS_DIR.relative_to(REPO_ROOT)}/, "
          f"diffed each region file against its committed version.")
    print(result.stdout.strip())

    if drifted:
        print(f"\n{len(drifted)} region file(s) have drifted from a fresh regeneration:")
        for d in drifted:
            print(f"  - {d}")
        print("\nRun: python3 -c \"import sys; sys.path.insert(0, 'benarbejde'); "
              "import generate_network_diagrams as gnd; gnd.insert_topology_into_docs()\" to fix.")
        return 1

    print(f"All {len(list(DOCS_DIR.glob('*.md')))} region files' Topology sketch blocks are fresh.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
