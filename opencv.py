import numpy as np
import cv2
import mss

def preprocessar_imagem(img) -> cv2.typing.MatLike:
    """
    Aplica técnicas de melhoria de imagem para facilitar a identificação de caracteres pelo OCR.
    Retorna imagem em escala de cinza (1 canal).
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # aumenta resolução
    gray = cv2.resize(gray, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)

    # melhora contraste local (ótimo para pontos e vírgulas)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # nitidez leve (sharpen)
    kernel = np.array([[0, -1, 0],
                       [-1, 5, -1],
                       [0, -1, 0]])
    gray = cv2.filter2D(gray, -1, kernel)

    return gray

def gerar_preview_ocr(img_proc: cv2.typing.MatLike,
                     aplicar_threshold: bool = True,
                     inverter: bool = False,
                     max_w: int = 950,
                     max_h: int = 160) -> cv2.typing.MatLike:
    """
    Gera uma imagem "amigável" para exibição na UI, mostrando exatamente
    o que será analisado pelo OCR (ou uma versão bem próxima).

    - img_proc: geralmente é o retorno do preprocessar_imagem (grayscale)
    - aplicar_threshold: cria um preview binarizado (mais fácil de visualizar)
    - inverter: inverte cores (útil se sua legenda for clara no fundo escuro)
    - max_w/max_h: limita o tamanho do preview para não travar a UI
    """

    if img_proc is None:
        return None

    preview = img_proc.copy()

    # garante grayscale
    if len(preview.shape) == 3:
        preview = cv2.cvtColor(preview, cv2.COLOR_BGR2GRAY)

    # threshold para "enxergar" melhor caracteres pequenos (vírgula/ponto)
    if aplicar_threshold:
        preview = cv2.adaptiveThreshold(
            preview,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            7
        )

    if inverter:
        preview = cv2.bitwise_not(preview)

    # redimensiona para caber na UI
    h, w = preview.shape[:2]
    scale = min(max_w / w, max_h / h, 1.0)

    if scale != 1.0:
        new_w = int(w * scale)
        new_h = int(h * scale)
        preview = cv2.resize(preview, (new_w, new_h), interpolation=cv2.INTER_AREA)

    return preview

def cv2_to_png_bytes(img: cv2.typing.MatLike) -> bytes:
    """
    Converte uma imagem OpenCV (grayscale ou BGR) para PNG em bytes.
    Isso permite exibir no Tkinter usando PhotoImage(data=...),
    sem depender de Pillow.
    """
    if img is None:
        return b""

    # se for grayscale, mantém; se for BGR, converte para RGB
    if len(img.shape) == 2:
        img_out = img
    else:
        img_out = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    ok, buffer = cv2.imencode(".png", img_out)
    if not ok:
        return b""

    return buffer.tobytes()

def imagem_mudou(img1, img2, DIFF_THRESHOLD) -> bool:
    """
    Verifica se houve alteração entre duas imagens passadas por parâmetro,
    considerando a DIFF_THRESHOLD passada como argumento
    """
    diff = cv2.absdiff(img1, img2)
    return np.mean(diff) > DIFF_THRESHOLD

def capturar_tela(capture_area) -> cv2.typing.MatLike:
    """
    Através da utilização da biblioteca mss (Multiple ScreenShot), captura uma seção da tela
    em formato BGRA (4 canais) e posteriormente converte a imagem OpenCV BGR (3 canais)
    """
    if capture_area is None:
        return None

    with mss.mss() as sct:
        img = np.array(sct.grab(capture_area))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
