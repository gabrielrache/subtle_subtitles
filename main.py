import time
import threading
import mss
import numpy as np
import cv2
import easyocr
import tkinter as tk
from deep_translator import GoogleTranslator

# ===============================
# CONFIGURAÇÕES
# ===============================

UPDATE_INTERVAL = 1.0
DIFF_THRESHOLD = 3

CAPTURE_AREA = None

# ===============================
# OCR / TRADUÇÃO
# ===============================

reader = easyocr.Reader(['en'], gpu=False)
translator = GoogleTranslator(source='en', target='pt')

ultima_legenda = ""
frame_anterior = None
cache_traducoes = {}
texto_traduzido_atual = "Aguardando legendas..."

# ===============================
# SELEÇÃO DE ÁREA (TOPLEVEL)
# ===============================

def selecionar_area_tela(root):
    global CAPTURE_AREA

    CAPTURE_AREA = None
    print("\n[DEBUG] Iniciando seleção de área")

    overlay = tk.Toplevel(root)
    overlay.attributes("-fullscreen", True)
    overlay.attributes("-alpha", 0.3)
    overlay.configure(bg="black")
    overlay.lift()
    overlay.focus_force()
    overlay.grab_set()

    canvas = tk.Canvas(overlay, cursor="cross", bg="black")
    canvas.pack(fill=tk.BOTH, expand=True)

    inicio = {"x": None, "y": None, "rect": None}

    def mouse_down(e):
        print(f"[DEBUG] mouse_down: x={e.x}, y={e.y}")
        inicio["x"], inicio["y"] = e.x, e.y
        inicio["rect"] = canvas.create_rectangle(
            e.x, e.y, e.x, e.y,
            outline="red", width=2
        )

    def mouse_move(e):
        if inicio["rect"] is not None:
            canvas.coords(inicio["rect"], inicio["x"], inicio["y"], e.x, e.y)

    def mouse_up(e):
        global CAPTURE_AREA  # 🔑 LINHA CRÍTICA

        print(f"[DEBUG] mouse_up: x={e.x}, y={e.y}")
        print(f"[DEBUG] inicio: {inicio}")

        if inicio["x"] is None or inicio["y"] is None:
            print("[DEBUG] mouse_up ignorado")
            return

        x1, y1 = inicio["x"], inicio["y"]
        x2, y2 = e.x, e.y

        width = abs(x2 - x1)
        height = abs(y2 - y1)

        print(f"[DEBUG] área calculada: width={width}, height={height}")

        if width >= 10 and height >= 10:
            CAPTURE_AREA = {
                "left": min(x1, x2),
                "top": min(y1, y2),
                "width": width,
                "height": height
            }
            print("[DEBUG] CAPTURE_AREA definida:", CAPTURE_AREA)
        else:
            print("[DEBUG] área descartada")

        overlay.destroy()

    canvas.bind("<ButtonPress-1>", mouse_down)
    canvas.bind("<B1-Motion>", mouse_move)
    canvas.bind("<ButtonRelease-1>", mouse_up)

    root.wait_window(overlay)

    print("[DEBUG] Seleção final:", CAPTURE_AREA)
    return CAPTURE_AREA is not None


# ===============================
# CAPTURA / OCR
# ===============================

def capturar_tela():
    with mss.mss() as sct:
        img = np.array(sct.grab(CAPTURE_AREA))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)


def preprocessar_imagem(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    gray = cv2.resize(
        gray,
        None,
        fx=2.0,
        fy=2.0,
        interpolation=cv2.INTER_CUBIC
    )

    gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
    return gray


def imagem_mudou(img1, img2):
    diff = cv2.absdiff(img1, img2)
    return np.mean(diff) > DIFF_THRESHOLD


def extrair_texto(img):
    resultado = reader.readtext(
        img,
        detail=0,
        paragraph=True,
        text_threshold=0.7,
        low_text=0.4
    )
    return " ".join(resultado).strip()


def traduzir_texto(texto):
    if texto in cache_traducoes:
        return cache_traducoes[texto]
    try:
        traducao = translator.translate(texto)
        cache_traducoes[texto] = traducao
        return traducao
    except Exception:
        return ""

# ===============================
# THREAD OCR
# ===============================

def loop_traducao():
    global ultima_legenda, frame_anterior, texto_traduzido_atual

    while True:
        frame = capturar_tela()

        if frame_anterior is not None and not imagem_mudou(frame, frame_anterior):
            time.sleep(UPDATE_INTERVAL)
            continue

        frame_anterior = frame.copy()

        img_proc = preprocessar_imagem(frame)
        texto = extrair_texto(img_proc)

        if texto and texto != ultima_legenda:
            ultima_legenda = texto
            traducao = traduzir_texto(texto)
            if traducao:
                texto_traduzido_atual = traducao

        time.sleep(UPDATE_INTERVAL)

# ===============================
# UI PRINCIPAL
# ===============================

root = tk.Tk()
root.title("Tradução de Legendas")
root.geometry("900x200")
root.minsize(400, 120)

frame = tk.Frame(root, bg="#111")
frame.pack(fill=tk.BOTH, expand=True)

label = tk.Label(
    frame,
    text=texto_traduzido_atual,
    fg="white",
    bg="#111",
    font=("Segoe UI Semibold", 22),
    wraplength=860,
    justify="center"
)
label.pack(expand=True, padx=20, pady=20)

# ===============================
# FLUXO CORRETO
# ===============================

# 1️⃣ selecionar área (bloqueante)
ok = selecionar_area_tela(root)

if not ok:
    label.config(text="Área de captura inválida.\nFechando o programa.")
    root.after(2000, root.destroy)
    root.mainloop()
    exit()

# 2️⃣ iniciar OCR só depois da área válida
thread = threading.Thread(target=loop_traducao, daemon=True)
thread.start()

# 3️⃣ atualizar UI
def atualizar_ui():
    label.config(text=texto_traduzido_atual)
    root.after(200, atualizar_ui)

atualizar_ui()
root.mainloop()
