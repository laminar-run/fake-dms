"""Bounded loopback delivery, durable receipts, and Tk-thread effect creation."""
import ctypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import queue
import re
import sqlite3
import threading
import uuid

from .config import user


def session_id():
    if os.name != "nt":
        return os.getsid(0)
    value = ctypes.c_ulong()
    if not ctypes.windll.kernel32.ProcessIdToSessionId(os.getpid(), ctypes.byref(value)):
        raise OSError("Cannot resolve OS session")
    return value.value


def validate(data, entry):
    keys = {"version", "requestId", "injectionId", "actionId", "parameters", "targetUser", "sessionId", "appInstanceId"}
    if not isinstance(data, dict) or set(data) != keys or type(data["version"]) is not int or data["version"] != 1:
        raise ValueError("invalid_envelope")
    for key in ("requestId", "injectionId", "appInstanceId"):
        if not isinstance(data[key], str) or not re.fullmatch(r"[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", data[key]):
            raise ValueError("invalid_uuid")
        try:
            data[key] = str(uuid.UUID(data[key]))
        except ValueError as error:
            raise ValueError("invalid_uuid") from error
    if data["targetUser"] != user() or type(data["sessionId"]) is not int or data["sessionId"] != session_id() or data["appInstanceId"] != entry["instanceId"]:
        raise ValueError("target_mismatch")
    if not isinstance(data["actionId"], str) or not isinstance(data["parameters"], dict):
        raise ValueError("invalid_action")
    if data["actionId"] == "dealerdesk.critical-error" and data["parameters"] != {}:
        raise ValueError("invalid_parameters")
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


class Work:
    def __init__(self, data, fingerprint):
        self.data = data
        self.fingerprint = fingerprint
        self.state = "queued"
        self.event = threading.Event()
        self.result = None


class BoundedServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False

    def __init__(self, *args):
        self.capacity = threading.BoundedSemaphore(16)
        super().__init__(*args)

    def process_request(self, request, address):
        if not self.capacity.acquire(blocking=False):
            try:
                request.settimeout(2)
                request.sendall(b"HTTP/1.1 503 Service Unavailable\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
            except OSError:
                pass
            finally:
                self.shutdown_request(request)
            return
        try:
            super().process_request(request, address)
        except Exception:
            self.capacity.release()
            raise

    def process_request_thread(self, request, address):
        try:
            request.settimeout(2)
            super().process_request_thread(request, address)
        finally:
            self.capacity.release()


class Receiver:
    def __init__(self, root, entry, database):
        self.root = root
        self.entry = entry
        self.database = str(database)
        self.lock = threading.RLock()
        self.pending = {}
        self.queue = queue.Queue(maxsize=16)
        self.active = None
        self.stopped = False
        with self._db() as db:
            db.execute("CREATE TABLE IF NOT EXISTS receipts (request_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, result TEXT)")
        self.server = BoundedServer(("127.0.0.1", entry["port"]), self._handler())
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def _db(self):
        return sqlite3.connect(self.database, timeout=2)

    def start(self):
        self.thread.start()
        self.root.after(20, self.poll)

    def stop(self):
        with self.lock:
            self.stopped = True
            for work in list(self.pending.values()):
                if work.state == "queued":
                    self._finish(work, "failed", "app_stopping")
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def _reply(self, data, status, code=None, injection=None):
        result = {"requestId": data["requestId"], "injectionId": injection or data["injectionId"], "status": status}
        if code:
            result["code"] = code
        return result

    def _finish(self, work, status, code=None, injection=None):
        result = self._reply(work.data, status, code, injection)
        try:
            with self._db() as db:
                db.execute("UPDATE receipts SET result=? WHERE request_id=?", (json.dumps(result), work.data["requestId"]))
        except sqlite3.Error:
            result = self._reply(work.data, "unknown", "receipt_unavailable")
        work.result = result
        work.state = "done"
        self.pending.pop(work.data["requestId"], None)
        work.event.set()

    def dispatch(self, data):
        fingerprint = validate(data, self.entry)
        with self.lock:
            if self.stopped:
                return self._reply(data, "failed", "app_stopping")
            fresh = False
            with self._db() as db:
                row = db.execute("SELECT fingerprint,result FROM receipts WHERE request_id=?", (data["requestId"],)).fetchone()
                if row:
                    if row[0] != fingerprint:
                        raise ValueError("request_conflict")
                    if row[1]:
                        return json.loads(row[1])
                    work = self.pending.get(data["requestId"])
                    if work is None:
                        return self._reply(data, "unknown", "unfinished_receipt")
                else:
                    if self.queue.full():
                        return self._reply(data, "failed", "app_busy")
                    db.execute("INSERT INTO receipts VALUES (?,?,NULL)", (data["requestId"], fingerprint))
                    work = Work(data, fingerprint)
                    fresh = True
            if fresh:
                self.pending[data["requestId"]] = work
                self.queue.put_nowait(work)
        if work.event.wait(1.5):
            return work.result
        with self.lock:
            if work.state == "queued":
                self._finish(work, "failed", "ui_unresponsive")
                return work.result
            if work.state == "done":
                return work.result
            return self._reply(data, "unknown", "request_in_progress")

    def poll(self):
        for _ in range(8):
            try:
                work = self.queue.get_nowait()
            except queue.Empty:
                break
            with self.lock:
                if work.state != "queued":
                    continue
                work.state = "started"
            try:
                from chaos.scenarios import scenario_critical_error
                if work.data["actionId"] != "dealerdesk.critical-error":
                    with self.lock:
                        self._finish(work, "failed", "unsupported_action")
                elif self.active is not None and self.active[0].winfo_exists():
                    with self.lock:
                        self._finish(work, "already_active", injection=self.active[1])
                else:
                    scenario_critical_error(self.root, on_created=lambda win, item=work: self._created(item, win), schedule=False)
            except Exception:
                with self.lock:
                    self._finish(work, "unknown", "effect_uncertain")
        if not self.stopped:
            self.root.after(20, self.poll)

    def _created(self, work, window):
        with self.lock:
            self.active = (window, work.data["injectionId"])
            self._finish(work, "completed")

    def _handler(self):
        receiver = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path != "/action":
                    return self.send(404, {"code": "not_found"})
                try:
                    size = self.headers.get("Content-Length", "")
                    if not size.isascii() or not size.isdecimal() or not 0 < int(size) <= 8192:
                        return self.send(400, {"code": "invalid_body"})
                    try:
                        data = json.loads(self.rfile.read(int(size)))
                        result = receiver.dispatch(data)
                    except (ValueError, UnicodeError, json.JSONDecodeError) as error:
                        code = str(error) if isinstance(error, ValueError) else "invalid_body"
                        return self.send(409 if code == "request_conflict" else 400, {"code": code})
                    except sqlite3.Error:
                        return self.send(503, {"code": "receipt_unavailable"})
                    self.send(200, result)
                except (BrokenPipeError, ConnectionResetError, TimeoutError):
                    pass

            def send(self, code, body):
                payload = json.dumps(body).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format, *args):
                pass

        return Handler
