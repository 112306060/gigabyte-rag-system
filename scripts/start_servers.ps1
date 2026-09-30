# Start the two llama.cpp servers used by the RAG pipeline.
#   :8080  generator  Qwen2.5-3B-Instruct Q4_K_M, fully on GPU
#   :8081  embedder   bge-m3 Q8_0, CPU only (keeps the 4GB VRAM budget for generation)
param(
    [string]$GenModel = "qwen2.5-3b-instruct-q4_k_m.gguf",
    [int]$Ctx = 4096,
    [switch]$GenOnly,
    [switch]$EmbedOnly
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$server = Join-Path $root "bin\llama.cpp\llama-server.exe"
$models = Join-Path $root "models"
$logs = Join-Path $root "logs"
New-Item -ItemType Directory -Force $logs | Out-Null

function Start-Llama($name, $argList) {
    $p = Start-Process -FilePath $server -ArgumentList $argList -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logs "$name.out.log") `
        -RedirectStandardError (Join-Path $logs "$name.err.log")
    Write-Host "$name started (pid $($p.Id))"
}

function Wait-Healthy($port) {
    for ($i = 0; $i -lt 120; $i++) {
        try {
            if ((Invoke-RestMethod "http://127.0.0.1:$port/health" -TimeoutSec 2).status -eq "ok") { return }
        } catch {}
        Start-Sleep -Milliseconds 500
    }
    throw "server on :$port did not become healthy (see logs/)"
}

if (-not $EmbedOnly) {
    # -ngl 99 : offload all layers to GPU
    # -np 1   : single slot (one user) -> only one KV cache is allocated
    Start-Llama "gen" @("-m", (Join-Path $models $GenModel), "-ngl", "99", "-c", "$Ctx", "-np", "1",
                       "--host", "127.0.0.1", "--port", "8080")
    Wait-Healthy 8080
}
if (-not $GenOnly) {
    # --device none : hide the GPU entirely. With only -ngl 0 the CUDA build still creates a
    #                 CUDA context and offloads large matmuls, costing ~450 MiB of VRAM.
    # -ub 8192      : embeddings (non-causal) need the whole input in one micro-batch
    Start-Llama "embed" @("-m", (Join-Path $models "bge-m3-Q8_0.gguf"), "--embedding", "--pooling", "cls",
                          "--device", "none", "-c", "8192", "-b", "8192", "-ub", "8192", "-np", "1",
                          "--host", "127.0.0.1", "--port", "8081")
    Wait-Healthy 8081
}
Write-Host "ready."
