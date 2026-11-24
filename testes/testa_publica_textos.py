#!/usr/bin/env python3
"""Testes do que o publica.py escreve para o leitor (CONTRATO, seção 4.5): o feed.xml e o texto (.md).

Rode da raiz do repositório: python3 -B testes/testa_publica_textos.py
O feed é conferido com um leitor de XML e por texto, contra cada exigência do workflow de publicação.
O .md é conferido com texto hostil em todo campo: nada do que vem da edição pode virar marca nem link.
"""
import copy
import json
import os
import re
import sys
import unittest
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "publica"))
import apoio  # noqa: E402

DIA = apoio.DIA
AMANHA = apoio.soma(DIA, 1)
NS = apoio.NS
publica = apoio.publica
comum_dd_mm_aaaa = apoio.comum.dd_mm_aaaa
HOSTIL = ("%s [clique](https://exemplo.invalid/isca) ![imagem](isca) *negrito* _grifo_ `codigo` # titulo | coluna \\ "
          "<b>marca</b> <https://exemplo.invalid/angulo> https://exemplo.invalid/cru www.exemplo.invalid "
          "isca@exemplo.invalid")


def com_player(novo):
    novo["novos_players"] = [apoio.player_novo()]


def troca_textos(valor, funcao, caminho="", so_livres=True):
    """Troca cada texto da edição por funcao(caminho). Com `so_livres`, só os campos de texto livre (os que
    têm tamanho máximo no esquema); sem, toda folha de texto, inclusive ids, listas fechadas e endereços."""
    livres = set(chave for _, chave in apoio.valida.MAXIMOS) - set(["anula_vetor"])
    if isinstance(valor, dict):
        for chave, dentro in list(valor.items()):
            onde = "%s.%s" % (caminho, chave) if caminho else chave
            if isinstance(dentro, str) and (chave in livres or not so_livres):
                valor[chave] = funcao(onde)
            elif isinstance(dentro, list) and dentro and all(isinstance(d, str) for d in dentro) \
                    and (chave in livres or not so_livres):
                valor[chave] = [funcao("%s[%d]" % (onde, i)) for i in range(len(dentro))]
            else:
                troca_textos(dentro, funcao, onde, so_livres)
    elif isinstance(valor, list):
        for indice, dentro in enumerate(valor):
            troca_textos(dentro, funcao, "%s[%d]" % (caminho, indice), so_livres)


class TestaOFeed(apoio.Bancada):
    def feed(self):
        with open(self.caminho("feed.xml"), "rb") as arquivo:
            bruto = arquivo.read()
        return bruto, ET.fromstring(bruto)

    def exige_o_que_o_workflow_exige(self, bruto):
        """As conferências do workflow de publicação sobre o feed.xml, uma a uma (CONTRATO, seção 4.5)."""
        self.assertNotIn(b"\0", bruto)
        self.assertNotIn(b"<!DOCTYPE", bruto)
        self.assertNotIn(b"<!ENTITY", bruto)
        self.assertNotIn(b"<!", bruto, "nem comentário nem seção CDATA")
        self.assertEqual(bruto.count(b"<?"), 1, "nenhuma instrução além da declaração")
        self.assertTrue(bruto.startswith(b'<?xml version="1.0" encoding="utf-8"?>\n'), bruto[:60])
        raiz = ET.fromstring(bruto)  # bem formado
        self.assertEqual(raiz.tag, NS + "feed")
        self.assertEqual(sorted(set(e.tag for e in raiz.iter() if not e.tag.startswith(NS))), [], "só elementos do Atom")
        for elemento in raiz.iter():
            if elemento.tag in (NS + "title", NS + "summary", NS + "content"):
                self.assertIn(elemento.get("type"), (None, "text"), "texto puro, nunca html nem xhtml")
            for atributo in elemento.attrib:
                self.assertNotIn("{", atributo, "nenhum atributo de outro vocabulário")
        self.assertEqual(apoio.valida.confere_feed(bruto), [], "e a conferência do validador concorda")
        bruto.decode("utf-8")
        self.assertTrue(bruto.endswith(b"</feed>\n"))
        return raiz

    def test_o_feed_de_uma_edicao(self):
        self.publica_o_dia()
        bruto, raiz = self.feed()
        self.exige_o_que_o_workflow_exige(bruto)
        self.assertEqual([filho.tag[len(NS):] for filho in raiz], ["title", "id", "link", "link", "updated", "author", "entry"])
        self.assertEqual(raiz.findtext(NS + "title"), "INFOCENARIUM · monitor geopolítico e de IA")
        self.assertEqual(raiz.findtext(NS + "id"), apoio.BASE)
        self.assertEqual([(l.get("rel"), l.get("href")) for l in raiz.findall(NS + "link")],
                         [(None, apoio.BASE), ("self", apoio.BASE + "feed.xml")])
        self.assertEqual(raiz.findtext(NS + "updated"), apoio.agora(DIA))
        self.assertEqual(raiz.findtext(NS + "author/" + NS + "name"), "INFOCENARIUM")
        entrada = raiz.find(NS + "entry")
        edicao = self.le("edicoes/%s.json" % DIA)
        self.assertEqual([filho.tag[len(NS):] for filho in entrada], ["title", "id", "link", "updated", "summary", "content"])
        self.assertEqual(entrada.findtext(NS + "title"), "INFOCENARIUM 20/11/2026 · nível 3 TENSÃO")
        endereco = apoio.BASE + "#/edicao/" + DIA
        self.assertEqual((entrada.findtext(NS + "id"), entrada.find(NS + "link").get("href")), (endereco, endereco))
        self.assertEqual(entrada.findtext(NS + "updated"), edicao["gerada_em"])
        self.assertEqual(entrada.findtext(NS + "summary"), edicao["resumo"])
        self.assertEqual(entrada.findtext(NS + "content"),
                         "\n\n".join("%d. %s\n%s" % (n, p["titulo"], p["fato"]) for n, p in enumerate(edicao["principais"], 1)))
        self.assertEqual((entrada.find(NS + "summary").get("type"), entrada.find(NS + "content").get("type")), ("text", "text"))

    def monta_arquivo_grande(self):
        """34 edições gravadas direto em edicoes/: 32 comuns, uma falha e a de exemplo. O refaz não as confere."""
        self.publica_o_dia()
        molde = self.le("edicoes/%s.json" % DIA)
        os.unlink(self.caminho("edicoes", "%s.json" % DIA))
        datas = [apoio.soma("2026-10-01", n) for n in range(32)]
        for data in datas:
            copia = copy.deepcopy(molde)
            copia.update(data=data, gerada_em=apoio.agora(data), resumo="Resumo fictício de %s." % data)
            self.grava("edicoes/%s.json" % data, copia)
        falha = copy.deepcopy(molde)
        falha.update(data="2026-11-02", gerada_em="2026-11-02T21:00:00Z", estado="falha", principais=[], radar=[],
                     resumo="Sem edição hoje. Motivo fictício.")
        self.grava("edicoes/2026-11-02.json", falha)
        exemplo = apoio.exemplo()
        exemplo.update(data="2026-11-03", gerada_em="2026-11-04T01:00:00Z")
        self.grava("edicoes/2026-11-03.json", exemplo)
        return datas

    def test_as_trinta_mais_novas_sem_a_de_exemplo(self):
        datas = self.monta_arquivo_grande()
        linhas = self.assertOK(self.publica("refaz"))
        self.assertEqual(linhas[-1], "OK refeitos o índice (34 edições), 34 textos e o feed (30 entradas)")
        bruto, raiz = self.feed()
        self.exige_o_que_o_workflow_exige(bruto)
        entradas = raiz.findall(NS + "entry")
        esperadas = (["2026-11-02"] + sorted(datas, reverse=True))[:30]
        self.assertEqual([e.findtext(NS + "id") for e in entradas], [apoio.BASE + "#/edicao/" + d for d in esperadas])
        self.assertEqual(entradas[0].findtext(NS + "title"), "INFOCENARIUM 02/11/2026 · sem edição")
        self.assertEqual(entradas[0].findtext(NS + "content"), "Sem edição hoje. Motivo fictício.",
                         "sem principal, o conteúdo da entrada é o resumo")
        self.assertEqual(entradas[1].findtext(NS + "title"), "INFOCENARIUM 01/11/2026 · nível 3 TENSÃO")
        self.assertEqual(raiz.findtext(NS + "updated"), "2026-11-02T21:00:00Z",
                         "o maior gerada_em das edições do feed; a de exemplo, mais nova, não conta")
        self.assertNotIn(b"2026-11-03", bruto)
        self.assertNotIn(b"EXEMPLO", bruto)
        indice = self.le("edicoes/indice.json")
        self.assertEqual(len(indice["edicoes"]), 34)
        self.assertEqual(indice["atualizado_em"], "2026-11-04T01:00:00Z")
        self.assertEqual([e["data"] for e in indice["edicoes"]][:3], ["2026-11-03", "2026-11-02", "2026-11-01"])

    def test_texto_hostil_nao_muda_a_forma_do_feed(self):
        self.publica_o_dia()
        hostil = ('</summary><script xmlns="http://www.w3.org/1999/xhtml">alert(1)</script> ]]> &amp; &lt; '
                  '<?xml-stylesheet href="isca.xsl"?> <!DOCTYPE x [<!ENTITY a "b">]> "aspas" \'apóstrofos\' '
                  + chr(0) + chr(11) + chr(0x85) + chr(0xFFFE) + chr(0xD83D) + " fim")

        def envenena(edicao):
            edicao["resumo"] = hostil
            edicao["principais"][0]["titulo"] = hostil
            edicao["principais"][1]["fato"] = "linha um\nlinha dois\r\n" + hostil
            edicao["alerta"]["nivel"] = "<nivel>"
        edicao = self.le("edicoes/%s.json" % DIA)
        envenena(edicao)
        apoio.grava(self.caminho("edicoes", "%s.json" % DIA), json.dumps(edicao))  # com os códigos \u dentro
        self.assertOK(self.publica("refaz"))
        bruto, raiz = self.feed()
        self.exige_o_que_o_workflow_exige(bruto)
        self.assertEqual(len(raiz.findall(NS + "entry")), 1)
        entrada = raiz.find(NS + "entry")
        limpo = " ".join(re.sub("[%s]" % (chr(0) + chr(11) + chr(0x85) + chr(0xFFFE) + chr(0xD83D)), " ", hostil).split())
        self.assertEqual(entrada.findtext(NS + "summary"), limpo, "o texto chega inteiro ao leitor, como texto")
        self.assertIn("1. " + limpo, entrada.findtext(NS + "content"))
        self.assertIn("linha um linha dois " + limpo, entrada.findtext(NS + "content"))
        self.assertEqual(entrada.findtext(NS + "title"), "INFOCENARIUM 20/11/2026 · nível <nivel>")
        self.assertNotIn(b"<script", bruto)
        self.assertIn(b"&lt;script", bruto)
        self.assertIn(b"]]&gt;", bruto)
        self.assertIn(b"&amp;amp;", bruto)

    # ------------------------------------------------------------ endereço base, na ordem da seção 4.5

    def ids(self):
        _, raiz = self.feed()
        return raiz.findtext(NS + "id"), [e.findtext(NS + "id") for e in raiz.findall(NS + "entry")]

    def test_ordem_do_endereco_base(self):
        self.inicia_git()
        self.git("remote", "add", "origin", "https://github.com/dono-ficticio/INFOCENARIUM.git")
        # 4º: sem --url-base, sem feed e com remoto que não serve, vale ./
        self.git("remote", "set-url", "origin", os.path.join(self.pasta, "remoto.git"))
        self.prepara()
        linhas = self.assertOK(self.publica("edicao"))
        self.assertEqual(self.ids(), ("./", ["./#/edicao/" + DIA]))
        self.assertTrue(any(linha.startswith("endereço base do feed: ./ (o padrão; ") and "--url-base" in linha
                            for linha in linhas))
        # 2º: o que já está no feed.xml vale mais que o remoto do git, mesmo sendo ./
        self.git("remote", "set-url", "origin", "https://github.com/dono-ficticio/INFOCENARIUM.git")
        linhas = self.assertOK(self.publica("refaz"))
        self.assertEqual(self.ids()[0], "./")
        # relativo vale, mas a linha diz como pôr o endereço do site (o Atom pede id absoluto)
        self.assertIn("endereço base do feed: ./ (o do feed.xml que já existe; relativo: para o feed levar o "
                      "endereço do site, use --url-base)", linhas)
        # 3º: sem feed, o endereço sai do remoto origin
        os.unlink(self.caminho("feed.xml"))
        linhas = self.assertOK(self.publica("refaz"))
        self.assertEqual(self.ids(), ("https://dono-ficticio.github.io/INFOCENARIUM/",
                                      ["https://dono-ficticio.github.io/INFOCENARIUM/#/edicao/" + DIA]))
        self.assertIn("endereço base do feed: https://dono-ficticio.github.io/INFOCENARIUM/ (tirado do remoto origin do git)", linhas)
        # 1º: --url-base vale mais que tudo, e fica gravado para as próximas vezes
        linhas = self.assertOK(self.publica("refaz", "--url-base", "https://exemplo.invalid/INFOCENARIUM"))
        self.assertEqual(self.ids()[0], apoio.BASE, "a barra do fim entra sozinha")
        self.assertIn("endereço base do feed: %s (--url-base)" % apoio.BASE, linhas)
        self.assertOK(self.publica("edicao"))
        self.assertEqual(self.ids(), (apoio.BASE, [apoio.BASE + "#/edicao/" + DIA]))
        self.publica_a_falha(AMANHA)
        self.assertEqual(self.ids()[1], [apoio.BASE + "#/edicao/" + AMANHA, apoio.BASE + "#/edicao/" + DIA])

    def test_feed_que_nao_serve_nao_empresta_o_endereco(self):
        self.publica_o_dia()
        for ruim in ('<?xml version="1.0"?>\n<!DOCTYPE feed [<!ENTITY base "https://isca.invalid/">]>\n'
                     '<feed xmlns="http://www.w3.org/2005/Atom"><id>&base;</id></feed>',
                     '<feed xmlns="http://www.w3.org/2005/Atom"><id>javascript:alert(1)</id></feed>',
                     '<feed xmlns="http://www.w3.org/2005/Atom"><id>https://isca.invalid/a b</id></feed>',
                     '<rss><channel><link>https://isca.invalid/</link></channel></rss>', "não é XML", ""):
            self.grava("feed.xml", ruim)
            self.assertOK(self.publica("refaz"))
            self.assertEqual(self.ids()[0], "./", ruim)
            self.assertNotIn("isca", self.texto("feed.xml"))

    def test_remoto_do_git_vira_endereco_do_site(self):
        certo = "https://dono-ficticio.github.io/INFOCENARIUM/"
        for remoto, esperado in (
                ("https://github.com/dono-ficticio/INFOCENARIUM.git", certo), ("https://github.com/dono-ficticio/INFOCENARIUM", certo),
                ("https://github.com/dono-ficticio/INFOCENARIUM/", certo), ("git@github.com:dono-ficticio/INFOCENARIUM.git", certo),
                ("ssh://git@github.com/dono-ficticio/INFOCENARIUM.git", certo),
                ("http://local_proxy@127.0.0.1:18080/git/dono-ficticio/INFOCENARIUM", certo),
                ("https://github.com/Dono/Outro.Repo.git", "https://Dono.github.io/Outro.Repo/"),
                ("/tmp/qualquer/remoto.git", None), ("../remoto.git", None), ("file:///tmp/dono/INFOCENARIUM.git", None),
                ("https://github.com/INFOCENARIUM", None), ("https://github.com/dono ficticio/INFOCENARIUM", None),
                ("https://github.com/-dono/INFOCENARIUM", None), ("", None), (None, None)):
            self.assertEqual(publica.base_do_remoto(remoto), esperado, remoto)

    def test_o_que_vale_como_endereco_base(self):
        for texto, esperado in (("https://exemplo.invalid/INFOCENARIUM/", "https://exemplo.invalid/INFOCENARIUM/"),
                                ("https://exemplo.invalid/INFOCENARIUM", "https://exemplo.invalid/INFOCENARIUM/"),
                                ("http://exemplo.invalid", "http://exemplo.invalid/"), ("./", "./"), (".", "./"),
                                ("/INFOCENARIUM/", "/INFOCENARIUM/"), ("javascript:alert(1)", None), ("data:text/html,x", None),
                                ("https://exemplo.invalid/a b/", None), ("https://exemplo.invalid/#/a", None),
                                ("https://exemplo.invalid/?a=1", None), ('./"onclick="x', None), ("./<b>", None),
                                ("", None), ("   ", None), ("https://" + "a" * 500, None), (None, None), (7, None)):
            self.assertEqual(publica.base_valida(texto), esperado, texto)


class TestaOEscape(unittest.TestCase):
    """A função md(): todo campo de texto passa por ela (CONTRATO, seção 4.5)."""

    def test_os_dez_sinais_do_contrato_levam_barra(self):
        for sinal in "\\[]()*_`#|":
            self.assertEqual(publica.md("a %s b" % sinal), "a \\%s b" % sinal)
        self.assertEqual(publica.md("[clique](https://exemplo.invalid) *a* _b_ `c` # d | e \\"),
                         "\\[clique\\]\\(https\\://exemplo.invalid\\) \\*a\\* \\_b\\_ \\`c\\` \\# d \\| e \\\\")

    def test_texto_comum_nao_muda(self):
        for texto in ("O petróleo Brent subiu 6,1% em 7 dias, até 20/11.", "Dólar a R$ 5,43: alta de 0,4%.",
                      "Segundo o governo, \"não houve mortos\".", "A meta cai em 01/12? Não se sabe; depende do voto.",
                      "IA & chips: contrato de US$ 2 bilhões", "até 12/11", "3 fontes", "20/11", "2026",
                      "3.000 barris por dia", "1.5", "2026.11"):
            self.assertEqual(publica.md(texto), texto)

    def test_o_que_ainda_viraria_marca_ou_link(self):
        self.assertEqual(publica.md("<b>x</b>"), "\\<b>x\\</b>")
        self.assertEqual(publica.md("ver <https://exemplo.invalid>"), "ver \\<https\\://exemplo.invalid>")
        self.assertEqual(publica.md("ver https://exemplo.invalid/a e WWW.exemplo.invalid"),
                         "ver https\\://exemplo.invalid/a e WWW\\.exemplo.invalid")
        self.assertEqual(publica.md("fale com a@exemplo.invalid"), "fale com a\\@exemplo.invalid")
        self.assertEqual(publica.md("![imagem](x)"), "!\\[imagem\\]\\(x\\)")

    def test_comeco_de_linha_que_abriria_bloco(self):
        for texto, esperado in (("- item", "\\- item"), ("+ item", "\\+ item"), ("> citação", "\\> citação"),
                                ("=== título", "\\=== título"), ("~~~ código", "\\~~~ código"), ("1. um", "1\\. um"),
                                ("12. doze", "12\\. doze"), ("1.", "1\\."), ("3.000 barris", "3.000 barris"),
                                ("# título", "\\# título"), ("    recuado", "recuado"),
                                ("-5% no dia", "\\-5% no dia"), ("1,5% no dia", "1,5% no dia")):
            self.assertEqual(publica.md(texto), esperado)

    def test_fica_tudo_numa_linha_e_nada_derruba(self):
        self.assertEqual(publica.md("linha um\nlinha dois\r\n\tlinha três" + chr(0x2028) + "quatro" + chr(0) + "cinco"),
                         "linha um linha dois linha três quatro cinco")
        self.assertEqual(publica.md("a" + chr(0xD83D) + "b"), "a b")
        for valor, esperado in ((None, ""), (True, "true"), (7, "7"), (1.5, "1.5"), (["a", "*"], '\\["a", "\\*"\\]'),
                                ({"a": 1}, '{"a"\\: 1}' if False else '{"a": 1}')):
            self.assertEqual(publica.md(valor), esperado)

    def test_codigo_e_endereco(self):
        self.assertEqual(publica.cod("usd_brl"), "`usd_brl`")
        self.assertEqual(publica.cod("2026-11-17_p3_ue"), "`2026-11-17_p3_ue`")
        self.assertEqual(publica.cod("energia.3"), "`energia.3`")
        self.assertEqual(publica.cod("a`b"), "a\\`b", "o que não tem forma de id sai como texto, com escape")
        self.assertEqual(publica.cod("[x](y)"), "\\[x\\]\\(y\\)")
        self.assertEqual(publica.cod(None), "")
        self.assertEqual(publica.md_url("https://exemplo.invalid/a_(b)*c"), "<https://exemplo.invalid/a_(b)*c>")
        self.assertEqual(publica.md_url("https://exemplo.invalid/a<b>c"), "<https://exemplo.invalid/a%3Cb%3Ec>")
        for ruim in ("javascript:alert(1)", "https://exemplo.invalid/a b", "nada", "", None, 7,
                     "https://exemplo.invalid/" + chr(0) + "x", "ftp://exemplo.invalid/x"):
            self.assertTrue(publica.md_url(ruim).endswith(" (endereço inválido)"), ruim)
            self.assertNotIn("<", publica.md_url(ruim).replace("\\<", ""))


class TestaOTexto(apoio.Bancada):
    """edicoes/DIA.md (CONTRATO, seção 4.5)."""

    CABECALHOS = re.compile(r"^(# INFOCENARIUM · |## (Domínios|Indicadores|Principais|Radar|Placar do dia|Respostas|Players novos"
                            r"|Errata|Bastidores)$|### )")

    def refaz_com(self, edicao, data=apoio.DIA_DO_EXEMPLO):
        """Grava a edição direto em edicoes/ (o refaz não confere regra) e devolve o texto que o refaz gera."""
        apoio.grava(self.caminho("edicoes", "%s.json" % data), json.dumps(edicao))
        self.assertOK(self.publica("refaz"))
        texto = self.texto("edicoes/%s.md" % data)
        self.assertTrue(texto.endswith("\n") and not texto.endswith("\n\n"))
        return texto

    def sem_marcas(self, texto):
        """O texto sem o que a ferramenta põe de propósito: sobra o que veio da edição, que tem de estar com barra."""
        linhas = []
        for linha in texto.splitlines():
            linha = re.sub(r"<https?://[^<>\s]+>", "", linha)  # os campos url
            linha = re.sub(r"`[A-Za-z0-9][A-Za-z0-9_./-]*`", "", linha)  # ids e códigos
            linha = re.sub(r"^#{1,3} ", "", linha)  # títulos
            linha = re.sub(r"^ *- ", "", linha)  # itens de lista
            linha = re.sub(r"\*\*[^*\\]+\*\*", "", linha)  # rótulos em negrito, que a ferramenta escreve
            # o nome do player novo, em negrito: "- **Nome** (`id`)". O "- " já saiu duas linhas acima.
            linha = re.sub(r"^\*\*(.*?)\*\* \(", r"\1 (", linha)
            # a linha do nível geral, toda em negrito ("**Nível 3 · TENSÃO · estável**"): sobra o miolo, conferido
            linha = re.sub(r"^\*\*(.*)\*\*$", r"\1", linha)
            linhas.append(linha)
        return "\n".join(linhas)

    def test_texto_hostil_em_todo_campo_de_texto(self):
        """Cada campo de texto livre da edição de exemplo vira isca. No .md, toda isca sai com barra."""
        edicao = apoio.exemplo()
        iscas = {}

        def isca(caminho):
            iscas[caminho] = HOSTIL % caminho
            return iscas[caminho]
        troca_textos(edicao, isca)
        self.assertGreater(len(iscas), 150)
        for obrigatorio in ("resumo", "alerta.motivo", "alerta.dominios[0].leitura", "alerta.dominios[0].gatilhos[0].texto",
                            "indicadores[0].nome", "indicadores[0].fonte.nome", "principais[0].titulo",
                            "principais[0].nao_confirmado[0]", "principais[0].ataques[0].enquadramento",
                            "principais[0].ataques[0].omite", "principais[0].ataques[2].alvo_nome",
                            "principais[0].realmente", "principais[0].na_pratica[0]", "principais[0].no_brasil",
                            "principais[0].eixo.porque", "principais[0].placar[0].porque", "principais[0].vetores[0].porque",
                            "principais[0].vigiar[0]", "principais[0].fontes[5].nome", "principais[0].fontes[0].titulo",
                            "radar[0].sem_placar", "radar[0].ataque.enquadramento", "placar_do_dia[0].frase",
                            "novos_players[0].nome", "novos_players[0].nota", "novos_players[0].justificativa",
                            "errata[0].erro", "errata[0].correcao", "respostas[0].pergunta", "respostas[0].texto",
                            "bastidores.limites", "bastidores.candidatos[0].nome", "bastidores.candidatos[0].motivo",
                            "bastidores.veiculos_sugeridos[0]"):
            self.assertIn(obrigatorio, iscas)
        texto = self.refaz_com(edicao)
        # Indicador sem valor sai como "sem dado", sem a unidade: não há número a que ela se refira.
        sem_valor = set("indicadores[%d].unidade" % i for i, medido in enumerate(edicao["indicadores"])
                        if medido["valor"] is None)
        self.assertEqual(sem_valor, set(["indicadores[2].unidade"]))
        for caminho, hostil in iscas.items():
            self.assertNotIn(hostil, texto, caminho)
            if caminho in sem_valor:
                self.assertNotIn(publica.md(hostil), texto, caminho)
                continue
            self.assertIn(publica.md(hostil), texto, "o campo %s não saiu, ou saiu sem escape" % caminho)
        # nada do que veio da edição ficou com sinal de Markdown solto
        resto = self.sem_marcas(texto)
        for sinal in ("[", "]", "(", ")", "*", "_", "`", "#", "|", "<"):
            soltos = re.findall(r"(?<!\\)(?:\\\\)*%s" % re.escape(sinal), resto)
            if sinal in "()":  # os parênteses que a ferramenta escreve: "(fora do mapa)", "(discutível)", "(hora de …)"
                continue
            self.assertEqual(soltos, [], "sinal %r sem barra no texto" % sinal)
        for proibido in ("](", "![", "<https://exemplo.invalid/angulo>", " https://", " www.exemplo", "isca@"):
            self.assertNotIn(proibido, texto)
        # A marca de HTML sai com barra antes do <, e assim é texto: "\<b>" é lido como "<b>" escrito, e não como marca.
        self.assertIn("\\<b>marca\\</b>", texto)
        self.assertEqual(re.findall(r"(?<!\\)</?b>", texto), [], "marca de HTML sem a barra")
        for linha in texto.splitlines():
            if linha.startswith("#"):
                self.assertRegex(linha, self.CABECALHOS)
        # Um título só, o da data: a edição de exemplo abre com a linha de exemplo, e o título vem logo depois.
        self.assertEqual([linha for linha in texto.splitlines() if linha.startswith("# ")], ["# INFOCENARIUM · 19/11/2026"])
        self.assertTrue(texto.startswith("EDIÇÃO DE EXEMPLO · dados fictícios\n\n# INFOCENARIUM · 19/11/2026\n"))

    def test_so_campo_url_vira_endereco(self):
        edicao = apoio.exemplo()
        texto = self.refaz_com(edicao)
        no_texto = re.findall(r"<(https?://[^<>\s]+)>", texto)
        da_edicao = [url for url in apoio.urls_do_agente(edicao)] + [i["fonte"]["url"] for i in edicao["indicadores"]]
        self.assertEqual(set(no_texto), set(da_edicao), "todo endereço da edição aparece por extenso, e só eles")
        self.assertEqual(len(re.findall(r"https?://", texto)), len(no_texto), "nenhum endereço fora de < >")
        self.assertNotIn("](", texto)

    def test_texto_hostil_em_toda_folha_inclusive_ids_e_enderecos(self):
        """Edição que não passou pelo validador: ids, listas fechadas e endereços também viram isca."""
        edicao = apoio.exemplo()
        iscas = []

        def isca(caminho):
            iscas.append(HOSTIL % caminho)
            return iscas[-1]
        troca_textos(edicao, isca, so_livres=False)
        edicao["alerta"]["nivel"] = "[5](https://exemplo.invalid/nivel)"
        edicao["indicadores"][0]["valor"] = "*caro*"
        edicao["principais"][0]["placar"][0]["forca"] = "<b>3</b>"
        texto = self.refaz_com(edicao, data="2026-11-18")
        for proibido in ("](", "<https://", " https://", " www.exemplo", "isca@"):
            self.assertNotIn(proibido, texto)
        self.assertEqual(re.findall(r"(?<!\\)</?b>", texto), [], "marca de HTML sem a barra")
        resto = self.sem_marcas(texto)
        for sinal in ("[", "]", "*", "_", "`", "#", "|", "<"):
            self.assertEqual(re.findall(r"(?<!\\)(?:\\\\)*%s" % re.escape(sinal), resto), [], sinal)
        self.assertGreater(texto.count("(endereço inválido)"), 40, "endereço que não serve sai como texto")
        self.assertIn("\\[5\\]\\(https\\://exemplo.invalid/nivel\\)", texto)
        self.assertGreater(sum(1 for hostil in iscas if publica.md(hostil) in texto), 300)
        # e o feed da mesma edição continua dentro do que o workflow aceita
        with open(self.caminho("feed.xml"), "rb") as arquivo:
            self.assertEqual(apoio.valida.confere_feed(arquivo.read()), [])

    def test_edicao_torta_nao_derruba_o_texto(self):
        for torta in ({}, {"data": 5, "alerta": [], "principais": "x", "radar": [None, 3, {"id": []}], "bastidores": []},
                      {"data": "2026-11-18", "estado": ["x"], "gerada_em": 3, "alerta": {"nivel": [], "tendencia": {},
                       "dominios": [None, {"id": {}, "nivel": "x", "sem_preco": [[], {}], "gatilhos": [None, {"ref": []}]}]},
                       "indicadores": [None, {"valor": [], "fonte": []}],
                       "principais": [{"id": [], "ataques": [None, {"alvo": [], "veiculo": {}},
                                                             {"veiculo": "nyt", "lado": [], "omite": 3}],
                                       "conflito_de_interesse": True, "eixo": {"tema": []},
                                       "placar": [{"forca": [], "partido": {}}], "vetores": [{"player": []}],
                                       "dominios": [[], {}], "fontes": [{"veiculo": []}, {"veiculo": "nyt"}],
                                       "continuacao_de": 7,
                                       "nao_confirmado": [None], "na_pratica": [[]], "vigiar": [{}]}],
                       "placar_do_dia": [{"partido": []}], "novos_players": [{"dna": {"x": []}, "dna_fontes": {"y": 3},
                                                                              "duvidas": [[]]}],
                       "errata": [{"edicao": [], "item": {}}], "respostas": [{"edicao": 3, "resposta": []}],
                       "bastidores": {"candidatos": [{"id": []}], "veiculos_sugeridos": [3, None, {}]}}):
            texto = self.refaz_com(torta, data="2026-11-18")
            self.assertTrue(texto.startswith("# INFOCENARIUM · "))
            self.assertNotIn("](", texto)

    def publicada(self, muda=com_player):
        self.publica_o_dia(muda=muda)
        return self.le("edicoes/%s.json" % DIA), self.texto("edicoes/%s.md" % DIA)

    def blocos_dos_itens(self, texto):
        """{id do item: o trecho do .md desse item}."""
        blocos = {}
        for pedaco in re.split(r"\n(?=### (?:p|r)[0-9]+ · )", texto)[1:]:
            blocos[pedaco.split(" ", 2)[1]] = pedaco.split("\n## ")[0]
        return blocos

    def test_aviso_de_conflito_de_interesse(self):
        edicao, texto = self.publicada()
        blocos = self.blocos_dos_itens(texto)
        self.assertEqual(sorted(blocos), ["p1", "p2", "p3", "r1", "r2", "r3", "r4", "r5", "r6"])
        aviso = ("Aviso: o INFOCENARIUM é escrito por um modelo de IA da Anthropic, que é do setor de IA e pode ser parte ou "
                 "concorrente nesta notícia.")
        for item in apoio.itens(edicao):
            linhas = blocos[item["id"]].splitlines()
            tem = aviso in linhas
            self.assertEqual(tem, item.get("conflito_de_interesse") is True, item["id"])
            if tem:
                # o teto da confiança, numa linha à parte, como no site (ESPEC-SITE, seção 8.3)
                self.assertEqual(linhas[linhas.index(aviso) + 1], "Por isso a confiança deste item não passa de média.")
        self.assertEqual(texto.count(aviso), 4)
        self.assertEqual(sorted(i for i, b in blocos.items() if aviso in b), ["p2", "r1", "r2", "r3"])

    def test_fonte_fora_do_mapa_e_fonte_do_mapa(self):
        edicao, texto = self.publicada()
        linhas = texto.splitlines()
        # O título vem da edição publicada (o exemplo muda de texto; a forma da linha é o que se confere).
        primaria = next(f for f in edicao["principais"][0]["fontes"] if f["veiculo"] == "outro")
        self.assertEqual(primaria["nome"], "Diário Oficial da República de Exemplo (fictício)")
        self.assertIn("- Diário Oficial da República de Exemplo \\(fictício\\) (fora do mapa) · %s · %s · fonte primária · "
                      "<https://diario.oficial.exemplo.invalid/decreto-1-2026>"
                      % (publica.md(primaria["titulo"]), comum_dd_mm_aaaa(primaria["publicado_em"])), linhas)
        self.assertIn("- Reuters · Centrão · Sample Kingdom oil terminal halts loading after drone strike · 20/11/2026 · "
                      "<%s>" % apoio.no_site_do_veiculo("https://exemplo.invalid/reuters/terminal-para"), linhas)
        fora = [linha for linha in linhas if "(fora do mapa)" in linha]
        self.assertEqual(len(fora), sum(1 for item in apoio.itens(edicao) for f in item["fontes"] if f["veiculo"] == "outro"))

    def test_a_ordem_do_texto_e_a_do_contrato(self):
        edicao, texto = self.publicada()
        marcos = ["# INFOCENARIUM · 20/11/2026", "Edição completa · gerada em 20/11/2026 às 18h14 (hora de Brasília)",
                  "**Nível 3 · TENSÃO**\n", "Primeira edição: sem comparação.", publica.md(edicao["resumo"]),
                  "**Motivo do nível:** ", "## Domínios", "### Energia · nível 3\n", "Neste nível desde 20/11/2026.",
                  "**Gatilhos de hoje:**", "- `energia.2` · ", " · ver indicador: Petróleo Brent\n",
                  "- `energia.3` · ", " · ver principal 1\n",
                  "**Leitura:** ", "**Vigiar:** ", "### Alimentos · nível 1 · sem dado de preço de: Milho\n",
                  "Nenhum gatilho hoje.", "### Cadeias de suprimento · nível 2\n", " · EXCEÇÃO",
                  "## Indicadores", "- Petróleo Brent: 78,4 US$ por barril · no dia +1,3% · em 7 dias +6,1% · cotação de "
                  "20/11/2026 · fonte: ", "- Gás natural nos EUA: sem dado · fonte prevista: ",
                  "cotação de 13/11/2026 (defasada)", "## Principais",
                  "\n\nMapa de veículos em rascunho, ainda sem revisão do dono.\n\n### p1 · ", "Geopolítica · confiança alta · domínios: Energia, Risco de conflito",
                  "**O que aconteceu:** ", "**Não confirmado:**", "- Segundo ", "**Quem atirou:**",
                  "- The New York Times · Partido da Ordem Global · alvo: ", " · Deixou de fora: ",
                  " Segundo a leitura do INFOCENARIUM em 20/11. · <",
                  "**O que está realmente acontecendo:** ", "**Na prática:**", "**No Brasil:** ",
                  "**O ato na régua:** Mudanças climáticas · empurra para: ", "**Quem ganha e quem perde:**",
                  "- Eixo Revisionista: ganha · força 2 (ato reversível) · preço · ", "**Vetores de mudança:**",
                  "- União Europeia (Centro Atlântico) → Soberanistas · força 2 · tema: Mudanças climáticas · ",
                  " · prova: <%s>" % apoio.no_site_do_veiculo("https://exemplo.invalid/comissao_europeia/"
                                                              "decreto-suspende-meta"), "**Vigiar:**",
                  "**Fontes:**", "### p2 · ", "IA · confiança média", "### p3 · ", "## Radar",
                  "\n\nMapa de veículos em rascunho, ainda sem revisão do dono.\n\n### r1 · ",
                  "**Sem placar:** ", "### r6 · ", "## Placar do dia", "- Partido da Ordem Global: saldo +4 · narrativa +1 · ",
                  "- Centrão: saldo -1 · Texto", "## Players novos",
                  "- **República de Exemplo** (`republica_exemplo`) · tipo: Governos e políticos · partido: Independentes · "
                  "time: Mudança da ordem (discutível)", "  - DNA: ", "  - Fontes das posições: ", "  - Posições em dúvida: ",
                  "  - Quem é: ", "  - Por que entrou: ", "  - Fonte: <https://", "## Bastidores",
                  "- Modo: coleta normal, pelos feeds dos veículos", "- Veículos consultados: 19 · feeds lidos: 61 · feeds "
                  "que falharam: 7 · páginas lidas: 11 · buscas: 4 · minutos de trabalho: 24 · ",
                  "- O que não deu para conferir: ", "- Ator sem ficha na régua: ", "- Veículo que fez falta: "]
        posicao = 0
        for marco in marcos:
            achado = texto.find(marco, posicao)
            self.assertNotEqual(achado, -1, "faltou, ou veio fora de ordem: %r" % marco)
            posicao = achado + len(marco)
        self.assertNotIn("EDIÇÃO DE EXEMPLO", texto)
        self.assertNotIn("## Respostas", texto, "seção sem item não aparece")
        self.assertNotIn("## Errata", texto)

    def test_respostas_errata_e_continuacao(self):
        texto = self.refaz_com(apoio.exemplo())
        linhas = texto.splitlines()
        self.assertIn("## Respostas", linhas)
        self.assertIn("- Pergunta de 12/11/2026, principal 1: O Reino de Amostra renova as sanções fictícias até 19/11? · "
                      "Resposta: SIM · Texto fictício. O Reino de Amostra renovou as sanções em 18/11, por mais 6 meses. · "
                      "fonte: <https://exemplo.invalid/reuters/sancoes-renovadas>", linhas)
        self.assertTrue(any(linha.startswith("- Pergunta de 16/11/2026, principal 3: ") and "Resposta: SEM DADO" in linha
                            and "fonte:" not in linha for linha in linhas))
        self.assertIn("## Errata", linhas)
        self.assertTrue(any(linha.startswith("- Edição de 17/11/2026, item `p3` · Estava errado: ")
                            and linha.endswith(" · anula o vetor `2026-11-17_p3_ue`") for linha in linhas))
        self.assertIn("Continuação de 18/11/2026, item `p2`.", linhas)
        self.assertIn("Primeira edição: sem comparação.", linhas)
        self.assertIn("### Câmbio · nível 2", linhas, "primeira edição: o estável não houve como medir")
        self.assertIn("**Nível 3 · TENSÃO · subindo**", linhas, "tendência que não é estável foi medida: fica")
        self.assertIn("Mantido desde 17/11. Sem gatilho novo. O nível desce um degrau depois de 2 edições seguidas sem "
                      "gatilho. Edição sem dado de preço não entra nessa conta.", linhas)
        # O nome do veículo vem do mapa congelado ("The Wall Street Journal"), e não do texto do teste.
        wsj = "- %s · Centrão · sem alvo · " % apoio.dados().mapa["wsj"]["nome"]
        self.assertTrue(any(linha.startswith(wsj) for linha in linhas), wsj)

    def test_gatilho_diz_para_onde_a_prova_leva(self):
        """Como o site (ESPEC-SITE, seção 8.3): "ver principal 1", "ver radar 4", "ver indicador: Nome"; o `ref` que
        não é desta edição sai pelo id. Nenhum "item `p1`" no texto."""
        exemplo = apoio.exemplo()
        energia = exemplo["alerta"]["dominios"][0]
        self.assertEqual([g["ref"] for g in energia["gatilhos"]], ["brent", "p1"])
        energia["gatilhos"].append(dict(energia["gatilhos"][1], ref="r4"))
        energia["gatilhos"].append(dict(energia["gatilhos"][1], ref="p9"))
        linhas = [linha for linha in self.refaz_com(exemplo).splitlines() if linha.startswith("- `energia.")]
        self.assertEqual([linha.rsplit(" · ", 1)[1] for linha in linhas],
                         ["ver indicador: Petróleo Brent", "ver principal 1", "ver radar 4", "`p9`"])
        self.assertTrue(all(linha.startswith(("- `energia.2` · ", "- `energia.3` · ")) for linha in linhas), linhas)

    def test_lado_da_fonte_e_o_gravado_no_ataque(self):
        """Depois de o dono mudar o lado de um veículo no mapa, o refaz não põe dois partidos para o mesmo veículo
        no mesmo item: a fonte usa o lado gravado no ataque. Fonte sem ataque do mesmo veículo segue o mapa."""
        edicao, _ = self.publicada()
        self.assertEqual([(a["veiculo"], a["lado"]) for a in edicao["principais"][0]["ataques"]][0], ("nyt", "ordem_global"))

        def muda_o_lado(mapa):
            for veiculo in mapa["veiculos"]:
                if veiculo["id"] in ("nyt", "reuters"):
                    veiculo["lado"] = "independentes"
        self.muda("dados/veiculos.json", muda_o_lado)
        self.assertOK(self.publica("refaz"))
        p1 = self.blocos_dos_itens(self.texto("edicoes/%s.md" % DIA))["p1"].splitlines()
        nyt = [linha for linha in p1 if linha.startswith("- The New York Times · ")]
        self.assertEqual(len(nyt), 2, "uma linha em Quem atirou e uma em Fontes")
        self.assertTrue(all(linha.startswith("- The New York Times · Partido da Ordem Global · ") for linha in nyt), nyt)
        self.assertTrue(any(linha.startswith("- Reuters · Independentes · ") for linha in p1), "sem ataque: o mapa")

    def test_nota_de_rascunho_segue_o_mapa(self):
        """O lado é palpite enquanto o mapa não foi revisado: a nota do site, abaixo de Principais e de Radar."""
        _, texto = self.publicada()
        nota = "Mapa de veículos em rascunho, ainda sem revisão do dono."
        self.assertEqual(texto.splitlines().count(nota), 2)
        self.assertIn("## Principais\n\n%s\n\n### p1 · " % nota, texto)
        self.assertIn("## Radar\n\n%s\n\n### r1 · " % nota, texto)
        self.muda("dados/veiculos.json", lambda mapa: mapa.update(revisado_em="2026-11-30"))
        self.assertOK(self.publica("refaz"))
        self.assertNotIn(nota, self.texto("edicoes/%s.md" % DIA), "mapa revisado: a nota sai no refaz")

    def test_vinculo_do_conflito_quando_a_regua_o_conhece(self):
        """O aviso nomeia o vínculo quando a lista de conflito da régua o conhece (regra R19, casos b e c), com o
        texto e a regra do site (ESPEC-SITE, seção 8.3): os nomes na ordem da lista, primeiro os players, depois
        os termos; termo que já está no nome de um player listado não se repete."""
        exemplo = apoio.exemplo()
        exemplo["radar"][1]["fato"] += " A Anthropic comenta."  # r2: Google, player e termo da lista
        texto = self.refaz_com(exemplo)
        blocos = self.blocos_dos_itens(texto)
        r2 = blocos["r2"].splitlines()
        vinculo = [linha for linha in r2 if linha.startswith("Este item envolve nomes da lista de conflito ")]
        self.assertEqual(vinculo, ["Este item envolve nomes da lista de conflito da régua: Google, Anthropic."], r2)
        # r1 é de IA sem nome da lista: só o aviso e o teto
        self.assertFalse([linha for linha in blocos["r1"].splitlines() if linha.startswith("Este item envolve")])
        # caso d (fonte de veículo ligado à Anthropic): vem do mapa, não da lista; como no site, não ganha frase
        dados = apoio.dados()
        self.assertTrue(dados.ligados, "o mapa congelado tem veículo ligado à Anthropic")
        ligado = sorted(dados.ligados)[0]
        exemplo["radar"][0]["fontes"][1]["veiculo"] = ligado
        texto = self.refaz_com(exemplo)
        r1 = self.blocos_dos_itens(texto)["r1"]
        self.assertIn(publica.AVISO_DE_CONFLITO, r1)
        self.assertFalse([linha for linha in r1.splitlines() if linha.startswith("Este item envolve")], r1)

if __name__ == "__main__":
    unittest.main()
