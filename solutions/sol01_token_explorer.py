"""
sol01_token_explorer.py
Token Explorer — embeddings, cosine similarity, and logprobs with Ollama.

Author: Senuk Manditha Dias
"""

import os
import math
import time
import json

import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")

console = Console()


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def get_embeddings(text: str) -> list[float]:
    """POST /api/embed and return the embedding vector as a list of floats."""
    url = f"{OLLAMA_HOST}/api/embed"
    payload = {"model": MODEL, "input": text}
    try:
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        # Ollama returns {"embeddings": [[...float...]]}
        embeddings = data.get("embeddings") or data.get("embedding")
        if embeddings is None:
            raise ValueError(f"Unexpected response structure: {data}")
        # embeddings may be a list-of-lists (batch) or a flat list
        if isinstance(embeddings[0], list):
            return embeddings[0]
        return embeddings
    except requests.RequestException as exc:
        console.print(f"[red]Error fetching embeddings:[/red] {exc}")
        raise


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Pure-Python cosine similarity between two vectors."""
    if len(vec_a) != len(vec_b):
        raise ValueError(
            f"Vector length mismatch: {len(vec_a)} vs {len(vec_b)}"
        )
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a * a for a in vec_a))
    mag_b = math.sqrt(sum(b * b for b in vec_b))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


def get_logprobs(prompt: str) -> dict:
    """
    POST /api/generate with logprobs=True (if supported) and num_predict=5.
    Returns the full response dict so callers can inspect whatever Ollama
    includes — logprobs support varies by model and Ollama version.
    """
    url = f"{OLLAMA_HOST}/api/generate"
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": 5,
            "logprobs": True,
        },
    }
    try:
        t0 = time.perf_counter()
        resp = requests.post(url, json=payload, timeout=120)
        ttft = time.perf_counter() - t0
        resp.raise_for_status()
        data = resp.json()
        data["_ttft_seconds"] = ttft
        return data
    except requests.RequestException as exc:
        console.print(f"[red]Error fetching logprobs:[/red] {exc}")
        raise


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def display_embedding_info(text: str, embedding: list[float]) -> None:
    """Rich Table showing dimension, L2 norm, and first 5 values."""
    dim = len(embedding)
    l2_norm = math.sqrt(sum(v * v for v in embedding))
    first5 = [f"{v:.6f}" for v in embedding[:5]]

    table = Table(
        title=f'[bold yellow]Embedding Info — "{text[:50]}"[/bold yellow]',
        style="on grey7",
        header_style="bold yellow",
        show_lines=True,
    )
    table.add_column("Property", style="yellow")
    table.add_column("Value", style="white")

    table.add_row("Dimension", str(dim))
    table.add_row("L2 Norm", f"{l2_norm:.6f}")
    table.add_row("First 5 Values", ", ".join(first5))

    console.print(table)


def display_similarity_table(
    phrases: list[str],
    sim_01: float,
    sim_02: float,
) -> None:
    """Display cosine similarity results in a Rich table."""
    table = Table(
        title="[bold yellow]Cosine Similarity Results[/bold yellow]",
        style="on grey7",
        header_style="bold yellow",
        show_lines=True,
    )
    table.add_column("Pair", style="yellow", no_wrap=False)
    table.add_column("Cosine Similarity", style="white", justify="right")
    table.add_column("Interpretation", style="cyan")

    def interpret(score: float) -> str:
        if score >= 0.90:
            return "Very similar (same domain)"
        if score >= 0.75:
            return "Related topics"
        if score >= 0.50:
            return "Loosely related"
        return "Very different topics"

    table.add_row(
        f'"{phrases[0][:35]}…"\nvs\n"{phrases[1][:35]}…"',
        f"{sim_01:.4f}",
        interpret(sim_01),
    )
    table.add_row(
        f'"{phrases[0][:35]}…"\nvs\n"{phrases[2][:35]}…"',
        f"{sim_02:.4f}",
        interpret(sim_02),
    )

    console.print(table)


def display_logprob_info(response: dict) -> None:
    """Show TTFT and whatever logprob data Ollama returned."""
    ttft = response.get("_ttft_seconds", 0.0)
    generated = response.get("response", "")
    logprobs = response.get("logprobs") or response.get("log_probs")

    table = Table(
        title="[bold yellow]Generate Response Info[/bold yellow]",
        style="on grey7",
        header_style="bold yellow",
        show_lines=True,
    )
    table.add_column("Field", style="yellow")
    table.add_column("Value", style="white")

    table.add_row("TTFT (Time to First Token)", f"{ttft:.4f} s")
    table.add_row("Generated Text (first 120 chars)", generated[:120])
    table.add_row(
        "Logprobs Available",
        "Yes" if logprobs else "No (model/version may not support it)",
    )

    if logprobs:
        # Pretty-print first token's logprob data if present
        if isinstance(logprobs, list) and logprobs:
            table.add_row("First Token Logprob", str(logprobs[0]))
        else:
            table.add_row("Logprob Data", str(logprobs)[:200])

    # Timing from Ollama response fields
    prompt_eval_ns = response.get("prompt_eval_duration", 0)
    eval_ns = response.get("eval_duration", 0)
    if prompt_eval_ns:
        table.add_row("Prompt Eval Duration", f"{prompt_eval_ns / 1e9:.4f} s")
    if eval_ns:
        table.add_row("Decode Duration", f"{eval_ns / 1e9:.4f} s")

    console.print(table)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    console.print(
        Panel(
            Text("🔍  Token Explorer", style="bold yellow", justify="center"),
            subtitle="[dim]Embeddings · Cosine Similarity · Logprobs[/dim]",
            style="on grey7",
            border_style="yellow",
        )
    )

    phrases = [
        "cybersecurity vulnerability scan",
        "security audit log review",
        "pizza recipe with extra cheese",
    ]

    # --- Embeddings ---
    console.rule("[yellow]Step 1: Generating Embeddings[/yellow]")
    embeddings: list[list[float]] = []
    for phrase in phrases:
        console.print(f"[dim]Embedding:[/dim] [yellow]{phrase}[/yellow]")
        try:
            emb = get_embeddings(phrase)
            embeddings.append(emb)
            display_embedding_info(phrase, emb)
        except Exception as exc:
            console.print(f"[red]Failed for phrase '{phrase}': {exc}[/red]")
            return

    # --- Cosine Similarity ---
    console.rule("[yellow]Step 2: Cosine Similarity[/yellow]")
    try:
        sim_01 = cosine_similarity(embeddings[0], embeddings[1])
        sim_02 = cosine_similarity(embeddings[0], embeddings[2])
        display_similarity_table(phrases, sim_01, sim_02)
    except Exception as exc:
        console.print(f"[red]Similarity computation failed: {exc}[/red]")
        return

    # --- Logprobs / TTFT ---
    console.rule("[yellow]Step 3: Logprobs & TTFT[/yellow]")
    test_prompt = "List one common cybersecurity best practice:"
    console.print(f"[dim]Prompt:[/dim] [yellow]{test_prompt}[/yellow]")
    try:
        logprob_resp = get_logprobs(test_prompt)
        display_logprob_info(logprob_resp)
    except Exception as exc:
        console.print(f"[red]Logprob request failed: {exc}[/red]")

    console.print(
        Panel(
            "[bold green]✓ Token Explorer complete.[/bold green]",
            style="on grey7",
            border_style="green",
        )
    )


if __name__ == "__main__":
    main()
