import streamlit as st
from Core import document, keywords, embeddings, rag, crossref, writer
import os

# ──────────────────────────────
# CONFIGURATION
# ──────────────────────────────
st.set_page_config(page_title="Assistant CIR", page_icon="🧾")
st.title("🧠 Assistant CIR")

col_societe, col_projet, col_annee = st.columns([1, 1, 1])
with col_projet:
    projet_name = st.text_input("📝 Nom du projet *")
with col_annee:
    annee = st.number_input("📅 Année *", min_value=2000, max_value=2100, value=2025, step=1, format="%d")
with col_societe:
    societe = st.text_input("📝 Societé")
objectif = st.text_area("🎯 Objectif du projet *", placeholder="Décrivez l’objectif du projet ici...")

# ──────────────────────────────
# TÉLÉVERSEMENT DE DOCUMENTS
# ──────────────────────────────
uploaded_files_client = st.file_uploader("📎 Téléversez les documents **client** (optionnel)", type=["pdf", "docx"], accept_multiple_files=True)
uploaded_files_admin = st.file_uploader("📁 Téléversez les documents **administratifs** (optionnel)", type=["pdf", "docx"], accept_multiple_files=True)

# ──────────────────────────────
# GÉNÉRATION DE LA SECTION OBJET
# ──────────────────────────────
if "articles" not in st.session_state:
    st.info("🔍 Astuce : Pour enrichir la section avec des publications scientifiques, effectuez d'abord une recherche d'articles.")

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

            full_text_admin = ""
            if uploaded_files_admin:
                for file in uploaded_files_admin:
                    full_text_admin += "\n" + document.extract_text(file)

            full_text_mix = full_text + "\n" + full_text_admin if full_text_admin else full_text
            chunks_mix = document.chunk_text(full_text_mix)
            index_mix, vectors_mix = embeddings.build_index(chunks_mix)

            st.session_state["full_text_mix"] = full_text_mix
            st.session_state["chunks_mix"] = chunks_mix
            st.session_state["index_mix"] = index_mix
            st.session_state["vectors_mix"] = vectors_mix
        with st.spinner("🧠 Génération de la section « Objet de l’opération de R&D »..."):
            verrou = st.session_state.get("verrou_technique", "")
            articles_selectionnes = st.session_state.get("articles", [])

            objet_genere = rag.generate_objectifs_section(
                index=index,
                chunks=chunks,
                vectors=vectors,
                objectif=objectif,
                verrou=verrou,
                annee=annee,
                societe=societe,
                articles=articles_selectionnes
            )

        st.success("✅ Section générée avec succès !")
        st.text_area("📄 Objet de l’opération de R&D :", objet_genere, height=300)

        # 🧠 Sauvegarde pour plus tard
        st.session_state["objet_genere"] = objet_genere
        st.session_state["objet_section"] = objet_genere




# ──────────────────────────────
# VERROU TECHNIQUE (optionnel)
# ──────────────────────────────
objet_section = st.session_state.get("objet_section", "")
objet_genere = st.session_state.get("objet_genere", "")

verrou_technique = st.session_state.get("verrou_technique", "")
verrou_technique = st.text_area("🔐 Verrou technique (optionnel)", value=verrou_technique, placeholder="Expliquez ici le verrou scientifique ou technique rencontré…")

if not verrou_technique.strip():
    st.warning("🔐 Aucun verrou technique saisi.")
    if st.button("✨ Générer le verrou technique automatiquement"):
        if "index" not in st.session_state:
            st.error("❗ Veuillez d'abord générer les objets à partir des documents client.")
        elif not objet_genere.strip():
            st.error("❗ Veuillez d'abord générer la section « Objet de l’opération de R&D ».")
        else:
            st.info("📄 Le verrou sera généré uniquement à partir des documents client.")
            with st.spinner("🔎 Génération du verrou technique..."):
                verrou_genere = rag.generate_section_with_rag(
                    "Verrou technique",
                    rag.prompt_verrou(objet_genere),
                    st.session_state["index"],
                    st.session_state["chunks"],
                    st.session_state["vectors"]
                )
                st.session_state["verrou_technique"] = verrou_genere
                objet_complet = objet_genere.strip() + "\n\n🔐 **Verrou technique rencontré :**\n" + verrou_genere.strip()
                st.session_state["objet_section"] = objet_complet
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
     if not objectif.strip():
        st.error("❗ Veuillez d'abord saisir l’objectif du projet.")
     else:
        with st.spinner("📄 Analyse des documents..."):
            keywords_list = keywords.extract_keywords(objectif)
            st.success("✅ Mots-clés : " + ", ".join(keywords_list))

            # Charger les articles suggérés une seule fois
            if "articles_suggested" not in st.session_state:
                st.session_state["articles_suggested"] = crossref.search_articles_crossref(keywords_list, annee_reference=annee)

        st.subheader("📚 Articles scientifiques suggérés")

        # Liste temporaire mise à jour
        updated_articles = []

        for i, article in enumerate(st.session_state["articles_suggested"]):
            key = f"article_select_{i}"

            # Utiliser la valeur précédente du checkbox (stockée dans article["selected"])
            default_checked = article.get("selected", True)
            checked = st.checkbox(
                f"{article['title']} ({article['year']}) — {article['authors']}",
                value=default_checked,
                key=key
            )

            # Affichage du lien
            if article.get("url"):
                st.markdown(f"[🔗 Voir l'article]({article['url']})", unsafe_allow_html=True)

            # Mettre à jour la sélection
            article["selected"] = checked
            updated_articles.append(article)

        # ✅ Mémorise tous les articles (cochés et décochés)
        st.session_state["articles_suggested"] = updated_articles

        # ✅ Garde uniquement les sélectionnés pour les parties : objectifs / biblio
        st.session_state["articles"] = [a for a in updated_articles if a["selected"]]

        st.success(f"✅ {len(st.session_state['articles'])} article(s) sélectionné(s).")

    
  

    if generer:
        if "index" in st.session_state:
            verrou_final = st.session_state.get("verrou_technique", verrou_technique)
            with st.spinner("✍️ Rédaction des sections..."):
                sections = {
                    "Contexte de l’opération de R&D": rag.generate_contexte_section(
                        st.session_state["index"], st.session_state["chunks"], st.session_state["vectors"], objectif, verrou_final, annee, societe),
                    "Indicateurs de R&D": rag.generate_indicateurs_section(
                        st.session_state["index_mix"], st.session_state["chunks_mix"], st.session_state["vectors_mix"], objectif, verrou_final, annee, societe),
                    "Objet de l’opération de R&D": st.session_state.get("objet_section", st.session_state.get("objet_genere", "")),
                    "Description de la démarche suivie et des travaux réalisés": rag.generate_travaux_section(
                        st.session_state["index"], st.session_state["chunks"], st.session_state["vectors"], objectif, verrou_final, annee, societe),
                    "Contribution scientifique, technique ou technologique": rag.generate_contribution_section(
                        st.session_state["index"], st.session_state["chunks"], st.session_state["vectors"], objectif, verrou_final, annee, societe),
                    "Références bibliographiques": rag.generate_biblio_section(
                        st.session_state["index"], st.session_state["chunks"], st.session_state["vectors"],
                        st.session_state.get("objet_section", ""),
                        st.session_state.get("articles", [])  # ✅ Passage des articles à la biblio
                    ),
                    "Partenariat scientifique et recherche confiée": rag.generate_partenariat_section(
                        st.session_state["index_mix"], st.session_state["chunks_mix"], st.session_state["vectors_mix"], objectif, verrou_final, annee, societe),
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
