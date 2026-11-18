"""
sol02_prefill_decode_benchmark.py
Prefill vs Decode benchmarking — KV cache, temperature sweep, model comparison.

Author: Senuk Manditha Dias
"""

import os
import time

import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
FAST_MODEL = os.getenv("OLLAMA_FAST_MODEL", "llama3.2:1b")

console = Console()


# ---------------------------------------------------------------------------
# Core inference function
# ---------------------------------------------------------------------------

def run_inference(model: str, prompt: str, options: dict | None = None) -> dict:
    """
    POST /api/generate with stream=False.
    Returns the full Ollama response dict including timing fields.
    """
    url = f"{OLLAMA_HOST}/api/generate"
    payload: dict = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    if options:
        payload["options"] = options

    try:
        resp = requests.post(url, json=payload, timeout=300)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        console.print(f"[red]Inference error ({model}):[/red] {exc}")
        raise


def _extract_metrics(resp: dict) -> tuple[float, float, int, float]:
    """
    Returns (ttft_s, decode_s, token_count, tokens_per_sec).
    Ollama timing fields are in nanoseconds.
    """
    prompt_eval_ns: int = resp.get("prompt_eval_duration", 0)
    eval_ns: int = resp.get("eval_duration", 0)
    eval_count: int = resp.get("eval_count", 0)

    ttft_s = prompt_eval_ns / 1e9 if prompt_eval_ns else 0.0
    decode_s = eval_ns / 1e9 if eval_ns else 0.0
    tokens_per_sec = eval_count / decode_s if decode_s > 0 else 0.0
    return ttft_s, decode_s, eval_count, tokens_per_sec


# ---------------------------------------------------------------------------
# Benchmark functions
# ---------------------------------------------------------------------------

def benchmark_cold_vs_warm(prompt: str, model: str = MODEL) -> None:
    """
    Run the same prompt twice — first (cold) and second (warm, KV cached).
    Display a Rich table comparing metrics and explain the speedup.
    """
    console.rule("[yellow]Cold vs Warm KV Cache Benchmark[/yellow]")
    console.print(f"[dim]Model:[/dim] [yellow]{model}[/yellow]")
    console.print(f"[dim]Prompt:[/dim] {prompt[:80]}")

    results = []
    for i, label in enumerate(["Cold (1st run)", "Warm (2nd run)"]):
        console.print(f"\n[dim]Running {label}…[/dim]")
        try:
            resp = run_inference(model, prompt, options={"num_predict": 60})
            ttft, decode, tokens, tps = _extract_metrics(resp)
            results.append((label, ttft, decode, tokens, tps))
        except Exception as exc:
            console.print(f"[red]Run {i+1} failed: {exc}[/red]")
            return

    table = Table(
        title="[bold yellow]Cold vs Warm Inference[/bold yellow]",
        style="on grey7",
        header_style="bold yellow",
        show_lines=True,
    )
    for col in ("Run", "TTFT (s)", "Decode (s)", "Tokens/s", "Total tokens"):
        table.add_column(col, style="white", justify="right" if col != "Run" else "left")

    for label, ttft, decode, tokens, tps in results:
        table.add_row(label, f"{ttft:.3f}", f"{decode:.3f}", f"{tps:.1f}", str(tokens))

    console.print(table)

    # Speedup ratio (TTFT comparison)
    if len(results) == 2 and results[0][1] > 0 and results[1][1] > 0:
        speedup = results[0][1] / results[1][1]
        console.print(
            Panel(
                f"[bold yellow]KV Cache Speedup:[/bold yellow] "
                f"[white]{speedup:.2f}×[/white] faster TTFT on second run.\n\n"
                "[dim]The first run (cold) must load and process all prompt tokens from scratch. "
                "The second run (warm) reuses the KV cache, so the prefill stage is dramatically "
                "shorter — only new tokens need attention computation.[/dim]",
                style="on grey7",
                border_style="yellow",
            )
        )


def temperature_sweep(
    prompt: str,
    temps: list[float] | None = None,
    model: str = MODEL,
) -> None:
    """
    Run inference at several temperatures with num_predict=50.
    Display a Rich table: Temp | First 80 chars of response | Tokens/s
    """
    if temps is None:
        temps = [0.0, 0.5, 1.0]

    console.rule("[yellow]Temperature Sweep[/yellow]")
    console.print(f"[dim]Model:[/dim] [yellow]{model}[/yellow]")
    console.print(f"[dim]Prompt:[/dim] {prompt[:80]}")

    table = Table(
        title="[bold yellow]Temperature Sweep[/bold yellow]",
        style="on grey7",
        header_style="bold yellow",
        show_lines=True,
    )
    table.add_column("Temp", style="yellow", justify="center")
    table.add_column("Response (first 80 chars)", style="white")
    table.add_column("Tokens/s", style="cyan", justify="right")

    for temp in temps:
        console.print(f"[dim]Running temperature={temp}…[/dim]")
        try:
            resp = run_inference(
                model,
                prompt,
                options={"temperature": temp, "num_predict": 50},
            )
            _, _, _, tps = _extract_metrics(resp)
            snippet = resp.get("response", "")[:80].replace("\n", " ")
            table.add_row(str(temp), snippet, f"{tps:.1f}")
        except Exception as exc:
            table.add_row(str(temp), f"[red]Error: {exc}[/red]", "-")

    console.print(table)


def model_speed_comparison(prompt: str) -> None:
    """
    Compare FAST_MODEL (llama3.2:1b) vs MODEL (qwen2.5:1.5b) speed.
    """
    console.rule("[yellow]Model Speed Comparison[/yellow]")

    table = Table(
        title="[bold yellow]Model Speed Comparison[/bold yellow]",
        style="on grey7",
        header_style="bold yellow",
        show_lines=True,
    )
    table.add_column("Model", style="yellow")
    table.add_column("TTFT (s)", style="white", justify="right")
    table.add_column("Decode (s)", style="white", justify="right")
    table.add_column("Tokens/s", style="cyan", justify="right")
    table.add_column("Total tokens", style="white", justify="right")

    for model in (FAST_MODEL, MODEL):
        console.print(f"[dim]Running {model}…[/dim]")
        try:
            resp = run_inference(model, prompt, options={"num_predict": 60})
            ttft, decode, tokens, tps = _extract_metrics(resp)
            table.add_row(model, f"{ttft:.3f}", f"{decode:.3f}", f"{tps:.1f}", str(tokens))
        except Exception as exc:
            table.add_row(model, "-", "-", "-", f"[red]{exc}[/red]")

    console.print(table)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    console.print(
        Panel(
            Text("⚡  Prefill & Decode Benchmark", style="bold yellow", justify="center"),
            subtitle="[dim]Cold/Warm KV Cache · Temperature Sweep · Model Comparison[/dim]",
            style="on grey7",
            border_style="yellow",
        )
    )

    bench_prompt = (
        "Explain three key differences between symmetric and asymmetric encryption "
        "in the context of enterprise network security."
    )

    # 1. Cold vs warm
    benchmark_cold_vs_warm(bench_prompt)

    # 2. Temperature sweep
    temperature_sweep(
        "Describe a common SQL injection vulnerability in one sentence:",
        temps=[0.0, 0.5, 1.0],
    )

    # 3. Model comparison
    model_speed_comparison(bench_prompt)

    console.print(
        Panel(
            "[bold green]✓ Benchmark complete.[/bold green]",
            style="on grey7",
            border_style="green",
        )
    )


if __name__ == "__main__":
    main()
