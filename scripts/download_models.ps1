# Download GGUF models into models/
#   - Generator: Qwen2.5-3B-Instruct Q4_K_M (runs on GPU)
#   - Embedder : bge-m3 Q8_0 (multilingual, runs on CPU)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$dest = Join-Path $root "models"
New-Item -ItemType Directory -Force $dest | Out-Null

$models = @(
    @{ Repo = "Qwen/Qwen2.5-3B-Instruct-GGUF"; File = "qwen2.5-3b-instruct-q4_k_m.gguf" },
    @{ Repo = "gpustack/bge-m3-GGUF";          File = "bge-m3-Q8_0.gguf" }
)

foreach ($m in $models) {
    $out = Join-Path $dest $m.File
    if (Test-Path $out) { Write-Host "Skip (exists): $($m.File)"; continue }
    Write-Host "Downloading $($m.Repo)/$($m.File) ..."
    # -C - : resume partial downloads
    curl.exe -L --fail -C - -s -S -o $out "https://huggingface.co/$($m.Repo)/resolve/main/$($m.File)"
}

Get-ChildItem $dest | ForEach-Object { "{0,-40} {1,8:N0} MB" -f $_.Name, ($_.Length / 1MB) }
