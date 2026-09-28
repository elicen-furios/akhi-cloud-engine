import os
import json
import time
import secrets
import hashlib
import hmac
import base64
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory, render_template_string
from flask_cors import CORS
from flask_sock import Sock
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)
sock = Sock(app)

BASE_DIR = "/sdcard/DataBase"
MEDIA_DIR = os.path.join(BASE_DIR, "media")
DATA_FILE = os.path.join(BASE_DIR, "platform_store.json")
SECRET_KEY = "AKHI_CLOUD_ULTRA_SECURE_SECRET_KEY_PROD"

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

def hash_pass(pwd, salt=None):
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac('sha256', pwd.encode(), salt.encode(), 100000).hex()
    return f"{salt}:{hashed}"

def verify_pass(pwd, stored):
    salt, hashed = stored.split(":")
    return stored == f"{salt}:{hashlib.pbkdf2_hmac('sha256', pwd.encode(), salt.encode(), 100000).hex()}"

def issue_token(user):
    payload = {"sub": user, "iat": int(time.time()), "exp": int(time.time()) + 604800}
    p_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().strip("=")
    h_b64 = base64.urlsafe_b64encode(json.dumps({"alg":"HS256"}).encode()).decode().strip("=")
    sig = base64.urlsafe_b64encode(hmac.new(SECRET_KEY.encode(), f"{h_b64}.{p_b64}".encode(), hashlib.sha256).digest()).decode().strip("=")
    return f"{h_b64}.{p_b64}.{sig}"

def verify_token(token):
    try:
        h, p, s = token.split(".")
        test_sig = base64.urlsafe_b64encode(hmac.new(SECRET_KEY.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()).decode().strip("=")
        if not hmac.compare_digest(s, test_sig):
            return None
        data = json.loads(base64.urlsafe_b64decode(p + "==").decode())
        if data["exp"] < int(time.time()):
            return None
        return data["sub"]
    except:
        return None

def gateway_check(allow_public_get=False):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if allow_public_get and request.method == "GET":
                return f(*args, **kwargs)

            auth = request.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                user = verify_token(auth.split(" ")[1])
                if user:
                    request.actor = f"Owner:{user}"
                    return f(*args, **kwargs)

            key = request.headers.get("x-api-key") or request.args.get("api_key")
            if key:
                db = read_db()
                k_data = db["keys"].get(key)
                if k_data and k_data.get("active", True):
                    k_data["hits"] = k_data.get("hits", 0) + 1
                    k_data["last_used"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    write_db(db)
                    request.actor = f"App:{k_data['app']}"
                    return f(*args, **kwargs)
                return jsonify({"status": "error", "message": "API key revoked or invalid"}), 403

            return jsonify({"status": "error", "message": "Authentication required: Missing x-api-key or Bearer Token"}), 401
        return decorated
    return decorator

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

@app.route('/api/v1/auth/register', methods=['POST'])
def auth_register():
    body = request.get_json(silent=True) or request.form
    u, p = body.get("username"), body.get("password")
    if not u or not p or len(p) < 6:
        return jsonify({"status": "error", "message": "Username and password (min 6 chars) required"}), 400
    db = read_db()
    if u in db["users"]:
        return jsonify({"status": "error", "message": "User already exists"}), 409
    db["users"][u] = hash_pass(p)
    write_db(db)
    ws_broadcast("AUTH", {"action": "REGISTER", "user": u})
    return jsonify({"status": "success", "message": f"User {u} registered"})

@app.route('/api/v1/auth/login', methods=['POST'])
def auth_login():
    body = request.get_json(silent=True) or request.form
    u, p = body.get("username"), body.get("password")
    db = read_db()
    if u not in db["users"] or not verify_pass(p, db["users"][u]):
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401
    tok = issue_token(u)
    ws_broadcast("AUTH", {"action": "LOGIN", "user": u})
    return jsonify({"status": "success", "token": tok, "username": u})

@app.route('/api/v1/db/<collection>', methods=['GET'])
@gateway_check(allow_public_get=True)
def db_get(collection):
    db = read_db()
    items = db["collections"].get(collection, [])
    return jsonify({"status": "success", "collection": collection, "count": len(items), "data": items})

@app.route('/api/v1/db/<collection>', methods=['POST'])
@gateway_check(allow_public_get=False)
def db_post(collection):
    body = request.get_json(silent=True) or {}
    db = read_db()
    if collection not in db["collections"]:
        db["collections"][collection] = []
    item = {
        "_id": secrets.token_hex(6),
        "created_by": getattr(request, "actor", "System"),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "body": body
    }
    db["collections"][collection].append(item)
    write_db(db)
    ws_broadcast("DATABASE", {"action": "INSERT", "collection": collection, "item": item})
    return jsonify({"status": "success", "record": item})

@app.route('/api/v1/media/upload', methods=['POST'])
@gateway_check(allow_public_get=False)
def media_upload():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded"}), 400
    f = request.files['file']
    safe_name = f"{int(time.time())}_{secrets.token_hex(3)}_{secure_filename(f.filename)}"
    f.save(os.path.join(MEDIA_DIR, safe_name))
    link = f"/media/{safe_name}"
    ws_broadcast("MEDIA", {"action": "UPLOAD", "file": safe_name})
    return jsonify({"status": "success", "file_url": link})

@app.route('/media/<path:filename>')
def serve_file(filename):
    return send_from_directory(MEDIA_DIR, secure_filename(filename))

@app.route('/api/admin/keys/create', methods=['POST'])
def create_key():
    req = request.get_json(silent=True) or {}
    name = req.get("app_name", "Untitled Project")
    key = f"akhi_live_{secrets.token_urlsafe(16)}"
    db = read_db()
    db["keys"][key] = {
        "app": name,
        "created": time.strftime("%Y-%m-%d"),
        "hits": 0,
        "last_used": "Never",
        "active": True
    }
    write_db(db)
    return jsonify({"status": "success", "key": key})

@app.route('/api/admin/keys/list', methods=['GET'])
def list_keys():
    return jsonify({"keys": read_db().get("keys", {})})

@app.route('/api/admin/keys/toggle', methods=['POST'])
def toggle_key():
    req = request.get_json(silent=True) or {}
    k = req.get("key")
    db = read_db()
    if k in db["keys"]:
        db["keys"][k]["active"] = not db["keys"][k].get("active", True)
        write_db(db)
        return jsonify({"status": "success", "active": db["keys"][k]["active"]})
    return jsonify({"status": "error", "message": "Key not found"}), 404

@app.route('/')
def console_ui():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Akhi Cloud - Console</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg: #090d16;
                --surface: #101623;
                --border: #1e293b;
                --primary: #38bdf8;
                --primary-glow: rgba(56, 189, 248, 0.15);
                --accent: #6366f1;
                --success: #10b981;
                --danger: #f43f5e;
                --text: #f1f5f9;
                --text-muted: #94a3b8;
            }
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { background: var(--bg); color: var(--text); font-family: 'Plus Jakarta Sans', sans-serif; display: flex; min-height: 100vh; }
            
            .sidebar { width: 240px; background: var(--surface); border-right: 1px solid var(--border); padding: 24px 16px; display: flex; flex-direction: column; gap: 8px; flex-shrink: 0; }
            .brand { font-size: 18px; font-weight: 700; color: #fff; margin-bottom: 20px; display: flex; align-items: center; gap: 8px; }
            .brand span { color: var(--primary); }
            .nav-item { padding: 10px 14px; border-radius: 8px; color: var(--text-muted); font-size: 14px; font-weight: 500; cursor: pointer; transition: all 0.2s; border: none; background: transparent; text-align: left; width: 100%; display: flex; align-items: center; gap: 10px; }
            .nav-item:hover, .nav-item.active { background: var(--primary-glow); color: var(--primary); }

            .main-content { flex: 1; padding: 32px; overflow-y: auto; }
            .header-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 28px; }
            .title-wrap h1 { font-size: 24px; font-weight: 700; }
            .title-wrap p { color: var(--text-muted); font-size: 14px; margin-top: 4px; }
            .status-badge { background: rgba(16, 185, 129, 0.12); color: var(--success); border: 1px solid rgba(16, 185, 129, 0.3); padding: 6px 12px; border-radius: 99px; font-size: 12px; font-weight: 600; display: flex; align-items: center; gap: 6px; }
            .dot { width: 7px; height: 7px; background: var(--success); border-radius: 50%; }

            .cards-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; }
            .card { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 22px; display: flex; flex-direction: column; gap: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.2); }
            .card-title { font-size: 16px; font-weight: 600; color: #fff; display: flex; justify-content: space-between; align-items: center; }
            
            input, select { background: #070b13; border: 1px solid var(--border); color: #fff; padding: 11px 14px; border-radius: 8px; font-size: 13px; font-family: inherit; width: 100%; outline: none; transition: border 0.2s; }
            input:focus { border-color: var(--primary); }
            
            .btn { background: var(--primary); color: #000; font-weight: 600; border: none; padding: 11px 16px; border-radius: 8px; cursor: pointer; font-size: 13px; transition: opacity 0.2s; display: inline-flex; justify-content: center; align-items: center; gap: 8px; }
            .btn:hover { opacity: 0.9; }
            .btn-outline { background: transparent; border: 1px solid var(--border); color: var(--text); }
            .btn-outline:hover { border-color: var(--primary); color: var(--primary); }
            .btn-danger { background: rgba(244, 63, 94, 0.12); color: var(--danger); border: 1px solid rgba(244, 63, 94, 0.3); }

            table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 8px; }
            th { text-align: left; color: var(--text-muted); font-weight: 500; padding: 10px; border-bottom: 1px solid var(--border); }
            td { padding: 12px 10px; border-bottom: 1px solid #141c2e; }
            .key-pill { font-family: 'JetBrains Mono', monospace; font-size: 11px; background: #070b13; padding: 4px 8px; border-radius: 6px; border: 1px solid #1e293b; color: var(--primary); }

            .terminal { background: #05080f; border: 1px solid var(--border); border-radius: 10px; padding: 14px; height: 160px; overflow-y: auto; font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #a5f3fc; }
            .terminal-row { margin-bottom: 6px; display: flex; gap: 8px; }
            .time { color: var(--text-muted); }

            @media(max-width: 768px) {
                body { flex-direction: column; }
                .sidebar { width: 100%; border-right: none; border-bottom: 1px solid var(--border); }
                .main-content { padding: 20px; }
            }
        </style>
    </head>
    <body>
        <div class="sidebar">
            <div class="brand">AKHI <span>CLOUD</span></div>
            <button class="nav-item active">Dashboard</button>
            <button class="nav-item" onclick="alert('Docs: Include x-api-key in headers for external POST requests')">API Docs</button>
            <button class="nav-item" onclick="alert('Connected to: localhost:8080')">Node Status</button>
        </div>

        <div class="main-content">
            <div class="header-bar">
                <div class="title-wrap">
                    <h1>Cloud Console</h1>
                    <p>Production Gateway & Backend Hub</p>
                </div>
                <div class="status-badge">
                    <div class="dot"></div> Server Live (Z+ Mode)
                </div>
            </div>

            <div class="cards-grid">
                <!-- Card 1: API Key Management -->
                <div class="card" style="grid-column: 1 / -1;">
                    <div class="card-title">
                        Developer API Keys
                        <span style="font-size: 12px; font-weight: normal; color: var(--text-muted);">External applications authentication</span>
                    </div>
                    <div style="display: flex; gap: 10px; max-width: 500px;">
                        <input type="text" id="appName" placeholder="Project Name (e.g. AndroidStore, ReactApp)">
                        <button class="btn" onclick="createKey()" style="white-space: nowrap;">Generate Key</button>
                    </div>
                    <div style="overflow-x: auto;">
                        <table>
                            <thead>
                                <tr>
                                    <th>Application</th>
                                    <th>API Key (x-api-key)</th>
                                    <th>Total Requests</th>
                                    <th>Status</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody id="keysTable"></tbody>
                        </table>
                    </div>
                </div>

                <!-- Card 2: REST DB Testing -->
                <div class="card">
                    <div class="card-title">REST Database Engine</div>
                    <input type="text" id="dbCol" value="products" placeholder="Collection Name">
                    <input type="text" id="dbPayload" placeholder='{"name": "Master Item", "price": 499}'>
                    <input type="text" id="testKeyRest" placeholder="Paste x-api-key or use JWT">
                    <div style="display: flex; gap: 10px;">
                        <button class="btn" style="flex: 1;" onclick="postRecord()">Insert Record</button>
                        <button class="btn btn-outline" style="flex: 1;" onclick="getRecords()">Fetch Records</button>
                    </div>
                    <div id="dbLog" style="font-size: 12px; color: var(--primary);"></div>
                </div>

                <!-- Card 3: Storage Cloud Drive -->
                <div class="card">
                    <div class="card-title">Cloud Storage Drive</div>
                    <input type="file" id="mediaFile">
                    <input type="text" id="testKeyMedia" placeholder="Paste x-api-key or use JWT">
                    <button class="btn" onclick="uploadFile()">Upload File</button>
                    <div id="mediaLog" style="font-size: 12px; color: var(--success); word-break: break-all;"></div>
                </div>

                <!-- Card 4: JWT Auth Service -->
                <div class="card">
                    <div class="card-title">Authentication Guard (JWT)</div>
                    <input type="text" id="authUser" placeholder="Username">
                    <input type="password" id="authPass" placeholder="Password (min 6 chars)">
                    <div style="display: flex; gap: 10px;">
                        <button class="btn btn-outline" style="flex: 1;" onclick="doRegister()">Register</button>
                        <button class="btn" style="flex: 1;" onclick="doLogin()">Login</button>
                    </div>
                    <div id="authLog" style="font-size: 12px; color: var(--primary);"></div>
                </div>

                <!-- Card 5: Realtime Stream -->
                <div class="card">
                    <div class="card-title">WebSocket Event Stream</div>
                    <div class="terminal" id="terminalLogs"></div>
                    <div style="display: flex; gap: 10px;">
                        <input type="text" id="wsInput" placeholder="Broadcast live message...">
                        <button class="btn btn-outline" onclick="sendWs()">Send</button>
                    </div>
                </div>
            </div>
        </div>

        <script>
            let savedJwt = localStorage.getItem("akhi_jwt") || "";
            if (savedJwt) document.getElementById("authLog").innerText = "JWT Token Active in Browser";

            const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
            const ws = new WebSocket(`${proto}//${location.host}/ws/stream`);
            const term = document.getElementById("terminalLogs");

            ws.onmessage = (e) => {
                const parsed = JSON.parse(e.data);
                const row = document.createElement("div");
                row.className = "terminal-row";
                row.innerHTML = `<span class="time">[${parsed.time}]</span> <b>${parsed.event}:</b> <span>${JSON.stringify(parsed.payload || parsed.data || '')}</span>`;
                term.appendChild(row);
                term.scrollTop = term.scrollHeight;
            };

            function sendWs() {
                const inp = document.getElementById("wsInput");
                ws.send(inp.value);
                inp.value = "";
            }

            async function loadKeys() {
                const res = await fetch('/api/admin/keys/list');
                const d = await res.json();
                const tb = document.getElementById("keysTable");
                tb.innerHTML = "";
                for (let k in d.keys) {
                    const item = d.keys[k];
                    tb.innerHTML += `<tr>
                        <td><b>${item.app}</b></td>
                        <td><span class="key-pill">${k}</span></td>
                        <td>${item.hits || 0}</td>
                        <td><span style="color: ${item.active ? 'var(--success)' : 'var(--danger)'}; font-weight: 600;">${item.active ? 'Active' : 'Revoked'}</span></td>
                        <td><button class="btn btn-danger" style="padding: 4px 8px; font-size: 11px;" onclick="toggleKey('${k}')">${item.active ? 'Revoke' : 'Enable'}</button></td>
                    </tr>`;
                }
            }

            async function createKey() {
                const n = document.getElementById("appName").value;
                if (!n) return alert("Project name daaliye");
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

            async function doRegister() {
                const u = document.getElementById("authUser").value;
                const p = document.getElementById("authPass").value;
                const res = await fetch('/api/v1/auth/register', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username: u, password: p})
                });
                const d = await res.json();
                document.getElementById("authLog").innerText = d.message;
            }

            async function doLogin() {
                const u = document.getElementById("authUser").value;
                const p = document.getElementById("authPass").value;
                const res = await fetch('/api/v1/auth/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username: u, password: p})
                });
                const d = await res.json();
                if (d.token) {
                    savedJwt = d.token;
                    localStorage.setItem("akhi_jwt", d.token);
                    document.getElementById("authLog").innerText = "Login Successful: Token Saved";
                } else {
                    document.getElementById("authLog").innerText = d.message;
                }
            }

            function getHeader(id) {
                const k = document.getElementById(id).value;
                const h = {};
                if (k) h['x-api-key'] = k;
                else if (savedJwt) h['Authorization'] = `Bearer ${savedJwt}`;
                return h;
            }

            async function postRecord() {
                const col = document.getElementById("dbCol").value;
                const body = document.getElementById("dbPayload").value || '{"status": "ok"}';
                const h = getHeader("testKeyRest");
                h['Content-Type'] = 'application/json';
                const res = await fetch(`/api/v1/db/${col}`, { method: 'POST', headers: h, body: body });
                const d = await res.json();
                document.getElementById("dbLog").innerText = d.status === 'success' ? `Record Created: ID ${d.record._id}` : d.message;
            }

            async function getRecords() {
                const col = document.getElementById("dbCol").value;
                const res = await fetch(`/api/v1/db/${col}`);
                const d = await res.json();
                document.getElementById("dbLog").innerText = `Total ${d.count} items fetched`;
            }

            async function uploadFile() {
                const f = document.getElementById("mediaFile").files[0];
                if (!f) return alert("Select a file");
                const fd = new FormData();
                fd.append("file", f);
                const h = getHeader("testKeyMedia");
                const res = await fetch('/api/v1/media/upload', { method: 'POST', headers: h, body: fd });
                const d = await res.json();
                document.getElementById("mediaLog").innerText = d.file_url ? `Stream URL: ${d.file_url}` : d.message;
            }

            loadKeys();
        </script>
    </body>
    </html>
    """)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
