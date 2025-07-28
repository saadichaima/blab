# core/keywords.py

import os
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

GPT_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")


def extract_keywords(text, max_keywords=8):
    """Utilise GPT pour extraire des mots-clés combinés et pertinents à partir du contenu scientifique"""
    prompt = f"""
Tu es un expert scientifique.

À partir du texte ci-dessous, génère une liste de 5 à {max_keywords} expressions clés ou groupes de mots-clés scientifiques/techniques (2 à 5 mots chacun). Ces mots-clés doivent représenter précisément les concepts, technologies ou problématiques abordés. N’utilise pas de termes vagues ou trop génériques comme "recherche", "technologie", etc.
essaye de choisir des expression combinés pour ne pas perdre le sens du texte, 
Texte source :
\"\"\"
{text[:3000]}
\"\"\"

Format attendu :
- mot-clé 1
- mot-clé 2
- ...
    """

    response = client.chat.completions.create(
        model=GPT_DEPLOYMENT,
        messages=[
            {"role": "system", "content": "Tu es un assistant en rédaction scientifique et technique."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=300
    )

    raw = response.choices[0].message.content
    keywords = [line.strip("-• ").strip() for line in raw.split("\n") if line.strip()]
    return [kw for kw in keywords if len(kw.split()) >= 2]
