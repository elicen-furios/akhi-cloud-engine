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
        "cluster": "NEO-TOKYO-EDGE-01",
        "protocol": "CYBER_REST_V4",
        "firebase_auth": "ENFORCED"
    })

@app.route('/api/admin/keys/list', methods=['GET'])
def list_keys():
    return jsonify({"keys": read_db().get("keys", {})})

@app.route('/api/admin/keys/create', methods=['POST'])
def create_key():
    req = request.get_json(silent=True) or {}
    uid = req.get("uid")
    email = req.get("email", "Anonymous")
    name = req.get("app_name", "CHRONO_CORE").strip() or "NEO_PROJECT"
    
    if not uid:
        return jsonify({"status": "error", "message": "Firebase Authentication Required"}), 401

    key = f"akhi_live_{secrets.token_urlsafe(18)}"
    db = read_db()
    db.setdefault("keys", {})[key] = {
        "app": name,
        "owner": email,
        "uid": uid,
        "created": time.strftime("%Y-%m-%d %H:%M"),
        "hits": 0,
        "active": True
    }
    write_db(db)
    return jsonify({"status": "success", "key": key, "app": name, "owner": email})

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
        return jsonify({"status": "success", "sector": collection, "records": items})
    
    key = request.headers.get("x-api-key") or request.args.get("api_key")
    keys = db.get("keys", {})
    if not key or key not in keys or not keys[key].get("active"):
        return jsonify({"status": "unauthorized", "message": "Security clearance denied. Valid key required."}), 403
    
    keys[key]["hits"] = keys[key].get("hits", 0) + 1
    if collection not in db["collections"]:
        db["collections"][collection] = []
    
    item = {
        "_id": secrets.token_hex(6),
        "origin": keys[key].get("app", "Agent"),
        "timestamp": time.strftime("%H:%M:%S // UTC"),
        "payload": request.get_json(silent=True) or {}
    }
    db["collections"][collection].append(item)
    write_db(db)
    return jsonify({"status": "success", "record": item})

@app.route('/api/v1/media/upload', methods=['POST'])
def media_upload():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file stream detected"}), 400
    f = request.files['file']
    s_name = f"{int(time.time())}_{secrets.token_hex(4)}_{secure_filename(f.filename)}"
    f.save(os.path.join(MEDIA_DIR, s_name))
    return jsonify({"status": "success", "url": f"/media/{s_name}"})

@app.route('/media/<path:fname>')
def media_serve(fname):
    return send_from_directory(MEDIA_DIR, secure_filename(fname))

# ========================================================
# REAL FIREBASE AUTH + KEY FORGE PORTAL (/portal/keys)
# ========================================================
@app.route('/portal/keys')
def key_provision_portal():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AKHI // ACCESS FORGE • セキュリティ認証</title>
        <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@600;800;900&family=Rajdhani:wght@600;700&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --cyan: #00f0ff;
                --magenta: #ff007f;
                --yellow: #ffe600;
                --bg: #030712;
            }
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Rajdhani', sans-serif; }
            body {
                background: linear-gradient(135deg, rgba(3,7,18,0.92), rgba(5,12,30,0.96)),
                            url('https://images.unsplash.com/photo-1578632767115-351597cf2477?q=80&w=1600&auto=format&fit=crop') center/cover fixed;
                color: #fff; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px;
            }
            .auth-card {
                background: rgba(8, 14, 30, 0.88); backdrop-filter: blur(24px);
                border: 1px solid rgba(0, 240, 255, 0.4); max-width: 480px; width: 100%; padding: 36px;
                box-shadow: 0 0 45px rgba(0, 240, 255, 0.25); position: relative;
                clip-path: polygon(0 0, calc(100% - 20px) 0, 100% 20px, 100% 100%, 20px 100%, 0 calc(100% - 20px));
            }
            .auth-card::before { content: ''; position: absolute; top:0; left:0; width:100%; height:3px; background: linear-gradient(90deg, var(--cyan), var(--magenta)); }
            .tag { font-family: 'Orbitron'; font-size: 11px; letter-spacing: 2px; color: var(--cyan); text-transform: uppercase; margin-bottom: 6px; }
            h1 { font-family: 'Orbitron'; font-size: 24px; font-weight: 900; letter-spacing: 1px; }
            .jp-sub { color: var(--magenta); font-size: 11px; letter-spacing: 3px; font-weight: 700; margin-bottom: 24px; }
            .form-box { display: flex; flex-direction: column; gap: 14px; }
            input {
                background: rgba(2, 4, 10, 0.85); border: 1px solid rgba(0, 240, 255, 0.25);
                padding: 13px 16px; color: #fff; font-size: 14px; font-weight: 600; outline: none; width: 100%;
            }
            input:focus { border-color: var(--cyan); box-shadow: 0 0 15px rgba(0, 240, 255, 0.4); }
            .btn-cyber {
                background: linear-gradient(90deg, var(--cyan), #0077ff); color: #000;
                font-family: 'Orbitron'; font-weight: 900; font-size: 13px; padding: 14px; border: none;
                cursor: pointer; letter-spacing: 1.5px; text-transform: uppercase; margin-top: 6px;
                transition: transform 0.15s, box-shadow 0.15s;
            }
            .btn-cyber:hover { box-shadow: 0 0 25px rgba(0, 240, 255, 0.6); }
            .btn-google {
                background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255,255,255,0.2);
                color: #fff; font-family: 'Orbitron'; font-size: 11px; font-weight: 700; padding: 12px;
                cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 10px;
                letter-spacing: 1px; text-transform: uppercase; margin-top: 8px;
            }
            .btn-google:hover { background: rgba(255, 255, 255, 0.16); }
            .logged-panel { display: none; flex-direction: column; gap: 16px; }
            .token-box { background: #000; border: 1px solid var(--magenta); padding: 16px; display: none; margin-top: 10px; }
            .token-str { font-family: 'JetBrains Mono'; font-size: 12px; color: var(--cyan); word-break: break-all; margin: 8px 0; }
        </style>
        <!-- Firebase SDKs -->
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
                if(user) {
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
                if(!email || !pass) return alert("Credentials required");
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
                if(!currentUser) return alert("Login required!");
                const appName = document.getElementById("appName").value.trim() || "VALKYRIE_NODE";
                const res = await fetch('/api/admin/keys/create', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        uid: currentUser.uid,
                        email: currentUser.email,
                        app_name: appName
                    })
                });
                const d = await res.json();
                if(d.status === "success") {
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
        <div class="auth-card">
            <div class="tag">Security Protocol Gate</div>
            <h1>Authentication Forge</h1>
            <div class="jp-sub">// セキュリティ認証・鍵生成システム</div>

            <!-- UN-AUTHENTICATED FORM -->
            <div id="authSection" class="form-box">
                <input type="email" id="authEmail" value="operative@akhi.cloud" placeholder="Operative Email">
                <input type="password" id="authPass" value="CyberStrike2026#" placeholder="Access Secret">
                <button class="btn-cyber" onclick="handleEmailAuth()">Authorize / Register</button>
                <button class="btn-google" onclick="handleGoogleAuth()">
                    <svg width="14" height="14" viewBox="0 0 24 24"><path fill="#fff" d="M12.48 10.92v3.28h7.84c-.24 1.84-.853 3.187-1.787 4.133-1.147 1.147-2.933 2.4-6.053 2.4-4.827 0-8.6-3.893-8.6-8.72s3.773-8.72 8.6-8.72c2.6 0 4.507 1.027 5.907 2.347l2.307-2.307C18.747 1.44 16.133 0 12.48 0 5.867 0 .307 5.387.307 12s5.56 12 12.173 12c3.573 0 6.267-1.173 8.373-3.36 2.16-2.16 2.84-5.213 2.84-7.667 0-.76-.053-1.467-.173-2.053H12.48z"/></svg>
                    Continue with Google ID
                </button>
            </div>

            <!-- AUTHENTICATED KEY GENERATOR -->
            <div id="forgeSection" class="logged-panel">
                <div id="userGreeting" style="font-family:'JetBrains Mono'; font-size:12px; color:var(--cyan);"></div>
                <input type="text" id="appName" value="PROJECT_GHOST_RUNNER" placeholder="Project Codename">
                <button class="btn-cyber" onclick="forgePass()">Issue Cryptographic Pass</button>
                <div id="tokenDisplay" class="token-box">
                    <div style="font-family:'Orbitron'; font-size:10px; color:var(--magenta);">DEPLOYED DIGITAL TOKEN:</div>
                    <div class="token-str" id="tokenStr"></div>
                    <button class="btn-cyber" style="padding:8px 12px; font-size:11px;" onclick="copyPass()">Copy Token</button>
                </div>
                <button onclick="handleSignOut()" style="background:transparent; border:1px solid rgba(255,255,255,0.2); color:#94a3b8; padding:8px; cursor:pointer; font-family:'Orbitron'; font-size:10px; text-transform:uppercase;">Sign Out</button>
            </div>
        </div>
    </body>
    </html>
    """)

# ========================================================
# MAIN COMMAND NEXUS INTERFACE (ROOT /)
# ========================================================
@app.route('/')
def main_console():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AKHI // COMMAND NEXUS • アニメ中枢</title>
        <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@600;800;900&family=Rajdhani:wght@600;700&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --cyan: #00f0ff;
                --magenta: #ff007f;
                --yellow: #ffe600;
                --emerald: #00ff88;
                --hud-bg: rgba(6, 11, 25, 0.88);
                --hud-border: rgba(0, 240, 255, 0.35);
            }
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Rajdhani', sans-serif; }
            body {
                background: linear-gradient(180deg, rgba(3, 7, 18, 0.94) 0%, rgba(5, 12, 30, 0.94) 100%),
                            url('https://images.unsplash.com/photo-1578632767115-351597cf2477?q=80&w=1920&auto=format&fit=crop') center/cover fixed;
                color: #e2e8f0; min-height: 100vh; padding: 20px; position: relative; overflow-x: hidden;
            }
            body::before {
                content: " "; display: block; position: fixed; top: 0; left: 0; bottom: 0; right: 0;
                background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.03), rgba(0, 255, 0, 0.01), rgba(0, 255, 0, 0.03));
                z-index: 100; background-size: 100% 3px, 6px 100%; pointer-events: none;
            }
            .layout { max-width: 1280px; margin: 0 auto; display: flex; flex-direction: column; gap: 24px; position: relative; z-index: 10; }

            /* HUD NAVIGATION BAR */
            .nav-bar {
                background: var(--hud-bg); backdrop-filter: blur(24px); border: 1px solid var(--hud-border);
                padding: 16px 24px; display: flex; justify-content: space-between; align-items: center;
                clip-path: polygon(0 0, calc(100% - 15px) 0, 100% 15px, 100% 100%, 15px 100%, 0 calc(100% - 15px));
            }
            .brand-left { display: flex; align-items: center; gap: 14px; }
            .menu-trigger {
                width: 38px; height: 38px; border: 1px solid var(--cyan); background: rgba(0, 240, 255, 0.1);
                display: grid; place-items: center; cursor: pointer; transition: all 0.2s;
            }
            .menu-trigger:hover { background: var(--cyan); box-shadow: 0 0 20px var(--cyan); }
            .menu-trigger:hover svg { stroke: #000; }
            .brand-title { font-family: 'Orbitron'; font-size: 18px; font-weight: 900; letter-spacing: 2px; }
            .brand-jp { font-size: 10px; letter-spacing: 4px; color: var(--cyan); font-weight: 700; }

            .btn-forge-portal {
                background: linear-gradient(90deg, var(--magenta), #a855f7); color: #fff; text-decoration: none;
                font-family: 'Orbitron'; font-size: 12px; font-weight: 800; padding: 12px 22px; letter-spacing: 1.5px;
                text-transform: uppercase; box-shadow: 0 0 25px rgba(255, 0, 127, 0.45); transition: 0.2s;
            }
            .btn-forge-portal:hover { box-shadow: 0 0 35px rgba(255, 0, 127, 0.8); transform: translateY(-1px); }

            /* INTERACTIVE OVERLAY MENU (CLICK ICON OPENS THIS) */
            .side-drawer {
                position: fixed; top: 0; left: -320px; width: 300px; height: 100%;
                background: rgba(4, 8, 20, 0.96); backdrop-filter: blur(30px); border-right: 2px solid var(--cyan);
                z-index: 1000; transition: left 0.3s ease; padding: 30px 24px; display: flex; flex-direction: column; gap: 20px;
                box-shadow: 10px 0 50px rgba(0,0,0,0.8);
            }
            .side-drawer.open { left: 0; }
            .drawer-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--hud-border); padding-bottom: 14px; }
            .drawer-link {
                text-decoration: none; color: #fff; font-family: 'Orbitron'; font-size: 13px; font-weight: 700;
                letter-spacing: 1.5px; padding: 12px 16px; border: 1px solid rgba(255,255,255,0.06); background: rgba(0,0,0,0.4);
                display: flex; align-items: center; justify-content: space-between; transition: 0.2s;
            }
            .drawer-link:hover { border-color: var(--cyan); background: rgba(0, 240, 255, 0.1); color: var(--cyan); }

            /* HORIZONTAL SCROLLABLE CYBER SHOWCASE */
            .scroll-strip-wrap { overflow-x: auto; padding-bottom: 10px; }
            .scroll-strip-wrap::-webkit-scrollbar { height: 4px; }
            .scroll-strip-wrap::-webkit-scrollbar-thumb { background: var(--cyan); }
            .scroll-strip { display: flex; gap: 16px; min-width: 900px; }
            .showcase-card {
                background: var(--hud-bg); border: 1px solid var(--hud-border); padding: 16px 20px; min-width: 240px;
                display: flex; flex-direction: column; gap: 8px; border-left: 4px solid var(--cyan);
            }
            .showcase-card.magenta { border-left-color: var(--magenta); }
            .showcase-card.yellow { border-left-color: var(--yellow); }
            .showcase-card .title { font-family: 'Orbitron'; font-size: 10px; letter-spacing: 1.5px; color: #94a3b8; }
            .showcase-card .val { font-family: 'Orbitron'; font-size: 20px; font-weight: 800; color: #fff; }

            /* TAB CONTROLS (ALAG BUTTON PAR ALAG REAL SCREEN) */
            .tabs-wrap { display: flex; gap: 10px; background: rgba(0,0,0,0.6); padding: 8px; border: 1px solid var(--hud-border); }
            .tab-btn {
                background: transparent; border: none; color: #94a3b8; padding: 12px 24px; font-family: 'Orbitron';
                font-size: 12px; font-weight: 700; letter-spacing: 1px; cursor: pointer; text-transform: uppercase; transition: 0.2s;
            }
            .tab-btn.active { background: var(--cyan); color: #000; box-shadow: 0 0 20px rgba(0, 240, 255, 0.6); }

            .panel { display: none; background: var(--hud-bg); backdrop-filter: blur(20px); border: 1px solid var(--hud-border); padding: 26px; }
            .panel.active { display: block; }

            /* TABLE */
            .table-box { overflow-x: auto; border: 1px solid rgba(0, 240, 255, 0.2); margin-top: 14px; }
            table { width: 100%; border-collapse: collapse; font-size: 14px; }
            th { text-align: left; padding: 14px 18px; background: rgba(0, 240, 255, 0.05); color: var(--cyan); font-family: 'Orbitron'; font-size: 11px; letter-spacing: 1.5px; border-bottom: 1px solid rgba(0, 240, 255, 0.2); }
            td { padding: 14px 18px; border-bottom: 1px solid rgba(255, 255, 255, 0.04); font-weight: 600; }
            .token-pill { font-family: 'JetBrains Mono'; font-size: 12px; color: var(--cyan); background: rgba(0, 240, 255, 0.08); padding: 4px 8px; border-radius: 4px; }

            /* INPUTS & CONTROLS (PRE-FILLED WITH REAL VALUES) */
            .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
            @media(max-width: 800px) { .form-grid { grid-template-columns: 1fr; } }
            input {
                background: rgba(2, 4, 10, 0.8); border: 1px solid rgba(0, 240, 255, 0.3); padding: 12px 16px;
                color: #fff; font-size: 14px; font-weight: 600; outline: none; width: 100%;
            }
            input:focus { border-color: var(--cyan); box-shadow: 0 0 15px rgba(0, 240, 255, 0.3); }
            .btn-action {
                background: linear-gradient(90deg, var(--cyan), #0077ff); color: #000; font-family: 'Orbitron';
                font-weight: 800; font-size: 12px; padding: 14px 24px; border: none; cursor: pointer; letter-spacing: 1.5px; text-transform: uppercase;
            }
            .terminal-view {
                background: #000; border: 1px solid var(--hud-border); padding: 16px; font-family: 'JetBrains Mono';
                font-size: 12px; color: var(--cyan); margin-top: 14px; line-height: 1.6;
            }
        </style>
    </head>
    <body>
        <!-- SIDE DRAWER OVERLAY -->
        <div id="sideDrawer" class="side-drawer">
            <div class="drawer-header">
                <span style="font-family:'Orbitron'; font-size:14px; color:var(--cyan); font-weight:900;">HUD PROTOCOLS</span>
                <span onclick="toggleMenu()" style="cursor:pointer; color:#94a3b8; font-family:'Orbitron'; font-size:14px;">[X]</span>
            </div>
            <a href="/portal/keys" target="_blank" class="drawer-link">
                <span>Issue API Pass</span>
                <span style="color:var(--magenta);">↗</span>
            </a>
            <a href="javascript:void(0)" onclick="switchTab('screenKeys'); toggleMenu();" class="drawer-link">
                <span>Access Passcodes</span>
                <span style="color:var(--cyan);">></span>
            </a>
            <a href="javascript:void(0)" onclick="switchTab('screenSim'); toggleMenu();" class="drawer-link">
                <span>Transmission Sandbox</span>
                <span style="color:var(--yellow);">></span>
            </a>
            <a href="javascript:void(0)" onclick="switchTab('screenMedia'); toggleMenu();" class="drawer-link">
                <span>Media Core Vault</span>
                <span style="color:var(--emerald);">></span>
            </a>
        </div>

        <div class="layout">
            <!-- TOP NAV -->
            <div class="nav-bar">
                <div class="brand-left">
                    <div class="menu-trigger" onclick="toggleMenu()">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
                    </div>
                    <div>
                        <div class="brand-title">AKHI // NEXUS</div>
                        <div class="brand-jp">// システム中枢・東京第参管区</div>
                    </div>
                </div>
                <a href="/portal/keys" target="_blank" class="btn-forge-portal">
                    [+] Get API Key ↗
                </a>
            </div>

            <!-- HORIZONTAL SCROLLABLE CYBER STRIP -->
            <div class="scroll-strip-wrap">
                <div class="scroll-strip">
                    <div class="showcase-card">
                        <div class="title">FIREBASE IDENTITY GATE</div>
                        <div class="val" style="color:var(--emerald);">ENFORCED 24/7</div>
                    </div>
                    <div class="showcase-card magenta">
                        <div class="title">CORE PROTOCOL CLUSTER</div>
                        <div class="val" style="color:var(--magenta);">FRANKFURT EDGE</div>
                    </div>
                    <div class="showcase-card yellow">
                        <div class="title">ACTIVE ACCESS TOKENS</div>
                        <div class="val" id="statKeys">0</div>
                    </div>
                    <div class="showcase-card">
                        <div class="title">ENCRYPTION ENGINE</div>
                        <div class="val" style="color:var(--cyan);">TLS 1.3 / REST</div>
                    </div>
                </div>
            </div>

            <!-- NAVIGATION BUTTONS (ALAG-ALAG SCREENS) -->
            <div class="tabs-wrap">
                <button class="tab-btn active" onclick="switchTab('screenKeys')">Passcode Ledger</button>
                <button class="tab-btn" onclick="switchTab('screenSim')">Interactive Sandbox</button>
                <button class="tab-btn" onclick="switchTab('screenMedia')">Media Core Ingestion</button>
            </div>

            <!-- SCREEN 1: PASSCODE LEDGER -->
            <div id="screenKeys" class="panel active">
                <div style="font-family:'Orbitron'; font-size:14px; font-weight:800; color:var(--cyan); text-transform:uppercase;">
                    Cryptographic Passes Ledger
                </div>
                <div class="table-box">
                    <table>
                        <thead>
                            <tr>
                                <th>Codename</th>
                                <th>Owner (Firebase)</th>
                                <th>Digital Pass</th>
                                <th>Hits</th>
                                <th>Status</th>
                                <th>Emergency Kill</th>
                            </tr>
                        </thead>
                        <tbody id="keysTable"></tbody>
                    </table>
                </div>
            </div>

            <!-- SCREEN 2: SIMULATOR SANDBOX (PRE-FILLED VALUES) -->
            <div id="screenSim" class="panel">
                <div style="font-family:'Orbitron'; font-size:14px; font-weight:800; color:var(--yellow); margin-bottom:14px;">
                    Direct Payload Transmitter
                </div>
                <div class="form-grid">
                    <input type="text" id="simKey" value="akhi_live_S_FeQXGXJfdfN8Q0yxA4Aw" placeholder="Enter Valid Passcode">
                    <input type="text" id="simSector" value="tactical_telemetry" placeholder="Target Sector">
                </div>
                <div style="display:flex; gap:10px; margin-top:12px;">
                    <input type="text" id="simPayload" value='{"unit": "EVA_01", "sync_ratio": "98.4%", "combat_mode": "ACTIVE"}'>
                    <button class="btn-action" onclick="execTransmit()">Transmit Packet</button>
                </div>
                <div id="simLog" class="terminal-view">// Ingestion pipeline ready. Awaiting packet push...</div>
            </div>

            <!-- SCREEN 3: MEDIA VAULT (PRE-CONFIGURED) -->
            <div id="screenMedia" class="panel">
                <div style="font-family:'Orbitron'; font-size:14px; font-weight:800; color:var(--emerald); margin-bottom:14px;">
                    Binary Media Storage Vault
                </div>
                <div style="display:flex; gap:12px; align-items:center;">
                    <input type="file" id="mediaFile">
                    <button class="btn-action" onclick="execMediaUpload()">Upload Artifact</button>
                </div>
                <div id="mediaLog" class="terminal-view">// Storage core connected. Upload assets directly to persistent cloud.</div>
            </div>
        </div>

        <script>
            function toggleMenu() {
                document.getElementById("sideDrawer").classList.toggle("open");
            }

            function switchTab(id) {
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
                event.target.classList.add('active');
                document.getElementById(id).classList.add('active');
            }

            async function refreshKeys() {
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
                        <td style="color:#94a3b8; font-family:'JetBrains Mono'; font-size:11px;">${item.owner || 'Legacy'}</td>
                        <td><span class="token-pill">${k}</span></td>
                        <td>${item.hits || 0}</td>
                        <td style="color:${item.active ? 'var(--emerald)' : 'var(--magenta)'}; font-family:'Orbitron'; font-size:11px;">
                            ${item.active ? 'ACTIVE' : 'REVOKED'}
                        </td>
                        <td>
                            <button style="background:transparent; border:1px solid rgba(255,255,255,0.2); color:${item.active ? 'var(--magenta)' : 'var(--emerald)'}; padding:4px 10px; font-family:'Orbitron'; font-size:10px; cursor:pointer;" onclick="toggleAccess('${k}')">
                                ${item.active ? 'REVOKE' : 'RESTORE'}
                            </button>
                        </td>
                    </tr>`;
                }
                document.getElementById("statKeys").innerText = count;
            }

            async function toggleAccess(k) {
                await fetch('/api/admin/keys/toggle', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({key: k})
                });
                refreshKeys();
            }

            async function execTransmit() {
                const k = document.getElementById("simKey").value.trim();
                const sec = document.getElementById("simSector").value.trim();
                const p = document.getElementById("simPayload").value || '{}';
                const log = document.getElementById("simLog");
                log.innerText = "// Transmitting to sector: " + sec + "...";
                
                try {
                    const res = await fetch(`/api/v1/db/${sec}`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json', 'x-api-key': k},
                        body: p
                    });
                    const d = await res.json();
                    log.innerText = JSON.stringify(d, null, 2);
                    refreshKeys();
                } catch(err) {
                    log.innerText = "// Transmission error: " + err.message;
                }
            }

            async function execMediaUpload() {
                const f = document.getElementById("mediaFile").files[0];
                if(!f) return alert("Select artifact first");
                const fd = new FormData();
                fd.append("file", f);
                const log = document.getElementById("mediaLog");
                log.innerText = "// Uploading binary artifact to Render storage...";
                const res = await fetch('/api/v1/media/upload', {method: 'POST', body: fd});
                const d = await res.json();
                log.innerText = JSON.stringify(d, null, 2);
            }

            refreshKeys();
        </script>
    </body>
    </html>
    """)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
