# core/crossref.py

import requests
import time

def search_articles_crossref(keywords, annee_reference=2025, max_articles=10):
    """Recherche les meilleurs articles scientifiques publiés entre (annee_reference - 5) et (annee_reference - 1)"""
    base_url = "https://api.crossref.org/works"
    found = []

    start_year = annee_reference - 5
    end_year = annee_reference - 1

    for kw in keywords:
        try:
            res = requests.get(
                base_url,
                params={
                    "query": kw,
                    "rows": max_articles,
                    "filter": f"from-pub-date:{start_year},until-pub-date:{end_year}",
                    "sort": "relevance"
                },
                timeout=20
            )

            if res.status_code == 200:
                items = res.json()["message"]["items"]
                for item in items:
                    pub_year = (
                        item.get("published-print", {}).get("date-parts", [[None]])[0][0]
                        or item.get("published-online", {}).get("date-parts", [[None]])[0][0]
                        or item.get("created", {}).get("date-parts", [[None]])[0][0]
                    )

                    if pub_year and start_year <= int(pub_year) <= end_year:
                        found.append({
                            "title": item.get("title", ["Sans titre"])[0],
                            "year": pub_year,
                            "authors": ", ".join(
                                a.get("family", "") for a in item.get("author", [])
                            ) if item.get("author") else "Auteur inconnu",
                            "url": item.get("URL", ""),
                            "citations": item.get("is-referenced-by-count", 0),
                            "selected": True
                        })

            time.sleep(1)  # anti-spam CrossRef
        except Exception as e:
            print(f"Erreur CrossRef pour '{kw}': {e}")
            continue

    # Trier par nombre de citations décroissant
    found.sort(key=lambda x: x["citations"], reverse=True)

    # Retourner les meilleurs articles
    return found[:max_articles]

