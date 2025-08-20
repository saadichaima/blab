# Core/rag.py

import os
import numpy as np
from typing import Callable, Optional, Dict, Any, List
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
# 🔢 Instrumentation tokens
# ─────────────────────────────
TOKENS_SINK: Optional[Callable[[Dict[str, Any]], None]] = None

def set_tokens_sink(fn: Optional[Callable[[Dict[str, Any]], None]]):
    """
    Enregistre un callback appelé à CHAQUE appel modèle.
    Signature: fn({'meta': ..., 'prompt_tokens': int, 'completion_tokens': int,
                   'total_tokens': int, 'prompt_tokens_details': {...} | None})
    Passe None pour désactiver.
    """
    global TOKENS_SINK
    TOKENS_SINK = fn

# ─────────────────────────────
# ⛽ Base d'appel OpenAI
# ─────────────────────────────
def _extract_usage(resp) -> Dict[str, Any]:
    """Rend un dict usage robuste selon la version du SDK."""
    try:
        if hasattr(resp, "model_dump"):
            return (resp.model_dump() or {}).get("usage", {}) or {}
        # fallback ultra prudent
        u = getattr(resp, "usage", None)
        return dict(u) if isinstance(u, dict) else (u or {})
    except Exception:
        return {}

def call_ai(prompt: str, *, meta: Optional[str] = None, return_usage: bool = False):
    """
    Appelle Azure OpenAI.
      - meta: étiquette libre (ex: nom de section) remontée au sink
      - return_usage=True → renvoie (texte, usage_dict), sinon juste le texte
    """
    response = client.chat.completions.create(
        model=GPT_DEPLOYMENT,
        messages=[
            {"role": "system", "content": "Tu es un expert du Crédit d'Impôt Recherche."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4,
        max_tokens=4000
    )
    text = response.choices[0].message.content
    usage = _extract_usage(response)

    # Notify sink
    if TOKENS_SINK:
        try:
            TOKENS_SINK({
                "meta": meta,
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
                "prompt_tokens_details": usage.get("prompt_tokens_details")
            })
        except Exception:
            # on ne bloque jamais l'exécution pour la télémétrie
            pass

    return (text, usage) if return_usage else text

# ─────────────────────────────
# 📥 Prompts distants
# ─────────────────────────────
def fetch_prompt_from_git(url: str) -> str:
    """
    Récupère un prompt texte depuis GitHub Raw. Timeout court et fallback "".
    (On évite d'injecter un message d'erreur textuel dans un prompt.)
    """
    try:
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        return response.text.strip()
    except Exception:
        return ""

# ─────────────────────────────
# 🔍 Recherche sémantique
# ─────────────────────────────
def search_similar_chunks(query: str, index, chunks: List[str], vectors, top_k: int = 3):
    q_vec = embed_texts([query])[0]
    q_vec_np = np.array([q_vec], dtype=np.float32).reshape(1, -1)

    actual_k = min(top_k, len(chunks))
    distances, indices = index.kneighbors(q_vec_np, n_neighbors=actual_k)
    return [chunks[i] for i in indices[0]]

def build_prompt_from_template(template_str: str, objectif: str, verrou: str, annee: int, societe: str) -> str:
    return (template_str or "").format(
        objectif=objectif.strip(),
        verrou=verrou.strip(),
        annee=annee,
        societe=societe.strip(),
    )

def build_prompt_from_template_verrou(template_str: str, objet: str) -> str:
    return (template_str or "").format(objet=objet.strip())

# ─────────────────────────────
# 🎯 Générateur générique
# ─────────────────────────────
def generate_section_with_rag(titre: str, prompt_instruction: str, index, chunks, vectors):
    context = "\n".join(search_similar_chunks(prompt_instruction, index, chunks, vectors))
    full_prompt = f"""Tu dois rédiger la section suivante : "{titre}".

Voici le contexte extrait des documents client :
\"\"\"
{context}
\"\"\"


Consignes spécifiques :
{prompt_instruction}
"""
    # meta=titre → utile pour tracer les tokens par section
    return call_ai(full_prompt, meta=titre)

# ─────────────────────────────
# ✍️ Prompts spécifiques (URLs corrigées)
# ─────────────────────────────
def prompt_contribution(objectif, verrou, annee, societe):
    raw_url = "https://raw.githubusercontent.com/saadichaima/prompt/main/contribution.txt"
    template = fetch_prompt_from_git(raw_url)
    return build_prompt_from_template(template, objectif, verrou, annee, societe)

def prompt_contexte(objectif, verrou, annee, societe):
    raw_url = "https://raw.githubusercontent.com/saadichaima/prompt/main/prompt_contexte.txt"
    template = fetch_prompt_from_git(raw_url)
    return build_prompt_from_template(template, objectif, verrou, annee, societe)

def prompt_indicateurs(objectif, verrou, annee, societe):
    raw_url = "https://raw.githubusercontent.com/saadichaima/prompt/main/indicateurs.txt"
    template = fetch_prompt_from_git(raw_url)
    return build_prompt_from_template(template, objectif, verrou, annee, societe)

def prompt_objectifs(objectif, verrou, annee, societe):
    raw_url = "https://raw.githubusercontent.com/saadichaima/prompt/main/objectifs.txt"
    template = fetch_prompt_from_git(raw_url)
    return build_prompt_from_template(template, objectif, verrou, annee, societe)

def prompt_travaux(objectif, verrou, annee, societe):
    raw_url = "https://raw.githubusercontent.com/saadichaima/prompt/main/travaux.txt"
    template = fetch_prompt_from_git(raw_url)
    return build_prompt_from_template(template, objectif, verrou, annee, societe)

def prompt_partenariat(objectif, verrou, annee, societe):
    raw_url = "https://raw.githubusercontent.com/saadichaima/prompt/main/partenariat.txt"
    template = fetch_prompt_from_git(raw_url)
    return build_prompt_from_template(template, objectif, verrou, annee, societe)

def prompt_verrou(objet):
    raw_url = "https://raw.githubusercontent.com/saadichaima/prompt/main/verrou.txt"
    template = fetch_prompt_from_git(raw_url)
    return build_prompt_from_template_verrou(template, objet)

def prompt_biblio(objet):
    raw_url = "https://raw.githubusercontent.com/saadichaima/prompt/main/bibliographie.txt"
    template = fetch_prompt_from_git(raw_url)
    return build_prompt_from_template_verrou(template, objet)

# ─────────────────────────────
# 🔧 Générateurs spécifiques
# ─────────────────────────────
def prompt_objectifs_filtre(objectif, verrou, annee, societe, articles):
    """
    Même template 'objectifs.txt' mais n'injecte que les articles sélectionnés.
    """
    raw_url = "https://raw.githubusercontent.com/saadichaima/prompt/main/objectifs.txt"
    template = fetch_prompt_from_git(raw_url)

    year_start = annee - 5
    year_end = annee - 1
    liste_articles = "\n".join([f"- {a['authors']} ({a['year']}). {a['title']}" for a in articles])

    return (template or "").format(
        objectif=objectif.strip(),
        verrou=verrou.strip(),
        annee=annee,
        societe=societe.strip(),
        liste_articles=liste_articles,
        annee_debut=year_start,
        annee_fin=year_end
    )

def generate_contexte_section(index, chunks, vectors, objectif, verrou, annee, societe):
    return generate_section_with_rag("Contexte de l’opération de R&D", prompt_contexte(objectif, verrou, annee, societe), index, chunks, vectors)

def generate_indicateurs_section(index, chunks, vectors, objectif, verrou, annee, societe):
    return generate_section_with_rag("Indicateurs de R&D", prompt_indicateurs(objectif, verrou, annee, societe), index, chunks, vectors)

def generate_objectifs_section(index, chunks, vectors, objectif, verrou, annee, societe, articles=[]):
    # Utilise uniquement les articles cochés
    return generate_section_with_rag(
        "Objet de l’opération de R&D",
        prompt_objectifs_filtre(objectif, verrou, annee, societe, articles),
        index, chunks, vectors
    )

def generate_travaux_section(index, chunks, vectors, objectif, verrou, annee, societe):
    return generate_section_with_rag("Description de la démarche suivie et des travaux réalisés", prompt_travaux(objectif, verrou, annee, societe), index, chunks, vectors)

def generate_contribution_section(index, chunks, vectors, objectif, verrou, annee, societe):
    return generate_section_with_rag("Contribution scientifique, technique ou technologique", prompt_contribution(objectif, verrou, annee, societe), index, chunks, vectors)

def generate_partenariat_section(index, chunks, vectors, objectif, verrou, annee, societe):
    return generate_section_with_rag("Partenariat scientifique et recherche confiée", prompt_partenariat(objectif, verrou, annee, societe), index, chunks, vectors)

def generate_biblio_section(index, chunks, vectors, objet, articles=[]):
    if articles:
        # Format ISO simplifié
        def format_iso(article):
            auteurs = article["authors"]
            annee = article["year"]
            titre = article["title"]
            url = article.get("url", "")
            return f"{auteurs} ({annee}). *{titre}*. Disponible sur : {url}"

        # Supprimer doublons par titre
        seen = set()
        unique_articles = []
        for a in articles:
            if a["title"] not in seen:
                seen.add(a["title"])
                unique_articles.append(a)

        articles_sorted = sorted(unique_articles, key=lambda x: x["authors"].split(",")[0].strip().lower())
        return "\n".join([format_iso(a) for a in articles_sorted])

    # Fallback si pas d’articles : génération RAG
    return generate_section_with_rag("Références bibliographiques", prompt_biblio(objet), index, chunks, vectors)

# ─────────────────────────────
# 🏢 Prompts "Entreprise" & "Gestion de la recherche"
# ─────────────────────────────
def prompt_entreprise(objectif, verrou, annee, societe):
    raw_url = "https://raw.githubusercontent.com/saadichaima/prompt/main/entreprise.txt"
    template = fetch_prompt_from_git(raw_url)
    return build_prompt_from_template(template, objectif, verrou, annee, societe)

def prompt_gestion_recherche(objectif, verrou, annee, societe):
    raw_url = "https://raw.githubusercontent.com/saadichaima/prompt/main/gestion_recherche.txt"
    template = fetch_prompt_from_git(raw_url)
    return build_prompt_from_template(template, objectif, verrou, annee, societe)

# ─────────────────────────────
# 🏗️ Générateurs
# ─────────────────────────────
def generate_entreprise_section(index, chunks, vectors, objectif, verrou, annee, societe):
    return generate_section_with_rag(
        "L’entreprise",
        prompt_entreprise(objectif, verrou, annee, societe),
        index, chunks, vectors
    )

def generate_gestion_recherche_section(index, chunks, vectors, objectif, verrou, annee, societe):
    return generate_section_with_rag(
        "Gestion de la recherche",
        prompt_gestion_recherche(objectif, verrou, annee, societe),
        index, chunks, vectors
    )
