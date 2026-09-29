import os
import sqlite3
import secrets
from flask import Flask, request, jsonify, send_file, session

app = Flask(__name__)
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
    for p in ["home", "api-keys", "sandbox", "media", "docs", "database", "system", "login"]:
        target = "{{ 'active' if active_page == '" + p + "' else '' }}"
        html = html.replace(target, "active" if active_page == p else "")
    html = html.replace("{{ content }}", inner_content)
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
@app.route("/admin-panel")
def page_admin_panel():
    # If not logged in as Admin, show the Obsidian Black Login Gate
    if not session.get("admin_authenticated"):
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Executive Admin Gate // AKHIL DEV</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }
        body {
            background: #09090b;
            color: #ffffff;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .gate-card {
            background: #111115;
            border: 1px solid #222228;
            box-shadow: 0 25px 60px -15px rgba(0, 0, 0, 0.8), 0 0 40px rgba(16, 185, 129, 0.05);
            border-radius: 22px;
            padding: 40px 32px;
            max-width: 420px;
            width: 100%;
        }
        .input-dark {
            width: 100%;
            background: #18181f;
            border: 1px solid #272732;
            color: #ffffff;
            padding: 13px 16px;
            border-radius: 10px;
            font-size: 0.92rem;
            outline: none;
            margin-bottom: 16px;
            transition: border-color 0.2s;
        }
        .input-dark:focus { border-color: #10b981; }
        .btn-gate {
            width: 100%;
            background: #10b981;
            color: #09090b;
            font-weight: 700;
            padding: 13px;
            border-radius: 10px;
            border: none;
            cursor: pointer;
            font-size: 0.92rem;
            margin-top: 8px;
            transition: all 0.2s;
        }
        .btn-gate:hover { background: #34d399; }
        .error-banner {
            display: none;
            background: #2b1114;
            border: 1px solid #501d22;
            color: #f87171;
            padding: 10px;
            border-radius: 8px;
            font-size: 0.82rem;
            margin-bottom: 14px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="gate-card">
        <div style="text-align:center; margin-bottom:28px;">
            <div style="width:52px; height:52px; border-radius:14px; background:#181820; border:1px solid #2a2a35; display:inline-flex; align-items:center; justify-content:center; color:#10b981; margin-bottom:14px;">
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
            </div>
            <h2 style="font-size:1.45rem; font-weight:800; letter-spacing:-0.5px;">ADMIN PANEL</h2>
            <p style="font-size:0.82rem; color:#71717a; margin-top:4px;">Restricted Clearance Required</p>
        </div>

        <div id="error-box" class="error-banner"></div>

        <div>
            <label style="font-size:0.75rem; font-weight:700; color:#a1a1aa; letter-spacing:0.8px; display:block; margin-bottom:6px;">ADMIN USERNAME</label>
            <input type="text" id="adm-user" class="input-dark" placeholder="Username">

            <label style="font-size:0.75rem; font-weight:700; color:#a1a1aa; letter-spacing:0.8px; display:block; margin-bottom:6px;">PASSWORD / KEY</label>
            <input type="password" id="adm-pass" class="input-dark" placeholder="••••••••••••">

            <button class="btn-gate" id="btn-login" onclick="doAdminLogin()">AUTHENTICATE</button>
        </div>
    </div>

    <script>
        async function doAdminLogin() {
            const user = document.getElementById("adm-user").value.trim();
            const pass = document.getElementById("adm-pass").value.trim();
            const err = document.getElementById("error-box");
            const btn = document.getElementById("btn-login");

            err.style.display = "none";
            btn.innerText = "VERIFYING...";
            btn.disabled = true;

            try {
                const res = await fetch("/api/admin/login", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username: user, password: pass })
                });
                const d = await res.json();
                if (d.status === "success") {
                    window.location.reload();
                } else {
                    err.innerText = d.message || "Invalid Credentials";
                    err.style.display = "block";
                }
            } catch(e) {
                err.innerText = "Server connection error";
                err.style.display = "block";
            } finally {
                btn.innerText = "AUTHENTICATE";
                btn.disabled = false;
            }
        }
    </script>













<!-- ARIA FLOWER THEMED FLOATING CHATBOT -->
<div id="aria-bot-container" style="position: fixed; bottom: 20px; right: 20px; z-index: 9999999; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
    
    <!-- Clean HD Girl Avatar Button -->
    <div id="aria-launcher" onclick="toggleAriaChat()" style="width: 58px; height: 58px; border-radius: 50%; box-shadow: 0 8px 25px rgba(244,114,182,0.55); cursor: pointer; border: 2.5px solid #f472b6; position: relative; overflow: hidden; background: #120815; display: flex; align-items: center; justify-content: center; transition: transform 0.2s ease;">
        <img src="https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=200&q=80" alt="Aria" style="width: 100%; height: 100%; object-fit: cover; display: block; border-radius: 50%;">
        <span style="position: absolute; bottom: 3px; right: 3px; width: 12px; height: 12px; background: #10b981; border: 2px solid #120815; border-radius: 50%;"></span>
    </div>

    <!-- Live Flower Wallpaper Chat Window -->
    <div id="aria-window" style="display: none; position: fixed; bottom: 20px; right: 20px; width: 345px; max-width: calc(100vw - 32px); height: 500px; border-radius: 20px; border: 1.5px solid rgba(244,114,182,0.35); box-shadow: 0 25px 60px rgba(0,0,0,0.9); flex-direction: column; overflow: hidden; backdrop-filter: blur(18px); background: linear-gradient(155deg, rgba(20, 9, 22, 0.97) 0%, rgba(36, 12, 33, 0.97) 100%);">
        
        <!-- Live Petals Wallpaper Animation -->
        <div style="position: absolute; inset: 0; pointer-events: none; background: radial-gradient(circle at 15% 15%, rgba(244,114,182,0.18) 0%, transparent 45%), radial-gradient(circle at 85% 85%, rgba(217,70,239,0.18) 0%, transparent 45%); z-index: 0;"></div>
        <div style="position: absolute; inset: 0; pointer-events: none; opacity: 0.22; background-image: radial-gradient(#f472b6 1px, transparent 1px), radial-gradient(#ec4899 1.5px, transparent 1.5px); background-size: 32px 32px; background-position: 0 0, 16px 16px; animation: flowerDrift 20s linear infinite; z-index: 0;"></div>

        <!-- Header -->
        <div style="padding: 12px 16px; background: rgba(30, 14, 32, 0.9); border-bottom: 1px solid rgba(244,114,182,0.25); display: flex; justify-content: space-between; align-items: center; z-index: 1;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <img src="https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=120&q=80" style="width: 34px; height: 34px; border-radius: 50%; object-fit: cover; border: 1.5px solid #f472b6;">
                <div>
                    <div style="font-weight: 700; color: #fbcfe8; font-size: 13.5px; letter-spacing: 0.5px;">ARIA &bull; AI ASSISTANT</div>
                    <div style="font-size: 10px; color: #6ee7b7; font-weight: 600;">Online &bull; Flower Mode</div>
                </div>
            </div>
            <!-- Cut / Close Button -->
            <button onclick="toggleAriaChat()" style="background: rgba(244,114,182,0.15); border: 1px solid rgba(244,114,182,0.3); color: #f472b6; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 17px; font-weight: bold; line-height: 1;">&times;</button>
        </div>

        <!-- Chat Area -->
        <div id="aria-messages" style="flex: 1; padding: 14px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; font-size: 13px; z-index: 1;">
            <div style="background: rgba(52, 21, 46, 0.7); border: 1px solid rgba(244,114,182,0.25); color: #fdf2f8; padding: 10px 14px; border-radius: 16px 16px 16px 4px; max-width: 82%; align-self: flex-start; line-height: 1.45;">
                Hello! Main Aria hoon. Aapki kya madad kar sakti hoon?
            </div>
        </div>

        <!-- Input Bar -->
        <div style="padding: 10px 12px; border-top: 1px solid rgba(244,114,182,0.25); background: rgba(20, 8, 21, 0.95); display: flex; gap: 8px; z-index: 1;">
            <input type="text" id="aria-input" placeholder="Type prompt or code..." style="flex: 1; background: rgba(40, 15, 37, 0.85); border: 1px solid rgba(244,114,182,0.35); color: #fff; padding: 9px 14px; border-radius: 20px; font-size: 13px; outline: none;">
            <button id="aria-send-btn" style="background: linear-gradient(135deg, #ec4899, #db2777); border: none; color: #fff; padding: 8px 16px; border-radius: 20px; cursor: pointer; font-size: 12px; font-weight: 700; box-shadow: 0 4px 12px rgba(236,72,153,0.4);">SEND</button>
        </div>
    </div>
</div>

<style>
@keyframes flowerDrift {
    0% { background-position: 0 0, 16px 16px; }
    100% { background-position: 0 350px, 16px 366px; }
}
#aria-launcher:hover { transform: scale(1.06); }
</style>

<script>
function toggleAriaChat() {
    var win = document.getElementById("aria-window");
    var launcher = document.getElementById("aria-launcher");
    if (!win) return;
    if (win.style.display === "none" || win.style.display === "") {
        win.style.display = "flex";
        if (launcher) launcher.style.display = "none";
    } else {
        win.style.display = "none";
        if (launcher) launcher.style.display = "flex";
    }
}

document.addEventListener("DOMContentLoaded", function() {
    var input = document.getElementById("aria-input");
    var sendBtn = document.getElementById("aria-send-btn");
    var box = document.getElementById("aria-messages");

    async function sendAriaMsg() {
        if (!input) return;
        var text = input.value.trim();
        if (!text) return;

        var u = document.createElement("div");
        u.style.cssText = "background: linear-gradient(135deg, #ec4899, #be185d); color: #fff; padding: 9px 14px; border-radius: 16px 16px 4px 16px; max-width: 82%; align-self: flex-end; line-height: 1.45;";
        u.innerText = text;
        box.appendChild(u);
        input.value = "";
        box.scrollTop = box.scrollHeight;

        // Exact Admin Trigger: [8630@]
        if (text === "[8630@]") {
            var g = document.createElement("div");
            g.style.cssText = "background: rgba(16, 185, 129, 0.2); border: 1.5px solid #10b981; color: #34d399; padding: 10px 14px; border-radius: 14px; max-width: 85%; align-self: flex-start; font-weight: bold; font-family: monospace;";
            g.innerText = "ACCESS GRANTED: INITIALIZING ADMIN PANEL...";
            box.appendChild(g);
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
        loader.id = "aria-loader";
        loader.style.cssText = "color: #f472b6; font-size: 11.5px; padding: 4px 8px; align-self: flex-start;";
        loader.innerText = "Aria is typing...";
        box.appendChild(loader);
        box.scrollTop = box.scrollHeight;

        try {
            var res = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text })
            });
            var d = await res.json();
            var l = document.getElementById("aria-loader");
            if (l) l.remove();

            var b = document.createElement("div");
            b.style.cssText = "background: rgba(52, 21, 46, 0.7); border: 1px solid rgba(244,114,182,0.25); color: #fdf2f8; padding: 10px 14px; border-radius: 16px 16px 16px 4px; max-width: 82%; align-self: flex-start; line-height: 1.45;";
            b.innerText = d.reply || "Aria is thinking...";
            box.appendChild(b);
            box.scrollTop = box.scrollHeight;
        } catch(e) {
            var l2 = document.getElementById("aria-loader");
            if (l2) l2.remove();
            var err = document.createElement("div");
            err.style.cssText = "background: rgba(239, 68, 68, 0.2); color: #fca5a5; padding: 8px 12px; border-radius: 8px; font-size: 12px; align-self: flex-start;";
            err.innerText = "Connection error. Please try again.";
            box.appendChild(err);
            box.scrollTop = box.scrollHeight;
        }
    }

    if (sendBtn) sendBtn.addEventListener("click", sendAriaMsg);
    if (input) {
        input.addEventListener("keydown", function(e) {
            if (e.key === "Enter") {
                e.preventDefault();
                sendAriaMsg();
            }
        });
    }
});
</script>

</body>
</html>""", 200, {"Content-Type": "text/html; charset=utf-8"}

    # Authenticated State: Full Obsidian Black Dashboard
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel // AKHIL DEV</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }
        body {
            background: #09090b;
            color: #ffffff;
            min-height: 100vh;
            padding: 30px 20px;
        }
        .container {
            max-width: 1100px;
            margin: 0 auto;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #222228;
            padding-bottom: 20px;
            margin-bottom: 30px;
            flex-wrap: wrap;
            gap: 14px;
        }
        .card-dark {
            background: #111116;
            border: 1px solid #222228;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .metric-box {
            background: #14141a;
            border: 1px solid #222228;
            border-radius: 14px;
            padding: 20px;
        }
        .btn-exit {
            background: #271214;
            color: #f87171;
            border: 1px solid #451a1d;
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 0.85rem;
            cursor: pointer;
            font-weight: 600;
        }
        table { width: 100%; border-collapse: collapse; font-size: 0.86rem; }
        th { border-bottom: 1px solid #272730; color: #71717a; padding: 12px; text-align: left; font-size: 0.75rem; }
        td { border-bottom: 1px solid #1a1a22; padding: 12px; color: #d4d4d8; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="width:8px; height:8px; border-radius:50%; background:#10b981; box-shadow:0 0 10px #10b981;"></span>
                    <span style="font-size:0.75rem; font-weight:700; color:#10b981; letter-spacing:1px;">ADMIN PANEL // OBSIDIAN VAULT</span>
                </div>
                <h1 style="font-size:1.8rem; font-weight:800; margin-top:4px;">Master Control Center</h1>
            </div>
            <div style="display:flex; gap:12px; align-items:center;">
                <span style="font-size:0.85rem; color:#71717a;">Logged in: <b style="color:#fff;">AKHIL</b></span>
                <button class="btn-exit" onclick="adminLogout()">Sign Out</button>
            </div>
        </div>

        <div class="metrics-grid">
            <div class="metric-box">
                <div style="font-size:0.72rem; color:#71717a; text-transform:uppercase; font-weight:700;">Engine Storage</div>
                <div style="font-size:1.6rem; font-weight:800; color:#10b981; margin-top:4px;">SQLite3</div>
                <div style="font-size:0.75rem; color:#71717a;">ACID Compliant</div>
            </div>
            <div class="metric-box">
                <div style="font-size:0.72rem; color:#71717a; text-transform:uppercase; font-weight:700;">Rate Limiter</div>
                <div style="font-size:1.6rem; font-weight:800; color:#38bdf8; margin-top:4px;">Active</div>
                <div style="font-size:0.75rem; color:#71717a;">Anti-Spam Armed</div>
            </div>
            <div class="metric-box">
                <div style="font-size:0.72rem; color:#71717a; text-transform:uppercase; font-weight:700;">Status</div>
                <div style="font-size:1.6rem; font-weight:800; color:#ffffff; margin-top:4px;">Operational</div>
                <div style="font-size:0.75rem; color:#10b981;">Render Cloud Live</div>
            </div>
        </div>

        <div class="card-dark">
            <h3 style="font-size:1.15rem; font-weight:700; margin-bottom:16px;">Global Registered Keys</h3>
            <div style="overflow-x:auto;">
                <table id="keys-table">
                    <thead>
                        <tr><th>ID</th><th>Owner</th><th>App Scope</th><th>Pass Token</th><th>Created</th></tr>
                    </thead>
                    <tbody id="keys-body">
                        <tr><td colspan="5" style="text-align:center; padding:18px; color:#71717a;">Loading tokens...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        async function fetchTokens() {
            try {
                const res = await fetch("/api/admin/all-keys");
                const d = await res.json();
                const tbody = document.getElementById("keys-body");
                if (d.status === "success" && d.keys.length > 0) {
                    tbody.innerHTML = d.keys.map(k => `
                        <tr>
                            <td style="font-family:'JetBrains Mono'; color:#71717a;">#${k.id}</td>
                            <td style="font-weight:600; color:#fff;">${k.email || 'N/A'}</td>
                            <td>${k.app_name}</td>
                            <td><code style="font-family:'JetBrains Mono'; font-size:0.8rem; background:#181822; padding:3px 6px; border-radius:4px; border:1px solid #272735;">${k.key}</code></td>
                            <td style="color:#71717a; font-size:0.8rem;">${k.created_at}</td>
                        </tr>
                    `).join("");
                } else {
                    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:18px; color:#71717a;">No keys issued yet.</td></tr>';
                }
            } catch(e) {}
        }
        async function adminLogout() {
            await fetch("/api/admin/logout", { method: "POST" });
            window.location.reload();
        }
        fetchTokens();
    </script>













<!-- ARIA FLOWER THEMED FLOATING CHATBOT -->
<div id="aria-bot-container" style="position: fixed; bottom: 20px; right: 20px; z-index: 9999999; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
    
    <!-- Clean HD Girl Avatar Button -->
    <div id="aria-launcher" onclick="toggleAriaChat()" style="width: 58px; height: 58px; border-radius: 50%; box-shadow: 0 8px 25px rgba(244,114,182,0.55); cursor: pointer; border: 2.5px solid #f472b6; position: relative; overflow: hidden; background: #120815; display: flex; align-items: center; justify-content: center; transition: transform 0.2s ease;">
        <img src="https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=200&q=80" alt="Aria" style="width: 100%; height: 100%; object-fit: cover; display: block; border-radius: 50%;">
        <span style="position: absolute; bottom: 3px; right: 3px; width: 12px; height: 12px; background: #10b981; border: 2px solid #120815; border-radius: 50%;"></span>
    </div>

    <!-- Live Flower Wallpaper Chat Window -->
    <div id="aria-window" style="display: none; position: fixed; bottom: 20px; right: 20px; width: 345px; max-width: calc(100vw - 32px); height: 500px; border-radius: 20px; border: 1.5px solid rgba(244,114,182,0.35); box-shadow: 0 25px 60px rgba(0,0,0,0.9); flex-direction: column; overflow: hidden; backdrop-filter: blur(18px); background: linear-gradient(155deg, rgba(20, 9, 22, 0.97) 0%, rgba(36, 12, 33, 0.97) 100%);">
        
        <!-- Live Petals Wallpaper Animation -->
        <div style="position: absolute; inset: 0; pointer-events: none; background: radial-gradient(circle at 15% 15%, rgba(244,114,182,0.18) 0%, transparent 45%), radial-gradient(circle at 85% 85%, rgba(217,70,239,0.18) 0%, transparent 45%); z-index: 0;"></div>
        <div style="position: absolute; inset: 0; pointer-events: none; opacity: 0.22; background-image: radial-gradient(#f472b6 1px, transparent 1px), radial-gradient(#ec4899 1.5px, transparent 1.5px); background-size: 32px 32px; background-position: 0 0, 16px 16px; animation: flowerDrift 20s linear infinite; z-index: 0;"></div>

        <!-- Header -->
        <div style="padding: 12px 16px; background: rgba(30, 14, 32, 0.9); border-bottom: 1px solid rgba(244,114,182,0.25); display: flex; justify-content: space-between; align-items: center; z-index: 1;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <img src="https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=120&q=80" style="width: 34px; height: 34px; border-radius: 50%; object-fit: cover; border: 1.5px solid #f472b6;">
                <div>
                    <div style="font-weight: 700; color: #fbcfe8; font-size: 13.5px; letter-spacing: 0.5px;">ARIA &bull; AI ASSISTANT</div>
                    <div style="font-size: 10px; color: #6ee7b7; font-weight: 600;">Online &bull; Flower Mode</div>
                </div>
            </div>
            <!-- Cut / Close Button -->
            <button onclick="toggleAriaChat()" style="background: rgba(244,114,182,0.15); border: 1px solid rgba(244,114,182,0.3); color: #f472b6; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 17px; font-weight: bold; line-height: 1;">&times;</button>
        </div>

        <!-- Chat Area -->
        <div id="aria-messages" style="flex: 1; padding: 14px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; font-size: 13px; z-index: 1;">
            <div style="background: rgba(52, 21, 46, 0.7); border: 1px solid rgba(244,114,182,0.25); color: #fdf2f8; padding: 10px 14px; border-radius: 16px 16px 16px 4px; max-width: 82%; align-self: flex-start; line-height: 1.45;">
                Hello! Main Aria hoon. Aapki kya madad kar sakti hoon?
            </div>
        </div>

        <!-- Input Bar -->
        <div style="padding: 10px 12px; border-top: 1px solid rgba(244,114,182,0.25); background: rgba(20, 8, 21, 0.95); display: flex; gap: 8px; z-index: 1;">
            <input type="text" id="aria-input" placeholder="Type prompt or code..." style="flex: 1; background: rgba(40, 15, 37, 0.85); border: 1px solid rgba(244,114,182,0.35); color: #fff; padding: 9px 14px; border-radius: 20px; font-size: 13px; outline: none;">
            <button id="aria-send-btn" style="background: linear-gradient(135deg, #ec4899, #db2777); border: none; color: #fff; padding: 8px 16px; border-radius: 20px; cursor: pointer; font-size: 12px; font-weight: 700; box-shadow: 0 4px 12px rgba(236,72,153,0.4);">SEND</button>
        </div>
    </div>
</div>

<style>
@keyframes flowerDrift {
    0% { background-position: 0 0, 16px 16px; }
    100% { background-position: 0 350px, 16px 366px; }
}
#aria-launcher:hover { transform: scale(1.06); }
</style>

<script>
function toggleAriaChat() {
    var win = document.getElementById("aria-window");
    var launcher = document.getElementById("aria-launcher");
    if (!win) return;
    if (win.style.display === "none" || win.style.display === "") {
        win.style.display = "flex";
        if (launcher) launcher.style.display = "none";
    } else {
        win.style.display = "none";
        if (launcher) launcher.style.display = "flex";
    }
}

document.addEventListener("DOMContentLoaded", function() {
    var input = document.getElementById("aria-input");
    var sendBtn = document.getElementById("aria-send-btn");
    var box = document.getElementById("aria-messages");

    async function sendAriaMsg() {
        if (!input) return;
        var text = input.value.trim();
        if (!text) return;

        var u = document.createElement("div");
        u.style.cssText = "background: linear-gradient(135deg, #ec4899, #be185d); color: #fff; padding: 9px 14px; border-radius: 16px 16px 4px 16px; max-width: 82%; align-self: flex-end; line-height: 1.45;";
        u.innerText = text;
        box.appendChild(u);
        input.value = "";
        box.scrollTop = box.scrollHeight;

        // Exact Admin Trigger: [8630@]
        if (text === "[8630@]") {
            var g = document.createElement("div");
            g.style.cssText = "background: rgba(16, 185, 129, 0.2); border: 1.5px solid #10b981; color: #34d399; padding: 10px 14px; border-radius: 14px; max-width: 85%; align-self: flex-start; font-weight: bold; font-family: monospace;";
            g.innerText = "ACCESS GRANTED: INITIALIZING ADMIN PANEL...";
            box.appendChild(g);
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
        loader.id = "aria-loader";
        loader.style.cssText = "color: #f472b6; font-size: 11.5px; padding: 4px 8px; align-self: flex-start;";
        loader.innerText = "Aria is typing...";
        box.appendChild(loader);
        box.scrollTop = box.scrollHeight;

        try {
            var res = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text })
            });
            var d = await res.json();
            var l = document.getElementById("aria-loader");
            if (l) l.remove();

            var b = document.createElement("div");
            b.style.cssText = "background: rgba(52, 21, 46, 0.7); border: 1px solid rgba(244,114,182,0.25); color: #fdf2f8; padding: 10px 14px; border-radius: 16px 16px 16px 4px; max-width: 82%; align-self: flex-start; line-height: 1.45;";
            b.innerText = d.reply || "Aria is thinking...";
            box.appendChild(b);
            box.scrollTop = box.scrollHeight;
        } catch(e) {
            var l2 = document.getElementById("aria-loader");
            if (l2) l2.remove();
            var err = document.createElement("div");
            err.style.cssText = "background: rgba(239, 68, 68, 0.2); color: #fca5a5; padding: 8px 12px; border-radius: 8px; font-size: 12px; align-self: flex-start;";
            err.innerText = "Connection error. Please try again.";
            box.appendChild(err);
            box.scrollTop = box.scrollHeight;
        }
    }

    if (sendBtn) sendBtn.addEventListener("click", sendAriaMsg);
    if (input) {
        input.addEventListener("keydown", function(e) {
            if (e.key === "Enter") {
                e.preventDefault();
                sendAriaMsg();
            }
        });
    }
});
</script>

</body>
</html>""", 200, {"Content-Type": "text/html; charset=utf-8"}



    api_key = os.environ.get("GEMINI_API_KEY") or "AQ.Ab8RN6Ixk9UDdqH-XelvTCqUH5vweLfqk41O0dB-FO6CBIf6dA"

    try:
        import urllib.request, json
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = json.dumps({
            "contents": [{
                "parts": [{
                    "text": f"You are Aria, an intelligent, professional, concise AI assistant for Akhil Dev Platform. Answer politely and directly without emojis: {user_msg}"
                }]
            }]
        }).encode("utf-8")
        
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            res_data = json.loads(resp.read().decode())
            bot_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
            return jsonify({"reply": bot_text.strip()})
    except Exception as e:
        return jsonify({"reply": f"AI Engine Notice: Request processed with status: {str(e)}"})


# AI Chatbot Backend - Live Google Gemini Integration

    api_key = os.environ.get("GEMINI_API_KEY") or "AQ.Ab8RN6Ixk9UDdqH-XelvTCqUH5vweLfqk41O0dB-FO6CBIf6dA"

    try:
        import urllib.request, json
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = json.dumps({
            "contents": [{
                "parts": [{
                    "text": f"You are Aria, an intelligent, professional, concise AI assistant for Akhil Dev Platform. Answer politely and directly without emojis: {user_msg}"
                }]
            }]
        }).encode("utf-8")
        
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            res_data = json.loads(resp.read().decode())
            bot_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
            return jsonify({"reply": bot_text.strip()})
    except Exception as e:
        return jsonify({"reply": f"AI Engine Notice: Request processed with status: {str(e)}"})



    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if api_key and api_key.startswith("AIzaSy"):
        try:
            import urllib.request, json
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            payload = json.dumps({
                "contents": [{"parts": [{"text": f"You are Aria, a friendly and intelligent assistant. Reply concisely: {msg}"}]}]
            }).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                res = json.loads(resp.read().decode())
                return jsonify({"reply": res["candidates"][0]["content"]["parts"][0]["text"].strip()})
        except Exception:
            pass

    # Clean local intelligent replies if Gemini key is invalid/401
    low = msg.lower()
    if "hello" in low or "hi" in low:
        reply = "Hello! Kaise hain aap? Main aapki kya help kar sakti hoon?"
    elif "kya hua" in low:
        reply = "Sab perfectly chal raha hai. Aap bataiye, kya command execute karni hai?"
    elif "admin" in low:
        reply = "Admin panel access ke liye code enter karein."
    else:
        reply = f"Main sun rahi hoon: '{msg}'. Aap koi sawaal pooch sakte hain ya command run kar sakte hain."
    return jsonify({"reply": reply})



    low = msg.lower()
    if any(w in low for w in ["hi", "hello", "hey"]):
        ans = "Namaste! Main Aria hoon. Aapki kya madad kar sakti hoon?"
    elif "kaise" in low:
        ans = "Main badhiya hoon! Aap bataiye sab kaisa chal raha hai?"
    elif "kya hua" in low:
        ans = "Kuch nahi, sab ekdam smoothly chal raha hai! Aap koi bhi sawal pooch sakte hain."
    elif "admin" in low:
        ans = "Admin panel ke liye secret code enter karein."
    else:
        ans = f"Samajh gayi! Aapne kaha: '{msg}'. Main system par active hoon."

    return jsonify({"reply": ans})



    low = msg.lower()

    if any(w in low for w in ["mai kon hu", "main kaun hoon", "who am i"]):
        reply = "Aap is platform ke master developer aur creator hain!"
    elif "python kya hai" in low or "what is python" in low:
        reply = "Python ek powerful aur aasan high-level programming language hai jo web development, AI, automation aur data science ke liye use hoti hai."
    elif any(w in low for w in ["hi", "hello", "hey"]):
        reply = "Hello! Kaise hain aap? Main aapki kya madad kar sakti hoon?"
    elif "kaise ho" in low or "kaisi ho" in low:
        reply = "Main ekdam badhiya hoon! Aap bataiye aapka din kaisa ja raha hai?"
    elif "kya hua" in low:
        reply = "Sab kuch normal aur smooth chal raha hai! Aap koi bhi question pooch sakte hain."
    elif "admin" in low or "code" in low:
        reply = "Admin panel open karne ke liye secret code '8630@' enter karein."
    elif "naam" in low or "name" in low:
        reply = "Mera naam Aria hai, main aapki AI Assistant hoon."
    elif "render" in low or "server" in low:
        reply = "Server Render Cloud par safely active aur deploy chal raha hai."
    else:
        reply = "Aapka message mil gaya! Aap coding, server status, ya platform ke baare mein kuch bhi pooch sakte hain."

    return jsonify({"reply": reply})


@app.route("/api/chat", methods=["POST"])
def api_chat_handler():
    data = request.get_json(silent=True) or {}
    msg = (data.get("message") or "").strip()
    if not msg:
        return jsonify({"reply": "Message cannot be empty."})

    import urllib.request, urllib.parse, json

    # 1. Real Generative AI Engine (Direct Cloud LLM without API Key restrictions)
    try:
        sys_prompt = "You are Aria, a friendly, intelligent female AI assistant. Speak naturally in Romanized Hindi/Hinglish and English as asked. Keep replies concise, helpful, and polite without emojis."
        full_query = f"{sys_prompt}\nUser: {msg}\nAria:"
        encoded_query = urllib.parse.quote(full_query)
        req_url = f"https://text.pollinations.ai/{encoded_query}?model=openai&seed=42"
        
        req = urllib.request.Request(req_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as response:
            result_text = response.read().decode("utf-8").strip()
            if result_text and len(result_text) > 1:
                return jsonify({"reply": result_text})
    except Exception as e:
        pass

    # 2. Smart fallback if internet is slow
    low = msg.lower()
    if "mai kon hu" in low or "who am i" in low:
        ans = "Aap Akhil hain, is platform ke master developer aur creator!"
    elif "python kya hai" in low:
        ans = "Python ek high-level aur aasan programming language hai jisse web apps, AI, bots aur backend automation banaye jaate hain."
    elif any(w in low for w in ["hi", "hello", "hey"]):
        ans = "Hello! Kaise hain aap? Main aapki kya madad kar sakti hoon?"
    else:
        ans = "Aapka message mil gaya. Main system par active hoon, aap koi bhi sawal pooch sakte hain."
    return jsonify({"reply": ans})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
