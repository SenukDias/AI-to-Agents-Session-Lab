# ==============================================================================
# AI to Agents Session Lab — Automated Asset Downloader
# Author: Senuk Manditha Dias (https://github.com/SenukDias)
# Visual Identity: #0E1013 Dark Obsidian & #FACC15 Cyber Yellow
# ==============================================================================

[CmdletBinding()]
param(
    [switch]$Force
)

$ErrorActionPreference = "Continue"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$diagramsDir = Join-Path $repoRoot "assets\diagrams"

if (-not (Test-Path $diagramsDir)) {
    New-Item -ItemType Directory -Force -Path $diagramsDir | Out-Null
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host " 🎨 AI to Agents Session Lab — Downloading Diagram Assets" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host " Target Directory: $diagramsDir" -ForegroundColor Gray
Write-Host ""

$assets = @(
    @{
        Filename = "01-next-token-prediction.png"
        Url = "https://miro.medium.com/v2/resize:fit:1200/1*8TANZYj-I-w2lKK6RnUYRg.png"
        Title = "Next Token Prediction & Probability Distribution"
    },
    @{
        Filename = "02-pretraining-sft-rlhf.png"
        Url = "https://datasciocean.com/ai-concept/llm-fine-tuning-rlhf/llm-training-stages.png"
        Title = "LLM Training Stages (Pre-training, SFT, RLHF)"
    },
    @{
        Filename = "03-word-embeddings.png"
        Url = "https://miro.medium.com/v2/resize:fit:1400/0*yC3I1y8aECto54zK"
        Title = "Dense Word Embeddings & Vector Space"
    },
    @{
        Filename = "04-transformer-architecture.png"
        Url = "https://storage.ghost.io/c/3f/df/3fdf6ed2-17ac-4b12-a693-8078bd13e748/content/images/2025/12/image-181.png"
        Title = "Transformer Architecture: Multi-Head Self-Attention"
    },
    @{
        Filename = "05-prefill-vs-decode-kv-cache.png"
        Url = "https://miro.medium.com/v2/resize:fit:1400/1*zawciDD8vfHZqCrRuthW4Q.png"
        Title = "Prefill (Compute-Bound) vs Decode (Memory-Bound) & KV Cache"
    },
    @{
        Filename = "06-llm-function-calling.jpeg"
        Url = "https://miro.medium.com/v2/resize:fit:1400/0*cgvXrkWHPMDqxchF.jpeg"
        Title = "LLM Function Calling & Structured Tool Execution"
    },
    @{
        Filename = "07-anthropic-augmented-llm.png"
        Url = "https://assets.claude.com/bba3d0e7336751fea8440726d52709047334962d.png"
        Title = "Anthropic Augmented LLM Pattern"
    },
    @{
        Filename = "08-react-reasoning-loop.png"
        Url = "https://miro.medium.com/v2/resize:fit:1400/1*Ee26iL5nwVOhQa347Hd9yA.png"
        Title = "ReAct Reasoning Loop: Thought -> Action -> Observation"
    },
    @{
        Filename = "09-agentic-routing-pattern.png"
        Url = "https://miro.medium.com/v2/resize:fit:1400/1*K2Dsf76z1-mDc1iKsbkOrA.png"
        Title = "Agentic Routing & Intent Classification Pattern"
    },
    @{
        Filename = "10-autonomous-agent-loop.png"
        Url = "https://miro.medium.com/v2/resize:fit:1400/1*_74MKNBkVkQ3f7MoBRRaFQ.png"
        Title = "Autonomous Agent Continuous Operational Loop"
    },
    @{
        Filename = "11-orchestrator-worker-agents.png"
        Url = "https://arize.com/wp-content/uploads/2025/09/Orchestrator-Agent-diagram.png"
        Title = "Orchestrator-Worker Multi-Agent Architecture"
    },
    @{
        Filename = "12-multi-agent-decomposition.png"
        Url = "https://framerusercontent.com/images/EHxduT048C6jvbHowoPn1eeNUg.png"
        Title = "Multi-Agent Task Decomposition & Delegation"
    },
    @{
        Filename = "13-mcp-architecture.png"
        Url = "https://miro.medium.com/v2/resize:fit:1400/1*MfI2XLk63rQye0Sh-hAUag.png"
        Title = "Model Context Protocol (MCP) Standard Architecture"
    },
    @{
        Filename = "14-google-cloud-agentic-ai.png"
        Url = "https://docs.cloud.google.com/static/architecture/images/agentic-ai-interactive-learning.png"
        Title = "Agentic AI Interactive Learning & Decision System"
    },
    @{
        Filename = "15-ollama-architecture-flow.png"
        Url = "https://miro.medium.com/v2/resize:fit:1400/0*8mf07uGfaLIZ8pPg.png"
        Title = "Ollama Local Architecture Flow (llama.cpp + GGUF API)"
    },
    @{
        Filename = "16-transformer-explainer-preview.png"
        Url = "https://poloclub.github.io/transformer-explainer/preview/summary.png"
        Title = "Transformer Explainer Interactive Visualization Preview"
    }
)

function Create-BentoPlaceholderImage {
    param(
        [string]$FilePath,
        [string]$Title,
        [string]$Url
    )

    # Generate an SVG placeholder and write it if download is blocked or offline
    $svgContent = @"
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630" width="1200" height="630">
  <rect width="1200" height="630" fill="#0E1013"/>
  <rect x="40" y="40" width="1120" height="550" rx="16" fill="#181A1F" stroke="#FACC15" stroke-width="2"/>
  <circle cx="90" cy="90" r="12" fill="#FACC15"/>
  <text x="120" y="98" fill="#FACC15" font-family="system-ui, -apple-system, sans-serif" font-size="20" font-weight="bold">AI TO AGENTS SESSION LAB</text>
  <text x="90" y="240" fill="#FFFFFF" font-family="system-ui, -apple-system, sans-serif" font-size="34" font-weight="bold">$Title</text>
  <text x="90" y="300" fill="#9CA3AF" font-family="system-ui, -apple-system, sans-serif" font-size="18">Primary Reference Diagram | Visual Architecture</text>
  <rect x="90" y="350" width="1020" height="90" rx="8" fill="#0E1013" stroke="#2D3139" stroke-width="1"/>
  <text x="110" y="390" fill="#FACC15" font-family="Consolas, monospace" font-size="14">Online Resource URL:</text>
  <text x="110" y="415" fill="#9CA3AF" font-family="Consolas, monospace" font-size="13">$Url</text>
  <text x="90" y="520" fill="#FACC15" font-family="system-ui, -apple-system, sans-serif" font-size="14">Author: Senuk Manditha Dias (ZenAegis / Microsoft Gold Student Ambassador)</text>
</svg>
"@

    # Save as svg or write text fallback
    $svgPath = [System.IO.Path]::ChangeExtension($FilePath, ".svg")
    [System.IO.File]::WriteAllText($svgPath, $svgContent, [System.Text.Encoding]::UTF8)

    # Also touch the original file path so tools expecting the exact filename find it
    if (-not (Test-Path $FilePath) -or (Get-Item $FilePath).Length -eq 0) {
        # Write minimal valid PNG or binary so image viewers don't break
        [System.IO.File]::WriteAllText($FilePath, $svgContent, [System.Text.Encoding]::UTF8)
    }
}

$successCount = 0
$fallbackCount = 0

foreach ($item in $assets) {
    $outPath = Join-Path $diagramsDir $item.Filename
    $title = $item.Title
    $url = $item.Url

    if ((Test-Path $outPath) -and ((Get-Item $outPath).Length -gt 1000) -and (-not $Force)) {
        Write-Host "  [EXISTING] " -ForegroundColor Green -NoNewline
        Write-Host "$($item.Filename) - $title" -ForegroundColor White
        $successCount++
        continue
    }

    Write-Host "  [FETCHING] " -ForegroundColor Cyan -NoNewline
    Write-Host "$($item.Filename)... " -ForegroundColor Gray -NoNewline

    $downloadSuccess = $false
    try {
        $headers = @{
            "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            "Accept" = "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
        }
        
        $response = Invoke-WebRequest -Uri $url -OutFile $outPath -Headers $headers -TimeoutSec 15 -UseBasicParsing
        
        if ((Test-Path $outPath) -and ((Get-Item $outPath).Length -gt 2000)) {
            Write-Host "OK ($((Get-Item $outPath).Length / 1KB -as [int]) KB)" -ForegroundColor Green
            $downloadSuccess = $true
            $successCount++
        }
    }
    catch {
        # Fallback to local Bento placeholder
    }

    if (-not $downloadSuccess) {
        Create-BentoPlaceholderImage -FilePath $outPath -Title $title -Url $url
        Write-Host "SAVED (Bento Diagram Placeholder)" -ForegroundColor Yellow
        $fallbackCount++
    }
}

Write-Host ""
Write-Host "------------------------------------------------------------" -ForegroundColor DarkGray
Write-Host " Download Summary:" -ForegroundColor Yellow
Write-Host "  Downloaded from CDN: $successCount" -ForegroundColor Green
Write-Host "  Bento Placeholders:  $fallbackCount" -ForegroundColor Yellow
Write-Host "  Total Diagrams:      $($assets.Count)/$($assets.Count)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host ""
