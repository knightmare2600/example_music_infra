# =============================================================================
# callback_plugins/exa_pretty.py
# Example Music Limited — Colourised Ansible output callback
# =============================================================================
# Based on the community.general diy callback:
#   https://docs.ansible.com/projects/ansible/latest/collections/community/general/diy_callback.html
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
# =============================================================================

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = """
    name: exa_pretty
    type: stdout
    short_description: Example Music colourised output
    description:
      - Colourised Ansible output following the Example Music colour scheme.
      - ok=green, changed=cyan, skipped=yellow, failed=red, unreachable=red.
"""

from ansible.plugins.callback import CallbackBase
from ansible.utils.color import colorize, hostcolor

import datetime


class C:
    RESET  = "\033[0m"
    GREEN  = "\033[0;32m"
    YELLOW = "\033[1;33m"
    RED    = "\033[0;31m"
    CYAN   = "\033[0;36m"
    ORANGE = "\033[38;5;208m"
    WHITE  = "\033[1;37m"
    DIM    = "\033[2;37m"


def _ts():
    return datetime.datetime.now().strftime("%H:%M:%S")


def ok(msg):    return f"{C.GREEN}[+]{C.RESET} {msg}"
def info(msg):  return f"{C.CYAN}[*]{C.RESET} {msg}"
def warn(msg):  return f"{C.YELLOW}[!]{C.RESET} {msg}"
def err(msg):   return f"{C.RED}[✗]{C.RESET} {msg}"
def chg(msg):   return f"{C.CYAN}[→]{C.RESET} {msg}"


class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE    = "stdout"
    CALLBACK_NAME    = "exa_pretty"

    def v2_playbook_on_start(self, playbook):
        self._display.display(
            f"\n{C.CYAN}{'═' * 62}{C.RESET}\n"
            f"{C.WHITE}  Example Music — Ansible{C.RESET}\n"
            f"{C.DIM}  {playbook._file_name}{C.RESET}\n"
            f"{C.CYAN}{'═' * 62}{C.RESET}\n"
        )

    def v2_playbook_on_play_start(self, play):
        self._display.display(
            f"\n{C.CYAN}── {play.get_name()} {'─' * max(0, 55 - len(play.get_name()))}{C.RESET}\n"
        )

    def v2_playbook_on_task_start(self, task, is_conditional):
        name = task.get_name()
        self._display.display(info(f"{C.DIM}{_ts()}{C.RESET}  {name}"))

    def v2_runner_on_ok(self, result):
        host   = result._host.get_name()
        changed = result._result.get("changed", False)
        msg    = result._result.get("msg", "")
        if changed:
            self._display.display(chg(f"  {C.WHITE}{host}{C.RESET}  {msg}"))
        else:
            self._display.display(ok(f"  {C.DIM}{host}{C.RESET}  {msg if msg else 'no change'}"))

    def v2_runner_on_failed(self, result, ignore_errors=False):
        host = result._host.get_name()
        msg  = result._result.get("msg", result._result.get("stderr", "unknown error"))
        self._display.display(err(f"  {C.WHITE}{host}{C.RESET}  {msg}"))
        if ignore_errors:
            self._display.display(warn("  (ignored)"))

    def v2_runner_on_skipped(self, result):
        host = result._host.get_name()
        self._display.display(warn(f"  {C.DIM}{host}{C.RESET}  skipped"))

    def v2_runner_on_unreachable(self, result):
        host = result._host.get_name()
        msg  = result._result.get("msg", "unreachable")
        self._display.display(err(f"  {C.WHITE}{host}{C.RESET}  UNREACHABLE — {msg}"))

    def v2_playbook_on_stats(self, stats):
        self._display.display(f"\n{C.WHITE}{'═' * 62}{C.RESET}")
        self._display.display(f"{C.WHITE}  PLAY RECAP{C.RESET}")
        self._display.display(f"{C.WHITE}{'═' * 62}{C.RESET}")
        hosts = sorted(stats.processed.keys())
        for host in hosts:
            s = stats.summarize(host)
            line = (
                f"  {C.WHITE}{host:<30}{C.RESET}"
                f"  {C.GREEN}ok={s['ok']:<4}{C.RESET}"
                f"  {C.CYAN}changed={s['changed']:<4}{C.RESET}"
                f"  {C.YELLOW}skipped={s['skipped']:<4}{C.RESET}"
                f"  {C.RED}failed={s['failures']:<4}{C.RESET}"
                f"  {C.RED}unreachable={s['unreachable']}{C.RESET}"
            )
            self._display.display(line)
        self._display.display(f"{C.WHITE}{'═' * 62}{C.RESET}\n")
