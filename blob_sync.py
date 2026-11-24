import os
import urllib.request
import urllib.parse
import urllib.error
import json
import time

# --- Configuration & In-Memory Cache (Server-Side) ---
BLOB_BASE_URL = "https://ueftinjdc4wrrw3o.public.blob.vercel-storage.com"
DB_CACHE_TTL_SECONDS = 300  # 5 minutes de mise en cache serveur en mémoire

_cached_db_version = None
_cached_db_url = None
_last_sync_check_time = 0

def get_blob_token():
    token = os.environ.get('BLOB_PUBLIC_READ_WRITE_TOKEN') or os.environ.get('BLOB_READ_WRITE_TOKEN')
    if not token and os.path.exists('.env.local'):
        try:
            with open('.env.local', 'r') as f:
                for line in f:
                    if line.startswith('BLOB_PUBLIC_READ_WRITE_TOKEN='):
                        token = line.strip().split('=', 1)[1].strip().strip('"').strip("'")
                        break
                    elif line.startswith('BLOB_READ_WRITE_TOKEN=') and not token:
                        token = line.strip().split('=', 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return token

def sync_from_blob(dest_path, force=False):
    """
    Télécharge la base de données depuis Vercel Blob SANS APPEL À list().
    Utilise un fichier pointeur JSON léger ('partage_cours_latest.json')
    effectué via un simple GET statique (0 opération avancée consommée).
    Met en cache le résultat pendant DB_CACHE_TTL_SECONDS.
    """
    global _cached_db_version, _cached_db_url, _last_sync_check_time

    now = time.time()
    # 1. Vérification du cache en mémoire serveur
    if not force and os.path.exists(dest_path) and (now - _last_sync_check_time < DB_CACHE_TTL_SECONDS):
        return True

    download_url = None
    cloud_version = None

    # 2. Récupération directe du pointeur de version (GET statique = Opération simple)
    try:
        pointer_url = f"{BLOB_BASE_URL}/partage_cours_latest.json"
        req_p = urllib.request.Request(pointer_url, headers={'User-Agent': 'PartageCoursSync/2.0'})
        with urllib.request.urlopen(req_p, timeout=5) as resp_p:
            if resp_p.status == 200:
                p_data = json.loads(resp_p.read().decode('utf-8'))
                cloud_version = p_data.get('version')
                download_url = p_data.get('url')
    except Exception:
        # Pointeur non encore initialisé ou inaccessible
        pass

    # Si la version en cache local correspond à la version cloud et que le fichier existe, ne pas retélécharger
    if cloud_version and cloud_version == _cached_db_version and os.path.exists(dest_path):
        _last_sync_check_time = now
        return True

    if not download_url:
        download_url = f"{BLOB_BASE_URL}/partage_cours.db"

    # 3. Téléchargement direct du fichier SQLite (GET direct = Opération simple)
    try:
        req = urllib.request.Request(download_url, headers={'User-Agent': 'PartageCoursSync/2.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                content = resp.read()
                if len(content) > 100 and content.startswith(b'SQLite format 3\x00'):
                    with open(dest_path, 'wb') as f:
                        f.write(content)
                    _cached_db_version = cloud_version
                    _cached_db_url = download_url
                    _last_sync_check_time = now
                    print(f"[BlobSync] Base cloud chargée ({len(content)} octets) depuis {download_url} (0 appel list())")
                    return True
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print("[BlobSync] Vercel Blob store suspendu ou quota dépassé. Tentative Supabase Storage...")
            try:
                from supabase_storage import download_file_from_supabase
                if download_file_from_supabase("database/partage_cours.db", dest_path):
                    _last_sync_check_time = now
                    return True
            except Exception:
                pass
        else:
            print(f"[BlobSync] HTTPError sync_from_blob: {e.code}")
    except Exception as e:
        print(f"[BlobSync] Erreur sync_from_blob: {e}")

    # Fallback : si la base locale existe déjà, continuer avec
    if os.path.exists(dest_path):
        _last_sync_check_time = now
        return True
        try:
            from supabase_storage import upload_file_to_supabase
            upload_file_to_supabase(data, "database/partage_cours.db")
        except Exception:
            pass

        return True

    return False

def sync_to_blob(source_path):
    """
    Sauvegarde la base de données locale dans Vercel Blob :
    1. Upload du fichier versionné (PUT direct).
    2. Mise à jour du pointeur 'partage_cours_latest.json' (PUT direct).
    AUCUN APPEL À list() n'est effectué (0 opération avancée).
    """
    global _cached_db_version, _cached_db_url, _last_sync_check_time

    token = get_blob_token()
    if not token or not os.path.exists(source_path):
        return False

    try:
        with open(source_path, 'rb') as f:
            data = f.read()

        if not data.startswith(b'SQLite format 3\x00'):
            return False

        version_id = int(time.time() * 1000)
        blob_name = f"partage_cours_v{version_id}.db"
        upload_url = f"https://blob.vercel-storage.com/{blob_name}?access=public&addRandomSuffix=false"

        req = urllib.request.Request(
            upload_url,
            data=data,
            headers={
                'Authorization': f'Bearer {token}',
                'x-api-version': '7',
                'Content-Type': 'application/vnd.sqlite3'
            },
            method='PUT'
        )

        created_url = None
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status in (200, 201):
                res_data = json.loads(resp.read().decode('utf-8'))
                created_url = res_data.get('url')
                print(f"[BlobSync] Nouvelle version cloud créée: {created_url}")

        if not created_url:
            created_url = f"{BLOB_BASE_URL}/{blob_name}"

        # 2. Mise à jour immédiate du pointeur JSON pour les lectures (PUT direct)
        try:
            pointer_payload = json.dumps({
                "version": version_id,
                "url": created_url,
                "updated_at": int(time.time())
            }).encode('utf-8')

            pointer_put_url = "https://blob.vercel-storage.com/partage_cours_latest.json?access=public&addRandomSuffix=false"
            req_p = urllib.request.Request(
                pointer_put_url,
                data=pointer_payload,
                headers={
                    'Authorization': f'Bearer {token}',
                    'x-api-version': '7',
                    'Content-Type': 'application/json'
                },
                method='PUT'
            )
            with urllib.request.urlopen(req_p, timeout=8):
                pass
        except Exception as pe:
            print(f"[BlobSync] Avertissement écriture pointeur: {pe}")

        # Mise à jour du cache local
        _cached_db_version = version_id
        _cached_db_url = created_url
        _last_sync_check_time = time.time()

        # Sauvegarde miroir automatique sur Supabase Storage si configuré
        try:
            from supabase_storage import upload_file_to_supabase
            upload_file_to_supabase(data, "database/partage_cours.db")
        except Exception:
            pass

        return True
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print("[BlobSync] Vercel Blob store suspendu ou quota dépassé. Mutation locale préservée.")
        else:
            print(f"[BlobSync] HTTPError sync_to_blob: {e.code}")
    except Exception as e:
        print(f"[BlobSync] Erreur sync_to_blob: {e}")

    return False

def upload_course_file_to_blob(file_bytes, filename):
    """
    Téléverse un fichier de cours dans Supabase Storage (en priorité) ou Vercel Blob
    et renvoie l'URL directe permanente à stocker en base de données.
    """
    try:
        from supabase_storage import upload_file_to_supabase
        supa_url = upload_file_to_supabase(file_bytes, f"courses/{os.path.basename(filename)}")
        if supa_url:
            return supa_url
    except Exception as se:
        pass

    token = get_blob_token()
    if not token:
        return None

    try:
        clean_name = os.path.basename(filename)
        safe_name = urllib.parse.quote(clean_name)
        url = f"https://blob.vercel-storage.com/courses/{safe_name}?access=public&addRandomSuffix=false"
        req = urllib.request.Request(
            url,
            data=file_bytes,
            headers={
                'Authorization': f'Bearer {token}',
                'x-api-version': '7',
                'Content-Type': 'application/octet-stream'
            },
            method='PUT'
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            if resp.status in (200, 201):
                res = json.loads(resp.read().decode('utf-8'))
                final_url = res.get('url') or f"{BLOB_BASE_URL}/courses/{safe_name}"
                print(f"[BlobSync] Fichier cours {clean_name} sauvegardé dans le cloud: {final_url}")
                return final_url
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print("[BlobSync] Vercel Blob suspendu. Fichier conservé localement.")
        else:
            print(f"[BlobSync] HTTPError upload_course_file: {e.code}")
    except Exception as e:
        print(f"[BlobSync] Erreur upload_course_file_to_blob: {e}")
    return None

def download_course_file_from_blob(filename, dest_path, direct_blob_url=None):
    """
    Télécharge un fichier de cours directement via son URL stockée en BDD.
    AUCUN APPEL À list().
    """
    clean_name = os.path.basename(filename)
    safe_name = urllib.parse.quote(clean_name)

    urls_to_try = []
    if direct_blob_url:
        urls_to_try.append(direct_blob_url)

    # Supabase Storage public URLs
    try:
        from supabase_storage import get_supabase_config
        sb_url, _, sb_bucket = get_supabase_config()
        if sb_url and sb_bucket:
            sb_base = f"{sb_url.rstrip('/')}/storage/v1/object/public/{sb_bucket}"
            urls_to_try.append(f"{sb_base}/courses/{safe_name}")
            urls_to_try.append(f"{sb_base}/courses/{clean_name}")
            urls_to_try.append(f"{sb_base}/{safe_name}")
            urls_to_try.append(f"{sb_base}/{clean_name}")
    except Exception as e:
        print("[BlobSync] Erreur configuration Supabase:", e)

    urls_to_try.append(f"{BLOB_BASE_URL}/courses/{safe_name}")
    urls_to_try.append(f"{BLOB_BASE_URL}/courses/{clean_name}")

    for d_url in urls_to_try:
        if not d_url:
            continue
        try:
            req = urllib.request.Request(d_url, headers={'User-Agent': 'PartageCours/2.0'})
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    dest_dir = os.path.dirname(dest_path)
                    if dest_dir:
                        os.makedirs(dest_dir, exist_ok=True)
                    with open(dest_path, 'wb') as f:
                        f.write(resp.read())
                    print(f"[BlobSync] Fichier {clean_name} téléchargé directement depuis: {d_url} (0 appel list())")
                    return True
        except Exception:
            pass

    return False

def upload_message_file_to_blob(file_bytes, filename):
    """
    Téléverse une pièce jointe de message dans Supabase Storage (en priorité) ou Vercel Blob
    et renvoie l'URL directe permanente à stocker en base de données.
    """
    try:
        from supabase_storage import upload_file_to_supabase
        supa_url = upload_file_to_supabase(file_bytes, f"messages/{os.path.basename(filename)}")
        if supa_url:
            return supa_url
    except Exception as se:
        pass

    token = get_blob_token()
    if not token:
        return None

    try:
        clean_name = os.path.basename(filename)
        safe_name = urllib.parse.quote(clean_name)
        url = f"https://blob.vercel-storage.com/messages/{safe_name}?access=public&addRandomSuffix=false"
        req = urllib.request.Request(
            url,
            data=file_bytes,
            headers={
                'Authorization': f'Bearer {token}',
                'x-api-version': '7',
                'Content-Type': 'application/octet-stream'
            },
            method='PUT'
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            if resp.status in (200, 201):
                res = json.loads(resp.read().decode('utf-8'))
                final_url = res.get('url') or f"{BLOB_BASE_URL}/messages/{safe_name}"
                print(f"[BlobSync] Fichier message {clean_name} sauvegardé dans le cloud: {final_url}")
                return final_url
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print("[BlobSync] Vercel Blob suspendu. Pièce jointe conservée localement.")
        else:
            print(f"[BlobSync] HTTPError upload_message_file: {e.code}")
    except Exception as e:
        print(f"[BlobSync] Erreur upload_message_file_to_blob: {e}")
    return None

def download_message_file_from_blob(filename, dest_path, direct_blob_url=None):
    """
    Télécharge une pièce jointe directement via son URL stockée en BDD.
    AUCUN APPEL À list().
    """
    clean_name = os.path.basename(filename)
    safe_name = urllib.parse.quote(clean_name)

    urls_to_try = []
    if direct_blob_url:
        urls_to_try.append(direct_blob_url)
    urls_to_try.append(f"{BLOB_BASE_URL}/messages/{safe_name}")
    urls_to_try.append(f"{BLOB_BASE_URL}/messages/{clean_name}")

    for d_url in urls_to_try:
        if not d_url:
            continue
        try:
            req = urllib.request.Request(d_url, headers={'User-Agent': 'PartageCours/2.0'})
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    dest_dir = os.path.dirname(dest_path)
                    if dest_dir:
                        os.makedirs(dest_dir, exist_ok=True)
                    with open(dest_path, 'wb') as f:
                        f.write(resp.read())
                    print(f"[BlobSync] Fichier message {clean_name} téléchargé directement depuis: {d_url} (0 appel list())")
                    return True
        except Exception:
            pass

    return False
