# Core/arxiv_api.py

import requests
import feedparser

def search_arxiv(keywords, start=0, max_results=10, year_min=None, year_max=None):
    """
    Recherche d'articles sur arXiv.
    :param keywords: liste de mots-clés
    :param start: index de départ
    :param max_results: nombre maximum d'articles
    :param year_min: année minimale (optionnel)
    :param year_max: année maximale (optionnel)
    :return: liste de dictionnaires avec infos article
    """
    query = "+".join(keywords)
    url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start={start}&max_results={max_results}&sortBy=relevance&sortOrder=descending"
    
    feed = feedparser.parse(requests.get(url, timeout=20).text)
    results = []

    for entry in feed.entries:
        published_year = int(entry.published.split("-")[0])

        # Filtre par date si précisé
        if year_min and published_year < year_min:
            continue
        if year_max and published_year > year_max:
            continue

        authors = ", ".join(author.name for author in entry.authors)
        pdf_link = None
        for link in entry.links:
            if link.rel == "alternate":
                continue
            if "pdf" in link.title.lower():
                pdf_link = link.href
                break

        results.append({
            "title": entry.title.strip(),
            "year": published_year,
            "authors": authors,
            "summary": entry.summary.strip(),
            "url": pdf_link or entry.id,
            "citations": None,  # arXiv ne fournit pas le nombre de citations
            "selected": False
        })

    return results
