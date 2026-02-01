import numpy as np
import cv2
import mss

def preprocessar_imagem(img) -> cv2.typing.MatLike:
    """
    Aplica técnicas de melhoria de imagem para facilitar a identificação de caracteres pelo OCR.
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

def imagem_mudou(img1, img2, DIFF_THRESHOLD) -> bool:
    """
    Verifica se houve altearação entre duas imagens passadas por parâmetro,
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