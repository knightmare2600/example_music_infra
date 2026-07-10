#!/usr/bin/env python3
"""
check_generated_freshness.py -- part of at_have_ryggen_fri.

benarbejde/generate_inventory.py is the single source of truth for three
generated outputs:
  - ansible/configs/inventory/<site>.ini  (one per site, 53 total)
  - ansible/configs/inventory/group_vars/all/site_services.yml
  - benarbejde/begyndelse.json

All three say, in their own header comment, "do not hand-edit, regenerate
instead" -- but nothing previously checked that anyone actually did. This
script regenerates all three into a scratch directory and diffs them
against the committed versions. Any difference means benarbejde/sites.csv,
devices.csv, address_policy.json, or ad_forest.json changed without a
regeneration -- a real bug (the committed files are now describing a
world that no longer matches their own source of truth), not a style
nitpick.

main.ini and rudder.ini are NOT generator output (they come from
ansibleme.sh's discovery scan / hand-curation) and are deliberately
excluded from this check.

Exit code: 0 if every generated file matches a fresh regeneration, 1 if
any has drifted.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BENARBEJDE = REPO_ROOT / "benarbejde"
GENERATOR = BENARBEJDE / "generate_inventory.py"
INVENTORY_DIR = REPO_ROOT / "ansible" / "configs" / "inventory"
SITE_SERVICES = INVENTORY_DIR / "group_vars" / "all" / "site_services.yml"
BEGYNDELSE = BENARBEJDE / "begyndelse.json"

NOT_GENERATOR_OWNED = {"main.ini", "rudder.ini"}


def run(args):
    result = subprocess.run(
        [sys.executable, str(GENERATOR)] + args,
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        print(f"generate_inventory.py {' '.join(args)} failed:")
        print(result.stderr)
        sys.exit(1)


def diff_dirs(scratch_ini_dir, drifted):
    committed = {p.name for p in INVENTORY_DIR.glob("*.ini")} - NOT_GENERATOR_OWNED
    fresh = {p.name for p in scratch_ini_dir.glob("*.ini")}

    for missing in sorted(committed - fresh):
        drifted.append(f"configs/inventory/{missing} exists but generate_inventory.py "
                        f"no longer produces it -- site removed from sites.csv?")
    for extra in sorted(fresh - committed):
        drifted.append(f"generate_inventory.py now produces configs/inventory/{extra}, "
                        f"but it isn't committed -- new site added to sites.csv, not regenerated?")

    for name in sorted(committed & fresh):
        committed_text = (INVENTORY_DIR / name).read_text()
        fresh_text = (scratch_ini_dir / name).read_text()
        if committed_text != fresh_text:
            drifted.append(f"configs/inventory/{name} differs from a fresh regeneration")


def diff_file(committed_path, fresh_path, drifted, label):
    if not fresh_path.exists():
        drifted.append(f"{label}: regeneration did not produce a file at all")
        return
    if committed_path.read_text() != fresh_path.read_text():
        drifted.append(f"{label} differs from a fresh regeneration")


def main():
    with tempfile.TemporaryDirectory(prefix="ryggen_fri_freshness_") as tmp:
        tmp = Path(tmp)
        scratch_ini_dir = tmp / "inventory"
        scratch_site_services = tmp / "site_services.yml"
        scratch_begyndelse = tmp / "begyndelse.json"

        run(["benarbejde/sites.csv", "-o", str(scratch_ini_dir),
             "--devices", "benarbejde/devices.csv"])
        run(["benarbejde/sites.csv", "--emit-group-vars",
             "--group-vars-out", str(scratch_site_services),
             "--devices", "benarbejde/devices.csv"])
        run(["benarbejde/sites.csv", "--emit-begyndelse-json",
             "--begyndelse-out", str(scratch_begyndelse),
             "--devices", "benarbejde/devices.csv"])

        drifted = []
        diff_dirs(scratch_ini_dir, drifted)
        diff_file(SITE_SERVICES, scratch_site_services, drifted,
                   "ansible/configs/inventory/group_vars/all/site_services.yml")
        diff_file(BEGYNDELSE, scratch_begyndelse, drifted,
                   "benarbejde/begyndelse.json")

    print("Regenerated configs/inventory/*.ini, site_services.yml, and begyndelse.json "
          "from benarbejde/sites.csv+devices.csv+address_policy.json+ad_forest.json, "
          "diffed against committed versions.")

    if drifted:
        print(f"\n{len(drifted)} generated file(s) have drifted from their source of truth:")
        for d in drifted:
            print(f"  - {d}")
        print("\nRun: python3 benarbejde/generate_inventory.py benarbejde/sites.csv "
              "-o ansible/configs/inventory --devices benarbejde/devices.csv "
              "(and --emit-group-vars / --emit-begyndelse-json) to fix.")
        return 1

    print("All generated files are fresh.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
