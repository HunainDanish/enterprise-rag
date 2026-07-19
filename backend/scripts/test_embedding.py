import time

from app.rag.embeddings import encode_texts

texts = [
    "Artificial intelligence is transforming software engineering."
] * 50

start = time.perf_counter()

embeddings = encode_texts(texts)

elapsed = time.perf_counter() - start

print(f"Generated {len(embeddings)} embeddings")
print(f"Embedding dimension: {len(embeddings[0])}")
print(f"Elapsed time: {elapsed:.3f} seconds")