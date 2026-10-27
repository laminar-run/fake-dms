from contextlib import contextmanager
import json
import os
import time


@contextmanager
def locked_log(path):
    with path.with_suffix(".lock").open("a+b") as lock:
        lock.seek(0, os.SEEK_END)
        if not lock.tell():
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            with path.open("a+", encoding="utf-8") as stream:
                stream.seek(0)
                yield stream
        finally:
            lock.seek(0)
            if os.name == "nt":
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock, fcntl.LOCK_UN)


def read_receipts(stream):
    receipts = {}
    for line in stream:
        record = json.loads(line)
        request_id = record["requestId"]
        if not line.endswith("\n") or not isinstance(request_id, str) or not isinstance(record["fingerprint"], str):
            raise ValueError("Invalid action log entry")
        previous = receipts.get(request_id)
        if record["event"] == "started" and previous is None:
            receipts[request_id] = record
        elif record["event"] == "outcome" and previous is not None and previous["event"] == "started" and previous["fingerprint"] == record["fingerprint"]:
            if record["result"]["requestId"] != request_id:
                raise ValueError("Action log result does not match request")
            receipts[request_id] = record
        else:
            raise ValueError("Invalid action log sequence")
    return receipts


def append(stream, request_id, fingerprint, event, result=None):
    record = {"requestId": request_id, "fingerprint": fingerprint, "event": event, "timestamp": time.time()}
    if result is not None:
        record["result"] = result
    stream.write(json.dumps(record) + "\n")
    stream.flush()
    os.fsync(stream.fileno())
