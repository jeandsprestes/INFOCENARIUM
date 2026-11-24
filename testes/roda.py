#!/usr/bin/env python3
"""Roda todos os testes do repositório. Funciona chamado de qualquer pasta.

    python3 -B testes/roda.py                    tudo
    python3 -B testes/roda.py --so python        só os testes das ferramentas
    python3 -B testes/roda.py --so site          só os testes do site
    python3 -B testes/roda.py --filtro valida    só arquivos cujo caminho contém "valida"
    python3 -B testes/roda.py --pula contrato    deixa de fora os de caminho com "contrato"

Python: cada arquivo testa_*.py debaixo de testes/ (inclusive subpastas), um por processo, com
python3 -B e PYTHONDONTWRITEBYTECODE=1, a partir da raiz do repositório.

Site: se houver o programa node, os arquivos de teste de testes/site/. Valem os nomes que o
`node --test testes/site/` do Node 18 reconhece: test.js, test-x.js, x.test.js, x-test.js, x_test.js
(também .cjs e .mjs) e tudo o que estiver numa subpasta chamada test. Cada arquivo roda no seu
`node --test ARQUIVO`: assim há uma linha por arquivo, e o resultado não depende de como cada
versão do Node trata uma pasta na linha de comando.

Saída: uma linha por arquivo (ok ou falhou, e o tempo), o trecho final da saída dos que falharam e,
por último, "OK N arquivos de teste" (código 0) ou "FALHA N de M arquivos de teste" (código 1).
--filtro e --pula podem ser repetidos: entra o arquivo que contém algum filtro e nenhum --pula.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import time

TESTES = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(TESTES)
TEMPO_MAXIMO = 600  # segundos por arquivo: teste travado não segura a fila para sempre
LINHAS_DO_FIM = 40
RE_TESTE_NODE = re.compile(r"((.+\.)?test|test-.+|.+[._-]test)\.(js|cjs|mjs)")
EXTENSOES_NODE = (".js", ".cjs", ".mjs")
FORA = ("__pycache__", "node_modules")


def relativo(caminho):
    return os.path.relpath(caminho, RAIZ).replace(os.sep, "/")


def arquivos_python():
    achados = []
    for pasta, subpastas, nomes in os.walk(TESTES):
        subpastas[:] = sorted(s for s in subpastas if s not in FORA and not s.startswith("."))
        achados += [os.path.join(pasta, n) for n in sorted(nomes) if n.startswith("testa_") and n.endswith(".py")]
    return achados


def arquivos_site():
    """Os arquivos de teste de testes/site/ e, à parte, os .js que não têm nome de teste."""
    testes, outros = [], []
    for pasta, subpastas, nomes in os.walk(os.path.join(TESTES, "site")):
        subpastas[:] = sorted(s for s in subpastas if s not in FORA and not s.startswith("."))
        em_test = "test" in os.path.relpath(pasta, TESTES).split(os.sep)
        for nome in sorted(nomes):
            if not nome.endswith(EXTENSOES_NODE):
                continue
            (testes if em_test or RE_TESTE_NODE.fullmatch(nome) else outros).append(os.path.join(pasta, nome))
    return testes, outros


def roda(comando):
    """Roda um arquivo de teste. Devolve (passou, segundos, saída)."""
    ambiente = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    inicio = time.monotonic()
    try:
        feito = subprocess.run(comando, cwd=RAIZ, env=ambiente, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=TEMPO_MAXIMO)
        passou, bruto = feito.returncode == 0, feito.stdout
    except subprocess.TimeoutExpired as erro:
        passou, bruto = False, (erro.stdout or b"") + ("\npassou de %d segundos" % TEMPO_MAXIMO).encode()
    except OSError as erro:
        passou, bruto = False, ("não deu para rodar: %s" % erro).encode()
    return passou, time.monotonic() - inicio, bruto.decode("utf-8", "replace")


def diz(texto=""):
    print(texto, flush=True)


def principal(argv=None):
    opcoes = argparse.ArgumentParser(description="Roda os testes do repositório.")
    opcoes.add_argument("--so", choices=("python", "site"), help="roda só uma das duas partes")
    opcoes.add_argument("--filtro", action="append", default=[], metavar="TEXTO",
                        help="só arquivos cujo caminho contém o texto")
    opcoes.add_argument("--pula", action="append", default=[], metavar="TEXTO",
                        help="deixa de fora os arquivos cujo caminho contém o texto")
    args = opcoes.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):  # acento sai inteiro mesmo com a máquina em locale C
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    def entra(caminho):
        nome = relativo(caminho)
        return (not args.filtro or any(f in nome for f in args.filtro)) and not any(p in nome for p in args.pula)

    fila = []
    if args.so != "site":
        fila += [([sys.executable, "-B", c], c) for c in arquivos_python() if entra(c)]
    if args.so != "python":
        testes, outros = arquivos_site()
        node = shutil.which("node")
        if testes and not node:
            diz("aviso: sem o programa node; os %d arquivos de testes/site/ não rodaram" % len(testes))
        elif testes:
            fila += [([node, "--test", c], c) for c in testes if entra(c)]
        elif outros:  # sem isto, teste com nome fora do padrão ficaria de fora calado
            diz("aviso: testes/site/ tem arquivo .js, mas nenhum com nome de teste (x.test.js, test-x.js)")

    falhos = 0
    for comando, caminho in fila:
        passou, segundos, saida = roda(comando)
        diz("%-6s %6.1fs  %s" % ("ok" if passou else "falhou", segundos, relativo(caminho)))
        if not passou:
            falhos += 1
            for linha in saida.rstrip("\n").split("\n")[-LINHAS_DO_FIM:]:
                diz("    | " + linha)
    if falhos:
        diz("FALHA %d de %d arquivos de teste" % (falhos, len(fila)))
        return 1
    diz("OK %d arquivos de teste" % len(fila))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
