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
            if (!confirm("Revoke this token permanently?")) return;
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
