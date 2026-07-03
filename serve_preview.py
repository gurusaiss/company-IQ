#!/usr/bin/env python3
"""Minimal static file server for frontend preview. Reads PORT from env."""
import os
import socketserver
import http.server

PORT = int(os.environ.get("PORT", 8080))
DIRECTORY = os.path.join(os.path.dirname(__file__), "frontend")

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    def log_message(self, *args):
        pass

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Serving frontend on port {PORT}")
    httpd.serve_forever()
