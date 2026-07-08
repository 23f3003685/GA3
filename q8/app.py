import os
import numpy as np
import requests

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


AIPIPE_TOKEN = os.getenv("AIPIPE_TOKEN")

EMBEDDING_URL = "https://aipipe.org/openai/v1/embeddings"


class RankRequest(BaseModel):
    query_id: str
    query: str
    candidates: list[str]


def get_embeddings(texts):

    response = requests.post(
        EMBEDDING_URL,
        headers={
            "Authorization": f"Bearer {AIPIPE_TOKEN}",
            "Content-Type": "application/json",
        },
        json={
            "model": "text-embedding-3-small",
            "input": texts,
        },
        timeout=120,
    )

    response.raise_for_status()

    data = response.json()["data"]

    embeddings = [
        np.array(item["embedding"], dtype=float)
        for item in data
    ]

    return embeddings


@app.post("/rank")
def rank(req: RankRequest):

    texts = [req.query] + req.candidates

    embeddings = get_embeddings(texts)

    query_embedding = embeddings[0]

    candidate_embeddings = embeddings[1:]

    similarities = []

    query_norm = np.linalg.norm(query_embedding)

    for i, emb in enumerate(candidate_embeddings):

        score = np.dot(query_embedding, emb) / (
            query_norm * np.linalg.norm(emb)
        )

        similarities.append((i, score))

    similarities.sort(
        key=lambda x: x[1],
        reverse=True
    )

    top3 = [idx for idx, _ in similarities[:3]]

    return {
        "ranking": top3
    }