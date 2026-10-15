import re
import socket
import zipfile
import requests
from bs4 import BeautifulSoup
from flask import Blueprint, request, jsonify, render_template

interactive_bp = Blueprint('interactive_bp', __name__)

@interactive_bp.route('/tools/api-bridge', methods=['GET', 'POST'])
def api_bridge():
    if request.method == 'GET':
        return render_template('tools/tool_api_bridge.html', active_page='tools')
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    if not url.startswith(('http://', 'https://')):
        return jsonify({"status": "error", "message": "Valid HTTP/HTTPS URL required"}), 400
    for blocked in ['localhost', '127.0.0.1', '0.0.0.0', '169.254.169.254']:
        if blocked in url:
            return jsonify({"status": "error", "message": "Access to local address restricted"}), 403
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Platform Audit)'}, timeout=8)
        try:
            return jsonify({"status": "success", "mode": "raw_json", "data": r.json()})
        except Exception:
            pass
        soup = BeautifulSoup(r.text, 'html.parser')
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        headings = [h.get_text().strip() for h in soup.find_all(['h1', 'h2']) if h.get_text().strip()]
        links = [a.get('href') for a in soup.find_all('a', href=True) if a.get('href').startswith('http')][:10]
        return jsonify({
            "status": "success",
            "mode": "dom_extracted",
            "data": {"title": title, "status_code": r.status_code, "headings": headings[:6], "links": links}
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@interactive_bp.route('/tools/api-vault', methods=['GET', 'POST'])
def api_vault():
    if request.method == 'GET':
        return render_template('tools/tool_api_vault.html', active_page='tools')
    data = request.get_json() or {}
    key = data.get('key', '').strip()
    entropy = len(set(key)) * 3.5 if key else 0
    return jsonify({
        "status": "success",
        "length": len(key),
        "estimated_entropy_bits": round(entropy, 2),
        "strength": "High" if entropy > 65 else ("Medium" if entropy > 35 else "Weak"),
        "compliance": "Passed basic format constraints"
    })

@interactive_bp.route('/tools/request-reverser', methods=['GET', 'POST'])
def request_reverser():
    if request.method == 'GET':
        return render_template('tools/tool_reverser.html', active_page='tools')
    data = request.get_json() or {}
    curl = data.get('curl', '').strip()
    match_url = re.search(r"curl\s+['\"]?([^'\"\s]+)", curl)
    target = match_url.group(1) if match_url else "https://example.com/api"
    py_code = f"import requests\n\nheaders = {{'User-Agent': 'Akhil-Platform-Client'}}\nresponse = requests.get('{target}', headers=headers)\nprint(response.json())"
    return jsonify({"status": "success", "parsed_url": target, "generated_python": py_code})

@interactive_bp.route('/tools/osint-username', methods=['GET', 'POST'])
def osint_username():
    if request.method == 'GET':
        return render_template('tools/tool_osint_user.html', active_page='tools')
    data = request.get_json() or {}
    user = data.get('username', '').strip()
    if not user or not re.match(r'^[a-zA-Z0-9_\-]+$', user):
        return jsonify({"status": "error", "message": "Valid alphanumeric handle required"}), 400
    
    platforms = [
        {"name": "GitHub", "url": f"https://api.github.com/users/{user}"},
        {"name": "Dev.to", "url": f"https://dev.to/api/users/by_username?url={user}"},
        {"name": "GitLab", "url": f"https://gitlab.com/{user}"}
    ]
    results = []
    for p in platforms:
        try:
            res = requests.get(p["url"], headers={'User-Agent': 'Mozilla/5.0'}, timeout=4)
            found = (res.status_code == 200)
            results.append({"platform": p["name"], "profile_url": p["url"].replace('api.', '').replace('api/users/by_username?url=', ''), "exists": found})
        except Exception:
            results.append({"platform": p["name"], "profile_url": "", "exists": False})
    return jsonify({"status": "success", "username": user, "matches": results})

@interactive_bp.route('/tools/domain-recon', methods=['GET', 'POST'])
def domain_recon():
    if request.method == 'GET':
        return render_template('tools/tool_domain_recon.html', active_page='tools')
    data = request.get_json() or {}
    domain = data.get('domain', '').replace('https://', '').replace('http://', '').strip().split('/')[0]
    if not domain:
        return jsonify({"status": "error", "message": "Domain required"}), 400
    try:
        ip = socket.gethostbyname(domain)
        resp = requests.get(f"https://{domain}", timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
        headers_found = {k: v for k, v in resp.headers.items() if k.lower() in ['server', 'content-security-policy', 'strict-transport-security', 'x-frame-options']}
        return jsonify({"status": "success", "domain": domain, "resolved_ip": ip, "security_headers": headers_found})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@interactive_bp.route('/tools/apk-inspector', methods=['GET', 'POST'])
def apk_inspector():
    if request.method == 'GET':
        return render_template('tools/tool_apk.html', active_page='tools')
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No APK file uploaded"}), 400
    f = request.files['file']
    if not f.filename.endswith('.apk'):
        return jsonify({"status": "error", "message": "File must end with .apk"}), 400
    try:
        with zipfile.ZipFile(f, 'r') as z:
            names = z.namelist()
            return jsonify({
                "status": "success",
                "filename": f.filename,
                "total_files": len(names),
                "dex_count": len([n for n in names if n.endswith('.dex')]),
                "manifest_present": 'AndroidManifest.xml' in names,
                "components": [n for n in names if n.endswith('.dex') or n.startswith('lib/')][:15]
            })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@interactive_bp.route('/tools/playlist-generator', methods=['GET', 'POST'])
def playlist_generator():
    if request.method == 'GET':
        return render_template('tools/tool_playlist.html', active_page='tools')
    data = request.get_json() or {}
    title = data.get('title', 'Cyber Synthwave')
    tracks = data.get('tracks', 'Track 01, Track 02, Track 03').split(',')
    clean_tracks = [{"index": idx+1, "title": t.strip(), "format": "lossless_flac"} for idx, t in enumerate(tracks) if t.strip()]
    return jsonify({"status": "success", "playlist_name": title, "track_count": len(clean_tracks), "items": clean_tracks})
