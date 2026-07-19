from sentence_transformers import SentenceTransformer

from app.core.config import settings

print("Loading SentenceTransformer model...")
_model = SentenceTransformer(settings.EMBEDDING_MODEL)
try:
    EMBEDDING_DIMENSION = _model.get_embedding_dimension()
except AttributeError:
    EMBEDDING_DIMENSION = _model.get_sentence_embedding_dimension()


def encode_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    return _model.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
    ).tolist()
