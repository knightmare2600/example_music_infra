# ------------------------------------------------------
# Detect CPU architecture and select the correct folder
# Works in PowerShell 5.1 (Windows PowerShell) and 7+
# ------------------------------------------------------

# Detect architecture
if ($PSVersionTable.PSVersion.Major -ge 6) {
    # PowerShell 7+ (cross-platform .NET Core)
    $arch = [System.Runtime.InteropServices.RuntimeInformation]::ProcessArchitecture.ToString().ToLower()
} else {
    # PowerShell 5.1 (Windows PowerShell)
    switch ($env:PROCESSOR_ARCHITECTURE) {
        'AMD64' { $arch = 'x86_64' }
        'ARM64' { $arch = 'arm64' }
        'x86'   { $arch = 'x86' }
        default { $arch = 'unknown' }
    }
}

# Set the path to the architecture-specific folder
$archPath = Join-Path -Path $PSScriptRoot -ChildPath $arch

# Debug output
Write-Host "Detected architecture: $arch"
Write-Host "Using binaries from folder: $archPath"

# Example: running a binary dynamically
# & "$archPath\RemoteDesktop_1.2.6228.0_$arch.msi"