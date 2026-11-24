#!/usr/bin/env python3
"""Testes do valida.py: o modo --dados.

Régua, players, mapa de veículos (regras M1 e M2), vetores, catálogo de indicadores (regras C1, C2, C5 e C6) e a
forma do índice. Para cada regra, um defeito plantado nos dados congelados é acusado com o código certo, e
um valor no limite permitido passa. E nenhum dado torto derruba o validador.

Rodar da raiz do repositório: python3 -B testes/testa_valida_dados.py
"""
import copy
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "valida"))

import apoio  # noqa: E402
from apoio import valida  # noqa: E402


def confere(objetos, **nomeados):
    """Os achados do modo --dados para um conjunto de objetos: o que é fatal mais o resto."""
    dados = apoio.monta(objetos)
    return dados.problemas + valida.confere_dados(dados, **nomeados)


class ComDados(unittest.TestCase):
    maxDiff = None

    def planta(self, regra, muda, caminho=None, gravidade="ERRO"):
        objetos = apoio.brutos()
        muda(objetos)
        return apoio.acusa(self, confere(objetos), regra, caminho, gravidade)

    def passa(self, muda=None):
        objetos = apoio.brutos()
        if muda is not None:
            muda(objetos)
        apoio.limpo(self, confere(objetos))


def veiculo(objetos, identificador):
    return [v for v in objetos["veiculos"]["veiculos"] if v["id"] == identificador][0]


def indicador(objetos, identificador):
    return [i for i in objetos["indicadores"]["indicadores"] if i["id"] == identificador][0]


def player(objetos, identificador):
    return [p for p in objetos["players"]["players"] if p["id"] == identificador][0]


class TestaDadosCongelados(ComDados):
    def test_os_dados_congelados_passam_sem_achado(self):
        # Com a CNBC como segunda fonte dos grãos, a C5 fecha também no trigo, no milho e na soja.
        achados = confere(apoio.brutos())
        apoio.limpo(self, achados)
        self.assertEqual([(a.regra, a.caminho) for a in achados], [])

    def test_o_que_o_objeto_dados_oferece(self):
        dados = apoio.dados()
        self.assertEqual(dados.dominios, ["energia", "alimentos", "cambio", "suprimentos", "conflito"])
        self.assertEqual(len(dados.partidos), 7)
        self.assertEqual(dados.partidos[-1], "independentes")
        self.assertEqual(dados.voto["independentes"], {})
        self.assertEqual(dados.voto["centro_atlantico"]["imigracao"], "R")
        self.assertEqual(dados.campo_de, {"ordem_global": "ordem", "centro_atlantico": "ordem",
                                          "soberanistas": "contestacao", "eixo_revisionista": "contestacao"})
        self.assertEqual(dados.codigos["energia.3"], ("energia", 3))
        self.assertEqual(len(dados.codigos), 25)
        self.assertEqual(dados.precos["energia"], [(2, "brent", "7d", 5), (3, "brent", "7d", 10), (4, "brent", "7d", 20)])
        self.assertEqual(dados.rotulos[2], "ATENÇÃO")
        self.assertEqual(dados.forcas, [1, 2, 3])
        self.assertIn("anthropic", dados.conflito_players)
        self.assertIn("gov.br", dados.oficiais_brasil)
        self.assertIn("europa.eu", dados.oficiais)
        self.assertEqual(dados.partido_do_player("ue"), "centro_atlantico")
        self.assertIsNone(dados.partido_do_player("ninguem"))
        self.assertEqual(dados.mapa["reuters"]["sites"], ["reuters.com"])
        self.assertIsNone(dados.revisado_em)
        self.assertEqual(sorted(dados.ligados), ["anthropic_news", "fli", "import_ai"])
        self.assertEqual(dados.catalogo[:2], ["brent", "wti"])
        self.assertEqual(dados.indicador["brent"]["dominio"], "energia")
        self.assertEqual(dados.vetores, [])
        self.assertEqual(list(dados.bruto), list(apoio.ARQUIVOS_DE_DADOS))


class TestaMapa(ComDados):
    """ESQUEMA, seção 15."""

    def test_m1_revisado_em(self):
        self.planta("M1", lambda o: o["veiculos"].pop("revisado_em"), "dados/veiculos.json:revisado_em")
        self.planta("M1", lambda o: o["veiculos"].update(revisado_em="ontem"), "revisado_em")
        self.planta("M1", lambda o: o["veiculos"].update(revisado_em="2026-02-30"), "revisado_em")
        self.planta("M1", lambda o: o["veiculos"].update(revisado_em=False), "revisado_em")
        self.assertIsNone(apoio.brutos()["veiculos"]["revisado_em"])    # null: mapa em rascunho
        self.passa(lambda o: o["veiculos"].update(revisado_em="2026-12-01"))
        revisado = apoio.brutos()
        revisado["veiculos"]["revisado_em"] = "2026-12-01"
        self.assertEqual(apoio.monta(revisado).revisado_em, "2026-12-01")

    def test_m2_sites(self):
        self.planta("M2", lambda o: veiculo(o, "reuters").pop("sites"), "veiculos[")
        self.planta("M2", lambda o: veiculo(o, "reuters").update(sites=[]), ".sites")
        self.planta("M2", lambda o: veiculo(o, "reuters").update(sites="reuters.com"), ".sites")
        self.planta("M2", lambda o: veiculo(o, "reuters").update(sites=["s%d.exemplo.invalid" % n for n in range(7)]), ".sites")
        self.passa(lambda o: veiculo(o, "reuters").update(sites=["s%d.exemplo.invalid" % n for n in range(6)]))
        for ruim in ("Reuters.com", "www.reuters.com", "reuters.com/", "https://reuters.com", "reuters", "reuters com", 7,
                     "reuters.com:443"):
            achado = self.planta("M2", lambda o: veiculo(o, "reuters").update(sites=["reuters.com", ruim]), ".sites[1]")
            self.assertIn("minúsculas", achado.mensagem)
            self.assertIn("sem porta", achado.mensagem)   # ESQUEMA, seção 15, M2
        self.planta("M2", lambda o: veiculo(o, "reuters").update(sites=["reuters.com", "reuters.com"]), ".sites[1]")

    def test_os_campos_que_as_regras_da_edicao_usam(self):
        self.planta("DADOS", lambda o: veiculo(o, "nyt").update(lado="esquerda"), ".lado")
        self.planta("DADOS", lambda o: veiculo(o, "nyt").update(lado_confianca="total"), ".lado_confianca")
        self.planta("DADOS", lambda o: veiculo(o, "nyt").update(fatos="boa"), ".fatos")
        self.planta("DADOS", lambda o: veiculo(o, "nyt").update(tipo="jornal"), ".tipo")
        self.planta("DADOS", lambda o: veiculo(o, "nyt").update(serve_a=["ninguem"]), ".serve_a[0]")
        self.planta("DADOS", lambda o: veiculo(o, "nyt").update(alvos="trump"), ".alvos")
        self.planta("DADOS", lambda o: veiculo(o, "nyt").update(nome=""), ".nome")
        self.planta("DADOS", lambda o: veiculo(o, "nyt").update(id="reuters"), ".id")
        self.planta("DADOS", lambda o: veiculo(o, "nyt").update(id="outro"), ".id")
        self.planta("DADOS", lambda o: veiculo(o, "nyt").update(id="NYT"), ".id")
        self.planta("DADOS", lambda o: veiculo(o, "nyt").update(feeds=[{"url": "feed"}]), ".feeds[0].url")
        self.planta("DADOS", lambda o: veiculo(o, "nyt").update(feeds=None), ".feeds")
        self.planta("DADOS", lambda o: veiculo(o, "nyt").update(controle_fonte="wikipedia"), ".controle_fonte")
        self.planta("DADOS", lambda o: o["veiculos"]["veiculos"].append("bbc"), "veiculos[146]")
        self.planta("DADOS", lambda o: o["veiculos"].update(versao=2), "dados/veiculos.json:versao")

    def test_mapa_que_nao_serve_de_base(self):
        self.planta("DADOS", lambda o: o.update(veiculos=[]), "dados/veiculos.json")
        self.planta("DADOS", lambda o: o["veiculos"].update(veiculos={}), "dados/veiculos.json:veiculos")
        self.planta("DADOS", lambda o: o["veiculos"].pop("veiculos"), "dados/veiculos.json:veiculos")


class TestaCatalogo(ComDados):
    """ESQUEMA, seção 14."""

    def test_c1_ids_unicos_e_de_1_a_20(self):
        self.planta("C1", lambda o: indicador(o, "wti").update(id="brent"), "indicadores[1].id")
        self.planta("C1", lambda o: o["indicadores"].update(indicadores=[]), "dados/indicadores.json:indicadores")
        self.planta("C1", lambda o: indicador(o, "wti").update(id="WTI"), "indicadores[1].id")
        self.planta("C1", lambda o: indicador(o, "wti").update(id="r4"), "indicadores[1].id")

        def com(quantos):
            def muda(o):
                molde = indicador(o, "wti")
                o["indicadores"]["indicadores"] += [dict(molde, id="extra_%d" % n) for n in range(quantos - 12)]
            return muda
        self.passa(com(20))
        self.planta("C1", com(21), "dados/indicadores.json:indicadores")

    def test_c2_indicador_citado_na_regua(self):
        def tira(o):
            o["indicadores"]["indicadores"] = [i for i in o["indicadores"]["indicadores"] if i["id"] != "brent"]
        achado = self.planta("C2", tira, "dados/indicadores.json:indicadores")
        self.assertIn("'brent'", achado.mensagem)
        self.planta("C2", lambda o: indicador(o, "usd_brl").update(obrigatorio=False), "indicadores[7]")
        self.planta("C2", lambda o: indicador(o, "soja").update(frequencia="mensal"), "indicadores[5]")
        self.passa(lambda o: indicador(o, "wti").update(obrigatorio=True))   # obrigatório sem critério na régua pode

    def test_c5_e_aviso_e_nao_erro(self):
        achado = self.planta("C5", lambda o: indicador(o, "brent").update(fontes=indicador(o, "brent")["fontes"][:1]),
                             "indicadores[0].fontes", "AVISO")
        self.assertIn("nunca passa do nível 2", achado.mensagem)
        self.passa(lambda o: indicador(o, "brent").update(fontes=indicador(o, "brent")["fontes"][:1]))
        com_duas = apoio.brutos()
        for nome in ("trigo", "milho", "soja"):
            indicador(com_duas, nome)["fontes"] = indicador(com_duas, "brent")["fontes"]
        self.assertEqual(confere(com_duas), [])

    def test_forma_de_cada_indicador(self):
        self.planta("DADOS", lambda o: indicador(o, "wti").update(nome="x" * 61), "indicadores[1].nome")
        self.passa(lambda o: indicador(o, "wti").update(nome="x" * 60))
        self.planta("DADOS", lambda o: indicador(o, "wti").update(unidade="x" * 31), "indicadores[1].unidade")
        self.planta("DADOS", lambda o: indicador(o, "wti").update(dominio="petroleo"), "indicadores[1].dominio")
        self.planta("DADOS", lambda o: indicador(o, "wti").update(frequencia="semanal"), "indicadores[1].frequencia")
        self.planta("DADOS", lambda o: indicador(o, "wti").update(obrigatorio="nao"), "indicadores[1].obrigatorio")
        for faixa in ({"min": 10, "max": 10}, {"min": -1, "max": 10}, {"min": 5}, [5, 400], {"min": "5", "max": 400}):
            self.planta("DADOS", lambda o: indicador(o, "wti").update(faixa=faixa), "indicadores[1].faixa")
        self.passa(lambda o: indicador(o, "wti").update(faixa={"min": 0, "max": 0.5}))
        self.planta("DADOS", lambda o: indicador(o, "wti").update(casas=7), "indicadores[1].casas")
        self.planta("DADOS", lambda o: indicador(o, "wti").update(casas=2.0), "indicadores[1].casas")
        self.passa(lambda o: indicador(o, "wti").update(casas=0))
        self.passa(lambda o: indicador(o, "wti").pop("casas"))
        self.planta("DADOS", lambda o: indicador(o, "wti").update(fontes=[]), "indicadores[1].fontes")
        self.planta("DADOS", lambda o: indicador(o, "wti").update(fontes=indicador(o, "wti")["fontes"] * 3), "indicadores[1].fontes")

    def test_forma_de_cada_fonte(self):
        def fonte(o):
            return indicador(o, "wti")["fontes"][0]
        self.planta("DADOS", lambda o: fonte(o).update(leitor="csv_qualquer"), "indicadores[1].fontes[0].leitor")
        self.planta("DADOS", lambda o: fonte(o).update(url="yahoo"), "indicadores[1].fontes[0].url")
        self.planta("DADOS", lambda o: fonte(o).update(fator=0), "indicadores[1].fontes[0].fator")
        self.planta("DADOS", lambda o: fonte(o).update(fator="2"), "indicadores[1].fontes[0].fator")
        self.passa(lambda o: fonte(o).update(fator=0.3674371))
        self.planta("DADOS", lambda o: fonte(o).update(nota="x" * 201), "indicadores[1].fontes[0].nota")
        self.planta("DADOS", lambda o: fonte(o).update(nome=None), "indicadores[1].fontes[0].nome")
        for leitor in valida.LEITORES:
            self.passa(lambda o: fonte(o).update(leitor=leitor))

    def test_a_lista_de_leitores_e_a_do_indicadores_py(self):
        """ESQUEMA, seção 0, lista leitor: os seis do CONTRATO, seção 2, os mesmos que o indicadores.py sabe ler."""
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ferramentas"))
        import indicadores
        self.assertEqual(valida.LEITORES, ("fred_csv", "yahoo_chart", "bcb_sgs", "eia_v2", "fao_csv", "cnbc_chart"))
        self.assertEqual(sorted(valida.LEITORES), sorted(indicadores.LEITORES))

    def test_c6_contratos(self):
        """ESQUEMA, seção 14, C6: objeto com exatamente `modelo` e `meses`; `modelo` é URL com exatamente uma marca
        {c}; `meses` tem de 1 a 12 letras de FGHJKMNQUVXZ, sem repetir, na ordem do ano."""
        modelo = "https://precos.exemplo.invalid/chart/ZC{c}.CBT?range=1mo&interval=1d"

        def contratos(valor):
            return lambda o: indicador(o, "milho")["fontes"][0].update(contratos=valor)

        cf = "indicadores[4].fontes[0].contratos"
        self.assertIn("contratos", indicador(apoio.brutos(), "milho")["fontes"][0])  # o catálogo congelado já tem
        self.passa(contratos({"modelo": modelo, "meses": "HKNUZ"}))
        self.passa(contratos({"meses": "FGHJKMNQUVXZ", "modelo": modelo}))
        self.passa(contratos({"modelo": modelo, "meses": "Z"}))
        self.passa(lambda o: indicador(o, "milho")["fontes"][0].pop("contratos"))  # o campo é opcional
        for torto in (None, "HKNUZ", [modelo], {}, {"modelo": modelo}, {"meses": "HKNUZ"},
                      {"modelo": modelo, "meses": "HKNUZ", "nota": "x"}):
            self.planta("C6", contratos(torto), cf)
        for modelo_torto in (modelo.replace("{c}", "H27"), modelo + "&x={c}", "ftp://precos.exemplo.invalid/{c}",
                             "https://precos.exemplo.invalid/ {c}", 7, None):
            self.planta("C6", contratos({"modelo": modelo_torto, "meses": "HKNUZ"}), cf + ".modelo")
        for meses in ("", "ZH", "HH", "hknuz", "HKNUZA", "FGHJKMNQUVXZF", 5, ["H"], None):
            self.planta("C6", contratos({"modelo": modelo, "meses": meses}), cf + ".meses")


class TestaRegua(ComDados):
    def regua(self, regra, muda, caminho):
        return self.planta(regra, lambda o: muda(o["regua"]), "dados/regua.json:" + caminho)

    def test_ids_unicos_e_listas_que_existem(self):
        self.regua("DADOS", lambda r: r["partidos"][1].update(id="ordem_global"), "partidos[1].id")
        self.regua("DADOS", lambda r: r["partidos"][1].update(sigla="OG"), "partidos[1].sigla")
        self.regua("DADOS", lambda r: r["temas"][1].update(id="pandemia_inicio"), "temas[1].id")
        self.regua("DADOS", lambda r: r["temas"].pop(), "temas")                       # some o tema atual imigracao
        self.regua("DADOS", lambda r: r["partidos"].pop(), "partidos")                 # some independentes
        self.regua("DADOS", lambda r: r.update(versao="1"), "versao")
        self.regua("DADOS", lambda r: r["tipos"].pop(), "tipos")
        self.regua("DADOS", lambda r: r["valores"].pop("W"), "valores")
        self.regua("DADOS", lambda r: r["polos"].pop("azul"), "polos.azul")

    def test_voto_tipico(self):
        self.regua("DADOS", lambda r: r["partidos"][0].update(voto_tipico="B B B B B B"), "partidos[0].voto_tipico")
        self.regua("DADOS", lambda r: r["partidos"][0].update(voto_tipico="B B B B B B X"), "partidos[0].voto_tipico")
        self.regua("DADOS", lambda r: r["partidos"][0].update(voto_tipico=None), "partidos[0].voto_tipico")
        self.assertEqual(apoio.brutos()["regua"]["partidos"][6]["voto_tipico"], "")   # independentes: vazio vale

    def test_cinco_dominios_cada_um_com_canal(self):
        self.regua("DADOS", lambda r: r["dominios"][0].pop("canal"), "dominios[0].canal")
        self.regua("DADOS", lambda r: r["dominios"][0].update(canal="  "), "dominios[0].canal")
        self.regua("DADOS", lambda r: r["dominios"].pop(), "dominios")
        self.regua("DADOS", lambda r: r["dominios"].append(dict(r["dominios"][0], id="agua")), "dominios")

    def test_cinco_niveis_com_codigos_dominio_ponto_nivel(self):
        self.regua("DADOS", lambda r: r["niveis_alerta"].pop(), "niveis_alerta")
        self.regua("DADOS", lambda r: r["niveis_alerta"][2].update(nivel=4), "niveis_alerta[2].nivel")
        self.regua("DADOS", lambda r: r["niveis_alerta"][2].update(rotulo=""), "niveis_alerta[2].rotulo")
        self.regua("DADOS", lambda r: r["niveis_alerta"][2]["criterios"]["energia"].update(codigo="energia.4"),
                   "niveis_alerta[2].criterios.energia.codigo")
        self.regua("DADOS", lambda r: r["niveis_alerta"][2]["criterios"].pop("conflito"), "niveis_alerta[2].criterios")
        self.regua("DADOS", lambda r: r["niveis_alerta"][2]["criterios"].update(agua={}), "niveis_alerta[2].criterios")
        self.regua("DADOS", lambda r: r["niveis_alerta"][2]["criterios"]["energia"].update(eventos=[""]),
                   "niveis_alerta[2].criterios.energia.eventos")
        self.regua("DADOS", lambda r: r["niveis_alerta"][2]["criterios"].update(energia="x"), "niveis_alerta[2].criterios.energia")

    def test_criterios_de_preco(self):
        def preco(r):
            return r["niveis_alerta"][1]["criterios"]["energia"]["precos"][0]
        caminho = "niveis_alerta[1].criterios.energia.precos[0]"
        self.regua("DADOS", lambda r: preco(r).update(janela="30d"), caminho + ".janela")
        self.regua("DADOS", lambda r: preco(r).update(alta_minima_pct=0), caminho + ".alta_minima_pct")
        self.regua("DADOS", lambda r: preco(r).update(alta_minima_pct="5"), caminho + ".alta_minima_pct")
        self.regua("DADOS", lambda r: preco(r).update(indicador=7), caminho + ".indicador")
        self.regua("DADOS", lambda r: preco(r).pop("texto"), caminho + ".texto")
        self.regua("DADOS", lambda r: r["niveis_alerta"][0]["criterios"]["energia"]["precos"].append(preco(r)),
                   "niveis_alerta[0].criterios.energia.precos")
        self.regua("DADOS", lambda r: r["niveis_alerta"][1]["criterios"]["energia"].update(precos=None),
                   "niveis_alerta[1].criterios.energia.precos")
        self.planta("C2", lambda o: o["regua"]["niveis_alerta"][1]["criterios"]["energia"]["precos"][0].update(indicador="cobre"),
                    "dados/indicadores.json:indicadores")
        self.passa(lambda o: preco(o["regua"]).update(alta_minima_pct=7.5))    # o dono recalibra o limiar

    def test_campos_forcas_evidencias_e_times(self):
        self.regua("DADOS", lambda r: r["campos"][0]["partidos"].append("verdes"), "campos[0].partidos[2]")
        self.regua("DADOS", lambda r: r["campos"][1]["partidos"].append("ordem_global"), "campos[1].partidos[2]")
        self.regua("DADOS", lambda r: r["campos"][0].update(partidos=[]), "campos[0].partidos")
        self.regua("DADOS", lambda r: r["campos"].pop(), "campos")
        self.regua("DADOS", lambda r: r["forcas"].pop(), "forcas")
        self.regua("DADOS", lambda r: r["forcas"][0].update(forca=0), "forcas")
        self.regua("DADOS", lambda r: r["forcas"][0].pop("nome"), "forcas[0].nome")
        self.regua("DADOS", lambda r: r["evidencias"].pop(), "evidencias")             # some narrativa
        self.regua("DADOS", lambda r: r["evidencias"][0].update(o_que_conta=3), "evidencias[0].o_que_conta")
        self.regua("DADOS", lambda r: r["times_avanco"].pop("mudanca"), "times_avanco.mudanca")
        self.regua("DADOS", lambda r: r["times_avanco"].update(reforma="x"), "times_avanco")
        self.regua("DADOS", lambda r: r.update(times_avanco=[]), "times_avanco")
        self.passa(lambda o: o["regua"]["times_avanco"].pop("nao_move"))

    def test_conflito_e_sites_oficiais_com_ids_que_existem(self):
        self.regua("DADOS", lambda r: r["conflito"]["players"].append("openai"), "conflito.players[5]")
        self.regua("DADOS", lambda r: r["conflito"].update(termos=["OpenAI", " Grok"]), "conflito.termos")
        self.regua("DADOS", lambda r: r["conflito"].update(termos="OpenAI"), "conflito.termos")
        self.regua("DADOS", lambda r: r["conflito"].pop("regra"), "conflito.regra")
        self.regua("DADOS", lambda r: r["sites_oficiais"]["brasil"].append("WWW.gov.br"), "sites_oficiais.brasil[4]")
        self.regua("DADOS", lambda r: r["sites_oficiais"]["outros"].append("gov.uk/"), "sites_oficiais.outros[15]")
        self.regua("DADOS", lambda r: r["sites_oficiais"].update(outros="gov"), "sites_oficiais.outros")
        self.passa(lambda o: o["regua"]["conflito"]["termos"].append("Mistral"))        # o dono amplia a lista
        self.passa(lambda o: o["regua"]["sites_oficiais"]["outros"].append("gob.mx"))

    def test_regua_que_nao_serve_de_base(self):
        for chave in ("temas", "partidos", "dominios", "niveis_alerta", "campos", "evidencias", "forcas",
                      "conflito", "sites_oficiais"):
            achado = self.regua("DADOS", lambda r: r.pop(chave), chave)
            self.assertIn("Sem isso não dá para conferir edição", achado.mensagem)
            self.regua("DADOS", lambda r: r.update({chave: "x"}), chave)
        self.planta("DADOS", lambda o: o.update(regua=["x"]), "dados/regua.json")


class TestaPlayers(ComDados):
    def test_forma_de_cada_player(self):
        self.planta("DADOS", lambda o: player(o, "nyt").update(id="oms_onu"), "players[1].id")
        self.planta("DADOS", lambda o: player(o, "nyt").update(id="soberanistas"), "players[1].id")
        self.planta("DADOS", lambda o: player(o, "nyt").update(id="nenhum"), "players[1].id")
        self.planta("DADOS", lambda o: player(o, "nyt").update(partido="imprensa"), "players[1].partido")
        self.planta("DADOS", lambda o: player(o, "nyt").update(tipo="jornal"), "players[1].tipo")
        self.planta("DADOS", lambda o: player(o, "nyt").update(time="reforma"), "players[1].time")
        self.planta("DADOS", lambda o: player(o, "nyt").update(origem="dono"), "players[1].origem")
        self.planta("DADOS", lambda o: player(o, "nyt").update(time_discutivel="nao"), "players[1].time_discutivel")
        self.planta("DADOS", lambda o: player(o, "nyt").update(incluido_em="20/11/2026"), "players[1].incluido_em")
        self.planta("DADOS", lambda o: player(o, "nyt").update(nota=""), "players[1].nota")
        self.planta("DADOS", lambda o: player(o, "nyt").update(duvidas=["economia"]), "players[1].duvidas")
        self.planta("DADOS", lambda o: o["players"].update(atualizado_em="hoje"), "dados/players.json:atualizado_em")
        self.planta("DADOS", lambda o: o["players"].update(players=None), "dados/players.json:players")

    def test_dna_valido(self):
        self.planta("DADOS", lambda o: player(o, "nyt")["dna"].update(clima="X"), "players[1].dna.clima")
        self.planta("DADOS", lambda o: player(o, "nyt")["dna"].update(clima="BRY"), "players[1].dna.clima")
        self.planta("DADOS", lambda o: player(o, "nyt")["dna"].update(clima=""), "players[1].dna.clima")
        self.planta("DADOS", lambda o: player(o, "nyt")["dna"].pop("clima"), "players[1].dna")
        self.planta("DADOS", lambda o: player(o, "nyt")["dna"].update(economia="B"), "players[1].dna")
        self.planta("DADOS", lambda o: player(o, "nyt").update(dna="BBBBBBB"), "players[1].dna")
        for vale in ("B", "R", "Y", "W", "K", "BR", "YR"):                               # virada: duas letras
            self.passa(lambda o: player(o, "nyt")["dna"].update(clima=vale))

    def test_player_que_a_rotina_incluiu(self):
        def inclui(**campos):
            def muda(o):
                novo = dict(apoio.exemplo()["novos_players"][0], origem="rotina", incluido_em="2026-11-19")
                novo.update(campos)
                o["players"]["players"].append(novo)
            return muda
        self.passa(inclui())
        self.planta("DADOS", inclui(url="sem esquema"), "players[30].url")
        self.planta("DADOS", inclui(dna_fontes={"clima": "x"}), "players[30].dna_fontes")
        self.planta("DADOS", inclui(justificativa=""), "players[30].justificativa")


class TestaVetores(ComDados):
    """ESQUEMA, seção 12: vetores e anulações bem formados."""

    def setUp(self):
        arquivo = apoio.Arquivo()
        arquivo.publica("2026-11-01")
        anula = {"edicao": "2026-11-01", "item": "p1", "erro": "Texto fictício. Errado.", "correcao": "Texto fictício. Certo.",
                 "url": "https://exemplo.invalid/comissao_europeia/desmentido", "anula_vetor": "2026-11-01_p1_ue"}
        arquivo.publica("2026-11-02", lambda r: r.update(errata=[anula]))
        self.objetos = arquivo.brutos
        self.assertEqual([v["id"] for v in self.objetos["vetores"]["vetores"]],
                         ["2026-11-01_p1_ue", "2026-11-01_r2_google", "2026-11-02_p1_ue", "2026-11-02_r2_google",
                          "2026-11-02_anula_1"])

    def vetor(self, regra_e_caminho, muda):
        objetos = copy.deepcopy(self.objetos)
        muda(objetos["vetores"]["vetores"])
        return apoio.acusa(self, confere(objetos), "DADOS", "dados/vetores.json:" + regra_e_caminho)

    def test_o_registro_que_o_publicador_grava_passa(self):
        apoio.limpo(self, confere(self.objetos))
        self.assertIs(self.objetos["vetores"]["vetores"][1]["conflito_de_interesse"], True)    # o item r2 é de IA
        self.assertNotIn("conflito_de_interesse", self.objetos["vetores"]["vetores"][0])

    def test_vetor_mal_formado(self):
        self.vetor("vetores[0].id", lambda v: v[0].update(id="2026-11-01_p2_ue"))
        self.vetor("vetores[2].id", lambda v: v[2].update(id="2026-11-01_p1_ue", data="2026-11-01"))   # repetido
        self.vetor("vetores[0].player", lambda v: v[0].update(player="uniao_europeia"))
        self.vetor("vetores[0].de", lambda v: v[0].update(de="soberanistas"))
        self.vetor("vetores[0].para", lambda v: v[0].update(para="direita"))
        self.vetor("vetores[0].forca", lambda v: v[0].update(forca=5))
        self.vetor("vetores[0].tema", lambda v: v[0].update(tema="economia"))
        self.vetor("vetores[0].url", lambda v: v[0].update(url="sem esquema"))
        self.vetor("vetores[0].porque", lambda v: v[0].update(porque=""))
        self.vetor("vetores[0].item", lambda v: v[0].update(item="x1"))
        self.vetor("vetores[0].data", lambda v: v[0].update(data="01/11/2026"))
        self.vetor("vetores[1].conflito_de_interesse", lambda v: v[1].update(conflito_de_interesse=False))
        self.vetor("vetores[0]", lambda v: v.__setitem__(0, "vetor"))

    def test_anulacao_mal_formada(self):
        self.vetor("vetores[4].anula", lambda v: v[4].update(anula="2026-10-01_p1_ue"))
        self.vetor("vetores[4].id", lambda v: v[4].update(id="2026-11-02_p9_ue"))
        self.vetor("vetores[4].id", lambda v: v[4].update(data="2026-11-03"))
        self.vetor("vetores[4].url", lambda v: v[4].pop("url"))
        self.vetor("vetores[5].anula", lambda v: v.append(dict(v[4], id="2026-11-02_anula_2")))           # anulado 2 vezes
        self.vetor("vetores[0].anula", lambda v: v.insert(0, v.pop(4)))                                  # antes do vetor


class TestaIndice(unittest.TestCase):
    """ESQUEMA, seção 11."""

    maxDiff = None

    def setUp(self):
        self.arquivo = apoio.Arquivo()
        self.arquivo.publica("2026-11-01")
        self.arquivo.publica_falha("2026-11-02")
        errata = {"edicao": "2026-11-01", "item": "r3", "erro": "Texto fictício. Errado.", "correcao": "Texto fictício. Certo."}
        self.arquivo.publica("2026-11-03", lambda r: r.update(errata=[errata]))
        exemplo = apoio.exemplo()
        exemplo["data"] = "2026-11-04"
        exemplo["gerada_em"] = "2026-11-04T21:00:00Z"
        self.arquivo.poe("2026-11-04", exemplo)
        self.edicoes = self.arquivo.edicoes
        self.indice = valida.monta_indice(self.edicoes)

    def test_o_indice_montado_segue_o_esquema(self):
        self.assertEqual(list(self.indice), ["versao", "atualizado_em", "edicoes"])
        self.assertEqual(self.indice["atualizado_em"], "2026-11-04T21:00:00Z")
        self.assertEqual([e["data"] for e in self.indice["edicoes"]], ["2026-11-04", "2026-11-03", "2026-11-02", "2026-11-01"])
        primeira = self.indice["edicoes"][3]
        self.assertEqual(list(primeira), ["data", "arquivo", "texto", "estado", "nivel", "tendencia", "niveis", "saldos",
                                          "eixos", "indicadores", "resumo", "gerada_em", "exemplo", "corrigida_em"])
        edicao = self.edicoes["2026-11-01"]
        self.assertEqual((primeira["arquivo"], primeira["texto"]), ("edicoes/2026-11-01.json", "edicoes/2026-11-01.md"))
        self.assertEqual(primeira["niveis"], {"energia": 3, "alimentos": 1, "cambio": 1, "suprimentos": 2, "conflito": 3})
        self.assertEqual(list(primeira["niveis"]), apoio.dados().dominios)
        self.assertEqual(primeira["saldos"], dict((l["partido"], l["saldo"]) for l in edicao["placar_do_dia"]))
        self.assertEqual(list(primeira["saldos"])[0], "ordem_global")
        self.assertEqual(primeira["eixos"], {"clima": {"azul": 0, "vermelho": 1}, "ia_depois": {"azul": 2, "vermelho": 0}})
        self.assertEqual(primeira["indicadores"]["brent"], 78.4)
        self.assertNotIn("gas_natural", primeira["indicadores"])      # sem valor
        self.assertNotIn("frete_seco", primeira["indicadores"])       # defasado
        self.assertEqual((primeira["estado"], primeira["nivel"], primeira["tendencia"], primeira["resumo"], primeira["gerada_em"]),
                         ("completa", 3, "estavel", edicao["resumo"], edicao["gerada_em"]))
        self.assertIs(primeira["exemplo"], False)
        self.assertEqual(primeira["corrigida_em"], ["2026-11-03"])
        self.assertIs(self.indice["edicoes"][0]["exemplo"], True)
        falha = self.indice["edicoes"][2]
        self.assertEqual((falha["estado"], falha["saldos"], falha["eixos"], falha["indicadores"]), ("falha", {}, {}, {}))
        self.assertEqual(valida.monta_indice({}), {"versao": 1, "atualizado_em": None, "edicoes": []})

    def test_indice_igual_aos_arquivos_passa(self):
        self.assertEqual(valida.confere_indice(self.indice, self.edicoes, lambda caminho: True), [])
        self.assertEqual(valida.confere_indice(self.indice), [])
        self.assertEqual(valida.confere_indice(valida.monta_indice({}), {}), [])

    def planta(self, muda, caminho, edicoes="as do arquivo"):
        indice = copy.deepcopy(self.indice)
        muda(indice)
        achados = valida.confere_indice(indice, self.edicoes if edicoes == "as do arquivo" else edicoes)
        return apoio.acusa(self, achados, "INDICE", "edicoes/indice.json" + (":" + caminho if caminho else ""))

    def test_indice_diferente_dos_arquivos(self):
        achado = self.planta(lambda i: i["edicoes"][3].update(nivel=2), "edicoes[3]")
        self.assertIn("não bate com edicoes/2026-11-01.json nos campos: nivel", achado.mensagem)
        self.assertIn("publica.py refaz", achado.mensagem)
        self.planta(lambda i: i["edicoes"][3]["saldos"].update(ordem_global=True), "edicoes[3]")   # 1 não é true
        self.planta(lambda i: i["edicoes"][3].update(corrigida_em=[]), "edicoes[3]")
        self.planta(lambda i: i["edicoes"][3].update(extra=1), "edicoes[3]")
        self.planta(lambda i: i["edicoes"][3].pop("eixos"), "edicoes[3]")
        self.planta(lambda i: i["edicoes"].pop(1), "edicoes")
        self.planta(lambda i: i["edicoes"].insert(0, dict(i["edicoes"][0], data="2026-11-09", arquivo="edicoes/2026-11-09.json",
                                                          texto="edicoes/2026-11-09.md")), "edicoes[0]")
        self.planta(lambda i: i.update(atualizado_em="2026-11-03T21:14:03Z"), "atualizado_em")
        self.planta(lambda i: i.update(extra=[]), "")

    def test_forma_do_indice(self):
        self.planta(lambda i: i["edicoes"].reverse(), "edicoes[1].data", None)
        self.planta(lambda i: i["edicoes"].append(dict(i["edicoes"][3])), "edicoes[4].data", None)
        self.planta(lambda i: i["edicoes"][0].update(arquivo="edicoes/x.json"), "edicoes[0].arquivo", None)
        self.planta(lambda i: i["edicoes"][0].update(texto="2026-11-04.md"), "edicoes[0].texto", None)
        self.planta(lambda i: i["edicoes"][0].update(data="04/11"), "edicoes[0].data", None)
        self.planta(lambda i: i["edicoes"][0].update(estado="pronta"), "edicoes[0].estado", None)
        self.planta(lambda i: i["edicoes"][0].update(nivel=6), "edicoes[0].nivel", None)
        self.planta(lambda i: i["edicoes"][0].update(niveis=[3, 1]), "edicoes[0].niveis", None)
        self.planta(lambda i: i["edicoes"][0].update(exemplo="sim"), "edicoes[0].exemplo", None)
        self.planta(lambda i: i["edicoes"][0].update(corrigida_em=["amanhã"]), "edicoes[0].corrigida_em", None)
        self.planta(lambda i: i["edicoes"][0].pop("gerada_em"), "edicoes[0].gerada_em", None)
        self.planta(lambda i: i["edicoes"].__setitem__(0, "x"), "edicoes[0]", None)
        self.planta(lambda i: i.update(edicoes={}), "edicoes", None)
        self.planta(lambda i: i.update(versao=2), "versao", None)
        self.planta(lambda i: i.update(atualizado_em="2026-11-01T00:00:00Z"), "atualizado_em", None)
        apoio.acusa(self, valida.confere_indice([]), "INDICE", "edicoes/indice.json")

    def test_arquivos_citados_que_nao_existem(self):
        achados = valida.confere_indice(self.indice, self.edicoes, lambda caminho: not caminho.endswith("2026-11-03.md"))
        self.assertEqual([a.caminho for a in achados], ["edicoes/indice.json:edicoes[1].texto"])


class TestaPelaLinhaDeComando(apoio.ComRaiz):
    def test_dados_congelados(self):
        codigo, linhas = self.valida("--dados")
        self.assertEqual((codigo, linhas[-1]), (0, "OK 0 erros, 0 avisos"), "\n".join(linhas))
        self.assertEqual(linhas[:-1], [])

    def test_defeito_em_cada_arquivo(self):
        self.muda("dados/veiculos.json", lambda o: (o.update(revisado_em="ontem"), o["veiculos"][0].update(sites=[])))
        self.muda("dados/indicadores.json", lambda o: o["indicadores"][1].update(id="brent"))
        self.muda("dados/regua.json", lambda o: o["partidos"][0].update(voto_tipico="B"))
        self.muda("dados/players.json", lambda o: o["players"][0].update(partido="x"))
        self.muda("dados/vetores.json", lambda o: o["vetores"].append({"id": "x"}))
        codigo, linhas = self.valida("--dados")
        self.assertEqual(codigo, 1)
        self.assertRegras(linhas, ["C1", "DADOS", "M1", "M2"])
        self.assertTrue(linhas[-1].startswith("FALHA "))
        for arquivo in apoio.ARQUIVOS_DE_DADOS:
            self.assertTrue([l for l in linhas if l.startswith("ERRO") and " dados/%s.json:" % arquivo in l], arquivo)

    def test_arquivo_que_falta_ou_que_nao_e_json(self):
        os.remove(self.caminho("dados", "vetores.json"))
        self.grava("dados/players.json", '{"versao": 1,\n "players": [,]}')
        self.grava("dados/regua.json", b"\xff\xfe\x00")
        self.grava("dados/indicadores.json", "[1, 2]")
        codigo, linhas = self.valida("--dados")
        self.assertEqual(codigo, 1)
        erros = dict((l.split()[2].rstrip(":"), l) for l in linhas if l.startswith("ERRO"))
        self.assertIn("ERRO ARQUIVO dados/vetores.json: o arquivo não existe", erros["dados/vetores.json"])
        self.assertIn("ERRO ARQUIVO dados/players.json: linha 2, coluna 14: JSON ilegível", erros["dados/players.json"])
        self.assertIn("não é UTF-8", erros["dados/regua.json"])
        self.assertIn("ERRO DADOS dados/indicadores.json: deveria ser um objeto, e é lista", erros["dados/indicadores.json"])
        self.assertFalse([l for l in linhas if self.raiz in l], "o caminho da máquina não aparece na saída")

    def test_arquivo_que_so_traz_null_nao_passa_por_arquivo_ausente(self):
        for nome in apoio.ARQUIVOS_DE_DADOS:
            with open(self.caminho("dados", nome + ".json"), "rb") as arquivo:
                inteiro = arquivo.read()
            self.grava("dados/%s.json" % nome, "null")
            for modo in (("--dados",), ("--tudo",), ("--edicao", apoio.EXEMPLO)):
                codigo, linhas = self.valida(*modo)
                self.assertEqual(codigo, 1, (nome, modo))
                self.assertIn("ERRO DADOS dados/%s.json: deveria ser um objeto, e é null. Recupere o arquivo do git." % nome, linhas)
            self.grava("dados/%s.json" % nome, inteiro)
        self.grava("edicoes/indice.json", "null")
        for modo in (("--dados",), ("--tudo",)):
            codigo, linhas = self.valida(*modo)
            self.assertEqual(codigo, 1, modo)
            self.assertRegras(linhas, ["INDICE"])

    def test_dados_confere_a_forma_do_indice_se_ele_existe(self):
        arquivo = apoio.Arquivo()
        arquivo.publica("2026-11-01")
        arquivo.grava(self.raiz)
        codigo, linhas = self.valida("--dados")
        self.assertEqual(codigo, 0, "\n".join(linhas))
        self.muda("edicoes/indice.json", lambda i: i["edicoes"][0].update(nivel="alto"))
        os.remove(self.caminho("edicoes", "2026-11-01.md"))
        codigo, linhas = self.valida("--dados")
        self.assertEqual(codigo, 1)
        erros = [l for l in linhas if l.startswith("ERRO")]
        self.assertEqual([l.split()[1:3] for l in erros], [["INDICE", "edicoes/indice.json:edicoes[0].texto:"],
                                                             ["INDICE", "edicoes/indice.json:edicoes[0].nivel:"]])
        self.grava("edicoes/indice.json", "{")
        codigo, linhas = self.valida("--dados")
        self.assertEqual(codigo, 1)
        self.assertRegras(linhas, ["ARQUIVO"])


class TestaRobustez(unittest.TestCase):
    """Tipo errado em qualquer profundidade: sempre achados, nunca exceção."""

    TORTOS = (None, True, 0, -1, 3.5, "", "x", [], [None], {}, {"id": []}, [[]], [{"id": 1}])

    def caminhos(self, valor, teto=4):
        """Os caminhos (listas de chaves) de um JSON, até certa profundidade; de cada lista, só os 2 primeiros itens."""
        saida = [[]]
        if teto and isinstance(valor, dict):
            for chave in valor:
                saida += [[chave] + resto for resto in self.caminhos(valor[chave], teto - 1)]
        elif teto and isinstance(valor, list):
            for indice in range(min(len(valor), 2)):
                saida += [[indice] + resto for resto in self.caminhos(valor[indice], teto - 1)]
        return saida

    def test_cada_pedaco_dos_dados_trocado_por_valor_de_tipo_errado(self):
        inteiros, exemplo, feitos, com_edicao = apoio.brutos(), apoio.exemplo(), 0, 0
        for nome in apoio.ARQUIVOS_DE_DADOS:
            for caminho in self.caminhos(inteiros[nome]):
                # perto da raiz, todos os valores tortos; no fundo, um de cada tipo
                for posicao, torto in enumerate(self.TORTOS if len(caminho) <= 2 else self.TORTOS[:9]):
                    objetos = dict(inteiros)
                    if caminho:
                        objetos[nome] = alvo = copy.deepcopy(inteiros[nome])
                        for chave in caminho[:-1]:
                            alvo = alvo[chave]
                        alvo[caminho[-1]] = torto
                    else:
                        objetos[nome] = torto
                    try:
                        dados = apoio.monta(objetos)
                        achados = dados.problemas + valida.confere_dados(dados, indice=torto)
                        if len(caminho) <= 2 and posicao % 3 == 0:   # com os dados tortos, a edição também não derruba
                            com_edicao += 1
                            valida.confere_edicao(exemplo, dados, None, True, tamanho=1)
                            valida.confere_edicao(exemplo, dados, valida.Historico(), False, tamanho=1)
                            valida.confere_trabalho(exemplo, dados, "2026-11-19", {}, "", {})
                            valida.completa(apoio.tira_calculados(exemplo), dados, None, {}, {}, None)
                    except Exception as erro:  # o teste é este: nada pode escapar
                        self.fail("%s%s = %r: %s: %s" % (nome, caminho, torto, type(erro).__name__, erro))
                    for achado in achados:
                        self.assertEqual(len(achado.linha().splitlines()), 1)
                    feitos += 1
        self.assertGreater(feitos, 2500)
        self.assertGreater(com_edicao, 300)

    def test_indice_torto(self):
        arquivo = apoio.Arquivo()
        arquivo.publica("2026-11-01")
        indice = valida.monta_indice(arquivo.edicoes)
        for caminho in self.caminhos(indice, 5):
            for torto in self.TORTOS:
                mexido = copy.deepcopy(indice)
                if caminho:
                    alvo = mexido
                    for chave in caminho[:-1]:
                        alvo = alvo[chave]
                    alvo[caminho[-1]] = torto
                else:
                    mexido = torto
                self.assertIsInstance(valida.confere_indice(mexido, arquivo.edicoes, lambda c: True), list)
                self.assertIsInstance(valida.confere_indice(mexido), list)


if __name__ == "__main__":
    unittest.main()
