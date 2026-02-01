import time
import threading
import easyocr
import re

from app import App
from overlay import selecionar_area
from opencv import CONFIG, capturar_tela, preprocessar_imagem, imagem_mudou, gerar_preview_ocr, cv2_to_png_bytes
from deep_translator import GoogleTranslator


def main():
    def recapturar_area() -> None:
        """
        Configuração de botão. Abre Overlay para o usuário apontar a área de captura de legendas
        """

        nonlocal CAPTURE_AREA, frame_anterior, ultima_legenda

        app.update_texts("Selecione a área na tela...", "")

        nova_area = selecionar_area(app, alpha=0.25)

        if not nova_area:
            app.update_texts("Seleção cancelada. Mantendo área atual.", "")
            return

        CAPTURE_AREA = nova_area
        frame_anterior = None
        ultima_legenda = ""

        print(f'CAPTURE_AREA = {CAPTURE_AREA}')

        app.update_texts("Área atualizada! Aguardando legendas...", "")

    def pausar_ou_retomar():
        """
        Configuração de botão. Interrompe temporariamente a tradução em tempo real
        """
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
        """
        Configuração de botão. Força nova leitura do OCR
        """
        force_read_event.set()

    def sair() -> None:
        """
        Configuração de botão. Encerra o programa
        """
        stop_event.set()
        app.destroy()

    def extrair_texto(img, cfg, conf_min=0.40) -> str:
        """
        Identifica e extrai o texto (En-US) na imagem
        """
        resultado = reader.readtext(
            img,
            detail=1,
            paragraph=False,
            text_threshold=cfg.text_threshold,
            low_text=cfg.low_text,
            link_threshold=cfg.link_threshold
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
        """
        Realiza pós processamento do texto para aprimor caracteres de pontuação
        """
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
        """
        Envia a string de texto fornecida em En-US para a API de tradução do Google Translator,
        que retorna a sua versão traduzida em Pt-BR
        """
        if texto in cache_traducoes:
            return cache_traducoes[texto]
        try:
            traducao = translator.translate(texto)
            cache_traducoes[texto] = traducao
            return traducao

        except Exception as e:
            print("Erro na tradução:", e)
            return ""

    def loop_traducao() -> None:
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

            cfg = CONFIG.get()

            frame = capturar_tela(CAPTURE_AREA)
            if frame is None:
                time.sleep(UPDATE_INTERVAL)
                continue

            precisa_forcar = force_read_event.is_set()

            if (not precisa_forcar) and frame_anterior is not None and not imagem_mudou(frame, frame_anterior, cfg.diff_threshold):
                time.sleep(UPDATE_INTERVAL)
                continue

            frame_anterior = frame.copy()

            force_read_event.clear()

            img_proc = preprocessar_imagem(frame, cfg)

            # gera preview da imagem que vai pro OCR
            preview = gerar_preview_ocr(img_proc, cfg)

            # converte para PNG bytes
            png = cv2_to_png_bytes(preview)

            # manda para UI com segurança (Tkinter só no main thread)
            app.after(0, app.update_preview, png)

            # agora roda OCR normal
            texto = extrair_texto(img_proc, cfg)

            if texto:
                texto = texto.replace("|", "I")

            if texto and (precisa_forcar or texto != ultima_legenda):
                ultima_legenda = texto
                texto_en_atual = texto

                traducao = traduzir_texto(texto)
                if traducao:
                    texto_pt_atual = traducao

            time.sleep(UPDATE_INTERVAL)

    def update_app() -> None:
        """
        Atualiza labels da janela principal do App conforme as legendas são lidas e armazenadas
        """
        app.update_texts(texto_en_atual, texto_pt_atual)
        app.after(500, update_app)

    # Constantes
    UPDATE_INTERVAL = 0.7
    CAPTURE_AREA = None

    # Variáveis
    ultima_legenda = ""
    frame_anterior = None
    cache_traducoes = {}
    texto_en_atual = "Aguardando legenda (EN)..."
    texto_pt_atual = "Aguardando tradução (PT)..."

    # Instâncias
    app = App(recapturar_area, pausar_ou_retomar, ler_novamente, sair)

    reader = easyocr.Reader(['en'], gpu=False)
    translator = GoogleTranslator(source='en', target='pt')

    # Eventos
    stop_event = threading.Event()
    force_read_event = threading.Event()
    pause_event = threading.Event()  # quando setado => pausado


    # Run
    app.update_texts("Selecione a área das legendas...", "")
    CAPTURE_AREA = selecionar_area(app)

    if not CAPTURE_AREA:
        app.update_texts("Área inválida ou cancelada.\nFechando...", "")
        app.after(1500, app.destroy)
        app.mainloop()
        return

    thread = threading.Thread(target=loop_traducao, daemon=True)
    thread.start()

    update_app()
    app.mainloop()


if __name__ == "__main__":
    main()
