# Gitleaks Pre-Commit Scanning Guide (Windows)

## Overview
This guide explains how to use Gitleaks to scan a folder for secrets such as:
- Passwords
- API keys
- Tokens
- Private keys
- Potential PII

---

## 1. Download Gitleaks (Portable)

1. Go to:
   https://github.com/gitleaks/gitleaks/releases

2. Download:
   gitleaks_windows_x64.zip

3. Extract to:
   C:\Tools\gitleaks\

---

## 2. Run a Scan (No Git Required)

```powershell
cd your-project-folder
C:\Tools\gitleaks\gitleaks.exe detect --source . --no-git
```

---

## 3. Show Findings in Console

```powershell
gitleaks detect --source . --no-git --verbose
```

---

## 4. Save Results to File

### JSON report
```powershell
gitleaks detect --source . --no-git --report-format json --report-path report.json
```

### View nicely in PowerShell
```powershell
(Get-Content report.json | ConvertFrom-Json).findings |
    Select-Object File, StartLine, Description, Secret
```

---

## 5. Fail Script if Leaks Found

```powershell
gitleaks detect --source . --no-git --exit-code 1
```

Exit code:
- 0 = clean
- 1 = leaks found

---

## 6. Reduce False Positives

Two different files, for two different kinds of false positive — don't confuse them:

### Ignoring a specific finding — `.gitleaksignore`

`.gitleaksignore` entries are **not** glob patterns or literal strings — each line must be a
**fingerprint** in the form `<commit>:<file>:<rule-id>:<line>`, e.g.:

```
cd5226711335c68be1e720b318b7bc3135a30eb2:cmd/generate/config/rules/sidekiq-secret.go:sidekiq-secret:23
```

Get the real fingerprint for a specific finding you want to ignore by running a scan with a JSON
report first (see Section 4) — each finding in the report already has a `Fingerprint` field in
exactly this format; copy it verbatim into `.gitleaksignore`.

### Ignoring a whole path/pattern — doesn't reliably work here, use `.gitleaksignore` instead

The gitleaks docs describe a `.gitleaks.toml` `[[allowlists]]` (or singular `[allowlist]`, or a
rule-scoped `[rules.allowlist]`) block for excluding whole paths/patterns at once. **Tested
directly against the gitleaks build installed for this repo, 2026-10-29, and confirmed broken**:
a trivial custom rule with an exact-matching `paths` entry in a top-level `[[allowlists]]` or
`[allowlist]` block still fired on the excluded path. `[rules.allowlist]` (nested under the
specific rule) behaved even more surprisingly — it suppressed the rule's matches on *every* path
in the scan, not just the allowlisted one, once any path in its list matched anywhere. None of
these three forms is safe to rely on without re-testing them directly first — don't assume any
syntax from gitleaks' own docs works here without proving it the same way (plant a trivial rule
+ a known match in both an allowed and a disallowed path, confirm only the disallowed one fires).

Until/unless that's re-verified against a gitleaks upgrade, use `.gitleaksignore` for
*everything*, including a whole class of known-safe matches across many files — it's just a flat
list of fingerprints, so "exclude this file/pattern" becomes "exclude every fingerprint that file/
pattern currently produces," generated once from a real scan and pasted in. Fingerprints carry no
secret content (they're `<commit>:<file>:<rule-id>:<line>`), so this is safe to commit even for
hundreds of lines. See `.gitleaksignore`'s own header in this repo for a worked example (815
fingerprints for one repo-wide placeholder-domain rule, generated this way).

### Don't forget `useDefault` — a config with none of your own `[[rules]]` disables ALL detection

A `--config` file that has no `[[rules]]` of its own and no `[extend] useDefault = true` runs
gitleaks with **zero active detection rules** — it will report "no secrets found" against any
content at all, including a planted real-looking AWS key, confirmed directly 2026-10-29 (this
repo's own `.gitleaks.toml` had exactly this bug from 2026-08-04 until then: an allowlist-only
config with no rules and no `useDefault`, silently scanning for nothing every single run). Any
custom config here starts with:

```toml
[extend]
useDefault = true
```

before adding its own `[[rules]]` — `useDefault` and `extend.path` (extending another config
file) can't be combined in the same `[extend]` block, confirmed directly: if you need both the
default ruleset AND another file's content, copy that content in rather than pointing at it.

---

## 7. Git Pre-Commit Hook (Automatic Scanning)

### Option A — Simple Git Hook (No extra tools)

Create this file:

```
.git/hooks/pre-commit
```

Contents:

```bash
#!/bin/sh
echo "Running Gitleaks scan..."

gitleaks detect --source . --no-git --exit-code 1

if [ $? -ne 0 ]; then
  echo "❌ Gitleaks detected secrets. Commit blocked."
  exit 1
fi

echo "✅ No secrets detected."
exit 0
```

#### On Windows (Git Bash)
This works out of the box if you're using Git for Windows.

---

### Option B — PowerShell Hook

Git only ever looks for and executes a file literally named `pre-commit` (no extension) in the
hooks directory — it has no built-in way to discover or run a `.ps1`-suffixed file. `.git/hooks`
is also already git's default hooks path; running `git config core.hooksPath .git/hooks` changes
nothing. To actually run PowerShell logic, `pre-commit` itself must be a shim that invokes it:

Create `.git/hooks/pre-commit.ps1` (the real logic):

```powershell
Write-Host "Running Gitleaks scan..."

gitleaks detect --source . --no-git --exit-code 1

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Gitleaks detected secrets. Commit blocked."
    exit 1
}

Write-Host "✅ No secrets detected."
exit 0
```

Create `.git/hooks/pre-commit` (the shim git actually invokes — no extension, must be executable):

```bash
#!/bin/sh
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(dirname "$0")/pre-commit.ps1"
exit $?
```

No `core.hooksPath` change needed — this is the default path already.

---

### Option C — Using pre-commit Framework (Optional)

Install:

```powershell
pip install pre-commit
```

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.30.1  # check https://github.com/gitleaks/gitleaks/releases for the current latest
    hooks:
      - id: gitleaks
```

Enable it:

```powershell
pre-commit install
```

---

## 8. Good Practices

Always check:
```powershell
git status
git diff
```

Never commit:
- .env files
- private keys
- real credentials

---

## 9. What to Fix Immediately

🚨 Fix if you see:
- AWS / Azure / Google API keys
- Passwords in plain text
- Private keys (BEGIN PRIVATE KEY)
- Database connection strings

---

## 10. Optional: Baseline Existing Issues

```powershell
gitleaks detect --source . --no-git --report-path baseline.json
```

---

## Summary

- Gitleaks is a single EXE (no install required)
- Works on any folder
- Can block commits automatically
- Should be run before every commit

