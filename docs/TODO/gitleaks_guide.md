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

## 6. Reduce False Positives (.gitleaksignore)

Create a file called:

.gitleaksignore

Example:

```
# Ignore test files
test-data/
*.example

# Ignore known fake keys
FAKE_API_KEY_123456

# Ignore hashes in documentation
docs/
```

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

Create:

```
.git/hooks/pre-commit.ps1
```

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

Then configure Git to use PowerShell hooks:

```powershell
git config core.hooksPath .git/hooks
```

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
    rev: v8.18.0
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

