#!/usr/bin/env python3
"""O mesmo urls.txt lido pelas três ferramentas que o leem (CONTRATO, seção 0, "Pasta de trabalho").

`coleta.py --confere` confere a data das páginas de urls.txt; `publica.py edicao` e o `valida.py` usam o
mesmo arquivo para as regras T1 e T5 (ESQUEMA, seção 10). Se as leituras divergissem, uma página conferida
pela coleta podia ser dada como "não vista" na publicação, ou o contrário. Aqui o mesmo texto passa pelas
duas leituras (a do `publica.py` é a do `valida.py`, sobre o texto que o `publica.py` lê do disco).

Rodar, da raiz do repositório:  python3 -B testes/testa_urls_txt.py
"""
import os
import shutil
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(RAIZ, "ferramentas"))

import coleta  # noqa: E402
import publica  # noqa: E402
import valida  # noqa: E402

TEXTO = (
    "# páginas abertas hoje\n"
    "https://reuters.com/exemplo/um\n"
    "\n"
    "   \n"
    "  https://apnews.com/exemplo/dois  \n"
    "https://reuters.com/exemplo/um\n"
    "#https://exemplo.invalid/comentada\n"
    "https://bbc.com/exemplo/tres\r\n"
    "\thttps://nytimes.com/exemplo/quatro\n"
)


class TestaMesmaLeitura(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp(prefix="info-urls-")
        self.addCleanup(shutil.rmtree, self.pasta, ignore_errors=True)

    def grava(self, dados):
        with open(os.path.join(self.pasta, "urls.txt"), "wb") as arquivo:
            arquivo.write(dados)

    def leituras(self):
        da_coleta, _ = coleta.le_urls(self.pasta)
        da_publicacao = valida.le_urls(publica._le_urls(self.pasta))
        return da_coleta, da_publicacao

    def test_as_duas_leituras_dao_as_mesmas_urls(self):
        self.grava(TEXTO.encode("utf-8"))
        da_coleta, da_publicacao = self.leituras()
        esperado = ["https://reuters.com/exemplo/um", "https://apnews.com/exemplo/dois", "https://reuters.com/exemplo/um",
                    "https://bbc.com/exemplo/tres", "https://nytimes.com/exemplo/quatro"]
        self.assertEqual(da_coleta, esperado)
        self.assertEqual(da_publicacao, esperado)

    def test_marca_de_ordem_de_bytes_no_comeco(self):
        # Um editor que grava UTF-8 "com BOM" não pode esconder a primeira URL de uma das leituras.
        self.grava(b"\xef\xbb\xbf" + TEXTO.encode("utf-8"))
        da_coleta, da_publicacao = self.leituras()
        self.assertEqual(da_coleta, da_publicacao)
        self.assertIn("https://reuters.com/exemplo/um", da_publicacao)

    def test_sem_arquivo_as_duas_ficam_vazias(self):
        self.assertEqual(self.leituras(), ([], []))


if __name__ == "__main__":
    unittest.main()
