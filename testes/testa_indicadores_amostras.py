#!/usr/bin/env python3
"""Testes de ferramentas/indicadores.py com as respostas de verdade colhidas em 23/11/2026 (CONTRATO, seção 2).

Três partes:
- os avisos da tabela de leitores: cada coisa que a resposta real tem e que um leitor ingênuo erraria
  (BOM e linhas de vírgulas na FAO, feriado vazio no FRED, null e carimbo de hora no Yahoo, dia sem pregão no
  Banco Central, ordem e texto na EIA);
- o leitor cnbc_chart, segunda fonte dos grãos, do petróleo, do gás e do ouro: a conferência que pôs cada
  endereço no catálogo (o último fechamento bate com a outra fonte) e a conta quando o Yahoo falha;
- a troca de contrato, com os números reais de 23/11/2026: o Yahoo passou trigo e milho de dezembro para
  março nesse dia, e a soja de novembro para janeiro em 16/11.

Rodar da raiz do repositório: python3 -B testes/testa_indicadores_amostras.py
As amostras estão em testes/fixtures/indicadores/ (o LEIA.md de lá diz de onde veio cada número).
"""
import datetime
import json
import os
import shutil
import sys
import unittest

sys.dont_write_bytecode = True
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from testa_indicadores import AMOSTRAS, Caso, DADOS, indicadores  # noqa: E402

CONTRATOS = os.path.join(AQUI, "fixtures", "indicadores", "contratos")
DIA, AGORA = "2026-11-23", "2026-11-23T21:07:00Z"
TRIGO, MILHO, SOJA = 0.3674371, 0.3936826, 0.3674371


def bruto(pasta, nome):
    with open(os.path.join(pasta, nome), "rb") as arquivo:
        return arquivo.read()


def serie(leitor, nome, fator=1.0, dia=DIA, pasta=AMOSTRAS):
    return indicadores.serie(leitor, bruto(pasta, nome), fator, dia)


def catalogo_congelado():
    with open(os.path.join(DADOS, "indicadores.json"), encoding="utf-8") as arquivo:
        return dict((i["id"], i) for i in json.load(arquivo)["indicadores"])


class AvisosDaTabelaDeLeitores(unittest.TestCase):
    """CONTRATO, seção 2, tabela de leitores: o que as respostas reais têm (uma amostra para cada aviso)."""

    def test_fao_csv_com_bom_linha_so_de_virgulas_e_virgulas_no_fim(self):
        corpo = bruto(AMOSTRAS, "fao_ffpi.fao_csv.csv")
        linhas = corpo.decode("utf-8").split("\r\n")
        self.assertTrue(corpo.startswith("﻿FAO Food Price Index".encode("utf-8")))  # o BOM do arquivo real
        self.assertEqual(linhas[3], ",,,,,,,,,")  # a linha só de vírgulas, logo abaixo do cabeçalho
        self.assertTrue(all(linha.endswith(",,,,,,,,,") for linha in linhas if linha))
        pontos = serie("fao_csv", "fao_ffpi.fao_csv.csv")
        self.assertEqual((len(pontos), pontos[0], pontos[-1]), (22, ("1990-01-01", 64.4), ("2026-10-01", 133.9)))
        # Sem o BOM e com fim de linha LF, a leitura é a mesma.
        sem_bom = corpo.decode("utf-8-sig").replace("\r\n", "\n").encode("utf-8")
        self.assertEqual(indicadores.serie("fao_csv", sem_bom, 1.0, DIA), pontos)

    def test_fred_csv_feriado_com_valor_vazio(self):
        corpo = bruto(AMOSTRAS, "usd_brl.fred_csv.csv")
        self.assertIn(b"\n2026-11-11,\n", corpo)  # feriado nos EUA: valor vazio, e não ponto
        self.assertTrue(corpo.endswith(b"\n") and b"\r" not in corpo)
        pontos = dict(serie("fred_csv", "usd_brl.fred_csv.csv"))
        self.assertNotIn("2026-11-11", pontos)
        self.assertEqual((len(pontos), pontos["2026-11-13"]), (30, 5.6449))

    def test_yahoo_chart_fechamento_null_de_verdade(self):
        objeto = json.loads(bruto(AMOSTRAS, "dxy.yahoo_chart.json"))
        fechamentos = objeto["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        self.assertEqual((len(fechamentos), fechamentos.count(None)), (27, 5))
        pontos = serie("yahoo_chart", "dxy.yahoo_chart.json")
        self.assertEqual(len(pontos), 22)
        self.assertNotIn("2026-11-22", dict(pontos))  # o domingo que veio com null

    def test_yahoo_chart_ultimo_carimbo_e_a_hora_da_cotacao(self):
        objeto = json.loads(bruto(AMOSTRAS, "usd_brl.yahoo_chart.json"))
        self.assertEqual(objeto["chart"]["result"][0]["timestamp"][-1], 1795456107)  # 23/11, 17:48:27 UTC
        pontos = serie("yahoo_chart", "usd_brl.yahoo_chart.json")
        self.assertEqual([data for data, _ in pontos].count("2026-11-23"), 1)
        self.assertEqual((pontos[-1][0], round(pontos[-1][1], 4)), ("2026-11-23", 5.9982))

    def test_yahoo_chart_dolar_datado_pelo_relogio_de_londres(self):
        # 1792710000 é 22/10 23:00 UTC: meia-noite de 23/10 em Londres, no horário de verão inglês.
        pontos = serie("yahoo_chart", "usd_brl.yahoo_chart.json")
        self.assertEqual(pontos[0][0], "2026-10-23")
        self.assertNotIn("2026-10-22", dict(pontos))

    def test_yahoo_chart_grao_em_centavos(self):
        objeto = json.loads(bruto(AMOSTRAS, "trigo.yahoo_chart.json"))
        self.assertEqual(objeto["chart"]["result"][0]["meta"]["currency"], "USX")
        self.assertEqual(round(serie("yahoo_chart", "trigo.yahoo_chart.json", TRIGO)[-1][1], 1), 218.3)

    def test_bcb_sgs_dia_sem_pregao_nao_vem(self):
        pontos = dict(serie("bcb_sgs", "usd_brl.bcb_sgs.json"))
        self.assertEqual(len(pontos), 20)  # ultimos/20: o teto do Banco Central
        for feriado in ("2026-11-02", "2026-11-20"):
            self.assertNotIn(feriado, pontos)
        medida = indicadores.mede(sorted(pontos.items()), False)
        self.assertEqual((medida["base_7d"], medida["7d"]), ("2026-11-16", 4.2))  # 5,9708 sobre 5,7324

    def test_eia_v2_warnings_antes_texto_sem_zero_e_do_mais_novo_para_o_mais_velho(self):
        texto = bruto(AMOSTRAS, "brent.eia_v2.json").decode("utf-8")
        self.assertLess(texto.index('"warnings"'), texto.index('"response"'))
        self.assertIn('"92.9"', texto)
        objeto = json.loads(texto)
        periodos = [item["period"] for item in objeto["response"]["data"]]
        self.assertEqual(periodos, sorted(periodos, reverse=True))
        pontos = serie("eia_v2", "brent.eia_v2.json")
        self.assertEqual([data for data, _ in pontos], sorted(periodos))
        self.assertEqual(dict(pontos)["2026-11-16"], 92.9)


class LeitorCnbc(Caso):
    """CONTRATO, seção 2, leitor cnbc_chart, e a conferência que pôs cada endereço da CNBC no catálogo."""

    def test_le_as_amostras(self):
        milho = serie("cnbc_chart", "milho.cnbc_chart.json", MILHO)
        self.assertEqual((len(milho), milho[0][0], milho[-1][0], round(milho[-1][1], 2)),
                         (15, "2026-11-02", "2026-11-20", 176.67))  # 448,75 centavos por bushel × 0,3936826
        self.assertEqual(serie("cnbc_chart", "ouro.cnbc_chart.json")[-1], ("2026-11-20", 3515.4))

    def test_o_ultimo_fechamento_bate_com_a_outra_fonte(self):
        """O critério do catálogo: só entrou o endereço cujo último fechamento bate com o da outra fonte."""
        for ident in ("brent", "wti", "gas_natural", "ouro", "soja"):
            cnbc = serie("cnbc_chart", ident + ".cnbc_chart.json")
            yahoo = dict(serie("yahoo_chart", ident + ".yahoo_chart.json"))
            data, valor = cnbc[-1]
            self.assertEqual(data, "2026-11-20", ident)
            self.assertTrue(indicadores.perto(valor, yahoo[data]), (ident, valor, yahoo[data]))
            self.assertEqual(round(valor, 2), round(yahoo[data], 2), ident)
        # Trigo e milho: a CNBC já estava no contrato de março em 20/11, e o Yahoo só passou em 23/11. O último
        # fechamento bate com o do mesmo contrato no Yahoo (ZWH27 e ZCH27).
        for ident, contrato in (("trigo", "ZWH27"), ("milho", "ZCH27")):
            cnbc = serie("cnbc_chart", ident + ".cnbc_chart.json")[-1]
            mesmo = dict(serie("yahoo_chart", contrato + ".yahoo_chart.json", pasta=CONTRATOS))
            self.assertEqual(cnbc[1], mesmo["2026-11-20"], ident)
        # No milho, antes da troca da CNBC, as duas séries são o mesmo número dia a dia.
        cnbc, yahoo = dict(serie("cnbc_chart", "milho.cnbc_chart.json")), dict(serie("yahoo_chart", "milho.yahoo_chart.json"))
        self.assertEqual([d for d in cnbc if d < "2026-11-20" and d in yahoo and cnbc[d] != yahoo[d]], [])

    def test_os_graos_tem_segunda_fonte_e_a_cnbc_vem_antes_do_fred(self):
        catalogo = catalogo_congelado()
        for ident in ("trigo", "milho", "soja", "brent", "wti", "gas_natural", "ouro"):
            fontes = catalogo[ident]["fontes"]
            self.assertEqual((fontes[0]["leitor"], fontes[1]["leitor"]), ("yahoo_chart", "cnbc_chart"), ident)
            self.assertEqual(fontes[1].get("fator"), fontes[0].get("fator"), ident)  # o mesmo fator da primeira
        self.assertEqual([f["leitor"] for f in catalogo["brent"]["fontes"]], ["yahoo_chart", "cnbc_chart", "fred_csv"])
        self.assertEqual([f["leitor"] for f in catalogo["dxy"]["fontes"]], ["yahoo_chart"])  # a CNBC dá barra no domingo

    def test_sem_o_yahoo_os_graos_vem_da_cnbc(self):
        with open(os.path.join(AMOSTRAS, "respostas.json"), encoding="utf-8") as arquivo:
            todas = json.load(arquivo)
        mapa = dict((url, nome) for url, nome in todas.items() if "yahoo" not in nome)
        for nome in mapa.values():
            shutil.copy(os.path.join(AMOSTRAS, nome), self.off)
        self.grava(os.path.join(self.off, "respostas.json"), json.dumps(mapa))
        codigo, linhas, objeto = self.roda(dia=DIA, agora=AGORA)
        achado = dict((i["id"], (i["valor"], i["variacao_pct"], i["variacao_7d_pct"], i["data"], i["defasado"],
                                 i["fonte"]["nome"])) for i in objeto["indicadores"])
        # milho: 448,75 × 0,3936826 = 176,67; dia: 448,75 / 439,0 → +2,2; 7 dias (13/11): 448,75 / 445,5 → +0,7
        self.assertEqual(achado["milho"], (176.7, 2.2, 0.7, "2026-11-20", False, "CNBC"))
        # trigo: 592,0 × 0,3674371 = 217,52; dia: 592 / 595 → −0,5; 7 dias (13/11): 592 / 606,75 → −2,4
        self.assertEqual(achado["trigo"], (217.5, -0.5, -2.4, "2026-11-20", False, "CNBC"))
        # soja: 1220,75 × 0,3674371 = 448,55; 7 dias (13/11): 1220,75 / 1231,5 → −0,9
        self.assertEqual(achado["soja"], (448.5, 1.1, -0.9, "2026-11-20", False, "CNBC"))
        self.assertEqual(achado["brent"][:4], (92.57, 0.6, -3.4, "2026-11-20"))  # 7 dias: 92,57 / 95,84 (13/11)
        self.assertEqual((codigo, linhas[-1]), (0, "OK 10 indicadores, 1 gatilho de preço"))  # dxy e frete só têm o Yahoo


class TiqueDaFonte(Caso):
    """CONTRATO, seção 2, passo 4: o caso da revisão de 24/11/2026, com a amostra real do Brent no Yahoo e o
    fechamento de 16/11 com o decimal deslocado (92,44 que vira 9,244). Antes, isso dava +844,4% em 7 dias e
    gatilho de energia; agora a variação de 7 dias fica sem base, com aviso."""

    def test_decimal_deslocado_na_base_de_7_dias_nao_vira_gatilho(self):
        with open(os.path.join(AMOSTRAS, "respostas.json"), encoding="utf-8") as arquivo:
            mapa = json.load(arquivo)
        for nome in mapa.values():
            shutil.copy(os.path.join(AMOSTRAS, nome), self.off)
        self.grava(os.path.join(self.off, "respostas.json"), json.dumps(mapa))
        caminho = os.path.join(self.off, "brent.yahoo_chart.json")
        with open(caminho, encoding="utf-8") as arquivo:
            objeto = json.load(arquivo)
        resultado = objeto["chart"]["result"][0]
        mudados = 0
        for indice, carimbo in enumerate(resultado["timestamp"]):
            if datetime.datetime.fromtimestamp(carimbo, datetime.timezone.utc).date().isoformat() == "2026-11-16":
                self.assertEqual(round(resultado["indicators"]["quote"][0]["close"][indice], 2), 92.44)
                resultado["indicators"]["quote"][0]["close"][indice] = 9.244
                mudados += 1
        self.assertEqual(mudados, 1)
        self.grava(caminho, json.dumps(objeto))
        codigo, linhas, objeto = self.roda(dia=DIA, agora=AGORA)
        brent = self.um(objeto, "brent")
        self.assertEqual((brent["valor"], brent["variacao_pct"], brent["variacao_7d_pct"]), (87.3, -5.7, None))
        self.assertNotIn("brent", [g["ref"] for g in objeto["gatilhos"]])
        self.assertEqual(objeto["avisos"], ["brent: ponto de 16/11 fora da série: variação de 7 dias sem base."])
        self.assertEqual((codigo, linhas[-1]), (3, "PARCIAL sem base de 7 dias: brent"))


class TrocaDeContrato(Caso):
    """CONTRATO, seção 2, "Troca de contrato", com os números reais de 23/11/2026 (CONFERENCIA do catálogo)."""

    def monta(self, sem=(), muda=None, **entradas):
        """Pasta do --offline com as amostras do dia e os contratos com data (ZCH27, ZWH27, ZSF27)."""
        with open(os.path.join(AMOSTRAS, "respostas.json"), encoding="utf-8") as arquivo:
            mapa = json.load(arquivo)
        with open(os.path.join(CONTRATOS, "respostas.json"), encoding="utf-8") as arquivo:
            contratos = json.load(arquivo)
        for pasta, nomes in ((AMOSTRAS, mapa.values()), (CONTRATOS, contratos.values())):
            for nome in nomes:
                shutil.copy(os.path.join(pasta, nome), self.off)
        for url, nome in contratos.items():
            if not any(codigo in nome for codigo in sem):
                mapa[url] = entradas.get(nome[:5], nome)
        if muda:
            muda(self.off)
        self.grava(os.path.join(self.off, "respostas.json"), json.dumps(mapa))

    def mede(self, *opcoes, dia=DIA, agora=AGORA):
        codigo, linhas, objeto = self.roda(*opcoes, dia=dia, agora=agora)
        achado = dict((i["id"], (i["valor"], i["variacao_pct"], i["variacao_7d_pct"], i["data"]))
                      for i in objeto["indicadores"])
        return codigo, linhas, objeto, achado

    def test_troca_dentro_da_janela(self):
        """23/11: o Yahoo passou trigo e milho para o contrato de março. As variações saem do contrato."""
        self.monta()
        codigo, linhas, objeto, achado = self.mede()
        # milho no contrato: dia 450,0 / 448,75 → +0,3; 7 dias (16/11) 450,0 / 459,0 → −2,0 (na série: +3,6 e +0,3)
        self.assertEqual(achado["milho"], (177.2, 0.3, -2.0, DIA))
        # trigo no contrato: dia 593,75 / 592,0 → +0,3; 7 dias (16/11) 593,75 / 601,0 → −1,2 (na série: +3,5 e +1,2)
        self.assertEqual(achado["trigo"], (218.3, 0.3, -1.2, DIA))
        self.assertEqual(objeto["avisos"], [
            "trigo: variações medidas no contrato H27, porque a série trocou de contrato em 23/11.",
            "milho: variações medidas no contrato H27, porque a série trocou de contrato em 23/11."])
        self.assertEqual(self.um(objeto, "milho")["fonte"]["nome"], "Yahoo Finance")  # valor, data e fonte não mudam
        self.assertEqual((codigo, linhas[-1]), (0, "OK 12 indicadores, 1 gatilho de preço"))

    def test_troca_fora_da_janela(self):
        """23/11: a soja trocou em 16/11 (de 1243,0 no contrato de novembro para o de janeiro). Os dois pontos de
        base (20/11 e 16/11) já são do contrato de janeiro: nada muda."""
        self.monta()
        codigo, linhas, objeto, achado = self.mede()
        self.assertEqual(achado["soja"], (451.1, 0.6, -0.1, DIA))  # 1227,75 / 1220,75 e 1227,75 / 1229,0
        self.assertFalse([aviso for aviso in objeto["avisos"] if aviso.startswith("soja")])

    def test_a_mesma_troca_dentro_da_janela_na_sexta(self):
        """20/11: a base de 7 dias da soja é 13/11, ainda no contrato de novembro. O degrau era para baixo:
        na série, −1,8% (1220,75 / 1243,0); no contrato de janeiro, −0,9% (1220,75 / 1231,5)."""
        self.monta()
        codigo, linhas, objeto, achado = self.mede(dia="2026-11-20", agora="2026-11-20T21:07:00Z")
        self.assertEqual(achado["soja"][1:], (1.1, -0.9, "2026-11-20"))
        self.assertIn("soja: variações medidas no contrato F27, porque a série trocou de contrato em 16/11.",
                      objeto["avisos"])

    def test_nenhum_candidato_casa(self):
        """20/11: o Yahoo ainda estava no contrato de dezembro (milho 434,5); o de março fechou em 448,75, 3,3%
        acima. Dezembro (Z26) não responde, e nenhum candidato casa: as variações vêm da série."""
        self.monta()
        codigo, linhas, objeto, achado = self.mede(dia="2026-11-20", agora="2026-11-20T21:07:00Z")
        # na série: dia 434,5 / 439,0 → −1,0; 7 dias (13/11) 434,5 / 445,5 → −2,5
        self.assertEqual(achado["milho"][1:], (-1.0, -2.5, "2026-11-20"))
        self.assertFalse([aviso for aviso in objeto["avisos"] if aviso.startswith(("milho", "trigo"))])
        self.assertTrue([linha for linha in linhas if linha.startswith("aviso: milho")
                         and "nenhum contrato casou com a série" in linha], linhas)

    def test_candidato_sem_ponto_de_base(self):
        """O contrato de março casa, mas a resposta dele começa em 17/11: falta o ponto de base de 7 dias (16/11).
        Nada muda, e a saída diz o porquê."""
        def corta(pasta):
            caminho = os.path.join(pasta, "ZCH27.yahoo_chart.json")
            with open(caminho, encoding="utf-8") as arquivo:
                objeto = json.load(arquivo)
            resultado = objeto["chart"]["result"][0]
            resultado["timestamp"] = resultado["timestamp"][-5:]
            resultado["indicators"]["quote"][0]["close"] = resultado["indicators"]["quote"][0]["close"][-5:]
            self.grava(caminho, json.dumps(objeto))
        self.monta(muda=corta)
        codigo, linhas, objeto, achado = self.mede()
        self.assertEqual(achado["milho"], (177.2, 3.6, 0.3, DIA))  # a série do catálogo: 450,0 / 434,5 e 450,0 / 448,75
        self.assertEqual(achado["trigo"], (218.3, 0.3, -1.2, DIA))  # o trigo segue no contrato
        self.assertFalse([aviso for aviso in objeto["avisos"] if aviso.startswith("milho")])
        self.assertTrue([linha for linha in linhas if "contrato H27: o contrato não tem os pontos de base" in linha])

    def test_tempo_esgotado(self):
        """O contrato de março do milho demora mais que o teto do --tempo: nada muda."""
        self.monta(ZCH27={"arquivo": "ZCH27.yahoo_chart.json", "demora": 5})
        codigo, linhas, objeto, achado = self.mede("--tempo", "2")
        self.assertEqual(achado["milho"], (177.2, 3.6, 0.3, DIA))
        self.assertTrue([linha for linha in linhas if linha.startswith("aviso: milho") and "contrato H27: não coube no tempo"
                         in linha], linhas)
        self.assertFalse([aviso for aviso in objeto["avisos"] if aviso.startswith("milho")])

    def test_sem_os_contratos_nada_muda(self):
        self.monta(sem=("ZCH27", "ZWH27", "ZSF27"))
        codigo, linhas, objeto, achado = self.mede()
        self.assertEqual((achado["milho"], achado["trigo"], objeto["avisos"]),
                         ((177.2, 3.6, 0.3, DIA), (218.3, 3.5, 1.2, DIA), []))


if __name__ == "__main__":
    unittest.main()
