import os

import chromadb
import pandas as pd
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

csv_path = "qa_dataset.csv"
if not os.path.exists(csv_path):
    raise FileNotFoundError(f"File {csv_path} not found.")

df = pd.read_csv(csv_path)
if 'question' not in df.columns or 'answer' not in df.columns:
    raise ValueError("CSV must contain 'question' and 'answer' columns.")

questions = df['question'].astype(str).tolist()
answers = df['answer'].astype(str).tolist()

embedder = SentenceTransformer('ai-forever/sbert_large_nlu_ru')
embeddings = embedder.encode(questions)

settings = Settings(
    anonymized_telemetry=False
)

client = chromadb.PersistentClient(path="./chroma_data", settings=settings)
collection = client.get_or_create_collection(name="qa_dataset")

try:
    client.delete_collection("qa_dataset")
except Exception:
    pass

collection = client.get_or_create_collection(
    name="qa_dataset",
    metadata={"hnsw:space": "cosine"}
)

metadatas = [{"answer": ans} for ans in answers]
ids = [str(i) for i in range(len(questions))]

collection.add(
    documents=questions,
    embeddings=embeddings.tolist(),
    metadatas=metadatas,
    ids=ids
)
