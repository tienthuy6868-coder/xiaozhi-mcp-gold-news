import os
import sys
import time
import threading
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"ok","service":"xiaozhi-mcp-vn"}')

    def log_message(self, format, *args):
        # Suppress noisy HTTP health-check access logs
        return


def start_health_server():
    port = int(os.environ.get("PORT", "8000"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"[CLOUD] Health server listening on 0.0.0.0:{port}", flush=True)
    server.serve_forever()


def main():
    if not os.environ.get("MCP_ENDPOINT"):
        print("[CLOUD] ERROR: MCP_ENDPOINT environment variable is not set!", file=sys.stderr, flush=True)
        sys.exit(1)

    if not os.environ.get("MCP_CONFIG") and os.path.exists("mcp_config.cloud.json"):
        os.environ["MCP_CONFIG"] = "mcp_config.cloud.json"

    t = threading.Thread(target=start_health_server, daemon=True)
    t.start()

    while True:
        print("[CLOUD] Starting mcp_pipe.py ...", flush=True)
        proc = subprocess.Popen([sys.executable, "mcp_pipe.py"])
        code = proc.wait()
        print(f"[CLOUD] mcp_pipe.py exited with code {code}, restarting in 5s...", flush=True)
        time.sleep(5)


if __name__ == "__main__":
    main()
