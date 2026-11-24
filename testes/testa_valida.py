#!/usr/bin/env python3
"""Testes do valida.py: a ferramenta chamada pela linha de comando, como a rotina e o GitHub chamam.

- o exemplo passa em --edicao, com a cópia congelada dos dados em --raiz;
- os modos (sem opção, --tudo, --dados, --edicao), os códigos de saída 0, 1 e 2 e o --json;
- o modo --tudo: índice igual aos arquivos, cada edição com seu .md, feed bem formado;
- regra (dia): mudar o mapa não derruba edição de arquivo, e derruba a do dia;
- robustez: arquivo ilegível, JSON quebrado, tipo errado em qualquer profundidade, arquivo enorme;
- nada é gravado (a árvore é fotografada antes e depois) e 400 edições cabem no tempo.

As regras, uma a uma, estão em testa_valida_regras.py (R), testa_valida_historico.py (H e cálculo),
testa_valida_trabalho.py (T), testa_valida_dados.py (M, C e dados) e testa_valida_git.py (G).

Rodar da raiz do repositório: python3 -B testes/testa_valida.py
"""
import ast
import copy
import json
import os
import re
import shutil
import sys
import time
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "valida"))

import apoio  # noqa: E402
from apoio import comum, valida  # noqa: E402

RE_LINHA = re.compile(r"(ERRO|AVISO) [A-Z]+[0-9]*[a-f]? \S+: \S.*")
RE_VEREDITO = re.compile(r"(OK 0 erros|FALHA [1-9][0-9]* erros?), [0-9]+ avisos?")


def dia(numero):
    return "2026-11-%02d" % numero


class ComSaida(apoio.ComRaiz):
    def assertSaidaNoFormato(self, linhas):
        """Uma linha por problema, no formato do CONTRATO, e o veredito na última."""
        self.assertTrue(linhas, "a saída não pode ser vazia")
        self.assertRegex(linhas[-1], RE_VEREDITO)
        for linha in linhas[:-1]:
            self.assertTrue(RE_LINHA.fullmatch(linha), "linha fora do formato: %r" % linha)
        erros = len([l for l in linhas[:-1] if l.startswith("ERRO ")])
        avisos = len([l for l in linhas[:-1] if l.startswith("AVISO ")])
        esperado = "%s %d erro%s, %d aviso%s" % ("FALHA" if erros else "OK", erros, "" if erros == 1 else "s",
                                                 avisos, "" if avisos == 1 else "s")
        self.assertEqual(linhas[-1], esperado)

    def falha(self, *argumentos):
        """Chama, exige código 1 e saída no formato. Devolve as linhas."""
        codigo, linhas = self.valida(*argumentos)
        self.assertEqual(codigo, 1, "\n".join(linhas))
        self.assertSaidaNoFormato(linhas)
        return linhas


class TestaExemplo(ComSaida):
    def test_o_exemplo_passa_em_edicao_com_os_dados_congelados(self):
        codigo, linhas = self.valida("--edicao", apoio.EXEMPLO)
        self.assertEqual((codigo, linhas), (0, ["OK 0 erros, 0 avisos"]))

    def test_o_caminho_do_contrato_relativo_a_pasta_de_onde_se_chama(self):
        codigo, saida, erro = apoio.roda(["--edicao", "testes/fixtures/edicao-exemplo.json", "--raiz", self.raiz])
        self.assertEqual((codigo, saida, erro), (0, "OK 0 erros, 0 avisos\n", ""))

    def test_defeito_no_exemplo_sai_no_formato_do_contrato(self):
        torto = apoio.exemplo()
        torto["radar"][3]["confianca"] = "alta"
        alvo = torto["alerta"]["dominios"][3]
        alvo["gatilhos"][0].update(criterio="suprimentos.3")
        del alvo["gatilhos"][0]["excecao"]
        alvo["nivel"] = 3
        arquivo = self.grava("../solta.json", torto)
        linhas = self.falha("--edicao", arquivo)
        self.assertEqual(linhas, [
            "ERRO R13b alerta.dominios[3].gatilhos[0].ref: nível 3 exige principal, e 'r4' é do radar. Baixe o "
            "critério para o nível 2 ou tire o gatilho.",
            "ERRO R08 radar[3].confianca: é 'alta', o teto pelas fontes é 'media'. Troque para 'media' ou "
            "acrescente fonte do outro campo.",
            "FALHA 2 erros, 0 avisos"])


class TestaModosECodigos(ComSaida):
    def test_repositorio_sem_edicao_e_sem_indice_termina_em_ok(self):
        for argumentos in ((), ("--tudo",), ("--tudo", "--dia", "2026-11-23"), ("--dados",)):
            codigo, linhas = self.valida(*argumentos)
            self.assertEqual((codigo, linhas[-1]), (0, "OK 0 erros, 0 avisos"), "\n".join(linhas))
            self.assertSaidaNoFormato(linhas)
        os.makedirs(self.caminho("edicoes"))        # com a pasta vazia também
        self.assertEqual(self.valida()[0], 0)

    def test_sem_opcao_vale_tudo(self):
        arquivo = apoio.Arquivo()
        arquivo.publica(dia(1))
        arquivo.grava(self.raiz)
        self.muda("edicoes/%s.json" % dia(1), lambda e: e["principais"][0].update(titulo=""))
        self.assertEqual(self.valida(), self.valida("--tudo"))
        self.assertEqual(self.valida()[0], 1)
        self.assertEqual(self.valida("--dados")[0], 0)   # o --dados não abre as edições

    def test_codigo_2_para_uso_errado(self):
        usos = (("--tudo", "--dados"), ("--dados", "--edicao", apoio.EXEMPLO), ("--anterior", apoio.EXEMPLO),
                ("--dados", "--base", "HEAD"), ("--edicao", apoio.EXEMPLO, "--base", "HEAD"), ("--edicao",),
                ("--edicao", ""), ("--base",), ("--dia", "ontem"), ("--dia", "2026-02-30"), ("--nao-existe",),
                ("sobra",), ("--trabalho", self.pasta), ("--edicao", apoio.EXEMPLO, "--anterior", " "))
        for uso in usos:
            codigo, saida, erro = apoio.roda(["--raiz", self.raiz] + list(uso))
            self.assertEqual((codigo, erro), (2, ""), uso)
            self.assertRegex(saida, r"\AFALHA uso: .+\n\Z", uso)
        codigo, saida, _ = apoio.roda(["--raiz", os.path.join(self.pasta, "nao-existe")])
        self.assertEqual(codigo, 2)
        codigo, saida, _ = apoio.roda(["--raiz", self.raiz], INFO_AGORA="amanhã")
        self.assertEqual((codigo, saida), (2, "FALHA uso: INFO_AGORA ilegível\n"))

    def test_o_dia_padrao_e_hoje_em_brasilia(self):
        arquivo = apoio.Arquivo()
        arquivo.publica(dia(19))
        arquivo.publica(dia(20), lambda r: r["radar"][3].update(confianca="alta"), confere=False)   # defeito só de regra (dia)
        arquivo.grava(self.raiz)
        self.assertEqual(comum.dia_brasilia(apoio.AGORA), dia(20))
        linhas = self.falha()                                               # sem --dia: a edição de hoje é a do dia
        self.assertEqual([l.split()[1:3] for l in linhas if l.startswith("ERRO")], [["R08", "edicoes/%s.json:radar[3].confianca:" % dia(20)]])
        codigo, _ = self.valida(INFO_AGORA="2026-11-22T02:59:59Z")          # 21/11 em Brasília: ninguém é do dia
        self.assertEqual(codigo, 0)
        codigo, _ = self.valida(INFO_AGORA="2026-11-21T02:59:59Z")          # ainda 20/11 em Brasília
        self.assertEqual(codigo, 1)
        self.assertEqual(self.valida("--dia", dia(19))[0], 0)

    def test_dia_e_aceito_e_ignorado_nos_outros_modos(self):
        self.assertEqual(self.valida("--dados", "--dia", dia(1))[0], 0)
        self.assertEqual(self.valida("--edicao", apoio.EXEMPLO, "--dia", dia(1)), (0, ["OK 0 erros, 0 avisos"]))

    def test_ajuda(self):
        codigo, saida, erro = apoio.roda(["-h"])
        self.assertEqual((codigo, erro), (0, ""))
        for opcao in ("--tudo", "--dados", "--edicao", "--anterior", "--base", "--raiz", "--dia", "--json"):
            self.assertIn(opcao, saida)
        self.assertNotIn("--trabalho", saida)


class TestaJson(ComSaida):
    def test_forma_do_contrato(self):
        codigo, saida, erro = apoio.roda(["--raiz", self.raiz, "--edicao", apoio.EXEMPLO, "--json"])
        self.assertEqual((codigo, erro), (0, ""))
        self.assertEqual(json.loads(saida), {"ok": True, "codigo": 0, "veredito": "OK 0 erros, 0 avisos", "linhas": [],
                                             "erros": [], "avisos": []})
        torto = apoio.exemplo()
        torto["radar"][3]["confianca"] = "alta"
        arquivo = self.grava("../solta.json", torto)
        codigo, saida, erro = apoio.roda(["--raiz", self.raiz, "--json", "--edicao", arquivo])
        self.assertEqual((codigo, erro), (1, ""))
        objeto = json.loads(saida)
        # A forma comum do --json (CONTRATO, seção 0) mais as duas listas do validador (CONTRATO, seção 3).
        self.assertEqual(list(objeto), ["ok", "codigo", "veredito", "linhas", "erros", "avisos"])
        linha = ("ERRO R08 radar[3].confianca: é 'alta', o teto pelas fontes é 'media'. Troque para 'media' ou "
                 "acrescente fonte do outro campo.")
        self.assertEqual(objeto, {"ok": False, "codigo": 1, "veredito": "FALHA 1 erro, 0 avisos", "linhas": [linha],
                                  "avisos": [], "erros": [{
            "regra": "R08", "caminho": "radar[3].confianca",
            "mensagem": "é 'alta', o teto pelas fontes é 'media'. Troque para 'media' ou acrescente fonte do outro campo."}]})
        self.assertEqual(list(objeto["erros"][0]), ["regra", "caminho", "mensagem"])

    def test_json_e_texto_dizem_o_mesmo(self):
        self.muda("dados/veiculos.json", lambda o: o["veiculos"][0].update(sites=[]))
        codigo_texto, linhas = self.valida("--dados")
        codigo_json, saida, _ = apoio.roda(["--raiz", self.raiz, "--dados", "--json"])
        objeto = json.loads(saida)
        self.assertEqual((codigo_texto, codigo_json, objeto["ok"]), (1, 1, False))
        refeitas = (["ERRO %(regra)s %(caminho)s: %(mensagem)s" % e for e in objeto["erros"]]
                    + ["AVISO %(regra)s %(caminho)s: %(mensagem)s" % a for a in objeto["avisos"]])
        self.assertEqual(refeitas, linhas[:-1])
        self.assertEqual((len(objeto["erros"]), len(objeto["avisos"])), (1, 0))

    def test_erro_de_uso_sai_em_texto_mesmo_com_json(self):
        codigo, saida, _ = apoio.roda(["--raiz", self.raiz, "--json", "--tudo", "--dados"])
        self.assertEqual(codigo, 2)
        self.assertTrue(saida.startswith("FALHA uso: "))


class TestaTudo(ComSaida):
    """Índice igual aos arquivos, cada edição com seu .md, feed bem formado."""

    def setUp(self):
        super().setUp()
        self.arquivo = apoio.Arquivo()
        for numero in (1, 2, 3):
            self.arquivo.publica(dia(numero))
        self.arquivo.grava(self.raiz)

    def erros(self, *argumentos):
        return [l for l in self.falha(*(argumentos or ("--tudo",))) if l.startswith("ERRO")]

    def test_arquivo_bom_passa(self):
        codigo, linhas = self.valida("--tudo", "--dia", dia(3))
        self.assertEqual((codigo, linhas[-1]), (0, "OK 0 erros, 2 avisos"), "\n".join(linhas))   # 2 de H3 (o catálogo congelado já não dá C5)
        self.assertSaidaNoFormato(linhas)
        self.assertTrue(all("edicoes/%s.json:" % dia(3) in l for l in linhas if l.startswith("AVISO H3")))

    def test_o_caminho_comeca_com_o_nome_do_arquivo(self):
        self.muda("edicoes/%s.json" % dia(2), lambda e: e.update(resumo=""))
        self.arquivo.edicoes[dia(2)]["resumo"] = ""
        apoio.grava(self.caminho("edicoes", "indice.json"), valida.monta_indice(self.arquivo.edicoes))
        self.assertEqual(self.erros(), ["ERRO R17 edicoes/%s.json:resumo: texto vazio. Escreva o conteúdo: este campo "
                                        "nunca fica vazio." % dia(2)])

    def test_indice_diferente_dos_arquivos(self):
        self.muda("edicoes/indice.json", lambda i: i["edicoes"][0].update(nivel=1, resumo="Outro."))
        self.assertEqual(self.erros(), ["ERRO INDICE edicoes/indice.json:edicoes[0]: não bate com edicoes/%s.json nos "
                                        "campos: nivel, resumo. O índice é gerado: rode publica.py refaz." % dia(3)])

    def test_indice_que_falta_ou_que_nao_abre(self):
        os.remove(self.caminho("edicoes", "indice.json"))
        self.assertEqual([l.split()[1:3] for l in self.erros()], [["INDICE", "edicoes/indice.json:"]])
        self.grava("edicoes/indice.json", "{não é json")
        self.assertEqual([l.split()[1:3] for l in self.erros()], [["ARQUIVO", "edicoes/indice.json:"]])

    def test_edicao_que_o_indice_nao_tem_e_entrada_sem_edicao(self):
        self.muda("edicoes/indice.json", lambda i: i["edicoes"].pop(1))
        erros = self.erros()
        self.assertEqual(len(erros), 1)
        self.assertIn("falta a entrada da edição de %s" % dia(2), erros[0])
        self.arquivo.grava(self.raiz)
        os.remove(self.caminho("edicoes", dia(3) + ".json"))
        os.remove(self.caminho("edicoes", dia(3) + ".md"))
        erros = self.erros()
        self.assertTrue([l for l in erros if "cita a edição de %s" % dia(3) in l], erros)

    def test_cada_edicao_com_seu_md(self):
        os.remove(self.caminho("edicoes", dia(2) + ".md"))
        erros = self.erros()
        self.assertEqual(sorted(l.split()[1:3] for l in erros), [["INDICE", "edicoes/indice.json:edicoes[1].texto:"],
                                                                 ["MD", "edicoes/%s.md:" % dia(2)]])
        self.assertIn("publica.py refaz", erros[0])

    def test_texto_sem_edicao_e_arquivo_de_nome_estranho(self):
        self.grava("edicoes/%s.md" % dia(9), "# sobra\n")
        self.grava("edicoes/notas.md", "# anotações\n")
        self.grava("edicoes/rascunho.json", "{}")
        self.grava("edicoes/2026-13-45.json", "{}")
        linhas = self.falha("--tudo")
        self.assertEqual([l.split()[1:3] for l in linhas if l.startswith("ERRO")], [["MD", "edicoes/%s.md:" % dia(9)]])
        # nome que não é data: só avisa (pode ser arquivo do dono; a rotina não consegue criar um: regra G4)
        self.assertEqual(sorted(l.split()[1:3] for l in linhas if l.startswith("AVISO ARQUIVO")), [
            ["ARQUIVO", "edicoes/2026-13-45.json:"], ["ARQUIVO", "edicoes/notas.md:"], ["ARQUIVO", "edicoes/rascunho.json:"]])
        os.remove(self.caminho("edicoes", dia(9) + ".md"))
        self.assertEqual(self.valida("--tudo")[0], 0)

    def test_data_diferente_do_nome_do_arquivo(self):
        self.muda("edicoes/%s.json" % dia(2), lambda e: e.update(data=dia(1)))
        erros = self.erros()
        self.assertTrue([l for l in erros if l.startswith("ERRO R01 edicoes/%s.json:data:" % dia(2))], erros)

    def test_feed(self):
        ruins = {
            "mal formado": "<feed xmlns='http://www.w3.org/2005/Atom'><title>INFOCENARIUM</feed>",
            "raiz que não é feed": "<rss version='2.0'><channel/></rss>",
            "feed sem o espaço de nomes do Atom": "<feed><title>INFOCENARIUM</title></feed>",
            "elemento de outro vocabulário": ("<feed xmlns='http://www.w3.org/2005/Atom'><entry><content>"
                                              "<script xmlns='http://www.w3.org/1999/xhtml'>alert(1)</script>"
                                              "</content></entry></feed>"),
            "DOCTYPE": "<!DOCTYPE feed [<!ENTITY a 'b'>]><feed xmlns='http://www.w3.org/2005/Atom'/>",
            "folha de estilo": ("<?xml version='1.0'?><?xml-stylesheet href='x.xsl'?>"
                                "<feed xmlns='http://www.w3.org/2005/Atom'/>"),
            "conteúdo em html": ("<feed xmlns='http://www.w3.org/2005/Atom'><entry><summary type='html'>&lt;b&gt;x"
                                 "&lt;/b&gt;</summary></entry></feed>"),
            "vazio": "",
            "link que não é http": ("<feed xmlns='http://www.w3.org/2005/Atom'><entry><link href='javascript:alert(1)'/>"
                                    "</entry></feed>"),
        }
        for nome, texto in sorted(ruins.items()):
            with self.subTest(nome):
                self.grava("feed.xml", texto)
                erros = self.erros()
                self.assertEqual([l.split()[1:3] for l in erros], [["FEED", "feed.xml:"]], nome)
                self.assertIn("publica.py refaz", erros[0])
        self.grava("feed.xml", "<?xml version='1.0' encoding='utf-8'?>\n<feed xmlns='http://www.w3.org/2005/Atom'>"
                   "<title type='text'>INFOCENARIUM</title><link href='https://exemplo.invalid/INFOCENARIUM/'/>"
                   "<entry><link rel='alternate' type='text/html' href='./#/edicao/2026-11-01'/>"
                   "<summary>Resumo.</summary><content type='text'>Texto.</content></entry></feed>")
        self.assertEqual(self.valida("--tudo")[0], 0)

    def test_feed_le_o_esquema_do_link_como_o_leitor_de_feed(self):
        """O leitor de feed tira tabulação, quebra de linha e espaço do endereço antes de ler o esquema:
        "java&#9;script:" vira "javascript:". O validador lê do mesmo jeito (CONTRATO, seção 4.5)."""
        def feed(href):
            return ("<feed xmlns='http://www.w3.org/2005/Atom'><entry><link href='%s'/></entry></feed>" % href).encode()
        for ruim in ("javascript:alert(1)", "java&#9;script:alert(1)", "java&#10;script:alert(1)", "java&#13;script:x",
                     " javascript:alert(1)", "&#1;javascript:x", "JaVa&#9;ScRiPt:x", "data:text/html,x", "vb&#x7f;script:x"):
            with self.subTest(ruim):
                self.assertEqual([a.regra for a in valida.confere_feed(feed(ruim))], ["FEED"], ruim)
        for bom in ("./#/edicao/2026-11-01", "/INFOCENARIUM/#/edicao/2026-11-01", "../", "site/",
                    "https://exemplo.invalid/INFOCENARIUM/", "http://exemplo.invalid/"):
            with self.subTest(bom):
                self.assertEqual(valida.confere_feed(feed(bom)), [], bom)

    def test_feed_que_falta_so_avisa(self):
        os.remove(self.caminho("feed.xml"))
        codigo, linhas = self.valida("--tudo")
        self.assertEqual(codigo, 0)
        self.assertIn("AVISO FEED feed.xml: não existe, e há edições em edicoes/. O feed é gerado: rode publica.py refaz.", linhas)

    def test_dados_tortos_param_a_conferencia_das_edicoes(self):
        self.grava("dados/regua.json", "{}")
        erros = self.erros()
        self.assertTrue([l for l in erros if l.startswith("ERRO DADOS dados/regua.json:partidos:")], erros)
        self.assertEqual(erros[-1], "ERRO DADOS edicoes: as 3 edições não foram conferidas: os dados de dados/ não "
                         "servem de base (erros acima). Conserte os dados e confira de novo.")
        self.assertFalse([l for l in erros if " edicoes/2026" in l], "sem base, nenhuma edição é acusada à toa")
        linhas = self.falha("--edicao", self.caminho("edicoes", dia(3) + ".json"))
        self.assertIn("a edição não foi conferida", linhas[-2])


class TestaRegraDoDia(ComSaida):
    """Edição publicada é registro: o dono revisa o mapa, a régua e o catálogo, e ela não quebra por isso."""

    def setUp(self):
        super().setUp()
        self.arquivo = apoio.Arquivo()
        for numero in (1, 2, 3):
            self.arquivo.publica(dia(numero))
        self.arquivo.grava(self.raiz)

    def test_mudar_o_lado_de_um_veiculo_derruba_so_a_edicao_do_dia(self):
        def revisa(mapa):
            for veiculo in mapa["veiculos"]:
                if veiculo["id"] == "nyt":
                    veiculo["lado"] = "centro_atlantico"
        self.muda("dados/veiculos.json", revisa)
        for sem_edicao_do_dia in (("--tudo",), ("--tudo", "--dia", dia(4)), ("--tudo", "--dia", "2027-01-15")):
            codigo, linhas = self.valida(*sem_edicao_do_dia)
            self.assertEqual(codigo, 0, "\n".join(linhas))
        linhas = self.falha("--tudo", "--dia", dia(3))
        erros = [l for l in linhas if l.startswith("ERRO")]
        self.assertEqual(erros, ["ERRO R03 edicoes/%s.json:principais[0].ataques[0].lado: é 'ordem_global', o mapa diz "
                                 "'centro_atlantico' para 'nyt'. É campo calculado: publique de novo com publica.py "
                                 "edicao (edição não se edita à mão)." % dia(3)])
        linhas = self.falha("--tudo", "--dia", dia(1))
        self.assertTrue(all("edicoes/%s.json:" % dia(1) in l for l in linhas if l.startswith("ERRO")))
        linhas = self.falha("--edicao", self.caminho("edicoes", dia(2) + ".json"))    # conferida sozinha, é a do dia
        self.assertRegras(linhas, ["R03"])

    def test_revisao_grande_do_dono_nao_derruba_o_arquivo(self):
        def revisa_mapa(mapa):
            mapa["revisado_em"] = "2026-11-22"
            mapa["veiculos"] = [v for v in mapa["veiculos"] if v["id"] not in ("wsj", "tass")]
            for veiculo in mapa["veiculos"]:
                if veiculo["id"] in ("reuters", "nyt", "guardian", "wired"):
                    veiculo.update(fatos="media", lado="centrao", lado_confianca="baixa")
                if veiculo["id"] == "comissao_europeia":
                    veiculo["tipo"] = "privado"
                veiculo["serve_a"] = [s for s in veiculo["serve_a"] if s != "anthropic"] + (
                    ["anthropic"] if veiculo["id"] == "ap" else [])

        def revisa_regua(regua):
            regua["conflito"]["termos"] += ["Reino de Amostra", "Brent", "Texto"]
            regua["conflito"]["players"] += ["russia", "ue"]
            regua["sites_oficiais"]["outros"].remove("oficial.exemplo.invalid")
            for linha in regua["niveis_alerta"]:
                for celula in linha["criterios"].values():
                    for preco in celula["precos"]:
                        preco["alta_minima_pct"] = 0.1

        def revisa_catalogo(catalogo):
            catalogo["indicadores"] = [i for i in catalogo["indicadores"] if i["id"] not in ("vix", "ouro")]
            for indicador in catalogo["indicadores"]:
                if indicador["id"] == "fao_ffpi":
                    indicador["frequencia"] = "diaria"
        self.muda("dados/veiculos.json", revisa_mapa)
        self.muda("dados/regua.json", revisa_regua)
        self.muda("dados/indicadores.json", revisa_catalogo)
        codigo, linhas = self.valida("--tudo", "--dia", dia(4))
        self.assertEqual(codigo, 0, "\n".join(linhas))
        do_dia = self.falha("--tudo", "--dia", dia(3))
        acusadas = set(l.split()[1] for l in do_dia if l.startswith("ERRO"))
        self.assertEqual(acusadas, set(["R00", "R02", "R03", "R07", "R08", "R13c", "R19", "R22"]))
        self.assertTrue(all(" edicoes/%s.json:" % dia(3) in l for l in do_dia if l.startswith("ERRO")))


class TestaNadaGravado(ComSaida):
    def test_a_arvore_fica_igual_em_todos_os_modos(self):
        arquivo = apoio.Arquivo()
        arquivo.publica(dia(1))
        arquivo.publica(dia(2), lambda r: r["radar"][3].update(confianca="alta"), confere=False)
        arquivo.grava(self.raiz)
        self.grava("edicoes/quebrada.json", "{")
        os.makedirs(self.caminho("ferramentas"))
        for nome in ("comum.py", "valida.py"):
            shutil.copy(os.path.join(apoio.FERRAMENTAS, nome), self.caminho("ferramentas"))
        foto = apoio.fotografa(self.pasta)
        chamadas = ([], ["--tudo"], ["--tudo", "--dia", dia(2)], ["--dados"], ["--dados", "--json"], ["--tudo", "--json"],
                    ["--edicao", self.caminho("edicoes", dia(2) + ".json")], ["--edicao", "edicoes/quebrada.json"],
                    ["--edicao", apoio.EXEMPLO, "--anterior", self.caminho("edicoes", dia(1) + ".json")],
                    ["--tudo", "--base", "HEAD"], ["--tudo", "--dados"], ["-h"])
        vistos = set()
        for argumentos in chamadas:
            codigo, _, erro = apoio.roda(["--raiz", self.raiz] + argumentos, PYTHONDONTWRITEBYTECODE=None)
            vistos.add(codigo)
            self.assertEqual(erro, "")
            self.assertEqual(apoio.fotografa(self.pasta), foto, "a chamada %s gravou alguma coisa" % argumentos)
        self.assertEqual(vistos, set([0, 1, 2]))
        # a cópia da ferramenta dentro da raiz, chamada como a rotina chama, também não deixa nada
        feito = apoio.subprocess.run([sys.executable, "ferramentas/valida.py", "--tudo", "--dia", dia(2)], cwd=self.raiz,
                                     env=apoio.ambiente(PYTHONDONTWRITEBYTECODE=None), stdout=apoio.subprocess.PIPE)
        self.assertEqual(feito.returncode, 1)
        self.assertEqual(apoio.fotografa(self.pasta), foto)

    def test_o_repositorio_de_verdade_nao_ganha_pycache(self):
        apoio.roda(["--raiz", self.raiz], PYTHONDONTWRITEBYTECODE=None)
        sujeira = [os.path.join(pasta, nome) for pasta, subpastas, _ in os.walk(apoio.RAIZ)
                   for nome in subpastas if nome == "__pycache__"]
        self.assertEqual(sujeira, [])


class TestaRobustez(ComSaida):
    """Sempre uma linha de ERRO e código 1; nunca exceção solta, nunca saída de erro."""

    def boa(self):
        """Uma edição de verdade para o dia 1, a primeira do arquivo."""
        return apoio.completa(apoio.rascunho(dia(1)))

    def com_edicao(self, conteudo):
        """Põe o conteúdo como edicoes/2026-11-01.json (com .md) e devolve as linhas de --tudo e de --edicao."""
        caminho = self.grava("edicoes/%s.json" % dia(1), conteudo)
        self.grava("edicoes/%s.md" % dia(1), "# texto\n")
        tudo = self.falha("--tudo")
        sozinha = self.falha("--edicao", caminho)
        self.assertNotIn("FALHA interna", "\n".join(tudo + sozinha))
        return tudo, sozinha

    def test_json_quebrado_bom_nan_e_bytes_tortos(self):
        casos = {
            '{"versao": 1,\n "data": }': "linha 2, coluna 10: JSON ilegível",
            "": "linha 1, coluna 1: JSON ilegível",
            b"\xef\xbb\xbf{}": "começa com BOM",
            '{"valor": NaN}': "NaN não vale em JSON",
            b'{"resumo": "\xff\xfe"}': "não é UTF-8",
            "[" * 100000: "JSON com níveis demais",
        }
        for conteudo, trecho in casos.items():
            tudo, sozinha = self.com_edicao(conteudo)
            self.assertIn(trecho, sozinha[0], conteudo[:30])
            self.assertTrue(sozinha[0].startswith("ERRO ARQUIVO "), sozinha[0])
            self.assertEqual(len(sozinha), 2)
            self.assertTrue([l for l in tudo if l.startswith("ERRO ARQUIVO edicoes/%s.json: " % dia(1)) and trecho in l], tudo)

    def test_o_que_nao_e_objeto_onde_se_esperava_objeto(self):
        for conteudo in ("[]", "null", '"texto"', "7", "[1, 2, 3]", "true"):
            tudo, sozinha = self.com_edicao(conteudo)
            self.assertEqual(sozinha[0].split()[:3], ["ERRO", "R00", "edicao:"], conteudo)
        torta = self.boa()
        torta.update(alerta=[], principais={}, radar="x", bastidores=None, indicadores=7, placar_do_dia=[[]],
                     errata={"a": 1}, respostas=[None], novos_players=[3])
        tudo, sozinha = self.com_edicao(torta)
        self.assertEqual(len(sozinha), 10)
        self.assertRegras(sozinha, ["R00"])

    def test_arquivo_de_5_mb_e_recusado_sem_ser_aberto(self):
        inicio = time.monotonic()
        tudo, sozinha = self.com_edicao(b'{"resumo": "' + b"x" * 5000000 + b'"}')
        self.assertEqual(len(sozinha), 2)
        self.assertRegex(sozinha[0], r"^ERRO ARQUIVO \S+: tem 5000014 bytes, e o validador lê até 2000000\.")
        self.assertLess(time.monotonic() - inicio, 10)

    def test_texto_gigante_e_edicao_gorda(self):
        gorda = self.boa()
        gorda["bastidores"]["limites"] = "muito texto " * 9000          # 108 mil caracteres num campo de 500
        tudo, sozinha = self.com_edicao(gorda)
        self.assertEqual([l.split()[1:3] for l in sozinha[:-1]], [["R17", "edicao:"], ["R17", "bastidores.limites:"]])
        self.assertLess(max(len(l) for l in sozinha), 400, "a mensagem não despeja o texto gigante")

    def test_edicao_com_itens_demais_tem_a_saida_cortada(self):
        gorda = self.boa()
        gorda["radar"] = [dict(gorda["radar"][0], id="x") for _ in range(400)]
        tudo, sozinha = self.com_edicao(gorda)
        self.assertEqual(len([l for l in sozinha if l.startswith("ERRO")]), valida.TETO_DE_ACHADOS + 1)
        self.assertRegex(sozinha[-2], r"^ERRO R00 edicao: há mais [0-9]+ erros neste arquivo, que não foram listados\.")

    def test_lixo_em_cada_arquivo_que_o_validador_le(self):
        """Cada arquivo trocado por conteúdo que não serve: código 1, linhas no formato, nenhuma falha interna."""
        arquivo = apoio.Arquivo()
        arquivo.publica(dia(1))
        lixos = ("", "null", "false", "[]", "{", '{"versao": [], "players": 3, "veiculos": {}, "vetores": "x", '
                 '"indicadores": [[]], "partidos": [1], "temas": {}, "dominios": [null], "niveis_alerta": [{}], '
                 '"campos": [[]], "evidencias": 0, "forcas": [{}], "conflito": [], "sites_oficiais": 1, "edicoes": 7}')
        alvos = ["dados/%s.json" % nome for nome in apoio.ARQUIVOS_DE_DADOS]
        alvos += ["edicoes/indice.json", "edicoes/%s.json" % dia(1), "feed.xml"]
        for alvo in alvos:
            for lixo in lixos:
                arquivo.grava(self.raiz)
                self.grava(alvo, lixo)
                linhas = self.falha("--tudo")
                self.assertNotIn("FALHA interna", "\n".join(linhas))
                self.assertTrue([l for l in linhas if l.startswith("ERRO ") and " %s" % alvo in l],
                                "%s com %r: faltou erro que cite o arquivo\n%s" % (alvo, lixo[:20], "\n".join(linhas)))

    def test_a_saida_inteira_tem_teto(self):
        for numero in range(1, 29):
            for mes in range(1, 9):
                self.grava("edicoes/2025-%02d-%02d.json" % (mes, numero), "{")     # 224 edições quebradas, sem .md
        linhas = self.falha("--tudo")
        erros = [l for l in linhas if l.startswith("ERRO")]
        self.assertEqual(len(erros), valida.TETO_DA_SAIDA + 1)
        self.assertEqual(erros[-1], "ERRO ARQUIVO saida: há mais 149 erros, que não foram listados. Conserte os de cima e "
                         "confira de novo.")
        self.assertEqual(linhas[-1], "FALHA 301 erros, 0 avisos")

    def test_muitos_niveis_dentro_de_um_campo(self):
        fundo = "x"
        for _ in range(300):
            fundo = [fundo]
        torta = self.boa()
        torta["principais"][0]["fato"] = fundo
        torta["radar"][0]["ataque"]["alvo"] = {"a": fundo}
        tudo, sozinha = self.com_edicao(torta)
        self.assertEqual([l.split()[1:3] for l in sozinha[:-1]], [   # o recuo de 300 níveis estoura os 60 KB
            ["R17", "edicao:"], ["R00", "principais[0].fato:"], ["R02", "radar[0].ataque.alvo:"]])

    def test_pasta_atalho_e_arquivo_sem_permissao(self):
        os.makedirs(self.caminho("edicoes", dia(1) + ".json"))
        self.grava("edicoes/%s.md" % dia(1), "# texto\n")
        linhas = self.falha("--tudo")
        self.assertTrue([l for l in linhas if l.startswith("ERRO ARQUIVO edicoes/%s.json: não é um arquivo comum" % dia(1))], linhas)
        os.rmdir(self.caminho("edicoes", dia(1) + ".json"))
        os.symlink(apoio.EXEMPLO, self.caminho("edicoes", dia(1) + ".json"))
        linhas = self.falha("--tudo")
        self.assertTrue([l for l in linhas if "é um atalho (link simbólico)" in l], linhas)
        os.remove(self.caminho("edicoes", dia(1) + ".json"))
        caminho = self.grava("edicoes/%s.json" % dia(1), self.boa())
        os.chmod(caminho, 0)
        if os.access(caminho, os.R_OK):
            self.skipTest("este usuário lê arquivo sem permissão")
        linhas = self.falha("--tudo")
        self.assertTrue([l for l in linhas if l.startswith("ERRO ARQUIVO edicoes/%s.json: não deu para ler" % dia(1))], linhas)

    def test_edicao_que_nao_existe(self):
        linhas = self.falha("--edicao", os.path.join(self.pasta, "nao-existe.json"))
        self.assertEqual(len(linhas), 2)
        self.assertIn("o arquivo não existe", linhas[0])
        self.assertEqual(self.falha("--edicao", self.raiz)[0].split()[1], "ARQUIVO")       # é uma pasta

    def test_nome_de_arquivo_com_espaco_e_acento_nao_quebra_a_linha(self):
        caminho = self.grava("../edição de teste.json", "{")
        linhas = self.falha("--edicao", caminho)
        self.assertEqual(len(linhas), 2)

    CAMINHOS_TORTOS = (None, True, 0, -1, 2.5, "", "x", [], [None], {}, {"id": []}, [[]], [{"id": 1}])

    def caminhos(self, valor, teto=7):
        saida = [[]]
        if teto and isinstance(valor, dict):
            for chave in valor:
                saida += [[chave] + resto for resto in self.caminhos(valor[chave], teto - 1)]
        elif teto and isinstance(valor, list):
            for indice in range(min(len(valor), 2)):
                saida += [[indice] + resto for resto in self.caminhos(valor[indice], teto - 1)]
        return saida

    def test_tipo_errado_em_qualquer_profundidade(self):
        """Cada pedaço do exemplo trocado por valor de tipo errado: a biblioteca devolve achados, nunca exceção."""
        dados, exemplo = apoio.dados(), apoio.exemplo()
        historico = apoio.historico_do_exemplo()
        caminhos = self.caminhos(exemplo)
        self.assertGreater(len(caminhos), 300)
        feitos = 0
        for posicao, caminho in enumerate(caminhos):
            # perto da raiz, todos os valores tortos; no fundo, 4 de cada vez, em rodízio
            if len(caminho) <= 2:
                tortos = self.CAMINHOS_TORTOS
            else:
                tortos = [self.CAMINHOS_TORTOS[(posicao + n * 3) % len(self.CAMINHOS_TORTOS)] for n in range(4)]
            for torto in tortos:
                edicao = copy.deepcopy(exemplo)
                if caminho:
                    alvo = edicao
                    for chave in caminho[:-1]:
                        alvo = alvo[chave]
                    alvo[caminho[-1]] = torto
                else:
                    edicao = torto
                try:
                    achados = valida.confere_edicao(edicao, dados, historico, True, "2026-11-19", tamanho=1)
                    if feitos % 2 == 0:
                        achados += valida.confere_edicao(edicao, dados, None, False, tamanho=1)
                    if feitos % 4 == 0:
                        achados += valida.confere_trabalho(edicao, dados, "2026-11-19", apoio.COLETA, "", {}, historico)
                        valida.completa(edicao, dados, historico, {"indicadores": torto, "gatilhos": torto}, torto, torto)
                        valida.normaliza(edicao, dados)
                        valida.monta_indice({"2026-11-19": edicao, "2026-11-18": apoio.vespera_do_exemplo()})
                        valida.alerta_anterior(valida.Historico({"2026-11-18": edicao}), "2026-11-19", dados.dominios)
                except Exception as erro:  # o teste é este: nada pode escapar
                    self.fail("%s = %r: %s: %s" % (caminho, torto, type(erro).__name__, erro))
                for achado in achados:
                    self.assertTrue(RE_LINHA.fullmatch(achado.linha()), achado.linha())
                feitos += 1
        self.assertGreater(feitos, 1400)


class TestaQuatrocentasEdicoes(ComSaida):
    def test_mais_de_um_ano_de_edicoes_em_poucos_segundos(self):
        arquivo = apoio.Arquivo()
        data = "2025-10-01"
        for numero in range(400):
            if numero % 50 == 49:
                arquivo.publica_falha(data)
            else:
                arquivo.publica(data, confere=(numero % 40 == 0))
            data = apoio.soma(data, 1)
        ultimo = apoio.soma(data, -1)
        arquivo.grava(self.raiz)
        self.assertEqual(len([n for n in os.listdir(self.caminho("edicoes")) if n.endswith(".json")]), 401)
        inicio = time.monotonic()
        codigo, linhas = self.valida("--tudo", "--dia", ultimo)
        sem_git = time.monotonic() - inicio
        self.assertEqual(codigo, 0, "\n".join(linhas[-20:]))
        self.assertSaidaNoFormato(linhas)
        tempos = "sem --base: %.1f s" % sem_git
        if shutil.which("git"):
            apoio.inicia_git(self.raiz)
            base = apoio.commit(self.raiz, "400 edições")
            arquivo.publica(data)
            arquivo.grava(self.raiz)
            inicio = time.monotonic()
            codigo, linhas = self.valida("--tudo", "--base", base, "--dia", data)
            com_git = time.monotonic() - inicio
            self.assertEqual(codigo, 0, "\n".join(linhas[-20:]))
            tempos += "; com --base: %.1f s" % com_git
            self.assertLess(com_git, 30, tempos)
        # O GitHub dá 120 segundos. Aqui o teto é folgado para máquina lenta; o normal é 2 ou 3 segundos.
        self.assertLess(sem_git, 30, tempos)
        print("\n    400 edições, %s" % tempos, file=sys.stderr)


class TestaOArquivoDaFerramenta(unittest.TestCase):
    def setUp(self):
        with open(apoio.VALIDA, encoding="utf-8") as arquivo:
            self.fonte = arquivo.read()

    def test_sintaxe_que_o_python_3_7_le(self):
        """A guarda de versão só funciona se o Python velho conseguir ler o arquivo inteiro. Pede-se (3, 7), e não
        (3, 6): o Python 3.13 recusa pedir menos que isso."""
        ast.parse(self.fonte, feature_version=(3, 7))
        self.assertIn('print("FALHA interna: Python 3.10 ou mais novo")', self.fonte)
        guarda = self.fonte.index("# --- guarda de versão: início ---")
        self.assertLess(guarda, self.fonte.index("import comum"))
        self.assertLess(self.fonte.index("sys.dont_write_bytecode = True"), self.fonte.index("import comum"))

    def test_python_velho_para_com_falha_interna(self):
        with apoio.tempfile.TemporaryDirectory(prefix="info-valida-") as pasta:
            velha = os.path.join(pasta, "valida_no_python_velho.py")
            apoio.grava(velha, "import sys\nsys.version_info = (3, 9, 18, 'final', 0)\n" + self.fonte)
            feito = apoio.subprocess.run([sys.executable, "-B", velha, "--dados"], stdout=apoio.subprocess.PIPE,
                                         stderr=apoio.subprocess.PIPE, env=apoio.ambiente())
        self.assertEqual((feito.returncode, feito.stdout.decode("utf-8"), feito.stderr),
                         (1, "FALHA interna: Python 3.10 ou mais novo\n", b""))

    def test_toda_funcao_publica_tem_docstring_e_esta_no_topo(self):
        arvore = ast.parse(self.fonte)
        topo = ast.get_docstring(arvore)
        publicas = [no for no in arvore.body if isinstance(no, (ast.FunctionDef, ast.ClassDef)) and not no.name.startswith("_")]
        self.assertGreater(len(publicas), 35)
        for no in publicas:
            if no.name == "principal":
                continue
            self.assertTrue(ast.get_docstring(no), "falta docstring em %s" % no.name)
            self.assertIn(no.name, topo, "%s não está na lista do topo do arquivo" % no.name)
        for nome in re.findall(r"^  ([a-z_]+[a-z0-9_]*)\(", topo, re.M):
            self.assertTrue(hasattr(valida, nome), "o topo promete %s, que não existe" % nome)

    def test_so_biblioteca_padrao_sem_rede_e_sem_gravar(self):
        importados = set()
        for no in ast.walk(ast.parse(self.fonte)):
            if isinstance(no, ast.Import):
                importados.update(nome.name.split(".")[0] for nome in no.names)
            elif isinstance(no, ast.ImportFrom):
                importados.add(no.module.split(".")[0])
        self.assertEqual(importados - set(["comum"]), set(["bisect", "collections", "difflib", "hashlib", "json", "math", "os",
                                                           "re", "stat", "subprocess", "sys", "unicodedata", "xml"]))
        for proibido in ("grava_json", "grava_texto", "Lote(", "os.replace", "os.remove", "os.unlink", "os.makedirs",
                         "mkstemp", "shutil", "urllib.request", "socket", "shell=True", 'open(caminho, "w', ".write("):
            self.assertNotIn(proibido, self.fonte, "o validador não grava nem usa a rede: %s" % proibido)

    def test_nada_do_que_nao_vai_a_publico(self):
        barra = "/"
        proibidas = (barra + "home" + barra, barra + "Users" + barra, "ofi" + "cina", "brie" + "fing", "G" + "SM",
                     "traba" + "lho" + barra)
        pasta = os.path.dirname(os.path.abspath(__file__))
        arquivos = [apoio.VALIDA, os.path.join(apoio.AQUI, "apoio.py")]
        arquivos += [os.path.join(pasta, n) for n in os.listdir(pasta) if n.startswith("testa_valida") and n.endswith(".py")]
        self.assertGreaterEqual(len(arquivos), 7)
        for caminho in arquivos:
            with open(caminho, encoding="utf-8") as arquivo:
                texto = arquivo.read()
            for palavra in proibidas:
                self.assertNotIn(palavra.lower(), texto.lower() if palavra[0] != "G" else texto,
                                 "%s traz %r" % (os.path.basename(caminho), palavra))
            self.assertIsNone(re.search(r"[\w.+-]+@(?!exemplo\.invalid|info\.invalid)[\w-]+\.[\w.-]+", texto),
                              os.path.basename(caminho))


if __name__ == "__main__":
    unittest.main()
