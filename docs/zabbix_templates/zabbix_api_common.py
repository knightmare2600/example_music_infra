#!/usr/bin/env python3
"""
docs/zabbix_templates/zabbix_api_common.py
Example Music Limited — Shared JSON-RPC helpers for the Zabbix API scripts in this directory

=============================================================================
Extracted from import_template.py (2026-10-24) when export_dashboard.py needed the exact
same auth/API-reachability logic -- rather than duplicate rpc()/discover_url() a second
time, same "don't hand-roll, sweep fully" discipline this repo applies everywhere else.
No behaviour change to import_template.py's own logic, just moved.

Stdlib only (urllib.request/json) -- no pip install needed.

Changelog:
    2026-10-25  Initial file. Extracted rpc()/discover_url() out of import_template.py
                verbatim, for export_dashboard.py to share.
=============================================================================
"""

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


def discover_url(scheme, host):
    # 2026-10-24: the vhost is mid-migration from Alias-mounted /zabbix/api_jsonrpc.php
    # to root-mounted /api_jsonrpc.php (playbooks/zabbix/templates/zabbix.vhost.conf.j2)
    # -- caters for both, root-mounted path tried first since that's the new default,
    # falling back to the old alias path for any box that hasn't had zabbix_server.yml
    # re-run with the new template yet. apiinfo.version needs no auth, so a real
    # JSON-RPC reply (even an error one) proves the path is live; only a 404 means
    # "wrong path, try the other one".
    candidates = [
        f"{scheme}://{host}/api_jsonrpc.php",
        f"{scheme}://{host}/zabbix/api_jsonrpc.php",
    ]
    probe = json.dumps(
        {"jsonrpc": "2.0", "method": "apiinfo.version", "params": {}, "id": 0}
    ).encode("utf-8")

    for url in candidates:
        req = urllib.request.Request(
            url,
            data=probe,
            headers={"Content-Type": "application/json-rpc"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
            return url
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            return url
        except urllib.error.URLError:
            continue

    print(
        f"[ERROR] Neither {candidates[0]} nor {candidates[1]} answered -- "
        "is the vhost up and reachable from here?"
    )
    sys.exit(1)
