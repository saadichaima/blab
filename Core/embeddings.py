import os
import numpy as np
from dotenv import load_dotenv
from openai import AzureOpenAI
from sklearn.neighbors import NearestNeighbors

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


def build_index(chunks):
    """Construit un index avec sklearn (remplaçant de FAISS)"""
    vectors = embed_texts(chunks)
    dim = len(vectors[0])
    index = NearestNeighbors(n_neighbors=5, metric="euclidean")
    index.fit(vectors)
    return index, vectors
