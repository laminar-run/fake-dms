"""DealerDesk 98 - Entry Point."""
import os
import sys
import argparse

# Ensure the project root is on sys.path when launched from a shortcut
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import tkinter as tk
from db.connection import init_db
from db.seed import seed


def _launch_login(root: tk.Tk):
    from ui.login import LoginWindow

    def on_login_success(user: dict):
        from ui.dashboard import DashboardWindow
        from chaos.engine import ChaosEngine

        dashboard = DashboardWindow(root, user, on_logout=lambda: _launch_login(root))

        engine = ChaosEngine(root, on_logout=lambda: _kick_to_login(dashboard, root))
        if _get_chaos_setting("master_enabled") == "1":
            engine.start()

    LoginWindow(root, on_success=on_login_success)


def _kick_to_login(dashboard, root):
    try:
        dashboard.destroy()
    except Exception:
        pass
    _launch_login(root)


def _get_chaos_setting(key):
    try:
        from db.connection import get_connection
        conn = get_connection()
        row = conn.execute("SELECT value FROM chaos_settings WHERE key=?", (key,)).fetchone()
        conn.close()
        return row["value"] if row else "0"
    except Exception:
        return "0"


def main():
    parser = argparse.ArgumentParser(description="DealerDesk 98")
    parser.add_argument("command", nargs="?", choices=["setup"])
    parser.add_argument("--port", type=int)
    args = parser.parse_args()
    if args.command == "setup":
        if args.port is None:
            parser.error("setup requires --port")
        from test_control.config import setup
        print(setup(args.port))
        return
    if args.port is not None:
        parser.error("--port is only used with setup")

    init_db()
    seed()

    root = tk.Tk()
    root.withdraw()  # Hidden root - acts as parent for all Toplevel windows

    ico = os.path.join(_HERE, "assets", "dms.ico")
    if os.path.exists(ico):
        try:
            root.iconbitmap(ico)
        except Exception:
            pass

    _launch_login(root)
    from test_control.config import current, location
    from test_control.receiver import Receiver
    receiver = None
    try:
        entry = current()
        if entry:
            receiver = Receiver(root, entry, location().parent / "dealerdesk-receipts.sqlite")
    except (OSError, ValueError) as error:
        print(f"Action receiver unavailable: {error}", file=sys.stderr)
    if receiver:
        receiver.start()
    try:
        root.mainloop()
    finally:
        if receiver:
            receiver.stop()


if __name__ == "__main__":
    main()
