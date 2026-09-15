"""memory — Başak hafıza motoru (P2).

SQLite + sqlite-vec (anlam araması) + FTS5/BM25 (anahtar kelime) ile
hibrit arama yapar. Embedding'ler Gemini'den gelir; yoksa BM25-only.
"""

from memory.engine import HafizaMotoru

__all__ = ["HafizaMotoru"]
