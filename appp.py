import os
import streamlit as st
from Core import document, keywords, embeddings, rag, crossref, writer

# ──────────────────────────────
# CONFIG
# ──────────────────────────────
st.set_page_config(page_title="Assistant CIR", page_icon="🧾", layout="centered")
st.title("🧠 Assistant CIR")

# Petit helper
def _need_client_docs(uploaded_files_client):
    return not uploaded_files_client or len(uploaded_files_client) == 0

# Flag global pour désactiver les boutons pendant un run
if "is_generating" not in st.session_state:
    st.session_state.is_generating = False


# ──────────────────────────────
# EN-TÊTE (inchangé)
# ──────────────────────────────
col_societe, col_projet, col_annee = st.columns([1, 1, 1])
with col_societe:
    societe = st.text_input("🏢 Société", value=st.session_state.get("societe", ""))
with col_projet:
    projet_name = st.text_input("📝 Nom du projet *", value=st.session_state.get("projet_name", ""))
with col_annee:
    annee = st.number_input("📅 Année *", min_value=2000, max_value=2100, value=st.session_state.get("annee", 2025), step=1, format="%d")

objectif = st.text_area(
    "🎯 Objectif du projet *",
    value=st.session_state.get("objectif", ""),
    placeholder="Décrivez l’objectif du projet ici..."
)

st.session_state["societe"] = societe
st.session_state["projet_name"] = projet_name
st.session_state["annee"] = annee
st.session_state["objectif"] = objectif

# ──────────────────────────────
# TÉLÉVERSEMENTS (inchangé)
# ──────────────────────────────
uploaded_files_client = st.file_uploader(
    "📎 Téléversez les documents client (optionnel)",
    type=["pdf", "docx"],
    accept_multiple_files=True
)
uploaded_files_admin = st.file_uploader(
    "📁 Téléversez les documents administratifs (optionnel)",
    type=["pdf", "docx"],
    accept_multiple_files=True
)

st.divider()

# ──────────────────────────────
# 1) RECHERCHE ARTICLES API
# ──────────────────────────────
st.subheader("🔎 Recherche bibliographique")

btn_rechercher = st.button("🔍 Recherche article API", disabled=st.session_state.is_generating)
if btn_rechercher:
    if not objectif.strip():
        st.error("❗ Veuillez d'abord saisir l’objectif du projet.")
    else:
        with st.spinner("📄 Analyse des documents & extraction de mots-clés…"):
            kw_list = keywords.extract_keywords(objectif, max_keywords=5)
            st.success("✅ Mots-clés : " + ", ".join(kw_list))

            # Première recherche seulement : on initialise et on décoche tout
            if "articles_suggested" not in st.session_state:
                arts = crossref.search_articles_crossref(kw_list, annee_reference=annee)
                for a in arts:
                    a["selected"] = False
                st.session_state["articles_suggested"] = arts

# Affichage de la liste des articles si on en a
if "articles_suggested" in st.session_state:
    st.subheader("📚 Articles scientifiques suggérés")
    new_list = []
    for i, article in enumerate(st.session_state["articles_suggested"]):
        checked = st.checkbox(
            f"{article['title']} ({article['year']}) — {article['authors']}",
            value=article.get("selected", False),
            key=f"article_select_{i}",
            disabled=st.session_state.is_generating
        )
        article["selected"] = checked
        new_list.append(article)
        if article.get("url"):
            st.markdown(f"[🔗 Voir l'article complet]({article['url']})")
    st.session_state["articles_suggested"] = new_list

st.divider()

# ──────────────────────────────
# 2) VERROU + 2 BOUTONS HORIZONTAUX
# ──────────────────────────────
st.subheader("🔐 Verrou technique & génération ciblée")

verrou_input = st.text_area(
    "🔐 Verrou technique (optionnel)",
    value=st.session_state.get("verrou_technique", ""),
    placeholder="Expliquez ici le verrou scientifique ou technique rencontré…",
    disabled=st.session_state.is_generating
)

# Deux boutons côte à côte
col_obj, col_ver = st.columns(2)
with col_obj:
    btn_gen_objet = st.button("🛠️ Générer l’objet de l’opération de R&D", disabled=st.session_state.is_generating)
with col_ver:
    btn_gen_verrou = st.button("✨ Générer le verrou automatiquement", disabled=st.session_state.is_generating)

# ---------- GÉNÉRER L’OBJET ----------
if btn_gen_objet:
    if _need_client_docs(uploaded_files_client):
        st.warning("📂 Veuillez téléverser au moins un document client.")
    elif not objectif.strip():
        st.warning("✏️ Veuillez saisir l’objectif du projet.")
    else:
        # Indexation si nécessaire (ou réindexation pour refléter les nouveaux uploads)
        with st.spinner("📄 Lecture et indexation des documents…"):
            full_text = ""
            for f in uploaded_files_client:
                full_text += "\n" + document.extract_text(f)
            chunks = document.chunk_text(full_text)
            index, vectors = embeddings.build_index(chunks)
            st.session_state.update({
                "full_text": full_text,
                "chunks": chunks,
                "index": index,
                "vectors": vectors
            })

            full_text_admin = ""
            if uploaded_files_admin:
                for f in uploaded_files_admin:
                    full_text_admin += "\n" + document.extract_text(f)

            full_text_mix = full_text + ("\n" + full_text_admin if full_text_admin else "")
            chunks_mix = document.chunk_text(full_text_mix)
            index_mix, vectors_mix = embeddings.build_index(chunks_mix)
            st.session_state.update({
                "full_text_mix": full_text_mix,
                "chunks_mix": chunks_mix,
                "index_mix": index_mix,
                "vectors_mix": vectors_mix
            })

        with st.spinner("🧠 Rédaction de la section « Objet de l’opération de R&D »…"):
            verrou_for_prompt = st.session_state.get("verrou_technique", verrou_input)
            selected_articles = [a for a in st.session_state.get("articles_suggested", []) if a.get("selected")]

            objet_genere = rag.generate_objectifs_section(
                index=st.session_state["index"],
                chunks=st.session_state["chunks"],
                vectors=st.session_state["vectors"],
                objectif=objectif,
                verrou=verrou_for_prompt,
                annee=annee,
                societe=societe,
                articles=selected_articles
            )

        st.session_state["objet_genere"] = objet_genere
        st.session_state["objet_section"] = objet_genere
        st.session_state["articles"] = selected_articles  # fige la sélection pour la biblio/état de l’art
        st.success("✅ Section « Objet » générée.")
        st.text_area("📄 Objet de l’opération de R&D :", objet_genere, height=280)

# ---------- GÉNÉRER LE VERROU ----------
if btn_gen_verrou:
    if "index" not in st.session_state or not st.session_state.get("objet_genere", "").strip():
        st.error("❗ Générez d’abord l’objet de l’opération de R&D.")
    else:
        with st.spinner("🔎 Génération du verrou technique…"):
            verrou_ai = rag.generate_section_with_rag(
                "Verrou technique",
                rag.prompt_verrou(st.session_state["objet_genere"]),
                st.session_state["index"],
                st.session_state["chunks"],
                st.session_state["vectors"]
            )
        st.session_state["verrou_technique"] = verrou_ai
        st.session_state["objet_section"] = st.session_state["objet_genere"].strip() + \
            "\n\n🔐 **Verrou technique rencontré :**\n" + verrou_ai.strip()
        st.success("✅ Verrou généré.")
        st.text_area("🔐 Verrou généré :", verrou_ai, height=220)

st.divider()

# ──────────────────────────────
# 3) GÉNÉRATION DU DOSSIER (à la fin)
# ──────────────────────────────
st.subheader("📝 Génération du dossier final")

# Bouton tout en bas
btn_gen_dossier = st.button("✨ Générer le dossier CIR", disabled=st.session_state.is_generating)

if btn_gen_dossier:
    if "index" not in st.session_state:
        st.error("❗ Veuillez d'abord générer la section « Objet de l’opération de R&D ».")
    else:
        st.session_state.is_generating = True
        try:
            holder = st.empty()
            with holder.container():
                with st.spinner("🧠 Génération du dossier technique…"):
                    verrou_final = st.session_state.get("verrou_technique", verrou_input)

                    # Fige la sélection d’articles au moment du build
                    st.session_state["articles"] = [
                        a for a in st.session_state.get("articles_suggested", []) if a.get("selected")
                    ]

                    # Contexte
                    contexte = rag.generate_contexte_section(
                        st.session_state["index"], st.session_state["chunks"], st.session_state["vectors"],
                        objectif, verrou_final, annee, societe
                    )
                    # Indicateurs
                    indicateurs = rag.generate_indicateurs_section(
                        st.session_state["index_mix"], st.session_state["chunks_mix"], st.session_state["vectors_mix"],
                        objectif, verrou_final, annee, societe
                    )
                    # Objet
                    objet_section = st.session_state.get("objet_section", st.session_state.get("objet_genere", ""))
                    # Travaux
                    travaux = rag.generate_travaux_section(
                        st.session_state["index"], st.session_state["chunks"], st.session_state["vectors"],
                        objectif, verrou_final, annee, societe
                    )
                    # Contribution
                    contribution = rag.generate_contribution_section(
                        st.session_state["index"], st.session_state["chunks"], st.session_state["vectors"],
                        objectif, verrou_final, annee, societe
                    )
                    # Biblio (avec sélection)
                    bibliographie = rag.generate_biblio_section(
                        st.session_state["index"], st.session_state["chunks"], st.session_state["vectors"],
                        objet_section,
                        st.session_state.get("articles", [])
                    )
                    # Partenariat
                    partenariat = rag.generate_partenariat_section(
                        st.session_state["index_mix"], st.session_state["chunks_mix"], st.session_state["vectors_mix"],
                        objectif, verrou_final, annee, societe
                    )
                    # État de l’art
                    etat_art = writer.generer_etat_art(st.session_state.get("articles", []))

                    sections = {
                        "Contexte de l’opération de R&D": contexte,
                        "Indicateurs de R&D": indicateurs,
                        "Objet de l’opération de R&D": objet_section,
                        "Description de la démarche suivie et des travaux réalisés": travaux,
                        "Contribution scientifique, technique ou technologique": contribution,
                        "Références bibliographiques": bibliographie,
                        "Partenariat scientifique et recherche confiée": partenariat,
                        "État de l’art scientifique": etat_art,
                        "Verrou technique rencontré": verrou_final
                    }

                    output_path = f"./Doc/Dossier_CIR_{projet_name.replace(' ', '_')}.docx"
                    writer.remplir_doc("./Doc/CLIENT_CIR.docx", output_path, sections)

            st.success("✅ Dossier généré avec succès !")
            with open(output_path, "rb") as f:
                st.download_button("📥 Télécharger le dossier Word", f, file_name=os.path.basename(output_path))
        except Exception as e:
            st.error("❌ Une erreur est survenue pendant la génération.")
            st.exception(e)
        finally:
            st.session_state.is_generating = False

# ──────────────────────────────
# PETITES AIDES / ÉTAT
# ──────────────────────────────
# Indications rapides si nécessaire
if not projet_name or not objectif.strip():
    st.info("ℹ️ Remplissez au minimum **Nom du projet** et **Objectif du projet**.")
