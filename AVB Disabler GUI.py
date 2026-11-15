import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

try:  # גרור ושחרר - אופציונלי (pip install tkinterdnd2)
    from tkinterdnd2 import TkinterDnD, DND_FILES
    BaseTk, HAS_DND = TkinterDnD.Tk, True
except Exception:
    BaseTk, HAS_DND = tk.Tk, False

BG, CARD, BORDER = "#0b1020", "#151b30", "#27304d"
FG, MUTED = "#f1f5f9", "#8b97b5"
BLUE, GREEN, AMBER, RED, GRAY = "#4f8cff", "#2ecc8f", "#f5a623", "#ff5d6c", "#5b6585"
FONT = "Segoe UI"


def hex2rgb(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def mix(a, b, t):
    ra, rb = hex2rgb(a), hex2rgb(b)
    return "#%02x%02x%02x" % tuple(int(x + (y - x) * t) for x, y in zip(ra, rb))


def base_dir():
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent


def round_rect(cv, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


class Anim:
    """אנימציית צבע חלקה לפריט בקנבס"""
    def __init__(self, widget, steps=10, delay=15):
        self.w, self.steps, self.delay, self.job = widget, steps, delay, None

    def run(self, start, end, apply):
        if self.job:
            self.w.after_cancel(self.job)
        def step(i=0):
            apply(mix(start, end, i / self.steps))
            if i < self.steps:
                self.job = self.w.after(self.delay, step, i + 1)
        step()


class Button(tk.Canvas):
    def __init__(self, parent, text, cmd, color=BLUE, width=190, height=50):
        super().__init__(parent, width=width, height=height, bg=parent["bg"], highlightthickness=0, bd=0)
        self.cmd, self.color, self.enabled, self.cur = cmd, color, True, color
        self.rect = round_rect(self, 2, 2, width - 2, height - 2, 14, fill=color, outline="")
        self.txt = self.create_text(width / 2, height / 2, text=text, fill="white", font=(FONT, 12, "bold"))
        self.anim = Anim(self, 8, 12)
        self.bind("<Enter>", lambda e: self.hover(True))
        self.bind("<Leave>", lambda e: self.hover(False))
        self.bind("<Button-1>", lambda e: self.enabled and self.cmd())

    def paint(self, c):
        self.cur = c
        self.itemconfig(self.rect, fill=c)

    def hover(self, on):
        if self.enabled:
            self.configure(cursor="hand2")
            self.anim.run(self.cur, mix(self.color, "#ffffff", 0.18) if on else self.color, self.paint)

    def set_enabled(self, on):
        self.enabled = on
        self.configure(cursor="" if not on else "hand2")
        self.anim.run(self.cur, self.color if on else "#232b45", self.paint)
        self.itemconfig(self.txt, fill="white" if on else "#5d6787")


class App(BaseTk):
    W = 560

    def __init__(self):
        super().__init__()
        self.title("משבית AVB")
        self.geometry("600x560")
        self.minsize(600, 560)
        self.configure(bg=BG)
        self.data = self.path = None
        self.accent = GRAY
        self.build()

    def text(self, parent, txt, size, color=FG, bold=False, **kw):
        return tk.Label(parent, text=txt, bg=parent["bg"], fg=color, anchor="e", justify="right",
                        font=(FONT, size, "bold" if bold else "normal"), **kw)

    def build(self):
        head = tk.Frame(self, bg=BG)
        head.pack(fill="x", padx=30, pady=(26, 0))
        self.text(head, "משבית AVB", 26, bold=True).pack(fill="x")
        self.text(head, "השבתת Android Verified Boot בקובץ vbmeta.img", 11, MUTED).pack(fill="x", pady=(2, 0))

        # אזור בחירת קובץ
        self.drop = tk.Canvas(self, height=170, bg=BG, highlightthickness=0, cursor="hand2")
        self.drop.pack(fill="x", padx=30, pady=22)
        self.drop.bind("<Configure>", self.draw_drop)
        self.drop.bind("<Button-1>", lambda e: self.choose())
        self.drop.bind("<Enter>", lambda e: self.drop_anim.run(self.drop_col, BLUE, self.set_drop))
        self.drop.bind("<Leave>", lambda e: self.drop_anim.run(self.drop_col, BORDER, self.set_drop))
        self.drop_anim, self.drop_col = Anim(self.drop, 8, 12), BORDER
        if HAS_DND:
            self.drop.drop_target_register(DND_FILES)
            self.drop.dnd_bind("<<Drop>>", lambda e: self.load(self.tk.splitlist(e.data)[0]))

        # כרטיס סטטוס
        self.card = tk.Canvas(self, height=96, bg=BG, highlightthickness=0)
        self.card.pack(fill="x", padx=30)
        self.card.bind("<Configure>", self.draw_card)

        # פס התקדמות
        self.bar = tk.Canvas(self, height=6, bg=BG, highlightthickness=0)
        self.bar.pack(fill="x", padx=30, pady=(16, 0))
        self.bar_pct = 0
        self.bar.bind("<Configure>", lambda e: self.draw_bar())

        row = tk.Frame(self, bg=BG)
        row.pack(fill="x", padx=30, pady=20)
        self.go = Button(row, "השבת AVB", self.disable, GREEN)
        self.go.pack(side="right")
        self.go.set_enabled(False)
        Button(row, "בחר קובץ", self.choose, "#3a4466", width=150).pack(side="right", padx=12)

        self.out = self.text(self, "", 9, MUTED, wraplength=520)
        self.out.pack(fill="x", padx=30)

    # ציורים
    def draw_drop(self, e=None):
        c, w = self.drop, self.drop.winfo_width()
        c.delete("all")
        self.drop_bg = round_rect(c, 2, 2, w - 2, 168, 22, fill=CARD, outline=self.drop_col, width=2)
        self.drop_icon = c.create_text(w / 2, 62, text="📂", font=(FONT, 36), fill=FG)
        hint = "לחץ לבחירת קובץ" + (" או גרור ושחרר לכאן" if HAS_DND else "")
        self.drop_title = c.create_text(w / 2, 117, text=getattr(self, "fname", hint), fill=FG, font=(FONT, 13, "bold"))
        self.drop_sub = c.create_text(w / 2, 142, text="vbmeta.img", fill=MUTED, font=(FONT, 10))

    def set_drop(self, col):
        self.drop_col = col
        self.drop.itemconfig(self.drop_bg, outline=col)

    def draw_card(self, e=None):
        c, w = self.card, self.card.winfo_width()
        c.delete("all")
        round_rect(c, 2, 2, w - 2, 94, 20, fill=CARD, outline="")
        self.stripe = round_rect(c, w - 12, 18, w - 6, 78, 3, fill=self.accent, outline="")
        self.s_title = c.create_text(w - 28, 34, anchor="e", text=getattr(self, "st", "לא נבחר קובץ"),
                                     fill=FG, font=(FONT, 15, "bold"))
        self.s_detail = c.create_text(w - 28, 64, anchor="e", width=w - 70, justify="right",
                                      text=getattr(self, "sd", "בחר קובץ vbmeta כדי להתחיל"),
                                      fill=MUTED, font=(FONT, 10))

    def draw_bar(self):
        b, w = self.bar, self.bar.winfo_width()
        b.delete("all")
        round_rect(b, 0, 0, w, 6, 3, fill=CARD, outline="")
        if self.bar_pct > 0:
            round_rect(b, w * (1 - self.bar_pct), 0, w, 6, 3, fill=GREEN, outline="")

    def fill_bar(self, i=0):
        self.bar_pct = i / 20
        self.draw_bar()
        if i < 20:
            self.after(18, self.fill_bar, i + 1)

    def set_status(self, title, detail, color):
        self.st, self.sd = title, detail
        old = self.accent
        self.accent = color
        self.card.itemconfig(self.s_title, text=title)
        self.card.itemconfig(self.s_detail, text=detail)
        Anim(self.card, 12, 15).run(old, color, lambda c: self.card.itemconfig(self.stripe, fill=c))

    # לוגיקה
    def choose(self):
        p = filedialog.askopenfilename(filetypes=[("vbmeta images", "*.img"), ("כל הקבצים", "*.*")])
        if p:
            self.load(p)

    def load(self, path_str):
        self.data = self.path = None
        self.go.set_enabled(False)
        self.out.config(text="")
        self.bar_pct = 0
        self.draw_bar()
        path = Path(path_str.strip('"'))
        if not path.exists():
            return self.set_status("הקובץ לא קיים", str(path), RED)
        try:
            data = bytearray(path.read_bytes())
        except Exception as e:
            return self.set_status("שגיאה בקריאת הקובץ", str(e), RED)
        self.fname = path.name
        self.drop.itemconfig(self.drop_title, text=path.name)
        self.drop.itemconfig(self.drop_icon, text="📄")
        if data[:4] != b"AVB0":
            return self.set_status("קובץ vbmeta לא חוקי", "הקובץ אינו מתחיל בחתימת AVB0", RED)
        if data[123] & 3:
            return self.set_status("AVB כבר מושבת", "אין צורך בשינוי בקובץ זה", AMBER)
        self.data, self.path = data, path
        self.set_status("AVB פעיל", "לחץ על ״השבת AVB״ כדי ליצור קובץ מושבת", BLUE)
        self.go.set_enabled(True)

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
            return self.set_status("שגיאה בשמירה", str(e), RED)
        self.data = None
        self.go.set_enabled(False)
        self.fill_bar()
        self.set_status("AVB הושבת בהצלחה ✓", "הקובץ המושבת נשמר", GREEN)
        self.out.config(text=f"נשמר ב: {out}")


if __name__ == "__main__":
    App().mainloop()
