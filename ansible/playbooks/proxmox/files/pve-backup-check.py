#!/usr/bin/env python3
# =============================================================================
# Proxmox VE Backup Check
#
# Checks all QEMU VMs and LXC containers on this node for backup status,
# scored against each guest's OWN expected backup cadence (pulled from the
# cluster's backup job definitions), not a single fleet-wide threshold.
#
# Writes a JSON report to /tmp/pve-backup-check.json on every run
# (file is overwritten, not appended — it is volatile between reboots).
#
# Uses pvesh locally as root — no API token or credential management required.
#
# Data sources per run:
#   /cluster/backup                             — job definitions (schedule, vmid,
#                                                 all, pool, exclude, enabled, storage)
#   /nodes/{node}/storage                       — enumerate 'backup' content storages
#   /nodes/{node}/storage/{id}/content          — per-storage backup listings incl.
#                                                 PBS verification state
#   /nodes/{node}/qemu, /nodes/{node}/lxc       — every guest on this node
#   /nodes/{node}/tasks (typefilter=vzdump)     — recent job task history
#   /pools/{name}                               — pool membership (only if a job
#                                                 targets a pool)
#
# Cadence-aware thresholds — computed per guest based on the tightest matching
# job schedule (via `systemd-analyze calendar`):
#   warning_at_hours  = interval + max(6h, interval * 0.10)
#   critical_at_hours = max(interval * 2, warning_at_hours + 6h)
#
# Severity per VM/CT:
#   CRITICAL  — running guest not covered by ANY backup job
#   CRITICAL  — running guest with no backup found on disk
#   CRITICAL  — most recent backup age >= critical_at_hours
#   HIGH      — stopped guest not covered by any backup job (often intentional
#               — decommissioned, archived, spare — but still surfaced)
#   HIGH      — stopped guest with no backup on disk
#   HIGH      — most recent backup verification == 'failed'
#   WARNING   — most recent backup age >= warning_at_hours (but < critical)
#   WARNING   — most recent backup verification unknown/pending on a PBS storage
#   UNKNOWN   — guest is in a job, but no matching job schedule could be
#               parsed (cadence unknown) and nothing worse applies
#   OK        — recent backup present, verified (or verification n/a)
#   OK        — guest is a template (excluded from scoring, still listed)
#
# Every guest also carries a human-readable `reason` string explaining its
# severity, intended for Zabbix operational data.
#
# NOTES:
#   - Guests matched to jobs whose schedule can't be parsed fall back to
#     FALLBACK_* thresholds and are flagged with a `schedule_parse_error` field.
#   - The task history is filtered to only vzdump tasks and capped by
#     RECENT_TASK_LIMIT. A separate `recent_vzdump_failures` list is included
#     for cheap Zabbix trigger access. A single vzdump task can cover multiple
#     VMs and PVE doesn't give clean per-guest status without parsing the task
#     log, so tasks are surfaced at the job level, not force-mapped to guests.
#   - This does NOT hit the PBS API directly — it reads backup existence off
#     the PVE storage content listing, which already surfaces PBS verification
#     state without needing separate PBS credentials.
#
# Version History:
#   1.0.0 - 2026-07-31 - Initial release
#   1.1.0 - 2026-07-31 - Cadence-aware thresholds from /cluster/backup;
#                        unmanaged-guest detection; RECENT_TASK_LIMIT raised to
#                        60; separate recent_vzdump_failures list; pool
#                        membership resolution.
#   1.1.1 - 2026-07-31 - Fast-path schedule classifier for named shortcuts
#                        (daily/monthly/weekly/hourly), bare HH:MM (daily),
#                        day-of-week (weekly), *-*-DD (monthly); relaxed
#                        systemd-analyze fallback regex and raw-output logging
#                        on parse failure.
#   1.2.0 - 2026-10-05 - Day-of-week schedules use the LONGEST gap between run
#                        days (mon..fri = 72h, not 168h); systemd-analyze
#                        fallback also uses the longest gap over 10 iterations.
#                        Live UNKNOWN (-1) severity for unparseable schedules.
#                        Per-guest `reason` string. Summary adds unknown_count
#                        and recent_vzdump_failures_24h; tasks gain
#                        starttime_unix.
#   1.2.1 - 2026-10-06 - Schedules with a date part (e.g. "sun *-*-1..7 01:00",
#                        first Sunday of the month; "*-*-01,15") skip the fast
#                        path and use systemd-analyze's longest gap. Previously
#                        scored as weekly / monthly respectively.
#                        Fix systemd-analyze fallback: it ignored "Iteration #N"
#                        lines (only matched "iter."), so it never got a second
#                        timestamp and every fallback schedule became UNKNOWN.
#                        Translate Proxmox "*/N" repetition to systemd "0/N".
#                        Sub-daily schedules: critical kept >= warning + 6h.
# =============================================================================

import json
import subprocess
import sys
import os
import re
from datetime import datetime, timezone

# =============================================================================
# Configuration
# =============================================================================

LOG_FILE = "/tmp/pve-backup-check.json"

# Fallback thresholds — used ONLY when a guest is matched to a job whose
# schedule can't be parsed. Guests with a parseable schedule use per-guest
# thresholds derived from that schedule (see compute_guest_thresholds).
FALLBACK_WARNING_AGE_HOURS  = 30
FALLBACK_CRITICAL_AGE_HOURS = 50

# How many recent vzdump tasks to include for job-level visibility.
# At ~2 jobs/day this covers ~30 days; raise if you have more frequent jobs.
RECENT_TASK_LIMIT = 60

SEVERITY_RANK = {
  "UNKNOWN": -1,
  "OK":       0,
  "WARNING":  1,
  "HIGH":     2,
  "CRITICAL": 3,
}

# =============================================================================
# pvesh helpers
# =============================================================================

def pvesh_get(path, extra_args=None):
  """
  Run: pvesh get <path> [extra_args...] --output-format json
  Returns parsed JSON on success, None on failure.
  Errors are printed to stderr so they appear in the systemd journal.
  """
  cmd = ["pvesh", "get", path]
  if extra_args:
    cmd += extra_args
  cmd += ["--output-format", "json"]

  try:
    result = subprocess.run(
      cmd,
      capture_output=True,
      text=True,
      timeout=30,
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
  """
  Returns the short hostname — matches the node name pvesh expects.
  """
  result = subprocess.run(["hostname", "-s"], capture_output=True, text=True)
  return result.stdout.strip()


def iso(ts):
  if not ts:
    return None
  return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds")


# =============================================================================
# Schedule parsing — systemd calendar → interval hours
# =============================================================================

# Match a datetime like "2026-08-01 00:00:00" (with or without a leading weekday
# word and with or without a trailing timezone). Relaxed on purpose — systemd
# has changed this format across versions and we shouldn't be fragile to it.
_DATETIME_RE = re.compile(r"(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})")

# Systemd calendar day-of-week tokens
_DOW_RE = re.compile(r"\b(mon|tue|wed|thu|fri|sat|sun)\b")

# A day token, optionally a range: "sun", "mon..fri", "fri..mon"
_DOW_TOKEN_RE = re.compile(
  r"\b(mon|tue|wed|thu|fri|sat|sun)\b(?:\.\.(mon|tue|wed|thu|fri|sat|sun)\b)?"
)
_DOW_ORDER = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _dow_max_gap_hours(s):
  """
  Works out which weekdays a schedule runs on (lists and ranges, including
  wrap-around ranges like fri..mon) and returns the LONGEST gap between
  consecutive run days, in hours. Using the longest gap means weekends and
  other planned gaps never raise false alarms.

    "sun 01:00"        -> 168h  (once a week)
    "mon..fri 00:00"   ->  72h  (Fri -> Mon)
    "mon,wed,fri 03:00"->  72h  (Fri -> Mon)
    "mon..sun 02:00"   ->  24h
  """
  days = set()
  for m in _DOW_TOKEN_RE.finditer(s):
    start = _DOW_ORDER.index(m.group(1))
    if m.group(2):
      end = _DOW_ORDER.index(m.group(2))
      i = start
      while True:
        days.add(i)
        if i == end:
          break
        i = (i + 1) % 7
    else:
      days.add(start)

  if not days:
    return None

  ordered = sorted(days)
  if len(ordered) == 1:
    return 24.0 * 7

  gaps = [ordered[i + 1] - ordered[i] for i in range(len(ordered) - 1)]
  gaps.append(ordered[0] + 7 - ordered[-1])   # wrap from last day back to first
  return 24.0 * max(gaps)

# Bare time-of-day form like "21:00" or "03:00:00" (which systemd treats as daily)
_BARE_TIME_RE = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?$")

# Explicit single day-of-month like "*-*-01" or "*-*-1 02:00" (monthly).
# Anchored: lists/ranges ("*-*-01,15", "*-*-1..7") must NOT match — they go to
# systemd-analyze so the real longest gap is used.
_DOM_RE = re.compile(r"^\*-\*-\d{1,2}( \d{1,2}:\d{2}(:\d{2})?)?$")

# Any date component (YYYY-MM-DD style, with * or ranges). Day-of-week ranges
# use "..", times use ":", so a "-" only ever appears in a date part.
_HAS_DATE_RE = re.compile(r"[\d*]+-[\d*.,]+")


def compute_schedule_interval_hours(schedule):
  """
  Determines the interval (in hours) between consecutive fires of a systemd
  calendar expression.

  Tries a fast-path keyword/pattern match first (covers all common PVE
  backup schedules without shelling out), then falls back to
  `systemd-analyze calendar` only when the fast path can't classify the spec.

  Returns float hours, or None if the schedule can't be interpreted.
  """
  if not schedule or not schedule.strip():
    return None

  s = schedule.strip().lower()

  # Named systemd calendar shortcuts
  if s in ("minutely",):                             return 1.0 / 60.0
  if s in ("hourly",):                               return 1.0
  if s in ("daily", "midnight"):                     return 24.0
  if s in ("weekly",):                               return 24.0 * 7
  if s in ("monthly",):                              return 24.0 * 30
  if s in ("quarterly",):                            return 24.0 * 91
  if s in ("semiannually",):                         return 24.0 * 182
  if s in ("yearly", "annually"):                    return 24.0 * 365

  # Bare "HH:MM" or "HH:MM:SS" → daily at that time
  if _BARE_TIME_RE.match(s):                         return 24.0

  # Weekday AND a date part (e.g. first Sunday of the month) — the weekday
  # alone would understate the gap, so let systemd-analyze work it out
  if _DOW_RE.search(s) and _HAS_DATE_RE.search(s):
    return _systemd_analyze_interval(schedule)

  # Day-of-week token(s) present → longest gap between run days
  if _DOW_RE.search(s):
    gap = _dow_max_gap_hours(s)
    if gap is not None:                              return gap

  # Explicit single *-*-DD form → monthly
  if _DOM_RE.match(s):                               return 24.0 * 30

  # Fallback: ask systemd-analyze
  return _systemd_analyze_interval(schedule)


def _systemd_analyze_interval(schedule):
  """
  Ask systemd-analyze for two consecutive fire times and return the delta in
  hours. Kept as a fallback for schedules the fast path can't classify.
  """
  env = {**os.environ, "TZ": "UTC"}

  # Proxmox accepts "*/N" repetition (e.g. "*/2:00" = every 2 hours,
  # "*/15" = every 15 minutes); systemd needs a start value ("0/2:00").
  sd_spec = re.sub(r"(^|[\s:])\*/", r"\g<1>0/", schedule.strip())
  # A bare "0/15" (PVE: every 15 min) means minutes to PVE, hours to systemd
  if re.fullmatch(r"0/\d+", sd_spec):
    sd_spec = "*:" + sd_spec

  try:
    result = subprocess.run(
      ["systemd-analyze", "calendar", sd_spec, "--iterations=10"],
      capture_output=True, text=True, timeout=5, env=env,
    )
  except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
    print(f"[WARN] systemd-analyze failed for schedule '{schedule}': {exc}", file=sys.stderr)
    return None

  if result.returncode != 0:
    print(f"[WARN] systemd-analyze rejected schedule '{schedule}': {result.stderr.strip()}", file=sys.stderr)
    return None

  times = []
  for line in result.stdout.splitlines():
    # Only look at lines that reference an elapse time — skip "Original form"
    # and "Normalized form" lines which may contain unrelated dates.
    low = line.lower()
    if "elapse" not in low and "iteration" not in low and "iter." not in low:
      continue
    m = _DATETIME_RE.search(line)
    if not m:
      continue
    try:
      dt = datetime.strptime(m.group(1).replace("T", " "), "%Y-%m-%d %H:%M:%S")
      times.append(dt.replace(tzinfo=timezone.utc))
    except ValueError:
      continue

  if len(times) < 2:
    # Log the raw output so we can adjust the parser if the format changes again
    preview = result.stdout.strip().replace("\n", " | ")
    print(f"[WARN] Could not extract elapse times from systemd-analyze output for '{schedule}': {preview}", file=sys.stderr)
    return None

  # Longest gap between consecutive fires — fail-safe against false alarms on
  # schedules with uneven spacing (weekdays only, specific dates, etc.)
  deltas = [(times[i + 1] - times[i]).total_seconds() for i in range(len(times) - 1)]
  delta_seconds = max(deltas)
  if delta_seconds <= 0:
    return None
  return delta_seconds / 3600.0


def compute_guest_thresholds(interval_hours):
  """
  Given a per-guest expected interval in hours, returns (warning_at, critical_at)
  in hours. Fails safe: if interval is None, returns the fallback pair.
  """
  if interval_hours is None:
    return FALLBACK_WARNING_AGE_HOURS, FALLBACK_CRITICAL_AGE_HOURS

  warning_at  = interval_hours + max(6.0, interval_hours * 0.10)
  # Critical is normally 2x the interval. For sub-daily schedules the 6h
  # warning grace would otherwise put warning AFTER critical, so keep critical
  # at least 6h beyond warning. No effect on daily-or-longer schedules.
  critical_at = max(interval_hours * 2.0, warning_at + 6.0)
  return round(warning_at, 1), round(critical_at, 1)


# =============================================================================
# Backup job enumeration and guest matching
# =============================================================================

def get_backup_jobs():
  """
  Reads /cluster/backup and returns list of enabled backup jobs with parsed
  schedule intervals and pre-split vmid/exclude lists.
  """
  jobs_raw = pvesh_get("/cluster/backup")
  if jobs_raw is None:
    print("[WARN] Could not read /cluster/backup — falling back to fixed thresholds for all guests", file=sys.stderr)
    return []

  jobs = []
  for j in jobs_raw:
    # PVE may express enabled as 0/1, missing = enabled
    enabled = j.get("enabled", 1)
    if str(enabled) == "0":
      continue

    schedule = j.get("schedule", "")
    interval_hours = compute_schedule_interval_hours(schedule)

    vmids   = [v.strip() for v in (j.get("vmid") or "").split(",") if v.strip()]
    excludes = [v.strip() for v in (j.get("exclude") or "").split(",") if v.strip()]

    # node scope — a job can be restricted to specific nodes with `node: n1,n2`
    node_scope = [n.strip() for n in (j.get("node") or "").split(",") if n.strip()]

    jobs.append({
      "id":              j.get("id"),
      "schedule":        schedule,
      "interval_hours":  round(interval_hours, 1) if interval_hours is not None else None,
      "schedule_parse_error": interval_hours is None and bool(schedule),
      "storage":         j.get("storage"),
      "vmid":            vmids,
      "all":             bool(int(j.get("all", 0) or 0)),
      "pool":            j.get("pool"),
      "exclude":         excludes,
      "node_scope":      node_scope,
      "mode":            j.get("mode"),
      "enabled":         True,
    })
  return jobs


def resolve_pool_vmids(pool_name):
  """Returns a set of vmid strings that are members of the named pool."""
  if not pool_name:
    return set()
  pool_data = pvesh_get(f"/pools/{pool_name}")
  if pool_data is None:
    return set()
  members = pool_data.get("members", [])
  return {str(m.get("vmid")) for m in members if m.get("vmid") is not None}


def build_pool_cache(jobs):
  """Pre-resolve every pool referenced by any job — one query per unique pool."""
  cache = {}
  for j in jobs:
    p = j.get("pool")
    if p and p not in cache:
      cache[p] = resolve_pool_vmids(p)
  return cache


def find_matching_jobs(vmid, node, jobs, pool_cache):
  """
  Returns list of jobs that would back up this vmid on this node.
  A job matches if:
    - it's enabled
    - its node_scope is empty OR contains this node
    - the vmid is NOT in its exclude list
    - AND (the vmid is in its vmid list, OR all=1, OR the vmid is in its pool)
  """
  vmid_str = str(vmid)
  matches = []
  for j in jobs:
    if j["node_scope"] and node not in j["node_scope"]:
      continue
    if vmid_str in j["exclude"]:
      continue

    covered = False
    if vmid_str in j["vmid"]:
      covered = True
    elif j["all"]:
      covered = True
    elif j["pool"] and vmid_str in pool_cache.get(j["pool"], set()):
      covered = True

    if covered:
      matches.append(j)
  return matches


def pick_tightest_interval(matching_jobs):
  """From the matching jobs, pick the tightest (shortest) parseable interval."""
  intervals = [j["interval_hours"] for j in matching_jobs if j["interval_hours"] is not None]
  if not intervals:
    return None
  return min(intervals)


# =============================================================================
# Storage / backup enumeration
# =============================================================================

def get_backup_storages(node):
  """
  Returns list of active storages on this node whose content types include 'backup'.
  """
  storages_raw = pvesh_get(f"/nodes/{node}/storage")
  if storages_raw is None:
    print(f"[WARN] Could not enumerate storages on {node}", file=sys.stderr)
    return []

  backup_storages = []
  for st in storages_raw:
    content_types = (st.get("content") or "").split(",")
    if "backup" in content_types and st.get("active", 1):
      backup_storages.append({
        "storage": st.get("storage"),
        "type":    st.get("type"),
      })
  return backup_storages


def build_backup_index(node, backup_storages, now_ts):
  """
  Queries each backup storage's content list and builds:
    { vmid_str: [ {storage, volid, ctime, age_hours, verification_state,
                   protected, size}, ... ] }
  sorted per-vmid newest-first.
  """
  index = {}

  for st in backup_storages:
    storage_id = st["storage"]
    content = pvesh_get(
      f"/nodes/{node}/storage/{storage_id}/content",
      extra_args=["--content", "backup"],
    )
    if content is None:
      print(f"[WARN] Could not list content for storage {storage_id}", file=sys.stderr)
      continue

    for item in content:
      vmid = str(item.get("vmid", "")).strip()
      if not vmid:
        continue
      ctime = item.get("ctime", 0)
      age_hours = round((now_ts - ctime) / 3600, 1) if ctime else None
      verification = item.get("verification") or {}

      index.setdefault(vmid, []).append({
        "storage":             storage_id,
        "storage_type":        st["type"],
        "volid":               item.get("volid"),
        "ctime_iso":           iso(ctime),
        "age_hours":           age_hours,
        "verification_state":  verification.get("state"),
        "protected":           bool(item.get("protected", 0)),
        "size_bytes":          item.get("size"),
      })

  for vmid in index:
    index[vmid].sort(key=lambda b: (b["age_hours"] if b["age_hours"] is not None else 999999))

  return index


# =============================================================================
# Severity
# =============================================================================

def _fmt_hours(h):
  """Human-friendly duration: '13.8h' under two days, '67.3d' beyond."""
  if h is None:
    return "?"
  if h <= 48:
    return f"{h:.1f}h"
  return f"{h / 24:.1f}d"


def calculate_severity(is_template, status, backups, matching_jobs,
                       warning_at_hours, critical_at_hours,
                       interval_hours, schedule_parse_error):
  """
  Applies the severity matrix. See module docstring for the full matrix.
  Returns (severity, reason) — reason is a short human-readable explanation.
  """
  if is_template:
    return "OK", "template (not scored)"

  job_ids = ", ".join(j["id"] for j in matching_jobs)

  # No job coverage — running is CRITICAL, stopped is HIGH
  if not matching_jobs:
    sev = "CRITICAL" if status == "running" else "HIGH"
    return sev, f"{status}, not in any backup job"

  # Job covers this guest but no backup exists on disk yet
  if not backups:
    sev = "CRITICAL" if status == "running" else "HIGH"
    return sev, f"{status}, in job {job_ids} but no backups found on any storage"

  newest = backups[0]
  age_hours = newest["age_hours"]
  verification = newest["verification_state"]
  where = newest["storage"]

  if age_hours is not None and age_hours >= critical_at_hours:
    return "CRITICAL", (f"last backup {_fmt_hours(age_hours)} ago on {where}, "
                        f"critical at {_fmt_hours(critical_at_hours)} (job {job_ids})")

  if verification == "failed":
    return "HIGH", f"latest backup on {where} FAILED verification"

  if schedule_parse_error:
    return "UNKNOWN", (f"schedule for job {job_ids} could not be parsed; "
                       f"last backup {_fmt_hours(age_hours)} ago on {where}")

  if age_hours is not None and age_hours >= warning_at_hours:
    return "WARNING", (f"last backup {_fmt_hours(age_hours)} ago on {where}, "
                       f"expected every {_fmt_hours(interval_hours)}")

  if verification not in (None, "ok"):
    return "WARNING", f"latest backup on {where} verification state '{verification}'"

  return "OK", f"last backup {_fmt_hours(age_hours)} ago on {where}"


# =============================================================================
# VM / CT enumeration
# =============================================================================

def check_guests(node, guest_type, backup_index, jobs, pool_cache, now_ts):
  """
  Enumerates ALL guests of guest_type ('qemu' or 'lxc') on node, regardless
  of running/stopped status. Returns a list of per-guest result dicts.
  """
  guests_raw = pvesh_get(f"/nodes/{node}/{guest_type}")
  if guests_raw is None:
    print(f"[WARN] Could not enumerate {guest_type} guests on {node}", file=sys.stderr)
    return []

  results = []

  for guest in sorted(guests_raw, key=lambda x: x.get("vmid", 0)):
    vmid        = guest.get("vmid")
    name        = guest.get("name", f"{guest_type}-{vmid}")
    status      = guest.get("status", "unknown")
    is_template = bool(guest.get("template", 0))

    matching_jobs = find_matching_jobs(vmid, node, jobs, pool_cache)
    interval_hours = pick_tightest_interval(matching_jobs)
    warning_at, critical_at = compute_guest_thresholds(interval_hours)

    # Flag if this guest is matched to jobs but none had a parseable schedule
    schedule_parse_error = bool(matching_jobs) and interval_hours is None

    backups = backup_index.get(str(vmid), [])
    severity, reason = calculate_severity(
      is_template, status, backups, matching_jobs, warning_at, critical_at,
      interval_hours, schedule_parse_error,
    )

    newest = backups[0] if backups else None
    age_hours = newest["age_hours"] if newest else None

    overdue_hours = None
    if age_hours is not None and interval_hours is not None:
      overshoot = round(age_hours - interval_hours, 1)
      if overshoot > 0:
        overdue_hours = overshoot

    results.append({
      "vmid":                    vmid,
      "name":                    name,
      "type":                    guest_type,
      "status":                  status,
      "template":                is_template,
      "severity":                severity,
      "severity_int":            SEVERITY_RANK.get(severity, -1),
      "reason":                  reason,
      "backup_count":            len(backups),
      "last_backup_ctime":       newest["ctime_iso"] if newest else None,
      "last_backup_age_hours":   age_hours,
      "last_backup_storage":     newest["storage"] if newest else None,
      "last_backup_verification": newest["verification_state"] if newest else None,
      # Cadence data — Zabbix triggers can key off these directly
      "expected_interval_hours": round(interval_hours, 1) if interval_hours is not None else None,
      "warning_at_hours":        warning_at,
      "critical_at_hours":       critical_at,
      "overdue_hours":           overdue_hours,
      "schedule_parse_error":    schedule_parse_error,
      "job_ids":                 [j["id"] for j in matching_jobs],
      "job_count":               len(matching_jobs),
      "unmanaged":               len(matching_jobs) == 0 and not is_template,
      "backups":                 backups,
    })

  return results


# =============================================================================
# Recent vzdump task history (job-level, not mapped to specific guests)
# =============================================================================

def get_recent_vzdump_tasks(node):
  tasks = pvesh_get(
    f"/nodes/{node}/tasks",
    extra_args=["--typefilter", "vzdump", "--limit", str(RECENT_TASK_LIMIT)],
  )
  if tasks is None:
    print(f"[WARN] Could not retrieve task history on {node}", file=sys.stderr)
    return []

  out = []
  for t in tasks:
    status = t.get("status")
    out.append({
      "upid":          t.get("upid"),
      "starttime":     iso(t.get("starttime")),
      "starttime_unix": t.get("starttime"),
      "endtime":       iso(t.get("endtime")),
      "status":        status,
      "ok":            status == "OK",
      "still_running": status is None,
    })
  return out


# =============================================================================
# Summary
# =============================================================================

def build_summary(vms, lxcs, recent_tasks, now_ts):
  all_guests = vms + lxcs
  scored     = [g for g in all_guests if not g["template"]]

  # UNKNOWN (-1) outranks OK for "worst" purposes, but not WARNING and above
  worst_order = ["OK", "UNKNOWN", "WARNING", "HIGH", "CRITICAL"]
  worst = max((g["severity"] for g in scored), key=worst_order.index, default="OK")
  worst_int = SEVERITY_RANK[worst]

  failed_recent_tasks = sum(1 for t in recent_tasks if t["status"] not in (None, "OK"))
  failed_last_24h = sum(
    1 for t in recent_tasks
    if t["status"] not in (None, "OK")
    and t.get("starttime_unix")
    and now_ts - t["starttime_unix"] <= 86400
  )

  return {
    "total_vms_checked":           len(vms),
    "total_lxc_checked":           len(lxcs),
    "templates_excluded":          sum(1 for g in all_guests if g["template"]),
    "guests_never_backed_up":      sum(1 for g in scored if g["backup_count"] == 0),
    "guests_unmanaged":            sum(1 for g in scored if g["unmanaged"]),
    "guests_overdue":              sum(1 for g in scored if g["overdue_hours"] is not None),
    "guests_schedule_parse_error": sum(1 for g in scored if g["schedule_parse_error"]),
    "critical_count":              sum(1 for g in scored if g["severity"] == "CRITICAL"),
    "high_count":                  sum(1 for g in scored if g["severity"] == "HIGH"),
    "warning_count":               sum(1 for g in scored if g["severity"] == "WARNING"),
    "unknown_count":               sum(1 for g in scored if g["severity"] == "UNKNOWN"),
    "worst_severity":              worst,
    "worst_severity_int":          worst_int,
    "recent_vzdump_task_failures": failed_recent_tasks,
    "recent_vzdump_failures_24h":  failed_last_24h,
  }


# =============================================================================
# Main
# =============================================================================

def main():
  now_ts   = datetime.now(timezone.utc).timestamp()
  now_iso  = datetime.now(timezone.utc).isoformat(timespec="seconds")
  node     = get_node_name()

  print(f"[INFO] pve-backup-check starting on {node}", file=sys.stderr)

  jobs        = get_backup_jobs()
  pool_cache  = build_pool_cache(jobs)
  print(f"[INFO] {len(jobs)} enabled backup job(s) discovered", file=sys.stderr)

  backup_storages = get_backup_storages(node)
  if not backup_storages:
    print(f"[WARN] No storages with 'backup' content found on {node}", file=sys.stderr)

  backup_index = build_backup_index(node, backup_storages, now_ts)

  vms  = check_guests(node, "qemu", backup_index, jobs, pool_cache, now_ts)
  lxcs = check_guests(node, "lxc",  backup_index, jobs, pool_cache, now_ts)

  recent_tasks    = get_recent_vzdump_tasks(node)
  recent_failures = [t for t in recent_tasks if not t["ok"] and not t["still_running"]]
  summary         = build_summary(vms, lxcs, recent_tasks, now_ts)

  report = {
    "generated_iso":          now_iso,
    "generated_unix":         int(now_ts),
    "hostname":               node,
    "backup_storages":        backup_storages,
    "backup_jobs":            jobs,
    "pool_membership":        {p: sorted(list(v)) for p, v in pool_cache.items()},
    "summary":                summary,
    "vms":                    vms,
    "lxc":                    lxcs,
    "recent_vzdump_tasks":    recent_tasks,
    "recent_vzdump_failures": recent_failures,
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
    f"{summary['total_lxc_checked']} LXC checked "
    f"({summary['templates_excluded']} templates excluded, "
    f"{summary['guests_unmanaged']} unmanaged). "
    f"Worst severity: {summary['worst_severity']}. "
    f"Report: {LOG_FILE}",
    file=sys.stderr,
  )


if __name__ == "__main__":
  main()
