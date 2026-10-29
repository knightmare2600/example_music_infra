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

Uses .gitleaks.toml (repo root) -- see that file's own header for the
2026-10-29 fix (useDefault was missing, so the entire built-in ruleset was
previously disabled) and why exclusions live in .gitleaksignore instead of
a [[allowlists]] block (that mechanism doesn't work against the gitleaks
build this was tested against).

If .gitleaks.local.toml exists (repo root, gitignored -- never committed),
it is used INSTEAD of .gitleaks.toml. This is for custom rules that need a
real, non-fictional value in their own regex pattern (e.g. a real email
domain) -- the rule's pattern text is never committed, only the
.gitleaksignore fingerprints it generates (which are opaque hashes/paths,
not the matched value itself). Robert's explicit instruction, 2026-10-29:
"do not commit the file with the real data in it, in fact, exclude it."

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
GITLEAKS_LOCAL_CONFIG = REPO_ROOT / ".gitleaks.local.toml"


def main():
    strict = "--strict" in sys.argv

    config_path = GITLEAKS_LOCAL_CONFIG if GITLEAKS_LOCAL_CONFIG.is_file() else GITLEAKS_CONFIG

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
                "--config", str(config_path),
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
              f"(config: {config_path.relative_to(REPO_ROOT)}).")
        return 0

    print(f"{len(findings)} potential secret(s) found by gitleaks -- NOT shown here "
          "(the actual matched value is deliberately never printed by this check):")
    for f in findings:
        commit = (f.get("Commit") or "working tree")[:12]
        print(f"  - {f.get('File')}:{f.get('StartLine')}  rule={f.get('RuleID')}  commit={commit}")

    print(
        "\nTriage each finding directly with gitleaks (not through this check's output) --"
        " it prints the actual matched value:\n"
        f"  gitleaks detect --source . --config {config_path.relative_to(REPO_ROOT)}"
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
