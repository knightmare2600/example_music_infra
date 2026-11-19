#!/usr/bin/env python3
"""
snmp_device_inventory.py -- real devices.csv ConnectionType=snmp rows, resolved to
their real IP, as JSON. Feeds ansible/playbooks/zabbix/zabbix_server.yml's
"snmp_devices" play (Zabbix host.create registration) -- never used to write
anything itself, same "advisory/read-only helper" shape as suggest_free_ip.py.

Robert's ask, 2026-11-17: register every real SNMP-capable device (switches,
printers, BMCs) into Zabbix, agentless (SNMP interface, not zabbix-agent),
left DISABLED in the web UI -- just getting the host/interface/MIB plumbing
in place, not turning on live monitoring yet.

Deliberately reuses generate_inventory.py's own load_devices()/build_hostname()/
offset_ip()/validate_cidr() rather than re-deriving hostname/IP computation a
second time -- this repo's own standing "don't hand-roll, use the real
generator" rule. Only new logic here: filtering to connection_type == "snmp"
and resolving each row's EFFECTIVE subnet (SubnetSite override if set, same
precedence suggest_free_ip.py's own docstring documents), since load_devices()
itself returns octet/subnet_site but doesn't resolve the IP.

Usage:
  python3 benarbejde/snmp_device_inventory.py            # every snmp device, all sites
  python3 benarbejde/snmp_device_inventory.py --site FAL # one site only

Exit code: 0 always once sites.csv/devices.csv load successfully -- an empty
result (e.g. an unknown --site) is valid JSON (`[]`), not an error.
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BENARBEJDE = REPO_ROOT / "benarbejde"
sys.path.insert(0, str(BENARBEJDE))

import generate_inventory as gi  # noqa: E402
from suggest_free_ip import load_sites  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", help="Only this site's own SNMP devices (by hostname Site, not SubnetSite)")
    args = parser.parse_args()

    sites = load_sites()
    devices_by_site, _stats = gi.load_devices(BENARBEJDE / "devices.csv")

    # Per-site subnet, resolved once -- same validate_cidr() every other consumer of
    # sites.csv's Subnet column uses, not a fresh ip_network() call here.
    nets = {}
    for site, row in sites.items():
        subnet = (row.get("Subnet") or "").strip()
        if subnet.upper() in ("N/A", "NA", ""):
            continue
        try:
            nets[site] = gi.validate_cidr(subnet)
        except ValueError:
            continue

    out = []
    for site, devices in devices_by_site.items():
        if args.site and site != args.site:
            continue
        for dev in devices:
            if dev["connection_type"] != "snmp":
                continue
            if dev["octet"] is None:
                continue  # no real HostOctet (e.g. LND's "Steno writer no IP" row) -- nothing to poll
            effective_site = dev["subnet_site"] or site
            net = nets.get(effective_site)
            if net is None:
                continue  # unresolvable subnet -- skip rather than guess
            out.append({
                "hostname": dev["hostname"],
                "site": site,
                "effective_subnet_site": effective_site,
                "type": dev["type"],
                "os": dev["os"],
                "ip": gi.offset_ip(net, dev["octet"]),
                "notes": dev["notes"],
            })

    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
