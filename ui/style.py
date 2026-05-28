"""Windows 98 aesthetic constants."""

BG = "#C0C0C0"
BG_DARK = "#808080"
BG_LIGHT = "#FFFFFF"
TITLE_BG = "#000080"
TITLE_FG = "#FFFFFF"
HIGHLIGHT = "#000080"
BUTTON_BG = "#C0C0C0"
ENTRY_BG = "#FFFFFF"
ENTRY_FG = "#000000"
SELECT_BG = "#000080"
SELECT_FG = "#FFFFFF"
STATUS_BG = "#C0C0C0"
ERROR_FG = "#FF0000"
DISABLED_FG = "#808080"

FONT = ("MS Sans Serif", 8)
FONT_BOLD = ("MS Sans Serif", 8, "bold")
FONT_TITLE = ("MS Sans Serif", 10, "bold")
FONT_SMALL = ("MS Sans Serif", 7)
FONT_MONO = ("Courier New", 8)

RELIEF_FRAME = "ridge"
RELIEF_BUTTON = "raised"
RELIEF_ENTRY = "sunken"
BORDER = 2

PADX = 4
PADY = 2


def apply_theme(widget):
    """Recursively apply W98 background to all widgets."""
    try:
        widget.configure(bg=BG)
    except Exception:
        pass
    for child in widget.winfo_children():
        apply_theme(child)
