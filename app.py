import os
import json
import time
import secrets
from flask import Flask, request, jsonify, send_from_directory, render_template_string
from flask_cors import CORS
from flask_sock import Sock
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)
sock = Sock(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEDIA_DIR = os.path.join(BASE_DIR, "media")
DATA_FILE = os.path.join(BASE_DIR, "platform_store.json")

os.makedirs(MEDIA_DIR, exist_ok=True)

def read_db():
    if not os.path.exists(DATA_FILE):
        init = {"keys": {}, "users": {}, "collections": {}}
        with open(DATA_FILE, "w") as f:
            json.dump(init, f, indent=2)
        return init
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def write_db(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

active_ws = []
def ws_broadcast(event, payload):
    data = json.dumps({"event": event, "payload": payload, "time": time.strftime("%H:%M:%S")})
    for client in active_ws[:]:
        try:
            client.send(data)
        except:
            active_ws.remove(client)

@sock.route('/ws/stream')
def realtime_stream(ws):
    active_ws.append(ws)
    ws_broadcast("CONNECT", {"online": len(active_ws)})
    try:
        while True:
            msg = ws.receive()
            if msg:
                ws_broadcast("TRANSMIT", {"data": msg})
    except:
        if ws in active_ws:
            active_ws.remove(ws)
        ws_broadcast("DISCONNECT", {"online": len(active_ws)})

@app.route('/api/system/status', methods=['GET'])
def get_status():
    return jsonify({"status": "online", "mode": "cyber_engine_active"})

@app.route('/api/admin/keys/list', methods=['GET'])
def list_keys():
    return jsonify({"keys": read_db().get("keys", {})})

@app.route('/api/admin/keys/create', methods=['POST'])
def create_key():
    req = request.get_json(silent=True) or {}
    name = req.get("app_name", "ANIME_OPERATOR")
    key = f"akhi_live_{secrets.token_urlsafe(16)}"
    db = read_db()
    db["keys"][key] = {"app": name, "created": time.strftime("%Y-%m-%d"), "hits": 0, "active": True}
    write_db(db)
    ws_broadcast("KEY_ISSUED", {"app": name})
    return jsonify({"status": "success", "key": key, "app": name})

@app.route('/api/admin/keys/toggle', methods=['POST'])
def toggle_key():
    req = request.get_json(silent=True) or {}
    k = req.get("key")
    db = read_db()
    if k in db["keys"]:
        db["keys"][k]["active"] = not db["keys"][k].get("active", True)
        write_db(db)
        return jsonify({"status": "success", "active": db["keys"][k]["active"]})
    return jsonify({"status": "error"}), 404

@app.route('/api/v1/db/<collection>', methods=['GET', 'POST'])
def db_handler(collection):
    db = read_db()
    if request.method == 'GET':
        items = db["collections"].get(collection, [])
        return jsonify({"status": "success", "collection": collection, "count": len(items), "data": items})
    
    key = request.headers.get("x-api-key") or request.args.get("api_key")
    if not key or key not in db["keys"] or not db["keys"][key].get("active"):
        return jsonify({"status": "error", "message": "Valid x-api-key required"}), 403
    
    db["keys"][key]["hits"] = db["keys"][key].get("hits", 0) + 1
    if collection not in db["collections"]:
        db["collections"][collection] = []
    
    item = {"_id": secrets.token_hex(6), "app": db["keys"][key]["app"], "time": time.strftime("%H:%M:%S"), "payload": request.get_json(silent=True) or {}}
    db["collections"][collection].append(item)
    write_db(db)
    ws_broadcast("DATA_SAVED", {"collection": collection, "item": item})
    return jsonify({"status": "success", "item": item})

@app.route('/api/v1/media/upload', methods=['POST'])
def media_upload():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No binary payload received"}), 400
    f = request.files['file']
    s_name = f"{int(time.time())}_{secrets.token_hex(3)}_{secure_filename(f.filename)}"
    f.save(os.path.join(MEDIA_DIR, s_name))
    ws_broadcast("MEDIA_UPLOADED", {"file": s_name})
    return jsonify({"status": "success", "url": f"/media/{s_name}"})

@app.route('/media/<path:fname>')
def media_serve(fname):
    return send_from_directory(MEDIA_DIR, secure_filename(fname))

# ========================================================
# 1. SEPARATE PAGE: GET API KEY GENERATION PORTAL (/portal/keys)
# ========================================================
@app.route('/portal/keys')
def key_provision_portal():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Akhi // Security Key Terminal</title>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg: #030611;
                --panel: rgba(10, 16, 30, 0.85);
                --cyan: #38bdf8;
                --purple: #c084fc;
                --neon-border: rgba(56, 189, 248, 0.3);
            }
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }
            body {
                background: radial-gradient(circle at 50% 10%, rgba(192, 132, 252, 0.15), transparent 60%),
                            radial-gradient(circle at 10% 90%, rgba(56, 189, 248, 0.1), transparent 50%), var(--bg);
                color: #f8fafc; min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px;
            }
            .hud-card {
                background: var(--panel); backdrop-filter: blur(20px); border: 1px solid var(--neon-border);
                border-radius: 20px; max-width: 480px; width: 100%; padding: 30px; box-shadow: 0 0 50px rgba(56, 189, 248, 0.15);
                position: relative; overflow: hidden;
            }
            .hud-card::before {
                content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
                background: linear-gradient(90deg, var(--cyan), var(--purple));
            }
            .badge-top { display: inline-flex; align-items: center; gap: 8px; font-size: 11px; font-family: 'JetBrains Mono'; text-transform: uppercase; color: var(--cyan); margin-bottom: 12px; }
            h1 { font-size: 22px; font-weight: 700; margin-bottom: 8px; letter-spacing: -0.5px; }
            p { font-size: 13px; color: #94a3b8; line-height: 1.5; margin-bottom: 24px; }
            input {
                width: 100%; background: rgba(3, 7, 18, 0.7); border: 1px solid rgba(255,255,255,0.12);
                border-radius: 10px; padding: 13px 16px; color: #fff; font-size: 14px; outline: none; margin-bottom: 16px;
            }
            input:focus { border-color: var(--cyan); box-shadow: 0 0 15px rgba(56, 189, 248, 0.3); }
            button {
                width: 100%; background: linear-gradient(135deg, var(--cyan), #0284c7); color: #030712;
                font-weight: 700; padding: 13px; border: none; border-radius: 10px; cursor: pointer; font-size: 13px;
                text-transform: uppercase; letter-spacing: 1px; transition: 0.2s;
            }
            button:active { transform: scale(0.98); }
            .token-result {
                margin-top: 20px; background: rgba(2, 6, 23, 0.8); border: 1px solid var(--neon-border);
                border-radius: 12px; padding: 16px; display: none;
            }
            .token-text { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--purple); word-break: break-all; margin: 10px 0; }
            .copy-btn {
                background: rgba(192, 132, 252, 0.15); border: 1px solid var(--purple); color: var(--purple);
                padding: 8px 12px; border-radius: 6px; font-size: 11px; width: auto; font-family: 'JetBrains Mono';
            }
        </style>
    </head>
    <body>
        <div class="hud-card">
            <div class="badge-top">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
                Identity Authorization Gateway
            </div>
            <h1>Generate Digital API Pass</h1>
            <p>Deploy secure cryptographic credentials for client systems, mobile applications, or game engine integration.</p>
            
            <input type="text" id="appName" placeholder="System ID / App Name (e.g. AnimeCore)">
            <button onclick="issueToken()">Authorize & Issue Pass</button>

            <div id="tokenBox" class="token-result">
                <div style="font-size: 11px; color:#94a3b8; font-family:'JetBrains Mono';">SECURE ACCESS TOKEN:</div>
                <div class="token-text" id="tokenDisplay"></div>
                <button class="copy-btn" onclick="copyToken()">Copy Pass</button>
            </div>
        </div>

        <script>
            async function issueToken() {
                const n = document.getElementById("appName").value.trim();
                if (!n) return alert("System ID name required");
                const res = await fetch('/api/admin/keys/create', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({app_name: n})
                });
                const d = await res.json();
                if (d.status === "success") {
                    document.getElementById("tokenDisplay").innerText = d.key;
                    document.getElementById("tokenBox").style.display = "block";
                }
            }
            function copyToken() {
                navigator.clipboard.writeText(document.getElementById("tokenDisplay").innerText);
                alert("Cryptographic token copied.");
            }
        </script>
    </body>
    </html>
    """)

# ========================================================
# 2. MAIN REMAKE: CYBER-ANIME ARCHITECT HUD (ROOT /)
# ========================================================
@app.route('/')
def architect_console():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AKHI // ARCHITECT • Cyber Engine</title>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg: #030611;
                --panel: rgba(11, 18, 33, 0.75);
                --cyan: #38bdf8;
                --purple: #c084fc;
                --green: #34d399;
                --red: #f87171;
                --border: rgba(56, 189, 248, 0.18);
            }
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }
            body {
                background: radial-gradient(circle at 10% 10%, rgba(192, 132, 252, 0.12), transparent 40%),
                            radial-gradient(circle at 90% 90%, rgba(56, 189, 248, 0.12), transparent 40%), var(--bg);
                color: #f1f5f9; min-height: 100vh; padding: 20px;
            }
            .hud-layout { max-width: 1200px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; }
            
            /* TOP NAV */
            .navbar {
                background: var(--panel); backdrop-filter: blur(16px); border: 1px solid var(--border);
                border-radius: 16px; padding: 14px 22px; display: flex; justify-content: space-between; align-items: center;
            }
            .brand { display: flex; align-items: center; gap: 12px; font-weight: 700; font-size: 16px; letter-spacing: 1px; }
            .brand-shield {
                width: 32px; height: 32px; border-radius: 8px; background: linear-gradient(135deg, var(--cyan), var(--purple));
                display: grid; place-items: center; box-shadow: 0 0 16px rgba(56, 189, 248, 0.4);
            }
            .nav-btn-link {
                text-decoration: none; font-size: 12px; font-weight: 700; padding: 8px 14px; border-radius: 8px;
                display: flex; align-items: center; gap: 8px; transition: 0.2s;
                background: rgba(192, 132, 252, 0.12); border: 1px solid rgba(192, 132, 252, 0.4); color: var(--purple);
            }
            .nav-btn-link:hover { background: rgba(192, 132, 252, 0.25); box-shadow: 0 0 15px rgba(192, 132, 252, 0.3); }

            /* HUD METRICS */
            .metric-bar { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; }
            .metric-card { background: var(--panel); border: 1px solid var(--border); border-radius: 14px; padding: 16px; }
            .metric-card .title { font-size: 11px; font-family: 'JetBrains Mono'; text-transform: uppercase; color: #94a3b8; }
            .metric-card .val { font-size: 22px; font-weight: 700; color: #fff; margin-top: 4px; font-family: 'JetBrains Mono'; }

            /* MULTI-VIEW HUD TABS */
            .view-selector { display: flex; gap: 10px; background: rgba(0,0,0,0.4); padding: 5px; border-radius: 12px; border: 1px solid var(--border); }
            .hud-tab {
                flex: 1; background: transparent; border: none; color: #94a3b8; padding: 10px; border-radius: 8px;
                font-weight: 600; font-size: 13px; cursor: pointer; display: flex; justify-content: center; align-items: center; gap: 8px;
                transition: 0.2s;
            }
            .hud-tab.active { background: linear-gradient(135deg, var(--cyan), #0284c7); color: #000; font-weight: 700; box-shadow: 0 0 15px rgba(56,189,248,0.4); }

            /* PANELS */
            .panel-container { display: none; }
            .panel-container.active { display: block; }
            .hud-glass-card { background: var(--panel); backdrop-filter: blur(14px); border: 1px solid var(--border); border-radius: 16px; padding: 22px; }
            
            .two-col { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
            @media(max-width: 900px) { .two-col { grid-template-columns: 1fr; } }

            /* TABLE */
            .table-wrap { overflow-x: auto; border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; }
            table { width: 100%; border-collapse: collapse; font-size: 12px; }
            th { text-align: left; padding: 12px; background: rgba(255,255,255,0.02); color: #94a3b8; font-family: 'JetBrains Mono'; border-bottom: 1px solid rgba(255,255,255,0.06); }
            td { padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.04); }
            .code-tag { font-family: 'JetBrains Mono'; font-size: 11px; color: var(--cyan); background: rgba(56, 189, 248, 0.08); padding: 4px 8px; border-radius: 6px; }

            /* TERMINAL */
            .term-hud { background: #01040a; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; height: 340px; padding: 14px; overflow-y: auto; font-family: 'JetBrains Mono'; font-size: 11px; }
            .log-line { margin-bottom: 8px; word-break: break-all; }
            .log-time { color: #64748b; margin-right: 6px; }
            .log-ev { color: var(--purple); font-weight: bold; }

            /* INPUTS */
            input {
                background: rgba(0, 0, 0, 0.5); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px;
                padding: 10px 14px; color: #fff; font-size: 13px; outline: none; width: 100%;
            }
            input:focus { border-color: var(--cyan); }
            .btn-hud { background: linear-gradient(135deg, var(--cyan), #0284c7); border: none; color: #000; font-weight: 700; padding: 10px 16px; border-radius: 8px; cursor: pointer; font-size: 12px; }
        </style>
    </head>
    <body>
        <div class="hud-layout">
            <!-- TOP BAR -->
            <div class="navbar">
                <div class="brand">
                    <div class="brand-shield">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#000" stroke-width="2.5"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>
                    </div>
                    <span>AKHI<span style="color:var(--cyan)">.CLOUD</span> // ENGINE CORE</span>
                </div>
                
                <!-- SEPARATE PAGE BUTTON -->
                <a href="/portal/keys" target="_blank" class="nav-btn-link">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"></path></svg>
                    Get API Key ↗
                </a>
            </div>

            <!-- METRIC HUD -->
            <div class="metric-bar">
                <div class="metric-card"><div class="title">Cloud Engine</div><div class="val" style="color:var(--green);">ONLINE</div></div>
                <div class="metric-card"><div class="title">Issued Passes</div><div class="val" id="statKeys">0</div></div>
                <div class="metric-card"><div class="title">Realtime Sockets</div><div class="val" id="statSockets">1</div></div>
                <div class="metric-card"><div class="title">Media Vault</div><div class="val" style="color:var(--purple);">ACTIVE</div></div>
            </div>

            <!-- MULTI-PAGE TAB CONTROLS -->
            <div class="view-selector">
                <button class="hud-tab active" onclick="switchHUD('keysView')">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
                    Pass Management & Telemetry
                </button>
                <button class="hud-tab" onclick="switchHUD('sandboxView')">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>
                    Live Operations Sandbox
                </button>
            </div>

            <!-- VIEW 1: KEYS & TELEMETRY -->
            <div id="keysView" class="panel-container active">
                <div class="two-col">
                    <div class="hud-glass-card">
                        <div style="font-size:14px; font-weight:700; color:var(--cyan); margin-bottom:14px; text-transform:uppercase;">
                            Active Digital Passes
                        </div>
                        <div class="table-wrap">
                            <table>
                                <thead><tr><th>Application</th><th>Access Token</th><th>Hits</th><th>Status</th><th>Control</th></tr></thead>
                                <tbody id="keysList"></tbody>
                            </table>
                        </div>
                    </div>

                    <div class="hud-glass-card">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                            <span style="font-size:13px; font-weight:700; color:var(--purple); text-transform:uppercase;">Live Telemetry</span>
                            <span style="font-size:10px; color:var(--green); font-family:'JetBrains Mono';">● CONNECTED</span>
                        </div>
                        <div class="term-hud" id="termLogs"></div>
                    </div>
                </div>
            </div>

            <!-- VIEW 2: DIRECT SANDBOX OPERATIONS -->
            <div id="sandboxView" class="panel-container">
                <div class="hud-glass-card" style="display:flex; flex-direction:column; gap:16px;">
                    <div style="font-size:14px; font-weight:700; color:var(--cyan); text-transform:uppercase;">Manual Cloud Operations</div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                        <input type="text" id="sandKey" placeholder="Paste x-api-key">
                        <input type="text" id="sandCol" value="project_data" placeholder="Target Collection">
                    </div>
                    <div style="display:flex; gap:10px;">
                        <input type="text" id="sandJson" placeholder='{"operator": "cyber", "rank": 1}'>
                        <button class="btn-hud" onclick="execDB()">Commit Data</button>
                    </div>
                    <div style="display:flex; gap:10px; align-items:center; border-top:1px solid rgba(255,255,255,0.06); padding-top:14px;">
                        <input type="file" id="sandFile">
                        <button class="btn-hud" onclick="execUpload()">Transmit Media</button>
                    </div>
                    <div id="sandOutput" style="font-family:'JetBrains Mono'; font-size:12px; color:var(--cyan);"></div>
                </div>
            </div>
        </div>

        <script>
            function switchHUD(id) {
                document.querySelectorAll('.hud-tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.panel-container').forEach(p => p.classList.remove('active'));
                if(id === 'keysView') document.querySelectorAll('.hud-tab')[0].classList.add('active');
                else document.querySelectorAll('.hud-tab')[1].classList.add('active');
                document.getElementById(id).classList.add('active');
            }

            const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
            const ws = new WebSocket(`${proto}//${location.host}/ws/stream`);
            const term = document.getElementById("termLogs");

            ws.onmessage = (e) => {
                const d = JSON.parse(e.data);
                const el = document.createElement("div");
                el.className = "log-line";
                el.innerHTML = `<span class="log-time">[${d.time}]</span> <span class="log-ev">${d.event}</span>: <span>${JSON.stringify(d.payload || '')}</span>`;
                term.appendChild(el);
                term.scrollTop = term.scrollHeight;
            };

            async function syncKeys() {
                const res = await fetch('/api/admin/keys/list');
                const data = await res.json();
                const tb = document.getElementById("keysList");
                tb.innerHTML = "";
                let count = 0;
                for (let k in data.keys) {
                    count++;
                    const item = data.keys[k];
                    tb.innerHTML += `<tr>
                        <td><b>${item.app}</b></td>
                        <td><span class="code-tag">${k}</span></td>
                        <td>${item.hits || 0}</td>
                        <td style="color:${item.active ? 'var(--green)' : 'var(--red)'}">${item.active ? 'ACTIVE' : 'REVOKED'}</td>
                        <td><button style="background:${item.active ? 'rgba(248,113,113,0.2)' : 'rgba(52,211,153,0.2)'}; color:${item.active ? 'var(--red)' : 'var(--green)'}; border:none; padding:4px 8px; border-radius:6px; font-size:11px; cursor:pointer;" onclick="toggleKey('${k}')">${item.active ? 'Revoke' : 'Allow'}</button></td>
                    </tr>`;
                }
                document.getElementById("statKeys").innerText = count;
            }

            async function toggleKey(k) {
                await fetch('/api/admin/keys/toggle', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({key: k})
                });
                syncKeys();
            }

            async function execDB() {
                const k = document.getElementById("sandKey").value.trim();
                const col = document.getElementById("sandCol").value.trim();
                const payload = document.getElementById("sandJson").value || '{}';
                const res = await fetch(`/api/v1/db/${col}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'x-api-key': k},
                    body: payload
                });
                const d = await res.json();
                document.getElementById("sandOutput").innerText = d.status === "success" ? `SUCCESS // ID: ${d.item._id}` : `ERROR // ${d.message}`;
            }

            async function execUpload() {
                const f = document.getElementById("sandFile").files[0];
                if (!f) return alert("Select a file");
                const fd = new FormData();
                fd.append("file", f);
                const res = await fetch('/api/v1/media/upload', {method: 'POST', body: fd});
                const d = await res.json();
                document.getElementById("sandOutput").innerText = d.status === "success" ? `MEDIA_STORED // ${d.url}` : `UPLOAD_FAIL`;
            }

            syncKeys();
        </script>
    </body>
    </html>
    """)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
