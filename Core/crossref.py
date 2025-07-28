# core/crossref.py

import requests
import time

def search_articles_crossref(keywords, max_articles=10):
    """Recherche les meilleurs articles scientifiques récents à partir des mots-clés"""
    base_url = "https://api.crossref.org/works"
    found = []

    for kw in keywords:
        try:
            res = requests.get(
                base_url,
                params={
                    "query": kw,
                    "rows": max_articles,
                    "filter": "from-pub-date:2023",
                    "sort": "relevance"  # peut être changé par 'is-referenced-by-count' si plus pertinent
                },
                timeout=20
            )
            if res.status_code == 200:
                items = res.json()["message"]["items"]
                for item in items:
                    # Vérification de l’année
                    pub_year = (
                        item.get("published-print", {}).get("date-parts", [[None]])[0][0]
                        or item.get("published-online", {}).get("date-parts", [[None]])[0][0]
                        or item.get("created", {}).get("date-parts", [[None]])[0][0]
                    )
                    if pub_year and int(pub_year) >= 2023:
                        found.append({
                            "title": item.get("title", ["Sans titre"])[0],
                            "year": pub_year,
                            "authors": ", ".join(
                                a.get("family", "") for a in item.get("author", [])
                            ) if item.get("author") else "Auteur inconnu",
                            "url": item.get("URL", ""),
                            "citations": item.get("is-referenced-by-count", 0),
                            "selected": True  # Par défaut cochés
                        })

            time.sleep(1)  # éviter le blocage de l'API
        except Exception as e:
            print(f"Erreur CrossRef pour '{kw}': {e}")
            continue

    # Trier tous les articles trouvés par nombre de citations décroissant
    found.sort(key=lambda x: x["citations"], reverse=True)

    # Ne garder que les 10 meilleurs globalement
    return found[:max_articles]
