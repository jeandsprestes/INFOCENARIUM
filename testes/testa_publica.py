#!/usr/bin/env python3
"""Testes do publica.py: a linha de comando, o arquivo da ferramenta e o ciclo da ROTINA, seção 8.

Rode da raiz do repositório: python3 -B testes/testa_publica.py
Os outros testes da ferramenta estão em testa_publica_contexto.py, testa_publica_edicao.py,
testa_publica_falha_refaz.py e testa_publica_textos.py. A bancada comum é testes/fixtures/publica/apoio.py.
Tudo roda em pasta temporária, com o relógio fixo (INFO_AGORA), sem rede e pela linha de comando.
"""
import ast
import json
import os
import shutil
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "publica"))
import apoio  # noqa: E402

DIA = apoio.DIA


class TestaALinhaDeComando(apoio.Bancada):
    """CONTRATO, seções 0 e 4: subcomandos, opções, erro de uso em uma linha e código 2, sem gravar nada."""

    def uso(self, argumentos, trecho, **variaveis):
        """A chamada termina em erro de uso: uma linha só, código 2, e nada muda na pasta do teste."""
        foto = apoio.fotografa(self.pasta)
        variaveis.setdefault("INFO_AGORA", apoio.agora(DIA))
        codigo, saida, erro = apoio.roda(apoio.PUBLICA, argumentos, **variaveis)
        self.assertEqual((codigo, erro), (2, ""), saida)
        self.assertEqual(len(saida.splitlines()), 1, saida)
        self.assertTrue(saida.startswith("FALHA uso: "), saida)
        self.assertIn(trecho, saida)
        self.assertEqual(apoio.fotografa(self.pasta), foto, "erro de uso não grava nada, nem prova a pasta de trabalho")

    def comuns(self, *mais):
        return ["--raiz", self.raiz, "--trabalho", self.trabalho] + list(mais)

    def test_sem_subcomando(self):
        self.uso([], "falta o subcomando")
        self.uso(["--raiz", self.raiz, "contexto"], "falta o subcomando, que vem antes das opções")
        self.uso(["--json"], "falta o subcomando")

    def test_subcomando_que_nao_existe(self):
        self.uso(["publica"] + self.comuns(), "contexto")

    def test_opcao_de_outro_subcomando(self):
        self.uso(["contexto"] + self.comuns("--simula"), "--simula")
        self.uso(["contexto"] + self.comuns("--url-base", apoio.BASE), "--url-base")
        self.uso(["falha"] + self.comuns("--motivo", "Sem rede.", "--simula"), "--simula")
        self.uso(["falha"] + self.comuns("--motivo", "Sem rede.", "--corta", "r1"), "--corta")
        self.uso(["refaz", "--raiz", self.raiz, "--corta", "r1"], "--corta")
        self.uso(["edicao"] + self.comuns("--motivo", "x"), "--motivo")

    def test_opcao_abreviada_nao_vale(self):
        self.uso(["edicao"] + self.comuns("--simul"), "--simul")

    def test_falta_o_motivo(self):
        self.uso(["falha"] + self.comuns(), "--motivo")

    def test_motivo_que_nao_serve(self):
        self.uso(["falha"] + self.comuns("--motivo", "x" * 201), "máximo é 200")
        self.uso(["falha"] + self.comuns("--motivo", "A coleta <b>falhou</b>."), "HTML")
        self.uso(["falha"] + self.comuns("--motivo", "   "), "vazio")
        self.uso(["falha"] + self.comuns("--motivo", "Veja em https://exemplo.invalid/a"), "endereço")
        self.uso(["falha"] + self.comuns("--motivo", "linha um\nlinha dois"), "controle")

    def test_corta_ilegivel(self):
        self.uso(["edicao"] + self.comuns("--corta", "x9"), "id ilegível")
        self.uso(["edicao"] + self.comuns("--corta", "r13"), "id ilegível")
        self.uso(["edicao"] + self.comuns("--corta", "p4"), "id ilegível")
        self.uso(["edicao"] + self.comuns("--corta", "r3,,r4"), "id ilegível")
        self.uso(["edicao"] + self.comuns("--corta", "r3,r3"), "repetido")
        self.uso(["edicao"] + self.comuns("--corta"), "--corta")

    def test_url_base_ilegivel(self):
        for ruim in ("javascript:alert(1)", "https://exemplo.invalid/a b/", "https://", "ftp://exemplo.invalid/",
                     "https://exemplo.invalid/#/x", "https://exemplo.invalid/?a=1", "", "./a\"b/"):
            self.uso(["refaz", "--raiz", self.raiz, "--url-base", ruim], "--url-base")

    def test_dia_ilegivel(self):
        self.uso(["contexto"] + self.comuns("--dia", "20/11/2026"), "--dia")
        self.uso(["edicao"] + self.comuns("--dia", "2026-02-30"), "--dia")

    def test_relogio_de_teste_ilegivel(self):
        self.uso(["contexto"] + self.comuns(), "INFO_AGORA ilegível", INFO_AGORA="ontem")

    def test_raiz_que_nao_existe(self):
        self.uso(["contexto", "--raiz", os.path.join(self.pasta, "nao-ha"), "--trabalho", self.trabalho], "--raiz")

    def test_ajuda_sai_com_codigo_zero(self):
        for argumentos in (["-h"], ["edicao", "-h"]):
            codigo, saida, erro = apoio.roda(apoio.PUBLICA, argumentos)
            self.assertEqual((codigo, erro), (0, ""))
            self.assertIn("--raiz" if argumentos != ["-h"] else "contexto", saida)

    def test_json_no_lugar_do_texto(self):
        codigo, linhas = self.publica("contexto", "--json")
        objeto = json.loads("\n".join(linhas))
        self.assertEqual((codigo, objeto["ok"], objeto["codigo"]), (0, True, 0))
        self.assertEqual(objeto["veredito"], "OK contexto de %s" % DIA)
        self.assertEqual(objeto["contexto"], apoio.le(self.no_trabalho("contexto.json")))
        self.assertIsInstance(objeto["linhas"], list)
        # com erro de regra, o --json traz os erros no formato do validador
        self.prepara(muda=lambda r: r["radar"][4].update(confianca="alta"))
        codigo, linhas = self.publica("edicao", "--json")
        objeto = json.loads("\n".join(linhas))
        self.assertEqual((codigo, objeto["ok"]), (1, False))
        self.assertEqual([erro["regra"] for erro in objeto["erros"]], ["R08"])
        self.assertEqual(sorted(objeto["erros"][0]), ["caminho", "mensagem", "regra"])
        self.assertTrue(objeto["veredito"].startswith("FALHA 1 erro"))

    def test_o_refaz_aceita_as_opcoes_comuns_e_nao_cria_a_pasta_de_trabalho(self):
        pasta = os.path.join(self.pasta, "nao-criada")
        self.assertOK(self.publica("refaz", "--trabalho", pasta, "--dia", DIA))
        self.assertFalse(os.path.exists(pasta))

    def test_contexto_json_quebrado_para_sem_gravar(self):
        """CONTRATO, seção 0: contexto.json quebrado é FALHA, código 1, e nada é gravado. Sem --dia, o dia vem
        dele: cair para "hoje" trocaria de dia calado depois da meia-noite."""
        self.prepara()
        for conteudo in ("{quebrado", "[]", '{"dia": "20/11/2026"}'):
            apoio.grava(self.no_trabalho("contexto.json"), conteudo)
            foto = self.fotos()
            for argumentos in (["edicao"], ["edicao", "--simula"], ["falha", "--motivo", "Sem rede."]):
                linhas = self.assertFALHA(self.publica(*argumentos, dia=None))
                self.assertIn("contexto.json", linhas[-1], conteudo)
                self.assertEqual(self.fotos(), foto, conteudo)

    def test_a_pasta_de_trabalho_e_criada_se_faltar(self):
        self.trabalho = os.path.join(self.pasta, "nova", "pasta")
        self.assertOK(self.publica("contexto"))
        self.assertEqual(sorted(os.listdir(self.trabalho)), ["contexto.json", "mapa.txt", "modelo.txt"])

    def test_pasta_de_trabalho_que_nao_aceita_gravacao(self):
        arquivo = os.path.join(self.pasta, "arquivo")
        apoio.grava(arquivo, "x")
        self.trabalho = os.path.join(arquivo, "dentro")
        linhas = self.assertFALHA(self.publica("contexto"))
        self.assertIn("--trabalho", linhas[-1])


class TestaOArquivoDaFerramenta(unittest.TestCase):
    def setUp(self):
        with open(apoio.PUBLICA, encoding="utf-8") as arquivo:
            self.fonte = arquivo.read()

    def test_sintaxe_que_o_python_velho_le(self):
        """A guarda de versão só funciona se o Python velho conseguir ler o arquivo inteiro."""
        ast.parse(self.fonte, feature_version=(3, 7))
        self.assertIn('print("FALHA interna: Python 3.10 ou mais novo")', self.fonte)
        guarda = self.fonte.index("# --- guarda de versão: início ---")
        self.assertLess(guarda, self.fonte.index("import comum"))
        self.assertLess(self.fonte.index("sys.dont_write_bytecode = True"), self.fonte.index("import comum"))

    def test_python_velho_para_com_falha_interna(self):
        with apoio.tempfile.TemporaryDirectory(prefix="info-publica-") as pasta:
            velha = os.path.join(pasta, "publica_no_python_velho.py")
            apoio.grava(velha, "import sys\nsys.version_info = (3, 9, 18, 'final', 0)\n" + self.fonte)
            feito = apoio.subprocess.run([sys.executable, "-B", velha, "refaz"], stdout=apoio.subprocess.PIPE,
                                         stderr=apoio.subprocess.PIPE, env=apoio.ambiente())
        self.assertEqual((feito.returncode, feito.stdout.decode("utf-8"), feito.stderr),
                         (1, "FALHA interna: Python 3.10 ou mais novo\n", b""))

    def test_so_biblioteca_padrao_e_sem_rede(self):
        importados = set()
        for no in ast.walk(ast.parse(self.fonte)):
            if isinstance(no, ast.Import):
                importados.update(nome.name.split(".")[0] for nome in no.names)
            elif isinstance(no, ast.ImportFrom):
                importados.add(no.module.split(".")[0])
        self.assertEqual(importados, set(["argparse", "comum", "datetime", "json", "os", "re", "stat", "sys",
                                          "valida", "xml"]))
        # git só pelo valida.Git (subprocess sem shell e com tempo limite): aqui não há processo nem rede
        for proibido in ("subprocess", "os.system", "urllib", "socket", "shell=True", "eval(", "exec("):
            self.assertNotIn(proibido, self.fonte)

    def test_nada_do_que_nao_vai_a_publico(self):
        # As palavras são montadas aqui, e não escritas por inteiro: este arquivo também vai a público.
        palavras = ("ofi" + "cina", "brie" + "fing", "G" + "SM", "trabalho" + "/metodo", "trabalho" + "/construcao")
        for proibido in ("/home/",) + palavras:
            self.assertNotIn(proibido, self.fonte)
            self.assertNotIn(proibido.lower(), self.fonte.lower())
        invisiveis = [c for c in self.fonte if ord(c) < 32 and c != "\n" or 0x7f <= ord(c) <= 0x9f
                      or ord(c) in (0x2028, 0x2029, 0xfeff) or 0xd800 <= ord(c) <= 0xdfff]
        self.assertEqual(invisiveis, [], "o arquivo não traz caractere invisível")

    def test_nunca_cita_como_destino_os_arquivos_do_dono(self):
        """O publica.py nunca grava veiculos.json, regua.json nem indicadores.json (CONTRATO, seção 4.2)."""
        for linha in self.fonte.splitlines():
            if "lote." in linha or "grava_json" in linha or "grava_texto" in linha:
                for nome in ("veiculos.json", "regua.json", "indicadores.json"):
                    if nome == "indicadores.json" and "trabalho" in linha:
                        continue
                    self.assertNotIn(nome, linha)

    def test_toda_funcao_publica_tem_docstring(self):
        arvore = ast.parse(self.fonte)
        publicas = [no for no in arvore.body if isinstance(no, ast.FunctionDef) and not no.name.startswith("_")]
        self.assertGreater(len(publicas), 10)
        for no in publicas:
            self.assertTrue(ast.get_docstring(no), "falta docstring em %s" % no.name)

    def test_o_modelo_esta_inteiro_no_arquivo(self):
        self.assertIn(apoio.le_texto(apoio.MODELO), self.fonte)


class TestaQueNaoSujaORepositorio(apoio.Bancada):
    def test_sem_bytecode_mesmo_sem_a_opcao_b(self):
        """Uma cópia das ferramentas, chamada como a rotina chama (sem -B), não ganha __pycache__ (regra G4)."""
        copia = os.path.join(self.raiz, "ferramentas")
        os.makedirs(copia)
        for nome in ("comum.py", "valida.py", "publica.py"):
            shutil.copy(os.path.join(apoio.FERRAMENTAS, nome), copia)
        self.prepara()
        for argumentos in (["contexto"], ["edicao", "--simula"], ["edicao"], ["falha", "--motivo", "Sem rede."],
                           ["refaz"], ["edicao", "--corta", "x"]):
            comuns = ["--raiz", self.raiz] + ([] if argumentos[0] == "refaz" else ["--trabalho", self.trabalho])
            feito = apoio.subprocess.run([sys.executable, "ferramentas/publica.py", argumentos[0]] + comuns
                                         + argumentos[1:], cwd=self.raiz, stdout=apoio.subprocess.PIPE,
                                         stderr=apoio.subprocess.PIPE,
                                         env=apoio.ambiente(INFO_AGORA=apoio.agora(DIA), PYTHONDONTWRITEBYTECODE=None))
            self.assertEqual(feito.stderr, b"", argumentos)
            self.assertIn(feito.returncode, (0, 1, 2), argumentos)
        achados = [caminho for caminho in apoio.fotografa(self.raiz) if "__pycache__" in caminho or caminho.endswith(".pyc")]
        self.assertEqual(achados, [])

    def test_o_repositorio_de_verdade_nao_ganha_pycache_nem_edicao(self):
        self.publica_o_dia()
        sujeira = [os.path.join(pasta, nome) for pasta, subpastas, _ in os.walk(apoio.RAIZ)
                   for nome in subpastas if nome == "__pycache__"]
        self.assertEqual(sujeira, [])


class TestaOCicloDaRotina(apoio.Bancada):
    """ROTINA, seção 8, sem rede: valida.py --dados, publica.py contexto, coleta.json e indicadores.json de
    fixture, publica.py edicao e valida.py --tudo --base com o dia. Cada comando é chamado como a rotina chama."""

    def chama(self, ferramenta, *argumentos, **variaveis):
        codigo, saida, erro = apoio.roda(ferramenta, list(argumentos), **variaveis)
        self.assertEqual(erro, "")
        return codigo, saida.splitlines()

    def test_o_ciclo_inteiro(self):
        base = self.inicia_git()
        relogio = apoio.agora(DIA, "21:07:00")  # 18h07 de Brasília
        # seção 1
        codigo, linhas = self.chama(apoio.VALIDA, "--raiz", self.raiz, "--dados", INFO_AGORA=relogio)
        self.assertEqual(codigo, 0, linhas)
        codigo, linhas = self.chama(apoio.PUBLICA, "contexto", "--raiz", self.raiz, "--trabalho", self.trabalho,
                                    INFO_AGORA=relogio)
        self.assertEqual((codigo, linhas[-1]), (0, "OK contexto de %s" % DIA))
        contexto = apoio.le(self.no_trabalho("contexto.json"))
        self.assertEqual((contexto["dia"], contexto["janela_horas"], contexto["edicao_do_dia"]), (DIA, 36, None))
        # seções 2 a 7: a coleta e os indicadores vêm de fixture, e o agente escreve o rascunho pelo modelo
        novo = apoio.rascunho(contexto["dia"])
        modelo = json.loads("\n".join(linha for linha in apoio.le_texto(self.no_trabalho("modelo.txt")).splitlines()
                                      if not linha.strip().startswith("//")))
        self.assertEqual(list(novo), list(modelo), "o rascunho de teste tem a forma do modelo.txt")
        apoio.monta_trabalho(self.trabalho, novo, contexto["dia"])
        apoio.grava(self.no_trabalho("contexto.json"), contexto)  # o monta_trabalho não mexe nele
        # seção 8: sem --dia, o dia vem do contexto.json
        relogio = apoio.agora(DIA, "21:29:40")
        codigo, linhas = self.chama(apoio.PUBLICA, "edicao", "--raiz", self.raiz, "--trabalho", self.trabalho,
                                    INFO_AGORA=relogio)
        self.assertEqual(codigo, 0, "\n".join(linhas))
        self.assertEqual(linhas[-1], "OK edição %s publicada: nível 3 TENSÃO (energia 3, alimentos 1, cambio 1, "
                         "suprimentos 2, conflito 3), 3 principais, 6 radar, 2 vetores, 0 players novos" % DIA)
        codigo, linhas = self.chama(apoio.VALIDA, "--raiz", self.raiz, "--tudo", "--base", base, "--dia", DIA,
                                    INFO_AGORA=relogio)
        self.assertEqual(codigo, 0, "\n".join(linhas))
        self.assertTrue(linhas[-1].startswith("OK 0 erros"), linhas[-1])
        # seção 9: o git add da rotina leva tudo o que mudou, e não sobra nada fora dele
        self.git("add", "edicoes", "feed.xml", "dados/players.json", "dados/vetores.json")
        self.assertEqual(sorted(self.git("diff", "--cached", "--name-only").splitlines()),
                         ["dados/vetores.json", "edicoes/%s.json" % DIA, "edicoes/%s.md" % DIA,
                          "edicoes/indice.json", "feed.xml"])
        self.assertEqual(self.mudancas(), [("A", "edicoes/%s.json" % DIA), ("A", "edicoes/%s.md" % DIA),
                                           ("A", "edicoes/indice.json"), ("A", "feed.xml"), ("M", "dados/vetores.json")],
                         "fora do que o git add levou, não sobrou nada")
        self.git("commit", "--quiet", "-m", "edição %s" % DIA)
        # com o commit feito e a pasta limpa (como no workflow), o validador continua aceitando
        codigo, linhas = self.chama(apoio.VALIDA, "--raiz", self.raiz, "--tudo", "--base", base, "--dia", DIA,
                                    INFO_AGORA=relogio)
        self.assertEqual(codigo, 0, "\n".join(linhas))
        # e a rotina que rodar de novo no mesmo dia para na seção 1: a edição já existe
        codigo, linhas = self.chama(apoio.PUBLICA, "contexto", "--raiz", self.raiz, "--trabalho", self.trabalho,
                                    INFO_AGORA=apoio.agora(DIA, "22:00:00"))
        self.assertEqual(apoio.le(self.no_trabalho("contexto.json"))["edicao_do_dia"],
                         {"estado": "completa", "gerada_em": relogio})

    def test_execucao_que_cruza_a_meia_noite_nao_troca_de_dia(self):
        """O dia nasce uma vez, no contexto: às 23h50 de Brasília é o dia 20; a edição sai à 0h10 com esse dia."""
        self.inicia_git()
        codigo, linhas = self.chama(apoio.PUBLICA, "contexto", "--raiz", self.raiz, "--trabalho", self.trabalho,
                                    INFO_AGORA="2026-11-21T02:50:00Z")
        self.assertEqual((codigo, linhas[-1]), (0, "OK contexto de %s" % DIA))
        contexto = apoio.le(self.no_trabalho("contexto.json"))
        apoio.monta_trabalho(self.trabalho, apoio.rascunho(DIA), DIA)
        apoio.grava(self.no_trabalho("contexto.json"), contexto)
        codigo, linhas = self.chama(apoio.PUBLICA, "edicao", "--raiz", self.raiz, "--trabalho", self.trabalho,
                                    INFO_AGORA="2026-11-21T03:10:00Z")
        self.assertEqual(codigo, 0, "\n".join(linhas))
        edicao = self.le("edicoes/%s.json" % DIA)
        self.assertEqual((edicao["data"], edicao["gerada_em"]), (DIA, "2026-11-21T03:10:00Z"))
        self.assertFalse(self.existe("edicoes/2026-11-21.json"))
        self.assertValido("--base", "HEAD", "--dia", DIA, agora="2026-11-21T03:11:00Z")

    def test_o_dia_sem_edicao_fecha_com_a_falha(self):
        """ROTINA, seção 10, "nada funciona": publica.py falha, depois o valida.py da seção 8."""
        base = self.inicia_git()
        self.assertOK(self.publica("contexto", dia=None))
        codigo, linhas = self.chama(apoio.PUBLICA, "falha", "--motivo", "Sem busca nem feed em 20/11.", "--raiz", self.raiz,
                                    "--trabalho", self.trabalho, INFO_AGORA=apoio.agora(DIA))
        self.assertEqual(codigo, 0, "\n".join(linhas))
        self.assertTrue(linhas[-1].startswith("OK falha de %s publicada" % DIA), linhas[-1])
        self.assertValido("--base", base, "--dia", DIA)


class TestaOQuePassaAoValidador(apoio.Bancada):
    """O publica.py não reimplementa regra: chama as funções do valida.py. Aqui se confere o que ele passa a elas.

    Este é o único teste que chama a ferramenta dentro do processo: é o jeito de ver os argumentos."""

    # A posição do argumento `historico` em cada função (a docstring do topo do valida.py).
    POSICOES = {"completa": 2, "confere_edicao": 2, "confere_trabalho": 6, "alerta_anterior": 0}

    def espia(self):
        vistos = []
        for nome, posicao in self.POSICOES.items():
            original = getattr(apoio.valida, nome)

            def espiao(*argumentos, _original=original, _nome=nome, _posicao=posicao, **nomeados):
                historico = nomeados.get("historico", argumentos[_posicao] if len(argumentos) > _posicao else None)
                vistos.append((_nome, historico))
                return _original(*argumentos, **nomeados)
            setattr(apoio.valida, nome, espiao)
            self.addCleanup(setattr, apoio.valida, nome, original)
        return vistos

    def aqui(self, *argumentos):
        """A linha de comando dentro do processo, com o relógio de teste. Devolve (código, linhas)."""
        import contextlib
        import io
        antes = os.environ.get("INFO_AGORA")
        os.environ["INFO_AGORA"] = apoio.agora(DIA)
        self.addCleanup(lambda: os.environ.pop("INFO_AGORA") if antes is None else os.environ.update(INFO_AGORA=antes))
        texto = io.StringIO()
        with contextlib.redirect_stdout(texto):
            codigo = apoio.comum.protege(apoio.publica.principal, list(argumentos))
        return codigo, texto.getvalue().splitlines()

    def test_o_historico_e_sempre_um_historico_mesmo_vazio(self):
        """Sem edição nenhuma, o histórico é vazio, e não None: None liga a saída "sem histórico à mão" da regra
        H1 (ESQUEMA, seção 10), que aceita nível mantido sem conferir contra as edições de verdade."""
        vistos = self.espia()
        comuns = ["--raiz", self.raiz, "--trabalho", self.trabalho, "--dia", DIA]
        self.prepara()
        for argumentos in (["contexto"], ["edicao", "--simula"], ["edicao", "--corta", "r6", "--simula"],
                           ["falha", "--motivo", "Sem busca nem feed."]):
            codigo, linhas = self.aqui(*(argumentos[:1] + comuns + argumentos[1:]))
            self.assertEqual(codigo, 0, "\n".join(linhas))
        chamadas = sorted(set(nome for nome, _ in vistos))
        self.assertEqual(chamadas, sorted(self.POSICOES), "cada função foi chamada ao menos uma vez")
        tortos = [(nome, historico) for nome, historico in vistos if not isinstance(historico, apoio.valida.Historico)]
        self.assertEqual(tortos, [])
        self.assertTrue(all(len(historico.datas) == 0 for _, historico in vistos), "a raiz não tem edição nenhuma")


class TestaOArquivoMexidoAMao(apoio.Bancada):
    """Edição antiga mexida à mão, com a metade de um emoji (código de d800 a dfff) num texto. O publica.py nunca
    grava isso (a edição nova é recusada, regra R17), mas o validador aceita o arquivo, e ele não pode derrubar as
    ferramentas do dia seguinte com FALHA interna: o índice copia o texto como está, escrito como \\uXXXX."""

    METADE = chr(0xD83D)

    def mexe_na_edicao(self, dia):
        edicao = self.le("edicoes/%s.json" % dia)
        edicao["resumo"] = "Resumo com metade " + self.METADE + " de emoji."
        edicao["principais"][0]["titulo"] = "Título " + self.METADE
        apoio.grava(self.caminho("edicoes", "%s.json" % dia), json.dumps(edicao))  # json.dumps escreve \ud83d
        return edicao

    def test_contexto_edicao_falha_e_refaz_seguem(self):
        self.inicia_git()
        self.publica_o_dia()
        edicao = self.mexe_na_edicao(DIA)
        self.commit("edição de %s, mexida à mão" % DIA)
        amanha = apoio.soma(DIA, 1)
        self.assertOK(self.publica("refaz", "--url-base", apoio.BASE))
        indice = self.le("edicoes/indice.json")
        self.assertEqual(indice["edicoes"][0]["resumo"], edicao["resumo"], "cópia fiel, lida de volta")
        self.assertIn("\\ud83d", self.texto("edicoes/indice.json"))
        self.assertNotIn(self.METADE, self.texto("edicoes/%s.md" % DIA), "no texto, a metade vira espaço")
        linhas = self.assertOK(self.publica("contexto", dia=amanha))
        contexto = apoio.le(self.no_trabalho("contexto.json"))
        self.assertEqual(contexto["historias_recentes"][0]["titulo"], edicao["principais"][0]["titulo"])
        self.publica_o_dia(amanha)
        self.publica_a_falha(apoio.soma(DIA, 2))
        codigo, linhas = self.valida("--tudo", "--dia", apoio.soma(DIA, 2), agora=apoio.agora(apoio.soma(DIA, 2)))
        self.assertEqual([linha for linha in linhas if linha.startswith("ERRO INDICE")], [], "o índice bate")
        self.assertFalse(any("interna" in linha for linha in linhas), linhas)

    def test_rascunho_com_metade_de_emoji_e_corta(self):
        """O --corta regrava o rascunho antes da conferência: a metade fica escrita como \\uXXXX, e o erro vem
        da regra R17, com o caminho do campo, e não como FALHA interna."""
        novo = self.prepara()
        novo["radar"][0]["fato"] = "Fato com metade " + self.METADE + " de emoji."
        apoio.grava(self.no_trabalho("rascunho.json"), json.dumps(novo))
        foto = apoio.fotografa(self.raiz)
        linhas = self.assertFALHA(self.publica("edicao", "--corta", "r6"))
        # Uma linha só para o campo: o validador acusa, e a rede do publica.py não repete o achado.
        erros = [linha for linha in linhas if linha.startswith("ERRO ")]
        self.assertEqual([linha.split(":")[0] for linha in erros], ["ERRO R17 radar[0].fato"], linhas)
        self.assertIn("metade solta de um caractere", erros[0])
        self.assertEqual(apoio.fotografa(self.raiz), foto)
        regravado = apoio.le(self.no_trabalho("rascunho.json"))
        self.assertEqual(regravado["radar"][0]["fato"], novo["radar"][0]["fato"])
        self.assertEqual(len(regravado["radar"]), 5)


if __name__ == "__main__":
    unittest.main()
