import tkinter as tk
from tkinter import ttk
import re

from opencv import CONFIG
from dictionary import buscar_significado_pt


class App(tk.Tk):
    def __init__(self, recapturar_callback, toggle_pause_callback, ler_callback, sair_callback):
        super().__init__()

        self.title("Tradução de Legendas")
        self.geometry("1000x600")
        self.minsize(1000, 600)
        self.on_texto_en_editado = None

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

    def registrar_callback_edicao(self, callback):
        self.on_texto_en_editado = callback

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

        self.parent = parent  # <-- referência ao App (Tk)

        self.place(x=0, y=0, relwidth=1, relheight=0.9)

        self._tk_preview_img = None

        self.texto_en_atual = ""
        self._editando_en = False

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
            font=("Segoe UI Semibold", 16),  # ⬆ fonte maior
            wraplength=960,
            justify="center",
            pady=12  # ⬆ altura visual
        )

        self.label_en.pack(expand=False, fill="both", padx=10, pady=(0, 5))

        self.label_en.bind("<Button-1>", self._entrar_modo_edicao)

        # ===== Widgets de edição inline (inicialmente ocultos) =====
        self.edit_frame = tk.Frame(
            self,
            bg="#1e90ff",
            highlightthickness=2,
            highlightbackground="#1e90ff"
        )

        self.edit_inner = tk.Frame(self.edit_frame, bg="#111")
        self.edit_inner.pack(fill="both", expand=True, padx=3, pady=3)

        # ===== Área de texto (esquerda) =====
        self.text_edit = tk.Text(
            self.edit_inner,
            font=("Segoe UI Semibold", 16),
            wrap="word",
            relief="flat",
            bg="#111",
            fg="white",
            insertbackground="white",
            insertwidth=2
        )

        self.text_edit.bind("<Return>", self._confirmar_edicao)

        # Shift+Enter quebra linha normalmente
        self.text_edit.bind("<Shift-Return>", self._quebra_linha)

        # ===== Área do botão =====
        btn_frame = tk.Frame(self.edit_inner, bg="#111")

        btn_frame.pack(
            side="right",
            fill="y",
            padx=(6, 10),
            pady=10
        )

        self.text_edit.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(10, 6),
            pady=10
        )

        self.btn_apply = ttk.Button(
            btn_frame,
            text="Aplicar",
            command=self._confirmar_edicao
        )
        self.btn_apply.pack(fill="x", ipady=6)

        self.text_pt = tk.Text(
            self,
            height=4,
            bg="#111",
            fg="white",
            font=("Segoe UI Semibold", 22),
            wrap="word",
            relief="flat",
            bd=0
        )
        self.text_pt.pack(expand=True, fill="both", padx=10, pady=(0, 30))

        # deixa somente leitura (mas vamos habilitar temporariamente quando atualizar)
        self.text_pt.config(state="disabled")

    def _entrar_modo_edicao(self, _event=None):
        if self._editando_en:
            return

        self._editando_en = True

        # garante layout pronto
        self.update_idletasks()

        y_inicio = self.label_en.winfo_y()
        altura_total = self.winfo_height() - y_inicio - 10  # margem inferior

        self.edit_frame.place(
            x=10,
            y=y_inicio,
            relwidth=1.0,
            width=-20,
            height=altura_total
        )

        self.text_edit.delete("1.0", "end")
        self.text_edit.insert("1.0", self.texto_en_atual)
        self.text_edit.focus_set()
        self.text_edit.mark_set("insert", "end")
        self.text_edit.see("insert")

        # self.after(100, self._debug_layout)

    def _confirmar_edicao(self, _event=None):
        novo_texto = self.text_edit.get("1.0", "end").strip()

        if not novo_texto:
            self._cancelar_edicao()
            return

        # atualiza estado interno
        self.texto_en_atual = novo_texto

        # atualiza UI
        self.label_en.config(text=novo_texto)

        # fecha editor
        self.edit_frame.place_forget()
        self._editando_en = False

        # avisa o main.py (se registrado)
        if self.parent.on_texto_en_editado:
            self.parent.on_texto_en_editado(novo_texto)

    def update_texts(self, texto_en, texto_pt):
        if not self._editando_en:
            self.texto_en_atual = texto_en
            self.label_en.config(text=texto_en)

        self.update_translation_clickable(texto_pt)

    def update_preview(self, png_bytes: bytes):
        if not png_bytes:
            return

        self._tk_preview_img = tk.PhotoImage(data=png_bytes)
        self.label_preview.config(image=self._tk_preview_img, text="")

    def _abrir_janela_significado(self, palavra: str):
        palavra = (palavra or "").strip()
        if not palavra:
            return

        # cria o popup como filho do App (isso já ajuda bastante)
        win = tk.Toplevel(self.parent)
        win.title(f"Significado: {palavra}")
        win.minsize(420, 260)
        win.resizable(True, True)

        # mantém "associado" ao App (mesmo grupo de janelas)
        win.transient(self.parent)

        # abre por cima, mas sem travar o app
        try:
            win.attributes("-topmost", True)
            win.after(250, lambda: win.attributes("-topmost", False))
        except Exception:
            pass

        # ==========================================================
        # POSICIONAMENTO GARANTIDO SOBRE O APP (monitor correto)
        # ==========================================================
        def posicionar_sobre_app():
            # garante geometria atualizada
            self.parent.update_idletasks()
            win.update_idletasks()

            # tenta pegar a geometria real do app: "1000x700+1920+120"
            geo = self.parent.wm_geometry()

            m = re.match(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)", geo)
            if not m:
                # fallback seguro
                app_x = self.parent.winfo_rootx()
                app_y = self.parent.winfo_rooty()
                app_w = self.parent.winfo_width()
                app_h = self.parent.winfo_height()
            else:
                app_w = int(m.group(1))
                app_h = int(m.group(2))
                app_x = int(m.group(3))
                app_y = int(m.group(4))

            w, h = 600, 380
            x = app_x + (app_w // 2) - (w // 2)
            y = app_y + (app_h // 2) - (h // 2)

            win.geometry(f"{w}x{h}+{x}+{y}")

            try:
                win.lift()
                win.focus_force()
            except Exception:
                pass

        # agenda para depois do Tk realmente "materializar" a janela
        win.after(1, posicionar_sobre_app)

        # UI
        frame = ttk.Frame(win, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text=f"Palavra: {palavra}",
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w")

        txt = tk.Text(frame, wrap="word", font=("Segoe UI", 11))
        txt.pack(expand=True, fill="both", pady=(10, 10))

        txt.insert("1.0", "Consultando dicionário...")
        txt.config(state="disabled")

        def carregar():
            significado = buscar_significado_pt(palavra)
            txt.config(state="normal")
            txt.delete("1.0", "end")
            txt.insert("1.0", significado)
            txt.config(state="disabled")

        win.after(50, carregar)

        ttk.Button(frame, text="Fechar", command=win.destroy).pack(anchor="e")

    def update_translation_clickable(self, texto_pt: str):
        """
        Renderiza o texto traduzido com palavras clicáveis.
        """
        self.text_pt.config(state="normal")
        self.text_pt.delete("1.0", "end")

        if not texto_pt:
            self.text_pt.insert("1.0", "")
            self.text_pt.config(state="disabled")
            return

        # separa em tokens mantendo pontuação
        tokens = re.findall(r"\w+|[^\w\s]", texto_pt, re.UNICODE)

        for i, token in enumerate(tokens):
            if re.fullmatch(r"\w+", token, re.UNICODE):
                tag = f"w_{i}_{token}"

                self.text_pt.insert("end", token, (tag,))
                self.text_pt.tag_config(tag, underline=False)

                # cursor de link
                self.text_pt.tag_bind(tag, "<Enter>", lambda e: self.text_pt.config(cursor="hand2"))
                self.text_pt.tag_bind(tag, "<Leave>", lambda e: self.text_pt.config(cursor=""))

                # clique -> abre significado
                self.text_pt.tag_bind(
                    tag,
                    "<Button-1>",
                    lambda e, palavra=token: self._abrir_janela_significado(palavra)
                )
            else:
                self.text_pt.insert("end", token)

            # adiciona espaço entre palavras (mas não antes de pontuação)
            if i < len(tokens) - 1:
                nxt = tokens[i + 1]
                if re.fullmatch(r"[.,;:!?)]", nxt):
                    pass
                else:
                    self.text_pt.insert("end", " ")

        self.text_pt.config(state="disabled")

    def _cancelar_edicao(self, _event=None):
        self.edit_frame.place_forget()
        self._editando_en = False

    def _quebra_linha(self, event):
        self.text_edit.insert("insert", "\n")
        return "break"

    def _debug_layout(self):
        print("\n=== DEBUG LAYOUT ===")

        print("edit_frame:")
        print("  exists:", self.edit_frame.winfo_exists())
        print("  mapped:", self.edit_frame.winfo_ismapped())
        print("  geom:", self.edit_frame.winfo_geometry())
        print("  size:", self.edit_frame.winfo_width(), self.edit_frame.winfo_height())

        print("edit_inner:")
        print("  geom:", self.edit_inner.winfo_geometry())
        print("  size:", self.edit_inner.winfo_width(), self.edit_inner.winfo_height())

        print("text_edit:")
        print("  geom:", self.text_edit.winfo_geometry())
        print("  size:", self.text_edit.winfo_width(), self.text_edit.winfo_height())

        print("btn_apply:")
        print("  exists:", self.btn_apply.winfo_exists())
        print("  mapped:", self.btn_apply.winfo_ismapped())
        print("  geom:", self.btn_apply.winfo_geometry())
        print("  size:", self.btn_apply.winfo_width(), self.btn_apply.winfo_height())


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
