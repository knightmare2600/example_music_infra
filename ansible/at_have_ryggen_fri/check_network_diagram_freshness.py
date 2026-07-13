#!/usr/bin/env python3
"""
check_network_diagram_freshness.py -- part of at_have_ryggen_fri.

benarbejde/generate_network_diagrams.py is the single source of truth for the
"New Network (current)" mermaid subgraph in every site section of
docs/network-diagram.md, wrapped in "%% GENERATED:NEW-NETWORK:<SITE>:START/END"
marker comments. This regenerates every site's block into a scratch copy of the
doc and diffs it against the committed version -- any difference means
sites.csv, devices.csv, or address_policy.json changed (or the New Network box
was hand-edited) without regenerating, the same drift class
check_generated_freshness.py already catches for the Ansible inventory files.

Hand-editing anything BETWEEN a START/END marker pair will show up here as
drift, including someone slipping FSMO/health text into a generated block --
this check doesn't need to know why the drift happened, only that committed
content no longer matches what the generator actually produces.

Exit code: 0 if the doc matches a fresh regeneration, 1 if it has drifted.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BENARBEJDE = REPO_ROOT / "benarbejde"
GENERATOR = BENARBEJDE / "generate_network_diagrams.py"
DOCS_FILE = REPO_ROOT / "docs" / "network-diagram.md"


def main():
    with tempfile.TemporaryDirectory(prefix="ryggen_fri_diagram_freshness_") as tmp:
        scratch_doc = Path(tmp) / "network-diagram.md"
        shutil.copyfile(DOCS_FILE, scratch_doc)

        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, sys.argv[1]); import generate_network_diagrams as gnd; "
             "from pathlib import Path; "
             "inserted, replaced, missing = gnd.insert_into_docs(docs_path=Path(sys.argv[2])); "
             "print(f'inserted={len(inserted)} replaced={len(replaced)} missing={missing}')",
             str(BENARBEJDE), str(scratch_doc)],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        if result.returncode != 0:
            print("generate_network_diagrams.py failed to regenerate:")
            print(result.stderr)
            return 1

        committed_text = DOCS_FILE.read_text(encoding="utf-8")
        fresh_text = scratch_doc.read_text(encoding="utf-8")

    print(f"Regenerated every site's New Network block from benarbejde/sites.csv+devices.csv"
          f"+address_policy.json into a scratch copy of {DOCS_FILE.relative_to(REPO_ROOT)}, "
          f"diffed against the committed version.")
    print(result.stdout.strip())

    if committed_text != fresh_text:
        committed_lines = committed_text.splitlines()
        fresh_lines = fresh_text.splitlines()
        first_diff = next(
            (i for i, (a, b) in enumerate(zip(committed_lines, fresh_lines)) if a != b),
            min(len(committed_lines), len(fresh_lines)),
        )
        print(f"\n{DOCS_FILE.relative_to(REPO_ROOT)} has drifted from a fresh regeneration "
              f"(first difference around line {first_diff + 1}).")
        print("Run: python3 benarbejde/generate_network_diagrams.py --write to fix.")
        return 1

    print("docs/network-diagram.md's New Network boxes are fresh.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
