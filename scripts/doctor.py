"""
doctor.py — Pre-flight hardware and Ollama diagnostics
Author: Senuk Manditha Dias
"""

import sys
import os
import socket
import subprocess
import importlib

import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")

console = Console()

STATUS_PASS = "[bold green]✅ PASS[/bold green]"
STATUS_WARN = "[bold yellow]⚠️  WARN[/bold yellow]"
STATUS_FAIL = "[bold red]❌ FAIL[/bold red]"
STATUS_INFO = "[bold cyan]ℹ️  INFO[/bold cyan]"


def build_table() -> Table:
    t = Table(
        title="[bold white]Pre-flight Diagnostics[/bold white]",
        box=box.ROUNDED,
        show_lines=True,
        header_style="bold white on #0E1013",
        border_style="#FACC15",
        expand=True,
    )
    t.add_column("Check", style="bold cyan", min_width=30)
    t.add_column("Detail", style="white", min_width=50)
    t.add_column("Status", justify="center", min_width=12)
    return t


def check_python_version():
    vi = sys.version_info
    version_str = f"Python {vi.major}.{vi.minor}.{vi.micro}"
    if vi >= (3, 9):
        return version_str, "pass"
    elif vi >= (3, 8):
        return f"{version_str} (Python 3.9+ recommended)", "warn"
    else:
        return f"{version_str} (Python 3.8+ required)", "fail"


def check_ram():
    try:
        import psutil
        avail_gb = psutil.virtual_memory().available / 1e9
        total_gb = psutil.virtual_memory().total / 1e9
        detail = f"{avail_gb:.1f} GB free / {total_gb:.1f} GB total"
        if avail_gb >= 6:
            return detail, "pass"
        elif avail_gb >= 3:
            return f"{detail} — consider qwen2.5:0.5b", "warn"
        else:
            return f"{detail} — insufficient for local LLM inference", "fail"
    except ImportError:
        return "psutil not installed — skipping", "warn"


def check_cpu():
    try:
        import psutil
        physical = psutil.cpu_count(logical=False)
        logical = psutil.cpu_count(logical=True)
        return f"{physical} physical cores, {logical} logical threads", "info"
    except ImportError:
        return "psutil not installed — skipping", "warn"


def check_disk():
    try:
        import psutil
        free_gb = psutil.disk_usage(".").free / 1e9
        detail = f"{free_gb:.1f} GB free on current drive"
        if free_gb >= 5:
            return detail, "pass"
        elif free_gb >= 2:
            return f"{detail} — may not fit all models", "warn"
        else:
            return f"{detail} — insufficient for model storage", "fail"
    except ImportError:
        return "psutil not installed — skipping", "warn"


def check_ollama_service():
    try:
        resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if resp.status_code == 200:
            return f"Ollama responding at {OLLAMA_HOST}", "pass", resp.json()
        else:
            return f"HTTP {resp.status_code} from Ollama", "fail", None
    except requests.ConnectionError:
        return (
            f"Cannot reach {OLLAMA_HOST} — Run: ollama serve",
            "fail",
            None,
        )
    except Exception as exc:
        return f"Error: {exc}", "fail", None


def check_port_11434():
    try:
        with socket.create_connection(("localhost", 11434), timeout=3):
            return "Port 11434 reachable", "pass"
    except OSError:
        return (
            "Port 11434 not accessible — debug with: netstat -ano | findstr :11434",
            "fail",
        )


def check_model_pulled(model_name: str, tags_data: dict | None):
    if tags_data is None:
        return f"Cannot check — Ollama unreachable", "fail"
    models = [m.get("name", "") for m in tags_data.get("models", [])]
    # Match on base name (strip tag if needed)
    matched = any(model_name in m for m in models)
    if matched:
        return f"{model_name} found locally", "pass"
    else:
        console.print(
            f"\n[yellow]  Model [bold]{model_name}[/bold] is not pulled.[/yellow]"
        )
        answer = console.input(
            f"  Pull [bold]{model_name}[/bold] now? ([bold green]y[/bold green]/[bold red]n[/bold red]): "
        ).strip().lower()
        if answer == "y":
            console.print(f"  [cyan]Pulling {model_name}…[/cyan]")
            result = subprocess.run(
                ["ollama", "pull", model_name],
                capture_output=False,
            )
            if result.returncode == 0:
                return f"{model_name} pulled successfully", "pass"
            else:
                return f"Pull failed for {model_name}", "fail"
        else:
            return f"{model_name} not found — skipped pull", "warn"


def check_packages():
    packages = {
        "requests": "requests",
        "rich": "rich",
        "pydantic": "pydantic",
        "schedule": "schedule",
        "python-dotenv": "dotenv",
    }
    results = {}
    for display_name, import_name in packages.items():
        try:
            importlib.import_module(import_name)
            results[display_name] = True
        except ImportError:
            results[display_name] = False

    all_ok = all(results.values())
    passed = [k for k, v in results.items() if v]
    failed = [k for k, v in results.items() if not v]

    detail_parts = []
    if passed:
        detail_parts.append(f"OK: {', '.join(passed)}")
    if failed:
        detail_parts.append(f"Missing: {', '.join(failed)}")

    detail = " | ".join(detail_parts)
    if not all_ok:
        return detail + "\n  → Run: pip install -r requirements.txt", "fail"
    return detail, "pass"


def check_smoke_test(tags_data: dict | None):
    if tags_data is None:
        return "Skipped — Ollama unreachable", "fail"

    models = [m.get("name", "") for m in tags_data.get("models", [])]
    model_to_use = None
    for candidate in ["qwen2.5:1.5b", "qwen2.5:0.5b", "llama3.2:1b"]:
        if any(candidate in m for m in models):
            model_to_use = candidate
            break
    if model_to_use is None and models:
        model_to_use = models[0]
    if model_to_use is None:
        return "No models available for smoke test", "fail"

    try:
        resp = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": model_to_use,
                "prompt": "Say OK",
                "num_predict": 3,
                "stream": False,
            },
            timeout=30,
        )
        if resp.status_code == 200:
            text = resp.json().get("response", "").strip()
            return f"Model '{model_to_use}' responded: '{text[:60]}'", "pass"
        else:
            return f"HTTP {resp.status_code} during smoke test", "fail"
    except requests.Timeout:
        return f"Smoke test timed out after 30s with model '{model_to_use}'", "fail"
    except Exception as exc:
        return f"Smoke test error: {exc}", "fail"


def status_cell(status: str) -> str:
    mapping = {
        "pass": STATUS_PASS,
        "warn": STATUS_WARN,
        "fail": STATUS_FAIL,
        "info": STATUS_INFO,
    }
    return mapping.get(status, STATUS_INFO)


def main():
    console.print(
        Panel.fit(
            "[bold #FACC15]AI to Agents Session Lab[/bold #FACC15]\n"
            "[white]Pre-flight Diagnostics — doctor.py[/white]",
            border_style="#FACC15",
        )
    )
    console.print()

    table = build_table()
    results = []  # list of (status_str)
    tags_data = None

    with Progress(
        SpinnerColumn(style="#FACC15"),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    ) as progress:

        # CHECK 1: Python Version
        task = progress.add_task("Checking Python version…", total=None)
        detail, status = check_python_version()
        table.add_row("1. Python Version", detail, status_cell(status))
        results.append(status)
        progress.remove_task(task)

        # CHECK 2: RAM
        task = progress.add_task("Checking available RAM…", total=None)
        detail, status = check_ram()
        table.add_row("2. Available RAM", detail, status_cell(status))
        results.append(status)
        progress.remove_task(task)

        # CHECK 3: CPU
        task = progress.add_task("Checking CPU core count…", total=None)
        detail, status = check_cpu()
        table.add_row("3. CPU Cores", detail, status_cell(status))
        results.append(status)
        progress.remove_task(task)

        # CHECK 4: Disk
        task = progress.add_task("Checking disk space…", total=None)
        detail, status = check_disk()
        table.add_row("4. Disk Space", detail, status_cell(status))
        results.append(status)
        progress.remove_task(task)

        # CHECK 5: Ollama service
        task = progress.add_task("Checking Ollama service…", total=None)
        detail, status, tags_data = check_ollama_service()
        table.add_row("5. Ollama Service Running", detail, status_cell(status))
        results.append(status)
        progress.remove_task(task)

        # CHECK 6: Port 11434
        task = progress.add_task("Checking port 11434…", total=None)
        detail, status = check_port_11434()
        table.add_row("6. Port 11434 Accessible", detail, status_cell(status))
        results.append(status)
        progress.remove_task(task)

    # CHECK 7 & 8: Models (interactive — outside progress so input works)
    console.print()
    detail, status = check_model_pulled("qwen2.5:1.5b", tags_data)
    table.add_row("7. Model qwen2.5:1.5b", detail, status_cell(status))
    results.append(status)

    detail, status = check_model_pulled("llama3.2:1b", tags_data)
    table.add_row("8. Model llama3.2:1b", detail, status_cell(status))
    results.append(status)

    with Progress(
        SpinnerColumn(style="#FACC15"),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    ) as progress:

        # CHECK 9: Python packages
        task = progress.add_task("Checking Python packages…", total=None)
        detail, status = check_packages()
        table.add_row("9. Python Packages", detail, status_cell(status))
        results.append(status)
        progress.remove_task(task)

        # CHECK 10: Smoke test
        task = progress.add_task("Running Ollama smoke test (up to 30s)…", total=None)
        detail, status = check_smoke_test(tags_data)
        table.add_row("10. Ollama API Smoke Test", detail, status_cell(status))
        results.append(status)
        progress.remove_task(task)

    console.print()
    console.print(table)
    console.print()

    # ── Summary ──────────────────────────────────────────────────────────────
    has_fail = "fail" in results
    has_warn = "warn" in results

    if has_fail:
        summary_text = "[bold red]❌ Fix the failures above before continuing.[/bold red]"
        summary_style = "red"
    elif has_warn:
        summary_text = "[bold yellow]⚠️  Some warnings — review above before proceeding.[/bold yellow]"
        summary_style = "yellow"
    else:
        summary_text = "[bold green]🚀 All checks passed! You're ready to start Lab 00.[/bold green]"
        summary_style = "green"

    console.print(Panel(summary_text, border_style=summary_style, expand=False))
    console.print()

    # ── RAM-based model recommendation ───────────────────────────────────────
    try:
        import psutil
        avail_gb = psutil.virtual_memory().available / 1e9
        if avail_gb < 4:
            rec = "Recommended: qwen2.5:0.5b   (OLLAMA_MODEL=qwen2.5:0.5b)"
            rec_style = "yellow"
        elif avail_gb <= 8:
            rec = "Recommended: qwen2.5:1.5b   (default)"
            rec_style = "cyan"
        else:
            rec = "Optional upgrade: qwen2.5:3b for better quality"
            rec_style = "green"
        console.print(
            Panel(
                f"[bold {rec_style}]💡 Model Recommendation[/bold {rec_style}]\n{rec}",
                border_style=rec_style,
                expand=False,
            )
        )
    except ImportError:
        pass

    # Exit with appropriate code
    sys.exit(1 if has_fail else 0)


if __name__ == "__main__":
    main()
