# 🛠️ Troubleshooting Guide — AI to Agents Session Lab

> Quick navigation: [1 · Installation](#1-ollama-installation-issues) · [2 · Port Conflict](#2-port-11434-conflicts) · [3 · Model Pull](#3-model-pull-failures) · [4 · OOM](#4-oom--memory-swap-on-4-gb-ram) · [5 · JSON](#5-json-parsing-errors-from-llm) · [6 · KV Cache](#6-kv-cache-issues) · [7 · ReAct Loop](#7-react-loop-infinite-iteration) · [8 · Windows](#8-windows-specific-issues)

---

## 1. Ollama Installation Issues

### Symptoms
- `ollama` command not recognized in PowerShell / terminal
- Ollama installer completes but service does not start
- `ollama serve` exits immediately with no output

### Cause
- Ollama binary not on system `PATH` after installation
- Windows Defender or antivirus blocking the executable
- Missing Visual C++ Redistributable on older Windows builds

### Fix

**Verify PATH (Windows PowerShell)**
```powershell
# Check if ollama is discoverable
where.exe ollama

# If not found, add manually (adjust path if installed elsewhere)
$env:PATH += ";$env:LOCALAPPDATA\Programs\Ollama"
[System.Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";$env:LOCALAPPDATA\Programs\Ollama", "User")
```

**Restart Ollama service manually**
```powershell
# Kill any existing process first
Get-Process -Name "ollama" -ErrorAction SilentlyContinue | Stop-Process -Force

# Start fresh
Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden

# Confirm it responded
Invoke-RestMethod http://localhost:11434/api/tags
```

**Re-install if binary is blocked**
1. Open Windows Security → Virus & Threat Protection → Protection History
2. Allow `ollama.exe` if it appears quarantined
3. Re-download from https://ollama.com and run as Administrator

---

## 2. Port 11434 Conflicts

### Symptoms
- `Error: listen tcp 127.0.0.1:11434: bind: address already in use`
- `ollama serve` starts but `curl http://localhost:11434` times out
- Another process is responding on port 11434 unexpectedly

### Cause
A previous Ollama instance, a stale process, or another application is holding port 11434.

### Fix

**Find the conflicting process**
```powershell
# Windows PowerShell
netstat -ano | findstr ":11434"

# Note the PID in the rightmost column, then:
Get-Process -Id <PID>
Stop-Process -Id <PID> -Force
```

```bash
# macOS / Linux
lsof -i :11434
kill -9 <PID>
```

**Change Ollama's port (if you need 11434 for something else)**
```powershell
# Set in .env
$env:OLLAMA_HOST = "http://localhost:11435"
ollama serve
```
Then update `OLLAMA_HOST=http://localhost:11435` in your `.env` file.

---

## 3. Model Pull Failures

### Symptoms
- `ollama pull qwen2.5:1.5b` stalls at 0% or errors out mid-download
- `Error: pull model manifest: Get ... dial tcp: i/o timeout`
- Download completes but model shows as corrupted

### Cause
- Insufficient disk space (models require 1–4 GB each)
- Network timeout or proxy blocking Ollama's registry
- Partial download left in cache

### Fix

**Check disk space first**
```powershell
# Windows PowerShell
Get-PSDrive C | Select-Object Used, Free

# Models are stored here — check available space
Get-ChildItem "$env:USERPROFILE\.ollama\models" -ErrorAction SilentlyContinue
```

**Clear corrupted partial downloads**
```powershell
# Remove all cached blobs and retry
Remove-Item "$env:USERPROFILE\.ollama\models\blobs" -Recurse -Force -ErrorAction SilentlyContinue
ollama pull qwen2.5:1.5b
```

**Pull with verbose output to debug network issues**
```powershell
# Check Ollama logs while pulling
ollama pull qwen2.5:1.5b 2>&1 | Tee-Object -FilePath pull.log
```

**Use the smallest fallback if disk is tight**
```powershell
ollama pull qwen2.5:0.5b   # ~390 MB only
```

---

## 4. OOM / Memory Swap on 4 GB RAM

### Symptoms
- Laptop fan spins to maximum during inference
- Inference takes 60+ seconds per token
- System becomes unresponsive; Task Manager shows 100% disk I/O
- Python script gets killed with `MemoryError`

### Cause
Ollama loaded a model larger than available RAM, forcing the OS to swap to disk. Even `qwen2.5:1.5b` needs ~2 GB free — if your system has only 4 GB total and other apps are running, there may not be enough headroom.

### Fix

**Switch to the smallest model**
```powershell
# Edit .env
OLLAMA_MODEL=qwen2.5:0.5b
OLLAMA_FAST_MODEL=qwen2.5:0.5b
OLLAMA_FALLBACK_MODEL=qwen2.5:0.5b
```

**Enforce single-model loading and short keep-alive**
```powershell
# In .env — prevents two models loading simultaneously
OLLAMA_NUM_PARALLEL=1
OLLAMA_MAX_LOADED_MODELS=1
OLLAMA_KEEP_ALIVE=2m
```

**Reduce context window**
```python
# In your Python code — lower num_ctx reduces VRAM/RAM usage dramatically
payload = {
    "model": "qwen2.5:0.5b",
    "options": {"num_ctx": 1024},   # default is 2048–4096
    ...
}
```

**Free RAM before running labs**
```powershell
# Close Chrome, VS Code extensions, Slack, Teams, etc.
# Then verify available memory:
Get-CimInstance Win32_OperatingSystem | Select-Object FreePhysicalMemory
```

---

## 5. JSON Parsing Errors from LLM

### Symptoms
- `json.JSONDecodeError: Expecting value: line 1 column 1`
- LLM returns JSON wrapped in markdown fences: ` ```json ... ``` `
- Output contains extra explanation text before or after the JSON block
- Intermittent parse failures (works sometimes, fails other times)

### Cause
LLMs naturally add conversational framing around JSON. The model is not broken — it just needs to be constrained.

### Fix

**Strip markdown fences before parsing**
```python
import json
import re

def parse_json_response(raw: str) -> dict:
    # Remove markdown code fences
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()
    # Extract first JSON object or array found
    match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    raise ValueError(f"No JSON found in response: {raw[:200]}")
```

**Use Ollama's `format` parameter to force JSON mode**
```python
payload = {
    "model": "qwen2.5:1.5b",
    "format": "json",           # Forces JSON-only output
    "messages": [
        {"role": "system", "content": "Respond only with valid JSON."},
        {"role": "user",   "content": your_prompt}
    ],
    "stream": False
}
```

**Add a retry with explicit instruction on failure**
```python
def call_with_json_retry(prompt: str, max_retries: int = 3) -> dict:
    for attempt in range(max_retries):
        raw = call_ollama(prompt)
        try:
            return parse_json_response(raw)
        except (json.JSONDecodeError, ValueError):
            prompt += "\n\nREMINDER: Your response MUST be valid JSON only. No explanation."
    raise RuntimeError("LLM failed to return valid JSON after retries")
```

---

## 6. KV Cache Issues

### Symptoms
- First request takes 10–15 seconds (cold start), subsequent requests are faster
- Increasing `num_ctx` causes out-of-memory errors
- "Prefill" phase in logs is extremely long for large prompts

### Cause
The KV (Key-Value) cache stores computed attention states for the prompt. A cold cache means the model recomputes everything from scratch. Setting `num_ctx` too high allocates more memory than available RAM.

### Fix

**Understand cold vs warm cache**
```
Cold cache  → first request after model load: full prefill (slow)
Warm cache  → subsequent requests with same prefix: partial prefill (fast)
```

**Set `num_ctx` to match your actual prompt length**
```python
# Rule of thumb: num_ctx ≈ max_prompt_tokens + max_response_tokens + 20% buffer
# For most lab exercises, 1024–2048 is sufficient
options = {"num_ctx": 2048}
```

**Keep the model loaded between calls (avoid keep_alive=0)**
```python
# In your .env — 5 minutes keeps model warm between exercises
OLLAMA_KEEP_ALIVE=5m
```

**Monitor active models**
```powershell
ollama ps   # Shows loaded models and their memory usage
```

---

## 7. ReAct Loop Infinite Iteration

### Symptoms
- Lab 03/04 agent keeps calling the same tool repeatedly without terminating
- Script runs indefinitely and must be killed manually (`Ctrl+C`)
- Each iteration produces the same "Action" and "Observation" without progress

### Cause
- Missing or unreachable `Final Answer` termination condition
- LLM ignoring the stop signal in the system prompt
- Tool returning an error the agent doesn't know how to handle
- Circular reasoning: agent misinterprets the observation and re-queries

### Fix

**Always enforce a maximum iteration guard**
```python
MAX_ITERATIONS = 10

def react_loop(task: str) -> str:
    history = []
    for step in range(MAX_ITERATIONS):
        response = call_ollama(build_prompt(task, history))
        
        if "Final Answer:" in response:
            return response.split("Final Answer:")[-1].strip()
        
        action = parse_action(response)
        observation = execute_tool(action)
        history.append({"thought": response, "observation": observation})
        
    # Fallback: ask model to summarize what it found so far
    return call_ollama(f"You have used {MAX_ITERATIONS} steps. Summarize your findings now.")
```

**Add a stall detector**
```python
from collections import Counter

def detect_loop(history: list, window: int = 3) -> bool:
    if len(history) < window:
        return False
    recent_actions = [h.get("action") for h in history[-window:]]
    return len(set(str(a) for a in recent_actions)) == 1  # All identical

# Inside the loop:
if detect_loop(history):
    return "Agent detected a loop and stopped. Last observation: " + history[-1]["observation"]
```

**Improve the system prompt termination instruction**
```
When you have enough information to answer, you MUST respond with:
Final Answer: <your complete answer here>

Do NOT call any more tools after reaching a Final Answer.
```

---

## 8. Windows-Specific Issues

### Symptoms
- `.\venv\Scripts\Activate.ps1` blocked: "running scripts is disabled on this system"
- Ollama works in CMD but not PowerShell
- WSL2 Ollama instance not reachable from Windows Python scripts
- Windows Defender Firewall blocking port 11434 connections

### Cause
Windows PowerShell execution policy, WSL2 network isolation, or Windows Firewall rules.

### Fix

**Fix PowerShell execution policy**
```powershell
# Check current policy
Get-ExecutionPolicy -List

# Set for current user (safe — does not affect system-wide policy)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Activate your venv
.\venv\Scripts\Activate.ps1
```

**Run Ollama on WSL2 and reach it from Windows**
```bash
# Inside WSL2 — bind to all interfaces so Windows can reach it
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

```powershell
# In Windows .env — use the WSL2 IP address
# Find it with: wsl hostname -I
OLLAMA_HOST=http://172.x.x.x:11434
```

**Allow Ollama through Windows Firewall**
```powershell
# Run PowerShell as Administrator
New-NetFirewallRule `
  -DisplayName "Ollama API" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 11434 `
  -Action Allow
```

**If `python` is not found — use `py` launcher**
```powershell
# Windows ships with the py launcher, not `python`
py -3 -m venv venv
py -3 -m pip install -r requirements.txt

# Or add Python to PATH permanently via System Properties → Environment Variables
```

**Long path issues on Windows**
```powershell
# Enable long path support (run as Administrator)
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
  -Name LongPathsEnabled -Value 1
```

---

> Still stuck? Open an issue at [github.com/SenukDias/AI-to-Agents-Session-Lab](https://github.com/SenukDias/AI-to-Agents-Session-Lab/issues) with your OS version, Python version, Ollama version (`ollama --version`), and the full error message.
