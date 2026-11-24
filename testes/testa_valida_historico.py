#!/usr/bin/env python3
"""Testes do valida.py: o que depende das outras edições.

- as funções de cálculo: aplicadas ao exemplo sem os campos calculados, devolvem os do exemplo;
- a conta do nível (regras R13, R13b, R13e, R14 e R15) contra o histórico de verdade (regra H1);
- as regras H2 (referências a edições antigas) e H3 (avisos de repetição);
- os números do contexto (edição anterior, origem do nível, edições sem gatilho), que o `publica.py
  contexto` lê daqui: o validador e o contexto não podem discordar.

Rodar da raiz do repositório: python3 -B testes/testa_valida_historico.py
"""
import copy
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "valida"))

import apoio  # noqa: E402
from apoio import comum, valida  # noqa: E402


def dia(numero):
    """O dia `numero` de novembro de 2026."""
    return "2026-11-%02d" % numero


def niveis(edicao):
    return [d["nivel"] for d in edicao["alerta"]["dominios"]]


def dominio(edicao, identificador):
    return [d for d in edicao["alerta"]["dominios"] if d["id"] == identificador][0]


def so(criterio, ref="p1", **mais):
    """Uma função que deixa no rascunho um gatilho de evento só."""
    def muda(rascunho):
        apoio.sem_gatilhos(rascunho)
        apoio.poe_gatilho(rascunho, criterio, ref, **mais)
    return muda


class ComArquivo(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.arquivo = apoio.Arquivo()

    def calmo(self, numero, cegos=(), muda=None):
        """Publica um dia sem gatilho nenhum (nem de preço)."""
        def tudo(rascunho):
            apoio.sem_gatilhos(rascunho)
            if muda:
                muda(rascunho)
        return self.arquivo.publica(dia(numero), tudo, indicadores=apoio.indicadores_calmos(dia(numero), cegos))

    def com(self, numero, muda, **indicadores):
        """Publica um dia com os gatilhos que `muda` puser, e sem alta de preço (salvo a pedida)."""
        return self.arquivo.publica(dia(numero), muda, indicadores=apoio.indicadores_calmos(dia(numero), **indicadores))

    def confere(self, edicao, do_dia=True, historico=None):
        historico = self.arquivo.historico() if historico is None else historico
        return valida.confere_edicao(edicao, self.arquivo.dados(), historico, do_dia,
                                     edicao.get("data"), tamanho=40000)

    def tenta(self, numero, muda, **indicadores):
        """Monta a edição do dia sem publicar e devolve (edição, achados)."""
        rascunho = self.arquivo.rascunho(dia(numero))
        muda(rascunho)
        edicao = apoio.completa(rascunho, self.arquivo.historico(), self.arquivo.dados(),
                                apoio.indicadores_calmos(dia(numero), **indicadores))
        return edicao, self.confere(edicao)


class TestaCalculo(unittest.TestCase):
    """As funções de cálculo, aplicadas ao exemplo sem os campos calculados, devolvem os do exemplo."""

    maxDiff = None

    def setUp(self):
        self.exemplo = apoio.exemplo()
        self.rascunho = apoio.tira_calculados(self.exemplo)
        self.historico = apoio.historico_do_exemplo()
        self.indicadores = {"indicadores": self.exemplo["indicadores"],
                            "gatilhos": [self.exemplo["alerta"]["dominios"][0]["gatilhos"][0]]}

    def completa(self, rascunho=None, **nomeados):
        nomeados.setdefault("indicadores", self.indicadores)
        nomeados.setdefault("coleta", apoio.COLETA)
        nomeados.setdefault("gerada_em", self.exemplo["gerada_em"])
        return valida.completa(self.rascunho if rascunho is None else rascunho, apoio.dados(), self.historico, **nomeados)

    def test_o_rascunho_nao_tem_campo_calculado(self):
        self.assertNotIn("versao", self.rascunho)
        self.assertNotIn("indicadores", self.rascunho)
        self.assertNotIn("nivel", self.rascunho["alerta"])
        self.assertNotIn("lado", self.rascunho["principais"][0]["ataques"][0])
        self.assertNotIn("saldo", self.rascunho["placar_do_dia"][0])
        self.assertNotIn("conflito_de_interesse", self.rascunho["radar"][0])
        self.assertEqual([g["ref"] for g in self.rascunho["alerta"]["dominios"][0]["gatilhos"]], ["p1"])

    def test_completa_devolve_o_exemplo_campo_a_campo(self):
        feita = self.completa()
        for chave in self.exemplo:
            self.assertEqual(feita[chave], self.exemplo[chave], chave)
        self.assertEqual(feita, self.exemplo)

    def test_completa_devolve_os_mesmos_bytes_do_arquivo(self):
        with open(apoio.EXEMPLO, "rb") as arquivo:
            self.assertEqual(comum.json_texto(self.completa()).encode("utf-8"), arquivo.read())

    def test_completa_nao_muda_o_que_recebe(self):
        antes = copy.deepcopy(self.rascunho)
        self.completa()
        self.assertEqual(self.rascunho, antes)

    def test_completa_de_novo_da_o_mesmo(self):
        feita = self.completa()
        self.assertEqual(self.completa(feita), feita)

    def test_campo_calculado_que_vem_no_rascunho_e_trocado(self):
        torto = copy.deepcopy(self.rascunho)
        torto["versao"] = 7
        torto["indicadores"] = [{"id": "inventado"}]
        torto["alerta"].update(nivel=5, tendencia="descendo")
        torto["alerta"]["dominios"][0].update(nivel=1, tendencia="descendo", desde="2020-01-01", sem_preco=["x"])
        torto["alerta"]["dominios"][0]["gatilhos"].insert(0, {"criterio": "energia.4", "ref": "brent", "texto": "Inventado."})
        torto["principais"][0]["ataques"][0]["lado"] = "soberanistas"
        torto["placar_do_dia"][0].update(saldo=99, narrativa=-9)
        torto["placar_do_dia"].reverse()
        torto["bastidores"].update(veiculos_consultados=0, feeds_ok=0, feeds_falhos=0)
        torto["radar"][0]["conflito_de_interesse"] = False
        self.assertEqual(self.completa(torto), self.exemplo)

    def test_a_marca_de_conflito_liga_e_nunca_desliga(self):
        ligado = copy.deepcopy(self.rascunho)
        ligado["principais"][2]["conflito_de_interesse"] = True  # o agente ligou num item que a máquina não marca
        feita = self.completa(ligado)
        self.assertIs(feita["principais"][2]["conflito_de_interesse"], True)
        self.assertEqual(list(feita["principais"][2])[-3:], ["confianca", "conflito_de_interesse", "fontes"])

    def test_cada_peca_devolve_o_campo_do_exemplo(self):
        dados, e = apoio.dados(), self.exemplo
        for item in e["principais"] + e["radar"]:
            for ataque in item.get("ataques", []) + ([item["ataque"]] if "ataque" in item else []):
                self.assertEqual(valida.lado_do_veiculo(dados, ataque["veiculo"]), ataque["lado"])
            self.assertEqual(valida.calcula_conflito(dados, item)[0], item.get("conflito_de_interesse", False), item["id"])
        self.assertIsNone(valida.lado_do_veiculo(dados, "outro"))
        calculado = valida.calcula_alerta(dados, e, self.historico)
        self.assertEqual((calculado["nivel"], calculado["tendencia"]), (e["alerta"]["nivel"], e["alerta"]["tendencia"]))
        for feito, escrito in zip(calculado["dominios"], e["alerta"]["dominios"]):
            self.assertEqual(dict(feito), dict((k, escrito[k]) for k in ("id", "nivel", "tendencia", "desde", "sem_preco")))
            self.assertEqual(valida.calcula_sem_preco(dados, escrito["id"], e["indicadores"]), escrito["sem_preco"])
        self.assertEqual(valida.calcula_gatilhos_de_preco(dados, e["indicadores"], e["data"]),
                         {"energia": {"brent": 2}, "alimentos": {}, "cambio": {}, "suprimentos": {}, "conflito": {}})
        self.assertEqual([dict(l) for l in valida.calcula_placar_do_dia(dados, e)],
                         [dict((k, l[k]) for k in ("partido", "saldo", "narrativa")) for l in e["placar_do_dia"]])
        self.assertEqual(valida.calcula_veiculos_consultados(e), e["bastidores"]["veiculos_consultados"])
        self.assertEqual(valida.calcula_feeds(apoio.COLETA), (e["bastidores"]["feeds_ok"], e["bastidores"]["feeds_falhos"]))
        self.assertEqual(valida.partido_pelo_dna(dados, e["novos_players"][0]["dna"]), e["novos_players"][0]["partido"])

    def test_sem_indicadores_e_sem_coleta(self):
        feita = self.completa(indicadores=None, coleta=None)
        self.assertEqual(feita["indicadores"], [])
        self.assertEqual((feita["bastidores"]["feeds_ok"], feita["bastidores"]["feeds_falhos"]), (0, 0))
        self.assertEqual([g["ref"] for g in feita["alerta"]["dominios"][0]["gatilhos"]], ["p1"])
        self.assertEqual([d["sem_preco"] for d in feita["alerta"]["dominios"]],
                         [["brent"], ["trigo", "milho", "soja"], ["usd_brl"], [], []])
        self.assertEqual(valida.calcula_feeds(None), (0, 0))
        self.assertEqual(valida.calcula_feeds({"resumo": {"feeds_ok": "muitos", "feeds_falhos": -3}}), (0, 0))

    def test_gatilho_de_preco_entra_na_frente_e_so_no_dominio_do_criterio(self):
        preco = {"indicadores": self.exemplo["indicadores"],
                 "gatilhos": [{"criterio": "cambio.2", "ref": "usd_brl", "texto": "Inventado."},
                              self.indicadores["gatilhos"][0]]}
        feita = self.completa(indicadores=preco)
        self.assertEqual([g["ref"] for g in feita["alerta"]["dominios"][0]["gatilhos"]], ["brent", "p1"])
        self.assertEqual([g["ref"] for g in feita["alerta"]["dominios"][2]["gatilhos"]], ["usd_brl"])

    def test_sem_historico_e_a_primeira_edicao(self):
        feita = valida.completa(self.rascunho, apoio.dados(), None, self.indicadores, apoio.COLETA, self.exemplo["gerada_em"])
        self.assertEqual(niveis(feita), [3, 1, 1, 2, 3])
        self.assertEqual(set(d["tendencia"] for d in feita["alerta"]["dominios"]), set(["estavel"]))
        self.assertEqual(set(d["desde"] for d in feita["alerta"]["dominios"]), set([self.exemplo["data"]]))
        self.assertEqual(feita["alerta"]["tendencia"], "estavel")

    def test_normaliza_poe_as_chaves_na_ordem_do_esquema(self):
        def embaralha(valor):
            if isinstance(valor, dict):
                return dict((chave, embaralha(valor[chave])) for chave in sorted(valor, reverse=True))
            return [embaralha(v) for v in valor] if isinstance(valor, list) else valor
        embaralhado = embaralha(self.exemplo)
        self.assertNotEqual(list(embaralhado), list(self.exemplo))
        with open(apoio.EXEMPLO, "rb") as arquivo:
            self.assertEqual(comum.json_texto(valida.normaliza(embaralhado, apoio.dados())).encode("utf-8"), arquivo.read())
        self.assertEqual(list(valida.normaliza({"zzz": 1, "data": "x"})), ["data", "zzz"])  # desconhecida vai para o fim
        normalizada = valida.normaliza(self.exemplo, apoio.dados())
        normalizada["principais"][0]["na_pratica"].append("mexido")           # a cópia não divide nada com o original
        self.assertNotIn("mexido", self.exemplo["principais"][0]["na_pratica"])
        for torto in (None, [], "x", {"alerta": 3, "principais": [1, {"ataques": 2}], "bastidores": []}):
            self.assertEqual(valida.normaliza(torto), torto)

    def test_rascunho_torto_nao_da_excecao(self):
        for torto in (None, [], "texto", 3, {}, {"alerta": []}, {"alerta": {"dominios": [1, {"id": 7}, {"id": "energia"}]}},
                      {"principais": [None, {"ataques": {}, "placar": 3, "fontes": "x", "vetores": [1]}], "radar": {}},
                      {"placar_do_dia": [1, {}, {"partido": []}], "bastidores": [], "indicadores": 9}):
            feita = valida.completa(torto, apoio.dados(), None, {"indicadores": "x", "gatilhos": 3}, [], None)
            self.assertIsInstance(valida.confere_edicao(feita, apoio.dados(), valida.Historico(), True), list)


class TestaNivelPeloHistorico(ComArquivo):
    """Regra H1: R13 e R14 contra as edições anteriores de verdade."""

    def test_o_nivel_se_mantem_por_2_edicoes_e_depois_desce_1(self):
        self.com(1, so("conflito.3"))
        vistos = [(3, "estavel", dia(1))]
        for numero in range(2, 8):
            conflito = dominio(self.calmo(numero), "conflito")
            vistos.append((conflito["nivel"], conflito["tendencia"], conflito["desde"]))
        self.assertEqual(vistos, [(3, "estavel", dia(1)), (3, "estavel", dia(1)), (3, "estavel", dia(1)),
                                  (2, "descendo", dia(4)), (2, "estavel", dia(4)),
                                  (1, "descendo", dia(6)), (1, "estavel", dia(6))])
        self.assertEqual([self.arquivo.edicoes[dia(n)]["alerta"]["nivel"] for n in range(1, 8)], [3, 3, 3, 2, 2, 1, 1])
        self.assertEqual([self.arquivo.edicoes[dia(n)]["alerta"]["tendencia"] for n in range(1, 8)],
                         ["estavel", "estavel", "estavel", "descendo", "estavel", "descendo", "estavel"])

    def test_a_primeira_edicao_nasce_estavel_mesmo_no_nivel_3(self):
        primeira = self.com(1, so("conflito.3"))
        self.assertEqual((primeira["alerta"]["nivel"], primeira["alerta"]["tendencia"]), (3, "estavel"))
        self.assertEqual(dominio(primeira, "conflito")["desde"], dia(1))

    def test_gatilho_novo_sobe_e_gatilho_menor_nao_segura_a_descida(self):
        self.com(1, so("conflito.3"))
        sobe = self.com(2, so("conflito.4"))
        self.assertEqual((dominio(sobe, "conflito")["nivel"], dominio(sobe, "conflito")["tendencia"], sobe["alerta"]["tendencia"]),
                         (4, "subindo", "subindo"))
        for numero in (3, 4):   # gatilho de nível 2: abaixo do 4, não zera a conta de edições calmas
            self.assertEqual(dominio(self.com(numero, so("conflito.2", "r6")), "conflito")["nivel"], 4)
        desce = self.com(5, so("conflito.2", "r6"))
        self.assertEqual((dominio(desce, "conflito")["nivel"], dominio(desce, "conflito")["tendencia"]), (3, "descendo"))

    def test_gatilho_do_mesmo_nivel_renova_e_mantem_o_desde(self):
        self.com(1, so("conflito.2", "r6"))
        self.calmo(2)
        renovado = self.com(3, so("conflito.2", "r6"))
        self.assertEqual((dominio(renovado, "conflito")["nivel"], dominio(renovado, "conflito")["desde"]), (2, dia(1)))
        self.calmo(4)
        self.assertEqual(dominio(self.calmo(5), "conflito")["nivel"], 2)   # só 1 edição calma depois do gatilho do dia 3
        self.assertEqual(dominio(self.calmo(6), "conflito")["nivel"], 1)

    def test_edicao_cega_nao_conta_e_dominio_cego_nao_desce(self):
        self.com(1, so("energia.3"))
        vistos = []
        for numero, cego in ((2, True), (3, False), (4, False), (5, True), (6, False), (7, False)):
            energia = dominio(self.calmo(numero, cegos=("brent",) if cego else ()), "energia")
            vistos.append((energia["nivel"], energia["sem_preco"]))
        self.assertEqual(vistos, [(3, ["brent"]), (3, []), (3, []), (3, ["brent"]), (2, []), (2, [])])

    def test_edicao_de_falha_e_pulada_e_repete_os_niveis(self):
        self.com(1, so("conflito.3"))
        falha = self.arquivo.publica_falha(dia(2))
        self.assertEqual((niveis(falha), dominio(falha, "conflito")["desde"], falha["alerta"]["tendencia"]),
                         ([1, 1, 1, 1, 3], dia(1), "estavel"))
        apoio.limpo(self, self.confere(falha))
        self.assertEqual(dominio(self.calmo(3), "conflito")["nivel"], 3)
        self.assertEqual(dominio(self.calmo(4), "conflito")["nivel"], 3)
        self.arquivo.publica_falha(dia(5))
        self.assertEqual(dominio(self.calmo(6), "conflito")["nivel"], 2)   # as calmas são 3 e 4; as falhas não contam

    def test_edicao_de_exemplo_nao_conta_como_anterior(self):
        self.com(1, so("conflito.3"))
        exemplo = apoio.exemplo()
        exemplo["data"] = dia(2)
        self.arquivo.poe(dia(2), exemplo)
        self.assertEqual(self.arquivo.historico().anterior(dia(3)).data, dia(1))

    def test_nivel_tendencia_e_desde_errados_sao_acusados(self):
        self.com(1, so("conflito.3"))
        self.calmo(2)
        self.calmo(3)
        quarta = self.calmo(4)
        for campo, valor, regra in (("nivel", 3, "R13"), ("nivel", 1, "R13"), ("tendencia", "estavel", "R14"),
                                    ("desde", dia(1), "R14")):
            torta = copy.deepcopy(quarta)
            dominio(torta, "conflito")[campo] = valor
            torta["alerta"]["nivel"] = max(niveis(torta))
            achado = apoio.acusa(self, self.confere(torta), regra, "alerta.dominios[4]." + campo)
            self.assertIn("publica.py edicao", achado.mensagem)
        torta = copy.deepcopy(quarta)
        torta["alerta"]["tendencia"] = "subindo"
        apoio.acusa(self, self.confere(torta), "R14", "alerta.tendencia")
        achado = apoio.acusa(self, self.confere(dict(quarta, alerta=dict(quarta["alerta"], dominios=[
            dict(d, nivel=3, tendencia="estavel", desde=dia(1)) if d["id"] == "conflito" else d
            for d in quarta["alerta"]["dominios"]]))), "R13", "alerta.dominios[4].nivel")
        self.assertIn("é 3; a conta dá 2: sem gatilho de nível 3 há 2 edições medidas", achado.mensagem)

    def test_a_edicao_de_arquivo_tambem_e_conferida_contra_o_historico(self):
        self.com(1, so("conflito.3"))
        self.calmo(2)
        torta = copy.deepcopy(self.arquivo.edicoes[dia(2)])
        dominio(torta, "conflito").update(nivel=1, tendencia="descendo", desde=dia(2))
        torta["alerta"].update(nivel=1, tendencia="descendo")
        apoio.acusa(self, self.confere(torta, do_dia=False), "R13", "alerta.dominios[4].nivel")

    def test_falha_com_niveis_diferentes_dos_da_anterior(self):
        self.com(1, so("conflito.3"))
        falha = self.arquivo.publica_falha(dia(2))
        torta = copy.deepcopy(falha)
        dominio(torta, "conflito").update(nivel=1, desde=dia(2))
        torta["alerta"]["nivel"] = 1
        achados = self.confere(torta)
        apoio.acusa(self, achados, "R15", "alerta.dominios[4].nivel")
        apoio.acusa(self, achados, "R15", "alerta.dominios[4].desde")

    def test_sem_historico_o_nivel_mantido_passa_e_com_historico_vazio_nao(self):
        self.com(1, so("conflito.3"))
        segunda = self.calmo(2)   # nível 3 mantido, sem gatilho
        apoio.limpo(self, valida.confere_edicao(segunda, self.arquivo.dados(), None, True, tamanho=40000))
        vazio = valida.Historico()
        apoio.acusa(self, self.confere(segunda, historico=vazio), "R13", "alerta.dominios[4].nivel")


class TestaEstadoQueContinuaEAlivio(ComArquivo):
    """Níveis 4 e 5 são estados (regra R13b): repetem-se com uma linha de radar e acabam com alívio (R13e)."""

    def test_estado_que_continua_aceita_radar_e_nao_pede_de_novo_a_primaria(self):
        self.com(1, so("conflito.5"))            # p1: principal, confiança alta, com fonte primária
        segunda = self.com(2, so("conflito.5", "r6", texto="Segue em 02/11: texto fictício."))
        self.assertEqual(dominio(segunda, "conflito")["nivel"], 5)
        terceira = self.com(3, so("conflito.5", "p3"))   # principal sem primária: também continua
        self.assertEqual(dominio(terceira, "conflito")["nivel"], 5)

    def test_gatilho_novo_de_nivel_4_nao_aceita_radar(self):
        _, achados = self.tenta(1, so("conflito.4", "r6"))
        apoio.acusa(self, achados, "R13b", "alerta.dominios[4].gatilhos[0].ref")
        self.com(1, so("conflito.4"))
        _, achados = self.tenta(2, so("conflito.5", "r6"))           # critério diferente do da origem
        apoio.acusa(self, achados, "R13b", "alerta.dominios[4].gatilhos[0].ref")
        _, achados = self.tenta(2, so("suprimentos.4", "r4"))        # outro domínio: é gatilho novo
        apoio.acusa(self, achados, "R13b", "alerta.dominios[3].gatilhos[0].ref")
        _, achados = self.tenta(2, so("conflito.4", "r3"))           # confiança baixa não prova nem estado que continua
        apoio.acusa(self, achados, "R13b", "alerta.dominios[4].gatilhos[0].ref")

    def test_depois_que_o_nivel_desceu_o_estado_volta_a_ser_gatilho_novo(self):
        self.com(1, so("conflito.4"))
        self.calmo(2)
        self.calmo(3)
        self.assertEqual(dominio(self.calmo(4), "conflito")["nivel"], 3)
        _, achados = self.tenta(5, so("conflito.4", "r6"))
        apoio.acusa(self, achados, "R13b", "alerta.dominios[4].gatilhos[0].ref")

    def test_alta_de_preco_nao_se_repete_a_mao(self):
        com_preco = apoio.indicadores_calmos(dia(1), brent=21.0)
        com_preco["gatilhos"] = [{"criterio": "energia.4", "ref": "brent", "texto": "Texto fictício. Alta de 21%."}]
        primeira = self.arquivo.publica(dia(1), apoio.sem_gatilhos, indicadores=com_preco)
        self.assertEqual(dominio(primeira, "energia")["nivel"], 4)
        self.assertEqual(valida.origem_do_nivel(self.arquivo.historico(), "energia", dia(2)),
                         {"edicao": dia(1), "criterio": "energia.4", "texto": "Texto fictício. Alta de 21%.", "preco": True})
        _, achados = self.tenta(2, so("energia.4", "r4"))
        apoio.acusa(self, achados, "R13b", "alerta.dominios[0].gatilhos[0].ref")
        _, achados = self.tenta(2, so("energia.4", "p1", alivio=True))
        achado = apoio.acusa(self, achados, "R13e", "alerta.dominios[0].gatilhos[0].alivio")
        self.assertIn("gatilho de preço", achado.mensagem)

    def test_alivio_desce_um_nivel_na_hora(self):
        self.com(1, so("conflito.4"))
        segunda = self.com(2, so("conflito.4", "p1", alivio=True))
        conflito = dominio(segunda, "conflito")
        self.assertEqual((conflito["nivel"], conflito["tendencia"], conflito["desde"]), (3, "descendo", dia(2)))
        self.assertEqual(valida.origem_do_nivel(self.arquivo.historico(), "conflito", dia(3)),
                         {"edicao": dia(2), "criterio": "conflito.4", "texto": "Texto fictício. Fato de teste, com data.",
                          "alivio": True})
        # a calma começa a ser contada depois do alívio: 2 edições no nível 3, e só então desce
        self.assertEqual([dominio(self.calmo(n), "conflito")["nivel"] for n in (3, 4, 5)], [3, 3, 2])

    def test_alivio_nao_conta_como_gatilho_de_hoje(self):
        self.com(1, so("conflito.5"))

        def alivio_e_ato(rascunho):
            apoio.sem_gatilhos(rascunho)
            apoio.poe_gatilho(rascunho, "conflito.5", "p1", alivio=True)
            apoio.poe_gatilho(rascunho, "conflito.2", "r6")
        segunda = self.com(2, alivio_e_ato)
        self.assertEqual(dominio(segunda, "conflito")["nivel"], 4)

    def test_alivio_recusado(self):
        self.com(1, so("conflito.4"))
        casos = (
            ("ref de radar", so("conflito.4", "r6", alivio=True), "gatilhos[0].ref"),
            ("principal de confiança media", so("conflito.4", "p2", alivio=True), "gatilhos[0].ref"),
            ("critério diferente do da origem", so("conflito.5", "p1", alivio=True), "gatilhos[0].criterio"),
            ("junto com exceção", so("conflito.4", "p1", alivio=True, excecao=True), "gatilhos[0].excecao"),
        )
        for nome, muda, caminho in casos:
            with self.subTest(nome):
                edicao, achados = self.tenta(2, muda)
                apoio.acusa(self, achados, "R13e", "alerta.dominios[4]." + caminho)
                self.assertEqual(dominio(edicao, "conflito")["nivel"], 4, "alívio recusado não desce o nível")

        def dois(rascunho):
            apoio.sem_gatilhos(rascunho)
            apoio.poe_gatilho(rascunho, "conflito.4", "p1", alivio=True)
            apoio.poe_gatilho(rascunho, "conflito.4", "p3", alivio=True)
        _, achados = self.tenta(2, dois)
        apoio.acusa(self, achados, "R13e", "alerta.dominios[4].gatilhos[1].alivio")

    def test_alivio_so_em_dominio_que_estava_em_4_ou_5(self):
        self.com(1, so("conflito.3"))
        _, achados = self.tenta(2, so("conflito.3", "p1", alivio=True))
        achado = apoio.acusa(self, achados, "R13e", "alerta.dominios[4].gatilhos[0].alivio")
        self.assertIn("estava no nível 3", achado.mensagem)

    def test_depois_do_alivio_nao_ha_outro_alivio_nem_estado_que_continua(self):
        self.com(1, so("conflito.5"))
        self.com(2, so("conflito.5", "p1", alivio=True))    # desce para 4; a origem agora é o alívio
        _, achados = self.tenta(3, so("conflito.5", "p1", alivio=True))
        achado = apoio.acusa(self, achados, "R13e", "alerta.dominios[4].gatilhos[0].alivio")
        self.assertIn("outro alívio", achado.mensagem)
        _, achados = self.tenta(3, so("conflito.5", "r6"))
        apoio.acusa(self, achados, "R13b", "alerta.dominios[4].gatilhos[0].ref")


class TestaContexto(ComArquivo):
    """Os números que o `publica.py contexto` lê: têm de ser os mesmos da conta do validador."""

    def test_sem_edicao_anterior(self):
        dominios = self.arquivo.dados().dominios
        contexto = valida.alerta_anterior(self.arquivo.historico(), dia(5), dominios)
        self.assertEqual(contexto["nivel"], 1)
        self.assertEqual([dict(d) for d in contexto["dominios"]], [
            {"id": d, "nivel": 1, "desde": dia(5), "edicoes_sem_gatilho": 0, "desce_hoje_sem_gatilho": False, "origem": None}
            for d in dominios])
        self.assertIsNone(self.arquivo.historico().anterior(dia(5)))
        self.assertEqual(valida.nivel_anterior(self.arquivo.historico(), "energia", dia(5)), 1)
        self.assertEqual(valida.alerta_anterior(None, dia(5), dominios), contexto)

    def test_o_formato_e_o_do_contrato(self):
        self.com(1, so("energia.2", "r4"))
        self.calmo(2)
        contexto = valida.alerta_anterior(self.arquivo.historico(), dia(3), self.arquivo.dados().dominios)
        self.assertEqual(list(contexto), ["nivel", "dominios"])
        energia = contexto["dominios"][0]
        self.assertEqual(list(energia), ["id", "nivel", "desde", "edicoes_sem_gatilho", "desce_hoje_sem_gatilho", "origem"])
        self.assertEqual(dict(energia, origem=dict(energia["origem"])), {
            "id": "energia", "nivel": 2, "desde": dia(1), "edicoes_sem_gatilho": 1, "desce_hoje_sem_gatilho": False,
            "origem": {"edicao": dia(1), "criterio": "energia.2", "texto": "Texto fictício. Fato de teste, com data."}})
        self.assertEqual(comum.json_texto(contexto).count('"origem": null'), 4)

    def test_desce_hoje_sem_gatilho_bate_com_o_nivel_que_o_validador_calcula(self):
        self.com(1, so("conflito.3"))
        dominios = self.arquivo.dados().dominios
        for numero in range(2, 9):
            contexto = valida.alerta_anterior(self.arquivo.historico(), dia(numero), dominios)
            anterior = self.arquivo.historico().anterior(dia(numero))
            self.assertEqual(contexto["nivel"], anterior.nivel_geral)
            edicao = self.calmo(numero)
            for previsto, feito in zip(contexto["dominios"], edicao["alerta"]["dominios"]):
                self.assertEqual(previsto["nivel"], anterior.niveis[feito["id"]])
                self.assertEqual(previsto["desde"], anterior.desde[feito["id"]])
                self.assertEqual(previsto["edicoes_sem_gatilho"],
                                 valida.edicoes_sem_gatilho(self.arquivo.historico().__class__(
                                     dict((d, e) for d, e in self.arquivo.edicoes.items() if d < dia(numero))),
                                     feito["id"], dia(numero)))
                self.assertEqual(previsto["desce_hoje_sem_gatilho"], feito["nivel"] == previsto["nivel"] - 1,
                                 "%s em %s" % (feito["id"], dia(numero)))

    def test_a_origem_e_o_gatilho_mais_recente_de_nivel_igual_ou_maior(self):
        self.com(1, so("conflito.3"))
        self.com(2, so("conflito.2", "r6", texto="Texto fictício. Ato menor."))
        historico = self.arquivo.historico()
        self.assertEqual(valida.origem_do_nivel(historico, "conflito", dia(3))["edicao"], dia(1))   # o de nível 2 não explica o 3
        self.assertIsNone(valida.origem_do_nivel(historico, "energia", dia(3)))                     # nível 1 não tem origem
        self.assertIsNone(valida.origem_do_nivel(historico, "conflito", dia(1)))                    # antes da primeira edição
        self.calmo(3)
        self.calmo(4)   # desce para 2: agora o gatilho de nível 2, mais recente, já serve
        self.assertEqual(dominio(self.arquivo.edicoes[dia(4)], "conflito")["nivel"], 2)
        self.assertEqual(valida.origem_do_nivel(self.arquivo.historico(), "conflito", dia(5))["edicao"], dia(2))

    def test_na_mesma_edicao_o_evento_vem_antes_do_preco(self):
        com_preco = apoio.indicadores_do_dia(dia(1))   # traz o gatilho de preço energia.2

        def evento_tambem(rascunho):
            apoio.sem_gatilhos(rascunho)
            apoio.poe_gatilho(rascunho, "energia.2", "r4", texto="Texto fictício. Ameaça a uma rota.")
        primeira = self.arquivo.publica(dia(1), evento_tambem, indicadores=com_preco)
        self.assertEqual([g["ref"] for g in dominio(primeira, "energia")["gatilhos"]], ["brent", "r4"])
        origem = valida.origem_do_nivel(self.arquivo.historico(), "energia", dia(2))
        self.assertEqual(dict(origem), {"edicao": dia(1), "criterio": "energia.2", "texto": "Texto fictício. Ameaça a uma rota."})

    def test_o_historico_so_olha_para_antes_da_data(self):
        self.com(1, so("conflito.3"))
        self.calmo(2)
        self.calmo(3)
        historico = self.arquivo.historico()
        self.assertEqual(historico.anterior(dia(3)).data, dia(2))
        self.assertEqual(historico.anterior(dia(2)).data, dia(1))
        self.assertEqual([r.data for r in historico.antes(dia(9))], [dia(3), dia(2), dia(1)])
        self.assertEqual(historico.datas, [dia(1), dia(2), dia(3)])
        self.assertIs(historico.edicao(dia(2)), self.arquivo.edicoes[dia(2)])
        self.assertIsNone(historico.edicao("2026-13-45"))
        self.assertEqual(list(historico.antes("lixo")), [])

    def test_edicao_antiga_torta_nao_derruba_as_contas(self):
        tortas = {dia(1): [], dia(2): {"alerta": "x", "estado": 3}, dia(3): {"alerta": {"dominios": [None, {"id": 5},
                  {"id": "energia", "nivel": "alto", "desde": 9, "sem_preco": "sim", "gatilhos": [3, {"criterio": []}]}]}},
                  "lixo": {}}
        historico = valida.Historico(tortas)
        self.assertEqual(historico.datas, [dia(1), dia(2), dia(3)])
        contexto = valida.alerta_anterior(historico, dia(4), self.arquivo.dados().dominios)
        self.assertEqual([d["nivel"] for d in contexto["dominios"]], [1] * 5)
        self.assertIsInstance(valida.monta_indice(tortas), dict)


class TestaH2(ComArquivo):
    """errata, continuacao_de e respostas apontam para edição e item que existem."""

    def setUp(self):
        super().setUp()
        self.arquivo.publica(dia(1))
        self.arquivo.publica(dia(2))
        self.pergunta = self.arquivo.edicoes[dia(1)]["principais"][0]["vigiar"][0]

    def errata(self, **campos):
        nova = {"edicao": dia(1), "item": "r3", "erro": "Texto fictício. Estava errado.", "correcao": "Texto fictício. O certo."}
        nova.update(campos)
        return valida.normaliza({"errata": [nova]})["errata"][0]

    def resposta(self, **campos):
        nova = {"edicao": dia(1), "item": "p1", "pergunta": self.pergunta, "resposta": "sem_dado",
                "texto": "Texto fictício. Nenhuma fonte trouxe a resposta."}
        nova.update(campos)
        return nova

    def test_tudo_certo_passa(self):
        def muda(rascunho):
            rascunho["errata"] = [self.errata(), self.errata(item="p2"), {k: v for k, v in self.errata().items() if k != "item"}]
            rascunho["respostas"] = [self.resposta()]
        terceira = self.arquivo.publica(dia(3), muda)
        self.assertEqual(terceira["principais"][0]["continuacao_de"], dia(2) + "/p1")

    def test_errata_para_edicao_ou_item_que_nao_existe(self):
        _, achados = self.tenta(3, lambda r: r.update(errata=[self.errata(edicao="2026-10-15")]))
        achado = apoio.acusa(self, achados, "H2", "errata[0].edicao")
        self.assertIn("não há edição de 2026-10-15", achado.mensagem)
        _, achados = self.tenta(3, lambda r: r.update(errata=[self.errata(item="r12")]))
        apoio.acusa(self, achados, "H2", "errata[0].item")

    def test_continuacao_de_edicao_ou_item_que_nao_existe(self):
        _, achados = self.tenta(3, lambda r: r["principais"][0].update(continuacao_de="2026-10-15/p1"))
        apoio.acusa(self, achados, "H2", "principais[0].continuacao_de")
        _, achados = self.tenta(3, lambda r: r["radar"][0].update(continuacao_de=dia(2) + "/r12"))
        apoio.acusa(self, achados, "H2", "radar[0].continuacao_de")
        _, achados = self.tenta(3, lambda r: r["radar"][0].update(continuacao_de=dia(1) + "/p3"))   # radar continua principal
        apoio.limpo(self, achados)

    def test_resposta_para_edicao_item_ou_pergunta_errados(self):
        _, achados = self.tenta(3, lambda r: r.update(respostas=[self.resposta(edicao="2026-10-15")]))
        apoio.acusa(self, achados, "H2", "respostas[0].edicao")
        _, achados = self.tenta(3, lambda r: r.update(respostas=[self.resposta(pergunta="O Reino responde até 22/11?")]))
        achado = apoio.acusa(self, achados, "H2", "respostas[0].pergunta")
        self.assertIn(self.pergunta, achado.mensagem)
        segunda = self.arquivo.edicoes[dia(1)]["principais"][0]["vigiar"][1]
        _, achados = self.tenta(3, lambda r: r.update(respostas=[self.resposta(pergunta=segunda)]))
        apoio.acusa(self, achados, "H2", "respostas[0].pergunta")   # só a primeira pergunta é cobrada
        self.arquivo.publica_falha(dia(3))
        _, achados = self.tenta(4, lambda r: r.update(respostas=[self.resposta(edicao=dia(3))]))
        apoio.acusa(self, achados, "H2", "respostas[0].item")       # a edição de falha não tem principal

    def test_anula_vetor(self):
        vetor = dia(1) + "_p1_ue"
        self.assertIn(vetor, [v["id"] for v in self.arquivo.brutos["vetores"]["vetores"]])
        anula = self.errata(item="p1", url="https://exemplo.invalid/comissao_europeia/desmentido", anula_vetor=vetor)
        _, achados = self.tenta(3, lambda r: r.update(errata=[dict(anula, anula_vetor="2026-10-15_p1_ue")]))
        apoio.acusa(self, achados, "H2", "errata[0].anula_vetor")
        _, achados = self.tenta(3, lambda r: r.update(errata=[anula, dict(anula, erro="Texto fictício. Outro erro.")]))
        achado = apoio.acusa(self, achados, "H2", "errata[1].anula_vetor")
        self.assertIn("outra errata desta edição", achado.mensagem)
        terceira = self.arquivo.publica(dia(3), lambda r: r.update(errata=[anula]))
        self.assertEqual(valida.vetores_anulados(self.arquivo.dados()), {vetor: dia(3)})
        apoio.limpo(self, self.confere(terceira))                    # depois de publicada: a anulação é o próprio registro
        apoio.limpo(self, self.confere(terceira, do_dia=False))
        _, achados = self.tenta(4, lambda r: r.update(errata=[anula]))
        achado = apoio.acusa(self, achados, "H2", "errata[0].anula_vetor")
        self.assertIn("já foi anulado em " + dia(3), achado.mensagem)

    def test_com_historico_incompleto_so_se_confere_o_que_da(self):
        parcial = valida.Historico({dia(2): self.arquivo.edicoes[dia(2)]}, completo=False)
        rascunho = self.arquivo.rascunho(dia(3))
        rascunho["errata"] = [self.errata(edicao="2026-10-15")]
        rascunho["respostas"] = [self.resposta()]           # aponta para o dia 1, que não está no histórico parcial
        edicao = apoio.completa(rascunho, parcial, self.arquivo.dados(), apoio.indicadores_do_dia(dia(3)))
        apoio.limpo(self, self.confere(edicao, historico=parcial))
        edicao["radar"][0]["continuacao_de"] = dia(2) + "/r12"   # o dia 2 está: aí confere
        apoio.acusa(self, self.confere(edicao, historico=parcial), "H2", "radar[0].continuacao_de")

    def test_sem_historico_nada_de_h2(self):
        rascunho = self.arquivo.rascunho(dia(3))
        rascunho["errata"] = [self.errata(edicao="2026-10-15", url="https://exemplo.invalid/a/b", anula_vetor="nada")]
        edicao = apoio.completa(rascunho, self.arquivo.historico(), self.arquivo.dados())
        achados = valida.confere_edicao(edicao, self.arquivo.dados(), None, True, tamanho=40000)
        self.assertNotIn("H2", apoio.regras(achados))


class TestaH3(ComArquivo):
    """Avisos, não erros, e só na edição do dia."""

    def test_titulo_quase_igual_sem_continuacao_de(self):
        self.arquivo.publica(dia(1))

        def solta(rascunho):
            for item in rascunho["principais"] + rascunho["radar"]:
                item.pop("continuacao_de", None)
            rascunho["principais"][0]["titulo"] += " de novo"
            rascunho["principais"][1]["titulo"] = "Assunto que nunca saiu antes no monitor"
        edicao, achados = self.tenta(2, solta)
        apoio.limpo(self, achados)
        avisos = [a for a in achados if a.gravidade == "AVISO" and a.caminho.endswith(".titulo")]
        self.assertEqual(len(avisos), 8, apoio.linhas(avisos))
        self.assertEqual(avisos[0].linha(), "AVISO H3 principais[0].titulo: quase igual ao de %s/p1. Se continua a "
                         "história, use continuacao_de." % dia(1))
        self.assertNotIn("principais[1].titulo", [a.caminho for a in avisos])
        self.assertEqual([a for a in self.confere(edicao, do_dia=False) if a.regra == "H3"], [])

    def test_com_continuacao_de_nao_avisa(self):
        self.arquivo.publica(dia(1))
        _, achados = self.tenta(2, lambda r: None)
        self.assertEqual([a for a in achados if a.caminho.endswith(".titulo")], [])

    def test_so_as_3_ultimas_edicoes_contam(self):
        self.arquivo.publica(dia(1))
        for numero in (2, 3, 4):
            def outros_titulos(rascunho, numero=numero):
                for indice, item in enumerate(rascunho["principais"] + rascunho["radar"]):
                    item.pop("continuacao_de", None)
                    item["titulo"] = "Assunto %d do dia %d, sem parentesco com os outros" % (indice * 37 + numero * 1000, numero)
            self.arquivo.publica(dia(numero), outros_titulos)

        def solta(rascunho):
            for item in rascunho["principais"] + rascunho["radar"]:
                item.pop("continuacao_de", None)
        _, achados = self.tenta(5, solta)
        self.assertEqual([a for a in achados if a.caminho.endswith(".titulo")], [])

    def test_vetor_repetido_em_7_dias(self):
        self.arquivo.publica(dia(1))
        _, achados = self.tenta(8, lambda r: None)
        avisos = [a for a in achados if a.regra == "H3" and "vetores" in a.caminho]
        self.assertEqual([a.caminho for a in avisos], ["principais[0].vetores[0]", "radar[1].vetores[0]"])
        self.assertIn(dia(1) + "_p1_ue", avisos[0].mensagem)
        _, achados = self.tenta(9, lambda r: None)   # 8 dias depois: já não avisa
        self.assertEqual([a for a in achados if a.regra == "H3" and "vetores" in a.caminho], [])

    def test_vetor_anulado_nao_conta_como_repeticao(self):
        self.arquivo.publica(dia(1))
        anula = {"edicao": dia(1), "item": "p1", "erro": "Texto fictício. Estava errado.", "correcao": "Texto fictício. O certo.",
                 "url": "https://exemplo.invalid/comissao_europeia/desmentido", "anula_vetor": dia(1) + "_p1_ue"}

        def anula_e_tira(rascunho):
            rascunho["errata"] = [anula]
            rascunho["principais"][0]["vetores"] = []
            rascunho["radar"][1]["vetores"] = []
        self.arquivo.publica(dia(2), anula_e_tira)
        _, achados = self.tenta(3, lambda r: None)
        self.assertEqual([a.caminho for a in achados if a.regra == "H3"], ["radar[1].vetores[0]"])


class TestaPelaLinhaDeComando(apoio.ComRaiz):
    """--edicao com arquivo dentro de edicoes/ usa as outras edições; --anterior força a anterior."""

    def setUp(self):
        super().setUp()
        self.arquivo = apoio.Arquivo()
        self.arquivo.publica(dia(1), so("conflito.3"), indicadores=apoio.indicadores_calmos(dia(1)))
        for numero in (2, 3):
            self.arquivo.publica(dia(numero), apoio.sem_gatilhos, indicadores=apoio.indicadores_calmos(dia(numero)))
        self.arquivo.grava(self.raiz)

    def test_arquivo_dentro_de_edicoes_e_conferido_contra_as_outras(self):
        codigo, linhas = self.valida("--edicao", self.caminho("edicoes", dia(3) + ".json"))
        self.assertEqual((codigo, linhas[-1]), (0, "OK 0 erros, 2 avisos"), "\n".join(linhas))
        self.assertRegras(linhas, ["H3"], "AVISO")   # os dois vetores repetem os da véspera: avisa, não recusa
        self.muda("edicoes/%s.json" % dia(3), lambda e: dominio(e, "conflito").update(nivel=1))
        codigo, linhas = self.valida("--edicao", "edicoes/%s.json" % dia(3))   # relativo à raiz também vale
        self.assertEqual(codigo, 1)
        self.assertRegras(linhas, ["R13", "R14"])

    def test_nome_de_arquivo_diferente_da_data(self):
        os.rename(self.caminho("edicoes", dia(3) + ".json"), self.caminho("edicoes", dia(4) + ".json"))
        codigo, linhas = self.valida("--edicao", self.caminho("edicoes", dia(4) + ".json"))
        self.assertEqual(codigo, 1)
        self.assertRegras(linhas, ["R01"])

    def test_anterior_forca_a_edicao_anterior(self):
        fora = os.path.join(self.pasta, "solta.json")
        apoio.grava(fora, self.arquivo.edicoes[dia(3)])
        codigo, linhas = self.valida("--edicao", fora)      # fora de edicoes/: sem histórico, o nível mantido passa
        self.assertEqual((codigo, linhas[-1]), (0, "OK 0 erros, 0 avisos"), "\n".join(linhas))
        codigo, linhas = self.valida("--edicao", fora, "--anterior", self.caminho("edicoes", dia(2) + ".json"))
        self.assertEqual((codigo, linhas[-1]), (0, "OK 0 erros, 2 avisos"), "\n".join(linhas))
        # com a edição do dia 1 (a do gatilho) como anterior, a conta muda: 1 calma só não bastaria... e o desde bate
        codigo, linhas = self.valida("--edicao", fora, "--anterior", self.caminho("edicoes", dia(1) + ".json"))
        self.assertEqual((codigo, linhas[-1]), (0, "OK 0 erros, 2 avisos"), "\n".join(linhas))
        calma = os.path.join(self.pasta, "calma.json")
        apoio.grava(calma, dict(self.arquivo.edicoes[dia(2)], alerta=dict(
            self.arquivo.edicoes[dia(2)]["alerta"], nivel=1,
            dominios=[dict(d, nivel=1, desde=dia(2)) for d in self.arquivo.edicoes[dia(2)]["alerta"]["dominios"]])))
        codigo, linhas = self.valida("--edicao", fora, "--anterior", calma)   # a anterior diz nível 1: o 3 não se explica
        self.assertEqual(codigo, 1)
        self.assertIn("ERRO R13 alerta.dominios[4].nivel", "\n".join(linhas))

    def test_anterior_ilegivel_ou_que_nao_e_anterior(self):
        fora = os.path.join(self.pasta, "solta.json")
        apoio.grava(fora, self.arquivo.edicoes[dia(2)])
        codigo, linhas = self.valida("--edicao", fora, "--anterior", os.path.join(self.pasta, "nao-existe.json"))
        self.assertEqual(codigo, 1)
        self.assertRegras(linhas, ["ARQUIVO"])
        codigo, linhas = self.valida("--edicao", fora, "--anterior", self.caminho("edicoes", dia(3) + ".json"))
        self.assertEqual(codigo, 1)
        self.assertIn("não é anterior", linhas[0])
        codigo, linhas = self.valida("--edicao", fora, "--anterior", self.caminho("dados", "vetores.json"))
        self.assertEqual(codigo, 1)
        self.assertRegras(linhas, ["ARQUIVO"])


if __name__ == "__main__":
    unittest.main()
