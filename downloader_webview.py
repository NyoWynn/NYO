"""
NYO — Video Downloader (pywebview edition)
Design: Stitch "Descargador Multiplataforma Moderno" design system
Build:  build_webview.bat
"""

import webview
import threading
import subprocess
import sys
import os
import base64
import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

# ── RESOURCE LOADER ──────────────────────────────────
def _res(filename):
    """Locate a resource file — works both in dev and in PyInstaller EXE."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

def _b64_img(filename):
    """Read an image file and return a base64 data-URI string."""
    path = _res(filename)
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()

# ── YT-DLP DISCOVERY ─────────────────────────────────
YTDLP_CANDIDATES = [
    # bundled alongside the EXE (PyInstaller)
    os.path.join(getattr(sys, '_MEIPASS', ''), 'yt-dlp.exe'),
    os.path.join(os.path.dirname(sys.executable), 'yt-dlp.exe'),
    # user's Python install
    r"C:\Users\ncamp\AppData\Local\Programs\Python\Python311\Scripts\yt-dlp.exe",
    r"C:\Users\ncamp\AppData\Roaming\Python\Python311\Scripts\yt-dlp.exe",
    # generic
    "yt-dlp.exe", "yt-dlp",
]

BROWSERS = ["edge", "chrome", "firefox", "brave", "opera", "chromium", "ninguno"]

FORMATS = {"mp4": "MP4", "mkv": "MKV", "webm": "WEBM", "mp3": "MP3 (audio)", "m4a": "M4A (audio)", "wav": "WAV (audio)"}
QUALITIES = {"best": "Best", "2160": "4K (2160p)", "1080": "1080p", "720": "720p", "480": "480p", "360": "360p"}

def _find_ytdlp():
    for p in YTDLP_CANDIDATES:
        if not p: continue
        try:
            r = subprocess.run([p, "--version"], capture_output=True, timeout=6)
            if r.returncode == 0:
                return p
        except Exception:
            continue
    return None

def _build_args(ytdlp, url, fmt, quality, output_dir, browser):
    args = [ytdlp, "--no-playlist", "--newline", "--no-update",
            "-o", str(Path(output_dir) / "%(title)s.%(ext)s")]
    if browser and browser != "ninguno":
        args += ["--cookies-from-browser", browser]
    is_audio = fmt in ("mp3", "m4a", "wav")
    if is_audio:
        args += ["-x", "--audio-format", fmt, "--audio-quality", "0"]
    else:
        h_map = {"2160": 2160, "1080": 1080, "720": 720, "480": 480, "360": 360}
        h = h_map.get(quality)
        if fmt == "mp4":
            f = (f"bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={h}]+bestaudio/best[height<={h}]/best"
                 if h else "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best")
            args += ["-f", f, "--merge-output-format", "mp4"]
        elif fmt == "mkv":
            args += ["-f", f"bestvideo[height<={h}]+bestaudio/best" if h else "bestvideo+bestaudio/best",
                     "--merge-output-format", "mkv"]
        else:
            args += ["-f", f"best[height<={h}]/best" if h else "best"]
    args.append(url)
    return args


# ── PYTHON ↔ JS API ───────────────────────────────────
class Api:
    def __init__(self):
        self._window   = None
        self._proc     = None
        self._out_dir  = str(Path.home() / "Downloads")

    def find_ytdlp(self):
        p = _find_ytdlp()
        return {"found": bool(p), "path": p or ""}

    def browse_folder(self):
        root = tk.Tk(); root.withdraw(); root.wm_attributes('-topmost', 1)
        folder = filedialog.askdirectory(initialdir=self._out_dir, title="Seleccionar carpeta de destino")
        root.destroy()
        if folder:
            self._out_dir = folder
        return folder or ""

    def get_output_dir(self):
        return self._out_dir

    def open_folder(self, path=""):
        target = path if path and os.path.exists(path) else self._out_dir
        if os.path.exists(target):
            os.startfile(target)

    def open_url(self, url):
        import webbrowser
        webbrowser.open(url)

    def download(self, params):
        """params = {url, format, quality, browser}"""
        url     = params.get("url", "").strip()
        fmt     = params.get("format", "mp4")
        quality = params.get("quality", "best")
        browser = params.get("browser", "edge")

        if not url.startswith("http"):
            self._js_log("ERROR: URL inválida.", "error")
            self._js_state("idle")
            return

        ytdlp = _find_ytdlp()
        if not ytdlp:
            self._js_log("ERROR: yt-dlp no encontrado.", "error")
            self._js_state("idle")
            return

        def worker():
            args = _build_args(ytdlp, url, fmt, quality, self._out_dir, browser)
            self._js_log(f"Iniciando: {url}", "info")
            cookie_error = False
            try:
                self._proc = subprocess.Popen(
                    args,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                )
                last_pct = ""
                for line in self._proc.stdout:
                    line = line.strip()
                    if not line: continue
                    if "Could not copy" in line or "cookie database" in line.lower():
                        cookie_error = True
                    if "[download]" in line and "%" in line:
                        if line != last_pct:
                            last_pct = line
                            self._js_log(line, "progress")
                    else:
                        lvl = "error" if "ERROR" in line else "info"
                        self._js_log(line, lvl)

                self._proc.wait()
                code = self._proc.returncode

                if code != 0 and cookie_error:
                    self._js_log("⚠ Cookies bloqueadas. Reintentando sin cookies...", "warn")
                    args_nc = [a for a in args if a != "--cookies-from-browser" and a not in BROWSERS]
                    self._proc = subprocess.Popen(
                        args_nc, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, encoding="utf-8", errors="replace",
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                    )
                    for line in self._proc.stdout:
                        line = line.strip()
                        if not line: continue
                        lvl = "progress" if ("[download]" in line and "%" in line) else ("error" if "ERROR" in line else "info")
                        self._js_log(line, lvl)
                    self._proc.wait()
                    code = self._proc.returncode

                if code == 0:
                    self._js_log(f"✓ Descarga completada → {self._out_dir}", "success")
                    self._js_state("done")
                    self._window.evaluate_js(f"onDone('{self._out_dir.replace(chr(92), chr(92)*2)}')")
                else:
                    self._js_log(f"✗ yt-dlp terminó con error (código {code})", "error")
                    self._js_state("idle")

            except Exception as e:
                self._js_log(f"✗ {e}", "error")
                self._js_state("idle")
            finally:
                self._proc = None

        threading.Thread(target=worker, daemon=True).start()

    def cancel(self):
        if self._proc:
            self._proc.terminate()
            self._js_log("✗ Descarga cancelada.", "warn")
            self._js_state("idle")

    # ── helpers ─────────────────────────────────────
    def _js_log(self, msg, level="info"):
        if not self._window: return
        safe = json.dumps(msg)
        self._window.evaluate_js(f"addLog({safe}, '{level}')")

    def _js_state(self, state):
        if not self._window: return
        self._window.evaluate_js(f"setState('{state}')")


# ── HTML ──────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Video Downloader</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
/* ── TOKENS (Stitch design system) ──────────────────── */
:root {
  --bg:          #0d0e14;
  --surface:     #181921;
  --s-high:      #1e1f27;
  --s-highest:   #24252e;
  --s-low:       #12131a;
  --s-lowest:    #000000;
  --primary:     #aaffdc;
  --p-container: #00fdc1;
  --p-dim:       #00edb4;
  --on-primary:  #004734;
  --tertiary:    #ff7350;
  --error:       #ff716c;
  --on-surface:  #f4f2fc;
  --on-sv:       #abaab3;
  --sec-cont:    #444559;
  --outline-v:   #47474f;
  --glow: 0 0 12px rgba(170,255,220,0.2);
}
*,*::before,*::after { box-sizing: border-box; margin: 0; padding: 0; }

html,body {
  height: 100%;
  background: var(--bg);
  color: var(--on-surface);
  font-family: 'Inter', sans-serif;
  font-size: 14px;
  overflow: hidden;
  -webkit-user-select: none;
  user-select: none;
}

/* ── TITLE BAR ──────────────────────────────────────── */
.titlebar {
  height: 40px;
  background: var(--surface);
  display: flex; align-items: center;
  padding: 0 16px;
  -webkit-app-region: drag;
  flex-shrink: 0;
  gap: 10px;
}
.titlebar-logo {
  width: 28px; height: 28px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
  -webkit-app-region: no-drag;
  box-shadow: 0 0 8px rgba(170,255,220,0.2);
}
.titlebar-title {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 13px; font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--on-surface);
  flex: 1;
}
.titlebar-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--on-sv);
  transition: background 0.3s, box-shadow 0.3s;
  -webkit-app-region: no-drag;
}
.titlebar-dot.ready { background: var(--primary); box-shadow: var(--glow); }
.titlebar-dot.busy  { background: #ffcc00; animation: blink .7s infinite; }
.titlebar-dot.error { background: var(--error); }

@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }

/* ── LAYOUT ─────────────────────────────────────────── */
.app {
  height: calc(100vh - 40px);
  overflow-y: auto;
  overflow-x: hidden;
  padding: 20px 20px 12px;
  display: flex; flex-direction: column; gap: 12px;
  scrollbar-width: thin;
  scrollbar-color: var(--s-highest) transparent;
}

/* ── SECTION LABEL ──────────────────────────────────── */
.label {
  font-size: 11px; font-weight: 600;
  letter-spacing: 0.12em; text-transform: uppercase;
  color: var(--on-sv); margin-bottom: 6px;
}

/* ── URL SECTION ─────────────────────────────────────── */
.url-wrap {
  background: var(--surface);
  border-radius: 16px;
  padding: 14px 16px;
}
.url-input-row {
  display: flex; gap: 10px; align-items: center;
  background: var(--s-lowest);
  border-radius: 10px;
  padding: 0 14px;
  transition: background .2s;
}
.url-input-row:focus-within {
  background: var(--s-high);
  box-shadow: inset 0 0 0 1px rgba(170,255,220,0.3);
}
.url-icon { color: var(--on-sv); font-size: 16px; flex-shrink: 0; }
.url-input {
  flex: 1;
  background: none; border: none; outline: none;
  color: var(--on-surface);
  font-family: 'Inter', sans-serif;
  font-size: 13px;
  padding: 12px 0;
  -webkit-user-select: text; user-select: text;
}
.url-input::placeholder { color: var(--on-sv); }

/* Platform chips */
.chips {
  display: flex; gap: 8px; flex-wrap: wrap;
  margin-top: 10px;
}
.chip {
  padding: 4px 12px;
  border-radius: 6px;
  background: var(--s-highest);
  font-size: 11px; font-weight: 600; letter-spacing: .06em;
  color: var(--on-sv);
  transition: all .2s;
}
.chip.active-yt   { background: rgba(255,0,0,.15);  color: #ff4444; }
.chip.active-tw   { background: rgba(145,70,255,.15);color: #9146ff; }
.chip.active-tt   { background: rgba(238,29,82,.15); color: #ee1d52; }
.chip.active-tx   { background: rgba(29,161,242,.15);color: #1da1f2; }
.chip.active-gen  { background: rgba(170,255,220,.1);color: var(--primary); }

/* ── OPTIONS ROW ─────────────────────────────────────── */
.options {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 10px;
}

.opt-group { display: flex; flex-direction: column; gap: 4px; }

.custom-select {
  position: relative;
}
.custom-select select {
  width: 100%;
  background: var(--s-lowest);
  color: var(--on-surface);
  border: none; outline: none;
  border-radius: 10px;
  padding: 10px 36px 10px 12px;
  font-family: 'Inter', sans-serif;
  font-size: 13px; font-weight: 500;
  appearance: none; cursor: pointer;
  transition: background .2s;
}
.custom-select select:focus { background: var(--s-high); }
.custom-select::after {
  content: '▾';
  position: absolute; right: 12px; top: 50%;
  transform: translateY(-50%);
  color: var(--on-sv); pointer-events: none;
  font-size: 12px;
}

/* ── OUTPUT FOLDER ───────────────────────────────────── */
.folder-row {
  display: flex; gap: 8px; align-items: center;
  background: var(--s-lowest);
  border-radius: 10px;
  padding: 10px 14px;
}
.folder-icon { color: var(--on-sv); flex-shrink: 0; }
.folder-path {
  flex: 1; font-size: 12px; color: var(--on-sv);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.folder-btn {
  background: var(--s-highest); border: none;
  color: var(--on-sv);
  font-family: 'Inter', sans-serif; font-size: 11px; font-weight: 600;
  letter-spacing: .06em; padding: 6px 14px;
  border-radius: 8px; cursor: pointer;
  transition: background .2s, color .2s;
}
.folder-btn:hover { background: var(--outline-v); color: var(--on-surface); }

/* ── DOWNLOAD BUTTON ─────────────────────────────────── */
.dl-btn {
  width: 100%;
  background: linear-gradient(90deg, var(--primary), var(--p-container));
  color: var(--on-primary);
  border: none; border-radius: 16px;
  font-family: 'Space Grotesk', sans-serif;
  font-size: 16px; font-weight: 700;
  letter-spacing: .06em;
  padding: 16px;
  cursor: pointer;
  transition: opacity .2s, transform .1s, box-shadow .2s;
  box-shadow: 0 0 24px rgba(0,253,193,.15);
  position: relative; overflow: hidden;
}
.dl-btn::before {
  content: '';
  position: absolute; inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,.15), transparent);
  transform: translateX(-100%);
  transition: transform .5s;
}
.dl-btn:hover::before { transform: translateX(100%); }
.dl-btn:hover { box-shadow: 0 0 36px rgba(0,253,193,.3); }
.dl-btn:active { transform: scale(.98); }
.dl-btn:disabled {
  background: var(--s-highest);
  color: var(--on-sv);
  box-shadow: none; cursor: not-allowed;
}
.dl-btn.cancel-mode {
  background: rgba(255,113,108,.15);
  color: var(--error);
  box-shadow: none;
}

/* ── LOG PANEL ───────────────────────────────────────── */
.log-wrap {
  background: var(--surface);
  border-radius: 16px;
  padding: 0;
  overflow: hidden;
  flex: 1; min-height: 0;
  display: flex; flex-direction: column;
}
.log-header {
  padding: 10px 16px;
  display: flex; align-items: center; justify-content: space-between;
}
.log-title {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 12px; font-weight: 600;
  letter-spacing: .1em; text-transform: uppercase;
  color: var(--on-sv);
}
.log-clear {
  background: none; border: none;
  font-size: 11px; color: var(--on-sv);
  cursor: pointer; padding: 2px 8px;
  border-radius: 4px;
  transition: color .15s;
}
.log-clear:hover { color: var(--on-surface); }

.log-body {
  background: var(--s-lowest);
  flex: 1; overflow-y: auto; overflow-x: hidden;
  padding: 10px 14px;
  scrollbar-width: thin;
  scrollbar-color: var(--s-highest) transparent;
  -webkit-user-select: text; user-select: text;
}
.log-line {
  font-family: 'Inter', monospace;
  font-size: 11.5px; line-height: 1.7;
  word-break: break-all;
}
.log-line.info     { color: var(--on-sv); }
.log-line.progress { color: #abaab3; }
.log-line.success  { color: var(--primary); }
.log-line.warn     { color: #ffcc00; }
.log-line.error    { color: var(--error); }

/* ── MISC ─────────────────────────────────────────────── */
@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
.spinning { display: inline-block; animation: spin 1s linear infinite; }

/* ── HERO LOGO ───────────────────────────────────────── */
.hero-logo {
  width: 64px; height: 64px;
  border-radius: 50%;
  object-fit: cover;
  box-shadow: 0 0 20px rgba(170,255,220,0.15), 0 0 40px rgba(170,255,220,0.06);
  transition: box-shadow .3s, transform .3s;
}
.hero-logo:hover {
  box-shadow: 0 0 28px rgba(170,255,220,0.3), 0 0 60px rgba(170,255,220,0.12);
  transform: scale(1.06);
}

/* ── FOOTER ──────────────────────────────────────────── */
.footer {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px 0 2px;
  flex-shrink: 0;
}
.footer-link {
  display: flex; align-items: center; gap: 6px;
  color: var(--on-sv);
  text-decoration: none;
  font-size: 11px; font-weight: 500;
  letter-spacing: .04em;
  opacity: 0.55;
  transition: opacity .2s, color .2s;
  cursor: pointer;
}
.footer-link:hover { opacity: 1; color: var(--primary); }
.gh-icon { width: 13px; height: 13px; flex-shrink: 0; }
</style>
</head>
<body>

<!-- TITLE BAR -->
<div class="titlebar">
  <img src="{{LOGO_SRC}}" class="titlebar-logo" alt="NYO" onerror="this.style.display='none'">
  <div class="titlebar-title">NYO</div>
  <div class="titlebar-dot" id="dot"></div>
</div>

<!-- APP -->
<div class="app">

  <!-- URL -->
  <div class="url-wrap">
    <div class="label">URL del Video</div>
    <div class="url-input-row">
      <span class="url-icon">⬡</span>
      <input class="url-input" id="urlInput"
             type="url" placeholder="Pega aquí el enlace de YouTube, Twitch, TikTok..."
             oninput="detectPlatform(this.value)">
    </div>
    <div class="chips" id="chips">
      <div class="chip" id="chip-yt">▶ YouTube</div>
      <div class="chip" id="chip-tw">◉ Twitch</div>
      <div class="chip" id="chip-tt">♫ TikTok</div>
      <div class="chip" id="chip-tx">✦ Twitter/X</div>
    </div>
  </div>

  <!-- OPTIONS -->
  <div>
    <div class="label">Opciones</div>
    <div class="options">
      <div class="opt-group">
        <div style="font-size:11px;color:var(--on-sv);margin-bottom:4px;">Formato</div>
        <div class="custom-select">
          <select id="fmtSelect">
            <option value="mp4">MP4 (Video)</option>
            <option value="mkv">MKV (Video)</option>
            <option value="webm">WEBM (Video)</option>
            <option value="mp3">MP3 (Audio)</option>
            <option value="m4a">M4A (Audio)</option>
            <option value="wav">WAV (Audio)</option>
          </select>
        </div>
      </div>
      <div class="opt-group">
        <div style="font-size:11px;color:var(--on-sv);margin-bottom:4px;">Calidad</div>
        <div class="custom-select">
          <select id="qualSelect">
            <option value="best">Best</option>
            <option value="2160">4K (2160p)</option>
            <option value="1080" selected>1080p</option>
            <option value="720">720p</option>
            <option value="480">480p</option>
            <option value="360">360p</option>
          </select>
        </div>
      </div>
      <div class="opt-group">
        <div style="font-size:11px;color:var(--on-sv);margin-bottom:4px;">Cookies de</div>
        <div class="custom-select">
          <select id="browserSelect">
            <option value="edge" selected>Edge</option>
            <option value="chrome">Chrome</option>
            <option value="firefox">Firefox</option>
            <option value="brave">Brave</option>
            <option value="opera">Opera</option>
            <option value="ninguno">Sin cookies</option>
          </select>
        </div>
      </div>
    </div>
  </div>

  <!-- OUTPUT -->
  <div>
    <div class="label">Destino</div>
    <div class="folder-row">
      <span class="folder-icon">📁</span>
      <span class="folder-path" id="folderPath">Cargando...</span>
      <button class="folder-btn" onclick="browseFolder()">CAMBIAR</button>
    </div>
  </div>

  <!-- DOWNLOAD BUTTON -->
  <button class="dl-btn" id="dlBtn" onclick="handleDlClick()">
    ⬇ &nbsp; DESCARGAR VIDEO
  </button>

  <!-- LOGO HERO (centered, below options) -->
  <div style="display:flex;justify-content:center;padding:4px 0 0;">
    <img src="{{LOGO_SRC}}" class="hero-logo" alt="NYO" onerror="this.style.display='none'">
  </div>

  <!-- LOG -->
  <div class="log-wrap">
    <div class="log-header">
      <span class="log-title">◈ Session Log</span>
      <button class="log-clear" onclick="clearLog()">limpiar</button>
    </div>
    <div class="log-body" id="logBody"></div>
  </div>

  <!-- FOOTER -->
  <div class="footer">
    <a class="footer-link" href="https://github.com/NyoWynn" target="_blank"
       onclick="pywebview.api.open_url('https://github.com/NyoWynn'); return false;">
      <svg class="gh-icon" viewBox="0 0 16 16" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38
                 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13
                 -.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66
                 .07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15
                 -.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27
                 .68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12
                 .51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48
                 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8
                 c0-4.42-3.58-8-8-8z"/>
      </svg>
      <span>NyoWynn</span>
    </a>
  </div>

</div>

<script>
// ── STATE ───────────────────────────────────────────
let _state = 'loading'; // loading | idle | busy | done
const dot  = document.getElementById('dot');
const dlBtn = document.getElementById('dlBtn');

function setState(s) {
  _state = s;
  dot.className = 'titlebar-dot';
  if (s === 'idle')  { dot.classList.add('ready'); dlBtn.disabled = false; dlBtn.className = 'dl-btn'; dlBtn.innerHTML = '⬇ &nbsp; DESCARGAR VIDEO'; }
  if (s === 'busy')  { dot.classList.add('busy');  dlBtn.disabled = false; dlBtn.className = 'dl-btn cancel-mode'; dlBtn.innerHTML = '✕ &nbsp; CANCELAR'; }
  if (s === 'done')  { dot.classList.add('ready'); dlBtn.disabled = false; dlBtn.className = 'dl-btn'; dlBtn.innerHTML = '⬇ &nbsp; DESCARGAR OTRO'; }
  if (s === 'loading'){ dot.className = 'titlebar-dot'; dlBtn.disabled = true; }
}

// ── PLATFORM DETECTION ──────────────────────────────
const chips = {
  yt: document.getElementById('chip-yt'),
  tw: document.getElementById('chip-tw'),
  tt: document.getElementById('chip-tt'),
  tx: document.getElementById('chip-tx'),
};
function detectPlatform(url) {
  Object.values(chips).forEach(c => c.className = 'chip');
  const u = url.toLowerCase();
  if (u.includes('youtube.com') || u.includes('youtu.be')) chips.yt.className = 'chip active-yt';
  else if (u.includes('twitch.tv'))  chips.tw.className = 'chip active-tw';
  else if (u.includes('tiktok.com')) chips.tt.className = 'chip active-tt';
  else if (u.includes('twitter.com') || u.includes('x.com')) chips.tx.className = 'chip active-tx';
  else if (url.startsWith('http'))   Object.values(chips).forEach(c => c.className = 'chip active-gen');
}

// ── FORMAT → QUALITY sync ──────────────────────────
document.getElementById('fmtSelect').addEventListener('change', function() {
  const q = document.getElementById('qualSelect');
  const isAudio = ['mp3','m4a','wav'].includes(this.value);
  q.disabled = isAudio;
  if (isAudio) { q.value = 'best'; }
});

// ── FOLDER ──────────────────────────────────────────
async function browseFolder() {
  const folder = await pywebview.api.browse_folder();
  if (folder) document.getElementById('folderPath').textContent = folder;
}

function onDone(folder) {
  // auto-open folder
  pywebview.api.open_folder(folder);
}

// ── DOWNLOAD ────────────────────────────────────────
function handleDlClick() {
  if (_state === 'busy') {
    pywebview.api.cancel();
    return;
  }
  const url     = document.getElementById('urlInput').value.trim();
  const fmt     = document.getElementById('fmtSelect').value;
  const quality = document.getElementById('qualSelect').value;
  const browser = document.getElementById('browserSelect').value;

  if (!url) { addLog('Ingresa una URL primero.', 'warn'); return; }

  setState('busy');
  pywebview.api.download({ url, format: fmt, quality, browser });
}

// ── LOG ─────────────────────────────────────────────
function addLog(msg, level) {
  const body = document.getElementById('logBody');
  const line = document.createElement('div');
  line.className = `log-line ${level || 'info'}`;
  line.textContent = msg;
  body.appendChild(line);
  body.scrollTop = body.scrollHeight;
}

function clearLog() {
  document.getElementById('logBody').innerHTML = '';
}

// ── INIT ────────────────────────────────────────────
async function init() {
  await new Promise(r => window.addEventListener('pywebviewready', r, { once: true }));

  const dir = await pywebview.api.get_output_dir();
  document.getElementById('folderPath').textContent = dir;

  addLog('Buscando yt-dlp...', 'info');
  const result = await pywebview.api.find_ytdlp();
  if (result.found) {
    addLog('✓ yt-dlp encontrado: ' + result.path, 'success');
    setState('idle');
  } else {
    addLog('✗ yt-dlp no encontrado. Instala con: pip install yt-dlp', 'error');
    setState('idle');
  }
}
init();
</script>
</body>
</html>"""


# ── MAIN ──────────────────────────────────────────────
def main():
    api = Api()

    # Inject logo at runtime (works in dev + EXE)
    logo_src = _b64_img("nyo_logo_icon.png")
    html = HTML.replace("{{LOGO_SRC}}", logo_src)

    window = webview.create_window(
        title           = "NYO",
        html            = html,
        js_api          = api,
        width           = 520,
        height          = 740,
        resizable       = False,
        background_color= "#0d0e14",
        frameless       = False,
        on_top          = False,
        min_size        = (400, 500),
    )
    api._window = window
    webview.start(debug=False, private_mode=False)


if __name__ == "__main__":
    main()
