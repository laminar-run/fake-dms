from bisect import insort
import hashlib
import json
import logging
import os
from pathlib import Path
import math
import time

from jsonschema import Draft202012Validator

from action_control import receipts

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


def install(user, instance, version):
    if not instance or len(instance) > 128 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in instance):
        raise ValueError("Invalid instance ID")
    if not version or len(version) > 128:
        raise ValueError("Installed version is required")
    directory = registration_dir(user)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "dealerdesk.json"
    identity = hashlib.sha256(("dealerdesk\0" + instance).encode()).hexdigest()
    inbox = directory.parent.parent / "inboxes" / directory.name / identity
    inbox.mkdir(parents=True, exist_ok=True)
    entry = {"targetUser": user, "target": {"kind": "app", "appId": "dealerdesk", "instanceId": instance},
             "installedVersion": version, "actions": [ACTION], "inbox": str(inbox)}
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
        self.inbox = Path(registration["inbox"])
        directory = Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))) / "DealerDesk" / "actions"
        directory.mkdir(parents=True, exist_ok=True)
        self.log_path = directory / (registration["target"]["instanceId"] + ".executed-actions.jsonl")

    def execute(self, request, expires_at):
        request_id = request.get("requestId") if isinstance(request, dict) else None
        try:
            Draft202012Validator(REQUEST_SCHEMA).validate(request)
            if request["target"] != self.registration["target"] or request["actionId"] != ACTION["id"] or request["actionVersion"] != ACTION["version"]:
                raise ValueError("Unknown target, action, or version")
            Draft202012Validator(ACTION["inputSchema"]).validate(request["parameters"])
        except Exception as exc:
            return outcome(request_id, "rejected", str(exc))
        fingerprint = hashlib.sha256(json.dumps(request, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        try:
            with receipts.locked_log(self.log_path) as stream:
                previous = receipts.read_receipts(stream).get(request_id)
                if previous:
                    if previous["fingerprint"] != fingerprint:
                        return outcome(request_id, "rejected", "requestId was already used for a different request")
                    return previous.get("result", outcome(request_id, "unknown", "Previous attempt was interrupted"))
                receipts.append(stream, request_id, fingerprint, "started")
                if time.time() >= expires_at:
                    response = outcome(request_id, "rejected", "Request expired before execution")
                else:
                    from chaos.scenarios import scenario_critical_error
                    try:
                        scenario_critical_error(self.root, immediate=True)
                        response = outcome(request_id, "completed")
                    except Exception as exc:
                        response = outcome(request_id, "failed", str(exc))
                receipts.append(stream, request_id, fingerprint, "outcome", response)
                return response
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return outcome(request_id, "unknown", f"Cannot safely use action log: {exc}")

    def pending_requests(self):
        pending = []
        for path in self.inbox.glob("*.request.json"):
            try:
                with path.open("rb") as stream:
                    body = stream.read(65537)
                if len(body) > 65536:
                    raise ValueError("Request exceeds size limit")
                envelope = json.loads(body)
                created = envelope["createdAt"]
                expires = envelope["expiresAt"]
                request_id = envelope["request"]["requestId"]
                if not isinstance(request_id, str) or any(type(t) not in (int, float) or not math.isfinite(t) for t in (created, expires)):
                    raise ValueError("Invalid request ID or timestamp")
                if not 0 < created <= expires or not 0 < expires - time.time() <= 30:
                    raise ValueError("Invalid or expired request timestamp")
                if path.name != hashlib.sha256(request_id.encode()).hexdigest() + ".request.json":
                    raise ValueError("Request filename does not match its ID")
                insort(pending, (created, request_id, path, body))
                if len(pending) > 10:
                    pending.pop()
            except FileNotFoundError:
                continue
            except OSError:
                logging.exception("Cannot read action request %s", path)
                continue
            except (ValueError, KeyError, TypeError, OverflowError):
                logging.exception("Discarding invalid action request %s", path)
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    logging.exception("Cannot discard action request %s", path)
        return pending

    def poll(self):
        try:
            for _, _, pending, expected_body in self.pending_requests():
                processing = pending.with_name(pending.name.replace(".request.json", ".processing.json"))
                result = pending.with_name(pending.name.replace(".request.json", ".result.json"))
                temporary = result.with_suffix(".tmp")
                claimed = False
                try:
                    os.link(pending, processing)
                    claimed = True
                    pending.unlink()
                    with processing.open("rb") as stream:
                        body = stream.read(65537)
                    if body != expected_body:
                        raise ValueError("Request changed after ordering")
                    envelope = json.loads(body)
                    request = envelope["request"]
                    expires_at = envelope["expiresAt"]
                    response = self.execute(request, expires_at)
                    temporary.write_text(json.dumps(response), encoding="utf-8")
                    os.replace(temporary, result)
                except (FileNotFoundError, FileExistsError):
                    pass
                except (OSError, ValueError, KeyError, TypeError):
                    logging.exception("Cannot process action request %s", pending)
                finally:
                    if claimed:
                        processing.unlink(missing_ok=True)
                        temporary.unlink(missing_ok=True)
            for path in self.inbox.iterdir():
                try:
                    if path.suffix in (".json", ".tmp") and time.time() - path.stat().st_mtime > 60:
                        path.unlink(missing_ok=True)
                except FileNotFoundError:
                    continue
        except OSError:
            logging.exception("Cannot poll action inbox %s", self.inbox)
        finally:
            self.root.after(100, self.poll)


def start_installed(root):
    user = os.environ.get("USERNAME")
    if not user or "PROGRAMDATA" not in os.environ:
        return
    for path in registration_dir(user).glob("dealerdesk.json"):
        try:
            registration = json.loads(path.read_text(encoding="utf-8"))
            if registration["targetUser"].split("\\")[-1].lower() != user.lower():
                continue
            if registration["target"]["appId"] != "dealerdesk":
                continue
            root.after(100, Receiver(root, registration).poll)
        except (OSError, ValueError, KeyError, TypeError):
            logging.exception("Cannot start action receiver for %s", path)
