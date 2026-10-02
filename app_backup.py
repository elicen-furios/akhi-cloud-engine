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
        "cluster": "Europe-Frankfurt Edge",
        "tls": "TLS 1.3 / AES-256-GCM",
        "uptime": "99.98%"
    })

@app.route('/api/admin/keys/list', methods=['GET'])
def list_keys():
    return jsonify({"keys": read_db().get("keys", {})})

@app.route('/api/admin/keys/create', methods=['POST'])
def create_key():
    req = request.get_json(silent=True) or {}
    name = req.get("app_name", "eva_units").strip() or "client_app"
    user_email = req.get("email", "akhil@example.com")
    key = f"akhi_live_{secrets.token_urlsafe(16)}"
    db = read_db()
    db.setdefault("keys", {})[key] = {
        "app": name,
        "email": user_email,
        "created": time.strftime("%Y-%m-%d"),
        "expires": "2026-09-27",
        "hits": 0,
        "active": True
    }
    write_db(db)
    return jsonify({"status": "success", "key": key, "app": name})

@app.route('/api/admin/keys/toggle', methods=['POST'])
def toggle_key():
    req = request.get_json(silent=True) or {}
    k = req.get("key")
    db = read_db()
    if k in db.get("keys", {}):
        db["keys"][k]["active"] = not db["keys"][k].get("active", True)
        write_db(db)
        return jsonify({"status": "success", "active": db["keys"][k]["active"]})
    return jsonify({"status": "error"}), 404

@app.route('/api/v1/db/<collection>', methods=['GET', 'POST'])
def db_handler(collection):
    db = read_db()
    db.setdefault("collections", {})
    if request.method == 'GET':
        items = db["collections"].get(collection, [])
        return jsonify({"status": "success", "collection": collection, "records": items})
    
    key = request.headers.get("x-api-key") or request.args.get("api_key")
    keys = db.get("keys", {})
    if not key or key not in keys or not keys[key].get("active"):
        return jsonify({"status": "unauthorized", "message": "Valid x-api-key required"}), 403
    
    keys[key]["hits"] = keys[key].get("hits", 0) + 1
    if collection not in db["collections"]:
        db["collections"][collection] = []
    
    item = {
        "_id": secrets.token_hex(6),
        "app": keys[key].get("app", "app"),
        "time": time.strftime("%H:%M:%S"),
        "payload": request.get_json(silent=True) or {}
    }
    db["collections"][collection].append(item)
    write_db(db)
    return jsonify({"message": "Data stored", "id": item["_id"], "hits": keys[key]["hits"]})

@app.route('/api/v1/media/upload', methods=['POST'])
def media_upload():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file chosen"}), 400
    f = request.files['file']
    s_name = f"{int(time.time())}_{secrets.token_hex(3)}_{secure_filename(f.filename)}"
    f.save(os.path.join(MEDIA_DIR, s_name))
    return jsonify({"status": "success", "url": f"/media/{s_name}", "filename": s_name})

@app.route('/media/<path:fname>')
def media_serve(fname):
    return send_from_directory(MEDIA_DIR, secure_filename(fname))

# ========================================================
# SEPARATE DEDICATED PAGE: GET API KEY PORTAL (/portal/keys)
# ========================================================
@app.route('/portal/keys')
def key_provision_portal():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AKHIL // API KEY PORTAL • システム</title>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --cyan: #00f0ff;
                --magenta: #ff007f;
                --bg: #060b18;
                --panel: rgba(10, 18, 36, 0.85);
                --border: rgba(0, 240, 255, 0.25);
            }
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }
            body {
                background: radial-gradient(circle at 50% 10%, rgba(0, 240, 255, 0.12), transparent 60%),
                            radial-gradient(circle at 10% 90%, rgba(255, 0, 127, 0.1), transparent 50%), var(--bg);
                color: #fff; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px;
            }
            .hud-card {
                background: var(--panel); backdrop-filter: blur(24px); border: 1px solid var(--border);
                border-radius: 16px; max-width: 480px; width: 100%; padding: 32px;
                box-shadow: 0 0 35px rgba(0, 240, 255, 0.2); position: relative;
            }
            .hud-card::before {
                content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
                background: linear-gradient(90deg, var(--cyan), var(--magenta));
            }
            .tag { font-family: 'JetBrains Mono'; font-size: 11px; color: var(--cyan); letter-spacing: 2px; text-transform: uppercase; margin-bottom: 8px; }
            h1 { font-size: 22px; font-weight: 800; letter-spacing: -0.5px; }
            .jp-sub { font-size: 11px; color: var(--magenta); letter-spacing: 3px; margin-bottom: 24px; font-weight: 700; }
            .form-box { display: flex; flex-direction: column; gap: 14px; }
            input {
                background: rgba(3, 7, 18, 0.8); border: 1px solid var(--border); border-radius: 8px;
                padding: 12px 14px; color: #fff; font-size: 14px; outline: none; width: 100%;
            }
            input:focus { border-color: var(--cyan); box-shadow: 0 0 12px rgba(0, 240, 255, 0.3); }
            .btn-action {
                background: linear-gradient(90deg, var(--cyan), #0077ff); color: #000;
                font-weight: 800; font-size: 13px; padding: 13px; border: none; border-radius: 8px;
                cursor: pointer; letter-spacing: 1px; text-transform: uppercase; margin-top: 6px;
            }
            .btn-google {
                background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.15);
                color: #fff; font-size: 12px; font-weight: 700; padding: 11px; border-radius: 8px;
                cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 10px; margin-top: 4px;
            }
            .logged-panel { display: none; flex-direction: column; gap: 14px; }
            .token-box { background: #000; border: 1px solid var(--magenta); border-radius: 8px; padding: 14px; display: none; margin-top: 8px; }
            .token-str { font-family: 'JetBrains Mono'; font-size: 12px; color: var(--cyan); word-break: break-all; margin: 8px 0; }
            .copy-btn { background: rgba(0, 240, 255, 0.15); border: 1px solid var(--cyan); color: var(--cyan); padding: 6px 12px; border-radius: 6px; font-size: 11px; cursor: pointer; }
        </style>
        <script type="module">
            import { initializeApp } from "https://www.gstatic.com/firebasejs/10.9.0/firebase-app.js";
            import { getAuth, signInWithEmailAndPassword, createUserWithEmailAndPassword, signInWithPopup, GoogleAuthProvider, onAuthStateChanged, signOut } from "https://www.gstatic.com/firebasejs/10.9.0/firebase-auth.js";

            const firebaseConfig = {
                apiKey: "AIzaSyBt_zPZndgJh82AK8tXWvOyN8ec3dY31KQ",
                authDomain: "free-api-web-2a7bc.firebaseapp.com",
                projectId: "free-api-web-2a7bc",
                storageBucket: "free-api-web-2a7bc.firebasestorage.app",
                messagingSenderId: "118488816924",
                appId: "1:118488816924:web:f4a86246ed76778f00eed9",
                measurementId: "G-2PG8X0PK0R"
            };

            const app = initializeApp(firebaseConfig);
            const auth = getAuth(app);
            const provider = new GoogleAuthProvider();

            let currentUser = null;

            onAuthStateChanged(auth, (user) => {
                if (user) {
                    currentUser = user;
                    document.getElementById("authSection").style.display = "none";
                    document.getElementById("forgeSection").style.display = "flex";
                    document.getElementById("userGreeting").innerText = `AUTHENTICATED: ${user.email}`;
                } else {
                    currentUser = null;
                    document.getElementById("authSection").style.display = "flex";
                    document.getElementById("forgeSection").style.display = "none";
                }
            });

            window.handleEmailAuth = async () => {
                const email = document.getElementById("authEmail").value.trim();
                const pass = document.getElementById("authPass").value.trim();
                if (!email || !pass) return alert("Credentials required");
                try {
                    await signInWithEmailAndPassword(auth, email, pass);
                } catch(e) {
                    try {
                        await createUserWithEmailAndPassword(auth, email, pass);
                    } catch(err) {
                        alert("Auth Failure: " + err.message);
                    }
                }
            };

            window.handleGoogleAuth = async () => {
                try {
                    await signInWithPopup(auth, provider);
                } catch(e) {
                    alert("Google Sign-in: " + e.message);
                }
            };

            window.handleSignOut = () => signOut(auth);

            window.forgePass = async () => {
                const appName = document.getElementById("appName").value.trim() || "eva_units";
                const res = await fetch('/api/admin/keys/create', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        email: currentUser ? currentUser.email : "akhil@example.com",
                        app_name: appName
                    })
                });
                const d = await res.json();
                if (d.status === "success") {
                    document.getElementById("tokenStr").innerText = d.key;
                    document.getElementById("tokenDisplay").style.display = "block";
                }
            };

            window.copyPass = () => {
                navigator.clipboard.writeText(document.getElementById("tokenStr").innerText);
                alert("Cryptographic pass saved to clipboard!");
            };
        </script>
    </head>
    <body>
        <div class="hud-card">
            <div class="tag">// IDENTITY GATE</div>
            <h1>API Key Portal</h1>
            <div class="jp-sub">// セキュリティ認証・鍵生成システム</div>

            <div id="authSection" class="form-box">
                <input type="email" id="authEmail" value="akhil@example.com" placeholder="Operative Email">
                <input type="password" id="authPass" value="CyberEngine2026#" placeholder="Access Secret">
                <button class="btn-action" onclick="handleEmailAuth()">Authorize & Login</button>
                <button class="btn-google" onclick="handleGoogleAuth()">
                    <svg width="14" height="14" viewBox="0 0 24 24"><path fill="#fff" d="M12.48 10.92v3.28h7.84c-.24 1.84-.853 3.187-1.787 4.133-1.147 1.147-2.933 2.4-6.053 2.4-4.827 0-8.6-3.893-8.6-8.72s3.773-8.72 8.6-8.72c2.6 0 4.507 1.027 5.907 2.347l2.307-2.307C18.747 1.44 16.133 0 12.48 0 5.867 0 .307 5.387.307 12s5.56 12 12.173 12c3.573 0 6.267-1.173 8.373-3.36 2.16-2.16 2.84-5.213 2.84-7.667 0-.76-.053-1.467-.173-2.053H12.48z"/></svg>
                    Continue with Google
                </button>
            </div>

            <div id="forgeSection" class="logged-panel">
                <div id="userGreeting" style="font-family:'JetBrains Mono'; font-size:12px; color:var(--cyan);"></div>
                <input type="text" id="appName" value="eva_units" placeholder="Project Name">
                <button class="btn-action" onclick="forgePass()">Generate New API Key</button>
                <div id="tokenDisplay" class="token-box">
                    <div style="font-size:10px; color:var(--magenta); font-family:'JetBrains Mono'; font-weight:700;">SECURE ACCESS PASS:</div>
                    <div class="token-str" id="tokenStr"></div>
                    <button class="copy-btn" onclick="copyPass()">Copy Pass to Memory</button>
                </div>
                <button onclick="handleSignOut()" style="background:transparent; border:1px solid rgba(255,255,255,0.2); color:#94a3b8; padding:8px; border-radius:6px; cursor:pointer; font-size:11px; text-transform:uppercase;">Sign Out</button>
            </div>
        </div>
    </body>
    </html>
    """)

# ========================================================
# MAIN DASHBOARD INTERFACE (EXACT SCREENSHOT LAYOUT) (ROOT /)
# ========================================================
@app.route('/')
def main_dashboard():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AKHIL // DEV PLATFORM • システム中枢</title>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --cyan: #00f0ff;
                --magenta: #ff007f;
                --emerald: #00ff88;
                --red: #ff3366;
                --bg: #040814;
                --sidebar-bg: #070d1e;
                --card-bg: rgba(10, 18, 38, 0.85);
                --border: rgba(0, 240, 255, 0.22);
            }
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }
            body {
                background: linear-gradient(135deg, rgba(3,7,18,0.96), rgba(4,10,26,0.96)),
                            url('https://images.unsplash.com/photo-1578632767115-351597cf2477?q=80&w=1600&auto=format&fit=crop') center/cover fixed;
                color: #e2e8f0; min-height: 100vh; display: flex; flex-direction: column; overflow-x: hidden;
            }

            /* TOP BAR */
            .top-bar {
                height: 60px; background: rgba(5, 10, 22, 0.95); border-bottom: 1px solid var(--border);
                display: flex; align-items: center; justify-content: space-between; padding: 0 20px;
                backdrop-filter: blur(15px);
            }
            .brand-group { display: flex; align-items: center; gap: 14px; }
            .brand-icon { cursor: pointer; display: flex; align-items: center; }
            .brand-name { font-size: 18px; font-weight: 800; letter-spacing: 0.5px; }
            .brand-name span { color: var(--cyan); }
            .brand-sub { font-size: 10px; color: var(--cyan); letter-spacing: 2px; font-weight: 700; margin-left: 4px; }

            .top-center-banner {
                font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: 1.5px;
                color: #94a3b8; text-transform: uppercase;
            }
            .top-center-banner b { color: var(--cyan); }

            .top-right-group { display: flex; align-items: center; gap: 14px; }
            .btn-issue-key {
                background: linear-gradient(90deg, var(--cyan), #0077ff); color: #000; text-decoration: none;
                font-size: 12px; font-weight: 700; padding: 8px 16px; border-radius: 6px; letter-spacing: 0.5px;
                display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 0 15px rgba(0, 240, 255, 0.35);
            }
            .user-chip { display: flex; align-items: center; gap: 10px; background: rgba(0,0,0,0.5); border: 1px solid var(--border); padding: 4px 10px 4px 6px; border-radius: 30px; }
            .user-avatar { width: 28px; height: 28px; border-radius: 50%; background: linear-gradient(135deg, var(--magenta), var(--cyan)); display: grid; place-items: center; font-size: 12px; font-weight: 800; }
            .user-details { font-size: 11px; line-height: 1.2; }
            .user-status { color: var(--emerald); font-size: 9px; font-weight: 700; display: flex; align-items: center; gap: 4px; }
            .status-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--emerald); box-shadow: 0 0 6px var(--emerald); }

            /* MAIN LAYOUT (3 COLUMNS) */
            .main-content {
                display: grid; grid-template-columns: 210px 1fr 230px; flex: 1; min-height: calc(100vh - 90px);
            }
            @media (max-width: 1050px) {
                .main-content { grid-template-columns: 1fr; }
                .left-sidebar, .right-sidebar { display: none; }
            }

            /* LEFT SIDEBAR */
            .left-sidebar {
                background: var(--sidebar-bg); border-right: 1px solid var(--border); padding: 18px 12px;
                display: flex; flex-direction: column; gap: 20px;
            }
            .nav-section-title { font-size: 10px; font-weight: 800; letter-spacing: 1.5px; text-transform: uppercase; color: #64748b; padding-left: 8px; }
            .nav-list { list-style: none; display: flex; flex-direction: column; gap: 4px; }
            .nav-item {
                display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 8px;
                font-size: 12px; font-weight: 600; color: #94a3b8; cursor: pointer; transition: 0.2s;
            }
            .nav-item:hover, .nav-item.active { background: rgba(0, 240, 255, 0.1); color: #fff; border-left: 3px solid var(--cyan); }
            .nav-item svg { width: 14px; height: 14px; stroke: currentColor; }

            .sidebar-character-card {
                margin-top: auto; background: rgba(0,0,0,0.5); border: 1px solid var(--border); border-radius: 10px;
                padding: 12px; display: flex; align-items: center; gap: 10px;
            }
            .character-avatar {
                width: 44px; height: 44px; border-radius: 8px;
                background: url('https://images.unsplash.com/photo-1578632767115-351597cf2477?q=80&w=200&auto=format&fit=crop') center/cover;
                border: 1px solid var(--cyan);
            }

            /* CENTER CANVAS */
            .center-canvas { padding: 16px; display: flex; flex-direction: column; gap: 16px; overflow-y: auto; }

            /* TELEMETRY HORIZONTAL STRIP */
            .telemetry-strip {
                display: grid; grid-template-columns: repeat(4, 1fr) 1.2fr; gap: 10px;
                background: rgba(5, 10, 22, 0.8); border: 1px solid var(--border); border-radius: 12px; padding: 14px;
            }
            @media (max-width: 800px) { .telemetry-strip { grid-template-columns: 1fr 1fr; } }
            .metric-box { display: flex; align-items: center; gap: 10px; }
            .metric-icon-wrap { width: 34px; height: 34px; border-radius: 8px; display: grid; place-items: center; }
            .metric-info .m-title { font-size: 9px; font-weight: 700; text-transform: uppercase; color: #94a3b8; letter-spacing: 0.5px; }
            .metric-info .m-val { font-size: 13px; font-weight: 800; color: #fff; margin-top: 2px; font-family: 'JetBrains Mono'; }
            .terminal-snippet { font-family: 'JetBrains Mono'; font-size: 10px; color: #94a3b8; line-height: 1.4; border-left: 1px solid var(--border); padding-left: 10px; }
            .terminal-snippet b { color: var(--emerald); }

            /* TAB CONTROLS STRIP */
            .hud-tabs-strip {
                display: flex; gap: 8px; border-bottom: 1px solid var(--border); padding-bottom: 8px;
            }
            .hud-tab-btn {
                background: rgba(0,0,0,0.4); border: 1px solid var(--border); color: #94a3b8;
                padding: 8px 16px; border-radius: 6px; font-size: 12px; font-weight: 700; cursor: pointer;
                display: inline-flex; align-items: center; gap: 8px; transition: 0.2s;
            }
            .hud-tab-btn.active { background: rgba(0, 240, 255, 0.15); border-color: var(--cyan); color: #fff; }

            /* VIEW PANELS */
            .view-panel { display: none; }
            .view-panel.active { display: block; }

            /* 2-COLUMN CARDS FOR PASSCODE LEDGER */
            .passcode-layout { display: grid; grid-template-columns: 1.6fr 1fr; gap: 14px; }
            @media (max-width: 900px) { .passcode-layout { grid-template-columns: 1fr; } }

            .hud-card {
                background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px;
                padding: 18px; display: flex; flex-direction: column; gap: 14px;
            }
            .card-header-line { display: flex; justify-content: space-between; align-items: center; }
            .card-header-title { font-size: 13px; font-weight: 800; letter-spacing: 0.5px; color: var(--cyan); text-transform: uppercase; }

            /* TABLES */
            .table-wrap { overflow-x: auto; }
            table { width: 100%; border-collapse: collapse; font-size: 11px; }
            th { text-align: left; padding: 10px; background: rgba(0, 240, 255, 0.04); color: #94a3b8; font-weight: 700; border-bottom: 1px solid var(--border); }
            td { padding: 10px; border-bottom: 1px solid rgba(255, 255, 255, 0.04); }
            .key-mono { font-family: 'JetBrains Mono'; font-size: 11px; color: var(--cyan); background: rgba(0, 240, 255, 0.08); padding: 3px 6px; border-radius: 4px; }
            .badge-active { background: rgba(0, 255, 136, 0.15); border: 1px solid var(--emerald); color: var(--emerald); padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 9px; }
            .badge-revoked { background: rgba(255, 51, 102, 0.15); border: 1px solid var(--red); color: var(--red); padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 9px; }

            /* TRANSMISSION SANDBOX (3 COLUMN LOWER ROW) */
            .bottom-grid { display: grid; grid-template-columns: 1.2fr 1fr 1fr; gap: 14px; margin-top: 14px; }
            @media (max-width: 950px) { .bottom-grid { grid-template-columns: 1fr; } }

            .code-input-area {
                background: #02050e; border: 1px solid var(--border); border-radius: 6px; padding: 10px;
                font-family: 'JetBrains Mono'; font-size: 11px; color: #94a3b8; height: 110px; overflow-y: auto;
            }
            .btn-send {
                background: linear-gradient(90deg, var(--cyan), #0077ff); color: #000; font-weight: 800;
                font-size: 12px; padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer;
                display: inline-flex; align-items: center; gap: 6px; align-self: flex-start;
            }

            /* RIGHT SIDEBAR */
            .right-sidebar {
                background: var(--sidebar-bg); border-left: 1px solid var(--border); padding: 18px 14px;
                display: flex; flex-direction: column; gap: 18px;
            }
            .flask-card {
                background: rgba(0,0,0,0.4); border: 1px solid var(--border); border-radius: 12px; padding: 16px;
                display: flex; flex-direction: column; gap: 10px;
            }
            .character-img-banner {
                width: 100%; height: 110px; border-radius: 8px;
                background: url('https://images.unsplash.com/photo-1578632767115-351597cf2477?q=80&w=400&auto=format&fit=crop') center/cover;
                border: 1px solid var(--border);
            }
            .status-list { display: flex; flex-direction: column; gap: 6px; font-size: 11px; }
            .status-item { display: flex; justify-content: space-between; color: #94a3b8; }
            .status-item b { color: #fff; font-family: 'JetBrains Mono'; }

            /* BOTTOM FOOTER */
            .footer-bar {
                height: 30px; background: rgba(3, 6, 14, 0.98); border-top: 1px solid var(--border);
                display: flex; align-items: center; justify-content: space-between; padding: 0 20px;
                font-size: 10px; color: #64748b; font-family: 'JetBrains Mono';
            }
        </style>
    </head>
    <body>
        <!-- TOP BAR -->
        <div class="top-bar">
            <div class="brand-group">
                <div class="brand-icon">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--cyan)" stroke-width="2.5"><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
                </div>
                <div>
                    <div class="brand-name">AKHIL <span>DEV PLATFORM</span></div>
                    <div class="brand-sub">// システム中枢</div>
                </div>
            </div>

            <div class="top-center-banner">
                BUILD &nbsp;/&nbsp; DEPLOY &nbsp;/&nbsp; SCALE &nbsp;/&nbsp; <b>24/7</b><br>
                <span style="font-size:9px; color:#64748b;">YOUR IDEAS &times; OUR INFRASTRUCTURE</span>
            </div>

            <div class="top-right-group">
                <a href="/portal/keys" target="_blank" class="btn-issue-key">
                    <span>+ Issue API Key ↗</span>
                </a>
                <div class="user-chip">
                    <div class="user-avatar">A</div>
                    <div class="user-details">
                        <div>Akhil</div>
                        <div class="user-status"><div class="status-dot"></div> Online</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- MAIN 3-COL LAYOUT -->
        <div class="main-content">
            <!-- LEFT SIDEBAR -->
            <div class="left-sidebar">
                <div class="nav-section-title">Navigation</div>
                <ul class="nav-list">
                    <li class="nav-item active" onclick="switchMainTab('tabLedger')">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path></svg>
                        Home
                    </li>
                    <li class="nav-item" onclick="switchMainTab('tabLedger')">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
                        Passcode Ledger
                    </li>
                    <li class="nav-item" onclick="switchMainTab('tabSandbox')">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                        Transmission Sandbox
                    </li>
                    <li class="nav-item" onclick="switchMainTab('tabMedia')">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>
                        Media Core Vault
                    </li>
                    <li class="nav-item" onclick="switchMainTab('tabDocs')">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>
                        Tactical Protocol Docs
                    </li>
                </ul>

                <div class="nav-section-title" style="margin-top:10px;">Quick Access</div>
                <ul class="nav-list">
                    <li class="nav-item">API Keys</li>
                    <li class="nav-item">Database</li>
                    <li class="nav-item">Media Upload</li>
                    <li class="nav-item">Admin Panel</li>
                    <li class="nav-item">System Status</li>
                </ul>

                <div class="sidebar-character-card">
                    <div class="character-avatar"></div>
                    <div>
                        <div style="font-size:12px; font-weight:800;">AKHIL</div>
                        <div style="font-size:10px; color:#64748b;">DEVELOPER CONSOLE<br>// 夢を作る</div>
                    </div>
                </div>
            </div>

            <!-- CENTER CANVAS -->
            <div class="center-canvas">
                <!-- TELEMETRY HORIZONTAL STRIP -->
                <div class="telemetry-strip">
                    <div class="metric-box">
                        <div class="metric-icon-wrap" style="background:rgba(0, 255, 136, 0.1); border:1px solid var(--emerald); color:var(--emerald);">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
                        </div>
                        <div class="metric-info">
                            <div class="m-title">Cluster Health</div>
                            <div class="m-val" style="color:var(--emerald);">HEALTHY 100%</div>
                        </div>
                    </div>

                    <div class="metric-box">
                        <div class="metric-icon-wrap" style="background:rgba(255, 230, 0, 0.1); border:1px solid #ffe600; color:#ffe600;">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
                        </div>
                        <div class="metric-info">
                            <div class="m-title">Firebase Status</div>
                            <div class="m-val" style="color:#ffe600;">ONLINE v10.12</div>
                        </div>
                    </div>

                    <div class="metric-box">
                        <div class="metric-icon-wrap" style="background:rgba(0, 240, 255, 0.1); border:1px solid var(--cyan); color:var(--cyan);">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"></path></svg>
                        </div>
                        <div class="metric-info">
                            <div class="m-title">Active Passes</div>
                            <div class="m-val" id="statPasses">3 / 10</div>
                        </div>
                    </div>

                    <div class="metric-box">
                        <div class="metric-icon-wrap" style="background:rgba(0, 255, 136, 0.1); border:1px solid var(--emerald); color:var(--emerald);">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
                        </div>
                        <div class="metric-info">
                            <div class="m-title">TLS Mode</div>
                            <div class="m-val" style="color:#fff;">TLS 1.3 AES-256</div>
                        </div>
                    </div>

                    <div class="terminal-snippet">
                        > Cluster: <b>Healthy</b><br>
                        > DB: <b>Connected</b><br>
                        > Media: <b>Ready</b><br>
                        > Uptime: <b>7d 12h 34m</b>
                    </div>
                </div>

                <!-- HUD TABS SELECTOR -->
                <div class="hud-tabs-strip">
                    <button class="hud-tab-btn active" onclick="switchMainTab('tabLedger')">Passcode Ledger</button>
                    <button class="hud-tab-btn" onclick="switchMainTab('tabSandbox')">Transmission Sandbox</button>
                    <button class="hud-tab-btn" onclick="switchMainTab('tabMedia')">Media Core Vault</button>
                    <button class="hud-tab-btn" onclick="switchMainTab('tabDocs')">Tactical Protocol Docs</button>
                </div>

                <!-- VIEW 1: PASSCODE LEDGER (DEFAULT SHOWN) -->
                <div id="tabLedger" class="view-panel active">
                    <div class="passcode-layout">
                        <!-- LEDGER TABLE -->
                        <div class="hud-card">
                            <div class="card-header-line">
                                <div>
                                    <div class="card-header-title">Passcode Ledger</div>
                                    <div style="font-size:10px; color:#94a3b8;">Manage your API keys and access tokens</div>
                                </div>
                            </div>

                            <div class="table-wrap">
                                <table>
                                    <thead>
                                        <tr>
                                            <th>Key / Token</th>
                                            <th>User</th>
                                            <th>Status</th>
                                            <th>Hits</th>
                                            <th>Action</th>
                                        </tr>
                                    </thead>
                                    <tbody id="keysTableBody"></tbody>
                                </table>
                            </div>

                            <div style="border-top:1px solid var(--border); padding-top:12px; display:flex; justify-content:space-between; align-items:center;">
                                <div>
                                    <div style="font-size:12px; font-weight:700;">Generate New API Key</div>
                                    <div style="font-size:10px; color:#64748b;">Create a new cryptographic pass for your account</div>
                                </div>
                                <button onclick="quickGenerateKey()" style="background:var(--cyan); color:#000; font-weight:700; font-size:11px; padding:8px 14px; border:none; border-radius:6px; cursor:pointer;">Generate Key</button>
                            </div>
                        </div>

                        <!-- API KEY PORTAL SUMMARY CARD -->
                        <div class="hud-card">
                            <div class="card-header-title">API Key Portal</div>
                            <div style="font-size:10px; color:#64748b;">Authenticated Required</div>

                            <div style="background:rgba(0,0,0,0.4); border:1px solid var(--border); border-radius:8px; padding:12px; display:flex; justify-content:space-between; align-items:center;">
                                <div>
                                    <div style="font-size:10px; color:var(--emerald);">You are logged in</div>
                                    <div style="font-size:12px; font-weight:700;">akhil@example.com</div>
                                </div>
                                <a href="/portal/keys" target="_blank" style="background:transparent; border:1px solid rgba(255,255,255,0.2); color:#fff; font-size:10px; padding:6px 12px; border-radius:4px; text-decoration:none;">Open Portal ↗</a>
                            </div>

                            <div style="display:flex; flex-direction:column; gap:6px;">
                                <div style="font-size:11px; font-weight:700; color:#94a3b8; text-transform:uppercase;">Quick Actions</div>
                                <button onclick="copyActiveKey()" style="background:rgba(255,255,255,0.04); border:1px solid var(--border); color:#fff; padding:8px 12px; border-radius:6px; font-size:11px; text-align:left; cursor:pointer;">Copy Pass to Memory</button>
                                <button onclick="switchMainTab('tabSandbox')" style="background:rgba(255,255,255,0.04); border:1px solid var(--border); color:#fff; padding:8px 12px; border-radius:6px; font-size:11px; text-align:left; cursor:pointer;">Test in Sandbox</button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- VIEW 2: TRANSMISSION SANDBOX -->
                <div id="tabSandbox" class="view-panel">
                    <div class="hud-card">
                        <div class="card-header-title">Transmission Sandbox</div>
                        <div style="font-size:11px; color:#94a3b8;">Test your live API endpoints with pre-filled production payloads</div>

                        <div style="display:flex; gap:10px; align-items:center;">
                            <span style="background:var(--cyan); color:#000; font-weight:800; font-size:11px; padding:6px 10px; border-radius:4px;">POST</span>
                            <input type="text" id="targetEndpoint" value="/api/v1/db/eva_units" style="background:rgba(0,0,0,0.5); border:1px solid var(--border); color:#fff; padding:8px 12px; border-radius:6px; font-size:12px; flex:1;">
                        </div>

                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:14px;">
                            <div>
                                <div style="font-size:11px; color:#94a3b8; margin-bottom:4px;">Request Payload (JSON)</div>
                                <textarea id="sandboxPayload" class="code-input-area" style="width:100%; height:120px; outline:none; resize:none;">{
  "name": "Eva-01",
  "status": "active",
  "location": "Sector-03",
  "power": 98.2
}</textarea>
                            </div>
                            <div>
                                <div style="font-size:11px; color:#94a3b8; margin-bottom:4px;">Server Response</div>
                                <div id="sandboxResponse" class="code-input-area" style="height:120px; color:var(--emerald);">// Awaiting transmission... Click 'Send Request'</div>
                            </div>
                        </div>

                        <button class="btn-send" onclick="sendSandboxRequest()">
                            <span>▶ Send Request</span>
                        </button>
                    </div>
                </div>

                <!-- VIEW 3: MEDIA CORE VAULT -->
                <div id="tabMedia" class="view-panel">
                    <div class="hud-card">
                        <div class="card-header-title">Media Core Vault</div>
                        <div style="font-size:11px; color:#94a3b8;">Upload and manage your binary media assets</div>

                        <div style="border:2px dashed var(--border); border-radius:10px; padding:30px; text-align:center; background:rgba(0,0,0,0.3);">
                            <input type="file" id="mediaUploadInput" style="display:none;" onchange="handleMediaFile(this)">
                            <div style="cursor:pointer;" onclick="document.getElementById('mediaUploadInput').click()">
                                <div style="font-size:14px; font-weight:700; color:var(--cyan); margin-bottom:4px;">Drag & drop files here or click to browse</div>
                                <div style="font-size:11px; color:#64748b;">Images, Payloads, Secure Assets</div>
                            </div>
                        </div>

                        <div id="mediaOutputLink" style="font-family:'JetBrains Mono'; font-size:11px; color:var(--cyan);"></div>
                    </div>
                </div>

                <!-- VIEW 4: TACTICAL PROTOCOL DOCS -->
                <div id="tabDocs" class="view-panel">
                    <div class="hud-card">
                        <div class="card-header-title">Tactical Protocol Docs</div>
                        <div style="font-size:11px; color:#94a3b8;">API Reference & Developer Quick Guide</div>

                        <div class="code-input-area" style="height:140px; color:#fff;">
// Authentication Header:
x-api-key: akhi_live_...

// POST Ingest Payload:
POST /api/v1/db/&lt;collection_name&gt;

// GET Retrieve Sector:
GET /api/v1/db/&lt;collection_name&gt;
                        </div>
                    </div>
                </div>

                <!-- BOTTOM 3-COL ROW (MATCHING SCREENSHOT) -->
                <div class="bottom-grid">
                    <div class="hud-card">
                        <div class="card-header-title">Transmission Sandbox</div>
                        <div style="font-size:10px; color:#64748b;">Fast Endpoint Ping</div>
                        <div class="code-input-area" style="height:70px;">POST /api/v1/db/eva_units<br>Status: 200 OK</div>
                    </div>
                    <div class="hud-card">
                        <div class="card-header-title">Media Core Vault</div>
                        <div style="font-size:10px; color:#64748b;">Vault Storage</div>
                        <div class="code-input-area" style="height:70px;">eva-01.jpg (2.4 MB)<br>cyber_bg.mp4 (12.0 MB)</div>
                    </div>
                    <div class="hud-card">
                        <div class="card-header-title">Tactical Protocol Docs</div>
                        <div style="font-size:10px; color:#64748b;">Endpoints Index</div>
                        <div class="code-input-area" style="height:70px;">Authentication & API Keys<br>Database Endpoints</div>
                    </div>
                </div>
            </div>

            <!-- RIGHT SIDEBAR -->
            <div class="right-sidebar">
                <div class="character-img-banner"></div>
                
                <div class="flask-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:12px; font-weight:800;">FLASK API ENGINE</span>
                        <span style="font-size:10px; color:#64748b;">v1.0.0</span>
                    </div>
                    <div style="font-size:10px; color:var(--cyan); font-family:'JetBrains Mono';">MULTI-TENANT • CORS • JSON LEDGER<br>// クラウドで動作中</div>
                </div>

                <div class="hud-card">
                    <div style="font-size:11px; font-weight:800; color:var(--cyan); text-transform:uppercase;">Server Status</div>
                    <div class="status-list">
                        <div class="status-item"><span>Status</span><b style="color:var(--emerald);">Online</b></div>
                        <div class="status-item"><span>Host</span><b>0.0.0.0</b></div>
                        <div class="status-item"><span>Port</span><b>10000</b></div>
                        <div class="status-item"><span>Env</span><b>Production</b></div>
                    </div>
                </div>

                <div class="hud-card">
                    <div style="font-size:11px; font-weight:800; color:var(--cyan); text-transform:uppercase;">Quick Stats</div>
                    <div class="status-list">
                        <div class="status-item"><span>Total Keys</span><b id="statKeysCount">3</b></div>
                        <div class="status-item"><span>Total Hits</span><b>392</b></div>
                        <div class="status-item"><span>Collections</span><b>5</b></div>
                        <div class="status-item"><span>Media Files</span><b>12</b></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- FOOTER BAR -->
        <div class="footer-bar">
            <span>AKHIL DEV PLATFORM &nbsp;//&nbsp; Powered by Flask + Firebase &nbsp;//&nbsp; 24/7 Uptime</span>
            <span>// あなたのアイデアは、世界を変える</span>
        </div>

        <script>
            let firstActiveKey = "";

            function switchMainTab(tabId) {
                document.querySelectorAll('.hud-tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active'));
                
                // Sidebar active switch
                document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));

                if(event && event.target && event.target.classList.contains('hud-tab-btn')) {
                    event.target.classList.add('active');
                }
                const panel = document.getElementById(tabId);
                if(panel) panel.classList.add('active');
            }

            async function syncLedger() {
                const res = await fetch('/api/admin/keys/list');
                const d = await res.json();
                const tb = document.getElementById("keysTableBody");
                tb.innerHTML = "";
                let count = 0;
                for (let k in d.keys) {
                    count++;
                    const item = d.keys[k];
                    if(!firstActiveKey && item.active) firstActiveKey = k;
                    tb.innerHTML += `<tr>
                        <td><span class="key-mono">${k.substring(0, 14)}...</span></td>
                        <td><div style="font-weight:700;">${item.email || 'akhil@example.com'}</div><div style="font-size:9px; color:#64748b;">UID: 7aK9...3dF2</div></td>
                        <td><span class="${item.active ? 'badge-active' : 'badge-revoked'}">${item.active ? 'ACTIVE' : 'REVOKED'}</span></td>
                        <td style="font-family:'JetBrains Mono';">${item.hits || 0}</td>
                        <td>
                            <button onclick="toggleKey('${k}')" style="background:transparent; border:1px solid rgba(255,255,255,0.2); color:${item.active ? 'var(--red)' : 'var(--emerald)'}; padding:2px 8px; border-radius:4px; font-size:10px; cursor:pointer;">
                                ${item.active ? 'Revoke' : 'Allow'}
                            </button>
                        </td>
                    </tr>`;
                }
                document.getElementById("statPasses").innerText = `${count} / 10`;
                document.getElementById("statKeysCount").innerText = count;
            }

            async function toggleKey(k) {
                await fetch('/api/admin/keys/toggle', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({key: k})
                });
                syncLedger();
            }

            async function quickGenerateKey() {
                await fetch('/api/admin/keys/create', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({app_name: 'eva_units', email: 'akhil@example.com'})
                });
                syncLedger();
            }

            function copyActiveKey() {
                if(!firstActiveKey) return alert("No active key found.");
                navigator.clipboard.writeText(firstActiveKey);
                alert("Copied active key to memory buffer.");
            }

            async function sendSandboxRequest() {
                const endpoint = document.getElementById("targetEndpoint").value.trim();
                const payload = document.getElementById("sandboxPayload").value;
                const respBox = document.getElementById("sandboxResponse");

                respBox.innerText = "// Transmitting request...";
                try {
                    const res = await fetch(endpoint, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'x-api-key': firstActiveKey
                        },
                        body: payload
                    });
                    const data = await res.json();
                    respBox.innerText = JSON.stringify(data, null, 2);
                    syncLedger();
                } catch(e) {
                    respBox.innerText = "// Error: " + e.message;
                }
            }

            async function handleMediaFile(input) {
                const f = input.files[0];
                if(!f) return;
                const fd = new FormData();
                fd.append("file", f);
                const out = document.getElementById("mediaOutputLink");
                out.innerText = "// Uploading...";
                const res = await fetch('/api/v1/media/upload', {method: 'POST', body: fd});
                const d = await res.json();
                if(d.status === "success") {
                    out.innerHTML = `✓ Uploaded: <a href="${d.url}" target="_blank" style="color:var(--cyan);">${d.url}</a>`;
                }
            }

            syncLedger();
        </script>
    </body>
    </html>
    """)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
