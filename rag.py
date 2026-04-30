import faiss
import numpy as np
import httpx
import os

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")


def split(text, size=400):
    words = text.split()
    return [" ".join(words[i:i+size]) for i in range(0, len(words), size)]


async def embed(text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={GEMINI_API_KEY}"

    payload = {"content": {"parts": [{"text": text}]}}

    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload)

    return np.array(r.json()["embedding"]["values"], dtype="float32")


def build_faiss(vectors):
    dim = len(vectors[0])
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(vectors))
    return index
