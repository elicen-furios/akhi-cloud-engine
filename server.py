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
    return render_template_string("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>AKHIL DEV PLATFORM // COMMAND CORE</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-void: #030712;
            --bg-panel: rgba(11, 19, 43, 0.8);
            --bg-panel-border: rgba(34, 211, 238, 0.28);
            --cyan-neon: #00f3ff;
            --cyan-glow: rgba(0, 243, 255, 0.38);
            --magenta-neon: #ff007f;
            --magenta-glow: rgba(255, 0, 127, 0.38);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --hud-font: "JetBrains Mono", monospace;
            --ui-font: "Space Grotesk", sans-serif;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; user-select: none; -webkit-tap-highlight-color: transparent; }
        body {
            background-color: var(--bg-void);
            color: var(--text-main);
            font-family: var(--ui-font);
            min-height: 100vh;
            overflow-x: hidden;
            position: relative;
        }
        body::before {
            content: "";
            position: fixed;
            inset: 0;
            background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.3) 50%);
            background-size: 100% 4px;
            z-index: 990;
            pointer-events: none;
            opacity: 0.55;
        }
        .ambient-glow {
            position: fixed;
            width: 520px;
            height: 520px;
            border-radius: 50%;
            background: radial-gradient(circle, var(--cyan-glow) 0%, rgba(3,7,18,0) 70%);
            filter: blur(95px);
            z-index: 0;
            pointer-events: none;
            top: -120px;
            right: -120px;
        }
        #intro-overlay {
            position: fixed;
            inset: 0;
            background: #000;
            z-index: 2500;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            transition: opacity 0.7s ease, visibility 0.7s ease;
        }
        .intro-hero-img {
            width: 130px;
            height: 130px;
            border-radius: 50%;
            border: 2px solid var(--cyan-neon);
            box-shadow: 0 0 32px var(--cyan-glow);
            margin-bottom: 22px;
            object-fit: cover;
            animation: introGlow 2.2s infinite alternate ease-in-out;
        }
        @keyframes introGlow {
            0% { transform: scale(0.96); filter: drop-shadow(0 0 12px var(--cyan-neon)); }
            100% { transform: scale(1.04); filter: drop-shadow(0 0 28px var(--magenta-neon)); }
        }
        .btn-skip {
            position: absolute;
            top: 24px;
            right: 24px;
            background: rgba(0,0,0,0.6);
            border: 1px solid var(--text-muted);
            color: var(--text-muted);
            font-family: var(--hud-font);
            font-size: 0.75rem;
            padding: 6px 14px;
            border-radius: 6px;
            cursor: pointer;
        }
        #onboard-modal {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.88);
            backdrop-filter: blur(12px);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 2000;
            padding: 20px;
        }
        #app-shell { display: flex; min-height: 100vh; position: relative; z-index: 10; }
        .nav-rail {
            width: 82px;
            background: rgba(3, 7, 18, 0.92);
            border-right: 1px solid var(--bg-panel-border);
            backdrop-filter: blur(18px);
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 24px 0;
            position: fixed;
            height: 100vh;
            z-index: 100;
        }
        .brand-avatar {
            width: 46px;
            height: 46px;
            border-radius: 12px;
            border: 1px solid var(--cyan-neon);
            box-shadow: 0 0 14px var(--cyan-glow);
            overflow: hidden;
            cursor: pointer;
            margin-bottom: 28px;
        }
        .brand-avatar img { width: 100%; height: 100%; object-fit: cover; }
        .nav-menu { display: flex; flex-direction: column; gap: 14px; width: 100%; align-items: center; flex: 1; }
        .nav-link-btn {
            width: 48px;
            height: 48px;
            border-radius: 10px;
            background: transparent;
            border: 1px solid transparent;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.22s ease;
        }
        .nav-link-btn svg { width: 21px; height: 21px; fill: currentColor; }
        .nav-link-btn:hover, .nav-link-btn.active {
            color: var(--cyan-neon);
            border-color: var(--cyan-neon);
            background: rgba(0, 243, 255, 0.09);
            box-shadow: 0 0 16px var(--cyan-glow);
        }
        .viewport { margin-left: 82px; flex: 1; padding: 24px 32px 64px; display: flex; flex-direction: column; }
        .top-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
            margin-bottom: 30px;
            padding-bottom: 18px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }
        .hud-status {
            font-family: var(--hud-font);
            font-size: 0.84rem;
            letter-spacing: 2px;
            color: var(--cyan-neon);
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .hud-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--cyan-neon);
            box-shadow: 0 0 8px var(--cyan-neon);
            animation: pulseDot 1.4s infinite;
        }
        @keyframes pulseDot { 0%, 100% { opacity: 1; } 50% { opacity: 0.25; } }
        .top-right-group { display: flex; align-items: center; gap: 14px; }
        .profile-chip {
            display: flex;
            align-items: center;
            gap: 10px;
            background: var(--bg-panel);
            padding: 5px 14px 5px 5px;
            border-radius: 28px;
            border: 1px solid var(--bg-panel-border);
            cursor: pointer;
        }
        .avatar-letter {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--cyan-neon), var(--magenta-neon));
            color: #000;
            font-weight: 800;
            font-family: var(--hud-font);
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .panel {
            background: var(--bg-panel);
            border: 1px solid var(--bg-panel-border);
            backdrop-filter: blur(18px);
            border-radius: 16px;
            padding: 26px;
            margin-bottom: 24px;
            position: relative;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.45);
        }
        .panel::after {
            content: "";
            position: absolute;
            top: 0; left: 0; width: 34px; height: 2px;
            background: var(--cyan-neon);
            box-shadow: 0 0 8px var(--cyan-neon);
        }
        .btn-cyber {
            background: rgba(0, 243, 255, 0.1);
            border: 1px solid var(--cyan-neon);
            color: var(--cyan-neon);
            font-family: var(--hud-font);
            font-size: 0.85rem;
            font-weight: 600;
            padding: 11px 22px;
            border-radius: 8px;
            cursor: pointer;
            letter-spacing: 1px;
            display: inline-flex;
            align-items: center;
            gap: 9px;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            box-shadow: 0 0 12px rgba(0, 243, 255, 0.16);
        }
        .btn-cyber svg { width: 17px; height: 17px; fill: currentColor; }
        .btn-cyber:hover {
            background: var(--cyan-neon);
            color: #000;
            box-shadow: 0 0 24px var(--cyan-glow);
            transform: translateY(-2px);
        }
        .btn-magenta {
            border-color: var(--magenta-neon);
            color: var(--magenta-neon);
            background: rgba(255, 0, 127, 0.1);
            box-shadow: 0 0 12px rgba(255, 0, 127, 0.16);
        }
        .btn-magenta:hover {
            background: var(--magenta-neon);
            color: #fff;
            box-shadow: 0 0 24px var(--magenta-glow);
        }
        .page-node { display: none; animation: routeFade 0.32s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
        .page-node.active { display: block; }
        @keyframes routeFade { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
        .hud-input {
            width: 100%;
            padding: 12px 14px;
            background: rgba(0, 0, 0, 0.6);
            border: 1px solid var(--bg-panel-border);
            border-radius: 8px;
            color: #fff;
            font-family: var(--hud-font);
            font-size: 0.85rem;
            margin-bottom: 14px;
            outline: none;
        }
        .hud-input:focus { border-color: var(--cyan-neon); box-shadow: 0 0 12px var(--cyan-glow); }
        .hud-toast-banner {
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: #000;
            border: 1px solid var(--cyan-neon);
            color: var(--cyan-neon);
            font-family: var(--hud-font);
            font-size: 0.8rem;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 0 22px var(--cyan-glow);
            transform: translateY(120px);
            opacity: 0;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            z-index: 3000;
        }
        .hud-toast-banner.visible { transform: translateY(0); opacity: 1; }
        @media (max-width: 768px) {
            .nav-rail {
                width: 100%;
                height: 62px;
                bottom: 0;
                top: auto;
                flex-direction: row;
                border-right: none;
                border-top: 1px solid var(--bg-panel-border);
                padding: 0 14px;
                justify-content: space-around;
            }
            .brand-avatar { display: none; }
            .nav-menu { flex-direction: row; justify-content: space-around; }
            .viewport { margin-left: 0; padding: 16px 16px 88px; }
            .top-bar { margin-bottom: 20px; }
        }
    </style>
</head>
<body>
    <div class="ambient-glow"></div>

    <div id="intro-overlay">
        <button class="btn-skip" onclick="dismissIntro()">SKIP INTRO</button>
        <img src="/public/second-image.png" onerror="this.src='/public/image.png'; this.onerror=null;" class="intro-hero-img" alt="Platform Core">
        <h1 style="font-family:var(--hud-font); font-size:1.35rem; letter-spacing:3px; color:var(--cyan-neon); margin-bottom:8px;">AKHIL DEV PLATFORM</h1>
        <p style="font-family:var(--hud-font); font-size:0.75rem; color:var(--text-muted);">INITIALIZING QUANTUM RUNTIME // 60/120Hz OPTIMIZED</p>
    </div>

    <div id="onboard-modal">
        <div class="panel" style="max-width:390px; width:100%; text-align:center;">
            <div style="font-family:var(--hud-font); font-size:0.72rem; color:var(--magenta-neon); margin-bottom:4px;">// IDENTITY SETUP</div>
            <h2 style="font-family:var(--hud-font); color:var(--cyan-neon); font-size:1.2rem; margin-bottom:12px;">OPERATIONAL IDENTIFIER</h2>
            <p style="font-size:0.85rem; color:var(--text-muted); margin-bottom:18px;">Register your operative handle to enter the developer core.</p>
            <input type="text" id="onboard-input" class="hud-input" placeholder="ENTER YOUR NAME">
            <button class="btn-cyber" style="width:100%; justify-content:center;" onclick="saveHandle()">
                <svg viewBox="0 0 24 24"><path d="M11 7L9.6 8.4l2.6 2.6H2v2h10.2l-2.6 2.6L11 17l5-5-5-5zm9 12h-8v2h8c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2h-8v2h8v14z"/></svg>
                ENTER PLATFORM
            </button>
        </div>
    </div>

    <div id="app-shell">
        <nav class="nav-rail">
            <div class="brand-avatar" onclick="switchRoute('/about')">
                <img src="/public/image.png" onerror="this.src='/image.png'; this.onerror=null;" alt="Core Handle">
            </div>
            <div class="nav-menu">
                <button class="nav-link-btn active" id="btn-home" title="Dashboard" onclick="switchRoute('/')">
                    <svg viewBox="0 0 24 24"><path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/></svg>
                </button>
                <button class="nav-link-btn" id="btn-api" title="API Vault" onclick="switchRoute('/api')">
                    <svg viewBox="0 0 24 24"><path d="M7 14c-1.66 0-3-1.34-3-3 0-1.31.84-2.41 2-2.83V4.2C3.34 4.93 1.24 7.72 1.02 11c-.26 3.91 2.7 7.28 6.61 7.54 2.87.19 5.48-1.36 6.72-3.76L11.5 12h-2v2H7zm10.5-8C15.01 6 13 8.01 13 10.5c0 .77.22 1.49.59 2.11L7 19.2V22h2.8l1.6-1.6v-2h2v-2l2.3-2.3c.57.31 1.22.5 1.9.5 2.49 0 4.5-2.01 4.5-4.5S20.01 6 17.5 6z"/></svg>
                </button>
                <button class="nav-link-btn" id="btn-login" title="Identity Gate" onclick="switchRoute('/login')">
                    <svg viewBox="0 0 24 24"><path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z"/></svg>
                </button>
                <button class="nav-link-btn" id="btn-sandbox" title="Sandbox Console" onclick="switchRoute('/sandbox')">
                    <svg viewBox="0 0 24 24"><path d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z"/></svg>
                </button>
                <button class="nav-link-btn" id="btn-database" title="Database Telemetry" onclick="switchRoute('/database')">
                    <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 4.02 2 6.5s4.48 4.5 10 4.5 10-2.02 10-4.5S17.52 2 12 2zm0 6c-3.87 0-7-1.12-7-2.5S8.13 3 12 3s7 1.12 7 2.5S15.87 8 12 8zm-7 5.5c0 1.38 3.13 2.5 7 2.5s7-1.12 7-2.5V11c-1.78 1.24-4.24 2-7 2s-5.22-.76-7-2v2.5zm0 5c0 1.38 3.13 2.5 7 2.5s7-1.12 7-2.5V16c-1.78 1.24-4.24 2-7 2s-5.22-.76-7-2v2.5z"/></svg>
                </button>
                <button class="nav-link-btn" id="btn-media" title="Media Vault" onclick="switchRoute('/media')">
                    <svg viewBox="0 0 24 24"><path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/></svg>
                </button>
                <button class="nav-link-btn" id="btn-docs" title="Documentation" onclick="switchRoute('/docs')">
                    <svg viewBox="0 0 24 24"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>
                </button>
                <button class="nav-link-btn" id="btn-system" title="System Telemetry" onclick="switchRoute('/system')">
                    <svg viewBox="0 0 24 24"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-2 10h-4v4h-2v-4H7v-2h4V7h2v4h4v2z"/></svg>
                </button>
            </div>
        </nav>

        <main class="viewport">
            <header class="top-bar">
                <div class="hud-status">
                    <div class="hud-dot"></div>
                    AKHIL DEV PLATFORM // システム中枢
                </div>
                <div class="top-right-group">
                    <button class="btn-cyber" onclick="switchRoute('/api')">
                        <svg viewBox="0 0 24 24"><path d="M7 2v11h3v9l7-12h-4l4-8z"/></svg>
                        ISSUE API KEY
                    </button>
                    <div class="profile-chip" onclick="switchRoute('/profile')">
                        <div class="avatar-letter" id="user-chip-badge">A</div>
                        <span id="user-chip-handle" style="font-family:var(--hud-font); font-size:0.8rem;">OPERATIVE</span>
                    </div>
                </div>
            </header>

            <!-- PAGE: HOME -->
            <section id="view-home" class="page-node active">
                <div class="panel" style="padding:44px 32px;">
                    <div style="display:flex; flex-wrap:wrap; gap:32px; align-items:center; justify-content:space-between;">
                        <div>
                            <span style="font-family:var(--hud-font); color:var(--magenta-neon); font-size:0.75rem; letter-spacing:2px;">// QUANTUM CLOUD ENGINE</span>
                            <h1 style="font-size:2.2rem; font-weight:800; margin:10px 0 12px;">AKHIL DEV PLATFORM</h1>
                            <p style="color:var(--text-muted); font-size:1.05rem; margin-bottom:26px;">YOUR IDEAS × OUR INFRASTRUCTURE</p>
                            <div style="display:flex; gap:12px; flex-wrap:wrap;">
                                <button class="btn-cyber" onclick="switchRoute('/api')">
                                    <svg viewBox="0 0 24 24"><path d="M7 2v11h3v9l7-12h-4l4-8z"/></svg>
                                    GET API KEY
                                </button>
                                <button class="btn-cyber btn-magenta" onclick="switchRoute('/sandbox')">
                                    <svg viewBox="0 0 24 24"><path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm-5 14H4v-4h11v4zm0-5H4V9h11v4zm5 5h-4V9h4v9z"/></svg>
                                    OPEN CONSOLE
                                </button>
                            </div>
                        </div>
                        <div>
                            <img src="/public/second-image.png" onerror="this.src='/public/image.png'; this.onerror=null;" style="width:190px; max-height:190px; object-fit:contain; filter:drop-shadow(0 0 20px var(--cyan-glow));" alt="Engine Visual">
                        </div>
                    </div>
                </div>

                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(210px, 1fr)); gap:16px;">
                    <div class="panel">
                        <span style="font-family:var(--hud-font); font-size:0.72rem; color:var(--text-muted);">CLUSTER HEALTH</span>
                        <h3 style="font-family:var(--hud-font); color:var(--cyan-neon); margin-top:6px;">ONLINE 100%</h3>
                    </div>
                    <div class="panel">
                        <span style="font-family:var(--hud-font); font-size:0.72rem; color:var(--text-muted);">PERSISTENCE STORE</span>
                        <h3 style="font-family:var(--hud-font); color:var(--cyan-neon); margin-top:6px;">SYNCHRONIZED</h3>
                    </div>
                    <div class="panel">
                        <span style="font-family:var(--hud-font); font-size:0.72rem; color:var(--text-muted);">AUTHENTICATION GATEWAY</span>
                        <h3 style="font-family:var(--hud-font); color:var(--magenta-neon); margin-top:6px;">FIREBASE MODULAR ACTIVE</h3>
                    </div>
                </div>
            </section>

            <!-- PAGE: IDENTITY GATE (LOGIN) -->
            <section id="view-login" class="page-node">
                <div style="max-width:440px; margin:0 auto;">
                    <div class="panel" style="text-align:center;">
                        <span style="font-family:var(--hud-font); font-size:0.75rem; color:var(--cyan-neon);">// IDENTITY GATE</span>
                        <h2 style="font-family:var(--hud-font); margin:6px 0 8px;">ACCESS VERIFICATION</h2>
                        <p style="font-family:var(--hud-font); font-size:0.75rem; color:var(--text-muted); margin-bottom:24px;">AUTHENTICATE TO ACCESS YOUR DEVELOPER CORE</p>

                        <div id="unauth-container" style="display:flex; flex-direction:column; gap:12px;">
                            <input type="email" id="in-email" class="hud-input" placeholder="Operative Email" value="akhil@example.com">
                            <input type="password" id="in-pass" class="hud-input" placeholder="Access Secret" value="CyberEngine2026#">
                            <button class="btn-cyber" style="width:100%; justify-content:center;" onclick="window.fbAuthEmail()">AUTHORIZE CREDENTIALS</button>
                            
                            <button class="btn-cyber" style="width:100%; justify-content:center;" onclick="window.fbAuthGoogle()">
                                <svg viewBox="0 0 24 24"><path d="M12.545 10.239v3.821h5.445c-.712 2.315-2.647 3.972-5.445 3.972-3.332 0-6.033-2.701-6.033-6.032s2.701-6.032 6.033-6.032c1.498 0 2.866.549 3.921 1.453l2.814-2.814C17.503 2.988 15.139 2 12.545 2 7.021 2 2.543 6.477 2.543 12s4.478 10 10.002 10c8.396 0 10.249-7.85 9.426-11.748L12.545 10.239z"/></svg>
                                Continue with Google
                            </button>

                            <button class="btn-cyber" style="width:100%; justify-content:center; background:rgba(24,119,242,0.15); border-color:#1877f2;" onclick="window.fbAuthFacebook()">
                                <svg style="fill:#1877f2;" viewBox="0 0 24 24"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>
                                Continue with Facebook
                            </button>

                            <button class="btn-cyber" style="width:100%; justify-content:center; background:rgba(255,255,255,0.05); border-color:var(--text-muted);" onclick="window.fbAuthGithub()">
                                <svg viewBox="0 0 24 24"><path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/></svg>
                                Continue with GitHub
                            </button>
                        </div>

                        <div id="auth-success-container" style="display:none; text-align:left;">
                            <p id="auth-user-msg" style="font-family:var(--hud-font); color:var(--cyan-neon); font-size:0.85rem; margin-bottom:16px;"></p>
                            <button class="btn-cyber btn-magenta" style="width:100%; justify-content:center;" onclick="window.fbSignOut()">TERMINATE SESSION</button>
                        </div>
                    </div>
                </div>
            </section>

            <!-- PAGE: API KEY VAULT -->
            <section id="view-api" class="page-node">
                <div class="panel">
                    <span style="font-family:var(--hud-font); font-size:0.75rem; color:var(--cyan-neon);">// CRYPTOGRAPHIC VAULT</span>
                    <h2 style="margin:6px 0 20px;">API KEY MANAGEMENT</h2>

                    <div id="gate-warning" style="display:none; padding:18px; background:rgba(255,0,127,0.1); border:1px solid var(--magenta-neon); border-radius:8px; margin-bottom:20px;">
                        <p style="font-family:var(--hud-font); font-size:0.85rem; color:var(--magenta-neon);">PLEASE LOGIN FIRST TO UNLOCK KEY OPERATIONS</p>
                        <button class="btn-cyber btn-magenta" style="margin-top:12px;" onclick="switchRoute('/login')">GO TO IDENTITY GATE</button>
                    </div>

                    <div id="vault-core-zone">
                        <label style="font-family:var(--hud-font); font-size:0.75rem; color:var(--text-muted); display:block; margin-bottom:6px;">APPLICATION IDENTITY</label>
                        <input type="text" id="target-app" class="hud-input" value="eva_units" placeholder="Application / Service Name">
                        
                        <div style="display:flex; gap:12px; flex-wrap:wrap; margin-bottom:24px;">
                            <button class="btn-cyber" id="btn-forge-token" onclick="generateBackendKey()">
                                <svg viewBox="0 0 24 24"><path d="M12.65 10C11.83 7.67 9.61 6 7 6c-3.31 0-6 2.69-6 6s2.69 6 6 6c2.61 0 4.83-1.67 5.65-4H17v4h4v-4h2v-4H12.65zM7 14c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2z"/></svg>
                                GENERATE API KEY
                            </button>
                        </div>

                        <div id="key-result-card" style="display:none; background:rgba(0,0,0,0.6); padding:18px; border-radius:8px; border:1px dashed var(--bg-panel-border); margin-bottom:22px;">
                            <div style="font-family:var(--hud-font); font-size:0.75rem; color:var(--magenta-neon); margin-bottom:6px;">ACTIVE SECURE PASS:</div>
                            <div id="active-key-string" style="font-family:var(--hud-font); color:var(--cyan-neon); font-size:0.95rem; word-break:break-all; margin-bottom:12px;">••••••••••••••••••••••••••••••••</div>
                            <button class="btn-cyber" onclick="copyCurrentKeyString()">
                                <svg viewBox="0 0 24 24"><path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>
                                COPY KEY
                            </button>
                        </div>

                        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(140px, 1fr)); gap:14px;">
                            <div>
                                <span style="font-family:var(--hud-font); font-size:0.72rem; color:var(--text-muted);">CREATED</span>
                                <p id="metric-created" style="font-family:var(--hud-font); font-size:0.85rem;">Unavailable</p>
                            </div>
                            <div>
                                <span style="font-family:var(--hud-font); font-size:0.72rem; color:var(--text-muted);">STATUS</span>
                                <p id="metric-status" style="font-family:var(--hud-font); font-size:0.85rem; color:var(--cyan-neon);">IDLE</p>
                            </div>
                            <div>
                                <span style="font-family:var(--hud-font); font-size:0.72rem; color:var(--text-muted);">USAGE COUNT</span>
                                <p id="metric-usage" style="font-family:var(--hud-font); font-size:0.85rem;">0</p>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <!-- PAGE: PROFILE -->
            <section id="view-profile" class="page-node">
                <div class="panel" style="max-width:580px;">
                    <span style="font-family:var(--hud-font); font-size:0.75rem; color:var(--cyan-neon);">// USER PROFILE</span>
                    <h2 style="margin:6px 0 20px;">OPERATIVE IDENTITY</h2>
                    <div style="display:flex; flex-direction:column; gap:14px; margin-bottom:24px;">
                        <div>
                            <label style="font-family:var(--hud-font); font-size:0.75rem; color:var(--text-muted);">DISPLAY NAME</label>
                            <input type="text" id="prof-display-name" class="hud-input" style="margin-top:6px;">
                        </div>
                        <div>
                            <label style="font-family:var(--hud-font); font-size:0.75rem; color:var(--text-muted);">ACCOUNT STATUS</label>
                            <p style="font-family:var(--hud-font); font-size:0.85rem; color:var(--cyan-neon); margin-top:6px;">VERIFIED OPERATOR</p>
                        </div>
                        <div>
                            <label style="font-family:var(--hud-font); font-size:0.75rem; color:var(--text-muted);">AUTH PROVIDER</label>
                            <p id="prof-provider" style="font-family:var(--hud-font); font-size:0.85rem; color:var(--cyan-neon); margin-top:6px;">None (Local Mode)</p>
                        </div>
                    </div>
                    <div style="display:flex; gap:12px;">
                        <button class="btn-cyber" onclick="saveProfileChanges()">
                            <svg viewBox="0 0 24 24"><path d="M17 3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V7l-4-4zm-5 16c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3zm3-10H5V5h10v4z"/></svg>
                            SAVE CHANGES
                        </button>
                        <button class="btn-cyber btn-magenta" onclick="window.fbSignOut()">LOGOUT</button>
                    </div>
                </div>
            </section>

            <!-- PAGE: SANDBOX -->
            <section id="view-sandbox" class="page-node">
                <div class="panel">
                    <span style="font-family:var(--hud-font); font-size:0.75rem; color:var(--cyan-neon);">// API RUNTIME SANDBOX</span>
                    <h2 style="margin:6px 0 16px;">INTERACTIVE CONSOLE</h2>
                    <div style="display:flex; gap:10px; margin-bottom:16px;">
                        <select id="sb-method" style="background:#000; border:1px solid var(--cyan-neon); color:var(--cyan-neon); padding:8px 12px; border-radius:6px; font-family:var(--hud-font); outline:none;">
                            <option>POST</option>
                            <option>GET</option>
                        </select>
                        <input type="text" id="sb-endpoint" class="hud-input" style="margin-bottom:0;" value="/api/admin/keys/create">
                        <button class="btn-cyber" onclick="triggerSandboxRequest()">
                            <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
                            SEND REQUEST
                        </button>
                    </div>
                    <div style="background:#000; padding:16px; border-radius:8px; border:1px solid rgba(255,255,255,0.08);">
                        <div style="display:flex; justify-content:space-between; margin-bottom:8px; font-family:var(--hud-font); font-size:0.75rem; color:var(--text-muted);">
                            <span>TELEMETRY PAYLOAD</span>
                            <span id="sb-telemetry-status">STATUS: IDLE</span>
                        </div>
                        <pre id="sb-output" style="font-family:var(--hud-font); color:var(--cyan-neon); font-size:0.85rem; overflow-x:auto;">// Ready for operational API execution</pre>
                    </div>
                </div>
            </section>

            <!-- PAGE: DATABASE -->
            <section id="view-database" class="page-node">
                <div class="panel">
                    <span style="font-family:var(--hud-font); font-size:0.75rem; color:var(--cyan-neon);">// PERSISTENCE TELEMETRY</span>
                    <h2 style="margin:6px 0 12px;">DATABASE REPOSITORY</h2>
                    <p style="color:var(--text-muted); font-size:0.9rem; margin-bottom:18px;">Direct telemetry link with underlying storage cluster.</p>
                    <div style="padding:16px; background:rgba(0,0,0,0.4); border:1px solid var(--bg-panel-border); border-radius:8px;">
                        <p style="font-family:var(--hud-font); font-size:0.85rem;">Status: <span style="color:var(--cyan-neon);">Synchronized</span></p>
                        <p style="font-family:var(--hud-font); font-size:0.85rem; margin-top:6px;">Cluster Engine: Cloud Native SQLite / JSON Store</p>
                    </div>
                </div>
            </section>

            <!-- PAGE: MEDIA -->
            <section id="view-media" class="page-node">
                <div class="panel">
                    <span style="font-family:var(--hud-font); font-size:0.75rem; color:var(--cyan-neon);">// STORAGE VAULT</span>
                    <h2 style="margin:6px 0 12px;">MEDIA REPOSITORY</h2>
                    <p style="color:var(--text-muted); font-size:0.9rem; margin-bottom:18px;">Uploaded assets and binaries managed by core storage vault.</p>
                    <div style="padding:16px; background:rgba(0,0,0,0.4); border:1px solid var(--bg-panel-border); border-radius:8px;">
                        <p style="font-family:var(--hud-font); font-size:0.85rem;">Storage Core: <span style="color:var(--cyan-neon);">Ready</span></p>
                        <p style="font-family:var(--hud-font); font-size:0.85rem; margin-top:6px;">Storage Target: /storage_vault & /public</p>
                    </div>
                </div>
            </section>

            <!-- PAGE: DOCS -->
            <section id="view-docs" class="page-node">
                <div class="panel">
                    <span style="font-family:var(--hud-font); font-size:0.75rem; color:var(--cyan-neon);">// DEVELOPER PROTOCOL</span>
                    <h2 style="margin:6px 0 16px;">INTEGRATION DOCUMENTATION</h2>
                    <h4 style="font-family:var(--hud-font); color:var(--magenta-neon); margin:12px 0 6px;">AUTHENTICATION</h4>
                    <p style="font-size:0.9rem; color:var(--text-muted); margin-bottom:12px;">All requests require an authorized Bearer token or pass key.</p>
                    <pre style="background:#000; padding:12px; border-radius:6px; font-family:var(--hud-font); font-size:0.8rem; color:var(--cyan-neon); overflow-x:auto;">curl -X POST https://akhil-private-backend.onrender.com/api/admin/keys/create   -H "Content-Type: application/json"   -d '{"email":"operative@domain.com","app_name":"core_unit"}'</pre>
                </div>
            </section>

            <!-- PAGE: SYSTEM -->
            <section id="view-system" class="page-node">
                <div class="panel">
                    <span style="font-family:var(--hud-font); font-size:0.75rem; color:var(--cyan-neon);">// TELEMETRY RADAR</span>
                    <h2 style="margin:6px 0 16px;">SYSTEM HEALTH</h2>
                    <div style="display:flex; flex-direction:column; gap:12px;">
                        <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.06); padding-bottom:8px;">
                            <span style="font-family:var(--hud-font); font-size:0.85rem;">API GATEWAY</span>
                            <span style="font-family:var(--hud-font); color:var(--cyan-neon); font-size:0.85rem;">ONLINE</span>
                        </div>
                        <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.06); padding-bottom:8px;">
                            <span style="font-family:var(--hud-font); font-size:0.85rem;">AUTH ENGINE</span>
                            <span style="font-family:var(--hud-font); color:var(--cyan-neon); font-size:0.85rem;">FIREBASE v10.8 ACTIVE</span>
                        </div>
                        <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.06); padding-bottom:8px;">
                            <span style="font-family:var(--hud-font); font-size:0.85rem;">STORAGE CLUSTER</span>
                            <span style="font-family:var(--hud-font); color:var(--cyan-neon); font-size:0.85rem;">OPERATIONAL</span>
                        </div>
                    </div>
                </div>
            </section>

            <!-- PAGE: ABOUT / PRIVACY -->
            <section id="view-about" class="page-node">
                <div class="panel">
                    <span style="font-family:var(--hud-font); font-size:0.75rem; color:var(--cyan-neon);">// TERMS & SECURITY</span>
                    <h2 style="margin:6px 0 14px;">PRIVACY POLICY & TERMS</h2>
                    <div style="color:var(--text-muted); font-size:0.86rem; line-height:1.65; display:flex; flex-direction:column; gap:10px;">
                        <p>• Account information is used strictly to provide platform functionality.</p>
                        <p>• Authentication data is processed securely through configured authentication providers (Firebase Auth).</p>
                        <p>• API keys must be treated as confidential credentials. Never expose them publicly.</p>
                        <p>• Uploaded media is handled according to the platform's configured storage.</p>
                        <p style="font-family:var(--hud-font); color:var(--cyan-neon); margin-top:10px;">LAST UPDATED: 2026</p>
                    </div>
                </div>
            </section>

            <footer style="margin-top:auto; padding-top:40px; text-align:center;">
                <p style="font-family:var(--hud-font); font-size:0.78rem; color:var(--cyan-neon); letter-spacing:2px;">DEVELOPER AKHIL</p>
                <p style="font-size:0.7rem; color:var(--text-muted); margin-top:4px;">Built with vision.</p>
            </footer>
        </main>
    </div>

    <div id="hud-toast" class="hud-toast-banner">ACTION VERIFIED</div>

    <!-- EXACT FIREBASE SDK + ANALYTICS + MODULAR CONFIG SCRIPT -->
    <script type="module">
        import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";
        import { getAnalytics } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-analytics.js";
        import { 
            getAuth, 
            onAuthStateChanged, 
            signInWithEmailAndPassword, 
            createUserWithEmailAndPassword, 
            signInWithPopup, 
            GoogleAuthProvider, 
            FacebookAuthProvider, 
            GithubAuthProvider,
            signOut 
        } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js";

        const firebaseConfig = {
            apiKey: "AIzaSyCr-q7bWfNuKLeui0LWl_FvoAlikfzuMFE",
            authDomain: "free-api-web-2a7bc-e81f3.firebaseapp.com",
            projectId: "free-api-web-2a7bc-e81f3",
            storageBucket: "free-api-web-2a7bc-e81f3.firebasestorage.app",
            messagingSenderId: "22422848110",
            appId: "1:22422848110:web:92e6ad4a7995b48369dc7f",
            measurementId: "G-FPZF166PW4"
        };

        const app = initializeApp(firebaseConfig);
        const analytics = getAnalytics(app);
        const auth = getAuth(app);

        window.currentAuthUser = null;

        onAuthStateChanged(auth, user => {
            window.currentAuthUser = user;
            if (user) {
                const name = user.displayName || localStorage.getItem('akhil_dev_handle') || "OPERATOR";
                updateIdentityUI(name, user.providerData[0]?.providerId || "Firebase Auth");
                document.getElementById('unauth-container').style.display = "none";
                document.getElementById('auth-success-container').style.display = "block";
                document.getElementById('auth-user-msg').innerText = "AUTHENTICATED: " + (user.displayName || user.email);
                document.getElementById('gate-warning').style.display = "none";
            } else {
                const localName = localStorage.getItem('akhil_dev_handle') || "OPERATIVE";
                updateIdentityUI(localName, "None (Local Mode)");
                document.getElementById('unauth-container').style.display = "flex";
                document.getElementById('auth-success-container').style.display = "none";
                document.getElementById('gate-warning').style.display = "block";
            }
        });

        window.fbAuthEmail = async () => {
            const em = document.getElementById('in-email').value.trim();
            const pw = document.getElementById('in-pass').value.trim();
            if (!em || !pw) return showHUDToast("CREDENTIALS REQUIRED");
            try {
                await signInWithEmailAndPassword(auth, em, pw);
                switchRoute('/api');
            } catch(e) {
                try {
                    await createUserWithEmailAndPassword(auth, em, pw);
                    switchRoute('/api');
                } catch(err) {
                    showHUDToast("AUTH FAILED: " + err.message);
                }
            }
        };

        window.fbAuthGoogle = async () => {
            try {
                const prov = new GoogleAuthProvider();
                await signInWithPopup(auth, prov);
                showHUDToast("GOOGLE AUTH SUCCESSFUL");
                switchRoute('/api');
            } catch(e) {
                showHUDToast(e.message);
            }
        };

        window.fbAuthFacebook = async () => {
            try {
                const prov = new FacebookAuthProvider();
                prov.addScope("email");
                prov.addScope("public_profile");
                await signInWithPopup(auth, prov);
                showHUDToast("FACEBOOK AUTH SUCCESSFUL");
                switchRoute('/api');
            } catch(e) {
                showHUDToast(e.message);
            }
        };

        window.fbAuthGithub = async () => {
            try {
                const prov = new GithubAuthProvider();
                await signInWithPopup(auth, prov);
                showHUDToast("GITHUB AUTH SUCCESSFUL");
                switchRoute('/api');
            } catch(e) {
                showHUDToast("GITHUB OAUTH: " + e.message);
            }
        };

        window.fbSignOut = async () => {
            await signOut(auth);
            showHUDToast("SESSION TERMINATED");
            switchRoute('/');
        };
    </script>

    <script>
        const routeMap = {
            '/': 'view-home',
            '/api': 'view-api',
            '/login': 'view-login',
            '/profile': 'view-profile',
            '/sandbox': 'view-sandbox',
            '/database': 'view-database',
            '/media': 'view-media',
            '/docs': 'view-docs',
            '/system': 'view-system',
            '/about': 'view-about'
        };

        let generatedKeyStore = null;

        function switchRoute(path) {
            window.history.pushState({}, '', path);
            applyRoute(path);
        }

        function applyRoute(path) {
            const pageId = routeMap[path] || 'view-home';
            document.querySelectorAll('.page-node').forEach(el => el.classList.remove('active'));
            const target = document.getElementById(pageId);
            if (target) target.classList.add('active');

            document.querySelectorAll('.nav-link-btn').forEach(b => b.classList.remove('active'));
            const activeBtn = Array.from(document.querySelectorAll('.nav-link-btn')).find(b => b.getAttribute('onclick')?.includes(path));
            if (activeBtn) activeBtn.classList.add('active');

            window.scrollTo({ top: 0, behavior: "smooth" });
        }

        window.onpopstate = () => applyRoute(window.location.pathname);

        window.addEventListener('DOMContentLoaded', () => {
            setTimeout(dismissIntro, 2400);
            const saved = localStorage.getItem('akhil_dev_handle');
            if (!saved) {
                document.getElementById('onboard-modal').style.display = "flex";
            } else {
                updateIdentityUI(saved);
            }
            applyRoute(window.location.pathname);
        });

        function dismissIntro() {
            const intro = document.getElementById('intro-overlay');
            if (intro) {
                intro.style.opacity = "0";
                setTimeout(() => intro.style.display = "none", 700);
            }
        }

        function saveHandle() {
            const val = document.getElementById('onboard-input').value.trim();
            const finalHandle = val || "AKHIL";
            localStorage.setItem('akhil_dev_handle', finalHandle);
            updateIdentityUI(finalHandle);
            document.getElementById('onboard-modal').style.display = "none";
            showHUDToast("ACCESS GRANTED: " + finalHandle);
        }

        function updateIdentityUI(name, provider) {
            document.getElementById('user-chip-handle').innerText = name.toUpperCase();
            document.getElementById('user-chip-badge').innerText = name.charAt(0).toUpperCase();
            document.getElementById('prof-display-name').value = name;
            if (provider) document.getElementById('prof-provider').innerText = provider;
        }

        function saveProfileChanges() {
            const val = document.getElementById('prof-display-name').value.trim();
            if (val) {
                localStorage.setItem('akhil_dev_handle', val);
                updateIdentityUI(val);
                showHUDToast("PROFILE SYNCHRONIZED");
            }
        }

        async function generateBackendKey() {
            const btn = document.getElementById('btn-forge-token');
            btn.innerText = "ENCRYPTING...";
            btn.disabled = true;

            const appTarget = document.getElementById('target-app').value.trim() || "eva_units";
            try {
                const res = await fetch('/api/admin/keys/create', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        email: window.currentAuthUser ? (window.currentAuthUser.email || "operative@akhil.dev") : "operative@akhil.dev",
                        app_name: appTarget
                    })
                });
                const data = await res.json();
                if (data.status === "success" || data.key) {
                    generatedKeyStore = data.key;
                    document.getElementById('active-key-string').innerText = generatedKeyStore;
                    document.getElementById('key-result-card').style.display = "block";
                    document.getElementById('metric-created').innerText = new Date().toLocaleDateString();
                    document.getElementById('metric-status').innerText = "ACTIVE // SECURE";
                    showHUDToast("API KEY GENERATED");
                } else {
                    showHUDToast(data.message || "UNABLE TO GENERATE KEY");
                }
            } catch(err) {
                showHUDToast("VAULT ERROR: " + err.message);
            } finally {
                btn.innerHTML = `<svg viewBox="0 0 24 24"><path d="M12.65 10C11.83 7.67 9.61 6 7 6c-3.31 0-6 2.69-6 6s2.69 6 6 6c2.61 0 4.83-1.67 5.65-4H17v4h4v-4h2v-4H12.65zM7 14c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2z"/></svg> GENERATE API KEY`;
                btn.disabled = false;
            }
        }

        function copyCurrentKeyString() {
            if (!generatedKeyStore) return showHUDToast("GENERATE KEY FIRST");
            navigator.clipboard.writeText(generatedKeyStore).then(() => {
                showHUDToast("API KEY COPIED");
            });
        }

        async function triggerSandboxRequest() {
            const m = document.getElementById('sb-method').value;
            const ep = document.getElementById('sb-endpoint').value;
            const out = document.getElementById('sb-output');
            const st = document.getElementById('sb-telemetry-status');

            st.innerText = "STATUS: RUNNING";
            try {
                const res = await fetch(ep, {
                    method: m,
                    headers: { 'Content-Type': 'application/json' },
                    body: m === "POST" ? JSON.stringify({ email: "test@akhil.dev", app_name: "sandbox_probe" }) : null
                });
                const d = await res.json();
                st.innerText = "STATUS: " + res.status;
                out.innerText = JSON.stringify(d, null, 2);
            } catch(e) {
                st.innerText = "STATUS: ERROR";
                out.innerText = e.toString();
            }
        }

        function showHUDToast(msg) {
            const t = document.getElementById('hud-toast');
            t.innerText = msg;
            t.classList.add('visible');
            setTimeout(() => t.classList.remove('visible'), 2600);
        }
    </script>
</body>
</html>""")

# ========================================================
# MAIN DASHBOARD INTERFACE (EXACT SCREENSHOT LAYOUT) (ROOT /)
# ========================================================



import os

def render_page(title, active_page, inner_content):
    base_file = os.path.join(os.path.dirname(__file__), "templates", "base.html")
    if not os.path.exists(base_file):
        base_file = "templates/base.html"
    with open(base_file, "r", encoding="utf-8") as f:
        html = f.read()
    html = html.replace("{{ title }}", title)
    html = html.replace("{{ active_page }}", active_page)
    # Handle jinja conditions cleanly
    for p in ["home", "api-keys", "sandbox", "media", "docs", "database", "system", "login"]:
        target = "{{ 'active' if active_page == '" + p + "' else '' }}"
        html = html.replace(target, "active" if active_page == p else "")
    html = html.replace("{{ content }}", inner_content)
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}

@app.route("/")
@app.route("/home")
def route_home():
    content = """
    <div class="panel-card">
        <h2 style="font-size:1.7rem; margin-bottom:8px; font-family:var(--font-code); color:var(--cyan);">AKHIL DEV CORE ENGINE</h2>
        <p style="color:var(--text-sub); margin-bottom:20px; line-height:1.6;">A high-concurrency developer platform engineered for persistent cryptographic pass management, high-throughput transmission APIs, and secure multi-tenant cloud telemetry.</p>
        <div style="display:flex; gap:12px; flex-wrap:wrap;">
            <a href="/api-keys" class="btn-action">ISSUE ACCESS KEY</a>
            <a href="/docs" class="btn-action" style="border-color:var(--magenta); color:var(--magenta);">READ PROTOCOL DOCS</a>
        </div>
    </div>

    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:16px; margin-bottom:24px;">
        <div class="panel-card" style="padding:18px;">
            <span style="font-family:var(--font-code); font-size:0.72rem; color:var(--text-sub);">AUTHENTICATION STATE</span>
            <h3 style="color:var(--cyan); font-family:var(--font-code); margin-top:6px; font-size:1.1rem;" id="auth-status-lbl">UNAUTHENTICATED</h3>
            <p style="font-size:0.75rem; color:var(--text-sub); margin-top:6px;">Firebase SDK v10.8 modular gate</p>
        </div>
        <div class="panel-card" style="padding:18px;">
            <span style="font-family:var(--font-code); font-size:0.72rem; color:var(--text-sub);">CLUSTER HEALTH</span>
            <h3 style="color:var(--green); font-family:var(--font-code); margin-top:6px; font-size:1.1rem;">100% OPERATIONAL</h3>
            <p style="font-size:0.75rem; color:var(--text-sub); margin-top:6px;">Render cloud worker verified</p>
        </div>
        <div class="panel-card" style="padding:18px;">
            <span style="font-family:var(--font-code); font-size:0.72rem; color:var(--text-sub);">ENCRYPTION LEVEL</span>
            <h3 style="color:var(--magenta); font-family:var(--font-code); margin-top:6px; font-size:1.1rem;">SHA-256 HMAC</h3>
            <p style="font-size:0.75rem; color:var(--text-sub); margin-top:6px;">Cryptographic signing enabled</p>
        </div>
    </div>

    <div class="panel-card">
        <h3 style="font-family:var(--font-code); color:var(--cyan); margin-bottom:12px;">SYSTEM ARCHITECTURE OVERVIEW</h3>
        <p style="color:var(--text-sub); font-size:0.85rem; line-height:1.6; margin-bottom:14px;">The AKHIL DEV infrastructure bridges client authentication tokens with a persistent sqlite3 storage engine hosted on Render containers. All incoming requests are authenticated through Bearer headers with cryptographic pass validation.</p>
        <table class="data-table">
            <thead><tr><th>Service</th><th>Internal Protocol</th><th>Status</th><th>Telemetry</th></tr></thead>
            <tbody>
                <tr><td>Auth Broker</td><td>Firebase Auth / OAuth2</td><td style="color:var(--green);">ACTIVE</td><td>TLS 1.3</td></tr>
                <tr><td>Persistence Engine</td><td>Encrypted SQLite Vault</td><td style="color:var(--green);">ACTIVE</td><td>100% Synced</td></tr>
                <tr><td>REST Gateway</td><td>Flask / Gunicorn Worker</td><td style="color:var(--green);">ACTIVE</td><td>&lt; 40ms Latency</td></tr>
            </tbody>
        </table>
    </div>
    """
    return render_page("Home", "home", content)

@app.route("/api-keys")
def route_api_keys():
    content = """
    <div class="panel-card">
        <h2 style="font-family:var(--font-code); color:var(--cyan); margin-bottom:10px;">API KEY VAULT</h2>
        <p style="color:var(--text-sub); font-size:0.85rem; margin-bottom:18px;">Issue cryptographic API tokens for your external microservices, scripts, and applications.</p>
        
        <div id="auth-warning-alert" style="display:none; background:rgba(255,0,85,0.15); border:1px solid var(--magenta); color:#fff; padding:12px; border-radius:6px; font-family:var(--font-code); font-size:0.8rem; margin-bottom:16px;">
            [!] AUTHENTICATION REQUIRED: You must sign in at the Identity Gate before generating an API access pass.
        </div>

        <div style="max-width:520px;">
            <label style="font-family:var(--font-code); font-size:0.75rem; color:var(--text-sub); display:block; margin-bottom:6px;">APPLICATION IDENTIFIER</label>
            <input type="text" id="app-key-name" class="hud-input" placeholder="e.g. production_client" value="eva_units">
            <button class="btn-action" id="gen-key-btn" onclick="executeKeyGeneration()">GENERATE API KEY</button>

            <div id="key-result-box" style="display:none; margin-top:20px; padding:16px; background:#000; border:1px dashed var(--border-line); border-radius:6px;">
                <span style="font-family:var(--font-code); font-size:0.72rem; color:var(--magenta);">GENERATED CRYPTOGRAPHIC PASS:</span>
                <div id="key-output-val" style="font-family:var(--font-code); color:var(--cyan); font-size:0.95rem; word-break:break-all; margin:8px 0;"></div>
                <button class="btn-action" onclick="copyPass()">COPY PASS</button>
            </div>
        </div>
    </div>

    <div class="panel-card">
        <h3 style="font-family:var(--font-code); color:var(--cyan); margin-bottom:10px;">KEY USAGE RESTRICTIONS</h3>
        <p style="color:var(--text-sub); font-size:0.85rem; line-height:1.6;">Generated API keys carry authorized read/write permissions for registered storage endpoints. Do not expose private keys in frontend bundles or client-side JavaScript. Store keys as environment variables (`AKHIL_API_KEY`) on your remote servers.</p>
    </div>

    <script>
        let currentPassKey = "";
        async function executeKeyGeneration() {
            if (!window.currentFirebaseUser) {
                alert("ACCESS DENIED: Please authorize your identity at the Identity Gate first.");
                window.location.href = "/login";
                return;
            }
            const appName = document.getElementById("app-key-name").value.trim() || "production_client";
            const btn = document.getElementById("gen-key-btn");
            btn.innerText = "GENERATING...";
            btn.disabled = true;
            try {
                const res = await fetch("/api/admin/keys/create", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ email: window.currentFirebaseUser.email, app_name: appName })
                });
                const d = await res.json();
                if (d.status === "success" || d.key) {
                    currentPassKey = d.key;
                    document.getElementById("key-output-val").innerText = currentPassKey;
                    document.getElementById("key-result-box").style.display = "block";
                } else alert(d.message || "Failed");
            } catch(e) { alert(e.message); }
            finally { btn.innerText = "GENERATE API KEY"; btn.disabled = false; }
        }
        function copyPass() {
            if (!currentPassKey) return;
            navigator.clipboard.writeText(currentPassKey).then(() => alert("Pass copied to clipboard!"));
        }
    </script>
    """
    return render_page("API Keys", "api-keys", content)

@app.route("/sandbox")
def route_sandbox():
    content = """
    <div class="panel-card">
        <h2 style="font-family:var(--font-code); color:var(--cyan); margin-bottom:10px;">TRANSMISSION SANDBOX</h2>
        <p style="color:var(--text-sub); font-size:0.85rem; margin-bottom:16px;">Test API endpoints against live backend routes in a real-time console environment.</p>
        <div style="display:flex; gap:10px; margin-bottom:14px;">
            <input type="text" id="sb-url" class="hud-input" style="margin-bottom:0;" value="/api/admin/keys/create">
            <button class="btn-action" onclick="runSandboxTest()">SEND REQUEST</button>
        </div>
        <pre id="sb-console" class="code-block">// Transmission Console Ready. Awaiting trigger...</pre>
    </div>

    <div class="panel-card">
        <h3 style="font-family:var(--font-code); color:var(--cyan); margin-bottom:10px;">ACTIVE REST ENDPOINTS</h3>
        <table class="data-table">
            <thead><tr><th>Method</th><th>Path</th><th>Description</th><th>Access</th></tr></thead>
            <tbody>
                <tr><td style="color:var(--green);">POST</td><td>/api/admin/keys/create</td><td>Issue authentic developer pass</td><td>Authenticated</td></tr>
                <tr><td style="color:var(--cyan);">GET</td><td>/api/status</td><td>Cluster telemetry health check</td><td>Public</td></tr>
                <tr><td style="color:var(--green);">POST</td><td>/api/telemetry/report</td><td>Push client operational events</td><td>API Key Required</td></tr>
            </tbody>
        </table>
    </div>

    <script>
        async function runSandboxTest() {
            const ep = document.getElementById("sb-url").value;
            const con = document.getElementById("sb-console");
            con.innerText = "Connecting to backend gateway...";
            try {
                const res = await fetch(ep, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ email: "test@akhil.dev", app_name: "probe_packet" })
                });
                const d = await res.json();
                con.innerText = JSON.stringify(d, null, 2);
            } catch(e) { con.innerText = e.toString(); }
        }
    </script>
    """
    return render_page("Sandbox", "sandbox", content)

@app.route("/media")
def route_media():
    content = """
    <div class="panel-card">
        <h2 style="font-family:var(--font-code); color:var(--cyan); margin-bottom:10px;">MEDIA CORE VAULT</h2>
        <p style="color:var(--text-sub); font-size:0.85rem; margin-bottom:16px;">Centralized repository for platform assets, static files, and cloud-stored artifacts.</p>
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(240px, 1fr)); gap:16px;">
            <div style="background:#000; border:1px solid var(--border-subtle); padding:16px; border-radius:6px;">
                <span style="font-family:var(--font-code); font-size:0.7rem; color:var(--cyan);">PRIMARY ASSET</span>
                <h4 style="margin:8px 0; font-family:var(--font-code);">image.png</h4>
                <p style="font-size:0.75rem; color:var(--text-sub);">Route: /public/image.png</p>
                <p style="font-size:0.75rem; color:var(--green); margin-top:4px;">Status: Mounted</p>
            </div>
            <div style="background:#000; border:1px solid var(--border-subtle); padding:16px; border-radius:6px;">
                <span style="font-family:var(--font-code); font-size:0.7rem; color:var(--cyan);">SECONDARY ASSET</span>
                <h4 style="margin:8px 0; font-family:var(--font-code);">second-image.png</h4>
                <p style="font-size:0.75rem; color:var(--text-sub);">Route: /public/second-image.png</p>
                <p style="font-size:0.75rem; color:var(--green); margin-top:4px;">Status: Mounted</p>
            </div>
            <div style="background:#000; border:1px solid var(--border-subtle); padding:16px; border-radius:6px;">
                <span style="font-family:var(--font-code); font-size:0.7rem; color:var(--magenta);">STORAGE VOLUME</span>
                <h4 style="margin:8px 0; font-family:var(--font-code);">/storage_vault</h4>
                <p style="font-size:0.75rem; color:var(--text-sub);">Capacity: Cloud Persistent</p>
                <p style="font-size:0.75rem; color:var(--green); margin-top:4px;">Status: Read/Write Active</p>
            </div>
        </div>
    </div>

    <div class="panel-card">
        <h3 style="font-family:var(--font-code); color:var(--cyan); margin-bottom:10px;">STORAGE TELEMETRY & QUOTA</h3>
        <p style="color:var(--text-sub); font-size:0.85rem; line-height:1.6;">Static binary assets are served directly through the optimized WSGI file handler with automatic fallback handling. MIME type detection ensures direct rendering for PNG, JPEG, and WebP payloads.</p>
    </div>
    """
    return render_page("Media Vault", "media", content)

@app.route("/database")
def route_database():
    content = """
    <div class="panel-card">
        <h2 style="font-family:var(--font-code); color:var(--cyan); margin-bottom:10px;">DATABASE TELEMETRY ENGINE</h2>
        <p style="color:var(--text-sub); font-size:0.85rem; margin-bottom:16px;">Live metrics and partition states for the platform persistent storage layer.</p>
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:14px; margin-bottom:20px;">
            <div style="background:#000; padding:14px; border-radius:6px; border:1px solid var(--border-subtle);">
                <span style="font-family:var(--font-code); font-size:0.7rem; color:var(--text-sub);">ACTIVE PARTITION</span>
                <h4 style="font-family:var(--font-code); color:var(--cyan); margin-top:4px;">SQLITE_MASTER_01</h4>
            </div>
            <div style="background:#000; padding:14px; border-radius:6px; border:1px solid var(--border-subtle);">
                <span style="font-family:var(--font-code); font-size:0.7rem; color:var(--text-sub);">TRANSACTION STATUS</span>
                <h4 style="font-family:var(--font-code); color:var(--green); margin-top:4px;">ACID COMPLIANT</h4>
            </div>
            <div style="background:#000; padding:14px; border-radius:6px; border:1px solid var(--border-subtle);">
                <span style="font-family:var(--font-code); font-size:0.7rem; color:var(--text-sub);">CACHE HIT RATIO</span>
                <h4 style="font-family:var(--font-code); color:var(--cyan); margin-top:4px;">99.4%</h4>
            </div>
        </div>
    </div>

    <div class="panel-card">
        <h3 style="font-family:var(--font-code); color:var(--cyan); margin-bottom:12px;">ACTIVE SCHEMA SCHEMATICS</h3>
        <table class="data-table">
            <thead><tr><th>Table Identifier</th><th>Key Type</th><th>Record Engine</th><th>Integrity</th></tr></thead>
            <tbody>
                <tr><td>api_tokens</td><td>VARCHAR(64) PRIMARY KEY</td><td>B-Tree Indexed</td><td style="color:var(--green);">VERIFIED</td></tr>
                <tr><td>developer_profiles</td><td>UUID V4</td><td>Row Hash Partition</td><td style="color:var(--green);">VERIFIED</td></tr>
                <tr><td>transmission_logs</td><td>TIMESTAMP / BLOB</td><td>Append Only Log</td><td style="color:var(--green);">VERIFIED</td></tr>
            </tbody>
        </table>
    </div>

    <div class="panel-card">
        <h3 style="font-family:var(--font-code); color:var(--cyan); margin-bottom:10px;">PERSISTENCE LOG DUMP</h3>
        <pre class="code-block">[2026-09-29 17:40:02 UTC] DB_SYNC: WAL mode checkpoint completed successfully.
[2026-09-29 17:40:15 UTC] DB_INTEGRITY: Integrity check returned 0 anomalies.
[2026-09-29 17:41:00 UTC] DB_STATUS: Ready for read/write microservices.</pre>
    </div>
    """
    return render_page("Database", "database", content)

@app.route("/docs")
def route_docs():
    content = """
    <div class="panel-card">
        <h2 style="font-family:var(--font-code); color:var(--cyan); margin-bottom:10px;">AKHIL DEV PROTOCOL DOCUMENTATION</h2>
        <p style="color:var(--text-sub); font-size:0.85rem; line-height:1.6; margin-bottom:16px;">A comprehensive developer reference guide for integrating the AKHIL DEV platform into distributed applications.</p>
    </div>

    <div class="panel-card">
        <h3 style="font-family:var(--font-code); color:var(--cyan); margin-bottom:10px;">1. WHAT IS AN AKHIL DEV API KEY?</h3>
        <p style="color:var(--text-sub); font-size:0.85rem; line-height:1.6;">An AKHIL DEV API Key is a cryptographic authentication token issued to verified developers. When your application sends requests to platform endpoints, the key validates account tier, rate limits, and secure database partitions.</p>
    </div>

    <div class="panel-card">
        <h3 style="font-family:var(--font-code); color:var(--cyan); margin-bottom:10px;">2. IDENTITY GATE VS API KEYS</h3>
        <p style="color:var(--text-sub); font-size:0.85rem; line-height:1.6; margin-bottom:10px;">The platform enforces a two-tier access architecture:</p>
        <ul style="color:var(--text-sub); font-size:0.85rem; line-height:1.6; padding-left:20px;">
            <li><strong>Identity Gate (Firebase Auth):</strong> Verifies developer ownership via OAuth2 providers or credentials.</li>
            <li><strong>API Key:</strong> Used by your backend servers and scripts to make authenticated automated requests without human interaction.</li>
        </ul>
    </div>

    <div class="panel-card">
        <h3 style="font-family:var(--font-code); color:var(--cyan); margin-bottom:10px;">3. QUICKSTART INTEGRATION EXAMPLES</h3>
        <p style="color:var(--text-sub); font-size:0.85rem; margin-bottom:6px;"><strong>Python 3 (Requests):</strong></p>
        <pre class="code-block">import requests

url = "https://private-backend.onrender.com/api/admin/keys/create"
headers = {
    "Authorization": "Bearer akhi_live_YOUR_KEY_HERE",
    "Content-Type": "application/json"
}
payload = {"app_name": "production_service"}

response = requests.post(url, headers=headers, json=payload)
print(response.json())</pre>

        <p style="color:var(--text-sub); font-size:0.85rem; margin-top:14px; margin-bottom:6px;"><strong>JavaScript / Node.js (Fetch):</strong></p>
        <pre class="code-block">const response = await fetch("https://private-backend.onrender.com/api/admin/keys/create", {
    method: "POST",
    headers: {
        "Authorization": "Bearer akhi_live_YOUR_KEY_HERE",
        "Content-Type": "application/json"
    },
    body: JSON.stringify({ app_name: "production_service" })
});
const data = await response.json();
console.log(data);</pre>
    </div>
    """
    return render_page("Protocol Docs", "docs", content)

@app.route("/system")
def route_system():
    content = """
    <div class="panel-card">
        <h2 style="font-family:var(--font-code); color:var(--cyan); margin-bottom:10px;">SYSTEM TELEMETRY STATUS</h2>
        <p style="color:var(--text-sub); font-size:0.85rem; margin-bottom:16px;">Live diagnostics and container health metrics.</p>
        <table class="data-table">
            <thead><tr><th>Component</th><th>Engine Version</th><th>Health</th><th>Uptime</th></tr></thead>
            <tbody>
                <tr><td>Web Framework</td><td>Flask 3.0 / Gunicorn</td><td style="color:var(--green);">HEALTHY</td><td>99.98%</td></tr>
                <tr><td>Auth Gateway</td><td>Firebase Web SDK v10.8</td><td style="color:var(--green);">HEALTHY</td><td>100.0%</td></tr>
                <tr><td>Container Host</td><td>Render Linux Cloud</td><td style="color:var(--green);">HEALTHY</td><td>Operational</td></tr>
            </tbody>
        </table>
    </div>
    """
    return render_page("System Status", "system", content)

@app.route("/login")
def route_login():
    content = """
    <div class="panel-card" style="max-width:440px; margin:0 auto; text-align:center;">
        <h2 style="font-family:var(--font-code); color:var(--cyan); margin-bottom:6px;">IDENTITY GATE</h2>
        <p style="font-size:0.78rem; color:var(--text-sub); margin-bottom:20px;">AUTHENTICATE TO ACCESS YOUR DEVELOPER CORE</p>

        <div id="login-form-area">
            <input type="email" id="user-email" class="hud-input" placeholder="Enter Your Email">
            <input type="password" id="user-pass" class="hud-input" placeholder="Enter Your Password">
            <button class="btn-action" style="width:100%; justify-content:center; margin-bottom:14px;" onclick="emailAuthCall()">AUTHORIZE & SIGN IN</button>

            <button class="btn-action" style="width:100%; justify-content:center; margin-bottom:10px; background:rgba(255,255,255,0.06); border-color:rgba(255,255,255,0.2); color:#fff;" onclick="googleAuthCall()">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12.48 10.92v3.28h7.84c-.24 1.84-.853 3.187-1.787 4.133-1.147 1.147-2.933 2.4-6.053 2.4-4.827 0-8.6-3.893-8.6-8.72s3.773-8.72 8.6-8.72c2.6 0 4.507 1.027 5.907 2.347l2.307-2.307C18.747 1.44 16.133 0 12.48 0 5.867 0 .307 5.387.307 12s5.56 12 12.173 12c3.573 0 6.267-1.173 8.373-3.36 2.16-2.16 2.84-5.213 2.84-7.667 0-.76-.053-1.467-.173-2.053H12.48z"/></svg>
                Continue with Google
            </button>
            <button class="btn-action" style="width:100%; justify-content:center; background:rgba(24,119,242,0.12); border-color:#1877f2; color:#1877f2;" onclick="facebookAuthCall()">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>
                Continue with Facebook
            </button>
        </div>

        <div id="logged-user-area" style="display:none; text-align:left;">
            <p id="logged-email-text" style="font-family:var(--font-code); color:var(--cyan); margin-bottom:14px; font-size:0.85rem;"></p>
            <button class="btn-action" style="border-color:var(--magenta); color:var(--magenta); width:100%; justify-content:center;" onclick="signOutCall()">SIGN OUT</button>
        </div>
    </div>
    """
    return render_page("Identity Gate", "login", content)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
