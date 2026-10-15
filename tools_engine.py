import zipfile
import requests
from bs4 import BeautifulSoup
from flask import Blueprint, request, jsonify, render_template

tools_bp = Blueprint('tools_bp', __name__)

@tools_bp.route('/tools/api-bridge', methods=['GET', 'POST'])
def api_bridge():
    if request.method == 'GET':
        return render_template('tool_bridge.html', active_page='tools')
    
    data = request.get_json() or {}
    target_url = data.get('url', '').strip()

    if not target_url or not (target_url.startswith('http://') or target_url.startswith('https://')):
        return jsonify({"status": "error", "message": "Valid HTTP/HTTPS URL required"}), 400

    disallowed_hosts = ['localhost', '127.0.0.1', '0.0.0.0', '169.254.169.254']
    for host in disallowed_hosts:
        if host in target_url:
            return jsonify({"status": "error", "message": "Restricted address"}), 403

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        resp = requests.get(target_url, headers=headers, timeout=8)
        
        try:
            return jsonify({"status": "success", "type": "json", "data": resp.json()})
        except Exception:
            pass

        soup = BeautifulSoup(resp.text, 'html.parser')
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        headings = [h.get_text().strip() for h in soup.find_all(['h1', 'h2']) if h.get_text().strip()]
        links = [a.get('href') for a in soup.find_all('a', href=True)][:10]

        extracted = {
            "title": title,
            "status_code": resp.status_code,
            "headings_sample": headings[:8],
            "links_sample": links
        }
        return jsonify({"status": "success", "type": "parsed_html", "data": extracted})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@tools_bp.route('/tools/apk-inspector', methods=['GET', 'POST'])
def apk_inspector():
    if request.method == 'GET':
        return render_template('tool_apk.html', active_page='tools')

    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded"}), 400

    uploaded_file = request.files['file']
    if not uploaded_file.filename.endswith('.apk'):
        return jsonify({"status": "error", "message": "Only .apk files allowed"}), 400

    try:
        with zipfile.ZipFile(uploaded_file, 'r') as z:
            file_list = z.namelist()
            dex_count = len([f for f in file_list if f.endswith('.dex')])
            res_count = len([f for f in file_list if f.startswith('res/')])
            has_manifest = 'AndroidManifest.xml' in file_list

            summary = {
                "filename": uploaded_file.filename,
                "manifest_present": has_manifest,
                "dex_files_count": dex_count,
                "resource_files_count": res_count,
                "total_files": len(file_list),
                "audit_type": "Static Read-Only Inspection"
            }
            return jsonify({"status": "success", "data": summary})

    except Exception as e:
        return jsonify({"status": "error", "message": f"Archive parsing failed: {str(e)}"}), 500
