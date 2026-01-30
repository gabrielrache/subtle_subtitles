import numpy as np
import cv2

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


def imagem_mudou(img1, img2, DIFF_THRESHOLD):
    diff = cv2.absdiff(img1, img2)
    return np.mean(diff) > DIFF_THRESHOLD
