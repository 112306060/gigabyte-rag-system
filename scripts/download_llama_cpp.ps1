# Download prebuilt llama.cpp (Windows, CUDA) into bin/llama.cpp/
# Pinned to a specific build so results are reproducible.
param(
    [string]$Build = "b11276",
    [string]$Cuda = "13.4"
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$dest = Join-Path $root "bin\llama.cpp"
New-Item -ItemType Directory -Force $dest | Out-Null

function Invoke-Native([scriptblock]$cmd) {
    # Native tools (curl, llama-server) write progress to stderr. With "Stop", Windows
    # PowerShell 5.1 turns redirected stderr lines into terminating errors, so relax it
    # here and check the exit code instead.
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try { & $cmd } finally { $ErrorActionPreference = $prev }
    if ($LASTEXITCODE -ne 0) { throw "command failed with exit code $LASTEXITCODE" }
}

$base = "https://github.com/ggml-org/llama.cpp/releases/download/$Build"
$assets = @(
    "llama-$Build-bin-win-cuda-$Cuda-x64.zip",  # llama-server.exe etc.
    "cudart-llama-bin-win-cuda-$Cuda-x64.zip"   # CUDA runtime DLLs (no CUDA Toolkit install needed)
)

foreach ($a in $assets) {
    $zip = Join-Path $env:TEMP $a
    if (-not (Test-Path $zip)) {
        Write-Host "Downloading $a ..."
        # Download to .part and rename only when complete, so an interrupted download is
        # resumed (-C -) instead of being mistaken for a finished file.
        Invoke-Native { curl.exe -L --fail -sS -C - -o "$zip.part" "$base/$a" }
        Move-Item "$zip.part" $zip -Force
    }
    Write-Host "Extracting $a ..."
    Expand-Archive -Path $zip -DestinationPath $dest -Force
}

# llama-server prints its version to stderr; merge it in cmd so PowerShell shows plain text.
$exe = Join-Path $dest "llama-server.exe"
Invoke-Native { cmd /c "`"$exe`" --version 2>&1" | Write-Host }
