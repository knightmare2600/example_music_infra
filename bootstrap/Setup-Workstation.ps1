#Requires -Version 5.1
<#
==============================================================================
bootstrap/Setup-Workstation.ps1
Example Music Limited — Engineer workstation setup (Windows)
==============================================================================
Three jobs, one script:
  1. Install/confirm the tool set docs/ExampleMusic_Beginners_Guide.md §11
     requires on an engineer's own machine, via Chocolatey.
  2. Install pinned-version workstation tools (currently: fyrtaarn, Robert's
     own BMC controller app) from benarbejde/asset_manifest.json's
     workstation_tools[] -- checksum-verified against the GitHub Releases
     API, reinstalled automatically if the installed binary doesn't match
     the manifest's pinned tag. Installed to C:\Tools\<name>\, added to the
     Machine PATH.
  3. Populate bootstrap/web/'s upstream-sourced boot assets from
     benarbejde/asset_manifest.json's assets[]/archives[] -- the same job
     ansible/playbooks/bootstrap_assets/fetch-assets.yml used to do. Ported
     natively to PowerShell because ansible-playbook cannot run on Windows
     at all (a hard, long-standing Ansible limitation, not a repo gap) --
     this is the whole reason these 3 platform scripts exist instead of one
     Ansible playbook.

Ported from the already live-tested bootstrap/setup-workstation-linux.sh /
setup-workstation-macos.sh -- same three checksum-verified fetch
strategies, NOT redesigned from scratch. Companion scripts:
  bootstrap/setup-workstation-linux.sh    (apt, live-tested)
  bootstrap/setup-workstation-macos.sh    (Homebrew, fetch logic live-tested)
Deliberately a separate file, not folded into either bash script, despite
the real logical overlap -- Robert's explicit instruction.

*** IMPORTANT -- NO WINDOWS AVAILABLE, BUT THE FETCH LOGIC WAS REAL-TESTED ***
This environment has no Windows at all -- but PowerShell Core (`pwsh`) turns
out to be installed on the Linux box that built this, and PowerShell Core
is genuinely cross-platform, so the asset-fetch functions below (JSON
manifest parsing, GitHub Release API calls, checksum-file extraction,
Get-FileHash verification, Expand-Archive) were actually parsed
(`[System.Management.Automation.Language.Parser]::ParseFile`, zero syntax
errors) AND executed for real against live sources -- fetched and
correctly SHA256-verified the real wimboot binary via `Invoke-RestMethod` +
`Get-FileHash`, extracted the correct hash from OpenBSD's real BSD-format
checksum file, and round-tripped a synthetic multi-member zip through
`Expand-Archive` end to end, all producing byte-correct results. This is
real execution proof for the fetch logic, not just careful reasoning.

What's still genuinely unverified, because it's Windows-only and nothing
here can exercise it: the actual Chocolatey install/package steps, the
`curl.exe`-vs-`curl`-alias distinction (Linux has no `curl.exe` to test
against), the elevation check (`WindowsIdentity`/`WindowsPrincipal` throw
`PlatformNotSupportedException` outside Windows), and the real
`$env:LOCALAPPDATA`/Windows Terminal settings paths. Chocolatey package IDs
were checked against Chocolatey's own package pages/search results, not
guessed from memory, but the actual `choco install` runs themselves are
unexercised. Malcolm, Jamie, or Robert: please run this for real on real
Windows and report back anything in the Windows-only parts that doesn't
match.

Presumes Windows PowerShell 5.1 (built into every Windows 10/11 box, no
install needed to reach that starting point) as the shell this is first
invoked under. One of this script's own jobs is installing PowerShell Core
(`pwsh`) via Chocolatey for later sessions -- it does not require Core to
already be present to run itself.

Download strategy (this is where "iwr or curl" actually matters, per
Robert's own framing):
  - `curl` is a BUILT-IN ALIAS for Invoke-WebRequest in Windows PowerShell
    5.1 -- typing `curl` does NOT call the real curl.exe. This script
    always calls `curl.exe` explicitly (the .exe suffix bypasses the
    alias and reaches the genuine curl binary Windows 10 1803+ ships in
    System32) for actual file downloads -- curl.exe has no progress-bar
    overhead at all, simplest fix.
  - For API/text calls that need the response parsed (GitHub's Release
    API, checksum-file text), Invoke-RestMethod is used instead --
    it returns already-parsed data and does not have the same
    progress-bar slowdown Invoke-WebRequest has (that bug is specific to
    Invoke-WebRequest's own per-byte progress rendering; Invoke-RestMethod
    was never affected).
  - `$ProgressPreference = 'SilentlyContinue'` is still set globally at
    the top of this script as a defensive belt-and-braces measure, in case
    any cmdlet anywhere in here ends up rendering a progress bar --
    Windows PowerShell 5.1's default per-byte progress rendering on
    Invoke-WebRequest is a real, well-documented, severe slowdown (can
    turn a fast download into one taking many minutes); fixed outright in
    PowerShell Core, not in 5.1.

Idempotent: every dependency check/install and every asset fetch is
skip-if-already-correct. Safe to re-run any time.

Windows Terminal's settings.json can contain comments (JSONC), which
ConvertFrom-Json cannot parse -- rewriting an EXISTING settings.json
programmatically risks corrupting a real user's config this script has no
way to inspect first. Deliberately conservative here: only writes a fresh
settings.json if none exists yet (a genuinely first-run install); if one
already exists, prints manual instructions instead of touching it.

Usage:
  .\bootstrap\Setup-Workstation.ps1                # deps + assets
  .\bootstrap\Setup-Workstation.ps1 -DepsOnly       # skip asset fetch
  .\bootstrap\Setup-Workstation.ps1 -AssetsOnly     # skip dependency install

Chocolatey package installs need an elevated (Administrator) PowerShell --
this script checks for elevation and exits with a clear message if it
isn't, rather than failing partway through with a confusing permissions
error.
==============================================================================
Changelog:
  2026-07-27  Initial file. Fetch logic ported from
              ansible/playbooks/bootstrap_assets/fetch-assets.yml (live-
              tested against every real source this manifest covers) via
              setup-workstation-linux.sh (also live-tested) -- same URLs,
              same tags, same checksum strategy, not re-researched from
              scratch. Chocolatey package IDs for microsoft-windows-terminal
              and nerd-fonts-jetbrainsmono confirmed against Chocolatey's
              own package pages before use, not assumed from memory. Parsed
              with zero syntax errors via
              [System.Management.Automation.Language.Parser]::ParseFile,
              and the cross-platform fetch functions (JSON parsing,
              Invoke-RestMethod, Get-FileHash, Expand-Archive) were actually
              executed for real under PowerShell Core on Linux -- correct
              results against live wimboot/OpenBSD sources and a synthetic
              multi-member zip. Windows-only parts (Chocolatey, curl.exe,
              elevation check, Windows Terminal paths) remain unverified.
  2026-08-08  Added Install-WorkstationTools (job 2, fyrtaarn) -- same
              Get-Sha256/Invoke-RestMethod/curl.exe pattern as the asset-fetch
              functions below. Installs to C:\Tools\<name>\<name>.exe
              (matching docs/gitleaks_guide.md's existing manual convention)
              and registers it on the Machine PATH -- safe at Machine scope
              since Install-Dependencies already enforces an elevated session
              before this ever runs.
  2026-08-10  Added winevdm to the package list -- Robert's ask, 16-bit
              Windows app compatibility layer. Confirmed as a real, current
              Chocolatey package (0.8.1 on the community feed) before adding.
==============================================================================
#>

[CmdletBinding()]
param(
    [switch]$DepsOnly,
    [switch]$AssetsOnly
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'  # see header -- defensive, belt-and-braces

$DoDeps = -not $AssetsOnly
$DoAssets = -not $DepsOnly

# -- Paths ---------------------------------------------------------------------
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path -Parent $ScriptDir
$Manifest  = Join-Path $RepoRoot 'benarbejde\asset_manifest.json'
$WebDir    = Join-Path $RepoRoot 'bootstrap\web'
$CacheDir  = Join-Path $RepoRoot '.cache\bootstrap_asset_fetch'

# -- Colour helpers (matches this repo's existing CY/GN/YW/RD convention, --
# -- see e.g. bootstrap/web/proxmox/select-pve-answer.sh) ----------------------
function Write-Info  { param([string]$Message) Write-Host "[*] $Message" -ForegroundColor Cyan }
function Write-Ok    { param([string]$Message) Write-Host "[+] $Message" -ForegroundColor Green }
function Write-Warn2 { param([string]$Message) Write-Host "[!] $Message" -ForegroundColor Yellow }
function Write-Err2  { param([string]$Message) Write-Host "[x] $Message" -ForegroundColor Red }

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# ==============================================================================
# 1. Dependency install
# ==============================================================================
function Install-Dependencies {
    Write-Info "Checking Chocolatey-based dependencies..."

    if (-not (Test-IsAdministrator)) {
        Write-Err2 "This must run in an elevated (Administrator) PowerShell -- Chocolatey installs need it."
        Write-Err2 "Right-click PowerShell/Windows Terminal and 'Run as Administrator', then re-run this script."
        exit 1
    }

    if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
        Write-Info "Chocolatey not found -- installing (official install script)."
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
        # Refresh PATH in this session so `choco` resolves without reopening the shell.
        $env:Path = [System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path', 'User')
    }

    $packages = @(
        'git',
        'git-lfs',
        'keepassxc',
        'putty',                        # bundles PSCP/PSFTP/Pageant/PuTTYgen
        'winscp',
        'pstools',
        'microsoft-windows-terminal',   # confirmed real package ID, 2026-07-27
        'nerd-fonts-jetbrainsmono',      # confirmed real package ID, 2026-07-27 -- NOT the deprecated JetBrainsMonoNF
        'powershell-core',
        'winevdm'                        # 16-bit Windows app compatibility layer, Robert's ask, 2026-08-10
    )
    choco install -y @packages

    git lfs install

    Write-Ok "Dependencies installed/confirmed: $($packages -join ', ')."
    Set-PowerShellProfiles
    Set-WindowsTerminalFont
}

function Set-PowerShellProfiles {
    Write-Info "Configuring PowerShell profiles (Windows PowerShell 5.1 and Core)..."

    $profileSnippet = @'

# Example Music Limited -- Nerd Font glyph support for Windows Terminal.
# Added by bootstrap/Setup-Workstation.ps1 -- safe to remove or edit freely.
$OutputEncoding = [System.Text.Encoding]::UTF8
'@

    # $PROFILE here resolves to WHICHEVER host this script is currently
    # running under (Windows PowerShell 5.1, per this script's own
    # presumption -- see header). Append-if-missing, never overwrite --
    # this may be a real, already-customised profile.
    Add-ProfileSnippetIfMissing -ProfilePath $PROFILE -Snippet $profileSnippet

    # PowerShell Core's own $PROFILE is a DIFFERENT path/host -- ask pwsh
    # itself rather than hardcoding the convention, since it can vary
    # (WindowsPowerShell vs PowerShell folder under Documents).
    $pwsh = Get-Command pwsh -ErrorAction SilentlyContinue
    if ($pwsh) {
        $corePath = & pwsh -NoLogo -NoProfile -Command '$PROFILE'
        Add-ProfileSnippetIfMissing -ProfilePath $corePath -Snippet $profileSnippet
    } else {
        Write-Warn2 "pwsh not found on PATH yet (may need a new shell session after this Chocolatey install) -- PowerShell Core's profile wasn't configured this run. Re-run with -DepsOnly after opening a new terminal if this matters."
    }
}

function Add-ProfileSnippetIfMissing {
    param([string]$ProfilePath, [string]$Snippet)

    $dir = Split-Path -Parent $ProfilePath
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    if (Test-Path $ProfilePath) {
        $existing = Get-Content $ProfilePath -Raw
        if ($existing -match [regex]::Escape('Example Music Limited -- Nerd Font glyph support')) {
            Write-Info "  ${ProfilePath}: already configured, skipping."
            return
        }
    }
    Add-Content -Path $ProfilePath -Value $Snippet
    Write-Ok "  ${ProfilePath}: updated."
}

function Set-WindowsTerminalFont {
    # Store-packaged Windows Terminal's settings.json (choco's
    # microsoft-windows-terminal package installs the same MSIX package,
    # same path convention).
    $settingsPath = Join-Path $env:LOCALAPPDATA 'Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json'

    if (Test-Path $settingsPath) {
        Write-Warn2 "Windows Terminal already has a settings.json -- NOT touching it automatically" `
                     "(it can contain comments, which would break a naive JSON round-trip and risks" `
                     "corrupting a real existing config this script can't safely inspect first)."
        Write-Warn2 "Set the font by hand: Settings -> Defaults -> Appearance -> Font face -> 'JetBrainsMono Nerd Font'."
        return
    }

    Write-Info "No existing Windows Terminal settings.json -- writing a fresh one with the Nerd Font set as default."
    $settingsDir = Split-Path -Parent $settingsPath
    New-Item -ItemType Directory -Path $settingsDir -Force | Out-Null
    $freshSettings = @{
        '$schema' = 'https://aka.ms/terminal-profiles-schema'
        profiles  = @{ defaults = @{ font = @{ face = 'JetBrainsMono Nerd Font' } } }
    }
    $freshSettings | ConvertTo-Json -Depth 5 | Set-Content -Path $settingsPath -Encoding UTF8
    Write-Ok "  Wrote ${settingsPath}."
}

# ==============================================================================
# 2. Workstation tools -- benarbejde/asset_manifest.json's workstation_tools[]
#    (added 2026-08-08, Robert -- real locally-run tools, not boot assets;
#    see that file's own _readme note for the full reasoning)
# ==============================================================================
# Deliberately NOT the same "skip if already exists" idempotency as
# Invoke-GithubReleaseFetch below -- these are pinned-version tools a harness
# check nudges Robert to bump over time (check_workstation_tool_versions.py),
# and a bumped pin needs to actually take effect on the next run without a
# manual delete first. Verifies the INSTALLED binary's checksum against the
# manifest's pinned tag/asset every run and only reinstalls on mismatch.
# Installs to C:\Tools\<name>\<name>.exe, matching this repo's existing
# C:\Tools\<name>\ convention (see docs/gitleaks_guide.md) -- and adds
# C:\Tools\<name>\ to the Machine PATH so the tool runs bare, not just via
# full path. Machine-scope is safe here: this whole script already requires
# an elevated session (Test-IsAdministrator, checked before this ever runs).
function Install-WorkstationTools {
    if (-not (Test-Path $Manifest)) {
        Write-Err2 "Manifest not found: $Manifest"
        exit 1
    }

    $goarch = switch ($env:PROCESSOR_ARCHITECTURE) {
        'AMD64' { 'amd64' }
        'ARM64' { 'arm64' }
        default {
            Write-Warn2 "Unrecognised architecture $($env:PROCESSOR_ARCHITECTURE) -- skipping workstation_tools install (no matching asset)."
            return
        }
    }
    $platformKey = "windows-$goarch"

    $data = Get-Content $Manifest -Raw | ConvertFrom-Json
    foreach ($tool in $data.workstation_tools) {
        $name = $tool.name
        $repo = $tool.repo
        $tag = $tool.tag
        $assetName = $tool.assets.$platformKey
        if (-not $assetName) {
            Write-Warn2 "${name}: no asset for $platformKey in the manifest -- skipping."
            continue
        }

        $installDir = "C:\Tools\$name"
        $installPath = Join-Path $installDir "$name.exe"

        Write-Info "Checking $name ($repo@$tag, $platformKey)..."

        $apiUrl = "https://api.github.com/repos/$repo/releases/tags/$tag"
        try {
            $meta = Invoke-RestMethod -Uri $apiUrl -Headers @{ 'User-Agent' = 'example-music-setup-workstation' }
        } catch {
            Write-Err2 "  Failed to query $apiUrl"
            continue
        }
        $asset = $meta.assets | Where-Object { $_.name -eq $assetName }
        if (-not $asset) {
            Write-Err2 "  Asset '$assetName' not found in $repo@$tag's release"
            continue
        }
        $expectedHash = ($asset.digest -replace '^sha256:', '')

        if (Test-Path $installPath) {
            $currentHash = Get-Sha256 -Path $installPath
            if ($currentHash -eq $expectedHash) {
                Write-Ok "  $name already at $tag (sha256:$currentHash)"
                continue
            }
            Write-Info "  Installed $name doesn't match pinned $tag -- reinstalling."
        }

        New-Item -ItemType Directory -Path $installDir -Force | Out-Null
        & curl.exe -fsSL -o $installPath $asset.browser_download_url

        $actualHash = Get-Sha256 -Path $installPath
        if ($actualHash -ne $expectedHash) {
            Write-Err2 "  CHECKSUM MISMATCH for ${name}: expected $expectedHash, got $actualHash"
            Remove-Item $installPath -Force
            continue
        }
        Write-Ok "  $name installed to $installPath ($tag, sha256:$actualHash)"

        $machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
        if (($machinePath -split ';') -notcontains $installDir) {
            [Environment]::SetEnvironmentVariable('Path', "$machinePath;$installDir", 'Machine')
            $env:Path = "$env:Path;$installDir"
            Write-Ok "  Added $installDir to the Machine PATH."
        }
    }
}

# ==============================================================================
# 3. Asset fetch -- three source_type handlers, matching
#    benarbejde/asset_manifest.json's own header exactly
# ==============================================================================

function Get-Sha256 {
    param([string]$Path)
    return (Get-FileHash -Path $Path -Algorithm SHA256).Hash.ToLower()
}

function Invoke-GithubReleaseFetch {
    param([string]$Dest, [string]$Repo, [string]$Tag, [string]$AssetName)

    $fullDest = Join-Path $WebDir $Dest
    if (Test-Path $fullDest) { return }

    $apiUrl = if ($Tag -eq 'latest') {
        "https://api.github.com/repos/$Repo/releases/latest"
    } else {
        "https://api.github.com/repos/$Repo/releases/tags/$Tag"
    }

    Write-Info "Fetching $Dest ($Repo@$Tag)..."

    $meta = Invoke-RestMethod -Uri $apiUrl -Headers @{ 'User-Agent' = 'example-music-setup-workstation' }
    $asset = $meta.assets | Where-Object { $_.name -eq $AssetName }
    if (-not $asset) {
        Write-Err2 "  Asset '$AssetName' not found in $Repo@$Tag's release"
        throw "Asset not found: $AssetName"
    }
    $expectedHash = ($asset.digest -replace '^sha256:', '')

    $destDir = Split-Path -Parent $fullDest
    New-Item -ItemType Directory -Path $destDir -Force | Out-Null

    & curl.exe -fsSL -o $fullDest $asset.browser_download_url

    $actualHash = Get-Sha256 -Path $fullDest
    if ($expectedHash -and ($actualHash -ne $expectedHash)) {
        Write-Err2 "  CHECKSUM MISMATCH for ${Dest}: expected $expectedHash, got $actualHash"
        Remove-Item $fullDest -Force
        throw "Checksum mismatch: $Dest"
    }
    Write-Ok "  $Dest (sha256:$actualHash)"
}

function Invoke-UrlWithChecksumFileFetch {
    param([string]$Dest, [string]$Url, [string]$ChecksumFileUrl, [string]$ChecksumFileEntry)

    $fullDest = Join-Path $WebDir $Dest
    if (Test-Path $fullDest) { return }

    Write-Info "Fetching $Dest..."

    $checksumText = Invoke-RestMethod -Uri $ChecksumFileUrl

    # Format-agnostic on purpose -- see benarbejde/asset_manifest.json's own
    # header. A SHA256 hash is always a 64-hex-char string regardless of
    # whether the surrounding line reads "<hash>  <path>" (GNU, Debian's
    # SHA256SUMS) or "SHA256 (<file>) = <hash>" (BSD, OpenBSD's SHA256).
    $matchingLine = ($checksumText -split "`n") | Where-Object { $_ -like "*$ChecksumFileEntry*" } | Select-Object -First 1
    if (-not $matchingLine) {
        Write-Err2 "  Could not find a checksum line for '$ChecksumFileEntry' in $ChecksumFileUrl"
        throw "Checksum entry not found: $ChecksumFileEntry"
    }
    $hashMatch = [regex]::Match($matchingLine, '[0-9a-fA-F]{64}')
    if (-not $hashMatch.Success) {
        Write-Err2 "  No 64-hex-char SHA256 found on the matching line for '$ChecksumFileEntry'"
        throw "Checksum not found on matching line: $ChecksumFileEntry"
    }
    $expectedHash = $hashMatch.Value.ToLower()

    $destDir = Split-Path -Parent $fullDest
    New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    & curl.exe -fsSL -o $fullDest $Url

    $actualHash = Get-Sha256 -Path $fullDest
    if ($actualHash -ne $expectedHash) {
        Write-Err2 "  CHECKSUM MISMATCH for ${Dest}: expected $expectedHash, got $actualHash"
        Remove-Item $fullDest -Force
        throw "Checksum mismatch: $Dest"
    }
    Write-Ok "  $Dest (sha256:$actualHash)"
}

function Invoke-ArchiveFetch {
    param([string]$Url, [array]$Members, [string]$ChecksumFileUrl, [string]$ChecksumFileEntry)
    # Members: array of @{archive_path=...; dest=...}. ChecksumFileUrl empty/$null = skip verification.

    $anyMissing = $false
    foreach ($m in $Members) {
        if (-not (Test-Path (Join-Path $WebDir $m.dest))) { $anyMissing = $true }
    }
    if (-not $anyMissing) { return }

    # SourceForge (and some other hosts) serve real download links ending in
    # a trailing /download segment, not a filename -- strip it before
    # deriving a local filename. The ACTUAL curl.exe request below still
    # uses the real, unmodified $Url -- SourceForge genuinely needs that
    # suffix to serve the file at all.
    $archiveFilename = Split-Path -Leaf ($Url -replace '/download/?$', '')

    New-Item -ItemType Directory -Path $CacheDir -Force | Out-Null
    $archiveLocal = Join-Path $CacheDir $archiveFilename
    $extractDir = Join-Path $CacheDir "extracted\$archiveFilename.d"

    Write-Info "Fetching archive $archiveFilename..."
    & curl.exe -fsSL -o $archiveLocal $Url

    if ($ChecksumFileUrl) {
        # Format-agnostic on purpose -- see Invoke-UrlWithChecksumFileFetch above /
        # benarbejde/asset_manifest.json's own header.
        $checksumText = Invoke-RestMethod -Uri $ChecksumFileUrl
        $matchingLine = ($checksumText -split "`n") | Where-Object { $_ -like "*$ChecksumFileEntry*" } | Select-Object -First 1
        if (-not $matchingLine) {
            Write-Err2 "  Could not find a checksum line for '$ChecksumFileEntry' in $ChecksumFileUrl"
            Remove-Item $archiveLocal -Force
            throw "Checksum entry not found: $ChecksumFileEntry"
        }
        $hashMatch = [regex]::Match($matchingLine, '[0-9a-fA-F]{64}')
        if (-not $hashMatch.Success) {
            Write-Err2 "  No 64-hex-char SHA256 found on the matching line for '$ChecksumFileEntry'"
            Remove-Item $archiveLocal -Force
            throw "Checksum not found on matching line: $ChecksumFileEntry"
        }
        $expectedHash = $hashMatch.Value.ToLower()
        $actualHash = Get-Sha256 -Path $archiveLocal
        if ($actualHash -ne $expectedHash) {
            Write-Err2 "  CHECKSUM MISMATCH for ${archiveFilename}: expected $expectedHash, got $actualHash"
            Remove-Item $archiveLocal -Force
            throw "Checksum mismatch: $archiveFilename"
        }
    }

    New-Item -ItemType Directory -Path $extractDir -Force | Out-Null
    Expand-Archive -Path $archiveLocal -DestinationPath $extractDir -Force

    foreach ($m in $Members) {
        $fullDest = Join-Path $WebDir $m.dest
        if (Test-Path $fullDest) { continue }
        $destDir = Split-Path -Parent $fullDest
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        # archive_path uses forward slashes in the manifest (matches the
        # Unix-built zip's own internal paths) -- Join-Path handles this
        # fine on Windows, but normalise explicitly for clarity.
        $srcInArchive = Join-Path $extractDir ($m.archive_path -replace '/', '\')
        Copy-Item -Path $srcInArchive -Destination $fullDest -Force
        Write-Ok "  $($m.dest) (from $archiveFilename)"
    }

    Remove-Item -Path $CacheDir -Recurse -Force
}

function Get-MissingAssets {
    if (-not (Test-Path $Manifest)) {
        Write-Err2 "Manifest not found: $Manifest"
        exit 1
    }
    Write-Info "Reading $Manifest..."

    $data = Get-Content $Manifest -Raw | ConvertFrom-Json

    foreach ($asset in ($data.assets | Where-Object { $_.source_type -eq 'github_release' })) {
        Invoke-GithubReleaseFetch -Dest $asset.dest -Repo $asset.repo -Tag $asset.tag -AssetName $asset.asset_name
    }

    foreach ($asset in ($data.assets | Where-Object { $_.source_type -eq 'url_with_checksum_file' })) {
        Invoke-UrlWithChecksumFileFetch -Dest $asset.dest -Url $asset.url `
            -ChecksumFileUrl $asset.checksum_file_url -ChecksumFileEntry $asset.checksum_file_entry
    }

    foreach ($archive in ($data.archives)) {
        Invoke-ArchiveFetch -Url $archive.url -Members $archive.members `
            -ChecksumFileUrl $archive.checksum_file_url -ChecksumFileEntry $archive.checksum_file_entry
    }

    Write-Ok "Asset fetch complete."
}

# ==============================================================================
if ($DoDeps)   { Install-Dependencies }
if ($DoDeps)   { Install-WorkstationTools }
if ($DoAssets) { Get-MissingAssets }
Write-Ok "Done."
