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
        if self.path == "/api/examples":
            return self._json(L.EXAMPLES)
        name = FILES.get(self.path)
        if not name:
            return self._send(b"Not found", "text/plain", 404)
        with open(os.path.join(ROOT, name), "rb") as f:
            self._send(f.read(), TYPES[os.path.splitext(name)[1]])

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/api/build":
            self._json(L.build(data["A"], data["B"], data["op"]))
        elif self.path == "/api/run":
            self._json(L.run(data["machine"], data["text"]))
        else:
            self._send(b"Not found", "text/plain", 404)

    def log_message(self, *args):  # keep the console quiet
        pass


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    print("Simulator running at http://127.0.0.1:8000  (Ctrl+C to stop)")
    webbrowser.open("http://127.0.0.1:8000")
    server.serve_forever()
