"""
Simple HTTP server for the minions visualizer

Serves:
- /           -> minions.html
- /api/state  -> visualizer_state.json (real-time state)

Usage:
    python serve_visualizer.py [port]
    Default port: 8765
"""

import http.server
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse


class VisualizerHandler(http.server.BaseHTTPRequestHandler):
    """Custom handler for visualizer"""

    visualizer_dir = Path(__file__).parent
    context_dir = visualizer_dir.parent / "context"

    def do_GET(self):
        """Handle GET requests"""
        parsed = urlparse(self.path)
        path = parsed.path

        # API state endpoint
        if path == "/api/state":
            self.send_state()
            return

        # API outputs endpoint - get node outputs from workflow result
        if path == "/api/outputs":
            self.send_outputs()
            return

        # Root -> serve minions.html
        if path == "/" or path == "":
            path = "/minions.html"

        # Serve static files from visualizer directory
        file_path = self.visualizer_dir / path.lstrip("/")
        if file_path.exists() and file_path.is_file():
            self.send_file(file_path)
        else:
            self.send_error(404, "File not found")

    def send_file(self, file_path):
        """Send a static file"""
        content_types = {
            ".html": "text/html",
            ".js": "application/javascript",
            ".css": "text/css",
            ".json": "application/json",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".svg": "image/svg+xml"
        }
        ext = file_path.suffix.lower()
        content_type = content_types.get(ext, "application/octet-stream")

        with open(file_path, "rb") as f:
            content = f.read()

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", len(content))
        self.end_headers()
        self.wfile.write(content)

    def send_state(self):
        """Send current visualizer state as JSON"""
        state_file = self.context_dir / "visualizer_state.json"

        try:
            if state_file.exists():
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
            else:
                state = {
                    "status": "waiting",
                    "message": "Waiting for workflow to start...",
                    "agents": {},
                    "chat_log": [],
                    "progress": 0
                }

            content = json.dumps(state).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)

        except Exception as e:
            error = json.dumps({"error": str(e)}).encode()
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(error))
            self.end_headers()
            self.wfile.write(error)

    def send_outputs(self):
        """Send node outputs from the most recent workflow result file"""
        try:
            # First get the ticker from visualizer state
            state_file = self.context_dir / "visualizer_state.json"
            ticker = None
            if state_file.exists():
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    ticker = state.get("ticker", "").replace(" ", "_")

            # Find the workflow result file
            outputs = {}
            if ticker:
                # Try different filename patterns
                patterns = [
                    f"{ticker}_workflow_result.json",
                    f"{ticker.replace('_', ' ')}_workflow_result.json",
                ]

                result_file = None
                for pattern in patterns:
                    candidate = self.context_dir / pattern
                    if candidate.exists():
                        result_file = candidate
                        break

                # Also check for trace file if main file not found
                if not result_file:
                    trace_file = self.context_dir / f"trace_{ticker}_workflow_result.json"
                    if trace_file.exists():
                        result_file = trace_file

                if result_file and result_file.exists():
                    with open(result_file, 'r', encoding='utf-8') as f:
                        result = json.load(f)
                        node_outputs = result.get("node_outputs", {})

                        # Extract content from each node's messages
                        for node_id, messages in node_outputs.items():
                            if messages and len(messages) > 0:
                                last_msg = messages[-1]
                                content = last_msg.get("content", "")
                                # Truncate for display (keep first 5000 chars)
                                outputs[node_id] = {
                                    "content": content[:5000] if len(content) > 5000 else content,
                                    "full_length": len(content),
                                    "provider": last_msg.get("metadata", {}).get("provider", "unknown"),
                                    "model": last_msg.get("metadata", {}).get("model", "unknown"),
                                    "timestamp": last_msg.get("timestamp", "")
                                }

            content = json.dumps(outputs).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)

        except Exception as e:
            error = json.dumps({"error": str(e), "outputs": {}}).encode()
            self.send_response(200)  # Still return 200 with empty outputs
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", len(error))
            self.end_headers()
            self.wfile.write(error)

    def log_message(self, format, *args):
        """Suppress logging for cleaner output"""
        pass


def run_server(port: int = 8765):
    """Run the visualizer server"""
    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, VisualizerHandler)

    print(f"""
    =============================================
    MINIONS VISUALIZER SERVER
    =============================================
    URL: http://localhost:{port}

    Endpoints:
      /           -> minions.html (visualizer)
      /api/state  -> Real-time workflow state

    Press Ctrl+C to stop
    =============================================
    """)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        httpd.shutdown()


if __name__ == "__main__":
    port = 8765
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port: {sys.argv[1]}, using default 8765")

    run_server(port)