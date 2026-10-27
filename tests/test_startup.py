import builtins
import logging
import sys
from unittest.mock import Mock

import main
import pytest


@pytest.mark.parametrize("failure", ["missing_dependency", "receiver_startup"])
def test_optional_actions_do_not_block_login(monkeypatch, caplog, failure):
    root = Mock()
    login = Mock()
    monkeypatch.setattr(main.tk, "Tk", lambda: root)
    monkeypatch.setattr(main, "init_db", lambda: None)
    monkeypatch.setattr(main, "seed", lambda: None)
    monkeypatch.setattr(main, "_launch_login", login)
    if failure == "missing_dependency":
        monkeypatch.delitem(sys.modules, "action_control.receiver", raising=False)
        original = builtins.__import__
        def without_jsonschema(name, *args, **kwargs):
            if name == "jsonschema":
                raise ModuleNotFoundError("No module named 'jsonschema'")
            return original(name, *args, **kwargs)
        monkeypatch.setattr(builtins, "__import__", without_jsonschema)
    else:
        monkeypatch.setattr("action_control.receiver.start_installed", Mock(side_effect=OSError("inbox unavailable")))
    with caplog.at_level(logging.ERROR):
        main.main()
    login.assert_called_once_with(root)
    root.mainloop.assert_called_once()
    assert "Cannot start optional action tools" in caplog.text
