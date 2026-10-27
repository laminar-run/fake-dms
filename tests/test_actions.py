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
    pending.write_text(json.dumps({"request": request, "expiresAt": time.time() + 15}))
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
    (receiver.inbox / (name + ".request.json")).write_text(json.dumps({"request": request, "expiresAt": time.time() - 1}))
    (receiver.inbox / "bad.request.json").write_text("{")
    receiver.poll()
    assert not seen and not list(receiver.inbox.glob("*.json"))
