import numpy as np
import cv2

def preprocessar_imagem(img):
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



def imagem_mudou(img1, img2, DIFF_THRESHOLD):
    diff = cv2.absdiff(img1, img2)
    return np.mean(diff) > DIFF_THRESHOLD
