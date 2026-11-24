#!/usr/bin/env python3
"""Testes do `publica.py falha` (CONTRATO, seção 4.3) e do `publica.py refaz` (seção 4.4).

Rode da raiz do repositório: python3 -B testes/testa_publica_falha_refaz.py
"""
import json
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "publica"))
import apoio  # noqa: E402

DIA = apoio.DIA
AMANHA = apoio.soma(DIA, 1)
DEPOIS = apoio.soma(DIA, 2)
MOTIVO = "Sem busca nem feed em 20/11: a máquina ficou sem rede."
DOMINIOS = ["energia", "alimentos", "cambio", "suprimentos", "conflito"]


def com_player(novo):
    novo["novos_players"] = [apoio.player_novo()]


class TestaAFalha(apoio.Bancada):
    def test_gera_e_publica_sem_edicao_anterior(self):
        self.publica_a_falha(motivo=MOTIVO)
        self.assertEqual(self.linhas[-1], "OK falha de %s publicada: sem edição hoje; nível 1 ROTINA (energia 1, "
                         "alimentos 1, cambio 1, suprimentos 1, conflito 1), sem edição anterior" % DIA)
        self.assertIn("gravado: edicoes/%s.json, edicoes/%s.md, edicoes/indice.json, feed.xml" % (DIA, DIA), self.linhas)
        edicao = self.le("edicoes/%s.json" % DIA)
        sem_leitura = "Sem leitura hoje."
        self.assertEqual(edicao, {
            "versao": 1, "data": DIA, "gerada_em": apoio.agora(DIA), "estado": "falha",
            "resumo": "Sem edição hoje. " + MOTIVO,
            "alerta": {"nivel": 1, "tendencia": "estavel", "motivo": MOTIVO, "dominios": [
                {"id": dominio, "nivel": 1, "tendencia": "estavel", "desde": DIA, "sem_preco": sem_preco, "gatilhos": [],
                 "leitura": sem_leitura, "vigiar": sem_leitura}
                for dominio, sem_preco in zip(DOMINIOS, (["brent"], ["trigo", "milho", "soja"], ["usd_brl"], [], []))]},
            "indicadores": [], "principais": [], "radar": [], "placar_do_dia": [], "novos_players": [], "errata": [],
            "respostas": [],
            "bastidores": {"modo": "feeds", "veiculos_consultados": 0, "feeds_ok": 0, "feeds_falhos": 0,
                           "paginas_lidas": 0, "buscas": 0, "minutos": 0, "injecoes_ignoradas": 0, "candidatos": [],
                           "veiculos_sugeridos": [], "limites": MOTIVO}})
        self.assertEqual(list(edicao), [c for c in apoio.valida.ORDEM["raiz"] if c != "exemplo"])
        self.assertEqual(self.texto("edicoes/%s.json" % DIA), apoio.comum.json_texto(edicao))
        self.assertValido("--dia", DIA)
        indice = self.le("edicoes/indice.json")
        self.assertEqual([(e["data"], e["estado"], e["nivel"], e["resumo"]) for e in indice["edicoes"]],
                         [(DIA, "falha", 1, "Sem edição hoje. " + MOTIVO)])
        feed = self.texto("feed.xml")
        self.assertIn("<title>INFOCENARIUM %s · sem edição</title>" % apoio.comum.dd_mm_aaaa(DIA), feed)
        self.assertIn('<summary type="text">Sem edição hoje. %s</summary>' % MOTIVO, feed)
        texto = self.texto("edicoes/%s.md" % DIA).splitlines()
        for linha in ("Sem edição hoje · gerada em 20/11/2026 às 18h14 (hora de Brasília)", "**Nível 1 · ROTINA**",
                      "Níveis sem base: ainda não houve edição.", "Sem itens: a rotina não fechou a edição deste dia.",
                      "**Leitura:** Sem leitura hoje.", "Nenhum indicador nesta edição."):
            self.assertIn(linha, texto)
        # Ninguém mediu nada: os bastidores da falha não dizem "coleta normal" nem dão os zeros como fato.
        bastidores = texto[texto.index("## Bastidores") + 1:]
        self.assertEqual([linha for linha in bastidores if linha], ["- O que não deu para conferir: " + MOTIVO])
        self.assertFalse([linha for linha in texto if "Modo:" in linha or "feeds lidos" in linha
                          or "Mapa de veículos em rascunho" in linha], "nem modo, nem contadores, nem nota sem item")

    def test_repete_os_niveis_e_o_desde_da_edicao_anterior(self):
        base = self.inicia_git()
        self.publica_o_dia(DIA)
        anterior = self.le("edicoes/%s.json" % DIA)
        self.commit("edição %s" % DIA)
        apoio.monta_trabalho(self.trabalho, apoio.rascunho(AMANHA), AMANHA)  # a pasta fica com coleta e indicadores
        codigo, linhas = self.publica("falha", "--motivo", "A sessão acabou antes do rascunho.", dia=AMANHA)
        self.assertEqual(codigo, 0, linhas)
        self.assertEqual(linhas[-1], "OK falha de %s publicada: sem edição hoje; nível 3 TENSÃO (energia 3, alimentos 1, "
                         "cambio 1, suprimentos 2, conflito 3), repetido de 20/11" % AMANHA)
        falha = self.le("edicoes/%s.json" % AMANHA)
        self.assertEqual((falha["alerta"]["nivel"], falha["alerta"]["tendencia"]), (3, "estavel"))
        for agora, antes in zip(falha["alerta"]["dominios"], anterior["alerta"]["dominios"]):
            self.assertEqual((agora["nivel"], agora["desde"]), (antes["nivel"], antes["desde"]), agora["id"])
            self.assertEqual((agora["tendencia"], agora["gatilhos"]), ("estavel", []))
            self.assertEqual(agora["leitura"], "Sem leitura hoje. Nível repetido de 20/11.")
            self.assertEqual(agora["vigiar"], agora["leitura"])
        # os indicadores entram (a alta do Brent está lá), mas a falha não leva gatilho, nem o de preço
        self.assertEqual(falha["indicadores"], apoio.indicadores_do_dia(AMANHA)["indicadores"])
        self.assertEqual([d["sem_preco"] for d in falha["alerta"]["dominios"]], [[], ["milho"], [], [], []])
        # e a coleta não é lida: os contadores ficam em 0, mesmo com coleta.json na pasta
        self.assertEqual((falha["bastidores"]["feeds_ok"], falha["bastidores"]["feeds_falhos"]), (0, 0))
        self.assertEqual(self.mudancas(), [("??", "edicoes/%s.json" % AMANHA), ("??", "edicoes/%s.md" % AMANHA),
                                           ("M", "edicoes/indice.json"), ("M", "feed.xml")])
        self.assertValido("--base", "HEAD", "--dia", AMANHA, agora=apoio.agora(AMANHA))
        self.assertValido("--base", base, "--dia", AMANHA, agora=apoio.agora(AMANHA))
        texto = self.texto("edicoes/%s.md" % AMANHA).splitlines()
        self.assertIn("Níveis repetidos de 20/11.", texto)
        self.assertIn("**Nível 3 · TENSÃO · estável**", texto, "com edição anterior, o estável foi medido: sai")
        self.assertNotIn("- Modo: coleta normal, pelos feeds dos veículos", texto)
        self.assertIn("Mantido desde 20/11. %s" % apoio.publica.SEM_GATILHO_NOVO, texto, "nível 3 sem gatilho na falha")
        # no dia seguinte, a falha não é edição anterior, e a janela da coleta cobre o buraco
        self.assertOK(self.publica("contexto", dia=DEPOIS))
        contexto = apoio.le(self.no_trabalho("contexto.json"))
        self.assertEqual((contexto["anterior"]["data"], contexto["janela_horas"]), (DIA, 60))

    def test_recusa_quando_o_dia_ja_tem_edicao_final(self):
        self.publica_o_dia()
        foto = apoio.fotografa(self.raiz)
        linhas = self.assertFALHA(self.publica("falha", "--motivo", MOTIVO))
        self.assertEqual(len(linhas), 1)
        self.assertTrue(linhas[0].startswith("FALHA edição %s já publicada (estado completa, no disco): a edição de falha "
                                             "não entra no lugar de edição final." % DIA), linhas[0])
        self.assertEqual(apoio.fotografa(self.raiz), foto)
        # com git, a mesma recusa vale para a edição que está no commit HEAD, completa ou reduzida
        self.inicia_git()
        self.muda("edicoes/%s.json" % DIA, lambda edicao: edicao.update(estado="reduzida"))
        self.commit("edição reduzida")
        linhas = self.assertFALHA(self.publica("falha", "--motivo", MOTIVO))
        self.assertIn("(estado reduzida, no commit HEAD)", linhas[0])

    def test_falha_por_cima_do_que_e_so_desta_execucao_limpa_os_registros(self):
        """Com git e sem commit, a edição do disco é desta execução: a falha entra no lugar, e o vetor e o player
        que ela tinha gravado saem dos registros."""
        base = self.inicia_git()
        self.publica_o_dia(muda=com_player)
        self.assertEqual(len(self.le("dados/vetores.json")["vetores"]), 2)
        self.publica_a_falha(motivo=MOTIVO)
        self.assertEqual(self.le("edicoes/%s.json" % DIA)["estado"], "falha")
        self.assertEqual(self.le("dados/vetores.json")["vetores"], [])
        self.assertEqual(self.texto("dados/vetores.json"), apoio.le_texto(os.path.join(apoio.DADOS, "vetores.json")))
        self.assertEqual(len(self.le("dados/players.json")["players"]), 30)
        self.assertValido("--base", base, "--dia", DIA)

    def test_falha_por_cima_de_falha(self):
        self.inicia_git()
        self.publica_a_falha(motivo="Primeira tentativa sem rede.")
        com_a_primeira = self.commit("falha")
        self.publica_a_falha(motivo="Segunda tentativa, também sem rede.")
        self.assertEqual(self.le("edicoes/%s.json" % DIA)["resumo"], "Sem edição hoje. Segunda tentativa, também sem rede.")
        self.assertEqual(len(self.le("edicoes/indice.json")["edicoes"]), 1)
        self.assertValido("--base", com_a_primeira, "--dia", DIA)

    def test_indicadores_que_nao_passam_nao_seguram_a_falha(self):
        tortos = apoio.indicadores_do_dia(DIA)
        tortos["indicadores"][0]["id"] = "inventado"
        self.publica_a_falha(motivo=MOTIVO, indicadores=tortos)
        avisos = [linha for linha in self.linhas if linha.startswith("aviso: indicadores.json não passou na conferência")]
        self.assertEqual(len(avisos), 1, self.linhas)
        self.assertIn("ERRO R02 indicadores[0].id", avisos[0])
        self.assertEqual(self.le("edicoes/%s.json" % DIA)["indicadores"], [])
        self.assertValido("--dia", DIA)
        # arquivo quebrado ou de outro dia conta como ausente
        for conteudo in ("{quebrado", apoio.indicadores_do_dia(apoio.soma(DIA, -3))):
            apoio.grava(self.no_trabalho("indicadores.json"), conteudo)
            linhas = self.assertOK(self.publica("falha", "--motivo", MOTIVO))
            self.assertTrue(any(linha.startswith("aviso: indicadores.json ") for linha in linhas), linhas)
            self.assertEqual(self.le("edicoes/%s.json" % DIA)["indicadores"], [])

    def test_mesma_entrada_mesmos_bytes_e_motivo_com_sinais(self):
        motivo = 'A coleta deu "tempo esgotado" em 61 feeds; a busca [WebSearch] ficou fora do ar (2 tentativas).'
        self.publica_a_falha(motivo=motivo)
        primeira = apoio.conteudos(self.raiz)
        self.publica_a_falha(motivo=motivo)
        self.assertEqual(apoio.conteudos(self.raiz), primeira)
        self.assertEqual(self.le("edicoes/%s.json" % DIA)["bastidores"]["limites"], motivo)
        self.assertIn('**Motivo do nível:** A coleta deu "tempo esgotado" em 61 feeds; a busca \\[WebSearch\\] ficou fora '
                      'do ar \\(2 tentativas\\).', self.texto("edicoes/%s.md" % DIA).splitlines())
        self.assertIn('<summary type="text">Sem edição hoje. %s</summary>' % motivo, self.texto("feed.xml"))
        self.assertValido("--dia", DIA)

    def test_relogio_fora_do_dia(self):
        foto = apoio.fotografa(self.raiz)
        linhas = self.assertFALHA(self.publica("falha", "--motivo", MOTIVO, agora=apoio.agora(apoio.soma(DIA, 2))))
        self.assertTrue(any(linha.startswith("ERRO R00 gerada_em: ") for linha in linhas))
        self.assertTrue(any(linha.startswith("aviso: o relógio marca ") for linha in linhas))
        self.assertEqual(apoio.fotografa(self.raiz), foto)

    def test_sem_dia_vale_o_do_contexto(self):
        apoio.grava(self.no_trabalho("contexto.json"), {"dia": DIA})
        codigo, linhas = self.publica("falha", "--motivo", MOTIVO, dia=None, agora="2026-11-21T03:30:00Z")
        self.assertEqual(codigo, 0, linhas)
        self.assertTrue(self.existe("edicoes/%s.json" % DIA))
        self.assertEqual(self.le("edicoes/%s.json" % DIA)["gerada_em"], "2026-11-21T03:30:00Z")


class TestaORefaz(apoio.Bancada):
    def tres_dias(self):
        """Edição com player novo, falha e edição que continua a primeira: é o arquivo que o refaz reconstrói."""
        self.publica_o_dia(DIA, com_player)
        self.publica_a_falha(AMANHA, "Sem rede em 21/11.")
        self.publica_o_dia(DEPOIS, lambda novo: apoio.continua(apoio.sem_gatilhos(novo), DIA),
                           indicadores=apoio.indicadores_calmos(DEPOIS))

    def intocaveis(self):
        return dict((caminho, ficha) for caminho, ficha in apoio.fotografa(self.raiz).items()
                    if caminho.startswith("dados") or (caminho.endswith(".json") and not caminho.endswith("indice.json")))

    def test_refaz_indice_textos_e_feed_sem_tocar_em_edicao_nem_em_dados(self):
        self.tres_dias()
        certo = apoio.conteudos(self.raiz)
        intocaveis = self.intocaveis()
        self.assertEqual(len(intocaveis), 6 + 3, "dados/ com os cinco arquivos, e as três edições")
        self.grava("edicoes/indice.json", {"versao": 1, "atualizado_em": None, "edicoes": []})
        os.unlink(self.caminho("edicoes", "%s.md" % DIA))
        self.grava("edicoes/%s.md" % AMANHA, "# texto velho, de antes de mudar a ferramenta\n")
        self.grava("feed.xml", '<?xml version="1.0"?>\n<feed xmlns="http://www.w3.org/2005/Atom"><id>%s</id></feed>\n' % apoio.BASE)
        codigo, linhas = self.valida("--tudo")
        self.assertEqual(codigo, 1, "antes do refaz, o validador acusa o índice e o texto que falta")
        linhas = self.assertOK(self.publica("refaz"))
        self.assertEqual(linhas[-1], "OK refeitos o índice (3 edições), 3 textos e o feed (3 entradas)")
        self.assertIn("gravado: edicoes/indice.json, edicoes/%s.md, edicoes/%s.md, edicoes/%s.md, feed.xml"
                      % (DIA, AMANHA, DEPOIS), linhas)
        self.assertIn("endereço base do feed: %s (o do feed.xml que já existe)" % apoio.BASE, linhas)
        self.assertEqual(apoio.conteudos(self.raiz), certo, "o refaz dá os mesmos bytes que a publicação deu")
        self.assertEqual(self.intocaveis(), intocaveis, "nem as edições nem dados/ foram tocados (nem a data de gravação)")
        self.assertValido("--dia", DEPOIS, agora=apoio.agora(DEPOIS))

    def test_refaz_duas_vezes_da_o_mesmo(self):
        self.tres_dias()
        self.assertOK(self.publica("refaz"))
        primeira = apoio.conteudos(self.raiz)
        self.assertOK(self.publica("refaz", agora="2027-01-01T00:00:00Z"))
        self.assertEqual(apoio.conteudos(self.raiz), primeira, "o refaz não usa o relógio")

    def test_edicao_ilegivel_para_sem_gravar(self):
        self.tres_dias()
        self.grava("edicoes/%s.json" % AMANHA, '{"data": "%s", "estado": ' % AMANHA)
        os.unlink(self.caminho("edicoes", "%s.md" % DIA))
        foto = apoio.fotografa(self.raiz)
        linhas = self.assertFALHA(self.publica("refaz"))
        self.assertIn("edicoes/%s.json" % AMANHA, linhas[-1])
        self.assertEqual(apoio.fotografa(self.raiz), foto)
        self.grava("edicoes/%s.json" % AMANHA, "[]")
        linhas = self.assertFALHA(self.publica("refaz"))
        self.assertIn("edicoes/%s.json" % AMANHA, linhas[-1])

    def test_texto_sem_edicao_ganha_aviso_e_nao_e_apagado(self):
        self.publica_o_dia()
        self.grava("edicoes/2026-01-01.md", "# sobra\n")
        linhas = self.assertOK(self.publica("refaz"))
        self.assertIn("aviso: edicoes/2026-01-01.md não tem edição (falta edicoes/2026-01-01.json). O refaz não apaga "
                      "arquivo: apague-o à mão.", linhas)
        self.assertEqual(self.texto("edicoes/2026-01-01.md"), "# sobra\n")

    def test_sem_edicao_nenhuma(self):
        linhas = self.assertOK(self.publica("refaz"))
        self.assertEqual(linhas[-1], "OK refeitos o índice (0 edições), 0 textos e o feed (0 entradas)")
        self.assertEqual(self.le("edicoes/indice.json"), {"versao": 1, "atualizado_em": None, "edicoes": []})
        feed = self.texto("feed.xml")
        self.assertNotIn("<entry>", feed)
        self.assertIn("<updated>1970-01-01T00:00:00Z</updated>", feed)
        self.assertIn("<id>./</id>", feed)
        self.assertValido()

    def test_so_com_a_edicao_de_exemplo(self):
        self.grava("edicoes/%s.json" % apoio.DIA_DO_EXEMPLO, apoio.exemplo())
        linhas = self.assertOK(self.publica("refaz"))
        self.assertEqual(linhas[-1], "OK refeitos o índice (1 edição), 1 texto e o feed (0 entradas)")
        self.assertEqual([(e["data"], e["exemplo"]) for e in self.le("edicoes/indice.json")["edicoes"]],
                         [(apoio.DIA_DO_EXEMPLO, True)])
        feed = self.texto("feed.xml")
        self.assertNotIn("<entry>", feed, "edição de exemplo não entra no feed")
        # CONTRATO, seção 4.5: a de exemplo também não conta para o updated; sem entrada, vale a data fixa.
        self.assertIn("<updated>1970-01-01T00:00:00Z</updated>", feed)
        self.assertNotIn(apoio.exemplo()["gerada_em"], feed)
        self.assertTrue(self.texto("edicoes/%s.md" % apoio.DIA_DO_EXEMPLO).startswith("EDIÇÃO DE EXEMPLO · dados fictícios\n\n# INFOCENARIUM · 19/11/2026\n"))

    def test_o_refaz_nao_depende_dos_dados(self):
        """Com dados/ ilegível, os textos saem com os ids no lugar dos nomes, e o feed sem o rótulo do nível."""
        self.publica_o_dia()
        for nome in ("regua", "veiculos", "players"):
            self.grava("dados/%s.json" % nome, "{quebrado")
        linhas = self.assertOK(self.publica("refaz"))
        self.assertEqual(len([linha for linha in linhas if linha.startswith("aviso: dados/")]), 3)
        texto = self.texto("edicoes/%s.md" % DIA)
        self.assertIn("**Nível 3**", texto.splitlines(), "sem rótulo e, sem edição anterior, sem o estável")
        self.assertNotIn("Mapa de veículos em rascunho", texto, "mapa ilegível não é mapa em rascunho")
        self.assertIn("- `nyt` · `ordem_global` · alvo: República de Exemplo \\(fictícia\\) · ", texto)
        self.assertIn("<title>INFOCENARIUM 20/11/2026 · nível 3</title>", self.texto("feed.xml"))

    def test_veiculo_que_saiu_do_mapa_aparece_pelo_id(self):
        self.publica_o_dia()
        self.muda("dados/veiculos.json",
                  lambda mapa: mapa.update(veiculos=[v for v in mapa["veiculos"] if v["id"] != "nyt"]))
        self.assertOK(self.publica("refaz"))
        texto = self.texto("edicoes/%s.md" % DIA)
        self.assertIn("- `nyt` · Partido da Ordem Global · alvo: ", texto)
        self.assertNotIn("The New York Times", texto)


if __name__ == "__main__":
    unittest.main()
