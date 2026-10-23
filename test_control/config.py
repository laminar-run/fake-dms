import ctypes
import getpass
import json
import os
from pathlib import Path
import socket
import tempfile
import uuid


APP_ID = "dealerdesk"


def user():
    if os.name == "nt":
        size = ctypes.c_ulong(257)
        name = ctypes.create_unicode_buffer(size.value)
        if not ctypes.windll.advapi32.GetUserNameW(name, ctypes.byref(size)):
            raise OSError("Cannot resolve Windows user")
        return name.value.split("\\")[-1].casefold()
    return getpass.getuser().strip().split("\\")[-1].casefold()


def location():
    override = os.getenv("MINICOR_DATA_DIR")
    if override:
        root = Path(override)
    elif os.name == "nt":
        root = Path(os.getenv("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "Minicor"
    else:
        root = Path.home() / ".minicor"
    return root / "injected-apps.json"


def _entries(path):
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if set(data) != {"version", "apps"} or type(data["version"]) is not int or data["version"] != 1 or not isinstance(data["apps"], list):
        raise ValueError("Invalid injected app map")
    seen = set()
    ports = set()
    for entry in data["apps"]:
        if set(entry) != {"appId", "targetUser", "instanceId", "port"}:
            raise ValueError("Invalid injected app entry")
        key = (entry["appId"], entry["targetUser"])
        if key in seen or type(entry["port"]) is not int or not 1 <= entry["port"] <= 65535 or entry["port"] in ports:
            raise ValueError("Duplicate app or port")
        uuid.UUID(entry["instanceId"])
        seen.add(key)
        ports.add(entry["port"])
    return data["apps"]


def current(path=None):
    entries = _entries(path or location())
    entry = next((item for item in entries if item["appId"] == APP_ID and item["targetUser"] == user()), None)
    return dict(entry, instanceId=str(uuid.UUID(entry["instanceId"]))) if entry else None


def setup(port, path=None):
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Port must be 1..65535")
    path = Path(path or location())
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(".lock")
    with open(lock_path, "a+b") as lock:
        if os.name == "nt":
            import msvcrt
            lock.seek(0)
            lock.write(b"0")
            lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            entries = _entries(path)
            for entry in entries:
                if entry["port"] == port and (entry["appId"], entry["targetUser"]) != (APP_ID, user()):
                    raise ValueError("Port already configured")
            prior = next((entry for entry in entries if (entry["appId"], entry["targetUser"]) == (APP_ID, user())), None)
            if prior and prior["port"] == port:
                return prior
            entry = {"appId": APP_ID, "targetUser": user(), "instanceId": prior["instanceId"] if prior else str(uuid.uuid4()), "port": port}
            entries = [item for item in entries if (item["appId"], item["targetUser"]) != (APP_ID, user())]
            entries.append(entry)
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", port))
            fd, temp = tempfile.mkstemp(dir=path.parent, prefix=".injected-apps-")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as output:
                    json.dump({"version": 1, "apps": entries}, output, separators=(",", ":"))
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(temp, path)
            finally:
                if os.path.exists(temp):
                    os.unlink(temp)
            return entry
        finally:
            if os.name == "nt":
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock, fcntl.LOCK_UN)
