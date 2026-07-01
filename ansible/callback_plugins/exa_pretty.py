# =================================================================================================
# callback_plugins/exa_pretty.py
# Example Music Limited — Colourised Ansible output callback
# =================================================================================================
# Based on the community.general diy callback:
#  https://docs.ansible.com/projects/ansible/latest/collections/community/general/diy_callback.html
#
# To enable globally, add to ansible.cfg:
#   [defaults]
#   stdout_callback     = exa_pretty
#   callback_whitelist  = exa_pretty
#
# Colours follow the firewallme.sh convention:
#   [*] cyan    — info / task running
#   [+] green   — ok / success / no change
#   [!] yellow  — warning / skipped
#   [→] cyan    — changed
#   [✗] red     — failed / unreachable
#
# Changelog:
#   2026-06-20  Initial file — port of firewallme.sh colour scheme to Ansible
#   2026-06-27  Merged: live unreachable counter + classify_unreachable + fmt_ip;
#               restored colourised recap and DIM/WHITE host distinction
#   2026-06-27  Fix \r/display collision; grouped recap (reachable, no_route, unreachable)
#   2026-06-30  Fix: list/tuple msg values (e.g. debug: msg: [...]) were being
#               rendered via Python repr — "['line1', 'line2', ...]" — instead
#               of one line per element. v2_runner_on_ok now detects list/tuple
#               msg and joins with real newlines, indented to align under the
#               host column, matching how multi-line debug summaries (preflight
#               summary, finish banner etc.) are meant to display.
#               Also: DIM (\033[2;37m, faint white) was unreadable on several
#               terminal colour schemes — replaced with CYAN throughout
#               (host column in ok/skipped lines, recap host names, play
#               separator dim text) for consistency with the [*] info colour
#               and actual readability. DIM constant kept defined (unused) in
#               case something else still references C.DIM externally.
# =================================================================================================

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = """
name: exa_pretty
type: stdout
short_description: Example Music colourised output
description:
  - Colourised Ansible output following Example Music style.
options:
  suppress_unreachable:
    description:
      - If true, suppress unreachable host messages.
    type: bool
    default: false
"""

from ansible.plugins.callback import CallbackBase
import datetime
import os
import sys
from collections import defaultdict

class C:
  RESET  = "\033[0m"
  GREEN  = "\033[0;32m"
  YELLOW = "\033[1;33m"
  RED    = "\033[0;31m"
  CYAN   = "\033[0;36m"
  ORANGE = "\033[38;5;208m"
  WHITE  = "\033[1;37m"
  DIM    = "\033[2;37m"   # kept for compatibility — no longer used below, see changelog 2026-06-30

def _ts():
  return datetime.datetime.now().strftime("%H:%M:%S")

def fmt_ip(ip):
  return f"{ip:<16}"

def ok(msg):   return f"{C.GREEN}[+]{C.RESET} {msg}"
def info(msg): return f"{C.CYAN}[*]{C.RESET} {msg}"
def warn(msg): return f"{C.YELLOW}[!]{C.RESET} {msg}"
def err(msg):  return f"{C.RED}[✗]{C.RESET} {msg}"
def chg(msg):  return f"{C.CYAN}[→]{C.RESET} {msg}"

def classify_unreachable(msg: str) -> str:
  m = (msg or "").lower()
  if "no route to host" in m:
    return "no_route"
  if "timed out" in m or "timeout" in m:
    return "timeout"
  if "connection refused" in m or "refused" in m:
    return "refused"
  return "other"

def fmt_msg(msg, indent_width):
  """
  Render a debug/result msg for display.

  - str:            returned as-is.
  - list/tuple:      joined with newlines, each continuation line indented
                      to align under the host column (indent_width spaces),
                      so multi-line debug summaries (e.g. preflight banners)
                      render as an actual multi-line block instead of a
                      single-line Python repr like "['a', 'b', 'c']".
  - anything else:   str()'d as a fallback (dicts etc. still readable,
                      just not specially formatted).
  """
  if isinstance(msg, (list, tuple)):
    pad = " " * indent_width
    lines = [str(line) for line in msg]
    if not lines:
      return ""
    return ("\n" + pad).join(lines)
  return msg if isinstance(msg, str) else str(msg)

class CallbackModule(CallbackBase):
  CALLBACK_VERSION = 2.0
  CALLBACK_TYPE    = "stdout"
  CALLBACK_NAME    = "exa_pretty"

  def _load_settings(self):
    self.suppress_unreachable = False
    try:
      opt = self.get_option("suppress_unreachable")
      if opt is not None:
        self.suppress_unreachable = bool(opt)
    except Exception:
      pass
    val = os.getenv("ANSIBLE_SUPPRESS_UNREACHABLE")
    if val is not None:
      self.suppress_unreachable = val.lower() in ("1", "true", "yes", "y")
    self._unreach_counts = defaultdict(int)
    self._unreach_hosts  = defaultdict(list)
    self._unreach_total  = 0
    self._last_line_len  = 0
    self._counter_active = False

  def _clear_counter(self):
    """Erase the live counter line before printing anything else."""
    if self._counter_active:
      sys.stdout.write("\r" + " " * self._last_line_len + "\r")
      sys.stdout.flush()
      self._counter_active = False

  def _render_unreachable_line(self):
    parts  = [f"{k}={v}" for k, v in self._unreach_counts.items()]
    line   = f"[!] UNREACHABLE total={self._unreach_total} ({', '.join(parts)})"
    padded = line + " " * max(0, self._last_line_len - len(line))
    self._last_line_len  = len(line)
    self._counter_active = True
    sys.stdout.write("\r" + padded)
    sys.stdout.flush()

  def v2_playbook_on_start(self, playbook):
    self._load_settings()
    self._display.display(
      f"\n{C.CYAN}{'═' * 80}{C.RESET}\n"
      f"{C.WHITE}  Example Music — Ansible{C.RESET}\n"
      f"{C.CYAN}  {playbook._file_name}{C.RESET}\n"
      f"{C.CYAN}{'═' * 80}{C.RESET}\n"
    )

  def v2_playbook_on_play_start(self, play):
    self._clear_counter()
    self._display.display(
      f"\n{C.CYAN}── {play.get_name()}{C.RESET}\n"
    )

  def v2_playbook_on_task_start(self, task, is_conditional):
    self._clear_counter()
    self._display.display(info(f"{C.CYAN}{_ts()}{C.RESET}  {task.get_name()}"))

  def v2_runner_on_ok(self, result):
    self._clear_counter()
    host    = result._host.get_name()
    changed = result._result.get("changed", False)
    raw_msg = result._result.get("msg", "")
    ip      = fmt_ip(host)
    # Host column width: "[+] " (4) + ip column width, so wrapped lines of a
    # multi-line msg align under the first line's text rather than under
    # column zero.
    indent_width = 4 + len(ip) + 2
    msg = fmt_msg(raw_msg, indent_width)

    if changed:
      self._display.display(chg(f"  {C.WHITE}{ip}{C.RESET}  {msg}"))
    else:
      self._display.display(ok(f"  {C.CYAN}{ip}{C.RESET}  {msg if msg else 'no change'}"))

  def v2_runner_on_failed(self, result, ignore_errors=False):
    self._clear_counter()
    host    = result._host.get_name()
    raw_msg = result._result.get("msg", result._result.get("stderr", "unknown error"))
    ip      = fmt_ip(host)
    indent_width = 4 + len(ip) + 2
    msg = fmt_msg(raw_msg, indent_width)

    self._display.display(err(f"  {C.WHITE}{ip}{C.RESET}  {msg}"))
    if ignore_errors:
      self._display.display(warn("  (ignored)"))

  def v2_runner_on_skipped(self, result):
    self._clear_counter()
    host = result._host.get_name()
    ip   = fmt_ip(host)
    self._display.display(warn(f"  {C.CYAN}{ip}{C.RESET}  skipped"))

  def v2_runner_on_unreachable(self, result):
    if getattr(self, "suppress_unreachable", False):
      return

    host     = result._host.get_name()
    msg      = result._result.get("msg", "unreachable")
    category = classify_unreachable(msg)

    self._unreach_counts[category] += 1
    self._unreach_hosts[category].append(host)
    self._unreach_total += 1
    self._render_unreachable_line()

  def v2_playbook_on_stats(self, stats):
    self._clear_counter()

    # bucket hosts by outcome
    reachable = []
    no_route  = []
    timeout   = []
    other_unr = []

    for host in sorted(stats.processed.keys()):
      s = stats.summarize(host)

      if s['unreachable']:
        # find which category this host landed in
        if host in self._unreach_hosts.get("no_route", []):
          no_route.append((host, s))
        elif host in self._unreach_hosts.get("timeout", []):
          timeout.append((host, s))
        else:
          other_unr.append((host, s))
      else:
        reachable.append((host, s))

    self._display.display(f"\n{C.WHITE}{'═' * 80}{C.RESET}")
    self._display.display(f"{C.CYAN}  PLAY RECAP{C.RESET}")
    self._display.display(f"{C.WHITE}{'═' * 80}{C.RESET}")

    # --- reachable ---
    if reachable:
      self._display.display(f"\n{C.GREEN}  ── Reachable ({len(reachable)}){C.RESET}")
      for host, s in reachable:
        fai_c = C.RED if s['failures'] else C.CYAN
        self._display.display(
          f"  {C.WHITE}{host:<30}{C.RESET}"
          f"  {C.GREEN}ok={s['ok']:<4}{C.RESET}"
          f"  {C.CYAN}changed={s['changed']:<4}{C.RESET}"
          f"  {C.YELLOW}skipped={s['skipped']:<4}{C.RESET}"
          f"  {fai_c}failed={s['failures']:<4}{C.RESET}"
        )

    # --- no route ---
    if no_route:
      self._display.display(f"\n{C.ORANGE}  ── No Route ({len(no_route)}){C.RESET}")
      for host, s in no_route:
        self._display.display(
          f"  {C.CYAN}{host:<30}{C.RESET}  {C.ORANGE}no route to host{C.RESET}"
        )

    # --- timeout / other unreachable ---
    unreachable_rows = timeout + other_unr
    if unreachable_rows:
      label = "Unreachable"
      self._display.display(f"\n{C.RED}  ── {label} ({len(unreachable_rows)}){C.RESET}")
      for host, s in unreachable_rows:
        reason = "timeout" if (host in self._unreach_hosts.get("timeout", [])) else "other"
        self._display.display(
          f"  {C.CYAN}{host:<30}{C.RESET}  {C.RED}{reason}{C.RESET}"
        )

    self._display.display(f"\n{C.WHITE}{'═' * 80}{C.RESET}\n")

