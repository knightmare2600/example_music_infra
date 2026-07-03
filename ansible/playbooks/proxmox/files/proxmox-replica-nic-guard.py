#!/usr/bin/env python3
"""
proxmox-replica-nic-guard.py

For every VM that has a Proxmox replication job, if the VM is currently STOPPED,
ensures that every NIC has link_down=1 so that a failover-start cannot accidentally
put the replica onto the live network.

Key safety rules:
  - Running / paused / migrating VMs are NEVER touched (they are the live source).
  - If any replication, vzdump, vzrestore, or migration task is actively running
    for a VM, that VM is SKIPPED for the whole run.
  - A live status re-check is done immediately before the config PUT to guard
    against a race where the VM started between our scan and our write.
  - Only link_down=1 is added to the NIC string; every other property is left
    exactly as-is (model, MAC, bridge, firewall settings, queues, etc.).
  - --dry-run prints what WOULD happen without writing anything.

Output: structured JSON (stdout + optional file for Zabbix pickup).
"""

import argparse
import json
import os
import socket
import sys
import uuid
from datetime import datetime, timezone

try:
    from proxmoxer import ProxmoxAPI
except ImportError:
    sys.exit("proxmoxer is not installed.  Run: pip3 install proxmoxer requests")

# ── Version ────────────────────────────────────────────────────────────────────
VERSION = "1.1.0"

# ── Constants ──────────────────────────────────────────────────────────────────

# Proxmox supports net0 … net31
NIC_KEYS = tuple(f"net{i}" for i in range(32))

# Task types whose presence means we skip the VM entirely this run
BLOCKING_TASK_TYPES = frozenset({"replication", "vzdump", "vzrestore", "migrate"})

# VM statuses that mean the VM is in active use – never touch these
SKIP_STATES = frozenset({"running", "paused", "migrating"})

# ── Credential defaults from environment ───────────────────────────────────────
# All of these are overridden by CLI flags; environment variables let you
# avoid putting secrets in the systemd unit file itself.

DEFAULT_HOST        = os.getenv("PROXMOX_HOST",        "localhost")
DEFAULT_USER        = os.getenv("PROXMOX_USER",        "root@pam")
DEFAULT_PASSWORD    = os.getenv("PROXMOX_PASSWORD",    "")
DEFAULT_TOKEN_NAME  = os.getenv("PROXMOX_TOKEN_NAME",  "")   # preferred over password
DEFAULT_TOKEN_VALUE = os.getenv("PROXMOX_TOKEN_VALUE", "")
DEFAULT_LOG_FILE    = os.getenv("NIC_GUARD_LOG",       "/var/log/proxmox-replica-nic-guard.json")
DEFAULT_VERIFY_SSL  = os.getenv("PROXMOX_VERIFY_SSL",  "false").lower() == "true"


# ═══════════════════════════════════════════════════════════════════════════════
# NIC string helpers
# The Proxmox NIC config format is:
#   net0: virtio=AA:BB:CC:DD:EE:FF,bridge=vmbr0[,option=value...]
# We treat the whole value as an opaque comma-separated list and only
# surgically add/replace the link_down token.
# ═══════════════════════════════════════════════════════════════════════════════

def nic_is_connected(nic_str: str) -> bool:
    """True when link_down=1 is absent (NIC will connect on VM start)."""
    return "link_down=1" not in nic_str


def nic_add_link_down(nic_str: str) -> str:
    """
    Return a new NIC config string with link_down=1 set.
    Any existing link_down=<X> token is stripped first so there are no duplicates.
    Every other token is carried through unchanged.
    """
    tokens = [t for t in nic_str.split(",") if not t.startswith("link_down")]
    tokens.append("link_down=1")
    return ",".join(tokens)


# ═══════════════════════════════════════════════════════════════════════════════
# Proxmox API helpers
# ═══════════════════════════════════════════════════════════════════════════════

def pve_connect(args) -> "ProxmoxAPI":
    kw: dict = dict(
        host=args.host,
        user=args.user,
        verify_ssl=args.verify_ssl,
        timeout=30,
    )
    if args.token_name and args.token_value:
        kw["token_name"]  = args.token_name
        kw["token_value"] = args.token_value
    else:
        if not args.password:
            sys.exit(
                "ERROR: no credentials supplied.  "
                "Provide --password or both --token-name and --token-value "
                "(or the equivalent PROXMOX_* environment variables)."
            )
        kw["password"] = args.password
    return ProxmoxAPI(**kw)


def fetch_cluster_vms(pve: "ProxmoxAPI") -> "dict[int, dict]":
    """
    Return {vmid: resource_record} for every QEMU VM visible in the cluster.
    The resource_record contains 'node', 'status', 'name', etc.
    """
    return {
        r["vmid"]: r
        for r in pve.cluster.resources.get(type="vm")
        if r.get("type") == "qemu"
    }


def fetch_replication_jobs(pve: "ProxmoxAPI") -> "dict[int, list[dict]]":
    """
    Return {vmid: [job, ...]} for all *enabled* replication jobs cluster-wide.
    A VM with any replication job is considered a 'replicated VM'.
    """
    jobs: "dict[int, list[dict]]" = {}
    for job in pve.cluster.replication.get():
        if not job.get("disable") and (vmid := job.get("vmid")):
            jobs.setdefault(int(vmid), []).append(job)
    return jobs


def vm_has_blocking_task(pve: "ProxmoxAPI", node: str, vmid: int) -> "tuple[bool, str]":
    """
    Return (True, reason) if a replication, backup, restore, or migration task
    is currently running for this VM on *node*.
    Returns (True, reason) on any API error – conservatively blocks.
    """
    try:
        tasks = pve.nodes(node).tasks.get(vmid=vmid, limit=50)
        for t in tasks:
            # Active tasks have endtime absent or 0
            if not t.get("endtime") and t.get("type") in BLOCKING_TASK_TYPES:
                return True, f"active {t['type']} task ({t.get('upid', 'unknown upid')})"
    except Exception as exc:
        return True, f"task query failed – skipping to be safe: {exc}"
    return False, ""


def fetch_vm_nics(pve: "ProxmoxAPI", node: str, vmid: int) -> "dict[str, str]":
    """Return {netN: nic_config_string} for all NICs present in the VM config."""
    cfg = pve.nodes(node).qemu(vmid).config.get()
    return {k: str(v) for k, v in cfg.items() if k in NIC_KEYS}


def vm_live_status(pve: "ProxmoxAPI", node: str, vmid: int) -> str:
    """Fetch the live (current) status of a VM.  Returns 'unknown' on error."""
    try:
        return pve.nodes(node).qemu(vmid).status.current.get().get("status", "unknown")
    except Exception:
        return "unknown"


def apply_link_down(
    pve: "ProxmoxAPI",
    node: str,
    vmid: int,
    nic_key: str,
    new_val: str,
    dry_run: bool,
) -> None:
    """Write the updated NIC config to Proxmox.  No-op when dry_run is True."""
    if not dry_run:
        pve.nodes(node).qemu(vmid).config.put(**{nic_key: new_val})


# ═══════════════════════════════════════════════════════════════════════════════
# Report helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _err(report: dict, context: str, msg: str) -> None:
    report["errors"].append({"context": context, "error": msg})
    report["summary"]["errors"] += 1


# ═══════════════════════════════════════════════════════════════════════════════
# Main guard logic
# ═══════════════════════════════════════════════════════════════════════════════

def build_report(args) -> dict:
    """
    Connect, find replicated VMs, check / fix NICs, and return the full report dict.
    All actions are non-destructive to VM properties other than link_down.
    """
    report: dict = {
        "schema_version":  "1",
        "script_version":  VERSION,
        "timestamp":       datetime.now(timezone.utc).isoformat(),
        "run_id":          str(uuid.uuid4()),
        "hostname":        socket.gethostname(),
        "dry_run":         int(args.dry_run),   # 0/1 for easy Zabbix trigger math
        "summary": {
            "replicated_vm_count":       0,
            "vms_skipped_running":       0,   # VM was live – not a replica right now
            "vms_skipped_busy":          0,   # active replication/backup task running
            "vms_skipped_no_node":       0,   # VM not found in cluster resources
            "vms_checked":               0,
            # nics_connected_on_stopped is the PRIMARY Zabbix alert metric:
            # how many NICs were found unguarded on stopped replicated VMs this run.
            "nics_connected_on_stopped": 0,
            "nics_already_safe":         0,
            "nics_disconnected":         0,   # successfully set link_down=1
            "nics_fix_failed":           0,   # found connected but could NOT fix
            "errors":                    0,
        },
        "vms":    [],
        "errors": [],
    }

    # ── Connect ────────────────────────────────────────────────────────────────
    try:
        pve = pve_connect(args)
    except Exception as exc:
        _err(report, "connect", str(exc))
        return report

    # ── Cluster-wide data ──────────────────────────────────────────────────────
    try:
        cluster_vms = fetch_cluster_vms(pve)
    except Exception as exc:
        _err(report, "cluster.resources", str(exc))
        return report

    try:
        repl_jobs = fetch_replication_jobs(pve)
    except Exception as exc:
        _err(report, "cluster.replication", str(exc))
        return report

    report["summary"]["replicated_vm_count"] = len(repl_jobs)

    # ── Per-VM loop ────────────────────────────────────────────────────────────
    for vmid, jobs in sorted(repl_jobs.items()):
        vm     = cluster_vms.get(vmid, {})
        node   = vm.get("node",   "")
        name   = vm.get("name",   f"vm{vmid}")
        status = vm.get("status", "unknown")

        vm_entry: dict = {
            "vmid":       vmid,
            "name":       name,
            "node":       node,
            "dest_nodes": sorted({j["target"] for j in jobs if j.get("target")}),
            "status":     status,
            "skipped":    None,
            "nics":       [],
        }

        # ── Guard 1: VM must be in the cluster resource list ───────────────────
        if not node:
            vm_entry["skipped"] = "VM not found in cluster resources (deleted but job remains?)"
            report["summary"]["vms_skipped_no_node"] += 1
            report["vms"].append(vm_entry)
            continue

        # ── Guard 2: Do not touch running / paused / migrating VMs ────────────
        # These are the *live source* copies, not replicas waiting for failover.
        if status in SKIP_STATES:
            vm_entry["skipped"] = f"vm is {status} — live source copy, not a waiting replica"
            report["summary"]["vms_skipped_running"] += 1
            report["vms"].append(vm_entry)
            continue

        # ── Guard 3: Skip if replication / backup / restore / migration is active
        busy, busy_reason = vm_has_blocking_task(pve, node, vmid)
        if busy:
            vm_entry["skipped"] = busy_reason
            report["summary"]["vms_skipped_busy"] += 1
            report["vms"].append(vm_entry)
            continue

        # ── Guard 4: Re-read live status immediately before writing anything ───
        # Catches the race where the VM started between our scan and our PUT.
        current_status = vm_live_status(pve, node, vmid)
        if current_status in SKIP_STATES:
            vm_entry["skipped"] = (
                f"vm transitioned to '{current_status}' between scan and write — aborted"
            )
            report["summary"]["vms_skipped_running"] += 1
            report["vms"].append(vm_entry)
            continue

        report["summary"]["vms_checked"] += 1

        # ── Read NIC config ────────────────────────────────────────────────────
        try:
            nics = fetch_vm_nics(pve, node, vmid)
        except Exception as exc:
            vm_entry["skipped"] = f"config read error: {exc}"
            _err(report, f"vm{vmid}.config.get", str(exc))
            report["vms"].append(vm_entry)
            continue

        # ── Check / fix each NIC ───────────────────────────────────────────────
        for nic_key in sorted(nics):
            nic_val   = nics[nic_key]
            connected = nic_is_connected(nic_val)

            nic_entry: dict = {
                "key":           nic_key,
                "original":      nic_val,
                "was_connected": connected,
                "action":        "already_safe",
            }

            if connected:
                report["summary"]["nics_connected_on_stopped"] += 1
                new_val = nic_add_link_down(nic_val)
                try:
                    apply_link_down(pve, node, vmid, nic_key, new_val, args.dry_run)
                    if args.dry_run:
                        nic_entry["action"]   = "would_disconnect"
                        nic_entry["proposed"] = new_val
                    else:
                        nic_entry["action"]    = "disconnected"
                        nic_entry["new_value"] = new_val
                        report["summary"]["nics_disconnected"] += 1
                except Exception as exc:
                    nic_entry["action"] = "error"
                    nic_entry["error"]  = str(exc)
                    report["summary"]["nics_fix_failed"] += 1
                    _err(report, f"vm{vmid}.{nic_key}.put", str(exc))
            else:
                report["summary"]["nics_already_safe"] += 1

            vm_entry["nics"].append(nic_entry)

        report["vms"].append(vm_entry)

    return report


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def parse_args():
    p = argparse.ArgumentParser(
        description=(
            "Ensure stopped replicated Proxmox VMs have link_down=1 on every NIC. "
            "Skips running VMs and VMs with active replication/backup tasks."
        ),
        epilog=(
            "Credentials via environment variables (can be set in systemd EnvironmentFile):\n"
            "  PROXMOX_HOST          PVE host or cluster VIP\n"
            "  PROXMOX_USER          API user  (default: root@pam)\n"
            "  PROXMOX_TOKEN_NAME    API token name  (preferred over password)\n"
            "  PROXMOX_TOKEN_VALUE   API token secret\n"
            "  PROXMOX_PASSWORD      Password  (only if not using token)\n"
            "  NIC_GUARD_LOG         JSON output file  (for Zabbix pickup)\n"
            "  PROXMOX_VERIFY_SSL    true/false  (default: false)\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--host",        default=DEFAULT_HOST,        help="Proxmox host/IP")
    p.add_argument("--user",        default=DEFAULT_USER,        help="API user (e.g. root@pam)")
    p.add_argument("--password",    default=DEFAULT_PASSWORD,    help="Password (prefer --token-*)")
    p.add_argument("--token-name",  default=DEFAULT_TOKEN_NAME,  dest="token_name",  help="API token name")
    p.add_argument("--token-value", default=DEFAULT_TOKEN_VALUE, dest="token_value", help="API token secret")
    p.add_argument("--verify-ssl",  action="store_true", default=DEFAULT_VERIFY_SSL, dest="verify_ssl")
    p.add_argument("--dry-run",     action="store_true", dest="dry_run",
                   help="Scan and report; do NOT write any changes to Proxmox")
    p.add_argument("--log-file",    default=DEFAULT_LOG_FILE,    dest="log_file",
                   help="Write JSON report here (for Zabbix vfs.file.contents pickup)")
    p.add_argument("--quiet",       action="store_true",
                   help="Suppress stdout (log file still written if --log-file is set)")
    return p.parse_args()


def main() -> None:
    args   = parse_args()
    report = build_report(args)

    json_out = json.dumps(report, indent=2)

    if not args.quiet:
        print(json_out)

    if args.log_file:
        try:
            log_dir = os.path.dirname(args.log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            with open(args.log_file, "w") as fh:
                fh.write(json_out + "\n")
            # Zabbix agent (zabbix user) needs read access
            os.chmod(args.log_file, 0o644)
        except OSError as exc:
            print(f"WARNING: cannot write log file {args.log_file}: {exc}", file=sys.stderr)

    # Non-zero exit if any API errors occurred (lets systemd mark the run as failed)
    sys.exit(1 if report["summary"]["errors"] > 0 else 0)


if __name__ == "__main__":
    main()
