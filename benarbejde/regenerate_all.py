#!/usr/bin/env python3
"""
benarbejde/regenerate_all.py -- Example Music Limited

The "one command" step of Robert's full-propagation single-source-of-truth vision
(2026-07-21): "I want to eventually get to a point where you can change something e.g.
an IP or a subnet or a user, and it permeates through the systems, updating,
regenerating ini files if needed, etc." -- see
[[project_full_propagation_ssot_vision]] in memory.

Researched before building (2026-10-01): most of that vision already exists --
at_have_ryggen_fri's freshness checks already regenerate every derived artefact into a
scratch copy and diff it against committed state, automatically, on every harness run.
What was still missing was a single command that actually APPLIES the regeneration --
docs/adding-new-sites-bands-devices-and-subnets.md's own Part B step 4 is five separate
commands, run by hand, every time. This file is that one command. It does not change how any of the five commands
work internally -- generate_inventory.py's own flags are deliberately NOT combined into
fewer calls (see that file's own 2026-07-30 changelog: an additive-flags attempt broke
check_generated_freshness.py's process isolation and leaked 52 stray .ini files into a
default path). This just orchestrates the same five, proven-separate subprocess calls
that at_have_ryggen_fri/check_new_site_boilerplate.py's own write_rows_and_regenerate()
already ran privately for its own --apply/--complete <SITE> workflow -- extracted here
as the one real, shared implementation, with that function now calling this instead of
keeping its own copy.

Usage:
    python3 benarbejde/regenerate_all.py
    python3 benarbejde/regenerate_all.py --verify
    python3 benarbejde/regenerate_all.py --devices /path/to/devices.csv --sites-csv /path/to/sites.csv

--verify additionally runs the full at_have_ryggen_fri harness afterward and surfaces
its exit code -- opt-in, not automatic, since that harness is a separate, more thorough
(and slower) concern someone may not always want chained into every regeneration.

Exit code: 0 if every regeneration step (and, with --verify, the harness) succeeded;
1 otherwise.
"""
import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BENARBEJDE = Path(__file__).resolve().parent


def regenerate_all(repo_root: Path, devices_csv: Path, sites_csv: Path) -> bool:
    """Runs the same five-command regeneration chain
    at_have_ryggen_fri/check_new_site_boilerplate.py's write_rows_and_regenerate() already
    proved live for its own narrower use case -- the single shared implementation both call
    sites use, so there is only ever one place that knows how to regenerate everything.
    Each command is a genuinely separate subprocess (not a combined set of generate_inventory.py
    flags, and not an in-process import of its main()) -- required by that file's own
    2026-07-30 changelog entry on why combining them broke process isolation. Returns True iff
    every step exits zero; stops and reports which step failed otherwise, rather than pressing
    on with a partially-regenerated estate."""
    benarbejde = Path(__file__).resolve().parent
    commands = [
        (["bash", "-c",
          f"yes | python3 {benarbejde / 'generate_inventory.py'} {sites_csv} "
          f"-o {repo_root / 'ansible' / 'configs' / 'inventory'} --devices {devices_csv}"],
         "inventory .ini files"),
        ([sys.executable, str(benarbejde / "generate_inventory.py"), str(sites_csv),
          "--emit-group-vars", "--devices", str(devices_csv)], "group_vars"),
        ([sys.executable, str(benarbejde / "generate_inventory.py"), str(sites_csv),
          "--emit-begyndelse-json", "--devices", str(devices_csv)], "begyndelse.json"),
        ([sys.executable, str(benarbejde / "generate_inventory.py"), str(sites_csv),
          "--emit-site-grains-pillar", "--devices", str(devices_csv)], "Salt site-grains pillar"),
        ([sys.executable, str(benarbejde / "generate_network_diagrams.py"), "--write"],
         "network diagrams"),
    ]
    for cmd, label in commands:
        result = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  [ERROR] Regenerating {label} failed:\n{result.stdout}\n{result.stderr}", flush=True)
            return False
        print(f"  Regenerated {label}.", flush=True)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().split("\n\n")[0])
    parser.add_argument(
        "--devices", type=Path, default=BENARBEJDE / "devices.csv",
        help="Path to devices.csv (default: benarbejde/devices.csv)"
    )
    parser.add_argument(
        "--sites-csv", type=Path, default=BENARBEJDE / "sites.csv",
        help="Path to sites.csv (default: benarbejde/sites.csv)"
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="After regenerating, also run the full at_have_ryggen_fri harness and surface its "
             "exit code -- confirms nothing else drifted, not just that this run's own output "
             "is internally consistent."
    )
    args = parser.parse_args()

    print("Regenerating derived artefacts...", flush=True)
    ok = regenerate_all(REPO_ROOT, args.devices, args.sites_csv)
    if not ok:
        sys.exit(1)

    if args.verify:
        print("\nRunning at_have_ryggen_fri/run.sh to verify...", flush=True)
        result = subprocess.run(
            ["bash", str(REPO_ROOT / "at_have_ryggen_fri" / "run.sh"), "--demur"],
            cwd=REPO_ROOT,
        )
        sys.exit(result.returncode)

    sys.exit(0)


if __name__ == "__main__":
    main()
