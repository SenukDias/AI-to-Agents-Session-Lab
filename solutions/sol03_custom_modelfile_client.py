"""
sol03_custom_modelfile_client.py
Custom Modelfile Client — SecOps Mentor threat analysis with Pydantic validation.

Author: Senuk Manditha Dias
"""

import os
import json
import re

import requests
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
CUSTOM_MODEL = "secops-mentor"

console = Console()


# ---------------------------------------------------------------------------
# Pydantic model
# ---------------------------------------------------------------------------

class ThreatReport(BaseModel):
    severity: str                    # critical / high / medium / low
    cve: str                         # e.g. "CVE-2024-1234" or "N/A"
    description: str
    remediation: list[str]
    affected_systems: list[str]


# ---------------------------------------------------------------------------
# Ollama helpers
# ---------------------------------------------------------------------------

def check_model_exists(model_name: str) -> bool:
    """GET /api/tags and return True if model_name is in the list."""
    url = f"{OLLAMA_HOST}/api/tags"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        models = resp.json().get("models", [])
        # Each entry has a "name" field like "qwen2.5:1.5b"
        names = [m.get("name", "") for m in models]
        # Also check without tag suffix
        base_names = [n.split(":")[0] for n in names]
        return model_name in names or model_name in base_names
    except requests.RequestException as exc:
        console.print(f"[red]Could not reach Ollama to check models:[/red] {exc}")
        return False


def query_model(model: str, prompt: str, use_format_json: bool = True) -> str:
    """
    POST /api/chat with optional format='json'.
    Returns the assistant message content as a string.
    """
    url = f"{OLLAMA_HOST}/api/chat"
    payload: dict = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    if use_format_json:
        payload["format"] = "json"

    try:
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"]
    except requests.RequestException as exc:
        console.print(f"[red]Query failed for model {model}:[/red] {exc}")
        raise


def _strip_json_fences(text: str) -> str:
    """Remove ```json ... ``` fences if present."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _build_analysis_prompt(threat_description: str) -> str:
    return (
        "You are a cybersecurity expert. Analyze the following threat and respond ONLY with "
        "a valid JSON object matching this exact schema:\n"
        "{\n"
        '  "severity": "<critical|high|medium|low>",\n'
        '  "cve": "<CVE number or N/A>",\n'
        '  "description": "<concise technical description>",\n'
        '  "remediation": ["<step 1>", "<step 2>", "..."],\n'
        '  "affected_systems": ["<system 1>", "<system 2>", "..."]\n'
        "}\n\n"
        f"Threat: {threat_description}\n\n"
        "Respond ONLY with the JSON object. No markdown, no explanation."
    )


# ---------------------------------------------------------------------------
# Threat analysis
# ---------------------------------------------------------------------------

def analyze_threat(threat_description: str) -> ThreatReport:
    """
    Try the custom 'secops-mentor' model first; fall back to base model.
    Retries once on JSON parse failure. Returns a validated ThreatReport.
    """
    if check_model_exists(CUSTOM_MODEL):
        active_model = CUSTOM_MODEL
        console.print(
            f"[green]Using custom model:[/green] [yellow]{CUSTOM_MODEL}[/yellow]"
        )
    else:
        active_model = MODEL
        console.print(
            f"[dim]Custom model '{CUSTOM_MODEL}' not found. "
            f"Falling back to[/dim] [yellow]{MODEL}[/yellow]"
        )

    prompt = _build_analysis_prompt(threat_description)

    for attempt in range(1, 3):  # up to 2 attempts
        try:
            raw = query_model(active_model, prompt, use_format_json=True)
            cleaned = _strip_json_fences(raw)
            parsed = json.loads(cleaned)
            report = ThreatReport.model_validate(parsed)
            return report
        except (json.JSONDecodeError, ValidationError, KeyError) as exc:
            console.print(
                f"[yellow]Attempt {attempt} — JSON/validation error:[/yellow] {exc}"
            )
            if attempt == 2:
                console.print("[red]Both attempts failed. Raising error.[/red]")
                raise
            # On retry, ask more strictly
            prompt = (
                "Return ONLY valid JSON — no prose, no markdown. "
                + _build_analysis_prompt(threat_description)
            )

    # Unreachable, but satisfies type checker
    raise RuntimeError("analyze_threat: exhausted retries")


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

SEVERITY_STYLES: dict[str, str] = {
    "critical": "bold white on red",
    "high": "bold white on dark_orange",
    "medium": "bold black on yellow",
    "low": "bold black on green",
}


def display_threat_report(report: ThreatReport) -> None:
    """Render a ThreatReport in a styled Rich Panel."""
    sev_key = report.severity.lower()
    sev_style = SEVERITY_STYLES.get(sev_key, "bold yellow")
    sev_badge = Text(f" {report.severity.upper()} ", style=sev_style)

    remediation_text = "\n".join(
        f"  {i+1}. {step}" for i, step in enumerate(report.remediation)
    )
    affected_text = "\n".join(f"  • {s}" for s in report.affected_systems)

    body = Text.assemble(
        ("Severity: ", "bold yellow"),
        sev_badge,
        "\n",
        ("CVE: ", "bold yellow"),
        (report.cve, "white"),
        "\n\n",
        ("Description\n", "bold yellow"),
        (report.description, "white"),
        "\n\n",
        ("Remediation Steps\n", "bold yellow"),
        (remediation_text, "white"),
        "\n\n",
        ("Affected Systems\n", "bold yellow"),
        (affected_text, "cyan"),
    )

    console.print(
        Panel(
            body,
            title="[bold yellow]🛡  Threat Report[/bold yellow]",
            style="on grey7",
            border_style="yellow",
            padding=(1, 2),
        )
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

THREAT_SCENARIOS = [
    (
        "A critical SQL injection vulnerability was discovered in the company's "
        "web application login form. Attackers could bypass authentication and "
        "dump the entire user database. The application uses MySQL 8.0 and is "
        "exposed publicly on port 443."
    ),
    (
        "An unpatched Log4Shell vulnerability (Log4j remote code execution) has "
        "been detected in the internal SIEM server running Java 8. Network scans "
        "show active exploitation attempts from external IPs targeting the JNDI "
        "lookup endpoint."
    ),
]


def main() -> None:
    console.print(
        Panel(
            Text("🛡  Custom Modelfile Client", style="bold yellow", justify="center"),
            subtitle="[dim]SecOps Mentor · Threat Analysis · Pydantic Validation[/dim]",
            style="on grey7",
            border_style="yellow",
        )
    )

    for idx, scenario in enumerate(THREAT_SCENARIOS, start=1):
        console.rule(f"[yellow]Threat Scenario {idx}[/yellow]")
        console.print(f"[dim]{scenario[:120]}…[/dim]")

        try:
            report = analyze_threat(scenario)
            display_threat_report(report)
        except Exception as exc:
            console.print(f"[red]Analysis failed:[/red] {exc}")

    console.print(
        Panel(
            "[bold green]✓ Threat analysis complete.[/bold green]",
            style="on grey7",
            border_style="green",
        )
    )


if __name__ == "__main__":
    main()
