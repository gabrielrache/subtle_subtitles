import tkinter as tk
from tkinter import ttk
from opencv import CONFIG

class App(tk.Tk):
    def __init__(self, recapturar_callback, toggle_pause_callback, ler_callback, sair_callback):
        super().__init__()

        self.title("Tradução de Legendas")
        self.geometry("1000x700")
        self.minsize(1000, 700)

        # callbacks do main.py
        self.recapturar_area = recapturar_callback
        self.toggle_pause = toggle_pause_callback
        self.ler_novamente = ler_callback
        self.sair = sair_callback

        # UI
        self.main = Main(self)
        self.menu = Menu(self)

    def update_texts(self, texto_en: str, texto_pt: str):
        self.main.update_texts(texto_en, texto_pt)

    def update_preview(self, png_bytes: bytes):
        self.main.update_preview(png_bytes)


class Menu(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.place(x=0, rely=0.85, relwidth=1, relheight=0.15)
        self.create_widgets()

    def create_widgets(self):
        # ===== Linha 1: Botões =====
        row_buttons = ttk.Frame(self)
        row_buttons.pack(side="top", fill="x", pady=(5, 2))

        row_buttons.columnconfigure((0, 1, 2, 3), weight=1, uniform="btn")

        ttk.Button(
            row_buttons, text="Recapturar área", command=self.parent.recapturar_area
        ).grid(row=0, column=0, padx=5, sticky="ew")

        ttk.Button(
            row_buttons, text="Pausar/Retomar", command=self.parent.toggle_pause
        ).grid(row=0, column=1, padx=5, sticky="ew")

        ttk.Button(
            row_buttons, text="Ler novamente", command=self.parent.ler_novamente
        ).grid(row=0, column=2, padx=5, sticky="ew")

        ttk.Button(
            row_buttons, text="Sair", command=self.parent.sair
        ).grid(row=0, column=3, padx=5, sticky="ew")

        # ===== Linha 2: Sliders =====
        row_sliders = ttk.Frame(self)
        row_sliders.pack(side="top", fill="x", pady=(2, 5), padx=10)

        for c in range(6):
            row_sliders.columnconfigure(c, weight=1, uniform="sliders")

        def add_slider(col_index, label, from_, to, value, key, tooltip_text):
            col = ttk.Frame(row_sliders, padding=(6, 0))  # padding interno
            col.grid(row=0, column=col_index, sticky="ew", padx=4)  # espaço entre sliders

            ttk.Label(col, text=label).pack()

            info = ttk.Frame(col)
            info.pack(fill="x", pady=(2, 0))

            lbl_min = ttk.Label(info, text=f"{from_:.2f}")
            lbl_min.pack(side="left")

            lbl_val = ttk.Label(info, text=f"{value:.2f}", font=("Segoe UI", 9, "bold"))
            lbl_val.pack(side="left", expand=True)

            lbl_max = ttk.Label(info, text=f"{to:.2f}")
            lbl_max.pack(side="right")

            var = tk.DoubleVar(value=value)

            def on_change(v):
                try:
                    fv = float(v)
                except Exception:
                    return

                CONFIG.update(**{key: fv})
                lbl_val.config(text=f"{fv:.2f}")

            scale = ttk.Scale(
                col,
                from_=from_,
                to=to,
                orient="horizontal",
                variable=var,
                command=on_change
            )
            scale.pack(fill="x")

            Tooltip(scale, tooltip_text)

        add_slider(0, "Resize", 1.0, 4.0, 4.0, "resize_fx",
                   "Aumenta a escala da imagem antes do OCR.\n"
                   "Maior = melhor para letras pequenas, mas mais lento.")

        add_slider(1, "CLAHE", 0.5, 4.0, 2.0, "clahe_clip",
                   "Aumenta contraste local (CLAHE).\n"
                   "Ajuda a destacar pontuação e bordas.")

        add_slider(2, "Sharp", 0.0, 2.0, 1.11, "sharpen_strength",
                   "Controla nitidez (sharpen).\n"
                   "Excesso pode gerar ruído.")

        add_slider(3, "Diff", 0.1, 6.0, 2.0, "diff_threshold",
                   "Sensibilidade de mudança entre frames.\n"
                   "Menor = atualiza mais vezes.")

        add_slider(4, "text_th", 0.3, 0.9, 0.61, "text_threshold",
                   "EasyOCR text_threshold.\n"
                   "Maior = mais seletivo.")

        add_slider(5, "low_txt", 0.1, 0.6, 0.2, "low_text",
                   "EasyOCR low_text.\n"
                   "Menor = pega texto fraco, mas pode vir ruído.")


class Main(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.place(x=0, y=0, relwidth=1, relheight=0.9)

        self._tk_preview_img = None

        # preview da imagem do OCR
        self.label_preview = tk.Label(
            self,
            text="Prévia OCR (imagem)",
            bg="#111"
        )
        self.label_preview.pack(expand=False, fill="both", padx=10, pady=(10, 5))

        # texto em inglês (OCR)
        self.label_en = tk.Label(
            self,
            text="Aguardando legenda (EN)...",
            fg="#dddddd",
            bg="#111",
            font=("Segoe UI Semibold", 14),
            wraplength=960,
            justify="center"
        )
        self.label_en.pack(expand=False, fill="both", padx=10, pady=(0, 5))

        # tradução PT
        self.label_pt = tk.Label(
            self,
            text="Aguardando tradução (PT)...",
            fg="white",
            bg="#111",
            font=("Segoe UI Semibold", 20),
            wraplength=960,
            justify="center"
        )
        self.label_pt.pack(expand=True, fill="both", padx=10, pady=(0, 10))

    def update_texts(self, texto_en: str, texto_pt: str):
        self.label_en.config(text=texto_en)
        self.label_pt.config(text=texto_pt)

    def update_preview(self, png_bytes: bytes):
        if not png_bytes:
            return

        self._tk_preview_img = tk.PhotoImage(data=png_bytes)
        self.label_preview.config(image=self._tk_preview_img, text="")


class Tooltip:
    """
    Tooltip simples para Tkinter/ttk.
    Mostra uma janelinha ao passar o mouse sobre um widget.
    """

    def __init__(self, widget, text: str, delay_ms: int = 400):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms

        self._after_id = None
        self._tip_window = None

        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<Motion>", self._on_motion, add="+")

    def _on_enter(self, _event=None):
        self._schedule()

    def _on_leave(self, _event=None):
        self._cancel()
        self._hide()

    def _on_motion(self, _event=None):
        # opcional: se quiser reposicionar conforme o mouse, pode fazer aqui
        pass

    def _schedule(self):
        self._cancel()
        self._after_id = self.widget.after(self.delay_ms, self._show)

    def _cancel(self):
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _show(self):
        if self._tip_window is not None:
            return

        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6

        self._tip_window = tk.Toplevel(self.widget)
        self._tip_window.wm_overrideredirect(True)
        self._tip_window.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            self._tip_window,
            text=self.text,
            justify="left",
            bg="#222",
            fg="white",
            padx=8,
            pady=6,
            font=("Segoe UI", 9)
        )
        label.pack()

    def _hide(self):
        if self._tip_window is not None:
            try:
                self._tip_window.destroy()
            except Exception:
                pass
            self._tip_window = None
