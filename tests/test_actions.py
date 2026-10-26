import json
import threading

from action_control.receiver import ACTION, Receiver, install


class Root:
    def after(self, delay, callback):
        pass


def test_receiver_validates_and_deduplicates_after_popup(tmp_path, monkeypatch):
    monkeypatch.setenv("PROGRAMDATA", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    path = install("Robot", "desk", 12345, "test-version")
    registration = json.loads(path.read_text())
    receiver = Receiver(Root(), registration)
    seen = []
    monkeypatch.setattr("chaos.scenarios.scenario_critical_error", lambda root, immediate: seen.append(immediate))
    request = {"requestId": "one", "target": registration["target"], "actionId": ACTION["id"], "actionVersion": 1, "parameters": {}}
    results = []
    thread = threading.Thread(target=lambda: results.append(receiver.execute(request)))
    thread.start()
    request_id, event, result = receiver.pending.get(timeout=2)
    receiver.pending.put((request_id, event, result))
    receiver.poll()
    thread.join(timeout=2)
    assert results[0]["outcome"]["kind"] == "completed"
    assert receiver.execute(request) == results[0]
    assert seen == [True]
    request["parameters"] = {"extra": True}
    assert receiver.execute(request)["outcome"]["kind"] == "rejected"


def test_reinstall_replaces_the_app_registration(tmp_path, monkeypatch):
    monkeypatch.setenv("PROGRAMDATA", str(tmp_path))
    first = install("Robot", "one", 12345, "old")
    second = install("Robot", "two", 12346, "new")
    assert first == second
    registration = json.loads(second.read_text())
    assert registration["target"]["instanceId"] == "two"
    assert registration["installedVersion"] == "new"
