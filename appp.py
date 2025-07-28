import streamlit as st
from Core import document, keywords, embeddings, rag, crossref, writer
import os

# ──────────────────────────────
# CONFIGURATION GÉNÉRALE
# ──────────────────────────────
st.set_page_config(page_title="Assistant CIR", layout="wide")
st.title("🧠 Assistant CIR")

# ──────────────────────────────
# BARRE LATÉRALE
# ──────────────────────────────
st.sidebar.title("🛠 Paramètres")

projet_name = st.sidebar.text_input("📝 Nom du projet")
temperature = st.sidebar.slider("🎯 Température IA (créativité)", 0.0, 1.0, 0.4, 0.1)

st.sidebar.markdown("---")
st.sidebar.markdown("💡 *Assistant CIR utilisant GPT, FAISS et CrossRef.*")
st.sidebar.markdown("👨‍🔬 Développé pour aider à la génération semi-automatique de dossiers de Crédit d’Impôt Recherche.")

# ──────────────────────────────
# SAISIE DU VERROU TECHNIQUE
# ──────────────────────────────
verrou_technique = st.text_area("🔐 Décrivez le verrou technique du projet", placeholder="Expliquez ici le verrou scientifique ou technique rencontré dans le cadre du projet...")

# ──────────────────────────────
# TÉLÉVERSEMENT DE DOCUMENTS
# ──────────────────────────────
uploaded_files = st.file_uploader("📎 Téléversez les documents client", type=["pdf", "docx"], accept_multiple_files=True)

# ──────────────────────────────
# CONDITIONS REQUISES POUR LES ACTIONS
# ──────────────────────────────
is_ready = bool(projet_name and uploaded_files and verrou_technique)

if not is_ready:
    st.warning("🛑 Veuillez remplir tous les champs requis (nom du projet, verrou technique et documents) pour activer les actions.")
else:
    # Boutons côte à côte
    col1, col2,col3,col4 = st.columns(4)

    with col1:
        rechercher = st.button("🔍 Rechercher des articles scientifiques")
    with col2:
        generer = st.button("✨ Générer le dossier CIR")

    if rechercher:
        with st.spinner("📄 Lecture et indexation des documents..."):
            full_text = ""
            for file in uploaded_files:
                st.write(f"📄 Lecture : {file.name}")
                full_text += "\n" + document.extract_text(file)

            # Mots-clés
            st.subheader("🔑 Mots-clés extraits")
            keywords_list = keywords.extract_keywords(full_text)
            st.success("✅ Mots-clés : " + ", ".join(keywords_list))

            # Recherche d’articles
            st.subheader("📚 Articles scientifiques suggérés")
            articles = crossref.search_articles_crossref(keywords_list)
            selected_articles = []

            for i, article in enumerate(articles):
                title_line = f"{article['title']} ({article['year']}) — {article['authors']}"
                checked = st.checkbox(title_line, value=True, key=f"art_{i}")

                if article.get("url"):
                    st.markdown(f"[🔗 Voir l'article]({article['url']})", unsafe_allow_html=True)

                if checked:
                    article["selected"] = True
                    selected_articles.append(article)

            # Stockage temporaire dans la session
            st.session_state["full_text"] = full_text
            st.session_state["chunks"] = document.chunk_text(full_text)
            st.session_state["index"], st.session_state["vectors"] = embeddings.build_index(st.session_state["chunks"])
            st.session_state["articles"] = selected_articles
            st.success("✅ Documents analysés et articles récupérés.")

    if generer:
        if "index" in st.session_state:
            with st.spinner("✍️ Rédaction des sections..."):
                sections = {
                    "Contexte de l’opération de R&D": rag.generate_contexte_section(
                        st.session_state["index"], st.session_state["chunks"], st.session_state["vectors"]),
                    "Indicateurs de R&D": rag.generate_indicateurs_section(
                        st.session_state["index"], st.session_state["chunks"], st.session_state["vectors"]),
                    "Objet de l’opération de R&D": rag.generate_objectifs_section(
                        st.session_state["index"], st.session_state["chunks"], st.session_state["vectors"]),
                    "Description de la démarche suivie et des travaux réalisés": rag.generate_travaux_section(
                        st.session_state["index"], st.session_state["chunks"], st.session_state["vectors"]),
                    "Contribution scientifique, technique ou technologique": rag.generate_contribution_section(
                        st.session_state["index"], st.session_state["chunks"], st.session_state["vectors"]),
                    "Partenariat scientifique et recherche confiée": rag.generate_partenariat_section(
                        st.session_state["index"], st.session_state["chunks"], st.session_state["vectors"]),
                    "État de l’art scientifique": writer.generer_etat_art(st.session_state.get("articles", [])),
                    "Verrou technique rencontré": verrou_technique
                }

                output_path = f"./Doc/Dossier_CIR_{projet_name.replace(' ', '_')}.docx"
                writer.remplir_doc("./Doc/CLIENT_CIR.docx", output_path, sections)

                st.success("✅ Dossier généré avec succès !")
                with open(output_path, "rb") as f:
                    st.download_button("📥 Télécharger le dossier Word", f, file_name=os.path.basename(output_path))
        else:
            st.error("❗ Veuillez d'abord lancer la recherche d'articles avant de générer le dossier.")
