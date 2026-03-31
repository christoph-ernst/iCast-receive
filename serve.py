"""
Static file server with a POST /config endpoint for saving config.json.
Replaces: python3 -m http.server 8000
Run with: python3 serve.py
"""
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json

ALLOWED_CONFIG_KEYS = {"home_team_name", "guest_team_name", "home_accent", "away_accent", "delay_tenths"}

class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/config":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                int_keys = {"delay_tenths"}
                filtered = {
                    k: (int(v) if k in int_keys else str(v))
                    for k, v in data.items() if k in ALLOWED_CONFIG_KEYS
                }
                with open("config.json", "w", encoding="utf-8") as f:
                    json.dump(filtered, f, indent=2, ensure_ascii=False)
                self._respond(200, {"ok": True})
            except Exception as e:
                self._respond(400, {"error": str(e)})
        else:
            self.send_response(404)
            self.end_headers()

    def _respond(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(fmt % args)

if __name__ == "__main__":
    server = HTTPServer(("", 8000), Handler)
    print("Serving on http://localhost:8000")
    print("Config page: http://localhost:8000/config.html")
    server.serve_forever()
