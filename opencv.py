import numpy as np
import cv2
import mss
from dataclasses import dataclass
import threading

@dataclass
class OcrConfig:
    # Preprocessamento
    resize_fx: float = 3.0
    resize_fy: float = 3.0
    clahe_clip: float = 2.0
    sharpen_strength: float = 1.0  # 0 = desliga, 1 = padrão

    # Preview
    preview_threshold: int = 1  # 0/1
    preview_invert: int = 0     # 0/1

    # Detector de mudança
    diff_threshold: float = 2.0

    # OCR (EasyOCR)
    text_threshold: float = 0.6
    low_text: float = 0.3
    link_threshold: float = 0.4

class ConfigStore:
    """
    Armazena a config de forma segura entre threads.
    Menu escreve, thread OCR lê.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._cfg = OcrConfig()

    def get(self) -> OcrConfig:
        with self._lock:
            return OcrConfig(**self._cfg.__dict__)  # cópia

    def update(self, **kwargs):
        with self._lock:
            for k, v in kwargs.items():
                if hasattr(self._cfg, k):
                    setattr(self._cfg, k, v)

# instância global compartilhada
CONFIG = ConfigStore()

def preprocessar_imagem(img, cfg: OcrConfig = None) -> cv2.typing.MatLike:
    """
    Aplica técnicas de melhoria de imagem para facilitar a identificação de caracteres pelo OCR.
    Retorna imagem em escala de cinza (1 canal).
    """
    if cfg is None:
        cfg = CONFIG.get()

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # resize controlável
    gray = cv2.resize(
        gray, None,
        fx=max(1.0, float(cfg.resize_fx)),
        fy=max(1.0, float(cfg.resize_fy)),
        interpolation=cv2.INTER_CUBIC
    )

    # clahe controlável
    clahe = cv2.createCLAHE(
        clipLimit=max(0.1, float(cfg.clahe_clip)),
        tileGridSize=(8, 8)
    )
    gray = clahe.apply(gray)

    # sharpen controlável
    if cfg.sharpen_strength > 0:
        s = float(cfg.sharpen_strength)
        kernel = np.array([[0, -1, 0],
                           [-1, 4 + s, -1],
                           [0, -1, 0]])
        gray = cv2.filter2D(gray, -1, kernel)

    return gray

def gerar_preview_ocr(img_proc, cfg: OcrConfig = None,
                     max_w: int = 950, max_h: int = 160):

    if cfg is None:
        cfg = CONFIG.get()

    if img_proc is None:
        return None

    preview = img_proc.copy()

    if len(preview.shape) == 3:
        preview = cv2.cvtColor(preview, cv2.COLOR_BGR2GRAY)

    if int(cfg.preview_threshold) == 1:
        preview = cv2.adaptiveThreshold(
            preview, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31, 7
        )

    if int(cfg.preview_invert) == 1:
        preview = cv2.bitwise_not(preview)

    h, w = preview.shape[:2]
    scale = min(max_w / w, max_h / h, 1.0)

    if scale != 1.0:
        preview = cv2.resize(
            preview,
            (int(w * scale), int(h * scale)),
            interpolation=cv2.INTER_AREA
        )

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

