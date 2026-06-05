# -*- coding: utf-8 -*-
"""
Репетитор — учёт учеников и занятий.
Локальное офлайн-приложение. Все данные хранятся в файле tutor_data.json
в той же папке, где лежит программа (рядом с .exe).
Чистый Python + tkinter, без внешних зависимостей.
"""

import os
import sys
import json
import uuid
from datetime import date, datetime, timedelta

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

# ----------------------------------------------------------------------------
# Где лежат данные: всегда рядом с .exe / скриптом
# ----------------------------------------------------------------------------
def get_app_dir():
    if getattr(sys, "frozen", False):          # запущено как собранный .exe
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

DATA_FILE = os.path.join(get_app_dir(), "tutor_data.json")

# ----------------------------------------------------------------------------
# Константы оформления и локализации
# ----------------------------------------------------------------------------
APP_TITLE   = "Репетитор — учёт занятий"

WEEKDAYS    = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTHS_GEN  = ["января", "февраля", "марта", "апреля", "мая", "июня",
               "июля", "августа", "сентября", "октября", "ноября", "декабря"]
MONTHS_SHORT = ["янв", "фев", "мар", "апр", "май", "июн",
                "июл", "авг", "сен", "окт", "ноя", "дек"]

STATUS_ORDER  = ["planned", "done", "canceled"]
STATUS_LABELS = {"planned": "Запланировано", "done": "Проведено", "canceled": "Отменено"}
LABEL_TO_STATUS = {v: k for k, v in STATUS_LABELS.items()}

# Палитра цветов для учеников
PALETTE = ["#4f46e5", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444",
           "#8b5cf6", "#ec4899", "#14b8a6", "#f97316", "#6366f1",
           "#84cc16", "#06b6d4"]

# Цвета интерфейса
C_SIDEBAR   = "#1f2937"
C_SIDE_HOV  = "#374151"
C_SIDE_ACT  = "#4f46e5"
C_BG        = "#f3f4f6"
C_CARD      = "#ffffff"
C_TEXT      = "#111827"
C_MUTED     = "#6b7280"
C_ACCENT    = "#4f46e5"
C_GRID      = "#e5e7eb"
C_HEADER    = "#f9fafb"
C_TODAY     = "#eef2ff"
C_DANGER    = "#dc2626"
C_OK        = "#16a34a"

F_BASE   = ("Segoe UI", 10)
F_SMALL  = ("Segoe UI", 9)
F_BOLD   = ("Segoe UI", 10, "bold")
F_H1     = ("Segoe UI", 18, "bold")
F_H2     = ("Segoe UI", 13, "bold")
F_CARDN  = ("Segoe UI", 20, "bold")


# ----------------------------------------------------------------------------
# Вспомогательные функции
# ----------------------------------------------------------------------------
def money(val, cur="€"):
    try:
        val = float(val)
    except (TypeError, ValueError):
        val = 0.0
    if abs(val - round(val)) < 1e-9:
        return f"{int(round(val))} {cur}"
    return f"{val:.2f} {cur}"


def parse_date(s):
    try:
        return date.fromisoformat(s)
    except Exception:
        return None


def monday_of(d):
    return d - timedelta(days=d.weekday())


def new_id():
    return uuid.uuid4().hex[:12]


# ----------------------------------------------------------------------------
# Хранилище данных
# ----------------------------------------------------------------------------
class DataStore:
    def __init__(self, path):
        self.path = path
        self.data = self._default()
        self.load()

    def _default(self):
        return {
            "settings": {"currency": "€", "day_start": 8, "day_end": 22},
            "students": [],
            "lessons": [],
        }

    # --- файл ---------------------------------------------------------------
    def load(self):
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                d = json.load(f)
            base = self._default()
            if isinstance(d.get("settings"), dict):
                base["settings"].update(d["settings"])
            if isinstance(d.get("students"), list):
                base["students"] = d["students"]
            if isinstance(d.get("lessons"), list):
                base["lessons"] = d["lessons"]
            self.data = base
        except Exception as e:
            print("Ошибка чтения данных:", e)

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Ошибка сохранения:", e)

    # --- настройки ----------------------------------------------------------
    @property
    def settings(self):
        return self.data["settings"]

    @property
    def currency(self):
        return self.settings.get("currency", "€")

    def update_settings(self, **kw):
        self.settings.update(kw)
        self.save()

    # --- ученики ------------------------------------------------------------
    def students(self, include_archived=True):
        res = self.data["students"]
        if not include_archived:
            res = [s for s in res if s.get("status") != "archived"]
        return sorted(res, key=lambda s: s.get("name", "").lower())

    def get_student(self, sid):
        for s in self.data["students"]:
            if s["id"] == sid:
                return s
        return None

    def _next_color(self):
        return PALETTE[len(self.data["students"]) % len(PALETTE)]

    def add_student(self, name, contact="", subject="", level="",
                    notes="", price=0.0, status="trial", color=None):
        s = {
            "id": new_id(),
            "name": name.strip(),
            "contact": contact.strip(),
            "subject": subject.strip(),
            "level": level.strip(),
            "notes": notes.strip(),
            "price": float(price or 0),
            "status": status,
            "color": color or self._next_color(),
            "created": date.today().isoformat(),
        }
        self.data["students"].append(s)
        self.save()
        return s

    def update_student(self, sid, **fields):
        s = self.get_student(sid)
        if not s:
            return
        for k, v in fields.items():
            s[k] = v
        self.save()

    def delete_student(self, sid):
        self.data["students"] = [s for s in self.data["students"] if s["id"] != sid]
        self.data["lessons"] = [l for l in self.data["lessons"] if l.get("student_id") != sid]
        self.save()

    # --- занятия ------------------------------------------------------------
    def lessons(self):
        return self.data["lessons"]

    def lessons_in_week(self, monday):
        end = monday + timedelta(days=7)
        out = []
        for l in self.data["lessons"]:
            d = parse_date(l.get("date", ""))
            if d and monday <= d < end:
                out.append(l)
        return out

    def get_lesson(self, lid):
        for l in self.data["lessons"]:
            if l["id"] == lid:
                return l
        return None

    def add_lesson(self, student_id, ldate, hour, duration=1, price=0.0,
                   trial=False, status="planned", notes=""):
        l = {
            "id": new_id(),
            "student_id": student_id,
            "date": ldate.isoformat() if isinstance(ldate, date) else str(ldate),
            "hour": int(hour),
            "duration": int(duration),
            "price": 0.0 if trial else float(price or 0),
            "trial": bool(trial),
            "status": status,
            "notes": notes.strip(),
        }
        self.data["lessons"].append(l)
        self.save()
        return l

    def update_lesson(self, lid, **fields):
        l = self.get_lesson(lid)
        if not l:
            return
        for k, v in fields.items():
            l[k] = v
        if l.get("trial"):
            l["price"] = 0.0
        self.save()

    def delete_lesson(self, lid):
        self.data["lessons"] = [l for l in self.data["lessons"] if l["id"] != lid]
        self.save()

    # --- статистика ---------------------------------------------------------
    def _earned_lessons(self):
        return [l for l in self.data["lessons"]
                if l.get("status") == "done" and not l.get("trial")]

    def total_earned(self):
        return sum(float(l.get("price", 0)) for l in self._earned_lessons())

    def earned_in_month(self, year, month):
        total = 0.0
        for l in self._earned_lessons():
            d = parse_date(l.get("date", ""))
            if d and d.year == year and d.month == month:
                total += float(l.get("price", 0))
        return total

    def planned_sum(self):
        return sum(float(l.get("price", 0)) for l in self.data["lessons"]
                   if l.get("status") == "planned" and not l.get("trial"))

    def earnings_by_month(self, months=6):
        today = date.today()
        buckets = []
        y, m = today.year, today.month
        seq = []
        for _ in range(months):
            seq.append((y, m))
            m -= 1
            if m == 0:
                m = 12
                y -= 1
        seq.reverse()
        for (yy, mm) in seq:
            label = MONTHS_SHORT[mm - 1]
            buckets.append((label, self.earned_in_month(yy, mm)))
        return buckets

    def earnings_by_student(self):
        totals = {}
        for l in self._earned_lessons():
            sid = l.get("student_id")
            totals[sid] = totals.get(sid, 0.0) + float(l.get("price", 0))
        rows = []
        for sid, val in totals.items():
            s = self.get_student(sid)
            name = s["name"] if s else "—"
            rows.append((name, val, (s["color"] if s else C_ACCENT)))
        rows.sort(key=lambda r: r[1], reverse=True)
        return rows

    def student_stats(self, sid):
        done = [l for l in self._earned_lessons() if l.get("student_id") == sid]
        return len(done), sum(float(l.get("price", 0)) for l in done)

    def counts(self):
        students = self.data["students"]
        done_paid = self._earned_lessons()
        done_trial = [l for l in self.data["lessons"]
                      if l.get("status") == "done" and l.get("trial")]
        return {
            "active": sum(1 for s in students if s.get("status") == "active"),
            "trial_people": sum(1 for s in students if s.get("status") == "trial"),
            "done": len(done_paid),
            "done_trial": len(done_trial),
        }

    # --- импорт / экспорт ---------------------------------------------------
    def export_to(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def import_from(self, path):
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict) or "students" not in d or "lessons" not in d:
            raise ValueError("Файл не похож на данные приложения.")
        base = self._default()
        if isinstance(d.get("settings"), dict):
            base["settings"].update(d["settings"])
        base["students"] = d.get("students", [])
        base["lessons"] = d.get("lessons", [])
        self.data = base
        self.save()


# ----------------------------------------------------------------------------
# Маленькие UI-помощники
# ----------------------------------------------------------------------------
def make_card(parent):
    f = tk.Frame(parent, bg=C_CARD, highlightbackground=C_GRID,
                 highlightthickness=1, bd=0)
    return f


def stat_card(parent, title, value_var):
    card = make_card(parent)
    tk.Label(card, text=title, bg=C_CARD, fg=C_MUTED, font=F_SMALL,
             anchor="w").pack(fill="x", padx=14, pady=(12, 0))
    tk.Label(card, textvariable=value_var, bg=C_CARD, fg=C_TEXT,
             font=F_CARDN, anchor="w").pack(fill="x", padx=14, pady=(0, 12))
    return card


# ----------------------------------------------------------------------------
# Диалог ученика
# ----------------------------------------------------------------------------
class StudentDialog(tk.Toplevel):
    def __init__(self, master, store, student=None):
        super().__init__(master)
        self.store = store
        self.student = student
        self.result = None
        self.chosen_color = (student["color"] if student
                             else store._next_color())

        self.title("Профиль ученика" if student else "Новый ученик")
        self.configure(bg=C_BG)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        body = tk.Frame(self, bg=C_BG)
        body.pack(fill="both", expand=True, padx=18, pady=18)

        self.v_name    = tk.StringVar(value=student["name"] if student else "")
        self.v_subject = tk.StringVar(value=student.get("subject", "") if student else "")
        self.v_level   = tk.StringVar(value=student.get("level", "") if student else "")
        self.v_contact = tk.StringVar(value=student.get("contact", "") if student else "")
        self.v_price   = tk.StringVar(value=str(student.get("price", "")) if student else "")
        self.v_status  = tk.StringVar(
            value=("Ученик" if (student and student.get("status") == "active")
                   else "Пробный"))

        self._row(body, "Имя *",        self.v_name,    0)
        self._row(body, "Предмет",      self.v_subject, 1)
        self._row(body, "Класс/уровень", self.v_level,  2)
        self._row(body, "Контакт",      self.v_contact, 3)
        self._row(body, "Цена занятия", self.v_price,   4)

        tk.Label(body, text="Статус", bg=C_BG, fg=C_TEXT, font=F_BASE,
                 anchor="w").grid(row=5, column=0, sticky="w", pady=6)
        ttk.Combobox(body, textvariable=self.v_status, state="readonly",
                     values=["Пробный", "Ученик"], width=26).grid(
                     row=5, column=1, sticky="we", pady=6)

        tk.Label(body, text="Заметки", bg=C_BG, fg=C_TEXT, font=F_BASE,
                 anchor="nw").grid(row=6, column=0, sticky="nw", pady=6)
        self.txt_notes = tk.Text(body, width=30, height=3, font=F_BASE,
                                 relief="solid", bd=1, highlightthickness=0)
        self.txt_notes.grid(row=6, column=1, sticky="we", pady=6)
        if student:
            self.txt_notes.insert("1.0", student.get("notes", ""))

        # выбор цвета
        tk.Label(body, text="Цвет", bg=C_BG, fg=C_TEXT, font=F_BASE,
                 anchor="w").grid(row=7, column=0, sticky="w", pady=6)
        sw = tk.Frame(body, bg=C_BG)
        sw.grid(row=7, column=1, sticky="w", pady=6)
        self.swatches = {}
        for i, col in enumerate(PALETTE):
            b = tk.Frame(sw, bg=col, width=22, height=22, cursor="hand2",
                         highlightthickness=2,
                         highlightbackground=(C_TEXT if col == self.chosen_color else col))
            b.grid(row=i // 6, column=i % 6, padx=3, pady=3)
            b.bind("<Button-1>", lambda e, c=col: self._pick_color(c))
            self.swatches[col] = b

        btns = tk.Frame(self, bg=C_BG)
        btns.pack(fill="x", padx=18, pady=(0, 16))
        tk.Button(btns, text="Сохранить", command=self._ok, bg=C_ACCENT,
                  fg="white", font=F_BOLD, relief="flat", padx=16, pady=6,
                  cursor="hand2").pack(side="right")
        tk.Button(btns, text="Отмена", command=self.destroy, bg="#e5e7eb",
                  fg=C_TEXT, font=F_BASE, relief="flat", padx=16, pady=6,
                  cursor="hand2").pack(side="right", padx=(0, 8))

        body.columnconfigure(1, weight=1)
        self.v_name  # focus
        self.after(50, lambda: self._center(master))

    def _row(self, parent, label, var, r):
        tk.Label(parent, text=label, bg=C_BG, fg=C_TEXT, font=F_BASE,
                 anchor="w").grid(row=r, column=0, sticky="w", pady=6)
        e = tk.Entry(parent, textvariable=var, font=F_BASE, width=30,
                     relief="solid", bd=1, highlightthickness=0)
        e.grid(row=r, column=1, sticky="we", pady=6)
        return e

    def _pick_color(self, col):
        self.chosen_color = col
        for c, w in self.swatches.items():
            w.configure(highlightbackground=(C_TEXT if c == col else c))

    def _center(self, master):
        self.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - self.winfo_width()) // 2
        y = master.winfo_rooty() + (master.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x,0)}+{max(y,0)}")

    def _ok(self):
        name = self.v_name.get().strip()
        if not name:
            messagebox.showwarning("Внимание", "Введите имя ученика.", parent=self)
            return
        try:
            price = float(self.v_price.get().replace(",", ".") or 0)
        except ValueError:
            messagebox.showwarning("Внимание", "Цена должна быть числом.", parent=self)
            return
        status = "active" if self.v_status.get() == "Ученик" else "trial"
        fields = dict(
            name=name,
            subject=self.v_subject.get().strip(),
            level=self.v_level.get().strip(),
            contact=self.v_contact.get().strip(),
            notes=self.txt_notes.get("1.0", "end").strip(),
            price=price,
            status=status,
            color=self.chosen_color,
        )
        if self.student:
            self.store.update_student(self.student["id"], **fields)
        else:
            self.store.add_student(**fields)
        self.result = True
        self.destroy()


# ----------------------------------------------------------------------------
# Диалог занятия
# ----------------------------------------------------------------------------
class LessonDialog(tk.Toplevel):
    def __init__(self, master, store, lesson=None,
                 default_date=None, default_hour=None):
        super().__init__(master)
        self.store = store
        self.lesson = lesson
        self.result = None

        self.title("Занятие" if lesson else "Новое занятие")
        self.configure(bg=C_BG)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        ds = store.settings
        day_start = int(ds.get("day_start", 8))
        day_end = int(ds.get("day_end", 22))
        hours = list(range(day_start, max(day_start + 1, day_end)))

        body = tk.Frame(self, bg=C_BG)
        body.pack(fill="both", expand=True, padx=18, pady=18)

        # список учеников
        self.students = [s for s in store.students() if s.get("status") != "archived"]
        self.disp_to_id = {}
        disp_values = []
        for s in self.students:
            tag = " · пробный" if s.get("status") == "trial" else ""
            d = f"{s['name']}{tag}"
            disp_values.append(d)
            self.disp_to_id[d] = s["id"]

        if lesson:
            ld = parse_date(lesson["date"]) or date.today()
            lh = int(lesson.get("hour", day_start))
            cur_sid = lesson.get("student_id")
            cur_disp = next((d for d, i in self.disp_to_id.items() if i == cur_sid), "")
        else:
            ld = default_date or date.today()
            lh = default_hour if default_hour is not None else day_start
            cur_disp = ""

        self.v_student  = tk.StringVar(value=cur_disp)
        self.v_date     = tk.StringVar(value=ld.isoformat())
        self.v_hour     = tk.IntVar(value=lh if lh in hours else hours[0])
        self.v_dur      = tk.IntVar(value=int(lesson.get("duration", 1)) if lesson else 1)
        self.v_trial    = tk.BooleanVar(value=bool(lesson.get("trial")) if lesson else False)
        self.v_price    = tk.StringVar(value=str(lesson.get("price", "")) if lesson else "")
        self.v_status   = tk.StringVar(
            value=STATUS_LABELS.get(lesson.get("status", "planned"), "Запланировано")
            if lesson else "Запланировано")

        r = 0
        tk.Label(body, text="Ученик *", bg=C_BG, fg=C_TEXT, font=F_BASE,
                 anchor="w").grid(row=r, column=0, sticky="w", pady=6)
        self.cb_student = ttk.Combobox(body, textvariable=self.v_student,
                                       values=disp_values, state="readonly", width=28)
        self.cb_student.grid(row=r, column=1, sticky="we", pady=6)
        self.cb_student.bind("<<ComboboxSelected>>", self._on_student)
        r += 1

        tk.Label(body, text="Дата (ГГГГ-ММ-ДД)", bg=C_BG, fg=C_TEXT, font=F_BASE,
                 anchor="w").grid(row=r, column=0, sticky="w", pady=6)
        drow = tk.Frame(body, bg=C_BG)
        drow.grid(row=r, column=1, sticky="we", pady=6)
        tk.Entry(drow, textvariable=self.v_date, font=F_BASE, width=14,
                 relief="solid", bd=1, highlightthickness=0).pack(side="left")
        tk.Button(drow, text="−", width=2, command=lambda: self._shift_date(-1),
                  relief="flat", bg="#e5e7eb", cursor="hand2").pack(side="left", padx=(8, 2))
        tk.Button(drow, text="+", width=2, command=lambda: self._shift_date(1),
                  relief="flat", bg="#e5e7eb", cursor="hand2").pack(side="left", padx=2)
        r += 1

        tk.Label(body, text="Время", bg=C_BG, fg=C_TEXT, font=F_BASE,
                 anchor="w").grid(row=r, column=0, sticky="w", pady=6)
        trow = tk.Frame(body, bg=C_BG)
        trow.grid(row=r, column=1, sticky="we", pady=6)
        ttk.Combobox(trow, textvariable=self.v_hour, state="readonly", width=6,
                     values=[f"{h:02d}:00" for h in hours]).pack(side="left")
        # Combobox показывает int -> подменим отображение через отдельный StringVar
        self._hours = hours
        self.cb_hour = trow.winfo_children()[0]
        self.cb_hour.configure(values=[f"{h:02d}:00" for h in hours])
        self.cb_hour.set(f"{self.v_hour.get():02d}:00")
        tk.Label(trow, text="   длительность:", bg=C_BG, fg=C_MUTED,
                 font=F_SMALL).pack(side="left")
        ttk.Spinbox(trow, from_=1, to=6, textvariable=self.v_dur, width=4
                    ).pack(side="left", padx=(4, 0))
        tk.Label(trow, text="ч", bg=C_BG, fg=C_MUTED, font=F_SMALL).pack(side="left")
        r += 1

        tk.Label(body, text="Статус", bg=C_BG, fg=C_TEXT, font=F_BASE,
                 anchor="w").grid(row=r, column=0, sticky="w", pady=6)
        ttk.Combobox(body, textvariable=self.v_status, state="readonly",
                     values=[STATUS_LABELS[s] for s in STATUS_ORDER]).grid(
                     row=r, column=1, sticky="we", pady=6)
        r += 1

        self.chk_trial = tk.Checkbutton(
            body, text="Пробное занятие (бесплатно)", variable=self.v_trial,
            bg=C_BG, fg=C_TEXT, font=F_BASE, activebackground=C_BG,
            command=self._on_trial, anchor="w")
        self.chk_trial.grid(row=r, column=0, columnspan=2, sticky="w", pady=(4, 2))
        r += 1

        tk.Label(body, text="Цена", bg=C_BG, fg=C_TEXT, font=F_BASE,
                 anchor="w").grid(row=r, column=0, sticky="w", pady=6)
        self.ent_price = tk.Entry(body, textvariable=self.v_price, font=F_BASE,
                                  width=14, relief="solid", bd=1, highlightthickness=0)
        self.ent_price.grid(row=r, column=1, sticky="w", pady=6)
        r += 1

        tk.Label(body, text="Тема / заметки", bg=C_BG, fg=C_TEXT, font=F_BASE,
                 anchor="nw").grid(row=r, column=0, sticky="nw", pady=6)
        self.txt_notes = tk.Text(body, width=30, height=3, font=F_BASE,
                                 relief="solid", bd=1, highlightthickness=0)
        self.txt_notes.grid(row=r, column=1, sticky="we", pady=6)
        if lesson:
            self.txt_notes.insert("1.0", lesson.get("notes", ""))
        r += 1

        body.columnconfigure(1, weight=1)

        btns = tk.Frame(self, bg=C_BG)
        btns.pack(fill="x", padx=18, pady=(0, 16))
        tk.Button(btns, text="Сохранить", command=self._ok, bg=C_ACCENT,
                  fg="white", font=F_BOLD, relief="flat", padx=16, pady=6,
                  cursor="hand2").pack(side="right")
        tk.Button(btns, text="Отмена", command=self.destroy, bg="#e5e7eb",
                  fg=C_TEXT, font=F_BASE, relief="flat", padx=16, pady=6,
                  cursor="hand2").pack(side="right", padx=(0, 8))
        if lesson:
            tk.Button(btns, text="Удалить", command=self._delete, bg=C_DANGER,
                      fg="white", font=F_BASE, relief="flat", padx=16, pady=6,
                      cursor="hand2").pack(side="left")

        self._on_trial()
        self.after(50, lambda: self._center(master))

    def _center(self, master):
        self.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - self.winfo_width()) // 2
        y = master.winfo_rooty() + (master.winfo_height() - self.winfo_height()) // 4
        self.geometry(f"+{max(x,0)}+{max(y,0)}")

    def _shift_date(self, days):
        d = parse_date(self.v_date.get()) or date.today()
        self.v_date.set((d + timedelta(days=days)).isoformat())

    def _on_student(self, *_):
        sid = self.disp_to_id.get(self.v_student.get())
        s = self.store.get_student(sid) if sid else None
        if not s:
            return
        if not self.lesson:
            if s.get("status") == "trial":
                self.v_trial.set(True)
            elif not self.v_price.get():
                self.v_price.set(str(s.get("price", "")))
        self._on_trial()

    def _on_trial(self):
        if self.v_trial.get():
            self.v_price.set("0")
            self.ent_price.configure(state="disabled")
        else:
            self.ent_price.configure(state="normal")

    def _collect_hour(self):
        txt = self.cb_hour.get()
        try:
            return int(txt.split(":")[0])
        except Exception:
            return self._hours[0]

    def _ok(self):
        sid = self.disp_to_id.get(self.v_student.get())
        if not sid:
            messagebox.showwarning("Внимание", "Выберите ученика.", parent=self)
            return
        d = parse_date(self.v_date.get())
        if not d:
            messagebox.showwarning("Внимание", "Дата в формате ГГГГ-ММ-ДД.", parent=self)
            return
        trial = self.v_trial.get()
        try:
            price = 0.0 if trial else float(self.v_price.get().replace(",", ".") or 0)
        except ValueError:
            messagebox.showwarning("Внимание", "Цена должна быть числом.", parent=self)
            return
        fields = dict(
            student_id=sid,
            ldate=d if not self.lesson else None,
            hour=self._collect_hour(),
            duration=int(self.v_dur.get()),
            price=price,
            trial=trial,
            status=LABEL_TO_STATUS.get(self.v_status.get(), "planned"),
            notes=self.txt_notes.get("1.0", "end").strip(),
        )
        if self.lesson:
            self.store.update_lesson(
                self.lesson["id"],
                student_id=sid, date=d.isoformat(), hour=fields["hour"],
                duration=fields["duration"], price=price, trial=trial,
                status=fields["status"], notes=fields["notes"])
        else:
            self.store.add_lesson(
                student_id=sid, ldate=d, hour=fields["hour"],
                duration=fields["duration"], price=price, trial=trial,
                status=fields["status"], notes=fields["notes"])
        self.result = True
        self.destroy()

    def _delete(self):
        if messagebox.askyesno("Удалить занятие", "Удалить это занятие?", parent=self):
            self.store.delete_lesson(self.lesson["id"])
            self.result = True
            self.destroy()


# ----------------------------------------------------------------------------
# Вид: Календарь (недельная сетка по часам)
# ----------------------------------------------------------------------------
class CalendarView(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=C_BG)
        self.app = app
        self.store = app.store
        self.monday = monday_of(date.today())

        top = tk.Frame(self, bg=C_BG)
        top.pack(fill="x", padx=24, pady=(20, 8))
        tk.Label(top, text="Календарь", bg=C_BG, fg=C_TEXT, font=F_H1).pack(side="left")

        nav = tk.Frame(top, bg=C_BG)
        nav.pack(side="right")
        tk.Button(nav, text="＋ Занятие", command=self.add_lesson, bg=C_ACCENT,
                  fg="white", font=F_BOLD, relief="flat", padx=14, pady=6,
                  cursor="hand2").pack(side="right", padx=(10, 0))
        tk.Button(nav, text="▶", width=3, command=lambda: self.shift_week(1),
                  relief="flat", bg="#e5e7eb", cursor="hand2").pack(side="right", padx=2)
        tk.Button(nav, text="Сегодня", command=self.go_today, relief="flat",
                  bg="#e5e7eb", cursor="hand2", padx=10).pack(side="right", padx=2)
        tk.Button(nav, text="◀", width=3, command=lambda: self.shift_week(-1),
                  relief="flat", bg="#e5e7eb", cursor="hand2").pack(side="right", padx=2)

        self.lbl_range = tk.Label(self, text="", bg=C_BG, fg=C_MUTED, font=F_BOLD)
        self.lbl_range.pack(fill="x", padx=24, pady=(0, 8))

        wrap = make_card(self)
        wrap.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        self.canvas = tk.Canvas(wrap, bg=C_CARD, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.draw())
        self.canvas.bind("<Button-1>", self.on_click)

    # геометрия общая для отрисовки и кликов
    def _layout(self):
        W = max(self.canvas.winfo_width(), 100)
        H = max(self.canvas.winfo_height(), 100)
        gutter, header = 58, 46
        ds = self.store.settings
        d0 = int(ds.get("day_start", 8))
        d1 = int(ds.get("day_end", 22))
        if d1 <= d0:
            d1 = d0 + 1
        nh = d1 - d0
        col_w = (W - gutter) / 7.0
        row_h = (H - header) / nh
        return dict(W=W, H=H, gutter=gutter, header=header,
                    col_w=col_w, row_h=row_h, nh=nh, d0=d0)

    def shift_week(self, n):
        self.monday += timedelta(days=7 * n)
        self.draw()

    def go_today(self):
        self.monday = monday_of(date.today())
        self.draw()

    def add_lesson(self):
        dlg = LessonDialog(self.app, self.store,
                           default_date=date.today(),
                           default_hour=int(self.store.settings.get("day_start", 8)))
        self.wait_window(dlg)
        if dlg.result:
            self.app.refresh_all()

    def _range_label(self):
        start = self.monday
        end = self.monday + timedelta(days=6)
        if start.month == end.month:
            return f"{start.day}–{end.day} {MONTHS_GEN[start.month-1]} {start.year}"
        if start.year == end.year:
            return (f"{start.day} {MONTHS_GEN[start.month-1]} – "
                    f"{end.day} {MONTHS_GEN[end.month-1]} {start.year}")
        return (f"{start.day} {MONTHS_GEN[start.month-1]} {start.year} – "
                f"{end.day} {MONTHS_GEN[end.month-1]} {end.year}")

    def refresh(self):
        self.draw()

    def draw(self):
        c = self.canvas
        c.delete("all")
        lay = self._layout()
        gutter, header = lay["gutter"], lay["header"]
        col_w, row_h, nh, d0 = lay["col_w"], lay["row_h"], lay["nh"], lay["d0"]
        W, H = lay["W"], lay["H"]
        today = date.today()

        self.lbl_range.configure(text=self._range_label())

        # фон рабочей зоны
        c.create_rectangle(0, 0, W, header, fill=C_HEADER, outline="")

        # колонки дней + заголовки
        for col in range(7):
            d = self.monday + timedelta(days=col)
            x0 = gutter + col * col_w
            if d == today:
                c.create_rectangle(x0, header, x0 + col_w, H,
                                   fill=C_TODAY, outline="")
            # заголовок дня
            head_fg = C_ACCENT if d == today else C_TEXT
            c.create_text(x0 + col_w / 2, header / 2 - 8, text=WEEKDAYS[col],
                          fill=C_MUTED, font=F_SMALL)
            c.create_text(x0 + col_w / 2, header / 2 + 9,
                          text=f"{d.day} {MONTHS_SHORT[d.month-1]}",
                          fill=head_fg, font=F_BOLD)

        # горизонтальные линии часов + подписи
        for i in range(nh + 1):
            y = header + i * row_h
            c.create_line(gutter, y, W, y, fill=C_GRID)
            if i < nh:
                c.create_text(gutter - 8, y + 3, text=f"{d0 + i:02d}:00",
                              anchor="ne", fill=C_MUTED, font=F_SMALL)
        # вертикальные линии
        for col in range(8):
            x = gutter + col * col_w
            c.create_line(x, header, x, H, fill=C_GRID)

        # занятия
        week = self.store.lessons_in_week(self.monday)
        for l in week:
            d = parse_date(l["date"])
            if not d:
                continue
            col = (d - self.monday).days
            if not (0 <= col <= 6):
                continue
            hour = int(l.get("hour", d0))
            dur = max(1, int(l.get("duration", 1)))
            row = hour - d0
            if row < 0:
                row = 0
            x0 = gutter + col * col_w + 3
            x1 = gutter + (col + 1) * col_w - 3
            y0 = header + row * row_h + 2
            y1 = header + (row + dur) * row_h - 2

            s = self.store.get_student(l.get("student_id"))
            base_col = s["color"] if s else C_ACCENT
            canceled = l.get("status") == "canceled"
            fill = "#d1d5db" if canceled else base_col
            c.create_rectangle(x0, y0, x1, y1, fill=fill, outline="", width=0)
            # цветная полоска слева
            c.create_rectangle(x0, y0, x0 + 4, y1,
                               fill=("#9ca3af" if canceled else base_col), outline="")

            name = s["name"] if s else "—"
            # примерно по ширине колонки, чтобы текст не переносился
            max_chars = max(6, int((col_w - 18) / 7.5))
            if len(name) > max_chars:
                name = name[:max_chars - 1] + "…"
            txt_fg = "#374151" if canceled else "white"
            c.create_text(x0 + 9, y0 + 5, text=name, anchor="nw",
                          fill=txt_fg, font=F_BOLD)
            sub = "Пробное" if l.get("trial") else money(l.get("price", 0), self.store.currency)
            if l.get("status") == "done":
                sub += "  ✓"
            elif canceled:
                sub = "Отменено"
            if (y1 - y0) > 34:
                c.create_text(x0 + 9, y0 + 22, text=sub, anchor="nw",
                              fill=txt_fg, font=F_SMALL)

    def on_click(self, event):
        lay = self._layout()
        gutter, header = lay["gutter"], lay["header"]
        col_w, row_h, nh, d0 = lay["col_w"], lay["row_h"], lay["nh"], lay["d0"]
        x, y = event.x, event.y
        if x < gutter or y < header:
            return
        col = int((x - gutter) // col_w)
        row = int((y - header) // row_h)
        if not (0 <= col <= 6) or not (0 <= row < nh):
            return
        clicked_date = self.monday + timedelta(days=col)
        clicked_hour = d0 + row

        # есть ли занятие в этом слоте?
        found = None
        for l in self.store.lessons_in_week(self.monday):
            if parse_date(l["date"]) != clicked_date:
                continue
            h = int(l.get("hour", d0))
            dur = max(1, int(l.get("duration", 1)))
            if h <= clicked_hour < h + dur:
                found = l
                break

        if found:
            dlg = LessonDialog(self.app, self.store, lesson=found)
        else:
            dlg = LessonDialog(self.app, self.store,
                               default_date=clicked_date, default_hour=clicked_hour)
        self.wait_window(dlg)
        if dlg.result:
            self.app.refresh_all()


# ----------------------------------------------------------------------------
# Вид: Ученики
# ----------------------------------------------------------------------------
class StudentsView(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=C_BG)
        self.app = app
        self.store = app.store

        top = tk.Frame(self, bg=C_BG)
        top.pack(fill="x", padx=24, pady=(20, 12))
        tk.Label(top, text="Ученики", bg=C_BG, fg=C_TEXT, font=F_H1).pack(side="left")
        tk.Button(top, text="＋ Ученик", command=self.add, bg=C_ACCENT, fg="white",
                  font=F_BOLD, relief="flat", padx=14, pady=6, cursor="hand2"
                  ).pack(side="right")

        card = make_card(self)
        card.pack(fill="both", expand=True, padx=24, pady=(0, 12))

        cols = ("name", "subject", "status", "price", "count", "earned")
        self.tree = ttk.Treeview(card, columns=cols, show="headings", height=12)
        heads = {"name": "Имя", "subject": "Предмет", "status": "Статус",
                 "price": "Цена", "count": "Занятий", "earned": "Заработано"}
        widths = {"name": 200, "subject": 150, "status": 100,
                  "price": 90, "count": 80, "earned": 120}
        for c in cols:
            self.tree.heading(c, text=heads[c])
            anchor = "w" if c in ("name", "subject") else "center"
            self.tree.column(c, width=widths[c], anchor=anchor)
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(card, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<Double-1>", lambda e: self.edit())

        btns = tk.Frame(self, bg=C_BG)
        btns.pack(fill="x", padx=24, pady=(0, 20))
        tk.Button(btns, text="Изменить", command=self.edit, relief="flat",
                  bg="#e5e7eb", padx=14, pady=6, cursor="hand2").pack(side="left")
        tk.Button(btns, text="Перевести в ученики", command=self.promote,
                  relief="flat", bg="#dbeafe", fg="#1e3a8a", padx=14, pady=6,
                  cursor="hand2").pack(side="left", padx=8)
        tk.Button(btns, text="Удалить", command=self.delete, relief="flat",
                  bg="#fee2e2", fg=C_DANGER, padx=14, pady=6,
                  cursor="hand2").pack(side="left")

        self._ids = {}

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return self._ids.get(sel[0])

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        self._ids = {}
        for s in self.store.students():
            cnt, earned = self.store.student_stats(s["id"])
            status = {"active": "Ученик", "trial": "Пробный",
                      "archived": "Архив"}.get(s.get("status"), s.get("status"))
            iid = self.tree.insert("", "end", values=(
                s["name"], s.get("subject", ""), status,
                money(s.get("price", 0), self.store.currency),
                cnt, money(earned, self.store.currency)))
            self._ids[iid] = s["id"]

    def add(self):
        dlg = StudentDialog(self.app, self.store)
        self.wait_window(dlg)
        if dlg.result:
            self.app.refresh_all()

    def edit(self):
        sid = self._selected_id()
        if not sid:
            messagebox.showinfo("Ученики", "Выберите ученика в списке.")
            return
        dlg = StudentDialog(self.app, self.store, student=self.store.get_student(sid))
        self.wait_window(dlg)
        if dlg.result:
            self.app.refresh_all()

    def promote(self):
        sid = self._selected_id()
        if not sid:
            messagebox.showinfo("Ученики", "Выберите пробного ученика.")
            return
        s = self.store.get_student(sid)
        if s.get("status") == "active":
            messagebox.showinfo("Ученики", "Этот человек уже постоянный ученик.")
            return
        price = simpledialog.askfloat(
            "Перевести в ученики",
            f"{s['name']} остаётся заниматься.\nЦена занятия:",
            parent=self.app, minvalue=0,
            initialvalue=float(s.get("price", 0) or 0))
        if price is None:
            return
        self.store.update_student(sid, status="active", price=price)
        self.app.refresh_all()

    def delete(self):
        sid = self._selected_id()
        if not sid:
            messagebox.showinfo("Ученики", "Выберите ученика.")
            return
        s = self.store.get_student(sid)
        if messagebox.askyesno(
                "Удалить ученика",
                f"Удалить «{s['name']}» и все его занятия?\nЭто действие необратимо."):
            self.store.delete_student(sid)
            self.app.refresh_all()


# ----------------------------------------------------------------------------
# Вид: Статистика
# ----------------------------------------------------------------------------
class StatsView(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=C_BG)
        self.app = app
        self.store = app.store

        tk.Label(self, text="Статистика", bg=C_BG, fg=C_TEXT, font=F_H1
                 ).pack(anchor="w", padx=24, pady=(20, 12))

        # карточки
        cards = tk.Frame(self, bg=C_BG)
        cards.pack(fill="x", padx=24)
        self.v_total   = tk.StringVar()
        self.v_month   = tk.StringVar()
        self.v_plan    = tk.StringVar()
        self.v_active  = tk.StringVar()
        defs = [("Всего заработано", self.v_total),
                ("За этот месяц", self.v_month),
                ("Ожидается (план)", self.v_plan),
                ("Активных учеников", self.v_active)]
        for i, (title, var) in enumerate(defs):
            card = stat_card(cards, title, var)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            cards.columnconfigure(i, weight=1)

        self.v_done  = tk.StringVar()
        self.v_trial = tk.StringVar()
        small = tk.Frame(self, bg=C_BG)
        small.pack(fill="x", padx=24, pady=(10, 4))
        tk.Label(small, textvariable=self.v_done, bg=C_BG, fg=C_MUTED,
                 font=F_BASE).pack(side="left")
        tk.Label(small, text="     ", bg=C_BG).pack(side="left")
        tk.Label(small, textvariable=self.v_trial, bg=C_BG, fg=C_MUTED,
                 font=F_BASE).pack(side="left")

        # графики
        charts = tk.Frame(self, bg=C_BG)
        charts.pack(fill="both", expand=True, padx=24, pady=(10, 20))

        left = make_card(charts)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        tk.Label(left, text="Заработок по месяцам", bg=C_CARD, fg=C_TEXT,
                 font=F_H2).pack(anchor="w", padx=14, pady=(12, 0))
        self.cv_month = tk.Canvas(left, bg=C_CARD, highlightthickness=0, height=240)
        self.cv_month.pack(fill="both", expand=True, padx=8, pady=8)
        self.cv_month.bind("<Configure>", lambda e: self._draw_month_chart())

        right = make_card(charts)
        right.pack(side="left", fill="both", expand=True, padx=(8, 0))
        tk.Label(right, text="Топ учеников по заработку", bg=C_CARD, fg=C_TEXT,
                 font=F_H2).pack(anchor="w", padx=14, pady=(12, 0))
        self.cv_top = tk.Canvas(right, bg=C_CARD, highlightthickness=0, height=240)
        self.cv_top.pack(fill="both", expand=True, padx=8, pady=8)
        self.cv_top.bind("<Configure>", lambda e: self._draw_top_chart())

    def refresh(self):
        cur = self.store.currency
        today = date.today()
        self.v_total.set(money(self.store.total_earned(), cur))
        self.v_month.set(money(self.store.earned_in_month(today.year, today.month), cur))
        self.v_plan.set(money(self.store.planned_sum(), cur))
        cnt = self.store.counts()
        self.v_active.set(str(cnt["active"]))
        self.v_done.set(f"Проведено занятий: {cnt['done']}")
        self.v_trial.set(f"Пробных проведено: {cnt['done_trial']}")
        self.after(30, self._draw_month_chart)
        self.after(30, self._draw_top_chart)

    def _draw_month_chart(self):
        c = self.cv_month
        c.delete("all")
        W = max(c.winfo_width(), 100)
        H = max(c.winfo_height(), 100)
        data = self.store.earnings_by_month(6)
        cur = self.store.currency
        if not data or all(v == 0 for _, v in data):
            c.create_text(W / 2, H / 2, text="Пока нет данных",
                          fill=C_MUTED, font=F_BASE)
            return
        pad_l, pad_b, pad_t, pad_r = 16, 28, 24, 16
        area_w = W - pad_l - pad_r
        area_h = H - pad_b - pad_t
        n = len(data)
        maxv = max(v for _, v in data) or 1
        slot = area_w / n
        bw = slot * 0.55
        base_y = H - pad_b
        c.create_line(pad_l, base_y, W - pad_r, base_y, fill=C_GRID)
        for i, (label, val) in enumerate(data):
            cx = pad_l + slot * i + slot / 2
            bh = (val / maxv) * area_h
            x0, x1 = cx - bw / 2, cx + bw / 2
            y0 = base_y - bh
            c.create_rectangle(x0, y0, x1, base_y, fill=C_ACCENT, outline="")
            if val > 0:
                c.create_text(cx, y0 - 8, text=money(val, cur),
                              fill=C_TEXT, font=F_SMALL)
            c.create_text(cx, base_y + 14, text=label, fill=C_MUTED, font=F_SMALL)

    def _draw_top_chart(self):
        c = self.cv_top
        c.delete("all")
        W = max(c.winfo_width(), 100)
        H = max(c.winfo_height(), 100)
        rows = self.store.earnings_by_student()[:6]
        cur = self.store.currency
        if not rows:
            c.create_text(W / 2, H / 2, text="Пока нет данных",
                          fill=C_MUTED, font=F_BASE)
            return
        pad_l, pad_r, pad_t = 14, 90, 14
        name_w = 110
        bar_x0 = pad_l + name_w
        bar_max = W - pad_r - bar_x0
        maxv = max(v for _, v, _ in rows) or 1
        row_h = min(40, (H - pad_t) / len(rows))
        for i, (name, val, col) in enumerate(rows):
            cy = pad_t + row_h * i + row_h / 2
            nm = name if len(name) <= 14 else name[:13] + "…"
            c.create_text(pad_l, cy, text=nm, anchor="w", fill=C_TEXT, font=F_SMALL)
            bw = (val / maxv) * bar_max
            c.create_rectangle(bar_x0, cy - 9, bar_x0 + max(bw, 2), cy + 9,
                               fill=col, outline="")
            c.create_text(bar_x0 + bw + 8, cy, text=money(val, cur),
                          anchor="w", fill=C_MUTED, font=F_SMALL)


# ----------------------------------------------------------------------------
# Вид: Настройки / Данные
# ----------------------------------------------------------------------------
class SettingsView(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=C_BG)
        self.app = app
        self.store = app.store

        tk.Label(self, text="Настройки", bg=C_BG, fg=C_TEXT, font=F_H1
                 ).pack(anchor="w", padx=24, pady=(20, 12))

        card = make_card(self)
        card.pack(fill="x", padx=24)
        inner = tk.Frame(card, bg=C_CARD)
        inner.pack(fill="x", padx=18, pady=18)

        self.v_cur = tk.StringVar(value=self.store.currency)
        self.v_d0 = tk.IntVar(value=int(self.store.settings.get("day_start", 8)))
        self.v_d1 = tk.IntVar(value=int(self.store.settings.get("day_end", 22)))

        tk.Label(inner, text="Валюта", bg=C_CARD, fg=C_TEXT, font=F_BASE,
                 anchor="w").grid(row=0, column=0, sticky="w", pady=6)
        tk.Entry(inner, textvariable=self.v_cur, width=8, relief="solid", bd=1,
                 highlightthickness=0).grid(row=0, column=1, sticky="w", pady=6)

        tk.Label(inner, text="Календарь с", bg=C_CARD, fg=C_TEXT, font=F_BASE,
                 anchor="w").grid(row=1, column=0, sticky="w", pady=6)
        hf = tk.Frame(inner, bg=C_CARD)
        hf.grid(row=1, column=1, sticky="w", pady=6)
        ttk.Spinbox(hf, from_=0, to=23, textvariable=self.v_d0, width=5).pack(side="left")
        tk.Label(hf, text=" до ", bg=C_CARD, fg=C_TEXT).pack(side="left")
        ttk.Spinbox(hf, from_=1, to=24, textvariable=self.v_d1, width=5).pack(side="left")
        tk.Label(hf, text=" часов", bg=C_CARD, fg=C_MUTED, font=F_SMALL).pack(side="left")

        tk.Button(inner, text="Сохранить настройки", command=self.save_settings,
                  bg=C_ACCENT, fg="white", font=F_BOLD, relief="flat",
                  padx=14, pady=6, cursor="hand2").grid(
                  row=2, column=0, columnspan=2, sticky="w", pady=(12, 0))

        # данные
        tk.Label(self, text="Данные", bg=C_BG, fg=C_TEXT, font=F_H2
                 ).pack(anchor="w", padx=24, pady=(20, 8))
        card2 = make_card(self)
        card2.pack(fill="x", padx=24)
        inner2 = tk.Frame(card2, bg=C_CARD)
        inner2.pack(fill="x", padx=18, pady=18)

        tk.Label(inner2,
                 text="Все данные автоматически сохраняются в файл рядом с программой:",
                 bg=C_CARD, fg=C_MUTED, font=F_SMALL, anchor="w",
                 justify="left").pack(anchor="w")
        tk.Label(inner2, text=DATA_FILE, bg=C_CARD, fg=C_TEXT, font=F_SMALL,
                 anchor="w", wraplength=720, justify="left").pack(anchor="w", pady=(2, 12))

        brow = tk.Frame(inner2, bg=C_CARD)
        brow.pack(anchor="w")
        tk.Button(brow, text="⬇ Экспорт (сохранить копию)", command=self.export,
                  relief="flat", bg="#e5e7eb", padx=14, pady=6,
                  cursor="hand2").pack(side="left")
        tk.Button(brow, text="⬆ Импорт (загрузить и применить)", command=self.do_import,
                  relief="flat", bg="#dbeafe", fg="#1e3a8a", padx=14, pady=6,
                  cursor="hand2").pack(side="left", padx=8)

    def refresh(self):
        self.v_cur.set(self.store.currency)
        self.v_d0.set(int(self.store.settings.get("day_start", 8)))
        self.v_d1.set(int(self.store.settings.get("day_end", 22)))

    def save_settings(self):
        d0, d1 = int(self.v_d0.get()), int(self.v_d1.get())
        if d1 <= d0:
            messagebox.showwarning("Настройки",
                                   "Время окончания должно быть больше начала.")
            return
        self.store.update_settings(currency=self.v_cur.get().strip() or "€",
                                   day_start=d0, day_end=d1)
        self.app.refresh_all()
        messagebox.showinfo("Настройки", "Сохранено.")

    def export(self):
        path = filedialog.asksaveasfilename(
            title="Сохранить копию данных",
            defaultextension=".json",
            initialfile=f"repetitor_backup_{date.today().isoformat()}.json",
            filetypes=[("JSON", "*.json"), ("Все файлы", "*.*")])
        if not path:
            return
        try:
            self.store.export_to(path)
            messagebox.showinfo("Экспорт", "Копия сохранена.")
        except Exception as e:
            messagebox.showerror("Экспорт", f"Не удалось сохранить:\n{e}")

    def do_import(self):
        path = filedialog.askopenfilename(
            title="Выбрать файл данных",
            filetypes=[("JSON", "*.json"), ("Все файлы", "*.*")])
        if not path:
            return
        if not messagebox.askyesno(
                "Импорт",
                "Текущие данные будут заменены данными из файла. Продолжить?"):
            return
        try:
            self.store.import_from(path)
            self.app.refresh_all()
            messagebox.showinfo("Импорт", "Данные загружены и применены.")
        except Exception as e:
            messagebox.showerror("Импорт", f"Не удалось загрузить:\n{e}")


# ----------------------------------------------------------------------------
# Главное окно
# ----------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.store = DataStore(DATA_FILE)

        self.title(APP_TITLE)
        self.geometry("1140x740")
        self.minsize(960, 620)
        self.configure(bg=C_BG)

        self._setup_style()

        # боковая панель
        side = tk.Frame(self, bg=C_SIDEBAR, width=190)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        tk.Label(side, text="Репетитор", bg=C_SIDEBAR, fg="white",
                 font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=20, pady=(22, 2))
        tk.Label(side, text="учёт занятий", bg=C_SIDEBAR, fg="#9ca3af",
                 font=F_SMALL).pack(anchor="w", padx=20, pady=(0, 20))

        self.nav_buttons = {}
        self.container = tk.Frame(self, bg=C_BG)
        self.container.pack(side="left", fill="both", expand=True)
        self.container.rowconfigure(0, weight=1)
        self.container.columnconfigure(0, weight=1)

        self.views = {
            "calendar": CalendarView(self.container, self),
            "students": StudentsView(self.container, self),
            "stats":    StatsView(self.container, self),
            "settings": SettingsView(self.container, self),
        }
        for v in self.views.values():
            v.grid(row=0, column=0, sticky="nsew")

        for key, label in [("calendar", "🗓  Календарь"),
                           ("students", "👥  Ученики"),
                           ("stats", "📊  Статистика"),
                           ("settings", "⚙  Настройки")]:
            b = tk.Button(side, text=label, anchor="w", bg=C_SIDEBAR, fg="#e5e7eb",
                          font=F_BASE, relief="flat", bd=0, padx=20, pady=10,
                          activebackground=C_SIDE_HOV, activeforeground="white",
                          cursor="hand2", command=lambda k=key: self.show(k))
            b.pack(fill="x")
            b.bind("<Enter>", lambda e, btn=b, k=key: self._hover(btn, k, True))
            b.bind("<Leave>", lambda e, btn=b, k=key: self._hover(btn, k, False))
            self.nav_buttons[key] = b

        self.current = None
        self.show("calendar")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_style(self):
        st = ttk.Style()
        try:
            st.theme_use("clam")
        except Exception:
            pass
        st.configure("Treeview", font=F_BASE, rowheight=28,
                     background=C_CARD, fieldbackground=C_CARD, foreground=C_TEXT)
        st.configure("Treeview.Heading", font=F_BOLD, background=C_HEADER,
                     foreground=C_TEXT)
        st.map("Treeview", background=[("selected", "#e0e7ff")],
               foreground=[("selected", C_TEXT)])

    def _hover(self, btn, key, entering):
        if key == self.current:
            return
        btn.configure(bg=C_SIDE_HOV if entering else C_SIDEBAR)

    def show(self, key):
        self.current = key
        for k, b in self.nav_buttons.items():
            if k == key:
                b.configure(bg=C_SIDE_ACT, fg="white")
            else:
                b.configure(bg=C_SIDEBAR, fg="#e5e7eb")
        view = self.views[key]
        view.refresh()
        view.tkraise()

    def refresh_all(self):
        for v in self.views.values():
            v.refresh()

    def _on_close(self):
        self.store.save()
        self.destroy()


# ----------------------------------------------------------------------------
# Самотест логики (без графики): python tutor_app.py --selftest
# ----------------------------------------------------------------------------
def _selftest():
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), "tutor_selftest.json")
    if os.path.exists(tmp):
        os.remove(tmp)
    store = DataStore(tmp)
    s1 = store.add_student("Аня", subject="Математика", price=20, status="trial")
    s2 = store.add_student("Боря", subject="Физика", price=25, status="active")
    today = date.today()
    # пробное (бесплатно)
    store.add_lesson(s1["id"], today, 10, trial=True, status="done")
    # перевели в ученики
    store.update_student(s1["id"], status="active", price=20)
    store.add_lesson(s1["id"], today, 11, price=20, status="done")
    store.add_lesson(s2["id"], today, 12, price=25, status="done")
    store.add_lesson(s2["id"], today + timedelta(days=1), 12, price=25, status="planned")
    assert abs(store.total_earned() - 45.0) < 1e-6, store.total_earned()
    assert abs(store.planned_sum() - 25.0) < 1e-6
    c = store.counts()
    assert c["active"] == 2 and c["done"] == 2 and c["done_trial"] == 1, c
    rows = store.earnings_by_student()
    assert rows[0][0] in ("Аня", "Боря")
    # экспорт/импорт
    exp = tmp + ".bak"
    store.export_to(exp)
    store2 = DataStore(tmp)
    store2.import_from(exp)
    assert abs(store2.total_earned() - 45.0) < 1e-6
    assert len(store2.lessons_in_week(monday_of(today))) >= 3
    print("SELFTEST OK — заработано:", store.total_earned(),
          store.currency, "| занятий:", len(store.lessons()))


def main():
    if "--selftest" in sys.argv:
        _selftest()
        return
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
