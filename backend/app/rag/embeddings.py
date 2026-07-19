from sentence_transformers import SentenceTransformer

from app.core.config import settings

print("Loading SentenceTransformer model...")
_model = SentenceTransformer(settings.EMBEDDING_MODEL)


def encode_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    return _model.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
    ).tolist()
