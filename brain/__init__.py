"""brain — Başak'ın beyin modülü.

9 bulut saglayici + Ollama (yerel) destekli.
Sirayla: Groq, GLM, Cloudflare, Cohere, NVIDIA, OpenRouter,
QwenCloud, Gemini → Ollama.
"""

from brain.brain import Brain

__all__ = ["Brain"]
