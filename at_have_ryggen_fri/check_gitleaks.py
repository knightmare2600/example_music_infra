#!/usr/bin/env python3
"""
check_gitleaks.py -- part of at_have_ryggen_fri.

Scans the repo's full git history (not just the current working tree) for
secrets -- API keys, private keys, passwords, tokens -- via gitleaks
(github.com/gitleaks/gitleaks). Robert's ask, 2026-08-04: "gitleaks needs to
hook into the framework too, so it can check not only before a git push but
as part of the harness."

Found live, 2026-08-04: this repo already had docs/gitleaks_guide.md (a
manual how-to reference) but gitleaks was NOT actually wired into anything --
no .git/hooks/pre-commit, no pre-push hook, no config file. An earlier
session note had assumed a pre-push hook existed; it didn't. Checked, not
assumed, before building this.

Same host-local-tool pattern as check 11 (check_ssh_keys.py's private-key
presence check) and check 13 (check_mermaid.py's kroki.io dependency): a
bare clone genuinely might not have the gitleaks binary installed (it isn't,
in the environment this check was built in) -- informational by default,
--strict fails on it. A genuine finding (an actual detected secret) is
ALWAYS a hard failure regardless of --strict -- there's no "soft" leaked
credential.

Uses .gitleaks.toml's allowlist (repo root) -- see that file's own header
for what's excluded and why (checked safe, not guessed broad). First real
run against actual gitleaks will likely surface findings needing allowlist
additions -- this check was built and syntax-checked without gitleaks
installed, not run against the real tool yet.

Deliberately does NOT print the actual secret value gitleaks finds, even in
its own informational output -- only file/line/rule-id, enough to triage
without putting the leaked value itself into terminal scrollback or a CI
log. Get the real value (to rotate it, confirm it's real, etc.) by running
gitleaks directly, not through this check's output.

Exit code: 0 if gitleaks is missing (unless --strict) or found nothing.
1 if gitleaks found any real finding (always, regardless of --strict), or
if gitleaks itself errored out (bad config, corrupt repo, etc).
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GITLEAKS_CONFIG = REPO_ROOT / ".gitleaks.toml"


def main():
    strict = "--strict" in sys.argv

    gitleaks_bin = shutil.which("gitleaks")
    if gitleaks_bin is None:
        msg = (
            "gitleaks is not installed on this host -- secret-scanning skipped.\n"
            "Install it (https://github.com/gitleaks/gitleaks/releases, or see\n"
            "docs/gitleaks_guide.md) to actually run this check. Informational only"
            " unless --strict."
        )
        print(msg)
        return 1 if strict else 0

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        report_path = Path(tmp.name)

    try:
        result = subprocess.run(
            [
                gitleaks_bin, "detect",
                "--source", str(REPO_ROOT),
                "--config", str(GITLEAKS_CONFIG),
                "--report-format", "json",
                "--report-path", str(report_path),
                "--exit-code", "0",  # always 0 from gitleaks itself -- we parse the report ourselves
                "--no-banner",
            ],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )

        if result.returncode != 0:
            print("gitleaks itself failed to run (not a finding -- a real tool error):")
            print(result.stderr.strip() or result.stdout.strip())
            return 1

        try:
            findings = json.loads(report_path.read_text(encoding="utf-8") or "[]")
        except json.JSONDecodeError as e:
            print(f"Could not parse gitleaks' own JSON report: {e}")
            return 1
    finally:
        report_path.unlink(missing_ok=True)

    if not findings:
        print("gitleaks scanned the full git history, no secrets found "
              f"(config: {GITLEAKS_CONFIG.relative_to(REPO_ROOT)}).")
        return 0

    print(f"{len(findings)} potential secret(s) found by gitleaks -- NOT shown here "
          "(the actual matched value is deliberately never printed by this check):")
    for f in findings:
        commit = (f.get("Commit") or "working tree")[:12]
        print(f"  - {f.get('File')}:{f.get('StartLine')}  rule={f.get('RuleID')}  commit={commit}")

    print(
        "\nTriage each finding directly with gitleaks (not through this check's output) --"
        " it prints the actual matched value:\n"
        f"  gitleaks detect --source . --config {GITLEAKS_CONFIG.relative_to(REPO_ROOT)}"
        " --report-format json --report-path report.json\n"
        "If a finding is a real secret: rotate it, then remove it from history (this repo's"
        " own git history, not just a new commit).\n"
        "If a finding is a confirmed false positive: add its exact fingerprint to"
        " .gitleaksignore (per-finding), or its path/pattern to .gitleaks.toml"
        " (whole-path/pattern) -- see docs/gitleaks_guide.md section 6 for the difference"
        " between the two mechanisms."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
