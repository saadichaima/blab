# core/embeddings.py

import os
import numpy as np
import faiss
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")


def embed_texts(texts):
    """Convertit une liste de textes en vecteurs d'embedding"""
    response = client.embeddings.create(input=texts, model=EMBEDDING_DEPLOYMENT)
    return [np.array(e.embedding, dtype=np.float32) for e in response.data]


def build_faiss_index(chunks):
    """Construit un index FAISS à partir des chunks de texte"""
    vectors = embed_texts(chunks)
    dim = len(vectors[0])
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(vectors))
    return index, vectors
