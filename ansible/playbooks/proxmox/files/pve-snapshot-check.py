#!/usr/bin/env python3
# =============================================================================
# Proxmox VE Snapshot Check
#
# Version History:
#   1.0.0 - 2026-05-27 - Initial release
# =============================================================================

import json
import subprocess
import sys
import os
from datetime import datetime, timezone

LOG_FILE = "/tmp/pve-snapshot-check.json"

CRITICAL_AGE_DAYS       = 7
CRITICAL_MULTI_AGE_DAYS = 5
HIGH_MULTI_COUNT        = 2

SEVERITY_RANK = {"OK": 0, "WARNING": 1, "HIGH": 2, "CRITICAL": 3}


def pvesh_get(path):
  try:
    result = subprocess.run(
      ["pvesh", "get", path, "--output-format", "json"],
      capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
      print(f"[ERROR] pvesh get {path} failed (rc={result.returncode}): {result.stderr.strip()}", file=sys.stderr)
      return None
    return json.loads(result.stdout)
  except subprocess.TimeoutExpired:
    print(f"[ERROR] pvesh get {path} timed out", file=sys.stderr)
    return None
  except json.JSONDecodeError as exc:
    print(f"[ERROR] pvesh get {path} returned non-JSON: {exc}", file=sys.stderr)
    return None
  except FileNotFoundError:
    print("[ERROR] pvesh not found — is this a Proxmox VE node?", file=sys.stderr)
    sys.exit(1)


def get_node_name():
  return subprocess.run(["hostname", "-s"], capture_output=True, text=True).stdout.strip()


def build_snapshot_list(raw_snaps, now_ts):
  snaps = {}
  for s in raw_snaps:
    if s.get("name") == "current":
      continue
    name = s.get("name", "unknown")
    snaptime = s.get("snaptime", 0)
    age_days = round((now_ts - snaptime) / 86400, 1) if snaptime else 0.0
    snaps[name] = {
      "name":        name,
      "description": s.get("description", "").strip(),
      "age_days":    age_days,
      "parent":      s.get("parent", None),
      "children":    [],
    }
  for name, snap in snaps.items():
    parent = snap["parent"]
    if parent and parent in snaps:
      snaps[parent]["children"].append(name)
  return sorted(snaps.values(), key=lambda x: x["age_days"], reverse=True)


def calculate_severity(snapshots):
  if not snapshots:
    return "OK"
  count   = len(snapshots)
  max_age = max(s["age_days"] for s in snapshots)
  if max_age >= CRITICAL_AGE_DAYS:
    return "CRITICAL"
  if count >= HIGH_MULTI_COUNT and max_age >= CRITICAL_MULTI_AGE_DAYS:
    return "CRITICAL"
  if count >= HIGH_MULTI_COUNT:
    return "HIGH"
  return "WARNING"


def check_guests(node, guest_type, now_ts):
  guests_raw = pvesh_get(f"/nodes/{node}/{guest_type}")
  if guests_raw is None:
    print(f"[WARN] Could not enumerate {guest_type} guests on {node}", file=sys.stderr)
    return []
  results = []
  for guest in sorted(guests_raw, key=lambda x: x.get("vmid", 0)):
    vmid   = guest.get("vmid")
    name   = guest.get("name", f"{guest_type}-{vmid}")
    status = guest.get("status", "unknown")
    snaps_raw = pvesh_get(f"/nodes/{node}/{guest_type}/{vmid}/snapshot")
    if snaps_raw is None:
      results.append({
        "vmid": vmid, "name": name, "type": guest_type, "status": status,
        "severity": "UNKNOWN", "severity_int": -1,
        "snapshot_count": -1, "oldest_snapshot_days": -1, "newest_snapshot_days": -1,
        "snapshots": [], "error": "pvesh snapshot query failed",
      })
      continue
    snapshots = build_snapshot_list(snaps_raw, now_ts)
    severity  = calculate_severity(snapshots)
    oldest = max((s["age_days"] for s in snapshots), default=0.0)
    newest = min((s["age_days"] for s in snapshots), default=0.0)
    results.append({
      "vmid": vmid, "name": name, "type": guest_type, "status": status,
      "severity": severity, "severity_int": SEVERITY_RANK.get(severity, -1),
      "snapshot_count": len(snapshots),
      "oldest_snapshot_days": oldest, "newest_snapshot_days": newest,
      "snapshots": snapshots,
    })
  return results


def build_summary(vms, lxcs):
  all_guests = vms + lxcs
  worst_int = max((g["severity_int"] for g in all_guests if g["severity_int"] >= 0), default=0)
  worst     = {v: k for k, v in SEVERITY_RANK.items()}.get(worst_int, "OK")
  return {
    "total_vms_checked":  len(vms),
    "total_lxc_checked":  len(lxcs),
    "vms_with_snapshots": sum(1 for g in vms  if g["snapshot_count"] > 0),
    "lxc_with_snapshots": sum(1 for g in lxcs if g["snapshot_count"] > 0),
    "critical_count":     sum(1 for g in all_guests if g["severity"] == "CRITICAL"),
    "high_count":         sum(1 for g in all_guests if g["severity"] == "HIGH"),
    "warning_count":      sum(1 for g in all_guests if g["severity"] == "WARNING"),
    "unknown_count":      sum(1 for g in all_guests if g["severity"] == "UNKNOWN"),
    "worst_severity":     worst,
    "worst_severity_int": worst_int,
  }


def main():
  now_ts  = datetime.now(timezone.utc).timestamp()
  now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
  node    = get_node_name()
  print(f"[INFO] pve-snapshot-check starting on {node}", file=sys.stderr)
  vms  = check_guests(node, "qemu", now_ts)
  lxcs = check_guests(node, "lxc",  now_ts)
  summary = build_summary(vms, lxcs)
  report = {
    "generated_iso":  now_iso,
    "generated_unix": int(now_ts),
    "hostname":       node,
    "summary":        summary,
    "vms":            vms,
    "lxc":            lxcs,
  }
  try:
    with open(LOG_FILE, "w", encoding="utf-8") as fh:
      json.dump(report, fh, indent=2)
    os.chmod(LOG_FILE, 0o644)
  except OSError as exc:
    print(f"[ERROR] Could not write {LOG_FILE}: {exc}", file=sys.stderr)
    sys.exit(1)
  print(
    f"[INFO] Done — {summary['total_vms_checked']} VMs, "
    f"{summary['total_lxc_checked']} LXC checked. "
    f"Worst severity: {summary['worst_severity']}. "
    f"Report: {LOG_FILE}",
    file=sys.stderr,
  )


if __name__ == "__main__":
  main()
