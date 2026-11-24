#!/usr/bin/env python3
"""Testes de contrato de indicadores.py: preços e gatilhos de preço (CONTRATO, seções 0 e 2).

Escritos só a partir do contrato, sem ler o código. Cada teste cita, na docstring, a cláusula que
confere. Nenhum teste daqui leva mais a marca INTERPRETACAO: a leitura que cada um escolhia virou frase do
CONTRATO, seção 2, na conciliação de 23/11/2026, e a docstring cita a frase.

As séries são escritas à mão, e a conta de cada valor esperado está no comentário ao lado.
O dia dos testes é 20/11/2026, uma sexta-feira (13/11 é a sexta anterior: 7 dias antes).
Os limiares vêm da régua da fixture: brent, trigo, milho e soja em 7 dias (5%, 10%, 20% para os
níveis 2, 3 e 4); usd_brl no dia (1,5%, 3%, 5%) e em 7 dias (3%, 6%, 10%).

    python3 -B testes/contrato/rede/testa_contrato_indicadores.py
"""
import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location("apoio_contrato_rede", Path(__file__).resolve().parent / "apoio.py")
apoio = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = apoio
_spec.loader.exec_module(apoio)

SEM_CONFIRMACAO = "Alta maior sem confirmação de segunda fonte."
CHAVES_DO_INDICADOR = ["id", "nome", "dominio", "valor", "unidade", "variacao_pct", "variacao_7d_pct", "data",
                       "defasado", "confirmado", "fonte"]
OBRIGATORIOS = ("brent", "trigo", "milho", "soja", "usd_brl")


def cnbc_chart(serie):
    """JSON do leitor cnbc_chart: barData.priceBars[], com tradeTime (texto AAAAMMDDhhmmss) e close (texto)."""
    barras = [{"open": "0", "close": None if v is None else "%.4f" % float(v), "volume": 1,
               "tradeTime": d.replace("-", "") + "000000"} for d, v in serie]
    return json.dumps({"barData": {"symbol": "1", "companyName": "Exemplo (Jan'27)", "exchange": None,
                                   "priceBars": barras}, "requestDetails": {"symbol": "@EX.1"}})


def yahoo_no_fuso(serie, meta):
    """JSON do leitor yahoo_chart com os carimbos exatos (data-hora UTC) e o `meta` dado."""
    carimbos = [int(apoio.instante(quando).timestamp()) for quando, _ in serie]
    return json.dumps({"chart": {"result": [{"meta": meta, "timestamp": carimbos,
                                             "indicators": {"quote": [{"close": [v for _, v in serie]}]}}],
                                 "error": None}})


class CasoIndicadores(apoio.Caso):
    """Parte do cenário pronto (fixtures/offline): todas as fontes respondem, sem alta nenhuma."""

    def setUp(self):
        super().setUp()
        self.b.usa_cenario("offline")

    def nova(self, agora=apoio.AGORA):
        self.b = apoio.Bancada(agora)
        self.addCleanup(self.b.fecha)
        self.b.usa_cenario("offline")
        return self.b

    # --- catálogo ---

    def indicador_do_catalogo(self, ident):
        return next(i for i in self.b.le_dados("indicadores.json")["indicadores"] if i["id"] == ident)

    def fonte(self, ident, numero=0):
        return self.indicador_do_catalogo(ident)["fontes"][numero]

    def muda_indicador(self, ident, **campos):
        catalogo = self.b.le_dados("indicadores.json")
        next(i for i in catalogo["indicadores"] if i["id"] == ident).update(campos)
        self.b.grava_dados("indicadores.json", catalogo)

    def muda_fonte(self, ident, numero, **campos):
        fontes = self.indicador_do_catalogo(ident)["fontes"]
        fontes[numero].update(campos)
        self.muda_indicador(ident, fontes=fontes)

    # --- respostas ---

    def poe(self, ident, numero, serie, **resposta):
        """Troca a resposta da fonte `numero` do indicador pela série dada, no formato do leitor dela."""
        fonte = self.fonte(ident, numero)
        self.b.responde(fonte["url"], apoio.LEITORES[fonte["leitor"]](serie), **resposta)

    def poe_cru(self, ident, numero, corpo, **resposta):
        self.b.responde(self.fonte(ident, numero)["url"], corpo, **resposta)

    def tira(self, ident, *numeros):
        """Tira a resposta das fontes citadas (sem número: de todas). URL ausente é erro de rede."""
        fontes = self.indicador_do_catalogo(ident)["fontes"]
        for numero in (numeros or range(len(fontes))):
            self.b.sem_resposta(fontes[numero]["url"])

    def so(self, ident, serie):
        """Só a 1ª fonte do indicador responde, com a série dada."""
        self.tira(ident)
        self.poe(ident, 0, serie)

    # --- execução e leitura ---

    def roda(self, *args, dia=apoio.DIA, **opcoes):
        return self.b.roda("indicadores", "--dia", dia, *args, **opcoes)

    def dados(self, res):
        d = self.json_gravado(res, "indicadores.json")
        self.assertIsInstance(d, dict, "indicadores.json devia ser um objeto")
        for chave in ("indicadores", "gatilhos", "falhas"):
            self.assertIn(chave, d, "indicadores.json sem a chave %s" % chave + res.relato())
        return d

    def roda_e_le(self, *args, **opcoes):
        res = self.roda(*args, **opcoes)
        return res, self.dados(res)

    def ind(self, d, ident):
        achados = [i for i in d["indicadores"] if i.get("id") == ident]
        self.assertEqual(len(achados), 1, "indicadores.json devia ter um item %s" % ident)
        return achados[0]

    def gatilhos(self, d, ident):
        return [g for g in d["gatilhos"] if g.get("ref") == ident]

    def confere(self, d, ident, **esperado):
        """Compara campos do indicador. `fonte=N` quer dizer: a fonte de número N do catálogo."""
        item = self.ind(d, ident)
        for campo, valor in esperado.items():
            if campo == "fonte":  # só nome e url: as chaves exatas de `fonte` são conferidas no teste de formato
                do_catalogo = self.fonte(ident, valor)
                self.assertEqual((item["fonte"].get("nome"), item["fonte"].get("url")),
                                 (do_catalogo["nome"], do_catalogo["url"]), "%s.fonte" % ident)
            elif valor is None or isinstance(valor, bool):
                self.assertIs(item[campo], valor, "%s.%s é %r" % (ident, campo, item[campo]))
            else:
                self.assertEqual(item[campo], valor, "%s.%s" % (ident, campo))
        return item

    def confere_gatilho(self, d, ident, criterio, data_da_cotacao=None, sem_confirmacao=False):
        """Um gatilho só para o indicador, com o critério dado. Com `data_da_cotacao`, ela tem de estar no texto."""
        achados = self.gatilhos(d, ident)
        self.assertEqual(len(achados), 1, "esperava um gatilho de %s; vieram: %s" % (ident, d["gatilhos"]))
        g = achados[0]
        self.assertEqual(g["criterio"], criterio)
        self.assertIsInstance(g["texto"], str)
        if data_da_cotacao:
            self.assertIn(data_da_cotacao, g["texto"], "o texto do gatilho traz sempre a data da cotação")
        if sem_confirmacao:
            self.assertTrue(g["texto"].endswith(SEM_CONFIRMACAO), g["texto"])
        else:
            self.assertFalse(g["texto"].endswith(SEM_CONFIRMACAO), g["texto"])
        return g


# ---------------------------------------------------------------------------------------------
# Os cinco leitores
# ---------------------------------------------------------------------------------------------

class Leitores(CasoIndicadores):

    def test_yahoo_chart_bem_formado(self):
        """CONTRATO, seção 2, leitor `yahoo_chart`: «em `chart.result[0]`: `timestamp[]` (segundos Unix; a data é a
        do dia em UTC) e `indicators.quote[0].close[]`».

        brent, 1ª fonte da fixture: 74.05 em 20/11, 73.40 em 19/11, 71.20 em 13/11.
        """
        res, d = self.roda_e_le()
        # dia: 74.05 / 73.40 = 1.008856 → +0,9
        # 7 dias: o ponto mais novo entre 10/11 e 13/11 é o de 13/11: 74.05 / 71.20 = 1.040028 → +4,0
        self.confere(d, "brent", valor=74.05, variacao_pct=0.9, variacao_7d_pct=4.0, data="2026-11-20",
                     defasado=False, confirmado=False, fonte=0)

    def test_yahoo_chart_pula_par_com_close_null(self):
        """CONTRATO, seção 2, leitor `yahoo_chart`: «par com `close` `null` é pulado».

        Resposta escrita à mão, com null no meio e no fim da lista de fechamentos.
        """
        carimbo = lambda dia: int(apoio.instante(dia + "T14:30:00Z").timestamp())
        corpo = json.dumps({"chart": {"result": [{
            "meta": {"currency": "USD", "symbol": "EXEMPLO=F"},
            "timestamp": [carimbo("2026-11-12"), carimbo("2026-11-13"), carimbo("2026-11-17"), carimbo("2026-11-18"),
                          carimbo("2026-11-19"), carimbo("2026-11-20")],
            "indicators": {"quote": [{"close": [70.00, 70.50, None, 71.00, 72.00, None]}]}}], "error": None}})
        self.tira("brent")
        self.poe_cru("brent", 0, corpo)
        res, d = self.roda_e_le()
        # sobram 12/11 70.00, 13/11 70.50, 18/11 71.00, 19/11 72.00; o último é o de 19/11
        # dia: 72.00 / 71.00 = 1.014085 → +1,4
        # 7 dias antes de 19/11 é 12/11: 72.00 / 70.00 = 1.028571 → +2,9
        self.confere(d, "brent", valor=72.0, variacao_pct=1.4, variacao_7d_pct=2.9, data="2026-11-19", defasado=False)

    def test_yahoo_chart_a_data_e_o_dia_em_utc(self):
        """CONTRATO, seção 2, leitor `yahoo_chart`: «A data é o dia do carimbo no fuso da bolsa: […] sem os dois, o
        dia em UTC.» (A resposta da fixture não traz `exchangeTimezoneName` nem `gmtoffset`.)

        Dois casos, com o fuso da máquina trocado pela variável TZ: carimbo de 20/11 à 01:00 UTC lido
        numa máquina em São Paulo (lá ainda é 19/11) tem data 2026-11-20; carimbo de 19/11 às 23:00 UTC
        lido numa máquina em Tóquio (lá já é 20/11) tem data 2026-11-19.
        """
        casos = (("America/Sao_Paulo", "T01:00:00Z", "2026-11-20"), ("Asia/Tokyo", "T23:00:00Z", "2026-11-19"))
        for fuso, hora, esperada in casos:
            with self.subTest(fuso=fuso):
                self.nova()
                ultimo = "2026-11-20" if esperada == "2026-11-20" else "2026-11-19"
                anterior = apoio.dia_mais(ultimo, -1)
                base = apoio.dia_mais(ultimo, -7)
                self.so("brent", [(base + hora, 70.00), (anterior + hora, 71.20), (ultimo + hora, 72.10)])
                res, d = self.roda_e_le(ambiente={"TZ": fuso})
                # dia: 72.10 / 71.20 = 1.012640 → +1,3 ; 7 dias: 72.10 / 70.00 = 1.03 → +3,0
                self.confere(d, "brent", valor=72.1, data=esperada, variacao_pct=1.3, variacao_7d_pct=3.0)

    def test_yahoo_chart_a_data_e_o_dia_no_fuso_da_bolsa(self):
        """CONTRATO, seção 2, leitor `yahoo_chart`: «A data é o dia do carimbo no fuso da bolsa:
        `meta.exchangeTimezoneName`, pela base de fusos da máquina; sem esse campo […], o desvio fixo
        `meta.gmtoffset` (segundos); sem os dois, o dia em UTC.»

        Barras carimbadas às 23:00 UTC, como o Yahoo carimba o dólar à meia-noite de Londres no verão inglês
        (outubro). Com `Europe/London`, cada barra é do dia seguinte ao do UTC; só com `gmtoffset` 3600, também;
        com `America/New_York`, é o dia do UTC.
        """
        serie = [("2026-10-12T23:00:00Z", 70.00), ("2026-10-15T23:00:00Z", 71.00), ("2026-10-19T23:00:00Z", 72.10)]
        casos = (({"exchangeTimezoneName": "Europe/London", "gmtoffset": 0}, "2026-10-20", 7.0),
                 ({"gmtoffset": 3600}, "2026-10-20", 7.0),
                 ({"exchangeTimezoneName": "America/New_York", "gmtoffset": -14400}, "2026-10-19", 7.0))
        for meta, esperada, dias in casos:
            with self.subTest(meta=meta):
                self.nova("2026-10-20T21:00:00Z")
                self.tira("brent")
                self.poe_cru("brent", 0, yahoo_no_fuso(serie, meta))
                res, d = self.roda_e_le(dia="2026-10-20")
                # dia: 72.10 / 71.00 = 1.015493 → +1,5 ; 7 dias (de 12/10 a 19/10, ou de 13/10 a 20/10): 72.10 / 70.00 → +3,0
                self.confere(d, "brent", valor=72.1, data=esperada, variacao_pct=1.5, variacao_7d_pct=3.0)

    def test_cnbc_chart_bem_formado(self):
        """CONTRATO, seção 2, leitor `cnbc_chart`: «em `barData.priceBars[]`: a data são os 8 primeiros caracteres de
        `tradeTime` […] e o valor é `close`, que vem como texto (`"448.7500"`) e pode vir como número. Barra sem um
        dos dois é pulada».

        A 2ª fonte do brent passa a ser cnbc_chart; a 1ª não responde. A série tem uma barra sem `close` e uma
        sem `tradeTime`, e um `close` como número.
        """
        self.muda_fonte("brent", 1, leitor="cnbc_chart")
        self.tira("brent", 0)
        corpo = json.loads(cnbc_chart([("2026-11-13", 71.20), ("2026-11-18", 99.0), ("2026-11-19", 73.40),
                                       ("2026-11-20", 74.05)]))
        barras = corpo["barData"]["priceBars"]
        del barras[1]["close"]
        barras.insert(0, {"close": "999.0000"})
        barras[-1]["close"] = 74.05
        self.poe_cru("brent", 1, json.dumps(corpo))
        res, d = self.roda_e_le()
        # dia: 74.05 / 73.40 = 1.008856 → +0,9 ; 7 dias: 74.05 / 71.20 = 1.040028 → +4,0
        self.confere(d, "brent", valor=74.05, variacao_pct=0.9, variacao_7d_pct=4.0, data="2026-11-20", fonte=1)

    def test_fred_csv_bem_formado_com_linha_de_ponto(self):
        """CONTRATO, seção 2, leitor `fred_csv`: «cabeçalho `observation_date,ID`; cada linha é `AAAA-MM-DD,valor`;
        linha com valor vazio ou `.` é pulada».

        milho, 1ª fonte da fixture: 4.43 em 20/11, 4.40 em 19/11, 4.35 em 13/11, e "." em 11/11.
        """
        res, d = self.roda_e_le()
        # dia: 4.43 / 4.40 = 1.006818 → +0,7 ; 7 dias (13/11): 4.43 / 4.35 = 1.018391 → +1,8
        self.confere(d, "milho", valor=4.43, variacao_pct=0.7, variacao_7d_pct=1.8, data="2026-11-20", fonte=0)

    def test_fred_csv_pula_linha_vazia_ou_com_ponto(self):
        """CONTRATO, seção 2, leitor `fred_csv`: «linha com valor vazio ou `.` é pulada».

        Resposta escrita à mão: as linhas de 16/11 ("."), 18/11 (vazia) e 20/11 (".") não contam.
        """
        corpo = ("observation_date,MILHO\n"
                 "2026-11-12,4.20\n"
                 "2026-11-13,4.22\n"
                 "2026-11-16,.\n"
                 "2026-11-17,4.25\n"
                 "2026-11-18,\n"
                 "2026-11-19,4.30\n"
                 "2026-11-20,.\n")
        self.tira("milho")
        self.poe_cru("milho", 0, corpo)
        res, d = self.roda_e_le()
        # o último ponto é o de 19/11 (4.30); o anterior é o de 17/11 (4.25): 4.30 / 4.25 = 1.011765 → +1,2
        # 7 dias antes de 19/11 é 12/11 (4.20): 4.30 / 4.20 = 1.023810 → +2,4
        self.confere(d, "milho", valor=4.3, variacao_pct=1.2, variacao_7d_pct=2.4, data="2026-11-19", defasado=False)

    def test_bcb_sgs_bem_formado(self):
        """CONTRATO, seção 2, leitor `bcb_sgs`: «lista de `{"data": "DD/MM/AAAA", "valor": "5.8889"}`».

        usd_brl, 1ª fonte da fixture: 5.4321 em 20/11, 5.4420 em 19/11, 5.4200 em 13/11 (4 casas).
        """
        res, d = self.roda_e_le()
        # dia: 5.4321 / 5.4420 = 0.998181 → −0,2 ; 7 dias (13/11): 5.4321 / 5.4200 = 1.002232 → +0,2
        self.confere(d, "usd_brl", valor=5.4321, variacao_pct=-0.2, variacao_7d_pct=0.2, data="2026-11-20", fonte=0)

    def test_bcb_sgs_ponto_sem_valor_e_descartado(self):
        """CONTRATO, seção 2, passo 2: «Descarta ponto sem valor».

        Resposta do leitor bcb_sgs escrita à mão, com `"valor": ""` no ponto de 20/11: ele é descartado,
        e o último ponto passa a ser o de 19/11.
        """
        corpo = json.dumps([{"data": "12/11/2026", "valor": "5.4000"}, {"data": "18/11/2026", "valor": "5.4000"},
                            {"data": "19/11/2026", "valor": "5.4108"}, {"data": "20/11/2026", "valor": ""}])
        self.tira("usd_brl")
        self.poe_cru("usd_brl", 0, corpo)
        res, d = self.roda_e_le()
        # dia: 5.4108 / 5.4000 = 1.002 → +0,2 ; 7 dias antes de 19/11 é 12/11: também +0,2
        self.confere(d, "usd_brl", valor=5.4108, variacao_pct=0.2, variacao_7d_pct=0.2, data="2026-11-19")

    def test_eia_v2_vem_do_mais_novo_para_o_mais_velho(self):
        """CONTRATO, seção 2, leitor `eia_v2`: «`response.data[]`, com `period` (`AAAA-MM-DD`) e `value` (texto); vem
        do mais novo para o mais velho»; e «devolve a série: pares (data, valor), em ordem crescente de data».

        gas_natural, na fixture: a lista começa por 20/11 (3.12) e termina em 09/11 (2.95). O valor do
        dia é o primeiro item da lista, não o último. O indicador não declara `casas`: valem 2.
        """
        res, d = self.roda_e_le()
        # dia: 3.12 / 3.09 = 1.009709 → +1,0 ; 7 dias (13/11): 3.12 / 3.00 = 1.04 → +4,0
        self.confere(d, "gas_natural", valor=3.12, variacao_pct=1.0, variacao_7d_pct=4.0, data="2026-11-20", fonte=0)

    def test_eia_v2_ponto_sem_valor_e_descartado(self):
        """CONTRATO, seção 2, passo 2: «Descarta ponto sem valor».

        Resposta do leitor eia_v2 escrita à mão, com `"value": null` no ponto mais novo (20/11).
        """
        corpo = json.dumps({"response": {"total": "4", "dateFormat": "YYYY-MM-DD", "frequency": "daily", "data": [
            {"period": "2026-11-20", "value": None, "units": "exemplo"},
            {"period": "2026-11-19", "value": "3.20", "units": "exemplo"},
            {"period": "2026-11-18", "value": "3.10", "units": "exemplo"},
            {"period": "2026-11-12", "value": "3.00", "units": "exemplo"}]}})
        self.poe_cru("gas_natural", 0, corpo)
        res, d = self.roda_e_le()
        # dia: 3.20 / 3.10 = 1.032258 → +3,2 ; 7 dias antes de 19/11 é 12/11: 3.20 / 3.00 = 1.066667 → +6,7
        self.confere(d, "gas_natural", valor=3.2, variacao_pct=3.2, variacao_7d_pct=6.7, data="2026-11-19")

    def test_fao_csv_bem_formado(self):
        """CONTRATO, seção 2, leitor `fao_csv`: «2 linhas de título; depois o cabeçalho `Date,Food Price Index,…`; a
        data é `AAAA-MM` (vira dia 1); lê a 2ª coluna».

        indice_fao, na fixture: 127.3 em 2026-10 e 126.4 em 2026-09 (as outras colunas trazem outros números).
        """
        res, d = self.roda_e_le()
        # mês: 127.3 / 126.4 = 1.007120 → +0,7 ; a data é o dia 1 de outubro
        self.confere(d, "indice_fao", valor=127.3, variacao_pct=0.7, variacao_7d_pct=None, data="2026-10-01", fonte=0)

    def test_fao_csv_pula_linha_sem_valor(self):
        """CONTRATO, seção 2, leitor `fao_csv`: «linha sem valor é pulada».

        Resposta escrita à mão: setembro e novembro vêm com a 2ª coluna vazia.
        """
        corpo = ("Índice de exemplo no formato do índice de preços de alimentos\n"
                 "2014-2016=100\n"
                 "Date,Food Price Index,Meat,Dairy,Cereals,Oils,Sugar\n"
                 "2026-07,124.0,118.0,120.5,110.2,150.3,105.4\n"
                 "2026-08,125.0,118.1,120.6,110.3,150.4,105.5\n"
                 "2026-09,,118.2,120.7,110.4,150.5,105.6\n"
                 "2026-10,126.5,118.3,120.8,110.5,150.6,105.7\n"
                 "2026-11,,118.4,120.9,110.6,150.7,105.8\n")
        self.poe_cru("indice_fao", 0, corpo)
        res, d = self.roda_e_le()
        # o último ponto é outubro (126.5); o anterior é agosto (125.0): 126.5 / 125.0 = 1.012 → +1,2
        self.confere(d, "indice_fao", valor=126.5, variacao_pct=1.2, variacao_7d_pct=None, data="2026-10-01")

    def test_leitor_desconhecido_e_pulado_com_aviso(self):
        """CONTRATO, seção 2: «Leitor que o catálogo cita e o script não conhece: a fonte é pulada, com aviso.»

        A 1ª fonte do milho passa a citar o leitor "leitor_do_futuro". A ferramenta pula essa fonte,
        avisa na saída padrão e usa a 2ª (yahoo_chart em centavos, fator 0.01). Os outros seguem: OK.
        """
        self.muda_fonte("milho", 0, leitor="leitor_do_futuro")
        res, d = self.roda_e_le()
        # 2ª fonte: 444.00 × 0.01 = 4.44 em 20/11 ; 441.00 em 19/11 ; 436.00 em 13/11
        # dia: 444 / 441 = 1.006803 → +0,7 ; 7 dias: 444 / 436 = 1.018349 → +1,8
        self.confere(d, "milho", valor=4.44, variacao_pct=0.7, variacao_7d_pct=1.8, data="2026-11-20", fonte=1)
        self.assertTrue("leitor_do_futuro" in res.saida or re.search(r"aviso", res.saida, re.I),
                        "faltou o aviso do leitor desconhecido" + res.relato())
        self.confere_veredito(res, "OK", 0)

    def test_leitor_desconhecido_na_unica_fonte(self):
        """CONTRATO, seção 2: «a fonte é pulada, com aviso»; passo 6: «Indicador sem fonte que sirva sai com `valor`,
        variações e `data` em `null` […]. Os outros seguem.»

        gas_natural só tem uma fonte; com leitor desconhecido, o indicador sai sem dado e a ferramenta
        não quebra. Como ele não é obrigatório, o veredito continua OK.
        """
        self.muda_fonte("gas_natural", 0, leitor="leitor_do_futuro")
        res, d = self.roda_e_le()
        self.confere(d, "gas_natural", valor=None, data=None, defasado=True, fonte=0)
        self.confere(d, "brent", valor=74.05)
        self.confere_veredito(res, "OK", 0)

    def test_fator_multiplica_o_valor_lido(self):
        """CONTRATO, seção 2, "Leitores": «Cada valor é multiplicado pelo `fator` da fonte, se houver.»

        trigo, 1ª fonte da fixture, entrega centavos e tem fator 0.01: 559.00 vira 5.59.
        """
        res, d = self.roda_e_le()
        # 559.00 × 0.01 = 5.59 ; dia: 559 / 556 = 1.005396 → +0,5 ; 7 dias (13/11): 559 / 548 = 1.020073 → +2,0
        self.confere(d, "trigo", valor=5.59, variacao_pct=0.5, variacao_7d_pct=2.0, data="2026-11-20", fonte=0)

    def test_fator_posto_no_catalogo_muda_o_valor(self):
        """CONTRATO, seção 2, "Leitores": «Cada valor é multiplicado pelo `fator` da fonte, se houver.» ESQUEMA,
        seção 14: `fator`, «sem o campo, 1».

        A 1ª fonte do brent ganha fator 2: 74.05 vira 148.1 (dentro da faixa de 10 a 400). As variações
        não mudam, porque o fator multiplica todos os pontos.
        """
        self.muda_fonte("brent", 0, fator=2)
        res, d = self.roda_e_le()
        # 74.05 × 2 = 148.10 ; dia: 148.10 / 146.80 = 1.008856 → +0,9 ; 7 dias: 148.10 / 142.40 = 1.040028 → +4,0
        self.confere(d, "brent", valor=148.1, variacao_pct=0.9, variacao_7d_pct=4.0, fonte=0)

    def test_a_faixa_vale_depois_do_fator(self):
        """CONTRATO, seção 2: a série que o leitor devolve já vem com «cada valor […] multiplicado pelo `fator`», e
        a fonte serve se «o último valor está dentro da `faixa` do catálogo».

        Dois lados. O trigo da fixture lê 559.00, fora da faixa de 1 a 30, e serve porque 559.00 × 0.01
        = 5.59. E o brent com fator 10 na 1ª fonte dá 740.50, fora da faixa de 10 a 400: essa fonte
        deixa de servir, e o valor vem da 2ª (73.85).
        """
        self.muda_fonte("brent", 0, fator=10)
        res, d = self.roda_e_le()
        self.confere(d, "trigo", valor=5.59, fonte=0)
        self.confere(d, "brent", valor=73.85, fonte=1)

    def test_o_endereco_vem_do_catalogo(self):
        """CONTRATO, seção 2: «O script não traz endereço nenhum: todo endereço mora no catálogo.»

        O endereço da 1ª fonte do brent é trocado no catálogo por outro, inventado, e a resposta muda
        junto. O valor continua vindo dela, e `fonte.url` é o endereço novo.
        """
        antigo = self.fonte("brent", 0)["url"]
        novo = "https://outro-lugar.exemplo.invalid/qualquer/caminho?serie=brent"
        self.b.respostas[novo] = self.b.respostas.pop(antigo)
        self.muda_fonte("brent", 0, url=novo)
        res, d = self.roda_e_le()
        item = self.confere(d, "brent", valor=74.05)
        self.assertEqual(item["fonte"]["url"], novo)


# ---------------------------------------------------------------------------------------------
# Escolha da fonte (passos 1 a 3)
# ---------------------------------------------------------------------------------------------

class EscolhaDaFonte(CasoIndicadores):

    def test_fica_com_a_primeira_fonte_que_serve(self):
        """CONTRATO, seção 2, passo 3: «Fica com a primeira fonte que serve e não está defasada.»

        Na fixture as três fontes do brent servem e estão em dia. Vale a 1ª (74.05), não a 2ª (73.85)
        nem a 3ª (73.95).
        """
        res, d = self.roda_e_le()
        self.confere(d, "brent", valor=74.05, fonte=0)

    def test_fonte_com_erro_de_rede_passa_para_a_seguinte(self):
        """CONTRATO, seção 2, passo 1: «Em cada um, tenta as `fontes` na ordem do catálogo»; seção 0, --offline: «URL
        ausente conta como erro de rede.»

        A 1ª fonte do brent não responde: o valor vem da 2ª (fred_csv).
        """
        self.tira("brent", 0)
        res, d = self.roda_e_le()
        # 2ª fonte: 73.85 em 20/11 ; 73.20 em 19/11 ; 71.05 em 13/11
        # dia: 73.85 / 73.20 = 1.008880 → +0,9 ; 7 dias: 73.85 / 71.05 = 1.039409 → +3,9
        self.confere(d, "brent", valor=73.85, variacao_pct=0.9, variacao_7d_pct=3.9, data="2026-11-20", fonte=1)
        self.confere_veredito(res, "OK", 0)

    def test_fonte_com_status_403_ou_404_passa_para_a_seguinte(self):
        """CONTRATO, seção 0, --offline: «`status` é o código da resposta»; seção 2, passo 1: tenta as fontes na ordem.

        A 1ª fonte responde 403 ou 404 (com um corpo legível, de propósito): não serve; vale a 2ª.
        """
        for status in (403, 404):
            with self.subTest(status=status):
                self.nova()
                self.poe("brent", 0, [("2026-11-19", 73.40), ("2026-11-20", 74.05)], status=status)
                res, d = self.roda_e_le()
                self.confere(d, "brent", valor=73.85, fonte=1)

    def test_resposta_ilegivel_passa_para_a_seguinte(self):
        """CONTRATO, seção 0: «Nunca termina com exceção solta»; seção 2, passo 2: a fonte serve «se sobrou ao menos
        1 ponto».

        A 1ª fonte do brent responde com uma página HTML no lugar do JSON: não dá ponto nenhum. A
        ferramenta não quebra e usa a 2ª.
        """
        self.poe_cru("brent", 0, "<!DOCTYPE html>\n<html><body><p>Serviço em manutenção.</p></body></html>\n",
                     tipo="text/html; charset=utf-8")
        res, d = self.roda_e_le()
        self.confere(d, "brent", valor=73.85, fonte=1)
        self.confere_veredito(res, "OK", 0)

    def test_valor_fora_da_faixa_nao_serve(self):
        """CONTRATO, seção 2, passo 2: «A fonte serve se sobrou ao menos 1 ponto e o último valor está dentro da
        `faixa` do catálogo.» ESQUEMA, seção 14: «valor fora da faixa é recusado».

        A faixa do brent é de 10 a 400. Com o último valor em 900.00 (acima) ou em 5.00 (abaixo), a 1ª
        fonte não serve, e o valor vem da 2ª.
        """
        for ultimo in (900.00, 5.00):
            with self.subTest(ultimo=ultimo):
                self.nova()
                self.poe("brent", 0, [("2026-11-13", 71.20), ("2026-11-19", 73.40), ("2026-11-20", ultimo)])
                res, d = self.roda_e_le()
                self.confere(d, "brent", valor=73.85, fonte=1)

    def test_fonte_sem_ponto_nenhum_nao_serve(self):
        """CONTRATO, seção 2, passo 2: «Descarta ponto sem valor […]. A fonte serve se sobrou ao menos 1 ponto».

        A 1ª fonte do brent responde bem formada, mas com todos os fechamentos em null.
        """
        self.poe("brent", 0, [("2026-11-18", None), ("2026-11-19", None), ("2026-11-20", None)])
        res, d = self.roda_e_le()
        self.confere(d, "brent", valor=73.85, fonte=1)

    def test_fonte_defasada_perde_para_a_seguinte_em_dia(self):
        """CONTRATO, seção 2, passo 3: «Fica com a primeira fonte que serve e não está defasada.»

        A 1ª fonte do brent serve, mas parou em 14/11 (6 dias antes de 20/11: defasada). A 2ª está em
        dia: vale a 2ª, e o indicador não sai defasado.
        """
        self.poe("brent", 0, [("2026-11-06", 70.00), ("2026-11-13", 71.20), ("2026-11-14", 71.50)])
        res, d = self.roda_e_le()
        self.confere(d, "brent", valor=73.85, data="2026-11-20", defasado=False, fonte=1)

    def test_todas_defasadas_fica_a_de_data_mais_nova(self):
        """CONTRATO, seção 2, passo 3: «Se todas as que servem estão defasadas, fica com a de data mais nova.»

        As três fontes do brent pararam: a 1ª em 10/11, a 2ª em 14/11, a 3ª em 12/11. Vale a 2ª, com o
        número e a data dela, e `defasado: true`. Trocando as séries (a 1ª para em 14/11), vale a 1ª.
        """
        velha = [("2026-11-03", 69.00), ("2026-11-09", 70.00), ("2026-11-10", 70.50)]
        nova = [("2026-11-06", 71.00), ("2026-11-13", 72.00), ("2026-11-14", 72.80)]
        media = [("2026-11-05", 70.00), ("2026-11-11", 71.00), ("2026-11-12", 71.30)]
        for ordem, escolhida in (((velha, nova, media), 1), ((nova, velha, media), 0)):
            with self.subTest(escolhida=escolhida):
                self.nova()
                for numero, serie in enumerate(ordem):
                    self.poe("brent", numero, serie)
                res, d = self.roda_e_le()
                # a escolhida é sempre a série "nova": 72.80 em 14/11 ; dia: 72.80 / 72.00 = 1.011111 → +1,1
                self.confere(d, "brent", valor=72.8, variacao_pct=1.1, data="2026-11-14", defasado=True,
                             fonte=escolhida)

    def test_nunca_mistura_pontos_de_duas_fontes(self):
        """CONTRATO, seção 2, passo 3: «Nunca mistura pontos de duas fontes»; passo 4: «Calcula, sempre dentro da
        série da fonte escolhida».

        A 1ª fonte do brent só traz 3 dias (18, 19 e 20/11). É ela a escolhida, e nela não há ponto de 7
        a 10 dias antes: `variacao_7d_pct` é null. A 2ª fonte tem o ponto de 13/11 (71.05), mas ele não
        pode ser usado: daria 81.00 / 71.05 = +14,0 e um gatilho que não existe.
        """
        self.poe("brent", 0, [("2026-11-18", 80.00), ("2026-11-19", 80.50), ("2026-11-20", 81.00)])
        res, d = self.roda_e_le()
        # dia: 81.00 / 80.50 = 1.006211 → +0,6
        self.confere(d, "brent", valor=81.0, variacao_pct=0.6, variacao_7d_pct=None, data="2026-11-20", fonte=0)
        self.assertEqual(self.gatilhos(d, "brent"), [])

    def test_ponto_com_data_depois_do_dia_e_descartado(self):
        """CONTRATO, seção 2, passo 2: «Descarta ponto sem valor e ponto com data depois de `--dia`.»

        Com --dia 2026-11-18, os pontos de 19/11 e 20/11 não existem: o último é o de 18/11. Se
        contassem, o brent fecharia em 95.00, com alta de 35% em 7 dias.
        """
        self.so("brent", [("2026-11-10", 70.00), ("2026-11-11", 70.00), ("2026-11-17", 71.20), ("2026-11-18", 72.10),
                          ("2026-11-19", 90.00), ("2026-11-20", 95.00)])
        res, d = self.roda_e_le(dia="2026-11-18")
        # dia: 72.10 / 71.20 = 1.012640 → +1,3 ; 7 dias antes de 18/11 é 11/11: 72.10 / 70.00 = 1.03 → +3,0
        self.confere(d, "brent", valor=72.1, variacao_pct=1.3, variacao_7d_pct=3.0, data="2026-11-18", defasado=False)
        self.assertEqual(self.gatilhos(d, "brent"), [])
        self.assertEqual(d.get("dia"), "2026-11-18")
        for item in d["indicadores"]:
            if item["data"] is not None:
                self.assertLessEqual(item["data"], "2026-11-18", item["id"])


# ---------------------------------------------------------------------------------------------
# As contas (passo 4)
# ---------------------------------------------------------------------------------------------

class Contas(CasoIndicadores):

    def test_valor_arredondado_a_casas(self):
        """CONTRATO, seção 2, passo 4: «`valor` (último ponto, arredondado a `casas`)». ESQUEMA, seção 14: `casas`,
        «0 a 6: casas decimais de `valor`; sem o campo, 2».

        brent (2 casas): 74.0567 → 74.06. usd_brl (4 casas): 5.43218 → 5.4322. gas_natural (sem o campo:
        2 casas): 3.1234 → 3.12. indice_fao (1 casa): 127.34 → 127.3. Em nenhum a casa cortada é 5.
        """
        self.so("brent", [("2026-11-13", 71.2345), ("2026-11-19", 73.4012), ("2026-11-20", 74.0567)])
        self.so("usd_brl", [("2026-11-13", "5.42003"), ("2026-11-19", "5.44204"), ("2026-11-20", "5.43218")])
        self.so("gas_natural", [("2026-11-13", "3.0012"), ("2026-11-19", "3.0934"), ("2026-11-20", "3.1234")])
        self.so("indice_fao", [("2026-09", "126.42"), ("2026-10", "127.34")])
        res, d = self.roda_e_le()
        self.confere(d, "brent", valor=74.06)
        self.confere(d, "usd_brl", valor=5.4322)
        self.confere(d, "gas_natural", valor=3.12)
        self.confere(d, "indice_fao", valor=127.3)

    def test_casas_zero(self):
        """ESQUEMA, seção 14: `casas`, «0 a 6: casas decimais de `valor`».

        Com `casas: 0` no brent, 74.05 vira 74.
        """
        self.muda_indicador("brent", casas=0)
        res, d = self.roda_e_le()
        self.confere(d, "brent", valor=74)

    def test_variacao_e_sobre_o_ponto_anterior_da_serie(self):
        """CONTRATO, seção 2, passo 4: «`variacao_pct` (último ponto sobre o anterior)». ESQUEMA, seção 3: «variação
        sobre o ponto anterior da série, 1 casa».

        O ponto anterior ao de 20/11 é o de 16/11, quatro dias antes: é ele que conta, e não um "ontem"
        que a série não tem.
        """
        self.so("brent", [("2026-11-10", 70.00), ("2026-11-12", 70.50), ("2026-11-16", 71.00), ("2026-11-20", 72.50)])
        res, d = self.roda_e_le()
        # dia: 72.50 / 71.00 = 1.021127 → +2,1
        # 7 dias: entre 10/11 e 13/11 o ponto mais novo é o de 12/11: 72.50 / 70.50 = 1.028369 → +2,8
        self.confere(d, "brent", valor=72.5, variacao_pct=2.1, variacao_7d_pct=2.8, data="2026-11-20")

    def test_variacao_7d_usa_o_ponto_mais_novo_entre_7_e_10_dias_antes(self):
        """CONTRATO, seção 2, passo 4: «`variacao_7d_pct` (último ponto sobre o ponto mais novo com data de 7 a 10
        dias corridos antes da dele […])».

        Antes de 20/11 a série tem pontos a 10 dias (10/11), 9 (11/11), 8 (12/11) e 6 (14/11); não tem a
        7. O ponto certo é o de 12/11: o mais novo dentro da faixa. O de 14/11 é mais novo, mas está
        fora dela.
        """
        self.so("brent", [("2026-11-10", 60.00), ("2026-11-11", 65.00), ("2026-11-12", 71.00), ("2026-11-14", 72.00),
                          ("2026-11-19", 73.00), ("2026-11-20", 73.50)])
        res, d = self.roda_e_le()
        # 7 dias: 73.50 / 71.00 = 1.035211 → +3,5   (com 14/11 daria +2,1; com 11/11, +13,1; com 10/11, +22,5)
        # dia: 73.50 / 73.00 = 1.006849 → +0,7
        self.confere(d, "brent", valor=73.5, variacao_pct=0.7, variacao_7d_pct=3.5)
        self.assertEqual(self.gatilhos(d, "brent"), [])

    def test_variacao_7d_aceita_as_duas_pontas_da_faixa(self):
        """CONTRATO, seção 2, passo 4: «com data de 7 a 10 dias corridos antes da dele».

        Com um ponto só na faixa: a exatamente 7 dias (13/11), e a exatamente 10 dias (10/11). Nos dois
        casos a variação existe.
        """
        for base in ("2026-11-13", "2026-11-10"):
            with self.subTest(base=base):
                self.nova()
                self.so("brent", [(base, 71.00), ("2026-11-19", 73.00), ("2026-11-20", 73.50)])
                res, d = self.roda_e_le()
                # 73.50 / 71.00 = 1.035211 → +3,5
                self.confere(d, "brent", variacao_7d_pct=3.5)

    def test_variacao_7d_null_sem_ponto_na_faixa(self):
        """CONTRATO, seção 2, passo 4: «sem ponto nessa faixa, `null`».

        A série tem pontos a 11 dias (09/11) e a 6 dias (14/11), nenhum entre 7 e 10. A variação de 7
        dias é null; a do dia existe.
        """
        self.so("brent", [("2026-11-09", 60.00), ("2026-11-14", 72.00), ("2026-11-19", 73.00), ("2026-11-20", 73.50)])
        res, d = self.roda_e_le()
        # dia: 73.50 / 73.00 = 1.006849 → +0,7
        self.confere(d, "brent", valor=73.5, variacao_pct=0.7, variacao_7d_pct=None)

    def test_variacao_7d_conta_a_partir_da_data_da_cotacao(self):
        """CONTRATO, seção 2, passo 4: «7 a 10 dias corridos antes da dele» (da data do último ponto, não de `--dia`).

        A cotação é de 18/11 e o dia é 20/11. A faixa vai de 08/11 a 11/11: o ponto é o de 08/11. O de
        12/11 está a 8 dias de `--dia`, mas a 6 da cotação: não entra.
        """
        self.so("brent", [("2026-11-08", 71.00), ("2026-11-12", 60.00), ("2026-11-17", 73.00), ("2026-11-18", 73.50)])
        res, d = self.roda_e_le()
        # 7 dias: 73.50 / 71.00 = 1.035211 → +3,5   (com o ponto de 12/11 daria +22,5)
        self.confere(d, "brent", valor=73.5, variacao_pct=0.7, variacao_7d_pct=3.5, data="2026-11-18", defasado=False)
        self.assertEqual(self.gatilhos(d, "brent"), [])

    def test_ponto_de_base_fora_da_serie_deixa_a_variacao_sem_base(self):
        """CONTRATO, seção 2, passo 4, "Ponto fora da série": «Ponto de base […] com valor fora de 0,5 a 2 vezes
        os **dois** vizinhos dele na mesma série […] é tique da fonte […]: a variação que o usa sai `null` […],
        e um texto vai para `avisos`».

        O fechamento de 13/11 veio com o decimal deslocado (7,12 no lugar de 71,2): a variação de 7 dias fica
        null, sem gatilho, e o brent cai em "sem base de 7 dias".
        """
        self.so("brent", [("2026-11-12", 71.0), ("2026-11-13", 7.12), ("2026-11-16", 71.5), ("2026-11-19", 72.0),
                          ("2026-11-20", 72.5)])
        res, d = self.roda_e_le()
        self.confere(d, "brent", valor=72.5, variacao_pct=0.7, variacao_7d_pct=None)
        self.assertEqual(self.gatilhos(d, "brent"), [])
        self.assertIn({"id": "brent", "erro": "sem base de 7 dias"}, d["falhas"])
        self.assertIn("brent: ponto de 13/11 fora da série: variação de 7 dias sem base.", d["avisos"])

    def test_alta_forte_de_verdade_nao_e_ponto_fora_da_serie(self):
        """CONTRATO, seção 2, passo 4, "Ponto fora da série": «Não há teto de variação: um choque real, que move o
        último ponto, continua valendo». Brent de 70 a 84 em 7 dias (+20%): a variação vale, e não há aviso."""
        self.so("brent", [("2026-11-12", 70.0), ("2026-11-13", 70.0), ("2026-11-16", 75.0), ("2026-11-19", 80.0),
                          ("2026-11-20", 84.0)])
        res, d = self.roda_e_le()
        self.confere(d, "brent", variacao_7d_pct=20.0)
        self.assertEqual(d.get("avisos"), [])

    def test_um_ponto_so_nao_tem_variacao(self):
        """CONTRATO, seção 2, passo 4: «Sem ponto para comparar, a variação é `null`.»"""
        self.so("brent", [("2026-11-20", 73.50)])
        res, d = self.roda_e_le()
        self.confere(d, "brent", valor=73.5, variacao_pct=None, variacao_7d_pct=None, data="2026-11-20", defasado=False)

    def test_indicador_mensal(self):
        """CONTRATO, seção 2, passo 4: «Em indicador `mensal`, `variacao_7d_pct` é sempre `null`»; leitor `fao_csv`:
        «a data é `AAAA-MM` (vira dia 1)».

        indice_fao com cinco meses seguidos: a variação é a do mês sobre o mês anterior, e a de 7 dias é null.
        """
        self.poe("indice_fao", 0, [("2026-06", "120.0"), ("2026-07", "121.0"), ("2026-08", "122.0"),
                                   ("2026-09", "125.0"), ("2026-10", "128.0")])
        res, d = self.roda_e_le()
        # mês: 128.0 / 125.0 = 1.024 → +2,4
        self.confere(d, "indice_fao", valor=128.0, variacao_pct=2.4, variacao_7d_pct=None, data="2026-10-01",
                     defasado=False, confirmado=False)


# ---------------------------------------------------------------------------------------------
# Defasado e indicador sem fonte (passos 5 e 6)
# ---------------------------------------------------------------------------------------------

class DefasadoESemFonte(CasoIndicadores):

    def test_diaria_com_4_dias_nao_e_defasada_com_5_e(self):
        """CONTRATO, seção 2, passo 5: «`defasado`: cotação com mais de 4 dias corridos antes de `--dia`».

        gas_natural (uma fonte só). Cotação de 16/11, a 4 dias de 20/11: não é defasada. Cotação de
        15/11, a 5 dias: é, e o valor e a data continuam os da cotação.
        """
        for ultimo, defasado in (("2026-11-16", False), ("2026-11-15", True)):
            with self.subTest(ultimo=ultimo):
                self.nova()
                self.poe("gas_natural", 0, [("2026-11-06", "3.00"), ("2026-11-09", "3.01"), ("2026-11-13", "3.05"),
                                            (ultimo, "3.10")])
                res, d = self.roda_e_le()
                # dia: 3.10 / 3.05 = 1.016393 → +1,6
                self.confere(d, "gas_natural", valor=3.1, variacao_pct=1.6, data=ultimo, defasado=defasado)

    def test_mensal_com_62_dias_nao_e_defasado_com_63_e(self):
        """CONTRATO, seção 2, passo 5: «(mensal: mais de 62)».

        indice_fao da fixture: último mês 2026-10, data 2026-10-01. De 01/10 a 02/12 são 62 dias (30 de
        outubro, 30 de novembro e 2 de dezembro): não é defasado. Em 03/12 são 63: é.
        """
        for dia, defasado in (("2026-12-02", False), ("2026-12-03", True)):
            with self.subTest(dia=dia):
                self.nova(dia + "T21:00:00Z")
                res, d = self.roda_e_le(dia=dia)
                self.confere(d, "indice_fao", valor=127.3, data="2026-10-01", defasado=defasado)

    def test_indicador_sem_fonte_que_sirva(self):
        """CONTRATO, seção 2, passo 6: «Indicador sem fonte que sirva sai com `valor`, variações e `data` em `null`,
        `defasado: true`, `confirmado: false` e `fonte` igual à primeira do catálogo. Os outros seguem.»

        A única fonte do gas_natural não responde. O item continua na lista, no lugar dele, com tudo
        em null; `falhas` cita o id; os outros indicadores saem normais. Ele não é obrigatório: OK.
        """
        self.tira("gas_natural")
        res, d = self.roda_e_le()
        self.confere(d, "gas_natural", valor=None, variacao_pct=None, variacao_7d_pct=None, data=None, defasado=True,
                     confirmado=False, fonte=0)
        self.assertIn("gas_natural", [f.get("id") for f in d["falhas"]])
        self.assertEqual(self.gatilhos(d, "gas_natural"), [])
        self.confere(d, "brent", valor=74.05, defasado=False)
        self.assertEqual([i["id"] for i in d["indicadores"]],
                         ["brent", "trigo", "milho", "soja", "usd_brl", "gas_natural", "indice_fao"])
        self.confere_veredito(res, "OK", 0)

    def test_sem_fonte_que_sirva_a_fonte_gravada_e_a_primeira_do_catalogo(self):
        """CONTRATO, seção 2, passo 6: «`fonte` igual à primeira do catálogo». ESQUEMA, seção 3: `fonte`, «se nenhuma
        respondeu, a primeira do catálogo».

        As três fontes do brent falham, cada uma de um jeito (erro de rede, 404, valor fora da faixa).
        """
        self.tira("brent", 0)
        self.poe("brent", 1, [("2026-11-20", "73.85")], status=404)
        self.poe("brent", 2, [("2026-11-19", "900.00"), ("2026-11-20", "950.00")])
        res, d = self.roda_e_le()
        self.confere(d, "brent", valor=None, variacao_pct=None, variacao_7d_pct=None, data=None, defasado=True,
                     confirmado=False, fonte=0)
        self.assertIn("brent", [f.get("id") for f in d["falhas"]])


# ---------------------------------------------------------------------------------------------
# Gatilhos de preço (passos 7 e 8)
# ---------------------------------------------------------------------------------------------

class Gatilhos(CasoIndicadores):

    # brent: 70.00 em 13/11 e 78.40 em 20/11 → 78.40 / 70.00 = 1.12 → +12,0 em 7 dias (nível 3: de 10 a menos de 20)
    BRENT_12 = [("2026-11-10", 70.00), ("2026-11-13", 70.00), ("2026-11-19", 77.00), ("2026-11-20", 78.40)]
    # 2ª fonte (fred_csv): 74.20 / 70.00 = 1.06 → +6,0 em 7 dias (cumpre o nível 2: 5 ou mais)
    SEGUNDA_6 = [("2026-11-10", "70.00"), ("2026-11-13", "70.00"), ("2026-11-19", "73.00"), ("2026-11-20", "74.20")]
    # 2ª fonte: 71.40 / 70.00 = 1.02 → +2,0 em 7 dias (não cumpre nada)
    SEGUNDA_2 = [("2026-11-10", "70.00"), ("2026-11-13", "70.00"), ("2026-11-19", "71.00"), ("2026-11-20", "71.40")]

    def test_sem_alta_nao_ha_gatilho(self):
        """CONTRATO, seção 2, passo 7: gatilho só quando a variação é «maior ou igual a `alta_minima_pct`».

        No cenário pronto nenhuma variação chega ao limiar: `gatilhos` é lista vazia, e todo indicador
        sai com `confirmado: false`.
        """
        res, d = self.roda_e_le()
        self.assertEqual(d["gatilhos"], [])
        for item in d["indicadores"]:
            self.assertIs(item["confirmado"], False, item["id"])

    def test_alta_de_7_dias_de_nivel_2(self):
        """CONTRATO, seção 2, passo 7: «para cada indicador não defasado, aplica os critérios de preço da régua»; e
        o formato: `{"criterio": "energia.2", "ref": "brent", "texto": "Petróleo Brent subiu 6,1% em 7 dias, até
        20/11 (limiar: 5%)."}`; «O `texto` do gatilho traz sempre a data da cotação.»

        brent sobe 6,2% em 7 dias: um gatilho energia.2, com `ref` brent e 20/11 no texto. É nível 2:
        `confirmado` fica false, e o texto não fala em falta de confirmação.
        """
        self.poe("brent", 0, [("2026-11-10", 70.00), ("2026-11-13", 70.00), ("2026-11-19", 73.00), ("2026-11-20", 74.34)])
        res, d = self.roda_e_le()
        # 7 dias: 74.34 / 70.00 = 1.062 → +6,2 (≥ 5 e < 10) ; dia: 74.34 / 73.00 = 1.018356 → +1,8
        self.confere(d, "brent", valor=74.34, variacao_pct=1.8, variacao_7d_pct=6.2, confirmado=False, fonte=0)
        g = self.confere_gatilho(d, "brent", "energia.2", data_da_cotacao="20/11")
        self.assertEqual(len(d["gatilhos"]), 1)
        self.assertGreaterEqual(set(g), {"criterio", "ref", "texto"})
        self.assertLessEqual(set(g), {"criterio", "ref", "texto", "excecao", "alivio"})
        self.assertLessEqual(len(g["texto"]), 200, "ESQUEMA, seção 2: o texto do gatilho tem até 200 caracteres")
        self.confere_veredito(res, "OK", 0)

    def test_nivel_2_nao_pede_segunda_fonte(self):
        """CONTRATO, seção 2, passo 8: a confirmação é só para critério «de nível 3 ou 4»; «Nos outros casos,
        `confirmado` é `false`.»

        A mesma alta de 6,2%, com as outras duas fontes do brent fora do ar: o gatilho energia.2 sai
        igual, sem a frase de falta de confirmação.
        """
        self.so("brent", [("2026-11-10", 70.00), ("2026-11-13", 70.00), ("2026-11-19", 73.00), ("2026-11-20", 74.34)])
        res, d = self.roda_e_le()
        self.confere(d, "brent", variacao_7d_pct=6.2, confirmado=False)
        self.confere_gatilho(d, "brent", "energia.2")

    def test_so_alta_conta(self):
        """CONTRATO, seção 2, passo 7: «só alta conta».

        brent cai 8,0% em 7 dias e o dólar cai 2,0% no dia: nenhum gatilho.
        """
        self.poe("brent", 0, [("2026-11-10", 80.00), ("2026-11-13", 80.00), ("2026-11-19", 74.00), ("2026-11-20", 73.60)])
        self.poe("usd_brl", 0, [("2026-11-10", "5.5000"), ("2026-11-13", "5.5000"), ("2026-11-19", "5.5000"),
                                ("2026-11-20", "5.3900")])
        res, d = self.roda_e_le()
        # brent, 7 dias: 73.60 / 80.00 = 0.92 → −8,0 ; dólar, dia e 7 dias: 5.39 / 5.50 = 0.98 → −2,0
        self.confere(d, "brent", variacao_7d_pct=-8.0)
        self.confere(d, "usd_brl", variacao_pct=-2.0, variacao_7d_pct=-2.0)
        self.assertEqual(d["gatilhos"], [])

    def test_o_limiar_e_comparado_com_a_variacao_ja_arredondada(self):
        """CONTRATO, seção 2, passo 7: «variação já arredondada maior ou igual a `alta_minima_pct`».

        brent sobe 4,96% em 7 dias. Arredondado a 1 casa é 5,0, que cumpre o limiar de 5%: há gatilho
        energia.2. (Comparando o número cru, 4,96 < 5, não haveria.)
        """
        self.poe("brent", 0, [("2026-11-10", 100.00), ("2026-11-13", 100.00), ("2026-11-19", 104.00), ("2026-11-20", 104.96)])
        res, d = self.roda_e_le()
        # 7 dias: 104.96 / 100.00 = 1.0496 → 4,96 → +5,0 ; dia: 104.96 / 104.00 = 1.009231 → +0,9
        self.confere(d, "brent", variacao_7d_pct=5.0, variacao_pct=0.9)
        self.confere_gatilho(d, "brent", "energia.2")

    def test_logo_abaixo_do_limiar_nao_ha_gatilho(self):
        """CONTRATO, seção 2, passo 7: «variação já arredondada maior ou igual a `alta_minima_pct`».

        brent sobe 4,94% em 7 dias: arredondado é 4,9, abaixo de 5. Sem gatilho.
        """
        self.poe("brent", 0, [("2026-11-10", 100.00), ("2026-11-13", 100.00), ("2026-11-19", 104.00), ("2026-11-20", 104.94)])
        res, d = self.roda_e_le()
        # 7 dias: 104.94 / 100.00 = 1.0494 → 4,94 → +4,9
        self.confere(d, "brent", variacao_7d_pct=4.9)
        self.assertEqual(d["gatilhos"], [])

    def test_variacao_null_nao_cumpre(self):
        """CONTRATO, seção 2, passo 7: «variação `null` não cumpre».

        O brent só tem critério de 7 dias. A série salta 28,6% no dia, mas não tem ponto de 7 a 10 dias
        antes: `variacao_7d_pct` é null, e não há gatilho.
        """
        self.so("brent", [("2026-11-18", 70.00), ("2026-11-19", 70.00), ("2026-11-20", 90.00)])
        res, d = self.roda_e_le()
        # dia: 90.00 / 70.00 = 1.285714 → +28,6
        self.confere(d, "brent", variacao_pct=28.6, variacao_7d_pct=None)
        self.assertEqual(d["gatilhos"], [])

    def test_indicador_defasado_nao_dispara(self):
        """CONTRATO, seção 2, passo 7: os critérios valem «para cada indicador não defasado».

        A única fonte do brent que responde parou em 14/11 (6 dias), com alta de 20,0% em 7 dias. O
        indicador sai defasado, e não há gatilho.
        """
        self.so("brent", [("2026-11-04", 70.00), ("2026-11-13", 80.00), ("2026-11-14", 84.00)])
        res, d = self.roda_e_le()
        # 7 dias antes de 14/11 é 07/11; o ponto mais novo entre 04/11 e 07/11 é o de 04/11: 84.00 / 70.00 = 1.2 → +20,0
        self.confere(d, "brent", valor=84.0, variacao_7d_pct=20.0, data="2026-11-14", defasado=True, confirmado=False)
        self.assertEqual(d["gatilhos"], [])

    def test_indicador_fora_da_regua_nao_dispara(self):
        """CONTRATO, seção 2, passo 7: «aplica os critérios de preço da régua». ESQUEMA, seção 14: indicador com
        `obrigatorio: false` é «de contexto, só aparece no site».

        gas_natural não é citado em critério nenhum da régua: sobe 50% em 7 dias e não gera gatilho.
        """
        self.poe("gas_natural", 0, [("2026-11-10", "2.00"), ("2026-11-13", "2.00"), ("2026-11-19", "2.88"),
                                    ("2026-11-20", "3.00")])
        res, d = self.roda_e_le()
        # 7 dias: 3.00 / 2.00 = 1.5 → +50,0
        self.confere(d, "gas_natural", variacao_7d_pct=50.0)
        self.assertEqual(d["gatilhos"], [])

    DOLAR_2 = [("2026-11-10", "5.4000"), ("2026-11-13", "5.4000"), ("2026-11-19", "5.4000"), ("2026-11-20", "5.5080")]

    def test_janela_de_1_dia_vale_no_dia_da_cotacao(self):
        """CONTRATO, seção 2, passo 7: «Critério de janela `1d` só vale no dia da cotação: `data` igual a `--dia`.»

        O dólar sobe 2,0% em 20/11, e o dia é 20/11: gatilho cambio.2 (1,5% ou mais no dia). Em 7 dias a
        alta também é 2,0%, abaixo dos 3% da outra janela.
        """
        self.poe("usd_brl", 0, self.DOLAR_2)
        res, d = self.roda_e_le()
        # dia: 5.5080 / 5.4000 = 1.02 → +2,0 (≥ 1,5 e < 3) ; 7 dias (13/11): também +2,0 (< 3)
        self.confere(d, "usd_brl", valor=5.508, variacao_pct=2.0, variacao_7d_pct=2.0, data="2026-11-20", confirmado=False)
        self.confere_gatilho(d, "usd_brl", "cambio.2", data_da_cotacao="20/11")
        self.assertEqual(len(d["gatilhos"]), 1)

    def test_janela_de_1_dia_nao_vale_no_dia_seguinte(self):
        """CONTRATO, seção 2, passo 7: «Critério de janela `1d` só vale no dia da cotação: `data` igual a `--dia`. Em
        fim de semana, a alta de sexta não vira gatilho de novo.»

        A mesma série, lida no sábado 21/11: a cotação continua a de 20/11, com +2,0% no dia, mas o
        critério de 1 dia não vale mais. A alta de 7 dias (2,0%) não chega a 3%: nenhum gatilho.
        """
        self.poe("usd_brl", 0, self.DOLAR_2)
        res, d = self.roda_e_le(dia="2026-11-21", agora="2026-11-21T21:00:00Z")
        self.confere(d, "usd_brl", valor=5.508, variacao_pct=2.0, variacao_7d_pct=2.0, data="2026-11-20", defasado=False)
        self.assertEqual(d["gatilhos"], [])

    def test_fica_com_o_criterio_de_maior_nivel_por_indicador(self):
        """CONTRATO, seção 2, passo 7: «Fica com o critério de maior nível por indicador.»

        brent sobe 12,0% em 7 dias: cumpre o de nível 2 (5%) e o de nível 3 (10%). A 2ª fonte confirma
        (+6,0%). Sai um gatilho só para o brent, e é o energia.3.
        """
        self.poe("brent", 0, self.BRENT_12)
        self.poe("brent", 1, self.SEGUNDA_6)
        res, d = self.roda_e_le()
        self.confere(d, "brent", variacao_7d_pct=12.0)
        self.confere_gatilho(d, "brent", "energia.3")
        self.assertEqual(len(d["gatilhos"]), 1)

    def test_alta_forte_confirmada_pela_segunda_fonte(self):
        """CONTRATO, seção 2, passo 8: «Se o critério que ficou é de nível 3 ou 4, baixa a fonte seguinte do catálogo
        que serve para o mesmo indicador e calcula a mesma variação nela. `confirmado` é `true` se essa segunda
        fonte cumpre critério de preço de nível 2 ou mais na mesma janela.»

        1ª fonte: +12,0% em 7 dias (nível 3). 2ª fonte: +6,0% em 7 dias (cumpre o nível 2). `confirmado`
        é true, o gatilho é energia.3, e o valor publicado continua o da 1ª fonte.
        """
        self.poe("brent", 0, self.BRENT_12)
        self.poe("brent", 1, self.SEGUNDA_6)
        res, d = self.roda_e_le()
        # dia: 78.40 / 77.00 = 1.018182 → +1,8
        self.confere(d, "brent", valor=78.4, variacao_pct=1.8, variacao_7d_pct=12.0, confirmado=True, fonte=0)
        self.confere_gatilho(d, "brent", "energia.3")
        self.confere_veredito(res, "OK", 0)

    def test_alta_forte_sem_confirmacao_vira_nivel_2(self):
        """CONTRATO, seção 2, passo 8: «Sem segunda fonte que sirva, ou sem confirmação, `confirmado` é `false`: o
        gatilho sai com o `criterio` de nível 2 do domínio, e o `texto` termina com "Alta maior sem confirmação de
        segunda fonte."»

        1ª fonte: +12,0% em 7 dias. 2ª fonte: +2,0% (não cumpre nada). A 3ª não responde. O gatilho sai
        como energia.2, com a frase no fim do texto.
        """
        self.poe("brent", 0, self.BRENT_12)
        self.poe("brent", 1, self.SEGUNDA_2)
        self.tira("brent", 2)
        res, d = self.roda_e_le()
        self.confere(d, "brent", valor=78.4, variacao_7d_pct=12.0, confirmado=False, fonte=0)
        g = self.confere_gatilho(d, "brent", "energia.2", data_da_cotacao="20/11", sem_confirmacao=True)
        self.assertLessEqual(len(g["texto"]), 200, "ESQUEMA, seção 2: o texto do gatilho tem até 200 caracteres")
        self.assertEqual(len(d["gatilhos"]), 1)

    def test_so_a_fonte_seguinte_que_serve_confirma(self):
        """CONTRATO, seção 2, passo 8: «baixa a fonte seguinte do catálogo que serve […]. `confirmado` é `true` se
        essa segunda fonte cumpre critério».

        A segunda fonte é uma só: a seguinte que serve. Aqui é a 2ª do catálogo, com +2,0%: não
        confirma. A 3ª mostra +12,0%, mas não é ela a segunda fonte: `confirmado` continua false.
        """
        self.poe("brent", 0, self.BRENT_12)
        self.poe("brent", 1, self.SEGUNDA_2)
        self.poe("brent", 2, [("2026-11-10", "70.00"), ("2026-11-13", "70.00"), ("2026-11-19", "77.00"),
                              ("2026-11-20", "78.40")])
        res, d = self.roda_e_le()
        self.confere(d, "brent", confirmado=False, fonte=0)
        self.confere_gatilho(d, "brent", "energia.2", sem_confirmacao=True)

    def test_alta_forte_sem_segunda_fonte_que_sirva(self):
        """CONTRATO, seção 2, passo 8: «Sem segunda fonte que sirva, ou sem confirmação, `confirmado` é `false`».

        Só a 1ª fonte do brent responde, com +12,0%: gatilho energia.2, com a frase no fim.
        """
        self.so("brent", self.BRENT_12)
        res, d = self.roda_e_le()
        self.confere(d, "brent", variacao_7d_pct=12.0, confirmado=False)
        self.confere_gatilho(d, "brent", "energia.2", sem_confirmacao=True)

    def test_alta_forte_com_uma_fonte_so_no_catalogo(self):
        """ESQUEMA, seção 14, regra C5: «Com uma só, não há segunda fonte para confirmar a alta, e o gatilho de preço
        desse indicador nunca passa do nível 2 (R13c).»

        O brent fica com uma fonte só no catálogo, e ela mostra +12,0%: gatilho energia.2, com a frase.
        """
        self.muda_indicador("brent", fontes=[self.fonte("brent", 0)])
        self.poe("brent", 0, self.BRENT_12)
        res, d = self.roda_e_le()
        self.confere(d, "brent", variacao_7d_pct=12.0, confirmado=False)
        self.confere_gatilho(d, "brent", "energia.2", sem_confirmacao=True)

    def test_a_segunda_fonte_e_a_seguinte_que_serve(self):
        """CONTRATO, seção 2, passo 8: «baixa a fonte seguinte do catálogo que serve para o mesmo indicador».

        A 2ª fonte do brent não serve (num caso não responde; no outro, o último valor está fora da
        faixa). A seguinte que serve é a 3ª, com +6,0%: ela confirma, e o gatilho é energia.3.
        """
        for caso in ("não responde", "fora da faixa"):
            with self.subTest(segunda=caso):
                self.nova()
                self.poe("brent", 0, self.BRENT_12)
                if caso == "não responde":
                    self.tira("brent", 1)
                else:
                    self.poe("brent", 1, [("2026-11-13", "70.00"), ("2026-11-20", "900.00")])
                self.poe("brent", 2, self.SEGUNDA_6)
                res, d = self.roda_e_le()
                self.confere(d, "brent", variacao_7d_pct=12.0, confirmado=True, fonte=0)
                self.confere_gatilho(d, "brent", "energia.3")

    def test_nivel_4_confirmado_e_nao_confirmado(self):
        """CONTRATO, seção 2, passo 8: a confirmação vale para critério «de nível 3 ou 4».

        brent sobe 25,0% em 7 dias (nível 4: 20% ou mais). Com a 2ª fonte em +11,0%, `confirmado` é
        true e o gatilho é energia.4. Com a 2ª fonte em +2,0%, o gatilho cai para energia.2, com a frase.
        """
        brent_25 = [("2026-11-10", 70.00), ("2026-11-13", 70.00), ("2026-11-19", 86.00), ("2026-11-20", 87.50)]
        segunda_11 = [("2026-11-10", "70.00"), ("2026-11-13", "70.00"), ("2026-11-19", "77.00"), ("2026-11-20", "77.70")]
        for segunda, confirmado, criterio in ((segunda_11, True, "energia.4"), (self.SEGUNDA_2, False, "energia.2")):
            with self.subTest(criterio=criterio):
                self.nova()
                self.poe("brent", 0, brent_25)
                self.poe("brent", 1, segunda)
                res, d = self.roda_e_le()
                # 1ª fonte, 7 dias: 87.50 / 70.00 = 1.25 → +25,0 ; 2ª fonte: 77.70 / 70.00 = 1.11 → +11,0
                self.confere(d, "brent", valor=87.5, variacao_7d_pct=25.0, confirmado=confirmado)
                self.confere_gatilho(d, "brent", criterio, sem_confirmacao=not confirmado)

    def test_a_confirmacao_e_na_mesma_janela(self):
        """CONTRATO, seção 2, passo 8: «`confirmado` é `true` se essa segunda fonte cumpre critério de preço de nível
        2 ou mais na mesma janela.»

        1ª fonte do dólar: +3,5% no dia (nível 3 pela janela de 1 dia). 2ª fonte: só +0,3% no dia, mas
        +4,7% em 7 dias, o que cumpriria o nível 2 na outra janela. Não é a mesma janela: não confirma.
        O gatilho sai como cambio.2, com a frase.
        """
        self.poe("usd_brl", 0, [("2026-11-10", "5.4000"), ("2026-11-13", "5.4000"), ("2026-11-19", "5.4000"),
                                ("2026-11-20", "5.5890")])
        self.poe("usd_brl", 1, [("2026-11-10", 5.3400), ("2026-11-13", 5.3400), ("2026-11-19", 5.5700),
                                ("2026-11-20", 5.5890)])
        res, d = self.roda_e_le()
        # 1ª fonte, dia: 5.5890 / 5.4000 = 1.035 → +3,5 (≥ 3 e < 5: nível 3) ; 7 dias: também +3,5 (nível 2)
        # 2ª fonte, dia: 5.5890 / 5.5700 = 1.003411 → +0,3 ; 7 dias: 5.5890 / 5.3400 = 1.046629 → +4,7
        self.confere(d, "usd_brl", valor=5.589, variacao_pct=3.5, variacao_7d_pct=3.5, confirmado=False, fonte=0)
        self.confere_gatilho(d, "usd_brl", "cambio.2", sem_confirmacao=True)

    def test_confirmacao_na_janela_de_1_dia(self):
        """CONTRATO, seção 2, passo 8: «cumpre critério de preço de nível 2 ou mais na mesma janela».

        1ª fonte do dólar: +3,5% no dia (nível 3). 2ª fonte: +2,0% no dia (cumpre o nível 2 da janela de
        1 dia). `confirmado` é true, e o gatilho é cambio.3.
        """
        self.poe("usd_brl", 0, [("2026-11-10", "5.4000"), ("2026-11-13", "5.4000"), ("2026-11-19", "5.4000"),
                                ("2026-11-20", "5.5890")])
        self.poe("usd_brl", 1, [("2026-11-10", 5.4000), ("2026-11-13", 5.4000), ("2026-11-19", 5.4000),
                                ("2026-11-20", 5.5080)])
        res, d = self.roda_e_le()
        # 2ª fonte, dia: 5.5080 / 5.4000 = 1.02 → +2,0 (≥ 1,5)
        self.confere(d, "usd_brl", valor=5.589, variacao_pct=3.5, confirmado=True, fonte=0)
        self.confere_gatilho(d, "usd_brl", "cambio.3")

    def test_o_texto_traz_a_data_da_cotacao_e_nao_a_do_dia(self):
        """CONTRATO, seção 2: «O `texto` do gatilho traz sempre a data da cotação.»

        A cotação do brent é de 18/11 (2 dias antes de `--dia`; não está defasada) e mostra +6,2% em 7
        dias. O gatilho energia.2 traz 18/11 no texto.
        """
        self.so("brent", [("2026-11-08", 70.00), ("2026-11-11", 70.00), ("2026-11-17", 73.00), ("2026-11-18", 74.34)])
        res, d = self.roda_e_le()
        # 7 dias antes de 18/11 é 11/11: 74.34 / 70.00 = 1.062 → +6,2
        self.confere(d, "brent", variacao_7d_pct=6.2, data="2026-11-18", defasado=False)
        self.confere_gatilho(d, "brent", "energia.2", data_da_cotacao="18/11")

    def test_dois_indicadores_do_mesmo_dominio(self):
        """CONTRATO, seção 2, passo 7: «Fica com o critério de maior nível por indicador» (um gatilho por indicador,
        não por domínio).

        trigo e milho sobem 6,0% em 7 dias cada um: dois gatilhos alimentos.2, um com `ref` trigo e
        outro com `ref` milho.
        """
        self.poe("trigo", 0, [("2026-11-10", 500.00), ("2026-11-13", 500.00), ("2026-11-19", 520.00), ("2026-11-20", 530.00)])
        self.poe("milho", 0, [("2026-11-10", "4.00"), ("2026-11-13", "4.00"), ("2026-11-19", "4.16"), ("2026-11-20", "4.24")])
        res, d = self.roda_e_le()
        # trigo: 530 × 0.01 = 5.30 ; 7 dias: 530 / 500 = 1.06 → +6,0 ; dia: 530 / 520 = 1.019231 → +1,9
        # milho: 7 dias: 4.24 / 4.00 = 1.06 → +6,0 ; dia: 4.24 / 4.16 = 1.019231 → +1,9
        self.confere(d, "trigo", valor=5.3, variacao_pct=1.9, variacao_7d_pct=6.0)
        self.confere(d, "milho", valor=4.24, variacao_pct=1.9, variacao_7d_pct=6.0)
        self.confere_gatilho(d, "trigo", "alimentos.2")
        self.confere_gatilho(d, "milho", "alimentos.2")
        self.assertEqual(len(d["gatilhos"]), 2)


class DecisoesDaConciliacao(CasoIndicadores):
    """As frases que a conciliação de 23/11/2026 pôs no CONTRATO, seção 2 (arredondamento, data repetida,
    segunda fonte velha, empate entre janelas, fonte anterior)."""

    def test_meio_arredondado_vai_para_longe_do_zero(self):
        """CONTRATO, seção 2, passo 4: «a metade vai para longe do zero (0,25 vira 0,3; −0,25 vira −0,3)»; passo 7:
        «variação já arredondada maior ou igual a `alta_minima_pct`».

        brent sobe 4,95% em 7 dias (de 100,00 a 104,95): arredondado é 5,0, e há gatilho energia.2. E o
        dólar cai 0,25% no dia (de 4,0000 a 3,9900): −0,3.
        """
        self.poe("brent", 0, [("2026-11-10", 100.00), ("2026-11-13", 100.00), ("2026-11-19", 104.00), ("2026-11-20", 104.95)])
        self.poe("usd_brl", 0, [("2026-11-10", "4.0000"), ("2026-11-13", "4.0000"), ("2026-11-19", "4.0000"),
                                ("2026-11-20", "3.9900")])
        res, d = self.roda_e_le()
        # brent: 104.95 / 100.00 = 1.0495 → 4,95 → +5,0 ; dólar: 3.99 / 4.00 = 0.9975 → −0,25 → −0,3
        self.confere(d, "brent", variacao_7d_pct=5.0)
        self.confere_gatilho(d, "brent", "energia.2")
        self.confere(d, "usd_brl", variacao_pct=-0.3, variacao_7d_pct=-0.3)

    def test_a_variacao_e_sobre_os_pontos_crus(self):
        """CONTRATO, seção 2, passo 4: «A variação é calculada sobre os pontos crus da série, já com o `fator` (e não
        sobre o `valor` arredondado)».

        gas_natural com `casas` 0: os valores 2,4 e 2,6 saem arredondados como 2 e 3, mas a variação é
        2,6 / 2,4 = +8,3%, e não +50%.
        """
        self.muda_indicador("gas_natural", casas=0)
        self.poe("gas_natural", 0, [("2026-11-13", "2.40"), ("2026-11-19", "2.50"), ("2026-11-20", "2.60")])
        res, d = self.roda_e_le()
        # 7 dias: 2.60 / 2.40 = 1.083333 → +8,3 ; dia: 2.60 / 2.50 = 1.04 → +4,0
        self.confere(d, "gas_natural", valor=3, variacao_7d_pct=8.3, variacao_pct=4.0)

    def test_data_repetida_fica_a_ultima_da_resposta(self):
        """CONTRATO, seção 2, leitores: «Dois pontos na mesma data: fica o que vem por último na resposta, entre os
        que têm valor.»

        A resposta do milho (fred_csv) traz 20/11 três vezes: 4,30, 4.43 e uma linha vazia. Vale 4,43.
        """
        corpo = "observation_date,MILHO\n2026-11-13,4.35\n2026-11-19,4.40\n2026-11-20,4.30\n2026-11-20,4.43\n2026-11-20,\n"
        self.tira("milho")
        self.poe_cru("milho", 0, corpo)
        res, d = self.roda_e_le()
        self.confere(d, "milho", valor=4.43, data="2026-11-20")

    def test_segunda_fonte_velha_nao_confirma(self):
        """CONTRATO, seção 2, passo 8: «A segunda fonte só confirma se a `data` dela não é mais de 4 dias corridos
        anterior à `data` da escolhida; senão, `confirmado` é `false`, e a busca para nela».

        1ª fonte do brent: +12,0% até 20/11. 2ª fonte: +6,0%, mas até 15/11 (5 dias antes). 3ª: +6,0% até 20/11,
        mas a busca parou na 2ª. Com a 2ª até 16/11 (4 dias), ela confirma.
        """
        velha = [("2026-11-05", "70.00"), ("2026-11-08", "70.00"), ("2026-11-14", "73.00"), ("2026-11-15", "74.20")]
        self.poe("brent", 0, Gatilhos.BRENT_12)
        self.poe("brent", 1, velha)
        self.poe("brent", 2, Gatilhos.SEGUNDA_6)
        res, d = self.roda_e_le()
        self.confere(d, "brent", confirmado=False)
        self.confere_gatilho(d, "brent", "energia.2", sem_confirmacao=True)
        self.nova()
        self.poe("brent", 0, Gatilhos.BRENT_12)
        self.poe("brent", 1, [("2026-11-06", "70.00"), ("2026-11-09", "70.00"), ("2026-11-15", "73.00"), ("2026-11-16", "74.20")])
        res, d = self.roda_e_le()
        self.confere(d, "brent", confirmado=True)
        self.confere_gatilho(d, "brent", "energia.3")

    def test_empate_de_nivel_vale_a_janela_de_7_dias(self):
        """CONTRATO, seção 2, passo 7: «no empate de nível entre a janela de 1 dia e a de 7 dias, vale a de 7 dias, no
        `texto` e na confirmação».

        Dólar, 1ª fonte: +3,5% no dia (nível 3 de 1 dia) e +6,5% em 7 dias (nível 3 de 7 dias). 2ª fonte: +3,5% no
        dia, mas só +3,9% em 7 dias. A de 7 dias vale: a 2ª cumpre o nível 2 de 7 dias (3%), e confirma. O texto é
        o de 7 dias.
        """
        self.poe("usd_brl", 0, [("2026-11-10", "5.0000"), ("2026-11-13", "5.0000"), ("2026-11-19", "5.1450"),
                                ("2026-11-20", "5.3250")])
        self.poe("usd_brl", 1, [("2026-11-10", 5.1250), ("2026-11-13", 5.1250), ("2026-11-19", 5.1450), ("2026-11-20", 5.3250)])
        res, d = self.roda_e_le()
        # 1ª: dia 5.3250 / 5.1450 = 1.034985 → +3,5 ; 7 dias 5.3250 / 5.0000 = 1.065 → +6,5
        # 2ª: dia +3,5 ; 7 dias 5.3250 / 5.1250 = 1.039024 → +3,9
        self.confere(d, "usd_brl", variacao_pct=3.5, variacao_7d_pct=6.5, confirmado=True)
        g = self.confere_gatilho(d, "usd_brl", "cambio.3")
        self.assertEqual(g["texto"], "Dólar em reais subiu 6,5% em 7 dias, até 20/11 (limiar: 6%).")

    def test_fonte_anterior_a_escolhida_nao_confirma(self):
        """CONTRATO, seção 2, passo 8: «A "fonte seguinte" é a primeira que serve depois da escolhida, na ordem do
        catálogo: fonte anterior à escolhida não confirma».

        A 1ª fonte do dólar parou em 13/11 (defasada), com alta. A escolhida é a 2ª (+3,5% no dia, nível 3); a 3ª
        não responde. Não há confirmação, mesmo com a 1ª mostrando alta.
        """
        self.poe("usd_brl", 0, [("2026-11-03", "5.0000"), ("2026-11-12", "5.0000"), ("2026-11-13", "5.5000")])
        self.poe("usd_brl", 1, [("2026-11-10", 5.4000), ("2026-11-13", 5.4000), ("2026-11-19", 5.4000), ("2026-11-20", 5.5890)])
        self.tira("usd_brl", 2)
        res, d = self.roda_e_le()
        self.confere(d, "usd_brl", fonte=1, confirmado=False)
        self.confere_gatilho(d, "usd_brl", "cambio.2", sem_confirmacao=True)


class TrocaDeContrato(CasoIndicadores):
    """CONTRATO, seção 2, "Troca de contrato", e ESQUEMA, seção 14, campo `contratos` (regra C6).

    A 1ª fonte do brent (yahoo_chart) ganha `contratos`, com o modelo `…/chart/brent-{c}` e os 12 meses. Em
    20/11/2026, os candidatos são X26, Z26, F27 e G27.
    """

    MODELO = "https://cotacoes.exemplo.invalid/chart/brent-{c}"
    # Na série do catálogo, a troca de contrato entra em 20/11, com degrau de +6%: +7,1% em 7 dias (gatilho).
    SERIE = [("2026-11-10", 70.00), ("2026-11-13", 70.00), ("2026-11-19", 70.70), ("2026-11-20", 74.97)]
    # O contrato que a série passou a usar: 74.90 / 74.00 = +1,2% em 7 dias; 74.90 / 74.70 = +0,3% no dia.
    CONTRATO = [("2026-11-10", 74.00), ("2026-11-13", 74.00), ("2026-11-19", 74.70), ("2026-11-20", 74.90)]

    def com_contratos(self, contratos=None):
        self.muda_fonte("brent", 0, contratos=contratos or {"modelo": self.MODELO, "meses": "FGHJKMNQUVXZ"})
        self.poe("brent", 0, self.SERIE)

    def contrato(self, codigo, serie, **resposta):
        self.b.responde(self.MODELO.replace("{c}", codigo), apoio.yahoo_chart(serie), **resposta)

    def avisos_de(self, d, ident="brent"):
        return [a for a in d["avisos"] if a.startswith(ident + ":")]

    def test_troca_dentro_da_janela(self):
        """Itens 2, 3, 4 e 6: o candidato X26 não responde; Z26 casa (último ponto de 20/11, 74.90 contra 74.97:
        0,09%); a série e o contrato diferem em 19/11, que é o ponto de base de 1 dia. As duas variações saem do
        contrato, nos mesmos dias; `valor`, `data` e `fonte` não mudam; `avisos` diz o contrato e o dia da troca."""
        self.com_contratos()
        self.contrato("Z26", self.CONTRATO)
        res, d = self.roda_e_le()
        self.confere(d, "brent", valor=74.97, data="2026-11-20", variacao_pct=0.3, variacao_7d_pct=1.2, fonte=0)
        self.assertEqual(self.gatilhos(d, "brent"), [])  # na série seria +7,1%: energia.2
        self.assertEqual(self.avisos_de(d), ["brent: variações medidas no contrato Z26, porque a série trocou de "
                                             "contrato em 20/11."])

    def test_para_no_primeiro_que_casa(self):
        """Item 2: «Para no primeiro que casa.» Z26 não casa (último valor 80,00, 6,7% acima); F27 casa; G27, que
        também casaria com outra conta, não é usado."""
        self.com_contratos()
        self.contrato("Z26", [("2026-11-13", 80.00), ("2026-11-20", 80.00)])
        self.contrato("F27", self.CONTRATO)
        self.contrato("G27", [("2026-11-13", 60.00), ("2026-11-19", 74.97), ("2026-11-20", 74.97)])
        res, d = self.roda_e_le()
        self.confere(d, "brent", variacao_pct=0.3, variacao_7d_pct=1.2)
        self.assertIn("contrato F27", self.avisos_de(d)[0])

    def test_troca_fora_da_janela(self):
        """Item 5: a troca foi antes dos dois pontos de base (a série e o contrato só diferem em 06/11): nada muda."""
        serie = [("2026-11-06", 60.00), ("2026-11-09", 70.00), ("2026-11-13", 70.00), ("2026-11-19", 71.00), ("2026-11-20", 72.10)]
        contrato = [("2026-11-06", 66.00), ("2026-11-09", 70.10), ("2026-11-13", 70.10), ("2026-11-19", 71.05),
                    ("2026-11-20", 72.00)]
        self.muda_fonte("brent", 0, contratos={"modelo": self.MODELO, "meses": "FGHJKMNQUVXZ"})
        self.poe("brent", 0, serie)
        self.contrato("X26", contrato)
        res, d = self.roda_e_le()
        # na série: dia 72.10 / 71.00 → +1,5 ; 7 dias 72.10 / 70.00 → +3,0
        self.confere(d, "brent", variacao_pct=1.5, variacao_7d_pct=3.0)
        self.assertEqual(d["avisos"], [])

    def test_nenhum_candidato_casa(self):
        """Item 5: Z26 tem outro valor no último dia; F27 tem outra data no último ponto; X26 e G27 não respondem.
        Nada muda, e a série dá o gatilho."""
        self.com_contratos()
        self.contrato("Z26", [("2026-11-13", 80.00), ("2026-11-20", 80.00)])
        self.contrato("F27", [("2026-11-13", 74.00), ("2026-11-19", 74.97)])
        res, d = self.roda_e_le()
        # na série: 74.97 / 70.00 = 1.071 → +7,1 ; dia 74.97 / 70.70 = 1.060396 → +6,0
        self.confere(d, "brent", variacao_pct=6.0, variacao_7d_pct=7.1)
        self.confere_gatilho(d, "brent", "energia.2")
        self.assertEqual(d["avisos"], [])
        self.confere_veredito(res, "OK", 0)

    def test_candidato_sem_ponto_de_base(self):
        """Item 5: o contrato casa, mas não tem o ponto de base de 7 dias (13/11). Nada muda."""
        self.com_contratos()
        self.contrato("Z26", [("2026-11-19", 74.70), ("2026-11-20", 74.90)])
        res, d = self.roda_e_le()
        self.confere(d, "brent", variacao_pct=6.0, variacao_7d_pct=7.1)
        self.assertEqual(d["avisos"], [])

    def test_tempo_esgotado(self):
        """Item 5: o contrato que casaria demora mais que o teto do `--tempo` (2 segundos). Nada muda, e o
        indicador sai com a medida da série."""
        self.com_contratos()
        self.contrato("Z26", self.CONTRATO, demora=5)
        res, d = self.roda_e_le("--tempo", "2")
        self.confere(d, "brent", valor=74.97, variacao_pct=6.0, variacao_7d_pct=7.1)
        self.assertEqual(d["avisos"], [])

    def test_contratos_fora_da_regra_c6_nao_derruba(self):
        """Item 5 e ESQUEMA, seção 14, C6: `contratos` sem a marca `{c}` (ou com meses fora da ordem): nada muda."""
        for contratos in ({"modelo": "https://cotacoes.exemplo.invalid/chart/brent-Z26", "meses": "Z"},
                          {"modelo": self.MODELO, "meses": "ZF"}, {"modelo": self.MODELO}):
            with self.subTest(contratos=contratos):
                self.nova()
                self.com_contratos(contratos)
                self.contrato("Z26", self.CONTRATO)
                res, d = self.roda_e_le()
                self.confere(d, "brent", variacao_pct=6.0, variacao_7d_pct=7.1)
                self.assertEqual(d["avisos"], [])
                self.confere_veredito(res, "OK", 0)

    def test_a_segunda_fonte_nao_passa_pelo_contrato(self):
        """«A segunda fonte (passo 8) é medida na série dela, sem esta etapa.» Alta forte no contrato (+12,0%), com
        a série também em +12,0% (sem troca), e a 2ª fonte em +6,0%: confirma pela série da 2ª fonte."""
        self.muda_fonte("brent", 0, contratos={"modelo": self.MODELO, "meses": "FGHJKMNQUVXZ"})
        self.poe("brent", 0, Gatilhos.BRENT_12)
        self.poe("brent", 1, Gatilhos.SEGUNDA_6)
        self.contrato("X26", Gatilhos.BRENT_12)
        res, d = self.roda_e_le()
        self.confere(d, "brent", variacao_7d_pct=12.0, confirmado=True)
        self.assertEqual(d["avisos"], [])  # o contrato casa, mas não houve troca na janela


# ---------------------------------------------------------------------------------------------
# Formato de indicadores.json
# ---------------------------------------------------------------------------------------------

class Formato(CasoIndicadores):

    def test_raiz_de_indicadores_json(self):
        """CONTRATO, seção 2, "Formato de `indicadores.json`": `versao`, `dia`, `gerada_em`, `indicadores`, `gatilhos`,
        `falhas` e `avisos` («vazia quando nenhum foi medido no contrato»); seção 0, relógio de teste: «em todo
        `gerada_em`».
        """
        res, d = self.roda_e_le()
        self.assertEqual(list(d), ["versao", "dia", "gerada_em", "indicadores", "gatilhos", "falhas", "avisos"])
        self.assertEqual(d["avisos"], [])  # nenhuma fonte da fixture tem `contratos`
        self.assertEqual(d.get("versao"), 1)
        self.assertEqual(d.get("dia"), apoio.DIA)
        self.assertEqual(d.get("gerada_em"), apoio.AGORA)
        self.assertIsInstance(d["indicadores"], list)
        self.assertIsInstance(d["gatilhos"], list)
        self.assertIsInstance(d["falhas"], list)

    def test_todos_os_indicadores_na_ordem_do_catalogo_com_as_copias(self):
        """CONTRATO, seção 2: «`indicadores` traz todos os indicadores do catálogo, na ordem do catálogo […]. `nome`,
        `dominio` e `unidade` são cópias do catálogo.»

        O catálogo é regravado em outra ordem (de trás para a frente), com um nome trocado: a saída
        segue a ordem nova e copia o nome novo.
        """
        catalogo = self.b.le_dados("indicadores.json")
        catalogo["indicadores"].reverse()
        catalogo["indicadores"][0]["nome"] = "Índice de comida (nome trocado no teste)"
        self.b.grava_dados("indicadores.json", catalogo)
        res, d = self.roda_e_le()
        self.assertEqual([i["id"] for i in d["indicadores"]], [i["id"] for i in catalogo["indicadores"]])
        for item, original in zip(d["indicadores"], catalogo["indicadores"]):
            self.assertEqual((item["nome"], item["dominio"], item["unidade"]),
                             (original["nome"], original["dominio"], original["unidade"]), item["id"])

    def test_chaves_de_cada_indicador_na_ordem_do_esquema(self):
        """CONTRATO, seção 2: os itens saem «já no formato da edição (`ESQUEMA.md`, seção 3)»; seção 0: «JSON
        gravado: […] chaves na ordem do `ESQUEMA.md`»; ESQUEMA, seção 0: «Chave desconhecida é erro.»

        Cada item tem exatamente as 11 chaves da tabela da seção 3 do ESQUEMA, na ordem dela, com os
        tipos da tabela; `fonte` é `{"nome", "url"}`, sem mais nada.
        """
        self.tira("gas_natural")
        res, d = self.roda_e_le()
        self.assertEqual(len(d["indicadores"]), 7)
        for item in d["indicadores"]:
            self.assertEqual(list(item), CHAVES_DO_INDICADOR, item.get("id"))
            self.assertIsInstance(item["defasado"], bool)
            self.assertIsInstance(item["confirmado"], bool)
            self.assertEqual(sorted(item["fonte"]), ["nome", "url"])
            for campo in ("valor", "variacao_pct", "variacao_7d_pct"):
                self.assertTrue(item[campo] is None or (isinstance(item[campo], (int, float))
                                                        and not isinstance(item[campo], bool)), campo)
            if item["valor"] is not None:
                self.assertGreater(item["valor"], 0)
                self.assertRegex(item["data"], r"^\d{4}-\d\d-\d\d$")

    def test_fonte_gravada_e_a_que_foi_usada(self):
        """ESQUEMA, seção 3: `fonte` é «`{"nome": texto até 60, "url": URL}`: a fonte usada hoje».

        No cenário pronto todo indicador usa a 1ª fonte do catálogo; sem a 1ª do brent, ele traz a 2ª.
        """
        self.tira("brent", 0)
        res, d = self.roda_e_le()
        self.confere(d, "brent", fonte=1)
        for ident in ("trigo", "milho", "soja", "usd_brl", "gas_natural", "indice_fao"):
            self.confere(d, ident, fonte=0)

    def test_json_gravado_no_padrao(self):
        """CONTRATO, seção 0: «JSON gravado: UTF-8, sem BOM, acentos legíveis, recuo de 2 espaços, quebra de linha
        no fim».

        "Petróleo Brent" e "US$ por milhão de BTU" aparecem com os acentos escritos.
        """
        res = self.roda()
        self.confere_json_no_padrao(res, "indicadores.json")
        self.assertIn("Petróleo Brent", res.texto("indicadores.json"))
        self.assertIn("US$ por milhão de BTU", res.texto("indicadores.json"))

    def test_falhas_vazia_quando_tudo_veio(self):
        """CONTRATO, seção 2, formato: `falhas` lista os indicadores com problema (`{"id": "gas_natural", "erro":
        "todas as fontes falharam"}`, `{"id": "milho", "erro": "sem base de 7 dias"}`).

        No cenário pronto não há problema nenhum: `falhas` é lista vazia.
        """
        res, d = self.roda_e_le()
        self.assertEqual(d["falhas"], [])

    def test_falhas_traz_id_e_erro(self):
        """CONTRATO, seção 2, formato: `"falhas": [{"id": "gas_natural", "erro": "todas as fontes falharam"}, {"id":
        "milho", "erro": "sem base de 7 dias"}]`.

        gas_natural sem fonte e brent sem base de 7 dias; a soja defasada. «`falhas` traz só dois textos: "todas as
        fontes falharam" (indicador sem valor) e "sem base de 7 dias" (indicador diário com valor e `variacao_7d_pct`
        `null`). O indicador defasado não entra em `falhas`».
        """
        self.tira("gas_natural")
        self.so("brent", [("2026-11-18", 73.10), ("2026-11-19", 73.40), ("2026-11-20", 74.05)])
        self.poe("soja", 0, [("2026-11-04", 1090.00), ("2026-11-13", 1100.00), ("2026-11-14", 1104.00)])
        self.tira("soja", 1)
        res, d = self.roda_e_le()
        self.confere(d, "soja", defasado=True, data="2026-11-14")
        self.assertEqual(d["falhas"], [{"id": "brent", "erro": "sem base de 7 dias"},
                                       {"id": "gas_natural", "erro": "todas as fontes falharam"}])

    def test_grava_so_indicadores_json_e_nao_mexe_no_repositorio(self):
        """CONTRATO, seção 2: «Grava: `P/indicadores.json`» e «Não altera nenhum dos dois» (catálogo e régua); seção
        0: «Nenhuma ferramenta deixa arquivo a mais no repositório» e a escrita atômica.
        """
        antes = apoio._fotografa(self.b.raiz)
        res = self.roda()
        self.assertEqual(sorted(res.arquivos), ["indicadores.json"], res.relato())
        self.assertEqual(apoio._fotografa(self.b.raiz), antes)

    def test_cria_a_pasta_de_trabalho_se_faltar(self):
        """CONTRATO, seção 0, opção `--trabalho PASTA`: «é criada se faltar»."""
        pasta = self.b.base / "ainda" / "nao" / "existe"
        res = self.roda(trabalho=pasta)
        self.confere_veredito(res, "OK", 0)
        self.assertEqual(sorted(res.arquivos), ["indicadores.json"])

    def test_a_mesma_entrada_da_os_mesmos_bytes(self):
        """CONTRATO, seção 0: «Mesma entrada, mesmos bytes.»"""
        saidas = []
        for _ in range(2):
            self.nova()
            self.poe("brent", 0, Gatilhos.BRENT_12)
            res = self.roda()
            self.assertIn("indicadores.json", res.arquivos, res.relato())
            saidas.append(res.arquivos["indicadores.json"])
        self.assertEqual(saidas[0], saidas[1])

    def test_dia_vem_do_contexto(self):
        """CONTRATO, seção 0, opção `--dia`: padrão «o `dia` de `P/contexto.json`, se o arquivo existe».

        Sem --dia e com contexto.json dizendo 2026-11-18: o arquivo sai com esse dia, e a cotação do
        brent é a de 18/11 (73.10), porque os pontos de 19 e 20/11 são «depois de `--dia`».
        """
        self.b.poe_contexto(dia="2026-11-18")
        res = self.b.roda("indicadores")
        d = self.dados(res)
        self.assertEqual(d.get("dia"), "2026-11-18")
        self.confere(d, "brent", valor=73.1, data="2026-11-18")

    def test_dia_padrao_e_hoje_em_brasilia(self):
        """CONTRATO, seção 0, opção `--dia`: padrão «senão, hoje em Brasília (UTC−3 fixo)».

        Sem --dia e sem contexto.json, com o relógio em 2026-11-21T01:30:00Z (22h30 de 20/11 em
        Brasília): o dia é 2026-11-20.
        """
        res = self.b.roda("indicadores", agora="2026-11-21T01:30:00Z")
        d = self.dados(res)
        self.assertEqual(d.get("dia"), "2026-11-20")
        self.assertEqual(d.get("gerada_em"), "2026-11-21T01:30:00Z")
        self.confere(d, "brent", valor=74.05, data="2026-11-20")


# ---------------------------------------------------------------------------------------------
# Veredito e código de saída
# ---------------------------------------------------------------------------------------------

class Vereditos(CasoIndicadores):

    CURTA = [("2026-11-18", 73.10), ("2026-11-19", 73.40), ("2026-11-20", 74.05)]

    def test_ok(self):
        """CONTRATO, seção 2, "Veredito e código": «todos os obrigatórios têm valor, não estão defasados e têm a
        variação de 7 dias» → `OK 11 indicadores, 1 gatilho de preço`, código 0.
        """
        res, d = self.roda_e_le()
        self.confere_veredito(res, "OK", 0)
        for ident in OBRIGATORIOS:
            item = self.ind(d, ident)
            self.assertIsNotNone(item["valor"])
            self.assertIsNotNone(item["variacao_7d_pct"])
            self.assertIs(item["defasado"], False)

    def test_ok_com_gatilho(self):
        """CONTRATO, seção 2, "Veredito e código": gatilho de preço não muda o veredito (`OK 11 indicadores, 1 gatilho
        de preço`, código 0).
        """
        self.poe("brent", 0, Gatilhos.BRENT_12)
        self.poe("brent", 1, Gatilhos.SEGUNDA_6)
        res, d = self.roda_e_le()
        self.assertEqual(len(d["gatilhos"]), 1)
        self.confere_veredito(res, "OK", 0)

    def test_ok_mesmo_com_indicador_de_contexto_sem_dado_ou_sem_base(self):
        """CONTRATO, seção 2, "Veredito e código": «Obrigatório é o indicador com `obrigatorio: true` no catálogo»; o
        veredito só olha os obrigatórios.

        gas_natural (não obrigatório) sem fonte, e depois com série curta, sem base de 7 dias: OK, código 0.
        """
        self.tira("gas_natural")
        res = self.roda()
        self.confere_veredito(res, "OK", 0)
        self.nova()
        self.poe("gas_natural", 0, [("2026-11-19", "3.09"), ("2026-11-20", "3.12")])
        res, d = self.roda_e_le()
        self.confere(d, "gas_natural", valor=3.12, variacao_7d_pct=None)
        self.confere_veredito(res, "OK", 0)

    def test_parcial_sem_dado(self):
        """CONTRATO, seção 2, "Veredito e código": «falta ou está defasado algum obrigatório» → `PARCIAL sem dado:
        milho`, código 3; seção 0: código 3 «gravou a saída, mas incompleta».

        As duas fontes do milho não respondem. Os outros indicadores saem normais.
        """
        self.tira("milho")
        res, d = self.roda_e_le()
        self.confere_veredito(res, "PARCIAL", 3)
        self.assertRegex(res.ultima, r"sem dado: [^;]*\bmilho\b")
        self.confere(d, "milho", valor=None, defasado=True)
        self.confere(d, "brent", valor=74.05)

    def test_indicador_sem_dado_nao_entra_tambem_em_sem_base(self):
        """CONTRATO, seção 2, "Veredito e código": «obrigatório citado em critério de 7 dias saiu com valor, em dia,
        mas com `variacao_7d_pct` `null`» e «O indicador sem dado entra só em "sem dado", nunca também em "sem
        base de 7 dias".»
        """
        self.tira("milho")
        res = self.roda()
        self.confere_veredito(res, "PARCIAL", 3)
        self.assertNotIn("sem base de 7 dias", res.ultima)

    def test_parcial_sem_dado_quando_o_obrigatorio_esta_defasado(self):
        """CONTRATO, seção 2, "Veredito e código": «falta ou está defasado algum obrigatório» → `PARCIAL sem dado: …`,
        código 3.

        As duas fontes da soja pararam (a 1ª em 14/11, a 2ª em 13/11). O indicador sai com o número da
        1ª, defasado, e o veredito é PARCIAL sem dado: soja.
        """
        self.poe("soja", 0, [("2026-11-04", 1090.00), ("2026-11-13", 1100.00), ("2026-11-14", 1104.00)])
        self.poe("soja", 1, [("2026-11-04", "10.90"), ("2026-11-12", "10.97"), ("2026-11-13", "11.01")])
        res, d = self.roda_e_le()
        # 1104.00 × 0.01 = 11.04
        self.confere(d, "soja", valor=11.04, data="2026-11-14", defasado=True, fonte=0)
        self.confere_veredito(res, "PARCIAL", 3)
        self.assertRegex(res.ultima, r"sem dado: [^;]*\bsoja\b")

    def test_parcial_sem_base_de_7_dias(self):
        """CONTRATO, seção 2, "Veredito e código": «obrigatório citado em critério de 7 dias saiu com
        `variacao_7d_pct` `null`» → `PARCIAL sem base de 7 dias: brent, trigo`, código 3. ESQUEMA, seção 14, regra
        C4: «Série mais curta deixa `variacao_7d_pct` em `null` […] e o `indicadores.py` termina em `PARCIAL`.»

        brent e trigo só têm 3 dias de série. Os dois ids vêm depois de "sem base de 7 dias:".
        """
        self.so("brent", self.CURTA)
        self.so("trigo", [("2026-11-18", 551.00), ("2026-11-19", 556.00), ("2026-11-20", 559.00)])
        res, d = self.roda_e_le()
        self.confere(d, "brent", valor=74.05, variacao_7d_pct=None, defasado=False)
        self.confere(d, "trigo", valor=5.59, variacao_7d_pct=None, defasado=False)
        self.confere_veredito(res, "PARCIAL", 3)
        self.assertRegex(res.ultima, r"sem base de 7 dias: .*\bbrent\b")
        self.assertRegex(res.ultima, r"sem base de 7 dias: .*\btrigo\b")
        self.assertNotIn("sem dado", res.ultima)

    def test_parcial_com_as_duas_situacoes(self):
        """CONTRATO, seção 2, "Veredito e código": «Com as duas situações de `PARCIAL` ao mesmo tempo, a última linha
        junta as duas: `PARCIAL sem dado: milho; sem base de 7 dias: brent`.»
        """
        self.tira("milho")
        self.so("brent", self.CURTA)
        res = self.roda()
        self.confere_veredito(res, "PARCIAL", 3)
        self.assertRegex(res.ultima, r"^PARCIAL sem dado: [^;]*\bmilho\b[^;]*; sem base de 7 dias: .*\bbrent\b")

    def test_parcial_quando_so_os_de_contexto_vieram(self):
        """CONTRATO, seção 2, "Veredito e código": `FALHA sem rede` é para «nenhum indicador veio»; faltando
        obrigatório, é `PARCIAL sem dado: …`, código 3.

        Os cinco obrigatórios ficam sem fonte; gas_natural e indice_fao vêm. Não é FALHA sem rede: é
        PARCIAL, com os cinco ids.
        """
        for ident in OBRIGATORIOS:
            self.tira(ident)
        res, d = self.roda_e_le()
        self.confere_veredito(res, "PARCIAL", 3)
        for ident in OBRIGATORIOS:
            self.assertRegex(res.ultima, r"sem dado: .*\b%s\b" % ident)
        self.confere(d, "gas_natural", valor=3.12)

    def test_falha_sem_rede(self):
        """CONTRATO, seção 2, "Veredito e código": «nenhum indicador veio» → `FALHA sem rede: 0 indicadores`, código
        4; seção 0: código 4 «gravou a saída vazia; a última linha é `FALHA sem rede: …`» e «sempre gravam o
        arquivo de saída, mesmo vazio».

        respostas.json vazio. O arquivo é gravado e é JSON; não há gatilho; nenhum item traz valor. Passo 6:
        «Com `FALHA sem rede`, a "saída vazia" da seção 0 é esta: `indicadores` traz todos os itens do catálogo,
        todos assim, sem valor.»
        """
        self.b.respostas = {}
        res = self.roda()
        self.confere_veredito(res, "FALHA", 4)
        self.assertTrue(res.ultima.startswith("FALHA sem rede:"), res.ultima)
        d = self.dados(res)
        self.assertEqual(d["gatilhos"], [])
        self.assertEqual([i["id"] for i in d["indicadores"]],
                         ["brent", "trigo", "milho", "soja", "usd_brl", "gas_natural", "indice_fao"])
        self.assertEqual(d["falhas"], [{"id": i["id"], "erro": "todas as fontes falharam"} for i in d["indicadores"]])
        for item in d["indicadores"]:
            self.assertIsNone(item["valor"], item.get("id"))
            self.assertIs(item["defasado"], True)
        self.assertEqual(d.get("dia"), apoio.DIA)

    def test_catalogo_ilegivel(self):
        """CONTRATO, seção 2, "Veredito e código": «catálogo ou régua ilegível» → `FALHA …` (nada é gravado), código
        1; "Grava": «o arquivo de antes, se havia, fica como estava».

        dados/indicadores.json que não é JSON, e depois ausente. Na pasta de trabalho há um indicadores.json de
        outra execução: ele não muda.
        """
        for caso in ("não é JSON", "não existe"):
            with self.subTest(caso=caso):
                self.nova()
                if caso == "não é JSON":
                    self.b.grava_dados("indicadores.json", '{"versao": 1, "indicadores": [')
                else:
                    self.b.apaga_dados("indicadores.json")
                self.b.poe_no_trabalho("indicadores.json", {"de": "ontem"})
                res = self.roda()
                self.confere_veredito(res, "FALHA", 1)
                self.assertEqual(res.gravados(), [], res.relato())

    def test_regua_ilegivel(self):
        """CONTRATO, seção 2, "Veredito e código": «catálogo ou régua ilegível» → `FALHA …` (nada é gravado), código 1.

        dados/regua.json que não é JSON, e depois ausente.
        """
        for caso in ("não é JSON", "não existe"):
            with self.subTest(caso=caso):
                self.nova()
                if caso == "não é JSON":
                    self.b.grava_dados("regua.json", "isto não é JSON\n")
                else:
                    self.b.apaga_dados("regua.json")
                res = self.roda()
                self.confere_veredito(res, "FALHA", 1)
                self.assertEqual(res.gravados(), [], res.relato())

    def test_erro_de_uso(self):
        """CONTRATO, seção 0, "Erro de uso": «Opção errada, valor ilegível ou falta de opção obrigatória: uma linha
        `FALHA uso: …` na saída padrão e código 2. Nada é gravado.» Seção 2: «`--tempo S` é o teto de tempo total,
        em segundos inteiros, de 1 a 3600 […]. Zero, negativo, número com casa decimal ou texto é erro de uso.»
        """
        casos = (["--opcao-que-nao-existe"], ["--tempo", "x"], ["--tempo", "0"], ["--tempo", "1.5"], ["--tempo", "-5"],
                 ["--dia", "20/11/2026"], ["--dia"])
        for args in casos:
            with self.subTest(args=" ".join(args)):
                self.nova()
                res = self.b.roda("indicadores", *args)
                self.confere_veredito(res, "FALHA", 2)
                self.assertTrue(res.ultima.startswith("FALHA uso:"), res.ultima)
                self.assertEqual(res.gravados(), [])

    def test_info_agora_ilegivel(self):
        """CONTRATO, seção 0, "Relógio de teste": «Com valor ilegível, a ferramenta para com `FALHA uso: INFO_AGORA
        ilegível` e código 2.»"""
        res = self.roda(agora="2026-11-20 21:00")
        self.confere_veredito(res, "FALHA", 2)
        self.assertTrue(res.ultima.startswith("FALHA uso:"), res.ultima)
        self.assertIn("INFO_AGORA", res.ultima)
        self.assertEqual(res.gravados(), [])

    def test_opcao_json_imprime_um_objeto(self):
        """CONTRATO, seção 0, opções comuns: `--json` «imprime um objeto JSON no lugar do texto».

        A saída padrão inteira é um objeto JSON, e o código de saída é o mesmo (0). O contrato não diz
        que chaves esse objeto tem em indicadores.py: o teste não confere nenhuma.
        """
        res = self.roda("--json")
        self.assertEqual(res.codigo, 0, res.relato())
        try:
            objeto = json.loads(res.saida)
        except ValueError as erro:
            self.fail("a saída padrão com --json não é JSON: %s%s" % (erro, res.relato()))
        self.assertIsInstance(objeto, dict)
        self.assertIn("indicadores.json", res.arquivos)


if __name__ == "__main__":
    unittest.main()
