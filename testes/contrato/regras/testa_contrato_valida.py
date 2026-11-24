#!/usr/bin/env python3
"""Testes de contrato do valida.py.

Escritos só a partir do ESQUEMA (o contrato de dados da edição) e do CONTRATO (a linha de comando
das ferramentas), sem ler o código do validador. Cada teste diz, na docstring, a cláusula que
confere. Teste cujo nome tem "acusa" planta um defeito e espera a regra; teste com "aceita" monta
o caso no limite permitido e espera que a regra não seja acusada.

Onde o contrato deixava duas leituras, a docstring começava com INTERPRETACAO. Na conciliação da fase 2b
cada leitura virou regra escrita no ESQUEMA ou no CONTRATO, e a docstring passou a citar a regra.

Rodar, da raiz do repositório:  python3 -B testes/contrato/regras/testa_contrato_valida.py
"""
import copy
import json
import os
import re
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import apoio  # noqa: E402
from apoio import (DIA, agora_de, calmaria, cega_energia, gatilho, mais_dias, monta_edicao, poe,  # noqa: E402
                   troca_titulos)

F = apoio.F
MARCA = "[EXEMPLO] "
DIA_EX = apoio.DIA_DO_EXEMPLO
ONTEM, ANTEONTEM, TRES_ANTES = apoio.ONTEM, apoio.ANTEONTEM, apoio.TRES_ANTES
AMANHA = mais_dias(DIA, 1)
ENERGIA, ALIMENTOS, CAMBIO, SUPRIMENTOS, CONFLITO = range(5)
AVISO_FIXO = ("Aviso: o INFOCENARIUM é escrito por modelos de IA, do setor de IA, que podem ser parte ou concorrente "
              "nesta notícia: foi construído pelo Claude Fable e pelo Claude Opus, da Anthropic, e hoje quem escreve é o "
              "GLM, da Z.ai.")

def P(edicao, i):
    return edicao["principais"][i]


def R(edicao, i):
    return edicao["radar"][i]


def D(edicao, i):
    return edicao["alerta"]["dominios"][i]


def texto_de(n):
    """Um texto fictício com exatamente n caracteres."""
    return (F + "palavra " * (n // 8 + 1))[:n - 1] + "."


def fonte_do_exemplo(veiculo, slug, dia=DIA_EX, **mais):
    """Uma fonte no estilo da edição de exemplo (endereço fictício, título com a marca)."""
    f = {"veiculo": veiculo, "titulo": MARCA + "Título fictício " + slug,
         "url": "https://exemplo.invalid/%s/%s" % (veiculo, slug), "publicado_em": dia}
    f.update(mais)
    return apoio.ordena(f, "fonte")


def so_uma_fonte_no_trigo(catalogo):
    """Deixa o trigo com uma fonte só, para plantar o aviso C5 (o catálogo congelado não tem o caso)."""
    for indicador in catalogo["indicadores"]:
        if indicador["id"] == "trigo":
            del indicador["fontes"][1:]


class CasoDeValida(apoio.Caso):
    """Base: as duas formas de chamar `valida.py --edicao`."""

    def solta(self, edicao, raiz=None, *mais):
        """A edição num arquivo fora de `edicoes/`: todas as regras R, e a H1 sem histórico."""
        return self.valida("--edicao", self.arquivo_solto(edicao), *mais, raiz=raiz or self.nova_raiz())

    def no_arquivo(self, edicao, historico=(), prepara=None):
        """A edição dentro de `edicoes/`, com as edições anteriores ao lado: regras R e H."""
        raiz = self.nova_raiz(list(historico) + [edicao], derivados=False)
        if prepara:
            prepara(raiz)
        return self.valida("--edicao", apoio.caminho_da_edicao(raiz, edicao["data"]), raiz=raiz,
                           agora=agora_de(edicao["data"]))


# =============================================================================================
# (a) O exemplo passa
# =============================================================================================

class ExemploPassa(CasoDeValida):

    def test_exemplo_sai_com_codigo_zero(self):
        """CONTRATO, seção 5: "`valida.py --edicao testes/fixtures/edicao-exemplo.json` tem de sair com
        código 0", contra a cópia congelada de `dados/` (opção `--raiz`)."""
        res = self.valida("--edicao", apoio.EXEMPLO, raiz=self.nova_raiz())
        self.passou(res)

    def test_exemplo_ultima_linha_no_formato(self):
        """CONTRATO, seção 3: "Sem erro, a última linha é `OK 0 erros, N avisos`"."""
        res = self.valida("--edicao", apoio.EXEMPLO, raiz=self.nova_raiz())
        self.assertRegex(res.ultima, r"^OK 0 erros, \d+ avisos?$", res.relato())

    def test_edicao_montada_pelo_apoio_passa(self):
        """ESQUEMA, seção 10 inteira: a edição que estes testes usam como "edição do dia" (o exemplo
        levado a outro dia, sem a marca de exemplo e com os endereços nos sites dos veículos) não
        tem erro. É a base dos testes do publica.py."""
        self.passou(self.solta(monta_edicao(DIA, rica=True)))
        self.passou(self.solta(monta_edicao(DIA)))


# =============================================================================================
# (b) Regras R, com a edição sozinha (arquivo fora de edicoes/)
# =============================================================================================

class Identidade(CasoDeValida):
    """ESQUEMA, seção 10, "Identidade e referência": R00 a R05."""

    # --- R00 ---
    def test_r00_acusa_campo_desconhecido(self):
        """ESQUEMA, seção 10, R00: "nenhum campo desconhecido"; seção 0: "Chave desconhecida é erro"."""
        e = apoio.exemplo()
        e["campo_novo"] = 1
        self.acusa(self.solta(e), "R00")

    def test_r00_acusa_campo_desconhecido_em_fonte(self):
        """ESQUEMA, seção 10, R00: "nenhum campo desconhecido" (vale em qualquer objeto da edição)."""
        e = apoio.exemplo()
        P(e, 0)["fontes"][0]["autor"] = "Alguém"
        self.acusa(self.solta(e), "R00")

    def test_r00_acusa_campo_obrigatorio_ausente(self):
        """ESQUEMA, seção 10, R00: "campo obrigatório presente"."""
        e = apoio.exemplo()
        del e["bastidores"]["modo"]
        self.acusa(self.solta(e), "R00")

    def test_r00_acusa_tipo_errado(self):
        """ESQUEMA, seção 10, R00: "tipo certo" (`forca` é inteiro; aqui vem como texto)."""
        e = apoio.exemplo()
        P(e, 0)["placar"][0]["forca"] = "2"
        self.acusa(self.solta(e), "R00")

    def test_r00_acusa_valor_fora_da_lista(self):
        """ESQUEMA, seção 10, R00: "valor dentro da lista" (`categoria` só aceita geopolitica e ia)."""
        e = apoio.exemplo()
        R(e, 4)["categoria"] = "esporte"
        self.acusa(self.solta(e), "R00")

    def test_r00_acusa_versao_diferente_de_1(self):
        """ESQUEMA, seção 1: `versao`, valores permitidos: `1`; seção 10, R00: "valor dentro da lista"."""
        e = apoio.exemplo()
        e["versao"] = 2
        self.acusa(self.solta(e), "R00")

    def test_r00_acusa_null_em_campo_opcional(self):
        """ESQUEMA, seção 0: "Campo opcional pode faltar; não use `null`, salvo onde a tabela permite";
        seção 10, R00: "tipo certo"."""
        e = apoio.exemplo()
        P(e, 0)["nao_confirmado"] = None
        self.acusa(self.solta(e), "R00")

    def test_r00_aceita_campo_opcional_ausente(self):
        """ESQUEMA, seção 0: "Campo opcional pode faltar" (`nao_confirmado` e `omite` são opcionais)."""
        e = apoio.exemplo()
        del P(e, 0)["nao_confirmado"]
        del P(e, 0)["ataques"][0]["omite"]
        self.nao_acusa(self.solta(e), "R00")

    # --- R01 ---
    def test_r01_acusa_ids_fora_de_ordem(self):
        """ESQUEMA, seção 10, R01: "Ids únicos e em ordem: `p1..pN` nas principais, `r1..rN` no radar"."""
        e = apoio.exemplo()
        R(e, 0)["id"], R(e, 1)["id"] = "r2", "r1"
        self.acusa(self.solta(e), "R01")

    def test_r01_acusa_id_repetido(self):
        """ESQUEMA, seção 10, R01: "Ids únicos e em ordem"."""
        e = apoio.exemplo()
        P(e, 1)["id"] = "p1"
        self.acusa(self.solta(e), "R01")

    def test_r01_acusa_data_diferente_do_nome_do_arquivo(self):
        """ESQUEMA, seção 10, R01: "Em `edicoes/`, `data` é igual ao nome do arquivo"."""
        e = monta_edicao(DIA)
        raiz = self.nova_raiz()
        caminho = apoio.caminho_da_edicao(raiz, AMANHA)
        apoio.grava_json(caminho, e)
        self.acusa(self.valida("--edicao", caminho, raiz=raiz), "R01")

    def test_r01_aceita_data_igual_ao_nome_do_arquivo(self):
        """ESQUEMA, seção 10, R01: "Em `edicoes/`, `data` é igual ao nome do arquivo" (caso certo)."""
        self.nao_acusa(self.no_arquivo(monta_edicao(DIA)), "R01")

    # --- R02 ---
    def test_r02_acusa_alvo_que_nao_existe(self):
        """ESQUEMA, seção 10, "Qual código sai": "`alvo` que não é player, partido, `outro` nem `nenhum`:
        R02" (a R04 cobre o mesmo defeito, e não sai)."""
        e = apoio.exemplo()
        R(e, 4)["ataque"]["alvo"] = "ninguem"
        res = self.solta(e)
        self.acusa(res, "R02", caminho="radar[4].ataque.alvo")
        self.assertNotIn("R04", res.regras, res.relato())

    def test_r02_acusa_partido_que_nao_existe(self):
        """ESQUEMA, seção 10, R02: "Toda referência existe. Partido, tema e domínio: em `regua.json`"."""
        e = apoio.exemplo()
        P(e, 0)["placar"][0]["partido"] = "partido_verde"
        self.acusa(self.solta(e), "R02")

    def test_r02_acusa_dominio_que_nao_existe(self):
        """ESQUEMA, seção 10, R02: "Partido, tema e domínio: em `regua.json`"."""
        e = apoio.exemplo()
        P(e, 0)["dominios"] = ["energia", "agua"]
        self.acusa(self.solta(e), "R02")

    def test_r02_acusa_veiculo_fora_do_mapa(self):
        """ESQUEMA, seção 10, R02: "**(dia)** Veículo: em `veiculos.json`"."""
        e = apoio.exemplo()
        R(e, 4)["ataque"]["veiculo"] = "jornal_inexistente"
        R(e, 4)["fontes"][0]["veiculo"] = "jornal_inexistente"
        self.acusa(self.solta(e), "R02")

    def test_r02_acusa_indicador_fora_do_catalogo(self):
        """ESQUEMA, seção 10, R02: "**(dia)** Indicador: em `dados/indicadores.json`, sem repetir"."""
        e = apoio.exemplo()
        e["indicadores"][1]["id"] = "cobre"
        self.acusa(self.solta(e), "R02")

    def test_r02_acusa_indicador_repetido(self):
        """ESQUEMA, seção 10, R02: "Indicador: em `dados/indicadores.json`, sem repetir"."""
        e = apoio.exemplo()
        e["indicadores"][1] = copy.deepcopy(e["indicadores"][0])
        self.acusa(self.solta(e), "R02")

    def test_r02_aceita_alvo_que_e_o_player_novo_do_dia(self):
        """ESQUEMA, seção 10, R02: "Player: em `players.json`; como `alvo`, vale também o de
        `novos_players` desta edição"."""
        e = apoio.exemplo()
        R(e, 4)["ataque"]["alvo"] = "republica_exemplo"
        self.nao_acusa(self.solta(e), "R02", "R04")

    def test_r02_aceita_alvo_que_e_partido(self):
        """ESQUEMA, seção 4, tabela de `ataques`: `alvo` é "id de player, id de partido, `outro` ou
        `nenhum`"; seção 10, R02."""
        e = apoio.exemplo()
        R(e, 4)["ataque"]["alvo"] = "centrao"
        self.nao_acusa(self.solta(e), "R02", "R04")

    # --- R03 ---
    def test_r03_acusa_lado_diferente_do_mapa(self):
        """ESQUEMA, seção 10, R03: "**(dia)** `lado` do ataque é igual ao `lado` do veículo no mapa"."""
        e = apoio.exemplo()
        P(e, 0)["ataques"][0]["lado"] = "soberanistas"       # nyt é ordem_global no mapa congelado
        self.acusa(self.solta(e), "R03")

    def test_r03_acusa_atirador_de_lado_incerto_em_principal(self):
        """ESQUEMA, seção 10, R03: "Em principal, o veículo do ataque tem `lado_confianca` `alta` ou
        `media`: veículo de lado incerto não atira em principal"."""
        e = apoio.exemplo()
        a = P(e, 1)["ataques"][0]
        a["veiculo"], a["lado"], a["url"] = "techcrunch", "bancada_talento", "https://exemplo.invalid/techcrunch/x"
        P(e, 1)["fontes"].append(fonte_do_exemplo("techcrunch", "x"))
        self.acusa(self.solta(e), "R03")

    def test_r03_aceita_atirador_de_lado_incerto_no_radar(self):
        """ESQUEMA, seção 10, R03: a exigência de `lado_confianca` vale "em principal". No radar, o
        veículo de lado incerto pode atirar."""
        e = apoio.exemplo()
        a = R(e, 0)["ataque"]
        a["veiculo"], a["lado"], a["url"] = "techcrunch", "bancada_talento", R(e, 0)["fontes"][1]["url"]
        self.nao_acusa(self.solta(e), "R03")

    # --- R04 ---
    def test_r04_acusa_alvo_outro_sem_alvo_nome(self):
        """ESQUEMA, seção 10, R04: "`alvo_nome` existe se, e só se, `alvo` é `outro`"."""
        e = apoio.exemplo()
        del P(e, 0)["ataques"][2]["alvo_nome"]
        self.acusa(self.solta(e), "R04")

    def test_r04_acusa_alvo_nome_sem_alvo_outro(self):
        """ESQUEMA, seção 10, R04: "`alvo_nome` existe se, e só se, `alvo` é `outro`"."""
        e = apoio.exemplo()
        poe(P(e, 0)["ataques"][0], "ataque", alvo_nome="República de Exemplo")
        self.acusa(self.solta(e), "R04")

    def test_r04_acusa_fonte_outro_sem_nome(self):
        """ESQUEMA, seção 10, R04: "`nome` da fonte existe se, e só se, `veiculo` é `outro`"."""
        e = apoio.exemplo()
        del P(e, 0)["fontes"][5]["nome"]
        self.acusa(self.solta(e), "R04")

    def test_r04_acusa_fonte_do_mapa_com_nome(self):
        """ESQUEMA, seção 10, R04: "`nome` da fonte existe se, e só se, `veiculo` é `outro`"."""
        e = apoio.exemplo()
        poe(P(e, 0)["fontes"][0], "fonte", nome="Agência fictícia")
        self.acusa(self.solta(e), "R04")

    def test_r04_acusa_ataque_de_veiculo_outro(self):
        """ESQUEMA, seção 10, R04: "`veiculo` de ataque nunca é `outro`"; seção 15: fonte fora do mapa
        "Nunca em `ataques` nem em `ataque`"."""
        e = apoio.exemplo()
        R(e, 4)["ataque"]["veiculo"] = "outro"
        poe(R(e, 4)["fontes"][0], "fonte", veiculo="outro", nome="Jornal de Amostra (fictício)")
        self.acusa(self.solta(e), "R04")

    def test_r04_aceita_alvo_nenhum_sem_alvo_nome(self):
        """ESQUEMA, seção 10, R04: "`alvo_nome` existe se, e só se, `alvo` é `outro`" (com `nenhum`,
        o campo não vem)."""
        e = apoio.exemplo()
        a = R(e, 3)["ataque"]
        a["alvo"] = "nenhum"
        del a["alvo_nome"]
        self.nao_acusa(self.solta(e), "R04")

    # --- R05 ---
    def test_r05_acusa_url_de_ataque_fora_das_fontes(self):
        """ESQUEMA, seção 10, R05: "Toda `url` de ataque e de vetor aparece em `fontes` do mesmo item"."""
        e = apoio.exemplo()
        P(e, 0)["ataques"][1]["url"] = "https://exemplo.invalid/fox_news/outra-pagina"
        self.acusa(self.solta(e), "R05")

    def test_r05_acusa_url_de_ataque_em_fonte_de_outro_veiculo(self):
        """ESQUEMA, seção 10, R05: "no ataque, com o mesmo `veiculo`"."""
        e = apoio.exemplo()
        P(e, 0)["ataques"][0]["url"] = P(e, 0)["fontes"][0]["url"]     # o ataque é do nyt; a fonte, da reuters
        self.acusa(self.solta(e), "R05")

    def test_r05_acusa_url_de_vetor_fora_das_fontes(self):
        """ESQUEMA, seção 10, R05: "Toda `url` de ataque e de vetor aparece em `fontes` do mesmo item"."""
        e = apoio.exemplo()
        P(e, 0)["vetores"][0]["url"] = "https://exemplo.invalid/comissao_europeia/outro-decreto"
        self.acusa(self.solta(e), "R05")

    def test_r05_acusa_url_de_fonte_repetida_no_item(self):
        """ESQUEMA, seção 10, R05: "Dentro de um item, nenhuma `url` de fonte se repete"."""
        e = apoio.exemplo()
        P(e, 0)["fontes"].append(copy.deepcopy(P(e, 0)["fontes"][0]))
        self.acusa(self.solta(e), "R05")

    def test_r05_aceita_mesma_url_em_itens_diferentes(self):
        """ESQUEMA, seção 10, R05: a repetição é proibida "dentro de um item"; entre itens, pode."""
        e = apoio.exemplo()
        R(e, 1)["fontes"][1]["url"] = R(e, 0)["fontes"][1]["url"]      # techcrunch nos dois itens
        self.nao_acusa(self.solta(e), "R05")


class FonteConfiancaEData(CasoDeValida):
    """ESQUEMA, seção 10, "Fonte, confiança e data": R06 a R09, R19 e R22."""

    # --- R06 ---
    def test_r06_acusa_principal_com_duas_fontes(self):
        """ESQUEMA, seção 10, R00: contagem fora da tabela é R00, mas "onde uma regra numerada dá o número,
        sai ela: R06 (principal com menos de 3 fontes)"."""
        e = apoio.exemplo()
        p = P(e, 2)
        p["ataques"] = p["ataques"][:2]                    # guardian e tass: 2 partidos
        p["fontes"] = p["fontes"][1:3]                     # guardian (forte) e tass
        res = self.solta(apoio.acerta(e))
        self.acusa(res, "R06", caminho="principais[2].fontes")
        self.assertNotIn("R00", res.regras, res.relato())

    def test_r06_acusa_ataques_de_um_partido_so(self):
        """ESQUEMA, seção 10, R06: "Os `ataques` também vêm de 2 partidos ou mais"."""
        e = apoio.exemplo()
        p = P(e, 2)
        for i, veiculo in ((1, "nyt"), (2, "wired")):      # os três atiradores passam a ser de ordem_global
            p["ataques"][i]["veiculo"], p["ataques"][i]["lado"] = veiculo, "ordem_global"
            p["fontes"][i + 1]["veiculo"] = veiculo
        p["confianca"] = "media"
        self.acusa(self.solta(apoio.acerta(e)), "R06")

    def test_r06_acusa_principal_sem_fonte_forte(self):
        """ESQUEMA, seção 10, R06: "1 fonte forte ou mais"; seção 0: fonte forte é "fonte de veículo com
        `fatos: alta` no mapa, ou fonte marcada `primaria: true`"."""
        e = apoio.exemplo()
        p = P(e, 2)
        p["fontes"][0]["veiculo"] = "al_jazeera"                              # no lugar da ap (fatos alta)
        p["ataques"][0]["veiculo"], p["ataques"][0]["lado"] = "fox_news", "soberanistas"
        p["fontes"][1]["veiculo"] = "fox_news"                                # no lugar do guardian (fatos alta)
        p["confianca"] = "media"
        self.acusa(self.solta(apoio.acerta(e)), "R06")

    def test_r06_aceita_tres_fontes_dois_partidos_uma_forte(self):
        """ESQUEMA, seção 10, R06: "3 fontes ou mais; veículos de 2 partidos ou mais; 1 fonte forte ou
        mais" (o mínimo exato)."""
        e = apoio.exemplo()
        P(e, 2)["fontes"] = P(e, 2)["fontes"][1:]          # sai a ap; ficam guardian (forte), tass e gazeta
        self.nao_acusa(self.solta(apoio.acerta(e)), "R06")

    # --- R07 ---
    def test_r07_acusa_radar_com_duas_fontes_do_mesmo_partido_sem_forte(self):
        """ESQUEMA, seção 10, R07: "Radar: 1 fonte forte, ou 2 fontes de veículos de partidos diferentes"."""
        e = apoio.exemplo()
        R(e, 2)["fontes"][0]["veiculo"] = "techcrunch"
        R(e, 2)["ataque"]["veiculo"], R(e, 2)["ataque"]["lado"] = "techcrunch", "bancada_talento"
        self.acusa(self.solta(apoio.acerta(e)), "R07")

    def test_r07_aceita_uma_fonte_forte_so(self):
        """ESQUEMA, seção 10, R07: "1 fonte forte" basta no radar."""
        e = apoio.exemplo()
        R(e, 0)["fontes"] = R(e, 0)["fontes"][:1]          # só a wired, fatos alta
        self.nao_acusa(self.solta(apoio.acerta(e)), "R07")

    def test_r07_aceita_duas_fontes_de_partidos_diferentes_sem_forte(self):
        """ESQUEMA, seção 10, R07: "ou 2 fontes de veículos de partidos diferentes"."""
        e = apoio.exemplo()
        r = R(e, 4)
        r["ataque"].update(veiculo="fox_news", lado="soberanistas", url="https://exemplo.invalid/fox_news/juros")
        r["fontes"] = [fonte_do_exemplo("fox_news", "juros"), fonte_do_exemplo("al_jazeera", "juros")]
        self.nao_acusa(self.solta(apoio.acerta(e)), "R07")

    # --- R08 ---
    def test_r08_acusa_alta_com_um_campo_so(self):
        """ESQUEMA, seção 10, R08: "`alta`: fontes de veículos dos dois campos e 1 forte". O caminho do
        campo segue o exemplo do CONTRATO, seção 3: `ERRO R08 radar[2].confianca: …`."""
        e = apoio.exemplo()
        R(e, 3)["confianca"] = "alta"                      # valor (Centrão) e ft (Centro Atlântico): um campo
        self.acusa(self.solta(e), "R08", caminho="radar[3].confianca")

    def test_r08_aceita_alta_com_dois_campos_e_uma_forte(self):
        """ESQUEMA, seção 10, R08: "`alta`: fontes de veículos dos dois campos e 1 forte" (é o conserto
        que a mensagem de exemplo do CONTRATO sugere: "acrescente fonte do outro campo")."""
        e = apoio.exemplo()
        R(e, 3)["confianca"] = "alta"
        R(e, 3)["fontes"].append(fonte_do_exemplo("fox_news", "seguro-suspenso"))
        self.nao_acusa(self.solta(apoio.acerta(e)), "R08")

    def test_r08_aceita_declarar_menos_que_o_teto(self):
        """ESQUEMA, seção 10, R08: "O agente pode declarar menos que o teto, nunca mais"."""
        e = apoio.exemplo()
        R(e, 4)["confianca"] = "baixa"                     # o teto de r5 é media; não tem placar nem gatilho
        self.nao_acusa(self.solta(e), "R08")

    # --- R09 ---
    def test_r09_acusa_fonte_tres_dias_antes(self):
        """ESQUEMA, seção 10, R09: "`publicado_em` fica entre `data` menos 2 dias e `data` mais 1 dia"."""
        e = apoio.exemplo()
        P(e, 0)["fontes"][0]["publicado_em"] = mais_dias(DIA_EX, -3)
        self.acusa(self.solta(e), "R09")

    def test_r09_acusa_fonte_dois_dias_depois(self):
        """ESQUEMA, seção 10, R09: "entre `data` menos 2 dias e `data` mais 1 dia"."""
        e = apoio.exemplo()
        P(e, 0)["fontes"][0]["publicado_em"] = mais_dias(DIA_EX, 2)
        self.acusa(self.solta(e), "R09")

    def test_r09_acusa_fonte_primaria_dois_dias_depois(self):
        """ESQUEMA, seção 10, R09: "Fonte `primaria` pode ser mais antiga, nunca depois de `data` mais 1"."""
        e = apoio.exemplo()
        P(e, 0)["fontes"][4]["publicado_em"] = mais_dias(DIA_EX, 2)
        self.acusa(self.solta(e), "R09")

    def test_r09_aceita_os_dois_limites_da_janela(self):
        """ESQUEMA, seção 10, R09: "entre `data` menos 2 dias e `data` mais 1 dia (a folga cobre o fuso)"."""
        e = apoio.exemplo()
        P(e, 0)["fontes"][0]["publicado_em"] = mais_dias(DIA_EX, -2)
        P(e, 0)["fontes"][1]["publicado_em"] = mais_dias(DIA_EX, 1)
        self.nao_acusa(self.solta(e), "R09")

    def test_r09_aceita_fonte_primaria_antiga(self):
        """ESQUEMA, seção 10, R09: "Fonte `primaria` pode ser mais antiga"."""
        e = apoio.exemplo()
        P(e, 0)["fontes"][5]["publicado_em"] = "2025-03-01"
        self.nao_acusa(self.solta(e), "R09")

    # --- R19 ---
    def test_r19_acusa_item_de_ia_sem_a_marca(self):
        """ESQUEMA, seção 10, R19: "`conflito_de_interesse` tem de ser `true` se: (a) a `categoria` do
        item é `ia`"."""
        e = apoio.exemplo()
        del R(e, 0)["conflito_de_interesse"]
        self.acusa(self.solta(e), "R19")

    def test_r19_acusa_alvo_da_lista_sem_a_marca(self):
        """ESQUEMA, seção 10, R19, caso (b): "algum `alvo` de ataque […] do item está em `regua.json`,
        lista `conflito.players`"."""
        e = apoio.exemplo()
        a = R(e, 3)["ataque"]
        a["alvo"] = "musk"
        del a["alvo_nome"]
        self.acusa(self.solta(e), "R19")

    def test_r19_acusa_vetor_de_player_da_lista_sem_a_marca(self):
        """ESQUEMA, seção 10, R19, caso (b): "ou `player` de vetor do item está em […] `conflito.players`"."""
        e = apoio.exemplo()
        P(e, 0)["vetores"][0]["player"] = "meta"           # bancada_talento, que vota Y em clima
        self.acusa(self.solta(e), "R19")

    def test_r19_acusa_termo_da_lista_no_texto_sem_a_marca(self):
        """ESQUEMA, seção 10, R19, caso (c): "algum texto do item, inclusive título de fonte, traz um
        termo de `conflito.termos`"."""
        e = apoio.exemplo()
        P(e, 2)["fato"] += " A OpenAI comentou."
        self.acusa(self.solta(e), "R19")

    def test_r19_acusa_termo_da_lista_em_titulo_de_fonte(self):
        """ESQUEMA, seção 10, R19, caso (c): "inclusive título de fonte"."""
        e = apoio.exemplo()
        P(e, 2)["fontes"][0]["titulo"] += " and Gemini"
        self.acusa(self.solta(e), "R19")

    def test_r19_aceita_palavra_parecida_que_nao_e_o_termo(self):
        """ESQUEMA, seção 10, R19, caso (c): "Vale a palavra inteira, escrita como na lista e sem hífen
        antes: "Jean-Claude" não conta"."""
        e = apoio.exemplo()
        P(e, 2)["fato"] += " Jean-Claude Exemplo presidiu a sessão, no auditório Googleplex. Um claude foi citado."
        self.nao_acusa(self.solta(e), "R19")

    def test_r19_acusa_fonte_de_veiculo_ligado_a_anthropic_sem_a_marca(self):
        """ESQUEMA, seção 10, R19, caso (d): "**(dia)** alguma fonte do item é de veículo que tem
        `anthropic` em `serve_a` ou em `alvos` no mapa"."""
        e = apoio.exemplo()
        R(e, 3)["fontes"].append(fonte_do_exemplo("fli", "seguro-suspenso"))     # fli tem anthropic em alvos
        self.acusa(self.solta(apoio.acerta(e)), "R19")

    def test_r19_aceita_caso_b_com_a_marca_e_dois_partidos(self):
        """ESQUEMA, seção 10, R19: com a marca, "`confianca` no máximo `media`" e, "nos casos (b), (c) e
        (d), **(dia)** fontes de veículos de 2 partidos ou mais, também no radar"."""
        e = apoio.exemplo()
        r = R(e, 3)                                        # r4: valor (Centrão) e ft (Centro Atlântico), media
        r["ataque"]["alvo"] = "musk"
        del r["ataque"]["alvo_nome"]
        poe(r, "radar", conflito_de_interesse=True)
        self.nao_acusa(self.solta(e), "R19")

    def test_r19_acusa_caso_b_com_a_marca_e_um_partido_so(self):
        """ESQUEMA, seção 10, R19: "Nos casos (b), (c) e (d), **(dia)** fontes de veículos de 2 partidos
        ou mais, também no radar"."""
        e = apoio.exemplo()
        r = R(e, 4)                                        # r5: uma fonte só (wsj)
        r["ataque"]["alvo"] = "musk"
        poe(r, "radar", conflito_de_interesse=True)
        self.acusa(self.solta(e), "R19")

    def test_r19_acusa_marca_com_confianca_alta(self):
        """ESQUEMA, seção 10, R19: "Com a marca em `true`: `confianca` no máximo `media`"."""
        e = apoio.exemplo()
        poe(P(e, 2), "principal", conflito_de_interesse=True)      # p3 tem confiança alta
        self.acusa(self.solta(e), "R19")

    def test_r19_aceita_marca_ligada_pelo_agente_em_outro_caso(self):
        """ESQUEMA, seção 10, R19: "O agente pode ligar em outros; ninguém desliga"."""
        e = apoio.exemplo()
        poe(P(e, 2), "principal", conflito_de_interesse=True, confianca="media")
        self.nao_acusa(self.solta(e), "R19")

    def test_r19_acusa_vetor_com_a_marca_provado_por_fonte_que_nao_e_primaria(self):
        """ESQUEMA, seção 10, R19: "Com a marca em `true`: […] vetor do item só com `url` de fonte
        `primaria`"."""
        e = apoio.exemplo()
        R(e, 1)["vetores"][0]["url"] = R(e, 1)["fontes"][0]["url"]     # wired: forte, mas não primária
        self.acusa(self.solta(e), "R19")

    # --- R22 ---
    def test_r22_acusa_primaria_fora_do_mapa_em_site_nao_oficial(self):
        """ESQUEMA, seção 10, R22: "ou em fonte `outro` cujo site bate com um sufixo de […]
        `sites_oficiais`"; seção 0: "`gov.br.exemplo.com` não bate com `gov.br`"."""
        e = apoio.exemplo()
        P(e, 0)["fontes"][5]["url"] = "https://gov.br.exemplo.com/decreto.pdf"
        self.acusa(self.solta(e), "R22")

    def test_r22_acusa_primaria_em_veiculo_privado(self):
        """ESQUEMA, seção 10, R22: "`primaria: true` só vale em fonte de veículo do mapa com `tipo`
        `oficial` ou `dados`"."""
        e = apoio.exemplo()
        poe(P(e, 0)["fontes"][0], "fonte", primaria=True)          # reuters é agência
        self.acusa(self.solta(e), "R22")

    def test_r22_aceita_primaria_fora_do_mapa_em_site_igual_ao_sufixo(self):
        """ESQUEMA, seção 0: "Um site **bate** com um nome da lista quando é igual a ele ou termina em
        ponto mais ele"; o site de uma URL é "em minúsculas, sem `www.`"."""
        e = apoio.exemplo()
        P(e, 0)["fontes"][5]["url"] = "https://www.gov.br/exemplo/decreto-1-2026"
        self.nao_acusa(self.solta(e), "R22")

    def test_r22_aceita_primaria_em_veiculo_de_tipo_dados(self):
        """ESQUEMA, seção 10, R22: "veículo do mapa com `tipo` `oficial` ou `dados`"."""
        e = apoio.exemplo()
        P(e, 0)["fontes"].append(fonte_do_exemplo("fmi", "relatorio", primaria=True))     # fmi é de tipo dados
        self.nao_acusa(self.solta(apoio.acerta(e)), "R22")


class PlacarVetorESinais(CasoDeValida):
    """ESQUEMA, seção 10, "Placar, vetor e sinais": R10, R11, R12, R21 e R23."""

    # --- R10 ---
    def test_r10_acusa_narrativa_com_forca_2(self):
        """ESQUEMA, seção 10, R10: "`evidencia: narrativa` só com `forca` 1"."""
        e = apoio.exemplo()
        P(e, 0)["placar"][2]["forca"] = 2
        self.acusa(self.solta(e), "R10")

    def test_r10_acusa_partido_repetido_no_placar_do_item(self):
        """ESQUEMA, seção 10, R10: "No máximo uma linha por partido em cada item"."""
        e = apoio.exemplo()
        P(e, 0)["placar"][1]["partido"] = "eixo_revisionista"
        self.acusa(self.solta(apoio.acerta(e)), "R10")

    def test_r10_acusa_forca_3_no_radar_sem_fonte_forte(self):
        """ESQUEMA, seção 10, R10: "No radar, `forca` 3 exige fonte forte no item"."""
        e = apoio.exemplo()
        R(e, 5)["placar"][0]["forca"] = 3                  # r6: xinhua e al_jazeera, nenhuma forte
        self.acusa(self.solta(apoio.acerta(e)), "R10")

    def test_r10_aceita_forca_3_no_radar_com_fonte_forte(self):
        """ESQUEMA, seção 10, R10: "No radar, `forca` 3 exige fonte forte no item" (r4 tem valor e ft)."""
        e = apoio.exemplo()
        R(e, 3)["placar"][0]["forca"] = 3
        self.nao_acusa(self.solta(apoio.acerta(e)), "R10")

    def test_r10_acusa_confianca_baixa_com_placar(self):
        """ESQUEMA, seção 10, R10: "Item com `confianca: baixa` tem `placar` vazia"."""
        e = apoio.exemplo()
        r = R(e, 2)
        del r["sem_placar"]
        r["placar"] = [{"partido": "bancada_talento", "efeito": "ganha", "forca": 1, "evidencia": "narrativa",
                        "porque": F + "A The Verge usa o caso a favor do partido."}]
        self.acusa(self.solta(apoio.acerta(e)), "R10")

    def test_r10_acusa_placar_vazio_sem_sem_placar(self):
        """ESQUEMA, seção 10, R10: "`sem_placar` existe se, e só se, `placar` é vazia"."""
        e = apoio.exemplo()
        del R(e, 4)["sem_placar"]
        self.acusa(self.solta(e), "R10")

    def test_r10_acusa_sem_placar_com_placar_preenchido(self):
        """ESQUEMA, seção 10, R10: "`sem_placar` existe se, e só se, `placar` é vazia"."""
        e = apoio.exemplo()
        poe(R(e, 3), "radar", sem_placar=F + "Ninguém ganhou nem perdeu.")
        self.acusa(self.solta(e), "R10")

    # --- R11 ---
    def test_r11_acusa_vetor_provado_por_fonte_que_nao_e_forte(self):
        """ESQUEMA, seção 10, R11: "a `url` do vetor é de fonte forte"."""
        e = apoio.exemplo()
        P(e, 0)["vetores"][0]["url"] = P(e, 0)["fontes"][2]["url"]     # fox_news, fatos media
        self.acusa(self.solta(e), "R11")

    def test_r11_acusa_destino_igual_ao_partido_do_player(self):
        """ESQUEMA, seção 10, R11: "`para` é diferente do partido do player e de `independentes`"."""
        e = apoio.exemplo()
        P(e, 0)["vetores"][0]["para"] = "centro_atlantico"             # o partido da ue
        self.acusa(self.solta(e), "R11")

    def test_r11_acusa_destino_independentes(self):
        """ESQUEMA, seção 10, R11: "`para` é diferente do partido do player e de `independentes`"."""
        e = apoio.exemplo()
        P(e, 0)["vetores"][0]["para"] = "independentes"
        self.acusa(self.solta(e), "R11")

    def test_r11_acusa_destino_que_vota_igual_no_tema(self):
        """ESQUEMA, seção 10, R11: "Com tema atual, o voto típico de `para` nesse tema é `B` ou `R` e é
        diferente do voto típico do partido do player"."""
        e = apoio.exemplo()
        P(e, 0)["vetores"][0]["para"] = "ordem_global"     # em clima, Centro Atlântico e Ordem Global votam B
        self.acusa(self.solta(e), "R11")

    def test_r11_acusa_destino_sem_voto_firme_no_tema(self):
        """ESQUEMA, seção 10, R11: "o voto típico de `para` nesse tema é `B` ou `R`"."""
        e = apoio.exemplo()
        P(e, 0)["vetores"][0].update(tema="pandemia_depois", para="eixo_revisionista")     # vota Y nesse tema
        self.acusa(self.solta(e), "R11")

    def test_r11_acusa_tema_que_e_historia(self):
        """ESQUEMA, seção 10, R11: "`tema` é da lista tema atual, ou `ordem`"; seção 0: "`pandemia_inicio`
        e `ia_inicio` são história"."""
        e = apoio.exemplo()
        P(e, 0)["vetores"][0]["tema"] = "pandemia_inicio"
        self.acusa(self.solta(e), "R11")

    def test_r11_acusa_vetor_do_player_novo_do_dia(self):
        """ESQUEMA, seção 10, R11: "`player` existe em `players.json` e não é o de `novos_players` desta
        edição"."""
        e = apoio.exemplo()
        P(e, 0)["vetores"][0]["player"] = "republica_exemplo"
        self.acusa(self.solta(e), "R11")

    def test_r11_acusa_vetor_de_player_que_nao_existe(self):
        """ESQUEMA, seção 10, "Qual código sai": "`player` de vetor que não existe em `players.json`: R11"
        (a R02 cobre o mesmo defeito, e não sai)."""
        e = apoio.exemplo()
        P(e, 0)["vetores"][0]["player"] = "atlantida"
        res = self.solta(e)
        self.acusa(res, "R11", caminho="principais[0].vetores[0].player")
        self.assertNotIn("R02", res.regras, res.relato())

    def test_r11_acusa_dois_vetores_do_mesmo_player_no_mesmo_item(self):
        """ESQUEMA, seção 10, R11: "em cada item, um só vetor por player (o `id` do registro é data, item e
        player: seção 12)"."""
        e = apoio.exemplo()
        R(e, 1)["vetores"] = []
        P(e, 0)["vetores"].append(dict(P(e, 0)["vetores"][0], para="eixo_revisionista", tema="ordem"))
        self.acusa(self.solta(e), "R11", caminho="principais[0].vetores[1].player")

    def test_r11_acusa_tres_vetores_na_edicao(self):
        """ESQUEMA, seção 10, R11: "no máximo 2 vetores na edição"."""
        e = apoio.exemplo()
        P(e, 2)["vetores"] = [{"player": "russia", "para": "centro_atlantico", "forca": 1, "tema": "ordem",
                               "porque": F + "Ato fictício do player.", "url": P(e, 2)["fontes"][0]["url"]}]
        self.acusa(self.solta(e), "R11")

    def test_r11_acusa_par_player_e_destino_repetido(self):
        """ESQUEMA, seção 10, R11: "um só por par player e destino"."""
        e = apoio.exemplo()
        R(e, 1)["vetores"] = []
        P(e, 0)["vetores"].append(copy.deepcopy(P(e, 0)["vetores"][0]))
        self.acusa(self.solta(e), "R11")

    def test_r11_acusa_vetor_em_item_com_fontes_de_um_partido_so(self):
        """ESQUEMA, seção 10, R11: "**(dia)** O item tem fontes de veículos de 2 partidos ou mais"."""
        e = apoio.exemplo()
        r = R(e, 1)                                        # r2: wired, techcrunch e google_deepmind
        r["fontes"][0]["veiculo"] = "venturebeat"          # os três passam a ser da Bancada do Talento
        r["ataque"]["veiculo"], r["ataque"]["lado"] = "venturebeat", "bancada_talento"
        self.acusa(self.solta(apoio.acerta(e)), "R11")

    def test_r11_aceita_tema_ordem_sem_conta_de_voto(self):
        """ESQUEMA, seção 10, R11: a conta do voto típico vale "com tema atual"; com `ordem`, não se faz."""
        e = apoio.exemplo()
        P(e, 0)["vetores"][0].update(tema="ordem", para="ordem_global")
        self.nao_acusa(self.solta(e), "R11")

    def test_r11_aceita_player_independente(self):
        """ESQUEMA, seção 10, R11: "player de `independentes` não tem voto típico: basta a primeira
        parte" (o voto de `para` no tema é B ou R)."""
        e = apoio.exemplo()
        P(e, 0)["vetores"][0]["player"] = "modi"           # independentes; soberanistas vota R em clima
        self.nao_acusa(self.solta(e), "R11")

    # --- R12 ---
    def test_r12_acusa_narrativa_somada_ao_saldo(self):
        """ESQUEMA, seção 10, R12: "`saldo` = soma das forças com `ganha` menos soma das forças com
        `perde` […] só das linhas com `evidencia` diferente de `narrativa`"."""
        e = apoio.exemplo()
        for linha in e["placar_do_dia"]:
            if linha["partido"] == "soberanistas":
                linha["saldo"] = 2
        self.acusa(self.solta(e), "R12")

    def test_r12_acusa_narrativa_errada(self):
        """ESQUEMA, seção 10, R12: "`narrativa` = linhas de narrativa com `ganha` menos linhas de
        narrativa com `perde`"."""
        e = apoio.exemplo()
        e["placar_do_dia"][0]["narrativa"] = 0             # ordem_global tem 1 linha de narrativa a favor
        self.acusa(self.solta(e), "R12")

    def test_r12_acusa_partido_que_falta_no_placar_do_dia(self):
        """ESQUEMA, seção 10, R12: "`placar_do_dia` tem exatamente os partidos que aparecem em algum
        `placar` do dia"."""
        e = apoio.exemplo()
        e["placar_do_dia"].pop()
        self.acusa(self.solta(e), "R12")

    def test_r12_acusa_partido_a_mais_no_placar_do_dia(self):
        """ESQUEMA, seção 10, R12: "exatamente os partidos que aparecem em algum `placar` do dia"."""
        e = apoio.exemplo()
        r = R(e, 3)                                        # a única linha do Centrão está em r4
        r["placar"] = []
        poe(r, "radar", sem_placar=F + "Ninguém ganhou nem perdeu algo medido.")
        self.acusa(self.solta(e), "R12")

    def test_r12_acusa_placar_do_dia_fora_de_ordem(self):
        """ESQUEMA, seção 10, R12: "na ordem da seção 6"; seção 6: "maior saldo primeiro; empate segue a
        ordem da régua"."""
        e = apoio.exemplo()
        e["placar_do_dia"][0], e["placar_do_dia"][1] = e["placar_do_dia"][1], e["placar_do_dia"][0]
        self.acusa(self.solta(e), "R12")

    def test_r12_acusa_contagem_de_veiculos_errada(self):
        """ESQUEMA, seção 10, R12: "`bastidores.veiculos_consultados` é a contagem de veículos distintos
        do mapa em `fontes`"."""
        e = apoio.exemplo()
        e["bastidores"]["veiculos_consultados"] = 5
        self.acusa(self.solta(e), "R12")

    def test_r12_aceita_partido_so_com_narrativa_e_saldo_zero(self):
        """ESQUEMA, seção 10, R12: "Partido que só tem linha de narrativa aparece com saldo 0". No
        exemplo, os Soberanistas só têm 2 linhas de narrativa a favor."""
        e = apoio.exemplo()
        linha = [x for x in e["placar_do_dia"] if x["partido"] == "soberanistas"][0]
        self.assertEqual((linha["saldo"], linha["narrativa"]), (0, 2))
        self.nao_acusa(self.solta(e), "R12")

    # --- R21 ---
    def test_r21_acusa_vigiar_sem_interrogacao(self):
        """ESQUEMA, seção 10, R21: "Cada texto de `vigiar` de uma principal termina com `?`"."""
        e = apoio.exemplo()
        P(e, 0)["vigiar"][0] = "O Reino de Amostra responde com ataque militar até 22/11."
        self.acusa(self.solta(e), "R21")

    def test_r21_acusa_vigiar_sem_data(self):
        """ESQUEMA, seção 10, R21: "e traz uma data no formato `DD/MM`"."""
        e = apoio.exemplo()
        P(e, 0)["vigiar"][1] = "O terminal fictício volta a embarcar petróleo?"
        self.acusa(self.solta(e), "R21")

    def test_r21_aceita_pergunta_com_data(self):
        """ESQUEMA, seção 10, R21: "termina com `?` e traz uma data no formato `DD/MM`". Na segunda pergunta,
        o prazo não é lido: 05/01 passa, mesmo a mais de 30 dias."""
        e = apoio.exemplo()
        P(e, 0)["vigiar"][1] = "O terminal fictício volta a embarcar petróleo até 05/01?"
        self.nao_acusa(self.solta(e), "R21")

    def test_r21_acusa_primeira_pergunta_com_prazo_a_mais_de_30_dias(self):
        """ESQUEMA, seção 10, R21: "**(dia)** Na primeira pergunta, o prazo (a última data `DD/MM` do texto […])
        fica entre `data` e 30 dias depois". O exemplo é de 19/11/2026: 20/12 é o 31º dia."""
        e = apoio.exemplo()
        P(e, 0)["vigiar"][0] = "O Reino de Amostra responde com ataque militar até 20/12?"
        self.acusa(self.solta(e), "R21", caminho="principais[0].vigiar[0]")

    def test_r21_acusa_data_de_referencia_por_ultimo_na_primeira_pergunta(self):
        """ESQUEMA, seção 10, R21: "a data limite vem por último". Com a data de referência (18/11, antes da
        edição) por último, o prazo lido é 18/11 do ano seguinte."""
        e = apoio.exemplo()
        P(e, 1)["vigiar"][0] = "Até 30/11, a lei fictícia citada desde 18/11 é sancionada?"
        self.acusa(self.solta(e), "R21", caminho="principais[1].vigiar[0]")

    def test_r21_aceita_primeira_pergunta_com_prazo_no_30o_dia(self):
        """ESQUEMA, seção 10, R21: "entre `data` e 30 dias depois, os dois inclusive"."""
        e = apoio.exemplo()
        P(e, 0)["vigiar"][0] = "O Reino de Amostra responde com ataque militar até 19/12?"
        self.nao_acusa(self.solta(e), "R21")

    # --- R23 ---
    def test_r23_acusa_dossie_com_799_caracteres(self):
        """ESQUEMA, seção 10, R23: "Na principal: `realmente` tem de 800 a 1.500 caracteres"."""
        e = apoio.exemplo()
        P(e, 0)["realmente"] = texto_de(799)
        self.acusa(self.solta(e), "R23")

    def test_r23_aceita_dossie_com_800_e_com_1500_caracteres(self):
        """ESQUEMA, seção 10, R23: "de 800 a 1.500 caracteres" (os dois limites)."""
        e = apoio.exemplo()
        P(e, 0)["realmente"] = texto_de(800)
        P(e, 2)["realmente"] = texto_de(1500)
        self.nao_acusa(self.solta(e), "R23", "R17")

    def test_r23_acusa_dossie_com_1501_caracteres(self):
        """ESQUEMA, seção 10, "Qual código sai": "`realmente` fora de 800 a 1.500 caracteres: R23" (a R17,
        com os "tamanhos máximos", não sai)."""
        e = apoio.exemplo()
        P(e, 0)["realmente"] = texto_de(1501)
        res = self.solta(e)
        self.acusa(res, "R23", caminho="principais[0].realmente")
        self.assertNotIn("R17", res.regras, res.relato())

    def test_r23_acusa_dominios_sem_no_brasil(self):
        """ESQUEMA, seção 10, R23: "`no_brasil` existe se, e só se, `dominios` não é vazia"."""
        e = apoio.exemplo()
        del P(e, 0)["no_brasil"]
        self.acusa(self.solta(e), "R23")

    def test_r23_acusa_no_brasil_sem_dominios(self):
        """ESQUEMA, seção 10, R23: "`no_brasil` existe se, e só se, `dominios` não é vazia"."""
        e = apoio.exemplo()
        poe(P(e, 1), "principal", no_brasil=F + "Nada tende a mudar no Brasil por esta notícia.")
        self.acusa(self.solta(e), "R23")

    def test_r23_aceita_sem_dominios_e_sem_no_brasil(self):
        """ESQUEMA, seção 10, R23: "`no_brasil` existe se, e só se, `dominios` não é vazia"."""
        e = apoio.exemplo()
        P(e, 2)["dominios"] = []
        del P(e, 2)["no_brasil"]
        self.nao_acusa(self.solta(e), "R23")


class AlertaSemHistorico(CasoDeValida):
    """ESQUEMA, seção 10, "Alerta" (R13 a R14), com a edição sozinha: vale a saída da regra H1."""

    # --- R13 e H1 ---
    def test_r13_acusa_nivel_menor_que_o_gatilho_de_hoje(self):
        """ESQUEMA, seção 10, H1: sem histórico, "o validador aceita `nivel` igual a `T`, ou maior que `T`
        quando `desde` é anterior a `data`"; "Qual código sai": nível que não fecha com a conta é R13, com
        ou sem histórico, e "o código H1 não aparece na saída"."""
        e = apoio.exemplo()
        D(e, ENERGIA)["nivel"] = 2                         # há gatilho energia.3 hoje
        res = self.solta(e)
        self.acusa(res, "R13", caminho="alerta.dominios[0].nivel")
        self.assertNotIn("H1", res.regras, res.relato())

    def test_r13_acusa_nivel_maior_que_o_gatilho_sem_desde_anterior(self):
        """ESQUEMA, seção 10, H1: nível maior que `T` só "quando `desde` é anterior a `data` (nível
        mantido)"; "Qual código sai": R13, e "o código H1 não aparece na saída"."""
        e = apoio.exemplo()
        D(e, CAMBIO)["desde"] = e["data"]                  # câmbio está em 2, sem gatilho hoje
        res = self.solta(e)
        self.acusa(res, "R13", caminho="alerta.dominios[2].nivel")
        self.assertNotIn("H1", res.regras, res.relato())

    def test_r13_aceita_nivel_mantido_com_desde_anterior(self):
        """ESQUEMA, seção 10, H1: "aceita `nivel` […] maior que `T` quando `desde` é anterior a `data`
        (nível mantido)"."""
        e = apoio.exemplo()
        D(e, ALIMENTOS).update(nivel=2, desde="2026-11-10")
        self.nao_acusa(self.solta(e), "R13", "H1")

    def test_h1_aceita_qualquer_tendencia_sem_historico(self):
        """ESQUEMA, seção 10, H1: sem histórico à mão, o validador "não confere `tendencia`"."""
        e = apoio.exemplo()
        e["alerta"]["tendencia"] = "descendo"
        D(e, ENERGIA)["tendencia"] = "descendo"
        self.nao_acusa(self.solta(e), "R14", "H1")

    def test_h1_acusa_alivio_sem_historico(self):
        """ESQUEMA, seção 10, H1: sem histórico, o validador "recusa `alivio`"; "Qual código sai": "Alívio
        sem histórico: R13e"."""
        e = apoio.exemplo()
        D(e, CAMBIO)["gatilhos"] = [gatilho("cambio.4", "p1", F + "Acabou o estado.", alivio=True)]
        res = self.solta(e)
        self.acusa(res, "R13e", caminho="alerta.dominios[2].gatilhos[0].alivio")
        self.assertNotIn("H1", res.regras, res.relato())

    # --- R13a ---
    def test_r13a_acusa_criterio_de_nivel_1_e_de_nivel_6(self):
        """ESQUEMA, seção 10, R13a: "`criterio` tem a forma `dominio.nivel`, com nível de 2 a 5, e
        existe na régua"."""
        for criterio in ("energia.1", "energia.6", "energia"):
            with self.subTest(criterio=criterio):
                e = apoio.exemplo()
                D(e, ENERGIA)["gatilhos"][1]["criterio"] = criterio
                self.acusa(self.solta(e), "R13a")

    def test_r13a_acusa_criterio_de_outro_dominio(self):
        """ESQUEMA, seção 10, R13a: "O domínio do `criterio` é o `id` do domínio onde o gatilho está"."""
        e = apoio.exemplo()
        D(e, ENERGIA)["gatilhos"][1]["criterio"] = "conflito.3"
        self.acusa(self.solta(e), "R13a")

    def test_r13a_acusa_ref_que_nao_existe_na_edicao(self):
        """ESQUEMA, seção 10, R13a: "`ref` existe na edição: id de item, ou, só em gatilho de preço, id
        de indicador"."""
        e = apoio.exemplo()
        D(e, SUPRIMENTOS)["gatilhos"][0]["ref"] = "r9"
        self.acusa(self.solta(e), "R13a")

    def test_r13a_aceita_criterios_de_nivel_2_e_de_nivel_5_e_ref_de_indicador(self):
        """ESQUEMA, seção 10, R13a: "nível de 2 a 5" (os dois limites) e "`ref` existe na edição: id de
        item, ou, só em gatilho de preço, id de indicador". A edição traz `energia.2` com `ref` de
        indicador, `suprimentos.2` com `ref` de radar e `conflito.5` com `ref` de principal."""
        e = apoio.exemplo()
        D(e, CONFLITO)["gatilhos"][0]["criterio"] = "conflito.5"
        D(e, CONFLITO)["nivel"] = 5
        e["alerta"]["nivel"] = 5
        self.assertEqual([(g["criterio"], g["ref"]) for d in e["alerta"]["dominios"] for g in d["gatilhos"]],
                         [("energia.2", "brent"), ("energia.3", "p1"), ("suprimentos.2", "r4"), ("conflito.5", "p1")])
        self.nao_acusa(self.solta(e), "R13a")

    # --- R13b ---
    def test_r13b_acusa_nivel_3_provado_por_radar(self):
        """ESQUEMA, seção 10, R13b: "Nível 3 exige principal". O caminho segue o exemplo do CONTRATO,
        seção 3: `ERRO R13b alerta.dominios[0].gatilhos[1].ref: …`."""
        e = apoio.exemplo()
        g = D(e, SUPRIMENTOS)["gatilhos"][0]
        g["criterio"] = "suprimentos.3"
        del g["excecao"]
        D(e, SUPRIMENTOS)["nivel"] = 3
        self.acusa(self.solta(e), "R13b", caminho="alerta.dominios[3].gatilhos[0].ref")

    def test_r13b_acusa_gatilho_provado_por_item_de_confianca_baixa(self):
        """ESQUEMA, seção 10, R13b: "O item tem `confianca` `alta` ou `media`"."""
        e = apoio.exemplo()
        D(e, SUPRIMENTOS)["gatilhos"][0]["ref"] = "r3"     # r3 tem confiança baixa
        self.acusa(self.solta(e), "R13b")

    def test_r13b_acusa_nivel_4_provado_por_principal_de_confianca_media(self):
        """ESQUEMA, seção 10, R13b: "Níveis 4 e 5 exigem principal com confiança `alta`"."""
        e = apoio.exemplo()
        g = D(e, SUPRIMENTOS)["gatilhos"][0]
        g.update(criterio="suprimentos.4", ref="p2")       # p2 tem confiança media
        del g["excecao"]
        D(e, SUPRIMENTOS)["nivel"] = 4
        e["alerta"]["nivel"] = 4
        self.acusa(self.solta(e), "R13b")

    def test_r13b_acusa_nivel_5_sem_fonte_primaria(self):
        """ESQUEMA, seção 10, R13b: "Nível 5 exige ainda uma fonte `primaria` no item"."""
        e = apoio.exemplo()
        D(e, CONFLITO)["gatilhos"][0].update(criterio="conflito.5", ref="p3")     # p3: alta, sem primária
        D(e, CONFLITO)["nivel"] = 5
        e["alerta"]["nivel"] = 5
        self.acusa(self.solta(e), "R13b")

    def test_r13b_acusa_nivel_5_em_energia_sem_primaria_de_site_do_brasil(self):
        """ESQUEMA, seção 10, R13b: "em `energia`, `alimentos`, `cambio` e `suprimentos`, com site que
        bate com a lista `sites_oficiais.brasil`"."""
        e = apoio.exemplo()
        D(e, ENERGIA)["gatilhos"][1]["criterio"] = "energia.5"     # p1 tem primárias, nenhuma do Brasil
        D(e, ENERGIA)["nivel"] = 5
        e["alerta"]["nivel"] = 5
        self.acusa(self.solta(e), "R13b")

    def test_r13b_aceita_nivel_5_em_energia_com_primaria_de_site_do_brasil(self):
        """ESQUEMA, seção 10, R13b: nível 5 com principal de confiança `alta` e fonte `primaria` de
        site que bate com `sites_oficiais.brasil` (aqui, um site fictício que termina em `.gov.br`)."""
        e = apoio.exemplo()
        D(e, ENERGIA)["gatilhos"][1]["criterio"] = "energia.5"
        D(e, ENERGIA)["nivel"] = 5
        e["alerta"]["nivel"] = 5
        P(e, 0)["fontes"].append(apoio.ordena({
            "veiculo": "outro", "nome": "Ministério de Exemplo (fictício)",
            "titulo": MARCA + "Portaria fictícia de racionamento",
            "url": "https://exemplo.invalid.gov.br/portaria-1", "publicado_em": DIA_EX, "primaria": True}, "fonte"))
        self.nao_acusa(self.solta(e), "R13b")

    def test_r13b_aceita_nivel_5_em_conflito_com_primaria_qualquer(self):
        """ESQUEMA, seção 10, R13b: a primária do Brasil só é pedida "em `energia`, `alimentos`, `cambio`
        e `suprimentos`"; em `conflito` basta "uma fonte `primaria` no item"."""
        e = apoio.exemplo()
        D(e, CONFLITO)["gatilhos"][0]["criterio"] = "conflito.5"   # p1: alta, com primárias
        D(e, CONFLITO)["nivel"] = 5
        e["alerta"]["nivel"] = 5
        self.nao_acusa(self.solta(e), "R13b")

    def test_r13b_aceita_nivel_3_provado_por_principal_de_confianca_media(self):
        """ESQUEMA, seção 10, R13b: "O item tem `confianca` `alta` ou `media`. […] Nível 3 exige
        principal"."""
        e = apoio.exemplo()
        g = D(e, SUPRIMENTOS)["gatilhos"][0]
        g.update(criterio="suprimentos.3", ref="p2")
        del g["excecao"]
        D(e, SUPRIMENTOS)["nivel"] = 3
        self.nao_acusa(self.solta(e), "R13b")

    def test_r13b_aceita_nivel_4_provado_por_principal_de_confianca_alta(self):
        """ESQUEMA, seção 10, R13b: "Níveis 4 e 5 exigem principal com confiança `alta`"."""
        e = apoio.exemplo()
        D(e, CONFLITO)["gatilhos"][0]["criterio"] = "conflito.4"
        D(e, CONFLITO)["nivel"] = 4
        e["alerta"]["nivel"] = 4
        self.nao_acusa(self.solta(e), "R13b")

    def test_r13b_acusa_estado_que_continua_sem_historico(self):
        """ESQUEMA, seção 10, H1: sem histórico, o validador "trata todo gatilho como novo". Um gatilho
        de nível 4 com `ref` de radar só vale como estado que continua (R13b); sozinho, é recusado."""
        e = apoio.exemplo()
        D(e, ENERGIA)["gatilhos"][1].update(criterio="energia.4", ref="r4",
                                            texto=F + "Segue em 19/11: a rota continua fechada.")
        D(e, ENERGIA)["nivel"] = 4
        e["alerta"]["nivel"] = 4
        self.acusa(self.solta(e), "R13b")

    # --- R13c ---
    def test_r13c_acusa_alta_forte_sem_confirmacao_declarada_como_nivel_3(self):
        """ESQUEMA, seção 10, R13c: "Se ele é de nível 3 ou 4 e `confirmado` é `false`, vale como nível 2"."""
        e = apoio.exemplo()
        e["indicadores"][0]["variacao_7d_pct"] = 10.4
        D(e, ENERGIA)["gatilhos"][0]["criterio"] = "energia.3"
        self.acusa(self.solta(e), "R13c")

    def test_r13c_aceita_alta_forte_sem_confirmacao_declarada_como_nivel_2(self):
        """ESQUEMA, seção 10, R13c: "Se ele é de nível 3 ou 4 e `confirmado` é `false`, vale como nível 2"."""
        e = apoio.exemplo()
        e["indicadores"][0]["variacao_7d_pct"] = 10.4
        self.nao_acusa(self.solta(e), "R13c")

    def test_r13c_acusa_alta_forte_confirmada_declarada_como_nivel_2(self):
        """ESQUEMA, seção 10, R13c: "Fica o critério cumprido de maior nível" (com `confirmado: true`,
        o nível 3 vale)."""
        e = apoio.exemplo()
        e["indicadores"][0].update(variacao_7d_pct=10.4, confirmado=True)
        self.acusa(self.solta(e), "R13c")

    def test_r13c_aceita_alta_forte_confirmada_declarada_como_nivel_3(self):
        """ESQUEMA, seção 10, R13c: "Fica o critério cumprido de maior nível", com `ref` igual ao id do
        indicador."""
        e = apoio.exemplo()
        e["indicadores"][0].update(variacao_7d_pct=10.4, confirmado=True)
        D(e, ENERGIA)["gatilhos"][0]["criterio"] = "energia.3"
        self.nao_acusa(self.solta(e), "R13c")

    def test_r13c_acusa_falta_do_gatilho_de_preco_devido(self):
        """ESQUEMA, seção 10, R13c: "O domínio traz exatamente esses gatilhos de preço"."""
        e = apoio.exemplo()
        del D(e, ENERGIA)["gatilhos"][0]                   # o Brent subiu 6,1% em 7 dias: o gatilho é devido
        self.acusa(self.solta(e), "R13c")

    def test_r13c_acusa_gatilho_de_preco_que_nao_e_devido(self):
        """ESQUEMA, seção 10, R13c: "O domínio traz exatamente esses gatilhos de preço"."""
        e = apoio.exemplo()
        D(e, ALIMENTOS).update(nivel=2, desde=e["data"], gatilhos=[
            {"criterio": "alimentos.2", "ref": "trigo", "texto": F + "Trigo subiu 1,0% em 7 dias, até 19/11."}])
        self.acusa(self.solta(e), "R13c")

    def test_r13c_aceita_alta_igual_ao_limiar(self):
        """CONTRATO, seção 2, passo 7: "variação já arredondada maior ou igual a `alta_minima_pct`";
        ESQUEMA, seção 10, R13c."""
        e = apoio.exemplo()
        e["indicadores"][0]["variacao_7d_pct"] = 5.0
        self.nao_acusa(self.solta(e), "R13c")

    def test_r13c_acusa_gatilho_com_alta_abaixo_do_limiar(self):
        """ESQUEMA, seção 10, R13c: "valem os critérios `precos` da régua" (Brent: 5% em 7 dias)."""
        e = apoio.exemplo()
        e["indicadores"][0]["variacao_7d_pct"] = 4.9
        self.acusa(self.solta(e), "R13c")

    def test_r13c_aceita_alta_abaixo_do_limiar_sem_gatilho(self):
        """ESQUEMA, seção 10, R13c: abaixo do limiar não há gatilho de preço."""
        e = apoio.exemplo()
        e["indicadores"][0]["variacao_7d_pct"] = 4.9
        del D(e, ENERGIA)["gatilhos"][0]
        self.nao_acusa(self.solta(e), "R13c")

    def test_r13c_aceita_queda_sem_gatilho(self):
        """ESQUEMA, seção 10, R13c: "só alta conta"."""
        e = apoio.exemplo()
        e["indicadores"][0]["variacao_7d_pct"] = -6.0
        del D(e, ENERGIA)["gatilhos"][0]
        self.nao_acusa(self.solta(e), "R13c")

    def test_r13c_aceita_indicador_defasado_sem_gatilho(self):
        """ESQUEMA, seção 10, R13c: "Para cada indicador não defasado" (o defasado não dá gatilho, e o
        domínio fica cego: R13f)."""
        e = apoio.exemplo()
        e["indicadores"][0].update(defasado=True, data="2026-11-12")
        del D(e, ENERGIA)["gatilhos"][0]
        D(e, ENERGIA)["sem_preco"] = ["brent"]
        self.nao_acusa(self.solta(e), "R13c", "R13f")

    def test_r13c_acusa_alta_do_dolar_no_dia_sem_gatilho(self):
        """ESQUEMA, seção 10, R13c: "critério de janela `1d` só vale quando a `data` do indicador é a
        `data` da edição" (aqui é, e a alta de 1,8% cumpre o limiar de 1,5%)."""
        e = apoio.exemplo()
        e["indicadores"][7]["variacao_pct"] = 1.8
        self.acusa(self.solta(e), "R13c")

    def test_r13c_aceita_alta_do_dolar_no_dia_com_gatilho(self):
        """ESQUEMA, seção 10, R13c: gatilho de preço "com `ref` igual ao id do indicador"."""
        e = apoio.exemplo()
        e["indicadores"][7]["variacao_pct"] = 1.8
        D(e, CAMBIO)["gatilhos"] = [{"criterio": "cambio.2", "ref": "usd_brl",
                                     "texto": F + "Dólar em reais subiu 1,8% no dia 19/11 (limiar: 1,5%)."}]
        self.nao_acusa(self.solta(e), "R13c")

    def test_r13c_aceita_alta_do_dolar_com_cotacao_de_outro_dia(self):
        """ESQUEMA, seção 10, R13c: "critério de janela `1d` só vale quando a `data` do indicador é a
        `data` da edição"."""
        e = apoio.exemplo()
        e["indicadores"][7].update(variacao_pct=1.8, data="2026-11-18")
        self.nao_acusa(self.solta(e), "R13c")

    # --- R13d ---
    def test_r13d_acusa_excecao_com_nivel_4(self):
        """ESQUEMA, seção 10, R13d: "`excecao: true` só com nível 2 ou 3"."""
        e = apoio.exemplo()
        D(e, SUPRIMENTOS)["gatilhos"][0].update(criterio="suprimentos.4", ref="p1")
        D(e, SUPRIMENTOS)["nivel"] = 4
        e["alerta"]["nivel"] = 4
        self.acusa(self.solta(e), "R13d")

    def test_r13d_acusa_duas_excecoes_na_edicao(self):
        """ESQUEMA, seção 10, R13d: "no máximo 1 por edição"."""
        e = apoio.exemplo()
        poe(D(e, CONFLITO)["gatilhos"][0], "gatilho", excecao=True)
        self.acusa(self.solta(e), "R13d")

    def test_r13d_acusa_excecao_em_gatilho_de_preco(self):
        """ESQUEMA, seção 10, R13d: "`excecao: true` só com […] `ref` de item"."""
        e = apoio.exemplo()
        poe(D(e, ENERGIA)["gatilhos"][0], "gatilho", excecao=True)
        D(e, SUPRIMENTOS)["gatilhos"] = []                 # para a exceção plantada ser a única da edição
        D(e, SUPRIMENTOS).update(nivel=2, desde="2026-11-17", tendencia="estavel")
        self.acusa(self.solta(e), "R13d")

    def test_r13d_aceita_excecao_de_nivel_3_com_principal(self):
        """ESQUEMA, seção 10, R13d: "`excecao: true` só com nível 2 ou 3, `ref` de item, e no máximo 1
        por edição"."""
        e = apoio.exemplo()
        D(e, SUPRIMENTOS)["gatilhos"][0].update(criterio="suprimentos.3", ref="p1")
        D(e, SUPRIMENTOS)["nivel"] = 3
        self.nao_acusa(self.solta(e), "R13d")

    # --- R13f ---
    def test_r13f_acusa_sem_preco_vazia_com_indicador_sem_base(self):
        """ESQUEMA, seção 10, R13f: `sem_preco` lista os indicadores dos critérios `precos` do domínio
        que "têm `variacao_7d_pct` `null`" (o milho do exemplo)."""
        e = apoio.exemplo()
        D(e, ALIMENTOS)["sem_preco"] = []
        self.acusa(self.solta(e), "R13f")

    def test_r13f_acusa_sem_preco_fora_da_ordem_do_catalogo(self):
        """ESQUEMA, seção 10, R13f: "`sem_preco` lista, na ordem do catálogo"."""
        e = apoio.exemplo()
        e["indicadores"][3]["variacao_7d_pct"] = None      # trigo
        D(e, ALIMENTOS)["sem_preco"] = ["milho", "trigo"]
        self.acusa(self.solta(e), "R13f")

    def test_r13f_aceita_os_quatro_casos_de_falta_de_preco(self):
        """ESQUEMA, seção 10, R13f: os indicadores "que hoje faltam em `indicadores`, têm `valor` `null`,
        têm `defasado: true` ou têm `variacao_7d_pct` `null`", na ordem do catálogo."""
        e = apoio.exemplo()
        e["indicadores"][3].update(valor=None, variacao_pct=None, variacao_7d_pct=None, data=None, defasado=True)
        e["indicadores"][7].update(defasado=True, data="2026-11-12")                 # dólar com cotação velha
        e["indicadores"] = [i for i in e["indicadores"] if i["id"] != "soja"]        # a soja falta
        D(e, ALIMENTOS)["sem_preco"] = ["trigo", "milho", "soja"]
        D(e, CAMBIO)["sem_preco"] = ["usd_brl"]
        self.nao_acusa(self.solta(e), "R13f")

    # --- R14 ---
    def test_r14_acusa_nivel_geral_diferente_do_maior_dominio(self):
        """ESQUEMA, seção 10, R14: "`alerta.nivel` é o maior nível dos domínios"."""
        e = apoio.exemplo()
        e["alerta"]["nivel"] = 2
        self.acusa(self.solta(e), "R14")

    def test_r14_acusa_desde_depois_da_data(self):
        """ESQUEMA, seção 2, tabela dos domínios: `desde` é o "dia em que o nível atual começou; nunca
        depois de `data`"; seção 10, "Qual código sai": "Nível, tendência ou `desde` que não fecham com a
        conta: R13 e R14"."""
        e = apoio.exemplo()
        D(e, ENERGIA)["desde"] = mais_dias(DIA_EX, 1)
        self.acusa(self.solta(e), "R14", caminho="alerta.dominios[0].desde")


class ContagensTextoEMarcas(CasoDeValida):
    """ESQUEMA, seção 10, "Contagens, texto e marcas": R15 a R18 e R20."""

    # --- R15 ---
    def test_r15_acusa_completa_com_duas_principais(self):
        """ESQUEMA, seção 10, R15, tabela: `completa` tem 3 principais."""
        e = apoio.exemplo()
        e["principais"] = e["principais"][:2]
        self.acusa(self.solta(apoio.acerta(e)), "R15")

    def test_r15_acusa_completa_com_cinco_no_radar(self):
        """ESQUEMA, seção 10, R15, tabela: `completa` tem de 6 a 12 no radar."""
        e = apoio.exemplo()
        e["radar"] = e["radar"][:5]
        self.acusa(self.solta(apoio.acerta(e)), "R15")

    def test_r15_acusa_completa_com_treze_no_radar(self):
        """ESQUEMA, seção 10, R15, tabela: `completa` tem de 6 a 12 no radar."""
        e = apoio.exemplo()
        self._mais_radar(e, 13)
        self.acusa(self.solta(apoio.acerta(e)), "R15")

    def test_r15_aceita_completa_com_doze_no_radar(self):
        """ESQUEMA, seção 10, R15, tabela: `completa` tem de 6 a 12 no radar (o limite de cima)."""
        e = apoio.exemplo()
        self._mais_radar(e, 12)
        self.nao_acusa(self.solta(apoio.acerta(e)), "R15")

    def test_r15_acusa_completa_com_dois_de_ia_no_radar(self):
        """ESQUEMA, seção 10, R15, tabela: `completa` tem 3 ou mais itens de IA no radar."""
        e = apoio.exemplo()
        R(e, 2)["categoria"] = "geopolitica"
        self.acusa(self.solta(e), "R15")

    def test_r15_acusa_completa_sem_geopolitica_nas_principais(self):
        """ESQUEMA, seção 10, R15, tabela: `completa` tem 1 ou mais principais de geopolítica."""
        e = apoio.exemplo()
        for i in (0, 2):
            poe(P(e, i), "principal", categoria="ia", conflito_de_interesse=True, confianca="media")
        self.acusa(self.solta(e), "R15")

    def test_r15_acusa_reduzida_com_dois_no_radar(self):
        """ESQUEMA, seção 10, R15, tabela: `reduzida` tem de 3 a 12 no radar."""
        e = apoio.exemplo()
        e["estado"] = "reduzida"
        e["radar"] = e["radar"][3:5]
        for i, r in enumerate(e["radar"]):
            r["id"] = "r%d" % (i + 1)
        D(e, SUPRIMENTOS)["gatilhos"][0]["ref"] = "r1"
        self.acusa(self.solta(apoio.acerta(e)), "R15")

    def test_r15_acusa_reduzida_sem_principal(self):
        """ESQUEMA, seção 10, R15, tabela: `reduzida` tem de 1 a 3 principais."""
        e = apoio.exemplo()
        e["estado"] = "reduzida"
        e["principais"] = []
        self.acusa(self.solta(apoio.acerta(e)), "R15")

    def test_r15_aceita_reduzida_com_uma_principal_e_tres_no_radar_sem_ia(self):
        """ESQUEMA, seção 10, R15, tabela: `reduzida` tem 1 a 3 principais, 3 a 12 no radar e "0 ou
        mais" de IA."""
        e = apoio.exemplo()
        e["estado"] = "reduzida"
        e["principais"] = e["principais"][:1]
        e["radar"] = e["radar"][3:]
        for i, r in enumerate(e["radar"]):
            r["id"] = "r%d" % (i + 1)
        D(e, SUPRIMENTOS)["gatilhos"][0]["ref"] = "r1"
        self.nao_acusa(self.solta(apoio.acerta(e)), "R15")

    def _mais_radar(self, e, total):
        """Completa o radar até `total` itens, com cópias do r5 (uma fonte forte, sem placar)."""
        for n in range(len(e["radar"]) + 1, total + 1):
            novo = copy.deepcopy(R(e, 4))
            novo["id"] = "r%d" % n
            novo["titulo"] = MARCA + "Banco central fictício número %d mantém juros" % n
            e["radar"].append(novo)

    # --- R16 ---
    def test_r16_acusa_errata_de_edicao_do_mesmo_dia(self):
        """ESQUEMA, seção 10, R16: "`errata[].edicao` e `respostas[].edicao` são anteriores a `data`"."""
        e = apoio.exemplo()
        e["errata"][0]["edicao"] = e["data"]
        self.acusa(self.solta(e), "R16")

    def test_r16_acusa_resposta_de_edicao_posterior(self):
        """ESQUEMA, seção 10, R16: "`respostas[].edicao` são anteriores a `data`"."""
        e = apoio.exemplo()
        e["respostas"][0]["edicao"] = mais_dias(DIA_EX, 2)
        self.acusa(self.solta(e), "R16")

    def test_r16_acusa_continuacao_de_para_o_mesmo_dia(self):
        """ESQUEMA, seção 10, R16: "`continuacao_de` aponta para data anterior a `data`"."""
        e = apoio.exemplo()
        P(e, 1)["continuacao_de"] = e["data"] + "/p2"
        self.acusa(self.solta(e), "R16")

    def test_r16_acusa_anula_vetor_sem_url(self):
        """ESQUEMA, seção 10, R16: "`errata[].anula_vetor` exige `url` na mesma errata"."""
        e = apoio.exemplo()
        del e["errata"][1]["url"]
        self.acusa(self.solta(e), "R16")

    def test_r16_acusa_resposta_sim_e_resposta_nao_sem_url(self):
        """ESQUEMA, seção 10, R16: "`respostas[].url` existe quando a `resposta` é `sim` ou `nao`"."""
        for indice in (0, 1):
            with self.subTest(resposta=apoio.exemplo()["respostas"][indice]["resposta"]):
                e = apoio.exemplo()
                del e["respostas"][indice]["url"]
                self.acusa(self.solta(e), "R16")

    def test_r16_acusa_resposta_com_item_de_radar(self):
        """ESQUEMA, seção 10, R16: "`respostas[].item` é id de principal"."""
        e = apoio.exemplo()
        e["respostas"][0]["item"] = "r1"
        self.acusa(self.solta(e), "R16")

    def test_r16_aceita_errata_so_com_os_campos_obrigatorios(self):
        """ESQUEMA, seção 8: em `errata`, `item` e `url` são opcionais ("sem o campo, vale para a edição
        toda"); seção 10, R16: a `url` só é exigida com `anula_vetor`."""
        e = apoio.exemplo()
        del e["errata"][0]["item"]
        del e["errata"][0]["url"]
        self.nao_acusa(self.solta(e), "R16")

    # --- R17 ---
    def test_r17_acusa_o_que_nao_pode_estar_em_texto(self):
        """ESQUEMA, seção 10, R17: "sem `<` seguido de letra ou barra; sem caractere de controle; sem
        e-mail; […] sem endereço (`http`, `www.`), sem `](` e sem `![` fora de campo `url`; sem número no
        formato de CPF […] nem de telefone". No trecho cortado, a regra lista três começos de caminho
        de computador (pasta de usuário de Linux, de Mac e disco de Windows): os três são plantados."""
        barra = "/"
        plantados = {
            "marca de HTML": "Veja <b>isto.",
            "fecho de marca de HTML": "Veja isto</p> agora.",
            "caractere de controle": "Veja\u0007isto.",
            "e-mail": "Escreva para redacao" + "@" + "jornal.exemplo.invalid.",
            "caminho de computador (home)": "Está em " + barra + "home" + barra + "alguem.",
            "caminho de computador (Users)": "Está em " + barra + "Users" + barra + "alguem.",
            "caminho de computador (C:)": "Está em C:" + "\\" + "pasta.",
            "endereço com www": "Leia em www.exemplo.invalid.",
            "endereço com http": "Leia em http://exemplo.invalid/pagina.",
            "marca de link": "Leia [aqui](pagina).",
            "marca de imagem": "Veja ![a figura].",
            "CPF": "O documento é 123.456.789-09.",
            "telefone com DDD": "Contato: (11) 91234-5678.",
            "telefone com sinal de mais": "Contato: +5511912345678.",
        }
        for nome, trecho in plantados.items():
            with self.subTest(plantado=nome):
                e = apoio.exemplo()
                P(e, 2)["na_pratica"][0] = F + trecho
                self.acusa(self.solta(e), "R17")

    def test_r17_acusa_quebra_de_linha_e_tabulacao(self):
        """ESQUEMA, seção 10, R17: "sem caractere de controle (os de código 0 a 31 e 127 a 159, que incluem
        a quebra de linha e a tabulação, e os separadores U+2028 e U+2029: todo texto é corrido, numa linha
        só)". Vale também no dossiê (`realmente`), escrito em parágrafos."""
        for nome, trecho in (("quebra de linha", "Veja\nisto."), ("retorno", "Veja\risto."),
                             ("tabulação", "Veja\tisto."), ("separador de linha", "Veja\u2028isto."),
                             ("controle C1", "Veja\u0085isto.")):
            with self.subTest(plantado=nome):
                e = apoio.exemplo()
                P(e, 2)["na_pratica"][0] = F + trecho
                self.acusa(self.solta(e), "R17", caminho="principais[2].na_pratica[0]")
        e = apoio.exemplo()
        texto = P(e, 0)["realmente"]
        P(e, 0)["realmente"] = texto[:400] + "\n" + texto[401:]       # dois parágrafos, mesmo tamanho
        self.acusa(self.solta(e), "R17", caminho="principais[0].realmente")

    def test_r17_acusa_metade_solta_de_caractere(self):
        """ESQUEMA, seção 10, R17: "sem metade solta de caractere (U+D800 a U+DFFF, como a de um emoji
        escrito pela metade: não se grava em UTF-8)". O arquivo traz a metade escrita como `\\ud83d`."""
        e = apoio.exemplo()
        R(e, 2)["fato"] += " " + chr(0xD83D)
        caminho = os.path.join(self.pasta("solta"), "metade.json")
        apoio.grava_texto(caminho, json.dumps(e) + "\n")                  # ensure_ascii: o arquivo é UTF-8 válido
        self.acusa(self.valida("--edicao", caminho, raiz=self.nova_raiz()), "R17", caminho="radar[2].fato")

    def test_r17_acusa_marca_de_link_em_titulo_de_fonte(self):
        """ESQUEMA, seção 10, R17: "sem `](` e sem `![` fora de campo `url`" (vale também no título de
        fonte, que é texto de terceiro)."""
        e = apoio.exemplo()
        P(e, 0)["fontes"][0]["titulo"] = MARCA + "[Leia](x)"
        self.acusa(self.solta(e), "R17")

    def test_r17_aceita_sinal_de_menor_seguido_de_espaco_ou_numero(self):
        """ESQUEMA, seção 10, R17: o proibido é "`<` seguido de letra ou barra"."""
        e = apoio.exemplo()
        P(e, 2)["na_pratica"][0] = F + "A alta ficou < 5% e a queda foi > 2%; no limite, <3%."
        self.nao_acusa(self.solta(e), "R17")

    def test_r17_acusa_texto_maior_que_o_maximo(self):
        """ESQUEMA, seção 10, R17: "Texto: tamanhos máximos" (`resumo`: 240)."""
        e = apoio.exemplo()
        e["resumo"] = MARCA + texto_de(241 - len(MARCA))
        self.acusa(self.solta(e), "R17")

    def test_r17_aceita_texto_do_tamanho_maximo(self):
        """ESQUEMA, seção 1: `resumo` tem no máximo 240 caracteres; seção 0: "Tamanho máximo é em
        caracteres"."""
        e = apoio.exemplo()
        e["resumo"] = MARCA + texto_de(240 - len(MARCA))
        self.assertEqual(len(e["resumo"]), 240)
        self.nao_acusa(self.solta(e), "R17")

    def test_r17_acusa_texto_vazio(self):
        """ESQUEMA, seção 10, R17: "nenhum texto vazio"."""
        e = apoio.exemplo()
        e["bastidores"]["limites"] = ""
        self.acusa(self.solta(e), "R17")

    def test_r17_acusa_texto_so_de_algarismos(self):
        """ESQUEMA, seção 10, R17: "nenhum texto feito só de algarismos (é sobra do `modelo.txt`)"."""
        e = apoio.exemplo()
        R(e, 0)["sem_placar"] = "160"
        self.acusa(self.solta(e), "R17")

    def test_r17_aceita_titulo_de_fonte_so_de_algarismos(self):
        """ESQUEMA, seção 10, R17: "nenhum texto feito só de algarismos […], salvo `fontes[].titulo`"."""
        e = monta_edicao(DIA, rica=True)
        P(e, 0)["fontes"][0]["titulo"] = "1984"
        self.nao_acusa(self.solta(e), "R17")

    def test_r17_acusa_url_fora_do_formato(self):
        """ESQUEMA, seção 10, R17: "URL no formato da seção 0"; seção 0: "**URL** começa com `http://` ou
        `https://` (em minúsculas), tem nome de site, tem até 500 caracteres e não tem espaço, caractere de
        controle […] nem os caracteres invisíveis de direção de texto e de largura zero"."""
        ruins = {
            "esquema que não é http": "ftp://exemplo.invalid/reuters/terminal-para",
            "espaço": "https://exemplo.invalid/reuters/terminal para",
            "501 caracteres": "https://exemplo.invalid/reuters/" + "a" * (501 - len("https://exemplo.invalid/reuters/")),
            "caractere de controle": "https://exemplo.invalid/reuters/terminal" + chr(0x01) + "para",
            "largura zero": "https://exemplo.invalid/reuters/terminal" + chr(0x200B) + "para",
            "direção de texto": "https://exemplo.invalid/reuters/terminal" + chr(0x202E) + "para",
            "sem nome de site": "https:///reuters/terminal-para",
        }
        for nome, url in ruins.items():
            with self.subTest(url=nome):
                e = apoio.exemplo()
                P(e, 0)["fontes"][0]["url"] = url
                self.acusa(self.solta(e), "R17")

    def test_r17_acusa_url_com_sinal_de_shell_barra_invertida_ou_usuario(self):
        """ESQUEMA, seção 0, "URL": "Também não tem aspas (`"`), apóstrofo (`'`), crase (`` ` ``), cifrão (`$`)
        nem barra invertida (`\\`), e não traz usuário nem senha antes do nome do site"."""
        base = "https://exemplo.invalid/reuters/"
        ruins = {
            "aspas": base + 'terminal"para', "apóstrofo": base + "terminal'para", "crase": base + "terminal`id`",
            "cifrão": base + "terminal-$(id)", "barra invertida": "https://golpe.invalid\\@exemplo.invalid/reuters/x",
            "usuário": "https://alguem@exemplo.invalid/reuters/terminal-para",
            "usuário e senha": "https://alguem:senha@exemplo.invalid/reuters/terminal-para",
        }
        for nome, url in ruins.items():
            with self.subTest(url=nome):
                e = apoio.exemplo()
                P(e, 0)["fontes"][0]["url"] = url
                self.acusa(self.solta(e), "R17")

    def test_r17_aceita_arroba_no_caminho_da_url(self):
        """ESQUEMA, seção 0: o proibido é o usuário "antes do nome do site"; arroba no caminho é caminho."""
        e = apoio.exemplo()
        P(e, 0)["fontes"][0]["url"] = "https://exemplo.invalid/reuters/@perfil/terminal-para"
        self.nao_acusa(self.solta(e), "R17")

    def test_r17_acusa_marca_que_reordena_o_texto(self):
        """ESQUEMA, seção 10, R17: "sem as marcas que reordenam o texto (U+202A a U+202E e U+2066 a U+2069
        […])". Vale também no título de fonte, copiado da página."""
        for codigo in (0x202A, 0x202E, 0x2066, 0x2069):
            with self.subTest(codigo=hex(codigo)):
                e = apoio.exemplo()
                P(e, 0)["fontes"][0]["titulo"] = MARCA + "Título" + chr(codigo) + " fictício"
                self.acusa(self.solta(e), "R17", caminho="principais[0].fontes[0].titulo")

    def test_r17_aceita_marca_simples_de_direcao_e_emoji_composto(self):
        """ESQUEMA, seção 10, R17: "U+200E, U+200F e o U+200D dos emojis podem"."""
        e = apoio.exemplo()
        P(e, 0)["fontes"][0]["titulo"] = MARCA + "Título" + chr(0x200F) + " fictício " + chr(0x1F469) + chr(0x200D) + chr(0x1F52C)
        self.nao_acusa(self.solta(e), "R17")

    def test_r17_aceita_http_sem_dois_pontos(self):
        """ESQUEMA, seção 10, R17: "sem endereço (`http:`, `https:` e `www.` em qualquer caixa, e `://`;
        "HTTP 403" não é endereço)"."""
        e = apoio.exemplo()
        e["bastidores"]["limites"] = F + "O proxy recusou a ligação (HTTP 403) em dois feeds."
        self.nao_acusa(self.solta(e), "R17")
        e["bastidores"]["limites"] = F + "Leia em http:pagina."
        self.acusa(self.solta(e), "R17", caminho="bastidores.limites")

    def test_r17_aceita_url_de_500_caracteres(self):
        """ESQUEMA, seção 0: a URL "tem até 500 caracteres"."""
        e = apoio.exemplo()
        url = "https://exemplo.invalid/reuters/" + "a" * (500 - len("https://exemplo.invalid/reuters/"))
        self.assertEqual(len(url), 500)
        P(e, 0)["fontes"][0]["url"] = url
        self.nao_acusa(self.solta(e), "R17")

    def test_r17_acusa_arquivo_maior_que_60_kb(self):
        """ESQUEMA, seção 10, R17: "Arquivo até 60 KB". O arquivo plantado tem o mesmo conteúdo do
        exemplo, gravado com recuo largo: passa de 80 KB sem estourar nenhum texto."""
        caminho = os.path.join(self.pasta("solta"), "gordo.json")
        apoio.grava_texto(caminho, json.dumps(apoio.exemplo(), ensure_ascii=False, indent=40) + "\n")
        self.assertGreater(os.path.getsize(caminho), 80 * 1024)
        self.acusa(self.valida("--edicao", caminho, raiz=self.nova_raiz()), "R17")

    def test_r17_acusa_data_fora_do_formato(self):
        """ESQUEMA, seção 0: "**Data** é texto `AAAA-MM-DD`"; seção 10, "Qual código sai": "Tipo errado,
        data ou data-hora mal escrita: R00"."""
        e = apoio.exemplo()
        P(e, 0)["fontes"][0]["publicado_em"] = "19/11/2026"
        self.acusa(self.solta(e), "R00", caminho="principais[0].fontes[0].publicado_em")

    # --- R18 ---
    def test_r18_acusa_titulo_sem_a_marca_em_edicao_de_exemplo(self):
        """ESQUEMA, seção 10, R18: "Com `exemplo: true`, todo `titulo` (de item e de fonte) começa com
        `[EXEMPLO]`"."""
        e = apoio.exemplo()
        P(e, 0)["titulo"] = P(e, 0)["titulo"][len(MARCA):]
        self.acusa(self.solta(e), "R18")

    def test_r18_acusa_titulo_de_fonte_sem_a_marca_em_edicao_de_exemplo(self):
        """ESQUEMA, seção 10, R18: "todo `titulo` (de item e de fonte) começa com `[EXEMPLO]`"."""
        e = apoio.exemplo()
        R(e, 5)["fontes"][1]["titulo"] = R(e, 5)["fontes"][1]["titulo"][len(MARCA):]
        self.acusa(self.solta(e), "R18")

    def test_r18_acusa_titulo_com_a_marca_em_edicao_de_verdade(self):
        """ESQUEMA, seção 10, R18: "Sem `exemplo`, nenhum título começa assim"."""
        e = monta_edicao(DIA, rica=True)
        R(e, 0)["titulo"] = MARCA + R(e, 0)["titulo"]
        self.acusa(self.solta(e), "R18")

    def test_r18_aceita_edicao_de_verdade_sem_a_marca(self):
        """ESQUEMA, seção 10, R18: "Sem `exemplo`, nenhum título começa assim" (caso certo)."""
        self.nao_acusa(self.solta(monta_edicao(DIA, rica=True)), "R18")

    # --- R20 ---
    def test_r20_acusa_dois_players_novos(self):
        """ESQUEMA, seção 10, R00: contagem fora da tabela é R00, mas "onde uma regra numerada dá o número,
        sai ela: […] R20 (mais de 1 player novo)"."""
        e = apoio.exemplo()
        outro = copy.deepcopy(e["novos_players"][0])
        outro["id"], outro["nome"] = "reino_de_amostra", "Reino de Amostra"
        e["novos_players"].append(outro)
        res = self.solta(e)
        self.acusa(res, "R20", caminho="novos_players")
        self.assertNotIn("R00", res.regras, res.relato())

    def test_r20_acusa_id_que_ja_existe(self):
        """ESQUEMA, seção 10, R20: "O `id` não existe em `players.json`"."""
        e = apoio.exemplo()
        e["novos_players"][0]["id"] = "china"
        self.acusa(self.solta(e), "R20")

    def test_r20_acusa_tipo_regime(self):
        """ESQUEMA, seção 10, R20: "`tipo` nunca é `regime`"."""
        e = apoio.exemplo()
        e["novos_players"][0]["tipo"] = "regime"
        self.acusa(self.solta(e), "R20")

    def test_r20_acusa_time_discutivel_falso(self):
        """ESQUEMA, seção 10, R20: "`time_discutivel` é `true`"."""
        e = apoio.exemplo()
        e["novos_players"][0]["time_discutivel"] = False
        self.acusa(self.solta(e), "R20")

    def test_r20_aceita_dna_fora_da_ordem_da_regua(self):
        """ESQUEMA, seção 10, R20: "A ordem das chaves do `dna` não é motivo de recusa"; seção 7, `dna`:
        "outra ordem não é recusada: o `publica.py` regrava na ordem"."""
        e = apoio.exemplo()
        novo = e["novos_players"][0]
        novo["dna"] = dict(reversed(list(novo["dna"].items())))
        novo["dna_fontes"] = dict(reversed(list(novo["dna_fontes"].items())))
        self.nao_acusa(self.solta(e), "R20", "R00")

    def test_r20_acusa_dna_com_virada(self):
        """ESQUEMA, seção 10, R20: "O `dna` só traz `B`, `R`, `Y` ou `W`"."""
        e = apoio.exemplo()
        e["novos_players"][0]["dna"]["ia_depois"] = "BY"
        self.acusa(self.solta(e), "R20")

    def test_r20_acusa_dna_com_tres_posicoes_conhecidas(self):
        """ESQUEMA, seção 10, R20: o `dna` "tem 4 posições conhecidas ou mais (diferentes de `W`)"."""
        e = apoio.exemplo()
        novo = e["novos_players"][0]
        novo["dna"]["moderacao"] = "W"
        del novo["dna_fontes"]["moderacao"]
        novo["duvidas"] = []
        self.acusa(self.solta(e), "R20")

    def test_r20_acusa_dna_fontes_sem_uma_posicao_conhecida(self):
        """ESQUEMA, seção 10, R20: "`dna_fontes` tem uma URL para cada posição conhecida, e só para elas"."""
        e = apoio.exemplo()
        del e["novos_players"][0]["dna_fontes"]["imigracao"]
        self.acusa(self.solta(e), "R20")

    def test_r20_acusa_dna_fontes_de_posicao_desconhecida(self):
        """ESQUEMA, seção 10, R20: "uma URL para cada posição conhecida, e só para elas"."""
        e = apoio.exemplo()
        e["novos_players"][0]["dna_fontes"]["clima"] = "https://exemplo.invalid/outro/clima"     # clima é W
        self.acusa(self.solta(e), "R20")

    def test_r20_acusa_partido_diferente_da_conta(self):
        """ESQUEMA, seção 10, R20: "`partido` é o de `voto_tipico` com mais posições iguais às conhecidas
        do `dna`; empate dá `independentes`" (no exemplo há empate)."""
        e = apoio.exemplo()
        e["novos_players"][0]["partido"] = "soberanistas"
        self.acusa(self.solta(e), "R20")

    def test_r20_acusa_duvida_que_nao_e_tema(self):
        """ESQUEMA, seção 10, R20: "`duvidas` só traz ids de tema"."""
        e = apoio.exemplo()
        e["novos_players"][0]["duvidas"] = ["futebol"]
        self.acusa(self.solta(e), "R20")

    def test_r20_aceita_partido_com_maioria_clara(self):
        """ESQUEMA, seção 10, R20: "`partido` é o de `voto_tipico` com mais posições iguais às conhecidas
        do `dna`". Com R em 4 temas, os Soberanistas (R R R R R R R) ganham sozinhos."""
        e = apoio.exemplo()
        novo = e["novos_players"][0]
        novo["dna"].update(pandemia_depois="R", ia_depois="R", moderacao="R", imigracao="R")
        novo["partido"] = "soberanistas"
        self.nao_acusa(self.solta(e), "R20")

    def test_r20_aceita_o_proprio_registro_ja_publicado(self):
        """ESQUEMA, seção 10, R20: "O `id` não existe em `players.json`, salvo como o próprio registro já
        publicado (`origem: "rotina"` e `incluido_em` igual a `data`)"."""
        e = apoio.exemplo()
        raiz = self._com_o_player_registrado(e, e["data"])
        self.nao_acusa(self.solta(e, raiz), "R20")

    def test_r20_acusa_id_registrado_em_outro_dia(self):
        """ESQUEMA, seção 10, R20: a exceção só vale com "`incluido_em` igual a `data`"."""
        e = apoio.exemplo()
        raiz = self._com_o_player_registrado(e, mais_dias(DIA_EX, -3))
        self.acusa(self.solta(e, raiz), "R20")

    def _com_o_player_registrado(self, edicao, incluido_em):
        """Raiz em que o player novo da edição já está em dados/players.json (ESQUEMA, seção 13)."""
        raiz = self.nova_raiz()

        def poe_no_fim(arquivo):
            registro = apoio.players_registrados(edicao)[0]
            registro["incluido_em"] = incluido_em
            arquivo["players"].append(registro)

        apoio.muda_json(os.path.join(raiz, "dados", "players.json"), poe_no_fim)
        return raiz

    # --- contagens das tabelas ---
    def test_tabelas_acusam_lista_fora_da_contagem(self):
        """ESQUEMA, seções 4, 5, 8 e 9, coluna "Valores permitidos": contagens das listas (`ataques`: 2 a
        4; `na_pratica`: 1 a 4; `vigiar`: 1 a 3; `nao_confirmado`: 0 a 3; `fontes` do radar: 1 a 4;
        `placar` do radar: 0 a 2; `errata`: 0 a 5; `respostas`: 0 a 3; `candidatos` e
        `veiculos_sugeridos`: 0 a 5). Seção 10, R00: "contagem dentro do intervalo das tabelas" (nenhuma
        destas contagens tem regra numerada que dê o número)."""
        def um_ataque(e):
            P(e, 1)["ataques"] = P(e, 1)["ataques"][:1]

        def cinco_na_pratica(e):
            P(e, 1)["na_pratica"] = [F + "Mudança medida número %d." % n for n in range(1, 6)]

        def sem_vigiar(e):
            P(e, 1)["vigiar"] = []

        def quatro_vigiar(e):
            P(e, 1)["vigiar"] = ["A lei fictícia é sancionada até %02d/11?" % n for n in range(27, 31)]

        def quatro_nao_confirmado(e):
            P(e, 0)["nao_confirmado"] = ["Segundo o governo fictício, a versão %d é a certa." % n for n in range(4)]

        def cinco_fontes_no_radar(e):
            R(e, 4)["fontes"] += [fonte_do_exemplo("wsj", "juros-%d" % n) for n in range(4)]

        def tres_linhas_de_placar_no_radar(e):
            R(e, 5)["placar"].append({"partido": "centrao", "efeito": "ganha", "forca": 1, "evidencia": "contrato",
                                      "porque": F + "Bancos fictícios financiam o acordo."})
            apoio.acerta(e)

        def seis_erratas(e):
            e["errata"] = [copy.deepcopy(e["errata"][0]) for _ in range(6)]

        def quatro_respostas(e):
            e["respostas"].append(copy.deepcopy(e["respostas"][2]))

        def seis_candidatos(e):
            e["bastidores"]["candidatos"] = [{"id": "ator_%d" % n, "nome": "Ator fictício %d" % n,
                                              "motivo": F + "Apareceu numa principal."} for n in range(6)]

        def seis_veiculos_sugeridos(e):
            e["bastidores"]["veiculos_sugeridos"] = ["Jornal %d (jornal%d.exemplo.invalid)" % (n, n) for n in range(6)]

        for muda in (um_ataque, cinco_na_pratica, sem_vigiar, quatro_vigiar, quatro_nao_confirmado,
                     cinco_fontes_no_radar, tres_linhas_de_placar_no_radar, seis_erratas, quatro_respostas,
                     seis_candidatos, seis_veiculos_sugeridos):
            with self.subTest(defeito=muda.__name__):
                e = apoio.exemplo()
                muda(e)
                self.acusa(self.solta(e), "R00")

    def test_tabela_acusa_nao_confirmado_que_nao_comeca_com_segundo(self):
        """ESQUEMA, seção 4: `nao_confirmado`: "cada um começa com "Segundo ""; seção 10, R00: "valor
        dentro da lista" e dos "Valores permitidos" das tabelas."""
        e = apoio.exemplo()
        P(e, 0)["nao_confirmado"][0] = "O governo do Reino de Amostra diz que os drones partiram de outro país."
        self.acusa(self.solta(e), "R00", caminho="principais[0].nao_confirmado[0]")

    def test_tabela_acusa_gerada_em_dois_dias_depois_da_data(self):
        """ESQUEMA, seção 1: `gerada_em` tem "dia UTC igual a `data` ou ao dia seguinte"; seção 10, R00:
        valor dentro dos "Valores permitidos" da tabela."""
        e = apoio.exemplo()
        e["gerada_em"] = mais_dias(DIA_EX, 2) + "T00:30:00Z"
        self.acusa(self.solta(e), "R00", caminho="gerada_em")

    def test_tabela_aceita_gerada_em_no_dia_seguinte(self):
        """ESQUEMA, seção 1: `gerada_em` tem "dia UTC igual a `data` ou ao dia seguinte" (a rotina das
        18h de Brasília pode publicar depois das 21h, já no dia seguinte em UTC)."""
        e = apoio.exemplo()
        e["gerada_em"] = mais_dias(DIA_EX, 1) + "T01:30:00Z"
        self.passou(self.solta(e))


# =============================================================================================
# (b) Regras que precisam das outras edições: R13 e R14 com histórico, R15 em falha, H1 a H3
# =============================================================================================

class AlertaComHistorico(CasoDeValida):
    """ESQUEMA, seção 10, R13, R13b, R13e, R14 e H1, com as edições anteriores de verdade.

    Nos testes desta classe que esperam erro de nível, de tendência ou de `desde`, vale o ESQUEMA, seção 10,
    "Qual código sai": "Nível, tendência ou `desde` que não fecham com a conta: R13 e R14 […], com ou sem
    histórico"; "o código H1 não aparece na saída". O nível sai como R13; a tendência e o `desde`, como R14.
    """

    # --- R13: a conta de edições calmas ---
    def test_r13_aceita_descida_depois_de_duas_edicoes_calmas(self):
        """ESQUEMA, seção 10, R13: "se `T` < `N`, `S` ≥ 2 e a edição de hoje não é cega para o domínio:
        `nivel` = `N` − 1"."""
        d3, d2, d1 = calmaria("suprimentos", "suprimentos.2")
        hoje = monta_edicao(DIA, anterior=d1)                      # suprimentos desce para 1
        self.assertEqual(apoio.dominio_de(hoje, "suprimentos")["nivel"], 1)
        self.nao_acusa(self.no_arquivo(hoje, [d3, d2, d1]), "R13", "R14", "H1")

    def test_r13_acusa_nivel_mantido_depois_de_duas_edicoes_calmas(self):
        """Código pela classe ("Qual código sai"). ESQUEMA, seção 10, R13: com `S` ≥ 2, "`nivel` = `N` − 1"; manter
        o nível é erro."""
        d3, d2, d1 = calmaria("suprimentos", "suprimentos.2")
        hoje = monta_edicao(DIA, anterior=d1, alerta={"suprimentos": {"nivel": 2}})
        self.acusa(self.no_arquivo(hoje, [d3, d2, d1]), "R13", caminho="alerta.dominios[3].nivel")

    def test_r13_aceita_nivel_mantido_com_uma_edicao_calma(self):
        """ESQUEMA, seção 10, R13: "nos outros casos: `nivel` = `N` (nível mantido)" (aqui `S` é 1)."""
        d3, d2, d1 = calmaria("suprimentos", "suprimentos.2")
        self.nao_acusa(self.no_arquivo(d1, [d3, d2]), "R13", "R14", "H1")

    def test_r13_acusa_descida_com_uma_edicao_calma(self):
        """Código pela classe ("Qual código sai"). ESQUEMA, seção 10, R13: a descida sem gatilho pede "`S` ≥ 2"."""
        d3, d2, _ = calmaria("suprimentos", "suprimentos.2")
        cedo = monta_edicao(ONTEM, anterior=d2)                    # desce com S = 1
        self.acusa(self.no_arquivo(cedo, [d3, d2]), "R13", caminho="alerta.dominios[3].nivel")

    def test_r13_aceita_nivel_mantido_quando_uma_das_calmas_e_falha(self):
        """ESQUEMA, seção 10, R13, conta `S`: "Pule a `falha`"."""
        d3, _, _ = calmaria("suprimentos", "suprimentos.2")
        falha = apoio.edicao_falha(ANTEONTEM, "Nada funcionou neste dia fictício.", anterior=d3)
        d1 = monta_edicao(ONTEM, anterior=d3, alerta={"suprimentos": {"nivel": 2}})
        hoje = monta_edicao(DIA, anterior=d1, alerta={"suprimentos": {"nivel": 2}})     # S = 1: mantém
        self.nao_acusa(self.no_arquivo(hoje, [d3, falha, d1]), "R13", "R14", "H1")

    def test_r13_acusa_descida_quando_uma_das_calmas_e_falha(self):
        """Código pela classe ("Qual código sai"). ESQUEMA, seção 10, R13, conta `S`: "Pule a `falha`" (a falha não
        conta como edição calma)."""
        d3, _, _ = calmaria("suprimentos", "suprimentos.2")
        falha = apoio.edicao_falha(ANTEONTEM, "Nada funcionou neste dia fictício.", anterior=d3)
        d1 = monta_edicao(ONTEM, anterior=d3, alerta={"suprimentos": {"nivel": 2}})
        hoje = monta_edicao(DIA, anterior=d1)
        self.acusa(self.no_arquivo(hoje, [d3, falha, d1]), "R13", caminho="alerta.dominios[3].nivel")

    def test_r13_aceita_nivel_mantido_quando_uma_das_calmas_e_cega(self):
        """ESQUEMA, seção 10, R13, conta `S`: "Das outras, conte as que não são cegas para o domínio"."""
        d3 = monta_edicao(TRES_ANTES, alerta={"energia": {"nivel": 2, "gatilhos": [gatilho("energia.2", "r4")]}})
        d2 = cega_energia(monta_edicao(ANTEONTEM, anterior=d3, alerta={"energia": {"nivel": 2}}))
        d1 = monta_edicao(ONTEM, anterior=d2, alerta={"energia": {"nivel": 2}})
        hoje = monta_edicao(DIA, anterior=d1, alerta={"energia": {"nivel": 2}})         # S = 1: mantém
        self.nao_acusa(self.no_arquivo(hoje, [d3, d2, d1]), "R13", "R14", "H1")

    def test_r13_acusa_descida_quando_uma_das_calmas_e_cega(self):
        """Código pela classe ("Qual código sai"). ESQUEMA, seção 10, R13, conta `S`: a edição cega não conta."""
        d3 = monta_edicao(TRES_ANTES, alerta={"energia": {"nivel": 2, "gatilhos": [gatilho("energia.2", "r4")]}})
        d2 = cega_energia(monta_edicao(ANTEONTEM, anterior=d3, alerta={"energia": {"nivel": 2}}))
        d1 = monta_edicao(ONTEM, anterior=d2, alerta={"energia": {"nivel": 2}})
        hoje = monta_edicao(DIA, anterior=d1)
        self.acusa(self.no_arquivo(hoje, [d3, d2, d1]), "R13", caminho="alerta.dominios[0].nivel")

    def test_r13_aceita_nivel_mantido_quando_hoje_e_cega(self):
        """ESQUEMA, seção 10, R13: a descida pede que "a edição de hoje não é cega para o domínio"."""
        d3, d2, d1 = calmaria("energia", "energia.2")
        hoje = cega_energia(monta_edicao(DIA, anterior=d1, alerta={"energia": {"nivel": 2}}))
        self.nao_acusa(self.no_arquivo(hoje, [d3, d2, d1]), "R13", "R14", "H1")

    def test_r13_acusa_descida_quando_hoje_e_cega(self):
        """Código pela classe ("Qual código sai"). ESQUEMA, seção 10, R13: sem dado de preço hoje, o nível não desce."""
        d3, d2, d1 = calmaria("energia", "energia.2")
        hoje = cega_energia(monta_edicao(DIA, anterior=d1))
        self.acusa(self.no_arquivo(hoje, [d3, d2, d1]), "R13", caminho="alerta.dominios[0].nivel")

    def test_r13_acusa_descida_de_dois_niveis_de_uma_vez(self):
        """Código pela classe ("Qual código sai"). ESQUEMA, seção 10, R13: com `S` ≥ 2, "`nivel` = `N` − 1" (de 3
        vai a 2, e não a 1)."""
        d3 = monta_edicao(TRES_ANTES, alerta={"conflito": {"nivel": 3, "gatilhos": [gatilho("conflito.3", "p1")]}})
        d2 = monta_edicao(ANTEONTEM, anterior=d3, alerta={"conflito": {"nivel": 3}})
        d1 = monta_edicao(ONTEM, anterior=d2, alerta={"conflito": {"nivel": 3}})
        certo = monta_edicao(DIA, anterior=d1, alerta={"conflito": {"nivel": 2}})
        errado = monta_edicao(DIA, anterior=d1)
        self.nao_acusa(self.no_arquivo(certo, [d3, d2, d1]), "R13", "R14", "H1")
        self.acusa(self.no_arquivo(errado, [d3, d2, d1]), "R13", caminho="alerta.dominios[4].nivel")

    def test_r13_aceita_gatilho_de_hoje_que_sobe_o_nivel(self):
        """ESQUEMA, seção 10, R13: "se `T` ≥ `N`: `nivel` = `T`"."""
        d1 = monta_edicao(ONTEM, alerta={"conflito": {"nivel": 2, "gatilhos": [gatilho("conflito.2", "r4")]}})
        hoje = monta_edicao(DIA, anterior=d1,
                            alerta={"conflito": {"nivel": 3, "gatilhos": [gatilho("conflito.3", "p1")]}})
        self.nao_acusa(self.no_arquivo(hoje, [d1]), "R13", "R14", "H1")

    # --- R13e: alívio ---
    def _crise_de_energia(self):
        return monta_edicao(ONTEM, alerta={"energia": {"nivel": 4, "gatilhos": [gatilho("energia.4", "p1")]}})

    def _alivio(self, **mais):
        return gatilho("energia.4", "p1", F + "Acabou em %s: a rota fictícia foi reaberta." % apoio.dia_mes(DIA),
                       alivio=True, **mais)

    def test_r13e_aceita_alivio_que_desce_um_nivel(self):
        """ESQUEMA, seção 10, R13: "se `T` < `N` e há gatilho de alívio válido (R13e): `nivel` = `N` − 1";
        R13e: "`criterio` igual ao da origem; `ref` de principal com confiança `alta`"."""
        d1 = self._crise_de_energia()
        hoje = monta_edicao(DIA, anterior=d1, alerta={"energia": {"nivel": 3, "gatilhos": [self._alivio()]}})
        self.nao_acusa(self.no_arquivo(hoje, [d1]), "R13", "R13e", "R14", "H1")

    def test_r13e_acusa_alivio_sem_descida(self):
        """Código pela classe ("Qual código sai"). ESQUEMA, seção 10, R13: com alívio válido, "`nivel` = `N` − 1";
        R13e: "Gatilho de alívio não conta em `T`"."""
        d1 = self._crise_de_energia()
        hoje = monta_edicao(DIA, anterior=d1, alerta={"energia": {"nivel": 4, "gatilhos": [self._alivio()]}})
        self.acusa(self.no_arquivo(hoje, [d1]), "R13", caminho="alerta.dominios[0].nivel")

    def test_r13e_acusa_alivio_em_dominio_que_estava_no_nivel_3(self):
        """ESQUEMA, seção 10, R13e: "`alivio: true` só em domínio que estava em nível 4 ou 5 na edição
        anterior"."""
        d1 = monta_edicao(ONTEM, alerta={"energia": {"nivel": 3, "gatilhos": [gatilho("energia.3", "p1")]}})
        alivio = gatilho("energia.3", "p1", F + "Acabou o estado fictício.", alivio=True)
        hoje = monta_edicao(DIA, anterior=d1, alerta={"energia": {"nivel": 2, "gatilhos": [alivio]}})
        self.acusa(self.no_arquivo(hoje, [d1]), "R13e")

    def test_r13e_acusa_alivio_com_criterio_diferente_da_origem(self):
        """ESQUEMA, seção 10, R13e: "`criterio` igual ao da origem"."""
        d1 = self._crise_de_energia()
        alivio = gatilho("energia.3", "p1", F + "Acabou o estado fictício.", alivio=True)
        hoje = monta_edicao(DIA, anterior=d1, alerta={"energia": {"nivel": 3, "gatilhos": [alivio]}})
        self.acusa(self.no_arquivo(hoje, [d1]), "R13e")

    def test_r13e_acusa_alivio_com_ref_de_radar(self):
        """ESQUEMA, seção 10, R13e: "`ref` de principal com confiança `alta`"."""
        d1 = self._crise_de_energia()
        alivio = gatilho("energia.4", "r4", F + "Acabou o estado fictício.", alivio=True)
        hoje = monta_edicao(DIA, anterior=d1, alerta={"energia": {"nivel": 3, "gatilhos": [alivio]}})
        self.acusa(self.no_arquivo(hoje, [d1]), "R13e")

    def test_r13e_acusa_alivio_junto_com_excecao(self):
        """ESQUEMA, seção 10, R13e: o alívio vem "nunca junto com `excecao`"; "Qual código sai": "Alívio
        junto com `excecao`: R13e" (a R13d, "`excecao: true` só com nível 2 ou 3", não sai)."""
        d1 = self._crise_de_energia()
        hoje = monta_edicao(DIA, anterior=d1,
                            alerta={"energia": {"nivel": 3, "gatilhos": [self._alivio(excecao=True)]}})
        res = self.no_arquivo(hoje, [d1])
        self.acusa(res, "R13e", caminho="alerta.dominios[0].gatilhos[0].excecao")
        self.assertNotIn("R13d", res.regras, res.relato())

    def test_r13e_acusa_dois_alivios_no_mesmo_dominio(self):
        """ESQUEMA, seção 10, R13e: "no máximo 1 por domínio"."""
        d1 = self._crise_de_energia()
        hoje = monta_edicao(DIA, anterior=d1,
                            alerta={"energia": {"nivel": 3, "gatilhos": [self._alivio(), self._alivio()]}})
        self.acusa(self.no_arquivo(hoje, [d1]), "R13e")

    def test_r13e_acusa_alivio_quando_a_origem_e_gatilho_de_preco(self):
        """ESQUEMA, seção 10, R13e: "por evento: a origem do nível não é gatilho de preço nem outro
        alívio"."""
        de_preco = {"criterio": "energia.4", "ref": "brent",
                    "texto": F + "Petróleo Brent subiu 21,0%% em 7 dias, até %s (limiar: 20%%)." % apoio.dia_mes(ONTEM)}
        d1 = monta_edicao(ONTEM, alerta={"energia": {"nivel": 4, "gatilhos": [de_preco]}})
        apoio.indicador_de(d1, "brent").update(variacao_7d_pct=21.0, confirmado=True)
        hoje = monta_edicao(DIA, anterior=d1, alerta={"energia": {"nivel": 3, "gatilhos": [self._alivio()]}})
        self.acusa(self.no_arquivo(hoje, [d1]), "R13e")

    def test_r13e_aceita_alivio_quando_a_origem_tem_preco_e_evento_do_mesmo_nivel(self):
        """ESQUEMA, seção 0, "Origem do nível": "Se a mesma edição tem mais de um gatilho que serve, fica o
        de evento antes do de preço". Ontem energia ficou em 4 por preço e por evento: a origem é o evento,
        e o alívio de hoje vale (R13e: "a origem do nível não é gatilho de preço")."""
        de_preco = {"criterio": "energia.4", "ref": "brent",
                    "texto": F + "Petróleo Brent subiu 21,0%% em 7 dias, até %s (limiar: 20%%)." % apoio.dia_mes(ONTEM)}
        d1 = monta_edicao(ONTEM, alerta={"energia": {"nivel": 4, "gatilhos": [de_preco, gatilho("energia.4", "p1")]}})
        apoio.indicador_de(d1, "brent").update(variacao_7d_pct=21.0, confirmado=True)
        hoje = monta_edicao(DIA, anterior=d1, alerta={"energia": {"nivel": 3, "gatilhos": [self._alivio()]}})
        self.nao_acusa(self.no_arquivo(hoje, [d1]), "R13", "R13e", "R14")

    # --- R13b: estado que continua ---
    def test_r13b_aceita_estado_que_continua_com_ref_de_radar(self):
        """ESQUEMA, seção 10, R13b, "Estado que continua": "Gatilho de nível 4 ou 5 com o mesmo `criterio`
        da origem do nível, num domínio que estava nesse nível ou acima na edição anterior, e cuja
        origem não é alívio nem gatilho de preço, aceita principal ou radar"."""
        d1 = self._crise_de_energia()
        segue = gatilho("energia.4", "r4", F + "Segue em %s: a rota fictícia continua fechada." % apoio.dia_mes(DIA))
        hoje = monta_edicao(DIA, anterior=d1, alerta={"energia": {"nivel": 4, "gatilhos": [segue]}})
        self.nao_acusa(self.no_arquivo(hoje, [d1]), "R13b", "R13", "H1")

    def test_r13b_aceita_estado_de_nivel_5_que_continua_sem_nova_fonte_primaria(self):
        """ESQUEMA, seção 10, R13b, "Estado que continua": "e não exige de novo a fonte `primaria`"."""
        d1 = monta_edicao(ONTEM, alerta={"conflito": {"nivel": 5, "gatilhos": [gatilho("conflito.5", "p1")]}})
        segue = gatilho("conflito.5", "r4", F + "Segue em %s: o estado fictício continua." % apoio.dia_mes(DIA))
        hoje = monta_edicao(DIA, anterior=d1, alerta={"conflito": {"nivel": 5, "gatilhos": [segue]}})
        self.nao_acusa(self.no_arquivo(hoje, [d1]), "R13b", "R13", "H1")

    def test_r13b_acusa_nivel_4_por_radar_em_dominio_que_nao_estava_nesse_nivel(self):
        """ESQUEMA, seção 10, R13b: fora do estado que continua, "Níveis 4 e 5 exigem principal com
        confiança `alta`" (a crise de ontem era de energia; o gatilho de hoje é de conflito)."""
        d1 = self._crise_de_energia()
        hoje = monta_edicao(DIA, anterior=d1, alerta={
            "energia": {"nivel": 4, "gatilhos": [gatilho("energia.4", "r4", F + "Segue em 20/11: a rota continua fechada.")]},
            "conflito": {"nivel": 4, "gatilhos": [gatilho("conflito.4", "r4")]}})
        self.acusa(self.no_arquivo(hoje, [d1]), "R13b")

    # --- R14: tendência e desde ---
    def test_r14_aceita_tendencia_e_desde_calculados_contra_a_anterior(self):
        """ESQUEMA, seção 10, R14: "`alerta.tendencia` compara `alerta.nivel` com o da edição anterior; a
        `tendencia` de cada domínio compara o `nivel` do domínio com o do mesmo domínio na edição anterior
        (`subindo`, `descendo`; igual ou sem anterior, `estavel`). `desde` repete o da edição anterior se o
        nível é o mesmo; senão é `data`"."""
        d1 = monta_edicao(ONTEM)
        hoje = monta_edicao(DIA, anterior=d1, rica=True)           # energia 1→3, suprimentos 1→2, conflito 1→3
        self.assertEqual(hoje["alerta"]["tendencia"], "subindo")
        self.assertEqual(apoio.dominio_de(hoje, "alimentos")["desde"], ONTEM)
        self.nao_acusa(self.no_arquivo(hoje, [d1]), "R14", "R13", "H1")

    def test_r14_acusa_tendencia_geral_errada(self):
        """Código pela classe ("Qual código sai"). ESQUEMA, seção 10, R14: "`alerta.tendencia` compara
        `alerta.nivel` com o da edição anterior"."""
        d1 = monta_edicao(ONTEM)
        hoje = monta_edicao(DIA, anterior=d1, rica=True)
        hoje["alerta"]["tendencia"] = "estavel"                    # o nível geral foi de 1 a 3
        self.acusa(self.no_arquivo(hoje, [d1]), "R14", caminho="alerta.tendencia")

    def test_r14_acusa_tendencia_de_dominio_errada(self):
        """ESQUEMA, seção 10, R14: "a `tendencia` de cada domínio compara o `nivel` do domínio com o do
        mesmo domínio na edição anterior"."""
        d1 = monta_edicao(ONTEM)
        hoje = monta_edicao(DIA, anterior=d1, rica=True)
        apoio.dominio_de(hoje, "energia")["tendencia"] = "estavel"     # energia foi de 1 a 3
        self.acusa(self.no_arquivo(hoje, [d1]), "R14", caminho="alerta.dominios[0].tendencia")

    def test_r14_acusa_primeira_edicao_com_tendencia_subindo(self):
        """Código pela classe ("Qual código sai"). ESQUEMA, seção 10, R14: "igual ou sem anterior, `estavel`"."""
        hoje = monta_edicao(DIA, rica=True)
        hoje["alerta"]["tendencia"] = "subindo"
        self.acusa(self.no_arquivo(hoje), "R14", caminho="alerta.tendencia")

    def test_r14_aceita_primeira_edicao_com_tudo_estavel(self):
        """ESQUEMA, seção 10, R14: "igual ou sem anterior, `estavel`"; R13: `N` é "1 se não há edição
        anterior"."""
        self.nao_acusa(self.no_arquivo(monta_edicao(DIA, rica=True)), "R14", "R13", "H1")

    def test_r14_acusa_desde_de_hoje_em_nivel_que_nao_mudou(self):
        """Código pela classe ("Qual código sai"). ESQUEMA, seção 10, R14: "`desde` repete o da edição anterior se
        o nível é o mesmo"."""
        d1 = monta_edicao(ONTEM)
        hoje = monta_edicao(DIA, anterior=d1)
        apoio.dominio_de(hoje, "alimentos")["desde"] = DIA
        self.acusa(self.no_arquivo(hoje, [d1]), "R14", caminho="alerta.dominios[1].desde")

    def test_r14_acusa_desde_antigo_em_nivel_que_mudou(self):
        """Código pela classe ("Qual código sai"). ESQUEMA, seção 10, R14: "senão é `data`"."""
        d1 = monta_edicao(ONTEM)
        hoje = monta_edicao(DIA, anterior=d1, rica=True)
        apoio.dominio_de(hoje, "energia")["desde"] = ONTEM
        self.acusa(self.no_arquivo(hoje, [d1]), "R14", caminho="alerta.dominios[0].desde")

    def test_h1_anterior_forca_a_edicao_anterior(self):
        """Código pela classe ("Qual código sai": a tendência sai como R14). CONTRATO, seção 3, modo
        `--edicao`: "`--anterior ARQ` força a edição anterior (testes): o histórico passa a ser só ela".
        Com ela, a tendência passa a ser conferida, mesmo com o arquivo fora de `edicoes/`."""
        d1 = monta_edicao(ONTEM)
        anterior = self.arquivo_solto(d1, "anterior.json")
        certa = monta_edicao(DIA, anterior=d1, rica=True)
        errada = copy.deepcopy(certa)
        errada["alerta"]["tendencia"] = "descendo"
        self.nao_acusa(self.solta(certa, None, "--anterior", anterior), "R14", "R13", "H1")
        self.acusa(self.solta(errada, None, "--anterior", anterior), "R14", caminho="alerta.tendencia")


class EdicaoDeFalha(CasoDeValida):
    """ESQUEMA, seção 10, R15 (linha `falha`) e R13 ("não valem para edição `falha`")."""

    MOTIVO = "Nada funcionou neste dia fictício: sem feed e sem busca."

    def test_r15_aceita_falha_que_repete_os_niveis_da_anterior(self):
        """ESQUEMA, seção 10, R15: "Em `falha`: […] níveis e `desde` iguais aos da edição anterior";
        R13: "R13 e R13c não valem para edição `falha`"."""
        d1 = monta_edicao(ONTEM, rica=True)                        # energia 3, suprimentos 2, conflito 3
        falha = apoio.edicao_falha(DIA, self.MOTIVO, anterior=d1)
        self.nao_acusa(self.no_arquivo(falha, [d1]), "R15", "R13", "R14", "H1")

    def test_r15_aceita_falha_sem_anterior_com_tudo_em_1(self):
        """ESQUEMA, seção 10, R15: "sem anterior, tudo em 1". Sem indicadores, `sem_preco` lista todos os
        indicadores de preço do domínio ("`sem_preco` segue a R13f")."""
        falha = apoio.edicao_falha(DIA, self.MOTIVO)
        self.assertEqual(apoio.dominio_de(falha, "alimentos")["sem_preco"], ["trigo", "milho", "soja"])
        self.nao_acusa(self.no_arquivo(falha), "R15", "R13f")

    def test_r15_acusa_falha_com_nivel_diferente_da_anterior(self):
        """ESQUEMA, seção 10, R15: "níveis e `desde` iguais aos da edição anterior"."""
        d1 = monta_edicao(ONTEM, rica=True)
        falha = apoio.edicao_falha(DIA, self.MOTIVO, anterior=d1)
        apoio.dominio_de(falha, "energia")["nivel"] = 1
        self.acusa(self.no_arquivo(falha, [d1]), "R15")

    def test_r15_acusa_falha_com_gatilho(self):
        """ESQUEMA, seção 10, R15: "Em `falha`: […] todos os `gatilhos` vazios"."""
        falha = apoio.edicao_falha(DIA, self.MOTIVO)
        apoio.dominio_de(falha, "conflito")["gatilhos"] = [gatilho("conflito.2", "p1")]
        self.acusa(self.no_arquivo(falha), "R15")

    def test_r15_acusa_falha_com_principal(self):
        """ESQUEMA, seção 10, R15, tabela: `falha` tem 0 principais e 0 no radar."""
        falha = apoio.edicao_falha(DIA, self.MOTIVO)
        falha["principais"] = [copy.deepcopy(monta_edicao(DIA)["principais"][2])]
        falha["principais"][0]["id"] = "p1"
        self.acusa(self.no_arquivo(falha), "R15")

    def test_r15_acusa_falha_com_placar_do_dia(self):
        """ESQUEMA, seção 10, "Qual código sai": "Edição `falha` com `placar_do_dia`: R15 e R12, os dois".
        A R15 diz "Em `falha`: `placar_do_dia` […] vazios"; a R12, que o `placar_do_dia` "tem exatamente os
        partidos que aparecem em algum `placar` do dia" (na falha, nenhum)."""
        falha = apoio.edicao_falha(DIA, self.MOTIVO)
        falha["placar_do_dia"] = [{"partido": "centrao", "saldo": 0, "narrativa": 0, "frase": F + "Dia parado."}]
        res = self.no_arquivo(falha)
        self.acusa(res, "R15", caminho="placar_do_dia")
        self.acusa(res, "R12", caminho="placar_do_dia")


class ReferenciasAoHistorico(CasoDeValida):
    """ESQUEMA, seção 10, H2 e H3."""

    def setUp(self):
        super().setUp()
        self.ontem = troca_titulos(monta_edicao(ONTEM), 0)
        self.hoje = troca_titulos(monta_edicao(DIA, anterior=self.ontem), 1)

    def _errata(self, **campos):
        errata = {"edicao": ONTEM, "item": "r3", "erro": F + "A edição anterior deu o prazo errado.",
                  "correcao": F + "O prazo certo é de 30 dias."}
        errata.update(campos)
        return apoio.ordena(errata, "errata")

    def _resposta(self, **campos):
        resposta = {"edicao": ONTEM, "item": "p1", "pergunta": self.ontem["principais"][0]["vigiar"][0],
                    "resposta": "sem_dado", "texto": F + "Nenhuma fonte de %s trouxe a resposta." % apoio.dia_mes(DIA)}
        resposta.update(campos)
        return apoio.ordena(resposta, "resposta")

    # --- H2 ---
    def test_h2_aceita_errata_de_edicao_e_item_que_existem(self):
        """ESQUEMA, seção 10, H2: "`errata[].edicao`, `continuacao_de` e `respostas[]` apontam para edição
        e item que existem"."""
        self.hoje["errata"] = [self._errata()]
        self.nao_acusa(self.no_arquivo(self.hoje, [self.ontem]), "H2")

    def test_h2_acusa_errata_de_edicao_que_nao_existe(self):
        """ESQUEMA, seção 10, H2: "apontam para edição e item que existem"; seção 8: `errata[].edicao` é
        "edição anterior que existe"."""
        self.hoje["errata"] = [self._errata(edicao=mais_dias(DIA, -5))]
        self.acusa(self.no_arquivo(self.hoje, [self.ontem]), "H2")

    def test_h2_acusa_errata_de_item_que_nao_existe(self):
        """ESQUEMA, seção 10, H2: "apontam para edição e item que existem"."""
        self.hoje["errata"] = [self._errata(item="r9")]
        self.acusa(self.no_arquivo(self.hoje, [self.ontem]), "H2")

    def test_h2_aceita_continuacao_de_principal_e_de_radar(self):
        """ESQUEMA, seção 10, H2: "(`continuacao_de`: principal ou radar)"."""
        poe(self.hoje["principais"][1], "principal", continuacao_de=ONTEM + "/p2")
        poe(self.hoje["radar"][3], "radar", continuacao_de=ONTEM + "/r5")
        self.nao_acusa(self.no_arquivo(self.hoje, [self.ontem]), "H2")

    def test_h2_acusa_continuacao_de_edicao_que_nao_existe(self):
        """ESQUEMA, seção 10, H2: "`continuacao_de` […] apontam para edição e item que existem"."""
        poe(self.hoje["principais"][1], "principal", continuacao_de=mais_dias(DIA, -5) + "/p2")
        self.acusa(self.no_arquivo(self.hoje, [self.ontem]), "H2")

    def test_h2_acusa_continuacao_de_item_que_nao_existe(self):
        """ESQUEMA, seção 10, H2: "apontam para edição e item que existem"."""
        poe(self.hoje["radar"][3], "radar", continuacao_de=ONTEM + "/r9")
        self.acusa(self.no_arquivo(self.hoje, [self.ontem]), "H2")

    def test_h2_aceita_resposta_com_a_pergunta_igual_ao_primeiro_vigiar(self):
        """ESQUEMA, seção 10, H2: "`respostas[].pergunta` é igual ao primeiro `vigiar` daquela principal"."""
        self.hoje["respostas"] = [self._resposta()]
        self.nao_acusa(self.no_arquivo(self.hoje, [self.ontem]), "H2")

    def test_h2_acusa_resposta_com_pergunta_diferente(self):
        """ESQUEMA, seção 10, H2: "`respostas[].pergunta` é igual ao primeiro `vigiar` daquela principal"."""
        self.hoje["respostas"] = [self._resposta(pergunta="O Reino de Amostra recua até 30/11?")]
        self.acusa(self.no_arquivo(self.hoje, [self.ontem]), "H2")

    def test_h2_acusa_resposta_com_o_segundo_vigiar(self):
        """ESQUEMA, seção 10, H2: a pergunta é "o primeiro `vigiar`", e não outro da mesma principal."""
        self.hoje["respostas"] = [self._resposta(pergunta=self.ontem["principais"][0]["vigiar"][1])]
        self.acusa(self.no_arquivo(self.hoje, [self.ontem]), "H2")

    def test_h2_acusa_resposta_de_principal_que_nao_existe_naquela_edicao(self):
        """ESQUEMA, seção 10, H2: "`respostas[]` apontam para edição e item que existem"."""
        ontem = self.ontem
        ontem["estado"] = "reduzida"
        ontem["principais"] = ontem["principais"][:1]
        apoio.acerta(ontem)
        hoje = troca_titulos(monta_edicao(DIA, anterior=ontem), 1)
        hoje["respostas"] = [self._resposta(item="p3", pergunta="O Reino de Amostra recua até 30/11?")]
        self.acusa(self.no_arquivo(hoje, [ontem]), "H2")

    def _com_vetor_registrado(self):
        """Põe na edição de ontem o vetor da União Europeia, para o registro de vetores ter o que anular."""
        rica = monta_edicao(ONTEM, rica=True)
        self.ontem["principais"][0]["vetores"] = copy.deepcopy(rica["principais"][0]["vetores"])
        return "%s_p1_ue" % ONTEM

    def _sem_a_anulacao_de_hoje(self, raiz):
        """Deixa o registro de vetores como estava antes de a edição de hoje ser publicada."""
        apoio.muda_json(os.path.join(raiz, "dados", "vetores.json"),
                        lambda arq: arq.update(vetores=[v for v in arq["vetores"] if v["data"] != DIA]))

    def test_h2_aceita_anula_vetor_de_vetor_registrado(self):
        """ESQUEMA, seção 10, H2: "`errata[].anula_vetor` é o `id` de um vetor de `dados/vetores.json`
        ainda não anulado". Aqui o registro ainda não tem a anulação de hoje: é como o `publica.py
        edicao` encontra o registro quando valida o rascunho."""
        ident = self._com_vetor_registrado()
        self.hoje["errata"] = [self._errata(item="p1", url="https://ec.europa.eu/exemplo/tarifa-segue",
                                            anula_vetor=ident)]
        self.nao_acusa(self.no_arquivo(self.hoje, [self.ontem], self._sem_a_anulacao_de_hoje), "H2")

    def test_h2_aceita_anula_vetor_depois_de_a_propria_edicao_registrar_a_anulacao(self):
        """ESQUEMA, seção 10, H2: "ainda não anulado por outra edição: a anulação que a própria edição já
        gravou no registro não conta". Depois de publicada, a anulação da própria edição já está em
        `dados/vetores.json` (CONTRATO, seção 4.2, passo 7), e a rotina valida de novo logo em seguida
        (CONTRATO, seção 5, sétima linha): essa validação tem de passar."""
        ident = self._com_vetor_registrado()
        self.hoje["errata"] = [self._errata(item="p1", url="https://ec.europa.eu/exemplo/tarifa-segue",
                                            anula_vetor=ident)]
        self.nao_acusa(self.no_arquivo(self.hoje, [self.ontem]), "H2")

    def test_h2_acusa_anula_vetor_de_id_que_nao_existe(self):
        """ESQUEMA, seção 10, H2: "é o `id` de um vetor de `dados/vetores.json`"."""
        self._com_vetor_registrado()
        self.hoje["errata"] = [self._errata(item="p1", url="https://ec.europa.eu/exemplo/tarifa-segue",
                                            anula_vetor="%s_p3_ue" % ONTEM)]
        self.acusa(self.no_arquivo(self.hoje, [self.ontem]), "H2")

    def test_h2_acusa_anula_vetor_de_vetor_ja_anulado(self):
        """ESQUEMA, seção 10, H2: "ainda não anulado"."""
        ident = self._com_vetor_registrado()
        self.hoje["errata"] = [self._errata(item="p1", url="https://ec.europa.eu/exemplo/tarifa-segue",
                                            anula_vetor=ident)]

        def ja_anulado(raiz):
            # a raiz foi montada com a anulação de hoje já no registro: troca por uma anulação de ontem
            def muda(arq):
                arq["vetores"] = [v for v in arq["vetores"] if "anula" not in v]
                arq["vetores"].append({"id": "%s_anula_1" % ONTEM, "data": ONTEM, "anula": ident,
                                       "porque": F + "Anulado antes.", "url": "https://ec.europa.eu/exemplo/antes"})
            apoio.muda_json(os.path.join(raiz, "dados", "vetores.json"), muda)

        self.acusa(self.no_arquivo(self.hoje, [self.ontem], ja_anulado), "H2")

    # --- H3 ---
    def test_h3_avisa_titulo_igual_ao_de_edicao_recente(self):
        """ESQUEMA, seção 10, H3: "**(dia)** Aviso, não erro: título quase igual a um das 3 últimas
        edições sem `continuacao_de`". CONTRATO, seção 3: "Aviso não muda o código de saída"; o caminho
        segue o exemplo `AVISO H3 principais[1].titulo: …`."""
        self.hoje["principais"][1]["titulo"] = self.ontem["principais"][1]["titulo"]
        res = self.no_arquivo(self.hoje, [self.ontem])
        self.avisa(res, "H3", caminho="principais[1].titulo")
        self.passou(res)

    def test_h3_nao_avisa_titulo_igual_com_continuacao_de(self):
        """ESQUEMA, seção 10, H3: o aviso é para título quase igual "sem `continuacao_de`"."""
        self.hoje["principais"][1]["titulo"] = self.ontem["principais"][1]["titulo"]
        poe(self.hoje["principais"][1], "principal", continuacao_de=ONTEM + "/p2")
        res = self.no_arquivo(self.hoje, [self.ontem])
        self.assertEqual(res.linhas_da_regra("H3", avisos=True), [], res.relato())
        self.passou(res)

    def test_h3_nao_avisa_titulos_diferentes(self):
        """ESQUEMA, seção 10, H3: sem título quase igual, não há aviso."""
        res = self.no_arquivo(self.hoje, [self.ontem])
        self.assertEqual(res.linhas_da_regra("H3", avisos=True), [], res.relato())
        self.passou(res)

    def test_h3_nao_avisa_titulo_igual_ao_de_edicao_fora_das_tres_ultimas(self):
        """ESQUEMA, seção 10, H3: "a um das 3 últimas edições"."""
        d4 = troca_titulos(monta_edicao(mais_dias(DIA, -4)), 1)                 # os mesmos títulos de hoje
        d3 = troca_titulos(monta_edicao(TRES_ANTES, anterior=d4), 0)
        d2 = troca_titulos(monta_edicao(ANTEONTEM, anterior=d3), 2)
        d1 = troca_titulos(monta_edicao(ONTEM, anterior=d2), 3)
        hoje = troca_titulos(monta_edicao(DIA, anterior=d1), 1)
        res = self.no_arquivo(hoje, [d4, d3, d2, d1])
        self.assertEqual(res.linhas_da_regra("H3", avisos=True), [], res.relato())
        self.passou(res)

    def test_h3_avisa_titulo_que_so_muda_na_caixa_e_na_pontuacao(self):
        """ESQUEMA, seção 10, H3: "**Quase igual:** os dois títulos, sem acento, sem pontuação e em
        minúsculas, têm 10 caracteres ou mais e são iguais, ou têm semelhança de 0,85 ou mais"."""
        self.hoje["principais"][1]["titulo"] = self.ontem["principais"][1]["titulo"].upper() + "!"
        res = self.no_arquivo(self.hoje, [self.ontem])
        self.avisa(res, "H3", caminho="principais[1].titulo")
        self.passou(res)

    def test_h3_falha_nao_conta_nas_tres_ultimas(self):
        """ESQUEMA, seção 10, H3: "das 3 últimas edições anteriores (as que valem como edição anterior,
        seção 0: a `falha` e o exemplo não contam)". Aqui a quarta edição para trás é a do título igual,
        mas uma das três do meio é falha: a do título igual entra nas 3."""
        d4 = troca_titulos(monta_edicao(mais_dias(DIA, -4)), 1)                 # os mesmos títulos de hoje
        falha = apoio.edicao_falha(TRES_ANTES, "Nada funcionou neste dia fictício.", anterior=d4)
        d2 = troca_titulos(monta_edicao(ANTEONTEM, anterior=d4), 2)
        d1 = troca_titulos(monta_edicao(ONTEM, anterior=d2), 3)
        hoje = troca_titulos(monta_edicao(DIA, anterior=d1), 1)
        res = self.no_arquivo(hoje, [d4, falha, d2, d1])
        self.avisa(res, "H3")
        self.passou(res)

    def _vetor_da_ue(self, edicao):
        rica = monta_edicao(edicao["data"], rica=True)
        edicao["principais"][0]["vetores"] = copy.deepcopy(rica["principais"][0]["vetores"])
        return edicao

    def test_h3_avisa_vetor_igual_a_outro_dos_ultimos_sete_dias(self):
        """ESQUEMA, seção 10, H3: "vetor igual (player e destino) a outro, de outra edição, dos últimos 7
        dias". É aviso: o código continua 0."""
        d3 = self._vetor_da_ue(troca_titulos(monta_edicao(TRES_ANTES), 0))
        hoje = self._vetor_da_ue(troca_titulos(monta_edicao(DIA, anterior=d3), 1))
        res = self.no_arquivo(hoje, [d3])
        self.assertTrue(any("vetores" in linha for linha in res.linhas_da_regra("H3", avisos=True)),
                        "esperava AVISO H3 no vetor repetido." + res.relato())
        self.passou(res)

    def test_h3_avisa_vetor_igual_ao_de_sete_dias_atras(self):
        """ESQUEMA, seção 10, H3: "dos últimos 7 dias (o sétimo dia antes de `data` conta)"."""
        d7 = self._vetor_da_ue(troca_titulos(monta_edicao(mais_dias(DIA, -7)), 0))
        hoje = self._vetor_da_ue(troca_titulos(monta_edicao(DIA, anterior=d7), 1))
        res = self.no_arquivo(hoje, [d7])
        self.assertTrue(any("vetores" in linha for linha in res.linhas_da_regra("H3", avisos=True)),
                        "esperava AVISO H3 no vetor repetido." + res.relato())
        self.passou(res)

    def test_h3_nao_avisa_vetor_igual_ao_de_oito_dias_atras(self):
        """ESQUEMA, seção 10, H3: "dos últimos 7 dias": o oitavo dia antes de `data` já não conta."""
        d8 = self._vetor_da_ue(troca_titulos(monta_edicao(mais_dias(DIA, -8)), 0))
        hoje = self._vetor_da_ue(troca_titulos(monta_edicao(DIA, anterior=d8), 1))
        res = self.no_arquivo(hoje, [d8])
        self.assertEqual(res.linhas_da_regra("H3", avisos=True), [], res.relato())
        self.passou(res)

    def test_h3_nao_avisa_vetor_igual_a_outro_de_dez_dias_atras(self):
        """ESQUEMA, seção 10, H3: "dos últimos 7 dias"."""
        d10 = self._vetor_da_ue(troca_titulos(monta_edicao(mais_dias(DIA, -10)), 0))
        hoje = self._vetor_da_ue(troca_titulos(monta_edicao(DIA, anterior=d10), 1))
        res = self.no_arquivo(hoje, [d10])
        self.assertEqual(res.linhas_da_regra("H3", avisos=True), [], res.relato())
        self.passou(res)


# =============================================================================================
# (b) `--dados`: regras M e C, e o resto da linha `--dados` da tabela de modos
# =============================================================================================

class Dados(apoio.Caso):
    """CONTRATO, seção 3, modo `--dados`; ESQUEMA, seções 14 (regras C) e 15 (regras M)."""

    def dados_com(self, arquivo, muda):
        raiz = self.nova_raiz()
        apoio.muda_json(os.path.join(raiz, "dados", arquivo + ".json"), muda)
        return self.valida("--dados", raiz=raiz)

    def test_m2_acusa_site_com_porta(self):
        """ESQUEMA, seção 15, M2: nomes de site "sem `www.`, sem barra e sem porta"."""
        self.acusa(self.dados_com("veiculos", lambda arq: arq["veiculos"][0].update(sites=["reuters.com:443"])),
                   "M2", caminho="dados/veiculos.json:veiculos[0].sites[0]")

    def test_dados_copia_congelada_passa(self):
        """CONTRATO, seção 3, modo `--dados`: a cópia congelada dos dados não tem erro (é com ela que a
        rotina começa: `python3 ferramentas/valida.py --dados`)."""
        self.passou(self.valida("--dados", raiz=self.nova_raiz()))

    # --- M1 ---
    def test_m1_acusa_mapa_sem_revisado_em(self):
        """ESQUEMA, seção 15, M1: "`revisado_em`, na raiz: a data em que o dono terminou de revisar os
        lados, ou `null` enquanto o mapa é rascunho" (o campo existe sempre)."""
        self.acusa(self.dados_com("veiculos", lambda m: m.pop("revisado_em")), "M1")

    def test_m1_acusa_revisado_em_que_nao_e_data(self):
        """ESQUEMA, seção 15, M1: `revisado_em` é "a data […] ou `null`"."""
        self.acusa(self.dados_com("veiculos", lambda m: m.update(revisado_em="em breve")), "M1")

    def test_m1_aceita_null_e_aceita_data(self):
        """ESQUEMA, seção 15, M1: "a data em que o dono terminou de revisar os lados, ou `null`"."""
        self.nao_acusa(self.valida("--dados", raiz=self.nova_raiz()), "M1")      # a cópia congelada traz null
        self.nao_acusa(self.dados_com("veiculos", lambda m: m.update(revisado_em="2026-11-22")), "M1")

    # --- M2 ---
    def test_m2_acusa_sites_fora_da_regra(self):
        """ESQUEMA, seção 15, M2: "`sites`, em cada veículo: lista de 1 a 6 nomes de site do veículo, em
        minúsculas, sem `www.` e sem barra"."""
        ruins = {
            "lista vazia": [],
            "sete nomes": ["site%d.exemplo.invalid" % n for n in range(7)],
            "com www.": ["www.reuters.com"],
            "com maiúscula": ["Reuters.com"],
            "com barra": ["reuters.com/world"],
        }
        for nome, sites in ruins.items():
            with self.subTest(sites=nome):
                def muda(m, sites=sites):
                    [v for v in m["veiculos"] if v["id"] == "reuters"][0]["sites"] = sites
                self.acusa(self.dados_com("veiculos", muda), "M2")

    def test_m2_acusa_veiculo_sem_sites(self):
        """ESQUEMA, seção 15, M2: "`sites`, em cada veículo"."""
        def muda(m):
            del [v for v in m["veiculos"] if v["id"] == "reuters"][0]["sites"]
        self.acusa(self.dados_com("veiculos", muda), "M2")

    def test_m2_aceita_um_site_e_seis_sites(self):
        """ESQUEMA, seção 15, M2: "lista de 1 a 6 nomes de site" (os dois limites)."""
        def muda(m):
            [v for v in m["veiculos"] if v["id"] == "reuters"][0]["sites"] = ["reuters.com"]
            [v for v in m["veiculos"] if v["id"] == "bbc"][0]["sites"] = ["site%d.bbc.exemplo.invalid" % n for n in range(6)]
        self.nao_acusa(self.dados_com("veiculos", muda), "M2")

    # --- C1 ---
    def test_c1_acusa_id_de_indicador_repetido(self):
        """ESQUEMA, seção 14, C1: "Ids únicos"."""
        self.acusa(self.dados_com("indicadores", lambda c: c["indicadores"][1].update(id="brent")), "C1")

    def test_c1_acusa_catalogo_com_21_indicadores(self):
        """ESQUEMA, seção 14, C1: "Lista com 1 a 20 indicadores"."""
        self.acusa(self.dados_com("indicadores", lambda c: self._completa(c, 21)), "C1")

    def test_c1_acusa_catalogo_vazio(self):
        """ESQUEMA, seção 14, C1: "Lista com 1 a 20 indicadores"."""
        self.acusa(self.dados_com("indicadores", lambda c: c.update(indicadores=[])), "C1")

    def test_c1_aceita_catalogo_com_20_indicadores(self):
        """ESQUEMA, seção 14, C1: "Lista com 1 a 20 indicadores" (o limite de cima)."""
        self.nao_acusa(self.dados_com("indicadores", lambda c: self._completa(c, 20)), "C1")

    @staticmethod
    def _completa(catalogo, total):
        modelo = [i for i in catalogo["indicadores"] if i["id"] == "dxy"][0]      # de contexto, uma fonte
        for n in range(len(catalogo["indicadores"]) + 1, total + 1):
            novo = copy.deepcopy(modelo)
            novo["id"], novo["nome"] = "extra_%d" % n, "Indicador fictício %d" % n
            catalogo["indicadores"].append(novo)

    # --- C2 ---
    def test_c2_acusa_indicador_de_criterio_de_preco_fora_do_catalogo(self):
        """ESQUEMA, seção 14, C2: "Todo `indicador` citado nos critérios `precos` de `regua.json` existe
        aqui"."""
        def muda(c):
            c["indicadores"] = [i for i in c["indicadores"] if i["id"] != "brent"]
        self.acusa(self.dados_com("indicadores", muda), "C2")

    def test_c2_acusa_indicador_de_criterio_de_preco_que_nao_e_obrigatorio(self):
        """ESQUEMA, seção 14, C2: "com `obrigatorio: true`"."""
        self.acusa(self.dados_com("indicadores", lambda c: c["indicadores"][0].update(obrigatorio=False)), "C2")

    def test_c2_acusa_indicador_de_criterio_de_preco_mensal(self):
        """ESQUEMA, seção 14, C2: "e `frequencia: diaria`"."""
        self.acusa(self.dados_com("indicadores", lambda c: c["indicadores"][0].update(frequencia="mensal")), "C2")

    def test_c2_aceita_catalogo_congelado(self):
        """ESQUEMA, seção 14, C2: no catálogo congelado, brent, trigo, milho, soja e usd_brl (os citados
        nos critérios de preço) são obrigatórios e diários."""
        self.nao_acusa(self.valida("--dados", raiz=self.nova_raiz()), "C2")

    # --- C5 ---
    def test_c5_avisa_obrigatorio_com_uma_fonte_so(self):
        """ESQUEMA, seção 14, C5: "Indicador obrigatório deve ter 2 fontes diárias ou mais"; CONTRATO,
        seção 3, modo `--dados`: "C5 como aviso". O catálogo congelado já tem 2 fontes em cada obrigatório;
        aqui o trigo fica com uma fonte só: sai aviso, e o código continua 0."""
        res = self.dados_com("indicadores", so_uma_fonte_no_trigo)
        self.avisa(res, "C5")
        self.assertNotIn("C5", res.regras, "C5 é aviso, não erro." + res.relato())
        self.passou(res)

    def test_c5_nao_avisa_com_duas_fontes_em_cada_obrigatorio(self):
        """ESQUEMA, seção 14, C5: com 2 fontes ou mais em cada obrigatório, não há o que avisar."""
        def muda(c):
            for indicador in c["indicadores"]:
                if indicador["obrigatorio"] and len(indicador["fontes"]) < 2:
                    segunda = copy.deepcopy(indicador["fontes"][0])
                    segunda["nome"] = "Segunda fonte fictícia"
                    segunda["url"] = "https://exemplo.invalid/indicadores/" + indicador["id"]
                    indicador["fontes"].append(segunda)
        res = self.dados_com("indicadores", muda)
        self.assertEqual(res.linhas_da_regra("C5", avisos=True), [], res.relato())
        self.passou(res)

    # --- o resto da linha `--dados` ---
    def test_dados_acusa_defeitos_de_estrutura_e_de_referencia(self):
        """CONTRATO, seção 3, modo `--dados`: "estrutura e referências de cada um: ids únicos; partidos,
        times, tipos e temas que existem; DNA válido; 5 domínios, cada um com `canal`, e 5 níveis com
        códigos `dominio.nivel`; `campos` […], `conflito` e `sites_oficiais` da régua, com ids que
        existem; […] catálogo de indicadores (`leitor` da lista, `faixa` e `fator` válidos); vetores e
        anulações bem formados; URLs". O CONTRATO não dá código de regra para estes: basta serem acusados."""
        def player(campo, valor):
            return lambda arq: arq["players"][0].update({campo: valor})

        casos = [
            ("players", "id de player repetido", lambda arq: arq["players"][1].update(id=arq["players"][0]["id"])),
            ("players", "partido que não existe", player("partido", "partido_verde")),
            ("players", "time que não existe", player("time", "neutro")),
            ("players", "tipo que não existe", player("tipo", "clube")),
            ("players", "DNA com letra inválida", lambda arq: arq["players"][0]["dna"].update(clima="Z")),
            ("players", "DNA com tema que não existe", lambda arq: arq["players"][0]["dna"].update(futebol="B")),
            ("regua", "domínio sem canal", lambda arq: arq["dominios"][0].pop("canal")),
            ("regua", "quatro domínios", lambda arq: arq["dominios"].pop()),
            ("regua", "código de critério errado",
             lambda arq: arq["niveis_alerta"][1]["criterios"]["energia"].update(codigo="energia.9")),
            ("regua", "campo com partido que não existe", lambda arq: arq["campos"][0]["partidos"].append("partido_verde")),
            ("regua", "lista de conflito com player que não existe", lambda arq: arq["conflito"]["players"].append("atlantida")),
            ("indicadores", "leitor fora da lista", lambda arq: arq["indicadores"][0]["fontes"][0].update(leitor="planilha")),
            ("indicadores", "faixa com min maior que max", lambda arq: arq["indicadores"][0].update(faixa={"min": 400, "max": 5})),
            ("indicadores", "fator zero", lambda arq: arq["indicadores"][0]["fontes"][0].update(fator=0)),
            ("veiculos", "lado que não é partido", lambda arq: arq["veiculos"][0].update(lado="partido_verde")),
            ("veiculos", "id de veículo repetido", lambda arq: arq["veiculos"][1].update(id=arq["veiculos"][0]["id"])),
            ("indicadores", "URL de fonte que não é http", lambda arq: arq["indicadores"][0]["fontes"][0].update(url="ftp://exemplo.invalid/brent")),
            ("vetores", "vetor sem os campos do registro", lambda arq: arq["vetores"].append({"id": "2026-11-18_p1_ue"})),
        ]
        for arquivo, nome, muda in casos:
            with self.subTest(arquivo=arquivo, defeito=nome):
                self.acusa_algo(self.dados_com(arquivo, muda))

    def test_dados_arquivo_ilegivel_da_falha(self):
        """CONTRATO, seção 3, "Situação, última linha e código": "arquivo que não existe ou ilegível (`ERRO
        ARQUIVO`)", código 1."""
        raiz = self.nova_raiz()
        apoio.grava_texto(os.path.join(raiz, "dados", "veiculos.json"), "{ isto não é JSON")
        self.falhou(self.valida("--dados", raiz=raiz))

    def test_dados_le_o_indice_se_existir(self):
        """CONTRATO, seção 3, modo `--dados`: lê "`edicoes/indice.json` se existir". Índice ilegível é
        "arquivo ilegível": código 1."""
        raiz = self.nova_raiz([monta_edicao(DIA)])
        self.passou(self.valida("--dados", raiz=raiz))
        apoio.grava_texto(os.path.join(raiz, "edicoes", "indice.json"), "{ isto não é JSON")
        self.falhou(self.valida("--dados", raiz=raiz))


# =============================================================================================
# (c) Edição do dia e edição de arquivo, em `--tudo`
# =============================================================================================

class RegrasDoDia(apoio.Caso):
    """CONTRATO, seção 3, "Edição do dia e edição de arquivo"; ESQUEMA, seção 0 e marcas **(dia)**.

    Vale para toda raiz montada à mão (esta classe e as seguintes): CONTRATO, seção 3, modo `--tudo`, "cada
    edição com seu `.md` (basta o arquivo existir: o texto não é comparado […])". O `.md` destas raízes é um
    texto de teste, e não o que o publica.py escreveria.
    """

    def raiz_com_edicao(self, edicao=None):
        return self.nova_raiz([edicao or monta_edicao(DIA, rica=True)])

    def muda_dados(self, raiz, arquivo, muda):
        apoio.muda_json(os.path.join(raiz, "dados", arquivo + ".json"), muda)

    def test_raiz_montada_a_mao_passa_em_tudo(self):
        """CONTRATO, seção 3, modo `--tudo`: "`--dados`; as regras R e H em cada edição […]; índice igual
        aos arquivos; cada edição com seu `.md` (basta o arquivo existir […]); `feed.xml` bem formado".
        A raiz tem uma edição, o índice da seção 11 do ESQUEMA, um `.md` e um feed Atom mínimo."""
        self.passou(self.valida("--tudo", "--dia", DIA, raiz=self.raiz_com_edicao()))

    def _lado_do_nyt(self, mapa):
        [v for v in mapa["veiculos"] if v["id"] == "nyt"][0]["lado"] = "centro_atlantico"

    def test_dia_acusa_mudanca_de_lado_no_mapa_na_edicao_do_dia(self):
        """CONTRATO, seção 3: "Se o dono mudar o mapa no mesmo dia, depois da edição, o validador pode
        acusar a edição do dia". A regra é a R03, **(dia)**. "Em `--tudo`, o caminho começa com o nome
        do arquivo"."""
        raiz = self.raiz_com_edicao()
        self.muda_dados(raiz, "veiculos", self._lado_do_nyt)
        self.acusa(self.valida("--tudo", "--dia", DIA, raiz=raiz), "R03", caminho="%s.json" % DIA)

    def test_dia_nao_acusa_mudanca_de_lado_no_mapa_na_edicao_de_arquivo(self):
        """CONTRATO, seção 3: "`--tudo` só aplica as regras **(dia)** […] à edição cuja `data` é igual a
        `--dia`. […] no dia seguinte, não acusa mais"."""
        raiz = self.raiz_com_edicao()
        self.muda_dados(raiz, "veiculos", self._lado_do_nyt)
        self.nao_acusa(self.valida("--tudo", "--dia", AMANHA, raiz=raiz, agora=agora_de(AMANHA)), "R03")

    def test_dia_padrao_e_hoje_em_brasilia(self):
        """CONTRATO, seção 0, `--dia`: "No `publica.py contexto` e no `valida.py`, o padrão é sempre hoje
        em Brasília"; "Relógio de teste": `INFO_AGORA` vale "no padrão de `--dia`"."""
        raiz = self.raiz_com_edicao()
        self.muda_dados(raiz, "veiculos", self._lado_do_nyt)
        self.acusa(self.valida("--tudo", raiz=raiz, agora=agora_de(DIA)), "R03")
        self.nao_acusa(self.valida("--tudo", raiz=raiz, agora=agora_de(AMANHA)), "R03")

    def test_dia_padrao_usa_o_fuso_de_brasilia(self):
        """CONTRATO, seção 0, `--dia`: "hoje em Brasília (UTC−3 fixo)". Às 02:59:59 UTC ainda é o dia
        anterior em Brasília; às 03:00:00 UTC já é o dia."""
        raiz = self.raiz_com_edicao()
        self.muda_dados(raiz, "veiculos", self._lado_do_nyt)
        self.acusa(self.valida("--tudo", raiz=raiz, agora=AMANHA + "T02:59:59Z"), "R03")
        self.nao_acusa(self.valida("--tudo", raiz=raiz, agora=AMANHA + "T03:00:00Z"), "R03")

    def test_dia_veiculo_que_saiu_do_mapa(self):
        """ESQUEMA, seção 10, R02: "**(dia)** Veículo: em `veiculos.json`"; seção 16: "Veículo citado
        numa edição antiga que saiu do mapa depois: o site mostra o id" (a edição de arquivo não quebra)."""
        raiz = self.raiz_com_edicao()

        def tira(mapa):
            mapa["veiculos"] = [v for v in mapa["veiculos"] if v["id"] != "gazeta_do_povo"]

        self.muda_dados(raiz, "veiculos", tira)
        self.acusa(self.valida("--tudo", "--dia", DIA, raiz=raiz), "R02")
        self.nao_acusa(self.valida("--tudo", "--dia", AMANHA, raiz=raiz, agora=agora_de(AMANHA)), "R02")

    def test_dia_limiar_de_preco_que_mudou(self):
        """CONTRATO, seção 3: as regras **(dia)** são "as que cruzam a edição com `dados/veiculos.json`,
        com os limiares de preço e com o catálogo". Com o limiar do Brent subindo de 5% para 7%, o
        gatilho de preço da edição (6,1%) deixa de ser devido: R13c, só na edição do dia."""
        raiz = self.raiz_com_edicao()

        def sobe(regua):
            regua["niveis_alerta"][1]["criterios"]["energia"]["precos"][0]["alta_minima_pct"] = 7

        self.muda_dados(raiz, "regua", sobe)
        self.acusa(self.valida("--tudo", "--dia", DIA, raiz=raiz), "R13c")
        self.nao_acusa(self.valida("--tudo", "--dia", AMANHA, raiz=raiz, agora=agora_de(AMANHA)), "R13c")

    def test_dia_indicador_que_saiu_do_catalogo(self):
        """ESQUEMA, seção 10, R02: "**(dia)** Indicador: em `dados/indicadores.json`"."""
        raiz = self.raiz_com_edicao()

        def tira(catalogo):
            catalogo["indicadores"] = [i for i in catalogo["indicadores"] if i["id"] != "wti"]

        self.muda_dados(raiz, "indicadores", tira)
        self.acusa(self.valida("--tudo", "--dia", DIA, raiz=raiz), "R02")
        self.nao_acusa(self.valida("--tudo", "--dia", AMANHA, raiz=raiz, agora=agora_de(AMANHA)), "R02")

    def test_dia_voto_tipico_que_mudou(self):
        """ESQUEMA, seção 10, "Princípio das regras do dia"; R11: "**(dia)** Com tema atual, o voto típico
        de `para` nesse tema é `B` ou `R`"; R20: "**(dia)** `partido` é o de `voto_tipico` com mais posições
        iguais às conhecidas do `dna`". O dono revê o voto típico depois da edição: no dia ela é acusada;
        no dia seguinte, não."""
        raiz = self.raiz_com_edicao()

        def revisa(regua):
            votos = dict((p["id"], p) for p in regua["partidos"])
            votos["soberanistas"]["voto_tipico"] = "R R R R R Y R"   # clima: o destino do vetor da UE fica sem posição firme
            votos["centrao"]["voto_tipico"] = "W Y B B R Y R"        # o dna do player novo passa a dar centrao

        self.muda_dados(raiz, "regua", revisa)
        res = self.valida("--tudo", "--dia", DIA, raiz=raiz)
        self.acusa(res, "R11", caminho="principais[0].vetores[0].para")
        self.acusa(res, "R20", caminho="novos_players[0].partido")
        self.nao_acusa(self.valida("--tudo", "--dia", AMANHA, raiz=raiz, agora=agora_de(AMANHA)), "R11", "R20")

    def test_dia_lista_de_conflito_que_mudou(self):
        """ESQUEMA, seção 10, R19: "(b) **(dia)** algum `alvo` de ataque […] está em `regua.json`, lista
        `conflito.players`". O dono acrescenta um player à lista depois da edição: no dia ela é acusada; no
        dia seguinte, não."""
        edicao = monta_edicao(DIA, rica=True)
        jogadores = set(p["id"] for p in apoio.dados("players")["players"])
        alvo = next(a["alvo"] for i in apoio.itens(edicao) if not i.get("conflito_de_interesse")
                    for a in apoio.ataques_de(i) if a["alvo"] in jogadores)
        raiz = self.raiz_com_edicao(edicao)
        self.muda_dados(raiz, "regua", lambda regua: regua["conflito"]["players"].append(alvo))
        self.acusa(self.valida("--tudo", "--dia", DIA, raiz=raiz), "R19")
        self.nao_acusa(self.valida("--tudo", "--dia", AMANHA, raiz=raiz, agora=agora_de(AMANHA)), "R19")

    def test_arquivo_continua_sob_as_regras_que_nao_sao_do_dia(self):
        """CONTRATO, seção 3: "Nas outras, aplica as demais regras". O trecho da R10 que pede força 1 na
        narrativa não tem a marca **(dia)**: vale também para a edição de arquivo. "Em `--tudo`, o caminho
        começa com o nome do arquivo"."""
        edicao = monta_edicao(DIA, rica=True)
        edicao["principais"][0]["placar"][2]["forca"] = 2          # narrativa com força 2
        raiz = self.raiz_com_edicao(edicao)
        self.acusa(self.valida("--tudo", "--dia", AMANHA, raiz=raiz, agora=agora_de(AMANHA)), "R10",
                   caminho="%s.json" % DIA)


# =============================================================================================
# (b) Regras de crescimento: G1 a G4, com `--base`
# =============================================================================================

class Crescimento(apoio.Caso):
    """ESQUEMA, seção 10, "Regras de crescimento"; CONTRATO, seção 3, "Regras G"."""

    def raiz_git(self, edicoes=(), antes=None):
        """Raiz com repositório git. O commit de base fica também em `origin/main`."""
        raiz = self.nova_raiz(edicoes)
        if antes:
            antes(raiz)
        apoio.inicia_git(raiz)
        return raiz, apoio.commita(raiz, "base", origin=True)

    def tudo(self, raiz, base="origin/main", *mais, **kw):
        return self.valida("--tudo", "--base", base, *mais, raiz=raiz, **kw)

    def muda(self, raiz, arquivo, funcao):
        return apoio.muda_json(os.path.join(raiz, "dados", arquivo + ".json"), funcao)

    def _player_novo(self, origem="rotina"):
        novo = apoio.players_registrados(monta_edicao(DIA, rica=True))[0]
        novo["origem"] = origem
        return novo

    def _vetor(self, dia=ONTEM):
        return apoio.vetores_registrados(monta_edicao(dia, rica=True))[0]

    # --- sem mudança ---
    def test_g_aceita_repositorio_sem_mudanca(self):
        """CONTRATO, seção 3, "Regras G": "Conferem o que a rotina mudou". Sem mudança nenhuma, nenhuma
        regra G é acusada."""
        raiz, _ = self.raiz_git()
        self.nao_acusa(self.tudo(raiz), "G1", "G2", "G3", "G4")

    # --- G1 ---
    def test_g1_acusa_player_da_base_alterado(self):
        """ESQUEMA, seção 10, G1: "os players da base continuam iguais e na mesma ordem"."""
        raiz, _ = self.raiz_git()
        self.muda(raiz, "players", lambda arq: arq["players"][3].update(partido="soberanistas"))
        self.acusa(self.tudo(raiz), "G1")

    def test_g1_acusa_player_da_base_removido(self):
        """ESQUEMA, seção 10, G1: "os players da base continuam iguais"."""
        raiz, _ = self.raiz_git()
        self.muda(raiz, "players", lambda arq: arq["players"].pop(3))
        self.acusa(self.tudo(raiz), "G1")

    def test_g1_acusa_players_da_base_fora_de_ordem(self):
        """ESQUEMA, seção 10, G1: "e na mesma ordem"."""
        raiz, _ = self.raiz_git()
        self.muda(raiz, "players", lambda arq: arq["players"].reverse())
        self.acusa(self.tudo(raiz), "G1")

    def test_g1_acusa_player_novo_fora_do_fim(self):
        """ESQUEMA, seção 10, G1: "só entram novos no fim"."""
        raiz, _ = self.raiz_git()
        self.muda(raiz, "players", lambda arq: arq["players"].insert(0, self._player_novo()))
        self.acusa(self.tudo(raiz), "G1")

    def test_g1_acusa_player_novo_que_nao_e_da_rotina(self):
        """ESQUEMA, seção 10, G1: "só entram novos no fim, com `origem: "rotina"`"."""
        raiz, _ = self.raiz_git()
        self.muda(raiz, "players", lambda arq: arq["players"].append(self._player_novo("regua")))
        self.acusa(self.tudo(raiz), "G1")

    def test_g1_aceita_player_novo_no_fim_e_atualizado_em_diferente(self):
        """ESQUEMA, seção 10, G1: "só entram novos no fim, com `origem: "rotina"`. `atualizado_em` pode
        mudar"."""
        raiz, _ = self.raiz_git()

        def cresce(arq):
            arq["players"].append(self._player_novo())
            arq["atualizado_em"] = DIA

        self.muda(raiz, "players", cresce)
        self.nao_acusa(self.tudo(raiz), "G1", "G4")

    # --- G2 ---
    def _com_um_vetor(self, raiz):
        self.muda(raiz, "vetores", lambda arq: arq["vetores"].append(self._vetor()))

    def test_g2_acusa_vetor_da_base_apagado(self):
        """ESQUEMA, seção 10, G2: "Vetor não se apaga: anula-se, com uma entrada nova"."""
        raiz, _ = self.raiz_git(antes=self._com_um_vetor)
        self.muda(raiz, "vetores", lambda arq: arq["vetores"].clear())
        self.acusa(self.tudo(raiz), "G2")

    def test_g2_acusa_vetor_da_base_alterado(self):
        """ESQUEMA, seção 10, G2: "as entradas da base continuam iguais"."""
        raiz, _ = self.raiz_git(antes=self._com_um_vetor)
        self.muda(raiz, "vetores", lambda arq: arq["vetores"][0].update(forca=3))
        self.acusa(self.tudo(raiz), "G2")

    def test_g2_acusa_vetor_novo_antes_dos_da_base(self):
        """ESQUEMA, seção 10, G2: "só entram novas no fim"."""
        raiz, _ = self.raiz_git(antes=self._com_um_vetor)
        self.muda(raiz, "vetores", lambda arq: arq["vetores"].insert(0, self._vetor(DIA)))
        self.acusa(self.tudo(raiz), "G2")

    def test_g2_aceita_vetor_novo_e_anulacao_no_fim(self):
        """ESQUEMA, seção 10, G2: "só entram novas no fim. Vetor não se apaga: anula-se, com uma entrada
        nova (seção 12)"."""
        raiz, _ = self.raiz_git(antes=self._com_um_vetor)

        def cresce(arq):
            arq["vetores"].append(self._vetor(DIA))
            arq["vetores"].append({"id": "%s_anula_1" % DIA, "data": DIA, "anula": arq["vetores"][0]["id"],
                                   "porque": F + "A fonte de hoje desmente o ato.",
                                   "url": "https://ec.europa.eu/exemplo/tarifa-segue"})

        self.muda(raiz, "vetores", cresce)
        self.nao_acusa(self.tudo(raiz), "G2", "G4")

    # --- G3 ---
    def _duas_edicoes(self):
        e1 = monta_edicao(ANTEONTEM)
        e2 = monta_edicao(ONTEM, anterior=e1)
        return e1, e2

    def test_g3_acusa_edicao_da_base_alterada(self):
        """ESQUEMA, seção 10, G3: "Edição que existe na base (os arquivos `AAAA-MM-DD.json` e
        `AAAA-MM-DD.md`) não muda nem some"."""
        e1, e2 = self._duas_edicoes()
        raiz, _ = self.raiz_git([e1, e2])
        e1["bastidores"]["minutos"] = 31
        apoio.grava_json(apoio.caminho_da_edicao(raiz, ANTEONTEM), e1)
        self.acusa(self.tudo(raiz), "G3")

    def test_g3_acusa_texto_da_edicao_da_base_alterado(self):
        """ESQUEMA, seção 10, G3: o `.md` da edição que existe na base também "não muda nem some"."""
        raiz, _ = self.raiz_git(self._duas_edicoes())
        apoio.grava_texto(apoio.caminho_da_edicao(raiz, ANTEONTEM, "md"), "# INFOCENARIUM\n\nTexto trocado.\n")
        self.acusa(self.tudo(raiz), "G3")

    def test_g3_acusa_edicao_da_base_apagada(self):
        """ESQUEMA, seção 10, G3: "não muda nem some"."""
        e1, e2 = self._duas_edicoes()
        raiz, _ = self.raiz_git([e1, e2])
        os.remove(apoio.caminho_da_edicao(raiz, ANTEONTEM))
        os.remove(apoio.caminho_da_edicao(raiz, ANTEONTEM, "md"))
        apoio.grava_edicoes(raiz, [e2])                             # índice e feed sem a edição apagada
        self.acusa(self.tudo(raiz), "G3")

    def test_g3_acusa_edicao_reduzida_da_base_trocada(self):
        """ESQUEMA, seção 10, G3: a exceção é só para "a de `estado: falha`"; edição `reduzida` que está
        na base não é trocada."""
        e1, e2 = self._duas_edicoes()
        e2["estado"] = "reduzida"
        raiz, _ = self.raiz_git([e1, e2])
        nova = monta_edicao(ONTEM, anterior=e1)
        nova["resumo"] = "Edição fictícia refeita depois de publicada."
        apoio.grava_edicoes(raiz, [e1, nova])
        self.acusa(self.tudo(raiz, "origin/main", "--dia", ONTEM), "G3")

    def test_g3_aceita_falha_da_base_trocada_por_edicao_de_verdade(self):
        """ESQUEMA, seção 10, G3: "Exceção: a de `estado: falha` pode ser trocada por qualquer edição do
        mesmo dia […]. O `indice.json` muda sempre"."""
        e1, _ = self._duas_edicoes()
        falha = apoio.edicao_falha(ONTEM, "Nada funcionou neste dia fictício.", anterior=e1)
        raiz, _ = self.raiz_git([e1, falha])
        apoio.grava_edicoes(raiz, [e1, monta_edicao(ONTEM, anterior=e1)])
        self.nao_acusa(self.tudo(raiz, "origin/main", "--dia", ONTEM, agora=agora_de(ONTEM)), "G3", "G4")

    def test_g3_aceita_falha_da_base_trocada_por_outra_falha(self):
        """ESQUEMA, seção 10, G3: a de `estado: falha` "pode ser trocada por qualquer edição do mesmo dia,
        inclusive outra falha" (o `publica.py falha` que roda de novo regrava a falha do dia)."""
        e1, _ = self._duas_edicoes()
        falha = apoio.edicao_falha(ONTEM, "Nada funcionou neste dia fictício.", anterior=e1)
        raiz, _ = self.raiz_git([e1, falha])
        outra = apoio.edicao_falha(ONTEM, "Nada funcionou de novo neste dia fictício.", anterior=e1)
        apoio.grava_edicoes(raiz, [e1, outra])
        self.nao_acusa(self.tudo(raiz, "origin/main", "--dia", ONTEM, agora=agora_de(ONTEM)), "G3", "G4")

    def test_g3_acusa_falha_da_base_apagada(self):
        """ESQUEMA, seção 10, G3: a falha "não pode sumir"."""
        e1, _ = self._duas_edicoes()
        falha = apoio.edicao_falha(ONTEM, "Nada funcionou neste dia fictício.", anterior=e1)
        raiz, _ = self.raiz_git([e1, falha])
        os.remove(apoio.caminho_da_edicao(raiz, ONTEM))
        os.remove(apoio.caminho_da_edicao(raiz, ONTEM, "md"))
        apoio.grava_edicoes(raiz, [e1])
        self.acusa(self.tudo(raiz, "origin/main", "--dia", ONTEM, agora=agora_de(ONTEM)), "G3",
                   caminho="edicoes/%s.json" % ONTEM)

    def test_g3_aceita_edicao_nova_com_indice_e_feed_refeitos(self):
        """ESQUEMA, seção 10, G3: "O `indice.json` muda sempre"; G4: mudam `edicoes/` (arquivos `.json` e
        `.md`) e `feed.xml`."""
        e1, e2 = self._duas_edicoes()
        raiz, _ = self.raiz_git([e1, e2])
        apoio.grava_edicoes(raiz, [e1, e2, monta_edicao(DIA, anterior=e2)])
        self.nao_acusa(self.tudo(raiz, "origin/main", "--dia", DIA), "G3", "G4")

    # --- G4 ---
    def test_g4_acusa_mudanca_nos_arquivos_do_dono(self):
        """ESQUEMA, seção 10, G4: "A rotina nunca muda `dados/veiculos.json`, `dados/regua.json` nem
        `dados/indicadores.json`". As mudanças plantadas deixam os dados válidos: o defeito é só o caminho."""
        mudancas = {
            "veiculos": lambda arq: arq.update(revisado_em="2026-11-22"),
            "regua": lambda arq: arq.update(aviso=arq["aviso"] + " Revisto."),
            "indicadores": lambda arq: arq.update(atualizado_em="2026-11-24"),
        }
        for arquivo, muda in mudancas.items():
            with self.subTest(arquivo=arquivo):
                raiz, _ = self.raiz_git()
                self.muda(raiz, arquivo, muda)
                self.acusa(self.tudo(raiz), "G4")

    def test_g4_acusa_arquivo_novo_fora_dos_caminhos_permitidos(self):
        """ESQUEMA, seção 10, G4: "Só mudam os caminhos permitidos: em `edicoes/`, só `AAAA-MM-DD.json` e
        `AAAA-MM-DD.md` […] e `indice.json`, sem subpasta; `feed.xml`; `dados/players.json` e
        `dados/vetores.json`"; CONTRATO, seção 3: entram "os arquivos novos de `git status --porcelain
        --untracked-files=all`"."""
        novos = {
            "arquivo solto na raiz": "anotacoes.txt",
            "arquivo que não é .json nem .md em edicoes": "edicoes/rascunho.txt",
            "arquivo novo em dados": "dados/notas.json",
            "pasta de bytecode": "ferramentas/__pycache__/valida.cpython-312.pyc",
        }
        for nome, caminho in novos.items():
            with self.subTest(novo=nome):
                raiz, _ = self.raiz_git()
                apoio.grava_texto(os.path.join(raiz, caminho), "{}\n")
                self.acusa(self.tudo(raiz), "G4")

    def test_g4_acusa_arquivo_de_nome_estranho_em_edicoes(self):
        """ESQUEMA, seção 10, G4: "em `edicoes/`, só `AAAA-MM-DD.json` e `AAAA-MM-DD.md` (com data que existe
        no calendário) e `indice.json`, sem subpasta"."""
        for caminho in ("edicoes/notas.json", "edicoes/copia.md", "edicoes/2026-02-30.json",
                        "edicoes/antigas/%s.json" % DIA):
            with self.subTest(novo=caminho):
                raiz, _ = self.raiz_git()
                apoio.grava_texto(os.path.join(raiz, caminho), "{}\n")
                self.acusa(self.tudo(raiz), "G4", caminho=caminho)

    def test_g4_acusa_mudanca_ja_commitada(self):
        """CONTRATO, seção 3, "Regras G": "Conferem o que a rotina mudou, antes ou depois do commit.
        Comparam os arquivos do repositório, como estão no disco, com `REF`"."""
        raiz, base = self.raiz_git()
        self.muda(raiz, "veiculos", lambda arq: arq.update(revisado_em="2026-11-22"))
        apoio.commita(raiz, "mudança no mapa")
        self.acusa(self.tudo(raiz, base), "G4")

    def test_g4_aceita_base_pelo_nome_e_pelo_identificador(self):
        """CONTRATO, seção 3, "Regras G": "`REF` é qualquer revisão do git: um nome, como `origin/main`,
        ou o identificador de um commit". Os dois dão o mesmo resultado."""
        raiz, base = self.raiz_git()
        self.muda(raiz, "veiculos", lambda arq: arq.update(revisado_em="2026-11-22"))
        pelo_nome = self.tudo(raiz, "origin/main")
        pelo_id = self.tudo(raiz, base)
        self.acusa(pelo_nome, "G4")
        self.acusa(pelo_id, "G4")
        self.assertEqual(pelo_nome.saida, pelo_id.saida)

    def test_g4_nao_conta_arquivo_ignorado(self):
        """CONTRATO, seção 3, "Regras G": "Arquivo ignorado pelo `.gitignore` não conta"; seção 0: a pasta
        de trabalho pode ficar "dentro do repositório, listada no `.gitignore`"."""
        raiz, _ = self.raiz_git(antes=lambda r: apoio.grava_texto(os.path.join(r, ".gitignore"), ".info-tmp/\n"))
        apoio.grava_texto(os.path.join(raiz, ".info-tmp", "rascunho.json"), "{}\n")
        self.nao_acusa(self.tudo(raiz), "G4")

    def test_g4_sem_base_mudanca_do_dono_nao_e_erro(self):
        """CONTRATO, seção 3, "Regras G": "Sem `--base`, mudança do dono em `dados/` ou em `ferramentas/`
        não é erro: é assim que o `valida.yml` chama"."""
        raiz, _ = self.raiz_git()
        self.muda(raiz, "veiculos", lambda arq: arq.update(revisado_em="2026-11-22"))
        apoio.grava_texto(os.path.join(raiz, "ferramentas", "nota.txt"), "arquivo novo do dono\n")
        self.nao_acusa(self.valida("--tudo", raiz=raiz), "G4")

    # --- git que não responde ---
    def test_base_sem_git_no_caminho_da_codigo_1(self):
        """CONTRATO, seção 3, "Situação, última linha e código": "`--base` […] com o git falhando (`ERRO
        GIT`)", código 1. O teste roda a ferramenta com a variável PATH apontando para uma pasta vazia: não
        há programa `git`."""
        raiz, _ = self.raiz_git()
        res = self.tudo(raiz, "origin/main", ambiente={"PATH": self.pasta("vazia")})
        self.falhou(res)

    def test_base_em_raiz_que_nao_e_repositorio_da_codigo_1(self):
        """CONTRATO, seção 3, "Situação, última linha e código": "`--base` numa raiz sem git, com revisão
        que não existe, ou com o git falhando (`ERRO GIT`)", última linha `FALHA N erros, M avisos`,
        código 1."""
        self.acusa(self.tudo(self.nova_raiz()), "GIT")


# =============================================================================================
# (d) Os modos e a saída
# =============================================================================================

class ModosESaida(CasoDeValida):
    """CONTRATO, seção 0 (regras comuns) e seção 3 (modos, formato da saída e códigos)."""

    def _defeituosa(self):
        e = apoio.exemplo()
        R(e, 3)["confianca"] = "alta"                      # R08
        return e

    # --- sem opção vale --tudo ---
    def test_sem_opcao_vale_tudo(self):
        """CONTRATO, seção 3: "**Sem opção nenhuma, vale `--tudo`.** É assim que o workflow `valida.yml`
        chama o validador". A mesma raiz dá a mesma saída e o mesmo código nas duas chamadas."""
        edicao = monta_edicao(DIA, rica=True)
        edicao["principais"][0]["placar"][2]["forca"] = 2          # R10: só o modo --tudo abre as edições
        raiz = self.nova_raiz([edicao])
        sem_opcao = self.valida(raiz=raiz)
        com_tudo = self.valida("--tudo", raiz=raiz)
        self.acusa(sem_opcao, "R10")
        self.assertEqual((sem_opcao.codigo, sem_opcao.saida), (com_tudo.codigo, com_tudo.saida))

    def test_sem_opcao_em_raiz_boa_passa(self):
        """CONTRATO, seção 3: "Sem opção nenhuma, vale `--tudo`"; seção 5: o `valida.yml` roda
        "`python3 ferramentas/valida.py` a cada push na `main`"."""
        self.passou(self.valida(raiz=self.nova_raiz([monta_edicao(DIA, rica=True)])))

    # --- repositório sem edição ---
    def test_tudo_em_repositorio_sem_pasta_de_edicoes(self):
        """CONTRATO, seção 3, modo `--tudo`: lê "todos os `edicoes/*.json`" (aqui, nenhum) e, de
        `--dados`, "`edicoes/indice.json` se existir". No primeiro dia o repositório não tem edição: o
        validador passa."""
        self.passou(self.valida("--tudo", raiz=self.nova_raiz()))

    def test_tudo_em_repositorio_com_pasta_de_edicoes_vazia(self):
        """CONTRATO, seção 3, modo `--tudo`, num repositório sem edição nenhuma (a pasta existe, vazia)."""
        raiz = self.nova_raiz()
        os.makedirs(os.path.join(raiz, "edicoes"))
        self.passou(self.valida("--tudo", raiz=raiz))

    def test_tudo_sem_edicao_com_base(self):
        """CONTRATO, seção 5: "sem edição mexida, uma chamada sem `--dia`": `valida.py --tudo --base
        ANTES` num repositório sem edição nenhuma."""
        raiz = self.nova_raiz(com_git=True)
        self.passou(self.valida("--tudo", "--base", "origin/main", raiz=raiz))

    # --- o que --tudo confere além das edições ---
    def test_tudo_acusa_indice_diferente_dos_arquivos(self):
        """CONTRATO, seção 3, modo `--tudo`: "índice igual aos arquivos"; tabela dos códigos: `INDICE`,
        "`edicoes/indice.json` […] diferente do que os arquivos dão"."""
        casos = {
            "nível trocado": lambda i: i["edicoes"][0].update(nivel=5),
            "edição que falta": lambda i: i["edicoes"].clear(),
            "resumo trocado": lambda i: i["edicoes"][0].update(resumo="Outro resumo."),
        }
        for nome, muda in casos.items():
            with self.subTest(defeito=nome):
                raiz = self.nova_raiz([monta_edicao(DIA, rica=True)])
                apoio.muda_json(os.path.join(raiz, "edicoes", "indice.json"), muda)
                self.acusa(self.valida("--tudo", raiz=raiz), "INDICE", caminho="edicoes/indice.json")

    def test_tudo_acusa_edicao_sem_md(self):
        """CONTRATO, seção 3, modo `--tudo`: "cada edição com seu `.md`"; tabela dos códigos: `MD`, "edição
        sem o `.md`"."""
        raiz = self.nova_raiz([monta_edicao(DIA, rica=True)])
        os.remove(apoio.caminho_da_edicao(raiz, DIA, "md"))
        self.acusa(self.valida("--tudo", raiz=raiz), "MD", caminho="edicoes/%s.md" % DIA)

    def test_tudo_acusa_feed_mal_formado(self):
        """CONTRATO, seção 3, modo `--tudo`: "`feed.xml` bem formado"; tabela dos códigos: `FEED`."""
        raiz = self.nova_raiz([monta_edicao(DIA, rica=True)])
        apoio.grava_texto(os.path.join(raiz, "feed.xml"), '<?xml version="1.0"?>\n<feed><entry></feed>\n')
        self.acusa(self.valida("--tudo", raiz=raiz), "FEED", caminho="feed.xml")

    def test_tudo_acusa_link_do_feed_com_esquema_escondido(self):
        """CONTRATO, seção 3, código `FEED`: "`link` que não é `http`, `https` nem relativo: o esquema é lido como
        o leitor de feed lê, depois de tirar espaço e caractere de controle (`java&#9;script:` é `javascript:`)"."""
        for href in ("java&#9;script:alert(1)", "java&#10;script:alert(1)", " javascript:alert(1)"):
            with self.subTest(href=href):
                raiz = self.nova_raiz([monta_edicao(DIA, rica=True)])
                apoio.grava_texto(os.path.join(raiz, "feed.xml"), '<?xml version="1.0"?>\n<feed xmlns="http://www.w3.org/2005/'
                                  'Atom"><entry><link href="%s"/></entry></feed>\n' % href)
                self.acusa(self.valida("--tudo", raiz=raiz), "FEED", caminho="feed.xml")

    def test_tudo_sem_feed_so_avisa(self):
        """CONTRATO, seção 3, modo `--tudo`: "Com edições, sem `indice.json` é erro; sem `feed.xml`, só
        aviso"."""
        raiz = self.nova_raiz([monta_edicao(DIA, rica=True)])
        os.remove(os.path.join(raiz, "feed.xml"))
        res = self.valida("--tudo", raiz=raiz)
        self.avisa(res, "FEED", caminho="feed.xml")
        self.passou(res)

    def test_tudo_sem_indice_e_erro(self):
        """CONTRATO, seção 3, modo `--tudo`: "Com edições, sem `indice.json` é erro"."""
        raiz = self.nova_raiz([monta_edicao(DIA, rica=True)])
        os.remove(os.path.join(raiz, "edicoes", "indice.json"))
        self.acusa(self.valida("--tudo", raiz=raiz), "INDICE", caminho="edicoes/indice.json")

    def test_tudo_acusa_md_sem_edicao(self):
        """CONTRATO, seção 3, modo `--tudo`: "`.md` com nome de data e sem a edição é erro"."""
        raiz = self.nova_raiz([monta_edicao(DIA, rica=True)])
        apoio.grava_texto(apoio.caminho_da_edicao(raiz, ONTEM, "md"), "# INFOCENARIUM\n\nTexto solto.\n")
        self.acusa(self.valida("--tudo", raiz=raiz), "MD", caminho="edicoes/%s.md" % ONTEM)

    def test_tudo_avisa_arquivo_de_nome_estranho_em_edicoes(self):
        """CONTRATO, seção 3, modo `--tudo`: "Arquivo `.json` ou `.md` de nome estranho em `edicoes/` (nem
        data, nem `indice.json`) só avisa (`ARQUIVO`)"."""
        raiz = self.nova_raiz([monta_edicao(DIA, rica=True)])
        apoio.grava_texto(os.path.join(raiz, "edicoes", "notas.json"), "{}\n")
        res = self.valida("--tudo", raiz=raiz)
        self.avisa(res, "ARQUIVO", caminho="edicoes/notas.json")
        self.passou(res)

    def test_tudo_caminho_e_arquivo_dois_pontos_campo(self):
        """CONTRATO, seção 3: "o caminho começa com o nome do arquivo, ligado ao campo por dois-pontos, sem
        espaço: `edicoes/2026-11-20.json:radar[2].confianca`"."""
        edicao = monta_edicao(DIA, rica=True)
        edicao["principais"][0]["placar"][2]["forca"] = 2          # narrativa com força 2 (R10, vale sempre)
        raiz = self.nova_raiz([edicao])
        res = self.valida("--tudo", raiz=raiz)
        linhas = res.linhas_da_regra("R10")
        self.assertTrue(any(l.startswith("ERRO R10 edicoes/%s.json:principais[0].placar[2]." % DIA) for l in linhas),
                        res.relato())

    # --- formato da saída ---
    def test_saida_uma_linha_por_problema_e_contagem_na_ultima(self):
        """CONTRATO, seção 3: "A última linha é sempre `OK 0 erros, N avisos` ou `FALHA N erros, M avisos`,
        com N e M iguais às linhas `ERRO` e `AVISO` impressas, e o singular só com 1"."""
        res = self.solta(self._defeituosa())
        self.falhou(res)
        m = re.match(r"^FALHA (\d+) (erros?), (\d+) (avisos?)$", res.ultima)
        self.assertTrue(m, "última linha fora do formato 'FALHA N erros, M avisos'." + res.relato())
        self.assertEqual((int(m.group(1)), int(m.group(3))), (len(res.erros), len(res.avisos)), res.relato())
        self.assertEqual(m.group(2), "erro" if int(m.group(1)) == 1 else "erros", res.relato())
        self.assertEqual(m.group(4), "aviso" if int(m.group(3)) == 1 else "avisos", res.relato())

    def test_saida_json(self):
        """CONTRATO, seção 3: "Com `--json`: a forma comum da seção 0 (`ok`, `codigo`, `veredito`, `linhas`)
        mais duas listas", `"erros": [{"regra": "R08", "caminho": "…", "mensagem": "…"}], "avisos": [ … ]`;
        seção 0: `--json` "imprime um objeto JSON no lugar do texto". O código de saída não muda."""
        res = self.solta(self._defeituosa(), None, "--json")
        self.assertEqual(res.codigo, 1, res.relato())
        objeto = self.objeto_json(res)
        self.assertIs(objeto["ok"], False)
        self.assertIsInstance(objeto["avisos"], list)
        do_r08 = [x for x in objeto["erros"] if x["regra"] == "R08"]
        self.assertTrue(do_r08, res.relato())
        self.assertEqual(sorted(do_r08[0]), ["caminho", "mensagem", "regra"])
        self.assertIn("radar[3].confianca", do_r08[0]["caminho"])

    def test_saida_json_tem_a_forma_comum(self):
        """CONTRATO, seção 3: "Com `--json`: a forma comum da seção 0 (`ok`, `codigo`, `veredito`,
        `linhas`) mais duas listas"; `linhas` são as linhas de texto, sem o veredito."""
        res = self.solta(self._defeituosa(), None, "--json")
        objeto = self.objeto_json(res)
        self.assertEqual(set(objeto), {"ok", "codigo", "veredito", "linhas", "erros", "avisos"}, res.relato())
        self.assertEqual(objeto["codigo"], res.codigo)
        self.assertRegex(objeto["veredito"], r"^FALHA %d erros?, %d avisos?$" % (len(objeto["erros"]),
                                                                              len(objeto["avisos"])))
        refeitas = (["ERRO %(regra)s %(caminho)s: %(mensagem)s" % x for x in objeto["erros"]]
                    + ["AVISO %(regra)s %(caminho)s: %(mensagem)s" % x for x in objeto["avisos"]])
        self.assertEqual(objeto["linhas"], refeitas)

    def test_saida_json_sem_erro(self):
        """CONTRATO, seção 3, `--json`: sem erro, `ok` é `true`, `erros` é vazia e o código é 0."""
        res = self.valida("--edicao", apoio.EXEMPLO, "--json", raiz=self.nova_raiz())
        self.assertEqual(res.codigo, 0, res.relato())
        objeto = self.objeto_json(res)
        self.assertIs(objeto["ok"], True)
        self.assertEqual(objeto["erros"], [])
        self.assertIsInstance(objeto["avisos"], list)

    def test_saida_json_traz_os_avisos(self):
        """CONTRATO, seção 3, `--json`: a chave `avisos` traz os avisos (aqui, o C5 do trigo com uma fonte
        só), e aviso não muda o código."""
        raiz = self.nova_raiz()
        apoio.muda_json(os.path.join(raiz, "dados", "indicadores.json"), so_uma_fonte_no_trigo)
        res = self.valida("--dados", "--json", raiz=raiz)
        self.assertEqual(res.codigo, 0, res.relato())
        objeto = self.objeto_json(res)
        self.assertIs(objeto["ok"], True)
        self.assertIn("C5", [aviso["regra"] for aviso in objeto["avisos"]])

    # --- erro de uso ---
    def test_uso_opcao_desconhecida(self):
        """CONTRATO, seção 0, "Erro de uso": "Opção errada, valor ilegível ou falta de opção obrigatória:
        uma linha `FALHA uso: …` na saída padrão e código 2. Nada é gravado"."""
        raiz = self.nova_raiz([monta_edicao(DIA)])
        antes = apoio.fotografa(raiz, rigor=True)
        self.erro_de_uso(self.valida("--nao-existe", raiz=raiz))
        self.nada_mudou(antes, apoio.fotografa(raiz, rigor=True), "a raiz")

    def test_uso_edicao_sem_arquivo(self):
        """CONTRATO, seção 0, "Erro de uso": "falta de opção obrigatória" (`--edicao` pede o arquivo)."""
        self.erro_de_uso(self.valida("--edicao", raiz=self.nova_raiz()))

    def test_uso_dia_ilegivel(self):
        """CONTRATO, seção 0, "Erro de uso": "valor ilegível" (`--dia` é `AAAA-MM-DD`)."""
        self.erro_de_uso(self.valida("--tudo", "--dia", "20/11/2026", raiz=self.nova_raiz()))

    def test_uso_info_agora_ilegivel(self):
        """CONTRATO, seção 0, "Relógio de teste": "Com valor ilegível, a ferramenta para com
        `FALHA uso: INFO_AGORA ilegível` e código 2"."""
        res = self.valida("--tudo", raiz=self.nova_raiz(), agora="ontem à tarde")
        self.erro_de_uso(res)
        self.assertTrue(any(l.startswith("FALHA uso:") and "INFO_AGORA" in l for l in res.linhas), res.relato())

    def test_uso_dois_modos_na_mesma_chamada(self):
        """CONTRATO, seção 3, "Situação, última linha e código": "dois modos juntos (`--tudo`, `--dados`,
        `--edicao`)", `FALHA uso: …`, código 2."""
        self.erro_de_uso(self.valida("--dados", "--edicao", apoio.EXEMPLO, raiz=self.nova_raiz()))

    def test_uso_opcao_trabalho(self):
        """CONTRATO, seção 3, "Situação, última linha e código": "`--trabalho`, ou outra opção que não
        existe", `FALHA uso: …`, código 2 (seção 0: "O `valida.py` não tem esta opção")."""
        self.erro_de_uso(self.valida("--dados", "--trabalho", self.pasta("trabalho"), raiz=self.nova_raiz()))

    # --- arquivo ilegível ---
    def test_edicao_que_nao_existe_da_codigo_1(self):
        """CONTRATO, seção 3, "Situação, última linha e código": "arquivo que não existe ou ilegível (`ERRO
        ARQUIVO`)", código 1; seção 0: a última linha começa com `FALHA`."""
        self.falhou(self.valida("--edicao", os.path.join(self.pasta("solta"), "nao-existe.json"), raiz=self.nova_raiz()))

    def test_edicao_que_nao_e_json_da_codigo_1(self):
        """CONTRATO, seção 3, "Situação, última linha e código": "arquivo que não existe ou ilegível",
        código 1."""
        caminho = os.path.join(self.pasta("solta"), "quebrada.json")
        apoio.grava_texto(caminho, '{"versao": 1, "data": ')
        self.falhou(self.valida("--edicao", caminho, raiz=self.nova_raiz()))

    # --- nunca grava ---
    def test_nunca_grava_em_nenhum_modo(self):
        """CONTRATO, seção 3: "Nunca grava arquivo"; seção 0: "`valida.py` nunca grava nada"; seção 6:
        "Grava no repositório: nada". O retrato da raiz (conteúdo, hora de modificação e número de cada
        arquivo) é o mesmo antes e depois de cada modo, com e sem erro."""
        e1 = monta_edicao(ONTEM)
        com_erro = monta_edicao(DIA, anterior=e1, rica=True)
        com_erro["principais"][0]["placar"][2]["forca"] = 2
        raiz = self.nova_raiz([e1, com_erro], com_git=True)
        solta = self.arquivo_solto(self._defeituosa())
        chamadas = [(), ("--tudo",), ("--tudo", "--dia", DIA), ("--tudo", "--base", "origin/main"), ("--dados",),
                    ("--dados", "--json"), ("--edicao", apoio.caminho_da_edicao(raiz, DIA)), ("--edicao", solta),
                    ("--edicao", solta, "--anterior", apoio.caminho_da_edicao(raiz, ONTEM))]
        for argumentos in chamadas:
            with self.subTest(chamada=" ".join(argumentos) or "(sem opção)"):
                antes = apoio.fotografa(raiz, rigor=True)
                antes_solta = apoio.fotografa(os.path.dirname(solta), rigor=True)
                res = self.valida(*argumentos, raiz=raiz)
                self.assertIn(res.codigo, (0, 1), res.relato())
                self.nada_mudou(antes, apoio.fotografa(raiz, rigor=True), "a raiz")
                self.nada_mudou(antes_solta, apoio.fotografa(os.path.dirname(solta), rigor=True), "a pasta da edição")

    # --- a chamada do workflow do GitHub ---
    def _repositorio_do_workflow(self, edicao_do_robo):
        """Monta o que o workflow `publica-edicao.yml` tem na hora de validar: o repositório com
        `ferramentas/`, o commit da `main` de antes (ANTES) e, em HEAD, o commit do robô com a edição."""
        e1 = monta_edicao(ONTEM)
        raiz = self.nova_raiz([e1])
        apoio.copia_ferramentas(raiz)
        apoio.inicia_git(raiz)
        antes = apoio.commita(raiz, "main de antes")
        if edicao_do_robo:
            hoje = edicao_do_robo(e1)
            apoio.grava_edicoes(raiz, [e1, hoje])
            apoio.registra(raiz, hoje)
            apoio.commita(raiz, "edição %s" % DIA)
        return raiz, antes

    def test_chamada_do_workflow_aceita_edicao_boa(self):
        """CONTRATO, seção 5, "O GitHub Action": "`python3 ferramentas/valida.py --tudo --base ANTES --dia
        DIA` […]. Nessa hora a pasta está limpa, com o commit do robô em `HEAD`, sem pasta de trabalho
        […]. Só empurra com código 0". A ferramenta é chamada de dentro do repositório, sem `--raiz`
        (vale o padrão da seção 0: "a pasta acima de `ferramentas/`"), sem `INFO_AGORA` e com
        PYTHONDONTWRITEBYTECODE=1. Depois da chamada, a pasta continua limpa para o git."""
        raiz, antes = self._repositorio_do_workflow(lambda e1: monta_edicao(DIA, anterior=e1, rica=True))
        self.assertEqual(apoio.git(raiz, "status", "--porcelain", "--untracked-files=all"), "")
        res = apoio.roda("valida", ["--tudo", "--base", antes, "--dia", DIA], raiz=raiz, na_raiz=True)
        self.passou(res)
        self.assertEqual(apoio.git(raiz, "status", "--porcelain", "--untracked-files=all"), "",
                         "a chamada deixou arquivo a mais ou mudou arquivo do repositório." + res.relato())

    def test_chamada_do_workflow_recusa_edicao_com_erro(self):
        """CONTRATO, seção 5, "O GitHub Action": "código 1, 2 ou tempo esgotado recusam a edição". A edição
        do robô tem um erro da regra R10: o validador sai com código 1."""
        def com_erro(e1):
            hoje = monta_edicao(DIA, anterior=e1, rica=True)
            hoje["principais"][0]["placar"][2]["forca"] = 2
            return hoje

        raiz, antes = self._repositorio_do_workflow(com_erro)
        self.acusa(apoio.roda("valida", ["--tudo", "--base", antes, "--dia", DIA], raiz=raiz, na_raiz=True), "R10")

    def test_chamada_do_workflow_recusa_commit_que_mexe_no_mapa(self):
        """CONTRATO, seção 5: o workflow roda o validador com `--base ANTES`; ESQUEMA, seção 10, G4: "A
        rotina nunca muda `dados/veiculos.json`". O commit em HEAD traz a edição boa e uma mudança no
        mapa: G4, com o commit já feito."""
        raiz, antes = self._repositorio_do_workflow(lambda e1: monta_edicao(DIA, anterior=e1, rica=True))
        apoio.muda_json(os.path.join(raiz, "dados", "veiculos.json"), lambda m: m.update(revisado_em="2026-11-22"))
        apoio.commita(raiz, "mudança no mapa")
        self.acusa(apoio.roda("valida", ["--tudo", "--base", antes, "--dia", DIA], raiz=raiz, na_raiz=True), "G4")

    def test_chamada_do_valida_yml(self):
        """CONTRATO, seção 5: "O `valida.yml` roda `python3 ferramentas/valida.py` a cada push na `main`"
        (sem opção nenhuma, de dentro do repositório)."""
        raiz, _ = self._repositorio_do_workflow(lambda e1: monta_edicao(DIA, anterior=e1, rica=True))
        self.passou(apoio.roda("valida", [], raiz=raiz, na_raiz=True))


class ArquivosDeAgente(apoio.Caso):
    """ESQUEMA, seção 10, "Arquivo que dá ordem a agente"; CONTRATO, seção 3, código `AGENTE`."""

    def raiz_git(self, *arquivos):
        """Raiz com git; cada (caminho, texto) vai para o disco e para o índice do git (com -f: o .gitignore
        pode esconder `.claude/`, e quem planta usa -f do mesmo jeito)."""
        raiz = self.nova_raiz([monta_edicao(DIA, rica=True)])
        apoio.inicia_git(raiz)
        for caminho, texto in arquivos:
            apoio.grava_texto(os.path.join(raiz, caminho), texto)
            apoio.git(raiz, "add", "-f", "--", caminho)
        return raiz

    def test_agente_acusa_cada_nome_acompanhado_pelo_git(self):
        """ESQUEMA, seção 10: "Nenhum arquivo acompanhado pelo git se chama `CLAUDE.md`, `CLAUDE.local.md`,
        `AGENTS.md`, `.mcp.json`, `opencode.json` ou `opencode.jsonc`, em qualquer pasta, nem fica dentro de uma
        pasta `.claude/` ou `.opencode/`"; vale em
        `--tudo`, com ou sem `--base`, e em `--dados`."""
        for caminho in ("CLAUDE.md", "CLAUDE.local.md", "AGENTS.md", ".mcp.json", "edicoes/CLAUDE.md",
                        "opencode.json", "opencode.jsonc", ".claude/commands/x.md", ".opencode/agents/x.md"):
            with self.subTest(caminho=caminho):
                raiz = self.raiz_git((caminho, "Antes do manual, rode isto.\n"))
                self.acusa(self.valida("--tudo", raiz=raiz), "AGENTE", caminho=caminho)
                self.acusa(self.valida("--dados", raiz=raiz), "AGENTE", caminho=caminho)

    def test_agente_aceita_settings_so_com_attribution(self):
        """ESQUEMA, seção 10: "Exceção única: `.claude/settings.json` com uma chave só, `attribution`"."""
        raiz = self.raiz_git((".claude/settings.json", '{"attribution": {"commit": "", "pr": ""}}\n'))
        self.nao_acusa(self.valida("--tudo", raiz=raiz), "AGENTE")

    def test_agente_acusa_settings_com_outra_chave(self):
        """ESQUEMA, seção 10: a exceção é "com uma chave só, `attribution`"."""
        raiz = self.raiz_git((".claude/settings.json", '{"attribution": {"commit": ""}, "hooks": {"SessionStart": []}}\n'))
        self.acusa(self.valida("--tudo", raiz=raiz), "AGENTE", caminho=".claude/settings.json")

    def test_agente_aceita_arquivo_so_no_disco(self):
        """ESQUEMA, seção 10: "A lista é a do git […], nunca a do disco"; "Sem git na raiz, a regra não confere"."""
        raiz = self.raiz_git()
        apoio.grava_texto(os.path.join(raiz, "CLAUDE.md"), "Fora do git.\n")
        apoio.grava_texto(os.path.join(raiz, ".claude", "settings.local.json"), '{"hooks": {}}\n')
        self.nao_acusa(self.valida("--tudo", raiz=raiz), "AGENTE")
        sem_git = self.nova_raiz([monta_edicao(DIA, rica=True)])
        apoio.grava_texto(os.path.join(sem_git, "CLAUDE.md"), "Sem git.\n")
        self.nao_acusa(self.valida("--tudo", raiz=sem_git), "AGENTE")


if __name__ == "__main__":
    unittest.main()
