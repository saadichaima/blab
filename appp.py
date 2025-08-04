import streamlit as st
from Core import document, keywords, embeddings, rag, crossref, writer
import os

# ──────────────────────────────
# CONFIGURATION
# ──────────────────────────────
st.set_page_config(page_title="Assistant CIR", page_icon="🧾")
st.title("🧠 Assistant CIR")

col_projet, col_annee = st.columns([2, 1])
with col_projet:
    projet_name = st.text_input("📝 Nom du projet *")
with col_annee:
    annee = st.number_input("📅 Année *", min_value=2000, max_value=2100, value=2025, step=1, format="%d")

objectif = st.text_area("🎯 Objectif du projet *", placeholder="Décrivez l’objectif du projet ici...")

# ──────────────────────────────
# TÉLÉVERSEMENT DE DOCUMENTS (optionnels)
# ──────────────────────────────
uploaded_files_client = st.file_uploader("📎 Téléversez les documents **client** (optionnel)", type=["pdf", "docx"], accept_multiple_files=True)
uploaded_files_admin = st.file_uploader("📁 Téléversez les documents **administratifs** (optionnel)", type=["pdf", "docx"], accept_multiple_files=True)

# ──────────────────────────────
# BOUTON : GÉNÉRER OBJETS
# ──────────────────────────────
# ──────────────────────────────
# BOUTON : GÉNÉRER LA SECTION "OBJET DE L’OPÉRATION DE R&D"
# ──────────────────────────────
if st.button("🛠️ Générer la section « Objet de l’opération de R&D »"):
    if not uploaded_files_client:
        st.warning("📂 Veuillez téléverser au moins un document client.")
    elif not objectif.strip():
        st.warning("✏️ Veuillez saisir l’objectif du projet.")
    else:
        with st.spinner("📄 Lecture et indexation des documents client..."):
            full_text = ""
            for file in uploaded_files_client:
                full_text += "\n" + document.extract_text(file)
            chunks = document.chunk_text(full_text)
            index, vectors = embeddings.build_index(chunks)

            st.session_state["full_text"] = full_text
            st.session_state["chunks"] = chunks
            st.session_state["index"] = index
            st.session_state["vectors"] = vectors

        with st.spinner("🧠 Génération de la section « Objet de l’opération de R&D »..."):
            verrou = st.session_state.get("verrou_technique", "")
            objet_section = rag.generate_objectifs_section(
                index=index,
                chunks=chunks,
                vectors=vectors,
                objectif=objectif,
                verrou=verrou,
                annee=annee
            )
            st.session_state["objet_section"] = objet_section

        st.success("✅ Section générée avec succès !")
        st.text_area("📄 Objet de l’opération de R&D :", objet_section, height=300)


# ──────────────────────────────
# VERROU TECHNIQUE (optionnel)
# ──────────────────────────────
verrou_technique = st.session_state.get("verrou_technique", "")
verrou_technique = st.text_area("🔐 Verrou technique (optionnel)", value=verrou_technique, placeholder="Expliquez ici le verrou scientifique ou technique rencontré…")

if not verrou_technique.strip():
    st.warning("🔐 Aucun verrou technique saisi.")
    if st.button("✨ Générer le verrou technique automatiquement"):
        if "index" not in st.session_state:
            st.error("❗ Veuillez d'abord générer les objets à partir des documents client.")
        else:
            st.info("📄 Le verrou sera généré uniquement à partir des documents client.")
            with st.spinner("🔎 Génération du verrou technique..."):
                verrou_genere = rag.generate_section_with_rag(
                    "Verrou technique",
                    rag.prompt_verrou(),
                    st.session_state["index"],
                    st.session_state["chunks"],
                    st.session_state["vectors"]
                )
                st.session_state["verrou_technique"] = verrou_genere
                st.success("✅ Verrou technique généré automatiquement.")
                st.text_area("🔐 Verrou généré :", verrou_genere, height=300)

# ──────────────────────────────
# ACTIONS FINALES
# ──────────────────────────────
is_ready = bool(projet_name and objectif)

if not is_ready:
    st.warning("🛑 Veuillez remplir les champs requis (nom du projet et objectif).")
else:
    col1, col2, col3 = st.columns(3)
    with col1:
        rechercher = st.button("🔍 Recherche article API")
    with col2:
        generer = st.button("✨ Générer le dossier CIR")
    with col3:
        prompt_search = st.button("🔎 Recherche article prompt")

    if rechercher:
        if "full_text" not in st.session_state:
            st.error("❗ Veuillez d'abord téléverser des documents client et générer les objets.")
        else:
            with st.spinner("📄 Analyse des documents..."):
                keywords_list = keywords.extract_keywords(st.session_state["full_text"])
                st.success("✅ Mots-clés : " + ", ".join(keywords_list))

                st.subheader("📚 Articles scientifiques suggérés")
                articles = crossref.search_articles_crossref(keywords_list)
                selected_articles = []

                for i, article in enumerate(articles):
                    checked = st.checkbox(f"{article['title']} ({article['year']}) — {article['authors']}", value=True, key=f"art_{i}")
                    if article.get("url"):
                        st.markdown(f"[🔗 Voir l'article]({article['url']})", unsafe_allow_html=True)
                    if checked:
                        article["selected"] = True
                        selected_articles.append(article)

                st.session_state["articles"] = selected_articles
                st.success("✅ Articles sélectionnés.")

    if generer:
        if "index" in st.session_state:
            verrou_final = st.session_state.get("verrou_technique", verrou_technique)
            with st.spinner("✍️ Rédaction des sections..."):
                sections = {
                    "Contexte de l’opération de R&D": rag.generate_contexte_section(
                        st.session_state["index"], st.session_state["chunks"], st.session_state["vectors"], objectif, verrou_final, annee),
                    "Indicateurs de R&D": rag.generate_indicateurs_section(
                        st.session_state["index"], st.session_state["chunks"], st.session_state["vectors"], objectif, verrou_final, annee),
                    "Objet de l’opération de R&D": rag.generate_objectifs_section(
                        st.session_state["index"], st.session_state["chunks"], st.session_state["vectors"], objectif, verrou_final, annee),
                    "Description de la démarche suivie et des travaux réalisés": rag.generate_travaux_section(
                        st.session_state["index"], st.session_state["chunks"], st.session_state["vectors"], objectif, verrou_final, annee),
                    "Contribution scientifique, technique ou technologique": rag.generate_contribution_section(
                        st.session_state["index"], st.session_state["chunks"], st.session_state["vectors"], objectif, verrou_final, annee),
                    "Partenariat scientifique et recherche confiée": rag.generate_partenariat_section(
                        st.session_state["index"], st.session_state["chunks"], st.session_state["vectors"], objectif, verrou_final, annee),
                    "État de l’art scientifique": writer.generer_etat_art(st.session_state.get("articles", [])),
                    "Verrou technique rencontré": verrou_final
                }

                output_path = f"./Doc/Dossier_CIR_{projet_name.replace(' ', '_')}.docx"
                writer.remplir_doc("./Doc/CLIENT_CIR.docx", output_path, sections)

                st.success("✅ Dossier généré avec succès !")
                with open(output_path, "rb") as f:
                    st.download_button("📥 Télécharger le dossier Word", f, file_name=os.path.basename(output_path))
        else:
            st.error("❗ Veuillez d'abord générer les objets à partir des documents client.")
