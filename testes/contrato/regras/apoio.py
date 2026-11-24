#!/usr/bin/env python3
"""Apoio dos testes de contrato de valida.py e de publica.py.

Quem escreveu estes testes leu só os contratos (ESQUEMA e CONTRATO), nunca o código das
ferramentas. Por isso tudo aqui trata a ferramenta como caixa-preta: linha de comando, saída
padrão, código de saída e arquivos gravados.

O que este módulo dá:

- roda(): chama uma ferramenta e devolve saída, código e última linha;
- fotografa() e diferenca(): provam "não grava nada" e "tudo ou nada";
- monta_raiz(), grava_edicoes(): a raiz temporária, a partir da cópia congelada dos dados;
- inicia_git(), commita(): repositório git temporário, com identidade de teste só dele;
- monta_edicao(), edicao_falha(), rascunho_de(): edições válidas feitas a partir do exemplo;
- Trabalho: a pasta de trabalho coerente com um rascunho (CONTRATO, seção 0);
- Caso: a classe-base dos testes, com as conferências de veredito.

Nada aqui usa rede nem grava dentro do repositório: tudo vai para uma pasta temporária.
"""
import copy
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ_REPO = os.path.normpath(os.path.join(AQUI, "..", "..", ".."))
FERRAMENTAS = os.path.join(RAIZ_REPO, "ferramentas")
FIXTURES = os.path.join(RAIZ_REPO, "testes", "fixtures")
DADOS_CONGELADOS = os.path.join(FIXTURES, "dados")
EXEMPLO = os.path.join(FIXTURES, "edicao-exemplo.json")
MODELO_ESPERADO = os.path.join(AQUI, "modelo_esperado.txt")

ARQUIVOS_DE_DADOS = ("regua.json", "players.json", "veiculos.json", "vetores.json", "indicadores.json")
DIA_DO_EXEMPLO = "2026-11-19"
DIA = "2026-11-20"          # o dia padrão dos testes
HORA = "21:14:03"           # 18h14 em Brasília: a hora em que a rotina costuma publicar
TEMPO_MAXIMO = 120          # segundos por chamada de ferramenta
ATOM = "http://www.w3.org/2005/Atom"

# Ordem das chaves, como nas tabelas do ESQUEMA (seções 1 a 9): "As chaves são gravadas na ordem
# das tabelas abaixo" (seção 0).
ORDEM = {
    "raiz": ["versao", "data", "gerada_em", "estado", "exemplo", "resumo", "alerta", "indicadores",
             "principais", "radar", "placar_do_dia", "novos_players", "errata", "respostas", "bastidores"],
    "alerta": ["nivel", "tendencia", "motivo", "dominios"],
    "dominio": ["id", "nivel", "tendencia", "desde", "sem_preco", "gatilhos", "leitura", "vigiar"],
    "gatilho": ["criterio", "ref", "texto", "excecao", "alivio"],
    "indicador": ["id", "nome", "dominio", "valor", "unidade", "variacao_pct", "variacao_7d_pct",
                  "data", "defasado", "confirmado", "fonte"],
    "fonte_indicador": ["nome", "url"],
    "principal": ["id", "categoria", "titulo", "fato", "nao_confirmado", "ataques", "realmente",
                  "na_pratica", "no_brasil", "eixo", "placar", "sem_placar", "vetores", "dominios",
                  "vigiar", "confianca", "conflito_de_interesse", "continuacao_de", "fontes"],
    "radar": ["id", "categoria", "titulo", "fato", "ataque", "eixo", "placar", "sem_placar", "vetores",
              "dominios", "confianca", "conflito_de_interesse", "continuacao_de", "fontes"],
    "ataque": ["veiculo", "lado", "alvo", "alvo_nome", "enquadramento", "omite", "url"],
    "eixo": ["tema", "sentido", "porque"],
    "placar": ["partido", "efeito", "forca", "evidencia", "porque"],
    "vetor": ["player", "para", "forca", "tema", "porque", "url"],
    "fonte": ["veiculo", "nome", "titulo", "url", "publicado_em", "primaria"],
    "placar_do_dia": ["partido", "saldo", "narrativa", "frase"],
    "novo_player": ["id", "nome", "tipo", "partido", "time", "time_discutivel", "dna", "dna_fontes",
                    "duvidas", "nota", "justificativa", "url"],
    "errata": ["edicao", "item", "erro", "correcao", "url", "anula_vetor"],
    "resposta": ["edicao", "item", "pergunta", "resposta", "texto", "url"],
    "bastidores": ["modo", "veiculos_consultados", "feeds_ok", "feeds_falhos", "paginas_lidas", "buscas",
                   "minutos", "injecoes_ignoradas", "candidatos", "veiculos_sugeridos", "limites"],
    "candidato": ["id", "nome", "motivo"],
}
# Uma entrada de dados/vetores.json e uma de anulação (ESQUEMA, seção 12).
ORDEM_VETOR_REGISTRADO = ["id", "data", "item", "player", "de", "para", "forca", "tema", "porque", "url",
                          "conflito_de_interesse"]
ORDEM_ANULACAO = ["id", "data", "anula", "porque", "url"]
# Uma entrada de edicoes/indice.json (ESQUEMA, seção 11).
ORDEM_INDICE = ["data", "arquivo", "texto", "estado", "nivel", "tendencia", "niveis", "saldos", "eixos",
                "indicadores", "resumo", "gerada_em", "exemplo", "corrigida_em"]


# ---------------------------------------------------------------------------------------------
# Leitura e gravação
# ---------------------------------------------------------------------------------------------

def le_texto(caminho):
    with open(caminho, encoding="utf-8") as arq:
        return arq.read()


def le_bytes(caminho):
    with open(caminho, "rb") as arq:
        return arq.read()


def le_json(caminho):
    return json.loads(le_texto(caminho))


def texto_json(objeto):
    """O formato de JSON do CONTRATO, seção 0: acentos legíveis, recuo de 2 e quebra de linha no fim."""
    return json.dumps(objeto, ensure_ascii=False, indent=2) + "\n"


def grava_texto(caminho, texto):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8", newline="\n") as arq:
        arq.write(texto)


def grava_json(caminho, objeto):
    grava_texto(caminho, texto_json(objeto))


_DADOS = {}
_PRONTOS = {}


def _lido(nome):
    """Um arquivo da cópia congelada, lido uma vez. É o objeto guardado: quem recebe não pode mudar."""
    if nome not in _DADOS:
        _DADOS[nome] = le_json(os.path.join(DADOS_CONGELADOS, nome + ".json"))
    return _DADOS[nome]


def dados(nome):
    """Um arquivo da cópia congelada dos dados, já lido. Devolve sempre uma cópia nova."""
    return copy.deepcopy(_lido(nome))


def regua():
    return dados("regua")


def veiculos():
    """O mapa de veículos congelado, por id. É só para leitura: o objeto é o mesmo a cada chamada."""
    if "veiculos" not in _PRONTOS:
        _PRONTOS["veiculos"] = {v["id"]: v for v in _lido("veiculos")["veiculos"]}
    return _PRONTOS["veiculos"]


def catalogo():
    """Os ids do catálogo de indicadores congelado, na ordem do arquivo."""
    return [i["id"] for i in _lido("indicadores")["indicadores"]]


def partidos():
    return [p["id"] for p in _lido("regua")["partidos"]]


def dominios():
    return [d["id"] for d in _lido("regua")["dominios"]]


def rotulo_do_nivel(nivel):
    return {n["nivel"]: n["rotulo"] for n in _lido("regua")["niveis_alerta"]}[nivel]


def exemplo():
    """A edição de exemplo, como está no repositório. Devolve sempre uma cópia nova."""
    if "exemplo" not in _PRONTOS:
        _PRONTOS["exemplo"] = le_json(EXEMPLO)
    return copy.deepcopy(_PRONTOS["exemplo"])


# ---------------------------------------------------------------------------------------------
# Datas e relógio
# ---------------------------------------------------------------------------------------------

def mais_dias(dia, n):
    return (dt.date.fromisoformat(dia) + dt.timedelta(days=n)).isoformat()


def dia_mes(dia):
    """AAAA-MM-DD vira DD/MM, como a edição escreve as datas no texto."""
    return dia[8:10] + "/" + dia[5:7]


def agora_de(dia, hora=HORA):
    """O valor de INFO_AGORA para publicar a edição de um dia (CONTRATO, seção 0, relógio de teste)."""
    return "%sT%sZ" % (dia, hora)


_RE_ISO = re.compile(r"(?<!\d)(20\d\d-\d\d-\d\d)(?!\d)")
_RE_DIA_MES = re.compile(r"(?<![\d/])(\d\d)/(\d\d)(?![\d/])")


def desloca(objeto, dias, ano=2026):
    """Soma dias a toda data do objeto: AAAA-MM-DD em qualquer texto e DD/MM no texto corrido.

    Serve para levar a edição de exemplo a outro dia sem deixar data incoerente. Endereços não mudam.
    """
    if dias == 0:
        return copy.deepcopy(objeto)

    def iso(m):
        try:
            return mais_dias(m.group(1), dias)
        except ValueError:
            return m.group(0)

    def curto(m):
        try:
            data = dt.date(ano, int(m.group(2)), int(m.group(1))) + dt.timedelta(days=dias)
        except ValueError:
            return m.group(0)
        return "%02d/%02d" % (data.day, data.month)

    def anda(x):
        if isinstance(x, str):
            if x.startswith(("http://", "https://")):
                return x
            return _RE_DIA_MES.sub(curto, _RE_ISO.sub(iso, x))
        if isinstance(x, list):
            return [anda(v) for v in x]
        if isinstance(x, dict):
            return {k: anda(v) for k, v in x.items()}
        return x

    return anda(objeto)


# ---------------------------------------------------------------------------------------------
# Contas mecânicas do ESQUEMA (as que não pedem julgamento)
# ---------------------------------------------------------------------------------------------

def itens(edicao):
    return list(edicao.get("principais", [])) + list(edicao.get("radar", []))


def ataques_de(item):
    return item["ataques"] if "ataques" in item else [item["ataque"]]


def indicadores_citados(dominio):
    """Ids dos indicadores citados nos critérios `precos` de um domínio, em qualquer nível."""
    citados = []
    for nivel in _lido("regua")["niveis_alerta"]:
        for preco in nivel["criterios"][dominio]["precos"]:
            if preco["indicador"] not in citados:
                citados.append(preco["indicador"])
    return citados


def sem_preco_de(indicadores, dominio):
    """ESQUEMA, regra R13f: na ordem do catálogo, os indicadores de preço do domínio que faltam,
    estão sem valor, defasados ou sem a variação de 7 dias."""
    por_id = {i["id"]: i for i in indicadores}
    citados = indicadores_citados(dominio)
    falta = []
    for chave in catalogo():
        if chave not in citados:
            continue
        ind = por_id.get(chave)
        if ind is None or ind["valor"] is None or ind["defasado"] or ind["variacao_7d_pct"] is None:
            falta.append(chave)
    return falta


def placar_do_dia_de(edicao, frases=None):
    """ESQUEMA, regra R12 e seção 6: saldo, narrativa e a ordem (maior saldo; empate, ordem da régua)."""
    frases = dict(frases or {})
    for linha in edicao.get("placar_do_dia", []):
        frases.setdefault(linha["partido"], linha["frase"])
    saldo, narrativa = {}, {}
    for item in itens(edicao):
        for linha in item["placar"]:
            sinal = 1 if linha["efeito"] == "ganha" else -1
            saldo.setdefault(linha["partido"], 0)
            narrativa.setdefault(linha["partido"], 0)
            if linha["evidencia"] == "narrativa":
                narrativa[linha["partido"]] += sinal
            else:
                saldo[linha["partido"]] += sinal * linha["forca"]
    ordem = partidos()
    return [{"partido": p, "saldo": saldo[p], "narrativa": narrativa[p],
             "frase": frases.get(p, "Texto fictício. O dia deste partido em uma frase.")}
            for p in sorted(saldo, key=lambda p: (-saldo[p], ordem.index(p)))]


def veiculos_consultados_de(edicao):
    return len({f["veiculo"] for item in itens(edicao) for f in item["fontes"]} - {"outro"})


def compara(hoje, antes):
    """ESQUEMA, regra R14: a tendência compara o nível de hoje com o da edição anterior."""
    if antes is None or hoje == antes:
        return "estavel"
    return "subindo" if hoje > antes else "descendo"


def acerta(edicao):
    """Refaz os campos que só dependem do resto da edição: placar do dia, contagem de veículos,
    sem_preco e o nível geral. Não mexe em nível de domínio, tendência nem desde."""
    edicao["placar_do_dia"] = placar_do_dia_de(edicao)
    edicao["bastidores"]["veiculos_consultados"] = veiculos_consultados_de(edicao)
    for dominio in edicao["alerta"]["dominios"]:
        dominio["sem_preco"] = sem_preco_de(edicao["indicadores"], dominio["id"])
    edicao["alerta"]["nivel"] = max(d["nivel"] for d in edicao["alerta"]["dominios"])
    return edicao


def dominio_de(edicao, ident):
    for dominio in edicao["alerta"]["dominios"]:
        if dominio["id"] == ident:
            return dominio
    raise KeyError(ident)


def indicador_de(edicao, ident):
    for indicador in edicao["indicadores"]:
        if indicador["id"] == ident:
            return indicador
    raise KeyError(ident)


def ordena(objeto, tipo):
    """Devolve o objeto com as chaves na ordem da tabela do ESQUEMA."""
    return {k: objeto[k] for k in ORDEM[tipo] if k in objeto}


def chaves_fora_de_ordem(edicao):
    """Lista os caminhos da edição cujas chaves não seguem a ordem das tabelas do ESQUEMA."""
    ruins = []

    def confere(objeto, tipo, caminho):
        if not isinstance(objeto, dict):
            ruins.append("%s: não é objeto" % caminho)
            return
        presentes = [k for k in objeto if k in ORDEM[tipo]]
        if list(objeto) != [k for k in ORDEM[tipo] if k in objeto] or len(presentes) != len(objeto):
            ruins.append("%s: %s" % (caminho, list(objeto)))

    def item(obj, tipo, caminho):
        confere(obj, tipo, caminho)
        for i, a in enumerate(ataques_de(obj) if ("ataques" in obj or "ataque" in obj) else []):
            confere(a, "ataque", "%s.ataque[%d]" % (caminho, i))
        if "eixo" in obj:
            confere(obj["eixo"], "eixo", caminho + ".eixo")
        for i, p in enumerate(obj.get("placar", [])):
            confere(p, "placar", "%s.placar[%d]" % (caminho, i))
        for i, v in enumerate(obj.get("vetores", [])):
            confere(v, "vetor", "%s.vetores[%d]" % (caminho, i))
        for i, f in enumerate(obj.get("fontes", [])):
            confere(f, "fonte", "%s.fontes[%d]" % (caminho, i))

    confere(edicao, "raiz", "raiz")
    alerta = edicao.get("alerta", {})
    confere(alerta, "alerta", "alerta")
    for i, d in enumerate(alerta.get("dominios", [])):
        confere(d, "dominio", "alerta.dominios[%d]" % i)
        for j, g in enumerate(d.get("gatilhos", [])):
            confere(g, "gatilho", "alerta.dominios[%d].gatilhos[%d]" % (i, j))
    for i, ind in enumerate(edicao.get("indicadores", [])):
        confere(ind, "indicador", "indicadores[%d]" % i)
        confere(ind.get("fonte"), "fonte_indicador", "indicadores[%d].fonte" % i)
    for i, p in enumerate(edicao.get("principais", [])):
        item(p, "principal", "principais[%d]" % i)
    for i, r in enumerate(edicao.get("radar", [])):
        item(r, "radar", "radar[%d]" % i)
    for i, p in enumerate(edicao.get("placar_do_dia", [])):
        confere(p, "placar_do_dia", "placar_do_dia[%d]" % i)
    for i, n in enumerate(edicao.get("novos_players", [])):
        confere(n, "novo_player", "novos_players[%d]" % i)
    for i, er in enumerate(edicao.get("errata", [])):
        confere(er, "errata", "errata[%d]" % i)
    for i, rp in enumerate(edicao.get("respostas", [])):
        confere(rp, "resposta", "respostas[%d]" % i)
    bastidores = edicao.get("bastidores", {})
    confere(bastidores, "bastidores", "bastidores")
    for i, c in enumerate(bastidores.get("candidatos", [])):
        confere(c, "candidato", "bastidores.candidatos[%d]" % i)
    return ruins


def difere(a, b, caminho=""):
    """Lista os caminhos em que dois objetos JSON diferem. Serve para a mensagem de falha dizer onde."""
    if isinstance(a, dict) and isinstance(b, dict):
        achados = []
        for chave in list(a) + [k for k in b if k not in a]:
            onde = "%s.%s" % (caminho, chave) if caminho else chave
            if chave not in a:
                achados.append("%s: só no segundo" % onde)
            elif chave not in b:
                achados.append("%s: só no primeiro" % onde)
            else:
                achados += difere(a[chave], b[chave], onde)
        return achados
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return ["%s: %d itens contra %d" % (caminho, len(a), len(b))]
        achados = []
        for i, (x, y) in enumerate(zip(a, b)):
            achados += difere(x, y, "%s[%d]" % (caminho, i))
        return achados
    if isinstance(a, bool) or isinstance(b, bool):
        iguais = a is b                            # true não é 1, false não é 0
    else:
        iguais = a == b
    return [] if iguais else ["%s: %r contra %r" % (caminho, a, b)]


def sem_marca_desligada(objeto):
    """Cópia da edição sem `conflito_de_interesse: false`. O ESQUEMA não diz se o item sem conflito
    sai sem o campo ou com `false`: para comparar duas edições, as duas formas valem o mesmo."""
    copia = copy.deepcopy(objeto)
    for item in itens(copia):
        if item.get("conflito_de_interesse") is False:
            del item["conflito_de_interesse"]
    return copia


# ---------------------------------------------------------------------------------------------
# Edições válidas, feitas a partir do exemplo
# ---------------------------------------------------------------------------------------------

_RE_URL_DO_EXEMPLO = re.compile(r"^https://exemplo\.invalid/([a-z0-9_]+)/(.+)$")
ALVO_FORA_DA_REGUA = "República de Exemplo (fictícia)"
NIVEIS_DO_EXEMPLO = {"energia": 3, "alimentos": 1, "cambio": 1, "suprimentos": 2, "conflito": 3}


def endereco_de_teste(url):
    """Troca o endereço fictício do exemplo por um que fecha com a regra T4: no site do veículo.

    `https://exemplo.invalid/nyt/terminal-atacado` vira `https://nytimes.com/exemplo/terminal-atacado`
    (o primeiro `sites` do veículo, no mapa congelado). O caminho continua fictício. Endereço que
    não é de veículo do mapa fica como está.
    """
    m = _RE_URL_DO_EXEMPLO.match(url)
    if not m or m.group(1) not in veiculos():
        return url
    return "https://%s/exemplo/%s" % (veiculos()[m.group(1)]["sites"][0], m.group(2))


def _troca_enderecos(objeto):
    if isinstance(objeto, str):
        return endereco_de_teste(objeto) if objeto.startswith("https://exemplo.invalid/") else objeto
    if isinstance(objeto, list):
        return [_troca_enderecos(v) for v in objeto]
    if isinstance(objeto, dict):
        return {k: _troca_enderecos(v) for k, v in objeto.items()}
    return objeto


def _tira_marca(texto):
    return texto[len("[EXEMPLO] "):] if texto.startswith("[EXEMPLO] ") else texto


def monta_edicao(dia=DIA, anterior=None, alerta=None, rica=False, hora=HORA):
    """Uma edição completa e válida para o dia pedido, feita a partir do exemplo.

    Sai sem `exemplo`, sem `[EXEMPLO]` nos títulos, com as datas levadas ao dia, com os endereços no
    site de cada veículo (regra T4) e sem o que depende de outras edições (`continuacao_de`, `errata`
    e `respostas` ficam vazios: cada teste acrescenta o que quer conferir).

    rica=True  mantém o player novo, os 2 vetores, o indicador de preço que dispara gatilho e os
               gatilhos do exemplo. É a edição "do dia" dos testes do publica.py.
    rica=False tira o player novo e os vetores, acalma os indicadores e sai sem gatilho: serve de
               edição de arquivo, para montar históricos.

    alerta     {dominio: {"nivel": N, "gatilhos": [...]}}. Domínio não citado fica em 1, sem gatilho.
               O nível é o que o teste declara, lido da regra R13 à mão: esta função não o calcula.
    anterior   a edição anterior (ESQUEMA, seção 0). Dela saem `desde` e as tendências (regra R14).
    """
    e = desloca(exemplo(), (dt.date.fromisoformat(dia) - dt.date.fromisoformat(DIA_DO_EXEMPLO)).days)
    e = _troca_enderecos(e)
    del e["exemplo"]
    e["gerada_em"] = agora_de(dia, hora)
    e["resumo"] = _tira_marca(e["resumo"])
    e["errata"], e["respostas"] = [], []
    for item in itens(e):
        item["titulo"] = _tira_marca(item["titulo"])
        item.pop("continuacao_de", None)
        for fonte in item["fontes"]:
            fonte["titulo"] = _tira_marca(fonte["titulo"])
    if not rica:
        e["novos_players"] = []
        for item in itens(e):
            item["vetores"] = []
            for ataque in ataques_de(item):
                if ataque["alvo"] == "republica_exemplo":
                    ataque["alvo"] = "outro"
                    ataque["alvo_nome"] = ALVO_FORA_DA_REGUA
            if "ataques" in item:
                item["ataques"] = [ordena(a, "ataque") for a in item["ataques"]]
            else:
                item["ataque"] = ordena(item["ataque"], "ataque")
        indicador_de(e, "brent")["variacao_7d_pct"] = 1.2      # abaixo de 5%: sem gatilho de preço
    for dominio in e["alerta"]["dominios"]:
        if alerta is None and rica:
            nivel, gatilhos = NIVEIS_DO_EXEMPLO[dominio["id"]], dominio["gatilhos"]
        else:
            pedido = (alerta or {}).get(dominio["id"], {})
            nivel, gatilhos = pedido.get("nivel", 1), copy.deepcopy(pedido.get("gatilhos", []))
        antes = dominio_de(anterior, dominio["id"]) if anterior else None
        dominio["nivel"] = nivel
        dominio["tendencia"] = compara(nivel, antes["nivel"] if antes else None)
        dominio["desde"] = antes["desde"] if antes and antes["nivel"] == nivel else dia
        dominio["gatilhos"] = gatilhos
    acerta(e)
    e["alerta"]["tendencia"] = compara(e["alerta"]["nivel"], anterior["alerta"]["nivel"] if anterior else None)
    return e


def gatilho(criterio, ref, texto=None, **marcas):
    """Um gatilho de evento, no formato do ESQUEMA, seção 2."""
    g = {"criterio": criterio, "ref": ref,
         "texto": texto or "Texto fictício. Fato inventado que cumpre o critério %s." % criterio}
    g.update(marcas)
    return ordena(g, "gatilho")


def edicao_falha(dia, motivo, anterior=None, indicadores=None, hora=HORA):
    """A edição de falha, campo a campo, como o CONTRATO, seção 4.3, a descreve."""
    indicadores = copy.deepcopy(indicadores or [])
    fixo = "Sem leitura hoje."
    if anterior:
        fixo += " Nível repetido de %s." % dia_mes(anterior["data"])
    doms = []
    for ident in dominios():
        antes = dominio_de(anterior, ident) if anterior else None
        doms.append({"id": ident, "nivel": antes["nivel"] if antes else 1, "tendencia": "estavel",
                     "desde": antes["desde"] if antes else dia,
                     "sem_preco": sem_preco_de(indicadores, ident), "gatilhos": [],
                     "leitura": fixo, "vigiar": fixo})
    return {
        "versao": 1, "data": dia, "gerada_em": agora_de(dia, hora), "estado": "falha",
        "resumo": "Sem edição hoje. " + motivo,
        "alerta": {"nivel": max(d["nivel"] for d in doms), "tendencia": "estavel", "motivo": motivo,
                   "dominios": doms},
        "indicadores": indicadores, "principais": [], "radar": [], "placar_do_dia": [],
        "novos_players": [], "errata": [], "respostas": [],
        "bastidores": {"modo": "feeds", "veiculos_consultados": 0, "feeds_ok": 0, "feeds_falhos": 0,
                       "paginas_lidas": 0, "buscas": 0, "minutos": 0, "injecoes_ignoradas": 0,
                       "candidatos": [], "veiculos_sugeridos": [], "limites": motivo},
    }


def rascunho_de(edicao):
    """O rascunho que daria esta edição: só os campos de origem `agente` (ESQUEMA, seção 0, e o
    modelo.txt do CONTRATO, seção 4.1). Sai sem versao, gerada_em, lado, níveis, tendências, desde,
    sem_preco, gatilho de preço, indicadores, saldo, narrativa, contadores e marca de conflito."""
    ids_de_indicador = set(catalogo())

    def item(obj):
        novo = copy.deepcopy(obj)
        novo.pop("conflito_de_interesse", None)
        for ataque in ataques_de(novo):
            ataque.pop("lado", None)
        return novo

    b = edicao["bastidores"]
    return {
        "data": edicao["data"],
        "estado": edicao["estado"],
        "resumo": edicao["resumo"],
        "alerta": {
            "motivo": edicao["alerta"]["motivo"],
            "dominios": [{"id": d["id"],
                          "gatilhos": [copy.deepcopy(g) for g in d["gatilhos"] if g["ref"] not in ids_de_indicador],
                          "leitura": d["leitura"], "vigiar": d["vigiar"]}
                         for d in edicao["alerta"]["dominios"]],
        },
        "principais": [item(p) for p in edicao["principais"]],
        "radar": [item(r) for r in edicao["radar"]],
        "placar_do_dia": [{"partido": p["partido"], "frase": p["frase"]} for p in edicao["placar_do_dia"]],
        "novos_players": copy.deepcopy(edicao["novos_players"]),
        "errata": copy.deepcopy(edicao["errata"]),
        "respostas": copy.deepcopy(edicao["respostas"]),
        "bastidores": {k: copy.deepcopy(b[k]) for k in ("modo", "paginas_lidas", "buscas", "minutos",
                                                        "injecoes_ignoradas", "candidatos",
                                                        "veiculos_sugeridos", "limites")},
    }


def todas_as_urls(objeto):
    """Toda URL de um rascunho, em qualquer campo (regra T1: "Toda URL do rascunho")."""
    achadas = []

    def anda(x):
        if isinstance(x, str):
            if x.startswith(("http://", "https://")) and x not in achadas:
                achadas.append(x)
        elif isinstance(x, list):
            for v in x:
                anda(v)
        elif isinstance(x, dict):
            for v in x.values():
                anda(v)

    anda(objeto)
    return achadas


def indice_de(edicoes):
    """edicoes/indice.json, pela tabela do ESQUEMA, seção 11."""
    ordem_dominios = dominios()
    entradas = []
    for e in sorted(edicoes, key=lambda e: e["data"], reverse=True):
        eixos = {}
        for item in itens(e):
            if "eixo" in item:
                conta = eixos.setdefault(item["eixo"]["tema"], {"azul": 0, "vermelho": 0})
                conta[item["eixo"]["sentido"]] += 1
        niveis = {d["id"]: d["nivel"] for d in e["alerta"]["dominios"]}
        entradas.append({
            "data": e["data"],
            "arquivo": "edicoes/%s.json" % e["data"],
            "texto": "edicoes/%s.md" % e["data"],
            "estado": e["estado"],
            "nivel": e["alerta"]["nivel"],
            "tendencia": e["alerta"]["tendencia"],
            "niveis": {d: niveis[d] for d in ordem_dominios},
            "saldos": {p["partido"]: p["saldo"] for p in e["placar_do_dia"]},
            "eixos": eixos,
            "indicadores": {i["id"]: i["valor"] for i in e["indicadores"]
                            if i["valor"] is not None and not i["defasado"]},
            "resumo": e["resumo"],
            "gerada_em": e["gerada_em"],
            "exemplo": e.get("exemplo") is True,
            "corrigida_em": sorted(o["data"] for o in edicoes
                                   if o["data"] > e["data"] and any(x["edicao"] == e["data"] for x in o["errata"])),
        })
    return {"versao": 1, "atualizado_em": max(e["gerada_em"] for e in edicoes), "edicoes": entradas}


def vetores_registrados(edicao):
    """As entradas que a edição acrescenta a dados/vetores.json: um registro por vetor e uma
    anulação por `errata[].anula_vetor` (ESQUEMA, seção 12; CONTRATO, seção 4.2, passo 7)."""
    partido_de = {p["id"]: p["partido"] for p in _lido("players")["players"]}
    dia = edicao["data"]
    entradas = []
    for item in itens(edicao):
        for vetor in item["vetores"]:
            entrada = {"id": "%s_%s_%s" % (dia, item["id"], vetor["player"]), "data": dia, "item": item["id"],
                       "player": vetor["player"], "de": partido_de[vetor["player"]], "para": vetor["para"],
                       "forca": vetor["forca"], "tema": vetor["tema"], "porque": vetor["porque"],
                       "url": vetor["url"]}
            if item.get("conflito_de_interesse") is True:
                entrada["conflito_de_interesse"] = True
            entradas.append(entrada)
    anuladas = [er for er in edicao["errata"] if "anula_vetor" in er]
    for numero, errata in enumerate(anuladas, 1):
        entradas.append({"id": "%s_anula_%d" % (dia, numero), "data": dia, "anula": errata["anula_vetor"],
                         "porque": errata["correcao"], "url": errata["url"]})
    return entradas


def players_registrados(edicao):
    """O que a edição acrescenta a dados/players.json: o item de `novos_players`, mais `origem` e
    `incluido_em` (ESQUEMA, seção 13)."""
    novos = []
    for novo in edicao["novos_players"]:
        registro = copy.deepcopy(novo)
        registro["origem"] = "rotina"
        registro["incluido_em"] = edicao["data"]
        novos.append(registro)
    return novos


def registra(raiz, edicao):
    """Acrescenta a dados/vetores.json e a dados/players.json o que a edição registra, como o
    publica.py faria. Deixa a raiz montada à mão coerente com as edições que ela tem."""
    def nos_vetores(arquivo):
        arquivo["vetores"] += vetores_registrados(edicao)

    def nos_players(arquivo):
        arquivo["players"] += players_registrados(edicao)
        if edicao["novos_players"]:
            arquivo["atualizado_em"] = edicao["data"]

    muda_json(os.path.join(raiz, "dados", "vetores.json"), nos_vetores)
    muda_json(os.path.join(raiz, "dados", "players.json"), nos_players)


def _xml(texto):
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def feed_de(edicoes, base="./"):
    """Um feed.xml mínimo, feito à mão pelas exigências do CONTRATO, seção 4.5. Serve só para a raiz
    montada à mão ter um feed bem formado: não é o texto que o publica.py grava."""
    novas = sorted((e for e in edicoes if e.get("exemplo") is not True), key=lambda e: e["data"], reverse=True)[:30]
    linhas = ['<?xml version="1.0" encoding="utf-8"?>', '<feed xmlns="%s">' % ATOM,
              "  <title>INFOCENARIUM · monitor geopolítico e de IA</title>", "  <id>%s</id>" % _xml(base),
              "  <updated>%s</updated>" % max([e["gerada_em"] for e in edicoes] or ["2026-01-01T00:00:00Z"])]
    for e in novas:
        d = e["data"]
        data_br = "%s/%s/%s" % (d[8:10], d[5:7], d[0:4])
        if e["estado"] == "falha":
            titulo = "INFOCENARIUM %s · sem edição" % data_br
        else:
            titulo = "INFOCENARIUM %s · nível %d %s" % (data_br, e["alerta"]["nivel"], rotulo_do_nivel(e["alerta"]["nivel"]))
        endereco = "%s#/edicao/%s" % (base, d)
        corpo = "\n".join("%s\n%s" % (p["titulo"], p["fato"]) for p in e["principais"])
        linhas += ["  <entry>", "    <title>%s</title>" % _xml(titulo), "    <id>%s</id>" % _xml(endereco),
                   '    <link href="%s"/>' % _xml(endereco), "    <updated>%s</updated>" % e["gerada_em"],
                   "    <summary>%s</summary>" % _xml(e["resumo"]),
                   '    <content type="text">%s</content>' % _xml(corpo), "  </entry>"]
    linhas.append("</feed>")
    return "\n".join(linhas) + "\n"


# ---------------------------------------------------------------------------------------------
# Ajudantes dos cenários
# ---------------------------------------------------------------------------------------------

F = "Texto fictício. "
ONTEM, ANTEONTEM, TRES_ANTES = mais_dias(DIA, -1), mais_dias(DIA, -2), mais_dias(DIA, -3)

VOCABULARIOS = [
    "abacate bicicleta cadeira dromedário escada farol girassol hortelã ilha jangada kiwi lanterna",
    "montanha navio orquídea pêssego quartzo riacho sabiá tambor urso violino xadrez zabumba",
    "âncora bússola cometa dúzia esquilo feira gaveta harpa íris jardim lagoa moinho",
    "nuvem oliveira pandeiro queijo relógio sino trilho universo vela zíper açude baleia",
]


def poe(objeto, tipo, **campos):
    """Põe os campos e deixa as chaves na ordem da tabela do ESQUEMA, para o defeito ser só o plantado."""
    objeto.update(campos)
    ordenado = ordena(objeto, tipo)
    objeto.clear()
    objeto.update(ordenado)
    return objeto


def troca_titulos(edicao, numero):
    """Dá a cada item um título sem palavra em comum com os títulos do exemplo nem com os de outro
    vocabulário. Serve para o aviso H3 de título quase igual não aparecer por acaso."""
    palavras = VOCABULARIOS[numero].split()
    for n, item in enumerate(itens(edicao)):
        escolhidas = [palavras[(n + k) % len(palavras)] for k in range(4)]
        item["titulo"] = " ".join(escolhidas).capitalize()
    return edicao


def calmaria(dominio, criterio, ref="r4"):
    """Três edições: a de 3 dias atrás leva o domínio ao nível 2 por evento; as duas seguintes não
    têm gatilho. Na contagem da regra R13, a edição de hoje encontra S = 2."""
    d3 = monta_edicao(TRES_ANTES, alerta={dominio: {"nivel": 2, "gatilhos": [gatilho(criterio, ref)]}})
    d2 = monta_edicao(ANTEONTEM, anterior=d3, alerta={dominio: {"nivel": 2}})
    d1 = monta_edicao(ONTEM, anterior=d2, alerta={dominio: {"nivel": 2}})
    return d3, d2, d1


def cega_energia(edicao):
    """Tira a base de 7 dias do Brent: a edição fica cega para energia (ESQUEMA, seção 0)."""
    indicador_de(edicao, "brent")["variacao_7d_pct"] = None
    return acerta(edicao)


# ---------------------------------------------------------------------------------------------
# Raiz temporária e git
# ---------------------------------------------------------------------------------------------

def monta_raiz(pasta):
    """Uma raiz de repositório só com `dados/`, copiada da cópia congelada. Não cria `edicoes/`."""
    os.makedirs(os.path.join(pasta, "dados"), exist_ok=True)
    for nome in ARQUIVOS_DE_DADOS:
        shutil.copyfile(os.path.join(DADOS_CONGELADOS, nome), os.path.join(pasta, "dados", nome))
    return pasta


def caminho_da_edicao(raiz, dia, extensao="json"):
    return os.path.join(raiz, "edicoes", "%s.%s" % (dia, extensao))


def grava_edicoes(raiz, edicoes, derivados=True):
    """Grava as edições em `edicoes/`. Com derivados=True, grava também o que acompanha uma edição
    publicada: um `.md` para cada uma, o `indice.json` (ESQUEMA, seção 11) e um `feed.xml` bem
    formado. O `.md` é um texto de teste, e não o que o publica.py escreveria."""
    for e in edicoes:
        grava_json(caminho_da_edicao(raiz, e["data"]), e)
    if derivados and edicoes:
        for e in edicoes:
            grava_texto(caminho_da_edicao(raiz, e["data"], "md"),
                        "# INFOCENARIUM · %s\n\nTexto de teste, gravado pelo apoio dos testes de contrato.\n" % e["data"])
        grava_json(os.path.join(raiz, "edicoes", "indice.json"), indice_de(edicoes))
        grava_texto(os.path.join(raiz, "feed.xml"), feed_de(edicoes))


def muda_json(caminho, muda):
    """Lê um JSON, aplica a função e grava de novo no formato do CONTRATO. Devolve o objeto."""
    objeto = le_json(caminho)
    muda(objeto)
    grava_json(caminho, objeto)
    return objeto


def _ambiente_git():
    ambiente = dict(os.environ)
    ambiente.update({
        # o git dos testes não lê a configuração de quem roda nem a da máquina
        "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
        "GIT_AUTHOR_DATE": "2026-11-20T12:00:00Z", "GIT_COMMITTER_DATE": "2026-11-20T12:00:00Z",
    })
    return ambiente


def git(raiz, *argumentos, confere=True):
    """Roda o git dentro da raiz temporária. Devolve a saída padrão, sem a quebra de linha do fim."""
    feito = subprocess.run(["git"] + list(argumentos), cwd=raiz, env=_ambiente_git(), stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    saida = feito.stdout.decode("utf-8", "replace")
    if confere and feito.returncode != 0:
        raise RuntimeError("git %s falhou (%d): %s" % (" ".join(argumentos), feito.returncode,
                                                       feito.stderr.decode("utf-8", "replace")))
    return saida.rstrip("\n")


def inicia_git(raiz):
    """Faz da raiz temporária um repositório git, com identidade de teste local àquele repositório."""
    git(raiz, "-c", "init.defaultBranch=main", "init", "-q")
    git(raiz, "config", "user.name", "Teste de contrato")
    git(raiz, "config", "user.email", "teste@contrato.invalid")
    git(raiz, "config", "commit.gpgsign", "false")
    git(raiz, "config", "core.autocrlf", "false")
    return raiz


def commita(raiz, mensagem="commit de teste", origin=False):
    """Põe tudo no commit e devolve o identificador. Com origin=True, marca também `origin/main`
    nesse commit (sem repositório remoto: só a referência, que é o que `--base origin/main` lê)."""
    git(raiz, "add", "-A")
    git(raiz, "commit", "-q", "--allow-empty", "-m", mensagem)
    sha = git(raiz, "rev-parse", "HEAD")
    if origin:
        git(raiz, "update-ref", "refs/remotes/origin/main", sha)
    return sha


# ---------------------------------------------------------------------------------------------
# Fotografia da árvore de arquivos
# ---------------------------------------------------------------------------------------------

def fotografa(pasta, rigor=False, fora=(".git",)):
    """Retrato de uma pasta: {caminho relativo: marca}. Pasta vira ("pasta",); arquivo vira
    ("arquivo", sha256). Com rigor=True entram também a hora de modificação e o número do arquivo
    no disco: assim regravar os mesmos bytes também aparece. A pasta `.git` fica de fora, porque o
    próprio git mexe nela ao responder uma consulta."""
    retrato = {}
    if not os.path.isdir(pasta):
        return retrato
    for atual, subpastas, nomes in os.walk(pasta):
        subpastas[:] = sorted(s for s in subpastas if os.path.relpath(os.path.join(atual, s), pasta) not in fora)
        for sub in subpastas:
            retrato[os.path.relpath(os.path.join(atual, sub), pasta).replace(os.sep, "/") + "/"] = ("pasta",)
        for nome in sorted(nomes):
            caminho = os.path.join(atual, nome)
            marca = ("arquivo", hashlib.sha256(le_bytes(caminho)).hexdigest())
            if rigor:
                info = os.stat(caminho)
                marca += (info.st_mtime_ns, info.st_ino)
            retrato[os.path.relpath(caminho, pasta).replace(os.sep, "/")] = marca
    return retrato


def diferenca(antes, depois):
    """Compara dois retratos. Devolve (criados, mudados, sumidos), cada um em ordem."""
    criados = sorted(k for k in depois if k not in antes)
    sumidos = sorted(k for k in antes if k not in depois)
    mudados = sorted(k for k in antes if k in depois and antes[k] != depois[k])
    return criados, mudados, sumidos


# ---------------------------------------------------------------------------------------------
# Chamada das ferramentas
# ---------------------------------------------------------------------------------------------

class Resultado:
    """O que uma chamada devolveu: saída padrão, saída de erro, código e a linha de comando."""

    def __init__(self, comando, codigo, saida, erro):
        self.comando = comando
        self.codigo = codigo
        self.saida = saida
        self.erro = erro

    @property
    def linhas(self):
        return self.saida.rstrip("\n").split("\n") if self.saida.strip("\n") else []

    @property
    def ultima(self):
        """A última linha da saída padrão: o veredito (CONTRATO, seção 0, "Saída")."""
        return self.linhas[-1] if self.linhas else ""

    @property
    def veredito(self):
        """A primeira palavra da última linha: OK, PARCIAL ou FALHA."""
        return self.ultima.split(" ", 1)[0] if self.ultima else ""

    def _marcadas(self, marca):
        achadas = []
        for linha in self.linhas:
            partes = linha.split(" ", 2)
            if partes[0] == marca and len(partes) >= 2:
                achadas.append((partes[1].rstrip(":"), linha))
        return achadas

    @property
    def erros(self):
        """As linhas `ERRO REGRA …`, como pares (regra, linha inteira)."""
        return self._marcadas("ERRO")

    @property
    def avisos(self):
        return self._marcadas("AVISO")

    @property
    def regras(self):
        return {regra for regra, _ in self.erros}

    @property
    def regras_de_aviso(self):
        return {regra for regra, _ in self.avisos}

    def linhas_da_regra(self, *regras, avisos=False):
        return [linha for regra, linha in (self.avisos if avisos else self.erros) if regra in regras]

    def json(self):
        return json.loads(self.saida)

    def relato(self):
        """Texto para a mensagem de falha do teste."""
        return ("\n--- comando: %s\n--- código de saída: %s\n--- saída padrão:\n%s\n--- saída de erro:\n%s"
                % (" ".join(self.comando), self.codigo, self.saida.rstrip("\n"), self.erro.rstrip("\n")))


class FerramentaAusente(AssertionError):
    """A ferramenta ainda não existe em ferramentas/. O teste de contrato não pode passar sem ela."""


def copia_ferramentas(raiz):
    """Copia a pasta ferramentas/ para dentro da raiz temporária, sem abrir os arquivos. Serve para
    chamar a ferramenta como o workflow chama: de dentro do repositório, sem `--raiz`."""
    destino = os.path.join(raiz, "ferramentas")
    shutil.copytree(FERRAMENTAS, destino, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return destino


def roda(ferramenta, argumentos=(), raiz=None, trabalho=None, agora=None, cwd=None, ambiente=None,
         sem=(), na_raiz=False):
    """Chama `python3 ferramentas/FERRAMENTA.py`, como a rotina e os workflows chamam.

    raiz      vira `--raiz`. Em publica.py, entra depois do subcomando, como as outras opções na
              sinopse do CONTRATO, seção 4.
    trabalho  vira `--trabalho` (o valida.py não tem essa opção).
    agora     o valor de INFO_AGORA; None deixa a variável de fora.
    cwd       a pasta de onde se chama; sem valor, a raiz.
    ambiente  variáveis a mais; `sem` lista variáveis a tirar.
    na_raiz   chama a cópia que está em RAIZ/ferramentas (ver copia_ferramentas), pelo caminho
              relativo e sem `--raiz`: vale o padrão, "a pasta acima de ferramentas/".

    Roda sempre com PYTHONDONTWRITEBYTECODE=1, como os workflows (CONTRATO, seção 5).
    """
    if na_raiz:
        caminho = os.path.join(raiz, "ferramentas", ferramenta + ".py")
    else:
        caminho = os.path.join(FERRAMENTAS, ferramenta + ".py")
    if not os.path.isfile(caminho):
        raise FerramentaAusente("não existe ferramentas/%s.py em %s" % (ferramenta, os.path.dirname(caminho)))
    argumentos = [str(a) for a in argumentos]
    comuns = []
    if na_raiz:
        caminho = os.path.join("ferramentas", ferramenta + ".py")
        cwd = raiz
    elif raiz is not None:
        comuns += ["--raiz", raiz]
    if trabalho is not None:
        comuns += ["--trabalho", trabalho]
    if ferramenta == "publica" and argumentos and not argumentos[0].startswith("-"):
        argumentos = argumentos[:1] + comuns + argumentos[1:]
    else:
        argumentos = comuns + argumentos
    comando = [sys.executable, caminho] + argumentos
    env = dict(os.environ)
    env.pop("INFO_AGORA", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # o git que a ferramenta chamar não lê a configuração de quem roda, nem sobe para fora da raiz
    env.update({"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"})
    if raiz is not None:
        env["GIT_CEILING_DIRECTORIES"] = os.path.dirname(os.path.abspath(raiz))
    if agora is not None:
        env["INFO_AGORA"] = agora
    env.update(ambiente or {})
    for nome in sem:
        env.pop(nome, None)
    try:
        feito = subprocess.run(comando, cwd=cwd or raiz or None, env=env, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=TEMPO_MAXIMO)
    except subprocess.TimeoutExpired as estouro:
        return Resultado(comando, None, (estouro.stdout or b"").decode("utf-8", "replace"),
                         "passou de %d segundos" % TEMPO_MAXIMO)
    return Resultado(comando, feito.returncode, feito.stdout.decode("utf-8", "replace"),
                     feito.stderr.decode("utf-8", "replace"))


# ---------------------------------------------------------------------------------------------
# A pasta de trabalho
# ---------------------------------------------------------------------------------------------

def tem_feed(veiculo):
    """O veículo tem feed que o coleta.py lê (formato rss ou atom)? Sem feed, a fonte só chega por
    página aberta: é o caso das agências (ROTINA, seção 4)."""
    return any(f["formato"] in ("rss", "atom") for f in veiculos()[veiculo]["feeds"])


class Trabalho:
    """A pasta de trabalho coerente com uma edição esperada (CONTRATO, seção 0, "Pasta de trabalho").

    Recebe a edição que se espera publicada e monta: o rascunho (só os campos de origem agente),
    `contexto.json`, `coleta.json`, `indicadores.json`, `urls.txt` e `conferencia.json`.

    De onde vem cada endereço do rascunho, para fechar com as regras T1 a T5 do ESQUEMA:

    - fonte comum de veículo que tem feed: manchete em `coleta.json`, com a data do feed (T1, T3, T4);
    - fonte de veículo sem feed (as agências), fonte primária e fonte fora do mapa: página aberta, em
      `urls.txt`, com a data lida em `conferencia.json` (T1, T3); o site fecha com o mapa (T4);
    - endereço de ataque com `omite`: também em `urls.txt` (T5);
    - os outros endereços (player novo, errata, respostas): página aberta, sem data.

    O teste muda os atributos e chama grava(). Atributo em None deixa o arquivo de fora.
    """

    def __init__(self, pasta, edicao, feeds=True):
        self.pasta = pasta
        self.dia = edicao["data"]
        self.rascunho = rascunho_de(edicao)
        self.manchetes = []      # entradas de coleta.json
        self.paginas = []        # entradas de conferencia.json
        self.urls = []           # linhas de urls.txt
        self.feeds_falhos = 4
        self.sem_coleta = False
        self.sem_conferencia = False
        self.sem_urls = False
        self.indicadores = {
            "versao": 1, "dia": self.dia, "gerada_em": agora_de(self.dia, "21:03:40"),
            "indicadores": copy.deepcopy(edicao["indicadores"]),
            "gatilhos": [copy.deepcopy(g) for d in edicao["alerta"]["dominios"] for g in d["gatilhos"]
                         if g["ref"] in set(catalogo())],
            "falhas": [{"id": i["id"], "erro": "todas as fontes falharam"} for i in edicao["indicadores"]
                       if i["valor"] is None],
        }
        self.contexto = {
            "dia": self.dia, "janela_horas": 36, "edicao_do_dia": None, "anterior": None,
            "alerta_anterior": {"nivel": 1, "dominios": [
                {"id": d, "nivel": 1, "desde": self.dia, "edicoes_sem_gatilho": 0,
                 "desce_hoje_sem_gatilho": False, "origem": None} for d in dominios()]},
            "historias_recentes": [], "vigiar_vencendo": [], "candidatos": [], "vetores_recentes": [],
        }
        mapa = veiculos()
        vistos = set()
        for numero, item in enumerate(itens(edicao), 1):
            for fonte in item["fontes"]:
                if fonte["url"] in vistos:
                    continue
                vistos.add(fonte["url"])
                veiculo = fonte["veiculo"]
                if feeds and veiculo != "outro" and not fonte.get("primaria") and tem_feed(veiculo):
                    self.manchetes.append({
                        "id": "m%04d" % (len(self.manchetes) + 1), "historia": "h%02d" % numero,
                        "veiculo": veiculo, "lado": mapa[veiculo]["lado"], "fatos": mapa[veiculo]["fatos"],
                        "titulo": fonte["titulo"], "resumo": "Texto fictício. Resumo da manchete.",
                        "url": fonte["url"], "publicado_em": fonte["publicado_em"] + "T14:02:00Z",
                        "categoria": item["categoria"], "suspeito": False})
                else:
                    self.abre(fonte["url"], publicado_em=fonte["publicado_em"])
            for ataque in ataques_de(item):
                if "omite" in ataque and ataque["url"] not in self.urls:
                    self.urls.append(ataque["url"])
        for url in todas_as_urls(self.rascunho):
            if url not in vistos:
                vistos.add(url)
                self.abre(url)

    # --- consultas e mudanças -----------------------------------------------------------------

    def manchete(self, url):
        for m in self.manchetes:
            if m["url"] == url:
                return m
        raise KeyError(url)

    def pagina(self, url):
        for p in self.paginas:
            if p["url"] == url:
                return p
        raise KeyError(url)

    def abre(self, url, estado="ok", publicado_em=None):
        """Registra uma página aberta: linha em urls.txt e entrada em conferencia.json."""
        if url not in self.urls:
            self.urls.append(url)
        self.paginas = [p for p in self.paginas if p["url"] != url]
        self.paginas.append({"url": url, "estado": estado, "publicado_em": publicado_em})

    def vira_pagina(self, url, estado="ok", publicado_em=None):
        """Tira a manchete da coleta e trata o endereço como página aberta."""
        self.manchetes = [m for m in self.manchetes if m["url"] != url]
        self.abre(url, estado, publicado_em)

    def esquece(self, url):
        """Tira o endereço de tudo o que a máquina viu: coleta, urls.txt e conferencia.json."""
        self.manchetes = [m for m in self.manchetes if m["url"] != url]
        self.paginas = [p for p in self.paginas if p["url"] != url]
        self.urls = [u for u in self.urls if u != url]

    # --- os arquivos --------------------------------------------------------------------------

    def coleta(self):
        mapa = veiculos()
        com_feed = []
        for m in self.manchetes:
            if m["veiculo"] not in com_feed:
                com_feed.append(m["veiculo"])
        feeds = []
        for veiculo in com_feed:
            lidos = [f for f in mapa[veiculo]["feeds"] if f["formato"] in ("rss", "atom")] or [{"url": "https://exemplo.invalid/feed/" + veiculo}]
            feeds.append({"veiculo": veiculo, "url": lidos[0]["url"], "estado": "ok",
                          "itens": sum(1 for m in self.manchetes if m["veiculo"] == veiculo), "erro": ""})
        sobra = [v for v in sorted(mapa) if v not in com_feed and tem_feed(v)][:self.feeds_falhos]
        for veiculo in sobra:
            lidos = [f for f in mapa[veiculo]["feeds"] if f["formato"] in ("rss", "atom")]
            feeds.append({"veiculo": veiculo, "url": lidos[0]["url"], "estado": "erro", "itens": 0,
                          "erro": "tempo esgotado"})
        historias = []
        for ident in sorted({m["historia"] for m in self.manchetes}):
            dela = [m for m in self.manchetes if m["historia"] == ident]
            lados = []
            for m in dela:
                if m["lado"] not in lados:
                    lados.append(m["lado"])
            distintos = len({m["veiculo"] for m in dela})
            historias.append({"id": ident, "pontos": 3 * len(lados) + min(distintos, 3),
                              "categoria": dela[0]["categoria"], "partidos": lados, "veiculos": distintos,
                              "manchetes": [m["id"] for m in dela]})
        return {
            "versao": 1, "dia": self.dia, "gerada_em": agora_de(self.dia, "21:03:10"), "janela_horas": 36,
            "resumo": {"feeds_ok": len(com_feed), "feeds_falhos": len(sobra), "veiculos_ok": len(com_feed),
                       "manchetes": len(self.manchetes), "suspeitas": 0,
                       "partidos": {p: sum(1 for m in self.manchetes if m["lado"] == p) for p in partidos()}},
            "feeds": feeds, "manchetes": self.manchetes, "historias": historias,
        }

    def conferencia(self):
        return {"versao": 1, "gerada_em": agora_de(self.dia, "21:12:10"), "paginas": self.paginas}

    def arquivo(self, nome):
        return os.path.join(self.pasta, nome)

    def grava(self):
        """Grava a pasta inteira, apagando o que sobrou de uma gravação anterior."""
        os.makedirs(self.pasta, exist_ok=True)
        for nome in ("rascunho.json", "contexto.json", "coleta.json", "indicadores.json", "urls.txt",
                     "conferencia.json"):
            if os.path.exists(self.arquivo(nome)):
                os.remove(self.arquivo(nome))
        if self.rascunho is not None:
            grava_json(self.arquivo("rascunho.json"), self.rascunho)
        if self.contexto is not None:
            grava_json(self.arquivo("contexto.json"), self.contexto)
        if not self.sem_coleta:
            grava_json(self.arquivo("coleta.json"), self.coleta())
        if self.indicadores is not None:
            grava_json(self.arquivo("indicadores.json"), self.indicadores)
        if not self.sem_urls:
            grava_texto(self.arquivo("urls.txt"), "# páginas abertas nesta execução\n" + "".join(u + "\n" for u in self.urls))
        if not self.sem_conferencia:
            grava_json(self.arquivo("conferencia.json"), self.conferencia())
        return self


# ---------------------------------------------------------------------------------------------
# A classe-base dos testes
# ---------------------------------------------------------------------------------------------

class Caso(unittest.TestCase):
    """Base dos testes de contrato: pasta temporária por teste e conferências de veredito."""

    maxDiff = 4000

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="info-contrato-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self._pastas = 0

    def pasta(self, nome="pasta"):
        """Uma pasta nova e vazia, dentro da pasta temporária do teste."""
        self._pastas += 1
        caminho = os.path.join(self.tmp, "%s%d" % (nome, self._pastas))
        os.makedirs(caminho)
        return caminho

    def nova_raiz(self, edicoes=(), derivados=True, com_git=False):
        """Raiz temporária com os dados congelados e, se pedidas, edições já gravadas (com os
        vetores e os players novos delas nos registros de `dados/`)."""
        raiz = monta_raiz(self.pasta("raiz"))
        grava_edicoes(raiz, list(edicoes), derivados=derivados)
        for edicao in sorted(edicoes, key=lambda e: e["data"]):
            if any(item["vetores"] for item in itens(edicao)) or edicao["novos_players"] or \
                    any("anula_vetor" in er for er in edicao["errata"]):
                registra(raiz, edicao)
        if com_git:
            inicia_git(raiz)
            commita(raiz, "base", origin=True)
        return raiz

    def arquivo_solto(self, edicao, nome="caso.json"):
        """Grava uma edição fora de `edicoes/`: é conferida sozinha, sem histórico (regra H1)."""
        caminho = os.path.join(self.pasta("solta"), nome)
        grava_json(caminho, edicao)
        return caminho

    # --- chamadas -----------------------------------------------------------------------------

    def valida(self, *argumentos, raiz=None, agora=agora_de(DIA), **mais):
        return roda("valida", argumentos, raiz=raiz, agora=agora, **mais)

    def publica(self, *argumentos, raiz=None, trabalho=None, agora=agora_de(DIA), **mais):
        return roda("publica", argumentos, raiz=raiz, trabalho=trabalho, agora=agora, **mais)

    # --- conferências -------------------------------------------------------------------------

    def passou(self, res, mensagem=""):
        """Código 0 e veredito OK (CONTRATO, seção 0: "Códigos de saída" e "Saída")."""
        self.assertEqual(res.codigo, 0, "esperava código 0. %s%s" % (mensagem, res.relato()))
        self.assertEqual(res.veredito, "OK", "a última linha deveria começar com OK. %s%s" % (mensagem, res.relato()))
        self.assertEqual(res.erros, [], "não deveria haver linha ERRO. %s%s" % (mensagem, res.relato()))

    def falhou(self, res, mensagem=""):
        """Código 1 e veredito FALHA."""
        self.assertEqual(res.codigo, 1, "esperava código 1. %s%s" % (mensagem, res.relato()))
        self.assertEqual(res.veredito, "FALHA",
                         "a última linha deveria começar com FALHA. %s%s" % (mensagem, res.relato()))

    def erro_de_uso(self, res):
        """CONTRATO, seção 0, "Erro de uso": uma linha `FALHA uso: …` na saída padrão e código 2."""
        self.assertEqual(res.codigo, 2, "esperava código 2 (uso)." + res.relato())
        self.assertTrue(any(l.startswith("FALHA uso:") for l in res.linhas),
                        "esperava uma linha 'FALHA uso: …' na saída padrão." + res.relato())
        self.assertEqual(res.veredito, "FALHA", "a última linha deveria começar com FALHA." + res.relato())

    def acusa(self, res, *regras, caminho=None):
        """Há linha `ERRO` com uma das regras, o código é 1 e o veredito é FALHA. Com `caminho`, a
        linha da regra traz esse caminho de campo."""
        self.falhou(res)
        linhas = res.linhas_da_regra(*regras)
        self.assertTrue(linhas, "esperava linha ERRO com a regra %s; vieram as regras %s.%s"
                        % (" ou ".join(regras), sorted(res.regras), res.relato()))
        if caminho is not None:
            self.assertTrue(any(caminho in linha for linha in linhas),
                            "a linha da regra %s deveria trazer o caminho %s.%s"
                            % (" ou ".join(regras), caminho, res.relato()))

    def acusa_algo(self, res):
        """Há ao menos uma linha `ERRO`, o código é 1 e o veredito é FALHA. Para o que o contrato
        manda recusar sem dizer com que código de regra."""
        self.falhou(res)
        self.assertTrue(res.erros, "esperava ao menos uma linha ERRO." + res.relato())

    def nao_acusa(self, res, *regras):
        """Nenhuma linha `ERRO` com essas regras. Depois confere que a chamada inteira passou: o
        caso no limite foi montado para não ter erro nenhum."""
        linhas = res.linhas_da_regra(*regras)
        self.assertEqual(linhas, [], "a regra %s não deveria ser acusada.%s" % (" ou ".join(regras), res.relato()))
        self.passou(res, "(a regra %s não foi acusada, mas o caso no limite deveria passar inteiro) "
                    % " ou ".join(regras))

    def avisa(self, res, regra, caminho=None):
        """Há linha `AVISO` com a regra, e ela não muda o código (CONTRATO, seção 3)."""
        linhas = res.linhas_da_regra(regra, avisos=True)
        self.assertTrue(linhas, "esperava linha AVISO %s.%s" % (regra, res.relato()))
        if caminho is not None:
            self.assertTrue(any(caminho in linha for linha in linhas),
                            "a linha AVISO %s deveria trazer %s.%s" % (regra, caminho, res.relato()))

    def le_arquivo(self, *partes):
        """Lê um arquivo que a ferramenta deveria ter gravado. Se não existe, o teste falha (e não quebra)."""
        caminho = os.path.join(*partes)
        self.assertTrue(os.path.isfile(caminho), "deveria existir o arquivo %s" % caminho)
        return le_texto(caminho)

    def le_json_de(self, *partes):
        texto = self.le_arquivo(*partes)
        try:
            return json.loads(texto)
        except ValueError as erro:
            self.fail("%s não é JSON: %s" % (os.path.join(*partes), erro))

    def objeto_json(self, res):
        """A saída padrão inteira lida como um objeto JSON (opção `--json`, CONTRATO, seção 0)."""
        try:
            objeto = res.json()
        except ValueError:
            self.fail("com --json, a saída padrão inteira deveria ser um objeto JSON." + res.relato())
        self.assertIsInstance(objeto, dict, "com --json, a saída deveria ser um objeto." + res.relato())
        return objeto

    def iguais(self, obtido, esperado, o_que="o objeto"):
        """Compara dois objetos JSON e, na falha, diz em que caminhos diferem."""
        diferencas = difere(obtido, esperado)
        self.assertEqual(diferencas, [], "%s difere do esperado (obtido contra esperado) em: %s"
                         % (o_que, "; ".join(diferencas[:12])))

    def nada_mudou(self, antes, depois, onde="a pasta"):
        criados, mudados, sumidos = diferenca(antes, depois)
        self.assertEqual((criados, mudados, sumidos), ([], [], []),
                         "%s não deveria mudar: criados %s, mudados %s, sumidos %s" % (onde, criados, mudados, sumidos))
