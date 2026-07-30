#!/usr/bin/env python3
"""
check_network_diagram_freshness.py -- part of at_have_ryggen_fri.

benarbejde/generate_network_diagrams.py is the single source of truth for the
"New Network (current)" mermaid subgraph in every site section under
docs/network-diagram/ (one file per region -- split 2026-07-13, see
generate_network_diagrams.py's REGION_FILES), wrapped in
"%% GENERATED:NEW-NETWORK:<SITE>:START/END" marker comments. This regenerates
every site's block into a scratch copy of the whole directory and diffs each
file against its committed version -- any difference means sites.csv,
devices.csv, or address_policy.csv changed (or a New Network box was
hand-edited) without regenerating, the same drift class
check_generated_freshness.py already catches for the Ansible inventory files.

Hand-editing anything BETWEEN a START/END marker pair will show up here as
drift, including someone slipping FSMO/health text into a generated block --
this check doesn't need to know why the drift happened, only that committed
content no longer matches what the generator actually produces.

Exit code: 0 if every region file matches a fresh regeneration, 1 if any has
drifted.
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
    with tempfile.TemporaryDirectory(prefix="ryggen_fri_diagram_freshness_") as tmp:
        scratch_dir = Path(tmp) / "network-diagram"
        shutil.copytree(DOCS_DIR, scratch_dir)

        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, sys.argv[1]); import generate_network_diagrams as gnd; "
             "from pathlib import Path; "
             "inserted, replaced, missing = gnd.insert_into_docs(docs_dir=Path(sys.argv[2])); "
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

    print(f"Regenerated every site's New Network block from benarbejde/sites.csv+devices.csv"
          f"+address_policy.csv into a scratch copy of {DOCS_DIR.relative_to(REPO_ROOT)}/, "
          f"diffed each region file against its committed version.")
    print(result.stdout.strip())

    if drifted:
        print(f"\n{len(drifted)} region file(s) have drifted from a fresh regeneration:")
        for d in drifted:
            print(f"  - {d}")
        print("\nRun: python3 benarbejde/generate_network_diagrams.py --write to fix.")
        return 1

    print(f"All {len(list(DOCS_DIR.glob('*.md')))} region files' New Network boxes are fresh.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
