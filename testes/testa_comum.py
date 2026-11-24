#!/usr/bin/env python3
"""Testes de ferramentas/comum.py, a base comum das quatro ferramentas.

Rodar da raiz do repositório: python3 -B testes/testa_comum.py
Nada é gravado dentro do repositório: tudo vai para uma pasta temporária (respeita $TMPDIR).
"""
import ast
import contextlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

sys.dont_write_bytecode = True
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "ferramentas"))

import comum  # noqa: E402


def guarda():
    """O trecho da guarda de versão, tirado da docstring do comum: testa-se o que as ferramentas copiam."""
    inicio = comum.__doc__.index("    # --- guarda de versão: início ---")
    fim = comum.__doc__.index("# --- guarda de versão: fim ---") + len("# --- guarda de versão: fim ---")
    return textwrap.dedent(comum.__doc__[inicio:fim]) + "\n"


FALSA = '''"""Ferramenta de mentira, só para os testes do comum."""
%s
import comum  # noqa: E402


def principal(argv):
    an = comum.opcoes("Ferramenta de mentira, com acentuação.")
    an.add_argument("--modo", default="ok")
    args = comum.prepara(an.parse_args(argv))
    saida = comum.Saida(args.json)
    saida.linha("dia %%s" %% args.dia)
    saida.linha("raiz %%s" %% args.raiz)
    saida.linha("agora %%s" %% comum.agora_texto())
    saida.dado("dia", args.dia)
    if args.modo == "explode":
        raise RuntimeError("deu ruim\\nna segunda linha")
    if args.modo == "falha":
        raise comum.Falha("sem rede: 0 feeds", comum.SEM_REDE)
    if args.modo == "mudo":
        return comum.OK
    if args.modo == "muito":
        for numero in range(20000):
            saida.linha("linha %%d, com acentuação" %% numero)
    if args.modo == "parcial":
        return saida.fecha("PARCIAL 5 feeds, 2 partidos")
    return saida.fecha("OK tudo certo, ação concluída")


if __name__ == "__main__":
    comum.executa(principal)
'''

VELHA = '''import sys
sys.version_info = (3, 9, 18, "final", 0)
%s
import comum  # noqa: E402
print("não devia chegar aqui")
'''


class ComPasta(unittest.TestCase):
    """Cada teste ganha uma pasta temporária com um repositório de mentira: repo/ferramentas/."""

    def setUp(self):
        temporaria = tempfile.TemporaryDirectory(prefix="info-comum-")
        self.addCleanup(temporaria.cleanup)
        self.pasta = os.path.realpath(temporaria.name)
        self.repo = os.path.join(self.pasta, "repo")
        self.ferramentas = os.path.join(self.repo, "ferramentas")
        self.trabalho = os.path.join(self.pasta, "trabalho")
        os.makedirs(self.ferramentas)
        shutil.copy(os.path.join(RAIZ, "ferramentas", "comum.py"), self.ferramentas)
        self.falsa = self.grava(os.path.join(self.ferramentas, "falsa.py"), FALSA % guarda())

    def grava(self, caminho, texto):
        with open(caminho, "w", encoding="utf-8", newline="\n") as arquivo:
            arquivo.write(texto)
        return caminho

    def roda(self, *argumentos, script=None, **ambiente):
        """Chama a ferramenta de mentira como a rotina chama: python3 ARQUIVO, sem -B. Devolve (código, saída, erro)."""
        base = {k: v for k, v in os.environ.items() if k not in ("PYTHONDONTWRITEBYTECODE", "INFO_AGORA")}
        base.update(ambiente)
        feito = subprocess.run([sys.executable, script or self.falsa] + list(argumentos), env=base,
                               cwd=self.pasta, stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
        return feito.returncode, feito.stdout.decode("utf-8"), feito.stderr.decode("utf-8", "replace")

    def tudo(self):
        """Todos os arquivos e pastas debaixo da pasta temporária, em caminho relativo."""
        achados = []
        for pasta, subpastas, nomes in os.walk(self.pasta):
            achados += [os.path.relpath(os.path.join(pasta, n), self.pasta) for n in subpastas + nomes]
        return sorted(achados)


class TestaGuarda(ComPasta):
    def test_python_velho_para_com_falha_interna(self):
        # Não há Python 3.9 nesta máquina: o script de mentira troca sys.version_info antes da guarda.
        velha = self.grava(os.path.join(self.ferramentas, "velha.py"), VELHA % guarda())
        codigo, saida, erro = self.roda(script=velha)
        self.assertEqual((codigo, saida, erro), (1, "FALHA interna: Python 3.10 ou mais novo\n", ""))

    def test_sintaxe_que_o_python_3_7_le(self):
        ast.parse(guarda(), feature_version=(3, 7))
        self.assertNotIn("comum", guarda().replace("# ---", ""), "a guarda vem antes de importar o comum")

    def test_python_atual_segue_sem_gravar_bytecode(self):
        codigo, saida, erro = self.roda("--trabalho", self.trabalho, INFO_AGORA="2026-11-20T21:00:00Z")
        self.assertEqual((codigo, erro), (0, ""), saida)
        self.assertIn("raiz %s\n" % self.repo, saida, "--raiz padrão é a pasta acima de ferramentas/")
        self.assertEqual([c for c in self.tudo() if "__pycache__" in c or c.endswith(".pyc")], [])


class TestaEsqueleto(ComPasta):
    def test_o_esqueleto_da_docstring_roda_como_esta(self):
        inicio = comum.__doc__.index("    import comum  # noqa: E402")
        esqueleto = self.grava(os.path.join(self.ferramentas, "esqueleto.py"),
                               guarda() + textwrap.dedent(comum.__doc__[inicio:]))
        linhas = textwrap.dedent(comum.__doc__[inicio:]).strip().count("\n") + 1
        self.assertTrue(15 <= linhas <= 25, "o exemplo de uso tem %d linhas" % linhas)
        os.mkdir(os.path.join(self.repo, "dados"))
        regua = os.path.join(self.repo, "dados", "regua.json")
        comum.grava_json(regua, {"dominios": ["energia", "alimentos"]})
        ambiente = {"INFO_AGORA": "2026-11-20T21:00:00Z"}
        codigo, saida, erro = self.roda("--trabalho", self.trabalho, script=esqueleto, **ambiente)
        self.assertEqual((codigo, saida, erro), (0, "dia 2026-11-20, 2 domínios\nOK 1 arquivo gravado\n", ""))
        self.assertEqual(comum.le_json(os.path.join(self.trabalho, "exemplo.json")),
                         {"dia": "2026-11-20", "gerada_em": "2026-11-20T21:00:00Z"})
        comum.grava_json(regua, {"temas": []})
        codigo, saida, erro = self.roda("--trabalho", self.trabalho, script=esqueleto, **ambiente)
        self.assertEqual((codigo, saida, erro), (1, "FALHA dados/regua.json sem a chave dominios\n", ""))


class TestaRelogio(ComPasta):
    def test_info_agora_valido(self):
        codigo, saida, _ = self.roda("--trabalho", self.trabalho, INFO_AGORA="2026-11-20T21:00:00Z")
        self.assertEqual(codigo, 0)
        self.assertIn("agora 2026-11-20T21:00:00Z\n", saida)
        self.assertIn("dia 2026-11-20\n", saida)

    def test_info_agora_ilegivel(self):
        for valor in ("ontem", "", "2026-11-20 21:00:00", "2026-11-20T21:00:00", "2026-11-20T21:00:00+00:00",
                      "2026-02-30T00:00:00Z", "2026-11-20T24:00:00Z", "2026-11-20T21:00:00Z\n"):
            with self.subTest(valor=valor):
                codigo, saida, erro = self.roda("--trabalho", self.trabalho, INFO_AGORA=valor)
                self.assertEqual((codigo, saida, erro), (2, "FALHA uso: INFO_AGORA ilegível\n", ""))
                self.assertFalse(os.path.exists(self.trabalho), "erro de uso não grava nada")

    def test_dia_em_brasilia(self):
        casos = (
            ("2026-11-20T23:59:59Z", "2026-11-20"),  # perto da meia-noite UTC, antes
            ("2026-11-21T00:00:00Z", "2026-11-20"),  # meia-noite UTC: em Brasília ainda são 21h do dia 20
            ("2026-11-21T02:59:59Z", "2026-11-20"),  # um segundo antes da meia-noite de Brasília
            ("2026-11-21T03:00:00Z", "2026-11-21"),  # meia-noite de Brasília
            ("2027-01-01T02:59:59Z", "2026-12-31"),  # a virada do ano
            ("2028-03-01T01:00:00Z", "2028-02-29"),  # ano bissexto
        )
        for instante, dia in casos:
            with self.subTest(instante=instante):
                self.assertEqual(comum.dia_brasilia(instante), dia)
                with mock.patch.dict(os.environ, {"INFO_AGORA": instante}):
                    self.assertEqual(comum.hoje_brasilia(), dia)
                    self.assertEqual(comum.agora_texto(), instante)

    def test_dia_nao_depende_do_fuso_da_maquina(self):
        for fuso in ("Asia/Tokyo", "America/Los_Angeles", "UTC"):
            with self.subTest(fuso=fuso):
                _, saida, _ = self.roda("--trabalho", self.trabalho, INFO_AGORA="2026-11-21T02:59:59Z", TZ=fuso)
                self.assertIn("dia 2026-11-20\n", saida)

    def test_relogio_de_verdade(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("INFO_AGORA", None)
            agora = comum.agora()
        self.assertEqual(agora.utcoffset(), timedelta(0))
        self.assertEqual(agora.microsecond, 0)
        self.assertLess(abs(agora.timestamp() - time.time()), 5)

    def test_datas(self):
        for boa in ("2026-01-05", "2028-02-29", "2026-12-31"):
            self.assertTrue(comum.data_valida(boa), boa)
        for ruim in ("2026-02-29", "2026-13-01", "2026-00-10", "2026-1-05", "26-01-05", "2026-01-05\n", " 2026-01-05",
                     "2026/01/05", "05/01/2026", "２０２６-01-05", "", None, 20260105, comum.le_data("2026-01-05")):
            self.assertFalse(comum.data_valida(ruim), repr(ruim))
            if not hasattr(ruim, "year"):
                self.assertRaises(ValueError, comum.le_data, ruim)
        self.assertEqual(comum.le_data("2026-01-05").isoformat(), "2026-01-05")
        self.assertEqual(comum.dd_mm("2026-01-05"), "05/01")
        self.assertEqual(comum.dd_mm_aaaa("2026-01-05"), "05/01/2026")
        self.assertEqual(comum.dias_entre("2026-02-27", "2026-03-01"), 2)
        self.assertEqual(comum.dias_entre("2028-02-27", "2028-03-01"), 3)
        self.assertEqual(comum.dias_entre("2026-03-01", "2026-02-27"), -2)
        self.assertEqual(comum.dias_entre("2026-03-01", "2026-03-01"), 0)
        self.assertEqual(comum.soma_dias("2026-12-31", 1), "2027-01-01")
        self.assertEqual(comum.soma_dias("2026-11-20", -30), "2026-10-21")

    def test_datas_e_horas(self):
        self.assertTrue(comum.data_hora_valida("2026-11-20T21:00:00Z"))
        for ruim in ("2026-11-20T21:00:00", "2026-11-20T21:00:00+00:00", "2026-11-20 21:00:00Z", "2026-11-20T21:00Z",
                     "2026-11-20T21:00:60Z", "2026-11-20T25:00:00Z", "2026-11-31T00:00:00Z", "2026-11-20", None):
            self.assertFalse(comum.data_hora_valida(ruim), repr(ruim))
        instante = comum.le_data_hora("2026-11-20T21:04:05Z")
        self.assertEqual(instante, datetime(2026, 11, 20, 21, 4, 5, tzinfo=timezone.utc))
        self.assertEqual(comum.texto_data_hora(instante), "2026-11-20T21:04:05Z")
        em_brasilia = instante.astimezone(timezone(timedelta(hours=-3)))
        self.assertEqual(comum.texto_data_hora(em_brasilia), "2026-11-20T21:04:05Z")
        self.assertEqual(comum.texto_data_hora(datetime(2026, 11, 20, 21, 4, 5, 999)), "2026-11-20T21:04:05Z")


class TestaLinhaDeComando(ComPasta):
    def test_erro_de_uso_em_uma_linha_na_saida_padrao(self):
        casos = (["--nao-existe"], ["--dia", "2026-02-30"], ["--dia", "20/11/2026"], ["--dia"], ["sobra"],
                 ["--trab", self.trabalho], ["--trabalho", ""], ["--json=1"],
                 ["--raiz", os.path.join(self.pasta, "nao-existe")])
        for caso in casos:
            with self.subTest(caso=caso):
                codigo, saida, erro = self.roda(*caso, "--trabalho", self.trabalho)
                self.assertEqual((codigo, erro), (2, ""), saida)
                self.assertTrue(saida.startswith("FALHA uso: "), saida)
                self.assertEqual(saida.count("\n"), 1, saida)
                self.assertTrue(saida.endswith("\n"))
                self.assertNotIn("usage", saida)
                self.assertFalse(os.path.exists(self.trabalho), "erro de uso não grava nada")

    def test_mensagens_de_uso_em_portugues(self):
        an = comum.opcoes("x")
        an.add_argument("--so", choices=("python", "site"))
        an.add_argument("--motivo", required=True)
        for argumentos, trecho in ((["--motivo", "x", "--nada"], "opção desconhecida: --nada"), (["--motivo"], "--motivo pede um valor"),
                                   ([], "falta --motivo"), (["--motivo", "x", "--so", "y"], "não vale"),
                                   (["--motivo", "x", "--dia", "ontem"], "--dia: data ilegível")):
            with self.assertRaises(comum.ErroDeUso) as pego:
                an.parse_args(argumentos)
            self.assertIn(trecho, str(pego.exception))

    def test_ajuda_sai_na_saida_padrao_em_utf8(self):
        codigo, saida, erro = self.roda("-h", LC_ALL="C", LANG="C", PYTHONUTF8="0", PYTHONCOERCECLOCALE="0")
        self.assertEqual((codigo, erro), (0, ""))
        self.assertIn("Ferramenta de mentira, com acentuação.", saida)
        self.assertIn("--trabalho PASTA", saida)

    def test_opcao_tirada_e_subcomandos(self):
        sem_trabalho = comum.opcoes("x", trabalho=False)
        self.assertRaises(comum.ErroDeUso, sem_trabalho.parse_args, ["--trabalho", self.trabalho])
        args = sem_trabalho.parse_args([])
        self.assertFalse(hasattr(args, "trabalho"))
        self.assertEqual(args.raiz, RAIZ)
        an = comum.analisador("x")
        sub = an.add_subparsers(dest="comando", required=True, metavar="COMANDO")
        comum.poe_comuns(sub.add_parser("contexto"))
        comum.poe_comuns(sub.add_parser("refaz"), trabalho=False, dia=False)
        args = an.parse_args(["contexto", "--trabalho", self.trabalho, "--dia", "2026-11-20", "--json"])
        self.assertEqual((args.comando, args.trabalho, args.dia, args.json), ("contexto", self.trabalho, "2026-11-20", True))
        self.assertEqual(an.parse_args(["contexto"]).trabalho, "/tmp/info")
        for errado in ([], ["nenhum"], ["refaz", "--dia", "2026-11-20"], ["contexto", "--dia", "2026-11-31"]):
            self.assertRaises(comum.ErroDeUso, an.parse_args, errado)

    def test_padrao_do_dia(self):
        agora = {"INFO_AGORA": "2026-11-21T04:00:00Z"}  # em Brasília, 21/11 à 1h
        with mock.patch.dict(os.environ, agora):
            def prepara(argumentos, forma=comum.DIA_DO_CONTEXTO, **opcoes):
                return comum.prepara(comum.opcoes("x", **opcoes).parse_args(argumentos), forma)

            sem_arquivo = prepara(["--trabalho", self.trabalho])
            self.assertEqual((sem_arquivo.dia, sem_arquivo.dia_informado), ("2026-11-21", False))
            self.assertTrue(os.path.isdir(self.trabalho), "a pasta de trabalho é criada se faltar")
            comum.grava_json(os.path.join(self.trabalho, "contexto.json"), {"dia": "2026-11-20", "janela_horas": 36})
            self.assertEqual(prepara(["--trabalho", self.trabalho]).dia, "2026-11-20", "o dia nasce no contexto")
            self.assertEqual(comum.le_contexto(self.trabalho)["janela_horas"], 36)
            self.assertEqual(prepara(["--trabalho", self.trabalho], comum.DIA_DE_HOJE).dia, "2026-11-21")
            dado = prepara(["--trabalho", self.trabalho, "--dia", "2026-11-05"])
            self.assertEqual((dado.dia, dado.dia_informado), ("2026-11-05", True))
            self.assertEqual(prepara([], trabalho=False).dia, "2026-11-21", "sem pasta de trabalho, vale hoje")
            self.assertRaises(ValueError, prepara, ["--trabalho", self.trabalho], "amanha")
            for quebrado in ('{"dia": "2026-11-31"}', '{"janela_horas": 36}', "[]", '{"dia": '):
                self.grava(os.path.join(self.trabalho, "contexto.json"), quebrado)
                with self.assertRaises(comum.Falha, msg=quebrado) as pego:
                    prepara(["--trabalho", self.trabalho])
                self.assertIn("contexto.json", str(pego.exception))
                self.assertEqual(prepara(["--trabalho", self.trabalho, "--dia", "2026-11-05"]).dia, "2026-11-05")

    def test_pasta_de_trabalho_criada_se_faltar(self):
        funda = os.path.join(self.trabalho, "a", "b")
        codigo, saida, _ = self.roda("--trabalho", funda, INFO_AGORA="2026-11-20T21:00:00Z")
        self.assertEqual(codigo, 0, saida)
        self.assertEqual(os.listdir(funda), [], "a prova de gravação não deixa arquivo")

    def confere_recusa(self, pasta):
        codigo, saida, erro = self.roda("--trabalho", pasta, INFO_AGORA="2026-11-20T21:00:00Z")
        self.assertEqual((codigo, erro), (1, ""), saida)
        self.assertEqual(saida.count("\n"), 1, saida)
        self.assertTrue(saida.startswith("FALHA a pasta de trabalho %s não aceita gravação" % pasta), saida)
        self.assertIn("Use --trabalho", saida)

    def test_pasta_de_trabalho_que_nao_da_para_criar(self):
        arquivo = self.grava(os.path.join(self.pasta, "arquivo"), "não sou pasta\n")
        self.confere_recusa(arquivo)
        self.confere_recusa(os.path.join(arquivo, "dentro"))

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "para o root não há pasta sem gravação")
    def test_pasta_de_trabalho_sem_gravacao(self):
        fechada = os.path.join(self.pasta, "fechada")
        os.mkdir(fechada)
        os.chmod(fechada, 0o555)
        self.addCleanup(os.chmod, fechada, 0o755)
        self.confere_recusa(fechada)
        self.confere_recusa(os.path.join(fechada, "dentro"))


class TestaSaida(ComPasta):
    def no_processo(self, principal, argumentos=()):
        tela = io.StringIO()
        with contextlib.redirect_stdout(tela), contextlib.redirect_stderr(tela):
            codigo = comum.protege(principal, argumentos)
        return codigo, tela.getvalue()

    def test_ultima_linha_e_o_veredito(self):
        codigo, saida, erro = self.roda("--trabalho", self.trabalho, "--dia", "2026-11-20")
        self.assertEqual((codigo, erro), (0, ""))
        linhas = saida.split("\n")
        self.assertEqual((linhas[0], linhas[-2], linhas[-1]), ("dia 2026-11-20", "OK tudo certo, ação concluída", ""))
        codigo, saida, _ = self.roda("--trabalho", self.trabalho, "--modo", "parcial")
        self.assertEqual((codigo, saida.split("\n")[-2]), (3, "PARCIAL 5 feeds, 2 partidos"))

    def test_veredito_tem_de_ser_veredito(self):
        with contextlib.redirect_stdout(io.StringIO()) as tela:
            saida = comum.Saida()
            self.assertRaises(ValueError, saida.fecha, "Tudo certo")
            self.assertRaises(ValueError, saida.fecha, "OK tudo certo", comum.FALHA)
            self.assertRaises(ValueError, saida.fecha, "FALHA 2 erros", comum.OK)
            self.assertEqual(tela.getvalue(), "", "veredito recusado não imprime nada")
            saida.linha("duas\nlinhas")
            self.assertEqual(saida.fecha("FALHA sem rede:\n0 feeds", comum.SEM_REDE), 4)
        self.assertEqual(tela.getvalue(), "duas\nlinhas\nFALHA sem rede: 0 feeds\n")

    def test_utf8_com_a_maquina_em_locale_c_ou_posix(self):
        for locale in ("C", "POSIX"):
            with self.subTest(locale=locale):
                codigo, saida, erro = self.roda("--trabalho", self.trabalho, LC_ALL=locale, LANG=locale,
                                                PYTHONUTF8="0", PYTHONCOERCECLOCALE="0", PYTHONIOENCODING="")
                self.assertEqual((codigo, erro), (0, ""))
                self.assertTrue(saida.endswith("OK tudo certo, ação concluída\n"), saida)

    def test_json_no_lugar_do_texto(self):
        codigo, saida, erro = self.roda("--trabalho", self.trabalho, "--dia", "2026-11-20", "--json")
        self.assertEqual((codigo, erro), (0, ""))
        objeto = json.loads(saida)
        self.assertEqual(list(objeto), ["ok", "codigo", "veredito", "linhas", "dia"])
        self.assertEqual((objeto["ok"], objeto["codigo"], objeto["dia"]), (True, 0, "2026-11-20"))
        self.assertEqual(objeto["veredito"], "OK tudo certo, ação concluída")
        self.assertEqual(objeto["linhas"][0], "dia 2026-11-20")
        self.assertIn("ação", saida, "acento legível, sem \\u")

    def test_json_tambem_na_falha(self):
        for modo, codigo_certo, veredito in (("explode", 1, "FALHA interna: RuntimeError: deu ruim na segunda linha"),
                                             ("falha", 4, "FALHA sem rede: 0 feeds")):
            codigo, saida, erro = self.roda("--trabalho", self.trabalho, "--json", "--modo", modo)
            objeto = json.loads(saida)
            self.assertEqual((codigo, erro, objeto["ok"], objeto["codigo"]), (codigo_certo, "", False, codigo_certo))
            self.assertEqual(objeto["veredito"], veredito)

    def test_json_antes_da_primeira_saida_e_erro_de_uso_sempre_em_texto(self):
        arquivo = self.grava(os.path.join(self.pasta, "arquivo"), "não sou pasta\n")
        codigo, saida, erro = self.roda("--json", "--trabalho", arquivo)
        objeto = json.loads(saida)
        self.assertEqual((codigo, erro, objeto["ok"], objeto["codigo"], objeto["linhas"]), (1, "", False, 1, []))
        self.assertTrue(objeto["veredito"].startswith("FALHA a pasta de trabalho"), saida)
        self.assertIn("Use --trabalho", objeto["veredito"])
        codigo, saida, erro = self.roda("--json", "--trabalho", self.trabalho, "--nao-existe")
        self.assertEqual((codigo, saida, erro), (2, "FALHA uso: opção desconhecida: --nao-existe\n", ""))
        codigo, saida, erro = self.roda("--json", "--trabalho", self.trabalho, INFO_AGORA="amanhã")
        self.assertEqual((codigo, saida, erro), (2, "FALHA uso: INFO_AGORA ilegível\n", ""))

    def test_json_com_objeto_proprio(self):
        proprio = {"ok": False, "erros": [{"regra": "R08", "caminho": "radar[2]", "mensagem": "é 'alta'"}], "avisos": []}

        def principal(argv):
            saida = comum.Saida(em_json=True)
            saida.linha("ERRO R08 radar[2]: é 'alta'")
            return saida.fecha("FALHA 1 erro, 0 avisos", objeto=proprio)

        codigo, saida = self.no_processo(principal)
        self.assertEqual((codigo, json.loads(saida)), (1, proprio))

    def test_excecao_solta_vira_falha_interna(self):
        codigo, saida, erro = self.roda("--trabalho", self.trabalho, "--modo", "explode")
        self.assertEqual((codigo, erro), (1, ""), "sem rastro de pilha na saída de erro")
        linhas = saida.split("\n")
        self.assertEqual(linhas[-2:], ["FALHA interna: RuntimeError: deu ruim na segunda linha", ""])
        self.assertEqual(linhas[0][:4], "dia ", "o que já estava juntado sai antes")
        self.assertNotIn("Traceback", saida)
        codigo, saida = self.no_processo(lambda argv: 1 // 0)
        self.assertEqual((codigo, saida), (1, "FALHA interna: ZeroDivisionError: integer division or modulo by zero\n"))
        codigo, saida = self.no_processo(lambda argv: [][0] if argv else exec("raise KeyError()"))
        self.assertEqual((codigo, saida), (1, "FALHA interna: KeyError\n"))

    def test_falha_prevista_e_codigo(self):
        codigo, saida, erro = self.roda("--trabalho", self.trabalho, "--modo", "falha")
        self.assertEqual((codigo, erro, saida.split("\n")[-2]), (4, "", "FALHA sem rede: 0 feeds"))

    def test_ferramenta_sem_veredito_ou_com_codigo_torto(self):
        codigo, saida, erro = self.roda("--trabalho", self.trabalho, "--modo", "mudo")
        self.assertEqual((codigo, erro), (1, ""))
        self.assertEqual(saida.split("\n")[-2], "FALHA interna: RuntimeError: a ferramenta terminou sem veredito")
        for torto in (None, 7, True, "0"):
            codigo, saida = self.no_processo(lambda argv, torto=torto: torto)
            self.assertEqual(codigo, 1)
            self.assertTrue(saida.startswith("FALHA interna: RuntimeError: código de saída fora da tabela"), saida)

    def test_interrupcao_sem_sujeira(self):
        def principal(argv):
            comum.Saida().linha("ia começar")
            raise KeyboardInterrupt

        self.assertEqual(self.no_processo(principal), (1, "ia começar\nFALHA interrompida\n"))

    def test_cano_fechado_sem_sujeira(self):
        base = {k: v for k, v in os.environ.items() if k != "INFO_AGORA"}
        processo = subprocess.Popen([sys.executable, self.falsa, "--trabalho", self.trabalho, "--modo", "muito"],
                                    env=base, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(processo.stdout.read(4), b"dia ")
        processo.stdout.close()  # quem lia foi embora com a saída pela metade (como em "| head -1")
        erro = processo.stderr.read()
        processo.stderr.close()
        self.assertEqual((processo.wait(timeout=60), erro), (0, b""))


class TestaArquivos(ComPasta):
    def le_falha(self, conteudo):
        caminho = os.path.join(self.pasta, "entrada.json")
        with open(caminho, "wb") as arquivo:
            arquivo.write(conteudo)
        with self.assertRaises(comum.Falha) as pego:
            comum.le_json(caminho)
        self.assertEqual(pego.exception.codigo, comum.FALHA)
        self.assertTrue(str(pego.exception).startswith(caminho + ": "), str(pego.exception))
        return str(pego.exception)[len(caminho) + 2:]

    def test_le_json(self):
        caminho = self.grava(os.path.join(self.pasta, "bom.json"), '{"título": "ação", "n": [1, 2.5, null, "NaN"]}')
        self.assertEqual(comum.le_json(caminho), {"título": "ação", "n": [1, 2.5, None, "NaN"]})
        self.assertEqual(list(comum.le_json(self.grava(caminho, '{"z": 1, "a": 2}'))), ["z", "a"])

    def test_le_json_quebrado_diz_arquivo_linha_e_coluna(self):
        self.assertRegex(self.le_falha(b'{\n  "a": 1,\n  "b": }\n'), r"^linha 3, coluna 8: JSON ilegível \(.+\)$")
        self.assertRegex(self.le_falha(b'{"a": 1,}'), r"^linha 1, coluna 9: JSON ilegível")
        self.assertRegex(self.le_falha(b''), r"^linha 1, coluna 1: JSON ilegível")
        self.assertRegex(self.le_falha(b'{"a": 1}\n{"b": 2}\n'), r"^linha 2, coluna 1: JSON ilegível")

    def test_le_json_recusa_nan_e_infinity(self):
        self.assertEqual(self.le_falha(b'{\n  "nota": "NaN e Infinity",\n  "valor": NaN\n}\n'),
                         "linha 3, coluna 12: NaN não vale em JSON")
        self.assertEqual(self.le_falha(b'[1, Infinity]'), "linha 1, coluna 5: Infinity não vale em JSON")
        self.assertEqual(self.le_falha(b'[1,\n -Infinity]'), "linha 2, coluna 2: -Infinity não vale em JSON")

    def test_le_json_recusa_o_que_nao_e_utf8_e_o_bom(self):
        self.assertEqual(self.le_falha('{\n "a": "ação"}'.encode("latin-1")), "linha 2, coluna 9: não é UTF-8")
        self.assertRegex(self.le_falha(b'\xef\xbb\xbf{"a": 1}'), r"^linha 1, coluna 1: começa com BOM")

    def test_le_json_arquivo_que_falta(self):
        falta = os.path.join(self.pasta, "falta.json")
        with self.assertRaises(comum.Falha) as pego:
            comum.le_json(falta)
        self.assertEqual(str(pego.exception), falta + ": o arquivo não existe")
        self.assertIsNone(comum.le_json(falta, se_faltar=None))
        self.assertEqual(comum.le_json(falta, se_faltar=[]), [])
        self.assertRaises(comum.Falha, comum.le_json, self.pasta, None)  # pasta não é arquivo que falta

    def test_formato_do_json_gravado(self):
        caminho = os.path.join(self.pasta, "saida.json")
        comum.grava_json(caminho, {"z": "ação · “aspas”", "a": [1, {"b": None, "c": True}], "vazio": []})
        with open(caminho, "rb") as arquivo:
            bruto = arquivo.read()
        certo = '{\n  "z": "ação · “aspas”",\n  "a": [\n    1,\n    {\n      "b": null,\n      "c": true\n    }\n  ],\n  "vazio": []\n}\n'
        self.assertEqual(bruto, certo.encode("utf-8"))  # sem BOM, acento legível, recuo de 2, ordem das chaves
        self.assertEqual(os.listdir(self.pasta).count("saida.json"), 1)
        self.assertEqual([n for n in os.listdir(self.pasta) if n.endswith(".tmp")], [])

    def test_mesma_entrada_mesmos_bytes(self):
        edicao = {"data": "2026-11-20", "resumo": "Petróleo sobe 4%; dólar a R$ 5,89.", "itens": [{"id": "p1", "x": 0.1}]}
        um, dois = os.path.join(self.pasta, "um.json"), os.path.join(self.pasta, "dois.json")
        comum.grava_json(um, edicao)
        comum.grava_json(dois, comum.le_json(um))
        comum.grava_json(um, edicao)
        with open(um, "rb") as a, open(dois, "rb") as b:
            self.assertEqual(a.read(), b.read())

    def test_gravacao_atomica(self):
        caminho = os.path.join(self.pasta, "nova", "pasta", "texto.md")
        comum.grava_texto(caminho, "primeira versão\n")
        os.chmod(caminho, 0o640)
        copia = os.path.join(self.pasta, "copia")
        os.link(caminho, copia)  # outro nome para o mesmo arquivo: mostra se ele foi reescrito no lugar
        comum.grava_texto(caminho, "segunda versão\n")
        with open(caminho, encoding="utf-8") as novo, open(copia, encoding="utf-8") as velho:
            self.assertEqual((novo.read(), velho.read()), ("segunda versão\n", "primeira versão\n"))
        self.assertEqual(stat.S_IMODE(os.stat(caminho).st_mode), 0o640, "a troca mantém as permissões")
        self.assertEqual(os.listdir(os.path.dirname(caminho)), ["texto.md"], "nenhum temporário sobra")
        mascara = os.umask(0)
        os.umask(mascara)
        outro = os.path.join(self.pasta, "outro.txt")
        comum.grava_texto(outro, "x")
        self.assertEqual(stat.S_IMODE(os.stat(outro).st_mode), 0o666 & ~mascara, "arquivo novo sai com permissão comum")

    def test_gravacao_que_falha_nao_muda_nada(self):
        caminho = os.path.join(self.pasta, "saida.json")
        comum.grava_json(caminho, {"a": 1})
        antes = self.tudo()
        self.assertRaises(ValueError, comum.grava_json, caminho, {"a": float("nan")})
        self.assertRaises(TypeError, comum.grava_json, caminho, {"a": {1, 2}})
        self.assertRaises(OSError, comum.grava_texto, self.pasta, "o destino é uma pasta\n")
        self.assertRaises(OSError, comum.grava_texto, os.path.join(caminho, "dentro.txt"), "o pai é um arquivo\n")
        self.assertEqual(comum.le_json(caminho), {"a": 1})
        self.assertEqual(self.tudo(), antes)

    def monta_lote(self):
        """Três arquivos que já existem e um lote que mexe em dois deles e cria dois novos."""
        self.a, self.b = os.path.join(self.repo, "edicoes", "indice.json"), os.path.join(self.repo, "feed.xml")
        self.novo = os.path.join(self.repo, "edicoes", "2026-11-20.json")
        self.fundo = os.path.join(self.repo, "pasta", "nova", "texto.md")
        comum.grava_json(self.a, {"versao": "antiga"})
        comum.grava_texto(self.b, "<feed>antigo</feed>\n")
        lote = comum.Lote()
        lote.json(self.a, {"versao": "nova"})
        lote.json(self.novo, {"data": "2026-11-20"})
        lote.texto(self.fundo, "# edição\n")
        lote.texto(self.b, "<feed>novo</feed>\n")
        return lote

    def test_lote_grava_tudo(self):
        lote = self.monta_lote()
        self.assertEqual(lote.caminhos(), [self.a, self.novo, self.fundo, self.b])
        self.assertEqual(comum.le_json(self.a), {"versao": "antiga"}, "antes do .grava() nada muda")
        self.assertFalse(os.path.exists(self.novo))
        lote.grava()
        self.assertEqual(comum.le_json(self.a), {"versao": "nova"})
        self.assertEqual(comum.le_json(self.novo), {"data": "2026-11-20"})
        with open(self.fundo, encoding="utf-8") as fundo, open(self.b, encoding="utf-8") as b:
            self.assertEqual((fundo.read(), b.read()), ("# edição\n", "<feed>novo</feed>\n"))
        self.assertEqual([c for c in self.tudo() if c.endswith(".tmp")], [])

    def confere_lote_desfeito(self, antes):
        self.assertEqual(self.tudo(), antes, "nenhum arquivo novo, nenhum temporário, nenhuma pasta a mais")
        self.assertEqual(comum.le_json(self.a), {"versao": "antiga"})
        with open(self.b, encoding="utf-8") as b:
            self.assertEqual(b.read(), "<feed>antigo</feed>\n")

    def test_lote_com_falha_na_preparacao(self):
        lote = self.monta_lote()
        lote.texto(os.path.join(self.b, "dentro.txt"), "o pai deste é um arquivo: não dá para criar\n")
        lote.texto(os.path.join(self.repo, "depois.txt"), "este nem chega a ser preparado\n")
        antes = self.tudo()
        self.assertRaises(OSError, lote.grava)
        self.confere_lote_desfeito(antes)

    def test_lote_com_destino_que_e_pasta(self):
        lote = self.monta_lote()
        lote.texto(self.ferramentas, "o destino é uma pasta\n")
        antes = self.tudo()
        self.assertRaises(OSError, lote.grava)
        self.confere_lote_desfeito(antes)

    def test_lote_com_falha_no_meio_das_trocas(self):
        troca_de_verdade = os.replace
        for defeito in (OSError("disco cheio"), KeyboardInterrupt()):
            with self.subTest(defeito=type(defeito).__name__):
                lote = self.monta_lote()
                antes = self.tudo()
                feitas = []

                def troca(origem, destino):
                    feitas.append(destino)
                    if len(feitas) == 3:  # as duas primeiras trocas já valeram: têm de ser desfeitas
                        raise defeito
                    return troca_de_verdade(origem, destino)

                with mock.patch.object(comum.os, "replace", troca):
                    self.assertRaises(type(defeito), lote.grava)
                self.assertEqual(feitas[:3], [self.a, self.novo, self.fundo])
                self.confere_lote_desfeito(antes)

    def test_lote_recusa_na_hora_o_que_nao_cabe_em_json(self):
        lote = self.monta_lote()
        antes = self.tudo()
        self.assertRaises(ValueError, lote.json, self.novo, {"valor": float("inf")})
        self.assertRaises(UnicodeEncodeError, lote.texto, self.novo, "meia letra: \ud83d")
        self.confere_lote_desfeito(antes)


class TestaUrl(unittest.TestCase):
    def test_url_valida(self):
        longa = "https://exemplo.invalid/" + "a" * 476
        self.assertEqual(len(longa), 500)
        for boa in ("https://exemplo.invalid/a", "http://exemplo.invalid", "https://www.exemplo.invalid:8443/a?b=1#c",
                    "https://exemplo.invalid/ação", longa):
            self.assertTrue(comum.url_valida(boa), boa)
        for ruim in (longa + "a", "https://exemplo.invalid/a b", "https://exemplo.invalid/a\n", " https://exemplo.invalid/a",
                     "https://exemplo.invalid/a\tb", "https://exemplo.invalid/a b", "https://", "https:///caminho",
                     "https://?a=1", "https://#a", "https://:8080/a", "https://www./a", "ftp://exemplo.invalid/a",
                     "HTTPS://exemplo.invalid/a", "//exemplo.invalid/a", "exemplo.invalid/a", "https:/exemplo.invalid",
                     "javascript:alert(1)", "https://[exemplo/a", "", None, 123, ["https://exemplo.invalid/a"]):
            self.assertFalse(comum.url_valida(ruim), repr(ruim))

    def test_url_valida_recusa_sinais_de_shell_barra_invertida_e_usuario(self):
        """ESQUEMA, seção 0, "URL": nada de aspas, apóstrofo, crase, cifrão nem barra invertida, e nada de
        usuário ou senha antes do nome do site. A barra invertida faz o Python e o navegador lerem sites
        diferentes no mesmo texto; os outros sinais fecham a aspa ou rodam comando numa linha de shell."""
        for ruim in ("https://exemplo.invalid/a'b", 'https://exemplo.invalid/a"b', "https://exemplo.invalid/a`id`",
                     "https://exemplo.invalid/$(id)", "https://exemplo.invalid/a?b=$HOME", "https://exemplo.invalid/a\\b",
                     "https://golpe.invalid\\@www.exemplo.invalid/a", "https://alguem@exemplo.invalid/a",
                     "https://alguem:senha@exemplo.invalid/a", "https://:senha@exemplo.invalid/a"):
            self.assertFalse(comum.url_valida(ruim), repr(ruim))
        self.assertEqual(comum.site_de("https://golpe.invalid\\@www.exemplo.invalid/a"), "exemplo.invalid",
                         "é por isso que a barra invertida sai: o Python lê um site, o navegador lê outro")
        # arroba no caminho não é usuário: continua valendo
        for boa in ("https://exemplo.invalid/@perfil/a", "https://exemplo.invalid/a?b=c@d", "https://exemplo.invalid/a(b)!*,;=+&"):
            self.assertTrue(comum.url_valida(boa), repr(boa))

    def test_url_valida_recusa_controle_e_invisivel(self):
        """ESQUEMA, seção 0, "URL": nada de caractere de controle (U+0000 a U+001F e U+007F), nem dos invisíveis
        de direção de texto e de largura zero (U+200B a U+200F, U+202A a U+202E, U+2060 a U+2064, U+2066 a
        U+2069 e U+FEFF), em qualquer ponto da URL."""
        proibidos = [chr(c) for c in range(0x00, 0x20)] + ["\x7f"]
        for inicio, fim in ((0x200B, 0x200F), (0x202A, 0x202E), (0x2060, 0x2064), (0x2066, 0x2069)):
            proibidos += [chr(c) for c in range(inicio, fim + 1)]
        proibidos.append("\ufeff")
        self.assertEqual(len(proibidos), 33 + 5 + 5 + 5 + 4 + 1)
        for caractere in proibidos:
            for url in ("https://exemplo.invalid/a" + caractere + "b", "https://exemplo.invalid/a" + caractere,
                        "https://exemplo" + caractere + ".invalid/a", "https://exemplo.invalid/a?b=" + caractere):
                self.assertFalse(comum.url_valida(url), repr(url))
        # o que fica de fora da lista continua valendo: acento, outra escrita, sinal comum
        for boa in ("https://exemplo.invalid/ação", "https://exemplo.invalid/путь", "https://exemplo.invalid/a~b_c-d.e%20",
                    "https://exemplo.invalid/e\u0301", "https://exemplo.invalid/a\u2065b"):
            self.assertTrue(comum.url_valida(boa), repr(boa))

    def test_site_de_uma_url(self):
        casos = (
            ("https://www.exemplo.com/a", "exemplo.com"),  # o exemplo do ESQUEMA, seção 0
            ("HTTPS://WWW.Exemplo.INVALID/A", "exemplo.invalid"),
            ("https://exemplo.invalid:8443/a", "exemplo.invalid"),
            ("http://www.exemplo.invalid:80", "exemplo.invalid"),
            ("https://noticias.exemplo.invalid/a", "noticias.exemplo.invalid"),
            ("https://www2.exemplo.invalid/a", "www2.exemplo.invalid"),
            ("https://alguem:senha" + "@" + "www.exemplo.invalid/a", "exemplo.invalid"),  # usuário na URL
            ("https://exemplo.invalid?a=1", "exemplo.invalid"),
            ("https:///caminho", ""), ("https://", ""), ("exemplo.invalid/a", ""), ("https://[exemplo/a", ""),
            ("", ""), (None, ""),
        )
        for url, site in casos:
            self.assertEqual(comum.site_de(url), site, url)

    def test_site_bate(self):
        lista = ["gov.br", "exemplo.invalid"]
        for site in ("gov.br", "planalto.gov.br", "www.gov.br", "a.b.exemplo.invalid"):
            self.assertTrue(comum.site_bate(site, lista), site)
        for site in ("gov.br.exemplo.com", "gov.br.exemplo.org", "xgov.br", "br", "gov", "exemplo.invalid.br", ".", ""):
            self.assertFalse(comum.site_bate(site, lista), site)
        self.assertTrue(comum.site_bate("planalto.gov.br", "gov.br"), "um nome só também vale")
        self.assertFalse(comum.site_bate("planalto.gov.br", "gov"), "texto sozinho não é lista de letras")
        self.assertFalse(comum.site_bate("gov.br", []))
        self.assertFalse(comum.site_bate("gov.br", ["", "com"]))

    def test_url_bate(self):
        lista = ["gov.br"]
        for url in ("https://www.gov.br/pt-br", "HTTPS://WWW.Planalto.GOV.BR/x", "http://dados.gov.br:8080/a?b=1#c"):
            self.assertTrue(comum.url_bate(url, lista), url)
        for url in ("https://gov.br.exemplo.com/a", "https://exemplo.com/gov.br", "https://exemplo.com/?site=gov.br",
                    "https://gov.br" + "@" + "exemplo.com/", "gov.br", ""):
            self.assertFalse(comum.url_bate(url, lista), url)

    def test_endereco_limpo_iguala(self):
        iguais = ("https://exemplo.invalid/a/b?id=7", "http://exemplo.invalid/a/b?id=7",
                  "HTTPS://WWW.Exemplo.INVALID/a/b?id=7", "https://www.exemplo.invalid/a/b/?id=7#topo",
                  "https://exemplo.invalid/a/b?utm_source=x&id=7&utm_medium=y", "http://exemplo.invalid/a/b//?id=7&UTM_campaign=z#x",
                  "  https://exemplo.invalid/a/b?id=7\n")
        for url in iguais:
            self.assertEqual(comum.endereco_limpo(url), "exemplo.invalid/a/b?id=7", url)
        for url in ("https://exemplo.invalid", "https://exemplo.invalid/", "http://www.exemplo.invalid/#topo",
                    "https://exemplo.invalid/?utm_source=a&utm_medium=b", "https://EXEMPLO.invalid?"):
            self.assertEqual(comum.endereco_limpo(url), "exemplo.invalid", url)
        self.assertEqual(comum.endereco_limpo("https://WWW.Exemplo.invalid:8443/a/"), "exemplo.invalid:8443/a")

    def test_endereco_limpo_nao_iguala_o_que_e_diferente(self):
        base = comum.endereco_limpo("https://exemplo.invalid/a/b?id=7")
        for outra in ("https://exemplo.invalid/A/b?id=7", "https://exemplo.invalid/a/b?id=8", "https://exemplo.invalid/a/b",
                      "https://exemplo.invalid:8080/a/b?id=7", "https://outro.exemplo.invalid/a/b?id=7",
                      "https://exemplo.invalid/a/b?id=7&pagina=2", "https://exemplo.invalid/a/b?ID=7"):
            self.assertNotEqual(comum.endereco_limpo(outra), base, outra)
        self.assertEqual(comum.endereco_limpo("texto qualquer"), "texto qualquer")
        self.assertFalse(comum.url_valida(base), "a chave sai sem esquema: não se grava como endereço")

    def test_sem_rastreio_mexe_so_no_que_promete(self):
        casos = (
            ("https://WWW.Exemplo.invalid/a/?utm_source=x&b=1#topo", "https://WWW.Exemplo.invalid/a/?b=1"),
            ("https://exemplo.invalid/a?utm_source=x&utm_medium=y", "https://exemplo.invalid/a"),
            ("https://exemplo.invalid/a/#topo", "https://exemplo.invalid/a/"),
            ("https://exemplo.invalid/a?b=1&c=2", "https://exemplo.invalid/a?b=1&c=2"),
            ("https://exemplo.invalid/a?autm_x=1", "https://exemplo.invalid/a?autm_x=1"),
            ("http://exemplo.invalid/utm_source=x", "http://exemplo.invalid/utm_source=x"),
        )
        for url, certo in casos:
            self.assertEqual(comum.sem_rastreio(url), certo, url)


if __name__ == "__main__":
    unittest.main()
