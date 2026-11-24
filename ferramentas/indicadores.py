#!/usr/bin/env python3
"""indicadores.py · baixa preços e calcula gatilhos de preço (CONTRATO, seção 2).

    python3 ferramentas/indicadores.py [--dia D] [--trabalho P] [--tempo 45] [--offline PASTA]

Lê dados/indicadores.json (o catálogo) e dados/regua.json (os critérios `precos` de `niveis_alerta`).
Grava P/indicadores.json sempre que chega a rodar, mesmo sem valor nenhum. Com erro de uso, `contexto.json`
quebrado ou catálogo e régua ilegíveis, não grava nada (CONTRATO, seção 0). Este arquivo não traz endereço
nenhum: todo endereço mora no catálogo (também o modelo de endereço dos contratos futuros, no campo
`contratos`). Aqui ficam só os leitores (como ler cada formato de resposta) e a conta.
O que chega da rede é dado: só números e datas são aproveitados, e nenhum texto de fonte vai para a saída.
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
import json  # noqa: E402
import math  # noqa: E402
import re  # noqa: E402
import time  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402
from decimal import ROUND_HALF_UP, Decimal, localcontext  # noqa: E402

try:  # a base de fusos; sem ela, o yahoo_chart cai para meta.gmtoffset e, sem ele, para UTC
    from zoneinfo import ZoneInfo  # noqa: E402
except ImportError:  # pragma: no cover
    ZoneInfo = None

import comum  # noqa: E402
import rede  # noqa: E402

PARALELOS = 4          # indicadores ao mesmo tempo
POR_PEDIDO = 10.0      # segundos por pedido
TEMPO_PADRAO = 45.0    # teto de tempo total
VELHO_DIARIO, VELHO_MENSAL = 4, 62   # dias corridos: passou disso, a cotação está defasada
CONFIRMA_ATE = 4       # dias corridos: segunda fonte mais velha que isso não confirma nem desmente
JANELAS = ("1d", "7d")
SEM_CONFIRMACAO = " Alta maior sem confirmação de segunda fonte."
LETRAS_DOS_MESES = "FGHJKMNQUVXZ"   # janeiro a dezembro, como as bolsas escrevem o mês do contrato
CANDIDATOS = 4         # contratos tentados na troca de contrato (CONTRATO, seção 2, "Troca de contrato")
PERTO = 0.005          # 0,5%: dois fechamentos "iguais" do mesmo contrato, em fontes ou horas diferentes
MARCA = "{c}"

_RE_DECIMAL = re.compile(r"[+-]?(?:[0-9]{1,20}(?:\.[0-9]{0,20})?|\.[0-9]{1,20})(?:[eE][+-]?[0-9]{1,3})?")
_RE_DIA = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_RE_MES = re.compile(r"[0-9]{4}-[0-9]{2}")
_RE_DIA_BR = re.compile(r"([0-9]{2})/([0-9]{2})/([0-9]{4})")
_RE_ID = re.compile(r"[a-z][a-z0-9_]{1,30}")
_RE_FUSO = re.compile(r"[A-Za-z][A-Za-z_+-]{0,30}(?:/[A-Za-z0-9][A-Za-z0-9_+-]{0,30}){0,2}")
_RE_TRADE = re.compile(r"([0-9]{4})([0-9]{2})([0-9]{2})")
_EPOCA = datetime(1970, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------- números

def numero(valor):
    """Número finito e maior que zero, ou None. Aceita número de JSON e texto decimal ("5.8889").

    Booleano, "nan", "inf", texto com sublinhado e valor zero ou negativo não são preço: viram None."""
    if isinstance(valor, bool):
        return None
    try:
        if isinstance(valor, (int, float)):
            lido = float(valor)
        elif isinstance(valor, str) and _RE_DECIMAL.fullmatch(valor.strip()):
            lido = float(valor.strip())
        else:
            return None
    except (OverflowError, ValueError):
        return None
    return lido if math.isfinite(lido) and lido > 0 else None


def _decimal(valor):
    """O número como o leitor o escreveria (repr), já em decimal: 448.75 é 448,75, sem resíduo binário."""
    return valor if isinstance(valor, Decimal) else Decimal(repr(float(valor)))


def arredonda(valor, casas):
    """Arredonda em decimal, com a metade para longe do zero (0,25 vira 0,3; -0,25 vira -0,3), e não como o
    round() do Python, que em empate vai para o par e depende do erro binário (CONTRATO, seção 2, passo 4).
    Antes, o número é levado a 9 casas: some o resíduo de conta binária (6,2499999999 é 6,25)."""
    limpo = _decimal(valor).quantize(Decimal("1e-9"), rounding=ROUND_HALF_UP)
    return float(limpo.quantize(Decimal(1).scaleb(-casas), rounding=ROUND_HALF_UP)) + 0.0  # sem zero negativo


def variacao(novo, base):
    """Quanto `novo` está acima de `base`, em %, com 1 casa. A conta é feita em decimal, sobre os pontos
    crus da série (já com o fator), e só o resultado é arredondado."""
    with localcontext() as contexto:
        contexto.prec = 40
        return arredonda((_decimal(novo) / _decimal(base) - 1) * 100, 1)


def perto(valor, referencia):
    """Os dois números diferem em até 0,5% de `referencia`."""
    return abs(valor - referencia) <= PERTO * referencia


def em_portugues(valor, casas=None):
    """Número com vírgula: 6.1 vira "6,1". Sem `casas`, some a casa que é zero: 5.0 vira "5", 1.5 vira "1,5"."""
    if casas is None:
        texto = ("%.4f" % valor).rstrip("0").rstrip(".")
    else:
        texto = "%.*f" % (casas, valor)
    return texto.replace(".", ",")


# ---------------------------------------------------------------- os 6 leitores (CONTRATO, seção 2)
# Cada leitor recebe a resposta já aberta (texto, ou o objeto do JSON) e devolve pares (data, valor cru).
# Nenhum levanta exceção: o que não tem a forma esperada é pulado. Quem confere número e data é serie().

def le_fred_csv(texto):
    """CSV: cabeçalho `observation_date,ID`; cada linha é `AAAA-MM-DD,valor`. Valor vazio ou "." é pulado."""
    pares = []
    for linha in texto.splitlines():
        campos = linha.split(",")
        if len(campos) >= 2 and _RE_DIA.fullmatch(campos[0].strip()):
            pares.append((campos[0].strip(), campos[1]))
    return pares


def fuso_da_bolsa(meta):
    """O fuso em que o yahoo_chart tira o dia de cada carimbo: `meta.exchangeTimezoneName`, pela base de fusos
    da máquina; sem o nome, ou sem a base, o desvio fixo `meta.gmtoffset` (segundos); sem os dois, UTC.

    O Yahoo carimba a barra do dólar à meia-noite de Londres, que no verão inglês é 23:00 UTC da véspera:
    pelo dia em UTC, a barra sairia com um dia a menos."""
    meta = meta if isinstance(meta, dict) else {}
    nome = meta.get("exchangeTimezoneName")
    if ZoneInfo is not None and isinstance(nome, str) and _RE_FUSO.fullmatch(nome):
        try:
            return ZoneInfo(nome)
        except Exception:  # nome que a base não conhece, ou máquina sem a base de fusos
            pass
    desvio = meta.get("gmtoffset")
    if isinstance(desvio, int) and not isinstance(desvio, bool) and abs(desvio) <= 18 * 3600:
        return timezone(timedelta(seconds=desvio))
    return timezone.utc


def le_yahoo_chart(objeto):
    """JSON: em chart.result[0], `timestamp[]` (segundos Unix; a data é a do dia no fuso da bolsa, ver
    fuso_da_bolsa) e `indicators.quote[0].close[]`. Par com `close` null é pulado."""
    try:
        resultado = objeto["chart"]["result"][0]
        instantes, fechamentos = resultado["timestamp"], resultado["indicators"]["quote"][0]["close"]
    except (KeyError, IndexError, TypeError):
        return []
    if not isinstance(instantes, list) or not isinstance(fechamentos, list):
        return []
    fuso = fuso_da_bolsa(resultado.get("meta") if isinstance(resultado, dict) else None)
    pares = []
    for instante, fechamento in zip(instantes, fechamentos):
        if isinstance(instante, bool) or not isinstance(instante, (int, float)):
            continue
        if not (math.isfinite(instante) and 0 < instante < 4102444800):  # até o ano 2100
            continue
        pares.append(((_EPOCA + timedelta(seconds=int(instante))).astimezone(fuso).date().isoformat(), fechamento))
    return pares


def le_bcb_sgs(objeto):
    """JSON: lista de {"data": "DD/MM/AAAA", "valor": "5.8889"}."""
    pares = []
    for item in objeto if isinstance(objeto, list) else []:
        achado = _RE_DIA_BR.fullmatch(item["data"].strip()) if isinstance(item, dict) and isinstance(
            item.get("data"), str) else None
        if achado:
            pares.append(("%s-%s-%s" % (achado.group(3), achado.group(2), achado.group(1)), item.get("valor")))
    return pares


def le_eia_v2(objeto):
    """JSON: response.data[], com `period` (AAAA-MM-DD) e `value` (texto). Vem do mais novo para o mais velho."""
    try:
        dados = objeto["response"]["data"]
    except (KeyError, TypeError):
        return []
    pares = []
    for item in dados if isinstance(dados, list) else []:
        if isinstance(item, dict) and isinstance(item.get("period"), str) and _RE_DIA.fullmatch(item["period"].strip()):
            pares.append((item["period"].strip(), item.get("value")))
    return pares


def le_fao_csv(texto):
    """CSV: 2 linhas de título, o cabeçalho `Date,Food Price Index,…` e uma linha por mês. A data é
    `AAAA-MM` (vira dia 1); o valor é a 2ª coluna. Título, cabeçalho e linha sem valor não têm essa forma."""
    pares = []
    for linha in texto.splitlines():
        campos = linha.split(",")
        if len(campos) >= 2 and _RE_MES.fullmatch(campos[0].strip()):
            pares.append((campos[0].strip() + "-01", campos[1]))
    return pares


def le_cnbc_chart(objeto):
    """JSON: em `barData.priceBars[]`, a data são os 8 primeiros caracteres de `tradeTime` (texto
    `AAAAMMDD…`) e o valor é `close`, que vem como texto ("448.7500") e pode vir como número.
    Barra sem um dos dois é pulada."""
    try:
        barras = objeto["barData"]["priceBars"]
    except (KeyError, TypeError):
        return []
    pares = []
    for barra in barras if isinstance(barras, list) else []:
        quando = barra.get("tradeTime") if isinstance(barra, dict) else None
        achado = _RE_TRADE.match(quando) if isinstance(quando, str) else None
        if achado and "close" in barra:
            pares.append(("%s-%s-%s" % achado.groups(), barra["close"]))
    return pares


# leitor -> (função, a resposta é JSON?, User-Agent do pedido). O Yahoo só responde a navegador.
LEITORES = {
    "fred_csv": (le_fred_csv, False, rede.AGENTE),
    "yahoo_chart": (le_yahoo_chart, True, rede.AGENTE_NAVEGADOR),
    "bcb_sgs": (le_bcb_sgs, True, rede.AGENTE),
    "eia_v2": (le_eia_v2, True, rede.AGENTE),
    "fao_csv": (le_fao_csv, False, rede.AGENTE),
    "cnbc_chart": (le_cnbc_chart, True, rede.AGENTE),
}


def _constante_recusada(nome):
    raise ValueError(nome)


def serie(leitor, corpo, fator, dia):
    """A série de uma resposta: pares (data, valor) em ordem crescente de data, já com o fator.
    Sai o ponto sem valor, o de data impossível e o de data depois de `dia`. Data repetida: vale o
    último que veio na resposta, entre os que têm valor. Devolve None se a resposta nem pôde ser aberta (JSON quebrado)."""
    funcao, em_json, _ = LEITORES[leitor]
    aberto = corpo.decode("utf-8-sig", "replace")
    if em_json:
        try:
            aberto = json.loads(aberto, parse_constant=_constante_recusada)
        except (ValueError, RecursionError):
            return None
    por_data = {}
    for data, cru in funcao(aberto):
        valor = numero(cru)
        if valor is None or not comum.data_valida(data) or data > dia:
            continue
        valor *= fator
        if math.isfinite(valor) and valor > 0:
            por_data[data] = valor
    return sorted(por_data.items())


# ---------------------------------------------------------------- catálogo e régua

def _e_numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool) and math.isfinite(valor)


def le_catalogo(raiz):
    """Os indicadores de dados/indicadores.json (ESQUEMA, seção 14), conferidos no que a conta usa."""
    caminho = os.path.join(raiz, "dados", "indicadores.json")
    catalogo = comum.le_json(caminho)
    itens = catalogo.get("indicadores") if isinstance(catalogo, dict) else None
    if not isinstance(itens, list) or not itens:
        raise comum.Falha("%s: falta a lista indicadores" % caminho)
    vistos = set()
    for posicao, item in enumerate(itens):
        onde = "%s: indicadores[%d]" % (caminho, posicao)
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not _RE_ID.fullmatch(item["id"]):
            raise comum.Falha("%s: id ilegível" % onde)
        onde = "%s: indicador %s" % (caminho, item["id"])
        if item["id"] in vistos:
            raise comum.Falha("%s: id repetido" % onde)
        vistos.add(item["id"])
        for campo in ("nome", "unidade", "dominio"):
            if not isinstance(item.get(campo), str) or not item[campo].strip():
                raise comum.Falha("%s: campo %s ilegível" % (onde, campo))
        if not isinstance(item.get("obrigatorio"), bool) or item.get("frequencia") not in ("diaria", "mensal"):
            raise comum.Falha("%s: obrigatorio ou frequencia ilegível" % onde)
        faixa = item.get("faixa")
        if not (isinstance(faixa, dict) and _e_numero(faixa.get("min")) and _e_numero(faixa.get("max"))
                and 0 <= faixa["min"] < faixa["max"]):
            raise comum.Falha("%s: faixa ilegível" % onde)
        casas = item.get("casas", 2)
        if isinstance(casas, bool) or not isinstance(casas, int) or not 0 <= casas <= 6:
            raise comum.Falha("%s: casas ilegível" % onde)
        fontes = item.get("fontes")
        if not isinstance(fontes, list) or not fontes:
            raise comum.Falha("%s: sem fontes" % onde)
        for fonte in fontes:
            if not (isinstance(fonte, dict) and all(isinstance(fonte.get(c), str) and fonte[c].strip()
                                                    for c in ("nome", "url", "leitor"))):
                raise comum.Falha("%s: fonte sem nome, url ou leitor" % onde)
            if "fator" in fonte and not (_e_numero(fonte["fator"]) and fonte["fator"] > 0):
                raise comum.Falha("%s: fator ilegível na fonte %s" % (onde, fonte["nome"]))
    return itens


def le_criterios(raiz):
    """Os critérios `precos` da régua. Devolve (por_indicador, codigos, avisos):
    por_indicador[id] é a lista de critérios na ordem da régua; codigos[(dominio, nivel)] é o código da célula."""
    caminho = os.path.join(raiz, "dados", "regua.json")
    regua = comum.le_json(caminho)
    niveis = regua.get("niveis_alerta") if isinstance(regua, dict) else None
    if not isinstance(niveis, list) or not niveis:
        raise comum.Falha("%s: falta a lista niveis_alerta" % caminho)
    por_indicador, codigos, avisos = {}, {}, []
    for nivel in niveis:
        numero_do_nivel = nivel.get("nivel") if isinstance(nivel, dict) else None
        celulas = nivel.get("criterios") if isinstance(nivel, dict) else None
        if isinstance(numero_do_nivel, bool) or not isinstance(numero_do_nivel, int) or not isinstance(celulas, dict):
            raise comum.Falha("%s: niveis_alerta com nível ou critérios ilegíveis" % caminho)
        for dominio, celula in celulas.items():
            precos = celula.get("precos") if isinstance(celula, dict) else None
            if not isinstance(precos, list) or not isinstance(celula.get("codigo"), str):
                raise comum.Falha("%s: critério %s do nível %d sem codigo ou sem precos"
                                  % (caminho, dominio, numero_do_nivel))
            codigos[(dominio, numero_do_nivel)] = celula["codigo"]
            for preco in precos:
                if not (isinstance(preco, dict) and isinstance(preco.get("indicador"), str)
                        and isinstance(preco.get("janela"), str) and _e_numero(preco.get("alta_minima_pct"))):
                    raise comum.Falha("%s: critério de preço ilegível em %s" % (caminho, celula["codigo"]))
                if preco["janela"] not in JANELAS:
                    avisos.append("aviso: critério de preço de %s com janela %r, que a ferramenta não conhece: pulado"
                                  % (celula["codigo"], preco["janela"]))
                    continue
                por_indicador.setdefault(preco["indicador"], []).append({
                    "nivel": numero_do_nivel, "dominio": dominio, "codigo": celula["codigo"],
                    "janela": preco["janela"], "alta": float(preco["alta_minima_pct"])})
    return por_indicador, codigos, avisos


# ---------------------------------------------------------------- a conta (passos 2 a 8)

def fora_da_serie(pontos, indice):
    """O ponto `indice` é um tique da fonte: fica fora de 0,5 a 2 vezes os DOIS vizinhos dele na série (o
    anterior e o seguinte). Um decimal deslocado (92,44 que vira 9,244) dá isso; um choque de mercado, mesmo
    forte, não dá, porque o preço não dobra nem cai à metade de um ponto para o outro e volta no seguinte.
    O primeiro e o último ponto, que têm um vizinho só, não são julgados aqui (o último tem a faixa)."""
    if not 0 < indice < len(pontos) - 1:
        return False
    valor = pontos[indice][1]
    return all(not vizinho / 2 <= valor <= vizinho * 2 for vizinho in (pontos[indice - 1][1], pontos[indice + 1][1]))


def mede(pontos, mensal):
    """Passo 4, dentro de uma série só. Devolve {"data", "cru", "1d", "7d", "base_1d", "base_7d", "fora"}: o
    último ponto, a variação sobre o ponto anterior e a variação sobre o ponto mais novo com data de 7 a 10
    dias antes da dele, a data de cada ponto de base (None quando não há) e, em "fora", os pares (janela,
    data) do ponto de base que é tique da fonte (fora_da_serie): essa variação fica None, sem base."""
    data, ultimo = pontos[-1]
    medida = {"data": data, "cru": ultimo, "1d": None, "7d": None, "base_1d": None, "base_7d": None, "fora": []}
    if len(pontos) >= 2:
        if fora_da_serie(pontos, len(pontos) - 2):
            medida["fora"].append(("1d", pontos[-2][0]))
        else:
            medida["1d"] = variacao(ultimo, pontos[-2][1])
            medida["base_1d"] = pontos[-2][0]
    if not mensal:
        for indice in range(len(pontos) - 2, -1, -1):
            outra, base = pontos[indice]
            distancia = comum.dias_entre(outra, data)
            if distancia > 10:
                break
            if distancia >= 7:
                if fora_da_serie(pontos, indice):
                    medida["fora"].append(("7d", outra))
                else:
                    medida["7d"] = variacao(ultimo, base)
                    medida["base_7d"] = outra
                break
    return medida


def textos_fora_da_serie(medida):
    """Um texto por ponto de base que é tique da fonte: "ponto de 16/11 fora da série: variação de 7 dias sem base"."""
    return ["ponto de %s fora da série: variação %s sem base" % (
        comum.dd_mm(data), "de 7 dias" if janela == "7d" else "sobre o ponto anterior") for janela, data in medida["fora"]]


def cumpre(criterio, medida, dia):
    """Passo 7: só alta conta; variação null não cumpre; a janela 1d só vale no dia da cotação."""
    alta = medida[criterio["janela"]]
    if alta is None or alta < criterio["alta"]:
        return False
    return criterio["janela"] != "1d" or medida["data"] == dia


def o_que_vale(cumpridos):
    """O critério de maior nível; no empate de nível, o de 7 dias; no empate que sobra, o primeiro da régua."""
    return max(cumpridos, key=lambda c: (c["nivel"], c["janela"] == "7d"))


def texto_do_gatilho(nome, medida, janela, limiar, confirmado_ou_nivel_2):
    quando = "em 7 dias, até %s" if janela == "7d" else "no dia %s"
    texto = "%s subiu %s%% %s (limiar: %s%%)." % (
        nome, em_portugues(medida[janela], 1), quando % comum.dd_mm(medida["data"]), em_portugues(limiar))
    return texto if confirmado_ou_nivel_2 else texto + SEM_CONFIRMACAO


# ---------------------------------------------------------------- troca de contrato (passo 4)

def contratos_validos(contratos):
    """O campo `contratos` de uma fonte na forma da regra C6 (ESQUEMA, seção 14): {"modelo", "meses"}, com
    exatamente uma marca {c} no modelo, e de 1 a 12 letras de FGHJKMNQUVXZ, sem repetir, na ordem do ano."""
    if not isinstance(contratos, dict) or sorted(contratos) != ["meses", "modelo"]:
        return False
    modelo, meses = contratos["modelo"], contratos["meses"]
    if not isinstance(modelo, str) or modelo.count(MARCA) != 1 or not comum.url_valida(modelo.replace(MARCA, "H27")):
        return False
    if not isinstance(meses, str) or not 1 <= len(meses) <= 12 or any(m not in LETRAS_DOS_MESES for m in meses):
        return False
    posicoes = [LETRAS_DOS_MESES.index(m) for m in meses]
    return posicoes == sorted(set(posicoes))


def candidatos(meses, dia):
    """Os 4 primeiros contratos de `meses` com mês igual ou posterior ao mês de `dia`: ["Z26", "H27", …]."""
    ano, mes = int(dia[:4]), int(dia[5:7])
    lista = []
    for este_ano in range(ano, ano + CANDIDATOS + 1):
        for letra in meses:
            numero_do_mes = LETRAS_DOS_MESES.index(letra) + 1
            if (este_ano, numero_do_mes) >= (ano, mes) and len(lista) < CANDIDATOS:
                lista.append("%s%02d" % (letra, este_ano % 100))
    return lista


def mede_no_contrato(pontos, contrato, medida):
    """Troca de contrato, itens 3 e 4 (CONTRATO, seção 2): com a série de um contrato que casou, a medida nova (ou None, com o porquê).

    Anda para trás nas datas que as duas séries têm. Enquanto os valores diferem em até 0,5%, a série escolhida
    já estava nesse contrato; a primeira data em que diferem mais marca a troca. Se um ponto de base de alguma
    variação é dessa data ou de antes, as duas variações são refeitas na série do contrato, nos mesmos dias.
    Devolve (medida nova ou None, dia da troca ou None, motivo)."""
    do_contrato = dict(contrato)
    escolhida = dict(pontos)
    comuns = [data for data, _ in pontos if data in do_contrato]
    ultima_fora, primeira_dentro = None, None
    for data in reversed(comuns):
        if not perto(do_contrato[data], escolhida[data]):
            ultima_fora = data
            break
        primeira_dentro = data
    if ultima_fora is None:
        return None, None, "a série já estava no contrato em todas as datas"
    bases = [medida[chave] for chave in ("base_1d", "base_7d") if medida[chave] is not None]
    if not any(base <= ultima_fora for base in bases):
        return None, primeira_dentro, "a troca foi antes dos pontos de base"
    if any(base not in do_contrato for base in bases):
        return None, primeira_dentro, "o contrato não tem os pontos de base"
    nova = dict(medida)
    fim = do_contrato[medida["data"]]
    nova["1d"] = variacao(fim, do_contrato[medida["base_1d"]]) if medida["base_1d"] else None
    nova["7d"] = variacao(fim, do_contrato[medida["base_7d"]]) if medida["base_7d"] else None
    return nova, primeira_dentro, ""


class Medidor:
    """Mede um indicador: escolhe a fonte, faz a conta (no contrato, se a série trocou de contrato) e, se a
    alta é forte, pede a segunda fonte."""

    def __init__(self, conexao, dia, prazo, criterios, codigos):
        self.conexao, self.dia, self.prazo = conexao, dia, prazo
        self.criterios, self.codigos = criterios, codigos
        self.parciais = {}  # id -> resultado já medido; serve se o teto cortar um pedido depois dele

    def _pontos(self, item, fonte, avisos, url=None, rotulo=None):
        """A série de uma fonte, se ela serve (passo 2); senão None, com o porquê em `avisos`."""
        rotulo = rotulo or fonte["nome"] + ": "
        if fonte["leitor"] not in LEITORES:
            avisos.append(rotulo + "leitor %r desconhecido: fonte pulada" % fonte["leitor"])
            return None
        resposta = self.conexao.baixa(url or fonte["url"], POR_PEDIDO, self.prazo, agente=LEITORES[fonte["leitor"]][2])
        if not resposta.boa:
            avisos.append(rotulo + resposta.falha())
            return None
        if resposta.cortada:  # série cortada no meio pode ter perdido justamente os pontos mais novos
            avisos.append(rotulo + "resposta maior que 2 MB")
            return None
        pontos = serie(fonte["leitor"], resposta.corpo, float(fonte.get("fator", 1)), self.dia)
        if not pontos:
            avisos.append(rotulo + ("resposta ilegível" if pontos is None else "nenhum ponto com valor até %s"
                                    % comum.dd_mm(self.dia)))
            return None
        faixa = item["faixa"]
        if not faixa["min"] <= pontos[-1][1] <= faixa["max"]:
            avisos.append(rotulo + "último valor fora da faixa (%s)" % em_portugues(arredonda(pontos[-1][1], 4)))
            return None
        return pontos

    def _defasada(self, item, data):
        return comum.dias_entre(data, self.dia) > (VELHO_MENSAL if item["frequencia"] == "mensal" else VELHO_DIARIO)

    def _gatilho(self, item, medida, confirmado):
        """Passos 7 e 8: o critério cumprido que vale; sem confirmação, o de nível 2 do domínio."""
        cumpridos = [c for c in self.criterios.get(item["id"], ()) if cumpre(c, medida, self.dia)]
        if not cumpridos:
            return None, None
        maior = o_que_vale(cumpridos)
        if maior["nivel"] < 3 or confirmado:
            saiu, limiar = maior["codigo"], maior["alta"]
        else:
            saiu = self.codigos.get((maior["dominio"], 2), "%s.2" % maior["dominio"])
            mesma_janela = [c for c in self.criterios[item["id"]] if c["janela"] == maior["janela"]]
            limiar = min(mesma_janela, key=lambda c: (c["nivel"] != 2, c["nivel"]))["alta"]
        texto = texto_do_gatilho(item["nome"], medida, maior["janela"], limiar, maior["nivel"] < 3 or confirmado)
        return maior, {"criterio": saiu, "ref": item["id"], "texto": texto}

    def _confirma(self, item, posicao, maior, medida, avisos):
        """Passo 8: a fonte seguinte do catálogo que serve, com a mesma variação medida nela. Fonte velha (data
        mais de 4 dias antes da data da escolhida) não confirma nem desmente, e a busca para nela."""
        for fonte in item["fontes"][posicao + 1:]:
            pontos = self._pontos(item, fonte, avisos)
            if pontos is None:
                continue
            segunda = mede(pontos, item["frequencia"] == "mensal")
            if comum.dias_entre(segunda["data"], medida["data"]) > CONFIRMA_ATE:
                avisos.append(fonte["nome"] + ": cotação de %s, velha demais para confirmar a alta de %s"
                              % (comum.dd_mm(segunda["data"]), comum.dd_mm(medida["data"])))
                return False
            return any(c["janela"] == maior["janela"] and c["nivel"] >= 2 and cumpre(c, segunda, self.dia)
                       for c in self.criterios[item["id"]])
        return False

    def _no_contrato(self, item, fonte, pontos, medida, avisos):
        """Troca de contrato (CONTRATO, seção 2): só na fonte escolhida, e só se ela tem `contratos`. Devolve (medida, aviso para a lista
        `avisos` de indicadores.json, ou None). Qualquer falha deixa a medida como estava."""
        contratos = fonte.get("contratos")
        if contratos is None:
            return medida, None
        rotulo = fonte["nome"] + ", contrato %s: "
        if not contratos_validos(contratos):
            avisos.append(fonte["nome"] + ": campo contratos fora da regra C6: variação medida na série do catálogo")
            return medida, None
        for codigo in candidatos(contratos["meses"], self.dia):
            serie_do_contrato = self._pontos(item, fonte, avisos, contratos["modelo"].replace(MARCA, codigo),
                                             rotulo % codigo)
            if serie_do_contrato is None:
                if time.monotonic() >= self.prazo:
                    break  # o teto chegou: não adianta pedir o candidato seguinte
                continue
            ultimo_data, ultimo_valor = serie_do_contrato[-1]
            if ultimo_data != medida["data"] or not perto(ultimo_valor, medida["cru"]):
                continue  # não casa: é outro contrato
            nova, dia_da_troca, motivo = mede_no_contrato(pontos, serie_do_contrato, medida)
            if nova is None:
                if motivo == "o contrato não tem os pontos de base":
                    avisos.append(rotulo % codigo + motivo + ": variação medida na série do catálogo")
                return medida, None
            avisos.append(rotulo % codigo + "a série trocou de contrato em %s: variações medidas no contrato"
                          % comum.dd_mm(dia_da_troca))
            return nova, "%s: variações medidas no contrato %s, porque a série trocou de contrato em %s." % (
                item["id"], codigo, comum.dd_mm(dia_da_troca))
        avisos.append(fonte["nome"] + ": nenhum contrato casou com a série: variação medida na série do catálogo")
        return medida, None

    def indicador(self, item):
        """Devolve (linha do indicador, gatilho ou None, avisos do terminal, avisos para a lista `avisos` de
        indicadores.json). Nunca mistura pontos de duas fontes."""
        avisos, servem, escolhida = [], [], None
        for posicao, fonte in enumerate(item["fontes"]):
            pontos = self._pontos(item, fonte, avisos)
            if pontos is None:
                continue
            if not self._defasada(item, pontos[-1][0]):
                escolhida = (posicao, pontos)  # passo 3: a primeira que serve e não está defasada
                break
            servem.append((posicao, pontos))
        if escolhida is None and servem:  # todas defasadas: a de data mais nova; empate, a primeira do catálogo
            escolhida = max(servem, key=lambda par: (par[1][-1][0], -par[0]))
        linha = linha_vazia(item)
        if escolhida is None:
            return linha, None, avisos, []
        posicao, pontos = escolhida
        medida = mede(pontos, item["frequencia"] == "mensal")
        fonte = item["fontes"][posicao]
        # Ponto de base que é tique da fonte: a variação fica sem base, e o porquê vai para os dois avisos.
        fora = textos_fora_da_serie(medida)
        avisos.extend(fonte["nome"] + ": " + texto for texto in fora)
        do_arquivo = ["%s: %s." % (item["id"], texto) for texto in fora]
        linha.update(valor=arredonda(medida["cru"], item.get("casas", 2)), variacao_pct=medida["1d"],
                     variacao_7d_pct=medida["7d"], data=medida["data"],
                     defasado=self._defasada(item, medida["data"]),
                     fonte={"nome": fonte["nome"], "url": fonte["url"]})
        if linha["defasado"]:
            return linha, None, avisos, do_arquivo
        self.parciais[item["id"]] = (dict(linha), self._gatilho(item, medida, False)[1], list(avisos), list(do_arquivo))
        medida, no_contrato = self._no_contrato(item, fonte, pontos, medida, avisos)
        if no_contrato is not None:
            do_arquivo.append(no_contrato)
        linha.update(variacao_pct=medida["1d"], variacao_7d_pct=medida["7d"])
        maior, gatilho = self._gatilho(item, medida, False)
        if maior is None or maior["nivel"] < 3:
            return linha, gatilho, avisos, do_arquivo
        self.parciais[item["id"]] = (dict(linha), gatilho, list(avisos), list(do_arquivo))
        if self._confirma(item, posicao, maior, medida, avisos):
            linha["confirmado"] = True
            gatilho = self._gatilho(item, medida, True)[1]
        return linha, gatilho, avisos, do_arquivo


def linha_vazia(item):
    """O indicador sem dado (passo 6): valor, variações e data em null, e a primeira fonte do catálogo."""
    return {"id": item["id"], "nome": item["nome"], "dominio": item["dominio"], "valor": None,
            "unidade": item["unidade"], "variacao_pct": None, "variacao_7d_pct": None, "data": None,
            "defasado": True, "confirmado": False,
            "fonte": {"nome": item["fontes"][0]["nome"], "url": item["fontes"][0]["url"]}}


# ---------------------------------------------------------------- linha de comando

def _pasta(texto):
    if not texto.strip():
        raise ValueError("falta o nome da pasta")
    return texto


def _tempo(texto):
    """--tempo: segundos inteiros, de 1 a 3600, como na coleta (CONTRATO, seção 2)."""
    try:
        valor = int(texto)
    except ValueError:
        valor = 0
    if not 1 <= valor <= 3600:
        raise argparse.ArgumentTypeError("use um número inteiro de 1 a 3600")
    return valor


def _vazio(dia):
    return {"versao": 1, "dia": dia, "gerada_em": comum.agora_texto(), "indicadores": [], "gatilhos": [],
            "falhas": [], "avisos": []}


def _resumo(linha):
    if linha["valor"] is None:
        return "%s: sem dado" % linha["id"]
    partes = ["%s: %s %s em %s" % (linha["id"], em_portugues(linha["valor"]), linha["unidade"],
                                   comum.dd_mm(linha["data"]))]
    for campo, rotulo in (("variacao_pct", "sobre o ponto anterior"), ("variacao_7d_pct", "em 7 dias")):
        if linha[campo] is not None:
            partes.append("%s%s%% %s" % ("+" if linha[campo] > 0 else "", em_portugues(linha[campo], 1), rotulo))
    partes.append(linha["fonte"]["nome"] + (" · DEFASADO" if linha["defasado"] else ""))
    return " · ".join(partes)


def _plural(quantos, um, varios):
    return "%d %s" % (quantos, um if quantos == 1 else varios)


def principal(argv):
    inicio = time.monotonic()
    an = comum.opcoes("Baixa os preços do catálogo e calcula os gatilhos de preço.")
    an.add_argument("--tempo", metavar="S", type=_tempo, default=TEMPO_PADRAO,
                    help="teto de tempo total, em segundos inteiros, de 1 a 3600 (padrão: 45)")
    an.add_argument("--offline", metavar="PASTA", type=_pasta, default=None,
                    help="no lugar da rede, lê PASTA/respostas.json (modo dos testes)")
    args = an.parse_args(argv)
    conexao = rede.Rede(offline=args.offline)  # --offline que não serve é erro de uso: antes de qualquer gravação
    args = comum.prepara(args)  # contexto.json quebrado é FALHA, e nada é gravado (CONTRATO, seção 0)
    destino = os.path.join(args.trabalho, "indicadores.json")
    saida = comum.Saida(args.json)
    saida.dado("arquivo", destino)
    args.gravado = False
    try:
        catalogo = le_catalogo(args.raiz)
        criterios, codigos, avisos = le_criterios(args.raiz)
    except comum.Falha:
        raise  # catálogo ou régua ilegível: nada é gravado, e o arquivo de antes fica como estava
    except Exception:
        comum.grava_json(destino, _vazio(args.dia))
        raise
    try:
        return _roda(args, conexao, inicio, destino, saida, catalogo, criterios, codigos, avisos)
    except comum.ErroDeUso:
        raise
    except Exception:  # erro inesperado no meio: a saída vazia é gravada, e o passo seguinte não lê a de ontem
        if not args.gravado:
            comum.grava_json(destino, _vazio(args.dia))
        raise


def _roda(args, conexao, inicio, destino, saida, catalogo, criterios, codigos, avisos):
    for sobra in sorted(set(criterios) - set(item["id"] for item in catalogo)):
        avisos.append("aviso: a régua cita o indicador %s, que não está no catálogo" % sobra)
    medidor = Medidor(conexao, args.dia, rede.prazo_de(inicio, args.tempo), criterios, codigos)
    # Toda chave já nasce aqui: thread atrasada que grave depois do teto não muda o tamanho do dicionário.
    medidor.parciais = dict((item["id"], None) for item in catalogo)
    feitos = rede.em_paralelo(medidor.indicador, catalogo, PARALELOS, medidor.prazo)
    parciais = dict(medidor.parciais)

    indicadores, gatilhos, falhas, do_arquivo_todos = [], [], [], []
    for item, feito in zip(catalogo, feitos):
        if feito is None:  # o teto cortou: fica o que já estava medido, ou nada
            linha, gatilho, do_item, do_arquivo = parciais.get(item["id"]) or (None, None, [], [])
            do_item = do_item + ["não coube no tempo"]
        else:
            linha, gatilho, do_item, do_arquivo = feito
        if linha is None:
            linha = linha_vazia(item)
        if do_item:  # uma linha por indicador, com o que cada fonte dele respondeu
            avisos.append("aviso: %s · %s" % (item["id"], " · ".join(do_item)))
        indicadores.append(linha)
        if gatilho is not None:
            gatilhos.append(gatilho)
        do_arquivo_todos.extend(do_arquivo)
        if linha["valor"] is None:
            falhas.append({"id": item["id"], "erro": "todas as fontes falharam"})
        elif item["frequencia"] == "diaria" and linha["variacao_7d_pct"] is None:
            falhas.append({"id": item["id"], "erro": "sem base de 7 dias"})

    comum.grava_json(destino, {"versao": 1, "dia": args.dia, "gerada_em": comum.agora_texto(),
                               "indicadores": indicadores, "gatilhos": gatilhos, "falhas": falhas,
                               "avisos": do_arquivo_todos})
    args.gravado = True

    por_id = dict((linha["id"], linha) for linha in indicadores)
    obrigatorios = [item["id"] for item in catalogo if item["obrigatorio"]]
    de_7_dias = set(i for i, lista in criterios.items() if any(c["janela"] == "7d" for c in lista))
    sem_dado = [i for i in obrigatorios if por_id[i]["valor"] is None or por_id[i]["defasado"]]
    sem_base = [i for i in obrigatorios if i in de_7_dias and i not in sem_dado
                and por_id[i]["variacao_7d_pct"] is None]
    com_valor = sum(1 for linha in indicadores if linha["valor"] is not None)

    saida.linha("INDICADORES %s · %d do catálogo, %d com valor" % (args.dia, len(indicadores), com_valor))
    for linha in indicadores:
        saida.linha(_resumo(linha))
    for gatilho in gatilhos:
        saida.linha("gatilho %s: %s" % (gatilho["criterio"], gatilho["texto"]))
    for aviso in avisos:
        saida.linha(aviso)
    saida.linha("gravado: %s" % destino)
    saida.dado("indicadores", com_valor)
    saida.dado("gatilhos", len(gatilhos))
    saida.dado("sem_dado", sem_dado)
    saida.dado("sem_base_7d", sem_base)

    if not com_valor:
        return saida.fecha("FALHA sem rede: 0 indicadores", comum.SEM_REDE)
    if sem_dado or sem_base:
        partes = (["sem dado: " + ", ".join(sem_dado)] if sem_dado else []) + (
            ["sem base de 7 dias: " + ", ".join(sem_base)] if sem_base else [])
        return saida.fecha("PARCIAL " + "; ".join(partes))
    return saida.fecha("OK %s, %s de preço" % (_plural(com_valor, "indicador", "indicadores"),
                                               _plural(len(gatilhos), "gatilho", "gatilhos")))


if __name__ == "__main__":
    comum.executa(principal)
