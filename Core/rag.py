import os
import numpy as np
import requests
from dotenv import load_dotenv
from openai import AzureOpenAI
from Core.embeddings import embed_texts

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

GPT_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")

# ─────────────────────────────
# 📥 Chargement des prompts depuis GitHub
# ─────────────────────────────
def load_prompt_from_github(file_name):
    base_url = "https://raw.githubusercontent.com/saadichaima/prompt/refs/heads/main/"
    url = base_url + file_name
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        print(f"✅ Prompt chargé : {file_name} ({len(response.text)} caractères)")
        return response.text
    except requests.RequestException as e:
        print(f"❌ Erreur chargement prompt '{file_name}': {e}")
        return ""

# ─────────────────────────────
# ⛽ Appel GPT via Azure
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

# ─────────────────────────────
# 🔍 Recherche sémantique
# ─────────────────────────────
def search_similar_chunks(query, index, chunks, vectors, top_k=3):
    if not query.strip():
        raise ValueError("❌ Le prompt est vide. Vérifiez vos fichiers de prompt GitHub.")
    q_vec = embed_texts([query])[0]
    q_vec_np = np.array([q_vec], dtype=np.float32)
    D, I = index.search(q_vec_np, top_k)
    return [chunks[i] for i in I[0]]

# ─────────────────────────────
# 🎯 Génération via RAG
# ─────────────────────────────
def generate_section_with_rag(titre, prompt_instruction, index, chunks, vectors):
    if not prompt_instruction.strip():
        raise ValueError(f"❌ Prompt vide pour la section : {titre}.")
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
# 🔧 Prompts dynamiques depuis GitHub
# ─────────────────────────────
def prompt_contexte():
    return load_prompt_from_github("prompt_contexte.txt")

def prompt_indicateurs():
    return load_prompt_from_github("indicateurs.txt")

def prompt_objectifs():
    return load_prompt_from_github("objectifs.txt")

def prompt_travaux():
    return load_prompt_from_github("travaux.txt")

def prompt_contribution():
    return load_prompt_from_github("contribution.txt")

def prompt_partenariat():
    return load_prompt_from_github("partenariat.txt")

# ─────────────────────────────
# 📄 Générateurs de sections CIR
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
