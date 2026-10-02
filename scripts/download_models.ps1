# Download GGUF models into models/
#   - Generator: Qwen3-4B-Instruct-2507 Q4_K_M (runs on GPU)
#   - Embedder : bge-m3 Q8_0 (multilingual, runs on CPU)
# Optional:
#   -With3B   : Qwen2.5-3B-Instruct Q4_K_M, fallback generator for a tighter VRAM budget
#   -Compare  : every model used in the model-comparison benchmark (1.5B and 3B)
param([switch]$With3B, [switch]$Compare)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$dest = Join-Path $root "models"
New-Item -ItemType Directory -Force $dest | Out-Null

$models = @(
    # Instruct-2507 is the non-thinking variant: no <think> block, so TTFT stays low.
    @{ Repo = "unsloth/Qwen3-4B-Instruct-2507-GGUF"; File = "Qwen3-4B-Instruct-2507-Q4_K_M.gguf" },
    @{ Repo = "gpustack/bge-m3-GGUF";                File = "bge-m3-Q8_0.gguf" }
)
if ($With3B -or $Compare) {
    $models += @{ Repo = "Qwen/Qwen2.5-3B-Instruct-GGUF"; File = "qwen2.5-3b-instruct-q4_k_m.gguf" }
}
if ($Compare) {
    $models += @{ Repo = "Qwen/Qwen2.5-1.5B-Instruct-GGUF"; File = "qwen2.5-1.5b-instruct-q4_k_m.gguf" }
}

foreach ($m in $models) {
    $out = Join-Path $dest $m.File
    if (Test-Path $out) { Write-Host "Skip (exists): $($m.File)"; continue }
    Write-Host "Downloading $($m.Repo)/$($m.File) ..."
    # -C - : resume partial downloads
    curl.exe -L --fail -C - -s -S -o $out "https://huggingface.co/$($m.Repo)/resolve/main/$($m.File)"
}

Get-ChildItem $dest | ForEach-Object { "{0,-40} {1,8:N0} MB" -f $_.Name, ($_.Length / 1MB) }
