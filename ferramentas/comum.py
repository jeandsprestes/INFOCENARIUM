"""Base comum das quatro ferramentas do INFOCENARIUM: coleta.py, indicadores.py, valida.py e publica.py.

Aqui mora só o que é igual nas quatro (CONTRATO, seção 0; ESQUEMA, seção 0). Regra de edição,
leitura de feed e pedido de rede NÃO moram aqui. Só biblioteca padrão.

GUARDA DE VERSÃO. Cole no topo de cada ferramenta, antes de importar este módulo. O Python lê o
arquivo inteiro antes de rodar a primeira linha: para a guarda funcionar, o arquivo da ferramenta
só usa sintaxe que o Python 3.6 lê (sem match, sem :=, sem "with (a, b):", sem parâmetro "/").

    # --- guarda de versão: início ---
    import os
    import sys

    if sys.version_info < (3, 10):
        print("FALHA interna: Python 3.10 ou mais novo")
        sys.exit(1)
    sys.dont_write_bytecode = True
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    # --- guarda de versão: fim ---

O QUE O MÓDULO OFERECE
  Códigos    OK=0  FALHA=1  USO=2  PARCIAL=3  SEM_REDE=4
  Erros      ErroDeUso(msg): vira "FALHA uso: msg", código 2.
             Falha(msg, codigo=FALHA): falha prevista; vira "FALHA msg" na última linha.
  Relógio    agora() (UTC, obedece a INFO_AGORA), agora_texto(), hoje_brasilia(), dia_brasilia(instante),
             le_data(t), data_valida(t), le_data_hora(t), data_hora_valida(t), texto_data_hora(instante),
             dd_mm(d), dd_mm_aaaa(d), dias_entre(de, ate), soma_dias(d, n).
             Data é texto AAAA-MM-DD. Data-hora é texto UTC AAAA-MM-DDTHH:MM:SSZ.
  Opções     opcoes(descricao, trabalho=True, dia=True, saida_json=True): argparse com --raiz, --trabalho,
             --dia e --json; erro de uso em uma linha. Com subcomandos: analisador(descricao) e
             poe_comuns(sub.add_parser("nome")) em cada um (opção comum vem depois do subcomando).
             prepara(args, dia_padrao=DIA_DO_CONTEXTO ou DIA_DE_HOJE): confere INFO_AGORA e --raiz,
             cria a pasta de trabalho e resolve --dia (args.dia_informado diz se veio na linha de comando).
             le_contexto(trabalho), dia_do_contexto(trabalho), garante_trabalho(pasta).
  Saída      Saida(em_json): .linha(texto), .dado(chave, valor), .fecha(veredito, codigo=None, objeto=None).
             Junta as linhas e imprime tudo no fim, em UTF-8, com o veredito na última linha.
  Execução   executa(principal): chama principal(argv), que devolve o código, e sai com ele. Exceção solta
             vira "FALHA interna: Tipo: mensagem", código 1. Erro de uso sai sempre como texto, até com --json.
             protege(principal, argv) faz o mesmo sem sair (para teste).
  Arquivos   le_json(caminho, se_faltar=...), json_texto(objeto), grava_json(caminho, objeto),
             grava_texto(caminho, texto), Lote() com .json(), .texto() e .grava() (tudo ou nada).
  URL        url_valida(v), site_de(url), site_bate(site, nomes), url_bate(url, nomes),
             endereco_limpo(url) (chave de comparação), sem_rastreio(url) (sem #… e sem utm_).

ESQUELETO DE UMA FERRAMENTA (depois da guarda)

    import comum  # noqa: E402

    def principal(argv):
        an = comum.opcoes("O que a ferramenta faz.")       # no valida.py: trabalho=False
        an.add_argument("--horas", type=int, default=None)
        args = comum.prepara(an.parse_args(argv))          # no valida.py e no publica.py contexto:
        saida = comum.Saida(args.json)                     #   dia_padrao=comum.DIA_DE_HOJE
        regua = comum.le_json(os.path.join(args.raiz, "dados", "regua.json"))
        if "dominios" not in regua:
            raise comum.Falha("dados/regua.json sem a chave dominios")
        saida.linha("dia %s, %d domínios" % (args.dia, len(regua["dominios"])))
        destino = os.path.join(args.trabalho, "exemplo.json")
        comum.grava_json(destino, {"dia": args.dia, "gerada_em": comum.agora_texto()})
        saida.dado("dia", args.dia)                        # entra no objeto do --json
        return saida.fecha("OK 1 arquivo gravado")         # imprime tudo e devolve o código

    if __name__ == "__main__":
        comum.executa(principal)
"""
import argparse
import json
import os
import re
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlsplit

OK, FALHA, USO, PARCIAL, SEM_REDE = 0, 1, 2, 3, 4

RAIZ_PADRAO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRABALHO_PADRAO = "/tmp/info"
DIA_DO_CONTEXTO, DIA_DE_HOJE = "contexto", "hoje"

# Código que cada começo de veredito aceita (CONTRATO, seção 0). O primeiro é o padrão.
_VEREDITOS = (("OK", (OK,)), ("PARCIAL", (PARCIAL,)), ("FALHA", (FALHA, USO, SEM_REDE)))
_NADA = object()
_saida_aberta = None  # a Saida em uso: o invólucro precisa dela para fechar depois de um erro
_json_pedido = False  # o prepara() anota o --json: falha antes da primeira Saida também sai em JSON


class ErroDeUso(Exception):
    """Opção errada ou valor ilegível na linha de comando: "FALHA uso: …", código 2."""


class Falha(Exception):
    """Falha prevista, com mensagem para quem lê: "FALHA …" e o código dado (1 por padrão)."""

    def __init__(self, mensagem, codigo=FALHA):
        super().__init__(mensagem)
        self.codigo = codigo


# ---------------------------------------------------------------- relógio

_RE_DATA = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})")
_RE_DATA_HORA = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})Z")


def le_data(texto):
    """'AAAA-MM-DD' vira date. ValueError se a forma é outra ou se o dia não existe no calendário."""
    if isinstance(texto, date) and not isinstance(texto, datetime):
        return texto
    achado = _RE_DATA.fullmatch(texto) if isinstance(texto, str) else None
    try:
        return date(*map(int, achado.groups()))
    except (AttributeError, ValueError):
        raise ValueError("data ilegível: %r (use AAAA-MM-DD, dia que existe)" % (texto,)) from None


def le_data_hora(texto):
    """'AAAA-MM-DDTHH:MM:SSZ' vira datetime em UTC. ValueError se a forma é outra ou o instante não existe."""
    achado = _RE_DATA_HORA.fullmatch(texto) if isinstance(texto, str) else None
    try:
        return datetime(*map(int, achado.groups()), tzinfo=timezone.utc)
    except (AttributeError, ValueError):
        raise ValueError("data-hora ilegível: %r (use AAAA-MM-DDTHH:MM:SSZ)" % (texto,)) from None


def _valida(leitor, texto):
    try:
        leitor(texto)
    except ValueError:
        return False
    return isinstance(texto, str)


def data_valida(texto):
    return _valida(le_data, texto)


def data_hora_valida(texto):
    return _valida(le_data_hora, texto)


def _em_utc(instante):
    """Aceita o texto de data-hora ou um datetime. Datetime sem fuso é lido como UTC, nunca como hora da máquina."""
    if isinstance(instante, str):
        return le_data_hora(instante)
    if instante.tzinfo is None:
        return instante.replace(tzinfo=timezone.utc)
    return instante.astimezone(timezone.utc)


def texto_data_hora(instante):
    i = _em_utc(instante)
    return "%04d-%02d-%02dT%02d:%02d:%02dZ" % (i.year, i.month, i.day, i.hour, i.minute, i.second)


def agora():
    """Agora, em UTC, sem fração de segundo. INFO_AGORA troca o relógio (só os testes definem a variável)."""
    fixo = os.environ.get("INFO_AGORA")
    if fixo is None:
        return datetime.now(timezone.utc).replace(microsecond=0)
    try:
        return le_data_hora(fixo)
    except ValueError:
        raise ErroDeUso("INFO_AGORA ilegível") from None


def agora_texto():
    return texto_data_hora(agora())


def dia_brasilia(instante):
    """O dia em Brasília de um instante. Conta fixa de UTC menos 3 horas: não usa o fuso da máquina."""
    return (_em_utc(instante) - timedelta(hours=3)).date().isoformat()


def hoje_brasilia():
    return dia_brasilia(agora())


def dd_mm(data):
    d = le_data(data)
    return "%02d/%02d" % (d.day, d.month)


def dd_mm_aaaa(data):
    return "%s/%04d" % (dd_mm(data), le_data(data).year)


def dias_entre(de, ate):
    """Quantos dias vão de `de` até `ate` (negativo se `ate` vem antes)."""
    return (le_data(ate) - le_data(de)).days


def soma_dias(data, dias):
    return (le_data(data) + timedelta(days=dias)).isoformat()


# ---------------------------------------------------------------- saída

def _uma_linha(texto):
    return " ".join(str(texto).split())


def _emite(texto):
    """Escreve na saída padrão em UTF-8, mesmo com a máquina em locale C ou POSIX."""
    try:
        saida = sys.stdout
        if hasattr(saida, "buffer"):
            saida.flush()
            saida.buffer.write(texto.encode("utf-8", "backslashreplace"))
            saida.buffer.flush()
        else:  # saída trocada por um objeto de texto, como nos testes
            saida.write(texto)
            saida.flush()
    except BrokenPipeError:
        _cala_saida()


def _cala_saida():
    """Quem lia fechou o cano: o resto vai para o nada, para o Python não reclamar na hora de sair."""
    try:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
    except (OSError, ValueError, AttributeError):
        pass


class Saida:
    """Junta as linhas e imprime tudo no fim, com o veredito na última linha (CONTRATO, seção 0)."""

    def __init__(self, em_json=False):
        global _saida_aberta
        self.em_json = bool(em_json)
        self.linhas = []
        self.dados = {}
        self.fechada = False
        _saida_aberta = self

    def linha(self, texto=""):
        self.linhas.extend(str(texto).splitlines() or [""])

    def dado(self, chave, valor):
        """Campo a mais do objeto do --json. No modo texto não aparece."""
        self.dados[chave] = valor

    def fecha(self, veredito, codigo=None, objeto=None):
        """Imprime tudo e devolve o código. Sem `codigo`, vale o do veredito: OK 0, PARCIAL 3, FALHA 1.

        Com --json sai {"ok", "codigo", "veredito", "linhas"} mais os dados; `objeto`, se dado, sai no
        lugar (o valida.py tem forma própria no CONTRATO, seção 3)."""
        veredito = _uma_linha(veredito)
        aceitos = next((cods for nome, cods in _VEREDITOS if veredito.startswith(nome)), None)
        if aceitos is None:
            raise ValueError("o veredito tem de começar com OK, PARCIAL ou FALHA: %r" % veredito)
        codigo = aceitos[0] if codigo is None else codigo
        if codigo not in aceitos:
            raise ValueError("o código %r não combina com o veredito %r" % (codigo, veredito))
        if not self.em_json:
            texto = "\n".join(self.linhas + [veredito]) + "\n"
        else:
            if objeto is None:
                objeto = {"ok": codigo == OK, "codigo": codigo, "veredito": veredito, "linhas": self.linhas}
                objeto.update(self.dados)
            texto = json_texto(objeto)
        self.fechada = True
        _emite(texto)
        return codigo


# ---------------------------------------------------------------- execução protegida

def _termina(veredito, codigo, so_veredito=False):
    """Fecha depois de um erro: o que já estava juntado sai antes, e a linha FALHA fica por último."""
    saida = _saida_aberta
    if saida is None and _json_pedido:
        saida = Saida(em_json=True)
    if saida is not None and not saida.fechada and not so_veredito:
        try:
            return saida.fecha(veredito, codigo)
        except (TypeError, ValueError):  # dado que não cabe em JSON: sobra a linha de texto
            pass
    _emite(_uma_linha(veredito) + "\n")
    return codigo


def protege(principal, argv=None):
    """Chama principal(argv) e devolve o código de saída. Nenhuma exceção escapa e nada vai para a saída de erro."""
    global _saida_aberta, _json_pedido
    _saida_aberta, _json_pedido = None, False
    try:
        codigo = principal(sys.argv[1:] if argv is None else list(argv))
        if _saida_aberta is not None and not _saida_aberta.fechada:
            raise RuntimeError("a ferramenta terminou sem veredito")
        if codigo not in (OK, FALHA, USO, PARCIAL, SEM_REDE) or isinstance(codigo, bool):
            raise RuntimeError("código de saída fora da tabela: %r" % (codigo,))
        return codigo
    except ErroDeUso as erro:  # sempre uma linha de texto: a linha de comando nem chegou a valer
        return _termina("FALHA uso: %s" % erro, USO, so_veredito=True)
    except Falha as erro:
        return _termina("FALHA %s" % erro, erro.codigo)
    except KeyboardInterrupt:
        return _termina("FALHA interrompida", FALHA)
    except BrokenPipeError:
        _cala_saida()
        return FALHA
    except Exception as erro:  # o CONTRATO pede: nunca terminar com exceção solta
        mensagem = _uma_linha(erro)
        return _termina("FALHA interna: %s%s" % (type(erro).__name__, ": " + mensagem if mensagem else ""), FALHA)


def executa(principal):
    sys.exit(protege(principal))


# ---------------------------------------------------------------- linha de comando

# O argparse fala inglês e não tem tradução. Estas são as mensagens que uma opção errada produz.
_TRADUCOES = (
    (r"unrecognized arguments: (.*)", r"opção desconhecida: \1"),
    (r"the following arguments are required: (.*)", r"falta \1"),
    (r"one of the arguments (.*) is required", r"falta uma destas opções: \1"),
    (r"argument (.+?): expected one argument", r"\1 pede um valor"),
    (r"argument (.+?): expected (.*)", r"\1 pede valor (\2)"),
    (r"argument (.+?): ignored explicit argument (.*)", r"\1 não aceita valor"),
    (r"argument (.+?): not allowed with argument (.*)", r"\1 não vai junto com \2"),
    (r"argument (.+?): invalid choice: (.+?) \(choose from (.*)\)", r"\1: \2 não vale; use um destes: \3"),
    (r"argument (.+?): invalid \S+ value: (.*)", r"\1: valor ilegível \2"),
    (r"argument (.+?): (.*)", r"\1: \2"),
)


class Opcoes(argparse.ArgumentParser):
    """O argparse com o erro de uso do CONTRATO: uma linha na saída padrão e código 2, sem o modo de usar."""

    def __init__(self, *posicionais, **nomeados):
        nomeados.setdefault("allow_abbrev", False)  # "--trab" não vale por "--trabalho"
        super().__init__(*posicionais, **nomeados)

    def error(self, message):
        mensagem = _uma_linha(message)
        for molde, troca in _TRADUCOES:
            achado = re.fullmatch(molde, mensagem)
            if achado:
                mensagem = achado.expand(troca)
                break
        raise ErroDeUso(mensagem)

    def _print_message(self, message, file=None):  # o -h também sai em UTF-8, na saída padrão
        if message:
            _emite(message)


def _tipo_dia(texto):
    if not data_valida(texto):
        raise argparse.ArgumentTypeError("data ilegível %r (use AAAA-MM-DD, dia que existe)" % texto)
    return texto


def _tipo_pasta(texto):
    if not texto.strip():  # pasta vazia viraria a pasta de onde a ferramenta foi chamada
        raise argparse.ArgumentTypeError("falta o nome da pasta")
    return texto


def analisador(descricao="", **nomeados):
    """Um Opcoes vazio, para quem monta as opções à mão (subcomandos)."""
    return Opcoes(description=descricao, **nomeados)


def poe_comuns(an, raiz=True, trabalho=True, dia=True, saida_json=True):
    """Acrescenta as opções comuns (CONTRATO, seção 0). Desligue a que a ferramenta não tem."""
    if raiz:
        an.add_argument("--raiz", metavar="PASTA", type=_tipo_pasta, default=RAIZ_PADRAO,
                        help="raiz do repositório (padrão: a pasta acima de ferramentas/)")
    if trabalho:
        an.add_argument("--trabalho", metavar="PASTA", type=_tipo_pasta, default=TRABALHO_PADRAO,
                        help="pasta de trabalho, fora do repositório (padrão: " + TRABALHO_PADRAO + ")")
    if dia:
        an.add_argument("--dia", metavar="AAAA-MM-DD", type=_tipo_dia, default=None, help="dia da edição")
    if saida_json:
        an.add_argument("--json", action="store_true", help="imprime um objeto JSON no lugar do texto")
    return an


def opcoes(descricao="", trabalho=True, dia=True, saida_json=True):
    return poe_comuns(analisador(descricao), trabalho=trabalho, dia=dia, saida_json=saida_json)


def garante_trabalho(pasta):
    """Cria a pasta de trabalho se faltar e prova que dá para gravar nela. Devolve o caminho absoluto."""
    pasta = os.path.abspath(pasta)
    try:
        os.makedirs(pasta, exist_ok=True)
        descritor, prova = tempfile.mkstemp(dir=pasta, prefix=".prova-")
        os.close(descritor)
        os.unlink(prova)
    except OSError as erro:
        raise Falha("a pasta de trabalho %s não aceita gravação (%s). Use --trabalho PASTA, com uma pasta "
                    "em que dê para gravar" % (pasta, erro.strerror or type(erro).__name__)) from None
    return pasta


def le_contexto(trabalho):
    """O contexto.json da pasta de trabalho, ou None se o arquivo não existe. Quebrado: Falha."""
    caminho = os.path.join(trabalho, "contexto.json")
    contexto = le_json(caminho, se_faltar=None)
    if contexto is not None and not isinstance(contexto, dict):
        raise Falha("%s: deveria ser um objeto. Rode publica.py contexto de novo" % caminho)
    return contexto


def dia_do_contexto(trabalho):
    """O padrão de --dia: o `dia` do contexto.json; sem o arquivo, hoje em Brasília (CONTRATO, seção 0).

    Arquivo que existe e não dá para ler é Falha: cair para "hoje" trocaria de dia calado, depois da meia-noite."""
    contexto = le_contexto(trabalho)
    if contexto is None:
        return hoje_brasilia()
    if not data_valida(contexto.get("dia")):
        raise Falha("%s: campo dia ilegível. Rode publica.py contexto de novo, ou passe --dia"
                    % os.path.join(trabalho, "contexto.json"))
    return contexto["dia"]


def prepara(args, dia_padrao=DIA_DO_CONTEXTO):
    """Depois do parse_args. O que é erro de uso aparece aqui, antes de qualquer gravação."""
    global _json_pedido
    if dia_padrao not in (DIA_DO_CONTEXTO, DIA_DE_HOJE):
        raise ValueError("dia_padrao desconhecido: %r" % (dia_padrao,))
    agora()  # INFO_AGORA ilegível para a ferramenta já
    _json_pedido = bool(getattr(args, "json", False))
    if getattr(args, "raiz", None) is not None:
        args.raiz = os.path.abspath(args.raiz)
        if not os.path.isdir(args.raiz):
            raise ErroDeUso("--raiz: a pasta %s não existe" % args.raiz)
    tem_trabalho = getattr(args, "trabalho", None) is not None
    if tem_trabalho:
        args.trabalho = garante_trabalho(args.trabalho)
    if hasattr(args, "dia"):
        args.dia_informado = args.dia is not None
        if args.dia is None:
            do_contexto = tem_trabalho and dia_padrao == DIA_DO_CONTEXTO
            args.dia = dia_do_contexto(args.trabalho) if do_contexto else hoje_brasilia()
    return args


# ---------------------------------------------------------------- arquivos

_RE_CONSTANTE = re.compile(r'"(?:[^"\\]|\\.)*"|-?Infinity|NaN', re.S)


def _recusa_constante(nome):
    raise ValueError(nome)


def _linha_e_coluna(trecho):
    return trecho.count("\n") + 1, len(trecho) - (trecho.rfind("\n") + 1) + 1


def le_json(caminho, se_faltar=_NADA):
    """Lê JSON em UTF-8. Recusa BOM, NaN e Infinity. O erro (Falha) diz o arquivo, a linha e a coluna.

    Com `se_faltar`, arquivo que não existe devolve esse valor no lugar da Falha."""
    try:
        with open(caminho, "rb") as arquivo:
            bruto = arquivo.read()
    except FileNotFoundError:
        if se_faltar is not _NADA:
            return se_faltar
        raise Falha("%s: o arquivo não existe" % caminho) from None
    except OSError as erro:
        raise Falha("%s: não deu para ler (%s)" % (caminho, type(erro).__name__)) from None
    onde, motivo = (1, 1), None
    try:
        if bruto.startswith(b"\xef\xbb\xbf"):
            motivo = "começa com BOM; grave em UTF-8 sem BOM"
        else:
            texto = bruto.decode("utf-8")
            return json.loads(texto, parse_constant=_recusa_constante)
    except UnicodeDecodeError as erro:
        onde, motivo = _linha_e_coluna(bruto[:erro.start].decode("utf-8", "replace")), "não é UTF-8"
    except json.JSONDecodeError as erro:
        onde, motivo = (erro.lineno, erro.colno), "JSON ilegível (%s)" % erro.msg
    except RecursionError:
        motivo = "JSON com níveis demais"
    except ValueError as erro:  # NaN ou Infinity: o leitor não diz onde, então procura-se fora dos textos
        fora = [a.start() for a in _RE_CONSTANTE.finditer(texto) if not a.group().startswith('"')]
        onde, motivo = _linha_e_coluna(texto[:fora[0] if fora else 0]), "%s não vale em JSON" % erro
    raise Falha("%s: linha %d, coluna %d: %s" % ((caminho,) + onde + (motivo,)))


def json_texto(objeto):
    """O formato de gravação do CONTRATO: acentos legíveis, recuo de 2, quebra de linha no fim, chaves na
    ordem em que estão no objeto. Mesma entrada, mesmo texto. NaN e Infinity dão ValueError."""
    return json.dumps(objeto, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def _modo(destino):
    """As permissões do arquivo que já existe; para arquivo novo, as de um arquivo comum."""
    try:
        return os.stat(destino).st_mode & 0o777
    except OSError:
        mascara = os.umask(0)
        os.umask(mascara)
        return 0o666 & ~mascara


def _apaga(caminho):
    try:
        os.unlink(caminho)
    except OSError:
        pass


def _conteudo(caminho):
    with open(caminho, "rb") as arquivo:
        return arquivo.read()


def _temporario(destino, conteudo):
    """Grava o conteúdo num arquivo temporário ao lado do destino (mesma pasta: a troca de nome é atômica)."""
    pasta, nome = os.path.split(destino)
    descritor, temporario = tempfile.mkstemp(dir=pasta, prefix="." + nome + ".", suffix=".tmp")
    try:
        with os.fdopen(descritor, "wb") as arquivo:
            arquivo.write(conteudo)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.chmod(temporario, _modo(destino))
    except BaseException:
        _apaga(temporario)
        raise
    return temporario


class Lote:
    """Gravação em lote, tudo ou nada: prepara todos os arquivos e só então troca os nomes.

    Erro em qualquer ponto: nenhum arquivo muda e nenhum temporário fica. O conteúdo é convertido já no
    .json() e no .texto(): objeto que não cabe em JSON falha antes de qualquer gravação em disco."""

    def __init__(self):
        self._itens = []

    def json(self, caminho, objeto):
        self.texto(caminho, json_texto(objeto))

    def texto(self, caminho, texto):
        self._itens.append((os.path.abspath(caminho), texto.encode("utf-8")))

    def caminhos(self):
        return [caminho for caminho, _ in self._itens]

    def grava(self):
        prontos, pastas, antes, trocados = [], [], {}, []
        try:
            for destino, conteudo in self._itens:
                pasta = os.path.dirname(destino)
                while not os.path.isdir(pasta):  # anota as pastas criadas, para desfazer se der erro
                    pastas.insert(0, pasta)
                    pasta = os.path.dirname(pasta)
                os.makedirs(os.path.dirname(destino), exist_ok=True)
                prontos.append((_temporario(destino, conteudo), destino))
            for _, destino in prontos:  # guarda o que havia: se uma troca falhar no meio, dá para devolver
                antes[destino] = _conteudo(destino) if os.path.lexists(destino) else None
            for temporario, destino in prontos:
                os.replace(temporario, destino)
                trocados.append(destino)
        except BaseException:
            for destino in trocados:
                if antes[destino] is None:
                    _apaga(destino)
                else:
                    try:
                        os.replace(_temporario(destino, antes[destino]), destino)
                    except OSError:  # o erro que conta é o primeiro, que sobe logo abaixo
                        pass
            for temporario, _ in prontos:
                _apaga(temporario)
            for pasta in reversed(pastas):
                try:
                    os.rmdir(pasta)
                except OSError:
                    pass
            raise
        self._itens = []


def grava_texto(caminho, texto):
    """Grava texto em UTF-8, sem BOM, de forma atômica. O texto sai como veio (ponha a quebra de linha do fim)."""
    lote = Lote()
    lote.texto(caminho, texto)
    lote.grava()


def grava_json(caminho, objeto):
    grava_texto(caminho, json_texto(objeto))


# ---------------------------------------------------------------- URL (ESQUEMA, seção 0)

# Depois do esquema, nada de espaço, de caractere de controle nem de caractere invisível de direção de
# texto ou de largura zero (ESQUEMA, seção 0, "URL"): a URL vai para a saída padrão, para os arquivos
# de trabalho e para a edição, e um desses caracteres faz o endereço parecer outro para quem lê.
# Também nada de aspas, apóstrofo, crase, cifrão nem barra invertida: a URL pode acabar numa linha de
# comando entre aspas, onde esses sinais fecham a aspa ou rodam comando; e o navegador lê a barra
# invertida como barra, e veria outro site no mesmo texto.
_RE_URL = re.compile(r"https?://[^\s\x00-\x1f\x7f" + "\"'`$" + r"\\\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff]+")
_RE_HTTP = re.compile(r"https?://", re.I)


def site_de(url):
    """O nome do site de uma URL, em minúsculas, sem `www.` e sem porta. Sem nome de site: texto vazio."""
    try:
        nome = (urlsplit(str(url)).hostname or "").lower()
    except ValueError:
        return ""
    return nome[4:] if nome.startswith("www.") else nome


def url_valida(valor):
    """URL: começa com http:// ou https://, não tem espaço, caractere de controle, caractere invisível, aspas,
    apóstrofo, crase, cifrão nem barra invertida, tem até 500 caracteres, tem nome de site e não tem usuário
    nem senha (`usuário@` antes do nome do site)."""
    if not (isinstance(valor, str) and len(valor) <= 500 and _RE_URL.fullmatch(valor) is not None
            and site_de(valor) != ""):
        return False
    try:
        partes = urlsplit(valor)
        return partes.username is None and partes.password is None
    except ValueError:
        return False


def site_bate(site, nomes):
    """O site (o que site_de devolve) é igual a um nome da lista, ou termina em ponto mais ele.

    `gov.br.exemplo.com` não bate com `gov.br`; `www.gov.br` e `planalto.gov.br` batem."""
    nomes = [nomes] if isinstance(nomes, str) else nomes
    return bool(site) and any(bool(nome) and (site == nome or site.endswith("." + nome)) for nome in nomes)


def url_bate(url, nomes):
    return site_bate(site_de(url), nomes)


def sem_rastreio(url):
    """A URL sem `#…` e sem parâmetros `utm_`, com o resto como veio. É endereço que se pode gravar."""
    texto = str(url).strip().split("#", 1)[0]
    antes, marca, consulta = texto.partition("?")
    if not marca:
        return texto
    consulta = "&".join(p for p in consulta.split("&") if not p.lower().startswith("utm_"))
    return antes + ("?" + consulta if consulta else "")


def endereco_limpo(url):
    """Chave para comparar duas URLs: nome do site em minúsculas, http igual a https, sem `www.`, sem `#…`,
    sem parâmetros `utm_`, sem barra no fim. Sai SEM o esquema, de propósito: não é endereço para gravar.

    A porta fica como veio (`:443` não é tirada). O que não começa com http(s):// só perde `#…` e `utm_`."""
    texto = sem_rastreio(url)
    esquema = _RE_HTTP.match(texto)
    if not esquema:
        return texto
    antes, marca, consulta = texto[esquema.end():].partition("?")
    local, barra, caminho = antes.partition("/")
    usuario, arroba, nome = local.rpartition("@")
    nome = nome.lower()
    nome = nome[4:] if nome.startswith("www.") else nome
    return usuario + arroba + nome + (barra + caminho).rstrip("/") + marca + consulta
