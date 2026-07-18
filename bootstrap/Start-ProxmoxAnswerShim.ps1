# ==============================================================================
# Example Music Limited
#
# Start-ProxmoxAnswerShim.ps1
#
# Version History
# ---------------
# 1.0.0   2026-07-18   Initial release
# 1.0.1   2026-07-19   First real test against pwsh 7 (Robert installed it specifically
#                       to test this) found three genuine bugs the original never caught,
#                       written but never run: (1) the resolved-directory path hardcoded
#                       a literal backslash separator, which is only correct on Windows --
#                       on pwsh Core, Join-Path then produced a path with a stray
#                       backslash inside it, and every single request 500'd on
#                       ReadAllBytes; (2) that exception (and any other per-request
#                       exception) was completely unguarded, so it took the whole accept
#                       loop down after the very first request -- confirmed live, every
#                       request after the first got connection-refused; (3) a malformed
#                       request (a bodyless POST, which .NET's own HttpListener rejects
#                       with 411 before this script's code runs) left the response object
#                       already disposed, and setting StatusCode/calling Close() on it
#                       threw too, unguarded a second time, still taking the loop down
#                       even after fix (2). Fixed all three: path resolution now uses
#                       [System.IO.Path] helpers instead of a hardcoded separator, and
#                       the entire per-request body (both the handler logic and the
#                       response finalisation) is now wrapped so nothing in this loop can
#                       propagate out and kill it. Also fixed the header's own POST test
#                       command -- it never carried a body either, so it was testing the
#                       411 edge case, not the do_POST-equivalent path this script exists
#                       for.
#
# Purpose
# -------
# static-web-server(-x64).exe already does the real job of the provisioning
# server -- multithreaded, directory listings, serving /debian, /alpine, /proxmox,
# etc -- and this script does not try to replace it. The one thing it categorically
# can't do is answer Proxmox VE's automated installer, which fetches its answer.toml
# via HTTP POST rather than GET when booted with proxmox-fetch-from-url (it sends the
# node's system properties as the POST body, so the answer file's [[match]] filters
# can key off them) -- SWS, like every other plain static file server, only answers
# GET/HEAD, so that fetch comes back as an error and the installer drops to a shell
# for a manual `wget` instead (see docs/bootstrap/bootstrapping.md 6.3 -- this is
# documented as expected behaviour today, precisely because nothing serves the POST).
#
# This script is the narrow fix, not a full replacement: a small HttpListener loop,
# on its own port, serving only the handful of small *.toml answer files out of one
# directory. Leave SWS running exactly as it is on its own port for everything else;
# point Proxmox's proxmox-fetch-from-url at this shim's port/path instead for the
# VRK/FRD answer files specifically. Request volume during a provisioning run is a
# handful of fetches, not a sustained load -- a single-threaded accept loop is
# genuinely fine for that, not a corner cut.
#
# Usage
# -----
#   .\Start-ProxmoxAnswerShim.ps1 -AnswerDir C:\path\to\proxmox -Port 8001
#
#   Then point the installer at, e.g.:
#     http://192.168.139.50:8001/proxmox/VRK-answer.toml
#     http://192.168.139.50:8001/proxmox/VRK-degraded.toml
#
# Verify before trusting it for a real install (same principle as every other
# bootstrap tool in this repo -- test it, don't just trust the reasoning; this one
# was tested live with pwsh 7 on 2026-07-19, see the changelog below for what that
# actually found):
#   Invoke-WebRequest http://localhost:8001/proxmox/VRK-answer.toml -Method GET
#   Invoke-WebRequest http://localhost:8001/proxmox/VRK-answer.toml -Method POST -Body '{}'
#
# The -Body '{}' on the POST test isn't cosmetic -- a POST with no body at all has no
# Content-Length, and .NET's own HttpListener auto-rejects that with 411 Length
# Required before this script's code ever runs, which is a meaningless test of what
# this script actually does (the real Proxmox installer's POST always carries a
# system-properties JSON body, so it always has one). Testing with a real body is
# what actually exercises the do_POST-equivalent path this script exists for.
#   Both should return 200 with the TOML body.
#
# Requires running as (or with) a principal allowed to reserve the URL ACL for
# http://+:<port>/ -- either an elevated PowerShell session, or a one-time
#   netsh http add urlacl url=http://+:8001/proxmox/ user=<you>
# run in advance. HttpListener throws "Access is denied" at Start() otherwise --
# this is a genuine Windows HTTP.sys requirement, not a bug in this script.
#
# ==============================================================================

#Requires -Version 5.1

param(
  [Parameter(Mandatory = $true)]
  [string]$AnswerDir,

  [int]$Port = 8001,

  [string]$UrlPrefix = 'proxmox'
)

$ScriptVersion = '1.0.1'

if (-not (Test-Path -Path $AnswerDir -PathType Container)) {
  Write-Host "Directory not found: $AnswerDir" -ForegroundColor Red
  exit 1
}

# Resolve once, up front -- every request's target path is checked against this
# so a crafted URL segment (../../whatever) can never escape $AnswerDir. Url.Segments
# already collapses "../" during .NET's own URI parsing in the common case, but this
# is the one part of the script that turns attacker-influenced input (the request URL)
# into a filesystem path, so it gets its own explicit belt-and-braces check rather than
# relying on that alone.
#
# BUG FIX (2026-07-19, caught live against real pwsh 7 once it was installed to test
# with -- not by reading): the original TrimEnd('\') + '\' hardcoded the Windows path
# separator. On pwsh Core (Linux/macOS -- a genuinely supported PowerShell runtime,
# not a hypothetical), Join-Path then produced a path with a literal backslash
# *inside* it instead of a real separator, so ReadAllBytes threw "Could not find a
# part of the path" on every single request -- uncaught (see the try/catch added
# below), which killed the whole listener after the very first hit. Using
# [System.IO.Path]::TrimEndingDirectorySeparator() and leaving Join-Path to add the
# platform-correct separator itself fixes this on every OS pwsh actually runs on, not
# just the one this was originally written against.
$AnswerDirResolved = [System.IO.Path]::TrimEndingDirectorySeparator((Resolve-Path -Path $AnswerDir).Path)

$Prefix = "http://+:$Port/$UrlPrefix/"
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add($Prefix)

try {
  $listener.Start()
} catch {
  Write-Host "Failed to start listener on $Prefix -- $($_.Exception.Message)" -ForegroundColor Red
  Write-Host "If this is 'Access is denied', reserve the URL ACL first:" -ForegroundColor Yellow
  Write-Host "  netsh http add urlacl url=$Prefix user=$env:USERNAME" -ForegroundColor Yellow
  exit 1
}

Write-Host "Example Music Limited -- Start-ProxmoxAnswerShim.ps1 v$ScriptVersion" -ForegroundColor Cyan
Write-Host "Proxmox answer-file shim listening on $Prefix" -ForegroundColor Cyan
Write-Host "Serving *.toml from: $AnswerDirResolved" -ForegroundColor Cyan
Write-Host 'Press Ctrl+C to stop.' -ForegroundColor Cyan

# Belt-and-braces containment check, used per-request below: fileResolved must fall
# strictly inside $AnswerDirResolved, not just share it as a textual prefix (a bare
# StartsWith("/tmp/foo") would wrongly accept "/tmp/foobar/x.toml" too) -- comparing
# against the directory PLUS its trailing separator closes that gap.
$AnswerDirWithSep = $AnswerDirResolved + [System.IO.Path]::DirectorySeparatorChar

try {
  while ($listener.IsListening) {
    $ctx = $listener.GetContext()
    $status = 500

    # BUG FIX (2026-07-19): this whole block used to run with no try/catch of its
    # own -- caught live via pwsh once it was actually available to test with:
    # the path-separator bug above threw on the very first request, and with
    # nothing catching it here, that exception unwound straight out of the while
    # loop entirely, taking the whole listener down after one hit (confirmed:
    # every request after the first got a bare connection-refused, and no
    # per-request log line ever printed, not even for the request that crashed
    # it). A shim that's supposed to sit and answer requests for the length of a
    # provisioning run must not die because one request hit an edge case --
    # caught here now, logged, answered 500, and the loop keeps going.
    try {
      $name = $ctx.Request.Url.Segments[-1]
      $status = 404

      # Only ever serve a bare filename ending .toml, straight out of $AnswerDir --
      # no subdirectories, no traversal, nothing else on disk is reachable through this.
      if ($name -match '^[A-Za-z0-9._-]+\.toml$') {
        $file = Join-Path $AnswerDirResolved $name
        $fileResolved = [System.IO.Path]::GetFullPath($file)
        if ($fileResolved.StartsWith($AnswerDirWithSep, [StringComparison]::OrdinalIgnoreCase) -and
            (Test-Path -Path $fileResolved -PathType Leaf)) {
          $bytes = [IO.File]::ReadAllBytes($fileResolved)
          $ctx.Response.ContentType = 'application/toml'
          $ctx.Response.ContentLength64 = $bytes.Length
          $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
          $status = 200
        }
      }
    } catch {
      $status = 500
      Write-Host "Error handling $($ctx.Request.Url.AbsolutePath): $($_.Exception.Message)" -ForegroundColor Red
    }

    # BUG FIX (2026-07-19, same live pwsh test as above): a malformed request (e.g. a
    # POST with no Content-Length and no body -- .NET's own HttpListener auto-rejects
    # this with 411 and disposes the response object before our code ever touches it,
    # confirmed live) leaves $ctx.Response already closed. Setting StatusCode/calling
    # Close() on an already-disposed response threw here too, completely unguarded --
    # and because this sat AFTER the try/catch above, that exception still took the
    # whole accept loop down, even with the fix above in place. Wrapped separately so
    # there is no line left in this loop, at all, that can propagate out and kill it.
    try {
      $ctx.Response.StatusCode = $status
      $ctx.Response.Close()
    } catch {
      # Response already finalised by the framework itself -- nothing left to do.
    }

    # HttpListener doesn't log to screen the way http.server/SWS do by default --
    # one manual line per request so this shim's activity is actually visible.
    Write-Host "$($ctx.Request.RemoteEndPoint) - $($ctx.Request.HttpMethod) $($ctx.Request.Url.AbsolutePath) - $status"
  }
} finally {
  # Always release the URL reservation on exit (Ctrl+C included, via the finally
  # block) -- an HttpListener left started would keep the port bound after the
  # script's own console session is gone.
  $listener.Stop()
  $listener.Close()
}
