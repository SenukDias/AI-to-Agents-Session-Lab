"""
sol04_react_agent_loop.py
ReAct (Reason + Act) Agent Loop — cybersecurity operations assistant.

Author: Senuk Manditha Dias
"""

import os
import json
import re
import datetime

import psutil
import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
MAX_ITERATIONS = 5

console = Console()


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def check_host_resources(threshold_cpu: float = 80.0, threshold_mem: float = 85.0) -> dict:
    """
    Return real host CPU, memory, and disk usage via psutil.
    Flags resources that exceed the given thresholds.
    """
    cpu_pct = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    alerts = []
    if cpu_pct >= threshold_cpu:
        alerts.append(f"CPU usage {cpu_pct:.1f}% exceeds threshold {threshold_cpu}%")
    if mem.percent >= threshold_mem:
        alerts.append(f"Memory usage {mem.percent:.1f}% exceeds threshold {threshold_mem}%")

    return {
        "cpu_percent": cpu_pct,
        "memory_percent": mem.percent,
        "memory_available_gb": round(mem.available / 1e9, 2),
        "disk_percent": disk.percent,
        "disk_free_gb": round(disk.free / 1e9, 2),
        "alerts": alerts,
        "status": "critical" if alerts else "nominal",
    }


def calculate_risk_score(
    severity: str,
    exploitability: str,
    asset_criticality: str,
) -> dict:
    """
    Compute a numeric risk score (0-100) from severity, exploitability, and
    asset criticality using a weighted model.
    """
    sev_map = {"critical": 10, "high": 7, "medium": 5, "low": 2, "info": 1}
    exp_map = {"easy": 10, "moderate": 6, "hard": 3, "theoretical": 1}
    crit_map = {"critical": 10, "high": 8, "medium": 5, "low": 2}

    sev_score = sev_map.get(severity.lower(), 5)
    exp_score = exp_map.get(exploitability.lower(), 5)
    crit_score = crit_map.get(asset_criticality.lower(), 5)

    # Weighted average: severity 40%, exploitability 35%, criticality 25%
    raw = (sev_score * 0.40) + (exp_score * 0.35) + (crit_score * 0.25)
    risk_score = round(raw * 10)  # scale to 0-100

    if risk_score >= 80:
        risk_level = "critical"
    elif risk_score >= 60:
        risk_level = "high"
    elif risk_score >= 40:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "breakdown": {
            "severity_score": sev_score,
            "exploitability_score": exp_score,
            "asset_criticality_score": crit_score,
        },
        "recommendation": (
            "Immediate remediation required." if risk_level == "critical"
            else "Schedule patching within 7 days." if risk_level == "high"
            else "Include in next maintenance cycle." if risk_level == "medium"
            else "Monitor and log."
        ),
    }


def search_runbook(keyword: str) -> dict:
    """
    Simulated runbook search. Returns relevant playbook steps for common
    incident types based on keyword matching.
    """
    keyword_lower = keyword.lower()

    runbooks: dict[str, dict] = {
        "ransomware": {
            "title": "Ransomware Response Playbook",
            "steps": [
                "Isolate affected hosts from the network immediately.",
                "Preserve volatile memory (RAM dump) before powering off.",
                "Identify patient-zero via SIEM timeline correlation.",
                "Check backup integrity and initiate restore from clean snapshot.",
                "Notify legal, compliance, and executive leadership.",
                "File incident report with CISA / relevant authority.",
            ],
            "severity": "critical",
        },
        "sql injection": {
            "title": "SQL Injection Incident Response",
            "steps": [
                "Block the offending IP at the WAF/firewall.",
                "Review application logs for data exfiltration indicators.",
                "Rotate all database credentials immediately.",
                "Apply parameterised query patches to the vulnerable endpoint.",
                "Conduct DAST scan on all public-facing endpoints.",
                "Notify DPA if PII exposure is confirmed.",
            ],
            "severity": "high",
        },
        "brute force": {
            "title": "Brute-Force / Credential Stuffing Response",
            "steps": [
                "Enable account lockout policy (≥5 failures → 15 min lockout).",
                "Force MFA enrolment for all affected accounts.",
                "Block source IPs via firewall; add to threat-intel feed.",
                "Review successful logins during the attack window.",
                "Reset passwords for accounts with successful logins.",
                "Alert users whose accounts were targeted.",
            ],
            "severity": "high",
        },
        "phishing": {
            "title": "Phishing Email Response",
            "steps": [
                "Quarantine malicious emails across all mailboxes.",
                "Block sender domain and malicious URLs at email gateway.",
                "Identify users who clicked links or opened attachments.",
                "Inspect endpoints of affected users for malware.",
                "Reset credentials for any users who entered credentials.",
                "Issue user awareness notification.",
            ],
            "severity": "medium",
        },
    }

    # Find best match
    for key, runbook in runbooks.items():
        if key in keyword_lower or keyword_lower in key:
            return {"found": True, "keyword": keyword, **runbook}

    return {
        "found": False,
        "keyword": keyword,
        "message": (
            f"No runbook found for '{keyword}'. "
            "Available topics: ransomware, sql injection, brute force, phishing."
        ),
    }


def inspect_log_entry(log_line: str) -> dict:
    """
    Parse and analyse a log line. Detects common patterns:
    HTTP status codes, IP addresses, timestamps, error keywords.
    """
    result: dict = {"raw": log_line, "indicators": [], "risk_flags": []}

    # Extract IPs
    ips = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", log_line)
    if ips:
        result["source_ips"] = ips

    # Extract HTTP status code
    http_match = re.search(r"\b([45]\d{2})\b", log_line)
    if http_match:
        code = int(http_match.group(1))
        result["http_status"] = code
        if code == 401 or code == 403:
            result["risk_flags"].append("Unauthorized / Forbidden — possible credential attack")
        elif code == 500:
            result["risk_flags"].append("Server Error — possible injection or crash exploit")
        elif code == 404 and "admin" in log_line.lower():
            result["risk_flags"].append("Scanning for admin paths")

    # Detect common threat keywords
    threat_keywords = {
        "../": "Path traversal attempt",
        "union select": "SQL injection attempt",
        "<script": "XSS attempt",
        "eval(": "Code injection attempt",
        "/etc/passwd": "Linux sensitive file access attempt",
        "cmd.exe": "Windows command injection attempt",
        "powershell": "PowerShell execution via web request",
        "base64": "Obfuscated payload (base64)",
    }
    for kw, label in threat_keywords.items():
        if kw.lower() in log_line.lower():
            result["risk_flags"].append(label)
            result["indicators"].append(kw)

    result["risk_level"] = (
        "high" if len(result["risk_flags"]) >= 2
        else "medium" if result["risk_flags"]
        else "low"
    )
    result["summary"] = (
        f"Detected {len(result['risk_flags'])} risk flag(s): "
        + ("; ".join(result["risk_flags"]) if result["risk_flags"] else "none")
    )
    return result


# ---------------------------------------------------------------------------
# Tool registry / schemas
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict] = [
    {
        "name": "check_host_resources",
        "description": (
            "Returns real-time CPU, memory, and disk usage of the current host "
            "using psutil. Optionally set thresholds for alerting."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "threshold_cpu": {
                    "type": "number",
                    "description": "CPU usage percentage threshold for alerts. Default 80.",
                },
                "threshold_mem": {
                    "type": "number",
                    "description": "Memory usage percentage threshold for alerts. Default 85.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "calculate_risk_score",
        "description": (
            "Calculates a numeric risk score (0-100) for a vulnerability based on "
            "severity, exploitability, and asset criticality using a weighted model."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "severity": {
                    "type": "string",
                    "enum": ["critical", "high", "medium", "low", "info"],
                    "description": "CVSS severity rating of the vulnerability.",
                },
                "exploitability": {
                    "type": "string",
                    "enum": ["easy", "moderate", "hard", "theoretical"],
                    "description": "How easy is it to exploit in the wild.",
                },
                "asset_criticality": {
                    "type": "string",
                    "enum": ["critical", "high", "medium", "low"],
                    "description": "Business criticality of the affected asset.",
                },
            },
            "required": ["severity", "exploitability", "asset_criticality"],
        },
    },
    {
        "name": "search_runbook",
        "description": (
            "Search the internal incident-response runbook library. "
            "Provide a keyword such as 'ransomware', 'sql injection', "
            "'brute force', or 'phishing' to retrieve response steps."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "Incident type keyword to search for.",
                },
            },
            "required": ["keyword"],
        },
    },
    {
        "name": "inspect_log_entry",
        "description": (
            "Parse and risk-analyse a single log line. Detects IPs, HTTP status "
            "codes, SQL injection, XSS, path traversal, and other threat patterns."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "log_line": {
                    "type": "string",
                    "description": "The raw log line to inspect.",
                },
            },
            "required": ["log_line"],
        },
    },
]

TOOL_FUNCTIONS: dict = {
    "check_host_resources": check_host_resources,
    "calculate_risk_score": calculate_risk_score,
    "search_runbook": search_runbook,
    "inspect_log_entry": inspect_log_entry,
}


# ---------------------------------------------------------------------------
# Agent machinery
# ---------------------------------------------------------------------------

def build_system_prompt() -> str:
    tool_desc = json.dumps(TOOL_SCHEMAS, indent=2)
    return f"""You are a cybersecurity ReAct agent. You reason step-by-step and use tools to answer questions.

## ReAct Loop

Each response MUST be a JSON object (no markdown fences) with ONE of these shapes:

### A) Use a tool
{{
  "thought": "<your reasoning about what to do next>",
  "action": "<tool_name>",
  "action_input": {{ <tool parameters as JSON object> }}
}}

### B) Final answer
{{
  "thought": "<final reasoning>",
  "final_answer": "<complete answer to the user's query>"
}}

## Rules
- Always think before acting. The "thought" field is mandatory.
- Call only one tool per response.
- Base your final answer on observed tool results, not prior assumptions.
- If a tool returns an error, adapt and try a different approach.
- If you have enough information, give the final answer immediately.
- Respond ONLY with the JSON object — no prose outside it.

## Available Tools
{tool_desc}

## Example exchange
User: Is the host under memory pressure?
Agent: {{"thought": "I need to check current memory usage.", "action": "check_host_resources", "action_input": {{}}}}
Observation: {{"cpu_percent": 12.3, "memory_percent": 91.2, "status": "critical", "alerts": ["Memory usage 91.2% exceeds threshold 85%"]}}
Agent: {{"thought": "Memory is at 91.2% which is critical.", "final_answer": "Yes — the host is under severe memory pressure (91.2%). Immediate investigation recommended."}}
"""


def parse_agent_response(text: str) -> dict:
    """Strip ```json fences, parse JSON, return dict. Raises ValueError on failure."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    return json.loads(text)


def execute_tool(name: str, input_dict: dict) -> str:
    """Dispatch to the named tool function; return JSON string of result."""
    fn = TOOL_FUNCTIONS.get(name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool: '{name}'"})
    try:
        result = fn(**input_dict)
        return json.dumps(result, indent=2)
    except TypeError as exc:
        return json.dumps({"error": f"Tool parameter error: {exc}"})
    except Exception as exc:
        return json.dumps({"error": f"Tool execution error: {exc}"})


def _chat(messages: list[dict]) -> str:
    """POST /api/chat with format=json; return assistant message content."""
    url = f"{OLLAMA_HOST}/api/chat"
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "format": "json",
    }
    resp = requests.post(url, json=payload, timeout=180)
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def run_react_agent(query: str) -> str | None:
    """
    Main ReAct loop. Runs up to MAX_ITERATIONS rounds of Thought → Action →
    Observation, then returns the final answer or None on failure.
    """
    console.print(
        Panel(
            Text(f"🤖  Query: {query}", style="bold yellow"),
            title="[bold yellow]ReAct Agent[/bold yellow]",
            style="on grey7",
            border_style="yellow",
        )
    )

    messages: list[dict] = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": query},
    ]

    for iteration in range(1, MAX_ITERATIONS + 1):
        console.rule(f"[yellow]Iteration {iteration} / {MAX_ITERATIONS}[/yellow]")

        # --- LLM call ---
        try:
            raw = _chat(messages)
        except requests.RequestException as exc:
            console.print(f"[red]LLM call failed:[/red] {exc}")
            return None

        # --- Parse ---
        try:
            parsed = parse_agent_response(raw)
        except (ValueError, json.JSONDecodeError) as exc:
            console.print(
                Panel(
                    f"[red]Parse error:[/red] {exc}\n[dim]Raw:[/dim] {raw[:300]}",
                    title="[red]Parse Failure[/red]",
                    style="on grey7",
                    border_style="red",
                )
            )
            # Append error observation and continue
            messages.append({"role": "assistant", "content": raw})
            messages.append({
                "role": "user",
                "content": f"ERROR: Your response was not valid JSON. Got: {exc}. Try again.",
            })
            continue

        thought = parsed.get("thought", "")
        if thought:
            console.print(
                Panel(
                    thought,
                    title="[bold yellow]💭 Thought[/bold yellow]",
                    style="on grey7",
                    border_style="yellow",
                )
            )

        # --- Final answer ---
        if "final_answer" in parsed:
            final = parsed["final_answer"]
            console.print(
                Panel(
                    Text(final, style="bold white"),
                    title="[bold green]✅  Final Answer[/bold green]",
                    style="on grey7",
                    border_style="green",
                )
            )
            return final

        # --- Tool action ---
        if "action" in parsed:
            tool_name = parsed["action"]
            tool_input = parsed.get("action_input", {})

            console.print(
                Panel(
                    f"[bold cyan]Tool:[/bold cyan] {tool_name}\n"
                    f"[bold cyan]Input:[/bold cyan] {json.dumps(tool_input, indent=2)}",
                    title="[bold cyan]⚙  Action[/bold cyan]",
                    style="on grey7",
                    border_style="cyan",
                )
            )

            observation = execute_tool(tool_name, tool_input)

            console.print(
                Panel(
                    observation,
                    title="[white]🔭 Observation[/white]",
                    style="on grey7",
                    border_style="white",
                )
            )

            # Append assistant turn + observation to history
            messages.append({"role": "assistant", "content": raw})
            messages.append({
                "role": "user",
                "content": f"Observation: {observation}",
            })
            continue

        # Unexpected shape — treat as error
        console.print(
            f"[yellow]Unexpected response shape (no 'action' or 'final_answer'):[/yellow] {raw[:200]}"
        )
        messages.append({"role": "assistant", "content": raw})
        messages.append({
            "role": "user",
            "content": "ERROR: Response must contain either 'action' or 'final_answer'. Try again.",
        })

    console.print(
        Panel(
            "[yellow]Max iterations reached without a final answer.[/yellow]",
            style="on grey7",
            border_style="yellow",
        )
    )
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

QUERIES = [
    (
        "My web server is showing a lot of 401 errors. "
        "I found this log line: "
        "'192.168.1.55 - - [18/Nov/2024:03:12:44 +0000] \"POST /wp-login.php HTTP/1.1\" 401 185'. "
        "What is the risk level and what should I do?"
    ),
    (
        "We found a critical SQL injection vulnerability on our public web app "
        "that also runs on a business-critical e-commerce server. "
        "Exploitation is easy. What is the risk score and what are the response steps?"
    ),
]


def main() -> None:
    console.print(
        Panel(
            Text("⚙  ReAct Agent Loop", style="bold yellow", justify="center"),
            subtitle="[dim]Reason + Act · Cybersecurity Operations Assistant[/dim]",
            style="on grey7",
            border_style="yellow",
        )
    )

    for query in QUERIES:
        run_react_agent(query)
        console.print()

    console.print(
        Panel(
            "[bold green]✓ ReAct agent session complete.[/bold green]",
            style="on grey7",
            border_style="green",
        )
    )


if __name__ == "__main__":
    main()
