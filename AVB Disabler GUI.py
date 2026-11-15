import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

try:  # גרור ושחרר - אופציונלי (pip install tkinterdnd2)
    from tkinterdnd2 import TkinterDnD, DND_FILES
    BaseTk = TkinterDnD.Tk
    HAS_DND = True
except Exception:
    BaseTk = tk.Tk
    HAS_DND = False

BG, CARD, FG, MUTED = "#0f172a", "#1e293b", "#f1f5f9", "#94a3b8"
ACCENT, OK, WARN, ERR = "#3b82f6", "#22c55e", "#f59e0b", "#ef4444"
FONT = "Segoe UI"


def base_dir():
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent


class App(BaseTk):
    def __init__(self):
        super().__init__()
        self.title("משבית AVB")
        self.geometry("560x480")
        self.minsize(520, 440)
        self.configure(bg=BG)
        self.data = None
        self.path = None
        self.build()

    def label(self, parent, text, size=11, color=FG, bold=False, **kw):
        return tk.Label(parent, text=text, bg=parent["bg"], fg=color, anchor="e", justify="right",
                        font=(FONT, size, "bold" if bold else "normal"), **kw)

    def button(self, parent, text, cmd, color=ACCENT, state="normal"):
        b = tk.Button(parent, text=text, command=cmd, bg=color, fg="white", activebackground=color,
                      activeforeground="white", relief="flat", bd=0, cursor="hand2", state=state,
                      font=(FONT, 12, "bold"), padx=18, pady=10, disabledforeground="#64748b")
        return b

    def build(self):
        self.label(self, "משבית AVB", 24, bold=True).pack(fill="x", padx=24, pady=(20, 0))
        self.label(self, "השבתת Android Verified Boot בקובץ vbmeta.img", 11, MUTED).pack(fill="x", padx=24)

        # אזור בחירת קובץ
        self.drop = tk.Frame(self, bg=CARD, highlightthickness=2, highlightbackground="#334155", cursor="hand2")
        self.drop.pack(fill="x", padx=24, pady=18)
        self.drop_icon = tk.Label(self.drop, text="📂", bg=CARD, fg=FG, font=(FONT, 30))
        self.drop_icon.pack(pady=(14, 0))
        hint = "לחץ כאן לבחירת קובץ" + (" או גרור ושחרר אותו לכאן" if HAS_DND else "")
        self.drop_text = tk.Label(self.drop, text=hint, bg=CARD, fg=FG, font=(FONT, 12, "bold"))
        self.drop_text.pack(pady=(4, 14))
        for w in (self.drop, self.drop_icon, self.drop_text):
            w.bind("<Button-1>", lambda e: self.choose())
        if HAS_DND:
            self.drop.drop_target_register(DND_FILES)
            self.drop.dnd_bind("<<Drop>>", lambda e: self.load(self.tk.splitlist(e.data)[0]))

        # סטטוס
        card = tk.Frame(self, bg=CARD)
        card.pack(fill="x", padx=24)
        self.status_dot = tk.Label(card, text="●", bg=CARD, fg=MUTED, font=(FONT, 16))
        self.status_dot.pack(side="right", padx=(8, 14), pady=14)
        box = tk.Frame(card, bg=CARD)
        box.pack(side="right", fill="x", expand=True, pady=10)
        self.status = self.label(box, "לא נבחר קובץ", 13, bold=True)
        self.status.pack(fill="x")
        self.status.configure(bg=CARD)
        self.detail = self.label(box, "בחר קובץ vbmeta כדי להתחיל", 10, MUTED, wraplength=380)
        self.detail.pack(fill="x")
        self.detail.configure(bg=CARD)

        # כפתורים
        row = tk.Frame(self, bg=BG)
        row.pack(fill="x", padx=24, pady=18)
        self.go = self.button(row, "השבת AVB", self.disable, OK, "disabled")
        self.go.pack(side="right")
        self.button(row, "בחר קובץ", self.choose, "#475569").pack(side="right", padx=10)

        self.out_label = self.label(self, "", 9, MUTED, wraplength=500)
        self.out_label.pack(fill="x", padx=24)

    def set_status(self, title, detail, color):
        self.status.config(text=title)
        self.detail.config(text=detail)
        self.status_dot.config(fg=color)

    def choose(self):
        p = filedialog.askopenfilename(filetypes=[("vbmeta images", "*.img"), ("כל הקבצים", "*.*")])
        if p:
            self.load(p)

    def load(self, path_str):
        self.data, self.path = None, None
        self.go.config(state="disabled")
        self.out_label.config(text="")
        path = Path(path_str.strip('"'))
        if not path.exists():
            return self.set_status("הקובץ לא קיים", str(path), ERR)
        try:
            data = bytearray(path.read_bytes())
        except Exception as e:
            return self.set_status("שגיאה בקריאת הקובץ", str(e), ERR)
        self.drop_text.config(text=path.name)
        self.drop_icon.config(text="📄")
        if data[:4] != b"AVB0":
            return self.set_status("קובץ vbmeta לא חוקי", "הקובץ אינו מתחיל בחתימת AVB0", ERR)
        if data[123] & 3:
            return self.set_status("AVB כבר מושבת", "אין צורך בשינוי בקובץ זה", WARN)
        self.data, self.path = data, path
        self.set_status("AVB פעיל", "ניתן להשבית אותו על ידי לחיצה על הכפתור", ACCENT)
        self.go.config(state="normal")

    def disable(self):
        if self.data is None:
            return
        out_dir = base_dir() / "Disabled"
        out_dir.mkdir(exist_ok=True)
        out = out_dir / f"{self.path.stem}_disabled{self.path.suffix}"
        if out.exists() and not messagebox.askyesno("הקובץ קיים", "הקובץ כבר קיים. האם לדרוס?"):
            return
        try:
            self.data[123] |= 3
            out.write_bytes(self.data)
        except Exception as e:
            return self.set_status("שגיאה בשמירה", str(e), ERR)
        self.data = None
        self.go.config(state="disabled")
        self.set_status("AVB הושבת בהצלחה", "הקובץ המושבת נשמר", OK)
        self.out_label.config(text=f"נשמר ב: {out}")


if __name__ == "__main__":
    App().mainloop()
