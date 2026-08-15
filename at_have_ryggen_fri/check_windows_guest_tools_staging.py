#!/usr/bin/env python3
"""
check_windows_guest_tools_staging.py -- part of at_have_ryggen_fri.

Real bug, found live 2026-08-15: bootstrap/web/windows/Detect-Platform.cmd's :KVM
label had an arm64 early-exit ("not supported, logged and skipped") that never
staged the required driver files for arm64 in the first place -- Deploy-OpenSSH.cmd
(the WinPE-phase script that stages every driver Detect-Platform.cmd later installs,
since no network is available at first boot) only ever fetched VMware Tools for
arm64, never the VirtIO/QEMU guest-agent MSIs. Fixed the same day: Detect-Platform.cmd
now installs the same amd64 virtio-win-gt-x64.msi/qemu-ga-x86_64.msi on arm64 KVM
guests too (Windows 11/Server 2025 ARM64 run amd64 MSIs fine under x64 emulation,
confirmed live by Robert -- no native arm64 build exists yet from either upstream
project), so Deploy-OpenSSH.cmd needed to start staging them for arm64 as well.

This check encodes that specific invariant so it can't silently regress again:
Detect-Platform.cmd's :KVM label installs virtio-win-gt-x64.msi and
qemu-ga-x86_64.msi UNCONDITIONALLY (no arch branch inside :KVM at all -- see
that file's own 2026-08-15 changelog entry for why), so Deploy-OpenSSH.cmd must
stage both files in BOTH its x86_64 and arm64 download blocks. If a future edit
re-adds an arch gate to either file without updating the other, this catches it.

Deliberately narrow, not a general cross-file dependency parser -- the VMware
Tools files are legitimately arch-specific (a real arm64 build exists, a real
x64 build exists, they're different binaries) and are correctly asymmetric
between the two scripts; this check doesn't touch that part.

Exit code: 0 if both required files are staged in both arch blocks, 1 otherwise.
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DETECT_PLATFORM = REPO_ROOT / "bootstrap" / "web" / "windows" / "Detect-Platform.cmd"
DEPLOY_OPENSSH = REPO_ROOT / "bootstrap" / "web" / "windows" / "Deploy-OpenSSH.cmd"

REQUIRED_KVM_FILES = ["virtio-win-gt-x64.msi", "qemu-ga-x86_64.msi"]


def kvm_installs_are_unconditional(text):
    """Confirm Detect-Platform.cmd's :KVM label still installs both files with no
    arch gate around the :MSI calls themselves -- if this ever becomes arch-gated
    again, the "must stage in both blocks" assertion below no longer applies the
    same way, and this check needs rethinking, not a silent false failure."""
    # ^:KVM$ (whole line, MULTILINE) matches the real batch-file label, not any
    # mention of the string ":KVM" in prose/comments elsewhere in the file (a real
    # bug in an earlier version of this check -- its own changelog entry mentioning
    # ":KVM" by name matched first and silently extracted the wrong block).
    m = re.search(r"^:KVM\s*$(.*?)(?=^:[A-Za-z_]+\s*$|\Z)", text, re.DOTALL | re.MULTILINE)
    if not m:
        return False, "no :KVM label found at all"
    kvm_block = m.group(1)

    # Track paren-depth of "if ... %ARCH%... (" / bare ")" lines only (not every
    # paren in the file -- e.g. %~1-style tokens elsewhere aren't parens at all,
    # and this only needs to know whether an ARCH-conditional block is open at
    # the point each :MSI call is reached, not full batch-file parsing).
    arch_if_depth = 0
    for line in kvm_block.splitlines():
        stripped = line.strip()
        if re.match(r'if\s+/i\s+"%ARCH%"==".*?"\s*\($', stripped):
            arch_if_depth += 1
            continue
        if stripped == ")" and arch_if_depth > 0:
            arch_if_depth -= 1
            continue
        for fname in REQUIRED_KVM_FILES:
            if fname in line and "call :MSI" in line:
                if arch_if_depth > 0:
                    return False, f"{fname}'s install call is inside an open arch-conditional block"

    for fname in REQUIRED_KVM_FILES:
        if not re.search(r"call :MSI \"[^\"]*" + re.escape(fname) + r"\"", kvm_block):
            return False, f"{fname} is not installed by :KVM at all"

    return True, ""


def extract_staged_files(text, arch_label):
    """Files fetched by certutil within the `if "%ARCH%"=="<arch_label>"` block."""
    m = re.search(
        r'if\s+"%ARCH%"=="' + re.escape(arch_label) + r'"\s*\((.*?)\n\)',
        text,
        re.DOTALL,
    )
    if not m:
        return set()
    block = m.group(1)
    return set(re.findall(r"certutil\.exe -urlcache -f \"[^\"]*/([^/\"]+)\"", block))


def main():
    if not DETECT_PLATFORM.is_file() or not DEPLOY_OPENSSH.is_file():
        print("Detect-Platform.cmd or Deploy-OpenSSH.cmd not found -- nothing to check.")
        return 0

    detect_text = DETECT_PLATFORM.read_text(encoding="utf-8", errors="replace")
    deploy_text = DEPLOY_OPENSSH.read_text(encoding="utf-8", errors="replace")

    ok, reason = kvm_installs_are_unconditional(detect_text)
    if not ok:
        print(f"Detect-Platform.cmd's :KVM install calls don't match the expected "
              f"unconditional shape: {reason}.")
        print("This check's assumption (both required files installed regardless of "
              "arch) may no longer hold -- review both files by hand before trusting "
              "this check's result either way.")
        return 1

    print("Confirmed: Detect-Platform.cmd's :KVM label installs both required files "
          "unconditionally (no arch gate).")

    staged_x86_64 = extract_staged_files(deploy_text, "x86_64")
    staged_arm64 = extract_staged_files(deploy_text, "arm64")

    missing = []
    for fname in REQUIRED_KVM_FILES:
        if fname not in staged_x86_64:
            missing.append(f'{fname} is not staged by Deploy-OpenSSH.cmd\'s "x86_64" block')
        if fname not in staged_arm64:
            missing.append(f'{fname} is not staged by Deploy-OpenSSH.cmd\'s "arm64" block')

    if missing:
        print(f"\n{len(missing)} issue(s) found:")
        for m in missing:
            print(f"  - {m}")
        print(
            "\nDetect-Platform.cmd installs these files on every KVM/Proxmox guest "
            "regardless of architecture -- Deploy-OpenSSH.cmd (the WinPE-phase script "
            "that stages them, since no network exists at first boot) must fetch both "
            "for both architectures too. See Detect-Platform.cmd's own 2026-08-15 "
            "changelog entry for the full reasoning."
        )
        return 1

    print(f"Both required files ({', '.join(REQUIRED_KVM_FILES)}) are staged for "
          f"both x86_64 and arm64 in Deploy-OpenSSH.cmd.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
