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

$base = "https://github.com/ggml-org/llama.cpp/releases/download/$Build"
$assets = @(
    "llama-$Build-bin-win-cuda-$Cuda-x64.zip",  # llama-server.exe etc.
    "cudart-llama-bin-win-cuda-$Cuda-x64.zip"   # CUDA runtime DLLs (no CUDA Toolkit install needed)
)

foreach ($a in $assets) {
    $zip = Join-Path $env:TEMP $a
    if (-not (Test-Path $zip)) {
        Write-Host "Downloading $a ..."
        curl.exe -L --fail -o $zip "$base/$a"
    }
    Write-Host "Extracting $a ..."
    Expand-Archive -Path $zip -DestinationPath $dest -Force
}

& (Join-Path $dest "llama-server.exe") --version
