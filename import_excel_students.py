import os
import re
import sqlite3
import zipfile
import xml.etree.ElementTree as ET
from werkzeug.security import generate_password_hash
import random
from database import DB_PATH, get_db

EXCEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'eleve 2 it.xlsx')

TRANSLITERATIONS = {
    # Classe 2 IT
    'ادم حمدي': ('Adam Hamdi', 'adam.hamdi'),
    'جيهان اولاد احمد': ('Jihane Ouled Ahmed', 'jihane.oa'),
    'ريم ماجري': ('Rym Majri', 'rym.majri'),
    'ريان نصري': ('Rayan Nasri', 'rayan.nasri'),
    'زينب قيزاني': ('Zeineb Guizani', 'zeineb.guizani'),
    'عبد الرحمان حاركي': ('Abderrahmane Harki', 'abderrahmane.h'),
    'عبد الرحمان رحماني': ('Abderrahmane Rahmani', 'abderrahmane.r'),
    'عمر ضويوي': ('Omar Dhouioui', 'omar.dhouioui'),
    'فاطمة خماري': ('Fatma Khemari', 'fatma.khemari'),
    'معتز ثابتي': ('Moataz Thabeti', 'moataz.thabeti'),
    'ياسمين ضويوي': ('Yasmine Dhouioui', 'yasmine.dhouioui'),
    'ياسمينة بلحودي': ('Yasmina Belhoudi', 'yasmina.belhoudi'),
    'يوسف نصري': ('Youssef Nasri', 'youssef.nasri'),
    'نور مسكيني': ('Nour Meskini', 'nour.meskini'),

    # Classe 2 ECO
    'ادم الشهيبي': ('Adam Chehibi', 'adam.chehibi'),
    'اريج عدالي': ('Arij Adali', 'arij.adali'),
    'اماني كريشي': ('Amani Krichi', 'amani.krichi'),
    'ايويب بلحودي': ('Ayoub Belhoudi', 'ayoub.belhoudi'),
    'ابتهال مسكيني': ('Ibtehal Meskini', 'ibtehal.meskini'),
    'حلا ثابتي': ('Hala Thabeti', 'hala.thabeti'),
    'ريم ضويوي': ('Rym Dhouioui', 'rym.dhouioui'),
    'ريان ضويوي': ('Rayan Dhouioui', 'rayan.dhouioui'),
    'زينب رحماني': ('Zeineb Rahmani', 'zeineb.rahmani'),
    'شيماء اللوزي': ('Chaima Ellouzi', 'chaima.ellouzi'),
    'غفران ثابتي': ('Ghofrane Thabeti', 'ghofrane.thabeti'),
    'فارس ضويوي': ('Fares Dhouioui', 'fares.dhouioui'),
    'مرام نصري': ('Maram Nasri', 'maram.nasri'),
    'مريم رحماني': ('Meriem Rahmani', 'meriem.rahmani'),
    'ملاك بريكي': ('Malek Briki', 'malek.briki'),
    'ميساء ضويوي': ('Mayssa Dhouioui', 'mayssa.dhouioui'),
    'نادين ثابتي': ('Nadine Thabeti', 'nadine.thabeti'),
    'نرمين نصري': ('Nermine Nasri', 'nermine.nasri'),
    'نور الهدى رحماني': ('Nour El Houda Rahmani', 'nour.rahmani'),
    'ياسمين حمدي': ('Yasmine Hamdi', 'yasmine.hamdi'),
    'يحي ثابتي': ('Yahya Thabeti', 'yahya.thabeti'),
    'احمد ضويوي  سيد': ('Ahmed Dhouioui Sayed', 'ahmed.dhouioui'),
    'رائد صعنوني': ('Raed Saanouni', 'raed.saanouni'),
    'هديل سبري': ('Hadeel Sebri', 'hadeel.sebri'),
    'احمد ضويوي حبيب': ('Ahmed Dhouioui Habib', 'ahmed.habib')
}

AR_MAP = {
    'ا': 'a', 'أ': 'a', 'إ': 'i', 'آ': 'a', 'ب': 'b', 'ت': 't', 'ث': 'th', 'ج': 'j', 'ح': 'h', 'خ': 'kh',
    'د': 'd', 'ذ': 'dh', 'ر': 'r', 'ز': 'z', 'س': 's', 'ش': 'ch', 'ص': 's', 'ض': 'dh', 'ط': 't', 'ظ': 'dh',
    'ع': 'a', 'غ': 'gh', 'ف': 'f', 'ق': 'k', 'ك': 'k', 'ل': 'l', 'م': 'm', 'ن': 'n', 'ه': 'h', 'و': 'ou',
    'ي': 'y', 'ى': 'a', 'ة': 'a', 'ء': '', 'ئ': 'e', 'ؤ': 'ou', ' ': ' '
}

def arabic_to_latin(name):
    clean = ' '.join(name.strip().split())
    if clean in TRANSLITERATIONS:
        return TRANSLITERATIONS[clean]
    
    # Generic transliteration
    res = ''.join(AR_MAP.get(c, c) for c in clean)
    parts = [p.capitalize() for p in res.split()]
    fr_name = ' '.join(parts)
    uname = (parts[0].lower() + '.' + parts[-1].lower()) if len(parts) > 1 else parts[0].lower()
    return fr_name, uname

def get_unique_username(base_uname, classe_name, cursor, allow_same_class_match=True):
    """
    Assure un identifiant unique dans la table 'users', permettant d'avoir des élèves
    portant le même nom dans différentes classes sans collision.
    - Si l'élève existe déjà dans la MÊME classe : renvoie son identifiant existant.
    - Si l'identifiant est pris par une AUTRE classe : génère un identifiant scopé (ex: nom.prenom.2eco).
    """
    clean_classe = re.sub(r'[^a-z0-9]', '', (classe_name or '').lower())
    if not clean_classe:
        clean_classe = 'c'

    # Vérification identifiant de base
    row = cursor.execute("SELECT id, username, classe FROM users WHERE LOWER(username) = LOWER(?)", (base_uname,)).fetchone()
    if not row:
        return base_uname, False, None
    
    if allow_same_class_match and (row['classe'] or '').strip().lower() == (classe_name or '').strip().lower():
        return row['username'], True, row['id']

    # Suffixe avec le nom de la classe
    candidate = f"{base_uname}.{clean_classe}"
    row = cursor.execute("SELECT id, username, classe FROM users WHERE LOWER(username) = LOWER(?)", (candidate,)).fetchone()
    if not row:
        return candidate, False, None
    if allow_same_class_match and (row['classe'] or '').strip().lower() == (classe_name or '').strip().lower():
        return row['username'], True, row['id']

    # Suffixes incrémentaux si nécessaire
    num = 2
    while True:
        candidate_num = f"{candidate}{num}"
        row = cursor.execute("SELECT id, username, classe FROM users WHERE LOWER(username) = LOWER(?)", (candidate_num,)).fetchone()
        if not row:
            return candidate_num, False, None
        if allow_same_class_match and (row['classe'] or '').strip().lower() == (classe_name or '').strip().lower():
            return row['username'], True, row['id']
        num += 1

def extract_students_from_excel(path):
    students = []
    with zipfile.ZipFile(path, 'r') as z:
        shared = []
        if 'xl/sharedStrings.xml' in z.namelist():
            tree = ET.fromstring(z.read('xl/sharedStrings.xml'))
            for elem in tree.iter():
                if elem.tag.endswith('}t'):
                    shared.append(elem.text or '')
        
        # Universal cell scanner
        sheet_tree = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
        for cell in sheet_tree.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c'):
            cell_type = cell.attrib.get('t')
            val = cell.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
            val_text = val.text if val is not None else ''
            name = ''
            if cell_type == 's' and val_text.isdigit():
                idx = int(val_text)
                if idx < len(shared):
                    name = shared[idx].strip()
            else:
                name = val_text.strip()
            
            # Filter valid Arabic student names
            if len(name) >= 4 and ' ' in name and name not in ['م+', 'م-', 'م+++', 'م+ ', 'ن-']:
                if not any(h in name for h in ['اللقب', 'الاسم', 'تاريخ', 'الملاحظات', 'رقم']):
                    if name not in students:
                        students.append(name)

    # Fallback to shared strings if sheet cell scan missed
    if not students and shared:
        for s in shared:
            s_clean = s.strip()
            if len(s_clean) >= 4 and ' ' in s_clean and s_clean not in ['م+', 'م-', 'م+++', 'م+ ', 'ن-']:
                if not any(h in s_clean for h in ['اللقب', 'الاسم', 'تاريخ', 'الملاحظات', 'رقم']):
                    if s_clean not in students:
                        students.append(s_clean)

    return students

def import_students_file(file_path, classe_name='2 IT'):
    raw_names = extract_students_from_excel(file_path)
    print(f"Élèves détectés dans '{file_path}' ({len(raw_names)}) pour la classe '{classe_name}' :")

    conn = get_db()
    cursor = conn.cursor()

    # Ensure class exists in classes table
    c_existing = cursor.execute("SELECT id FROM classes WHERE LOWER(name) = LOWER(?)", (classe_name,)).fetchone()
    if not c_existing:
        cursor.execute("INSERT INTO classes (name, level, description) VALUES (?, '2ème Année', ?)", 
                       (classe_name, f"Classe importée : {classe_name}"))

    imported_count = 0
    updated_count = 0

    for ar_name in raw_names:
        fr_name, base_uname = arabic_to_latin(ar_name)
        full_display_name = f"{fr_name} ({ar_name})"

        final_uname, is_existing, existing_id = get_unique_username(base_uname, classe_name, cursor, allow_same_class_match=True)
        email = f"{final_uname}@eleve.tn"

        if not is_existing:
            cursor.execute('''
                INSERT INTO users (username, password_hash, full_name, email, role, classe, created_at, last_active_at)
                VALUES (?, ?, ?, ?, 'student', ?, datetime('now', '-5 days'), NULL)
            ''', (
                final_uname,
                generate_password_hash('eleve123'),
                full_display_name,
                email,
                classe_name
            ))
            imported_count += 1
        else:
            # Élève déjà existant dans CETTE classe: mise à jour sécurisée sans changer de classe
            cursor.execute('''
                UPDATE users 
                SET full_name = ?, email = ?, classe = ?
                WHERE id = ?
            ''', (full_display_name, email, classe_name, existing_id))
            updated_count += 1

    conn.commit()
    conn.close()

    print(f"Succès ! {imported_count} nouveaux élèves importés dans '{classe_name}', {updated_count} mis à jour.")
    return imported_count, updated_count

def import_students():
    return import_students_file(EXCEL_PATH, '2 IT')

if __name__ == '__main__':
    import_students()
