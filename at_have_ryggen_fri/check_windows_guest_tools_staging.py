#!/usr/bin/env python3
"""
check_windows_guest_tools_staging.py -- part of at_have_ryggen_fri.

Real bug, found live 2026-08-15: bootstrap/web/windows/Detect-Platform.cmd's :KVM
label had an arm64 early-exit ("not supported, logged and skipped") that never
staged the required driver files for arm64 in the first place -- Deploy-OpenSSH.cmd
(the WinPE-phase script that stages every driver Detect-Platform.cmd later installs,
since no network is available at first boot) only ever fetched VMware Tools for
arm64, never the VirtIO/QEMU guest-agent MSIs.

Fixed in two passes the same day:
  1.1.0 (Detect-Platform.cmd) / 1.4.0 (Deploy-OpenSSH.cmd): arm64 KVM guests
  install the same amd64 MSIs as x86_64, under Windows' built-in x64 emulation
  (no native arm64 build existed at the time).
  1.2.0 / 1.5.0: real native arm64 MSIs turned up the same day
  (github.com/knightmare2600/virtio-win-guest-tools-installer, arm64-preview-0.1.0,
  verified for real -- PE header machine field of the binaries inside confirmed
  genuine ARM64 code). :KVM now tries the native MSIs first and falls back to the
  amd64-under-emulation path if either is missing or fails, since the native
  release is explicitly experimental/untested on real hardware. The native
  downloads are best-effort in Deploy-OpenSSH.cmd (a failure there logs a warning
  and continues); the amd64 fallback files are NOT optional -- they're the safety
  net the whole design depends on, so Deploy-OpenSSH.cmd must always stage them
  for arm64 too, same as it always has for x86_64.

This check encodes that specific invariant so it can't silently regress again:
Deploy-OpenSSH.cmd's arm64 block must stage BOTH amd64 fallback files
(virtio-win-gt-x64.msi, qemu-ga-x86_64.msi), same as its x86_64 block always has.
Whether the native arm64 files are also staged is checked and reported, but not
enforced -- their absence is an explicitly tolerated, handled state (see
Detect-Platform.cmd's own `if exist` guard around them), not a bug.

Deliberately narrow, not a general cross-file dependency parser -- the VMware
Tools files are legitimately arch-specific (a real arm64 build exists, a real
x64 build exists, they're different binaries) and are correctly asymmetric
between the two scripts; this check doesn't touch that part.

Second half, added 2026-08-15 same day (Robert: "add some additional harness
checks to ensure they are in place, and if not, grab them"): the two native
arm64 MSIs are committed directly into this repo (bootstrap/web/windows/arm64/,
git-lfs -- NOT one of benarbejde/asset_manifest.json's fetch-on-demand assets,
those exist specifically for things deliberately NOT vendored into git, and
these two now are). "Grab them if missing" in this context means detecting a
checkout that never pulled the real LFS content (a common, easy-to-hit state --
see this repo's own git-stash-and-lfs caution precedent) and telling the
operator `git lfs pull`, not fetching from an external URL -- there's nothing
external to fetch from for a vendored file. Checks the file is present AND is
not a raw, unresolved LFS pointer stub (~130 bytes of text starting
"version https://git-lfs.github.com/spec/v1", not a real multi-MB MSI).

Exit code: 0 if both amd64 fallback files are staged for both x86_64 and arm64
in Deploy-OpenSSH.cmd, AND both native arm64 MSIs are present as real,
LFS-resolved files. 1 otherwise.
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEPLOY_OPENSSH = REPO_ROOT / "bootstrap" / "web" / "windows" / "Deploy-OpenSSH.cmd"
ARM64_DIR = REPO_ROOT / "bootstrap" / "web" / "windows" / "arm64"

REQUIRED_FALLBACK_FILES = ["virtio-win-gt-x64.msi", "qemu-ga-x86_64.msi"]
OPTIONAL_NATIVE_FILES = ["virtio-win-gt-arm64.msi", "qemu-ga-arm64.msi"]
LFS_POINTER_SIGNATURE = b"version https://git-lfs.github.com/spec/v1"


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
    if not DEPLOY_OPENSSH.is_file():
        print("Deploy-OpenSSH.cmd not found -- nothing to check.")
        return 0

    deploy_text = DEPLOY_OPENSSH.read_text(encoding="utf-8", errors="replace")

    staged_x86_64 = extract_staged_files(deploy_text, "x86_64")
    staged_arm64 = extract_staged_files(deploy_text, "arm64")

    missing = []
    for fname in REQUIRED_FALLBACK_FILES:
        if fname not in staged_x86_64:
            missing.append(f'{fname} is not staged by Deploy-OpenSSH.cmd\'s "x86_64" block')
        if fname not in staged_arm64:
            missing.append(f'{fname} is not staged by Deploy-OpenSSH.cmd\'s "arm64" block '
                            f'-- this is the mandatory amd64 fallback, not optional')

    if missing:
        print(f"{len(missing)} issue(s) found:")
        for m in missing:
            print(f"  - {m}")
        print(
            "\nBoth architectures need the amd64 fallback files staged -- x86_64 installs "
            "them directly, arm64 falls back to them if the native arm64 MSIs are missing "
            "or fail to install. See Detect-Platform.cmd's own 1.2.0 changelog entry for "
            "the full reasoning."
        )
        return 1

    print(f"Required amd64 fallback files ({', '.join(REQUIRED_FALLBACK_FILES)}) are staged "
          f"for both x86_64 and arm64 in Deploy-OpenSSH.cmd.")

    native_staged = [f for f in OPTIONAL_NATIVE_FILES if f in staged_arm64]
    if native_staged:
        print(f"Native arm64 MSIs also staged (optional, best-effort): {', '.join(native_staged)}")
    else:
        print("Native arm64 MSIs not staged (optional -- Detect-Platform.cmd falls back to "
              "amd64 cleanly if they're absent, this is not a failure).")

    lfs_missing = []
    for fname in OPTIONAL_NATIVE_FILES:
        fpath = ARM64_DIR / fname
        if not fpath.is_file():
            lfs_missing.append(f"{fname} does not exist at {fpath.relative_to(REPO_ROOT)}")
            continue
        with fpath.open("rb") as f:
            head = f.read(len(LFS_POINTER_SIGNATURE))
        if head == LFS_POINTER_SIGNATURE:
            lfs_missing.append(
                f"{fname} is an unresolved git-lfs pointer stub, not the real MSI"
            )

    if lfs_missing:
        print(f"\n{len(lfs_missing)} issue(s) found with the vendored native arm64 MSIs:")
        for m in lfs_missing:
            print(f"  - {m}")
        print(
            "\nBoth MSIs are committed directly into this repo via git-lfs "
            f"({ARM64_DIR.relative_to(REPO_ROOT)}/) -- they are not fetched on demand the way "
            "benarbejde/asset_manifest.json's assets are, that file is explicitly scoped to "
            "assets NOT vendored into git. Run `git lfs pull` to fetch the real content, then "
            "re-run this check."
        )
        return 1

    print(f"Both native arm64 MSIs ({', '.join(OPTIONAL_NATIVE_FILES)}) are present in "
          f"{ARM64_DIR.relative_to(REPO_ROOT)}/ as real, LFS-resolved content.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
