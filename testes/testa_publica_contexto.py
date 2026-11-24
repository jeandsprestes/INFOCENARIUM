#!/usr/bin/env python3
"""Testes do `publica.py contexto` (CONTRATO, seção 4.1): contexto.json, mapa.txt e modelo.txt.

Rode da raiz do repositório: python3 -B testes/testa_publica_contexto.py
O histórico de cada teste é publicado na hora, dia a dia, pela própria ferramenta, em pasta temporária.
"""
import json
import os
import re
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "publica"))
import apoio  # noqa: E402

CHAVES = ["dia", "janela_horas", "edicao_do_dia", "anterior", "alerta_anterior", "historias_recentes",
          "vigiar_vencendo", "candidatos", "vetores_recentes"]
DOMINIOS = ["energia", "alimentos", "cambio", "suprimentos", "conflito"]


def dia(n):
    """Os dias do histórico de teste: dia(0) é 10/11/2026."""
    return apoio.soma("2026-11-10", n)


class ComContexto(apoio.Bancada):
    def contexto(self, do_dia, **opcoes):
        self.assertOK(self.publica("contexto", dia=do_dia, **opcoes))
        return apoio.le(self.no_trabalho("contexto.json"))


class TestaSemEdicaoNenhuma(ComContexto):
    def test_o_contexto_da_primeira_edicao(self):
        codigo, linhas = self.publica("contexto")
        self.assertEqual((codigo, linhas[-1]), (0, "OK contexto de %s" % apoio.DIA))
        self.assertEqual(sorted(os.listdir(self.trabalho)), ["contexto.json", "mapa.txt", "modelo.txt"])
        contexto = apoio.le(self.no_trabalho("contexto.json"))
        self.assertEqual(list(contexto), CHAVES, "as chaves saem na ordem do CONTRATO")
        self.assertEqual(contexto, {
            "dia": apoio.DIA, "janela_horas": 36, "edicao_do_dia": None, "anterior": None,
            "alerta_anterior": {"nivel": 1, "dominios": [
                {"id": dominio, "nivel": 1, "desde": apoio.DIA, "edicoes_sem_gatilho": 0,
                 "desce_hoje_sem_gatilho": False, "origem": None} for dominio in DOMINIOS]},
            "historias_recentes": [], "vigiar_vencendo": [], "candidatos": [], "vetores_recentes": []})
        self.assertEqual(list(contexto["alerta_anterior"]["dominios"][0]),
                         ["id", "nivel", "desde", "edicoes_sem_gatilho", "desce_hoje_sem_gatilho", "origem"])
        texto = "\n".join(linhas)
        for trecho in ("dia %s · janela de 36 horas" % apoio.DIA, "edição do dia: não há", "anterior: não há",
                       "alerta anterior: nível 1 ROTINA", "vigiar vencendo: 0", "146 veículos"):
            self.assertIn(trecho, texto)

    def test_o_contexto_nao_grava_no_repositorio(self):
        foto = apoio.fotografa(self.raiz)
        self.assertOK(self.publica("contexto"))
        self.assertEqual(apoio.fotografa(self.raiz), foto)

    def test_sem_dia_vale_hoje_em_brasilia(self):
        """21h de 20/11 em UTC ainda é dia 20 em Brasília; 2h de 21/11 em UTC também (são 23h do dia 20)."""
        for relogio, esperado in (("2026-11-20T21:00:00Z", "2026-11-20"), ("2026-11-21T02:59:59Z", "2026-11-20"),
                                  ("2026-11-21T03:00:00Z", "2026-11-21")):
            self.assertOK(self.publica("contexto", dia=None, agora=relogio))
            self.assertEqual(apoio.le(self.no_trabalho("contexto.json"))["dia"], esperado)

    def test_o_contexto_nao_le_o_dia_do_contexto_antigo(self):
        """No `contexto` o padrão de --dia é sempre hoje: é ele que cria o contexto (CONTRATO, seção 0)."""
        apoio.grava(self.no_trabalho("contexto.json"), {"dia": "2026-11-01"})
        self.assertOK(self.publica("contexto", dia=None, agora=apoio.agora(apoio.DIA)))
        self.assertEqual(apoio.le(self.no_trabalho("contexto.json"))["dia"], apoio.DIA)

    def test_mesma_entrada_mesmos_bytes(self):
        self.assertOK(self.publica("contexto"))
        antes = apoio.conteudos(self.trabalho)
        self.assertOK(self.publica("contexto", agora=apoio.agora(apoio.DIA, "23:59:59")))
        self.assertEqual(apoio.conteudos(self.trabalho), antes, "o contexto não leva carimbo de hora")
        texto = apoio.le_texto(self.no_trabalho("contexto.json"))
        self.assertEqual(texto, apoio.comum.json_texto(json.loads(texto)), "JSON no formato de gravação do CONTRATO")


class TestaComVariasEdicoes(ComContexto):
    """Um histórico de quatro dias: edição com gatilhos, falha, dois dias calmos (um com errata, outro com
    resposta). O contexto do quinto dia tem de contar tudo isso."""

    PERGUNTAS = {"p1": "O Reino de Amostra responde com ataque militar até 12/11?",
                 "p2": "A lei fictícia é sancionada até 11/11?",
                 "p3": "A República de Exemplo autoriza a entrada dos observadores até 30/11?"}

    def primeiro_dia(self, novo):
        for item in novo["principais"]:
            item["vigiar"][0] = self.PERGUNTAS[item["id"]]
        novo["bastidores"]["candidatos"].append({"id": "porto_ficticio", "nome": "Porto Fictício",
                                                 "motivo": "Texto fictício. Dono do terminal atacado."})

    def dia_calmo(self, novo):
        apoio.continua(apoio.sem_vetores(apoio.sem_gatilhos(novo)), dia(0))

    def monta_o_historico(self):
        self.publica_o_dia(dia(0), self.primeiro_dia)
        self.publica_a_falha(dia(1), "Sem busca nem feed em 11/11.")

        def com_errata(novo):
            self.dia_calmo(novo)
            novo["errata"] = [{"edicao": dia(0), "item": "p1", "erro": "Texto fictício. A meta não foi suspensa.",
                               "correcao": "Texto fictício. A Comissão Europeia desmentiu a suspensão em 12/11.",
                               "url": "https://exemplo.invalid/comissao_europeia/meta-segue",
                               "anula_vetor": "%s_p1_ue" % dia(0)}]
        self.publica_o_dia(dia(2), com_errata, indicadores=apoio.indicadores_calmos(dia(2)))

        def com_resposta(novo):
            self.dia_calmo(novo)
            novo["respostas"] = [{"edicao": dia(0), "item": "p2", "pergunta": self.PERGUNTAS["p2"], "resposta": "sim",
                                  "texto": "Texto fictício. A lei foi sancionada em 11/11.",
                                  "url": "https://exemplo.invalid/reuters/lei-sancionada"}]
            novo["bastidores"]["candidatos"][0]["motivo"] = "Texto fictício. Terceira aparição: voltou em 13/11."
        self.publica_o_dia(dia(3), com_resposta, indicadores=apoio.indicadores_calmos(dia(3)))

    def test_o_contexto_do_quinto_dia(self):
        self.monta_o_historico()
        contexto = self.contexto(dia(4))
        self.assertEqual(list(contexto), CHAVES)
        self.assertEqual((contexto["dia"], contexto["janela_horas"], contexto["edicao_do_dia"]), (dia(4), 36, None))
        self.assertEqual(contexto["anterior"], {"data": dia(3), "estado": "completa"})

        # alerta_anterior: os níveis da edição anterior, a conta de edições calmas e a origem de cada nível
        alerta = contexto["alerta_anterior"]
        self.assertEqual(alerta["nivel"], 3)
        por_id = dict((dominio["id"], dominio) for dominio in alerta["dominios"])
        self.assertEqual([dominio["id"] for dominio in alerta["dominios"]], DOMINIOS)
        self.assertEqual(dict((d, por_id[d]["nivel"]) for d in DOMINIOS),
                         {"energia": 3, "alimentos": 1, "cambio": 1, "suprimentos": 2, "conflito": 3})
        for dominio in ("energia", "suprimentos", "conflito"):
            self.assertEqual((por_id[dominio]["desde"], por_id[dominio]["edicoes_sem_gatilho"],
                              por_id[dominio]["desce_hoje_sem_gatilho"]), (dia(0), 2, True), dominio)
        primeira = self.le("edicoes/%s.json" % dia(0))
        gatilhos = dict((g["criterio"], g) for d in primeira["alerta"]["dominios"] for g in d["gatilhos"])
        self.assertEqual(por_id["energia"]["origem"],
                         {"edicao": dia(0), "criterio": "energia.3", "texto": gatilhos["energia.3"]["texto"]})
        self.assertEqual(por_id["suprimentos"]["origem"],
                         {"edicao": dia(0), "criterio": "suprimentos.2", "texto": gatilhos["suprimentos.2"]["texto"]})
        for dominio in ("alimentos", "cambio"):
            self.assertEqual((por_id[dominio]["origem"], por_id[dominio]["desce_hoje_sem_gatilho"]), (None, False))
        # a falha não conta, e a edição cega para o domínio (sem a variação de 7 dias do milho) também não
        self.assertEqual((por_id["cambio"]["edicoes_sem_gatilho"], por_id["alimentos"]["edicoes_sem_gatilho"]), (3, 0))

        # historias_recentes: principais e radar das 3 últimas edições que não são falha; vigiar só nas principais
        historias = contexto["historias_recentes"]
        self.assertEqual([h["edicao"] for h in historias], [dia(3)] * 9 + [dia(2)] * 9 + [dia(0)] * 9)
        self.assertEqual([h["id"] for h in historias[:9]], ["p1", "p2", "p3", "r1", "r2", "r3", "r4", "r5", "r6"])
        for historia in historias:
            self.assertEqual(list(historia), ["edicao", "id", "titulo"] + (["vigiar"] if historia["id"][0] == "p" else []))
        self.assertEqual(historias[18]["vigiar"][0], self.PERGUNTAS["p1"])
        self.assertEqual(historias[18]["titulo"], primeira["principais"][0]["titulo"])

        # vigiar_vencendo: a primeira pergunta de cada principal, com prazo vencido e sem resposta
        self.assertEqual(contexto["vigiar_vencendo"],
                         [{"edicao": dia(0), "item": "p1", "pergunta": self.PERGUNTAS["p1"], "prazo": dia(2)}])

        # candidatos: contados por id; o nome e o motivo são os da aparição mais recente
        self.assertEqual(contexto["candidatos"], [
            {"id": "reino_de_amostra", "nome": "Reino de Amostra (fictício)", "edicoes": 3, "ultima": dia(3),
             "motivo": "Texto fictício. Terceira aparição: voltou em 13/11."},
            {"id": "porto_ficticio", "nome": "Porto Fictício", "edicoes": 1, "ultima": dia(0),
             "motivo": "Texto fictício. Dono do terminal atacado."}])

        # vetores_recentes: os dos últimos 30 dias, sem o que a errata de 12/11 anulou
        self.assertEqual(contexto["vetores_recentes"],
                         [{"id": "%s_r2_google" % dia(0), "data": dia(0), "player": "google", "para": "ordem_global",
                           "forca": 2}])
        registro = self.le("dados/vetores.json")["vetores"]
        self.assertEqual([entrada["id"] for entrada in registro],
                         ["%s_p1_ue" % dia(0), "%s_r2_google" % dia(0), "%s_anula_1" % dia(2)])

        linhas = self.assertOK(self.publica("contexto", dia=dia(4)))
        texto = "\n".join(linhas)
        for trecho in ("anterior: %s, completa" % dia(3), "alerta anterior: nível 3 TENSÃO",
                       "energia 3 desde 10/11 · 2 edições sem gatilho · desce hoje sem gatilho · origem: energia.3 de "
                       + dia(0), "vigiar vencendo: 1", "%s/p1, prazo 12/11: %s" % (dia(0), self.PERGUNTAS["p1"]),
                       "candidatos: reino_de_amostra (3 edições), porto_ficticio (1 edição)", "vetores recentes: 1"):
            self.assertIn(trecho, texto)

    def test_o_aviso_de_descida_se_cumpre_na_edicao_seguinte(self):
        """desce_hoje_sem_gatilho diz o que a edição calma de hoje faz: os três domínios descem 1."""
        self.monta_o_historico()
        self.publica_o_dia(dia(4), self.dia_calmo, indicadores=apoio.indicadores_calmos(dia(4)))
        edicao = self.le("edicoes/%s.json" % dia(4))
        self.assertEqual([(d["id"], d["nivel"], d["tendencia"], d["desde"]) for d in edicao["alerta"]["dominios"]],
                         [("energia", 2, "descendo", dia(4)), ("alimentos", 1, "estavel", dia(0)),
                          ("cambio", 1, "estavel", dia(0)), ("suprimentos", 1, "descendo", dia(4)),
                          ("conflito", 2, "descendo", dia(4))])
        self.assertIn("Desde 13/11: energia 3 → 2, suprimentos 2 → 1, conflito 3 → 2.",
                      self.texto("edicoes/%s.md" % dia(4)).splitlines())
        self.assertIn("Desde 12/11: nenhum nível mudou.", self.texto("edicoes/%s.md" % dia(3)).splitlines())
        self.assertValido("--dia", dia(4), agora=apoio.agora(dia(4)))

    def test_janela_de_36_e_de_60_horas(self):
        self.publica_o_dia(dia(0), self.primeiro_dia)
        self.assertEqual(self.contexto(dia(1))["janela_horas"], 36, "a anterior é a véspera")
        self.assertEqual(self.contexto(dia(2))["janela_horas"], 60, "há um dia sem edição no meio")
        self.publica_a_falha(dia(1))
        depois_da_falha = self.contexto(dia(2))
        self.assertEqual((depois_da_falha["janela_horas"], depois_da_falha["anterior"]),
                         (60, {"data": dia(0), "estado": "completa"}), "a falha não é edição anterior: a janela cobre o buraco")
        self.assertEqual(self.contexto(dia(30))["janela_horas"], 60)
        self.assertEqual(self.contexto(dia(0))["janela_horas"], 36, "sem anterior, 36")

    def test_o_contexto_so_olha_para_antes_do_dia(self):
        """Pedir de novo o contexto de um dia antigo dá o mesmo que deu na hora, fora a edição do dia."""
        self.publica_o_dia(dia(0), self.primeiro_dia)
        self.publica_a_falha(dia(1))
        na_hora = self.contexto(dia(2))
        self.assertEqual([v["id"] for v in na_hora["vetores_recentes"]], ["%s_p1_ue" % dia(0), "%s_r2_google" % dia(0)])
        self.assertEqual([v["item"] for v in na_hora["vigiar_vencendo"]], ["p2", "p1"], "o prazo mais antigo primeiro")
        self.assertEqual([v["prazo"] for v in na_hora["vigiar_vencendo"]], [dia(1), dia(2)])
        self.monta_o_historico_a_partir_do_terceiro_dia()
        depois = self.contexto(dia(2))
        self.assertEqual(depois["edicao_do_dia"]["estado"], "completa")
        depois["edicao_do_dia"] = None
        self.assertEqual(depois, na_hora)

    def monta_o_historico_a_partir_do_terceiro_dia(self):
        for n in (2, 3):
            self.publica_o_dia(dia(n), self.dia_calmo, indicadores=apoio.indicadores_calmos(dia(n)))

    def test_edicao_do_dia(self):
        self.publica_a_falha(dia(0))
        self.assertEqual(self.contexto(dia(0))["edicao_do_dia"], {"estado": "falha", "gerada_em": apoio.agora(dia(0))})
        linhas = self.assertOK(self.publica("contexto", dia=dia(0)))
        self.assertIn("edição do dia: já existe, estado falha, gerada em %s" % apoio.agora(dia(0)), linhas)
        self.assertEqual(self.contexto(dia(1))["anterior"], None, "a falha não é edição anterior")

    def test_origem_de_preco(self):
        """Nível que veio só do preço: a origem leva "preco": true."""
        self.publica_o_dia(dia(0), apoio.sem_gatilhos)
        energia = self.contexto(dia(1))["alerta_anterior"]["dominios"][0]
        self.assertEqual((energia["nivel"], energia["origem"]["criterio"], energia["origem"].get("preco")),
                         (2, "energia.2", True))
        self.assertEqual(list(energia["origem"]), ["edicao", "criterio", "texto", "preco"])

    def test_pergunta_de_prazo_no_30o_dia_tem_7_dias_de_folga(self):
        """fer-01: a pergunta de prazo no 30º dia entra no dia do prazo e, se a rotina desse dia falhar, ainda volta
        por 7 dias (edição com até 37); no 8º dia depois do prazo, sai."""
        def vence_no_30o(novo):
            novo["principais"][0]["vigiar"][0] = "A pergunta fictícia se resolve até %s?" % apoio.comum.dd_mm(dia(30))
        self.publica_o_dia(dia(0), vence_no_30o)

        def da_p1(n):
            return [(v["edicao"], v["prazo"]) for v in self.contexto(dia(n))["vigiar_vencendo"] if v["item"] == "p1"]
        self.assertEqual(da_p1(29), [], "antes do prazo, não")
        for n in (30, 31, 37):
            self.assertEqual(da_p1(n), [(dia(0), dia(30))], "dia %d" % n)
        self.assertEqual(da_p1(38), [], "vencida há 8 dias: sai")

    def test_ate_tres_perguntas_vencendo_e_so_dos_ultimos_30_dias(self):
        def vence_logo(novo):
            for item in novo["principais"]:
                item["vigiar"][0] = "A pergunta fictícia de %s se resolve até %s?" % (item["id"], apoio.comum.dd_mm(novo["data"]))
        self.publica_o_dia(dia(0), vence_logo)
        self.publica_o_dia(dia(1), lambda novo: vence_logo(apoio.continua(novo, dia(0))))
        vencendo = self.contexto(dia(2))["vigiar_vencendo"]
        self.assertEqual([(v["edicao"], v["item"]) for v in vencendo], [(dia(0), "p1"), (dia(0), "p2"), (dia(0), "p3")])
        self.assertEqual(len(self.contexto(dia(30))["vigiar_vencendo"]), 3)
        self.assertEqual([v["edicao"] for v in self.contexto(dia(31))["vigiar_vencendo"]], [dia(1)] * 3,
                         "a edição de 31 dias atrás saiu da janela")
        self.assertEqual(self.contexto(dia(32))["vigiar_vencendo"], [])
        self.assertEqual(self.contexto(dia(14))["candidatos"][0]["edicoes"], 2)
        self.assertEqual(self.contexto(dia(15))["candidatos"][0]["edicoes"], 1, "candidato conta 14 dias")
        self.assertEqual(self.contexto(dia(16))["candidatos"], [])
        self.assertEqual(len(self.contexto(dia(30))["vetores_recentes"]), 4)
        self.assertEqual(len(self.contexto(dia(31))["vetores_recentes"]), 2, "vetor conta 30 dias")


class TestaExemploEArquivoTorto(ComContexto):
    def test_edicao_de_exemplo_e_ignorada_em_tudo(self):
        self.grava("edicoes/%s.json" % apoio.DIA_DO_EXEMPLO, apoio.exemplo())
        vazio = dict(self.contexto(apoio.DIA))
        self.assertEqual((vazio["anterior"], vazio["janela_horas"], vazio["historias_recentes"], vazio["candidatos"],
                          vazio["vigiar_vencendo"]), (None, 36, [], [], []))
        self.assertEqual([d["nivel"] for d in vazio["alerta_anterior"]["dominios"]], [1] * 5)
        self.assertIsNone(self.contexto(apoio.DIA_DO_EXEMPLO)["edicao_do_dia"])
        # e continua ignorada quando há edição de verdade antes dela
        self.publica_o_dia(dia(0))
        self.assertEqual(self.contexto(apoio.DIA)["anterior"], {"data": dia(0), "estado": "completa"})

    def test_edicao_antiga_ilegivel_para_com_o_nome_do_arquivo(self):
        self.publica_o_dia(dia(0))
        for conteudo, trecho in (('{"data": "2026-11-11", ', "linha 1"), ("[1, 2]", "objeto"), (b"\xff\xfe", "UTF-8")):
            self.grava("edicoes/%s.json" % dia(1), conteudo)
            for nome in os.listdir(self.trabalho):
                os.unlink(self.no_trabalho(nome))
            linhas = self.assertFALHA(self.publica("contexto", dia=dia(2)))
            self.assertIn("edicoes/%s.json" % dia(1), linhas[-1])
            self.assertIn(trecho, "\n".join(linhas))
            self.assertEqual(os.listdir(self.trabalho), [], "com erro, o contexto não é gravado")

    def test_dados_que_o_contexto_le_e_dados_que_nao_le(self):
        """Lê a régua, o mapa e os vetores (CONTRATO, seção 4.1). players.json e o catálogo não o seguram."""
        for nome in ("players", "indicadores"):
            self.grava("dados/%s.json" % nome, "{quebrado")
            linhas = self.assertOK(self.publica("contexto"))
            self.assertIn("aviso: dados/%s.json" % nome, "\n".join(linhas))
        for nome in ("regua", "veiculos", "vetores"):
            original = self.texto("dados/%s.json" % nome)
            self.grava("dados/%s.json" % nome, "{quebrado")
            linhas = self.assertFALHA(self.publica("contexto"))
            self.assertIn("dados/%s.json" % nome, linhas[-1])
            self.grava("dados/%s.json" % nome, original)

    def test_o_indice_quebrado_nao_segura_o_contexto(self):
        self.publica_o_dia(dia(0))
        self.grava("edicoes/indice.json", "{quebrado")
        self.assertOK(self.publica("contexto", dia=dia(1)))


class TestaOMapa(ComContexto):
    def setUp(self):
        super().setUp()
        self.dados = apoio.dados()

    def mapa(self):
        self.assertOK(self.publica("contexto"))
        texto = apoio.le_texto(self.no_trabalho("mapa.txt"))
        self.assertTrue(texto.endswith("\n"))
        return texto.splitlines()

    def test_legenda_e_uma_linha_por_veiculo(self):
        linhas = self.mapa()
        self.assertEqual(linhas[0], "MAPA · 146 veículos · rascunho, sem revisão do dono · id · partido (? = lado incerto) "
                         "· fatos · tipo · serve a · site · nome")
        self.assertEqual(len(linhas), 1 + len(self.dados.mapa))
        ids = [linha.split(" · ")[0] for linha in linhas[1:]]
        self.assertEqual(ids, sorted(self.dados.mapa), "em ordem de id")
        # as três linhas de exemplo do CONTRATO, seção 4.1, saem iguais com o mapa congelado
        for esperada in ("afp · CA · fatos alta · agencia · serve a: ue, macron · afp.com · Agence France-Presse (AFP)",
                         "anthropic_news · IN · fatos media · oficial · serve a: anthropic · anthropic.com · "
                         "Anthropic (sala de imprensa) · LIGADO À ANTHROPIC",
                         "ap · CA? · fatos alta · agencia · serve a: — · apnews.com · Associated Press (AP)"):
            self.assertIn(esperada, linhas)

    def test_cada_coluna_vem_do_mapa(self):
        siglas = dict((p["id"], p["sigla"]) for p in self.dados.bruto["regua"]["partidos"])
        for linha in self.mapa()[1:]:
            partes = linha.split(" · ")
            ficha = self.dados.mapa[partes[0]]
            self.assertEqual(partes[1], siglas[ficha["lado"]] + ("?" if ficha["lado_confianca"] == "baixa" else ""))
            self.assertEqual(partes[2:4], ["fatos " + ficha["fatos"], ficha["tipo"]])
            players = [alvo for alvo in ficha["serve_a"] if alvo not in self.dados.partidos]
            self.assertEqual(partes[4], "serve a: " + (", ".join(players) or "—"), "partido não entra em serve a")
            self.assertEqual(partes[5], ficha["sites"][0])
            ligado = "anthropic" in ficha["serve_a"] or "anthropic" in ficha["alvos"]
            self.assertEqual(partes[-1] == "LIGADO À ANTHROPIC", ligado, linha)
            self.assertEqual(" · ".join(partes[6:len(partes) - (1 if ligado else 0)]), ficha["nome"])
        self.assertEqual(sum(1 for linha in self.mapa() if linha.endswith("LIGADO À ANTHROPIC")), len(self.dados.ligados))

    def test_mapa_revisado_e_veiculo_torto(self):
        def mexe(mapa):
            mapa["revisado_em"] = "2026-12-05"
            mapa["veiculos"] = mapa["veiculos"][:2] + [{"id": "torto", "nome": "Veículo\ncom quebra", "lado": "nao_existe",
                                                        "serve_a": "x", "sites": []}]
        self.muda("dados/veiculos.json", mexe)
        linhas = self.mapa()
        self.assertEqual(linhas[0].split(" · ")[:3], ["MAPA", "3 veículos", "revisado em 05/12/2026"])
        self.assertEqual(linhas[-1], "torto · nao_existe? · fatos ? · ? · serve a: — · — · Veículo com quebra")
        self.assertEqual(len(linhas), 4, "uma linha por veículo, mesmo com quebra de linha no nome")


class TestaOModelo(ComContexto):
    def test_o_modelo_sai_com_o_texto_exato_do_contrato(self):
        self.assertOK(self.publica("contexto"))
        with open(self.no_trabalho("modelo.txt"), "rb") as arquivo:
            gravado = arquivo.read()
        with open(apoio.MODELO, "rb") as arquivo:
            congelado = arquivo.read()
        self.assertEqual(gravado, congelado, "modelo.txt é a cópia, byte a byte, do texto do CONTRATO, seção 4.1")
        self.assertEqual(apoio.publica.MODELO.encode("utf-8"), congelado)
        self.assertTrue(gravado.startswith("// MODELO DO RASCUNHO · copie a forma para /tmp/info/rascunho.json\n".encode("utf-8")))
        self.assertNotIn(b"\r", gravado)

    def test_o_modelo_publicado_com_o_contrato_e_o_mesmo(self):
        """Quando o contrato for publicado em docs/, o texto do modelo é conferido contra ele."""
        caminho = os.path.join(apoio.RAIZ, "docs", "CONTRATO-FERRAMENTAS.md")
        if not os.path.exists(caminho):
            # Pulado de propósito: o contrato só vai para docs/ no fim da construção. Até lá vale a cópia
            # congelada do teste acima, que é o bloco do CONTRATO, seção 4.1, letra por letra.
            self.skipTest("docs/CONTRATO-FERRAMENTAS.md ainda não existe no repositório")
        achado = re.search(r"\*\*Formato de `modelo\.txt`\.\*\*.*?```\n(.*?)\n```", apoio.le_texto(caminho), re.S)
        self.assertIsNotNone(achado, "o contrato publicado traz o bloco do modelo.txt")
        self.assertEqual(apoio.publica.MODELO, achado.group(1) + "\n")

    def test_o_modelo_bate_com_as_tabelas_do_validador(self):
        self.assertEqual(apoio.publica.confere_modelo(), [])
        modelo = apoio.publica.MODELO
        sem_comentario = "\n".join(linha for linha in modelo.splitlines() if not linha.strip().startswith("//"))
        objeto = json.loads(sem_comentario)
        self.assertEqual(list(objeto), ["data", "estado", "resumo", "alerta", "principais", "radar", "placar_do_dia",
                                        "novos_players", "errata", "respostas", "bastidores"])
        calculados = ("versao", "gerada_em", "indicadores", "nivel", "tendencia", "desde", "sem_preco", "lado", "saldo",
                      "narrativa", "veiculos_consultados", "feeds_ok", "feeds_falhos", "exemplo")
        for campo in calculados:
            self.assertNotIn('"%s"' % campo, sem_comentario, "campo calculado não vai no modelo")
        # e a conferência acusa quando o modelo e as tabelas se separam
        self.assertTrue(apoio.publica.confere_modelo(modelo.replace('"resumo": "240"', '"resumo": "250"')))
        self.assertTrue(apoio.publica.confere_modelo(modelo.replace('  "estado": "completa",\n', "")))
        self.assertTrue(apoio.publica.confere_modelo(modelo.replace('"data": "AAAA-MM-DD",', '"data": "AAAA-MM-DD", "versao": 1,')))
        self.assertTrue(apoio.publica.confere_modelo("{"))

    def test_o_dossie_pede_texto_corrido_numa_linha_so(self):
        """Quebra de linha e tabulação contam como caractere de controle (ESQUEMA, regra R17): o comentário do
        `realmente`, o campo mais longo, avisa antes que o agente escreva o dossiê em parágrafos."""
        linhas = apoio.publica.MODELO.splitlines()
        campo = linhas.index('      "realmente": "1500",')
        self.assertEqual(linhas[campo - 1], "      // o dossiê: de 800 a 1.500 caracteres, em texto corrido, numa linha só")

    def test_o_modelo_nao_manda_escrever_jargao_nem_dois_comecos(self):
        """O no_brasil não manda escrever "prazo sem fonte" (a frase ia ao leitor), e o enquadramento diz como
        juntar as duas aberturas quando valem as duas ("No título: " e o aviso de que o veículo serve a parte)."""
        linhas = apoio.publica.MODELO.splitlines()
        self.assertNotIn("prazo sem fonte", apoio.publica.MODELO.lower())
        campo = linhas.index('      "no_brasil": "240",')
        self.assertEqual(linhas[campo - 1], "      // Prazo só com fonte do dia; sem fonte, não dê prazo.")
        campo = linhas.index('          "enquadramento": "240",')
        self.assertEqual(linhas[campo - 1],
                         '          // Valendo os dois, junte: "No título: agência do Estado russo, que é parte: …"')

    def test_o_rascunho_de_teste_segue_o_modelo(self):
        """O rascunho que os testes publicam tem os campos do modelo, e só eles (os opcionais podem faltar)."""
        modelo = json.loads("\n".join(linha for linha in apoio.publica.MODELO.splitlines()
                                      if not linha.strip().startswith("//")))
        novo = apoio.rascunho()
        self.assertEqual(list(novo), list(modelo))
        self.assertLessEqual(set(novo["principais"][0]), set(modelo["principais"][0]))
        self.assertLessEqual(set(novo["radar"][0]), set(modelo["radar"][0]))
        self.assertEqual(list(novo["bastidores"]), list(modelo["bastidores"]))
        self.assertEqual(list(novo["alerta"]["dominios"][0]), list(modelo["alerta"]["dominios"][0]))


if __name__ == "__main__":
    unittest.main()
