"""
Embedder - Generates embeddings using all-MiniLM-L6-v2

Uses sentence-transformers for local, fast embedding generation.
The model is downloaded on first use (~80MB).
"""

import os
from typing import List, Optional
import numpy as np

# Lazy load to avoid import overhead
_model = None


def get_model():
    """Lazy load the embedding model."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer

            # Suppress logging during model load
            import logging
            logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

            _model = SentenceTransformer("all-MiniLM-L6-v2")
            print("[Housekeeper] Loaded embedding model: all-MiniLM-L6-v2")
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers"
            )
    return _model


def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Generate embedding for a piece of code or text.

    Args:
        text: The code/text to embed

    Returns:
        List of floats representing the embedding vector (384 dimensions)
    """
    if not text or not text.strip():
        return None

    try:
        model = get_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    except Exception as e:
        print(f"[Housekeeper] Embedding error: {e}")
        return None


def generate_embeddings_batch(texts: List[str]) -> List[Optional[List[float]]]:
    """
    Generate embeddings for multiple texts efficiently.

    Args:
        texts: List of code/text to embed

    Returns:
        List of embedding vectors
    """
    if not texts:
        return []

    try:
        model = get_model()

        # Filter out empty texts but track indices
        valid_indices = []
        valid_texts = []
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_indices.append(i)
                valid_texts.append(text)

        if not valid_texts:
            return [None] * len(texts)

        # Batch encode
        embeddings = model.encode(valid_texts, convert_to_numpy=True, show_progress_bar=False)

        # Rebuild list with None for invalid texts
        result = [None] * len(texts)
        for idx, embedding in zip(valid_indices, embeddings):
            result[idx] = embedding.tolist()

        return result

    except Exception as e:
        print(f"[Housekeeper] Batch embedding error: {e}")
        return [None] * len(texts)


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two embedding vectors.

    Args:
        vec1: First embedding vector
        vec2: Second embedding vector

    Returns:
        Similarity score between 0 and 1
    """
    if vec1 is None or vec2 is None:
        return 0.0

    a = np.array(vec1)
    b = np.array(vec2)

    # Cosine similarity
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(dot_product / (norm_a * norm_b))


def preload_model():
    """
    Preload the model to avoid latency on first use.
    Call this during startup/index rebuild.
    """
    try:
        get_model()
        return True
    except Exception as e:
        print(f"[Housekeeper] Failed to preload model: {e}")
        return False
