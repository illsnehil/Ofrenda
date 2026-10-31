#!/usr/bin/env python3
"""Local-only backend: serves the page, proxies Ollama, transcribes audio with faster-whisper."""
import json, os, tempfile, threading, urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
if not OLLAMA.startswith("http"): OLLAMA = "http://" + OLLAMA
MODEL = os.environ.get("OFRENDA_MODEL", "qwen2.5:7b")
WHISPER = os.environ.get("OFRENDA_WHISPER", "small")
PORT = int(os.environ.get("PORT", "8765"))
PAGE = (Path(__file__).parent / "static" / "index.html").read_bytes()
_w, _lock = None, threading.Lock()

def whisper():
    global _w
    with _lock:
        if _w is None:
            from faster_whisper import WhisperModel
            _w = WhisperModel(WHISPER, compute_type="int8")
    return _w

def has_whisper():
    try: import faster_whisper; return True
    except ImportError: return False

class H(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def _body(self):
        return self.rfile.read(int(self.headers.get("Content-Length", 0)))

    def do_GET(self):
        if self.path == "/api/status":
            s = {"ollama": False, "model_ready": False, "model": MODEL, "whisper": has_whisper()}
            try:
                tags = json.load(urllib.request.urlopen(OLLAMA + "/api/tags", timeout=2))
                s["ollama"] = True
                names = {m["name"] for m in tags.get("models", [])}
                s["model_ready"] = MODEL in names or MODEL + ":latest" in names
            except Exception: pass
            return self._json(s)
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(PAGE))); self.end_headers(); self.wfile.write(PAGE)

    def do_POST(self):
        data = self._body()
        if self.path == "/api/chat":
            req = json.loads(data)
            payload = json.dumps({"model": MODEL, "messages": req["messages"], "stream": True,
                                  "options": {"temperature": req.get("temperature", 0.7)}}).encode()
            try:
                r = urllib.request.urlopen(urllib.request.Request(
                    OLLAMA + "/api/chat", payload, {"Content-Type": "application/json"}))
            except Exception as e:
                return self._json({"error": f"Can't reach Ollama ({e}). Is it running?"}, 502)
            self.send_response(200); self.send_header("Content-Type", "application/x-ndjson"); self.end_headers()
            for line in r: self.wfile.write(line); self.wfile.flush()
        elif self.path == "/api/transcribe":
            ct = self.headers.get("Content-Type", "")
            ext = ".ogg" if "ogg" in ct else ".mp4" if "mp4" in ct else ".wav" if "wav" in ct else ".webm"
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f: f.write(data); p = f.name
            try:
                segs, _ = whisper().transcribe(p, vad_filter=True)
                self._json({"text": " ".join(s.text.strip() for s in segs)})
            except Exception as e:
                self._json({"error": str(e)}, 500)
            finally: os.unlink(p)
        else: self._json({"error": "not found"}, 404)

    def log_message(self, *a): pass

if __name__ == "__main__":
    print(f"Ofrenda running at http://127.0.0.1:{PORT}  (model: {MODEL})")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
