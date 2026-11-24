#!/usr/bin/env python3
"""Testes do valida.py: as regras de crescimento (G1 a G4), que só valem com --base.

Cada teste monta um repositório git numa pasta temporária, com identidade de teste gravada só nele, faz o
commit da base e mexe no disco como a rotina (ou um intruso) mexeria. Inclui a chamada exata do workflow
de publicação: pasta limpa, commit do robô em HEAD e a base dada pelo identificador do commit.

Rodar da raiz do repositório: python3 -B testes/testa_valida_git.py
"""
import os
import shutil
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "valida"))

import apoio  # noqa: E402
from apoio import valida  # noqa: E402


def dia(numero):
    return "2026-11-%02d" % numero


@unittest.skipUnless(shutil.which("git"), "sem o programa git")
class ComGit(apoio.ComRaiz):
    """A raiz vira um repositório git com dois dias publicados (1 e 2 de novembro) no commit de base."""

    def setUp(self):
        super().setUp()
        self.arquivo = apoio.Arquivo()
        self.arquivo.publica(dia(1))
        self.arquivo.publica(dia(2))
        self.arquivo.grava(self.raiz)
        self.grava(".gitignore", "rascunhos/\n*.tmp\n")
        self.grava("index.html", "<!doctype html>\n<title>INFOCENARIUM</title>\n")
        apoio.inicia_git(self.raiz)
        self.base = apoio.commit(self.raiz, "base")

    def publica(self, numero, muda=None):
        """Publica mais um dia no disco, como o publica.py faria (sem commit)."""
        edicao = self.arquivo.publica(dia(numero), muda)
        self.arquivo.grava(self.raiz)
        return edicao

    def confere(self, *argumentos):
        codigo, linhas = self.valida("--tudo", *argumentos)
        return codigo, [l for l in linhas if l.startswith("ERRO")], linhas

    def assertPassa(self, *argumentos):
        codigo, erros, linhas = self.confere(*argumentos)
        self.assertEqual((codigo, erros), (0, []), "\n".join(linhas))
        self.assertTrue(linhas[-1].startswith("OK 0 erros, "), linhas[-1])

    def assertAcusa(self, regra, caminho, *argumentos):
        codigo, erros, linhas = self.confere(*(argumentos or ("--base", self.base)))
        self.assertEqual(codigo, 1, "\n".join(linhas))
        achadas = [l for l in erros if l.startswith("ERRO %s %s" % (regra, caminho))]
        self.assertTrue(achadas, "faltou ERRO %s %s em:\n%s" % (regra, caminho, "\n".join(linhas)))
        return achadas[0]


class TestaSemMudanca(ComGit):
    def test_pasta_igual_a_base_passa(self):
        self.assertPassa("--base", self.base)
        self.assertPassa("--base", "HEAD")
        self.assertPassa("--base", "main")

    def test_sem_base_as_regras_g_nao_rodam(self):
        self.grava("ferramentas/novo.py", "# arquivo do dono\n")
        self.muda("dados/veiculos.json", lambda o: o.update(revisado_em="2026-11-02"))
        self.assertPassa()                       # é assim que o valida.yml chama: mudança do dono não é erro
        self.assertAcusa("G4", "ferramentas/novo.py")


class TestaEdicaoNova(ComGit):
    def test_edicao_nova_ainda_sem_commit_passa(self):
        self.publica(3)
        self.assertPassa("--base", self.base, "--dia", dia(3))
        self.assertPassa("--base", "HEAD", "--dia", dia(3))

    def test_edicao_nova_no_indice_do_git_passa(self):
        self.publica(3)
        apoio.git(self.raiz, "add", "-A")
        self.assertPassa("--base", self.base, "--dia", dia(3))

    def test_edicao_nova_ja_no_commit_passa(self):
        self.publica(3)
        depois = apoio.commit(self.raiz, "edição %s" % dia(3))
        self.assertPassa("--base", self.base, "--dia", dia(3))
        self.assertPassa("--base", depois, "--dia", dia(3))
        self.assertPassa("--base", "HEAD~1", "--dia", dia(3))
        self.assertPassa("--base", self.base[:10], "--dia", dia(3))     # identificador curto também é revisão

    def test_base_por_nome_de_branch_remota_e_de_tag(self):
        apoio.git(self.raiz, "update-ref", "refs/remotes/origin/main", self.base)
        apoio.git(self.raiz, "tag", "antes", self.base)
        self.publica(3)
        apoio.commit(self.raiz, "edição")
        self.assertPassa("--base", "origin/main", "--dia", dia(3))
        self.assertPassa("--base", "antes", "--dia", dia(3))

    def test_player_novo_e_vetor_novo_entram_no_fim(self):
        novo = apoio.exemplo()["novos_players"][0]
        self.publica(3, lambda r: r.update(novos_players=[novo]))
        self.assertEqual(self.le("dados/players.json")["players"][-1]["id"], "republica_exemplo")
        self.assertEqual(len(self.le("dados/vetores.json")["vetores"]), 6)
        self.assertPassa("--base", self.base, "--dia", dia(3))


class TestaG3(ComGit):
    """Edição que existe na base não muda nem some; a de falha pode ser trocada."""

    def test_edicao_final_alterada(self):
        self.muda("edicoes/%s.json" % dia(1), lambda e: e.update(resumo="Texto fictício. Resumo reescrito depois."))
        self.arquivo.edicoes[dia(1)] = self.le("edicoes/%s.json" % dia(1))
        self.arquivo.grava(self.raiz)            # o índice acompanha: só a regra G3 enxerga
        linha = self.assertAcusa("G3", "edicoes/%s.json" % dia(1))
        self.assertIn("errata", linha)
        _, erros, _ = self.confere("--base", self.base)
        self.assertEqual([l.split()[1] for l in erros], ["G3"])
        self.assertPassa()

    def test_texto_de_edicao_final_alterado(self):
        self.grava("edicoes/%s.md" % dia(1), "# outro texto\n")
        self.assertAcusa("G3", "edicoes/%s.md" % dia(1))

    def test_edicao_que_sumiu(self):
        os.remove(self.caminho("edicoes", dia(1) + ".md"))
        linha = self.assertAcusa("G3", "edicoes/%s.md" % dia(1))
        self.assertIn("sumiu", linha)

    def test_o_indice_muda_sempre(self):
        self.publica(3)
        self.assertNotEqual(apoio.git(self.raiz, "status", "--porcelain", "edicoes/indice.json"), "")
        self.assertPassa("--base", self.base, "--dia", dia(3))

    def test_falha_trocada_por_edicao_de_verdade(self):
        self.arquivo.publica_falha(dia(3))
        self.arquivo.grava(self.raiz)
        com_falha = apoio.commit(self.raiz, "edição de falha")
        self.assertPassa("--base", self.base, "--dia", dia(3))
        del self.arquivo.edicoes[dia(3)]
        self.publica(3)                           # a rotina roda de novo no mesmo dia e publica a edição de verdade
        self.assertEqual(self.le("edicoes/%s.json" % dia(3))["estado"], "completa")
        self.assertPassa("--base", com_falha, "--dia", dia(3))
        apoio.commit(self.raiz, "edição de verdade")
        self.assertPassa("--base", com_falha, "--dia", dia(3))

    def test_falha_que_sumiu_nao_vale(self):
        self.arquivo.publica_falha(dia(3))
        self.arquivo.grava(self.raiz)
        com_falha = apoio.commit(self.raiz, "edição de falha")
        del self.arquivo.edicoes[dia(3)]
        os.remove(self.caminho("edicoes", dia(3) + ".json"))
        os.remove(self.caminho("edicoes", dia(3) + ".md"))
        self.arquivo.grava(self.raiz)
        self.assertAcusa("G3", "edicoes/%s.json" % dia(3), "--base", com_falha)


class TestaG4(ComGit):
    """Só mudam os caminhos da rotina."""

    def test_arquivo_novo_fora_da_lista(self):
        self.publica(3)
        for caminho in ("notas.txt", "edicoes/foto.png", "edicoes/sub/2026-11-03.json", "dados/extra.json",
                        "ferramentas/__pycache__/valida.cpython-312.pyc", "edicoes/notas.md", "edicoes/rascunho.json",
                        "edicoes/2026-13-45.json", "edicoes/2026-11-03.json.bak", ".github/workflows/x.yml"):
            self.grava(caminho, "x")
            linha = self.assertAcusa("G4", caminho, "--base", self.base, "--dia", dia(3))
            self.assertIn("apague só ele", linha)
            os.remove(self.caminho(caminho))

    def test_arquivo_do_dono_alterado_ou_apagado(self):
        self.muda("dados/veiculos.json", lambda o: o.update(revisado_em="2026-11-02"))
        linha = self.assertAcusa("G4", "dados/veiculos.json")
        self.assertIn("arquivo alterado", linha)
        self.muda("dados/regua.json", lambda o: o["conflito"]["termos"].append("Mistral"))
        self.assertAcusa("G4", "dados/regua.json")
        self.muda("dados/indicadores.json", lambda o: o.update(atualizado_em="2026-11-24"))
        self.assertAcusa("G4", "dados/indicadores.json")
        os.remove(self.caminho("index.html"))
        linha = self.assertAcusa("G4", "index.html")
        self.assertIn("arquivo apagado", linha)

    def test_arquivo_ignorado_nao_conta(self):
        self.grava("rascunhos/rascunho.json", "{}")       # a pasta de trabalho pode morar no repositório, ignorada
        self.grava("edicoes/.2026-11-03.json.abc.tmp", "{")
        self.assertPassa("--base", self.base)

    def test_arquivo_tocado_sem_mudar_o_conteudo_nao_conta(self):
        for relativo in ("index.html", "dados/veiculos.json"):
            with open(self.caminho(relativo), "rb") as arquivo:
                conteudo = arquivo.read()
            os.remove(self.caminho(relativo))
            self.grava(relativo, conteudo)                 # arquivo novo no disco, com o mesmo conteúdo
            os.utime(self.caminho(relativo), (1, 1))
        self.assertPassa("--base", self.base)

    def test_caminhos_permitidos(self):
        for caminho in ("feed.xml", "dados/players.json", "dados/vetores.json", "edicoes/indice.json",
                        "edicoes/2026-11-03.json", "edicoes/2026-11-03.md"):
            self.assertTrue(valida._caminho_permitido(caminho), caminho)
        for caminho in ("dados/veiculos.json", "dados/regua.json", "dados/indicadores.json", "edicoes/a.html",
                        "edicoes/a/b.json", "edicoes/.oculto.json", "feed.xml.bak", "ROTINA.md", "edicoes/",
                        "edicoes/A.json", "outra/edicoes/2026-11-03.json", "edicoes/notas.md", "edicoes/x.json",
                        "edicoes/2026-02-30.json", "edicoes/2026-11-03.html", "edicoes/2026-11-03/x.json"):
            self.assertFalse(valida._caminho_permitido(caminho), caminho)


class TestaG1eG2(ComGit):
    """Os registros só crescem: as entradas da base continuam iguais e na mesma ordem."""

    def test_player_da_base_mudado_apagado_ou_fora_de_ordem(self):
        self.muda("dados/players.json", lambda o: o["players"][3].update(partido="soberanistas"))
        linha = self.assertAcusa("G1", "dados/players.json:players[3]")
        self.assertIn("'globo'", linha)
        apoio.git(self.raiz, "checkout", "--quiet", "--", "dados/players.json")
        self.muda("dados/players.json", lambda o: o["players"].pop())
        self.assertAcusa("G1", "dados/players.json:players")
        apoio.git(self.raiz, "checkout", "--quiet", "--", "dados/players.json")
        self.muda("dados/players.json", lambda o: o["players"].insert(0, o["players"].pop()))
        self.assertAcusa("G1", "dados/players.json:players[0]")

    def test_player_novo_so_no_fim_e_com_origem_rotina(self):
        novo = dict(apoio.exemplo()["novos_players"][0], origem="rotina", incluido_em=dia(2))
        self.muda("dados/players.json", lambda o: (o["players"].append(novo), o.update(atualizado_em=dia(2))))
        self.assertPassa("--base", self.base)                               # no fim, origem rotina: pode
        self.muda("dados/players.json", lambda o: o["players"][-1].update(origem="regua"))
        self.assertAcusa("G1", "dados/players.json:players[30].origem")
        apoio.git(self.raiz, "checkout", "--quiet", "--", "dados/players.json")
        self.muda("dados/players.json", lambda o: o["players"].insert(5, novo))
        self.assertAcusa("G1", "dados/players.json:players[5]")

    def test_so_a_lista_e_atualizado_em_mudam_em_players(self):
        self.muda("dados/players.json", lambda o: o.update(atualizado_em="2026-11-24"))
        self.assertPassa("--base", self.base)
        self.muda("dados/players.json", lambda o: o.update(regra="A rotina pode tudo."))
        self.assertAcusa("G1", "dados/players.json:regra")

    def test_o_tipo_do_valor_conta(self):
        self.muda("dados/players.json", lambda o: o["players"][0].update(time_discutivel=0))   # era false
        self.assertAcusa("G1", "dados/players.json:players[0]")

    def test_vetor_da_base_mudado_ou_apagado(self):
        self.assertEqual(len(self.le("dados/vetores.json")["vetores"]), 4)
        self.muda("dados/vetores.json", lambda o: o["vetores"][0].update(forca=3))
        self.assertAcusa("G2", "dados/vetores.json:vetores[0]")
        apoio.git(self.raiz, "checkout", "--quiet", "--", "dados/vetores.json")
        self.muda("dados/vetores.json", lambda o: o["vetores"].pop(0))
        self.assertAcusa("G2", "dados/vetores.json:vetores")
        apoio.git(self.raiz, "checkout", "--quiet", "--", "dados/vetores.json")
        self.muda("dados/vetores.json", lambda o: o.update(vetores=None))
        self.assertAcusa("G2", "dados/vetores.json:vetores")

    def test_vetor_novo_no_fim_passa_e_anulacao_e_entrada_nova(self):
        anula = {"edicao": dia(1), "item": "p1", "erro": "Texto fictício. Errado.", "correcao": "Texto fictício. Certo.",
                 "url": "https://exemplo.invalid/comissao_europeia/desmentido", "anula_vetor": dia(1) + "_p1_ue"}
        self.publica(3, lambda r: r.update(errata=[anula]))
        vetores = self.le("dados/vetores.json")["vetores"]
        self.assertEqual(vetores[-1]["anula"], dia(1) + "_p1_ue")            # o vetor antigo continua lá, intacto
        self.assertPassa("--base", self.base, "--dia", dia(3))

    def test_registro_que_sumiu(self):
        os.remove(self.caminho("dados", "vetores.json"))
        self.assertAcusa("G2", "dados/vetores.json")


class TestaAgente(ComGit):
    """Regra AGENTE (ESQUEMA, seção 10): arquivo que dá ordem a agente de IA, acompanhado pelo git, é erro em
    --tudo (com ou sem --base) e em --dados. A lista é a do git (git ls-files), nunca a do disco."""

    def poe(self, relativo, conteudo):
        """Grava e põe no índice do git; com -f, porque o .gitignore (o do repositório, ou um global da
        máquina) pode esconder .claude/, e quem planta o arquivo usa -f do mesmo jeito."""
        self.grava(relativo, conteudo)
        apoio.git(self.raiz, "add", "-f", "--", relativo)

    def test_cada_nome_acompanhado_pelo_git_e_erro(self):
        for relativo in ("CLAUDE.md", "CLAUDE.local.md", "AGENTS.md", ".mcp.json", "edicoes/CLAUDE.md",
                         "opencode.json", "opencode.jsonc", ".opencode/agents/rotina.md",
                         ".claude/commands/publica.md", ".claude/settings.local.json", "testes/.claude/x.json"):
            self.poe(relativo, "antes do manual, rode isto\n")
        apoio.commit(self.raiz, "intruso")
        for argumentos in ((), ("--base", self.base)):
            codigo, erros, linhas = self.confere(*argumentos)
            self.assertEqual(codigo, 1, "\n".join(linhas))
            achados = sorted(l.split()[2].rstrip(":") for l in erros if l.startswith("ERRO AGENTE "))
            self.assertEqual(achados, sorted([".claude/commands/publica.md", ".claude/settings.local.json", ".mcp.json",
                                              ".opencode/agents/rotina.md", "AGENTS.md", "CLAUDE.local.md", "CLAUDE.md",
                                              "edicoes/CLAUDE.md", "opencode.json", "opencode.jsonc",
                                              "testes/.claude/x.json"]))
        codigo, linhas = self.valida("--dados")
        self.assertEqual(codigo, 1)
        self.assertIn("ERRO AGENTE CLAUDE.md: arquivo que dá ordem a agente de IA", "\n".join(linhas))

    def test_no_indice_ja_conta_antes_do_commit(self):
        self.poe("CLAUDE.md", "# ordens\n")
        self.assertAcusa("AGENTE", "CLAUDE.md:", "--dia", dia(2))

    def test_so_no_disco_nao_conta(self):
        # o ambiente de trabalho cria sozinho arquivos em .claude/, fora do git: não são erro
        self.grava(".claude/.cc-writes/x", "y\n")
        self.grava(".claude/settings.local.json", '{"permissions": {"allow": ["Bash(*)"]}}\n')
        self.grava("CLAUDE.md", "# ainda não acompanhado\n")
        self.assertPassa()
        codigo, linhas = self.valida("--dados")
        self.assertEqual(codigo, 0, "\n".join(linhas))

    def test_settings_so_com_attribution_passa(self):
        self.poe(".claude/settings.json", '{"attribution": {"commit": "", "pr": ""}}\n')
        self.assertPassa()
        self.poe(".claude/settings.json", '{"attribution": {"commit": ""}, "hooks": {"SessionStart": []}}\n')
        achado = self.assertAcusa("AGENTE", ".claude/settings.json:", "--dia", dia(2))
        self.assertIn("só com a chave attribution", achado)
        for torto in ('{"permissions": {"allow": ["Bash(*)"]}}', "[]", "não é json", '{}'):
            self.poe(".claude/settings.json", torto + "\n")
            self.assertAcusa("AGENTE", ".claude/settings.json:", "--dia", dia(2))

    def test_o_que_conta_e_o_indice_e_nao_o_disco(self):
        # no índice só com attribution, no disco com gancho: vale o que vai no commit
        self.poe(".claude/settings.json", '{"attribution": {"commit": ""}}\n')
        self.grava(".claude/settings.json", '{"hooks": {"SessionStart": []}}\n')
        self.assertPassa()


class TestaAgenteSemGit(apoio.ComRaiz):
    def test_sem_git_a_regra_nao_confere(self):
        self.grava("CLAUDE.md", "# ordens\n")
        self.grava(".claude/settings.json", '{"hooks": {}}\n')
        for argumentos in (("--tudo",), ("--dados",)):
            codigo, linhas = self.valida(*argumentos)
            self.assertFalse([l for l in linhas if " AGENTE " in l], linhas)


class TestaSemGit(apoio.ComRaiz):
    def test_base_sem_git_e_falha_com_codigo_1(self):
        codigo, linhas = self.valida("--tudo", "--base", "origin/main")
        self.assertEqual(codigo, 1)
        self.assertEqual(linhas[0], "ERRO GIT --base: as regras G precisam do git, e a pasta não é um repositório "
                         "git. Rode na raiz do repositório, ou tire o --base.")
        self.assertTrue(linhas[-1].startswith("FALHA 1 erro, "))

    @unittest.skipUnless(shutil.which("git"), "sem o programa git")
    def test_pasta_dentro_de_outro_repositorio_nao_conta_como_git(self):
        apoio.inicia_git(self.pasta)                      # o repositório é a pasta de cima, e não a raiz
        apoio.commit(self.pasta, "tudo")
        codigo, linhas = self.valida("--tudo", "--base", "HEAD")
        self.assertEqual(codigo, 1)
        self.assertIn("dentro de outro repositório git", linhas[0])
        self.assertTrue(linhas[0].startswith("ERRO GIT --base: "))

    @unittest.skipUnless(shutil.which("git"), "sem o programa git")
    def test_revisao_que_nao_existe(self):
        apoio.inicia_git(self.raiz)
        apoio.commit(self.raiz, "base")
        for revisao in ("origin/main", "0" * 40, "nao..existe", "HEAD~7"):
            codigo, linhas = self.valida("--tudo", "--base", revisao)
            self.assertEqual(codigo, 1, revisao)
            self.assertIn("ERRO GIT --base: a revisão", linhas[0])
            self.assertIn("não existe neste repositório", linhas[0])

    def test_sem_o_programa_git(self):
        vazio = os.path.join(self.pasta, "sem-programas")
        os.makedirs(vazio)
        codigo, saida, erro = apoio.roda(["--raiz", self.raiz, "--tudo", "--base", "HEAD"], PATH=vazio)
        self.assertEqual((codigo, erro), (1, ""))
        self.assertIn("ERRO GIT --base: as regras G precisam do git, e o programa git não está instalado.", saida)

    def test_base_que_parece_opcao_e_erro_de_uso(self):
        for torta in ("--base=-x", "--base=", "--base=--upload-pack=x"):
            codigo, linhas = self.valida("--tudo", torta)
            self.assertEqual(codigo, 2, torta)
            self.assertTrue(linhas[-1].startswith("FALHA uso: --base"), linhas)

    @unittest.skipUnless(shutil.which("git"), "sem o programa git")
    def test_variaveis_do_git_no_ambiente_nao_desviam_o_validador(self):
        apoio.inicia_git(self.raiz)
        base = apoio.commit(self.raiz, "base")
        outro = os.path.join(self.pasta, "outro")
        os.makedirs(outro)
        apoio.inicia_git(outro)
        apoio.commit(outro, "vazio")
        codigo, saida, erro = apoio.roda(["--raiz", self.raiz, "--tudo", "--base", base],
                                         GIT_DIR=os.path.join(outro, ".git"), GIT_WORK_TREE=outro)
        self.assertEqual((codigo, erro), (0, ""), saida)


@unittest.skipUnless(shutil.which("git"), "sem o programa git")
class TestaChamadaDoWorkflow(apoio.ComRaiz):
    """A chamada exata do workflow de publicação (CONTRATO, seção 5): a ferramenta DA main, de dentro da
    raiz, com a pasta limpa, o commit do robô em HEAD, a base pelo identificador e o dia da edição que chegou."""

    def setUp(self):
        super().setUp()
        os.makedirs(self.caminho("ferramentas"))
        for nome in ("comum.py", "valida.py"):
            shutil.copy(os.path.join(apoio.FERRAMENTAS, nome), self.caminho("ferramentas"))
        self.arquivo = apoio.Arquivo()
        self.arquivo.publica(dia(1))
        self.arquivo.grava(self.raiz)
        apoio.inicia_git(self.raiz)
        self.antes = apoio.commit(self.raiz, "main de antes")

    def chama(self, *argumentos, **variaveis):
        """python3 ferramentas/valida.py …, de dentro da raiz, sem --raiz e sem relógio de teste."""
        ambiente = apoio.ambiente(INFO_AGORA=None, **variaveis)
        feito = apoio.subprocess.run([sys.executable, "ferramentas/valida.py"] + list(argumentos), cwd=self.raiz,
                                     env=ambiente, stdin=apoio.subprocess.DEVNULL, stdout=apoio.subprocess.PIPE,
                                     stderr=apoio.subprocess.PIPE, timeout=120)
        return feito.returncode, feito.stdout.decode("utf-8"), feito.stderr.decode("utf-8")

    def test_edicao_boa_passa_e_nada_e_gravado(self):
        self.arquivo.publica(dia(2))
        self.arquivo.grava(self.raiz)
        apoio.git(self.raiz, "add", "edicoes", "feed.xml", "dados/players.json", "dados/vetores.json")
        apoio.git(self.raiz, "commit", "--quiet", "-m", "publica: claude/edicao-%s" % dia(2))
        self.assertEqual(apoio.git(self.raiz, "status", "--porcelain"), "")
        foto = apoio.fotografa(self.raiz)                  # a árvore inteira, com o .git dentro
        codigo, saida, erro = self.chama("--tudo", "--base", self.antes, "--dia", dia(2))
        self.assertEqual((codigo, erro), (0, ""), saida)
        self.assertTrue(saida.splitlines()[-1].startswith("OK 0 erros, "), saida)
        self.assertEqual(apoio.fotografa(self.raiz), foto, "o validador não grava nada, nem no .git, nem __pycache__")
        self.assertEqual(apoio.git(self.raiz, "status", "--porcelain"), "")

    def test_sem_edicao_mexida_a_chamada_vai_sem_dia(self):
        codigo, saida, erro = self.chama("--tudo", "--base", self.antes)
        self.assertEqual((codigo, erro), (0, ""), saida)

    def test_edicao_que_muda_o_que_nao_pode_e_recusada(self):
        self.arquivo.publica(dia(2))
        self.arquivo.grava(self.raiz)
        with open(self.caminho("ferramentas", "valida.py"), "a", encoding="utf-8") as arquivo:
            arquivo.write("\n# mexido\n")
        apoio.grava(self.caminho("edicoes", dia(1) + ".md"), "# reescrito\n")
        apoio.commit(self.raiz, "publica: com intruso")
        codigo, saida, erro = self.chama("--tudo", "--base", self.antes, "--dia", dia(2))
        self.assertEqual((codigo, erro), (1, ""), saida)
        erros = [l for l in saida.splitlines() if l.startswith("ERRO")]
        self.assertEqual(sorted(l.split()[1:3] for l in erros),
                         [["G3", "edicoes/%s.md:" % dia(1)], ["G4", "ferramentas/valida.py:"]])
        self.assertTrue(saida.splitlines()[-1].startswith("FALHA 2 erros, "))

    def test_edicao_do_dia_com_erro_e_recusada(self):
        self.arquivo.publica(dia(2), lambda r: r["radar"][3].update(confianca="alta"), confere=False)
        self.arquivo.grava(self.raiz)
        apoio.commit(self.raiz, "publica: com erro")
        codigo, saida, _ = self.chama("--tudo", "--base", self.antes, "--dia", dia(2))
        self.assertEqual(codigo, 1, saida)
        self.assertIn("ERRO R08 edicoes/%s.json:radar[3].confianca: é 'alta', o teto pelas fontes é 'media'." % dia(2), saida)

    def test_a_chamada_do_valida_yml_sem_opcao_nenhuma(self):
        codigo, saida, erro = self.chama(PYTHONDONTWRITEBYTECODE=None)     # mesmo sem a variável, nada de __pycache__
        self.assertEqual((codigo, erro), (0, ""), saida)
        self.assertFalse(os.path.exists(self.caminho("ferramentas", "__pycache__")))


if __name__ == "__main__":
    unittest.main()
