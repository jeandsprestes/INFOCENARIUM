#!/usr/bin/env python3
"""Uma conta só: os gatilhos de preço que o indicadores.py grava são os que o valida.py calcula.

O indicadores.py faz a conta dos gatilhos (CONTRATO, seção 2, passos 7 e 8). O valida.py confere a edição
recalculando (ESQUEMA, seção 10, regras R13c e R13f), pelas funções que a docstring dele lista:
calcula_gatilhos_de_preco(dados, indicadores, data) e calcula_sem_preco(dados, dominio, indicadores).
Se as duas contas divergirem, a edição de um dia de alta é recusada, ou passa com o nível errado.

Cada cenário roda o indicadores.py pela linha de comando, com --offline, e passa a lista `indicadores` que ele
gravou pelas funções do valida.py, com os mesmos dados (a mesma raiz temporária). Confere:
- os gatilhos: o mesmo {domínio: {indicador: nível}} dos dois lados;
- `confirmado: true` só onde o valida.py vê alta de nível 3 ou 4 antes da confirmação (R13c);
- os obrigatórios que o veredito dá como "sem dado" ou "sem base de 7 dias" são os que a R13f põe em sem_preco.

Rodar da raiz do repositório: python3 -B testes/testa_indicadores_valida.py
"""
import json
import os
import shutil
import subprocess
import sys
import unittest

sys.dont_write_bytecode = True
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from testa_indicadores import (AGORA, AMOSTRAS, DIA, FERRAMENTAS, SITE, Caso, alta, antes, calma, fonte, fred,  # noqa: E402
                               indicador)

import valida  # noqa: E402  (testa_indicadores já pôs ferramentas/ no caminho)

CONTRATOS = os.path.join(AQUI, "fixtures", "indicadores", "contratos")


def yahoo(*pontos, hora="05:00:00"):
    """Corpo de yahoo_chart (fuso de Nova York, como os futuros do catálogo), de pares (dias antes de DIA, valor)."""
    from datetime import datetime, timezone
    carimbos = [int(datetime.strptime(antes(d) + "T" + hora, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp())
                for d, _ in pontos]
    return json.dumps({"chart": {"result": [{"meta": {"exchangeTimezoneName": "America/New_York", "gmtoffset": -18000},
                                             "timestamp": carimbos, "indicators": {"quote": [{"close": [v for _, v in pontos]}]}}],
                                 "error": None}}).encode("utf-8")


class UmaContaSo(Caso):

    def confere(self, dia=DIA, agora=AGORA, off=None, opcoes=()):
        """Roda o indicadores.py e confere a saída contra as funções do valida.py. Devolve o indicadores.json."""
        comando = [sys.executable, os.path.join(FERRAMENTAS, "indicadores.py"), "--raiz", self.raiz, "--trabalho",
                   self.trabalho, "--offline", off or self.off, "--dia", dia, "--json"] + list(opcoes)
        ambiente = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", INFO_AGORA=agora)
        feito = subprocess.run(comando, env=ambiente, capture_output=True, timeout=120)
        self.assertEqual(feito.stderr, b"")
        saida = json.loads(feito.stdout.decode("utf-8"))
        objeto = self.gravado()
        dados, problemas = valida.carrega_dados(self.raiz)
        self.assertEqual([p.linha() for p in problemas + dados.problemas], [])
        lista = objeto["indicadores"]

        def sem_vazios(por_dominio):
            return dict((d, dict(v)) for d, v in por_dominio.items() if v)

        do_validador = sem_vazios(valida.calcula_gatilhos_de_preco(dados, lista, dia))
        da_ferramenta = {}
        for gatilho in objeto["gatilhos"]:
            dominio, nivel = gatilho["criterio"].split(".")
            self.assertNotIn(gatilho["ref"], da_ferramenta.get(dominio, {}), "dois gatilhos do mesmo indicador")
            da_ferramenta.setdefault(dominio, {})[gatilho["ref"]] = int(nivel)
        self.assertEqual(da_ferramenta, do_validador, "a conta do indicadores.py e a do valida.py divergem")

        antes_de_confirmar = valida.calcula_gatilhos_de_preco(dados, [dict(i, confirmado=True) for i in lista], dia)
        for item in lista:
            if item["confirmado"]:
                niveis = [por_id.get(item["id"]) for por_id in antes_de_confirmar.values()]
                self.assertTrue(any(n in (3, 4) for n in niveis), "confirmado sem alta forte: %s" % item["id"])

        cegos = set()
        for dominio in dados.dominios:
            cegos.update(valida.calcula_sem_preco(dados, dominio, lista))
        # Indicador que a régua cita e o catálogo não tem: o valida.py o põe em sem_preco, e o indicadores.py só
        # avisa. Não é divergência de conta: a regra C2 (valida.py --dados, erro) não deixa esse catálogo passar.
        no_catalogo = set(i["id"] for i in lista)
        self.assertEqual(set(saida["sem_dado"]) | set(saida["sem_base_7d"]), cegos & no_catalogo)
        return objeto

    def niveis(self, objeto):
        return [(g["ref"], g["criterio"]) for g in objeto["gatilhos"]]

    # --- os cenários ---

    def dois(self, brent, dolar, segunda=None, dolar_2=None):
        fontes = [fonte("b")] + ([fonte("b2")] if segunda is not None else [])
        fontes_dolar = [fonte("d")] + ([fonte("d2")] if dolar_2 is not None else [])
        self.catalogo(indicador("brent", fontes), indicador("usd_brl", fontes_dolar, dominio="cambio", casas=4))
        corpos = dict((nome, corpo) for nome, corpo in (("b", brent), ("d", dolar)) if corpo is not None)
        if segunda is not None:
            corpos["b2"] = segunda
        if dolar_2 is not None:
            corpos["d2"] = dolar_2
        self.respostas(corpos)

    def test_alta_exatamente_no_limiar(self):
        self.dois(fred((7, 100), (0, 105)), fred((7, 5.0), (1, 5.0), (0, 5.075)))  # +5,0% em 7 dias; +1,5% no dia
        objeto = self.confere()
        self.assertEqual(self.niveis(objeto), [("brent", "energia.2"), ("usd_brl", "cambio.2")])

    def test_meio_arredondado(self):
        self.dois(fred((7, 400), (0, 419.8)), fred((7, 4.0), (1, 4.0), (0, 4.0598)))  # 4,95 → 5,0; 1,495 → 1,5
        self.assertEqual(self.niveis(self.confere()), [("brent", "energia.2"), ("usd_brl", "cambio.2")])
        self.dois(fred((7, 400), (0, 419.79)), fred((7, 4.0), (1, 4.0), (0, 4.0597)))  # 4,9475 → 4,9; 1,4925 → 1,5
        objeto = self.confere()
        self.assertEqual(self.niveis(objeto), [("usd_brl", "cambio.2")])
        self.dois(fred((7, 4.0597), (0, 4.0)), fred((7, 4.0), (1, 4.0), (0, 4.0)))  # queda de −1,47%: só alta conta
        self.assertEqual(self.niveis(self.confere()), [])

    def test_cotacao_de_sexta_lida_no_domingo(self):
        self.dois(alta(6.0), alta(2.0, 2.0))  # sexta: brent +6,0% em 7 dias; dólar +2,0% no dia e em 7 dias
        self.assertEqual(self.niveis(self.confere()), [("brent", "energia.2"), ("usd_brl", "cambio.2")])
        domingo = self.confere(dia="2026-11-22", agora="2026-11-22T21:05:00Z")
        self.assertEqual(self.niveis(domingo), [("brent", "energia.2")])  # a alta de 1 dia não volta no domingo
        self.assertEqual([i["data"] for i in domingo["indicadores"]], [DIA, DIA])
        self.dois(alta(6.0), alta(3.5, 2.0))  # com +3,5% em 7 dias, o dólar segue no domingo, pela janela de 7 dias
        self.assertEqual(self.niveis(self.confere(dia="2026-11-22", agora="2026-11-22T21:05:00Z")),
                         [("brent", "energia.2"), ("usd_brl", "cambio.2")])
        quinta_feira = self.confere(dia="2026-11-25", agora="2026-11-25T21:05:00Z")  # 5 dias: defasado, sem gatilho
        self.assertEqual((self.niveis(quinta_feira), [i["defasado"] for i in quinta_feira["indicadores"]]), ([], [True, True]))

    def test_alta_forte_com_e_sem_segunda_fonte(self):
        self.dois(alta(12.0), calma(5.0), segunda=alta(6.0))
        objeto = self.confere()
        self.assertEqual((self.niveis(objeto), objeto["indicadores"][0]["confirmado"]), ([("brent", "energia.3")], True))
        self.dois(alta(12.0), calma(5.0))
        objeto = self.confere()
        self.assertEqual((self.niveis(objeto), objeto["indicadores"][0]["confirmado"]), ([("brent", "energia.2")], False))
        self.dois(alta(21.0), calma(5.0), segunda=alta(2.0))  # nível 4 que a segunda fonte não confirma
        self.assertEqual(self.niveis(self.confere()), [("brent", "energia.2")])
        self.dois(alta(21.0), calma(5.0), segunda=alta(5.0))
        self.assertEqual(self.niveis(self.confere()), [("brent", "energia.4")])

    def test_segunda_fonte_velha(self):
        self.dois(alta(12.0), calma(5.0), segunda=alta(6.0, ultimo_dia=5))
        objeto = self.confere()
        self.assertEqual((self.niveis(objeto), objeto["indicadores"][0]["confirmado"]), ([("brent", "energia.2")], False))

    def test_empate_de_janelas_no_dolar(self):
        self.dois(calma(), alta(6.5, 3.2), dolar_2=alta(6.1, 0.2))  # nível 3 nas duas janelas; confirma a de 7 dias
        objeto = self.confere()
        self.assertEqual((self.niveis(objeto), objeto["indicadores"][1]["confirmado"]), ([("usd_brl", "cambio.3")], True))
        self.dois(calma(), alta(6.5, 3.2), dolar_2=alta(1.0, 3.5))  # a segunda só cumpre a de 1 dia: não confirma
        self.assertEqual(self.niveis(self.confere()), [("usd_brl", "cambio.2")])

    def test_sem_dado_e_sem_base(self):
        self.dois(fred((1, 100), (0, 104)), None)
        objeto = self.confere()
        self.assertEqual(([f["id"] for f in objeto["falhas"]], self.niveis(objeto)), (["brent", "usd_brl"], []))

    def test_troca_de_contrato(self):
        # A série do catálogo troca de contrato no último dia, com degrau de +6%: na série, alta de 7,1% em 7 dias
        # (gatilho de nível 2). No contrato, +1,0% em 7 dias: nenhum gatilho. O valida.py recalcula com a
        # variação gravada, que é a do contrato, e as duas contas dão "nenhum gatilho".
        modelo = SITE + "brent-{c}"
        catalogo = indicador("brent", [dict(fonte("b", "yahoo_chart"), contratos={"modelo": modelo, "meses": "FGHJKMNQUVXZ"}),
                                       fonte("b2")])
        self.catalogo(catalogo, indicador("usd_brl", [fonte("d")], dominio="cambio", casas=4))
        serie = yahoo((8, 100.0), (7, 100.0), (1, 100.5), (0, 107.1))
        contrato = yahoo((8, 106.0), (7, 106.0), (1, 106.5), (0, 107.06))
        self.respostas({"b": serie, "brent-X26": contrato, "b2": calma(), "d": calma(5.0)})
        objeto = self.confere()
        brent = objeto["indicadores"][0]
        self.assertEqual((brent["valor"], brent["variacao_pct"], brent["variacao_7d_pct"]), (107.1, 0.5, 1.0))
        self.assertEqual((self.niveis(objeto), objeto["avisos"]),
                         ([], ["brent: variações medidas no contrato X26, porque a série trocou de contrato em 20/11."]))
        # E o contrário: na série, +1,0% em 7 dias; o degrau para baixo escondia uma alta de 7,3% no contrato
        # (100,899 / 94,0), que vira gatilho de nível 2 dos dois lados.
        serie = yahoo((8, 100.0), (7, 100.0), (1, 100.5), (0, 101.0))
        contrato = yahoo((8, 94.0), (7, 94.0), (1, 94.5), (0, 100.899))
        self.respostas({"b": serie, "brent-X26": contrato, "b2": calma(), "d": calma(5.0)})
        objeto = self.confere()
        self.assertEqual((objeto["indicadores"][0]["variacao_7d_pct"], self.niveis(objeto)), (7.3, [("brent", "energia.2")]))

    def test_o_dia_real_de_23_de_novembro_com_os_contratos(self):
        shutil.rmtree(self.off)
        os.makedirs(self.off)
        with open(os.path.join(AMOSTRAS, "respostas.json"), encoding="utf-8") as arquivo:
            mapa = json.load(arquivo)
        with open(os.path.join(CONTRATOS, "respostas.json"), encoding="utf-8") as arquivo:
            mapa.update(json.load(arquivo))
        for pasta in (AMOSTRAS, CONTRATOS):
            for nome in os.listdir(pasta):
                if nome != "respostas.json" and nome.endswith((".json", ".csv")):
                    shutil.copy(os.path.join(pasta, nome), self.off)
        self.grava(os.path.join(self.off, "respostas.json"), json.dumps(mapa))
        objeto = self.confere(dia="2026-11-23", agora="2026-11-23T21:07:00Z")
        self.assertEqual(self.niveis(objeto), [("usd_brl", "cambio.2")])
        sexta = self.confere(dia="2026-11-20", agora="2026-11-20T21:07:00Z")
        self.assertEqual(len(sexta["indicadores"]), 12)


if __name__ == "__main__":
    unittest.main()
