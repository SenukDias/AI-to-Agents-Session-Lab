<p align="center">
  <img src="../assets/bento/hero-banner.svg" alt="AI to Agents Session Lab" width="100%"/>
</p>

![Lab 04](https://img.shields.io/badge/Lab%2004-ReAct%20Agent%20from%20Scratch-FACC15?style=for-the-badge&labelColor=0E1013&logoColor=FACC15)
![Time](https://img.shields.io/badge/Time-60%20min-white?style=for-the-badge&labelColor=0E1013)
![Difficulty](https://img.shields.io/badge/Difficulty-Intermediate-FACC15?style=for-the-badge&labelColor=0E1013)
![CPU Only](https://img.shields.io/badge/CPU%20Only-No%20GPU%20Required-FACC15?style=for-the-badge&labelColor=0E1013)

[⬅️ Previous Lab](lab-03-ollama-cli-and-modelfile.md) | [🏠 Home](../README.md) | [➡️ Next Lab](lab-05-agentic-task-scheduling.md)

---

# Lab 04: ReAct Agent from Scratch

## 🎯 Learning Objectives

By the end of this lab you will be able to:

- Articulate the difference between a passive LLM and an active agent
- Explain the ReAct (Reason + Act) loop and trace its Thought → Action → Observation → Answer cycle
- Build four Python tool functions and expose them to an LLM via JSON schema
- Implement a ReAct agent loop with a `max_iterations` safety guard
- Manage multi-turn conversation history to give the agent persistent context
- Run a fully local, CPU-only agent that reasons over real system data

---

## 📚 Theory

### 1. Passive LLM vs Active Agent

| | Passive LLM | Active Agent |
|---|---|---|
| **Input** | A single prompt | A goal / task description |
| **Process** | One forward pass → one response | Iterative loop: reason → act → observe |
| **Tools** | None | Calculator, search, APIs, file I/O, shell |
| **Memory** | Stateless (no context between calls) | Maintains conversation history + optionally persistent state |
| **Output** | Text | Actions taken + final answer |
| **Failure mode** | Hallucination | Infinite loops, wrong tool calls |

The key insight: **an LLM alone can only recall; an agent can discover.** When a task requires information that wasn't in the training data (current system metrics, live logs, today's date), only an agent with tool access can answer correctly.

---

### 2. The ReAct Loop

**ReAct** (Yao et al., 2022) is the dominant pattern for LLM agents. It interleaves reasoning traces with tool calls, grounding the agent in real-world observations at each step.

![ReAct Reasoning Loop](../assets/diagrams/08-react-reasoning-loop.png)

**Cycle:**

```
┌──────────────────────────────────────────────────────┐
│                    REACT LOOP                        │
│                                                      │
│  User Goal                                           │
│      │                                               │
│      ▼                                               │
│  ┌─────────┐    Thought: "I need to check CPU usage" │
│  │   LLM   │ ──────────────────────────────────────▶ │
│  │ Reasons │    Action: check_host_resources({})     │
│  └─────────┘                                         │
│      ▲                                               │
│      │  Observation: {"cpu": 78, "ram_free_mb": 512} │
│      │                                               │
│  ┌──────────┐                                        │
│  │  Tool    │  ← Python function executed locally    │
│  │ Executor │                                        │
│  └──────────┘                                        │
│      │                                               │
│      └─── Repeat until: Final Answer or max_iter     │
└──────────────────────────────────────────────────────┘
```

**The four states:**
1. **Thought** — the LLM's internal reasoning about what to do next (not shown to user)
2. **Action** — a tool call: `{"name": "check_host_resources", "arguments": {}}`
3. **Observation** — the tool's return value, injected back into conversation history
4. **Final Answer** — when the LLM decides it has enough information to respond directly

---

### 3. Anthropic's Augmented LLM Pattern

![Anthropic Augmented LLM](../assets/diagrams/07-anthropic-augmented-llm.png)

Anthropic's model card for Claude describes the "Augmented LLM" — an LLM extended with three primitives:

| Primitive | Purpose |
|---|---|
| **Tools** | Extend what the LLM can *do* (web search, code execution, API calls) |
| **Memory** | Extend what the LLM can *remember* (vector DBs, conversation history, files) |
| **Retrieval** | Extend what the LLM can *know* (RAG, document stores, real-time data) |

In this lab, we implement **Tools** (the foundation) and **Memory** (conversation history). Lab 05 adds persistence between agent runs.

---

### 4. Tool / Function Calling

![LLM Function Calling](../assets/diagrams/06-llm-function-calling.jpeg)

Modern instruction-tuned models (including `qwen2.5:1.5b`) support **function calling**: you describe your tools in JSON, the model decides which one to call, and returns a structured JSON object instead of plain text.

**How Ollama handles tool calling:**

1. You include a `tools` array in the `/api/chat` request (OpenAI-compatible format)
2. When the model wants to call a tool, it returns a message with `tool_calls` instead of `content`
3. You execute the function locally and append the result as a `tool` role message
4. You re-send the updated conversation; the model continues reasoning

---

### 5. The Four Tools

**Tool 1 — `check_host_resources`**
```python
import psutil

def check_host_resources() -> dict:
    """Return current CPU %, RAM usage, and disk free space."""
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "ram_total_mb": round(psutil.virtual_memory().total / 1e6),
        "ram_free_mb": round(psutil.virtual_memory().available / 1e6),
        "disk_free_gb": round(psutil.disk_usage("/").free / 1e9, 1)
    }
```

**Tool 2 — `calculate_risk_score`**
```python
def calculate_risk_score(failed_logins: int, source_ip: str, is_internal: bool) -> dict:
    """Calculate a numeric risk score (0-100) for a login event."""
    score = min(failed_logins * 5, 60)
    if not is_internal:
        score += 30
    if source_ip.startswith("10.0.0."):
        score = max(score - 20, 0)
    severity = "critical" if score >= 80 else "high" if score >= 60 else "medium" if score >= 40 else "low"
    return {"risk_score": score, "severity": severity, "source_ip": source_ip}
```

**Tool 3 — `search_runbook`**
```python
RUNBOOKS = {
    "brute_force": "1. Block source IP at firewall\n2. Reset compromised account\n3. Enable MFA",
    "data_exfil": "1. Isolate endpoint\n2. Capture network traffic\n3. Notify CISO",
    "malware": "1. Quarantine host\n2. Run AV scan\n3. Restore from clean backup"
}

def search_runbook(incident_type: str) -> dict:
    """Look up the standard remediation runbook for an incident type."""
    key = incident_type.lower().replace(" ", "_").replace("-", "_")
    runbook = RUNBOOKS.get(key, "No runbook found. Escalate to Tier 3.")
    return {"incident_type": incident_type, "runbook": runbook}
```

**Tool 4 — `inspect_log_entry`**
```python
import re
from datetime import datetime

def inspect_log_entry(log_line: str) -> dict:
    """Parse a syslog/auth.log line and extract structured fields."""
    pattern = r"(\w+ \d+ \d+:\d+:\d+) (\S+) (\S+)\[(\d+)\]: (.*)"
    match = re.match(pattern, log_line)
    if not match:
        return {"raw": log_line, "parsed": False, "error": "Unrecognised log format"}
    timestamp, host, service, pid, message = match.groups()
    return {
        "timestamp": timestamp,
        "host": host,
        "service": service,
        "pid": int(pid),
        "message": message,
        "parsed": True
    }
```

---

### 6. JSON Tool Schema (OpenAI-Compatible)

Each tool is described to the LLM in a JSON schema so it knows what parameters to pass:

```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_host_resources",
            "description": "Return current CPU percent, RAM, and disk space of the local machine.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_risk_score",
            "description": "Calculate a risk score (0-100) for a login event based on failed attempts and source IP.",
            "parameters": {
                "type": "object",
                "properties": {
                    "failed_logins": {"type": "integer", "description": "Number of failed login attempts"},
                    "source_ip": {"type": "string", "description": "Source IP address of the login attempt"},
                    "is_internal": {"type": "boolean", "description": "True if the IP is on the internal network"}
                },
                "required": ["failed_logins", "source_ip", "is_internal"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_runbook",
            "description": "Look up the standard remediation runbook for an incident type.",
            "parameters": {
                "type": "object",
                "properties": {
                    "incident_type": {"type": "string", "description": "Type of incident (brute_force, data_exfil, malware)"}
                },
                "required": ["incident_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_log_entry",
            "description": "Parse a raw syslog/auth.log line and extract structured fields.",
            "parameters": {
                "type": "object",
                "properties": {
                    "log_line": {"type": "string", "description": "Raw log line to parse"}
                },
                "required": ["log_line"]
            }
        }
    }
]
```

---

### 7. The Agent Loop with Safety Guard

```python
import requests, json

TOOL_MAP = {
    "check_host_resources": check_host_resources,
    "calculate_risk_score": calculate_risk_score,
    "search_runbook": search_runbook,
    "inspect_log_entry": inspect_log_entry,
}

def run_agent(user_goal: str, max_iterations: int = 5) -> str:
    messages = [
        {"role": "system", "content": "You are a SecOps analyst with access to local tools. Use them to investigate and respond to incidents."},
        {"role": "user", "content": user_goal}
    ]

    for iteration in range(max_iterations):
        resp = requests.post(
            "http://localhost:11434/api/chat",
            json={"model": "qwen2.5:1.5b", "messages": messages, "tools": TOOLS, "stream": False}
        )
        message = resp.json()["message"]
        messages.append(message)   # append assistant's response to history

        # Did the LLM return a tool call or a final answer?
        if message.get("tool_calls"):
            for tool_call in message["tool_calls"]:
                fn_name = tool_call["function"]["name"]
                fn_args = tool_call["function"]["arguments"]

                # Execute the tool locally
                try:
                    result = TOOL_MAP[fn_name](**fn_args)
                except Exception as e:
                    result = {"error": str(e)}

                # Append the tool result as an observation
                messages.append({
                    "role": "tool",
                    "content": json.dumps(result)
                })
        else:
            # No tool call → LLM gave a final answer
            return message.get("content", "")

    # Safety guard: exceeded max_iterations
    return f"[Agent stopped after {max_iterations} iterations without a final answer]"
```

> [!IMPORTANT]
> The `max_iterations=5` guard prevents infinite loops where a buggy or confused model keeps calling tools in a cycle. Always set this in production agents.

---

### 8. Multi-Turn Conversation History

The `messages` list is the agent's working memory within a session. Its structure follows the OpenAI chat format:

```
[
  {"role": "system",    "content": "...system prompt..."},
  {"role": "user",      "content": "Investigate this incident"},
  {"role": "assistant", "content": null, "tool_calls": [...]},   ← tool call
  {"role": "tool",      "content": "{\"cpu_percent\": 78}"},     ← observation
  {"role": "assistant", "content": null, "tool_calls": [...]},   ← second tool call
  {"role": "tool",      "content": "{\"risk_score\": 85}"},      ← second observation
  {"role": "assistant", "content": "Based on the data..."}       ← final answer
]
```

Each turn appends messages; the full history is re-sent with every request so the model retains context.

> [!TIP]
> On CPU with limited RAM, long histories slow down Prefill. Trim the history to the last N turns (`messages[-N:]`) if TTFT becomes unacceptable.

---

### Animated Overview

![ReAct Scheduler](../assets/bento/react-scheduler-animated.svg)

---

## 🔬 Hands-On Steps

### Step 1 — Read the Exercise File

Open `exercises/ex04_react_agent_loop.py`. It contains the tool implementations and TODOs.

### Step 2 — Complete the TODOs

**TODO 1** — Implement the `tool_calls` detection and dispatch logic

**TODO 2** — Wrap the tool execution in `try/except` and return `{"error": str(e)}` on failure

**TODO 3** — Add the `max_iterations` guard

### Step 3 — Run the Agent

```bash
python exercises/ex04_react_agent_loop.py
```

The agent will be given this task:
> "My server is behaving strangely. Check its resources, then analyse this log line: `Nov 18 03:21:07 prod-server sshd[1234]: Failed password for admin from 203.0.113.42 port 54321 ssh2` and calculate the risk score. Finally, give me the runbook for the incident type."

Watch the agent work through 3–4 iterations before producing a final structured report.

---

<details><summary>💡 Hint 1 — How to detect if LLM returned a tool_call vs final answer (Click to expand)</summary>

When using `/api/chat` with `tools`, inspect the `message` object in the response:

```python
message = resp.json()["message"]

# Case A: Tool call requested
if message.get("tool_calls"):
    for tc in message["tool_calls"]:
        name = tc["function"]["name"]
        args = tc["function"]["arguments"]  # may be dict or JSON string
        # Normalise arguments to dict
        if isinstance(args, str):
            args = json.loads(args)
        # Execute: TOOL_MAP[name](**args)

# Case B: Final text answer
elif message.get("content"):
    final_answer = message["content"]

# Case C: Empty (edge case — model returned nothing useful)
else:
    # Retry or escalate
    pass
```

> [!NOTE]
> `qwen2.5:1.5b` sometimes returns `arguments` as a JSON **string** rather than a dict. Always normalise with `json.loads()` if `isinstance(args, str)`.

</details>

<details><summary>💡 Hint 2 — JSON parsing with try/except (Click to expand)</summary>

Tool arguments from the LLM should always be parsed defensively:

```python
import json

def safe_parse_args(raw_args) -> dict:
    if isinstance(raw_args, dict):
        return raw_args
    if isinstance(raw_args, str):
        try:
            return json.loads(raw_args)
        except json.JSONDecodeError as e:
            # LLM returned malformed JSON — log and return empty dict
            print(f"[WARN] Failed to parse tool args: {e}")
            print(f"[WARN] Raw args: {raw_args!r}")
            return {}
    return {}

# When executing a tool:
try:
    args = safe_parse_args(tool_call["function"]["arguments"])
    result = TOOL_MAP[fn_name](**args)
except TypeError as e:
    # Missing required argument or unexpected keyword
    result = {"error": f"Invalid arguments: {e}"}
except Exception as e:
    result = {"error": f"Tool execution failed: {e}"}
```

Always append an error observation back to the history instead of crashing — the agent can then reason about the failure and try a different approach.

</details>

<details><summary>💡 Hint 3 — Conversation history format (Click to expand)</summary>

The `messages` list has strict role ordering rules for `qwen2.5`:

```python
# ✅ VALID — tool result immediately follows assistant tool_call
messages = [
    {"role": "system",    "content": "..."},
    {"role": "user",      "content": "..."},
    {"role": "assistant", "content": None, "tool_calls": [...]},
    {"role": "tool",      "content": json.dumps(result)},   ← always a string
    {"role": "assistant", "content": "Final answer"},
]

# ❌ INVALID — tool result without preceding tool_call
messages = [
    {"role": "tool", "content": "..."},   # nothing before it
]

# ❌ INVALID — two consecutive user messages
messages = [
    {"role": "user", "content": "first question"},
    {"role": "user", "content": "second question"},   # merge into one
]
```

**Key rules:**
- `tool` messages must immediately follow the `assistant` message that requested the call
- If the assistant made multiple `tool_calls` in one response, append one `tool` message per call, in order
- `tool` message `content` must be a **string** (JSON-serialise dicts with `json.dumps()`)
- Always include the `system` message as the first element

</details>

---

## ✅ Verification

- [ ] `python exercises/ex04_react_agent_loop.py` runs and the agent produces a multi-step analysis
- [ ] You can trace the Thought → Action → Observation cycle in the printed output
- [ ] The agent stops after `max_iterations` if it enters a loop
- [ ] You understand why the `role: "tool"` message must follow the `role: "assistant"` tool_call message

---

<details><summary>🔧 Common Lab Errors & Fixes</summary>

**`KeyError: 'tool_calls'` on message**
> Use `.get("tool_calls")` instead of `["tool_calls"]` — the key is absent (not None) when the model returns a plain text answer.

**Tool call loop — agent keeps calling the same tool**
> Add a deduplication check: if the same tool with the same arguments was called in the previous iteration, skip the call and inject a synthetic observation: `{"note": "Already called, see previous result."}`. Increase `max_iterations` only if genuinely needed.

**Agent always says "I don't have the ability to call tools"**
> This means the model is not function-calling capable or the `tools` parameter is not supported by the Ollama version. Update Ollama to ≥ 0.3.0 and use `qwen2.5:1.5b` (not `llama3.2:1b`, which has weaker tool-call support).

**`psutil` not found**
> Run `pip install psutil` or add it to `requirements.txt` and `pip install -r requirements.txt`.

**Arguments come back as a JSON string, not a dict**
> `args = json.loads(args) if isinstance(args, str) else args` — see Hint 2 above.

</details>

---

[⬅️ Previous Lab](lab-03-ollama-cli-and-modelfile.md) | [🏠 Home](../README.md) | [➡️ Next Lab](lab-05-agentic-task-scheduling.md)
