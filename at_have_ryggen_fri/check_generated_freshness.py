#!/usr/bin/env python3
"""
check_generated_freshness.py -- part of at_have_ryggen_fri.

benarbejde/generate_inventory.py is the single source of truth for four
generated outputs:
  - ansible/configs/inventory/<site>.ini  (one per site, 53 total)
  - ansible/configs/inventory/group_vars/all/site_services.yml
  - benarbejde/begyndelse.json
  - salt/pillar/sites.sls (added 2026-07-21, --emit-site-grains-pillar)

All four say, in their own header comment, "do not hand-edit, regenerate
instead" -- but nothing previously checked that anyone actually did. This
script regenerates all four into a scratch directory and diffs them
against the committed versions. Any difference means benarbejde/sites.csv,
devices.csv, address_policy.csv, or ad_forest.json changed without a
regeneration -- a real bug (the committed files are now describing a
world that no longer matches their own source of truth), not a style
nitpick.

main.ini, rudder.ini, and salt.ini are NOT generator output (they come from
ansibleme.sh's discovery scan / hand-curation) and are deliberately
excluded from this check.

Exit code: 0 if every generated file matches a fresh regeneration, 1 if
any has drifted.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BENARBEJDE = REPO_ROOT / "benarbejde"
GENERATOR = BENARBEJDE / "generate_inventory.py"
INVENTORY_DIR = REPO_ROOT / "ansible" / "configs" / "inventory"
SITE_SERVICES = INVENTORY_DIR / "group_vars" / "all" / "site_services.yml"
BEGYNDELSE = BENARBEJDE / "begyndelse.json"
SITE_GRAINS_PILLAR = REPO_ROOT / "salt" / "pillar" / "sites.sls"
# Served COPIES of benarbejde/ files, not second generator targets -- late_command.sh (both the
# Debian and top-level copies) / first-boot.sh / select-pve-answer.sh fetch these over HTTP from
# the provisioning server at boot time, before Ansible/benarbejde/ exist on the box. begyndelse.json
# found stale by hand 2026-07-21 (still had EXAPRVVRK001/EXAPRVFRD001 hostnames removed everywhere
# else, AND a leftover EXARDRCLD001 from before the 2026-07-20 RDR->RUD split, AND was missing the
# "salt" block entirely); devices.csv found stale the same day (same PRV->TMP rename). Neither had
# ever been checked before. sites.csv/address_policy.json/ad_forest.json were already in sync when
# checked, but are included here too so future drift in any of them is caught the same way.
# Checked as "must be byte-identical to the canonical benarbejde/ copy", not independently
# regenerated.
PROXMOX_SERVED_DIR = REPO_ROOT / "bootstrap" / "web" / "proxmox"
SERVED_COPIES = ["begyndelse.json", "devices.csv", "sites.csv", "address_policy.csv", "ad_forest.json"]

NOT_GENERATOR_OWNED = {"main.ini", "rudder.ini", "salt.ini"}


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
        scratch_site_grains_pillar = tmp / "sites.sls"

        run(["benarbejde/sites.csv", "-o", str(scratch_ini_dir),
             "--devices", "benarbejde/devices.csv"])
        run(["benarbejde/sites.csv", "--emit-group-vars",
             "--group-vars-out", str(scratch_site_services),
             "--devices", "benarbejde/devices.csv"])
        run(["benarbejde/sites.csv", "--emit-begyndelse-json",
             "--begyndelse-out", str(scratch_begyndelse),
             "--devices", "benarbejde/devices.csv"])
        run(["benarbejde/sites.csv", "--emit-site-grains-pillar",
             "--site-grains-pillar-out", str(scratch_site_grains_pillar),
             "--devices", "benarbejde/devices.csv"])

        drifted = []
        diff_dirs(scratch_ini_dir, drifted)
        diff_file(SITE_SERVICES, scratch_site_services, drifted,
                   "ansible/configs/inventory/group_vars/all/site_services.yml")
        diff_file(BEGYNDELSE, scratch_begyndelse, drifted,
                   "benarbejde/begyndelse.json")
        diff_file(SITE_GRAINS_PILLAR, scratch_site_grains_pillar, drifted,
                   "salt/pillar/sites.sls")

        for name in SERVED_COPIES:
            committed = BENARBEJDE / name
            served = PROXMOX_SERVED_DIR / name
            if not committed.exists():
                continue
            if not served.exists():
                drifted.append(f"bootstrap/web/proxmox/{name} (served copy) does not exist")
                continue
            if committed.read_text() != served.read_text():
                drifted.append(f"bootstrap/web/proxmox/{name} (served copy) differs from benarbejde/{name}")

    print("Regenerated configs/inventory/*.ini, site_services.yml, begyndelse.json, and "
          "salt/pillar/sites.sls from benarbejde/sites.csv+devices.csv+address_policy.csv+"
          "ad_forest.json, diffed against committed versions (including the served copies under "
          "bootstrap/web/proxmox/, which must stay byte-identical to their benarbejde/ originals).")

    if drifted:
        print(f"\n{len(drifted)} generated file(s) have drifted from their source of truth:")
        for d in drifted:
            print(f"  - {d}")
        print("\nRun: python3 benarbejde/generate_inventory.py benarbejde/sites.csv "
              "-o ansible/configs/inventory --devices benarbejde/devices.csv "
              "(and --emit-group-vars / --emit-begyndelse-json / --emit-site-grains-pillar) "
              "to fix. If any bootstrap/web/proxmox/ served copy drifted, "
              "cp benarbejde/<file> bootstrap/web/proxmox/<file> afterward for each one -- "
              "they're served copies, not independently regenerated.")
        return 1

    print("All generated files are fresh.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
