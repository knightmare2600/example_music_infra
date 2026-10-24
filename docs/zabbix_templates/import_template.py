#!/usr/bin/env python3
"""
docs/zabbix_templates/import_template.py
Example Music Limited — Import a Zabbix template export file via the real JSON-RPC API

=============================================================================
First real `configuration.import` attempt against a live Zabbix 7.0 instance for any
of the 8 companion templates this repo has built so far -- see this directory's own
README.md ("First real configuration.import attempt is the actual test"). No template
has ever been test-imported before this script exists.

Stdlib only (urllib.request/json) -- no pip install needed, matches this repo's own
"no pip installs, ask to apt-install" convention; nothing here needs a package that
isn't already part of a normal Python 3 install.

Auth: prompts for the Admin password (getpass, never a CLI arg/env var that could sit
in shell history) and calls user.login itself -- doesn't read KeePass directly (this
script runs from wherever Robert has network access to the Zabbix API, not necessarily
the control node with KeePass set up). The real Admin password is already filed in
KeePass at Infrastructure/CLD/EXAZABCLD001-zabbix-admin as of the 2026-10-24
zabbix_server.yml run -- copy it from there.

Rules: createMissing/updateExisting true, deleteMissing FALSE everywhere, always --
this estate's own standing "never auto-delete, that's a human decision" convention
([[feedback_security_posture_is_roberts_call]], same principle applied here). If a
later run genuinely needs to prune something, do it by hand in the UI, not by flipping
this script's defaults.

Usage:
    python3 import_template.py --host 192.168.69.13 docs/zabbix_templates/zabbix_template_linuxtools.json
    python3 import_template.py --host 192.168.69.13 --user Admin *.json   # multiple files, one call each

=============================================================================
Changelog:
    2026-10-24  Initial script. Robert's ask: test-import the 8 companion templates
                built so far against the real, now-confirmed-working EXAZABCLD001.
=============================================================================
"""

import argparse
import getpass
import json
import sys
import urllib.error
import urllib.request


def rpc(url, method, params, auth=None, req_id=1):
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": req_id,
    }
    if auth is not None:
        payload["auth"] = auth

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json-rpc"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"[ERROR] HTTP {e.code} calling {method}: {e.read().decode('utf-8', 'replace')}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"[ERROR] Could not reach {url}: {e}")
        sys.exit(1)

    if "error" in body:
        err = body["error"]
        print(f"[ERROR] {method} failed: {err.get('message')} -- {err.get('data')}")
        sys.exit(1)

    return body["result"]


def detect_format(path):
    if path.endswith(".json"):
        return "json"
    if path.endswith(".yaml") or path.endswith(".yml"):
        return "yaml"
    if path.endswith(".xml"):
        return "xml"
    print(f"[ERROR] Can't tell the export format from the filename: {path}")
    sys.exit(1)


def import_rules():
    # createMissing/updateExisting everywhere that supports it; deleteMissing: false
    # everywhere, always -- never auto-delete, that's Robert's call, not this script's.
    # template_groups has no updateExisting/deleteMissing concept (groups are just
    # named containers) -- createMissing only, matching the real export's own
    # top-level "template_groups" key (confirmed against the real file, not guessed).
    both = {"createMissing": True, "updateExisting": True}
    full = {"createMissing": True, "updateExisting": True, "deleteMissing": False}
    return {
        "template_groups": {"createMissing": True},
        "host_groups": {"createMissing": True},
        "templates": both,
        "templateDashboards": full,
        "valueMaps": full,
        "templateLinkage": {"createMissing": True, "deleteMissing": False},
        "items": full,
        "discoveryRules": full,
        "triggers": full,
        "graphs": full,
        "httptests": full,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", required=True, help="Zabbix server IP/hostname")
    ap.add_argument("--user", default="Admin", help="Zabbix API username (default: Admin)")
    ap.add_argument("--scheme", default="http", choices=["http", "https"])
    ap.add_argument("files", nargs="+", help="Template export file(s) to import")
    args = ap.parse_args()

    url = f"{args.scheme}://{args.host}/api_jsonrpc.php"
    password = getpass.getpass(f"Zabbix API password for {args.user}: ")

    print(f"[*] Logging in to {url} as {args.user}...")
    auth = rpc(url, "user.login", {"username": args.user, "password": password})
    print("[+] Logged in.")

    rules = import_rules()

    for path in args.files:
        fmt = detect_format(path)
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()

        print(f"[*] Importing {path} ({fmt}, {len(source)} bytes)...")
        rpc(
            url,
            "configuration.import",
            {"format": fmt, "source": source, "rules": rules},
            auth=auth,
        )
        print(f"[+] {path} imported successfully.")

    rpc(url, "user.logout", {}, auth=auth)
    print("[*] Logged out.")


if __name__ == "__main__":
    main()
