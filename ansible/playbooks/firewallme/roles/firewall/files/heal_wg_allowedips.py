#!/usr/bin/env python3
# =============================================================================
# roles/firewall/files/heal_wg_allowedips.py
# Example Music Limited — add a spoke's own missing WAN address to its AllowedIPs
# =============================================================================
# Pushed to and run ON the hub by playbooks/heal-hub-allowedips.yml (ansible.builtin.script),
# operating on that hub's own /etc/wireguard/wg0.conf.
#
# Root cause this heals: INC-2026-10-30-WG-ALLOWEDIPS (docs/INCIDENT-LOG.md) found the hub's
# per-spoke AllowedIPs list never included that spoke's own WAN address -- only its tunnel IP
# and LAN subnet -- so the hub silently discards a reply arriving from a spoke's own WAN
# identity (e.g. replying to a connection relayed via the hub, not originating from the
# spoke's local network). Fixed in the code that WRITES a peer block on registration
# (10_register_spoke_on_hub.yml / add-wg-spoke.yml) -- but that fix only applies the next time
# a spoke successfully completes its OWN run, pushing itself onto the hub. A spoke that can't
# currently reach the hub to re-register (e.g. its own inbound SSH is broken -- the exact
# scenario this script exists for) stays stuck with its old, incomplete entry indefinitely,
# with no way to self-heal via the normal path. This script reconciles every ALREADY-
# registered spoke's entry from the hub side alone, needing no access to any spoke at all.
#
# Deliberately does NOT recompute the whole AllowedIPs string from scratch. The tunnel IP in
# particular is an ask-time value with a real override history (00_preflight_3_ask.yml:
# older spokes defaulted to .2, newer ones to .1, changed 2026-07-19) -- it is not safely
# re-derivable from the site octet alone, and guessing it here risks silently replacing a
# legitimately non-default value with the wrong one. Every other component (LAN subnet, WAN
# address) IS a pure convention from the site octet, confirmed directly against
# 00_preflight_1_derive.yml (fw_subnet = "192.168.<octet>", fw_wan_static_ip =
# "192.168.139.<octet>"), so only the one specific, known-missing piece -- the WAN address --
# is checked and appended; the tunnel IP, LAN subnet, and any extra subnets already on file
# are left completely untouched, whatever they are.
#
# Needs each site's octet to compute its WAN address -- passed in as a JSON object
# (site_code -> octet) built from the control node's own wg_site_octets var, not
# hand-maintained a second time here.
#
# Idempotent: a spoke whose AllowedIPs already includes its own WAN address is left alone,
# HEAL_COUNT=0 if none needed it, exit 0.
# --check: reports exactly what would be added, writes nothing.
# Apply mode: backs up the original file to <path>.bak-heal-allowedips before writing.
# =============================================================================
# Changelog:
#   2026-11-05  Initial version. Robert, after EXAFWLLIV001 turned up unreachable from
#               EXAANSCLD001 with the exact INC-2026-10-30-WG-ALLOWEDIPS symptom, and asked
#               whether a hub-only run could have healed it (rather than a one-off manual
#               command) -- it could, given every value needed except the tunnel IP already
#               derives from sites.csv alone, so built as a real, idempotent, reusable
#               mechanism rather than a one-off fix, matching dedupe_wg_peers.py's own shape.
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

        if wan_entry in existing_entries:
            continue  # already correct, nothing to do for this site

        new_entries = existing_entries + [wan_entry]
        new_allowedips = ", ".join(new_entries)
        new_block_body = (
            block_body[: ai_match.start(2)] + new_allowedips + block_body[ai_match.end(2) :]
        )

        fixes.append((m.start(), m.end(), site_code, new_block_body, current, new_allowedips))

    if not fixes:
        print("HEAL_COUNT=0")
        return 0

    for _start, _end, site_code, _new_body, old_ai, new_ai in fixes:
        print(f"-- {site_code}: AllowedIPs missing its own WAN address --")
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
