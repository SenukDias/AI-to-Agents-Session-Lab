"""
Lab 04 Exercise: ReAct Agent Loop
Build a ReAct (Reason + Act) agent that uses local tools to answer security questions.

Author: Senuk Manditha Dias
"""
import os
import json
import psutil  # pip install psutil if needed
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
MAX_ITERATIONS = 5


# ===== LOCAL TOOLS =====

def check_host_resources() -> dict:
    """Check current CPU, RAM, and disk usage of this machine."""
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "ram_used_gb": round(psutil.virtual_memory().used / 1e9, 2),
        "ram_total_gb": round(psutil.virtual_memory().total / 1e9, 2),
        "ram_percent": psutil.virtual_memory().percent,
        "disk_free_gb": round(psutil.disk_usage('/').free / 1e9, 2),
        "timestamp": datetime.now().isoformat(),
    }


def calculate_risk_score(severity: str, exploitability: float, asset_value: int) -> dict:
    """Calculate a simple risk score for a security finding."""
    severity_weights = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    weight = severity_weights.get(severity.lower(), 1)
    score = round(weight * exploitability * (asset_value / 10), 2)
    return {"risk_score": score, "severity": severity, "rating": "HIGH" if score > 7 else "MEDIUM" if score > 4 else "LOW"}


def search_runbook(query: str) -> dict:
    """Search the local runbook for relevant response procedures."""
    runbook = {
        "ssh brute force": "1. Block source IP with iptables. 2. Enable fail2ban. 3. Review /var/log/auth.log.",
        "malware detected": "1. Isolate the host. 2. Capture memory dump. 3. Run ClamAV scan. 4. Escalate to IR team.",
        "log4j": "1. Patch to Log4j 2.17.1+. 2. Apply WAF rule to block JNDI lookups. 3. Scan for exploitation indicators.",
        "default": "No specific runbook entry found. Escalate to Tier-2 analyst.",
    }
    for key in runbook:
        if key in query.lower():
            return {"runbook_entry": runbook[key], "matched_key": key}
    return {"runbook_entry": runbook["default"], "matched_key": "none"}


def inspect_log_entry(log_line: str) -> dict:
    """Parse a log line and extract key security-relevant fields."""
    result = {"raw": log_line, "length": len(log_line), "contains_error": "error" in log_line.lower(),
              "contains_failed": "fail" in log_line.lower(), "contains_root": "root" in log_line.lower()}
    return result


TOOLS = {
    "check_host_resources": check_host_resources,
    "calculate_risk_score": calculate_risk_score,
    "search_runbook": search_runbook,
    "inspect_log_entry": inspect_log_entry,
}

TOOL_SCHEMAS = [
    # TODO 1: Define JSON schema dicts for all 4 tools
    # HINT: Each schema = {"name": "...", "description": "...", "parameters": {"type": "object", "properties": {...}, "required": [...]}}
    # HINT: check_host_resources has NO parameters (empty properties, empty required)
    # HINT: calculate_risk_score needs: severity (string), exploitability (number), asset_value (integer)
]


def build_system_prompt() -> str:
    """Build the ReAct agent system prompt with tool descriptions."""
    # TODO 2: Return a system prompt that:
    # - Explains the ReAct loop (Thought / Action / Observation / Final Answer)
    # - Lists available tools with their schemas
    # - Instructs the model to respond with JSON: {"thought": "...", "action": "tool_name", "action_input": {...}}
    # - OR for final answer: {"thought": "...", "final_answer": "..."}
    raise NotImplementedError("Complete TODO 2")


def parse_agent_response(response_text: str) -> dict:
    """Parse the LLM response to extract thought, action, and action_input."""
    # TODO 3: Strip markdown code fences (```json ... ```) if present
    # TODO 4: json.loads() the cleaned text
    # TODO 5: Return the parsed dict (or raise ValueError if parsing fails)
    # HINT: response_text.strip().removeprefix("```json").removesuffix("```").strip()
    raise NotImplementedError("Complete TODO 3-5")


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute the named tool with given input and return result as JSON string."""
    # TODO 6: Look up tool_name in TOOLS dict
    # TODO 7: Call the function with **tool_input (unpack dict as kwargs)
    # TODO 8: Return json.dumps(result)
    # HINT: Handle KeyError (unknown tool) and TypeError (wrong args) with try/except
    raise NotImplementedError("Complete TODO 6-8")


def run_react_agent(user_query: str) -> str:
    """Run the full ReAct agent loop."""
    messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": user_query},
    ]

    for iteration in range(MAX_ITERATIONS):
        print(f"\n--- Iteration {iteration + 1}/{MAX_ITERATIONS} ---")

        # TODO 9: Call Ollama /api/chat with messages, format="json", stream=False
        # TODO 10: Extract response content from result["message"]["content"]
        # TODO 11: Call parse_agent_response() on the content
        # TODO 12: If parsed has "final_answer" key → print it and return
        # TODO 13: If parsed has "action" key → call execute_tool(), append observation to messages
        # HINT: Append assistant message: {"role": "assistant", "content": raw_response}
        # HINT: Append tool observation: {"role": "user", "content": f"Observation: {observation}"}

        raise NotImplementedError("Complete TODO 9-13")

    return "Max iterations reached without final answer."


if __name__ == "__main__":
    query = "Check the current host resources and calculate the risk score for a high severity SSH brute force attack with exploitability 0.8 on an asset valued at 9."
    print(f"Query: {query}\n")
    result = run_react_agent(query)
    print(f"\nFinal Answer: {result}")
    print("\nDone! Compare with solutions/sol04_react_agent_loop.py")
