#!/usr/bin/env python3
"""
check_old_network_freshness.py -- part of at_have_ryggen_fri.

benarbejde/generate_network_diagrams.py's render_old_network_block() is the
single source of truth for the "Old Network" mermaid diagram in every
old-network site's own docs/network-diagram/*.md section, wrapped in
"%% GENERATED:OLDNETWORK:<SITE>:START/END" marker comments -- the sibling
generator to render_topology_block()'s "Topology sketch", which
check_topology_diagram_freshness.py (check 31) already covers.

Found live 2026-08-04: insert_old_network_into_docs() existed, fully built,
mirroring insert_topology_into_docs()'s own idempotent shape, but was never
called from generate_network_diagrams.py's main() -- the GENERATED marker
implied it ran on every --write same as the topology sketch; it didn't.
Real drift had already accumulated by the time this was noticed: FAL's Old
Network box was missing a workstation devices.csv had gained, and still
showed a router note that had since been edited. Wired into main() and this
check added the same day, same reason check 31 exists -- so that class of
silent drift can't happen again unnoticed.

Same regeneration-into-scratch-copy-and-diff technique as check 31, calling
insert_old_network_into_docs() instead. Unlike check 31, a non-empty
"missing" list here is expected and not a failure -- plenty of sites
genuinely have no old-network data or no recorded RTR (render_old_network_
block() never fabricates a router; see its own docstring), so there's
nothing to regenerate for them and nothing to compare.

Exit code: 0 if every region file's Old Network block(s) match a fresh
regeneration, 1 if any has drifted.
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
    with tempfile.TemporaryDirectory(prefix="ryggen_fri_oldnet_freshness_") as tmp:
        scratch_dir = Path(tmp) / "network-diagram"
        shutil.copytree(DOCS_DIR, scratch_dir)

        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, sys.argv[1]); import generate_network_diagrams as gnd; "
             "from pathlib import Path; "
             "inserted, replaced, missing = gnd.insert_old_network_into_docs(docs_dir=Path(sys.argv[2])); "
             "print(f'inserted={len(inserted)} replaced={len(replaced)} missing={len(missing)}')",
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

    print(f"Regenerated every old-network site's Old Network block from benarbejde/devices.csv"
          f"+legacy-devices.csv into a scratch copy of {DOCS_DIR.relative_to(REPO_ROOT)}/, "
          f"diffed each region file against its committed version.")
    print(result.stdout.strip())

    if drifted:
        print(f"\n{len(drifted)} region file(s) have drifted from a fresh regeneration:")
        for d in drifted:
            print(f"  - {d}")
        print("\nRun: python3 -c \"import sys; sys.path.insert(0, 'benarbejde'); "
              "import generate_network_diagrams as gnd; gnd.insert_old_network_into_docs()\" to fix.")
        return 1

    print(f"All {len(list(DOCS_DIR.glob('*.md')))} region files' Old Network blocks are fresh.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
