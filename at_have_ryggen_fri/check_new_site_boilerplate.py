#!/usr/bin/env python3
"""
check_new_site_boilerplate.py -- part of at_have_ryggen_fri.

Robert, 2026-09-24, on PHI/DET (both real sites.csv entries with zero real
equipment anywhere): "the harness needs to look for and identify new sites
which do not have any devices... you know the IPs, the subnets, the other
stuff, so can build a diagram, even if it's not feature filled out yet."

A "new" site here means genuinely zero rows in devices.csv AND zero records
in ad_computers.json for that Site -- not "missing one device type" (that's
check_ad_data_integrity.py's own, much narrower, job). For each one found,
prints the full day-one boilerplate equipment list with real, computed
hostnames and IPs -- everything a brand-new standard site is now confirmed
to get (see benarbejde/standard_site_boilerplate.json for the underlying
rules, all confirmed live with Robert the same evening):

  - RTR (.1, FortiGate), FWL (.253, vendor TBD per site)
  - SWI (.250, 96-port)
  - WAP (.82), SBC (.48), RDR (.21, badge reader), NAS (.19)
  - Two PVE nodes + their BMCs: server 1 is always HP/ILO (.5 / .3),
    server 2 is always Dell/RAC (.6 / .4) -- .2 is deliberately skipped,
    reserved for a second/legacy RTR (see README.md's Addressing section)
  - DCS (.10)

Deliberately excludes WKS/LAP (headcount-driven, not site-driven) and
CLD/VRK/FRD (each architecturally special -- see
standard_site_boilerplate.json's own excluded_sites_notes).

A bare run is an ADVISORY only -- it never fails the harness (always exits
0) and never writes anything. Robert, 2026-09-24, on doing this by hand:
"invariably a[sic] human error mistakes... the harness ought to flag it
then have a command line option to actually go add it... release the
'safety valve' to make changes... explicitly." --apply <SITE> is that
valve -- see apply_boilerplate() below.
"""
import csv
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BENARBEJDE = REPO_ROOT / "benarbejde"
DEVICES_CSV = BENARBEJDE / "devices.csv"
PROXMOX_DEVICES_CSV = REPO_ROOT / "bootstrap" / "web" / "proxmox" / "devices.csv"
DEVICES_CSV_COLUMNS = [
    "Site", "Type", "Number", "HostOctet", "OS", "ConnectionType", "Managed",
    "Notes", "SubnetSite", "Legacy", "Migrating", "Planned",
]
# Matches this file's own real, established devices.csv convention per Type --
# confirmed by grepping existing rows, not role_codes.csv's ConnectionMethod column
# alone (WAP in particular is documented there as snmp but every real devices.csv
# WAP row actually uses http -- match reality, not the aspirational policy doc).
CONNECTION_TYPES = {
    "RTR": "telnet", "FWL": "telnet", "SWI": "snmp", "WAP": "http",
    "SBC": "ssh", "RDR": "ssh", "NAS": "ssh", "ILO": "snmp", "RAC": "snmp",
    "PVE": "ssh", "DCS": "ssh",
}

sys.path.insert(0, str(BENARBEJDE))
import generate_inventory as gi  # noqa: E402


def load_sites(problems):
    """Reads via DictReader specifically -- an earlier plain csv.reader() version
    matched row[0] against nothing but a blank check, which let the header row
    itself ("Site,City,Country,...") through as if it were a real site named
    "Site" with subnet "Subnet". Found live 2026-09-24 asking the check to list
    its own findings out loud -- DictReader consumes the header line itself and
    can never make this mistake."""
    sites = {}
    try:
        with (BENARBEJDE / "sites.csv").open(newline="") as f:
            for row in csv.DictReader(f):
                site = (row.get("Site") or "").strip()
                subnet = (row.get("Subnet") or "").strip()
                if not site or not subnet:
                    continue
                base = ".".join(subnet.split("/")[0].split(".")[:3])
                sites[site] = base
    except Exception as e:
        problems.append(f"sites.csv: could not load -- {e}")
    return sites


def load_devices_sites(problems):
    sites = set()
    try:
        with DEVICES_CSV.open(newline="") as f:
            for row in csv.DictReader(f):
                site = (row.get("Site") or "").strip()
                if site:
                    sites.add(site)
    except Exception as e:
        problems.append(f"devices.csv: could not load -- {e}")
    return sites


def load_ad_computers_sites(problems):
    sites = set()
    try:
        computers = json.loads((BENARBEJDE / "ad_computers.json").read_text())
        for c in computers:
            site = (c.get("Site") or "").strip()
            if site:
                sites.add(site)
    except Exception as e:
        problems.append(f"ad_computers.json: could not load -- {e}")
    return sites


def load_boilerplate(problems):
    try:
        return json.loads((BENARBEJDE / "standard_site_boilerplate.json").read_text())
    except Exception as e:
        problems.append(f"standard_site_boilerplate.json: could not load -- {e}")
        return None


def build_boilerplate_rows(site, boilerplate):
    """One dict per day-one device a brand-new standard site gets, using
    address_policy.csv's own octets (via generate_inventory.py's already-loaded
    OFFSETS_SINGLE/ROLE_OFFSETS) plus this file's vendor conventions for
    anything address_policy.csv doesn't specify. Structured so it can feed
    both the advisory print-out and a real devices.csv write."""
    rows = []
    vendors = boilerplate.get("vendor_defaults", {})

    def add(role, number, octet, vendor=None, note=""):
        rows.append({
            "role": role, "number": number, "octet": octet,
            "vendor": vendor or "", "note": note,
        })

    add("RTR", 1, gi.OFFSETS_SINGLE.get("RTR", 1), vendors.get("RTR"))
    add("FWL", 1, gi.ROLE_OFFSETS.get("FWL", [253])[0], note="vendor varies per site, no default")
    add("SWI", 1, gi.ROLE_OFFSETS.get("SWI", [250])[0], vendors.get("SWI"), "96-port")
    add("WAP", 1, gi.ROLE_OFFSETS.get("WAP", [82])[0], vendors.get("WAP"))
    add("SBC", 1, gi.OFFSETS_SINGLE.get("SBC", 48), vendors.get("SBC"))
    add("RDR", 1, gi.OFFSETS_SINGLE.get("RDR", 21), vendors.get("RDR"), "badge reader")
    add("NAS", 1, gi.OFFSETS_SINGLE.get("NAS", 19), vendors.get("NAS"))

    pve_conv = boilerplate.get("pve_convention", {})
    pve_octets = gi.ROLE_OFFSETS.get("PVE", [5, 6])
    bmc_octets = gi.ROLE_OFFSETS.get("BMC", [2, 3, 4])
    # .2 deliberately skipped -- reserved for a second/legacy RTR (README.md Addressing)
    usable_bmc_octets = [o for o in bmc_octets if o != 2]
    for i, (num_str, conv) in enumerate(sorted(pve_conv.items())):
        num = int(num_str)
        pve_octet = pve_octets[num - 1] if num - 1 < len(pve_octets) else None
        bmc_octet = usable_bmc_octets[i] if i < len(usable_bmc_octets) else None
        add("PVE", num, pve_octet, conv.get("vendor"))
        add(conv.get("bmc_type", "BMC"), num, bmc_octet, note=f"BMC for PVE{num}")

    add("DCS", 1, gi.OFFSETS_SINGLE.get("DCS") or (gi.ROLE_OFFSETS.get("DCS", [10])[0]))

    return rows


def print_advisory(site, base, rows):
    print(f"\n  {site} ({base}.0/24):")
    for r in rows:
        hostname = gi.build_hostname(r["role"], site, r["number"])
        vendor_str = f" ({r['vendor']})" if r["vendor"] else ""
        note_str = f" -- {r['note']}" if r["note"] else ""
        print(f"    {hostname}  {base}.{r['octet']}{vendor_str}{note_str}")


def apply_boilerplate(site, sites, devices_sites, boilerplate):
    """The 'safety valve' -- Robert, 2026-09-24: normal runs stay read-only/
    advisory; this is the explicit, deliberate opt-in to actually write.
    Writes real devices.csv rows (Planned=yes -- the same convention already
    used estate-wide for confirmed-but-not-yet-built hardware, e.g. ODE's
    second firewall), then regenerates every derived artefact (.ini files,
    group_vars, diagrams) in the same run -- Robert, same conversation:
    skipping that "leaves operational gaps", so it's not a separate step
    here. Deliberately does NOT touch ad_computers.json -- that file drives
    real New-ADComputer creation, and writing planned/unbuilt hardware into
    it would try to create real AD objects for equipment that doesn't exist
    yet (see docs/adding-a-new-site.md's Phase 2)."""
    excluded = set(boilerplate.get("excluded_sites", []))

    if site not in sites:
        print(f"[ERROR] '{site}' is not a real site in sites.csv -- refusing to apply.")
        return 1
    if site in excluded:
        print(f"[ERROR] '{site}' is architecturally special ({', '.join(excluded)}) -- "
              f"refusing to apply the standard boilerplate. See standard_site_boilerplate.json's "
              f"own excluded_sites_notes.")
        return 1
    if site in devices_sites:
        print(f"[ERROR] '{site}' already has real devices.csv row(s) -- refusing to apply. "
              f"This is specifically for a genuinely brand-new site with zero existing rows, "
              f"not a way to bulk-append to one already in progress.")
        return 1

    rows = build_boilerplate_rows(site, boilerplate)
    incomplete = [r for r in rows if r["octet"] is None]
    if incomplete:
        print(f"[ERROR] Could not compute an octet for: "
              f"{', '.join(r['role'] + str(r['number']) for r in incomplete)} -- "
              f"address_policy.csv may be missing a convention. Aborting, nothing written.")
        return 1

    print(f"Applying standard boilerplate to '{site}' -- writing {len(rows)} Planned=yes "
          f"devices.csv row(s)...")

    with DEVICES_CSV.open("a", newline="") as f:
        writer = csv.writer(f)
        for r in rows:
            vendor_note = (
                f"{r['note']}. Vendor '{r['vendor']}' is a default pick, not confirmed."
                if r["vendor"] and r["note"]
                else f"Vendor '{r['vendor']}' is a default pick, not confirmed." if r["vendor"]
                else r["note"] or "Standard boilerplate for a new site, not yet built."
            )
            writer.writerow([
                site, r["role"], r["number"], r["octet"], r["vendor"],
                CONNECTION_TYPES.get(r["role"], "ssh"), "",
                f"PLANNED -- new-site boilerplate ({vendor_note})",
                "", "no", "", "yes",
            ])

    PROXMOX_DEVICES_CSV.write_bytes(DEVICES_CSV.read_bytes())
    print(f"  Wrote devices.csv rows, synced {PROXMOX_DEVICES_CSV.relative_to(REPO_ROOT)}.")

    print("Regenerating derived artefacts...")
    commands = [
        (["bash", "-c",
          f"yes | python3 {BENARBEJDE / 'generate_inventory.py'} {BENARBEJDE / 'sites.csv'} "
          f"-o {REPO_ROOT / 'ansible' / 'configs' / 'inventory'} --devices {DEVICES_CSV}"],
         "inventory .ini files"),
        ([sys.executable, str(BENARBEJDE / "generate_inventory.py"), str(BENARBEJDE / "sites.csv"),
          "--emit-group-vars", "--devices", str(DEVICES_CSV)], "group_vars"),
        ([sys.executable, str(BENARBEJDE / "generate_inventory.py"), str(BENARBEJDE / "sites.csv"),
          "--emit-begyndelse-json", "--devices", str(DEVICES_CSV)], "begyndelse.json"),
        ([sys.executable, str(BENARBEJDE / "generate_inventory.py"), str(BENARBEJDE / "sites.csv"),
          "--emit-site-grains-pillar", "--devices", str(DEVICES_CSV)], "Salt site-grains pillar"),
        ([sys.executable, str(BENARBEJDE / "generate_network_diagrams.py"), "--write"],
         "network diagrams"),
    ]
    for cmd, label in commands:
        result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  [ERROR] Regenerating {label} failed:\n{result.stdout}\n{result.stderr}")
            return 1
        print(f"  Regenerated {label}.")

    print(
        f"\nDone. '{site}' now has its full boilerplate as Planned=yes devices.csv rows, and "
        f"every derived artefact is regenerated. Run bash at_have_ryggen_fri/run.sh to confirm "
        f"clean, then commit. See docs/adding-a-new-site.md's Phase 2 for what happens as real "
        f"hardware actually gets built."
    )
    return 0


def main():
    problems = []
    apply_target = None
    if "--apply" in sys.argv:
        idx = sys.argv.index("--apply")
        if idx + 1 >= len(sys.argv):
            print("[ERROR] --apply requires a site code, e.g. --apply DET")
            return 1
        apply_target = sys.argv[idx + 1].strip().upper()

    sites = load_sites(problems)
    devices_sites = load_devices_sites(problems)
    ad_sites = load_ad_computers_sites(problems)
    boilerplate = load_boilerplate(problems)

    if problems:
        print("\n".join(problems))
        return 0 if apply_target is None else 1

    gi.load_address_policy(BENARBEJDE / "address_policy.csv")

    if apply_target:
        return apply_boilerplate(apply_target, sites, devices_sites, boilerplate)

    excluded = set(boilerplate.get("excluded_sites", []))
    new_sites = sorted(
        s for s in sites
        if s not in excluded and s not in devices_sites and s not in ad_sites
    )

    print(
        f"Checked {len(sites)} site(s) in sites.csv against devices.csv/ad_computers.json "
        f"for zero real equipment anywhere ({len(excluded)} architecturally-special site(s) "
        f"excluded: {', '.join(sorted(excluded))})."
    )

    if not new_sites:
        print("No genuinely new (zero-equipment) sites found.")
        return 0

    print(
        f"\n{len(new_sites)} new site(s) found with zero real equipment -- "
        f"day-one boilerplate for each (ADVISORY, not a failure -- run with "
        f"--apply <SITE> to actually write it):"
    )
    for site in new_sites:
        base = sites[site]
        print_advisory(site, base, build_boilerplate_rows(site, boilerplate))

    return 0


if __name__ == "__main__":
    sys.exit(main())
