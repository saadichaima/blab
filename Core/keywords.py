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
SERPAPI_KEY = os.getenv("SERPAPI_API_KEY")

def extract_keywords(text, max_keywords=5):
    """Utilise GPT pour extraire des mots-clés scientifiques ET techniques précis"""
    prompt = f"""
Tu es un expert scientifique et technique.

À partir du texte ci-dessous, génère {max_keywords} mots-clés ou expressions-clés pertinents
(2 à 5 mots chacun) comprenant au moins :
- un ou plusieurs concepts scientifiques spécifiques
- un ou plusieurs termes techniques ou technologies précises

Ces mots-clés doivent être adaptés à une recherche bibliographique internationale
et éviter les termes vagues (ex : "recherche", "technologie").

Texte source :
\"\"\"{text[:3000]}\"\"\"

Format attendu :
mot-clé 1
mot-clé 2
...
    """

    response = client.chat.completions.create(
        model=GPT_DEPLOYMENT,
        messages=[
            {"role": "system", "content": "Tu es un assistant en rédaction scientifique et technique."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=300
    )

    raw = response.choices[0].message.content
    keywords = [line.strip("-• ").strip() for line in raw.split("\n") if line.strip()]
    return [kw for kw in keywords if len(kw.split()) >= 2]
