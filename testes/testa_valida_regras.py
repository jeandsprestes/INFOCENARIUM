#!/usr/bin/env python3
"""Testes do valida.py: as regras R da edição (ESQUEMA, seção 10), uma a uma.

Para cada regra, um defeito plantado na edição de exemplo tem de ser acusado com o código certo, e um
valor no limite permitido tem de passar. Os 41 casos da conferência da fase 1 estão na tabela OS_41, com o
mesmo nome, e voltam espalhados pelas regras, ao lado dos casos novos.
As regras de histórico (H), de crescimento (G), de dados (M, C) e da pasta de trabalho (T) têm arquivo próprio.

Rodar da raiz do repositório: python3 -B testes/testa_valida_regras.py
"""
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "valida"))

import apoio  # noqa: E402
from apoio import valida  # noqa: E402

DIA = apoio.DIA_DO_EXEMPLO


def confere(edicao, **nomeados):
    nomeados.setdefault("tamanho", 40000)
    return valida.confere_edicao(edicao, nomeados.pop("dados", None) or apoio.dados(), **nomeados)


def P(e, i):
    return e["principais"][i]


def R(e, i):
    return e["radar"][i]


def D(e, i):
    return e["alerta"]["dominios"][i]


def fonte(veiculo, slug, dia=DIA, **mais):
    nova = {"veiculo": veiculo, "titulo": "[EXEMPLO] Título fictício", "url": "https://exemplo.invalid/%s/%s" % (veiculo, slug),
            "publicado_em": dia}
    nova.update(mais)
    return valida.normaliza({"principais": [{"fontes": [nova]}]})["principais"][0]["fontes"][0]


class Regra(unittest.TestCase):
    """Base: planta um defeito no exemplo e exige a regra; ou mexe no exemplo e exige que passe."""

    def planta(self, regra, muda, caminho=None, **nomeados):
        edicao = apoio.exemplo()
        muda(edicao)
        return apoio.acusa(self, confere(edicao, **nomeados), regra, caminho)

    def passa(self, muda=None, refaz=False, **nomeados):
        edicao = apoio.exemplo()
        if muda is not None:
            muda(edicao)
        if refaz:
            edicao = apoio.refaz(edicao, nomeados.get("dados"))
        apoio.limpo(self, confere(edicao, **nomeados))
        return edicao


class TestaExemplo(Regra):
    def test_o_exemplo_passa_inteiro(self):
        achados = confere(apoio.exemplo(), tamanho=os.path.getsize(apoio.EXEMPLO))
        self.assertEqual(achados, [], apoio.linhas(achados))

    def test_o_exemplo_passa_tambem_como_edicao_de_arquivo(self):
        self.assertEqual(confere(apoio.exemplo(), do_dia=False), [])

    def test_cada_erro_traz_regra_caminho_problema_e_conserto(self):
        def muda(e):
            R(e, 3)["confianca"] = "alta"
        achado = self.planta("R08", muda, "radar[3].confianca")
        self.assertEqual(achado.linha(), "ERRO R08 radar[3].confianca: é 'alta', o teto pelas fontes é 'media'. "
                         "Troque para 'media' ou acrescente fonte do outro campo.")
        self.assertEqual(dict(achado.objeto()), {"regra": "R08", "caminho": "radar[3].confianca",
                                                 "mensagem": achado.mensagem})

    def test_toda_mensagem_tem_uma_linha_e_diz_o_que_fazer(self):
        def muda(e):
            P(e, 0)["fato"] = "linha um\nlinha dois " + chr(0x2028) + " três"
            P(e, 0)["titulo"] = 7
            R(e, 0)["categoria"] = "a\nb"
            e["estado"] = ["completa"]
        edicao = apoio.exemplo()
        muda(edicao)
        achados = confere(edicao)
        self.assertTrue(achados)
        for achado in achados:
            self.assertEqual(len(achado.linha().splitlines()), 1, repr(achado.linha()))
            self.assertRegex(achado.linha(), r"^ERRO [A-Z]+[0-9]*[a-f]? \S+: .+[.?!)]$")


class TestaR00(Regra):
    """Estrutura: tipo certo, campo obrigatório presente, nenhum campo desconhecido, valor dentro da lista."""

    def test_campo_desconhecido(self):
        achado = self.planta("R00", lambda e: e.update(extra=1), "edicao")
        self.assertIn("'extra'", achado.mensagem)
        achado = self.planta("R00", lambda e: P(e, 0).update(titulos="x"), "principais[0]")
        self.assertIn("Você quis dizer 'titulo'?", achado.mensagem)

    def test_campo_obrigatorio_que_falta(self):
        self.planta("R00", lambda e: e.pop("resumo"), "resumo")
        self.planta("R00", lambda e: P(e, 1).pop("fato"), "principais[1].fato")
        self.planta("R00", lambda e: D(e, 2).pop("leitura"), "alerta.dominios[2].leitura")
        achado = self.planta("R00", lambda e: D(e, 2).pop("nivel"), "alerta.dominios[2].nivel")
        self.assertIn("publica.py", achado.mensagem)

    def test_tipo_errado(self):
        self.planta("R00", lambda e: e.update(principais={}), "principais")
        self.planta("R00", lambda e: P(e, 0).update(titulo=12), "principais[0].titulo")
        self.planta("R00", lambda e: e.update(exemplo="sim"), "exemplo")
        self.planta("R00", lambda e: e["bastidores"].update(minutos="24"), "bastidores.minutos")
        self.planta("R00", lambda e: e["bastidores"].update(minutos=24.0), "bastidores.minutos")
        self.planta("R00", lambda e: e["bastidores"].update(buscas=-1), "bastidores.buscas")
        self.planta("R00", lambda e: P(e, 0)["placar"][0].update(forca=True), "principais[0].placar[0].forca")
        self.planta("R00", lambda e: e.update(alerta=[]), "alerta")
        self.planta("R00", lambda e: R(e, 0).update(ataque=[R(e, 0)["ataque"]]), "radar[0].ataque")

    def test_valor_fora_da_lista(self):
        self.planta("R00", lambda e: e.update(estado="rascunho"), "estado")
        self.planta("R00", lambda e: P(e, 0).update(categoria="esporte"), "principais[0].categoria")
        self.planta("R00", lambda e: P(e, 0).update(confianca="baixa"), "principais[0].confianca")
        self.planta("R00", lambda e: P(e, 0)["placar"][0].update(efeito="empata"), "placar[0].efeito")
        self.planta("R00", lambda e: P(e, 0)["placar"][0].update(evidencia="boato"), "placar[0].evidencia")
        self.planta("R00", lambda e: P(e, 0)["placar"][0].update(forca=4), "placar[0].forca")
        self.planta("R00", lambda e: P(e, 0)["eixo"].update(sentido="verde"), "eixo.sentido")
        self.planta("R00", lambda e: P(e, 0)["eixo"].update(tema="pandemia_inicio"), "eixo.tema")
        self.planta("R00", lambda e: e["bastidores"].update(modo="manual"), "bastidores.modo")
        self.planta("R00", lambda e: e["respostas"][2].update(resposta="talvez"), "respostas[2].resposta")
        self.planta("R00", lambda e: D(e, 0).update(tendencia="caindo"), "alerta.dominios[0].tendencia")
        self.planta("R00", lambda e: e["novos_players"][0].update(time="reforma"), "novos_players[0].time")

    def test_raiz(self):
        self.planta("R00", lambda e: e.update(versao=2), "versao")
        self.planta("R00", lambda e: e.update(data="19/11/2026"), "data")
        self.planta("R00", lambda e: e.update(data="2026-02-30"), "data")
        self.planta("R00", lambda e: e.update(gerada_em="2026-11-19 21:14"), "gerada_em")
        self.planta("R00", lambda e: e.update(gerada_em="2026-11-21T00:00:00Z"), "gerada_em")
        self.planta("R00", lambda e: e.update(gerada_em="2026-11-18T23:59:59Z"), "gerada_em")
        self.passa(lambda e: e.update(gerada_em="2026-11-20T02:59:59Z"))  # o dia seguinte, em UTC, ainda vale
        achados = confere([apoio.exemplo()])
        apoio.acusa(self, achados, "R00", "edicao")

    def test_contagens_das_tabelas(self):
        def cinco_ataques(e):
            P(e, 0)["ataques"] += [dict(P(e, 0)["ataques"][0]), dict(P(e, 0)["ataques"][1])]
        self.planta("R00", cinco_ataques, "principais[0].ataques")
        self.planta("R00", lambda e: P(e, 0).update(ataques=P(e, 0)["ataques"][:1]), "principais[0].ataques")
        self.planta("R00", lambda e: P(e, 0).update(na_pratica=[]), "principais[0].na_pratica")
        self.planta("R00", lambda e: P(e, 0).update(vigiar=["A?" + " 22/11?"] * 4), "principais[0].vigiar")
        self.planta("R00", lambda e: P(e, 0)["fontes"].extend(fonte("bbc", "x%d" % n) for n in range(3)), "principais[0].fontes")
        self.planta("R00", lambda e: R(e, 0)["fontes"].extend(fonte("bbc", "x%d" % n) for n in range(3)), "radar[0].fontes")
        self.planta("R00", lambda e: e["bastidores"].update(candidatos=e["bastidores"]["candidatos"] * 6), "bastidores.candidatos")
        self.planta("R00", lambda e: e.update(errata=e["errata"] * 3), "errata")
        self.planta("R00", lambda e: e.update(respostas=e["respostas"] * 2), "respostas")
        self.planta("R00", lambda e: P(e, 0)["dominios"].append("energia"), "principais[0].dominios[2]")
        self.planta("R00", lambda e: R(e, 1)["vetores"].append(dict(R(e, 1)["vetores"][0])), "radar[1].vetores")

    def test_dominios_do_alerta_exatos_e_em_ordem(self):
        def troca(e):
            e["alerta"]["dominios"][0], e["alerta"]["dominios"][1] = D(e, 1), D(e, 0)
        self.planta("R00", troca, "alerta.dominios")
        self.planta("R00", lambda e: e["alerta"]["dominios"].pop(), "alerta.dominios")

    def test_gatilhos_de_evento_no_maximo_quatro(self):
        def cinco(e):
            D(e, 4)["gatilhos"] = [dict(D(e, 4)["gatilhos"][0]) for _ in range(5)]
        self.planta("R00", cinco, "alerta.dominios[4].gatilhos")
        self.passa(lambda e: D(e, 4).update(gatilhos=[dict(D(e, 4)["gatilhos"][0]) for _ in range(4)]))

    def test_textos_de_forma_fixa(self):
        self.planta("R00", lambda e: P(e, 0)["nao_confirmado"].__setitem__(0, "Dizem que os drones partiram de outro país."),
                    "principais[0].nao_confirmado[0]")
        self.planta("R00", lambda e: e["bastidores"].update(veiculos_sugeridos=["Gazeta de Amostra"]), "veiculos_sugeridos[0]")
        self.planta("R00", lambda e: e["bastidores"]["candidatos"][0].update(id="Reino de Amostra"), "candidatos[0].id")
        self.planta("R00", lambda e: e["errata"][0].update(item="x9"), "errata[0].item")
        self.planta("R00", lambda e: P(e, 1).update(continuacao_de="18/11, p2"), "principais[1].continuacao_de")
        self.planta("R00", lambda e: e["novos_players"][0].update(id="República"), "novos_players[0].id")

    def test_indicadores(self):
        self.planta("R00", lambda e: e["indicadores"][0].update(valor=0), "indicadores[0].valor")
        self.planta("R00", lambda e: e["indicadores"][0].update(valor="78,4"), "indicadores[0].valor")
        self.planta("R00", lambda e: e["indicadores"][1].update(variacao_pct=1.14), "indicadores[1].variacao_pct")
        self.planta("R00", lambda e: e["indicadores"][2].update(defasado=False), "indicadores[2].defasado")
        self.planta("R00", lambda e: e["indicadores"][2].update(data=DIA), "indicadores[2].data")
        self.planta("R00", lambda e: e["indicadores"][1].update(data="2026-11-20"), "indicadores[1].data")
        self.planta("R00", lambda e: e["indicadores"][1].update(data=None), "indicadores[1].data")
        self.planta("R00", lambda e: e["indicadores"][1].update(fonte="Yahoo"), "indicadores[1].fonte")
        self.planta("R00", lambda e: e["indicadores"][1].pop("confirmado"), "indicadores[1].confirmado")

    def test_defasado_segue_a_data_da_cotacao_so_na_edicao_do_dia(self):
        def velha_sem_marca(e):  # WTI com cotação de 5 dias antes e defasado: false
            e["indicadores"][1].update(data="2026-11-14")
        self.planta("R00", velha_sem_marca, "indicadores[1].defasado")
        self.planta("R00", lambda e: e["indicadores"][1].update(defasado=True), "indicadores[1].defasado")
        self.passa(lambda e: e["indicadores"][1].update(data="2026-11-15"))  # 4 dias: ainda vale
        self.passa(lambda e: e["indicadores"][6].update(data="2026-09-18"))  # mensal: 62 dias ainda vale
        self.planta("R00", lambda e: e["indicadores"][6].update(data="2026-09-17"), "indicadores[6].defasado")
        self.passa(velha_sem_marca, do_dia=False)  # edição de arquivo não é medida contra o catálogo de hoje


class TestaR01(Regra):
    def test_ids_em_ordem_e_sem_repetir(self):
        self.planta("R01", lambda e: P(e, 1).update(id="p3"), "principais[1].id")
        self.planta("R01", lambda e: R(e, 0).update(id="r0"), "radar[0].id")

        def pula(e):
            for indice, item in enumerate(e["radar"]):
                item["id"] = "r%d" % (indice + 2)
        self.planta("R01", pula, "radar[0].id")

    def test_data_igual_ao_nome_do_arquivo(self):
        achados = confere(apoio.exemplo(), data_do_arquivo="2026-11-20")
        achado = apoio.acusa(self, achados, "R01", "data")
        self.assertIn("2026-11-20.json", achado.mensagem)
        apoio.limpo(self, confere(apoio.exemplo(), data_do_arquivo=DIA))


class TestaR02(Regra):
    def test_alvo_desconhecido(self):
        self.planta("R02", lambda e: R(e, 4)["ataque"].update(alvo="ninguem"), "radar[4].ataque.alvo")

    def test_o_player_novo_do_dia_vale_como_alvo(self):
        self.assertEqual(P(apoio.exemplo(), 0)["ataques"][0]["alvo"], "republica_exemplo")
        self.passa()
        self.planta("R02", lambda e: e.update(novos_players=[]), "principais[0].ataques[0].alvo")

    def test_partido_tema_e_dominio_da_regua(self):
        self.planta("R02", lambda e: P(e, 0)["placar"][0].update(partido="eixo"), "placar[0].partido")
        self.planta("R02", lambda e: P(e, 0)["vetores"][0].update(para="direita"), "vetores[0].para")
        self.planta("R02", lambda e: P(e, 0)["eixo"].update(tema="economia"), "eixo.tema")
        self.planta("R02", lambda e: P(e, 0)["dominios"].append("agua"), "principais[0].dominios[2]")
        self.planta("R02", lambda e: e["indicadores"][0].update(dominio="agua"), "indicadores[0].dominio")
        self.planta("R02", lambda e: e["placar_do_dia"][0].update(partido="eixo"), "placar_do_dia[0].partido")
        self.planta("R02", lambda e: e["novos_players"][0].update(partido="eixo"), "novos_players[0].partido")
        self.planta("R02", lambda e: P(e, 0)["ataques"][0].update(lado="eixo"), "ataques[0].lado")

    def test_veiculo_do_mapa_so_na_edicao_do_dia(self):
        def some_do_mapa(e):
            P(e, 2)["fontes"][0]["veiculo"] = "agencia_que_saiu_do_mapa"
        achado = self.planta("R02", some_do_mapa, "principais[2].fontes[0].veiculo")
        self.assertIn("mapa.txt", achado.mensagem)
        self.passa(some_do_mapa, do_dia=False)
        self.planta("R02", lambda e: R(e, 4)["ataque"].update(veiculo="wsjj"), "radar[4].ataque.veiculo")

    def test_indicador_do_catalogo_sem_repetir(self):
        def fora(e):
            e["indicadores"][11]["id"] = "cobre"
        self.planta("R02", fora, "indicadores[11].id")
        self.passa(fora, do_dia=False)
        self.planta("R02", lambda e: e["indicadores"][1].update(id="brent"), "indicadores[1].id")
        self.planta("R02", lambda e: e["indicadores"][1].update(id="brent"), "indicadores[1].id", do_dia=False)


class TestaR03(Regra):
    def test_lado_igual_ao_do_mapa(self):
        achado = self.planta("R03", lambda e: P(e, 0)["ataques"][0].update(lado="soberanistas"), "ataques[0].lado")
        self.assertIn("o mapa diz 'ordem_global'", achado.mensagem)

    def test_principal_com_atirador_de_lado_incerto(self):
        def muda(e):
            a = P(e, 1)["ataques"][0]
            a["veiculo"], a["lado"] = "techcrunch", "bancada_talento"
            a["url"] = "https://exemplo.invalid/techcrunch/x"
            P(e, 1)["fontes"].append(fonte("techcrunch", "x"))
        self.planta("R03", muda, "principais[1].ataques[0].veiculo")

    def test_no_radar_o_lado_incerto_pode_atirar(self):
        self.assertEqual(apoio.dados().mapa["the_verge"]["lado_confianca"], "baixa")
        self.assertEqual(R(apoio.exemplo(), 2)["ataque"]["veiculo"], "the_verge")
        self.passa()


class TestaR04(Regra):
    def test_alvo_nome_se_e_so_se_o_alvo_e_outro(self):
        self.planta("R04", lambda e: P(e, 0)["ataques"][2].pop("alvo_nome"), "ataques[2].alvo_nome")
        self.planta("R04", lambda e: P(e, 0)["ataques"][1].update(alvo_nome="União Europeia"), "ataques[1].alvo_nome")

    def test_nome_da_fonte_se_e_so_se_o_veiculo_e_outro(self):
        self.planta("R04", lambda e: P(e, 0)["fontes"][5].pop("nome"), "fontes[5].nome")
        self.planta("R04", lambda e: P(e, 0)["fontes"][0].update(nome="Reuters"), "fontes[0].nome")

    def test_veiculo_fora_do_mapa_nunca_atira(self):
        self.planta("R04", lambda e: R(e, 4)["ataque"].update(veiculo="outro"), "radar[4].ataque.veiculo")

    def test_alvo_nenhum_vale(self):
        self.assertEqual(R(apoio.exemplo(), 4)["ataque"]["alvo"], "nenhum")
        self.passa()


class TestaR05(Regra):
    def test_url_de_ataque_tem_de_estar_nas_fontes_com_o_mesmo_veiculo(self):
        self.planta("R05", lambda e: P(e, 0)["ataques"][0].update(url="https://exemplo.invalid/nyt/outra"), "ataques[0].url")
        self.planta("R05", lambda e: P(e, 0)["ataques"][0].update(url=P(e, 0)["fontes"][0]["url"]), "ataques[0].url")

    def test_url_de_vetor_tem_de_estar_nas_fontes(self):
        self.planta("R05", lambda e: P(e, 0)["vetores"][0].update(url="https://exemplo.invalid/x/y"), "vetores[0].url")

    def test_fonte_repetida_no_item(self):
        self.planta("R05", lambda e: P(e, 2)["fontes"][1].update(url=P(e, 2)["fontes"][0]["url"]), "fontes[1].url")
        self.planta("R05", lambda e: P(e, 2)["fontes"][1].update(
            url=P(e, 2)["fontes"][0]["url"].replace("https://", "http://www.") + "/?utm_source=rss#topo"), "fontes[1].url")

    def test_a_comparacao_e_pelo_endereco_limpo(self):
        def muda(e):
            a = P(e, 0)["ataques"][0]
            a["url"] = a["url"].replace("https://", "http://www.") + "/#comentarios"
        self.passa(muda)


class TestaR06(Regra):
    def test_principal_com_menos_de_tres_fontes(self):
        self.planta("R06", lambda e: P(e, 2).update(fontes=P(e, 2)["fontes"][:2]), "principais[2].fontes")

    def test_principal_com_fontes_de_um_partido_so(self):
        def muda(e):
            for f in P(e, 2)["fontes"]:
                f["veiculo"] = "guardian"
        achado = self.planta("R06", muda, "principais[2].fontes")
        self.assertIn("1 partido só (ordem_global)", achado.mensagem)

    def test_principal_sem_fonte_forte(self):
        def muda(e):
            P(e, 2)["fontes"][0]["veiculo"] = "fox_news"   # ap -> fatos media
            P(e, 2)["fontes"][1]["veiculo"] = "rt"         # guardian -> fatos baixa
            P(e, 2)["ataques"][0].update(veiculo="rt", lado="eixo_revisionista")
        achado = self.planta("R06", muda, "principais[2].fontes")
        self.assertIn("fonte forte", achado.mensagem)

    def test_ataques_de_um_partido_so(self):
        def muda(e):
            P(e, 2)["ataques"] = [P(e, 2)["ataques"][0], dict(P(e, 2)["ataques"][0], veiculo="guardian")]
        self.planta("R06", muda, "principais[2].ataques")

    def test_fonte_outro_nao_conta_como_partido(self):
        def muda(e):
            for f in P(e, 1)["fontes"][:3]:
                f["veiculo"] = "wired"
            P(e, 1)["ataques"][0].update(veiculo="wired", lado="ordem_global")
        self.planta("R06", muda, "principais[1].fontes")

    def test_no_limite_passa(self):
        def minimo(e):  # 3 fontes, de 2 partidos (ordem_global e eixo_revisionista), 1 forte, e 2 atiradores
            p = P(e, 2)
            p["fontes"] = p["fontes"][:3]
            p["ataques"] = p["ataques"][:2]
            p["placar"] = p["placar"][:2]
        self.passa(minimo, refaz=True)

    def test_so_vale_para_a_edicao_do_dia(self):
        objetos = apoio.brutos()  # o dono revê o mapa: os quatro veículos da principal p3 passam a um partido só
        for veiculo in objetos["veiculos"]["veiculos"]:
            if veiculo["id"] in ("ap", "tass", "gazeta_do_povo"):
                veiculo["lado"] = "ordem_global"
        revisados = apoio.monta(objetos)
        apoio.acusa(self, confere(apoio.exemplo(), dados=revisados), "R06", "principais[2].fontes")
        apoio.acusa(self, confere(apoio.exemplo(), dados=revisados), "R06", "principais[2].ataques")
        apoio.limpo(self, confere(apoio.exemplo(), dados=revisados, do_dia=False))


class TestaR07(Regra):
    def test_radar_com_2_fontes_do_mesmo_partido_sem_forte(self):
        def muda(e):
            R(e, 2)["fontes"][0]["veiculo"] = "techcrunch"
            R(e, 2)["ataque"].update(veiculo="techcrunch", lado="bancada_talento")
        self.planta("R07", muda, "radar[2].fontes")

    def test_radar_sem_fonte(self):
        self.planta("R07", lambda e: R(e, 4).update(fontes=[]), "radar[4].fontes")

    def test_uma_fonte_forte_basta(self):
        self.assertEqual(len(R(apoio.exemplo(), 4)["fontes"]), 1)
        self.assertEqual(apoio.dados().mapa["wsj"]["fatos"], "alta")
        self.passa()

    def test_duas_fontes_de_partidos_diferentes_bastam(self):
        mapa = apoio.dados().mapa
        self.assertEqual([mapa[f["veiculo"]]["fatos"] for f in R(apoio.exemplo(), 5)["fontes"]], ["media", "media"])
        self.passa()


class TestaR08(Regra):
    def test_radar_com_confianca_alta_e_um_campo_so(self):
        self.planta("R08", lambda e: R(e, 3).update(confianca="alta"), "radar[3].confianca")

    def test_media_sem_forte_e_com_um_partido_so(self):
        def muda(e):
            R(e, 4)["fontes"][0]["veiculo"] = "fox_news"
            R(e, 4)["ataque"].update(veiculo="fox_news", lado="soberanistas")
        achado = self.planta("R08", muda, "radar[4].confianca")
        self.assertIn("o teto pelas fontes é 'baixa'", achado.mensagem)

    def test_alta_com_os_dois_campos_mas_sem_forte(self):
        def muda(e):
            R(e, 5).update(confianca="alta")
            R(e, 5)["fontes"][1]["veiculo"] = "fox_news"      # contestação com contestação não fecha os dois campos
        self.planta("R08", muda, "radar[5].confianca")

    def test_declarar_menos_que_o_teto_pode(self):
        self.assertEqual(valida.teto_de_confianca(apoio.dados(), P(apoio.exemplo(), 2)), "alta")
        self.passa(lambda e: P(e, 2).update(confianca="media"))
        self.assertEqual(valida.teto_de_confianca(apoio.dados(), R(apoio.exemplo(), 3)), "media")
        self.assertEqual(valida.teto_de_confianca(apoio.dados(), {"fontes": [fonte("rt", "x")]}), "baixa")


class TestaR09(Regra):
    def test_janela_da_data_de_publicacao(self):
        self.planta("R09", lambda e: P(e, 2)["fontes"][0].update(publicado_em="2026-11-21"), "fontes[0].publicado_em")
        self.passa(lambda e: P(e, 2)["fontes"][0].update(publicado_em="2026-11-20"))
        self.planta("R09", lambda e: P(e, 2)["fontes"][0].update(publicado_em="2026-11-16"), "fontes[0].publicado_em")
        self.passa(lambda e: P(e, 2)["fontes"][0].update(publicado_em="2026-11-17"))

    def test_fonte_primaria_pode_ser_antiga_mas_nao_do_futuro(self):
        self.passa(lambda e: P(e, 0)["fontes"][5].update(publicado_em="2025-03-01"))
        self.planta("R09", lambda e: P(e, 0)["fontes"][5].update(publicado_em="2026-11-21"), "fontes[5].publicado_em")


class TestaR10(Regra):
    def test_narrativa_so_com_forca_1(self):
        self.planta("R10", lambda e: P(e, 0)["placar"][2].update(forca=2), "principais[0].placar[2].forca")

    def test_uma_linha_por_partido_no_item(self):
        self.planta("R10", lambda e: P(e, 0)["placar"][1].update(partido="eixo_revisionista"), "placar[1].partido")

    def test_placar_vazio_sem_sem_placar(self):
        self.planta("R10", lambda e: R(e, 4).pop("sem_placar"), "radar[4].sem_placar")

    def test_sem_placar_com_placar_cheio(self):
        self.planta("R10", lambda e: R(e, 3).update(sem_placar="Texto fictício. Ninguém ganha ainda."), "radar[3].sem_placar")

    def test_item_de_confianca_baixa_com_placar(self):
        def muda(e):
            del R(e, 2)["sem_placar"]
            R(e, 2)["placar"] = [{"partido": "bancada_talento", "efeito": "ganha", "forca": 1,
                                  "evidencia": "narrativa", "porque": "Texto fictício. x"}]
        self.planta("R10", muda, "radar[2].placar")

    def test_radar_com_forca_3_sem_fonte_forte(self):
        def muda(e):
            R(e, 5)["placar"][0]["forca"] = 3
        self.planta("R10", muda, "radar[5].placar[0].forca")
        edicao = apoio.exemplo()
        muda(edicao)
        self.assertNotIn("R10", apoio.regras(confere(edicao, do_dia=False)))  # o mapa muda: só na edição do dia

    def test_radar_com_forca_3_e_fonte_forte_passa(self):
        self.passa(lambda e: R(e, 3)["placar"][0].update(forca=3), refaz=True)


class TestaR11(Regra):
    def test_vetor_provado_por_fonte_que_nao_e_forte(self):
        self.planta("R11", lambda e: P(e, 0)["vetores"][0].update(url=P(e, 0)["fontes"][2]["url"]), "vetores[0].url")

    def test_destino_igual_ao_partido_do_player_ou_independentes(self):
        self.planta("R11", lambda e: P(e, 0)["vetores"][0].update(para="centro_atlantico"), "vetores[0].para")
        self.planta("R11", lambda e: P(e, 0)["vetores"][0].update(para="independentes"), "vetores[0].para")

    def test_player_que_nao_existe_ou_que_e_o_novo_do_dia(self):
        self.planta("R11", lambda e: P(e, 0)["vetores"][0].update(player="uniao_europeia"), "vetores[0].player")
        achado = self.planta("R11", lambda e: P(e, 0)["vetores"][0].update(player="republica_exemplo"), "vetores[0].player")
        self.assertIn("player novo desta edição", achado.mensagem)

    def test_vetor_para_partido_que_vota_igual_no_tema(self):
        self.planta("R11", lambda e: P(e, 0)["vetores"][0].update(para="ordem_global"), "vetores[0].para")

    def test_vetor_com_tema_historico(self):
        self.planta("R11", lambda e: P(e, 0)["vetores"][0].update(tema="pandemia_inicio"), "vetores[0].tema")

    def test_destino_sem_posicao_firme_no_tema(self):
        self.assertEqual(apoio.dados().voto["bancada_talento"]["clima"], "Y")
        self.planta("R11", lambda e: P(e, 0)["vetores"][0].update(para="bancada_talento"), "vetores[0].para")

    def test_no_maximo_dois_vetores_e_um_por_par(self):
        def terceiro(e):
            P(e, 0)["vetores"].append(dict(P(e, 0)["vetores"][0], para="eixo_revisionista"))
        achado = self.planta("R11", terceiro, "radar[1].vetores[0]")
        self.assertIn("3º vetor da edição", achado.mensagem)

        def repetido(e):
            R(e, 1)["vetores"] = []
            P(e, 0)["vetores"].append(dict(P(e, 0)["vetores"][0]))
        achado = self.planta("R11", repetido, "principais[0].vetores[1]")
        self.assertIn("repete o par", achado.mensagem)

    def test_item_com_fontes_de_um_partido_so(self):
        def muda(e):
            R(e, 1)["fontes"] = [R(e, 1)["fontes"][2]]
            R(e, 1)["ataque"].update(veiculo="google_deepmind", lado="bancada_talento", url=R(e, 1)["fontes"][0]["url"])
        self.planta("R11", muda, "radar[1].vetores[0]")

    def test_um_vetor_por_player_em_cada_item(self):
        """Achado do publica.py na fase 2b: o id do registro é data, item e player (ESQUEMA, seção 12). Dois
        vetores do mesmo player no mesmo item, para destinos diferentes, dariam o mesmo id."""
        def dobra(e):
            R(e, 1)["vetores"] = []
            P(e, 0)["vetores"].append(dict(P(e, 0)["vetores"][0], para="eixo_revisionista", tema="ordem"))
        achado = self.planta("R11", dobra, "principais[0].vetores[1].player")
        self.assertIn("já tem outro vetor neste item (principais[0].vetores[0])", achado.mensagem)
        edicao = apoio.exemplo()
        dobra(edicao)
        self.assertEqual(len([a for a in confere(edicao) if a.regra == "R11"]), 1)   # uma linha só

    def test_tema_ordem_nao_olha_voto_tipico(self):
        self.passa(lambda e: P(e, 0)["vetores"][0].update(tema="ordem", para="ordem_global"))

    def test_player_independente_so_precisa_de_destino_firme(self):
        self.assertEqual(apoio.dados().players["modi"]["partido"], "independentes")
        self.passa(lambda e: P(e, 0)["vetores"][0].update(player="modi", para="soberanistas"))
        self.planta("R11", lambda e: P(e, 0)["vetores"][0].update(player="modi", para="bancada_talento"), "vetores[0].para")

    def test_exigencias_do_mapa_so_na_edicao_do_dia(self):
        self.passa(lambda e: P(e, 0)["vetores"][0].update(url=P(e, 0)["fontes"][2]["url"]), do_dia=False)


class TestaR12(Regra):
    def test_narrativa_somada_ao_saldo(self):
        def muda(e):
            for linha in e["placar_do_dia"]:
                if linha["partido"] == "soberanistas":
                    linha["saldo"] = 2
        achado = self.planta("R12", muda, "placar_do_dia[2].saldo")
        self.assertIn("é 2; a soma das forças de hoje dá 0", achado.mensagem)

    def test_narrativa_errada(self):
        self.planta("R12", lambda e: e["placar_do_dia"][0].update(narrativa=0), "placar_do_dia[0].narrativa")

    def test_partido_que_falta_ou_que_sobra(self):
        self.planta("R12", lambda e: e["placar_do_dia"].pop(1), "placar_do_dia")

        def sobra(e):
            R(e, 5)["placar"] = [R(e, 5)["placar"][1]]
        self.planta("R12", sobra, "placar_do_dia[1].partido")
        self.planta("R12", lambda e: e["placar_do_dia"].append(dict(e["placar_do_dia"][0])), "placar_do_dia[7].partido")

    def test_fora_de_ordem(self):
        def muda(e):
            e["placar_do_dia"][0], e["placar_do_dia"][1] = e["placar_do_dia"][1], e["placar_do_dia"][0]
        self.planta("R12", muda, "placar_do_dia")

    def test_empate_segue_a_ordem_da_regua(self):
        calculado = valida.calcula_placar_do_dia(apoio.dados(), apoio.exemplo())
        self.assertEqual([(l["partido"], l["saldo"]) for l in calculado][-2:],
                         [("centro_atlantico", -2), ("bancada_talento", -2)])

    def test_partido_so_com_narrativa_aparece_com_saldo_zero(self):
        linha = [l for l in apoio.exemplo()["placar_do_dia"] if l["partido"] == "soberanistas"][0]
        self.assertEqual((linha["saldo"], linha["narrativa"]), (0, 2))
        self.passa()

    def test_veiculos_consultados(self):
        achado = self.planta("R12", lambda e: e["bastidores"].update(veiculos_consultados=20), "bastidores.veiculos_consultados")
        self.assertIn("citam 19", achado.mensagem)


class TestaR13(Regra):
    """Sem histórico à mão vale a saída da regra H1; a conta contra as edições de verdade está no teste de histórico."""

    def test_nivel_abaixo_do_gatilho_de_hoje(self):
        def muda(e):
            D(e, 0)["nivel"] = 2
        achado = self.planta("R13", muda, "alerta.dominios[0].nivel")
        self.assertIn("é 2, e o maior gatilho de hoje é de nível 3", achado.mensagem)

    def test_nivel_acima_sem_desde_anterior(self):
        self.planta("R13", lambda e: D(e, 1).update(nivel=2, desde=DIA), "alerta.dominios[1].nivel")

    def test_nivel_mantido_com_desde_anterior_passa(self):
        cambio = D(apoio.exemplo(), 2)
        self.assertEqual((cambio["nivel"], cambio["gatilhos"], cambio["desde"]), (2, [], "2026-11-17"))
        self.passa()


class TestaR13a(Regra):
    def test_criterio_que_nao_existe_na_regua(self):
        self.planta("R13a", lambda e: D(e, 0)["gatilhos"][1].update(criterio="energia.9"), "gatilhos[1].criterio")
        self.planta("R13a", lambda e: D(e, 0)["gatilhos"][1].update(criterio="energia.1"), "gatilhos[1].criterio")
        self.planta("R13a", lambda e: D(e, 0)["gatilhos"][1].update(criterio="energia 3"), "gatilhos[1].criterio")

    def test_criterio_de_outro_dominio(self):
        self.planta("R13a", lambda e: D(e, 0)["gatilhos"][1].update(criterio="conflito.3"), "gatilhos[1].criterio")

    def test_ref_que_nao_existe_na_edicao(self):
        self.planta("R13a", lambda e: D(e, 0)["gatilhos"][1].update(ref="p9"), "gatilhos[1].ref")
        self.planta("R13a", lambda e: D(e, 0)["gatilhos"][1].update(ref="cobre"), "gatilhos[1].ref")


class TestaR13b(Regra):
    def test_gatilho_de_nivel_3_provado_por_radar(self):
        def muda(e):
            g = D(e, 3)["gatilhos"][0]
            g["criterio"] = "suprimentos.3"
            del g["excecao"]
            D(e, 3)["nivel"] = 3
        achado = self.planta("R13b", muda, "alerta.dominios[3].gatilhos[0].ref")
        self.assertEqual(achado.mensagem, "nível 3 exige principal, e 'r4' é do radar. Baixe o critério para o "
                         "nível 2 ou tire o gatilho.")

    def test_gatilho_provado_por_item_de_confianca_baixa(self):
        self.planta("R13b", lambda e: D(e, 3)["gatilhos"][0].update(ref="r3"), "gatilhos[0].ref")

    def test_nivel_4_pede_principal_de_confianca_alta(self):
        def muda(e):
            D(e, 4)["gatilhos"][0].update(criterio="conflito.4", ref="p2")
            D(e, 4)["nivel"] = e["alerta"]["nivel"] = 4
        self.planta("R13b", muda, "alerta.dominios[4].gatilhos[0].ref")

    def test_nivel_5_pede_fonte_primaria(self):
        def muda(e):
            D(e, 4)["gatilhos"][0].update(criterio="conflito.5", ref="p3")
            D(e, 4)["nivel"] = e["alerta"]["nivel"] = 5
        achado = self.planta("R13b", muda, "alerta.dominios[4].gatilhos[0].ref")
        self.assertIn("fonte primária", achado.mensagem)

    def test_nivel_5_do_brasil_pede_fonte_primaria_de_site_oficial_do_brasil(self):
        def muda(e):
            D(e, 0)["gatilhos"][1].update(criterio="energia.5")
            D(e, 0)["nivel"] = e["alerta"]["nivel"] = 5
        achado = self.planta("R13b", muda, "alerta.dominios[0].gatilhos[1].ref")
        self.assertIn("gov.br", achado.mensagem)

        def com_documento_do_brasil(e):
            muda(e)
            P(e, 0)["fontes"].append(fonte("outro", "x", nome="Agência fictícia do governo", primaria=True,
                                           url="https://www.gov.br/exemplo/racionamento"))
        self.passa(com_documento_do_brasil)

    def test_nivel_5_de_conflito_aceita_primaria_de_qualquer_autoridade(self):
        def muda(e):
            D(e, 4)["gatilhos"][0].update(criterio="conflito.5")
            D(e, 4)["nivel"] = e["alerta"]["nivel"] = 5
        self.passa(muda)

    def test_nivel_2_aceita_radar_e_nivel_3_aceita_principal_de_confianca_media(self):
        self.passa(lambda e: P(e, 0).update(confianca="media"))


class TestaR13c(Regra):
    def test_alta_forte_de_preco_sem_confirmacao_declarada_como_nivel_3(self):
        def muda(e):
            e["indicadores"][0]["variacao_7d_pct"] = 10.4
            D(e, 0)["gatilhos"][0]["criterio"] = "energia.3"
        self.planta("R13c", muda, "alerta.dominios[0].gatilhos[0].criterio")

    def test_alta_forte_de_preco_sem_confirmacao_declarada_como_nivel_2(self):
        self.passa(lambda e: e["indicadores"][0].update(variacao_7d_pct=10.4))

    def test_alta_forte_de_preco_confirmada_pede_nivel_3(self):
        self.planta("R13c", lambda e: e["indicadores"][0].update(variacao_7d_pct=10.4, confirmado=True),
                    "alerta.dominios[0].gatilhos[0].criterio")

    def test_alta_do_dolar_no_dia_com_cotacao_de_outro_dia_nao_vale(self):
        self.passa(lambda e: e["indicadores"][7].update(variacao_pct=1.8, data="2026-11-18"))

    def test_alta_do_dolar_no_dia_com_cotacao_do_dia_pede_gatilho(self):
        achado = self.planta("R13c", lambda e: e["indicadores"][7].update(variacao_pct=1.8), "alerta.dominios[2].gatilhos")
        self.assertIn("'usd_brl'", achado.mensagem)
        self.assertIn("'cambio.2'", achado.mensagem)

    def test_no_limiar_exato_o_gatilho_vale(self):
        self.assertEqual(valida.calcula_gatilhos_de_preco(apoio.dados(), [dict(apoio.exemplo()["indicadores"][0], variacao_7d_pct=5.0)], DIA)["energia"], {"brent": 2})
        self.assertEqual(valida.calcula_gatilhos_de_preco(apoio.dados(), [dict(apoio.exemplo()["indicadores"][0], variacao_7d_pct=4.9)], DIA)["energia"], {})
        self.passa(lambda e: e["indicadores"][0].update(variacao_7d_pct=5.0))
        self.planta("R13c", lambda e: e["indicadores"][0].update(variacao_7d_pct=4.9), "alerta.dominios[0].gatilhos[0]")

    def test_so_alta_conta_e_indicador_defasado_nao_cumpre(self):
        self.planta("R13c", lambda e: e["indicadores"][0].update(variacao_7d_pct=-12.0), "alerta.dominios[0].gatilhos[0]")
        self.planta("R13c", lambda e: e["indicadores"][0].update(variacao_7d_pct=None), "alerta.dominios[0].gatilhos[0]")
        self.planta("R13c", lambda e: e["indicadores"][0].update(defasado=True, data="2026-11-12"), "alerta.dominios[0].gatilhos[0]")

    def test_gatilho_de_preco_escrito_a_mao(self):
        def muda(e):
            D(e, 2)["gatilhos"] = [{"criterio": "cambio.2", "ref": "usd_brl", "texto": "Texto fictício. O dólar subiu."}]
        self.planta("R13c", muda, "alerta.dominios[2].gatilhos[0]")

    def test_confirmado_so_com_alta_forte(self):
        self.planta("R13c", lambda e: e["indicadores"][0].update(confirmado=True), "indicadores[0].confirmado")

    def test_so_vale_para_a_edicao_do_dia_e_nao_vale_para_a_falha(self):
        self.passa(lambda e: e["indicadores"][7].update(variacao_pct=1.8), do_dia=False)


class TestaR13d(Regra):
    def test_excecao_so_de_nivel_2_ou_3(self):
        def muda(e):
            D(e, 4)["gatilhos"][0].update(criterio="conflito.4", excecao=True)
            D(e, 3)["gatilhos"][0].pop("excecao")
            D(e, 4)["nivel"] = e["alerta"]["nivel"] = 4
        self.planta("R13d", muda, "alerta.dominios[4].gatilhos[0].excecao")

    def test_uma_excecao_por_edicao(self):
        achado = self.planta("R13d", lambda e: D(e, 4)["gatilhos"][0].update(excecao=True), "alerta.dominios[4].gatilhos[0].excecao")
        self.assertIn("alerta.dominios[3].gatilhos[0]", achado.mensagem)

    def test_excecao_so_com_ref_de_item(self):
        def muda(e):
            D(e, 3)["gatilhos"][0].pop("excecao")
            D(e, 0)["gatilhos"][0]["excecao"] = True
        self.planta("R13d", muda, "alerta.dominios[0].gatilhos[0].excecao")

    def test_excecao_de_nivel_3_com_principal_passa(self):
        def muda(e):
            D(e, 3)["gatilhos"][0].pop("excecao")
            D(e, 4)["gatilhos"][0]["excecao"] = True
        self.passa(muda)


class TestaR13e(Regra):
    def test_alivio_sem_historico(self):
        def muda(e):
            D(e, 2)["gatilhos"] = [{"criterio": "cambio.4", "ref": "p1", "texto": "Texto fictício. Acabou.", "alivio": True}]
        self.planta("R13e", muda, "alerta.dominios[2].gatilhos[0].alivio")


class TestaR13f(Regra):
    def test_sem_preco_errada(self):
        achado = self.planta("R13f", lambda e: D(e, 1).update(sem_preco=[]), "alerta.dominios[1].sem_preco")
        self.assertIn("deveria ser ['milho']", achado.mensagem)

    def test_o_que_deixa_o_dominio_cego(self):
        dados, medidos = apoio.dados(), apoio.exemplo()["indicadores"]
        self.assertEqual(valida.calcula_sem_preco(dados, "alimentos", medidos), ["milho"])     # sem variação de 7 dias
        self.assertEqual(valida.calcula_sem_preco(dados, "energia", medidos), [])
        self.assertEqual(valida.calcula_sem_preco(dados, "energia", []), ["brent"])            # falta na lista
        self.assertEqual(valida.calcula_sem_preco(dados, "alimentos", []), ["trigo", "milho", "soja"])  # ordem do catálogo
        self.assertEqual(valida.calcula_sem_preco(dados, "suprimentos", []), [])               # domínio sem critério de preço
        sem_valor = [dict(i, valor=None, defasado=True) if i["id"] == "usd_brl" else i for i in medidos]
        self.assertEqual(valida.calcula_sem_preco(dados, "cambio", sem_valor), ["usd_brl"])
        defasado = [dict(i, defasado=True) if i["id"] == "brent" else i for i in medidos]
        self.assertEqual(valida.calcula_sem_preco(dados, "energia", defasado), ["brent"])

    def test_so_vale_para_a_edicao_do_dia(self):
        self.passa(lambda e: D(e, 1).update(sem_preco=[]), do_dia=False)


class TestaR14(Regra):
    def test_nivel_geral_e_o_maior_dos_dominios(self):
        achado = self.planta("R14", lambda e: e["alerta"].update(nivel=2), "alerta.nivel")
        self.assertIn("é 2; deveria ser o maior nível entre os domínios, que é 3", achado.mensagem)

    def test_desde_nunca_depois_da_data(self):
        self.planta("R14", lambda e: D(e, 1).update(desde="2026-11-20"), "alerta.dominios[1].desde")


class TestaR15(Regra):
    def test_contagens_da_completa(self):
        achado = self.planta("R15", lambda e: e["principais"].pop(), "principais")
        self.assertIn("reduzida", achado.mensagem)
        self.planta("R15", lambda e: e["radar"].pop(), "radar")
        self.planta("R15", lambda e: R(e, 0).update(categoria="geopolitica"), "radar")

        def sem_geopolitica(e):
            for principal in e["principais"]:
                principal["categoria"] = "ia"
        self.planta("R15", sem_geopolitica, "principais")

        def treze(e):
            e["radar"] += [dict(e["radar"][5], id="r%d" % n) for n in range(7, 14)]
        self.planta("R15", treze, "radar")

    def test_reduzida_sem_ia_no_radar(self):
        def muda(e):
            e["estado"] = "reduzida"
            e["radar"] = e["radar"][3:]
            for indice, item in enumerate(e["radar"]):
                item["id"] = "r%d" % (indice + 1)
            D(e, 3)["gatilhos"][0]["ref"] = "r1"
            for linha in e["placar_do_dia"]:
                if linha["partido"] == "ordem_global":
                    linha["narrativa"] = 0
            e["bastidores"]["veiculos_consultados"] = valida.calcula_veiculos_consultados(e)
        self.passa(muda)

    def test_contagens_da_reduzida(self):
        def minima(e):  # 1 principal e 3 no radar
            e["estado"] = "reduzida"
            e["principais"] = e["principais"][:1]
            e["radar"] = e["radar"][3:]
            for indice, item in enumerate(e["radar"]):
                item["id"] = "r%d" % (indice + 1)
            D(e, 3)["gatilhos"][0]["ref"] = "r1"
            sobraram = set(l["partido"] for item in e["principais"] + e["radar"] for l in item["placar"])
            e["placar_do_dia"] = [l for l in e["placar_do_dia"] if l["partido"] in sobraram]
        edicao = self.passa(minima, refaz=True)
        self.assertEqual((len(edicao["principais"]), len(edicao["radar"])), (1, 3))

        def curta(e):
            minima(e)
            e["radar"].pop()
        self.planta("R15", curta, "radar")
        self.planta("R15", lambda e: e.update(estado="reduzida", principais=[]), "principais")

    def test_edicao_de_falha(self):
        arquivo = apoio.Arquivo()
        falha = arquivo.publica_falha("2026-11-10")
        apoio.limpo(self, confere(falha, historico=arquivo.historico()))
        self.assertEqual([d["nivel"] for d in falha["alerta"]["dominios"]], [1] * 5)
        for chave in ("principais", "radar", "placar_do_dia", "novos_players", "errata", "respostas"):
            cheia = dict(falha)
            cheia[chave] = [apoio.exemplo()[chave][0]]
            apoio.acusa(self, confere(cheia, historico=arquivo.historico()), "R15", chave)
        com_gatilho = apoio.copy.deepcopy(falha)
        com_gatilho["alerta"]["dominios"][0]["gatilhos"] = [{"criterio": "energia.2", "ref": "p1", "texto": "Texto fictício."}]
        apoio.acusa(self, confere(com_gatilho, historico=arquivo.historico()), "R15", "alerta.dominios[0].gatilhos")


class TestaR16(Regra):
    def test_errata_e_resposta_de_edicao_anterior(self):
        self.planta("R16", lambda e: e["errata"][0].update(edicao=DIA), "errata[0].edicao")
        self.planta("R16", lambda e: e["respostas"][0].update(edicao="2026-11-20"), "respostas[0].edicao")
        self.passa(lambda e: e["respostas"][0].update(edicao="2026-11-18"))

    def test_continuacao_de_data_anterior(self):
        self.planta("R16", lambda e: P(e, 1).update(continuacao_de="2026-11-19/p2"), "principais[1].continuacao_de")

    def test_continuacao_de_apontando_para_radar(self):
        self.passa(lambda e: P(e, 1).update(continuacao_de="2026-11-18/r12"))

    def test_errata_que_anula_vetor_sem_url(self):
        self.planta("R16", lambda e: e["errata"][1].pop("url"), "errata[1].url")

    def test_resposta_sim_sem_url(self):
        self.planta("R16", lambda e: e["respostas"][0].pop("url"), "respostas[0].url")
        self.planta("R16", lambda e: e["respostas"][1].pop("url"), "respostas[1].url")
        self.assertNotIn("url", apoio.exemplo()["respostas"][2])  # sem_dado dispensa a url

    def test_resposta_so_de_principal(self):
        self.planta("R16", lambda e: e["respostas"][0].update(item="r1"), "respostas[0].item")


class TestaR17(Regra):
    def test_link_em_texto(self):
        self.planta("R17", lambda e: P(e, 0).update(fato=P(e, 0)["fato"] + " Leia em www.exemplo.com."), "principais[0].fato")
        self.planta("R17", lambda e: P(e, 0).update(fato=P(e, 0)["fato"] + " Veja HTTPS://EXEMPLO.INVALID/a."), "principais[0].fato")
        self.planta("R17", lambda e: P(e, 0).update(fato=P(e, 0)["fato"] + " Baixe de ftp://exemplo.invalid/a."), "principais[0].fato")

    def test_http_so_conta_como_endereco_com_dois_pontos(self):
        """ESQUEMA, seção 10, R17: o endereço é `http:` ou `https:` em qualquer caixa. "HTTP 403", o erro que a
        coleta grava e que o agente copia para limites ou para o --motivo, não é endereço."""
        self.passa(lambda e: e["bastidores"].update(limites="Sem rede: o proxy recusou a ligação (HTTP 403)."))
        self.assertEqual(valida.confere_texto("O proxy recusou a ligação (HTTP 403) em todos os feeds."), [])
        self.planta("R17", lambda e: e["bastidores"].update(limites="Leia em http:x."), "bastidores.limites")
        self.planta("R17", lambda e: e["bastidores"].update(limites="Leia em HTTPS:exemplo."), "bastidores.limites")

    def test_marca_de_direcao_de_texto(self):
        """ESQUEMA, seção 10, R17: sem as marcas que reordenam o texto (U+202A a U+202E, U+2066 a U+2069). As
        marcas simples (U+200E, U+200F) e o ZWJ (U+200D) de emoji ficam."""
        achado = self.planta("R17", lambda e: P(e, 0)["fontes"][0].update(titulo="[EXEMPLO] " + chr(0x202E) + "anu"),
                             "principais[0].fontes[0].titulo")
        self.assertIn("marca de direção de texto (código 202e", achado.mensagem)
        for codigo in list(range(0x202A, 0x202F)) + list(range(0x2066, 0x206A)):
            self.assertTrue(valida.confere_texto("Texto" + chr(codigo) + " fictício."), hex(codigo))
        self.planta("R17", lambda e: R(e, 0).update(titulo="[EXEMPLO] Título " + chr(0x2067) + "fictício"), "radar[0].titulo")
        for fica in (chr(0x200E), chr(0x200F), chr(0x1F469) + chr(0x200D) + chr(0x1F52C), chr(0x2065)):
            self.assertEqual(valida.confere_texto("Texto" + fica + " fictício."), [], repr(fica))

    def test_markdown_de_link_em_titulo_de_fonte(self):
        self.planta("R17", lambda e: P(e, 0)["fontes"][0].update(titulo="[EXEMPLO] [Leia](x)"), "fontes[0].titulo")
        self.planta("R17", lambda e: P(e, 0)["fontes"][0].update(titulo="[EXEMPLO] ![foto] aqui"), "fontes[0].titulo")

    def test_sobra_do_modelo(self):
        self.planta("R17", lambda e: R(e, 0).update(sem_placar="160"), "radar[0].sem_placar")

    def test_metade_solta_de_caractere(self):
        """Achado do publica.py na fase 2b: a metade de um emoji (U+D800 a U+DFFF) passa pelo JSON e não se
        grava em UTF-8. É R17, com o campo (ESQUEMA, seção 10, R17)."""
        achado = self.planta("R17", lambda e: R(e, 2).update(fato=R(e, 2)["fato"] + " " + chr(0xD83D)), "radar[2].fato")
        self.assertIn("metade solta", achado.mensagem)
        self.assertIn("d83d", achado.mensagem)
        self.planta("R17", lambda e: P(e, 0)["fontes"][0].update(titulo="[EXEMPLO] " + chr(0xDE00)), "fontes[0].titulo")
        self.assertEqual(valida.confere_texto("Emoji inteiro: " + chr(0x1F600) + "."), [])

    def test_titulo_de_fonte_pode_ser_so_algarismos(self):
        edicao = apoio.completa(apoio.rascunho(DIA))
        edicao["principais"][2]["fontes"][0]["titulo"] = "1984"
        apoio.limpo(self, confere(edicao, historico=valida.Historico()))
        edicao["principais"][2]["titulo"] = "1984"
        apoio.acusa(self, confere(edicao, historico=valida.Historico()), "R17", "principais[2].titulo")

    def test_telefone_cpf_e_email(self):
        self.planta("R17", lambda e: P(e, 0).update(fato=P(e, 0)["fato"] + " Contato: (11) 91234-5678."), "principais[0].fato")
        self.planta("R17", lambda e: P(e, 0).update(fato=P(e, 0)["fato"] + " Ligue +55 11 91234 5678."), "principais[0].fato")
        self.planta("R17", lambda e: P(e, 0).update(fato=P(e, 0)["fato"] + " CPF 123.456.789-09."), "principais[0].fato")
        self.planta("R17", lambda e: P(e, 0).update(fato=P(e, 0)["fato"] + " Escreva a fulano@exemplo.invalid."), "principais[0].fato")
        self.passa(lambda e: P(e, 0).update(fato=P(e, 0)["fato"] + " Subiu +12,5% e fechou em 1.234.567 (11)."))

    def test_html_controle_e_caminho_de_computador(self):
        self.planta("R17", lambda e: e.update(resumo=e["resumo"] + " <b>urgente</b>"), "resumo")
        self.planta("R17", lambda e: e.update(resumo=e["resumo"] + " </script>"), "resumo")
        self.passa(lambda e: e.update(resumo=e["resumo"] + " Alta < 5% e 3 > 2."))
        for controle in ("\n", "\t", "\r", "\x00", "\x07", "\x7f", "\x85", chr(0x2028), chr(0x2029)):
            achado = self.planta("R17", lambda e: e.update(resumo="Texto fictício." + controle + "Segunda linha."), "resumo")
            self.assertIn("caractere de controle", achado.mensagem)
        barra = "/"
        for caminho in (barra + "home" + barra + "alguem", barra + "Users" + barra + "alguem", "C:" + chr(92) + "Docs"):
            self.planta("R17", lambda e: e.update(resumo=e["resumo"] + " Arquivo em " + caminho), "resumo")

    def test_texto_vazio(self):
        self.planta("R17", lambda e: e["bastidores"].update(limites="  "), "bastidores.limites")
        self.planta("R17", lambda e: P(e, 0)["na_pratica"].__setitem__(0, ""), "principais[0].na_pratica[0]")

    def test_tamanho_maximo_em_caracteres(self):
        self.planta("R17", lambda e: P(e, 0).update(titulo="[EXEMPLO] " + "á" * 111), "principais[0].titulo")
        self.passa(lambda e: P(e, 0).update(titulo="[EXEMPLO] " + "á" * 110))
        achado = self.planta("R17", lambda e: e.update(resumo="x" * 250), "resumo")
        self.assertIn("tem 250 caracteres, o máximo é 240. Corte 10.", achado.mensagem)
        self.planta("R17", lambda e: e["bastidores"].update(limites="x" * 100000), "bastidores.limites")

    def test_cada_campo_de_texto_tem_o_maximo_da_tabela(self):
        caminhos = {
            ("alerta", "motivo"): lambda e: e["alerta"], ("dominio", "leitura"): lambda e: D(e, 0),
            ("dominio", "vigiar"): lambda e: D(e, 0), ("gatilho", "texto"): lambda e: D(e, 0)["gatilhos"][0],
            ("indicador", "nome"): lambda e: e["indicadores"][0], ("indicador", "unidade"): lambda e: e["indicadores"][0],
            ("fonte_indicador", "nome"): lambda e: e["indicadores"][0]["fonte"],
            ("principal", "fato"): lambda e: P(e, 0), ("principal", "no_brasil"): lambda e: P(e, 0),
            ("radar", "titulo"): lambda e: R(e, 0), ("radar", "fato"): lambda e: R(e, 0),
            ("radar", "sem_placar"): lambda e: R(e, 0), ("ataque", "alvo_nome"): lambda e: P(e, 0)["ataques"][2],
            ("ataque", "enquadramento"): lambda e: P(e, 0)["ataques"][0], ("ataque", "omite"): lambda e: P(e, 0)["ataques"][0],
            ("eixo", "porque"): lambda e: P(e, 0)["eixo"], ("placar", "porque"): lambda e: P(e, 0)["placar"][0],
            ("vetor", "porque"): lambda e: P(e, 0)["vetores"][0], ("fonte", "nome"): lambda e: P(e, 0)["fontes"][5],
            ("fonte", "titulo"): lambda e: P(e, 0)["fontes"][0], ("placar_do_dia", "frase"): lambda e: e["placar_do_dia"][0],
            ("novo_player", "nome"): lambda e: e["novos_players"][0], ("novo_player", "nota"): lambda e: e["novos_players"][0],
            ("novo_player", "justificativa"): lambda e: e["novos_players"][0], ("errata", "erro"): lambda e: e["errata"][0],
            ("errata", "correcao"): lambda e: e["errata"][0], ("errata", "anula_vetor"): lambda e: e["errata"][1],
            ("resposta", "pergunta"): lambda e: e["respostas"][0], ("resposta", "texto"): lambda e: e["respostas"][0],
            ("bastidores", "limites"): lambda e: e["bastidores"], ("candidato", "nome"): lambda e: e["bastidores"]["candidatos"][0],
            ("candidato", "motivo"): lambda e: e["bastidores"]["candidatos"][0],
        }
        for (tipo, campo), onde in sorted(caminhos.items()):
            maximo = valida.MAXIMOS[(tipo, campo)]
            with self.subTest(tipo=tipo, campo=campo):
                edicao = apoio.exemplo()
                onde(edicao)[campo] = "[EXEMPLO] " + "x" * (maximo - 10)
                self.assertNotIn("R17", apoio.regras(confere(edicao)), "no limite (%d) tem de passar" % maximo)
                onde(edicao)[campo] = "[EXEMPLO] " + "x" * (maximo - 9)
                achado = apoio.acusa(self, confere(edicao), "R17", campo)
                self.assertIn("o máximo é %d" % maximo, achado.mensagem)

    def test_url(self):
        self.planta("R17", lambda e: e["errata"][0].update(url="ftp://exemplo.invalid/a"), "errata[0].url")
        self.planta("R17", lambda e: e["errata"][0].update(url="https://exemplo.invalid/a b"), "errata[0].url")
        self.planta("R17", lambda e: e["errata"][0].update(url="exemplo.invalid/a"), "errata[0].url")
        self.planta("R17", lambda e: e["errata"][0].update(url="https://exemplo.invalid/" + "a" * 477), "errata[0].url")
        self.passa(lambda e: e["errata"][0].update(url="https://exemplo.invalid/" + "a" * 476))
        self.planta("R17", lambda e: e["novos_players"][0]["dna_fontes"].update(moderacao="javascript:alert(1)"), "dna_fontes.moderacao")
        self.planta("R17", lambda e: e["indicadores"][0]["fonte"].update(url=None), "indicadores[0].fonte.url")

    def test_url_sem_sinal_de_shell_barra_invertida_nem_usuario(self):
        """ESQUEMA, seção 0, "URL": nada de aspas, apóstrofo, crase, cifrão, barra invertida nem usuário@."""
        ruins = ("https://exemplo.invalid/a'b", 'https://exemplo.invalid/a"b', "https://exemplo.invalid/a`id`",
                 "https://exemplo.invalid/$(id)", "https://exemplo.invalid/a\\b",
                 "https://golpe.invalid\\@www.exemplo.invalid/a", "https://alguem@exemplo.invalid/a")
        for ruim in ruins:
            achado = self.planta("R17", lambda e: e["errata"][0].update(url=ruim), "errata[0].url")
            self.assertIn("barra invertida nem usuário@", achado.mensagem)
        self.planta("R17", lambda e: P(e, 0)["fontes"][0].update(url="https://golpe.invalid\\@www.exemplo.invalid/a"),
                    "principais[0].fontes[0].url")
        self.passa(lambda e: e["errata"][0].update(url="https://exemplo.invalid/@perfil/a"))

    def test_arquivo_de_ate_60_kb(self):
        apoio.limpo(self, confere(apoio.exemplo(), tamanho=61440))
        achado = apoio.acusa(self, confere(apoio.exemplo(), tamanho=61441), "R17", "edicao")
        self.assertIn("61441 bytes; o máximo é 61440", achado.mensagem)
        gorda = apoio.exemplo()
        gorda["extra"] = "x" * 70000
        apoio.acusa(self, valida.confere_edicao(gorda, apoio.dados()), "R17", "edicao")  # sem `tamanho`, mede o JSON


class TestaR18(Regra):
    def test_exemplo_pede_a_marca_em_todo_titulo(self):
        self.planta("R18", lambda e: P(e, 0).update(titulo="País fictício ataca terminal"), "principais[0].titulo")
        self.planta("R18", lambda e: R(e, 0)["fontes"][0].update(titulo="A new AI chip deal"), "radar[0].fontes[0].titulo")

    def test_sem_exemplo_nenhum_titulo_leva_a_marca(self):
        achados = confere(dict((k, v) for k, v in apoio.exemplo().items() if k != "exemplo"))
        self.assertEqual(apoio.regras(achados), ["R18"])
        self.assertEqual(len(achados), 9 + sum(len(i["fontes"]) for i in apoio.exemplo()["principais"] + apoio.exemplo()["radar"]))
        self.assertEqual(len(valida.confere_edicao(apoio.exemplo(), apoio.dados(), tamanho=1)), 0)

    def test_exemplo_false_e_o_mesmo_que_sem_o_campo(self):
        edicao = apoio.completa(apoio.rascunho(DIA))
        apoio.limpo(self, confere(edicao, historico=valida.Historico()))
        edicao = valida.normaliza(dict(edicao, exemplo=False))
        apoio.limpo(self, confere(edicao, historico=valida.Historico()))


class TestaR19(Regra):
    def test_item_de_ia_sem_a_marca_de_conflito(self):
        achado = self.planta("R19", lambda e: R(e, 0).pop("conflito_de_interesse"), "radar[0].conflito_de_interesse")
        self.assertIn("a categoria é 'ia'", achado.mensagem)
        self.planta("R19", lambda e: R(e, 0).update(conflito_de_interesse=False), "radar[0].conflito_de_interesse")

    def test_texto_cita_openai_sem_a_marca(self):
        achado = self.planta("R19", lambda e: P(e, 2).update(fato=P(e, 2)["fato"] + " A OpenAI comentou."), "principais[2]")
        self.assertIn("'OpenAI'", achado.mensagem)
        self.planta("R19", lambda e: P(e, 2)["fontes"][0].update(titulo="[EXEMPLO] Claude-4 is out"), "principais[2]")

    def test_jean_claude_nao_liga_a_marca(self):
        self.passa(lambda e: P(e, 2).update(fato=P(e, 2)["fato"] + " Jean-Claude Exemplo presidiu a sessão."))
        self.passa(lambda e: P(e, 2).update(fato=P(e, 2)["fato"] + " O Googleplex e a metaAnthropica não contam."))
        self.passa(lambda e: P(e, 2)["fontes"][0].update(url="https://exemplo.invalid/ap/Claude"))  # url não é texto

    def test_alvo_ou_player_de_vetor_na_lista_de_conflito(self):
        achado = self.planta("R19", lambda e: P(e, 2)["ataques"][0].update(alvo="musk"), "principais[2].conflito_de_interesse")
        self.assertIn("'musk'", achado.mensagem)

    def test_fonte_de_veiculo_ligado_a_anthropic(self):
        self.assertIn("anthropic", apoio.dados().mapa["anthropic_news"]["serve_a"])

        def muda(e):
            P(e, 2)["fontes"].append(fonte("anthropic_news", "nota"))
        achado = self.planta("R19", muda, "principais[2].conflito_de_interesse")
        self.assertIn("'anthropic_news'", achado.mensagem)

    def test_com_a_marca_a_confianca_vai_ate_media(self):
        self.planta("R19", lambda e: P(e, 2).update(conflito_de_interesse=True), "principais[2].confianca")
        self.passa(lambda e: P(e, 2).update(conflito_de_interesse=True, confianca="media"))  # o agente pode ligar

    def test_vetor_em_item_de_ia_provado_por_fonte_forte_que_nao_e_primaria(self):
        self.planta("R19", lambda e: R(e, 1)["vetores"][0].update(url=R(e, 1)["fontes"][0]["url"]), "radar[1].vetores[0].url")

    def test_quando_a_empresa_e_parte_pede_fontes_de_dois_partidos_ate_no_radar(self):
        def muda(e):
            R(e, 4)["ataque"]["alvo"] = "musk"
            R(e, 4)["conflito_de_interesse"] = True
        achado = self.planta("R19", muda, "radar[4].fontes")
        self.assertIn("2 partidos", achado.mensagem)

    def test_noticia_de_ia_sem_parte_na_lista_passa_com_um_partido(self):
        def muda(e):  # r1: IA, alvo fora da lista, sem termo: uma fonte forte basta
            R(e, 0)["fontes"] = R(e, 0)["fontes"][:1]
        self.assertEqual(valida.calcula_conflito(apoio.dados(), R(apoio.exemplo(), 0)), (True, ["a"]))
        self.passa(muda)

    def test_os_casos_calculados(self):
        dados, e = apoio.dados(), apoio.exemplo()
        self.assertEqual(valida.calcula_conflito(dados, P(e, 0)), (False, []))
        self.assertEqual(valida.calcula_conflito(dados, P(e, 1)), (True, ["a", "b", "c"]))  # ia; alvo altman; "Google"
        self.assertEqual(valida.calcula_conflito(dados, R(e, 1)), (True, ["a", "b", "c"]))  # ia; google; "Google"
        self.assertEqual(valida.calcula_conflito(dados, R(e, 1), do_dia=False), (True, ["a"]))
        ligado = dict(P(e, 2), fontes=P(e, 2)["fontes"] + [fonte("import_ai", "x")])
        self.assertEqual(valida.calcula_conflito(dados, ligado), (True, ["d"]))

    def test_edicao_de_arquivo_nao_e_medida_contra_a_lista_de_hoje(self):
        self.passa(lambda e: P(e, 2).update(fato=P(e, 2)["fato"] + " A OpenAI comentou."), do_dia=False)
        self.passa(lambda e: P(e, 2)["ataques"][0].update(alvo="musk"), do_dia=False)
        self.planta("R19", lambda e: R(e, 0).pop("conflito_de_interesse"), "radar[0]", do_dia=False)  # o caso (a) fica
        self.planta("R19", lambda e: P(e, 1).update(confianca="alta"), "principais[1].confianca", do_dia=False)


class TestaR20(Regra):
    def test_player_novo_com_3_posicoes(self):
        def muda(e):
            novo = e["novos_players"][0]
            novo["dna"]["moderacao"] = "W"
            del novo["dna_fontes"]["moderacao"]
        achado = self.planta("R20", muda, "novos_players[0].dna")
        self.assertIn("3 posições conhecidas", achado.mensagem)

    def test_player_novo_com_partido_errado(self):
        achado = self.planta("R20", lambda e: e["novos_players"][0].update(partido="soberanistas"), "novos_players[0].partido")
        self.assertIn("'independentes'", achado.mensagem)

    def test_a_conta_do_partido(self):
        dados = apoio.dados()
        self.assertEqual(valida.partido_pelo_dna(dados, apoio.exemplo()["novos_players"][0]["dna"]), "independentes")  # empate
        tudo_azul = dict((tema, "B") for tema in dados.temas)
        self.assertEqual(valida.partido_pelo_dna(dados, tudo_azul), "ordem_global")
        self.assertEqual(valida.partido_pelo_dna(dados, dict(tudo_azul, ia_depois="R", imigracao="R")), "centro_atlantico")
        self.assertEqual(valida.partido_pelo_dna(dados, dict((tema, "W") for tema in dados.temas)), "independentes")
        self.assertEqual(valida.partido_pelo_dna(dados, None), "independentes")

    def test_player_novo_de_tipo_regime(self):
        self.planta("R20", lambda e: e["novos_players"][0].update(tipo="regime"), "novos_players[0].tipo")

    def test_player_novo_com_virada(self):
        self.planta("R20", lambda e: e["novos_players"][0]["dna"].update(ia_depois="BY"), "novos_players[0].dna.ia_depois")
        self.planta("R20", lambda e: e["novos_players"][0]["dna"].update(ia_depois="K"), "novos_players[0].dna.ia_depois")

    def test_no_maximo_um_e_que_ainda_nao_exista(self):
        self.planta("R20", lambda e: e["novos_players"].append(dict(e["novos_players"][0], id="reino_de_amostra")), "novos_players")
        self.planta("R20", lambda e: e["novos_players"][0].update(id="russia"), "novos_players[0].id")
        self.planta("R20", lambda e: e["novos_players"][0].update(id="soberanistas"), "novos_players[0].id")
        self.planta("R20", lambda e: e["novos_players"][0].update(id="outro"), "novos_players[0].id")

    def test_o_proprio_registro_ja_publicado_passa(self):
        objetos = apoio.brutos()
        ficha = dict(apoio.exemplo()["novos_players"][0], origem="rotina", incluido_em=DIA)
        objetos["players"]["players"].append(ficha)
        self.passa(dados=apoio.monta(objetos))
        ficha["incluido_em"] = "2026-11-18"  # publicado noutro dia: já era player
        self.planta("R20", lambda e: None, "novos_players[0].id", dados=apoio.monta(objetos))

    def test_time_discutivel_dna_dna_fontes_e_duvidas(self):
        self.planta("R20", lambda e: e["novos_players"][0].update(time_discutivel=False), "novos_players[0].time_discutivel")
        self.planta("R20", lambda e: e["novos_players"][0]["dna"].pop("clima"), "novos_players[0].dna")
        self.planta("R20", lambda e: e["novos_players"][0]["dna"].update(economia="B"), "novos_players[0].dna")
        self.planta("R20", lambda e: e["novos_players"][0]["dna_fontes"].pop("moderacao"), "novos_players[0].dna_fontes")
        self.planta("R20", lambda e: e["novos_players"][0]["dna_fontes"].update(clima="https://exemplo.invalid/c"), "novos_players[0].dna_fontes")
        self.planta("R20", lambda e: e["novos_players"][0].update(duvidas=["economia"]), "novos_players[0].duvidas[0]")


class TestaR21(Regra):
    def test_vigiar_e_pergunta_com_data(self):
        self.planta("R21", lambda e: P(e, 0)["vigiar"].__setitem__(0, "O Reino de Amostra responde até 22/11."), "principais[0].vigiar[0]")
        self.planta("R21", lambda e: P(e, 0)["vigiar"].__setitem__(1, "O terminal volta a embarcar petróleo logo?"), "principais[0].vigiar[1]")
        self.planta("R21", lambda e: P(e, 0)["vigiar"].__setitem__(1, "O terminal volta a embarcar até 45/13?"), "principais[0].vigiar[1]")
        self.planta("R21", lambda e: P(e, 0)["vigiar"].__setitem__(1, "O terminal volta a embarcar até 30/02?"), "principais[0].vigiar[1]")
        self.passa(lambda e: P(e, 0)["vigiar"].__setitem__(1, "O terminal volta a embarcar até 29/02?"))

    def test_prazo_da_primeira_pergunta_em_ate_30_dias(self):
        """ESQUEMA, seção 10, R21 (dia): o prazo da primeira pergunta (a última DD/MM dela) vai até 30 dias depois
        da edição. É ela que o publica.py contexto devolve em vigiar_vencendo quando o prazo vence."""
        self.passa(lambda e: P(e, 0)["vigiar"].__setitem__(0, "O Reino de Amostra responde até 19/12?"))  # 30 dias
        achado = self.planta("R21", lambda e: P(e, 0)["vigiar"].__setitem__(0, "O Reino de Amostra responde até 20/12?"),
                             "principais[0].vigiar[0]")
        self.assertIn("aqui, 20/12/2026", achado.mensagem)
        self.assertIn("ponha a data limite por último, em até 30 dias", achado.mensagem)
        # a forma da 2ª pergunta da edição de 23/11/2026: a data de referência por último vira prazo do ano seguinte
        achado = self.planta("R21", lambda e: P(e, 1)["vigiar"].__setitem__(
            0, "Até 30/11, a lei fictícia citada desde 18/11 é sancionada?"), "principais[1].vigiar[0]")
        self.assertIn("aqui, 18/11/2027", achado.mensagem)
        # nas outras perguntas o prazo não é lido, e na edição de arquivo a conta não vale
        self.passa(lambda e: P(e, 0)["vigiar"].__setitem__(1, "Até 30/11, o terminal citado desde 18/11 volta a embarcar?"))
        edicao = apoio.exemplo()
        P(edicao, 0)["vigiar"][0] = "O Reino de Amostra responde até 31/12?"
        apoio.limpo(self, confere(edicao, do_dia=False))

    def test_o_prazo_e_a_ultima_data_lida_a_partir_da_edicao(self):
        self.assertEqual(valida.prazo_do_vigiar("O Reino responde até 22/11?", DIA), "2026-11-22")
        self.assertEqual(valida.prazo_do_vigiar("Depois de 20/11, a lei é sancionada até 05/01?", DIA), "2027-01-05")
        self.assertEqual(valida.prazo_do_vigiar("Sai até 19/11?", DIA), DIA)
        self.assertEqual(valida.prazo_do_vigiar("Sai até 18/11?", DIA), "2027-11-18")
        self.assertIsNone(valida.prazo_do_vigiar("Sai logo?", DIA))
        self.assertIsNone(valida.prazo_do_vigiar(None, DIA))


class TestaR22(Regra):
    def test_fonte_fora_do_mapa_primaria_em_site_nao_oficial(self):
        achado = self.planta("R22", lambda e: P(e, 0)["fontes"][5].update(url="https://gov.br.exemplo.com/decreto.pdf"),
                             "principais[0].fontes[5].primaria")
        self.assertIn("'gov.br.exemplo.com'", achado.mensagem)

    def test_primaria_em_veiculo_privado(self):
        self.planta("R22", lambda e: P(e, 0)["fontes"][0].update(primaria=True), "principais[0].fontes[0].primaria")

    def test_primaria_em_site_oficial_e_em_veiculo_oficial_passa(self):
        self.passa(lambda e: P(e, 0)["fontes"][5].update(url="https://www.planalto.gov.br/decreto.pdf"))
        self.assertEqual(apoio.dados().mapa["comissao_europeia"]["tipo"], "oficial")
        self.assertIs(P(apoio.exemplo(), 0)["fontes"][4]["primaria"], True)

    def test_so_vale_para_a_edicao_do_dia(self):
        self.passa(lambda e: P(e, 0)["fontes"][0].update(primaria=True), do_dia=False)


class TestaR23(Regra):
    def test_dossie_curto_ou_longo(self):
        achado = self.planta("R23", lambda e: P(e, 0).update(realmente="Texto fictício. Curto."), "principais[0].realmente")
        self.assertIn("de 800 a 1500", achado.mensagem)
        self.planta("R23", lambda e: P(e, 0).update(realmente="x" * 799), "principais[0].realmente")
        self.passa(lambda e: P(e, 0).update(realmente="x" * 800))
        self.passa(lambda e: P(e, 0).update(realmente="x" * 1500))
        self.planta("R23", lambda e: P(e, 0).update(realmente="x" * 1501), "principais[0].realmente")

    def test_no_brasil_se_e_so_se_ha_dominios(self):
        self.planta("R23", lambda e: P(e, 0).pop("no_brasil"), "principais[0].no_brasil")
        self.planta("R23", lambda e: P(e, 1).update(no_brasil="Texto fictício. Nada muda."), "principais[1].no_brasil")


def _lado_incerto(e):
    a = P(e, 1)["ataques"][0]
    a["veiculo"], a["lado"], a["url"] = "techcrunch", "bancada_talento", "https://exemplo.invalid/techcrunch/x"
    P(e, 1)["fontes"].append({"veiculo": "techcrunch", "titulo": "[EXEMPLO] x", "url": a["url"], "publicado_em": "2026-11-19"})


def _mesmo_partido(e):
    R(e, 2)["fontes"][0]["veiculo"] = "techcrunch"
    R(e, 2)["ataque"].update(veiculo="techcrunch", lado="bancada_talento")


def _baixa_com_placar(e):
    del R(e, 2)["sem_placar"]
    R(e, 2)["placar"] = [{"partido": "bancada_talento", "efeito": "ganha", "forca": 1, "evidencia": "narrativa",
                          "porque": "Texto fictício. x"}]


def _nivel_3_por_radar(e):
    g = D(e, 3)["gatilhos"][0]
    g["criterio"] = "suprimentos.3"
    del g["excecao"]
    D(e, 3)["nivel"] = e["alerta"]["nivel"] = 3


def _alta_sem_confirmacao_como_3(e):
    e["indicadores"][0]["variacao_7d_pct"] = 10.4
    D(e, 0)["gatilhos"][0]["criterio"] = "energia.3"


def _alivio(e):
    D(e, 2)["gatilhos"] = [{"criterio": "cambio.4", "ref": "p1", "texto": "Texto fictício. Acabou.", "alivio": True}]


def _tres_posicoes(e):
    novo = e["novos_players"][0]
    novo["dna"]["moderacao"] = "W"
    del novo["dna_fontes"]["moderacao"]


def _reduzida_sem_ia(e):
    e["estado"] = "reduzida"
    e["radar"] = e["radar"][3:]
    for indice, item in enumerate(e["radar"]):
        item["id"] = "r%d" % (indice + 1)
    D(e, 3)["gatilhos"][0]["ref"] = "r1"
    for linha in e["placar_do_dia"]:
        if linha["partido"] == "ordem_global":
            linha["narrativa"] = 0
    e["bastidores"]["veiculos_consultados"] = len(set(
        f["veiculo"] for item in e["principais"] + e["radar"] for f in item["fontes"]) - set(["outro"]))


# Os 41 casos da conferência da fase 1, na mesma ordem e com o mesmo nome: (nome, regra esperada, defeito).
# Regra None quer dizer que o caso tem de passar sem erro nenhum.
OS_41 = (
    ("sem mudança", None, lambda e: None),
    ("radar com confiança alta e um campo só", "R08", lambda e: R(e, 3).update(confianca="alta")),
    ("principal com atirador de lado incerto", "R03", _lado_incerto),
    ("fonte fora do mapa primária em site não oficial", "R22",
     lambda e: P(e, 0)["fontes"][5].update(url="https://gov.br.exemplo.com/decreto.pdf")),
    ("primária em veículo privado", "R22", lambda e: P(e, 0)["fontes"][0].update(primaria=True)),
    ("radar com 2 fontes do mesmo partido, sem forte", "R07", _mesmo_partido),
    ("vetor provado por fonte que não é forte", "R11", lambda e: P(e, 0)["vetores"][0].update(url=P(e, 0)["fontes"][2]["url"])),
    ("vetor em item de IA provado por fonte forte que não é primária", "R19",
     lambda e: R(e, 1)["vetores"][0].update(url=R(e, 1)["fontes"][0]["url"])),
    ("vetor para partido que vota igual no tema", "R11", lambda e: P(e, 0)["vetores"][0].update(para="ordem_global")),
    ("vetor com tema histórico", "R11", lambda e: P(e, 0)["vetores"][0].update(tema="pandemia_inicio")),
    ("item de IA sem a marca de conflito", "R19", lambda e: R(e, 0).pop("conflito_de_interesse")),
    ("texto cita OpenAI sem a marca", "R19", lambda e: P(e, 2).update(fato=P(e, 2)["fato"] + " A OpenAI comentou.")),
    ("Jean-Claude não liga a marca", None,
     lambda e: P(e, 2).update(fato=P(e, 2)["fato"] + " Jean-Claude Exemplo presidiu a sessão.")),
    ("narrativa somada ao saldo", "R12",
     lambda e: [l.update(saldo=2) for l in e["placar_do_dia"] if l["partido"] == "soberanistas"]),
    ("placar vazio sem sem_placar", "R10", lambda e: R(e, 4).pop("sem_placar")),
    ("item de confiança baixa com placar", "R10", _baixa_com_placar),
    ("radar com força 3 sem fonte forte", "R10", lambda e: R(e, 5)["placar"][0].update(forca=3)),
    ("dossiê curto", "R23", lambda e: P(e, 0).update(realmente="Texto fictício. Curto.")),
    ("principal com domínios e sem no_brasil", "R23", lambda e: P(e, 0).pop("no_brasil")),
    ("gatilho de nível 3 provado por radar", "R13b", _nivel_3_por_radar),
    ("gatilho provado por item de confiança baixa", "R13b", lambda e: D(e, 3)["gatilhos"][0].update(ref="r3")),
    ("alta forte de preço sem confirmação declarada como nível 3", "R13c", _alta_sem_confirmacao_como_3),
    ("alta forte de preço sem confirmação declarada como nível 2", None,
     lambda e: e["indicadores"][0].update(variacao_7d_pct=10.4)),
    ("alta forte de preço confirmada pede nível 3", "R13c",
     lambda e: e["indicadores"][0].update(variacao_7d_pct=10.4, confirmado=True)),
    ("alta do dólar no dia com cotação de outro dia não vale", None,
     lambda e: e["indicadores"][7].update(variacao_pct=1.8, data="2026-11-18")),
    ("alta do dólar no dia, com cotação do dia, pede gatilho", "R13c", lambda e: e["indicadores"][7].update(variacao_pct=1.8)),
    ("sem_preco errada", "R13f", lambda e: D(e, 1).update(sem_preco=[])),
    ("alívio sem histórico", "R13e", _alivio),
    ("player novo com 3 posições", "R20", _tres_posicoes),
    ("player novo com partido errado", "R20", lambda e: e["novos_players"][0].update(partido="soberanistas")),
    ("player novo de tipo regime", "R20", lambda e: e["novos_players"][0].update(tipo="regime")),
    ("player novo com virada", "R20", lambda e: e["novos_players"][0]["dna"].update(ia_depois="BY")),
    ("errata que anula vetor sem url", "R16", lambda e: e["errata"][1].pop("url")),
    ("resposta sim sem url", "R16", lambda e: e["respostas"][0].pop("url")),
    ("link em texto", "R17", lambda e: P(e, 0).update(fato=P(e, 0)["fato"] + " Leia em www.exemplo.com.")),
    ("markdown de link em título de fonte", "R17", lambda e: P(e, 0)["fontes"][0].update(titulo="[EXEMPLO] [Leia](x)")),
    ("sobra do modelo (texto só de algarismos)", "R17", lambda e: R(e, 0).update(sem_placar="160")),
    ("telefone em texto", "R17", lambda e: P(e, 0).update(fato=P(e, 0)["fato"] + " Contato: (11) 91234-5678.")),
    ("continuacao_de apontando para radar", None, lambda e: P(e, 1).update(continuacao_de="2026-11-18/r12")),
    ("alvo desconhecido", "R02", lambda e: R(e, 4)["ataque"].update(alvo="ninguem")),
    ("reduzida sem IA no radar", None, _reduzida_sem_ia),
)


class TestaOs41DaFase1(unittest.TestCase):
    """A lista de defeitos plantados que provou a conferência da fase 1, agora contra o validador de verdade."""

    def test_sao_41_e_cada_um_da_o_resultado_esperado(self):
        self.assertEqual(len(OS_41), 41)
        self.assertEqual(len(set(nome for nome, _, _ in OS_41)), 41)
        for nome, regra, defeito in OS_41:
            with self.subTest(nome):
                edicao = apoio.exemplo()
                defeito(edicao)
                achados = confere(edicao)
                if regra is None:
                    self.assertEqual(achados, [], apoio.linhas(achados))
                else:
                    self.assertIn(regra, apoio.regras(achados), apoio.linhas(achados) or "nenhum erro")

    def test_pela_linha_de_comando_o_codigo_de_saida_acompanha(self):
        with apoio.tempfile.TemporaryDirectory(prefix="info-valida-") as pasta:
            raiz = apoio.os.path.join(pasta, "raiz")
            apoio.shutil.copytree(apoio.DADOS, apoio.os.path.join(raiz, "dados"))
            for nome, regra, defeito in OS_41[::5]:
                edicao = apoio.exemplo()
                defeito(edicao)
                arquivo = apoio.os.path.join(pasta, "edicao.json")
                apoio.grava(arquivo, edicao)
                codigo, saida, erro = apoio.roda(["--raiz", raiz, "--edicao", arquivo])
                self.assertEqual((codigo, erro), (0 if regra is None else 1, ""), nome)
                if regra is not None:
                    self.assertIn("ERRO %s " % regra, saida, nome)


class TestaNadaPassaCalado(unittest.TestCase):
    """O pior defeito de um validador é aceitar calado. Aqui o exemplo inteiro é mexido, nó por nó."""

    def setUp(self):
        self.exemplo = apoio.exemplo()
        self.nos = list(self.percorre(self.exemplo))
        self.assertGreater(len(self.nos), 800)

    def percorre(self, valor, caminho=()):
        yield caminho, valor
        if isinstance(valor, dict):
            for chave in valor:
                yield from self.percorre(valor[chave], caminho + (chave,))
        elif isinstance(valor, list):
            for indice, item in enumerate(valor):
                yield from self.percorre(item, caminho + (indice,))

    def mexe(self, caminho, funcao):
        edicao = apoio.exemplo()
        alvo = edicao
        for chave in caminho[:-1]:
            alvo = alvo[chave]
        funcao(alvo, caminho[-1])
        return [a for a in confere(edicao, tamanho=1) if a.gravidade == "ERRO"]

    def test_tirar_qualquer_campo_obrigatorio_e_acusado(self):
        opcionais = set(chave for chaves in valida.OPCIONAIS.values() for chave in chaves)
        tirados = 0
        for caminho, valor in self.nos:
            if not caminho or not isinstance(caminho[-1], str):
                continue
            erros = self.mexe(caminho, lambda alvo, chave: alvo.pop(chave))
            tirados += 1
            if caminho[-1] in opcionais:
                continue   # opcional pode sair (se a saída quebra outra regra, é ela que acusa)
            self.assertTrue(erros, "tirar %s passou calado" % ".".join(map(str, caminho)))
        self.assertGreater(tirados, 500)

    def test_campo_desconhecido_em_qualquer_objeto_e_acusado(self):
        objetos = [caminho for caminho, valor in self.nos if isinstance(valor, dict)]
        self.assertGreater(len(objetos), 100)
        for caminho in objetos:
            edicao = apoio.exemplo()
            alvo = edicao
            for chave in caminho:
                alvo = alvo[chave]
            alvo["campo_inventado"] = 1
            erros = [a for a in confere(edicao, tamanho=1) if a.gravidade == "ERRO"]
            self.assertTrue(erros, "campo inventado em %s passou calado" % ".".join(map(str, caminho)))

    def test_valor_de_outro_tipo_em_qualquer_lugar_e_acusado(self):
        feitos = 0
        for posicao, (caminho, valor) in enumerate(self.nos):
            if not caminho:
                continue
            for torto in (None, True, 7, 3.5, "x", [], {}):
                if type(torto) is type(valor):
                    continue
                numero = isinstance(valor, (int, float)) and not isinstance(valor, bool)
                if numero and isinstance(torto, (int, float)) and not isinstance(torto, bool):
                    continue   # número por número pode valer
                if torto is None and caminho[0] == "indicadores" and caminho[-1] in ("variacao_pct", "variacao_7d_pct"):
                    continue   # a variação pode ser null (o domínio fica cego, e aí é a regra R13f que acusa ou não)
                if (posicao + feitos) % 2 and not isinstance(valor, (dict, list)):
                    feitos += 1
                    continue   # das folhas, metade em rodízio: o teste inteiro roda em poucos segundos
                erros = self.mexe(caminho, lambda alvo, chave: alvo.__setitem__(chave, torto))
                feitos += 1
                self.assertTrue(erros, "%s = %r passou calado" % (".".join(map(str, caminho)), torto))
        self.assertGreater(feitos, 3000)

    def test_indicador_mensal_nao_tem_variacao_de_7_dias(self):
        edicao = apoio.exemplo()
        self.assertEqual(edicao["indicadores"][6]["id"], "fao_ffpi")
        edicao["indicadores"][6]["variacao_7d_pct"] = 0.4
        apoio.acusa(self, confere(edicao), "R00", "indicadores[6].variacao_7d_pct")
        apoio.limpo(self, confere(edicao, do_dia=False))   # a frequência vem do catálogo: só na edição do dia


class TestaRegrasDoDia(Regra):
    """Edição publicada é registro: o que cruza a edição com o mapa, o catálogo e os limiares só vale no dia."""

    DEFEITOS = {
        "R02 veículo fora do mapa": lambda e: P(e, 2)["fontes"][0].update(veiculo="saiu_do_mapa"),
        "R03 lado diferente do mapa": lambda e: P(e, 0)["ataques"][0].update(lado="soberanistas"),
        "R07 radar sem fonte forte": lambda e: (R(e, 2)["fontes"][0].update(veiculo="meta_ai"),
                                                R(e, 2)["ataque"].update(veiculo="meta_ai", lado="bancada_talento")),
        "R08 teto de confiança": lambda e: R(e, 3).update(confianca="alta"),
        "R10 força 3 no radar sem fonte forte": lambda e: (
            R(e, 5)["placar"][0].update(forca=3),
            [l.update(saldo=3) for l in e["placar_do_dia"] if l["partido"] == "independentes"]),
        "R11 vetor provado por fonte que não é forte": lambda e: P(e, 0)["vetores"][0].update(url=P(e, 0)["fontes"][2]["url"]),
        "R13b nível 5 do Brasil sem documento do Brasil": lambda e: (
            D(e, 0)["gatilhos"][1].update(criterio="energia.5"), D(e, 0).update(nivel=5), e["alerta"].update(nivel=5)),
        "R19 texto cita termo da lista de conflito": lambda e: P(e, 2).update(fato=P(e, 2)["fato"] + " A OpenAI comentou."),
        "R13c gatilho de preço": lambda e: e["indicadores"][7].update(variacao_pct=1.8),
        "R13f sem_preco": lambda e: D(e, 1).update(sem_preco=[]),
        "R22 primária em veículo privado": lambda e: P(e, 0)["fontes"][0].update(primaria=True),
        # Voto típico é da régua, que o dono revê (ESQUEMA, seção 10, princípio das regras do dia).
        "R11 destino que vota igual no tema": lambda e: P(e, 0)["vetores"][0].update(para="ordem_global"),
        "R11 destino sem posição firme no tema": lambda e: P(e, 0)["vetores"][0].update(para="bancada_talento"),
        "R20 partido fora da conta do dna": lambda e: e["novos_players"][0].update(partido="soberanistas"),
        # O prazo só se julga no dia em que é escrito: a edição de arquivo não volta a ser conferida contra a data.
        "R21 prazo da primeira pergunta a mais de 30 dias": lambda e: P(e, 0)["vigiar"].__setitem__(
            0, "O Reino de Amostra responde até 05/01?"),
    }

    def test_cada_regra_do_dia_acusa_no_dia_e_cala_no_arquivo(self):
        for nome, muda in sorted(self.DEFEITOS.items()):
            with self.subTest(nome):
                edicao = apoio.exemplo()
                muda(edicao)
                self.assertIn(nome.split()[0], apoio.regras(confere(edicao, do_dia=True)))
                apoio.limpo(self, confere(edicao, do_dia=False))

    def test_o_dono_revisa_o_mapa_e_a_edicao_de_arquivo_continua_valendo(self):
        objetos = apoio.brutos()
        for veiculo in objetos["veiculos"]["veiculos"]:
            if veiculo["id"] == "nyt":
                veiculo.update(lado="centrao", fatos="baixa", lado_confianca="baixa", tipo="estatal")
            if veiculo["id"] == "comissao_europeia":
                veiculo.update(tipo="privado", fatos="media")
        objetos["veiculos"]["veiculos"] = [v for v in objetos["veiculos"]["veiculos"] if v["id"] != "wsj"]
        objetos["regua"]["conflito"]["termos"].append("Reino de Amostra")
        objetos["regua"]["conflito"]["players"].append("russia")
        objetos["regua"]["sites_oficiais"]["outros"].remove("oficial.exemplo.invalid")
        objetos["regua"]["niveis_alerta"][1]["criterios"]["energia"]["precos"][0]["alta_minima_pct"] = 9
        objetos["indicadores"]["indicadores"] = [i for i in objetos["indicadores"]["indicadores"] if i["id"] != "vix"]
        revisados = apoio.monta(objetos)
        self.assertEqual(revisados.problemas, [])
        apoio.limpo(self, confere(apoio.exemplo(), dados=revisados, do_dia=False))
        do_dia = apoio.regras(confere(apoio.exemplo(), dados=revisados, do_dia=True))
        for regra in ("R02", "R03", "R13c", "R19", "R22"):
            self.assertIn(regra, do_dia)

    def test_o_dono_revisa_o_voto_tipico_e_a_edicao_de_arquivo_continua_valendo(self):
        objetos = apoio.brutos()
        votos = dict((p["id"], p) for p in objetos["regua"]["partidos"])
        votos["soberanistas"]["voto_tipico"] = "R R R R R Y R"   # clima: o destino do vetor de p1 deixa de ser firme
        votos["centrao"]["voto_tipico"] = "W Y B B R Y R"        # o dna do player novo passa a dar centrao
        revisados = apoio.monta(objetos)
        self.assertEqual(revisados.problemas, [])
        self.assertEqual(valida.partido_pelo_dna(revisados, apoio.exemplo()["novos_players"][0]["dna"]), "centrao")
        apoio.limpo(self, confere(apoio.exemplo(), dados=revisados, do_dia=False))
        achados = confere(apoio.exemplo(), dados=revisados, do_dia=True)
        caminhos = [a.caminho for a in achados if a.gravidade == "ERRO"]
        self.assertIn("principais[0].vetores[0].para", caminhos)
        self.assertIn("novos_players[0].partido", caminhos)
        self.assertEqual(apoio.regras(achados), ["R11", "R20"])


if __name__ == "__main__":
    unittest.main()
