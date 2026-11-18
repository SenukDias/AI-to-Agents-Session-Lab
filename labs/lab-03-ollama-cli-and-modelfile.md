<p align="center">
  <img src="../assets/bento/hero-banner.svg" alt="AI to Agents Session Lab" width="100%"/>
</p>

![Lab 03](https://img.shields.io/badge/Lab%2003-Ollama%20CLI%20%26%20Modelfile-FACC15?style=for-the-badge&labelColor=0E1013&logoColor=FACC15)
![Time](https://img.shields.io/badge/Time-40%20min-white?style=for-the-badge&labelColor=0E1013)
![Difficulty](https://img.shields.io/badge/Difficulty-Intermediate-FACC15?style=for-the-badge&labelColor=0E1013)
![CPU Only](https://img.shields.io/badge/CPU%20Only-No%20GPU%20Required-FACC15?style=for-the-badge&labelColor=0E1013)

[⬅️ Previous Lab](lab-02-prompt-to-answer-pipeline.md) | [🏠 Home](../README.md) | [➡️ Next Lab](lab-04-react-agent-from-scratch.md)

---

# Lab 03: Ollama CLI & Custom Modelfile

## 🎯 Learning Objectives

By the end of this lab you will be able to:

- Use all core Ollama CLI commands to inspect and manage local models
- Read and understand GGUF quantization level tradeoffs for CPU inference
- Write a custom `Modelfile` to create a bespoke persona-tuned model
- Build and run a custom model with `ollama create` and `ollama run`
- Use Ollama's `format` parameter to request structured JSON output
- Validate LLM JSON responses with Pydantic

---

## 📚 Theory

### 1. Ollama CLI Reference

| Command | What it does |
|---|---|
| `ollama list` | List all locally downloaded models with size and modification date |
| `ollama ps` | Show models currently loaded in RAM and their memory usage |
| `ollama show --modelfile <model>` | Print the Modelfile that defines a model (including system prompt, parameters) |
| `ollama cp <src> <dst>` | Duplicate a model under a new name (creates a lightweight alias) |
| `ollama rm <model>` | Delete a model and free its disk space |
| `ollama pull <model>` | Download a model from the Ollama registry |
| `ollama push <model>` | Upload a model to the Ollama registry (requires login) |
| `ollama create <name> -f <Modelfile>` | Build a new model from a Modelfile |
| `ollama run <model>` | Start an interactive REPL session with a model |

**Useful inspection commands:**
```bash
# See what parameters and system prompt a model uses
ollama show --modelfile qwen2.5:1.5b

# Check which models are currently taking up RAM
ollama ps

# Free up RAM without restarting Ollama
ollama stop qwen2.5:1.5b
```

---

### 2. GGUF Quantization Levels

Choosing the right quantization level is a RAM vs quality tradeoff. Here is a practical reference for a **1.5B parameter model** (multiply roughly by 2× for 3B, 4× for 7B):

| Quantization | Bits/weight | RAM usage | Quality vs F16 | Best for |
|---|---|---|---|---|
| `F16` | 16 | ~3.1 GB | Baseline (perfect) | GPU with ample VRAM |
| `Q8_0` | 8 | ~1.6 GB | Negligible loss | 8–16 GB RAM machines |
| `Q6_K` | 6 | ~1.3 GB | Very small loss | 8 GB RAM machines |
| **`Q4_K_M`** | **4 (mixed)** | **~1.0 GB** | **Small loss** | **Sweet spot — recommended** |
| `Q4_K_S` | 4 (small) | ~0.9 GB | Small-medium loss | Tight RAM budgets |
| `Q3_K_M` | 3 (mixed) | ~0.8 GB | Moderate loss | Very constrained devices |
| `Q2_K` | 2 | ~0.6 GB | Significant loss | Last resort (4 GB RAM) |

> [!TIP]
> When you run `ollama pull qwen2.5:1.5b`, Ollama automatically selects `Q4_K_M` as the default. To pull a specific quantization: `ollama pull qwen2.5:1.5b:q8_0`

**How k-quants (`_K`) differ from plain quants:**
- Plain quantization (`Q4_0`) applies the same 4-bit compression to every weight
- K-quants (`Q4_K_M`) use mixed precision: attention layers (most quality-sensitive) are kept at higher precision, while feed-forward layers are compressed more aggressively
- Result: better output quality at the same average bit-width

---

### 3. The Modelfile

An Ollama `Modelfile` is a text file (similar to a Dockerfile) that defines a custom model by composing a base model with parameters and a system prompt.

**Repo Modelfile** (`Modelfile` in the repo root):

```dockerfile
FROM qwen2.5:1.5b

PARAMETER temperature 0.2
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_ctx 4096
PARAMETER repeat_penalty 1.1
PARAMETER stop "<|im_end|>"

SYSTEM """
You are SecOps Mentor — a precise, structured AI assistant for cybersecurity operations and DevSecOps workflows.
Always respond with valid JSON when instructed. Never hallucinate tool names or file paths.
Keep answers concise and actionable. When uncertain, state it explicitly rather than guessing.
For threat analysis tasks, structure output as: {"severity": "...", "findings": [...], "remediation": [...]}.
"""
```

**Modelfile instruction reference:**

| Instruction | Purpose |
|---|---|
| `FROM <model>` | Base model to build on (required) |
| `PARAMETER <name> <value>` | Override a generation parameter |
| `SYSTEM <text>` | Set the system prompt injected before every conversation |
| `TEMPLATE <template>` | Override the chat template (usually not needed) |
| `MESSAGE <role> <content>` | Inject few-shot examples into the default context |

---

### 4. Building and Using a Custom Model

**Step 1 — Create the model from the repo Modelfile:**
```bash
ollama create secops-mentor -f Modelfile
```

Ollama will:
1. Read the `FROM` base model (download if not already present)
2. Apply the `PARAMETER` overrides
3. Store the new model as `secops-mentor` (a lightweight config layer on top of the base weights)

**Step 2 — Verify it was created:**
```bash
ollama list
# secops-mentor should appear
```

**Step 3 — Run an interactive session:**
```bash
ollama run secops-mentor
>>> Analyse this log line and return JSON: "FAILED LOGIN from 192.168.1.42 to admin@corp.com"
```

**Step 4 — Inspect the resulting Modelfile:**
```bash
ollama show --modelfile secops-mentor
```

---

### 5. Structured JSON Output with Ollama

Ollama supports a `format` parameter that forces the model to output valid JSON. This is crucial for agentic pipelines where you need to parse the response programmatically.

**API request with `format="json"`:**
```python
import requests, json
from pydantic import BaseModel
from typing import Literal

OLLAMA_HOST = "http://localhost:11434"

# Define your expected response schema with Pydantic
class ThreatAnalysis(BaseModel):
    severity: Literal["low", "medium", "high", "critical"]
    findings: list[str]
    remediation: list[str]
    confidence: float  # 0.0 to 1.0

def analyse_log(log_line: str) -> ThreatAnalysis:
    prompt = f"""Analyse the following log line and return a JSON object.

Log: {log_line}

Return JSON with keys: severity, findings (list), remediation (list), confidence (0.0-1.0)."""

    resp = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={
            "model": "secops-mentor",
            "prompt": prompt,
            "stream": False,
            "format": "json",        # ← Forces valid JSON output
            "options": {
                "temperature": 0.2,  # Low temp for structured output
                "num_ctx": 2048
            }
        }
    )

    raw_json = resp.json()["response"]

    # Validate and parse with Pydantic
    result = ThreatAnalysis.model_validate_json(raw_json)
    return result

# Usage
analysis = analyse_log("FAILED LOGIN from 192.168.1.42 to admin@corp.com (5 attempts in 30s)")
print(f"Severity: {analysis.severity}")
print(f"Confidence: {analysis.confidence:.0%}")
```

> [!IMPORTANT]
> `format="json"` guarantees syntactically valid JSON but does **not** guarantee your expected keys are present. Always validate with Pydantic (`model_validate_json`) or wrap in `try/except` to handle schema mismatches.

---

### 6. Why Temperature 0.2 for Structured Output?

| Temperature | Effect on JSON output |
|---|---|
| `0.0` | Perfectly deterministic. Same input always produces identical JSON. Risk: model may get stuck in a rut if the first token was wrong |
| `0.1–0.2` | Near-deterministic with tiny variation. **Best for structured output** — allows minor recovery from early wrong choices |
| `0.5+` | Increases risk of hallucinated keys or values that don't match your schema |
| `1.0+` | JSON schema compliance degrades significantly |

---

## 🔬 Hands-On Steps

### Step 1 — Explore Existing Models

```bash
ollama list
ollama show --modelfile qwen2.5:1.5b
```

Notice the default parameters and chat template used by the base model.

### Step 2 — Create the secops-mentor Model

```bash
ollama create secops-mentor -f Modelfile
ollama list   # confirm secops-mentor appears
```

### Step 3 — Test It Interactively

```bash
ollama run secops-mentor
```

Try this prompt:
```
Analyse: "SSH brute force detected: 847 failed login attempts from 10.0.0.5 in 60 seconds". Return JSON.
```

### Step 4 — Run the Exercise

```bash
python exercises/ex03_custom_modelfile_client.py
```

The exercise script sends several pre-defined log lines to `secops-mentor`, validates responses with Pydantic, and prints a formatted threat report.

Complete the TODOs in the script to:
1. Add the `format="json"` parameter to the API request
2. Implement Pydantic validation with error handling
3. Add a retry on `ValidationError` (up to 2 retries)

---

<details><summary>💡 Hint 1 — How `ollama show --modelfile` works (Click to expand)</summary>

`ollama show --modelfile <model>` reconstructs the Modelfile that produced a model. This is useful for:

1. **Inspecting community models** — understand what system prompt a Hugging Face or Ollama Hub model uses before trusting it
2. **Debugging** — confirm your `ollama create` applied the parameters you intended
3. **Forking** — copy the output, modify it, and `ollama create` a new variant

```bash
ollama show --modelfile llama3.2:1b
```

You will see the full chat template (including the special tokens like `<|start_header_id|>`) that the model expects. This is why you should use the `/api/chat` endpoint (which handles templating automatically) rather than `/api/generate` with a hand-crafted template for chat models.

</details>

<details><summary>💡 Hint 2 — Why temperature 0.2 is ideal for structured output (Click to expand)</summary>

When generating JSON, the model must commit to an exact token sequence: `{`, `"`, `s`, `e`, `v`, etc. Deviation at any point can produce invalid JSON that crashes `json.loads()`.

At `temperature=0.0` (greedy), the model always picks the highest-probability token. This sounds ideal, but it has a subtle failure mode: if the model assigns almost equal probability to two valid keys, greedy can flip between runs if internal floating-point order changes — not in practice on CPU, but it can get "stuck" producing the same wrong key repeatedly.

At `temperature=0.2`, the distribution is still sharply peaked (the highest-probability token is chosen ~95%+ of the time), but the tiny stochasticity lets the model occasionally course-correct from an early poor choice. In practice, `0.1`–`0.2` maximises JSON schema compliance while remaining effectively deterministic for most use cases.

</details>

<details><summary>💡 Hint 3 — How Pydantic `model_validate` works (Click to expand)</summary>

Pydantic v2 (required by `requirements.txt`) offers two JSON validation methods:

```python
from pydantic import BaseModel, ValidationError

class MySchema(BaseModel):
    name: str
    score: float

# Option A: validate from a JSON string directly
try:
    obj = MySchema.model_validate_json('{"name": "test", "score": 0.95}')
except ValidationError as e:
    print(e)   # structured error listing every field that failed

# Option B: validate from a dict (after json.loads)
import json
raw = '{"name": "test", "score": "not_a_float"}'
try:
    obj = MySchema.model_validate(json.loads(raw))
except ValidationError as e:
    for error in e.errors():
        print(f"Field: {error['loc']}, Issue: {error['msg']}")
```

**What Pydantic validates:**
- Type coercion: `"0.95"` → `0.95` (string to float, automatic)
- Missing required fields: raises `ValidationError` with field name
- `Literal` constraints: `severity` must be one of the allowed values
- Custom validators: add `@field_validator` for domain-specific rules

</details>

---

## ✅ Verification

- [ ] `ollama list` shows `secops-mentor` in the model list
- [ ] `ollama run secops-mentor` produces JSON-structured threat analysis
- [ ] `python exercises/ex03_custom_modelfile_client.py` runs and all Pydantic validations pass
- [ ] You can explain the difference between `Q4_K_M` and `Q2_K` and when to use each

---

<details><summary>🔧 Common Lab Errors & Fixes</summary>

**`Error: model 'secops-mentor' not found` when running exercise**
> Run `ollama create secops-mentor -f Modelfile` from the repo root first. The Modelfile path is relative to where you run the command.

**`json.JSONDecodeError` even with `format="json"`**
> Some models occasionally prefix JSON with markdown fences (` ```json `). Strip them before parsing:
> ```python
> raw = resp.json()["response"].strip()
> if raw.startswith("```"):
>     raw = raw.split("```")[1]
>     if raw.startswith("json"):
>         raw = raw[4:]
> ```

**`pydantic.ValidationError` on `severity` field**
> The model returned a capitalised severity (e.g. `"High"` vs `"high"`). Add case normalisation:
> ```python
> from pydantic import field_validator
>
> class ThreatAnalysis(BaseModel):
>     severity: str
>
>     @field_validator("severity")
>     @classmethod
>     def normalise_severity(cls, v):
>         return v.lower()
> ```

**`ollama create` fails with `Error: file not found`**
> Ensure you are running the command from the repo root where `Modelfile` lives, or use the full path: `ollama create secops-mentor -f C:\path\to\Modelfile`

</details>

---

[⬅️ Previous Lab](lab-02-prompt-to-answer-pipeline.md) | [🏠 Home](../README.md) | [➡️ Next Lab](lab-04-react-agent-from-scratch.md)
