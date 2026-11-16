import os
import sqlite3
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'partage_cours.db')
DOCX_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Liste_Eleves_Mots_de_Passe_Prof_Msalbi.docx')

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    tcPr.append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>'))

def set_cell_margins(cell, top=120, bottom=120, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def create_word_document():
    doc = docx.Document()

    # Page Margins
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # Styles
    navy = RGBColor(30, 58, 138)
    dark_gray = RGBColor(51, 65, 85)
    light_blue = RGBColor(37, 99, 235)

    # Header / Subtitle
    p_top = doc.add_paragraph()
    p_top.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_top = p_top.add_run("RÉPUBLIQUE TUNISIENNE — MINISTÈRE DE L'ÉDUCATION\nESPACE PÉDAGOGIQUE — PROFESSEUR MSALBI")
    run_top.font.name = 'Arial'
    run_top.font.size = Pt(9)
    run_top.font.bold = True
    run_top.font.color.rgb = RGBColor(100, 116, 139)

    # Main Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(8)
    p_title.paragraph_format.space_after = Pt(4)
    run_title = p_title.add_run("LISTE OFFICIELLE DES IDENTIFIANTS & MOTS DE PASSE")
    run_title.font.name = 'Arial'
    run_title.font.size = Pt(17)
    run_title.font.bold = True
    run_title.font.color.rgb = navy

    # Sub-Title
    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_after = Pt(16)
    run_sub = p_sub.add_run("Plateforme Web de Partage de Cours & Suivi d'Assiduité • Année Scolaire 2025-2026")
    run_sub.font.name = 'Arial'
    run_sub.font.size = Pt(10)
    run_sub.font.italic = True
    run_sub.font.color.rgb = light_blue

    # Notice Box (Admin note)
    p_box = doc.add_paragraph()
    p_box.paragraph_format.space_after = Pt(12)
    run_box = p_box.add_run("📌 DOCUMENT CONFIDENTIEL : ")
    run_box.bold = True
    run_box.font.color.rgb = RGBColor(180, 83, 9)
    run_box_text = p_box.add_run("Ce document récapitule les accès attribués aux élèves pour consulter les cours et les exercices sur la plateforme. Chaque élève doit conserver son identifiant et son mot de passe confidentiels.")
    run_box_text.font.size = Pt(9.5)
    run_box_text.font.color.rgb = dark_gray

    # Connect to DB to get students
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    students = cursor.execute('''
        SELECT full_name, username, classe, email 
        FROM users 
        WHERE role = 'student' 
        ORDER BY CASE WHEN classe = '2 IT' THEN 1 ELSE 2 END, full_name
    ''').fetchall()
    conn.close()

    # Section 1: Classe 2 IT
    students_2it = [s for s in students if s[2] == '2 IT']
    students_other = [s for s in students if s[2] != '2 IT']

    # Header Section 1
    h1 = doc.add_heading(level=2)
    h1.paragraph_format.space_before = Pt(10)
    h1.paragraph_format.space_after = Pt(6)
    run_h1 = h1.add_run(f"1. CLASSE : 2 IT ({len(students_2it)} Élèves — Fichier 'eleve 2 it.xlsx')")
    run_h1.font.name = 'Arial'
    run_h1.font.size = Pt(12)
    run_h1.font.bold = True
    run_h1.font.color.rgb = navy

    table = doc.add_table(rows=1, cols=5)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    # Column widths
    col_widths = [Inches(0.5), Inches(2.7), Inches(1.5), Inches(1.2), Inches(0.9)]
    headers = ["N°", "Nom & Prénom de l'Élève", "Identifiant (Login)", "Mot de passe", "Classe"]

    hdr_cells = table.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].width = col_widths[i]
        hdr_cells[i].text = title
        set_cell_background(hdr_cells[i], "1E3A8A") # Navy
        set_cell_margins(hdr_cells[i], top=120, bottom=120, left=100, right=100)
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in p.runs:
            r.font.name = 'Arial'
            r.font.bold = True
            r.font.size = Pt(9.5)
            r.font.color.rgb = RGBColor(255, 255, 255)

    for idx, s in enumerate(students_2it, start=1):
        row_cells = table.add_row().cells
        bg_color = "F8FAFC" if idx % 2 == 0 else "FFFFFF"

        values = [str(idx), s[0], s[1], "eleve123", s[2]]
        alignments = [
            WD_ALIGN_PARAGRAPH.CENTER,
            WD_ALIGN_PARAGRAPH.LEFT,
            WD_ALIGN_PARAGRAPH.LEFT,
            WD_ALIGN_PARAGRAPH.CENTER,
            WD_ALIGN_PARAGRAPH.CENTER
        ]

        for i, val in enumerate(values):
            row_cells[i].width = col_widths[i]
            row_cells[i].text = val
            set_cell_background(row_cells[i], bg_color)
            set_cell_margins(row_cells[i], top=80, bottom=80, left=100, right=100)
            p = row_cells[i].paragraphs[0]
            p.alignment = alignments[i]
            for r in p.runs:
                r.font.name = 'Arial'
                r.font.size = Pt(9)
                if i == 1:
                    r.font.bold = True
                    r.font.color.rgb = RGBColor(15, 23, 42)
                elif i == 2:
                    r.font.name = 'Consolas'
                    r.font.color.rgb = RGBColor(37, 99, 235)
                elif i == 3:
                    r.font.name = 'Consolas'
                    r.font.bold = True
                    r.font.color.rgb = RGBColor(16, 185, 129)
                else:
                    r.font.color.rgb = dark_gray

    # Section 2: Autres élèves
    if students_other:
        h2 = doc.add_heading(level=2)
        h2.paragraph_format.space_before = Pt(18)
        h2.paragraph_format.space_after = Pt(6)
        run_h2 = h2.add_run(f"2. AUTRES CLASSES ENREGISTRÉES ({len(students_other)} Élèves)")
        run_h2.font.name = 'Arial'
        run_h2.font.size = Pt(12)
        run_h2.font.bold = True
        run_h2.font.color.rgb = navy

        table2 = doc.add_table(rows=1, cols=5)
        table2.alignment = WD_TABLE_ALIGNMENT.CENTER
        table2.autofit = False

        hdr_cells2 = table2.rows[0].cells
        for i, title in enumerate(headers):
            hdr_cells2[i].width = col_widths[i]
            hdr_cells2[i].text = title
            set_cell_background(hdr_cells2[i], "334155") # Slate dark
            set_cell_margins(hdr_cells2[i], top=120, bottom=120, left=100, right=100)
            p = hdr_cells2[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for r in p.runs:
                r.font.name = 'Arial'
                r.font.bold = True
                r.font.size = Pt(9.5)
                r.font.color.rgb = RGBColor(255, 255, 255)

        for idx, s in enumerate(students_other, start=1):
            row_cells = table2.add_row().cells
            bg_color = "F8FAFC" if idx % 2 == 0 else "FFFFFF"

            values = [str(idx), s[0], s[1], "eleve123", s[2]]
            alignments = [
                WD_ALIGN_PARAGRAPH.CENTER,
                WD_ALIGN_PARAGRAPH.LEFT,
                WD_ALIGN_PARAGRAPH.LEFT,
                WD_ALIGN_PARAGRAPH.CENTER,
                WD_ALIGN_PARAGRAPH.CENTER
            ]

            for i, val in enumerate(values):
                row_cells[i].width = col_widths[i]
                row_cells[i].text = val
                set_cell_background(row_cells[i], bg_color)
                set_cell_margins(row_cells[i], top=80, bottom=80, left=100, right=100)
                p = row_cells[i].paragraphs[0]
                p.alignment = alignments[i]
                for r in p.runs:
                    r.font.name = 'Arial'
                    r.font.size = Pt(9)
                    if i == 1:
                        r.font.bold = True
                    elif i == 2:
                        r.font.name = 'Consolas'
                        r.font.color.rgb = RGBColor(37, 99, 235)
                    elif i == 3:
                        r.font.name = 'Consolas'
                        r.font.bold = True
                        r.font.color.rgb = RGBColor(16, 185, 129)

    # Section 3: Accès Enseignant (Professeur Msalbi)
    doc.add_paragraph().paragraph_format.space_before = Pt(16)
    p_admin = doc.add_paragraph()
    r_admin_t = p_admin.add_run("🔑 COMPTE PROFESSEUR (ADMINISTRATEUR) :\n")
    r_admin_t.bold = True
    r_admin_t.font.size = Pt(11)
    r_admin_t.font.color.rgb = navy

    p_admin_details = doc.add_paragraph()
    p_admin_details.paragraph_format.left_indent = Inches(0.3)
    p_admin_details.add_run("• Nom complet : ").bold = True
    p_admin_details.add_run("Professeur Msalbi\n")
    p_admin_details.add_run("• Identifiant de connexion : ").bold = True
    p_admin_details.add_run("msalbi\n")
    p_admin_details.add_run("• Mot de passe administrateur : ").bold = True
    r_pwd = p_admin_details.add_run("msalbi123\n")
    r_pwd.bold = True
    r_pwd.font.color.rgb = RGBColor(220, 38, 38)
    p_admin_details.add_run("• Adresse du site web : ").bold = True
    p_admin_details.add_run("http://localhost:5050")

    # Footer note
    p_foot = doc.add_paragraph()
    p_foot.paragraph_format.space_before = Pt(18)
    p_foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_foot = p_foot.add_run("Espace Pédagogique Msalbi — Document généré automatiquement pour le Professeur Msalbi.")
    r_foot.font.name = 'Arial'
    r_foot.font.size = Pt(8.5)
    r_foot.font.italic = True
    r_foot.font.color.rgb = RGBColor(148, 163, 184)

    try:
        doc.save(DOCX_PATH)
        print(f"[OK] Fichier Word créé avec succès : {DOCX_PATH}")
    except PermissionError:
        alt_path = DOCX_PATH.replace('.docx', '_new.docx')
        try:
            doc.save(alt_path)
            print(f"[NOTE] Le fichier original est ouvert dans Word. Sauvegardé sous : {alt_path}")
        except Exception as e:
            print("[WARN] Impossible de sauvegarder Word :", e)

if __name__ == '__main__':
    create_word_document()
