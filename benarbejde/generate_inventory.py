#!/usr/bin/env python3

# ==================================================================================================
# Example Music Inventory Generator
#
# Authoritative sources: /etc/example-music/sites.csv, /etc/example-music/devices.csv
#
# Requires an apt -y install python3-ipy to be run on your ansible node.
#
# Address allocation policy:
#
#   .1          RTR   Upstream router
#   .2-.4       BMC   iDRAC / iLO / Redfish
#   .5-.7       PVE   Proxmox nodes
#   .10         DCS1  Primary Domain Controller
#   .11         DCS2  Secondary Domain Controller
#   .19         NAS   Storage (NAS/SAN, e.g. TrueNAS)
#   .48         SBC   VoIP Session Border Controller
#   .100-.249   DHCP  DHCP Pool
#   .250-.252   SWI   Switches
#   .253        FWL1  Firewall
#   .254        FWL2  Firewall
#
# Everything else for a site — the long tail of real, non-standard devices (extra workstations,
# a Rudder server, a PBX, a NAS, right down to the vending machine — see devices.csv) — comes from
# devices.csv, joined in per-site on the Site column (sites.csv is the "left" table: one row per
# site drives which .ini gets written; devices.csv is the "right" table: zero or more rows per
# site, matched on Site, added into that site's .ini).
#
# Host naming:
#
#   EXA<ROLE><SITE><NNN>
# ==================================================================================================
# Changelog:
#  2026-07-26  Robert's explicit policy call: NAS/RDR/BMC/WAP joined DNS_MULTI_FIRST_INSTANCE_ONLY
#              (matching SWI's existing "every site has one, even if not physically racked yet"
#              treatment) -- previously excluded 2026-07-20 on "not universally deployed yet"
#              reasoning, which is a true fact but not a reason to withhold synthesis; unlike PRV
#              (structurally only ever exists at VRK/FRD), these are roles every real site WILL
#              have. Also fixed a real collision this surfaced: CLD's real UFC (UniFi Network
#              Controller) row sits on WAP1's own octet, which the generic real_device_types
#              suppression doesn't catch (it matches on Type, and "UFC" != "WAP") -- added "WAP"
#              to SUPPRESSED_STANDARD_ROLES["CLD"] alongside the existing "SBC" entry, same
#              pattern as PBX's own SBC-slot reuse. Caught before generating real DNS records,
#              not after.
#  2026-07-21  Fixed a real EXAFWLVRK001 duplicate-hostname collision found live in vrk.ini: two
#              entries, two different IPs (.139 and .69). Root cause was two-fold -- VRK's own
#              standard-slot FWL1 used the generic "this site's own octet within VRK's network"
#              formula, which for VRK itself (whose subnet IS the vRACK network) produced a
#              nonsensical self-referential 192.168.139.139 instead of the real
#              devices.csv-documented .69 address; and the standard-slot FWL1 line had no
#              skip-if-a-real-row-already-covers-it guard the way BMC/WAP already do, so it kept
#              rendering alongside devices.csv's own VRK,FWL,1,69 row under the identical
#              hostname. VRK now uses the same find_device()-based lookup CLD already used for
#              its own FWL1 WAN address, and the [firewalls] block now skips the standard-slot
#              FWL1 line whenever a real devices.csv row already covers instance 1.
#  2026-07-20  Robert: added role_codes.csv's new DNSAlias column (Type -> friendly short DNS
#              name, e.g. SLT -> "salt") as TYPE_DNS_ALIAS, loaded the same way as
#              TYPE_CONNECTION. --emit-devices-json now includes each device's own Type and
#              DNSAlias so bind9-dns.yml's devices.csv-driven zone can emit a CNAME for the
#              handful of roles that have one -- see db.forward-zone.devices.j2. Also added
#              "salt" (CLD's SLT row) to compute_site_services(), which both begyndelse.json
#              and site_services.yml derive from -- was missing entirely, so nothing had a
#              single source of truth for the Salt master's address; windows_bootstrap now
#              reads the DNS alias instead of a separately-hardcoded IP (see
#              group_vars/windows_nodes's removal and 82-salt-minion.yml).
#              Also properly CSV-quoted role_codes.csv's Notes column -- it had unescaped
#              commas in ~9 rows since it was first written (harmless in practice, since every
#              existing reader only accesses fields before Notes via DictReader, but genuinely
#              ambiguous CSV; fixed while every row was being touched for the new column
#              anyway rather than left to bite whoever reads Notes programmatically first).
#  2026-07-20  Robert: SUR (Microsoft Surface) now folds into windows_laptop -- DEVICE_GROUP_MAP
#              never had a SUR entry, so real SUR devices were silently falling into the generic
#              site_devices catch-all, even though windows_bootstrap/playbooks/00-preflight.yml's
#              own _role_group_map and group_vars/windows_laptop/vars.yml's own header have
#              treated SUR as windows_laptop all along -- the generator was the one place that
#              never got the memo. TAB (Tablet) added too, but conditionally: only folds into
#              windows_laptop when devices.csv's OS column actually says Windows -- real TAB rows
#              are mostly Android/iPadOS, and treating TAB as blanket-Windows would have pulled
#              those into a Windows-only inventory group. Found while wiring Salt (Windows client
#              endpoint config mgmt) scope up correctly -- see ansible/playbooks/windows_bootstrap/
#              playbooks/82-salt-minion.yml.
#  2026-07-19  Robert: PRV retired from address_policy.json entirely (offsets_single, _addressing,
#              connection_types.none, and DNS_SINGLE_ROLES below) -- confirmed via a real
#              --emit-devices-json run that every one of the 51 ordinary sites was getting a
#              synthesized EXAPRV<SITE>001 DNS record for a device that has never existed
#              anywhere (devices.csv has zero real PRV rows outside VRK/FRD, whose real ones sit
#              at .1/.50 via the devices.csv-exception path, untouched by this). Provisioning is
#              genuinely centralised at VRK/FRD, not per-site -- the standard .15 slot was dead
#              from the start. Added NAS (address_policy.json's new ".19") as its replacement
#              slot for site storage (TrueNAS), deliberately NOT added to DNS_SINGLE_ROLES --
#              same WAP/BMC treatment, since it isn't universally deployed yet either. Also
#              removed the 3 legacy NAS devices.csv rows (FAL/PER/MEL, all flagged Legacy=yes) --
#              considered retired, replaced by the new standard NAS slot going forward.
#  2026-07-16  Robert, live: brt.ini had EXAFWLBRT001 and EXAFWLBRT002 both at 192.168.169.253 --
#              the [firewalls] template used vals['FW'] (sites.csv's single LAN column) for BOTH
#              hostnames instead of the already-correctly-computed vals['FWL1']/vals['FWL2']
#              (.253/.254 respectively, from the ROLE_OFFSETS loop a few lines above -- the
#              values existed, the template just referenced the wrong variable). Fixed.
#              Also: FWL1's ansible_host is now the VRK/provisioning-network WAN address
#              (192.168.139.<site's own subnet octet>), not its LAN .253 -- confirmed live this
#              is how every firewall is actually managed, including CLD (whose LAN address only
#              ever worked in earlier testing because the control node happens to sit on that
#              exact subnet itself, not because LAN is generally reachable). CLD is a genuine
#              special case, reusing devices.csv's own VRK,FWL,1 row via find_device() rather
#              than the site-octet pattern, matching bind9-dns.yml's db.forward-zone.j2 (which
#              already generates exafwl<site>001-wan the same way). FWL2 is unaffected -- still
#              the LAN .254 secondary address.
#  2026-07-05  Fixed offset_ip() — IPy's IP.__add__ is reserved for merging two adjacent IP()/net
#              objects into a parent CIDR block (see https://pypi.org/project/IPy/), not address
#              offsetting. base + offset with offset as a plain int made IPy's __add__ try to read
#              offset._ipversion, causing 'int' object has no attribute '_ipversion'. Fixed by
#              converting to the integer form with .int(), adding there, then rebuilding an IP from
#              the result.
#  2026-07-05  Rewrote build_ini() to use the standard header block & proper multi-group INI syntax
#              (firewalls/windows_server/windows_desktop/windows_laptop/windows:children), matching
#              windows_bootstrap/inventory/cld.ini's structure. Hostnames (FWL/DCS1/DCS2/WKS1/LAP1)
#              now come from build_hostname() instead of duplicated as inline EXA{ROLE}{SITE}001
#              string literals — known source of truth for EXA<ROLE><SITE><NNN> naming convention.
#              (2026-07-09 note: the "windows_bootstrap/inventory/cld.ini" this comment refers to
#              no longer exists under that path/structure -- see the 2026-07-09 entry below.)
#  2026-07-05  Wire in unused hostname_map (BMC/PVE) built in generate() into build_ini(). PVE nodes
#              get a real, uncommented [pvenodes] group (matching the existing group_vars/pvenodes/
#              directory) since they're genuinely Ansible-managed. BMC hosts (iDRAC/iLO/Redfish) are
#              not Ansible-managed, so added as commented reference lines only, no group header.
#  2026-07-05  register_ip() now skips "N/A" entirely instead of treating it as a real address. Two
#              unrelated sites both legitimately having "N/A" for Gateway/DC/FW (e.g. VRK, BRD) were
#              colliding with each other on the literal string "N/A". N/A is an established sentinel
#              elsewhere in this estate (ad_schema.yml rejectattr('Subnet', 'equalto', 'N/A')); this
#              brings register_ip() in line with that convention.
#  2026-07-07  Fixed two bugs that made this script unrunnable: a stray "." after
#              ROLE_OFFSETS["FWL"]'s value (hard SyntaxError, the script could not even be
#              imported), and OFFSETS_SINGLE["DCS"] in generate() — OFFSETS_SINGLE never had a
#              "DCS" key (DCS lives in ROLE_OFFSETS, since it's a two-instance role like BMC/FWL/PVE,
#              not a single-instance one like RTR/PRV/SBC/WKS/LAP) — that would have raised
#              KeyError: 'DCS' on the very first site as soon as the syntax error was fixed.
#  2026-07-07  Merged inventory_devices.py's functionality in — this script now reads devices.csv
#              directly (no separate devices_old.csv/devices_new.csv preprocessing pass) and joins
#              each site's device rows into that site's generated .ini. Standard-offset devices
#              (already covered by the address policy above — e.g. a WKS row sitting exactly at
#              .101) and RAC/PVE rows (per longstanding operator instruction: RAC is being
#              decommissioned in favour of BMC, and real PVE nodes are handled by the standard
#              template + group_vars/pvenodes, not the devices.csv exception path) are still
#              excluded, same as inventory_devices.py did. inventory_devices.py is removed —
#              its logic lives here now, applied at generation time instead of as a one-off
#              preprocessing script, so there's one source of truth instead of two files that can
#              drift (devices.csv used to need a separate devices_new.csv regenerated by hand).
#  2026-07-07  Extracted OFFSETS_SINGLE/ROLE_OFFSETS into address_policy.json (sibling to
#              sites.csv) instead of hardcoding them here — bind9-dns.yml's Play 2 needs the same
#              standard-slot address policy (to synthesise DNS records for the standard devices,
#              now that devices.csv is exceptions-only rather than a complete device list) and
#              would otherwise be a second hand-maintained copy that could drift from this one.
#  2026-07-07  Added --emit-devices-json (compute_standard_devices_for_site/emit_devices_for_dns)
#              — bind9-dns.yml consumes this directly instead of re-deriving the standard-slot +
#              devices.csv-exception merge in Jinja, so DNS and the .ini generator can never
#              disagree about which devices are real or what they're called. Only synthesizes
#              slots build_ini() shows uncommented (RTR/PRV/SBC, both FWL instances, first
#              DCS/PVE instance only) — synthesizing the "example" WKS/LAP slots or BMC/DCS2/PVE2/
#              PVE3 caused real hostname collisions with devices.csv's own numbering in testing
#              (e.g. FAL's real WKS Number=1 at octet .100 colliding with the WKS "example" slot's
#              assumed index 1). BRD (legacy alias for BER, identical subnet) is folded into BER
#              entirely, hostnames rebuilt under BER. VRK (provisioning network, manually-assigned
#              roles) never gets standard-slot synthesis, only its real devices.csv rows.
#  2026-07-08  build_ini()'s header now includes a "Site Information" block (legal entity, city,
#              country, timezone, landline/mobile, subnet, gateway, firewall, primary DC, Ansible
#              region) — for humans reading the generated .ini, not for Ansible. This data was
#              already in sites.csv, just never surfaced in the file itself.
#  2026-07-08  Added WAP to ROLE_OFFSETS (.82-.94, 13 slots) — a gap in the addressing convention
#              not used by any standard slot or any site's real devices.csv rows, for moving WAPs
#              off DHCP to static IPs. Unlike BMC/DCS/PVE/FWL, WAP count varies wildly per site
#              (FAL has 6, most sites have 1-2) — deliberately NOT added to DNS_SINGLE_ROLES/
#              DNS_MULTI_ALL_INSTANCES/DNS_MULTI_FIRST_INSTANCE_ONLY, so no DNS records are
#              auto-synthesized for it, same treatment as BMC. Devices.csv rows at .82-.94 ARE
#              excluded from the .ini/DNS output as "already standard" (same STANDARD_OFFSETS
#              mechanism as every other role_offsets entry) — this was an explicit, informed
#              choice: real per-device Notes are lost for WAPs at this range in favour of treating
#              the slot as standardised, same tradeoff already accepted for DCS/PVE/FWL/RTR.
#  2026-07-08  Wired up devices.csv's ConnectionType column (was always blank, never read by
#              anything since the schema migration). address_policy.json now has a
#              connection_types map (Type -> ssh/winrm/telnet/snmp/http/none) — populated every
#              existing devices.csv row from it. is_managed()/needs_review() now treat
#              ConnectionType as a signal between Managed (explicit override) and the OS-regex
#              guess (fallback): snmp/http/none are never managed regardless of OS, since Ansible
#              can't task-execute over those. render_device_line() now emits the right
#              ansible_connection for ssh/winrm/telnet, and documents snmp/http as a query
#              protocol in the comment instead (Ansible itself never connects that way).
#  2026-07-08  Added --emit-group-vars: writes ansible/group_vars/all/site_services.yml, deriving
#              well-known service addresses (both provisioning servers, DNS, Ansible control node,
#              PBX x2, Rudder, WAC) from sites.csv/devices.csv instead of the hand-maintained
#              literals scattered across group_vars/all/vars.yml and windows_bootstrap playbooks.
#              Also emits exa_asset_base/exa_wallpaper_url directly (the concrete vars those
#              playbooks already read) so migrating off the hardcoded copies is a pure deletion,
#              not a rewrite. group_vars/all/vars.yml still defines these too for now (loads after
#              site_services.yml alphabetically, so it still wins) -- removing the duplicate is a
#              separate, deliberate follow-up, not done as part of adding this generator.
#  2026-07-08  Removed exa_asset_base/exa_wallpaper_url emission -- windows_bootstrap's wallpaper
#              and binaries now win_copy from a local files/ directory instead of HTTP-fetching
#              from the provisioning server (that pattern only ever existed for the pre-Ansible
#              bootstrap scripts). The site_services dict itself (provisioning server hostnames/
#              IPs/URLs, still useful documentation) is unchanged.
#  2026-07-09  Consolidated the two parallel inventory locations this generator and windows_dc
#              onboarding had drifted into. ansible/inventory/ (this script's own --out default)
#              and ansible/configs/inventory/ (windows_dc's hand-curated cld.ini/fal.ini/liv.ini)
#              had different, incompatible group structures for the exact same sites -- this
#              script put DCS1 straight into [windows_server] with no windows_dc/windows_nodes
#              groups at all, while configs/inventory/*.ini used a distinct
#              windows_dc -> windows_server -> windows -> windows_nodes chain (needed for
#              group_vars/windows_dc/ and group_vars/windows_nodes/connection.yml to apply).
#              Running both meant whichever one a given operator invocation happened to load
#              silently determined whether DC-specific group_vars applied at all. build_ini() now
#              emits the windows_dc/windows_nodes structure directly (DEVICE_GROUP_MAP's DCS entry
#              moved from windows_server to windows_dc to match), and --out's default moved from
#              ~/ansible/inventory to ~/ansible/configs/inventory -- one location, one structure,
#              matching what windows_dc onboarding has always actually needed. ansible/inventory/
#              retired; see configs/inventory/README or the commit that made this change for the
#              migration.
#  2026-07-09  Moved ansible/group_vars/ and ansible/host_vars/ to ansible/configs/inventory/
#              (group_vars_out default and doc references here updated to match). Root cause:
#              Ansible's group_vars/host_vars auto-loading is anchored to the actual loaded
#              inventory PATH (ansible.builtin.host_group_vars vars plugin, "only applies to
#              inventory sources that are existing paths") -- confirmed empirically that it must
#              be inside that path, not just a sibling of it. ansible/group_vars/ was never inside
#              ansible/configs/inventory/, so it silently never applied to any numbered playbook,
#              regardless of correct inventory group membership -- this is the real root cause
#              behind the registry_common/domain_ou_role crashes fixed earlier this session.
#              A symlink-based fix was tried and reverted -- this repo is cloned on Windows, Linux,
#              and macOS, and symlinks don't survive that reliably. A real directory move is the
#              only fix that's identical on every platform.
#  2026-07-14  Added SWI to role_offsets (.250-.252, address_policy.json) and
#              DNS_MULTI_FIRST_INSTANCE_ONLY -- per Robert: "even if the physical thing... isn't
#              yet there, it already has a 'space' to place it." Confirmed the .250 start is
#              simple arithmetic, not an arbitrary choice: DHCP's pool ends at .249 and FWL is
#              pinned to the top two addresses (.253/.254) with .255 as broadcast, leaving
#              .250-.252 as the only consecutive static gap left in the /24. Unlike DCS/PVE (which
#              never have devices.csv rows to collide with), 15 sites already have a real SWI row
#              carrying genuine vendor/model data -- SWI is deliberately EXEMPTED from the
#              STANDARD_OFFSETS devices.csv-exclusion mechanism (would have silently replaced real
#              Notes with a generic placeholder) and compute_standard_devices_for_site() gained a
#              real_device_types parameter so the synthetic placeholder is suppressed per-site
#              when a real devices.csv row already covers it. Verified via --emit-devices-json:
#              58 SWI entries (36 synthesized + 22 real), zero duplicate hostnames, VRK/FRD
#              correctly excluded (NON_STANDARD_SITES).
# ==================================================================================================

import csv
import json
import sys
import re
import argparse
from pathlib import Path
from IPy import IP

# ==================================================================================================
# ANSI colours
# ==================================================================================================
C = {
  "red": "\033[31m",
  "green": "\033[32m",
  "yellow": "\033[33m",
  "white": "\033[37m",
  "end": "\033[0m",
}

def msg(col, text):
  print(C[col] + text + C["end"])

# ==================================================================================================
# Address Policy
# ==================================================================================================
# Loaded at runtime from address_policy.csv (sibling to sites.csv by default; JSON until
# 2026-07-30, see load_address_policy()'s own docstring) — this is the single source of truth
# for standard-slot synthesis. bind9-dns.yml's own DNS records come from this same policy too,
# but only indirectly, via this script's --emit-devices-json (bind9-dns.yml never parses
# address_policy.csv itself — confirmed 2026-07-30, see feedback_check_dont_guess_known_source_
# of_truth in memory for why that distinction got checked rather than assumed). Do not hardcode
# a second copy here; if these dicts are empty, load_address_policy() hasn't run yet (see main()).
OFFSETS_SINGLE = {}
ROLE_OFFSETS = {}
STANDARD_OFFSETS = {}
TYPE_CONNECTION = {}
TYPE_DNS_ALIAS = {}

def load_address_policy(policy_path: Path, role_codes_path: Path = None):
  """Reads address_policy.csv (one row per octet: Type,Octet,Multi,Notes) and rebuilds the exact
  same OFFSETS_SINGLE (Type -> single int)/ROLE_OFFSETS (Type -> list[int]) shape every consumer
  already expects -- the on-disk format changed 2026-07-30 (JSON -> CSV, matching every other
  data file in this directory), the in-memory shape and everyone downstream of it did not.
  Multi=no rows go to OFFSETS_SINGLE (one octet per Type, last one wins if duplicated -- not
  expected, but no crash either); Multi=yes rows accumulate into ROLE_OFFSETS in file order.
  The old JSON's ".100-.249 DHCP pool" documentation-only entry was never consumed by any code
  (not in offsets_single or role_offsets either) -- correctly has no equivalent row here."""
  global OFFSETS_SINGLE, ROLE_OFFSETS, TYPE_CONNECTION, TYPE_DNS_ALIAS
  if not policy_path.exists():
    raise ValueError(
      f"address_policy.csv not found at {policy_path} — this is the shared source of truth "
      f"for the standard address policy (also used by bind9-dns.yml); it must exist alongside "
      f"sites.csv."
    )
  OFFSETS_SINGLE = {}
  ROLE_OFFSETS = {}
  with open(policy_path, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
      role = row["Type"].strip()
      octet = int(row["Octet"].strip())
      if row["Multi"].strip().lower() in ("yes", "y", "true", "1"):
        ROLE_OFFSETS.setdefault(role, []).append(octet)
      else:
        OFFSETS_SINGLE[role] = octet

  # TYPE_CONNECTION: Type -> ConnectionType (ssh/winrm/telnet/snmp/http/none). 2026-07-20: moved
  # from address_policy.json's own connection_types block (removed) to role_codes.csv's
  # Code/ConnectionMethod columns — role/type metadata belongs there, not in the addressing
  # policy file, and role_codes.csv is also generate_network_diagrams.py's TYPE_SYMBOLS source
  # now, so there's exactly one place this data lives instead of three (found drifted by one
  # entry, MBP, while consolidating — exactly the kind of thing keeping three hand-maintained
  # copies in sync eventually causes).
  TYPE_CONNECTION.clear()
  TYPE_DNS_ALIAS.clear()
  role_codes_path = role_codes_path or (policy_path.parent / "role_codes.csv")
  if role_codes_path.exists():
    with open(role_codes_path, newline="", encoding="utf-8") as f:
      for row in csv.DictReader(f):
        TYPE_CONNECTION[row["Code"]] = row["ConnectionMethod"]
        # DNSAlias: Type -> short friendly DNS name (e.g. SLT -> "salt"), added 2026-07-20.
        # Only a couple of roles have one (single-instance CLD-only services worth a nicer
        # name than the full EXA<ROLE><SITE><NNN> hostname) -- empty for everything else.
        # bind9-dns.yml's devices.csv-driven zone (db.forward-zone.devices.j2) emits a CNAME
        # for any device whose Type has a non-empty alias here.
        if row.get("DNSAlias"):
          TYPE_DNS_ALIAS[row["Code"]] = row["DNSAlias"]

  # STANDARD_OFFSETS: derived from the address policy just loaded (not a second, separately-
  # maintained copy — inventory_devices.py used to keep its own STANDARD_SINGLE/STANDARD_MULTI
  # tables, which could silently drift from OFFSETS_SINGLE/ROLE_OFFSETS; this builds them from
  # the same source instead). A devices.csv row whose Type+HostOctet exactly matches one of these
  # is already rendered by the standard template for that site — skip it rather than duplicate it.
  #
  # FULL_RENDER_TYPES are exempted from that skip — their real devices.csv rows always render
  # fully in [site_devices] (real Notes, real Managed status) instead of being silently dropped
  # or demoted to a generic placeholder, even when the octet matches the standard slot exactly.
  #   - SWI (exempted 2026-07-14): real devices.csv rows carry real vendor/model data (Cisco
  #     Catalyst 9300, "Core switch", etc.) for 15 sites — a generic "Standard SWI slot 1"
  #     placeholder would be a real data loss, not a dedup.
  #   - NAS/RDR/BMC/WAP (exempted 2026-07-20, Robert): found the hard way — NAS and BMC have no
  #     .ini template section at all, so a real devices.csv row landing exactly on their standard
  #     octet doesn't get demoted to a placeholder, it silently VANISHES from the .ini entirely
  #     (caught live: moving LIV's real badge reader onto RDR's new .21 standard slot made it
  #     disappear from liv.ini with nothing to show for it). Robert's call, explicitly: "by
  #     omission it makes a gap that trips us up in future, whereas by explicitly being there,
  #     even if not managed we can't conflate, confuse or omit them" — WAP included, even though
  #     it does have a template block (see wap_block below, now skips octets a real row already
  #     covers instead of listing both).
  #   - SBC/WKS/LAP (exempted 2026-08-04): same bug class, found the same way -- FAL,WKS,2
  #     (EXAWKSFAL002, "Reel-to-Reel Recorder 24-track", a real, confirmed-still-there device)
  #     silently vanished from fal.ini entirely when added at devices.csv's WKS Number=2, because
  #     its HostOctet (.101) exactly matches WKS's standard-slot octet -- same class of gap as
  #     RDR/NAS/BMC, just never swept to the rest of address_policy.csv's Multi=no roles when
  #     those three were fixed. RTR deliberately NOT added here: every current RTR row in
  #     devices.csv is old-network Legacy=yes data (see generate_network_diagrams.py's Old
  #     Network generator), not a live/current exception row -- exposing it here would surface
  #     historical vendor detail into the *current*-network .ini across ~19 sites, a separate,
  #     bigger decision than this fix, not something to fold in silently.
  STANDARD_OFFSETS.clear()
  FULL_RENDER_TYPES = {"SWI", "NAS", "RDR", "BMC", "WAP", "SBC", "WKS", "LAP"}
  for role, offset in OFFSETS_SINGLE.items():
    if role in FULL_RENDER_TYPES:
      continue
    STANDARD_OFFSETS.setdefault(role, set()).add(offset)
  for role, offsets in ROLE_OFFSETS.items():
    if role in FULL_RENDER_TYPES:
      continue
    STANDARD_OFFSETS.setdefault(role, set()).update(offsets)

# ==================================================================================================
# devices.csv join — classification of "extra" per-site devices
# ==================================================================================================
# devices.csv columns: Site, Type, Number, HostOctet, OS, ConnectionType, Managed, Notes

# Excluded unconditionally, regardless of octet (per longstanding operator instruction — RAC is
# being decommissioned in favour of BMC; real PVE nodes are handled by the standard template +
# group_vars/pvenodes/, not by the devices.csv exception path).
ALWAYS_EXCLUDE_TYPES = {"RAC", "PVE"}

# Known Type -> existing inventory group, for devices.csv rows that ARE Ansible-managed. Anything
# manageable but not in this map (e.g. a one-off NAS or Rudder relay) falls into a generic
# per-site [site_devices] group instead of a made-up group nothing else references.
#
# SUR (Microsoft Surface) folds into windows_laptop, not a new "windows_surface" group --
# windows_bootstrap/playbooks/00-preflight.yml's own _role_group_map already treats SUR as
# windows_laptop (SUR: [windows_laptop, windows, windows_nodes]), as does group_vars/
# windows_laptop/vars.yml's own header ("Variables for Windows laptop/tablet hosts (LAP,
# SUR)") -- this map just never had the SUR row to match, so real SUR devices were silently
# falling into the generic site_devices catch-all instead of windows_laptop. Fixed 2026-07-20.
#
# TAB (Tablet) is NOT unconditionally Windows -- real devices.csv rows are mostly Android
# ("Galaxy Tab") or iPadOS ("iPad"); only fold into windows_laptop when the OS column
# actually says Windows (see the TAB-specific override in load_devices() below). A non-
# Windows TAB stays in the generic site_devices catch-all, same as any other non-Windows
# endpoint -- there is no such thing as "Windows tablet" as a blanket assumption here.
DEVICE_GROUP_MAP = {
  "WKS": "windows_desktop",
  "LAP": "windows_laptop",
  "SUR": "windows_laptop",
  "TAB": "windows_laptop",  # only when OS says Windows -- see override below
  "SVR": "windows_server",
  "DCS": "windows_dc",
  "FWL": "firewalls",
  # NAS (2026-07-22, ansible/playbooks/truenas/ added the same day): without this, a real
  # devices.csv NAS row would fall into the generic site_devices catch-all instead of a
  # targetable group -- matches FWL/DCS/etc's own treatment. No real row exists yet (the
  # .19 slot is reserved, not deployed -- see docs/proxmox/proxmox-dcm-pbs-planning.md's
  # Site Storage section), so this has no effect on any currently-generated .ini until one
  # is added.
  "NAS": "truenas_servers",
  # PVE (2026-07-30, alongside ALWAYS_EXCLUDE_TYPES's narrow NON_STANDARD_SITES carve-out):
  # a real devices.csv PVE row (currently only EXAPVEFRD001) needs group_vars/pvenodes/'s own
  # vars (pve_packages, template IDs, storage pool) the same as every standard-template PVE
  # node already gets -- without this it would fall into the generic site_devices catch-all
  # and silently miss all of that.
  "PVE": "pvenodes",
}

# Manageability default when devices.csv's own Managed column is blank (true for every row at the
# time this was written — nobody has gone through and filled it in yet). Managed=yes/no on a row
# always overrides this; this is only the fallback guess. A real, recognisable server OS is a
# reasonable signal that this is something we'd actually run Ansible against; an appliance OS
# (or no OS at all — a switch, a coffee machine, a payment terminal) is not.
MANAGEABLE_OS_PATTERN = re.compile(
  r"windows|debian|ubuntu|trixie|bookworm|bullseye|noble|red ?hat|rhel|centos|rocky|almalinux"
  r"|truenas",
  re.IGNORECASE,
)

DEVICE_REQUIRED_COLUMNS = [
  "Site", "Type", "Number", "HostOctet", "OS", "ConnectionType", "Managed", "Notes"
]

# ==================================================================================================
# Special Sites
# ==================================================================================================

SPECIAL_SITES = {
  "VRK": "Virtual Rack / Cloud Abstraction Site (192.168.139.0/24)",
  "CLD": "Cloud Aggregation Site (192.168.69.0/24)",
}

# ==================================================================================================
# Collision Rules
# ==================================================================================================

## These roles are allowed to share same IP
ALLOWED_IP_ALIASES = {
  ("Gateway", "Firewall"),
  ("Firewall", "Gateway"),
}

## BRD / BER are allowed to overlap (legacy vs modern naming)
## Mohrenstraße 37 10117, Berlin, 18:53 CET, Donnerstag 9th November 1989
##
## PHI / VRK, 2026-09-04 -> REMOVED 2026-09-05: briefly needed here for a genuine coincidence,
## not a legacy-naming case like BRD/BER above. PHI's site octet (215) happened to equal
## EXABMCVRK002's devices.csv HostOctet at the time -- that device was actually still sitting on
## a DHCP-era IP from before the estate-wide BMC-pool convention existed, not the deliberate,
## permanent deviation it was believed to be when this entry was added (a same-day mix-up between
## EXABMCVRK001/002 during a long session -- see INC-2026-09-04-BMC-VRK002-IP). Once
## EXABMCVRK002 was corrected to its real, intended .4 slot, the collision this entry excused
## no longer exists at all -- confirmed by removing the entry and re-running
## check_duplicate_devices.py clean. Left removed rather than kept as a historical artifact:
## keeping it would silently excuse any FUTURE genuine collision between PHI and anything else on
## VRK's network, not just this resolved one.
ALLOWED_SITE_OVERLAP = {
  ("BRD", "BER"),
  ("BER", "BRD"),
}

## Cloud/hub "black swan" sites (CLD, FRD — see site-inventory-audit.py's own black-swan
## handling) have no real standalone Router device; the standard template's Router slot (.1)
## is a documentation-only placeholder for them, not a real device. FRD's actual devices.csv TMP
## row legitimately claims .1 (the real boot-url, per menu.ipxe/late_command.sh) — registering
## the fictional Router slot first would collide with it. Skip that one registration for these
## sites; every other standard-slot registration (Gateway/DC/FW) still happens as normal.
NO_STANDARD_ROUTER_SITES = {"CLD", "FRD"}

# ==================================================================================================
# State
# ==================================================================================================

seen_subnets = {}
seen_ips = {}

# ==================================================================================================
# Helpers
# ==================================================================================================
def validate_cidr(subnet: str):
  subnet = str(subnet).strip().replace("\r", "").replace("\n", "").replace(" ", "")

  try:
    net = IP(str(subnet))   # <-- FIX HERE
  except Exception as e:
    raise ValueError(f"Invalid CIDR '{subnet}': {e}")

  if net.version() != 4:
    raise ValueError(f"IPv4 only supported: {subnet}")
  return net

def offset_ip(net: IP, offset: int) -> str:
  base = IP(net.strNormal(0).split('/')[0])

  # IPy's IP + IP merges adjacent CIDR blocks into a parent network — it is not address offsetting,
  # and fails with a confusing AttributeError if the right-hand side isn't also an IP object. Do the
  # arithmetic on the integer form instead, then rebuild an IP from the result.
  return str(IP(base.int() + offset))

def register_subnet(site: str, net: IP):
  net = IP(str(net))  # FORCE canonical IP object

  for existing_net, existing_site in seen_subnets.items():
    existing_net = IP(str(existing_net))  # FORCE same type

    if (site, existing_site) in ALLOWED_SITE_OVERLAP:
      continue
    if net.overlaps(existing_net):
      raise ValueError(
        f"\nCIDR overlap detected:\n"
        f"  {site} ({net})\n"
        f"  conflicts with {existing_site} ({existing_net})"
      )
  seen_subnets[net.strNormal()] = site

def register_ip(site: str, ip: str, role: str):
  # "N/A" is an established sentinel for "no real value" elsewhere in this estate (e.g. ad_schema.yml
  # rejectattr('Subnet', 'equalto', 'N/A')). It's NOT a real address & must never be collision-checked
  # — two unrelated sites both legitimately having "N/A" for a field is not a collision.
  if str(ip).strip().upper() in ("N/A", "NA", ""):
    return

  if ip in seen_ips:
    prev_site, prev_role = seen_ips[ip]

    # allow intentional role sharing
    if (role, prev_role) in ALLOWED_IP_ALIASES:
      return

    # allow BRD/BER coexistence
    if (site, prev_site) in ALLOWED_SITE_OVERLAP:
      return

    raise ValueError(
      f"\nIP collision detected:\n"
      f"  {ip}\n"
      f"  {site} ({role})\n"
      f"  already used by {prev_site} ({prev_role})"
    )
  seen_ips[ip] = (site, role)

def build_hostname(role: str, site: str, index: int) -> str:
  return f"EXA{role}{site}{index:03d}"

# ==================================================================================================
# devices.csv — load, classify, and join per site
# ==================================================================================================

def validate_devices_csv_structure(rows):
  if not rows:
    return
  header = rows[0].keys()
  for col in DEVICE_REQUIRED_COLUMNS:
    if col not in header:
      raise ValueError(f"devices.csv missing column: {col}")

# ConnectionType values that are real Ansible connection methods (task-execution capable).
# snmp/http are monitoring/query protocols, not Ansible connection methods — a device with one
# of those (or "none") is never treated as managed, regardless of what its OS looks like.
ANSIBLE_CAPABLE_CONNECTIONS = {"ssh", "winrm", "telnet"}

def is_managed(row: dict) -> bool:
  """
  Priority: Managed column (explicit operator override) > ConnectionType (the row's own explicit
  value — a deliberate signal, not a guess; benarbejde/role_codes.csv's Code/ConnectionMethod
  columns document what each Type's ConnectionType should be) > OS-based guess (fallback for
  rows predating ConnectionType, or a Type with no entry in role_codes.csv).
  """
  flag = row.get("Managed", "").strip().lower()
  if flag in ("yes", "y", "true", "1"):
    return True
  if flag in ("no", "n", "false", "0"):
    return False

  conn = row.get("ConnectionType", "").strip().lower()
  if conn:
    return conn in ANSIBLE_CAPABLE_CONNECTIONS

  return bool(MANAGEABLE_OS_PATTERN.search(row.get("OS", "") or ""))

def needs_review(row: dict) -> bool:
  """Ambiguous rows: no explicit Managed flag, no ConnectionType, AND no OS-based signal either way."""
  flag = row.get("Managed", "").strip().lower()
  if flag in ("yes", "y", "true", "1", "no", "n", "false", "0"):
    return False
  if row.get("ConnectionType", "").strip():
    return False
  return not (row.get("OS", "") or "").strip()

def load_devices(devices_path: Path):
  """
  Reads devices.csv and returns (devices_by_site, stats) where devices_by_site maps
  site -> list of processed extra-host dicts (hostname, ip, group, managed, notes, type),
  ready to hand to build_ini(). Applies the same exclusions inventory_devices.py used to
  apply as a separate preprocessing pass (standard-offset rows, RAC/PVE rows).
  """
  stats = {
    "total": 0, "excluded_standard": 0, "excluded_always": 0, "excluded_planned": 0,
    "included_managed": 0, "included_reference": 0, "needs_review": 0,
  }
  devices_by_site = {}

  if not devices_path.exists():
    msg("yellow", f"devices.csv not found at {devices_path} — generating standard template only.")
    return devices_by_site, stats

  rows = list(csv.DictReader(devices_path.open()))
  validate_devices_csv_structure(rows)
  stats["total"] = len(rows)

  for r in rows:
    site = r["Site"].strip()
    dtype = r["Type"].strip().upper()
    octet_raw = r["HostOctet"].strip()

    # Planned=yes rows (2026-07-30) are hardware that doesn't exist yet -- known expansion slots
    # Robert has told us about directly (e.g. CLD's second BMC/PVE), not derived or guessed. Never
    # surfaced to any real consumer of this function (DNS zones, Ansible inventory, every existing
    # harness check) -- only benarbejde/generate_network_diagrams.py reads them, via its own
    # separate load_planned_devices(), specifically to draw them differently on a diagram. Keeping
    # the exclusion here (not in each individual consumer) means a new consumer of load_devices()
    # can't forget to filter these out and accidentally treat non-existent hardware as real.
    if (r.get("Planned") or "").strip().lower() in ("yes", "y", "true", "1"):
      stats["excluded_planned"] += 1
      continue

    # PVE is unconditionally excluded for every regular site (real PVE nodes come from the
    # standard template + group_vars/pvenodes/, never devices.csv) -- but VRK/FRD structurally
    # have no standard template at all (NON_STANDARD_SITES), so a real PVE there has no other way
    # to ever reach the real Ansible inventory. Narrow exception, 2026-07-30, after FRD's real
    # site kit (a NUC running Proxmox, confirmed by Robert) turned out to have no path to being
    # represented anywhere -- RAC stays unconditionally excluded regardless of site.
    if dtype in ALWAYS_EXCLUDE_TYPES and not (dtype == "PVE" and site in NON_STANDARD_SITES):
      stats["excluded_always"] += 1
      continue

    octet = int(octet_raw) if octet_raw.isdigit() else None
    # Same NON_STANDARD_SITES carve-out as the ALWAYS_EXCLUDE_TYPES check above, applied here too
    # (2026-07-30 fix): STANDARD_OFFSETS['PVE'] is {5,6,7} regardless of site, but VRK/FRD never
    # go through compute_standard_devices_for_site() at all (see the `site not in
    # NON_STANDARD_SITES` guard around that call), so there is no standard-template PVE row for
    # this check to be deduplicating against there -- without this, FRD's real EXAPVEFRD001 at
    # octet 5 was silently vanishing here, having already survived the ALWAYS_EXCLUDE_TYPES check
    # just above.
    if (octet is not None and octet in STANDARD_OFFSETS.get(dtype, set())
        and not (dtype == "PVE" and site in NON_STANDARD_SITES)):
      stats["excluded_standard"] += 1
      continue

    try:
      number = int(r["Number"])
    except (KeyError, ValueError):
      msg("yellow", f"Skipping devices.csv row with non-numeric Number: {r}")
      continue

    managed = is_managed(r)
    review = needs_review(r)
    if review:
      stats["needs_review"] += 1
    if managed:
      stats["included_managed"] += 1
    else:
      stats["included_reference"] += 1

    _group = DEVICE_GROUP_MAP.get(dtype, "site_devices")
    if dtype == "TAB" and "windows" not in r.get("OS", "").strip().lower():
      # TAB covers Android/iPadOS tablets as well as Windows ones -- only a real Windows
      # OS string earns a spot in windows_laptop; blank/Android/iPadOS stays generic.
      _group = "site_devices"

    devices_by_site.setdefault(site, []).append({
      "hostname": build_hostname(dtype, site, number),
      "octet": octet,
      "type": dtype,
      "group": _group,
      "managed": managed,
      "needs_review": review,
      "os": r.get("OS", ""),
      "notes": r.get("Notes", ""),
      "connection_type": r.get("ConnectionType", "").strip().lower(),
      # Optional -- set only when this device's real IP is on a DIFFERENT site's subnet than
      # the one its hostname/Site column names (e.g. a device hostnamed EXA...CLD... that
      # physically sits on FRD Havn's own network, sharing OVH's vRACK fabric with CLD but
      # keeping its own subnet behind its own firewall). Empty/absent for the overwhelming
      # majority of rows, where Site alone determines both hostname and subnet.
      "subnet_site": (r.get("SubnetSite") or "").strip() or None,
    })

  return devices_by_site, stats

def render_device_line(net: IP, dev: dict) -> str:
  conn = dev.get("connection_type", "")
  notes_parts = [dev["notes"]] if dev["notes"] else []

  # snmp/http aren't Ansible connection methods — document them as a query/monitoring protocol
  # instead, since Ansible itself will never be the one connecting to these.
  if conn in ("snmp", "http"):
    notes_parts.append(f"reachable via {conn.upper()}")
  note = f"  # {' -- '.join(notes_parts)}" if notes_parts else ""

  # TMP (VRK/FRD's bootstrap-only provisioning servers) deliberately never gets a formal
  # EXA<ROLE><SITE><NNN> hostname (2026-07-21, Robert) -- unlike every OTHER ConnectionType=none
  # device here (payphones, jukeboxes, etc.), where a hostname-style label IS the point. IP only,
  # no leading "#" of its own -- the caller (build_ini's reference_lines join) already adds one.
  if dev["type"] == "TMP":
    if dev["octet"] is None:
      return f"(no HostOctet in devices.csv){note}"
    return f"{offset_ip(net, dev['octet'])}{note}"

  if dev["octet"] is None:
    return f"# {dev['hostname']}  (no HostOctet in devices.csv){note}"

  ip = offset_ip(net, dev["octet"])

  # ssh is Ansible's own default and needs no override; telnet/winrm do. Spelled out explicitly
  # for ssh too, for the same reason windows_dc/windows_bootstrap set it explicitly elsewhere in
  # this repo — makes it correct on an ungrouped/ad hoc run, not just when group_vars applies.
  conn_str = {
    "ssh":    "  ansible_connection=ssh",
    "winrm":  "  ansible_connection=winrm",
    "telnet": "  ansible_connection=community.general.telnet",
  }.get(conn, "")

  return f"{dev['hostname']}  ansible_host={ip}{conn_str}{note}"

# ==================================================================================================
# Output
# ==================================================================================================

def site_filename(site: str):
  return f"{site.lower()}.ini"


def build_ini(site, row, vals, hostnames, net, site_devices):
  managed_by_group = {}
  reference_lines = []
  review_lines = []

  # BMC (.2-.4): same skip-if-a-real-row-already-covers-it treatment as WAP below, added
  # 2026-07-20 for the same reason -- BMC now flows through the normal site_devices path (see
  # FULL_RENDER_TYPES) if a real row is ever added, so this generic 3-line placeholder must not
  # also list the same octet, or the same physical device shows up twice.
  real_bmc_octets = {dev["octet"] for dev in site_devices if dev["type"] == "BMC"}
  bmc_offsets = ROLE_OFFSETS.get("BMC", [])
  bmc_lines = "\n".join(
    f"# {hostnames[f'BMC{i}']}  {vals[f'BMC{i}']}"
    for i, off in enumerate(bmc_offsets, start=1)
    if off not in real_bmc_octets
  )
  bmc_block = (
    "# Out-of-band management (iDRAC/iLO/Redfish) — not Ansible-managed, for\n"
    "# reference only:\n"
    f"{bmc_lines}"
  ) if bmc_lines else "# Out-of-band management (iDRAC/iLO/Redfish) — all slots have real devices.csv entries below."

  # WAP (.82-.94, added 2026-07-08): count varies per site (unlike BMC/DCS/PVE/FWL's fixed
  # count), so every slot is commented/reference-only, never confirmed-real — matches BMC's
  # treatment. Rendered from ROLE_OFFSETS directly rather than hardcoded so this doesn't drift
  # if address_policy.json's WAP range is ever resized.
  #
  # CLD and VRK are skipped entirely: neither has physical WiFi (CLD is the datacenter/hub,
  # VRK is a virtual provisioning network) — showing a "you might put a WAP here" placeholder
  # at either would be actively misleading. CLD's .82 is instead a REAL device: the UniFi
  # Network Controller (see devices.csv, Type=UFC) that manages every site's WAPs — putting
  # controller/management infrastructure at the same octet the devices it manages use, at the
  # hub site that doesn't have any of those devices itself, is a deliberate convention, not a
  # collision to route around.
  if site in ("CLD", "VRK"):
    wap_block = (
      "# No WAP placeholder block here — this site has no physical WiFi (hub/provisioning\n"
      "# site, not a physical location that serves wireless clients)."
    )
  else:
    # 2026-07-20: skip any slot a real devices.csv WAP row already covers (see FULL_RENDER_TYPES
    # above) -- WAP rows now render fully via the normal site_devices path below, so listing the
    # same octet again here as a generic "you might put one here" placeholder would just
    # duplicate it.
    real_wap_octets = {dev["octet"] for dev in site_devices if dev["type"] == "WAP"}
    wap_offsets = ROLE_OFFSETS.get("WAP", [])
    wap_lines = "\n".join(
      f"# {hostnames[f'WAP{i}']}  {vals[f'WAP{i}']}"
      for i, off in enumerate(wap_offsets, start=1)
      if off not in real_wap_octets
    )
    wap_block = (
      "# Wireless access points (.82-.94, static) — count varies per site, not\n"
      "# Ansible-managed, for reference only. Uncomment the ones that actually exist\n"
      "# at this site:\n"
      f"{wap_lines}"
    )

  # Standard-slot collision guard (originally added 2026-07-21 for FWL1/EXAFWLVRK001 only --
  # VRK's own devices.csv row (VRK,FWL,1,69, the vRACK firewall's own WAN face) computed to the
  # exact same hostname as the standard-template FWL1 line, a real EXAFWLVRK001 duplicate-
  # hostname collision in vrk.ini. Swept 2026-07-22 to every other role+instance line in this
  # function that was still unconditional/unguarded, after the identical bug turned up live in
  # fal.ini for EXAWKSFAL001 and EXALAPFAL001 (commented placeholder vs. real device row, same
  # hostname, two different IPs). PVE1-3 don't need this: PVE is in ALWAYS_EXCLUDE_TYPES, so no
  # devices.csv PVE row ever reaches site_devices to collide with. BMC/WAP already had their own
  # (octet-based) guards before this and are left as-is.
  def covered_by_real_device(dtype, hostname):
    return any(dev["type"] == dtype and dev["hostname"] == hostname for dev in site_devices)

  fwl1_line = (
    f"{hostnames['FWL1']}  ansible_host={vals['FWL1']}  ansible_user=ansible  ansible_connection=ssh\n"
    if not covered_by_real_device("FWL", hostnames["FWL1"]) else ""
  )
  fwl2_line = (
    f"{hostnames['FWL2']}  ansible_host={vals['FWL2']}  ansible_user=ansible  ansible_connection=ssh"
    if not covered_by_real_device("FWL", hostnames["FWL2"]) else ""
  )
  dcs1_line = (
    f"{hostnames['DCS1']}  ansible_host={vals['DCS1']}\n"
    if not covered_by_real_device("DCS", hostnames["DCS1"]) else ""
  )
  dcs2_line = (
    f"# {hostnames['DCS2']}  ansible_host={vals['DCS2']}"
    if not covered_by_real_device("DCS", hostnames["DCS2"]) else ""
  )
  wks1_line = (
    f"# {hostnames['WKS1']}  ansible_host={vals['WKS1']}"
    if not covered_by_real_device("WKS", hostnames["WKS1"]) else ""
  )
  lap1_line = (
    f"# {hostnames['LAP1']}  ansible_host={vals['LAP1']}"
    if not covered_by_real_device("LAP", hostnames["LAP1"]) else ""
  )
  # PVE1-3 never needed this guard before 2026-07-30 -- PVE was in ALWAYS_EXCLUDE_TYPES
  # unconditionally, so no devices.csv PVE row ever reached site_devices to collide with. The
  # narrow NON_STANDARD_SITES exception (real hardware at VRK/FRD, e.g. EXAPVEFRD001) broke that
  # invariant -- without this guard, extra_group_blocks below would render a SECOND, duplicate
  # `[pvenodes]` header for the exact same hostname instead of folding into this one.
  pve1_line = (
    f"{hostnames['PVE1']}  ansible_host={vals['PVE1']}\n"
    if not covered_by_real_device("PVE", hostnames["PVE1"]) else ""
  )
  pve2_line = (
    f"# {hostnames['PVE2']}  ansible_host={vals['PVE2']}\n"
    if not covered_by_real_device("PVE", hostnames["PVE2"]) else ""
  )
  pve3_line = (
    f"# {hostnames['PVE3']}  ansible_host={vals['PVE3']}"
    if not covered_by_real_device("PVE", hostnames["PVE3"]) else ""
  )

  for dev in site_devices:
    line = render_device_line(dev.get("_net", net), dev)
    if dev["needs_review"]:
      review_lines.append(f"# NEEDS REVIEW (no OS/Managed set): {line}")
    elif dev["managed"]:
      managed_by_group.setdefault(dev["group"], []).append(line)
    else:
      reference_lines.append(line)

  extra_group_blocks = ""
  for group, lines in managed_by_group.items():
    if group in ("windows_desktop", "windows_laptop", "windows_server", "windows_dc", "firewalls", "pvenodes"):
      # These groups already exist above with their standard-template entries — append to
      # the SAME group rather than declaring it a second time (INI parsers merge repeated
      # group headers, but keeping it readable matters more than being clever here).
      continue
    extra_group_blocks += f"\n[{group}]\n" + "\n".join(lines) + "\n"

  # Devices destined for windows_desktop/windows_laptop/windows_dc/firewalls get folded
  # into those groups' existing blocks below via these lookups.
  def extra_for(group):
    lines = managed_by_group.get(group, [])
    return ("\n" + "\n".join(lines)) if lines else ""

  # windows_server has no standard-template hosts of its own any more (DCS moved to its own
  # windows_dc group below, :children-linked into windows_server) -- only devices.csv SVR-role
  # extras (a plain, non-DC server) put anything directly into windows_server. Only emit the
  # section if there's actually something to put in it, since an empty [windows_server] header
  # with nothing but a blank line under it is confusing next to windows_server:children below.
  windows_server_extra_block = ""
  if managed_by_group.get("windows_server"):
    windows_server_extra_block = "\n[windows_server]" + extra_for("windows_server") + "\n"

  other_devices_block = ""
  if reference_lines or review_lines:
    other_devices_block = (
      "\n# Other devices from devices.csv — not Ansible-managed (or not yet classified), "
      "for reference only:\n"
      + "\n".join(f"# {l}" for l in reference_lines)
      + ("\n" + "\n".join(review_lines) if review_lines else "")
      + "\n"
    )

  return f"""# ==================================================================================================
# inventory/{site_filename(site)}
# Example Music Limited — {vals['CITY']} ({site})
#
# --------------------------------------------------------------------------------------------------
# Site Information (for humans — Ansible does not read this block)
#
#   Legal entity  : {row['Entity']}
#   Location      : {row['City']}, {row['Country']} ({row['CountryCode']})
#   Timezone      : {row['Timezone']}
#   Landline      : {row['Landline']}
#   Mobile        : {row['Mobile']}
#
#   Subnet        : {row['Subnet']}
#   Gateway       : {row['Gateway']}
#   Firewall      : {row['FW']}
#   Primary DC    : {row['DC']}
#   Ansible region: {row['AnsibleRegion']}
# --------------------------------------------------------------------------------------------------
#
# THIS FILE IS AUTOMATICALLY GENERATED.
#
# Source:
# /etc/example-music/sites.csv (standard template)
# /etc/example-music/devices.csv (per-site extras, joined in on the Site column)
#
# DO NOT EDIT.
# Changes may be overwritten.
# --------------------------------------------------------------------------------------------------
#
# Addressing
#
# .10 Primary DC
# .11 Secondary DC
# .101 Example workstation
# .102 Example laptop
# .253 Primary Firewall (LAN side -- ansible_host below uses its VRK/WAN address instead,
#      192.168.139.<this site's own octet>; Ansible manages every firewall over the shared
#      provisioning network, not each site's own LAN)
# .254 Secondary Firewall
#
# ==================================================================================================

[firewalls]
{fwl1_line}{fwl2_line}{extra_for('firewalls')}

[windows_dc]
{dcs1_line}{dcs2_line}{extra_for('windows_dc')}

[windows_server:children]
windows_dc
{windows_server_extra_block}
[windows_desktop]
{wks1_line}{extra_for('windows_desktop')}

[windows_laptop]
{lap1_line}{extra_for('windows_laptop')}

[pvenodes]
{pve1_line}{pve2_line}{pve3_line}{extra_for('pvenodes')}

[windows:children]
windows_server
windows_desktop
windows_laptop

[windows_nodes:children]
windows
{extra_group_blocks}
{bmc_block}

{wap_block}
{other_devices_block}"""

# ==================================================================================================
# CSV validation
# ==================================================================================================

REQUIRED_COLUMNS = [
  "Site", "City", "Country", "CountryCode", "Subnet", "Gateway", "DC", "FW", "Landline", "Mobile",
  "Timezone", "AnsibleRegion", "Entity"
]

def validate_csv_structure(rows):
  if not rows:
    raise ValueError("CSV empty")
  header = rows[0].keys()

  for col in REQUIRED_COLUMNS:
    if col not in header:
      raise ValueError(f"Missing column: {col}")

# ==================================================================================================
# Standard device synthesis — for consumers other than the .ini generator (e.g. bind9-dns.yml,
# which needs a DNS record for every confirmed-real standard-slot device now that devices.csv is
# exceptions-only rather than a complete device list — see address_policy.json's header comment)
# ==================================================================================================
# Only slots build_ini() shows UNCOMMENTED (confirmed real, not a "may not be built yet"
# placeholder) are synthesized here:
#   - RTR/SBC: single-instance infra roles, always physically present at a real site (even
#     though they're not Ansible-managed/not rendered in the .ini at all)
#   - FWL: both instances (FWL1/FWL2) are real in every site's .ini
#   - DCS/PVE: only the FIRST instance is real in the .ini (DCS2/PVE2/PVE3 are commented —
#     "may not be built yet"); synthesizing a DNS record for a DC/PVE node that might not exist
#     would be actively misleading, and WOULD collide with devices.csv's OWN numbering for real
#     extra instances at that site (devices.csv's Number is chosen independently by whoever
#     filled in the row, not guaranteed to skip index 1)
#   - WKS/LAP "example" slots are never synthesized here, ever — a real devices.csv "WKS
#     Number=1" at a non-standard octet legitimately reuses EXAWKS<SITE>001, the same hostname
#     the "example" placeholder would use; unlike NAS/RDR/BMC/WAP below, there's no way to tell
#     apart "the standard slot" from "a real device that happens to claim the standard hostname"
#     for these two specifically, so they stay permanently excluded from synthesis.
#
# 2026-07-19, Robert: PRV removed from this list entirely (was here, alongside RTR/SBC, as an
# "always physically present" role). Confirmed via a real --emit-devices-json run that this was
# wrong for every one of the 51 ordinary sites: devices.csv has never had a single real PRV row
# for any of them — only VRK and FRD have real ones (at .1/.50 respectively, via the devices.csv-
# exception path, unrelated to this OFFSETS_SINGLE/DNS_SINGLE_ROLES mechanism and unaffected by
# this removal), because provisioning is genuinely centralised at VRK/FRD, not per-site. Every
# other site was getting a synthesized EXAPRV<SITE>001 DNS record for a device that never
# existed — the exact class of bug this repo's own harness exists to catch. PRV is a genuinely
# different case from what follows: provisioning is structurally centralised at 2 sites only, so
# "every site has one" was never true for it, at any point in time.
#
# 2026-07-26, Robert's explicit policy call: NAS/RDR/BMC/WAP were previously excluded from
# synthesis on 2026-07-20 with the reasoning "not universally deployed yet" -- correct as a fact
# (EXANASFAL001 is, as of this same day, the very first real NAS box in the whole estate), but
# wrong as a reason to withhold synthesis. Robert's own framing: every real site WILL eventually
# have a NAS, a badge reader, switches, WAPs, and BMCs -- not yet physically present is not the
# same as PRV's "structurally will never exist here," and SWI (added 2026-07-14, same treatment
# below) already proved this distinction out in practice with zero problems. Brought all four up
# to SWI's exact treatment -- NAS/RDR join DNS_SINGLE_ROLES (they're OFFSETS_SINGLE roles, same
# shape as RTR/SBC, not ROLE_OFFSETS -- confirmed live before committing: adding them to
# DNS_MULTI_FIRST_INSTANCE_ONLY instead was dead code, since that set is only ever consumed by a
# loop over ROLE_OFFSETS.items(), which NAS/RDR were never in; caught via --emit-devices-json
# showing 1-2 entries instead of ~51 before this was fixed). BMC/WAP genuinely are ROLE_OFFSETS
# roles, so DNS_MULTI_FIRST_INSTANCE_ONLY is the correct list for them.
DNS_SINGLE_ROLES = ["RTR", "SBC", "NAS", "RDR"]
# SWI moved here 2026-07-30 (was DNS_MULTI_FIRST_INSTANCE_ONLY, first-instance-only, since
# 2026-07-14) -- Robert's explicit call: treat SWI exactly like FWL, every site always gets DNS
# records for all 3 standard slots regardless of how many switches are actually racked. Real
# volume consequence, confirmed and accepted knowingly, not a guess: ~90 new placeholder A
# records estate-wide for hardware that doesn't exist yet at most sites. Robert: "this is fine,
# because they are DNS records... Jamie the PFY can do some DNS lookups and look at our
# documentation" when it's time to actually rack a second/third switch somewhere. WAP
# deliberately NOT given the same treatment -- stays first-instance-only below, real counts
# (1 to 13+) are the UniFi controller's own concern, DNS only needs to guarantee at least one
# exists, which DNS_MULTI_FIRST_INSTANCE_ONLY already does.
DNS_MULTI_ALL_INSTANCES = {"FWL", "SWI"}
# BMC/WAP joined 2026-07-26 -- see the note above (NAS/RDR joined DNS_SINGLE_ROLES instead, not
# this set -- different underlying offsets shape). PVE/DCS stay first-instance-only: no
# equivalent "always synthesize headroom" case has been made for either.
DNS_MULTI_FIRST_INSTANCE_ONLY = {"DCS", "PVE", "BMC", "WAP"}

def compute_standard_devices_for_site(site: str, net: IP, real_device_types: frozenset = frozenset(),
                                       real_device_octets: dict = None):
  """
  Returns every confirmed-real standard-slot device for one site as a flat list of dicts
  (Site, Hostname, HostOctet, Type, DNSAlias, Notes) — the same addresses build_ini() derives
  for the ones it shows uncommented, just shaped for JSON consumption instead of f-string
  interpolation.

  real_device_types: Types this site already has a genuine devices.csv row for (caller's
  responsibility to compute from devices_by_site). Used to suppress synthesizing a standard
  placeholder for DNS_SINGLE_ROLES (RTR/SBC/NAS/RDR) -- these only ever have one instance, so
  "any real row for this type" and "this specific instance is real" are the same question there.

  real_device_octets: {Type: frozenset(real octets)} -- the per-instance equivalent, used for
  ROLE_OFFSETS roles (SWI/FWL/BMC/PVE/DCS/WAP) instead of real_device_types. Found live
  2026-07-30, when SWI moved from first-instance-only to DNS_MULTI_ALL_INSTANCES (every site
  always gets all 3 standard slots, matching FWL): the old blanket-per-role suppression silently
  dropped ODE/BRK's auto-synthesized SWI1 the moment either site gained a real SWI2 row, because
  it only ever checked "does this TYPE have any real row," never "does THIS octet have one."
  A role not present in this dict gets no per-instance suppression at all (every offset
  synthesizes) -- callers that only care about DNS_SINGLE_ROLES can omit this entirely.
  """
  real_device_octets = real_device_octets or {}
  site_suppressed = SUPPRESSED_STANDARD_ROLES.get(site, set())

  devices = []
  for role in DNS_SINGLE_ROLES:
    if role in site_suppressed or role in real_device_types:
      continue
    devices.append({
      "Site": site,
      "Hostname": build_hostname(role, site, 1),
      "HostOctet": str(OFFSETS_SINGLE[role]),
      "Type": role,
      "DNSAlias": TYPE_DNS_ALIAS.get(role, ""),
      "Notes": f"Standard {role} slot",
    })
  for role, offsets in ROLE_OFFSETS.items():
    if role in site_suppressed:
      continue
    real_octets_here = real_device_octets.get(role, frozenset())
    if role in DNS_MULTI_ALL_INSTANCES:
      selected = [(i, o) for i, o in enumerate(offsets, start=1) if o not in real_octets_here]
    elif role in DNS_MULTI_FIRST_INSTANCE_ONLY:
      selected = [] if offsets[0] in real_octets_here else [(1, offsets[0])]
    else:
      continue  # e.g. BMC — always commented/reference-only, never synthesized for DNS
    for i, offset in selected:
      # FWL1's bare hostname is the VRK/provisioning-network WAN address, not the site's own
      # LAN slot -- matching build_ini()'s own vals["FWL1"] convention exactly (Ansible itself
      # connects via this address; confirmed live 2026-07-16 against a genuinely remote site,
      # BRT -- LAN isn't routable pre-tunnel). Robert, 2026-07-26, live: `host exafwlams001`
      # returned the LAN address while Ansible's own inventory meant the VRK one under the
      # exact same hostname -- DNS and the .ini generator had silently diverged on what the
      # bare name means. Fixed by making DNS match the .ini's convention (Robert's explicit
      # choice, not assumed): bare hostname now gets the VRK address here, and a second,
      # -LAN-suffixed entry (own HostOctet, no SubnetSite) carries what the bare hostname used
      # to mean, mirroring the existing `-wan` naming pattern already used in the DNS templates.
      # CLD is excluded (matches build_ini()'s own `if site in ("CLD", "VRK")` branch) -- CLD's
      # WAN face already has its own distinct, real devices.csv-driven hostname (EXAFWLVRK001,
      # Site=VRK), it was never ambiguous under EXAFWLCLD001 the way ordinary sites are, so
      # doesn't need the same dual-entry treatment.
      if role == "FWL" and i == 1 and site != "CLD":
        site_octet = int(net.strNormal(0).split("/")[0].split(".")[2])
        devices.append({
          "Site": site,
          "Hostname": build_hostname(role, site, i),
          "HostOctet": str(site_octet),
          "SubnetSite": "VRK",
          "Type": role,
          "DNSAlias": TYPE_DNS_ALIAS.get(role, ""),
          "Notes": f"Standard {role} slot {i} -- WAN/provisioning-network face, matches "
                   f"Ansible's own inventory convention for this hostname; LAN face is "
                   f"{build_hostname(role, site, i)}-LAN",
        })
        devices.append({
          "Site": site,
          "Hostname": f"{build_hostname(role, site, i)}-LAN",
          "HostOctet": str(offset),
          "Type": role,
          "DNSAlias": "",
          "Notes": f"Standard {role} slot {i} -- LAN face (this is what the bare hostname "
                   f"meant before 2026-07-26)",
        })
        continue
      devices.append({
        "Site": site,
        "Hostname": build_hostname(role, site, i),
        "HostOctet": str(offset),
        "Type": role,
        "DNSAlias": TYPE_DNS_ALIAS.get(role, ""),
        "Notes": f"Standard {role} slot {i}",
      })
  return devices

# BRD (West Berlin) is a real, separate site that happens to share BER's exact subnet — see
# ALLOWED_SITE_OVERLAP above, which already treats this as intentional: the .ini generator gives
# BRD its own brd.ini with its own EXA...BRD... hostnames at the same IPs as BER's. Two hostnames
# resolving to the same address is normal DNS (like aliases), so BRD gets its own standard-slot
# synthesis and keeps its own devices.csv rows here too — it is NOT folded into BER. (An earlier
# version of this function did fold BRD into BER, which silently erased BRD's own identity and
# its real devices.csv rows — wrong, caught in review.)

# Sites that have a real sites.csv row/subnet but deliberately do NOT follow the standard
# per-site convention (per bind9-dns.yml's own "CLD BLACK SWAN" documentation for VRK: the
# provisioning network, with manually-assigned roles — no EXADCS, no EXAPVE, no EXASBC). Their
# standard-slot devices are never synthesized; only their real devices.csv rows appear.
# FRD (Fredericia Havn) gets the same treatment — it's one machine (a MacBook playing PXE
# server + secondary PBX), not a real office with DCS/FWL/PVE of its own.
NON_STANDARD_SITES = {"VRK", "FRD"}

# CLD has real DCS/FWL/PVE (unlike VRK/FRD), so it can't go in NON_STANDARD_SITES wholesale —
# but it deliberately reuses specific empty standard slots for real devices.csv devices (PBX on
# the SBC octet, since CLD has no SBC of its own — same pattern as the UniFi controller reusing
# WAP1's octet). Suppress just those specific standard roles per site, so the fictional
# standard-slot entry doesn't collide in the DNS output with the real device sitting there.
# 2026-07-26: added "WAP" alongside the existing "SBC" suppression -- CLD's real UFC
# (UniFi Network Controller) row sits on WAP1's own octet (.82), same deliberate slot-reuse
# pattern as PBX reusing the empty SBC octet. The generic real_device_types suppression
# (compute_standard_devices_for_site's own docstring) only matches on Type, so a real "UFC"
# row does NOT suppress a synthesized "WAP" placeholder by itself -- confirmed by checking
# CLD's actual devices.csv rows before adding WAP/BMC to DNS_MULTI_FIRST_INSTANCE_ONLY, since
# without this fix CLD would get a phantom EXAWAPCLD001 DNS record colliding with the real
# EXAUFCCLD001 at the exact same IP.
# 2026-07-31: AKL/SYD added -- backfilling real WAP counts from ad_computers.json (the AD
# computer-object export, now the source of truth for these device lists per Robert) found both
# sites' real EXACAM<SITE>001 camera genuinely sits at .82, the same octet WAP1's synthesized
# default always uses. Same collision shape as CLD's SBC/WAP reuse above, just WAP-on-CAM instead
# of WAP-on-UFC -- resolved the same way: suppress the synthesized WAP1 placeholder, add a real
# devices.csv WAP1 row at the next free octet (.84 for both) instead. Every other backfilled site
# had no such collision, so WAP1 stays at the synthesized default (.82) there -- only WAP2+ needed
# real rows.
SUPPRESSED_STANDARD_ROLES = {
  "CLD": {"SBC", "WAP"},
  "AKL": {"WAP"},
  "SYD": {"WAP"},
}

def emit_devices_for_dns(csv_path: Path, devices_path: Path):
  """
  Prints the FULL, deduplicated device list (every standard-slot device for every site, plus
  every devices.csv exception that isn't just a redundant description of a standard slot) as
  JSON to stdout, with full_ip already resolved — everything bind9-dns.yml needs to generate DNS
  records, computed by the exact same rules (STANDARD_OFFSETS/ALWAYS_EXCLUDE_TYPES exclusion,
  build_hostname, ALLOWED_SITE_OVERLAP) the .ini generator uses, so the two can never disagree
  about which devices are real or what they're called. BRD/BER's shared subnet duplicates IPs
  under different hostnames by design — bind9-dns.yml keeps BRD out of the per-site *reverse*
  zone loop only (a subnet can only have one authoritative reverse zone; BER owns it), not out of
  the forward zone.

  OPEN QUESTION (2026-07-11, not resolved here): a device with a SubnetSite override (see
  load_devices()) now gets a correct full_ip on its real subnet, so the FORWARD zone is right.
  The REVERSE zone is not necessarily right — bind9-dns.yml's per-site reverse-zone loop filters
  all_devices by Site (the hostname/naming site), not SubnetSite, and CLD doesn't go through
  that generic loop at all (it has its own dedicated db.192.168.139 handling, which has no
  awareness of FRD's 172.16.124.0/24 range). A CLD-hostnamed, FRD-subnetted device may end up
  with no PTR record at all rather than a wrong one -- confirmed safe-by-omission, not fixed.
  Needs a real decision (does FRD Havn get its own reverse zone at all?) before touching the
  reverse-zone templates further.
  """
  rows = list(csv.DictReader(csv_path.open()))
  validate_csv_structure(rows)

  # Loaded before the standard-slot synthesis loop below (not after, as this used to be ordered)
  # so compute_standard_devices_for_site() can be told, per site, which Types already have a real
  # devices.csv row -- currently only matters for SWI (see that function's own docstring).
  # real_octets_by_site is the per-instance version (added 2026-07-30 alongside SWI's move to
  # DNS_MULTI_ALL_INSTANCES) -- without it, a site with a real SWI2 row would silently lose its
  # still-synthesized SWI1 in the live DNS zone, not just a diagram.
  devices_by_site, _stats = load_devices(devices_path)
  real_types_by_site = {
    site: {dev["type"] for dev in site_devices}
    for site, site_devices in devices_by_site.items()
  }
  real_octets_by_site = {}
  for site, site_devices in devices_by_site.items():
    for dev in site_devices:
      if dev["octet"] is not None:
        real_octets_by_site.setdefault(site, {}).setdefault(dev["type"], set()).add(int(dev["octet"]))

  subnet_base = {}
  all_devices = []
  for r in rows:
    try:
      net = validate_cidr(r["Subnet"])
    except ValueError:
      continue  # e.g. Subnet == "N/A" — same rows generate()'s per-site loop would also choke on
    subnet_base[r["Site"]] = ".".join(net.strNormal(0).split("/")[0].split(".")[:3])
    if r["Site"] in NON_STANDARD_SITES:
      continue  # e.g. VRK — no standard-convention devices, only its real devices.csv rows
    all_devices.extend(compute_standard_devices_for_site(
      r["Site"], net, real_device_types=real_types_by_site.get(r["Site"], frozenset()),
      real_device_octets=real_octets_by_site.get(r["Site"], {}),
    ))

  for site, site_devices in devices_by_site.items():
    for dev in site_devices:
      all_devices.append({
        "Site": site,
        # SubnetSite override (see load_devices()) -- which site's subnet this device's real
        # IP is actually on, if different from Site (its hostname/naming site). Empty string,
        # not None, so the reverse-zone consumer below can treat "" the same as "unset" without
        # a separate None check.
        "SubnetSite": dev["subnet_site"] or "",
        "Hostname": dev["hostname"],
        "HostOctet": str(dev["octet"]) if dev["octet"] is not None else "",
        # Type/DNSAlias added 2026-07-20 so bind9-dns.yml's devices.csv-driven zone can emit
        # a CNAME for the handful of roles with a friendly short name (role_codes.csv's
        # DNSAlias column) -- e.g. SLT -> "salt". Empty string for everything else, same
        # "empty not None" convention as SubnetSite above.
        "Type": dev["type"],
        "DNSAlias": TYPE_DNS_ALIAS.get(dev["type"], ""),
        "Notes": dev["notes"],
      })

  for d in all_devices:
    # Standard-slot devices (from compute_standard_devices_for_site()) never have a
    # SubnetSite key at all -- only devices.csv exceptions can carry one.
    base = subnet_base.get(d.get("SubnetSite") or d["Site"], "")
    d["full_ip"] = f"{base}.{d['HostOctet']}" if (base and d["HostOctet"]) else ""

  print(json.dumps(all_devices))

# ==================================================================================================
# Generated group_vars — well-known services
# ==================================================================================================
# Playbooks have historically hardcoded well-known service addresses (provisioning server,
# Ansible control node, PBX, etc) as literals scattered across many files — e.g.
# ansible/configs/inventory/group_vars/all/vars.yml's exa_asset_base, windows_bootstrap/playbooks/
# 05-bootstrap.yml's
# own duplicate copy of the same value, bind9-dns.yml's ancillary_hosts list. Every one of these
# is already a real devices.csv row; this emits them as a single generated group_vars file so
# Ansible reads one derived source instead of N hand-maintained copies that can silently drift
# (as CLD's PBX octet already did once this session — see generate_inventory.py's own changelog).

def find_device(devices_by_site: dict, site: str, dtype: str):
  """
  First devices.csv row matching (site, dtype), or None if there isn't one. Tries the direct
  Site bucket first (the common case), then falls back to scanning every site's devices for
  a SubnetSite match -- a device can be hostnamed/bucketed under one site while physically
  living on another's network (e.g. a CLD-hostnamed device whose real subnet is FRD Havn's),
  and callers here mean "physically at this site" (see prv_frd/pbx_frd below), not "hostnamed
  under this site". See load_devices()'s subnet_site field and the 2026-07-11 CLD/FRD rework.
  """
  for dev in devices_by_site.get(site, []):
    if dev["type"] == dtype:
      return dev
  for devs in devices_by_site.values():
    for dev in devs:
      if dev["type"] == dtype and dev.get("subnet_site") == site:
        return dev
  return None

def compute_site_services(csv_path: Path, devices_path: Path, ad_forest_path: Path = None) -> dict:
  """
  Well-known service hostnames/IPs/subnets derived from sites.csv + devices.csv, plus the AD
  forest's domain name (from ad_forest.json, if given) as "_domain_fqdn" -- underscore-prefixed
  since it's a single string, not a {hostname,ip,...} dict like the other entries. Shared by
  emit_group_vars() (site_services.yml, for Ansible) and emit_begyndelse_json() (begyndelse.json,
  for non-Ansible consumers like bindme.sh/menu.ipxe/firewallme) so the two outputs can never
  drift out of sync with each other -- this is the one place either is computed from.
  """
  rows = list(csv.DictReader(csv_path.open()))
  validate_csv_structure(rows)

  nets = {}
  for r in rows:
    try:
      nets[r["Site"]] = validate_cidr(r["Subnet"])
    except ValueError:
      continue  # e.g. Subnet == "N/A"

  devices_by_site, _stats = load_devices(devices_path)

  def lookup(site, dtype, with_subnet=False):
    dev = find_device(devices_by_site, site, dtype)
    if dev is None or dev["octet"] is None or site not in nets:
      return None
    result = {"hostname": dev["hostname"], "ip": offset_ip(nets[site], dev["octet"])}
    if with_subnet:
      result["subnet"] = str(nets[site])
    return result

  tmp_edi = lookup("VRK", "TMP", with_subnet=True)
  tmp_frd = lookup("FRD", "TMP", with_subnet=True)
  dns = lookup("VRK", "DNS")
  ans = lookup("CLD", "ANS")
  pbx_edi = lookup("CLD", "PBX")
  pbx_frd = lookup("FRD", "PBX")
  rdr = lookup("CLD", "RUD")  # 2026-07-20: Type renamed RDR -> RUD (badge readers kept RDR)
  wac = lookup("CLD", "SVR")
  slt = lookup("CLD", "SLT")

  # Port 8000 is a real, fixed detail of the Fredericia Havn MacBook's python3 http.server setup
  # (menu.ipxe/late_command.sh both hardcode it too) -- not derivable from devices.csv, which has
  # no port column. Documented here for reference even though nothing currently consumes these
  # URLs directly -- windows_bootstrap's assets moved to a local files/ win_copy (2026-07-08),
  # since HTTP-fetching from the provisioning server was only ever a pre-Ansible bootstrap thing.
  if tmp_edi:
    tmp_edi["url"] = f"http://{tmp_edi['ip']}"
  if tmp_frd:
    tmp_frd["url"] = f"http://{tmp_frd['ip']}:8000"

  # These two are bootstrap-only helpers (2026-07-21, Robert) -- deliberately never get a formal
  # EXA<ROLE><SITE><NNN> hostname or DNS record, unlike every other entry here. Drop "hostname"
  # (the only field lookup() gives every other row) so nothing downstream can accidentally treat
  # one as a real, named, DNS-resolvable node -- IP/subnet/url only.
  for tmp in (tmp_edi, tmp_frd):
    if tmp:
      tmp.pop("hostname", None)

  result = {
    "provisioning_edinburgh": tmp_edi,
    "provisioning_fredericia_havn": tmp_frd,
    "dns": dns,
    "ansible_control": ans,
    "pbx_edinburgh": pbx_edi,
    "pbx_fredericia_havn": pbx_frd,
    "rudder": rdr,
    "wac": wac,
    "salt": slt,
  }

  if ad_forest_path is not None and ad_forest_path.exists():
    ad_forest = json.loads(ad_forest_path.read_text())
    result["_domain_fqdn"] = ad_forest.get("domain_fqdn")

  return result


def emit_group_vars(csv_path: Path, devices_path: Path, ad_forest_path: Path = None) -> str:
  """
  Returns the full text of ansible/configs/inventory/group_vars/all/site_services.yml -- well-known service
  hostnames/IPs derived from sites.csv + devices.csv, plus domain_fqdn from ad_forest.json.
  """
  services = compute_site_services(csv_path, devices_path, ad_forest_path)
  domain_fqdn = services.pop("_domain_fqdn", None)

  def yaml_block(name, dev):
    if dev is None:
      return f"  {name}: null  # no matching devices.csv row found\n"
    lines = [f"  {name}:\n"]
    for key in ("hostname", "ip", "subnet", "url"):
      if key in dev:
        lines.append(f"    {key}: \"{dev[key]}\"\n")
    return "".join(lines)

  blocks = "".join(yaml_block(name, dev) for name, dev in services.items())
  domain_line = f'  domain_fqdn: "{domain_fqdn}"\n' if domain_fqdn else ""

  return f"""\
# =============================================================================
# ansible/configs/inventory/group_vars/all/site_services.yml
# Example Music Limited — well-known service addresses
#
# THIS FILE IS AUTOMATICALLY GENERATED by benarbejde/generate_inventory.py --emit-group-vars.
# Source: sites.csv + devices.csv (single source of truth) — do not hand-edit, regenerate instead.
#
# Documents well-known service addresses in one derived place instead of hardcoded literals
# scattered across playbooks (e.g. bind9-dns.yml's ancillary_hosts, migrated 2026-07-08 to read
# devices.csv directly rather than this file — see that playbook's own changelog). If a
# well-known service's IP ever changes, fix its devices.csv row and regenerate.
#
# For non-Ansible consumers (bindme.sh, menu.ipxe, etc.) see benarbejde/begyndelse.json instead
# -- same underlying data, JSON, jq-friendly. Both are generated from compute_site_services() in
# this script, so they never drift out of sync with each other.
# =============================================================================

site_services:
{domain_line}{blocks}"""


def emit_begyndelse_json(csv_path: Path, devices_path: Path, ad_forest_path: Path = None) -> str:
  """
  Returns the full text of benarbejde/begyndelse.json -- the same well-known service data as
  site_services.yml, in JSON, for non-Ansible consumers (bindme.sh/ansibleme.sh/firewallme.sh,
  menu.ipxe-adjacent tooling) to read via jq instead of hardcoding IPs.

  "Begyndelse" is Danish for "beginning"/"origin" -- matches benarbejde/'s own Danish naming.
  """
  services = compute_site_services(csv_path, devices_path, ad_forest_path)
  domain_fqdn = services.pop("_domain_fqdn", None)
  payload = {
    "_comment": (
      "Example Music Limited -- well-known service addresses. AUTOMATICALLY GENERATED by "
      "benarbejde/generate_inventory.py --emit-begyndelse-json. Source: sites.csv + devices.csv "
      "(single source of truth) -- do not hand-edit, regenerate instead. Same underlying data as "
      "ansible/configs/inventory/group_vars/all/site_services.yml (for Ansible); this file is for "
      "everything else."
    ),
    **({"domain_fqdn": domain_fqdn} if domain_fqdn else {}),
    **services,
  }
  return json.dumps(payload, indent=2) + "\n"

def emit_site_grains_pillar(csv_path: Path) -> str:
  """
  Returns the full text of salt/pillar/sites.sls -- a Site -> {city, country, country_code,
  entity, office_name, street_address, postal_code} lookup, read directly from sites.csv's own
  columns. No hand-duplication: Entity genuinely varies per site (real regional legal suffixes
  -- ApS for Denmark, Ltd for Scotland/England, GmbH for Germany, B.V. for Netherlands, LLC.
  for the US, etc. -- not a single global company name), so this has to read the real column
  per site rather than assume one string fits everywhere. Consumed by salt/states/grains/
  init.sls to populate custom grains from a minion's own site code, the same way every other
  role in this estate (Rudder, Salt master itself, etc.) already gets site_city/site_country/
  site_entity -- via a real sites.csv lookup, not baked into the hostname.

  street_address/postal_code (2026-08-04, Robert): where the site's network infrastructure
  physically sits, not a general office/employee-workplace address -- see benarbejde/
  sites.csv's own Street/PostalCode columns. Empty string where sites.csv itself has the
  column blank (a few sites still have no postcode on record), same "blank is fine, don't
  fabricate" treatment as city/country/entity already get.

  office_name/country_code (2026-08-12, Robert): sites.csv's own Street column used to mix a
  venue/building name in with the actual street address for 14 sites (e.g. "Brockville
  Stadium, 1876 Hope Street") -- split into sites.csv's own new OfficeName column (blank
  where a site genuinely has no venue name, e.g. a plain street address) and a corrected
  Street value, per-site, by hand (Robert's own knowledge of each site, not a mechanical
  comma-split -- several of the pre-split values had a comma for an unrelated reason, e.g. an
  Italian "Piazza Name, number" address format, not a venue name). country_code was already a
  real sites.csv column (CountryCode), just not previously piped into this pillar.
  """
  rows = list(csv.DictReader(csv_path.open()))
  validate_csv_structure(rows)

  sites = {
    r["Site"]: {
      "city": r["City"], "country": r["Country"], "country_code": r.get("CountryCode", ""),
      "entity": r["Entity"], "office_name": r.get("OfficeName", ""),
      "street_address": r.get("Street", ""), "postal_code": r.get("PostalCode", ""),
    }
    for r in rows
  }

  lines = [
    "# =============================================================================",
    "# salt/pillar/sites.sls",
    "# Example Music Limited — Site -> {city, country, country_code, entity, office_name,",
    "# street_address, postal_code} lookup",
    "# =============================================================================",
    "# THIS FILE IS AUTOMATICALLY GENERATED by benarbejde/generate_inventory.py",
    "# --emit-site-grains-pillar. Source: sites.csv (single source of truth) -- do not",
    "# hand-edit, regenerate instead. Consumed by salt/states/grains/init.sls.",
    "# =============================================================================",
    "",
    "sites:",
  ]
  for site in sorted(sites):
    data = sites[site]
    lines.append(f"  {site}:")
    lines.append(f"    city: \"{data['city']}\"")
    lines.append(f"    country: \"{data['country']}\"")
    lines.append(f"    country_code: \"{data['country_code']}\"")
    lines.append(f"    entity: \"{data['entity']}\"")
    lines.append(f"    office_name: \"{data['office_name']}\"")
    lines.append(f"    street_address: \"{data['street_address']}\"")
    lines.append(f"    postal_code: \"{data['postal_code']}\"")
  return "\n".join(lines) + "\n"


def emit_sites_json(csv_path: Path) -> str:
  """
  Prints one Proxmox pool ID per sites.csv row (the site code itself, uppercased -- matches
  bootstrap/web/proxmox/manage-pool.py's own SITE_CODES naming exactly, no prefix or other
  transform) as a JSON array to stdout. Added 2026-07-22 so
  playbooks/proxmox/playbooks/35-pools.yml can stop reading sites.csv directly (deferred from
  2026-07-19 -- see that file's own header comment: "eventually this probably moves to reading
  from a benarbejde/*.json generated file instead of sites.csv directly"). The pool-ID
  derivation now lives here, the one place site-code-derived facts get computed, instead of
  being re-derived ad hoc in the playbook's own Jinja (map('upper')). Deliberately just the pool
  IDs, not the full row -- pool creation is the only consumer today and needs nothing else from
  sites.csv; add fields here if a future consumer needs them, rather than shipping unused ones
  now.
  """
  rows = list(csv.DictReader(csv_path.open()))
  validate_csv_structure(rows)
  pool_ids = sorted({r["Site"].strip().upper() for r in rows if r["Site"].strip()})
  return json.dumps(pool_ids)

# ==================================================================================================
# Generator
# ==================================================================================================

def generate(csv_path: Path, out_dir: Path, devices_path: Path):
  rows = list(csv.DictReader(csv_path.open()))
  validate_csv_structure(rows)

  out_dir.mkdir(parents=True, exist_ok=True)

  devices_by_site, device_stats = load_devices(devices_path)

  # Full site -> subnet lookup, built before the main loop so a devices.csv row's optional
  # SubnetSite override (a device whose hostname/site-segment is one site but whose real IP
  # is on a different site's subnet -- e.g. a device folded into CLD's naming that still
  # physically sits on FRD Havn's own network) can resolve regardless of row order in
  # sites.csv. See the 2026-07-11 CLD/FRD Pulsant-vRACK rework.
  site_to_net = {r["Site"]: validate_cidr(r["Subnet"]) for r in rows}

  for r in rows:
    site = r["Site"]
    net = validate_cidr(r["Subnet"])

    register_subnet(site, net)

    vals = {
      "SITE": site,
      "CITY": r["City"],
      "COUNTRY": r["Country"],
      "SUBNET": r["Subnet"],
      "GATEWAY": r["Gateway"],
      "DC": r["DC"],
      "FW": r["FW"],
      "TZ": r["Timezone"],
      "REGION": r["AnsibleRegion"],
    }

    hostname_map = {}

    ## fixed single-role offsets
    vals["RTR"] = offset_ip(net, OFFSETS_SINGLE["RTR"])
    vals["NAS"] = offset_ip(net, OFFSETS_SINGLE["NAS"])
    vals["SBC"] = offset_ip(net, OFFSETS_SINGLE["SBC"])
    vals["WKS1"] = offset_ip(net, OFFSETS_SINGLE["WKS"])
    vals["LAP1"] = offset_ip(net, OFFSETS_SINGLE["LAP"])

    ## fixed multi-role offsets (BMC/PVE etc)
    for role, offsets in ROLE_OFFSETS.items():
      for i, off in enumerate(offsets, start=1):
        ip = offset_ip(net, off)
        vals[f"{role}{i}"] = ip

        # NEW: deterministic hostname (3-digit safe)
        hostname_map[f"{role}{i}"] = build_hostname(role, site, i)

    # DCS special (DCS is a two-instance role, defined in ROLE_OFFSETS — not OFFSETS_SINGLE)
    vals["DCS1"] = offset_ip(net, ROLE_OFFSETS["DCS"][0])
    vals["DCS2"] = offset_ip(net, ROLE_OFFSETS["DCS"][1])

    # FWL1's ansible_host is the VRK/provisioning-network WAN address, not the site's own LAN
    # .253 -- Ansible manages every firewall over this shared network, confirmed live 2026-07-16
    # against a genuinely remote site (BRT): its own LAN is not routable from the control node at
    # all, "No route to host". CLD's LAN address only ever worked in earlier testing because the
    # control node happens to sit on that exact subnet itself, not because LAN is generally
    # reachable. Matches the same VRK-derived address bind9-dns.yml's own DNS zone already
    # generates as exafwl<site>001-wan -- see db.forward-zone.j2's "Firewall WAN addresses on
    # provisioning network" section, including its own CLD special case reproduced here: CLD's
    # WAN address comes from devices.csv's real VRK,FWL,1 row, not the site-octet pattern below,
    # since CLD's own subnet is the LAN side, not the vRACK.
    #
    # VRK is the SAME special case as CLD, not the generic else-branch below (fixed 2026-07-21,
    # found live as a real EXAFWLVRK001 duplicate-hostname collision with two different IPs in
    # vrk.ini): the else-branch's "this site's own octet within VRK's network" formula is meant
    # for a normal remote site; fed VRK's own site (whose subnet IS the vRACK network, octet
    # 139), it produced the nonsensical self-referential 192.168.139.139 instead of the real
    # devices.csv-documented address (.69) the devices.csv row itself already renders separately
    # under the same hostname -- hence the collision.
    if site in ("CLD", "VRK"):
      cld_fwl_wan = find_device(devices_by_site, "VRK", "FWL")
      vals["FWL1"] = offset_ip(site_to_net["VRK"], cld_fwl_wan["octet"])
    else:
      site_octet = int(net.strNormal(0).split("/")[0].split(".")[2])
      vals["FWL1"] = offset_ip(site_to_net["VRK"], site_octet)

    # Hostnames for roles that appear in .ini — built via build_hostname() so  EXA<ROLE><SITE><NNN>
    # convention lives in one place rather than being duplicated as inline string literals.
    hostnames = {
      "FWL1": build_hostname("FWL", site, 1),
      "DCS1": build_hostname("DCS", site, 1),
      "DCS2": build_hostname("DCS", site, 2),
      "WKS1": build_hostname("WKS", site, 1),
      "LAP1": build_hostname("LAP", site, 1),
    }
    hostnames.update(hostname_map)

    # register IPs — standard template
    register_ip(site, vals["GATEWAY"], "Gateway")
    register_ip(site, vals["DC"], "Domain Controller")
    register_ip(site, vals["FW"], "Firewall")
    if site not in NO_STANDARD_ROUTER_SITES:
      register_ip(site, vals["RTR"], "Router")

    # register IPs — devices.csv extras for this site (real collisions against the standard
    # template, or between two devices.csv rows, are still caught here)
    site_devices = devices_by_site.get(site, [])
    for dev in site_devices:
      dev["_net"] = site_to_net[dev["subnet_site"]] if dev["subnet_site"] else net
      if dev["octet"] is not None:
        register_ip(dev["subnet_site"] or site, offset_ip(dev["_net"], dev["octet"]), dev["type"])

    dest = out_dir / site_filename(site)

    if dest.exists():
      msg("yellow", f"{dest} exists")
      if input("Overwrite? [y/N]: ").strip().lower() != "y":
        continue

    dest.write_text(build_ini(site, r, vals, hostnames, net, site_devices))
    msg("green", f"Wrote {dest}")

  msg("white",
    f"\ndevices.csv: {device_stats['total']} rows read | "
    f"{device_stats['excluded_standard']} already-standard (skipped) | "
    f"{device_stats['excluded_always']} RAC/PVE (skipped) | "
    f"{device_stats['included_managed']} added as managed hosts | "
    f"{device_stats['included_reference']} added as reference-only | "
    f"{device_stats['needs_review']} flagged NEEDS REVIEW (no OS/Managed set)"
  )

# ==================================================================================================
# CLI
# ==================================================================================================

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("csv", type=Path, help="Path to sites.csv")
  parser.add_argument("-o", "--out", type=Path, default=Path.home() / "ansible/configs/inventory")
  parser.add_argument(
    "--devices", type=Path, default=None,
    help="Path to devices.csv (default: devices.csv next to sites.csv)"
  )
  parser.add_argument(
    "--policy", type=Path, default=None,
    help="Path to address_policy.csv (default: address_policy.csv next to sites.csv)"
  )
  parser.add_argument(
    "--role-codes", type=Path, default=None,
    help="Path to role_codes.csv (default: role_codes.csv next to sites.csv). Type -> "
         "ConnectionMethod for TYPE_CONNECTION."
  )
  parser.add_argument(
    "--ad-forest", type=Path, default=None,
    help="Path to ad_forest.json (default: ad_forest.json next to sites.csv). Used by "
         "--emit-group-vars/--emit-begyndelse-json to add a domain_fqdn field."
  )
  parser.add_argument(
    "--emit-devices-json", action="store_true",
    help="Print the full merged device list (standard-slot + devices.csv exceptions, full_ip "
         "resolved) as JSON to stdout instead of writing .ini files — used by bind9-dns.yml to "
         "generate DNS records from the exact same data the .ini generator uses."
  )
  parser.add_argument(
    "--emit-sites-json", action="store_true",
    help="Print the list of Proxmox pool IDs (one per sites.csv row, site code uppercased) as a "
         "JSON array to stdout — used by playbooks/proxmox/playbooks/35-pools.yml instead of "
         "reading sites.csv directly."
  )
  parser.add_argument(
    "--emit-group-vars", action="store_true",
    help="Write ansible/configs/inventory/group_vars/all/site_services.yml — well-known service "
         "addresses (provisioning servers, DNS, Ansible control node, PBX, Rudder, WAC) derived "
         "from sites.csv + devices.csv, instead of writing .ini files."
  )
  parser.add_argument(
    "--group-vars-out", type=Path, default=None,
    help="Path to write with --emit-group-vars (default: "
         "ansible/configs/inventory/group_vars/all/site_services.yml, resolved relative to this "
         "script's own location)."
  )
  parser.add_argument(
    "--emit-begyndelse-json", action="store_true",
    help="Write benarbejde/begyndelse.json — the same well-known service addresses as "
         "--emit-group-vars, in JSON, for non-Ansible consumers (bindme.sh, menu.ipxe, etc.) to "
         "read via jq instead of hardcoding IPs."
  )
  parser.add_argument(
    "--begyndelse-out", type=Path, default=None,
    help="Path to write with --emit-begyndelse-json (default: begyndelse.json next to sites.csv)."
  )
  parser.add_argument(
    "--emit-site-grains-pillar", action="store_true",
    help="Write salt/pillar/sites.sls — a Site -> {city, country, entity} lookup derived "
         "directly from sites.csv, for Salt's custom grains state (salt/states/grains/init.sls) "
         "to read instead of parsing this data out of a hostname/minion-ID scheme."
  )
  parser.add_argument(
    "--site-grains-pillar-out", type=Path, default=None,
    help="Path to write with --emit-site-grains-pillar (default: salt/pillar/sites.sls, "
         "resolved relative to this script's own location)."
  )
  args = parser.parse_args()

  devices_path = args.devices if args.devices is not None else args.csv.parent / "devices.csv"
  policy_path = args.policy if args.policy is not None else args.csv.parent / "address_policy.csv"
  role_codes_path = args.role_codes if args.role_codes is not None else args.csv.parent / "role_codes.csv"
  ad_forest_path = args.ad_forest if args.ad_forest is not None else args.csv.parent / "ad_forest.json"

  try:
    load_address_policy(policy_path, role_codes_path)
    # Each of these five modes is exclusive with the others -- --emit-devices-json/--emit-sites-json
    # print machine-readable data to stdout instead of writing files; --emit-group-vars/
    # --emit-begyndelse-json/--emit-site-grains-pillar each write exactly one, narrowly-scoped
    # side-effect file. check_generated_freshness.py relies on this: it calls the generator four
    # separate times, each with its own scratch-dir `-o`/`--*-out` path, to verify one output at a
    # time in isolation. A 2026-07-30 attempt to make these additive (so a single CLI invocation
    # combining `-o` with all three --emit-* flags, as check_generated_freshness.py's own fix hint
    # below reads if taken too literally, would do everything in one line) broke that isolation --
    # generate() started running as a side effect of check_generated_freshness.py's own narrowly-
    # scoped --emit-group-vars-only sub-call, targeting the default `-o` (~/ansible/configs/
    # inventory, outside this repo entirely) and silently writing 52 stray .ini files there.
    # Reverted; run these as four SEPARATE commands (see the fix hint text) if regenerating
    # everything, not one combined line.
    if args.emit_devices_json:
      emit_devices_for_dns(args.csv, devices_path)
    elif args.emit_sites_json:
      print(emit_sites_json(args.csv))
    elif args.emit_group_vars:
      group_vars_out = args.group_vars_out or (
        Path(__file__).resolve().parent.parent / "ansible" / "configs" / "inventory" / "group_vars"
        / "all" / "site_services.yml"
      )
      group_vars_out.parent.mkdir(parents=True, exist_ok=True)
      group_vars_out.write_text(emit_group_vars(args.csv, devices_path, ad_forest_path))
      msg("green", f"Wrote {group_vars_out}")
    elif args.emit_begyndelse_json:
      begyndelse_out = args.begyndelse_out or (args.csv.parent / "begyndelse.json")
      begyndelse_out.parent.mkdir(parents=True, exist_ok=True)
      begyndelse_out.write_text(emit_begyndelse_json(args.csv, devices_path, ad_forest_path))
      msg("green", f"Wrote {begyndelse_out}")
    elif args.emit_site_grains_pillar:
      site_grains_pillar_out = args.site_grains_pillar_out or (
        Path(__file__).resolve().parent.parent / "salt" / "pillar" / "sites.sls"
      )
      site_grains_pillar_out.parent.mkdir(parents=True, exist_ok=True)
      site_grains_pillar_out.write_text(emit_site_grains_pillar(args.csv))
      msg("green", f"Wrote {site_grains_pillar_out}")
    else:
      generate(args.csv, args.out, devices_path)
  except Exception as e:
    msg("red", f"[FATAL]\n{e}")
    sys.exit(2)

if __name__ == "__main__":
  main()
