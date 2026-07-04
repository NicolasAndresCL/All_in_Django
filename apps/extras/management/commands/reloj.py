"""
Management command: reloj

Reloj de escritorio + cronómetro (tkinter, solo stdlib). Port compacto del
`reloj` de all_in_one (ventana única). Se ejecuta localmente, no por HTTP:

    python manage.py reloj
"""

import time
import tkinter as tk

from django.core.management.base import BaseCommand

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
BG, PANEL, TXT, DIM, GREEN, AMBER, RED = (
    "#1e1e1e", "#252526", "#d4d4d4", "#858585", "#4ec9b0", "#d7ba7d", "#f48771")


class _Reloj:
    """Ventana con hora actual + cronómetro Iniciar/Pausar/Reiniciar."""

    def __init__(self, root):
        self.root = root
        self.running = False
        self.start = 0.0
        self.acc = 0.0
        root.configure(bg=BG)
        root.title("Reloj + Cronómetro")
        root.attributes("-topmost", True)

        self.clock = tk.Label(root, text="00:00:00", bg=BG, fg=TXT, font=("Consolas", 30, "bold"))
        self.clock.pack(padx=24, pady=(16, 0))
        self.date = tk.Label(root, text="", bg=BG, fg=DIM, font=("Consolas", 10))
        self.date.pack()
        self.sw = tk.Label(root, text="00:00:00.0", bg=BG, fg=GREEN, font=("Consolas", 24, "bold"))
        self.sw.pack(pady=(12, 6))

        btns = tk.Frame(root, bg=BG)
        btns.pack(padx=16, pady=(0, 16), fill="x")
        for txt, color, cmd in [("▶ Iniciar", GREEN, self._start),
                                ("❚❚ Pausar", AMBER, self._pause),
                                ("↺ Reiniciar", RED, self._reset)]:
            tk.Button(btns, text=txt, fg=color, bg=PANEL, bd=0, padx=8, pady=6,
                      activebackground=PANEL, command=cmd).pack(side="left", expand=True, fill="x", padx=2)

        self._tick_clock()
        self._tick_sw()

    def _elapsed(self):
        return self.acc + (time.monotonic() - self.start if self.running else 0)

    def _start(self):
        if not self.running:
            self.running = True
            self.start = time.monotonic()

    def _pause(self):
        if self.running:
            self.acc += time.monotonic() - self.start
            self.running = False

    def _reset(self):
        self.running = False
        self.acc = 0.0

    def _tick_clock(self):
        now = time.localtime()
        self.clock.config(text=time.strftime("%H:%M:%S", now))
        self.date.config(text=f"{DIAS[now.tm_wday]} {now.tm_mday} de {MESES[now.tm_mon - 1]} de {now.tm_year}")
        self.root.after(250, self._tick_clock)

    def _tick_sw(self):
        s = self._elapsed()
        self.sw.config(text=f"{int(s // 3600):02d}:{int(s % 3600 // 60):02d}:{int(s % 60):02d}.{int(s * 10 % 10)}")
        self.root.after(50, self._tick_sw)


class Command(BaseCommand):
    """Abre la ventana tkinter del reloj + cronómetro y entra en su mainloop."""

    help = "Abre el reloj de escritorio con cronómetro (tkinter)."

    def handle(self, *args, **opts):
        root = tk.Tk()
        _Reloj(root)
        root.mainloop()
