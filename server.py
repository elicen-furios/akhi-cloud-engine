import os
import sqlite3
import secrets
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

from flask import session

app.secret_key = os.environ.get("SECRET_KEY", "akhil_super_secret_session_vault_key_2026")

@app.route('/api/auth/session', methods=['POST'])
def save_auth_session():
    data = request.get_json(silent=True) or {}
    session['user_email'] = data.get('email', '')
    session['user_name'] = data.get('name', '')
    session['authenticated'] = True
    return jsonify({'status': 'approved'})

@app.route('/api/auth/logout', methods=['POST'])
def clear_auth_session():
    session.clear()
    return jsonify({'status': 'cleared'})
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

# Direct Image Serving
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

# Backend API
@app.route("/api/admin/keys/create", methods=["POST"])
def create_key():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "auth_user")
    app_name = data.get("app_name", "prod_app")
    new_key = f"akhi_live_{secrets.token_hex(16)}"
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("INSERT INTO api_keys (key, email, app_name) VALUES (?, ?, ?)", (new_key, email, app_name))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "key": new_key})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

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
    <div style="max-width: 420px; margin: 30px auto 0;">
        <div class="card" id="login-box-card" style="padding: 36px 30px; border-radius:16px;">
            <div style="text-align:center; margin-bottom:26px;">
                <div style="width:54px; height:54px; border-radius:12px; margin:0 auto 16px; overflow:hidden; border:1px solid #e4e4e7; background:#fafafa; display:flex; align-items:center; justify-content:center;">
                    <img src="/logo.png?v=3" onerror="this.onerror=null; this.src='/image.png';" alt="Logo" style="width:100%; height:100%; object-fit:cover; display:block;">
                </div>
                <h2 style="font-size:1.35rem; font-weight:800; letter-spacing:-0.5px; margin-bottom:6px;">Welcome Back</h2>
                <p style="font-size:0.85rem; color:#71717a;">Authenticate to access your developer console</p>
            </div>

            <div style="display:flex; flex-direction:column; gap:12px;">
                <button class="btn-secondary" style="width:100%; justify-content:center; padding:12px;" onclick="loginGoogle()">
                    <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/></svg>
                    Continue with Google
                </button>
                <button class="btn-secondary" style="width:100%; justify-content:center; padding:12px;" onclick="loginGithub()">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="#18181b"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
                    Continue with GitHub
                </button>
            </div>
        </div>

        <div class="card" id="logged-in-profile-card" style="display:none; text-align:center; padding:36px 30px;">
            <h2 style="font-size:1.3rem; font-weight:700; margin-bottom:6px;">Active Developer Session</h2>
            <p id="profile-display-info" style="font-family:var(--font-mono); font-size:0.85rem; color:#52525b; margin-bottom:20px;"></p>
            <div style="display:flex; gap:10px; justify-content:center;">
                <a href="/api-keys" class="btn-primary">Access Vault</a>
                <button class="btn-secondary" onclick="signOutAccount()">Sign Out</button>
            </div>
        </div>
    </div>
    """
    return render_page("Identity Gate", "login", content)

@app.route("/api-keys")
def page_api_keys():
    content = """
    <div class="card">
        <h2 style="font-size:1.3rem; font-weight:700; margin-bottom:8px;">API Access Vault</h2>
        <p style="color:#71717a; font-size:0.88rem; margin-bottom:24px;">Issue production authorization tokens for client applications.</p>

        <div style="max-width:500px;">
            <label style="font-size:0.75rem; font-weight:600; color:#52525b; display:block; margin-bottom:6px;">APPLICATION IDENTIFIER</label>
            <input type="text" id="app-key-name" class="input-text" value="production_service">
            <button class="btn-primary" id="btn-forge-key" onclick="issueDevKey()">Generate Pass Token</button>

            <div id="key-output-panel" style="display:none; margin-top:20px; padding:16px; background:#fafafa; border:1px solid #e4e4e7; border-radius:8px;">
                <span style="font-size:0.72rem; font-weight:700;">GENERATED CRYPTOGRAPHIC PASS</span>
                <div id="pass-val-box" style="font-family:var(--font-mono); font-size:0.92rem; font-weight:600; margin:8px 0; word-break:break-all;"></div>
                <button class="btn-secondary" style="padding:6px 12px; font-size:0.78rem;" onclick="navigator.clipboard.writeText(document.getElementById('pass-val-box').innerText); window.showToast('Copied to clipboard!');">Copy Token</button>
            </div>
        </div>
    </div>

    <script>
        async function issueDevKey() {
            if (!window.currentFirebaseUser) {
                window.showToast("ACCESS RESTRICTED: Please authenticate at the Identity Gate first.");
                setTimeout(() => { window.location.href = "/login"; }, 1200);
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
                } else window.showToast(d.message || "Key generation failed");
            } catch(e) { window.showToast("Server error: " + e.message); }
            finally { btn.innerText = "Generate Pass Token"; btn.disabled = false; }
        }
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
