"""Apoio dos testes do valida.py. Não é teste: é a bancada que os arquivos testa_valida*.py dividem.

O que há aqui:
  - os caminhos das fixtures e os dados congelados já carregados (dados());
  - exemplo(): cópia nova da edição de exemplo; rascunho(data): um rascunho de verdade derivado dela;
  - Arquivo: um repositório de mentira em memória, que "publica" um dia por vez com as funções de cálculo
    do valida.py (do jeito que o publica.py fará) e sabe se gravar numa pasta;
  - ComRaiz: caso de teste com uma raiz temporária montada da cópia congelada, e a chamada da ferramenta
    pela linha de comando, como a rotina chama.
Nada daqui grava dentro do repositório: tudo vai para pasta temporária (respeita $TMPDIR).
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
AQUI = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.dirname(AQUI)
RAIZ = os.path.dirname(os.path.dirname(FIXTURES))
FERRAMENTAS = os.path.join(RAIZ, "ferramentas")
VALIDA = os.path.join(FERRAMENTAS, "valida.py")
DADOS = os.path.join(FIXTURES, "dados")
EXEMPLO = os.path.join(FIXTURES, "edicao-exemplo.json")
ARQUIVOS_DE_DADOS = ("regua", "players", "veiculos", "vetores", "indicadores")
AGORA = "2026-11-20T15:00:00Z"  # o relógio dos testes: meio-dia de 20/11/2026 em Brasília
DIA_DO_EXEMPLO = "2026-11-19"

sys.path.insert(0, FERRAMENTAS)
import comum  # noqa: E402
import valida  # noqa: E402

_guardados = {}


def le(caminho):
    with open(caminho, encoding="utf-8") as arquivo:
        return json.load(arquivo)


def brutos():
    """Cópia nova dos cinco objetos de dados congelados: {"regua": …, "players": …, …}."""
    if "brutos" not in _guardados:
        _guardados["brutos"] = dict((nome, le(os.path.join(DADOS, nome + ".json"))) for nome in ARQUIVOS_DE_DADOS)
    return copy.deepcopy(_guardados["brutos"])


def monta(objetos):
    """Dados a partir de {"regua": …, …}, na ordem que o valida.monta_dados pede."""
    return valida.monta_dados(*[objetos.get(nome) for nome in ARQUIVOS_DE_DADOS])


def dados():
    """Os dados congelados, já carregados. É o mesmo objeto em todos os testes: não mexa nele."""
    if "dados" not in _guardados:
        _guardados["dados"] = monta(brutos())
    return _guardados["dados"]


def exemplo():
    """Cópia nova da edição de exemplo."""
    if "exemplo" not in _guardados:
        _guardados["exemplo"] = le(EXEMPLO)
    return copy.deepcopy(_guardados["exemplo"])


def regras(achados, gravidade="ERRO"):
    """Os códigos de regra de uma lista de achados, sem repetir, em ordem."""
    return sorted(set(a.regra for a in achados if a.gravidade == gravidade))


def linhas(achados):
    return "\n".join(a.linha() for a in achados)


def soma(data, dias):
    return comum.soma_dias(data, dias)


# ---------------------------------------------------------------- do exemplo ao rascunho

def tira_calculados(edicao):
    """A edição sem os campos que o publica.py calcula: é o rascunho que daria essa edição.

    Tira os campos de valida.CALCULADOS, os gatilhos de preço e a marca de conflito de interesse."""
    rascunho = copy.deepcopy(edicao)
    ids_de_indicador = set(i["id"] for i in edicao.get("indicadores", []))
    for chave in valida.CALCULADOS["raiz"]:
        rascunho.pop(chave, None)
    for chave in valida.CALCULADOS["alerta"]:
        rascunho["alerta"].pop(chave, None)
    for dominio in rascunho["alerta"]["dominios"]:
        for chave in valida.CALCULADOS["dominio"]:
            dominio.pop(chave, None)
        dominio["gatilhos"] = [g for g in dominio["gatilhos"] if g["ref"] not in ids_de_indicador]
    for item in rascunho["principais"] + rascunho["radar"]:
        item.pop("conflito_de_interesse", None)
        for ataque in item.get("ataques", []) + ([item["ataque"]] if "ataque" in item else []):
            ataque.pop("lado", None)
    for linha in rascunho["placar_do_dia"]:
        for chave in valida.CALCULADOS["placar_do_dia"]:
            linha.pop(chave, None)
    for chave in valida.CALCULADOS["bastidores"]:
        rascunho["bastidores"].pop(chave, None)
    return rascunho


def _troca_datas(valor, dias):
    """Anda `dias` em todo campo de data (data, publicado_em) de um pedaço da edição."""
    if isinstance(valor, dict):
        for chave, dentro in valor.items():
            if chave in ("data", "publicado_em") and isinstance(dentro, str) and comum.data_valida(dentro):
                valor[chave] = soma(dentro, dias)
            else:
                _troca_datas(dentro, dias)
    elif isinstance(valor, list):
        for dentro in valor:
            _troca_datas(dentro, dias)


def _anda_prazos(item, dias):
    """Anda `dias` em cada data DD/MM das perguntas de `vigiar` de uma principal: a regra R21 (dia) pede o
    prazo da primeira pergunta em até 30 dias da edição, e o rascunho de outro dia leva a pergunta junto."""
    def anda(achado):
        prazo = valida.prazo_do_vigiar(achado.group(0), DIA_DO_EXEMPLO)
        return comum.dd_mm(soma(prazo, dias)) if prazo else achado.group(0)
    item["vigiar"] = [valida._RE_DIA_MES.sub(anda, texto) for texto in item.get("vigiar", [])]


def no_site_do_veiculo(url, dados_=None):
    """`https://exemplo.invalid/VEICULO/resto` vira `https://SITE/exemplo/resto`, com SITE o primeiro `sites`
    do veículo no mapa congelado. É o endereço que passa na regra T4 (o site da URL é do veículo). Endereço
    que não segue esse molde, ou de veículo fora do mapa, fica como está."""
    prefixo = "https://exemplo.invalid/"
    if not isinstance(url, str) or not url.startswith(prefixo) or "/" not in url[len(prefixo):]:
        return url
    veiculo, resto = url[len(prefixo):].split("/", 1)
    ficha = (dados_ or dados()).mapa.get(veiculo)
    return "https://%s/exemplo/%s" % (ficha["sites"][0], resto) if ficha else url


def nos_sites(edicao, dados_=None):
    """Leva ao site do veículo (no_site_do_veiculo) todo endereço de fonte, ataque e vetor da edição. Muda a
    edição recebida e a devolve. Os endereços de fonte `outro` não seguem o molde e ficam como estão."""
    for item in edicao.get("principais", []) + edicao.get("radar", []):
        objetos = list(item.get("fontes", [])) + list(item.get("ataques", [])) + list(item.get("vetores", []))
        if "ataque" in item:
            objetos.append(item["ataque"])
        for objeto in objetos:
            if isinstance(objeto, dict) and "url" in objeto:
                objeto["url"] = no_site_do_veiculo(objeto["url"], dados_)
    return edicao


def indicadores_do_dia(data):
    """O que o indicadores.py gravaria no dia: os 12 indicadores do exemplo, com as datas andadas, e o
    gatilho de preço do Brent (alta de 6,1% em 7 dias)."""
    medidos = exemplo()["indicadores"]
    _troca_datas(medidos, comum.dias_entre(DIA_DO_EXEMPLO, data))
    return {"versao": 1, "dia": data, "gerada_em": data + "T21:03:40Z", "indicadores": medidos,
            "gatilhos": [{"criterio": "energia.2", "ref": "brent",
                          "texto": "Petróleo Brent subiu 6,1%% em 7 dias, até %s (limiar: 5%%)." % comum.dd_mm(data)}],
            "falhas": []}


def indicadores_calmos(data, cegos=(), **variacoes_7d):
    """Os indicadores do dia sem alta nenhuma: nenhum gatilho de preço.

    `cegos` lista indicadores sem a variação de 7 dias (o domínio deles fica cego). `variacoes_7d` troca a
    variação de 7 dias de um indicador e o marca como confirmado: `brent=21.0` dá alta forte confirmada."""
    do_dia = indicadores_do_dia(data)
    do_dia["gatilhos"] = []
    for medido in do_dia["indicadores"]:
        if medido["id"] == "brent":
            medido["variacao_7d_pct"] = 1.0
        if medido["id"] in cegos:
            medido["variacao_7d_pct"] = None
        if medido["id"] in variacoes_7d:
            medido["variacao_7d_pct"] = variacoes_7d[medido["id"]]
            medido["confirmado"] = True
    return do_dia


def sem_gatilhos(rascunho_):
    """Tira todos os gatilhos de evento de um rascunho: um dia calmo."""
    for dominio in rascunho_["alerta"]["dominios"]:
        dominio["gatilhos"] = []
    return rascunho_


def poe_gatilho(rascunho_, criterio, ref, **mais):
    """Acrescenta um gatilho de evento no domínio do critério."""
    gatilho = {"criterio": criterio, "ref": ref, "texto": "Texto fictício. Fato de teste, com data."}
    gatilho.update(mais)
    for dominio in rascunho_["alerta"]["dominios"]:
        if dominio["id"] == criterio.split(".")[0]:
            dominio["gatilhos"].append(gatilho)
    return rascunho_


COLETA = {"versao": 1, "resumo": {"feeds_ok": 61, "feeds_falhos": 7}}


def rascunho(data):
    """Um rascunho de verdade (não é exemplo) para o dia `data`, derivado da edição de exemplo.

    Sai sem player novo, sem errata, sem respostas e sem continuacao_de: o que depende de outras edições
    cada teste põe. Os títulos perdem a marca [EXEMPLO], e as datas das fontes e os prazos DD/MM das
    perguntas de vigiar andam junto com a edição."""
    novo = tira_calculados(exemplo())
    del novo["exemplo"]
    novo["resumo"] = novo["resumo"].replace("[EXEMPLO] ", "")
    _troca_datas(novo, comum.dias_entre(DIA_DO_EXEMPLO, data))
    for item in novo["principais"]:
        _anda_prazos(item, comum.dias_entre(DIA_DO_EXEMPLO, data))
    novo["novos_players"], novo["errata"], novo["respostas"] = [], [], []
    for item in novo["principais"] + novo["radar"]:
        item["titulo"] = item["titulo"].replace("[EXEMPLO] ", "")
        item.pop("continuacao_de", None)
        for fonte in item["fontes"]:
            fonte["titulo"] = fonte["titulo"].replace("[EXEMPLO] ", "")
        for ataque in item.get("ataques", []) + ([item["ataque"]] if "ataque" in item else []):
            if ataque["alvo"] == "republica_exemplo":  # no exemplo é o player novo do dia; aqui não há
                ataque["alvo"], ataque["alvo_nome"] = "outro", "República de Exemplo (fictícia)"
    return novo


def completa(rascunho_, historico=None, dados_=None, indicadores="do dia", coleta=COLETA):
    """O rascunho com os campos calculados, como o publica.py edicao gravaria."""
    data = rascunho_.get("data")
    if indicadores == "do dia":
        indicadores = indicadores_do_dia(data)
    return valida.completa(rascunho_, dados_ or dados(), historico if historico is not None else valida.Historico(),
                           indicadores=indicadores, coleta=coleta, gerada_em="%sT21:14:03Z" % data)


def vespera_do_exemplo():
    """A edição de 18/11/2026 que explica os níveis mantidos do exemplo (câmbio em 2 desde 17/11, alimentos em
    1 desde 10/11). Traz só o que as regras de histórico leem; não é edição completa."""
    def dominio(identificador, nivel, desde):
        return {"id": identificador, "nivel": nivel, "tendencia": "estavel", "desde": desde, "sem_preco": [],
                "gatilhos": [], "leitura": "Texto fictício.", "vigiar": "Texto fictício?"}
    return {"versao": 1, "data": "2026-11-18", "gerada_em": "2026-11-18T21:10:00Z", "estado": "reduzida",
            "resumo": "Véspera fictícia do exemplo.",
            "alerta": {"nivel": 2, "tendencia": "estavel", "motivo": "Texto fictício.", "dominios": [
                dominio("energia", 1, "2026-11-10"), dominio("alimentos", 1, "2026-11-10"),
                dominio("cambio", 2, "2026-11-17"), dominio("suprimentos", 1, "2026-11-10"),
                dominio("conflito", 1, "2026-11-10")]},
            "indicadores": [], "principais": [], "radar": []}


def historico_do_exemplo():
    return valida.Historico({"2026-11-18": vespera_do_exemplo()}, completo=False)


def refaz(edicao, dados_=None):
    """Recalcula os campos calculados de uma edição mexida à mão, como o publica.py faria, com a véspera
    coerente com o exemplo. Os gatilhos de preço que a edição já traz são reaproveitados."""
    ids = set(i["id"] for i in edicao["indicadores"])
    de_preco = [g for d in edicao["alerta"]["dominios"] for g in d["gatilhos"] if g.get("ref") in ids]
    return valida.completa(tira_calculados(edicao), dados_ or dados(), historico_do_exemplo(),
                           indicadores={"indicadores": edicao["indicadores"], "gatilhos": de_preco},
                           coleta=COLETA, gerada_em=edicao["gerada_em"])


class Arquivo(object):
    """Um repositório de mentira, em memória. Publica um dia por vez com as funções do valida.py e acrescenta
    vetores e players nos registros, do jeito que o CONTRATO, seção 4.2, passo 7, manda o publica.py fazer."""

    def __init__(self):
        self.brutos = brutos()
        self.edicoes = {}

    def dados(self):
        return monta(self.brutos)

    def historico(self):
        return valida.Historico(self.edicoes)

    def rascunho(self, data):
        """O rascunho do dia; se já há edição anterior, cada item continua o item de mesmo id dela."""
        novo = rascunho(data)
        anterior = self.historico().anterior(data)
        if anterior is not None:
            ids = set(i["id"] for i in anterior.edicao["principais"] + anterior.edicao["radar"])
            for item in novo["principais"] + novo["radar"]:
                if item["id"] in ids:
                    item["continuacao_de"] = "%s/%s" % (anterior.data, item["id"])
        return novo

    def publica(self, data, muda=None, confere=True, indicadores="do dia"):
        """Publica o dia: rascunho, `muda(rascunho)` se houver, campos calculados, registros. Devolve a edição."""
        novo = self.rascunho(data)
        if muda is not None:
            muda(novo)
        edicao = completa(novo, self.historico(), self.dados(), indicadores)
        if confere:
            achados = valida.confere_edicao(edicao, self.dados(), self.historico(), True, data)
            erros = [a for a in achados if a.gravidade == "ERRO"]
            if erros:
                raise AssertionError("a edição de %s não passa:\n%s" % (data, linhas(erros)))
        self.poe(data, edicao)
        return edicao

    def poe(self, data, edicao):
        """Põe a edição no arquivo e nos registros, sem conferir."""
        self.edicoes[data] = edicao
        if not isinstance(edicao, dict):
            return
        anulacoes = 0
        for chave in ("principais", "radar"):
            for item in edicao.get(chave, []):
                for vetor in item.get("vetores", []):
                    entrada = {"id": "%s_%s_%s" % (data, item["id"], vetor["player"]), "data": data, "item": item["id"],
                               "player": vetor["player"], "de": self.dados().partido_do_player(vetor["player"])}
                    entrada.update((k, vetor[k]) for k in ("para", "forca", "tema", "porque", "url"))
                    if item.get("conflito_de_interesse") is True:
                        entrada["conflito_de_interesse"] = True
                    self.brutos["vetores"]["vetores"].append(entrada)
        for errata in edicao.get("errata", []):
            if "anula_vetor" in errata:
                anulacoes += 1
                self.brutos["vetores"]["vetores"].append({
                    "id": "%s_anula_%d" % (data, anulacoes), "data": data, "anula": errata["anula_vetor"],
                    "porque": errata["correcao"], "url": errata["url"]})
        for novo in edicao.get("novos_players", []):
            self.brutos["players"]["players"].append(dict(novo, origem="rotina", incluido_em=data))
            self.brutos["players"]["atualizado_em"] = data

    def publica_falha(self, data, motivo="Nada funcionou."):
        """A edição de falha do dia, como o `publica.py falha` a monta (CONTRATO, seção 4.3)."""
        anterior = self.historico().anterior(data)
        texto = "Sem leitura hoje." + (" Nível repetido de %s." % comum.dd_mm(anterior.data) if anterior else "")
        falha = {"data": data, "estado": "falha", "resumo": "Sem edição hoje. " + motivo,
                 "alerta": {"motivo": motivo,
                            "dominios": [{"id": d, "gatilhos": [], "leitura": texto, "vigiar": texto}
                                         for d in self.dados().dominios]},
                 "principais": [], "radar": [], "placar_do_dia": [], "novos_players": [], "errata": [],
                 "respostas": [],
                 "bastidores": {"modo": "feeds", "paginas_lidas": 0, "buscas": 0, "minutos": 0,
                                "injecoes_ignoradas": 0, "candidatos": [], "veiculos_sugeridos": [],
                                "limites": motivo}}
        edicao = completa(falha, self.historico(), self.dados(), indicadores=None, coleta=None)
        self.poe(data, edicao)
        return edicao

    def grava(self, raiz, com_indice=True, com_feed=True):
        """Grava tudo numa pasta: dados/, edicoes/ (json, md e índice) e feed.xml."""
        os.makedirs(os.path.join(raiz, "dados"), exist_ok=True)
        os.makedirs(os.path.join(raiz, "edicoes"), exist_ok=True)
        for nome in ARQUIVOS_DE_DADOS:
            grava(os.path.join(raiz, "dados", nome + ".json"), self.brutos[nome])
        for data, edicao in self.edicoes.items():
            grava(os.path.join(raiz, "edicoes", data + ".json"), edicao)
            grava(os.path.join(raiz, "edicoes", data + ".md"), "# INFOCENARIUM %s\n\nTexto de teste.\n" % data)
        if com_indice:
            grava(os.path.join(raiz, "edicoes", "indice.json"), valida.monta_indice(self.edicoes))
        if com_feed:
            grava(os.path.join(raiz, "feed.xml"), FEED)


FEED = ('<?xml version="1.0" encoding="utf-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom">\n'
        "  <title>INFOCENARIUM · monitor geopolítico e de IA</title>\n  <id>./</id>\n"
        "  <updated>2026-11-19T21:14:03Z</updated>\n</feed>\n")


def grava(caminho, conteudo):
    """Grava JSON (objeto), texto ou bytes. Cria a pasta se faltar."""
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    if isinstance(conteudo, bytes):
        bruto = conteudo
    elif isinstance(conteudo, str):
        bruto = conteudo.encode("utf-8")
    else:
        bruto = comum.json_texto(conteudo).encode("utf-8")
    with open(caminho, "wb") as arquivo:
        arquivo.write(bruto)


def fotografa(pasta):
    """A árvore inteira de uma pasta, para comparar antes e depois: {caminho: (tipo, tamanho, mtime, conteúdo)}."""
    foto = {}
    for atual, subpastas, nomes in os.walk(pasta):
        for nome in subpastas + nomes:
            inteiro = os.path.join(atual, nome)
            estado = os.lstat(inteiro)
            conteudo = None
            if os.path.isfile(inteiro) and not os.path.islink(inteiro):
                with open(inteiro, "rb") as arquivo:
                    conteudo = arquivo.read()
            foto[os.path.relpath(inteiro, pasta)] = (estado.st_mode, estado.st_size, estado.st_mtime_ns, conteudo)
    return foto


def ambiente(**variaveis):
    """O ambiente das chamadas: relógio fixo, sem bytecode, e as variáveis do git da máquina fora do caminho."""
    limpo = dict((k, v) for k, v in os.environ.items() if not k.startswith("GIT_") and k != "INFO_AGORA")
    limpo.update(INFO_AGORA=AGORA, PYTHONDONTWRITEBYTECODE="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)
    limpo.update(variaveis)
    return dict((k, v) for k, v in limpo.items() if v is not None)


def roda(argumentos, cwd=RAIZ, **variaveis):
    """Chama `python3 -B valida.py argumentos…` como a rotina chama. Devolve (código, saída, erro)."""
    feito = subprocess.run([sys.executable, "-B", VALIDA] + list(argumentos), cwd=cwd, env=ambiente(**variaveis),
                           stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    return feito.returncode, feito.stdout.decode("utf-8"), feito.stderr.decode("utf-8", "replace")


def git(pasta, *argumentos):
    """Roda o git numa pasta de teste, com identidade local àquele repositório (nunca a da máquina)."""
    feito = subprocess.run(["git"] + list(argumentos), cwd=pasta, env=ambiente(), stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    if feito.returncode != 0:
        raise AssertionError("git %s falhou: %s" % (" ".join(argumentos), feito.stderr.decode("utf-8", "replace")))
    return feito.stdout.decode("utf-8").strip()


def inicia_git(pasta):
    """git init numa pasta de teste, com a identidade de teste gravada só no .git/config dela."""
    git(pasta, "init", "--quiet", "--initial-branch=main", ".")
    git(pasta, "config", "user.name", "Teste do validador")
    git(pasta, "config", "user.email", "teste@exemplo.invalid")
    git(pasta, "config", "commit.gpgsign", "false")


def commit(pasta, mensagem):
    """Põe tudo no índice e faz um commit. Devolve o identificador do commit."""
    git(pasta, "add", "-A")
    git(pasta, "commit", "--quiet", "--allow-empty", "-m", mensagem)
    return git(pasta, "rev-parse", "HEAD")


class ComRaiz(unittest.TestCase):
    """Cada teste ganha uma pasta temporária com `raiz/dados/`, cópia dos dados congelados."""

    maxDiff = None

    def setUp(self):
        temporaria = tempfile.TemporaryDirectory(prefix="info-valida-")
        self.addCleanup(temporaria.cleanup)
        self.pasta = os.path.realpath(temporaria.name)
        self.raiz = os.path.join(self.pasta, "raiz")
        os.makedirs(os.path.join(self.raiz, "dados"))
        for nome in ARQUIVOS_DE_DADOS:
            shutil.copy(os.path.join(DADOS, nome + ".json"), os.path.join(self.raiz, "dados"))

    def caminho(self, *partes):
        return os.path.join(self.raiz, *partes)

    def grava(self, relativo, conteudo):
        grava(self.caminho(relativo), conteudo)
        return self.caminho(relativo)

    def le(self, relativo):
        return le(self.caminho(relativo))

    def muda(self, relativo, funcao):
        """Lê um JSON da raiz, aplica `funcao(objeto)` e grava de volta."""
        objeto = self.le(relativo)
        funcao(objeto)
        self.grava(relativo, objeto)

    def valida(self, *argumentos, **variaveis):
        """Chama a ferramenta com --raiz na raiz do teste. Devolve (código, linhas da saída)."""
        codigo, saida, erro = roda(["--raiz", self.raiz] + list(argumentos), **variaveis)
        self.assertEqual(erro, "", "nada essencial vai para a saída de erro")
        return codigo, saida.splitlines()

    def assertRegras(self, linhas_, esperadas, gravidade="ERRO"):
        """As regras acusadas nas linhas de saída são exatamente as esperadas."""
        achadas = sorted(set(l.split()[1] for l in linhas_ if l.startswith(gravidade + " ")))
        self.assertEqual(achadas, sorted(esperadas), "\n".join(linhas_))


def acusa(teste, achados, regra, caminho=None, gravidade="ERRO"):
    """Afirma que há um achado dessa regra (e, se dado, com esse trecho no caminho). Devolve o achado."""
    for achado in achados:
        if achado.regra == regra and achado.gravidade == gravidade and (caminho is None or caminho in achado.caminho):
            return achado
    teste.fail("faltou %s %s%s em:\n%s" % (gravidade, regra, " em " + caminho if caminho else "", linhas(achados) or "(nada)"))


def limpo(teste, achados, gravidade="ERRO"):
    """Afirma que não há achado dessa gravidade."""
    ruins = [a for a in achados if a.gravidade == gravidade]
    teste.assertEqual(ruins, [], linhas(ruins))
