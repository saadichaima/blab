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

def build_prompt_from_template(template_str, objectif, verrou, annee,societe):
    return template_str.format(
        objectif=objectif.strip(),
        verrou=verrou.strip(),
        annee=annee,
        societe=societe.strip(),
 
    )
def build_prompt_from_template_verrou(template_str, objet):
    return template_str.format(
        objet=objet.strip(),

 
    )

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


"""
    return call_ai(full_prompt)

# ─────────────────────────────
# ✍️ Prompts spécifiques
# ─────────────────────────────


def prompt_contribution(objectif, verrou, annee,societe):
    raw_url = "https://raw.githubusercontent.com/saadichaima/prompt/refs/heads/main/contribution.txt"
    template = fetch_prompt_from_git(raw_url)
    return build_prompt_from_template(template, objectif, verrou, annee,societe)

def prompt_contexte(objectif, verrou, annee,societe):
    raw_url = "https://raw.githubusercontent.com/saadichaima/prompt/refs/heads/main/prompt_contexte.txt"
    template = fetch_prompt_from_git(raw_url)
    return build_prompt_from_template(template, objectif, verrou, annee,societe)


def prompt_indicateurs(objectif, verrou, annee,societe):
    raw_url = "https://raw.githubusercontent.com/saadichaima/prompt/refs/heads/main/indicateurs.txt"
    template = fetch_prompt_from_git(raw_url)
    return build_prompt_from_template(template, objectif, verrou, annee,societe)

def prompt_objectifs(objectif, verrou, annee,societe):
    raw_url = "https://raw.githubusercontent.com/saadichaima/prompt/refs/heads/main/objectifs.txt"
    template = fetch_prompt_from_git(raw_url)
    return build_prompt_from_template(template, objectif, verrou, annee,societe)


def prompt_travaux(objectif, verrou, annee,societe):
    raw_url = "https://raw.githubusercontent.com/saadichaima/prompt/refs/heads/main/travaux.txt"
    template = fetch_prompt_from_git(raw_url)
    return build_prompt_from_template(template, objectif, verrou, annee,societe)

def prompt_partenariat(objectif, verrou, annee,societe):
    raw_url = "https://raw.githubusercontent.com/saadichaima/prompt/refs/heads/main/partenariat.txt"
    template = fetch_prompt_from_git(raw_url)
    return build_prompt_from_template(template, objectif, verrou, annee,societe)

def prompt_verrou(objet):
    raw_url = "https://raw.githubusercontent.com/saadichaima/prompt/refs/heads/main/verrou.txt"
    template = fetch_prompt_from_git(raw_url)
    return build_prompt_from_template_verrou(template, objet)
def prompt_biblio(objet):
    raw_url = "https://raw.githubusercontent.com/saadichaima/prompt/refs/heads/main/bibliographie.txt"
    template = fetch_prompt_from_git(raw_url)
    return build_prompt_from_template_verrou(template, objet)

# ─────────────────────────────
# 🔧 Générateurs spécifiques
# ─────────────────────────────
def generate_contexte_section(index, chunks, vectors,objectif,verrou,annee,societe):
    return generate_section_with_rag("Contexte de l’opération de R&D", prompt_contexte(objectif,verrou,annee,societe), index, chunks, vectors)

def generate_indicateurs_section(index, chunks, vectors,objectif,verrou,annee,societe):
    return generate_section_with_rag("Indicateurs de R&D", prompt_indicateurs(objectif,verrou,annee,societe), index, chunks, vectors)

def generate_objectifs_section(index, chunks, vectors,objectif,verrou,annee,societe):
    return generate_section_with_rag("Objet de l’opération de R&D", prompt_objectifs(objectif,verrou,annee,societe), index, chunks, vectors)

def generate_travaux_section(index, chunks, vectors,objectif,verrou,annee,societe):
    return generate_section_with_rag("Description de la démarche suivie et des travaux réalisés", prompt_travaux(objectif,verrou,annee,societe), index, chunks, vectors)

def generate_contribution_section(index, chunks, vectors,objectif,verrou,annee,societe):
    return generate_section_with_rag("Contribution scientifique, technique ou technologique", prompt_contribution(objectif,verrou,annee,societe), index, chunks, vectors)

def generate_partenariat_section(index, chunks, vectors,objectif,verrou,annee,societe):
    return generate_section_with_rag("Partenariat scientifique et recherche confiée", prompt_partenariat(objectif,verrou,annee,societe), index, chunks, vectors)
def generate_biblio_section(index, chunks, vectors,objet):
    return generate_section_with_rag("Références bibliographiques", prompt_biblio(objet), index, chunks, vectors)
