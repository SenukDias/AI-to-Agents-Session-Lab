# ==============================================================================
# AI to Agents Session Lab — Production Repository Verification Suite
# Author: Senuk Manditha Dias (https://github.com/SenukDias)
# Visual Identity: #0E1013 Dark Obsidian & #FACC15 Cyber Yellow
# ==============================================================================

[CmdletBinding()]
param()

$ErrorActionPreference = "Continue"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir

$totalChecks = 0
$passedChecks = 0
$failedChecks = 0
$warningsCount = 0

function Report-Pass {
    param([string]$Message)
    $global:totalChecks++
    $global:passedChecks++
    Write-Host "  [ PASS ] " -ForegroundColor Green -NoNewline
    Write-Host $Message -ForegroundColor White
}

function Report-Fail {
    param([string]$Message)
    $global:totalChecks++
    $global:failedChecks++
    Write-Host "  [ FAIL ] " -ForegroundColor Red -NoNewline
    Write-Host $Message -ForegroundColor Yellow
}

function Report-Warn {
    param([string]$Message)
    $global:totalChecks++
    $global:warningsCount++
    Write-Host "  [ WARN ] " -ForegroundColor DarkYellow -NoNewline
    Write-Host $Message -ForegroundColor Gray
}

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Yellow
Write-Host "  🔍 AI TO AGENTS SESSION LAB — REPOSITORY INTEGRITY VERIFIER" -ForegroundColor Yellow
Write-Host "================================================================================" -ForegroundColor Yellow
Write-Host "  Repository Path: $repoRoot" -ForegroundColor Gray
Write-Host ""

# ------------------------------------------------------------------------------
# Check 1: Mandatory Core Files Existence & Non-Empty
# ------------------------------------------------------------------------------
Write-Host " [1/6] Auditing Core Repository Files..." -ForegroundColor Cyan

$requiredFiles = @(
    "README.md",
    "TROUBLESHOOTING.md",
    "CHEATSHEET.md",
    "_config.yml",
    "index.html",
    "requirements.txt",
    ".env.example",
    ".gitignore",
    "Modelfile",
    "labs\lab-00-setup-and-cpu-tuning.md",
    "labs\lab-01-llm-theory-and-tokens.md",
    "labs\lab-02-prompt-to-answer-pipeline.md",
    "labs\lab-03-ollama-cli-and-modelfile.md",
    "labs\lab-04-react-agent-from-scratch.md",
    "labs\lab-05-agentic-task-scheduling.md",
    "exercises\ex01_token_explorer.py",
    "exercises\ex02_prefill_decode_benchmark.py",
    "exercises\ex03_custom_modelfile_client.py",
    "exercises\ex04_react_agent_loop.py",
    "exercises\ex05_scheduled_autonomous_agent.py",
    "solutions\sol01_token_explorer.py",
    "solutions\sol02_prefill_decode_benchmark.py",
    "solutions\sol03_custom_modelfile_client.py",
    "solutions\sol04_react_agent_loop.py",
    "solutions\sol05_scheduled_autonomous_agent.py",
    "scripts\doctor.py",
    "scripts\download-assets.ps1",
    "scripts\verify-repo.ps1",
    "assets\bento\hero-banner.svg",
    "assets\bento\prompt-to-answer-animated.svg",
    "assets\bento\react-scheduler-animated.svg"
)

foreach ($relPath in $requiredFiles) {
    $fullPath = Join-Path $repoRoot $relPath
    if (-not (Test-Path $fullPath)) {
        Report-Fail "Missing required file: $relPath"
    }
    else {
        $size = (Get-Item $fullPath).Length
        if ($size -lt 20) {
            Report-Fail "File exists but is empty or truncated ($size bytes): $relPath"
        }
        else {
            Report-Pass "Found: $relPath ($size bytes)"
        }
    }
}

# ------------------------------------------------------------------------------
# Check 2: Python Compilation & Syntax Validation
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host " [2/6] Verifying Python Script Syntax (python -m py_compile)..." -ForegroundColor Cyan

$pythonScripts = @(
    "exercises\ex01_token_explorer.py",
    "exercises\ex02_prefill_decode_benchmark.py",
    "exercises\ex03_custom_modelfile_client.py",
    "exercises\ex04_react_agent_loop.py",
    "exercises\ex05_scheduled_autonomous_agent.py",
    "solutions\sol01_token_explorer.py",
    "solutions\sol02_prefill_decode_benchmark.py",
    "solutions\sol03_custom_modelfile_client.py",
    "solutions\sol04_react_agent_loop.py",
    "solutions\sol05_scheduled_autonomous_agent.py",
    "scripts\doctor.py"
)

foreach ($pyRel in $pythonScripts) {
    $fullPyPath = Join-Path $repoRoot $pyRel
    if (Test-Path $fullPyPath) {
        $compileProc = Start-Process -FilePath "python" -ArgumentList "-m", "py_compile", "`"$fullPyPath`"" -NoNewWindow -Wait -PassThru
        if ($compileProc.ExitCode -eq 0) {
            Report-Pass "Syntax valid: $pyRel"
        }
        else {
            Report-Fail "Python compilation error in: $pyRel (ExitCode $($compileProc.ExitCode))"
        }
    }
}

# ------------------------------------------------------------------------------
# Check 3: Microsoft Learn Student Ambassador Tracking Rule
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host " [3/6] Auditing Microsoft Learn Tracking Tags (?wt.mc_id=studentamb_296178)..." -ForegroundColor Cyan

$trackingPattern = "wt\.mc_id=studentamb_296178"
$docFiles = Get-ChildItem -Path $repoRoot -Recurse -Include *.md, *.html | Where-Object { $_.FullName -notmatch "\\venv\\" -and $_.FullName -notmatch "\\\.git\\" }

$totalMsLinks = 0
$compliantMsLinks = 0

foreach ($file in $docFiles) {
    $content = Get-Content -Path $file.FullName -Raw -Encoding UTF8
    $matches = [regex]::Matches($content, 'https?://learn\.microsoft\.com[^\s\)"\x27]+')
    foreach ($m in $matches) {
        $totalMsLinks++
        $url = $m.Value
        if ($url -match $trackingPattern) {
            $compliantMsLinks++
        }
        else {
            Report-Fail "Missing tracking ID in $($file.Name): $url"
        }
    }
}

if ($totalMsLinks -eq 0) {
    Report-Warn "No learn.microsoft.com links discovered."
}
elseif ($compliantMsLinks -eq $totalMsLinks) {
    Report-Pass "All $totalMsLinks Microsoft Learn links contain required tracking ID (?wt.mc_id=studentamb_296178)"
}

# ------------------------------------------------------------------------------
# Check 4: Bento SVG Assets Validity & Animation Keys
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host " [4/6] Auditing Bento SVG Vector Identity Assets..." -ForegroundColor Cyan

$svgFiles = @(
    "assets\bento\hero-banner.svg",
    "assets\bento\prompt-to-answer-animated.svg",
    "assets\bento\react-scheduler-animated.svg"
)

foreach ($svgRel in $svgFiles) {
    $fullSvg = Join-Path $repoRoot $svgRel
    if (Test-Path $fullSvg) {
        $svgText = Get-Content -Path $fullSvg -Raw -Encoding UTF8
        if ($svgText -match "<svg" -and $svgText -match "</svg>") {
            $hasKeyframes = $svgText -match "@keyframes"
            if ($hasKeyframes) {
                Report-Pass "Valid animated SVG: $svgRel (includes @keyframes animations)"
            }
            else {
                Report-Pass "Valid SVG: $svgRel"
            }
        }
        else {
            Report-Fail "Malformed SVG structure: $svgRel"
        }
    }
}

# ------------------------------------------------------------------------------
# Check 5: Diagram Assets Availability
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host " [5/6] Auditing Technical Diagram Assets (assets/diagrams/)..." -ForegroundColor Cyan

$diagramsDir = Join-Path $repoRoot "assets\diagrams"
if (Test-Path $diagramsDir) {
    $diagramFiles = Get-ChildItem -Path $diagramsDir -File | Where-Object { $_.Length -gt 50 }
    if ($diagramFiles.Count -ge 16) {
        Report-Pass "All $($diagramFiles.Count)/16 diagram assets present in assets/diagrams/"
    }
    else {
        Report-Warn "Found $($diagramFiles.Count)/16 diagram assets. Run scripts/download-assets.ps1 to populate."
    }
}
else {
    Report-Fail "Missing directory: assets/diagrams/"
}

# ------------------------------------------------------------------------------
# Check 6: Strict Cleanliness & Dependencies
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host " [6/6] Auditing Requirements.txt & Strict Cleanliness..." -ForegroundColor Cyan

$reqPath = Join-Path $repoRoot "requirements.txt"
if (Test-Path $reqPath) {
    $reqText = Get-Content -Path $reqPath -Raw -Encoding UTF8
    $expectedPkgs = @("requests", "rich", "pydantic", "schedule", "python-dotenv")
    $missingPkgs = @()
    foreach ($pkg in $expectedPkgs) {
        if ($reqText -notmatch $pkg) {
            $missingPkgs += $pkg
        }
    }
    if ($missingPkgs.Count -eq 0) {
        Report-Pass "requirements.txt contains all 5 required dependencies"
    }
    else {
        Report-Fail "requirements.txt is missing: $($missingPkgs -join ', ')"
    }
}

# Cleanliness scan: Check for forbidden meta-text
$forbiddenTokens = @("generated by AI", "generated by Gemini", "generated by Antigravity")
$foundForbidden = 0
foreach ($file in $docFiles) {
    $content = Get-Content -Path $file.FullName -Raw -Encoding UTF8
    foreach ($token in $forbiddenTokens) {
        if ($content -match [regex]::Escape($token)) {
            Report-Fail "Forbidden meta-text '$token' discovered in $($file.Name)"
            $foundForbidden++
        }
    }
}
if ($foundForbidden -eq 0) {
    Report-Pass "Cleanliness confirmed: Zero AI generation meta-text discovered across repository"
}

# ------------------------------------------------------------------------------
# Summary Output
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host "================================================================================" -ForegroundColor Yellow
Write-Host "  VERIFICATION AUDIT SUMMARY" -ForegroundColor Yellow
Write-Host "================================================================================" -ForegroundColor Yellow
Write-Host "  Total Checks:    $totalChecks" -ForegroundColor White
Write-Host "  Passed:          $passedChecks" -ForegroundColor Green
if ($warningsCount -gt 0) {
    Write-Host "  Warnings:        $warningsCount" -ForegroundColor DarkYellow
}
if ($failedChecks -gt 0) {
    Write-Host "  Failed:          $failedChecks" -ForegroundColor Red
    Write-Host ""
    Write-Host "❌ Verification failed with $failedChecks error(s). Please review the logs above." -ForegroundColor Red
    exit 1
}
else {
    Write-Host "  Failed:          0" -ForegroundColor Green
    Write-Host ""
    Write-Host "🚀 REPOSITORY VERIFICATION COMPLETE: PRODUCTION READY!" -ForegroundColor Green
    exit 0
}
