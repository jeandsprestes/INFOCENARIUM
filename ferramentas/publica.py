#!/usr/bin/env python3
"""publica.py: contexto do dia, publicação da edição, edição de falha, e índice, textos e feed. Sem rede.

LINHA DE COMANDO (CONTRATO, seção 4). Quatro subcomandos; as opções vêm depois do subcomando:

    python3 ferramentas/publica.py contexto [--dia D] [--trabalho P]
    python3 ferramentas/publica.py edicao   [--dia D] [--trabalho P] [--corta ID[,ID]] [--simula] [--url-base URL]
    python3 ferramentas/publica.py falha --motivo "TEXTO" [--dia D] [--trabalho P] [--url-base URL]
    python3 ferramentas/publica.py refaz    [--url-base URL]
    opções comuns: --raiz PASTA, --json

contexto  lê as edições e os dados e grava, na pasta de trabalho, contexto.json (a memória dos dias
          anteriores), mapa.txt (os veículos, uma linha cada) e modelo.txt (a forma do rascunho).
edicao    lê rascunho.json, completa os campos calculados, confere tudo (regras R, H e T) e, sem erro,
          grava a edição, o texto dela (.md), o índice, o feed e os dois registros (vetores e players).
falha     grava a edição de falha do dia: "sem edição hoje", com os níveis da edição anterior.
refaz     refaz o índice, todos os textos e o feed a partir dos arquivos de edição.

Saída: uma informação por linha; a última é o veredito, "OK …" ou "FALHA …". Código 0, 1 ou 2 (uso errado).
Os erros de regra saem no formato do valida.py: "ERRO REGRA caminho: problema. Conserto."

Regra nenhuma mora aqui. O que se calcula e o que se confere vem do valida.py (completa, confere_edicao,
confere_trabalho, monta_indice, alerta_anterior, prazo_do_vigiar…): o validador confere recalculando com as
mesmas funções, e assim os dois nunca discordam. Este arquivo junta as peças, escreve o texto, o feed e os
registros, e grava tudo ou nada: com erro, nenhum arquivo do repositório muda.
Nunca grava dados/veiculos.json, dados/regua.json nem dados/indicadores.json.
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
import argparse  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import stat  # noqa: E402
import xml.etree.ElementTree as ET  # noqa: E402
from datetime import timedelta  # noqa: E402

import comum  # noqa: E402
import valida  # noqa: E402

SUBCOMANDOS = ("contexto", "edicao", "falha", "refaz")
ENTRADAS_DO_FEED = 30  # edições no feed, as mais novas (CONTRATO, seção 4.5)
TITULO_DO_FEED = "INFOCENARIUM · monitor geopolítico e de IA"
BASE_PADRAO = "./"  # o último endereço base da lista: relativo, serve em qualquer lugar
UPDATED_SEM_ENTRADA = "1970-01-01T00:00:00Z"  # o updated do feed que não tem entrada (CONTRATO, seção 4.5)
LINHA_DE_EXEMPLO = "EDIÇÃO DE EXEMPLO · dados fictícios"
AVISO_DE_CONFLITO = ("Aviso: o INFOCENARIUM é escrito por modelos de IA, do setor de IA, que podem ser parte ou "
                     "concorrente nesta notícia: foi construído pelo Claude Fable e pelo Claude Opus, da Anthropic, e hoje "
                     "quem escreve é o GLM, da Z.ai.")
# Os textos abaixo são os do site, palavra por palavra (ESPEC-SITE, seções 2.2, 5.1 e 8.3): o .md e o site dizem o mesmo.
TETO_DO_CONFLITO = "Por isso a confiança deste item não passa de média."
NOTA_DE_RASCUNHO = "Mapa de veículos em rascunho, ainda sem revisão do dono."
SEM_GATILHO_NOVO = ("Sem gatilho novo. O nível desce um degrau depois de 2 edições seguidas sem gatilho. Edição sem dado "
                    "de preço não entra nessa conta.")
MOTIVO_MAXIMO = 200  # caracteres do --motivo (CONTRATO, seção 4.3)
# Janelas do contexto, em dias corridos antes do dia (CONTRATO, seção 4.1).
DIAS_DE_VIGIAR, DIAS_DE_CANDIDATO, DIAS_DE_VETOR = 30, 14, 30
# Folga do vigiar: a pergunta de prazo vencido há até 7 dias ainda volta, mesmo de edição com mais de 30 dias (até
# 37). Sem ela, o prazo no 30º dia só entraria no próprio dia, e uma falha nesse dia a perderia de vez.
DIAS_DE_FOLGA_DO_VIGIAR = 7
EDICOES_DE_HISTORIA, PERGUNTAS_VENCENDO = 3, 3
JANELA_NORMAL, JANELA_COM_BURACO = 36, 60  # horas de coleta: a segunda cobre o dia sem edição

# O texto de modelo.txt, igual ao do CONTRATO, seção 4.1. O confere_modelo() cruza com as tabelas do validador.
MODELO = r'''// MODELO DO RASCUNHO · copie a forma para /tmp/info/rascunho.json
// Linha que começa com // é comentário: não copie. Número entre aspas é o tamanho máximo do texto.
// Campo marcado (opcional) ou (só se …) sai quando não se aplica. Lista sem item fica [].
// O que não está aqui é calculado pelo publica.py: lado, saldo, indicadores, gatilho de preço, níveis e tendências.
{
  // o `dia` do contexto
  "data": "AAAA-MM-DD",
  // completa: 3 principais (1 ou mais de geopolítica) e 6 a 12 no radar (3 ou mais de IA).
  // reduzida: 1 a 3 principais e 3 a 12 no radar
  "estado": "completa",
  // o dia em uma frase
  "resumo": "240",
  "alerta": {
    // o que explica o nível geral: o gatilho mais alto de hoje, ou a origem do nível mantido. Não descreva a regra de descida
    "motivo": "400",
    // os 5 domínios, nesta ordem: energia, alimentos, cambio, suprimentos, conflito
    "dominios": [
      {
        "id": "energia",
        // 0 a 4 gatilhos seus. Os de preço entram sozinhos
        "gatilhos": [
          {
            // o código da célula da régua: dominio.nivel, com nível de 2 a 5
            "criterio": "energia.3",
            // o id do item de hoje que prova
            "ref": "p1",
            // o que houve, com número ou data. Estado que continua: "Segue em DD/MM: …"
            "texto": "200",
            // (opcional) true: fato grave fora da tabela, que equivale ao nível. Só nível 2 ou 3; 1 por edição; explique a equivalência no texto
            "excecao": true,
            // (opcional) true: acabou o estado que segurava o nível 4 ou 5. Pede ref de principal com confiança alta
            "alivio": true
          }
        ],
        // primeiro o que as notícias de hoje mudam; depois, o caminho até o Brasil (o `canal` do domínio, na régua).
        // Nível mantido sem gatilho: comece pela `origem`, com a data. Sem previsão de preço e sem ordem ao leitor
        "leitura": "300",
        // o próximo sinal que mudaria o nível
        "vigiar": "200"
      }
    ]
  },
  "principais": [
    {
      // p1, p2, p3
      "id": "p1",
      // geopolitica ou ia
      "categoria": "geopolitica",
      // descritivo, sem adjetivo
      "titulo": "120",
      // quem, o quê, onde, quando, quanto: só o que os dois campos afirmam igual ou um documento primário mostra
      "fato": "500",
      // (opcional) 0 a 3; cada um começa com "Segundo "
      "nao_confirmado": ["240"],
      // 2 a 4, de 2 partidos ou mais
      "ataques": [
        {
          // id do mapa; nunca "outro". Em principal, veículo de lado incerto (?) não atira
          "veiculo": "id",
          // quem sai mal no título e no primeiro parágrafo: id de player, id de partido, "outro" ou "nenhum" (o texto só relata ou só promove)
          "alvo": "id",
          // (só se alvo é "outro") o nome do alvo
          "alvo_nome": "60",
          // o que o veículo destacou e com que palavras. Só viu título e resumo: comece com "No título: ".
          // Alvo "nenhum": diga quem sai bem ("Promove a China: …").
          // Veículo que serve a player que é parte da notícia: comece avisando ("Agência do Estado russo, que é parte: …")
          // Valendo os dois, junte: "No título: agência do Estado russo, que é parte: …"
          "enquadramento": "240",
          // (opcional) o que está no fato e a página não traz. Só de página aberta nesta execução
          "omite": "200",
          // a página do veículo. A mesma URL entra em fontes, com o mesmo veiculo
          "url": "https://…"
        }
      ],
      // o dossiê: de 800 a 1.500 caracteres, em texto corrido, numa linha só
      "realmente": "1500",
      // 1 a 4; só mudança medida. Se nada mudou, um item só: "Nada mudou na prática até DD/MM: só declarações."
      "na_pratica": ["200"],
      // (só se dominios não é vazia) o que tende a encarecer, baratear, faltar ou atrasar no Brasil, e por qual caminho.
      // Prazo só com fonte do dia; sem fonte, não dê prazo.
      "no_brasil": "240",
      // (opcional) o tema da régua em que um ato da notícia mexe.
      // tema: pandemia_depois, ia_depois, moderacao, clima ou imigracao. sentido: azul ou vermelho. porque: o ato
      "eixo": {"tema": "clima", "sentido": "vermelho", "porque": "160"},
      // 0 a 4; uma linha por partido. Item de confiança baixa não tem placar
      "placar": [
        {
          "partido": "id",
          // ganha ou perde
          "efeito": "ganha",
          // 1, 2 ou 3 (a escala está em regua.json, chave forcas). No radar, 3 só com fonte forte
          "forca": 2,
          // preco, tropa, contrato, lei, voto, sancao ou narrativa (narrativa só com força 1)
          "evidencia": "sancao",
          // quem ganhou ou perdeu, pelo nome, e o quê; ou "Na pauta de [tema]: …"; em narrativa, qual veículo usou o fato
          "porque": "200"
        }
      ],
      // (só se placar é []) por que ninguém ganha nem perde ainda, e o que teria de acontecer
      "sem_placar": "160",
      // 0 a 2 na edição inteira
      "vetores": [
        {
          // id de players.json (o player novo do dia não vale)
          "player": "id",
          // id de partido; nunca o do player, nunca independentes
          "para": "id",
          // 1, 2 ou 3, na mesma escala do placar
          "forca": 1,
          // pandemia_depois, ia_depois, moderacao, clima, imigracao ou ordem
          "tema": "clima",
          // o ato do player
          "porque": "240",
          // a prova: URL de fonte forte que está em fontes; em notícia com conflito de interesse, de fonte primária.
          // O item precisa de fontes de 2 partidos
          "url": "https://…"
        }
      ],
      // 0 a 5 domínios que a notícia toca
      "dominios": ["energia"],
      // 1 a 3 perguntas de sim ou não, cada uma com "?" e data limite DD/MM. A data limite é a última DD/MM
      // do texto: ponha-a por último, em até 30 dias.
      // A primeira é a que derruba o dossiê: é ela que o INFOCENARIUM responde quando o prazo chega
      "vigiar": ["200"],
      // alta ou media
      "confianca": "alta",
      // (opcional) true se você vê conflito de interesse com a Anthropic que a máquina não marca.
      // Notícia de IA e notícia que cita a lista `conflito` da régua, o publica.py marca sozinho
      "conflito_de_interesse": true,
      // (opcional) o item anterior que este continua: AAAA-MM-DD/p1 ou AAAA-MM-DD/r4
      "continuacao_de": "AAAA-MM-DD/p1",
      // 3 a 8
      "fontes": [
        {
          // id do mapa, ou "outro". É o dono do site da url
          "veiculo": "id",
          // (só se veiculo é "outro") quem publicou
          "nome": "80",
          // o título original, como foi publicado
          "titulo": "200",
          "url": "https://…",
          // a data que aparece na página ou na mesa: de 2 dias antes da edição a 1 depois
          "publicado_em": "AAAA-MM-DD",
          // (opcional) true: documento primário, de veículo de tipo oficial ou dados, ou de site oficial
          "primaria": true
        }
      ]
    }
  ],
  "radar": [
    {
      // r1, r2, … em ordem
      "id": "r1",
      "categoria": "ia",
      "titulo": "120",
      "fato": "300",
      // um só, com os campos de um item de ataques
      "ataque": {"veiculo": "id", "alvo": "id", "alvo_nome": "60", "enquadramento": "240", "omite": "200", "url": "https://…"},
      // (opcional) como na principal
      "eixo": {"tema": "ia_depois", "sentido": "azul", "porque": "160"},
      // 0 a 2 linhas, com os campos do placar da principal
      "placar": [],
      // (só se placar é [])
      "sem_placar": "160",
      // 0 ou 1
      "vetores": [],
      "dominios": [],
      // alta, media ou baixa (baixa: o núcleo vem de fonte anônima)
      "confianca": "media",
      // (opcional)
      "conflito_de_interesse": true,
      // (opcional)
      "continuacao_de": "AAAA-MM-DD/r1",
      // 1 a 4, com os campos das fontes da principal
      "fontes": [{"veiculo": "id", "nome": "80", "titulo": "200", "url": "https://…", "publicado_em": "AAAA-MM-DD", "primaria": true}]
    }
  ],
  // uma frase para cada partido que aparece em algum placar
  "placar_do_dia": [{"partido": "id", "frase": "160"}],
  // 0 ou 1
  "novos_players": [
    {
      "id": "slug",
      "nome": "60",
      // governo, instituicao ou empresa (nunca regime)
      "tipo": "governo",
      // o partido de voto_tipico com mais posições iguais às do dna; empate dá independentes
      "partido": "id",
      // manutencao ou mudanca
      "time": "mudanca",
      // sempre true: quem confirma o time é o dono
      "time_discutivel": true,
      // B, R, Y ou W. Só posição sustentada por página aberta nesta execução; 4 ou mais diferentes de W
      "dna": {"pandemia_inicio": "W", "pandemia_depois": "Y", "ia_inicio": "W", "ia_depois": "B", "moderacao": "R", "clima": "W", "imigracao": "R"},
      // uma URL para cada posição diferente de W, e só para elas
      "dna_fontes": {"pandemia_depois": "https://…", "ia_depois": "https://…", "moderacao": "https://…", "imigracao": "https://…"},
      // temas de posição incerta; pode ser []
      "duvidas": ["moderacao"],
      // quem é, em uma linha
      "nota": "200",
      // por que entrou hoje e por que esse partido
      "justificativa": "400",
      "url": "https://…"
    }
  ],
  // 0 a 5: fato de edição anterior que uma fonte de hoje desmente
  "errata": [
    {
      "edicao": "AAAA-MM-DD",
      // (opcional) o id do item corrigido
      "item": "p2",
      "erro": "300",
      "correcao": "300",
      // (opcional; obrigatória com anula_vetor)
      "url": "https://…",
      // (opcional) o id, em vetores_recentes, do vetor que o fato desmentido sustentava
      "anula_vetor": "AAAA-MM-DD_p2_id"
    }
  ],
  // 0 a 3: uma para cada pergunta de vigiar_vencendo, no contexto
  "respostas": [
    {
      "edicao": "AAAA-MM-DD",
      "item": "p1",
      // cópia da pergunta
      "pergunta": "200",
      // sim, nao ou sem_dado
      "resposta": "sim",
      // o que houve, com data. Se desmente o dossiê daquele dia: "O INFOCENARIUM leu errado em DD/MM: …"
      "texto": "240",
      // (obrigatória com sim e com nao)
      "url": "https://…"
    }
  ],
  "bastidores": {
    // feeds, ou busca (a coleta falhou)
    "modo": "feeds",
    "paginas_lidas": 0,
    "buscas": 0,
    "minutos": 0,
    "injecoes_ignoradas": 0,
    // 0 a 5 atores centrais sem ficha na régua; use o mesmo id do contexto
    "candidatos": [{"id": "slug", "nome": "60", "motivo": "160"}],
    // 0 a 5 veículos fora do mapa que fizeram falta
    "veiculos_sugeridos": ["Nome (dominio.com)"],
    // o que não deu para conferir hoje, e que campo ficou em silêncio; nunca vazio
    "limites": "500"
  }
}
'''

# Rótulos das listas fechadas, para o texto da edição. São os mesmos que o site mostra.
_ESTADOS = {"completa": "Edição completa", "reduzida": "Edição reduzida", "falha": "Sem edição hoje"}
_TENDENCIAS = {"subindo": "subindo", "estavel": "estável", "descendo": "descendo"}
_CATEGORIAS = {"geopolitica": "Geopolítica", "ia": "IA"}
_CONFIANCAS = {"alta": "alta", "media": "média", "baixa": "baixa"}
_EVIDENCIAS = {"preco": "preço", "tropa": "tropa", "contrato": "contrato", "lei": "lei", "voto": "voto",
               "sancao": "sanção", "narrativa": "só narrativa"}
_RESPOSTAS = {"sim": "SIM", "nao": "NÃO", "sem_dado": "SEM DADO"}
_MODOS = {"feeds": "coleta normal, pelos feeds dos veículos", "busca": "a coleta falhou: edição feita por busca"}
# O nome curto do domínio, na linha "Desde 18/11: …" do .md, é o id; só este pede acento. A saída da
# ferramenta (o veredito, o resumo do contexto) usa o id puro.
_DOMINIOS_CURTOS = {"cambio": "câmbio"}

# Os códigos abaixo entram por chr(): assim este arquivo não traz caractere invisível nem metade de par
# substituto. São os dois separadores de linha do Unicode e a faixa dos substitutos.
_SEPARADORES = chr(0x2028) + chr(0x2029)
_SUBSTITUTOS = chr(0xD800) + "-" + chr(0xDFFF)

_RE_ID_DE_ITEM = re.compile(r"p[1-3]|r(?:1[0-2]|[1-9])")
_RE_PRINCIPAL = re.compile(r"p[1-9][0-9]?")  # a forma de principal que o site reconhece nas respostas
_RE_CITA_ITEM = re.compile(r"(?<![A-Za-z0-9_])(p[1-3]|r(?:1[0-2]|[1-9]))(?![A-Za-z0-9_])")
_RE_CONTINUACAO = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2})/(p[1-3]|r(?:1[0-2]|[1-9]))")
# Espaço, caractere de controle e metade solta de par substituto: tudo isso vira um espaço só.
_RE_JUNTA = re.compile("[" + r"\s\x00-\x1f\x7f-\x9f" + _SEPARADORES + _SUBSTITUTOS + "]+")
_RE_SUBSTITUTO = re.compile("[" + _SUBSTITUTOS + "]")
_RE_CODIGO = re.compile(r"[A-Za-z0-9][A-Za-z0-9_./-]{0,79}")
_RE_ESQUEMA = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:")
_RE_FORA_DA_BASE = re.compile(r"[\s\x00-\x20\x7f-\x9f<>\"'`\\#?]")
_RE_LINHA_E_COLUNA = re.compile(r"linha ([0-9]+), coluna ([0-9]+): ")
# Sinais de Markdown que levam barra (CONTRATO, seção 4.5), mais dois que também viram marca ou link: < e @.
_RE_SINAIS = re.compile(r"[\\\[\]()*_`#|<@]")
_RE_ESQUEMA_CRU = re.compile(r":(?=//)")
_RE_WWW = re.compile(r"(?i)(www)\.")
# Lista numerada só abre com o ponto seguido de espaço ou do fim da linha: "1.5" e "3.000 barris" ficam como estão.
_RE_NUMERO_NO_COMECO = re.compile(r"([0-9]{1,9})\.(?= |$)")
# O que o XML 1.0 não aceita (ou desaconselha) num texto: controles, metades de par substituto e os dois
# últimos códigos do plano básico. A quebra de linha fica: o conteúdo de uma entrada tem mais de uma linha.
_RE_FORA_DO_XML = re.compile("[^" + r"\x0a\x20-\x7e\xa0-" + chr(0xD7FF) + chr(0xE000) + "-" + chr(0xFFFD)
                             + chr(0x10000) + "-" + chr(0x10FFFF) + "]")
_RE_FORA_DA_URL = re.compile("[" + r"\x00-\x20\x7f-\x9f" + _SEPARADORES + _SUBSTITUTOS + "]")
_RE_REMOTO = re.compile(r"(?:^|[/:])([A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?)/([A-Za-z0-9._-]{1,100}?)"
                        r"(?:\.git)?/?$")

# As mensagens do leitor de JSON do Python, ditas para quem vai consertar o rascunho.
_ERROS_DE_JSON = (
    ("Expecting ',' delimiter", "falta vírgula entre dois itens, ou há aspa sobrando dentro de um texto"),
    ("Expecting property name enclosed in double quotes",
     "aqui devia vir o nome de um campo, entre aspas duplas; pode ser vírgula sobrando antes de }"),
    ("Expecting ':' delimiter", "falta : depois do nome do campo"),
    ("Expecting value", "aqui devia vir um valor; pode ser vírgula sobrando antes de ] ou de }"),
    ("Extra data", "sobra texto depois do fim do objeto"),
    ("Unterminated string starting at", "texto sem as aspas do fim"),
    ("Invalid control character at", "quebra de linha ou tabulação dentro de um texto: o texto fica numa linha só"),
    ("Invalid \\escape", "barra invertida solta dentro de um texto: tire a barra, ou dobre"),
    ("Invalid \\uXXXX escape", "código de caractere incompleto dentro de um texto: escreva o caractere direto"),
)


# ---------------------------------------------------------------- miudezas

def _objetos(valor):
    """Os itens que são objeto, de um valor que deveria ser lista de objetos."""
    return [v for v in valor if isinstance(v, dict)] if isinstance(valor, list) else []


def _objeto(valor):
    return valor if isinstance(valor, dict) else {}


def _textos(valor):
    return [v for v in valor if isinstance(v, str)] if isinstance(valor, list) else []


def _por_id(valor):
    """{id: objeto} de uma lista de objetos; se um id se repete, vale o primeiro."""
    saida = {}
    for objeto in _objetos(valor):
        if isinstance(objeto.get("id"), str) and objeto["id"] not in saida:
            saida[objeto["id"]] = objeto
    return saida


def _e_inteiro(valor):
    return isinstance(valor, int) and not isinstance(valor, bool)


def _como_texto(valor):
    """Um valor qualquer do JSON como texto: campo de texto que veio com outro tipo não derruba nada."""
    if isinstance(valor, str):
        return valor
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, (int, float)):
        return repr(valor)
    try:
        return json.dumps(valor, ensure_ascii=False)
    except (TypeError, ValueError, RecursionError):
        return str(valor)


def _uma_linha(valor):
    """Tudo numa linha só, sem caractere de controle: cada informação da saída e do texto é uma linha."""
    return " ".join(_RE_JUNTA.sub(" ", _como_texto(valor)).split())


def _entre_aspas(valor):
    return "'%s'" % _uma_linha(valor)[:60]


def _conta(quantos, singular, plural):
    return "%d %s" % (quantos, singular if quantos == 1 else plural)


def _json_texto(objeto):
    """O texto de todo JSON que esta ferramenta grava: o de comum.json_texto, com cada metade solta de par
    substituto (o código de um emoji escrito pela metade) escrita como \\uXXXX.

    A edição nova nunca traz essa metade (_confere_gravacao recusa). Ela só chega de arquivo mexido à mão: uma
    edição antiga, players.json ou vetores.json. O UTF-8 não tem como gravá-la crua, e sem isto o índice, o
    contexto e os registros paravam em FALHA interna todo dia. Escrita assim, lida de volta dá o mesmo texto:
    o índice segue cópia fiel da edição. O resto não muda: os acentos ficam legíveis."""
    return _RE_SUBSTITUTO.sub(lambda achado: "\\u%04x" % ord(achado.group()), comum.json_texto(objeto))


def _canonico(valor):
    return json.dumps(valor, sort_keys=True, ensure_ascii=True, allow_nan=False)


def _iguais(um, outro):
    """Igualdade pelo texto JSON: em Python 1 == True == 1.0, e num registro isso não pode passar por igual."""
    try:
        return _canonico(um) == _canonico(outro)
    except (TypeError, ValueError, RecursionError):
        return False


def _dia(valor):
    """DD/MM/AAAA de uma data da edição; o que não é data sai como texto, com escape."""
    return comum.dd_mm_aaaa(valor) if comum.data_valida(valor) else md(valor)


def _dia_curto(valor):
    return comum.dd_mm(valor) if comum.data_valida(valor) else md(valor)


def _numero(valor):
    """Número no padrão brasileiro: 78.4 vira "78,4"; 2650.0 vira "2650". O que não é número sai como texto."""
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return md(valor)
    texto = repr(valor)
    if isinstance(valor, float) and texto.endswith(".0"):
        texto = texto[:-2]
    return texto.replace(".", ",")


def _com_sinal(valor):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return md(valor)
    return ("+" if valor > 0 else "") + _numero(valor)


# ---------------------------------------------------------------- escape (CONTRATO, seção 4.5)

def md(valor):
    """Um campo de texto pronto para o .md: numa linha só e com barra antes de cada sinal de Markdown.

    Os dez sinais do CONTRATO (barra invertida, colchetes, parênteses, asterisco, sublinhado, crase,
    cerquilha e barra vertical) e mais o que ainda viraria marca ou link num leitor de Markdown: `<`
    (marca de HTML e endereço entre < >), `@` (e-mail), `://` e `www.` (endereço cru). No começo do
    texto, o que abriria lista, citação ou título leva barra também. Texto de terceiro nunca vira link."""
    texto = _RE_SINAIS.sub(lambda achado: "\\" + achado.group(), _uma_linha(valor))
    texto = _RE_ESQUEMA_CRU.sub(lambda achado: "\\:", texto)
    texto = _RE_WWW.sub(lambda achado: achado.group(1) + "\\.", texto)
    if texto and texto[0] in "-+>=~":
        return "\\" + texto
    numero = _RE_NUMERO_NO_COMECO.match(texto)
    if numero:
        return numero.group(1) + "\\." + texto[numero.end():]
    return texto


def cod(valor):
    """Um id ou código (p1, energia.3, usd_brl) em letra de máquina. O que não tem forma de id sai como texto."""
    return "`%s`" % valor if isinstance(valor, str) and _RE_CODIGO.fullmatch(valor) else md(valor)


def _url_serve(valor):
    return comum.url_valida(valor) and not _RE_FORA_DA_URL.search(valor)


def md_url(valor):
    """Só campo `url` vira endereço, e aparece por extenso. Endereço que não serve sai como texto, com aviso."""
    if _url_serve(valor):
        return "<%s>" % valor.replace("<", "%3C").replace(">", "%3E")
    return "%s (endereço inválido)" % md(valor)


def _linha_do_feed(valor):
    """Um texto da edição numa linha só, para o feed. O que o XML não aceita vira espaço antes de juntar os
    espaços: assim um caractere proibido entre duas palavras não deixa três espaços no lugar de um."""
    return _uma_linha(_RE_FORA_DO_XML.sub(" ", _como_texto(valor)))


def _xml(valor, atributo=False):
    """Texto escapado para o feed. O que o XML não aceita vira espaço."""
    texto = _RE_FORA_DO_XML.sub(" ", _como_texto(valor))
    texto = texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return texto.replace('"', "&quot;") if atributo else texto


# ---------------------------------------------------------------- nomes para o leitor

class _Nomes(object):
    """Os nomes que o texto mostra, tirados da régua, do mapa e de players.json. O que não se acha sai pelo
    id: veículo que saiu do mapa e dado que não deu para ler não derrubam o texto de uma edição antiga."""

    def __init__(self, dados, edicao):
        regua = _objeto(dados.bruto.get("regua"))
        self.dados = dados
        self.partidos = _por_id(regua.get("partidos"))
        self.dominios = _por_id(regua.get("dominios"))
        self.temas = _por_id(regua.get("temas"))
        self.tipos = _por_id(regua.get("tipos"))
        self.times = _por_id(regua.get("times"))
        self.forcas = dict((f["forca"], f.get("nome")) for f in _objetos(regua.get("forcas"))
                           if _e_inteiro(f.get("forca")))
        self.novos = _por_id(edicao.get("novos_players"))
        self.indicadores = _por_id(edicao.get("indicadores"))
        self.principais = set(_por_id(edicao.get("principais")))
        self.itens = self.principais | set(_por_id(edicao.get("radar")))
        self.data = edicao.get("data")
        self.primeira = False  # sem edição anterior: quem monta o texto acerta

    def _nome(self, tabela, identificador):
        ficha = tabela.get(identificador) if isinstance(identificador, str) else None
        nome = ficha.get("nome") if ficha else None
        return md(nome) if isinstance(nome, str) and nome.strip() else cod(identificador)

    def partido(self, identificador):
        return self._nome(self.partidos, identificador)

    def dominio(self, identificador):
        return self._nome(self.dominios, identificador)

    def tipo(self, identificador):
        return self._nome(self.tipos, identificador)

    def time(self, identificador):
        return self._nome(self.times, identificador)

    def tema(self, identificador):
        return "Ordem mundial" if identificador == "ordem" else self._nome(self.temas, identificador)

    def veiculo(self, identificador):
        return self._nome(self.dados.mapa, identificador)

    def player(self, identificador):
        """Player (o novo do dia vale), ou partido; senão, o id."""
        for tabela in (self.novos, self.dados.players, self.partidos):
            if isinstance(identificador, str) and identificador in tabela:
                return self._nome(tabela, identificador)
        return cod(identificador)

    def indicador(self, identificador):
        """O nome do indicador, como está na edição; se ela não o traz, como está no catálogo."""
        na_edicao = isinstance(identificador, str) and identificador in self.indicadores
        return self._nome(self.indicadores if na_edicao else self.dados.indicador, identificador)

    def polo(self, tema, sentido):
        """O texto do polo para onde o ato empurra (o campo azul ou vermelho do tema, na régua)."""
        ficha = self.temas.get(tema) if isinstance(tema, str) else None
        texto = ficha.get(sentido) if ficha and isinstance(sentido, str) else None
        return md(texto) if isinstance(texto, str) and texto.strip() else "polo %s" % md(sentido)

    def rotulo(self, nivel):
        rotulo = self.dados.rotulos.get(nivel) if _e_inteiro(nivel) else None
        return md(rotulo) if isinstance(rotulo, str) else ""

    def item(self, identificador):
        """"principal 1" ou "radar 4", como o site chama um item desta edição; None se não é item dela."""
        if not isinstance(identificador, str) or identificador not in self.itens:
            return None
        return "%s %s" % ("principal" if identificador in self.principais else "radar", md(identificador[1:]))


def _dominio_curto(identificador):
    return _DOMINIOS_CURTOS.get(identificador, _uma_linha(identificador)) if isinstance(identificador, str) else "?"


def _rotulo(dados, nivel):
    """" ATENÇÃO" para o nível 2, com o espaço na frente; texto vazio se a régua não traz o rótulo."""
    rotulo = dados.rotulos.get(nivel) if _e_inteiro(nivel) else None
    return " " + _uma_linha(rotulo) if isinstance(rotulo, str) and rotulo.strip() else ""


def _nivel_em_texto(dados, edicao):
    """"nível 2 ATENÇÃO (energia 2, alimentos 1, cambio 2, suprimentos 1, conflito 1)", da edição completa.

    Os domínios saem pelo id, sem acento: é linha de máquina, como os ids do contexto.json (CONTRATO,
    seção 4.2, passo 8). O nome com acento fica no texto do .md."""
    alerta = _objeto(edicao.get("alerta"))
    dominios = ", ".join("%s %s" % (_uma_linha(d.get("id")), _uma_linha(d.get("nivel")))
                         for d in _objetos(alerta.get("dominios")))
    return "nível %s%s (%s)" % (_uma_linha(alerta.get("nivel")), _rotulo(dados, alerta.get("nivel")), dominios)


# ---------------------------------------------------------------- o texto da edição (.md)

def texto_da_edicao(edicao, dados, historico):
    """O conteúdo de edicoes/DIA.md (CONTRATO, seção 4.5): a edição em texto, na ordem do site.

    Todo campo de texto passa pelo md(): nada do que o agente escreveu vira marca nem link. Só os campos
    `url` viram endereço, por extenso. `historico` diz qual é a edição anterior, para a linha do que mudou.
    Edição torta não dá exceção: o que não dá para ler sai como texto, ou não sai."""
    edicao = _objeto(edicao)
    nomes = _Nomes(dados, edicao)
    blocos = []

    def bloco(*linhas):
        blocos.append("\n".join(linhas))

    data = edicao.get("data")
    alerta = _objeto(edicao.get("alerta"))
    # Sem edição anterior não houve medida de tendência: o "estável" que a regra R14 grava nesse caso não sai,
    # como no site; a linha "Primeira edição: sem comparação." explica.
    nomes.primeira = historico is None or not comum.data_valida(data) or historico.anterior(data) is None
    if edicao.get("exemplo") is True:
        bloco(LINHA_DE_EXEMPLO)
    bloco("# INFOCENARIUM · %s" % _dia(data))
    carimbo = _ESTADOS.get(edicao.get("estado")) if isinstance(edicao.get("estado"), str) else None
    carimbo = carimbo or "Edição %s" % md(edicao.get("estado"))
    if comum.data_hora_valida(edicao.get("gerada_em")):
        instante = comum.le_data_hora(edicao["gerada_em"]) - timedelta(hours=3)
        carimbo += " · gerada em %02d/%02d/%04d às %02dh%02d (hora de Brasília)" % (
            instante.day, instante.month, instante.year, instante.hour, instante.minute)
    bloco(carimbo)
    geral = [parte for parte in ("Nível %s" % _numero(alerta.get("nivel")), nomes.rotulo(alerta.get("nivel")),
                                 _tendencia(nomes, alerta.get("tendencia"))) if parte]
    bloco("**%s**" % " · ".join(geral))
    bloco(_o_que_mudou(alerta, data, historico, edicao.get("estado") == "falha"))
    bloco(md(edicao.get("resumo")))
    bloco("**Motivo do nível:** %s" % md(alerta.get("motivo")))

    bloco("## Domínios")
    for dominio in _objetos(alerta.get("dominios")):
        _md_dominio(bloco, nomes, dominio)

    bloco("## Indicadores")
    indicadores = _objetos(edicao.get("indicadores"))
    if indicadores:
        bloco(*["- " + _md_indicador(indicador) for indicador in indicadores])
    else:
        bloco("Nenhum indicador nesta edição.")

    for titulo, chave, principal in (("## Principais", "principais", True), ("## Radar", "radar", False)):
        bloco(titulo)
        itens = _objetos(edicao.get(chave))
        if not itens:
            bloco("Sem itens: a rotina não fechou a edição deste dia." if edicao.get("estado") == "falha"
                  else "Nenhum item.")
        elif _mapa_em_rascunho(dados):
            # O lado de cada veículo é palpite enquanto o dono não revisa o mapa: a nota do site, logo abaixo
            # do título da seção. Segue o mapa de hoje, como o site: some dos textos no refaz depois da revisão.
            bloco(NOTA_DE_RASCUNHO)
        for item in itens:
            _md_item(bloco, nomes, item, principal)

    bloco("## Placar do dia")
    placar = _objetos(edicao.get("placar_do_dia"))
    if placar:
        # A narrativa só aparece quando não é 0, como no site.
        bloco(*["- %s: saldo %s%s · %s"
                % (nomes.partido(linha.get("partido")), _com_sinal(linha.get("saldo")),
                   "" if _e_inteiro(linha.get("narrativa")) and linha["narrativa"] == 0
                   else " · narrativa %s" % _com_sinal(linha.get("narrativa")), md(linha.get("frase")))
                for linha in placar])
    else:
        bloco("Nenhum partido ganhou ou perdeu hoje.")

    respostas = _objetos(edicao.get("respostas"))
    if respostas:
        bloco("## Respostas")
        bloco(*["- " + _md_resposta(resposta) for resposta in respostas])
    novos = _objetos(edicao.get("novos_players"))
    if novos:
        bloco("## Players novos")
        for novo in novos:
            bloco(*_md_player(nomes, novo))
    erratas = _objetos(edicao.get("errata"))
    if erratas:
        bloco("## Errata")
        bloco(*["- " + _md_errata(errata) for errata in erratas])

    bloco("## Bastidores")
    bloco(*_md_bastidores(_objeto(edicao.get("bastidores")), edicao.get("estado") == "falha"))
    return "\n\n".join(blocos) + "\n"


def _mapa_em_rascunho(dados):
    """O mapa de veículos foi lido e o dono ainda não o revisou (`revisado_em` nulo): a regra do site."""
    return isinstance(dados.bruto.get("veiculos"), dict) and not dados.revisado_em


def _tendencia(nomes, valor):
    """A palavra da tendência; vazia no "estável" de quem não tem edição anterior (não houve medida)."""
    return "" if nomes.primeira and valor == "estavel" else _de_lista(_TENDENCIAS, valor)


def _de_lista(rotulos, valor):
    """O rótulo de um valor de lista fechada; valor fora da lista sai como texto, com escape."""
    rotulo = rotulos.get(valor) if isinstance(valor, str) else None
    return rotulo or md(valor)


def _o_que_mudou(alerta, data, historico, falha=False):
    """A linha do que mudou desde a edição anterior: "Desde 18/11: energia 2 → 3." (CONTRATO, seção 4.5).

    Na edição de falha ninguém mediu nada: a linha diz que os níveis são repetidos, como a nota do site."""
    anterior = historico.anterior(data) if historico is not None and comum.data_valida(data) else None
    if anterior is None:
        return "Níveis sem base: ainda não houve edição." if falha else "Primeira edição: sem comparação."
    if falha:
        return "Níveis repetidos de %s." % comum.dd_mm(anterior.data)
    mudancas = []
    for dominio in _objetos(alerta.get("dominios")):
        identificador, nivel = dominio.get("id"), dominio.get("nivel")
        antes = anterior.niveis.get(identificador, 1) if isinstance(identificador, str) else None
        if _e_inteiro(nivel) and antes is not None and antes != nivel:
            mudancas.append("%s %d → %d" % (md(_dominio_curto(identificador)), antes, nivel))
    if not mudancas:
        return "Desde %s: nenhum nível mudou." % comum.dd_mm(anterior.data)
    return "Desde %s: %s." % (comum.dd_mm(anterior.data), ", ".join(mudancas))


def _md_dominio(bloco, nomes, dominio):
    titulo = " · ".join(parte for parte in ("### " + nomes.dominio(dominio.get("id")),
                                            "nível %s" % _numero(dominio.get("nivel")),
                                            _tendencia(nomes, dominio.get("tendencia"))) if parte)
    sem_preco = dominio.get("sem_preco")
    if isinstance(sem_preco, list) and sem_preco:
        # A frase do CONTRATO, seção 4.5, ao lado do nível, como o site mostra: com o nome de cada indicador.
        titulo += " · sem dado de preço de: %s" % ", ".join(nomes.indicador(i) for i in sem_preco)
    bloco(titulo)
    bloco("Neste nível desde %s." % _dia(dominio.get("desde")))
    gatilhos = _objetos(dominio.get("gatilhos"))
    if gatilhos:
        bloco("**Gatilhos de hoje:**")
        bloco(*["- " + _md_gatilho(nomes, gatilho) for gatilho in gatilhos])
    elif _e_inteiro(dominio.get("nivel")) and dominio["nivel"] > 1:
        bloco("Mantido desde %s. %s" % (_dia_curto(dominio.get("desde")), SEM_GATILHO_NOVO))
    else:
        bloco("Nenhum gatilho hoje.")
    bloco("**Leitura:** %s" % md(dominio.get("leitura")))
    bloco("**Vigiar:** %s" % md(dominio.get("vigiar")))


def _md_gatilho(nomes, gatilho):
    """Na ordem do site: o código do critério, o texto, as etiquetas e para onde a prova leva ("ver principal 1",
    "ver radar 4", "ver indicador: Petróleo Brent"); `ref` que não é desta edição sai pelo id."""
    ref = gatilho.get("ref")
    if nomes.item(ref) is not None:
        prova = "ver " + nomes.item(ref)
    elif isinstance(ref, str) and ref in nomes.indicadores:
        prova = "ver indicador: %s" % nomes.indicador(ref)
    else:
        prova = cod(ref)
    partes = [cod(gatilho.get("criterio")), md(gatilho.get("texto"))]
    if gatilho.get("excecao") is True:
        partes.append("EXCEÇÃO")
    if gatilho.get("alivio") is True:
        partes.append("ALÍVIO")
    partes.append(prova)
    return " · ".join(partes)


def _md_indicador(indicador):
    fonte = _objeto(indicador.get("fonte"))
    partes = []
    if indicador.get("valor") is None:
        partes.append("%s: sem dado" % md(indicador.get("nome")))
    else:
        partes.append("%s: %s %s" % (md(indicador.get("nome")), _numero(indicador.get("valor")),
                                     md(indicador.get("unidade"))))
        if indicador.get("variacao_pct") is not None:
            partes.append("no dia %s%%" % _com_sinal(indicador["variacao_pct"]))
        if indicador.get("variacao_7d_pct") is not None:
            partes.append("em 7 dias %s%%" % _com_sinal(indicador["variacao_7d_pct"]))
        if indicador.get("data") is not None:
            partes.append("cotação de %s%s" % (_dia(indicador["data"]),
                                               " (defasada)" if indicador.get("defasado") is True else ""))
    # Sem valor, a fonte é a primeira do catálogo (ESQUEMA, seção 3): a prevista, e não a de um número que veio.
    rotulo = "fonte prevista" if indicador.get("valor") is None else "fonte"
    partes.append("%s: %s %s" % (rotulo, md(fonte.get("nome")), md_url(fonte.get("url"))))
    return " · ".join(partes)


def _md_ataque(nomes, ataque):
    alvo = ataque.get("alvo")
    if alvo == "nenhum":
        alvo_em_texto = "sem alvo"
    elif alvo == "outro":
        alvo_em_texto = "alvo: %s" % md(ataque.get("alvo_nome"))
    else:
        alvo_em_texto = "alvo: %s" % nomes.player(alvo)
    partes = [nomes.veiculo(ataque.get("veiculo")), nomes.partido(ataque.get("lado")), alvo_em_texto,
              md(ataque.get("enquadramento"))]
    if "omite" in ataque:
        # O que o veículo deixou de fora é leitura do INFOCENARIUM, e não fato sobre o veículo: a ressalva do site.
        partes.append("Deixou de fora: %s Segundo a leitura do INFOCENARIUM em %s."
                      % (md(ataque["omite"]), _dia_curto(nomes.data)))
    partes.append(md_url(ataque.get("url")))
    return " · ".join(partes)


def _md_fonte(nomes, fonte, lados_do_item):
    """`lados_do_item` é {veículo: lado gravado no ataque} do mesmo item. O lado gravado vale mais que o do mapa
    de hoje: depois de o dono mudar o mapa, o refaz não põe dois partidos para o mesmo veículo no mesmo item."""
    veiculo = fonte.get("veiculo")
    if veiculo == "outro":
        partes = ["%s (fora do mapa)" % md(fonte.get("nome"))]
    else:
        partes = [nomes.veiculo(veiculo)]
        lado = lados_do_item.get(veiculo) if isinstance(veiculo, str) else None
        if lado is None:
            lado = valida.lado_do_veiculo(nomes.dados, veiculo)
        if lado is not None:
            partes.append(nomes.partido(lado))
    partes += [md(fonte.get("titulo")), _dia(fonte.get("publicado_em"))]
    if fonte.get("primaria") is True:
        partes.append("fonte primária")
    partes.append(md_url(fonte.get("url")))
    return " · ".join(partes)


def _md_vetor(nomes, vetor):
    de = nomes.dados.partido_do_player(vetor.get("player"))
    quem = nomes.player(vetor.get("player")) + (" (%s)" % nomes.partido(de) if de else "")
    return " · ".join(["%s → %s" % (quem, nomes.partido(vetor.get("para"))),
                       "força %s" % _numero(vetor.get("forca")), "tema: %s" % nomes.tema(vetor.get("tema")),
                       md(vetor.get("porque")), "prova: %s" % md_url(vetor.get("url"))])


def _md_placar(nomes, linha):
    forca = linha.get("forca")
    nome_da_forca = nomes.forcas.get(forca) if _e_inteiro(forca) else None
    return "%s: %s · força %s%s · %s · %s" % (
        nomes.partido(linha.get("partido")), md(linha.get("efeito")), _numero(forca),
        " (%s)" % md(nome_da_forca) if isinstance(nome_da_forca, str) else "",
        _de_lista(_EVIDENCIAS, linha.get("evidencia")), md(linha.get("porque")))


def _md_item(bloco, nomes, item, principal):
    """Uma principal ou um item do radar, na ordem do CONTRATO, seção 4.5."""
    bloco("### %s · %s" % (md(item.get("id")), md(item.get("titulo"))))
    marcas = [_de_lista(_CATEGORIAS, item.get("categoria")),
              "confiança %s" % _de_lista(_CONFIANCAS, item.get("confianca"))]
    dominios = item.get("dominios")
    if isinstance(dominios, list) and dominios:
        marcas.append("domínios: %s" % ", ".join(nomes.dominio(d) for d in dominios))
    linhas = [" · ".join(marcas)]
    if "continuacao_de" in item:
        lido = _RE_CONTINUACAO.fullmatch(item["continuacao_de"]) if isinstance(item["continuacao_de"], str) else None
        if lido and comum.data_valida(lido.group(1)):
            linhas.append("Continuação de %s, item %s." % (_dia(lido.group(1)), cod(lido.group(2))))
        else:
            linhas.append("Continuação de %s." % md(item["continuacao_de"]))
    if item.get("conflito_de_interesse") is True:
        linhas.append(AVISO_DE_CONFLITO)
        linhas.append(TETO_DO_CONFLITO)
        vinculo = _vinculo_do_conflito(nomes, item)
        if vinculo:
            linhas.append(vinculo)
    bloco(*linhas)

    bloco("**O que aconteceu:** %s" % md(item.get("fato")))
    nao_confirmado = item.get("nao_confirmado")
    if isinstance(nao_confirmado, list) and nao_confirmado:
        bloco("**Não confirmado:**")
        bloco(*["- " + md(texto) for texto in nao_confirmado])
    ataques = _objetos(item.get("ataques")) + ([item["ataque"]] if isinstance(item.get("ataque"), dict) else [])
    if ataques:
        bloco("**Quem atirou:**")
        bloco(*["- " + _md_ataque(nomes, ataque) for ataque in ataques])
    if principal:
        bloco("**O que está realmente acontecendo:** %s" % md(item.get("realmente")))
        na_pratica = item.get("na_pratica")
        if isinstance(na_pratica, list) and na_pratica:
            bloco("**Na prática:**")
            bloco(*["- " + md(texto) for texto in na_pratica])
        if "no_brasil" in item:
            bloco("**No Brasil:** %s" % md(item["no_brasil"]))
    if isinstance(item.get("eixo"), dict):
        eixo = item["eixo"]
        bloco("**O ato na régua:** %s · empurra para: %s · ato: %s"
              % (nomes.tema(eixo.get("tema")), nomes.polo(eixo.get("tema"), eixo.get("sentido")),
                 md(eixo.get("porque"))))
    placar = _objetos(item.get("placar"))
    if placar:
        bloco("**Quem ganha e quem perde:**")
        bloco(*["- " + _md_placar(nomes, linha) for linha in placar])
    elif "sem_placar" in item:
        bloco("**Sem placar:** %s" % md(item["sem_placar"]))
    vetores = _objetos(item.get("vetores"))
    if vetores:
        bloco("**Vetores de mudança:**")
        bloco(*["- " + _md_vetor(nomes, vetor) for vetor in vetores])
    vigiar = item.get("vigiar")
    if principal and isinstance(vigiar, list) and vigiar:
        bloco("**Vigiar:**")
        bloco(*["- " + md(texto) for texto in vigiar])
    fontes = _objetos(item.get("fontes"))
    if fontes:
        lados = {}
        for ataque in ataques:
            if isinstance(ataque.get("veiculo"), str) and isinstance(ataque.get("lado"), str):
                lados.setdefault(ataque["veiculo"], ataque["lado"])
        bloco("**Fontes:**")
        bloco(*["- " + _md_fonte(nomes, fonte, lados) for fonte in fontes])


def _vinculo_do_conflito(nomes, item):
    """A frase que nomeia o vínculo do item com a lista de conflito da régua, quando a régua o conhece; senão,
    None. É o texto e a regra do site (ESPEC-SITE, seção 8.3): "Este item envolve nomes da lista de conflito da
    régua: NOMES.", na ordem da lista; primeiro o player de `conflito.players` citado como alvo ou em vetor (pelo
    nome da ficha), depois o termo de `conflito.termos` escrito em algum texto do item, palavra inteira, como a
    regra R19 lê; termo que já está no nome de um player listado não se repete. O caso a (notícia de IA) o aviso
    já diz; o caso d (fonte de veículo ligado à Anthropic) vem do mapa, não da lista, e o site também não o nomeia.
    Como a nota de rascunho, segue a régua de hoje: o refaz põe o vínculo que o dono acrescentar depois."""
    dados = nomes.dados
    regua = dados.bruto.get("regua") if isinstance(dados.bruto, dict) else None
    conflito = regua.get("conflito") if isinstance(regua, dict) else None
    if not isinstance(conflito, dict):
        return None
    lista_players = conflito.get("players") if isinstance(conflito.get("players"), list) else []
    lista_termos = conflito.get("termos") if isinstance(conflito.get("termos"), list) else []
    citados = [ataque.get("alvo") for ataque, _ in valida._ataques_do_item(item)]
    citados += [vetor.get("player") for vetor in _objetos(item.get("vetores"))]
    brutos = []   # os nomes como estão na ficha (para ver se o termo já está dentro de um deles)
    for identificador in lista_players:
        if isinstance(identificador, str) and identificador in citados:
            ficha = dados.players.get(identificador)
            nome = ficha.get("nome") if isinstance(ficha, dict) else None
            nome = nome if isinstance(nome, str) and nome.strip() else identificador
            if nome not in brutos:
                brutos.append(nome)
    achados = [md(nome) for nome in brutos]
    textos = list(valida._textos_do_item(item))
    for termo in lista_termos:
        if not isinstance(termo, str) or not termo.strip() or any(termo in nome for nome in brutos):
            continue
        forma = re.compile(r"(?<![\w-])%s(?!\w)" % re.escape(termo))
        if any(forma.search(texto) for texto in textos):
            achados.append(md(termo))
    if not achados:
        return None
    return "Este item envolve nomes da lista de conflito da régua: %s." % ", ".join(achados)


def _md_resposta(resposta):
    item = resposta.get("item")
    # "principal 1", como o site; o que não tem a forma de principal sai pelo id.
    quem = ("principal %s" % item[1:] if isinstance(item, str) and _RE_PRINCIPAL.fullmatch(item)
            else "item %s" % cod(item))
    partes = ["Pergunta de %s, %s: %s" % (_dia(resposta.get("edicao")), quem, md(resposta.get("pergunta"))),
              "Resposta: %s" % _de_lista(_RESPOSTAS, resposta.get("resposta")), md(resposta.get("texto"))]
    if "url" in resposta:
        partes.append("fonte: %s" % md_url(resposta["url"]))
    return " · ".join(partes)


def _md_player(nomes, novo):
    time = nomes.time(novo.get("time")) + (" (discutível)" if novo.get("time_discutivel") is True else "")
    linhas = ["- **%s** (%s) · tipo: %s · partido: %s · time: %s"
              % (md(novo.get("nome")), cod(novo.get("id")), nomes.tipo(novo.get("tipo")),
                 nomes.partido(novo.get("partido")), time)]
    dna = novo.get("dna")
    if isinstance(dna, dict):
        linhas.append("  - DNA: %s" % " · ".join("%s %s" % (nomes.tema(tema), md(letra))
                                                 for tema, letra in dna.items()))
    fontes = novo.get("dna_fontes")
    if isinstance(fontes, dict) and fontes:
        linhas.append("  - Fontes das posições: %s"
                      % " · ".join("%s %s" % (nomes.tema(tema), md_url(url)) for tema, url in fontes.items()))
    duvidas = novo.get("duvidas")
    if isinstance(duvidas, list) and duvidas:
        linhas.append("  - Posições em dúvida: %s" % ", ".join(nomes.tema(tema) for tema in duvidas))
    linhas.append("  - Quem é: %s" % md(novo.get("nota")))
    linhas.append("  - Por que entrou: %s" % md(novo.get("justificativa")))
    linhas.append("  - Fonte: %s" % md_url(novo.get("url")))
    return linhas


def _md_errata(errata):
    onde = "Edição de %s, %s" % (_dia(errata.get("edicao")),
                                 "item %s" % cod(errata["item"]) if "item" in errata else "inteira")
    partes = [onde, "Estava errado: %s" % md(errata.get("erro")), "O certo: %s" % md(errata.get("correcao"))]
    if "url" in errata:
        partes.append("fonte: %s" % md_url(errata["url"]))
    if "anula_vetor" in errata:
        partes.append("anula o vetor %s" % cod(errata["anula_vetor"]))
    return " · ".join(partes)


def _md_bastidores(bastidores, falha=False):
    """Na edição de falha ninguém mediu nada: sem a linha do modo e sem os contadores, que o publica.py grava
    em 0 (CONTRATO, seção 4.3) e que o leitor tomaria por fato. Ficam os limites, como no site."""
    contas = (("Veículos consultados", "veiculos_consultados"), ("feeds lidos", "feeds_ok"),
              ("feeds que falharam", "feeds_falhos"), ("páginas lidas", "paginas_lidas"), ("buscas", "buscas"),
              ("minutos de trabalho", "minutos"),
              ("páginas descartadas por trazer ordens ao agente", "injecoes_ignoradas"))
    linhas = [] if falha else [
        "- Modo: %s" % _de_lista(_MODOS, bastidores.get("modo")),
        "- " + " · ".join("%s: %s" % (rotulo, _numero(bastidores.get(chave))) for rotulo, chave in contas)]
    linhas.append("- O que não deu para conferir: %s" % md(bastidores.get("limites")))
    for candidato in _objetos(bastidores.get("candidatos")):
        linhas.append("- Ator sem ficha na régua: %s (%s): %s"
                      % (md(candidato.get("nome")), cod(candidato.get("id")), md(candidato.get("motivo"))))
    sugeridos = bastidores.get("veiculos_sugeridos")
    for sugerido in (sugeridos if isinstance(sugeridos, list) else ()):
        linhas.append("- Veículo que fez falta: %s" % md(sugerido))
    return linhas


# ---------------------------------------------------------------- feed.xml (CONTRATO, seção 4.5)

def base_valida(texto):
    """O endereço base do feed, já com a barra do fim, ou None se o texto não serve.

    Vale endereço http ou https, ou caminho relativo (./). Sem espaço, sem `#`, sem `?` e sem aspas."""
    if not isinstance(texto, str):
        return None
    texto = texto.strip()
    if not texto or len(texto) > 500 or _RE_FORA_DA_BASE.search(texto) or _RE_SUBSTITUTO.search(texto):
        return None
    if _RE_ESQUEMA.match(texto) and not comum.url_valida(texto):
        return None
    return texto if texto.endswith("/") else texto + "/"


def base_do_remoto(remoto):
    """`…/DONO/REPO` vira `https://DONO.github.io/REPO/` (CONTRATO, seção 4.5). None se não tem essa forma.

    Remoto que é pasta desta máquina não tem dono nem site: fica de fora."""
    remoto = remoto.strip() if isinstance(remoto, str) else ""
    if not remoto or remoto.startswith(("/", ".", "~", "file:")) or _RE_JUNTA.search(remoto):
        return None
    lido = _RE_REMOTO.search(remoto)
    if not lido or lido.group(2) in (".", ".."):
        return None
    return base_valida("https://%s.github.io/%s/" % (lido.group(1), lido.group(2)))


def _base_do_feed(raiz):
    """O endereço base que já está no feed.xml da raiz (o <id> do feed), ou None."""
    caminho = os.path.join(raiz, "feed.xml")
    try:
        estado = os.lstat(caminho)
        if not stat.S_ISREG(estado.st_mode) or estado.st_size > valida.LIMITE_ARQUIVO:
            return None
        with open(caminho, "rb") as arquivo:
            bruto = arquivo.read()
    except OSError:
        return None
    # Só se abre o XML que passa na conferência: sem DOCTYPE nem ENTITY não há o que expandir.
    if valida.separa(valida.confere_feed(bruto))[0]:
        return None
    try:
        return base_valida(ET.fromstring(bruto).findtext("{%s}id" % valida.NS_ATOM))
    except (ET.ParseError, ValueError, RecursionError, LookupError):
        return None


def endereco_base(raiz, informado=None):
    """(endereço, de onde veio), na ordem do CONTRATO, seção 4.5: --url-base; o que já está no feed.xml;
    o derivado de `git remote get-url origin`; por último ./"""
    if informado is not None:
        return informado, "--url-base"
    do_feed = _base_do_feed(raiz)
    if do_feed is not None and not _RE_ESQUEMA.match(do_feed):
        # Relativo vale (os links funcionam), mas o Atom pede id absoluto: a linha diz como trocar.
        return do_feed, "o do feed.xml que já existe; relativo: para o feed levar o endereço do site, use --url-base"
    if do_feed is not None:
        return do_feed, "o do feed.xml que já existe"
    git, _ = valida.abre_git(raiz)
    if git is not None:
        codigo, saida, _ = git.roda(["remote", "get-url", "origin"])
        do_git = base_do_remoto(saida.decode("utf-8", "replace")) if codigo == 0 else None
        if do_git is not None:
            return do_git, "tirado do remoto origin do git"
    return BASE_PADRAO, "o padrão; para o feed levar o endereço do site, use --url-base"


def texto_do_feed(edicoes, dados, base):
    """O conteúdo de feed.xml: Atom 1.0, só com elementos do Atom, texto escapado, sem DOCTYPE e sem
    instrução além da declaração do começo. Uma entrada por edição, as 30 mais novas, sem as de exemplo."""
    reais = dict((d, e) for d, e in edicoes.items() if isinstance(e, dict) and e.get("exemplo") is not True)
    entradas, carimbos = [], []
    for data in sorted(reais, reverse=True)[:ENTRADAS_DO_FEED]:
        edicao = reais[data]
        alerta = _objeto(edicao.get("alerta"))
        gerada = edicao["gerada_em"] if comum.data_hora_valida(edicao.get("gerada_em")) else data + "T00:00:00Z"
        carimbos.append(gerada)
        if edicao.get("estado") == "falha":
            titulo = "INFOCENARIUM %s · sem edição" % comum.dd_mm_aaaa(data)
        else:
            titulo = "INFOCENARIUM %s · nível %s%s" % (comum.dd_mm_aaaa(data), _linha_do_feed(alerta.get("nivel")),
                                               _rotulo(dados, alerta.get("nivel")))
        conteudo = "\n\n".join("%d. %s\n%s" % (posicao, _linha_do_feed(item.get("titulo")),
                                               _linha_do_feed(item.get("fato")))
                               for posicao, item in enumerate(_objetos(edicao.get("principais")), 1))
        endereco = _xml("%s#/edicao/%s" % (base, data), atributo=True)
        entradas += [
            "  <entry>",
            "    <title>%s</title>" % _xml(titulo),
            "    <id>%s</id>" % endereco,
            '    <link href="%s"/>' % endereco,
            "    <updated>%s</updated>" % gerada,
            '    <summary type="text">%s</summary>' % _xml(_linha_do_feed(edicao.get("resumo"))),
            # Edição sem principal (a de falha) leva o resumo: entrada de feed não fica sem conteúdo.
            '    <content type="text">%s</content>' % _xml(conteudo or _linha_do_feed(edicao.get("resumo"))),
            "  </entry>"]
    if not carimbos:
        # Feed sem entrada (nenhuma edição, ou só a de exemplo): a de exemplo não conta para o updated, e o
        # relógio também não, porque a mesma entrada dá os mesmos bytes. Fica uma data fixa.
        carimbos = [UPDATED_SEM_ENTRADA]
    linhas = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<feed xmlns="%s">' % valida.NS_ATOM,
        "  <title>%s</title>" % _xml(TITULO_DO_FEED),
        "  <id>%s</id>" % _xml(base, atributo=True),
        '  <link href="%s"/>' % _xml(base, atributo=True),
        '  <link rel="self" type="application/atom+xml" href="%s"/>' % _xml(base + "feed.xml", atributo=True),
        "  <updated>%s</updated>" % max(carimbos),
        "  <author>",
        "    <name>INFOCENARIUM</name>",
        "  </author>"] + entradas + ["</feed>"]
    return "\n".join(linhas) + "\n"


# ---------------------------------------------------------------- contexto (CONTRATO, seção 4.1)

def monta_contexto(dia, dados, edicoes):
    """O objeto de contexto.json: a memória dos dias anteriores, para o agente que escreve a edição de `dia`.

    `edicoes` é {data: edição}. Edição com exemplo: true é ignorada em tudo. Só conta o que é de ANTES de
    `dia`: a edição do próprio dia só aparece em `edicao_do_dia`."""
    reais = dict((d, e) for d, e in edicoes.items() if isinstance(e, dict) and e.get("exemplo") is not True)
    historico = valida.Historico(reais)
    anterior = historico.anterior(dia)
    do_dia = reais.get(dia)
    janela = JANELA_NORMAL if anterior is None or anterior.data == comum.soma_dias(dia, -1) else JANELA_COM_BURACO

    historias = []
    for posicao, resumo in enumerate(historico.antes(dia)):
        if posicao >= EDICOES_DE_HISTORIA:
            break
        for chave in ("principais", "radar"):
            for item in _objetos(resumo.edicao.get(chave)):
                historia = {"edicao": resumo.data, "id": item.get("id"), "titulo": item.get("titulo")}
                if chave == "principais":
                    historia["vigiar"] = _textos(item.get("vigiar"))
                historias.append(historia)

    respondidas = set()
    for data, edicao in reais.items():
        if data < dia:
            for resposta in _objetos(edicao.get("respostas")):
                if isinstance(resposta.get("edicao"), str) and isinstance(resposta.get("item"), str):
                    respondidas.add((resposta["edicao"], resposta["item"]))
    vencendo = []
    for data in sorted(reais):
        idade = comum.dias_entre(data, dia)
        if not 0 < idade <= DIAS_DE_VIGIAR + DIAS_DE_FOLGA_DO_VIGIAR:
            continue
        for item in _objetos(reais[data].get("principais")):
            perguntas = _textos(item.get("vigiar"))
            if not perguntas or not isinstance(item.get("id"), str) or (data, item["id"]) in respondidas:
                continue
            prazo = valida.prazo_do_vigiar(perguntas[0], data)
            # edição com até 30 dias, ou prazo vencido há até 7 dias (edição com até 37)
            if prazo is not None and prazo <= dia and (
                    idade <= DIAS_DE_VIGIAR or comum.dias_entre(prazo, dia) <= DIAS_DE_FOLGA_DO_VIGIAR):
                vencendo.append({"edicao": data, "item": item["id"], "pergunta": perguntas[0], "prazo": prazo})
    vencendo.sort(key=lambda v: (v["prazo"], v["edicao"], v["item"]))

    candidatos = {}
    for data in sorted(reais):  # da mais velha para a mais nova: o nome e o motivo que ficam são os da última
        if not 0 < comum.dias_entre(data, dia) <= DIAS_DE_CANDIDATO:
            continue
        for identificador, candidato in _por_id(_objeto(reais[data].get("bastidores")).get("candidatos")).items():
            ficha = candidatos.setdefault(identificador, {"id": identificador, "nome": None, "edicoes": 0,
                                                          "ultima": None, "motivo": None})
            ficha["edicoes"] += 1
            ficha["nome"], ficha["ultima"], ficha["motivo"] = candidato.get("nome"), data, candidato.get("motivo")
    em_ordem = sorted(candidatos.values(), key=lambda c: c["id"])
    em_ordem.sort(key=lambda c: c["ultima"], reverse=True)
    em_ordem.sort(key=lambda c: c["edicoes"], reverse=True)

    anulados = valida.vetores_anulados(dados)
    vetores = []
    for entrada in dados.vetores:
        data, identificador = entrada.get("data"), entrada.get("id")
        if "anula" in entrada or not comum.data_valida(data) or not 0 < comum.dias_entre(data, dia) <= DIAS_DE_VETOR:
            continue
        if isinstance(identificador, str) and identificador in anulados \
                and (anulados[identificador] is None or anulados[identificador] < dia):
            continue
        vetores.append(dict((chave, entrada.get(chave)) for chave in ("id", "data", "player", "para", "forca")))

    return {
        "dia": dia,
        "janela_horas": janela,
        "edicao_do_dia": ({"estado": do_dia.get("estado"), "gerada_em": do_dia.get("gerada_em")}
                          if do_dia is not None else None),
        "anterior": {"data": anterior.data, "estado": anterior.estado} if anterior is not None else None,
        "alerta_anterior": valida.alerta_anterior(historico, dia, dados.dominios),
        "historias_recentes": historias,
        "vigiar_vencendo": vencendo[:PERGUNTAS_VENCENDO],
        "candidatos": em_ordem,
        "vetores_recentes": vetores,
    }


def texto_do_mapa(dados):
    """O conteúdo de mapa.txt: a legenda e uma linha por veículo, em ordem de id (CONTRATO, seção 4.1)."""
    siglas = dict((identificador, partido.get("sigla"))
                  for identificador, partido in _por_id(_objeto(dados.bruto.get("regua")).get("partidos")).items())
    revisao = ("revisado em %s" % comum.dd_mm_aaaa(dados.revisado_em) if dados.revisado_em
               else "rascunho, sem revisão do dono")
    linhas = ["MAPA · %s · %s · id · partido (? = lado incerto) · fatos · tipo · serve a · site · nome"
              % (_conta(len(dados.mapa), "veículo", "veículos"), revisao)]
    for identificador in sorted(dados.mapa):
        ficha = dados.mapa[identificador]
        sigla = siglas.get(ficha["lado"]) if isinstance(ficha["lado"], str) else None
        sigla = sigla if isinstance(sigla, str) and sigla else (ficha["lado"] or "??")
        # Lado incerto é o que não tem confiança alta nem media: o mesmo corte da regra R03.
        incerto = "" if ficha["lado_confianca"] in ("alta", "media") else "?"
        serve = [alvo for alvo in ficha["serve_a"] if alvo not in dados.partidos]
        partes = [identificador, sigla + incerto, "fatos %s" % (ficha["fatos"] or "?"), ficha["tipo"] or "?",
                  "serve a: %s" % (", ".join(serve) or "—"), ficha["sites"][0] if ficha["sites"] else "—",
                  ficha["nome"] or identificador]
        if identificador in dados.ligados:
            partes.append("LIGADO À ANTHROPIC")
        linhas.append(" · ".join(_uma_linha(parte) for parte in partes))
    return "\n".join(linhas) + "\n"


_FILHOS_DO_MODELO = {
    ("raiz", "alerta"): "alerta", ("alerta", "dominios"): "dominio", ("dominio", "gatilhos"): "gatilho",
    ("raiz", "principais"): "principal", ("raiz", "radar"): "radar", ("principal", "ataques"): "ataque",
    ("radar", "ataque"): "ataque", ("principal", "eixo"): "eixo", ("radar", "eixo"): "eixo",
    ("principal", "placar"): "placar", ("radar", "placar"): "placar", ("principal", "vetores"): "vetor",
    ("radar", "vetores"): "vetor", ("principal", "fontes"): "fonte", ("radar", "fontes"): "fonte",
    ("raiz", "placar_do_dia"): "placar_do_dia", ("raiz", "novos_players"): "novo_player",
    ("raiz", "errata"): "errata", ("raiz", "respostas"): "resposta", ("raiz", "bastidores"): "bastidores",
    ("bastidores", "candidatos"): "candidato",
}


def confere_modelo(texto=MODELO):
    """O modelo.txt diz o mesmo que as tabelas do validador? Devolve as diferenças; lista vazia se bate.

    Tirando as linhas de comentário, o modelo é JSON; traz todo campo que o agente escreve (os de
    valida.ORDEM menos os de valida.CALCULADOS e o `exemplo`), na mesma ordem, e o número entre aspas é o
    tamanho máximo de valida.MAXIMOS."""
    sem_comentario = "\n".join(linha for linha in texto.splitlines() if not linha.strip().startswith("//"))
    try:
        modelo = json.loads(sem_comentario)
    except ValueError as erro:
        return ["tirando os comentários, o modelo não é JSON (%s)" % erro]
    problemas = []

    def anda(objeto, tipo, caminho):
        esperadas = [chave for chave in valida.ORDEM[tipo]
                     if chave not in valida.CALCULADOS.get(tipo, ()) and (tipo, chave) != ("raiz", "exemplo")]
        if list(objeto) != esperadas:
            problemas.append("%s: o modelo traz %s, e as tabelas do validador pedem %s"
                             % (caminho or "raiz", ", ".join(objeto), ", ".join(esperadas)))
        for chave, valor in objeto.items():
            amostra = valor[0] if isinstance(valor, list) and valor else valor
            if isinstance(amostra, str) and amostra.isdigit() and int(amostra) != valida.MAXIMOS.get((tipo, chave)):
                problemas.append("%s.%s: o modelo diz %s, e o validador aceita até %s"
                                 % (caminho or "raiz", chave, amostra, valida.MAXIMOS.get((tipo, chave))))
            filho = _FILHOS_DO_MODELO.get((tipo, chave))
            if filho and isinstance(amostra, dict):
                anda(amostra, filho, "%s.%s" % (caminho, chave) if caminho else chave)

    if isinstance(modelo, dict):
        anda(modelo, "raiz", "")
    else:
        problemas.append("o modelo deveria ser um objeto")
    return problemas


# ---------------------------------------------------------------- ler o repositório e a pasta de trabalho

def _barra(rep, saida, fatais, livre=None):
    """Para com FALHA se algo que a ferramenta precisa ler não serve de base.

    `fatais` são os começos de caminho que contam (o resto vira aviso). O índice nunca conta: ele é refeito.
    `livre` é o dia cujo arquivo de edição pode ser regravado: se ele está quebrado, não atrapalha."""
    do_dia = "edicoes/%s.json" % livre if livre else None
    achados = [a for a in rep.problemas
               if a.caminho.split(":")[0] != "edicoes/indice.json" and a.caminho != do_dia]
    for data in sorted(rep.edicoes):
        if not isinstance(rep.edicoes[data], dict) and "edicoes/%s.json" % data != do_dia:
            achados.append(valida.Achado(valida.ERRO, "ARQUIVO", "edicoes/%s.json" % data,
                                         "deveria ser um objeto, e não é. Edição publicada não se edita à mão: "
                                         "recupere o arquivo do git."))
    graves = [a for a in achados if a.caminho.startswith(fatais)]
    for achado in achados:
        if achado not in graves:
            saida.linha("aviso: %s: %s" % (achado.caminho, achado.mensagem))
    if not graves:
        return
    for achado in graves:
        saida.linha(achado.linha())
    arquivos = sorted(set(a.caminho.split(":")[0] for a in graves))
    if len(arquivos) == 1:
        raise comum.Falha("%s: não deu para ler, ou não serve de base (linha acima). Conserte o arquivo, ou "
                          "recupere-o do git" % arquivos[0])
    raise comum.Falha("%d arquivos não servem de base (linhas acima): %s. Conserte, ou recupere do git"
                      % (len(arquivos), ", ".join(arquivos)))


def _edicoes_legiveis(rep, mais=None):
    """{data: edição} das edições que são objeto; `mais` entra por cima (a edição que está sendo publicada)."""
    edicoes = dict((data, edicao) for data, edicao in rep.edicoes.items() if isinstance(edicao, dict))
    edicoes.update(mais or {})
    return edicoes


def _le_rascunho(trabalho):
    """O objeto de P/rascunho.json (CONTRATO, seção 4.2, passo 1). O erro diz a linha, a coluna e o conserto."""
    caminho = os.path.join(trabalho, "rascunho.json")
    try:
        estado = os.lstat(caminho)
    except OSError:
        raise comum.Falha("rascunho.json: o arquivo não existe em %s. Escreva o rascunho na forma do modelo.txt "
                          "e rode de novo" % trabalho) from None
    if not stat.S_ISREG(estado.st_mode):
        raise comum.Falha("rascunho.json: não é um arquivo comum. Grave o rascunho como arquivo de texto, em JSON")
    if estado.st_size > valida.LIMITE_ARQUIVO:
        raise comum.Falha("rascunho.json: tem %d bytes, e a edição inteira vai até %d. Confira o que foi gravado "
                          "nele" % (estado.st_size, valida.LIMITE_EDICAO))
    try:
        rascunho = comum.le_json(caminho)
    except comum.Falha as falha:
        motivo = str(falha)
        motivo = motivo[len(caminho) + 2:] if motivo.startswith(caminho + ": ") else motivo
        raise comum.Falha("rascunho.json: %s" % _explica_json(caminho, motivo)) from None
    if not isinstance(rascunho, dict):
        raise comum.Falha("rascunho.json: deveria ser um objeto, entre { e }, na forma do modelo.txt. Reescreva")
    return rascunho


def _explica_json(caminho, motivo):
    """A mensagem do leitor de JSON em português, com o conserto. Linha de comentário copiada do modelo é o
    erro mais provável: ganha mensagem própria."""
    lido = _RE_LINHA_E_COLUNA.match(motivo)
    if lido:
        try:
            with open(caminho, "rb") as arquivo:
                linha = arquivo.read().decode("utf-8", "replace").split("\n")[int(lido.group(1)) - 1]
        except (OSError, IndexError):
            linha = ""
        if linha.strip().startswith("//"):
            return ("%sa linha começa com //, e JSON não tem comentário. Tire todas as linhas de comentário "
                    "copiadas do modelo.txt e rode de novo" % lido.group())
    for ingles, portugues in _ERROS_DE_JSON:
        motivo = motivo.replace("(%s)" % ingles, "(%s)" % portugues)
    return "%s. Conserte e rode de novo" % motivo


def _le_apoio(saida, trabalho, nome, dia, sem_ele):
    """Um JSON da pasta de trabalho que pode faltar: o objeto, ou None, com um aviso que diz o que muda sem ele.

    Arquivo que existe e não dá para ler, ou que é de outro dia (`dia` diz qual é o de hoje; None não confere),
    conta como ausente: a ferramenta que o grava pode ser rodada de novo, e dado de outro dia não entra na
    edição de hoje."""
    caminho = os.path.join(trabalho, nome)
    if not os.path.lexists(caminho):
        motivo = "não existe"
    else:
        objeto, _, problema = valida.le_json_do_repositorio(caminho, nome)
        if problema is not None:
            motivo = "não deu para ler (%s)" % problema.mensagem
        elif not isinstance(objeto, dict):
            motivo = "deveria ser um objeto, e não é"
        elif dia is not None and comum.data_valida(objeto.get("dia")) and objeto["dia"] != dia:
            motivo = "é de %s, e o dia da edição é %s" % (objeto["dia"], dia)
        else:
            return objeto
    saida.linha("aviso: %s %s: %s." % (nome, motivo, sem_ele))
    return None


def _le_urls(trabalho):
    """O texto de P/urls.txt, ou None se o arquivo não existe (ou não dá para ler)."""
    caminho = os.path.join(trabalho, "urls.txt")
    try:
        estado = os.lstat(caminho)
        if not stat.S_ISREG(estado.st_mode) or estado.st_size > valida.LIMITE_ARQUIVO:
            return None
        with open(caminho, "rb") as arquivo:
            # "utf-8-sig", como o coleta.py --confere: a marca de ordem de bytes não gruda na primeira URL.
            return arquivo.read().decode("utf-8-sig", "replace")
    except OSError:
        return None


class _Situacao(object):
    """O que já há publicado para o dia (CONTRATO, seção 4.2, passo 3).

    .tipo   "livre" (nada publicado: o que houver no disco é desta execução), "falha" (publicada como falha:
            pode ser trocada), "final" (completa ou reduzida: não muda) ou "ilegivel" (há algo no lugar, e
            não dá para saber o quê: não se grava por cima)
    .edicao o objeto publicado, ou None       .onde   "no commit HEAD" ou "no disco" """

    def __init__(self, tipo, edicao=None, onde=""):
        self.tipo, self.edicao, self.onde = tipo, edicao, onde


def _situacao_do_dia(raiz, dia, rep):
    """"Já publicado" se decide pelo commit HEAD; sem git na raiz, vale o disco.

    Só há git quando a raiz do repositório git é a própria raiz (valida.abre_git)."""
    relativo = "edicoes/%s.json" % dia
    git, _ = valida.abre_git(raiz)
    if git is None:
        if dia in rep.ilegiveis:
            return _Situacao("ilegivel", None, "no disco")
        if dia not in rep.edicoes:
            return _Situacao("livre")
        objeto, onde = rep.edicoes[dia], "no disco"
    else:
        conserto = "Rode de novo; persistindo, pare, sem commit, e relate"
        codigo, saida, erro = git.roda(["rev-parse", "--verify", "--quiet", "HEAD^{commit}"])
        if codigo >= 124:  # o git não rodou ou não respondeu: sem ele não dá para saber o que é final
            raise comum.Falha("o git não respondeu (%s), e é ele que diz se o dia já foi publicado. %s"
                              % (erro, conserto))
        if codigo != 0:
            return _Situacao("livre")  # repositório ainda sem commit
        revisao = saida.decode("ascii", "replace").strip()
        codigo, saida, erro = git.roda(["ls-tree", "-z", revisao, "--", relativo])
        if codigo != 0:
            raise comum.Falha("o git falhou ao procurar %s no commit HEAD (%s). %s" % (relativo, erro, conserto))
        if not saida.strip(b"\0"):
            return _Situacao("livre")
        bruto = git.conteudo(revisao, relativo)
        try:
            objeto = json.loads(bruto.decode("utf-8")) if bruto is not None else None
        except (ValueError, RecursionError):
            objeto = None
        onde = "no commit HEAD"
    if isinstance(objeto, dict) and objeto.get("estado") == "falha":
        return _Situacao("falha", objeto, onde)
    if isinstance(objeto, dict) and objeto.get("estado") in ("completa", "reduzida"):
        return _Situacao("final", objeto, onde)
    return _Situacao("ilegivel", None, onde)


def _recusa_ilegivel(situacao, dia):
    if situacao.tipo == "ilegivel":
        raise comum.Falha("edicoes/%s.json já existe %s, e não dá para ler o estado dela: pode ser edição final. "
                          "Nada foi gravado. Pare, sem commit, e relate" % (dia, situacao.onde))


# ---------------------------------------------------------------- os dois registros (ESQUEMA, seções 12 e 13)

def _sem_o_dia(dados, dia):
    """(Dados, players, vetores) sem o que o dia já tinha gravado nos dois registros.

    Na republicação do mesmo dia, o vetor ou a anulação com `data` igual ao dia e o player da rotina com
    `incluido_em` igual ao dia são tirados e refeitos a partir do rascunho novo. A conferência roda contra
    os registros já limpos: é contra eles que a edição vai ficar gravada."""
    players, vetores = dados.bruto["players"], dados.bruto["vetores"]
    players = dict(players, players=[p for p in players["players"]
                                     if not (isinstance(p, dict) and p.get("origem") == "rotina"
                                             and p.get("incluido_em") == dia)])
    vetores = dict(vetores, vetores=[v for v in vetores["vetores"]
                                     if not (isinstance(v, dict) and v.get("data") == dia)])
    limpos = valida.monta_dados(dados.bruto["regua"], players, dados.bruto["veiculos"], vetores,
                                dados.bruto["indicadores"])
    return limpos, players, vetores


def _itens(edicao):
    """[(item, caminho)] das principais e do radar, nessa ordem."""
    saida = []
    for chave in ("principais", "radar"):
        lista = edicao.get(chave)
        for indice, item in enumerate(lista if isinstance(lista, list) else ()):
            if isinstance(item, dict):
                saida.append((item, "%s[%d]" % (chave, indice)))
    return saida


def entradas_de_vetor(edicao, dia, dados):
    """As entradas que a edição acrescenta a dados/vetores.json: os vetores de cada item e uma anulação para
    cada errata com `anula_vetor`. Devolve (entradas, achados).

    O id do vetor é data, item e player (ESQUEMA, seção 12). Dois vetores do mesmo player no mesmo item
    dariam o mesmo id: o segundo vira erro, e nada é publicado."""
    entradas, achados, vistos = [], [], {}
    for item, caminho in _itens(edicao):
        vetores = item.get("vetores")
        for indice, vetor in enumerate(vetores if isinstance(vetores, list) else ()):
            if not isinstance(vetor, dict):
                continue
            identificador = "%s_%s_%s" % (dia, _uma_linha(item.get("id")), _uma_linha(vetor.get("player")))
            if identificador in vistos:
                # Dois vetores do mesmo player no mesmo item dariam ids iguais no registro. A regra R11 do
                # validador já os recusa; este achado só entra se ela calar (ver _edicao).
                achados.append(valida.Achado(
                    valida.ERRO, "R11", "%s.vetores[%d].player" % (caminho, indice),
                    "%s já tem outro vetor neste item (%s), e o registro guarda um vetor por player em cada item: "
                    "o id dele é data, item e player. Fique com o do ato mais forte e tire o outro."
                    % (_entre_aspas(vetor.get("player")), vistos[identificador])))
                continue
            vistos[identificador] = "%s.vetores[%d]" % (caminho, indice)
            entrada = {"id": identificador, "data": dia, "item": item.get("id"), "player": vetor.get("player"),
                       "de": dados.partido_do_player(vetor.get("player"))}
            for chave in ("para", "forca", "tema", "porque", "url"):
                entrada[chave] = vetor.get(chave)
            if item.get("conflito_de_interesse") is True:
                entrada["conflito_de_interesse"] = True
            entradas.append(entrada)
    anulacoes = 0
    for errata in _objetos(edicao.get("errata")):
        if "anula_vetor" in errata:
            anulacoes += 1
            entradas.append({"id": "%s_anula_%d" % (dia, anulacoes), "data": dia, "anula": errata["anula_vetor"],
                             "porque": errata.get("correcao"), "url": errata.get("url")})
    return entradas, achados


def _registros(edicao, dia, dados, players, vetores, entradas):
    """Os dois registros como vão ficar: (players ou None, vetores ou None). None: o arquivo não muda.

    `dados` são os do disco; `players` e `vetores`, os objetos já sem o que era do dia."""
    novos = [dict(novo, origem="rotina", incluido_em=dia) for novo in _objetos(edicao.get("novos_players"))]
    if novos:
        players = dict(players, atualizado_em=dia, players=players["players"] + novos)
    vetores = dict(vetores, vetores=vetores["vetores"] + entradas)
    return (None if _iguais(players, dados.bruto["players"]) else players,
            None if _iguais(vetores, dados.bruto["vetores"]) else vetores)


def _substitutos(valor, caminho=""):
    """Os caminhos dos textos que trazem metade solta de par substituto."""
    if isinstance(valor, str):
        if _RE_SUBSTITUTO.search(valor):
            yield caminho or "edicao"
    elif isinstance(valor, dict):
        for chave, dentro in valor.items():
            onde = "%s.%s" % (caminho, _uma_linha(chave)) if caminho else _uma_linha(chave)
            if isinstance(chave, str) and _RE_SUBSTITUTO.search(chave):
                yield onde
            for achado in _substitutos(dentro, onde):
                yield achado
    elif isinstance(valor, list):
        for indice, dentro in enumerate(valor):
            for achado in _substitutos(dentro, "%s[%d]" % (caminho, indice)):
                yield achado


def _confere_gravacao(edicao):
    """O que a gravação recusaria: texto com metade solta de par substituto, em qualquer lugar da edição.

    A regra R17 do validador já acusa essa metade nos campos que confere; esta é a última rede antes de
    gravar, e só entra onde ela calou (ver _edicao). Sem ela, a gravação escreveria o \\uXXXX na edição nova."""
    try:
        caminhos = sorted(set(_substitutos(edicao)))
    except RecursionError:
        return []
    return [valida.Achado(valida.ERRO, "R17", caminho, "traz metade solta de um caractere (código de d800 a dfff, "
                          "como o de um emoji escrito pela metade), que não dá para gravar. Escreva o caractere "
                          "direto, ou tire.") for caminho in caminhos[:20]]


# ---------------------------------------------------------------- --corta (CONTRATO, seção 4.2)

_CHAVES_DE_TEXTO = frozenset(chave for _, chave in valida.MAXIMOS) - frozenset(["anula_vetor"])


def _textos_livres(valor, caminho=""):
    """(caminho, texto) de cada campo de texto livre do rascunho: os que têm tamanho máximo no esquema."""
    if isinstance(valor, dict):
        for chave, dentro in valor.items():
            onde = "%s.%s" % (caminho, _uma_linha(chave)) if caminho else _uma_linha(chave)
            if chave in _CHAVES_DE_TEXTO and isinstance(dentro, str):
                yield onde, dentro
            elif chave in _CHAVES_DE_TEXTO and isinstance(dentro, list):
                for indice, texto in enumerate(dentro):
                    if isinstance(texto, str):
                        yield "%s[%d]" % (onde, indice), texto
            else:
                for achado in _textos_livres(dentro, onde):
                    yield achado
    elif isinstance(valor, list):
        for indice, dentro in enumerate(valor):
            for achado in _textos_livres(dentro, "%s[%d]" % (caminho, indice)):
                yield achado


def corta(rascunho, pedidos):
    """Tira do rascunho os itens pedidos e conserta o que dependia deles. Devolve (rascunho novo, relato).

    Renumera os ids em ordem (p1..pN, r1..rN), acerta os `ref` dos gatilhos, tira o gatilho que apontava
    para item cortado e tira de `placar_do_dia` o partido que ficou sem linha em placar nenhum. Texto livre
    que cita id cortado ou renumerado não é reescrito: o relato avisa onde está. Não mexe em `estado`: quem
    diz se a contagem da completa deixou de fechar é o validador (ver _acerta_estado).
    Id pedido que o rascunho não tem é comum.ErroDeUso (código 2: a opção pediu o que não existe). Id que
    aparece em dois itens é comum.Falha (código 1: o defeito é do rascunho). Nos dois casos nada é cortado."""
    novo = json.loads(json.dumps(rascunho))
    relato = []
    existentes = [item.get("id") for chave in ("principais", "radar") for item in _objetos(novo.get(chave))]
    for pedido in pedidos:
        if existentes.count(pedido) != 1:
            tem = ", ".join(_uma_linha(e) for e in existentes if isinstance(e, str)) or "nenhum"
            erro = comum.ErroDeUso if pedido not in existentes else comum.Falha
            raise erro("--corta: o rascunho %s o item %s (os ids dele: %s). Nada foi cortado. Confira o id "
                       "e rode de novo" % ("não tem" if pedido not in existentes else "tem mais de um com",
                                           pedido, tem))
    cortados, mapa = set(pedidos), {}
    for chave, prefixo in (("principais", "p"), ("radar", "r")):
        lista = novo.get(chave)
        if not isinstance(lista, list):
            continue
        sai = [isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"] in cortados for item in lista]
        for item, cortado in zip(lista, sai):
            if cortado:
                relato.append("cortado %s: %s" % (item["id"], _uma_linha(item.get("titulo"))[:80]))
        restantes = [item for item, cortado in zip(lista, sai) if not cortado]
        for indice, item in enumerate(restantes):
            certo = "%s%d" % (prefixo, indice + 1)
            if isinstance(item, dict) and item.get("id") != certo:
                if isinstance(item.get("id"), str):
                    mapa[item["id"]] = certo
                item["id"] = certo
        novo[chave] = restantes
    if mapa:
        relato.append("renumerado: %s" % ", ".join("%s virou %s" % (_uma_linha(antes), depois)
                                                   for antes, depois in mapa.items()))

    for dominio in _objetos(_objeto(novo.get("alerta")).get("dominios")):
        gatilhos = dominio.get("gatilhos")
        if not isinstance(gatilhos, list):
            continue
        ficam = []
        for gatilho in gatilhos:
            ref = gatilho.get("ref") if isinstance(gatilho, dict) else None
            if isinstance(ref, str) and ref in cortados:
                relato.append("gatilho tirado de %s: %s apontava para %s, que foi cortado"
                              % (_uma_linha(dominio.get("id")), _uma_linha(gatilho.get("criterio")), ref))
                continue
            if isinstance(ref, str) and ref in mapa:
                relato.append("gatilho de %s acertado: ref %s virou %s"
                              % (_uma_linha(dominio.get("id")), ref, mapa[ref]))
                gatilho["ref"] = mapa[ref]
            ficam.append(gatilho)
        dominio["gatilhos"] = ficam

    com_linha = set(linha.get("partido") for item, _ in _itens(novo) for linha in _objetos(item.get("placar"))
                    if isinstance(linha.get("partido"), str))
    if isinstance(novo.get("placar_do_dia"), list):
        ficam = []
        for linha in novo["placar_do_dia"]:
            partido = linha.get("partido") if isinstance(linha, dict) else None
            if isinstance(partido, str) and partido not in com_linha:
                relato.append("placar_do_dia: saiu %s, que ficou sem linha em placar nenhum" % _uma_linha(partido))
            else:
                ficam.append(linha)
        novo["placar_do_dia"] = ficam

    for caminho, texto in _textos_livres(novo):
        for citado in sorted(set(_RE_CITA_ITEM.findall(texto))):
            if citado in cortados:
                relato.append("aviso: %s cita %s, que foi cortado. O texto não foi reescrito: confira."
                              % (caminho, citado))
            elif citado in mapa:
                relato.append("aviso: %s cita %s, que agora é %s. O texto não foi reescrito: confira."
                              % (caminho, citado, mapa[citado]))
    return novo, relato


def _acerta_estado(rascunho, dados, historico, indicadores, coleta, relato):
    """Troca `estado` para reduzida se a contagem da completa deixou de fechar (regra R15).

    Quem conta é o validador: a edição é completada e conferida, e basta um erro R15 para a troca."""
    if rascunho.get("estado") != "completa":
        return
    edicao = valida.completa(rascunho, dados, historico, indicadores, coleta, None)
    achados = valida.confere_edicao(edicao, dados, historico, True)
    if any(a.regra == "R15" and a.gravidade == valida.ERRO for a in achados):
        rascunho["estado"] = "reduzida"
        relato.append("estado: completa virou reduzida, porque a contagem da completa deixou de fechar. Diga em "
                      "bastidores.limites o que ficou de fora.")


# ---------------------------------------------------------------- os subcomandos

def _feed_conferido(edicoes, dados, base):
    """O texto do feed, já passado pela conferência do validador: é a mesma do workflow de publicação."""
    feed = texto_do_feed(edicoes, dados, base)
    recusas = valida.separa(valida.confere_feed(feed.encode("utf-8")))[0]
    if recusas:  # nunca deveria acontecer: é a última rede antes de gravar o que o workflow recusaria
        raise RuntimeError("o feed montado não passa na conferência: %s" % recusas[0].mensagem)
    return feed


def _monta_lote(raiz, dia, edicao, rep, dados, players, vetores, base):
    """O que o passo 7 grava (CONTRATO, seção 4.2): (lote, caminhos relativos). Nada vai para o disco aqui."""
    edicoes = _edicoes_legiveis(rep, {dia: edicao})
    conteudos = [("edicoes/%s.json" % dia, edicao),
                 ("edicoes/%s.md" % dia, texto_da_edicao(edicao, dados, valida.Historico(edicoes))),
                 ("edicoes/indice.json", valida.monta_indice(edicoes)),
                 ("feed.xml", _feed_conferido(edicoes, dados, base))]
    if vetores is not None:
        conteudos.append(("dados/vetores.json", vetores))
    if players is not None:
        conteudos.append(("dados/players.json", players))
    lote, relativos = comum.Lote(), []
    for relativo, conteudo in conteudos:
        caminho = os.path.join(raiz, *relativo.split("/"))
        lote.texto(caminho, conteudo if isinstance(conteudo, str) else _json_texto(conteudo))
        relativos.append(relativo)
    return lote, relativos


def _grava(saida, lote, relativos):
    lote.grava()
    saida.linha("gravado: %s" % ", ".join(relativos))
    saida.dado("arquivos", relativos)


def _resumo_da_edicao(dados, edicao):
    vetores = sum(len(_objetos(item.get("vetores"))) for item, _ in _itens(edicao))
    return "%s, %s, %d radar, %s, %s" % (
        _nivel_em_texto(dados, edicao),
        _conta(len(_objetos(edicao.get("principais"))), "principal", "principais"),
        len(_objetos(edicao.get("radar"))), _conta(vetores, "vetor", "vetores"),
        _conta(len(_objetos(edicao.get("novos_players"))), "player novo", "players novos"))


def _mostra_achados(saida, achados, dia):
    """Os achados no formato do valida.py: os erros primeiro, os avisos depois. Devolve os erros."""
    erros, avisos = valida.separa(achados)
    for achado in erros + avisos:
        saida.linha(achado.linha())
    saida.dado("erros", [achado.objeto() for achado in erros])
    saida.dado("avisos", [achado.objeto() for achado in avisos])
    if any(achado.caminho == "gerada_em" for achado in erros):
        # O carimbo é do relógio, e não do rascunho: o conserto está no dia pedido, não no texto.
        saida.linha("aviso: o relógio marca %s, e o dia da edição é %s. Edição só se publica no próprio dia: "
                    "confira o --dia (ou o dia do contexto.json)." % (comum.agora_texto(), dia))
    return erros


def _contexto(args, saida):
    rep = valida.carrega(args.raiz)
    _barra(rep, saida, ("dados/regua.json", "dados/veiculos.json", "dados/vetores.json", "edicoes"))
    dia, dados = args.dia, rep.dados
    contexto = monta_contexto(dia, dados, _edicoes_legiveis(rep))
    lote = comum.Lote()
    lote.texto(os.path.join(args.trabalho, "contexto.json"), _json_texto(contexto))
    lote.texto(os.path.join(args.trabalho, "mapa.txt"), texto_do_mapa(dados))
    lote.texto(os.path.join(args.trabalho, "modelo.txt"), MODELO)
    lote.grava()

    saida.linha("dia %s · janela de %d horas" % (dia, contexto["janela_horas"]))
    do_dia = contexto["edicao_do_dia"]
    if do_dia is None:
        saida.linha("edição do dia: não há")
    else:
        saida.linha("edição do dia: já existe, estado %s, gerada em %s"
                    % (_uma_linha(do_dia["estado"]), _uma_linha(do_dia["gerada_em"])))
    anterior = contexto["anterior"]
    saida.linha("anterior: %s" % ("%s, %s" % (anterior["data"], _uma_linha(anterior["estado"])) if anterior
                                  else "não há (primeira edição)"))
    alerta = contexto["alerta_anterior"]
    saida.linha("alerta anterior: nível %d%s" % (alerta["nivel"], _rotulo(dados, alerta["nivel"])))
    for dominio in alerta["dominios"]:
        if dominio["nivel"] <= 1:
            continue
        partes = ["%s %d desde %s" % (_uma_linha(dominio["id"]), dominio["nivel"], _dia_curto(dominio["desde"])),
                  _conta(dominio["edicoes_sem_gatilho"], "edição sem gatilho", "edições sem gatilho")]
        if dominio["desce_hoje_sem_gatilho"]:
            partes.append("desce hoje sem gatilho")
        if dominio["origem"]:
            partes.append("origem: %s de %s" % (_uma_linha(dominio["origem"]["criterio"]),
                                                dominio["origem"]["edicao"]))
        saida.linha("  " + " · ".join(partes))
    saida.linha("histórias recentes: %d" % len(contexto["historias_recentes"]))
    saida.linha("vigiar vencendo: %d" % len(contexto["vigiar_vencendo"]))
    for pergunta in contexto["vigiar_vencendo"]:
        saida.linha("  %s/%s, prazo %s: %s" % (pergunta["edicao"], _uma_linha(pergunta["item"]),
                                               comum.dd_mm(pergunta["prazo"]), _uma_linha(pergunta["pergunta"])))
    saida.linha("candidatos: %s" % (", ".join("%s (%s)" % (_uma_linha(c["id"]),
                                                           _conta(c["edicoes"], "edição", "edições"))
                                              for c in contexto["candidatos"]) or "nenhum"))
    saida.linha("vetores recentes: %d" % len(contexto["vetores_recentes"]))
    for problema in confere_modelo():
        saida.linha("aviso: o modelo.txt não bate com as tabelas do validador: %s" % problema)
    saida.linha("gravado em %s: contexto.json, mapa.txt (%s) e modelo.txt"
                % (args.trabalho, _conta(len(dados.mapa), "veículo", "veículos")))
    saida.dado("contexto", contexto)
    saida.dado("arquivos", [os.path.join(args.trabalho, nome) for nome in ("contexto.json", "mapa.txt", "modelo.txt")])
    return saida.fecha("OK contexto de %s" % dia)


def _edicao(args, saida):
    dia, raiz, trabalho = args.dia, args.raiz, args.trabalho
    rascunho = _le_rascunho(trabalho)  # passo 1
    rep = valida.carrega(raiz)
    situacao = _situacao_do_dia(raiz, dia, rep)
    _recusa_ilegivel(situacao, dia)
    _barra(rep, saida, ("dados/", "edicoes"), livre=dia if situacao.tipo == "livre" else None)
    dados, players, vetores = _sem_o_dia(rep.dados, dia)
    historico = rep.historico
    indicadores = _le_apoio(saida, trabalho, "indicadores.json", dia, "a edição sai sem indicadores, e os domínios "
                            "com preço ficam sem dado. Rode indicadores.py")
    coleta = _le_apoio(saida, trabalho, "coleta.json", dia, "feeds_ok e feeds_falhos saem 0, e só vale URL anotada "
                       "em urls.txt. Rode coleta.py")
    conferencia = _le_apoio(saida, trabalho, "conferencia.json", None, "só as URLs da coleta têm data conferida. "
                            "Rode coleta.py --confere")
    urls = _le_urls(trabalho)

    if args.corta:  # passo 2
        rascunho, relato = corta(rascunho, args.corta)
        _acerta_estado(rascunho, dados, historico, indicadores, coleta, relato)
        for linha in relato:
            saida.linha(linha)
        if args.simula:
            saida.linha("simulação: o rascunho.json não foi regravado")
        else:
            comum.grava_texto(os.path.join(trabalho, "rascunho.json"), _json_texto(rascunho))
            saida.linha("rascunho.json regravado, já sem %s" % ", ".join(args.corta))

    edicao = valida.completa(rascunho, dados, historico, indicadores, coleta, comum.agora_texto())  # passo 4
    saida.dado("dia", dia)

    if situacao.tipo == "final":  # passo 3: precisa da edição completa, para comparar com a publicada
        sem_carimbo = dict((chave, valor) for chave, valor in edicao.items() if chave != "gerada_em")
        publicada = dict((chave, valor) for chave, valor in situacao.edicao.items() if chave != "gerada_em")
        if _iguais(sem_carimbo, publicada):
            return saida.fecha("OK edição %s já publicada: nada mudou" % dia)
        diferentes = [chave for chave in sorted(set(sem_carimbo) | set(publicada), key=_ordem_da_raiz)
                      if not _iguais(sem_carimbo.get(chave), publicada.get(chave))]
        raise comum.Falha("edição %s já publicada (estado %s, %s), e o rascunho dá outra edição (difere em: %s). "
                          "Edição publicada não muda: nada foi gravado. Pare, sem alterar nada, e relate; "
                          "correção de fato vai na errata da edição seguinte"
                          % (dia, situacao.edicao.get("estado"), situacao.onde,
                             ", ".join(_uma_linha(chave)[:30] for chave in diferentes)))

    do_arquivo = dia if edicao.get("data") == dia else None  # data errada é a regra T2 que acusa, e não a R01
    achados = valida.confere_edicao(edicao, dados, historico, True, do_arquivo)  # passo 5
    achados += valida.confere_trabalho(rascunho, dados, dia, coleta, urls, conferencia, historico)
    entradas, colisoes = entradas_de_vetor(edicao, dia, dados)
    # O validador já acusa os dois casos que a gravação não aguenta (R11: dois vetores do mesmo player no mesmo
    # item; R17: metade solta de par substituto). O publica.py é a última rede antes de gravar: soma o seu
    # achado só onde o validador calou, e a mesma linha nunca sai duas vezes.
    vistos = set((achado.regra, achado.caminho) for achado in achados)
    achados += [achado for achado in colisoes + _confere_gravacao(edicao) if (achado.regra, achado.caminho) not in vistos]
    if _mostra_achados(saida, achados, dia):  # passo 6
        if args.simula:
            saida.linha("níveis calculados: %s" % _nivel_em_texto(dados, edicao))
        return saida.fecha(valida.veredito(achados), comum.FALHA)

    novos_players, novos_vetores = _registros(edicao, dia, rep.dados, players, vetores, entradas)
    base, origem = endereco_base(raiz, args.url_base)
    lote, relativos = _monta_lote(raiz, dia, edicao, rep, dados, novos_players, novos_vetores, base)  # passo 7
    resumo = _resumo_da_edicao(dados, edicao)
    saida.dado("estado", edicao.get("estado"))
    saida.dado("nivel", _objeto(edicao.get("alerta")).get("nivel"))
    saida.linha("endereço base do feed: %s (%s)" % (base, origem))
    if args.simula:
        saida.linha("simulação: gravaria %s" % ", ".join(relativos))
        saida.linha("níveis calculados: %s" % _nivel_em_texto(dados, edicao))
        saida.dado("gravaria", relativos)
        return saida.fecha("OK simulação: a edição %s passa, e nada foi gravado: %s" % (dia, resumo))
    if situacao.tipo == "falha":
        saida.linha("a edição de falha de %s (%s) dá lugar à edição nova" % (dia, situacao.onde))
    _grava(saida, lote, relativos)
    return saida.fecha("OK edição %s publicada: %s" % (dia, resumo))  # passo 8


def _ordem_da_raiz(chave):
    ordem = valida.ORDEM["raiz"]
    return (ordem.index(chave) if chave in ordem else len(ordem), _como_texto(chave))


def _falha(args, saida):
    dia, raiz, motivo = args.dia, args.raiz, args.motivo
    rep = valida.carrega(raiz)
    situacao = _situacao_do_dia(raiz, dia, rep)
    _recusa_ilegivel(situacao, dia)
    _barra(rep, saida, ("dados/", "edicoes"), livre=dia if situacao.tipo == "livre" else None)
    if situacao.tipo == "final":
        raise comum.Falha("edição %s já publicada (estado %s, %s): a edição de falha não entra no lugar de "
                          "edição final. Nada foi gravado. Pare, sem alterar nada, e relate"
                          % (dia, situacao.edicao.get("estado"), situacao.onde))
    dados, players, vetores = _sem_o_dia(rep.dados, dia)
    historico = rep.historico
    anterior = historico.anterior(dia)
    sem_leitura = "Sem leitura hoje." + (" Nível repetido de %s." % comum.dd_mm(anterior.data) if anterior else "")
    rascunho = {
        "data": dia, "estado": "falha", "resumo": "Sem edição hoje. " + motivo,
        "alerta": {"motivo": motivo,
                   "dominios": [{"id": dominio, "gatilhos": [], "leitura": sem_leitura, "vigiar": sem_leitura}
                                for dominio in dados.dominios]},
        "principais": [], "radar": [], "placar_do_dia": [], "novos_players": [], "errata": [], "respostas": [],
        "bastidores": {"modo": "feeds", "paginas_lidas": 0, "buscas": 0, "minutos": 0, "injecoes_ignoradas": 0,
                       "candidatos": [], "veiculos_sugeridos": [], "limites": motivo}}
    indicadores = _le_apoio(saida, args.trabalho, "indicadores.json", dia, "a edição de falha sai sem indicadores")
    agora = comum.agora_texto()
    edicao = valida.completa(rascunho, dados, historico, indicadores, None, agora)
    achados = valida.confere_edicao(edicao, dados, historico, True, dia)
    if indicadores is not None and valida.separa(achados)[0]:
        # A falha é a última saída do dia: indicador que não passa na conferência não a segura.
        sem_eles = valida.completa(rascunho, dados, historico, None, None, agora)
        de_novo = valida.confere_edicao(sem_eles, dados, historico, True, dia)
        if not valida.separa(de_novo)[0]:
            saida.linha("aviso: indicadores.json não passou na conferência (%s): a edição de falha sai sem "
                        "indicadores." % valida.separa(achados)[0][0].linha())
            edicao, achados = sem_eles, de_novo
    saida.dado("dia", dia)
    if _mostra_achados(saida, achados, dia):
        return saida.fecha(valida.veredito(achados), comum.FALHA)
    novos_players, novos_vetores = _registros(edicao, dia, rep.dados, players, vetores, [])
    base, origem = endereco_base(raiz, args.url_base)
    lote, relativos = _monta_lote(raiz, dia, edicao, rep, dados, novos_players, novos_vetores, base)
    saida.dado("estado", "falha")
    saida.dado("nivel", _objeto(edicao.get("alerta")).get("nivel"))
    saida.linha("endereço base do feed: %s (%s)" % (base, origem))
    _grava(saida, lote, relativos)
    repetido = "repetido de %s" % comum.dd_mm(anterior.data) if anterior else "sem edição anterior"
    return saida.fecha("OK falha de %s publicada: sem edição hoje; %s, %s"
                       % (dia, _nivel_em_texto(dados, edicao), repetido))


def _refaz(args, saida):
    raiz = args.raiz
    rep = valida.carrega(raiz)
    _barra(rep, saida, ("edicoes",))
    edicoes, dados = _edicoes_legiveis(rep), rep.dados
    historico = valida.Historico(edicoes)
    base, origem = endereco_base(raiz, args.url_base)
    lote, relativos = comum.Lote(), ["edicoes/indice.json"]
    lote.texto(os.path.join(raiz, "edicoes", "indice.json"), _json_texto(valida.monta_indice(edicoes)))
    for data in sorted(edicoes):
        lote.texto(os.path.join(raiz, "edicoes", data + ".md"), texto_da_edicao(edicoes[data], dados, historico))
        relativos.append("edicoes/%s.md" % data)
    lote.texto(os.path.join(raiz, "feed.xml"), _feed_conferido(edicoes, dados, base))
    relativos.append("feed.xml")
    for data in sorted(rep.textos - set(edicoes)):
        saida.linha("aviso: edicoes/%s.md não tem edição (falta edicoes/%s.json). O refaz não apaga arquivo: "
                    "apague-o à mão." % (data, data))
    saida.linha("endereço base do feed: %s (%s)" % (base, origem))
    _grava(saida, lote, relativos)
    no_feed = min(ENTRADAS_DO_FEED, sum(1 for edicao in edicoes.values() if edicao.get("exemplo") is not True))
    return saida.fecha("OK refeitos o índice (%s), %s e o feed (%s)"
                       % (_conta(len(edicoes), "edição", "edições"), _conta(len(edicoes), "texto", "textos"),
                          _conta(no_feed, "entrada", "entradas")))


# ---------------------------------------------------------------- linha de comando

def _tipo_corta(texto):
    ids = [parte.strip() for parte in texto.split(",")]
    for identificador in ids:
        if not _RE_ID_DE_ITEM.fullmatch(identificador):
            raise argparse.ArgumentTypeError("id ilegível %r (use p1 a p3 ou r1 a r12; vários, com vírgula: r3,r7)"
                                             % identificador)
    if len(set(ids)) != len(ids):
        raise argparse.ArgumentTypeError("id repetido em %r" % texto)
    return ids


def _tipo_base(texto):
    base = base_valida(texto)
    if base is None:
        raise argparse.ArgumentTypeError("endereço ilegível %r (use o endereço do site, como "
                                         "https://DONO.github.io/INFOCENARIUM/, ou ./)" % texto)
    return base


def _analisador():
    an = comum.analisador("Contexto do dia, publicação da edição, edição de falha, e índice, textos e feed do "
                          "INFOCENARIUM. Sem rede. As opções vêm depois do subcomando.")
    sub = an.add_subparsers(dest="comando", metavar="SUBCOMANDO", title="subcomandos")
    base = dict(metavar="URL", type=_tipo_base, default=None, dest="url_base",
                help="endereço do site, para o feed (padrão: o que já está no feed.xml; depois, o remoto do git)")
    comum.poe_comuns(sub.add_parser(
        "contexto", help="grava contexto.json, mapa.txt e modelo.txt",
        description="Grava na pasta de trabalho a memória dos dias anteriores (contexto.json), o mapa de veículos "
        "em resumo (mapa.txt) e a forma do rascunho (modelo.txt)."))
    edicao = comum.poe_comuns(sub.add_parser(
        "edicao", help="completa, confere e publica o rascunho",
        description="Lê rascunho.json da pasta de trabalho, preenche os campos calculados, confere tudo e, sem "
        "erro, grava a edição, o texto, o índice, o feed e os registros."))
    edicao.add_argument("--corta", metavar="ID[,ID]", type=_tipo_corta, default=None,
                        help="tira do rascunho os itens citados (r3, ou r3,r7), renumera e regrava o rascunho")
    edicao.add_argument("--simula", action="store_true", help="faz tudo menos gravar, e diz o que gravaria")
    edicao.add_argument("--url-base", **base)
    falha = comum.poe_comuns(sub.add_parser(
        "falha", help="publica a edição de falha do dia",
        description="Publica a edição de falha: sem edição hoje, com os níveis da edição anterior."))
    falha.add_argument("--motivo", metavar="TEXTO", required=True,
                       help="o que houve, em até %d caracteres, sem HTML" % MOTIVO_MAXIMO)
    falha.add_argument("--url-base", **base)
    refaz = comum.poe_comuns(sub.add_parser(
        "refaz", help="refaz o índice, os textos e o feed",
        description="Refaz edicoes/indice.json, todos os edicoes/*.md e o feed.xml a partir dos arquivos de "
        "edição. Não toca nas edições nem em dados/."), trabalho=False)
    # O refaz não usa a pasta de trabalho, mas a opção é comum: fica aceita, e a pasta nem é criada.
    refaz.add_argument("--trabalho", metavar="PASTA", dest="trabalho_sem_uso", default=None,
                       help="aceita e sem uso: o refaz só olha o repositório")
    refaz.add_argument("--url-base", **base)
    return an


def principal(argv):
    """A linha de comando (CONTRATO, seção 4). Recebe os argumentos e devolve o código de saída."""
    if not argv or (argv[0].startswith("-") and argv[0] not in ("-h", "--help")):
        raise comum.ErroDeUso("falta o subcomando, que vem antes das opções: use %s (publica.py contexto --dia …)"
                              % ", ".join(SUBCOMANDOS))
    args = _analisador().parse_args(argv)
    if args.comando == "falha":
        problemas = valida.confere_texto(args.motivo, MOTIVO_MAXIMO)
        if _RE_SUBSTITUTO.search(args.motivo):
            problemas.append("traz byte que não é UTF-8. Escreva o motivo em texto simples.")
        if problemas:
            raise comum.ErroDeUso("--motivo: %s" % problemas[0])
    de_hoje = args.comando in ("contexto", "refaz")
    args = comum.prepara(args, dia_padrao=comum.DIA_DE_HOJE if de_hoje else comum.DIA_DO_CONTEXTO)
    saida = comum.Saida(args.json)
    return {"contexto": _contexto, "edicao": _edicao, "falha": _falha, "refaz": _refaz}[args.comando](args, saida)


if __name__ == "__main__":
    comum.executa(principal)
