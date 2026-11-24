"""Apoio dos testes do publica.py. Não é teste: é a bancada que os arquivos testa_publica*.py dividem.

O que há aqui:
  - rascunho(dia): um rascunho de verdade, derivado da edição de exemplo, só com os campos que o agente escreve;
  - monta_trabalho(pasta, rascunho, dia): a pasta de trabalho que a rotina teria nessa hora (rascunho.json,
    coleta.json, indicadores.json, urls.txt e conferencia.json), coerente com as regras T;
  - Bancada: caso de teste com uma raiz temporária montada da cópia congelada dos dados, uma pasta de
    trabalho temporária, o relógio fixo e as chamadas das ferramentas pela linha de comando, como a rotina
    chama. Tem também o git de teste, com identidade local àquele repositório.
Nada daqui grava dentro do repositório: tudo vai para pasta temporária (respeita $TMPDIR).
"""
import copy
import json
import os
import re
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
PUBLICA = os.path.join(FERRAMENTAS, "publica.py")
VALIDA = os.path.join(FERRAMENTAS, "valida.py")
DADOS = os.path.join(FIXTURES, "dados")
EXEMPLO = os.path.join(FIXTURES, "edicao-exemplo.json")
MODELO = os.path.join(AQUI, "modelo.txt")
ARQUIVOS_DE_DADOS = ("regua", "players", "veiculos", "vetores", "indicadores")
DIA_DO_EXEMPLO = "2026-11-19"
DIA = "2026-11-20"  # o dia das edições de teste, quando o teste não pede outro
BASE = "https://exemplo.invalid/INFOCENARIUM/"  # endereço base de teste para o feed
NS = "{http://www.w3.org/2005/Atom}"

sys.path.insert(0, FERRAMENTAS)
import comum  # noqa: E402
import publica  # noqa: E402
import valida  # noqa: E402

_guardados = {}


def agora(dia, hora="21:14:03"):
    """O relógio de teste: o dia da edição, às 18h14 de Brasília (21h14 UTC)."""
    return "%sT%sZ" % (dia, hora)


def le(caminho):
    with open(caminho, encoding="utf-8") as arquivo:
        return json.load(arquivo)


def le_texto(caminho):
    with open(caminho, encoding="utf-8", newline="") as arquivo:
        return arquivo.read()


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


def soma(data, dias):
    return comum.soma_dias(data, dias)


def exemplo():
    """Cópia nova da edição de exemplo."""
    if "exemplo" not in _guardados:
        _guardados["exemplo"] = le(EXEMPLO)
    return copy.deepcopy(_guardados["exemplo"])


def dados():
    """Os dados congelados, já carregados. É o mesmo objeto em todos os testes: não mexa nele."""
    if "dados" not in _guardados:
        _guardados["dados"] = valida.monta_dados(*[le(os.path.join(DADOS, nome + ".json"))
                                                   for nome in ARQUIVOS_DE_DADOS])
    return _guardados["dados"]


# ---------------------------------------------------------------- do exemplo ao rascunho

def _anda_datas(valor, dias):
    """Anda `dias` em todo campo de data (data, publicado_em) de um pedaço da edição."""
    if isinstance(valor, dict):
        for chave, dentro in valor.items():
            if chave in ("data", "publicado_em") and isinstance(dentro, str) and comum.data_valida(dentro):
                valor[chave] = soma(dentro, dias)
            else:
                _anda_datas(dentro, dias)
    elif isinstance(valor, list):
        for dentro in valor:
            _anda_datas(dentro, dias)


_RE_URL_DO_EXEMPLO = re.compile(r"^https://exemplo\.invalid/([a-z0-9_]+)/(.+)$")


def no_site_do_veiculo(url):
    """O endereço fictício do exemplo levado ao site do veículo, para fechar com a regra T4 (o site da URL bate
    com um dos `sites` do veículo; estar na coleta não basta). `https://exemplo.invalid/nyt/terminal-atacado`
    vira `https://nytimes.com/exemplo/terminal-atacado`: o site é o primeiro `sites` do mapa congelado, e o
    caminho continua fictício. Endereço que não é de veículo do mapa fica como está."""
    achado = _RE_URL_DO_EXEMPLO.match(url) if isinstance(url, str) else None
    if not achado or achado.group(1) not in dados().mapa:
        return url
    return "https://%s/exemplo/%s" % (dados().mapa[achado.group(1)]["sites"][0], achado.group(2))


def _leva_ao_site(valor):
    if isinstance(valor, str):
        return no_site_do_veiculo(valor)
    if isinstance(valor, list):
        return [_leva_ao_site(dentro) for dentro in valor]
    if isinstance(valor, dict):
        return dict((chave, _leva_ao_site(dentro)) for chave, dentro in valor.items())
    return valor


def itens(edicao):
    return edicao["principais"] + edicao["radar"]


def ataques(item):
    return item.get("ataques", []) + ([item["ataque"]] if "ataque" in item else [])


def so_do_agente(edicao):
    """A edição sem os campos que o publica.py calcula: é o rascunho que daria essa edição."""
    novo = copy.deepcopy(edicao)
    de_indicador = set(indicador["id"] for indicador in edicao.get("indicadores", []))
    for chave in valida.CALCULADOS["raiz"]:
        novo.pop(chave, None)
    for chave in valida.CALCULADOS["alerta"]:
        novo["alerta"].pop(chave, None)
    for dominio in novo["alerta"]["dominios"]:
        for chave in valida.CALCULADOS["dominio"]:
            dominio.pop(chave, None)
        dominio["gatilhos"] = [gatilho for gatilho in dominio["gatilhos"] if gatilho["ref"] not in de_indicador]
    for item in itens(novo):
        item.pop("conflito_de_interesse", None)
        for ataque in ataques(item):
            ataque.pop("lado", None)
    for linha in novo["placar_do_dia"]:
        for chave in valida.CALCULADOS["placar_do_dia"]:
            linha.pop(chave, None)
    for chave in valida.CALCULADOS["bastidores"]:
        novo["bastidores"].pop(chave, None)
    return novo


def rascunho(dia=DIA):
    """Um rascunho de verdade para o dia, derivado da edição de exemplo: só os campos de origem agente.

    Sai sem player novo, sem errata, sem respostas e sem continuacao_de: o que depende de outras edições,
    cada teste põe. Os títulos perdem a marca [EXEMPLO], as datas das fontes andam junto com o dia e os
    endereços de veículo do mapa vão para o site do veículo (no_site_do_veiculo)."""
    novo = _leva_ao_site(so_do_agente(exemplo()))
    del novo["exemplo"]
    _anda_datas(novo, comum.dias_entre(DIA_DO_EXEMPLO, dia))
    novo["resumo"] = novo["resumo"].replace("[EXEMPLO] ", "")
    novo["novos_players"], novo["errata"], novo["respostas"] = [], [], []
    for item in itens(novo):
        item["titulo"] = item["titulo"].replace("[EXEMPLO] ", "")
        item.pop("continuacao_de", None)
        for fonte in item["fontes"]:
            fonte["titulo"] = fonte["titulo"].replace("[EXEMPLO] ", "")
        for ataque in ataques(item):
            if ataque["alvo"] == "republica_exemplo":  # no exemplo é o player novo do dia; aqui não há
                ataque["alvo"], ataque["alvo_nome"] = "outro", "República de Exemplo (fictícia)"
    return novo


def continua(novo, anterior):
    """Marca cada item do rascunho como continuação do item de mesmo id da edição de `anterior` (a data)."""
    for item in itens(novo):
        item["continuacao_de"] = "%s/%s" % (anterior, item["id"])
    return novo


def player_novo(dia=DIA):
    """O player novo da edição de exemplo, como o agente o escreveria no rascunho."""
    return copy.deepcopy(exemplo()["novos_players"][0])


def indicadores_do_dia(dia=DIA):
    """O que o indicadores.py gravaria no dia: os 12 indicadores do exemplo, com as datas andadas, e o
    gatilho de preço do Brent (alta de 6,1% em 7 dias)."""
    medidos = exemplo()["indicadores"]
    _anda_datas(medidos, comum.dias_entre(DIA_DO_EXEMPLO, dia))
    return {"versao": 1, "dia": dia, "gerada_em": agora(dia, "21:03:40"), "indicadores": medidos,
            "gatilhos": [{"criterio": "energia.2", "ref": "brent",
                          "texto": "Petróleo Brent subiu 6,1%% em 7 dias, até %s (limiar: 5%%)." % comum.dd_mm(dia)}],
            "falhas": [{"id": "gas_natural", "erro": "todas as fontes falharam"}]}


def indicadores_calmos(dia=DIA):
    """Os indicadores do dia sem alta nenhuma: o Brent sobe só 1% em 7 dias, e não há gatilho de preço."""
    do_dia = indicadores_do_dia(dia)
    do_dia["gatilhos"] = []
    for medido in do_dia["indicadores"]:
        if medido["id"] == "brent":
            medido["variacao_7d_pct"] = 1.0
    return do_dia


def sem_gatilhos(novo):
    """Tira todos os gatilhos de evento de um rascunho: um dia calmo."""
    for dominio in novo["alerta"]["dominios"]:
        dominio["gatilhos"] = []
    return novo


def sem_vetores(novo):
    for item in itens(novo):
        item["vetores"] = []
    return novo


def urls_do_agente(novo):
    """Todo endereço que o agente escreveu no rascunho, sem repetir, na ordem."""
    achadas = []
    for item in itens(novo):
        achadas += [fonte["url"] for fonte in item["fontes"]]
        achadas += [ataque["url"] for ataque in ataques(item)]
        achadas += [vetor["url"] for vetor in item["vetores"]]
    for player in novo["novos_players"]:
        achadas += [player["url"]] + list(player["dna_fontes"].values())
    achadas += [objeto["url"] for chave in ("errata", "respostas") for objeto in novo[chave] if "url" in objeto]
    return list(dict.fromkeys(achadas))


def coleta_do_dia(novo, dia=DIA):
    """O coleta.json que deixa o rascunho coerente com as regras T: toda fonte de veículo do mapa é manchete
    da mesa, com o veículo dela (T1 e T4) e a data do feed igual a `publicado_em` (T3)."""
    mapa, manchetes, vistas = dados().mapa, [], set()
    for item in itens(novo):
        for fonte in item["fontes"]:
            if fonte["veiculo"] == "outro" or fonte["url"] in vistas:
                continue
            vistas.add(fonte["url"])
            ficha = mapa[fonte["veiculo"]]
            manchetes.append({"id": "m%04d" % (len(manchetes) + 1), "historia": "h01", "veiculo": fonte["veiculo"],
                              "lado": ficha["lado"], "fatos": ficha["fatos"], "titulo": fonte["titulo"],
                              "resumo": "", "url": fonte["url"], "publicado_em": fonte["publicado_em"] + "T12:00:00Z",
                              "categoria": item["categoria"], "suspeito": False})
    return {"versao": 1, "dia": dia, "gerada_em": agora(dia, "21:03:10"), "janela_horas": 36,
            "resumo": {"feeds_ok": 61, "feeds_falhos": 7, "veiculos_ok": 48, "manchetes": len(manchetes),
                       "suspeitas": 0, "partidos": {}},
            "feeds": [], "manchetes": manchetes, "historias": []}


def monta_trabalho(pasta, novo, dia=DIA, coleta=True, indicadores=True, conferencia=True, urls=True):
    """Grava a pasta de trabalho do dia: o rascunho e o que as outras ferramentas teriam deixado.

    Cada opção aceita True (o arquivo coerente com o rascunho), None ou False (sem o arquivo) ou o próprio
    conteúdo. urls.txt leva as páginas que o agente "abriu": tudo o que não está na mesa, mais a página de
    cada ataque com `omite` (T5). conferencia.json diz que todas responderam, sem data."""
    os.makedirs(pasta, exist_ok=True)
    grava(os.path.join(pasta, "rascunho.json"), novo if isinstance(novo, (str, bytes)) else comum.json_texto(novo))
    for nome in ("coleta.json", "indicadores.json", "conferencia.json", "urls.txt"):
        if os.path.exists(os.path.join(pasta, nome)):
            os.unlink(os.path.join(pasta, nome))
    if not isinstance(novo, dict):
        return
    da_coleta = coleta_do_dia(novo, dia) if coleta is True else coleta
    na_mesa = set(m["url"] for m in da_coleta["manchetes"]) if da_coleta else set()
    abertas = [url for url in urls_do_agente(novo) if url not in na_mesa]
    abertas += [ataque["url"] for item in itens(novo) for ataque in ataques(item)
                if "omite" in ataque and ataque["url"] not in abertas]
    if da_coleta:
        grava(os.path.join(pasta, "coleta.json"), da_coleta)
    if indicadores:
        grava(os.path.join(pasta, "indicadores.json"), indicadores_do_dia(dia) if indicadores is True else indicadores)
    if urls:
        texto = "# páginas abertas nesta execução\n" + "".join(url + "\n" for url in abertas)
        grava(os.path.join(pasta, "urls.txt"), texto if urls is True else urls)
    if conferencia:
        paginas = [{"url": url, "estado": "ok", "publicado_em": None} for url in abertas if url not in na_mesa]
        grava(os.path.join(pasta, "conferencia.json"),
              {"versao": 1, "gerada_em": agora(dia, "21:12:00"), "paginas": paginas}
              if conferencia is True else conferencia)


# ---------------------------------------------------------------- rodar as ferramentas

def ambiente(**variaveis):
    """O ambiente das chamadas: sem bytecode, sem relógio herdado e com o git da máquina fora do caminho."""
    limpo = dict((k, v) for k, v in os.environ.items() if not k.startswith("GIT_") and k != "INFO_AGORA")
    limpo.update(PYTHONDONTWRITEBYTECODE="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)
    limpo.update(variaveis)
    return dict((k, v) for k, v in limpo.items() if v is not None)


def roda(ferramenta, argumentos, cwd=RAIZ, **variaveis):
    """Chama `python3 -B ferramenta argumentos…` como a rotina chama. Devolve (código, saída, saída de erro)."""
    feito = subprocess.run([sys.executable, "-B", ferramenta] + list(argumentos), cwd=cwd, env=ambiente(**variaveis),
                           stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
    return feito.returncode, feito.stdout.decode("utf-8"), feito.stderr.decode("utf-8", "replace")


def git(pasta, *argumentos):
    """Roda o git numa pasta de teste, com identidade local àquele repositório (nunca a da máquina)."""
    feito = subprocess.run(["git"] + list(argumentos), cwd=pasta, env=ambiente(), stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    if feito.returncode != 0:
        raise AssertionError("git %s falhou: %s" % (" ".join(argumentos), feito.stderr.decode("utf-8", "replace")))
    return feito.stdout.decode("utf-8").strip()


def fotografa(pasta):
    """A árvore inteira de uma pasta, para comparar antes e depois: {caminho: (modo, tamanho, mtime, conteúdo)}.
    A pasta .git fica de fora: o git mexe nela por conta própria."""
    foto = {}
    for atual, subpastas, nomes in os.walk(pasta):
        subpastas[:] = [s for s in subpastas if s != ".git"]
        for nome in subpastas + nomes:
            inteiro = os.path.join(atual, nome)
            estado = os.lstat(inteiro)
            conteudo = None
            if os.path.isfile(inteiro) and not os.path.islink(inteiro):
                with open(inteiro, "rb") as arquivo:
                    conteudo = arquivo.read()
            foto[os.path.relpath(inteiro, pasta)] = (estado.st_mode, estado.st_size, estado.st_mtime_ns, conteudo)
    return foto


def conteudos(pasta):
    """{caminho: bytes} dos arquivos de uma pasta (sem a .git): para comparar duas publicações byte a byte."""
    return dict((caminho, ficha[3]) for caminho, ficha in fotografa(pasta).items() if ficha[3] is not None)


class Bancada(unittest.TestCase):
    """Cada teste ganha uma pasta temporária com `raiz/dados/` (cópia dos dados congelados) e `trabalho/`."""

    maxDiff = None
    dia = DIA

    def setUp(self):
        temporaria = tempfile.TemporaryDirectory(prefix="info-publica-")
        self.addCleanup(temporaria.cleanup)
        self.pasta = os.path.realpath(temporaria.name)
        self.raiz = os.path.join(self.pasta, "raiz")
        self.trabalho = os.path.join(self.pasta, "trabalho")
        os.makedirs(os.path.join(self.raiz, "dados"))
        os.makedirs(self.trabalho)
        for nome in ARQUIVOS_DE_DADOS:
            shutil.copy(os.path.join(DADOS, nome + ".json"), os.path.join(self.raiz, "dados"))

    # ------------------------------------------------------------ arquivos

    def caminho(self, *partes):
        return os.path.join(self.raiz, *partes)

    def no_trabalho(self, *partes):
        return os.path.join(self.trabalho, *partes)

    def le(self, relativo):
        return le(self.caminho(relativo))

    def texto(self, relativo):
        return le_texto(self.caminho(relativo))

    def grava(self, relativo, conteudo):
        grava(self.caminho(relativo), conteudo)

    def muda(self, relativo, funcao):
        """Lê um JSON da raiz, aplica `funcao(objeto)` e grava de volta."""
        objeto = self.le(relativo)
        funcao(objeto)
        self.grava(relativo, objeto)

    def existe(self, relativo):
        return os.path.exists(self.caminho(relativo))

    # ------------------------------------------------------------ ferramentas

    def publica(self, subcomando, *argumentos, **opcoes):
        """Chama o publica.py com --raiz e --trabalho de teste e o relógio fixo. Devolve (código, linhas).

        Opções: dia (None deixa a ferramenta escolher), agora (o INFO_AGORA; padrão: o dia, às 21h14 UTC),
        sem_trabalho (não passa --trabalho) e variáveis de ambiente a mais."""
        dia = opcoes.pop("dia", self.dia)
        relogio = opcoes.pop("agora", agora(dia or self.dia))
        linha = [subcomando, "--raiz", self.raiz]
        if not opcoes.pop("sem_trabalho", subcomando == "refaz"):
            linha += ["--trabalho", self.trabalho]
        if dia is not None and subcomando != "refaz":
            linha += ["--dia", dia]
        codigo, saida, erro = roda(PUBLICA, linha + list(argumentos), INFO_AGORA=relogio, **opcoes)
        self.assertEqual(erro, "", "nada essencial vai para a saída de erro")
        self.assertTrue(saida.endswith("\n"), saida)
        return codigo, saida.splitlines()

    def valida(self, *argumentos, **opcoes):
        relogio = opcoes.pop("agora", agora(self.dia))
        codigo, saida, erro = roda(VALIDA, ["--raiz", self.raiz] + list(argumentos), INFO_AGORA=relogio, **opcoes)
        self.assertEqual(erro, "", "nada essencial vai para a saída de erro")
        return codigo, saida.splitlines()

    def prepara(self, dia=None, muda=None, **opcoes):
        """Monta a pasta de trabalho do dia com um rascunho válido (`muda(rascunho)` mexe nele antes)."""
        dia = dia or self.dia
        novo = rascunho(dia)
        if muda is not None:
            muda(novo)
        monta_trabalho(self.trabalho, novo, dia, **opcoes)
        return novo

    def publica_o_dia(self, dia=None, muda=None, argumentos=(), **trabalho):
        """Prepara a pasta de trabalho e publica a edição do dia; o teste falha se a publicação não passa.

        `trabalho` são as opções do monta_trabalho (indicadores=…, coleta=…). Devolve o rascunho publicado."""
        dia = dia or self.dia
        novo = self.prepara(dia, muda, **trabalho)
        codigo, linhas = self.publica("edicao", "--url-base", BASE, *argumentos, dia=dia)
        self.assertEqual(codigo, 0, "\n".join(linhas))
        self.assertTrue(linhas[-1].startswith("OK edição %s publicada" % dia), linhas[-1])
        self.linhas = linhas
        return novo

    def publica_a_falha(self, dia=None, motivo="Sem busca nem feed.", **trabalho):
        """Publica a edição de falha do dia. A pasta de trabalho fica só com o que `trabalho` pedir."""
        dia = dia or self.dia
        for nome in os.listdir(self.trabalho):
            os.unlink(self.no_trabalho(nome))
        if trabalho.get("indicadores"):
            grava(self.no_trabalho("indicadores.json"),
                  indicadores_do_dia(dia) if trabalho["indicadores"] is True else trabalho["indicadores"])
        codigo, linhas = self.publica("falha", "--motivo", motivo, "--url-base", BASE, dia=dia)
        self.assertEqual(codigo, 0, "\n".join(linhas))
        self.assertTrue(linhas[-1].startswith("OK falha de %s publicada" % dia), linhas[-1])
        self.linhas = linhas

    def assertOK(self, resultado):
        codigo, linhas = resultado
        self.assertEqual(codigo, 0, "\n".join(linhas))
        self.assertTrue(linhas[-1].startswith("OK"), linhas[-1])
        return linhas

    def assertFALHA(self, resultado, codigo_esperado=1):
        codigo, linhas = resultado
        self.assertEqual(codigo, codigo_esperado, "\n".join(linhas))
        self.assertTrue(linhas[-1].startswith("FALHA"), linhas[-1])
        return linhas

    def assertValido(self, *argumentos, **opcoes):
        """O validador de verdade aceita a raiz: `valida.py --tudo` mais os argumentos dados."""
        codigo, linhas = self.valida("--tudo", *argumentos, **opcoes)
        self.assertEqual(codigo, 0, "\n".join(linhas))
        self.assertTrue(linhas[-1].startswith("OK 0 erros"), linhas[-1])
        return linhas

    # ------------------------------------------------------------ git de teste

    def git(self, *argumentos):
        return git(self.raiz, *argumentos)

    def inicia_git(self):
        """git init na raiz de teste, com a identidade gravada só no .git/config dela, e o primeiro commit."""
        self.git("init", "--quiet", "--initial-branch=main", ".")
        self.git("config", "user.name", "Teste do publicador")
        self.git("config", "user.email", "teste@exemplo.invalid")
        self.git("config", "commit.gpgsign", "false")
        return self.commit("base")

    def commit(self, mensagem):
        self.git("add", "-A")
        self.git("commit", "--quiet", "--allow-empty", "-m", mensagem)
        return self.git("rev-parse", "HEAD")

    def mudancas(self):
        """O `git status` da raiz de teste: [(marca, caminho)], em ordem. "??" é arquivo novo; "M", alterado."""
        feito = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=self.raiz,
                               env=ambiente(), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, timeout=60)
        self.assertEqual(feito.returncode, 0)
        return sorted((linha[:2].strip(), linha[3:]) for linha in feito.stdout.decode("utf-8").splitlines())

    def fotos(self):
        """A raiz inteira (com datas de gravação) e o conteúdo da pasta de trabalho. A data da pasta de trabalho
        fica de fora: toda chamada prova que dá para gravar nela, criando e apagando um arquivo."""
        return fotografa(self.raiz), conteudos(self.trabalho)
