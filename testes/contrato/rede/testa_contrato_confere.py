#!/usr/bin/env python3
"""Testes de contrato de `coleta.py --confere`: a data das páginas abertas (CONTRATO, seção 1.1).

Escritos só a partir do contrato, sem ler o código, e conciliados com ele na fase 2b: onde o
contrato não fechava a questão, a decisão virou frase do contrato, e o teste cita essa frase. Cada
teste cita, na docstring, a cláusula que confere.

    python3 -B testes/contrato/rede/testa_contrato_confere.py
"""
import importlib.util
import json
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location("apoio_contrato_rede", Path(__file__).resolve().parent / "apoio.py")
apoio = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = apoio
_spec.loader.exec_module(apoio)

HTML = "text/html; charset=utf-8"
PAGINA = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Página fictícia</title>
%s
</head>
<body>
<h1>Página fictícia</h1>
<p>Texto de exemplo, sem valor de notícia.</p>
%s
</body>
</html>
"""


def pagina(cabeca="", corpo=""):
    return PAGINA % (cabeca, corpo)


def meta(data):
    return '<meta property="article:published_time" content="%s">' % data


def jsonld(objeto):
    return '<script type="application/ld+json">%s</script>' % json.dumps(objeto, ensure_ascii=False)


def artigo(data):
    return jsonld({"@context": "https://schema.org", "@type": "NewsArticle", "headline": "Página fictícia",
                   "datePublished": data})


def coleta_de_teste(urls=()):
    """Um coleta.json no formato do CONTRATO, seção 1, com uma manchete para cada URL dada."""
    manchetes = [{"id": "m%04d" % n, "historia": "h%02d" % n, "veiculo": "gazeta_og", "lado": "ordem_global",
                  "fatos": "alta", "titulo": "Manchete fictícia %d" % n, "resumo": "Resumo fictício.", "url": url,
                  "publicado_em": "2026-11-20T12:00:00Z", "categoria": "geopolitica", "suspeito": False}
                 for n, url in enumerate(urls, 1)]
    historias = [{"id": m["historia"], "pontos": 4, "categoria": "geopolitica", "partidos": ["ordem_global"],
                  "veiculos": 1, "manchetes": [m["id"]]} for m in manchetes]
    partidos = {"ordem_global": len(manchetes), "centro_atlantico": 0, "bancada_talento": 0, "soberanistas": 0,
                "eixo_revisionista": 0, "centrao": 0, "independentes": 0}
    return {"versao": 1, "dia": apoio.DIA, "gerada_em": apoio.AGORA, "janela_horas": 36,
            "resumo": {"feeds_ok": 9, "feeds_falhos": 0, "veiculos_ok": 9, "manchetes": len(manchetes),
                       "suspeitas": 0, "partidos": partidos},
            "feeds": [{"veiculo": "gazeta_og", "url": "https://gazeta-og.exemplo.invalid/rss.xml", "estado": "ok",
                       "itens": len(manchetes), "erro": ""}],
            "manchetes": manchetes, "historias": historias}


def u(caminho, site="gazeta-og"):
    return "https://%s.exemplo.invalid/%s" % (site, caminho)


class CasoConfere(apoio.Caso):

    def setUp(self):
        super().setUp()
        self.b.poe_no_trabalho("coleta.json", coleta_de_teste())

    def nova(self):
        self.b = apoio.Bancada()
        self.addCleanup(self.b.fecha)
        self.b.poe_no_trabalho("coleta.json", coleta_de_teste())
        return self.b

    def urls(self, *linhas):
        self.b.poe_no_trabalho("urls.txt", "".join(linha + "\n" for linha in linhas))

    def poe(self, url, cabeca="", corpo="", tipo=HTML, **resposta):
        self.b.responde(url, pagina(cabeca, corpo), tipo=tipo, **resposta)

    def confere(self, *args, **opcoes):
        return self.b.roda("coleta", "--confere", *args, **opcoes)

    def paginas(self, res):
        """As páginas de conferencia.json, por URL."""
        conferencia = self.json_gravado(res, "conferencia.json")
        self.assertIsInstance(conferencia, dict)
        self.assertIn("paginas", conferencia, "conferencia.json sem a chave paginas" + res.relato())
        return {p["url"]: p for p in conferencia["paginas"]}

    def uma_pagina(self, cabeca="", corpo="", tipo=HTML, **resposta):
        """Uma URL só em urls.txt, com a página dada. Devolve (res, a entrada dela em conferencia.json)."""
        url = u("analise/pagina-sob-teste")
        self.urls(url)
        self.poe(url, cabeca, corpo, tipo, **resposta)
        res = self.confere()
        paginas = self.paginas(res)
        self.assertEqual(list(paginas), [url], res.relato())
        return res, paginas[url]


class DataDaPagina(CasoConfere):

    def test_data_no_meta_article_published_time(self):
        """CONTRATO, seção 1.1: procura a data «em dois lugares, nesta ordem: `<meta
        property="article:published_time">` e `"datePublished"` no bloco de dados da página (JSON-LD)»; tabela:
        «`ok`: a página respondeu. `publicado_em` é a data achada (dia em UTC)».

        Página só com o meta, de 20/11 às 08:15 UTC: estado ok, publicado_em 2026-11-20.
        """
        res, p = self.uma_pagina(meta("2026-11-20T08:15:00+00:00"))
        self.assertEqual((p["estado"], p["publicado_em"]), ("ok", "2026-11-20"))
        self.confere_veredito(res, "OK", 0)

    def test_data_no_datepublished_do_json_ld(self):
        """CONTRATO, seção 1.1: o segundo lugar é «`"datePublished"` no bloco de dados da página (JSON-LD)».

        Página sem o meta, com JSON-LD de 19/11 às 15:00 UTC: estado ok, publicado_em 2026-11-19.
        """
        res, p = self.uma_pagina(artigo("2026-11-19T15:00:00Z"))
        self.assertEqual((p["estado"], p["publicado_em"]), ("ok", "2026-11-19"))

    def test_com_os_dois_vale_o_meta(self):
        """CONTRATO, seção 1.1: «em dois lugares, nesta ordem: `<meta property="article:published_time">` e
        `"datePublished"`».

        O meta diz 18/11 e o JSON-LD diz 20/11: vale 2026-11-18. Vale igual quando o JSON-LD aparece
        antes do meta no texto da página: a ordem é a da procura, não a do arquivo.
        """
        casos = {"meta primeiro no arquivo": meta("2026-11-18T10:00:00Z") + "\n" + artigo("2026-11-20T10:00:00Z"),
                 "json-ld primeiro no arquivo": artigo("2026-11-20T10:00:00Z") + "\n" + meta("2026-11-18T10:00:00Z")}
        for nome, cabeca in casos.items():
            with self.subTest(caso=nome):
                self.nova()
                res, p = self.uma_pagina(cabeca)
                self.assertEqual((p["estado"], p["publicado_em"]), ("ok", "2026-11-18"))

    def test_a_data_e_o_dia_em_utc(self):
        """CONTRATO, seção 1.1, tabela: «`publicado_em` é a data achada (dia em UTC)».

        Meta com 19/11 às 23:30 em −03:00: em UTC já é 20/11. JSON-LD com 21/11 à 00:30 em +02:00: em
        UTC ainda é 20/11.
        """
        casos = {"meta em -03:00": meta("2026-11-19T23:30:00-03:00"), "json-ld em +02:00": artigo("2026-11-21T00:30:00+02:00")}
        for nome, cabeca in casos.items():
            with self.subTest(caso=nome):
                self.nova()
                res, p = self.uma_pagina(cabeca)
                self.assertEqual((p["estado"], p["publicado_em"]), ("ok", "2026-11-20"))

    def test_data_escrita_so_com_o_dia(self):
        """CONTRATO, seção 1.1, tabela: «`publicado_em` é a data achada (dia em UTC)».

        O campo traz só `2026-11-20`, sem hora: a data achada é esse dia.
        """
        casos = {"meta": meta("2026-11-20"), "json-ld": artigo("2026-11-20")}
        for nome, cabeca in casos.items():
            with self.subTest(caso=nome):
                self.nova()
                res, p = self.uma_pagina(cabeca)
                self.assertEqual((p["estado"], p["publicado_em"]), ("ok", "2026-11-20"))

    def test_meta_com_os_atributos_em_outra_ordem(self):
        """CONTRATO, seção 1.1: o primeiro lugar é «`<meta property="article:published_time">`».

        A mesma marca com `content` antes de `property` e fechada com `/>`: em HTML a ordem dos
        atributos não muda a marca. A data é achada.
        """
        res, p = self.uma_pagina('<meta content="2026-11-20T08:15:00Z" property="article:published_time" />')
        self.assertEqual((p["estado"], p["publicado_em"]), ("ok", "2026-11-20"))

    def test_datepublished_dentro_de_graph(self):
        """CONTRATO, seção 1.1: «`"datePublished"` no bloco de dados da página (JSON-LD)».

        O bloco JSON-LD traz o artigo dentro de `@graph`, depois de outro item: o campo está no bloco, e
        a data é achada.
        """
        bloco = jsonld({"@context": "https://schema.org", "@graph": [
            {"@type": "WebSite", "name": "Gazeta de Exemplo"},
            {"@type": "NewsArticle", "headline": "Página fictícia", "datePublished": "2026-11-19T15:00:00Z"}]})
        res, p = self.uma_pagina(bloco)
        self.assertEqual((p["estado"], p["publicado_em"]), ("ok", "2026-11-19"))

    def test_pagina_sem_nenhum_dos_dois_campos(self):
        """CONTRATO, seção 1.1, tabela: `publicado_em` é «`null` se a página não traz nenhum dos dois campos»; e
        «Não segue link, não roda script, não lê mais nada da página.»

        A página responde e traz outras datas (modified_time, og:updated_time, meta name=date, <time>,
        dateModified e dateCreated no JSON-LD) e links para outra página que tem a data. Nada disso
        conta: estado ok, publicado_em null, e a outra página não é pedida.
        """
        outra = u("analise/outra-pagina-com-data")
        self.poe(outra, meta("2026-11-20T08:15:00Z"))
        cabeca = "\n".join([
            '<meta property="article:modified_time" content="2026-11-20T09:00:00Z">',
            '<meta property="og:updated_time" content="2026-11-20T09:00:00Z">',
            '<meta name="date" content="2026-11-20">',
            '<link rel="canonical" href="%s">' % outra,
            '<meta http-equiv="refresh" content="30; url=%s">' % outra,
            jsonld({"@context": "https://schema.org", "@type": "NewsArticle", "dateModified": "2026-11-20T09:00:00Z",
                    "dateCreated": "2026-11-20T07:00:00Z"})])
        corpo = '<p>Publicado em <time datetime="2026-11-20T08:00:00Z">20/11/2026</time>. <a href="%s">Leia mais</a></p>' % outra
        res, p = self.uma_pagina(cabeca, corpo)
        self.assertEqual((p["estado"], p["publicado_em"]), ("ok", None))
        self.confere_veredito(res, "OK", 0)

    def test_pagina_que_nao_e_html(self):
        """CONTRATO, seção 1.1, tabela: `publicado_em` é «`null` se a página não traz nenhum dos dois campos, ou
        não é HTML»; seção 0, "Rede": a ferramenta só lê, «no modo `--confere`, dois campos de data do HTML».

        Resposta 200 com Content-Type de PDF e de JSON. O corpo traz, de propósito, o texto dos dois
        campos: como não é HTML, a data fica null, e o estado é ok.
        """
        corpo_pdf = "%PDF-1.4\n" + meta("2026-11-20T08:15:00Z") + "\n"
        corpo_json = json.dumps({"@type": "NewsArticle", "datePublished": "2026-11-20T08:15:00Z"})
        for tipo, corpo in (("application/pdf", corpo_pdf), ("application/json", corpo_json),
                            ("text/plain; charset=utf-8", pagina(meta("2026-11-20T08:15:00Z")))):
            with self.subTest(tipo=tipo):
                self.nova()
                url = u("documentos/arquivo")
                self.urls(url)
                self.b.responde(url, corpo, tipo=tipo)
                res = self.confere()
                p = self.paginas(res)[url]
                self.assertEqual((p["estado"], p["publicado_em"]), ("ok", None))

    def test_forma_simples_sem_content_type_e_lida_como_html(self):
        """CONTRATO, seção 1.1: «A página é lida quando não há `Content-Type`, ou quando ele é `text/html` ou
        `application/xhtml+xml`»; seção 0, --offline: na forma simples não há `tipo`, e «`tipo` é o cabeçalho
        `Content-Type` (sem o campo, nenhum)».
        """
        url = u("analise/pagina-forma-simples")
        self.urls(url)
        self.b.responde(url, pagina(meta("2026-11-20T12:00:00Z")))
        self.assertIsInstance(self.b.respostas[url], str)
        res = self.confere()
        p = self.paginas(res)[url]
        self.assertEqual((p["estado"], p["publicado_em"]), ("ok", "2026-11-20"))

    def test_xhtml_e_lida(self):
        """CONTRATO, seção 1.1: a página é lida quando o `Content-Type` «é `text/html` ou `application/xhtml+xml`
        (o `; charset=…` não conta)»."""
        res, p = self.uma_pagina(meta("2026-11-20T08:15:00Z"), tipo="application/xhtml+xml; charset=utf-8")
        self.assertEqual((p["estado"], p["publicado_em"]), ("ok", "2026-11-20"))

    def test_pagina_redirecionada(self):
        """CONTRATO, seção 0, --offline: «`para` é um redirecionamento: a ferramenta segue como seguiria na rede».

        A URL de urls.txt responde 302 para outra, que traz a data. Em conferencia.json a página aparece
        com a URL de urls.txt, estado ok e a data do destino.
        """
        origem, destino = u("analise/endereco-antigo"), u("analise/endereco-novo")
        self.urls(origem)
        self.b.responde(origem, status=302, para=destino)
        self.poe(destino, meta("2026-11-19T09:30:00+01:00"))
        res = self.confere()
        paginas = self.paginas(res)
        self.assertEqual(list(paginas), [origem])
        self.assertEqual((paginas[origem]["estado"], paginas[origem]["publicado_em"]), ("ok", "2026-11-19"))


class EstadosDaPagina(CasoConfere):

    def com_status(self, status):
        self.nova()
        url = u("analise/pagina-com-status-%d" % status)
        self.urls(url, u("analise/pagina-boa"))
        # o corpo traz a data de propósito: com esses códigos, ela não pode ser lida
        self.poe(url, meta("2026-11-20T08:15:00Z"), status=status)
        self.poe(u("analise/pagina-boa"), meta("2026-11-20T08:15:00Z"))
        res = self.confere()
        paginas = self.paginas(res)
        self.assertEqual(paginas[u("analise/pagina-boa")]["estado"], "ok")
        return res, paginas[url]

    def test_bloqueada_com_401_403_e_429(self):
        """CONTRATO, seção 1.1, tabela: «`bloqueada`: o site recusou a máquina (códigos 401, 403, 429) ou não
        respondeu a tempo»; no exemplo, a página bloqueada tem `"publicado_em": null`.
        """
        for status in (401, 403, 429):
            with self.subTest(status=status):
                res, p = self.com_status(status)
                self.assertEqual((p["estado"], p["publicado_em"]), ("bloqueada", None))
                self.confere_veredito(res, "OK", 0)

    def test_erro_com_404_e_410(self):
        """CONTRATO, seção 1.1, tabela: «`erro`: a página não existe (códigos 404 e 410) ou o nome do site não
        existe»; no exemplo, a página com erro tem `"publicado_em": null`.
        """
        for status in (404, 410):
            with self.subTest(status=status):
                res, p = self.com_status(status)
                self.assertEqual((p["estado"], p["publicado_em"]), ("erro", None))
                self.confere_veredito(res, "OK", 0)

    def test_bloqueada_com_5xx_e_outros_4xx(self):
        """CONTRATO, seção 1.1, tabela: `bloqueada` é «401, 403, 429, 5xx, outros 4xx» (fora 404 e 410)."""
        for status in (400, 451, 500, 503):
            with self.subTest(status=status):
                res, p = self.com_status(status)
                self.assertEqual((p["estado"], p["publicado_em"]), ("bloqueada", None))
                self.confere_veredito(res, "OK", 0)

    def test_resposta_maior_que_2_mb_e_bloqueada(self):
        """CONTRATO, seção 1.1, tabela: `bloqueada` inclui a «resposta maior que 2 MB»; seção 0, "Rede": «no
        `--confere`, a página é `bloqueada`». A data, no começo da página, não é lida."""
        url = u("analise/pagina-enorme")
        self.urls(url, u("analise/pagina-boa"))
        self.b.responde(url, pagina(meta("2026-11-20T08:15:00Z"), "<!-- %s -->" % ("x" * 3000000)), tipo=HTML)
        self.poe(u("analise/pagina-boa"), meta("2026-11-20T08:15:00Z"))
        res = self.confere()
        p = self.paginas(res)[url]
        self.assertEqual((p["estado"], p["publicado_em"]), ("bloqueada", None))

    def test_nome_do_site_que_nao_existe_e_erro(self):
        """CONTRATO, seção 1.1, tabela: `erro` quando «o nome do site não existe»; seção 0, --offline:
        «`"falha": "nome"` simula o nome do site que não existe (no `--confere`, `erro`)»."""
        url = u("analise/site-que-nao-existe", "site-inexistente")
        self.urls(url, u("analise/pagina-boa"))
        self.b.responde(url, falha="nome")
        self.poe(u("analise/pagina-boa"), meta("2026-11-20T08:15:00Z"))
        res = self.confere()
        self.assertEqual((self.paginas(res)[url]["estado"], self.paginas(res)[url]["publicado_em"]), ("erro", None))
        self.confere_veredito(res, "OK", 0)

    def test_pagina_lenta_alem_do_tempo_e_bloqueada(self):
        """CONTRATO, seção 1.1, tabela: `bloqueada` é o site que «não respondeu a tempo»; seção 0, --offline:
        `demora` é esperada de verdade.

        Com --tempo 1, uma página demora 5 segundos e a outra 0,2: a lenta sai bloqueada, e a outra ok.
        """
        import time
        lenta, boa = u("analise/lenta"), u("analise/pagina-boa")
        self.urls(lenta, boa)
        self.poe(lenta, meta("2026-11-20T08:15:00Z"), demora=5)
        self.poe(boa, meta("2026-11-20T08:15:00Z"), demora=0.2)
        inicio = time.monotonic()
        res = self.confere("--tempo", "1")
        self.assertLess(time.monotonic() - inicio, 4.5)
        paginas = self.paginas(res)
        self.assertEqual((paginas[lenta]["estado"], paginas[boa]["estado"]), ("bloqueada", "ok"))
        self.confere_veredito(res, "OK", 0)

    def test_pagina_sem_resposta_no_meio_das_outras(self):
        """CONTRATO, seção 0, --offline: «URL ausente é "não respondeu"» (no `--confere`, `bloqueada`); seção 1.1,
        tabela: `bloqueada` inclui a «URL ausente no `--offline`».

        Uma URL de urls.txt não está em respostas.json, e a outra responde: a ausente sai bloqueada,
        sem data; a outra sai ok, e o veredito é OK.
        """
        ausente, boa = u("analise/sem-resposta"), u("analise/pagina-boa")
        self.urls(ausente, boa)
        self.poe(boa, meta("2026-11-20T08:15:00Z"))
        res = self.confere()
        paginas = self.paginas(res)
        self.assertEqual(paginas[ausente]["estado"], "bloqueada")
        self.assertIsNone(paginas[ausente]["publicado_em"])
        self.assertEqual((paginas[boa]["estado"], paginas[boa]["publicado_em"]), ("ok", "2026-11-20"))
        self.confere_veredito(res, "OK", 0)

    def test_nenhuma_pagina_responde(self):
        """CONTRATO, seção 1.1, "Veredito e código": «Nenhuma página respondeu: `FALHA sem rede: 0 páginas`, código
        4; o `conferencia.json` sai com todas as páginas como `bloqueada`.»

        Três URLs em urls.txt e respostas.json vazio.
        """
        tres = [u("analise/a"), u("analise/b"), u("analise/c", "tribuna-so")]
        self.urls(*tres)
        res = self.confere()
        self.confere_veredito(res, "FALHA", 4)
        self.assertTrue(res.ultima.startswith("FALHA sem rede:"), res.ultima)
        paginas = self.paginas(res)
        self.assertEqual(sorted(paginas), sorted(tres))
        for url in tres:
            self.assertEqual((paginas[url]["estado"], paginas[url]["publicado_em"]), ("bloqueada", None))

    def test_todas_recusadas_tambem_e_falha_sem_rede(self):
        """CONTRATO, seção 1.1, "Veredito e código": «Nenhuma página respondeu (nenhuma com estado `ok`)» →
        `FALHA sem rede: 0 páginas`, código 4.

        Todas as páginas respondem 403: nenhuma ficou `ok`.
        """
        duas = [u("analise/a"), u("analise/b")]
        self.urls(*duas)
        for url in duas:
            self.poe(url, meta("2026-11-20T08:15:00Z"), status=403)
        res = self.confere()
        self.confere_veredito(res, "FALHA", 4)
        self.assertEqual({p["estado"] for p in self.paginas(res).values()}, {"bloqueada"})

    def test_sem_rede_404_e_410_continuam_erro(self):
        """CONTRATO, seção 1.1, "Veredito e código": com nenhuma página `ok`, «Continuam `erro` só a URL que nem
        pode ser pedida e a página que respondeu 404 ou 410: as duas não dependem da rede».

        Uma página inventada (404) sozinha, e depois ao lado de uma 410 e de uma 403.
        """
        sumiu = u("analise/pagina-inventada")
        self.urls(sumiu)
        self.poe(sumiu, status=404)
        res = self.confere()
        self.confere_veredito(res, "FALHA", 4)
        self.assertEqual(self.paginas(res)[sumiu]["estado"], "erro")
        apagada, recusada = u("analise/apagada"), u("analise/recusada")
        self.urls(sumiu, apagada, recusada)
        self.poe(apagada, status=410)
        self.poe(recusada, status=403)
        res = self.confere()
        self.confere_veredito(res, "FALHA", 4)
        paginas = self.paginas(res)
        self.assertEqual([paginas[x]["estado"] for x in (sumiu, apagada, recusada)], ["erro", "erro", "bloqueada"])

    def test_sem_rede_o_nome_que_nao_existe_tambem_vira_bloqueada(self):
        """CONTRATO, seção 1.1, "Veredito e código": com nenhuma página `ok`, «`conferencia.json` sai com todas as
        páginas como `bloqueada` (a regra vale mais que a tabela: até o nome de site que não existe vira
        `bloqueada`, porque numa máquina sem rede todo nome parece não existir)».
        """
        duas = [u("analise/a"), u("analise/b", "tribuna-so")]
        self.urls(*duas)
        for url in duas:
            self.b.responde(url, falha="nome")
        res = self.confere()
        self.confere_veredito(res, "FALHA", 4)
        self.assertEqual({p["estado"] for p in self.paginas(res).values()}, {"bloqueada"})


class QuaisPaginas(CasoConfere):

    def test_url_que_ja_esta_na_coleta_nao_e_pedida_de_novo(self):
        """CONTRATO, seção 1.1: «Para cada URL de `urls.txt` que não está em `coleta.json` […] baixa a página».

        urls.txt tem duas URLs; uma delas é de uma manchete de coleta.json (a data dela já veio do
        feed). Só a outra aparece em conferencia.json, mesmo havendo resposta pronta para as duas.
        """
        da_coleta, nova = u("mundo/manchete-do-feed"), u("analise/pagina-aberta")
        self.b.poe_no_trabalho("coleta.json", coleta_de_teste([da_coleta]))
        self.urls(da_coleta, nova)
        self.poe(da_coleta, meta("2026-11-17T08:00:00Z"))
        self.poe(nova, meta("2026-11-20T08:15:00Z"))
        res = self.confere()
        paginas = self.paginas(res)
        self.assertEqual(list(paginas), [nova])
        self.assertEqual(paginas[nova]["publicado_em"], "2026-11-20")
        self.confere_veredito(res, "OK", 0)

    def test_url_da_coleta_e_reconhecida_pelo_endereco_limpo(self):
        """ESQUEMA, seção 0, "Endereço limpo": «para comparar duas URLs, as ferramentas limpam os dois lados do
        mesmo jeito: esquema e nome do site em minúsculas, `http` igual a `https`, sem `www.`, sem `#…`, sem
        parâmetros `utm_`, sem barra no fim.» CONTRATO, seção 1.1: «sem URL nova: `OK 0 páginas`, código 0».

        A URL de urls.txt é a da manchete de coleta.json, escrita com http, www., barra no fim, utm_ e
        âncora. É a mesma página: não é pedida, e o veredito é `OK 0 páginas`.
        """
        self.b.poe_no_trabalho("coleta.json", coleta_de_teste([u("mundo/manchete-do-feed")]))
        outra_forma = "http://www.gazeta-og.exemplo.invalid/mundo/manchete-do-feed/?utm_source=busca#topo"
        self.urls(outra_forma)
        self.poe(outra_forma, meta("2026-11-17T08:00:00Z"))
        self.poe(u("mundo/manchete-do-feed"), meta("2026-11-17T08:00:00Z"))
        res = self.confere()
        self.assertEqual(self.paginas(res), {})
        self.confere_veredito(res, "OK", 0)
        self.assertIn("0 páginas", res.ultima)

    def test_sem_urls_txt(self):
        """CONTRATO, seção 1.1, "Veredito e código": «Sem `urls.txt`, ou sem URL nova: `OK 0 páginas`, código 0»;
        seção 0: «`coleta.py` e `indicadores.py` sempre gravam o arquivo de saída, mesmo vazio.»

        Sem urls.txt na pasta de trabalho: OK, código 0, e conferencia.json gravado com a lista vazia.
        """
        res = self.confere()
        self.confere_veredito(res, "OK", 0)
        self.assertIn("0 páginas", res.ultima)
        conferencia = self.json_gravado(res, "conferencia.json")
        self.assertEqual(conferencia.get("paginas"), [])
        self.assertEqual(conferencia.get("versao"), 1)
        self.assertEqual(conferencia.get("gerada_em"), apoio.AGORA)

    def test_linha_em_branco_e_url_repetida_sao_ignoradas(self):
        """CONTRATO, seção 1.1, `urls.txt`: «linha em branco é ignorada […]; URL repetida (mesmo endereço limpo)
        conta uma vez».

        A mesma página três vezes (uma delas com âncora e utm_), com linhas em branco no meio: uma
        entrada só em conferencia.json, com a URL da primeira linha.
        """
        url = u("analise/pagina-aberta")
        self.urls("", url, "   ", url, url + "?utm_source=busca#topo", "")
        self.poe(url, meta("2026-11-20T08:15:00Z"))
        res = self.confere()
        self.assertEqual(list(self.paginas(res)), [url])
        self.confere_veredito(res, "OK", 0)

    def test_linha_com_cerquilha_e_comentario(self):
        """CONTRATO, seção 0, tabela da pasta de trabalho: `urls.txt` tem «uma URL por linha; linha com `#` é
        comentário».

        Duas linhas de comentário, uma delas com um endereço escrito depois do #. Só a URL de verdade é
        conferida; a do comentário, que tem resposta pronta, não aparece.
        """
        boa, comentada = u("analise/pagina-aberta"), u("analise/pagina-comentada")
        self.urls("# páginas abertas nesta execução", boa, "# " + comentada)
        self.poe(boa, meta("2026-11-20T08:15:00Z"))
        self.poe(comentada, meta("2026-11-20T08:15:00Z"))
        res = self.confere()
        self.assertEqual(list(self.paginas(res)), [boa])

    def test_linha_que_nao_e_url_do_esquema_e_pulada(self):
        """CONTRATO, seção 1.1, `urls.txt`: «Linha que não é URL (`ESQUEMA.md`, seção 0) é pulada, com aviso»;
        ESQUEMA, seção 0, "URL": sem aspas, apóstrofo, crase, cifrão, barra invertida nem usuário antes do site.

        Uma URL boa e seis que não são URL: nenhuma das seis é pedida nem vai para conferencia.json.
        """
        boa = u("analise/pagina-aberta")
        ruins = [u("analise/a'b"), u('analise/a"b'), u("analise/a`id`"), u("analise/$(id)"),
                 "https://golpe.exemplo.invalid\\@gazeta-og.exemplo.invalid/analise/x",
                 "https://alguem@gazeta-og.exemplo.invalid/analise/y"]
        self.urls(boa, *ruins)
        self.poe(boa, meta("2026-11-20T08:15:00Z"))
        for ruim in ruins:
            self.poe(ruim, meta("2026-11-20T08:15:00Z"))
        res = self.confere()
        self.assertEqual(list(self.paginas(res)), [boa])
        self.confere_veredito(res, "OK", 0)

    def test_urls_txt_so_com_comentario(self):
        """CONTRATO, seção 1.1, "Veredito e código": «sem URL nova: `OK 0 páginas`, código 0».

        urls.txt existe, mas só tem comentário.
        """
        self.urls("# nenhuma página aberta hoje")
        res = self.confere()
        self.confere_veredito(res, "OK", 0)
        self.assertEqual(self.paginas(res), {})

    def test_teto_de_30_paginas(self):
        """CONTRATO, seção 1.1: «Para cada URL de `urls.txt` que não está em `coleta.json` (até 30; 8 por vez; 8
        segundos cada), baixa a página».

        35 URLs novas, todas com resposta e com data. «As URLs além da 30ª ficam fora de `conferencia.json`,
        e a última linha diz quantas: `…; 5 URLs fora do teto de 30`.» As 30 que ficam são as primeiras de
        urls.txt, na ordem.
        """
        todas = [u("analise/pagina-%02d" % n) for n in range(35)]
        self.urls(*todas)
        for url in todas:
            self.poe(url, meta("2026-11-20T08:15:00Z"))
        res = self.confere()
        conferencia = self.json_gravado(res, "conferencia.json")
        self.assertEqual([p["url"] for p in conferencia["paginas"]], todas[:30])
        self.assertEqual({(p["estado"], p["publicado_em"]) for p in conferencia["paginas"]}, {("ok", "2026-11-20")})
        self.confere_veredito(res, "OK", 0)
        self.assertTrue(res.ultima.endswith("; 5 URLs fora do teto de 30"), res.ultima)

    def test_trinta_paginas_cabem(self):
        """CONTRATO, seção 1.1: «até 30». Com exatamente 30 URLs novas, as 30 são conferidas."""
        todas = [u("analise/pagina-%02d" % n) for n in range(30)]
        self.urls(*todas)
        for url in todas:
            self.poe(url, meta("2026-11-20T08:15:00Z"))
        res = self.confere()
        paginas = self.paginas(res)
        self.assertEqual(sorted(paginas), sorted(todas))
        self.assertEqual({(p["estado"], p["publicado_em"]) for p in paginas.values()}, {("ok", "2026-11-20")})


class FormatoEVeredito(CasoConfere):

    def cenario_pronto(self):
        """As 9 páginas da fixture offline/, uma de cada tipo."""
        self.b.usa_cenario("offline")
        self.esperado = {
            u("analise/brumal-com-meta"): ("ok", "2026-11-20"),
            u("analise/brumal-com-jsonld", "tribuna-so"): ("ok", "2026-11-19"),
            u("analise/brumal-com-os-dois", "agencia-er"): ("ok", "2026-11-18"),
            u("analise/sem-data", "mercado-ce"): ("ok", None),
            u("documentos/relatorio.pdf", "painel-og"): ("ok", None),
            u("analise/pagina-recusada", "folha-so"): ("bloqueada", None),
            u("analise/pagina-que-sumiu", "nuvem-bt"): ("erro", None),
            u("analise/endereco-antigo", "canal-ca"): ("ok", "2026-11-19"),
        }
        self.urls("# páginas abertas nesta execução", *self.esperado)
        return self.confere()

    def test_cenario_pronto_estado_e_data_de_cada_pagina(self):
        """CONTRATO, seção 1.1, tabela dos estados (`ok`, `bloqueada`, `erro`) e "Veredito e código": `OK 9
        páginas: 6 com data, 2 bloqueadas, 1 com erro`, código 0.

        Oito páginas da fixture: com meta (20/11), com JSON-LD (19/11), com os dois (vale o meta: 18/11),
        sem data, PDF, 403 (bloqueada), 404 (erro) e redirecionada (a data do destino, 19/11 às 09:30
        em +01:00). O veredito é OK, código 0, mesmo com uma bloqueada e uma com erro.
        """
        res = self.cenario_pronto()
        paginas = self.paginas(res)
        self.assertEqual({url: (p["estado"], p["publicado_em"]) for url, p in paginas.items()}, self.esperado)
        self.confere_veredito(res, "OK", 0)

    def test_formato_de_conferencia_json(self):
        """CONTRATO, seção 1.1: `{"versao": 1, "gerada_em": "…", "paginas": [{"url": "https://…", "estado": "ok",
        "publicado_em": "2026-11-20"}, …]}`; seção 0: «JSON gravado: UTF-8, sem BOM, acentos legíveis, recuo de 2
        espaços, quebra de linha no fim» e, no relógio de teste, «em todo `gerada_em`».

        versao 1, gerada_em igual ao relógio, e cada página com `url`, `estado` (ok, bloqueada ou erro)
        e `publicado_em` (data AAAA-MM-DD ou null).
        """
        res = self.cenario_pronto()
        self.confere_json_no_padrao(res, "conferencia.json")
        conferencia = self.json_gravado(res, "conferencia.json")
        self.assertEqual(conferencia.get("versao"), 1)
        self.assertEqual(conferencia.get("gerada_em"), apoio.AGORA)
        self.assertIsInstance(conferencia.get("paginas"), list)
        self.assertEqual(len(conferencia["paginas"]), 8)
        for p in conferencia["paginas"]:
            for chave in ("url", "estado", "publicado_em"):
                self.assertIn(chave, p)
            self.assertIn(p["estado"], ("ok", "bloqueada", "erro"))
            if p["publicado_em"] is not None:
                self.assertRegex(p["publicado_em"], r"^\d{4}-\d\d-\d\d$")

    def test_grava_so_conferencia_json(self):
        """CONTRATO, seção 1.1: «Grava: `P/conferencia.json`»; seção 6: `coleta.py --confere` grava na pasta de
        trabalho só `conferencia.json`.

        coleta.json e urls.txt ficam como estavam; não sobra arquivo temporário; mesa.txt não é criada.
        """
        res = self.cenario_pronto()
        self.assertEqual(res.gravados(), ["conferencia.json"], res.relato())
        self.assertEqual(sorted(res.arquivos), ["coleta.json", "conferencia.json", "urls.txt"])

    def test_nao_le_o_repositorio(self):
        """CONTRATO, seção 1.1: «Não lê nem altera o repositório.» (seção 6: «Lê do repositório: nada».)

        Com --raiz apontando para uma pasta vazia, sem dados/, o modo --confere funciona igual.
        """
        self.b.usa_cenario("offline")
        vazia = self.b.base / "raiz-vazia"
        vazia.mkdir()
        self.urls(u("analise/brumal-com-meta"))
        res = self.confere(raiz=vazia)
        self.confere_veredito(res, "OK", 0)
        self.assertEqual(self.paginas(res)[u("analise/brumal-com-meta")]["publicado_em"], "2026-11-20")
        self.assertEqual(list(vazia.iterdir()), [], "o modo --confere gravou na raiz")

    def test_nao_altera_o_repositorio(self):
        """CONTRATO, seção 1.1: «Não lê nem altera o repositório.»; seção 0: «Nenhuma ferramenta deixa arquivo a
        mais no repositório.»
        """
        antes = apoio._fotografa(self.b.raiz)
        self.cenario_pronto()
        self.assertEqual(apoio._fotografa(self.b.raiz), antes)

    def test_a_mesma_entrada_da_os_mesmos_bytes(self):
        """CONTRATO, seção 0: «Mesma entrada, mesmos bytes.»"""
        saidas = []
        for _ in range(2):
            self.nova()
            res = self.cenario_pronto()
            self.assertIn("conferencia.json", res.arquivos, res.relato())
            saidas.append(res.arquivos["conferencia.json"])
        self.assertEqual(saidas[0], saidas[1])

    def test_erro_de_uso(self):
        """CONTRATO, seção 0, "Erro de uso": «uma linha `FALHA uso: …` na saída padrão e código 2. Nada é gravado.»

        `--confere --tempo x`, com `--tempo` zero, negativo ou decimal (seção 1: «inteiro maior que zero»),
        e `--confere` com opção que não existe.
        """
        for args in (["--tempo", "x"], ["--tempo", "0"], ["--tempo", "-1"], ["--tempo", "2.5"], ["--opcao-que-nao-existe"]):
            with self.subTest(args=" ".join(args)):
                self.nova()
                self.urls(u("analise/pagina-aberta"))
                res = self.confere(*args)
                self.confere_veredito(res, "FALHA", 2)
                self.assertTrue(res.ultima.startswith("FALHA uso:"), res.ultima)
                self.assertEqual(res.gravados(), [])

    def test_cria_a_pasta_de_trabalho_se_faltar(self):
        """CONTRATO, seção 0, opção `--trabalho PASTA`: «é criada se faltar»; seção 1.1: «Sem `coleta.json`, ou
        com ele ilegível, toda URL de `urls.txt` conta como nova» e «Sem `urls.txt` […]: `OK 0 páginas`, código 0.»

        A pasta de trabalho ainda não existe, logo faltam os dois arquivos: a ferramenta cria a pasta,
        grava conferencia.json com a lista vazia e termina em OK.
        """
        pasta = self.b.base / "ainda" / "nao" / "existe"
        res = self.confere(trabalho=pasta)
        self.confere_veredito(res, "OK", 0)
        self.assertEqual(self.json_gravado(res, "conferencia.json").get("paginas"), [])

    def test_sem_coleta_json_toda_url_e_nova(self):
        """CONTRATO, seção 1.1: «Sem `coleta.json`, ou com ele ilegível, toda URL de `urls.txt` conta como nova
        (ilegível: com aviso).»"""
        url = u("analise/pagina-aberta")
        for nome, conteudo in (("sem coleta.json", None), ("coleta.json ilegível", "{quebrado")):
            with self.subTest(caso=nome):
                self.nova()
                if conteudo is None:
                    (self.b.trabalho / "coleta.json").unlink()
                else:
                    self.b.poe_no_trabalho("coleta.json", conteudo)
                self.urls(url)
                self.poe(url, meta("2026-11-20T08:15:00Z"))
                res = self.confere()
                self.assertEqual(self.paginas(res)[url]["publicado_em"], "2026-11-20")
                self.confere_veredito(res, "OK", 0)


if __name__ == "__main__":
    unittest.main()
