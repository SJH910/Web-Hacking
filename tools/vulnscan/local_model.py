"""Serve the team's existing Chapter 7 model over loopback HTTP."""
import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

MODEL = "local-gpt2"


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        self.request.settimeout(5)
        super().setup()

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            return self.send_json(404, {"error": {"message": "Unknown endpoint"}})
        try:
            size = int(self.headers.get("Content-Length", 0))
            if not 0 < size <= 8192:
                raise ValueError("Request body must be between 1 and 8192 bytes")
            request = json.loads(self.rfile.read(size))
            if not isinstance(request, dict) or request.get("model") != MODEL:
                raise ValueError("Expected model local-gpt2")
            if set(request) - {"model", "messages", "max_tokens"}:
                raise ValueError("Unsupported request fields")
            messages = request.get("messages")
            if (not isinstance(messages, list) or len(messages) != 1
                    or not isinstance(messages[0], dict) or messages[0].get("role") != "user"
                    or not isinstance(messages[0].get("content"), str)
                    or not messages[0]["content"].strip()):
                raise ValueError("Expected one nonempty user message")
            limit = request.get("max_tokens", 64)
            if type(limit) is not int or not 1 <= limit <= 96:
                raise ValueError("max_tokens must be between 1 and 96")
            model = self.server.model
            ids = model.encode_prompt(messages[0]["content"])
            if len(ids) + limit > model.context_length:
                raise ValueError("Prompt and response exceed the model context")
        except ValueError as exc:
            return self.send_json(400, {"error": {"message": str(exc)}})
        try:
            answer = model.reply(ids, limit).strip()
            if not answer:
                raise ValueError("Empty model output")
        except (RuntimeError, ValueError):
            return self.send_json(500, {"error": {"message": "Model generation failed"}})
        self.send_json(200, {"model": MODEL, "choices": [
            {"index": 0, "message": {"role": "assistant", "content": answer}}
        ]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8910)
    args = parser.parse_args()
    project = args.model_dir.resolve()
    if not (project / "generate.py").is_file():
        parser.error("--model-dir must point to the llm-from-scratch project")
    sys.path.insert(0, str(project))
    from generate import InstructionModel

    with HTTPServer(("127.0.0.1", args.port), Handler) as server:
        server.model = InstructionModel()
        print(f"Local model ready at http://127.0.0.1:{args.port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
