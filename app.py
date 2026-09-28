import os
import json
import time
import secrets
import hashlib
from flask import Flask, request, jsonify, send_from_directory, render_template_string
from flask_cors import CORS
from flask_sock import Sock
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)
sock = Sock(app)

# Cloud native storage path (No /sdcard)
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
                ws_broadcast("BROADCAST", {"body": msg})
    except:
        if ws in active_ws:
            active_ws.remove(ws)
        ws_broadcast("DISCONNECT", {"online": len(active_ws)})

@app.route('/api/system/status', methods=['GET'])
def get_status():
    return jsonify({"status": "online", "mode": "cloud_native_24x7"})

@app.route('/api/admin/keys/list', methods=['GET'])
def list_keys():
    return jsonify({"keys": read_db().get("keys", {})})

@app.route('/api/admin/keys/create', methods=['POST'])
def create_key():
    req = request.get_json(silent=True) or {}
    name = req.get("app_name", "Untitled")
    key = f"akhi_live_{secrets.token_urlsafe(16)}"
    db = read_db()
    db["keys"][key] = {"app": name, "created": time.strftime("%Y-%m-%d"), "hits": 0, "active": True}
    write_db(db)
    ws_broadcast("KEY_NEW", {"app": name})
    return jsonify({"status": "success", "key": key})

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
    ws_broadcast("DATA_INSERT", {"collection": collection, "item": item})
    return jsonify({"status": "success", "item": item})

@app.route('/api/v1/media/upload', methods=['POST'])
def media_upload():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded"}), 400
    f = request.files['file']
    s_name = f"{int(time.time())}_{secrets.token_hex(3)}_{secure_filename(f.filename)}"
    f.save(os.path.join(MEDIA_DIR, s_name))
    ws_broadcast("MEDIA_UPLOAD", {"file": s_name})
    return jsonify({"status": "success", "url": f"/media/{s_name}"})

@app.route('/media/<path:fname>')
def media_serve(fname):
    return send_from_directory(MEDIA_DIR, secure_filename(fname))

@app.route('/')
def modern_console():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Akhi Cloud • Developer Console</title>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg: #07090e; --panel: rgba(16, 22, 34, 0.7); --border: rgba(255, 255, 255, 0.08);
                --border-focus: rgba(56, 189, 248, 0.4); --primary: #38bdf8; --accent: #818cf8;
                --success: #34d399; --danger: #f87171; --text: #f8fafc; --muted: #94a3b8;
            }
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }
            body {
                background: radial-gradient(circle at 10% 20%, rgba(56, 189, 248, 0.05) 0%, transparent 40%),
                            radial-gradient(circle at 90% 80%, rgba(129, 140, 248, 0.05) 0%, transparent 40%), var(--bg);
                color: var(--text); min-height: 100vh; padding: 24px;
            }
            .app-container { max-width: 1200px; margin: 0 auto; display: flex; flex-direction: column; gap: 24px; }
            .navbar { display: flex; justify-content: space-between; align-items: center; background: var(--panel); backdrop-filter: blur(12px); border: 1px solid var(--border); border-radius: 16px; padding: 14px 20px; }
            .brand { display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 17px; }
            .brand-badge { background: linear-gradient(135deg, var(--primary), var(--accent)); width: 28px; height: 28px; border-radius: 8px; display: grid; place-items: center; font-size: 14px; color: #000; font-weight: 800; }
            .hw-status { display: flex; align-items: center; gap: 8px; background: rgba(0,0,0,0.3); padding: 6px 14px; border-radius: 99px; border: 1px solid var(--border); }
            .hw-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--success); box-shadow: 0 0 10px var(--success); }
            .hw-label { font-size: 12px; font-weight: 600; color: var(--success); }
            .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }
            .stat-card { background: var(--panel); border: 1px solid var(--border); border-radius: 14px; padding: 18px; display: flex; flex-direction: column; gap: 6px; }
            .stat-title { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }
            .stat-value { font-size: 24px; font-weight: 700; color: #fff; }
            .main-layout { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
            @media(max-width: 900px) { .main-layout { grid-template-columns: 1fr; } }
            .card { background: var(--panel); backdrop-filter: blur(10px); border: 1px solid var(--border); border-radius: 16px; padding: 22px; display: flex; flex-direction: column; gap: 16px; }
            .card-header { display: flex; justify-content: space-between; align-items: center; }
            .card-title { font-size: 15px; font-weight: 600; color: #fff; }
            input { background: rgba(0, 0, 0, 0.4); border: 1px solid var(--border); color: #fff; padding: 11px 14px; border-radius: 10px; font-size: 13px; outline: none; width: 100%; }
            input:focus { border-color: var(--border-focus); box-shadow: 0 0 12px rgba(56, 189, 248, 0.2); }
            .btn { background: linear-gradient(135deg, var(--primary), #0284c7); color: #030712; font-weight: 600; border: none; padding: 10px 18px; border-radius: 10px; font-size: 13px; cursor: pointer; white-space: nowrap; }
            .btn-outline { background: transparent; border: 1px solid var(--border); color: #fff; }
            .btn-danger { background: rgba(248, 113, 113, 0.15); border: 1px solid rgba(248, 113, 113, 0.3); color: var(--danger); }
            .table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 10px; }
            table { width: 100%; border-collapse: collapse; font-size: 12px; }
            th { text-align: left; padding: 12px; background: rgba(255,255,255,0.02); color: var(--muted); font-weight: 500; border-bottom: 1px solid var(--border); }
            td { padding: 12px; border-bottom: 1px solid var(--border); }
            .key-mono { font-family: 'JetBrains Mono', monospace; font-size: 11px; background: rgba(0,0,0,0.5); padding: 4px 8px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05); color: var(--primary); }
            .term-stream { background: #020408; border: 1px solid var(--border); border-radius: 12px; padding: 14px; height: 320px; overflow-y: auto; font-family: 'JetBrains Mono', monospace; font-size: 11px; display: flex; flex-direction: column; gap: 8px; }
            .log-line { display: flex; gap: 8px; align-items: baseline; word-break: break-all; }
            .log-time { color: var(--muted); font-size: 10px; }
            .log-tag { color: var(--primary); font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="app-container">
            <div class="navbar">
                <div class="brand">
                    <div class="brand-badge">A</div>
                    <span>Akhi<span style="color:var(--primary);">Cloud</span> Platform</span>
                </div>
                <div class="hw-status">
                    <div class="hw-dot"></div>
                    <span class="hw-label">Cloud Native: 24/7 LIVE</span>
                </div>
            </div>

            <div class="stat-grid">
                <div class="stat-card"><span class="stat-title">Platform Gateway</span><span class="stat-value" style="color:var(--success);">Online</span></div>
                <div class="stat-card"><span class="stat-title">Total API Keys</span><span class="stat-value" id="statKeys">0</span></div>
                <div class="stat-card"><span class="stat-title">Active Sockets</span><span class="stat-value" id="statSockets">1</span></div>
                <div class="stat-card"><span class="stat-title">Cloud Storage</span><span class="stat-value" style="color:var(--accent);">Ready</span></div>
            </div>

            <div class="main-layout">
                <div style="display:flex; flex-direction:column; gap:20px;">
                    <div class="card">
                        <div class="card-header"><span class="card-title">Developer API Keys</span></div>
                        <div style="display:flex; gap:10px;">
                            <input type="text" id="appName" placeholder="Project Name">
                            <button class="btn" onclick="createKey()">Issue Key</button>
                        </div>
                        <div class="table-wrap">
                            <table>
                                <thead><tr><th>Application</th><th>API Key</th><th>Hits</th><th>Status</th><th>Action</th></tr></thead>
                                <tbody id="keysTable"></tbody>
                            </table>
                        </div>
                    </div>

                    <div class="card">
                        <div class="card-header"><span class="card-title">Database & Media Sandbox</span></div>
                        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px;">
                            <input type="text" id="testKey" placeholder="Paste x-api-key">
                            <input type="text" id="testCol" value="project_data" placeholder="Collection">
                        </div>
                        <div style="display:flex; gap:10px;">
                            <input type="text" id="testPayload" placeholder='{"score": 100}'>
                            <button class="btn btn-outline" onclick="testDB()">Insert Data</button>
                        </div>
                        <div style="display:flex; gap:10px; align-items:center;">
                            <input type="file" id="testFile">
                            <button class="btn btn-outline" onclick="testUpload()">Upload Media</button>
                        </div>
                        <div id="testOutput" style="font-size:12px; color:var(--primary); font-family:'JetBrains Mono';"></div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Realtime Event Stream</span>
                        <span style="font-size:11px; color:var(--success);">● WebSocket</span>
                    </div>
                    <div class="term-stream" id="termLogs"></div>
                </div>
            </div>
        </div>

        <script>
            const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
            const ws = new WebSocket(`${proto}//${location.host}/ws/stream`);
            const term = document.getElementById("termLogs");

            ws.onmessage = (e) => {
                const parsed = JSON.parse(e.data);
                const line = document.createElement("div");
                line.className = "log-line";
                line.innerHTML = `<span class="log-time">[${parsed.time}]</span> <span class="log-tag">${parsed.event}:</span> <span>${JSON.stringify(parsed.payload || '')}</span>`;
                term.appendChild(line);
                term.scrollTop = term.scrollHeight;
            };

            async function loadKeys() {
                const res = await fetch('/api/admin/keys/list');
                const d = await res.json();
                const tb = document.getElementById("keysTable");
                tb.innerHTML = "";
                let count = 0;
                for (let k in d.keys) {
                    count++;
                    const item = d.keys[k];
                    tb.innerHTML += `<tr>
                        <td><b>${item.app}</b></td>
                        <td><span class="key-mono">${k}</span></td>
                        <td>${item.hits || 0}</td>
                        <td style="color:${item.active ? 'var(--success)' : 'var(--danger)'}">${item.active ? 'Active' : 'Revoked'}</td>
                        <td><button class="btn btn-danger" style="padding:4px 8px; font-size:10px;" onclick="toggleKey('${k}')">${item.active ? 'Revoke' : 'Allow'}</button></td>
                    </tr>`;
                }
                document.getElementById("statKeys").innerText = count;
            }

            async function createKey() {
                const n = document.getElementById("appName").value;
                if (!n) return alert("Project name likhein");
                await fetch('/api/admin/keys/create', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({app_name: n})
                });
                document.getElementById("appName").value = "";
                loadKeys();
            }

            async function toggleKey(k) {
                await fetch('/api/admin/keys/toggle', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({key: k})
                });
                loadKeys();
            }

            async function testDB() {
                const k = document.getElementById("testKey").value;
                const col = document.getElementById("testCol").value;
                const payload = document.getElementById("testPayload").value || '{}';
                const res = await fetch(`/api/v1/db/${col}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'x-api-key': k},
                    body: payload
                });
                const d = await res.json();
                document.getElementById("testOutput").innerText = d.status === "success" ? `✓ Inserted ID: ${d.item._id}` : `✗ ${d.message}`;
            }

            async function testUpload() {
                const f = document.getElementById("testFile").files[0];
                if (!f) return alert("File choose karein");
                const fd = new FormData();
                fd.append("file", f);
                const res = await fetch('/api/v1/media/upload', {method: 'POST', body: fd});
                const d = await res.json();
                document.getElementById("testOutput").innerText = d.status === "success" ? `✓ URL: ${d.url}` : `✗ Error uploading`;
            }

            loadKeys();
        </script>
    </body>
    </html>
    """)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
