import logging
import os

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

os.environ["CHROMA_TELEMETRY_ENABLED"] = "false"

settings = Settings(
    anonymized_telemetry=False
)

client = chromadb.PersistentClient(path="./chroma_data", settings=settings)

embedder = SentenceTransformer('ai-forever/sbert_large_nlu_ru')

collection = client.get_or_create_collection(
    name="qa_dataset",
    metadata={"hnsw:space": "cosine"}
)

threshold_exact = 0.2


def generate_answer(user_question, top_k=3, similarity_threshold=0.5):
    logging.info("Started generating answer")
    query_embedding = embedder.encode([user_question])[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )

    if not results["distances"][0]:
        return "No similar answer found in the knowledge base."

    best_distance = results["distances"][0][0]
    best_answer = results["metadatas"][0][0]["answer"]

    if best_distance < threshold_exact:
        return best_answer
    else:
        answers = [
            meta["answer"]
            for meta, distance in zip(results["metadatas"][0], results["distances"][0])
            if distance < similarity_threshold
        ]

        if not answers:
            return "No similar answer found in the knowledge base."

        return f"(Semantically similar question)\n{answers[0]}"
