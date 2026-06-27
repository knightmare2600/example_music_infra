# ColorEcho GitHub Actions Build & Release Documentation

This document explains the GitHub Actions workflow used to **build ColorEcho for Windows x64 and ARM**, package the binaries, and automatically create a **GitHub Release** with both architectures included. It also breaks down each step, alternatives, and customization options.

---

## Workflow Overview

The workflow has **two jobs**:

1. **Build job**: Compiles ColorEcho for multiple architectures using MSBuild/.NET, zips the output, and uploads artifacts.
2. **Release job**: Waits for all matrix builds, downloads artifacts, creates a GitHub Release, and uploads the ZIPs as release assets.

---

## Full Workflow YAML

```yaml
name: Build and Release ColorEcho

on:
  workflow_dispatch:
  push:
    branches: [ main, master ]

jobs:
  build:
    runs-on: windows-latest
    strategy:
      matrix:
        rid: [win-x64, win-arm64]

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup MSBuild
        uses: microsoft/setup-msbuild@v1

      - name: Restore NuGet
        working-directory: src
        shell: pwsh
        run: nuget restore ColorEcho.sln

      - name: Build with MSBuild
        working-directory: src
        shell: pwsh
        run: msbuild ColorEcho.sln /p:Configuration=Release /p:Platform="Any CPU" /verbosity:minimal

      - name: Zip Artifact
        working-directory: src
        shell: pwsh
        run: |
          $zipPath = "bin\Release\ColorEcho-${{ matrix.rid }}.zip"
          if (Test-Path $zipPath) { Remove-Item $zipPath }
          Compress-Archive -Path "bin\Release\*" -DestinationPath $zipPath
          Write-Host "Zipped $zipPath"

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: ColorEcho-${{ matrix.rid }}
          path: src/bin/Release/ColorEcho-${{ matrix.rid }}.zip

  release:
    runs-on: windows-latest
    needs: build
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Download x64 artifact
        uses: actions/download-artifact@v4
        with:
          name: ColorEcho-win-x64
          path: ./artifacts/ColorEcho-win-x64

      - name: Download ARM artifact
        uses: actions/download-artifact@v4
        with:
          name: ColorEcho-win-arm64
          path: ./artifacts/ColorEcho-win-arm64

      - name: Create GitHub Release
        id: create_release
        uses: actions/create-release@v1
        with:
          tag_name: v1.0.${{ github.run_number }}
          release_name: ColorEcho v1.0.${{ github.run_number }}
          body: Automated release with x64 and ARM builds.
          draft: false
          prerelease: false
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Upload x64 Release Asset
        uses: actions/upload-release-asset@v1
        with:
          upload_url: ${{ steps.create_release.outputs.upload_url }}
          asset_path: ./artifacts/ColorEcho-win-x64/ColorEcho-win-x64.zip
          asset_name: ColorEcho-win-x64.zip
          asset_content_type: application/zip

      - name: Upload ARM Release Asset
        uses: actions/upload-release-asset@v1
        with:
          upload_url: ${{ steps.create_release.outputs.upload_url }}
          asset_path: ./artifacts/ColorEcho-win-arm64/ColorEcho-win-arm64.zip
          asset_name: ColorEcho-win-arm64.zip
          asset_content_type: application/zip
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
    rid: [win-x64, win-arm64]
```

- Defines a **matrix** of build targets: x64 and ARM.
- Each matrix entry runs **independently**, allowing parallel builds.

**Alternative:** Add `win-x86` or Linux/macOS RIDs.

------

### Checkout Step

```
- uses: actions/checkout@v4
```

- Checks out your repository code into the runner.

------

### Setup MSBuild

```
- uses: microsoft/setup-msbuild@v1
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

### Zip Artifact

```
Compress-Archive -Path "bin\Release\*" -DestinationPath $zipPath
```

- Packages compiled binaries into a **ZIP**.
- `$zipPath` includes the RID (`win-x64`, `win-arm64`) in the filename.

------

### Upload Artifact

```
uses: actions/upload-artifact@v4
```

- Uploads the ZIPs for the **release job** to use.

------

### Release Job

- **Depends on** `build` via `needs: build`.

### Download Artifact

```
uses: actions/download-artifact@v4
path: ./artifacts/ColorEcho-win-x64
```

- Downloads the ZIP into a subfolder.

------

### Create GitHub Release

```
uses: actions/create-release@v1
```

- Creates a new release with dynamic tag: `v1.0.${{ github.run_number }}`.

**Alternative:** `draft: true` for review before publishing.

------

### Upload Release Assets

```
uses: actions/upload-release-asset@v1
asset_path: ./artifacts/ColorEcho-win-x64/ColorEcho-win-x64.zip
```

- Attaches the ZIP to the release.
- Repeat for ARM artifact.

------

## Customization Examples

| Scenario                   | How to adapt                                                 |
| -------------------------- | ------------------------------------------------------------ |
| Add **x86 build**          | Add `win-x86` to the matrix                                  |
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