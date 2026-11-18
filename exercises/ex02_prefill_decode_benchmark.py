"""
Lab 02 Exercise: Prefill vs. Decode Benchmark
Measure Time-to-First-Token (TTFT), tokens-per-second, and KV Cache warm-up effects.

Author: Senuk Manditha Dias
"""
import os
import time
import json
import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
FAST_MODEL = os.getenv("OLLAMA_FAST_MODEL", "llama3.2:1b")


def run_inference(model: str, prompt: str, options: dict = None) -> dict:
    """Run inference and return timing metadata from Ollama."""
    # TODO 1: POST to f"{OLLAMA_HOST}/api/generate" with stream=False
    # HINT: Include "options" key for temperature, top_k, top_p, num_ctx
    # HINT: Response contains: response, prompt_eval_duration, eval_duration, eval_count
    # HINT: Durations are in nanoseconds — divide by 1e9 for seconds
    raise NotImplementedError("Complete TODO 1")


def benchmark_cold_vs_warm(prompt: str) -> None:
    """Compare cold cache (first run) vs warm cache (second run) TTFT."""
    print("=== Cold Cache vs Warm Cache Benchmark ===\n")

    # TODO 2: Run inference TWICE with the same prompt
    # TODO 3: Extract prompt_eval_duration from both responses
    # TODO 4: Calculate speedup ratio: cold_ttft / warm_ttft
    # TODO 5: Display results using Rich table with columns: Run, TTFT (s), Speedup
    # HINT: First run = cold cache (Ollama must load weights + build KV cache)
    # HINT: Second run = warm cache (KV cache reused if prompt unchanged)
    raise NotImplementedError("Complete TODO 2-5")


def temperature_sweep(prompt: str) -> None:
    """Compare outputs at different temperatures."""
    temperatures = [0.0, 0.5, 1.0]

    # TODO 6: For each temperature, run inference with num_predict=50
    # TODO 7: Display side-by-side: temperature value, first 100 chars of response, eval tokens/sec
    # HINT: tokens_per_sec = eval_count / (eval_duration / 1e9)
    raise NotImplementedError("Complete TODO 6-7")


if __name__ == "__main__":
    test_prompt = "Explain what a firewall does in exactly 3 sentences."

    # Run benchmarks
    benchmark_cold_vs_warm(test_prompt)
    print("\n")
    temperature_sweep(test_prompt)
    print("\nDone! Compare with solutions/sol02_prefill_decode_benchmark.py")
