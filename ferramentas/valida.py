#!/usr/bin/env python3
"""valida.py: confere edição e dados do INFOCENARIUM. Nunca grava nada. Sem rede.

LINHA DE COMANDO (CONTRATO, seção 3). Um modo por chamada:

    python3 ferramentas/valida.py                           sem opção vale --tudo
    python3 ferramentas/valida.py --tudo [--base REF] [--dia D]
    python3 ferramentas/valida.py --dados
    python3 ferramentas/valida.py --edicao ARQ [--anterior ARQ]
    opções comuns: --raiz PASTA, --json

Saída: uma linha por problema, "ERRO REGRA caminho: problema. Conserto." ou "AVISO …", e a última
linha "OK 0 erros, N avisos" ou "FALHA N erros, M avisos". Código 0, 1 (erro) ou 2 (uso errado).
Em --tudo e em --dados o caminho começa com o nome do arquivo: "edicoes/2026-11-20.json:radar[2].confianca".

Códigos de regra: os do ESQUEMA (R00 a R23, H1 a H3, T1 a T5, G1 a G4, M1, M2, C1, C2, C5, C6) e sete
próprios, para o que o ESQUEMA manda conferir sem dar número: ARQUIVO (não deu para ler, ou arquivo de
nome estranho em edicoes/), DADOS (estrutura de dados/*.json), INDICE (edicoes/indice.json), MD (o .md
de cada edição), FEED (feed.xml), GIT (--base sem git, ou revisão que não existe) e AGENTE (arquivo que
dá ordem a agente de IA acompanhado pelo git, em --tudo e em --dados). A saída tem teto:
60 erros por arquivo e 300 por chamada; o que passa disso vira uma linha que diz quantos ficaram de fora.

Regras (dia): só valem para a edição do dia. São as que cruzam a edição com o que o dono revisa
depois: o mapa de veículos (R02 veículo, R03, R06, R07, R08, R11 no que pede fonte forte e 2 partidos,
R10 na força 3 do radar, R19 caso d, R22), o catálogo e os limiares de preço (R02 indicador, R13c, R13f,
e `defasado` e a variação de 7 dias de cada indicador contra a frequência do catálogo), as listas
`conflito` e `sites_oficiais` da régua (R19 casos b e c, R13b no site oficial do Brasil) e o
`voto_tipico` dos partidos (R11 no voto típico do tema, R20 no partido pela conta do dna).
A regra H3 também, e o prazo da primeira pergunta de vigiar (R21: até 30 dias da edição). Edição de arquivo é registro: não é conferida de novo contra esses dados.
Os ids da régua (partidos, temas, domínios, evidências, códigos de critério) e os registros que só crescem
(players.json e vetores.json) valem sempre (ESQUEMA, seção 10, princípio das regras do dia).

------------------------------------------------------------------------------------------------
BIBLIOTECA. O publica.py importa este módulo: `import valida`. Nenhuma função daqui grava em disco,
usa a rede ou lê o relógio. Só as de nome carrega*, le_json_do_repositorio e as de git leem o disco.
As outras recebem tudo já lido e devolvem valor novo: não mudam o que receberam. Nenhuma dá exceção
por dado torto: o que não dá para ler vira Achado.

Os tipos que circulam:

  Achado      um problema. Campos: gravidade ("ERRO" ou "AVISO"), regra, caminho, mensagem.
              .linha() dá a linha de saída; .objeto() dá {"regra", "caminho", "mensagem"} (o --json).
  Dados       os cinco arquivos de dados/, já em forma segura (os atributos estão na classe Dados).
  Historico   as edições já publicadas, por data. Histórico vazio é Historico(), e não None:
              None quer dizer "sem histórico à mão" e muda a conferência (regra H1).
  Repositorio o que carrega() devolve: dados, edições, índice e histórico de uma raiz.

O caminho do `publica.py edicao`, em cinco linhas:

    rep = valida.carrega(raiz)                      # rep.problemas não vazio: pare, os dados não servem
    edicao = valida.completa(rascunho, rep.dados, rep.historico, indicadores, coleta, comum.agora_texto())
    achados = valida.confere_edicao(edicao, rep.dados, rep.historico, do_dia=True, data_do_arquivo=dia)
    achados += valida.confere_trabalho(rascunho, rep.dados, dia, coleta, urls, conferencia, rep.historico)
    erros, avisos = valida.separa(achados)          # sem erro: grave `edicao` com comum.json_texto

E o do `publica.py contexto`: rep.historico.anterior(dia) e valida.alerta_anterior(rep.historico, dia,
rep.dados.dominios). O rep.historico pode conter a própria edição do dia (republicação): toda função
de histórico só olha para ANTES da data pedida.
Na republicação do mesmo dia, players.json e vetores.json já trazem o que a primeira publicação gravou
(player com incluido_em igual ao dia; vetor e anulação com data igual ao dia). A conferência aceita
isso como "o próprio registro" (regras R20 e H2). Para conferir contra o que vai ficar gravado, monte os
Dados com esses registros já limpos: valida.monta_dados(regua, players_limpo, veiculos, vetores_limpo,
catalogo), a partir de rep.dados.bruto.

1. CARREGAR
  carrega(raiz, com_edicoes=True) -> Repositorio
      Lê dados/*.json, edicoes/indice.json e todos os edicoes/AAAA-MM-DD.json. Campos do resultado:
      .raiz, .dados (Dados), .edicoes ({data: edição}, só as legíveis), .tamanhos ({data: bytes}),
      .ilegiveis (datas de edição que não deu para ler), .textos (datas que têm .md), .indice (o
      objeto, ou None), .tem_indice (o arquivo existe), .historico (Historico de .edicoes),
      .problemas (lista de Achado: o que não deu para ler) e .estranhos (avisos: arquivo de nome
      estranho em edicoes/). .dados_servem() diz se dá para conferir edição.
  carrega_dados(raiz) -> (Dados, [Achado])
  monta_dados(regua, players, veiculos, vetores, catalogo) -> Dados
      Dos objetos JSON já lidos (qualquer um pode ser None). Dados.problemas lista o que é fatal.
  le_json_do_repositorio(caminho, rotulo, limite=LIMITE_ARQUIVO) -> (objeto ou None, bytes, Achado ou None)
  le_urls(texto) -> [url]      o conteúdo de urls.txt: uma URL por linha; linha com # é comentário.

2. CALCULAR (os campos de origem publica, indicadores, mapa e misto do ESQUEMA)
  completa(rascunho, dados, historico, indicadores=None, coleta=None, gerada_em=None) -> edição
      Faz o passo 4 do CONTRATO, seção 4.2, de uma vez: versao, gerada_em, lado de cada ataque,
      indicadores e gatilhos de preço (copiados de `indicadores`, o objeto de indicadores.json, ou
      None), sem_preco, níveis, tendências e desde, conflito_de_interesse (liga, nunca desliga),
      saldo, narrativa e ordem do placar_do_dia, e os três contadores de bastidores (de `coleta`, o
      objeto de coleta.json, ou None). Devolve edição nova, com as chaves na ordem do ESQUEMA. Campo
      calculado que veio no rascunho é trocado, e gatilho com ref de indicador também. Serve à edição
      de falha (estado "falha": níveis e desde da anterior, sem gatilho de preço). Rascunho torto não
      dá exceção: o que não dá para calcular fica como veio, e o confere_edicao acusa.
  normaliza(edicao, dados=None) -> edição    as mesmas chaves, na ordem das tabelas do ESQUEMA.
  As peças, uma por campo:
  lado_do_veiculo(dados, veiculo) -> id de partido ou None                              (regra R03)
  calcula_sem_preco(dados, dominio, indicadores) -> [id de indicador]                   (regra R13f)
  calcula_gatilhos_de_preco(dados, indicadores, data) -> {dominio: {indicador: nivel}}  (regra R13c)
  calcula_alerta(dados, edicao, historico, do_dia=True) -> {"nivel", "tendencia", "dominios": [
      {"id", "nivel", "tendencia", "desde", "sem_preco"}]}                              (R13, R14, R15)
  calcula_conflito(dados, item, do_dia=True) -> (bool, [casos "a", "b", "c", "d"])      (regra R19)
  calcula_placar_do_dia(dados, edicao) -> [{"partido", "saldo", "narrativa"}], já em ordem   (R12)
  calcula_veiculos_consultados(edicao) -> inteiro                                       (regra R12)
  calcula_feeds(coleta) -> (feeds_ok, feeds_falhos)
  teto_de_confianca(dados, item) -> "alta", "media" ou "baixa"                          (regra R08)
  partido_pelo_dna(dados, dna) -> id de partido                                         (regra R20)
  prazo_do_vigiar(pergunta, data_da_edicao) -> data ou None    a última DD/MM da pergunta (R21)
  monta_indice(edicoes) -> o objeto de edicoes/indice.json     (ESQUEMA, seção 11; edicoes: {data: edição})

3. HISTÓRICO (o validador e o `publica.py contexto` usam os mesmos números)
  Historico(edicoes, completo=True)     edicoes: {data: edição}, com a data do nome do arquivo.
      .anterior(data) -> resumo da edição anterior (a mais recente antes de `data` que não é falha
          nem exemplo), ou None. Campos do resumo: .data, .estado, .nivel_geral, .niveis
          ({dominio: nivel}), .desde ({dominio: data}), .cegas (domínios com sem_preco não vazia),
          .gatilhos ({dominio: [{"criterio", "nivel", "tipo", "texto"}]}) e .edicao (o objeto inteiro).
      .antes(data) -> os resumos que valem como anterior, do mais novo ao mais velho.
      .edicao(data) -> a edição dessa data, ou None.      .datas -> as datas, em ordem.
  nivel_anterior(historico, dominio, data) -> o N da regra R13 (1 se não há anterior)
  edicoes_sem_gatilho(historico, dominio, data) -> o S da regra R13
  origem_do_nivel(historico, dominio, data) -> {"edicao", "criterio", "texto"} mais "preco": True ou
      "alivio": True quando for o caso; None no nível 1
  alerta_anterior(historico, data, dominios) -> o objeto alerta_anterior do contexto.json (CONTRATO,
      seção 4.1), com nivel e, por domínio: id, nivel, desde, edicoes_sem_gatilho,
      desce_hoje_sem_gatilho e origem. `dominios` é dados.dominios.
  vetores_anulados(dados) -> {id do vetor: data da anulação}

4. CONFERIR (cada função devolve a lista de Achado; lista sem ERRO quer dizer que passou)
  confere_edicao(edicao, dados, historico=None, do_dia=True, data_do_arquivo=None, tamanho=None, arquivo="")
      Regras R e H numa edição COMPLETA (depois de completa()). `historico=None` é "sem histórico"
      (regra H1: aceita nível mantido, não confere tendência, recusa alívio; H2 e H3 não rodam).
      `do_dia=False` deixa de fora as regras (dia). `data_do_arquivo` é a data do nome do arquivo (R01).
      `tamanho` é o tamanho em bytes (R17); sem ele, mede o JSON que o publica.py gravaria.
      `arquivo` entra na frente do caminho de cada achado.
  confere_trabalho(edicao, dados, dia, coleta=None, urls=None, conferencia=None, historico=None)
      Regras T1 a T5 (só o publica.py edicao usa). `coleta` e `conferencia` são os objetos JSON já
      lidos, ou None se o arquivo não existe. `urls` é o texto de urls.txt, ou a lista, ou None.
      As cinco também existem soltas, com a mesma leitura dos argumentos:
      confere_t1(edicao, coleta=None, urls=None)        URL vista
      confere_t2(edicao, dia)                           data do dia; sem exemplo e sem estado falha
      confere_t3(edicao, dados, coleta=None, conferencia=None, historico=None)   data conferida pela máquina
      confere_t4(edicao, dados, coleta=None)            veículo e endereço (pelo site; `coleta` não é lida)
      confere_t5(edicao, urls=None)                     omite só de página aberta
  confere_dados(dados, indice=None, existe=None) -> o modo --dados (régua, players, mapa M1 e M2,
      vetores, catálogo C1, C2, C5 e C6, e a forma do índice). `existe(caminho relativo)` diz se o arquivo existe.
  confere_indice(indice, edicoes=None, existe=None)     forma do índice e, com `edicoes`, índice igual aos arquivos
  confere_feed(bruto) -> feed.xml bem formado e só com Atom (CONTRATO, seção 4.5); `bruto` em bytes
  confere_crescimento(raiz, base) -> regras G1 a G4, pelo git
  confere_agente(raiz) -> regra AGENTE, pelo git (git ls-files): CLAUDE.md, CLAUDE.local.md, AGENTS.md,
      .mcp.json, opencode.json, opencode.jsonc ou arquivo em .claude/ ou .opencode/ (salvo .claude/settings.json
      só com attribution). Sem git: nada.
  confere_tudo(raiz, dia, base=None) -> o modo --tudo inteiro
  confere_texto(valor, maximo=None, so_algarismos=False, opcional=False) -> [mensagem]
      a regra R17 num texto solto (serve ao --motivo do publica.py falha)

5. APOIO
  separa(achados) -> (erros, avisos)        veredito(achados) -> a última linha da saída
  abre_git(raiz) -> (Git ou None, motivo)   só há git quando a raiz do repositório git é a própria raiz.
      Git.revisao(ref) -> identificador do commit ou None; Git.conteudo(revisao, caminho) -> bytes ou
      None (serve para saber se edicoes/DIA.json já está no commit HEAD: CONTRATO, seção 4.2, passo 3).
  principal(argv) -> código de saída: a linha de comando.
  Tabelas: ORDEM (chaves de cada objeto, na ordem do ESQUEMA), OPCIONAIS, CALCULADOS (o que o agente
      não escreve), MAXIMOS (tamanho de cada texto), TEMAS_ATUAIS, LIMITE_EDICAO e as listas fechadas
      (ESTADOS, CATEGORIAS, TENDENCIAS, CONFIANCAS, RESPOSTAS, MODOS, LEITORES…).
"""
# --- guarda de versão: início ---
import os
import sys

if sys.version_info < (3, 10):
    print("FALHA interna: Python 3.10 ou mais novo")
    sys.exit(1)
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# --- guarda de versão: fim ---

import bisect  # noqa: E402
import difflib  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import re  # noqa: E402
import stat  # noqa: E402
import subprocess  # noqa: E402
import unicodedata  # noqa: E402
import xml.etree.ElementTree as ET  # noqa: E402
from collections import OrderedDict  # noqa: E402

import comum  # noqa: E402

ERRO, AVISO = "ERRO", "AVISO"

# ---------------------------------------------------------------- listas fechadas (ESQUEMA, seção 0)

ESTADOS = ("completa", "reduzida", "falha")
CATEGORIAS = ("geopolitica", "ia")
TENDENCIAS = ("subindo", "estavel", "descendo")
EFEITOS = ("ganha", "perde")
CONFIANCAS = ("baixa", "media", "alta")  # em ordem crescente: o índice serve de comparação
SENTIDOS = ("azul", "vermelho")
RESPOSTAS = ("sim", "nao", "sem_dado")
MODOS = ("feeds", "busca")
TEMAS_ATUAIS = ("pandemia_depois", "ia_depois", "moderacao", "clima", "imigracao")
TIPOS_DE_PLAYER_NOVO = ("governo", "instituicao", "empresa")  # a rotina não usa "regime" (regra R20)
TIPOS_DE_VEICULO = ("agencia", "estatal", "publico", "privado", "plataforma", "oficial", "think_tank", "dados")
TIPOS_PRIMARIOS = ("oficial", "dados")  # só estes podem ser fonte primária (regra R22)
ORIGENS_DE_PLAYER = ("regua", "rotina")
FREQUENCIAS = ("diaria", "mensal")
LEITORES = ("fred_csv", "yahoo_chart", "bcb_sgs", "eia_v2", "fao_csv", "cnbc_chart")
LETRAS_DOS_MESES = "FGHJKMNQUVXZ"  # janeiro a dezembro, no campo contratos do catálogo (regra C6)
JANELAS = ("1d", "7d")
DOMINIOS_DO_BRASIL = ("energia", "alimentos", "cambio", "suprimentos")  # nível 5: fonte primária do Brasil (R13b)
ALVOS_ESPECIAIS = ("outro", "nenhum")
ESTADOS_DE_PAGINA = ("ok", "bloqueada", "erro")

LIMITE_EDICAO = 60 * 1024  # bytes de uma edição (regra R17)
LIMITE_ARQUIVO = 2000000  # bytes que o validador aceita ler de um arquivo: o mesmo teto do workflow de publicação
REALMENTE_MINIMO, REALMENTE_MAXIMO = 800, 1500  # regra R23
DIAS_DO_PRAZO = 30  # regra R21 (dia): o prazo da primeira pergunta de vigiar vai até 30 dias depois da edição
TETO_DE_ACHADOS = 60  # por arquivo: depois disso, uma linha só diz quantos ficaram de fora
TETO_DA_SAIDA = 300  # linhas de erro (e de aviso) de uma chamada inteira
TEMPO_DO_GIT = 30  # segundos por comando do git
NS_ATOM = "http://www.w3.org/2005/Atom"

# Chaves de cada objeto da edição, na ordem das tabelas do ESQUEMA (seções 1 a 9).
ORDEM = {
    "raiz": ("versao", "data", "gerada_em", "estado", "exemplo", "resumo", "alerta", "indicadores",
             "principais", "radar", "placar_do_dia", "novos_players", "errata", "respostas", "bastidores"),
    "alerta": ("nivel", "tendencia", "motivo", "dominios"),
    "dominio": ("id", "nivel", "tendencia", "desde", "sem_preco", "gatilhos", "leitura", "vigiar"),
    "gatilho": ("criterio", "ref", "texto", "excecao", "alivio"),
    "indicador": ("id", "nome", "dominio", "valor", "unidade", "variacao_pct", "variacao_7d_pct",
                  "data", "defasado", "confirmado", "fonte"),
    "fonte_indicador": ("nome", "url"),
    "principal": ("id", "categoria", "titulo", "fato", "nao_confirmado", "ataques", "realmente",
                  "na_pratica", "no_brasil", "eixo", "placar", "sem_placar", "vetores", "dominios",
                  "vigiar", "confianca", "conflito_de_interesse", "continuacao_de", "fontes"),
    "radar": ("id", "categoria", "titulo", "fato", "ataque", "eixo", "placar", "sem_placar", "vetores",
              "dominios", "confianca", "conflito_de_interesse", "continuacao_de", "fontes"),
    "ataque": ("veiculo", "lado", "alvo", "alvo_nome", "enquadramento", "omite", "url"),
    "eixo": ("tema", "sentido", "porque"),
    "placar": ("partido", "efeito", "forca", "evidencia", "porque"),
    "vetor": ("player", "para", "forca", "tema", "porque", "url"),
    "fonte": ("veiculo", "nome", "titulo", "url", "publicado_em", "primaria"),
    "placar_do_dia": ("partido", "saldo", "narrativa", "frase"),
    "novo_player": ("id", "nome", "tipo", "partido", "time", "time_discutivel", "dna", "dna_fontes",
                    "duvidas", "nota", "justificativa", "url"),
    "errata": ("edicao", "item", "erro", "correcao", "url", "anula_vetor"),
    "resposta": ("edicao", "item", "pergunta", "resposta", "texto", "url"),
    "bastidores": ("modo", "veiculos_consultados", "feeds_ok", "feeds_falhos", "paginas_lidas", "buscas",
                   "minutos", "injecoes_ignoradas", "candidatos", "veiculos_sugeridos", "limites"),
    "candidato": ("id", "nome", "motivo"),
}
# Campos que podem faltar: os opcionais e os condicionais ("só se …") das tabelas.
OPCIONAIS = {
    "raiz": ("exemplo",),
    "gatilho": ("excecao", "alivio"),
    "principal": ("nao_confirmado", "no_brasil", "eixo", "sem_placar", "conflito_de_interesse", "continuacao_de"),
    "radar": ("eixo", "sem_placar", "conflito_de_interesse", "continuacao_de"),
    "ataque": ("alvo_nome", "omite"),
    "fonte": ("nome", "primaria"),
    "errata": ("item", "url", "anula_vetor"),
    "resposta": ("url",),
}
# Campos que o agente não escreve (coluna "Vem de": publica, indicadores ou mapa). O completa() os preenche.
CALCULADOS = {
    "raiz": ("versao", "gerada_em", "indicadores"),
    "alerta": ("nivel", "tendencia"),
    "dominio": ("nivel", "tendencia", "desde", "sem_preco"),
    "ataque": ("lado",),
    "placar_do_dia": ("saldo", "narrativa"),
    "bastidores": ("veiculos_consultados", "feeds_ok", "feeds_falhos"),
}
# Tamanho máximo, em caracteres, de cada campo de texto (coluna "Máx." das tabelas).
MAXIMOS = {
    ("raiz", "resumo"): 240,
    ("alerta", "motivo"): 400,
    ("dominio", "leitura"): 300, ("dominio", "vigiar"): 200,
    ("gatilho", "texto"): 200,
    ("indicador", "nome"): 60, ("indicador", "unidade"): 30, ("fonte_indicador", "nome"): 60,
    ("principal", "titulo"): 120, ("principal", "fato"): 500, ("principal", "nao_confirmado"): 240,
    ("principal", "realmente"): REALMENTE_MAXIMO, ("principal", "na_pratica"): 200,
    ("principal", "no_brasil"): 240, ("principal", "sem_placar"): 160, ("principal", "vigiar"): 200,
    ("radar", "titulo"): 120, ("radar", "fato"): 300, ("radar", "sem_placar"): 160,
    ("ataque", "alvo_nome"): 60, ("ataque", "enquadramento"): 240, ("ataque", "omite"): 200,
    ("eixo", "porque"): 160, ("placar", "porque"): 200, ("vetor", "porque"): 240,
    ("fonte", "nome"): 80, ("fonte", "titulo"): 200,
    ("placar_do_dia", "frase"): 160,
    ("novo_player", "nome"): 60, ("novo_player", "nota"): 200, ("novo_player", "justificativa"): 400,
    ("errata", "erro"): 300, ("errata", "correcao"): 300, ("errata", "anula_vetor"): 60,
    ("resposta", "pergunta"): 200, ("resposta", "texto"): 240,
    ("bastidores", "veiculos_sugeridos"): 80, ("bastidores", "limites"): 500,
    ("candidato", "nome"): 60, ("candidato", "motivo"): 160,
}

_FALTA = object()
_ORDEM_DA_CONFIANCA = dict((nome, indice) for indice, nome in enumerate(CONFIANCAS))

_RE_SLUG = re.compile(r"[a-z][a-z0-9_]{1,30}")
_RE_ID_DE_ITEM = re.compile(r"p[1-3]|r(?:[1-9]|1[0-2])")
_RE_ID_DE_PRINCIPAL = re.compile(r"p[1-3]")
_RE_CONTINUACAO = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2})/(p[1-3]|r(?:[1-9]|1[0-2]))")
_RE_CRITERIO = re.compile(r"([a-z][a-z0-9_]*)\.([1-5])")
_RE_NOME_DE_EDICAO = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2})\.(json|md)")
_RE_DIA_MES = re.compile(r"(?<![0-9/])([0-9]{2})/([0-9]{2})(?![0-9/])")
_RE_SITE = re.compile(r"[a-z0-9-]+(?:\.[a-z0-9-]+)+")
_RE_SUGERIDO = re.compile(r"\S.* \([a-z0-9-]+(?:\.[a-z0-9-]+)+\)")
_RE_BRANCO_DE_HREF = re.compile(r"[\x00-\x20\x7f]")
_RE_ID_DE_ANULACAO = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2})_anula_([1-9][0-9]{0,2})")

# Regra R17. Os trechos de caminho de computador são montados em pedaços para este arquivo não trazer um.
_BARRA = "/"
_CAMINHOS_DE_COMPUTADOR = (_BARRA + "home" + _BARRA, _BARRA + "Users" + _BARRA, "C:" + "\\")
# Controle: os caracteres C0 e C1 do Unicode e os dois separadores de linha (U+2028 e U+2029), que quebram
# a linha do mesmo jeito. Os separadores entram por chr() para o arquivo não trazer caractere invisível.
_SEPARADORES = chr(0x2028) + chr(0x2029)
_CONTROLES = "\x00-\x1f\x7f-\x9f" + _SEPARADORES
_RE_CONTROLE = re.compile("[" + _CONTROLES + "]")
# Metade solta de par substituto (U+D800 a U+DFFF): o JSON a lê, mas o texto não se grava em UTF-8.
_SUBSTITUTOS = chr(0xD800) + "-" + chr(0xDFFF)
_RE_SUBSTITUTO = re.compile("[" + _SUBSTITUTOS + "]")
# Marcas que reordenam o texto (U+202A a U+202E e U+2066 a U+2069): fazem o leitor ver as letras em outra
# ordem, e podem esconder um termo. Entram por chr(), como os separadores. As marcas simples de direção
# (U+200E, U+200F) e o ZWJ (U+200D) ficam: aparecem em título árabe e em emoji.
_DIRECAO = chr(0x202A) + "-" + chr(0x202E) + chr(0x2066) + "-" + chr(0x2069)
_RE_DIRECAO = re.compile("[" + _DIRECAO + "]")
_RE_HTML = re.compile(r"<[A-Za-z/]")
_RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# "http" só conta seguido de dois-pontos: "HTTP 403", o erro que a coleta grava, não é endereço.
_RE_ENDERECO = re.compile(r"https?:|www\.|://|\]\(|!\[", re.I)
_RE_CPF = re.compile(r"(?<![0-9])[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2}(?![0-9])")
_RE_TELEFONE = re.compile(r"\([0-9]{2}\)\s?[0-9]{4,5}-[0-9]{4}|\+(?:[\s().-]*[0-9]){10,}")
_RE_SO_ALGARISMOS = re.compile(r"\s*[0-9]+\s*")
# Peneira rápida: quase todo texto passa por ela sem mais nenhuma conta.
_RE_SUSPEITO = re.compile(
    "[<@" + _CONTROLES + _SUBSTITUTOS + _DIRECAO + "]|https?:|www\\.|://|\\]\\(|!\\[|" + "|".join(
        re.escape(trecho) for trecho in _CAMINHOS_DE_COMPUTADOR)
    + "|[0-9]{3}\\.[0-9]{3}\\.[0-9]{3}-[0-9]{2}|\\([0-9]{2}\\)|\\+[\\s().-]*[0-9]", re.I)
_NOMES_DE_CONTROLE = {"\n": "quebra de linha", "\r": "quebra de linha", "\t": "tabulação",
                      chr(0x2028): "quebra de linha", chr(0x2029): "quebra de parágrafo"}


# ---------------------------------------------------------------- achados

class Achado(object):
    """Um problema achado: gravidade ("ERRO" ou "AVISO"), regra, caminho do campo e mensagem (problema e conserto)."""

    __slots__ = ("gravidade", "regra", "caminho", "mensagem")

    def __init__(self, gravidade, regra, caminho, mensagem):
        self.gravidade = gravidade
        self.regra = regra
        self.caminho = _uma_linha(caminho) or "?"  # nome de arquivo também pode trazer quebra de linha
        self.mensagem = _uma_linha(mensagem)

    def linha(self):
        return "%s %s %s: %s" % (self.gravidade, self.regra, self.caminho, self.mensagem)

    def objeto(self):
        return OrderedDict((("regra", self.regra), ("caminho", self.caminho), ("mensagem", self.mensagem)))

    def __repr__(self):
        return "Achado(%r)" % self.linha()

    def __eq__(self, outro):
        return isinstance(outro, Achado) and self.linha() == outro.linha()

    def __ne__(self, outro):
        return not self == outro

    def __hash__(self):
        return hash(self.linha())


class _Achados(object):
    """Junta os achados de um arquivo. O nome do arquivo, se houver, entra na frente de cada caminho."""

    def __init__(self, arquivo=""):
        self.arquivo = arquivo
        self.lista = []

    def caminho(self, campo):
        if not self.arquivo:
            return campo or "edicao"
        return self.arquivo + (":" + campo if campo else "")

    def erro(self, regra, campo, mensagem):
        self.lista.append(Achado(ERRO, regra, self.caminho(campo), mensagem))

    def aviso(self, regra, campo, mensagem):
        self.lista.append(Achado(AVISO, regra, self.caminho(campo), mensagem))

    def fecha(self):
        """A lista, cortada no teto: arquivo todo torto não despeja mil linhas em quem lê com pressa."""
        erros = [a for a in self.lista if a.gravidade == ERRO]
        if len(erros) <= TETO_DE_ACHADOS:
            return list(self.lista)
        resto = len(erros) - TETO_DE_ACHADOS
        mantidos, vistos = [], 0
        for achado in self.lista:
            if achado.gravidade == ERRO:
                vistos += 1
                if vistos > TETO_DE_ACHADOS:
                    continue
            mantidos.append(achado)
        mantidos.append(Achado(ERRO, "R00", self.caminho(""),
                               "há mais %d erros neste arquivo, que não foram listados. Conserte os de cima e "
                               "confira de novo." % resto))
        return mantidos


def separa(achados):
    """(erros, avisos), cada lista na ordem em que os achados vieram."""
    return ([a for a in achados if a.gravidade == ERRO], [a for a in achados if a.gravidade != ERRO])


def _corta(achados, gravidade, teto=TETO_DA_SAIDA):
    """A lista cortada no teto da saída, com uma linha no fim dizendo quantos ficaram de fora."""
    if len(achados) <= teto:
        return achados
    o_que = "erros" if gravidade == ERRO else "avisos"
    return achados[:teto] + [Achado(gravidade, "ARQUIVO", "saida", "há mais %d %s, que não foram listados. Conserte "
                                    "os de cima e confira de novo." % (len(achados) - teto, o_que))]


def _conta(quantos, singular, plural):
    return "%d %s" % (quantos, singular if quantos == 1 else plural)


def veredito(achados):
    """A última linha da saída: "OK 0 erros, N avisos" ou "FALHA N erros, M avisos" (CONTRATO, seção 3)."""
    erros, avisos = separa(achados)
    return "%s %s, %s" % ("FALHA" if erros else "OK", _conta(len(erros), "erro", "erros"),
                          _conta(len(avisos), "aviso", "avisos"))


# ---------------------------------------------------------------- miudezas

def _uma_linha(texto):
    """Tudo numa linha só: valor copiado da edição pode trazer quebra de linha, e cada problema é uma linha."""
    return " ".join(_RE_CONTROLE.sub(" ", str(texto)).split())


def _mostra(valor, teto=60):
    """Um valor da edição, curto e numa linha, para caber na mensagem."""
    if isinstance(valor, str):
        texto = _uma_linha(valor)
        return "'%s'" % (texto if len(texto) <= teto else texto[:teto - 1] + "…")
    if valor is None:
        return "null"
    if valor is True:
        return "true"
    if valor is False:
        return "false"
    if isinstance(valor, (int, float)):
        return repr(valor)
    if isinstance(valor, (list, tuple, set, frozenset)):
        partes = ", ".join(_mostra(v, 24) for v in list(valor)[:8])
        texto = "[%s%s]" % (partes, ", …" if len(valor) > 8 else "")
    elif isinstance(valor, dict):
        texto = "{%s%s}" % (", ".join(_mostra(k, 24) for k in list(valor)[:6]), ", …" if len(valor) > 6 else "")
    else:
        texto = _uma_linha(repr(valor))
    return texto if len(texto) <= 2 * teto else texto[:2 * teto - 1] + "…"


def _nome_do_tipo(valor):
    if valor is None:
        return "null"
    if isinstance(valor, bool):
        return "booleano"
    if isinstance(valor, (int, float)):
        return "número"
    if isinstance(valor, str):
        return "texto"
    if isinstance(valor, list):
        return "lista"
    if isinstance(valor, dict):
        return "objeto"
    return type(valor).__name__


def _e_inteiro(valor):
    return isinstance(valor, int) and not isinstance(valor, bool)


def _e_numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool) and math.isfinite(valor)


def _e_data(valor):
    return isinstance(valor, str) and comum.data_valida(valor)


def _lista_de_objetos(valor):
    """Os itens que são objeto, de um valor que deveria ser lista de objetos. O resto fica de fora, sem erro aqui."""
    return [v for v in valor if isinstance(v, dict)] if isinstance(valor, list) else []


def _textos_da_lista(valor):
    return [v for v in valor if isinstance(v, str)] if isinstance(valor, list) else []


def _lista_em_texto(itens):
    itens = [str(i) for i in itens]
    return ", ".join(itens) if itens else "nenhum"


def _limpo(url):
    """A chave de comparação de uma URL (ESQUEMA, seção 0, "endereço limpo"). Valor que não é texto dá None."""
    return comum.endereco_limpo(url) if isinstance(url, str) and url else None


def _igual_em_json(a, b):
    """Igualdade pelo texto JSON: em Python 1 == True == 1.0, e num registro isso não pode passar por igual."""
    try:
        return _json_canonico(a) == _json_canonico(b)
    except (TypeError, ValueError):
        return False


def _json_canonico(valor):
    return json.dumps(valor, sort_keys=True, ensure_ascii=True, allow_nan=False)


def confere_texto(valor, maximo=None, so_algarismos=False, opcional=False):
    """A regra R17 num texto. Devolve a lista de mensagens (problema e conserto); vazia se o texto passa.

    `so_algarismos=True` aceita texto feito só de algarismos (vale para o título de fonte).
    `opcional=True` muda o conserto do texto vazio: o campo pode sair."""
    if not isinstance(valor, str):
        return ["deveria ser texto, e é %s (%s). Escreva o texto entre aspas." % (_nome_do_tipo(valor), _mostra(valor))]
    problemas = []
    if not valor.strip():
        return ["texto vazio. %s" % ("Escreva o conteúdo, ou tire o campo, que é opcional." if opcional
                                    else "Escreva o conteúdo: este campo nunca fica vazio.")]
    if maximo is not None and len(valor) > maximo:
        problemas.append("tem %d caracteres, o máximo é %d. Corte %d." % (len(valor), maximo, len(valor) - maximo))
    if not so_algarismos and _RE_SO_ALGARISMOS.fullmatch(valor):
        problemas.append("é só o número %s: sobra do modelo.txt. Escreva o texto de verdade." % _mostra(valor))
    if not _RE_SUSPEITO.search(valor):
        return problemas
    achado = _RE_CONTROLE.search(valor)
    if achado:
        nome = _NOMES_DE_CONTROLE.get(achado.group(), "código %d" % ord(achado.group()))
        problemas.append("traz caractere de controle (%s, na posição %d). Texto é corrido, numa linha só: troque "
                         "por espaço." % (nome, achado.start() + 1))
    achado = _RE_DIRECAO.search(valor)
    if achado:
        problemas.append("traz marca de direção de texto (código %x, na posição %d), que muda a ordem do que o "
                         "leitor vê. Tire." % (ord(achado.group()), achado.start() + 1))
    achado = _RE_SUBSTITUTO.search(valor)
    if achado:
        problemas.append("traz metade solta de um caractere (código %x, na posição %d; de d800 a dfff, como o de "
                         "um emoji escrito pela metade), que não dá para gravar. Escreva o caractere direto, ou "
                         "tire." % (ord(achado.group()), achado.start() + 1))
    achado = _RE_HTML.search(valor)
    if achado:
        problemas.append("traz marca de HTML (%s). Tire: o texto é puro, sem marcação."
                         % _mostra(valor[achado.start():achado.start() + 12]))
    achado = _RE_EMAIL.search(valor)
    if achado:
        problemas.append("traz e-mail (%s). Tire: o INFOCENARIUM não publica e-mail." % _mostra(achado.group()))
    for trecho in _CAMINHOS_DE_COMPUTADOR:
        if trecho in valor:
            problemas.append("traz caminho de computador (%s). Tire." % _mostra(trecho))
            break
    achado = _RE_ENDERECO.search(valor)
    if achado:
        problemas.append("traz endereço ou marca de link (%s) fora de campo url. Tire do texto: endereço só entra "
                         "em campo url." % _mostra(achado.group()))
    achado = _RE_CPF.search(valor)
    if achado:
        problemas.append("traz número com forma de CPF (%s). Tire: o INFOCENARIUM não publica documento."
                         % _mostra(achado.group()))
    achado = _RE_TELEFONE.search(valor)
    if achado:
        problemas.append("traz número com forma de telefone (%s). Tire: o INFOCENARIUM não publica telefone."
                         % _mostra(achado.group()))
    return problemas


def le_urls(texto):
    """O conteúdo de urls.txt: uma URL por linha; linha vazia e linha que começa com # ficam de fora.

    Aceita o texto do arquivo, uma lista de linhas, ou None (arquivo que não existe: lista vazia)."""
    if isinstance(texto, str):
        linhas = texto.splitlines()
    else:
        linhas = list(texto) if isinstance(texto, (list, tuple)) else []
    urls = []
    for linha in linhas:
        linha = linha.strip() if isinstance(linha, str) else ""
        if linha and not linha.startswith("#"):
            urls.append(linha)
    return urls


def _datas_dd_mm(texto):
    """As datas DD/MM de um texto que existem no calendário, na ordem: [(dia, mês)]. 29/02 conta."""
    if not isinstance(texto, str):
        return []
    achadas = [(int(dia), int(mes)) for dia, mes in _RE_DIA_MES.findall(texto)]
    return [(dia, mes) for dia, mes in achadas if _dia_existe(2024, mes, dia)]  # 2024 é bissexto


def prazo_do_vigiar(pergunta, data_da_edicao):
    """O prazo de uma pergunta de `vigiar`: a última data DD/MM do texto, lida como o primeiro dia assim a
    partir da edição que perguntou (CONTRATO, seção 4.1). Devolve AAAA-MM-DD, ou None se o texto não traz
    data DD/MM que exista no calendário, ou se `data_da_edicao` não é data. É a mesma leitura da regra R21."""
    achadas = _datas_dd_mm(pergunta)
    if not achadas or not _e_data(data_da_edicao):
        return None
    dia, mes = achadas[-1]
    ano = int(data_da_edicao[:4])
    for tentativa in range(ano, ano + 9):  # 29/02 pode demorar até o próximo ano bissexto
        if _dia_existe(tentativa, mes, dia):
            texto = "%04d-%02d-%02d" % (tentativa, mes, dia)
            if texto >= data_da_edicao:
                return texto
    return None


def _dia_existe(ano, mes, dia):
    return 1 <= mes <= 12 and 1 <= dia <= 31 and comum.data_valida("%04d-%02d-%02d" % (ano, mes, dia))


# ---------------------------------------------------------------- dados (carregar)

ARQUIVOS_DE_DADOS = ("regua", "players", "veiculos", "vetores", "indicadores")
# O que cada arquivo precisa ter para as regras da edição fazerem sentido. Sem isso, nem se confere edição.
_LISTAS_ESSENCIAIS = (
    ("regua", ("temas", "partidos", "dominios", "niveis_alerta", "campos", "evidencias", "forcas")),
    ("players", ("players",)), ("veiculos", ("veiculos",)), ("vetores", ("vetores",)),
    ("indicadores", ("indicadores",)))
_OBJETOS_ESSENCIAIS = (("regua", ("conflito", "sites_oficiais")),)


class Dados(object):
    """Os dados de dados/*.json, já lidos e postos em forma segura: quem usa não precisa conferir tipo.
    É para leitura: depois de montado, não se mexe nele (para outro conteúdo, monte outro com monta_dados).

    .bruto        {"regua", "players", "veiculos", "vetores", "indicadores"}: os objetos como estão nos arquivos
    .problemas    lista de Achado: o que impede de usar os dados (arquivo que não é objeto, lista que falta)
    Da régua:
    .partidos     ids, na ordem da régua           .temas, .dominios, .evidencias, .times, .tipos, .campos: idem
    .forcas       [1, 2, 3]                        .letras: as letras do DNA ("B", "Y", "R", "W", "K")
    .voto         {partido: {tema: letra}}         o voto típico; partido sem voto típico tem {}
    .campo_de     {partido: id do campo}
    .codigos      {"energia.3": ("energia", 3)}    os códigos dos critérios de alerta
    .precos       {dominio: [(nivel, indicador, janela, alta_minima_pct)]}
    .rotulos      {nivel: rótulo}
    .conflito_players (conjunto), .conflito_termos (lista), .re_termos (expressão regular, ou None)
    .oficiais_brasil, .oficiais    sufixos de site oficial: os do Brasil, e os do Brasil mais os outros
    De players.json:  .players   {id: player, como está no arquivo}
    Do mapa:          .mapa      {id: {"id", "nome", "tipo", "lado", "lado_confianca", "fatos", "serve_a",
                                 "alvos", "sites"}}; valor de tipo errado vira None (ou lista vazia)
                      .revisado_em, .ligados (ids de veículo com anthropic em serve_a ou em alvos)
    De vetores.json:  .vetores   as entradas (vetores e anulações), na ordem do arquivo
    Do catálogo:      .catalogo  ids dos indicadores, na ordem; .indicador {id: indicador}
    Métodos: .partido_do_player(id), .posicao_do_partido(id) e .registro_de_vetores().
    """

    def __init__(self):
        self.bruto = OrderedDict((nome, None) for nome in ARQUIVOS_DE_DADOS)
        self.problemas = []
        self.partidos, self.temas, self.dominios = [], [], []
        self.evidencias, self.times, self.tipos, self.campos = [], [], [], []
        self.forcas, self.letras = [], []
        self.voto, self.campo_de, self.codigos, self.precos, self.rotulos = {}, {}, {}, {}, {}
        self.conflito_players, self.conflito_termos, self.re_termos = frozenset(), [], None
        self.oficiais_brasil, self.oficiais = [], []
        self.players = {}
        self.mapa, self.revisado_em, self.ligados = {}, None, frozenset()
        self.vetores = []
        self.catalogo, self.indicador = [], {}
        self._registro = None

    def registro_de_vetores(self):
        """({id: vetor}, [(id do vetor anulado, data da anulação)]) de dados/vetores.json. A conta é feita uma
        vez só: com centenas de edições, refazê-la a cada edição pesava."""
        if self._registro is None:
            vetores = dict((v["id"], v) for v in self.vetores if isinstance(v.get("id"), str) and "anula" not in v)
            anulacoes = [(v["anula"], v.get("data")) for v in self.vetores if isinstance(v.get("anula"), str)]
            self._registro = (vetores, anulacoes)
        return self._registro

    def partido_do_player(self, player):
        ficha = self.players.get(player) if isinstance(player, str) else None
        partido = ficha.get("partido") if ficha else None
        return partido if isinstance(partido, str) else None

    def posicao_do_partido(self, partido):
        """O lugar do partido na ordem da régua; partido de fora vai para o fim."""
        try:
            return self.partidos.index(partido)
        except ValueError:
            return len(self.partidos)


def _ids(valor):
    """Os ids (texto não vazio) dos objetos de uma lista, sem repetir, na ordem."""
    vistos, saida = set(), []
    for objeto in _lista_de_objetos(valor):
        identificador = objeto.get("id")
        if isinstance(identificador, str) and identificador and identificador not in vistos:
            vistos.add(identificador)
            saida.append(identificador)
    return saida


def _por_id(valor):
    """{id: objeto} de uma lista de objetos; se um id se repete, vale o primeiro."""
    saida = OrderedDict()
    for objeto in _lista_de_objetos(valor):
        identificador = objeto.get("id")
        if isinstance(identificador, str) and identificador and identificador not in saida:
            saida[identificador] = objeto
    return saida


def monta_dados(regua=None, players=None, veiculos=None, vetores=None, catalogo=None):
    """Monta o objeto Dados a partir dos cinco objetos JSON já lidos. Qualquer um pode ser None (não veio).

    Nunca dá exceção: valor de tipo errado vira o vazio do tipo certo. O que é fatal (arquivo que não é
    objeto, lista essencial que falta) fica em Dados.problemas; o resto é o confere_dados que acusa."""
    dados = Dados()
    dados.bruto = OrderedDict(zip(ARQUIVOS_DE_DADOS, (regua, players, veiculos, vetores, catalogo)))
    seguro = {}
    for nome in ARQUIVOS_DE_DADOS:
        objeto = dados.bruto[nome]
        seguro[nome] = objeto if isinstance(objeto, dict) else {}
        if objeto is not None and not isinstance(objeto, dict):
            dados.problemas.append(Achado(ERRO, "DADOS", "dados/%s.json" % nome,
                                          "deveria ser um objeto, e é %s. Recupere o arquivo do git."
                                          % _nome_do_tipo(objeto)))
    for tabela, tipo, nome_do_tipo in ((_LISTAS_ESSENCIAIS, list, "uma lista"), (_OBJETOS_ESSENCIAIS, dict, "um objeto")):
        for nome, chaves in tabela:
            if not isinstance(dados.bruto[nome], dict):
                continue
            for chave in chaves:
                if not isinstance(seguro[nome].get(chave), tipo):
                    dados.problemas.append(Achado(
                        ERRO, "DADOS", "dados/%s.json:%s" % (nome, chave),
                        "deveria ser %s, e %s. Sem isso não dá para conferir edição: recupere o arquivo do git."
                        % (nome_do_tipo, "falta" if chave not in seguro[nome]
                           else "é " + _nome_do_tipo(seguro[nome][chave]))))
    _monta_regua(dados, seguro["regua"])
    dados.players = _por_id(seguro["players"].get("players"))
    _monta_mapa(dados, seguro["veiculos"])
    dados.vetores = _lista_de_objetos(seguro["vetores"].get("vetores"))
    dados.indicador = _por_id(seguro["indicadores"].get("indicadores"))
    dados.catalogo = list(dados.indicador)
    return dados


def _monta_regua(dados, regua):
    dados.temas = _ids(regua.get("temas"))
    dados.partidos = _ids(regua.get("partidos"))
    dados.dominios = _ids(regua.get("dominios"))
    dados.evidencias = _ids(regua.get("evidencias"))
    dados.times = _ids(regua.get("times"))
    dados.tipos = _ids(regua.get("tipos"))
    dados.campos = _ids(regua.get("campos"))
    dados.forcas = [f["forca"] for f in _lista_de_objetos(regua.get("forcas")) if _e_inteiro(f.get("forca"))]
    valores = regua.get("valores")
    dados.letras = [letra for letra in valores if isinstance(letra, str)] if isinstance(valores, dict) else []
    for partido in _por_id(regua.get("partidos")).values():
        votos = partido.get("voto_tipico")
        votos = votos.split() if isinstance(votos, str) else []
        dados.voto[partido["id"]] = dict(zip(dados.temas, votos)) if len(votos) == len(dados.temas) else {}
    for campo in _por_id(regua.get("campos")).values():
        for partido in _textos_da_lista(campo.get("partidos")):
            dados.campo_de.setdefault(partido, campo["id"])
    for linha in _lista_de_objetos(regua.get("niveis_alerta")):
        nivel = linha.get("nivel")
        if not _e_inteiro(nivel) or not 1 <= nivel <= 5:
            continue
        if isinstance(linha.get("rotulo"), str):
            dados.rotulos.setdefault(nivel, linha["rotulo"])
        criterios = linha.get("criterios")
        for dominio, celula in (criterios.items() if isinstance(criterios, dict) else ()):
            if not isinstance(celula, dict):
                continue
            if isinstance(celula.get("codigo"), str):
                dados.codigos.setdefault(celula["codigo"], (dominio, nivel))
            for preco in _lista_de_objetos(celula.get("precos")):
                if (isinstance(preco.get("indicador"), str) and preco.get("janela") in JANELAS
                        and _e_numero(preco.get("alta_minima_pct"))):
                    dados.precos.setdefault(dominio, []).append(
                        (nivel, preco["indicador"], preco["janela"], preco["alta_minima_pct"]))
    conflito = regua.get("conflito") if isinstance(regua.get("conflito"), dict) else {}
    dados.conflito_players = frozenset(_textos_da_lista(conflito.get("players")))
    dados.conflito_termos = [t for t in _textos_da_lista(conflito.get("termos")) if t.strip()]
    if dados.conflito_termos:
        # Palavra inteira, escrita como na lista e sem hífen antes: "Jean-Claude" não conta (regra R19, caso c).
        dados.re_termos = re.compile(r"(?<![\w-])(?:%s)(?!\w)"
                                     % "|".join(re.escape(t) for t in dados.conflito_termos))
    oficiais = regua.get("sites_oficiais") if isinstance(regua.get("sites_oficiais"), dict) else {}
    dados.oficiais_brasil = [s for s in _textos_da_lista(oficiais.get("brasil")) if s]
    dados.oficiais = dados.oficiais_brasil + [s for s in _textos_da_lista(oficiais.get("outros")) if s]


def _monta_mapa(dados, veiculos):
    revisado = veiculos.get("revisado_em")
    dados.revisado_em = revisado if _e_data(revisado) else None
    ligados = set()
    for identificador, veiculo in _por_id(veiculos.get("veiculos")).items():
        ficha = {"id": identificador}
        for chave in ("nome", "tipo", "lado", "lado_confianca", "fatos"):
            ficha[chave] = veiculo.get(chave) if isinstance(veiculo.get(chave), str) else None
        for chave in ("serve_a", "alvos", "sites"):
            ficha[chave] = _textos_da_lista(veiculo.get(chave))
        dados.mapa[identificador] = ficha
        if "anthropic" in ficha["serve_a"] or "anthropic" in ficha["alvos"]:
            ligados.add(identificador)
    dados.ligados = frozenset(ligados)


def le_json_do_repositorio(caminho, rotulo, limite=LIMITE_ARQUIVO):
    """Lê um JSON do disco sem nunca dar exceção. Devolve (objeto, bytes, achado).

    Com problema, o objeto é None e o achado é um ERRO de regra ARQUIVO, com `rotulo` no caminho. Recusa
    arquivo que não existe, atalho (link simbólico), o que não é arquivo comum e arquivo maior que `limite`."""
    try:
        estado = os.lstat(caminho)
    except (FileNotFoundError, NotADirectoryError):
        return None, 0, Achado(ERRO, "ARQUIVO", rotulo, "o arquivo não existe. Confira o caminho; se é arquivo "
                               "do repositório, recupere-o do git.")
    except OSError as erro:
        return None, 0, Achado(ERRO, "ARQUIVO", rotulo, "não deu para ler (%s). Confira as permissões."
                               % type(erro).__name__)
    if stat.S_ISLNK(estado.st_mode):
        return None, 0, Achado(ERRO, "ARQUIVO", rotulo, "é um atalho (link simbólico), e o validador só lê "
                               "arquivo comum. Troque pelo arquivo de verdade.")
    if not stat.S_ISREG(estado.st_mode):
        return None, 0, Achado(ERRO, "ARQUIVO", rotulo, "não é um arquivo comum. Tire o que está nesse lugar "
                               "e recupere o arquivo do git.")
    if estado.st_size > limite:
        return None, estado.st_size, Achado(
            ERRO, "ARQUIVO", rotulo, "tem %d bytes, e o validador lê até %d. Arquivo desse tamanho não é do "
            "INFOCENARIUM: confira o que foi gravado nele." % (estado.st_size, limite))
    try:
        return comum.le_json(caminho), estado.st_size, None
    except comum.Falha as falha:
        motivo = str(falha)
        if motivo.startswith(caminho + ": "):
            motivo = motivo[len(caminho) + 2:]
        return None, estado.st_size, Achado(ERRO, "ARQUIVO", rotulo, "%s. Conserte o arquivo (aspas, vírgulas e "
                                            "chaves do JSON) e confira de novo." % motivo)


def carrega_dados(raiz):
    """Lê os cinco arquivos de dados/. Devolve (Dados, achados): os achados dizem o que não deu para usar."""
    achados, objetos = [], []
    for nome in ARQUIVOS_DE_DADOS:
        objeto, _, achado = le_json_do_repositorio(os.path.join(raiz, "dados", nome + ".json"),
                                                   "dados/%s.json" % nome)
        objetos.append(objeto)
        if achado:
            achados.append(achado)
        elif objeto is None:  # o arquivo traz só `null`: para o monta_dados, None quer dizer "não veio"
            achados.append(Achado(ERRO, "DADOS", "dados/%s.json" % nome, "deveria ser um objeto, e é null. "
                                  "Recupere o arquivo do git."))
    dados = monta_dados(*objetos)
    return dados, achados + dados.problemas


# ---------------------------------------------------------------- histórico

def _ids_dos_itens(edicao):
    """Os ids dos itens (principais e radar) de uma edição, do jeito que estão escritos."""
    ids = set()
    for chave in ("principais", "radar"):
        ids.update(_ids(edicao.get(chave)))
    return ids


class _Resumo(object):
    """O que as regras de histórico precisam de uma edição antiga, já em forma segura.

    .data, .edicao (o objeto inteiro), .estado, .exemplo, .vale (conta como edição anterior: nem falha, nem
    exemplo), .nivel_geral, .niveis {dominio: nivel}, .desde {dominio: data}, .cegas (domínios com sem_preco
    não vazia) e .gatilhos {dominio: [{"criterio", "nivel", "tipo", "texto"}]}, com tipo "evento", "preco"
    ou "alivio"."""

    __slots__ = ("data", "edicao", "estado", "exemplo", "vale", "nivel_geral", "niveis", "desde", "cegas",
                 "gatilhos")

    def __init__(self, data, edicao):
        self.data = data
        self.edicao = edicao if isinstance(edicao, dict) else {}
        estado = self.edicao.get("estado")
        self.estado = estado if isinstance(estado, str) else None
        self.exemplo = self.edicao.get("exemplo") is True
        self.vale = self.estado != "falha" and not self.exemplo
        self.niveis, self.desde, self.cegas, self.gatilhos = OrderedDict(), {}, set(), {}
        alerta = self.edicao.get("alerta")
        alerta = alerta if isinstance(alerta, dict) else {}
        itens = _ids_dos_itens(self.edicao)
        indicadores = set(_ids(self.edicao.get("indicadores")))
        for dominio in _lista_de_objetos(alerta.get("dominios")):
            identificador = dominio.get("id")
            if not isinstance(identificador, str) or identificador in self.niveis:
                continue
            nivel = dominio.get("nivel")
            self.niveis[identificador] = nivel if _e_inteiro(nivel) and 1 <= nivel <= 5 else 1
            if _e_data(dominio.get("desde")):
                self.desde[identificador] = dominio["desde"]
            if _textos_da_lista(dominio.get("sem_preco")):
                self.cegas.add(identificador)
            gatilhos = []
            for gatilho in _lista_de_objetos(dominio.get("gatilhos")):
                criterio = gatilho.get("criterio")
                lido = _RE_CRITERIO.fullmatch(criterio) if isinstance(criterio, str) else None
                if not lido or lido.group(1) != identificador or int(lido.group(2)) < 2:
                    continue
                gatilhos.append({"criterio": criterio, "nivel": int(lido.group(2)),
                                 "tipo": _tipo_do_gatilho(gatilho, itens, indicadores),
                                 "texto": gatilho["texto"] if isinstance(gatilho.get("texto"), str) else ""})
            self.gatilhos[identificador] = gatilhos
        geral = alerta.get("nivel")
        self.nivel_geral = (geral if _e_inteiro(geral) and 1 <= geral <= 5
                            else max(list(self.niveis.values()) or [1]))


def _tipo_do_gatilho(gatilho, itens, indicadores):
    """"alivio", "preco" (o ref é de indicador da edição) ou "evento" (o ref é de item, ou não se achou)."""
    if gatilho.get("alivio") is True:
        return "alivio"
    ref = gatilho.get("ref")
    if isinstance(ref, str) and ref not in itens and ref in indicadores:
        return "preco"
    return "evento"


class Historico(object):
    """As edições já publicadas, por data. Tudo o que depende de "antes" passa por aqui.

    `edicoes` é {data: edição}, com a data do nome do arquivo. `completo=False` diz que o conjunto não é o
    arquivo inteiro (caso do --anterior): aí a regra H2 não acusa a edição que não está aqui.
    Nenhum método olha para a própria data pedida nem para depois dela: a edição do dia pode estar na lista."""

    def __init__(self, edicoes=None, completo=True):
        self._edicoes = dict((d, e) for d, e in dict(edicoes or {}).items() if _e_data(d))
        self.datas = sorted(self._edicoes)
        self.completo = bool(completo)
        self._resumos = {}

    def __contains__(self, data):
        return data in self._edicoes

    def edicao(self, data):
        """A edição dessa data (o objeto, como está no arquivo), ou None."""
        return self._edicoes.get(data) if isinstance(data, str) else None

    def resumo(self, data):
        if data not in self._resumos:
            self._resumos[data] = _Resumo(data, self._edicoes[data])
        return self._resumos[data]

    def antes(self, data):
        """Os resumos das edições de antes de `data` que valem como anterior (nem falha, nem exemplo),
        da mais nova para a mais velha."""
        if not _e_data(data):
            return
        posicao = bisect.bisect_left(self.datas, data)
        while posicao > 0:
            posicao -= 1
            resumo = self.resumo(self.datas[posicao])
            if resumo.vale:
                yield resumo

    def anterior(self, data):
        """A edição anterior (ESQUEMA, seção 0): a mais recente antes de `data` que não é falha nem exemplo."""
        return next(self.antes(data), None)


def nivel_anterior(historico, dominio, data):
    """O N da regra R13: o nível do domínio na edição anterior; 1 se não há edição anterior."""
    anterior = historico.anterior(data) if historico is not None else None
    return anterior.niveis.get(dominio, 1) if anterior else 1


def edicoes_sem_gatilho(historico, dominio, data):
    """O S da regra R13: a conta de edições calmas.

    Anda pelas edições anteriores, da mais nova para a mais velha, enquanto o domínio está no nível N.
    A falha já ficou de fora. Para na que tem gatilho de nível N ou mais (o de alívio conta). Das outras,
    conta as que não são cegas para o domínio."""
    anterior = historico.anterior(data) if historico is not None else None
    if anterior is None:
        return 0
    nivel = anterior.niveis.get(dominio, 1)
    calmas = 0
    for resumo in historico.antes(data):
        if resumo.niveis.get(dominio, 1) != nivel:
            break
        if any(g["nivel"] >= nivel for g in resumo.gatilhos.get(dominio, ())):
            break
        if dominio not in resumo.cegas:
            calmas += 1
    return calmas


_ORDEM_DO_TIPO = {"evento": 0, "preco": 1, "alivio": 2}


def origem_do_nivel(historico, dominio, data):
    """A origem do nível (ESQUEMA, seção 0): o gatilho mais recente do domínio, até a edição anterior, com
    nível igual ou maior que o do domínio na edição anterior. O de alívio conta. No nível 1, None.

    Devolve {"edicao", "criterio", "texto"}, mais "preco": True se o gatilho é de preço e "alivio": True se
    é de alívio. Se a mesma edição tem mais de um gatilho que serve, fica o de evento antes do de preço e
    este antes do de alívio; depois, o de maior nível; depois, o primeiro da lista."""
    anterior = historico.anterior(data) if historico is not None else None
    if anterior is None:
        return None
    nivel = anterior.niveis.get(dominio, 1)
    if nivel <= 1:
        return None
    for resumo in historico.antes(data):
        servem = [g for g in resumo.gatilhos.get(dominio, ()) if g["nivel"] >= nivel]
        if servem:
            escolhido = min(servem, key=lambda g: (_ORDEM_DO_TIPO[g["tipo"]], -g["nivel"]))
            origem = OrderedDict((("edicao", resumo.data), ("criterio", escolhido["criterio"]),
                                  ("texto", escolhido["texto"])))
            if escolhido["tipo"] != "evento":
                origem[escolhido["tipo"]] = True
            return origem
    return None


def alerta_anterior(historico, data, dominios):
    """O objeto `alerta_anterior` do contexto.json (CONTRATO, seção 4.1), para a edição de `data`.

    `dominios` é a lista de ids da régua (dados.dominios). Sem edição anterior: tudo em 1, `desde` igual a
    `data`, contadores em 0 e origem None."""
    anterior = historico.anterior(data) if historico is not None else None
    saida = OrderedDict((("nivel", anterior.nivel_geral if anterior else 1), ("dominios", [])))
    for dominio in dominios:
        nivel = anterior.niveis.get(dominio, 1) if anterior else 1
        calmas = edicoes_sem_gatilho(historico, dominio, data) if anterior else 0
        saida["dominios"].append(OrderedDict((
            ("id", dominio),
            ("nivel", nivel),
            ("desde", anterior.desde.get(dominio, anterior.data) if anterior else data),
            ("edicoes_sem_gatilho", calmas),
            ("desce_hoje_sem_gatilho", calmas >= 2 and nivel > 1),
            ("origem", origem_do_nivel(historico, dominio, data) if anterior else None))))
    return saida


def vetores_anulados(dados):
    """{id do vetor anulado: data da anulação}, lido das entradas de anulação de dados/vetores.json."""
    anulados = {}
    for entrada in dados.vetores:
        if isinstance(entrada.get("anula"), str):
            anulados.setdefault(entrada["anula"], entrada.get("data") if _e_data(entrada.get("data")) else None)
    return anulados


# ---------------------------------------------------------------- calcular: peças

def lado_do_veiculo(dados, veiculo):
    """O `lado` do veículo no mapa (id de partido), ou None se o veículo não está no mapa (regra R03)."""
    ficha = dados.mapa.get(veiculo) if isinstance(veiculo, str) else None
    return ficha["lado"] if ficha else None


def _itens(edicao):
    """[(item, caminho, é principal)] dos itens que são objeto, principais primeiro."""
    saida = []
    for chave, principal in (("principais", True), ("radar", False)):
        lista = edicao.get(chave) if isinstance(edicao, dict) else None
        for indice, item in enumerate(lista if isinstance(lista, list) else ()):
            if isinstance(item, dict):
                saida.append((item, "%s[%d]" % (chave, indice), principal))
    return saida


def _ataques_do_item(item):
    """[(ataque, caminho relativo ao item)]: os de `ataques` (principal) e o de `ataque` (radar)."""
    saida = []
    lista = item.get("ataques")
    for indice, ataque in enumerate(lista if isinstance(lista, list) else ()):
        if isinstance(ataque, dict):
            saida.append((ataque, "ataques[%d]" % indice))
    if isinstance(item.get("ataque"), dict):
        saida.append((item["ataque"], "ataque"))
    return saida


def _textos_do_item(item):
    """Todos os textos de um item, inclusive título de fonte, menos os campos `url` (regra R19, caso c).

    Sem recursão: item com níveis demais não derruba o validador."""
    pilha = [item]
    while pilha:
        valor = pilha.pop()
        if isinstance(valor, str):
            yield valor
        elif isinstance(valor, dict):
            pilha.extend(v for k, v in valor.items() if k != "url")
        elif isinstance(valor, list):
            pilha.extend(valor)


def _le_fontes(dados, item):
    """O que as fontes de um item dizem, cruzadas com o mapa de hoje.

    lados: partidos dos veículos do mapa citados; campos: os campos desses partidos; forte: há fonte forte
    (veículo com fatos alta, ou fonte marcada primaria); fortes e primarias: endereços limpos dessas fontes;
    tem_primaria e primaria_do_brasil (fonte primária em site oficial do Brasil); ligada: alguma fonte é de
    veículo ligado à Anthropic. Fonte "outro" não conta como partido nem como campo (ESQUEMA, seção 15)."""
    lados, campos, fortes, primarias = set(), set(), set(), set()
    forte = tem_primaria = primaria_do_brasil = ligada = False
    for fonte in _lista_de_objetos(item.get("fontes") if isinstance(item, dict) else None):
        veiculo, url = fonte.get("veiculo"), fonte.get("url")
        limpo = _limpo(url)
        ficha = dados.mapa.get(veiculo) if isinstance(veiculo, str) and veiculo != "outro" else None
        primaria = fonte.get("primaria") is True
        esta_forte = primaria
        if ficha:
            if ficha["lado"] in dados.partidos:
                lados.add(ficha["lado"])
            if ficha["lado"] in dados.campo_de:
                campos.add(dados.campo_de[ficha["lado"]])
            if ficha["fatos"] == "alta":
                esta_forte = True
            if veiculo in dados.ligados:
                ligada = True
        if primaria:
            tem_primaria = True
            if limpo:
                primarias.add(limpo)
            if isinstance(url, str) and comum.url_bate(url, dados.oficiais_brasil):
                primaria_do_brasil = True
        if esta_forte:
            forte = True
            if limpo:
                fortes.add(limpo)
    return {"lados": lados, "campos": campos, "forte": forte, "fortes": fortes, "primarias": primarias,
            "tem_primaria": tem_primaria, "primaria_do_brasil": primaria_do_brasil, "ligada": ligada}


def _teto(fontes):
    if len(fontes["campos"]) >= 2 and fontes["forte"]:
        return "alta"
    if len(fontes["lados"]) >= 2 or fontes["forte"]:
        return "media"
    return "baixa"


def teto_de_confianca(dados, item):
    """O teto de confiança de um item pelas fontes (regra R08): "alta" com fontes de veículos dos dois campos
    e 1 forte; "media" com 2 fontes de veículos de partidos diferentes, ou 1 forte; senão "baixa"."""
    return _teto(_le_fontes(dados, item))


def calcula_conflito(dados, item, do_dia=True):
    """A regra R19: o item tem de levar `conflito_de_interesse: true`? Devolve (bool, casos).

    Casos: "a" a categoria é ia; "b" algum alvo de ataque ou player de vetor está em conflito.players;
    "c" algum texto traz termo de conflito.termos; "d" alguma fonte é de veículo ligado à Anthropic.
    Com `do_dia=False` só o caso "a" é olhado: os outros cruzam o item com listas que o dono revisa
    (a lista `conflito` da régua e o mapa), e edição publicada não é conferida de novo contra elas."""
    casos = []
    if not isinstance(item, dict):
        return False, casos
    if item.get("categoria") == "ia":
        casos.append("a")
    if do_dia:
        citados = [ataque.get("alvo") for ataque, _ in _ataques_do_item(item)]
        citados += [vetor.get("player") for vetor in _lista_de_objetos(item.get("vetores"))]
        if any(isinstance(c, str) and c in dados.conflito_players for c in citados):
            casos.append("b")
        if dados.re_termos is not None and any(dados.re_termos.search(t) for t in _textos_do_item(item)):
            casos.append("c")
        if _le_fontes(dados, item)["ligada"]:
            casos.append("d")
    return bool(casos), casos


def calcula_placar_do_dia(dados, edicao):
    """A regra R12: [{"partido", "saldo", "narrativa"}] dos partidos que aparecem em algum placar do dia.

    saldo: forças das linhas que não são de narrativa (ganha soma, perde subtrai). narrativa: linhas de
    narrativa a favor menos linhas contra. Ordem: maior saldo primeiro; empate segue a ordem da régua."""
    saldos, narrativas = OrderedDict(), {}
    for item, _, _ in _itens(edicao):
        for linha in _lista_de_objetos(item.get("placar")):
            partido, efeito, forca = linha.get("partido"), linha.get("efeito"), linha.get("forca")
            if not isinstance(partido, str) or efeito not in EFEITOS or not _e_inteiro(forca) or not 1 <= forca <= 3:
                continue
            sinal = 1 if efeito == "ganha" else -1
            saldos.setdefault(partido, 0)
            narrativas.setdefault(partido, 0)
            if linha.get("evidencia") == "narrativa":
                narrativas[partido] += sinal
            else:
                saldos[partido] += sinal * forca
    ordem = sorted(saldos, key=lambda p: (-saldos[p], dados.posicao_do_partido(p)))
    return [OrderedDict((("partido", p), ("saldo", saldos[p]), ("narrativa", narrativas[p]))) for p in ordem]


def calcula_veiculos_consultados(edicao):
    """Veículos distintos do mapa citados em `fontes` (regra R12). O "outro" não conta."""
    citados = set()
    for item, _, _ in _itens(edicao):
        for fonte in _lista_de_objetos(item.get("fontes")):
            if isinstance(fonte.get("veiculo"), str) and fonte["veiculo"] != "outro":
                citados.add(fonte["veiculo"])
    return len(citados)


def calcula_feeds(coleta):
    """(feeds_ok, feeds_falhos) do objeto de coleta.json; (0, 0) se não há coleta (ESQUEMA, seção 9)."""
    resumo = coleta.get("resumo") if isinstance(coleta, dict) else None
    resumo = resumo if isinstance(resumo, dict) else {}
    contas = []
    for chave in ("feeds_ok", "feeds_falhos"):
        valor = resumo.get(chave)
        contas.append(valor if _e_inteiro(valor) and valor >= 0 else 0)
    return tuple(contas)


def partido_pelo_dna(dados, dna):
    """A conta da regra R20: o partido de `voto_tipico` com mais posições iguais às conhecidas do `dna`
    (as diferentes de W). Empate, ou nenhuma posição igual, dá "independentes"."""
    dna = dna if isinstance(dna, dict) else {}
    contas = OrderedDict()
    for partido in dados.partidos:
        votos = dados.voto.get(partido)
        if votos:
            contas[partido] = sum(1 for tema, letra in votos.items()
                                  if isinstance(dna.get(tema), str) and dna[tema] != "W" and dna[tema] == letra)
    maior = max(list(contas.values()) or [0])
    lideres = [partido for partido, iguais in contas.items() if iguais == maior]
    return lideres[0] if len(lideres) == 1 and maior > 0 else "independentes"


def _indicador_cego(indicador):
    """Sem dado de preço hoje (regra R13f): falta, não tem valor, está defasado ou não tem a variação de 7 dias."""
    return (indicador is None or not _e_numero(indicador.get("valor")) or indicador.get("defasado") is not False
            or not _e_numero(indicador.get("variacao_7d_pct")))


def calcula_sem_preco(dados, dominio, indicadores):
    """A regra R13f: os indicadores citados nos critérios `precos` do domínio, em qualquer nível, que hoje
    faltam em `indicadores`, têm valor null, estão defasados ou têm variacao_7d_pct null.

    Na ordem do catálogo. Indicador citado na régua que nem está no catálogo vai para o fim: o INFOCENARIUM não o
    mediu. `indicadores` é a lista de indicadores da edição."""
    citados = []
    for _, indicador, _, _ in dados.precos.get(dominio, ()):
        if indicador not in citados:
            citados.append(indicador)
    do_dia = _por_id(indicadores)
    em_ordem = [i for i in dados.catalogo if i in citados] + [i for i in citados if i not in dados.indicador]
    return [i for i in em_ordem if _indicador_cego(do_dia.get(i))]


def _precos_cumpridos(dados, indicadores, data):
    """{dominio: {indicador: nível}}: o critério de preço cumprido de maior nível, antes de olhar `confirmado`."""
    do_dia = _por_id(indicadores)
    saida = OrderedDict()
    for dominio in dados.dominios:
        melhores = OrderedDict()
        for nivel, indicador, janela, minimo in dados.precos.get(dominio, ()):
            medido = do_dia.get(indicador)
            if medido is None or medido.get("defasado") is not False:
                continue
            if janela == "1d":
                if not data or medido.get("data") != data:
                    continue  # critério de 1 dia só vale no dia da cotação
                variacao = medido.get("variacao_pct")
            else:
                variacao = medido.get("variacao_7d_pct")
            if _e_numero(variacao) and variacao >= minimo and nivel > melhores.get(indicador, 0):
                melhores[indicador] = nivel
        saida[dominio] = melhores
    return saida


def calcula_gatilhos_de_preco(dados, indicadores, data):
    """A regra R13c: {dominio: {id do indicador: nível}} dos gatilhos de preço que a edição tem de trazer.

    Para cada indicador não defasado, fica o critério `precos` cumprido de maior nível (só alta conta;
    variação null não cumpre; critério de janela "1d" só vale se a `data` do indicador é `data`). Critério
    de nível 3 ou 4 sem `confirmado: true` vale como nível 2. `indicadores` é a lista da edição."""
    do_dia = _por_id(indicadores)
    saida = _precos_cumpridos(dados, indicadores, data)
    for melhores in saida.values():
        for indicador, nivel in list(melhores.items()):
            if nivel in (3, 4) and do_dia[indicador].get("confirmado") is not True:
                melhores[indicador] = 2
    return saida


# ---------------------------------------------------------------- calcular: alerta (regras R13, R14 e R15)

def _info_dos_itens(dados, edicao):
    """{id do item: {"tipo", "confianca", "primaria", "primaria_do_brasil"}}: o que a regra R13b quer saber."""
    info = {}
    for item, _, principal in _itens(edicao):
        identificador = item.get("id")
        if not isinstance(identificador, str) or identificador in info:
            continue
        fontes = _le_fontes(dados, item)
        info[identificador] = {"tipo": "principal" if principal else "radar",
                               "confianca": item.get("confianca") if isinstance(item.get("confianca"), str) else None,
                               "primaria": fontes["tem_primaria"],
                               "primaria_do_brasil": fontes["primaria_do_brasil"]}
    return info


def _analisa_gatilho(dados, dominio, gatilho, itens, indicadores, nivel_anterior_, origem):
    """Lê um gatilho. Não acusa nada: devolve o que o cálculo e a conferência precisam saber dele."""
    lido = {"objeto": isinstance(gatilho, dict), "criterio_ok": False, "dominio_ok": False, "nivel": None,
            "ref": None, "alvo": None, "item": None, "alivio": False, "excecao": False, "continua": False,
            "recusas": []}
    if not lido["objeto"]:
        return lido
    criterio = gatilho.get("criterio")
    par = dados.codigos.get(criterio) if isinstance(criterio, str) else None
    if par is not None and 2 <= par[1] <= 5:
        lido["criterio_ok"], lido["nivel"] = True, par[1]
        lido["dominio_ok"] = par[0] == dominio
    ref = gatilho.get("ref")
    if isinstance(ref, str):
        lido["ref"] = ref
        if ref in itens:
            lido["alvo"], lido["item"] = "item", itens[ref]
        elif ref in indicadores:
            lido["alvo"] = "indicador"
    lido["alivio"] = gatilho.get("alivio") is True
    lido["excecao"] = gatilho.get("excecao") is True
    if not (lido["criterio_ok"] and lido["dominio_ok"]):
        return lido
    por_evento = origem is not None and not origem.get("preco") and not origem.get("alivio")
    if lido["alivio"]:
        # Regra R13e. Cada recusa é (campo do gatilho, mensagem); sem recusa, o alívio vale.
        recusas = lido["recusas"]
        if nivel_anterior_ not in (4, 5):
            recusas.append(("alivio", "o domínio estava no nível %d na edição anterior, e alívio só vale em "
                            "domínio que estava em 4 ou 5. Tire o gatilho: nos níveis 2 e 3 o nível desce "
                            "sozinho." % nivel_anterior_))
        elif not por_evento:
            recusas.append(("alivio", "o nível anterior não veio de evento (%s). Alívio só encerra estado "
                            "aberto por evento. Tire o gatilho." % _descreve_origem(origem)))
        elif origem["criterio"] != criterio:
            recusas.append(("criterio", "é %s, e a origem do nível é %s (edição %s). O alívio repete o "
                            "critério da origem: troque." % (_mostra(criterio), _mostra(origem["criterio"]),
                                                              origem["edicao"])))
        if lido["alvo"] != "item" or lido["item"]["tipo"] != "principal" or lido["item"]["confianca"] != "alta":
            recusas.append(("ref", "alívio pede ref de principal com confiança 'alta', e %s não é. Aponte "
                            "para a principal que mostra o fim do estado, ou tire o gatilho." % _mostra(ref)))
        if lido["excecao"]:
            recusas.append(("excecao", "alívio nunca vem junto com exceção. Tire um dos dois campos."))
    elif (lido["nivel"] >= 4 and lido["alvo"] == "item" and por_evento and origem["criterio"] == criterio
          and nivel_anterior_ >= lido["nivel"]):
        lido["continua"] = True  # estado que continua (regra R13b): aceita radar e não pede de novo a primária
    return lido


def _descreve_origem(origem):
    if origem is None:
        return "não há gatilho de origem no histórico"
    tipo = "gatilho de preço" if origem.get("preco") else ("outro alívio" if origem.get("alivio") else "evento")
    return "a origem é %s, %s de %s" % (_mostra(origem["criterio"]), tipo, origem["edicao"])


def _analisa_alerta(dados, edicao, historico, do_dia):
    """A conta inteira do alerta de uma edição. É a única implementação das regras R13, R13e, R14 e R15:
    o calcula_alerta devolve um resumo dela, e o confere_edicao compara a edição com ela.

    `historico=None` conta como histórico vazio (primeira edição). Com `do_dia=False`, `sem_preco` é o que
    está escrito na edição: edição de arquivo não é medida de novo contra o catálogo de hoje."""
    edicao = edicao if isinstance(edicao, dict) else {}
    data = edicao["data"] if _e_data(edicao.get("data")) else None
    falha = edicao.get("estado") == "falha"
    itens = _info_dos_itens(dados, edicao)
    indicadores = _por_id(edicao.get("indicadores"))
    alerta = edicao.get("alerta") if isinstance(edicao.get("alerta"), dict) else {}
    escritos = _por_id(alerta.get("dominios"))
    anterior = historico.anterior(data) if historico is not None and data else None
    dominios = OrderedDict()
    for dominio in dados.dominios:
        escrito = escritos.get(dominio, {})
        antes = anterior.niveis.get(dominio, 1) if anterior else 1
        origem = origem_do_nivel(historico, dominio, data) if anterior and antes > 1 else None
        lista = escrito.get("gatilhos")
        gatilhos = [_analisa_gatilho(dados, dominio, g, itens, indicadores, antes, origem)
                    for g in (lista if isinstance(lista, list) else ())]
        alivios = [g for g in gatilhos if g["alivio"] and g["criterio_ok"] and g["dominio_ok"]]
        for extra in alivios[1:]:
            extra["recusas"].append(("alivio", "já há outro gatilho de alívio neste domínio, e vale no máximo 1. "
                                     "Tire um."))
        maior = max([g["nivel"] for g in gatilhos if g["criterio_ok"] and g["dominio_ok"] and not g["alivio"]]
                    or [1])
        if do_dia:
            sem_preco = calcula_sem_preco(dados, dominio, edicao.get("indicadores"))
        else:
            sem_preco = _textos_da_lista(escrito.get("sem_preco"))
        alivio_vale = any(not g["recusas"] for g in alivios)
        calmas = None
        if falha:
            nivel, ramo = antes, "falha"
        elif maior >= antes:
            nivel, ramo = maior, "gatilho"
        elif alivio_vale:
            nivel, ramo = antes - 1, "alivio"
        else:
            calmas = edicoes_sem_gatilho(historico, dominio, data) if anterior else 0
            if calmas >= 2 and not sem_preco:
                nivel, ramo = antes - 1, "calma"
            else:
                nivel, ramo = antes, "mantido"
        if anterior is None or nivel == antes:
            tendencia = "estavel"
        else:
            tendencia = "subindo" if nivel > antes else "descendo"
        if anterior is not None and nivel == antes:
            desde = anterior.desde.get(dominio)
            desde = desde if desde and (not data or desde <= data) else data
        else:
            desde = data
        dominios[dominio] = {"id": dominio, "escrito": escrito, "N": antes, "T": maior, "S": calmas,
                             "origem": origem, "sem_preco": sem_preco, "gatilhos": gatilhos, "ramo": ramo,
                             "nivel": nivel, "tendencia": tendencia, "desde": desde}
    geral = max([d["nivel"] for d in dominios.values()] or [1])
    if anterior is None or geral == anterior.nivel_geral:
        tendencia = "estavel"
    else:
        tendencia = "subindo" if geral > anterior.nivel_geral else "descendo"
    return {"dominios": dominios, "nivel": geral, "tendencia": tendencia, "anterior": anterior, "itens": itens,
            "indicadores": indicadores}


def calcula_alerta(dados, edicao, historico, do_dia=True):
    """Os campos calculados do alerta (regras R13, R13f, R14 e R15).

    Devolve {"nivel", "tendencia", "dominios": [{"id", "nivel", "tendencia", "desde", "sem_preco"}]}, com
    os domínios na ordem da régua. Usa da edição: data, estado, os gatilhos de cada domínio, os itens que
    eles citam e a lista `indicadores`. `historico=None` conta como histórico vazio. Em edição `falha`, os
    níveis e os `desde` repetem os da edição anterior."""
    conta = _analisa_alerta(dados, edicao, historico, do_dia)
    return OrderedDict((
        ("nivel", conta["nivel"]),
        ("tendencia", conta["tendencia"]),
        ("dominios", [OrderedDict((chave, d[chave]) for chave in ("id", "nivel", "tendencia", "desde", "sem_preco"))
                      for d in conta["dominios"].values()])))


# ---------------------------------------------------------------- calcular: a edição inteira

def _copia(valor):
    """Cópia funda de um valor JSON, sem recursão do Python além da do próprio JSON."""
    return json.loads(json.dumps(valor, allow_nan=True))


def _ordena(objeto, tipo):
    """O objeto com as chaves na ordem do ESQUEMA; chave desconhecida vai para o fim (o validador acusa)."""
    if not isinstance(objeto, dict):
        return objeto
    novo = dict((chave, objeto[chave]) for chave in ORDEM[tipo] if chave in objeto)
    for chave in objeto:
        if chave not in novo:
            novo[chave] = objeto[chave]
    return novo


def _ordena_lista(valor, tipo, cada=None):
    if not isinstance(valor, list):
        return valor
    return [(cada(_ordena(v, tipo)) if cada and isinstance(v, dict) else _ordena(v, tipo)) for v in valor]


def normaliza(edicao, dados=None):
    """A mesma edição, com as chaves de cada objeto na ordem das tabelas do ESQUEMA (seção 0).

    Com `dados`, `dna` e `dna_fontes` do player novo saem na ordem dos temas da régua. Não muda valor
    nenhum e não mexe na ordem das listas. Devolve objeto novo, sem pedaço em comum com o que recebeu."""
    try:
        return _normaliza(_copia(edicao), dados)
    except (TypeError, ValueError, RecursionError):
        return _normaliza(edicao, dados)  # valor que não cabe em JSON: vai sem a cópia


def _normaliza(edicao, dados):
    if not isinstance(edicao, dict):
        return edicao
    temas = dados.temas if dados is not None else []

    def item(objeto):
        if isinstance(objeto.get("ataques"), list):
            objeto["ataques"] = _ordena_lista(objeto["ataques"], "ataque")
        for chave, tipo in (("ataque", "ataque"), ("eixo", "eixo")):
            if chave in objeto:
                objeto[chave] = _ordena(objeto[chave], tipo)
        for chave, tipo in (("placar", "placar"), ("vetores", "vetor"), ("fontes", "fonte")):
            if chave in objeto:
                objeto[chave] = _ordena_lista(objeto[chave], tipo)
        return objeto

    def dominio(objeto):
        if "gatilhos" in objeto:
            objeto["gatilhos"] = _ordena_lista(objeto["gatilhos"], "gatilho")
        return objeto

    def indicador(objeto):
        if "fonte" in objeto:
            objeto["fonte"] = _ordena(objeto["fonte"], "fonte_indicador")
        return objeto

    def player(objeto):
        for chave in ("dna", "dna_fontes"):
            valor = objeto.get(chave)
            if isinstance(valor, dict) and temas:
                novo = dict((t, valor[t]) for t in temas if t in valor)
                novo.update((k, v) for k, v in valor.items() if k not in novo)
                objeto[chave] = novo
        return objeto

    raiz = _ordena(edicao, "raiz")
    if isinstance(raiz.get("alerta"), dict):
        alerta = _ordena(raiz["alerta"], "alerta")
        if "dominios" in alerta:
            alerta["dominios"] = _ordena_lista(alerta["dominios"], "dominio", dominio)
        raiz["alerta"] = alerta
    for chave, tipo, cada in (("indicadores", "indicador", indicador), ("principais", "principal", item),
                              ("radar", "radar", item), ("placar_do_dia", "placar_do_dia", None),
                              ("novos_players", "novo_player", player), ("errata", "errata", None),
                              ("respostas", "resposta", None)):
        if chave in raiz:
            raiz[chave] = _ordena_lista(raiz[chave], tipo, cada)
    if isinstance(raiz.get("bastidores"), dict):
        bastidores = _ordena(raiz["bastidores"], "bastidores")
        if "candidatos" in bastidores:
            bastidores["candidatos"] = _ordena_lista(bastidores["candidatos"], "candidato")
        raiz["bastidores"] = bastidores
    return raiz


def completa(rascunho, dados, historico, indicadores=None, coleta=None, gerada_em=None):
    """Preenche os campos calculados de um rascunho (CONTRATO, seção 4.2, passo 4) e devolve a edição.

    rascunho     o objeto de rascunho.json (só os campos de origem agente; o que vier a mais é trocado)
    historico    Historico das edições publicadas; None conta como vazio
    indicadores  o objeto de indicadores.json ({"indicadores": […], "gatilhos": […]}); None: lista vazia
    coleta       o objeto de coleta.json; None: feeds_ok e feeds_falhos em 0
    gerada_em    a data-hora da gravação (comum.agora_texto()); None deixa o campo como veio
    Não muda o rascunho. Se ele não é um objeto, devolve como veio: o confere_edicao acusa."""
    if not isinstance(rascunho, dict):
        return rascunho
    try:
        return _completa(_copia(rascunho), dados, historico, indicadores, coleta, gerada_em)
    except (TypeError, ValueError, RecursionError):
        return rascunho  # valor que nem cabe em JSON, ou níveis demais: fica como veio, e a conferência acusa


def _completa(edicao, dados, historico, indicadores, coleta, gerada_em):
    edicao["versao"] = 1
    if gerada_em is not None:
        edicao["gerada_em"] = gerada_em
    medidos = indicadores.get("indicadores") if isinstance(indicadores, dict) else None
    edicao["indicadores"] = _copia(medidos) if isinstance(medidos, list) else []
    de_preco = _lista_de_objetos(indicadores.get("gatilhos")) if isinstance(indicadores, dict) else []
    ids_de_preco = (set(dados.catalogo) | set(_ids(edicao["indicadores"]))) - _ids_dos_itens(edicao)

    for item, _, _ in _itens(edicao):
        for ataque, _ in _ataques_do_item(item):
            lado = lado_do_veiculo(dados, ataque.get("veiculo"))
            if lado is not None:
                ataque["lado"] = lado
            else:
                ataque.pop("lado", None)  # veículo fora do mapa: sem lado para copiar; a regra R02 acusa
        if calcula_conflito(dados, item, True)[0]:
            item["conflito_de_interesse"] = True  # liga; o que o agente ligou continua ligado

    alerta = edicao.get("alerta")
    if isinstance(alerta, dict):
        falha = edicao.get("estado") == "falha"
        for dominio in _lista_de_objetos(alerta.get("dominios")):
            proprios = dominio.get("gatilhos")
            if not isinstance(proprios, list):
                continue
            proprios = [g for g in proprios
                        if not (isinstance(g, dict) and isinstance(g.get("ref"), str) and g["ref"] in ids_de_preco)]
            copiados = []
            if not falha:
                for gatilho in de_preco:
                    par = dados.codigos.get(gatilho.get("criterio")) if isinstance(gatilho.get("criterio"), str) else None
                    if par is not None and par[0] == dominio.get("id"):
                        copiados.append(_copia(gatilho))
            dominio["gatilhos"] = copiados + proprios
        conta = calcula_alerta(dados, edicao, historico, True)
        por_id = dict((d["id"], d) for d in conta["dominios"])
        for dominio in _lista_de_objetos(alerta.get("dominios")):
            calculado = por_id.get(dominio.get("id")) if isinstance(dominio.get("id"), str) else None
            if calculado is not None:
                for chave in CALCULADOS["dominio"]:
                    dominio[chave] = calculado[chave]
        alerta["nivel"], alerta["tendencia"] = conta["nivel"], conta["tendencia"]

    escritas = edicao.get("placar_do_dia")
    if isinstance(escritas, list):
        usadas, novas = set(), []
        calculadas = calcula_placar_do_dia(dados, edicao)
        for calculada in calculadas:
            for posicao, escrita in enumerate(escritas):
                if posicao not in usadas and isinstance(escrita, dict) and escrita.get("partido") == calculada["partido"]:
                    usadas.add(posicao)
                    novas.append(dict(escrita, saldo=calculada["saldo"], narrativa=calculada["narrativa"]))
                    break
        # O que sobrou (partido sem linha em placar nenhum, ou repetido) fica no fim, com a conta que tem:
        # quem acusa é a regra R12, e não a falta de um campo calculado.
        contas = dict((c["partido"], c) for c in calculadas)
        for posicao, escrita in enumerate(escritas):
            if posicao in usadas:
                continue
            if isinstance(escrita, dict):
                conta = contas.get(escrita.get("partido") if isinstance(escrita.get("partido"), str) else None, {})
                escrita = dict(escrita, saldo=conta.get("saldo", 0), narrativa=conta.get("narrativa", 0))
            novas.append(escrita)
        edicao["placar_do_dia"] = novas

    bastidores = edicao.get("bastidores")
    if isinstance(bastidores, dict):
        bastidores["veiculos_consultados"] = calcula_veiculos_consultados(edicao)
        bastidores["feeds_ok"], bastidores["feeds_falhos"] = calcula_feeds(coleta)
    return _normaliza(edicao, dados)


def monta_indice(edicoes):
    """O objeto de edicoes/indice.json (ESQUEMA, seção 11), a partir de {data: edição}.

    Mais nova primeiro. `atualizado_em` é o maior `gerada_em` (None se não há edição). `corrigida_em` de
    cada entrada traz, em ordem crescente, as edições posteriores cuja errata a cita. `eixos` segue a ordem
    em que os temas aparecem na edição. Edição torta não dá exceção: o campo que não dá para ler sai None."""
    edicoes = dict((d, e) for d, e in dict(edicoes or {}).items() if _e_data(d) and isinstance(e, dict))
    corrigidas = {}
    for data in sorted(edicoes):
        for errata in _lista_de_objetos(edicoes[data].get("errata")):
            alvo = errata.get("edicao")
            if isinstance(alvo, str) and alvo in edicoes and alvo < data and data not in corrigidas.setdefault(alvo, []):
                corrigidas[alvo].append(data)
    entradas, geradas = [], []
    for data in sorted(edicoes, reverse=True):
        edicao = edicoes[data]
        alerta = edicao.get("alerta") if isinstance(edicao.get("alerta"), dict) else {}
        niveis = OrderedDict((d["id"], d.get("nivel")) for d in _lista_de_objetos(alerta.get("dominios"))
                             if isinstance(d.get("id"), str))
        saldos = OrderedDict((l["partido"], l.get("saldo")) for l in _lista_de_objetos(edicao.get("placar_do_dia"))
                             if isinstance(l.get("partido"), str))
        eixos = OrderedDict()
        for item, _, _ in _itens(edicao):
            eixo = item.get("eixo")
            if isinstance(eixo, dict) and isinstance(eixo.get("tema"), str) and eixo.get("sentido") in SENTIDOS:
                conta = eixos.setdefault(eixo["tema"], OrderedDict((s, 0) for s in SENTIDOS))
                conta[eixo["sentido"]] += 1
        valores = OrderedDict((i["id"], i["valor"]) for i in _lista_de_objetos(edicao.get("indicadores"))
                              if isinstance(i.get("id"), str) and _e_numero(i.get("valor"))
                              and i.get("defasado") is False)
        if comum.data_hora_valida(edicao.get("gerada_em")):
            geradas.append(edicao["gerada_em"])
        entradas.append(OrderedDict((
            ("data", data),
            ("arquivo", "edicoes/%s.json" % data),
            ("texto", "edicoes/%s.md" % data),
            ("estado", edicao.get("estado")),
            ("nivel", alerta.get("nivel")),
            ("tendencia", alerta.get("tendencia")),
            ("niveis", niveis),
            ("saldos", saldos),
            ("eixos", eixos),
            ("indicadores", valores),
            ("resumo", edicao.get("resumo")),
            ("gerada_em", edicao.get("gerada_em")),
            ("exemplo", edicao.get("exemplo") is True),
            ("corrigida_em", corrigidas.get(data, [])))))
    return OrderedDict((("versao", 1), ("atualizado_em", max(geradas) if geradas else None),
                        ("edicoes", entradas)))


# ---------------------------------------------------------------- conferir: a edição (regras R e H)

_CAMPOS_DE_CONTAGEM = ("veiculos_consultados", "feeds_ok", "feeds_falhos", "paginas_lidas", "buscas", "minutos",
                       "injecoes_ignoradas")
_FAIXAS_POR_ESTADO = {"completa": ((3, 3), (6, 12)), "reduzida": ((1, 3), (3, 12)), "falha": ((0, 0), (0, 0))}
_CONSERTO_DO_CALCULADO = "É campo calculado: publique de novo com publica.py edicao (edição não se edita à mão)."


def _junta(campo, chave):
    return "%s.%s" % (campo, chave) if campo else chave


def _sugere(valor, opcoes):
    """" Você quis dizer 'x'?" quando o valor errado parece com um dos certos; senão, texto vazio."""
    if not isinstance(valor, str):
        return ""
    perto = difflib.get_close_matches(valor, [o for o in opcoes if isinstance(o, str)], 1, 0.75)
    return " Você quis dizer %s?" % _mostra(perto[0]) if perto else ""


def _chave_do_titulo(titulo):
    """O título sem acento, sem pontuação e em minúsculas: é o que a regra H3 compara."""
    texto = unicodedata.normalize("NFKD", titulo.casefold())
    return " ".join(re.findall("[a-z0-9]+", "".join(c for c in texto if not unicodedata.combining(c))))


def _quase_iguais(um, outro):
    if len(um) < 10 or len(outro) < 10:
        return False
    return um == outro or difflib.SequenceMatcher(None, um, outro).ratio() >= 0.85


class _Conferente(object):
    """Confere uma edição completa. Cada método olha um trecho e põe os achados em self.a."""

    def __init__(self, edicao, dados, historico, do_dia, data_do_arquivo, achados):
        self.e, self.dados, self.historico, self.do_dia, self.a = edicao, dados, historico, bool(do_dia), achados
        self.data_do_arquivo = data_do_arquivo
        self.data = edicao["data"] if _e_data(edicao.get("data")) else None
        self.exemplo = edicao.get("exemplo") is True
        self.estado = edicao.get("estado") if edicao.get("estado") in ESTADOS else None
        self.ids_novos = set(_ids(edicao.get("novos_players")))
        self.vetores = []  # (player, para, caminho) de todos os vetores da edição
        self.excecoes = []  # caminhos dos gatilhos com excecao: true

    # ------------------------------------------------------------ ferramentas

    def erro(self, regra, campo, mensagem):
        self.a.erro(regra, campo, mensagem)

    def objeto(self, valor, campo, tipo, dispensados=()):
        """A forma de um objeto (regra R00): é objeto, tem os campos obrigatórios e nenhum desconhecido."""
        if not isinstance(valor, dict):
            self.erro("R00", campo, "deveria ser um objeto, e é %s (%s). Escreva na forma do modelo.txt."
                      % (_nome_do_tipo(valor), _mostra(valor, 30)))
            return False
        ordem, opcionais, calculados = ORDEM[tipo], OPCIONAIS.get(tipo, ()), CALCULADOS.get(tipo, ())
        for chave in ordem:
            if chave in valor or chave in opcionais or chave in dispensados:
                continue
            if chave in calculados:
                self.erro("R00", _junta(campo, chave), "falta o campo, que é o publica.py que preenche. "
                          "Publique com publica.py edicao: edição não se escreve à mão.")
            else:
                self.erro("R00", _junta(campo, chave), "falta o campo obrigatório. Acrescente.")
        for chave in valor:
            if chave not in ordem:
                self.erro("R00", campo, "campo desconhecido %s. Tire: o esquema não tem esse campo.%s"
                          % (_mostra(chave, 30), _sugere(chave, ordem)))
        return True

    def um_texto(self, valor, campo, maximo, so_algarismos=False, opcional=False):
        if not isinstance(valor, str):
            self.erro("R00", campo, "deveria ser texto, e é %s (%s). Escreva o texto entre aspas."
                      % (_nome_do_tipo(valor), _mostra(valor, 30)))
            return None
        for mensagem in confere_texto(valor, maximo, so_algarismos, opcional):
            self.erro("R17", campo, mensagem)
        return valor

    def texto(self, objeto, chave, campo, tipo, so_algarismos=False):
        if chave not in objeto:
            return None
        return self.um_texto(objeto[chave], _junta(campo, chave), MAXIMOS[(tipo, chave)], so_algarismos,
                             opcional=chave in OPCIONAIS.get(tipo, ()))

    def lista(self, objeto, chave, campo, minimo=0, maximo=None, regra="R00", regra_do_minimo=None, dica=""):
        """Uma lista e a sua contagem. Devolve a lista ([] se falta ou se não é lista)."""
        if chave not in objeto:
            return []
        valor, caminho = objeto[chave], _junta(campo, chave)
        if not isinstance(valor, list):
            self.erro("R00", caminho, "deveria ser uma lista, e é %s (%s). Escreva entre colchetes; lista sem item é []."
                      % (_nome_do_tipo(valor), _mostra(valor, 30)))
            return []
        faixa = ("de %d a %d" % (minimo, maximo) if maximo is not None and maximo != minimo
                 else ("exatamente %d" % minimo if maximo is not None else "%d ou mais" % minimo))
        if len(valor) < minimo:
            self.erro(regra_do_minimo or regra, caminho, "tem %s; o esquema pede %s. Acrescente %d.%s"
                      % (_conta(len(valor), "item", "itens"), faixa, minimo - len(valor), dica))
        elif maximo is not None and len(valor) > maximo:
            self.erro(regra, caminho, "tem %s; o esquema pede %s. Tire %d.%s"
                      % (_conta(len(valor), "item", "itens"), faixa, len(valor) - maximo, dica))
        return valor

    def inteiro(self, objeto, chave, campo, minimo=None, maximo=None, regra="R00", conserto="Corrija."):
        if chave not in objeto:
            return None
        valor, caminho = objeto[chave], _junta(campo, chave)
        if not _e_inteiro(valor):
            self.erro("R00", caminho, "deveria ser número inteiro, e é %s (%s). Escreva o número, sem aspas e "
                      "sem casa decimal." % (_nome_do_tipo(valor), _mostra(valor, 30)))
            return None
        if (minimo is not None and valor < minimo) or (maximo is not None and valor > maximo):
            faixa = ("de %d a %d" % (minimo, maximo) if maximo is not None and minimo is not None
                     else ("%d ou mais" % minimo if minimo is not None else "até %d" % maximo))
            self.erro(regra, caminho, "é %d; vale %s. %s" % (valor, faixa, conserto))
            return None
        return valor

    def booleano(self, objeto, chave, campo):
        if chave not in objeto:
            return None
        valor = objeto[chave]
        if not isinstance(valor, bool):
            self.erro("R00", _junta(campo, chave), "deveria ser true ou false (sem aspas), e é %s (%s). Corrija."
                      % (_nome_do_tipo(valor), _mostra(valor, 30)))
            return None
        return valor

    def um_de(self, objeto, chave, campo, valores, regra="R00"):
        if chave not in objeto:
            return None
        valor = objeto[chave]
        if not isinstance(valor, str) or valor not in valores:
            self.erro(regra, _junta(campo, chave), "é %s; vale um destes: %s. Troque.%s"
                      % (_mostra(valor, 30), _lista_em_texto(valores), _sugere(valor, valores)))
            return None
        return valor

    def uma_data(self, objeto, chave, campo):
        if chave not in objeto:
            return None
        valor = objeto[chave]
        if not _e_data(valor):
            self.erro("R00", _junta(campo, chave), "é %s; deveria ser uma data AAAA-MM-DD que existe no "
                      "calendário. Corrija." % _mostra(valor, 30))
            return None
        return valor

    def url(self, objeto, chave, campo):
        if chave not in objeto:
            return None
        return self.uma_url(objeto[chave], _junta(campo, chave))

    def uma_url(self, valor, caminho):
        if not comum.url_valida(valor):
            self.erro("R17", caminho, "URL inválida (%s): começa com http:// ou https://, tem nome de site, tem até "
                      "500 caracteres e não tem espaço, caractere de controle, caractere invisível, aspas, "
                      "apóstrofo, crase, cifrão, barra invertida nem usuário@ antes do site. Corrija o endereço, "
                      "ou use outra página." % _mostra(valor, 50))
            return None
        return valor

    def marca_de_exemplo(self, titulo, caminho):
        """Regra R18: com exemplo: true todo título começa com [EXEMPLO]; sem exemplo, nenhum."""
        if not isinstance(titulo, str):
            return
        marcado = titulo.startswith("[EXEMPLO]")
        if self.exemplo and not marcado:
            self.erro("R18", caminho, "a edição tem exemplo: true, e todo título de edição de exemplo começa com "
                      "'[EXEMPLO]'. Acrescente a marca no começo do título.")
        elif marcado and not self.exemplo:
            self.erro("R18", caminho, "começa com '[EXEMPLO]', e a edição não é de exemplo. Tire a marca do título.")

    # ------------------------------------------------------------ o roteiro

    def roda(self):
        self.objeto(self.e, "", "raiz")
        self.raiz()
        self.alerta()
        self.indicadores()
        self.itens()
        self.placar_do_dia()
        self.novos_players()
        self.errata_e_respostas()
        self.bastidores()
        if self.historico is not None:
            self.historia()

    def raiz(self):
        e = self.e
        if "versao" in e and (not _e_inteiro(e["versao"]) or e["versao"] != 1):
            self.erro("R00", "versao", "é %s; deveria ser 1. %s" % (_mostra(e["versao"], 30), _CONSERTO_DO_CALCULADO))
        if "data" in e:
            if self.data is None:
                self.erro("R00", "data", "é %s; deveria ser o dia da edição, AAAA-MM-DD. Use o dia do contexto.json."
                          % _mostra(e["data"], 30))
            elif self.data_do_arquivo and self.data != self.data_do_arquivo:
                self.erro("R01", "data", "é %s, e o arquivo se chama %s.json. Em edicoes/ a data é igual ao nome do "
                          "arquivo: publique com publica.py edicao, que grava com o nome certo."
                          % (_mostra(self.data), self.data_do_arquivo))
        if "gerada_em" in e:
            gerada = e["gerada_em"]
            if not comum.data_hora_valida(gerada):
                self.erro("R00", "gerada_em", "é %s; deveria ser data-hora UTC, AAAA-MM-DDTHH:MM:SSZ. %s"
                          % (_mostra(gerada, 30), _CONSERTO_DO_CALCULADO))
            elif self.data and gerada[:10] not in (self.data, comum.soma_dias(self.data, 1)):
                self.erro("R00", "gerada_em", "o dia UTC é %s; deveria ser o da edição (%s) ou o dia seguinte. %s"
                          % (gerada[:10], self.data, _CONSERTO_DO_CALCULADO))
        self.um_de(e, "estado", "", ESTADOS)
        self.booleano(e, "exemplo", "")
        self.texto(e, "resumo", "", "raiz")

    # ------------------------------------------------------------ indicadores (ESQUEMA, seção 3)

    def indicadores(self):
        e, dados = self.e, self.dados
        maximo = len(dados.catalogo) if self.do_dia and dados.catalogo else None
        lista = self.lista(e, "indicadores", "", 0, maximo, dica=" Vale um item por indicador do catálogo.")
        cumpridos = _precos_cumpridos(dados, lista, self.data) if self.do_dia else {}
        vistos = set()
        for indice, indicador in enumerate(lista):
            c = "indicadores[%d]" % indice
            if not self.objeto(indicador, c, "indicador"):
                continue
            identificador = indicador.get("id", _FALTA)
            if identificador is not _FALTA:
                if not isinstance(identificador, str) or not identificador:
                    self.erro("R00", c + ".id", "deveria ser o id de um indicador do catálogo, e é %s. Corrija."
                              % _mostra(identificador, 30))
                    identificador = _FALTA
                elif identificador in vistos:
                    self.erro("R02", c + ".id", "%s está repetido na lista. Vale um item por indicador: tire um."
                              % _mostra(identificador))
                elif self.do_dia and identificador not in dados.indicador:
                    self.erro("R02", c + ".id", "%s não está no catálogo (dados/indicadores.json). A lista vem do "
                              "indicadores.py: rode-o e publique de novo.%s"
                              % (_mostra(identificador), _sugere(identificador, dados.catalogo)))
                vistos.add(identificador)
            self.texto(indicador, "nome", c, "indicador")
            self.texto(indicador, "unidade", c, "indicador")
            if "dominio" in indicador and (not isinstance(indicador["dominio"], str)
                                           or indicador["dominio"] not in dados.dominios):
                self.erro("R02", c + ".dominio", "%s não é domínio da régua. Vale: %s."
                          % (_mostra(indicador["dominio"], 30), _lista_em_texto(dados.dominios)))
            for chave in ("valor", "variacao_pct", "variacao_7d_pct"):
                valor = indicador.get(chave)
                if chave in indicador and valor is not None and not _e_numero(valor):
                    self.erro("R00", _junta(c, chave), "deveria ser número ou null, e é %s (%s). Corrija."
                              % (_nome_do_tipo(valor), _mostra(valor, 30)))
                elif chave != "valor" and _e_numero(valor) and abs(valor * 10 - round(valor * 10)) > 1e-6:
                    self.erro("R00", _junta(c, chave), "é %s; a variação vem arredondada a 1 casa. Quem grava é "
                              "o indicadores.py: rode-o de novo." % _mostra(valor))
            valor = indicador.get("valor")
            if _e_numero(valor) and valor <= 0:
                self.erro("R00", c + ".valor", "é %s; deveria ser maior que zero, ou null se não há dado hoje."
                          % _mostra(valor))
            cotacao = indicador.get("data")
            if "data" in indicador and cotacao is not None:
                cotacao = self.uma_data(indicador, "data", c)
                if cotacao and self.data and cotacao > self.data:
                    self.erro("R00", c + ".data", "a cotação é de %s, depois da data da edição (%s). Cotação do "
                              "futuro não vale: rode o indicadores.py com o dia certo." % (cotacao, self.data))
            defasado = self.booleano(indicador, "defasado", c)
            confirmado = self.booleano(indicador, "confirmado", c)
            if "valor" in indicador and valor is None:
                if defasado is False:
                    self.erro("R00", c + ".defasado", "é false com valor null. Indicador sem dado é defasado: "
                              "deveria ser true.")
                for chave in ("variacao_pct", "variacao_7d_pct", "data"):
                    if indicador.get(chave) is not None:
                        self.erro("R00", _junta(c, chave), "é %s com valor null. Indicador sem dado não tem "
                                  "variação nem data: deveria ser null." % _mostra(indicador[chave], 30))
                if confirmado is True:
                    self.erro("R00", c + ".confirmado", "é true com valor null. Sem dado não há alta confirmada: "
                              "deveria ser false.")
            elif _e_numero(valor) and "data" in indicador and indicador["data"] is None:
                self.erro("R00", c + ".data", "é null, e o indicador tem valor. Falta o dia da cotação: rode o indicadores.py "
                          "de novo.")
            if self.do_dia and isinstance(identificador, str) and identificador in dados.indicador:
                if _e_numero(valor) and cotacao and self.data and defasado is not None:
                    mensal = dados.indicador[identificador].get("frequencia") == "mensal"
                    limite = 62 if mensal else 4
                    velho = comum.dias_entre(cotacao, self.data) > limite
                    if velho != defasado:
                        self.erro("R00", c + ".defasado", "é %s, e a cotação é de %s, %d dias antes da edição "
                                  "(indicador %s: defasado com mais de %d dias). Deveria ser %s: rode o "
                                  "indicadores.py de novo."
                                  % (_mostra(defasado), cotacao, comum.dias_entre(cotacao, self.data),
                                     "mensal" if mensal else "diário", limite, _mostra(velho)))
                if (dados.indicador[identificador].get("frequencia") == "mensal"
                        and indicador.get("variacao_7d_pct") is not None):
                    self.erro("R00", c + ".variacao_7d_pct", "é %s, e %s é indicador mensal: nele a variação de 7 "
                              "dias é sempre null. Rode o indicadores.py de novo."
                              % (_mostra(indicador["variacao_7d_pct"], 30), _mostra(identificador)))
                if confirmado is True and not any(cumpridos.get(d, {}).get(identificador) in (3, 4)
                                                 for d in dados.dominios):
                    self.erro("R13c", c + ".confirmado", "é true, e a alta de %s não cumpre critério de preço de "
                              "nível 3 ou 4. Só alta forte tem confirmação: deveria ser false. Rode o "
                              "indicadores.py de novo." % _mostra(identificador))
            if "fonte" in indicador and self.objeto(indicador["fonte"], c + ".fonte", "fonte_indicador"):
                self.texto(indicador["fonte"], "nome", c + ".fonte", "fonte_indicador")
                self.url(indicador["fonte"], "url", c + ".fonte")

    # ------------------------------------------------------------ principais e radar (seções 4 e 5)

    def itens(self):
        e = self.e
        (pmin, pmax), (rmin, rmax) = _FAIXAS_POR_ESTADO.get(self.estado, ((0, 3), (0, 12)))
        if self.estado == "completa":
            dica = " Se o dia não rende, publique com estado 'reduzida' (1 a 3 principais, 3 a 12 no radar)."
        elif self.estado == "falha":
            dica = " Edição 'falha' não tem item."
        else:
            dica = ""
        principais = self.lista(e, "principais", "", pmin, pmax, regra="R15", dica=dica)
        radar = self.lista(e, "radar", "", rmin, rmax, regra="R15", dica=dica)
        for prefixo, chave, lista in (("p", "principais", principais), ("r", "radar", radar)):
            for indice, item in enumerate(lista):
                c = "%s[%d]" % (chave, indice)
                certo = "%s%d" % (prefixo, indice + 1)
                if isinstance(item, dict) and "id" in item and item["id"] != certo:
                    self.erro("R01", c + ".id", "é %s; deveria ser %s: os ids vão em ordem, sem pular e sem "
                              "repetir. Renumere (e acerte os ref dos gatilhos)."
                              % (_mostra(item["id"], 30), _mostra(certo)))
                self.item(item, c, chave == "principais")
        if self.estado == "completa":
            de_ia = sum(1 for item in radar if isinstance(item, dict) and item.get("categoria") == "ia")
            if isinstance(e.get("radar"), list) and de_ia < 3:
                self.erro("R15", "radar", "tem %s de IA (categoria 'ia'); a edição 'completa' pede 3 ou mais. "
                          "Acrescente, ou publique com estado 'reduzida' e diga em bastidores.limites."
                          % _conta(de_ia, "item", "itens"))
            if principais and not any(isinstance(item, dict) and item.get("categoria") == "geopolitica"
                                      for item in principais):
                self.erro("R15", "principais", "nenhuma principal é de geopolítica; a edição 'completa' pede 1 ou "
                          "mais. Troque uma das principais.")
        vistos = {}
        for posicao, (player, para, caminho) in enumerate(self.vetores):
            if posicao >= 2:
                self.erro("R11", caminho, "é o %dº vetor da edição, e valem no máximo 2. Fique com os 2 de ato "
                          "mais forte." % (posicao + 1))
            par = (player, para)
            if isinstance(player, str) and isinstance(para, str):
                if par in vistos:
                    self.erro("R11", caminho, "repete o par player e destino de %s (%s para %s). Vale um vetor só "
                              "por par na edição: tire um." % (vistos[par], player, para))
                vistos.setdefault(par, caminho)

    def item(self, item, cam, principal):
        dados = self.dados
        tipo = "principal" if principal else "radar"
        if not self.objeto(item, cam, tipo):
            return
        self.um_de(item, "categoria", cam, CATEGORIAS)
        self.texto(item, "titulo", cam, tipo)
        self.marca_de_exemplo(item.get("titulo"), cam + ".titulo")
        self.texto(item, "fato", cam, tipo)
        self.fontes(item, cam, principal)
        leitura = _le_fontes(dados, item)
        partidos = sorted(leitura["lados"], key=dados.posicao_do_partido)
        das_fontes = set(_limpo(f.get("url")) for f in _lista_de_objetos(item.get("fontes"))) - set([None])

        if principal:
            ataques = self.lista(item, "ataques", cam, 2, 4)
            lados = [self.ataque(ataque, "%s.ataques[%d]" % (cam, i), item, True) for i, ataque in enumerate(ataques)]
            if self.do_dia and len(ataques) >= 2 and None not in lados and len(set(lados)) < 2:
                self.erro("R06", cam + ".ataques", "todos os atiradores são de %s; a principal pede ataques de "
                          "veículos de 2 partidos ou mais. Troque um atirador por veículo de outro partido, ou "
                          "passe o item para o radar." % _mostra(lados[0]))
        elif "ataque" in item:
            self.ataque(item["ataque"], cam + ".ataque", item, False)

        confianca = self.um_de(item, "confianca", cam, ("alta", "media") if principal else CONFIANCAS)
        if self.do_dia and isinstance(item.get("fontes"), list):
            if principal:
                if len(partidos) < 2:
                    self.erro("R06", cam + ".fontes", "os veículos do mapa citados são de %s; a principal pede "
                              "fontes de veículos de 2 partidos ou mais (fonte 'outro' não conta). Acrescente "
                              "fonte de veículo de outro partido, ou passe o item para o radar."
                              % self._partidos_em_texto(partidos))
                if not leitura["forte"]:
                    self.erro("R06", cam + ".fontes", "nenhuma fonte forte; a principal pede 1 ou mais (veículo "
                              "com fatos alta no mapa, ou documento primário). Acrescente uma, ou passe o item "
                              "para o radar.")
            elif item["fontes"] and not leitura["forte"] and len(partidos) < 2:
                self.erro("R07", cam + ".fontes", "nenhuma fonte forte, e os veículos do mapa citados são de %s; "
                          "o radar pede 1 fonte forte, ou 2 fontes de veículos de partidos diferentes. Acrescente "
                          "uma fonte, ou corte o item." % self._partidos_em_texto(partidos))
            teto = _teto(leitura)
            if confianca and _ORDEM_DA_CONFIANCA[confianca] > _ORDEM_DA_CONFIANCA[teto]:
                if teto == "media":
                    falta = ("fonte do outro campo" if len(leitura["campos"]) < 2 else "uma fonte forte")
                    conserto = "Troque para 'media' ou acrescente %s." % falta
                elif principal:
                    conserto = "Acrescente fonte forte ou fonte de veículo de outro partido."
                else:
                    conserto = "Troque para 'baixa', ou acrescente fonte forte ou de outro partido."
                self.erro("R08", cam + ".confianca", "é %s, o teto pelas fontes é %s. %s"
                          % (_mostra(confianca), _mostra(teto), conserto))

        marca = self.booleano(item, "conflito_de_interesse", cam)
        precisa, casos = calcula_conflito(dados, item, self.do_dia)
        if precisa and marca is not True:
            self.erro("R19", cam + ".conflito_de_interesse", "deveria ser true: %s. Quem liga a marca é o "
                      "publica.py: publique de novo com publica.py edicao." % self._motivo_do_conflito(item, casos))
        if marca is True:
            if confianca == "alta":
                self.erro("R19", cam + ".confianca", "é 'alta', e item com conflito de interesse vai no máximo a "
                          "'media'. Troque para 'media'.")
            if self.do_dia and set(casos) & set("bcd") and len(partidos) < 2:
                self.erro("R19", cam + ".fontes", "a notícia envolve a Anthropic ou concorrente (%s), e os "
                          "veículos do mapa citados são de %s; pede fontes de veículos de 2 partidos ou mais, "
                          "também no radar. Acrescente fonte de outro partido, ou corte o item."
                          % (self._motivo_do_conflito(item, [c for c in casos if c != "a"]),
                             self._partidos_em_texto(partidos)))

        if "eixo" in item and self.objeto(item["eixo"], cam + ".eixo", "eixo"):
            eixo = item["eixo"]
            if "tema" in eixo:
                if not isinstance(eixo["tema"], str) or eixo["tema"] not in dados.temas:
                    self.erro("R02", cam + ".eixo.tema", "%s não é tema da régua. Vale um dos temas atuais: %s.%s"
                              % (_mostra(eixo["tema"], 30), _lista_em_texto(TEMAS_ATUAIS),
                                 _sugere(eixo["tema"], TEMAS_ATUAIS)))
                elif eixo["tema"] not in TEMAS_ATUAIS:
                    self.erro("R00", cam + ".eixo.tema", "%s é tema de história: ato de hoje não mexe nele. Vale "
                              "um dos temas atuais: %s. Troque, ou tire o eixo."
                              % (_mostra(eixo["tema"]), _lista_em_texto(TEMAS_ATUAIS)))
            self.um_de(eixo, "sentido", cam + ".eixo", SENTIDOS)
            self.texto(eixo, "porque", cam + ".eixo", "eixo")

        self.placar(item, cam, principal, confianca, leitura)

        no_item = {}  # player: (destino, caminho) do primeiro vetor dele neste item
        for indice, vetor in enumerate(self.lista(item, "vetores", cam, 0, 2 if principal else 1)):
            c = "%s.vetores[%d]" % (cam, indice)
            self.vetor(vetor, c, marca, leitura, das_fontes, partidos)
            player = vetor.get("player") if isinstance(vetor, dict) else None
            if not isinstance(player, str):
                continue
            if player in no_item and no_item[player][0] != vetor.get("para"):
                # O id do registro é data, item e player (ESQUEMA, seção 12): o segundo teria o id do primeiro.
                # O mesmo par player e destino já é acusado na conta da edição inteira.
                self.erro("R11", c + ".player", "%s já tem outro vetor neste item (%s), e o registro guarda um "
                          "vetor por player em cada item: o id dele é data, item e player. Fique com o do ato "
                          "mais forte e tire o outro." % (_mostra(player), no_item[player][1]))
            no_item.setdefault(player, (vetor.get("para"), c))

        dominios = self.lista(item, "dominios", cam, 0, 5)
        vistos = set()
        for indice, dominio in enumerate(dominios):
            c = "%s.dominios[%d]" % (cam, indice)
            if not isinstance(dominio, str) or dominio not in dados.dominios:
                self.erro("R02", c, "%s não é domínio da régua. Vale: %s.%s"
                          % (_mostra(dominio, 30), _lista_em_texto(dados.dominios), _sugere(dominio, dados.dominios)))
            elif dominio in vistos:
                self.erro("R00", c, "%s está repetido. Tire um." % _mostra(dominio))
            vistos.add(dominio if isinstance(dominio, str) else None)

        if "continuacao_de" in item:
            valor, c = item["continuacao_de"], cam + ".continuacao_de"
            lido = _RE_CONTINUACAO.fullmatch(valor) if isinstance(valor, str) else None
            if not lido or not comum.data_valida(lido.group(1)):
                self.erro("R00", c, "é %s; deveria ter a forma AAAA-MM-DD/p1 ou AAAA-MM-DD/r4: a edição e o item "
                          "que este continua. Corrija, ou tire o campo." % _mostra(valor, 30))
            elif self.data and lido.group(1) >= self.data:
                self.erro("R16", c, "aponta para %s, que não é anterior a esta edição (%s). Aponte para o item de "
                          "uma edição anterior, ou tire o campo." % (lido.group(1), self.data))

        if principal:
            self.so_da_principal(item, cam, dominios)

    def _partidos_em_texto(self, partidos):
        if not partidos:
            return "nenhum partido"
        return "%s (%s)" % (_conta(len(partidos), "partido só", "partidos"), ", ".join(partidos))

    def _motivo_do_conflito(self, item, casos):
        dados, motivos = self.dados, []
        if "a" in casos:
            motivos.append("a categoria é 'ia'")
        if "b" in casos:
            citados = [a.get("alvo") for a, _ in _ataques_do_item(item)]
            citados += [v.get("player") for v in _lista_de_objetos(item.get("vetores"))]
            nome = next((c for c in citados if isinstance(c, str) and c in dados.conflito_players), "")
            motivos.append("%s, alvo de ataque ou player de vetor, está na lista conflito da régua" % _mostra(nome))
        if "c" in casos:
            achado = None
            for texto in _textos_do_item(item):
                achado = dados.re_termos.search(texto)
                if achado:
                    break
            motivos.append("o texto cita %s, termo da lista conflito da régua" % _mostra(achado.group() if achado else ""))
        if "d" in casos:
            nome = next((f.get("veiculo") for f in _lista_de_objetos(item.get("fontes"))
                         if f.get("veiculo") in dados.ligados), "")
            motivos.append("a fonte %s é de veículo ligado à Anthropic" % _mostra(nome))
        return "; ".join(motivos) if motivos else "a marca foi ligada à mão"

    def fontes(self, item, cam, principal):
        dados = self.dados
        lista = self.lista(item, "fontes", cam, 3 if principal else 1, 8 if principal else 4,
                           regra_do_minimo="R06" if principal else "R07")
        vistos = {}
        for indice, fonte in enumerate(lista):
            c = "%s.fontes[%d]" % (cam, indice)
            if not self.objeto(fonte, c, "fonte"):
                continue
            primaria = self.booleano(fonte, "primaria", c)
            url = self.url(fonte, "url", c)
            veiculo = fonte.get("veiculo", _FALTA)
            if veiculo is _FALTA:
                pass
            elif not isinstance(veiculo, str) or not veiculo:
                self.erro("R00", c + ".veiculo", "deveria ser o id de um veículo do mapa, ou 'outro', e é %s. Corrija."
                          % _mostra(veiculo, 30))
            elif veiculo == "outro":
                if "nome" not in fonte:
                    self.erro("R04", c + ".nome", "falta: fonte de veículo 'outro' pede o nome de quem publicou. "
                              "Acrescente.")
                if self.do_dia and primaria is True and url and not comum.url_bate(url, dados.oficiais):
                    self.erro("R22", c + ".primaria", "é true, e o site %s não é oficial: fonte fora do mapa só é "
                              "primária em site que bate com sites_oficiais da régua. Tire a marca, ou troque a "
                              "fonte pelo documento oficial." % _mostra(comum.site_de(url)))
            else:
                if "nome" in fonte:
                    self.erro("R04", c + ".nome", "só vale com veiculo 'outro', e esta fonte é de %s. Tire o campo."
                              % _mostra(veiculo))
                ficha = dados.mapa.get(veiculo)
                if self.do_dia and ficha is None:
                    self.erro("R02", c + ".veiculo", "%s não está no mapa de veículos. Use o id do mapa.txt; se o "
                              "veículo não está lá, use 'outro' com nome.%s"
                              % (_mostra(veiculo), _sugere(veiculo, dados.mapa)))
                elif self.do_dia and primaria is True and ficha["tipo"] not in TIPOS_PRIMARIOS:
                    self.erro("R22", c + ".primaria", "é true, e %s é veículo de tipo %s: só veículo de tipo "
                              "'oficial' ou 'dados' é fonte primária. Tire a marca."
                              % (_mostra(veiculo), _mostra(ficha["tipo"])))
            self.texto(fonte, "nome", c, "fonte")
            self.texto(fonte, "titulo", c, "fonte", so_algarismos=True)
            self.marca_de_exemplo(fonte.get("titulo"), c + ".titulo")
            if url:
                limpo = _limpo(url)
                if limpo in vistos:
                    self.erro("R05", c + ".url", "é o mesmo endereço de fontes[%d]. A mesma página não conta duas "
                              "vezes: tire uma." % vistos[limpo])
                vistos.setdefault(limpo, indice)
            publicado = self.uma_data(fonte, "publicado_em", c)
            if publicado and self.data:
                if publicado > comum.soma_dias(self.data, 1):
                    self.erro("R09", c + ".publicado_em", "é %s, mais de 1 dia depois da edição (%s). Fonte do "
                              "futuro não vale: corrija a data." % (publicado, self.data))
                elif primaria is not True and publicado < comum.soma_dias(self.data, -2):
                    self.erro("R09", c + ".publicado_em", "é %s, mais de 2 dias antes da edição (%s). Fonte velha "
                              "não prova fato do dia: troque a fonte (só documento primário pode ser mais antigo)."
                              % (publicado, self.data))

    def ataque(self, ataque, c, item, principal):
        """Confere um ataque. Devolve o lado do veículo no mapa (edição do dia, veículo conhecido), ou None."""
        dados = self.dados
        veiculo = ataque.get("veiculo") if isinstance(ataque, dict) else None
        ficha = dados.mapa.get(veiculo) if isinstance(veiculo, str) and veiculo != "outro" else None
        # Sem veículo conhecido não há lado para copiar: acusa o veículo, e não a falta do campo calculado.
        if not self.objeto(ataque, c, "ataque", dispensados=("lado",) if self.do_dia and ficha is None else ()):
            return None
        lado_no_mapa = None
        if "veiculo" in ataque:
            if not isinstance(veiculo, str) or not veiculo:
                self.erro("R00", c + ".veiculo", "deveria ser o id de um veículo do mapa, e é %s. Corrija."
                          % _mostra(veiculo, 30))
            elif veiculo == "outro":
                self.erro("R04", c + ".veiculo", "veículo fora do mapa ('outro') pode ser fonte, nunca atirador: o "
                          "INFOCENARIUM não sabe de que lado ele está. Troque o atirador por veículo do mapa.")
            elif self.do_dia:
                if ficha is None:
                    self.erro("R02", c + ".veiculo", "%s não está no mapa de veículos. Use o id do mapa.txt.%s"
                              % (_mostra(veiculo), _sugere(veiculo, dados.mapa)))
                else:
                    lado_no_mapa = ficha["lado"]
                    if "lado" in ataque and ataque["lado"] != ficha["lado"]:
                        self.erro("R03", c + ".lado", "é %s, o mapa diz %s para %s. %s"
                                  % (_mostra(ataque["lado"], 30), _mostra(ficha["lado"]), _mostra(veiculo),
                                     _CONSERTO_DO_CALCULADO))
                    if principal and ficha["lado_confianca"] not in ("alta", "media"):
                        self.erro("R03", c + ".veiculo", "%s tem lado incerto no mapa (lado_confianca %s), e "
                                  "veículo de lado incerto não atira em principal. Troque o atirador, ou passe "
                                  "o item para o radar." % (_mostra(veiculo), _mostra(ficha["lado_confianca"])))
        if "lado" in ataque and (not isinstance(ataque["lado"], str) or ataque["lado"] not in dados.partidos):
            self.erro("R02", c + ".lado", "%s não é partido da régua. %s"
                      % (_mostra(ataque["lado"], 30), _CONSERTO_DO_CALCULADO))
        if "alvo" in ataque:
            alvo = ataque["alvo"]
            if alvo == "outro":
                if "alvo_nome" not in ataque:
                    self.erro("R04", c + ".alvo_nome", "falta: alvo 'outro' pede o nome de quem é o alvo. Acrescente.")
            else:
                if "alvo_nome" in ataque:
                    self.erro("R04", c + ".alvo_nome", "só vale com alvo 'outro', e o alvo é %s. Tire o campo."
                              % _mostra(alvo, 30))
                if not isinstance(alvo, str) or not (alvo == "nenhum" or alvo in dados.players
                                                     or alvo in self.ids_novos or alvo in dados.partidos):
                    self.erro("R02", c + ".alvo", "%s não é player, partido, 'outro' nem 'nenhum'. Use o id de "
                              "players.json ou do partido; se o alvo não tem ficha, 'outro' com alvo_nome; se o "
                              "texto só relata, 'nenhum'.%s"
                              % (_mostra(alvo, 30), _sugere(alvo, list(dados.players) + dados.partidos)))
        self.texto(ataque, "alvo_nome", c, "ataque")
        self.texto(ataque, "enquadramento", c, "ataque")
        self.texto(ataque, "omite", c, "ataque")
        url = self.url(ataque, "url", c)
        if url and isinstance(item.get("fontes"), list):
            limpo = _limpo(url)
            mesmas = [f for f in _lista_de_objetos(item["fontes"]) if _limpo(f.get("url")) == limpo]
            if not mesmas:
                self.erro("R05", c + ".url", "não aparece em fontes deste item. A página do atirador também é "
                          "fonte: acrescente-a em fontes, com o mesmo veiculo, ou corrija o endereço.")
            elif isinstance(veiculo, str) and not any(f.get("veiculo") == veiculo for f in mesmas):
                self.erro("R05", c + ".url", "em fontes, esse endereço é de %s, e o ataque diz %s. O atirador é o "
                          "dono da página: acerte o veiculo num dos dois."
                          % (_mostra(mesmas[0].get("veiculo"), 30), _mostra(veiculo)))
        return lado_no_mapa

    def placar(self, item, cam, principal, confianca, leitura):
        dados = self.dados
        linhas = self.lista(item, "placar", cam, 0, 4 if principal else 2)
        vistos = set()
        for indice, linha in enumerate(linhas):
            c = "%s.placar[%d]" % (cam, indice)
            if not self.objeto(linha, c, "placar"):
                continue
            if "partido" in linha:
                partido = linha["partido"]
                if not isinstance(partido, str) or partido not in dados.partidos:
                    self.erro("R02", c + ".partido", "%s não é partido da régua. Vale: %s.%s"
                              % (_mostra(partido, 30), _lista_em_texto(dados.partidos), _sugere(partido, dados.partidos)))
                elif partido in vistos:
                    self.erro("R10", c + ".partido", "%s já tem linha neste placar, e vale no máximo uma linha por "
                              "partido em cada item. Junte as duas numa." % _mostra(partido))
                else:
                    vistos.add(partido)
            self.um_de(linha, "efeito", c, EFEITOS)
            forca = self.inteiro(linha, "forca", c, 1, 3)
            evidencia = self.um_de(linha, "evidencia", c, dados.evidencias)
            if forca and evidencia == "narrativa" and forca != 1:
                self.erro("R10", c + ".forca", "é %d com evidência 'narrativa', que só vale força 1. Baixe para 1, "
                          "ou troque a evidência pelo que mudou de fato." % forca)
            if self.do_dia and not principal and forca == 3 and not leitura["forte"]:
                self.erro("R10", c + ".forca", "é 3, e no radar força 3 pede fonte forte no item, que não há. "
                          "Baixe para 2, ou acrescente fonte forte.")
            self.texto(linha, "porque", c, "placar")
        if isinstance(item.get("placar"), list):
            if linhas and confianca == "baixa":
                self.erro("R10", cam + ".placar", "o item tem confiança 'baixa', e item assim não tem placar. "
                          "Esvazie o placar e escreva sem_placar.")
            elif linhas and "sem_placar" in item:
                self.erro("R10", cam + ".sem_placar", "só vale com o placar vazio, e o placar tem %s. Tire o campo."
                          % _conta(len(linhas), "linha", "linhas"))
            if not linhas and "sem_placar" not in item:
                self.erro("R10", cam + ".sem_placar", "falta: o placar está vazio, e é preciso dizer por que "
                          "ninguém ganha nem perde ainda. Acrescente sem_placar.")
        self.texto(item, "sem_placar", cam, "principal" if principal else "radar")

    def vetor(self, vetor, c, marca, leitura, das_fontes, partidos):
        dados = self.dados
        if not self.objeto(vetor, c, "vetor"):
            return
        player, para = vetor.get("player", _FALTA), vetor.get("para", _FALTA)
        partido_do_player, para_serve = None, False
        if player is not _FALTA:
            if isinstance(player, str) and player in self.ids_novos:
                self.erro("R11", c + ".player", "%s é o player novo desta edição, e vetor só vale para quem já "
                          "estava em players.json. Tire o vetor." % _mostra(player))
            elif not isinstance(player, str) or player not in dados.players:
                self.erro("R11", c + ".player", "%s não existe em players.json. Vetor só de player da régua: "
                          "corrija o id, ou tire o vetor.%s" % (_mostra(player, 30), _sugere(player, dados.players)))
            else:
                partido_do_player = dados.partido_do_player(player)
        if para is not _FALTA:
            if not isinstance(para, str) or para not in dados.partidos:
                self.erro("R02", c + ".para", "%s não é partido da régua. Vale: %s.%s"
                          % (_mostra(para, 30), _lista_em_texto(dados.partidos), _sugere(para, dados.partidos)))
            elif para == "independentes":
                self.erro("R11", c + ".para", "'independentes' não é destino de vetor: quem é independente não "
                          "tem bancada para onde ir. Troque o destino, ou tire o vetor.")
            elif para == partido_do_player:
                self.erro("R11", c + ".para", "%s é o partido do próprio player. Vetor é deslocamento para OUTRO "
                          "partido: troque o destino, ou tire o vetor." % _mostra(para))
            else:
                para_serve = True
        self.inteiro(vetor, "forca", c, 1, 3)
        if "tema" in vetor:
            tema = vetor["tema"]
            if tema != "ordem" and tema not in TEMAS_ATUAIS:
                self.erro("R11", c + ".tema", "é %s; vale um tema atual (%s) ou 'ordem'. Troque."
                          % (_mostra(tema, 30), _lista_em_texto(TEMAS_ATUAIS)))
            elif tema != "ordem" and para_serve and partido_do_player is not None and self.do_dia:
                # Voto típico é da régua, que o dono revê: só vale na edição do dia (ESQUEMA, seção 10).
                destino = dados.voto.get(para, {}).get(tema)
                origem = dados.voto.get(partido_do_player, {}).get(tema)
                if destino not in ("B", "R"):
                    self.erro("R11", c + ".para", "%s não tem posição firme em %s (voto típico %s). Vetor de tema "
                              "pede destino com voto B ou R: troque o destino, ou use o tema 'ordem'."
                              % (_mostra(para), _mostra(tema), _mostra(destino)))
                elif origem == destino:
                    self.erro("R11", c + ".para", "em %s, %s vota igual ao partido do player (%s): %s. Não há "
                              "deslocamento: troque o destino ou o tema, ou tire o vetor."
                              % (_mostra(tema), _mostra(para), partido_do_player, destino))
        self.texto(vetor, "porque", c, "vetor")
        url = self.url(vetor, "url", c)
        if url:
            limpo = _limpo(url)
            if limpo not in das_fontes:
                self.erro("R05", c + ".url", "não aparece em fontes deste item. A prova do vetor é uma das fontes: "
                          "acrescente-a, ou corrija o endereço.")
            elif self.do_dia and limpo not in leitura["fortes"]:
                self.erro("R11", c + ".url", "a prova do vetor tem de ser fonte forte (veículo com fatos alta, ou "
                          "documento primário), e esta não é. Troque a prova, ou tire o vetor.")
            elif marca is True and limpo not in leitura["primarias"]:
                self.erro("R19", c + ".url", "o item tem conflito de interesse, e nele a prova do vetor tem de ser "
                          "fonte primária (primaria: true). Esta não é: troque a prova, ou tire o vetor.")
        if self.do_dia and len(partidos) < 2:
            self.erro("R11", c, "vetor pede item com fontes de veículos de 2 partidos ou mais, e as deste item são "
                      "de %s. Acrescente fonte de veículo de outro partido, ou tire o vetor."
                      % self._partidos_em_texto(partidos))
        self.vetores.append((player if isinstance(player, str) else None, para if isinstance(para, str) else None, c))

    def so_da_principal(self, item, cam, dominios):
        if "nao_confirmado" in item:
            for indice, texto in enumerate(self.lista(item, "nao_confirmado", cam, 0, 3)):
                c = "%s.nao_confirmado[%d]" % (cam, indice)
                texto = self.um_texto(texto, c, MAXIMOS[("principal", "nao_confirmado")])
                if texto is not None and not texto.startswith("Segundo "):
                    self.erro("R00", c, "deveria começar com 'Segundo ' e dizer quem afirma. Reescreva: "
                              "'Segundo …, …'.")
        if "realmente" in item:
            realmente, c = item["realmente"], cam + ".realmente"
            if not isinstance(realmente, str):
                self.erro("R00", c, "deveria ser texto, e é %s. Escreva o dossiê entre aspas." % _nome_do_tipo(realmente))
            else:
                if len(realmente) < REALMENTE_MINIMO:
                    self.erro("R23", c, "tem %d caracteres; o dossiê pede de %d a %d. Escreva mais %d: responda às "
                              "4 perguntas do dossiê." % (len(realmente), REALMENTE_MINIMO, REALMENTE_MAXIMO,
                                                           REALMENTE_MINIMO - len(realmente)))
                elif len(realmente) > REALMENTE_MAXIMO:
                    self.erro("R23", c, "tem %d caracteres; o dossiê pede de %d a %d. Corte %d."
                              % (len(realmente), REALMENTE_MINIMO, REALMENTE_MAXIMO, len(realmente) - REALMENTE_MAXIMO))
                if realmente.strip():
                    for mensagem in confere_texto(realmente):
                        self.erro("R17", c, mensagem)
        for indice, texto in enumerate(self.lista(item, "na_pratica", cam, 1, 4)):
            self.um_texto(texto, "%s.na_pratica[%d]" % (cam, indice), MAXIMOS[("principal", "na_pratica")])
        if isinstance(item.get("dominios"), list):
            if dominios and "no_brasil" not in item:
                self.erro("R23", cam + ".no_brasil", "falta: a notícia toca domínio de alerta (dominios não é "
                          "vazia), e é preciso dizer o que ela muda no Brasil. Acrescente no_brasil, ou esvazie "
                          "dominios.")
            elif not dominios and "no_brasil" in item:
                self.erro("R23", cam + ".no_brasil", "só vale quando dominios não é vazia. Tire o campo, ou diga "
                          "em dominios que domínio a notícia toca.")
        self.texto(item, "no_brasil", cam, "principal")
        for indice, texto in enumerate(self.lista(item, "vigiar", cam, 1, 3)):
            c = "%s.vigiar[%d]" % (cam, indice)
            texto = self.um_texto(texto, c, MAXIMOS[("principal", "vigiar")])
            if texto is not None and (not texto.rstrip().endswith("?") or not _datas_dd_mm(texto)):
                self.erro("R21", c, "deveria ser pergunta de sim ou não, terminar com '?' e trazer a data limite "
                          "no formato DD/MM. Ex.: 'A lei é sancionada até 30/11?'. Reescreva.")
            elif texto is not None and indice == 0 and self.do_dia and self.data:
                # Só a primeira: é a que o publica.py contexto devolve quando o prazo vence (vigiar_vencendo).
                prazo = prazo_do_vigiar(texto, self.data)
                if prazo is None or comum.dias_entre(self.data, prazo) > DIAS_DO_PRAZO:
                    self.erro("R21", c, "o prazo é a última data DD/MM da pergunta (aqui, %s), e passa de %d dias "
                              "depois da edição: ponha a data limite por último, em até %d dias da edição. "
                              "Reescreva." % (comum.dd_mm_aaaa(prazo) if prazo else "sem data", DIAS_DO_PRAZO,
                                                  DIAS_DO_PRAZO))

    # ------------------------------------------------------------ alerta (seção 2; regras R13 a R15)

    def alerta(self):
        e, dados = self.e, self.dados
        if "alerta" not in e or not self.objeto(e["alerta"], "alerta", "alerta"):
            return
        alerta = e["alerta"]
        self.texto(alerta, "motivo", "alerta", "alerta")
        geral = self.inteiro(alerta, "nivel", "alerta", 1, 5, conserto=_CONSERTO_DO_CALCULADO)
        tendencia_geral = self.um_de(alerta, "tendencia", "alerta", TENDENCIAS)
        lista = self.lista(alerta, "dominios", "alerta")
        if isinstance(alerta.get("dominios"), list):
            ids = [d.get("id") if isinstance(d, dict) else None for d in lista]
            if ids != dados.dominios:
                self.erro("R00", "alerta.dominios", "traz %s; deveriam ser exatamente os %d domínios da régua, "
                          "nesta ordem: %s. Acerte a lista." % (_mostra(ids), len(dados.dominios),
                                                                _lista_em_texto(dados.dominios)))
        conta = _analisa_alerta(dados, e, self.historico, self.do_dia)
        de_preco = calcula_gatilhos_de_preco(dados, e.get("indicadores"), self.data) if self.do_dia else {}
        niveis = []
        for indice, dominio in enumerate(lista):
            c = "alerta.dominios[%d]" % indice
            if not self.objeto(dominio, c, "dominio"):
                continue
            identificador = dominio.get("id")
            calculo = conta["dominios"].get(identificador) if isinstance(identificador, str) else None
            if calculo is not None and calculo["escrito"] is not dominio:
                calculo = None  # id repetido: a conta é do primeiro; a lista errada já foi acusada acima
            nivel = self.inteiro(dominio, "nivel", c, 1, 5, conserto=_CONSERTO_DO_CALCULADO)
            tendencia = self.um_de(dominio, "tendencia", c, TENDENCIAS)
            desde = self.uma_data(dominio, "desde", c)
            if desde and self.data and desde > self.data:
                self.erro("R14", c + ".desde", "é %s, depois da data da edição (%s). O nível não começa no futuro. %s"
                          % (desde, self.data, _CONSERTO_DO_CALCULADO))
                desde = None
            self.texto(dominio, "leitura", c, "dominio")
            self.texto(dominio, "vigiar", c, "dominio")
            sem_preco = dominio.get("sem_preco", _FALTA)
            if sem_preco is not _FALTA and (not isinstance(sem_preco, list)
                                            or any(not isinstance(i, str) for i in sem_preco)):
                self.erro("R00", c + ".sem_preco", "deveria ser lista de ids de indicador (vazia quando o preço foi "
                          "medido), e é %s. %s" % (_mostra(sem_preco, 30), _CONSERTO_DO_CALCULADO))
                sem_preco = _FALTA
            gatilhos = self.lista(dominio, "gatilhos", c, 0, 6)
            if nivel is not None:
                niveis.append(nivel)
            if self.estado == "falha" and gatilhos:
                self.erro("R15", c + ".gatilhos", "tem %s, e edição 'falha' não tem gatilho nenhum. Esvazie a lista."
                          % _conta(len(gatilhos), "gatilho", "gatilhos"))
            if calculo is None:
                continue
            self.gatilhos(gatilhos, c, identificador, calculo)
            if self.do_dia and sem_preco is not _FALTA and sem_preco != calculo["sem_preco"]:
                self.erro("R13f", c + ".sem_preco", "é %s; pelos indicadores de hoje deveria ser %s (os indicadores "
                          "de preço do domínio que faltam, estão sem valor, defasados ou sem a variação de 7 dias). "
                          "%s" % (_mostra(sem_preco), _mostra(calculo["sem_preco"]), _CONSERTO_DO_CALCULADO))
            if self.do_dia and self.estado != "falha":
                self.precos(c, identificador, calculo, de_preco.get(identificador, {}))
            self.niveis(c, calculo, nivel, tendencia, desde)
        for extra in self.excecoes[1:]:
            self.erro("R13d", extra + ".excecao", "já há outra exceção na edição (%s), e vale no máximo 1. Tire uma "
                      "das duas." % self.excecoes[0])
        if geral is not None and niveis and geral != max(niveis):
            self.erro("R14", "alerta.nivel", "é %d; deveria ser o maior nível entre os domínios, que é %d. %s"
                      % (geral, max(niveis), _CONSERTO_DO_CALCULADO))
        if self.historico is not None and tendencia_geral and tendencia_geral != conta["tendencia"]:
            anterior = conta["anterior"]
            self.erro("R14", "alerta.tendencia", "é %s; deveria ser %s: o nível geral de hoje é %d e o da edição "
                      "anterior %s. %s"
                      % (_mostra(tendencia_geral), _mostra(conta["tendencia"]), conta["nivel"],
                         "(%s) era %d" % (anterior.data, anterior.nivel_geral) if anterior else "não existe",
                         _CONSERTO_DO_CALCULADO))

    def gatilhos(self, lista, c, dominio, calculo):
        """Regras R13a, R13b, R13d e R13e nos gatilhos de um domínio."""
        de_evento = 0
        for indice, gatilho in enumerate(lista):
            cg = "%s.gatilhos[%d]" % (c, indice)
            lido = calculo["gatilhos"][indice]
            if not self.objeto(gatilho, cg, "gatilho"):
                continue
            self.texto(gatilho, "texto", cg, "gatilho")
            self.booleano(gatilho, "excecao", cg)
            self.booleano(gatilho, "alivio", cg)
            if lido["alvo"] != "indicador":
                de_evento += 1
            if "criterio" in gatilho:
                criterio = gatilho["criterio"]
                if not lido["criterio_ok"]:
                    self.erro("R13a", cg + ".criterio", "é %s; deveria ser o código de um critério da régua, na "
                              "forma dominio.nivel, com nível de 2 a 5 (aqui, de '%s.2' a '%s.5'). Corrija o código."
                              % (_mostra(criterio, 30), dominio, dominio))
                elif not lido["dominio_ok"]:
                    self.erro("R13a", cg + ".criterio", "%s é critério de outro domínio, e o gatilho está em %s. "
                              "Mude o gatilho para o domínio certo, ou troque o critério."
                              % (_mostra(criterio), _mostra(dominio)))
            if "ref" in gatilho and lido["alvo"] is None:
                self.erro("R13a", cg + ".ref", "%s não é item desta edição (p1…, r1…) nem indicador com dado hoje. "
                          "Aponte para o item de hoje que prova o gatilho." % _mostra(gatilho["ref"], 30))
            if not (lido["criterio_ok"] and lido["dominio_ok"]):
                continue
            if lido["alivio"]:
                if self.historico is None:
                    self.erro("R13e", cg + ".alivio", "alívio só se confere contra a edição anterior, e aqui não há "
                              "histórico (arquivo fora de edicoes/, sem --anterior). Tire o gatilho.")
                else:
                    for campo, mensagem in lido["recusas"]:
                        self.erro("R13e", _junta(cg, campo), mensagem)
                continue
            if lido["excecao"]:
                if lido["nivel"] > 3:
                    self.erro("R13d", cg + ".excecao", "exceção só vale em gatilho de nível 2 ou 3, e este é de "
                              "nível %d. Tire a exceção e use um critério da tabela, ou baixe o nível." % lido["nivel"])
                elif lido["alvo"] == "indicador":
                    self.erro("R13d", cg + ".excecao", "exceção só vale com ref de item, e este gatilho aponta para "
                              "o indicador %s. Tire a exceção." % _mostra(lido["ref"]))
                self.excecoes.append(cg)
            if lido["alvo"] == "item":
                self.prova(lido, cg, dominio)
        if de_evento > 4:
            self.erro("R00", c + ".gatilhos", "tem %d gatilhos de evento; o máximo é 4 (os de preço não contam). "
                      "Fique com os 4 mais graves." % de_evento)

    def prova(self, lido, cg, dominio):
        """Regra R13b: a prova que cada nível pede do item citado em `ref`."""
        item, nivel, ref = lido["item"], lido["nivel"], _mostra(lido["ref"])
        campo = cg + ".ref"
        if item["confianca"] not in ("alta", "media"):
            self.erro("R13b", campo, "%s tem confiança %s, e só item de confiança 'alta' ou 'media' prova gatilho. "
                      "Aponte para outro item, ou tire o gatilho." % (ref, _mostra(item["confianca"])))
            return
        if lido["continua"]:
            return  # estado que continua: vale principal ou radar, e não se pede de novo a fonte primária
        if nivel >= 3 and item["tipo"] != "principal":
            self.erro("R13b", campo, "nível %d exige principal, e %s é do radar. Baixe o critério para o nível 2 "
                      "ou tire o gatilho." % (nivel, ref))
        elif nivel >= 4 and item["confianca"] != "alta":
            self.erro("R13b", campo, "nível %d exige principal com confiança 'alta', e %s tem 'media'. Baixe o "
                      "critério para o nível 3 ou tire o gatilho." % (nivel, ref))
        elif nivel == 5 and not item["primaria"]:
            self.erro("R13b", campo, "nível 5 exige fonte primária (primaria: true) no item %s, e não há. Acrescente "
                      "o documento da autoridade, ou baixe o critério." % ref)
        elif nivel == 5 and self.do_dia and dominio in DOMINIOS_DO_BRASIL and not item["primaria_do_brasil"]:
            self.erro("R13b", campo, "nível 5 em %s exige, no item %s, fonte primária de site oficial do Brasil "
                      "(%s). Acrescente o documento da autoridade brasileira, ou baixe o critério."
                      % (_mostra(dominio), ref, _lista_em_texto(self.dados.oficiais_brasil)))

    def precos(self, c, dominio, calculo, esperados):
        """Regra R13c: o domínio traz exatamente os gatilhos de preço que os indicadores de hoje pedem."""
        declarados = OrderedDict()
        for indice, lido in enumerate(calculo["gatilhos"]):
            if lido["alvo"] == "indicador" and lido["criterio_ok"] and lido["dominio_ok"] and not lido["alivio"]:
                if lido["ref"] in declarados:
                    self.erro("R13c", "%s.gatilhos[%d].ref" % (c, indice), "o indicador %s já tem gatilho de preço "
                              "neste domínio. Vale um por indicador: tire um." % _mostra(lido["ref"]))
                declarados.setdefault(lido["ref"], (lido["nivel"], indice))
        conserto = "Gatilho de preço vem pronto do indicadores.py: rode-o e publique de novo com publica.py edicao."
        for indicador, nivel in esperados.items():
            if indicador not in declarados:
                self.erro("R13c", c + ".gatilhos", "falta o gatilho de preço de %s, que hoje cumpre o critério "
                          "'%s.%d'. %s" % (_mostra(indicador), dominio, nivel, conserto))
            elif declarados[indicador][0] != nivel:
                self.erro("R13c", "%s.gatilhos[%d].criterio" % (c, declarados[indicador][1]), "é '%s.%d', e a alta "
                          "de %s hoje vale '%s.%d' (alta de nível 3 ou 4 sem confirmado: true vale nível 2). %s"
                          % (dominio, declarados[indicador][0], _mostra(indicador), dominio, nivel, conserto))
        for indicador, (_, indice) in declarados.items():
            if indicador not in esperados:
                self.erro("R13c", "%s.gatilhos[%d]" % (c, indice), "%s não cumpre critério de preço de %s hoje "
                          "(só alta conta; indicador defasado ou sem variação não cumpre; critério de 1 dia só "
                          "vale no dia da cotação). Tire o gatilho: gatilho de preço não se escreve à mão."
                          % (_mostra(indicador), _mostra(dominio)))

    def niveis(self, c, calculo, nivel, tendencia, desde):
        """Regras R13, R14, R15 e H1: nível, tendência e desde de um domínio contra a conta."""
        anterior = calculo["N"]
        if self.historico is None:
            # Regra H1, sem histórico: aceita o nível dos gatilhos de hoje, ou maior se mantido desde antes.
            maior = calculo["T"]
            if nivel is None:
                return
            if nivel < maior:
                self.erro("R13", c + ".nivel", "é %d, e o maior gatilho de hoje é de nível %d: o nível não fica "
                          "abaixo dele. %s" % (nivel, maior, _CONSERTO_DO_CALCULADO))
            elif nivel > maior and not (desde and self.data and desde < self.data):
                self.erro("R13", c + ".nivel", "é %d, sem gatilho de hoje que sustente (o maior é de nível %d) e "
                          "sem `desde` anterior à edição, que mostraria nível mantido. %s"
                          % (nivel, maior, _CONSERTO_DO_CALCULADO))
            return
        if self.estado == "falha":
            regra, porque = "R15", "edição 'falha' repete o nível e o `desde` da edição anterior (sem anterior, 1)"
        else:
            regra, porque = "R13", self._explica(calculo)
        if nivel is not None and nivel != calculo["nivel"]:
            self.erro(regra, c + ".nivel", "é %d; a conta dá %d: %s. %s"
                      % (nivel, calculo["nivel"], porque, _CONSERTO_DO_CALCULADO))
        if tendencia and tendencia != calculo["tendencia"]:
            self.erro("R14", c + ".tendencia", "é %s; deveria ser %s: o nível de hoje é %d e o anterior era %d. %s"
                      % (_mostra(tendencia), _mostra(calculo["tendencia"]), calculo["nivel"], anterior,
                         _CONSERTO_DO_CALCULADO))
        if desde and desde != calculo["desde"]:
            self.erro("R15" if self.estado == "falha" else "R14", c + ".desde", "é %s; deveria ser %s (repete o da "
                      "edição anterior se o nível é o mesmo; senão é a data da edição). %s"
                      % (desde, calculo["desde"], _CONSERTO_DO_CALCULADO))

    def _explica(self, calculo):
        maior, anterior, calmas = calculo["T"], calculo["N"], calculo["S"]
        if calculo["ramo"] == "gatilho":
            return "o maior gatilho de hoje é de nível %d e o nível anterior era %d" % (maior, anterior)
        if calculo["ramo"] == "alivio":
            return "há gatilho de alívio válido, e o nível desce 1 do anterior (%d)" % anterior
        if calculo["ramo"] == "calma":
            return ("sem gatilho de nível %d há %d edições medidas, o nível desce 1 do anterior"
                    % (anterior, calmas))
        cego = ", e hoje falta dado de preço (%s)" % ", ".join(calculo["sem_preco"]) if calculo["sem_preco"] else ""
        return ("o maior gatilho de hoje é de nível %d, abaixo do anterior (%d), com %s%s: o nível se mantém"
                % (maior, anterior, _conta(calmas or 0, "edição calma", "edições calmas"), cego))

    # ------------------------------------------------------------ placar do dia, players, errata, bastidores

    def placar_do_dia(self):
        e, dados = self.e, self.dados
        lista = self.lista(e, "placar_do_dia", "", 0, 7)
        if not isinstance(e.get("placar_do_dia"), list):
            return
        if self.estado == "falha" and lista:
            self.erro("R15", "placar_do_dia", "edição 'falha' não tem placar do dia. Esvazie a lista.")
        esperado = calcula_placar_do_dia(dados, e)
        certo = OrderedDict((linha["partido"], linha) for linha in esperado)
        vistos = []
        for indice, linha in enumerate(lista):
            c = "placar_do_dia[%d]" % indice
            if not self.objeto(linha, c, "placar_do_dia"):
                continue
            self.texto(linha, "frase", c, "placar_do_dia")
            saldo = self.inteiro(linha, "saldo", c)
            narrativa = self.inteiro(linha, "narrativa", c)
            if "partido" not in linha:
                continue
            partido = linha["partido"]
            if not isinstance(partido, str) or partido not in dados.partidos:
                self.erro("R02", c + ".partido", "%s não é partido da régua. Vale: %s.%s"
                          % (_mostra(partido, 30), _lista_em_texto(dados.partidos), _sugere(partido, dados.partidos)))
            elif partido in vistos:
                self.erro("R12", c + ".partido", "%s está repetido no placar do dia. Vale uma linha por partido: "
                          "tire uma." % _mostra(partido))
            elif partido not in certo:
                self.erro("R12", c + ".partido", "%s não aparece em nenhum placar de hoje, e o placar do dia só "
                          "traz quem aparece. Tire a linha." % _mostra(partido))
            else:
                vistos.append(partido)
                if saldo is not None and saldo != certo[partido]["saldo"]:
                    self.erro("R12", c + ".saldo", "é %d; a soma das forças de hoje dá %d (ganha soma, perde "
                              "subtrai, e linha de narrativa não entra). %s"
                              % (saldo, certo[partido]["saldo"], _CONSERTO_DO_CALCULADO))
                if narrativa is not None and narrativa != certo[partido]["narrativa"]:
                    self.erro("R12", c + ".narrativa", "é %d; as linhas de narrativa de hoje dão %d (a favor menos "
                              "contra). %s" % (narrativa, certo[partido]["narrativa"], _CONSERTO_DO_CALCULADO))
        faltam = [partido for partido in certo if partido not in vistos]
        if faltam:
            self.erro("R12", "placar_do_dia", "falta %s, que aparece em placar de hoje. Acrescente uma linha para "
                      "cada partido que falta, com a frase do dia dele." % _lista_em_texto(_mostra(f) for f in faltam))
        ordem = [partido for partido in certo if partido in vistos]
        if vistos != ordem:
            self.erro("R12", "placar_do_dia", "fora de ordem: está %s, e a ordem é maior saldo primeiro, com "
                      "empate na ordem da régua: %s. %s"
                      % (_lista_em_texto(vistos), _lista_em_texto(ordem), _CONSERTO_DO_CALCULADO))

    def novos_players(self):
        e, dados = self.e, self.dados
        lista = self.lista(e, "novos_players", "", 0, 1, regra="R20",
                           dica=" Os outros ficam em bastidores.candidatos.")
        if self.estado == "falha" and lista:
            self.erro("R15", "novos_players", "edição 'falha' não tem player novo. Esvazie a lista.")
        for indice, novo in enumerate(lista):
            c = "novos_players[%d]" % indice
            if not self.objeto(novo, c, "novo_player"):
                continue
            if "id" in novo:
                identificador = novo["id"]
                if not isinstance(identificador, str) or not _RE_SLUG.fullmatch(identificador):
                    self.erro("R00", c + ".id", "é %s; deveria ter de 2 a 31 letras minúsculas, algarismos ou "
                              "sublinhado, começando por letra (ex.: 'arabia_saudita'). Corrija."
                              % _mostra(identificador, 30))
                elif identificador in dados.partidos or identificador in ALVOS_ESPECIAIS:
                    self.erro("R20", c + ".id", "%s é id de partido ou palavra reservada, e não pode ser id de "
                              "player. Escolha outro id." % _mostra(identificador))
                else:
                    ficha = dados.players.get(identificador)
                    proprio = (ficha is not None and ficha.get("origem") == "rotina"
                               and ficha.get("incluido_em") == self.data)
                    if ficha is not None and not proprio:
                        self.erro("R20", c + ".id", "%s já é player da régua (players.json). Player novo é quem "
                                  "ainda não tem ficha: tire o item de novos_players." % _mostra(identificador))
            self.texto(novo, "nome", c, "novo_player")
            if "tipo" in novo and novo["tipo"] not in TIPOS_DE_PLAYER_NOVO:
                self.erro("R20", c + ".tipo", "é %s; a rotina só registra %s (nunca 'regime'). Troque."
                          % (_mostra(novo["tipo"], 30), _lista_em_texto(TIPOS_DE_PLAYER_NOVO)))
            partido_serve = False
            if "partido" in novo:
                if not isinstance(novo["partido"], str) or novo["partido"] not in dados.partidos:
                    self.erro("R02", c + ".partido", "%s não é partido da régua. Vale: %s."
                              % (_mostra(novo["partido"], 30), _lista_em_texto(dados.partidos)))
                else:
                    partido_serve = True
            self.um_de(novo, "time", c, dados.times)
            if "time_discutivel" in novo and novo["time_discutivel"] is not True:
                self.erro("R20", c + ".time_discutivel", "é %s; em player novo é sempre true: quem confirma o time "
                          "é o dono. Troque." % _mostra(novo["time_discutivel"], 30))
            conhecidas = None
            if "dna" in novo:
                dna = novo["dna"]
                if not isinstance(dna, dict):
                    self.erro("R00", c + ".dna", "deveria ser um objeto com os temas da régua, e é %s. Corrija."
                              % _nome_do_tipo(dna))
                else:
                    faltam = [t for t in dados.temas if t not in dna]
                    sobram = [t for t in dna if t not in dados.temas]
                    if faltam or sobram:
                        self.erro("R20", c + ".dna", "deveria ter exatamente os %d temas da régua. Faltam: %s. "
                                  "Sobram: %s. Acerte as chaves (tema sem posição leva 'W')."
                                  % (len(dados.temas), _lista_em_texto(faltam), _lista_em_texto(sobram)))
                    conhecidas = []
                    for tema in dados.temas:
                        if tema not in dna:
                            continue
                        if dna[tema] not in ("B", "R", "Y", "W"):
                            self.erro("R20", "%s.dna.%s" % (c, tema), "é %s; a rotina só registra B, R, Y ou W "
                                      "(sem virada e sem K). Troque." % _mostra(dna[tema], 30))
                        elif dna[tema] != "W":
                            conhecidas.append(tema)
                    if len(conhecidas) < 4:
                        self.erro("R20", c + ".dna", "tem %s (diferentes de W); com menos de 4 o ator não entra na "
                                  "régua. Tire-o de novos_players e deixe em bastidores.candidatos, com as "
                                  "posições achadas no motivo." % _conta(len(conhecidas), "posição conhecida",
                                                                         "posições conhecidas"))
                    if partido_serve and self.do_dia:  # a conta usa o voto típico da régua: (dia)
                        certo = partido_pelo_dna(dados, dna)
                        if novo["partido"] != certo:
                            self.erro("R20", c + ".partido", "é %s; a conta das posições dá %s (o partido de "
                                      "voto_tipico com mais posições iguais às do dna; empate dá "
                                      "'independentes'). Troque." % (_mostra(novo["partido"]), _mostra(certo)))
            if "dna_fontes" in novo:
                fontes = novo["dna_fontes"]
                if not isinstance(fontes, dict):
                    self.erro("R00", c + ".dna_fontes", "deveria ser um objeto de tema para URL, e é %s. Corrija."
                              % _nome_do_tipo(fontes))
                else:
                    if conhecidas is not None:
                        faltam = [t for t in conhecidas if t not in fontes]
                        sobram = [t for t in fontes if t not in conhecidas]
                        if faltam or sobram:
                            self.erro("R20", c + ".dna_fontes", "deveria ter uma URL para cada posição conhecida "
                                      "do dna, e só para elas. Faltam: %s. Sobram: %s. Acerte."
                                      % (_lista_em_texto(faltam), _lista_em_texto(sobram)))
                    for tema, endereco in fontes.items():
                        self.uma_url(endereco, "%s.dna_fontes.%s" % (c, tema) if tema in dados.temas
                                     else c + ".dna_fontes")
            for indice_d, tema in enumerate(self.lista(novo, "duvidas", c)):
                if not isinstance(tema, str) or tema not in dados.temas:
                    self.erro("R20", "%s.duvidas[%d]" % (c, indice_d), "%s não é tema da régua. Vale: %s."
                              % (_mostra(tema, 30), _lista_em_texto(dados.temas)))
            self.texto(novo, "nota", c, "novo_player")
            self.texto(novo, "justificativa", c, "novo_player")
            self.url(novo, "url", c)

    def errata_e_respostas(self):
        e = self.e
        erratas = self.lista(e, "errata", "", 0, 5)
        if self.estado == "falha" and erratas:
            self.erro("R15", "errata", "edição 'falha' não tem errata. Esvazie a lista.")
        for indice, errata in enumerate(erratas):
            c = "errata[%d]" % indice
            if not self.objeto(errata, c, "errata"):
                continue
            edicao = self.uma_data(errata, "edicao", c)
            if edicao and self.data and edicao >= self.data:
                self.erro("R16", c + ".edicao", "é %s, que não é anterior a esta edição (%s). Errata corrige edição "
                          "anterior: acerte a data, ou tire a errata." % (edicao, self.data))
            if "item" in errata and not (isinstance(errata["item"], str) and _RE_ID_DE_ITEM.fullmatch(errata["item"])):
                self.erro("R00", c + ".item", "é %s; deveria ser id de item (p1 a p3, r1 a r12). Corrija, ou tire o "
                          "campo: sem ele a errata vale para a edição toda." % _mostra(errata["item"], 30))
            self.texto(errata, "erro", c, "errata")
            self.texto(errata, "correcao", c, "errata")
            self.url(errata, "url", c)
            self.texto(errata, "anula_vetor", c, "errata")
            if "anula_vetor" in errata and "url" not in errata:
                self.erro("R16", c + ".url", "falta: errata que anula vetor pede url, a fonte da correção. Acrescente.")
        respostas = self.lista(e, "respostas", "", 0, 3)
        if self.estado == "falha" and respostas:
            self.erro("R15", "respostas", "edição 'falha' não tem respostas. Esvazie a lista.")
        for indice, resposta in enumerate(respostas):
            c = "respostas[%d]" % indice
            if not self.objeto(resposta, c, "resposta"):
                continue
            edicao = self.uma_data(resposta, "edicao", c)
            if edicao and self.data and edicao >= self.data:
                self.erro("R16", c + ".edicao", "é %s, que não é anterior a esta edição (%s). A resposta é para "
                          "pergunta de edição anterior: acerte a data." % (edicao, self.data))
            if "item" in resposta and not (isinstance(resposta["item"], str)
                                           and _RE_ID_DE_PRINCIPAL.fullmatch(resposta["item"])):
                self.erro("R16", c + ".item", "é %s; deveria ser id de principal (p1, p2 ou p3): só principal faz "
                          "pergunta de vigiar. Corrija." % _mostra(resposta["item"], 30))
            self.texto(resposta, "pergunta", c, "resposta")
            valor = self.um_de(resposta, "resposta", c, RESPOSTAS)
            self.texto(resposta, "texto", c, "resposta")
            if "url" in resposta:
                self.url(resposta, "url", c)
            elif valor in ("sim", "nao"):
                self.erro("R16", c + ".url", "falta: resposta %s pede url, a fonte da resposta. Acrescente, ou "
                          "troque a resposta para 'sem_dado'." % _mostra(valor))

    def bastidores(self):
        e = self.e
        if "bastidores" not in e or not self.objeto(e["bastidores"], "bastidores", "bastidores"):
            return
        bastidores = e["bastidores"]
        self.um_de(bastidores, "modo", "bastidores", MODOS)
        for chave in _CAMPOS_DE_CONTAGEM:
            self.inteiro(bastidores, chave, "bastidores", 0)
        consultados = bastidores.get("veiculos_consultados")
        if _e_inteiro(consultados) and consultados >= 0 and consultados != calcula_veiculos_consultados(e):
            self.erro("R12", "bastidores.veiculos_consultados", "é %d; as fontes de hoje citam %d veículos "
                      "distintos do mapa. %s" % (consultados, calcula_veiculos_consultados(e), _CONSERTO_DO_CALCULADO))
        for indice, candidato in enumerate(self.lista(bastidores, "candidatos", "bastidores", 0, 5)):
            c = "bastidores.candidatos[%d]" % indice
            if not self.objeto(candidato, c, "candidato"):
                continue
            if "id" in candidato and not (isinstance(candidato["id"], str) and _RE_SLUG.fullmatch(candidato["id"])):
                self.erro("R00", c + ".id", "é %s; deveria ter de 2 a 31 letras minúsculas, algarismos ou "
                          "sublinhado, começando por letra (ex.: 'arabia_saudita'). Corrija."
                          % _mostra(candidato["id"], 30))
            self.texto(candidato, "nome", c, "candidato")
            self.texto(candidato, "motivo", c, "candidato")
        for indice, sugerido in enumerate(self.lista(bastidores, "veiculos_sugeridos", "bastidores", 0, 5)):
            c = "bastidores.veiculos_sugeridos[%d]" % indice
            sugerido = self.um_texto(sugerido, c, MAXIMOS[("bastidores", "veiculos_sugeridos")])
            if sugerido is not None and not _RE_SUGERIDO.fullmatch(sugerido):
                self.erro("R00", c, "é %s; deveria ter a forma 'Nome (dominio.com)', com o site entre parênteses, "
                          "em minúsculas. Reescreva." % _mostra(sugerido, 40))
        self.texto(bastidores, "limites", "bastidores", "bastidores")

    # ------------------------------------------------------------ histórico (regras H2 e H3)

    def _edicao_citada(self, data, campo):
        """A edição antiga que um campo cita, ou None (data torta, edição que não há ou que não é objeto)."""
        if not _e_data(data) or (self.data and data >= self.data):
            return None  # a regra R16 já acusou
        outra = self.historico.edicao(data)
        if outra is None and self.historico.completo:
            self.erro("H2", campo, "não há edição de %s em edicoes/. Confira a data no contexto.json, ou tire o "
                      "que aponta para ela." % data)
        return outra if isinstance(outra, dict) else None

    def historia(self):
        e, dados = self.e, self.dados
        registro, anulacoes = dados.registro_de_vetores()
        ja_anulados = set()
        erratas = e.get("errata")
        for indice, errata in enumerate(erratas if isinstance(erratas, list) else ()):
            if not isinstance(errata, dict):
                continue
            c = "errata[%d]" % indice
            outra = self._edicao_citada(errata.get("edicao"), c + ".edicao")
            item = errata.get("item")
            if outra is not None and isinstance(item, str) and _RE_ID_DE_ITEM.fullmatch(item) \
                    and item not in _ids_dos_itens(outra):
                self.erro("H2", c + ".item", "a edição de %s não tem o item %s. Corrija o id, ou tire o campo."
                          % (errata["edicao"], _mostra(item)))
            anula = errata.get("anula_vetor")
            if isinstance(anula, str):
                antes = [data for alvo, data in anulacoes if alvo == anula and data != self.data]
                if anula not in registro:
                    self.erro("H2", c + ".anula_vetor", "%s não é id de vetor em dados/vetores.json. Copie o id de "
                              "vetores_recentes, no contexto.json, ou tire o campo." % _mostra(anula))
                elif anula in ja_anulados:
                    self.erro("H2", c + ".anula_vetor", "%s já é anulado por outra errata desta edição. Tire o "
                              "campo de uma das duas." % _mostra(anula))
                elif antes:
                    self.erro("H2", c + ".anula_vetor", "%s já foi anulado em %s. Vetor só se anula uma vez: tire o "
                              "campo." % (_mostra(anula), antes[0] or "outra edição"))
                ja_anulados.add(anula)
        for item, c, _ in _itens(e):
            valor = item.get("continuacao_de")
            lido = _RE_CONTINUACAO.fullmatch(valor) if isinstance(valor, str) else None
            if lido:
                outra = self._edicao_citada(lido.group(1), c + ".continuacao_de")
                if outra is not None and lido.group(2) not in _ids_dos_itens(outra):
                    self.erro("H2", c + ".continuacao_de", "a edição de %s não tem o item %s. Corrija o id (veja "
                              "historias_recentes, no contexto.json), ou tire o campo."
                              % (lido.group(1), _mostra(lido.group(2))))
        respostas = e.get("respostas")
        for indice, resposta in enumerate(respostas if isinstance(respostas, list) else ()):
            if not isinstance(resposta, dict):
                continue
            c = "respostas[%d]" % indice
            outra = self._edicao_citada(resposta.get("edicao"), c + ".edicao")
            item = resposta.get("item")
            if outra is None or not isinstance(item, str) or not _RE_ID_DE_PRINCIPAL.fullmatch(item):
                continue
            principal = _por_id(outra.get("principais")).get(item)
            if principal is None:
                self.erro("H2", c + ".item", "a edição de %s não tem a principal %s. Corrija o id."
                          % (resposta["edicao"], _mostra(item)))
                continue
            perguntas = _textos_da_lista(principal.get("vigiar"))
            primeira = perguntas[0] if perguntas else ""
            if isinstance(resposta.get("pergunta"), str) and resposta["pergunta"].strip() != primeira.strip():
                self.erro("H2", c + ".pergunta", "não é igual à primeira pergunta de vigiar da principal %s de %s, "
                          "que é: %s. Copie a pergunta como está em vigiar_vencendo, no contexto.json."
                          % (item, resposta["edicao"], _mostra(primeira, 200)))
        if self.do_dia and self.data:
            self.repeticoes(registro, anulacoes)

    def repeticoes(self, registro, anulacoes):
        """Regra H3, que só avisa: título quase igual a um das 3 últimas edições; vetor repetido em 7 dias."""
        antigos = []
        for posicao, resumo in enumerate(self.historico.antes(self.data)):
            if posicao >= 3:
                break
            for item, _, _ in _itens(resumo.edicao):
                if isinstance(item.get("titulo"), str) and isinstance(item.get("id"), str):
                    antigos.append((_chave_do_titulo(item["titulo"]), "%s/%s" % (resumo.data, item["id"])))
        for item, c, _ in _itens(self.e):
            if "continuacao_de" in item or not isinstance(item.get("titulo"), str):
                continue
            chave = _chave_do_titulo(item["titulo"])
            for antiga, onde in antigos:
                if _quase_iguais(chave, antiga):
                    self.a.aviso("H3", c + ".titulo", "quase igual ao de %s. Se continua a história, use "
                                 "continuacao_de." % onde)
                    break
        anulados = set(alvo for alvo, _ in anulacoes)
        for player, para, c in self.vetores:
            for identificador, antigo in reversed(list(registro.items())):
                if (antigo.get("player") == player and antigo.get("para") == para and player and para
                        and identificador not in anulados and _e_data(antigo.get("data"))
                        and antigo["data"] != self.data
                        and 0 < comum.dias_entre(antigo["data"], self.data) <= 7):
                    self.a.aviso("H3", c, "vetor igual (player %s, destino %s) ao de %s, de %s. Só repita com ato "
                                 "novo." % (player, para, identificador, antigo["data"]))
                    break


def confere_edicao(edicao, dados, historico=None, do_dia=True, data_do_arquivo=None, tamanho=None, arquivo=""):
    """Confere uma edição COMPLETA (já com os campos calculados) contra as regras R e H do ESQUEMA, seção 10.

    edicao           o objeto JSON da edição (o que o completa() devolve, ou o que está em edicoes/)
    dados            Dados
    historico        Historico das outras edições; None quer dizer "sem histórico" (regra H1: aceita nível
                     mantido, não confere tendência, recusa alívio; as regras H2 e H3 não rodam)
    do_dia           True aplica também as regras (dia), que cruzam a edição com o mapa, o catálogo, os
                     limiares de preço e as listas `conflito` e `sites_oficiais` da régua
    data_do_arquivo  a data do nome do arquivo, quando ele está em edicoes/ (regra R01)
    tamanho          bytes do arquivo (regra R17); None mede o JSON que o publica.py gravaria
    arquivo          entra na frente do caminho de cada achado ("edicoes/2026-11-20.json:radar[2].fato")
    Devolve a lista de Achado, erros e avisos misturados, na ordem da edição. Nunca dá exceção."""
    achados = _Achados(arquivo)
    if tamanho is None:
        try:
            tamanho = len(comum.json_texto(edicao).encode("utf-8"))
        except (TypeError, ValueError, RecursionError):
            tamanho = None
    if tamanho is not None and tamanho > LIMITE_EDICAO:
        achados.erro("R17", "", "o arquivo tem %d bytes; o máximo é %d (60 KB). Corte itens do radar ou encurte "
                     "textos." % (tamanho, LIMITE_EDICAO))
    if not isinstance(edicao, dict):
        achados.erro("R00", "", "a edição deveria ser um objeto, e é %s. Publique com publica.py edicao."
                     % _nome_do_tipo(edicao))
        return achados.fecha()
    try:
        _Conferente(edicao, dados, historico, do_dia, data_do_arquivo, achados).roda()
    except RecursionError:
        achados.erro("ARQUIVO", "", "tem níveis demais, um dentro do outro, e não dá para conferir. Isso não é "
                     "edição do INFOCENARIUM: confira o que foi gravado.")
    return achados.fecha()


# ---------------------------------------------------------------- conferir: pasta de trabalho (regras T1 a T5)
#
# Só o publica.py edicao usa estas funções (CONTRATO, seção 3). Todas recebem o conteúdo dos arquivos já lido.

def _urls_do_agente(edicao):
    """[(url, caminho)] de todo campo de URL que o agente escreve. Os dos indicadores ficam de fora."""
    saida = []
    edicao = edicao if isinstance(edicao, dict) else {}
    for item, c, _ in _itens(edicao):
        fontes = item.get("fontes")
        for indice, fonte in enumerate(fontes if isinstance(fontes, list) else ()):
            if isinstance(fonte, dict) and "url" in fonte:
                saida.append((fonte["url"], "%s.fontes[%d].url" % (c, indice)))
        for ataque, ca in _ataques_do_item(item):
            if "url" in ataque:
                saida.append((ataque["url"], "%s.%s.url" % (c, ca)))
        vetores = item.get("vetores")
        for indice, vetor in enumerate(vetores if isinstance(vetores, list) else ()):
            if isinstance(vetor, dict) and "url" in vetor:
                saida.append((vetor["url"], "%s.vetores[%d].url" % (c, indice)))
    for chave in ("novos_players", "errata", "respostas"):
        lista = edicao.get(chave)
        for indice, objeto in enumerate(lista if isinstance(lista, list) else ()):
            if not isinstance(objeto, dict):
                continue
            if "url" in objeto:
                saida.append((objeto["url"], "%s[%d].url" % (chave, indice)))
            if chave == "novos_players" and isinstance(objeto.get("dna_fontes"), dict):
                for tema, url in objeto["dna_fontes"].items():
                    saida.append((url, "novos_players[%d].dna_fontes.%s" % (indice, _uma_linha(tema)[:40])))
    return saida


def _manchetes(coleta):
    """{endereço limpo: {"veiculos": conjunto, "data": dia UTC ou None}} das manchetes de coleta.json."""
    saida = {}
    for manchete in _lista_de_objetos(coleta.get("manchetes") if isinstance(coleta, dict) else None):
        limpo = _limpo(manchete.get("url"))
        if not limpo:
            continue
        publicado = manchete.get("publicado_em")
        dia = publicado[:10] if isinstance(publicado, str) and comum.data_valida(publicado[:10]) else None
        ficha = saida.setdefault(limpo, {"veiculos": set(), "data": dia})
        if isinstance(manchete.get("veiculo"), str):
            ficha["veiculos"].add(manchete["veiculo"])
        ficha["data"] = ficha["data"] or dia
    return saida


def _paginas(conferencia):
    """{endereço limpo: {"estado", "data"}} das páginas de conferencia.json."""
    saida = {}
    for pagina in _lista_de_objetos(conferencia.get("paginas") if isinstance(conferencia, dict) else None):
        limpo = _limpo(pagina.get("url"))
        if limpo and limpo not in saida:
            saida[limpo] = {"estado": pagina.get("estado") if pagina.get("estado") in ESTADOS_DE_PAGINA else None,
                            "data": pagina["publicado_em"] if _e_data(pagina.get("publicado_em")) else None}
    return saida


def _sem_rede(coleta, conferencia):
    """Regra T3, "máquina sem rede": nenhum feed respondeu e nenhuma página da conferência veio ok."""
    return calcula_feeds(coleta)[0] == 0 and not any(p["estado"] == "ok" for p in _paginas(conferencia).values())


def confere_t1(edicao, coleta=None, urls=None):
    """T1, URL vista: toda URL do rascunho está em coleta.json (manchetes) ou em urls.txt. Compara pelo endereço limpo."""
    achados = _Achados()
    vistas = set(_manchetes(coleta)) | set(_limpo(u) for u in le_urls(urls))
    for url, caminho in _urls_do_agente(edicao):
        if isinstance(url, str) and url and _limpo(url) not in vistas:
            achados.erro("T1", caminho, "%s não está na mesa (coleta.json) nem em urls.txt. Só vale URL vista "
                         "nesta execução: se você abriu a página, anote o endereço em urls.txt; senão, troque a "
                         "fonte." % _mostra(url, 80))
    return achados.fecha()


def confere_t2(edicao, dia):
    """T2: a `data` do rascunho é o dia da execução, e o rascunho não traz `exemplo` nem `estado: falha`."""
    achados = _Achados()
    edicao = edicao if isinstance(edicao, dict) else {}
    if "data" in edicao and edicao["data"] != dia:
        achados.erro("T2", "data", "é %s, e o dia desta execução é %s (o `dia` do contexto.json). Troque."
                     % (_mostra(edicao["data"], 30), dia))
    if "exemplo" in edicao:
        achados.erro("T2", "exemplo", "rascunho não traz o campo exemplo: ele é só da edição fictícia dos testes. "
                     "Tire o campo.")
    if edicao.get("estado") == "falha":
        achados.erro("T2", "estado", "rascunho não traz estado 'falha': use 'completa' ou 'reduzida'. Edição de "
                     "falha se publica com publica.py falha --motivo \"…\".")
    return achados.fecha()


def confere_t3(edicao, dados, coleta=None, conferencia=None, historico=None):
    """T3, data conferida pela máquina.

    A fonte tem data conferida quando a URL está em coleta.json (data do feed) ou em conferencia.json com
    estado ok e data. Aí `publicado_em` bate com ela, com 1 dia de folga. URL com estado erro não vale.
    Cada principal tem 2 fontes com data conferida dentro da janela da regra R09; item que sustenta gatilho
    tem 1, ou 3 se o gatilho é novo e de nível 3 ou mais (fonte primária não entra na conta). Com a máquina
    sem rede essas contas não valem: bastidores.modo tem de ser busca, e nenhum item sustenta gatilho de
    nível 3 ou mais. `historico` serve para saber se um gatilho de nível 4 ou 5 é estado que continua."""
    achados = _Achados()
    edicao = edicao if isinstance(edicao, dict) else {}
    data = edicao["data"] if _e_data(edicao.get("data")) else None
    manchetes, paginas = _manchetes(coleta), _paginas(conferencia)
    sem_rede = _sem_rede(coleta, conferencia)

    def conferida(url):
        limpo = _limpo(url)
        if limpo in manchetes and manchetes[limpo]["data"]:
            return manchetes[limpo]["data"], "o feed"
        pagina = paginas.get(limpo)
        if pagina and pagina["estado"] == "ok" and pagina["data"]:
            return pagina["data"], "a página"
        return None, None

    for url, caminho in _urls_do_agente(edicao):
        limpo = _limpo(url)
        if limpo and limpo not in manchetes and paginas.get(limpo, {}).get("estado") == "erro":
            achados.erro("T3", caminho, "a página não existe (a conferência deu estado 'erro'). URL assim não vale "
                         "como fonte: troque a fonte, ou corrija o endereço e rode coleta.py --confere.")
    na_janela = {}
    for item, c, principal in _itens(edicao):
        conta = 0
        fontes = item.get("fontes")
        for indice, fonte in enumerate(fontes if isinstance(fontes, list) else ()):
            if not isinstance(fonte, dict):
                continue
            dia, quem = conferida(fonte.get("url"))
            publicado = fonte.get("publicado_em")
            if dia and _e_data(publicado) and abs(comum.dias_entre(dia, publicado)) > 1:
                achados.erro("T3", "%s.fontes[%d].publicado_em" % (c, indice), "é %s, %s diz %s. Corrija a data; "
                             "se sair da janela, troque a fonte." % (publicado, quem, dia))
            if (dia and data and fonte.get("primaria") is not True
                    and comum.soma_dias(data, -2) <= dia <= comum.soma_dias(data, 1)):
                conta += 1
        if isinstance(item.get("id"), str):
            na_janela.setdefault(item["id"], conta)
        if principal and not sem_rede and conta < 2:
            achados.erro("T3", c + ".fontes", "tem %s com data conferida pela máquina dentro da janela (de 2 dias "
                         "antes a 1 depois da edição); a principal pede 2 ou mais, sem contar fonte primária. Use "
                         "fonte da mesa, ou anote as páginas em urls.txt e rode coleta.py --confere."
                         % _conta(conta, "fonte", "fontes"))
    if sem_rede:
        bastidores = edicao.get("bastidores")
        if isinstance(bastidores, dict) and bastidores.get("modo") != "busca":
            achados.erro("T3", "bastidores.modo", "é %s, e nesta execução nenhum feed respondeu e nenhuma página "
                         "foi conferida. Sem rede o modo é 'busca': troque." % _mostra(bastidores.get("modo"), 30))
    conta = _analisa_alerta(dados, edicao, historico, True)
    alerta = edicao.get("alerta") if isinstance(edicao.get("alerta"), dict) else {}
    escritos = alerta.get("dominios") if isinstance(alerta.get("dominios"), list) else []
    for indice, dominio in enumerate(escritos):
        identificador = dominio.get("id") if isinstance(dominio, dict) else None
        # id que não é texto (lista, objeto) não serve de chave: a R00 já o acusou na conferência da edição.
        calculo = conta["dominios"].get(identificador) if isinstance(identificador, str) else None
        if calculo is None or calculo["escrito"] is not dominio:
            continue
        for posicao, lido in enumerate(calculo["gatilhos"]):
            if not (lido["criterio_ok"] and lido["dominio_ok"] and lido["alvo"] == "item"):
                continue
            c = "alerta.dominios[%d].gatilhos[%d].ref" % (indice, posicao)
            if sem_rede:
                if lido["nivel"] >= 3:
                    achados.erro("T3", c, "sem rede não há como conferir data, e nesse caso nenhum item sustenta "
                                 "gatilho de nível 3 ou mais (este é de nível %d). Tire o gatilho e ponha o fato "
                                 "na leitura do domínio e em bastidores.limites: o alerta sobe quando a rede voltar."
                                 % lido["nivel"])
                continue
            pede = 3 if lido["nivel"] >= 3 and not lido["continua"] else 1
            tem = na_janela.get(lido["ref"], 0)
            if tem < pede:
                achados.erro("T3", c, "o item %s tem %s com data conferida pela máquina dentro da janela, e %s "
                             "pede %d (fonte primária não conta). Acrescente fonte da mesa ou página conferida "
                             "(urls.txt e coleta.py --confere), ou baixe o critério."
                             % (_mostra(lido["ref"]), _conta(tem, "fonte", "fontes"),
                                "gatilho novo de nível %d" % lido["nivel"] if pede == 3 else "item que sustenta gatilho",
                                pede))
    return achados.fecha()


def confere_t4(edicao, dados, coleta=None):
    """T4, veículo e endereço: em fonte de veículo do mapa, o site da URL bate com um dos `sites` do veículo.

    Estar em coleta.json com o veículo não basta: um feed comprometido, ou de agregador, pode pôr na mesa o
    endereço de outro site com o nome do veículo. `coleta` fica na assinatura e não é lida."""
    achados = _Achados()
    for item, c, _ in _itens(edicao if isinstance(edicao, dict) else {}):
        fontes = item.get("fontes")
        for indice, fonte in enumerate(fontes if isinstance(fontes, list) else ()):
            if not isinstance(fonte, dict):
                continue
            veiculo, url = fonte.get("veiculo"), fonte.get("url")
            ficha = dados.mapa.get(veiculo) if isinstance(veiculo, str) and veiculo != "outro" else None
            if ficha is None or not isinstance(url, str) or not url:
                continue
            if comum.url_bate(url, ficha["sites"]):
                continue
            donos = sorted(v for v, f in dados.mapa.items() if comum.url_bate(url, f["sites"]))
            achados.erro("T4", "%s.fontes[%d].veiculo" % (c, indice), "o site %s não é de %s (sites dele no mapa: "
                         "%s). O veiculo da fonte é o dono do site da URL: %s."
                         % (_mostra(comum.site_de(url)), _mostra(veiculo), _lista_em_texto(ficha["sites"]),
                            "use %s" % " ou ".join(_mostra(d) for d in donos[:3]) if donos
                            else "use 'outro', com nome"))
    return achados.fecha()


def confere_t5(edicao, urls=None):
    """T5: `omite` só em ataque cuja URL está em urls.txt (página aberta nesta execução)."""
    achados = _Achados()
    abertas = set(_limpo(u) for u in le_urls(urls))
    for item, c, _ in _itens(edicao if isinstance(edicao, dict) else {}):
        for ataque, ca in _ataques_do_item(item):
            if "omite" in ataque and isinstance(ataque.get("url"), str) and _limpo(ataque["url"]) not in abertas:
                achados.erro("T5", "%s.%s.omite" % (c, ca), "só vale para página aberta nesta execução, e a URL "
                             "do ataque não está em urls.txt. Tire o campo; ou abra a página, confira o que falta "
                             "nela e anote o endereço em urls.txt.")
    return achados.fecha()


def confere_trabalho(edicao, dados, dia, coleta=None, urls=None, conferencia=None, historico=None):
    """As regras T1 a T5 de uma vez (ESQUEMA, seção 10). É o que o publica.py edicao soma ao confere_edicao.

    edicao       o rascunho, ou a edição já completa: só os campos do agente são olhados
    dia          o dia da execução (--dia)
    coleta       o objeto de coleta.json, ou None se o arquivo não existe
    urls         o texto de urls.txt, ou a lista de linhas, ou None
    conferencia  o objeto de conferencia.json, ou None
    historico    Historico (diz se um gatilho de nível 4 ou 5 é estado que continua); None: todo gatilho é novo
    Devolve a lista de Achado, com o caminho relativo à edição."""
    try:
        return (confere_t1(edicao, coleta, urls) + confere_t2(edicao, dia)
                + confere_t3(edicao, dados, coleta, conferencia, historico)
                + confere_t4(edicao, dados, coleta) + confere_t5(edicao, urls))
    except RecursionError:
        return [Achado(ERRO, "ARQUIVO", "edicao", "tem níveis demais, um dentro do outro, e não dá para conferir. "
                       "Reescreva o rascunho na forma do modelo.txt.")]


# ---------------------------------------------------------------- conferir: os dados (modo --dados)

def _d_texto(a, campo, valor, maximo=None, regra="DADOS"):
    """Texto não vazio (e até `maximo` caracteres) num arquivo de dados."""
    if not isinstance(valor, str) or not valor.strip():
        a.erro(regra, campo, "deveria ser texto não vazio, e é %s. Corrija." % _mostra(valor, 30))
        return False
    if maximo is not None and len(valor) > maximo:
        a.erro(regra, campo, "tem %d caracteres, o máximo é %d. Encurte." % (len(valor), maximo))
        return False
    return True


def _d_objetos(a, campo, lista, textos=(), regra="DADOS", slug=True):
    """Uma lista de objetos com `id`: cada um é objeto, tem id de forma certa e sem repetir, e os textos pedidos.

    Devolve [(caminho, objeto)] dos que são objeto. Lista que não é lista devolve [] sem acusar: quem acusa a
    falta de uma lista essencial é o monta_dados."""
    saida, vistos = [], set()
    for indice, objeto in enumerate(lista if isinstance(lista, list) else ()):
        c = "%s[%d]" % (campo, indice)
        if not isinstance(objeto, dict):
            a.erro(regra, c, "deveria ser um objeto, e é %s. Corrija." % _nome_do_tipo(objeto))
            continue
        identificador = objeto.get("id")
        if not isinstance(identificador, str) or not (_RE_SLUG.fullmatch(identificador) if slug else identificador):
            a.erro(regra, c + ".id", "é %s; deveria ter de 2 a 31 letras minúsculas, algarismos ou sublinhado, "
                   "começando por letra. Corrija." % _mostra(identificador, 30))
        elif identificador in vistos:
            a.erro(regra, c + ".id", "%s está repetido: cada id aparece uma vez só. Tire ou renomeie um."
                   % _mostra(identificador))
        else:
            vistos.add(identificador)
        for chave in textos:
            _d_texto(a, _junta(c, chave), objeto.get(chave), regra=regra)
        saida.append((c, objeto))
    return saida


def _d_versao(a, objeto):
    if not _e_inteiro(objeto.get("versao")) or objeto["versao"] != 1:
        a.erro("DADOS", "versao", "é %s; deveria ser 1. Corrija." % _mostra(objeto.get("versao"), 30))


def _confere_regua(dados):
    regua, a = dados.bruto["regua"], _Achados("dados/regua.json")
    if not isinstance(regua, dict):
        return []
    _d_versao(a, regua)
    _d_objetos(a, "temas", regua.get("temas"), ("nome", "sigla", "azul", "vermelho"))
    for tema in TEMAS_ATUAIS:
        if isinstance(regua.get("temas"), list) and tema not in dados.temas:
            a.erro("DADOS", "temas", "falta o tema %s, que o esquema usa como tema atual. Recupere a régua do git."
                   % _mostra(tema))
    siglas = set()
    for c, partido in _d_objetos(a, "partidos", regua.get("partidos"), ("nome", "sigla", "descricao")):
        if isinstance(partido.get("sigla"), str):
            if partido["sigla"] in siglas:
                a.erro("DADOS", c + ".sigla", "%s está repetida: cada partido tem a sua sigla. Troque uma."
                       % _mostra(partido["sigla"]))
            siglas.add(partido["sigla"])
        votos = partido.get("voto_tipico")
        if not isinstance(votos, str):
            a.erro("DADOS", c + ".voto_tipico", "deveria ser texto com uma letra por tema, separadas por espaço "
                   "(ou vazio, em partido sem voto típico), e é %s. Corrija." % _mostra(votos, 30))
        elif votos.split() and (len(votos.split()) != len(dados.temas)
                                or any(letra not in dados.letras for letra in votos.split())):
            a.erro("DADOS", c + ".voto_tipico", "é %s; deveria ter %d letras, uma por tema, cada uma entre %s. "
                   "Corrija." % (_mostra(votos), len(dados.temas), _lista_em_texto(dados.letras)))
    if isinstance(regua.get("partidos"), list) and "independentes" not in dados.partidos:
        a.erro("DADOS", "partidos", "falta o partido 'independentes', que as regras R11 e R20 citam pelo id. "
               "Recupere a régua do git.")
    _d_objetos(a, "times", regua.get("times"), ("nome",))
    _d_objetos(a, "tipos", regua.get("tipos"), ("nome",))
    for tipo in TIPOS_DE_PLAYER_NOVO:
        if isinstance(regua.get("tipos"), list) and tipo not in dados.tipos:
            a.erro("DADOS", "tipos", "falta o tipo %s, que o esquema usa em player novo. Recupere a régua do git."
                   % _mostra(tipo))
    valores = regua.get("valores")
    if not isinstance(valores, dict) or any(letra not in valores for letra in ("B", "R", "Y", "W")):
        a.erro("DADOS", "valores", "deveria ser um objeto com as letras do DNA, e pelo menos B, R, Y e W. "
               "Recupere a régua do git.")
    polos = regua.get("polos")
    for polo in SENTIDOS:
        if not isinstance(polos, dict) or not isinstance(polos.get(polo), str) or not polos[polo].strip():
            a.erro("DADOS", "polos." + polo, "falta o texto do polo %s. Recupere a régua do git." % _mostra(polo))
    _d_objetos(a, "dominios", regua.get("dominios"), ("nome", "descricao", "canal"))
    if isinstance(regua.get("dominios"), list) and len(regua["dominios"]) != 5:
        a.erro("DADOS", "dominios", "tem %s; o esquema pede exatamente 5 domínios. Recupere a régua do git."
               % _conta(len(regua["dominios"]), "item", "itens"))
    _confere_niveis(dados, regua, a)
    em_campo = {}
    for c, campo in _d_objetos(a, "campos", regua.get("campos"), ("nome", "descricao")):
        partidos = campo.get("partidos")
        if not isinstance(partidos, list) or not partidos:
            a.erro("DADOS", c + ".partidos", "deveria ser lista de ids de partido, com 1 ou mais. Corrija.")
            continue
        for indice, partido in enumerate(partidos):
            if not isinstance(partido, str) or partido not in dados.partidos:
                a.erro("DADOS", "%s.partidos[%d]" % (c, indice), "%s não é partido da régua. Vale: %s."
                       % (_mostra(partido, 30), _lista_em_texto(dados.partidos)))
            elif partido in em_campo:
                a.erro("DADOS", "%s.partidos[%d]" % (c, indice), "%s já está no campo %s: um partido fica num "
                       "campo só. Tire de um." % (_mostra(partido), _mostra(em_campo[partido])))
            else:
                em_campo[partido] = campo.get("id")
    if isinstance(regua.get("campos"), list) and len(regua["campos"]) != 2:
        a.erro("DADOS", "campos", "tem %s; a regra R08 conta com exatamente 2 campos (ordem e contestação). "
               "Recupere a régua do git." % _conta(len(regua["campos"]), "item", "itens"))
    forcas = regua.get("forcas")
    if isinstance(forcas, list):
        if [f.get("forca") if isinstance(f, dict) else None for f in forcas] != [1, 2, 3]:
            a.erro("DADOS", "forcas", "deveriam ser as forças 1, 2 e 3, nesta ordem (campo forca de cada item). "
                   "Recupere a régua do git.")
        for indice, forca in enumerate(forcas):
            if isinstance(forca, dict):
                for chave in ("nome", "o_que_conta"):
                    _d_texto(a, "forcas[%d].%s" % (indice, chave), forca.get(chave))
    _d_objetos(a, "evidencias", regua.get("evidencias"), ("o_que_conta",))
    if isinstance(regua.get("evidencias"), list) and "narrativa" not in dados.evidencias:
        a.erro("DADOS", "evidencias", "falta a evidência 'narrativa', que as regras R10 e R12 citam pelo id. "
               "Recupere a régua do git.")
    avanco = regua.get("times_avanco")
    if not isinstance(avanco, dict):
        a.erro("DADOS", "times_avanco", "deveria ser um objeto com um texto por time. Recupere a régua do git.")
    else:
        for time in dados.times:
            _d_texto(a, "times_avanco." + time, avanco.get(time))
        for chave in avanco:
            if chave not in dados.times and chave != "nao_move":
                a.erro("DADOS", "times_avanco", "a chave %s não é time da régua (vale: %s, e nao_move). Tire ou "
                       "corrija." % (_mostra(chave, 30), _lista_em_texto(dados.times)))
    conflito = regua.get("conflito")
    if isinstance(conflito, dict):
        _d_texto(a, "conflito.regra", conflito.get("regra"))
        players = conflito.get("players")
        if not isinstance(players, list):
            a.erro("DADOS", "conflito.players", "deveria ser lista de ids de player. Corrija.")
        elif isinstance(dados.bruto["players"], dict):
            for indice, player in enumerate(players):
                if not isinstance(player, str) or player not in dados.players:
                    a.erro("DADOS", "conflito.players[%d]" % indice, "%s não existe em players.json. Corrija o id, "
                           "ou tire da lista.%s" % (_mostra(player, 30), _sugere(player, dados.players)))
        termos = conflito.get("termos")
        if not isinstance(termos, list) or any(not isinstance(t, str) or not t.strip() or t != t.strip()
                                               for t in termos):
            a.erro("DADOS", "conflito.termos", "deveria ser lista de textos não vazios, sem espaço nas pontas. "
                   "Corrija.")
    oficiais = regua.get("sites_oficiais")
    if isinstance(oficiais, dict):
        _d_texto(a, "sites_oficiais.regra", oficiais.get("regra"))
        for chave in ("brasil", "outros"):
            sufixos = oficiais.get(chave)
            if not isinstance(sufixos, list):
                a.erro("DADOS", "sites_oficiais." + chave, "deveria ser lista de sufixos de site. Corrija.")
                continue
            for indice, sufixo in enumerate(sufixos):
                if (not isinstance(sufixo, str) or not re.fullmatch(r"[a-z0-9-]+(?:\.[a-z0-9-]+)*", sufixo)
                        or sufixo.startswith("www.")):
                    a.erro("DADOS", "sites_oficiais.%s[%d]" % (chave, indice), "é %s; deveria ser sufixo de site "
                           "em minúsculas, sem www., sem barra e sem esquema (ex.: 'gov.br'). Corrija."
                           % _mostra(sufixo, 30))
    return a.fecha()


def _confere_niveis(dados, regua, a):
    """`niveis_alerta`: 5 níveis, de 1 a 5, cada um com a célula de cada domínio e o código dominio.nivel."""
    niveis = regua.get("niveis_alerta")
    if not isinstance(niveis, list):
        return
    if len(niveis) != 5:
        a.erro("DADOS", "niveis_alerta", "tem %s; o esquema pede exatamente 5 níveis. Recupere a régua do git."
               % _conta(len(niveis), "item", "itens"))
    for indice, linha in enumerate(niveis):
        c = "niveis_alerta[%d]" % indice
        if not isinstance(linha, dict):
            a.erro("DADOS", c, "deveria ser um objeto, e é %s. Corrija." % _nome_do_tipo(linha))
            continue
        nivel = indice + 1
        if not _e_inteiro(linha.get("nivel")) or linha["nivel"] != nivel:
            a.erro("DADOS", c + ".nivel", "é %s; deveria ser %d: os níveis vão de 1 a 5, em ordem. Corrija."
                   % (_mostra(linha.get("nivel"), 30), nivel))
        for chave in ("rotulo", "significado", "prova_minima"):
            _d_texto(a, _junta(c, chave), linha.get(chave))
        criterios = linha.get("criterios")
        if not isinstance(criterios, dict):
            a.erro("DADOS", c + ".criterios", "deveria ser um objeto com uma célula por domínio. Corrija.")
            continue
        faltam = [d for d in dados.dominios if d not in criterios]
        sobram = [d for d in criterios if d not in dados.dominios]
        if faltam or sobram:
            a.erro("DADOS", c + ".criterios", "deveria ter exatamente os domínios da régua. Faltam: %s. Sobram: "
                   "%s. Corrija." % (_lista_em_texto(faltam), _lista_em_texto(sobram)))
        for dominio in dados.dominios:
            celula, cc = criterios.get(dominio), "%s.criterios.%s" % (c, dominio)
            if dominio not in criterios:
                continue
            if not isinstance(celula, dict):
                a.erro("DADOS", cc, "deveria ser um objeto com codigo, precos e eventos. Corrija.")
                continue
            certo = "%s.%d" % (dominio, nivel)
            if celula.get("codigo") != certo:
                a.erro("DADOS", cc + ".codigo", "é %s; deveria ser %s (dominio.nivel). Corrija."
                       % (_mostra(celula.get("codigo"), 30), _mostra(certo)))
            eventos = celula.get("eventos")
            if not isinstance(eventos, list) or any(not isinstance(t, str) or not t.strip() for t in eventos):
                a.erro("DADOS", cc + ".eventos", "deveria ser lista de textos não vazios. Corrija.")
            precos = celula.get("precos")
            if not isinstance(precos, list):
                a.erro("DADOS", cc + ".precos", "deveria ser uma lista (vazia se o nível não tem critério de "
                       "preço). Corrija.")
                continue
            if nivel == 1 and precos:
                a.erro("DADOS", cc + ".precos", "o nível 1 não tem critério de preço: gatilho só existe do nível 2 "
                       "ao 5. Esvazie a lista.")
            for posicao, preco in enumerate(precos):
                cp = "%s.precos[%d]" % (cc, posicao)
                if not isinstance(preco, dict):
                    a.erro("DADOS", cp, "deveria ser um objeto, e é %s. Corrija." % _nome_do_tipo(preco))
                    continue
                if not isinstance(preco.get("indicador"), str) or not _RE_SLUG.fullmatch(preco["indicador"]):
                    a.erro("DADOS", cp + ".indicador", "é %s; deveria ser o id de um indicador do catálogo. Corrija."
                           % _mostra(preco.get("indicador"), 30))
                if preco.get("janela") not in JANELAS:
                    a.erro("DADOS", cp + ".janela", "é %s; vale um destes: %s. Corrija."
                           % (_mostra(preco.get("janela"), 30), _lista_em_texto(JANELAS)))
                if not _e_numero(preco.get("alta_minima_pct")) or preco["alta_minima_pct"] <= 0:
                    a.erro("DADOS", cp + ".alta_minima_pct", "é %s; deveria ser número maior que zero: só alta "
                           "conta. Corrija." % _mostra(preco.get("alta_minima_pct"), 30))
                _d_texto(a, cp + ".texto", preco.get("texto"))


def _confere_players(dados):
    arquivo, a = dados.bruto["players"], _Achados("dados/players.json")
    if not isinstance(arquivo, dict):
        return []
    _d_versao(a, arquivo)
    if not _e_data(arquivo.get("atualizado_em")):
        a.erro("DADOS", "atualizado_em", "é %s; deveria ser uma data AAAA-MM-DD. Corrija."
               % _mostra(arquivo.get("atualizado_em"), 30))
    _d_texto(a, "regra", arquivo.get("regra"))
    for c, player in _d_objetos(a, "players", arquivo.get("players"), ("nome", "nota")):
        identificador = player.get("id")
        if isinstance(identificador, str) and (identificador in dados.partidos or identificador in ALVOS_ESPECIAIS):
            a.erro("DADOS", c + ".id", "%s é id de partido ou palavra reservada ('outro', 'nenhum'): como alvo de "
                   "ataque, ficaria ambíguo. Renomeie o player." % _mostra(identificador))
        for chave, valores in (("tipo", dados.tipos), ("partido", dados.partidos), ("time", dados.times),
                               ("origem", ORIGENS_DE_PLAYER)):
            if not isinstance(player.get(chave), str) or player[chave] not in valores:
                a.erro("DADOS", _junta(c, chave), "é %s; vale um destes: %s. Corrija.%s"
                       % (_mostra(player.get(chave), 30), _lista_em_texto(valores), _sugere(player.get(chave), valores)))
        if not isinstance(player.get("time_discutivel"), bool):
            a.erro("DADOS", c + ".time_discutivel", "deveria ser true ou false, e é %s. Corrija."
                   % _mostra(player.get("time_discutivel"), 30))
        if not _e_data(player.get("incluido_em")):
            a.erro("DADOS", c + ".incluido_em", "é %s; deveria ser uma data AAAA-MM-DD. Corrija."
                   % _mostra(player.get("incluido_em"), 30))
        dna = player.get("dna")
        if not isinstance(dna, dict):
            a.erro("DADOS", c + ".dna", "deveria ser um objeto com uma posição por tema. Corrija.")
        else:
            faltam = [t for t in dados.temas if t not in dna]
            sobram = [t for t in dna if t not in dados.temas]
            if faltam or sobram:
                a.erro("DADOS", c + ".dna", "deveria ter exatamente os temas da régua. Faltam: %s. Sobram: %s. "
                       "Corrija." % (_lista_em_texto(faltam), _lista_em_texto(sobram)))
            for tema in dados.temas:
                posicao = dna.get(tema)
                if tema in dna and not (isinstance(posicao, str) and 1 <= len(posicao) <= 2
                                        and all(letra in dados.letras for letra in posicao)):
                    a.erro("DADOS", "%s.dna.%s" % (c, tema), "é %s; deveria ser uma letra, ou duas em caso de "
                           "virada, entre %s. Corrija." % (_mostra(posicao, 30), _lista_em_texto(dados.letras)))
        duvidas = player.get("duvidas")
        if not isinstance(duvidas, list) or any(not isinstance(t, str) or t not in dados.temas for t in duvidas):
            a.erro("DADOS", c + ".duvidas", "deveria ser lista de ids de tema da régua (pode ser vazia), e é %s. "
                   "Corrija." % _mostra(duvidas, 30))
        if "url" in player and not comum.url_valida(player["url"]):
            a.erro("DADOS", c + ".url", "URL inválida (%s). Corrija." % _mostra(player["url"], 50))
        if "justificativa" in player:
            _d_texto(a, c + ".justificativa", player["justificativa"])
        if "dna_fontes" in player:
            fontes = player["dna_fontes"]
            if not isinstance(fontes, dict) or any(t not in dados.temas or not comum.url_valida(u)
                                                   for t, u in fontes.items()):
                a.erro("DADOS", c + ".dna_fontes", "deveria ser um objeto de tema da régua para URL válida. Corrija.")
    return a.fecha()


def _confere_mapa(dados):
    """O mapa de veículos: regras M1 e M2 (ESQUEMA, seção 15) e os outros campos que as regras da edição usam."""
    arquivo, a = dados.bruto["veiculos"], _Achados("dados/veiculos.json")
    if not isinstance(arquivo, dict):
        return []
    _d_versao(a, arquivo)
    if "revisado_em" not in arquivo:
        a.erro("M1", "revisado_em", "falta o campo. Enquanto o dono não revisa o mapa, ele fica null; depois, "
               "leva a data da revisão. Acrescente \"revisado_em\": null.")
    elif arquivo["revisado_em"] is not None and not _e_data(arquivo["revisado_em"]):
        a.erro("M1", "revisado_em", "é %s; deveria ser null (mapa em rascunho) ou a data AAAA-MM-DD em que o dono "
               "terminou de revisar os lados. Corrija." % _mostra(arquivo["revisado_em"], 30))
    conhecidos = set(dados.players) | set(dados.partidos)
    for c, veiculo in _d_objetos(a, "veiculos", arquivo.get("veiculos"), ("nome",)):
        if veiculo.get("id") == "outro":
            a.erro("DADOS", c + ".id", "'outro' é palavra reservada: quer dizer veículo fora do mapa. Renomeie.")
        for chave, valores in (("tipo", TIPOS_DE_VEICULO), ("lado", dados.partidos),
                               ("lado_confianca", CONFIANCAS), ("fatos", CONFIANCAS)):
            if not isinstance(veiculo.get(chave), str) or veiculo[chave] not in valores:
                a.erro("DADOS", _junta(c, chave), "é %s; vale um destes: %s. Corrija.%s"
                       % (_mostra(veiculo.get(chave), 30), _lista_em_texto(valores), _sugere(veiculo.get(chave), valores)))
        for chave in ("serve_a", "alvos"):
            lista = veiculo.get(chave)
            if not isinstance(lista, list):
                a.erro("DADOS", _junta(c, chave), "deveria ser lista de ids de player ou de partido (pode ser "
                       "vazia), e é %s. Corrija." % _mostra(lista, 30))
                continue
            for indice, alvo in enumerate(lista):
                if not isinstance(alvo, str) or alvo not in conhecidos:
                    a.erro("DADOS", "%s.%s[%d]" % (c, chave, indice), "%s não é player nem partido. Corrija o id, "
                           "ou tire da lista.%s" % (_mostra(alvo, 30), _sugere(alvo, conhecidos)))
        sites = veiculo.get("sites")
        if not isinstance(sites, list) or not 1 <= len(sites) <= 6:
            a.erro("M2", c + ".sites", "deveria ser lista de 1 a 6 nomes de site do veículo (ex.: [\"reuters.com\"]), "
                   "e é %s. É o que liga o veículo ao endereço da fonte: corrija." % _mostra(sites, 30))
        else:
            for indice, site in enumerate(sites):
                if (not isinstance(site, str) or not _RE_SITE.fullmatch(site) or site.startswith("www.")
                        or site in sites[:indice]):
                    a.erro("M2", "%s.sites[%d]" % (c, indice), "é %s; deveria ser o nome de um site, em minúsculas, "
                           "sem www., sem porta, sem barra e sem repetir (ex.: 'reuters.com'). Corrija."
                           % _mostra(site, 40))
        feeds = veiculo.get("feeds")
        if not isinstance(feeds, list):
            a.erro("DADOS", c + ".feeds", "deveria ser uma lista (vazia se o veículo não tem feed). Corrija.")
        else:
            for indice, feed in enumerate(feeds):
                if not isinstance(feed, dict) or not comum.url_valida(feed.get("url")):
                    a.erro("DADOS", "%s.feeds[%d].url" % (c, indice), "URL inválida (%s). Corrija o endereço do feed."
                           % _mostra(feed.get("url") if isinstance(feed, dict) else feed, 50))
        if "controle_fonte" in veiculo and not comum.url_valida(veiculo["controle_fonte"]):
            a.erro("DADOS", c + ".controle_fonte", "URL inválida (%s). Corrija." % _mostra(veiculo["controle_fonte"], 50))
    return a.fecha()


def _confere_vetores(dados):
    """dados/vetores.json: vetores e anulações bem formados (ESQUEMA, seção 12)."""
    arquivo, a = dados.bruto["vetores"], _Achados("dados/vetores.json")
    if not isinstance(arquivo, dict):
        return []
    _d_versao(a, arquivo)
    _d_texto(a, "regra", arquivo.get("regra"))
    tem_players = isinstance(dados.bruto["players"], dict)
    vetores, anulados = {}, {}
    lista = arquivo.get("vetores")
    for indice, entrada in enumerate(lista if isinstance(lista, list) else ()):
        c = "vetores[%d]" % indice
        if not isinstance(entrada, dict):
            a.erro("DADOS", c, "deveria ser um objeto, e é %s. Corrija." % _nome_do_tipo(entrada))
            continue
        identificador, data = entrada.get("id"), entrada.get("data")
        if not _e_data(data):
            a.erro("DADOS", c + ".data", "é %s; deveria ser a data AAAA-MM-DD da edição de origem. Corrija."
                   % _mostra(data, 30))
        if not isinstance(identificador, str) or not identificador:
            a.erro("DADOS", c + ".id", "é %s; deveria ser texto. Corrija." % _mostra(identificador, 30))
        elif identificador in vetores or identificador in anulados.values():
            a.erro("DADOS", c + ".id", "%s está repetido: cada entrada tem o seu id. Tire a entrada repetida (a mais "
                   "nova)." % _mostra(identificador))
        if not comum.url_valida(entrada.get("url")):
            a.erro("DADOS", c + ".url", "URL inválida (%s). Corrija." % _mostra(entrada.get("url"), 50))
        _d_texto(a, c + ".porque", entrada.get("porque"), 300)
        if "anula" in entrada:
            lido = _RE_ID_DE_ANULACAO.fullmatch(identificador) if isinstance(identificador, str) else None
            if not lido or lido.group(1) != data:
                a.erro("DADOS", c + ".id", "é %s; em entrada de anulação deveria ser a data, '_anula_' e um número "
                       "(ex.: '2026-11-21_anula_1'). Corrija." % _mostra(identificador, 40))
            alvo = entrada["anula"]
            if not isinstance(alvo, str) or alvo not in vetores:
                a.erro("DADOS", c + ".anula", "%s não é id de vetor que venha antes nesta lista. Anulação aponta "
                       "para vetor já registrado: corrija." % _mostra(alvo, 40))
            elif alvo in anulados:
                a.erro("DADOS", c + ".anula", "%s já foi anulado pela entrada %s. Vetor só se anula uma vez: tire "
                       "esta entrada." % (_mostra(alvo), _mostra(anulados[alvo])))
            else:
                anulados[alvo] = identificador
            continue
        item, player = entrada.get("item"), entrada.get("player")
        if not isinstance(item, str) or not _RE_ID_DE_ITEM.fullmatch(item):
            a.erro("DADOS", c + ".item", "é %s; deveria ser o id do item de origem (p1 a p3, r1 a r12). Corrija."
                   % _mostra(item, 30))
        if not isinstance(player, str) or (tem_players and player not in dados.players):
            a.erro("DADOS", c + ".player", "%s não existe em players.json. Corrija." % _mostra(player, 30))
        elif tem_players and entrada.get("de") != dados.partido_do_player(player):
            a.erro("DADOS", c + ".de", "é %s; deveria ser o partido do player em players.json, %s. Corrija."
                   % (_mostra(entrada.get("de"), 30), _mostra(dados.partido_do_player(player))))
        if not isinstance(entrada.get("para"), str) or entrada["para"] not in dados.partidos:
            a.erro("DADOS", c + ".para", "%s não é partido da régua. Corrija." % _mostra(entrada.get("para"), 30))
        if not _e_inteiro(entrada.get("forca")) or not 1 <= entrada["forca"] <= 3:
            a.erro("DADOS", c + ".forca", "é %s; vale 1, 2 ou 3. Corrija." % _mostra(entrada.get("forca"), 30))
        if entrada.get("tema") != "ordem" and entrada.get("tema") not in dados.temas:
            a.erro("DADOS", c + ".tema", "é %s; vale um tema da régua, ou 'ordem'. Corrija."
                   % _mostra(entrada.get("tema"), 30))
        if "conflito_de_interesse" in entrada and entrada["conflito_de_interesse"] is not True:
            a.erro("DADOS", c + ".conflito_de_interesse", "é %s; o campo só existe quando é true. Tire o campo."
                   % _mostra(entrada["conflito_de_interesse"], 30))
        if isinstance(identificador, str) and isinstance(item, str) and isinstance(player, str) and _e_data(data):
            certo = "%s_%s_%s" % (data, item, player)
            if identificador != certo:
                a.erro("DADOS", c + ".id", "é %s; deveria ser %s (data, item e player). Corrija."
                       % (_mostra(identificador, 50), _mostra(certo, 50)))
        if isinstance(identificador, str):
            vetores.setdefault(identificador, indice)
    return a.fecha()


def _confere_contratos(a, campo, contratos):
    """A regra C6 (ESQUEMA, seção 14): {"modelo": URL com exatamente uma marca {c}, "meses": de 1 a 12 letras de
    FGHJKMNQUVXZ, sem repetir, na ordem do ano}."""
    if not isinstance(contratos, dict) or sorted(contratos) != ["meses", "modelo"]:
        a.erro("C6", campo, "é %s; deveria ser {\"modelo\": URL com {c}, \"meses\": letras dos meses}, sem outra "
               "chave. Corrija, ou tire o campo." % _mostra(contratos, 60))
        return
    modelo, meses = contratos["modelo"], contratos["meses"]
    if not isinstance(modelo, str) or modelo.count("{c}") != 1 or not comum.url_valida(modelo.replace("{c}", "H27")):
        a.erro("C6", campo + ".modelo", "é %s; deveria ser um endereço (ESQUEMA, seção 0) com exatamente uma marca "
               "{c}, no lugar do código do contrato (H27). Corrija." % _mostra(modelo, 60))
    letras = list(meses) if isinstance(meses, str) else None
    if (letras is None or not 1 <= len(letras) <= 12 or any(m not in LETRAS_DOS_MESES for m in letras)
            or [LETRAS_DOS_MESES.index(m) for m in letras] != sorted(set(LETRAS_DOS_MESES.index(m) for m in letras))):
        a.erro("C6", campo + ".meses", "é %s; deveria ter de 1 a 12 letras de %s (janeiro a dezembro), sem repetir, "
               "na ordem do ano. Corrija." % (_mostra(meses, 30), LETRAS_DOS_MESES))


def _confere_catalogo(dados):
    """dados/indicadores.json: regras C1, C2, C5 e C6 (ESQUEMA, seção 14) e a forma de cada indicador."""
    arquivo, a = dados.bruto["indicadores"], _Achados("dados/indicadores.json")
    if not isinstance(arquivo, dict):
        return []
    _d_versao(a, arquivo)
    if not _e_data(arquivo.get("atualizado_em")):
        a.erro("DADOS", "atualizado_em", "é %s; deveria ser uma data AAAA-MM-DD. Corrija."
               % _mostra(arquivo.get("atualizado_em"), 30))
    lista = arquivo.get("indicadores")
    if isinstance(lista, list) and not 1 <= len(lista) <= 20:
        a.erro("C1", "indicadores", "tem %s; o catálogo pede de 1 a 20 indicadores. Acerte a lista."
               % _conta(len(lista), "item", "itens"))
    for c, indicador in _d_objetos(a, "indicadores", lista, regra="C1"):
        identificador = indicador.get("id")
        if isinstance(identificador, str) and _RE_ID_DE_ITEM.fullmatch(identificador):
            a.erro("C1", c + ".id", "%s tem a forma de id de item da edição (p1, r4): no ref de um gatilho, ficaria "
                   "ambíguo. Renomeie o indicador." % _mostra(identificador))
        _d_texto(a, c + ".nome", indicador.get("nome"), 60)
        _d_texto(a, c + ".unidade", indicador.get("unidade"), 30)
        for chave, valores in (("dominio", dados.dominios), ("frequencia", FREQUENCIAS)):
            if not isinstance(indicador.get(chave), str) or indicador[chave] not in valores:
                a.erro("DADOS", _junta(c, chave), "é %s; vale um destes: %s. Corrija."
                       % (_mostra(indicador.get(chave), 30), _lista_em_texto(valores)))
        if not isinstance(indicador.get("obrigatorio"), bool):
            a.erro("DADOS", c + ".obrigatorio", "deveria ser true ou false, e é %s. Corrija."
                   % _mostra(indicador.get("obrigatorio"), 30))
        faixa = indicador.get("faixa")
        if not (isinstance(faixa, dict) and _e_numero(faixa.get("min")) and _e_numero(faixa.get("max"))
                and 0 <= faixa["min"] < faixa["max"]):
            a.erro("DADOS", c + ".faixa", "é %s; deveria ser {\"min\": número, \"max\": número}, com 0 <= min < max. "
                   "Corrija." % _mostra(faixa, 40))
        if "casas" in indicador and not (_e_inteiro(indicador["casas"]) and 0 <= indicador["casas"] <= 6):
            a.erro("DADOS", c + ".casas", "é %s; vale um inteiro de 0 a 6. Corrija." % _mostra(indicador["casas"], 30))
        fontes = indicador.get("fontes")
        if not isinstance(fontes, list) or not 1 <= len(fontes) <= 5:
            a.erro("DADOS", c + ".fontes", "deveria ser lista de 1 a 5 fontes, na ordem de tentativa, e é %s. "
                   "Corrija." % _mostra(fontes, 30))
            continue
        for indice, fonte in enumerate(fontes):
            cf = "%s.fontes[%d]" % (c, indice)
            if not isinstance(fonte, dict):
                a.erro("DADOS", cf, "deveria ser um objeto, e é %s. Corrija." % _nome_do_tipo(fonte))
                continue
            _d_texto(a, cf + ".nome", fonte.get("nome"), 60)
            if not comum.url_valida(fonte.get("url")):
                a.erro("DADOS", cf + ".url", "URL inválida (%s). Corrija o endereço da fonte."
                       % _mostra(fonte.get("url"), 50))
            if fonte.get("leitor") not in LEITORES:
                a.erro("DADOS", cf + ".leitor", "é %s; vale um destes: %s. Leitor novo pede mudança no "
                       "indicadores.py." % (_mostra(fonte.get("leitor"), 30), _lista_em_texto(LEITORES)))
            if "fator" in fonte and not (_e_numero(fonte["fator"]) and fonte["fator"] > 0):
                a.erro("DADOS", cf + ".fator", "é %s; deveria ser número maior que zero. Corrija."
                       % _mostra(fonte["fator"], 30))
            if "nota" in fonte:
                _d_texto(a, cf + ".nota", fonte["nota"], 200)
            if "contratos" in fonte:
                _confere_contratos(a, cf + ".contratos", fonte["contratos"])
        if indicador.get("obrigatorio") is True and len(fontes) < 2:
            a.aviso("C5", c + ".fontes", "indicador obrigatório com 1 fonte só: sem segunda fonte não há como "
                    "confirmar alta forte, e o gatilho de preço de %s nunca passa do nível 2. Acrescente uma "
                    "segunda fonte diária." % _mostra(identificador, 30))
    if isinstance(lista, list) and isinstance(dados.bruto["regua"], dict):
        citados = []
        for dominio in dados.dominios:
            for _, indicador, _, _ in dados.precos.get(dominio, ()):
                if indicador not in citados:
                    citados.append(indicador)
        for indicador in citados:
            ficha = dados.indicador.get(indicador)
            if ficha is None:
                a.erro("C2", "indicadores", "falta o indicador %s, que os critérios de preço da régua citam. "
                       "Acrescente-o ao catálogo, ou tire o critério da régua." % _mostra(indicador))
            elif ficha.get("obrigatorio") is not True or ficha.get("frequencia") != "diaria":
                a.erro("C2", "indicadores[%d]" % dados.catalogo.index(indicador), "%s é citado nos critérios de "
                       "preço da régua, e por isso tem de ser obrigatorio: true e frequencia: 'diaria'. Corrija."
                       % _mostra(indicador))
    return a.fecha()


def confere_dados(dados, indice=None, existe=None):
    """O modo --dados: estrutura e referências de régua, players, mapa (M1, M2), vetores e catálogo (C1, C2,
    C5 como aviso, C6). Com `indice` (o objeto de edicoes/indice.json), também a forma dele.

    Não repete o que o carrega_dados já acusou (arquivo ilegível, lista essencial que falta).
    `existe(caminho)` responde se um arquivo citado no índice existe; None deixa de conferir isso."""
    try:
        achados = (_confere_regua(dados) + _confere_players(dados) + _confere_mapa(dados)
                   + _confere_vetores(dados) + _confere_catalogo(dados))
        if indice is not None:
            achados += confere_indice(indice, None, existe)
    except RecursionError:
        achados = [Achado(ERRO, "ARQUIVO", "dados", "há arquivo com níveis demais, um dentro do outro. Recupere "
                          "os dados do git.")]
    return achados


# ---------------------------------------------------------------- conferir: índice e feed

_CONSERTO_DO_INDICE = "O índice é gerado: rode publica.py refaz."


def confere_indice(indice, edicoes=None, existe=None):
    """edicoes/indice.json (ESQUEMA, seção 11): a forma e, com `edicoes` ({data: edição}), se está igual aos
    arquivos de edição. `existe(caminho)` diz se `arquivo` e `texto` de cada entrada existem."""
    a = _Achados("edicoes/indice.json")
    if not isinstance(indice, dict):
        a.erro("INDICE", "", "deveria ser um objeto, e é %s. %s" % (_nome_do_tipo(indice), _CONSERTO_DO_INDICE))
        return a.fecha()
    if not _e_inteiro(indice.get("versao")) or indice["versao"] != 1:
        a.erro("INDICE", "versao", "é %s; deveria ser 1. %s" % (_mostra(indice.get("versao"), 30), _CONSERTO_DO_INDICE))
    for chave in indice:
        if chave not in ("versao", "atualizado_em", "edicoes"):
            a.erro("INDICE", "", "campo desconhecido %s na raiz do índice. %s" % (_mostra(chave, 30), _CONSERTO_DO_INDICE))
    lista = indice.get("edicoes")
    if not isinstance(lista, list):
        a.erro("INDICE", "edicoes", "deveria ser uma lista, e é %s. %s" % (_nome_do_tipo(lista), _CONSERTO_DO_INDICE))
        return a.fecha()
    datas, geradas = [], []
    for posicao, entrada in enumerate(lista):
        c = "edicoes[%d]" % posicao
        if not isinstance(entrada, dict):
            a.erro("INDICE", c, "deveria ser um objeto, e é %s. %s" % (_nome_do_tipo(entrada), _CONSERTO_DO_INDICE))
            continue
        data = entrada.get("data")
        if not _e_data(data):
            a.erro("INDICE", c + ".data", "é %s; deveria ser uma data AAAA-MM-DD. %s"
                   % (_mostra(data, 30), _CONSERTO_DO_INDICE))
            continue
        if data in datas:
            a.erro("INDICE", c + ".data", "%s está repetida: vale uma entrada por edição. %s" % (data, _CONSERTO_DO_INDICE))
        elif datas and data > datas[-1]:
            a.erro("INDICE", c + ".data", "%s vem depois de %s: a lista vai da edição mais nova para a mais velha. %s"
                   % (data, datas[-1], _CONSERTO_DO_INDICE))
        datas.append(data)
        for chave, certo in (("arquivo", "edicoes/%s.json" % data), ("texto", "edicoes/%s.md" % data)):
            if entrada.get(chave) != certo:
                a.erro("INDICE", _junta(c, chave), "é %s; deveria ser %s. %s"
                       % (_mostra(entrada.get(chave), 40), _mostra(certo), _CONSERTO_DO_INDICE))
            elif existe is not None and not existe(certo):
                a.erro("INDICE", _junta(c, chave), "o arquivo %s não existe. %s" % (certo, _CONSERTO_DO_INDICE))
        formas = (("estado", entrada.get("estado") in ESTADOS),
                  ("nivel", _e_inteiro(entrada.get("nivel")) and 1 <= entrada["nivel"] <= 5),
                  ("tendencia", entrada.get("tendencia") in TENDENCIAS),
                  ("niveis", isinstance(entrada.get("niveis"), dict)),
                  ("saldos", isinstance(entrada.get("saldos"), dict)),
                  ("eixos", isinstance(entrada.get("eixos"), dict)),
                  ("indicadores", isinstance(entrada.get("indicadores"), dict)),
                  ("resumo", isinstance(entrada.get("resumo"), str)),
                  ("gerada_em", comum.data_hora_valida(entrada.get("gerada_em"))),
                  ("exemplo", isinstance(entrada.get("exemplo"), bool)),
                  ("corrigida_em", isinstance(entrada.get("corrigida_em"), list)
                   and all(_e_data(d) for d in entrada["corrigida_em"])))
        for chave, serve in formas:
            if not serve:
                a.erro("INDICE", _junta(c, chave), "%s. %s" % ("falta o campo" if chave not in entrada else
                                                              "é %s, que não é a forma do esquema"
                                                              % _mostra(entrada[chave], 30), _CONSERTO_DO_INDICE))
        if comum.data_hora_valida(entrada.get("gerada_em")):
            geradas.append(entrada["gerada_em"])
    atualizado = indice.get("atualizado_em")
    if edicoes is None and atualizado != (max(geradas) if geradas else None) and (geradas or atualizado is not None):
        a.erro("INDICE", "atualizado_em", "é %s; deveria ser o maior gerada_em das entradas, %s. %s"
               % (_mostra(atualizado, 30), _mostra(max(geradas) if geradas else None), _CONSERTO_DO_INDICE))
    if edicoes is not None:
        esperado = monta_indice(edicoes)
        certas = OrderedDict((entrada["data"], entrada) for entrada in esperado["edicoes"])
        escritas = {}
        for posicao, entrada in enumerate(lista):
            if isinstance(entrada, dict) and isinstance(entrada.get("data"), str):
                escritas.setdefault(entrada["data"], (posicao, entrada))
        for data, certa in certas.items():
            if data not in escritas:
                a.erro("INDICE", "edicoes", "falta a entrada da edição de %s, que existe em edicoes/. %s"
                       % (data, _CONSERTO_DO_INDICE))
                continue
            posicao, escrita = escritas[data]
            diferentes = [chave for chave in certa if chave not in escrita or not _igual_em_json(certa[chave], escrita[chave])]
            diferentes += [chave for chave in escrita if chave not in certa]
            if diferentes:
                a.erro("INDICE", "edicoes[%d]" % posicao, "não bate com edicoes/%s.json nos campos: %s. %s"
                       % (data, _lista_em_texto(_uma_linha(d)[:30] for d in diferentes), _CONSERTO_DO_INDICE))
        for data, (posicao, _) in sorted(escritas.items()):
            if data not in certas:
                a.erro("INDICE", "edicoes[%d]" % posicao, "cita a edição de %s, e não há edicoes/%s.json legível. %s"
                       % (_uma_linha(data)[:20], _uma_linha(data)[:20], _CONSERTO_DO_INDICE))
        if not _igual_em_json(atualizado, esperado["atualizado_em"]):
            a.erro("INDICE", "atualizado_em", "é %s; deveria ser o maior gerada_em das edições, %s. %s"
                   % (_mostra(atualizado, 30), _mostra(esperado["atualizado_em"]), _CONSERTO_DO_INDICE))
    return a.fecha()


def confere_feed(bruto):
    """feed.xml: bem formado e só com o que o CONTRATO, seção 4.5, deixa passar. `bruto` são os bytes do arquivo.

    As mesmas conferências do workflow de publicação (raiz feed e todos os elementos no espaço de nomes do
    Atom; sem DOCTYPE, ENTITY nem instrução além da declaração xml), mais duas: o tipo dos textos, que nunca
    é html nem xhtml, e o endereço dos links, que é relativo, http ou https. Assim a rotina vê o problema
    antes de empurrar a edição."""
    a = _Achados("feed.xml")
    conserto = "O feed é gerado: rode publica.py refaz."
    if not isinstance(bruto, (bytes, bytearray)):
        a.erro("FEED", "", "não deu para ler. %s" % conserto)
        return a.fecha()
    if b"\0" in bruto or b"<!DOCTYPE" in bruto or b"<!ENTITY" in bruto:
        a.erro("FEED", "", "traz DOCTYPE, ENTITY ou byte nulo, que o feed do INFOCENARIUM não pode ter. %s" % conserto)
        return a.fecha()
    if bruto.count(b"<?") > 1 or (b"<?" in bruto and not bruto.startswith(b"<?xml ")):
        a.erro("FEED", "", "traz instrução de processamento além da declaração <?xml …?> do começo (folha de "
               "estilo, por exemplo). %s" % conserto)
        return a.fecha()
    try:
        raiz = ET.fromstring(bytes(bruto))
    except (ET.ParseError, ValueError, RecursionError, LookupError) as erro:
        a.erro("FEED", "", "XML mal formado (%s). %s" % (_uma_linha(erro)[:80], conserto))
        return a.fecha()
    prefixo = "{%s}" % NS_ATOM
    if raiz.tag != prefixo + "feed":
        a.erro("FEED", "", "a raiz é %s; deveria ser <feed> do Atom (%s). %s" % (_mostra(str(raiz.tag), 60), NS_ATOM, conserto))
        return a.fecha()
    fora = sorted(set(str(e.tag) for e in raiz.iter() if not str(e.tag).startswith(prefixo)))
    if fora:
        a.erro("FEED", "", "traz elemento fora do Atom: %s. O feed só leva elementos do Atom. %s"
               % (_mostra(fora[0], 60), conserto))
    for elemento in raiz.iter():
        nome = str(elemento.tag)[len(prefixo):] if str(elemento.tag).startswith(prefixo) else ""
        if nome in ("title", "subtitle", "summary", "content", "rights") and elemento.get("type") not in (None, "text"):
            a.erro("FEED", "", "o elemento <%s> tem type %s; texto do feed é sempre puro (type \"text\" ou sem o "
                   "atributo). %s" % (nome, _mostra(elemento.get("type"), 20), conserto))
            break
        endereco = elemento.get("href") if nome == "link" else None
        # O leitor de feed tira espaço, tabulação e quebra de linha do endereço antes de ler o esquema
        # ("java&#9;script:" vira "javascript:"): o esquema é lido do mesmo jeito aqui.
        endereco = _RE_BRANCO_DE_HREF.sub("", endereco) if endereco is not None else None
        if endereco is not None and re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", endereco) \
                and not re.match(r"https?://", endereco):
            a.erro("FEED", "", "o link %s não é http, https nem relativo. %s" % (_mostra(endereco, 60), conserto))
            break
    return a.fecha()


# ---------------------------------------------------------------- git e regras de crescimento (G1 a G4)

# Variáveis que apontariam o git para outro repositório: saem do ambiente de cada chamada.
_VARIAVEIS_DO_GIT = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
                     "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_COMMON_DIR", "GIT_NAMESPACE", "GIT_PREFIX")
_ARQUIVOS_DA_ROTINA = ("feed.xml", "dados/players.json", "dados/vetores.json", "edicoes/indice.json")
_TIPOS_DE_MUDANCA = {"A": "arquivo novo", "M": "arquivo alterado", "D": "arquivo apagado"}


class _ErroDeGit(Exception):
    pass


class Git(object):
    """O git de uma raiz, só para leitura: nenhum comando daqui grava no repositório. Crie com abre_git()."""

    def __init__(self, raiz):
        self.raiz = raiz

    def roda(self, argumentos, entrada=None):
        """Roda `git argumentos…` sem shell e com tempo limite. Devolve (código, saída em bytes, erro em uma linha)."""
        ambiente = dict((k, v) for k, v in os.environ.items() if k not in _VARIAVEIS_DO_GIT)
        # Sem trava opcional (o git não regrava o índice), sem pergunta no terminal e sem busca na rede.
        ambiente.update(GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0", GIT_NO_LAZY_FETCH="1", LC_ALL="C")
        try:
            feito = subprocess.run(["git"] + list(argumentos), cwd=self.raiz, env=ambiente, input=entrada,
                                   stdin=subprocess.DEVNULL if entrada is None else None,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=TEMPO_DO_GIT)
        except FileNotFoundError:
            return 127, b"", "o programa git não está instalado"
        except subprocess.TimeoutExpired:
            return 124, b"", "o git não respondeu em %d segundos" % TEMPO_DO_GIT
        except OSError as erro:
            return 126, b"", "não deu para rodar o git (%s)" % type(erro).__name__
        linhas = feito.stderr.decode("utf-8", "replace").strip().splitlines()
        return feito.returncode, feito.stdout, _uma_linha(linhas[0])[:200] if linhas else ""

    def revisao(self, ref):
        """O identificador do commit de uma revisão (nome, como origin/main, ou identificador). None se não existe."""
        if not isinstance(ref, str) or not ref.strip() or ref.startswith("-"):
            return None
        codigo, saida, _ = self.roda(["rev-parse", "--verify", "--quiet", ref + "^{commit}"])
        texto = saida.decode("ascii", "replace").strip()
        return texto if codigo == 0 and re.fullmatch("[0-9a-f]{40,64}", texto) else None

    def conteudo(self, revisao, caminho):
        """Os bytes de um arquivo numa revisão (`git cat-file blob REV:caminho`). None se não existe lá.
        Com a revisão vazia, o arquivo como está no índice do git (o que vai no próximo commit)."""
        codigo, saida, _ = self.roda(["cat-file", "blob", "%s:%s" % (revisao, caminho)])
        return saida if codigo == 0 else None

    def arvore(self, revisao):
        """{caminho: (modo, tipo, identificador)} de todos os arquivos de uma revisão."""
        codigo, saida, erro = self.roda(["ls-tree", "-r", "-z", "--full-tree", revisao])
        if codigo != 0:
            raise _ErroDeGit(erro or "git ls-tree falhou")
        arvore = {}
        for entrada in saida.split(b"\0"):
            meta, tabulacao, caminho = entrada.partition(b"\t")
            partes = meta.decode("ascii", "replace").split()
            if tabulacao and len(partes) == 3:
                arvore[os.fsdecode(caminho)] = tuple(partes)
        return arvore

    def no_disco(self):
        """Os caminhos que contam no disco: os que o git acompanha e os novos que o .gitignore não esconde."""
        codigo, saida, erro = self.roda(["ls-files", "-z", "--cached", "--others", "--exclude-standard"])
        if codigo != 0:
            raise _ErroDeGit(erro or "git ls-files falhou")
        return set(os.fsdecode(caminho) for caminho in saida.split(b"\0") if caminho)


def abre_git(raiz):
    """(Git, "") se `raiz` é a raiz de um repositório git; senão (None, motivo).

    Pasta que só está DENTRO de outro repositório não conta: as regras G comparam a raiz inteira."""
    git = Git(raiz)
    codigo, saida, erro = git.roda(["rev-parse", "--show-toplevel"])
    if codigo != 0:
        if not erro or "not a git repository" in erro:
            return None, "a pasta não é um repositório git"
        return None, "o git respondeu: %s" % erro if codigo < 124 else erro
    topo = os.fsdecode(saida).rstrip("\r\n")
    if not topo or os.path.realpath(topo) != os.path.realpath(raiz):
        return None, "a pasta está dentro de outro repositório git, e a raiz dele não é esta"
    return git, ""


def _identificador_de_blob(conteudo, tamanho):
    """O identificador que o git dá a um conteúdo: SHA-1 (40 letras) ou SHA-256 (64), conforme o repositório."""
    conta = hashlib.sha256() if tamanho == 64 else hashlib.sha1()
    conta.update(("blob %d" % len(conteudo)).encode("ascii") + b"\0")
    conta.update(conteudo)
    return conta.hexdigest()


def _mudancas(git, revisao):
    """O que difere, no disco, de uma revisão: {caminho: "A" (novo), "M" (alterado) ou "D" (apagado)}.

    É a lista de `git diff --name-only REV` mais os arquivos novos de `git status --untracked-files=all`,
    mas calculada pelo conteúdo, sem tocar no índice do git: assim a pasta limpa e a pasta com arquivo novo
    sem commit dão a resposta certa, e nada é gravado. Arquivo que o .gitignore esconde não conta."""
    arvore = git.arvore(revisao)
    mudancas, duvidosos = {}, []
    for caminho, (modo, tipo, identificador) in arvore.items():
        if tipo != "blob":
            continue
        inteiro = os.path.join(git.raiz, caminho)
        if not os.path.lexists(inteiro):
            mudancas[caminho] = "D"
            continue
        try:
            if os.path.islink(inteiro):
                conteudo = os.fsencode(os.readlink(inteiro)) if modo == "120000" else None
            elif os.path.isfile(inteiro) and modo != "120000":
                with open(inteiro, "rb") as arquivo:
                    conteudo = arquivo.read()
            else:
                conteudo = None
        except OSError:
            conteudo = None
        if conteudo is None:
            mudancas[caminho] = "M"
        elif _identificador_de_blob(conteudo, len(identificador)) != identificador:
            duvidosos.append(caminho)
    # O que parece mudado pode ser só filtro do git (fim de linha, por exemplo): o próprio git desempata.
    simples = [c for c in duvidosos if "\n" not in c and "\r" not in c]
    confirmados = {}
    if simples:
        codigo, saida, _ = git.roda(["hash-object", "--stdin-paths"], os.fsencode("\n".join(simples) + "\n"))
        linhas = saida.decode("ascii", "replace").split()
        if codigo == 0 and len(linhas) == len(simples):
            confirmados = dict(zip(simples, linhas))
    for caminho in duvidosos:
        if confirmados.get(caminho) != arvore[caminho][2]:
            mudancas[caminho] = "M"
    for caminho in git.no_disco():
        if caminho not in arvore and os.path.lexists(os.path.join(git.raiz, caminho)):
            mudancas[caminho] = "A"
    return mudancas


def _caminho_permitido(caminho):
    """Regra G4: os caminhos que a rotina pode mudar. Em edicoes/, só o que o publica.py grava: a edição
    (AAAA-MM-DD.json), o texto dela (AAAA-MM-DD.md) e o índice. Fora dela: feed.xml, dados/players.json e
    dados/vetores.json. Subpasta e arquivo de outro nome não entram."""
    if caminho in _ARQUIVOS_DA_ROTINA:
        return True
    pasta, _, nome = caminho.rpartition("/")
    lido = _RE_NOME_DE_EDICAO.fullmatch(nome) if pasta == "edicoes" else None
    return lido is not None and comum.data_valida(lido.group(1))


def _json_de_bytes(bruto):
    try:
        return json.loads(bruto.decode("utf-8")) if bruto is not None else None
    except (ValueError, RecursionError):
        return None


def _confere_registro(a, regra, chave, antigo, novo, base, livres=(), origem=None):
    """Regras G1 e G2: as entradas da base continuam iguais e na mesma ordem; só entram novas no fim."""
    conserto = "O registro só cresce, e quem grava nele é o publica.py: pare, sem commit, e relate."
    if not isinstance(antigo, dict) or not isinstance(antigo.get(chave), list):
        return  # a base não tinha o registro, ou não dava para ler: nada a proteger
    if not isinstance(novo, dict) or not isinstance(novo.get(chave), list):
        a.erro(regra, chave, "a lista sumiu ou deixou de ser lista; em %s tinha %s. %s"
               % (base, _conta(len(antigo[chave]), "entrada", "entradas"), conserto))
        return
    velha, nova = antigo[chave], novo[chave]
    if len(nova) < len(velha):
        a.erro(regra, chave, "tem %s, e em %s tinha %d: entrada não se apaga. %s"
               % (_conta(len(nova), "entrada", "entradas"), base, len(velha), conserto))
    for indice, entrada in enumerate(velha[:len(nova)]):
        if not _igual_em_json(entrada, nova[indice]):
            nome = entrada.get("id") if isinstance(entrada, dict) else None
            a.erro(regra, "%s[%d]" % (chave, indice), "a entrada %s de %s foi mudada, apagada ou trocada de lugar. %s"
                   % (_mostra(nome, 50), base, conserto))
            break
    if origem is not None:
        for indice in range(len(velha), len(nova)):
            entrada = nova[indice]
            if not isinstance(entrada, dict) or entrada.get("origem") != origem:
                a.erro(regra, "%s[%d].origem" % (chave, indice), "é %s; entrada nova, posta pela rotina, leva "
                       "origem %s. %s" % (_mostra(entrada.get("origem") if isinstance(entrada, dict) else entrada, 30),
                                          _mostra(origem), conserto))
    for campo in sorted(set(antigo) | set(novo)):
        if campo == chave or campo in livres:
            continue
        if campo not in antigo or campo not in novo or not _igual_em_json(antigo[campo], novo[campo]):
            a.erro(regra, _uma_linha(campo)[:40], "o campo mudou em relação a %s, e a rotina só acrescenta "
                   "entradas em %s. %s" % (base, chave, conserto))


def confere_crescimento(raiz, base):
    """As regras G1 a G4 (ESQUEMA, seção 10): o que mudou no disco em relação à revisão `base` do git.

    G4: só mudam os caminhos da rotina. G3: edição que existe na base não muda nem some, salvo a de estado
    falha, que pode ser trocada. G1 e G2: players.json e vetores.json só crescem, no fim.
    Sem git na raiz, ou com revisão que não existe: um ERRO de regra GIT."""
    git, motivo = abre_git(raiz)
    if git is None:
        return [Achado(ERRO, "GIT", "--base", "as regras G precisam do git, e %s. Rode na raiz do repositório, "
                       "ou tire o --base." % motivo)]
    revisao = git.revisao(base)
    if revisao is None:
        return [Achado(ERRO, "GIT", "--base", "a revisão %s não existe neste repositório. Confira o nome (ex.: "
                       "origin/main) ou o identificador do commit; pode faltar um git fetch." % _mostra(base, 60))]
    try:
        mudancas = _mudancas(git, revisao)
    except _ErroDeGit as erro:
        return [Achado(ERRO, "GIT", "--base", "o git falhou ao comparar com %s (%s). Rode de novo; persistindo, "
                       "pare, sem commit, e relate." % (_mostra(base, 60), erro))]
    achados, nome_da_base = [], _mostra(base, 40)
    for caminho in sorted(mudancas):
        if _caminho_permitido(caminho):
            continue
        if mudancas[caminho] == "A":
            conserto = "Se foi você que criou, apague só ele e confira de novo."
        else:
            conserto = "A rotina não mexe nesse arquivo: pare, sem commit, e relate."
        achados.append(Achado(ERRO, "G4", _uma_linha(caminho)[:200] or "?", "%s fora dos caminhos que a rotina pode "
                              "mudar (em edicoes/, só AAAA-MM-DD.json, AAAA-MM-DD.md e indice.json; mais feed.xml, "
                              "dados/players.json e dados/vetores.json). %s" % (_TIPOS_DE_MUDANCA[mudancas[caminho]], conserto)))
    falhas = {}
    for caminho in sorted(mudancas):
        lido = _RE_NOME_DE_EDICAO.fullmatch(caminho[len("edicoes/"):]) if caminho.startswith("edicoes/") else None
        if not lido or mudancas[caminho] == "A":
            continue
        data = lido.group(1)
        if mudancas[caminho] == "D":
            achados.append(Achado(ERRO, "G3", caminho, "existia em %s e sumiu. Edição publicada não some: pare, sem "
                                  "commit, e relate." % nome_da_base))
            continue
        if data not in falhas:
            antiga = _json_de_bytes(git.conteudo(revisao, "edicoes/%s.json" % data))
            falhas[data] = isinstance(antiga, dict) and antiga.get("estado") == "falha"
        if not falhas[data]:
            achados.append(Achado(ERRO, "G3", caminho, "está diferente do que há em %s. Edição publicada não muda "
                                  "(só a de estado 'falha' pode ser trocada): a correção vai na errata da edição "
                                  "de hoje. Pare, sem commit, e relate." % nome_da_base))
    for caminho, chave, regra, livres, origem in (("dados/players.json", "players", "G1", ("atualizado_em",), "rotina"),
                                                  ("dados/vetores.json", "vetores", "G2", (), None)):
        if mudancas.get(caminho) != "M":
            continue
        a = _Achados(caminho)
        novo, _, problema = le_json_do_repositorio(os.path.join(raiz, caminho), caminho)
        if problema is None:
            _confere_registro(a, regra, chave, _json_de_bytes(git.conteudo(revisao, caminho)), novo, nome_da_base,
                              livres, origem)
        achados += a.fecha()
    for caminho, regra in (("dados/players.json", "G1"), ("dados/vetores.json", "G2")):
        if mudancas.get(caminho) == "D":
            achados.append(Achado(ERRO, regra, caminho, "existia em %s e sumiu. O registro só cresce: pare, sem "
                                  "commit, e relate." % nome_da_base))
    return achados


# ---------------------------------------------------------------- arquivos que dão ordem a agente (AGENTE)

# O agente da rotina carrega estes arquivos sozinho, antes do manual: o Claude Code lê os da primeira linha e os de
# .claude/; o OpenCode lê AGENTS.md, opencode.json e .opencode/. Um deles plantado no repositório transforma o
# sequestro de um dia em instrução de todo dia. O INFOCENARIUM não tem nenhum.
_NOMES_DE_AGENTE = ("CLAUDE.md", "CLAUDE.local.md", "AGENTS.md", ".mcp.json", "opencode.json",
                    "opencode.jsonc")
_PASTAS_DE_AGENTE = (".claude", ".opencode")
_AJUSTE_DE_ATRIBUICAO = ".claude/settings.json"  # a única exceção: só com a chave attribution


def _da_ordem_a_agente(caminho):
    partes = caminho.split("/")
    return (partes[-1] in _NOMES_DE_AGENTE
            or any(pasta in _PASTAS_DE_AGENTE for pasta in partes[:-1]))


def _so_atribuicao(conteudo):
    objeto = _json_de_bytes(conteudo)
    return isinstance(objeto, dict) and list(objeto) == ["attribution"]


def confere_agente(raiz):
    """Regra AGENTE (ESQUEMA, seção 10): nenhum arquivo acompanhado pelo git se chama CLAUDE.md, CLAUDE.local.md,
    AGENTS.md, .mcp.json, opencode.json ou opencode.jsonc, nem fica dentro de uma pasta .claude/ ou .opencode/.
    Exceção: .claude/settings.json só com a chave
    attribution. A lista é a do git (`git ls-files`, o que vai no commit), nunca a do disco: o ambiente de
    trabalho cria sozinho, fora do git, arquivos em .claude/. Sem git na raiz, a regra não confere."""
    git, _ = abre_git(raiz)
    if git is None:
        return []
    codigo, saida, erro = git.roda(["ls-files", "-z", "--cached"])
    if codigo != 0:
        return [Achado(AVISO, "AGENTE", ".", "não deu para listar os arquivos do git (%s): a regra não foi "
                       "conferida. Rode de novo." % (erro or "git ls-files falhou"))]
    achados = []
    for caminho in sorted(set(os.fsdecode(c) for c in saida.split(b"\0") if c)):
        if not _da_ordem_a_agente(caminho):
            continue
        rotulo = _uma_linha(caminho)[:200] or "?"
        if caminho == _AJUSTE_DE_ATRIBUICAO:
            if _so_atribuicao(git.conteudo("", caminho)):
                continue
            achados.append(Achado(ERRO, "AGENTE", rotulo, "pode existir só com a chave attribution (o texto de "
                                  "atribuição dos commits), e traz outra coisa: regra, gancho ou permissão de agente "
                                  "não entram no repositório. Se não foi o dono que mudou, pare, sem commit, e "
                                  "relate."))
            continue
        achados.append(Achado(ERRO, "AGENTE", rotulo, "arquivo que dá ordem a agente de IA (o agente da rotina o "
                              "carrega sozinho, antes do manual), acompanhado pelo git. O INFOCENARIUM não tem "
                              "nenhum: pare, sem commit, e relate. Quem tira é o dono."))
    return achados


# ---------------------------------------------------------------- o repositório inteiro (modos --tudo e --dados)

class Repositorio(object):
    """O que o validador lê de uma raiz. Monte com carrega().

    .raiz, .dados (Dados), .problemas (lista de Achado: o que não deu para ler ou não serve de base),
    .edicoes ({data: edição}, só as que deu para ler), .tamanhos ({data: bytes}), .ilegiveis (datas de edição
    que não deu para ler), .textos (datas que têm o .md), .estranhos (avisos: arquivo de nome estranho em
    edicoes/), .indice (objeto de edicoes/indice.json, ou None), .tem_indice (o arquivo existe) e .historico
    (Historico de .edicoes)."""

    def __init__(self, raiz):
        self.raiz = raiz
        self.dados = Dados()
        self.problemas = []
        self.edicoes, self.tamanhos = OrderedDict(), {}
        self.ilegiveis, self.textos = set(), set()
        self.estranhos = []
        self.indice, self.tem_indice = None, False
        self.historico = Historico()

    def dados_servem(self):
        """Os dados de dados/ dão para conferir edição? (Nenhum problema fatal ao carregar.)"""
        return not any(a.caminho.startswith("dados/") for a in self.problemas)


def carrega(raiz, com_edicoes=True):
    """Lê o repositório inteiro num objeto Repositorio. Nunca dá exceção por arquivo torto.

    Com `com_edicoes=False` lê só dados/ e edicoes/indice.json (é o que o modo --dados precisa)."""
    repositorio = Repositorio(raiz)
    repositorio.dados, problemas = carrega_dados(raiz)
    repositorio.problemas = list(problemas)
    pasta = os.path.join(raiz, "edicoes")
    try:
        nomes = sorted(os.listdir(pasta)) if os.path.isdir(pasta) else []
    except OSError as erro:
        nomes = []
        repositorio.problemas.append(Achado(ERRO, "ARQUIVO", "edicoes", "não deu para listar a pasta (%s). "
                                            "Confira as permissões." % type(erro).__name__))
    if os.path.lexists(pasta) and not os.path.isdir(pasta):
        repositorio.problemas.append(Achado(ERRO, "ARQUIVO", "edicoes", "deveria ser uma pasta. Tire o que está "
                                            "nesse lugar."))
    for nome in nomes:
        rotulo = "edicoes/" + _uma_linha(nome)[:80]
        inteiro = os.path.join(pasta, nome)
        lido = _RE_NOME_DE_EDICAO.fullmatch(nome)
        if nome == "indice.json":
            repositorio.tem_indice = True
            repositorio.indice, _, problema = le_json_do_repositorio(inteiro, rotulo)
            if problema is None and repositorio.indice is None:
                problema = Achado(ERRO, "INDICE", rotulo, "deveria ser um objeto, e é null. " + _CONSERTO_DO_INDICE)
            if problema:
                repositorio.problemas.append(problema)
        elif not com_edicoes or nome.startswith("."):
            continue
        elif lido and comum.data_valida(lido.group(1)):
            data = lido.group(1)
            if lido.group(2) == "md":
                if os.path.isfile(inteiro) and not os.path.islink(inteiro):
                    repositorio.textos.add(data)
                continue
            edicao, tamanho, problema = le_json_do_repositorio(inteiro, rotulo)
            if problema:
                repositorio.problemas.append(problema)
                repositorio.ilegiveis.add(data)
            else:
                repositorio.edicoes[data] = edicao
                repositorio.tamanhos[data] = tamanho
        elif nome.endswith((".json", ".md")):
            # Só avisa: o arquivo pode ser do dono, e a rotina não consegue criar um destes (a regra G4 acusa).
            repositorio.estranhos.append(Achado(
                AVISO, "ARQUIVO", rotulo, "não é edição, nem texto de edição, nem o índice: o nome não é uma data. "
                "Em edicoes/ só entram AAAA-MM-DD.json, AAAA-MM-DD.md e indice.json. Se foi você que criou, apague-o."))
    repositorio.historico = Historico(repositorio.edicoes)
    return repositorio


def _existe_em(raiz):
    def existe(caminho):
        inteiro = os.path.join(raiz, caminho)
        return os.path.isfile(inteiro) and not os.path.islink(inteiro)
    return existe


def _le_feed(raiz):
    """(bytes ou None, achado ou None) do feed.xml. Sem o arquivo: (None, None)."""
    caminho = os.path.join(raiz, "feed.xml")
    try:
        estado = os.lstat(caminho)
    except OSError:
        return None, None
    if not stat.S_ISREG(estado.st_mode) or estado.st_size > LIMITE_ARQUIVO:
        return None, Achado(ERRO, "FEED", "feed.xml", "não é arquivo comum, ou passa de %d bytes. O feed é gerado: "
                            "rode publica.py refaz." % LIMITE_ARQUIVO)
    try:
        with open(caminho, "rb") as arquivo:
            return arquivo.read(), None
    except OSError as erro:
        return None, Achado(ERRO, "FEED", "feed.xml", "não deu para ler (%s). Confira as permissões."
                            % type(erro).__name__)


def confere_tudo(raiz, dia, base=None):
    """O modo --tudo: os dados; as regras R e H em cada edição, com as (dia) só na edição de `dia`; índice
    igual aos arquivos; cada edição com seu .md; feed.xml bem formado. Com `base`, também as regras G.

    Devolve a lista de Achado, com o nome do arquivo na frente de cada caminho."""
    repositorio = carrega(raiz)
    achados = repositorio.problemas + repositorio.estranhos
    achados += confere_dados(repositorio.dados)
    edicoes = repositorio.edicoes
    if not repositorio.dados_servem():
        if edicoes:
            achados.append(Achado(ERRO, "DADOS", "edicoes", "as %d edições não foram conferidas: os dados de dados/ "
                                  "não servem de base (erros acima). Conserte os dados e confira de novo."
                                  % len(edicoes)))
    else:
        for data in sorted(edicoes):
            achados += confere_edicao(edicoes[data], repositorio.dados, repositorio.historico, do_dia=(data == dia),
                                      data_do_arquivo=data, tamanho=repositorio.tamanhos[data],
                                      arquivo="edicoes/%s.json" % data)
    for data in sorted(set(edicoes) | repositorio.ilegiveis):
        if data not in repositorio.textos:
            achados.append(Achado(ERRO, "MD", "edicoes/%s.md" % data, "falta a versão em texto da edição de %s. "
                                  "Ela é gerada: rode publica.py refaz." % data))
    for data in sorted(repositorio.textos):
        if data not in edicoes and data not in repositorio.ilegiveis:
            achados.append(Achado(ERRO, "MD", "edicoes/%s.md" % data, "não há edicoes/%s.json: é texto de edição "
                                  "que não existe. Se foi você que criou, apague-o." % data))
    if repositorio.tem_indice:
        if repositorio.indice is not None:
            achados += confere_indice(repositorio.indice, edicoes, _existe_em(raiz))
    elif edicoes or repositorio.ilegiveis:
        achados.append(Achado(ERRO, "INDICE", "edicoes/indice.json", "falta o índice, e há edições em edicoes/. "
                              + _CONSERTO_DO_INDICE))
    feed, problema = _le_feed(raiz)
    if problema:
        achados.append(problema)
    elif feed is not None:
        achados += confere_feed(feed)
    elif edicoes:
        achados.append(Achado(AVISO, "FEED", "feed.xml", "não existe, e há edições em edicoes/. O feed é gerado: "
                              "rode publica.py refaz."))
    achados += confere_agente(raiz)
    if base is not None:
        achados += confere_crescimento(raiz, base)
    return achados


def _confere_so_dados(raiz):
    """O modo --dados."""
    repositorio = carrega(raiz, com_edicoes=False)
    return (repositorio.problemas + confere_dados(repositorio.dados, repositorio.indice, _existe_em(raiz))
            + confere_agente(raiz))


def _resolve(arquivo, raiz):
    """O caminho de um arquivo dado na linha de comando: como veio; se não existe assim, dentro da raiz."""
    if os.path.isabs(arquivo) or os.path.exists(arquivo):
        return os.path.abspath(arquivo)
    na_raiz = os.path.join(raiz, arquivo)
    return na_raiz if os.path.exists(na_raiz) else os.path.abspath(arquivo)


def _confere_uma_edicao(raiz, arquivo, anterior=None):
    """O modo --edicao: todas as regras R, inclusive as (dia). Arquivo dentro de edicoes/ da raiz: também as
    regras H, contra as outras edições. `anterior` força a edição anterior (e o histórico passa a ser só ela)."""
    dados, problemas = carrega_dados(raiz)
    if problemas:
        return problemas + [Achado(ERRO, "DADOS", "dados", "a edição não foi conferida: os dados de dados/ não "
                                   "servem de base (erros acima). Conserte os dados, ou aponte --raiz para a "
                                   "pasta certa.")]
    caminho = _resolve(arquivo, raiz)
    rotulo = _uma_linha(arquivo)[:200].replace(" ", "_") or "edicao"
    edicao, tamanho, problema = le_json_do_repositorio(caminho, rotulo)
    if problema:
        return [problema]
    achados, historico, data_do_arquivo = [], None, None
    if os.path.realpath(os.path.dirname(caminho)) == os.path.realpath(os.path.join(raiz, "edicoes")):
        lido = _RE_NOME_DE_EDICAO.fullmatch(os.path.basename(caminho))
        if lido and lido.group(2) == "json" and comum.data_valida(lido.group(1)):
            data_do_arquivo = lido.group(1)
        else:
            achados.append(Achado(ERRO, "R01", rotulo, "o nome do arquivo não é uma data: em edicoes/ a edição se "
                                  "chama AAAA-MM-DD.json, com a data igual ao campo data. Renomeie o arquivo, ou "
                                  "publique com publica.py edicao."))
        historico = carrega(raiz).historico
    if anterior is not None:
        rotulo_anterior = _uma_linha(anterior)[:200].replace(" ", "_") or "anterior"
        antiga, _, problema = le_json_do_repositorio(_resolve(anterior, raiz), rotulo_anterior)
        if problema:
            return achados + [problema]
        data_antiga = antiga.get("data") if isinstance(antiga, dict) else None
        data_nova = edicao.get("data") if isinstance(edicao, dict) else None
        if not _e_data(data_antiga):
            return achados + [Achado(ERRO, "ARQUIVO", rotulo_anterior, "não é uma edição: falta o campo data, "
                                     "AAAA-MM-DD. Passe em --anterior o arquivo de uma edição.")]
        if _e_data(data_nova) and data_antiga >= data_nova:
            return achados + [Achado(ERRO, "ARQUIVO", rotulo_anterior, "é a edição de %s, que não é anterior à "
                                     "edição conferida (%s). Passe em --anterior uma edição de data anterior."
                                     % (data_antiga, data_nova))]
        historico = Historico({data_antiga: antiga}, completo=False)
    return achados + confere_edicao(edicao, dados, historico, True, data_do_arquivo, tamanho)


# ---------------------------------------------------------------- linha de comando

def principal(argv):
    """A linha de comando (CONTRATO, seção 3). Recebe os argumentos e devolve o código de saída."""
    an = comum.opcoes("Confere edição e dados do INFOCENARIUM. Nunca grava nada e não usa a rede. Sem opção de modo, "
                      "vale --tudo.", trabalho=False)
    modos = an.add_mutually_exclusive_group()
    modos.add_argument("--tudo", action="store_true",
                       help="dados, todas as edições, índice, textos e feed (é o padrão)")
    modos.add_argument("--dados", action="store_true", help="só os arquivos de dados/ e a forma do índice")
    modos.add_argument("--edicao", metavar="ARQ", help="uma edição só, como edição do dia")
    an.add_argument("--base", metavar="REF",
                    help="com --tudo: confere também o que mudou desde essa revisão do git (regras G1 a G4)")
    an.add_argument("--anterior", metavar="ARQ", help="com --edicao: força a edição anterior (testes)")
    args = comum.prepara(an.parse_args(argv), dia_padrao=comum.DIA_DE_HOJE)
    if args.anterior is not None and args.edicao is None:
        raise comum.ErroDeUso("--anterior só vale junto com --edicao")
    if args.base is not None and (args.dados or args.edicao is not None):
        raise comum.ErroDeUso("--base só vale no modo --tudo")
    if args.base is not None and (not args.base.strip() or args.base.startswith("-")):
        raise comum.ErroDeUso("--base: revisão ilegível %r (use um nome, como origin/main, ou o identificador "
                              "de um commit)" % args.base)
    for nome in ("edicao", "anterior"):
        if getattr(args, nome) is not None and not getattr(args, nome).strip():
            raise comum.ErroDeUso("--%s pede o nome de um arquivo" % nome)
    saida = comum.Saida(args.json)
    if args.dados:
        achados = _confere_so_dados(args.raiz)
    elif args.edicao is not None:
        achados = _confere_uma_edicao(args.raiz, args.edicao, args.anterior)
    else:
        achados = confere_tudo(args.raiz, args.dia, args.base)
    erros, avisos = separa(achados)
    erros, avisos = _corta(erros, ERRO), _corta(avisos, AVISO)
    for achado in erros + avisos:
        saida.linha(achado.linha())
    # --json: a forma comum ({"ok", "codigo", "veredito", "linhas"}, CONTRATO, seção 0) mais "erros" e "avisos".
    saida.dado("erros", [a.objeto() for a in erros])
    saida.dado("avisos", [a.objeto() for a in avisos])
    return saida.fecha(veredito(erros + avisos))


if __name__ == "__main__":
    comum.executa(principal)
