import tkinter as tk

class OverlaySelecaoArea(tk.Toplevel):
    """
    Overlay em tela cheia para o usuário selecionar (clicar e arrastar) uma área da tela.
    Retorna um dict no formato MSS:
    {"top": int, "left": int, "width": int, "height": int}
    """

    def __init__(self, parent, alpha=0.25):
        super().__init__(parent)

        self.parent = parent
        self.alpha = alpha

        self._start_x = 0
        self._start_y = 0
        self._rect_id = None
        self._area = None  # resultado final

        self._setup_window()
        self._setup_canvas()
        self._bind_events()

    # ---------- Configurações ----------

    def _setup_window(self):
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", self.alpha)
        self.configure(bg="black")
        self.overrideredirect(True)

    def _setup_canvas(self):
        self.canvas = tk.Canvas(self, cursor="cross", bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.canvas.create_text(
            20, 20,
            anchor="nw",
            fill="white",
            font=("Segoe UI", 16, "bold"),
            text="Clique e arraste para selecionar a área.\nESC = cancelar"
        )

    def _bind_events(self):
        self.bind("<Escape>", self._cancelar)

        self.canvas.bind("<Button-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)

    # ---------- Eventos do mouse ----------

    def _on_mouse_down(self, event):
        self._start_x, self._start_y = event.x, event.y

        if self._rect_id is not None:
            self.canvas.delete(self._rect_id)

        self._rect_id = self.canvas.create_rectangle(
            self._start_x, self._start_y,
            self._start_x, self._start_y,
            outline="red",
            width=3
        )

    def _on_mouse_move(self, event):
        if self._rect_id is None:
            return

        self.canvas.coords(self._rect_id, self._start_x, self._start_y, event.x, event.y)

    def _on_mouse_up(self, event):
        if self._rect_id is None:
            self._area = None
            self.destroy()
            return

        x1, y1, x2, y2 = self.canvas.coords(self._rect_id)

        left = int(min(x1, x2))
        top = int(min(y1, y2))
        right = int(max(x1, x2))
        bottom = int(max(y1, y2))

        width = right - left
        height = bottom - top

        if width < 10 or height < 10:
            self._area = None
        else:
            self._area = {"top": top, "left": left, "width": width, "height": height}

        self.destroy()

    def _cancelar(self, event=None):
        self._area = None
        self.destroy()

    # ---------- API pública ----------

    def get_area(self):
        return self._area


def selecionar_area(parent, alpha=0.25):
    """
    Função helper para abrir o overlay e retornar a área selecionada.
    Bloqueia até o usuário finalizar.
    """
    overlay = OverlaySelecaoArea(parent, alpha=alpha)
    overlay.grab_set()
    parent.wait_window(overlay)
    return overlay.get_area()
