#!/usr/bin/env python3
"""
docs/zabbix_templates/export_dashboard.py
Example Music Limited — Export a Zabbix dashboard to JSON via the real JSON-RPC API

=============================================================================
Robert's ask (2026-10-25): get the World Clocks widget's test dashboard into the repo
as JSON, same way the 8 companion templates in this directory already are, rather than
fight the UI's own Dashboards-list checkbox-then-Export control.

Real mechanism, confirmed against the live 7.0 API docs before writing this: dashboards
export via the same configuration.export method the templates use, under
options.dashboards (a list of dashboard IDs -- confirmed via the real docs that an
empty/omitted ID list does NOT mean "export everything", so dashboard.get is used
first to resolve a name to its real ID).

Auth/API-reachability logic shared with import_template.py via zabbix_api_common.py
(extracted the same day) -- not duplicated here.

Usage:
    python3 export_dashboard.py --host 192.168.69.13 --name "World Clocks"
    python3 export_dashboard.py --host 192.168.69.13 --id 5 --out docs/management/zabbix-worldclocks-dashboard.json

=============================================================================
Changelog:
    2026-10-25  Initial file.
=============================================================================
"""

import argparse
import getpass

from zabbix_api_common import discover_url, rpc


def resolve_dashboard_id(url, auth, name):
    dashboards = rpc(
        url,
        "dashboard.get",
        {"output": ["dashboardid", "name"], "search": {"name": name}},
        auth=auth,
    )
    if not dashboards:
        print(f"[ERROR] No dashboard found matching name {name!r}.")
        raise SystemExit(1)
    if len(dashboards) > 1:
        print(f"[ERROR] {len(dashboards)} dashboards match {name!r} -- use --id instead:")
        for d in dashboards:
            print(f"    id {d['dashboardid']}  {d['name']!r}")
        raise SystemExit(1)

    found = dashboards[0]
    print(f"[*] Resolved {name!r} -> dashboard id {found['dashboardid']}")
    return found["dashboardid"]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", required=True, help="Zabbix server IP/hostname")
    ap.add_argument("--user", default="Admin", help="Zabbix API username (default: Admin)")
    ap.add_argument("--scheme", default="http", choices=["http", "https"])
    target = ap.add_mutually_exclusive_group(required=True)
    target.add_argument("--name", help="Dashboard name (must match exactly one dashboard)")
    target.add_argument("--id", help="Dashboard ID (skips the name lookup)")
    ap.add_argument(
        "--out",
        help="Output file path (default: zbx_export_dashboards.json in the current dir)",
        default="zbx_export_dashboards.json",
    )
    args = ap.parse_args()

    url = discover_url(args.scheme, args.host)
    print(f"[*] API reachable at {url}")
    password = getpass.getpass(f"Zabbix API password for {args.user}: ")

    print(f"[*] Logging in to {url} as {args.user}...")
    auth = rpc(url, "user.login", {"username": args.user, "password": password})
    print("[+] Logged in.")

    dashboard_id = args.id if args.id else resolve_dashboard_id(url, auth, args.name)

    print(f"[*] Exporting dashboard id {dashboard_id}...")
    result = rpc(
        url,
        "configuration.export",
        {
            "format": "json",
            "prettyprint": True,
            "options": {"dashboards": [dashboard_id]},
        },
        auth=auth,
    )

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(result)

    print(f"[+] Wrote {len(result)} bytes to {args.out}")

    rpc(url, "user.logout", {}, auth=auth)
    print("[*] Logged out.")


if __name__ == "__main__":
    main()
