import os
import sqlite3
import uuid
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, request, jsonify, render_template, send_from_directory,
    session, redirect, url_for, send_file, Response
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

import time
from database import get_db, init_db, seed_database_if_empty, UPLOADS_DIR, DB_PATH

IS_VERCEL = bool(os.environ.get('VERCEL'))
_last_blob_sync_time = 0

import threading

def _run_background_sync():
    try:
        from blob_sync import sync_to_blob
        sync_to_blob(DB_PATH)
    except Exception as e:
        print("[CloudDB] Erreur synchronisation cloud:", e)

def notify_db_mutation():
    """Synchronise les changements de la base de données en arrière-plan sans bloquer la requête utilisateur."""
    t = threading.Thread(target=_run_background_sync, daemon=True)
    t.start()

from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__, static_folder='static', template_folder='templates')
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

@app.before_request
def check_cloud_db_sync():
    global _last_blob_sync_time
    if IS_VERCEL:
        # Ne jamais synchroniser sur les requêtes statiques ou les pings périodiques
        req_path = request.path or ''
        if req_path.startswith('/static') or req_path in ('/api/track/ping', '/api/messages/unread-count'):
            return

        now = time.time()
        # Rafraîchissement périodique avec cache serveur (toutes les 5 minutes au maximum)
        if now - _last_blob_sync_time > 300:
            _last_blob_sync_time = now
            try:
                from blob_sync import sync_from_blob
                sync_from_blob(DB_PATH)
            except Exception:
                pass
app.config['SECRET_KEY'] = 'msalbi_super_secret_cours_key_2025_education'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
if os.environ.get('VERCEL'):
    app.config['SESSION_COOKIE_SECURE'] = True
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB max file upload
app.config['UPLOAD_FOLDER'] = os.path.join(UPLOADS_DIR, 'courses')
MESSAGES_UPLOAD_FOLDER = os.path.join(UPLOADS_DIR, 'messages')
os.makedirs(MESSAGES_UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt', 'png', 'jpg', 'jpeg', 'zip'}

ALLOWED_MESSAGE_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt', 'rtf', 'csv', 'odt', 'ods', 'odp',
    'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp',
    'zip', 'rar', '7z', 'tar', 'gz',
    'mp3', 'wav', 'ogg', 'm4a', 'aac', 'mp4', 'webm',
    'py', 'sql', 'html', 'css', 'js', 'json', 'md'
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_message_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_MESSAGE_EXTENSIONS

# --- Dual-Authentication Helper (Session Cookie + Bearer Token) ---
def get_auth_user():
    # 1. Priorité au Bearer Token explicite dans l'en-tête Authorization ou paramètre URL
    token = None
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header.split(' ', 1)[1].strip()
    elif request.args.get('auth_token'):
        token = request.args.get('auth_token')

    if token:
        try:
            conn = get_db()
            sess = conn.execute(
                "SELECT ss.user_id, u.role FROM student_sessions ss JOIN users u ON ss.user_id = u.id WHERE ss.session_token = ? AND ss.is_active = 1",
                (token,)
            ).fetchone()
            conn.close()
            if sess:
                return sess['user_id'], sess['role']
        except Exception as e:
            print("[Token Auth Error]", e)

    # 2. Session Cookie Flask (Web UI)
    if 'user_id' in session:
        return session['user_id'], session.get('user_role')

    return None, None

# --- Security Decorators & Authorization Helpers ---
def is_user_admin(user_id):
    if not user_id:
        return False
    try:
        conn = get_db()
        u = conn.execute("SELECT id, username, is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        return bool(u and (u['username'] == 'msalbi' or (u['is_admin'] and u['is_admin'] == 1)))
    except Exception:
        return False

def get_teacher_classes(teacher_id):
    if not teacher_id:
        return []
    try:
        conn = get_db()
        u = conn.execute("SELECT id, username, role, is_admin FROM users WHERE id = ?", (teacher_id,)).fetchone()
        if not u or u['role'] != 'teacher':
            conn.close()
            return []
        if u['username'] == 'msalbi' or (u['is_admin'] and u['is_admin'] == 1):
            classes = conn.execute("SELECT name FROM classes ORDER BY id ASC").fetchall()
            conn.close()
            return [c['name'] for c in classes]
        rows = conn.execute("SELECT class_name FROM teacher_classes WHERE teacher_id = ? ORDER BY class_name ASC", (teacher_id,)).fetchall()
        conn.close()
        return [r['class_name'] for r in rows]
    except Exception:
        return []

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id, role = get_auth_user()
        if not user_id:
            return jsonify({'error': 'Authentification requise pour accéder à cette ressource'}), 401
        if 'user_id' not in session:
            session['user_id'] = user_id
            session['user_role'] = role
        return f(*args, **kwargs)
    return decorated_function

def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id, role = get_auth_user()
        if not user_id:
            return jsonify({'error': 'Authentification requise'}), 401
        if role != 'teacher':
            return jsonify({'error': 'Accès réservé aux enseignants'}), 403
        if 'user_id' not in session:
            session['user_id'] = user_id
            session['user_role'] = role
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id, role = get_auth_user()
        if not user_id:
            return jsonify({'error': 'Authentification requise'}), 401
        if role != 'teacher' or not is_user_admin(user_id):
            return jsonify({'error': "Accès réservé à l'administrateur principal (Professeur Msalbi)"}), 403
        if 'user_id' not in session:
            session['user_id'] = user_id
            session['user_role'] = role
        return f(*args, **kwargs)
    return decorated_function

# --- Health Check (pour Cloudflare, Render & Uptime Monitors) ---
@app.route('/health')
@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'coursjloula',
        'domain': 'coursjloula.tn',
        'timestamp': int(time.time())
    }), 200

# --- Frontend Single Page Shell ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    resp = send_from_directory(static_dir, filename)
    if filename.endswith('.js') or filename.endswith('.css'):
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
    return resp

@app.route('/download/apk')
@app.route('/app.apk')
def download_apk():
    apk_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'Espace_Pedagogique_Msalbi.apk')
    if os.path.exists(apk_path):
        return send_file(
            apk_path,
            as_attachment=True,
            download_name="Espace_Pedagogique_Msalbi.apk",
            mimetype="application/vnd.android.package-archive"
        )
    return jsonify({'error': 'APK non disponible'}), 404

@app.route('/api/public/classes', methods=['GET'])
def get_public_classes():
    conn = get_db()
    rows = conn.execute("SELECT id, name, level FROM classes ORDER BY id ASC").fetchall()
    classes_list = [dict(c) for c in rows]
    existing_names = {c['name'].strip().lower() for c in classes_list}

    # Inclut également automatiquement toute classe présente chez les élèves
    user_classes = conn.execute("""
        SELECT DISTINCT classe 
        FROM users 
        WHERE role = 'student' 
          AND classe IS NOT NULL 
          AND classe != '' 
          AND LOWER(classe) NOT IN ('sans classe', 'général', 'teacher', 'admin')
        ORDER BY classe ASC
    """).fetchall()

    for uc in user_classes:
        cname = (uc['classe'] or '').strip()
        if cname and cname.lower() not in existing_names:
            classes_list.append({'id': 999, 'name': cname, 'level': 'Secondaire'})
            existing_names.add(cname.lower())

    conn.close()
    return jsonify({'classes': classes_list})

@app.route('/api/public/students', methods=['GET'])
def get_public_students():
    classe = (request.args.get('classe') or '').strip()
    conn = get_db()
    if classe and classe.lower() not in ['teacher', 'enseignant', 'admin']:
        students = conn.execute(
            "SELECT id, username, full_name, classe FROM users WHERE role = 'student' AND LOWER(classe) = LOWER(?) ORDER BY full_name ASC",
            (classe,)
        ).fetchall()
    else:
        students = []
    conn.close()
    return jsonify({'students': [dict(s) for s in students]})

# --- Authentication Routes ---
@app.route('/api/auth/me', methods=['GET'])
def get_current_user():
    user_id, role = get_auth_user()
    if not user_id:
        return jsonify({'authenticated': False})
    
    conn = get_db()
    user = conn.execute(
        "SELECT id, username, full_name, email, role, classe, is_admin, last_active_at FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    conn.close()

    if not user:
        session.clear()
        return jsonify({'authenticated': False})

    token = session.get('session_token') or request.headers.get('Authorization', '').replace('Bearer ', '').strip()
    u_dict = dict(user)
    u_dict['is_admin'] = bool(u_dict['username'] == 'msalbi' or (u_dict.get('is_admin') and u_dict['is_admin'] == 1))
    if u_dict['role'] == 'teacher':
        u_dict['assigned_classes'] = get_teacher_classes(u_dict['id'])

    return jsonify({
        'authenticated': True,
        'user': u_dict,
        'session_token': token
    })

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    ident = (data.get('username') or '').strip()
    password = data.get('password') or ''
    remember_me = bool(data.get('remember_me'))

    if not ident or not password:
        return jsonify({'error': 'Veuillez saisir votre identifiant et votre mot de passe'}), 400

    conn = get_db()
    cursor = conn.cursor()

    # Smart matching: supports username, email, full French name, or Arabic name!
    ident_lower = ident.lower()
    user = None
    classe = (data.get('classe') or '').strip()
    is_student_class = bool(classe and classe.lower() not in ['teacher', 'enseignant', 'professeur msalbi', 'admin', 'auto'])

    # 1. Priorité absolue : recherche ciblée dans la classe sélectionnée (gère parfaitement les homonymes)
    if is_student_class:
        # 1a. Identifiant exact ou email dans la classe sélectionnée
        user = cursor.execute(
            "SELECT * FROM users WHERE (LOWER(username) = ? OR LOWER(email) = ?) AND LOWER(classe) = LOWER(?)",
            (ident_lower, ident_lower, classe)
        ).fetchone()

        # 1b. Préfixe d'identifiant dans la classe sélectionnée (ex: 'adam.chehibi' saisi, compte 'adam.chehibi.2it' dans cette classe)
        if not user:
            user = cursor.execute(
                "SELECT * FROM users WHERE (LOWER(username) LIKE ? OR LOWER(email) LIKE ?) AND LOWER(classe) = LOWER(?)",
                (f"{ident_lower}.%", f"{ident_lower}.%", classe)
            ).fetchone()

        # 1c. Recherche par nom complet ou arabe dans la classe sélectionnée
        if not user:
            clean = ident_lower.replace('prof.', '').replace('prof', '').strip()
            user = cursor.execute("""
                SELECT * FROM users 
                WHERE (LOWER(full_name) = ?
                   OR LOWER(full_name) LIKE ?
                   OR full_name LIKE ?
                   OR LOWER(username) LIKE ?)
                  AND LOWER(classe) = LOWER(?)
                LIMIT 1
            """, (clean, f"%{clean}%", f"%{ident}%", f"%{clean}%", classe)).fetchone()

    # 2. Match Enseignant spécifique (Msalbi ou Jamila Rahmeni) ou profil enseignant
    if not user:
        if 'msalbi' in ident_lower:
            user = cursor.execute("SELECT * FROM users WHERE username = 'msalbi'").fetchone()
        elif 'jamila' in ident_lower or 'rahmeni' in ident_lower:
            user = cursor.execute("SELECT * FROM users WHERE username IN ('jamila.rahmeni', 'jamila')").fetchone()
        elif classe and classe.lower() in ['teacher', 'enseignant', 'professeur msalbi', 'admin']:
            user = cursor.execute(
                "SELECT * FROM users WHERE role = 'teacher' AND (LOWER(username) = ? OR LOWER(email) = ? OR LOWER(full_name) LIKE ?)",
                (ident_lower, ident_lower, f"%{ident_lower}%")
            ).fetchone()
            if not user and not ident_lower:
                user = cursor.execute("SELECT * FROM users WHERE username = 'msalbi'").fetchone()

    # 3. Recherche globale exacte par nom d'utilisateur ou email
    if not user:
        user = cursor.execute(
            "SELECT * FROM users WHERE LOWER(username) = ? OR LOWER(email) = ?",
            (ident_lower, ident_lower)
        ).fetchone()

    # 4. Recherche globale par nom normalisé (Français ou Arabe)
    if not user:
        clean = ident_lower.replace('prof.', '').replace('prof', '').replace('mme.', '').replace('mme', '').strip()
        user = cursor.execute("""
            SELECT * FROM users 
            WHERE LOWER(full_name) = ?
               OR LOWER(full_name) LIKE ?
               OR full_name LIKE ?
               OR LOWER(username) LIKE ?
            LIMIT 1
        """, (clean, f"%{clean}%", f"%{ident}%", f"%{clean}%")).fetchone()

    if not user or not check_password_hash(user['password_hash'], password):
        if IS_VERCEL:
            try:
                from blob_sync import sync_from_blob
                if sync_from_blob(DB_PATH):
                    conn.close()
                    conn = get_db()
                    cursor = conn.cursor()
                    if is_student_class:
                        user = cursor.execute("SELECT * FROM users WHERE (LOWER(username) = ? OR LOWER(email) = ?) AND LOWER(classe) = LOWER(?)", (ident_lower, ident_lower, classe)).fetchone()
                    if not user and 'msalbi' in ident_lower:
                        user = cursor.execute("SELECT * FROM users WHERE username = 'msalbi'").fetchone()
                    if not user and ('jamila' in ident_lower or 'rahmeni' in ident_lower):
                        user = cursor.execute("SELECT * FROM users WHERE username IN ('jamila.rahmeni', 'jamila')").fetchone()
                    if not user and (classe and classe.lower() in ['teacher', 'enseignant', 'professeur msalbi']):
                        user = cursor.execute("SELECT * FROM users WHERE role = 'teacher' AND (LOWER(username) = ? OR LOWER(email) = ? OR LOWER(full_name) LIKE ?)", (ident_lower, ident_lower, f"%{ident_lower}%")).fetchone()
                    if not user:
                        user = cursor.execute("SELECT * FROM users WHERE LOWER(username) = ? OR LOWER(email) = ?", (ident_lower, ident_lower)).fetchone()
            except Exception:
                pass

    if not user or not check_password_hash(user['password_hash'], password):
        conn.close()
        return jsonify({'error': 'Identifiant ou mot de passe incorrect. Vérifiez vos identifiants ou cliquez sur l\'un des boutons d\'accès rapide ci-dessous.'}), 401

    # Verify class matching if a class was selected
    if is_student_class:
        if user['role'] == 'teacher':
            conn.close()
            return jsonify({
                'error': f"Vous avez sélectionné une classe d'élèves, mais ces identifiants correspondent au compte Enseignant ({user['full_name']}). Veuillez choisir 'Espace Enseignant'."
            }), 401
        elif user['classe'] and user['classe'].lower() != classe.lower():
            conn.close()
            return jsonify({
                'error': f"L'élève '{user['full_name']}' est inscrit dans la classe '{user['classe']}', et non dans '{classe}'."
            }), 401
    elif classe and classe.lower() in ['teacher', 'enseignant', 'professeur msalbi', 'admin']:
        if user['role'] != 'teacher':
            conn.close()
            return jsonify({
                'error': f"Le compte '{user['full_name']}' est un compte élève (Classe : {user['classe']}). Veuillez sélectionner sa classe pour vous connecter."
            }), 401

    session_token = str(uuid.uuid4())
    session.permanent = remember_me
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['user_role'] = user['role']
    session['full_name'] = user['full_name']
    session['session_token'] = session_token

    # Update last_active_at
    cursor.execute("UPDATE users SET last_active_at = CURRENT_TIMESTAMP WHERE id = ?", (user['id'],))

    # Register active session in student_sessions
    cursor.execute('''
        INSERT INTO student_sessions (user_id, session_token, ip_address, user_agent, started_at, last_heartbeat, duration_seconds, is_active)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0, 1)
    ''', (user['id'], session_token, request.remote_addr, request.headers.get('User-Agent', '')[:250]))

    cursor.execute('''
        INSERT INTO activity_logs (user_id, action_type, description, target_type)
        VALUES (?, 'LOGIN', ?, 'auth')
    ''', (user['id'], f"Connexion réussie : {user['full_name']} ({user['role']})"))

    conn.commit()
    conn.close()

    user_dict = {
        'id': user['id'],
        'username': user['username'],
        'full_name': user['full_name'],
        'email': user['email'],
        'role': user['role'],
        'classe': user['classe'],
        'is_admin': bool(user['username'] == 'msalbi' or (user['is_admin'] and user['is_admin'] == 1))
    }
    if user['role'] == 'teacher':
        user_dict['assigned_classes'] = get_teacher_classes(user['id'])

    return jsonify({
        'success': True,
        'message': f"Bienvenue, {user['full_name']} !",
        'user': user_dict,
        'session_token': session_token
    })

@app.route('/api/auth/change-password', methods=['POST'])
@login_required
def change_password():
    data = request.get_json() or {}
    old_password = data.get('old_password') or ''
    new_password = data.get('new_password') or ''
    confirm_password = data.get('confirm_password') or ''

    if not old_password or not new_password:
        return jsonify({'error': 'Veuillez saisir votre mot de passe actuel et votre nouveau mot de passe'}), 400

    if len(new_password) < 4:
        return jsonify({'error': 'Le nouveau mot de passe doit comporter au moins 4 caractères'}), 400

    if new_password != confirm_password:
        return jsonify({'error': 'La confirmation ne correspond pas au nouveau mot de passe'}), 400

    user_id, _ = get_auth_user()
    if not user_id:
        user_id = session.get('user_id')
    conn = get_db()
    cursor = conn.cursor()
    user = cursor.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,)).fetchone()

    if not user or not check_password_hash(user['password_hash'], old_password):
        conn.close()
        return jsonify({'error': 'Votre mot de passe actuel est incorrect'}), 400

    cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(new_password), user_id))
    
    cursor.execute('''
        INSERT INTO activity_logs (user_id, action_type, description, target_type)
        VALUES (?, 'CHANGE_PASSWORD', 'Modification du mot de passe personnel réussie', 'auth')
    ''', (user_id,))

    conn.commit()
    conn.close()

    notify_db_mutation()

    return jsonify({'success': True, 'message': 'Votre mot de passe a été modifié avec succès !'})

@app.route('/api/auth/register', methods=['POST'])
def register():
    return jsonify({
        'error': 'L\'inscription autonome des élèves est désactivée. Seul le Professeur Msalbi (Administrateur) peut inscrire des élèves ou importer des listes.'
    }), 403

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    user_id = session.get('user_id')
    session_token = session.get('session_token')

    if user_id and session.get('user_role') == 'student':
        conn = get_db()
        cursor = conn.cursor()
        if session_token:
            cursor.execute('''
                UPDATE student_sessions 
                SET is_active = 0, last_heartbeat = CURRENT_TIMESTAMP 
                WHERE session_token = ?
            ''', (session_token,))
        cursor.execute('''
            INSERT INTO activity_logs (user_id, action_type, description, target_type)
            VALUES (?, 'LOGOUT', 'Déconnexion du site', 'auth')
        ''', (user_id,))
        conn.commit()
        conn.close()

    session.clear()
    return jsonify({'success': True, 'message': 'Déconnexion effectuée avec succès'})

# --- Courses API ---
@app.route('/api/courses', methods=['GET'])
@login_required
def get_courses():
    classe_filter = request.args.get('classe')
    subject_filter = request.args.get('subject')
    search_q = request.args.get('q', '').strip()
    my_only = request.args.get('my_only') == '1'

    conn = get_db()
    cursor = conn.cursor()

    query = '''
        SELECT c.*, 
               COALESCE(u.full_name, 'Professeur Msalbi') AS author_name,
               u.role AS author_role,
               u.classe AS author_title,
               COUNT(cf.id) AS file_count
        FROM courses c
        LEFT JOIN users u ON c.author_id = u.id
        LEFT JOIN course_files cf ON c.id = cf.course_id
        WHERE 1=1
    '''
    params = []

    # Détection de l'utilisateur et de son rôle
    user_id, user_role = get_auth_user()
    is_admin = is_user_admin(user_id) if user_role == 'teacher' else False

    # Si élève, affiche les cours de sa classe OU les cours pour 'Toutes les classes'
    if user_role == 'student':
        student = cursor.execute("SELECT classe FROM users WHERE id = ?", (user_id,)).fetchone()
        student_class = (student['classe'] or '').strip() if student else ''
        query += """ AND (
            LOWER(TRIM(c.classe)) = LOWER(TRIM(?))
            OR LOWER(c.classe) LIKE '%toute%'
            OR LOWER(TRIM(c.classe)) = 'général'
            OR c.classe IS NULL 
            OR TRIM(c.classe) = ''
        )"""
        params.append(student_class)
    elif user_role == 'teacher':
        # Un enseignant non-admin ne gère et ne voit que ses propres cours
        if not is_admin:
            query += " AND c.author_id = ?"
            params.append(user_id)
        elif my_only:
            query += " AND c.author_id = ?"
            params.append(user_id)

    if classe_filter and classe_filter != 'all':
        query += " AND (LOWER(TRIM(c.classe)) = LOWER(TRIM(?)) OR LOWER(c.classe) LIKE '%toute%')"
        params.append(classe_filter)

    if subject_filter and subject_filter != 'all':
        query += " AND LOWER(TRIM(c.subject)) = LOWER(TRIM(?))"
        params.append(subject_filter)

    if search_q:
        query += " AND (c.title LIKE ? OR c.description LIKE ? OR c.chapter LIKE ?)"
        term = f"%{search_q}%"
        params.extend([term, term, term])

    query += " GROUP BY c.id ORDER BY c.created_at DESC"

    courses = cursor.execute(query, params).fetchall()

    # Get distinct subjects and classes for filters
    subjects = [row['subject'] for row in cursor.execute("SELECT DISTINCT subject FROM courses ORDER BY subject").fetchall()]
    classes = [row['classe'] for row in cursor.execute("SELECT DISTINCT classe FROM courses ORDER BY classe").fetchall()]

    result = []
    for c in courses:
        cdict = dict(c)
        # Fetch files
        files = cursor.execute(
            "SELECT id, file_name, file_size, mime_type, uploaded_at FROM course_files WHERE course_id = ? ORDER BY id ASC",
            (c['id'],)
        ).fetchall()
        cdict['files'] = [dict(f) for f in files]
        result.append(cdict)

    conn.close()

    resp = jsonify({
        'courses': result,
        'subjects': subjects,
        'classes': classes
    })
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    return resp

@app.route('/api/courses/<int:course_id>', methods=['GET'])
@login_required
def get_course_detail(course_id):
    conn = get_db()
    cursor = conn.cursor()

    course = cursor.execute("""
        SELECT c.*, COALESCE(u.full_name, 'Professeur Msalbi') AS author_name 
        FROM courses c 
        LEFT JOIN users u ON c.author_id = u.id 
        WHERE c.id = ?
    """, (course_id,)).fetchone()
    if not course:
        conn.close()
        return jsonify({'error': 'Cours introuvable'}), 404

    files = cursor.execute(
        "SELECT id, file_name, file_size, mime_type, uploaded_at FROM course_files WHERE course_id = ? ORDER BY id ASC",
        (course_id,)
    ).fetchall()

    # Log view event for student
    if session.get('user_role') == 'student':
        cursor.execute('''
            INSERT INTO activity_logs (user_id, action_type, description, target_type, target_id)
            VALUES (?, 'VIEW_COURSE', ?, 'course', ?)
        ''', (session['user_id'], f"Consultation de la fiche cours : {course['title']}", course_id))
        conn.commit()

    conn.close()

    cdict = dict(course)
    cdict['files'] = [dict(f) for f in files]
    return jsonify(cdict)

@app.route('/api/courses', methods=['POST'])
@teacher_required
def create_course():
    user_id, user_role = get_auth_user()
    is_admin = is_user_admin(user_id)

    title = (request.form.get('title') or '').strip()
    subject = (request.form.get('subject') or '').strip()
    classe = (request.form.get('classe') or 'Toutes les classes').strip()
    chapter = (request.form.get('chapter') or '').strip()
    description = (request.form.get('description') or '').strip()
    content_html = (request.form.get('content_html') or '').strip()

    if not title or not subject:
        return jsonify({'error': 'Le titre et la matière sont obligatoires'}), 400

    # Un enseignant non-admin ne peut publier que dans ses classes assignées
    if not is_admin:
        assigned = get_teacher_classes(user_id)
        if classe not in assigned:
            return jsonify({
                'error': f"Vous ne pouvez publier des cours que pour vos classes assignées : {', '.join(assigned) if assigned else 'Aucune classe'}"
            }), 403

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO courses (title, subject, classe, chapter, description, content_html, author_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (title, subject, classe, chapter, description, content_html, user_id))
    course_id = cursor.lastrowid

    # Handle file uploads
    uploaded_files = request.files.getlist('files')
    saved_files = []
    for file in uploaded_files:
        if file and file.filename and allowed_file(file.filename):
            orig_name = secure_filename(file.filename)
            unique_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{orig_name}"
            dest_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
            file_bytes = file.read()
            with open(dest_path, 'wb') as f:
                f.write(file_bytes)
            fsize = len(file_bytes)
            mtype = file.content_type or 'application/octet-stream'

            # Persist to Vercel Blob (recupere l'URL directe permanente)
            blob_url = None
            try:
                from blob_sync import upload_course_file_to_blob
                blob_url = upload_course_file_to_blob(file_bytes, unique_name)
            except Exception as e:
                print("[UploadBlob] Error:", e)

            cursor.execute('''
                INSERT INTO course_files (course_id, file_name, file_path, file_size, mime_type, blob_url, uploaded_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (course_id, orig_name, f"courses/{unique_name}", fsize, mtype, blob_url))
            saved_files.append(orig_name)

    conn.commit()
    conn.close()

    notify_db_mutation()

    return jsonify({
        'success': True,
        'message': f"Cours '{title}' publié avec succès avec {len(saved_files)} fichier(s).",
        'course_id': course_id
    })

@app.route('/api/courses/<int:course_id>', methods=['PUT', 'POST'])
@teacher_required
def update_course(course_id):
    user_id, user_role = get_auth_user()
    is_admin = is_user_admin(user_id)

    if request.is_json:
        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        subject = (data.get('subject') or '').strip()
        classe = (data.get('classe') or 'Toutes les classes').strip()
        chapter = (data.get('chapter') or '').strip()
        description = (data.get('description') or '').strip()
        content_html = (data.get('content_html') or '').strip()
    else:
        title = (request.form.get('title') or '').strip()
        subject = (request.form.get('subject') or '').strip()
        classe = (request.form.get('classe') or 'Toutes les classes').strip()
        chapter = (request.form.get('chapter') or '').strip()
        description = (request.form.get('description') or '').strip()
        content_html = (request.form.get('content_html') or '').strip()

    if not title or not subject:
        return jsonify({'error': 'Titre et matière obligatoires'}), 400

    conn = get_db()
    cursor = conn.cursor()

    course = cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
    if not course:
        conn.close()
        return jsonify({'error': 'Cours introuvable'}), 404

    # Un enseignant non-admin ne peut modifier que ses propres cours
    if not is_admin and course['author_id'] != user_id:
        conn.close()
        return jsonify({'error': 'Action non autorisée. Vous ne pouvez modifier que vos propres cours.'}), 403

    if not is_admin:
        assigned = get_teacher_classes(user_id)
        if classe not in assigned:
            conn.close()
            return jsonify({'error': f"Vous n'êtes pas assigné(e) à la classe '{classe}'."}), 403

    cursor.execute('''
        UPDATE courses 
        SET title = ?, subject = ?, classe = ?, chapter = ?, description = ?, content_html = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (title, subject, classe, chapter, description, content_html, course_id))

    # Handle any added files
    uploaded_files = request.files.getlist('files') if 'files' in request.files else []
    for file in uploaded_files:
        if file and file.filename and allowed_file(file.filename):
            orig_name = secure_filename(file.filename)
            unique_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{orig_name}"
            dest_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
            file_bytes = file.read()
            with open(dest_path, 'wb') as f:
                f.write(file_bytes)
            fsize = len(file_bytes)
            mtype = file.content_type or 'application/octet-stream'

            blob_url = None
            try:
                from blob_sync import upload_course_file_to_blob
                blob_url = upload_course_file_to_blob(file_bytes, unique_name)
            except Exception:
                pass

            cursor.execute('''
                INSERT INTO course_files (course_id, file_name, file_path, file_size, mime_type, blob_url, uploaded_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (course_id, orig_name, f"courses/{unique_name}", fsize, mtype, blob_url))

    conn.commit()
    conn.close()

    notify_db_mutation()

    return jsonify({'success': True, 'message': 'Cours mis à jour avec succès'})

@app.route('/api/courses/<int:course_id>', methods=['DELETE'])
@teacher_required
def delete_course(course_id):
    user_id, user_role = get_auth_user()
    is_admin = is_user_admin(user_id)

    conn = get_db()
    cursor = conn.cursor()

    course = cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
    if not course:
        conn.close()
        return jsonify({'error': 'Cours introuvable'}), 404

    # Un enseignant non-admin ne peut supprimer que ses propres cours
    if not is_admin and course['author_id'] != user_id:
        conn.close()
        return jsonify({'error': 'Action non autorisée. Vous ne pouvez supprimer que vos propres cours.'}), 403

    # Find files to delete from disk
    files = cursor.execute("SELECT file_path FROM course_files WHERE course_id = ?", (course_id,)).fetchall()
    for f in files:
        fpath = os.path.join(UPLOADS_DIR, f['file_path'])
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
            except Exception:
                pass

    cursor.execute("DELETE FROM file_consultations WHERE course_id = ?", (course_id,))
    cursor.execute("DELETE FROM course_files WHERE course_id = ?", (course_id,))
    cursor.execute("DELETE FROM courses WHERE id = ?", (course_id,))
    conn.commit()
    conn.close()

    notify_db_mutation()

    return jsonify({'success': True, 'message': 'Cours supprimé avec succès'})

@app.route('/api/courses/<int:course_id>/upload', methods=['POST'])
@teacher_required
def upload_file_to_course(course_id):
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier transmis'}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'error': 'Nom de fichier invalide'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Format de fichier non supporté'}), 400

    orig_name = secure_filename(file.filename)
    unique_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{orig_name}"
    dest_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
    file.save(dest_path)
    fsize = os.path.getsize(dest_path)

    blob_url = None
    try:
        from blob_sync import upload_course_file_to_blob
        with open(dest_path, 'rb') as f:
            blob_url = upload_course_file_to_blob(f.read(), unique_name)
    except Exception:
        pass

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO course_files (course_id, file_name, file_path, file_size, mime_type, blob_url, uploaded_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (course_id, orig_name, f"courses/{unique_name}", fsize, file.content_type or 'application/octet-stream', blob_url))
    fid = cursor.lastrowid
    conn.commit()
    conn.close()

    notify_db_mutation()

    return jsonify({'success': True, 'file_id': fid, 'file_name': orig_name, 'file_size': fsize})

# --- File Access & Tracking Routes ---
@app.route('/api/files/<int:file_id>/view')
@login_required
def view_file(file_id):
    conn = get_db()
    cursor = conn.cursor()
    file_record = cursor.execute(
        "SELECT cf.*, c.title as course_title FROM course_files cf JOIN courses c ON cf.course_id = c.id WHERE cf.id = ?",
        (file_id,)
    ).fetchone()

    if not file_record:
        conn.close()
        return jsonify({'error': 'Fichier introuvable'}), 404

    # Log consultation event if user is student
    consultation_id = None
    if session.get('user_role') == 'student':
        user_id = session['user_id']
        cursor.execute('''
            INSERT INTO file_consultations (user_id, file_id, course_id, file_name, action_type, duration_seconds, started_at)
            VALUES (?, ?, ?, ?, 'VIEW', 0, CURRENT_TIMESTAMP)
        ''', (user_id, file_id, file_record['course_id'], file_record['file_name']))
        consultation_id = cursor.lastrowid

        cursor.execute('''
            INSERT INTO activity_logs (user_id, action_type, description, target_type, target_id, extra_data)
            VALUES (?, 'VIEW_FILE', ?, 'file', ?, ?)
        ''', (user_id, f"Ouverture du document : {file_record['file_name']}", file_id, file_record['course_title']))
        conn.commit()

    conn.close()

    full_path = os.path.join(UPLOADS_DIR, file_record['file_path'])
    if not os.path.exists(full_path):
        try:
            from blob_sync import download_course_file_from_blob
            b_url = file_record['blob_url'] if 'blob_url' in file_record.keys() else None
            download_course_file_from_blob(file_record['file_path'], full_path, direct_blob_url=b_url)
        except Exception as e:
            print("[view_file] blob download err:", e)

    if not os.path.exists(full_path):
        return jsonify({'error': "Le fichier physique n'existe plus sur le serveur"}), 404

    ext = os.path.splitext(file_record['file_name'])[1].lower()

    # Word documents: render to clean responsive HTML directly in the iframe
    if ext in ('.docx', '.doc'):
        from document_viewer import render_docx
        html_content = render_docx(full_path, file_record['file_name'])
        return Response(html_content, mimetype='text/html; charset=utf-8')

    # Images
    if ext in ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'):
        return send_file(
            full_path,
            mimetype=file_record['mime_type'] or 'image/jpeg',
            as_attachment=False,
            download_name=file_record['file_name']
        )

    # PowerPoint / Excel fallback with styled preview and direct download action
    if ext in ('.ppt', '.pptx', '.xls', '.xlsx'):
        from document_viewer import render_office_fallback
        auth_param = f"?auth_token={request.args.get('auth_token')}" if request.args.get('auth_token') else ""
        download_url = f"/api/files/{file_id}/download{auth_param}"
        html_content = render_office_fallback(file_record['file_name'], download_url)
        return Response(html_content, mimetype='text/html; charset=utf-8')

    # PDF documents: render via mobile-first HTML5 viewer with touch scroll & zoom
    if ext == '.pdf':
        if request.args.get('raw') == '1':
            return send_file(
                full_path,
                mimetype='application/pdf',
                as_attachment=False,
                download_name=file_record['file_name']
            )
        from document_viewer import render_pdf_viewer
        auth_param = f"&auth_token={request.args.get('auth_token')}" if request.args.get('auth_token') else ""
        raw_pdf_url = f"/api/files/{file_id}/view?raw=1{auth_param}"
        download_url = f"/api/files/{file_id}/download{auth_param.replace('&', '?', 1)}"
        html_content = render_pdf_viewer(raw_pdf_url, file_record['file_name'], download_url)
        return Response(html_content, mimetype='text/html; charset=utf-8')

    # Default inline display
    return send_file(
        full_path,
        mimetype=file_record['mime_type'] or 'application/octet-stream',
        as_attachment=False,
        download_name=file_record['file_name']
    )

@app.route('/api/files/<int:file_id>/download')
@login_required
def download_file(file_id):
    conn = get_db()
    cursor = conn.cursor()
    file_record = cursor.execute(
        "SELECT cf.*, c.title as course_title FROM course_files cf JOIN courses c ON cf.course_id = c.id WHERE cf.id = ?",
        (file_id,)
    ).fetchone()

    if not file_record:
        conn.close()
        return jsonify({'error': 'Fichier introuvable'}), 404

    if session.get('user_role') == 'student':
        user_id = session['user_id']
        cursor.execute('''
            INSERT INTO file_consultations (user_id, file_id, course_id, file_name, action_type, duration_seconds, started_at)
            VALUES (?, ?, ?, ?, 'DOWNLOAD', 0, CURRENT_TIMESTAMP)
        ''', (user_id, file_id, file_record['course_id'], file_record['file_name']))

        cursor.execute('''
            INSERT INTO activity_logs (user_id, action_type, description, target_type, target_id, extra_data)
            VALUES (?, 'DOWNLOAD_FILE', ?, 'file', ?, ?)
        ''', (user_id, f"Téléchargement du document : {file_record['file_name']}", file_id, file_record['course_title']))
        conn.commit()

    conn.close()

    full_path = os.path.join(UPLOADS_DIR, file_record['file_path'])
    if not os.path.exists(full_path):
        try:
            from blob_sync import download_course_file_from_blob
            b_url = file_record['blob_url'] if 'blob_url' in file_record.keys() else None
            download_course_file_from_blob(file_record['file_path'], full_path, direct_blob_url=b_url)
        except Exception as e:
            print("[download_file] blob download err:", e)

    if not os.path.exists(full_path):
        return jsonify({'error': 'Fichier physique introuvable'}), 404

    return send_file(
        full_path,
        as_attachment=True,
        download_name=file_record['file_name']
    )

# --- Active Presence & Heartbeat Tracking API ---
@app.route('/api/track/ping', methods=['POST'])
@login_required
def track_ping():
    """
    Heartbeat ping sent every 15s from client while tab is active.
    Increments total student study time and file reading duration.
    """
    if session.get('user_role') != 'student':
        return jsonify({'status': 'ignored_teacher'})

    data = request.get_json() or {}
    session_token = data.get('session_token') or session.get('session_token')
    active_seconds = int(data.get('active_seconds') or 15)
    file_id = data.get('file_id')

    # Guard against spoofed large heartbeat increments
    if active_seconds > 60:
        active_seconds = 15

    user_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor()

    # Update session active duration
    if session_token:
        cursor.execute('''
            UPDATE student_sessions
            SET duration_seconds = duration_seconds + ?,
                last_heartbeat = CURRENT_TIMESTAMP,
                is_active = 1
            WHERE session_token = ? AND user_id = ?
        ''', (active_seconds, session_token, user_id))

    # Update user's overall last_active_at
    cursor.execute("UPDATE users SET last_active_at = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))

    # If currently reading a file, increment its view duration in file_consultations
    if file_id:
        # Find the latest open consultation for this file and user
        cursor.execute('''
            UPDATE file_consultations
            SET duration_seconds = duration_seconds + ?,
                ended_at = CURRENT_TIMESTAMP
            WHERE id = (
                SELECT id FROM file_consultations 
                WHERE user_id = ? AND file_id = ? AND action_type = 'VIEW'
                ORDER BY id DESC LIMIT 1
            )
        ''', (active_seconds, user_id, file_id))

    # Calculate student total time spent
    total_time = cursor.execute(
        "SELECT COALESCE(SUM(duration_seconds), 0) AS total FROM student_sessions WHERE user_id = ?",
        (user_id,)
    ).fetchone()['total']

    conn.commit()
    conn.close()

    return jsonify({
        'status': 'ok',
        'total_time_seconds': total_time
    })

@app.route('/api/track/file-start', methods=['POST'])
@login_required
def track_file_start():
    if session.get('user_role') != 'student':
        return jsonify({'status': 'ok'})

    data = request.get_json() or {}
    file_id = data.get('file_id')
    course_id = data.get('course_id')
    file_name = data.get('file_name', 'Fichier')

    if not file_id:
        return jsonify({'error': 'file_id requis'}), 400

    user_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO file_consultations (user_id, file_id, course_id, file_name, action_type, duration_seconds, started_at)
        VALUES (?, ?, ?, ?, 'VIEW', 0, CURRENT_TIMESTAMP)
    ''', (user_id, file_id, course_id, file_name))
    cid = cursor.lastrowid

    cursor.execute('''
        INSERT INTO activity_logs (user_id, action_type, description, target_type, target_id)
        VALUES (?, 'VIEW_FILE', ?, 'file', ?)
    ''', (user_id, f"Début de lecture : {file_name}", file_id))

    conn.commit()
    conn.close()

    return jsonify({'status': 'ok', 'consultation_id': cid})

# --- Teacher Dashboard & Tracking Analytics API ---
@app.route('/api/teacher/dashboard', methods=['GET'])
@teacher_required
def teacher_dashboard():
    user_id, role = get_auth_user()
    conn = get_db()
    cursor = conn.cursor()

    is_admin = is_user_admin(user_id)

    if is_admin:
        # 1. Global KPIs
        total_students = cursor.execute("SELECT COUNT(*) AS c FROM users WHERE role = 'student'").fetchone()['c']
        total_courses = cursor.execute("SELECT COUNT(*) AS c FROM courses").fetchone()['c']
        total_files = cursor.execute("SELECT COUNT(*) AS c FROM course_files").fetchone()['c']
        total_consultations = cursor.execute("SELECT COUNT(*) AS c FROM file_consultations WHERE action_type = 'VIEW'").fetchone()['c']
        total_downloads = cursor.execute("SELECT COUNT(*) AS c FROM file_consultations WHERE action_type = 'DOWNLOAD'").fetchone()['c']
        total_time_seconds = cursor.execute("SELECT COALESCE(SUM(duration_seconds), 0) AS s FROM student_sessions").fetchone()['s']

        # Online students (last heartbeat < 2 minutes)
        online_students = cursor.execute('''
            SELECT COUNT(DISTINCT user_id) AS c 
            FROM student_sessions 
            WHERE is_active = 1 AND datetime(last_heartbeat, '+2 minutes') >= datetime('now')
        ''').fetchone()['c']

        # 2. Top Most Active Students
        top_students = cursor.execute('''
            SELECT u.id, u.full_name, u.classe, u.username,
                   COALESCE(SUM(s.duration_seconds), 0) AS total_seconds,
                   (SELECT COUNT(*) FROM file_consultations fc WHERE fc.user_id = u.id) AS total_files_viewed,
                   u.last_active_at
            FROM users u
            LEFT JOIN student_sessions s ON u.id = s.user_id
            WHERE u.role = 'student'
            GROUP BY u.id
            ORDER BY total_seconds DESC
            LIMIT 5
        ''').fetchall()

        # 3. Top Most Viewed Files
        top_files = cursor.execute('''
            SELECT cf.id, cf.file_name, c.title AS course_title, c.subject,
                   COUNT(fc.id) AS view_count,
                   COALESCE(SUM(fc.duration_seconds), 0) AS total_reading_seconds
            FROM course_files cf
            JOIN courses c ON cf.course_id = c.id
            LEFT JOIN file_consultations fc ON cf.id = fc.file_id AND fc.action_type = 'VIEW'
            GROUP BY cf.id
            ORDER BY view_count DESC
            LIMIT 5
        ''').fetchall()

        # 4. Activity per day for the last 7 days (for chart)
        daily_stats = cursor.execute('''
            SELECT date(started_at) AS day,
                   COUNT(id) AS session_count,
                   COALESCE(SUM(duration_seconds), 0) / 60 AS duration_minutes
            FROM student_sessions
            WHERE date(started_at) >= date('now', '-6 days')
            GROUP BY date(started_at)
            ORDER BY date(started_at) ASC
        ''').fetchall()

        # 5. Recent global activity feed
        recent_activity = cursor.execute('''
            SELECT al.*, u.full_name, u.classe, u.username
            FROM activity_logs al
            JOIN users u ON al.user_id = u.id
            WHERE u.role = 'student'
            ORDER BY al.created_at DESC
            LIMIT 12
        ''').fetchall()
    else:
        # Enseignant régulier (non-admin) : Statistiques limitées à ses propres cours et ses classes assignées
        assigned = get_teacher_classes(user_id)
        placeholders = ','.join(['?'] * len(assigned)) if assigned else "''"

        if assigned:
            total_students = cursor.execute(f"SELECT COUNT(*) AS c FROM users WHERE role = 'student' AND classe IN ({placeholders})", assigned).fetchone()['c']
            online_students = cursor.execute(f'''
                SELECT COUNT(DISTINCT s.user_id) AS c 
                FROM student_sessions s
                JOIN users u ON s.user_id = u.id
                WHERE u.classe IN ({placeholders}) AND s.is_active = 1 AND datetime(s.last_heartbeat, '+2 minutes') >= datetime('now')
            ''', assigned).fetchone()['c']
            top_students = cursor.execute(f'''
                SELECT u.id, u.full_name, u.classe, u.username,
                       COALESCE(SUM(s.duration_seconds), 0) AS total_seconds,
                       (SELECT COUNT(*) FROM file_consultations fc JOIN courses cr ON fc.course_id = cr.id WHERE fc.user_id = u.id AND cr.author_id = ?) AS total_files_viewed,
                       u.last_active_at
                FROM users u
                LEFT JOIN student_sessions s ON u.id = s.user_id
                WHERE u.role = 'student' AND u.classe IN ({placeholders})
                GROUP BY u.id
                ORDER BY total_seconds DESC
                LIMIT 5
            ''', [user_id] + assigned).fetchall()
            recent_activity = cursor.execute(f'''
                SELECT al.*, u.full_name, u.classe, u.username
                FROM activity_logs al
                JOIN users u ON al.user_id = u.id
                WHERE u.role = 'student' AND u.classe IN ({placeholders})
                ORDER BY al.created_at DESC
                LIMIT 12
            ''', assigned).fetchall()
        else:
            total_students = 0
            online_students = 0
            top_students = []
            recent_activity = []

        total_courses = cursor.execute("SELECT COUNT(*) AS c FROM courses WHERE author_id = ?", (user_id,)).fetchone()['c']
        total_files = cursor.execute('''
            SELECT COUNT(cf.id) AS c 
            FROM course_files cf 
            JOIN courses c ON cf.course_id = c.id 
            WHERE c.author_id = ?
        ''', (user_id,)).fetchone()['c']
        total_consultations = cursor.execute('''
            SELECT COUNT(fc.id) AS c 
            FROM file_consultations fc 
            JOIN courses c ON fc.course_id = c.id 
            WHERE c.author_id = ? AND fc.action_type = 'VIEW'
        ''', (user_id,)).fetchone()['c']
        total_downloads = cursor.execute('''
            SELECT COUNT(fc.id) AS c 
            FROM file_consultations fc 
            JOIN courses c ON fc.course_id = c.id 
            WHERE c.author_id = ? AND fc.action_type = 'DOWNLOAD'
        ''', (user_id,)).fetchone()['c']
        total_time_seconds = cursor.execute('''
            SELECT COALESCE(SUM(fc.duration_seconds), 0) AS s 
            FROM file_consultations fc 
            JOIN courses c ON fc.course_id = c.id 
            WHERE c.author_id = ?
        ''', (user_id,)).fetchone()['s']

        top_files = cursor.execute('''
            SELECT cf.id, cf.file_name, c.title AS course_title, c.subject,
                   COUNT(fc.id) AS view_count,
                   COALESCE(SUM(fc.duration_seconds), 0) AS total_reading_seconds
            FROM course_files cf
            JOIN courses c ON cf.course_id = c.id
            LEFT JOIN file_consultations fc ON cf.id = fc.file_id AND fc.action_type = 'VIEW'
            WHERE c.author_id = ?
            GROUP BY cf.id
            ORDER BY view_count DESC
            LIMIT 5
        ''', (user_id,)).fetchall()

        daily_stats = cursor.execute('''
            SELECT date(fc.created_at) AS day,
                   COUNT(fc.id) AS session_count,
                   COALESCE(SUM(fc.duration_seconds), 0) / 60 AS duration_minutes
            FROM file_consultations fc
            JOIN courses c ON fc.course_id = c.id
            WHERE c.author_id = ? AND date(fc.created_at) >= date('now', '-6 days')
            GROUP BY date(fc.created_at)
            ORDER BY date(fc.created_at) ASC
        ''', (user_id,)).fetchall()

    conn.close()

    return jsonify({
        'kpi': {
            'total_students': total_students,
            'total_courses': total_courses,
            'total_files': total_files,
            'total_consultations': total_consultations,
            'total_downloads': total_downloads,
            'total_time_seconds': total_time_seconds,
            'online_students': online_students
        },
        'top_students': [dict(s) for s in top_students],
        'top_files': [dict(f) for f in top_files],
        'daily_stats': [dict(d) for d in daily_stats],
        'recent_activity': [dict(a) for a in recent_activity]
    })

@app.route('/api/teacher/students', methods=['GET'])
@teacher_required
def get_all_students_report():
    user_id, role = get_auth_user()
    conn = get_db()
    cursor = conn.cursor()

    is_admin = is_user_admin(user_id)
    where_classe = ""
    params = []
    if not is_admin:
        assigned = get_teacher_classes(user_id)
        if assigned:
            placeholders = ','.join(['?'] * len(assigned))
            where_classe = f" AND u.classe IN ({placeholders})"
            params = assigned
        else:
            conn.close()
            return jsonify({'students': []})

    query = f'''
        SELECT 
            u.id, u.username, u.full_name, u.email, u.classe, u.created_at, u.last_active_at,
            COALESCE(SUM(s.duration_seconds), 0) AS total_seconds,
            COUNT(DISTINCT s.id) AS total_sessions,
            (SELECT COUNT(*) FROM file_consultations fc WHERE fc.user_id = u.id AND fc.action_type = 'VIEW') AS views_count,
            (SELECT COUNT(*) FROM file_consultations fc WHERE fc.user_id = u.id AND fc.action_type = 'DOWNLOAD') AS downloads_count,
            CASE 
                WHEN EXISTS (
                    SELECT 1 FROM student_sessions ss 
                    WHERE ss.user_id = u.id AND ss.is_active = 1 
                      AND datetime(ss.last_heartbeat, '+2 minutes') >= datetime('now')
                ) THEN 1 
                ELSE 0 
            END AS is_online
        FROM users u
        LEFT JOIN student_sessions s ON u.id = s.user_id
        WHERE u.role = 'student'{where_classe}
        GROUP BY u.id
        ORDER BY total_seconds DESC, u.last_active_at DESC
    '''
    students = cursor.execute(query, params).fetchall()
    conn.close()
    return jsonify({'students': [dict(s) for s in students]})

# --- Teacher Classes Management Routes ---
@app.route('/api/teacher/my-classes', methods=['GET'])
@teacher_required
def get_my_classes():
    user_id, role = get_auth_user()
    assigned = get_teacher_classes(user_id)
    return jsonify({
        'classes': assigned,
        'is_admin': is_user_admin(user_id)
    })

@app.route('/api/admin/teacher-assignments', methods=['GET'])
@admin_required
def get_admin_teacher_assignments():
    conn = get_db()
    cursor = conn.cursor()
    all_classes = [c['name'] for c in cursor.execute("SELECT name FROM classes ORDER BY id ASC").fetchall()]
    teachers = cursor.execute("""
        SELECT id, username, full_name, email, classe, is_admin
        FROM users
        WHERE role = 'teacher'
        ORDER BY is_admin DESC, full_name ASC
    """).fetchall()

    result = []
    for t in teachers:
        tdict = dict(t)
        if tdict['is_admin'] == 1 or tdict['username'] == 'msalbi':
            tdict['assigned_classes'] = all_classes
        else:
            rows = cursor.execute("SELECT class_name FROM teacher_classes WHERE teacher_id = ? ORDER BY class_name ASC", (t['id'],)).fetchall()
            tdict['assigned_classes'] = [r['class_name'] for r in rows]
        result.append(tdict)

    conn.close()
    return jsonify({
        'all_classes': all_classes,
        'teachers': result
    })

@app.route('/api/admin/teacher-assignments/<int:teacher_id>', methods=['POST'])
@admin_required
def set_admin_teacher_assignments(teacher_id):
    data = request.get_json(silent=True) or {}
    classes_list = data.get('classes', [])
    if not isinstance(classes_list, list):
        return jsonify({'error': 'Format de données invalide'}), 400

    conn = get_db()
    cursor = conn.cursor()
    teacher = cursor.execute("SELECT id, full_name, username, is_admin FROM users WHERE id = ? AND role = 'teacher'", (teacher_id,)).fetchone()
    if not teacher:
        conn.close()
        return jsonify({'error': 'Enseignant introuvable'}), 404

    if teacher['is_admin'] == 1 or teacher['username'] == 'msalbi':
        conn.close()
        return jsonify({'error': "L'administrateur principal supervise automatiquement toutes les classes."}), 400

    valid_classes = [c['name'] for c in cursor.execute("SELECT name FROM classes").fetchall()]

    cursor.execute("DELETE FROM teacher_classes WHERE teacher_id = ?", (teacher_id,))
    added = []
    for cname in classes_list:
        if cname in valid_classes:
            cursor.execute("INSERT OR IGNORE INTO teacher_classes (teacher_id, class_name) VALUES (?, ?)", (teacher_id, cname))
            added.append(cname)

    conn.commit()
    conn.close()

    notify_db_mutation()

    return jsonify({
        'success': True,
        'message': f"Affectations de {teacher['full_name']} enregistrées ({len(added)} classe(s)).",
        'assigned_classes': added
    })

# --- Admin: Gestion Complète des Enseignants ---
@app.route('/api/admin/teachers', methods=['GET'])
@admin_required
def get_admin_teachers():
    conn = get_db()
    cursor = conn.cursor()
    all_classes = [c['name'] for c in cursor.execute("SELECT name FROM classes ORDER BY id ASC").fetchall()]
    teachers = cursor.execute("""
        SELECT id, username, full_name, email, classe, is_admin, created_at, last_active_at
        FROM users
        WHERE role = 'teacher'
        ORDER BY is_admin DESC, full_name ASC
    """).fetchall()

    result = []
    for t in teachers:
        tdict = dict(t)
        if tdict['is_admin'] == 1 or tdict['username'] == 'msalbi':
            tdict['assigned_classes'] = all_classes
        else:
            rows = cursor.execute("SELECT class_name FROM teacher_classes WHERE teacher_id = ? ORDER BY class_name ASC", (t['id'],)).fetchall()
            tdict['assigned_classes'] = [r['class_name'] for r in rows]
        result.append(tdict)

    conn.close()
    return jsonify({
        'teachers': result,
        'all_classes': all_classes
    })

@app.route('/api/admin/teachers', methods=['POST'])
@admin_required
def create_teacher():
    data = request.get_json(silent=True) or {}
    full_name = (data.get('full_name') or '').strip()
    username = (data.get('username') or '').strip().lower()
    password = (data.get('password') or '').strip()
    email = (data.get('email') or '').strip().lower()
    subject = (data.get('subject') or data.get('classe') or 'Professeur').strip()
    classes_list = data.get('classes', [])

    if not full_name or not username or not password:
        return jsonify({'error': 'Nom complet, identifiant et mot de passe sont obligatoires'}), 400

    if len(password) < 4:
        return jsonify({'error': 'Le mot de passe doit comporter au moins 4 caractères'}), 400

    conn = get_db()
    cursor = conn.cursor()

    existing = cursor.execute("SELECT id FROM users WHERE LOWER(TRIM(username)) = ?", (username,)).fetchone()
    if existing:
        conn.close()
        return jsonify({'error': f"L'identifiant '{username}' est déjà utilisé par un autre utilisateur."}), 400

    from werkzeug.security import generate_password_hash
    pwd_hash = generate_password_hash(password)

    cursor.execute('''
        INSERT INTO users (username, password_hash, full_name, email, role, classe, is_admin, created_at, last_active_at)
        VALUES (?, ?, ?, ?, 'teacher', ?, 0, CURRENT_TIMESTAMP, NULL)
    ''', (username, pwd_hash, full_name, email, subject))
    teacher_id = cursor.lastrowid

    valid_classes = [c['name'] for c in cursor.execute("SELECT name FROM classes").fetchall()]
    added_classes = []
    for cname in classes_list:
        if cname in valid_classes:
            cursor.execute("INSERT OR IGNORE INTO teacher_classes (teacher_id, class_name) VALUES (?, ?)", (teacher_id, cname))
            added_classes.append(cname)

    cursor.execute('''
        INSERT INTO activity_logs (user_id, action_type, description, target_type, target_id)
        VALUES (?, 'CREATE_TEACHER', ?, 'user', ?)
    ''', (session.get('user_id', 1), f"Création du compte enseignant : {full_name} ({username})", teacher_id))

    conn.commit()
    conn.close()

    notify_db_mutation()

    return jsonify({
        'success': True,
        'message': f"L'enseignant(e) '{full_name}' a été créé(e) avec succès avec {len(added_classes)} classe(s) assignée(s) !",
        'teacher_id': teacher_id
    })

@app.route('/api/admin/teachers/<int:teacher_id>', methods=['PUT', 'POST'])
@admin_required
def update_teacher(teacher_id):
    data = request.get_json(silent=True) or {}
    full_name = (data.get('full_name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    subject = (data.get('subject') or data.get('classe') or '').strip()
    password = (data.get('password') or '').strip()
    classes_list = data.get('classes')

    conn = get_db()
    cursor = conn.cursor()

    teacher = cursor.execute("SELECT id, full_name, username, is_admin FROM users WHERE id = ? AND role = 'teacher'", (teacher_id,)).fetchone()
    if not teacher:
        conn.close()
        return jsonify({'error': 'Enseignant introuvable'}), 404

    updates = []
    params = []
    if full_name:
        updates.append("full_name = ?")
        params.append(full_name)
    if email:
        updates.append("email = ?")
        params.append(email)
    if subject:
        updates.append("classe = ?")
        params.append(subject)
    if password:
        if len(password) < 4:
            conn.close()
            return jsonify({'error': 'Le mot de passe doit comporter au moins 4 caractères'}), 400
        from werkzeug.security import generate_password_hash
        updates.append("password_hash = ?")
        params.append(generate_password_hash(password))

    if updates:
        params.append(teacher_id)
        cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)

    if classes_list is not None and isinstance(classes_list, list) and not teacher['is_admin']:
        cursor.execute("DELETE FROM teacher_classes WHERE teacher_id = ?", (teacher_id,))
        valid_classes = [c['name'] for c in cursor.execute("SELECT name FROM classes").fetchall()]
        for cname in classes_list:
            if cname in valid_classes:
                cursor.execute("INSERT OR IGNORE INTO teacher_classes (teacher_id, class_name) VALUES (?, ?)", (teacher_id, cname))

    cursor.execute('''
        INSERT INTO activity_logs (user_id, action_type, description, target_type, target_id)
        VALUES (?, 'UPDATE_TEACHER', ?, 'user', ?)
    ''', (session.get('user_id', 1), f"Mise à jour du profil enseignant : {teacher['full_name']}", teacher_id))

    conn.commit()
    conn.close()

    notify_db_mutation()

    return jsonify({'success': True, 'message': f"Enseignant(e) '{teacher['full_name']}' mis à jour avec succès !"})

@app.route('/api/admin/teachers/<int:teacher_id>', methods=['DELETE'])
@admin_required
def delete_teacher(teacher_id):
    conn = get_db()
    cursor = conn.cursor()

    try:
        teacher = cursor.execute("SELECT id, full_name, username, is_admin FROM users WHERE id = ? AND role = 'teacher'", (teacher_id,)).fetchone()
        if not teacher:
            return jsonify({'error': 'Enseignant introuvable'}), 404

        if teacher['is_admin'] == 1 or teacher['username'] == 'msalbi':
            return jsonify({'error': "Impossible de supprimer l'administrateur principal (Professeur Msalbi)."}), 400

        admin_user_id, _ = get_auth_user()
        if not admin_user_id:
            admin_user_id = session.get('user_id', 1)

        # Journalisation avant suppression
        cursor.execute('''
            INSERT INTO activity_logs (user_id, action_type, description, target_type, target_id)
            VALUES (?, 'DELETE_TEACHER', ?, 'user', ?)
        ''', (admin_user_id, f"Suppression de l'enseignant : {teacher['full_name']} ({teacher['username']})", teacher_id))

        # Nettoyage des enregistrements liés
        cursor.execute("DELETE FROM teacher_classes WHERE teacher_id = ?", (teacher_id,))
        cursor.execute("DELETE FROM student_sessions WHERE user_id = ?", (teacher_id,))
        cursor.execute("DELETE FROM message_reads WHERE user_id = ?", (teacher_id,))
        cursor.execute("DELETE FROM messages WHERE sender_id = ? OR receiver_id = ?", (teacher_id, teacher_id))
        cursor.execute("DELETE FROM file_consultations WHERE user_id = ?", (teacher_id,))
        cursor.execute("DELETE FROM activity_logs WHERE user_id = ?", (teacher_id,))
        cursor.execute("DELETE FROM users WHERE id = ?", (teacher_id,))

        conn.commit()
    finally:
        conn.close()

    notify_db_mutation()

    return jsonify({'success': True, 'message': f"L'enseignant(e) {teacher['full_name']} a été supprimé(e) avec succès."})

@app.route('/api/admin/teachers/<int:teacher_id>/reset-password', methods=['POST'])
@admin_required
def reset_teacher_password(teacher_id):
    data = request.get_json(silent=True) or {}
    new_password = (data.get('new_password') or '').strip()
    if not new_password or len(new_password) < 4:
        return jsonify({'error': 'Le nouveau mot de passe doit comporter au moins 4 caractères'}), 400

    conn = get_db()
    cursor = conn.cursor()

    try:
        teacher = cursor.execute("SELECT id, full_name FROM users WHERE id = ? AND role = 'teacher'", (teacher_id,)).fetchone()
        if not teacher:
            return jsonify({'error': 'Enseignant introuvable'}), 404

        from werkzeug.security import generate_password_hash
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(new_password), teacher_id))

        admin_user_id, _ = get_auth_user()
        if not admin_user_id:
            admin_user_id = session.get('user_id', 1)

        cursor.execute('''
            INSERT INTO activity_logs (user_id, action_type, description, target_type, target_id)
            VALUES (?, 'RESET_PASSWORD', ?, 'user', ?)
        ''', (admin_user_id, f"Réinitialisation mot de passe de {teacher['full_name']}", teacher_id))

        conn.commit()
    finally:
        conn.close()

    notify_db_mutation()

    return jsonify({'success': True, 'message': f"Mot de passe de {teacher['full_name']} réinitialisé avec succès !"})

@app.route('/api/teacher/classes', methods=['GET'])
@teacher_required
def get_classes():
    user_id, role = get_auth_user()
    conn = get_db()
    cursor = conn.cursor()

    is_admin = is_user_admin(user_id)
    if is_admin:
        classes_records = cursor.execute("SELECT * FROM classes ORDER BY id ASC").fetchall()
    else:
        assigned = get_teacher_classes(user_id)
        if assigned:
            placeholders = ','.join(['?'] * len(assigned))
            classes_records = cursor.execute(f"SELECT * FROM classes WHERE name IN ({placeholders}) ORDER BY id ASC", assigned).fetchall()
        else:
            classes_records = []

    result = []
    for c in classes_records:
        cdict = dict(c)
        cname = c['name']
        
        # Count students
        s_count = cursor.execute("SELECT COUNT(*) AS c FROM users WHERE role = 'student' AND classe = ?", (cname,)).fetchone()['c']
        cdict['students_count'] = s_count

        # Count courses
        courses_count = cursor.execute("SELECT COUNT(*) AS c FROM courses WHERE classe = ? OR classe = 'Toutes les classes'", (cname,)).fetchone()['c']
        cdict['courses_count'] = courses_count

        # Total study time of students in this class
        total_time = cursor.execute('''
            SELECT COALESCE(SUM(ss.duration_seconds), 0) AS t
            FROM student_sessions ss
            JOIN users u ON ss.user_id = u.id
            WHERE u.role = 'student' AND u.classe = ?
        ''', (cname,)).fetchone()['t']
        cdict['total_time_seconds'] = total_time

        # Online students in this class
        online_count = cursor.execute('''
            SELECT COUNT(DISTINCT u.id) AS c
            FROM users u
            JOIN student_sessions ss ON u.id = ss.user_id
            WHERE u.role = 'student' AND u.classe = ?
              AND ss.is_active = 1
              AND datetime(ss.last_heartbeat, '+2 minutes') >= datetime('now')
        ''', (cname,)).fetchone()['c']
        cdict['online_count'] = online_count

        result.append(cdict)

    conn.close()
    return jsonify({'classes': result, 'is_admin': is_admin})

@app.route('/api/teacher/classes', methods=['POST'])
@teacher_required
def create_class():
    user_id, role = get_auth_user()
    if not is_user_admin(user_id):
        return jsonify({'error': "Seul l'administrateur principal (Prof. Msalbi) peut créer des classes."}), 403

    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    level = (data.get('level') or 'Secondaire').strip()
    description = (data.get('description') or '').strip()

    if not name:
        return jsonify({'error': 'Le nom de la classe est obligatoire (ex: 2 IT, 3ème Math, etc.)'}), 400

    conn = get_db()
    cursor = conn.cursor()
    existing = cursor.execute("SELECT id FROM classes WHERE LOWER(name) = ?", (name.lower(),)).fetchone()
    if existing:
        conn.close()
        return jsonify({'error': f"La classe '{name}' existe déjà."}), 400

    cursor.execute('''
        INSERT INTO classes (name, level, description, created_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ''', (name, level, description))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    notify_db_mutation()

    return jsonify({'success': True, 'message': f"Classe '{name}' créée avec succès !", 'class_id': new_id})

@app.route('/api/teacher/classes/<int:class_id>', methods=['PUT'])
@teacher_required
def update_class(class_id):
    user_id, role = get_auth_user()
    if not is_user_admin(user_id):
        return jsonify({'error': "Seul l'administrateur principal (Prof. Msalbi) peut modifier des classes."}), 403

    data = request.get_json(silent=True) or {}
    new_name = (data.get('name') or '').strip()
    new_level = (data.get('level') or 'Secondaire').strip()
    new_description = (data.get('description') or '').strip()

    if not new_name:
        return jsonify({'error': 'Nom de classe obligatoire'}), 400

    conn = get_db()
    cursor = conn.cursor()
    old_class = cursor.execute("SELECT name FROM classes WHERE id = ?", (class_id,)).fetchone()
    if not old_class:
        conn.close()
        return jsonify({'error': 'Classe introuvable'}), 404

    old_name = old_class['name']

    if new_name.lower() != old_name.lower():
        existing = cursor.execute("SELECT id FROM classes WHERE LOWER(name) = ? AND id != ?", (new_name.lower(), class_id)).fetchone()
        if existing:
            conn.close()
            return jsonify({'error': 'Ce nom de classe est déjà attribué'}), 400

    cursor.execute('''
        UPDATE classes 
        SET name = ?, level = ?, description = ?
        WHERE id = ?
    ''', (new_name, new_level, new_description, class_id))

    if new_name != old_name:
        cursor.execute("UPDATE users SET classe = ? WHERE classe = ?", (new_name, old_name))
        cursor.execute("UPDATE courses SET classe = ? WHERE classe = ?", (new_name, old_name))

    conn.commit()
    conn.close()

    notify_db_mutation()

    return jsonify({'success': True, 'message': f"Classe '{new_name}' mise à jour avec succès."})

@app.route('/api/teacher/classes/<int:class_id>', methods=['DELETE'])
@teacher_required
def delete_class(class_id):
    user_id, role = get_auth_user()
    if not is_user_admin(user_id):
        return jsonify({'error': "Seul l'administrateur principal (Prof. Msalbi) peut supprimer des classes."}), 403

    conn = get_db()
    cursor = conn.cursor()

    cls = cursor.execute("SELECT name FROM classes WHERE id = ?", (class_id,)).fetchone()
    if not cls:
        conn.close()
        return jsonify({'error': 'Classe introuvable'}), 404

    cname = cls['name']
    cursor.execute("DELETE FROM classes WHERE id = ?", (class_id,))
    cursor.execute("UPDATE users SET classe = 'Général' WHERE classe = ?", (cname,))

    conn.commit()
    conn.close()

    notify_db_mutation()

    return jsonify({'success': True, 'message': f"Classe '{cname}' supprimée avec succès."})

@app.route('/api/teacher/classes/<int:class_id>/students', methods=['GET'])
@teacher_required
def get_class_students(class_id):
    conn = get_db()
    cursor = conn.cursor()

    cls = cursor.execute("SELECT * FROM classes WHERE id = ?", (class_id,)).fetchone()
    if not cls:
        conn.close()
        return jsonify({'error': 'Classe introuvable'}), 404

    cname = cls['name']
    students = cursor.execute('''
        SELECT 
            u.id, u.username, u.full_name, u.email, u.classe, u.created_at, u.last_active_at,
            COALESCE(SUM(s.duration_seconds), 0) AS total_seconds,
            COUNT(DISTINCT s.id) AS total_sessions,
            (SELECT COUNT(*) FROM file_consultations fc WHERE fc.user_id = u.id AND fc.action_type = 'VIEW') AS views_count,
            (SELECT COUNT(*) FROM file_consultations fc WHERE fc.user_id = u.id AND fc.action_type = 'DOWNLOAD') AS downloads_count,
            CASE 
                WHEN EXISTS (
                    SELECT 1 FROM student_sessions ss 
                    WHERE ss.user_id = u.id AND ss.is_active = 1 
                      AND datetime(ss.last_heartbeat, '+2 minutes') >= datetime('now')
                ) THEN 1 
                ELSE 0 
            END AS is_online
        FROM users u
        LEFT JOIN student_sessions s ON u.id = s.user_id
        WHERE u.role = 'student' AND u.classe = ?
        GROUP BY u.id
        ORDER BY total_seconds DESC, u.full_name ASC
    ''', (cname,)).fetchall()

    conn.close()
    return jsonify({
        'class': dict(cls),
        'students': [dict(s) for s in students]
    })

@app.route('/api/teacher/students/<int:student_id>', methods=['GET'])
@teacher_required
def get_student_dossier(student_id):
    """
    Detailed personal dossier for a student:
    - Overall profile and stats
    - Files consulted (with exact reading duration and download count)
    - Complete chronological timeline of actions
    - Login sessions breakdown
    """
    conn = get_db()
    cursor = conn.cursor()

    student = cursor.execute('''
        SELECT id, username, full_name, email, classe, created_at, last_active_at
        FROM users 
        WHERE id = ? AND role = 'student'
    ''', (student_id,)).fetchone()

    if not student:
        conn.close()
        return jsonify({'error': 'Élève introuvable'}), 404

    # Summary metrics
    total_time = cursor.execute(
        "SELECT COALESCE(SUM(duration_seconds), 0) AS t FROM student_sessions WHERE user_id = ?",
        (student_id,)
    ).fetchone()['t']

    total_sessions = cursor.execute(
        "SELECT COUNT(*) AS c FROM student_sessions WHERE user_id = ?",
        (student_id,)
    ).fetchone()['c']

    # Files consulted breakdown
    files_consulted = cursor.execute('''
        SELECT 
            fc.file_id, 
            fc.file_name,
            c.title AS course_title,
            c.subject,
            COUNT(CASE WHEN fc.action_type = 'VIEW' THEN 1 END) AS view_count,
            COUNT(CASE WHEN fc.action_type = 'DOWNLOAD' THEN 1 END) AS download_count,
            COALESCE(SUM(fc.duration_seconds), 0) AS total_reading_seconds,
            MAX(fc.started_at) AS last_consultation_at
        FROM file_consultations fc
        LEFT JOIN courses c ON fc.course_id = c.id
        WHERE fc.user_id = ?
        GROUP BY fc.file_id, fc.file_name
        ORDER BY total_reading_seconds DESC, view_count DESC
    ''', (student_id,)).fetchall()

    # Detailed chronological activity timeline (last 50 events)
    timeline = cursor.execute('''
        SELECT id, action_type, description, target_type, extra_data, created_at
        FROM activity_logs
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 60
    ''', (student_id,)).fetchall()

    # Sessions history
    sessions = cursor.execute('''
        SELECT id, started_at, last_heartbeat, duration_seconds, ip_address, is_active
        FROM student_sessions
        WHERE user_id = ?
        ORDER BY started_at DESC
        LIMIT 25
    ''', (student_id,)).fetchall()

    conn.close()

    return jsonify({
        'student': dict(student),
        'stats': {
            'total_time_seconds': total_time,
            'total_sessions': total_sessions,
            'files_count': len(files_consulted)
        },
        'files_consulted': [dict(f) for f in files_consulted],
        'timeline': [dict(t) for t in timeline],
        'sessions': [dict(s) for s in sessions]
    })

@app.route('/api/teacher/students/import-excel', methods=['POST'])
@teacher_required
def import_excel_endpoint():
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier Excel transmis'}), 400

    file = request.files['file']
    classe_name = (request.form.get('classe') or '2 IT').strip()

    if not file or not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'error': 'Veuillez transmettre un fichier au format .xlsx'}), 400

    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_import_{uuid.uuid4().hex}.xlsx")
    file.save(temp_path)

    try:
        from import_excel_students import extract_students_from_excel, arabic_to_latin, get_unique_username
        names = extract_students_from_excel(temp_path)

        conn = get_db()
        cursor = conn.cursor()

        # Ensure class exists in classes table
        c_exist = cursor.execute("SELECT id FROM classes WHERE LOWER(name) = LOWER(?)", (classe_name,)).fetchone()
        if not c_exist:
            cursor.execute("INSERT INTO classes (name, level, description) VALUES (?, 'Secondaire', ?)", 
                           (classe_name, f"Classe : {classe_name}"))

        imported = 0
        updated = 0

        for ar_name in names:
            fr_name, base_uname = arabic_to_latin(ar_name)
            full_display = f"{fr_name} ({ar_name})"

            final_uname, is_existing, existing_id = get_unique_username(base_uname, classe_name, cursor, allow_same_class_match=True)
            email = f"{final_uname}@eleve.tn"

            if not is_existing:
                cursor.execute('''
                    INSERT INTO users (username, password_hash, full_name, email, role, classe, created_at, last_active_at)
                    VALUES (?, ?, ?, ?, 'student', ?, CURRENT_TIMESTAMP, NULL)
                ''', (final_uname, generate_password_hash('eleve123'), full_display, email, classe_name))
                imported += 1
            else:
                cursor.execute('''
                    UPDATE users 
                    SET full_name = ?, email = ?, classe = ?
                    WHERE id = ?
                ''', (full_display, email, classe_name, existing_id))
                updated += 1

        conn.commit()
        conn.close()

        notify_db_mutation()

        if os.path.exists(temp_path):
            os.remove(temp_path)

        return jsonify({
            'success': True,
            'message': f"{len(names)} élèves traités avec succès dans la classe '{classe_name}' ({imported} nouveaux inscrits) !",
            'imported_count': imported,
            'total_students': len(names)
        })
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({'error': f"Erreur lors de la lecture du fichier Excel : {str(e)}"}), 500

@app.route('/api/teacher/students', methods=['POST'])
@teacher_required
def create_student():
    data = request.get_json() or {}
    raw_username = (data.get('username') or '').strip().lower()
    password = data.get('password') or 'eleve123'
    full_name = (data.get('full_name') or '').strip()
    email = (data.get('email') or '').strip()
    classe = (data.get('classe') or '2 IT').strip()

    if not raw_username or not full_name:
        return jsonify({'error': 'Nom complet et identifiant obligatoires'}), 400

    conn = get_db()
    cursor = conn.cursor()

    from import_excel_students import get_unique_username
    final_uname, is_existing, _ = get_unique_username(raw_username, classe, cursor, allow_same_class_match=False)
    if is_existing:
        conn.close()
        return jsonify({'error': f"Un élève possède déjà cet identifiant dans la classe '{classe}'."}), 400

    if not email:
        email = f"{final_uname}@eleve.tn"

    cursor.execute('''
        INSERT INTO users (username, password_hash, full_name, email, role, classe, created_at, last_active_at)
        VALUES (?, ?, ?, ?, 'student', ?, CURRENT_TIMESTAMP, NULL)
    ''', (final_uname, generate_password_hash(password), full_name, email, classe))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    notify_db_mutation()

    msg = f"Élève créé avec succès dans la classe '{classe}' !"
    if final_uname != raw_username:
        msg += f" (Identifiant attribué : '{final_uname}' pour éviter les doublons avec une autre classe)"

    return jsonify({
        'success': True,
        'message': msg,
        'student': {
            'id': new_id,
            'username': final_uname,
            'full_name': full_name,
            'email': email,
            'classe': classe
        }
    })

@app.route('/api/teacher/students/<int:student_id>/reset-password', methods=['POST'])
@teacher_required
def reset_student_password(student_id):
    data = request.get_json() or {}
    new_password = data.get('new_password') or 'eleve123'

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET password_hash = ? WHERE id = ? AND role = 'student'",
        (generate_password_hash(new_password), student_id)
    )
    conn.commit()
    conn.close()

    notify_db_mutation()

    return jsonify({'success': True, 'message': f"Mot de passe réinitialisé à '{new_password}'."})

@app.route('/api/teacher/students/<int:student_id>', methods=['DELETE'])
@teacher_required
def delete_student(student_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ? AND role = 'student'", (student_id,))
    conn.commit()
    conn.close()

    notify_db_mutation()

    return jsonify({'success': True, 'message': 'Compte élève supprimé avec succès'})

@app.route('/api/teacher/students/clear-all', methods=['POST'])
@teacher_required
def clear_all_students():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE role = 'student'")
    cursor.execute("DELETE FROM student_sessions WHERE user_id NOT IN (SELECT id FROM users WHERE role = 'teacher')")
    cursor.execute("DELETE FROM file_consultations WHERE user_id NOT IN (SELECT id FROM users WHERE role = 'teacher')")
    cursor.execute("DELETE FROM activity_logs WHERE user_id NOT IN (SELECT id FROM users WHERE role = 'teacher')")
    conn.commit()
    conn.close()

    notify_db_mutation()
    return jsonify({'success': True, 'message': 'Tous les comptes élèves ont été supprimés avec succès.'})

@app.route('/api/teacher/students/<int:student_id>/remove-from-class', methods=['POST'])
@teacher_required
def remove_student_from_class(student_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET classe = 'Sans classe' WHERE id = ? AND role = 'student'", (student_id,))
    conn.commit()
    conn.close()

    notify_db_mutation()
    return jsonify({'success': True, 'message': "L'élève a été retiré de la classe avec succès."})

@app.route('/api/teacher/students/<int:student_id>/change-class', methods=['POST'])
@teacher_required
def change_student_class(student_id):
    data = request.get_json(silent=True) or {}
    new_class = (data.get('classe') or 'Sans classe').strip()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET classe = ? WHERE id = ? AND role = 'student'", (new_class, student_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': f"L'élève a été affecté à la classe '{new_class}' avec succès."})

@app.route('/api/teacher/export/word')
@teacher_required
def export_word():
    docx_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Liste_Eleves_Mots_de_Passe_Prof_Msalbi.docx')
    try:
        from generer_word import create_word_document
        create_word_document()
    except Exception as e:
        print("Erreur refresh word:", e)
    return send_file(
        docx_path,
        as_attachment=True,
        download_name="Liste_Eleves_Mots_de_Passe_Prof_Msalbi.docx",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

@app.route('/api/teacher/export/csv')
@teacher_required
def export_csv_report():
    """Generates an instant downloadable CSV report of all students and their study time"""
    conn = get_db()
    cursor = conn.cursor()

    students = cursor.execute('''
        SELECT 
            u.id, u.full_name, u.username, u.email, u.classe, u.created_at, u.last_active_at,
            COALESCE(SUM(s.duration_seconds), 0) AS total_seconds,
            COUNT(DISTINCT s.id) AS total_sessions,
            (SELECT COUNT(*) FROM file_consultations fc WHERE fc.user_id = u.id AND fc.action_type = 'VIEW') AS views_count,
            (SELECT COUNT(*) FROM file_consultations fc WHERE fc.user_id = u.id AND fc.action_type = 'DOWNLOAD') AS downloads_count
        FROM users u
        LEFT JOIN student_sessions s ON u.id = s.user_id
        WHERE u.role = 'student'
        GROUP BY u.id
        ORDER BY total_seconds DESC
    ''').fetchall()

    conn.close()

    # Build CSV content with UTF-8 BOM for Microsoft Excel compatibility
    csv_rows = ["\ufeffIdentifiant;Nom Complet;Email;Classe;Temps Total (minutes);Temps Total (format);Sessions;Fichiers Consultes;Fichiers Telecharges;Derniere Activite"]
    for s in students:
        secs = s['total_seconds']
        mins = secs // 60
        formatted = f"{mins // 60}h {mins % 60}min" if mins >= 60 else f"{mins} min"
        csv_rows.append(
            f"{s['username']};{s['full_name']};{s['email'] or ''};{s['classe']};{mins};{formatted};{s['total_sessions']};{s['views_count']};{s['downloads_count']};{s['last_active_at'] or 'Jamais'}"
        )

    csv_data = "\n".join(csv_rows)
    return Response(
        csv_data,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-disposition": "attachment; filename=Rapport_Assiduite_Eleves_Prof_Msalbi.csv"}
    )

# ==========================================
# --- Messagerie & Échange de Messages ---
# ==========================================

@app.route('/api/messages/unread-count', methods=['GET'])
@login_required
def get_unread_messages_count():
    user_id, role = get_auth_user()
    conn = get_db()
    cursor = conn.cursor()

    me = cursor.execute("SELECT id, role, classe FROM users WHERE id = ?", (user_id,)).fetchone()
    if not me:
        conn.close()
        return jsonify({'unread_count': 0})

    # Messages directs non lus envoyés à cet utilisateur
    direct_unread = cursor.execute(
        "SELECT COUNT(*) AS c FROM messages WHERE receiver_id = ? AND is_read = 0",
        (user_id,)
    ).fetchone()['c']

    # Diffusions de classe non lues pour l'élève (venant des enseignants de sa classe)
    broadcast_unread = 0
    if me['role'] == 'student' and me['classe']:
        student_class = me['classe'].strip()
        teachers = cursor.execute("""
            SELECT id FROM users 
            WHERE role = 'teacher' AND (
                is_admin = 1 OR id IN (
                    SELECT teacher_id FROM teacher_classes 
                    WHERE LOWER(TRIM(class_name)) = LOWER(TRIM(?)) OR LOWER(class_name) LIKE '%toute%'
                )
            )
        """, (student_class,)).fetchall()
        teacher_ids = [t['id'] for t in teachers]

        if teacher_ids:
            placeholders = ','.join(['?'] * len(teacher_ids))
            broadcast_unread = cursor.execute(f'''
                SELECT COUNT(*) AS c 
                FROM messages 
                WHERE message_type = 'class_broadcast' 
                  AND (LOWER(TRIM(target_class)) = LOWER(TRIM(?)) OR target_class = 'Toutes les classes')
                  AND sender_id IN ({placeholders})
                  AND id NOT IN (SELECT message_id FROM message_reads WHERE user_id = ?)
            ''', [student_class] + teacher_ids + [user_id]).fetchone()['c']

    conn.close()
    return jsonify({
        'unread_count': direct_unread + broadcast_unread,
        'direct_unread': direct_unread,
        'broadcast_unread': broadcast_unread
    })


@app.route('/api/messages/conversations', methods=['GET'])
@login_required
def get_conversations():
    user_id, role = get_auth_user()
    conn = get_db()
    cursor = conn.cursor()

    me = cursor.execute("SELECT id, username, full_name, role, classe, is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
    if not me:
        conn.close()
        return jsonify({'error': 'Utilisateur introuvable'}), 404

    channels = []
    direct_chats = []

    if me['role'] == 'teacher':
        is_admin = is_user_admin(user_id)
        if is_admin:
            classes_rows = cursor.execute("SELECT name FROM classes ORDER BY id ASC").fetchall()
            class_names = ['Toutes les classes'] + [r['name'] for r in classes_rows]
        else:
            class_names = get_teacher_classes(user_id)

        # 1. Canaux de diffusion propres à cet enseignant pour ses classes assignées
        for cname in class_names:
            last_msg = cursor.execute('''
                SELECT m.content, m.file_name, m.created_at, u.full_name AS sender_name
                FROM messages m
                JOIN users u ON m.sender_id = u.id
                WHERE m.message_type = 'class_broadcast' 
                  AND (LOWER(TRIM(m.target_class)) = LOWER(TRIM(?)) OR m.target_class = ?)
                  AND m.sender_id = ?
                ORDER BY m.created_at DESC LIMIT 1
            ''', (cname, cname, user_id)).fetchone()

            last_prev = "Aucune annonce diffusée pour l'instant"
            if last_msg:
                last_prev = last_msg['content'] or (f"📎 {last_msg['file_name']}" if last_msg['file_name'] else "Pièce jointe")

            channels.append({
                'id': f"broadcast_{cname}_{user_id}",
                'type': 'class_broadcast',
                'target_class': cname,
                'teacher_id': user_id,
                'name': f"📢 Annonces : {cname}",
                'badge': 'Diffusion',
                'last_message': last_prev,
                'last_time': last_msg['created_at'] if last_msg else None,
                'unread': 0
            })

        # 2. Discussions directes pour les enseignants :
        # - Autres enseignants de l'établissement
        # - Élèves des classes assignées (ou tous les élèves pour l'administrateur)
        if is_admin:
            direct_rows = cursor.execute('''
                SELECT u.id, u.username, u.full_name, u.classe, u.role,
                       (SELECT CASE 
                                   WHEN m.content IS NOT NULL AND TRIM(m.content) != '' THEN m.content 
                                   WHEN m.file_name IS NOT NULL THEN '📎 ' || m.file_name 
                                   ELSE 'Pièce jointe' 
                               END 
                        FROM messages m 
                        WHERE (m.sender_id = u.id AND m.receiver_id = ?) OR (m.sender_id = ? AND m.receiver_id = u.id)
                        ORDER BY m.created_at DESC LIMIT 1) AS last_message,
                       (SELECT m.created_at FROM messages m 
                        WHERE (m.sender_id = u.id AND m.receiver_id = ?) OR (m.sender_id = ? AND m.receiver_id = u.id)
                        ORDER BY m.created_at DESC LIMIT 1) AS last_time,
                       (SELECT COUNT(*) FROM messages m 
                        WHERE m.sender_id = u.id AND m.receiver_id = ? AND m.is_read = 0) AS unread
                FROM users u
                WHERE u.id != ?
                ORDER BY unread DESC, CASE WHEN last_time IS NOT NULL THEN 0 ELSE 1 END, last_time DESC, u.role DESC, u.classe ASC, u.full_name ASC
            ''', (user_id, user_id, user_id, user_id, user_id, user_id)).fetchall()
        else:
            assigned = get_teacher_classes(user_id)
            placeholders = ','.join(['?'] * len(assigned)) if assigned else "''"
            params = [user_id, user_id, user_id, user_id, user_id, user_id]
            classe_clause = f"u.classe IN ({placeholders})" if assigned else "0=1"
            if assigned:
                params.extend(assigned)
            params.extend([user_id, user_id])

            direct_rows = cursor.execute(f'''
                SELECT u.id, u.username, u.full_name, u.classe, u.role,
                       (SELECT CASE 
                                   WHEN m.content IS NOT NULL AND TRIM(m.content) != '' THEN m.content 
                                   WHEN m.file_name IS NOT NULL THEN '📎 ' || m.file_name 
                                   ELSE 'Pièce jointe' 
                               END 
                        FROM messages m 
                        WHERE (m.sender_id = u.id AND m.receiver_id = ?) OR (m.sender_id = ? AND m.receiver_id = u.id)
                        ORDER BY m.created_at DESC LIMIT 1) AS last_message,
                       (SELECT m.created_at FROM messages m 
                        WHERE (m.sender_id = u.id AND m.receiver_id = ?) OR (m.sender_id = ? AND m.receiver_id = u.id)
                        ORDER BY m.created_at DESC LIMIT 1) AS last_time,
                       (SELECT COUNT(*) FROM messages m 
                        WHERE m.sender_id = u.id AND m.receiver_id = ? AND m.is_read = 0) AS unread
                FROM users u
                WHERE u.id != ? AND (
                    u.role = 'teacher'
                    OR {classe_clause}
                    OR EXISTS (SELECT 1 FROM messages m WHERE (m.sender_id = u.id AND m.receiver_id = ?) OR (m.sender_id = ? AND m.receiver_id = u.id))
                )
                ORDER BY unread DESC, CASE WHEN last_time IS NOT NULL THEN 0 ELSE 1 END, last_time DESC, u.role DESC, u.classe ASC, u.full_name ASC
            ''', params).fetchall()

        for d in direct_rows:
            is_teacher = d['role'] == 'teacher'
            badge = 'Professeur' if is_teacher else (d['classe'] or 'Élève')
            icon = "👨‍🏫" if is_teacher else "👤"
            if is_teacher and "jamila" in d['username'].lower():
                icon = "👩‍🏫"

            direct_chats.append({
                'id': f"direct_{d['id']}",
                'type': 'direct',
                'with_user_id': d['id'],
                'name': f"{icon} {d['full_name']}" if is_teacher else d['full_name'],
                'classe': d['classe'],
                'badge': badge,
                'is_teacher': is_teacher,
                'last_message': d['last_message'] or ("Démarrer la discussion" if is_teacher else "Nouvelle discussion"),
                'last_time': d['last_time'],
                'unread': d['unread']
            })

    else:
        # Vue Élève
        student_classe = (me['classe'] or 'Général').strip()

        # Enseignants affectés à cette classe ou administrateur
        teachers = cursor.execute("""
            SELECT u.id, u.username, u.full_name, u.classe, u.is_admin
            FROM users u
            WHERE u.role = 'teacher' AND (
                u.is_admin = 1 OR EXISTS (
                    SELECT 1 FROM teacher_classes tc 
                    WHERE tc.teacher_id = u.id 
                      AND (LOWER(TRIM(tc.class_name)) = LOWER(TRIM(?)) OR LOWER(tc.class_name) LIKE '%toute%')
                )
            )
            ORDER BY u.id ASC
        """, (student_classe,)).fetchall()

        # 1. Canaux de diffusion par enseignant pour cette classe
        for teacher in teachers:
            last_broadcast = cursor.execute('''
                SELECT m.content, m.file_name, m.created_at, u.full_name AS sender_name
                FROM messages m
                JOIN users u ON m.sender_id = u.id
                WHERE m.message_type = 'class_broadcast' 
                  AND (LOWER(TRIM(m.target_class)) = LOWER(TRIM(?)) OR m.target_class = 'Toutes les classes')
                  AND m.sender_id = ?
                ORDER BY m.created_at DESC LIMIT 1
            ''', (student_classe, teacher['id'])).fetchone()

            unread_broadcast = cursor.execute('''
                SELECT COUNT(*) AS c 
                FROM messages 
                WHERE message_type = 'class_broadcast' 
                  AND (LOWER(TRIM(target_class)) = LOWER(TRIM(?)) OR target_class = 'Toutes les classes')
                  AND sender_id = ?
                  AND id NOT IN (SELECT message_id FROM message_reads WHERE user_id = ?)
            ''', (student_classe, teacher['id'], user_id)).fetchone()['c']

            last_b_text = "Aucune annonce récente"
            if last_broadcast:
                last_b_text = last_broadcast['content'] or (f"📎 {last_broadcast['file_name']}" if last_broadcast['file_name'] else "Pièce jointe")

            channels.append({
                'id': f"broadcast_{student_classe}_{teacher['id']}",
                'type': 'class_broadcast',
                'target_class': student_classe,
                'teacher_id': teacher['id'],
                'name': f"📢 Annonces {student_classe} — {teacher['full_name']}",
                'badge': 'Enseignant',
                'last_message': last_b_text,
                'last_time': last_broadcast['created_at'] if last_broadcast else None,
                'unread': unread_broadcast
            })

        # 2. Discussions privées avec les enseignants de la classe
        for teacher in teachers:
            last_t_msg = cursor.execute('''
                SELECT m.content, m.file_name, m.created_at
                FROM messages m
                WHERE (m.sender_id = ? AND m.receiver_id = ?) OR (m.sender_id = ? AND m.receiver_id = ?)
                ORDER BY m.created_at DESC LIMIT 1
            ''', (teacher['id'], user_id, user_id, teacher['id'])).fetchone()

            unread_t = cursor.execute('''
                SELECT COUNT(*) AS c FROM messages 
                WHERE sender_id = ? AND receiver_id = ? AND is_read = 0
            ''', (teacher['id'], user_id)).fetchone()['c']

            role_badge = teacher['classe'] if teacher['classe'] else 'Professeur'
            icon = "👩‍🏫" if "jamila" in teacher['username'].lower() else "👨‍🏫"

            last_t_text = f"Posez vos questions à {teacher['full_name']} ici..."
            if last_t_msg:
                last_t_text = last_t_msg['content'] or (f"📎 {last_t_msg['file_name']}" if last_t_msg['file_name'] else "Pièce jointe")

            direct_chats.append({
                'id': f"direct_{teacher['id']}",
                'type': 'direct',
                'with_user_id': teacher['id'],
                'name': f"{icon} {teacher['full_name']}",
                'classe': role_badge,
                'badge': 'Professeur',
                'is_teacher': True,
                'last_message': last_t_text,
                'last_time': last_t_msg['created_at'] if last_t_msg else None,
                'unread': unread_t
            })

        # 3. Discussions privées avec les camarades de la même classe (strictement confidentielles entre ces deux élèves)
        classmates = cursor.execute('''
            SELECT u.id, u.username, u.full_name, u.classe,
                   (SELECT CASE 
                               WHEN m.content IS NOT NULL AND TRIM(m.content) != '' THEN m.content 
                               WHEN m.file_name IS NOT NULL THEN '📎 ' || m.file_name 
                               ELSE 'Pièce jointe' 
                           END 
                    FROM messages m 
                    WHERE (m.sender_id = u.id AND m.receiver_id = ?) OR (m.sender_id = ? AND m.receiver_id = u.id)
                    ORDER BY m.created_at DESC LIMIT 1) AS last_message,
                   (SELECT m.created_at FROM messages m 
                    WHERE (m.sender_id = u.id AND m.receiver_id = ?) OR (m.sender_id = ? AND m.receiver_id = u.id)
                    ORDER BY m.created_at DESC LIMIT 1) AS last_time,
                   (SELECT COUNT(*) FROM messages m 
                    WHERE m.sender_id = u.id AND m.receiver_id = ? AND m.is_read = 0) AS unread
            FROM users u
            WHERE u.role = 'student' AND u.id != ? AND LOWER(TRIM(u.classe)) = LOWER(TRIM(?))
            ORDER BY unread DESC, CASE WHEN last_time IS NOT NULL THEN 0 ELSE 1 END, last_time DESC, u.full_name ASC
        ''', (user_id, user_id, user_id, user_id, user_id, user_id, student_classe)).fetchall()

        for c in classmates:
            direct_chats.append({
                'id': f"direct_{c['id']}",
                'type': 'direct',
                'with_user_id': c['id'],
                'name': c['full_name'],
                'classe': c['classe'],
                'badge': 'Camarade',
                'is_teacher': False,
                'last_message': c['last_message'] or "Démarrer une discussion",
                'last_time': c['last_time'],
                'unread': c['unread']
            })

    conn.close()
    return jsonify({
        'channels': channels,
        'direct_chats': direct_chats,
        'current_user': dict(me)
    })


@app.route('/api/messages/thread', methods=['GET'])
@login_required
def get_message_thread():
    user_id, role = get_auth_user()
    is_admin = is_user_admin(user_id)
    conn = get_db()
    cursor = conn.cursor()

    target_type = (request.args.get('type') or 'direct').strip()
    target_class = (request.args.get('target_class') or '').strip()
    teacher_id = request.args.get('teacher_id', type=int)
    with_user_id = request.args.get('with_user_id', type=int)

    messages = []
    thread_info = {}

    if target_type == 'class_broadcast':
        if not target_class:
            conn.close()
            return jsonify({'error': 'Classe cible obligatoire'}), 400

        # Si l'utilisateur connecté est un enseignant, le fil d'annonces est le sien
        if role == 'teacher':
            teacher_id = user_id

        # Information sur l'enseignant émetteur
        teacher_row = None
        if teacher_id:
            teacher_row = cursor.execute("SELECT full_name FROM users WHERE id = ?", (teacher_id,)).fetchone()

        teacher_label = f" — {teacher_row['full_name']}" if teacher_row else ""
        thread_info = {
            'type': 'class_broadcast',
            'target_class': target_class,
            'teacher_id': teacher_id,
            'title': f"📢 Annonces : {target_class}{teacher_label}",
            'subtitle': f"Diffusions officielles pour la classe {target_class}"
        }

        # Récupération des messages de diffusion
        query = '''
            SELECT m.id, m.sender_id, m.content, m.created_at, m.message_type, m.target_class,
                   m.file_path, m.file_name, m.file_size, m.mime_type,
                   u.full_name AS sender_name, u.role AS sender_role, u.classe AS sender_classe
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE m.message_type = 'class_broadcast' 
              AND (LOWER(TRIM(m.target_class)) = LOWER(TRIM(?)) OR m.target_class = 'Toutes les classes')
        '''
        params = [target_class]

        if teacher_id:
            query += " AND m.sender_id = ?"
            params.append(teacher_id)

        query += " ORDER BY m.created_at ASC"
        rows = cursor.execute(query, params).fetchall()

        for r in rows:
            m = dict(r)
            m['is_mine'] = (m['sender_id'] == user_id)
            m['can_delete'] = (m['sender_id'] == user_id) or is_admin or (role == 'teacher')
            messages.append(m)

        # Marquer comme lus les messages de cette diffusion pour l'utilisateur
        read_query = '''
            INSERT OR IGNORE INTO message_reads (message_id, user_id)
            SELECT id, ? FROM messages 
            WHERE message_type = 'class_broadcast' 
              AND (LOWER(TRIM(target_class)) = LOWER(TRIM(?)) OR target_class = 'Toutes les classes')
        '''
        read_params = [user_id, target_class]
        if teacher_id:
            read_query += " AND sender_id = ?"
            read_params.append(teacher_id)

        cursor.execute(read_query, read_params)
        conn.commit()

    else:
        # Discussion directe 1-à-1
        if not with_user_id:
            conn.close()
            return jsonify({'error': 'Identifiant du destinataire obligatoire'}), 400

        other_user = cursor.execute("SELECT id, full_name, role, classe FROM users WHERE id = ?", (with_user_id,)).fetchone()
        if not other_user:
            conn.close()
            return jsonify({'error': 'Destinataire introuvable'}), 404

        thread_info = {
            'type': 'direct',
            'with_user_id': with_user_id,
            'title': other_user['full_name'],
            'subtitle': f"Rôle : {('Enseignant' if other_user['role'] == 'teacher' else 'Élève - Classe ' + (other_user['classe'] or ''))}"
        }

        # Récupération STRICTE des messages entre ces deux utilisateurs uniquement
        rows = cursor.execute('''
            SELECT m.id, m.sender_id, m.receiver_id, m.content, m.created_at, m.is_read, m.message_type,
                   m.file_path, m.file_name, m.file_size, m.mime_type,
                   u.full_name AS sender_name, u.role AS sender_role, u.classe AS sender_classe
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE m.message_type = 'direct'
              AND ((m.sender_id = ? AND m.receiver_id = ?) OR (m.sender_id = ? AND m.receiver_id = ?))
            ORDER BY m.created_at ASC
        ''', (user_id, with_user_id, with_user_id, user_id)).fetchall()

        for r in rows:
            m = dict(r)
            m['is_mine'] = (m['sender_id'] == user_id)
            m['can_delete'] = (m['sender_id'] == user_id) or is_admin or (role == 'teacher')
            messages.append(m)

        # Marquer les messages reçus de cet utilisateur comme lus
        cursor.execute('''
            UPDATE messages SET is_read = 1 
            WHERE receiver_id = ? AND sender_id = ? AND is_read = 0
        ''', (user_id, with_user_id))
        conn.commit()

    conn.close()
    return jsonify({
        'thread': thread_info,
        'messages': messages
    })


@app.route('/api/messages/send', methods=['POST'])
@login_required
def send_message():
    user_id, role = get_auth_user()
    if request.is_json:
        data = request.get_json(silent=True) or {}
        content = (data.get('content') or '').strip()
        target_type = (data.get('target_type') or data.get('message_type') or 'direct').strip()
        target_class = (data.get('target_class') or '').strip()
        receiver_id = data.get('receiver_id')
        file_obj = None
    else:
        content = (request.form.get('content') or '').strip()
        target_type = (request.form.get('target_type') or request.form.get('message_type') or 'direct').strip()
        target_class = (request.form.get('target_class') or '').strip()
        receiver_id = request.form.get('receiver_id')
        file_obj = request.files.get('file') or request.files.get('attachment')

    if not content and not file_obj:
        return jsonify({'error': 'Veuillez saisir un message ou joindre un fichier'}), 400

    saved_file_rel = None
    saved_file_orig = None
    saved_file_size = None
    saved_file_mime = None
    saved_file_blob_url = None

    if file_obj and file_obj.filename:
        if not allowed_message_file(file_obj.filename):
            return jsonify({'error': 'Format de fichier non autorisé. Formats acceptés : PDF, Word, Excel, PowerPoint, Images, Zip, Audio...'}), 400
        
        orig_name = secure_filename(file_obj.filename)
        if not orig_name:
            orig_name = "fichier_joint"
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_name = f"{timestamp}_{orig_name}"
        
        messages_dir = os.path.join(UPLOADS_DIR, 'messages')
        os.makedirs(messages_dir, exist_ok=True)
        dest_path = os.path.join(messages_dir, unique_name)
        
        file_bytes = file_obj.read()
        with open(dest_path, 'wb') as f:
            f.write(file_bytes)
            
        saved_file_rel = f"messages/{unique_name}"
        saved_file_orig = orig_name
        saved_file_size = len(file_bytes)
        saved_file_mime = file_obj.content_type or 'application/octet-stream'
        saved_file_blob_url = None

        try:
            from blob_sync import upload_message_file_to_blob
            saved_file_blob_url = upload_message_file_to_blob(file_bytes, unique_name)
        except Exception as e:
            print("[MessageUploadBlob] Error:", e)

    conn = get_db()
    cursor = conn.cursor()

    sender = cursor.execute("SELECT id, full_name, role, classe, is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
    if not sender:
        conn.close()
        return jsonify({'error': 'Expéditeur introuvable'}), 404

    if target_type == 'class_broadcast':
        if sender['role'] != 'teacher':
            conn.close()
            return jsonify({'error': 'Seul un enseignant est autorisé à diffuser des messages à toute une classe.'}), 403

        if not target_class:
            conn.close()
            return jsonify({'error': 'Veuillez sélectionner la classe destinataire.'}), 400

        # Vérification d'affectation pour enseignant non-admin
        if not sender['is_admin']:
            assigned = get_teacher_classes(user_id)
            if target_class not in assigned:
                conn.close()
                return jsonify({
                    'error': f"Vous n'êtes pas assigné(e) à la classe '{target_class}'. Vos classes : {', '.join(assigned)}"
                }), 403

        cursor.execute('''
            INSERT INTO messages (sender_id, receiver_id, target_class, message_type, content, file_path, file_name, file_size, mime_type, blob_url, is_read, created_at)
            VALUES (?, NULL, ?, 'class_broadcast', ?, ?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
        ''', (user_id, target_class, content, saved_file_rel, saved_file_orig, saved_file_size, saved_file_mime, saved_file_blob_url))
        msg_id = cursor.lastrowid

        # Lu automatiquement par l'émetteur
        cursor.execute('INSERT OR IGNORE INTO message_reads (message_id, user_id) VALUES (?, ?)', (msg_id, user_id))

        desc = f"Diffusion de message à la classe : {target_class}"
        if saved_file_orig:
            desc += f" (Pièce jointe : {saved_file_orig})"

        cursor.execute('''
            INSERT INTO activity_logs (user_id, action_type, description, target_type, target_id, extra_data)
            VALUES (?, 'BROADCAST_MESSAGE', ?, 'message', ?, ?)
        ''', (user_id, desc, msg_id, saved_file_orig))

        conn.commit()
        conn.close()

        notify_db_mutation()

        return jsonify({
            'success': True,
            'message': f"Message diffusé avec succès à la classe '{target_class}' !",
            'message_id': msg_id,
            'has_attachment': bool(saved_file_rel)
        })

    else:
        # Message direct 1-à-1
        if not receiver_id:
            conn.close()
            return jsonify({'error': 'Destinataire obligatoire'}), 400

        try:
            receiver_id = int(receiver_id)
        except (ValueError, TypeError):
            conn.close()
            return jsonify({'error': 'Identifiant du destinataire invalide'}), 400

        receiver = cursor.execute("SELECT id, full_name, role, classe, is_admin FROM users WHERE id = ?", (receiver_id,)).fetchone()
        if not receiver:
            conn.close()
            return jsonify({'error': 'Destinataire introuvable'}), 404

        sender_is_admin = is_user_admin(user_id)
        receiver_is_admin = is_user_admin(receiver_id)

        # Contrôle d'accès :
        # 1. Élève <-> Élève : doivent être dans la même classe
        if sender['role'] == 'student' and receiver['role'] == 'student':
            if (sender['classe'] or '').strip().lower() != (receiver['classe'] or '').strip().lower():
                conn.close()
                return jsonify({'error': "Vous pouvez uniquement échanger avec des élèves de votre propre classe."}), 403

        # 2. Enseignant non-admin <-> Élève : l'élève doit être dans une des classes assignées au prof
        if sender['role'] == 'teacher' and not sender_is_admin and receiver['role'] == 'student':
            assigned = [c.strip().lower() for c in get_teacher_classes(user_id)]
            if (receiver['classe'] or '').strip().lower() not in assigned:
                conn.close()
                return jsonify({'error': "Cet élève n'appartient pas à l'une de vos classes assignées."}), 403

        # 3. Élève <-> Enseignant non-admin : le prof doit enseigner à la classe de l'élève
        if sender['role'] == 'student' and receiver['role'] == 'teacher' and not receiver_is_admin:
            assigned = [c.strip().lower() for c in get_teacher_classes(receiver['id'])]
            if (sender['classe'] or '').strip().lower() not in assigned:
                conn.close()
                return jsonify({'error': "Cet enseignant n'est pas assigné à votre classe."}), 403

        cursor.execute('''
            INSERT INTO messages (sender_id, receiver_id, target_class, message_type, content, file_path, file_name, file_size, mime_type, blob_url, is_read, created_at)
            VALUES (?, ?, NULL, 'direct', ?, ?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
        ''', (user_id, receiver_id, content, saved_file_rel, saved_file_orig, saved_file_size, saved_file_mime, saved_file_blob_url))
        msg_id = cursor.lastrowid

        desc = f"Message envoyé à {receiver['full_name']}"
        if saved_file_orig:
            desc += f" (Pièce jointe : {saved_file_orig})"

        cursor.execute('''
            INSERT INTO activity_logs (user_id, action_type, description, target_type, target_id, extra_data)
            VALUES (?, 'SEND_DIRECT_MESSAGE', ?, 'message', ?, ?)
        ''', (user_id, desc, msg_id, saved_file_orig))

        conn.commit()
        conn.close()

        notify_db_mutation()

        return jsonify({
            'success': True,
            'message': 'Message envoyé avec succès !',
            'message_id': msg_id,
            'has_attachment': bool(saved_file_rel)
        })


@app.route('/api/messages/files/<int:message_id>/view', methods=['GET'])
@login_required
def view_message_file(message_id):
    user_id, role = get_auth_user()
    conn = get_db()
    cursor = conn.cursor()

    msg = cursor.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    if not msg or not msg['file_path']:
        conn.close()
        return jsonify({'error': 'Pièce jointe introuvable'}), 404

    user = cursor.execute("SELECT id, role, classe, is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
    allowed = False

    if user and user['is_admin']:
        allowed = True
    elif msg['message_type'] == 'direct':
        if msg['sender_id'] == user_id or msg['receiver_id'] == user_id:
            allowed = True
    elif msg['message_type'] == 'class_broadcast':
        target = (msg['target_class'] or '').strip()
        if user['role'] == 'teacher':
            assigned = get_teacher_classes(user_id)
            if target == 'Toutes les classes' or target in assigned or msg['sender_id'] == user_id:
                allowed = True
        elif user['role'] == 'student':
            student_class = (user['classe'] or '').strip()
            if target == 'Toutes les classes' or student_class.lower() == target.lower():
                allowed = True

    conn.close()

    if not allowed:
        return jsonify({'error': 'Accès non autorisé à cette pièce jointe'}), 403

    full_path = os.path.join(UPLOADS_DIR, msg['file_path'])
    if not os.path.exists(full_path):
        try:
            from blob_sync import download_message_file_from_blob
            b_url = msg['blob_url'] if 'blob_url' in msg.keys() else None
            download_message_file_from_blob(msg['file_path'], full_path, direct_blob_url=b_url)
        except Exception as e:
            print("[view_message_file] blob download err:", e)

    if not os.path.exists(full_path):
        return jsonify({'error': "Le fichier physique n'est plus disponible sur le serveur"}), 404

    ext = os.path.splitext(msg['file_name'])[1].lower() if msg['file_name'] else ''

    # Word documents: render HTML directly in iframe
    if ext in ('.docx', '.doc'):
        from document_viewer import render_docx
        html_content = render_docx(full_path, msg['file_name'])
        return Response(html_content, mimetype='text/html; charset=utf-8')

    # Images
    if ext in ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'):
        return send_file(
            full_path,
            mimetype=msg['mime_type'] or 'image/jpeg',
            as_attachment=False,
            download_name=msg['file_name']
        )

    # PowerPoint / Excel fallback
    if ext in ('.ppt', '.pptx', '.xls', '.xlsx'):
        from document_viewer import render_office_fallback
        auth_param = f"?auth_token={request.args.get('auth_token')}" if request.args.get('auth_token') else ""
        download_url = f"/api/messages/files/{message_id}/download{auth_param}"
        html_content = render_office_fallback(msg['file_name'], download_url)
        return Response(html_content, mimetype='text/html; charset=utf-8')

    # PDF documents
    if ext == '.pdf':
        if request.args.get('raw') == '1':
            return send_file(
                full_path,
                mimetype='application/pdf',
                as_attachment=False,
                download_name=msg['file_name']
            )
        from document_viewer import render_pdf_viewer
        auth_param = f"&auth_token={request.args.get('auth_token')}" if request.args.get('auth_token') else ""
        raw_pdf_url = f"/api/messages/files/{message_id}/view?raw=1{auth_param}"
        download_url = f"/api/messages/files/{message_id}/download{auth_param.replace('&', '?', 1)}"
        html_content = render_pdf_viewer(raw_pdf_url, msg['file_name'], download_url)
        return Response(html_content, mimetype='text/html; charset=utf-8')

    # Default inline display
    return send_file(
        full_path,
        mimetype=msg['mime_type'] or 'application/octet-stream',
        as_attachment=False,
        download_name=msg['file_name']
    )


@app.route('/api/messages/files/<int:message_id>/download', methods=['GET'])
@login_required
def download_message_file(message_id):
    user_id, role = get_auth_user()
    conn = get_db()
    cursor = conn.cursor()

    msg = cursor.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    if not msg or not msg['file_path']:
        conn.close()
        return jsonify({'error': 'Pièce jointe introuvable'}), 404

    user = cursor.execute("SELECT id, role, classe, is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
    allowed = False

    if user and user['is_admin']:
        allowed = True
    elif msg['message_type'] == 'direct':
        if msg['sender_id'] == user_id or msg['receiver_id'] == user_id:
            allowed = True
    elif msg['message_type'] == 'class_broadcast':
        target = (msg['target_class'] or '').strip()
        if user['role'] == 'teacher':
            assigned = get_teacher_classes(user_id)
            if target == 'Toutes les classes' or target in assigned or msg['sender_id'] == user_id:
                allowed = True
        elif user['role'] == 'student':
            student_class = (user['classe'] or '').strip()
            if target == 'Toutes les classes' or student_class.lower() == target.lower():
                allowed = True

    conn.close()

    if not allowed:
        return jsonify({'error': 'Accès non autorisé à cette pièce jointe'}), 403

    full_path = os.path.join(UPLOADS_DIR, msg['file_path'])
    if not os.path.exists(full_path):
        try:
            from blob_sync import download_message_file_from_blob
            b_url = msg['blob_url'] if 'blob_url' in msg.keys() else None
            download_message_file_from_blob(msg['file_path'], full_path, direct_blob_url=b_url)
        except Exception as e:
            print("[download_message_file] blob download err:", e)

    if not os.path.exists(full_path):
        return jsonify({'error': "Le fichier physique n'est plus disponible sur le serveur"}), 404

    return send_file(
        full_path,
        mimetype=msg['mime_type'] or 'application/octet-stream',
        as_attachment=True,
        download_name=msg['file_name'] or 'piece_jointe'
    )


@app.route('/api/messages/<int:message_id>', methods=['DELETE'])
@login_required
def delete_message(message_id):
    user_id, role = get_auth_user()
    conn = get_db()
    cursor = conn.cursor()

    msg = cursor.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    if not msg:
        conn.close()
        return jsonify({'error': 'Message introuvable'}), 404

    is_admin = is_user_admin(user_id)
    can_delete = (msg['sender_id'] == user_id) or is_admin or (role == 'teacher')
    if not can_delete:
        conn.close()
        return jsonify({'error': "Vous n'êtes pas autorisé(e) à supprimer ce message."}), 403

    # Supprimer le fichier physique associé si existant
    if msg['file_path']:
        try:
            full_path = os.path.join(UPLOADS_DIR, msg['file_path'])
            if os.path.exists(full_path):
                os.remove(full_path)
        except Exception as e:
            print(f"[delete_message] Erreur suppression fichier: {e}")

    # Suppression des lectures et du message
    cursor.execute("DELETE FROM message_reads WHERE message_id = ?", (message_id,))
    cursor.execute("DELETE FROM messages WHERE id = ?", (message_id,))

    cursor.execute('''
        INSERT INTO activity_logs (user_id, action_type, description, target_type, target_id)
        VALUES (?, 'DELETE_MESSAGE', ?, 'message', ?)
    ''', (user_id, f"Suppression du message #{message_id}", message_id))

    conn.commit()
    conn.close()

    notify_db_mutation()

    return jsonify({'success': True, 'message': 'Message supprimé avec succès'})


@app.route('/api/messages/contacts', methods=['GET'])
@login_required
def get_message_contacts():
    user_id, role = get_auth_user()
    conn = get_db()
    cursor = conn.cursor()

    me = cursor.execute("SELECT id, role, classe, is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
    if not me:
        conn.close()
        return jsonify({'contacts': []})

    contacts = []
    if me['role'] == 'teacher':
        is_admin = is_user_admin(user_id)
        # Autres enseignants
        other_teachers = cursor.execute("""
            SELECT id, full_name, username, classe, 'teacher' AS role
            FROM users 
            WHERE role = 'teacher' AND id != ?
            ORDER BY full_name ASC
        """, (user_id,)).fetchall()
        contacts.extend([dict(t) for t in other_teachers])

        if is_admin:
            # Tous les élèves pour l'administrateur
            rows = cursor.execute("""
                SELECT id, full_name, username, classe, 'student' AS role
                FROM users 
                WHERE role = 'student'
                ORDER BY classe ASC, full_name ASC
            """).fetchall()
            contacts.extend([dict(r) for r in rows])
        else:
            # Uniquement les élèves des classes assignées à cet enseignant
            assigned = get_teacher_classes(user_id)
            if assigned:
                placeholders = ','.join(['?'] * len(assigned))
                rows = cursor.execute(f"""
                    SELECT id, full_name, username, classe, 'student' AS role
                    FROM users 
                    WHERE role = 'student' AND classe IN ({placeholders})
                    ORDER BY classe ASC, full_name ASC
                """, assigned).fetchall()
                contacts.extend([dict(r) for r in rows])

    else:
        student_classe = (me['classe'] or '').strip()
        # Enseignants qui enseignent à cette classe ou administrateur
        teachers = cursor.execute("""
            SELECT u.id, u.full_name, u.username, u.classe, 'teacher' AS role
            FROM users u
            WHERE u.role = 'teacher' AND (
                u.is_admin = 1 OR EXISTS (
                    SELECT 1 FROM teacher_classes tc 
                    WHERE tc.teacher_id = u.id 
                      AND (LOWER(TRIM(tc.class_name)) = LOWER(TRIM(?)) OR LOWER(tc.class_name) LIKE '%toute%')
                )
            )
            ORDER BY u.id ASC
        """, (student_classe,)).fetchall()
        for t in teachers:
            contacts.append(dict(t))

        # Camarades de la même classe
        rows = cursor.execute("""
            SELECT id, full_name, username, classe, 'student' AS role
            FROM users 
            WHERE role = 'student' AND id != ? AND LOWER(TRIM(classe)) = LOWER(TRIM(?))
            ORDER BY full_name ASC
        """, (user_id, student_classe)).fetchall()
        contacts.extend([dict(r) for r in rows])

    conn.close()
    return jsonify({'contacts': contacts})

# Initialize database on app startup (supports both local and Vercel serverless)
try:
    init_db()
    seed_database_if_empty()
except Exception as e:
    print("[Startup DB Init Error]", e)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    print(f"\n=======================================================")
    print(f"🚀 Plateforme de Partage de Cours - Prof. Msalbi")
    print(f"📍 Serveur démarré sur : http://localhost:{port}")
    print(f"🔑 Compte Enseignant : identifiant = msalbi / mot de passe = msalbi123")
    print(f"🎓 Compte Élève Démo : identifiant = yassine.b / mot de passe = eleve123")
    print(f"=======================================================\n")
    app.run(host='0.0.0.0', port=port, debug=False)
