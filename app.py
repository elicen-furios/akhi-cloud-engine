import os
import json
import time
import secrets
from flask import Flask, request, jsonify, send_from_directory, render_template_string
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEDIA_DIR = os.path.join(BASE_DIR, "media")
DATA_FILE = os.path.join(BASE_DIR, "platform_store.json")

os.makedirs(MEDIA_DIR, exist_ok=True)

def read_db():
    if not os.path.exists(DATA_FILE):
        init = {"keys": {}, "collections": {}}
        try:
            with open(DATA_FILE, "w") as f:
                json.dump(init, f, indent=2)
        except Exception:
            pass
        return init
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"keys": {}, "collections": {}}

def write_db(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

@app.route('/api/system/status', methods=['GET'])
def get_status():
    return jsonify({
        "status": "operational",
        "engine": "Akhi Unified Cloud Fabric",
        "protocol": "HTTP/1.1 REST",
        "cluster": "Europe-Frankfurt (Render Edge)"
    })

@app.route('/api/admin/keys/list', methods=['GET'])
def list_keys():
    return jsonify({"keys": read_db().get("keys", {})})

@app.route('/api/admin/keys/create', methods=['POST'])
def create_key():
    req = request.get_json(silent=True) or {}
    name = req.get("app_name", "Primary Client Engine").strip() or "Unnamed Integration"
    env = req.get("environment", "Production")
    key = f"akhi_live_{secrets.token_urlsafe(16)}"
    db = read_db()
    db.setdefault("keys", {})[key] = {
        "app": name,
        "environment": env,
        "created": time.strftime("%Y-%m-%d %H:%M"),
        "hits": 0,
        "active": True
    }
    write_db(db)
    return jsonify({"status": "success", "key": key, "app": name, "environment": env})

@app.route('/api/admin/keys/toggle', methods=['POST'])
def toggle_key():
    req = request.get_json(silent=True) or {}
    k = req.get("key")
    db = read_db()
    if k in db.get("keys", {}):
        db["keys"][k]["active"] = not db["keys"][k].get("active", True)
        write_db(db)
        return jsonify({"status": "success", "active": db["keys"][k]["active"]})
    return jsonify({"status": "error", "message": "Key identifier not found"}), 404

@app.route('/api/v1/db/<collection>', methods=['GET', 'POST'])
def db_handler(collection):
    db = read_db()
    db.setdefault("collections", {})
    if request.method == 'GET':
        items = db["collections"].get(collection, [])
        return jsonify({
            "status": "success",
            "collection": collection,
            "total_records": len(items),
            "data": items
        })
    
    key = request.headers.get("x-api-key") or request.args.get("api_key")
    keys = db.get("keys", {})
    if not key or key not in keys or not keys[key].get("active"):
        return jsonify({
            "status": "unauthorized",
            "error_code": "INVALID_X_API_KEY",
            "message": "Access denied. Valid cryptographic pass required via 'x-api-key' header."
        }), 403
    
    keys[key]["hits"] = keys[key].get("hits", 0) + 1
    if collection not in db["collections"]:
        db["collections"][collection] = []
    
    payload = request.get_json(silent=True) or {}
    record = {
        "_id": secrets.token_hex(6),
        "origin_app": keys[key].get("app", "Client"),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "payload": payload
    }
    db["collections"][collection].append(record)
    write_db(db)
    return jsonify({"status": "success", "record": record})

@app.route('/api/v1/media/upload', methods=['POST'])
def media_upload():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No binary multipart file detected"}), 400
    f = request.files['file']
    s_name = f"{int(time.time())}_{secrets.token_hex(4)}_{secure_filename(f.filename)}"
    f.save(os.path.join(MEDIA_DIR, s_name))
    return jsonify({"status": "success", "asset_id": s_name, "url": f"/media/{s_name}"})

@app.route('/media/<path:fname>')
def media_serve(fname):
    return send_from_directory(MEDIA_DIR, secure_filename(fname))

# ========================================================
# STANDALONE KEY PROVISIONING TERMINAL (/portal/keys)
# ========================================================
@app.route('/portal/keys')
def key_provision_portal():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Identity & Access Provisioning • Akhi Cloud</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg: #07090f;
                --panel: rgba(14, 20, 36, 0.7);
                --border: rgba(255, 255, 255, 0.08);
                --border-highlight: rgba(56, 189, 248, 0.35);
                --cyan: #38bdf8;
                --text-main: #f1f5f9;
                --text-muted: #94a3b8;
            }
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }
            body {
                background: radial-gradient(circle at 50% 0%, rgba(56, 189, 248, 0.12), transparent 50%), var(--bg);
                color: var(--text-main); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 24px;
            }
            .card {
                background: var(--panel); backdrop-filter: blur(24px); border: 1px solid var(--border);
                border-radius: 20px; max-width: 520px; width: 100%; padding: 36px; box-shadow: 0 20px 50px rgba(0,0,0,0.6);
            }
            .breadcrumb { display: flex; align-items: center; gap: 8px; font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; color: var(--cyan); margin-bottom: 16px; font-weight: 700; }
            h1 { font-size: 26px; font-weight: 800; letter-spacing: -0.5px; margin-bottom: 10px; }
            p { font-size: 14px; color: var(--text-muted); line-height: 1.6; margin-bottom: 24px; }
            .form-group { margin-bottom: 18px; display: flex; flex-direction: column; gap: 6px; }
            label { font-size: 12px; font-weight: 600; color: #cbd5e1; }
            input, select {
                background: rgba(3, 7, 18, 0.7); border: 1px solid var(--border); border-radius: 10px;
                padding: 13px 16px; color: #fff; font-size: 14px; outline: none; transition: all 0.2s;
            }
            input:focus, select:focus { border-color: var(--border-highlight); box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.15); }
            button {
                background: linear-gradient(135deg, #38bdf8, #0284c7); color: #020617; font-weight: 700;
                padding: 14px; border: none; border-radius: 10px; cursor: pointer; font-size: 14px;
                letter-spacing: 0.5px; width: 100%; transition: opacity 0.2s; margin-top: 8px;
            }
            button:hover { opacity: 0.95; }
            .result-container {
                margin-top: 24px; background: rgba(3, 7, 18, 0.85); border: 1px solid var(--border-highlight);
                border-radius: 12px; padding: 18px; display: none;
            }
            .token-view {
                font-family: 'JetBrains Mono', monospace; font-size: 13px; color: var(--cyan);
                background: rgba(56, 189, 248, 0.08); padding: 12px; border-radius: 8px; margin: 10px 0; word-break: break-all;
            }
            .copy-btn {
                background: transparent; border: 1px solid var(--border); color: #cbd5e1; padding: 8px 14px;
                border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; width: auto; margin: 0;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="breadcrumb">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
                Access Control Module
            </div>
            <h1>Generate Client Token</h1>
            <p>Provision a cryptographically signed digital pass. This key grants authorized write privilege to your backend database and media pipeline.</p>
            
            <div class="form-group">
                <label>Integration / Application Name</label>
                <input type="text" id="appName" placeholder="e.g. AnimeStudio Web Client">
            </div>
            <div class="form-group">
                <label>Environment Scope</label>
                <select id="appEnv">
                    <option value="Production">Production Instance</option>
                    <option value="Staging">Staging & Testing</option>
                    <option value="Development">Local Development</option>
                </select>
            </div>
            <button onclick="generateToken()">Issue Access Token</button>

            <div id="resultBox" class="result-container">
                <div style="font-size:11px; text-transform:uppercase; letter-spacing:1px; color:var(--text-muted); font-weight:600;">Cryptographic Key Generated</div>
                <div class="token-view" id="tokenOutput"></div>
                <button class="copy-btn" onclick="copyToken()">Copy Token to Clipboard</button>
            </div>
        </div>

        <script>
            async function generateToken() {
                const name = document.getElementById("appName").value.trim();
                const env = document.getElementById("appEnv").value;
                if (!name) return alert("Please specify an integration name.");
                const res = await fetch('/api/admin/keys/create', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ app_name: name, environment: env })
                });
                const d = await res.json();
                if (d.status === "success") {
                    document.getElementById("tokenOutput").innerText = d.key;
                    document.getElementById("resultBox").style.display = "block";
                }
            }
            function copyToken() {
                navigator.clipboard.writeText(document.getElementById("tokenOutput").innerText);
                alert("Pass copied to clipboard.");
            }
        </script>
    </body>
    </html>
    """)

# ========================================================
# MAIN DEVELOPER PLATFORM & ARCHITECTURE INTERFACE (ROOT /)
# ========================================================
@app.route('/')
def main_developer_hub():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Akhi Cloud • Developer Infrastructure Platform</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg: #07090f;
                --panel: rgba(14, 20, 36, 0.65);
                --border: rgba(255, 255, 255, 0.08);
                --cyan: #38bdf8;
                --purple: #a855f7;
                --green: #34d399;
                --red: #f87171;
                --text-main: #f8fafc;
                --text-muted: #94a3b8;
            }
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }
            body {
                background: radial-gradient(circle at 15% 10%, rgba(56, 189, 248, 0.08), transparent 40%),
                            radial-gradient(circle at 85% 90%, rgba(168, 85, 247, 0.08), transparent 40%), var(--bg);
                color: var(--text-main); min-height: 100vh; padding: 24px;
            }
            .app-wrapper { max-width: 1240px; margin: 0 auto; display: flex; flex-direction: column; gap: 32px; }
            
            /* NAVIGATION HEADER */
            .header-bar {
                background: var(--panel); backdrop-filter: blur(20px); border: 1px solid var(--border);
                border-radius: 18px; padding: 16px 28px; display: flex; justify-content: space-between; align-items: center;
            }
            .brand-group { display: flex; align-items: center; gap: 14px; font-weight: 800; font-size: 17px; }
            .brand-emblem {
                width: 36px; height: 36px; border-radius: 10px; background: linear-gradient(135deg, var(--cyan), #2563eb);
                display: grid; place-items: center; box-shadow: 0 0 20px rgba(56, 189, 248, 0.35);
            }
            .header-actions { display: flex; align-items: center; gap: 12px; }
            .btn-portal {
                text-decoration: none; font-size: 13px; font-weight: 700; padding: 10px 18px; border-radius: 10px;
                background: rgba(56, 189, 248, 0.12); border: 1px solid rgba(56, 189, 248, 0.3); color: var(--cyan);
                display: inline-flex; align-items: center; gap: 8px; transition: all 0.2s;
            }
            .btn-portal:hover { background: rgba(56, 189, 248, 0.22); }

            /* HERO INTRO */
            .hero-section {
                padding: 20px 8px; display: flex; flex-direction: column; gap: 12px; max-width: 780px;
            }
            .hero-tag { font-size: 12px; text-transform: uppercase; letter-spacing: 2px; color: var(--cyan); font-weight: 700; }
            .hero-heading { font-size: 34px; font-weight: 800; line-height: 1.25; letter-spacing: -0.5px; }
            .hero-desc { font-size: 15px; color: var(--text-muted); line-height: 1.6; }

            /* METRIC STRIP */
            .metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }
            .metric-card {
                background: var(--panel); border: 1px solid var(--border); border-radius: 14px; padding: 20px;
                display: flex; flex-direction: column; gap: 6px;
            }
            .metric-card .caption { font-size: 11px; font-family: 'JetBrains Mono'; text-transform: uppercase; color: var(--text-muted); }
            .metric-card .value { font-size: 24px; font-weight: 800; font-family: 'JetBrains Mono'; }

            /* MAIN SECTION TABS */
            .tab-nav {
                display: flex; gap: 8px; background: rgba(3, 7, 18, 0.6); padding: 6px; border-radius: 12px;
                border: 1px solid var(--border); width: fit-content;
            }
            .tab-btn {
                background: transparent; border: none; color: var(--text-muted); padding: 10px 20px; border-radius: 8px;
                font-size: 13px; font-weight: 600; cursor: pointer; transition: 0.2s;
            }
            .tab-btn.active { background: rgba(255, 255, 255, 0.08); color: #fff; }

            .tab-pane { display: none; }
            .tab-pane.active { display: block; }

            /* CARDS & TABLES */
            .content-card {
                background: var(--panel); backdrop-filter: blur(16px); border: 1px solid var(--border);
                border-radius: 18px; padding: 26px; display: flex; flex-direction: column; gap: 20px;
            }
            .card-title-group { display: flex; justify-content: space-between; align-items: center; }
            .card-title { font-size: 16px; font-weight: 700; letter-spacing: -0.2px; }

            .table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 12px; }
            table { width: 100%; border-collapse: collapse; font-size: 13px; }
            th { text-align: left; padding: 14px 16px; background: rgba(255,255,255,0.02); color: var(--text-muted); font-weight: 600; border-bottom: 1px solid var(--border); }
            td { padding: 14px 16px; border-bottom: 1px solid rgba(255,255,255,0.04); }
            .token-badge { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--cyan); background: rgba(56, 189, 248, 0.08); padding: 4px 8px; border-radius: 6px; }

            /* DOCUMENTATION CODE BLOCKS */
            .code-sample {
                background: #020612; border: 1px solid var(--border); border-radius: 12px; padding: 16px;
                font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #cbd5e1; line-height: 1.6;
                overflow-x: auto;
            }
            .code-comment { color: #64748b; }
            .code-keyword { color: var(--cyan); }
            .code-str { color: var(--green); }
        </style>
    </head>
    <body>
        <div class="app-wrapper">
            <!-- HEADER -->
            <div class="header-bar">
                <div class="brand-group">
                    <div class="brand-emblem">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>
                    </div>
                    <span>AKHI<span style="color:var(--cyan);">.CLOUD</span> CORE</span>
                </div>
                
                <div class="header-actions">
                    <a href="/portal/keys" target="_blank" class="btn-portal">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"></path></svg>
                        Get API Key ↗
                    </a>
                </div>
            </div>

            <!-- HERO INFORMATION -->
            <div class="hero-section">
                <div class="hero-tag">Cloud Native Infrastructure</div>
                <h1 class="hero-heading">High-Performance Backend Fabric for Modern Client Applications</h1>
                <p class="hero-desc">
                    A multi-tenant REST database, media ingestion vault, and key-gated access layer running 24/7 on Frankfurt cloud compute. Connect any web client, mobile application, or automation pipeline using cryptographic digital passes.
                </p>
            </div>

            <!-- METRICS -->
            <div class="metric-grid">
                <div class="metric-card">
                    <span class="caption">System Cluster</span>
                    <span class="value" style="color:var(--green);">ONLINE 24/7</span>
                </div>
                <div class="metric-card">
                    <span class="caption">Registered Passes</span>
                    <span class="value" id="statKeys">0</span>
                </div>
                <div class="metric-card">
                    <span class="caption">Architecture Protocol</span>
                    <span class="value" style="color:var(--cyan);">REST / JSON</span>
                </div>
                <div class="metric-card">
                    <span class="caption">Media Vault</span>
                    <span class="value" style="color:var(--purple);">ACTIVE</span>
                </div>
            </div>

            <!-- TABS -->
            <div class="tab-nav">
                <button class="tab-btn active" onclick="switchTab('passesTab')">Active Key Management</button>
                <button class="tab-btn" onclick="switchTab('docsTab')">API Integration Guide</button>
            </div>

            <!-- TAB 1: PASS MANAGEMENT -->
            <div id="passesTab" class="tab-pane active">
                <div class="content-card">
                    <div class="card-title-group">
                        <span class="card-title">Provisioned Digital Tokens</span>
                        <span style="font-size:12px; color:var(--text-muted);">Scoped Cryptographic Gating</span>
                    </div>
                    <div class="table-wrap">
                        <table>
                            <thead>
                                <tr>
                                    <th>Application</th>
                                    <th>Environment</th>
                                    <th>Digital Pass</th>
                                    <th>Hits</th>
                                    <th>Status</th>
                                    <th>Revocation</th>
                                </tr>
                            </thead>
                            <tbody id="keysTable"></tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- TAB 2: DEVELOPER DOCUMENTATION -->
            <div id="docsTab" class="tab-pane">
                <div class="content-card">
                    <div class="card-title">How Client Applications Connect</div>
                    <p style="font-size:14px; color:var(--text-muted); line-height:1.6;">
                        Your frontend client talks directly to this backend using standard HTTPS requests. Supply your issued token via the <code>x-api-key</code> header to persist data to the cloud database.
                    </p>

                    <div style="font-size:13px; font-weight:700; color:var(--cyan);">JavaScript / Web Client Example</div>
                    <div class="code-sample">
<span class="code-comment">// Storing data into collection 'users'</span>
<span class="code-keyword">await</span> fetch(<span class="code-str">'https://akhil-private-backend.onrender.com/api/v1/db/users'</span>, {
    method: <span class="code-str">'POST'</span>,
    headers: {
        <span class="code-str">'Content-Type'</span>: <span class="code-str">'application/json'</span>,
        <span class="code-str">'x-api-key'</span>: <span class="code-str">'YOUR_GENERATED_KEY'</span>
    },
    body: JSON.stringify({
        player_name: <span class="code-str">"Ren"</span>,
        score: 1540
    })
});
                    </div>
                </div>
            </div>
        </div>

        <script>
            function switchTab(id) {
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
                if (id === 'passesTab') document.querySelectorAll('.tab-btn')[0].classList.add('active');
                else document.querySelectorAll('.tab-btn')[1].classList.add('active');
                document.getElementById(id).classList.add('active');
            }

            async function syncKeyTable() {
                const res = await fetch('/api/admin/keys/list');
                const data = await res.json();
                const tb = document.getElementById("keysTable");
                tb.innerHTML = "";
                let count = 0;
                for (let k in data.keys) {
                    count++;
                    const item = data.keys[k];
                    tb.innerHTML += `<tr>
                        <td><b>${item.app}</b></td>
                        <td style="color:var(--text-muted);">${item.environment || 'Production'}</td>
                        <td><span class="token-badge">${k}</span></td>
                        <td>${item.hits || 0}</td>
                        <td style="color:${item.active ? 'var(--green)' : 'var(--red)'}; font-weight:600;">${item.active ? 'ACTIVE' : 'REVOKED'}</td>
                        <td>
                            <button style="background:transparent; border:1px solid var(--border); color:${item.active ? 'var(--red)' : 'var(--green)'}; padding:6px 12px; border-radius:6px; font-size:11px; cursor:pointer;" onclick="toggleKey('${k}')">
                                ${item.active ? 'Revoke Access' : 'Re-enable'}
                            </button>
                        </td>
                    </tr>`;
                }
                document.getElementById("statKeys").innerText = count;
            }

            async function toggleKey(k) {
                await fetch('/api/admin/keys/toggle', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ key: k })
                });
                syncKeyTable();
            }

            syncKeyTable();
        </script>
    </body>
    </html>
    """)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
