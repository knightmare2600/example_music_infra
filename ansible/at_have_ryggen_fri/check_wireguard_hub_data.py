#!/usr/bin/env python3
"""
check_wireguard_hub_data.py -- part of at_have_ryggen_fri.

Robert, 2026-07-14, after finding CLD's WAN IP had been wrong in
group_vars/firewalls/main.yml ("192.168.139.139" instead of the real
"192.168.139.69") for an unknown length of time, live, during the
EXAFWLBRT001 firewallme test: "this suggests the harness is also not
checking such things against docs, or memories so fix all that shit up
too." This is that check.

Every WireGuard hub (CLD, FAL, ODE, BRK) follows one uniform, derivable
convention: its WAN IP on the provisioning network is
"192.168.139.<the hub's own site subnet octet, from sites.csv>" -- the same
convention 02_wan_config.yml itself uses to derive any site's static WAN IP.
Confirmed against all 4 real values before writing this check (not assumed):
FAL/ODE/BRK were already correct; only CLD had drifted.

Clone-safe, always runs -- only needs benarbejde/sites.csv and
ansible/configs/inventory/group_vars/firewalls/main.yml, no live host.

Does NOT check wg_hub_known_pubkeys for correctness (there's no
independent source of truth for a WireGuard public key outside the live
box itself -- that's exactly why 03_wireguard_config.yml fetches and
cross-checks it live rather than trusting a static file). Only flags a
key that's blank for a hub that has a real WAN IP on record, since a blank
entry silently skips the known-good cross-check for every spoke built
against that hub.
"""
import csv
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SITES_CSV = REPO_ROOT / "benarbejde" / "sites.csv"
HUB_DATA_FILE = REPO_ROOT / "ansible/configs/inventory/group_vars/firewalls/main.yml"


def load_site_octets():
    rows = list(csv.DictReader(SITES_CSV.open()))
    octets = {}
    for r in rows:
        m = re.match(r"^192\.168\.(\d+)\.0/24$", r["Subnet"].strip())
        if m:
            octets[r["Site"]] = m.group(1)
    return octets


def load_hub_data():
    """Minimal, targeted parse -- avoids a full YAML+Jinja round-trip (this file has
    no Jinja, just plain YAML) but doesn't pull in a YAML library dependency either;
    the two dicts we need (wg_hub_wan_ips, wg_hub_known_pubkeys) are simple
    SITE: "value" blocks, easy to parse directly and worth keeping dependency-free."""
    text = HUB_DATA_FILE.read_text(encoding="utf-8")

    def parse_block(key):
        m = re.search(rf"^{key}:\n((?:  \w+:.*\n)+)", text, re.MULTILINE)
        if not m:
            return {}
        block = {}
        for line in m.group(1).splitlines():
            lm = re.match(r'^\s*([A-Z]+):\s*"([^"]*)"', line)
            if lm:
                block[lm.group(1)] = lm.group(2)
        return block

    return parse_block("wg_hub_wan_ips"), parse_block("wg_hub_known_pubkeys")


def main():
    failures = []

    if not SITES_CSV.exists():
        return [f"{SITES_CSV.relative_to(REPO_ROOT)} does not exist."]
    if not HUB_DATA_FILE.exists():
        return [f"{HUB_DATA_FILE.relative_to(REPO_ROOT)} does not exist."]

    site_octets = load_site_octets()
    wan_ips, pubkeys = load_hub_data()

    if not wan_ips:
        return [f"Could not parse wg_hub_wan_ips out of {HUB_DATA_FILE.relative_to(REPO_ROOT)} -- format may have changed."]

    for hub, recorded_ip in wan_ips.items():
        octet = site_octets.get(hub)
        if octet is None:
            failures.append(f"{hub}: no matching site in sites.csv (or non-standard 192.168.x.0/24 subnet) -- can't verify its WAN IP.")
            continue
        expected_ip = f"192.168.139.{octet}"
        if recorded_ip != expected_ip:
            failures.append(
                f"{hub}: wg_hub_wan_ips says {recorded_ip!r}, but sites.csv's own subnet "
                f"octet ({octet}) implies {expected_ip!r} -- these must match the "
                f"'192.168.139.<site octet>' convention every other WAN IP in this estate follows."
            )

    for hub in wan_ips:
        if not pubkeys.get(hub, "").strip():
            failures.append(
                f"{hub}: wg_hub_known_pubkeys is blank -- every spoke built against this hub "
                f"will skip the known-good pubkey cross-check silently. Populate it via "
                f"ssh ansible@<hub-wan-ip> 'cat /etc/wireguard/public.key' once the hub is live."
            )

    return failures


if __name__ == "__main__":
    failures = main()
    if failures:
        print(f"{len(failures)} problem(s):")
        for f in failures:
            print(f"  {f}")
        sys.exit(1)
    print("wg_hub_wan_ips matches sites.csv's own subnet-octet convention for every hub; no blank known-good pubkeys.")
    sys.exit(0)
