from typing import Any, List, Optional
import numpy as np
from backend.config.settings import settings
from backend.utils.logging import logger


class EmbeddingGenerator:
    """Generates 768-dim dense vector embeddings via Google Vertex AI (text-embedding-004).

    Falls back to a deterministic pseudo-vector if Vertex AI is unavailable.
    """

    def __init__(self) -> None:
        self._vertex_model: Optional[Any] = None
        self._vertex_init_failed: bool = False

    # ── Vertex AI ───────────────────────────────────────────────────────
    def _get_vertex_model(self) -> Optional[Any]:
        if self._vertex_init_failed:
            return None
        if self._vertex_model is None:
            try:
                import vertexai
                from vertexai.language_models import TextEmbeddingModel

                vertexai.init(project=settings.GCP_PROJECT_ID, location=settings.GCP_LOCATION)
                self._vertex_model = TextEmbeddingModel.from_pretrained(settings.VERTEX_EMBEDDING_MODEL)
                logger.info(
                    "Vertex AI embedding model loaded",
                    model=settings.VERTEX_EMBEDDING_MODEL,
                    dim=768,
                )
            except Exception as exc:
                logger.warning(
                    "Vertex AI embedding model unavailable — using deterministic fallback",
                    error=str(exc),
                )
                self._vertex_init_failed = True
                return None
        return self._vertex_model

    def _vertex_embed(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Attempt a Vertex AI batch embed.  Returns None on failure."""
        model = self._get_vertex_model()
        if model is None:
            return None
        try:
            embeddings = model.get_embeddings(texts)
            return [e.values for e in embeddings]
        except Exception as exc:
            logger.warning("Vertex AI embedding call failed", error=str(exc))
            return None

    # ── Deterministic fallback ──────────────────────────────────────────
    @staticmethod
    def _deterministic_vector(text: str, dim: int = 768) -> List[float]:
        seed = abs(hash(text)) % (2**32)
        rng = np.random.RandomState(seed)
        vec = rng.normal(0, 0.1, dim)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    # ── Public API ──────────────────────────────────────────────────────
    def generate_embedding(self, text: str) -> List[float]:
        """Generates a 768-dim embedding vector for a string."""
        if not text or not text.strip():
            return [0.0] * 768

        # 1. Vertex AI (768-dim)
        vertex_result = self._vertex_embed([text])
        if vertex_result is not None:
            return vertex_result[0]

        # 2. Deterministic fallback (768-dim)
        return self._deterministic_vector(text, 768)

    def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generates 768-dim embedding vectors for a list of strings."""
        if not texts:
            return []

        # 1. Vertex AI
        vertex_result = self._vertex_embed(texts)
        if vertex_result is not None:
            return vertex_result

        # 2. Per-item deterministic fallback
        return [self.generate_embedding(t) for t in texts]


embedding_generator = EmbeddingGenerator()
