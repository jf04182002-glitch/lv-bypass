#!/usr/bin/env python3
# language: Python 3.10+, file: app.py, target: any
# Local web UI for Linkvertise bypass – direct publisher API + public resolvers.

from flask import Flask, request, jsonify, render_template_string
import base64
import json
import random
import re
import time
from typing import Optional
from urllib.parse import unquote

import requests

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Bypass engine
# ---------------------------------------------------------------------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:129.0) Gecko/20100101 Firefox/129.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36",
]

PUBLISHER = "https://publisher.linkvertise.com"
BYPASS_VIP = "https://api.bypass.vip/bypass"

def clean_url(url: str) -> str:
    url = url.strip()
    url = url.replace("%3D", "=").replace("&o=sharing", "").replace("?o=sharing", "")
    url = url.replace("dynamic?r=", "dynamic/?r=")
    return url

def extract_path(url: str) -> Optional[str]:
    m = re.search(r"[?&]r=([A-Za-z0-9+/=%]+)", url)
    if m:
        try:
            decoded = base64.b64decode(unquote(m.group(1))).decode("utf-8", errors="ignore")
            if decoded.startswith("http"):
                return decoded
        except Exception:
            pass
    m = re.search(r"/(\d+/[^/?#]+)", url)
    return f"/{m.group(1)}" if m else None

def random_headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://linkvertise.com",
        "Referer": "https://linkvertise.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
    }

def sleep_jitter(min_s: float = 0.3, max_s: float = 1.0):
    time.sleep(random.uniform(min_s, max_s))

def direct_bypass(url: str, proxies: Optional[dict] = None) -> Optional[str]:
    path = extract_path(url)
    if not path:
        return None
    if path.startswith("http"):
        return path

    session = requests.Session()
    session.headers.update(random_headers())
    if proxies:
        session.proxies.update(proxies)

    for p in ("/captcha", "/countdown_impression?trafficOrigin=network",
              "/todo_impression?mobile=true&trafficOrigin=network"):
        try:
            session.get(f"{PUBLISHER}/api/v1/redirect/link{path}{p}", timeout=10)
            sleep_jitter(0.15, 0.4)
        except Exception:
            pass

    try:
        r = session.get(f"{PUBLISHER}/api/v1/redirect/link/static{path}", timeout=12)
        r.raise_for_status()
        data = r.json()
        link = data["data"]["link"]
        link_id = link["id"]
        target_type = "target" if link.get("target_type") == "URL" else "paste"
    except Exception:
        return None

    user_token = None
    try:
        acc = session.get(f"{PUBLISHER}/api/v1/account", timeout=8).json()
        user_token = acc.get("user_token")
    except Exception:
        pass

    serial = {
        "timestamp": int(time.time() * 1000),
        "random": "6548307",
        "link_id": link_id,
    }
    payload = {"serial": base64.b64encode(json.dumps(serial).encode()).decode()}

    endpoint = f"{PUBLISHER}/api/v1/redirect/link{path}/{target_type}"
    if user_token:
        endpoint += f"?X-Linkvertise-UT={user_token}"

    try:
        r = session.post(endpoint, json=payload, timeout=12)
        r.raise_for_status()
        result = r.json()["data"]
        return result.get("target") or result.get("paste")
    except Exception:
        return None

def vip_bypass(url: str, proxies: Optional[dict] = None) -> Optional[str]:
    try:
        r = requests.get(
            BYPASS_VIP,
            params={"url": url},
            headers=random_headers(),
            proxies=proxies,
            timeout=18,
        )
        data = r.json()
        if data.get("status") == "success":
            return data.get("result")
    except Exception:
        pass
    return None

def bypass(url: str, proxy: Optional[str] = None) -> Optional[str]:
    url = clean_url(url)
    if not url:
        return None
    proxies = {"http": proxy, "https": proxy} if proxy else None

    result = direct_bypass(url, proxies)
    if result:
        return result.strip()

    sleep_jitter(0.6, 1.2)
    result = vip_bypass(url, proxies)
    return result.strip() if result else None

# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------
HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Linkvertise Bypass</title>
<style>
  :root {
    --bg: #0f1115;
    --card: #1a1d24;
    --border: #2a2e38;
    --text: #e6e8ee;
    --muted: #8b90a0;
    --accent: #5b8def;
    --ok: #3ecf8e;
    --err: #f07178;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: "Segoe UI", system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1.5rem;
  }
  .card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 2rem;
    width: 100%;
    max-width: 560px;
    box-shadow: 0 12px 40px rgba(0,0,0,.4);
  }
  h1 {
    font-size: 1.35rem;
    font-weight: 600;
    margin-bottom: .35rem;
  }
  .sub {
    color: var(--muted);
    font-size: .85rem;
    margin-bottom: 1.5rem;
  }
  label {
    display: block;
    font-size: .8rem;
    color: var(--muted);
    margin-bottom: .4rem;
  }
  input[type="url"], input[type="text"], textarea {
    width: 100%;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: .7rem .9rem;
    color: var(--text);
    font-size: .95rem;
    outline: none;
    transition: border .15s;
  }
  input:focus, textarea:focus { border-color: var(--accent); }
  textarea { resize: vertical; min-height: 90px; font-family: inherit; }
  .row { margin-bottom: 1rem; }
  .opts {
    display: flex;
    gap: .75rem;
    margin-bottom: 1.25rem;
  }
  .opts input { flex: 1; }
  button {
    width: 100%;
    background: var(--accent);
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: .75rem;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: opacity .15s;
  }
  button:hover { opacity: .9; }
  button:disabled { opacity: .5; cursor: not-allowed; }
  .result {
    margin-top: 1.25rem;
    padding: 1rem;
    border-radius: 8px;
    background: var(--bg);
    border: 1px solid var(--border);
    word-break: break-all;
    display: none;
  }
  .result.show { display: block; }
  .result.ok { border-color: var(--ok); }
  .result.err { border-color: var(--err); }
  .result a { color: var(--accent); }
  .copy {
    margin-top: .6rem;
    font-size: .8rem;
    color: var(--muted);
    cursor: pointer;
    user-select: none;
  }
  .copy:hover { color: var(--text); }
  .status { font-size: .8rem; color: var(--muted); margin-top: .5rem; min-height: 1.2em; }
</style>
</head>
<body>
  <div class="card">
    <h1>Linkvertise Bypass</h1>
    <p class="sub">direct API first · public resolver fallback · local only</p>

    <div class="row">
      <label>Linkvertise URL(s) — one per line</label>
      <textarea id="urls" placeholder="https://linkvertise.com/123456/example&#10;https://linkvertise.com/..."></textarea>
    </div>

    <div class="opts">
      <div style="flex:1">
        <label>Proxy (optional)</label>
        <input type="text" id="proxy" placeholder="socks5://127.0.0.1:9050">
      </div>
    </div>

    <button id="go">Bypass</button>
    <div class="status" id="status"></div>
    <div class="result" id="result"></div>
  </div>

<script>
const go = document.getElementById('go');
const urlsEl = document.getElementById('urls');
const proxyEl = document.getElementById('proxy');
const status = document.getElementById('status');
const result = document.getElementById('result');

go.onclick = async () => {
  const raw = urlsEl.value.trim();
  if (!raw) return;
  const lines = raw.split(/\\r?\\n/).map(l => l.trim()).filter(Boolean);
  go.disabled = true;
  result.className = 'result';
  result.innerHTML = '';
  status.textContent = 'working…';

  const out = [];
  for (let i = 0; i < lines.length; i++) {
    status.textContent = `[${i+1}/${lines.length}] resolving…`;
    try {
      const res = await fetch('/bypass', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ url: lines[i], proxy: proxyEl.value.trim() || null })
      });
      const data = await res.json();
      if (data.success) {
        out.push(`<div><a href="${data.result}" target="_blank" rel="noopener">${data.result}</a></div>`);
      } else {
        out.push(`<div style="color:var(--err)">${lines[i].slice(0,60)}… → ${data.error || 'failed'}</div>`);
      }
    } catch (e) {
      out.push(`<div style="color:var(--err)">${lines[i].slice(0,60)}… → network error</div>`);
    }
  }

  result.innerHTML = out.join('') + '<div class="copy" onclick="navigator.clipboard.writeText(result.innerText)">click to copy all</div>';
  result.classList.add('show', out.some(x => x.includes('href')) ? 'ok' : 'err');
  status.textContent = 'done';
  go.disabled = false;
};
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/bypass", methods=["POST"])
def api_bypass():
    data = request.get_json(force=True, silent=True) or {}
    url = data.get("url", "").strip()
    proxy = data.get("proxy") or None
    if not url:
        return jsonify(success=False, error="no url"), 400
    try:
        dest = bypass(url, proxy)
        if dest:
            return jsonify(success=True, result=dest)
        return jsonify(success=False, error="could not resolve")
    except Exception as e:
        return jsonify(success=False, error=str(e)[:120]), 500

if __name__ == "__main__":
    print("→ http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
