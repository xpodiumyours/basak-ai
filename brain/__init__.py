"""brain — Başak'ın beyin modülü.

Groq (bulut) + Ollama (yerel) destekli.
Tool calling: Groq kullanır (qwen2.5:3b tool calling'i iyi yapamaz).
"""

from brain.brain import Brain

__all__ = ["Brain"]
