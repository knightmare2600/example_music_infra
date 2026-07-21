# ColorEcho GitHub Actions Build & Release Documentation

This document explains the GitHub Actions workflow used to **build ColorEcho for Windows x64 and ARM**, package the binaries, and automatically create a **GitHub Release** with both architectures included. It also breaks down each step, alternatives, and customization options.

---

## Workflow Overview

The workflow has **two jobs**:

1. **Build job**: Compiles ColorEcho for multiple architectures using MSBuild/.NET, zips the output, and uploads artifacts.
2. **Release job**: Waits for all matrix builds, downloads artifacts, creates a GitHub Release, and uploads the ZIPs as release assets.

---

## Full Workflow YAML

> Verified 2026-07-21 against the live workflow file (`master` branch) — the version below was
> stale (missing the `win-x86` matrix target entirely, and used `actions/create-release`/
> `actions/upload-release-asset`, both archived/deprecated by GitHub years ago). Replaced with an
> exact, current copy.

```yaml
name: Build and Release ColorEcho

on:
  workflow_dispatch:
  push:
    branches: [ main, master ]

# Future-proof Node 24 opt-in (prevents deprecation warnings)
env:
  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true

jobs:
  build:
    runs-on: windows-2025

    strategy:
      matrix:
        rid: [win-x86, win-x64, win-arm64]

    steps:
      - name: Checkout
        uses: actions/checkout@v5

      - name: Setup MSBuild
        uses: microsoft/setup-msbuild@v2

      - name: Restore NuGet
        working-directory: src
        shell: pwsh
        run: nuget restore ColorEcho.sln

      - name: Build with MSBuild
        working-directory: src
        shell: pwsh
        run: msbuild ColorEcho.sln /p:Configuration=Release /p:Platform="Any CPU" /verbosity:minimal

      - name: Create ZIP
        working-directory: src
        shell: pwsh
        run: |
          $outDir = "bin\Release"
          $zipPath = "$outDir\ColorEcho-${{ matrix.rid }}.zip"

          if (Test-Path $zipPath) {
            Remove-Item $zipPath -Force
          }

          Compress-Archive -Path "$outDir\*" -DestinationPath $zipPath
          Write-Host "Created $zipPath"

      - name: Upload artifact
        uses: actions/upload-artifact@v5
        with:
          name: ColorEcho-${{ matrix.rid }}
          path: src/bin/Release/ColorEcho-${{ matrix.rid }}.zip
          if-no-files-found: error


  release:
    runs-on: windows-2025
    needs: build

    steps:
      - name: Checkout
        uses: actions/checkout@v5

      - name: Download artifacts
        uses: actions/download-artifact@v5
        with:
          path: ./artifacts
          merge-multiple: true

      - name: Create Release
        uses: softprops/action-gh-release@v2
        with:
          tag_name: v1.0.${{ github.run_number }}
          name: ColorEcho v1.0.${{ github.run_number }}
          body: |
            Automated release:
            - win-x86
            - win-x64
            - win-arm64

          files: |
            ./artifacts/ColorEcho-win-x86.zip
            ./artifacts/ColorEcho-win-x64.zip
            ./artifacts/ColorEcho-win-arm64.zip
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Step-by-Step Breakdown

### Trigger Section

```
on:
  workflow_dispatch:
  push:
    branches: [ main, master ]
```

- **`workflow_dispatch`**: Allows manual triggering from GitHub UI.
- **`push`**: Automatically triggers on pushes to `main` or `master`.

**Alternative:** Add `pull_request:` or `schedule:` for PRs or cron jobs.

------

### Build Job

```
strategy:
  matrix:
    rid: [win-x86, win-x64, win-arm64]
```

- Defines a **matrix** of build targets: x86, x64, and ARM.
- Each matrix entry runs **independently**, allowing parallel builds.

**Alternative:** Add Linux/macOS RIDs.

------

### Checkout Step

```
- uses: actions/checkout@v5
```

- Checks out your repository code into the runner.

------

### Setup MSBuild

```
- uses: microsoft/setup-msbuild@v2
```

- Ensures the **full .NET Framework MSBuild** is available.
- Needed for **non-SDK-style projects**.

**Alternative:** For SDK-style projects, use `actions/setup-dotnet@v4`.

------

### Restore NuGet

```
- run: nuget restore ColorEcho.sln
```

- Restores all NuGet packages required for the project.

------

### Build

```
- run: msbuild ColorEcho.sln /p:Configuration=Release /p:Platform="Any CPU"
```

- Compiles the project in **Release mode**.

**Alternative:** SDK-style projects use:

```
dotnet publish ColorEcho.csproj -c Release -r win-x64 --self-contained true
```

------

### Create ZIP

```
Compress-Archive -Path "$outDir\*" -DestinationPath $zipPath
```

- Packages compiled binaries into a **ZIP**.
- `$zipPath` includes the RID (`win-x86`, `win-x64`, `win-arm64`) in the filename.

------

### Upload Artifact

```
uses: actions/upload-artifact@v5
```

- Uploads the ZIPs for the **release job** to use.
- `if-no-files-found: error` fails the job loudly if the zip step didn't actually produce a file.

------

### Release Job

- **Depends on** `build` via `needs: build`.

### Download Artifacts

```
uses: actions/download-artifact@v5
with:
  path: ./artifacts
  merge-multiple: true
```

- Downloads **all** matrix artifacts in one step, flattened into a single `./artifacts` directory
  (`merge-multiple: true`) — not one separate download step per RID.

------

### Create GitHub Release

```
uses: softprops/action-gh-release@v2
```

- Creates a release with dynamic tag `v1.0.${{ github.run_number }}` **and** uploads all three
  ZIPs in the same step (`files:` list) — the old two-step create-then-upload pattern
  (`actions/create-release` + `actions/upload-release-asset`) is gone; both of those actions were
  archived/deprecated by GitHub some time ago.

**Alternative:** add `draft: true` for review before publishing.

------

## Customization Examples

| Scenario                   | How to adapt                                                 |
| -------------------------- | ------------------------------------------------------------ |
| Add another RID             | Add it to the matrix (`win-x86`/`win-x64`/`win-arm64` are already all built) |
| Switch to **Linux builds** | `runs-on: ubuntu-latest` and RIDs like `linux-x64`           |
| Use **Go instead of .NET** | Replace MSBuild + NuGet with `go build -o bin/ColorEcho-${{ matrix.rid }}` |
| Add **macOS build**        | `runs-on: macos-latest`, RIDs: `osx-x64` / `osx-arm64`       |
| Make **draft releases**    | Set `draft: true` in `create-release`                        |
| Automatic **versioning**   | Use Git tags: `tag_name: ${{ github.ref_name }}`             |

------

## Notes & Tips

1. **Matrix builds** allow parallel compilation → faster workflow.
2. **Artifacts** are temporary but necessary for cross-job file transfer.
3. **Always verify paths**: download folder vs upload path mismatch is a common failure.
4. **Full .NET Framework** is required for non-SDK-style projects; SDK-style .NET Core/6+ uses `dotnet publish`.
5. Extra **environment variables** per build can be added (`DOTNET_ROOT`, `MSBuildSDKsPath`, etc.).

------

## Summary

This workflow is **fully automatic**:

- Push → Build x64 + ARM
- Artifacts uploaded → release waits for both
- Creates **GitHub Release** → attaches both binaries

It’s flexible, expandable for:

- Additional architectures
- Different OSes
- Other programming languages

This is a **production-ready release pipeline** for ColorEcho and similar projects.