import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
from pathlib import Path
import queue
import sqlite3
import threading

from jsonschema import Draft202012Validator

REQUEST_SCHEMA = {
    "type": "object",
    "properties": {
        "requestId": {"type": "string", "minLength": 1, "maxLength": 128},
        "target": {"type": "object"},
        "actionId": {"type": "string"},
        "actionVersion": {"type": "integer", "minimum": 1},
        "parameters": {"type": "object"},
    },
    "required": ["requestId", "target", "actionId", "actionVersion", "parameters"],
    "additionalProperties": False,
}

ACTION = {
    "id": "dealerdesk.critical-error",
    "version": 1,
    "description": "Show the DealerDesk critical application error dialog.",
    "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
}


def registration_dir(user):
    account = user.split("\\")[-1].lower()
    if not account or account in (".", "..") or any(c in account for c in '/\\:'):
        raise ValueError("Invalid Windows user")
    return Path(os.environ["PROGRAMDATA"]) / "Minicor" / "actions" / "registrations" / account


def install(user, instance, port, version):
    if not instance or len(instance) > 128 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in instance):
        raise ValueError("Invalid instance ID")
    if not version or len(version) > 128:
        raise ValueError("Installed version is required")
    if not 1024 <= port <= 65535:
        raise ValueError("Port must be between 1024 and 65535")
    directory = registration_dir(user)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "dealerdesk.json"
    entry = {"targetUser": user, "target": {"kind": "app", "appId": "dealerdesk", "instanceId": instance},
             "installedVersion": version, "actions": [ACTION], "port": port}
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(entry), encoding="utf-8")
    os.replace(temp, path)
    return path


def outcome(request_id, kind, reason=None):
    value = {"kind": kind}
    if reason:
        value["reason"] = reason
    return {"requestId": request_id, "outcome": value}


class Receiver:
    def __init__(self, root, registration):
        self.root = root
        self.registration = registration
        self.pending = queue.Queue()
        directory = Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))) / "DealerDesk" / "actions"
        directory.mkdir(parents=True, exist_ok=True)
        self.db_path = directory / (registration["target"]["instanceId"] + ".sqlite3")
        with sqlite3.connect(self.db_path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS receipts (id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, result TEXT, created INTEGER NOT NULL)")

    def execute(self, request):
        request_id = request.get("requestId") if isinstance(request, dict) else None
        try:
            Draft202012Validator(REQUEST_SCHEMA).validate(request)
            if request["target"] != self.registration["target"] or request["actionId"] != ACTION["id"] or request["actionVersion"] != ACTION["version"]:
                raise ValueError("Unknown target, action, or version")
            Draft202012Validator(ACTION["inputSchema"]).validate(request["parameters"])
        except Exception as exc:
            return outcome(request_id, "rejected", str(exc))
        fingerprint = hashlib.sha256(json.dumps(request, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        with sqlite3.connect(self.db_path, timeout=5) as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT fingerprint, result FROM receipts WHERE id = ?", (request_id,)).fetchone()
            if previous:
                if previous[0] != fingerprint:
                    return outcome(request_id, "rejected", "requestId was already used for a different request")
                return json.loads(previous[1]) if previous[1] else outcome(request_id, "unknown", "Previous attempt was interrupted")
            count = db.execute("SELECT COUNT(*) FROM receipts WHERE result IS NULL").fetchone()[0]
            if count >= 1000:
                return outcome(request_id, "rejected", "Too many unresolved requests")
            db.execute("INSERT INTO receipts VALUES (?, ?, NULL, unixepoch())", (request_id, fingerprint))
            db.execute("DELETE FROM receipts WHERE id IN (SELECT id FROM receipts WHERE result IS NOT NULL ORDER BY created DESC LIMIT -1 OFFSET 999)")
        event = threading.Event()
        result = []
        self.pending.put((request_id, event, result))
        if not event.wait(10):
            return outcome(request_id, "unknown", "Timed out waiting for the UI")
        return result[0]

    def poll(self):
        from chaos.scenarios import scenario_critical_error
        while True:
            try:
                request_id, event, result = self.pending.get_nowait()
            except queue.Empty:
                break
            try:
                scenario_critical_error(self.root, immediate=True)
                response = outcome(request_id, "completed")
            except Exception as exc:
                response = outcome(request_id, "failed", str(exc))
            with sqlite3.connect(self.db_path) as db:
                db.execute("UPDATE receipts SET result = ? WHERE id = ?", (json.dumps(response), request_id))
            result.append(response)
            event.set()
        self.root.after(100, self.poll)

    def start(self):
        receiver = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                try:
                    size = int(self.headers.get("Content-Length", "0"))
                    if self.path != "/actions" or not 0 < size <= 65536:
                        raise ValueError("Invalid request")
                    result = receiver.execute(json.loads(self.rfile.read(size)))
                    body = json.dumps(result).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except (ValueError, json.JSONDecodeError):
                    self.send_error(400)

            def log_message(self, format, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", self.registration["port"]), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.root.after(100, self.poll)
        return server


def start_installed(root):
    user = os.environ.get("USERNAME")
    if not user or "PROGRAMDATA" not in os.environ:
        return []
    servers = []
    for path in registration_dir(user).glob("dealerdesk.json"):
        try:
            registration = json.loads(path.read_text(encoding="utf-8"))
            if registration["targetUser"].split("\\")[-1].lower() != user.lower():
                continue
            if registration["target"]["appId"] != "dealerdesk":
                continue
            servers.append(Receiver(root, registration).start())
        except (OSError, ValueError, KeyError, TypeError):
            logging.exception("Cannot start action receiver for %s", path)
    return servers
