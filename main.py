import time
import threading
import mss
import easyocr
import re
from deep_translator import GoogleTranslator

from opencv import *

from app import App
from overlay import selecionar_area


def main():
    def recapturar_area() -> None:
        """Configuração de botão. Abre Overlay para o usuário apontar a área de captura de legendas"""

        nonlocal CAPTURE_AREA, frame_anterior, ultima_legenda

        app.update_label("Selecione a área na tela...")

        nova_area = selecionar_area(app, alpha=0.25)

        if not nova_area:
            app.update_label("Seleção cancelada. Mantendo área atual.")
            return

        CAPTURE_AREA = nova_area
        frame_anterior = None
        ultima_legenda = ""

        print(f'CAPTURE_AREA = {CAPTURE_AREA}')

        app.update_label("Área atualizada! Aguardando legendas...")

    def pausar_ou_retomar():
        """Configuração de botão. Interrompe temporariamente a tradução em tempo real"""
        nonlocal texto_pt_atual

        if pause_event.is_set():
            # estava pausado -> retoma
            pause_event.clear()
            texto_pt_atual = "Retomando..."
            force_read_event.set()  # força uma leitura imediata
        else:
            # estava rodando -> pausa
            pause_event.set()
            texto_pt_atual = "⏸ Tradução pausada"

    def ler_novamente() -> None:
        """Configuração de botão. Força nova leitura do OCR"""
        force_read_event.set()

    def sair() -> None:
        """Configuração de botão. Encerra o programa"""
        stop_event.set()
        app.destroy()

    def capturar_tela() -> cv2.typing.MatLike:
        """Através da utilização da biblioteca mss (Multiple ScreenShot), captura uma seção da tela
        em formato BGRA (4 canais) e posteriormente converte a imagem OpenCV BGR (3 canais) """
        if CAPTURE_AREA is None:
            return None

        with mss.mss() as sct:
            img = np.array(sct.grab(CAPTURE_AREA))
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    def extrair_texto(img, conf_min=0.40) -> str:
        """Identifica e extrai o texto (En-US) na imagem"""
        resultado = reader.readtext(
            img,
            detail=1,
            paragraph=True,
            text_threshold=0.7,  # mais permissivo
            low_text=0.5,  # detecta texto fraco
            link_threshold=0.4  # ajuda a juntar caracteres próximos (pontuação)
        )

        textos_validos = []

        for item in resultado:
            # Formatos possíveis:
            # 1) (bbox, texto, conf)
            # 2) (bbox, texto)
            if len(item) == 3:
                bbox, texto, conf = item
            elif len(item) == 2:
                bbox, texto = item
                conf = 1.0  # sem score -> assume confiança alta (ou você pode ignorar)
            else:
                continue

            if not texto:
                continue

            # conf pode vir como string em alguns casos -> força float
            try:
                conf = float(conf)
            except Exception:
                conf = 0.0

            if conf < conf_min:
                continue

            texto = texto.strip()
            texto = re.sub(r"\s+", " ", texto)

            # ignora lixo: só símbolos ou muito curto
            if len(texto) < 2:
                continue
            if re.fullmatch(r"[\W_]+", texto):
                continue

            textos_validos.append(texto)

        texto_final = " ".join(textos_validos).strip()
        texto_final = limpar_pontuacao(texto_final)
        return texto_final

    def limpar_pontuacao(texto: str) -> str:
        texto = texto.strip()

        # remove espaços antes de pontuação: "hello ," -> "hello,"
        texto = re.sub(r"\s+([,.;:!?])", r"\1", texto)

        # garante espaço depois de pontuação quando necessário: "hello,world" -> "hello, world"
        texto = re.sub(r"([,.;:!?])([A-Za-z])", r"\1 \2", texto)

        # junta reticências quebradas: ". . ." -> "..."
        texto = re.sub(r"\.\s*\.\s*\.", "...", texto)

        # junta dois pontos " .. " -> "..."
        texto = re.sub(r"\.\.", "...", texto)

        # remove múltiplos espaços
        texto = re.sub(r"\s+", " ", texto)

        return texto

    def traduzir_texto(texto) -> str:
        """Envia a string de texto fornecida em En-US para a API de tradução do Google Translator,
        que retorna a sua versão traduzida em Pt-BR"""
        if texto in cache_traducoes:
            return cache_traducoes[texto]
        try:
            traducao = translator.translate(texto)
            cache_traducoes[texto] = traducao
            return traducao

        except Exception as e:
            print("Erro na tradução:", e)
            return ""

    def loop_traducao():
        """
        Loop principal doo APP. Coordena a captura a tela, detecta quando a legenda mudou, faz o OCR,
        traduz a frase lida e atualiza a variável global que exibirá o texto em tela.
        """
        nonlocal ultima_legenda, frame_anterior, texto_en_atual, texto_pt_atual

        while not stop_event.is_set():

            # se estiver pausado, não roda OCR
            if pause_event.is_set():
                time.sleep(0.1)
                continue

            frame = capturar_tela()
            if frame is None:
                time.sleep(UPDATE_INTERVAL)
                continue

            precisa_forcar = force_read_event.is_set()

            if (not precisa_forcar) and frame_anterior is not None and not imagem_mudou(frame, frame_anterior,
                                                                                        DIFF_THRESHOLD):
                time.sleep(UPDATE_INTERVAL)
                continue

            frame_anterior = frame.copy()

            force_read_event.clear()

            img_proc = preprocessar_imagem(frame)
            texto = extrair_texto(img_proc)

            if texto and (precisa_forcar or texto != ultima_legenda):
                ultima_legenda = texto
                texto_en_atual = texto

                traducao = traduzir_texto(texto)
                if traducao:
                    texto_pt_atual = traducao

            time.sleep(UPDATE_INTERVAL)

    UPDATE_INTERVAL = 0.1
    DIFF_THRESHOLD = 1
    CAPTURE_AREA = None

    ultima_legenda = ""
    frame_anterior = None
    cache_traducoes = {}
    texto_en_atual = "Aguardando legenda (EN)..."
    texto_pt_atual = "Aguardando tradução (PT)..."

    app = App(recapturar_area, pausar_ou_retomar, ler_novamente, sair)

    reader = easyocr.Reader(['en'], gpu=False)
    translator = GoogleTranslator(source='en', target='pt')

    stop_event = threading.Event()
    force_read_event = threading.Event()
    pause_event = threading.Event()  # quando setado => pausado

    app.update_label("Selecione a área das legendas...")
    CAPTURE_AREA = selecionar_area(app)

    if not CAPTURE_AREA:
        app.update_label("Área inválida ou cancelada.\nFechando...")
        app.after(1500, app.destroy)
        app.mainloop()
        return

    thread = threading.Thread(target=loop_traducao, daemon=True)
    thread.start()

    def update_app():
        app.update_labels(texto_en_atual, texto_pt_atual)
        app.after(200, update_app)

    update_app()

    app.mainloop()


if __name__ == "__main__":
    main()
