#!/usr/bin/env python3
# =============================================================================
# Proxmox VE — ZFS VM Placement Audit
#
# Enumerates all QEMU VMs and LXC containers on this node and reports which
# ZFS pool each disk resides on.  Flags any disk whose pool matches one of
# the excluded pool glob patterns (case-insensitive by default).
#
# The system/boot pool (the one mounting /) is ALWAYS treated as excluded
# regardless of the --excluded-pools argument — no hardcoding required.
#
# Writes a JSON report to /tmp/zfs-vm-audit.json on every run.
# File is overwritten, not appended.  Volatile between reboots (/tmp).
#
# Uses pvesh and standard CLI tools as root — no API token required.
#
# Excluded pool patterns support shell globs (fnmatch, case-insensitive):
#   pbs*     → pbs, PBS, pbs-fast, PBS-BACKUPS
#   Backup*  → Backups, backup-pool, BACKUP2
#   rpool    → rpool exactly
#
# Severity per VM/CT:
#   FLAGGED  — one or more disks reside on an excluded pool
#   OK       — all disks on acceptable pools
#   UNKNOWN  — pvesh query failed for this guest
#
# Version History:
#   1.0.0 - 2026-06-01 - Initial release (ported from shell script; systemd
#                        timer + vfs.file.contents pattern, no UserParameter)
# =============================================================================

import fnmatch
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

# =============================================================================
# Configuration
# =============================================================================

OUTPUT_FILE = "/tmp/zfs-vm-audit.json"

# Default excluded pool glob patterns (case-insensitive).
# The system/boot pool is always appended at runtime regardless of this list.
# Override via --excluded-pools on the command line (comma-separated globs).
DEFAULT_EXCLUDED_PATTERNS = [
  "rpool",
  "pve*",
  "Backups*",
  "PBS*",
  "pbs*",
  "backup*",
]

# =============================================================================
# Argument parsing (minimal — no argparse dependency)
# =============================================================================

def parse_args():
  excluded_override = None
  case_sensitive = False
  args = sys.argv[1:]
  i = 0
  while i < len(args):
    if args[i] == "--excluded-pools" and i + 1 < len(args):
      excluded_override = [p.strip() for p in args[i + 1].split(",") if p.strip()]
      i += 2
    elif args[i] == "--case-sensitive":
      case_sensitive = True
      i += 1
    else:
      print(f"[WARN] Unknown argument ignored: {args[i]}", file=sys.stderr)
      i += 1
  return excluded_override, case_sensitive

# =============================================================================
# System pool detection
# =============================================================================

def find_system_pool():
  """
  Returns the name of the ZFS pool that mounts /.
  Works regardless of pool name (rpool, pve, tank, etc.).
  Returns empty string if it cannot be determined.
  """
  try:
    pools_raw = subprocess.run(
      ["zpool", "list", "-H", "-o", "name"],
      capture_output=True, text=True, timeout=15,
    )
    for pool in pools_raw.stdout.splitlines():
      pool = pool.strip()
      if not pool:
        continue
      ds_raw = subprocess.run(
        ["zfs", "list", "-H", "-o", "name,mountpoint", "-r", pool],
        capture_output=True, text=True, timeout=15,
      )
      for line in ds_raw.stdout.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == "/":
          return pool
  except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
    print(f"[WARN] Could not detect system pool: {exc}", file=sys.stderr)
  return ""

# =============================================================================
# Storage map — storage_id -> pool name
# =============================================================================

def build_storage_map():
  """
  Queries pvesm to build a dict of storage_id -> ZFS pool name.
  Covers zfspool-type storages and dir-type storages mounted on ZFS datasets.
  Returns an empty dict if pvesm is unavailable.
  """
  storage_map = {}

  try:
    status_raw = subprocess.run(
      ["pvesm", "status"],
      capture_output=True, text=True, timeout=15,
    )
  except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
    print(f"[WARN] pvesm status failed: {exc}", file=sys.stderr)
    return storage_map

  for line in status_raw.stdout.splitlines()[1:]:   # skip header
    parts = line.split()
    if len(parts) < 2:
      continue
    sid, stype = parts[0], parts[1]

    if stype == "zfspool":
      try:
        cfg_raw = subprocess.run(
          ["pvesm", "config", sid],
          capture_output=True, text=True, timeout=10,
        )
        for cfg_line in cfg_raw.stdout.splitlines():
          if cfg_line.startswith("pool"):
            pool = cfg_line.split(":", 1)[-1].strip()
            if pool:
              storage_map[sid] = pool
            break
      except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    elif stype == "dir":
      try:
        cfg_raw = subprocess.run(
          ["pvesm", "config", sid],
          capture_output=True, text=True, timeout=10,
        )
        fspath = ""
        for cfg_line in cfg_raw.stdout.splitlines():
          if cfg_line.startswith("path"):
            fspath = cfg_line.split(":", 1)[-1].strip()
            break
        if fspath and os.path.isdir(fspath):
          df_raw = subprocess.run(
            ["df", "--output=source", fspath],
            capture_output=True, text=True, timeout=10,
          )
          lines = df_raw.stdout.splitlines()
          if len(lines) >= 2:
            source = lines[1].strip()
            # Confirm it is a ZFS dataset
            chk = subprocess.run(
              ["zfs", "list", source],
              capture_output=True, text=True, timeout=10,
            )
            if chk.returncode == 0:
              storage_map[sid] = source.split("/")[0]
      except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

  return storage_map

# =============================================================================
# Disk → pool resolution
# =============================================================================

def disk_spec_to_pool(spec, storage_map):
  """
  Resolves a 'storage_id:volume' disk spec to a pool name.
  Falls back to /dev/zvol inspection if the storage_id is not in the map.
  Returns 'unknown' if resolution fails.
  """
  if ":" not in spec:
    return "unknown"   # passthrough device or non-storage path

  sid, volume = spec.split(":", 1)

  if sid in storage_map:
    return storage_map[sid]

  zvol_path = f"/dev/zvol/{volume}"
  if os.path.exists(zvol_path):
    return volume.split("/")[0]

  return "unknown"

# =============================================================================
# Glob matching
# =============================================================================

def pool_is_excluded(pool_name, patterns, case_sensitive):
  if pool_name in ("unknown", ""):
    return False
  test = pool_name if case_sensitive else pool_name.lower()
  pats = patterns if case_sensitive else [p.lower() for p in patterns]
  return any(fnmatch.fnmatch(test, pat) for pat in pats)

# =============================================================================
# pvesh helpers
# =============================================================================

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
  result = subprocess.run(["hostname", "-s"], capture_output=True, text=True)
  return result.stdout.strip()

# =============================================================================
# Disk line parsing
# =============================================================================

# Config key prefixes that represent disk attachments
QEMU_DISK_PREFIXES = ("scsi", "virtio", "ide", "sata", "efidisk", "tpmstate")
LXC_DISK_PREFIXES  = ("rootfs", "mp")


def extract_disk_specs(config_lines, guest_type):
  """
  Parses pvesh config output lines and returns a list of
  {'key': str, 'spec': str} for each disk attachment.
  Skips passthrough devices (no colon in spec).
  """
  disks = []
  prefixes = QEMU_DISK_PREFIXES if guest_type == "qemu" else LXC_DISK_PREFIXES

  for item in config_lines:
    key = item.get("key", "")
    value = item.get("value", "")

    # Check if the key looks like a disk attachment
    if not any(key.startswith(pfx) for pfx in prefixes):
      continue
    # The value is comma-delimited; first field is storage:volume
    spec = value.split(",")[0].strip()
    if ":" not in spec:
      continue   # passthrough or bare path
    disks.append({"key": key, "spec": spec})

  return disks

# =============================================================================
# Guest enumeration
# =============================================================================

def check_guests(node, guest_type, storage_map, excl_patterns, case_sensitive):
  guests_raw = pvesh_get(f"/nodes/{node}/{guest_type}")
  if guests_raw is None:
    print(f"[WARN] Could not enumerate {guest_type} guests on {node}", file=sys.stderr)
    return []

  results = []

  for guest in sorted(guests_raw, key=lambda x: x.get("vmid", 0)):
    vmid   = guest.get("vmid")
    name   = guest.get("name", f"{guest_type}-{vmid}")
    status = guest.get("status", "unknown")

    # pvesh returns config as a list of {key, value} objects
    config_raw = pvesh_get(f"/nodes/{node}/{guest_type}/{vmid}/config")
    if config_raw is None:
      results.append({
        "vmid":          vmid,
        "name":          name,
        "type":          guest_type,
        "status":        status,
        "severity":      "UNKNOWN",
        "severity_int":  -1,
        "flagged":       False,
        "flagged_disks": [],
        "all_disks":     [],
        "error":         "pvesh config query failed",
      })
      continue

    # pvesh /config can return a dict or a list depending on PVE version
    if isinstance(config_raw, dict):
      config_lines = [{"key": k, "value": str(v)} for k, v in config_raw.items()]
    else:
      config_lines = config_raw   # already a list of {key, value}

    disk_specs = extract_disk_specs(config_lines, guest_type)

    all_disks     = []
    flagged_disks = []

    for d in disk_specs:
      pool = disk_spec_to_pool(d["spec"], storage_map)
      excluded = pool_is_excluded(pool, excl_patterns, case_sensitive)
      disk_entry = {
        "disk":          d["key"],
        "spec":          d["spec"],
        "pool":          pool,
        "excluded_pool": excluded,
      }
      all_disks.append(disk_entry)
      if excluded:
        flagged_disks.append({"disk": d["key"], "pool": pool})

    flagged   = len(flagged_disks) > 0
    severity  = "FLAGGED" if flagged else "OK"
    sev_int   = 1 if flagged else 0

    results.append({
      "vmid":          vmid,
      "name":          name,
      "type":          guest_type,
      "status":        status,
      "severity":      severity,
      "severity_int":  sev_int,
      "flagged":       flagged,
      "flagged_disks": flagged_disks,
      "all_disks":     all_disks,
    })

  return results

# =============================================================================
# Summary
# =============================================================================

def build_summary(vms, lxcs, excl_patterns, system_pool):
  all_guests = vms + lxcs
  flagged    = [g for g in all_guests if g["flagged"]]

  return {
    "total_vms_checked":  len(vms),
    "total_lxc_checked":  len(lxcs),
    "total_checked":      len(all_guests),
    "flagged_count":      len(flagged),
    "unknown_count":      sum(1 for g in all_guests if g["severity"] == "UNKNOWN"),
    "flagged_vmids":      [g["vmid"] for g in flagged],
    "flagged_detail": [
      {
        "vmid":          g["vmid"],
        "name":          g["name"],
        "flagged_disks": g["flagged_disks"],
      }
      for g in flagged
    ],
    "system_pool":        system_pool,
    "excluded_patterns":  excl_patterns,
  }

# =============================================================================
# Main
# =============================================================================

def main():
  excluded_override, case_sensitive = parse_args()

  system_pool = find_system_pool()
  print(f"[INFO] System/boot pool detected as: '{system_pool or '(none detected)'}'", file=sys.stderr)

  # Build final excluded patterns: system pool always first, then user patterns
  base_patterns = DEFAULT_EXCLUDED_PATTERNS if excluded_override is None else excluded_override
  excl_patterns = list(dict.fromkeys(
    ([system_pool] if system_pool else []) + base_patterns
  ))
  print(f"[INFO] Excluded pool patterns: {excl_patterns}", file=sys.stderr)

  now_ts  = datetime.now(timezone.utc).timestamp()
  now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
  node    = get_node_name()

  print(f"[INFO] zfs-vm-audit starting on {node}", file=sys.stderr)

  storage_map = build_storage_map()
  print(f"[INFO] Storage map: {storage_map}", file=sys.stderr)

  vms  = check_guests(node, "qemu", storage_map, excl_patterns, case_sensitive)
  lxcs = check_guests(node, "lxc",  storage_map, excl_patterns, case_sensitive)

  summary = build_summary(vms, lxcs, excl_patterns, system_pool)

  report = {
    "generated_iso":  now_iso,
    "generated_unix": int(now_ts),
    "hostname":       node,
    "case_sensitive": case_sensitive,
    "summary":        summary,
    "vms":            vms,
    "lxc":            lxcs,
  }

  try:
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
      json.dump(report, fh, indent=2)
    os.chmod(OUTPUT_FILE, 0o644)
  except OSError as exc:
    print(f"[ERROR] Could not write {OUTPUT_FILE}: {exc}", file=sys.stderr)
    sys.exit(1)

  print(
    f"[INFO] Done — {summary['total_vms_checked']} VMs, "
    f"{summary['total_lxc_checked']} LXC checked. "
    f"Flagged: {summary['flagged_count']}. "
    f"Report: {OUTPUT_FILE}",
    file=sys.stderr,
  )


if __name__ == "__main__":
  main()
