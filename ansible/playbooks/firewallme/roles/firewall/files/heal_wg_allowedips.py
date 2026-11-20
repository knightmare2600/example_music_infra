#!/usr/bin/env python3
# =============================================================================
# roles/firewall/files/heal_wg_allowedips.py
# Example Music Limited — strip a spoke's own WAN address back out of its AllowedIPs
# =============================================================================
# Pushed to and run ON the hub by playbooks/heal-hub-allowedips.yml (ansible.builtin.script),
# operating on that hub's own /etc/wireguard/wg0.conf.
#
# REVERSED, 2026-11-20, Robert's explicit architecture call. This script originally ADDED a
# spoke's own WAN address to its AllowedIPs (INC-2026-10-30-WG-ALLOWEDIPS, see the superseded
# changelog entry below) to stop the hub silently discarding a reply arriving from a spoke's
# own WAN identity. That fix worked, but AllowedIPs is WireGuard's only mechanism -- there is
# no way to use it as a crypto ingress filter without wg-quick's Table=auto *also* routing
# outbound WAN-to-WAN traffic through wg0 instead of the flat VRK L2 network. Confirmed live,
# same day, EXAFWLCLD001 -> EXAFWLEDI001/EXAFWLDET001: SSH to either one's own WAN address hung
# indefinitely even with a healthy, actively-transferring tunnel, because `ip route get`
# showed `dev wg0`, not the direct connected route. Robert's stated, intentional architecture:
# 192.168.139.0/24 reaches any device's WAN interface directly over that flat network, full
# stop -- wg0 is for LAN-to-LAN traffic only. The real fix for the original problem is
# upstream: tasks/zabbix_agent_onboard.yml now registers a firewall's Zabbix interface as its
# LAN IP, never its WAN IP, so the WAN-sourced-reply scenario this addition existed for can't
# occur any more -- this script now does the opposite of its original job, removing the entry
# if present rather than adding it if missing, to clean up every spoke this was already
# applied to (8, per feedback_wg_allowedips_duplicated_seven_places_2026_10_30.md).
#
# Deliberately does NOT touch anything else in the block. The tunnel IP in particular is an
# ask-time value with a real override history (00_preflight_3_ask.yml: older spokes defaulted
# to .2, newer ones to .1, changed 2026-07-19) and is left completely untouched either way,
# same as the LAN subnet and any extra subnets -- only the one specific entry (the WAN address,
# if present) is removed.
#
# Needs each site's octet to compute its WAN address -- passed in as a JSON object
# (site_code -> octet) built from the control node's own wg_site_octets var, not
# hand-maintained a second time here.
#
# Idempotent: a spoke whose AllowedIPs doesn't have its own WAN address (already correct, or
# never had this applied) is left alone, HEAL_COUNT=0 if none needed it, exit 0.
# --check: reports exactly what would be removed, writes nothing.
# Apply mode: backs up the original file to <path>.bak-heal-allowedips before writing.
# =============================================================================
# Changelog:
#   2026-11-20  REVERSED (see header above) -- removes the WAN address entry instead of
#               adding it. Same file, same mechanism, opposite direction; kept as one file
#               rather than a new script so the git history/blame for this exact AllowedIPs
#               entry stays in one place.
#   2026-11-05  Initial version (SUPERSEDED above). Robert, after EXAFWLLIV001 turned up
#               unreachable from EXAANSCLD001 with the exact INC-2026-10-30-WG-ALLOWEDIPS
#               symptom, and asked whether a hub-only run could have healed it (rather than a
#               one-off manual command) -- it could, given every value needed except the
#               tunnel IP already derives from sites.csv alone, so built as a real, idempotent,
#               reusable mechanism rather than a one-off fix, matching dedupe_wg_peers.py's own
#               shape.
# =============================================================================

import argparse
import json
import re
import sys
from pathlib import Path

MANAGED_RE = re.compile(
    r"(# BEGIN ANSIBLE MANAGED BLOCK (\S+)\n)(.*?)(\n# END ANSIBLE MANAGED BLOCK \2\n)",
    re.DOTALL,
)
PUBKEY_RE = re.compile(r"^PublicKey\s*=\s*(\S+)", re.MULTILINE)
ALLOWEDIPS_RE = re.compile(r"^(AllowedIPs\s*=\s*)(.*)$", re.MULTILINE)


def wan_address_for(site_code, site_octets):
    octet = site_octets.get(site_code)
    if octet is None:
        return None
    return f"192.168.139.{octet}"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path")
    ap.add_argument("site_octets_json", help="JSON object: {\"SITE\": octet, ...}")
    ap.add_argument("--check", action="store_true", help="Report only, write nothing")
    args = ap.parse_args()

    try:
        site_octets = json.loads(args.site_octets_json)
    except json.JSONDecodeError as e:
        print(f"ERROR: could not parse site_octets_json: {e}", file=sys.stderr)
        return 1

    content = Path(args.path).read_text()
    fixes = []  # (block_start, block_end, site_code, new_block_text, old_allowedips, new_allowedips)

    for m in MANAGED_RE.finditer(content):
        site_code = m.group(2)
        block_body = m.group(3)

        # The hub's own [Interface] section is wrapped in the same marker style
        # (09_wireguard_deploy.yml: "# {mark} ANSIBLE MANAGED BLOCK INTERFACE") --
        # it is not a spoke and has no [Peer]/AllowedIPs at all. Skip explicitly by
        # shape (no [Peer] in the block), not by relying on "INTERFACE" never
        # colliding with a real site code.
        if "[Peer]" not in block_body:
            continue

        wan_ip = wan_address_for(site_code, site_octets)
        if wan_ip is None:
            print(f"-- {site_code}: no known octet, skipping (not in site_octets) --")
            continue

        ai_match = ALLOWEDIPS_RE.search(block_body)
        if not ai_match:
            print(f"-- {site_code}: no AllowedIPs line found in its managed block, skipping --")
            continue

        current = ai_match.group(2).strip()
        existing_entries = [e.strip() for e in current.split(",") if e.strip()]
        wan_entry = f"{wan_ip}/32"

        if wan_entry not in existing_entries:
            continue  # already correct (never had it, or already stripped), nothing to do

        new_entries = [e for e in existing_entries if e != wan_entry]
        new_allowedips = ", ".join(new_entries)
        new_block_body = (
            block_body[: ai_match.start(2)] + new_allowedips + block_body[ai_match.end(2) :]
        )

        fixes.append((m.start(), m.end(), site_code, new_block_body, current, new_allowedips))

    if not fixes:
        print("HEAL_COUNT=0")
        return 0

    for _start, _end, site_code, _new_body, old_ai, new_ai in fixes:
        print(f"-- {site_code}: AllowedIPs still has its own WAN address, removing --")
        print(f"   current : {old_ai}")
        print(f"   corrected: {new_ai}")

    if args.check:
        print(f"HEAL_COUNT={len(fixes)} (check mode, nothing written)")
        return 0

    new_content = content
    for start, end, site_code, new_body, _old_ai, _new_ai in sorted(
        fixes, key=lambda f: f[0], reverse=True
    ):
        m = MANAGED_RE.match(content, start)
        rebuilt = m.group(1) + new_body + m.group(4)
        new_content = new_content[:start] + rebuilt + new_content[end:]

    Path(args.path + ".bak-heal-allowedips").write_text(content)
    Path(args.path).write_text(new_content)
    print(f"HEAL_COUNT={len(fixes)}")
    # 2026-11-20: removing an AllowedIPs entry here only corrects WireGuard's own
    # crypto-routing state (via the caller's `wg syncconf` afterward) -- it does NOT
    # remove whatever kernel route wg-quick's Table=auto previously installed for that
    # same entry (confirmed live: EXAFWLCLD001 kept routing to EDI/DET's WAN addresses
    # via wg0 after a syncconf-only heal run, because the `192.168.139.x/32 dev wg0`
    # route itself was untouched). Printed so the caller can clean those up too, without
    # this script needing route-table access/privileges of its own.
    print("FIXED_SITES=" + ",".join(site_code for _s, _e, site_code, _b, _o, _n in fixes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
