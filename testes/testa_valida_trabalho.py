#!/usr/bin/env python3
"""Testes do valida.py: as regras da pasta de trabalho (T1 a T5 do ESQUEMA, seção 10).

A linha de comando do valida.py não usa estas regras: quem usa é o publica.py edicao, que importa as
funções e passa o conteúdo de coleta.json, urls.txt e conferencia.json já lido. Aqui cada função é chamada
direto, com um defeito e com o caso bom.

Rodar da raiz do repositório: python3 -B testes/testa_valida_trabalho.py
"""
import copy
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "valida"))

import apoio  # noqa: E402
from apoio import valida  # noqa: E402

DIA = "2026-11-19"
VESPERA = "2026-11-18"


def itens(rascunho):
    return rascunho["principais"] + rascunho["radar"]


def ataques(item):
    return item.get("ataques", []) + ([item["ataque"]] if "ataque" in item else [])


def pasta_de_trabalho(rascunho):
    """(coleta, urls, conferencia) coerentes com o rascunho, como numa execução boa da rotina.

    Toda fonte de veículo do mapa veio da mesa (está em coleta.json, com o veículo e a data do feed). As
    fontes "outro" e as páginas de ataque com `omite` foram abertas: estão em urls.txt e na conferência."""
    manchetes, urls, paginas = [], ["# páginas abertas nesta execução", ""], []
    for item in itens(rascunho):
        for fonte in item["fontes"]:
            if fonte["veiculo"] == "outro":
                urls.append(fonte["url"])
                paginas.append({"url": fonte["url"], "estado": "ok", "publicado_em": fonte["publicado_em"]})
            else:
                manchetes.append({"id": "m%04d" % (len(manchetes) + 1), "veiculo": fonte["veiculo"],
                                  "titulo": fonte["titulo"], "url": fonte["url"],
                                  "publicado_em": fonte["publicado_em"] + "T14:02:00Z"})
        for ataque in ataques(item):
            if "omite" in ataque:
                urls.append(ataque["url"])
    for errata in rascunho["errata"]:
        if "url" in errata:
            urls.append(errata["url"])
            paginas.append({"url": errata["url"], "estado": "ok", "publicado_em": None})
    coleta = {"versao": 1, "dia": rascunho["data"], "resumo": {"feeds_ok": 61, "feeds_falhos": 7},
              "manchetes": manchetes}
    return coleta, "\n".join(urls) + "\n", {"versao": 1, "paginas": paginas}


class ComRascunho(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.dados = apoio.dados()
        self.rascunho = apoio.nos_sites(apoio.rascunho(DIA))   # regra T4: cada endereço no site do veículo
        self.coleta, self.urls, self.conferencia = pasta_de_trabalho(self.rascunho)

    def p(self, indice):
        return self.rascunho["principais"][indice]

    def r(self, indice):
        return self.rascunho["radar"][indice]

    def tira_da_mesa(self, *urls):
        self.coleta["manchetes"] = [m for m in self.coleta["manchetes"] if m["url"] not in urls]

    def abre(self, url, estado="bloqueada", publicado_em=None):
        """Anota a página em urls.txt e põe o resultado dela na conferência."""
        self.urls += url + "\n"
        self.conferencia["paginas"].append({"url": url, "estado": estado, "publicado_em": publicado_em})

    def tudo(self, historico=None):
        return valida.confere_trabalho(self.rascunho, self.dados, DIA, self.coleta, self.urls, self.conferencia, historico)


class TestaTudoJunto(ComRascunho):
    def test_execucao_boa_passa_nas_cinco_regras(self):
        self.assertEqual(self.tudo(), [])
        self.assertEqual(valida.confere_t1(self.rascunho, self.coleta, self.urls), [])
        self.assertEqual(valida.confere_t2(self.rascunho, DIA), [])
        self.assertEqual(valida.confere_t3(self.rascunho, self.dados, self.coleta, self.conferencia), [])
        self.assertEqual(valida.confere_t4(self.rascunho, self.dados, self.coleta), [])
        self.assertEqual(valida.confere_t5(self.rascunho, self.urls), [])

    def test_vale_tambem_para_a_edicao_ja_completa(self):
        completa = apoio.completa(self.rascunho)
        self.assertEqual(valida.confere_trabalho(completa, self.dados, DIA, self.coleta, self.urls, self.conferencia), [])

    def test_as_mensagens_saem_no_formato_do_validador(self):
        self.p(0)["fontes"][0]["publicado_em"] = "2026-11-17"
        achado = apoio.acusa(self, self.tudo(), "T3", "principais[0].fontes[0].publicado_em")
        self.assertEqual(achado.linha(), "ERRO T3 principais[0].fontes[0].publicado_em: é 2026-11-17, o feed diz "
                         "2026-11-19. Corrija a data; se sair da janela, troque a fonte.")

    def test_rascunho_torto_nao_da_excecao(self):
        for torto in (None, [], "x", {}, {"principais": [3, {"fontes": "x", "ataques": [None, {"omite": 1, "url": 2}]}],
                                          "alerta": {"dominios": [None, {"id": "energia", "gatilhos": [None, {"ref": []}]}]},
                                          "novos_players": [{"dna_fontes": {"x": 1}, "url": None}], "errata": "x",
                                          "bastidores": []}):
            for coleta in (None, [], {"manchetes": [None, {"url": 3}], "resumo": "x"}):
                achados = valida.confere_trabalho(torto, self.dados, DIA, coleta, 7 if coleta else None,
                                                  {"paginas": [None, {"url": []}]}, None)
                self.assertIsInstance(achados, list)

    def test_id_de_dominio_que_nao_e_texto_nao_da_excecao(self):
        """Achado do publica.py na fase 2b: com `id` de domínio em lista ou objeto, a T3 procurava a conta do
        domínio num dicionário e dava TypeError. O id torto é da R00, na conferência da edição."""
        for torto in (["energia"], {"id": "energia"}):
            self.rascunho["alerta"]["dominios"][0]["id"] = torto
            self.assertIsInstance(self.tudo(), list)
            self.assertIsInstance(valida.confere_t3(self.rascunho, self.dados, self.coleta, self.conferencia), list)

    def test_le_urls(self):
        self.assertEqual(valida.le_urls(None), [])
        self.assertEqual(valida.le_urls("# comentário\n\n  https://exemplo.invalid/a  \r\nhttps://exemplo.invalid/b\n"),
                         ["https://exemplo.invalid/a", "https://exemplo.invalid/b"])
        self.assertEqual(valida.le_urls(["https://exemplo.invalid/a\n", "#x", 7]), ["https://exemplo.invalid/a"])


class TestaT1(ComRascunho):
    """URL vista: toda URL do rascunho está em coleta.json ou em urls.txt, pelo endereço limpo."""

    def confere(self):
        return valida.confere_t1(self.rascunho, self.coleta, self.urls)

    def test_fonte_que_nao_esta_na_mesa_nem_em_urls(self):
        self.tira_da_mesa(self.p(0)["fontes"][0]["url"])
        achado = apoio.acusa(self, self.confere(), "T1", "principais[0].fontes[0].url")
        self.assertIn("urls.txt", achado.mensagem)
        self.urls += self.p(0)["fontes"][0]["url"] + "\n"
        self.assertEqual(self.confere(), [])

    def test_vale_para_toda_url_que_o_agente_escreve(self):
        self.rascunho["novos_players"] = copy.deepcopy(apoio.exemplo()["novos_players"])
        self.rascunho["errata"] = [{"edicao": VESPERA, "erro": "Texto fictício.", "correcao": "Texto fictício.",
                                    "url": "https://exemplo.invalid/outro/errata"}]
        self.rascunho["respostas"] = [{"edicao": VESPERA, "item": "p1", "pergunta": "Sai até 19/11?", "resposta": "sim",
                                       "texto": "Texto fictício.", "url": "https://exemplo.invalid/outro/resposta"}]
        self.p(0)["vetores"][0]["url"] = "https://exemplo.invalid/outro/vetor"
        self.p(0)["ataques"][1]["url"] = "https://exemplo.invalid/outro/ataque"
        caminhos = sorted(a.caminho for a in self.confere())
        self.assertEqual(caminhos, sorted([
            "principais[0].vetores[0].url", "principais[0].ataques[1].url", "errata[0].url", "respostas[0].url",
            "novos_players[0].dna_fontes.pandemia_depois", "novos_players[0].dna_fontes.moderacao",
            "novos_players[0].dna_fontes.imigracao"]))
        # a url do player novo e a posição de ia_depois são documentos que já estavam em urls.txt, como fonte

    def test_a_comparacao_e_pelo_endereco_limpo(self):
        url = self.p(0)["fontes"][0]["url"]
        self.tira_da_mesa(url)
        self.urls += url.replace("https://", "http://www.") + "/?utm_source=x&utm_medium=y#topo\n"
        self.assertEqual(self.confere(), [])

    def test_linha_de_comentario_nao_e_url_vista(self):
        url = self.p(0)["fontes"][0]["url"]
        self.tira_da_mesa(url)
        self.urls += "# " + url + "\n"
        apoio.acusa(self, self.confere(), "T1", "principais[0].fontes[0].url")

    def test_sem_coleta_e_sem_urls_nada_foi_visto(self):
        achados = valida.confere_t1(self.rascunho, None, None)
        self.assertEqual(apoio.regras(achados), ["T1"])
        self.assertGreater(len(achados), 20)

    def test_os_indicadores_nao_sao_do_agente(self):
        completa = apoio.completa(self.rascunho)
        self.assertTrue(completa["indicadores"][0]["fonte"]["url"])
        self.assertEqual(valida.confere_t1(completa, self.coleta, self.urls), [])


class TestaT2(ComRascunho):
    """A data do rascunho é o dia da execução; o rascunho não traz exemplo nem estado falha."""

    def test_data_diferente_do_dia(self):
        achado = apoio.acusa(self, valida.confere_t2(self.rascunho, "2026-11-20"), "T2", "data")
        self.assertIn("é '2026-11-19', e o dia desta execução é 2026-11-20", achado.mensagem)
        self.assertEqual(valida.confere_t2(self.rascunho, DIA), [])

    def test_rascunho_com_exemplo(self):
        self.rascunho["exemplo"] = True
        apoio.acusa(self, valida.confere_t2(self.rascunho, DIA), "T2", "exemplo")
        self.rascunho["exemplo"] = False
        apoio.acusa(self, valida.confere_t2(self.rascunho, DIA), "T2", "exemplo")

    def test_rascunho_com_estado_falha(self):
        self.rascunho["estado"] = "falha"
        achado = apoio.acusa(self, valida.confere_t2(self.rascunho, DIA), "T2", "estado")
        self.assertIn("publica.py falha", achado.mensagem)
        self.rascunho["estado"] = "reduzida"
        self.assertEqual(valida.confere_t2(self.rascunho, DIA), [])


class TestaT3(ComRascunho):
    """Data conferida pela máquina."""

    def confere(self, historico=None):
        return valida.confere_t3(self.rascunho, self.dados, self.coleta, self.conferencia, historico)

    def troca_por_pagina(self, item, quantas, estado="bloqueada", publicado_em=None):
        """Faz as primeiras `quantas` fontes do item deixarem a mesa e virarem páginas abertas."""
        for fonte in item["fontes"][:quantas]:
            self.tira_da_mesa(fonte["url"])
            self.abre(fonte["url"], estado, publicado_em)

    def test_data_do_rascunho_tem_de_bater_com_a_do_feed_com_1_dia_de_folga(self):
        self.p(2)["fontes"][0]["publicado_em"] = "2026-11-17"
        apoio.acusa(self, self.confere(), "T3", "principais[2].fontes[0].publicado_em")
        for perto in (VESPERA, "2026-11-20"):
            self.p(2)["fontes"][0]["publicado_em"] = perto
            self.assertEqual(self.confere(), [], perto)

    def test_data_do_rascunho_tem_de_bater_com_a_da_pagina(self):
        outro = self.p(0)["fontes"][5]          # o diário oficial fictício: fonte "outro", aberta e conferida
        self.assertEqual(outro["veiculo"], "outro")
        outro["publicado_em"] = "2026-11-15"
        achado = apoio.acusa(self, self.confere(), "T3", "principais[0].fontes[5].publicado_em")
        self.assertIn("é 2026-11-15, a página diz 2026-11-18", achado.mensagem)

    def test_pagina_sem_data_ou_bloqueada_vale_sem_data_conferida(self):
        url = self.r(4)["fontes"][0]["url"]     # r5: uma fonte só, e não sustenta gatilho
        self.tira_da_mesa(url)
        for estado in ("bloqueada", "ok"):
            self.conferencia["paginas"] = [p for p in self.conferencia["paginas"] if p["url"] != url]
            self.abre(url, estado, None)
            self.r(4)["fontes"][0]["publicado_em"] = "2026-11-17"   # sem data conferida, vale o que o agente escreveu
            self.assertEqual(self.confere(), [], estado)

    def test_pagina_que_nao_existe_nao_vale_como_fonte(self):
        url = self.r(4)["fontes"][0]["url"]
        self.tira_da_mesa(url)
        self.abre(url, "erro")
        achado = apoio.acusa(self, self.confere(), "T3", "radar[4].fontes[0].url")
        self.assertIn("a página não existe", achado.mensagem)
        apoio.acusa(self, self.confere(), "T3", "radar[4].ataque.url")

    def test_principal_pede_2_fontes_com_data_conferida_na_janela(self):
        self.troca_por_pagina(self.p(2), 3)          # sobra 1 na mesa
        achado = apoio.acusa(self, self.confere(), "T3", "principais[2].fontes")
        self.assertIn("tem 1 fonte com data conferida", achado.mensagem)
        self.conferencia["paginas"][-1].update(estado="ok", publicado_em=DIA)   # a 2ª: página conferida, com data
        self.assertEqual(self.confere(), [])

    def test_data_conferida_fora_da_janela_nao_conta(self):
        for manchete in self.coleta["manchetes"]:
            if manchete["url"] in [f["url"] for f in self.p(2)["fontes"][:3]]:
                manchete["publicado_em"] = "2026-11-16T10:00:00Z"   # 3 dias antes da edição
        for fonte in self.p(2)["fontes"][:3]:
            fonte["publicado_em"] = "2026-11-17"                    # o agente escreveu dentro da janela e a 1 dia do feed
        apoio.acusa(self, self.confere(), "T3", "principais[2].fontes")

    def test_fonte_primaria_nao_entra_na_conta(self):
        p1 = self.p(0)
        self.assertEqual([f.get("primaria", False) for f in p1["fontes"]], [False, False, False, False, True, True])
        self.troca_por_pagina(p1, 3)                # ficam na mesa: xinhua e a comissão (primária)
        achados = self.confere()
        achado = apoio.acusa(self, achados, "T3", "principais[0].fontes")
        self.assertIn("tem 1 fonte", achado.mensagem)

    def test_gatilho_novo_de_nivel_3_pede_3_fontes_conferidas_no_item(self):
        self.troca_por_pagina(self.p(0), 2)         # sobram 2 que contam: fox_news e xinhua
        achados = self.confere()
        achado = apoio.acusa(self, achados, "T3", "alerta.dominios[0].gatilhos[0].ref")
        self.assertIn("gatilho novo de nível 3 pede 3", achado.mensagem)
        apoio.acusa(self, achados, "T3", "alerta.dominios[4].gatilhos[0].ref")
        self.assertNotIn("principais[0].fontes", [a.caminho for a in achados])   # para a principal, 2 bastam
        self.conferencia["paginas"][-1].update(estado="ok", publicado_em=DIA)    # a 3ª
        self.assertEqual(self.confere(), [])

    def test_item_que_sustenta_gatilho_de_nivel_2_pede_1(self):
        r4 = self.r(3)
        self.troca_por_pagina(r4, 2)
        achado = apoio.acusa(self, self.confere(), "T3", "alerta.dominios[3].gatilhos[0].ref")
        self.assertIn("item que sustenta gatilho pede 1", achado.mensagem)
        self.conferencia["paginas"][-1].update(estado="ok", publicado_em=DIA)
        self.assertEqual(self.confere(), [])

    def test_estado_que_continua_pede_1_e_gatilho_novo_de_nivel_4_pede_3(self):
        arquivo = apoio.Arquivo()

        def crise(rascunho):
            apoio.sem_gatilhos(rascunho)
            apoio.poe_gatilho(rascunho, "conflito.4", "p1")
        arquivo.publica(VESPERA, crise, indicadores=apoio.indicadores_calmos(VESPERA))
        apoio.sem_gatilhos(self.rascunho)
        apoio.poe_gatilho(self.rascunho, "conflito.4", "r6", texto="Segue em 19/11: texto fictício.")
        self.assertEqual(len(self.r(5)["fontes"]), 2)
        self.assertEqual(self.confere(arquivo.historico()), [])                 # continua: 1 basta, e o radar tem 2
        achado = apoio.acusa(self, self.confere(None), "T3", "alerta.dominios[4].gatilhos[0].ref")   # sem histórico é novo
        self.assertIn("gatilho novo de nível 4 pede 3", achado.mensagem)

    def test_maquina_sem_rede(self):
        sem_feed = {"versao": 1, "resumo": {"feeds_ok": 0, "feeds_falhos": 68}, "manchetes": []}
        so_bloqueadas = {"versao": 1, "paginas": [{"url": u, "estado": "bloqueada", "publicado_em": None}
                                                  for u in valida.le_urls(self.urls)]}
        for coleta in (sem_feed, None):
            for conferencia in (so_bloqueadas, None):
                achados = valida.confere_t3(self.rascunho, self.dados, coleta, conferencia)
                caminhos = [a.caminho for a in achados]
                self.assertEqual(apoio.regras(achados), ["T3"])
                self.assertIn("bastidores.modo", caminhos)                               # tem de ser busca
                self.assertIn("alerta.dominios[0].gatilhos[0].ref", caminhos)            # energia.3
                self.assertIn("alerta.dominios[4].gatilhos[0].ref", caminhos)            # conflito.3
                self.assertNotIn("alerta.dominios[3].gatilhos[0].ref", caminhos)         # suprimentos.2 pode
                self.assertFalse([c for c in caminhos if c.endswith(".fontes")])         # as contas não valem
        self.rascunho["bastidores"]["modo"] = "busca"
        self.rascunho["alerta"]["dominios"][0]["gatilhos"] = []
        self.rascunho["alerta"]["dominios"][4]["gatilhos"] = []
        self.assertEqual(valida.confere_t3(self.rascunho, self.dados, None, so_bloqueadas), [])

    def test_uma_pagina_ok_ja_e_rede(self):
        sem_feed = {"versao": 1, "resumo": {"feeds_ok": 0, "feeds_falhos": 68}, "manchetes": []}
        achados = valida.confere_t3(self.rascunho, self.dados, sem_feed, self.conferencia)   # a conferência tem páginas ok
        caminhos = [a.caminho for a in achados]
        self.assertNotIn("bastidores.modo", caminhos)
        self.assertIn("principais[2].fontes", caminhos)   # com rede, as contas valem: e a mesa veio vazia


class TestaT4(ComRascunho):
    """Veículo e endereço: em fonte de veículo do mapa, o site da URL é um dos `sites` do veículo. Estar na mesa
    com o veículo não basta (ESQUEMA, seção 10, T4)."""

    def confere(self):
        return valida.confere_t4(self.rascunho, self.dados, self.coleta)

    def test_a_mesa_nao_basta_vale_o_site(self):
        self.assertEqual(self.confere(), [])
        fonte = self.p(0)["fontes"][0]
        self.assertEqual(fonte["veiculo"], "reuters")
        fonte["url"] = "https://exemplo.invalid/reuters/terminal"   # na mesa com o veículo, fora do site dele
        self.coleta["manchetes"][0]["url"] = fonte["url"]
        self.assertEqual(self.coleta["manchetes"][0]["veiculo"], "reuters")
        achado = apoio.acusa(self, self.confere(), "T4", "principais[0].fontes[0].veiculo")
        self.assertIn("o site 'exemplo.invalid' não é de 'reuters'", achado.mensagem)
        self.assertEqual(valida.confere_t4(self.rascunho, self.dados, None), self.confere())   # a coleta não muda nada

    def test_o_veiculo_da_mesa_nao_decide(self):
        for manchete in self.coleta["manchetes"]:
            if manchete["url"] == self.p(0)["fontes"][0]["url"]:
                manchete["veiculo"] = "bbc"       # na mesa, o endereço veio de outro veículo; o site é da reuters
        self.assertEqual(self.confere(), [])

    def test_pagina_aberta_vale_pelo_site_do_veiculo(self):
        fonte = self.p(0)["fontes"][0]
        self.assertEqual((fonte["veiculo"], self.dados.mapa["reuters"]["sites"]), ("reuters", ["reuters.com"]))
        self.tira_da_mesa(fonte["url"])
        self.assertEqual(self.confere(), [])
        fonte["url"] = "https://exemplo.invalid/reuters/a"
        achado = apoio.acusa(self, self.confere(), "T4", "principais[0].fontes[0].veiculo")
        self.assertIn("o site 'exemplo.invalid' não é de 'reuters'", achado.mensagem)
        self.assertIn("use 'outro', com nome", achado.mensagem)
        for boa in ("https://www.reuters.com/world/a", "http://reuters.com/a", "https://jp.reuters.com/a"):
            fonte["url"] = boa
            self.assertEqual(self.confere(), [], boa)
        for ruim in ("https://reuters.com.exemplo.invalid/a", "https://naoreuters.com/a"):
            fonte["url"] = ruim
            apoio.acusa(self, self.confere(), "T4", "principais[0].fontes[0].veiculo")

    def test_site_dividido_vale_para_os_dois_veiculos(self):
        """ESQUEMA, seção 15, M2: dois veículos podem ter o mesmo site; a T4 aceita o endereço com os dois."""
        divididos = [(v, f["sites"]) for v, f in self.dados.mapa.items()
                     if any(s in o["sites"] for s in f["sites"] for w, o in self.dados.mapa.items() if w != v)]
        self.assertTrue(divididos)
        fonte = self.p(0)["fontes"][0]
        for veiculo, sites in divididos:
            fonte["veiculo"], fonte["url"] = veiculo, "https://%s/exemplo/a" % sites[0]
            self.assertEqual(self.confere(), [], veiculo)

    def test_a_mensagem_diz_de_quem_e_o_site(self):
        fonte = self.p(0)["fontes"][0]
        self.tira_da_mesa(fonte["url"])
        fonte["url"] = "https://www.nytimes.com/2026/11/19/world/a.html"
        achado = apoio.acusa(self, self.confere(), "T4", "principais[0].fontes[0].veiculo")
        self.assertIn("use 'nyt'", achado.mensagem)

    def test_fonte_outro_e_veiculo_fora_do_mapa_nao_sao_desta_regra(self):
        self.tira_da_mesa(*[m["url"] for m in self.coleta["manchetes"]])
        for item in itens(self.rascunho):
            for fonte in item["fontes"]:
                fonte["veiculo"] = "outro" if fonte["veiculo"] != "reuters" else "saiu_do_mapa"
        self.assertEqual(self.confere(), [])


class TestaT5(ComRascunho):
    """`omite` só em ataque cuja URL está em urls.txt."""

    def test_omite_de_pagina_que_nao_foi_aberta(self):
        com_omite = [(i, a) for i in itens(self.rascunho) for a in ataques(i) if "omite" in a]
        self.assertGreaterEqual(len(com_omite), 3)
        self.assertEqual(valida.confere_t5(self.rascunho, self.urls), [])
        url = self.p(0)["ataques"][0]["url"]
        self.assertIn("omite", self.p(0)["ataques"][0])
        self.urls = "\n".join(u for u in valida.le_urls(self.urls) if u != url)   # só a mesa trouxe a página
        achado = apoio.acusa(self, valida.confere_t5(self.rascunho, self.urls), "T5", "principais[0].ataques[0].omite")
        self.assertIn("urls.txt", achado.mensagem)
        self.assertEqual(len(valida.confere_t5(self.rascunho, self.urls)), 1)

    def test_sem_urls_todo_omite_e_recusado_e_sem_omite_nada_e_cobrado(self):
        self.assertEqual(len(valida.confere_t5(self.rascunho, None)),
                         len([a for i in itens(self.rascunho) for a in ataques(i) if "omite" in a]))
        for item in itens(self.rascunho):
            for ataque in ataques(item):
                ataque.pop("omite", None)
        self.assertEqual(valida.confere_t5(self.rascunho, None), [])

    def test_ataque_do_radar_tambem(self):
        self.r(4)["ataque"]["omite"] = "Texto fictício. Não diz quanto custa."
        apoio.acusa(self, valida.confere_t5(self.rascunho, self.urls), "T5", "radar[4].ataque.omite")
        url = self.r(4)["ataque"]["url"]
        site, caminho = url[len("https://"):].split("/", 1)
        self.urls += "https://%s/%s\n" % (site.upper(), caminho.upper())
        apoio.acusa(self, valida.confere_t5(self.rascunho, self.urls), "T5", "radar[4].ataque.omite")   # o caminho não muda de caixa
        self.urls += "https://%s/%s/\n" % (site.upper(), caminho)
        self.assertEqual(valida.confere_t5(self.rascunho, self.urls), [])


if __name__ == "__main__":
    unittest.main()
