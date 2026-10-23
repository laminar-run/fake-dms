import hashlib
import http.client
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
import uuid
from unittest.mock import patch

from test_control.config import current, setup, user
from test_control.receiver import Receiver, session_id


class Root:
    def after(self, _delay, _callback):
        pass


class Window:
    alive = True

    def winfo_exists(self):
        return self.alive


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.entry = {"appId": "dealerdesk", "targetUser": user(), "instanceId": str(uuid.uuid4()), "port": 0}
        self.receiver = Receiver(Root(), self.entry, Path(self.temp.name) / "receipts.sqlite")
        self.addCleanup(self.receiver.stop)
        self.receiver.start()
        self.port = self.receiver.server.server_address[1]

    def envelope(self, **changes):
        value = {"version": 1, "requestId": str(uuid.uuid4()), "injectionId": str(uuid.uuid4()),
                 "actionId": "dealerdesk.critical-error", "parameters": {}, "targetUser": user(),
                 "sessionId": session_id(), "appInstanceId": self.entry["instanceId"]}
        value.update(changes)
        return value

    def post(self, value):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        conn.request("POST", "/action", json.dumps(value), {"Content-Type": "application/json"})
        response = conn.getresponse()
        result = response.status, json.loads(response.read())
        conn.close()
        return result

    def execute(self, value):
        output = []
        thread = threading.Thread(target=lambda: output.append(self.post(value)))
        thread.start()
        for _ in range(100):
            if self.receiver.pending:
                break
            time.sleep(.005)
        self.receiver.poll()
        thread.join(3)
        self.assertFalse(thread.is_alive())
        return output[0]

    def test_popup_duplicate_conflict_and_reinject(self):
        windows = []

        def show(_root, on_created, schedule):
            self.assertFalse(schedule)
            window = Window()
            windows.append(window)
            on_created(window)

        with patch("chaos.scenarios.scenario_critical_error", side_effect=show):
            first = self.envelope()
            status, result = self.execute(first)
            self.assertEqual((status, result["status"], len(windows)), (200, "completed", 1))
            self.assertEqual(self.post(first), (status, result))
            upper = dict(first, requestId=first["requestId"].upper())
            self.assertEqual(self.post(upper), (status, result))
            second = self.envelope()
            self.assertEqual(self.execute(second)[1]["injectionId"], first["injectionId"])
            self.assertEqual(len(windows), 1)
            windows[0].alive = False
            self.assertEqual(self.execute(self.envelope())[1]["status"], "completed")
            self.assertEqual(len(windows), 2)
            changed = dict(first, parameters={"unexpected": 1})
            self.assertEqual(self.post(changed)[0], 400)
            changed = dict(first, injectionId=str(uuid.uuid4()))
            self.assertEqual(self.post(changed)[0], 409)

    def test_uncertain_restart_and_rejected_shapes(self):
        request = self.envelope()
        with self.receiver._db() as db:
            from test_control.receiver import validate
            db.execute("INSERT INTO receipts VALUES (?,?,NULL)", (request["requestId"], validate(request, self.entry)))
        self.assertEqual(self.post(request)[1]["status"], "unknown")
        self.assertEqual(self.execute(self.envelope(actionId="unknown.action"))[1]["code"], "unsupported_action")
        self.assertEqual(self.execute(self.envelope(version=2))[1]["code"], "unsupported_version")
        for changes in ({"sessionId": True}, {"appInstanceId": str(uuid.uuid4())},
                        {"parameters": {"x": 1}}, {"requestId": "bad"}, {"extra": 1}):
            self.assertEqual(self.post(self.envelope(**changes))[0], 400)

    def test_queued_timeout_does_not_show_later(self):
        request = self.envelope()
        self.assertEqual(self.post(request)[1]["code"], "ui_unresponsive")
        with patch("chaos.scenarios.scenario_critical_error") as show:
            self.receiver.poll()
            show.assert_not_called()
        self.assertEqual(self.post(request)[1]["status"], "failed")

    def test_started_timeout_reconciles_without_second_effect(self):
        request = self.envelope()
        entered = threading.Event()
        release = threading.Event()
        output = []

        def show(_root, on_created, schedule):
            entered.set()
            release.wait(3)
            on_created(Window())

        with patch("chaos.scenarios.scenario_critical_error", side_effect=show):
            client = threading.Thread(target=lambda: output.append(self.post(request)))
            client.start()
            for _ in range(100):
                if self.receiver.pending:
                    break
                time.sleep(.005)
            poll = threading.Thread(target=self.receiver.poll)
            poll.start()
            self.assertTrue(entered.wait(1))
            client.join(3)
            self.assertEqual(output[0][1]["status"], "unknown")
            release.set()
            poll.join(3)
            self.assertEqual(self.post(request)[1]["status"], "completed")


class ConfigTests(unittest.TestCase):
    def test_atomic_setup_preserves_other_apps_and_instance(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "injected-apps.json"
            other = {"appId": "other", "targetUser": user(), "instanceId": str(uuid.uuid4()).upper(), "port": 39111}
            path.write_text(json.dumps({"version": 1, "apps": [other]}))
            first = setup(39112, path)
            second = setup(39113, path)
            self.assertEqual(first["instanceId"], second["instanceId"])
            self.assertEqual(current(path), second)
            self.assertEqual(json.loads(path.read_text())["apps"], [other, second])
            with self.assertRaises(ValueError):
                setup(39111, path)
            self.assertEqual(current(path), second)
            second["instanceId"] = second["instanceId"].upper()
            path.write_text(json.dumps({"version": 1, "apps": [other, second]}))
            self.assertEqual(current(path)["instanceId"], first["instanceId"])
            path.write_text(json.dumps({"version": True, "apps": []}))
            with self.assertRaises(ValueError):
                current(path)

    def test_pinned_contract_parameter_shapes(self):
        path = Path(__file__).parents[1] / "contracts" / "injected-actions.v1.json"
        raw = path.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), "7f17102b9a7c9567ad409429b6ba717efd386876afce79e420ff9e013f062f9a")
        actions = json.loads(raw)["actions"]
        self.assertEqual(actions["dealerdesk.critical-error"]["properties"], {})
        self.assertFalse(actions["dealerdesk.critical-error"]["additionalProperties"])
        self.assertEqual(actions["vm.minimize-window"]["required"], ["windowId"])
