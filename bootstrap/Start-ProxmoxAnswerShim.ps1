# ==============================================================================
# Example Music Limited
#
# Start-ProxmoxAnswerShim.ps1
#
# Version History
# ---------------
# 1.0.0   2026-07-18   Initial release
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
# bootstrap tool in this repo -- test it, don't just trust the reasoning):
#   Invoke-WebRequest http://localhost:8001/proxmox/VRK-answer.toml -Method GET
#   Invoke-WebRequest http://localhost:8001/proxmox/VRK-answer.toml -Method POST
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

$ScriptVersion = '1.0.0'

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
$AnswerDirResolved = (Resolve-Path -Path $AnswerDir).Path.TrimEnd('\') + '\'

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

try {
  while ($listener.IsListening) {
    $ctx = $listener.GetContext()
    $name = $ctx.Request.Url.Segments[-1]
    $status = 404

    # Only ever serve a bare filename ending .toml, straight out of $AnswerDir --
    # no subdirectories, no traversal, nothing else on disk is reachable through this.
    if ($name -match '^[A-Za-z0-9._-]+\.toml$') {
      $file = Join-Path $AnswerDirResolved $name
      $fileResolved = [System.IO.Path]::GetFullPath($file)
      if ($fileResolved.StartsWith($AnswerDirResolved, [StringComparison]::OrdinalIgnoreCase) -and
          (Test-Path -Path $fileResolved -PathType Leaf)) {
        $bytes = [IO.File]::ReadAllBytes($fileResolved)
        $ctx.Response.ContentType = 'application/toml'
        $ctx.Response.ContentLength64 = $bytes.Length
        $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
        $status = 200
      }
    }

    $ctx.Response.StatusCode = $status
    $ctx.Response.Close()

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
