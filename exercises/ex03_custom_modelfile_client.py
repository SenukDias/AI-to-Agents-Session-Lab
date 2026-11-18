"""
Lab 03 Exercise: Custom Modelfile Client
Query the secops-mentor custom model and validate structured JSON output.

Author: Senuk Manditha Dias
"""
import os
import json
import requests
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError
from typing import List

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
CUSTOM_MODEL = "secops-mentor"
FALLBACK_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")


class ThreatReport(BaseModel):
    """Pydantic schema for structured threat analysis output."""
    severity: str          # "critical", "high", "medium", "low"
    cve: str               # CVE ID or "N/A"
    description: str       # Brief description of the threat
    # TODO 1: Add a 'remediation' field as List[str] (list of remediation steps)
    # TODO 2: Add an 'affected_systems' field as List[str]
    # HINT: from typing import List; field: List[str]


def check_model_exists(model_name: str) -> bool:
    """Check if a model is available in Ollama."""
    # TODO 3: GET request to f"{OLLAMA_HOST}/api/tags"
    # HINT: Response is {"models": [{"name": "...", ...}, ...]}
    # HINT: Check if model_name appears in any model's "name" field
    raise NotImplementedError("Complete TODO 3")


def query_model(model: str, prompt: str) -> str:
    """Query a model and return raw text response."""
    # TODO 4: POST to /api/chat with format="json" to enforce JSON output
    # HINT: messages = [{"role": "user", "content": prompt}]
    # HINT: Set "format": "json" in the request body for structured output
    raise NotImplementedError("Complete TODO 4")


def analyze_threat(threat_description: str) -> ThreatReport:
    """Send a threat description and get a structured ThreatReport back."""
    system_prompt = """Analyze the following security threat and respond ONLY with valid JSON matching this schema:
{"severity": "critical|high|medium|low", "cve": "CVE-XXXX-XXXXX or N/A", "description": "...", "remediation": ["step1", "step2"], "affected_systems": ["system1"]}"""

    full_prompt = f"{system_prompt}\n\nThreat: {threat_description}"

    # TODO 5: Determine which model to use (custom or fallback), call query_model()
    # TODO 6: Parse the JSON response string
    # TODO 7: Validate with ThreatReport.model_validate(parsed_json) and return
    # HINT: Wrap in try/except (json.JSONDecodeError, ValidationError)
    raise NotImplementedError("Complete TODO 5-7")


if __name__ == "__main__":
    test_threats = [
        "Apache Log4j remote code execution vulnerability allowing unauthenticated attackers to execute arbitrary code",
        "SSH brute force attack detected from IP 192.168.1.100 with 500 failed login attempts in 60 seconds",
    ]

    for threat in test_threats:
        print(f"\nAnalyzing: {threat[:60]}...")
        # TODO 8: Call analyze_threat() and print the result nicely
        # HINT: report.model_dump() gives a dict you can pretty-print
    print("\nDone! Compare with solutions/sol03_custom_modelfile_client.py")
