#!/usr/bin/env python3
"""Testes de contrato do publica.py: contexto, edicao, falha e refaz.

Escritos só a partir do CONTRATO (seções 0, 4, 5 e 6) e do ESQUEMA, sem ler o código da ferramenta.
Cada teste diz, na docstring, a cláusula que confere. A ferramenta é chamada pela linha de comando,
com raiz e pasta de trabalho temporárias e o relógio fixo em INFO_AGORA.

O que cada teste espera de nível, tendência e `desde` foi tirado à mão das regras R13 e R14 do
ESQUEMA, para o histórico montado no próprio teste.

Onde o contrato deixa duas leituras, a docstring começa com INTERPRETACAO e diz a leitura
escolhida e a outra. Na conciliação (23/11/2026), as leituras deste arquivo viraram frase do CONTRATO,
seções 4 a 6, ou do ESQUEMA, seção 10 ("Qual código sai"), e a marca saiu: hoje nenhum teste daqui a traz.

Rodar, da raiz do repositório:  python3 -B testes/contrato/regras/testa_contrato_publica.py
"""
import copy
import os
import re
import sys
import unittest
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import apoio  # noqa: E402
from apoio import (ANTEONTEM, DIA, F, ONTEM, TRES_ANTES, agora_de, calmaria, cega_energia, dia_mes,  # noqa: E402
                   gatilho, mais_dias, monta_edicao, poe, troca_titulos)

AMANHA = mais_dias(DIA, 1)
NS = "{%s}" % apoio.ATOM
BASE = "https://exemplo.invalid/INFOCENARIUM/"
MOTIVO = "Nada funcionou neste dia fictício: sem feed e sem busca."
AVISO_FIXO = ("Aviso: o INFOCENARIUM é escrito por modelos de IA, do setor de IA, que podem ser parte ou concorrente "
              "nesta notícia: foi construído pelo Claude Fable e pelo Claude Opus, da Anthropic, e hoje quem escreve é o "
              "GLM, da Z.ai.")
SINAIS_DE_MARKDOWN = ["\\", "[", "]", "(", ")", "*", "_", "`", "#", "|"]
ARQUIVOS_DA_PUBLICACAO = ["dados/players.json", "dados/vetores.json", "edicoes/%s.json" % DIA,
                          "edicoes/%s.md" % DIA, "edicoes/indice.json", "feed.xml"]


def P(edicao, i):
    return edicao["principais"][i]


def R(edicao, i):
    return edicao["radar"][i]


def data_br(dia):
    return "%s/%s/%s" % (dia[8:10], dia[5:7], dia[0:4])


def so_o_brent(dia):
    """O gatilho de preço do Brent, como o indicadores.py o entrega na edição "rica" do apoio."""
    return copy.deepcopy(apoio.dominio_de(monta_edicao(dia, rica=True), "energia")["gatilhos"][0])


class CasoDePublica(apoio.Caso):
    """Base: monta raiz e pasta de trabalho, chama os subcomandos e lê o que foi gravado."""

    def cenario(self, esperada=None, historico=(), com_git=False, feeds=True):
        """Devolve (raiz, pasta de trabalho, edição esperada). A pasta de trabalho sai coerente com a
        edição esperada: publicar o rascunho dela tem de dar exatamente essa edição."""
        if esperada is None:
            esperada = monta_edicao(DIA, rica=True)
        raiz = self.nova_raiz(historico, com_git=com_git)
        t = apoio.Trabalho(self.pasta("trabalho"), esperada, feeds=feeds)
        resumo = t.coleta()["resumo"]
        esperada["bastidores"].update(feeds_ok=resumo["feeds_ok"], feeds_falhos=resumo["feeds_falhos"])
        t.grava()
        return raiz, t, esperada

    def edicao(self, raiz, t, *mais, agora=None, com_dia=True, **kw):
        argumentos = ["edicao"] + (["--dia", t.dia] if com_dia else []) + list(mais)
        return self.publica(*argumentos, raiz=raiz, trabalho=t.pasta, agora=agora or agora_de(t.dia), **kw)

    def publicada(self, raiz, dia=DIA):
        return self.le_json_de(apoio.caminho_da_edicao(raiz, dia))

    def texto_md(self, raiz, dia=DIA):
        return self.le_arquivo(apoio.caminho_da_edicao(raiz, dia, "md"))

    def feed(self, raiz):
        """Devolve (texto, raiz do XML) do feed.xml. Se não é XML bem formado, o teste falha."""
        texto = self.le_arquivo(raiz, "feed.xml")
        try:
            return texto, ET.fromstring(texto.encode("utf-8"))
        except ET.ParseError as erro:
            self.fail("feed.xml não é XML bem formado: %s" % erro)

    def entradas(self, raiz):
        """As entradas do feed, por dia: {AAAA-MM-DD: elemento entry}."""
        _, xml = self.feed(raiz)
        achadas = {}
        for entrada in xml.findall(NS + "entry"):
            ident = entrada.findtext(NS + "id") or ""
            achadas[ident[-10:]] = entrada
        return achadas

    def publica_e_le(self, esperada=None, historico=(), **kw):
        raiz, t, esperada = self.cenario(esperada, historico, **kw)
        res = self.edicao(raiz, t)
        self.passou(res)
        return raiz, t, esperada, self.publicada(raiz, esperada["data"])

    def roda_contexto(self, raiz, dia=DIA, agora=None, com_dia=True):
        """Chama `publica.py contexto` e devolve (resultado, pasta de trabalho, contexto.json lido)."""
        pasta = self.pasta("trabalho")
        argumentos = ["contexto"] + (["--dia", dia] if com_dia else [])
        res = self.publica(*argumentos, raiz=raiz, trabalho=pasta, agora=agora or agora_de(dia))
        self.passou(res)
        return res, pasta, self.le_json_de(pasta, "contexto.json")

    def contexto_de(self, edicoes, dia=DIA, prepara=None):
        raiz = self.nova_raiz(edicoes)
        if prepara:
            prepara(raiz)
        return self.roda_contexto(raiz, dia)[2]


def dominio_do_contexto(contexto, ident):
    return [d for d in contexto["alerta_anterior"]["dominios"] if d["id"] == ident][0]


# =============================================================================================
# (a) contexto
# =============================================================================================

class Contexto(CasoDePublica):
    """CONTRATO, seção 4.1: `publica.py contexto`, linha a linha da tabela de regras."""

    # --- o que grava ---
    def test_contexto_grava_tres_arquivos_na_pasta_de_trabalho_e_nada_na_raiz(self):
        """CONTRATO, seção 4.1: "**Grava:** `P/contexto.json`, `P/mapa.txt` e `P/modelo.txt`"; seção 6:
        `publica.py contexto` grava no repositório "nada"; seção 0: a última linha começa com `OK`."""
        raiz = self.nova_raiz([monta_edicao(ONTEM)])
        antes = apoio.fotografa(raiz, rigor=True)
        res, pasta, _ = self.roda_contexto(raiz)
        self.assertEqual(sorted(os.listdir(pasta)), ["contexto.json", "mapa.txt", "modelo.txt"], res.relato())
        self.nada_mudou(antes, apoio.fotografa(raiz, rigor=True), "a raiz")

    def test_contexto_cria_a_pasta_de_trabalho_se_faltar(self):
        """CONTRATO, seção 0, `--trabalho`: "pasta de trabalho, fora do repositório; é criada se faltar"."""
        raiz = self.nova_raiz()
        pasta = os.path.join(self.pasta("fora"), "ainda", "nao", "existe")
        self.passou(self.publica("contexto", "--dia", DIA, raiz=raiz, trabalho=pasta))
        self.le_json_de(pasta, "contexto.json")

    def test_contexto_json_imprime_um_objeto(self):
        """CONTRATO, seção 0, `--json`: "imprime um objeto JSON no lugar do texto"."""
        res = self.publica("contexto", "--dia", DIA, "--json", raiz=self.nova_raiz(), trabalho=self.pasta("trabalho"))
        self.assertEqual(res.codigo, 0, res.relato())
        self.objeto_json(res)

    def test_contexto_edicao_antiga_ilegivel_da_falha_com_o_nome_do_arquivo(self):
        """CONTRATO, seção 4.1, "Código": "Edição antiga ilegível: `FALHA` com o nome do arquivo e código 1"."""
        raiz = self.nova_raiz([monta_edicao(ONTEM)])
        apoio.grava_texto(apoio.caminho_da_edicao(raiz, ANTEONTEM), '{"versao": 1, "data": ')
        res = self.publica("contexto", "--dia", DIA, raiz=raiz, trabalho=self.pasta("trabalho"))
        self.falhou(res)
        self.assertIn("%s.json" % ANTEONTEM, res.ultima, res.relato())

    # --- dia ---
    def test_contexto_dia_e_o_da_opcao(self):
        """CONTRATO, seção 4.1, `dia`: "o `--dia`: o agente usa este valor em `data` do rascunho"."""
        _, _, contexto = self.roda_contexto(self.nova_raiz(), ANTEONTEM, agora=agora_de(DIA))
        self.assertEqual(contexto["dia"], ANTEONTEM)

    def test_contexto_dia_padrao_e_hoje_em_brasilia(self):
        """CONTRATO, seção 0, `--dia`: "hoje em Brasília (UTC−3 fixo)"; "Relógio de teste": `INFO_AGORA`
        vale "no padrão de `--dia`". Às 02:59:59 UTC ainda é o dia anterior em Brasília."""
        raiz = self.nova_raiz()
        _, _, antes_da_virada = self.roda_contexto(raiz, agora=AMANHA + "T02:59:59Z", com_dia=False)
        _, _, depois_da_virada = self.roda_contexto(raiz, agora=AMANHA + "T03:00:00Z", com_dia=False)
        self.assertEqual((antes_da_virada["dia"], depois_da_virada["dia"]), (DIA, AMANHA))

    def test_contexto_dia_padrao_nao_le_o_contexto_antigo(self):
        """CONTRATO, seção 0, `--dia`: "No `publica.py contexto` […], o padrão é sempre hoje em Brasília:
        o primeiro cria o contexto" (não lê o `dia` de um `contexto.json` que já esteja na pasta)."""
        raiz, pasta = self.nova_raiz(), self.pasta("trabalho")
        apoio.grava_json(os.path.join(pasta, "contexto.json"), {"dia": TRES_ANTES, "janela_horas": 36})
        self.passou(self.publica("contexto", raiz=raiz, trabalho=pasta, agora=agora_de(DIA)))
        self.assertEqual(self.le_json_de(pasta, "contexto.json")["dia"], DIA)

    # --- sem edição nenhuma ---
    def test_contexto_sem_edicao_nenhuma(self):
        """CONTRATO, seção 4.1: `janela_horas` é 36 "se não há `anterior`"; `edicao_do_dia` e `anterior`
        são `null`; `alerta_anterior`, "Sem `anterior`: tudo em 1, `desde` = `--dia`, contadores em 0,
        `origem` `null`"; as listas saem vazias."""
        _, _, contexto = self.roda_contexto(self.nova_raiz())
        esperado = {
            "dia": DIA, "janela_horas": 36, "edicao_do_dia": None, "anterior": None,
            "alerta_anterior": {"nivel": 1, "dominios": [
                {"id": d, "nivel": 1, "desde": DIA, "edicoes_sem_gatilho": 0, "desce_hoje_sem_gatilho": False,
                 "origem": None} for d in apoio.dominios()]},
            "historias_recentes": [], "vigiar_vencendo": [], "candidatos": [], "vetores_recentes": [],
        }
        self.iguais(contexto, esperado, "contexto.json")

    # --- janela_horas e anterior ---
    def test_contexto_janela_36_quando_a_anterior_e_a_vespera(self):
        """CONTRATO, seção 4.1, `janela_horas`: "36 se `anterior.data` é a véspera de `dia`"; `anterior` é
        `{"data": …, "estado": …}`."""
        contexto = self.contexto_de([monta_edicao(ONTEM)])
        self.assertEqual(contexto["anterior"], {"data": ONTEM, "estado": "completa"})
        self.assertEqual(contexto["janela_horas"], 36)

    def test_contexto_janela_60_quando_a_anterior_e_mais_antiga(self):
        """CONTRATO, seção 4.1, `janela_horas`: "senão 60"."""
        contexto = self.contexto_de([monta_edicao(ANTEONTEM)])
        self.assertEqual((contexto["anterior"]["data"], contexto["janela_horas"]), (ANTEONTEM, 60))

    def test_contexto_falha_nao_e_anterior_e_abre_a_janela(self):
        """CONTRATO, seção 4.1, `anterior`: "a mais recente antes de `--dia` que não é `falha`";
        `janela_horas`: "depois de um dia de `falha`, a janela cobre o buraco"."""
        d2 = monta_edicao(ANTEONTEM)
        contexto = self.contexto_de([d2, apoio.edicao_falha(ONTEM, MOTIVO, anterior=d2)])
        self.assertEqual((contexto["anterior"]["data"], contexto["janela_horas"]), (ANTEONTEM, 60))

    def test_contexto_anterior_nao_tem_limite_de_dias(self):
        """CONTRATO, seção 4.1, `anterior`: "sem limite de dias"."""
        antiga = mais_dias(DIA, -40)
        contexto = self.contexto_de([monta_edicao(antiga)])
        self.assertEqual(contexto["anterior"], {"data": antiga, "estado": "completa"})

    def test_contexto_ignora_a_edicao_de_exemplo(self):
        """CONTRATO, seção 4.1: "Edição com `exemplo: true` é ignorada em tudo". O exemplo é da véspera;
        a anterior de verdade é a de dois dias antes."""
        self.assertEqual(apoio.exemplo()["data"], ONTEM)
        raiz = self.nova_raiz([monta_edicao(ANTEONTEM)])
        apoio.grava_json(apoio.caminho_da_edicao(raiz, ONTEM), apoio.exemplo())
        _, _, contexto = self.roda_contexto(raiz)
        self.assertEqual((contexto["anterior"]["data"], contexto["janela_horas"]), (ANTEONTEM, 60))
        self.assertEqual({h["edicao"] for h in contexto["historias_recentes"]}, {ANTEONTEM})

    def test_contexto_edicao_posterior_ao_dia_nao_e_anterior(self):
        """CONTRATO, seção 4.1, `anterior`: "a mais recente **antes de** `--dia`"."""
        d2 = monta_edicao(ANTEONTEM)
        contexto = self.contexto_de([d2, monta_edicao(AMANHA, anterior=d2)])
        self.assertEqual(contexto["anterior"]["data"], ANTEONTEM)

    # --- edicao_do_dia ---
    def test_contexto_edicao_do_dia_existente(self):
        """CONTRATO, seção 4.1, `edicao_do_dia`: "`null`, ou `{"estado": …, "gerada_em": …}` se
        `edicoes/DIA.json` já existe"."""
        d1 = monta_edicao(ONTEM)
        de_hoje = monta_edicao(DIA, anterior=d1)
        de_hoje["estado"] = "reduzida"
        contexto = self.contexto_de([d1, de_hoje])
        self.assertEqual(contexto["edicao_do_dia"], {"estado": "reduzida", "gerada_em": de_hoje["gerada_em"]})
        self.assertEqual(contexto["anterior"]["data"], ONTEM)

    def test_contexto_edicao_do_dia_de_falha(self):
        """CONTRATO, seção 4.1, `edicao_do_dia`; ROTINA, seção 1: "Estado `falha`: siga; a edição nova
        entra no lugar"."""
        d1 = monta_edicao(ONTEM)
        falha = apoio.edicao_falha(DIA, MOTIVO, anterior=d1)
        contexto = self.contexto_de([d1, falha])
        self.assertEqual(contexto["edicao_do_dia"], {"estado": "falha", "gerada_em": falha["gerada_em"]})

    def test_contexto_edicao_do_dia_ausente(self):
        """CONTRATO, seção 4.1, `edicao_do_dia`: "`null`" quando `edicoes/DIA.json` não existe."""
        self.assertIsNone(self.contexto_de([monta_edicao(ONTEM)])["edicao_do_dia"])

    # --- alerta_anterior ---
    def test_contexto_alerta_anterior_copia_os_niveis_da_anterior(self):
        """CONTRATO, seção 4.1, `alerta_anterior`: "níveis de `anterior`, com os 5 domínios"; `origem`: "a
        origem do nível […]: `edicao`, `criterio` e `texto` do gatilho […]; `null` no nível 1"."""
        d1 = monta_edicao(ONTEM, rica=True)                # energia 3, suprimentos 2, conflito 3
        alerta = self.contexto_de([d1])["alerta_anterior"]
        self.assertEqual(alerta["nivel"], 3)
        self.assertEqual([(d["id"], d["nivel"], d["desde"]) for d in alerta["dominios"]],
                         [("energia", 3, ONTEM), ("alimentos", 1, ONTEM), ("cambio", 1, ONTEM),
                          ("suprimentos", 2, ONTEM), ("conflito", 3, ONTEM)])
        do_evento = apoio.dominio_de(d1, "energia")["gatilhos"][1]
        energia = alerta["dominios"][0]
        self.assertEqual((energia["origem"]["edicao"], energia["origem"]["criterio"], energia["origem"]["texto"]),
                         (ONTEM, "energia.3", do_evento["texto"]))
        self.assertFalse(energia["origem"].get("preco"), "a origem do nível 3 é o evento, não o gatilho de preço")
        self.assertEqual((energia["edicoes_sem_gatilho"], energia["desce_hoje_sem_gatilho"]), (0, False))
        self.assertIsNone(alerta["dominios"][1]["origem"])
        self.assertIs(alerta["dominios"][1]["desce_hoje_sem_gatilho"], False)

    def test_contexto_uma_edicao_calma(self):
        """CONTRATO, seção 4.1, `edicoes_sem_gatilho`: "o `S` da regra R13"; `desce_hoje_sem_gatilho`:
        "`true` se `S` ≥ 2 e `nivel` > 1". Com uma edição calma depois do gatilho, `S` é 1."""
        d3, d2, _ = calmaria("suprimentos", "suprimentos.2")
        dominio = dominio_do_contexto(self.contexto_de([d3, d2], ONTEM), "suprimentos")
        self.assertEqual((dominio["nivel"], dominio["desde"], dominio["edicoes_sem_gatilho"],
                          dominio["desce_hoje_sem_gatilho"]), (2, TRES_ANTES, 1, False))
        self.assertEqual((dominio["origem"]["edicao"], dominio["origem"]["criterio"]), (TRES_ANTES, "suprimentos.2"))

    def test_contexto_duas_edicoes_calmas_desce_hoje(self):
        """CONTRATO, seção 4.1, `desce_hoje_sem_gatilho`: "`true` se `S` ≥ 2 e `nivel` > 1: sem gatilho
        hoje, e com o preço medido, o domínio desce 1". A origem continua sendo o gatilho de 3 dias atrás."""
        dominio = dominio_do_contexto(self.contexto_de(calmaria("suprimentos", "suprimentos.2")), "suprimentos")
        self.assertEqual((dominio["nivel"], dominio["desde"], dominio["edicoes_sem_gatilho"],
                          dominio["desce_hoje_sem_gatilho"]), (2, TRES_ANTES, 2, True))
        self.assertEqual((dominio["origem"]["edicao"], dominio["origem"]["criterio"]), (TRES_ANTES, "suprimentos.2"))

    def test_contexto_falha_nao_conta_como_edicao_calma(self):
        """CONTRATO, seção 4.1, `edicoes_sem_gatilho`: "edição `falha` e edição cega não contam"."""
        d3, _, _ = calmaria("suprimentos", "suprimentos.2")
        falha = apoio.edicao_falha(ANTEONTEM, MOTIVO, anterior=d3)
        d1 = monta_edicao(ONTEM, anterior=d3, alerta={"suprimentos": {"nivel": 2}})
        dominio = dominio_do_contexto(self.contexto_de([d3, falha, d1]), "suprimentos")
        self.assertEqual((dominio["edicoes_sem_gatilho"], dominio["desce_hoje_sem_gatilho"]), (1, False))

    def test_contexto_edicao_cega_nao_conta_como_edicao_calma(self):
        """CONTRATO, seção 4.1, `edicoes_sem_gatilho`: "edição `falha` e edição cega não contam"; ESQUEMA,
        seção 0: edição cega é "a que tem `sem_preco` não vazia nesse domínio"."""
        d3 = monta_edicao(TRES_ANTES, alerta={"energia": {"nivel": 2, "gatilhos": [gatilho("energia.2", "r4")]}})
        d2 = cega_energia(monta_edicao(ANTEONTEM, anterior=d3, alerta={"energia": {"nivel": 2}}))
        d1 = monta_edicao(ONTEM, anterior=d2, alerta={"energia": {"nivel": 2}})
        dominio = dominio_do_contexto(self.contexto_de([d3, d2, d1]), "energia")
        self.assertEqual((dominio["edicoes_sem_gatilho"], dominio["desce_hoje_sem_gatilho"]), (1, False))

    def test_contexto_origem_de_preco(self):
        """CONTRATO, seção 4.1, `origem`: "mais `"preco": true` se ele é de preço"."""
        d1 = monta_edicao(ONTEM, rica=True, alerta={"energia": {"nivel": 2, "gatilhos": [so_o_brent(ONTEM)]}})
        origem = dominio_do_contexto(self.contexto_de([d1]), "energia")["origem"]
        self.assertEqual((origem["edicao"], origem["criterio"]), (ONTEM, "energia.2"))
        self.assertIs(origem.get("preco"), True)
        self.assertFalse(origem.get("alivio"))

    def test_contexto_origem_de_alivio(self):
        """CONTRATO, seção 4.1, `origem`: "e `"alivio": true` se é de alívio"; ESQUEMA, seção 0: "O gatilho
        de alívio conta"; R13, conta `S`: "a calma começa a ser contada depois dele"."""
        d2 = monta_edicao(ANTEONTEM, alerta={"energia": {"nivel": 4, "gatilhos": [gatilho("energia.4", "p1")]}})
        alivio = gatilho("energia.4", "p1", F + "Acabou em %s: a rota fictícia foi reaberta." % dia_mes(ONTEM), alivio=True)
        d1 = monta_edicao(ONTEM, anterior=d2, alerta={"energia": {"nivel": 3, "gatilhos": [alivio]}})
        dominio = dominio_do_contexto(self.contexto_de([d2, d1]), "energia")
        self.assertEqual((dominio["nivel"], dominio["desde"], dominio["edicoes_sem_gatilho"]), (3, ONTEM, 0))
        self.assertEqual((dominio["origem"]["edicao"], dominio["origem"]["criterio"], dominio["origem"]["texto"]),
                         (ONTEM, "energia.4", alivio["texto"]))
        self.assertIs(dominio["origem"].get("alivio"), True)

    # --- historias_recentes ---
    def test_contexto_historias_das_tres_ultimas_edicoes_que_nao_sao_falha(self):
        """CONTRATO, seção 4.1, `historias_recentes`: "principais e radar das 3 últimas edições que não
        são `falha`; `vigiar` só nas principais". Cada entrada é `{"edicao", "id", "titulo", "vigiar"}`."""
        d5 = troca_titulos(monta_edicao(mais_dias(DIA, -5)), 0)
        d4 = troca_titulos(monta_edicao(mais_dias(DIA, -4), anterior=d5), 1)
        falha = apoio.edicao_falha(TRES_ANTES, MOTIVO, anterior=d4)
        d2 = troca_titulos(monta_edicao(ANTEONTEM, anterior=d4), 2)
        d1 = troca_titulos(monta_edicao(ONTEM, anterior=d2), 3)
        historias = self.contexto_de([d5, d4, falha, d2, d1])["historias_recentes"]
        obtido = {(h["edicao"], h["id"]): h for h in historias}
        esperado = {(e["data"], item["id"]): item for e in (d4, d2, d1) for item in apoio.itens(e)}
        self.assertEqual(sorted(obtido), sorted(esperado))
        self.assertEqual(len(historias), 27)
        for chave, item in esperado.items():
            self.assertEqual(obtido[chave]["titulo"], item["titulo"])
            if chave[1].startswith("p"):
                self.assertEqual(obtido[chave]["vigiar"], item["vigiar"])
            else:
                self.assertFalse(obtido[chave].get("vigiar"), "radar não tem vigiar")

    # --- vigiar_vencendo ---
    def _com_perguntas(self, dia, perguntas, anterior=None):
        """Edição de arquivo cujas principais perguntam o que o teste quer. `perguntas` é
        {indice da principal: [textos]}; as outras principais perguntam com prazo distante."""
        e = monta_edicao(dia, anterior=anterior)
        longe = dia_mes(mais_dias(DIA, 20))
        for i, principal in enumerate(e["principais"]):
            principal["vigiar"] = perguntas.get(i, ["O caso fictício número %d se resolve até %s?" % (i + 1, longe)])
        return e

    @staticmethod
    def _pergunta(numero, prazo):
        return "O prazo fictício número %d é cumprido até %s?" % (numero, dia_mes(prazo))

    def test_contexto_vigiar_vencendo_lista_as_perguntas_de_prazo_chegado(self):
        """CONTRATO, seção 4.1, `vigiar_vencendo`: "o primeiro `vigiar` de cada principal dos últimos 30
        dias cujo prazo já chegou (`prazo` ≤ `--dia`) […]. As de prazo mais antigo primeiro". Cada
        entrada é `{"edicao", "item", "pergunta", "prazo"}`."""
        d8 = mais_dias(DIA, -8)
        e = self._com_perguntas(d8, {0: [self._pergunta(1, ANTEONTEM)],        # venceu há 2 dias
                                     1: [self._pergunta(2, DIA)],              # vence hoje: prazo ≤ dia
                                     2: [self._pergunta(3, AMANHA)]})          # ainda não venceu
        vencendo = self.contexto_de([e])["vigiar_vencendo"]
        self.assertEqual(vencendo, [
            {"edicao": d8, "item": "p1", "pergunta": self._pergunta(1, ANTEONTEM), "prazo": ANTEONTEM},
            {"edicao": d8, "item": "p2", "pergunta": self._pergunta(2, DIA), "prazo": DIA},
        ])

    def test_contexto_vigiar_vencendo_so_o_primeiro_vigiar(self):
        """CONTRATO, seção 4.1, `vigiar_vencendo`: "o **primeiro** `vigiar` de cada principal" (o segundo,
        mesmo vencido, não entra)."""
        e = self._com_perguntas(mais_dias(DIA, -8), {0: [self._pergunta(1, mais_dias(DIA, 5)),
                                                         self._pergunta(2, TRES_ANTES)]})
        self.assertEqual(self.contexto_de([e])["vigiar_vencendo"], [])

    def test_contexto_vigiar_vencendo_tira_a_pergunta_ja_respondida(self):
        """CONTRATO, seção 4.1, `vigiar_vencendo`: "e que nenhuma edição respondeu em `respostas`"."""
        d8 = mais_dias(DIA, -8)
        e = self._com_perguntas(d8, {0: [self._pergunta(1, ANTEONTEM)], 1: [self._pergunta(2, TRES_ANTES)]})
        d1 = self._com_perguntas(ONTEM, {}, anterior=e)
        d1["respostas"] = [apoio.ordena({"edicao": d8, "item": "p1", "pergunta": self._pergunta(1, ANTEONTEM),
                                         "resposta": "sem_dado", "texto": F + "Nenhuma fonte trouxe a resposta."},
                                        "resposta")]
        vencendo = self.contexto_de([e, d1])["vigiar_vencendo"]
        self.assertEqual([(v["edicao"], v["item"]) for v in vencendo], [(d8, "p2")])

    def test_contexto_vigiar_vencendo_ate_tres_as_de_prazo_mais_antigo(self):
        """CONTRATO, seção 4.1, `vigiar_vencendo`: "Até 3, as de prazo mais antigo primeiro"."""
        edicoes, anterior = [], None
        for n, recuo in enumerate((9, 8, 7)):
            dia = mais_dias(DIA, -recuo)
            anterior = self._com_perguntas(dia, {0: [self._pergunta(2 * n + 1, mais_dias(DIA, -6 + 2 * n))],
                                                 1: [self._pergunta(2 * n + 2, mais_dias(DIA, -5 + 2 * n))]}, anterior)
            edicoes.append(anterior)
        vencendo = self.contexto_de(edicoes)["vigiar_vencendo"]
        self.assertEqual([v["prazo"] for v in vencendo], [mais_dias(DIA, -6), mais_dias(DIA, -5), mais_dias(DIA, -4)])
        self.assertEqual([(v["edicao"], v["item"]) for v in vencendo],
                         [(mais_dias(DIA, -9), "p1"), (mais_dias(DIA, -9), "p2"), (mais_dias(DIA, -8), "p1")])

    def test_contexto_vigiar_vencendo_prazo_e_a_ultima_data_da_pergunta(self):
        """CONTRATO, seção 4.1, `vigiar_vencendo`: "O `prazo` é a última data `DD/MM` da pergunta"."""
        d8 = mais_dias(DIA, -8)
        pergunta = "O acordo fictício, anunciado em %s, é assinado até %s?" % (dia_mes(mais_dias(DIA, -9)), dia_mes(ANTEONTEM))
        vencendo = self.contexto_de([self._com_perguntas(d8, {0: [pergunta]})])["vigiar_vencendo"]
        self.assertEqual([(v["item"], v["prazo"]) for v in vencendo], [("p1", ANTEONTEM)])

    def test_contexto_vigiar_vencendo_prazo_que_cai_no_ano_seguinte(self):
        """CONTRATO, seção 4.1, `vigiar_vencendo`: o prazo é a data `DD/MM` "lida como o primeiro dia
        assim a partir da edição que perguntou" (pergunta de 28/12 com prazo 05/01 vence no ano seguinte)."""
        e = self._com_perguntas("2026-12-28", {0: ["O prazo fictício de fim de ano é cumprido até 05/01?"]})
        for principal in e["principais"][1:]:
            principal["vigiar"] = ["O caso fictício se resolve até 25/01?"]
        vencendo = self.contexto_de([e], "2027-01-10")["vigiar_vencendo"]
        self.assertEqual([(v["edicao"], v["item"], v["prazo"]) for v in vencendo], [("2026-12-28", "p1", "2027-01-05")])

    def test_contexto_vigiar_vencendo_so_dos_ultimos_30_dias(self):
        """CONTRATO, seção 4.1, `vigiar_vencendo`: "de cada principal dos últimos 30 dias"."""
        d45 = mais_dias(DIA, -45)
        e = self._com_perguntas(d45, {0: [self._pergunta(1, mais_dias(DIA, -40))]})
        for principal in e["principais"][1:]:
            principal["vigiar"] = [self._pergunta(9, mais_dias(DIA, -38))]
        self.assertEqual(self.contexto_de([e])["vigiar_vencendo"], [])

    # --- candidatos ---
    @staticmethod
    def _com_candidatos(edicao, *candidatos):
        edicao["bastidores"]["candidatos"] = [{"id": i, "nome": n, "motivo": F + m} for i, n, m in candidatos]
        return edicao

    def test_contexto_candidatos_contados_por_id(self):
        """CONTRATO, seção 4.1, `candidatos`: "de `bastidores.candidatos` dos últimos 14 dias, contados
        por `id` (`edicoes` = em quantas edições apareceu); `motivo` é o da aparição mais recente". Cada
        entrada é `{"id", "nome", "edicoes", "ultima", "motivo"}`. A aparição de 20 dias atrás não conta."""
        d20 = self._com_candidatos(monta_edicao(mais_dias(DIA, -20)),
                                   ("reino_de_amostra", "Reino de Amostra (fictício)", "Aparição antiga."),
                                   ("ilha_de_teste", "Ilha de Teste (fictícia)", "Só apareceu há 20 dias."))
        d3 = self._com_candidatos(monta_edicao(TRES_ANTES, anterior=d20),
                                  ("reino_de_amostra", "Reino de Amostra (fictício)", "Primeira aparição da quinzena."))
        d2 = self._com_candidatos(monta_edicao(ANTEONTEM, anterior=d3))
        d1 = self._com_candidatos(monta_edicao(ONTEM, anterior=d2),
                                  ("reino_de_amostra", "Reino de Amostra (fictício)", "Aparição mais recente."))
        candidatos = self.contexto_de([d20, d3, d2, d1])["candidatos"]
        self.assertEqual(candidatos, [{"id": "reino_de_amostra", "nome": "Reino de Amostra (fictício)", "edicoes": 2,
                                       "ultima": ONTEM, "motivo": F + "Aparição mais recente."}])

    # --- vetores_recentes ---
    def test_contexto_vetores_recentes_sem_os_anulados_e_sem_os_antigos(self):
        """CONTRATO, seção 4.1, `vetores_recentes`: "de `dados/vetores.json`, últimos 30 dias, sem os
        anulados"; ESQUEMA, seção 12: "O `contexto` não o lista em `vetores_recentes`". Cada entrada é
        `{"id", "data", "player", "para", "forca"}`."""
        recente, antigo, anulado = mais_dias(DIA, -5), mais_dias(DIA, -45), mais_dias(DIA, -6)

        def vetor(dia, item, player, para):
            return {"id": "%s_%s_%s" % (dia, item, player), "data": dia, "item": item, "player": player,
                    "de": {"ue": "centro_atlantico", "google": "bancada_talento", "modi": "independentes"}[player],
                    "para": para, "forca": 2, "tema": "ordem", "porque": F + "Ato fictício do player.",
                    "url": "https://exemplo.invalid/outro/ato-%s" % player}

        def semeia(raiz):
            def muda(arquivo):
                arquivo["vetores"] += [
                    vetor(antigo, "p1", "modi", "soberanistas"),
                    vetor(anulado, "p2", "google", "ordem_global"),
                    vetor(recente, "p1", "ue", "soberanistas"),
                    {"id": "%s_anula_1" % ANTEONTEM, "data": ANTEONTEM, "anula": "%s_p2_google" % anulado,
                     "porque": F + "A fonte desmentiu o ato.", "url": "https://exemplo.invalid/outro/desmentido"},
                ]
            apoio.muda_json(os.path.join(raiz, "dados", "vetores.json"), muda)

        recentes = self.contexto_de([], prepara=semeia)["vetores_recentes"]
        self.assertEqual(recentes, [{"id": "%s_p1_ue" % recente, "data": recente, "player": "ue",
                                     "para": "soberanistas", "forca": 2}])

    # --- bordas ---
    def test_contexto_janelas_de_14_e_30_dias_incluem_o_dia_do_limite(self):
        """CONTRATO, seção 4.1, "Bordas": "As janelas de 14 e de 30 dias contam para trás a partir da véspera e
        incluem o dia do limite". No dia 20/11 valem a pergunta e o vetor de 21/10 (30 dias antes) e o
        candidato de 06/11 (14 dias antes); os de um dia antes de cada limite ficam de fora."""
        d31, d30, d15, d14 = (mais_dias(DIA, -n) for n in (31, 30, 15, 14))
        prazo = mais_dias(DIA, -20)
        e31 = self._com_candidatos(self._com_perguntas(d31, {0: [self._pergunta(1, prazo)]}))
        e30 = self._com_candidatos(self._com_perguntas(d30, {0: [self._pergunta(2, prazo)]}, anterior=e31))
        e15 = self._com_candidatos(self._com_perguntas(d15, {}, anterior=e30),
                                   ("ilha_de_teste", "Ilha de Teste (fictícia)", "Um dia antes da janela."))
        e14 = self._com_candidatos(self._com_perguntas(d14, {}, anterior=e15),
                                   ("reino_de_amostra", "Reino de Amostra (fictício)", "No dia do limite."))

        def semeia(raiz):
            def muda(arquivo):
                for dia, player, de in ((d31, "modi", "independentes"), (d30, "ue", "centro_atlantico")):
                    arquivo["vetores"].append({
                        "id": "%s_p1_%s" % (dia, player), "data": dia, "item": "p1", "player": player, "de": de,
                        "para": "soberanistas", "forca": 2, "tema": "ordem", "porque": F + "Ato fictício do player.",
                        "url": "https://exemplo.invalid/outro/ato-%s" % player})
            apoio.muda_json(os.path.join(raiz, "dados", "vetores.json"), muda)

        contexto = self.contexto_de([e31, e30, e15, e14], prepara=semeia)
        self.assertEqual([(v["edicao"], v["item"]) for v in contexto["vigiar_vencendo"]], [(d30, "p1")])
        self.assertEqual([(c["id"], c["edicoes"], c["ultima"]) for c in contexto["candidatos"]],
                         [("reino_de_amostra", 1, d14)])
        self.assertEqual([v["id"] for v in contexto["vetores_recentes"]], ["%s_p1_ue" % d30])

    def test_contexto_prazo_no_proprio_dia_da_pergunta(self):
        """CONTRATO, seção 4.1, "Bordas": "a data `DD/MM` igual à da própria edição que perguntou é esse mesmo
        dia". A pergunta de 12/11 com prazo 12/11 já venceu no dia 20/11 (não é 12/11 do ano seguinte)."""
        d8 = mais_dias(DIA, -8)
        vencendo = self.contexto_de([self._com_perguntas(d8, {0: [self._pergunta(1, d8)]})])["vigiar_vencendo"]
        self.assertEqual([(v["item"], v["prazo"]) for v in vencendo], [("p1", d8)])

    def test_contexto_nivel_1_conta_edicoes_calmas_e_nunca_desce(self):
        """CONTRATO, seção 4.1, "Bordas": "Em nível 1, `edicoes_sem_gatilho` é contado do mesmo jeito, e
        `desce_hoje_sem_gatilho` é sempre `false`". Três edições calmas em nível 1: energia conta 3 (alimentos
        conta 0, porque o milho sem dado deixa as três cegas para alimentos)."""
        d3 = monta_edicao(TRES_ANTES)
        d2 = monta_edicao(ANTEONTEM, anterior=d3)
        d1 = monta_edicao(ONTEM, anterior=d2)
        contexto = self.contexto_de([d3, d2, d1])
        energia, alimentos = dominio_do_contexto(contexto, "energia"), dominio_do_contexto(contexto, "alimentos")
        self.assertEqual((energia["nivel"], energia["edicoes_sem_gatilho"], energia["desce_hoje_sem_gatilho"]),
                         (1, 3, False))
        self.assertEqual((alimentos["nivel"], alimentos["edicoes_sem_gatilho"]), (1, 0))
        self.assertTrue(all(d["desce_hoje_sem_gatilho"] is False and d["origem"] is None
                            for d in contexto["alerta_anterior"]["dominios"]))

    # --- mapa.txt ---
    def _mapa(self, prepara=None):
        raiz = self.nova_raiz()
        if prepara:
            prepara(raiz)
        _, pasta, _ = self.roda_contexto(raiz)
        return self.le_arquivo(pasta, "mapa.txt").rstrip("\n").split("\n")

    def test_mapa_uma_linha_por_veiculo_em_ordem_de_id(self):
        """CONTRATO, seção 4.1, "Formato de `mapa.txt`": "Uma linha por veículo do mapa, em ordem de `id`",
        depois da linha de legenda."""
        linhas = self._mapa()
        ids = sorted(apoio.veiculos())
        self.assertEqual(len(linhas), 1 + len(ids))
        self.assertEqual([linha.split(" · ")[0] for linha in linhas[1:]], ids)

    def test_mapa_legenda_de_mapa_em_rascunho(self):
        """CONTRATO, seção 4.1: "A primeira linha é a legenda das colunas. Diz `rascunho, sem revisão do
        dono` enquanto `revisado_em` é `null` no mapa". O começo da linha segue o bloco de exemplo do
        CONTRATO, com a contagem de veículos do mapa congelado."""
        legenda = self._mapa()[0]
        self.assertTrue(legenda.startswith("MAPA · %d veículos · rascunho, sem revisão do dono" % len(apoio.veiculos())),
                        legenda)

    def test_mapa_legenda_de_mapa_revisado(self):
        """CONTRATO, seção 4.1: "depois, `revisado em DD/MM/AAAA`"."""
        def revisa(raiz):
            apoio.muda_json(os.path.join(raiz, "dados", "veiculos.json"), lambda m: m.update(revisado_em="2026-11-22"))
        legenda = self._mapa(revisa)[0]
        self.assertIn("revisado em 22/11/2026", legenda)
        self.assertNotIn("rascunho", legenda)

    def test_mapa_linhas_do_exemplo_do_contrato(self):
        """CONTRATO, seção 4.1, "Formato de `mapa.txt`": "O bloco é o formato exato: as colunas vêm separadas
        por ` · `, nesta ordem". As três linhas do bloco (afp, anthropic_news e ap) saem assim, letra por
        letra, do mapa congelado."""
        linhas = self._mapa()
        for esperada in ("afp · CA · fatos alta · agencia · serve a: ue, macron · afp.com · Agence France-Presse (AFP)",
                         "anthropic_news · IN · fatos media · oficial · serve a: anthropic · anthropic.com · "
                         "Anthropic (sala de imprensa) · LIGADO À ANTHROPIC",
                         "ap · CA? · fatos alta · agencia · serve a: — · apnews.com · Associated Press (AP)"):
            self.assertIn(esperada, linhas)

    def test_mapa_campos_de_cada_veiculo(self):
        """CONTRATO, seção 4.1, "Formato de `mapa.txt`": o formato exato do bloco (colunas separadas por ` · `,
        nesta ordem): a sigla do partido, com `?` em veículo de
        lado incerto; `fatos`; `tipo`; "`serve a` lista os players de `serve_a` (partido não entra); `—`
        se não há"; "`site` é o primeiro de `sites`"; o nome; e "`LIGADO À ANTHROPIC` marca veículo com
        `anthropic` em `serve_a` ou em `alvos`"."""
        siglas = {p["id"]: p["sigla"] for p in apoio.regua()["partidos"]}
        players = {p["id"] for p in apoio.dados("players")["players"]}
        mapa = apoio.veiculos()
        por_id = {linha.split(" · ")[0]: linha.split(" · ") for linha in self._mapa()[1:]}
        for ident, v in mapa.items():
            with self.subTest(veiculo=ident):
                campos = por_id[ident]
                servidos = [p for p in v["serve_a"] if p in players]
                ligado = "anthropic" in v["serve_a"] or "anthropic" in v["alvos"]
                esperado = [ident, siglas[v["lado"]] + ("?" if v["lado_confianca"] == "baixa" else ""),
                            "fatos " + v["fatos"], v["tipo"], "serve a: " + (", ".join(servidos) or "—"),
                            v["sites"][0], v["nome"]] + (["LIGADO À ANTHROPIC"] if ligado else [])
                self.assertEqual(campos, esperado)

    # --- modelo.txt ---
    def test_modelo_e_o_texto_do_contrato(self):
        """CONTRATO, seção 4.1, "Formato de `modelo.txt`": "O arquivo é sempre o mesmo texto […]. O texto
        é este:" (o bloco do CONTRATO está copiado em `modelo_esperado.txt`, nesta pasta). A comparação
        não conta quebra de linha no fim do arquivo."""
        _, pasta, _ = self.roda_contexto(self.nova_raiz([monta_edicao(ONTEM)]))
        obtido = self.le_arquivo(pasta, "modelo.txt").rstrip("\n").split("\n")
        esperado = apoio.le_texto(apoio.MODELO_ESPERADO).rstrip("\n").split("\n")
        self.assertEqual(obtido, esperado)

    def test_modelo_sem_os_comentarios_e_json_e_so_tem_campo_do_agente(self):
        """CONTRATO, seção 4.1: "Tirando as linhas de comentário, é JSON válido"; "o modelo traz todo
        campo de origem `agente` e `misto` […] e nenhum campo calculado"."""
        import json
        _, pasta, _ = self.roda_contexto(self.nova_raiz())
        linhas = [l for l in self.le_arquivo(pasta, "modelo.txt").split("\n") if not l.lstrip().startswith("//")]
        try:
            modelo = json.loads("\n".join(linhas))
        except ValueError as erro:
            self.fail("modelo.txt sem os comentários não é JSON: %s" % erro)
        self.assertEqual(list(modelo), ["data", "estado", "resumo", "alerta", "principais", "radar", "placar_do_dia",
                                        "novos_players", "errata", "respostas", "bastidores"])
        self.assertEqual(list(modelo["alerta"]["dominios"][0]), ["id", "gatilhos", "leitura", "vigiar"])
        self.assertNotIn("lado", modelo["principais"][0]["ataques"][0])
        self.assertEqual(list(modelo["placar_do_dia"][0]), ["partido", "frase"])
        for calculado in ("veiculos_consultados", "feeds_ok", "feeds_falhos"):
            self.assertNotIn(calculado, modelo["bastidores"])


# =============================================================================================
# (b) edicao: publica, campo a campo
# =============================================================================================

class EdicaoPublica(CasoDePublica):
    """CONTRATO, seção 4.2, passos 4, 7 e 8, numa raiz sem edição anterior."""

    def test_edicao_publica_com_codigo_zero(self):
        """CONTRATO, seção 4.2, "Código": "0 publicada"; seção 0: a última linha começa com `OK`."""
        raiz, t, _ = self.cenario()
        self.passou(self.edicao(raiz, t))

    def test_edicao_ultima_linha_no_formato(self):
        """CONTRATO, seção 4.2, passo 8: "Última linha: `OK edição 2026-11-20 publicada: nível 2 ATENÇÃO
        (energia 2, alimentos 1, cambio 2, suprimentos 1, conflito 1), 3 principais, 9 radar, 1 vetor, 0 players
        novos`. É o formato da linha: os domínios pelo id, na ordem da régua (`cambio`, sem acento); o rótulo
        do nível é o da régua; singular só com 1". Aqui: nível 3 TENSÃO, 3 principais, 6 no radar, 2 vetores
        e 1 player novo."""
        raiz, t, _ = self.cenario()
        res = self.edicao(raiz, t)
        self.assertEqual(res.ultima, "OK edição 2026-11-20 publicada: nível 3 TENSÃO (energia 3, alimentos 1, "
                                     "cambio 1, suprimentos 2, conflito 3), 3 principais, 6 radar, 2 vetores, "
                                     "1 player novo", res.relato())

    def test_edicao_grava_os_seis_arquivos_e_so_eles(self):
        """CONTRATO, seção 4.2, passo 7: grava `edicoes/DIA.json`, `edicoes/DIA.md`, `edicoes/indice.json`,
        `feed.xml`, `dados/vetores.json` e `dados/players.json`; "O `publica.py` nunca grava
        `dados/veiculos.json`, `dados/regua.json` nem `dados/indicadores.json`"; seção 6: sem `--corta`,
        não grava na pasta de trabalho."""
        raiz, t, _ = self.cenario()
        antes, antes_trabalho = apoio.fotografa(raiz), apoio.fotografa(t.pasta, rigor=True)
        self.passou(self.edicao(raiz, t))
        criados, mudados, sumidos = apoio.diferenca(antes, apoio.fotografa(raiz))
        self.assertEqual(sorted(x for x in criados + mudados if not x.endswith("/")), ARQUIVOS_DA_PUBLICACAO)
        self.assertEqual(sumidos, [])
        self.nada_mudou(antes_trabalho, apoio.fotografa(t.pasta, rigor=True), "a pasta de trabalho")

    def test_edicao_publicada_e_igual_a_esperada(self):
        """CONTRATO, seção 4.2, passo 7: "`edicoes/DIA.json`, completo e normalizado", com os campos
        calculados do passo 4. A edição inteira é comparada com a esperada (os testes seguintes olham
        campo a campo)."""
        raiz, t, esperada, publicada = self.publica_e_le()
        self.iguais(apoio.sem_marca_desligada(publicada), esperada, "edicoes/%s.json" % DIA)

    def test_edicao_resultado_passa_no_valida(self):
        """CONTRATO, seção 5, sétima linha da rotina: `valida.py --tudo --base origin/main --dia "$DIA"`
        roda depois do `publica.py edicao` e tem de dar código 0. Também `valida.py --edicao` no arquivo
        publicado e `valida.py` sem opção."""
        raiz, t, _ = self.cenario(com_git=True)
        self.passou(self.edicao(raiz, t))
        self.passou(self.valida("--tudo", "--base", "origin/main", "--dia", DIA, raiz=raiz))
        self.passou(self.valida("--edicao", apoio.caminho_da_edicao(raiz, DIA), raiz=raiz))
        self.passou(self.valida(raiz=raiz))

    def test_edicao_formato_do_json_gravado(self):
        """CONTRATO, seção 0: "JSON gravado: UTF-8, sem BOM, acentos legíveis, recuo de 2 espaços, quebra
        de linha no fim, chaves na ordem do `ESQUEMA.md`"."""
        raiz, t, _ = self.cenario()
        self.passou(self.edicao(raiz, t))
        self.publicada(raiz)
        bruto = apoio.le_bytes(apoio.caminho_da_edicao(raiz, DIA))
        self.assertFalse(bruto.startswith(b"\xef\xbb\xbf"), "tem BOM")
        texto = bruto.decode("utf-8")
        self.assertTrue(texto.startswith('{\n  "versao": 1,\n  "data": "%s",\n' % DIA), texto[:80])
        self.assertTrue(texto.endswith("}\n") and not texto.endswith("\n\n"), repr(texto[-20:]))
        self.assertIn("fictício", texto)
        self.assertNotIn("\\u00", texto, "acento gravado como \\uXXXX")
        self.assertEqual(apoio.chaves_fora_de_ordem(self.publicada(raiz)), [])

    def test_edicao_poe_as_chaves_em_ordem_mesmo_com_o_rascunho_fora_de_ordem(self):
        """ESQUEMA, seção 0: "As chaves são gravadas na ordem das tabelas abaixo"; CONTRATO, seção 4.2,
        passo 7: "completo e normalizado". O rascunho vem com as chaves de todo objeto em ordem
        invertida, menos as de `dna` e `dna_fontes` (ali as chaves são os temas, e a tabela pede "na
        ordem da régua": o contrato não diz se o publica.py reordena ou recusa)."""
        raiz, t, esperada = self.cenario()

        def inverte(x, chave=None):
            if isinstance(x, dict) and chave not in ("dna", "dna_fontes"):
                return {k: inverte(x[k], k) for k in reversed(list(x))}
            return [inverte(v) for v in x] if isinstance(x, list) else x

        t.rascunho = inverte(t.rascunho)
        t.grava()
        self.passou(self.edicao(raiz, t))
        publicada = self.publicada(raiz)
        self.assertEqual(apoio.chaves_fora_de_ordem(publicada), [])
        self.iguais(apoio.sem_marca_desligada(publicada), esperada, "edicoes/%s.json" % DIA)

    # --- passo 4, campo a campo ---
    def test_campo_versao_e_gerada_em(self):
        """CONTRATO, seção 4.2, passo 4: "`versao` e `gerada_em` (hora UTC de agora, sempre que a edição é
        gravada)"; seção 0: `INFO_AGORA` vale "em todo `gerada_em`"."""
        _, _, _, publicada = self.publica_e_le()
        self.assertEqual((publicada["versao"], publicada["gerada_em"]), (1, agora_de(DIA)))

    def test_campo_lado_de_cada_ataque(self):
        """CONTRATO, seção 4.2, passo 4: "`lado` de cada ataque, copiado do mapa"."""
        _, _, _, publicada = self.publica_e_le()
        mapa = apoio.veiculos()
        ataques = [a for item in apoio.itens(publicada) for a in apoio.ataques_de(item)]
        self.assertEqual(len(ataques), 14)
        self.assertEqual([a.get("lado") for a in ataques], [mapa[a["veiculo"]]["lado"] for a in ataques])

    def test_campo_indicadores(self):
        """CONTRATO, seção 4.2, passo 4: "`indicadores`, copiado de `P/indicadores.json`"."""
        _, t, _, publicada = self.publica_e_le()
        self.iguais(publicada["indicadores"], t.indicadores["indicadores"], "indicadores")

    def test_campo_gatilho_de_preco_na_frente(self):
        """CONTRATO, seção 4.2, passo 4: "os gatilhos de preço de cada domínio, copiados de
        `P/indicadores.json`, na frente dos do agente"."""
        _, t, _, publicada = self.publica_e_le()
        gatilhos = apoio.dominio_de(publicada, "energia")["gatilhos"]
        self.assertEqual(gatilhos[0], t.indicadores["gatilhos"][0])
        self.assertEqual([(g["criterio"], g["ref"]) for g in gatilhos], [("energia.2", "brent"), ("energia.3", "p1")])

    def test_campo_sem_preco(self):
        """CONTRATO, seção 4.2, passo 4: "`sem_preco` de cada domínio (regra R13f)". No cenário, o milho
        não tem variação de 7 dias; os outros indicadores de preço foram medidos."""
        _, _, _, publicada = self.publica_e_le()
        self.assertEqual([d["sem_preco"] for d in publicada["alerta"]["dominios"]], [[], ["milho"], [], [], []])

    def test_campo_niveis_tendencias_e_desde_sem_edicao_anterior(self):
        """CONTRATO, seção 4.2, passo 4: "`nivel` de cada domínio (regra R13), `alerta.nivel`, as
        `tendencia` e os `desde` (regra R14)". Sem edição anterior: `N` é 1, o nível é o maior gatilho de
        hoje, a tendência é `estavel` e `desde` é `data`."""
        _, _, _, publicada = self.publica_e_le()
        alerta = publicada["alerta"]
        self.assertEqual([(d["id"], d["nivel"]) for d in alerta["dominios"]],
                         [("energia", 3), ("alimentos", 1), ("cambio", 1), ("suprimentos", 2), ("conflito", 3)])
        self.assertEqual((alerta["nivel"], alerta["tendencia"]), (3, "estavel"))
        self.assertEqual({d["tendencia"] for d in alerta["dominios"]}, {"estavel"})
        self.assertEqual({d["desde"] for d in alerta["dominios"]}, {DIA})

    def test_campo_conflito_de_interesse(self):
        """CONTRATO, seção 4.2, passo 4: "`conflito_de_interesse` de cada item (regra R19: liga, nunca
        desliga)". No cenário, os itens de IA (p2, r1, r2 e r3) saem com a marca; os outros, sem."""
        _, _, _, publicada = self.publica_e_le()
        marcados = [item["id"] for item in apoio.itens(publicada) if item.get("conflito_de_interesse") is True]
        self.assertEqual(marcados, ["p2", "r1", "r2", "r3"])

    def test_campo_placar_do_dia(self):
        """CONTRATO, seção 4.2, passo 4: "`placar_do_dia[].saldo`, `narrativa` e a ordem da lista (regra
        R12)"; ESQUEMA, seção 6: "maior saldo primeiro; empate segue a ordem da régua". O rascunho traz
        as frases em ordem invertida."""
        raiz, t, _ = self.cenario()
        frases = {p["partido"]: p["frase"] for p in t.rascunho["placar_do_dia"]}
        t.rascunho["placar_do_dia"].reverse()
        t.grava()
        self.passou(self.edicao(raiz, t))
        placar = self.publicada(raiz)["placar_do_dia"]
        self.assertEqual([(p["partido"], p["saldo"], p["narrativa"]) for p in placar],
                         [("ordem_global", 4, 1), ("independentes", 2, 0), ("soberanistas", 0, 2),
                          ("eixo_revisionista", 0, 1), ("centrao", -1, 0), ("centro_atlantico", -2, 0),
                          ("bancada_talento", -2, 0)])
        self.assertEqual({p["partido"]: p["frase"] for p in placar}, frases)

    def test_campo_contadores_dos_bastidores(self):
        """CONTRATO, seção 4.2, passo 4: "`bastidores.veiculos_consultados`, `feeds_ok` e `feeds_falhos`";
        ESQUEMA, seção 9: `feeds_ok` e `feeds_falhos` vêm "de `coleta.json`"; `veiculos_consultados` são os
        "veículos distintos do mapa citados em `fontes`"."""
        raiz, t, _ = self.cenario()
        self.assertEqual((t.coleta()["resumo"]["feeds_ok"], t.coleta()["resumo"]["feeds_falhos"]), (15, 4))
        self.passou(self.edicao(raiz, t))
        b = self.publicada(raiz)["bastidores"]
        self.assertEqual((b["veiculos_consultados"], b["feeds_ok"], b["feeds_falhos"]), (19, 15, 4))

    def test_campo_calculado_que_vem_no_rascunho_e_trocado(self):
        """ESQUEMA, seção 0: "Campo calculado que vier no rascunho é trocado, sem erro"; seção 2: "Gatilho
        com `ref` de indicador que vier no rascunho é trocado"."""
        raiz, t, esperada = self.cenario()
        r = t.rascunho
        r["versao"], r["gerada_em"] = 7, "2020-01-01T00:00:00Z"
        r["alerta"].update(nivel=5, tendencia="descendo")
        for dominio in r["alerta"]["dominios"]:
            dominio.update(nivel=5, tendencia="descendo", desde="2020-01-01", sem_preco=["ouro"])
        r["alerta"]["dominios"][0]["gatilhos"].insert(0, {"criterio": "energia.4", "ref": "brent",
                                                          "texto": F + "Gatilho de preço escrito à mão."})
        r["indicadores"] = []
        r["principais"][0]["ataques"][0]["lado"] = "soberanistas"
        for linha in r["placar_do_dia"]:
            linha.update(saldo=99, narrativa=99)
        r["bastidores"].update(veiculos_consultados=0, feeds_ok=0, feeds_falhos=0)
        t.grava()
        self.passou(self.edicao(raiz, t))
        self.iguais(apoio.sem_marca_desligada(self.publicada(raiz)), esperada, "edicoes/%s.json" % DIA)

    def test_edicao_sem_indicadores_json(self):
        """CONTRATO, seção 4.2, passo 4: "`indicadores`, copiado de `P/indicadores.json` (sem o arquivo:
        lista vazia e aviso)". Sem preço medido, todo domínio com critério de preço fica cego (R13f), e
        não há gatilho de preço."""
        raiz, t, _ = self.cenario()
        t.indicadores = None
        t.grava()
        self.passou(self.edicao(raiz, t))
        publicada = self.publicada(raiz)
        self.assertEqual(publicada["indicadores"], [])
        self.assertEqual([d["sem_preco"] for d in publicada["alerta"]["dominios"]],
                         [["brent"], ["trigo", "milho", "soja"], ["usd_brl"], [], []])
        self.assertEqual([g["ref"] for g in apoio.dominio_de(publicada, "energia")["gatilhos"]], ["p1"])
        self.assertEqual(apoio.dominio_de(publicada, "energia")["nivel"], 3)

    def test_edicao_sem_coleta_json(self):
        """CONTRATO, seção 4.2, passo 4: "`bastidores.veiculos_consultados`, `feeds_ok` e `feeds_falhos`
        (sem `P/coleta.json`: 0 e aviso)". As fontes chegam todas por página aberta, com data conferida."""
        raiz, t, _ = self.cenario(feeds=False)
        t.sem_coleta = True
        t.grava()
        self.passou(self.edicao(raiz, t))
        b = self.publicada(raiz)["bastidores"]
        self.assertEqual((b["veiculos_consultados"], b["feeds_ok"], b["feeds_falhos"]), (19, 0, 0))

    def test_edicao_sem_conferencia_json_avisa(self):
        """CONTRATO, seção 4.2, passo 5: "Sem `P/conferencia.json`, só as URLs de `coleta.json` têm data
        conferida, e o comando avisa: "rode `coleta.py --confere`"". No cenário, as fontes de feed bastam
        para as contas da regra T3: a edição sai."""
        raiz, t, _ = self.cenario()
        t.sem_conferencia = True
        t.grava()
        res = self.edicao(raiz, t)
        self.passou(res)
        self.assertIn("--confere", res.saida, res.relato())

    def test_edicao_dia_padrao_vem_do_contexto(self):
        """CONTRATO, seção 0, `--dia`: o padrão é "o `dia` de `P/contexto.json`, se o arquivo existe"; "uma
        execução que cruza a meia-noite não troca de dia no meio". O relógio já está no dia seguinte."""
        raiz, t, _ = self.cenario()
        depois_da_meia_noite = AMANHA + "T03:10:00Z"
        self.passou(self.edicao(raiz, t, agora=depois_da_meia_noite, com_dia=False))
        publicada = self.publicada(raiz, DIA)
        self.assertEqual((publicada["data"], publicada["gerada_em"]), (DIA, depois_da_meia_noite))

    # --- conflito de interesse: liga, nunca desliga ---
    def _publica_com(self, muda):
        """Publica o cenário de base com uma mudança no rascunho. Devolve a edição publicada."""
        raiz, t, _ = self.cenario()
        muda(t.rascunho, t)
        t.grava()
        self.passou(self.edicao(raiz, t))
        return self.publicada(raiz)

    def test_conflito_liga_em_item_de_ia_mesmo_com_false_no_rascunho(self):
        """ESQUEMA, seção 10, R19: "O `publica.py` liga a marca nesses casos. […] ninguém desliga" (caso a:
        categoria `ia`)."""
        def muda(r, t):
            poe(r["radar"][0], "radar", conflito_de_interesse=False)
        self.assertIs(self._publica_com(muda)["radar"][0].get("conflito_de_interesse"), True)

    def test_conflito_liga_quando_o_alvo_esta_na_lista(self):
        """ESQUEMA, seção 10, R19, caso (b): "algum `alvo` de ataque […] está em […] `conflito.players`"."""
        def muda(r, t):
            ataque = r["radar"][3]["ataque"]               # r4: valor e ft, dois partidos
            ataque["alvo"] = "musk"
            del ataque["alvo_nome"]
        self.assertIs(self._publica_com(muda)["radar"][3].get("conflito_de_interesse"), True)

    def test_conflito_liga_quando_o_texto_traz_termo_da_lista(self):
        """ESQUEMA, seção 10, R19, caso (c): "algum texto do item, inclusive título de fonte, traz um termo
        de `conflito.termos`". A principal p3 tem confiança alta; com a marca, o máximo é media."""
        def muda(r, t):
            r["principais"][2]["na_pratica"][0] += " A OpenAI comentou."
            r["principais"][2]["confianca"] = "media"
        self.assertIs(self._publica_com(muda)["principais"][2].get("conflito_de_interesse"), True)

    def test_conflito_liga_quando_a_fonte_e_de_veiculo_ligado_a_anthropic(self):
        """ESQUEMA, seção 10, R19, caso (d): "alguma fonte do item é de veículo que tem `anthropic` em
        `serve_a` ou em `alvos` no mapa"."""
        url = "https://futureoflife.org/exemplo/seguro-suspenso"

        def muda(r, t):
            r["radar"][3]["fontes"].append(apoio.ordena({"veiculo": "fli", "titulo": "Insurers and the Example Strait",
                                                         "url": url, "publicado_em": DIA}, "fonte"))
            t.abre(url, publicado_em=DIA)

        publicada = self._publica_com(muda)
        self.assertIs(publicada["radar"][3].get("conflito_de_interesse"), True)
        self.assertEqual(publicada["bastidores"]["veiculos_consultados"], 20)

    def test_conflito_ligado_pelo_agente_nao_e_desligado(self):
        """ESQUEMA, seção 10, R19: "O agente pode ligar em outros; ninguém desliga"."""
        def muda(r, t):
            poe(r["principais"][2], "principal", conflito_de_interesse=True, confianca="media")
        self.assertIs(self._publica_com(muda)["principais"][2].get("conflito_de_interesse"), True)

    # --- índice ---
    def test_indice_da_edicao_publicada(self):
        """CONTRATO, seção 4.2, passo 7: "`edicoes/indice.json`, refeito a partir de todos os arquivos de
        edição (`ESQUEMA.md`, seção 11)". Confere cada campo da tabela da seção 11."""
        raiz, _, esperada, _ = self.publica_e_le()
        indice = self.le_json_de(raiz, "edicoes", "indice.json")
        self.assertEqual((indice["versao"], indice["atualizado_em"], len(indice["edicoes"])), (1, agora_de(DIA), 1))
        entrada = indice["edicoes"][0]
        self.assertEqual(list(entrada), apoio.ORDEM_INDICE)
        self.assertEqual((entrada["data"], entrada["arquivo"], entrada["texto"]),
                         (DIA, "edicoes/%s.json" % DIA, "edicoes/%s.md" % DIA))
        self.assertEqual((entrada["estado"], entrada["nivel"], entrada["tendencia"], entrada["resumo"],
                          entrada["gerada_em"]), ("completa", 3, "estavel", esperada["resumo"], agora_de(DIA)))
        self.assertEqual(list(entrada["niveis"].items()),
                         [("energia", 3), ("alimentos", 1), ("cambio", 1), ("suprimentos", 2), ("conflito", 3)])
        self.assertEqual(entrada["saldos"], {"ordem_global": 4, "independentes": 2, "soberanistas": 0,
                                             "eixo_revisionista": 0, "centrao": -1, "centro_atlantico": -2,
                                             "bancada_talento": -2})
        self.assertEqual(entrada["eixos"], {"clima": {"azul": 0, "vermelho": 1}, "ia_depois": {"azul": 2, "vermelho": 0}})
        self.assertEqual(entrada["indicadores"], {"brent": 78.4, "wti": 74.1, "trigo": 216.9, "milho": 179.3,
                                                  "soja": 383.1, "fao_ffpi": 126.4, "usd_brl": 5.4321, "dxy": 103.2,
                                                  "ouro": 2650.0, "vix": 18.4})
        self.assertIs(entrada["exemplo"], False)
        self.assertEqual(entrada["corrigida_em"], [])

    def test_indice_mais_nova_primeiro_e_corrigida_em(self):
        """ESQUEMA, seção 11: "Mais nova primeiro. Uma entrada por edição"; `atualizado_em` é "igual ao
        maior `gerada_em`"; `corrigida_em` lista as "edições posteriores cuja `errata` cita esta"."""
        ontem = troca_titulos(monta_edicao(ONTEM), 0)
        hoje = monta_edicao(DIA, anterior=ontem, rica=True)
        hoje["errata"] = [apoio.ordena({"edicao": ONTEM, "item": "r3", "erro": F + "A edição anterior deu o prazo errado.",
                                        "correcao": F + "O prazo certo é de 30 dias."}, "errata")]
        raiz, _, _, _ = self.publica_e_le(hoje, [ontem])
        indice = self.le_json_de(raiz, "edicoes", "indice.json")
        self.assertEqual([e["data"] for e in indice["edicoes"]], [DIA, ONTEM])
        self.assertEqual(indice["atualizado_em"], agora_de(DIA))
        self.assertEqual([e["corrigida_em"] for e in indice["edicoes"]], [[], [DIA]])
        self.iguais(indice, apoio.indice_de([ontem, self.publicada(raiz)]), "edicoes/indice.json")

    # --- os registros ---
    def test_registro_de_vetores_cresce(self):
        """CONTRATO, seção 4.2, passo 7: "`dados/vetores.json`: acrescenta os vetores da edição (com
        `conflito_de_interesse: true` quando o item tem a marca)"; ESQUEMA, seção 12: `id` é "`data` + `_` +
        id do item + `_` + id do player"; `de` é "o partido do player, copiado de `players.json`"."""
        raiz, _, esperada, _ = self.publica_e_le()
        registro = self.le_json_de(raiz, "dados", "vetores.json")
        self.assertEqual(list(registro), ["versao", "regra", "vetores"])
        self.iguais(registro["vetores"], apoio.vetores_registrados(esperada), "dados/vetores.json")
        da_ue, do_google = registro["vetores"]
        self.assertEqual((da_ue["id"], da_ue["de"], da_ue["para"]), ("%s_p1_ue" % DIA, "centro_atlantico", "soberanistas"))
        self.assertNotIn("conflito_de_interesse", da_ue)
        self.assertEqual((do_google["id"], do_google["de"]), ("%s_r2_google" % DIA, "bancada_talento"))
        self.assertIs(do_google.get("conflito_de_interesse"), True)
        for entrada in registro["vetores"]:
            self.assertEqual(list(entrada), [k for k in apoio.ORDEM_VETOR_REGISTRADO if k in entrada])

    def test_registro_de_players_cresce(self):
        """CONTRATO, seção 4.2, passo 7: "`dados/players.json`: acrescenta o item de `novos_players` com
        `origem: "rotina"` e `incluido_em: DIA`, e atualiza `atualizado_em`"; ESQUEMA, seção 13: "Entra no
        fim da lista"; G1: "os players da base continuam iguais e na mesma ordem"."""
        raiz, _, esperada, _ = self.publica_e_le()
        registro = self.le_json_de(raiz, "dados", "players.json")
        base = apoio.dados("players")
        self.assertEqual(registro["players"][:-1], base["players"])
        self.assertEqual(registro["players"][-1], apoio.players_registrados(esperada)[0])
        self.assertEqual(list(registro["players"][-1])[-2:], ["origem", "incluido_em"])
        self.assertEqual(registro["atualizado_em"], DIA)

    def test_registro_de_players_sem_player_novo_nao_muda(self):
        """CONTRATO, seção 4.2, passo 7: "`atualizado_em` recebe o dia da edição, e só muda quando a lista
        muda". Edição sem player novo: `dados/players.json` fica como estava, byte a byte."""
        raiz, t, _ = self.cenario(monta_edicao(DIA))
        caminho = os.path.join(raiz, "dados", "players.json")
        with open(caminho, "rb") as arquivo:
            antes = arquivo.read()
        self.passou(self.edicao(raiz, t))
        with open(caminho, "rb") as arquivo:
            self.assertEqual(arquivo.read(), antes)

    def test_registro_de_vetores_guarda_os_antigos_e_acrescenta_a_anulacao(self):
        """CONTRATO, seção 4.2, passo 7: "e uma entrada de anulação para cada `errata[].anula_vetor`";
        ESQUEMA, seção 12: "`anula` é o `id` do vetor desfeito; `porque` copia a `correcao` da errata e
        `url` copia a `url`"; "acrescenta no fim, sem duplicar `id`"."""
        ontem = troca_titulos(monta_edicao(ONTEM), 0)
        ontem["principais"][0]["vetores"] = copy.deepcopy(monta_edicao(ONTEM, rica=True)["principais"][0]["vetores"])
        hoje = monta_edicao(DIA, anterior=ontem, rica=True)
        hoje["principais"][0]["vetores"] = []              # hoje não repete o vetor da União Europeia
        correcao = F + "A Comissão Europeia desmentiu a suspensão em %s." % dia_mes(DIA)
        hoje["errata"] = [apoio.ordena({"edicao": ONTEM, "item": "p1", "erro": F + "A edição anterior deu o ato como certo.",
                                        "correcao": correcao, "url": "https://ec.europa.eu/exemplo/tarifa-segue",
                                        "anula_vetor": "%s_p1_ue" % ONTEM}, "errata")]
        raiz, _, _, _ = self.publica_e_le(hoje, [ontem])
        vetores = self.le_json_de(raiz, "dados", "vetores.json")["vetores"]
        self.assertEqual(vetores[0], apoio.vetores_registrados(ontem)[0])
        self.assertEqual({v["id"] for v in vetores[1:]}, {"%s_r2_google" % DIA, "%s_anula_1" % DIA})
        anulacao = [v for v in vetores if v["id"].endswith("_anula_1")][0]
        self.assertEqual(anulacao, {"id": "%s_anula_1" % DIA, "data": DIA, "anula": "%s_p1_ue" % ONTEM,
                                    "porque": correcao, "url": "https://ec.europa.eu/exemplo/tarifa-segue"})
        self.assertEqual(list(anulacao), apoio.ORDEM_ANULACAO)

    # --- mesmos bytes ---
    def test_mesma_entrada_mesmos_bytes(self):
        """CONTRATO, seção 0: "Mesma entrada, mesmos bytes". Duas raízes novas, o mesmo rascunho e o
        mesmo `INFO_AGORA`: os seis arquivos saem iguais, byte a byte."""
        retratos = []
        for _ in range(2):
            raiz, t, _ = self.cenario()
            self.passou(self.edicao(raiz, t))
            retratos.append(apoio.fotografa(raiz))
        self.assertEqual(sorted(k for k in retratos[0] if not k.endswith("/")),
                         sorted(ARQUIVOS_DA_PUBLICACAO + ["dados/veiculos.json", "dados/regua.json", "dados/indicadores.json"]))
        self.nada_mudou(retratos[0], retratos[1], "a segunda raiz, comparada com a primeira,")


class EdicaoComHistorico(CasoDePublica):
    """CONTRATO, seção 4.2, passo 4: níveis, tendências e `desde` pelas regras R13 e R14 do ESQUEMA,
    contra as edições anteriores. O rascunho do dia não traz gatilho, salvo onde o teste diz."""

    def _dominio(self, esperada, historico, ident):
        """Publica e devolve o domínio pedido, depois de conferir a edição inteira contra a esperada."""
        raiz, _, esperada, publicada = self.publica_e_le(esperada, historico)
        self.iguais(apoio.sem_marca_desligada(publicada), esperada, "edicoes/%s.json" % esperada["data"])
        return apoio.dominio_de(publicada, ident), publicada

    def test_nivel_sobe_com_gatilho_de_hoje(self):
        """ESQUEMA, seção 10, R13: "se `T` ≥ `N`: `nivel` = `T`"; R14: tendência `subindo`, `desde` igual a
        `data`; nos domínios que não mudaram, `desde` repete o da edição anterior."""
        ontem = troca_titulos(monta_edicao(ONTEM), 0)
        hoje = monta_edicao(DIA, anterior=ontem, rica=True)
        energia, publicada = self._dominio(hoje, [ontem], "energia")
        self.assertEqual((energia["nivel"], energia["tendencia"], energia["desde"]), (3, "subindo", DIA))
        alimentos = apoio.dominio_de(publicada, "alimentos")
        self.assertEqual((alimentos["nivel"], alimentos["tendencia"], alimentos["desde"]), (1, "estavel", ONTEM))
        self.assertEqual((publicada["alerta"]["nivel"], publicada["alerta"]["tendencia"]), (3, "subindo"))

    def test_nivel_mantido_com_uma_edicao_calma(self):
        """ESQUEMA, seção 10, R13: "nos outros casos: `nivel` = `N` (nível mantido)" (`S` é 1); R14:
        tendência `estavel` e `desde` repetido."""
        d3, d2, d1 = calmaria("suprimentos", "suprimentos.2")
        hoje = monta_edicao(ONTEM, anterior=d2, alerta={"suprimentos": {"nivel": 2}})
        dominio, _ = self._dominio(hoje, [d3, d2], "suprimentos")
        self.assertEqual((dominio["nivel"], dominio["tendencia"], dominio["desde"], dominio["gatilhos"]),
                         (2, "estavel", TRES_ANTES, []))

    def test_nivel_desce_depois_de_duas_edicoes_calmas(self):
        """ESQUEMA, seção 10, R13: "se `T` < `N`, `S` ≥ 2 e a edição de hoje não é cega para o domínio:
        `nivel` = `N` − 1"; R14: tendência `descendo` e `desde` igual a `data`."""
        d3, d2, d1 = calmaria("suprimentos", "suprimentos.2")
        hoje = monta_edicao(DIA, anterior=d1)
        dominio, publicada = self._dominio(hoje, [d3, d2, d1], "suprimentos")
        self.assertEqual((dominio["nivel"], dominio["tendencia"], dominio["desde"]), (1, "descendo", DIA))
        self.assertEqual((publicada["alerta"]["nivel"], publicada["alerta"]["tendencia"]), (1, "descendo"))

    def test_nivel_desce_um_de_cada_vez(self):
        """ESQUEMA, seção 10, R13: com `S` ≥ 2, "`nivel` = `N` − 1" (de 3 vai a 2, e não a 1)."""
        d3 = monta_edicao(TRES_ANTES, alerta={"conflito": {"nivel": 3, "gatilhos": [gatilho("conflito.3", "p1")]}})
        d2 = monta_edicao(ANTEONTEM, anterior=d3, alerta={"conflito": {"nivel": 3}})
        d1 = monta_edicao(ONTEM, anterior=d2, alerta={"conflito": {"nivel": 3}})
        hoje = monta_edicao(DIA, anterior=d1, alerta={"conflito": {"nivel": 2}})
        dominio, _ = self._dominio(hoje, [d3, d2, d1], "conflito")
        self.assertEqual((dominio["nivel"], dominio["tendencia"], dominio["desde"]), (2, "descendo", DIA))

    def test_nivel_nao_desce_quando_uma_das_calmas_e_falha(self):
        """ESQUEMA, seção 10, R13, conta `S`: "Pule a `falha`"; seção 0: a edição anterior é "a edição mais
        recente antes de `data` que não é `falha`"."""
        d3, _, _ = calmaria("suprimentos", "suprimentos.2")
        falha = apoio.edicao_falha(ANTEONTEM, MOTIVO, anterior=d3)
        d1 = monta_edicao(ONTEM, anterior=d3, alerta={"suprimentos": {"nivel": 2}})
        hoje = monta_edicao(DIA, anterior=d1, alerta={"suprimentos": {"nivel": 2}})
        dominio, _ = self._dominio(hoje, [d3, falha, d1], "suprimentos")
        self.assertEqual((dominio["nivel"], dominio["tendencia"], dominio["desde"]), (2, "estavel", TRES_ANTES))

    def test_nivel_nao_desce_quando_uma_das_calmas_e_cega(self):
        """ESQUEMA, seção 10, R13, conta `S`: "Das outras, conte as que não são cegas para o domínio"."""
        d3 = monta_edicao(TRES_ANTES, alerta={"energia": {"nivel": 2, "gatilhos": [gatilho("energia.2", "r4")]}})
        d2 = cega_energia(monta_edicao(ANTEONTEM, anterior=d3, alerta={"energia": {"nivel": 2}}))
        d1 = monta_edicao(ONTEM, anterior=d2, alerta={"energia": {"nivel": 2}})
        hoje = monta_edicao(DIA, anterior=d1, alerta={"energia": {"nivel": 2}})
        dominio, _ = self._dominio(hoje, [d3, d2, d1], "energia")
        self.assertEqual((dominio["nivel"], dominio["tendencia"], dominio["sem_preco"]), (2, "estavel", []))

    def test_nivel_nao_desce_quando_hoje_e_cega(self):
        """ESQUEMA, seção 10, R13: a descida pede que "a edição de hoje não é cega para o domínio"; ROTINA,
        seção 6: "sem dado de preço, não desce"."""
        d3, d2, d1 = calmaria("energia", "energia.2")
        hoje = cega_energia(monta_edicao(DIA, anterior=d1, alerta={"energia": {"nivel": 2}}))
        dominio, _ = self._dominio(hoje, [d3, d2, d1], "energia")
        self.assertEqual((dominio["nivel"], dominio["tendencia"], dominio["sem_preco"]), (2, "estavel", ["brent"]))

    def test_nivel_por_gatilho_de_preco(self):
        """ESQUEMA, seção 10, R13: `T` é "o maior nível entre os `criterio` de hoje"; o gatilho de preço,
        copiado de `P/indicadores.json`, conta."""
        ontem = troca_titulos(monta_edicao(ONTEM), 0)
        hoje = monta_edicao(DIA, anterior=ontem, rica=True,
                            alerta={"energia": {"nivel": 2, "gatilhos": [so_o_brent(DIA)]}})
        dominio, _ = self._dominio(hoje, [ontem], "energia")
        self.assertEqual((dominio["nivel"], dominio["tendencia"], [g["ref"] for g in dominio["gatilhos"]]),
                         (2, "subindo", ["brent"]))

    def test_alivio_desce_um_nivel(self):
        """ESQUEMA, seção 10, R13: "se `T` < `N` e há gatilho de alívio válido (R13e): `nivel` = `N` − 1";
        R13e: "Gatilho de alívio não conta em `T`"."""
        ontem = troca_titulos(monta_edicao(ONTEM, alerta={"energia": {"nivel": 4, "gatilhos": [gatilho("energia.4", "p1")]}}), 0)
        alivio = gatilho("energia.4", "p1", F + "Acabou em %s: a rota fictícia foi reaberta." % dia_mes(DIA), alivio=True)
        hoje = monta_edicao(DIA, anterior=ontem, alerta={"energia": {"nivel": 3, "gatilhos": [alivio]}})
        dominio, publicada = self._dominio(hoje, [ontem], "energia")
        self.assertEqual((dominio["nivel"], dominio["tendencia"], dominio["desde"]), (3, "descendo", DIA))
        self.assertIs(dominio["gatilhos"][0].get("alivio"), True)
        self.assertEqual(publicada["alerta"]["nivel"], 3)

    def test_estado_que_continua_segura_o_nivel(self):
        """ESQUEMA, seção 10, R13b, "Estado que continua": gatilho de nível 4 com o mesmo `criterio` da
        origem "aceita principal ou radar"; R13: "se `T` ≥ `N`: `nivel` = `T`"; regra T3: o item que
        sustenta gatilho que não é novo precisa de 1 fonte com data conferida."""
        ontem = troca_titulos(monta_edicao(ONTEM, alerta={"energia": {"nivel": 4, "gatilhos": [gatilho("energia.4", "p1")]}}), 0)
        segue = gatilho("energia.4", "r4", F + "Segue em %s: a rota fictícia continua fechada." % dia_mes(DIA))
        hoje = monta_edicao(DIA, anterior=ontem, alerta={"energia": {"nivel": 4, "gatilhos": [segue]}})
        dominio, _ = self._dominio(hoje, [ontem], "energia")
        self.assertEqual((dominio["nivel"], dominio["tendencia"], dominio["desde"]), (4, "estavel", ONTEM))

    def test_edicao_com_historico_passa_no_valida(self):
        """CONTRATO, seção 5: depois do `publica.py edicao`, o `valida.py --edicao` do arquivo publicado
        (regras R e H, contra as outras edições) dá código 0. O histórico é o da descida por calmaria."""
        d3, d2, d1 = calmaria("suprimentos", "suprimentos.2")
        raiz, _, _, _ = self.publica_e_le(monta_edicao(DIA, anterior=d1), [d3, d2, d1])
        self.passou(self.valida("--edicao", apoio.caminho_da_edicao(raiz, DIA), raiz=raiz))


# =============================================================================================
# (b) edicao: as regras da pasta de trabalho (T1 a T5) e a validação
# =============================================================================================

class RegrasDaPastaDeTrabalho(CasoDePublica):
    """ESQUEMA, seção 10, "Regras da pasta de trabalho"; CONTRATO, seção 4.2, passos 5 e 6."""

    def recusa(self, raiz, t, *regras, caminho=None):
        """Roda `edicao`, espera a regra e confere que nada foi gravado na raiz."""
        t.grava()
        antes = apoio.fotografa(raiz, rigor=True)
        res = self.edicao(raiz, t)
        self.acusa(res, *regras, caminho=caminho)
        self.nada_mudou(antes, apoio.fotografa(raiz, rigor=True), "a raiz")
        return res

    def aceita(self, raiz, t, *regras):
        t.grava()
        res = self.edicao(raiz, t)
        self.nao_acusa(res, *regras)
        return res

    def fonte(self, t, principal, indice):
        return t.rascunho["principais"][principal]["fontes"][indice]

    # --- T1 ---
    def test_t1_acusa_url_de_fonte_que_a_maquina_nao_viu(self):
        """ESQUEMA, seção 10, T1: "Toda URL do rascunho está em `coleta.json` ou em `urls.txt`"."""
        raiz, t, _ = self.cenario()
        t.esquece(self.fonte(t, 0, 0)["url"])              # a página da agência, aberta pelo agente
        self.recusa(raiz, t, "T1")

    def test_t1_acusa_url_do_player_novo_que_a_maquina_nao_viu(self):
        """ESQUEMA, seção 10, T1: "**Toda** URL do rascunho" (aqui, uma das `dna_fontes` do player novo)."""
        raiz, t, _ = self.cenario()
        t.esquece(t.rascunho["novos_players"][0]["dna_fontes"]["moderacao"])
        self.recusa(raiz, t, "T1")

    def test_t1_acusa_url_que_so_esta_em_linha_de_comentario(self):
        """CONTRATO, seção 0, `urls.txt`: "uma URL por linha; linha com `#` é comentário"."""
        raiz, t, _ = self.cenario()
        url = self.fonte(t, 0, 0)["url"]
        t.esquece(url)
        t.urls.append("# " + url)
        self.recusa(raiz, t, "T1")

    def test_t1_aceita_endereco_que_so_difere_na_forma(self):
        """ESQUEMA, seção 10, T1: "A comparação usa o endereço limpo (seção 0)"; seção 0: "esquema e nome
        do site em minúsculas, `http` igual a `https`, sem `www.`, sem `#…`, sem parâmetros `utm_`, sem
        barra no fim". Em cada caso, `urls.txt` e `conferencia.json` trazem uma forma e o rascunho, outra."""
        limpa = "https://reuters.com/exemplo/terminal-para"
        formas = {
            "com www.": "https://www.reuters.com/exemplo/terminal-para",
            "com http": "http://reuters.com/exemplo/terminal-para",
            "site em maiúsculas": "https://REUTERS.COM/exemplo/terminal-para",
            "barra no fim": "https://reuters.com/exemplo/terminal-para/",
            "parâmetros utm_": "https://reuters.com/exemplo/terminal-para?utm_source=boletim&utm_medium=email",
        }
        for nome, vista in formas.items():
            with self.subTest(forma=nome):
                raiz, t, _ = self.cenario()
                self.assertEqual(self.fonte(t, 0, 0)["url"], limpa)
                t.esquece(limpa)
                t.abre(vista, publicado_em=DIA)
                self.aceita(raiz, t, "T1", "T3", "T4")

    def test_t1_aceita_rascunho_com_ancora_no_endereco(self):
        """ESQUEMA, seção 0, endereço limpo: "sem `#…`" ("as ferramentas limpam os dois lados do mesmo
        jeito"). O rascunho cita a página com âncora; a máquina viu a página sem ela."""
        raiz, t, _ = self.cenario()
        self.fonte(t, 0, 0)["url"] += "#trecho"
        self.aceita(raiz, t, "T1", "T3", "T4")

    # --- T2 ---
    def test_t2_acusa_data_diferente_do_dia(self):
        """ESQUEMA, seção 10, T2: "`data` do rascunho é igual ao dia (`--dia`)"."""
        raiz, t, _ = self.cenario()
        t.rascunho["data"] = ONTEM
        self.recusa(raiz, t, "T2")

    def test_t2_acusa_rascunho_com_estado_falha(self):
        """ESQUEMA, seção 10, T2: "O rascunho não traz `exemplo` nem `estado: falha`"."""
        raiz, t, _ = self.cenario()
        t.rascunho["estado"] = "falha"
        self.recusa(raiz, t, "T2")

    def test_t2_acusa_rascunho_com_exemplo(self):
        """ESQUEMA, seção 10, "Qual código sai": "Rascunho com `exemplo`: T2, e também R18 em cada título sem a
        marca `[EXEMPLO]`". Os títulos do rascunho não têm a marca: saem os dois códigos."""
        raiz, t, _ = self.cenario()
        t.rascunho = {"data": t.rascunho["data"], "estado": t.rascunho["estado"], "exemplo": True,
                      **{k: v for k, v in t.rascunho.items() if k not in ("data", "estado")}}
        res = self.recusa(raiz, t, "T2")
        self.acusa(res, "R18")

    def test_t2_aceita_rascunho_do_dia(self):
        """ESQUEMA, seção 10, T2: "`data` do rascunho é igual ao dia (`--dia`). O rascunho não traz
        `exemplo` nem `estado: falha`" (o caso certo: data do dia, estado `completa`, sem `exemplo`)."""
        raiz, t, _ = self.cenario()
        self.assertEqual((t.rascunho["data"], t.rascunho["estado"], "exemplo" in t.rascunho), (DIA, "completa", False))
        self.aceita(raiz, t, "T2")

    # --- T3 ---
    def test_t3_acusa_data_diferente_da_data_da_pagina(self):
        """ESQUEMA, seção 10, T3: "`publicado_em` é igual a essa data, com 1 dia de folga". O caso é o do
        exemplo do CONTRATO, seção 4.2, passo 6: `ERRO T3 principais[0].fontes[2].publicado_em: é
        2026-11-20, a página diz 2025-11-20`."""
        raiz, t, _ = self.cenario()
        t.pagina(self.fonte(t, 0, 0)["url"])["publicado_em"] = "2025-11-20"
        self.recusa(raiz, t, "T3", caminho="principais[0].fontes[0].publicado_em")

    def test_t3_acusa_data_diferente_da_data_do_feed(self):
        """ESQUEMA, seção 10, T3: fonte cuja `url` está em `coleta.json` tem a "data do feed"; `publicado_em`
        "é igual a essa data, com 1 dia de folga" (aqui a diferença é de 2 dias)."""
        raiz, t, _ = self.cenario()
        t.manchete(self.fonte(t, 0, 1)["url"])["publicado_em"] = ANTEONTEM + "T14:02:00Z"
        self.recusa(raiz, t, "T3", caminho="principais[0].fontes[1].publicado_em")

    def test_t3_aceita_um_dia_de_folga_para_cada_lado(self):
        """ESQUEMA, seção 10, T3: "com 1 dia de folga"."""
        raiz, t, _ = self.cenario()
        t.manchete(self.fonte(t, 0, 1)["url"])["publicado_em"] = ONTEM + "T14:02:00Z"      # o rascunho diz DIA
        self.fonte(t, 0, 2)["publicado_em"] = ONTEM                                        # o feed diz DIA
        self.aceita(raiz, t, "T3")

    def test_t3_acusa_fonte_de_pagina_que_nao_existe(self):
        """ESQUEMA, seção 10, T3: "URL com estado `erro` em `conferencia.json` não vale como fonte: a
        página não existe"."""
        raiz, t, _ = self.cenario()
        t.pagina(self.fonte(t, 0, 0)["url"]).update(estado="erro", publicado_em=None)
        self.recusa(raiz, t, "T3")

    def test_t3_acusa_principal_com_uma_fonte_de_data_conferida(self):
        """ESQUEMA, seção 10, T3: "Cada principal tem 2 fontes ou mais com data conferida dentro da janela
        da R09. […] Fonte `primaria` não entra nessas contas". Em p2 sobram uma fonte comum de data
        conferida e a primária (que tem data conferida, mas não conta)."""
        raiz, t, _ = self.cenario()
        t.vira_pagina(self.fonte(t, 1, 0)["url"], "bloqueada")         # bloomberg
        t.vira_pagina(self.fonte(t, 1, 2)["url"], "ok", None)          # wired: página sem data
        self.assertEqual(t.pagina(self.fonte(t, 1, 3)["url"])["publicado_em"], DIA)
        self.recusa(raiz, t, "T3")

    def test_t3_aceita_principal_com_duas_fontes_de_data_conferida(self):
        """ESQUEMA, seção 10, T3: "Cada principal tem 2 fontes ou mais com data conferida"; CONTRATO, seção
        1.1: página `bloqueada`: "a fonte vale, sem data conferida"."""
        raiz, t, _ = self.cenario()
        t.vira_pagina(self.fonte(t, 1, 0)["url"], "bloqueada")
        self.aceita(raiz, t, "T3")

    def test_t3_acusa_item_de_gatilho_sem_fonte_de_data_conferida(self):
        """ESQUEMA, seção 10, T3: "Item que sustenta gatilho tem 1 ou mais" (r4 sustenta o gatilho de
        suprimentos)."""
        raiz, t, _ = self.cenario()
        for fonte in t.rascunho["radar"][3]["fontes"]:
            t.vira_pagina(fonte["url"], "bloqueada")
        self.recusa(raiz, t, "T3")

    def test_t3_aceita_item_de_gatilho_com_uma_fonte_de_data_conferida(self):
        """ESQUEMA, seção 10, T3: "Item que sustenta gatilho tem 1 ou mais"."""
        raiz, t, _ = self.cenario()
        t.vira_pagina(t.rascunho["radar"][3]["fontes"][0]["url"], "bloqueada")
        self.aceita(raiz, t, "T3")

    def test_t3_acusa_gatilho_novo_de_nivel_3_com_duas_fontes_de_data_conferida(self):
        """ESQUEMA, seção 10, T3: "se o gatilho é novo e de nível 3 ou mais, tem 3" (p1 sustenta os
        gatilhos novos de nível 3 de energia e de conflito)."""
        raiz, t, _ = self.cenario()
        t.vira_pagina(self.fonte(t, 0, 0)["url"], "bloqueada")         # reuters
        t.vira_pagina(self.fonte(t, 0, 3)["url"], "bloqueada")         # xinhua
        self.recusa(raiz, t, "T3")

    def test_t3_aceita_gatilho_novo_de_nivel_3_com_tres_fontes_de_data_conferida(self):
        """ESQUEMA, seção 10, T3: "se o gatilho é novo e de nível 3 ou mais, tem 3" (o mínimo exato)."""
        raiz, t, _ = self.cenario()
        t.vira_pagina(self.fonte(t, 0, 0)["url"], "bloqueada")
        self.aceita(raiz, t, "T3")

    def _sem_rede(self):
        """Máquina sem rede: nenhum feed respondeu e nenhuma página veio `ok`. A edição esperada sai em
        modo `busca`, com o gatilho de preço e o de nível 2, sem gatilho de nível 3."""
        esperada = monta_edicao(DIA, rica=True, alerta={
            "energia": {"nivel": 2, "gatilhos": [so_o_brent(DIA)]},
            "suprimentos": {"nivel": 2, "gatilhos": [apoio.dominio_de(monta_edicao(DIA, rica=True), "suprimentos")["gatilhos"][0]]}})
        esperada["bastidores"]["modo"] = "busca"
        raiz, t, esperada = self.cenario(esperada, feeds=False)
        for pagina in t.paginas:
            pagina.update(estado="bloqueada", publicado_em=None)
        return raiz, t, esperada

    def test_t3_maquina_sem_rede_aceita_modo_busca_sem_gatilho_de_nivel_3(self):
        """ESQUEMA, seção 10, T3, "Máquina sem rede": "Se nenhum feed respondeu (`coleta.json` com
        `feeds_ok` 0, ou sem o arquivo) e nenhuma página de `conferencia.json` veio `ok`, não há como
        conferir data: as contas acima não valem. Em troca, `bastidores.modo` tem de ser `busca`, e
        nenhum item sustenta gatilho de nível 3 ou mais". Vale com `coleta.json` zerado e sem o arquivo."""
        for sem_arquivo in (False, True):
            with self.subTest(sem_coleta_json=sem_arquivo):
                raiz, t, esperada = self._sem_rede()
                t.sem_coleta = sem_arquivo
                self.assertEqual(t.coleta()["resumo"]["feeds_ok"], 0)
                self.aceita(raiz, t, "T3")
                publicada = self.publicada(raiz)
                self.assertEqual((publicada["bastidores"]["modo"], publicada["alerta"]["nivel"]), ("busca", 2))

    def test_t3_maquina_sem_rede_acusa_modo_feeds(self):
        """ESQUEMA, seção 10, T3, "Máquina sem rede": "`bastidores.modo` tem de ser `busca`"."""
        raiz, t, _ = self._sem_rede()
        t.rascunho["bastidores"]["modo"] = "feeds"
        self.recusa(raiz, t, "T3")

    def test_t3_maquina_sem_rede_acusa_gatilho_de_nivel_3(self):
        """ESQUEMA, seção 10, T3, "Máquina sem rede": "nenhum item sustenta gatilho de nível 3 ou mais"."""
        raiz, t, _ = self._sem_rede()
        t.rascunho["alerta"]["dominios"][4]["gatilhos"] = [gatilho("conflito.3", "p1")]
        self.recusa(raiz, t, "T3")

    # --- T4 ---
    def _troca_endereco(self, t, novo, na_coleta=False):
        """Troca o endereço da fonte da agência (p1, fonte 0), no rascunho e no que a máquina viu."""
        fonte = self.fonte(t, 0, 0)
        t.esquece(fonte["url"])
        fonte["url"] = novo
        t.abre(novo, publicado_em=DIA)

    def test_t4_acusa_endereco_fora_dos_sites_do_veiculo(self):
        """ESQUEMA, seção 10, T4: "Em fonte de veículo do mapa, o site da `url` bate com um dos `sites` do
        veículo no mapa"."""
        raiz, t, _ = self.cenario()
        self._troca_endereco(t, "https://exemplo.invalid/reuters/terminal-para")
        self.recusa(raiz, t, "T4")

    def test_t4_acusa_site_que_so_comeca_com_o_nome_do_veiculo(self):
        """ESQUEMA, seção 0: um site bate com um nome "quando é igual a ele ou termina em ponto mais ele"
        (`reuters.com.exemplo.invalid` não bate com `reuters.com`)."""
        raiz, t, _ = self.cenario()
        self._troca_endereco(t, "https://reuters.com.exemplo.invalid/terminal-para")
        self.recusa(raiz, t, "T4")

    def test_t4_aceita_subdominio_do_site_do_veiculo(self):
        """ESQUEMA, seção 0: um site bate com um nome quando "termina em ponto mais ele"."""
        raiz, t, _ = self.cenario()
        self._troca_endereco(t, "https://internacional.reuters.com/exemplo/terminal-para")
        self.aceita(raiz, t, "T4")

    def test_t4_acusa_endereco_da_coleta_fora_dos_sites_do_veiculo(self):
        """ESQUEMA, seção 10, T4: "Estar em `coleta.json` com esse veículo não basta: um feed comprometido, ou
        de agregador, pode pôr na mesa o endereço de outro site com o nome do veículo". A página está na
        coleta com a Fox News, e o site dela não é o da Fox News. (Até a fase 2b, este teste dizia o contrário,
        `test_t4_aceita_endereco_que_esta_na_coleta_com_o_veiculo`: a T4 aceitava a URL só por estar na coleta.)"""
        raiz, t, _ = self.cenario()
        antiga, nova = self.fonte(t, 0, 2)["url"], "https://exemplo.invalid/fox_news/europa-dependente"
        t.manchete(antiga)["url"] = nova
        self.fonte(t, 0, 2)["url"] = nova
        t.rascunho["principais"][0]["ataques"][1]["url"] = nova        # o ataque da Fox News usa a mesma página
        self.recusa(raiz, t, "T4", caminho="principais[0].fontes[2].veiculo")

    def test_t4_acusa_endereco_que_esta_na_coleta_com_outro_veiculo(self):
        """ESQUEMA, seção 10, T4: em fonte de veículo do mapa, "o site da `url` bate com um dos `sites` do
        veículo no mapa". Aqui a coleta atribui a página a outro veículo, e o site não bate com os do
        veículo declarado."""
        raiz, t, _ = self.cenario()
        antiga, nova = self.fonte(t, 0, 2)["url"], "https://exemplo.invalid/fox_news/europa-dependente"
        t.manchete(antiga).update(url=nova, veiculo="new_york_post")
        self.fonte(t, 0, 2)["url"] = nova
        t.rascunho["principais"][0]["ataques"][1]["url"] = nova
        self.recusa(raiz, t, "T4")

    # --- T5 ---
    def test_t5_acusa_omite_de_pagina_que_nao_foi_aberta(self):
        """ESQUEMA, seção 10, T5: "`omite` só em ataque cuja `url` está em `urls.txt`". A página continua
        na coleta (a regra T1 passa), mas sai de `urls.txt`."""
        raiz, t, _ = self.cenario()
        ataque = t.rascunho["principais"][0]["ataques"][0]
        self.assertIn("omite", ataque)
        t.urls.remove(ataque["url"])
        self.recusa(raiz, t, "T5")

    def test_t5_aceita_ataque_sem_omite_de_pagina_que_nao_foi_aberta(self):
        """ESQUEMA, seção 10, T5: a exigência é só para ataque com `omite`. O ataque da Fox News na p1 não
        tem `omite`, e a página dele só está na coleta."""
        raiz, t, _ = self.cenario()
        ataque = t.rascunho["principais"][0]["ataques"][1]
        self.assertNotIn("omite", ataque)
        self.assertNotIn(ataque["url"], t.urls)
        self.aceita(raiz, t, "T5")

    # --- as outras regras também valem ---
    def test_edicao_confere_as_regras_r(self):
        """CONTRATO, seção 4.2, passo 5: "Valida em memória, com todas as regras: R (inclusive as
        **(dia)**), H e T"; passo 6: "Com erro: imprime no formato do `valida.py`, **não grava nada**,
        código 1"."""
        raiz, t, _ = self.cenario()
        t.rascunho["principais"][0]["realmente"] = F + "Dossiê curto demais."
        self.recusa(raiz, t, "R23")

    def test_edicao_confere_as_regras_do_dia(self):
        """CONTRATO, seção 4.2, passo 5: "R (inclusive as **(dia)**)". A regra R03 é do dia: veículo de
        lado incerto não atira em principal."""
        raiz, t, _ = self.cenario()
        url = "https://techcrunch.com/exemplo/lei-de-registro"
        ataque = t.rascunho["principais"][1]["ataques"][0]
        ataque.update(veiculo="techcrunch", url=url)
        t.rascunho["principais"][1]["fontes"].append(apoio.ordena({"veiculo": "techcrunch", "titulo": "Registry bill passes",
                                                                   "url": url, "publicado_em": DIA}, "fonte"))
        t.abre(url, publicado_em=DIA)
        self.recusa(raiz, t, "R03")

    def test_edicao_confere_as_regras_h(self):
        """CONTRATO, seção 4.2, passo 5: "R […], H e T". A regra H2 pede que `continuacao_de` aponte para
        edição e item que existem; a raiz não tem edição anterior."""
        raiz, t, _ = self.cenario()
        poe(t.rascunho["principais"][1], "principal", continuacao_de=ONTEM + "/p2")
        self.recusa(raiz, t, "H2")


# =============================================================================================
# (b) edicao: tudo ou nada, --simula, --corta e dia já publicado
# =============================================================================================

class TudoOuNada(CasoDePublica):
    """CONTRATO, seção 0, "Comportamento em falha", e seção 4.2, passos 1, 3 e 6."""

    def test_erro_nao_muda_arquivo_nenhum(self):
        """CONTRATO, seção 0: "`publica.py` grava tudo ou nada: com erro, nenhum arquivo muda"; seção 4.2,
        passo 6: "**não grava nada**, código 1". A raiz já tem uma edição anterior publicada; o retrato
        dela e o da pasta de trabalho são os mesmos antes e depois."""
        ontem = troca_titulos(monta_edicao(ONTEM), 0)
        raiz, t, _ = self.cenario(monta_edicao(DIA, anterior=ontem, rica=True), [ontem])
        t.rascunho["principais"][0]["vigiar"][0] = "O Reino de Amostra responde com ataque militar?"       # R21
        t.rascunho["radar"][5]["placar"][0]["forca"] = 3                                                    # R10
        t.grava()
        antes, antes_trabalho = apoio.fotografa(raiz, rigor=True), apoio.fotografa(t.pasta, rigor=True)
        res = self.edicao(raiz, t)
        self.acusa(res, "R21")
        self.acusa(res, "R10")
        self.nada_mudou(antes, apoio.fotografa(raiz, rigor=True), "a raiz")
        self.nada_mudou(antes_trabalho, apoio.fotografa(t.pasta, rigor=True), "a pasta de trabalho")

    def test_sem_rascunho_da_falha(self):
        """CONTRATO, seção 4.2, passo 1: "Lê `P/rascunho.json`. Não existe: `FALHA`, código 1"."""
        raiz, t, _ = self.cenario()
        os.remove(t.arquivo("rascunho.json"))
        antes = apoio.fotografa(raiz, rigor=True)
        self.falhou(self.edicao(raiz, t))
        self.nada_mudou(antes, apoio.fotografa(raiz, rigor=True), "a raiz")

    def test_rascunho_que_nao_e_json_diz_linha_e_coluna(self):
        """CONTRATO, seção 4.2, passo 1: "Não é JSON: `FALHA rascunho.json: linha L, coluna C: mensagem`,
        código 1"."""
        raiz, t, _ = self.cenario()
        apoio.grava_texto(t.arquivo("rascunho.json"), '{\n  "data": "%s",\n  "estado": "completa" "resumo"\n}\n' % DIA)
        res = self.edicao(raiz, t)
        self.falhou(res)
        self.assertRegex(res.ultima, r"^FALHA rascunho\.json: linha \d+, coluna \d+: \S", res.relato())

    def test_erro_de_uso_nao_grava(self):
        """CONTRATO, seção 0, "Erro de uso": "Opção errada […]: uma linha `FALHA uso: …` na saída padrão e
        código 2. Nada é gravado"."""
        raiz, t, _ = self.cenario()
        antes = apoio.fotografa(raiz, rigor=True)
        self.erro_de_uso(self.edicao(raiz, t, "--nao-existe"))
        self.erro_de_uso(self.publica("publique", raiz=raiz, trabalho=t.pasta))
        self.erro_de_uso(self.edicao(raiz, t, agora="ontem à tarde"))
        self.nada_mudou(antes, apoio.fotografa(raiz, rigor=True), "a raiz")

    # --- --simula ---
    def test_simula_nao_grava(self):
        """CONTRATO, seção 4.2: "`--simula` faz os passos 1 a 6, lista o que o passo 7 gravaria e imprime
        os níveis calculados. Não grava"."""
        raiz, t, _ = self.cenario()
        antes, antes_trabalho = apoio.fotografa(raiz, rigor=True), apoio.fotografa(t.pasta, rigor=True)
        res = self.edicao(raiz, t, "--simula")
        self.passou(res)
        self.nada_mudou(antes, apoio.fotografa(raiz, rigor=True), "a raiz")
        self.nada_mudou(antes_trabalho, apoio.fotografa(t.pasta, rigor=True), "a pasta de trabalho")
        for nome in ("%s.json" % DIA, "%s.md" % DIA, "indice.json", "feed.xml"):
            self.assertIn(nome, res.saida, "a simulação deveria listar o que gravaria." + res.relato())

    def test_simula_com_erro_da_codigo_1(self):
        """CONTRATO, seção 4.2: "`--simula` faz os passos 1 a 6" (o passo 6: com erro, código 1)."""
        raiz, t, _ = self.cenario()
        t.rascunho["principais"][0]["realmente"] = F + "Dossiê curto demais."
        t.grava()
        antes = apoio.fotografa(raiz, rigor=True)
        self.acusa(self.edicao(raiz, t, "--simula"), "R23")
        self.nada_mudou(antes, apoio.fotografa(raiz, rigor=True), "a raiz")

    # --- dia já publicado ---
    def _publicada_e_commitada(self):
        raiz, t, esperada = self.cenario(com_git=True)
        self.passou(self.edicao(raiz, t))
        apoio.commita(raiz, "edição %s" % DIA)
        return raiz, t, esperada

    def test_dia_ja_publicado_com_o_mesmo_rascunho(self):
        """CONTRATO, seção 4.2, passo 3: ""Já publicado" quer dizer: `edicoes/DIA.json` está no commit
        `HEAD` […] com estado `completa` ou `reduzida`. Essa edição é final: com rascunho que dá a mesma
        edição (sem contar `gerada_em`), termina em `OK edição DIA já publicada: nada mudou`, código 0"."""
        raiz, t, _ = self._publicada_e_commitada()
        antes = apoio.fotografa(raiz)
        res = self.edicao(raiz, t, agora=agora_de(DIA, "22:30:00"))
        self.passou(res)
        self.assertEqual(res.ultima, "OK edição %s já publicada: nada mudou" % DIA)
        self.nada_mudou(antes, apoio.fotografa(raiz), "a raiz")

    def test_dia_ja_publicado_com_rascunho_diferente(self):
        """CONTRATO, seção 4.2, passo 3: "com rascunho diferente, `FALHA`, código 1"."""
        raiz, t, _ = self._publicada_e_commitada()
        t.rascunho["resumo"] = "Edição fictícia refeita depois de publicada."
        t.grava()
        antes = apoio.fotografa(raiz)
        self.falhou(self.edicao(raiz, t, agora=agora_de(DIA, "22:30:00")))
        self.nada_mudou(antes, apoio.fotografa(raiz), "a raiz")

    def test_arquivo_do_dia_sem_commit_e_gravado_por_cima(self):
        """CONTRATO, seção 4.2, passo 3: "Arquivo do dia que só está no disco, sem commit, é desta
        execução: `edicao` e `falha` gravam por cima"; passo 7, "Republicação na mesma execução": o que
        o dia já tinha gravado nos dois registros "é tirado e refeito a partir do rascunho novo"."""
        raiz, t, esperada = self.cenario(com_git=True)
        self.passou(self.edicao(raiz, t))
        t.rascunho["resumo"] = "Edição fictícia refeita na mesma execução."
        t.rascunho["principais"][0]["vetores"] = []                    # sai o vetor da União Europeia
        t.rascunho["novos_players"][0]["nota"] = F + "Nota refeita."
        t.grava()
        mais_tarde = agora_de(DIA, "21:40:00")
        self.passou(self.edicao(raiz, t, agora=mais_tarde))
        publicada = self.publicada(raiz)
        self.assertEqual((publicada["resumo"], publicada["gerada_em"]),
                         ("Edição fictícia refeita na mesma execução.", mais_tarde))
        vetores = self.le_json_de(raiz, "dados", "vetores.json")["vetores"]
        self.assertEqual([v["id"] for v in vetores], ["%s_r2_google" % DIA])
        players = self.le_json_de(raiz, "dados", "players.json")["players"]
        self.assertEqual(len(players), 31)
        self.assertEqual((players[-1]["id"], players[-1]["nota"]), ("republica_exemplo", F + "Nota refeita."))

    def test_republicacao_sem_o_player_novo_tira_o_registro(self):
        """CONTRATO, seção 4.2, passo 7, "Republicação na mesma execução": "player com `incluido_em` igual
        a DIA" é tirado e refeito a partir do rascunho novo (que não traz mais player novo)."""
        raiz, t, _ = self.cenario(com_git=True)
        self.passou(self.edicao(raiz, t))
        t.rascunho["novos_players"] = []
        for item in apoio.itens(t.rascunho):
            for ataque in apoio.ataques_de(item):
                if ataque["alvo"] == "republica_exemplo":
                    poe(ataque, "ataque", alvo="outro", alvo_nome=apoio.ALVO_FORA_DA_REGUA)
        t.grava()
        self.passou(self.edicao(raiz, t, agora=agora_de(DIA, "21:40:00")))
        self.assertEqual(self.le_json_de(raiz, "dados", "players.json")["players"], apoio.dados("players")["players"])
        self.assertEqual(self.publicada(raiz)["novos_players"], [])

    def test_republicacao_igual_da_os_mesmos_bytes(self):
        """CONTRATO, seção 0: "Mesma entrada, mesmos bytes"; seção 4.2, passo 7, "Republicação na mesma
        execução": os registros não duplicam o que o dia já tinha gravado."""
        raiz, t, _ = self.cenario(com_git=True)
        self.passou(self.edicao(raiz, t))
        antes = apoio.fotografa(raiz)
        self.passou(self.edicao(raiz, t))
        self.nada_mudou(antes, apoio.fotografa(raiz), "a raiz")

    def test_sem_git_vale_o_disco(self):
        """CONTRATO, seção 4.2, passo 3: "Sem git na raiz, o disco decide o que já foi publicado: a edição
        `completa` ou `reduzida` que está em `edicoes/DIA.json` é final, como se estivesse no commit"."""
        raiz, t, _ = self.cenario()
        self.passou(self.edicao(raiz, t))
        antes = apoio.fotografa(raiz)
        igual = self.edicao(raiz, t, agora=agora_de(DIA, "22:30:00"))
        self.passou(igual)
        self.assertEqual(igual.ultima, "OK edição %s já publicada: nada mudou" % DIA)
        t.rascunho["resumo"] = "Edição fictícia refeita depois de publicada."
        t.grava()
        self.falhou(self.edicao(raiz, t, agora=agora_de(DIA, "22:30:00")))
        self.nada_mudou(antes, apoio.fotografa(raiz), "a raiz")

    def test_falha_do_dia_e_trocada_pela_edicao(self):
        """CONTRATO, seção 4.2, passo 3: "Edição do dia com estado `falha` é trocada pela nova"; ESQUEMA,
        seção 10, G3: "a de `estado: falha` pode ser trocada por uma edição de verdade". A falha já
        está no commit e em `origin/main`."""
        raiz, t, esperada = self.cenario(com_git=True)
        self.passou(self.publica("falha", "--motivo", MOTIVO, "--dia", DIA, raiz=raiz, trabalho=t.pasta,
                                 agora=agora_de(DIA, "20:50:00")))
        self.assertEqual(self.publicada(raiz)["estado"], "falha")
        apoio.commita(raiz, "falha %s" % DIA, origin=True)
        self.passou(self.edicao(raiz, t))
        self.iguais(apoio.sem_marca_desligada(self.publicada(raiz)), esperada, "edicoes/%s.json" % DIA)
        self.assertEqual([e["estado"] for e in self.le_json_de(raiz, "edicoes", "indice.json")["edicoes"]], ["completa"])
        self.passou(self.valida("--tudo", "--base", "origin/main", "--dia", DIA, raiz=raiz))


class Corta(CasoDePublica):
    """CONTRATO, seção 4.2, "`--corta ID[,ID]`"."""

    def corta(self, ids, esperada=None, defeito=None):
        """Publica com `--corta`. Devolve (resultado, edição publicada, rascunho regravado)."""
        raiz, t, _ = self.cenario(esperada)
        if defeito:
            defeito(t.rascunho)
            t.grava()
        res = self.edicao(raiz, t, "--corta", ids)
        self.passou(res)
        return res, self.publicada(raiz), self.le_json_de(t.pasta, "rascunho.json")

    def test_corta_item_do_radar_renumera_e_acerta_o_gatilho(self):
        """CONTRATO, seção 4.2, `--corta`: "Tira do rascunho os itens citados e conserta o que dependia
        deles: renumera os ids em ordem (`p1..pN`, `r1..rN`); acerta os `ref` dos gatilhos; […] troca
        `estado` para `reduzida` se a contagem da `completa` deixou de fechar". Sem o r3, o radar fica
        com 5 itens e o antigo r4 (que sustenta o gatilho de suprimentos) vira r3."""
        base = monta_edicao(DIA, rica=True)
        titulos = [r["titulo"] for r in base["radar"]]
        _, publicada, rascunho = self.corta("r3")
        for objeto in (publicada, rascunho):
            self.assertEqual([r["id"] for r in objeto["radar"]], ["r1", "r2", "r3", "r4", "r5"])
            self.assertEqual([r["titulo"] for r in objeto["radar"]], titulos[:2] + titulos[3:])
            self.assertEqual(objeto["estado"], "reduzida")
        self.assertEqual(apoio.dominio_de(publicada, "suprimentos")["gatilhos"][0]["ref"], "r3")
        self.assertEqual(rascunho["alerta"]["dominios"][3]["gatilhos"][0]["ref"], "r3")
        self.assertEqual(publicada["bastidores"]["veiculos_consultados"], 17)

    def test_corta_tira_o_gatilho_e_o_partido_que_ficou_sem_linha(self):
        """CONTRATO, seção 4.2, `--corta`: "tira o gatilho que apontava para item cortado; tira de
        `placar_do_dia` o partido que ficou sem linha em placar nenhum". O r4 sustentava o gatilho de
        suprimentos e tinha a única linha de placar do Centrão."""
        _, publicada, rascunho = self.corta("r4")
        suprimentos = apoio.dominio_de(publicada, "suprimentos")
        self.assertEqual((suprimentos["gatilhos"], suprimentos["nivel"]), ([], 1))
        self.assertEqual(rascunho["alerta"]["dominios"][3]["gatilhos"], [])
        self.assertNotIn("centrao", [p["partido"] for p in publicada["placar_do_dia"]])
        self.assertNotIn("centrao", [p["partido"] for p in rascunho["placar_do_dia"]])
        self.assertEqual(len(publicada["placar_do_dia"]), 6)
        self.assertEqual(publicada["alerta"]["nivel"], 3)

    def test_corta_varios_ids_com_virgula(self):
        """CONTRATO, seção 4.2, `--corta`: "vários ids, com vírgula: `--corta r3,r7`"."""
        base = monta_edicao(DIA, rica=True)
        _, publicada, _ = self.corta("r2,r5")
        self.assertEqual([r["id"] for r in publicada["radar"]], ["r1", "r2", "r3", "r4"])
        self.assertEqual([r["titulo"] for r in publicada["radar"]],
                         [base["radar"][i]["titulo"] for i in (0, 2, 3, 5)])
        self.assertEqual(apoio.dominio_de(publicada, "suprimentos")["gatilhos"][0]["ref"], "r3")
        self.assertEqual(publicada["estado"], "reduzida")
        vetores = [v["player"] for item in apoio.itens(publicada) for v in item["vetores"]]
        self.assertEqual(vetores, ["ue"])

    def test_corta_principal_renumera_as_principais(self):
        """CONTRATO, seção 4.2, `--corta`: "renumera os ids em ordem (`p1..pN`, `r1..rN`)"; com 2
        principais, a `completa` deixa de fechar. A Bancada do Talento só tinha linha de placar na p2."""
        base = monta_edicao(DIA, rica=True)
        _, publicada, _ = self.corta("p2")
        self.assertEqual([p["id"] for p in publicada["principais"]], ["p1", "p2"])
        self.assertEqual([p["titulo"] for p in publicada["principais"]],
                         [base["principais"][0]["titulo"], base["principais"][2]["titulo"]])
        self.assertEqual(publicada["estado"], "reduzida")
        self.assertNotIn("bancada_talento", [p["partido"] for p in publicada["placar_do_dia"]])

    def _com_sete_no_radar(self):
        """A edição "rica" com um sétimo item de radar, de geopolítica (cópia do r5)."""
        e = monta_edicao(DIA, rica=True)
        novo = copy.deepcopy(e["radar"][4])
        novo.update(id="r7", titulo="Banco central fictício de outro país mantém juros")
        novo["ataque"]["url"] = novo["fontes"][0]["url"] = "https://wsj.com/exemplo/juros-mantidos-de-novo"
        e["radar"].append(novo)
        return apoio.acerta(e)

    def test_corta_mantem_completa_quando_a_contagem_ainda_fecha(self):
        """CONTRATO, seção 4.2, `--corta`: troca `estado` para `reduzida` "se a contagem da `completa`
        deixou de fechar". Com 7 no radar, cortar um de geopolítica deixa 6, com 3 de IA: segue `completa`."""
        _, publicada, _ = self.corta("r5", self._com_sete_no_radar())
        self.assertEqual((publicada["estado"], len(publicada["radar"])), ("completa", 6))
        self.assertEqual(publicada["radar"][5]["id"], "r6")

    def test_corta_vira_reduzida_quando_faltam_itens_de_ia(self):
        """CONTRATO, seção 4.2, `--corta`: "se a contagem da `completa` deixou de fechar" (ESQUEMA, R15:
        a `completa` pede 3 ou mais itens de IA no radar). Com 7 no radar, cortar um de IA deixa 6, mas
        só 2 de IA."""
        _, publicada, _ = self.corta("r1", self._com_sete_no_radar())
        self.assertEqual((publicada["estado"], len(publicada["radar"])), ("reduzida", 6))
        self.assertEqual(apoio.dominio_de(publicada, "suprimentos")["gatilhos"][0]["ref"], "r3")

    def test_corta_item_com_erro_e_publica_o_resto(self):
        """CONTRATO, seção 4.2, `--corta`: "Para quando um item não passa e não há mais rodada"; "segue
        para os passos 3 a 8". Sem `--corta`, o r3 com defeito segura a edição; com ele, a edição sai."""
        def defeito(rascunho):
            rascunho["radar"][2]["sem_placar"] = "160"                 # sobra do modelo: regra R17

        raiz, t, _ = self.cenario()
        defeito(t.rascunho)
        t.grava()
        self.acusa(self.edicao(raiz, t), "R17")
        _, publicada, _ = self.corta("r3", defeito=defeito)
        self.assertEqual((publicada["estado"], len(publicada["radar"])), ("reduzida", 5))

    def test_corta_resultado_passa_no_valida(self):
        """CONTRATO, seção 4.2, `--corta`: depois do corte, "segue para os passos 3 a 8"; seção 5: o
        `valida.py --edicao` do arquivo publicado dá código 0."""
        raiz, t, _ = self.cenario()
        self.passou(self.edicao(raiz, t, "--corta", "r4"))
        self.passou(self.valida("--edicao", apoio.caminho_da_edicao(raiz, DIA), raiz=raiz))

    def test_corta_sem_valor_e_erro_de_uso(self):
        """CONTRATO, seção 0, "Erro de uso": "falta de opção obrigatória" (`--corta` pede os ids)."""
        raiz, t, _ = self.cenario()
        self.erro_de_uso(self.edicao(raiz, t, "--corta"))

    def test_corta_id_que_o_rascunho_nao_tem_e_erro_de_uso(self):
        """CONTRATO, seção 4.2, `--corta`: "Id que o rascunho não tem é erro de uso: `FALHA uso: …`, código 2,
        e nada é cortado nem gravado". Basta um id que falta para segurar o corte inteiro."""
        raiz, t, _ = self.cenario()
        antes, antes_trabalho = apoio.fotografa(raiz), apoio.fotografa(t.pasta, rigor=True)
        for ids in ("r9", "r2,r9"):
            with self.subTest(ids=ids):
                self.erro_de_uso(self.edicao(raiz, t, "--corta", ids))
        self.nada_mudou(antes, apoio.fotografa(raiz), "a raiz")
        self.nada_mudou(antes_trabalho, apoio.fotografa(t.pasta, rigor=True), "a pasta de trabalho")

    def test_corta_com_simula_corta_so_em_memoria(self):
        """CONTRATO, seção 4.2: "Com `--simula`, o passo 2 corta em memória: o `rascunho.json` não é regravado"
        (e o `--simula` não grava nada no repositório)."""
        raiz, t, _ = self.cenario()
        antes, antes_trabalho = apoio.fotografa(raiz), apoio.fotografa(t.pasta, rigor=True)
        self.passou(self.edicao(raiz, t, "--corta", "r3", "--simula"))
        self.nada_mudou(antes, apoio.fotografa(raiz), "a raiz")
        self.nada_mudou(antes_trabalho, apoio.fotografa(t.pasta, rigor=True), "a pasta de trabalho")

    def test_corta_regravado_fica_mesmo_quando_a_edicao_nao_passa(self):
        """CONTRATO, seção 4.2: "O rascunho regravado fica, mesmo que a conferência recuse a edição depois: a
        rodada seguinte parte dele". Um item do radar com defeito continua no rascunho; o corte de outro item
        é regravado assim mesmo, e a raiz não muda."""
        raiz, t, _ = self.cenario()
        t.rascunho["radar"][4]["confianca"] = "alta"   # o teto pelas fontes é media: R08
        t.grava()
        antes = apoio.fotografa(raiz)
        self.acusa(self.edicao(raiz, t, "--corta", "r1"), "R08")
        self.nada_mudou(antes, apoio.fotografa(raiz), "a raiz")
        regravado = self.le_json_de(t.pasta, "rascunho.json")
        self.assertEqual([r["id"] for r in regravado["radar"]], ["r1", "r2", "r3", "r4", "r5"])


# =============================================================================================
# (c) falha e refaz
# =============================================================================================

class Falha(CasoDePublica):
    """CONTRATO, seção 4.3: `publica.py falha`."""

    def falha(self, raiz, *mais, trabalho=None, agora=None, com_dia=True):
        argumentos = ["falha", "--motivo", MOTIVO] + (["--dia", DIA] if com_dia else []) + list(mais)
        return self.publica(*argumentos, raiz=raiz, trabalho=trabalho or self.pasta("trabalho"),
                            agora=agora or agora_de(DIA))

    def test_falha_sem_edicao_anterior(self):
        """CONTRATO, seção 4.3: "Gera `edicoes/DIA.json` com `estado: "falha"`: níveis e `desde` copiados
        de `anterior` (ou 1), `gatilhos` vazios, `tendencia` `estavel`, `sem_preco` pela regra R13f,
        `leitura` e `vigiar` com texto fixo […] (sem `anterior`, só "Sem leitura hoje."), `resumo` igual a
        "Sem edição hoje. " mais o `--motivo`, `alerta.motivo` e `bastidores.limites` com o `--motivo`,
        `principais`, `radar`, `placar_do_dia`, `novos_players`, `errata` e `respostas` vazios, […]
        `bastidores.modo` `feeds`, contadores em 0 e listas vazias". A edição inteira é comparada."""
        raiz = self.nova_raiz()
        self.passou(self.falha(raiz))
        publicada = self.publicada(raiz)
        self.iguais(publicada, apoio.edicao_falha(DIA, MOTIVO), "edicoes/%s.json" % DIA)
        self.assertEqual((publicada["estado"], publicada["resumo"]), ("falha", "Sem edição hoje. " + MOTIVO))
        self.assertEqual((publicada["alerta"]["motivo"], publicada["bastidores"]["limites"]), (MOTIVO, MOTIVO))
        self.assertEqual({(d["nivel"], d["tendencia"], d["desde"], d["leitura"], d["vigiar"])
                          for d in publicada["alerta"]["dominios"]},
                         {(1, "estavel", DIA, "Sem leitura hoje.", "Sem leitura hoje.")})
        self.assertEqual(apoio.chaves_fora_de_ordem(publicada), [])

    def test_falha_repete_os_niveis_da_anterior(self):
        """CONTRATO, seção 4.3: "níveis e `desde` copiados de `anterior`"; texto fixo "Sem leitura hoje.
        Nível repetido de DD/MM."; ESQUEMA, R15: "níveis e `desde` iguais aos da edição anterior"."""
        ontem = monta_edicao(ONTEM, rica=True)             # energia 3, suprimentos 2, conflito 3
        raiz = self.nova_raiz([ontem])
        self.passou(self.falha(raiz))
        publicada = self.publicada(raiz)
        self.iguais(publicada, apoio.edicao_falha(DIA, MOTIVO, anterior=ontem), "edicoes/%s.json" % DIA)
        self.assertEqual([(d["nivel"], d["desde"]) for d in publicada["alerta"]["dominios"]],
                         [(3, ONTEM), (1, ONTEM), (1, ONTEM), (2, ONTEM), (3, ONTEM)])
        self.assertEqual((publicada["alerta"]["nivel"], publicada["alerta"]["tendencia"]), (3, "estavel"))
        fixo = "Sem leitura hoje. Nível repetido de %s." % dia_mes(ONTEM)
        self.assertEqual({d["leitura"] for d in publicada["alerta"]["dominios"]}, {fixo})
        self.assertEqual({d["vigiar"] for d in publicada["alerta"]["dominios"]}, {fixo})

    def test_falha_anterior_e_a_ultima_que_nao_e_falha(self):
        """CONTRATO, seção 4.3: "níveis e `desde` copiados de `anterior`"; seção 4.1: `anterior` é "a mais
        recente antes de `--dia` que não é `falha`". Duas falhas seguidas repetem a mesma edição."""
        d2 = monta_edicao(ANTEONTEM, rica=True)
        falha_de_ontem = apoio.edicao_falha(ONTEM, MOTIVO, anterior=d2)
        raiz = self.nova_raiz([d2, falha_de_ontem])
        self.passou(self.falha(raiz))
        self.iguais(self.publicada(raiz), apoio.edicao_falha(DIA, MOTIVO, anterior=d2), "edicoes/%s.json" % DIA)

    def test_falha_copia_os_indicadores_se_existirem(self):
        """CONTRATO, seção 4.3: "`indicadores` de `P/indicadores.json` se existir"; "`sem_preco` pela regra
        R13f" (com os indicadores do cenário, só o milho fica sem base de 7 dias)."""
        raiz, t, esperada = self.cenario()
        os.remove(t.arquivo("coleta.json"))                # no dia de falha, a coleta não funcionou
        self.passou(self.falha(raiz, trabalho=t.pasta))
        publicada = self.publicada(raiz)
        self.iguais(publicada["indicadores"], esperada["indicadores"], "indicadores")
        self.assertEqual([d["sem_preco"] for d in publicada["alerta"]["dominios"]], [[], ["milho"], [], [], []])
        self.assertEqual(publicada["principais"], [])

    def test_falha_sem_indicadores(self):
        """CONTRATO, seção 4.3: sem `P/indicadores.json`, `indicadores` sai vazia e `sem_preco` lista todos
        os indicadores de preço de cada domínio (regra R13f)."""
        raiz = self.nova_raiz()
        self.passou(self.falha(raiz))
        publicada = self.publicada(raiz)
        self.assertEqual(publicada["indicadores"], [])
        self.assertEqual([d["sem_preco"] for d in publicada["alerta"]["dominios"]],
                         [["brent"], ["trigo", "milho", "soja"], ["usd_brl"], [], []])

    def test_falha_publica_como_o_passo_7(self):
        """CONTRATO, seção 4.3: "Depois publica como no passo 7 de `edicao`": saem o `.json`, o `.md`, o
        índice e o feed, e os registros não ganham nada. No feed, o título é `INFOCENARIUM DD/MM/AAAA · sem
        edição` (seção 4.5)."""
        raiz = self.nova_raiz()
        self.passou(self.falha(raiz, "--url-base", BASE))
        self.assertTrue(self.texto_md(raiz).strip())
        indice = self.le_json_de(raiz, "edicoes", "indice.json")
        self.assertEqual([(e["data"], e["estado"], e["nivel"]) for e in indice["edicoes"]], [(DIA, "falha", 1)])
        self.assertEqual(self.entradas(raiz)[DIA].findtext(NS + "title"), "INFOCENARIUM %s · sem edição" % data_br(DIA))
        self.assertEqual(self.le_json_de(raiz, "dados", "vetores.json")["vetores"], [])
        self.assertEqual(self.le_json_de(raiz, "dados", "players.json")["players"], apoio.dados("players")["players"])

    def test_falha_md_sem_modo_nem_contadores(self):
        """CONTRATO, seção 4.5: na edição `falha`, "os bastidores trazem só o que não deu para conferir: sem a
        linha do modo e sem os contadores"; a linha do que mudou é "Níveis repetidos de DD/MM."."""
        ontem = monta_edicao(ONTEM, rica=True)
        raiz = self.nova_raiz([ontem])
        self.passou(self.falha(raiz))
        linhas = self.texto_md(raiz).split("\n")
        self.assertIn("Níveis repetidos de %s." % dia_mes(ONTEM), linhas)
        bastidores = [linha for linha in linhas[linhas.index("## Bastidores") + 1:] if linha]
        self.assertEqual(bastidores, ["- O que não deu para conferir: " + MOTIVO])
        self.assertFalse([linha for linha in linhas if linha.startswith("- Modo:") or "feeds lidos" in linha])

    def test_falha_resultado_passa_no_valida(self):
        """CONTRATO, seção 5: no dia de falha, a rotina roda depois o `valida.py --tudo --base origin/main
        --dia "$DIA"`; ROTINA, seção 10: "depois o `valida.py` da seção 8 e a seção 9"."""
        ontem = monta_edicao(ONTEM, rica=True)
        raiz = self.nova_raiz([ontem], com_git=True)
        self.passou(self.falha(raiz))
        self.passou(self.valida("--tudo", "--base", "origin/main", "--dia", DIA, raiz=raiz))
        self.passou(self.valida("--edicao", apoio.caminho_da_edicao(raiz, DIA), raiz=raiz))

    def test_falha_recusa_dia_ja_publicado(self):
        """CONTRATO, seção 4.3: "Recusa (`FALHA`, código 1) se o dia já foi publicado com estado `completa`
        ou `reduzida` (passo 3 de `edicao`)"."""
        raiz, t, _ = self.cenario(com_git=True)
        self.passou(self.edicao(raiz, t))
        apoio.commita(raiz, "edição %s" % DIA)
        antes = apoio.fotografa(raiz)
        self.falhou(self.falha(raiz, trabalho=t.pasta))
        self.nada_mudou(antes, apoio.fotografa(raiz), "a raiz")

    def test_falha_sem_motivo_e_erro_de_uso(self):
        """CONTRATO, seção 4: `publica.py falha --motivo "TEXTO"`; seção 0, "Erro de uso": "falta de opção
        obrigatória"."""
        raiz = self.nova_raiz()
        self.erro_de_uso(self.publica("falha", "--dia", DIA, raiz=raiz, trabalho=self.pasta("trabalho")))
        self.assertFalse(os.path.exists(apoio.caminho_da_edicao(raiz, DIA)))

    def test_falha_recusa_motivo_longo_ou_com_html(self):
        """CONTRATO, seção 4.3: "`--motivo`: até 200 caracteres, sem HTML (regra R17). Motivo fora da regra é
        erro de uso: `FALHA uso: …`, código 2, e nada é gravado (o texto não é cortado)"."""
        for nome, motivo in (("201 caracteres", "m" * 201), ("com HTML", "Nada funcionou <b>hoje</b>."),
                             ("com quebra de linha", "Nada funcionou\nhoje."), ("vazio", "")):
            with self.subTest(motivo=nome):
                raiz = self.nova_raiz()
                antes = apoio.fotografa(raiz)
                res = self.publica("falha", "--motivo", motivo, "--dia", DIA, raiz=raiz, trabalho=self.pasta("trabalho"))
                self.erro_de_uso(res)
                self.nada_mudou(antes, apoio.fotografa(raiz), "a raiz")

    def test_falha_aceita_motivo_de_200_caracteres(self):
        """CONTRATO, seção 4.3: "`--motivo`: até 200 caracteres"."""
        motivo = ("Motivo fictício. " * 20)[:199] + "."
        raiz = self.nova_raiz()
        self.passou(self.publica("falha", "--motivo", motivo, "--dia", DIA, raiz=raiz, trabalho=self.pasta("trabalho")))
        self.assertEqual(self.publicada(raiz)["alerta"]["motivo"], motivo)


class Refaz(CasoDePublica):
    """CONTRATO, seção 4.4: `publica.py refaz`."""

    DERIVADOS = ["edicoes/%s.md" % ONTEM, "edicoes/%s.md" % DIA, "edicoes/indice.json", "feed.xml"]

    def _dois_dias_publicados(self):
        """Raiz com duas edições publicadas pela própria ferramenta (ontem e hoje), com endereço base."""
        ontem = troca_titulos(monta_edicao(ONTEM), 0)
        raiz, t, _ = self.cenario(ontem)
        self.passou(self.edicao(raiz, t, "--url-base", BASE))
        hoje = monta_edicao(DIA, anterior=ontem, rica=True)
        t2 = apoio.Trabalho(self.pasta("trabalho"), hoje).grava()
        self.passou(self.edicao(raiz, t2))
        return raiz

    def test_refaz_recria_indice_textos_e_feed_com_os_mesmos_bytes(self):
        """CONTRATO, seção 4.4: "Refaz `edicoes/indice.json`, todos os `edicoes/*.md` e `feed.xml` a partir
        dos arquivos de edição. Não toca nos `.json` de edição nem em `dados/`"; seção 0: "Mesma entrada,
        mesmos bytes". Os derivados são apagados ou estragados e voltam iguais."""
        raiz = self._dois_dias_publicados()
        antes = apoio.fotografa(raiz)
        for derivado in self.DERIVADOS:
            self.le_arquivo(raiz, derivado)
        os.remove(os.path.join(raiz, "edicoes", "indice.json"))
        os.remove(apoio.caminho_da_edicao(raiz, ONTEM, "md"))
        apoio.grava_texto(apoio.caminho_da_edicao(raiz, DIA, "md"), "texto estragado\n")
        self.passou(self.publica("refaz", raiz=raiz))
        self.nada_mudou(antes, apoio.fotografa(raiz), "a raiz, depois do refaz,")

    def test_refaz_nao_toca_nas_edicoes_nem_nos_dados(self):
        """CONTRATO, seção 4.4: "Não toca nos `.json` de edição nem em `dados/`"; seção 6: grava só
        `edicoes/indice.json`, `edicoes/*.md` e `feed.xml`, e nada na pasta de trabalho."""
        raiz = self._dois_dias_publicados()
        antes = apoio.fotografa(raiz, rigor=True)
        self.passou(self.publica("refaz", raiz=raiz))
        criados, mudados, sumidos = apoio.diferenca(antes, apoio.fotografa(raiz, rigor=True))
        self.assertEqual((criados, sumidos), ([], []))
        self.assertLessEqual(set(mudados), set(self.DERIVADOS), "o refaz mexeu fora dos derivados")

    def test_refaz_em_raiz_montada_a_mao(self):
        """CONTRATO, seção 4.4: "a partir dos arquivos de edição". A raiz só tem os `.json` de duas
        edições; o `refaz` cria o índice (ESQUEMA, seção 11), um `.md` para cada uma e o feed. Depois o
        `valida.py --tudo` passa."""
        ontem = troca_titulos(monta_edicao(ONTEM), 0)
        hoje = monta_edicao(DIA, anterior=ontem, rica=True)
        raiz = self.nova_raiz([ontem, hoje], derivados=False)
        self.passou(self.publica("refaz", "--url-base", BASE, raiz=raiz))
        self.iguais(self.le_json_de(raiz, "edicoes", "indice.json"), apoio.indice_de([ontem, hoje]), "edicoes/indice.json")
        self.assertTrue(self.texto_md(raiz, ONTEM).strip() and self.texto_md(raiz, DIA).strip())
        self.assertEqual(sorted(self.entradas(raiz)), [ONTEM, DIA])
        self.passou(self.valida("--tudo", "--dia", DIA, raiz=raiz))


# =============================================================================================
# (d) o formato do .md e do feed.xml
# =============================================================================================

class FormatoDoTexto(CasoDePublica):
    """CONTRATO, seção 4.5, "`edicoes/DIA.md`"."""

    def _md_com(self, muda=None, esperada=None, historico=()):
        raiz, t, _ = self.cenario(esperada, historico)
        if muda:
            muda(t.rascunho)
            t.grava()
        self.passou(self.edicao(raiz, t))
        return self.texto_md(raiz, t.dia), self.publicada(raiz, t.dia)

    def test_md_escapa_os_sinais_de_markdown(self):
        """CONTRATO, seção 4.5: "Todo campo de texto sai com escape dos sinais de Markdown (`\\`, `[`, `]`,
        `(`, `)`, `*`, `_`, crase, `#`, `|`)". Cada sinal plantado no `resumo` sai precedido de barra
        invertida, e não aparece cru."""
        marcas = {sinal: "sinal%02dx%sxfim" % (n, sinal) for n, sinal in enumerate(SINAIS_DE_MARKDOWN)}

        def muda(rascunho):
            rascunho["resumo"] = "Edição fictícia com sinais: " + " ".join(marcas.values()) + "."

        md, _ = self._md_com(muda)
        for sinal, marca in marcas.items():
            with self.subTest(sinal=sinal):
                self.assertIn(marca.replace(sinal, "\\" + sinal), md)
                self.assertNotIn(marca, md.replace(marca.replace(sinal, "\\" + sinal), ""))

    def test_md_titulo_de_fonte_nao_vira_link_nem_destaque(self):
        """CONTRATO, seção 4.5: "Texto de terceiro nunca vira link" (o título de fonte é texto de
        terceiro: sai com os sinais escapados)."""
        def muda(rascunho):
            rascunho["principais"][0]["fontes"][0]["titulo"] = "Sample deal [update] is *big* news"

        md, _ = self._md_com(muda)
        self.assertIn("Sample deal \\[update\\] is \\*big\\* news", md)
        self.assertIsNone(re.search(r"(?<!\\)\[update", md))

    def test_md_url_aparece_por_extenso(self):
        """CONTRATO, seção 4.5: "Só campo `url` vira endereço, e aparece por extenso". Cada endereço de
        fonte da edição está no texto, inteiro."""
        md, publicada = self._md_com()
        urls = [f["url"] for item in apoio.itens(publicada) for f in item["fontes"]]
        self.assertEqual(len(urls), 26)
        for url in urls:
            self.assertIn(url, md)

    def test_md_fonte_fora_do_mapa(self):
        """CONTRATO, seção 4.5: "Fonte `outro` aparece com o `nome` e "(fora do mapa)""."""
        md, _ = self._md_com()
        self.assertIn("(fora do mapa)", md)
        self.assertIn("Diário Oficial da República de Exemplo \\(fictício\\)", md)

    def test_md_aviso_de_conflito_de_interesse(self):
        """CONTRATO, seção 4.5: "Item com `conflito_de_interesse: true` leva a linha `Aviso: o INFOCENARIUM é
        escrito por modelos de IA, do setor de IA, que podem ser parte ou concorrente
        nesta notícia: foi construído pelo Claude Fable e pelo Claude Opus, da Anthropic, e hoje quem escreve é o
        GLM, da Z.ai.`" (4 itens têm a marca no cenário)."""
        md, _ = self._md_com()
        self.assertGreaterEqual(md.split("\n").count(AVISO_FIXO), 4)

    def test_md_sem_item_com_conflito_nao_traz_o_aviso(self):
        """CONTRATO, seção 4.5: a linha de aviso é do "item com `conflito_de_interesse: true`". Numa
        edição `reduzida` sem item de IA nem nome da lista de conflito, a linha não aparece."""
        e = monta_edicao(DIA)
        e["estado"] = "reduzida"
        e["principais"] = [e["principais"][0], e["principais"][2]]
        e["principais"][1]["id"] = "p2"
        e["radar"] = e["radar"][3:]
        for n, item in enumerate(e["radar"], 1):
            item["id"] = "r%d" % n
        apoio.acerta(e)
        self.assertFalse([i["id"] for i in apoio.itens(e) if i.get("conflito_de_interesse")])
        md, publicada = self._md_com(esperada=e)
        self.assertFalse([i["id"] for i in apoio.itens(publicada) if i.get("conflito_de_interesse")])
        self.assertNotIn(AVISO_FIXO, md)

    def test_md_edicao_de_exemplo_abre_com_a_linha_de_exemplo(self):
        """CONTRATO, seção 4.5: "Edição com `exemplo: true` abre com a linha `EDIÇÃO DE EXEMPLO · dados
        fictícios`". O `publica.py edicao` recusa rascunho de exemplo; o texto sai pelo `refaz`."""
        raiz = self.nova_raiz()
        apoio.grava_json(apoio.caminho_da_edicao(raiz, ONTEM), apoio.exemplo())
        self.passou(self.publica("refaz", raiz=raiz))
        self.assertEqual(self.texto_md(raiz, ONTEM).split("\n")[0], "EDIÇÃO DE EXEMPLO · dados fictícios")

    def test_md_edicao_de_verdade_nao_abre_com_a_linha_de_exemplo(self):
        """CONTRATO, seção 4.5: a linha `EDIÇÃO DE EXEMPLO · dados fictícios` é só da edição com
        `exemplo: true`."""
        md, _ = self._md_com()
        self.assertNotIn("EDIÇÃO DE EXEMPLO", md)

    def test_md_titulo_com_a_data_e_nivel_com_rotulo(self):
        """CONTRATO, seção 4.5: "título com a data; nível geral, rótulo e tendência". O CONTRATO não fixa
        a forma da data: o teste aceita `20/11/2026` ou `2026-11-20` na primeira linha com texto."""
        md, _ = self._md_com()
        primeira = [linha for linha in md.split("\n") if linha.strip()][0]
        self.assertTrue(data_br(DIA) in primeira or DIA in primeira, primeira)
        self.assertIn("TENSÃO", md)

    def test_md_linha_do_que_mudou_desde_a_anterior(self):
        """CONTRATO, seção 4.5: "a linha do que mudou desde a edição anterior ("Desde 18/11: energia 2 →
        3.")". Ontem: energia 2, suprimentos 2 e conflito 3; hoje só a energia muda, para 3."""
        ontem = troca_titulos(monta_edicao(ONTEM, alerta={
            "energia": {"nivel": 2, "gatilhos": [gatilho("energia.2", "r4")]},
            "suprimentos": {"nivel": 2, "gatilhos": [gatilho("suprimentos.2", "r4")]},
            "conflito": {"nivel": 3, "gatilhos": [gatilho("conflito.3", "p1")]}}), 0)
        hoje = monta_edicao(DIA, anterior=ontem, rica=True)
        md, publicada = self._md_com(esperada=hoje, historico=[ontem])
        self.assertEqual([d["nivel"] for d in publicada["alerta"]["dominios"]], [3, 1, 1, 2, 3])
        self.assertIn("Desde %s: energia 2 → 3." % dia_mes(ONTEM), md)

    def test_md_linha_do_que_mudou_com_dois_dominios_e_sem_anterior(self):
        """CONTRATO, seção 4.5: "Com mais de um domínio, as mudanças vêm na ordem da régua, separadas por
        vírgula ("Desde 18/11: energia 2 → 3, conflito 2 → 3."). Sem edição anterior: "Primeira edição: sem
        comparação."". Ontem: energia, suprimentos e conflito em 2; hoje energia e conflito vão a 3."""
        ontem = troca_titulos(monta_edicao(ONTEM, alerta={
            "energia": {"nivel": 2, "gatilhos": [gatilho("energia.2", "r4")]},
            "suprimentos": {"nivel": 2, "gatilhos": [gatilho("suprimentos.2", "r4")]},
            "conflito": {"nivel": 2, "gatilhos": [gatilho("conflito.2", "r4")]}}), 0)
        hoje = monta_edicao(DIA, anterior=ontem, rica=True)
        md, publicada = self._md_com(esperada=hoje, historico=[ontem])
        self.assertEqual([d["nivel"] for d in publicada["alerta"]["dominios"]], [3, 1, 1, 2, 3])
        self.assertIn("Desde %s: energia 2 → 3, conflito 2 → 3." % dia_mes(ONTEM), md.split("\n"))
        primeira, _ = self._md_com()
        self.assertIn("Primeira edição: sem comparação.", primeira.split("\n"))

    def test_md_linha_de_niveis_iguais(self):
        """CONTRATO, seção 4.5: "sem mudança, "Desde 18/11: nenhum nível mudou."" (o texto do site)."""
        ontem = troca_titulos(monta_edicao(ONTEM), 0)
        md, _ = self._md_com(esperada=monta_edicao(DIA, anterior=ontem), historico=[ontem])
        self.assertIn("Desde %s: nenhum nível mudou." % dia_mes(ONTEM), md.split("\n"))

    def test_md_conflito_traz_o_teto_da_confianca_numa_linha_a_parte(self):
        """CONTRATO, seção 4.5: o item com conflito leva o aviso "e, numa linha à parte, `Por isso a confiança
        deste item não passa de média.`". Cada aviso vem seguido do teto."""
        md, _ = self._md_com()
        linhas = md.split("\n")
        avisos = [n for n, linha in enumerate(linhas) if linha == AVISO_FIXO]
        self.assertGreaterEqual(len(avisos), 4)
        for n in avisos:
            self.assertEqual(linhas[n + 1], "Por isso a confiança deste item não passa de média.")

    def test_md_conflito_nomeia_o_vinculo_da_regua(self):
        """CONTRATO, seção 4.5: "Quando a lista `conflito` da régua conhece o vínculo (regra R19, casos b e c),
        uma terceira linha o nomeia, com o texto do site: "Este item envolve nomes da lista de conflito da régua:
        NOMES."", na ordem da lista; termo que já está no nome de um player listado não se repete."""
        md, publicada = self._md_com()
        nome = apoio.dados("players")
        nome = next(p["nome"] for p in nome["players"] if p["id"] == "altman")
        blocos = dict((b.split(" ", 1)[0], b.split("\n\n")[1].split("\n")) for b in md.split("\n### ")[1:])
        p2 = blocos["p2"]
        self.assertEqual(p2[1:3], [AVISO_FIXO, "Por isso a confiança deste item não passa de média."])
        self.assertTrue(p2[3].startswith("Este item envolve nomes da lista de conflito da régua: %s"
                                         % nome.replace("(", "\\(").replace(")", "\\)")), p2)
        self.assertTrue(p2[3].endswith("."), p2)
        self.assertEqual(p2[3].count("OpenAI"), 1, "o termo que já está no nome do player não se repete")
        # notícia de IA sem nome da lista (r1): o aviso já diz o vínculo, e não há terceira linha
        self.assertEqual(blocos["r1"][1:], [AVISO_FIXO, "Por isso a confiança deste item não passa de média."])
        self.assertEqual(publicada["radar"][0]["categoria"], "ia")

    def test_md_nota_de_mapa_em_rascunho(self):
        """CONTRATO, seção 4.5: "Com o mapa de veículos em rascunho (`revisado_em` nulo […]), "Mapa de
        veículos em rascunho, ainda sem revisão do dono." vem logo abaixo de `## Principais` e de `## Radar`"."""
        self.assertIsNone(apoio.dados("veiculos").get("revisado_em"))
        md, _ = self._md_com()
        nota = "Mapa de veículos em rascunho, ainda sem revisão do dono."
        self.assertIn("## Principais\n\n%s\n\n### p1 · " % nota, md)
        self.assertIn("## Radar\n\n%s\n\n### r1 · " % nota, md)
        self.assertEqual(md.count(nota), 2)

    def test_md_deixou_de_fora_com_a_ressalva_da_leitura(self):
        """CONTRATO, seção 4.5: "Deixou de fora: … Segundo a leitura do INFOCENARIUM em DD/MM." (com a data
        da edição)."""
        md, publicada = self._md_com()
        omissoes = [a for item in apoio.itens(publicada) for a, _ in [(x, 0) for x in item.get("ataques", [])]
                    + ([(item["ataque"], 0)] if "ataque" in item else []) if "omite" in a]
        self.assertTrue(omissoes)
        self.assertEqual(md.count("Segundo a leitura do INFOCENARIUM em %s." % dia_mes(DIA)), len(omissoes))

    def test_md_gatilho_diz_para_onde_a_prova_leva(self):
        """CONTRATO, seção 4.5: os gatilhos vêm sob "**Gatilhos de hoje:**", com "ver principal 1", "ver radar
        4" ou "ver indicador: Petróleo Brent"; sem o id do item no texto."""
        md, publicada = self._md_com()
        self.assertIn("**Gatilhos de hoje:**", md.split("\n"))
        self.assertNotIn("**Gatilhos:**", md)
        refs = [g["ref"] for d in publicada["alerta"]["dominios"] for g in d["gatilhos"]]
        for ref in refs:
            with self.subTest(ref=ref):
                if ref.startswith("p"):
                    self.assertIn(" · ver principal %s\n" % ref[1:], md)
                elif ref.startswith("r"):
                    self.assertIn(" · ver radar %s\n" % ref[1:], md)
                else:
                    self.assertIn(" · ver indicador: ", md)
        self.assertNotIn(" · item `p", md)

    def test_md_indicador_sem_valor_traz_a_fonte_prevista(self):
        """CONTRATO, seção 4.5: "Indicador sem valor diz "sem dado · fonte prevista: NOME <url>"". O de valor
        segue com "fonte: "."""
        md, publicada = self._md_com()
        linhas = [linha for linha in md.split("\n") if linha.startswith("- ") and " · fonte" in linha
                  and ": sem dado" in linha]
        sem_valor = [i for i in publicada["indicadores"] if i["valor"] is None]
        self.assertEqual(len(linhas), len(sem_valor))
        for linha in linhas:
            self.assertIn(" · fonte prevista: ", linha)

    def test_md_placar_do_dia_so_mostra_narrativa_diferente_de_zero(self):
        """CONTRATO, seção 4.5: "placar do dia (saldo, e a narrativa quando não é 0)"."""
        md, publicada = self._md_com()
        linhas = md.split("## Placar do dia\n\n")[1].split("\n\n")[0].split("\n")
        self.assertEqual(len(linhas), len(publicada["placar_do_dia"]))
        for linha, placar in zip(linhas, publicada["placar_do_dia"]):
            with self.subTest(partido=placar["partido"]):
                self.assertEqual(" · narrativa " in linha, placar["narrativa"] != 0, linha)

    def test_md_sem_dado_de_preco(self):
        """CONTRATO, seção 4.5: nos domínios, ""sem dado de preço de: …" quando houver". No cenário, o
        milho deixa alimentos sem dado; numa edição com tudo medido, a frase não aparece."""
        md, _ = self._md_com()
        self.assertIn("sem dado de preço de:", md)
        # "ao lado do nível, no título do domínio; a frase lista os nomes dos indicadores, como estão na
        # edição" (CONTRATO, seção 4.5)
        # (sem edição anterior, o "estável" não sai: CONTRATO, seção 4.5, linhas fixas)
        self.assertIn("### Alimentos · nível 1 · sem dado de preço de: Milho", md.split("\n"))
        medida = monta_edicao(DIA)
        apoio.indicador_de(medida, "milho")["variacao_7d_pct"] = 0.4
        apoio.acerta(medida)
        md_medido, publicada = self._md_com(esperada=medida)
        self.assertEqual([d["sem_preco"] for d in publicada["alerta"]["dominios"]], [[], [], [], [], []])
        self.assertNotIn("sem dado de preço de:", md_medido)

    def test_md_segue_a_ordem_do_site(self):
        """CONTRATO, seção 4.5: "mesma ordem do site: […] resumo; domínios […]; indicadores; cada principal
        […]; radar; placar do dia (saldo e narrativa); respostas; players novos; errata; bastidores".
        Uma palavra única é plantada em um campo de cada parte; elas aparecem nessa ordem."""
        ontem = troca_titulos(monta_edicao(ONTEM), 0)
        hoje = monta_edicao(DIA, anterior=ontem, rica=True)
        hoje["respostas"] = [apoio.ordena({"edicao": ONTEM, "item": "p1", "pergunta": ontem["principais"][0]["vigiar"][0],
                                           "resposta": "sem_dado", "texto": F + "Marcaresposta: nenhuma fonte respondeu."},
                                          "resposta")]
        hoje["errata"] = [apoio.ordena({"edicao": ONTEM, "item": "r3", "erro": F + "Marcaerrata: o prazo saiu errado.",
                                        "correcao": F + "O prazo certo é de 30 dias."}, "errata")]
        hoje["resumo"] = "Marcaresumo: edição fictícia para conferir a ordem do texto."
        apoio.dominio_de(hoje, "energia")["leitura"] = F + "Marcadominio: leitura fictícia do domínio."
        hoje["principais"][0]["titulo"] = "Marcaprincipal ataca terminal fictício"
        hoje["radar"][0]["titulo"] = "Marcaradar assina contrato fictício"
        hoje["placar_do_dia"][0]["frase"] = F + "Marcaplacar: o dia do partido em uma frase."
        hoje["novos_players"][0]["nota"] = F + "Marcaplayer: país inventado."
        hoje["bastidores"]["limites"] = "Marcabastidores: o que não deu para conferir neste dia fictício."
        md, _ = self._md_com(esperada=hoje, historico=[ontem])
        ordem = ["Marcaresumo", "Marcadominio", "Frete marítimo de grãos e minério", "Marcaprincipal", "Marcaradar",
                 "Marcaplacar", "Marcaresposta", "Marcaplayer", "Marcaerrata", "Marcabastidores"]
        for palavra in ordem:
            self.assertIn(palavra, md)
        posicoes = [md.index(palavra) for palavra in ordem]
        self.assertEqual(posicoes, sorted(posicoes), "ordem das partes no .md: %s" % list(zip(ordem, posicoes)))

    def test_md_ordem_dentro_da_principal(self):
        """CONTRATO, seção 4.5: "cada principal (fato, não confirmado, quem atirou, o que está realmente
        acontecendo, na prática, no Brasil, eixo, placar ou a frase de `sem_placar`, vetores, vigiar,
        fontes)". Uma palavra única em cada campo da p1; elas aparecem nessa ordem."""
        def muda(rascunho):
            p = rascunho["principais"][0]
            p["fato"] = F + "Marcafato: drones fictícios atingiram um terminal inventado."
            p["nao_confirmado"][0] = "Segundo o governo fictício, marcaduvida: os drones partiram de outro país."
            p["ataques"][0]["enquadramento"] = F + "Marcatiro: chama o ataque de agressão."
            p["realmente"] = F + "Marcadossie: " + ("as manchetes brigam por um nome e o chão mostra menos. " * 16)
            p["na_pratica"][0] = F + "Marcapratica: terminal parado."
            p["no_brasil"] = F + "Marcabrasil: tende a encarecer o diesel importado."
            p["eixo"]["porque"] = F + "Marcaeixo: decreto suspendeu uma meta."
            p["placar"][0]["porque"] = F + "Marcaganho: barril mais caro em 7 dias."
            p["vetores"][0]["porque"] = F + "Marcavetor: decreto formal e reversível."
            p["vigiar"][0] = "Marcapergunta: o Reino de Amostra responde até %s?" % dia_mes(mais_dias(DIA, 3))
            p["fontes"][0]["titulo"] = "Marcafonte: terminal halts loading"

        md, _ = self._md_com(muda)
        ordem = ["Marcafato", "marcaduvida", "Marcatiro", "Marcadossie", "Marcapratica", "Marcabrasil", "Marcaeixo",
                 "Marcaganho", "Marcavetor", "Marcapergunta", "Marcafonte"]
        for palavra in ordem:
            self.assertIn(palavra, md)
        posicoes = [md.index(palavra) for palavra in ordem]
        self.assertEqual(posicoes, sorted(posicoes), "ordem dos campos da principal: %s" % list(zip(ordem, posicoes)))

    def test_md_radar_sem_placar_traz_a_frase(self):
        """CONTRATO, seção 4.5: "placar ou a frase de `sem_placar`"."""
        def muda(rascunho):
            rascunho["radar"][4]["sem_placar"] = F + "Marcasemplacar: decisão esperada, nada mudou."

        md, _ = self._md_com(muda)
        self.assertIn("Marcasemplacar", md)


class FormatoDoFeed(CasoDePublica):
    """CONTRATO, seção 4.5, "`feed.xml`" e "Endereço base"."""

    def _publica(self, *mais, esperada=None, historico=(), muda=None, com_git=False):
        raiz, t, esperada = self.cenario(esperada, historico, com_git=com_git)
        if muda:
            muda(t.rascunho)
            t.grava()
        self.passou(self.edicao(raiz, t, *mais))
        return raiz, self.publicada(raiz, t.dia)

    def test_feed_e_atom_bem_formado_com_titulo_e_updated(self):
        """CONTRATO, seção 4.5: "Atom 1.0, bem formado, texto escapado. Título `INFOCENARIUM · monitor geopolítico
        e de IA`. `updated` é o maior `gerada_em`". A raiz é `<feed>`, no espaço de nomes do Atom, com
        `id`, `title` e `updated` (os três são obrigatórios no Atom 1.0)."""
        raiz, _ = self._publica("--url-base", BASE)
        _, xml = self.feed(raiz)
        self.assertEqual(xml.tag, NS + "feed")
        self.assertEqual(xml.findtext(NS + "title"), "INFOCENARIUM · monitor geopolítico e de IA")
        self.assertEqual(xml.findtext(NS + "updated"), agora_de(DIA))
        self.assertTrue((xml.findtext(NS + "id") or "").strip(), "o feed precisa de <id>")

    def test_feed_entrada_da_edicao(self):
        """CONTRATO, seção 4.5: "Uma entrada por edição […]: título `INFOCENARIUM DD/MM/AAAA · nível N RÓTULO` […];
        `id` e `link` com o endereço da edição (`URL-BASE#/edicao/AAAA-MM-DD`); `updated` = `gerada_em`;
        `summary` = `resumo`; `content` em texto com os títulos e os fatos das principais"."""
        raiz, publicada = self._publica("--url-base", BASE)
        _, xml = self.feed(raiz)
        entradas = xml.findall(NS + "entry")
        self.assertEqual(len(entradas), 1)
        entrada, endereco = entradas[0], "%s#/edicao/%s" % (BASE, DIA)
        self.assertEqual(entrada.findtext(NS + "title"), "INFOCENARIUM %s · nível 3 TENSÃO" % data_br(DIA))
        self.assertEqual(entrada.findtext(NS + "id"), endereco)
        self.assertIn(endereco, [l.get("href") for l in entrada.findall(NS + "link")])
        self.assertEqual(entrada.findtext(NS + "updated"), agora_de(DIA))
        self.assertEqual(entrada.findtext(NS + "summary"), publicada["resumo"])
        conteudo = entrada.findtext(NS + "content") or ""
        for principal in publicada["principais"]:
            self.assertIn(principal["titulo"], conteudo)
            self.assertIn(principal["fato"], conteudo)

    def test_feed_exigencias_do_workflow(self):
        """CONTRATO, seção 4.5: "O workflow `publica-edicao.yml` recusa a edição inteira se o `feed.xml`
        sair disto: raiz `<feed>` e **todos** os elementos no espaço de nomes do Atom […], sem elemento de
        extensão; `content` e `summary` em texto puro (`type="text"` ou sem o atributo; nunca `xhtml`);
        nenhum `<!DOCTYPE`, nenhum `<!ENTITY`; e nenhuma instrução `<?…?>` além da declaração `<?xml …?>`
        no começo do arquivo"."""
        raiz, _ = self._publica("--url-base", BASE)
        texto, xml = self.feed(raiz)
        self.assertEqual(xml.tag, NS + "feed")
        fora = sorted({e.tag for e in xml.iter() if not e.tag.startswith(NS)})
        self.assertEqual(fora, [], "elementos fora do espaço de nomes do Atom")
        for nome in ("content", "summary"):
            for elemento in xml.iter(NS + nome):
                self.assertIn(elemento.get("type"), (None, "text"), "<%s> tem de ser texto puro" % nome)
                self.assertEqual(list(elemento), [], "<%s> não pode ter elemento dentro" % nome)
        self.assertNotIn("<!DOCTYPE", texto)
        self.assertNotIn("<!ENTITY", texto)
        instrucoes = re.findall(r"<\?", texto)
        self.assertLessEqual(len(instrucoes), 1, "há instrução <?…?> além da declaração")
        if instrucoes:
            self.assertTrue(texto.startswith("<?xml "), "a única instrução permitida é <?xml …?> no começo")

    def test_feed_texto_escapado(self):
        """CONTRATO, seção 4.5: "bem formado, texto escapado". Um resumo com `&`, `<` e `>` sai escapado no
        arquivo e é lido de volta igual."""
        resumo = "Edição fictícia: Amostra & Exemplo, com alta < 5% e queda > 2%."

        def muda(rascunho):
            rascunho["resumo"] = resumo

        raiz, _ = self._publica("--url-base", BASE, muda=muda)
        texto, xml = self.feed(raiz)
        self.assertEqual(xml.find(NS + "entry").findtext(NS + "summary"), resumo)
        self.assertIn("Amostra &amp; Exemplo", texto)
        self.assertIn("alta &lt; 5%", texto)

    def test_feed_so_as_30_mais_novas_e_sem_a_de_exemplo(self):
        """CONTRATO, seção 4.5: "Uma entrada por edição, as 30 mais novas, sem as de `exemplo: true`". A
        raiz tem 32 edições de verdade e a de exemplo, que é a mais nova de todas."""
        edicoes, anterior = [], None
        for recuo in range(33, 1, -1):                     # 32 edições, de 33 a 2 dias antes do exemplo
            anterior = monta_edicao(mais_dias(apoio.DIA_DO_EXEMPLO, -recuo), anterior=anterior)
            edicoes.append(anterior)
        raiz = self.nova_raiz(edicoes, derivados=False)
        apoio.grava_json(apoio.caminho_da_edicao(raiz, apoio.DIA_DO_EXEMPLO), apoio.exemplo())
        self.passou(self.publica("refaz", "--url-base", BASE, raiz=raiz))
        self.assertEqual(sorted(self.entradas(raiz)), [e["data"] for e in edicoes[2:]])

    def test_feed_entradas_da_mais_nova_para_a_mais_velha(self):
        """CONTRATO, seção 4.5: "As entradas vêm da edição mais nova para a mais velha"."""
        d3 = monta_edicao(TRES_ANTES)
        d2 = monta_edicao(ANTEONTEM, anterior=d3)
        raiz = self.nova_raiz([d3, d2, apoio.edicao_falha(ONTEM, MOTIVO, anterior=d2)], derivados=False)
        self.passou(self.publica("refaz", "--url-base", BASE, raiz=raiz))
        _, xml = self.feed(raiz)
        self.assertEqual([(e.findtext(NS + "id") or "")[-10:] for e in xml.findall(NS + "entry")],
                         [ONTEM, ANTEONTEM, TRES_ANTES])

    def test_feed_updated_sem_a_de_exemplo(self):
        """CONTRATO, seção 4.5: "a de exemplo não entra no feed nem conta para o `updated`, mesmo sendo a mais
        nova. Feed sem entrada (nenhuma edição, ou só a de exemplo) leva `1970-01-01T00:00:00Z`"."""
        real = monta_edicao(ANTEONTEM)
        raiz = self.nova_raiz([real], derivados=False)
        apoio.grava_json(apoio.caminho_da_edicao(raiz, apoio.DIA_DO_EXEMPLO), apoio.exemplo())
        self.assertGreater(apoio.exemplo()["gerada_em"], real["gerada_em"])
        self.passou(self.publica("refaz", "--url-base", BASE, raiz=raiz))
        _, xml = self.feed(raiz)
        self.assertEqual(xml.findtext(NS + "updated"), real["gerada_em"])
        so_exemplo = self.nova_raiz([], derivados=False)
        apoio.grava_json(apoio.caminho_da_edicao(so_exemplo, apoio.DIA_DO_EXEMPLO), apoio.exemplo())
        self.passou(self.publica("refaz", "--url-base", BASE, raiz=so_exemplo))
        _, xml = self.feed(so_exemplo)
        self.assertEqual((xml.findtext(NS + "updated"), xml.findall(NS + "entry")), ("1970-01-01T00:00:00Z", []))

    def test_feed_entrada_de_falha(self):
        """CONTRATO, seção 4.5: "em edição `falha`: `INFOCENARIUM DD/MM/AAAA · sem edição`"."""
        ontem = monta_edicao(ONTEM)
        raiz = self.nova_raiz([ontem, apoio.edicao_falha(DIA, MOTIVO, anterior=ontem)], derivados=False)
        self.passou(self.publica("refaz", "--url-base", BASE, raiz=raiz))
        entradas = self.entradas(raiz)
        self.assertEqual(entradas[DIA].findtext(NS + "title"), "INFOCENARIUM %s · sem edição" % data_br(DIA))
        self.assertEqual(entradas[ONTEM].findtext(NS + "title"), "INFOCENARIUM %s · nível 1 ROTINA" % data_br(ONTEM))

    # --- endereço base ---
    def _endereco(self, raiz, dia=DIA):
        return self.entradas(raiz)[dia].findtext(NS + "id")

    def test_base_sem_nada_e_ponto_barra(self):
        """CONTRATO, seção 4.5, "Endereço base", o último da ordem: "por último `./`"."""
        raiz, _ = self._publica()
        self.assertEqual(self._endereco(raiz), "./#/edicao/%s" % DIA)

    def test_base_vem_do_git_remote(self):
        """CONTRATO, seção 4.5, "Endereço base": "o derivado de `git remote get-url origin` (`…/DONO/REPO`
        vira `https://DONO.github.io/REPO/`)"."""
        raiz, t, _ = self.cenario(com_git=True)
        apoio.git(raiz, "remote", "add", "origin", "https://github.com/dono-de-exemplo/INFOCENARIUM")
        self.passou(self.edicao(raiz, t))
        self.assertEqual(self._endereco(raiz), "https://dono-de-exemplo.github.io/INFOCENARIUM/#/edicao/%s" % DIA)

    def test_base_do_feed_existente_vale_mais_que_o_git_remote(self):
        """CONTRATO, seção 4.5, "Endereço base, nesta ordem": "`--url-base`; o que já está no `feed.xml`
        existente; o derivado de `git remote get-url origin`". O feed de ontem foi gravado com
        `--url-base`; a edição de hoje sai sem a opção, numa raiz com `origin`."""
        ontem = troca_titulos(monta_edicao(ONTEM), 0)
        raiz, t, _ = self.cenario(ontem, com_git=True)
        apoio.git(raiz, "remote", "add", "origin", "https://github.com/dono-de-exemplo/INFOCENARIUM")
        self.passou(self.edicao(raiz, t, "--url-base", BASE))
        apoio.commita(raiz, "edição %s" % ONTEM)
        t2 = apoio.Trabalho(self.pasta("trabalho"), monta_edicao(DIA, anterior=ontem, rica=True)).grava()
        self.passou(self.edicao(raiz, t2))
        self.assertEqual(self._endereco(raiz, DIA), "%s#/edicao/%s" % (BASE, DIA))
        self.assertEqual(self._endereco(raiz, ONTEM), "%s#/edicao/%s" % (BASE, ONTEM))

    def test_base_da_opcao_vale_mais_que_o_feed_existente(self):
        """CONTRATO, seção 4.5, "Endereço base, nesta ordem": "`--url-base`" vem primeiro. O feed de ontem
        saiu com um endereço; a edição de hoje pede outro."""
        ontem = troca_titulos(monta_edicao(ONTEM), 0)
        raiz, t, _ = self.cenario(ontem)
        self.passou(self.edicao(raiz, t, "--url-base", "https://antigo.exemplo.invalid/INFOCENARIUM/"))
        t2 = apoio.Trabalho(self.pasta("trabalho"), monta_edicao(DIA, anterior=ontem, rica=True)).grava()
        self.passou(self.edicao(raiz, t2, "--url-base", BASE))
        self.assertEqual(self._endereco(raiz, DIA), "%s#/edicao/%s" % (BASE, DIA))
        self.assertEqual(self._endereco(raiz, ONTEM), "%s#/edicao/%s" % (BASE, ONTEM))

    def test_base_no_refaz(self):
        """CONTRATO, seção 4: `publica.py refaz [--url-base URL]`; seção 4.5, "Endereço base"."""
        raiz = self.nova_raiz([monta_edicao(DIA)], derivados=False)
        self.passou(self.publica("refaz", "--url-base", BASE, raiz=raiz))
        self.assertEqual(self._endereco(raiz), "%s#/edicao/%s" % (BASE, DIA))


if __name__ == "__main__":
    unittest.main()
