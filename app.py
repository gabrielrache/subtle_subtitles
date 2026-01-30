import tkinter as tk
from tkinter import ttk

class App(tk.Tk):
    def __init__(self):

        # main setup
        super().__init__()
        self.title("Tradução de Legendas")
        self.geometry("1000x300")
        self.minsize(1000, 300)

        # widgets
        self.menu = Menu(self)
        self.main = Main(self)



        # run
        self.mainloop()



class Menu(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.place(x = 0, rely = 0.9, relwidth = 1, relheight = 0.1)

        self.create_widgets()

    def create_widgets(self):
        menu_button1 = ttk.Button(self, text = 'Recapturar área')
        menu_button2 = ttk.Button(self, text = 'parar tradução')
        menu_button3 = ttk.Button(self, text = 'sair')

        # create grid
        self.columnconfigure((0,1,2), weight = 1, uniform = 'a')
        self.rowconfigure(0, weight = 1, uniform = 'a')

        # place widgets
        menu_button1.grid(row = 0, column = 0)
        menu_button2.grid(row = 0, column = 1)
        menu_button3.grid(row = 0, column = 2)


class Main(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.place(x = 0.0, y = 0, relwidth = 1, relheight = 0.9)

        frame = ttk.Frame(self)
        label = ttk.Label(self, background='black')

        label.pack(expand = True, fill = 'both')
        frame.pack(side = 'left', expand = True, fill = 'both')

# App()