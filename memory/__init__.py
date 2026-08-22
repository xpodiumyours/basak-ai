"""memory — Başak hafıza motoru (P2).

SQLite + sqlite-vec (anlam araması) + FTS5/BM25 (anahtar kelime) ile
hibrit arama yapar. Embedding'ler yerel Ollama nomic-embed-text'ten gelir.
"""

from memory.engine import HafizaMotoru

__all__ = ["HafizaMotoru"]
