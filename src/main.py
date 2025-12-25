from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from urllib.parse import parse_qs

PORT = 8080

TASKS = [
    {
        "task_id": "demo-1",
        "lecture_name": "Пример лекции",
        "video_url": "https://disk.yandex.ru/d/example",
        "status": "DONE",
        "created_at": "2025-12-25T12:00:00",
        "result_url": "/demo.pdf",
        "error_message": None,
    }
]

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.serve_file("html/form.html")
        elif self.path == "/tasks":
            self.serve_file("html/tasks.html")
        elif self.path == "/api/tasks":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"tasks": TASKS}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode()
            data = parse_qs(body)

            TASKS.insert(0, {
                "task_id": f"task-{len(TASKS)+1}",
                "lecture_name": data.get("lecture", [""])[0],
                "video_url": data.get("video_url", [""])[0],
                "status": "QUEUED",
                "created_at": "2025-12-25T12:30:00",
                "result_url": None,
                "error_message": None,
            })

            self.send_response(302)
            self.send_header("Location", "/tasks")
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def serve_file(self, path):
        try:
            with open(path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()

print(f"Server started at http://localhost:{PORT}")
HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
