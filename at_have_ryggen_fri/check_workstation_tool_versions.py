#!/usr/bin/env python3
"""
check_workstation_tool_versions.py -- part of at_have_ryggen_fri.

Checks benarbejde/asset_manifest.json's workstation_tools[] (added
2026-08-08 for fyrtaarn, Robert's own BMC controller app -- see that file's
own _readme note for the full "assets[] vs workstation_tools[]" distinction)
against the real upstream GitHub release. Robert's ask, live: "have the
harness check for new versions, verify checksums, all the usual spangly
stuff."

"Verify checksums" is deliberately NOT this check's job -- neither this
check nor the manifest itself hardcodes a checksum anywhere to go stale.
Same philosophy as assets[]'s own github_release source_type (see the
manifest's own header): the 3 workstation setup scripts fetch the GitHub
Releases API's own per-asset 'digest' field fresh at actual install time and
verify against that live. This check's job is structural/freshness only:

  1. (Hard fail) Every platform asset_name the manifest lists for the
     PINNED tag actually exists in that real release right now -- a broken
     pin (renamed/removed upstream asset) is a real problem, not a nudge.
  2. (Informational, --strict promotes) The pinned tag is the real latest
     release upstream. Deliberately soft by default -- bumping the pin is a
     human decision (a brand new release might want a day of testing before
     every engineer's machine picks it up on their next setup-workstation
     run), not something to force or auto-adopt.

Same host-local network-dependency pattern as check 13 (check_mermaid.py's
kroki.io dependency) and check 17 (check_wireguard_hub_data.py's "no
independent source of truth for a pubkey" reasoning) -- GitHub API
unreachable is reported informationally, not a hard failure, since a bare
clone with no internet shouldn't be blocked by this.
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "benarbejde" / "asset_manifest.json"


def github_api(url):
    req = urllib.request.Request(url, headers={"User-Agent": "example-music-harness"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.load(resp)


def main():
    hard_failures = []
    soft_findings = []

    if not MANIFEST.exists():
        return [f"{MANIFEST.relative_to(REPO_ROOT)} does not exist."], []

    data = json.loads(MANIFEST.read_text())
    tools = data.get("workstation_tools", [])
    if not tools:
        print("No workstation_tools[] entries in the manifest -- nothing to check.")
        return [], []

    for tool in tools:
        name = tool["name"]
        repo = tool["repo"]
        tag = tool["tag"]
        assets = tool.get("assets", {})

        # -- Tier 1: pinned release actually exists and has every listed asset --
        pinned_url = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"
        try:
            pinned = github_api(pinned_url)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                hard_failures.append(f"{name}: pinned tag {tag!r} does not exist in {repo} anymore (404).")
            else:
                soft_findings.append(f"{name}: could not query {pinned_url} (HTTP {e.code}) -- network/rate-limit issue, not necessarily a real problem.")
            continue
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            soft_findings.append(f"{name}: could not reach GitHub API ({e}) -- skipping, informational only.")
            continue

        real_asset_names = {a["name"] for a in pinned.get("assets", [])}
        for platform_key, asset_name in assets.items():
            if asset_name not in real_asset_names:
                hard_failures.append(
                    f"{name}: manifest lists {asset_name!r} for {platform_key} under pinned tag {tag!r}, "
                    f"but that asset is not in the real {repo}@{tag} release anymore -- upstream renamed/removed it."
                )

        # -- Tier 2: pinned tag vs real latest (informational) --
        latest_url = f"https://api.github.com/repos/{repo}/releases/latest"
        try:
            latest = github_api(latest_url)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            soft_findings.append(f"{name}: could not query {latest_url} ({e}) -- skipping freshness check, informational only.")
            continue

        latest_tag = latest.get("tag_name")
        if latest_tag and latest_tag != tag:
            soft_findings.append(
                f"{name}: manifest pins {tag!r}, but {repo}'s real latest release is {latest_tag!r} "
                f"(published {latest.get('published_at', 'unknown date')}) -- bump the pin in "
                f"{MANIFEST.relative_to(REPO_ROOT)} when ready, not automatic."
            )

    return hard_failures, soft_findings


if __name__ == "__main__":
    strict = "--strict" in sys.argv
    hard_failures, soft_findings = main()

    if soft_findings:
        print(f"{len(soft_findings)} informational finding(s):")
        for f in soft_findings:
            print(f"  {f}")

    if hard_failures:
        print(f"{len(hard_failures)} problem(s):")
        for f in hard_failures:
            print(f"  {f}")
        sys.exit(1)

    if strict and soft_findings:
        sys.exit(1)

    if not soft_findings:
        print("Every workstation_tools[] pinned tag exists with all listed assets present and is the real latest release.")
    sys.exit(0)
