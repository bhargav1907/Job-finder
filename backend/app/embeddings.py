"""Local embeddings via fastembed. No network, no per-call cost."""

from functools import lru_cache

import numpy as np

from .config import get_settings


@lru_cache(maxsize=2)
def _model(model_name: str):
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=model_name)


def embed_texts(texts: list[str], model_name: str | None = None) -> np.ndarray:
    """Returns a float32 array of shape (len(texts), dim), L2-normalized."""
    if not texts:
        return np.zeros((0, 0), dtype=np.float32)

    model = _model(model_name or get_settings().embedding_model)
    vectors = np.vstack([np.asarray(vec, dtype=np.float32) for vec in model.embed(texts)])
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


def to_bytes(vector: np.ndarray) -> bytes:
    return np.asarray(vector, dtype=np.float32).tobytes()


def from_bytes(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)
