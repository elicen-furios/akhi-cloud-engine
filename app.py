import os
import sqlite3
import json
import urllib.request
import secrets
from flask import Flask, request, jsonify, redirect, url_for, Response

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(24))
DB_PATH = "data.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL UNIQUE,
            email TEXT,
            app_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

def render_page(title, active_tab, body_content):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | Akhi Cloud Engine</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #030712; color: #f3f4f6; display: flex; min-height: 100vh; }}
        .sidebar {{ width: 260px; background: #0b0f19; border-right: 1px solid rgba(255,255,255,0.08); padding: 24px 16px; display: flex; flex-direction: column; gap: 16px; }}
        .brand {{ font-size: 1.15rem; font-weight: 700; color: #38bdf8; padding: 0 10px; margin-bottom: 10px; }}
        .nav-list {{ display: flex; flex-direction: column; gap: 8px; }}
        .nav-item {{ display: flex; align-items: center; gap: 12px; padding: 10px 14px; border-radius: 8px; color: #94a3b8; text-decoration: none; font-size: 0.92rem; font-weight: 600; }}
        .nav-item:hover, .nav-item.active {{ background: rgba(56,189,248,0.12); color: #38bdf8; }}
        .main-content {{ flex: 1; display: flex; flex-direction: column; overflow-y: auto; }}
        .topbar {{ height: 60px; border-bottom: 1px solid rgba(255,255,255,0.08); display: flex; align-items: center; justify-content: space-between; padding: 0 28px; background: #0b0f19; }}
        .workspace {{ padding: 28px; flex: 1; }}
        @media (max-width: 768px) {{ body {{ flex-direction: column; }} .sidebar {{ width: 100%; }} }}
    </style>
</head>
<body>
    <aside class="sidebar">
        <div class="brand">AKHI CLOUD ENGINE</div>
        <nav class="nav-list">
            <a href="/" class="nav-item {'active' if active_tab == 'dashboard' else ''}">Dashboard</a>
            <a href="/api-keys" class="nav-item {'active' if active_tab == 'api-keys' else ''}">API Keys Registry</a>
            <a href="/nvidia-ai-hub" class="nav-item {'active' if active_tab == 'nvidia-hub' else ''}">Akhil Neural Studio</a>
            <a href="/voice-studio" class="nav-item {'active' if active_tab == 'voice-studio' else ''}">Voice Studio</a>
            <a href="/database-control-center" class="nav-item {'active' if active_tab == 'database-control' else ''}">DB Control Center</a>
        </nav>
    </aside>
    <main class="main-content">
        <header class="topbar">
            <div>{title}</div>
            <div style="color:#10b981; font-size:0.85rem; font-weight:600;">● Cluster Online</div>
        </header>
        <div class="workspace">{body_content}</div>
    </main>
</body>
</html>"""

@app.route("/")
def page_home():
    return render_page("Dashboard", "dashboard", """
    <div style="background:#0b1120; border:1px solid rgba(255,255,255,0.08); border-radius:14px; padding:28px;">
        <h2 style="margin-bottom:10px;">Akhi Cloud Engine Overview</h2>
        <p style="color:#94a3b8; margin-bottom:24px;">Integrated AI, Cartesia Neural Voice, and DB Orchestration Cluster.</p>
        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:16px;">
            <a href="/nvidia-ai-hub" style="text-decoration:none; background:#020617; border:1px solid rgba(118,185,0,0.3); border-radius:10px; padding:18px; color:#f8fafc;">
                <div style="color:#76b900; font-weight:700; margin-bottom:4px;">Akhil Neural Studio</div>
                <div style="color:#64748b; font-size:0.85rem;">DeepSeek v4 Pro/Flash, Nemotron 550B, Kimi K3 & Gemma.</div>
            </a>
            <a href="/voice-studio" style="text-decoration:none; background:#020617; border:1px solid rgba(56,189,248,0.3); border-radius:10px; padding:18px; color:#f8fafc;">
                <div style="color:#38bdf8; font-weight:700; margin-bottom:4px;">Voice Studio</div>
                <div style="color:#64748b; font-size:0.85rem;">Cartesia Sonic-2 voices with 3D audio filters & downloader.</div>
            </a>
            <a href="/database-control-center" style="text-decoration:none; background:#020617; border:1px solid rgba(16,185,129,0.3); border-radius:10px; padding:18px; color:#f8fafc;">
                <div style="color:#10b981; font-weight:700; margin-bottom:4px;">DB Control Center</div>
                <div style="color:#64748b; font-size:0.85rem;">Secure SQLite table management & auth generator.</div>
            </a>
        </div>
    </div>
    """)

@app.route("/api-keys", methods=["GET", "POST"])
def page_api_keys():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method == "POST":
        app_name = request.form.get("app_name", "").strip() or "Default App"
        email = request.form.get("email", "").strip() or "admin@akhi.internal"
        k = f"akhi_{secrets.token_hex(16)}"
        c.execute("INSERT INTO api_keys (key, email, app_name) VALUES (?, ?, ?)", (k, email, app_name))
        conn.commit()
        conn.close()
        return redirect(url_for("page_api_keys"))
    c.execute("SELECT id, key, app_name, email, created_at FROM api_keys ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    items = "".join([f"<tr style='border-bottom:1px solid rgba(255,255,255,0.06);'><td style='padding:10px;'>{r[2]}</td><td style='padding:10px; font-family:monospace; color:#38bdf8;'>{r[1]}</td><td style='padding:10px; color:#94a3b8;'>{r[3]}</td></tr>" for r in rows])
    return render_page("API Keys", "api-keys", f"""
    <div style="background:#0b1120; border:1px solid rgba(255,255,255,0.08); border-radius:14px; padding:24px;">
        <h2 style="margin-bottom:16px;">API Key Generator & Registry</h2>
        <form method="POST" style="display:flex; gap:10px; margin-bottom:24px; flex-wrap:wrap;">
            <input type="text" name="app_name" placeholder="Application Name" style="flex:1; background:#0f172a; border:1px solid rgba(255,255,255,0.12); border-radius:8px; padding:10px; color:#fff;" required>
            <input type="email" name="email" placeholder="Owner Email" style="flex:1; background:#0f172a; border:1px solid rgba(255,255,255,0.12); border-radius:8px; padding:10px; color:#fff;" required>
            <button type="submit" style="background:#0284c7; border:none; border-radius:8px; padding:10px 18px; color:#fff; font-weight:600; cursor:pointer;">Generate Key</button>
        </form>
        <table style="width:100%; border-collapse:collapse; text-align:left; font-size:0.9rem;">
            <thead><tr style="color:#94a3b8; border-bottom:1px solid rgba(255,255,255,0.1);"><th style="padding:8px;">App</th><th style="padding:8px;">Key</th><th style="padding:8px;">Email</th></tr></thead>
            <tbody>{items or "<tr><td colspan='3' style='padding:16px; text-align:center; color:#64748b;'>No keys found.</td></tr>"}</tbody>
        </table>
    </div>
    """)

@app.route("/api/verify-control-key", methods=["POST"])
def verify_control_key():
    data = request.get_json(silent=True) or {}
    key = data.get("api_key", "").strip()
    if not key:
        return jsonify({"valid": False, "error": "Please enter your API Key."}), 400
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, app_name, email FROM api_keys WHERE key = ?", (key,))
        row = c.fetchone()
        conn.close()
        if row:
            return jsonify({"valid": True, "app_name": row[1] or "User App", "email": row[2] or "", "key": key})
        return jsonify({"valid": False, "error": "Invalid API Key. Not found in database."}), 401
    except Exception as e:
        return jsonify({"valid": False, "error": str(e)}), 500

@app.route("/database-control-center")
def page_database_control_center():
    return render_page("DB Control Center", "database-control", """
    <div id="dcc-gate" style="max-width:460px; margin:40px auto; background:#0b1120; border:1px solid rgba(255,255,255,0.08); border-radius:14px; padding:24px; text-align:center;">
        <h2 style="margin-bottom:8px;">Database Control Center</h2>
        <p style="color:#94a3b8; font-size:0.9rem; margin-bottom:18px;">Enter your API Key to unlock database orchestration</p>
        <input type="text" id="dcc-key" placeholder="Paste your API Key..." style="width:100%; box-sizing:border-box; background:#0f172a; border:1px solid rgba(255,255,255,0.12); border-radius:8px; padding:12px; color:#fff; margin-bottom:14px;">
        <div id="dcc-status" style="font-size:0.85rem; margin-bottom:12px;"></div>
        <button id="dcc-vbtn" style="width:100%; background:#0284c7; color:#fff; border:none; padding:12px; border-radius:8px; font-weight:700; cursor:pointer;">Verify API Key</button>
    </div>
    <div id="dcc-dash" style="display:none; max-width:800px; margin:0 auto; background:#0b1120; border:1px solid rgba(255,255,255,0.08); border-radius:14px; padding:24px;">
        <h3 style="margin-bottom:16px; color:#10b981;">✔ Session Verified & Active</h3>
        <input type="text" id="dcc-dbname" placeholder="Enter Database Name (e.g. users_db)" style="width:100%; box-sizing:border-box; background:#0f172a; border:1px solid rgba(255,255,255,0.12); border-radius:8px; padding:12px; color:#fff; margin-bottom:14px;">
        <button id="dcc-genbtn" style="background:#059669; color:#fff; border:none; padding:12px 20px; border-radius:8px; font-weight:700; cursor:pointer;">Generate Database URL</button>
        <div id="dcc-res" style="display:none; margin-top:16px; background:#020617; padding:14px; border-radius:8px;">
            <input type="text" id="dcc-url" readonly style="width:100%; background:transparent; border:none; color:#38bdf8; font-family:monospace;">
            <a id="dcc-link" href="#" target="_blank" style="display:inline-block; margin-top:10px; color:#34d399; font-weight:600; text-decoration:none;">Open Admin Instance ↗</a>
        </div>
    </div>
    <script>
    let vKey = "";
    document.getElementById('dcc-vbtn').onclick = async () => {
        const k = document.getElementById('dcc-key').value.trim();
        const s = document.getElementById('dcc-status');
        if(!k) { s.style.color="#f43f5e"; s.innerText = "Please enter API Key."; return; }
        s.style.color="#38bdf8"; s.innerText = "⚡ Scanning Database Registry...";
        try {
            const r = await fetch('/api/verify-control-key', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({api_key:k}) });
            const d = await r.json();
            if(d.valid) {
                vKey = k;
                s.style.color="#10b981"; s.innerText = "✔ Success! Unlocking...";
                setTimeout(() => { document.getElementById('dcc-gate').style.display='none'; document.getElementById('dcc-dash').style.display='block'; }, 600);
            } else { throw new Error(d.error); }
        } catch(e) {
            s.style.color="#f43f5e"; s.innerText = "✖ Failed: " + e.message;
            setTimeout(() => { window.location.href='/api-keys'; }, 2000);
        }
    };
    document.getElementById('dcc-genbtn').onclick = () => {
        const db = document.getElementById('dcc-dbname').value.trim() || 'my_db';
        const url = window.location.origin + '/db-admin/' + encodeURIComponent(db) + '?key=' + encodeURIComponent(vKey);
        document.getElementById('dcc-url').value = url;
        document.getElementById('dcc-link').href = url;
        document.getElementById('dcc-res').style.display = 'block';
    };
    </script>
    """)

@app.route("/db-admin/<db_slug>")
def page_user_db_admin(db_slug):
    k = request.args.get("key", "")
    return render_page(f"DB: {db_slug}", "database-control", f"""
    <div style="background:#0b1120; border:1px solid rgba(56,189,248,0.25); border-radius:12px; padding:24px;">
        <h2 style="color:#38bdf8; margin-bottom:12px;">Database Instance: {db_slug.upper()}</h2>
        <div style="font-size:0.85rem; color:#94a3b8; margin-bottom:20px;">Authenticated Key: <span style="color:#38bdf8; font-family:monospace;">{k[:14]}...</span></div>
        <div style="background:#020617; padding:16px; border-radius:8px; font-family:monospace; color:#34d399; font-size:0.85rem;">[SUCCESS] Shard online. 0 queries pending.</div>
    </div>
    """)

# ------------------------------------------------------------------------------
# CARTESIA VOICE STUDIO & PROXY
# ------------------------------------------------------------------------------
@app.route("/api/tts", methods=["POST"])
def api_cartesia_tts():
    data = request.get_json(silent=True) or {}
    text_c = data.get("text", "").strip()
    voice_id = data.get("voice_id", "a0e99841-438c-4a64-b679-ae501e7d6091").strip()
    if not text_c: return jsonify({"error": "Text is required"}), 400
    payload = {"model_id": "sonic-2", "transcript": text_c, "voice": {"mode": "id", "id": voice_id}, "output_format": {"container": "wav", "encoding": "pcm_s16le", "sample_rate": 44100}}
    headers = {"X-API-Key": "sk_car_ohzRe16X4ToST5Yz2mT4hZ", "Cartesia-Version": "2024-06-10", "Content-Type": "application/json"}
    try:
        req = urllib.request.Request("https://api.cartesia.ai/tts/bytes", data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return Response(resp.read(), mimetype="audio/wav")
    except Exception as e:
        return jsonify({"error": str(e)}), 502

@app.route("/voice-studio")
def page_voice_studio():
    return render_page("AI Voice Studio", "voice-studio", """
    <div style="max-width:860px; margin:0 auto; background:#0b1120; border:1px solid rgba(255,255,255,0.08); border-radius:14px; padding:24px;">
        <h2 style="margin-bottom:6px;">Cartesia AI Voice Studio</h2>
        <p style="color:#94a3b8; font-size:0.85rem; margin-bottom:18px;">Ultra-Realistic Sonic-2 Neural Voice Generation with 3D Spatial Audio</p>
        <textarea id="vs-text" rows="3" placeholder="Enter text to speak..." style="width:100%; box-sizing:border-box; background:#0f172a; border:1px solid rgba(255,255,255,0.12); border-radius:8px; padding:12px; color:#fff; margin-bottom:14px;"></textarea>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:16px;">
            <select id="vs-voice" style="background:#0f172a; border:1px solid rgba(255,255,255,0.12); border-radius:8px; padding:10px; color:#fff;">
                <option value="a0e99841-438c-4a64-b679-ae501e7d6091">Barbershop Guy (Male)</option>
                <option value="fb26447f-308b-471e-8b00-8e9f04284eb5">Helpful Assistant (Male)</option>
                <option value="69267136-1bdc-4103-a11a-7a0676499b66">British Narrator (Male)</option>
                <option value="79a125e8-cd45-4c13-8a67-188112f4dd22">Calm & Friendly (Female)</option>
                <option value="21b81c14-f857-4359-aa54-26de70819eb4">Storyteller (Female)</option>
                <option value="b7d50908-b17c-442d-ad8d-810c63997ed9">News Anchor (Female)</option>
            </select>
            <select id="vs-speed" style="background:#0f172a; border:1px solid rgba(255,255,255,0.12); border-radius:8px; padding:10px; color:#fff;">
                <option value="0.8">0.8x (Slow)</option>
                <option value="1.0" selected>1.0x (Normal)</option>
                <option value="1.2">1.2x (Fast)</option>
                <option value="1.5">1.5x (Speed)</option>
            </select>
        </div>
        <button id="vs-btn" style="width:100%; background:#0284c7; color:#fff; border:none; padding:12px; border-radius:8px; font-weight:700; cursor:pointer; margin-bottom:18px;">Generate Neural Speech</button>
        <div id="vs-player-box" style="display:none; background:#020617; border:1px solid rgba(56,189,248,0.25); border-radius:10px; padding:16px;">
            <audio id="vs-audio" controls style="width:100%; margin-bottom:12px;"></audio>
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <label style="font-size:0.85rem; color:#94a3b8;">🎧 3D Stereo Orbit: <input type="range" id="vs-pan" min="-1" max="1" step="0.1" value="0"></label>
                <a id="vs-dl" href="#" download="voice.wav" style="background:#059669; color:#fff; text-decoration:none; padding:8px 14px; border-radius:6px; font-size:0.85rem; font-weight:600;">Download .WAV</a>
            </div>
        </div>
    </div>
    <script>
    let aCtx = null, pNode = null;
    document.getElementById('vs-btn').onclick = async () => {
        const t = document.getElementById('vs-text').value.trim();
        if(!t) return alert('Please enter text');
        const b = document.getElementById('vs-btn');
        b.disabled = true; b.innerText = "Rendering Sonic-2...";
        try {
            const r = await fetch('/api/tts', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({text:t, voice_id:document.getElementById('vs-voice').value}) });
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
            if('speechSynthesis' in window) { const u = new SpeechSynthesisUtterance(t); window.speechSynthesis.speak(u); }
            else alert('Generation failed');
        } finally { b.disabled = false; b.innerText = "Generate Neural Speech"; }
    };
    document.getElementById('vs-pan').oninput = (e) => {
        if(!aCtx) { const A = window.AudioContext || window.webkitAudioContext; aCtx = new A(); const s = aCtx.createMediaElementSource(document.getElementById('vs-audio')); pNode = aCtx.createStereoPanner(); s.connect(pNode); pNode.connect(aCtx.destination); }
        if(pNode) pNode.pan.value = parseFloat(e.target.value);
    };
    </script>
    """)

# ------------------------------------------------------------------------------
# AKHIL NEURAL CLUSTER (NVIDIA NIM PROXY)
# ------------------------------------------------------------------------------
NVIDIA_CFG = {
    "deepseek-flash": {"m": "deepseek-ai/deepseek-v4-flash-0731", "k": "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"},
    "deepseek-pro": {"m": "deepseek-ai/deepseek-v4-pro-0813", "k": "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"},
    "nemotron-550b": {"m": "nvidia/nemotron-3-ultra-550b-a55b", "k": "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"},
    "kimi-k3": {"m": "moonshotai/kimi-k3", "k": "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"},
    "gemma-31b": {"m": "google/gemma-4-31b-it", "k": "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"}
}

@app.route("/api/nvidia-generate", methods=["POST"])
def api_nvidia_gen():
    d = request.get_json(silent=True) or {}
    model_alias = d.get("model_alias", "deepseek-flash")
    p = d.get("prompt", "").strip()
    if not p: return jsonify({"error": "Prompt required"}), 400
    cfg = NVIDIA_CFG.get(model_alias, NVIDIA_CFG["deepseek-flash"])
    headers = {"Authorization": f"Bearer {cfg['k']}", "Content-Type": "application/json"}
    body = {"model": cfg["m"], "messages": [{"role": "user", "content": p}], "max_tokens": 4096}
    try:
        req = urllib.request.Request("https://integrate.api.nvidia.com/v1/chat/completions", data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            msg = res["choices"][0]["message"]
            return jsonify({"reply": msg.get("content", ""), "reasoning": msg.get("reasoning_content") or msg.get("reasoning", "")})
    except Exception as e:
        return jsonify({"error": str(e)}), 502

@app.route("/nvidia-ai-hub")
def page_nvidia_hub():
    return render_page("Akhil Neural Studio", "nvidia-hub", """
    <div style="max-width:900px; margin:0 auto; background:#0b1120; border:1px solid rgba(255,255,255,0.08); border-radius:14px; padding:24px;">
        <h2 style="color:#76b900; margin-bottom:4px;">AKHIL NEURAL CLUSTER</h2>
        <p style="color:#94a3b8; font-size:0.85rem; margin-bottom:18px;">Private Multi-LLM GPU Inference Core (DeepSeek, Nemotron & Kimi)</p>
        <select id="nv-m" style="width:100%; box-sizing:border-box; background:#0f172a; border:1px solid rgba(255,255,255,0.12); border-radius:8px; padding:12px; color:#fff; margin-bottom:14px;">
            <option value="deepseek-flash">DeepSeek v4 Flash (Reasoning Core)</option>
            <option value="deepseek-pro">DeepSeek v4 Pro (Heavy Computational)</option>
            <option value="nemotron-550b">NVIDIA Nemotron-3 Ultra (550B Cluster)</option>
            <option value="kimi-k3">Moonshot Kimi-K3 (Deep Thinking)</option>
            <option value="gemma-31b">Google Gemma-4 31B Instruct</option>
        </select>
        <textarea id="nv-p" rows="4" placeholder="Enter query for Akhil Neural Core..." style="width:100%; box-sizing:border-box; background:#0f172a; border:1px solid rgba(255,255,255,0.12); border-radius:8px; padding:12px; color:#fff; margin-bottom:14px;"></textarea>
        <button id="nv-b" style="width:100%; background:linear-gradient(135deg, #76b900, #4c7c00); color:#fff; border:none; padding:12px; border-radius:8px; font-weight:700; cursor:pointer;">Fire Akhil Neural Core</button>
        <div id="nv-out" style="display:none; margin-top:18px; background:#020617; border:1px solid rgba(118,185,0,0.3); border-radius:10px; padding:16px;">
            <div id="nv-thought" style="display:none; font-family:monospace; font-size:0.8rem; color:#38bdf8; background:rgba(15,23,42,0.8); padding:10px; border-radius:6px; margin-bottom:12px; white-space:pre-wrap;"></div>
            <div id="nv-rep" style="font-size:0.95rem; line-height:1.6; white-space:pre-wrap;"></div>
        </div>
    </div>
    <script>
    document.getElementById('nv-b').onclick = async () => {
        const p = document.getElementById('nv-p').value.trim();
        if(!p) return alert('Please enter query');
        const b = document.getElementById('nv-b');
        b.disabled = true; b.innerText = "Routing via Akhil Cluster...";
        try {
            const r = await fetch('/api/nvidia-generate', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({model_alias:document.getElementById('nv-m').value, prompt:p}) });
            const d = await r.json();
            if(!r.ok) throw new Error(d.error);
            document.getElementById('nv-rep').innerText = d.reply || 'No text output';
            const t = document.getElementById('nv-thought');
            if(d.reasoning) { t.innerText = "🧠 Chain of Thought:\\n" + d.reasoning; t.style.display = 'block'; } else { t.style.display = 'none'; }
            document.getElementById('nv-out').style.display = 'block';
        } catch(e) { alert('Failed: ' + e.message); }
        finally { b.disabled = false; b.innerText = "Fire Akhil Neural Core"; }
    };
    </script>
    """)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
