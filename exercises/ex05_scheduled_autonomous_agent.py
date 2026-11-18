"""
Lab 05 Exercise: Scheduled Autonomous Agent
Build an autonomous agent that runs on a schedule, persists state, and includes a HITL gate.

Author: Senuk Manditha Dias
"""
import os
import json
import time
import schedule
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
STATE_FILE = Path("agent_state.json")
MAX_RETRIES = 3


def load_state() -> dict:
    """Load agent state from JSON file, or return default state."""
    # TODO 1: Read STATE_FILE if it exists using json.loads(STATE_FILE.read_text())
    # TODO 2: If file doesn't exist, return default state dict:
    # {"last_run": None, "run_count": 0, "findings": [], "action_log": [], "high_risk_pending": []}
    raise NotImplementedError("Complete TODO 1-2")


def save_state(state: dict) -> None:
    """Save agent state to JSON file."""
    # TODO 3: Write state to STATE_FILE as pretty JSON (indent=2)
    # HINT: STATE_FILE.write_text(json.dumps(state, indent=2))
    raise NotImplementedError("Complete TODO 3")


def query_ollama_with_retry(prompt: str, retries: int = MAX_RETRIES) -> str:
    """Query Ollama with exponential backoff retry logic."""
    # TODO 4: Implement retry loop with exponential backoff
    # HINT: for attempt in range(retries): try: ... except Exception: time.sleep(2 ** attempt)
    # HINT: On success return response text; after all retries raise the last exception
    raise NotImplementedError("Complete TODO 4")


def hitl_gate(action_description: str, risk_level: str) -> bool:
    """Human-in-the-Loop approval gate for high-risk actions."""
    # TODO 5: If risk_level is "high" or "critical":
    #   - Print a prominent warning with the action description
    #   - Ask for user input: "Approve this action? (y/n): "
    #   - Return True if user typed 'y', False otherwise
    # TODO 6: If risk_level is "low" or "medium": return True automatically (no human needed)
    raise NotImplementedError("Complete TODO 5-6")


def run_audit_job() -> None:
    """Main audit job that runs on schedule."""
    state = load_state()
    state["run_count"] += 1
    state["last_run"] = datetime.now().isoformat()

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Running audit #{state['run_count']}...")

    # TODO 7: Build a prompt asking the LLM to analyze a simulated system log snippet
    # TODO 8: Call query_ollama_with_retry() to get findings
    # TODO 9: Append findings to state["findings"] list (keep last 10 only)
    # TODO 10: Save state

    # Simulate a high-risk action found
    high_risk_action = "Delete logs older than 7 days to free disk space"
    # TODO 11: Call hitl_gate(high_risk_action, "high")
    # TODO 12: If approved, log to state["action_log"]; if denied, log the denial
    # TODO 13: Save state again

    raise NotImplementedError("Complete TODO 7-13")


if __name__ == "__main__":
    print("Starting Autonomous Scheduled Agent...")
    print("Press Ctrl+C to stop.\n")

    # TODO 14: Schedule run_audit_job to run every 2 minutes using the schedule library
    # HINT: schedule.every(2).minutes.do(run_audit_job)
    # TODO 15: Run immediately on startup, then enter the schedule loop
    # HINT: schedule.run_pending(); time.sleep(1) in a while True loop
    raise NotImplementedError("Complete TODO 14-15")
