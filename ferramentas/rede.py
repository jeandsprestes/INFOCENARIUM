"""Rede do coleta.py e do indicadores.py (CONTRATO, seção 0, "Rede").

O que este módulo garante a quem chama:
  - só http e https, e só para endereço com nome de site: nada de file:, de número de IP, de
    localhost nem de nome interno, no pedido e em cada destino de redirecionamento;
  - tempo limite por pedido, contado do começo ao fim (resposta em conta-gotas também estoura);
  - uma nova tentativa, depois de 1 segundo, só para falha passageira (conexão caída, 429, 5xx); tempo
    esgotado não se repete;
  - até 3 redirecionamentos, seguidos aqui, com a mesma conferência em cada destino;
  - resposta de até 2 MB, lida em pedaços (o Content-Length não entra na conta), e gzip aberto com
    o mesmo teto (arquivo pequeno que incha não passa);
  - proxy e certificados do sistema; a conferência de certificado nunca é desligada;
  - o modo --offline (respostas.json), que passa pelo mesmo laço de redirecionamento e pelos mesmos tetos;
    a `demora` de uma entrada é esperada de verdade, até o tempo limite do pedido, e `"falha": "nome"`
    simula o nome de site que não existe;
  - um teto de tempo para o lote: o que não respondeu até lá é abandonado e conta como erro;
  - nenhuma exceção: todo pedido devolve uma Resposta, com `erro` preenchido quando falhou.

O que chega da rede é dado. Aqui nada é interpretado: quem lê XML, JSON, CSV ou HTML é a ferramenta.
O texto de `erro` é sempre uma frase fixa deste arquivo, nunca a mensagem crua do sistema: ela pode
trazer o endereço do proxy, que às vezes carrega senha.
"""
import http.client
import ipaddress
import json
import os
import re
import socket
import ssl
import threading
import time
import urllib.error
import urllib.request
import zlib
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

import comum

LIMITE = 2 * 1024 * 1024          # bytes por resposta, já aberta
REDIRECIONAMENTOS = 3
PEDACO = 64 * 1024
PAUSA = 1.0                       # segundos antes da nova tentativa
SEM_SINAL = 8                     # falhas sem nenhum sucesso que fazem desistir da nova tentativa
FOLGA = 1.0                       # segundos, depois do teto, para os pedidos em curso fecharem
AGENTE = "Mozilla/5.0 (compatible; INFOCENARIUM-monitor/1)"
AGENTE_NAVEGADOR = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"

# Motivos de falha (campo `motivo` da Resposta). Texto vazio: chegou uma resposta HTTP.
URL, NOME, TEMPO, TETO, CONEXAO, CERTIFICADO, DESVIO, PROTOCOLO, PROXY, OFFLINE = (
    "url", "nome", "tempo", "teto", "conexao", "certificado", "desvio", "protocolo", "proxy", "offline")

_DESVIOS = (301, 302, 303, 307, 308)
_RE_PROIBIDO = re.compile(r"[\x00-\x20\x7f\\]")
_RE_NOME = re.compile(r"[a-z0-9_]([a-z0-9_-]*[a-z0-9_])?(\.[a-z0-9_]([a-z0-9_-]*[a-z0-9_])?)*\.?")
_RE_FIM_DO_NOME = re.compile(r"[a-z][a-z0-9-]*")  # o último rótulo de um nome público nunca é número
_RE_TUNEL = re.compile(r"Tunnel connection failed: (\d{3})")
_RE_CABECALHO = re.compile(r"[a-z0-9_-]{1,40}")
_INTERNOS = ("localhost", "local", "localdomain", "internal", "intranet", "lan", "home", "corp", "arpa", "svc")


class Resposta:
    """O que voltou de um pedido. `erro` vazio quer dizer que chegou resposta HTTP, com qualquer código."""

    __slots__ = ("url", "final", "status", "tipo", "corpo", "cortada", "erro", "motivo")

    def __init__(self, url, final=None, status=0, tipo="", corpo=b"", cortada=False, erro="", motivo=""):
        self.url, self.final = url, final or url
        self.status, self.tipo, self.corpo, self.cortada = status, tipo, corpo, cortada
        self.erro, self.motivo = erro, motivo

    @property
    def boa(self):
        """Resposta 2xx, com corpo lido (inteiro ou cortado no teto)."""
        return not self.erro and 200 <= self.status < 300

    def falha(self):
        """Por que não serviu, em poucas palavras; vazio se serviu."""
        if self.erro:
            return self.erro
        return "" if self.boa else "HTTP %d" % self.status


class _Falha(Exception):
    def __init__(self, motivo, erro, passageira=False):
        super().__init__(erro)
        self.motivo, self.erro, self.passageira = motivo, erro, passageira


# ---------------------------------------------------------------- endereço

def recusa(url, livres=()):
    """Por que esta URL não pode ser pedida; texto vazio se pode.

    Vale para o primeiro pedido e para cada destino de redirecionamento. `livres` são nomes de
    máquina que escapam da regra do nome público: só os testes usam (servidor em 127.0.0.1)."""
    if not isinstance(url, str) or not url or len(url) > 2000:
        return "endereço ilegível"
    if _RE_PROIBIDO.search(url):
        return "endereço com espaço, barra invertida ou caractere de controle"
    try:
        partes = urlsplit(url)
        nome, _ = partes.hostname, partes.port
    except ValueError:
        return "endereço ilegível"
    if partes.scheme.lower() not in ("http", "https"):
        return "só http e https"
    if not nome:
        return "endereço sem nome de site"
    if partes.username is not None or partes.password is not None:
        return "endereço com usuário ou senha"
    if nome in livres:
        return ""
    try:
        ascii_ = nome.encode("idna").decode("ascii").lower() if not nome.isascii() else nome.lower()
    except UnicodeError:
        return "nome de site ilegível"
    try:
        ipaddress.ip_address(ascii_)
        return "endereço sem nome de site (número de IP)"
    except ValueError:
        pass
    rotulos = ascii_.rstrip(".").split(".")
    if len(ascii_) > 253 or not _RE_NOME.fullmatch(ascii_) or any(len(r) > 63 for r in rotulos):
        return "nome de site ilegível"
    if len(rotulos) < 2 or not _RE_FIM_DO_NOME.fullmatch(rotulos[-1]) or rotulos[-1] in _INTERNOS:
        return "endereço sem nome de site público"
    return ""


def _para_pedir(url):
    """A URL como vai no pedido: só ASCII (nome em IDNA, o resto com %XX) e sem `#…`."""
    partes = urlsplit(url)
    nome = partes.hostname
    local = nome.encode("idna").decode("ascii") if not nome.isascii() else nome
    if ":" in local:
        local = "[" + local + "]"
    if partes.port is not None:
        local += ":%d" % partes.port
    seguro = "/%:@!$&'()*+,;=~-._"
    return urlunsplit((partes.scheme.lower(), local, quote(partes.path or "/", safe=seguro),
                       quote(partes.query, safe=seguro + "?[]"), ""))


def _destino(atual, para):
    """O endereço de um redirecionamento. Absoluto fica como veio; relativo é resolvido contra o atual."""
    para = para.strip()
    return para if re.match(r"https?://", para, re.I) else urljoin(atual, para)


# ---------------------------------------------------------------- modo offline

def le_offline(pasta):
    """Lê PASTA/respostas.json (CONTRATO, seção 0). Devolve (pasta absoluta, objeto). Erro de uso se não dá.
    `{}` e arquivo de 0 bytes (ou só de espaços) valem como nenhuma resposta."""
    pasta = os.path.abspath(pasta)
    caminho = os.path.join(pasta, "respostas.json")
    if not os.path.isdir(pasta):
        raise comum.ErroDeUso("--offline: a pasta %s não existe" % pasta)
    try:
        with open(caminho, "rb") as arquivo:
            bruto = arquivo.read()
    except OSError:
        raise comum.ErroDeUso("--offline: falta o arquivo %s" % caminho) from None
    if not bruto.strip():  # arquivo vazio vale como nenhuma resposta: tudo falha, como numa máquina sem rede
        return pasta, {}
    try:
        mapa = json.loads(bruto.decode("utf-8-sig"))
    except (ValueError, RecursionError):
        raise comum.ErroDeUso("--offline: %s não é JSON em UTF-8" % caminho) from None
    if not isinstance(mapa, dict):
        raise comum.ErroDeUso("--offline: %s deveria ser um objeto {\"URL\": \"arquivo\"}" % caminho)
    return pasta, mapa


def _arquivo_offline(pasta, nome):
    """O corpo de uma resposta simulada, até o teto mais 1 byte. O arquivo tem de morar dentro da pasta."""
    if not isinstance(nome, str) or not nome:
        raise _Falha(OFFLINE, "respostas.json: nome de arquivo ilegível")
    caminho = os.path.realpath(os.path.join(pasta, nome))
    if os.path.commonpath([caminho, os.path.realpath(pasta)]) != os.path.realpath(pasta):
        raise _Falha(OFFLINE, "respostas.json: arquivo fora da pasta do --offline")
    try:
        with open(caminho, "rb") as arquivo:
            return arquivo.read(LIMITE + 1)
    except OSError:
        raise _Falha(OFFLINE, "respostas.json: arquivo de resposta não encontrado") from None


# ---------------------------------------------------------------- a rede

def _contexto_tls():
    """Certificados do sistema, com a conferência ligada (o padrão do Python). Soma, se houver, o pacote
    de certificados que a máquina indica para outros programas: é assim que um proxy que abre o https
    costuma avisar qual é a autoridade dele. Nunca tira certificado nem desliga conferência."""
    contexto = ssl.create_default_context()
    for variavel in ("REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"):
        caminho = os.environ.get(variavel)
        if caminho and os.path.isfile(caminho):
            try:
                contexto.load_verify_locations(cafile=caminho)
            except (OSError, ssl.SSLError):
                pass
    return contexto


def _soquete(resposta):
    """O soquete por baixo da resposta, para apertar o tempo limite a cada leitura. Se o Python mudar por
    dentro e ele não estiver ali, fica o tempo limite posto na abertura."""
    try:
        return resposta.fp.raw._sock
    except AttributeError:
        return None


def _classifica(erro):
    """Uma exceção do pedido vira _Falha, com frase fixa. A mensagem crua nunca sai daqui."""
    if isinstance(erro, _Falha):
        return erro
    causa = erro.reason if isinstance(erro, urllib.error.URLError) and isinstance(erro.reason, BaseException) else erro
    if isinstance(causa, ssl.SSLCertVerificationError):
        return _Falha(CERTIFICADO, "certificado recusado")
    if isinstance(causa, (socket.timeout, TimeoutError)):
        return _Falha(TEMPO, "tempo esgotado")
    if isinstance(causa, socket.gaierror):
        if causa.errno in (socket.EAI_NONAME, getattr(socket, "EAI_NODATA", socket.EAI_NONAME)):
            return _Falha(NOME, "o nome do site não existe")
        return _Falha(CONEXAO, "nome do site não resolvido", passageira=True)
    tunel = _RE_TUNEL.search(str(causa)) if isinstance(causa, OSError) else None
    if tunel:  # o proxy respondeu ao pedido de túnel com um código HTTP
        codigo = int(tunel.group(1))
        return _Falha(PROXY, "o proxy recusou a ligação (HTTP %d)" % codigo, passageira=codigo >= 500)
    if isinstance(causa, ssl.SSLError):
        return _Falha(CONEXAO, "falha na ligação segura", passageira=True)
    if isinstance(causa, (http.client.HTTPException, ConnectionError, EOFError)):
        return _Falha(CONEXAO, "ligação caiu ou resposta não é HTTP (%s)" % type(causa).__name__, passageira=True)
    if isinstance(causa, OSError):
        return _Falha(CONEXAO, "sem ligação (%s)" % type(causa).__name__, passageira=True)
    if isinstance(causa, (ValueError, UnicodeError)):
        return _Falha(URL, "endereço ilegível")
    return _Falha(CONEXAO, "falha no pedido (%s)" % type(causa).__name__)


class Rede:
    """Faz os pedidos de uma execução: pela rede, ou pela pasta do --offline."""

    def __init__(self, offline=None, livres=()):
        self.livres = tuple(livres)
        self.offline = None
        if offline is not None:
            self.offline = le_offline(offline)
        self._abridor = None
        self._tranca = threading.Lock()
        self._bons = self._ruins = 0

    # ---- um pedido

    def baixa(self, url, tempo, prazo=None, agente=AGENTE, aceita="*/*"):
        """Pede a URL. `tempo` é o limite de cada tentativa, em segundos; `prazo` é o teto do lote, na
        escala de time.monotonic(). Nunca levanta exceção."""
        prazo = float("inf") if prazo is None else prazo
        ultima = None
        for tentativa in (1, 2):
            if time.monotonic() >= prazo:
                return ultima or Resposta(url, erro="não coube no tempo", motivo=TETO)
            try:
                resposta = self._segue(url, min(time.monotonic() + tempo, prazo), agente, aceita)
            except _Falha as falha:
                if falha.motivo == TEMPO and time.monotonic() >= prazo:
                    falha = _Falha(TETO, "não coube no tempo")
                resposta = Resposta(url, erro=falha.erro, motivo=falha.motivo)
                passageira = falha.passageira
            else:
                passageira = resposta.status == 429 or 500 <= resposta.status <= 599
            self._conta(resposta.boa)
            ultima = resposta
            if tentativa == 2 or not passageira or self.offline is not None or self._sem_sinal():
                break
            espera = min(PAUSA, prazo - time.monotonic())
            if espera <= 0:
                break
            time.sleep(espera)
        return ultima

    def _conta(self, boa):
        with self._tranca:
            if boa:
                self._bons += 1
            else:
                self._ruins += 1

    def _sem_sinal(self):
        """Nenhum pedido deu certo e vários já falharam: a máquina parece sem rede, e insistir só gasta o teto."""
        with self._tranca:
            return self._bons == 0 and self._ruins >= SEM_SINAL

    def _segue(self, url, fim, agente, aceita):
        """Um pedido com os redirecionamentos. O mesmo laço serve à rede e ao --offline."""
        atual = url
        for salto in range(REDIRECIONAMENTOS + 1):
            motivo = recusa(atual, self.livres)
            if motivo:
                raise _Falha(URL if salto == 0 else DESVIO,
                             motivo if salto == 0 else "redirecionamento recusado: " + motivo)
            busca = self._busca_offline if self.offline is not None else self._busca_rede
            status, tipo, para, corpo, cortada = busca(atual, fim, agente, aceita)
            if para is None:
                return Resposta(url, atual, status, tipo, corpo, cortada)
            atual = _destino(atual, para)
        raise _Falha(DESVIO, "redirecionamentos demais")

    # ---- offline

    def _busca_offline(self, url, fim, agente, aceita):
        pasta, mapa = self.offline
        if url not in mapa:
            raise _Falha(OFFLINE, "sem resposta no modo offline")
        entrada = mapa[url]
        if isinstance(entrada, str):
            entrada = {"arquivo": entrada}
        if not isinstance(entrada, dict):
            raise _Falha(OFFLINE, "respostas.json: entrada ilegível")
        status, tipo, para = entrada.get("status", 200), entrada.get("tipo", ""), entrada.get("para")
        demora, falha = entrada.get("demora", 0), entrada.get("falha")
        if isinstance(status, bool) or not isinstance(status, int) or not 100 <= status <= 599:
            raise _Falha(OFFLINE, "respostas.json: status ilegível")
        if not isinstance(tipo, str) or (para is not None and (not isinstance(para, str) or not para.strip())):
            raise _Falha(OFFLINE, "respostas.json: entrada ilegível")
        if isinstance(demora, bool) or not isinstance(demora, (int, float)) or not 0 <= demora <= 3600:
            raise _Falha(OFFLINE, "respostas.json: demora ilegível")
        if falha not in (None, "nome"):
            raise _Falha(OFFLINE, "respostas.json: falha ilegível")
        if demora:  # a resposta lenta é simulada de verdade: o relógio corre, e o tempo limite corta
            resta = fim - time.monotonic()
            time.sleep(max(0.0, min(demora, resta)))
            if demora > resta:
                raise _Falha(TEMPO, "tempo esgotado")
        if falha == "nome":  # o nome do site não existe: o caso que o modo offline não teria como mostrar
            raise _Falha(NOME, "o nome do site não existe")
        if para is not None:
            return status, tipo, para, b"", False
        corpo = _arquivo_offline(pasta, entrada["arquivo"]) if "arquivo" in entrada else b""
        return status, tipo, None, corpo[:LIMITE], len(corpo) > LIMITE

    # ---- rede de verdade

    def _abre(self):
        """O abridor do urllib, montado peça por peça: proxy do ambiente, http, https e mais nada.
        Não entra a peça que abre file:, ftp: ou data:, nem a que segue redirecionamento sozinha: sem
        ela, todo 3xx volta como resposta, e quem segue é o laço de _segue, que confere cada destino."""
        with self._tranca:
            if self._abridor is None:
                abridor = urllib.request.OpenerDirector()
                for peca in (urllib.request.ProxyHandler(), urllib.request.UnknownHandler(),
                             urllib.request.HTTPHandler(), urllib.request.HTTPSHandler(context=_contexto_tls()),
                             urllib.request.HTTPDefaultErrorHandler(), urllib.request.HTTPErrorProcessor()):
                    abridor.add_handler(peca)
                self._abridor = abridor
            return self._abridor

    def _busca_rede(self, url, fim, agente, aceita):
        resta = fim - time.monotonic()
        if resta <= 0:
            raise _Falha(TEMPO, "tempo esgotado")
        resposta = None
        try:
            pedido = urllib.request.Request(_para_pedir(url), method="GET", headers={
                "User-Agent": agente, "Accept": aceita, "Accept-Encoding": "gzip"})
            try:
                resposta = self._abre().open(pedido, timeout=resta)
            except urllib.error.HTTPError as erro:  # 3xx, 4xx e 5xx chegam assim; são respostas
                resposta = erro
            status = int(resposta.status if hasattr(resposta, "status") else resposta.code)
            cabecalhos = resposta.headers
            tipo = " ".join(str(cabecalhos.get("Content-Type") or "").split())[:200]
            if status in _DESVIOS:
                para = cabecalhos.get("Location")
                if not para or not str(para).strip():
                    raise _Falha(DESVIO, "redirecionamento sem destino")
                return status, tipo, str(para), b"", False
            if not 200 <= status < 300:
                return status, tipo, None, b"", False  # o corpo de um erro não interessa: nem é lido
            codificacao = str(cabecalhos.get("Content-Encoding") or "").strip().lower()
            corpo, cortada = _le_corpo(resposta, fim, codificacao)
            return status, tipo, None, corpo, cortada
        except Exception as erro:  # tudo vira _Falha com frase fixa; nada escapa para a ferramenta
            raise _classifica(erro) from None
        finally:
            if resposta is not None:
                try:
                    resposta.close()
                except Exception:
                    pass


def _le_corpo(resposta, fim, codificacao):
    """Lê o corpo em pedaços até o teto de 2 MB, olhando o relógio a cada pedaço. Devolve (corpo, cortada)."""
    abre = None
    if codificacao in ("gzip", "x-gzip", "deflate"):
        abre = zlib.decompressobj(zlib.MAX_WBITS | 32)
    elif codificacao not in ("", "identity"):
        raise _Falha(PROTOCOLO, "compressão que a ferramenta não lê")
    soquete = _soquete(resposta)
    pedacos, tamanho, lido = [], 0, 0
    while True:
        resta = fim - time.monotonic()
        if resta <= 0:
            raise _Falha(TEMPO, "tempo esgotado")
        if soquete is not None:
            try:
                soquete.settimeout(max(resta, 0.05))
            except OSError:  # o corpo acabou e o Python já fechou o soquete: a próxima leitura devolve o fim
                soquete = None
        pedaco = resposta.read1(PEDACO)
        if not pedaco:
            break
        lido += len(pedaco)
        if abre is not None:
            try:  # o segundo número limita o que sai: um gzip que incha para de ser aberto no teto
                pedaco = abre.decompress(pedaco, LIMITE + 1 - tamanho)
            except zlib.error:
                raise _Falha(PROTOCOLO, "gzip estragado", passageira=True) from None
        pedacos.append(pedaco)
        tamanho += len(pedaco)
        if tamanho > LIMITE or lido > LIMITE:
            return b"".join(pedacos)[:LIMITE], True
    if getattr(resposta, "length", None):  # o servidor prometeu mais bytes do que mandou
        raise _Falha(CONEXAO, "resposta incompleta", passageira=True)
    return b"".join(pedacos), False


# ---------------------------------------------------------------- lote em paralelo

class _Quebra:
    def __init__(self, erro):
        self.erro = erro


def em_paralelo(funcao, itens, paralelos, prazo):
    """Chama funcao(item) para cada item, `paralelos` por vez, em threads. Devolve os resultados na
    ordem dos itens, seja qual for a ordem em que terminaram. Fica None o que não terminou até o prazo
    (escala de time.monotonic()) mais uma folga curta: a thread é abandonada, e não trava a saída."""
    itens = list(itens)
    total = len(itens)
    resultados = [None] * total
    estado = {"proximo": 0, "feitos": 0, "aberto": True}
    sinal = threading.Condition()

    def trabalha():
        while True:
            with sinal:
                if not estado["aberto"] or estado["proximo"] >= total:
                    return
                indice = estado["proximo"]
                estado["proximo"] += 1
            try:
                resultado = funcao(itens[indice])
            except BaseException as erro:  # erro de programação sobe na thread principal, e não some aqui
                resultado = _Quebra(erro)
            with sinal:
                if estado["aberto"]:
                    resultados[indice] = resultado
                estado["feitos"] += 1
                sinal.notify_all()

    ligadas = 0
    for _ in range(max(1, min(paralelos, total))):
        try:  # threads de fundo: se uma ficar presa (resolução de nome não tem tempo limite), o programa sai assim mesmo
            threading.Thread(target=trabalha, daemon=True).start()
            ligadas += 1
        except RuntimeError:
            break
    if not ligadas:  # máquina que não deixa abrir thread: um por vez, aqui mesmo
        trabalha()
    with sinal:
        while estado["feitos"] < total:
            resta = prazo + FOLGA - time.monotonic()
            if resta <= 0:
                break
            sinal.wait(resta)
        estado["aberto"] = False
        copia = list(resultados)
    for resultado in copia:
        if isinstance(resultado, _Quebra):
            raise resultado.erro
    return copia


def prazo_de(inicio, tempo):
    """O instante em que a rede para, dado o --tempo: o teto menos uma reserva curta para ler e gravar."""
    return inicio + tempo - min(5.0, tempo * 0.1)
