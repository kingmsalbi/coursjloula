import os
import sqlite3
import shutil
from datetime import datetime, timedelta
import random
from werkzeug.security import generate_password_hash

IS_VERCEL = bool(os.environ.get('VERCEL'))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if IS_VERCEL:
    DB_PATH = '/tmp/partage_cours.db'
    ORIG_DB = os.path.join(BASE_DIR, 'partage_cours.db')
    synced = False
    try:
        from blob_sync import sync_from_blob
        synced = sync_from_blob(DB_PATH)
    except Exception as e:
        print("[Vercel Blob Init Error]", e)

    if not synced and not os.path.exists(DB_PATH) and os.path.exists(ORIG_DB):
        try:
            shutil.copy2(ORIG_DB, DB_PATH)
        except Exception as e:
            print("[Vercel DB Copy Error]", e)
    UPLOADS_DIR = '/tmp/uploads'
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    os.makedirs(os.path.join(UPLOADS_DIR, 'courses'), exist_ok=True)
    os.makedirs(os.path.join(UPLOADS_DIR, 'messages'), exist_ok=True)
    # Copy sample courses from static/uploads if needed
    src_courses = os.path.join(BASE_DIR, 'static', 'uploads', 'courses')
    dest_courses = os.path.join(UPLOADS_DIR, 'courses')
    if os.path.exists(src_courses):
        for f in os.listdir(src_courses):
            s_file = os.path.join(src_courses, f)
            d_file = os.path.join(dest_courses, f)
            if not os.path.exists(d_file) and os.path.isfile(s_file):
                try:
                    shutil.copy2(s_file, d_file)
                except Exception:
                    pass
else:
    DB_PATH = os.path.join(BASE_DIR, 'partage_cours.db')
    UPLOADS_DIR = os.path.join(BASE_DIR, 'static', 'uploads')
    
    # Restauration automatique depuis Supabase Storage si configuré
    try:
        from supabase_storage import download_file_from_supabase, get_supabase_config
        s_url, s_key, _ = get_supabase_config()
        if s_url and s_key:
            print("[CloudInit] Vérification de la base de données cloud sur Supabase...")
            download_file_from_supabase("database/partage_cours.db", DB_PATH)
    except Exception as e:
        print("[CloudInit Exception]", e)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    os.makedirs(os.path.join(UPLOADS_DIR, 'courses'), exist_ok=True)
    os.makedirs(os.path.join(UPLOADS_DIR, 'messages'), exist_ok=True)
    
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        email TEXT,
        role TEXT NOT NULL DEFAULT 'student', -- 'teacher' or 'student'
        classe TEXT DEFAULT 'Général',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_active_at DATETIME
    );

    CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        level TEXT DEFAULT 'Secondaire',
        description TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        subject TEXT NOT NULL,
        classe TEXT NOT NULL,
        chapter TEXT,
        description TEXT,
        content_html TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS course_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_size INTEGER DEFAULT 0,
        mime_type TEXT,
        blob_url TEXT,
        uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS student_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        session_token TEXT UNIQUE NOT NULL,
        ip_address TEXT,
        user_agent TEXT,
        started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_heartbeat DATETIME DEFAULT CURRENT_TIMESTAMP,
        duration_seconds INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS file_consultations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        file_id INTEGER REFERENCES course_files(id) ON DELETE CASCADE,
        course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
        file_name TEXT NOT NULL,
        action_type TEXT NOT NULL, -- 'VIEW' or 'DOWNLOAD'
        duration_seconds INTEGER DEFAULT 0,
        started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        ended_at DATETIME
    );

    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        action_type TEXT NOT NULL, -- 'LOGIN', 'LOGOUT', 'VIEW_COURSE', 'VIEW_FILE', 'DOWNLOAD_FILE', 'HEARTBEAT'
        description TEXT NOT NULL,
        target_type TEXT, -- 'course', 'file', 'auth'
        target_id INTEGER,
        extra_data TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        receiver_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        target_class TEXT, -- NULL pour messages directs; '2 IT', '2 ECO', '2 Lettre', 'Toutes les classes' pour diffusion
        message_type TEXT NOT NULL DEFAULT 'direct', -- 'direct' ou 'class_broadcast'
        content TEXT NOT NULL,
        file_path TEXT,
        file_name TEXT,
        file_size INTEGER,
        mime_type TEXT,
        blob_url TEXT,
        is_read INTEGER NOT NULL DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS message_reads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        read_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(message_id, user_id)
    );

    CREATE TABLE IF NOT EXISTS teacher_classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        class_name TEXT NOT NULL,
        assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(teacher_id, class_name)
    );

    CREATE INDEX IF NOT EXISTS idx_logs_user ON activity_logs(user_id);
    CREATE INDEX IF NOT EXISTS idx_logs_created ON activity_logs(created_at);
    CREATE INDEX IF NOT EXISTS idx_consult_user ON file_consultations(user_id);
    CREATE INDEX IF NOT EXISTS idx_consult_file ON file_consultations(file_id);
    CREATE INDEX IF NOT EXISTS idx_sessions_user ON student_sessions(user_id);
    CREATE INDEX IF NOT EXISTS idx_msg_sender ON messages(sender_id);
    CREATE INDEX IF NOT EXISTS idx_msg_receiver ON messages(receiver_id);
    CREATE INDEX IF NOT EXISTS idx_msg_target_class ON messages(target_class);
    CREATE INDEX IF NOT EXISTS idx_msg_created ON messages(created_at);
    CREATE INDEX IF NOT EXISTS idx_msg_reads_user ON message_reads(user_id);
    CREATE INDEX IF NOT EXISTS idx_teacher_classes_tid ON teacher_classes(teacher_id);
    ''')

    # Migration checks for columns
    u_cols = [c[1] for c in cursor.execute("PRAGMA table_info(users)").fetchall()]
    if 'is_admin' not in u_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
    cursor.execute("UPDATE users SET is_admin = 1 WHERE username = 'msalbi'")

    c_cols = [c[1] for c in cursor.execute("PRAGMA table_info(courses)").fetchall()]
    if 'author_id' not in c_cols:
        cursor.execute("ALTER TABLE courses ADD COLUMN author_id INTEGER")
    cursor.execute("UPDATE courses SET author_id = 1 WHERE author_id IS NULL")

    cf_cols = [c[1] for c in cursor.execute("PRAGMA table_info(course_files)").fetchall()]
    if 'blob_url' not in cf_cols:
        cursor.execute("ALTER TABLE course_files ADD COLUMN blob_url TEXT")

    m_cols = [c[1] for c in cursor.execute("PRAGMA table_info(messages)").fetchall()]
    if 'file_path' not in m_cols:
        cursor.execute("ALTER TABLE messages ADD COLUMN file_path TEXT")
    if 'file_name' not in m_cols:
        cursor.execute("ALTER TABLE messages ADD COLUMN file_name TEXT")
    if 'file_size' not in m_cols:
        cursor.execute("ALTER TABLE messages ADD COLUMN file_size INTEGER")
    if 'mime_type' not in m_cols:
        cursor.execute("ALTER TABLE messages ADD COLUMN mime_type TEXT")
    if 'blob_url' not in m_cols:
        cursor.execute("ALTER TABLE messages ADD COLUMN blob_url TEXT")

    conn.commit()
    conn.close()

    ensure_default_teachers()

def generate_sample_pdfs():
    """Generate realistic PDF sample courses using ReportLab"""
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    sample_files = [
        {
            "filename": "Math_Suites_Numeriques_Prof_Msalbi.pdf",
            "title": "Chapitre 1 : Suites Numériques & Limites",
            "subject": "Mathématiques - Classe Terminale",
            "sections": [
                ("1. Rappels & Définitions", "Une suite numérique (u_n) est une fonction définie de N (ou une partie de N) vers R. Elle est dite arithmétique de raison r si u_(n+1) = u_n + r. Elle est dite géométrique de raison q si u_(n+1) = q * u_n."),
                ("2. Théorème de Convergence", "Toute suite croissante et majorée est convergente. Toute suite décroissante et minorée est convergente. Si u_n <= v_n <= w_n et lim u_n = lim w_n = L, alors lim v_n = L (Théorème des Gendarmes)."),
                ("3. Exercices d'application", "Exercice 1 : Étudier la convergence de la suite définie par u_0 = 2 et u_(n+1) = sqrt(2 * u_n + 3). Montrer par récurrence que 1 <= u_n <= 3.")
            ]
        },
        {
            "filename": "Info_Algorithmes_Tri_Prof_Msalbi.pdf",
            "title": "Algorithmique : Tris & Complexité temporelle",
            "subject": "Informatique - Classe Terminale",
            "sections": [
                ("1. Notion de Complexité", "La complexité temporelle d'un algorithme mesure le nombre d'opérations élémentaires en fonction de la taille de l'entrée n. On note O(1) pour temps constant, O(n) pour linéaire, O(n log n) pour quasi-linéaire et O(n^2) pour quadratique."),
                ("2. Tri par Sélection vs Tri Fusion", "Le tri à bulles et le tri par sélection possèdent une complexité dans le pire des cas de O(n^2). Le tri fusion (Merge Sort) utilise le principe 'Diviser pour Régner' et atteint une complexité optimale de O(n log n)."),
                ("3. Travaux Pratiques", "Implémenter en Python la fonction tri_fusion(liste) et mesurer le temps d'exécution sur un tableau aléatoire de 10 000 entiers.")
            ]
        },
        {
            "filename": "Physique_Mecanique_Newton_Prof_Msalbi.pdf",
            "title": "Mécanique Classique : Lois de Newton & Énergie",
            "subject": "Sciences Physiques - Terminale",
            "sections": [
                ("1. La Deuxième Loi de Newton", "Dans un référentiel galiléen, la somme vectorielle des forces extérieures appliquées à un point matériel est égale au produit de sa masse par son vecteur accélération : Somme(F) = m * a."),
                ("2. Théorème de l'Énergie Cinétique", "La variation de l'énergie cinétique d'un solide entre deux instants t1 et t2 est égale à la somme des travaux de toutes les forces extérieures appliquées entre ces deux instants : Delta(Ec) = Somme(W_F)."),
                ("3. Exercice Type Bac", "Un projectile de masse m = 0.5 kg est lancé avec une vitesse initiale v0 faisant un angle alpha = 45° avec l'horizontale. Établir l'équation de la trajectoire y(x).")
            ]
        },
        {
            "filename": "Python_Bases_Prof_Msalbi.pdf",
            "title": "Bases de Python : Variables, Boucles & Fonctions",
            "subject": "Informatique - 1ère Année",
            "sections": [
                ("1. Variables et Types de Données", "Python est un langage à typage dynamique fort. Principaux types : int, float, str, bool, list, dict, tuple."),
                ("2. Structures de Contrôle", "Conditionnelles (if / elif / else), boucles définies (for i in range(n)) et boucles conditionnelles (while condition)."),
                ("3. Exercices Pratiques", "Écrire un script qui calcule le factoriel d'un entier n entré par l'utilisateur.")
            ]
        }
    ]

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1e3a8a'),
        alignment=1, # Center
        spaceAfter=15
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#475569'),
        alignment=1,
        spaceAfter=20
    )
    h2_style = ParagraphStyle(
        'DocH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#0f766e'),
        spaceBefore=14,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10.5,
        leading=15,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=8
    )
    footer_style = ParagraphStyle(
        'DocFooter',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor('#64748b'),
        alignment=1
    )

    generated_paths = {}
    for doc_info in sample_files:
        dest_path = os.path.join(UPLOADS_DIR, 'courses', doc_info['filename'])
        doc = SimpleDocTemplate(
            dest_path,
            pagesize=letter,
            rightMargin=45,
            leftMargin=45,
            topMargin=45,
            bottomMargin=45
        )
        story = []

        # Header Badge
        header_text = f"<b>ESPACE PÉDAGOGIQUE — PROF. MSALBI</b><br/>Année Scolaire 2025-2026 | Support de Cours Officiel"
        story.append(Paragraph(header_text, subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563eb'), spaceBefore=5, spaceAfter=15))

        # Title
        story.append(Paragraph(doc_info['title'], title_style))
        story.append(Paragraph(f"<b>Matière & Niveau :</b> {doc_info['subject']}", subtitle_style))
        story.append(Spacer(1, 10))

        # Sections
        for title, text in doc_info['sections']:
            story.append(Paragraph(title, h2_style))
            story.append(Paragraph(text, body_style))
            story.append(Spacer(1, 6))

        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor('#cbd5e1'), spaceBefore=10, spaceAfter=10))
        story.append(Paragraph("Ce document est réservé aux élèves autorisés par le Professeur Msalbi. Toute reproduction sans accord est interdite.", footer_style))

        doc.build(story)
        generated_paths[doc_info['filename']] = dest_path

    return generated_paths

def ensure_default_teachers():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Professeur Msalbi
    admin = cursor.execute("SELECT * FROM users WHERE username = 'msalbi'").fetchone()
    if not admin:
        cursor.execute('''
            INSERT INTO users (username, password_hash, full_name, email, role, classe, is_admin, created_at, last_active_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, datetime('now', '-30 days'), datetime('now'))
        ''', (
            'msalbi',
            generate_password_hash('msalbi123'),
            'Professeur Msalbi',
            'msalbi.prof@education.tn',
            'teacher',
            'Enseignant Principal'
        ))
    else:
        cursor.execute("UPDATE users SET is_admin = 1 WHERE username = 'msalbi'")

    # 2. Mme Jamila Rahmeni (Enseignante d'Anglais)
    jamila = cursor.execute("SELECT * FROM users WHERE username = 'jamila.rahmeni' OR username = 'jamila'").fetchone()
    if not jamila:
        cursor.execute('''
            INSERT INTO users (username, password_hash, full_name, email, role, classe, is_admin, created_at, last_active_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, datetime('now'), datetime('now'))
        ''', (
            'jamila.rahmeni',
            generate_password_hash('jamila123'),
            'Jamila Rahmeni',
            'jamila.rahmeni@education.tn',
            'teacher',
            "Enseignante d'Anglais"
        ))
        jamila = cursor.execute("SELECT * FROM users WHERE username = 'jamila.rahmeni'").fetchone()

    if jamila:
        j_id = jamila['id']
        assigned_cnt = cursor.execute("SELECT COUNT(*) AS c FROM teacher_classes WHERE teacher_id = ?", (j_id,)).fetchone()['c']
        if assigned_cnt == 0:
            cursor.execute("INSERT OR IGNORE INTO teacher_classes (teacher_id, class_name) VALUES (?, '2 IT'), (?, '2 ECO')", (j_id, j_id))

    conn.commit()
    conn.close()

def seed_database_if_empty():
    ensure_default_teachers()
    conn = get_db()
    cursor = conn.cursor()

    # Check if excel files exist in workspace and import them
    for x_file, c_name in [('eleve 2 it.xlsx', '2 IT'), ('eleve 2 eco.xlsx', '2 ECO'), ('eleve 2 lettre.xlsx', '2 Lettre')]:
        excel_path = os.path.join(BASE_DIR, x_file)
        if os.path.exists(excel_path):
            try:
                from import_excel_students import import_students_file
                import_students_file(excel_path, c_name)
            except Exception as e:
                print(f"[Database] Erreur import {x_file}:", e)

    conn.close()

if __name__ == '__main__':
    init_db()
    seed_database_if_empty()
