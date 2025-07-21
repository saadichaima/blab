# core/writer.py

from docx import Document

def generer_etat_art(articles):
    """Génère la section État de l’art scientifique à partir des articles sélectionnés"""
    refs = [
        f"- {a['title']} ({a['year']}) — {a['authors']} — {a['url']}"
        for a in articles if a.get("selected")
    ]
    return "## État de l’art scientifique\n\n" + ("\n".join(refs) if refs else "Aucun article retenu.")

def remplir_doc(template_path, output_path, sections):
    """Remplit un fichier Word basé sur une trame, en insérant le contenu IA sous les bons titres"""
    doc = Document(template_path)

    for i, para in enumerate(doc.paragraphs):
        titre = para.text.strip()
        if titre in sections:
            if i + 1 < len(doc.paragraphs):
                doc.paragraphs[i + 1].text = sections[titre]
            else:
                doc.add_paragraph(sections[titre])

    doc.save(output_path)
