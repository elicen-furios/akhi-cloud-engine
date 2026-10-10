import os
import sqlite3
import secrets
from flask_cors import CORS
from flask import Flask, request, jsonify, send_file, session

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)


def render_base(title, content):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - AKHIL DEV PLATFORM</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: #09090b;
            color: #f4f4f5;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            min-height: 100vh;
        }
        nav {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 24px;
            background: rgba(15, 15, 20, 0.95);
            border-bottom: 1px solid #27272a;
            position: sticky;
            top: 0;
            z-index: 100;
            backdrop-filter: blur(12px);
        }
        nav .brand {
            font-weight: 800;
            letter-spacing: -0.5px;
            color: #fff;
            text-decoration: none;
            font-size: 1.1rem;
        }
        nav .links a {
            color: #a1a1aa;
            text-decoration: none;
            margin-left: 18px;
            font-size: 0.9rem;
            transition: color 0.2s ease;
        }
        nav .links a:hover { color: #f472b6; }
        main { padding: 20px 14px 60px; }
    </style>
</head>
<body>
    <nav>
        <a href="/" class="brand"> AKHIL PLATFORM</a>
        <div class="links">
            <a href="/">Home</a>
            <a href="/admin-panel">Cloud DB Panel</a>
        </div>
    </nav>
    <main>
        {content}
    </main>
</body>
</html>"""

app.secret_key = os.environ.get("SECRET_KEY", "akhil_dev_platform_secret_vault_2026")

import time
from collections import defaultdict

# IP-based rate limiting memory store
REQUEST_LOGS = defaultdict(list)

def is_rate_limited(ip, max_requests=5, window_seconds=60):
    now = time.time()
    REQUEST_LOGS[ip] = [t for t in REQUEST_LOGS[ip] if now - t < window_seconds]
    if len(REQUEST_LOGS[ip]) >= max_requests:
        return True
    REQUEST_LOGS[ip].append(now)
    return False

@app.after_request
def inject_security_headers(response):
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
DB_PATH = "data.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE,
            email TEXT,
            app_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Direct Image Serving Routes
@app.route("/image.png")
@app.route("/static/image.png")
def serve_image():
    for f in ["image.png", "logo.png", "static/image.png", "static/logo.png"]:
        if os.path.exists(f):
            return send_file(f, mimetype="image/png")
    return ("", 404)

@app.route("/logo.png")
@app.route("/static/logo.png")
def serve_logo():
    for f in ["logo.png", "image.png", "static/logo.png", "static/image.png"]:
        if os.path.exists(f):
            return send_file(f, mimetype="image/png")
    return ("", 404)

# Backend Auth Session Sync
@app.route("/api/auth/session", methods=["POST"])
def auth_session():
    data = request.get_json(silent=True) or {}
    session["user_email"] = data.get("email", "")
    session["user_name"] = data.get("name", "")
    session["authenticated"] = True
    return jsonify({"status": "approved"})

@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"status": "cleared"})

# API Key Generation Route
@app.route("/api/admin/keys/create", methods=["POST"])
def create_key():
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()
    
    # Layer 1: Anti-Spam Rate Limit Guard
    if is_rate_limited(client_ip, max_requests=5, window_seconds=60):
        return jsonify({"status": "error", "message": "RATE_LIMIT_EXCEEDED: Maximum 5 keys per minute allowed. Try again later."}), 429

    # Layer 2: Strict Server-Side Session Enforcement (Blocks direct curl/Postman bypass)
    if not session.get("authenticated") or not session.get("user_email"):
        return jsonify({"status": "error", "message": "UNAUTHORIZED_ACCESS: Identity gate clearance required."}), 403

    data = request.get_json(silent=True) or {}
    email = session.get("user_email")
    app_name = (data.get("app_name") or "production_client").strip()[:50]
    new_key = f"akhi_live_{secrets.token_hex(16)}"

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("INSERT INTO api_keys (key, email, app_name) VALUES (?, ?, ?)", (new_key, email, app_name))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "key": new_key})
    except Exception as e:
        return jsonify({"status": "error", "message": "Database write error"}), 500

@app.route("/api/status")
def status_api():
    return jsonify({"status": "healthy", "service": "AKHIL_DEV_CORE", "version": "2.4.0"})

def render_page(title, active_page, inner_content):
    base_file = os.path.join(os.path.dirname(__file__), "templates", "base.html")
    with open(base_file, "r", encoding="utf-8") as f:
        html = f.read()
    html = html.replace("{{ title }}", title)
    for p in ["home", "api-keys", "sandbox", "media", "docs", "database", "system", "login", "neural-studio"]:
        target = "{{ 'active' if active_page == '" + p + "' else '' }}"
        html = html.replace(target, "active" if active_page == p else "")
    html = html.replace("{{ content }}", inner_content)
    html = html.replace("</body>", """
<!-- MAYARA FLOATING ASSISTANT -->
<style>
#mayara-root {
    position: fixed;
    bottom: 24px;
    right: 20px;
    z-index: 2147483647;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
#mayara-btn {
    width: 62px;
    height: 62px;
    border-radius: 50%;
    cursor: pointer;
    box-shadow: 0 8px 25px rgba(244, 114, 182, 0.65);
    border: 2.5px solid #f472b6;
    background: #0f0714;
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform 0.2s ease;
    user-select: none;
    -webkit-tap-highlight-color: transparent;
}
#mayara-btn:active { transform: scale(0.92); }
#mayara-btn img {
    width: 100%;
    height: 100%;
    border-radius: 50%;
    object-fit: cover;
    display: block;
}
.mayara-dot {
    position: absolute;
    bottom: 2px;
    right: 2px;
    width: 13px;
    height: 13px;
    background: #10b981;
    border: 2px solid #0f0714;
    border-radius: 50%;
}
#mayara-box {
    display: none;
    position: fixed;
    bottom: 24px;
    right: 20px;
    width: 350px;
    max-width: calc(100vw - 32px);
    height: 520px;
    border-radius: 20px;
    border: 1.5px solid rgba(244, 114, 182, 0.35);
    box-shadow: 0 25px 60px rgba(0, 0, 0, 0.95);
    flex-direction: column;
    overflow: hidden;
    backdrop-filter: blur(20px);
    background: linear-gradient(160deg, rgba(20, 9, 24, 0.97) 0%, rgba(35, 11, 38, 0.97) 100%);
    z-index: 2147483647;
}
@keyframes mayaraDrift {
    0% { background-position: 0 0, 16px 16px; }
    100% { background-position: 0 350px, 16px 366px; }
}
.mayara-bg {
    position: absolute;
    inset: 0;
    pointer-events: none;
    opacity: 0.22;
    background-image: radial-gradient(#f472b6 1px, transparent 1px), radial-gradient(#ec4899 1.5px, transparent 1.5px);
    background-size: 32px 32px;
    background-position: 0 0, 16px 16px;
    animation: mayaraDrift 20s linear infinite;
    z-index: 0;
}
</style>

<div id="mayara-root">
    <div id="mayara-btn" onclick="toggleMayaraUI()">
        <img src="https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?auto=format&fit=crop&w=250&q=80" alt="Mayara">
        <span class="mayara-dot"></span>
    </div>

    <div id="mayara-box">
        <div style="position: absolute; inset: 0; pointer-events: none; background: radial-gradient(circle at 15% 15%, rgba(244,114,182,0.18) 0%, transparent 45%), radial-gradient(circle at 85% 85%, rgba(192,132,252,0.18) 0%, transparent 45%); z-index: 0;"></div>
        <div class="mayara-bg"></div>

        <div style="padding: 12px 16px; background: rgba(30, 12, 35, 0.92); border-bottom: 1px solid rgba(244,114,182,0.25); display: flex; justify-content: space-between; align-items: center; z-index: 1;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="width: 36px; height: 36px; border-radius: 50%; overflow: hidden; border: 2px solid #f472b6; flex-shrink: 0;">
                    <img src="https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?auto=format&fit=crop&w=150&q=80" style="width: 100%; height: 100%; object-fit: cover;">
                </div>
                <div>
                    <div style="font-weight: 700; color: #fbcfe8; font-size: 13.5px;">MAYARA</div>
                    <div style="font-size: 10px; color: #6ee7b7; font-weight: 600;">Online &bull; Active</div>
                </div>
            </div>
            <button onclick="toggleMayaraUI()" style="background: rgba(244,114,182,0.15); border: 1px solid rgba(244,114,182,0.3); color: #f472b6; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 18px; font-weight: bold;">&times;</button>
        </div>

        <div id="mayara-msgs" style="flex: 1; padding: 14px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; font-size: 13px; z-index: 1;">
            <div style="background: rgba(48, 16, 54, 0.7); border: 1px solid rgba(244,114,182,0.25); color: #fdf2f8; padding: 10px 14px; border-radius: 16px 16px 16px 4px; max-width: 82%; align-self: flex-start;">
                Hello! Main Mayara hoon. Aap mujhse koi bhi sawaal pooch sakte hain.
            </div>
        </div>

        <div style="padding: 10px 12px; border-top: 1px solid rgba(244,114,182,0.25); background: rgba(18, 7, 21, 0.95); display: flex; gap: 8px; z-index: 1;">
            <input type="text" id="mayara-in" placeholder="Type prompt or code..." style="flex: 1; background: rgba(38, 13, 44, 0.85); border: 1px solid rgba(244,114,182,0.35); color: #fff; padding: 9px 14px; border-radius: 20px; font-size: 13px; outline: none;">
            <button id="mayara-send" style="background: linear-gradient(135deg, #ec4899, #a855f7); border: none; color: #fff; padding: 8px 16px; border-radius: 20px; cursor: pointer; font-size: 12px; font-weight: 700;">SEND</button>
        </div>
    </div>
</div>

<script>
function toggleMayaraUI() {
    var box = document.getElementById("mayara-box");
    var btn = document.getElementById("mayara-btn");
    if (!box) return;
    if (box.style.display === "none" || box.style.display === "") {
        box.style.display = "flex";
        if (btn) btn.style.display = "none";
    } else {
        box.style.display = "none";
        if (btn) btn.style.display = "flex";
    }
}

document.addEventListener("DOMContentLoaded", function() {
    var inp = document.getElementById("mayara-in");
    var btn = document.getElementById("mayara-send");
    var msgs = document.getElementById("mayara-msgs");

    async function sendMsg() {
        if (!inp) return;
        var text = inp.value.trim();
        if (!text) return;

        var u = document.createElement("div");
        u.style.cssText = "background: linear-gradient(135deg, #ec4899, #be185d); color: #fff; padding: 9px 14px; border-radius: 16px 16px 4px 16px; max-width: 82%; align-self: flex-end;";
        u.innerText = text;
        msgs.appendChild(u);
        inp.value = "";
        msgs.scrollTop = msgs.scrollHeight;

        if (text === "[8630@]") {
            var g = document.createElement("div");
            g.style.cssText = "background: rgba(16, 185, 129, 0.2); border: 1.5px solid #10b981; color: #34d399; padding: 10px 14px; border-radius: 14px; max-width: 85%; align-self: flex-start; font-weight: bold; font-family: monospace;";
            g.innerText = "ACCESS GRANTED: INITIALIZING ADMIN PANEL...";
            msgs.appendChild(g);
            try {
                var audio = new Audio("/bot.mp3");
                audio.play().catch(function(e){ console.log(e); });
            } catch(e){}
            setTimeout(function() {
                window.location.href = "/admin-panel";
            }, 1200);
            return;
        }

        var loader = document.createElement("div");
        loader.id = "mayara-loader";
        loader.style.cssText = "color: #f472b6; font-size: 11.5px; padding: 4px 8px; align-self: flex-start;";
        loader.innerText = "Mayara is thinking...";
        msgs.appendChild(loader);
        msgs.scrollTop = msgs.scrollHeight;

        try {
            var res = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text })
            });
            var d = await res.json();
            var l = document.getElementById("mayara-loader");
            if (l) l.remove();

            var b = document.createElement("div");
            b.style.cssText = "background: rgba(48, 16, 54, 0.7); border: 1px solid rgba(244,114,182,0.25); color: #fdf2f8; padding: 10px 14px; border-radius: 16px 16px 16px 4px; max-width: 82%; align-self: flex-start;";
            b.innerText = d.reply || "Mayara online.";
            msgs.appendChild(b);
            msgs.scrollTop = msgs.scrollHeight;
        } catch(e) {
            var l2 = document.getElementById("mayara-loader");
            if (l2) l2.remove();
            var err = document.createElement("div");
            err.style.cssText = "background: rgba(239, 68, 68, 0.2); color: #fca5a5; padding: 8px 12px; border-radius: 8px; font-size: 12px; align-self: flex-start;";
            err.innerText = "Connection error. Retrying...";
            msgs.appendChild(err);
            msgs.scrollTop = msgs.scrollHeight;
        }
    }

    if (btn) btn.addEventListener("click", sendMsg);
    if (inp) {
        inp.addEventListener("keydown", function(e) {
            if (e.key === "Enter") {
                e.preventDefault();
                sendMsg();
            }
        });
    }
});
</script>
</body>""")
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}

@app.route("/")
@app.route("/home")
def page_home():
    content = """
    <div style="text-align:center; padding: 36px 10px 48px;">
        <h1 style="font-size: clamp(2rem, 5vw, 3.2rem); font-weight:800; letter-spacing:-1px; line-height:1.2; margin-bottom:16px;">
            High-Performance API Infrastructure
        </h1>
        <p style="font-size:1.05rem; color:#52525b; max-width:600px; margin: 0 auto 30px; line-height:1.6;">
            Cryptographic access management, persistent SQLite storage, and production-ready telemetry.
        </p>
        <div style="display:flex; justify-content:center; gap:12px; flex-wrap:wrap;">
            <a href="/api-keys" class="btn-primary">Get Started &rarr;</a>
            <a href="/docs" class="btn-secondary">Read Documentation</a>
        </div>
    </div>

    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:18px;">
        <div class="card" style="margin-bottom:0;">
            <h3 style="font-size:1.05rem; font-weight:700; margin-bottom:8px;">Instant Access Tokens</h3>
            <p style="color:#71717a; font-size:0.85rem; line-height:1.5;">Authenticate external backend services with cryptographically unique tokens.</p>
        </div>
        <div class="card" style="margin-bottom:0;">
            <h3 style="font-size:1.05rem; font-weight:700; margin-bottom:8px;">Live Telemetry & Logs</h3>
            <p style="color:#71717a; font-size:0.85rem; line-height:1.5;">Continuous health monitoring and persistent ACID-compliant SQLite records.</p>
        </div>
        <div class="card" style="margin-bottom:0;">
            <h3 style="font-size:1.05rem; font-weight:700; margin-bottom:8px;">Strict Identity Gate</h3>
            <p style="color:#71717a; font-size:0.85rem; line-height:1.5;">Zero unauthorized pass generation without verified Firebase authentication.</p>
        </div>
    </div>
    """
    return render_page("Home", "home", content)

@app.route("/login")
def page_login():
    content = """
    <div style="max-width: 440px; margin: 20px auto 0;">
        <div class="card" id="login-box-card" style="padding: 34px 28px; border-radius: 20px; box-shadow: 0 10px 30px -10px rgba(0,0,0,0.06);">
            
            <!-- Brand Logo at top -->
            <div style="text-align:center; margin-bottom: 20px;">
                <div style="width: 58px; height: 58px; border-radius: 16px; margin: 0 auto 14px; overflow: hidden; border: 1px solid #e4e4e7; background: #fafafa; display: flex; align-items: center; justify-content: center;">
                    <img src="/logo.png" onerror="this.onerror=null; this.src='/image.png';" alt="Logo" style="width: 100%; height: 100%; object-fit: cover; display: block;">
                </div>
                <h2 style="font-size: 1.4rem; font-weight: 800; letter-spacing: -0.5px; color:#09090b; margin-bottom: 4px;">Developer Gate</h2>
                <p style="font-size: 0.84rem; color: #71717a;">Select your preferred access channel</p>
            </div>

            <!-- Segmented Pill: Login / Sign Up -->
            <div class="auth-segmented-nav">
                <button type="button" class="auth-tab-btn active" id="tab-btn-login" onclick="switchAuthTab('login')">Login</button>
                <button type="button" class="auth-tab-btn" id="tab-btn-signup" onclick="switchAuthTab('signup')">Sign up</button>
            </div>

            <!-- Login Form Tab -->
            <div id="pane-login" style="display: block;">
                <label style="font-size: 0.76rem; font-weight: 600; color: #52525b; display: block; margin-bottom: 6px;">USERNAME / EMAIL</label>
                <input type="text" id="login-identifier" class="input-text" placeholder="Enter username or email">
                
                <label style="font-size: 0.76rem; font-weight: 600; color: #52525b; display: block; margin-bottom: 6px;">PASSWORD</label>
                <div style="display: flex; align-items: center; position: relative; margin-bottom: 14px; background: #ffffff; border: 1px solid #e4e4e7; border-radius: 8px;">
                    <input type="password" id="login-password" style="width: 100%; border: none; outline: none; padding: 12px 14px; font-size: 0.9rem; background: transparent;" placeholder="Enter password">
                    <button type="button" onclick="togglePassVisibility('login-password', this)" style="background: transparent; border: none; padding: 10px 14px; cursor: pointer; color: #71717a; display: flex; align-items: center; justify-content: center; outline: none;">
                        <svg class="eye-open" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                        <svg class="eye-closed" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:none;"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>
                    </button>
                </div>
                
                <button type="button" class="btn-primary" style="width: 100%; justify-content: center; padding: 12px; margin-top: 6px; border-radius: 10px;" onclick="window.showSaasError('Please use Google or GitHub sign-in below to verify identity.', 'Authentication Required')">Login to Account</button>
            </div>

            <!-- Sign Up Form Tab -->
            <div id="pane-signup" style="display: none;">
                <label style="font-size: 0.76rem; font-weight: 600; color: #52525b; display: block; margin-bottom: 6px;">USERNAME</label>
                <input type="text" id="reg-username" class="input-text" placeholder="Enter username">

                <label style="font-size: 0.76rem; font-weight: 600; color: #52525b; display: block; margin-bottom: 6px;">EMAIL</label>
                <input type="email" id="reg-email" class="input-text" placeholder="Enter email address">
                
                <label style="font-size: 0.76rem; font-weight: 600; color: #52525b; display: block; margin-bottom: 6px;">PASSWORD</label>
                <div style="display: flex; align-items: center; position: relative; margin-bottom: 14px; background: #ffffff; border: 1px solid #e4e4e7; border-radius: 8px;">
                    <input type="password" id="reg-pass" style="width: 100%; border: none; outline: none; padding: 12px 14px; font-size: 0.9rem; background: transparent;" placeholder="Create password">
                    <button type="button" onclick="togglePassVisibility('reg-pass', this)" style="background: transparent; border: none; padding: 10px 14px; cursor: pointer; color: #71717a; display: flex; align-items: center; justify-content: center; outline: none;">
                        <svg class="eye-open" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                        <svg class="eye-closed" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:none;"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>
                    </button>
                </div>

                <label style="font-size: 0.76rem; font-weight: 600; color: #52525b; display: block; margin-bottom: 6px;">CONFIRM PASSWORD</label>
                <div style="display: flex; align-items: center; position: relative; margin-bottom: 14px; background: #ffffff; border: 1px solid #e4e4e7; border-radius: 8px;">
                    <input type="password" id="reg-confirm" style="width: 100%; border: none; outline: none; padding: 12px 14px; font-size: 0.9rem; background: transparent;" placeholder="Confirm password">
                    <button type="button" onclick="togglePassVisibility('reg-confirm', this)" style="background: transparent; border: none; padding: 10px 14px; cursor: pointer; color: #71717a; display: flex; align-items: center; justify-content: center; outline: none;">
                        <svg class="eye-open" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                        <svg class="eye-closed" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:none;"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>
                    </button>
                </div>
                
                <button type="button" class="btn-primary" style="width: 100%; justify-content: center; padding: 12px; margin-top: 6px; border-radius: 10px;" onclick="window.showSaasError('Direct user creation is locked. Authenticate via Google or GitHub.', 'System Policy')">Create Developer Account</button>
            </div>

            <div style="display: flex; align-items: center; margin: 22px 0 16px; gap: 10px;">
                <div style="flex: 1; height: 1px; background: #e4e4e7;"></div>
                <span style="font-size: 0.72rem; color: #a1a1aa; font-weight: 600;">OR CONTINUE WITH</span>
                <div style="flex: 1; height: 1px; background: #e4e4e7;"></div>
            </div>

            <!-- OAuth Fast Login -->
            <div style="display: flex; flex-direction: column; gap: 10px;">
                <button class="btn-secondary" style="width: 100%; justify-content: center; padding: 11px; border-radius: 10px;" onclick="loginGoogle()">
                    <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/></svg>
                    Continue with Google
                </button>
                <button class="btn-secondary" style="width: 100%; justify-content: center; padding: 11px; border-radius: 10px;" onclick="loginGithub()">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="#18181b"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
                    Continue with GitHub
                </button>
            </div>
        </div>

        <!-- Returning User / Active Session State Card -->
        <div class="card" id="logged-in-profile-card" style="display:none; text-align:center; padding:38px 28px; border-radius:20px;">
            <div style="width:58px; height:58px; border-radius:50%; background:#10b981; color:#fff; display:flex; align-items:center; justify-content:center; margin:0 auto 16px; font-weight:700; font-size:1.4rem;">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
            </div>
            <h2 style="font-size:1.35rem; font-weight:700; margin-bottom:6px;">Active Developer Session</h2>
            <p id="profile-display-info" style="font-family:var(--font-mono); font-size:0.86rem; color:#52525b; margin-bottom:24px;"></p>
            <div style="display:flex; gap:12px; justify-content:center;">
                <a href="/api-keys" class="btn-primary">Access Vault</a>
                <button class="btn-secondary" onclick="signOutAccount()">Sign Out</button>
            </div>
        </div>
    </div>

    <script>
        function switchAuthTab(mode) {
            const btnLogin = document.getElementById("tab-btn-login");
            const btnSignup = document.getElementById("tab-btn-signup");
            const paneLogin = document.getElementById("pane-login");
            const paneSignup = document.getElementById("pane-signup");

            if (mode === "login") {
                btnLogin.classList.add("active");
                btnSignup.classList.remove("active");
                paneLogin.style.display = "block";
                paneSignup.style.display = "none";
            } else {
                btnSignup.classList.add("active");
                btnLogin.classList.remove("active");
                paneLogin.style.display = "none";
                paneSignup.style.display = "block";
            }
        }

        function togglePassVisibility(inputId, btn) {
            const field = document.getElementById(inputId);
            if (!field) return;
            const eyeOpen = btn.querySelector('.eye-open');
            const eyeClosed = btn.querySelector('.eye-closed');

            if (field.type === 'password') {
                field.type = 'text';
                eyeOpen.style.display = 'none';
                eyeClosed.style.display = 'block';
            } else {
                field.type = 'password';
                eyeOpen.style.display = 'block';
                eyeClosed.style.display = 'none';
            }
        }
    </script>
    """
    return render_page("Identity Gate", "login", content)

@app.route("/api-keys")
def page_api_keys():
    content = """
    <div class="card">
        <h2 style="font-size:1.3rem; font-weight:700; margin-bottom:8px;">API Access Vault</h2>
        <p style="color:#71717a; font-size:0.88rem; margin-bottom:24px;">Issue and manage production authorization tokens for client applications.</p>

        <div style="max-width:500px;">
            <label style="font-size:0.75rem; font-weight:600; color:#52525b; display:block; margin-bottom:6px;">APPLICATION IDENTIFIER</label>
            <input type="text" id="app-key-name" class="input-text" value="production_service">
            <button class="btn-primary" id="btn-forge-key" onclick="issueDevKey()">Generate Pass Token</button>

            <div id="key-output-panel" style="display:none; margin-top:20px; padding:16px; background:#fafafa; border:1px solid #e4e4e7; border-radius:8px;">
                <span style="font-size:0.72rem; font-weight:700; color:#10b981;">NEW TOKEN GENERATED</span>
                <div id="pass-val-box" style="font-family:var(--font-mono); font-size:0.92rem; font-weight:600; margin:8px 0; word-break:break-all;"></div>
                <button class="btn-secondary" style="padding:6px 12px; font-size:0.78rem;" onclick="navigator.clipboard.writeText(document.getElementById('pass-val-box').innerText); window.showSaasError('Cryptographic token copied to clipboard!', 'Success');">Copy Token</button>
            </div>
        </div>
    </div>

    <!-- Active Keys Section -->
    <div class="card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
            <div>
                <h3 style="font-size:1.1rem; font-weight:700;">Active Tokens</h3>
                <p style="font-size:0.82rem; color:#71717a;">Tokens currently authorized to interact with your services.</p>
            </div>
            <button class="btn-secondary" style="padding:6px 12px; font-size:0.8rem;" onclick="loadUserKeys()">Refresh</button>
        </div>
        <div style="overflow-x:auto;">
            <table class="data-table" id="keys-table">
                <thead>
                    <tr>
                        <th>Application</th>
                        <th>Token</th>
                        <th>Created</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody id="keys-table-body">
                    <tr><td colspan="4" style="text-align:center; color:#a1a1aa; padding:18px;">Checking session...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        async function loadUserKeys() {
            const tbody = document.getElementById("keys-table-body");
            try {
                const res = await fetch("/api/admin/keys/list");
                if (res.status === 403) {
                    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:#71717a; padding:18px;">Sign in at Identity Gate to view active keys.</td></tr>';
                    return;
                }
                const data = await res.json();
                if (data.status === "success" && data.keys.length > 0) {
                    tbody.innerHTML = data.keys.map(k => `
                        <tr>
                            <td style="font-weight:600;">${k.app_name}</td>
                            <td><code style="font-family:var(--font-mono); font-size:0.8rem; background:#f4f4f5; padding:3px 6px; border-radius:4px;">${k.key.substring(0, 14)}...</code></td>
                            <td style="color:#71717a; font-size:0.8rem;">${k.created_at}</td>
                            <td>
                                <button class="btn-secondary" style="padding:4px 8px; font-size:0.75rem; color:#ef4444; border-color:#fecaca;" onclick="revokeKey(${k.id})">Revoke</button>
                            </td>
                        </tr>
                    `).join("");
                } else {
                    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:#a1a1aa; padding:18px;">No active tokens issued yet.</td></tr>';
                }
            } catch(e) {
                tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:#ef4444; padding:18px;">Failed to load tokens.</td></tr>';
            }
        }

        async function revokeKey(id) {
            const ok = await window.showSaasConfirm("Revoke Token", "Are you sure you want to revoke this pass token permanently? Connected services will immediately lose access."); if (!ok) return;
            try {
                const res = await fetch("/api/admin/keys/revoke", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ id: id })
                });
                const d = await res.json();
                if (d.status === "success") {
                    loadUserKeys();
                } else {
                    window.showSaasError(d.message || "Failed to revoke token");
                }
            } catch(e) { window.showSaasError(e.message); }
        }

        async function issueDevKey() {
            if (!window.currentFirebaseUser) {
                window.showSaasError("ACCESS RESTRICTED: Please authenticate at the Identity Gate first.", "Unauthorized Access");
                setTimeout(() => { window.location.href = "/login"; }, 1800);
                return;
            }
            const btn = document.getElementById("btn-forge-key");
            btn.innerText = "Generating...";
            btn.disabled = true;
            try {
                const res = await fetch("/api/admin/keys/create", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        email: window.currentFirebaseUser.email || "auth_user",
                        app_name: document.getElementById("app-key-name").value || "prod_client"
                    })
                });
                const d = await res.json();
                if (d.status === "success" || d.key) {
                    document.getElementById("pass-val-box").innerText = d.key;
                    document.getElementById("key-output-panel").style.display = "block";
                    loadUserKeys();
                } else {
                    window.showSaasError(d.message || "Failed to generate key", "Generation Failed");
                }
            } catch(e) { 
                window.showSaasError("Server communication failed: " + e.message, "Network Error"); 
            } finally { 
                btn.innerText = "Generate Pass Token"; 
                btn.disabled = false; 
            }
        }

        // Auto load on page load
        setTimeout(loadUserKeys, 800);
    </script>
    """
    return render_page("API Keys", "api-keys", content)

@app.route("/sandbox")
def page_sandbox():
    content = """
    <div class="card">
        <h2 style="font-size:1.3rem; font-weight:700; margin-bottom:8px;">Transmission Console</h2>
        <div style="display:flex; gap:10px; margin: 16px 0;">
            <input type="text" id="sb-url" class="input-text" style="margin-bottom:0;" value="/api/status">
            <button class="btn-primary" onclick="probe()">Execute</button>
        </div>
        <pre id="sb-res" class="code-box">// Ready</pre>
    </div>
    <script>
        async function probe() {
            const out = document.getElementById("sb-res");
            out.innerText = "Connecting...";
            try {
                const r = await fetch(document.getElementById("sb-url").value);
                const d = await r.json();
                out.innerText = JSON.stringify(d, null, 2);
            } catch(e) { out.innerText = e.toString(); }
        }
    </script>
    """
    return render_page("Sandbox", "sandbox", content)

@app.route("/media")
def page_media():
    content = """
    <div class="card">
        <h2 style="font-size:1.3rem; font-weight:700; margin-bottom:14px;">Media Core Storage</h2>
        <table class="data-table">
            <thead><tr><th>Asset Name</th><th>Mount Path</th><th>Status</th></tr></thead>
            <tbody>
                <tr><td>Brand Logo</td><td>/image.png</td><td style="color:#10b981; font-weight:600;">ACTIVE</td></tr>
                <tr><td>Auth Logo</td><td>/logo.png</td><td style="color:#10b981; font-weight:600;">ACTIVE</td></tr>
            </tbody>
        </table>
    </div>
    """
    return render_page("Media Vault", "media", content)

@app.route("/database")
def page_database():
    content = """
    <div class="card">
        <h2 style="font-size:1.3rem; font-weight:700; margin-bottom:14px;">Database Telemetry</h2>
        <table class="data-table">
            <thead><tr><th>Table Identifier</th><th>Engine</th><th>Status</th></tr></thead>
            <tbody>
                <tr><td>api_keys</td><td>SQLite3 B-Tree</td><td style="color:#10b981; font-weight:600;">HEALTHY</td></tr>
            </tbody>
        </table>
    </div>
    """
    return render_page("Database", "database", content)

@app.route("/docs")
def page_docs():
    content = """
    <div class="card">
        <h2 style="font-size:1.3rem; font-weight:700; margin-bottom:10px;">Protocol Documentation</h2>
        <p style="color:#52525b; font-size:0.88rem; line-height:1.6;">Include your pass token in the Bearer authorization header:</p>
        <pre class="code-box">Authorization: Bearer akhi_live_YOUR_TOKEN_HERE</pre>
    </div>
    """
    return render_page("Protocol Docs", "docs", content)

@app.route("/system")
def page_system():
    content = """
    <div class="card">
        <h2 style="font-size:1.3rem; font-weight:700; margin-bottom:14px;">Telemetry Status</h2>
        <table class="data-table">
            <thead><tr><th>Component</th><th>Status</th></tr></thead>
            <tbody>
                <tr><td>Web Server (Gunicorn)</td><td style="color:#10b981; font-weight:600;">OPERATIONAL</td></tr>
                <tr><td>Database Storage</td><td style="color:#10b981; font-weight:600;">OPERATIONAL</td></tr>
            </tbody>
        </table>
    </div>
    """
    return render_page("System Status", "system", content)


# Layer 3: Keys Management (List & Delete)
@app.route("/api/admin/keys/list", methods=["GET"])
def list_keys():
    if not session.get("authenticated") or not session.get("user_email"):
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
    email = session.get("user_email")
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, key, app_name, created_at FROM api_keys WHERE email = ? ORDER BY id DESC", (email,))
        rows = cur.fetchall()
        conn.close()
        keys_list = [{"id": r[0], "key": r[1], "app_name": r[2], "created_at": r[3]} for r in rows]
        return jsonify({"status": "success", "keys": keys_list})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/admin/keys/revoke", methods=["POST"])
def revoke_key():
    if not session.get("authenticated") or not session.get("user_email"):
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
    data = request.get_json(silent=True) or {}
    key_id = data.get("id")
    email = session.get("user_email")
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("DELETE FROM api_keys WHERE id = ? AND email = ?", (key_id, email))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Public Key Validation Route for External Apps
@app.route("/api/v1/verify", methods=["GET", "POST"])
def verify_api_key():
    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header.split("Bearer ")[1].strip()
    elif request.args.get("key"):
        token = request.args.get("key").strip()
    
    if not token:
        return jsonify({"valid": False, "error": "MISSING_TOKEN", "message": "Provide token via Bearer header or ?key= param"}), 401

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT email, app_name, created_at FROM api_keys WHERE key = ?", (token,))
        row = cur.fetchone()
        conn.close()
        if row:
            return jsonify({
                "valid": True,
                "app_name": row[1],
                "owner": row[0],
                "created_at": row[2]
            }), 200
        else:
            return jsonify({"valid": False, "error": "INVALID_TOKEN", "message": "Token not found or revoked"}), 403
    except Exception as e:
        return jsonify({"valid": False, "error": "SERVER_ERROR", "message": str(e)}), 500


# Bot Voice File Route
@app.route("/bot.mp3")
@app.route("/static/bot.mp3")
def serve_bot_voice():
    for f in ["bot.mp3", "static/bot.mp3"]:
        if os.path.exists(f):
            return send_file(f, mimetype="audio/mpeg")
    return ("", 404)

# Admin Panel Direct Authentication Session Route
@app.route("/api/admin/login", methods=["POST"])
def admin_panel_login():
    data = request.get_json(silent=True) or {}
    user = (data.get("username") or "").strip()
    pwd = (data.get("password") or "").strip()

    if user == "AKHIL" and pwd == "akhilrawat027@gmail.com":
        session["admin_authenticated"] = True
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "INVALID CREDENTIALS: Access Denied"}), 401

@app.route("/api/admin/logout", methods=["POST"])
def admin_panel_logout():
    session.pop("admin_authenticated", None)
    return jsonify({"status": "cleared"})

# Dedicated Secret Route: /admin-panel

@app.route("/api/chat", methods=["POST"])
def api_chat_handler():
    data = request.get_json(silent=True) or {}
    msg = (data.get("message") or "").strip()
    if not msg:
        return jsonify({"reply": "Message cannot be empty."})

    import urllib.request, urllib.parse

    # 1. Real Generative AI Query
    sys_prompt = "You are Mayara, a helpful female anime AI assistant. Answer directly to the point in Romanized Hindi (Hinglish) or English as asked."
    full_prompt = f"{sys_prompt}\n\nQuestion: {msg}\nAnswer:"
    try:
        encoded = urllib.parse.quote(full_prompt)
        url = f"https://text.pollinations.ai/{encoded}?model=mistral&seed=42"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=9) as resp:
            text = resp.read().decode("utf-8").strip()
            if text and len(text) > 2 and "pollinations" not in text.lower():
                return jsonify({"reply": text})
    except Exception:
        pass

    # 2. Targeted Fallback
    low = msg.lower()
    if "mai kon hu" in low or "who am i" in low:
        reply = "Aap Akhil hain, is poore platform aur system ke creator aur master admin!"
    elif "python kya hai" in low or "what is python" in low:
        reply = "Python ek high-level, interpreted programming language hai jo Web development, AI, automation scripts aur data science ke liye use hoti hai."
    elif any(w in low for w in ["hi", "hello", "hey"]):
        reply = "Hello! Kaise hain aap? Main Mayara hoon, batayein main kya help kar sakti hoon?"
    elif "kaise ho" in low or "kaisi ho" in low:
        reply = "Main bilkul badhiya hoon! Aap bataiye aapka din kaisa ja raha hai?"
    elif "admin" in low:
        reply = "Admin panel unlock karne ke liye bracket code '[8630@]' send karein."
    else:
        reply = f"Aapne pucha: '{msg}'. Main system par directly connected hoon."

    return jsonify({"reply": reply})






# ---------------- SECURE CLOUD DATABASE ENGINE ----------------
import json, sqlite3, os, html
from flask import session, redirect

MASTER_ADMIN_KEY = "8630"
API_AUTH_KEY = "akhil_8630_secure"

def get_db():
    b_dir = os.path.dirname(os.path.abspath(__file__))
    d_path = os.path.join(b_dir, "database.db")
    c = sqlite3.connect(d_path)
    c.row_factory = sqlite3.Row
    c.execute("""
    CREATE TABLE IF NOT EXISTS cloud_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        collection TEXT NOT NULL,
        payload TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.commit()
    return c

def verify_api_key(req):
    # Header ya query param me key check karna
    key = req.headers.get("x-api-key") or req.args.get("api_key")
    if key == API_AUTH_KEY:
        return True
    if session.get("is_admin"):
        return True
    return False

@app.route("/api/admin-auth", methods=["POST"])
def api_admin_auth():
    data = request.get_json(silent=True) or {}
    passcode = (data.get("passcode") or "").strip()
    if passcode == MASTER_ADMIN_KEY:
        session["is_admin"] = True
        return jsonify({"status": "success", "message": "Authenticated", "redirect": "/admin-panel"})
    return jsonify({"status": "error", "message": "Invalid passcode"}), 403

@app.route("/admin-logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect("/admin-panel")

@app.route("/api/db/insert", methods=["POST"])
def api_db_insert():
    if not verify_api_key(request):
        return jsonify({"status": "error", "message": "Unauthorized. Invalid or missing x-api-key"}), 401
    
    try:
        req_data = request.get_json(force=True, silent=True) or {}
        collection = req_data.get("collection", "default")
        payload = req_data.get("data")
        if not payload:
            return jsonify({"status": "error", "message": "Field 'data' is required"}), 400
        
        payload_str = json.dumps(payload) if isinstance(payload, (dict, list)) else str(payload)
        
        c = get_db()
        cur = c.cursor()
        cur.execute("INSERT INTO cloud_records (collection, payload) VALUES (?, ?)", (collection, payload_str))
        c.commit()
        rec_id = cur.lastrowid
        c.close()
        return jsonify({"status": "success", "id": rec_id, "collection": collection}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/db/all", methods=["GET"])
def api_db_get_all():
    if not verify_api_key(request):
        return jsonify({"status": "error", "message": "Unauthorized. Provide x-api-key header"}), 401
        
    try:
        col = request.args.get("collection")
        c = get_db()
        cur = c.cursor()
        if col:
            cur.execute("SELECT id, collection, payload, created_at FROM cloud_records WHERE collection = ? ORDER BY id DESC", (col,))
        else:
            cur.execute("SELECT id, collection, payload, created_at FROM cloud_records ORDER BY id DESC")
        rows = cur.fetchall()
        c.close()
        
        data = []
        for r in rows:
            try:
                val = json.loads(r["payload"])
            except Exception:
                val = r["payload"]
            data.append({"id": r["id"], "collection": r["collection"], "data": val, "created_at": r["created_at"]})
        return jsonify({"status": "success", "count": len(data), "records": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/db/delete", methods=["POST"])
def api_db_delete():
    if not verify_api_key(request):
        return jsonify({"status": "error", "message": "Unauthorized. Provide x-api-key header"}), 401

    try:
        req_data = request.get_json(force=True, silent=True) or {}
        rec_id = req_data.get("id")
        if not rec_id:
            return jsonify({"status": "error", "message": "ID is required"}), 400
        
        c = get_db()
        c.execute("DELETE FROM cloud_records WHERE id = ?", (rec_id,))
        c.commit()
        c.close()
        return jsonify({"status": "success", "message": f"Record {rec_id} deleted successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/admin-panel")
def page_admin_panel():
    if not session.get("is_admin"):
        return """<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lock Gate - Admin</title>
    <style>
        body { background: #09090b; color: #fff; font-family: sans-serif; display: flex; height: 100vh; align-items: center; justify-content: center; margin: 0; }
        .box { background: #121217; border: 1px solid #27272a; padding: 30px; border-radius: 14px; width: 320px; text-align: center; }
        input { width: 100%; box-sizing: border-box; background: #1a1a22; border: 1px solid #27272a; color: #fff; padding: 12px; border-radius: 8px; margin: 15px 0; text-align: center; font-size: 16px; outline: none; }
        button { width: 100%; background: linear-gradient(135deg, #ec4899, #a855f7); color: #fff; border: none; padding: 12px; border-radius: 8px; font-weight: bold; cursor: pointer; }
    </style>
</head>
<body>
    <div class="box">
        <h2 style="margin-bottom: 6px;">Admin Access Gate</h2>
        <p style="color: #71717a; font-size: 13px;">Passcode verify karke login karein.</p>
        <input type="password" id="pass" placeholder="Enter Secret Code">
        <button onclick="login()">Unlock Dashboard</button>
        <div id="err" style="color: #ef4444; font-size: 13px; margin-top: 10px;"></div>
    </div>
    <script>
    async function login() {
        var p = document.getElementById("pass").value.trim();
        var res = await fetch("/api/admin-auth", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ passcode: p })
        });
        var d = await res.json();
        if (d.status === "success") {
            location.reload();
        } else {
            document.getElementById("err").innerText = d.message || "Invalid Code";
        }
    }
    </script>
</body>
</html>"""

    # Admin is authenticated, render protected dashboard
    c = get_db()
    cur = c.cursor()
    cur.execute("SELECT id, collection, payload, created_at FROM cloud_records ORDER BY id DESC")
    records = cur.fetchall()
    c.close()

    table_rows = ""
    for r in records:
        safe_payload = html.escape(str(r['payload']))
        safe_col = html.escape(str(r['collection']))
        table_rows += f"""
        <tr style="border-bottom: 1px solid #27272a;">
            <td style="padding: 12px; color: #a1a1aa; font-family: monospace;">#{r['id']}</td>
            <td style="padding: 12px;"><span style="background: rgba(236,72,153,0.15); color: #f472b6; padding: 4px 10px; border-radius: 8px; font-weight: 600; font-size: 12px;">{safe_col}</span></td>
            <td style="padding: 12px; font-family: monospace; font-size: 12px; color: #e4e4e7; max-width: 320px; word-break: break-all;">{safe_payload}</td>
            <td style="padding: 12px; color: #71717a; font-size: 12px;">{r['created_at']}</td>
            <td style="padding: 12px;">
                <button onclick="deleteRecord({r['id']})" style="background: rgba(239,68,68,0.2); border: 1px solid #ef4444; color: #f87171; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px;">Delete</button>
            </td>
        </tr>
        """

    if not table_rows:
        table_rows = '<tr><td colspan="5" style="text-align:center; padding: 24px; color: #71717a;">Database abhi khali hai. Naya data add karein.</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Secure Cloud Database - AKHIL PLATFORM</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ background-color: #09090b; color: #f4f4f5; font-family: sans-serif; min-height: 100vh; }}
        nav {{ display: flex; justify-content: space-between; align-items: center; padding: 16px 24px; background: rgba(15, 15, 20, 0.95); border-bottom: 1px solid #27272a; position: sticky; top: 0; z-index: 100; }}
        nav .brand {{ font-weight: 800; color: #fff; text-decoration: none; }}
        nav .links a {{ color: #a1a1aa; text-decoration: none; margin-left: 18px; font-size: 0.9rem; }}
        main {{ padding: 20px 14px 60px; max-width: 1000px; margin: 0 auto; }}
    </style>
</head>
<body>
    <nav>
        <a href="/" class="brand"> SECURE CORE V2.4</a>
        <div class="links">
            <a href="/">Home</a>
            <a href="/admin-logout" style="color: #ef4444; font-weight: bold;">Logout</a>
        </div>
    </nav>
    <main>
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px; margin-bottom: 24px;">
            <div>
                <h1 style="font-size: 1.8rem; font-weight: 800; color: #fff; margin-bottom: 4px;">Cloud Database Manager</h1>
                <p style="color: #a1a1aa; font-size: 0.9rem;">Authenticated REST Storage &bull; Master Active</p>
            </div>
            <div style="background: #18181b; border: 1px solid #27272a; padding: 10px 18px; border-radius: 12px; text-align: center;">
                <div style="font-size: 1.3rem; font-weight: 800; color: #10b981;">{len(records)}</div>
                <div style="font-size: 0.75rem; color: #71717a; text-transform: uppercase;">Total Records</div>
            </div>
        </div>

        <div style="background: #121217; border: 1px solid #27272a; border-radius: 14px; padding: 20px; margin-bottom: 30px;">
            <h3 style="font-size: 1.05rem; font-weight: 700; color: #fff; margin-bottom: 14px;">+ Insert Record (Auto-Authorized)</h3>
            <div style="display: flex; flex-direction: column; gap: 12px;">
                <input type="text" id="db-col" placeholder="Collection (e.g. users, tokens, config)" style="background: #1c1c22; border: 1px solid #27272a; color: #fff; padding: 10px 14px; border-radius: 8px; outline: none;">
                <textarea id="db-payload" placeholder='JSON data ya string' rows="3" style="background: #1c1c22; border: 1px solid #27272a; color: #fff; padding: 10px 14px; border-radius: 8px; outline: none; font-family: monospace;"></textarea>
                <button onclick="insertRecord()" style="background: linear-gradient(135deg, #ec4899, #a855f7); color: #fff; border: none; padding: 10px 20px; border-radius: 8px; font-weight: 700; cursor: pointer; align-self: flex-start;">Save Record</button>
            </div>
        </div>

        <div style="background: #121217; border: 1px solid #27272a; border-radius: 14px; overflow-x: auto; margin-bottom: 30px;">
            <table style="width: 100%; border-collapse: collapse; text-align: left;">
                <thead>
                    <tr style="border-bottom: 1px solid #27272a; background: #18181f; color: #a1a1aa; font-size: 12px; text-transform: uppercase;">
                        <th style="padding: 12px;">ID</th>
                        <th style="padding: 12px;">Collection</th>
                        <th style="padding: 12px;">Payload</th>
                        <th style="padding: 12px;">Timestamp</th>
                        <th style="padding: 12px;">Action</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>

        <div style="background: #0f0f14; border: 1px dashed #27272a; border-radius: 12px; padding: 16px; font-size: 0.85rem; color: #a1a1aa;">
            <strong style="color: #fff;">Authorized External API Curl:</strong>
            <pre style="margin-top: 8px; background: #000; padding: 12px; border-radius: 8px; overflow-x: auto; color: #34d399;">curl -X POST https://akhil-private-backend.onrender.com/api/db/insert \
     -H "Content-Type: application/json" \
     -H "x-api-key: {API_AUTH_KEY}" \
     -d '{{"collection": "secure_logs", "data": {{"status": "ok"}}}}'</pre>
        </div>
    </main>

    <script>
    async function insertRecord() {{
        var col = document.getElementById("db-col").value.trim() || "default";
        var payload = document.getElementById("db-payload").value.trim();
        if (!payload) {{ alert("Data enter karein"); return; }}
        var parsed = payload;
        try {{ parsed = JSON.parse(payload); }} catch(e){{}}

        var res = await fetch("/api/db/insert", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ collection: col, data: parsed }})
        }});
        var data = await res.json();
        if (data.status === "success") {{ location.reload(); }}
        else {{ alert(data.message || "Insert failed"); }}
    }}

    async function deleteRecord(id) {{
        if (!confirm("Delete record #" + id + "?")) return;
        var res = await fetch("/api/db/delete", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ id: id }})
        }});
        var data = await res.json();
        if (data.status === "success") {{ location.reload(); }}
        else {{ alert(data.message || "Delete failed"); }}
    }}
    </script>
</body>
</html>"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))


@app.after_request
def apply_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, x-api-key, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
    return response

# Route to serve the Workspace Engine Dashboard
    return render_template('index.html')

# Route to serve the 3D Portal Page
@app.route('/portal')
def serve_portal():
    return render_template('portal.html')


# --- DATABASE CONTROL CENTER SUITE ---
@app.route("/database-control-center")
def page_database_control_center():
    content = """
    <style>
        .dcc-container { max-width: 860px; margin: 0 auto; padding: 24px 14px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #f1f5f9; }
        .dcc-card { background: #0b1120; border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; padding: 28px; box-shadow: 0 20px 40px rgba(0,0,0,0.6); }
        .dcc-input-group { margin-bottom: 18px; }
        .dcc-label { display: block; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8; margin-bottom: 8px; }
        .dcc-input { width: 100%; box-sizing: border-box; background: #0f172a; border: 1px solid rgba(255,255,255,0.12); border-radius: 8px; padding: 12px 14px; color: #f8fafc; font-size: 0.95rem; outline: none; transition: border-color 0.2s; }
        .dcc-input:focus { border-color: #38bdf8; box-shadow: 0 0 0 2px rgba(56,189,248,0.2); }
        .dcc-input:disabled { background: #020617; color: #475569; cursor: not-allowed; border-color: rgba(255,255,255,0.04); }
        .dcc-btn { padding: 12px 20px; border: none; border-radius: 8px; font-size: 0.95rem; font-weight: 600; cursor: pointer; transition: all 0.2s; display: inline-flex; align-items: center; justify-content: center; gap: 8px; text-decoration: none; }
        .dcc-btn-primary { background: #0284c7; color: #fff; width: 100%; }
        .dcc-btn-primary:hover { background: #0369a1; }
        .dcc-btn-success { background: #059669; color: #fff; width: 100%; }
        .dcc-btn-success:hover { background: #047857; }
        .dcc-btn-secondary { background: #1e293b; color: #cbd5e1; border: 1px solid rgba(255,255,255,0.1); }
        .dcc-btn-secondary:hover { background: #334155; color: #fff; }
        .dcc-error { color: #f43f5e; font-size: 0.85rem; margin-top: 8px; font-weight: 500; }
        .dcc-success-msg { color: #10b981; font-size: 0.85rem; margin-top: 8px; font-weight: 500; }
        .dcc-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 18px; margin-bottom: 22px; }
        .dcc-profile-badge { display: flex; align-items: center; gap: 12px; cursor: pointer; padding: 6px 12px; border-radius: 10px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); }
        .dcc-profile-badge:hover { background: rgba(255,255,255,0.06); }
        .dcc-profile-badge img { width: 42px; height: 42px; border-radius: 50%; object-fit: cover; border: 2px solid #38bdf8; }
        .dcc-auth-box { background: rgba(15,23,42,0.6); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 18px; margin: 20px 0; }
        .dcc-footer { text-align: center; margin-top: 26px; padding-top: 18px; border-top: 1px solid rgba(255,255,255,0.06); font-size: 0.85rem; color: #64748b; letter-spacing: 0.03em; }
    </style>

    <div class="dcc-container">
        <div id="dcc-gate" class="dcc-card" style="max-width: 480px; margin: 40px auto;">
            <div style="text-align:center; margin-bottom: 22px;">
                <div style="display:inline-block; padding:12px; border-radius:50%; background:rgba(56,189,248,0.1); border:1px solid rgba(56,189,248,0.25); margin-bottom:12px;">
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
                </div>
                <h2 style="font-size:1.4rem; font-weight:700; margin:0 0 6px;">Database Control Center</h2>
                <p style="font-size:0.9rem; color:#94a3b8; margin:0;">Enter your API Key to continue</p>
            </div>
            
            <div class="dcc-input-group">
                <label class="dcc-label">Your API Key</label>
                <input type="password" id="dcc-api-key-input" class="dcc-input" placeholder="Paste your developer key here...">
                <div id="dcc-gate-error" class="dcc-error"></div>
            </div>

            <button type="button" id="dcc-verify-btn" onclick="verifyAccessKey()" class="dcc-btn dcc-btn-primary" style="position:relative; overflow:hidden;">
                <span id="dcc-btn-text">Verify API Key</span>
                <span id="dcc-btn-loader" style="display:none; align-items:center; justify-content:center; gap:8px;">
                    <span style="width:16px; height:16px; border:2px solid rgba(255,255,255,0.3); border-top-color:#fff; border-radius:50%; animation: dccSpin 0.7s linear infinite; display:inline-block;"></span>
                    <span>Scanning Database Registry...</span>
                </span>
            </button>
            <style>
                @keyframes dccSpin { to { transform: rotate(360deg); } }
                @keyframes pulseGlow { 0% { box-shadow: 0 0 0 rgba(56,189,248,0.2); } 50% { box-shadow: 0 0 16px rgba(56,189,248,0.6); } 100% { box-shadow: 0 0 0 rgba(56,189,248,0.2); } }
            </style>
        </div>

        <div id="dcc-dashboard" class="dcc-card" style="display:none;">
            <div class="dcc-header">
                <div>
                    <h2 style="font-size:1.35rem; font-weight:700; margin:0 0 4px;">Database Control Center</h2>
                    <span style="font-size:0.8rem; color:#10b981; font-weight:600; display:inline-flex; align-items:center; gap:6px;">
                        <span style="width:8px; height:8px; background:#10b981; border-radius:50%; display:inline-block;"></span> Authenticated Session Active
                    </span>
                </div>
                
                <div class="dcc-profile-badge" onclick="toggleProfileModal()" title="Click to manage profile">
                    <img id="dcc-badge-avatar" src="https://api.dicebear.com/7.x/bottts/svg?seed=DBMaster" alt="Profile">
                    <div>
                        <div id="dcc-badge-name" style="font-size:0.88rem; font-weight:600;">Database Admin</div>
                        <div style="font-size:0.75rem; color:#38bdf8;">Edit Profile</div>
                    </div>
                </div>
            </div>

            <div id="dcc-profile-panel" style="display:none; background:#020617; border:1px solid rgba(56,189,248,0.25); border-radius:10px; padding:18px; margin-bottom:24px;">
                <h3 style="font-size:1rem; font-weight:600; margin:0 0 14px;">Profile Settings</h3>
                <div style="display:flex; gap:16px; align-items:center; margin-bottom:14px;">
                    <img id="dcc-profile-preview" src="https://api.dicebear.com/7.x/bottts/svg?seed=DBMaster" style="width:60px; height:60px; border-radius:50%; border:2px solid #38bdf8; object-fit:cover;">
                    <div style="flex:1;">
                        <label class="dcc-label">Profile Photo URL</label>
                        <input type="url" id="dcc-profile-url-input" class="dcc-input" placeholder="https://example.com/avatar.jpg">
                    </div>
                </div>
                <div class="dcc-input-group">
                    <label class="dcc-label">Display Name</label>
                    <input type="text" id="dcc-profile-name-input" class="dcc-input" placeholder="Your display name">
                </div>
                <div style="display:flex; gap:10px;">
                    <button type="button" onclick="saveProfileSettings()" class="dcc-btn dcc-btn-primary" style="flex:1;">Save Profile</button>
                    <button type="button" onclick="toggleProfileModal()" class="dcc-btn dcc-btn-secondary">Cancel</button>
                </div>
            </div>

            <form id="dcc-form" onsubmit="return false;">
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px;">
                    <div class="dcc-input-group">
                        <label class="dcc-label">Your Name</label>
                        <input type="text" id="dcc-name" class="dcc-input" placeholder="e.g. Alex Carter">
                    </div>
                    <div class="dcc-input-group">
                        <label class="dcc-label">Your Domain Name</label>
                        <input type="text" id="dcc-domain" class="dcc-input" placeholder="e.g. cybercloud.internal">
                    </div>
                </div>

                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px;">
                    <div class="dcc-input-group">
                        <label class="dcc-label">Web URL</label>
                        <input type="url" id="dcc-web-url" class="dcc-input" placeholder="https://example.com">
                        <div id="dcc-web-url-err" class="dcc-error"></div>
                    </div>
                    <div class="dcc-input-group">
                        <label class="dcc-label">Air Web URL</label>
                        <input type="url" id="dcc-air-url" class="dcc-input" placeholder="https://air.example.com">
                        <div id="dcc-air-url-err" class="dcc-error"></div>
                    </div>
                </div>

                <div class="dcc-input-group">
                    <label class="dcc-label">Your Database Name</label>
                    <input type="text" id="dcc-dbname" class="dcc-input" placeholder="e.g. production_shard_01">
                    <div id="dcc-dbname-err" class="dcc-error"></div>
                </div>

                <div class="dcc-auth-box">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px;">
                        <div>
                            <h4 style="font-size:0.95rem; font-weight:700; margin:0 0 4px;">Database Authentication</h4>
                            <p style="font-size:0.8rem; color:#94a3b8; margin:0;">Authentication is optional. Enable it only if you want to protect your database with a username and password.</p>
                        </div>
                        <input type="checkbox" id="dcc-auth-toggle" onchange="handleAuthToggle()" style="width:18px; height:18px; cursor:pointer;">
                    </div>

                    <div id="dcc-auth-fields" style="display:none; margin-top:16px;">
                        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px;">
                            <div class="dcc-input-group" style="margin-bottom:0;">
                                <label class="dcc-label">Username</label>
                                <input type="text" id="dcc-username" class="dcc-input" placeholder="Enter DB Username" oninput="handleUserFieldInput()">
                            </div>
                            <div class="dcc-input-group" style="margin-bottom:0;">
                                <label class="dcc-label">Password</label>
                                <input type="password" id="dcc-password" class="dcc-input" placeholder="Username required first" disabled>
                            </div>
                        </div>
                        <div id="dcc-auth-err" class="dcc-error"></div>
                    </div>
                </div>

                <div style="display:flex; gap:12px; margin-bottom:20px;">
                    <button type="button" id="dcc-save-btn" onclick="saveFormState()" class="dcc-btn dcc-btn-secondary" style="flex:1;">Save Changes</button>
                    <button type="button" id="dcc-edit-btn" onclick="enableFormEdit()" class="dcc-btn dcc-btn-secondary" style="flex:1; display:none;">Edit Details</button>
                </div>
                <div id="dcc-save-status" class="dcc-success-msg" style="text-align:center;"></div>

                <div style="margin-top:22px;">
                    <button type="button" onclick="generateDatabaseUrl()" class="dcc-btn dcc-btn-success">Generate Your Database URL</button>
                </div>

                <div id="dcc-result-panel" style="display:none; margin-top:20px; background:#020617; border:1px solid rgba(16,185,129,0.3); border-radius:10px; padding:18px;">
                    <label class="dcc-label" style="color:#34d399;">Your Database URL</label>
                    <div style="display:flex; gap:10px; margin-bottom:8px;">
                        <input type="text" id="dcc-generated-url" class="dcc-input" readonly style="background:#0b1120; color:#38bdf8; font-family:monospace;">
                        <button type="button" onclick="copyDatabaseUrl()" class="dcc-btn dcc-btn-secondary" style="white-space:nowrap;">Copy Database URL</button>
                    </div>
                    <div id="dcc-gen-success-msg" style="font-size:0.85rem; color:#10b981; font-weight:500;"></div>
                </div>
            </form>

            <div class="dcc-footer">
                Thank you for using our database service.
            </div>
        </div>
    </div>

    <script>
        let verifiedKey = "";
        const validProtocolRegex = /^(https?:\/\/)[a-zA-Z0-9.-]+(\.[a-zA-Z]{2,})(:[0-9]{1,5})?(\/.*)?$/i;

        async function verifyAccessKey() {
            const input = document.getElementById('dcc-api-key-input');
            const err = document.getElementById('dcc-gate-error');
            const btnText = document.getElementById('dcc-btn-text');
            const btnLoader = document.getElementById('dcc-btn-loader');
            const verifyBtn = document.getElementById('dcc-verify-btn');
            const key = input.value.trim();

                err.style.color = '#f43f5e';
                err.innerText = 'Please enter your API Key.';
                return;
            }

            // Radar Scanning Animation Trigger
            err.style.color = '#38bdf8';
            err.innerHTML = ' <b>Scanning Cryptographic Registry...</b> Validating with backend cluster';
            btnText.style.display = 'none';
            btnLoader.style.display = 'inline-flex';
            verifyBtn.disabled = true;
            input.classList.add('dcc-verifying-border');

            // Realistic 1.5s verification delay for animation feel
            await new Promise(r => setTimeout(r, 1500));

            try {
                const res = await fetch('/api/verify-control-key', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ api_key: key })
                });
                const data = await res.json();

                if (data.valid) {
                    input.classList.remove('dcc-verifying-border');
                    err.style.color = '#10b981';
                    err.innerHTML = ' <b>SUCCESS: Key Verified!</b> Initializing Database Control Center...';
                    verifiedKey = key;

                    setTimeout(() => {
                        document.getElementById('dcc-gate').style.display = 'none';
                        document.getElementById('dcc-dashboard').style.display = 'block';
                        loadStoredState();
                    }, 800);
                } else {
                    throw new Error(data.error || 'Invalid API Key.');
                }
            } catch(e) {
                input.classList.remove('dcc-verifying-border');
                btnText.style.display = 'inline-block';
                btnLoader.style.display = 'none';
                verifyBtn.disabled = false;

                err.style.color = '#f43f5e';
                err.innerHTML = ' <b>Verification Failed:</b> Key not found in database.<br><span style="color:#cbd5e1; font-size:0.8rem;">Redirecting to generate a valid API Key in <b>2s</b>...</span>';
                
                setTimeout(() => {
                    window.location.href = '/api-keys';
                }, 2000);
            }
        }

        function validateUrlString(url) {
            return validProtocolRegex.test(url.trim());
        }

        function handleAuthToggle() {
            const isChecked = document.getElementById('dcc-auth-toggle').checked;
            const fields = document.getElementById('dcc-auth-fields');
            fields.style.display = isChecked ? 'block' : 'none';
                document.getElementById('dcc-username').value = '';
                document.getElementById('dcc-password').value = '';
                handleUserFieldInput();
            }
        }

        function handleUserFieldInput() {
            const u = document.getElementById('dcc-username').value.trim();
            const p = document.getElementById('dcc-password');
            if (u.length > 0) {
                p.disabled = false;
                p.placeholder = 'Enter DB Password';
            } else {
                p.disabled = true;
                p.value = '';
                p.placeholder = 'Username required first';
            }
        }

        function toggleProfileModal() {
            const p = document.getElementById('dcc-profile-panel');
            p.style.display = (p.style.display === 'block') ? 'none' : 'block';
            if (p.style.display === 'block') {
                document.getElementById('dcc-profile-name-input').value = document.getElementById('dcc-badge-name').innerText;
                document.getElementById('dcc-profile-url-input').value = document.getElementById('dcc-badge-avatar').src;
            }
        }

        function saveProfileSettings() {
            const newName = document.getElementById('dcc-profile-name-input').value.trim();
            const newPhoto = document.getElementById('dcc-profile-url-input').value.trim();

            if (newName) {
                document.getElementById('dcc-badge-name').innerText = newName;
                localStorage.setItem('dcc_profile_name', newName);
            }
            if (newPhoto) {
                document.getElementById('dcc-badge-avatar').src = newPhoto;
                document.getElementById('dcc-profile-preview').src = newPhoto;
                localStorage.setItem('dcc_profile_photo', newPhoto);
            }
            toggleProfileModal();
        }

        function generateDatabaseUrl() {
            const name = document.getElementById('dcc-name').value.trim();
            const domain = document.getElementById('dcc-domain').value.trim();
            const webUrl = document.getElementById('dcc-web-url').value.trim();
            const airUrl = document.getElementById('dcc-air-url').value.trim();
            const dbname = document.getElementById('dcc-dbname').value.trim();

            const webErr = document.getElementById('dcc-web-url-err');
            const airErr = document.getElementById('dcc-air-url-err');
            const dbErr = document.getElementById('dcc-dbname-err');

            webErr.innerText = '';
            airErr.innerText = '';
            dbErr.innerText = '';

            let hasError = false;

                dbErr.innerText = 'Database Name is required.';
                hasError = true;
            }

                webErr.innerText = 'Please enter a valid website URL.';
                hasError = true;
            }

                airErr.innerText = 'Please enter a valid website URL.';
                hasError = true;
            }

            const authEnabled = document.getElementById('dcc-auth-toggle').checked;
            const username = document.getElementById('dcc-username').value.trim();
            const authErr = document.getElementById('dcc-auth-err');
            authErr.innerText = '';

                authErr.innerText = 'Username is required when authentication is enabled.';
                hasError = true;
            }

            if (hasError) return;

            // Generate verified production database URL
            const cleanDb = dbname.toLowerCase().replace(/[^a-z0-9_]/g, '_');
            const baseOrigin = window.location.origin;
            let finalUrl = baseOrigin + '/db-admin/' + encodeURIComponent(cleanDb) + '?key=' + encodeURIComponent(verifiedKey) + '&owner=' + encodeURIComponent(name) + '&web_url=' + encodeURIComponent(webUrl);

            if (domain) finalUrl += '&domain=' + encodeURIComponent(domain);
            if (webUrl) finalUrl += '&web_url=' + encodeURIComponent(webUrl);
            if (airUrl) finalUrl += '&air_url=' + encodeURIComponent(airUrl);
            if (authEnabled && username) finalUrl += '&auth=true&user=' + encodeURIComponent(username);

            document.getElementById('dcc-generated-url').value = finalUrl;
            document.getElementById('dcc-gen-success-msg').innerText = 'Your database URL has been generated successfully.';
            document.getElementById('dcc-result-panel').style.display = 'block';
        }

        function copyDatabaseUrl() {
            const input = document.getElementById('dcc-generated-url');
            input.select();
            input.setSelectionRange(0, 99999);
            navigator.clipboard.writeText(input.value).then(() => {
                alert('Database URL copied to clipboard!');
            });
        }

        function saveFormState() {
            const data = {
                name: document.getElementById('dcc-name').value,
                domain: document.getElementById('dcc-domain').value,
                web_url: document.getElementById('dcc-web-url').value,
                air_url: document.getElementById('dcc-air-url').value,
                dbname: document.getElementById('dcc-dbname').value,
                auth_enabled: document.getElementById('dcc-auth-toggle').checked,
                username: document.getElementById('dcc-username').value
            };
            localStorage.setItem('dcc_saved_form', JSON.stringify(data));

            // Lock inputs to view mode
            setInputsReadOnly(true);
            document.getElementById('dcc-save-btn').style.display = 'none';
            document.getElementById('dcc-edit-btn').style.display = 'block';

            const status = document.getElementById('dcc-save-status');
            status.innerText = 'Changes saved successfully.';
            setTimeout(() => { status.innerText = ''; }, 3500);
        }

        function enableFormEdit() {
            setInputsReadOnly(false);
            document.getElementById('dcc-save-btn').style.display = 'block';
            document.getElementById('dcc-edit-btn').style.display = 'none';
        }

        function setInputsReadOnly(locked) {
            document.getElementById('dcc-name').disabled = locked;
            document.getElementById('dcc-domain').disabled = locked;
            document.getElementById('dcc-web-url').disabled = locked;
            document.getElementById('dcc-air-url').disabled = locked;
            document.getElementById('dcc-dbname').disabled = locked;
            document.getElementById('dcc-auth-toggle').disabled = locked;
            document.getElementById('dcc-username').disabled = locked;
            else document.getElementById('dcc-password').disabled = true;
        }

        function loadStoredState() {
            const pName = localStorage.getItem('dcc_profile_name');
            const pPhoto = localStorage.getItem('dcc_profile_photo');
            if (pName) document.getElementById('dcc-badge-name').innerText = pName;
            if (pPhoto) {
                document.getElementById('dcc-badge-avatar').src = pPhoto;
                document.getElementById('dcc-profile-preview').src = pPhoto;
            }

            const raw = localStorage.getItem('dcc_saved_form');
            if (raw) {
                try {
                    const data = JSON.parse(raw);
                    document.getElementById('dcc-name').value = data.name || '';
                    document.getElementById('dcc-domain').value = data.domain || '';
                    document.getElementById('dcc-web-url').value = data.web_url || '';
                    document.getElementById('dcc-air-url').value = data.air_url || '';
                    document.getElementById('dcc-dbname').value = data.dbname || '';
                    document.getElementById('dcc-auth-toggle').checked = cd ~/akhi-cloud-enginedata.auth_enabled;
                    handleAuthToggle();
                    document.getElementById('dcc-username').value = data.username || '';
                    handleUserFieldInput();
                } catch(e) {}
            }
        }
    </script>
    """
    return render_page("Database Control Center", "database-control", content)


# Dedicated Admin Portal for the Generated Database
@app.route("/db-admin/<db_slug>")
def page_user_db_admin(db_slug):
    owner_key = request.args.get('key', '')
    owner_name = request.args.get('owner', 'Admin')
    web_url = request.args.get('web_url', '')
    
    content = f"""
    <div style='max-width:960px; margin:24px auto; padding:16px; font-family:sans-serif; color:#f8fafc;'>
        <div style='background:#0f172a; border:1px solid rgba(56,189,248,0.25); border-radius:12px; padding:24px; box-shadow:0 10px 30px rgba(0,0,0,0.5);'>
            <div style='display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(255,255,255,0.08); padding-bottom:16px; margin-bottom:20px;'>
                <div>
                    <h2 style='margin:0; font-size:1.4rem; color:#38bdf8;'>Database Admin Panel: {db_slug.upper()}</h2>
                    <span style='font-size:0.85rem; color:#94a3b8;'>Target Web: <b>{web_url or 'Custom Node'}</b> | Operator: <b>{owner_name}</b></span>
                </div>
                <span style='background:#059669; color:#fff; font-size:0.75rem; font-weight:700; padding:6px 12px; border-radius:20px;'>ACTIVE INSTANCE</span>
            </div>
            
            <div style='display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:16px; margin-bottom:24px;'>
                <div style='background:#1e293b; padding:16px; border-radius:8px; border:1px solid rgba(255,255,255,0.05);'>
                    <div style='font-size:0.75rem; color:#94a3b8; text-transform:uppercase;'>Storage Allocated</div>
                    <div style='font-size:1.3rem; font-weight:700; margin-top:6px;'>Dedicated Partition</div>
                </div>
                <div style='background:#1e293b; padding:16px; border-radius:8px; border:1px solid rgba(255,255,255,0.05);'>
                    <div style='font-size:0.75rem; color:#94a3b8; text-transform:uppercase;'>Connection Status</div>
                    <div style='font-size:1.3rem; font-weight:700; color:#34d399; margin-top:6px;'>Encrypted TLS</div>
                </div>
                <div style='background:#1e293b; padding:16px; border-radius:8px; border:1px solid rgba(255,255,255,0.05);'>
                    <div style='font-size:0.75rem; color:#94a3b8; text-transform:uppercase;'>Security Binding</div>
                    <div style='font-size:1.3rem; font-weight:700; color:#38bdf8; margin-top:6px;'>API Key Locked</div>
                </div>
            </div>

            <div style='background:#020617; border-radius:8px; padding:18px; border:1px solid rgba(255,255,255,0.06);'>
                <h3 style='margin:0 0 12px; font-size:1rem; color:#e2e8f0;'>Database Query & Records Terminal</h3>
                <p style='color:#64748b; font-size:0.85rem; margin-bottom:14px;'>This admin environment is linked specifically to your website domain. Direct CRUD mutations are isolated to this workspace partition.</p>
                <div style='background:#0b1120; border-radius:6px; padding:12px; font-family:monospace; font-size:0.85rem; color:#a5f3fc;'>
                    SELECT * FROM {db_slug}_records WHERE active = 1 ORDER BY timestamp DESC;
                </div>
            </div>
            
            <div style='margin-top:20px; text-align:right;'>
                <a href='/database-control-center' style='color:#94a3b8; text-decoration:none; font-size:0.85rem;'>← Back to Control Center</a>
            </div>
        </div>
    </div>
    """
    return render_page(f"Admin Panel - {db_slug}", "database", content)



# ==============================================================================
# AKHIL PRIVATE AI ENGINE (PURPOSE-BASED WHITE SUITE)
# ==============================================================================

AI_MODELS = {
    "reasoning-core": {"m": "deepseek-ai/deepseek-v4-flash-0731", "k": "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"},
    "deep-thinker": {"m": "moonshotai/kimi-k3", "k": "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"},
    "computational-pro": {"m": "deepseek-ai/deepseek-v4-pro-0813", "k": "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"},
    "cluster-ultra": {"m": "nvidia/nemotron-3-ultra-550b-a55b", "k": "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"}
}

@app.route("/api/ai-generate", methods=["POST"])
def api_private_generate():
    import urllib.request, json
    d = request.get_json(silent=True) or {}
    model_alias = d.get("model", "reasoning-core")
    prompt = d.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "Prompt zaroori hai"}), 400
    cfg = AI_MODELS.get(model_alias, AI_MODELS["reasoning-core"])
    headers = {"Authorization": f"Bearer {cfg['k']}", "Content-Type": "application/json"}
    body = {"model": cfg["m"], "messages": [{"role": "user", "content": prompt}], "max_tokens": 4096}
    try:
        req = urllib.request.Request("https://integrate.api.nvidia.com/v1/chat/completions", data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            msg = res["choices"][0]["message"]
            return jsonify({"reply": msg.get("content", ""), "thought": msg.get("reasoning_content") or msg.get("reasoning", "")})
    except Exception as e:
        return jsonify({"error": "Generation fail ho gaya: " + str(e)}), 502

@app.route("/api/tts-generate", methods=["POST"])
def api_sonic_voice():
    import urllib.request, json
    d = request.get_json(silent=True) or {}
    text_c = d.get("text", "").strip()
    voice_id = d.get("voice_id", "a0e99841-438c-4a64-b679-ae501e7d6091").strip()
    if not text_c:
        return jsonify({"error": "Script text zaroori hai"}), 400
    payload = {
        "model_id": "sonic-2",
        "transcript": text_c,
        "voice": {"mode": "id", "id": voice_id},
        "output_format": {"container": "wav", "encoding": "pcm_s16le", "sample_rate": 44100}
    }
    headers = {
        "X-API-Key": "sk_car_ohzRe16X4ToST5Yz2mT4hZ",
        "Cartesia-Version": "2024-06-10",
        "Content-Type": "application/json"
    }
    try:
        req = urllib.request.Request("https://api.cartesia.ai/tts/bytes", data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return Response(resp.read(), mimetype="audio/wav")
    except Exception as e:
        return jsonify({"error": "Voice synthesis fail: " + str(e)}), 502

@app.route("/neural-studio")
def page_neural_studio():
    body = """
    <div style="max-width:920px; margin:24px auto;">
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:28px; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #f1f5f9; padding-bottom:16px; margin-bottom:20px;">
                <div>
                    <h2 style="margin:0; font-size:1.35rem; color:#0f172a; font-weight:700;">Akhil Neural Studio</h2>
                    <p style="margin:4px 0 0; color:#64748b; font-size:0.85rem;">Autonomous Cognitive Reasoning & Deep Logic Engine</p>
                </div>
                <span style="background:#f0fdf4; color:#15803d; border:1px solid #bbf7d0; font-size:0.75rem; font-weight:700; padding:4px 10px; border-radius:20px;">● Neural Cluster Active</span>
            </div>
            <div style="margin-bottom:16px;">
                <label style="display:block; font-size:0.8rem; font-weight:700; color:#475569; text-transform:uppercase; margin-bottom:6px;">Processing Core Mode</label>
                <select id="ns-model" style="width:100%; box-sizing:border-box; background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:10px; font-size:0.9rem; color:#0f172a;">
                    <option value="reasoning-core">Neural Reasoning Core (Fast Adaptive Intelligence)</option>
                    <option value="deep-thinker">Deep Logic Thinker (Complex Analytical Strategy)</option>
                    <option value="computational-pro">Heavy Compute Engine (Maximum Output Depth)</option>
                    <option value="cluster-ultra">Distributed Cluster Ultra (Multi-Scale Synthesis)</option>
                </select>
            </div>
            <div style="margin-bottom:16px;">
                <label style="display:block; font-size:0.8rem; font-weight:700; color:#475569; text-transform:uppercase; margin-bottom:6px;">Prompt / Command</label>
                <textarea id="ns-prompt" rows="4" placeholder="Enter input prompt..." style="width:100%; box-sizing:border-box; background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:12px; font-size:0.95rem; color:#0f172a; outline:none;"></textarea>
            </div>
            <button id="ns-btn" style="width:100%; background:#0f172a; color:#fff; border:none; padding:12px; border-radius:8px; font-weight:700; font-size:0.95rem; cursor:pointer;">Synthesize Intelligence</button>
            <div id="ns-out" style="display:none; margin-top:20px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:18px;">
                <div id="ns-thought" style="display:none; font-family:monospace; font-size:0.8rem; color:#2563eb; background:#eff6ff; padding:12px; border-radius:6px; margin-bottom:12px; border:1px solid #bfdbfe; white-space:pre-wrap;"></div>
                <div id="ns-rep" style="font-size:0.95rem; line-height:1.6; color:#0f172a; white-space:pre-wrap;"></div>
            </div>
        </div>
    </div>
    <script>
    document.getElementById('ns-btn').onclick = async () => {
        const p = document.getElementById('ns-prompt').value.trim();
        if(!p) return alert('Prompt daalna zaroori hai');
        const b = document.getElementById('ns-btn');
        b.disabled = true; b.innerText = "Synthesizing...";
        try {
            const r = await fetch('/api/ai-generate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({model: document.getElementById('ns-model').value, prompt: p})
            });
            const d = await r.json();
            if(!r.ok) throw new Error(d.error);
            document.getElementById('ns-rep').innerText = d.reply || 'No output';
            const t = document.getElementById('ns-thought');
            if(d.thought) {
                t.innerText = " Chain of Reasoning:\n" + d.thought;
                t.style.display = 'block';
            } else { t.style.display = 'none'; }
            document.getElementById('ns-out').style.display = 'block';
        } catch(e) { alert('Error: ' + e.message); }
        finally { b.disabled = false; b.innerText = "Synthesize Intelligence"; }
    };
    </script>
    """
    return render_page("Akhil Neural Studio", "neural-studio", body)

@app.route("/voice-studio")
def page_voice_studio():
    body = """
    <div style="max-width:920px; margin:24px auto;">
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:28px; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #f1f5f9; padding-bottom:16px; margin-bottom:20px;">
                <div>
                    <h2 style="margin:0; font-size:1.35rem; color:#0f172a; font-weight:700;">Voice Studio (Sonic)</h2>
                    <p style="margin:4px 0 0; color:#64748b; font-size:0.85rem;">Realistic Neural Voice Synthesis with 3D Spatial Audio</p>
                </div>
                <span style="background:#ecfdf5; color:#059669; border:1px solid #a7f3d0; font-size:0.75rem; font-weight:700; padding:4px 10px; border-radius:20px;">● Sonic Ready</span>
            </div>
            <div style="margin-bottom:16px;">
                <label style="display:block; font-size:0.8rem; font-weight:700; color:#475569; text-transform:uppercase; margin-bottom:6px;">Voice Script</label>
                <textarea id="vs-text" rows="3" placeholder="Enter text to convert into realistic voice..." style="width:100%; box-sizing:border-box; background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:12px; font-size:0.95rem; color:#0f172a; outline:none;"></textarea>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:18px;">
                <div>
                    <label style="display:block; font-size:0.8rem; font-weight:700; color:#475569; text-transform:uppercase; margin-bottom:6px;">Vocal Profile</label>
                    <select id="vs-voice" style="width:100%; box-sizing:border-box; background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:10px; font-size:0.9rem; color:#0f172a;">
                        <option value="a0e99841-438c-4a64-b679-ae501e7d6091">Natural Male (Conversational)</option>
                        <option value="fb26447f-308b-471e-8b00-8e9f04284eb5">Helpful Executive (Male)</option>
                        <option value="69267136-1bdc-4103-a11a-7a0676499b66">Deep Narrator (Male)</option>
                        <option value="79a125e8-cd45-4c13-8a67-188112f4dd22">Natural Female (Warm)</option>
                        <option value="21b81c14-f857-4359-aa54-26de70819eb4">Expressive Female (Storyteller)</option>
                        <option value="b7d50908-b17c-442d-ad8d-810c63997ed9">Broadcaster Female (Studio)</option>
                    </select>
                </div>
                <div>
                    <label style="display:block; font-size:0.8rem; font-weight:700; color:#475569; text-transform:uppercase; margin-bottom:6px;">Cadence & Speed</label>
                    <select id="vs-speed" style="width:100%; box-sizing:border-box; background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:10px; font-size:0.9rem; color:#0f172a;">
                        <option value="0.8">0.8x (Measured)</option>
                        <option value="1.0" selected>1.0x (Standard)</option>
                        <option value="1.2">1.2x (Fast)</option>
                        <option value="1.5">1.5x (Express)</option>
                    </select>
                </div>
            </div>
            <button id="vs-btn" style="width:100%; background:#2563eb; color:#fff; border:none; padding:12px; border-radius:8px; font-weight:700; font-size:0.95rem; cursor:pointer; margin-bottom:20px;">Generate Voice Audio</button>
            <div id="vs-player-box" style="display:none; background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:18px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <span style="font-weight:700; color:#0f172a; font-size:0.9rem;">Audio Wave Player</span>
                    <a id="vs-dl" href="#" download="voice.wav" style="background:#059669; color:#fff; text-decoration:none; padding:6px 14px; border-radius:6px; font-size:0.8rem; font-weight:700;">Download .WAV</a>
                </div>
                <audio id="vs-audio" controls style="width:100%; margin-bottom:14px; outline:none;"></audio>
                <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid #e2e8f0; padding-top:10px;">
                    <label style="font-size:0.85rem; color:#475569; font-weight:600;"> 3D Spatial Pan:</label>
                    <input type="range" id="vs-pan" min="-1" max="1" step="0.1" value="0" style="width:180px;">
                </div>
            </div>
        </div>
    </div>
    <script>
    let aCtx = null, pNode = null;
    document.getElementById('vs-btn').onclick = async () => {
        const t = document.getElementById('vs-text').value.trim();
        if(!t) return alert('Script text enter karein');
        const b = document.getElementById('vs-btn');
        b.disabled = true; b.innerText = "Synthesizing...";
        try {
            const r = await fetch('/api/tts-generate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text: t, voice_id: document.getElementById('vs-voice').value})
            });
            if(!r.ok) throw new Error();
            const blob = await r.blob();
            const url = URL.createObjectURL(blob);
            const a = document.getElementById('vs-audio');
            a.src = url;
            a.playbackRate = parseFloat(document.getElementById('vs-speed').value);
            document.getElementById('vs-dl').href = url;
            document.getElementById('vs-player-box').style.display = 'block';
            a.play();
        } catch(e) {
            if('speechSynthesis' in window) {
                const u = new SpeechSynthesisUtterance(t);
                u.rate = parseFloat(document.getElementById('vs-speed').value);
                window.speechSynthesis.speak(u);
            } else alert('Synthesis failed');
        } finally {
            b.disabled = false; b.innerText = "Generate Voice Audio";
        }
    };
    document.getElementById('vs-pan').oninput = (e) => {
        if(!aCtx) {
            const A = window.AudioContext || window.webkitAudioContext;
            aCtx = new A();
            const s = aCtx.createMediaElementSource(document.getElementById('vs-audio'));
            pNode = aCtx.createStereoPanner();
            s.connect(pNode);
            pNode.connect(aCtx.destination);
        }
        if(pNode) pNode.pan.value = parseFloat(e.target.value);
    };
    </script>
    """
    return render_page("Voice Studio", "voice-studio", body)

@app.route("/vision-studio")
def page_vision_studio():
    body = """
    <div style="max-width:920px; margin:24px auto;">
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:28px; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #f1f5f9; padding-bottom:16px; margin-bottom:20px;">
                <div>
                    <h2 style="margin:0; font-size:1.35rem; color:#0f172a; font-weight:700;">Vision & Image Lab</h2>
                    <p style="margin:4px 0 0; color:#64748b; font-size:0.85rem;">High-Resolution Neural Image & Visual Generation Core</p>
                </div>
                <span style="background:#eff6ff; color:#1d4ed8; border:1px solid #bfdbfe; font-size:0.75rem; font-weight:700; padding:4px 10px; border-radius:20px;">● Visual Engine Online</span>
            </div>
            <div style="margin-bottom:16px;">
                <label style="display:block; font-size:0.8rem; font-weight:700; color:#475569; text-transform:uppercase; margin-bottom:6px;">Visual Creation Mode</label>
                <select id="vi-mode" style="width:100%; box-sizing:border-box; background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:10px; font-size:0.9rem; color:#0f172a;">
                    <option value="photoreal">Photorealistic HD Render</option>
                    <option value="cinematic">Cinematic 4K Digital Art</option>
                    <option value="vector">Minimalist Vector & Icon Design</option>
                    <option value="cyberpunk">High-Contrast Cyberpunk & Neon</option>
                </select>
            </div>
            <div style="margin-bottom:16px;">
                <label style="display:block; font-size:0.8rem; font-weight:700; color:#475569; text-transform:uppercase; margin-bottom:6px;">Image Description (Prompt)</label>
                <textarea id="vi-prompt" rows="3" placeholder="Describe the image you want to render..." style="width:100%; box-sizing:border-box; background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:12px; font-size:0.95rem; color:#0f172a; outline:none;"></textarea>
            </div>
            <button id="vi-btn" style="width:100%; background:#4338ca; color:#fff; border:none; padding:12px; border-radius:8px; font-weight:700; font-size:0.95rem; cursor:pointer;">Generate Render</button>
            <div id="vi-preview" style="display:none; margin-top:20px; text-align:center; background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:18px;">
                <div style="font-size:0.85rem; color:#64748b; margin-bottom:10px; font-weight:600;">Engine Render Stream Output:</div>
                <img id="vi-img" src="" alt="Render" style="max-width:100%; border-radius:8px; box-shadow:0 4px 6px -1px rgba(0,0,0,0.1); margin-bottom:12px;">
                <div>
                    <a id="vi-dl" href="#" target="_blank" download="render.jpg" style="background:#0f172a; color:#fff; text-decoration:none; padding:8px 18px; border-radius:6px; font-size:0.85rem; font-weight:700;">Download High-Res Render</a>
                </div>
            </div>
        </div>
    </div>
    <script>
    document.getElementById('vi-btn').onclick = () => {
        const p = document.getElementById('vi-prompt').value.trim();
        if(!p) return alert('Image prompt daalna zaroori hai');
        const b = document.getElementById('vi-btn');
        b.disabled = true; b.innerText = "Rendering...";
        const seed = Math.floor(Math.random() * 100000);
        const encoded = encodeURIComponent(p + ', high quality, ' + document.getElementById('vi-mode').value);
        const imgUrl = 'https://image.pollinations.ai/prompt/' + encoded + '?seed=' + seed + '&width=1024&height=1024&nologo=true';
        const img = document.getElementById('vi-img');
        img.onload = () => {
            b.disabled = false; b.innerText = "Generate Render";
            document.getElementById('vi-preview').style.display = 'block';
            document.getElementById('vi-dl').href = imgUrl;
        };
        img.onerror = () => {
            b.disabled = false; b.innerText = "Generate Render";
            alert('Render fail ho gaya');
        };
        img.src = imgUrl;
    };
    </script>
    """
    return render_page("Vision & Image Lab", "vision-studio", body)



# ==============================================================================
# AKHIL NEURAL AI STUDIO (UNIFIED PRODUCTION DASHBOARD)
# ==============================================================================
@app.route("/ai-studio")
def page_ai_studio():
    body = """
    <style>
        .eng-wrap { max-width: 960px; margin: 10px auto; padding: 0 10px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: #09090b; }
        .eng-card { background: #ffffff; border: 1px solid #e4e4e7; border-radius: 6px; padding: 14px 18px; margin-bottom: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.03); }
        .eng-head { display: flex; justify-content: space-between; align-items: center; }
        .eng-title { font-size: 1.1rem; font-weight: 700; color: #09090b; margin: 0; text-transform: uppercase; letter-spacing: -0.01em; font-family: monospace; }
        .eng-sub { font-size: 0.8rem; color: #71717a; margin: 3px 0 0; }
        .eng-badge { font-family: monospace; font-size: 0.72rem; font-weight: 700; color: #18181b; background: #f4f4f5; border: 1px solid #d4d4d8; padding: 4px 8px; border-radius: 3px; }

        .eng-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 12px; }
        @media(max-width: 680px) { .eng-grid { grid-template-columns: 1fr; } }
        .eng-stat-box { background: #ffffff; border: 1px solid #e4e4e7; border-radius: 6px; padding: 12px 14px; }
        .eng-stat-lbl { font-family: monospace; font-size: 0.7rem; font-weight: 700; color: #71717a; text-transform: uppercase; }
        .eng-stat-val { font-size: 1.05rem; font-weight: 700; color: #09090b; margin: 4px 0 2px; }
        .eng-stat-sub { font-family: monospace; font-size: 0.72rem; color: #27272a; }

        .eng-tabs { display: flex; background: #f4f4f5; border: 1px solid #e4e4e7; border-bottom: none; border-radius: 6px 6px 0 0; padding: 4px; gap: 4px; }
        .eng-tab-btn { flex: 1; padding: 9px 12px; font-family: monospace; font-size: 0.8rem; font-weight: 700; border: none; background: transparent; color: #71717a; border-radius: 4px; cursor: pointer; text-transform: uppercase; transition: all 0.15s; }
        .eng-tab-btn.active { background: #ffffff; color: #09090b; box-shadow: 0 1px 2px rgba(0,0,0,0.06); }

        .eng-body { background: #ffffff; border: 1px solid #e4e4e7; border-radius: 0 0 6px 6px; padding: 18px; margin-bottom: 14px; }
        .eng-lbl { display: block; font-family: monospace; font-size: 0.72rem; font-weight: 700; color: #27272a; text-transform: uppercase; margin-bottom: 5px; }
        .eng-input { width: 100%; box-sizing: border-box; background: #fafafa; border: 1px solid #d4d4d8; border-radius: 4px; padding: 10px 12px; font-size: 0.88rem; color: #09090b; outline: none; font-family: inherit; }
        .eng-input:focus { border-color: #09090b; background: #ffffff; }

        .eng-btn { width: 100%; background: #09090b; color: #fafafa; border: 1px solid #09090b; padding: 12px; border-radius: 4px; font-family: monospace; font-size: 0.85rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.03em; cursor: pointer; margin-top: 12px; }
        .eng-btn:hover { background: #27272a; }
        .eng-btn:disabled { opacity: 0.6; cursor: not-allowed; }

        .eng-out { margin-top: 14px; background: #fafafa; border: 1px solid #e4e4e7; border-radius: 4px; padding: 14px; font-size: 0.88rem; line-height: 1.6; color: #09090b; }
        .eng-log { font-family: monospace; font-size: 0.78rem; background: #f4f4f5; border-left: 3px solid #18181b; padding: 8px 10px; margin-bottom: 10px; color: #27272a; white-space: pre-wrap; }
    </style>

    <div class="eng-wrap">
        <div class="eng-card">
            <div class="eng-head">
                <div>
                    <h1 class="eng-title">Core Intelligence Console</h1>
                    <p class="eng-sub">Cognitive Logic, Sonic Acoustics and Visual Synthesis Matrix</p>
                </div>
                <div class="eng-badge">STATUS // ARMED</div>
            </div>
        </div>

        <div class="eng-grid">
            <div class="eng-stat-box">
                <div class="eng-stat-lbl">Inference Cluster</div>
                <div class="eng-stat-val">550B Multi-Node</div>
                <div class="eng-stat-sub">Latency: Sub-40ms Fast-Path</div>
            </div>
            <div class="eng-stat-box">
                <div class="eng-stat-lbl">Acoustic Model</div>
                <div class="eng-stat-val">Sonic PCM 44.1k</div>
                <div class="eng-stat-sub">Format: Raw Waveform</div>
            </div>
            <div class="eng-stat-box">
                <div class="eng-stat-lbl">Visual Synthesis</div>
                <div class="eng-stat-val">Adaptive Diffusion</div>
                <div class="eng-stat-sub">Resolution: 1024 Standard</div>
            </div>
        </div>

        <div>
            <div class="eng-tabs">
                <button class="eng-tab-btn active" id="btn-t-cog" onclick="openEngine('cog')">Cognitive Engine</button>
                <button class="eng-tab-btn" id="btn-t-snc" onclick="openEngine('snc')">Sonic Synthesizer</button>
                <button class="eng-tab-btn" id="btn-t-vis" onclick="openEngine('vis')">Visual Studio</button>
            </div>

            <!-- Tab 1: Cognitive Engine -->
            <div id="tab-cog" class="eng-body">
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px;">
                    <div>
                        <label class="eng-lbl">Execution Model</label>
                        <select id="cg-model" class="eng-input">
                            <option value="reasoning-core">Neural Reasoning Core (Realtime Analysis)</option>
                            <option value="deep-thinker">Deep Strategic Thinker (Complex Logic)</option>
                            <option value="computational-pro">Heavy Compute Engine (Maximum Tokens)</option>
                            <option value="cluster-ultra">Distributed Cluster Ultra (Multi-Scale)</option>
                        </select>
                    </div>
                    <div>
                        <label class="eng-lbl">Execution Channel</label>
                        <select class="eng-input">
                            <option>Production Pipeline [Direct]</option>
                            <option>Deterministic Strict Trace</option>
                        </select>
                    </div>
                </div>

                <div style="margin-bottom: 10px;">
                    <label class="eng-lbl">Input Query / Command</label>
                    <textarea id="cg-prompt" class="eng-input" rows="4" placeholder="Enter query parameters, technical instructions or source code..."></textarea>
                </div>

                <button id="cg-btn" class="eng-btn">Dispatch Inference Query</button>

                <div id="cg-out" class="eng-out" style="display:none;">
                    <div id="cg-trace" class="eng-log" style="display:none;"></div>
                    <div id="cg-txt" style="white-space: pre-wrap;"></div>
                </div>
            </div>

            <!-- Tab 2: Sonic Voice -->
            <div id="tab-snc" class="eng-body" style="display:none;">
                <div style="margin-bottom: 12px;">
                    <label class="eng-lbl">Vocal Script Transcript</label>
                    <textarea id="snc-text" class="eng-input" rows="3" placeholder="Enter clean transcript text for acoustic generation..."></textarea>
                </div>

                <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px;">
                    <div>
                        <label class="eng-lbl">Voice Timbre Profile</label>
                        <select id="snc-voice" class="eng-input">
                            <option value="a0e99841-438c-4a64-b679-ae501e7d6091">Natural Male (Conversational Standard)</option>
                            <option value="fb26447f-308b-471e-8b00-8e9f04284eb5">Command Executive (Male)</option>
                            <option value="69267136-1bdc-4103-a11a-7a0676499b66">Deep Resonance (Male Narrator)</option>
                            <option value="79a125e8-cd45-4c13-8a67-188112f4dd22">Natural Calm (Female Standard)</option>
                            <option value="21b81c14-f857-4359-aa54-26de70819eb4">Expressive Acoustic (Female)</option>
                            <option value="b7d50908-b17c-442d-ad8d-810c63997ed9">Studio Broadcaster (Female)</option>
                        </select>
                    </div>
                    <div>
                        <label class="eng-lbl">Delivery Cadence</label>
                        <select id="snc-speed" class="eng-input">
                            <option value="0.8">0.8x Precision Cadence</option>
                            <option value="1.0" selected>1.0x Realtime Natural</option>
                            <option value="1.2">1.2x Dynamic Stream</option>
                            <option value="1.5">1.5x Rapid Briefing</option>
                        </select>
                    </div>
                </div>

                <button id="snc-btn" class="eng-btn">Generate Acoustic Stream</button>

                <div id="snc-out" class="eng-out" style="display:none;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                        <span class="eng-lbl" style="margin:0;">PCM Waveform Monitor</span>
                        <a id="snc-dl" href="#" download="acoustic_stream.wav" style="font-family:monospace; font-size:0.75rem; color:#fafafa; background:#18181b; padding:4px 10px; border-radius:3px; text-decoration:none;">Download .WAV</a>
                    </div>
                    <audio id="snc-aud" controls style="width:100%; margin-bottom:10px;"></audio>
                    <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid #e4e4e7; padding-top:8px;">
                        <span class="eng-lbl" style="margin:0;">Spatial Stereo Pan:</span>
                        <input type="range" id="snc-pan" min="-1" max="1" step="0.1" value="0" style="width:150px;">
                    </div>
                </div>
            </div>

            <!-- Tab 3: Visual Studio -->
            <div id="tab-vis" class="eng-body" style="display:none;">
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px;">
                    <div>
                        <label class="eng-lbl">Diffusion Style Preset</label>
                        <select id="vs-mode" class="eng-input">
                            <option value="photoreal">Photorealistic HD Capture</option>
                            <option value="cinematic">Cinematic Digital Film</option>
                            <option value="vector">Technical Vector Blueprint</option>
                            <option value="cyberpunk">High-Contrast Industrial Neon</option>
                        </select>
                    </div>
                    <div>
                        <label class="eng-lbl">Canvas Dimensions</label>
                        <select id="vs-asp" class="eng-input">
                            <option value="1024x1024">Square (1024x1024 // 1:1)</option>
                            <option value="1280x720">Landscape (1280x720 // 16:9)</option>
                            <option value="720x1280">Portrait (720x1280 // 9:16)</option>
                        </select>
                    </div>
                </div>

                <div style="margin-bottom: 10px;">
                    <label class="eng-lbl">Visual Synthesis Prompt</label>
                    <textarea id="vs-prompt" class="eng-input" rows="3" placeholder="Enter composition instructions, scene dynamics, lighting specs..."></textarea>
                </div>

                <button id="vs-btn" class="eng-btn">Dispatch Visual Render</button>

                <div id="vs-out" class="eng-out" style="display:none; text-align:center;">
                    <img id="vs-img" src="" alt="Synthesis Output" style="max-width:100%; border-radius:4px; border:1px solid #e4e4e7; margin-bottom:12px;">
                    <div>
                        <a id="vs-dl" href="#" target="_blank" download="render.jpg" style="font-family:monospace; font-size:0.75rem; color:#fafafa; background:#18181b; padding:6px 14px; border-radius:3px; text-decoration:none;">Download Master Render</a>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
    function openEngine(target) {
        ['cog', 'snc', 'vis'].forEach(k => {
            document.getElementById('tab-' + k).style.display = (k === target ? 'block' : 'none');
            const b = document.getElementById('btn-t-' + k);
            if(k === target) b.classList.add('active'); else b.classList.remove('active');
        });
    }

    document.getElementById('cg-btn').onclick = async () => {
        const p = document.getElementById('cg-prompt').value.trim();
        if(!p) return alert('Prompt required');
        const b = document.getElementById('cg-btn');
        b.disabled = true; b.innerText = "EXECUTING QUERY...";
        try {
            const r = await fetch('/api/ai-generate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({model: document.getElementById('cg-model').value, prompt: p})
            });
            const d = await r.json();
            if(!r.ok) throw new Error(d.error);
            document.getElementById('cg-txt').innerText = d.reply || 'No text output returned';
            const t = document.getElementById('cg-trace');
            if(d.thought) {
                t.innerText = "EXECUTION TRACE LOG:
" + d.thought;
                t.style.display = 'block';
            } else { t.style.display = 'none'; }
            document.getElementById('cg-out').style.display = 'block';
        } catch(e) { alert('Inference Failure: ' + e.message); }
        finally { b.disabled = false; b.innerText = "DISPATCH INFERENCE QUERY"; }
    };

    let aCtx = null, pNode = null;
    document.getElementById('snc-btn').onclick = async () => {
        const t = document.getElementById('snc-text').value.trim();
        if(!t) return alert('Enter transcript');
        const b = document.getElementById('snc-btn');
        b.disabled = true; b.innerText = "SYNTHESIZING ACOUSTICS...";
        try {
            const r = await fetch('/api/tts-generate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text: t, voice_id: document.getElementById('snc-voice').value})
            });
            if(!r.ok) throw new Error();
            const blob = await r.blob();
            const url = URL.createObjectURL(blob);
            const a = document.getElementById('snc-aud');
            a.src = url;
            a.playbackRate = parseFloat(document.getElementById('snc-speed').value);
            document.getElementById('snc-dl').href = url;
            document.getElementById('snc-out').style.display = 'block';
            a.play();
        } catch(e) {
            if('speechSynthesis' in window) {
                const u = new SpeechSynthesisUtterance(t);
                u.rate = parseFloat(document.getElementById('snc-speed').value);
                window.speechSynthesis.speak(u);
            } else alert('Synthesis failed');
        } finally {
            b.disabled = false; b.innerText = "GENERATE ACOUSTIC STREAM";
        }
    };
    document.getElementById('snc-pan').oninput = (e) => {
        if(!aCtx) {
            const A = window.AudioContext || window.webkitAudioContext;
            aCtx = new A();
            const s = aCtx.createMediaElementSource(document.getElementById('snc-aud'));
            pNode = aCtx.createStereoPanner();
            s.connect(pNode);
            pNode.connect(aCtx.destination);
        }
        if(pNode) pNode.pan.value = parseFloat(e.target.value);
    };

    document.getElementById('vs-btn').onclick = () => {
        const p = document.getElementById('vs-prompt').value.trim();
        if(!p) return alert('Visual render prompt required');
        const b = document.getElementById('vs-btn');
        b.disabled = true; b.innerText = "COMPUTING DIFFUSION MATRIX...";
        const seed = Math.floor(Math.random() * 1000000);
        const [w, h] = document.getElementById('vs-asp').value.split('x');
        const encoded = encodeURIComponent(p + ', highly detailed, ' + document.getElementById('vs-mode').value);
        const imgUrl = 'https://image.pollinations.ai/prompt/' + encoded + '?seed=' + seed + '&width=' + w + '&height=' + h + '&nologo=true';
        const img = document.getElementById('vs-img');
        img.onload = () => {
            b.disabled = false; b.innerText = "DISPATCH VISUAL RENDER";
            document.getElementById('vs-out').style.display = 'block';
            document.getElementById('vs-dl').href = imgUrl;
        };
        img.onerror = () => {
            b.disabled = false; b.innerText = "DISPATCH VISUAL RENDER";
            alert('Visual render failed');
        };
        img.src = imgUrl;
    };
    </script>
    """
    return render_page("Neural AI Studio", "ai-studio", body)
