#!/usr/bin/env python3
"""coleta.py · baixa as manchetes dos feeds e confere a data das páginas abertas (CONTRATO, seções 1 e 1.1).

    python3 ferramentas/coleta.py [--dia D] [--trabalho P] [--horas N] [--tempo 90] [--por-feed 15] [--offline PASTA]
    python3 ferramentas/coleta.py --confere [--trabalho P] [--tempo 60] [--offline PASTA]

Sem --confere: lê dados/veiculos.json e dados/regua.json e grava P/coleta.json e P/mesa.txt.
Com --confere: lê P/urls.txt e P/coleta.json e grava P/conferencia.json.
Grava sempre que chega a rodar (CONTRATO, seção 0): com erro de uso ou entrada ilegível, nada.

O que chega da rede é dado de terceiro, e a mesa vai parar na frente de um agente de IA. Por isso:
feed com DOCTYPE ou ENTITY é recusado antes de chegar ao leitor de XML; todo texto passa por limpa();
só entra endereço http(s) com nome de site público; e nada do que foi baixado é executado.
"""
# --- guarda de versão: início ---
import os
import sys

if sys.version_info < (3, 10):
    print("FALHA interna: Python 3.10 ou mais novo")
    sys.exit(1)
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# --- guarda de versão: fim ---
import argparse  # noqa: E402
import codecs  # noqa: E402
import email.utils  # noqa: E402
import html  # noqa: E402
import html.entities  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import time  # noqa: E402
import unicodedata  # noqa: E402
import xml.etree.ElementTree as ET  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402
from xml.sax.saxutils import escape as _escapa_xml  # noqa: E402

import comum  # noqa: E402
import rede  # noqa: E402

PARALELOS = 8              # pedidos ao mesmo tempo
POR_PEDIDO = 8.0           # segundos por pedido
TEMPO, TEMPO_CONFERE = 90.0, 60.0
HORAS, POR_FEED = 36, 15
MAX_TITULO, MAX_RESUMO = 200, 300
FUTURO = timedelta(hours=2)
MAX_ENTRADAS = 2000        # entradas lidas de um feed (2 MB cabem muitas; só as N mais novas ficam)
MAX_BRUTO = 20000          # caracteres de um campo antes da limpeza: o resto não caberia mesmo
MAX_PAGINAS = 30           # páginas conferidas pelo --confere
MESA_BYTES = 60 * 1024     # 60 KB = 61.440 bytes em UTF-8
MESA_HISTORIAS, MESA_MANCHETES, MESA_POR_VEICULO = 40, 8, 2
IA_HISTORIAS, IA_MANCHETES = 10, 4
LEGENDA = ("LEGENDA: [XX] partido do veículo · ? lado incerto · serve a: player a quem o veículo serve · "
           "fatos: confiança para fato cru · [SUSPEITA] pode ser ordem, e não notícia")
ACEITA_FEED = "application/rss+xml, application/atom+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5"
ACEITA_PAGINA = "text/html, application/xhtml+xml;q=0.9, */*;q=0.5"


# ================================================================ limpeza de texto (passo 4)

# Caracteres que não se veem, ou que mudam a leitura sem aparecer. Saem todos: controles, largura zero,
# marcas de direção de texto (podem inverter o que o leitor vê), seletores de variação e o bloco de
# "etiquetas" (dá para esconder uma frase inteira neles), preenchedores, uso privado e substitutos soltos
# (estes últimos nem cabem em UTF-8). A lista é escrita aqui, e não tirada da tabela Unicode do Python,
# para a mesma entrada dar a mesma saída em qualquer versão.
_RE_INVISIVEL = re.compile(
    r"[\u0000-\u001f\u007f-\u009f\u00ad\u034f\u061c\u070f"            # controles, hífen opcional, marcas
    r"\u115f\u1160\u17b4\u17b5\u180b-\u180f\u3164\uffa0"   # preenchedores e seletores
    r"\u200b-\u200f\u202a-\u202e\u2060-\u206f"         # largura zero e direção de texto
    r"\ufe00-\ufe0f\ufeff\ufff0-\ufffc\ufdd0-\ufdef\ufffe\uffff"   # variação, BOM, não caracteres
    r"\ud800-\udfff\ue000-\uf8ff\U0001bca0-\U0001bca3\U0001d173-\U0001d17a"
    r"\U000e0000-\U000e0fff\U000f0000-\U0010ffff"                                  # etiquetas e uso privado
    + "".join(r"\U%08x\U%08x" % (plano * 0x10000 + 0xFFFE, plano * 0x10000 + 0xFFFF) for plano in range(1, 15))
    + "]")
_RE_VIRA_ESPACO = re.compile(r"[\t\n\u000b\u000c\r\u001c-\u001f\u0085\u2028\u2029\u2800]")
# Marca de HTML: tem de começar como marca ("<p", "</p", "<!", "<?"). "<2%" não é marca, e fica.
_RE_MARCA = re.compile(r"</?[A-Za-z][^<>]*>|<![^<>]*>|<\?[^<>]*>")
_RE_BLOCO = re.compile(r"<(script|style)\b", re.I)
_RE_FIM_BLOCO = {"script": re.compile(r"</script\s*>", re.I), "style": re.compile(r"</style\s*>", re.I)}
_RE_SOBRA = re.compile(r"<(?=[A-Za-z/!?])")


def _sem_trechos(texto, abre, fecha):
    """Tira tudo entre `abre` e `fecha`. Sem o fecho, o resto do texto é do trecho. Uma passada só."""
    partes, posicao = [], 0
    while True:
        inicio = texto.find(abre, posicao)
        if inicio < 0:
            partes.append(texto[posicao:])
            break
        partes.append(texto[posicao:inicio])
        fim = texto.find(fecha, inicio + len(abre))
        if fim < 0:
            break
        posicao = fim + len(fecha)
    return " ".join(partes)


def _sem_blocos(texto):
    """Tira <script>…</script> e <style>…</style> com o que há dentro: código não é texto de notícia."""
    partes, posicao = [], 0
    while True:
        abre = _RE_BLOCO.search(texto, posicao)
        if not abre:
            partes.append(texto[posicao:])
            break
        partes.append(texto[posicao:abre.start()])
        fecha = _RE_FIM_BLOCO[abre.group(1).lower()].search(texto, abre.end())
        if not fecha:
            break
        posicao = fecha.end()
    return " ".join(partes)


def limpa(texto, maximo):
    """Texto de terceiro vira texto puro, de uma linha, com até `maximo` caracteres.

    Sai: marca de HTML, que vira espaço (com o conteúdo de script e de style), comentário, entidade (vira
    o caractere), caractere de controle, invisível e de direção de texto. Espaços seguidos viram um, e o
    texto é aparado nas pontas (CONTRATO, seção 1, passo 4). O que passa do tamanho é cortado e ganha
    "…", dentro do limite: quem lê sabe que o título não está inteiro. Nenhuma expressão regular daqui
    anda para trás: texto feito para travar a limpeza não trava."""
    if not isinstance(texto, str):
        return ""
    texto = texto[:MAX_BRUTO]
    for _ in range(3):  # entidade esconde marca ("&lt;b&gt;") e marca esconde entidade: até 3 voltas
        antes = texto
        texto = _sem_trechos(_sem_blocos(texto), "<!--", "-->")
        texto = texto.replace("<![CDATA[", " ").replace("]]>", " ")
        texto = html.unescape(_RE_MARCA.sub(" ", texto))
        if texto == antes:
            break
    texto = _RE_MARCA.sub(" ", _sem_blocos(texto))
    texto = _RE_SOBRA.sub("< ", texto)  # "<" solto seguido de letra não pode parecer marca para quem lê depois
    texto = _RE_INVISIVEL.sub("", _RE_VIRA_ESPACO.sub(" ", texto))
    texto = " ".join(texto.split())
    if len(texto) > maximo:
        texto = texto[:maximo - 1].rstrip() + "…"
    return texto


def chave(texto):
    """Forma de comparar: sem acento, sem diferença de caixa e de largura. Não é texto para gravar."""
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)).casefold()


# ================================================================ suspeita e categoria (passos 7 e 8)

# Frases que parecem dar ordem a quem lê. É pista, não filtro: a manchete continua na mesa, com a marca
# [SUSPEITA] e sem o resumo, e quem decide se é notícia sobre o assunto ou ordem é o agente.
# Os moldes são escritos com acento e passam por chave(), como o texto que vão examinar.
_SUSPEITAS = re.compile("|".join(chave(molde) for molde in (
    r"\b(ignore|ignorem|ignora|ignorar|ignorez|ignoriere|desconsidere|desconsiderem|esqueça|esqueçam|disregard|"
    r"forget|override|olvida|olvide)\b.{0,40}\b(instruç\w*|instruction\w*|instruccion\w*|prompt\w*|orientaç\w*|"
    r"regras|rules|diretriz\w*|guidelines|comandos|ordens|anweisung\w*|consignes)\b",
    r"\b(system|developer) (prompt|message|instructions?)\b",
    r"\b(prompt|mensagem|mensaje|instruções|instrucciones) (do|de|del) sistema\b",
    r"\b(você|tu|vc) é (um|uma) (ia|assistente|modelo|agente|robô|chatbot|inteligência artificial)\b",
    r"\byou are (an?|the) (ai|assistant|language model|llm|chatbot|agent|bot)\b",
    r"\b(eres|usted es) (un|una) (ia|asistente|modelo|agente)\b",
    r"\bas an ai\b",
    r"\bcomo (um|uma) (ia|assistente|modelo de linguagem)\b",
    r"\b(nota|aviso|recado|mensagem|atenção|instrução|instruções|ordem) (ao|aos|à|às|a|para|para o|para os|para a|para as) "
    r"(agregador\w*|assistente\w*|modelo|modelos|ia|ias|robô|robôs|editor|editores|agente|agentes|llm|llms|chatbot\w*|resumidor\w*)\b",
    r"\b(note|notice|message|attention|instruction|instructions) (to|for) (the |all |any )?(ai|ais|llm|llms|assistant|assistants|"
    r"aggregator|aggregators|model|models|agent|agents|editor|editors|bot|bots|summarizer|summarizers)\b",
    r"\b(new|novas|nuevas|nouvelles) (instructions|instruções|instrucciones)\b",
    r"<\|?(im_start|im_end|system|endoftext)\|?>", r"\[/?inst\]", r"###\s?(instruction|system|instrução|sistema)\b",
    r"\b(begin|end) (system|instructions)\b",
    r"игнорируй\w*.{0,30}инструкци\w*", r"системн\w+ (промпт\w*|инструкци\w*)", r"\bты (- |— )?(ии|ассистент|языковая модель)\b",
    r"忽略.{0,12}(指令|指示|提示|说明)", r"系统提示", r"你是(一个|一名)?(ai|人工智能|语言模型|助手)",
    r"تجاهل.{0,20}تعليمات",
)), re.S)

# Termos de IA (passo 8). Sigla vale só em maiúscula e fora de palavra: "ia" também é verbo, e "ai", interjeição.
_RE_IA_SIGLA = re.compile(r"(?<![^\W\d_])(?:IA|AI|AGI|LLM|LLMs|GPT|ИИ)(?![^\W\d_])")
_RE_IA = re.compile("|".join(chave(molde) for molde in (
    r"\binteligência artificial\b", r"\bartificial intelligence\b", r"\bintelligence artificielle\b",
    r"\bkünstliche\w* intelligenz\b", r"\bintelligenza artificiale\b", r"\bmachine learning\b",
    r"\b(aprendizado|aprendizagem|aprendizaje) (de máquina|automático|profundo)\b", r"\bdeep learning\b",
    r"\brede neural\b", r"\bredes neurais\b", r"\bneural networks?\b", r"\b(large )?language models?\b",
    r"\bmodelos? de (linguagem|lenguaje)\b", r"\bgenerative ai\b", r"\bia generativa\b", r"\bgenai\b",
    r"\bchatbots?\b", r"chatgpt", r"\bopenai\b", r"\banthropic\b", r"\bdeepmind\b", r"\bdeepseek\b", r"\bnvidia\b",
    r"\bhugging face\b", r"\bmidjourney\b", r"\bxai\b", r"\bgrok\b", r"\bqwen\b", r"\bgigachat\b", r"gpt-?\d",
    r"\bsuperinteligência\b", r"\bsuperintelligence\b", r"\bclaude ?(\d|opus|sonnet|haiku|code\b)",
    r"\bgemini ?(\d|pro\b|ultra\b|flash\b|nano\b)", r"\bgoogle gemini\b", r"\bstable diffusion\b", r"\bmistral ai\b",
    r"искусственн\w* интеллект\w*", r"нейросет\w*", r"штучн\w* інтелект\w*", r"人工智能", r"人工知能", r"生成式", r"大模型",
    r"인공지능", r"الذكاء الاصطناعي", r"ذكاء اصطناعي", r"هوش مصنوعی", r"בינה מלאכותית", r"\byapay zek[aâ]\b",
    r"कृत्रिम बुद्धिमत्ता",
)))


def parece_ordem(titulo, resumo):
    return _SUSPEITAS.search(chave(titulo + " \n " + resumo)) is not None


def categoria_de(titulo, resumo):
    texto = titulo + " \n " + resumo
    return "ia" if _RE_IA_SIGLA.search(texto) or _RE_IA.search(chave(texto)) else "geopolitica"


# ================================================================ datas (passo 5)

_RE_ISO = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})(?:[Tt ]([0-9]{2}):([0-9]{2})(?::([0-9]{2})(?:[.,][0-9]{1,9})?)?)?"
                     r"\s*([Zz]|[+-][0-9]{2}(?::?[0-9]{2})?)?")
_RE_FUSO_NOME = re.compile(r"\b([A-Za-z]{2,5})\s*$")
# Siglas de fuso que aparecem em feeds e que a RFC 822 não cobre (ela só conhece as dos EUA). Em horas.
_FUSOS = {"UTC": 0, "GMT": 0, "UT": 0, "Z": 0, "WET": 0, "WEST": 1, "BST": 1, "CET": 1, "CEST": 2, "EET": 2, "EEST": 3,
          "MSK": 3, "TRT": 3, "EAT": 3, "SAST": 2, "CAT": 2, "WAT": 1, "GST": 4, "PKT": 5, "IST": 5.5, "ICT": 7, "WIB": 7,
          "HKT": 8, "SGT": 8, "PHT": 8, "JST": 9, "KST": 9, "AEST": 10, "AEDT": 11, "NZST": 12, "NZDT": 13,
          "BRT": -3, "ART": -3}


def _monta(ano, mes, dia, hora, minuto, segundo, minutos_de_fuso):
    try:
        local = datetime(ano, mes, dia, hora, minuto, min(segundo, 59), tzinfo=timezone.utc)
        return local - timedelta(minutes=minutos_de_fuso)
    except (ValueError, OverflowError):
        return None


def le_instante(texto):
    """Data de feed ou de página vira datetime em UTC; None se não dá para ler.

    Aceita ISO 8601 (Atom, dc:date, páginas) e RFC 822 (pubDate do RSS), com fuso em número ou em sigla.
    Sem fuso, a hora é lida como UTC."""
    if not isinstance(texto, str):
        return None
    texto = " ".join(texto.split())[:80]
    achado = _RE_ISO.fullmatch(texto)
    if achado:
        ano, mes, dia, hora, minuto, segundo, fuso = achado.groups()
        desvio = 0
        if fuso and fuso not in "Zz":
            numeros = fuso[1:].replace(":", "")
            desvio = (int(numeros[:2]) * 60 + int(numeros[2:] or 0)) * (-1 if fuso[0] == "-" else 1)
        if abs(desvio) > 16 * 60:
            return None
        return _monta(int(ano), int(mes), int(dia), int(hora or 0), int(minuto or 0), int(segundo or 0), desvio)
    try:
        partes = email.utils.parsedate_tz(texto)
    except (TypeError, ValueError, IndexError, OverflowError):
        partes = None
    if not partes:
        return None
    desvio = partes[9]
    if desvio is None or (desvio == 0 and not re.search(r"[+-][0-9]{4}\s*$|\b(GMT|UTC?|Z)\s*$", texto, re.I)):
        sigla = _RE_FUSO_NOME.search(texto)  # sigla que o leitor da RFC 822 não conhece volta como zero
        desvio = int(_FUSOS.get(sigla.group(1).upper(), 0) * 3600) if sigla else 0
    if abs(desvio) > 16 * 3600:
        return None
    return _monta(partes[0], partes[1], partes[2], partes[3], partes[4], partes[5], desvio / 60.0)


# ================================================================ leitura de RSS e Atom (passos 2 e 3)

_RE_HOSTIL = re.compile(r"<!\s*(DOCTYPE|ENTITY)", re.I)
_RE_DECLARACAO = re.compile(r"[\s\ufeff]*<\?xml[^>]{0,200}\?>")
_RE_CODIFICACAO = re.compile(br"<\?xml[^>]{0,100}?encoding\s*=\s*[\"']([A-Za-z0-9._:-]{1,40})[\"']")
_RE_FORA_DO_XML = re.compile(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f\ufffe\uffff]")
_RE_ENTIDADE = re.compile(r"&([A-Za-z][A-Za-z0-9]{1,31});")
_CODIFICACOES_RECUSADAS = ("utf-7", "unicode_escape", "raw_unicode_escape", "idna", "punycode", "undefined", "mbcs", "oem")
# Começo do arquivo -> codificação. As 5 primeiras são marcas de ordem de bytes; as 4 últimas, o "<" de um
# texto em UTF-16 ou UTF-32 sem marca. A de UTF-32 vem antes da de UTF-16, que é o começo dela.
_MARCAS_DE_ORDEM = ((codecs.BOM_UTF8, "utf-8"), (codecs.BOM_UTF32_LE, "utf-32-le"), (codecs.BOM_UTF32_BE, "utf-32-be"),
                    (codecs.BOM_UTF16_LE, "utf-16-le"), (codecs.BOM_UTF16_BE, "utf-16-be"),
                    (b"<\x00\x00\x00", "utf-32-le"), (b"\x00\x00\x00<", "utf-32-be"), (b"<\x00", "utf-16-le"),
                    (b"\x00<", "utf-16-be"))
NS_RSS = ("", "http://purl.org/rss/1.0/", "http://my.netscape.com/rdf/simple/0.9/")
NS_ATOM = ("http://www.w3.org/2005/Atom", "http://purl.org/atom/ns#")
NS_DC = ("http://purl.org/dc/elements/1.1/", "http://purl.org/dc/terms/")
NS_CONTEUDO = "http://purl.org/rss/1.0/modules/content/"


def _textos_possiveis(corpo):
    """O corpo como texto, nas codificações que valem tentar, da mais provável para a menos.

    Quem decide a codificação é esta função, e não o leitor de XML: assim o texto conferido contra
    DOCTYPE e ENTITY é exatamente o texto que o leitor recebe, mesmo com a declaração errada ou em UTF-16."""
    for posicao, (marca, nome) in enumerate(_MARCAS_DE_ORDEM):
        if corpo.startswith(marca):
            yield corpo[len(marca) if posicao < 5 else 0:].decode(nome, "replace")  # só a marca de ordem é pulada
            return
    declarada = _RE_CODIFICACAO.match(corpo.lstrip()[:200])
    tentadas = set()
    for nome in (declarada.group(1).decode("ascii") if declarada else "utf-8", "utf-8", "cp1252"):
        try:
            nome = codecs.lookup(nome).name
            if nome in tentadas or nome in _CODIFICACOES_RECUSADAS:
                continue
            tentadas.add(nome)
            yield corpo.decode(nome)
        except (LookupError, UnicodeError, ValueError):
            continue
    yield corpo.decode("utf-8", "replace")


def _troca_entidade(achado):
    """Entidade de HTML que o XML não conhece (&nbsp;, &eacute;) vira o caractere. As 5 do XML ficam."""
    nome = achado.group(1)
    if nome in ("amp", "lt", "gt", "quot", "apos"):
        return achado.group(0)
    valor = html.entities.html5.get(nome + ";")
    return achado.group(0) if valor is None else _escapa_xml(valor, {'"': "&quot;", "'": "&apos;"})


def abre_xml(corpo):
    """Bytes de um feed viram a árvore do XML. Devolve (raiz, "") ou (None, motivo)."""
    if not corpo.strip():
        return None, "resposta vazia"
    for texto in _textos_possiveis(corpo):
        declaracao = _RE_DECLARACAO.match(texto)  # só a do começo: a codificação já foi resolvida aqui
        texto = _RE_FORA_DO_XML.sub("", texto[declaracao.end():] if declaracao else texto)
        texto = _RE_ENTIDADE.sub(_troca_entidade, texto)
        # A conferência é feita no texto pronto, o mesmo que vai para o leitor de XML: tirar um caractere de
        # controle do meio de "<!DOC\x00TYPE" não pode montar um DOCTYPE depois de conferido.
        if _RE_HOSTIL.search(texto):
            return None, "tem DOCTYPE ou ENTITY: feed recusado"
        try:  # em bytes UTF-8 e com a codificação imposta: o leitor não tem como ler outra coisa
            return ET.fromstring(texto.encode("utf-8", "replace"), parser=ET.XMLParser(encoding="utf-8")), ""
        except (ET.ParseError, ValueError, RecursionError, LookupError):
            continue
    return None, "XML mal formado"


def _nome(elemento):
    """(espaço de nomes, nome local) de um elemento."""
    etiqueta = elemento.tag
    if not isinstance(etiqueta, str):
        return "?", ""
    if etiqueta.startswith("{"):
        espaco, _, local = etiqueta[1:].partition("}")
        return espaco, local
    return "", etiqueta


def _texto(elemento):
    return "".join(elemento.itertext())[:MAX_BRUTO]


def _item_rss(item):
    """Título, resumo, endereço e data de um <item>. RSS: pubDate; na falta, dc:date ou a data do Atom."""
    campos, datas = {}, {}
    for filho in item:
        espaco, local = _nome(filho)
        if espaco in NS_RSS:
            if local in ("title", "description", "link") and local not in campos:
                campos[local] = _texto(filho)
            elif local == "guid" and "guid" not in campos and (filho.get("isPermaLink") or "true").strip().lower() != "false":
                campos["guid"] = _texto(filho)
            elif local == "pubDate":
                datas.setdefault(0, _texto(filho))
        elif espaco in NS_DC and local == "date":
            datas.setdefault(1, _texto(filho))
        elif espaco in NS_ATOM:
            if local == "link" and (filho.get("rel") or "alternate").strip().lower() == "alternate" and filho.get("href"):
                campos.setdefault("atom", filho.get("href"))
            elif local in ("published", "issued"):
                datas.setdefault(2, _texto(filho))
        elif espaco == NS_CONTEUDO and local == "encoded":
            campos.setdefault("conteudo", _texto(filho))
    endereco = next((campos[c] for c in ("link", "guid", "atom") if campos.get(c, "").strip()), "")
    return {"titulo": campos.get("title", ""), "resumo": campos.get("description") or campos.get("conteudo", ""),
            "url": endereco, "data": datas[min(datas)] if datas else ""}


def _item_atom(entrada):
    """Título, resumo, endereço e data de um <entry>. Atom: published; só na falta dele, updated."""
    campos, datas = {}, {}
    for filho in entrada:
        espaco, local = _nome(filho)
        if espaco not in NS_ATOM:
            continue
        if local in ("title", "summary", "content") and local not in campos:
            campos[local] = _texto(filho)
        elif local == "link" and (filho.get("rel") or "alternate").strip().lower() == "alternate" and filho.get("href"):
            if "link" not in campos or "html" in (filho.get("type") or "").lower():
                campos["link"] = filho.get("href")
        elif local in ("published", "issued"):
            datas.setdefault(0, _texto(filho))
        elif local in ("updated", "modified"):
            datas.setdefault(1, _texto(filho))
    return {"titulo": campos.get("title", ""), "resumo": campos.get("summary") or campos.get("content", ""),
            "url": campos.get("link", ""), "data": datas[min(datas)] if datas else ""}


def le_feed(corpo):
    """As entradas cruas de um feed RSS (0.9x, 1.0, 2.0) ou Atom. Devolve (lista, "") ou (None, motivo)."""
    raiz, motivo = abre_xml(corpo)
    if raiz is None:
        return None, motivo
    espaco, local = _nome(raiz)
    crus = []
    if local == "feed" and espaco in NS_ATOM:
        crus = [_item_atom(filho) for filho in raiz if _nome(filho) in [(e, "entry") for e in NS_ATOM]][:MAX_ENTRADAS]
    elif local in ("rss", "RDF"):
        itens = []
        for filho in raiz:  # RSS 2.0: rss/channel/item. RSS 1.0: rdf:RDF/item, ao lado do channel
            if _nome(filho)[1] == "channel":
                itens.extend(neto for neto in filho if _nome(neto)[1] == "item" and _nome(neto)[0] in NS_RSS)
            elif _nome(filho)[1] == "item" and _nome(filho)[0] in NS_RSS:
                itens.append(filho)
        crus = [_item_rss(item) for item in itens[:MAX_ENTRADAS]]
    else:
        return None, "não é RSS nem Atom"
    return crus, ""


# ================================================================ mapa, fila e colheita (passos 1, 5 e 6)

_RE_ID = re.compile(r"[a-z0-9_]{1,60}")
_RE_HTTP = re.compile(r"(https?)://", re.I)


def le_mapa_siglas(raiz):
    """As siglas dos partidos, na ordem da régua: {id do partido: sigla}."""
    caminho = os.path.join(raiz, "dados", "regua.json")
    regua = comum.le_json(caminho)
    partidos = regua.get("partidos") if isinstance(regua, dict) else None
    if not isinstance(partidos, list) or not partidos or not all(
            isinstance(p, dict) and isinstance(p.get("id"), str) and isinstance(p.get("sigla"), str) for p in partidos):
        raise comum.Falha("%s: falta a lista partidos, com id e sigla" % caminho)
    return dict((p["id"], limpa(p["sigla"], 6)) for p in partidos)


def le_mapa(raiz):
    """Lê a régua (siglas dos partidos) e o mapa de veículos. Devolve (veiculos, siglas, avisos).

    Arquivo ilegível é Falha. Veículo torto dentro de um mapa legível é pulado, com aviso: quem confere
    o mapa campo a campo é o valida.py --dados, e a coleta do dia não para por causa de um registro."""
    siglas = le_mapa_siglas(raiz)
    caminho = os.path.join(raiz, "dados", "veiculos.json")
    mapa = comum.le_json(caminho)
    lista = mapa.get("veiculos") if isinstance(mapa, dict) else None
    if not isinstance(lista, list):
        raise comum.Falha("%s: falta a lista veiculos" % caminho)
    veiculos, avisos, vistos = [], [], set()
    for posicao, item in enumerate(lista):
        ident = item.get("id") if isinstance(item, dict) else None
        if not isinstance(ident, str) or not _RE_ID.fullmatch(ident) or ident in vistos:
            avisos.append("aviso: veiculos[%d] sem id que sirva: pulado" % posicao)
            continue
        if item.get("lado") not in siglas or item.get("fatos") not in ("alta", "media", "baixa"):
            avisos.append("aviso: veículo %s com lado ou fatos fora da régua: pulado" % ident)
            continue
        vistos.add(ident)
        feeds = [(feed["url"], feed.get("conferido") is True) for feed in item.get("feeds") or []
                 if isinstance(feed, dict) and isinstance(feed.get("url"), str) and feed.get("formato") in ("rss", "atom")]
        serve = [s for s in item.get("serve_a") or [] if isinstance(s, str) and _RE_ID.fullmatch(s) and s not in siglas]
        # Os sites do veículo: só entra na mesa a entrada cujo endereço é de um deles (CONTRATO, seção 1, passo 5).
        sites = [s.strip().lower() for s in item.get("sites") or [] if isinstance(s, str) and s.strip()]
        veiculos.append({"id": ident, "lado": item["lado"], "fatos": item["fatos"], "serve_a": serve,
                         "incerto": item.get("lado_confianca") == "baixa", "sites": sites, "feeds": feeds})
    return veiculos, siglas, avisos


def monta_fila(veiculos, siglas):
    """Passo 1. Primeiro todos os feeds de `conferido: true`, depois os outros. Dentro de cada bloco, um
    feed de cada partido por vez, na ordem da régua; dentro do partido, o primeiro feed de cada veículo
    antes do segundo de qualquer um. Assim o corte do --tempo cai no fim da fila, que são os feeds nunca
    conferidos, e não cai sempre no mesmo partido nem no mesmo veículo. Devolve [(veículo, url)]."""
    fila = []
    for conferido in (True, False):
        por_partido = dict((lado, []) for lado in siglas)
        for ordem, veiculo in enumerate(veiculos):
            for posicao, (url, marca) in enumerate(veiculo["feeds"]):
                if marca is conferido:
                    por_partido[veiculo["lado"]].append((posicao, ordem, veiculo, url))
        filas = [sorted(lista, key=lambda t: t[:2]) for lista in por_partido.values()]
        while any(filas):
            for lista in filas:
                if lista:
                    fila.append(lista.pop(0)[2:])
    return fila


def endereco_de(cru):
    """O endereço de uma entrada, pronto para gravar (passo 6): sem `#…` e sem `utm_`. Texto vazio se não
    começa com http:// ou https:// (endereço relativo também sai: a coleta não adivinha a base), se não
    tem nome de site público (a mesma regra dos pedidos de rede: nada de IP, de localhost, de usuário e
    senha), se passa de 500 caracteres, se traz caractere que não se vê, ou se traz aspas, apóstrofo, crase,
    cifrão ou barra invertida (ESQUEMA, seção 0, "URL": a URL da mesa pode ir para uma linha de comando)."""
    texto = cru.strip() if isinstance(cru, str) else ""
    if not texto or _RE_INVISIVEL.search(texto):
        return ""
    esquema = _RE_HTTP.match(texto)
    if not esquema:
        return ""
    texto = comum.sem_rastreio(esquema.group(1).lower() + texto[esquema.end(1):])
    return texto if comum.url_valida(texto) and not rede.recusa(texto) else ""


def colhe(veiculo, resposta, agora, horas, por_feed):
    """De uma resposta, as manchetes do feed que valem. Devolve (estado, erro, manchetes, fora_do_site).

    `fora_do_site` conta as entradas da janela, com título e endereço que serviriam, que caíram porque o
    site do endereço não bate com os `sites` do veículo: um feed comprometido, ou de agregador, não põe
    na mesa o endereço de outro site com o nome do veículo. O número fica em coleta.json para o dono ver
    o feed legítimo que usa domínio de redirecionamento e acrescentar esse domínio em `sites`."""
    if resposta is None:
        return "erro", "não coube no tempo", [], 0
    if not resposta.boa:
        return "erro", resposta.falha(), [], 0
    if resposta.cortada:
        return "erro", "resposta maior que 2 MB", [], 0
    crus, motivo = le_feed(resposta.corpo)
    if crus is None:
        return "erro", motivo, [], 0
    de, ate = agora - timedelta(hours=horas), agora + FUTURO
    validas, fora = [], 0
    for ordem, cru in enumerate(crus):
        instante = le_instante(cru["data"])
        if instante is None or not de <= instante <= ate:
            continue
        endereco = endereco_de(cru["url"])
        titulo = limpa(cru["titulo"], MAX_TITULO)
        if not (endereco and titulo):  # sem título não há manchete
            continue
        if not comum.url_bate(endereco, veiculo["sites"]):
            fora += 1
            continue
        validas.append((-instante.timestamp(), ordem, instante, endereco, titulo, cru["resumo"]))
    validas.sort(key=lambda v: v[:2])  # as mais novas na frente: entre duas repetidas, fica a mais nova
    enderecos, titulos, manchetes = set(), set(), []
    for _, ordem, instante, endereco, titulo, resumo in validas:
        marca_endereco, marca_titulo = comum.endereco_limpo(endereco), chave(titulo)
        if marca_endereco in enderecos or marca_titulo in titulos:
            continue
        enderecos.add(marca_endereco)
        titulos.add(marca_titulo)
        if len(manchetes) == por_feed:
            break
        # Endereço dentro do resumo vira "[link]": na mesa, o único endereço de cada manchete é o dela.
        # E não começa com "#", "-" ou "[": a linha do resumo não pode parecer cabeçalho nem manchete da mesa.
        resumo = limpa(_RE_LINK.sub("[link]", limpa(resumo, MAX_BRUTO)).lstrip("#-[]>*=| "), MAX_RESUMO)
        manchetes.append({
            "id": "", "historia": "", "veiculo": veiculo["id"], "lado": veiculo["lado"], "fatos": veiculo["fatos"],
            "titulo": titulo, "resumo": "" if chave(resumo) == marca_titulo else resumo, "url": endereco,
            "publicado_em": comum.texto_data_hora(instante), "categoria": categoria_de(titulo, resumo),
            "suspeito": parece_ordem(titulo, resumo), "_quando": instante, "_ordem": ordem})
    return ("ok" if manchetes else "vazio"), "", manchetes, fora


def junta(por_feed):
    """Passo 6, entre feeds: tira a manchete de endereço limpo repetido e a de título repetido no mesmo
    veículo, ficando com a mais nova, e numera (m0001 é a mais nova). `por_feed` vem na ordem da fila,
    e é essa ordem, e não a de chegada das respostas, que desempata: mesma entrada, mesma saída."""
    todas = []
    for fila, manchetes in enumerate(por_feed):
        for manchete in manchetes:
            todas.append((-manchete.pop("_quando").timestamp(), fila, manchete.pop("_ordem"), manchete))
    todas.sort(key=lambda t: t[:3])
    enderecos, titulos, ficam = set(), set(), []
    for _, _, _, manchete in todas:
        marca_endereco = comum.endereco_limpo(manchete["url"])
        marca_titulo = (manchete["veiculo"], chave(manchete["titulo"]))
        if marca_endereco in enderecos or marca_titulo in titulos:
            continue
        enderecos.add(marca_endereco)
        titulos.add(marca_titulo)
        manchete["id"] = "m%04d" % (len(ficam) + 1)
        ficam.append(manchete)
    return ficam


# ================================================================ histórias (passos 9 e 10)
#
# COMO AS MANCHETES SÃO AGRUPADAS. É palpite: o agente confirma. O erro que se quer evitar é juntar
# assuntos diferentes numa história só; deixar de juntar duas manchetes do mesmo assunto custa menos.
#
# 1. De cada título saem MARCAS: nomes próprios e números.
#    - Em alfabeto com maiúscula (latino, cirílico, grego): palavra que começa com maiúscula, sem acento e
#      sem diferença de caixa ("Rússia" e "RUSSIA" dão "russia"). Palavra que aparece em minúscula em outra
#      manchete do dia não é nome próprio: é assim que "Minister" e "Says", dos títulos em que toda palavra
#      leva maiúscula, ficam de fora. Uma lista curta de palavras de manchete faz o mesmo quando o dia é pequeno.
#    - Número: "25%", "1,5" (igual a "1.5"), "F-16", "G20". Algarismo sozinho e ano não contam.
#    - Em alfabeto sem maiúscula (árabe, hebraico, hindi, coreano), não dá para saber o que é nome: toda
#      palavra é marca, e vale menos. Em escrita sem espaço entre palavras (chinês, japonês, tailandês),
#      a marca é cada par de letras vizinhas, e vale menos ainda.
# 2. Nome muito comum não junta ninguém. Sai da conta a marca que está numa lista fixa (EUA, China, Rússia,
#    Trump, UE, ONU…) e a que aparece em mais de 5% dos títulos do mesmo tipo de escrita (o teto nunca é
#    menor que 10 títulos nem maior que 40): num dia em que todo mundo fala de um lugar, o nome dele
#    deixa de distinguir.
#    Marca que só aparece em um título também não serve para nada.
# 3. Duas manchetes se ligam quando têm em comum 2 nomes ou números que sobraram (ou 3 palavras de
#    alfabeto sem maiúscula, ou 4 pares de letras). Um nome só nunca liga: "Macron" em duas manchetes
#    pode ser duas notícias. Título que cita nomes demais (mais de 12) não liga ninguém: é resumo do dia,
#    ou isca para costurar várias histórias numa só.
# 4. História é o conjunto de manchetes ligadas, direta ou indiretamente. Títulos iguais (sem diferença de
#    maiúsculas nem de acentos) ficam sempre juntos, tenham ou não marcas, e contam como um título só em
#    todas as contas acima e abaixo.
# 5. Ligação indireta costura: A liga com B, B com C, e no fim A e Z não têm nada em comum. Por isso a
#    história que passa de 40 manchetes é refeita só com as ligações de 3 nomes em comum; se ainda passar,
#    de 4; e assim até 6. O que sobra junto depois disso são títulos quase iguais.
#
# LIMITES, DE PROPÓSITO. Nome próprio escrito em alfabeto não latino não casa com o mesmo nome em alfabeto
# latino ("Путин" e "Putin"), nem com a grafia de outra língua ("Ormuz" e "Hormuz"): a mesma notícia pode
# sair em duas histórias. Manchetes que só têm um nome em comum ficam separadas. Tudo aqui depende só dos
# títulos e da ordem das manchetes, que é fixa: a mesma coleta dá sempre as mesmas histórias.

PESO = {"n": 6, "p": 4, "b": 3}   # nome ou número; palavra de alfabeto sem maiúscula; par de letras
MAX_MARCAS = {"n": 12, "p": 30, "b": 60}  # título com mais marcas que isso é lista ou isca: não liga ninguém
LIGA = 12                         # 2 nomes, ou 3 palavras, ou 4 pares
MAX_HISTORIA, LIGA_MAXIMA = 40, 36  # história com mais de 40 manchetes é refeita com régua mais dura, até 6 nomes
TETO_MINIMO, TETO_MAXIMO, TETO_FRACAO = 10, 40, 20  # "muito comum": mais de 5% dos títulos (1 em 20)

# Escritas sem espaço entre palavras: tailandês e laosiano, birmanês, khmer, kana, ideogramas.
_SEM_ESPACO = r"\u0e00-\u0eff\u1000-\u109f\u1780-\u17ff\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
_RE_SIGLA_COM_PONTO = re.compile(r"\b(?:[A-Za-z]\.){2,}")
_RE_TERMO = re.compile(
    r"(?P<n>[A-Za-z]{0,6}-?[0-9][0-9A-Za-z]*(?:[.,-][0-9A-Za-z]+)*%?)"
    r"|(?P<b>[" + _SEM_ESPACO + r"]+)"
    r"|(?P<p>(?:(?![" + _SEM_ESPACO + r"])[^\W\d_])+)")
_RE_ANO = re.compile(r"(?:19|20)[0-9]{2}")

# Palavras de manchete que levam maiúscula sem ser nome (começo de frase, título em que tudo é maiúsculo,
# cargo, dia, mês) e nomes que estão no noticiário todo dia. Escritas já na forma de chave(): sem acento.
_PARADAS = frozenset("""
a o as os um uma uns umas de do da dos das em no na nos nas por para com sem sob sobre entre apos ate desde como que
se nao mais menos ja ainda tambem diz dizem disse afirma anuncia quer vai pode deve novo nova novos novas governo
presidente ministro ministra premie primeiro primeira lider chefe pais paises mundo guerra paz acordo crise ataque
veja saiba entenda por que quem onde quando hoje ontem amanha segunda terca quarta quinta sexta sabado domingo
janeiro fevereiro marco abril maio junho julho agosto setembro outubro novembro dezembro
the an and or but of in on at to for from by with without after before over under amid amidst against into as is are
was were be been has have had will would could should may might says said say tells told warns calls urges seeks
vows new news latest live update updates breaking analysis opinion video watch report reports exclusive what why how
who when where this that these those his her its their our your not more less than about up down out off first last
president minister prime government leader leaders chief official officials country countries world war peace deal
talks crisis attack attacks court police state states national international monday tuesday wednesday thursday
friday saturday sunday january february march april june july august september october november december
el la los las un una unos unas del al y e en con sin sobre entre tras desde hasta como que se no mas dice
afirma anuncia nuevo nueva gobierno presidente ministro lider pais mundo guerra paz acuerdo crisis ataque
le les des du et ou dans sur sous avec sans pour par apres avant contre selon dit annonce nouveau nouvelle
gouvernement president ministre pays monde guerre paix accord crise attaque
der die das den dem des ein eine und oder in im an auf mit ohne nach vor gegen uber bei von zu zum zur ist sind
в на по из за от до для при как что это после перед против президент министр страна
eua usa us ee uu eeuu america american americano americana americanos estados unidos united washington trump biden
china chinese chines chinesa chineses pequim beijing xi jinping russia russian russo russa russos rusia russie
moscou moscow kremlin putin ue eu europa europe european europeu europeia europeus bruxelas brussels onu un nato otan
israel israeli israelense gaza hamas ira iran iranian iraniano ucrania ukraine ukrainian ucraniano kiev kyiv
brasil brazil brazilian brasileiro brasileira lula india japan japao germany alemanha france franca uk britain
british reino ia ai сша россия россии китаи китая украина украины трамп трампа путин путина
أمريكا الصين روسيا ترامب إسرائيل غزة إيران في من على إلى عن مع أن بعد قبل بين حول خلال ضد هذا هذه التي الذي ما لا قد كل أو ثم
של על את עם זה לא כי גם אל או אם הוא היא
""".split())
_PARES_PARADOS = frozenset(nome[i:i + 2] for nome in "美国 中国 俄罗斯 特朗普 普京 欧盟 以色列 乌克兰 伊朗 日本 表示 政府".split()
                           for i in range(len(nome) - 1))


def marcas_de(titulo):
    """As marcas de um título e as palavras que ele traz em minúscula. Devolve (conjunto de (tipo, texto), conjunto)."""
    marcas, minusculas = set(), set()
    for achado in _RE_TERMO.finditer(_RE_SIGLA_COM_PONTO.sub(lambda a: a.group().replace(".", ""), titulo)):
        termo = achado.group()
        if achado.lastgroup == "n":
            marca = chave(termo).replace(",", ".")
            so_numero = all(c.isdigit() or c in ".-%" for c in marca)
            if _RE_ANO.fullmatch(marca) or (so_numero and sum(c.isdigit() for c in marca) < 2 and "%" not in marca):
                continue  # ano e algarismo sozinho aparecem em toda parte
            marcas.add(("n", marca))
        elif achado.lastgroup == "b":
            marcas.update(("b", termo[i:i + 2]) for i in range(min(len(termo), 60) - 1)
                          if termo[i:i + 2] not in _PARES_PARADOS)
        elif termo[0].islower():
            minusculas.add(chave(termo))
        else:
            marca = chave(termo)
            com_caixa = termo[0].isupper() or termo[0].istitle()
            minimo = 3 if com_caixa and not termo.isupper() else 2  # sigla de 2 letras vale: "UE", "EU"
            if len(marca) >= minimo and marca not in _PARADAS:
                marcas.add(("n" if com_caixa else "p", marca))
    return marcas, minusculas


def agrupa(titulos):
    """Passo 9: recebe os títulos e devolve os grupos, cada um como lista crescente de posições.

    Títulos iguais (sem diferença de maiúsculas nem de acentos) ficam sempre no mesmo grupo: é a garantia
    mínima do CONTRATO, seção 1, passo 9. As contas de marcas são feitas uma vez por título distinto, e
    não por manchete: a mesma manchete repetida em 30 veículos é um assunto, e não torna os nomes dela
    "muito comuns"."""
    posicoes_de, distintos = {}, []
    for posicao, titulo in enumerate(titulos):
        marca = chave(titulo)
        if marca not in posicoes_de:
            posicoes_de[marca] = []
            distintos.append(titulo)
        posicoes_de[marca].append(posicao)
    grupos = []
    for grupo in _agrupa_distintos(distintos):
        grupos.append(sorted(p for indice in grupo for p in posicoes_de[chave(distintos[indice])]))
    return sorted(grupos)


def _agrupa_distintos(titulos):
    """O agrupamento por marcas em comum (passos 1 a 5 do comentário acima), sobre títulos distintos."""
    por_titulo, minusculas = [], set()
    for titulo in titulos:
        marcas, pequenas = marcas_de(titulo)
        por_titulo.append(marcas)
        minusculas |= pequenas
    onde, titulos_do_tipo = {}, {}
    for posicao, marcas in enumerate(por_titulo):
        marcas = set(m for m in marcas if not (m[0] == "n" and m[1] in minusculas))
        for tipo, teto in MAX_MARCAS.items():
            if sum(1 for m in marcas if m[0] == tipo) > teto:
                marcas = set(m for m in marcas if m[0] != tipo)
        for tipo in set(m[0] for m in marcas):
            titulos_do_tipo[tipo] = titulos_do_tipo.get(tipo, 0) + 1
        for marca in marcas:
            onde.setdefault(marca, []).append(posicao)
    pesos = {}
    for marca, posicoes in onde.items():
        teto = min(TETO_MAXIMO, max(TETO_MINIMO, titulos_do_tipo[marca[0]] // TETO_FRACAO))
        if not 2 <= len(posicoes) <= teto:
            continue
        for i, primeira in enumerate(posicoes):
            for segunda in posicoes[i + 1:]:
                pesos[(primeira, segunda)] = pesos.get((primeira, segunda), 0) + PESO[marca[0]]
    vizinhos = {}
    for (primeira, segunda), peso in pesos.items():
        if peso >= LIGA:
            vizinhos.setdefault(primeira, []).append((segunda, peso))
            vizinhos.setdefault(segunda, []).append((primeira, peso))

    def ligadas(membros, limiar):
        """Os conjuntos de manchetes ligadas entre si, direta ou indiretamente, por ligações de peso `limiar` ou mais."""
        dentro, vistas, grupos = set(membros), set(), []
        for semente in membros:
            if semente in vistas:
                continue
            vistas.add(semente)
            fila, grupo = [semente], []
            while fila:
                atual = fila.pop()
                grupo.append(atual)
                for outra, peso in vizinhos.get(atual, ()):
                    if peso >= limiar and outra in dentro and outra not in vistas:
                        vistas.add(outra)
                        fila.append(outra)
            grupos.append(sorted(grupo))
        return grupos

    prontos, pendentes = [], [(list(range(len(titulos))), LIGA)]
    while pendentes:
        membros, limiar = pendentes.pop()
        for grupo in ligadas(membros, limiar):
            if len(grupo) > MAX_HISTORIA and limiar < LIGA_MAXIMA:
                pendentes.append((grupo, limiar + PESO["n"]))  # grande demais: refaz pedindo mais um nome em comum
            else:
                prontos.append(grupo)
    return sorted(prontos)


def monta_historias(manchetes, siglas):
    """Passos 9 e 10: agrupa, pontua (3 por partido distinto mais 1 por veículo distinto, até 3) e ordena.
    Preenche `historia` em cada manchete e devolve a lista de histórias, a de mais pontos primeiro."""
    ordem_dos_partidos = list(siglas)
    historias = []
    for grupo in agrupa([m["titulo"] for m in manchetes]):
        membros = [manchetes[posicao] for posicao in grupo]
        partidos = [lado for lado in ordem_dos_partidos if any(m["lado"] == lado for m in membros)]
        veiculos = len(set(m["veiculo"] for m in membros))
        de_ia = sum(1 for m in membros if m["categoria"] == "ia")
        historias.append({"id": "", "pontos": 3 * len(partidos) + min(3, veiculos),
                          "categoria": "ia" if 2 * de_ia > len(membros) else "geopolitica",  # a maioria
                          "partidos": partidos, "veiculos": veiculos, "manchetes": [m["id"] for m in membros]})
    # Empate de pontos: mais veículos, depois mais manchetes, depois a de manchete mais nova (id menor).
    historias.sort(key=lambda h: (-h["pontos"], -h["veiculos"], -len(h["manchetes"]), h["manchetes"][0]))
    por_id = dict((m["id"], m) for m in manchetes)
    for numero, historia in enumerate(historias, 1):
        historia["id"] = "h%02d" % numero
        for ident in historia["manchetes"]:
            por_id[ident]["historia"] = historia["id"]
    return historias


# ================================================================ mesa.txt

_FATOS = ("alta", "media", "baixa")
# Para caber em 60 KB: (manchetes por história, tamanho do resumo). Vale o primeiro degrau que couber.
_ESCADA = ((8, 300), (8, 240), (8, 180), (6, 180), (6, 120), (5, 120), (4, 120), (4, 60), (4, 0), (3, 0), (2, 0), (1, 0))


def _plural(quantos, um, varios):
    return "%d %s" % (quantos, um if quantos == 1 else varios)


def escolhe(membros, maximo, siglas):
    """As manchetes de uma história que vão para a mesa: até `maximo`, no máximo 2 por veículo, alternando
    os partidos na ordem da régua. Dentro do partido: a mais nova de cada veículo antes da segunda de
    qualquer um, e veículo de fatos `alta` na frente."""
    filas = []
    for lado in siglas:
        vez, do_lado = {}, []
        for manchete in membros:  # já vêm da mais nova para a mais velha
            if manchete["lado"] != lado:
                continue
            ja = vez.get(manchete["veiculo"], 0)
            vez[manchete["veiculo"]] = ja + 1
            if ja < MESA_POR_VEICULO:
                do_lado.append((ja, _FATOS.index(manchete["fatos"]), manchete["id"], manchete))
        if do_lado:
            filas.append([item[3] for item in sorted(do_lado, key=lambda item: item[:3])])
    escolhidas = []
    while len(escolhidas) < maximo and any(filas):
        for fila in filas:
            if fila and len(escolhidas) < maximo:
                escolhidas.append(fila.pop(0))
    return escolhidas


def _bloco(historia, por_id, veiculos, siglas, maximo, tamanho_do_resumo):
    """As linhas de uma história, no formato do CONTRATO, seção 1."""
    linhas = ["### %s · %d pontos · partidos %d (%s) · veículos %d · %s" % (
        historia["id"], historia["pontos"], len(historia["partidos"]),
        " ".join(siglas[lado] for lado in historia["partidos"]), historia["veiculos"], historia["categoria"])]
    for manchete in escolhe([por_id[i] for i in historia["manchetes"]], maximo, siglas):
        veiculo = veiculos[manchete["veiculo"]]
        quando = comum.le_data_hora(manchete["publicado_em"])
        partes = ["[%s%s] %s" % (siglas[manchete["lado"]], "?" if veiculo["incerto"] else "", manchete["veiculo"])]
        if veiculo["serve_a"]:
            partes.append("serve a: " + ", ".join(veiculo["serve_a"]))
        partes.append("fatos " + manchete["fatos"])
        partes.append("%02d/%02d %02d:%02d UTC" % (quando.day, quando.month, quando.hour, quando.minute))
        partes.append(("[SUSPEITA] " if manchete["suspeito"] else "") + manchete["titulo"])
        linhas.append("- " + " · ".join(partes))
        resumo = manchete["resumo"]
        if resumo and tamanho_do_resumo and not manchete["suspeito"]:  # a suspeita vem só com o título
            if len(resumo) > tamanho_do_resumo:
                resumo = resumo[:tamanho_do_resumo - 1].rstrip() + "…"
            linhas.append("  " + resumo)
        linhas.append("  " + manchete["url"])
    return linhas


def monta_mesa(dia, horas, resumo, siglas, historias, manchetes, veiculos):
    """O texto de mesa.txt e o degrau usado. As 3 primeiras linhas (a 3ª é a legenda) ficam sempre; depois
    vêm as 40 histórias de mais pontos e, no fim, a seção `### IA`, com até 10 histórias de IA que ficaram
    de fora. Para caber em 60 KB, desce a escada (_ESCADA): todas as histórias perdem manchetes e resumo
    por igual, e só depois saem histórias inteiras, do fim, primeiro as da seção IA. Assim a história de
    mais pontos nunca sai antes de uma de menos."""
    cabeca = ["MESA %s · janela %d h · feeds ok %d, falhos %d · manchetes %d · suspeitas: %d" % (
        dia, horas, resumo["feeds_ok"], resumo["feeds_falhos"], resumo["manchetes"], resumo["suspeitas"]),
        "PARTIDOS COM MANCHETE: " + (" · ".join("%s %d" % (siglas[lado], resumo["partidos"][lado]) for lado in siglas)
                                     or "nenhum"), LEGENDA]
    por_id = dict((m["id"], m) for m in manchetes)
    principais = historias[:MESA_HISTORIAS]
    de_ia = [h for h in historias[MESA_HISTORIAS:] if h["categoria"] == "ia"][:IA_HISTORIAS]

    def texto(principais, de_ia, maximo, tamanho):
        # Sem história, a mesa é só o topo: a 1ª linha já diz "manchetes 0" (CONTRATO, seção 1, mesa.txt).
        # A linha "### IA" só aparece se houver história para pôr nela.
        linhas = list(cabeca)
        for historia in principais:
            linhas += [""] + _bloco(historia, por_id, veiculos, siglas, maximo, tamanho)
        if de_ia:
            linhas += ["", "### IA"]
        for historia in de_ia:
            linhas += [""] + _bloco(historia, por_id, veiculos, siglas, min(maximo, IA_MANCHETES), tamanho)
        return "\n".join(linhas) + "\n"

    for degrau in _ESCADA:
        pronto = texto(principais, de_ia, degrau[0], degrau[1])
        if len(pronto.encode("utf-8")) <= MESA_BYTES:
            return pronto, degrau, len(principais), len(de_ia)
    while True:  # nem com 1 manchete por história coube (títulos e endereços enormes): saem histórias do fim
        if de_ia:
            de_ia = de_ia[:-1]
        elif principais:
            principais = principais[:-1]
        pronto = texto(principais, de_ia, 1, 0)
        if len(pronto.encode("utf-8")) <= MESA_BYTES or not (principais or de_ia):
            return pronto, _ESCADA[-1], len(principais), len(de_ia)


# ================================================================ --confere: a data das páginas (seção 1.1)

_RE_META = re.compile(r"<meta\b([^<>]{0,2000})>", re.I)
_RE_ATRIBUTO = re.compile(r"([A-Za-z_:][-A-Za-z0-9_:.]{0,60})\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s\"'>]+)")
_RE_SCRIPT = re.compile(r"<script\b([^<>]{0,1000})>", re.I)
_RE_FIM_SCRIPT = re.compile(r"</script\s*>", re.I)
_RE_DATA_SOLTA = re.compile(r"\"datePublished\"\s*:\s*\"([^\"\\]{1,64})\"")
_RE_LINK = re.compile(r"(?:https?://|www\.)\S+", re.I)
MAX_BLOCOS, MAX_NOS = 50, 20000


def _atributos(texto):
    return dict((nome.lower(), html.unescape(valor.strip("\"'")).strip())
                for nome, valor in _RE_ATRIBUTO.findall(texto))


def _dia_utc(texto):
    """Uma data de página vira o dia em UTC (AAAA-MM-DD), ou None."""
    instante = le_instante(texto)
    return instante.date().isoformat() if instante is not None and 1990 <= instante.year <= 2100 else None


def _datas_do_json(objeto):
    """Os valores de "datePublished" de um bloco JSON-LD, na ordem do texto: (os de artigo, os outros)."""
    de_artigo, outras, pilha, vistos = [], [], [objeto], 0
    while pilha and vistos < MAX_NOS:
        no = pilha.pop()
        vistos += 1
        if isinstance(no, list):
            pilha.extend(reversed(no))
        elif isinstance(no, dict):
            data = no.get("datePublished")
            if isinstance(data, str):
                tipos = no.get("@type")
                tipos = " ".join(t for t in (tipos if isinstance(tipos, list) else [tipos]) if isinstance(t, str)).lower()
                (de_artigo if ("article" in tipos or "posting" in tipos) else outras).append(data)
            pilha.extend(reversed([valor for valor in no.values() if isinstance(valor, (dict, list))]))
    return de_artigo, outras


def data_da_pagina(texto):
    """A data de publicação de uma página HTML, lida em dois lugares e só neles, nesta ordem:
    <meta property="article:published_time"> e "datePublished" num bloco JSON-LD. Devolve AAAA-MM-DD ou None.
    Nada da página é seguido nem executado: o texto é só procurado."""
    for numero, achado in enumerate(_RE_META.finditer(texto)):
        if numero >= 2000:
            break
        atributos = _atributos(achado.group(1))
        if (atributos.get("property") or atributos.get("name") or "").lower() == "article:published_time":
            dia = _dia_utc(atributos.get("content"))
            if dia:
                return dia
    # A página pode trazer vários blocos, e um deles pode listar outras matérias, cada uma com a sua data.
    # Vale a primeira data de um objeto que se diz artigo (NewsArticle, BlogPosting…); só na falta, a primeira que houver.
    de_artigo, outras, posicao, blocos = [], [], 0, 0
    while blocos < MAX_BLOCOS:  # cada busca começa onde a anterior parou: uma passada só pelo texto
        abre = _RE_SCRIPT.search(texto, posicao)
        if not abre:
            break
        fecha = _RE_FIM_SCRIPT.search(texto, abre.end())
        if not fecha:
            break
        posicao = fecha.end()
        if _atributos(abre.group(1)).get("type", "").lower() != "application/ld+json":
            continue
        blocos += 1
        bloco = texto[abre.end():fecha.start()].replace("<!--", " ").replace("-->", " ")
        bloco = bloco.replace("<![CDATA[", " ").replace("]]>", " ").strip()
        try:
            do_bloco = _datas_do_json(json.loads(bloco))
        except (ValueError, RecursionError):  # JSON-LD quebrado é comum: procura o campo no texto do bloco
            do_bloco = ([], _RE_DATA_SOLTA.findall(bloco)[:20])
        de_artigo += do_bloco[0]
        outras += do_bloco[1]
    for candidata in de_artigo + outras:
        dia = _dia_utc(candidata)
        if dia:
            return dia
    return None


_TIPOS_HTML = ("text/html", "application/xhtml+xml")


def _e_html(resposta):
    """A página é lida quando não há Content-Type, ou quando ele é text/html ou application/xhtml+xml
    (CONTRATO, seção 1.1). Os parâmetros (`; charset=…`) não contam."""
    tipo = resposta.tipo.split(";", 1)[0].strip().lower()
    return not tipo or tipo in _TIPOS_HTML


def confere_pagina(resposta):
    """Estado e data de uma página (CONTRATO, seção 1.1). Devolve (estado, publicado_em)."""
    if resposta is None:
        return "bloqueada", None  # não respondeu a tempo
    if resposta.erro:  # só o nome de site que não existe (ou endereço que nem é de site) vira `erro`
        return ("erro" if resposta.motivo in (rede.NOME, rede.URL) else "bloqueada"), None
    if not resposta.boa:
        return ("erro" if resposta.status in (404, 410) else "bloqueada"), None
    if resposta.cortada:  # maior que 2 MB: a página veio, mas a ferramenta não aceita ler
        return "bloqueada", None
    if not _e_html(resposta):
        return "ok", None
    corpo = resposta.corpo
    for marca, nome in _MARCAS_DE_ORDEM[1:5]:
        if corpo.startswith(marca):
            return "ok", data_da_pagina(corpo[len(marca):].decode(nome, "replace"))
    return "ok", data_da_pagina(corpo.decode("utf-8", "replace"))


def le_urls(trabalho):
    """As URLs de P/urls.txt, uma por linha. Linha em branco é ignorada; linha que começa com # é comentário
    (o # no primeiro caractere da linha). Espaço nas pontas da URL é tirado. Devolve (urls, ilegíveis)."""
    try:
        with open(os.path.join(trabalho, "urls.txt"), "rb") as arquivo:
            bruto = arquivo.read(1024 * 1024)
    except OSError:
        return [], 0
    urls, ilegiveis = [], 0
    for linha in bruto.decode("utf-8-sig", "replace").splitlines()[:5000]:
        if linha.startswith("#") or not linha.strip():
            continue
        linha = linha.strip()
        if comum.url_valida(linha) and not _RE_INVISIVEL.search(linha):  # a URL vai para a saída: nada de controle
            urls.append(linha)
        else:
            ilegiveis += 1
    return urls, ilegiveis


def roda_confere(args, conexao, inicio, saida):
    destino = os.path.join(args.trabalho, "conferencia.json")
    urls, ilegiveis = le_urls(args.trabalho)
    da_coleta = set()
    try:
        coleta = comum.le_json(os.path.join(args.trabalho, "coleta.json"), se_faltar={})
        da_coleta = set(comum.endereco_limpo(m["url"]) for m in coleta.get("manchetes", [])
                        if isinstance(m, dict) and isinstance(m.get("url"), str))
    except (comum.Falha, AttributeError, TypeError):
        saida.linha("aviso: coleta.json ilegível: todas as URLs de urls.txt contam como novas")
    novas, vistas = [], set()
    for url in urls:
        marca = comum.endereco_limpo(url)
        if marca not in da_coleta and marca not in vistas:
            vistas.add(marca)
            novas.append(url)
    sobra, novas = len(novas) - MAX_PAGINAS, novas[:MAX_PAGINAS]
    prazo = rede.prazo_de(inicio, args.tempo)
    respostas = rede.em_paralelo(lambda url: conexao.baixa(url, POR_PEDIDO, prazo, aceita=ACEITA_PAGINA),
                                 novas, PARALELOS, prazo)
    paginas = []
    for url, resposta in zip(novas, respostas):
        estado, dia = confere_pagina(resposta)
        paginas.append({"url": url, "estado": estado, "publicado_em": dia})
    sem_rede = bool(paginas) and not any(p["estado"] == "ok" for p in paginas)
    if sem_rede:  # nenhuma respondeu: não dá para distinguir página que não existe de máquina sem rede
        for pagina, resposta in zip(paginas, respostas):
            # Ficam `erro` a URL que nem pode ser pedida e a resposta 404 ou 410: as duas não dependem da rede
            # (a 404 é um servidor dizendo que a página não existe).
            if not (resposta is not None and (resposta.motivo == rede.URL
                                             or (not resposta.erro and resposta.status in (404, 410)))):
                pagina["estado"] = "bloqueada"
    comum.grava_json(destino, {"versao": 1, "gerada_em": comum.agora_texto(), "paginas": paginas})
    args.gravado = True

    conta = dict((estado, sum(1 for p in paginas if p["estado"] == estado)) for estado in ("ok", "bloqueada", "erro"))
    com_data = sum(1 for p in paginas if p["publicado_em"])
    saida.linha("CONFERE · %s em urls.txt, %d fora da coleta" % (_plural(len(urls), "URL", "URLs"), len(novas) + max(sobra, 0)))
    if ilegiveis:
        saida.linha("aviso: %s de urls.txt não é URL http(s): pulada" % _plural(ilegiveis, "linha", "linhas"))
    if sobra > 0:
        saida.linha("aviso: %s ficaram sem conferir: o teto é de %d por execução" % (_plural(sobra, "URL", "URLs"), MAX_PAGINAS))
    for pagina, resposta in zip(paginas, respostas):
        saida.linha("%s · %s · %s" % (pagina["estado"], pagina["publicado_em"] or (
            "sem data" if pagina["estado"] == "ok" else "não coube no tempo" if resposta is None else resposta.falha()),
            pagina["url"]))
    saida.linha("gravado: %s" % destino)
    saida.dado("arquivo", destino)
    saida.dado("paginas", conta)
    saida.dado("fora_do_teto", max(sobra, 0))
    # As URLs além da 30ª ficam fora de conferencia.json; a última linha diz quantas (CONTRATO, seção 1.1).
    de_fora = "; %s fora do teto de %d" % (_plural(sobra, "URL", "URLs"), MAX_PAGINAS) if sobra > 0 else ""
    if sem_rede:
        return saida.fecha("FALHA sem rede: 0 páginas" + de_fora, comum.SEM_REDE)
    if not paginas:
        return saida.fecha("OK 0 páginas")
    return saida.fecha("OK %s: %d com data, %s, %d com erro%s" % (
        _plural(len(paginas), "página", "páginas"), com_data,
        _plural(conta["bloqueada"], "bloqueada", "bloqueadas"), conta["erro"], de_fora))


# ================================================================ a coleta

def _coleta_vazia(dia, horas, siglas):
    return {"versao": 1, "dia": dia, "gerada_em": comum.agora_texto(), "janela_horas": horas,
            "resumo": {"feeds_ok": 0, "feeds_falhos": 0, "veiculos_ok": 0, "manchetes": 0, "suspeitas": 0,
                       "partidos": dict((lado, 0) for lado in siglas)},
            "feeds": [], "manchetes": [], "historias": []}


def _grava_coleta(trabalho, objeto, mesa):
    """Os dois arquivos saem juntos, ou nenhum: a mesa nunca fica de uma coleta e o coleta.json de outra."""
    lote = comum.Lote()
    lote.json(os.path.join(trabalho, "coleta.json"), objeto)
    lote.texto(os.path.join(trabalho, "mesa.txt"), mesa)
    lote.grava()


def _janela(args, saida):
    """--horas; sem a opção, a `janela_horas` de P/contexto.json; sem o arquivo, 36 (CONTRATO, seção 1)."""
    if args.horas is not None:
        return args.horas
    contexto = comum.le_contexto(args.trabalho)  # quebrado: FALHA, código 1, nada gravado (CONTRATO, seção 0)
    if contexto is None:
        return HORAS
    janela = contexto.get("janela_horas")
    if isinstance(janela, int) and not isinstance(janela, bool) and 1 <= janela <= 720:
        return janela
    saida.linha("aviso: contexto.json sem janela_horas que sirva: vale a janela de %d h" % HORAS)
    return HORAS


def roda_coleta(args, conexao, inicio, saida):
    args.horas = _janela(args, saida)
    veiculos, siglas, avisos = le_mapa(args.raiz)
    fila = monta_fila(veiculos, siglas)
    prazo = rede.prazo_de(inicio, args.tempo)
    respostas = rede.em_paralelo(lambda par: conexao.baixa(par[1], POR_PEDIDO, prazo, aceita=ACEITA_FEED),
                                 fila, PARALELOS, prazo)
    agora = comum.agora()
    feeds, por_feed = [], []
    for (veiculo, url), resposta in zip(fila, respostas):  # na ordem da fila, e não na de chegada
        try:
            if resposta is not None and resposta.boa and time.monotonic() > inicio + args.tempo:
                # O teto é do comando inteiro: ler os feeds também conta. Só acontece com resposta
                # enorme e em quantidade; em dia normal a leitura de todos leva menos de 1 segundo.
                estado, erro, manchetes, fora = "erro", "não coube no tempo", [], 0
            else:
                estado, erro, manchetes, fora = colhe(veiculo, resposta, agora, args.horas, args.por_feed)
        except Exception as defeito:  # um feed que o leitor não previu não derruba a coleta dos outros
            estado, erro, manchetes, fora = "erro", "feed ilegível (%s)" % type(defeito).__name__, [], 0
        feeds.append({"veiculo": veiculo["id"], "url": url, "estado": estado, "itens": len(manchetes),
                      "fora_do_site": fora, "erro": erro})
        por_feed.append(manchetes)
    manchetes = junta(por_feed)
    historias = monta_historias(manchetes, siglas)

    responderam = [feed for feed in feeds if feed["estado"] != "erro"]
    resumo = {"feeds_ok": len(responderam), "feeds_falhos": len(feeds) - len(responderam),
              "veiculos_ok": len(set(feed["veiculo"] for feed in responderam)), "manchetes": len(manchetes),
              "suspeitas": sum(1 for m in manchetes if m["suspeito"]),
              "partidos": dict((lado, sum(1 for m in manchetes if m["lado"] == lado)) for lado in siglas)}
    objeto = {"versao": 1, "dia": args.dia, "gerada_em": comum.agora_texto(), "janela_horas": args.horas,
              "resumo": resumo, "feeds": feeds, "manchetes": manchetes, "historias": historias}
    mesa, degrau, na_mesa, na_ia = monta_mesa(args.dia, args.horas, resumo, siglas, historias, manchetes,
                                              dict((v["id"], v) for v in veiculos))
    _grava_coleta(args.trabalho, objeto, mesa)
    args.gravado = True

    com_manchete = sum(1 for feed in feeds if feed["estado"] == "ok")
    saida.linha("COLETA %s · janela %d h · %s na fila" % (args.dia, args.horas, _plural(len(feeds), "feed", "feeds")))
    saida.linha("feeds: %d responderam (%d com manchete, %d sem nada na janela), %d com erro"
                % (len(responderam), com_manchete, len(responderam) - com_manchete, resumo["feeds_falhos"]))
    erros = {}
    for feed in feeds:
        if feed["estado"] == "erro":
            erros[feed["erro"]] = erros.get(feed["erro"], 0) + 1
    if erros:
        saida.linha("erros: " + " · ".join("%d %s" % (quantos, erro) for erro, quantos in
                                           sorted(erros.items(), key=lambda par: (-par[1], par[0]))))
    com_fora = [feed for feed in feeds if feed["fora_do_site"]]
    if com_fora:
        saida.linha("aviso: %s com endereço fora dos sites do veículo, descartadas: %s" % (
            _plural(sum(feed["fora_do_site"] for feed in com_fora), "entrada", "entradas"),
            " · ".join("%d %s" % (feed["fora_do_site"], feed["url"]) for feed in com_fora[:10])))
    saida.linha("manchetes: %d de %s · suspeitas: %d" % (
        len(manchetes), _plural(len(set(m["veiculo"] for m in manchetes)), "veículo", "veículos"), resumo["suspeitas"]))
    saida.linha("partidos: " + " · ".join("%s %d" % (siglas[lado], resumo["partidos"][lado]) for lado in siglas))
    saida.linha("histórias: %d (%d na mesa, %d na seção IA)" % (len(historias), na_mesa, na_ia))
    if degrau != _ESCADA[0] or na_mesa < min(len(historias), MESA_HISTORIAS):
        saida.linha("mesa encurtada para caber em 60 KB: até %s por história, resumo de até %d caracteres"
                    % (_plural(degrau[0], "manchete", "manchetes"), degrau[1]))
    for aviso in avisos[:20]:
        saida.linha(aviso)
    saida.linha("gravado: %s e %s" % (os.path.join(args.trabalho, "coleta.json"), os.path.join(args.trabalho, "mesa.txt")))
    saida.dado("arquivos", [os.path.join(args.trabalho, "coleta.json"), os.path.join(args.trabalho, "mesa.txt")])
    saida.dado("resumo", resumo)

    partidos = sum(1 for quantas in resumo["partidos"].values() if quantas)
    if not responderam:
        return saida.fecha("FALHA sem rede: 0 feeds", comum.SEM_REDE)
    if len(responderam) >= 8 and partidos >= 3:
        return saida.fecha("OK %s, %s, %s" % (_plural(len(responderam), "feed", "feeds"),
                                              _plural(len(manchetes), "manchete", "manchetes"),
                                              _plural(na_mesa, "história", "histórias")))
    return saida.fecha("PARCIAL %s, %s" % (_plural(len(responderam), "feed", "feeds"),
                                           _plural(partidos, "partido", "partidos")))


# ================================================================ linha de comando

def _inteiro(minimo, maximo):
    def le(texto):
        try:
            valor = int(texto)
        except ValueError:
            valor = minimo - 1
        if not minimo <= valor <= maximo:
            raise argparse.ArgumentTypeError("use um número inteiro de %d a %d" % (minimo, maximo))
        return valor
    return le


def _pasta(texto):
    if not texto.strip():
        raise argparse.ArgumentTypeError("falta o nome da pasta")
    return texto


def _socorro(args, siglas, dia=None):
    """Grava a saída vazia quando a execução para no meio por um erro que ninguém previu (FALHA interna):
    a ferramenta chegou a rodar, e o passo seguinte não pode ler por engano o arquivo de uma execução
    anterior. Erro de uso e entrada ilegível (mapa, régua, contexto.json) não gravam nada (CONTRATO, seção 0)."""
    try:
        pasta = os.path.abspath(args.trabalho)
        if not os.path.isdir(pasta):
            return
        if args.confere:
            comum.grava_json(os.path.join(pasta, "conferencia.json"),
                             {"versao": 1, "gerada_em": comum.agora_texto(), "paginas": []})
            return
        horas = args.horas if isinstance(args.horas, int) else HORAS
        vazia = _coleta_vazia(dia or comum.hoje_brasilia(), horas, siglas)
        _grava_coleta(pasta, vazia, monta_mesa(vazia["dia"], horas, vazia["resumo"], siglas, [], [], {})[0])
    except Exception:
        pass


def _siglas_se_der(raiz):
    try:
        return le_mapa_siglas(raiz)
    except Exception:
        return {}


def principal(argv):
    inicio = time.monotonic()
    an = comum.opcoes("Baixa as manchetes dos feeds dos veículos. Com --confere, confere a data das páginas de urls.txt.")
    an.add_argument("--horas", metavar="N", type=_inteiro(1, 720), default=None,
                    help="janela: só entra manchete das últimas N horas (padrão: a do contexto.json, ou 36)")
    an.add_argument("--tempo", metavar="S", type=_inteiro(1, 3600), default=None,
                    help="teto de tempo total, em segundos inteiros (padrão: 90; com --confere, 60)")
    an.add_argument("--por-feed", dest="por_feed", metavar="N", type=_inteiro(1, 200), default=POR_FEED,
                    help="no máximo N manchetes, as mais novas, por feed (padrão: 15)")
    an.add_argument("--confere", action="store_true", help="confere a data das páginas de urls.txt")
    an.add_argument("--offline", metavar="PASTA", type=_pasta, default=None,
                    help="no lugar da rede, lê PASTA/respostas.json (modo dos testes)")
    args = an.parse_args(argv)
    conexao = rede.Rede(offline=args.offline)  # --offline que não serve é erro de uso: antes de qualquer gravação
    if args.tempo is None:
        args.tempo = TEMPO_CONFERE if args.confere else TEMPO
    # O --confere não usa o dia: não depende do contexto.json. contexto.json quebrado é FALHA, sem gravar.
    args = comum.prepara(args, comum.DIA_DE_HOJE if args.confere else comum.DIA_DO_CONTEXTO)
    saida = comum.Saida(args.json)
    args.gravado = False
    try:
        return (roda_confere if args.confere else roda_coleta)(args, conexao, inicio, saida)
    except (comum.ErroDeUso, comum.Falha):
        raise
    except Exception:
        if not args.gravado:
            _socorro(args, _siglas_se_der(args.raiz), args.dia)
        raise


if __name__ == "__main__":
    comum.executa(principal)
