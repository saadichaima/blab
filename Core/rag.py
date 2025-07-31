# core/rag.py

import os
import numpy as np
from dotenv import load_dotenv
from openai import AzureOpenAI
from Core.embeddings import embed_texts
import requests

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

GPT_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")

# ─────────────────────────────
# ⛽ Base d'appel OpenAI
# ─────────────────────────────
def call_ai(prompt):
    response = client.chat.completions.create(
        model=GPT_DEPLOYMENT,
        messages=[
            {"role": "system", "content": "Tu es un expert du Crédit d'Impôt Recherche."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4,
        max_tokens=1500
    )
    return response.choices[0].message.content
def fetch_prompt_from_git(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text.strip()
    except Exception as e:
        return f"❌ Erreur lors du chargement du prompt : {e}"

# ─────────────────────────────
# 🔍 Recherche sémantique
# ─────────────────────────────
def search_similar_chunks(query, index, chunks, vectors, top_k=3):
    q_vec = embed_texts([query])[0]
    q_vec_np = np.array([q_vec], dtype=np.float32).reshape(1, -1)
    
    # ⚠️ Ajuster top_k si nécessaire
    actual_k = min(top_k, len(chunks))
    
    distances, indices = index.kneighbors(q_vec_np, n_neighbors=actual_k)
    return [chunks[i] for i in indices[0]]



# ─────────────────────────────
# 🎯 Générateur générique
# ─────────────────────────────
def generate_section_with_rag(titre, prompt_instruction, index, chunks, vectors):
    context = "\n".join(search_similar_chunks(prompt_instruction, index, chunks, vectors))
    full_prompt = f"""Tu dois rédiger la section suivante : "{titre}".

Voici le contexte extrait des documents client :
\"\"\"
{context}
\"\"\"

Consignes spécifiques :
{prompt_instruction}

Structure la section de manière claire, technique, et adaptée à un dossier CIR.
"""
    return call_ai(full_prompt)

# ─────────────────────────────
# ✍️ Prompts spécifiques
# ─────────────────────────────
def prompt_contribution():
    return fetch_prompt_from_git("https://raw.githubusercontent.com/saadichaima/prompt/refs/heads/main/contribution.txt")

def prompt_contexte():
    return fetch_prompt_from_git("https://raw.githubusercontent.com/saadichaima/prompt/refs/heads/main/prompt_contexte.txt")

def prompt_indicateurs():
    return fetch_prompt_from_git("https://raw.githubusercontent.com/saadichaima/prompt/refs/heads/main/indicateurs.txt")

def prompt_objectifs():
    return fetch_prompt_from_git("https://raw.githubusercontent.com/saadichaima/prompt/refs/heads/main/objectifs.txt")

def prompt_travaux():
    return fetch_prompt_from_git("https://raw.githubusercontent.com/saadichaima/prompt/refs/heads/main/travaux.txt")

def prompt_partenariat():
    return fetch_prompt_from_git("https://raw.githubusercontent.com/saadichaima/prompt/refs/heads/main/partenariat.txt")

def prompt_verrou():
    return fetch_prompt_from_git("https://raw.githubusercontent.com/saadichaima/prompt/refs/heads/main/verrou.txt")


# ─────────────────────────────
# 🔧 Générateurs spécifiques
# ─────────────────────────────
def generate_contexte_section(index, chunks, vectors):
    return generate_section_with_rag("Contexte de l’opération de R&D", prompt_contexte(), index, chunks, vectors)

def generate_indicateurs_section(index, chunks, vectors):
    return generate_section_with_rag("Indicateurs de R&D", prompt_indicateurs(), index, chunks, vectors)

def generate_objectifs_section(index, chunks, vectors):
    return generate_section_with_rag("Objet de l’opération de R&D", prompt_objectifs(), index, chunks, vectors)

def generate_travaux_section(index, chunks, vectors):
    return generate_section_with_rag("Description de la démarche suivie et des travaux réalisés", prompt_travaux(), index, chunks, vectors)

def generate_contribution_section(index, chunks, vectors):
    return generate_section_with_rag("Contribution scientifique, technique ou technologique", prompt_contribution(), index, chunks, vectors)

def generate_partenariat_section(index, chunks, vectors):
    return generate_section_with_rag("Partenariat scientifique et recherche confiée", prompt_partenariat(), index, chunks, vectors)
