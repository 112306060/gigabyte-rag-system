# Run the same experiment set on every generator model, so models are compared under
# identical conditions (prompt v1/v2/v3 + retrieval ablations).
# Each model is loaded alone on :8080 and verified via /v1/models before benchmarking.
param(
    [hashtable]$Models = [ordered]@{
        "qwen2.5-1.5b" = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
        "qwen2.5-3b"   = "qwen2.5-3b-instruct-q4_k_m.gguf"
        "qwen3-4b"     = "Qwen3-4B-Instruct-2507-Q4_K_M.gguf"
    },
    # name suffix -> extra benchmark args
    [hashtable]$Configs = [ordered]@{
        "prompt-v1"  = @("--prompt", "v1")
        "prompt-v2"  = @("--prompt", "v2")
        "prompt-v3"  = @("--prompt", "v3")
        "no-prune"   = @("--no-prune", "--repeat", "1")
        "dense"      = @("--mode", "dense", "--repeat", "1")
        "bm25"       = @("--mode", "bm25", "--repeat", "1")
    },
    [switch]$SkipExisting
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

function Stop-Generator {
    Get-CimInstance Win32_Process -Filter "Name='llama-server.exe'" |
        Where-Object { $_.CommandLine -match "--port 8080" } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
    Start-Sleep -Seconds 2
}

foreach ($short in $Models.Keys) {
    $file = $Models[$short]
    $todo = @($Configs.Keys | Where-Object {
        -not ($SkipExisting -and (Test-Path (Join-Path $root "eval\results\${short}_$_.json")))
    })
    if ($todo.Count -eq 0) { Write-Host "=== $short : all results exist, skipping"; continue }

    Write-Host "`n=== $short ($file)"
    Stop-Generator
    & (Join-Path $PSScriptRoot "start_servers.ps1") -GenOnly -GenModel $file
    $served = Split-Path -Leaf (Invoke-RestMethod "http://127.0.0.1:8080/v1/models").data[0].id
    if ($served -ne $file) { throw "expected $file on :8080 but server reports $served" }

    foreach ($cfg in $todo) {
        $name = "${short}_$cfg"
        Write-Host "--- $name"
        uv run --project $root aorus-bench --name $name @($Configs[$cfg]) |
            Select-String -Pattern "overall accuracy|correct refusal|E2E TTFT" | ForEach-Object { "    " + $_.Line }
    }
}
