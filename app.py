"""app.py — tiny local web server (standard library only). Run:  python app.py
The browser page only draws things; every DFA operation is done by dfa_logic.py."""
import json, os, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import dfa_logic as L

ROOT = os.path.dirname(os.path.abspath(__file__))
FILES = {"/": "index.html", "/index.html": "index.html", "/style.css": "style.css",
         "/graph.js": "graph.js", "/script.js": "script.js"}
TYPES = {".html": "text/html", ".css": "text/css", ".js": "text/javascript"}


class Handler(BaseHTTPRequestHandler):
    def _send(self, body, ctype, code=200):
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj):
        self._send(json.dumps(obj).encode(), "application/json")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/examples":
            return self._json(L.EXAMPLES)
        name = FILES.get(path)
        if not name:
            return self._send(b"Not found", "text/plain", 404)
        with open(os.path.join(ROOT, name), "rb") as f:
            self._send(f.read(), TYPES[os.path.splitext(name)[1]])

    def do_POST(self):
        try:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.path == "/api/build":
                return self._json(L.build(data["A"], data["B"], data["op"]))
            if self.path == "/api/run":
                return self._json(L.run(data["machine"], data["text"]))
        except Exception as e:  # malformed request: answer with JSON instead of dropping the connection
            return self._json({"errors": [f"Server error: {e!r}"], "error": f"Server error: {e!r}"})
        self._send(b"Not found", "text/plain", 404)

    def log_message(self, *args):  # keep the console quiet
        pass


if __name__ == "__main__":
    for port in range(8000, 8010):  # use the next free port if 8000 is taken
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            continue
    else:
        raise SystemExit("Ports 8000-8009 are all in use. Close another server and retry.")
    url = f"http://127.0.0.1:{port}"
    print(f"Simulator running at {url}  (Ctrl+C to stop)")
    webbrowser.open(url)
    server.serve_forever()
