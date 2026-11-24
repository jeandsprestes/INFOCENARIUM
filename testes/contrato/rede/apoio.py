#!/usr/bin/env python3
"""Apoio dos testes de contrato de coleta.py e de indicadores.py.

Estes testes foram escritos só a partir dos contratos (CONTRATO das ferramentas e ESQUEMA), sem ler
o código. Cada ferramenta é uma caixa-preta: linha de comando, saída padrão, código de saída e
arquivos gravados.

O que há aqui:

- Bancada: uma raiz pequena (cópia de fixtures/raiz), uma pasta de trabalho e uma pasta de
  respostas do modo --offline, todas temporárias (respeitam $TMPDIR);
- Bancada.roda(): chama a ferramenta com --raiz, --trabalho e --offline, com o relógio fixo
  (INFO_AGORA) e PYTHONDONTWRITEBYTECODE=1, e devolve saída, código, última linha e arquivos;
- rss() e atom(): feeds gerados a partir de uma lista de manchetes, com datas relativas ao relógio;
- os cinco formatos de resposta dos leitores de indicadores (CONTRATO, seção 2);
- le_mesa(): leitura de mesa.txt pelo formato do CONTRATO, seção 1.

A variável INFO_CONTRATO_FERRAMENTAS troca a pasta das ferramentas. Serve para provar o
encanamento deste arquivo com uma ferramenta de mentira; no uso normal, não se define.
"""
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

sys.dont_write_bytecode = True

AQUI = Path(__file__).resolve().parent
FIXTURES = AQUI / "fixtures"
RAIZ_DO_REPOSITORIO = AQUI.parents[2]

# O relógio dos testes: 18h de Brasília de 20/11/2026, uma sexta-feira.
AGORA = "2026-11-20T21:00:00Z"
DIA = "2026-11-20"
UTC = datetime.timezone.utc

LEGENDA = ("LEGENDA: [XX] partido do veículo · ? lado incerto · serve a: player a quem o veículo serve · "
           "fatos: confiança para fato cru · [SUSPEITA] pode ser ordem, e não notícia")


def pasta_das_ferramentas():
    return Path(os.environ.get("INFO_CONTRATO_FERRAMENTAS") or RAIZ_DO_REPOSITORIO / "ferramentas")


# ---------------------------------------------------------------------------------------------
# Relógio e datas
# ---------------------------------------------------------------------------------------------

def instante(texto=AGORA):
    """Lê uma data-hora UTC no formato do ESQUEMA, seção 0."""
    return datetime.datetime.strptime(texto, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def ha(horas, agora=AGORA):
    """O instante de `horas` horas antes do relógio. Número negativo: no futuro."""
    return instante(agora) - datetime.timedelta(hours=horas)


def data_hora(momento):
    """Data-hora UTC como o ESQUEMA, seção 0, manda gravar."""
    return momento.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def dia_mais(dia, dias):
    """A data `dias` dias depois de `dia` (negativo: antes), em AAAA-MM-DD."""
    return (datetime.date.fromisoformat(dia) + datetime.timedelta(days=dias)).isoformat()


_DIAS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_MESES = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _no_fuso(momento, minutos):
    return momento.astimezone(datetime.timezone(datetime.timedelta(minutes=minutos)))


def data_rss(momento, fuso=0, gmt=False):
    """Data no formato do pubDate do RSS 2.0. `fuso` é o deslocamento em minutos (−180 = Brasília)."""
    local = _no_fuso(momento, fuso)
    sinal = "-" if fuso < 0 else "+"
    sufixo = "GMT" if gmt else "%s%02d%02d" % (sinal, abs(fuso) // 60, abs(fuso) % 60)
    return "%s, %02d %s %04d %02d:%02d:%02d %s" % (
        _DIAS[local.weekday()], local.day, _MESES[local.month - 1], local.year,
        local.hour, local.minute, local.second, sufixo)


def data_atom(momento, fuso=None):
    """Data no formato do Atom (RFC 3339). Sem `fuso`, termina em Z."""
    if fuso is None:
        return data_hora(momento)
    local = _no_fuso(momento, fuso)
    sinal = "-" if fuso < 0 else "+"
    return local.strftime("%Y-%m-%dT%H:%M:%S") + "%s%02d:%02d" % (sinal, abs(fuso) // 60, abs(fuso) % 60)


# ---------------------------------------------------------------------------------------------
# Feeds
# ---------------------------------------------------------------------------------------------

def manchete(titulo, url, horas=1.0, resumo="Resumo de exemplo.", **outros):
    """Uma manchete para rss() e atom().

    Chaves: titulo, resumo e url (texto, escapado ao gravar; url None tira o endereço; resumo None
    tira o resumo); horas (há quantas horas foi publicada; negativo é futuro); fuso (minutos: a data
    sai escrita nesse fuso); gmt (RSS: termina em GMT); data (texto posto como está no lugar da
    data); sem_data (True: nenhuma data); titulo_xml e resumo_xml (XML posto como está, para CDATA
    e marcas); xml (XML a mais dentro da entrada). Só no Atom: atualizado (horas do <updated>,
    quando difere do <published>) e so_atualizado (True: só <updated>, sem <published>).
    """
    return dict(titulo=titulo, url=url, horas=horas, resumo=resumo, **outros)


def _texto(m, campo):
    return m[campo + "_xml"] if campo + "_xml" in m else escape(m[campo])


def _tem(m, campo):
    return m.get(campo) is not None or campo + "_xml" in m


def rss(manchetes, agora=AGORA, antes_da_raiz=""):
    """Um feed RSS 2.0, em bytes UTF-8. `antes_da_raiz` entra depois da declaração XML."""
    partes = ['<?xml version="1.0" encoding="UTF-8"?>\n', antes_da_raiz,
              '<rss version="2.0">\n<channel>\n<title>Feed de exemplo</title>\n'
              '<link>https://feed.exemplo.invalid/</link>\n'
              '<description>Feed fictício, para teste.</description>\n']
    for m in manchetes:
        partes.append("<item>\n")
        if _tem(m, "titulo"):
            partes.append("<title>%s</title>\n" % _texto(m, "titulo"))
        if m.get("url") is not None:
            partes.append("<link>%s</link>\n" % escape(m["url"]))
        if _tem(m, "resumo"):
            partes.append("<description>%s</description>\n" % _texto(m, "resumo"))
        if "data" in m:
            partes.append("<pubDate>%s</pubDate>\n" % escape(m["data"]))
        elif not m.get("sem_data"):
            quando = data_rss(ha(m["horas"], agora), m.get("fuso", 0), m.get("gmt", False))
            partes.append("<pubDate>%s</pubDate>\n" % quando)
        partes.append(m.get("xml", ""))
        partes.append("</item>\n")
    partes.append("</channel>\n</rss>\n")
    return "".join(partes).encode("utf-8")


def atom(manchetes, agora=AGORA, antes_da_raiz=""):
    """Um feed Atom 1.0, em bytes UTF-8. `antes_da_raiz` entra depois da declaração XML."""
    partes = ['<?xml version="1.0" encoding="UTF-8"?>\n', antes_da_raiz,
              '<feed xmlns="http://www.w3.org/2005/Atom">\n<title>Feed de exemplo</title>\n'
              '<id>https://feed.exemplo.invalid/</id>\n<updated>%s</updated>\n' % agora]
    for numero, m in enumerate(manchetes, 1):
        partes.append("<entry>\n")
        if _tem(m, "titulo"):
            partes.append("<title>%s</title>\n" % _texto(m, "titulo"))
        if m.get("url") is not None:
            partes.append('<link rel="alternate" href=%s/>\n' % quoteattr(m["url"]))
        partes.append("<id>tag:feed.exemplo.invalid,2026:%d</id>\n" % numero)
        if "data" in m:
            partes.append("<published>%s</published>\n" % escape(m["data"]))
        elif not m.get("sem_data"):
            quando = data_atom(ha(m["horas"], agora), m.get("fuso"))
            if not m.get("so_atualizado"):
                partes.append("<published>%s</published>\n" % quando)
            if "atualizado" in m:
                quando = data_atom(ha(m["atualizado"], agora), m.get("fuso"))
            partes.append("<updated>%s</updated>\n" % quando)
        if _tem(m, "resumo"):
            partes.append("<summary>%s</summary>\n" % _texto(m, "resumo"))
        partes.append(m.get("xml", ""))
        partes.append("</entry>\n")
    partes.append("</feed>\n")
    return "".join(partes).encode("utf-8")


# ---------------------------------------------------------------------------------------------
# Respostas das fontes de indicadores (CONTRATO, seção 2, tabela dos leitores)
# Uma série é uma lista de pares (data, valor). Valor None é ponto sem valor.
# ---------------------------------------------------------------------------------------------

def _numero(valor):
    return "" if valor is None else str(valor)


def fred_csv(serie, coluna="SERIE"):
    """CSV com o cabeçalho observation_date,ID e uma linha AAAA-MM-DD,valor por ponto."""
    return "".join(["observation_date,%s\n" % coluna] + ["%s,%s\n" % (d, _numero(v)) for d, v in serie])


def yahoo_chart(serie, hora="14:30:00"):
    """JSON com chart.result[0].timestamp[] e indicators.quote[0].close[].

    A data pode vir como AAAA-MM-DD (o instante é esse dia, na `hora` dada, em UTC) ou como
    data-hora UTC completa.
    """
    carimbos = []
    for quando, _ in serie:
        texto = quando if "T" in quando else "%sT%sZ" % (quando, hora)
        carimbos.append(int(instante(texto).timestamp()))
    corpo = {"chart": {"result": [{"meta": {"currency": "USD", "symbol": "EXEMPLO=F"},
                                   "timestamp": carimbos,
                                   "indicators": {"quote": [{"close": [v for _, v in serie]}]}}],
                       "error": None}}
    return json.dumps(corpo)


def bcb_sgs(serie):
    """JSON: lista de {"data": "DD/MM/AAAA", "valor": "5.8889"}."""
    itens = []
    for quando, valor in serie:
        ano, mes, dia = quando.split("-")
        itens.append({"data": "%s/%s/%s" % (dia, mes, ano), "valor": _numero(valor)})
    return json.dumps(itens)


def eia_v2(serie):
    """JSON com response.data[], do mais novo para o mais velho, como a fonte entrega."""
    dados = [{"period": quando, "value": None if valor is None else str(valor), "units": "exemplo"}
             for quando, valor in sorted(serie, reverse=True)]
    return json.dumps({"response": {"total": str(len(dados)), "dateFormat": "YYYY-MM-DD",
                                    "frequency": "daily", "data": dados}})


def fao_csv(serie):
    """CSV com 2 linhas de título, o cabeçalho Date,Food Price Index,… e uma linha AAAA-MM por mês."""
    linhas = ["Índice de exemplo no formato do índice de preços de alimentos\n", "2014-2016=100\n",
              "Date,Food Price Index,Meat,Dairy,Cereals,Oils,Sugar\n"]
    linhas += ["%s,%s,118.0,120.5,110.2,150.3,105.4\n" % (mes, _numero(valor)) for mes, valor in serie]
    return "".join(linhas)


LEITORES = {"fred_csv": fred_csv, "yahoo_chart": yahoo_chart, "bcb_sgs": bcb_sgs,
            "eia_v2": eia_v2, "fao_csv": fao_csv}


# ---------------------------------------------------------------------------------------------
# A bancada: raiz, pasta de trabalho e respostas, tudo temporário
# ---------------------------------------------------------------------------------------------

def _fotografa(pasta):
    """Os arquivos de uma pasta, com subpastas: caminho relativo → bytes."""
    pasta = Path(pasta)
    if not pasta.is_dir():
        return {}
    return {c.relative_to(pasta).as_posix(): c.read_bytes() for c in sorted(pasta.rglob("*")) if c.is_file()}


class Resultado:
    """O que uma execução deixou: saída, código, última linha e arquivos da pasta de trabalho."""

    def __init__(self, comando, codigo, saida, erro, antes, depois):
        self.comando = comando
        self.codigo = codigo
        self.saida = saida
        self.erro = erro
        self.linhas = [linha for linha in saida.splitlines() if linha.strip()]
        self.ultima = self.linhas[-1] if self.linhas else ""
        self.palavra = self.ultima.split()[0] if self.ultima.split() else ""
        self.antes = antes
        self.arquivos = depois

    def gravados(self):
        """Nomes dos arquivos da pasta de trabalho que a execução criou ou mudou."""
        return sorted(nome for nome, corpo in self.arquivos.items() if self.antes.get(nome) != corpo)

    def texto(self, nome):
        return self.arquivos[nome].decode("utf-8")

    def json(self, nome):
        return json.loads(self.texto(nome))

    def relato(self):
        """Resumo para a mensagem de um teste que falhou."""
        return ("\n  comando: %s\n  código: %s\n  fim da saída padrão:\n    %s\n  fim da saída de erro:\n    %s"
                % (" ".join(self.comando[1:]), self.codigo,
                   "\n    ".join(self.saida.splitlines()[-8:]), "\n    ".join(self.erro.splitlines()[-8:])))


class Bancada:
    """Uma raiz pequena, uma pasta de trabalho e uma pasta de respostas, em pasta temporária."""

    def __init__(self, agora=AGORA):
        self.agora = agora
        self.base = Path(tempfile.mkdtemp(prefix="info-contrato-rede-"))
        self.raiz = self.base / "raiz"
        shutil.copytree(FIXTURES / "raiz", self.raiz)
        self.trabalho = self.base / "trabalho"
        self.trabalho.mkdir()
        self.offline = self.base / "offline"
        self.offline.mkdir()
        self.respostas = {}
        self._conta = 0

    def fecha(self):
        shutil.rmtree(self.base, ignore_errors=True)

    # --- dados da raiz -----------------------------------------------------------------------

    def le_dados(self, nome):
        return json.loads((self.raiz / "dados" / nome).read_text(encoding="utf-8"))

    def grava_dados(self, nome, objeto):
        texto = objeto if isinstance(objeto, str) else json.dumps(objeto, ensure_ascii=False, indent=2) + "\n"
        (self.raiz / "dados" / nome).write_text(texto, encoding="utf-8")

    def apaga_dados(self, nome):
        (self.raiz / "dados" / nome).unlink()

    def mapa(self):
        return self.le_dados("veiculos.json")

    def veiculo(self, ident):
        return next(v for v in self.mapa()["veiculos"] if v["id"] == ident)

    def so_veiculos(self, *ids):
        """Deixa no mapa só os veículos citados (na ordem do mapa)."""
        mapa = self.mapa()
        mapa["veiculos"] = [v for v in mapa["veiculos"] if v["id"] in ids]
        faltam = set(ids) - {v["id"] for v in mapa["veiculos"]}
        assert not faltam, "veículo fora da fixture: %s" % sorted(faltam)
        self.grava_dados("veiculos.json", mapa)

    def muda_veiculo(self, ident, **campos):
        mapa = self.mapa()
        next(v for v in mapa["veiculos"] if v["id"] == ident).update(campos)
        self.grava_dados("veiculos.json", mapa)

    def feeds(self):
        """Os feeds de formato rss ou atom do mapa: lista de (id do veículo, feed)."""
        return [(v["id"], f) for v in self.mapa()["veiculos"] for f in v.get("feeds", [])
                if f.get("formato") in ("rss", "atom")]

    def feed(self, ident, numero=0):
        """O endereço do feed rss ou atom de número `numero` do veículo."""
        return [f["url"] for v, f in self.feeds() if v == ident][numero]

    def partidos(self):
        return [p["id"] for p in self.le_dados("regua.json")["partidos"]]

    def siglas(self):
        return {p["id"]: p["sigla"] for p in self.le_dados("regua.json")["partidos"]}

    # --- respostas do modo --offline ---------------------------------------------------------

    def responde(self, url, corpo=None, status=None, tipo=None, para=None, objeto=False, demora=None, falha=None):
        """Registra a resposta de uma URL.

        Só com `corpo`, usa a forma simples ({"URL": "arquivo"}). Com `status`, `tipo`, `para`, `demora`,
        `falha` ou `objeto=True`, usa a forma de objeto ({"arquivo", "status", "tipo", "para", "demora",
        "falha"}). `demora` são segundos de verdade, e `falha` só aceita "nome" (CONTRATO, seção 0, --offline).
        """
        nome = None
        if corpo is not None:
            self._conta += 1
            nome = "r%04d.dat" % self._conta
            (self.offline / nome).write_bytes(corpo.encode("utf-8") if isinstance(corpo, str) else corpo)
        if status is None and tipo is None and para is None and demora is None and falha is None and not objeto:
            assert nome is not None, "a forma simples pede um corpo"
            self.respostas[url] = nome
            return
        valor = {}
        if nome is not None:
            valor["arquivo"] = nome
        if status is not None:
            valor["status"] = status
        if tipo is not None:
            valor["tipo"] = tipo
        if para is not None:
            valor["para"] = para
        if demora is not None:
            valor["demora"] = demora
        if falha is not None:
            valor["falha"] = falha
        self.respostas[url] = valor

    def sem_resposta(self, url):
        """Tira a URL das respostas: no modo --offline, URL ausente conta como erro de rede."""
        self.respostas.pop(url, None)

    def usa_cenario(self, nome):
        """Copia para a pasta de respostas um cenário pronto de fixtures/ (respostas.json e arquivos)."""
        origem = FIXTURES / nome
        for arquivo in origem.iterdir():
            shutil.copy(arquivo, self.offline / arquivo.name)
        self.respostas = json.loads((origem / "respostas.json").read_text(encoding="utf-8"))

    def grava_respostas(self):
        (self.offline / "respostas.json").write_text(
            json.dumps(self.respostas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # --- pasta de trabalho -------------------------------------------------------------------

    def poe_no_trabalho(self, nome, conteudo):
        texto = conteudo if isinstance(conteudo, str) else json.dumps(conteudo, ensure_ascii=False, indent=2) + "\n"
        self.trabalho.mkdir(parents=True, exist_ok=True)
        (self.trabalho / nome).write_text(texto, encoding="utf-8")

    def poe_contexto(self, dia=DIA, janela_horas=36):
        """Grava um contexto.json com todos os campos do CONTRATO, seção 4.1, sem edição anterior."""
        dominios = [{"id": d["id"], "nivel": 1, "desde": dia, "edicoes_sem_gatilho": 0,
                     "desce_hoje_sem_gatilho": False, "origem": None}
                    for d in self.le_dados("regua.json")["dominios"]]
        self.poe_no_trabalho("contexto.json", {
            "dia": dia, "janela_horas": janela_horas, "edicao_do_dia": None, "anterior": None,
            "alerta_anterior": {"nivel": 1, "dominios": dominios},
            "historias_recentes": [], "vigiar_vencendo": [], "candidatos": [], "vetores_recentes": []})

    # --- execução ----------------------------------------------------------------------------

    def roda(self, ferramenta, *args, agora=True, offline=True, raiz=None, trabalho=None, ambiente=None,
             tempo=180):
        """Roda `ferramenta` (coleta ou indicadores) como a rotina roda, pela linha de comando.

        `agora`: True usa o relógio da bancada; texto usa esse valor; None não define INFO_AGORA.
        `offline`: True usa a pasta de respostas da bancada; False roda sem --offline (só para
        casos que param antes de usar a rede, como o erro de uso).
        """
        raiz = Path(raiz or self.raiz)
        trabalho = Path(trabalho or self.trabalho)
        comando = [sys.executable, "-B", str(pasta_das_ferramentas() / (ferramenta + ".py"))]
        comando += [str(a) for a in args]
        comando += ["--raiz", str(raiz), "--trabalho", str(trabalho)]
        if offline:
            self.grava_respostas()
            comando += ["--offline", str(self.offline)]
        ambiente_final = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        ambiente_final.pop("INFO_AGORA", None)
        if agora is True:
            ambiente_final["INFO_AGORA"] = self.agora
        elif agora is not None:
            ambiente_final["INFO_AGORA"] = agora
        ambiente_final.update(ambiente or {})
        antes = _fotografa(trabalho)
        feito = subprocess.run(comando, cwd=str(raiz) if raiz.is_dir() else str(self.base), env=ambiente_final,
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               timeout=tempo)
        return Resultado(comando, feito.returncode, feito.stdout.decode("utf-8", "replace"),
                         feito.stderr.decode("utf-8", "replace"), antes, _fotografa(trabalho))


class Caso(unittest.TestCase):
    """Base dos testes: cada teste ganha uma bancada nova, apagada no fim."""

    maxDiff = None

    def setUp(self):
        self.b = Bancada()
        self.addCleanup(self.b.fecha)

    def confere_veredito(self, res, palavra, codigo):
        """CONTRATO, seção 0: a última linha começa com OK, PARCIAL ou FALHA, e o código é o da tabela."""
        self.assertNotIn("Traceback (most recent call last)", res.erro + res.saida,
                         "a ferramenta terminou com exceção solta" + res.relato())
        self.assertEqual(res.palavra, palavra,
                         "a última linha da saída padrão devia começar com %s" % palavra + res.relato())
        self.assertEqual(res.codigo, codigo, "código de saída" + res.relato())

    def json_gravado(self, res, nome):
        self.assertIn(nome, res.arquivos, "a ferramenta não gravou %s" % nome + res.relato())
        try:
            return res.json(nome)
        except ValueError as erro:
            self.fail("%s não é JSON em UTF-8: %s" % (nome, erro))

    def texto_gravado(self, res, nome):
        self.assertIn(nome, res.arquivos, "a ferramenta não gravou %s" % nome + res.relato())
        try:
            return res.texto(nome)
        except UnicodeDecodeError as erro:
            self.fail("%s não é texto em UTF-8: %s" % (nome, erro))

    def confere_json_no_padrao(self, res, nome):
        """CONTRATO, seção 0: UTF-8, sem BOM, acentos legíveis, recuo de 2 espaços, quebra de linha no fim."""
        self.assertIn(nome, res.arquivos, "a ferramenta não gravou %s" % nome + res.relato())
        bruto = res.arquivos[nome]
        self.assertFalse(bruto.startswith(b"\xef\xbb\xbf"), "%s começa com BOM" % nome)
        texto = bruto.decode("utf-8")
        self.assertTrue(texto.endswith("\n"), "%s não termina com quebra de linha" % nome)
        self.assertNotRegex(texto, r"\\u00[0-9a-fA-F]{2}", "%s traz acento escapado (\\u00..)" % nome)
        linhas = texto.split("\n")
        self.assertGreater(len(linhas), 2, "%s veio numa linha só: falta o recuo" % nome)
        self.assertRegex(linhas[1], r'^  "', "%s: a segunda linha devia ter recuo de 2 espaços" % nome)


# ---------------------------------------------------------------------------------------------
# Leitura de mesa.txt (CONTRATO, seção 1, "Formato de mesa.txt")
# ---------------------------------------------------------------------------------------------

RE_MESA_1 = re.compile(r"^MESA (\d{4}-\d\d-\d\d) · janela (\d+) h · feeds ok (\d+), falhos (\d+) · "
                       r"manchetes (\d+) · suspeitas: (\d+)$")
RE_MESA_2 = re.compile(r"^PARTIDOS COM MANCHETE:(.*)$")
RE_HISTORIA = re.compile(r"^### (h\d+) · (\d+) pontos? · partidos (\d+) \(([^)]*)\) · veículos (\d+) · (\w+)$")
RE_MANCHETE = re.compile(r"^- \[([A-Z]+)(\?)?\] (\S+)(?: · serve a: (.+?))? · fatos (\w+) · "
                         r"(\d\d/\d\d \d\d:\d\d) UTC · (\[SUSPEITA\] )?(.*)$")


class Mesa:
    """mesa.txt lida: as linhas, as histórias de cima, as da seção IA e as linhas fora do formato."""

    def __init__(self, texto):
        self.linhas = texto.split("\n")
        self.historias = []
        self.ia = []
        self.tem_secao_ia = False
        self.estranhas = []
        destino = self.historias
        historia = None
        atual = None
        for linha in self.linhas[3:]:
            if not linha.strip():
                continue
            if linha.startswith("### IA"):
                self.tem_secao_ia = True
                destino, historia, atual = self.ia, None, None
                continue
            achado = RE_HISTORIA.match(linha)
            if achado:
                historia = {"id": achado.group(1), "pontos": int(achado.group(2)),
                            "n_partidos": int(achado.group(3)), "siglas": achado.group(4).split(),
                            "veiculos": int(achado.group(5)), "categoria": achado.group(6), "manchetes": []}
                destino.append(historia)
                atual = None
                continue
            achado = RE_MANCHETE.match(linha)
            if achado and historia is not None:
                atual = {"sigla": achado.group(1), "incerto": bool(achado.group(2)), "veiculo": achado.group(3),
                         "serve_a": achado.group(4), "fatos": achado.group(5), "quando": achado.group(6),
                         "suspeita": bool(achado.group(7)), "titulo": achado.group(8), "resto": []}
                historia["manchetes"].append(atual)
                continue
            if linha[:1] in (" ", "\t") and atual is not None:
                atual["resto"].append(linha.strip())
                continue
            self.estranhas.append(linha)

    def todas(self):
        return self.historias + self.ia

    def manchetes(self):
        return [m for h in self.todas() for m in h["manchetes"]]


def le_mesa(texto):
    return Mesa(texto)


def partidos_da_linha_2(linha):
    """A segunda linha de mesa.txt: {sigla: contagem}, ou None se não segue o formato."""
    achado = RE_MESA_2.match(linha)
    if not achado:
        return None
    contagens = {}
    for parte in achado.group(1).split("·"):
        parte = parte.strip()
        if not parte:
            continue
        item = re.match(r"^([A-Z]{2}) (\d+)$", parte)
        if not item:
            return None
        contagens[item.group(1)] = int(item.group(2))
    return contagens


def quando_na_mesa(publicado_em):
    """Como a mesa escreve uma data-hora: DD/MM HH:MM, em UTC."""
    return instante(publicado_em).strftime("%d/%m %H:%M")
