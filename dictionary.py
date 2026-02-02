# dictionary.py
import re
import unicodedata
import requests

_CACHE: dict[str, str] = {}


def _limpar_palavra(palavra: str) -> str:
    if not palavra:
        return ""
    p = palavra.strip().lower()
    p = re.sub(r"^[^0-9A-Za-zÀ-ÿ]+", "", p)
    p = re.sub(r"[^0-9A-Za-zÀ-ÿ]+$", "", p)
    return p.strip()


def _remover_acentos(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def _gerar_variacoes_plural_singular(p: str) -> list[str]:
    variacoes = []

    if p.endswith("ões") and len(p) > 3:
        variacoes.append(p[:-3] + "ão")  # libações -> libação

    if p.endswith("ães") and len(p) > 3:
        variacoes.append(p[:-3] + "ão")

    if p.endswith("ais") and len(p) > 3:
        variacoes.append(p[:-3] + "al")

    if p.endswith("eis") and len(p) > 3:
        variacoes.append(p[:-3] + "el")

    if p.endswith("óis") and len(p) > 3:
        variacoes.append(p[:-3] + "ol")

    if p.endswith("ns") and len(p) > 2:
        variacoes.append(p[:-2] + "m")

    if p.endswith("es") and len(p) > 3:
        variacoes.append(p[:-2])

    if p.endswith("s") and len(p) > 3:
        variacoes.append(p[:-1])

    return variacoes


def gerar_variacoes(palavra: str) -> list[str]:
    p = _limpar_palavra(palavra)
    if not p:
        return []

    tentativas = [p]

    sem_acento = _remover_acentos(p)
    if sem_acento != p:
        tentativas.append(sem_acento)

    for s in _gerar_variacoes_plural_singular(p):
        if s and s not in tentativas:
            tentativas.append(s)

        s2 = _remover_acentos(s)
        if s2 and s2 not in tentativas:
            tentativas.append(s2)

    out = []
    seen = set()
    for t in tentativas:
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


# ------------------ Fonte 1: dicionario-aberto ------------------

def _buscar_dicionario_aberto(palavra: str) -> str:
    try:
        url = f"https://api.dicionario-aberto.net/word/{palavra}"
        r = requests.get(url, timeout=4)

        if r.status_code != 200:
            return ""

        data = r.json()
        if not data:
            return ""

        item = data[0]
        xml = item.get("xml", "") or ""
        if not xml:
            return ""

        texto = (
            xml.replace("<br/>", "\n")
               .replace("<br />", "\n")
               .replace("<br>", "\n")
        )
        texto = re.sub(r"<[^>]+>", "", texto)
        texto = re.sub(r"\n{3,}", "\n\n", texto).strip()

        return texto[:2500]
    except Exception:
        return ""


# ------------------ Fonte 2: Wiktionary (PT) ------------------

def _buscar_wiktionary_pt(palavra: str) -> str:
    """
    Busca o extrato do Wiktionary em português via API do MediaWiki.
    Retorna texto limpo ou vazio.
    """
    try:
        url = "https://pt.wiktionary.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "prop": "extracts",
            "explaintext": 1,
            "exintro": 1,
            "redirects": 1,
            "titles": palavra
        }

        r = requests.get(url, params=params, timeout=4)
        if r.status_code != 200:
            return ""

        data = r.json()
        pages = data.get("query", {}).get("pages", {})
        if not pages:
            return ""

        page = next(iter(pages.values()))
        extract = page.get("extract", "") or ""
        extract = extract.strip()

        if not extract:
            return ""

        # limpa excesso de linhas vazias
        extract = re.sub(r"\n{3,}", "\n\n", extract).strip()

        # limita tamanho
        return extract[:2500]

    except Exception:
        return ""


def buscar_significado_pt(palavra: str) -> str:
    original = _limpar_palavra(palavra)
    if not original:
        return "Palavra inválida."

    if original in _CACHE:
        return _CACHE[original]

    tentativas = gerar_variacoes(original)

    for t in tentativas:
        # cache para tentativas também
        if t in _CACHE and _CACHE[t]:
            definicao = _CACHE[t]
            if t != original:
                resp = f"(Forma normalizada: {t})\n\n{definicao}"
                _CACHE[original] = resp
                return resp
            _CACHE[original] = definicao
            return definicao

        # 1) tenta dicionario-aberto
        definicao = _buscar_dicionario_aberto(t)
        if definicao:
            _CACHE[t] = definicao
            if t != original:
                resp = f"(Forma normalizada: {t})\n\n{definicao}"
                _CACHE[original] = resp
                return resp
            _CACHE[original] = definicao
            return definicao

        # 2) fallback Wiktionary
        definicao = _buscar_wiktionary_pt(t)
        if definicao:
            _CACHE[t] = definicao
            if t != original:
                resp = f"(Forma normalizada: {t})\n\n{definicao}"
                _CACHE[original] = resp
                return resp
            _CACHE[original] = definicao
            return definicao

    msg = "Nenhuma definição encontrada."
    _CACHE[original] = msg
    return msg
