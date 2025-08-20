import os
from dotenv import load_dotenv
from openai import AzureOpenAI

# Charger .env (situé à la racine du projet)
load_dotenv()

required = [
    "AZURE_OPENAI_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_VERSION",
    "AZURE_OPENAI_DEPLOYMENT",
]
missing = [k for k in required if not os.getenv(k)]
if missing:
    raise SystemExit(f"❌ Variables manquantes: {', '.join(missing)}  (vérifie ton .env)")

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
)

DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT")

def test_once():
    messages = [
        {"role": "system", "content": "Tu es un assistant concis."},
        {"role": "user", "content": "Explique-moi le RAG en 3 phrases."},
    ]
    resp = client.chat.completions.create(
        model=DEPLOYMENT_NAME,   # ← nom de DÉPLOIEMENT Azure
        messages=messages,
        temperature=0.2,
        max_tokens=200,
    )

    text = resp.choices[0].message.content
    usage = getattr(resp, "usage", None) or (resp.model_dump() or {}).get("usage", {})

    print("\n==== RÉPONSE ====\n", text)
    print("\n==== TOKENS ====")
    print(
        "prompt_tokens =", usage.get("prompt_tokens"),
        "| completion_tokens =", usage.get("completion_tokens"),
        "| total_tokens =", usage.get("total_tokens"),
    )
    details = usage.get("prompt_tokens_details") if isinstance(usage, dict) else None
    if details:
        print("prompt_tokens_details =", details)

if __name__ == "__main__":
    print("Endpoint :", os.getenv("AZURE_OPENAI_ENDPOINT"))
    print("Deployment name :", DEPLOYMENT_NAME)
    print("API version :", os.getenv("AZURE_OPENAI_API_VERSION"))
    test_once()
