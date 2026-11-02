#!/usr/bin/env python3
"""
check_asset_manifest_freshness.py -- part of at_have_ryggen_fri.

Checks benarbejde/asset_manifest.json's assets[] entries with
source_type == "github_release" against the real upstream GitHub release --
the klargoring/saekkevogn/pakhus/Spejder family (pinned tag "latest", so
they always auto-track upstream's newest release) plus wimboot/
ipxe-arm64-sb.iso (pinned to a literal tag instead).

This closes backlog item 2 (PLAN-harness-and-bootstrap-backlog-2026-08-06.md,
"Spin-off repo release tracking"): the manifest's own 2026-08-06 changelog
entry records a real incident this check exists to catch automatically going
forward -- klargoring's upstream renamed its release assets from a bare
'vmlinuz' to 'vmlinuz-amd64'/'vmlinuz-arm64', silently breaking every fetch
until someone noticed by hand. Nothing previously checked these entries at
all. The backlog doc's other half -- fyrtaarn -- turned out to already be
done: workstation_tools[] (added 2026-08-08, same manifest) plus the sibling
check_workstation_tool_versions.py already cover it; that backlog entry was
just stale (written 2026-08-06, two days before the fix landed).

Same two-tier shape as check_workstation_tool_versions.py, deliberately not
sharing code with it -- that check's key shape is name+assets{} (one tool,
many platforms); this one is dest+asset_name (one entry, one platform/file),
so a shared helper would cost more in indirection than it saves:

  1. (Hard fail) The asset_name the manifest lists for this entry's tag
     actually exists in that real release right now -- tag "latest" resolves
     to /releases/latest, a literal tag to /releases/tags/<tag>. A broken
     fetch (upstream renamed/removed the asset) is a real problem, not a
     nudge.
  2. (Informational, --strict promotes) Only for entries pinned to a literal
     tag, not "latest" -- there's no drift concept for an entry that always
     tracks newest by design: is the pinned tag the real latest release.

archives[] is out of scope -- none of its entries use source_type
"github_release" (they're url_with_checksum_file or plain url+members,
unrelated upstreams). workstation_tools[] is out of scope too -- that's
check_workstation_tool_versions.py's job, not duplicated here.

Same host-local network-dependency pattern as check 13/17/37 -- GitHub API
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
    entries = [a for a in data.get("assets", []) if a.get("source_type") == "github_release"]
    if not entries:
        print("No assets[] entries with source_type github_release -- nothing to check.")
        return [], []

    for entry in entries:
        dest = entry["dest"]
        repo = entry["repo"]
        tag = entry["tag"]
        asset_name = entry["asset_name"]

        tag_url = (f"https://api.github.com/repos/{repo}/releases/latest" if tag == "latest"
                   else f"https://api.github.com/repos/{repo}/releases/tags/{tag}")
        try:
            release = github_api(tag_url)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                hard_failures.append(f"{dest}: tag {tag!r} does not exist in {repo} anymore (404).")
            else:
                soft_findings.append(f"{dest}: could not query {tag_url} (HTTP {e.code}) -- network/rate-limit issue, not necessarily a real problem.")
            continue
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            soft_findings.append(f"{dest}: could not reach GitHub API ({e}) -- skipping, informational only.")
            continue

        real_asset_names = {a["name"] for a in release.get("assets", [])}
        if asset_name not in real_asset_names:
            hard_failures.append(
                f"{dest}: manifest lists asset_name {asset_name!r} for {repo}@{tag!r}, "
                f"but that asset is not in the real release anymore -- upstream renamed/removed it."
            )

        if tag == "latest":
            continue  # no drift concept -- this entry always tracks newest by design

        latest_url = f"https://api.github.com/repos/{repo}/releases/latest"
        try:
            latest = github_api(latest_url)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            soft_findings.append(f"{dest}: could not query {latest_url} ({e}) -- skipping freshness check, informational only.")
            continue

        latest_tag = latest.get("tag_name")
        if latest_tag and latest_tag != tag:
            soft_findings.append(
                f"{dest}: manifest pins {tag!r}, but {repo}'s real latest release is {latest_tag!r} "
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
        print("Every assets[] github_release entry's asset_name exists in its real release, and every literally-pinned tag is the real latest.")
    sys.exit(0)
