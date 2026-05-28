"""
Run once to place a DealerDesk 98 shortcut on the desktop.
Requires: pip install pywin32
"""
import os
import sys


def create_shortcut():
    try:
        import win32com.client
    except ImportError:
        print("ERROR: pywin32 not installed. Run: pip install pywin32 --user")
        sys.exit(1)

    here = os.path.dirname(os.path.abspath(__file__))
    desktop = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), "Desktop")
    shortcut_path = os.path.join(desktop, "DealerDesk 98.lnk")

    python_exe = sys.executable
    pythonw = python_exe.replace("python.exe", "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = python_exe  # fall back to python.exe (shows console)

    ico_path = os.path.join(here, "assets", "dms.ico")
    main_script = os.path.join(here, "main.py")

    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.TargetPath = pythonw
    shortcut.Arguments = f'"{main_script}"'
    shortcut.WorkingDirectory = here
    shortcut.Description = "DealerDesk 98 - Dealership Management System"
    if os.path.exists(ico_path):
        shortcut.IconLocation = ico_path
    shortcut.save()

    print(f"Shortcut created: {shortcut_path}")
    print(f"  Target : {pythonw}")
    print(f"  Script : {main_script}")


if __name__ == "__main__":
    create_shortcut()
