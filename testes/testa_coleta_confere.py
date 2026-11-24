#!/usr/bin/env python3
"""Testes de ferramentas/coleta.py --confere: a data das páginas abertas (CONTRATO, seção 1.1).

Rodar da raiz do repositório: python3 -B testes/testa_coleta_confere.py
Sempre --offline, com pasta de trabalho temporária e relógio fixo (INFO_AGORA).
"""
import json
import os
import subprocess
import sys
import unittest
from unittest import mock

sys.dont_write_bytecode = True
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FERRAMENTAS = os.path.join(RAIZ, "ferramentas")
sys.path.insert(0, FERRAMENTAS)
sys.path.insert(0, os.path.join(RAIZ, "testes"))

import coleta  # noqa: E402
import rede  # noqa: E402
from testa_coleta import AGORA, Caso, item, rss  # noqa: E402

SITE = "https://paginas.exemplo.invalid/"
META = '<meta property="article:published_time" content="%s">'
LD = '<script type="application/ld+json">%s</script>'


def pagina(cabeca="", corpo="<p>Texto da matéria.</p>"):
    return ("<!DOCTYPE html>\n<html lang=\"pt-BR\"><head><meta charset=\"utf-8\"><title>Matéria</title>%s</head>"
            "<body>%s</body></html>" % (cabeca, corpo)).encode("utf-8")


class CasoConfere(Caso):
    def paginas(self, corpos, **entradas):
        """corpos: {nome curto: bytes da página}, servidas como text/html. entradas: {nome: entrada pronta}."""
        os.makedirs(self.trabalho, exist_ok=True)
        for nome, corpo in corpos.items():
            self.grava(os.path.join(self.off, nome + ".html"), corpo)
            self.respostas[SITE + nome] = {"arquivo": nome + ".html", "tipo": "text/html; charset=utf-8"}
        for nome, entrada in entradas.items():
            self.respostas[SITE + nome] = entrada
        self.grava_respostas()

    def urls(self, *nomes, cru=None):
        os.makedirs(self.trabalho, exist_ok=True)
        self.grava(os.path.join(self.trabalho, "urls.txt"), cru if cru is not None else "".join(SITE + n + "\n" for n in nomes))

    def confere(self, *opcoes, agora=AGORA):
        comando = [sys.executable, os.path.join(FERRAMENTAS, "coleta.py"), "--confere", "--trabalho", self.trabalho,
                   "--offline", self.off] + list(opcoes)
        base = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", INFO_AGORA=agora)
        feito = subprocess.run(comando, env=base, cwd=self.pasta, stdin=subprocess.DEVNULL, capture_output=True, timeout=120)
        self.assertEqual(feito.stderr.decode("utf-8", "replace"), "")
        return feito.returncode, feito.stdout.decode("utf-8").splitlines(), self.le("conferencia.json")

    def estados(self, conferencia):
        return [(p["url"].replace(SITE, ""), p["estado"], p["publicado_em"]) for p in conferencia["paginas"]]


class TestaDatas(CasoConfere):
    def test_os_dois_campos_de_data_e_a_ordem_entre_eles(self):
        artigo = json.dumps({"@context": "https://schema.org", "@type": "NewsArticle", "headline": "x", "datePublished": "2026-11-18T09:00:00Z"})
        self.paginas({
            "meta": pagina(META % "2026-11-20T10:00:00-03:00"),
            "meta-vira-o-dia": pagina(META % "2026-11-20T23:30:00-03:00"),
            "json-ld": pagina(LD % artigo),
            "os-dois": pagina(LD % artigo + META % "2026-11-19T12:00:00Z"),
            "meta-ilegivel": pagina(META % "ontem à noite" + LD % artigo),
            "nenhum": pagina('<meta name="description" content="2026-11-20">', '<time datetime="2026-11-17T10:00:00Z">17/11</time>'),
            "so-o-dia": pagina(META % "2026-11-18"),
            "aspas-simples": pagina("<META CONTENT='2026-11-19T08:00:00Z' PROPERTY='article:published_time' />"),
            "atributo-name": pagina('<meta name="article:published_time" content="2026-11-17T08:00:00+00:00">'),
            "data-absurda": pagina(META % "1066-10-14T09:00:00Z"),
        })
        self.urls("meta", "meta-vira-o-dia", "json-ld", "os-dois", "meta-ilegivel", "nenhum", "so-o-dia", "aspas-simples",
                  "atributo-name", "data-absurda")
        codigo, linhas, conferencia = self.confere()
        self.assertEqual(self.estados(conferencia), [
            ("meta", "ok", "2026-11-20"), ("meta-vira-o-dia", "ok", "2026-11-21"),  # o dia é o de UTC
            ("json-ld", "ok", "2026-11-18"), ("os-dois", "ok", "2026-11-19"),      # o meta vem primeiro
            ("meta-ilegivel", "ok", "2026-11-18"), ("nenhum", "ok", None),         # o <time> não é lido
            ("so-o-dia", "ok", "2026-11-18"), ("aspas-simples", "ok", "2026-11-19"), ("atributo-name", "ok", "2026-11-17"),
            ("data-absurda", "ok", None)])
        self.assertEqual((codigo, linhas[-1]), (0, "OK 10 páginas: 8 com data, 0 bloqueadas, 0 com erro"))

    def test_json_ld_em_varias_formas(self):
        outra = {"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "datePublished": "2026-10-01"}]}
        artigo = {"@type": ["Thing", "NewsArticle"], "datePublished": "2026-11-19T22:00:00+09:00", "author": {"@type": "Person", "name": "x"}}
        self.paginas({
            "grafo": pagina(LD % json.dumps({"@context": "https://schema.org", "@graph": [{"@type": "WebSite"}, artigo]})),
            "lista": pagina(LD % json.dumps([{"@type": "BreadcrumbList"}, artigo])),
            "outra-materia-antes": pagina(LD % json.dumps(outra) + LD % json.dumps(artigo)),
            "so-outra-materia": pagina(LD % json.dumps(outra)),
            "quebrado": pagina(LD % '{"@type": "NewsArticle", "datePublished": "2026-11-16T05:00:00Z", }'),
            "comentado": pagina(LD % ("<!-- " + json.dumps(artigo) + " -->")),
            "no-corpo": pagina("", "<p>texto</p>" + LD % json.dumps(artigo)),
            "script-comum": pagina('<script>var dados = {"datePublished": "2026-11-01"};</script>'),
            "depois-de-muitos-scripts": pagina("<script>var a = 1;</script>" * 80 + LD % json.dumps(artigo)),
            "data-que-nao-e-texto": pagina(LD % '{"@type": "Article", "datePublished": 20261120}'),
        })
        nomes = ["grafo", "lista", "outra-materia-antes", "so-outra-materia", "quebrado", "comentado", "no-corpo", "script-comum",
                 "depois-de-muitos-scripts", "data-que-nao-e-texto"]
        self.urls(*nomes)
        achado = dict((nome, dia) for nome, _, dia in self.estados(self.confere()[2]))
        self.assertEqual(achado, {
            "grafo": "2026-11-19", "lista": "2026-11-19", "outra-materia-antes": "2026-11-19",  # a do artigo, não a da lista
            "so-outra-materia": "2026-10-01", "quebrado": "2026-11-16", "comentado": "2026-11-19", "no-corpo": "2026-11-19",
            "script-comum": None, "depois-de-muitos-scripts": "2026-11-19", "data-que-nao-e-texto": None})

    def test_pagina_que_nao_e_html(self):
        com_meta = pagina(META % "2026-11-20T10:00:00Z")
        self.grava(os.path.join(self.off, "doc.bin"), b"%PDF-1.7\n" + com_meta)
        self.grava(os.path.join(self.off, "pagina.bin"), com_meta)
        self.grava(os.path.join(self.off, "utf16.bin"), com_meta.decode("utf-8").encode("utf-16"))
        self.grava(os.path.join(self.off, "grande.bin"), com_meta + b"<!-- " + b"x" * (2 * 1024 * 1024) + b" -->")
        self.paginas({}, **{
            "pdf": {"arquivo": "pagina.bin", "tipo": "application/pdf"},
            "json": {"arquivo": "pagina.bin", "tipo": "application/json"},
            "texto": {"arquivo": "pagina.bin", "tipo": "text/plain"},
            "pdf-sem-tipo": {"arquivo": "doc.bin"},
            "html-sem-tipo": {"arquivo": "pagina.bin"},
            "xhtml": {"arquivo": "pagina.bin", "tipo": "application/xhtml+xml"},
            "utf16": {"arquivo": "utf16.bin", "tipo": "text/html; charset=utf-16"},
            "maior-que-2-mb": {"arquivo": "grande.bin", "tipo": "text/html"},
            "vazia": {"tipo": "text/html"},
        })
        nomes = ["pdf", "json", "texto", "pdf-sem-tipo", "html-sem-tipo", "xhtml", "utf16", "maior-que-2-mb", "vazia"]
        self.urls(*nomes)
        codigo, linhas, conferencia = self.confere()
        # CONTRATO, seção 1.1: a página é lida sem Content-Type, ou com text/html ou application/xhtml+xml. Sem o
        # cabeçalho, nem o começo de PDF muda isso. A resposta maior que 2 MB é `bloqueada`.
        self.assertEqual(self.estados(conferencia), [
            ("pdf", "ok", None), ("json", "ok", None), ("texto", "ok", None), ("pdf-sem-tipo", "ok", "2026-11-20"),
            ("html-sem-tipo", "ok", "2026-11-20"), ("xhtml", "ok", "2026-11-20"), ("utf16", "ok", "2026-11-20"),
            ("maior-que-2-mb", "bloqueada", None), ("vazia", "ok", None)])
        self.assertEqual(linhas[-1], "OK 9 páginas: 4 com data, 1 bloqueada, 0 com erro")

    def test_nao_segue_link_nem_roda_script(self):
        outra = SITE + "outra"
        isca = pagina('<meta http-equiv="refresh" content="0; url=%s"><link rel="canonical" href="%s"><script src="%s"></script>'
                      % (outra, outra, outra) + META % "2026-11-20T08:00:00Z",
                      '<a href="%s">leia também</a><iframe src="%s"></iframe><script>fetch("%s")</script>' % (outra, outra, outra))
        self.paginas({"isca": isca, "outra": pagina(META % "2020-01-01T00:00:00Z")})
        self.urls("isca")
        codigo, linhas, conferencia = self.confere()
        self.assertEqual(self.estados(conferencia), [("isca", "ok", "2026-11-20")])
        # dentro do processo: achar a data não faz pedido nenhum
        with mock.patch.object(rede.Rede, "baixa") as baixa:
            resposta = rede.Resposta(SITE + "isca", status=200, tipo="text/html", corpo=isca)
            self.assertEqual(coleta.confere_pagina(resposta), ("ok", "2026-11-20"))
            baixa.assert_not_called()


class TestaEstados(CasoConfere):
    def test_os_tres_estados_e_a_linha_do_contrato(self):
        com_data = pagina(META % "2026-11-20T10:00:00Z")
        self.paginas(dict(("com-data-%d" % n, com_data) for n in range(1, 7)), **{
            "recusada": {"status": 403, "tipo": "text/html"}, "limite": {"status": 429}, "sumiu": {"status": 404},
        })
        self.urls(*(["com-data-%d" % n for n in range(1, 7)] + ["recusada", "limite", "sumiu"]))
        codigo, linhas, conferencia = self.confere()
        self.assertEqual((codigo, linhas[-1]), (0, "OK 9 páginas: 6 com data, 2 bloqueadas, 1 com erro"))
        self.assertEqual(self.estados(conferencia)[6:], [("recusada", "bloqueada", None), ("limite", "bloqueada", None), ("sumiu", "erro", None)])
        self.assertEqual(list(conferencia), ["versao", "gerada_em", "paginas"])
        self.assertEqual((conferencia["versao"], conferencia["gerada_em"], list(conferencia["paginas"][0])),
                         (1, AGORA, ["url", "estado", "publicado_em"]))
        self.assertEqual(conferencia["paginas"][0], {"url": SITE + "com-data-1", "estado": "ok", "publicado_em": "2026-11-20"})

    def test_cada_codigo_e_cada_falha(self):
        self.paginas({"boa": pagina(), "destino": pagina(META % "2026-11-19T10:00:00Z")}, **{
            "c401": {"status": 401}, "c403": {"status": 403}, "c429": {"status": 429}, "c404": {"status": 404},
            "c410": {"status": 410}, "c500": {"status": 500}, "c503": {"status": 503}, "c400": {"status": 400},
            "mudou": {"status": 301, "para": SITE + "destino"}, "para-arquivo": {"para": "file:///etc/passwd"},
            "laco": {"para": SITE + "laco"}, "para-o-nada": {"para": SITE + "nao-esta-no-mapa"},
            "c451": {"status": 451}, "sem-nome": {"falha": "nome"}, "lenta": {"arquivo": "boa.html", "demora": 0.3},
        })
        nomes = ["boa", "c401", "c403", "c429", "c404", "c410", "c500", "c503", "c400", "mudou", "para-arquivo", "laco",
                 "para-o-nada", "ausente", "c451", "sem-nome", "lenta"]
        # usuário e senha na URL: nem é URL (ESQUEMA, seção 0), e a linha é pulada com aviso
        self.urls(cru="".join(SITE + n + "\n" for n in nomes) + "http://127.0.0.1:8188/prompt\nhttps://usuario:senha@exemplo.invalid/x\n")
        codigo, linhas, conferencia = self.confere()
        achado = dict((nome, (estado, dia)) for nome, estado, dia in self.estados(conferencia))
        self.assertEqual(achado, {
            "boa": ("ok", None), "c401": ("bloqueada", None), "c403": ("bloqueada", None), "c429": ("bloqueada", None),
            "c404": ("erro", None), "c410": ("erro", None), "c500": ("bloqueada", None), "c503": ("bloqueada", None),
            "c400": ("bloqueada", None), "mudou": ("ok", "2026-11-19"), "para-arquivo": ("bloqueada", None),
            "laco": ("bloqueada", None), "para-o-nada": ("bloqueada", None), "ausente": ("bloqueada", None),
            "http://127.0.0.1:8188/prompt": ("erro", None),
            "c451": ("bloqueada", None), "sem-nome": ("erro", None), "lenta": ("ok", None)})
        self.assertIn("aviso: 1 linha de urls.txt não é URL http(s): pulada", linhas)
        self.assertEqual(linhas[-1], "OK 18 páginas: 1 com data, 11 bloqueadas, 4 com erro")

    def test_falhas_que_o_offline_nao_ensaia(self):
        def de(motivo, erro="x"):
            return coleta.confere_pagina(rede.Resposta(SITE + "a", erro=erro, motivo=motivo))

        self.assertEqual(de(rede.NOME), ("erro", None))        # o nome do site não existe
        self.assertEqual(de(rede.TEMPO), ("bloqueada", None))  # não respondeu a tempo
        self.assertEqual(de(rede.TETO), ("bloqueada", None))
        self.assertEqual(coleta.confere_pagina(None), ("bloqueada", None))  # o teto do lote cortou
        for motivo in (rede.CONEXAO, rede.CERTIFICADO, rede.PROXY, rede.PROTOCOLO, rede.DESVIO, rede.OFFLINE):
            self.assertEqual(de(motivo), ("bloqueada", None), motivo)

    def test_nenhuma_pagina_respondeu_e_falha_sem_rede_com_tudo_bloqueada(self):
        self.paginas({}, **{"sumiu": {"status": 404}, "recusada": {"status": 403}, "apagada": {"status": 410}})
        self.urls("sumiu", "recusada", "ausente", "apagada")
        codigo, linhas, conferencia = self.confere()
        self.assertEqual((codigo, linhas[-1]), (4, "FALHA sem rede: 0 páginas"))
        # 404 e 410 são resposta de servidor, que não depende da rede: a página não existe, e fica `erro`
        # (CONTRATO, seção 1.1); o resto vira `bloqueada`
        self.assertEqual(self.estados(conferencia), [("sumiu", "erro", None), ("recusada", "bloqueada", None),
                                                     ("ausente", "bloqueada", None), ("apagada", "erro", None)])
        # a 404 sozinha: FALHA sem rede, e a página inventada continua sem valer como fonte (regra T3)
        self.urls("sumiu")
        codigo, linhas, conferencia = self.confere()
        self.assertEqual((codigo, linhas[-1], self.estados(conferencia)), (4, "FALHA sem rede: 0 páginas",
                                                                           [("sumiu", "erro", None)]))
        # nada coube no tempo (a página demora 5 s; com --tempo 1 a rede para em 0,9 s): mesma coisa
        self.paginas({"lenta": pagina(META % "2026-11-20T10:00:00Z")})
        self.respostas[SITE + "lenta"]["demora"] = 5
        self.grava_respostas()
        self.urls("lenta")
        codigo, linhas, conferencia = self.confere("--tempo", "1")
        self.assertEqual((codigo, linhas[-1], self.estados(conferencia)), (4, "FALHA sem rede: 0 páginas", [("lenta", "bloqueada", None)]))
        # o nome do site não existe em todas: nenhuma respondeu, e a regra do código 4 vale mais que a tabela
        self.paginas({}, **{"sem-nome-1": {"falha": "nome"}, "sem-nome-2": {"falha": "nome"}})
        self.urls("sem-nome-1", "sem-nome-2")
        codigo, linhas, conferencia = self.confere()
        self.assertEqual((codigo, set(p["estado"] for p in conferencia["paginas"])), (4, {"bloqueada"}))

    def test_singular_e_pagina_sem_data(self):
        self.paginas({"uma": pagina(META % "2026-11-20T10:00:00Z"), "sem-data": pagina()}, recusada={"status": 403})
        self.urls("uma")
        self.assertEqual(self.confere()[1][-1], "OK 1 página: 1 com data, 0 bloqueadas, 0 com erro")
        self.urls("sem-data", "recusada")
        self.assertEqual(self.confere()[1][-1], "OK 2 páginas: 0 com data, 1 bloqueada, 0 com erro")


class TestaUrls(CasoConfere):
    def test_sem_urls_txt_ou_sem_url_nova(self):
        os.makedirs(self.trabalho)
        codigo, linhas, conferencia = self.confere()
        self.assertEqual((codigo, linhas[-1], conferencia), (0, "OK 0 páginas", {"versao": 1, "gerada_em": AGORA, "paginas": []}))
        self.urls(cru="\n# só comentário\n\n")
        self.assertEqual(self.confere()[1][-1], "OK 0 páginas")

    def test_url_que_ja_esta_na_coleta_nao_e_conferida(self):
        self.feeds({"og_um": rss(item("Da coleta", link="https://og-um.exemplo.invalid/materia?id=3"))})
        self.roda()
        self.paginas({"nova": pagina(META % "2026-11-20T10:00:00Z")})
        self.urls(cru="https://og-um.exemplo.invalid/materia?id=3\nhttp://www.og-um.exemplo.invalid/materia/?id=3&utm_source=x#topo\n"
                      + SITE + "nova\n")
        codigo, linhas, conferencia = self.confere()
        self.assertEqual(self.estados(conferencia), [("nova", "ok", "2026-11-20")])
        self.assertIn("CONFERE · 3 URLs em urls.txt, 1 fora da coleta", linhas)

    def test_coleta_json_quebrado_nao_derruba(self):
        self.paginas({"nova": pagina(META % "2026-11-20T10:00:00Z")})
        self.urls("nova")
        for estrago in (b"{quebrado", b"[1, 2]", b'{"manchetes": [7, {"url": 3}, null]}'):
            self.grava(os.path.join(self.trabalho, "coleta.json"), estrago)
            codigo, linhas, conferencia = self.confere()
            self.assertEqual((codigo, self.estados(conferencia)), (0, [("nova", "ok", "2026-11-20")]), estrago)

    def test_linhas_do_urls_txt(self):
        self.paginas({"a": pagina(META % "2026-11-20T10:00:00Z"), "b": pagina(META % "2026-11-19T10:00:00Z")})
        cru = ("\ufeff# páginas abertas nesta execução\r\n\r\n  " + SITE + "a  \r\n" + SITE + "a#comentarios\r\n" + SITE + "a/\r\n"
               "isto não é endereço\r\nftp://exemplo.invalid/arquivo\r\n" + SITE + "b?utm_medium=social\r\n#" + SITE + "comentada\r\n")
        self.urls(cru=cru)
        codigo, linhas, conferencia = self.confere()
        self.assertEqual([p["url"] for p in conferencia["paginas"]], [SITE + "a", SITE + "b?utm_medium=social"])
        self.assertEqual(conferencia["paginas"][1]["estado"], "bloqueada")  # a chave do --offline é a URL exata do pedido
        self.assertIn("aviso: 2 linhas de urls.txt não é URL http(s): pulada", linhas)

    def test_url_com_caractere_que_nao_se_ve_nao_vai_para_a_saida(self):
        self.paginas({"a": pagina(META % "2026-11-20T10:00:00Z")})
        self.urls(cru=SITE + "a\n" + SITE + "b\x1b[31mvermelho\n" + SITE + "c\u202edireita\n" + SITE + "d\x00nulo\n")
        codigo, linhas, conferencia = self.confere()
        self.assertEqual([p["url"] for p in conferencia["paginas"]], [SITE + "a"])
        self.assertIn("aviso: 3 linhas de urls.txt não é URL http(s): pulada", linhas)
        self.assertNotRegex("\n".join(linhas), "[\x00-\x08\x0e-\x1f\u202e]")

    def test_url_com_aspas_cifrao_crase_barra_ou_usuario_e_pulada(self):
        """ESQUEMA, seção 0, "URL": nada de aspas, apóstrofo, crase, cifrão, barra invertida nem usuário@. Uma
        URL assim fecha a aspa ou roda comando numa linha de shell, ou leva o navegador a outro site."""
        self.paginas({"a": pagina(META % "2026-11-20T10:00:00Z")})
        ruins = [SITE + "b'x", SITE + 'c"x', SITE + "d`id`", SITE + "e$(id)", SITE + "f$HOME",
                 "https://golpe.exemplo.invalid\\@" + SITE[len("https://"):] + "g", "https://alguem@" + SITE[len("https://"):] + "h"]
        self.urls(cru=SITE + "a\n" + "".join(url + "\n" for url in ruins))
        codigo, linhas, conferencia = self.confere()
        self.assertEqual([p["url"] for p in conferencia["paginas"]], [SITE + "a"])
        self.assertIn("aviso: 7 linhas de urls.txt não é URL http(s): pulada", linhas)
        self.assertEqual(linhas[-1], "OK 1 página: 1 com data, 0 bloqueadas, 0 com erro")

    def test_ate_30_paginas_por_execucao(self):
        self.paginas(dict(("p%02d" % n, pagina(META % "2026-11-20T10:00:00Z")) for n in range(35)))
        self.urls(*["p%02d" % n for n in range(35)])
        codigo, linhas, conferencia = self.confere()
        self.assertEqual([p["url"] for p in conferencia["paginas"]], [SITE + "p%02d" % n for n in range(30)])
        self.assertEqual(linhas[-1], "OK 30 páginas: 30 com data, 0 bloqueadas, 0 com erro; 5 URLs fora do teto de 30")
        self.assertIn("aviso: 5 URLs ficaram sem conferir: o teto é de 30 por execução", linhas)

    def test_nao_le_o_repositorio_nem_depende_do_contexto(self):
        self.paginas({"a": pagina(META % "2026-11-20T10:00:00Z")})
        self.urls("a")
        self.grava(os.path.join(self.trabalho, "contexto.json"), b"{quebrado")
        vazia = os.path.join(self.pasta, "repositorio-vazio")
        os.makedirs(vazia)
        codigo, linhas, conferencia = self.confere("--raiz", vazia)
        self.assertEqual((codigo, self.estados(conferencia)), (0, [("a", "ok", "2026-11-20")]))
        self.assertEqual(os.listdir(vazia), [])
        self.assertEqual(sorted(os.listdir(self.trabalho)), ["conferencia.json", "contexto.json", "urls.txt"])

    def test_erro_de_uso_nao_grava_nada(self):
        self.urls("a")
        for opcoes in (["--tempo", "x"], ["--nao-existe"], ["--offline", os.path.join(self.pasta, "sumiu")]):
            codigo, linhas, conferencia = self.confere(*opcoes)
            self.assertEqual((codigo, conferencia, linhas[0][:11]), (2, None, "FALHA uso: "), opcoes)

    def test_mesma_entrada_mesmos_bytes(self):
        self.paginas({"a": pagina(META % "2026-11-20T10:00:00Z")}, b={"status": 403})
        self.urls("a", "b", "c")

        def retrato():
            self.confere()
            with open(os.path.join(self.trabalho, "conferencia.json"), "rb") as arquivo:
                return arquivo.read()

        primeiro = retrato()
        self.assertEqual(primeiro, retrato())
        self.assertTrue(primeiro.endswith(b"}\n") and b'\n  "paginas": [\n' in primeiro)


if __name__ == "__main__":
    unittest.main()
