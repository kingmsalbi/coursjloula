import os
import urllib.request
import urllib.parse
import urllib.error
import json

def get_supabase_config():
    """
    Récupère l'URL et la clé d'API Supabase depuis l'environnement ou .env.local
    """
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_KEY') or os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or os.environ.get('SUPABASE_ANON_KEY')
    bucket = os.environ.get('SUPABASE_BUCKET', 'partage-cours')

    if (not url or not key) and os.path.exists('.env.local'):
        try:
            with open('.env.local', 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('SUPABASE_URL='):
                        url = line.split('=', 1)[1].strip().strip('"').strip("'")
                    elif line.startswith('SUPABASE_KEY=') or line.startswith('SUPABASE_ANON_KEY='):
                        key = line.split('=', 1)[1].strip().strip('"').strip("'")
                    elif line.startswith('SUPABASE_BUCKET='):
                        bucket = line.split('=', 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass

    if not url:
        url = "https://hrxceonzdtpcluwnitpk.supabase.co"
    if not key:
        key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhyeGNlb256ZHRwY2x1d25pdHBrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5NTAzODExNiwiZXhwIjoyMTEwNjE0MTE2fQ.t40dN1CRuqhujDHoXvkfBj0uT0Lmn07enJG4D8h-ZIc"

    return url, key, bucket

def upload_file_to_supabase(file_bytes, remote_path, content_type='application/octet-stream'):
    """
    Téléverse un fichier (cours, message, base de données) sur Supabase Storage.
    Renvoie l'URL publique directe du fichier, ou None en cas d'erreur.
    """
    url, key, bucket = get_supabase_config()
    if not url or not key:
        return None

    # Normalisation de l'URL
    url = url.rstrip('/')
    remote_path = remote_path.lstrip('/')
    safe_path = urllib.parse.quote(remote_path)

    # Supabase Storage Upload API
    endpoint = f"{url}/storage/v1/object/{bucket}/{safe_path}"
    headers = {
        'Authorization': f'Bearer {key}',
        'apikey': key,
        'Content-Type': content_type,
        'x-upsert': 'true'  # Écrase le fichier s'il existe déjà
    }

    try:
        req = urllib.request.Request(endpoint, data=file_bytes, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=25) as resp:
            if resp.status in (200, 201):
                public_url = f"{url}/storage/v1/object/public/{bucket}/{safe_path}"
                print(f"[SupabaseStorage] Fichier {remote_path} téléversé avec succès: {public_url}")
                return public_url
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode('utf-8', errors='ignore')
        print(f"[SupabaseStorage] Erreur HTTP {e.code} lors de l'upload: {err_msg}")
    except Exception as e:
        print(f"[SupabaseStorage] Exception upload: {e}")

    return None

def download_file_from_supabase(remote_path, dest_local_path):
    """
    Télécharge un fichier depuis Supabase Storage vers le disque local.
    """
    url, key, bucket = get_supabase_config()
    if not url or not key:
        return False

    url = url.rstrip('/')
    remote_path = remote_path.lstrip('/')
    safe_path = urllib.parse.quote(remote_path)

    public_url = f"{url}/storage/v1/object/public/{bucket}/{safe_path}"

    try:
        req = urllib.request.Request(public_url, headers={'User-Agent': 'PartageCours/3.0'})
        with urllib.request.urlopen(req, timeout=20) as resp:
            if resp.status == 200:
                os.makedirs(os.path.dirname(os.path.abspath(dest_local_path)), exist_ok=True)
                with open(dest_local_path, 'wb') as f:
                    f.write(resp.read())
                print(f"[SupabaseStorage] Téléchargement réussi: {dest_local_path}")
                return True
    except Exception as e:
        print(f"[SupabaseStorage] Erreur téléchargement {remote_path}: {e}")

    return False
