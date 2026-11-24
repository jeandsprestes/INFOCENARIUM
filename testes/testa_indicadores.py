#!/usr/bin/env python3
"""Testes de ferramentas/indicadores.py (CONTRATO, seção 2).

Rodar da raiz do repositório: python3 -B testes/testa_indicadores.py
Sempre --offline, com raiz e pasta de trabalho temporárias e relógio fixo (INFO_AGORA).
As respostas de testes/fixtures/indicadores/amostras/ foram colhidas das fontes do catálogo em 23/11/2026.
"""
import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta

sys.dont_write_bytecode = True
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FERRAMENTAS = os.path.join(RAIZ, "ferramentas")
sys.path.insert(0, FERRAMENTAS)

import indicadores  # noqa: E402

DADOS = os.path.join(RAIZ, "testes", "fixtures", "dados")
AMOSTRAS = os.path.join(RAIZ, "testes", "fixtures", "indicadores", "amostras")
DIA = "2026-11-20"  # uma sexta-feira
AGORA = "2026-11-20T21:05:00Z"
SITE = "https://precos.exemplo.invalid/"
SUFIXO = " Alta maior sem confirmação de segunda fonte."


def antes(dias):
    return (date(2026, 11, 20) - timedelta(days=dias)).isoformat()


def fred(*pontos):
    """Corpo no formato do leitor fred_csv, a partir de pares (dias antes de DIA, valor)."""
    linhas = ["observation_date,SERIE"] + ["%s,%s" % (antes(dias), valor) for dias, valor in pontos]
    return ("\n".join(linhas) + "\n").encode("utf-8")


def calma(valor=100.0):
    """Série de 12 dias, parada: tem base de 7 dias e nenhuma alta."""
    return fred(*[(dias, valor) for dias in range(11, -1, -1)])


def alta(pct_7d, pct_1d=0.0, base=100.0, ultimo_dia=0):
    """Série com a alta pedida em 7 dias e no último dia, terminando `ultimo_dia` dias antes de DIA."""
    fim = base * (1 + pct_7d / 100.0)
    ontem = fim / (1 + pct_1d / 100.0)
    return fred((ultimo_dia + 9, base), (ultimo_dia + 7, base), (ultimo_dia + 1, round(ontem, 6)),
                (ultimo_dia, round(fim, 6)))


def fonte(nome, leitor="fred_csv", **mais):
    return dict({"nome": "Fonte %s" % nome, "url": SITE + nome, "leitor": leitor}, **mais)


def indicador(ident, fontes, nome=None, dominio="energia", obrigatorio=True, frequencia="diaria",
              faixa=(1, 1000), **mais):
    nomes = {"brent": "Petróleo Brent", "usd_brl": "Dólar em reais", "trigo": "Trigo", "milho": "Milho"}
    return dict({"id": ident, "nome": nome or nomes.get(ident, ident.capitalize()), "unidade": "unidade de teste",
                 "dominio": dominio, "obrigatorio": obrigatorio, "frequencia": frequencia,
                 "faixa": {"min": faixa[0], "max": faixa[1]}, "fontes": fontes}, **mais)


class Caso(unittest.TestCase):
    """Raiz temporária com a cópia congelada de dados/, pasta de trabalho e pasta do --offline."""

    def setUp(self):
        temporaria = tempfile.TemporaryDirectory(prefix="info-indicadores-")
        self.addCleanup(temporaria.cleanup)
        self.pasta = os.path.realpath(temporaria.name)
        self.raiz = os.path.join(self.pasta, "raiz")
        self.trabalho = os.path.join(self.pasta, "trabalho")
        self.off = os.path.join(self.pasta, "off")
        shutil.copytree(DADOS, os.path.join(self.raiz, "dados"))
        os.makedirs(self.off)
        self.respostas({})

    def grava(self, caminho, conteudo):
        with open(caminho, "wb") as arquivo:
            arquivo.write(conteudo if isinstance(conteudo, bytes) else conteudo.encode("utf-8"))

    def catalogo(self, *itens):
        self.grava(os.path.join(self.raiz, "dados", "indicadores.json"),
                   json.dumps({"versao": 1, "atualizado_em": DIA, "regra": "teste", "indicadores": list(itens)}))

    def respostas(self, corpos, **outras):
        """corpos: nome curto da fonte -> bytes do corpo. outras: nome curto -> entrada pronta do respostas.json."""
        mapa = {}
        for nome, corpo in corpos.items():
            self.grava(os.path.join(self.off, nome + ".txt"), corpo)
            mapa[SITE + nome] = nome + ".txt"
        for nome, entrada in outras.items():
            mapa[SITE + nome] = entrada
        self.grava(os.path.join(self.off, "respostas.json"), json.dumps(mapa))

    def roda(self, *opcoes, agora=AGORA, dia=DIA, off=None, ferramenta=None, **ambiente):
        """Chama a ferramenta como a rotina chama. Devolve (código, linhas da saída, o arquivo gravado ou None)."""
        comando = [sys.executable, ferramenta or os.path.join(FERRAMENTAS, "indicadores.py"),
                   "--raiz", self.raiz, "--trabalho", self.trabalho]
        if off is not False:
            comando += ["--offline", off or self.off]
        if dia:
            comando += ["--dia", dia]
        base = {k: v for k, v in os.environ.items() if k != "INFO_AGORA"}
        base.update(PYTHONDONTWRITEBYTECODE="1", **ambiente)
        if agora:
            base["INFO_AGORA"] = agora
        feito = subprocess.run(comando + list(opcoes), env=base, cwd=self.pasta, stdin=subprocess.DEVNULL,
                               capture_output=True, timeout=120)
        self.assertEqual(feito.stderr.decode("utf-8", "replace"), "")
        return feito.returncode, feito.stdout.decode("utf-8").splitlines(), self.gravado()

    def gravado(self):
        caminho = os.path.join(self.trabalho, "indicadores.json")
        if not os.path.exists(caminho):
            return None
        with open(caminho, encoding="utf-8") as arquivo:
            return json.load(arquivo)

    def um(self, objeto, ident):
        return [linha for linha in objeto["indicadores"] if linha["id"] == ident][0]


class TestaAmostrasDoDia(Caso):
    """O catálogo congelado contra as respostas de verdade de 23/11/2026."""

    def roda_dia(self, **nomeados):
        return self.roda(off=AMOSTRAS, dia="2026-11-23", agora="2026-11-23T21:07:00Z", **nomeados)

    def test_os_12_indicadores_do_dia(self):
        codigo, linhas, objeto = self.roda_dia()
        self.assertEqual((codigo, linhas[-1]), (0, "OK 12 indicadores, 1 gatilho de preço"))
        esperado = [  # id, valor, variação, 7 dias, data, fonte
            ("brent", 87.3, -5.7, -5.6, "2026-11-23", "Yahoo Finance"),
            ("wti", 80.85, -3.7, -5.7, "2026-11-23", "Yahoo Finance"),
            ("gas_natural", 3.51, 2.8, 12.3, "2026-11-23", "Yahoo Finance"),
            ("trigo", 218.3, 3.5, 1.2, "2026-11-23", "Yahoo Finance"),
            ("milho", 177.2, 3.6, 0.3, "2026-11-23", "Yahoo Finance"),
            ("soja", 451.1, 0.6, -0.1, "2026-11-23", "Yahoo Finance"),
            ("fao_ffpi", 133.9, -1.3, None, "2026-10-01", "FAO (agência da ONU para a alimentação)"),
            ("usd_brl", 5.9708, 1.4, 4.2, "2026-11-23", "Banco Central do Brasil"),
            ("dxy", 104.48, 0.6, 0.9, "2026-11-23", "Yahoo Finance"),
            ("ouro", 3661.3, 4.2, -5.0, "2026-11-23", "Yahoo Finance"),
            ("vix", 27.15, -24.4, 18.5, "2026-11-23", "Yahoo Finance"),
            ("frete_seco", 12.66, 4.5, 0.5, "2026-11-23", "Yahoo Finance"),
        ]
        achado = [(i["id"], i["valor"], i["variacao_pct"], i["variacao_7d_pct"], i["data"], i["fonte"]["nome"])
                  for i in objeto["indicadores"]]
        self.assertEqual(achado, esperado)
        self.assertTrue(all(not i["defasado"] and not i["confirmado"] for i in objeto["indicadores"]))
        self.assertEqual(objeto["gatilhos"], [{"criterio": "cambio.2", "ref": "usd_brl",
                                               "texto": "Dólar em reais subiu 4,2% em 7 dias, até 23/11 (limiar: 3%)."}])
        self.assertEqual(objeto["falhas"], [])

    def test_formato_do_arquivo_e_ordem_das_chaves(self):
        self.roda_dia()
        with open(os.path.join(self.trabalho, "indicadores.json"), "rb") as arquivo:
            bruto = arquivo.read()
        objeto = json.loads(bruto.decode("utf-8"))
        self.assertFalse(bruto.startswith(b"\xef\xbb\xbf"))
        self.assertTrue(bruto.endswith(b"}\n"))
        self.assertIn('\n  "dia": "2026-11-23",\n', bruto.decode("utf-8"))
        self.assertIn("Petróleo Brent".encode("utf-8"), bruto)
        self.assertEqual(list(objeto), ["versao", "dia", "gerada_em", "indicadores", "gatilhos", "falhas", "avisos"])
        self.assertEqual(objeto["avisos"], [])  # as amostras não trazem os contratos com data: nada foi medido neles
        self.assertEqual((objeto["versao"], objeto["dia"], objeto["gerada_em"]), (1, "2026-11-23", "2026-11-23T21:07:00Z"))
        self.assertEqual(list(objeto["indicadores"][0]), ["id", "nome", "dominio", "valor", "unidade", "variacao_pct",
                                                          "variacao_7d_pct", "data", "defasado", "confirmado", "fonte"])
        self.assertEqual(list(objeto["indicadores"][0]["fonte"]), ["nome", "url"])
        with open(os.path.join(DADOS, "indicadores.json"), encoding="utf-8") as arquivo:
            catalogo = json.load(arquivo)["indicadores"]
        self.assertEqual([(i["id"], i["nome"], i["dominio"], i["unidade"]) for i in objeto["indicadores"]],
                         [(c["id"], c["nome"], c["dominio"], c["unidade"]) for c in catalogo])

    def test_mesma_entrada_mesmos_bytes(self):
        def bytes_do_arquivo():
            self.roda_dia()
            with open(os.path.join(self.trabalho, "indicadores.json"), "rb") as arquivo:
                return arquivo.read()

        self.assertEqual(bytes_do_arquivo(), bytes_do_arquivo())

    def test_no_dia_seguinte_so_com_o_fred_os_obrigatorios_ficam_sem_dado(self):
        # Sem Yahoo e sem Banco Central, sobram as séries semanais do FRED, que param em 13/11 e 17/11.
        with open(os.path.join(AMOSTRAS, "respostas.json"), encoding="utf-8") as arquivo:
            todas = json.load(arquivo)
        mapa = {}
        for url, nome in todas.items():
            if "fred" in nome or "fao" in nome:
                shutil.copy(os.path.join(AMOSTRAS, nome), self.off)
                mapa[url] = nome
        self.grava(os.path.join(self.off, "respostas.json"), json.dumps(mapa))
        codigo, linhas, objeto = self.roda(dia="2026-11-24", agora="2026-11-24T21:07:00Z")
        self.assertEqual((codigo, linhas[-1]), (3, "PARCIAL sem dado: brent, trigo, milho, soja, usd_brl"))
        brent, dolar, vix = self.um(objeto, "brent"), self.um(objeto, "usd_brl"), self.um(objeto, "vix")
        self.assertEqual((brent["valor"], brent["data"], brent["defasado"], brent["variacao_7d_pct"]),
                         (92.94, "2026-11-17", True, 3.1))
        self.assertEqual((dolar["valor"], dolar["data"], dolar["defasado"], dolar["fonte"]["nome"]),
                         (5.6449, "2026-11-13", True, "FRED (Fed de St. Louis)"))
        self.assertEqual((vix["valor"], vix["data"], vix["defasado"], vix["variacao_7d_pct"]),
                         (35.89, "2026-11-20", False, 86.0))
        self.assertEqual(objeto["gatilhos"], [])  # o VIX subiu 86%, mas não há critério de preço para ele
        self.assertEqual([f for f in objeto["falhas"] if f["id"] in ("trigo", "dxy")],
                         [{"id": "trigo", "erro": "todas as fontes falharam"},
                          {"id": "dxy", "erro": "todas as fontes falharam"}])
        self.assertEqual(self.um(objeto, "trigo")["fonte"]["nome"], "Yahoo Finance")  # a primeira do catálogo


class TestaLeitores(unittest.TestCase):
    """Os 6 leitores, com as respostas colhidas e com as formas tortas que uma fonte pode mandar."""

    def serie(self, leitor, corpo, fator=1.0, dia="2026-11-23"):
        if isinstance(corpo, str) and corpo.endswith((".csv", ".json")) and "\n" not in corpo:
            with open(os.path.join(AMOSTRAS, corpo), "rb") as arquivo:
                corpo = arquivo.read()
        return indicadores.serie(leitor, corpo if isinstance(corpo, bytes) else corpo.encode("utf-8"), fator, dia)

    def test_fred_csv(self):
        pontos = self.serie("fred_csv", "brent.fred_csv.csv")
        self.assertEqual((len(pontos), pontos[0], pontos[-1]), (34, ("2026-10-01", 114.82), ("2026-11-17", 92.94)))
        dolar = self.serie("fred_csv", "usd_brl.fred_csv.csv")  # 32 linhas, 2 de feriado com valor vazio
        self.assertEqual((len(dolar), dolar[-1]), (30, ("2026-11-13", 5.6449)))
        self.assertNotIn("2026-10-12", dict(dolar))
        torto = "observation_date,X\r\n2026-11-02,.\r\n2026-11-03,\r\n2026-11-04,7.5\r\n2026-11-05,abc\r\n" \
                "2026-11-06,nan\r\n2026-11-09,inf\r\n2026-11-10,1_0\r\n2026-11-11,-3\r\n2026-11-12,0\r\n" \
                "2026-13-45,9\r\n2026-11-13, 8.25 \r\nlixo\r\n,,,\r\n2026-11-16,1e400\r\n2026-11-17,2e1\r\n"
        self.assertEqual(self.serie("fred_csv", torto), [("2026-11-04", 7.5), ("2026-11-13", 8.25), ("2026-11-17", 20.0)])
        self.assertEqual(self.serie("fred_csv", "<html><body>Access denied</body></html>"), [])
        self.assertEqual(self.serie("fred_csv", b""), [])

    def test_yahoo_chart(self):
        pontos = self.serie("yahoo_chart", "brent.yahoo_chart.json")
        self.assertEqual((len(pontos), pontos[0][0], pontos[-1][0]), (22, "2026-10-23", "2026-11-23"))
        self.assertEqual((round(pontos[0][1], 2), round(pontos[-1][1], 2)), (116.72, 87.3))
        dxy = self.serie("yahoo_chart", "dxy.yahoo_chart.json")  # 27 carimbos, 5 fechamentos null
        self.assertEqual((len(dxy), round(dxy[-1][1], 3)), (22, 104.479))
        dolar = self.serie("yahoo_chart", "usd_brl.yahoo_chart.json")
        # 22/10 23:00 UTC é meia-noite de 23/10 em Londres, o fuso da bolsa (meta.exchangeTimezoneName)
        self.assertEqual(dolar[0][0], "2026-10-23")
        trigo = self.serie("yahoo_chart", "trigo.yahoo_chart.json", fator=0.3674371)  # a resposta inteira
        self.assertEqual((len(trigo), round(trigo[-1][1], 1)), (22, 218.3))

        def chart(instantes, fechamentos):
            return json.dumps({"chart": {"result": [{"timestamp": instantes, "indicators": {"quote": [
                {"close": fechamentos}]}}], "error": None}})

        dia_19, dia_20 = 1795046400, 1795132800  # 00:00 UTC de 19/11 e de 20/11 de 2026
        self.assertEqual(self.serie("yahoo_chart", chart([dia_19, dia_20, dia_20 + 50000], [10, 11, 12])),
                         [("2026-11-19", 10.0), ("2026-11-20", 12.0)])  # dois carimbos no dia: vale o último
        self.assertEqual(self.serie("yahoo_chart", chart([dia_19, True, "x", None, -5, 9e18, dia_20],
                                                         [None, 1, 2, 3, 4, 5, "6.5"])), [("2026-11-20", 6.5)])
        self.assertEqual(self.serie("yahoo_chart", chart([dia_19, dia_20], [True, False])), [])
        self.assertEqual(self.serie("yahoo_chart", chart([dia_19], [5]), dia="2026-11-18"), [])  # depois de --dia
        for torta in ('{"chart": {"result": null, "error": {"code": "Not Found"}}}', '{"chart": {"result": []}}',
                      "[]", "7", '"texto"', "null", '{"chart": {"result": [{"timestamp": 5}]}}',
                      '{"chart": {"result": [{"timestamp": [1], "indicators": {"quote": [{"close": 7}]}}]}}'):
            self.assertEqual(self.serie("yahoo_chart", torta), [], torta)
        for quebrada in ("", "{", "<html>Too Many Requests</html>", '{"chart": NaN}', "[" * 100000, "1" * 5000):
            self.assertIsNone(self.serie("yahoo_chart", quebrada), quebrada[:20])
        self.assertEqual(self.serie("yahoo_chart", chart([dia_20], [float("nan")]).replace("NaN", "Infinity")), None)

    def test_yahoo_chart_no_fuso_da_bolsa(self):
        def chart(instantes, meta):
            return json.dumps({"chart": {"result": [{"meta": meta, "timestamp": instantes, "indicators": {"quote": [
                {"close": [10.0] * len(instantes)}]}}], "error": None}})

        meia_noite_de_londres = 1792710000  # 22/10/2026 23:00 UTC: em Londres, horário de verão, já é 23/10
        casos = [  # meta, dia esperado
            ({"exchangeTimezoneName": "Europe/London", "gmtoffset": 0}, "2026-10-23"),  # o nome vence o desvio
            ({"gmtoffset": 3600}, "2026-10-23"),  # sem o nome, o desvio fixo
            ({"exchangeTimezoneName": "Lugar/Inventado", "gmtoffset": 3600}, "2026-10-23"),  # nome que a base não tem
            ({"exchangeTimezoneName": "../../etc/passwd", "gmtoffset": -18000}, "2026-10-22"),  # nome torto: o desvio
            ({"exchangeTimezoneName": "America/New_York"}, "2026-10-22"),
            ({}, "2026-10-22"), ({"gmtoffset": "3600"}, "2026-10-22"), ({"gmtoffset": 10 ** 9}, "2026-10-22"),
            ({"gmtoffset": True}, "2026-10-22"), (None, "2026-10-22"), ("meta", "2026-10-22"),  # sem os dois: UTC
        ]
        for meta, esperado in casos:
            pontos = self.serie("yahoo_chart", chart([meia_noite_de_londres], meta), dia="2026-11-23")
            self.assertEqual(pontos, [(esperado, 10.0)], meta)

    def test_yahoo_chart_sem_a_base_de_fusos_usa_o_desvio(self):
        vazia = tempfile.mkdtemp(prefix="info-sem-fusos-")
        self.addCleanup(shutil.rmtree, vazia)
        programa = ("import sys; sys.dont_write_bytecode = True; sys.path.insert(0, %r); import indicadores, json; "
                    "c = lambda meta: json.dumps({'chart': {'result': [{'meta': meta, 'timestamp': [1792710000], "
                    "'indicators': {'quote': [{'close': [5]}]}}]}}).encode(); "
                    "print(indicadores.serie('yahoo_chart', c({'exchangeTimezoneName': 'Europe/London', 'gmtoffset': 0}), 1.0, '2026-11-23'), "
                    "indicadores.serie('yahoo_chart', c({'exchangeTimezoneName': 'Europe/London'}), 1.0, '2026-11-23'))"
                    % FERRAMENTAS)
        feito = subprocess.run([sys.executable, "-B", "-c", programa], capture_output=True, timeout=60,
                               env=dict(os.environ, PYTHONTZPATH=vazia))
        self.assertEqual(feito.stderr, b"")
        # Sem a base, Europe/London não abre: vale o gmtoffset (0, o desvio de hoje), e sem ele o dia em UTC.
        self.assertEqual(feito.stdout.decode().strip(), "[('2026-10-22', 5.0)] [('2026-10-22', 5.0)]")

    def test_cnbc_chart(self):
        pontos = self.serie("cnbc_chart", "milho.cnbc_chart.json", fator=0.3936826)
        self.assertEqual((len(pontos), pontos[-1][0], round(pontos[-1][1], 2)), (15, "2026-11-20", 176.67))

        def barras(*lista):
            return json.dumps({"barData": {"symbol": "1", "priceBars": list(lista)}, "requestDetails": {}})

        self.assertEqual(self.serie("cnbc_chart", barras(
            {"tradeTime": "20261119000000", "close": "439.0000"}, {"tradeTime": "20261120", "close": 448.75},
            {"tradeTime": "20261118000000"}, {"close": "1.0"}, {"tradeTime": "20261117000000", "close": None},
            {"tradeTime": 20261116000000, "close": "2.0"}, {"tradeTime": "2026-11-13", "close": "3.0"},
            {"tradeTime": "20261345000000", "close": "4.0"}, {"tradeTime": "20261112000000", "close": "abc"},
            {"tradeTime": "20261111000000", "close": "-1"}, "barra", None,
            {"tradeTime": "20261121000000", "close": "9.0"}), dia="2026-11-20"),  # a de 21/11 é depois de --dia
            [("2026-11-19", 439.0), ("2026-11-20", 448.75)])
        # dois pontos na mesma data: fica o último da resposta (entre os que têm valor)
        self.assertEqual(self.serie("cnbc_chart", barras({"tradeTime": "20261120000000", "close": "1.0"},
                                                         {"tradeTime": "20261120120000", "close": "2.0"},
                                                         {"tradeTime": "20261120180000", "close": None})),
                         [("2026-11-20", 2.0)])
        for torta in ('{"barData": null}', '{"barData": {"priceBars": "x"}}', "[]", '{"erro": 1}', "7"):
            self.assertEqual(self.serie("cnbc_chart", torta), [], torta)
        self.assertIsNone(self.serie("cnbc_chart", "<html>"))

    def test_bcb_sgs(self):
        pontos = self.serie("bcb_sgs", "usd_brl.bcb_sgs.json")
        self.assertEqual((len(pontos), pontos[0], pontos[-1]), (20, ("2026-10-23", 5.0377), ("2026-11-23", 5.9708)))
        torto = json.dumps([{"data": "20/11/2026", "valor": "5.5"}, {"data": "2026-11-19", "valor": "5.4"},
                            {"data": "31/02/2026", "valor": "5.3"}, {"data": "18/11/2026"}, {"valor": "5.2"},
                            "texto", None, {"data": 20112026, "valor": "5.1"}, {"data": "17/11/2026", "valor": 5.0}])
        self.assertEqual(self.serie("bcb_sgs", torto), [("2026-11-17", 5.0), ("2026-11-20", 5.5)])
        self.assertEqual(self.serie("bcb_sgs", '{"erro": "400"}'), [])

    def test_eia_v2(self):
        pontos = self.serie("eia_v2", "brent.eia_v2.json")  # vem do mais novo para o mais velho
        self.assertEqual((len(pontos), pontos[-1], pontos[-2]), (15, ("2026-11-17", 92.94), ("2026-11-16", 92.9)))
        self.assertEqual([p[0] for p in pontos], sorted(p[0] for p in pontos))
        self.assertEqual(pontos[0][0], "2026-10-28")
        for torta in ('{"response": {"data": "x"}}', '{"response": null}', '{"error": "API_KEY_INVALID"}', "[]"):
            self.assertEqual(self.serie("eia_v2", torta), [], torta)

    def test_fao_csv(self):
        pontos = self.serie("fao_csv", "fao_ffpi.fao_csv.csv")  # com BOM, CRLF e as vírgulas do fim
        self.assertEqual((len(pontos), pontos[0], pontos[-1], pontos[-2]),
                         (22, ("1990-01-01", 64.4), ("2026-10-01", 133.9), ("2026-09-01", 135.6)))
        sem_vinculas = "FAO Food Price Index\n2014-2016=100\nDate,Food Price Index,Meat\n\n2026-09,135.6,1\n" \
                       "2026-10,,2\n2026-11,133.9,3\n2026-12,140,4\n"
        self.assertEqual(self.serie("fao_csv", sem_vinculas, dia="2026-11-23"),
                         [("2026-09-01", 135.6), ("2026-11-01", 133.9)])

    def test_fator_e_valor_que_deixa_de_ser_preco(self):
        self.assertEqual(indicadores.serie("fred_csv", b"x\n2026-11-20,200\n", 0.5, DIA), [("2026-11-20", 100.0)])
        self.assertEqual(indicadores.serie("fred_csv", b"x\n2026-11-20,1e300\n", 1e300, DIA), [])  # estoura: infinito

    def test_numero_e_arredondamento(self):
        self.assertEqual([indicadores.numero(v) for v in ("5.8889", " 7 ", "+2.5", ".5", "1e2", 3, 2.5)],
                         [5.8889, 7.0, 2.5, 0.5, 100.0, 3.0, 2.5])
        for ruim in ("", ".", "-1", "0", "nan", "inf", "Infinity", "1_000", "0x10", "1,5", "5 6", None, True, [], {},
                     float("nan"), float("inf"), -2, 0, 10 ** 400):
            self.assertIsNone(indicadores.numero(ruim), repr(ruim)[:20])
        self.assertEqual([indicadores.arredonda(v, 1) for v in (6.25, 6.35, 0.05, -0.04, 4.96, 4.94, -6.25)],
                         [6.3, 6.4, 0.1, 0.0, 5.0, 4.9, -6.3])
        self.assertEqual(str(indicadores.arredonda(-0.04, 1)), "0.0")
        self.assertEqual((indicadores.arredonda(3.505, 2), indicadores.arredonda(218.3495, 1), indicadores.arredonda(87.5, 0)),
                         (3.51, 218.3, 88.0))
        self.assertEqual([indicadores.em_portugues(v) for v in (5.0, 1.5, 20, 0.25)], ["5", "1,5", "20", "0,25"])
        self.assertEqual((indicadores.em_portugues(6.1, 1), indicadores.em_portugues(6.0, 1)), ("6,1", "6,0"))


class TestaArredondamento(unittest.TestCase):
    """CONTRATO, seção 2, passo 4: metade para longe do zero, em decimal; a conta é sobre os pontos crus."""

    def test_meio_vai_para_longe_do_zero(self):
        self.assertEqual([indicadores.variacao(n, 400.0) for n in (401.0, 399.0, 421.0, 379.0)], [0.3, -0.3, 5.3, -5.3])
        self.assertEqual([indicadores.variacao(n, 100.0) for n in (100.25, 99.75, 104.95, 104.94999)], [0.3, -0.3, 5.0, 4.9])
        self.assertEqual(indicadores.variacao(108.15, 103.0), 5.0)  # 4,99999… em binário; 5,0 em decimal
        self.assertEqual([indicadores.arredonda(v, 1) for v in (0.25, -0.25, 0.35, -0.35, 2.675)], [0.3, -0.3, 0.4, -0.4, 2.7])
        self.assertEqual(indicadores.arredonda(2.675, 2), 2.68)  # round(2.675, 2) do Python dá 2.67

    def test_variacao_sobre_os_pontos_crus_e_nao_sobre_o_valor_arredondado(self):
        medida = indicadores.mede([(antes(7), 100.06), (antes(0), 105.04)], False)
        self.assertEqual(medida["7d"], 5.0)  # 105,04 / 100,06 = +4,977 → 5,0; pelos valores de 1 casa (105,0 / 100,1), 4,9
        medida = indicadores.mede([(antes(7), 0.204), (antes(0), 0.214)], False)
        self.assertEqual(medida["7d"], 4.9)  # 0,214 / 0,204 = +4,90; com 2 casas (0,21 / 0,20) daria +5,0

    def test_perto_e_meio_por_cento(self):
        self.assertTrue(indicadores.perto(100.5, 100.0) and indicadores.perto(99.5, 100.0))
        self.assertFalse(indicadores.perto(100.51, 100.0) or indicadores.perto(99.49, 100.0))


class TestaCandidatosDeContrato(unittest.TestCase):
    """CONTRATO, seção 2, "Troca de contrato", item 1, e a forma do campo contratos (ESQUEMA, seção 14, C6)."""

    def test_os_4_primeiros_a_partir_do_mes_do_dia(self):
        self.assertEqual(indicadores.candidatos("HKNUZ", "2026-11-23"), ["Z26", "H27", "K27", "N27"])
        self.assertEqual(indicadores.candidatos("HKNUZ", "2026-12-01"), ["Z26", "H27", "K27", "N27"])
        self.assertEqual(indicadores.candidatos("HKNUZ", "2026-12-31"), ["Z26", "H27", "K27", "N27"])
        self.assertEqual(indicadores.candidatos("FGHJKMNQUVXZ", "2026-11-23"), ["X26", "Z26", "F27", "G27"])
        self.assertEqual(indicadores.candidatos("FHKNQUX", "2026-11-02"), ["X26", "F27", "H27", "K27"])
        self.assertEqual(indicadores.candidatos("Z", "2026-11-23"), ["Z26", "Z27", "Z28", "Z29"])
        self.assertEqual(indicadores.candidatos("GJMQVZ", "2099-12-10"), ["Z99", "G00", "J00", "M00"])

    def test_forma_do_campo(self):
        modelo = "https://precos.exemplo.invalid/chart/ZC{c}.CBT?range=1mo"
        self.assertTrue(indicadores.contratos_validos({"modelo": modelo, "meses": "HKNUZ"}))
        self.assertTrue(indicadores.contratos_validos({"meses": "FGHJKMNQUVXZ", "modelo": modelo}))
        for torto in (None, "HKNUZ", [], {}, {"modelo": modelo}, {"modelo": modelo, "meses": "HKNUZ", "nota": "x"},
                      {"modelo": modelo.replace("{c}", ""), "meses": "Z"}, {"modelo": modelo + "{c}", "meses": "Z"},
                      {"modelo": "ftp://x.exemplo.invalid/{c}", "meses": "Z"},
                      {"modelo": modelo, "meses": ""}, {"modelo": modelo, "meses": "ZH"}, {"modelo": modelo, "meses": "HH"},
                      {"modelo": modelo, "meses": "hk"}, {"modelo": modelo, "meses": "A"}, {"modelo": modelo, "meses": 5},
                      {"modelo": modelo, "meses": "FGHJKMNQUVXZF"}, {"modelo": 7, "meses": "Z"}):
            self.assertFalse(indicadores.contratos_validos(torto), torto)

    def test_a_troca_dentro_e_fora_da_janela(self):
        dias = [antes(n) for n in (10, 9, 8, 7, 3, 2, 1, 0)]
        serie = list(zip(dias, (90.0, 91.0, 92.0, 93.0, 94.0, 95.0, 103.0, 104.0)))  # troca entre antes(2) e antes(1)
        contrato = list(zip(dias, (98.0, 99.0, 100.0, 101.0, 102.0, 103.0, 103.2, 104.1)))
        medida = indicadores.mede(serie, False)
        nova, troca, motivo = indicadores.mede_no_contrato(serie, contrato, medida)
        self.assertEqual((troca, nova["1d"], nova["7d"], nova["data"], nova["cru"]), (antes(1), 0.9, 3.1, DIA, 104.0))
        self.assertEqual((medida["1d"], medida["7d"]), (1.0, 11.8))  # na série, o degrau vira alta
        contrato_desde_cedo = list(zip(dias, (90.0, 91.0, 92.0, 93.0, 94.0, 95.0, 103.0, 104.0)))
        self.assertEqual(indicadores.mede_no_contrato(serie, contrato_desde_cedo, medida)[0], None)  # sem troca na janela
        troca_velha = list(zip(dias, (1.0, 1.0, 1.0, 93.0, 94.0, 95.0, 103.0, 104.0)))  # troca antes das bases
        self.assertEqual(indicadores.mede_no_contrato(serie, troca_velha, medida)[::2], (None, "a troca foi antes dos pontos de base"))
        sem_base = contrato[4:]  # o contrato não tem o ponto de 7 dias
        self.assertEqual(indicadores.mede_no_contrato(serie, sem_base, medida)[::2], (None, "o contrato não tem os pontos de base"))


class TestaConta(unittest.TestCase):
    """Passo 4: a variação de 7 dias usa o ponto mais novo com data de 7 a 10 dias antes."""

    def mede(self, *pontos, mensal=False):
        return indicadores.mede([(antes(dias), valor) for dias, valor in pontos], mensal)

    def test_base_de_7_a_10_dias(self):
        self.assertEqual(self.mede((11, 50), (10, 80), (8, 100), (3, 104), (0, 110))["7d"], 10.0)  # base: 8 dias antes
        self.assertEqual(self.mede((10, 80), (0, 100))["7d"], 25.0)
        self.assertEqual(self.mede((7, 80), (0, 100))["7d"], 25.0)
        self.assertEqual(self.mede((9, 50), (7, 80), (0, 100))["7d"], 25.0)  # o mais novo da faixa
        self.assertIsNone(self.mede((11, 80), (6, 90), (0, 100))["7d"])
        self.assertIsNone(self.mede((6, 90), (0, 100))["7d"])
        self.assertIsNone(self.mede((0, 100))["7d"])

    def test_a_conta_parte_da_data_do_ultimo_ponto_e_nao_do_dia(self):
        self.assertEqual(self.mede((12, 80), (3, 100))["7d"], 25.0)  # 9 dias antes do último ponto

    def test_variacao_sobre_o_ponto_anterior(self):
        self.assertEqual(self.mede((5, 100), (0, 101.3))["1d"], 1.3)
        self.assertIsNone(self.mede((0, 100))["1d"])
        self.assertEqual(self.mede((1, 100), (0, 90))["1d"], -10.0)

    def test_mensal_nunca_tem_variacao_de_7_dias(self):
        medida = self.mede((38, 135.6), (8, 133.9), (0, 134.0), mensal=True)
        self.assertEqual((medida["7d"], medida["1d"]), (None, 0.1))


class TestaPontoForaDaSerie(Caso):
    """CONTRATO, seção 2, passo 4: ponto de base fora de 0,5 a 2 vezes os dois vizinhos dele na série é tique da
    fonte (um decimal deslocado): a variação que o usa sai null, com aviso. Um choque real não é tique."""

    def mede(self, *pontos):
        return indicadores.mede([(antes(dias), valor) for dias, valor in pontos], False)

    def test_tique_na_base_de_7_dias(self):
        medida = self.mede((9, 92.44), (8, 92.0), (7, 9.244), (6, 92.5), (1, 92.1), (0, 87.3))
        self.assertEqual((medida["7d"], medida["base_7d"], medida["fora"]), (None, None, [("7d", antes(7))]))
        self.assertEqual(medida["1d"], -5.2)  # a outra variação segue
        self.assertEqual(indicadores.textos_fora_da_serie(medida),
                         ["ponto de 13/11 fora da série: variação de 7 dias sem base"])

    def test_tique_no_ponto_anterior(self):
        medida = self.mede((8, 100), (7, 100), (2, 100), (1, 1000), (0, 101))
        self.assertEqual((medida["1d"], medida["base_1d"], medida["7d"]), (None, None, 1.0))
        self.assertEqual(medida["fora"], [("1d", antes(1))])

    def test_choque_real_e_vizinho_estranho_de_um_lado_so_nao_sao_tique(self):
        medida = self.mede((8, 80), (7, 80), (1, 85), (0, 92))  # +15% em 7 dias: alta forte, não tique
        self.assertEqual((medida["7d"], medida["fora"]), (15.0, []))
        medida = self.mede((8, 100), (7, 100), (6, 210), (1, 210), (0, 200))  # a base bate com um dos vizinhos
        self.assertEqual((medida["7d"], medida["1d"], medida["fora"]), (100.0, -4.8, []))
        medida = self.mede((7, 9.0), (6, 100), (0, 100))  # o primeiro ponto tem um vizinho só: não é julgado
        self.assertEqual(medida["fora"], [])
        self.assertTrue(indicadores.fora_da_serie([(1, 100), (2, 40), (3, 100)], 1))
        self.assertFalse(indicadores.fora_da_serie([(1, 100), (2, 50), (3, 100)], 1))  # 0,5 vez: a borda vale
        self.assertFalse(indicadores.fora_da_serie([(1, 100), (2, 200), (3, 100)], 1))  # 2 vezes: a borda vale

    def test_tique_nao_vira_gatilho_e_sai_nos_avisos(self):
        # o caso da revisão: o fechamento de 7 dias antes com o decimal deslocado dava +844% e gatilho de energia
        self.catalogo(indicador("brent", [fonte("a"), fonte("b")]))
        self.respostas({"a": fred((9, 92.44), (8, 92.0), (7, 9.244), (6, 92.5), (1, 92.1), (0, 87.3)), "b": alta(-3.4)})
        codigo, linhas, objeto = self.roda()
        linha = self.um(objeto, "brent")
        self.assertEqual((linha["valor"], linha["variacao_pct"], linha["variacao_7d_pct"]), (87.3, -5.2, None))
        self.assertEqual(objeto["gatilhos"], [])
        self.assertEqual(objeto["falhas"], [{"id": "brent", "erro": "sem base de 7 dias"}])
        self.assertEqual(objeto["avisos"], ["brent: ponto de 13/11 fora da série: variação de 7 dias sem base."])
        self.assertIn("aviso: brent · Fonte a: ponto de 13/11 fora da série: variação de 7 dias sem base", linhas)
        self.assertEqual((codigo, linhas[-1]), (3, "PARCIAL sem base de 7 dias: brent"))

    def test_choque_real_continua_dando_gatilho(self):
        self.catalogo(indicador("brent", [fonte("a")]))
        self.respostas({"a": fred((9, 80), (8, 80), (7, 80), (6, 81), (1, 85), (0, 89.6))})
        codigo, linhas, objeto = self.roda()
        self.assertEqual(self.um(objeto, "brent")["variacao_7d_pct"], 12.0)
        self.assertEqual([g["criterio"] for g in objeto["gatilhos"]], ["energia.2"])
        self.assertEqual(objeto["avisos"], [])


class TestaEscolhaDaFonte(Caso):
    def test_primeira_fonte_que_serve_e_nao_esta_defasada(self):
        self.catalogo(indicador("brent", [fonte("a"), fonte("b"), fonte("c")]))
        self.respostas({"b": alta(6.1, 1.0), "c": calma(50)}, a={"status": 404})
        codigo, linhas, objeto = self.roda()
        brent = objeto["indicadores"][0]
        self.assertEqual((brent["fonte"], brent["valor"], brent["variacao_7d_pct"], brent["variacao_pct"]),
                         ({"nome": "Fonte b", "url": SITE + "b"}, 106.1, 6.1, 1.0))
        self.assertIn("aviso: brent · Fonte a: HTTP 404", linhas)
        self.assertEqual((codigo, linhas[-1]), (0, "OK 1 indicador, 1 gatilho de preço"))
        self.assertEqual(objeto["gatilhos"], [{"criterio": "energia.2", "ref": "brent",
                                               "texto": "Petróleo Brent subiu 6,1% em 7 dias, até 20/11 (limiar: 5%)."}])

    def test_fonte_que_nao_serve_e_pulada(self):
        casos = {
            "fora da faixa": (fred((7, 100), (0, 5000)), "Fonte a: último valor fora da faixa (5000)"),
            "sem ponto": (b"observation_date,X\n", "Fonte a: nenhum ponto com valor até 20/11"),
            "só ponto futuro": (fred((-1, 100), (-2, 101)), "Fonte a: nenhum ponto com valor até 20/11"),
            "html no lugar": (b"<html>Access denied</html>", "Fonte a: nenhum ponto com valor até 20/11"),
        }
        for nome, (corpo, aviso) in casos.items():
            self.catalogo(indicador("brent", [fonte("a"), fonte("b")]))
            self.respostas({"a": corpo, "b": calma(70)})
            codigo, linhas, objeto = self.roda()
            self.assertEqual((objeto["indicadores"][0]["fonte"]["nome"], objeto["indicadores"][0]["valor"]),
                             ("Fonte b", 70.0), nome)
            self.assertIn("aviso: brent · " + aviso, linhas, nome)

    def test_json_quebrado_e_resposta_maior_que_2_mb(self):
        self.catalogo(indicador("brent", [fonte("a", "yahoo_chart"), fonte("b", "bcb_sgs"), fonte("c")]))
        self.respostas({"a": b"<html>Too Many Requests</html>", "b": b"[" + b" " * (2 * 1024 * 1024) + b"]", "c": calma()})
        codigo, linhas, objeto = self.roda()
        self.assertEqual(objeto["indicadores"][0]["fonte"]["nome"], "Fonte c")
        self.assertIn("aviso: brent · Fonte a: resposta ilegível · Fonte b: resposta maior que 2 MB", linhas)

    def test_leitor_desconhecido_e_pulado_com_aviso(self):
        self.catalogo(indicador("brent", [fonte("a", "leitor_novo"), fonte("b")]))
        self.respostas({"a": calma(), "b": calma(60)})
        codigo, linhas, objeto = self.roda()
        self.assertEqual((codigo, objeto["indicadores"][0]["valor"]), (0, 60.0))
        self.assertIn("aviso: brent · Fonte a: leitor 'leitor_novo' desconhecido: fonte pulada", linhas)

    def test_fonte_defasada_perde_para_a_seguinte_que_esta_em_dia(self):
        self.catalogo(indicador("brent", [fonte("a"), fonte("b")]))
        self.respostas({"a": alta(0, ultimo_dia=5), "b": calma(60)})
        brent = self.roda()[2]["indicadores"][0]
        self.assertEqual((brent["fonte"]["nome"], brent["defasado"], brent["data"]), ("Fonte b", False, DIA))

    def test_quatro_dias_ainda_vale_e_cinco_ja_e_defasado(self):
        self.catalogo(indicador("brent", [fonte("a")]))
        self.respostas({"a": alta(0, ultimo_dia=4)})
        codigo, linhas, objeto = self.roda()
        self.assertEqual((objeto["indicadores"][0]["defasado"], objeto["indicadores"][0]["data"], codigo),
                         (False, antes(4), 0))
        self.respostas({"a": alta(30, ultimo_dia=5)})
        codigo, linhas, objeto = self.roda()
        self.assertEqual((objeto["indicadores"][0]["defasado"], objeto["indicadores"][0]["variacao_7d_pct"]), (True, 30.0))
        self.assertEqual((objeto["gatilhos"], codigo, linhas[-1]), ([], 3, "PARCIAL sem dado: brent"))  # defasado não dispara

    def test_todas_defasadas_fica_a_de_data_mais_nova(self):
        self.catalogo(indicador("brent", [fonte("a"), fonte("b"), fonte("c")]))
        self.respostas({"a": alta(0, ultimo_dia=9, base=10), "b": alta(0, ultimo_dia=6, base=20),
                        "c": alta(0, ultimo_dia=6, base=30)})
        brent = self.roda()[2]["indicadores"][0]  # b e c empatam na data: fica a primeira do catálogo
        self.assertEqual((brent["fonte"]["nome"], brent["valor"], brent["data"], brent["defasado"]),
                         ("Fonte b", 20.0, antes(6), True))

    def test_nunca_mistura_pontos_de_duas_fontes(self):
        # A primeira fonte está em dia, mas só traz 2 pontos. A segunda tem a série inteira, com alta de 12%.
        self.catalogo(indicador("brent", [fonte("a"), fonte("b")]))
        self.respostas({"a": fred((1, 100), (0, 101)), "b": alta(12)})
        codigo, linhas, objeto = self.roda()
        brent = objeto["indicadores"][0]
        self.assertEqual((brent["fonte"]["nome"], brent["valor"], brent["variacao_pct"], brent["variacao_7d_pct"]),
                         ("Fonte a", 101.0, 1.0, None))
        self.assertEqual((objeto["gatilhos"], objeto["falhas"]), ([], [{"id": "brent", "erro": "sem base de 7 dias"}]))
        self.assertEqual((codigo, linhas[-1]), (3, "PARCIAL sem base de 7 dias: brent"))

    def test_ponto_depois_do_dia_e_descartado(self):
        self.catalogo(indicador("brent", [fonte("a")]))
        self.respostas({"a": fred((8, 100), (1, 104), (0, 105), (-1, 999), (-3, 5))})
        brent = self.roda()[2]["indicadores"][0]
        self.assertEqual((brent["valor"], brent["data"], brent["variacao_7d_pct"]), (105.0, DIA, 5.0))

    def test_fator_casas_e_mensal(self):
        self.catalogo(indicador("trigo", [fonte("a", fator=0.3674371)], casas=1, dominio="alimentos"),
                      indicador("indice", [fonte("m", "fao_csv")], frequencia="mensal", obrigatorio=False, casas=0),
                      indicador("padrao", [fonte("p")], obrigatorio=False))
        self.respostas({"a": fred((7, 574.25), (0, 594.25)), "m": "T\nB\nDate,Indice\n2026-08,120.4\n2026-09,131.5\n",
                        "p": fred((0, 12.3456))})
        objeto = self.roda()[2]
        trigo, indice, padrao = objeto["indicadores"]
        self.assertEqual((trigo["valor"], trigo["variacao_7d_pct"]), (218.3, 3.5))
        self.assertEqual((indice["valor"], indice["data"], indice["variacao_pct"], indice["variacao_7d_pct"], indice["defasado"]),
                         (132.0, "2026-09-01", 9.2, None, True))  # 80 dias: mais de 62
        self.assertEqual(padrao["valor"], 12.35)  # sem o campo casas, 2
        self.assertEqual(objeto["falhas"], [{"id": "padrao", "erro": "sem base de 7 dias"}])  # mensal não entra

    def test_mensal_com_ate_62_dias_nao_esta_defasado(self):
        self.catalogo(indicador("indice", [fonte("m", "fao_csv")], frequencia="mensal", obrigatorio=False))
        self.respostas({"m": "Date,Indice\n2026-09,131.5\n2026-10,133.9\n"})
        indice = self.roda()[2]["indicadores"][0]
        self.assertEqual((indice["data"], indice["defasado"]), ("2026-10-01", False))  # 50 dias


class TestaGatilhos(Caso):
    def monta(self, primeira, segunda=None, terceira=None, ident="brent", dominio="energia", **outras):
        nomes = [n for n, corpo in (("a", primeira), ("b", segunda), ("c", terceira)) if corpo is not None or n in outras]
        self.catalogo(indicador(ident, [fonte(n) for n in nomes], dominio=dominio))
        self.respostas(dict((n, c) for n, c in (("a", primeira), ("b", segunda), ("c", terceira)) if c is not None), **outras)
        codigo, linhas, objeto = self.roda()
        return objeto["indicadores"][0], objeto["gatilhos"], linhas[-1]

    def test_variacao_ja_arredondada_maior_ou_igual_ao_limiar(self):
        linha, gatilhos, _ = self.monta(alta(4.96))
        self.assertEqual((linha["variacao_7d_pct"], gatilhos), (5.0, [{
            "criterio": "energia.2", "ref": "brent", "texto": "Petróleo Brent subiu 5,0% em 7 dias, até 20/11 (limiar: 5%)."}]))
        linha, gatilhos, _ = self.monta(alta(4.94))
        self.assertEqual((linha["variacao_7d_pct"], gatilhos), (4.9, []))

    def test_so_alta_conta(self):
        linha, gatilhos, veredito = self.monta(alta(-12, -4))
        self.assertEqual((linha["variacao_7d_pct"], gatilhos, veredito), (-12.0, [], "OK 1 indicador, 0 gatilhos de preço"))

    def test_nivel_3_confirmado_pela_segunda_fonte(self):
        linha, gatilhos, _ = self.monta(alta(12.3), alta(6.0))
        self.assertEqual((linha["confirmado"], linha["fonte"]["nome"]), (True, "Fonte a"))
        self.assertEqual(gatilhos, [{"criterio": "energia.3", "ref": "brent",
                                     "texto": "Petróleo Brent subiu 12,3% em 7 dias, até 20/11 (limiar: 10%)."}])

    def test_nivel_3_sem_confirmacao_cai_para_o_criterio_de_nivel_2(self):
        esperado = [{"criterio": "energia.2", "ref": "brent",
                     "texto": "Petróleo Brent subiu 12,3% em 7 dias, até 20/11 (limiar: 5%)." + SUFIXO}]
        casos = {
            "a segunda fonte não cumpre nem o nível 2": dict(segunda=alta(4.0)),
            "a segunda fonte caiu": dict(segunda=alta(-3.0)),
            "a segunda fonte não tem base de 7 dias": dict(segunda=fred((1, 100), (0, 130))),
            "não há segunda fonte": dict(),
            "a segunda fonte não responde": dict(b={"status": 403}),
            "a segunda fonte não serve (fora da faixa)": dict(segunda=alta(12, base=5000)),
        }
        for nome, extras in casos.items():
            linha, gatilhos, _ = self.monta(alta(12.3), **extras)
            self.assertEqual((linha["confirmado"], gatilhos), (False, esperado), nome)
            self.assertLessEqual(len(gatilhos[0]["texto"]), 200)

    def test_a_segunda_fonte_e_a_seguinte_do_catalogo_que_serve(self):
        linha, gatilhos, _ = self.monta(alta(12.3), None, alta(5.0), b={"status": 404})
        self.assertEqual((linha["confirmado"], gatilhos[0]["criterio"]), (True, "energia.3"))
        # A que serve é a segunda; ela não confirma, e a terceira nem é consultada.
        linha, gatilhos, _ = self.monta(alta(12.3), alta(1.0), alta(15.0))
        self.assertEqual((linha["confirmado"], gatilhos[0]["criterio"]), (False, "energia.2"))

    def test_segunda_fonte_velha_nao_confirma_nem_desmente(self):
        # A segunda fonte cumpre o nível 2, mas a cotação dela é de 5 dias antes da escolhida: não confirma.
        linha, gatilhos, _ = self.monta(alta(12.3), alta(6.0, ultimo_dia=5))
        self.assertEqual((linha["confirmado"], gatilhos[0]["criterio"], gatilhos[0]["texto"].endswith(SUFIXO)),
                         (False, "energia.2", True))
        # Com 4 dias, ainda confirma.
        linha, gatilhos, _ = self.monta(alta(12.3), alta(6.0, ultimo_dia=4))
        self.assertEqual((linha["confirmado"], gatilhos[0]["criterio"]), (True, "energia.3"))
        # A velha encerra a busca: a terceira, em dia e com alta, não é consultada.
        linha, gatilhos, _ = self.monta(alta(12.3), alta(6.0, ultimo_dia=6), alta(6.0))
        self.assertEqual((linha["confirmado"], gatilhos[0]["criterio"]), (False, "energia.2"))

    def test_empate_de_nivel_entre_as_janelas_vale_a_de_7_dias(self):
        # Dólar: +3,2% no dia e +6,5% em 7 dias, os dois de nível 3. Vale a de 7 dias, no texto e na confirmação.
        linha, gatilhos = self.dolar(alta(6.5, 3.2), alta(6.1, 0.2))
        self.assertEqual((linha["confirmado"], gatilhos), (True, [{
            "criterio": "cambio.3", "ref": "usd_brl", "texto": "Dólar em reais subiu 6,5% em 7 dias, até 20/11 (limiar: 6%)."}]))
        # A segunda fonte só cumpre a janela de 1 dia: não confirma a de 7.
        linha, gatilhos = self.dolar(alta(6.5, 3.2), alta(1.0, 3.5))
        self.assertEqual((linha["confirmado"], gatilhos[0]["criterio"], gatilhos[0]["texto"]),
                         (False, "cambio.2", "Dólar em reais subiu 6,5% em 7 dias, até 20/11 (limiar: 3%)." + SUFIXO))

    def test_limiar_exato_e_meio_arredondado(self):
        linha, gatilhos, _ = self.monta(fred((7, 100), (0, 105)))  # exatamente 5,0%
        self.assertEqual((linha["variacao_7d_pct"], [g["criterio"] for g in gatilhos]), (5.0, ["energia.2"]))
        linha, gatilhos, _ = self.monta(fred((7, 400), (0, 419.8)))  # 4,95% → 5,0 (metade para longe do zero)
        self.assertEqual((linha["variacao_7d_pct"], [g["criterio"] for g in gatilhos]), (5.0, ["energia.2"]))
        linha, gatilhos, _ = self.monta(fred((7, 400), (0, 419.79)))  # 4,9475% → 4,9
        self.assertEqual((linha["variacao_7d_pct"], gatilhos), (4.9, []))

    def test_data_repetida_vale_a_ultima_da_resposta(self):
        corpo = b"observation_date,X\n%s,100\n%s,103\n%s,106\n" % (antes(7).encode(), antes(0).encode(), antes(0).encode())
        linha, gatilhos, _ = self.monta(corpo)
        self.assertEqual((linha["valor"], linha["variacao_7d_pct"], [g["criterio"] for g in gatilhos]), (106.0, 6.0, ["energia.2"]))

    def test_fonte_anterior_a_escolhida_nao_confirma(self):
        # A primeira está defasada (e mostra alta); a escolhida é a segunda; não há fonte seguinte.
        linha, gatilhos, _ = self.monta(alta(15, ultimo_dia=6), alta(12.3))
        self.assertEqual((linha["fonte"]["nome"], linha["confirmado"], gatilhos[0]["criterio"]),
                         ("Fonte b", False, "energia.2"))

    def test_nivel_4_confirmado_por_fonte_que_cumpre_o_nivel_2(self):
        linha, gatilhos, _ = self.monta(alta(21.0), alta(5.5))
        self.assertEqual((linha["confirmado"], gatilhos), (True, [{
            "criterio": "energia.4", "ref": "brent", "texto": "Petróleo Brent subiu 21,0% em 7 dias, até 20/11 (limiar: 20%)."}]))
        linha, gatilhos, _ = self.monta(alta(21.0))
        self.assertEqual((linha["confirmado"], gatilhos[0]["criterio"], gatilhos[0]["texto"].endswith(SUFIXO)),
                         (False, "energia.2", True))

    def test_nivel_2_nao_pede_segunda_fonte(self):
        linha, gatilhos, _ = self.monta(alta(6.1), alta(30))
        self.assertEqual((linha["confirmado"], gatilhos[0]["criterio"], SUFIXO in gatilhos[0]["texto"]),
                         (False, "energia.2", False))

    def dolar(self, primeira, segunda=None, dia=DIA, agora=AGORA):
        self.catalogo(indicador("usd_brl", [fonte("a")] + ([fonte("b")] if segunda else []), dominio="cambio",
                                faixa=(1, 1000), casas=4))
        self.respostas(dict((n, c) for n, c in (("a", primeira), ("b", segunda)) if c))
        codigo, linhas, objeto = self.roda(dia=dia, agora=agora)
        return objeto["indicadores"][0], objeto["gatilhos"]

    def test_janela_de_1_dia_no_dia_da_cotacao(self):
        linha, gatilhos = self.dolar(alta(2.0, 1.6))
        self.assertEqual((linha["variacao_pct"], linha["variacao_7d_pct"]), (1.6, 2.0))
        self.assertEqual(gatilhos, [{"criterio": "cambio.2", "ref": "usd_brl",
                                     "texto": "Dólar em reais subiu 1,6% no dia 20/11 (limiar: 1,5%)."}])

    def test_janela_de_1_dia_nao_vale_no_dia_seguinte(self):
        # Sábado, 21/11: a cotação é a de sexta. Não está defasada, mas a alta de sexta não dispara de novo.
        linha, gatilhos = self.dolar(alta(2.0, 1.6), dia="2026-11-21", agora="2026-11-21T21:05:00Z")
        self.assertEqual((linha["data"], linha["defasado"], linha["variacao_pct"], gatilhos), (DIA, False, 1.6, []))
        # O critério de 7 dias continua valendo no sábado.
        linha, gatilhos = self.dolar(alta(3.5, 1.6), dia="2026-11-21", agora="2026-11-21T21:05:00Z")
        self.assertEqual(gatilhos, [{"criterio": "cambio.2", "ref": "usd_brl",
                                     "texto": "Dólar em reais subiu 3,5% em 7 dias, até 20/11 (limiar: 3%)."}])

    def test_fica_o_criterio_de_maior_nivel_e_um_gatilho_so_por_indicador(self):
        linha, gatilhos = self.dolar(alta(3.5, 1.6))  # os dois de nível 2: no empate de nível, vale o de 7 dias
        self.assertEqual([g["texto"] for g in gatilhos], ["Dólar em reais subiu 3,5% em 7 dias, até 20/11 (limiar: 3%)."])
        linha, gatilhos = self.dolar(alta(6.5, 1.6), alta(3.1))  # 7 dias no nível 3, 1 dia no nível 2
        self.assertEqual((linha["confirmado"], gatilhos), (True, [{
            "criterio": "cambio.3", "ref": "usd_brl", "texto": "Dólar em reais subiu 6,5% em 7 dias, até 20/11 (limiar: 6%)."}]))

    def test_janela_de_1_dia_no_nivel_3_pede_segunda_fonte_com_cotacao_do_dia(self):
        linha, gatilhos = self.dolar(alta(3.2, 3.2), alta(2.0, 1.6))
        self.assertEqual((linha["confirmado"], gatilhos), (True, [{
            "criterio": "cambio.3", "ref": "usd_brl", "texto": "Dólar em reais subiu 3,2% no dia 20/11 (limiar: 3%)."}]))
        # A segunda fonte parou na véspera: a alta de 5% dela é de outro dia, e não confirma.
        linha, gatilhos = self.dolar(alta(3.2, 3.2), alta(5.0, 5.0, ultimo_dia=1))
        self.assertEqual((linha["confirmado"], gatilhos), (False, [{
            "criterio": "cambio.2", "ref": "usd_brl",
            "texto": "Dólar em reais subiu 3,2% no dia 20/11 (limiar: 1,5%)." + SUFIXO}]))

    def test_grao_com_uma_fonte_so_nunca_passa_do_nivel_2(self):
        linha, gatilhos, _ = self.monta(alta(25.0), ident="trigo", dominio="alimentos")
        self.assertEqual((linha["confirmado"], gatilhos), (False, [{
            "criterio": "alimentos.2", "ref": "trigo",
            "texto": "Trigo subiu 25,0% em 7 dias, até 20/11 (limiar: 5%)." + SUFIXO}]))

    def test_indicador_sem_criterio_na_regua_nao_dispara(self):
        linha, gatilhos, veredito = self.monta(alta(40.0), ident="ouro", dominio="cambio")
        self.assertEqual((linha["variacao_7d_pct"], gatilhos), (40.0, []))

    def test_gatilhos_saem_na_ordem_do_catalogo(self):
        self.catalogo(indicador("usd_brl", [fonte("d")], dominio="cambio"), indicador("milho", [fonte("m")], dominio="alimentos"),
                      indicador("brent", [fonte("b")]))
        self.respostas({"d": alta(3.0), "m": alta(7.0), "b": alta(5.0)})
        codigo, linhas, objeto = self.roda()
        self.assertEqual([(g["criterio"], g["ref"]) for g in objeto["gatilhos"]],
                         [("cambio.2", "usd_brl"), ("alimentos.2", "milho"), ("energia.2", "brent")])
        self.assertEqual(linhas[-1], "OK 3 indicadores, 3 gatilhos de preço")


class TestaVereditos(Caso):
    def tres(self, brent, milho, gas):
        self.catalogo(indicador("brent", [fonte("b")]), indicador("milho", [fonte("m")], dominio="alimentos"),
                      indicador("gas_natural", [fonte("g")], obrigatorio=False))
        self.respostas(dict((n, c) for n, c in (("b", brent), ("m", milho), ("g", gas)) if c))
        return self.roda()

    def test_ok(self):
        codigo, linhas, objeto = self.tres(calma(), calma(), calma())
        self.assertEqual((codigo, linhas[-1], objeto["falhas"]), (0, "OK 3 indicadores, 0 gatilhos de preço", []))

    def test_ok_mesmo_sem_o_que_nao_e_obrigatorio(self):
        codigo, linhas, objeto = self.tres(calma(), calma(), None)
        self.assertEqual((codigo, linhas[-1]), (0, "OK 2 indicadores, 0 gatilhos de preço"))
        self.assertEqual(objeto["falhas"], [{"id": "gas_natural", "erro": "todas as fontes falharam"}])
        gas = objeto["indicadores"][2]
        self.assertEqual((gas["valor"], gas["variacao_pct"], gas["variacao_7d_pct"], gas["data"], gas["defasado"],
                          gas["confirmado"], gas["fonte"]), (None, None, None, None, True, False,
                                                             {"nome": "Fonte g", "url": SITE + "g"}))

    def test_parcial_sem_dado(self):
        codigo, linhas, objeto = self.tres(calma(), None, calma())
        self.assertEqual((codigo, linhas[-1]), (3, "PARCIAL sem dado: milho"))
        self.assertEqual(objeto["falhas"], [{"id": "milho", "erro": "todas as fontes falharam"}])

    def test_parcial_sem_base_de_7_dias(self):
        curta = fred((2, 100), (1, 100), (0, 100))
        codigo, linhas, objeto = self.tres(curta, curta, curta)
        self.assertEqual((codigo, linhas[-1]), (3, "PARCIAL sem base de 7 dias: brent, milho"))
        self.assertEqual(objeto["falhas"], [{"id": i, "erro": "sem base de 7 dias"} for i in ("brent", "milho", "gas_natural")])

    def test_parcial_com_as_duas_situacoes(self):
        codigo, linhas, objeto = self.tres(fred((1, 100), (0, 100)), None, calma())
        self.assertEqual((codigo, linhas[-1]), (3, "PARCIAL sem dado: milho; sem base de 7 dias: brent"))
        self.assertEqual(objeto["falhas"], [{"id": "brent", "erro": "sem base de 7 dias"},
                                            {"id": "milho", "erro": "todas as fontes falharam"}])

    def test_falha_sem_rede_grava_tudo_em_null(self):
        codigo, linhas, objeto = self.tres(None, None, None)
        self.assertEqual((codigo, linhas[-1]), (4, "FALHA sem rede: 0 indicadores"))
        self.assertEqual([(i["id"], i["valor"], i["defasado"]) for i in objeto["indicadores"]],
                         [("brent", None, True), ("milho", None, True), ("gas_natural", None, True)])
        self.assertEqual((objeto["gatilhos"], len(objeto["falhas"])), ([], 3))

    def test_teto_de_tempo_corta_o_pedido_e_conta_como_erro(self):
        self.grava(os.path.join(self.off, "b.txt"), calma())
        self.catalogo(indicador("brent", [fonte("b")]))
        self.respostas({}, b={"arquivo": "b.txt", "demora": 3})
        codigo, linhas, objeto = self.roda("--tempo", "1")
        self.assertEqual((codigo, linhas[-1], objeto["indicadores"][0]["valor"]), (4, "FALHA sem rede: 0 indicadores", None))
        self.assertIn("aviso: brent · Fonte b: não coube no tempo", linhas)

    def test_catalogo_ou_regua_ilegivel_e_falha_sem_gravar_nada(self):
        bons = {}
        for nome in ("indicadores.json", "regua.json"):
            with open(os.path.join(self.raiz, "dados", nome), "rb") as arquivo:
                bons[nome] = arquivo.read()
        estragos = [("indicadores.json", b"{quebrado"), ("indicadores.json", b"[]"), ("indicadores.json", b'{"indicadores": []}'),
                    ("indicadores.json", json.dumps({"indicadores": [indicador("brent", [])]}).encode()),
                    ("indicadores.json", json.dumps({"indicadores": [indicador("brent", [fonte("a", fator=0)])]}).encode()),
                    ("indicadores.json", json.dumps({"indicadores": [indicador("Brent!", [fonte("a")])]}).encode()),
                    ("regua.json", b"nada"), ("regua.json", b'{"niveis_alerta": "x"}'),
                    ("regua.json", b'{"niveis_alerta": [{"nivel": 2, "criterios": {"energia": {"codigo": "energia.2"}}}]}')]
        for nome, estrago in estragos:
            for arquivo, conteudo in bons.items():
                self.grava(os.path.join(self.raiz, "dados", arquivo), conteudo)
            self.grava(os.path.join(self.raiz, "dados", nome), estrago)
            os.makedirs(self.trabalho, exist_ok=True)
            self.grava(os.path.join(self.trabalho, "indicadores.json"), b'{"de": "ontem"}\n')
            codigo, linhas, objeto = self.roda()
            self.assertEqual(codigo, 1, estrago)
            self.assertTrue(linhas[-1].startswith("FALHA ") and not linhas[-1].startswith("FALHA sem rede"), linhas[-1])
            self.assertIn(nome, linhas[-1])
            self.assertEqual(objeto, {"de": "ontem"}, estrago)  # CONTRATO, seção 0: o arquivo de antes fica como estava

    def test_arquivo_apagado_falta(self):
        os.unlink(os.path.join(self.raiz, "dados", "indicadores.json"))
        codigo, linhas, objeto = self.roda()
        self.assertEqual((codigo, objeto), (1, None))
        self.assertTrue(linhas[-1].startswith("FALHA "))

    def test_saida_em_json(self):
        self.catalogo(indicador("brent", [fonte("b")]))
        self.respostas({"b": alta(6.1)})
        comando = [sys.executable, "-B", os.path.join(FERRAMENTAS, "indicadores.py"), "--raiz", self.raiz, "--trabalho",
                   self.trabalho, "--offline", self.off, "--dia", DIA, "--json"]
        feito = subprocess.run(comando, env=dict(os.environ, INFO_AGORA=AGORA), capture_output=True, timeout=120)
        objeto = json.loads(feito.stdout.decode("utf-8"))
        self.assertEqual((feito.returncode, objeto["ok"], objeto["codigo"], objeto["veredito"]),
                         (0, True, 0, "OK 1 indicador, 1 gatilho de preço"))
        self.assertEqual((objeto["indicadores"], objeto["gatilhos"], objeto["sem_dado"], objeto["sem_base_7d"]), (1, 1, [], []))
        self.assertEqual(objeto["arquivo"], os.path.join(self.trabalho, "indicadores.json"))


class TestaUsoEAmbiente(Caso):
    def test_erro_de_uso_nao_grava_nada(self):
        casos = (["--tempo", "abc"], ["--tempo", "-1"], ["--tempo", "0"], ["--tempo", "1.5"], ["--tempo", "3601"], ["--tempo"], ["--dia", "20/11/2026"], ["--nao-existe"],
                 ["--offline", os.path.join(self.pasta, "nao-existe")], ["--offline", ""], ["sobra"])
        for opcoes in casos:
            codigo, linhas, objeto = self.roda(*opcoes)
            self.assertEqual((codigo, len(linhas), objeto), (2, 1, None), opcoes)
            self.assertTrue(linhas[0].startswith("FALHA uso: "), linhas)
            self.assertFalse(os.path.exists(os.path.join(self.trabalho, "indicadores.json")))

    def test_offline_sem_respostas_json_ou_com_ele_quebrado(self):
        os.unlink(os.path.join(self.off, "respostas.json"))
        codigo, linhas, objeto = self.roda()
        self.assertEqual((codigo, objeto, linhas[0][:21]), (2, None, "FALHA uso: --offline:"))
        self.assertFalse(os.path.exists(self.trabalho))  # nem a pasta de trabalho chega a ser criada
        self.grava(os.path.join(self.off, "respostas.json"), b"{quebrado")
        self.assertEqual(self.roda()[0], 2)

    def test_respostas_json_vazio_e_maquina_sem_rede(self):
        for vazio in (b"{}", b"", b"\n"):
            self.grava(os.path.join(self.off, "respostas.json"), vazio)
            codigo, linhas, objeto = self.roda()
            self.assertEqual((codigo, linhas[-1], len(objeto["indicadores"])), (4, "FALHA sem rede: 0 indicadores", 12))

    def test_relogio_ilegivel_e_erro_de_uso(self):
        codigo, linhas, objeto = self.roda(agora="ontem")
        self.assertEqual((codigo, linhas, objeto), (2, ["FALHA uso: INFO_AGORA ilegível"], None))

    def test_dia_vem_do_contexto(self):
        os.makedirs(self.trabalho)
        self.grava(os.path.join(self.trabalho, "contexto.json"), json.dumps({"dia": "2026-11-18", "janela_horas": 36}))
        self.catalogo(indicador("brent", [fonte("b")]))
        self.respostas({"b": calma()})
        codigo, linhas, objeto = self.roda(dia=None)
        self.assertEqual((objeto["dia"], objeto["indicadores"][0]["data"], objeto["gerada_em"]), ("2026-11-18", "2026-11-18", AGORA))

    def test_sem_contexto_o_dia_e_hoje_em_brasilia(self):
        self.assertEqual(self.roda(dia=None, agora="2026-11-21T02:30:00Z")[2]["dia"], "2026-11-20")

    def test_contexto_quebrado_e_falha_e_nada_e_gravado(self):
        os.makedirs(self.trabalho)
        self.grava(os.path.join(self.trabalho, "contexto.json"), b"{quebrado")
        codigo, linhas, objeto = self.roda(dia=None)
        self.assertEqual(codigo, 1)
        self.assertTrue(linhas[-1].startswith("FALHA ") and "contexto.json" in linhas[-1], linhas)
        self.assertEqual(objeto, None)  # CONTRATO, seção 0: contexto.json que não dá para ler não grava nada

    def test_nao_deixa_pycache_nem_arquivo_a_mais(self):
        copia = os.path.join(self.raiz, "ferramentas")
        os.makedirs(copia)
        for nome in ("comum.py", "rede.py", "indicadores.py"):
            shutil.copy(os.path.join(FERRAMENTAS, nome), copia)
        comando = [sys.executable, os.path.join(copia, "indicadores.py"), "--trabalho", self.trabalho, "--offline", self.off,
                   "--dia", DIA]  # sem -B, sem --raiz e sem a variável: como a rotina chama
        ambiente = {k: v for k, v in os.environ.items() if k != "PYTHONDONTWRITEBYTECODE"}
        feito = subprocess.run(comando, env=dict(ambiente, INFO_AGORA=AGORA), cwd=self.raiz, capture_output=True, timeout=120)
        self.assertEqual((feito.returncode, feito.stderr), (4, b""))
        self.assertEqual(sorted(os.listdir(copia)), ["comum.py", "indicadores.py", "rede.py"])
        self.assertEqual(sorted(os.listdir(self.trabalho)), ["indicadores.json"])
        self.assertEqual(sorted(os.listdir(os.path.join(self.raiz, "dados"))), sorted(os.listdir(DADOS)))

    def test_nao_altera_o_catalogo_nem_a_regua(self):
        def retrato():
            fotos = {}
            for nome in sorted(os.listdir(os.path.join(self.raiz, "dados"))):
                with open(os.path.join(self.raiz, "dados", nome), "rb") as arquivo:
                    fotos[nome] = arquivo.read()
            return fotos

        antes_ = retrato()
        self.roda(off=AMOSTRAS, dia="2026-11-23", agora="2026-11-23T21:07:00Z")
        self.assertEqual(retrato(), antes_)


class TestaFonteDoScript(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(FERRAMENTAS, "indicadores.py"), encoding="utf-8") as arquivo:
            self.fonte = arquivo.read()

    def test_o_script_nao_traz_endereco_nenhum(self):
        for trecho in ("http://", "https://", "www.", "yahoo.com", "stlouisfed", "bcb.gov", "eia.gov", "fao.org"):
            self.assertNotIn(trecho, self.fonte)

    def test_numeros_do_contrato(self):
        self.assertEqual((indicadores.PARALELOS, indicadores.POR_PEDIDO, indicadores.TEMPO_PADRAO), (4, 10.0, 45.0))
        self.assertEqual((indicadores.VELHO_DIARIO, indicadores.VELHO_MENSAL), (4, 62))

    def test_os_6_leitores_do_contrato(self):
        self.assertEqual(sorted(indicadores.LEITORES), ["bcb_sgs", "cnbc_chart", "eia_v2", "fao_csv", "fred_csv",
                                                       "yahoo_chart"])
        self.assertIn("Firefox", indicadores.LEITORES["yahoo_chart"][2])  # o Yahoo pede User-Agent de navegador
        self.assertEqual(indicadores.LEITORES["fred_csv"][2], "Mozilla/5.0 (compatible; INFOCENARIUM-monitor/1)")

    def test_sintaxe_que_o_python_3_7_le(self):
        ast.parse(self.fonte, feature_version=(3, 7))  # senão a guarda de versão nem chega a rodar

    def test_nada_que_execute_o_que_baixou(self):
        for proibido in ("eval(", "exec(", "pickle", "subprocess", "os.system", "__import__", "marshal", "shelve"):
            self.assertNotIn(proibido, self.fonte)


if __name__ == "__main__":
    unittest.main()
