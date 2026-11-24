#!/usr/bin/env python3
"""Testes de ferramentas/rede.py: o pedido de rede do coleta.py e do indicadores.py.

Rodar da raiz do repositório: python3 -B testes/testa_rede.py
O caminho de rede de verdade é exercitado contra um servidor HTTP aberto em 127.0.0.1 dentro do
próprio teste, e fechado no fim. Nada sai da máquina e nada é gravado dentro do repositório.
"""
import gzip
import json
import os
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

sys.dont_write_bytecode = True
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "ferramentas"))

import comum  # noqa: E402
import rede  # noqa: E402

GRANDE = rede.LIMITE + 300 * 1024


class Tratador(BaseHTTPRequestHandler):
    """Servidor de mentira. Cada caminho ensaia um comportamento de site real, ou hostil."""

    protocol_version = "HTTP/1.0"

    def log_message(self, *posicionais):
        pass

    def manda(self, codigo, corpo=b"", **cabecalhos):
        self.send_response(codigo)
        for nome, valor in cabecalhos.items():
            self.send_header(nome.replace("_", "-"), valor)
        self.end_headers()
        self.wfile.write(corpo)

    def do_CONNECT(self):  # pedido de túnel: o servidor faz o papel de proxy que recusa
        self.server.pedidos.append(("CONNECT", self.path, dict(self.headers)))
        self.manda(self.server.tunel)

    def do_GET(self):
        self.server.pedidos.append(("GET", self.path, dict(self.headers)))
        vezes = sum(1 for metodo, caminho, _ in self.server.pedidos if caminho == self.path)
        base = "http://127.0.0.1:%d" % self.server.server_port
        caminho = self.path.split("?")[0]
        if self.path.startswith("http://"):  # pedido com endereço inteiro: chegou por proxy
            self.manda(200, b"pelo proxy", Content_Type="text/plain")
        elif caminho == "/ok":
            self.manda(200, b"<rss/>", Content_Type="application/rss+xml; charset=utf-8")
        elif caminho.startswith("/salto/"):  # /salto/3 -> /salto/2 -> /salto/1 -> /salto/0 (responde)
            resta = int(caminho.rsplit("/", 1)[1])
            if resta:
                self.manda(302, Location="/salto/%d" % (resta - 1))
            else:
                self.manda(200, b"fim da cadeia")
        elif caminho == "/laco/a":
            self.manda(301, Location=base + "/laco/b")
        elif caminho == "/laco/b":
            self.manda(307, Location=base + "/laco/a")
        elif caminho == "/para":
            self.manda(302, Location=self.server.para)
        elif caminho == "/sem-destino":
            self.manda(302)
        elif caminho == "/grande":
            self.manda(200, b"x" * GRANDE, Content_Length=str(GRANDE))
        elif caminho == "/grande-mentindo":  # diz 10 bytes e manda mais de 2 MB
            self.manda(200, b"y" * GRANDE, Content_Length="10")
        elif caminho == "/exata":  # o caso comum: tamanho declarado e cumprido
            self.manda(200, b"<rss>exata</rss>", Content_Length="16")
        elif caminho == "/gigante-declarado":  # diz 50 GB; o que conta é o que chega
            self.manda(200, b"w" * GRANDE, Content_Length=str(50 * 1024 ** 3))
        elif caminho == "/grande-sem-tamanho":
            self.manda(200, b"z" * GRANDE)
        elif caminho == "/gzip":
            self.manda(200, gzip.compress("<rss>ação</rss>".encode("utf-8")), Content_Encoding="gzip")
        elif caminho == "/gzip-bomba":  # 30 MB de zeros cabem em uns 30 KB de gzip
            self.manda(200, gzip.compress(b"\0" * (30 * 1024 * 1024)), Content_Encoding="gzip")
        elif caminho == "/gzip-estragado":
            self.manda(200, b"isto nao e gzip", Content_Encoding="gzip")
        elif caminho == "/brotli":
            self.manda(200, b"\x0b\x02\x80ab\x03", Content_Encoding="br")
        elif caminho == "/lento":
            time.sleep(self.server.demora)
            self.manda(200, b"tarde demais")
        elif caminho == "/gotas":  # cabeçalho na hora, corpo de 1 byte por vez: nenhuma leitura sozinha estoura
            self.send_response(200)
            self.end_headers()
            try:
                for _ in range(60):
                    self.wfile.write(b"g")
                    self.wfile.flush()
                    time.sleep(0.1)
            except OSError:
                pass
        elif caminho == "/incompleta":
            self.manda(200, b"so metade", Content_Length="5000")
        elif caminho == "/lixo":
            self.wfile.write(b"isto nao e HTTP\r\n\r\n")
        elif caminho.startswith("/codigo/"):
            self.manda(int(caminho.rsplit("/", 1)[1]), b"corpo de erro que ninguem le")
        elif caminho == "/falha-depois-ok":
            self.manda(503 if vezes == 1 else 200, b"na segunda foi")
        elif caminho == "/eco":
            self.manda(200, json.dumps(dict(self.headers)).encode("utf-8"), Content_Type="application/json")
        else:
            self.manda(404)


class Servidor(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):  # cliente que desliga no meio é o esperado aqui
        pass


class ComServidor(unittest.TestCase):
    """Abre o servidor em 127.0.0.1, numa porta livre, e fecha no fim de cada teste."""

    def setUp(self):
        self.servidor = Servidor(("127.0.0.1", 0), Tratador)
        self.servidor.pedidos, self.servidor.demora, self.servidor.tunel = [], 3.0, 403
        self.servidor.para = "file:///etc/passwd"
        fio = threading.Thread(target=self.servidor.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
        fio.start()
        self.addCleanup(fio.join, 5)
        self.addCleanup(self.servidor.server_close)
        self.addCleanup(self.servidor.shutdown)
        self.base = "http://127.0.0.1:%d" % self.servidor.server_port
        # Sem proxy no ambiente: o pedido vai direto ao servidor do teste, em qualquer máquina.
        limpo = {k: v for k, v in os.environ.items() if not k.lower().endswith("_proxy")}
        ambiente = mock.patch.dict(os.environ, limpo, clear=True)
        ambiente.start()
        self.addCleanup(ambiente.stop)
        pausa = mock.patch.object(rede, "PAUSA", 0.05)
        pausa.start()
        self.addCleanup(pausa.stop)
        self.rede = rede.Rede(livres=("127.0.0.1",))

    def baixa(self, caminho, tempo=5, **nomeados):
        return self.rede.baixa(self.base + caminho, tempo, **nomeados)

    def pedidos(self, caminho):
        return [p for p in self.servidor.pedidos if p[1] == caminho]


class TestaPedido(ComServidor):
    def test_resposta_boa_traz_status_tipo_e_corpo(self):
        r = self.baixa("/ok")
        self.assertEqual((r.erro, r.status, r.corpo, r.cortada, r.boa), ("", 200, b"<rss/>", False, True))
        self.assertEqual(r.tipo, "application/rss+xml; charset=utf-8")
        self.assertEqual((r.url, r.final, r.falha()), (self.base + "/ok", self.base + "/ok", ""))

    def test_user_agent_do_contrato_e_pedido_de_gzip(self):
        cabecalhos = json.loads(self.baixa("/eco").corpo)
        self.assertEqual(cabecalhos["User-Agent"], "Mozilla/5.0 (compatible; INFOCENARIUM-monitor/1)")
        self.assertEqual(cabecalhos["Accept-Encoding"], "gzip")
        outro = json.loads(self.baixa("/eco", agente=rede.AGENTE_NAVEGADOR).corpo)
        self.assertIn("Firefox", outro["User-Agent"])

    def test_tres_redirecionamentos_em_cadeia_passam(self):
        r = self.baixa("/salto/3")
        self.assertEqual((r.status, r.corpo, r.erro), (200, b"fim da cadeia", ""))
        self.assertEqual((r.url, r.final), (self.base + "/salto/3", self.base + "/salto/0"))

    def test_quatro_redirecionamentos_e_demais(self):
        r = self.baixa("/salto/4")
        self.assertEqual((r.motivo, r.erro, r.corpo), (rede.DESVIO, "redirecionamentos demais", b""))
        self.assertEqual(len(self.servidor.pedidos), 4)  # o 5º pedido nunca sai

    def test_redirecionamento_em_laco_para_no_terceiro(self):
        r = self.baixa("/laco/a")
        self.assertEqual((r.motivo, r.erro), (rede.DESVIO, "redirecionamentos demais"))
        self.assertEqual(len(self.servidor.pedidos), 4)

    def test_redirecionamento_para_file_e_recusado(self):
        r = self.baixa("/para")
        self.assertEqual(r.motivo, rede.DESVIO)
        self.assertEqual(r.erro, "redirecionamento recusado: só http e https")
        self.assertEqual((r.corpo, r.boa), (b"", False))
        self.assertNotIn(b"root:", r.corpo)

    def test_redirecionamento_para_endereco_interno_e_recusado_sem_ligar(self):
        for destino in ("http://localhost:8188/prompt", "http://169.254.169.254/latest/meta-data/",
                        "http://10.0.0.1/", "https://[::1]/", "http://servidor/", "ftp://exemplo.invalid/a",
                        "http://0x7f.0.0.1/", "http://usuario:senha@exemplo.invalid/"):
            self.servidor.para = destino
            self.servidor.pedidos.clear()
            r = self.baixa("/para", tempo=2)
            self.assertEqual(r.motivo, rede.DESVIO, destino)
            self.assertTrue(r.erro.startswith("redirecionamento recusado: "), r.erro)
            self.assertEqual(len(self.servidor.pedidos), 1, destino)

    def test_redirecionamento_sem_destino(self):
        r = self.baixa("/sem-destino")
        self.assertEqual((r.motivo, r.erro), (rede.DESVIO, "redirecionamento sem destino"))

    def test_resposta_maior_que_2_mb_e_cortada_lendo_em_pedacos(self):
        for caminho, letra in (("/grande", b"x"), ("/gigante-declarado", b"w"), ("/grande-sem-tamanho", b"z")):
            r = self.baixa(caminho)
            self.assertEqual((r.erro, r.status, r.cortada), ("", 200, True), caminho)
            self.assertEqual(len(r.corpo), rede.LIMITE, caminho)
            self.assertEqual(set(r.corpo), set(letra), caminho)

    def test_tamanho_declarado_menor_que_o_enviado_fica_no_declarado(self):
        # O Content-Length é a moldura do HTTP: o que passa dele não é corpo. Nada além dos 10 bytes é lido.
        r = self.baixa("/grande-mentindo")
        self.assertEqual((r.erro, r.status, r.cortada, r.corpo), ("", 200, False, b"y" * 10))

    def test_resposta_com_tamanho_declarado_e_cumprido(self):
        r = self.baixa("/exata")
        self.assertEqual((r.erro, r.status, r.cortada, r.corpo), ("", 200, False, b"<rss>exata</rss>"))
        self.assertEqual(len(self.pedidos("/exata")), 1)

    def test_gzip_e_aberto(self):
        r = self.baixa("/gzip")
        self.assertEqual((r.erro, r.cortada, r.corpo.decode("utf-8")), ("", False, "<rss>ação</rss>"))

    def test_gzip_que_incha_para_no_teto(self):
        inicio = time.monotonic()
        r = self.baixa("/gzip-bomba")
        self.assertEqual((r.erro, r.cortada, len(r.corpo)), ("", True, rede.LIMITE))
        self.assertLess(time.monotonic() - inicio, 5)

    def test_gzip_estragado_e_compressao_desconhecida_viram_erro(self):
        r = self.baixa("/gzip-estragado")
        self.assertEqual((r.motivo, r.erro, r.corpo), (rede.PROTOCOLO, "gzip estragado", b""))
        self.assertEqual(len(self.pedidos("/gzip-estragado")), 2)  # passageira: tentou de novo
        r = self.baixa("/brotli")
        self.assertEqual((r.motivo, r.erro), (rede.PROTOCOLO, "compressão que a ferramenta não lê"))

    def test_resposta_lenta_estoura_o_tempo_limite_sem_nova_tentativa(self):
        inicio = time.monotonic()
        r = self.baixa("/lento", tempo=0.4)
        gasto = time.monotonic() - inicio
        self.assertEqual((r.motivo, r.erro, r.status), (rede.TEMPO, "tempo esgotado", 0))
        self.assertLess(gasto, 1.5)
        self.assertEqual(len(self.pedidos("/lento")), 1)

    def test_resposta_em_conta_gotas_estoura_o_tempo_total(self):
        # Cada leitura recebe 1 byte dentro do tempo limite: só o relógio do pedido inteiro pega.
        inicio = time.monotonic()
        r = self.baixa("/gotas", tempo=0.5)
        gasto = time.monotonic() - inicio
        self.assertEqual((r.motivo, r.erro, r.corpo), (rede.TEMPO, "tempo esgotado", b""))
        self.assertLess(gasto, 1.5)

    def test_codigos_403_e_404_voltam_sem_nova_tentativa_e_sem_corpo(self):
        for codigo in (401, 403, 404, 410):
            r = self.baixa("/codigo/%d" % codigo)
            self.assertEqual((r.erro, r.status, r.corpo, r.boa), ("", codigo, b"", False))
            self.assertEqual(r.falha(), "HTTP %d" % codigo)
            self.assertEqual(len(self.pedidos("/codigo/%d" % codigo)), 1)

    def test_429_e_5xx_ganham_uma_nova_tentativa_e_so_uma(self):
        # CONTRATO, seção 0: uma nova tentativa, depois de 1 segundo, só para falha passageira (conexão caída, 429, 5xx)
        for codigo in (429, 500, 501, 503, 504, 599):
            self.rede._ruins = 0  # sem isso, o freio de "máquina sem rede" (8 falhas sem sucesso) entra no meio do laço
            r = self.baixa("/codigo/%d" % codigo)
            self.assertEqual((r.erro, r.status, r.falha()), ("", codigo, "HTTP %d" % codigo))
            self.assertEqual(len(self.pedidos("/codigo/%d" % codigo)), 2)

    def test_nova_tentativa_que_da_certo(self):
        r = self.baixa("/falha-depois-ok")
        self.assertEqual((r.status, r.corpo), (200, b"na segunda foi"))

    def test_sem_sinal_de_rede_nao_insiste(self):
        self.rede._ruins = rede.SEM_SINAL  # vários pedidos falharam e nenhum deu certo
        self.baixa("/codigo/503")
        self.assertEqual(len(self.pedidos("/codigo/503")), 1)
        self.baixa("/ok")  # um sucesso prova que há rede: volta a insistir
        self.baixa("/codigo/500")
        self.assertEqual(len(self.pedidos("/codigo/500")), 2)

    def test_resposta_incompleta_e_resposta_que_nao_e_http(self):
        r = self.baixa("/incompleta")
        self.assertEqual((r.motivo, r.erro, r.corpo), (rede.CONEXAO, "resposta incompleta", b""))
        r = self.baixa("/lixo")
        self.assertEqual(r.motivo, rede.CONEXAO)
        self.assertEqual(len(self.pedidos("/lixo")), 2)

    def test_porta_fechada_e_falha_de_conexao(self):
        with socket.socket() as livre:
            livre.bind(("127.0.0.1", 0))
            porta = livre.getsockname()[1]
        r = self.rede.baixa("http://127.0.0.1:%d/x" % porta, 2)
        self.assertEqual((r.motivo, r.status, r.boa), (rede.CONEXAO, 0, False))
        self.assertNotIn("127.0.0.1", r.erro)

    def test_teto_do_lote_ja_vencido_nem_pede(self):
        r = self.baixa("/ok", prazo=time.monotonic() - 1)
        self.assertEqual((r.motivo, r.erro), (rede.TETO, "não coube no tempo"))
        self.assertEqual(self.servidor.pedidos, [])

    def test_teto_do_lote_corta_o_pedido_em_curso(self):
        inicio = time.monotonic()
        r = self.baixa("/lento", tempo=30, prazo=inicio + 0.4)
        self.assertEqual((r.motivo, r.erro), (rede.TETO, "não coube no tempo"))
        self.assertLess(time.monotonic() - inicio, 1.5)

    def test_endereco_recusado_nem_sai(self):
        for url in ("file:///etc/passwd", "http://127.0.0.2/x", "http://localhost/x", "gopher://exemplo.invalid/",
                    "https:///sem-nome", "http://exemplo.invalid/a b", "", None, 7):
            r = rede.Rede().baixa(url, 2)
            self.assertEqual((r.motivo, r.status, r.corpo), (rede.URL, 0, b""), url)
        self.assertEqual(self.servidor.pedidos, [])


class TestaNomeDeSite(ComServidor):
    def test_nome_que_nao_existe_e_nome_que_nao_resolveu(self):
        def nao_existe(*posicionais, **nomeados):
            raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")

        def agora_nao(*posicionais, **nomeados):
            raise socket.gaierror(socket.EAI_AGAIN, "Temporary failure in name resolution")

        with mock.patch("socket.getaddrinfo", nao_existe):
            r = rede.Rede().baixa("http://site-que-nao-existe.invalid/a", 2)
        self.assertEqual((r.motivo, r.erro), (rede.NOME, "o nome do site não existe"))
        with mock.patch("socket.getaddrinfo", agora_nao):
            r = rede.Rede().baixa("http://site-que-nao-existe.invalid/a", 2)
        self.assertEqual((r.motivo, r.erro), (rede.CONEXAO, "nome do site não resolvido"))


class TestaProxyECertificado(ComServidor):
    def test_http_passa_pelo_proxy_do_ambiente(self):
        with mock.patch.dict(os.environ, {"http_proxy": self.base}):
            r = rede.Rede().baixa("http://exemplo.invalid/feed.xml", 5)
        self.assertEqual((r.status, r.corpo), (200, b"pelo proxy"))
        self.assertEqual(self.servidor.pedidos[0][:2], ("GET", "http://exemplo.invalid/feed.xml"))

    def test_https_pede_tunel_ao_proxy_e_a_recusa_vira_erro_sem_vazar_o_endereco(self):
        proxy = "http://usuario:senha-secreta@127.0.0.1:%d" % self.servidor.server_port
        with mock.patch.dict(os.environ, {"https_proxy": proxy}):
            r = rede.Rede().baixa("https://exemplo.invalid/feed.xml", 5)
        self.assertEqual((r.motivo, r.erro), (rede.PROXY, "o proxy recusou a ligação (HTTP 403)"))
        self.assertEqual([p[:2] for p in self.servidor.pedidos], [("CONNECT", "exemplo.invalid:443")])
        self.assertNotIn("senha", r.erro + r.falha())

    def test_proxy_com_erro_passageiro_ganha_nova_tentativa(self):
        self.servidor.tunel = 502
        with mock.patch.dict(os.environ, {"https_proxy": self.base}):
            r = rede.Rede().baixa("https://exemplo.invalid/feed.xml", 5)
        self.assertEqual(r.erro, "o proxy recusou a ligação (HTTP 502)")
        self.assertEqual(len(self.servidor.pedidos), 2)

    def test_no_proxy_e_respeitado(self):
        with mock.patch.dict(os.environ, {"http_proxy": "http://127.0.0.1:9", "no_proxy": "127.0.0.1"}):
            r = rede.Rede(livres=("127.0.0.1",)).baixa(self.base + "/ok", 5)
        self.assertEqual(r.status, 200)

    def test_conferencia_de_certificado_fica_ligada(self):
        contexto = rede._contexto_tls()
        self.assertEqual(contexto.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(contexto.check_hostname)
        with open(os.path.join(RAIZ, "ferramentas", "rede.py"), encoding="utf-8") as arquivo:
            fonte = arquivo.read()
        for proibido in ("CERT_NONE", "_create_unverified_context", "check_hostname = False", "verify=False"):
            self.assertNotIn(proibido, fonte)

    def test_https_em_porta_que_nao_fala_tls_falha(self):
        r = self.rede.baixa("https://127.0.0.1:%d/ok" % self.servidor.server_port, 3)
        self.assertEqual((r.motivo, r.boa, r.corpo), (rede.CONEXAO, False, b""))

    @unittest.skipUnless(shutil.which("openssl"), "sem o programa openssl para gerar o certificado de teste")
    def test_certificado_que_ninguem_assinou_e_recusado(self):
        pasta = tempfile.TemporaryDirectory(prefix="info-rede-")
        self.addCleanup(pasta.cleanup)
        chave, certificado = os.path.join(pasta.name, "chave.pem"), os.path.join(pasta.name, "cert.pem")
        feito = subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "2",
                                "-subj", "/CN=127.0.0.1", "-addext", "subjectAltName=IP:127.0.0.1",
                                "-keyout", chave, "-out", certificado], capture_output=True, timeout=60)
        if feito.returncode != 0:
            self.skipTest("o openssl desta máquina não gerou o certificado")
        seguro = Servidor(("127.0.0.1", 0), Tratador)
        seguro.pedidos, seguro.demora, seguro.tunel, seguro.para = [], 0, 403, ""
        contexto = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        contexto.load_cert_chain(certificado, chave)
        seguro.socket = contexto.wrap_socket(seguro.socket, server_side=True)
        fio = threading.Thread(target=seguro.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
        fio.start()
        self.addCleanup(fio.join, 5)
        self.addCleanup(seguro.server_close)
        self.addCleanup(seguro.shutdown)
        url = "https://127.0.0.1:%d/ok" % seguro.server_port
        r = self.rede.baixa(url, 5)
        self.assertEqual((r.motivo, r.erro, r.corpo), (rede.CERTIFICADO, "certificado recusado", b""))
        self.assertEqual(seguro.pedidos, [])  # o pedido nem chega a ser feito
        # A máquina indica a autoridade pelo ambiente (o caso do proxy que abre o https): aí passa.
        with mock.patch.dict(os.environ, {"REQUESTS_CA_BUNDLE": certificado}):
            r = rede.Rede(livres=("127.0.0.1",)).baixa(url, 5)
        self.assertEqual((r.erro, r.status, r.corpo), ("", 200, b"<rss/>"))


class TestaRecusa(unittest.TestCase):
    def test_aceita_http_e_https_com_nome_de_site(self):
        for url in ("https://exemplo.invalid/a", "http://www.exemplo.com.br/feed?x=1&utm_source=a#b",
                    "HTTPS://Exemplo.COM/Caminho", "https://пример.рф/новости", "https://a_b.exemplo.org./x",
                    "https://exemplo.com:8443/x"):
            self.assertEqual(rede.recusa(url), "", url)

    def test_recusa_o_que_nao_e_site_publico(self):
        for url in ("file:///etc/passwd", "ftp://exemplo.com/a", "data:text/html,x", "javascript:alert(1)",
                    "jar:file:///x!/y", "gopher://exemplo.com", "//exemplo.com/a", "exemplo.com/a", "https:///a",
                    "http://127.0.0.1/", "http://127.1/", "http://0x7f.0.0.1/", "http://2130706433/",
                    "http://[::1]/", "http://[fd00::1]/", "http://169.254.169.254/", "http://localhost/",
                    "http://maquina/", "http://a.localhost/", "http://a.internal/", "http://impressora.local/",
                    "http://roteador.lan/", "http://kubernetes.default.svc/", "http://api.svc/",
                    "https://usuario@exemplo.com/", "https://u:s@exemplo.com/",
                    "https://exemplo.com:99999/", "https://exem plo.com/", "https://exemplo.com/a\nb",
                    "https://exemplo.com/a\tb", "https://exemplo.com\\@malvado.com/", "https://-a.com/",
                    "https://a..com/", "https://" + "a" * 64 + ".com/", "https://exemplo.com/" + "a" * 2000):
            self.assertNotEqual(rede.recusa(url), "", url)

    def test_o_que_vai_no_pedido_e_ascii_e_sem_fragmento(self):
        self.assertEqual(rede._para_pedir("https://пример.рф/новости?q=ação#topo"),
                         "https://xn--e1afmkfd.xn--p1ai/%D0%BD%D0%BE%D0%B2%D0%BE%D1%81%D1%82%D0%B8?q=a%C3%A7%C3%A3o")
        self.assertEqual(rede._para_pedir("https://exemplo.com/a%20b/c?d[0]=e&f=%5E"),
                         "https://exemplo.com/a%20b/c?d[0]=e&f=%5E")
        self.assertEqual(rede._para_pedir("https://exemplo.com"), "https://exemplo.com/")


class TestaOffline(unittest.TestCase):
    def setUp(self):
        temporaria = tempfile.TemporaryDirectory(prefix="info-rede-")
        self.addCleanup(temporaria.cleanup)
        self.pasta = os.path.realpath(temporaria.name)

    def monta(self, respostas, **arquivos):
        for nome, conteudo in arquivos.items():
            with open(os.path.join(self.pasta, nome.replace("__", ".")), "wb") as arquivo:
                arquivo.write(conteudo)
        with open(os.path.join(self.pasta, "respostas.json"), "w", encoding="utf-8") as arquivo:
            json.dump(respostas, arquivo)
        return rede.Rede(offline=self.pasta)

    def test_forma_simples_url_para_arquivo(self):
        r = self.monta({"https://exemplo.invalid/feed": "feed.xml"}, feed__xml=b"<rss/>").baixa(
            "https://exemplo.invalid/feed", 5)
        self.assertEqual((r.erro, r.status, r.tipo, r.corpo, r.cortada), ("", 200, "", b"<rss/>", False))

    def test_url_ausente_conta_como_erro_de_rede(self):
        r = self.monta({}).baixa("https://exemplo.invalid/feed", 5)
        self.assertEqual((r.motivo, r.erro, r.status), (rede.OFFLINE, "sem resposta no modo offline", 0))

    def test_a_chave_e_a_url_exata(self):
        local = self.monta({"https://exemplo.invalid/feed": "feed.xml"}, feed__xml=b"<rss/>")
        for outra in ("https://exemplo.invalid/feed/", "http://exemplo.invalid/feed", "https://exemplo.invalid/feed#a"):
            self.assertEqual(local.baixa(outra, 5).motivo, rede.OFFLINE, outra)

    def test_forma_de_objeto_status_tipo_e_corpo(self):
        local = self.monta({
            "https://exemplo.invalid/a": {"arquivo": "pagina.html", "status": 403, "tipo": "text/html; charset=utf-8"},
            "https://exemplo.invalid/b": {"status": 404},
            "https://exemplo.invalid/c": {"arquivo": "pagina.html", "tipo": "text/html"},
            "https://exemplo.invalid/d": {},
        }, pagina__html=b"<html></html>")
        a, b = local.baixa("https://exemplo.invalid/a", 5), local.baixa("https://exemplo.invalid/b", 5)
        c, d = local.baixa("https://exemplo.invalid/c", 5), local.baixa("https://exemplo.invalid/d", 5)
        self.assertEqual((a.erro, a.status, a.tipo, a.boa), ("", 403, "text/html; charset=utf-8", False))
        self.assertEqual((b.erro, b.status, b.corpo, b.falha()), ("", 404, b"", "HTTP 404"))
        self.assertEqual((c.status, c.tipo, c.corpo), (200, "text/html", b"<html></html>"))
        self.assertEqual((d.status, d.tipo, d.corpo, d.boa), (200, "", b"", True))

    def test_redirecionamento_segue_como_na_rede(self):
        local = self.monta({
            "https://exemplo.invalid/1": {"status": 301, "para": "https://outro.invalid/2"},
            "https://outro.invalid/2": {"para": "/3"},
            "https://outro.invalid/3": {"para": "https://outro.invalid/4"},
            "https://outro.invalid/4": "fim.txt",
            "https://exemplo.invalid/sem-destino": {"para": "https://outro.invalid/nao-esta"},
            "https://exemplo.invalid/laco": {"para": "https://exemplo.invalid/laco"},
            "https://exemplo.invalid/0": {"para": "https://exemplo.invalid/1"},
            "https://exemplo.invalid/arquivo": {"para": "file:///etc/passwd"},
            "https://exemplo.invalid/interno": {"para": "http://127.0.0.1:8188/"},
        }, fim__txt=b"cheguei")
        r = local.baixa("https://exemplo.invalid/1", 5)
        self.assertEqual((r.status, r.corpo, r.final), (200, b"cheguei", "https://outro.invalid/4"))
        self.assertEqual(local.baixa("https://exemplo.invalid/sem-destino", 5).motivo, rede.OFFLINE)
        self.assertEqual(local.baixa("https://exemplo.invalid/laco", 5).erro, "redirecionamentos demais")
        self.assertEqual(local.baixa("https://exemplo.invalid/0", 5).erro, "redirecionamentos demais")
        self.assertEqual(local.baixa("https://exemplo.invalid/arquivo", 5).erro,
                         "redirecionamento recusado: só http e https")
        self.assertEqual(local.baixa("https://exemplo.invalid/interno", 5).motivo, rede.DESVIO)

    def test_teto_de_2_mb_vale_no_offline(self):
        r = self.monta({"https://exemplo.invalid/g": "grande.bin"}, grande__bin=b"g" * GRANDE).baixa(
            "https://exemplo.invalid/g", 5)
        self.assertEqual((r.erro, r.cortada, len(r.corpo)), ("", True, rede.LIMITE))

    def test_arquivo_que_falta_ou_que_mora_fora_da_pasta(self):
        fora = tempfile.NamedTemporaryFile(prefix="info-rede-fora-", delete=False)
        fora.write(b"segredo")
        fora.close()
        self.addCleanup(os.unlink, fora.name)
        local = self.monta({
            "https://exemplo.invalid/a": "nao-existe.xml",
            "https://exemplo.invalid/b": fora.name,
            "https://exemplo.invalid/c": "../" + os.path.basename(fora.name),
            "https://exemplo.invalid/d": 7,
            "https://exemplo.invalid/e": {"arquivo": "x", "status": "200"},
        })
        for letra in "abcde":
            r = local.baixa("https://exemplo.invalid/" + letra, 5)
            self.assertEqual((r.motivo, r.corpo, r.boa), (rede.OFFLINE, b"", False), letra)

    def test_pasta_ou_respostas_json_que_nao_servem_sao_erro_de_uso(self):
        with self.assertRaises(comum.ErroDeUso):
            rede.Rede(offline=os.path.join(self.pasta, "nao-existe"))
        with self.assertRaises(comum.ErroDeUso):
            rede.Rede(offline=self.pasta)  # sem respostas.json
        for ruim in (b"{quebrado", b"[1, 2]", b"\xff\xfe"):
            with open(os.path.join(self.pasta, "respostas.json"), "wb") as arquivo:
                arquivo.write(ruim)
            with self.assertRaises(comum.ErroDeUso):
                rede.Rede(offline=self.pasta)

    def test_respostas_json_vazio_vale_como_nenhuma_resposta(self):
        with open(os.path.join(self.pasta, "respostas.json"), "wb") as arquivo:
            arquivo.write(b"  \n")
        self.assertEqual(rede.Rede(offline=self.pasta).baixa("https://exemplo.invalid/a", 5).motivo, rede.OFFLINE)

    def test_offline_nao_espera_nem_insiste(self):
        local = self.monta({"https://exemplo.invalid/a": {"status": 503}})
        inicio = time.monotonic()
        self.assertEqual(local.baixa("https://exemplo.invalid/a", 5).status, 503)
        self.assertLess(time.monotonic() - inicio, 0.5)

    def test_demora_e_esperada_de_verdade_ate_o_tempo_limite(self):
        # CONTRATO, seção 0, --offline: `demora` em segundos; a ferramenta espera de verdade, até o tempo limite do
        # pedido. Dentro do limite, a resposta chega; além dele, é tempo esgotado (não respondeu), sem nova tentativa.
        local = self.monta({"https://exemplo.invalid/a": {"arquivo": "a.txt", "demora": 0.3},
                            "https://exemplo.invalid/b": {"arquivo": "a.txt", "demora": 3},
                            "https://exemplo.invalid/c": {"status": 302, "para": "https://exemplo.invalid/d", "demora": 0.3},
                            "https://exemplo.invalid/d": {"arquivo": "a.txt", "demora": 0.3}}, a__txt=b"veio")
        inicio = time.monotonic()
        r = local.baixa("https://exemplo.invalid/a", 1)
        self.assertEqual((r.erro, r.corpo), ("", b"veio"))
        self.assertGreaterEqual(time.monotonic() - inicio, 0.3)
        inicio = time.monotonic()
        r = local.baixa("https://exemplo.invalid/b", 0.5)
        gasto = time.monotonic() - inicio
        self.assertEqual((r.motivo, r.erro, r.corpo), (rede.TEMPO, "tempo esgotado", b""))
        self.assertTrue(0.45 <= gasto < 1.5, gasto)
        # a demora de cada salto soma no mesmo relógio: o tempo limite é do pedido inteiro
        self.assertEqual(local.baixa("https://exemplo.invalid/c", 0.5).motivo, rede.TEMPO)
        self.assertEqual(local.baixa("https://exemplo.invalid/c", 1).corpo, b"veio")
        # o teto do lote corta antes: vira "não coube no tempo"
        r = local.baixa("https://exemplo.invalid/b", 5, prazo=time.monotonic() + 0.3)
        self.assertEqual((r.motivo, r.erro), (rede.TETO, "não coube no tempo"))

    def test_falha_nome_simula_o_site_que_nao_existe(self):
        local = self.monta({"https://exemplo.invalid/a": {"falha": "nome"},
                            "https://exemplo.invalid/b": {"status": 302, "para": "https://outro.invalid/c"},
                            "https://outro.invalid/c": {"falha": "nome"}})
        for letra in "ab":
            r = local.baixa("https://exemplo.invalid/" + letra, 5)
            self.assertEqual((r.motivo, r.erro, r.status), (rede.NOME, "o nome do site não existe", 0), letra)

    def test_demora_ou_falha_tortas_sao_erro_de_rede_daquela_url(self):
        local = self.monta({"https://exemplo.invalid/a": {"demora": -1}, "https://exemplo.invalid/b": {"demora": "1"},
                            "https://exemplo.invalid/c": {"demora": True}, "https://exemplo.invalid/d": {"falha": "tempo"},
                            "https://exemplo.invalid/e": {"falha": 1}})
        for letra in "abcde":
            self.assertEqual(local.baixa("https://exemplo.invalid/" + letra, 5).motivo, rede.OFFLINE, letra)


class TestaLote(unittest.TestCase):
    def test_resultado_sai_na_ordem_dos_itens_e_nao_na_de_chegada(self):
        chegada = []

        def demora(item):
            time.sleep(item)
            chegada.append(item)
            return item * 10

        itens = [0.25, 0.01, 0.15, 0.05, 0.2, 0.0]
        self.assertEqual(rede.em_paralelo(demora, itens, 6, time.monotonic() + 5), [i * 10 for i in itens])
        self.assertNotEqual(chegada, itens)

    def test_respeita_o_numero_de_paralelos(self):
        tranca, agora, pico = threading.Lock(), [0], [0]

        def conta(item):
            with tranca:
                agora[0] += 1
                pico[0] = max(pico[0], agora[0])
            time.sleep(0.03)
            with tranca:
                agora[0] -= 1
            return item

        self.assertEqual(rede.em_paralelo(conta, range(20), 4, time.monotonic() + 10), list(range(20)))
        self.assertEqual(pico[0], 4)

    def test_o_que_nao_terminou_ate_o_teto_fica_de_fora_e_nao_trava(self):
        def prende(item):
            time.sleep(30 if item == "preso" else 0)
            return item

        inicio = time.monotonic()
        with mock.patch.object(rede, "FOLGA", 0.1):
            feitos = rede.em_paralelo(prende, ["a", "preso", "b"], 2, inicio + 0.3)
        self.assertEqual(feitos, ["a", None, "b"])
        self.assertLess(time.monotonic() - inicio, 2)

    def test_erro_de_programacao_sobe_na_thread_principal(self):
        def quebra(item):
            raise KeyError("defeito")

        with self.assertRaises(KeyError):
            rede.em_paralelo(quebra, [1, 2], 2, time.monotonic() + 5)

    def test_lista_vazia(self):
        self.assertEqual(rede.em_paralelo(len, [], 8, time.monotonic() + 1), [])

    def test_reserva_do_teto(self):
        # O valor de --tempo é conferido em cada ferramenta (inteiro de 1 a 3600: CONTRATO, seções 1 e 2).
        self.assertEqual(rede.prazo_de(100.0, 90), 185.0)
        self.assertEqual(rede.prazo_de(100.0, 10), 109.0)
        self.assertEqual(rede.prazo_de(100.0, 0), 100.0)


if __name__ == "__main__":
    unittest.main()
