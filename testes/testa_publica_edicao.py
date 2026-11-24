#!/usr/bin/env python3
"""Testes do `publica.py edicao` (CONTRATO, seção 4.2): completa, valida e publica o rascunho.

Rode da raiz do repositório: python3 -B testes/testa_publica_edicao.py
O rascunho de teste vem da edição de exemplo, só com os campos do agente; a pasta de trabalho (coleta.json,
indicadores.json, urls.txt, conferencia.json) é montada para ser coerente com as regras T.
"""
import json
import os
import shutil
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "publica"))
import apoio  # noqa: E402

DIA = apoio.DIA
AMANHA = apoio.soma(DIA, 1)
DO_DIA = ["edicoes/%s.json" % DIA, "edicoes/%s.md" % DIA, "edicoes/indice.json", "feed.xml"]
# CONTRATO, seção 4.2, passo 8: os domínios pelo id (cambio, sem acento); singular só com 1.
VEREDITO = ("OK edição %s publicada: nível 3 TENSÃO (energia 3, alimentos 1, cambio 1, suprimentos 2, conflito 3), "
            "3 principais, 6 radar, 2 vetores, 0 players novos" % DIA)


def com_player(novo):
    novo["novos_players"] = [apoio.player_novo()]


class TestaAPublicacao(apoio.Bancada):
    def test_rascunho_valido_vira_edicao_que_passa_no_validador(self):
        base = self.inicia_git()
        novo = self.publica_o_dia()
        self.assertEqual(self.linhas[-1], VEREDITO)
        self.assertIn("gravado: %s" % ", ".join(DO_DIA + ["dados/vetores.json"]), self.linhas)
        self.assertEqual(self.mudancas(), sorted([("M", "dados/vetores.json")] + [("??", caminho) for caminho in DO_DIA]))
        self.assertValido("--base", base, "--dia", DIA)

        texto = self.texto("edicoes/%s.json" % DIA)
        edicao = json.loads(texto)
        self.assertEqual(texto, apoio.comum.json_texto(edicao), "recuo de 2, acentos legíveis, quebra de linha no fim")
        self.assertNotIn("\\u", texto)
        self.assertFalse(texto.encode("utf-8").startswith(b"\xef\xbb\xbf"))
        self.assertLess(len(texto.encode("utf-8")), 60 * 1024)
        # o que o agente escreveu fica como veio; o resto é calculado
        self.assertEqual(apoio.so_do_agente(edicao), novo)
        self.assertEqual(list(edicao), [chave for chave in apoio.valida.ORDEM["raiz"] if chave != "exemplo"],
                         "chaves na ordem das tabelas do ESQUEMA")
        self.assertEqual((edicao["versao"], edicao["data"], edicao["gerada_em"]), (1, DIA, apoio.agora(DIA)))
        self.assertEqual(list(edicao["alerta"]), list(apoio.valida.ORDEM["alerta"]))
        self.assertEqual((edicao["alerta"]["nivel"], edicao["alerta"]["tendencia"]), (3, "estavel"))
        energia, alimentos = edicao["alerta"]["dominios"][:2]
        self.assertEqual(list(energia), list(apoio.valida.ORDEM["dominio"]))
        self.assertEqual((energia["nivel"], energia["tendencia"], energia["desde"], energia["sem_preco"]),
                         (3, "estavel", DIA, []))
        do_dia = apoio.indicadores_do_dia(DIA)
        self.assertEqual(energia["gatilhos"][0], do_dia["gatilhos"][0], "o gatilho de preço entra na frente")
        self.assertEqual([g["ref"] for g in energia["gatilhos"]], ["brent", "p1"])
        self.assertEqual(alimentos["sem_preco"], ["milho"], "o milho veio sem a variação de 7 dias")
        self.assertEqual(edicao["indicadores"], do_dia["indicadores"])
        mapa = apoio.dados().mapa
        for item in apoio.itens(edicao):
            self.assertEqual(list(item), [c for c in apoio.valida.ORDEM["principal" if "ataques" in item else "radar"]
                                          if c in item])
            for ataque in apoio.ataques(item):
                self.assertEqual(ataque["lado"], mapa[ataque["veiculo"]]["lado"])
                self.assertEqual(list(ataque), [c for c in apoio.valida.ORDEM["ataque"] if c in ataque])
        self.assertEqual([item["id"] for item in apoio.itens(edicao) if item.get("conflito_de_interesse") is True],
                         ["p2", "r1", "r2", "r3"], "a marca é ligada nos itens de IA")
        self.assertEqual([(l["partido"], l["saldo"], l["narrativa"]) for l in edicao["placar_do_dia"]],
                         [("ordem_global", 4, 1), ("independentes", 2, 0), ("soberanistas", 0, 2),
                          ("eixo_revisionista", 0, 1), ("centrao", -1, 0), ("centro_atlantico", -2, 0),
                          ("bancada_talento", -2, 0)])
        bastidores = edicao["bastidores"]
        self.assertEqual((bastidores["veiculos_consultados"], bastidores["feeds_ok"], bastidores["feeds_falhos"]),
                         (19, 61, 7))
        self.assertEqual(list(bastidores), list(apoio.valida.ORDEM["bastidores"]))

    def test_os_registros_e_os_arquivos_do_dono(self):
        """Acrescenta em vetores.json e players.json; nunca grava veiculos.json, regua.json nem indicadores.json."""
        do_dono = ("dados/veiculos.json", "dados/regua.json", "dados/indicadores.json")
        antes = dict((nome, (os.stat(self.caminho(nome)).st_mtime_ns, self.texto(nome))) for nome in do_dono)
        players_antes, vetores_antes = self.le("dados/players.json"), self.le("dados/vetores.json")
        self.publica_o_dia(muda=com_player)
        self.assertTrue(self.linhas[-1].endswith("2 vetores, 1 player novo"), self.linhas[-1])
        for nome in do_dono:
            self.assertEqual((os.stat(self.caminho(nome)).st_mtime_ns, self.texto(nome)), antes[nome], nome)
        edicao = self.le("edicoes/%s.json" % DIA)

        vetores = self.le("dados/vetores.json")
        self.assertEqual(dict(vetores, vetores=[]), vetores_antes, "o resto do arquivo fica como estava")
        ue, google = vetores["vetores"]
        vetor = edicao["principais"][0]["vetores"][0]
        self.assertEqual(ue, {"id": "%s_p1_ue" % DIA, "data": DIA, "item": "p1", "player": "ue", "de": "centro_atlantico",
                              "para": "soberanistas", "forca": 2, "tema": "clima", "porque": vetor["porque"],
                              "url": vetor["url"]})
        self.assertEqual(list(ue), ["id", "data", "item", "player", "de", "para", "forca", "tema", "porque", "url"])
        self.assertEqual((google["id"], google["de"], google["conflito_de_interesse"]),
                         ("%s_r2_google" % DIA, "bancada_talento", True), "vetor de item com a marca leva a marca")
        self.assertEqual(list(google)[-1], "conflito_de_interesse")

        players = self.le("dados/players.json")
        self.assertEqual(players["players"][:-1], players_antes["players"], "os players antigos, iguais e na ordem")
        self.assertEqual(players["atualizado_em"], DIA)
        novo = players["players"][-1]
        self.assertEqual(novo, dict(edicao["novos_players"][0], origem="rotina", incluido_em=DIA))
        self.assertEqual(list(novo)[-2:], ["origem", "incluido_em"])
        self.assertEqual(list(novo["dna"]), apoio.dados().temas)
        for nome in ("dados/players.json", "dados/vetores.json"):
            self.assertEqual(self.texto(nome), apoio.comum.json_texto(self.le(nome)))
        self.assertValido("--dia", DIA)

    def test_sem_vetor_nem_player_os_registros_nem_sao_tocados(self):
        marcas = dict((nome, os.stat(self.caminho(nome)).st_mtime_ns) for nome in ("dados/players.json", "dados/vetores.json"))
        self.publica_o_dia(muda=apoio.sem_vetores)
        self.assertIn("gravado: %s" % ", ".join(DO_DIA), self.linhas)
        for nome, marca in marcas.items():
            self.assertEqual(os.stat(self.caminho(nome)).st_mtime_ns, marca, nome)

    def test_dna_fora_de_ordem_e_regravado_na_ordem_da_regua(self):
        """A ordem das chaves de `dna` e de `dna_fontes` no rascunho não é motivo de recusa: a edição e o registro
        saem com os temas na ordem da régua (ESQUEMA, seção 0: as chaves são gravadas na ordem das tabelas)."""
        def avesso(novo):
            novo_player = apoio.player_novo()
            novo_player["dna"] = dict(reversed(list(novo_player["dna"].items())))
            novo_player["dna_fontes"] = dict(reversed(list(novo_player["dna_fontes"].items())))
            novo["novos_players"] = [novo_player]
        self.publica_o_dia(muda=avesso)
        temas = [tema["id"] for tema in apoio.le(os.path.join(apoio.DADOS, "regua.json"))["temas"]]
        publicado = self.le("edicoes/%s.json" % DIA)["novos_players"][0]
        registrado = self.le("dados/players.json")["players"][-1]
        for player in (publicado, registrado):
            self.assertEqual(list(player["dna"]), temas)
            self.assertEqual(list(player["dna_fontes"]), [tema for tema in temas if tema in player["dna_fontes"]])
        self.assertValido("--dia", DIA)

    def test_campo_calculado_que_vem_no_rascunho_e_trocado_sem_erro(self):
        self.inicia_git()
        self.publica_o_dia()
        limpa = apoio.conteudos(self.raiz)

        def suja(novo):
            novo.update(versao=7, gerada_em="ontem", indicadores=[{"id": "inventado", "valor": "caro"}])
            novo["alerta"].update(nivel=5, tendencia="descendo")
            for dominio in novo["alerta"]["dominios"]:
                dominio.update(nivel=5, tendencia="subindo", desde="2020-01-01", sem_preco=["inventado"])
            novo["alerta"]["dominios"][0]["gatilhos"].insert(
                0, {"criterio": "energia.4", "ref": "brent", "texto": "Texto fictício. Gatilho de preço escrito à mão."})
            for item in apoio.itens(novo):
                for ataque in apoio.ataques(item):
                    ataque["lado"] = "centrao"
                if item["categoria"] == "ia":
                    item["conflito_de_interesse"] = False
            novo["placar_do_dia"].reverse()
            for linha in novo["placar_do_dia"]:
                linha.update(saldo=99, narrativa=-9)
            novo["bastidores"].update(veiculos_consultados=999, feeds_ok=0, feeds_falhos=0)
        self.publica_o_dia(muda=suja)
        self.assertEqual(self.linhas[-1], VEREDITO)
        self.assertEqual(apoio.conteudos(self.raiz), limpa, "a edição sai igual, byte a byte, à do rascunho limpo")

    def test_mesma_entrada_mesmos_bytes_em_outra_raiz(self):
        self.publica_o_dia(muda=com_player)
        primeira = apoio.conteudos(self.raiz)
        shutil.rmtree(self.raiz)
        os.makedirs(self.caminho("dados"))
        for nome in apoio.ARQUIVOS_DE_DADOS:
            shutil.copy(os.path.join(apoio.DADOS, nome + ".json"), self.caminho("dados"))
        self.publica_o_dia(muda=com_player)
        self.assertEqual(apoio.conteudos(self.raiz), primeira)

    def test_simula_nao_grava(self):
        self.prepara(muda=com_player)
        fotos = self.fotos()
        codigo, linhas = self.publica("edicao", "--simula", "--url-base", apoio.BASE)
        self.assertEqual(codigo, 0, linhas)
        self.assertEqual(self.fotos(), fotos, "nem a raiz nem a pasta de trabalho mudam")
        self.assertIn("simulação: gravaria %s" % ", ".join(DO_DIA + ["dados/vetores.json", "dados/players.json"]), linhas)
        self.assertIn("níveis calculados: nível 3 TENSÃO (energia 3, alimentos 1, cambio 1, suprimentos 2, conflito 3)",
                      linhas)
        self.assertTrue(linhas[-1].startswith("OK simulação: a edição %s passa, e nada foi gravado" % DIA), linhas[-1])
        # com erro, a simulação diz o erro e os níveis, e também não grava
        self.prepara(muda=lambda novo: novo["radar"][4].update(confianca="alta"))
        fotos = self.fotos()
        linhas = self.assertFALHA(self.publica("edicao", "--simula"))
        self.assertTrue(any(linha.startswith("níveis calculados: nível 3") for linha in linhas))
        self.assertEqual(self.fotos(), fotos)

    def test_o_veredito_conta_o_que_saiu(self):
        def menor(novo):
            com_player(novo)
            novo["radar"][1]["vetores"] = []
        self.publica_o_dia(muda=menor)
        self.assertTrue(self.linhas[-1].endswith("3 principais, 6 radar, 1 vetor, 1 player novo"), self.linhas[-1])


class TestaOsErros(apoio.Bancada):
    """Com erro, nada do repositório muda, e cada erro vem numa linha, com a regra, o caminho e o conserto."""

    def recusa(self, regras=None, muda=None, depois=None, **trabalho):
        """Prepara, publica e espera FALHA. `depois()` mexe na pasta de trabalho antes da publicação."""
        self.prepara(muda=muda, **trabalho)
        if depois is not None:
            depois()
        foto = apoio.fotografa(self.raiz)
        linhas = self.assertFALHA(self.publica("edicao", "--url-base", apoio.BASE))
        self.assertEqual(apoio.fotografa(self.raiz), foto, "com erro, nenhum arquivo do repositório muda")
        erros = [linha for linha in linhas if linha.startswith("ERRO ")]
        for erro in erros:
            self.assertRegex(erro, r"^ERRO [A-Z]+[0-9]*[a-f]? \S+: .+[.?!]$")
        if regras is not None:
            self.assertEqual(sorted(set(erro.split()[1] for erro in erros)), sorted(regras), "\n".join(linhas))
            self.assertRegex(linhas[-1], r"^FALHA %d erros?, [0-9]+ avisos?$" % len(erros))
        return linhas

    def muda_trabalho(self, nome, funcao):
        objeto = apoio.le(self.no_trabalho(nome))
        funcao(objeto)
        apoio.grava(self.no_trabalho(nome), objeto)

    def test_erro_de_regra_r_nao_grava_nada(self):
        linhas = self.recusa(["R08"], lambda novo: novo["radar"][4].update(confianca="alta"))
        self.assertEqual(linhas[-2:], ["ERRO R08 radar[4].confianca: é 'alta', o teto pelas fontes é 'media'. Troque para "
                                       "'media' ou acrescente fonte do outro campo.", "FALHA 1 erro, 0 avisos"])
        self.assertFalse(self.existe("edicoes"))
        self.assertFalse(self.existe("feed.xml"))

    def test_varios_erros_uma_linha_cada(self):
        def estraga(novo):
            novo["resumo"] = "x" * 241
            novo["principais"][0]["realmente"] = "Curto demais."
            novo["radar"][0]["titulo"] = "Título com <b>marca</b>"
            del novo["bastidores"]["limites"]
        linhas = self.recusa(["R00", "R17", "R23"], estraga)
        self.assertEqual(linhas[-1], "FALHA 4 erros, 0 avisos")

    def test_url_que_nao_foi_vista(self):
        """Só a T1: o endereço está no site do veículo, e a T4 não depende de estar na coleta (ESQUEMA, T4)."""
        def tira_da_mesa():
            self.muda_trabalho("coleta.json", lambda coleta: coleta["manchetes"].pop())
        linhas = self.recusa(["T1"], depois=tira_da_mesa)
        self.assertTrue(any(linha.startswith("ERRO T1 radar[5].fontes[1].url: ") and "urls.txt" in linha for linha in linhas))

    def test_data_que_a_pagina_desmente(self):
        decreto = "https://diario.oficial.exemplo.invalid/decreto-1-2026"

        def outra_data():
            def mexe(conferencia):
                for pagina in conferencia["paginas"]:
                    if pagina["url"] == decreto:
                        pagina["publicado_em"] = "2025-11-19"
            self.muda_trabalho("conferencia.json", mexe)
        linhas = self.recusa(["T3"], depois=outra_data)
        self.assertIn("ERRO T3 principais[0].fontes[5].publicado_em: é %s, a página diz 2025-11-19. Corrija a data; se "
                      "sair da janela, troque a fonte." % apoio.soma(DIA, -1), linhas)

    def test_pagina_que_nao_existe_e_omite_de_pagina_fechada(self):
        def pagina_morta():
            self.muda_trabalho("conferencia.json", lambda c: c["paginas"][0].update(estado="erro"))
        self.recusa(["T3"], depois=pagina_morta)
        self.recusa(["T1", "T5"], urls="# nenhuma página aberta\n", conferencia=None)

    def test_data_do_rascunho_que_nao_e_a_do_dia(self):
        linhas = self.recusa(muda=lambda novo: novo.update(data=AMANHA))
        erros = [linha for linha in linhas if linha.startswith("ERRO ") and " data: " in linha]
        self.assertEqual(len(erros), 1, "a data errada é acusada uma vez só")
        self.assertTrue(erros[0].startswith("ERRO T2 data: é '%s', e o dia desta execução é %s" % (AMANHA, DIA)))

    def test_exemplo_e_estado_falha_nao_entram_pelo_rascunho(self):
        linhas = self.recusa(muda=lambda novo: novo.update(exemplo=True))
        self.assertTrue(any(linha.startswith("ERRO T2 exemplo: ") for linha in linhas))
        linhas = self.recusa(muda=lambda novo: novo.update(estado="falha"))
        self.assertTrue(any(linha.startswith("ERRO T2 estado: ") and "publica.py falha" in linha for linha in linhas))

    def test_sem_os_arquivos_das_outras_ferramentas(self):
        linhas = self.recusa(coleta=None, indicadores=None, conferencia=None)
        for nome, conserto in (("indicadores.json", "Rode indicadores.py."), ("coleta.json", "Rode coleta.py."),
                               ("conferencia.json", "Rode coleta.py --confere.")):
            aviso = [linha for linha in linhas if linha.startswith("aviso: %s não existe: " % nome)]
            self.assertEqual(len(aviso), 1, nome)
            self.assertTrue(aviso[0].endswith(conserto), aviso[0])
        self.assertLess(linhas.index(aviso[0]), [i for i, linha in enumerate(linhas) if linha.startswith("ERRO ")][0],
                        "os avisos dos arquivos vêm antes dos erros")

    def test_sem_indicadores_a_edicao_sai_com_a_lista_vazia(self):
        self.publica_o_dia(indicadores=None)
        self.assertIn("aviso: indicadores.json não existe: a edição sai sem indicadores, e os domínios com preço ficam "
                      "sem dado. Rode indicadores.py.", self.linhas)
        edicao = self.le("edicoes/%s.json" % DIA)
        self.assertEqual(edicao["indicadores"], [])
        self.assertEqual([d["sem_preco"] for d in edicao["alerta"]["dominios"]],
                         [["brent"], ["trigo", "milho", "soja"], ["usd_brl"], [], []])
        self.assertEqual([g["ref"] for g in edicao["alerta"]["dominios"][0]["gatilhos"]], ["p1"])
        self.assertValido("--dia", DIA)

    def test_arquivo_de_apoio_de_outro_dia_ou_quebrado_fica_de_fora(self):
        self.publica_o_dia(indicadores=apoio.indicadores_do_dia(apoio.soma(DIA, -1)))
        self.assertTrue(any(linha.startswith("aviso: indicadores.json é de %s, e o dia da edição é %s: "
                                             % (apoio.soma(DIA, -1), DIA)) for linha in self.linhas), self.linhas)
        self.assertEqual(self.le("edicoes/%s.json" % DIA)["indicadores"], [])
        for nome, conteudo in (("indicadores.json", "{quebrado"), ("coleta.json", "[]"), ("conferencia.json", "nada")):
            self.prepara()
            apoio.grava(self.no_trabalho(nome), conteudo)
            codigo, linhas = self.publica("edicao", "--simula")
            self.assertTrue(any(linha.startswith("aviso: %s " % nome) for linha in linhas), linhas)
            self.assertFalse(any("interna" in linha for linha in linhas), linhas)

    def test_rascunho_que_falta_ou_nao_e_json(self):
        foto = apoio.fotografa(self.raiz)
        linhas = self.assertFALHA(self.publica("edicao"))
        self.assertEqual(len(linhas), 1)
        self.assertTrue(linhas[0].startswith("FALHA rascunho.json: o arquivo não existe em %s" % self.trabalho), linhas)
        casos = (
            ('{\n  "data": "%s",\n  "estado": "completa"\n  "resumo": "x"\n}' % DIA, "linha 4, coluna 3: ", "falta vírgula"),
            ('{\n  // o `dia` do contexto\n  "data": "%s"\n}' % DIA, "linha 2, coluna 3: ", "a linha começa com //"),
            ('{"data": "%s",}' % DIA, "linha 1, coluna 23: ", "vírgula sobrando"),
            ('{"resumo": "linha um\nlinha dois"}', "linha 1, coluna 21: ", "numa linha só"),
            ('{"resumo": "sem fim}', "linha 1, coluna 12: ", "aspas do fim"),
            ("", "linha 1, coluna 1: ", "valor"),
            (b"\xef\xbb\xbf{}", "linha 1, coluna 1: ", "BOM"),
            ('{"n": NaN}', "linha 1, coluna 7: ", "NaN"),
        )
        for conteudo, onde, trecho in casos:
            apoio.grava(self.no_trabalho("rascunho.json"), conteudo)
            linhas = self.assertFALHA(self.publica("edicao"))
            self.assertEqual(len(linhas), 1, linhas)
            self.assertTrue(linhas[0].startswith("FALHA rascunho.json: " + onde), linhas[0])
            self.assertIn(trecho, linhas[0])
        for conteudo in ("[]", '"texto"', "null", "7"):
            apoio.grava(self.no_trabalho("rascunho.json"), conteudo)
            linhas = self.assertFALHA(self.publica("edicao"))
            self.assertTrue(linhas[-1].startswith("FALHA rascunho.json: deveria ser um objeto"), linhas)
        self.assertEqual(apoio.fotografa(self.raiz), foto)

    def test_rascunho_torto_nunca_vira_falha_interna(self):
        for conteudo in ({}, {"data": DIA}, {"data": DIA, "alerta": [], "principais": {}, "radar": "x", "bastidores": 3},
                         {"data": DIA, "estado": "completa", "alerta": {"dominios": [1, None, {"id": []}]},
                          "principais": [None, 7, {"id": "p1", "ataques": [None], "fontes": "x", "vetores": [3]}],
                          "radar": [{"ataque": 5, "placar": [[]]}], "placar_do_dia": [None, {"partido": []}],
                          "novos_players": [None], "errata": [3], "respostas": [{}], "bastidores": {"candidatos": [1]}}):
            apoio.monta_trabalho(self.trabalho, apoio.comum.json_texto(conteudo), DIA)
            foto = apoio.fotografa(self.raiz)
            for argumentos in ([], ["--simula"], ["--corta", "r1"]):
                # Nenhum destes rascunhos tem item r1: o --corta para em erro de uso (código 2).
                linhas = self.assertFALHA(self.publica("edicao", *argumentos), 2 if argumentos[:1] == ["--corta"] else 1)
                self.assertFalse(any("interna" in linha for linha in linhas), linhas)
            self.assertEqual(apoio.fotografa(self.raiz), foto)

    def test_dois_vetores_do_mesmo_player_no_mesmo_item(self):
        """O id do vetor é data, item e player: o segundo teria o id do primeiro, e por isso é recusado."""
        def dobra(novo):
            outro = dict(novo["principais"][0]["vetores"][0], para="eixo_revisionista", tema="ordem")
            novo["principais"][0]["vetores"].append(outro)
            novo["radar"][1]["vetores"] = []
        linhas = self.recusa(["R11"], dobra)
        self.assertTrue(linhas[-2].startswith("ERRO R11 principais[0].vetores[1].player: 'ue' já tem outro vetor neste item"))

    def test_metade_de_caractere_no_texto(self):
        novo = apoio.rascunho()
        novo["radar"][2]["fato"] += " " + chr(0xD83D)
        apoio.monta_trabalho(self.trabalho, json.dumps(novo), DIA)
        apoio.monta_trabalho(self.trabalho, apoio.rascunho(), DIA)
        apoio.grava(self.no_trabalho("rascunho.json"), json.dumps(novo))
        foto = apoio.fotografa(self.raiz)
        linhas = self.assertFALHA(self.publica("edicao"))
        self.assertEqual(apoio.fotografa(self.raiz), foto)
        self.assertEqual([linha.split(":")[0] for linha in linhas if linha.startswith("ERRO ")], ["ERRO R17 radar[2].fato"])

    def test_relogio_fora_do_dia_da_edicao(self):
        self.prepara()
        linhas = self.assertFALHA(self.publica("edicao", agora=apoio.agora(apoio.soma(DIA, 3))))
        self.assertTrue(any(linha.startswith("ERRO R00 gerada_em: ") for linha in linhas), linhas)
        self.assertTrue(any(linha.startswith("aviso: o relógio marca ") and "confira o --dia" in linha for linha in linhas))

    def test_dados_ou_edicao_antiga_que_nao_servem(self):
        self.prepara()
        original = self.texto("dados/veiculos.json")
        self.grava("dados/veiculos.json", "{quebrado")
        linhas = self.assertFALHA(self.publica("edicao"))
        self.assertIn("dados/veiculos.json", linhas[-1])
        self.assertTrue(linhas[0].startswith("ERRO ARQUIVO dados/veiculos.json: linha 1, coluna 2"), linhas)
        self.grava("dados/veiculos.json", original)
        self.grava("edicoes/2026-11-01.json", '{"data": ')
        foto = apoio.fotografa(self.raiz)
        linhas = self.assertFALHA(self.publica("edicao"))
        self.assertIn("edicoes/2026-11-01.json", linhas[-1])
        self.assertEqual(apoio.fotografa(self.raiz), foto)

    def test_tudo_ou_nada_quando_a_gravacao_falha_no_meio(self):
        """Uma pasta no lugar do feed.xml derruba a troca do quarto arquivo: os três primeiros são desfeitos."""
        os.makedirs(self.caminho("feed.xml", "pasta"))
        self.prepara()
        antes = apoio.conteudos(self.raiz), sorted(apoio.fotografa(self.raiz))
        linhas = self.assertFALHA(self.publica("edicao"))
        self.assertTrue(linhas[-1].startswith("FALHA interna: "), linhas[-1])
        self.assertEqual((apoio.conteudos(self.raiz), sorted(apoio.fotografa(self.raiz))), antes,
                         "nem edição, nem índice, nem registro, nem arquivo temporário: nada ficou pela metade")


class TestaOCorte(apoio.Bancada):
    """--corta (CONTRATO, seção 4.2): tira os itens, conserta o que dependia deles e segue para a publicação."""

    def rascunho_no_disco(self):
        return apoio.le(self.no_trabalho("rascunho.json"))

    def test_renumera_acerta_ref_e_vira_reduzida(self):
        def cita(novo):
            novo["bastidores"]["limites"] = "O item r5 ficou sem segunda fonte, e o r2 depende de um comunicado só."
        self.prepara(muda=cita)
        linhas = self.assertOK(self.publica("edicao", "--corta", "r2", "--url-base", apoio.BASE))
        for esperada in (
                "cortado r2: Google adia modelo fictício até auditoria externa",
                "renumerado: r3 virou r2, r4 virou r3, r5 virou r4, r6 virou r5",
                "gatilho de suprimentos acertado: ref r4 virou r3",
                "estado: completa virou reduzida, porque a contagem da completa deixou de fechar. Diga em "
                "bastidores.limites o que ficou de fora.",
                "aviso: bastidores.limites cita r2, que foi cortado. O texto não foi reescrito: confira.",
                "aviso: bastidores.limites cita r5, que agora é r4. O texto não foi reescrito: confira.",
                "rascunho.json regravado, já sem r2"):
            self.assertIn(esperada, linhas)
        self.assertTrue(linhas[-1].endswith("3 principais, 5 radar, 1 vetor, 0 players novos"), linhas[-1])
        novo = self.rascunho_no_disco()
        self.assertEqual([item["id"] for item in novo["radar"]], ["r1", "r2", "r3", "r4", "r5"])
        self.assertEqual(novo["estado"], "reduzida")
        self.assertEqual(novo["alerta"]["dominios"][3]["gatilhos"][0]["ref"], "r3")
        self.assertEqual(novo["bastidores"]["limites"], "O item r5 ficou sem segunda fonte, e o r2 depende de um comunicado só.")
        edicao = self.le("edicoes/%s.json" % DIA)
        self.assertEqual((edicao["estado"], len(edicao["radar"])), ("reduzida", 5))
        self.assertEqual(edicao["radar"][2]["titulo"], apoio.rascunho()["radar"][3]["titulo"], "o r4 de antes é o r3")
        self.assertEqual([entrada["id"] for entrada in self.le("dados/vetores.json")["vetores"]], ["%s_p1_ue" % DIA])
        self.assertValido("--dia", DIA)

    def test_tira_gatilho_orfao_e_partido_sem_linha(self):
        self.prepara()
        linhas = self.assertOK(self.publica("edicao", "--corta", "r4,r6", "--url-base", apoio.BASE))
        for esperada in ("cortado r4: Seguradoras fictícias anunciam fim da cobertura no Estreito de Exemplo",
                         "renumerado: r5 virou r4",
                         "gatilho tirado de suprimentos: suprimentos.2 apontava para r4, que foi cortado",
                         "placar_do_dia: saiu independentes, que ficou sem linha em placar nenhum",
                         "placar_do_dia: saiu centrao, que ficou sem linha em placar nenhum",
                         "rascunho.json regravado, já sem r4, r6"):
            self.assertIn(esperada, linhas)
        edicao = self.le("edicoes/%s.json" % DIA)
        self.assertEqual((edicao["estado"], [item["id"] for item in edicao["radar"]]), ("reduzida", ["r1", "r2", "r3", "r4"]))
        suprimentos = edicao["alerta"]["dominios"][3]
        self.assertEqual((suprimentos["nivel"], suprimentos["gatilhos"]), (1, []))
        self.assertEqual([linha["partido"] for linha in edicao["placar_do_dia"]],
                         ["ordem_global", "soberanistas", "eixo_revisionista", "centro_atlantico", "bancada_talento"])
        self.assertTrue(linhas[-1].startswith("OK edição %s publicada: nível 3 TENSÃO (energia 3, alimentos 1, cambio 1, "
                                              "suprimentos 1, conflito 3), 3 principais, 4 radar" % DIA), linhas[-1])
        self.assertValido("--dia", DIA)

    def test_corta_principal(self):
        self.prepara(muda=com_player)
        linhas = self.assertOK(self.publica("edicao", "--corta", "p1", "--url-base", apoio.BASE))
        for esperada in ("renumerado: p2 virou p1, p3 virou p2",
                         "gatilho tirado de energia: energia.3 apontava para p1, que foi cortado",
                         "gatilho tirado de conflito: conflito.3 apontava para p1, que foi cortado",
                         "placar_do_dia: saiu centro_atlantico, que ficou sem linha em placar nenhum",
                         "aviso: novos_players[0].justificativa cita p1, que foi cortado. O texto não foi reescrito: confira.",
                         "aviso: bastidores.candidatos[0].motivo cita p1, que foi cortado. O texto não foi reescrito: confira."):
            self.assertIn(esperada, linhas)
        edicao = self.le("edicoes/%s.json" % DIA)
        self.assertEqual((edicao["estado"], [item["id"] for item in edicao["principais"]]), ("reduzida", ["p1", "p2"]))
        self.assertEqual([d["nivel"] for d in edicao["alerta"]["dominios"]], [2, 1, 1, 2, 1], "energia fica com o preço")
        self.assertValido("--dia", DIA)

    def test_id_que_o_rascunho_nao_tem(self):
        """CONTRATO, seção 4.2, --corta: id que o rascunho não tem é erro de uso (código 2), numa linha só; id que
        aparece em dois itens é defeito do rascunho (código 1). Nos dois casos nada é cortado nem gravado."""
        self.prepara()
        fotos = self.fotos()
        linhas = self.assertFALHA(self.publica("edicao", "--corta", "r9"), 2)
        self.assertEqual(len(linhas), 1, linhas)
        self.assertTrue(linhas[-1].startswith("FALHA uso: --corta: o rascunho não tem o item r9 (os ids dele: p1, p2, "
                                              "p3, r1"), linhas[-1])
        self.assertEqual(self.fotos(), fotos, "nada foi cortado nem gravado")
        linhas = self.assertFALHA(self.publica("edicao", "--corta", "r2,r9", "--simula"), 2)
        self.assertEqual(self.fotos(), fotos, "um id que falta segura o corte inteiro")
        self.prepara(muda=lambda novo: novo["radar"][2].update(id="r2"))
        fotos = self.fotos()
        linhas = self.assertFALHA(self.publica("edicao", "--corta", "r2"))
        self.assertIn("tem mais de um com o item r2", linhas[-1])
        self.assertEqual(self.fotos(), fotos)

    def test_com_simula_o_rascunho_nao_e_regravado(self):
        self.prepara()
        fotos = self.fotos()
        linhas = self.assertOK(self.publica("edicao", "--corta", "r2", "--simula"))
        self.assertIn("simulação: o rascunho.json não foi regravado", linhas)
        self.assertIn("cortado r2: Google adia modelo fictício até auditoria externa", linhas)
        self.assertEqual(self.fotos(), fotos)

    def test_o_corte_fica_mesmo_quando_a_edicao_ainda_nao_passa(self):
        """O passo 2 vem antes da conferência: o rascunho é regravado, e os erros já falam dos ids novos."""
        self.prepara(muda=lambda novo: novo["radar"][4].update(confianca="alta"))
        foto = apoio.fotografa(self.raiz)
        linhas = self.assertFALHA(self.publica("edicao", "--corta", "r2"))
        self.assertTrue(any(linha.startswith("ERRO R08 radar[3].confianca: ") for linha in linhas), linhas)
        self.assertEqual(apoio.fotografa(self.raiz), foto)
        self.assertEqual([item["id"] for item in self.rascunho_no_disco()["radar"]], ["r1", "r2", "r3", "r4", "r5"])
        linhas = self.assertOK(self.publica("edicao", "--corta", "r4", "--url-base", apoio.BASE))
        self.assertTrue(linhas[-1].endswith("3 principais, 4 radar, 1 vetor, 0 players novos"), linhas[-1])

    def test_a_funcao_corta_nao_mexe_no_que_recebeu(self):
        original = apoio.rascunho()
        copia = json.loads(json.dumps(original))
        novo, relato = apoio.publica.corta(original, ["r1"])
        self.assertEqual(original, copia)
        self.assertEqual(len(novo["radar"]), 5)
        self.assertEqual(novo["estado"], "completa", "o estado é o validador que decide, no passo seguinte")


class TestaOQueJaFoiPublicado(apoio.Bancada):
    """CONTRATO, seção 4.2, passo 3: "já publicado" se decide pelo commit HEAD; sem git na raiz, vale o disco."""

    def test_republicacao_no_mesmo_dia_refaz_os_registros_sem_duplicar(self):
        base = self.inicia_git()
        self.publica_o_dia(muda=com_player)
        self.assertEqual(len(self.le("dados/players.json")["players"]), 31)
        primeira = apoio.conteudos(self.raiz)
        self.publica_o_dia(muda=com_player)
        self.assertEqual(apoio.conteudos(self.raiz), primeira, "publicar de novo o mesmo rascunho não muda nada")
        self.assertEqual([entrada["id"] for entrada in self.le("dados/vetores.json")["vetores"]],
                         ["%s_p1_ue" % DIA, "%s_r2_google" % DIA])
        self.assertEqual([p["id"] for p in self.le("dados/players.json")["players"]].count("republica_exemplo"), 1)
        self.assertValido("--base", base, "--dia", DIA)

        # o rascunho novo já não traz o player nem o vetor do Google: os dois saem dos registros
        self.publica_o_dia(muda=lambda novo: novo["radar"][1].update(vetores=[]))
        self.assertEqual([entrada["id"] for entrada in self.le("dados/vetores.json")["vetores"]], ["%s_p1_ue" % DIA])
        players = self.le("dados/players.json")["players"]
        self.assertEqual(players, apoio.le(os.path.join(apoio.DADOS, "players.json"))["players"])
        self.assertTrue(self.linhas[-1].endswith("1 vetor, 0 players novos"))
        self.assertValido("--base", base, "--dia", DIA)

    def test_republicacao_confere_contra_os_registros_ja_limpos(self):
        """CONTRATO, seção 4.2, passo 7: na republicação, o que o dia gravou nos registros é tirado e refeito. A
        conferência roda contra os registros já limpos: o rascunho novo que deixa de trazer o player novo e ainda o
        usa como alvo é recusado (R02), porque é assim que a edição ficaria gravada, e o --tudo acusaria depois."""
        base = self.inicia_git()

        def com_player_e_alvo(novo):
            com_player(novo)
            for item in apoio.itens(novo):
                for ataque in apoio.ataques(item):
                    if ataque["alvo"] == "outro" and ataque.get("alvo_nome") == "República de Exemplo (fictícia)":
                        ataque["alvo"] = "republica_exemplo"
                        del ataque["alvo_nome"]
        self.publica_o_dia(muda=com_player_e_alvo)
        self.assertValido("--base", base, "--dia", DIA)
        publicada = apoio.conteudos(self.raiz)

        def so_o_alvo(novo):
            com_player_e_alvo(novo)
            novo["novos_players"] = []
        self.prepara(muda=so_o_alvo)
        linhas = self.assertFALHA(self.publica("edicao", "--url-base", apoio.BASE))
        erros = [linha for linha in linhas if linha.startswith("ERRO ")]
        self.assertTrue(erros and all(linha.startswith("ERRO R02 ") and "'republica_exemplo'" in linha for linha in erros),
                        linhas)
        self.assertEqual(apoio.conteudos(self.raiz), publicada, "nada mudou: nem o registro de players")
        # e o rascunho que traz o player de novo é aceito, sem duplicá-lo
        self.publica_o_dia(muda=com_player_e_alvo)
        self.assertEqual([p["id"] for p in self.le("dados/players.json")["players"]].count("republica_exemplo"), 1)
        self.assertValido("--base", base, "--dia", DIA)

    def test_republicacao_nao_duplica_a_anulacao(self):
        base = self.inicia_git()
        self.publica_o_dia(DIA)
        self.commit("edição %s" % DIA)

        def com_errata(novo):
            apoio.continua(apoio.sem_vetores(novo), DIA)
            novo["errata"] = [{"edicao": DIA, "item": "p1", "erro": "Texto fictício. A meta não foi suspensa.",
                               "correcao": "Texto fictício. A suspensão foi desmentida em 21/11.",
                               "url": "https://exemplo.invalid/comissao_europeia/meta-segue",
                               "anula_vetor": "%s_p1_ue" % DIA}]
        for _ in range(2):
            self.publica_o_dia(AMANHA, com_errata)
        registro = self.le("dados/vetores.json")["vetores"]
        self.assertEqual([entrada["id"] for entrada in registro],
                         ["%s_p1_ue" % DIA, "%s_r2_google" % DIA, "%s_anula_1" % AMANHA])
        self.assertEqual(registro[-1], {"id": "%s_anula_1" % AMANHA, "data": AMANHA, "anula": "%s_p1_ue" % DIA,
                                        "porque": "Texto fictício. A suspensão foi desmentida em 21/11.",
                                        "url": "https://exemplo.invalid/comissao_europeia/meta-segue"})
        self.assertEqual(self.le("edicoes/indice.json")["edicoes"][1]["corrigida_em"], [AMANHA])
        self.assertValido("--base", "HEAD", "--dia", AMANHA, agora=apoio.agora(AMANHA))
        self.assertNotEqual(base, self.git("rev-parse", "HEAD"))

    def test_dia_ja_publicado_no_head(self):
        self.inicia_git()
        self.publica_o_dia()
        self.commit("edição %s" % DIA)
        foto = apoio.fotografa(self.raiz)
        # igual: OK, sem gravar, mesmo com o relógio mais tarde (o gerada_em não conta)
        codigo, linhas = self.publica("edicao", agora=apoio.agora(DIA, "23:40:00"))
        self.assertEqual((codigo, linhas[-1]), (0, "OK edição %s já publicada: nada mudou" % DIA))
        self.assertEqual(apoio.fotografa(self.raiz), foto)
        # diferente: FALHA, e nada muda
        self.prepara(muda=lambda novo: novo.update(resumo="Outro resumo, escrito depois."))
        for argumentos in ([], ["--simula"], ["--url-base", apoio.BASE]):
            linhas = self.assertFALHA(self.publica("edicao", *argumentos))
            self.assertTrue(linhas[-1].startswith("FALHA edição %s já publicada (estado completa, no commit HEAD), e o "
                                                  "rascunho dá outra edição (difere em: resumo)." % DIA), linhas[-1])
            self.assertIn("Pare, sem alterar nada, e relate", linhas[-1])
        self.assertEqual(apoio.fotografa(self.raiz), foto)
        # e a edição de falha não entra no lugar
        linhas = self.assertFALHA(self.publica("falha", "--motivo", "Tarde demais."))
        self.assertIn("já publicada (estado completa, no commit HEAD)", linhas[-1])
        self.assertEqual(apoio.fotografa(self.raiz), foto)

    def test_quem_decide_e_o_head_e_nao_o_disco(self):
        self.inicia_git()
        self.publica_o_dia()
        self.commit("edição %s" % DIA)
        self.muda("edicoes/%s.json" % DIA, lambda edicao: edicao.update(resumo="Mexido à mão, sem commit."))
        foto = apoio.fotografa(self.raiz)
        self.prepara()
        codigo, linhas = self.publica("edicao")
        self.assertEqual((codigo, linhas[-1]), (0, "OK edição %s já publicada: nada mudou" % DIA))
        os.unlink(self.caminho("edicoes", "%s.json" % DIA))
        self.prepara(muda=lambda novo: novo.update(resumo="Outro resumo."))
        linhas = self.assertFALHA(self.publica("edicao"))
        self.assertIn("no commit HEAD", linhas[-1])
        self.assertFalse(self.existe("edicoes/%s.json" % DIA), "nada foi gravado por cima")
        self.grava("edicoes/%s.json" % DIA, foto[os.path.join("edicoes", "%s.json" % DIA)][3])

    def test_arquivo_do_dia_so_no_disco_e_desta_execucao(self):
        """Com git e sem commit, o que está no disco é desta execução: a edição nova grava por cima."""
        self.inicia_git()
        self.publica_o_dia()
        self.publica_o_dia(muda=lambda novo: novo.update(resumo="Segunda rodada da mesma execução."))
        self.assertEqual(self.le("edicoes/%s.json" % DIA)["resumo"], "Segunda rodada da mesma execução.")
        self.grava("edicoes/%s.json" % DIA, "{quebrado na metade")
        self.publica_o_dia()
        self.assertEqual(self.le("edicoes/%s.json" % DIA)["estado"], "completa")

    def test_sem_git_na_raiz_vale_o_disco(self):
        self.publica_o_dia()
        foto = apoio.fotografa(self.raiz)
        codigo, linhas = self.publica("edicao", agora=apoio.agora(DIA, "22:00:00"))
        self.assertEqual((codigo, linhas[-1]), (0, "OK edição %s já publicada: nada mudou" % DIA))
        self.prepara(muda=lambda novo: novo.update(resumo="Outro resumo."))
        linhas = self.assertFALHA(self.publica("edicao"))
        self.assertIn("já publicada (estado completa, no disco)", linhas[-1])
        linhas = self.assertFALHA(self.publica("falha", "--motivo", "Tarde demais."))
        self.assertIn("no disco", linhas[-1])
        self.assertEqual(apoio.fotografa(self.raiz), foto)
        self.grava("edicoes/%s.json" % DIA, "{quebrado")
        linhas = self.assertFALHA(self.publica("edicao"))
        self.assertIn("edicoes/%s.json já existe no disco, e não dá para ler o estado dela" % DIA, linhas[-1])

    def test_git_de_uma_pasta_de_cima_nao_conta(self):
        """Só há git quando a raiz do repositório git é a própria --raiz: aqui o repositório é a pasta de cima."""
        apoio.git(self.pasta, "init", "--quiet", "--initial-branch=main", ".")
        apoio.git(self.pasta, "config", "user.name", "Teste do publicador")
        apoio.git(self.pasta, "config", "user.email", "teste@exemplo.invalid")
        apoio.git(self.pasta, "add", "raiz/dados/regua.json")
        apoio.git(self.pasta, "commit", "--quiet", "-m", "pasta de cima")
        self.publica_o_dia()
        self.prepara(muda=lambda novo: novo.update(resumo="Outro resumo."))
        linhas = self.assertFALHA(self.publica("edicao"))
        self.assertIn("já publicada (estado completa, no disco)", linhas[-1])

    def test_edicao_ilegivel_no_head_nao_e_regravada(self):
        self.grava("edicoes/%s.json" % DIA, '{"data": "%s", "estado": "rascunho"}' % DIA)
        self.inicia_git()
        self.prepara()
        foto = apoio.fotografa(self.raiz)
        for subcomando in (["edicao"], ["falha", "--motivo", "Sem rede."]):
            linhas = self.assertFALHA(self.publica(*subcomando))
            self.assertIn("edicoes/%s.json já existe no commit HEAD, e não dá para ler o estado dela" % DIA, linhas[-1])
        self.assertEqual(apoio.fotografa(self.raiz), foto)

    def test_falha_trocada_por_edicao(self):
        base = self.inicia_git()
        self.publica_a_falha()
        self.assertValido("--base", base, "--dia", DIA)
        com_a_falha = self.commit("falha de %s" % DIA)
        self.publica_o_dia(muda=com_player)
        self.assertIn("a edição de falha de %s (no commit HEAD) dá lugar à edição nova" % DIA, self.linhas)
        self.assertEqual(self.le("edicoes/%s.json" % DIA)["estado"], "completa")
        indice = self.le("edicoes/indice.json")
        self.assertEqual([(entrada["data"], entrada["estado"]) for entrada in indice["edicoes"]], [(DIA, "completa")])
        self.assertNotIn("sem edição", self.texto("feed.xml"))
        self.assertValido("--base", com_a_falha, "--dia", DIA)
        self.assertValido("--base", base, "--dia", DIA)


class TestaASegundaEdicao(apoio.Bancada):
    def test_uma_segunda_edicao_no_dia_seguinte(self):
        base = self.inicia_git()
        self.publica_o_dia(DIA, com_player)
        primeiro = self.commit("edição %s" % DIA)
        self.assertOK(self.publica("contexto", dia=AMANHA))
        contexto = apoio.le(self.no_trabalho("contexto.json"))
        self.assertEqual((contexto["anterior"], contexto["janela_horas"]), ({"data": DIA, "estado": "completa"}, 36))
        self.assertEqual([d["nivel"] for d in contexto["alerta_anterior"]["dominios"]], [3, 1, 1, 2, 3])
        self.assertEqual(len(contexto["historias_recentes"]), 9)
        self.assertEqual([v["id"] for v in contexto["vetores_recentes"]], ["%s_p1_ue" % DIA, "%s_r2_google" % DIA])

        # sem continuacao_de, os títulos repetidos e os vetores repetidos viram aviso H3, e a edição passa
        self.publica_o_dia(AMANHA)
        avisos = [linha for linha in self.linhas if linha.startswith("AVISO H3 ")]
        self.assertEqual(len(avisos), 11, "9 títulos e 2 vetores iguais aos da véspera")
        self.assertIn("AVISO H3 principais[0].titulo: quase igual ao de %s/p1. Se continua a história, use continuacao_de."
                      % DIA, avisos)
        # com continuacao_de, sobram os dois avisos de vetor repetido
        self.publica_o_dia(AMANHA, lambda novo: apoio.continua(novo, DIA))
        self.assertEqual(len([linha for linha in self.linhas if linha.startswith("AVISO H3 ")]), 2)
        self.assertValido("--base", primeiro, "--dia", AMANHA, agora=apoio.agora(AMANHA))
        self.assertValido("--base", base, "--dia", AMANHA, agora=apoio.agora(AMANHA))

        segunda = self.le("edicoes/%s.json" % AMANHA)
        self.assertEqual([(d["nivel"], d["tendencia"], d["desde"]) for d in segunda["alerta"]["dominios"]],
                         [(3, "estavel", DIA), (1, "estavel", DIA), (1, "estavel", DIA), (2, "estavel", DIA),
                          (3, "estavel", DIA)], "nível igual repete o desde da edição anterior")
        self.assertEqual(segunda["principais"][0]["continuacao_de"], "%s/p1" % DIA)
        self.assertEqual(segunda["principais"][0]["ataques"][0]["alvo"], "outro")
        indice = self.le("edicoes/indice.json")
        self.assertEqual([entrada["data"] for entrada in indice["edicoes"]], [AMANHA, DIA], "mais nova primeiro")
        self.assertEqual(indice["atualizado_em"], apoio.agora(AMANHA))
        self.assertEqual(indice, json.loads(json.dumps(apoio.valida.monta_indice(
            {DIA: self.le("edicoes/%s.json" % DIA), AMANHA: segunda}))))
        feed = apoio.publica.ET.fromstring(self.texto("feed.xml").encode("utf-8"))
        entradas = feed.findall(apoio.NS + "entry")
        self.assertEqual([entrada.findtext(apoio.NS + "id") for entrada in entradas],
                         [apoio.BASE + "#/edicao/" + AMANHA, apoio.BASE + "#/edicao/" + DIA])
        self.assertEqual(feed.findtext(apoio.NS + "updated"), apoio.agora(AMANHA))
        texto = self.texto("edicoes/%s.md" % AMANHA)
        self.assertIn("Desde %s: nenhum nível mudou." % apoio.comum.dd_mm(DIA), texto.splitlines())
        self.assertIn("Continuação de %s, item `p1`." % apoio.comum.dd_mm_aaaa(DIA), texto.splitlines())
        registro = self.le("dados/vetores.json")["vetores"]
        self.assertEqual([entrada["id"] for entrada in registro],
                         ["%s_p1_ue" % DIA, "%s_r2_google" % DIA, "%s_p1_ue" % AMANHA, "%s_r2_google" % AMANHA])
        # a edição da véspera não foi tocada
        self.assertEqual(self.mudancas(), [("??", "edicoes/%s.json" % AMANHA), ("??", "edicoes/%s.md" % AMANHA),
                                           ("M", "dados/vetores.json"), ("M", "edicoes/indice.json"), ("M", "feed.xml")])

    def test_o_player_novo_de_ontem_ja_vale_como_alvo_e_nao_entra_de_novo(self):
        self.publica_o_dia(DIA, com_player)

        def de_novo(novo):
            apoio.continua(novo, DIA)
            com_player(novo)
        self.prepara(AMANHA, de_novo)
        linhas = self.assertFALHA(self.publica("edicao", dia=AMANHA))
        self.assertTrue(any(linha.startswith("ERRO R20 novos_players[0].id: 'republica_exemplo' já é player")
                            for linha in linhas), linhas)

        def como_alvo(novo):
            apoio.continua(novo, DIA)
            ataque = novo["principais"][0]["ataques"][0]
            ataque["alvo"] = "republica_exemplo"
            del ataque["alvo_nome"]
        self.publica_o_dia(AMANHA, como_alvo)
        self.assertIn("alvo: República de Exemplo ·", self.texto("edicoes/%s.md" % AMANHA))
        self.assertEqual(len(self.le("dados/players.json")["players"]), 31)


if __name__ == "__main__":
    unittest.main()
