# 📋 AI to Agents — Cheat Sheet

> One-page quick reference for LLM internals, Ollama CLI, Modelfile syntax, API endpoints, and Python snippets.

---

## 🧠 LLM Glossary

| Term | Definition |
|---|---|
| **Token** | The atomic unit of text an LLM processes. Words, sub-words, or characters depending on the tokenizer. ~1 token ≈ 0.75 words in English. |
| **BPE** | Byte-Pair Encoding — the most common tokenization algorithm. Iteratively merges the most frequent character pairs into single tokens. |
| **Embedding** | A dense numeric vector that represents a token (or sequence) in high-dimensional space. Semantically similar tokens cluster together. |
| **Cosine Similarity** | A metric measuring the angle between two embedding vectors. Score of 1.0 = identical direction (meaning), 0.0 = orthogonal, −1.0 = opposite. |
| **Attention** | The mechanism that lets each token "look at" every other token in the context to decide how much weight to give it. Core of the Transformer. |
| **KV Cache** | Key-Value cache — stores computed attention states for already-processed tokens so they don't need recomputing on each new token. |
| **Prefill** | The phase where the model processes the entire prompt at once and populates the KV cache. Measured in tokens/second. |
| **Decode** | The autoregressive phase where the model generates one token at a time, attending to the prompt + already-generated tokens. |
| **TTFT** | Time To First Token — latency from sending the request to receiving the first generated token. Dominated by prefill time. |
| **TPS** | Tokens Per Second — throughput of the decode phase. The number you watch to gauge model speed on your hardware. |
| **Temperature** | Controls output randomness. `0.0` = deterministic (always picks the most probable token). `1.0` = default randomness. `>1.0` = more creative/chaotic. |
| **Top-K** | At each step, restricts sampling to only the K most probable next tokens. Prevents very unlikely tokens from being selected. |
| **Top-P** | Nucleus sampling — restricts sampling to the smallest set of tokens whose cumulative probability ≥ P. More adaptive than Top-K. |
| **GGUF** | A binary file format for storing quantized LLM weights. Successor to GGML. Used by llama.cpp and Ollama. |
| **Q4_K_M** | A specific GGUF quantization level: 4-bit weights, K-quant method, Medium variant. Good balance of speed, size, and quality. |
| **Quantization** | Reducing model weight precision (e.g., from 32-bit float → 4-bit int) to shrink model size and speed up inference at the cost of minor quality loss. |
| **ReAct** | Reasoning + Acting — a prompting pattern where the model alternates between Thought → Action → Observation steps to solve tasks with tools. |
| **Tool Call** | A structured LLM output that requests execution of a named function with specific arguments. The result (Observation) is fed back to the model. |
| **MCP** | Model Context Protocol — an open standard for connecting LLMs to external tools, data sources, and services via a unified interface. |
| **HITL** | Human-In-The-Loop — a design pattern where an autonomous agent pauses and requests human approval before executing high-risk or irreversible actions. |

---

## ⚙️ Ollama CLI Commands

| Command | Usage | Description |
|---|---|---|
| `ollama list` | `ollama list` | List all locally downloaded models |
| `ollama ps` | `ollama ps` | Show currently loaded (running) models and their memory usage |
| `ollama pull` | `ollama pull qwen2.5:1.5b` | Download a model from the Ollama registry |
| `ollama run` | `ollama run qwen2.5:1.5b "prompt"` | Run a model interactively or with a one-shot prompt |
| `ollama show` | `ollama show qwen2.5:1.5b` | Display model info: Modelfile, parameters, template, license |
| `ollama cp` | `ollama cp qwen2.5:1.5b my-model` | Copy a model to a new name (useful before customizing) |
| `ollama rm` | `ollama rm my-model` | Remove a model from local storage |
| `ollama serve` | `ollama serve` | Start the Ollama API server (default: http://localhost:11434) |
| `ollama create` | `ollama create secops-mentor -f Modelfile` | Build a custom model from a Modelfile |

---

## 📄 Modelfile Syntax

| Instruction | Example | Purpose |
|---|---|---|
| `FROM` | `FROM qwen2.5:1.5b` | **Required.** Base model to build on. Can be a registry model or local GGUF path. |
| `PARAMETER` | `PARAMETER temperature 0.2` | Set inference parameters. Common params: `temperature`, `top_p`, `top_k`, `num_ctx`, `repeat_penalty`, `stop`. |
| `SYSTEM` | `SYSTEM """You are..."""` | Set the system prompt baked into the model. Use triple-quotes for multi-line. |
| `TEMPLATE` | `TEMPLATE """{{ .System }}..."""` | Override the chat template (Go template syntax). Usually not needed — the base model's template is inherited. |
| `MESSAGE` | `MESSAGE user "Hello"` | Pre-seed conversation history with example turns (few-shot). |
| `ADAPTER` | `ADAPTER ./lora.gguf` | Apply a LoRA adapter on top of the base model. |

**Build & run your custom model:**
```powershell
ollama create secops-mentor -f Modelfile
ollama run secops-mentor
```

---

## 🌐 Key Ollama API Endpoints

Base URL: `http://localhost:11434`

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/chat` | `POST` | Multi-turn chat with message history. Use this for agents. |
| `/api/generate` | `POST` | Single-turn raw text completion. Good for simple prompts. |
| `/api/embed` | `POST` | Generate embeddings for a text input. Use for RAG/semantic search. |
| `/api/tags` | `GET` | List all locally available models (same as `ollama list`). |
| `/api/show` | `POST` | Get detailed model info (Modelfile, parameters, template). |
| `/api/pull` | `POST` | Programmatically pull a model (streams progress). |
| `/api/delete` | `DELETE` | Remove a model by name. |
| `/api/ps` | `GET` | List currently loaded models and their GPU/RAM usage. |

---

## 🐍 Minimal Python · Ollama Chat Request

```python
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_HOST  = os.getenv("OLLAMA_HOST",  "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")

def chat(prompt: str, system: str = "You are a helpful assistant.") -> str:
    response = requests.post(
        f"{OLLAMA_HOST}/api/chat",
        json={
            "model":    OLLAMA_MODEL,
            "stream":   False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
            "options": {"temperature": 0.2, "num_ctx": 2048},
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]

if __name__ == "__main__":
    print(chat("What is a KV cache in the context of LLMs?"))
```

---

## 🔢 Quick Reference — Sampling Parameters

```
temperature  0.0  → deterministic   | 0.7 → balanced   | 1.5 → creative
top_p        0.5  → conservative    | 0.9 → standard   | 1.0 → off
top_k        10   → narrow          | 40  → standard   | 100 → wide
num_ctx      512  → short prompts   | 2048 → standard  | 4096 → long context
repeat_pen   1.0  → no penalty      | 1.1 → standard   | 1.3 → strong
```

---

> Created by [Senuk Manditha Dias](https://github.com/SenukDias) · [Ronin Tech Sec](https://youtube.com/@RoninTechSec)
