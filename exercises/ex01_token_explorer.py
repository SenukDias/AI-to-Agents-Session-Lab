"""
Lab 01 Exercise: Token Explorer
Explore how Ollama tokenizes text, generates embeddings, and assigns probabilities.

Author: Senuk Manditha Dias
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")


def get_embeddings(text: str) -> list[float]:
    """Call Ollama /api/embed and return the embedding vector."""
    # TODO 1: Make a POST request to f"{OLLAMA_HOST}/api/embed"
    # HINT: payload = {"model": MODEL, "input": text}
    # HINT: response.json() returns {"embeddings": [[...float values...]]}
    raise NotImplementedError("Complete TODO 1")


def get_logprobs(prompt: str, num_predict: int = 5) -> dict:
    """Get token-level log probabilities for the first predicted token."""
    # TODO 2: Make a POST request to f"{OLLAMA_HOST}/api/generate"
    # HINT: payload needs "model", "prompt", "logprobs": True, "num_predict": num_predict, "stream": False
    # HINT: response.json() may include a "logprobs" key — explore what comes back
    raise NotImplementedError("Complete TODO 2")


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    # TODO 3: Implement cosine similarity WITHOUT using numpy
    # HINT: dot_product = sum(a*b for a,b in zip(vec_a, vec_b))
    # HINT: norm_a = sum(x**2 for x in vec_a) ** 0.5
    raise NotImplementedError("Complete TODO 3")


def display_embedding_info(text: str, embedding: list[float]) -> None:
    """Display embedding info in a Rich table."""
    # TODO 4: Use rich.table.Table to display:
    #   - Dimension count (len(embedding))
    #   - L2 norm of the embedding
    #   - First 5 values preview
    # HINT: from rich.console import Console; from rich.table import Table
    # HINT: Console().print(table) renders the table
    raise NotImplementedError("Complete TODO 4")


if __name__ == "__main__":
    # Test phrases for embedding comparison
    phrases = [
        "cybersecurity vulnerability scan",
        "security audit log review",
        "pizza recipe with extra cheese",
    ]

    print(f"Connecting to Ollama at {OLLAMA_HOST} using model {MODEL}\n")

    # Step 1: Get embeddings
    # TODO 5: Call get_embeddings() for each phrase and store results
    # TODO 6: Compute cosine similarity between phrase[0] and phrase[1], and phrase[0] and phrase[2]
    # TODO 7: Display results showing which phrases are semantically similar

    # Step 2: Get logprobs
    prompt = "The capital of France is"
    # TODO 8: Call get_logprobs(prompt) and display the top token predictions
    print("Done! Compare your results with solutions/sol01_token_explorer.py")
