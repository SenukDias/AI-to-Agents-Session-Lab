<p align="center">
  <img src="../assets/bento/hero-banner.svg" alt="AI to Agents Session Lab" width="100%"/>
</p>

![Lab 00](https://img.shields.io/badge/Lab%2000-Setup%20%26%20CPU%20Tuning-FACC15?style=for-the-badge&labelColor=0E1013&logoColor=FACC15)
![Time](https://img.shields.io/badge/Time-30%20min-white?style=for-the-badge&labelColor=0E1013)
![Difficulty](https://img.shields.io/badge/Difficulty-Beginner-FACC15?style=for-the-badge&labelColor=0E1013)
![CPU Only](https://img.shields.io/badge/CPU%20Only-No%20GPU%20Required-FACC15?style=for-the-badge&labelColor=0E1013)

[🏠 Home](../README.md) | [➡️ Next Lab](lab-01-llm-theory-and-tokens.md)

---

# Lab 00: Environment Setup & CPU Tuning

## 🎯 Learning Objectives

By the end of this lab you will be able to:

- Install Ollama on Windows, macOS, or Linux
- Understand how Ollama wraps `llama.cpp` and serves GGUF quantized models via REST
- Configure CPU-only environment variables to prevent RAM swapping on laptops
- Pull and verify two lightweight models (`qwen2.5:1.5b` and `llama3.2:1b`)
- Run the repo pre-flight health check script

---

## 📚 Theory

### What Is Ollama?

Ollama is an open-source model server that bundles `llama.cpp` (a highly optimised C++ LLM inference engine) into a simple CLI + REST API. It downloads model weights in **GGUF** (GPT-Generated Unified Format) — a binary format that stores quantized weights and all metadata in a single file.

![Ollama Architecture](../assets/diagrams/15-ollama-architecture-flow.png)

**How it works end-to-end:**

```
Your Code  ──HTTP──▶  Ollama REST API (:11434)
                             │
                             ▼
                     llama.cpp engine
                             │
                       GGUF file on disk
                     (quantized weights)
                             │
                       CPU RAM (mmap)
                             │
                       Token output
```

1. Ollama exposes a REST API on `http://localhost:11434`
2. When you call `/api/generate` or `/api/chat`, Ollama loads the GGUF file into RAM via memory-mapping (`mmap`)
3. `llama.cpp` performs inference entirely on CPU using BLAS-accelerated matrix multiplication
4. Generated tokens stream back as newline-delimited JSON

### Why GGUF Quantization Matters for CPU

Full-precision (FP32) weights for even a 1.5B parameter model would require ~6 GB RAM. **Quantization** compresses weights to 4-bit integers, shrinking memory footprint by ~4×:

| Format   | Bits/weight | 1.5B model RAM | Quality impact |
|----------|-------------|----------------|----------------|
| F16      | 16          | ~3.0 GB        | None           |
| Q8_0     | 8           | ~1.6 GB        | Negligible     |
| Q4_K_M   | 4 (mixed)   | ~1.0 GB        | Very small     |
| Q2_K     | 2           | ~0.6 GB        | Noticeable     |

> [!TIP]
> `Q4_K_M` is the sweet spot for CPU inference: it cuts RAM by ~75% versus F16 with minimal quality loss. The `K` means it uses a mixed-precision scheme (some layers kept higher precision), and `M` is the "medium" variant of that scheme.

---

## 🔬 Hands-On Steps

### Step 1 — Install Ollama

**Windows (winget)**
```powershell
winget install Ollama.Ollama
```
After installation, Ollama runs as a background Windows Service and starts automatically on boot.

**macOS (Homebrew)**
```bash
brew install ollama
# Then start the service:
brew services start ollama
```

**Linux (one-liner)**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```
On Linux the installer registers a `systemd` service: `sudo systemctl enable --now ollama`

---

### Step 2 — CPU Memory Tuning

On machines with ≤ 8 GB RAM, the default Ollama settings allow multiple models to stay loaded simultaneously, which can cause the OS to swap to disk and slow inference to a crawl. Set these environment variables **permanently** before the next steps:

**Windows — PowerShell (run once, persists across reboots)**
```powershell
# Restrict to one model loaded at a time
[System.Environment]::SetEnvironmentVariable("OLLAMA_NUM_PARALLEL","1","User")
[System.Environment]::SetEnvironmentVariable("OLLAMA_MAX_LOADED_MODELS","1","User")

# Unload model from RAM after 5 minutes of inactivity
[System.Environment]::SetEnvironmentVariable("OLLAMA_KEEP_ALIVE","5m","User")

# Apply immediately in current session
$env:OLLAMA_NUM_PARALLEL = "1"
$env:OLLAMA_MAX_LOADED_MODELS = "1"
$env:OLLAMA_KEEP_ALIVE = "5m"
```

**macOS / Linux — `.bashrc` / `.zshrc`**
```bash
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_KEEP_ALIVE=5m
```

| Variable | What it does |
|---|---|
| `OLLAMA_NUM_PARALLEL` | Max concurrent generation requests per loaded model |
| `OLLAMA_MAX_LOADED_MODELS` | Max models resident in RAM simultaneously |
| `OLLAMA_KEEP_ALIVE` | Idle TTL before Ollama evicts a model from RAM |

> [!IMPORTANT]
> After setting these variables on Windows, **restart the Ollama service** via Task Manager → Services → Ollama, or run:
> ```powershell
> Stop-Service -Name "Ollama" -ErrorAction SilentlyContinue; Start-Service -Name "Ollama"
> ```

---

### Step 3 — Pull Models

Pull both models used throughout the labs. These are small enough to run on 4 GB RAM machines:

```bash
# Primary model — excellent instruction-following, 1.0 GB (Q4_K_M)
ollama pull qwen2.5:1.5b

# Fast model — ultra-light, great for benchmarking overhead
ollama pull llama3.2:1b
```

Verify they are stored locally:
```bash
ollama list
```

Expected output:
```
NAME               ID            SIZE    MODIFIED
qwen2.5:1.5b       ...           986 MB  just now
llama3.2:1b        ...           1.3 GB  just now
```

---

### Step 4 — Run the Pre-flight Check

From the **repo root**, run the doctor script. It checks that Ollama is reachable, models are present, and Python dependencies are installed:

```bash
python scripts/doctor.py
```

A passing run looks like:
```
✅ Ollama reachable at http://localhost:11434
✅ qwen2.5:1.5b — found
✅ llama3.2:1b — found
✅ Python packages: requests, rich, pydantic, schedule, python-dotenv
🎉 All checks passed — you are ready for Lab 01!
```

---

<details><summary>💡 Hint 1 — How to verify Ollama is running via curl (Click to expand)</summary>

Ollama exposes a simple health endpoint:

```bash
curl http://localhost:11434/
```
Expected response: `Ollama is running`

To list available models via API:
```bash
curl http://localhost:11434/api/tags
```

If Ollama is not running on Windows:
```powershell
# Check service status
Get-Service -Name "Ollama"

# Start it if stopped
Start-Service -Name "Ollama"
```

</details>

<details><summary>💡 Hint 2 — What does GGUF Q4_K_M actually mean? (Click to expand)</summary>

Breaking down the naming:
- **GGUF** — GPT-Generated Unified Format. A single binary file containing weights + tokenizer + metadata
- **Q4** — 4-bit integer quantization (weights stored as 4-bit values, reducing precision but massively cutting size)
- **K** — k-quants scheme: uses different quantization levels per tensor layer. Attention layers (most quality-sensitive) stay at higher precision; feed-forward layers are quantized more aggressively
- **M** — "Medium" variant of k-quants (between _S small and _L large in quality/size tradeoff)

Result: a model that behaves very close to its full-precision parent but fits in ~1 GB instead of ~3 GB.

</details>

<details><summary>💡 Hint 3 — How to free RAM by unloading models (Click to expand)</summary>

Ollama keeps a model in RAM for `OLLAMA_KEEP_ALIVE` after the last request. To evict it immediately without restarting Ollama:

```bash
# Force unload by setting keep_alive to 0 in an API request
curl http://localhost:11434/api/generate -d '{"model":"qwen2.5:1.5b","keep_alive":0}'
```

Or use the CLI to run with an immediate unload:
```bash
ollama run qwen2.5:1.5b --keepalive 0s
```

You can confirm the model is unloaded with:
```bash
ollama ps
# Empty output = no models currently loaded in RAM
```

</details>

---

## ✅ Verification

Before moving on, confirm all of the following:

- [ ] `ollama list` shows both `qwen2.5:1.5b` and `llama3.2:1b`
- [ ] `curl http://localhost:11434/` returns `Ollama is running`
- [ ] `python scripts/doctor.py` shows all green checkmarks
- [ ] Environment variables are set (`echo $env:OLLAMA_NUM_PARALLEL` on Windows should print `1`)

---

<details><summary>🔧 Common Lab Errors & Fixes</summary>

**`ollama: command not found` after `winget install`**
> The `winget` installer adds Ollama to `%LOCALAPPDATA%\Programs\Ollama`. Close and reopen PowerShell/Terminal so the updated `PATH` is loaded. If still missing, add manually:
> ```powershell
> $env:PATH += ";$env:LOCALAPPDATA\Programs\Ollama"
> ```

**`Error: listen tcp 127.0.0.1:11434: bind: address already in use`**
> Something else is using port 11434. Find and stop it:
> ```powershell
> # Windows
> netstat -ano | findstr :11434
> # Note the PID in the last column, then:
> Stop-Process -Id <PID> -Force
> ```
> ```bash
> # macOS / Linux
> lsof -ti:11434 | xargs kill -9
> ```

**`ollama pull` hangs or times out**
> Check disk space first (`df -h` / `Get-PSDrive C`). Models need 1–2 GB free. If space is fine, it may be a network issue — retry with `ollama pull qwen2.5:1.5b` and wait; large files can take several minutes on slower connections.

**Model runs extremely slowly (< 1 token/sec)**
> RAM is likely being swapped to disk. Confirm env vars are set, restart the Ollama service, and try `qwen2.5:0.5b` as the smallest fallback:
> ```bash
> ollama pull qwen2.5:0.5b
> ```

**`python scripts/doctor.py` fails with `ModuleNotFoundError`**
> Install dependencies first:
> ```bash
> pip install -r requirements.txt
> ```

</details>

---

📖 **Further Reading:** [Microsoft Learn — Fundamentals of Generative AI](https://learn.microsoft.com/en-us/training/modules/fundamentals-generative-ai/?wt.mc_id=studentamb_296178)

---

[🏠 Home](../README.md) | [➡️ Next Lab](lab-01-llm-theory-and-tokens.md)
