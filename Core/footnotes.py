# Core/footnotes.py
from __future__ import annotations

import io
import os
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Set, Optional

from docx.oxml.ns import qn  # QName helper pour les tags w:*
from Core import rag         # utilise rag.call_ai(...) et rag.fetch_prompt_from_git(...)

# Namespaces
W_NS   = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS  = "http://schemas.openxmlformats.org/package/2006/content-types"
XML_NS = "http://www.w3.org/XML/1998/namespace"  # pour xml:space="preserve"

NS = {"w": W_NS}

# Filet : repérer des acronymes si l'IA en manque (>=2 caractères majuscules/chiffres)
ACRONYM_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,7}\b")

# ───────────────────────────────────────────────────────────────────
# 0) Chargement du prompt distant (détection des termes)
# ───────────────────────────────────────────────────────────────────
# URL configurable par variable d'environnement, sinon valeur par défaut
REMOTE_FOOTNOTES_PROMPT_URL = os.getenv(
    "FOOTNOTES_PROMPT_URL",
    "https://raw.githubusercontent.com/saadichaima/prompt/main/footnotes",
)

# Prompt local par défaut (fallback) si le distant est indisponible
DEFAULT_DETECT_PROMPT = """
Tu reçois un document en français. Tu dois lister UNIQUEMENT les termes qui nécessitent une
explication pour un lecteur non spécialiste, et fournir pour chacun une définition claire en 1 phrase.

INCLUS UNIQUEMENT SI VRAIMENT PERTINENT
- ACRONYMES techniques/scientifiques (2–10 caractères) : ex. RAG, LLM, MRR@k, BM25, FAISS.
- TERMES TECHNIQUES (expressions spécialisées) : ex. "réseau de neurones", "embedding vectoriel",
  "reranking hybride", "groundedness", "graphe de mémoire".

EXCLUSIONS FORMELLES (NE JAMAIS LISTER)
- Mots du langage courant, concepts business/généraux : entreprise, projet, client, équipe, consultant,
  innovation, objectif, rapport, présentation, etc.
- Titres/fonctions et entités organisationnelles : CEO, CTO, Direction, Comité scientifique, département.
- Formes juridiques/tailles/secteurs : SAS, SARL, SA, PME, TPE, secteur, pôle, université, laboratoire.
- Lieux, dates, personnes, noms d'entreprise/produit (sauf si c'est un acronyme technique standard).
- Unités/valeurs/mesures/métriques isolées : %, K€, s, ms, GPU, CPU (sauf si partie d’un concept technique).
- Marqueurs bibliographiques/citations : [SHAO, 2023], (YANG, 2024), DOI, URL.
- Termes déjà explicités entre parenthèses dans le texte (ex. "RAG (Retrieval-Augmented Generation)").

CRITÈRE DE COUPURE
- Si tu hésites, N'INCLUS PAS le terme.
- Objectif : haute précision, faible rappel. Mieux vaut rater un terme que lister un terme banal.

FORMAT DE SORTIE — JSON STRICT
[
  {"term": "RAG", "definition": "Méthode qui combine recherche d’informations et génération de texte pour répondre précisément à une requête."},
  {"term": "reranking hybride", "definition": "Technique qui re-classe les documents en combinant des scores d’indexation dense et parcimonieuse pour améliorer la pertinence."}
]
Ne renvoie RIEN d’autre que le tableau JSON.

LIMITE MAXIMALE (sécurité) : {max_terms} éléments.

DOCUMENT (extraits concaténés) :
\"\"\"{document}\"\"\"
""".strip()

def _load_remote_footnotes_template() -> str:
    """
    Récupère le template distant pour la détection des termes.
    Retourne "" si indisponible (on utilisera le fallback local).
    On ignore explicitement le message d'erreur retourné par fetch_prompt_from_git.
    """
    try:
        tpl = rag.fetch_prompt_from_git(REMOTE_FOOTNOTES_PROMPT_URL) or ""
        if tpl.strip().startswith("❌"):
            return ""
        return tpl.strip()
    except Exception:
        return ""

# ───────────────────────────────────────────────────────────────────
# 1) Détection par IA (termes + définitions 1 phrase)
# ───────────────────────────────────────────────────────────────────
def _detect_terms_with_ai(full_text: str, max_terms: int = 60) -> List[Dict[str, str]]:
    """
    Retourne une liste d'objets {"term": "...", "definition": "..."} détectés dans le texte.
    L'IA NE doit renvoyer QUE des termes réellement présents.

    Cette version charge d'abord un template distant (REMOTE_FOOTNOTES_PROMPT_URL)
    contenant les placeholders {max_terms} et {document}.
    Si indisponible, utilise DEFAULT_DETECT_PROMPT (même placeholders).
    """
    template = _load_remote_footnotes_template() or DEFAULT_DETECT_PROMPT

    # Construction du prompt final (on reste robuste si le template n'a pas les placeholders)
    try:
        prompt = template.format(
            max_terms=max_terms,
            document=full_text[:120000]  # borne de sécurité
        )
    except Exception:
        prompt = (
            f"{template}\n\n"
            f"[LIMITE] max_terms={max_terms}\n\n"
            f"[DOCUMENT]\n{full_text[:120000]}"
        )

    raw = rag.call_ai(prompt)
    try:
        start = raw.find("[")
        end   = raw.rfind("]") + 1
        arr = json.loads(raw[start:end])
        out = []
        for it in arr:
            t = (it.get("term") or "").strip()
            d = (it.get("definition") or "").strip()
            if not t or not d:
                continue
            if not d.endswith("."):
                d += "."
            out.append({"term": t, "definition": d})
        return out
    except Exception:
        return []


def _define_missing_acronyms(acronyms: List[str]) -> Dict[str, str]:
    """Complète des définitions pour des acronymes si la détection IA les a oubliés."""
    if not acronyms:
        return {}
    prompt = (
        "Donne une définition brève (1 phrase, français simple) pour chaque acronyme ci-dessous. "
        "Réponds LIGNE PAR LIGNE au format 'ACRONYME: définition'.\n\n" + "\n".join(sorted(set(acronyms)))
    )
    raw = rag.call_ai(prompt)
    defs: Dict[str, str] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip()
        if not v.endswith("."):
            v += "."
        if k:
            defs[k] = v
    # Sécurité si l'IA ne couvre pas tout
    for a in acronyms:
        defs.setdefault(a, f"{a} : acronyme technique.")
    return defs


# ───────────────────────────────────────────────────────────────────
# 2) Outils ZIP/XML (DOCX)
# ───────────────────────────────────────────────────────────────────
def _read_zip(z: zipfile.ZipFile, name: str) -> bytes | None:
    try:
        with z.open(name) as f:
            return f.read()
    except KeyError:
        return None

def _write_zip(zout: zipfile.ZipFile, name: str, data: bytes):
    zout.writestr(name, data)

def _ensure_content_types_override(xml_ct: bytes | None) -> bytes:
    if not xml_ct:
        root = ET.Element(f"{{{CT_NS}}}Types")
    else:
        root = ET.fromstring(xml_ct)
    exists = any(
        e.tag == f"{{{CT_NS}}}Override" and e.get("PartName") == "/word/footnotes.xml"
        for e in root
    )
    if not exists:
        ov = ET.Element(f"{{{CT_NS}}}Override")
        ov.set("PartName", "/word/footnotes.xml")
        ov.set("ContentType", "application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml")
        root.append(ov)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)

def _ensure_document_rels(xml_rels: bytes | None) -> bytes:
    rel_tag = f"{{{PKG_NS}}}Relationship"
    if not xml_rels:
        root = ET.Element(f"{{{PKG_NS}}}Relationships")
    else:
        root = ET.fromstring(xml_rels)

    for rel in root.findall(rel_tag):
        if rel.get("Type") == f"{REL_NS}/footnotes":
            return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    max_id = 1
    for rel in root.findall(rel_tag):
        rid = rel.get("Id", "")
        if rid.startswith("rId"):
            try:
                max_id = max(max_id, int(rid[3:]))
            except Exception:
                pass
    new_rel = ET.Element(rel_tag)
    new_rel.set("Id", f"rId{max_id+1}")
    new_rel.set("Type", f"{REL_NS}/footnotes")
    new_rel.set("Target", "footnotes.xml")
    root.append(new_rel)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)

def _build_or_append_footnotes_xml(existing: bytes | None, notes: Dict[int, Tuple[str, str]]) -> bytes:
    """
    notes = {footnote_id: (term, definition)}
    Crée 'word/footnotes.xml' si absent, sinon ajoute les nouvelles notes.
    Chaque note est formatée comme Word l’attend :
      - style de paragraphe 'FootnoteText'
      - run de référence initial (w:footnoteRef) avec style 'FootnoteReference'
      - tabulation, puis le texte "TERME : définition"
    """
    if existing:
        root = ET.fromstring(existing)
    else:
        root = ET.Element(qn("w:footnotes"), {qn("xmlns:w"): W_NS})
        # Separators requis (id=0, id=1)
        fn0 = ET.SubElement(root, qn("w:footnote"), {qn("w:type"): "separator", qn("w:id"): "0"})
        p0 = ET.SubElement(fn0, qn("w:p")); r0 = ET.SubElement(p0, qn("w:r"))
        ET.SubElement(r0, qn("w:separator"))

        fn1 = ET.SubElement(root, qn("w:footnote"), {qn("w:type"): "continuationSeparator", qn("w:id"): "1"})
        p1 = ET.SubElement(fn1, qn("w:p")); r1 = ET.SubElement(p1, qn("w:r"))
        ET.SubElement(r1, qn("w:continuationSeparator"))

    for nid in sorted(notes.keys()):
        term, desc = notes[nid]

        fn = ET.SubElement(root, qn("w:footnote"))
        fn.set(qn("w:id"), str(nid))

        p = ET.SubElement(fn, qn("w:p"))

        # Style de paragraphe 'FootnoteText'
        ppr = ET.SubElement(p, qn("w:pPr"))
        ET.SubElement(ppr, qn("w:pStyle"), {qn("w:val"): "FootnoteText"})

        # 1) Référence (numéro) au début de la note
        r_ref = ET.SubElement(p, qn("w:r"))
        rpr_ref = ET.SubElement(r_ref, qn("w:rPr"))
        ET.SubElement(rpr_ref, qn("w:rStyle"), {qn("w:val"): "FootnoteReference"})
        ET.SubElement(r_ref, qn("w:footnoteRef"))

        # 2) Tabulation après le numéro
        r_tab = ET.SubElement(p, qn("w:r"))
        ET.SubElement(r_tab, qn("w:tab"))

        # 3) Texte de la note
        r_txt = ET.SubElement(p, qn("w:r"))
        t = ET.SubElement(r_txt, qn("w:t"))
        t.text = f"{term} : {desc}"

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)

def _make_run_text(text: str) -> ET.Element:
    r = ET.Element(qn("w:r"))
    t = ET.SubElement(r, qn("w:t"))
    if text != text.strip():
        t.set(f"{{{XML_NS}}}space", "preserve")  # xml:space="preserve"
    t.text = text
    return r

def _make_run_footnote_ref(fid: int) -> ET.Element:
    r = ET.Element(qn("w:r"))

    # Style du renvoi (= numérotation affichée) + exposant
    rpr = ET.SubElement(r, qn("w:rPr"))
    ET.SubElement(rpr, qn("w:rStyle"), {qn("w:val"): "FootnoteReference"})
    ET.SubElement(rpr, qn("w:vertAlign"), {qn("w:val"): "superscript"})

    # Le renvoi lui-même
    fr = ET.SubElement(r, qn("w:footnoteReference"))
    fr.set(qn("w:id"), str(fid))
    return r



# ───────────────────────────────────────────────────────────────────
# 3) Parcours du document & insertion des footnotes (LOGIQUE INCHANGÉE)
# ───────────────────────────────────────────────────────────────────
def _extract_full_text(root: ET.Element) -> str:
    """Concatène tous les w:t pour analyse IA (sans mise en forme)."""
    texts = []
    for t in root.findall(".//w:t", NS):
        texts.append(t.text or "")
    return "\n".join(texts)

def _paragraph_runs_with_text(p: ET.Element) -> List[Tuple[ET.Element, ET.Element, str]]:
    """Liste ordonnée de (run, t, texte) pour un paragraphe w:p (on ignore les runs sans w:t)."""
    items: List[Tuple[ET.Element, ET.Element, str]] = []
    for r in list(p):
        if r.tag != qn("w:r"):
            continue
        for t in r.findall("w:t", NS):
            items.append((r, t, t.text or ""))
    return items

def _find_matches_in_text(text: str, terms: List[str]) -> List[Tuple[int, int, str]]:
    """
    Trouve la 1re occurrence de chaque terme dans 'text'.
    Retour : liste de (start, end, term) SANS chevauchement, triée par end décroissant.
    """
    found: List[Tuple[int, int, str]] = []
    used: List[Tuple[int, int]] = []
    for term in sorted(terms, key=len, reverse=True):
        start = text.find(term)
        if start < 0:
            continue
        end = start + len(term)
        if any(not (end <= s or start >= e) for (s, e) in used):
            continue
        used.append((start, end))
        found.append((start, end, term))
    found.sort(key=lambda x: x[1], reverse=True)  # droite -> gauche
    return found

def _insert_footnote_in_paragraph(p: ET.Element, matches: List[Tuple[int,int,str]],
                                  term2fid: Dict[str,int]):
    """
    Insère, dans le paragraphe w:p 'p', un <w:footnoteReference w:id="...">
    juste après chaque match (triés de droite à gauche).
    """
    items = _paragraph_runs_with_text(p)
    if not items:
        return

    # positions cumulées sur le paragraphe
    cum = []
    pos = 0
    for r, t, txt in items:
        start = pos
        end = pos + len(txt)
        cum.append((r, t, txt, start, end))
        pos = end

    para_len = pos

    for start, end, term in matches:
        if end > para_len:
            continue
        # segment qui contient 'end'
        seg_idx = None
        for i, (_, _, _, s, e) in enumerate(cum):
            if s < end <= e:
                seg_idx = i
                break
        if seg_idx is None:
            continue

        r, t, txt, s, e = cum[seg_idx]
        off = end - s
        left, right = txt[:off], txt[off:]

        # 1) tronquer le run courant à 'left'
        t.text = left

        # 2) insérer footnoteRef + run 'right' après le run courant
        siblings = list(p)
        ridx = siblings.index(r)

        p.insert(ridx + 1, _make_run_footnote_ref(term2fid[term]))
        if right:
            p.insert(ridx + 2, _make_run_text(right))
        # (On traite droite→gauche, donc pas besoin de recalculer 'cum')


def add_smart_footnotes(docx_path: str, max_terms: Optional[int] = None) -> int:
    """
    Analyse le .docx, détecte via IA les acronymes + termes techniques présents,
    génère une définition 1 phrase et insère de VRAIES notes de bas de page Word
    à la 1ʳᵉ occurrence globale de chaque terme.

    Modifie le fichier en place.
    Retourne le nombre de notes ajoutées.

    max_terms:
      - None  -> pas de limite côté appelant (plafond interne large pour sécurité).
      - int   -> limite explicite.
    """
    # 1) Ouvrir le docx
    with zipfile.ZipFile(docx_path, "r") as zin:
        files = {n: zin.read(n) for n in zin.namelist()}

    DOC = "word/document.xml"
    REL = "word/_rels/document.xml.rels"
    CT  = "[Content_Types].xml"
    FNS = "word/footnotes.xml"

    if DOC not in files:
        return 0

    root = ET.fromstring(files[DOC])

    # 2) Texte complet pour l'IA
    full_text = _extract_full_text(root)

    # 3) Détection IA (termes + définitions)
    cap = 120 if (max_terms is None) else max_terms  # garde-fou interne large
    ai_pairs = _detect_terms_with_ai(full_text, max_terms=cap)

    # 3bis) filet : ajouter acronymes repérés par regex si l'IA les a manqués
    acrs = sorted(set(ACRONYM_RE.findall(full_text)))
    known_terms = {p["term"] for p in ai_pairs}
    missing_acrs = [a for a in acrs if a not in known_terms]
    if missing_acrs:
        defs_extra = _define_missing_acronyms(missing_acrs)
        for a in missing_acrs:
            ai_pairs.append({"term": a, "definition": defs_extra.get(a, f"{a} : acronyme technique.")})

    # 4) Uniques + cap éventuel
    uniq: List[Dict[str, str]] = []
    seen: Set[str] = set()
    for it in ai_pairs:
        t = it["term"]
        if t in seen:
            continue
        seen.add(t)
        uniq.append(it)
        if max_terms is not None and len(uniq) >= max_terms:
            break
    if not uniq:
        return 0

    # 5) Numérotation des footnotes (si footnotes.xml existe déjà → reprendre à max+1)
    start_id = 2
    if FNS in files:
        froot = ET.fromstring(files[FNS])
        ids = []
        for n in froot.findall(f".//{{{W_NS}}}footnote"):
            try:
                ids.append(int(n.get(qn("w:id"))))
            except Exception:
                pass
        if ids:
            start_id = max(max(ids) + 1, 2)

    term2fid: Dict[str, int] = {}
    notes_payload: Dict[int, Tuple[str, str]] = {}
    nxt = start_id
    for it in uniq:
        term = it["term"]
        term2fid[term] = nxt
        notes_payload[nxt] = (term, it["definition"])
        nxt += 1

    # 6) Parcourir les paragraphes et insérer la note à la 1ʳᵉ occurrence globale
    annotated: Set[str] = set()
    for p in root.findall(".//w:p", NS):
        items = _paragraph_runs_with_text(p)
        if not items:
            continue
        para_text = "".join(txt for _, _, txt in items)
        remaining = [t for t in term2fid.keys() if t not in annotated and t in para_text]
        if not remaining:
            continue
        matches = _find_matches_in_text(para_text, remaining)
        if not matches:
            continue
        _insert_footnote_in_paragraph(p, matches, term2fid)
        for _, _, term in matches:
            annotated.add(term)
        if len(annotated) == len(term2fid):
            break

    added = len(annotated)
    if added == 0:
        return 0

    # 7) Écrire / mettre à jour footnotes.xml
    new_fns = _build_or_append_footnotes_xml(
        files.get(FNS),
        {term2fid[t]: notes_payload[term2fid[t]] for t in annotated}
    )

    # 8) Mettre à jour rels + content types
    new_rels = _ensure_document_rels(files.get(REL))
    new_ct   = _ensure_content_types_override(files.get(CT))

    # 9) Sauvegarder le docx mis à jour
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            if name in {DOC, REL, CT, FNS}:
                continue
            _write_zip(zout, name, data)
        _write_zip(zout, DOC, ET.tostring(root, encoding="utf-8", xml_declaration=True))
        _write_zip(zout, REL, new_rels)
        _write_zip(zout, CT, new_ct)
        _write_zip(zout, FNS, new_fns)

    with open(docx_path, "wb") as f:
        f.write(buf.getvalue())

    return added
