import tkinter as tk
from tkinter import ttk

class App(tk.Tk):
    def __init__(self, recapturar_callback, toggle_pause_callback, ler_callback, sair_callback):
        super().__init__()

        self.title("Tradução de Legendas")
        self.geometry("1000x300")
        self.minsize(1000, 300)

        self.recapturar_area = recapturar_callback
        self.toggle_pause = toggle_pause_callback
        self.ler_novamente = ler_callback
        self.sair = sair_callback

        self.menu = Menu(self)
        self.main = Main(self)

    def update_label(self, text):
        self.main.update_label(text)

    def update_labels(self, texto_en, texto_pt):
        self.main.update_labels(texto_en, texto_pt)

    def update_preview(self, png_bytes: bytes):
        self.main.update_preview(png_bytes)


class Menu(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.place(x = 0, rely = 0.9, relwidth = 1, relheight = 0.1)
        self.create_widgets()


    def create_widgets(self):
        menu_button1 = ttk.Button(self, text='Recapturar área', command=self.parent.recapturar_area)
        menu_button2 = ttk.Button(self, text='Pausar/Retomar', command=self.parent.toggle_pause)
        menu_button3 = ttk.Button(self, text='Ler novamente', command=self.parent.ler_novamente)
        menu_button4 = ttk.Button(self, text='Sair', command=self.parent.sair)

        # create grid
        self.columnconfigure((0,1,2,3), weight = 1, uniform = 'a')
        self.rowconfigure(0, weight = 1, uniform = 'a')

        # place widgets
        menu_button1.grid(row = 0, column = 0)
        menu_button2.grid(row = 0, column = 1)
        menu_button3.grid(row = 0, column = 2)
        menu_button4.grid(row = 0, column = 3)


class Main(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.place(x=0.0, y=0, relwidth=1, relheight=0.9)

        self._tk_preview_img = None  # referência obrigatória

        # Label do texto original (inglês)
        self.label_en = tk.Label(
            self,
            text="Prévia OCR (imagem)",
            bg="#111",
        )
        self.label_en.pack(expand=False, fill="both", padx=10, pady=(10, 5))

        # Label do texto traduzido (português)
        self.label_pt = tk.Label(
            self,
            text="Aguardando tradução (PT)...",
            fg="white",
            bg="#111",
            font=("Segoe UI Semibold", 22),
            wraplength=860,
            justify="center"
        )
        self.label_pt.pack(expand=True, fill="both", padx=10, pady=(0, 30))

    def update_labels(self, texto_en, texto_pt):
        self.label_en.config(text=texto_en)
        self.label_pt.config(text=texto_pt)

    def update_label(self, texto):
        self.label_pt.config(text=texto)

    def update_preview(self, png_bytes: bytes):
        if not png_bytes:
            return

        self._tk_preview_img = tk.PhotoImage(data=png_bytes)
        self.label_en.config(image=self._tk_preview_img, text="")

# App()