import re
import socket
import zipfile
import math
import requests
from bs4 import BeautifulSoup
from flask import Blueprint, request, jsonify, render_template

interactive_bp = Blueprint('interactive_bp', __name__)

# 1. API Anything Bridge
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
            return jsonify({"status": "error", "message": "Restricted address"}), 403
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

# 2. Enhanced OSINT Public Profile Inspector
@interactive_bp.route('/tools/osint-username', methods=['GET', 'POST'])
def osint_username():
    if request.method == 'GET':
        return render_template('tools/tool_osint_user.html', active_page='tools')
    data = request.get_json() or {}
    user = data.get('username', '').strip()
    if not user or not re.match(r'^[a-zA-Z0-9_\-]+$', user):
        return jsonify({"status": "error", "message": "Valid alphanumeric username required"}), 400

    profile_info = {
        "query_username": user,
        "registries": []
    }

    # GitHub Public Endpoint Analysis
    try:
        gh_res = requests.get(f"https://api.github.com/users/{user}", headers={'User-Agent': 'AkhilDevPlatform'}, timeout=5)
        if gh_res.status_code == 200:
            gh_data = gh_res.json()
            profile_info["registries"].append({
                "platform": "GitHub",
                "exists": True,
                "public_name": gh_data.get("name") or "Not provided",
                "bio": gh_data.get("bio") or "No bio text",
                "public_repos": gh_data.get("public_repos", 0),
                "followers": gh_data.get("followers", 0),
                "profile_url": gh_data.get("html_url"),
                "avatar_url": gh_data.get("avatar_url"),
                "location": gh_data.get("location") or "Not specified",
                "blog": gh_data.get("blog") or "None"
            })
        else:
            profile_info["registries"].append({"platform": "GitHub", "exists": False})
    except Exception:
        profile_info["registries"].append({"platform": "GitHub", "exists": "Timeout / Network Issue"})

    # Dev.to Public Endpoint Analysis
    try:
        dev_res = requests.get(f"https://dev.to/api/users/by_username?url={user}", headers={'User-Agent': 'AkhilDevPlatform'}, timeout=5)
        if dev_res.status_code == 200:
            dev_data = dev_res.json()
            profile_info["registries"].append({
                "platform": "Dev.to",
                "exists": True,
                "public_name": dev_data.get("name") or user,
                "bio": dev_data.get("summary") or "None",
                "profile_url": f"https://dev.to/{user}",
                "location": dev_data.get("location") or "Not specified"
            })
        else:
            profile_info["registries"].append({"platform": "Dev.to", "exists": False})
    except Exception:
        profile_info["registries"].append({"platform": "Dev.to", "exists": "Timeout"})

    # GitLab Public Profile Check
    try:
        gl_res = requests.get(f"https://gitlab.com/{user}", headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        profile_info["registries"].append({
            "platform": "GitLab",
            "exists": (gl_res.status_code == 200),
            "profile_url": f"https://gitlab.com/{user}"
        })
    except Exception:
        profile_info["registries"].append({"platform": "GitLab", "exists": "Timeout"})

    return jsonify({"status": "success", "data": profile_info})

# 3. ApiVault Secret Auditor & Key Generator
@interactive_bp.route('/tools/api-vault', methods=['GET', 'POST'])
def api_vault():
    if request.method == 'GET':
        return render_template('tools/tool_api_vault.html', active_page='tools')
    data = request.get_json() or {}
    key = data.get('key', '').strip()
    if not key:
        return jsonify({"status": "error", "message": "Key cannot be empty"}), 400

    # Shannon Entropy Calculation
    prob = [float(key.count(c)) / len(key) for c in dict.fromkeys(list(key))]
    entropy = - sum([p * math.log(p) / math.log(2.0) for p in prob])

    has_upper = any(c.isupper() for c in key)
    has_lower = any(c.islower() for c in key)
    has_digit = any(c.isdigit() for c in key)
    has_special = bool(re.search(r'[^a-zA-Z0-9]', key))

    strength = "High" if entropy > 3.8 and len(key) >= 24 else ("Medium" if entropy > 2.5 and len(key) >= 12 else "Weak")

    return jsonify({
        "status": "success",
        "key_length": len(key),
        "shannon_entropy_score": round(entropy, 2),
        "character_diversity": {
            "uppercase": has_upper,
            "lowercase": has_lower,
            "numeric": has_digit,
            "special_symbols": has_special
        },
        "rating": strength,
        "recommendation": "Optimal key complexity" if strength == "High" else "Use a longer string with mixed cases and symbols."
    })

# 4. Request Reverser (cURL to Python Client)
@interactive_bp.route('/tools/request-reverser', methods=['GET', 'POST'])
def request_reverser():
    if request.method == 'GET':
        return render_template('tools/tool_reverser.html', active_page='tools')
    data = request.get_json() or {}
    curl = data.get('curl', '').strip()
    if not curl:
        return jsonify({"status": "error", "message": "cURL command required"}), 400

    url_match = re.search(r"curl\s+(?:-[A-Za-z]+\s+)*['\"]?([^'\"\s]+)", curl)
    target_url = url_match.group(1) if url_match else "https://api.example.com"

    method = "GET"
    if "-X POST" in curl or "--request POST" in curl:
        method = "POST"
    elif "-X PUT" in curl or "--request PUT" in curl:
        method = "PUT"
    elif "-X DELETE" in curl or "--request DELETE" in curl:
        method = "DELETE"

    headers = re.findall(r"-H\s+['\"]([^'\"]+)['\"]", curl)
    header_dict = {}
    for h in headers:
        if ":" in h:
            k, v = h.split(":", 1)
            header_dict[k.strip()] = v.strip()

    generated_code = f"""import requests

url = "{target_url}"
headers = {header_dict if header_dict else "{'User-Agent': 'AkhilDevPlatform'}"}

response = requests.{method.lower()}(url, headers=headers)
print("Status Code:", response.status_code)
try:
    print("Response JSON:", response.json())
except Exception:
    print("Response Text:", response.text)
"""
    return jsonify({
        "status": "success",
        "target_url": target_url,
        "http_method": method,
        "detected_headers": header_dict,
        "executable_python": generated_code
    })

# 5. Playlist Metadata Generator
@interactive_bp.route('/tools/playlist-generator', methods=['GET', 'POST'])
def playlist_generator():
    if request.method == 'GET':
        return render_template('tools/tool_playlist.html', active_page='tools')
    data = request.get_json() or {}
    title = data.get('title', 'Cyber Soundscape').strip()
    raw_tracks = data.get('tracks', '').strip()
    track_list = [t.strip() for t in raw_tracks.split('\n') if t.strip()]
    if not track_list:
        track_list = [t.strip() for t in raw_tracks.split(',') if t.strip()]

    formatted = []
    for i, t in enumerate(track_list, 1):
        formatted.append({
            "track_no": f"{i:02d}",
            "title": t,
            "format": "lossless_flac",
            "bitrate": "1411 kbps"
        })

    m3u8_content = f"#EXTM3U\n#PLAYLIST:{title}\n"
    for item in formatted:
        m3u8_content += f"#EXTINF:-1,{item['title']}\n{item['title'].lower().replace(' ', '_')}.flac\n"

    return jsonify({
        "status": "success",
        "playlist_title": title,
        "total_tracks": len(formatted),
        "tracks": formatted,
        "m3u8_export": m3u8_content
    })

# 6. Domain Recon Suite
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


@interactive_bp.route('/tools/website-generator', methods=['GET', 'POST'])
def website_generator():
    if request.method == 'GET':
        return render_template('tools/tool_webgen.html', active_page='tools')
    data = request.get_json() or {}
    brand = data.get('brand', 'Akhil Cyber Studio').strip()
    tagline = data.get('tagline', 'Next-Generation AI & Security Infrastructure').strip()
    accent = data.get('accent', '#38bdf8').strip()

    generated_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{brand}</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 font-sans min-h-screen">
  <header class="border-b border-slate-800 px-6 py-4 flex justify-between items-center max-w-6xl mx-auto">
    <h1 class="text-xl font-bold tracking-wider" style="color: {accent};">{brand}</h1>
    <a href="#contact" class="px-4 py-2 rounded-lg font-semibold text-slate-950" style="background: {accent};">Get Started</a>
  </header>
  <main class="max-w-4xl mx-auto text-center py-24 px-6">
    <span class="px-3 py-1 rounded-full text-xs uppercase tracking-widest bg-slate-900 border border-slate-700" style="color: {accent};">Live Production System</span>
    <h2 class="text-5xl font-extrabold mt-6 mb-4 text-white">{tagline}</h2>
    <p class="text-slate-400 text-lg mb-8">Built with automated responsive architecture for high-speed cloud deployment.</p>
  </main>
</body>
</html>"""
    return jsonify({
        "status": "success",
        "brand": brand,
        "generated_html": generated_html
    })


# 8. Interactive Voice Studio & Waveform Workstation
@interactive_bp.route('/tools/voice-studio', methods=['GET'])
def voice_studio_workstation():
    return render_template('tools/tool_voice_studio.html', active_page='tools')

# 9. Master Prompt & Slash Command Engine
@interactive_bp.route('/tools/prompt-commander', methods=['GET', 'POST'])
def prompt_commander():
    if request.method == 'GET':
        return render_template('tools/tool_prompt_commander.html', active_page='tools')
    data = request.get_json() or {}
    cmd = data.get('command', '/debug').strip()
    topic = data.get('input_text', '').strip()
    if not topic:
        return jsonify({"status": "error", "message": "Input code or topic required"}), 400

    templates_map = {
        "/debug": f"[DEBUG DIAGNOSTIC REPORT]\nTarget Input: {topic[:120]}...\n\n1. Syntax & Runtime Verification:\n   - Check for unhandled exceptions, null pointers, and async race conditions.\n2. Root Cause Isolation:\n   - Verify API payload keys and response status codes (200 vs 4xx/5xx).\n3. Recommended Fix:\n   - Wrap network/IO calls in try-except blocks with explicit timeout parameters.",
        "/refactor": f"[CLEAN CODE REFACTOR BLUEPRINT]\nTarget Input: {topic[:120]}...\n\n1. Modularity: Extract repeated logic into pure helper functions.\n2. Naming Conventions: Enforce PEP8 (snake_case for Python) and descriptive variable identifiers.\n3. Dead Code Removal: Strip unused imports and redundant conditional branches.",
        "/optimizecode": f"[PERFORMANCE OPTIMIZATION PLAN]\nTarget Input: {topic[:120]}...\n\n1. Time Complexity: Replace nested O(n^2) loops with hash maps/dictionaries O(1) lookups.\n2. Memory Footprint: Use generators/streams instead of loading full lists in 512MB RAM containers.\n3. I/O Caching: Cache repetitive HTTP/DNS lookups in memory.",
        "/systemdesign": f"[SYSTEM ARCHITECTURE BLUEPRINT]\nProject Scope: {topic}\n\n1. Frontend Layer: Standalone Responsive HTML5 + Glassmorphism Dark UI.\n2. Application Gateway: Flask Gunicorn WSGI Worker Pool.\n3. Security Layer: SSRF Filtering, Shannon Entropy Token Auditing, Rate Limiting.\n4. Deployment Pipeline: GitHub Main Branch -> Render Cloud Container.",
        "/security": f"[DEFENSIVE SECURITY AUDIT]\nTarget Scope: {topic[:120]}...\n\n1. Input Sanitization: Validate all query/JSON payloads against command and SQL injection.\n2. Secret Protection: Store API keys in environment variables (.env), never hardcoded.\n3. Transport Security: Enforce Strict-Transport-Security (HSTS) and CSP headers.",
        "/blueprint": f"[EXECUTION BLUEPRINT & CHECKLIST]\nObjective: {topic}\n\n[x] Phase 1: Core Requirements & Route Definition\n[x] Phase 2: Backend API Endpoint & Error Handling\n[x] Phase 3: Standalone Frontend UI & Terminal Integration\n[x] Phase 4: Bytecode Compilation & Production Git Push"
    }

    output_text = templates_map.get(cmd, f"[COMMAND EXECUTION: {cmd.upper()}]\nTarget: {topic}\n\nStructured analysis generated:\n- First Principles Breakdown\n- Actionable Implementation Steps\n- Edge Case & Risk Verification")

    return jsonify({
        "status": "success",
        "command": cmd,
        "output": output_text
    })
