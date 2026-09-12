"""
src/pipeline/embedder.py — Gemini embedding wrapper with batching and retry.
"""
import time
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from google import genai
from config import EMBEDDING_MODEL, EMBED_BATCH_DELAY


class Embedder:
    """
    Wraps the Gemini gemini-embedding-001 model.
    Supports single-text and batch embedding with rate-limit protection.
    """

    def __init__(self, client: genai.Client):
        self.client = client
        self.model = EMBEDDING_MODEL
        self._cache: dict[str, list[float]] = {}

    def embed(self, text: str, use_cache: bool = True) -> list[float]:
        """Embed a single piece of text. Caches by text hash."""
        if use_cache and text in self._cache:
            return self._cache[text]

        response = self.client.models.embed_content(
            model=self.model,
            contents=text,
        )
        embedding = response.embeddings[0].values
        if use_cache:
            self._cache[text] = embedding
        return embedding

    def embed_batch(
        self,
        texts: list[str],
        delay: float = EMBED_BATCH_DELAY,
        verbose: bool = False,
    ) -> list[list[float]]:
        """
        Embed a list of texts with a small delay between calls to avoid
        rate-limiting. Skips already-cached texts.
        """
        embeddings: list[list[float]] = []
        total = len(texts)
        for i, text in enumerate(texts):
            if verbose and (i % 10 == 0 or i == total - 1):
                print(f"  Embedding {i + 1}/{total}...", end="\r")
            emb = self.embed(text)
            embeddings.append(emb)
            if delay > 0:
                time.sleep(delay)
        if verbose:
            print()
        return embeddings

