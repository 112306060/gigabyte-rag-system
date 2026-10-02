# Run the full benchmark once per generator model (one model loaded at a time).
# The embedding server (:8081) is left running; only the generator (:8080) is swapped.
param(
    [string[]]$Models = @(
        "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "qwen2.5-3b-instruct-q4_k_m.gguf",
        "Qwen3-4B-Instruct-2507-Q4_K_M.gguf"
    ),
    [int]$Repeat = 3
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

function Stop-Generator {
    Get-CimInstance Win32_Process -Filter "Name='llama-server.exe'" |
        Where-Object { $_.CommandLine -match "--port 8080" } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
    Start-Sleep -Seconds 2
}

foreach ($m in $Models) {
    $name = "model_" + [IO.Path]::GetFileNameWithoutExtension($m).ToLower()
    Write-Host "`n=== $m"
    Stop-Generator
    $idle = (nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits).Trim()
    & (Join-Path $PSScriptRoot "start_servers.ps1") -GenOnly -GenModel $m
    $loaded = (nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits).Trim()
    Write-Host "VRAM idle $idle MiB -> loaded $loaded MiB"
    uv run --project $root aorus-bench --name $name --repeat $Repeat
}
