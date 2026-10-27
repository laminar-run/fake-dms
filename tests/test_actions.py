import json
import hashlib
import time

from action_control.receiver import ACTION, Receiver, install


class Root:
    def after(self, delay, callback):
        pass


def test_receiver_validates_and_deduplicates_after_popup(tmp_path, monkeypatch):
    monkeypatch.setenv("PROGRAMDATA", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    path = install("Robot", "desk", "test-version")
    registration = json.loads(path.read_text())
    receiver = Receiver(Root(), registration)
    seen = []
    monkeypatch.setattr("chaos.scenarios.scenario_critical_error", lambda root, immediate: seen.append(immediate))
    request = {"requestId": "one", "target": registration["target"], "actionId": ACTION["id"], "actionVersion": 1, "parameters": {}}
    name = hashlib.sha256(request["requestId"].encode()).hexdigest()
    pending = receiver.inbox / (name + ".request.json")
    result = receiver.inbox / (name + ".result.json")
    pending.write_text(json.dumps({"request": request, "createdAt": time.time(), "expiresAt": time.time() + 15}))
    receiver.poll()
    response = json.loads(result.read_text())
    assert response["outcome"]["kind"] == "completed"
    assert receiver.execute(request, time.time() + 15) == response
    assert seen == [True]
    request["parameters"] = {"extra": True}
    assert receiver.execute(request, time.time() + 15)["outcome"]["kind"] == "rejected"


def test_reinstall_replaces_the_app_registration(tmp_path, monkeypatch):
    monkeypatch.setenv("PROGRAMDATA", str(tmp_path))
    first = install("Robot", "one", "old")
    second = install("Robot", "two", "new")
    assert first == second
    registration = json.loads(second.read_text())
    assert registration["target"]["instanceId"] == "two"
    assert registration["installedVersion"] == "new"


def test_expired_and_malformed_files_do_not_block_polling(tmp_path, monkeypatch):
    monkeypatch.setenv("PROGRAMDATA", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    receiver = Receiver(Root(), json.loads(install("robot", "desk", "v1").read_text()))
    seen = []
    monkeypatch.setattr("chaos.scenarios.scenario_critical_error", lambda *args, **kwargs: seen.append(1))
    request = {"requestId": "expired", "target": receiver.registration["target"], "actionId": ACTION["id"], "actionVersion": 1, "parameters": {}}
    name = hashlib.sha256(b"expired").hexdigest()
    (receiver.inbox / (name + ".request.json")).write_text(json.dumps({"request": request, "createdAt": time.time() - 20, "expiresAt": time.time() - 1}))
    (receiver.inbox / "bad.request.json").write_text("{")
    receiver.poll()
    assert not seen and not list(receiver.inbox.glob("*.json"))


def test_cleanup_continues_when_a_file_disappears(tmp_path, monkeypatch, caplog):
    from pathlib import Path
    from unittest.mock import Mock
    monkeypatch.setenv("PROGRAMDATA", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    receiver = Receiver(Mock(), json.loads(install("robot", "desk", "v1").read_text()))
    missing = receiver.inbox / "missing.json"
    stale = receiver.inbox / "stale.json"
    stale.write_text("{}")
    monkeypatch.setattr(Path, "iterdir", lambda self: iter([missing, stale]))
    monkeypatch.setattr("action_control.receiver.time.time", lambda: 10**12)
    receiver.poll()
    assert not stale.exists()
    assert not caplog.records
    receiver.root.after.assert_called_once_with(100, receiver.poll)


def test_text_receipts_survive_restart_and_fail_closed(tmp_path, monkeypatch):
    from action_control import receipts
    monkeypatch.setenv("PROGRAMDATA", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    registration = json.loads(install("robot", "desk", "v1").read_text())
    receiver = Receiver(Root(), registration)
    effects = []
    monkeypatch.setattr("chaos.scenarios.scenario_critical_error", lambda *a, **k: effects.append(1))
    request = {"requestId": "one", "target": registration["target"], "actionId": ACTION["id"], "actionVersion": 1, "parameters": {}}
    result = receiver.execute(request, time.time() + 15)
    assert Receiver(Root(), registration).execute(request, time.time() + 15) == result
    entries = receiver.log_path.read_text().splitlines()
    assert [json.loads(line)["event"] for line in entries] == ["started", "outcome"]
    conflicting = {**json.loads(entries[0]), "fingerprint": "different"}
    receiver.log_path.write_text(json.dumps(conflicting) + "\n")
    assert receiver.execute(request, time.time() + 15)["outcome"]["kind"] == "rejected"
    with receipts.locked_log(receiver.log_path):
        assert receiver.execute(request, time.time() + 15)["outcome"]["kind"] == "unknown"
    receiver.log_path.write_text(entries[0] + "\n")
    assert Receiver(Root(), registration).execute(request, time.time() + 15)["outcome"]["kind"] == "unknown"
    receiver.log_path.write_text(entries[0] + '\n{"requestId":')
    assert receiver.execute({**request, "requestId": "two"}, time.time() + 15)["outcome"]["kind"] == "unknown"
    receiver.log_path.write_text("")
    monkeypatch.setattr(receipts.os, "fsync", lambda fd: (_ for _ in ()).throw(OSError("disk failed")))
    assert receiver.execute(request, time.time() + 15)["outcome"]["kind"] == "unknown"
    assert effects == [1]


def test_pending_requests_execute_by_timestamp_then_id(tmp_path, monkeypatch):
    monkeypatch.setenv("PROGRAMDATA", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    receiver = Receiver(Root(), json.loads(install("robot", "desk", "v1").read_text()))
    calls = []
    def execute(request, expires):
        calls.append(request["requestId"])
        return {"requestId": request["requestId"], "outcome": {"kind": "completed"}}
    monkeypatch.setattr(receiver, "execute", execute)
    now = time.time()
    for request_id, created in (("z", now), ("b", now - 1), ("a", now - 1)):
        name = hashlib.sha256(request_id.encode()).hexdigest()
        (receiver.inbox / (name + ".request.json")).write_text(json.dumps({"request": {"requestId": request_id}, "createdAt": created, "expiresAt": now + 15}))
    receiver.poll()
    assert calls == ["a", "b", "z"]
