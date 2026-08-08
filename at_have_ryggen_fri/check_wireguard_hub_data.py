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

2026-08-08, Robert, live (EXAFWLLAX001): a real, live bug -- the AllowedIPs
builder in roles/firewall/tasks/00_preflight_4_post_ask.yml looped over
`[hub] + wg_hub_topology[hub]['spokes']` with no exclusion of the spoke this
list was being built FOR. Every spoke's own site code is a member of its
hub's own spokes: list (LAX is in CLD's), so every spoke's [Peer] AllowedIPs
included its own subnet -- wg-quick then installed that as a second, competing
kernel route to the box's own directly-connected LAN, racing the correct one
via fw_lan_iface. Symptom: LAN clients got 100% packet loss reaching anything
off their own subnet through the tunnel, while the firewall's own self-sourced
traffic (never touching this route) worked fine -- looked exactly like a
DNS/DHCP-lease bug at first. Fixed by adding `| reject('equalto',
fw_site_code) | list` to the all_sites derivation. Two checks added here
after that fix, following Robert's own framing ("is there anywhere in the
codebase that fights itself or adds duplicate things at variance with each
other"): a source-level regression guard on the exact fixed line (below), and
a data-level self-consistency check on wg_hub_topology itself (duplicate
spoke entries within one hub, a site double-booked across two hubs, or a hub
listed as its own spoke) -- the general shape of "a topology/loop-based
generator that doesn't exclude its own subject" this bug belongs to.
"""
import csv
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SITES_CSV = REPO_ROOT / "benarbejde" / "sites.csv"
HUB_DATA_FILE = REPO_ROOT / "ansible/configs/inventory/group_vars/firewalls/main.yml"
ALLOWED_IPS_TASK_FILE = (
    REPO_ROOT
    / "ansible/playbooks/firewallme/roles/firewall/tasks/00_preflight_4_post_ask.yml"
)


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


def load_hub_topology():
    """Minimal, targeted parse of the wg_hub_topology: block -- same
    dependency-free reasoning as load_hub_data() above. Returns
    {HUB: [spoke, spoke, ...]}, preserving duplicates exactly as written
    (duplicate detection is the caller's job, not this parser's)."""
    text = HUB_DATA_FILE.read_text(encoding="utf-8")
    m = re.search(r"^wg_hub_topology:\n((?:  \w+:\n    spokes:.*\n)+)", text, re.MULTILINE)
    if not m:
        return {}
    topology = {}
    for hub_m in re.finditer(r"^  (\w+):\n    spokes:\s*\[([^\]]*)\]", m.group(1), re.MULTILINE):
        hub = hub_m.group(1)
        raw = hub_m.group(2).strip()
        spokes = [s.strip() for s in raw.split(",") if s.strip()] if raw else []
        topology[hub] = spokes
    return topology


def check_allowed_ips_self_reference_guard():
    """Source-level regression guard: the AllowedIPs derivation this file's
    own docstring describes fixing must still exclude the current site from
    its own all_sites list. Grep-based on purpose (see
    check_network_session_safety.py for the same established pattern in this
    harness) -- cheap, exact, and catches the one thing that actually broke
    live: someone reverting or copy-pasting the pre-fix line."""
    if not ALLOWED_IPS_TASK_FILE.exists():
        return [f"{ALLOWED_IPS_TASK_FILE.relative_to(REPO_ROOT)} does not exist -- AllowedIPs self-reference guard can't run."]

    text = ALLOWED_IPS_TASK_FILE.read_text(encoding="utf-8")
    m = re.search(r"set all_sites = (.+?)-%\}", text)
    if not m:
        return [
            f"{ALLOWED_IPS_TASK_FILE.relative_to(REPO_ROOT)}: no 'set all_sites =' line found -- "
            f"the AllowedIPs derivation this check guards may have moved or been rewritten; update this check."
        ]
    expr = m.group(1)
    if "fw_site_code" not in expr:
        return [
            f"{ALLOWED_IPS_TASK_FILE.relative_to(REPO_ROOT)}: all_sites derivation ({expr.strip()}) no longer "
            f"excludes fw_site_code -- this is the exact self-referential-route bug fixed live on EXAFWLLAX001 "
            f"2026-08-08 (a spoke's own subnet ends up in its own [Peer] AllowedIPs, wg-quick installs it as a "
            f"second competing kernel route to the box's own LAN). Restore the "
            f"'| reject(\"equalto\", fw_site_code) | list' filter."
        ]
    return []


def check_topology_self_consistency(topology):
    """Data-level checks on wg_hub_topology itself -- the general 'duplicate
    or self-referential entry' shape the live AllowedIPs bug belongs to,
    independent of whether the Jinja that consumes this data currently
    filters correctly."""
    failures = []
    seen_under = {}  # site -> [hubs it appears under]

    for hub, spokes in topology.items():
        if hub in spokes:
            failures.append(f"wg_hub_topology.{hub}.spokes lists {hub} as its own spoke -- a hub can't be a spoke of itself.")

        counts = {}
        for s in spokes:
            counts[s] = counts.get(s, 0) + 1
        for s, n in counts.items():
            if n > 1:
                failures.append(f"wg_hub_topology.{hub}.spokes lists {s} {n} times -- duplicate entry.")

        for s in set(spokes):
            seen_under.setdefault(s, set()).add(hub)

    for site, hubs in seen_under.items():
        if len(hubs) > 1:
            failures.append(
                f"{site} appears as a spoke under more than one hub ({', '.join(sorted(hubs))}) -- "
                f"a spoke can only have one [Peer] entry pointing at one hub at a time."
            )

    return failures


def main():
    failures = []

    if not SITES_CSV.exists():
        return [f"{SITES_CSV.relative_to(REPO_ROOT)} does not exist."]
    if not HUB_DATA_FILE.exists():
        return [f"{HUB_DATA_FILE.relative_to(REPO_ROOT)} does not exist."]

    site_octets = load_site_octets()
    wan_ips, pubkeys = load_hub_data()
    topology = load_hub_topology()

    failures += check_allowed_ips_self_reference_guard()
    failures += check_topology_self_consistency(topology)

    if not wan_ips:
        failures.append(f"Could not parse wg_hub_wan_ips out of {HUB_DATA_FILE.relative_to(REPO_ROOT)} -- format may have changed.")
        return failures

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
    print(
        "wg_hub_wan_ips matches sites.csv's own subnet-octet convention for every hub; "
        "no blank known-good pubkeys; AllowedIPs self-reference guard intact; "
        "wg_hub_topology has no duplicate/double-booked/self-referential spokes."
    )
    sys.exit(0)
