import tkinter as tk

def criar_janela():

    root = tk.Tk()
    root.title("Tradução de Legendas")
    root.geometry("900x200")
    root.minsize(400, 120)

    frame = tk.Frame(root, bg="#111")
    frame.pack(fill=tk.BOTH, expand=True)

    label = tk.Label(
        frame,
        text="Aguardando legendas...",
        fg="white",
        bg="#111",
        font=("Segoe UI Semibold", 22),
        wraplength=860,
        justify="center"
    )
    label.pack(expand=True, padx=20, pady=20)

    return root, frame, label