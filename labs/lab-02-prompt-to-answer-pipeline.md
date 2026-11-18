<p align="center">
  <img src="../assets/bento/hero-banner.svg" alt="AI to Agents Session Lab" width="100%"/>
</p>

![Lab 02](https://img.shields.io/badge/Lab%2002-Prompt%20to%20Answer%20Pipeline-FACC15?style=for-the-badge&labelColor=0E1013&logoColor=FACC15)
![Time](https://img.shields.io/badge/Time-45%20min-white?style=for-the-badge&labelColor=0E1013)
![Difficulty](https://img.shields.io/badge/Difficulty-Intermediate-FACC15?style=for-the-badge&labelColor=0E1013)
![CPU Only](https://img.shields.io/badge/CPU%20Only-No%20GPU%20Required-FACC15?style=for-the-badge&labelColor=0E1013)

[⬅️ Previous Lab](lab-01-llm-theory-and-tokens.md) | [🏠 Home](../README.md) | [➡️ Next Lab](lab-03-ollama-cli-and-modelfile.md)

---

# Lab 02: The Prompt-to-Answer Pipeline

## 🎯 Learning Objectives

By the end of this lab you will be able to:

- Describe the complete lifecycle of an LLM request from text input to streamed output
- Distinguish between the **Prefill** and **Decode** phases and explain why each is bottlenecked by different hardware resources
- Explain what the KV Cache is, what it stores, and how it affects repeated queries
- Extract and interpret timing metrics from the Ollama API response
- Tune `temperature`, `top_k`, `top_p`, and `num_ctx` to control generation quality and speed

---

## 📚 Theory

### 1. Full Request Lifecycle

Every call to `/api/generate` or `/api/chat` follows this exact sequence:

```
User sends prompt text
        │
        ▼
  ┌─────────────┐
  │  Tokenizer  │  text → token IDs (integers)
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │  Embeddings │  IDs → dense vectors (input to Transformer)
  └──────┬──────┘
         │
         ▼
  ╔══════════════════════════════════╗
  ║  PHASE 1: PREFILL                ║
  ║  All input tokens processed      ║
  ║  simultaneously (parallel)       ║
  ║  → Builds KV Cache               ║
  ║  → Outputs first-token logits    ║
  ╚══════════════════════════════════╝
         │
         ▼
  ╔══════════════════════════════════╗
  ║  PHASE 2: DECODE (loop)          ║
  ║  One token generated per step    ║
  ║  Uses KV Cache, appends result   ║
  ║  → Repeats until EOS or max_len  ║
  ╚══════════════════════════════════╝
         │
         ▼
  ┌─────────────┐
  │ Detokenizer │  token IDs → human-readable text
  └──────┬──────┘
         │
         ▼
  Streamed response to caller
```

![Prompt to Answer](../assets/bento/prompt-to-answer-animated.svg)

---

### 2. Phase 1 — Prefill (Compute-Bound)

During Prefill, the model processes **all input tokens at the same time** using parallel matrix multiplication.

- Every token in your prompt attends to every other token simultaneously
- This is compute-intensive: more input tokens = proportionally more FLOPs
- The result is stored in the **KV Cache** (Key-Value Cache)
- The latency of Prefill is your **Time-To-First-Token (TTFT)** — Ollama reports this as `prompt_eval_duration`

**Why compute-bound?** The GPU/CPU arithmetic units are the bottleneck. Memory bandwidth is not the limiting factor because all matrix operations happen in one large batch.

```
TTFT ≈ num_input_tokens × constant_per_token
```

A prompt of 4096 tokens takes roughly 4× as long to prefill as a 1024-token prompt.

---

### 3. Phase 2 — Decode (Memory-Bandwidth-Bound)

After Prefill, the model generates **one token per step** in an autoregressive loop:

1. Take the most recently generated token
2. Run it through all Transformer layers (each reading from the KV Cache)
3. Sample the next token from the output distribution
4. Append it to the history → go to step 1

- Decode is **memory-bandwidth-bound**: the bottleneck is reading the KV Cache and model weights from RAM on every step
- On CPU with 4 GB RAM, typical decode speed is 5–20 tokens/sec for a 1.5B model
- Ollama reports total decode time as `eval_duration`

**Tokens-per-second (TPS) formula:**
```
TPS = eval_count / (eval_duration / 1e9)
```
(Ollama reports durations in nanoseconds)

---

### 4. KV Cache Mechanics

![Prefill vs Decode KV Cache](../assets/diagrams/05-prefill-vs-decode-kv-cache.png)

The **Key-Value Cache** stores intermediate attention computations from every past token. This avoids recomputing attention over the entire history on every decode step.

| Cache state | Effect |
|---|---|
| **Cold cache** (first query) | Full Prefill required; TTFT proportional to prompt length |
| **Warm cache** (same context, follow-up) | Prefill only over new tokens; dramatically lower TTFT |
| **Cache evicted** (long conversation or restart) | Full cold Prefill for entire history |

**What is stored in the cache?**
- For every Transformer layer: a matrix of Key vectors and a matrix of Value vectors for every token seen so far
- Cache size (bytes) ≈ `2 × num_layers × num_heads × head_dim × num_tokens × bytes_per_element`
- For `qwen2.5:1.5b` at Q4_K_M: roughly 1 MB per 1024 context tokens

> [!WARNING]
> Setting `num_ctx` very large (e.g. 32768) on a 4 GB RAM machine will allocate a large KV Cache upfront and may cause OOM even before any tokens are generated.

---

### 5. Measuring Real Timing

Ollama's `/api/generate` response includes rich timing metadata when you set `"stream": false`:

```python
import requests

resp = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "qwen2.5:1.5b",
        "prompt": "Explain what a firewall does in one sentence.",
        "stream": False,
        "options": {"num_ctx": 2048}
    }
)
data = resp.json()

# All durations are in nanoseconds
ttft_ms        = data["prompt_eval_duration"] / 1e6   # Prefill (TTFT)
decode_ms      = data["eval_duration"] / 1e6           # Decode total
prompt_tokens  = data["prompt_eval_count"]             # Tokens in prompt
output_tokens  = data["eval_count"]                    # Tokens generated
tps            = output_tokens / (data["eval_duration"] / 1e9)

print(f"TTFT:          {ttft_ms:.1f} ms")
print(f"Decode time:   {decode_ms:.1f} ms")
print(f"Prompt tokens: {prompt_tokens}")
print(f"Output tokens: {output_tokens}")
print(f"Speed:         {tps:.1f} tok/s")
```

| Ollama field | Meaning | Unit |
|---|---|---|
| `prompt_eval_duration` | Prefill time (TTFT) | nanoseconds |
| `eval_duration` | Decode time | nanoseconds |
| `prompt_eval_count` | Input token count | tokens |
| `eval_count` | Output token count | tokens |
| `load_duration` | Model load time (0 if already loaded) | nanoseconds |
| `total_duration` | End-to-end wall time | nanoseconds |

---

### 6. Sampling Knobs

The model outputs a probability distribution over all ~32k vocabulary tokens. **Sampling parameters** control how you pick from that distribution:

| Parameter | What it controls | Practical effect |
|---|---|---|
| `temperature` | Scales logits before softmax. >1 flattens distribution (more random), <1 sharpens it (more deterministic) | 0.0 = greedy (always most likely token); 1.0 = default; 2.0 = creative/chaotic |
| `top_k` | Only consider the top K most probable tokens | `top_k=1` = greedy; `top_k=40` = common default |
| `top_p` | Nucleus sampling: take the smallest set of tokens whose cumulative probability ≥ p | `top_p=0.9` = typical; filters unlikely long tails |
| `num_ctx` | Context window size (tokens). Limits how much history the model can attend to | Larger = slower Prefill + bigger KV Cache |
| `repeat_penalty` | Penalise tokens that have already appeared | >1.0 reduces repetition; 1.1 is a mild setting |

> [!TIP]
> For deterministic, repeatable output (useful in automated pipelines): set `temperature=0.0`, `top_k=1`, `top_p=1.0`.
> For creative brainstorming: `temperature=0.8`, `top_k=50`, `top_p=0.95`.

---

## 🔬 Hands-On Steps

### Step 1 — Run the Benchmark Exercise

```bash
python exercises/ex02_prefill_decode_benchmark.py
```

The script sends the same prompt at different context lengths and plots TTFT vs. prompt token count, then shows TPS at different output lengths.

### Step 2 — Experiment with Sampling

Modify the script to send the same prompt three times with different temperature settings:
- `temperature=0.0` (deterministic)
- `temperature=0.7` (balanced)
- `temperature=1.5` (highly random)

Compare the outputs and timing. Notice that temperature does **not** affect speed — it only affects which token is selected from the already-computed distribution.

### Step 3 — Observe KV Cache Warmth

Send the same system prompt twice in quick succession and compare `prompt_eval_duration`:

```python
# First call — cold cache
resp1 = send_request(long_system_prompt)
# Second call — warm cache (same session)
resp2 = send_request(long_system_prompt)
# resp2["prompt_eval_duration"] should be significantly lower
```

---

<details><summary>💡 Hint 1 — Why is Prefill compute-bound but Decode memory-bandwidth-bound? (Click to expand)</summary>

**Prefill is compute-bound** because all input tokens are processed in one giant batch. The attention operation involves multiplying large matrices (Q × K^T), which is arithmetic-intensive. The GPU/CPU arithmetic units are saturated; memory bandwidth is relatively underutilised because the data fits in cache for the batch.

**Decode is memory-bandwidth-bound** because only **one token** is processed per step. The batch size is 1. The model must read the entire KV Cache (potentially hundreds of MB) and all layer weights on every single step, but does only a tiny amount of arithmetic with that data. The ratio of memory reads to compute is very high — the memory bus is the bottleneck.

This is why faster RAM (DDR5 vs DDR4) improves decode speed more than a faster CPU core clock.

</details>

<details><summary>💡 Hint 2 — How to measure TTFT accurately (Click to expand)</summary>

**Option A — Non-streaming (simpler):**
```python
import time
start = time.perf_counter()
resp = requests.post(url, json=payload)
# TTFT is not accurately measured here — total time includes network + decode
```

**Option B — Streaming (accurate TTFT):**
```python
import time, requests, json

start = time.perf_counter()
first_token_time = None

with requests.post(url, json={**payload, "stream": True}, stream=True) as r:
    for line in r.iter_lines():
        if line:
            chunk = json.loads(line)
            if first_token_time is None and chunk.get("response"):
                first_token_time = time.perf_counter() - start
                print(f"TTFT: {first_token_time*1000:.1f} ms")
```

**Option C — From Ollama metadata (non-streaming):**
```python
# Use prompt_eval_duration from the response (most accurate, Ollama-measured)
ttft_ms = data["prompt_eval_duration"] / 1_000_000
```

Option C is preferred because it excludes network overhead and is measured inside the Ollama process.

</details>

<details><summary>💡 Hint 3 — Effect of temperature=0 vs temperature=1 (Click to expand)</summary>

| Setting | Behaviour | Use case |
|---|---|---|
| `temperature=0` | Greedy decoding — always picks the single most probable token. Output is **deterministic** and **reproducible** | Structured output, JSON, code, automated testing |
| `temperature=0.7` | Moderate randomness — high-probability tokens still dominate, but occasional variation allowed | General chat, summaries, Q&A |
| `temperature=1.0` | Raw model distribution — no scaling applied. Standard creative generation | Creative writing, brainstorming |
| `temperature=1.5+` | Artificially flattened — unlikely tokens get boosted. Output becomes incoherent quickly | Avoid in production |

**Important:** `temperature=0` does not change **speed**. The softmax computation still runs; it just becomes a winner-take-all selection. The latency difference you might observe comes from shorter outputs (fewer decode steps) when greedy decoding produces EOS sooner.

</details>

---

## ✅ Verification

- [ ] `python exercises/ex02_prefill_decode_benchmark.py` completes and prints timing data
- [ ] You can read `prompt_eval_duration` and `eval_duration` from an Ollama API response
- [ ] You can explain in one sentence why decode speed is limited by RAM bandwidth, not CPU speed
- [ ] You set `temperature=0.0` and confirmed the output is identical across two calls with the same prompt

---

<details><summary>🔧 Common Lab Errors & Fixes</summary>

**`KeyError: 'prompt_eval_duration'` in response**
> This field is only present when `"stream": false`. With streaming, you must parse the final JSON chunk (the one with `"done": true`), which contains all timing metadata.

**TTFT is 0 ms on the second identical call**
> This is correct — the KV Cache was warm, so there was no Prefill work to do. This is the expected behaviour and shows the cache working as intended.

**TPS is very low (< 2 tok/s)**
> RAM is likely swapped to disk. Check: `ollama ps` — if the model shows "100% GPU" but you have no GPU, something is misconfigured. Restart Ollama and check that `OLLAMA_MAX_LOADED_MODELS=1` is set.

**`num_ctx` causes OOM crash**
> Reduce `num_ctx` to 2048 or 1024. On 4 GB RAM machines, do not exceed `num_ctx=4096` with any model larger than 1.5B.

</details>

---

[⬅️ Previous Lab](lab-01-llm-theory-and-tokens.md) | [🏠 Home](../README.md) | [➡️ Next Lab](lab-03-ollama-cli-and-modelfile.md)
