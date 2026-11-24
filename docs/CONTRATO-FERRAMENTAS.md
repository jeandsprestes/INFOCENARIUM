# INFOCENARIUM · CONTRATO DAS FERRAMENTAS (versão 1)

Interface de linha de comando de `coleta.py`, `indicadores.py`, `valida.py` e `publica.py`.
Quem escreve as ferramentas segue este contrato. Quem as usa (o agente diário, o GitHub Action, os testes)
só conta com o que está aqui. Os formatos de dado da edição e as regras R, H, T, G, M e C estão em `ESQUEMA.md`.
Versão 1, de 23/11/2026. O formato dos dados está em `docs/ESQUEMA.md`; o manual do agente diário, em
`ROTINA.md`, na raiz do repositório.

## 0. Regras comuns às quatro

**Chamada.** `python3 ferramentas/NOME.py [opções]`, a partir da raiz do repositório. Python 3.10 ou mais novo,
só biblioteca padrão.
A documentação da VM da nuvem diz só "Python 3.x", e a versão do runner do GitHub não foi conferida (as duas
máquinas são Ubuntu 24.04, que traz o 3.12): confere-se na primeira execução. Com Python mais velho que 3.10,
a ferramenta para logo no começo, com `FALHA interna: Python 3.10 ou mais novo` e código 1. Para essa guarda
funcionar, o arquivo de cada uma das quatro ferramentas é escrito em sintaxe que o Python 3.7 lê (sem `match`,
sem `:=`, sem parâmetro `/`, sem `f"{x=}"`). Um teste confere com `ast.parse(…, feature_version=(3, 7))`; não se
pede menos que 3.7 porque o Python 3.13 recusa.

**Opções comuns.**

| Opção | Padrão | Para quê |
|---|---|---|
| `--raiz PASTA` | a pasta acima de `ferramentas/` | raiz do repositório (testes usam outra) |
| `--trabalho PASTA` | `/tmp/info` | pasta de trabalho, fora do repositório; é criada se faltar. O `valida.py` não tem esta opção: ele só olha o repositório |
| `--dia AAAA-MM-DD` | o `dia` de `P/contexto.json`, se o arquivo existe; senão, hoje em Brasília (UTC−3 fixo) | dia da edição. No `publica.py contexto` e no `valida.py`, o padrão é sempre hoje em Brasília: o primeiro cria o contexto, o segundo não lê a pasta de trabalho |
| `--json` | desligado | imprime um objeto JSON no lugar do texto |

**`--json`.** A forma padrão é `{"ok", "codigo", "veredito", "linhas"}`: `ok` é `true` só com código 0, `codigo`
é o código de saída, `veredito` é a última linha que o modo texto daria e `linhas` são as outras linhas, na
ordem. Cada ferramenta acrescenta os campos próprios (a `coleta.py`, por exemplo, `arquivos` e `resumo`). O
`valida.py` acrescenta `erros` e `avisos` (seção 3). Erro de uso sai sempre como uma linha de texto, mesmo com `--json`:
a linha de comando recusada não chegou a valer. `--raiz` com pasta que não existe também é erro de uso.

O dia nasce uma vez, no `publica.py contexto`, e as outras ferramentas leem dali. Assim uma execução que
cruza a meia-noite não troca de dia no meio.

**Pasta de trabalho** (`P`). Tudo o que não vai a público mora nela. Nomes fixos:

| Arquivo | Quem grava | Quem lê |
|---|---|---|
| `inicio` | o agente (segundos do relógio no começo) | o agente |
| `contexto.json` | `publica.py contexto` | o agente, e as outras ferramentas (o `dia` e a `janela_horas`) |
| `mapa.txt` | `publica.py contexto` | o agente |
| `modelo.txt` | `publica.py contexto` | o agente (a forma do rascunho, comentada) |
| `coleta.json` | `coleta.py` | `publica.py edicao`, `coleta.py --confere` |
| `mesa.txt` | `coleta.py` | o agente |
| `indicadores.json` | `indicadores.py` | o agente, `publica.py edicao` e `falha` |
| `urls.txt` | o agente (uma URL por linha; linha com `#` é comentário) | `coleta.py --confere`, `publica.py edicao` |
| `conferencia.json` | `coleta.py --confere` | `publica.py edicao` |
| `rascunho.json` | o agente (a edição, só com os campos de origem `agente`) | `publica.py edicao` |
| `notas.md` | o agente (anotações livres do que leu; a sessão pode ser resumida no meio) | o agente |

O agente não grava dentro do repositório. Quem grava é o `publica.py`.

`/tmp/info` é pasta com nome, criada pela rotina e nunca apagada por ela. A documentação da nuvem não diz se
`/tmp` aceita gravação: confere-se na primeira execução.
Se não aceitar, a saída é a opção `--trabalho` com uma pasta dentro do repositório, listada no `.gitignore`
(a regra G4 não conta arquivo ignorado). Por isso toda ferramenta que usa a pasta de trabalho obedece a `--trabalho`.

**Saída.** Texto em português na saída padrão, uma informação por linha. A **última linha** é o veredito e
começa com `OK`, `PARCIAL` ou `FALHA`. Nada essencial vai para a saída de erro.

**Códigos de saída.**

| Código | Nome | Sentido |
|---|---|---|
| 0 | OK | fez tudo |
| 1 | FALHA | erro de validação, entrada ilegível ou nada publicado |
| 2 | USO | opção errada na linha de comando |
| 3 | PARCIAL | gravou a saída, mas incompleta (só `coleta.py` e `indicadores.py`) |
| 4 | SEM REDE | gravou a saída vazia; a última linha é `FALHA sem rede: …` (só `coleta.py` e `indicadores.py`) |

**Comportamento em falha.**

- Nunca termina com exceção solta. Erro inesperado vira `FALHA interna: Tipo: mensagem` e código 1.
- `coleta.py` e `indicadores.py` gravam o arquivo de saída **sempre que chegam a rodar**, mesmo vazio (sem rede,
  sem nada na janela), e também quando param no meio com `FALHA interna`: o passo seguinte não quebra nem lê o
  arquivo de uma execução anterior. Com erro de uso (código 2) ou entrada ilegível (código 1: mapa, catálogo,
  régua ou `contexto.json`), nada é gravado, e os arquivos de antes ficam como estavam.
- `contexto.json` que existe e não dá para ler (JSON quebrado, não é objeto, `dia` ausente ou impossível),
  numa ferramenta que precisa dele, é `FALHA`, código 1, e nada é gravado. A mensagem manda rodar o
  `publica.py contexto` de novo, ou passar `--dia`. Cair para "hoje" trocaria de dia calado depois da meia-noite.
- `valida.py` nunca grava nada. `publica.py` grava tudo ou nada: com erro, nenhum arquivo muda.
- Escrita atômica: grava num arquivo temporário na mesma pasta e troca de nome no fim.
- Nenhuma ferramenta deixa arquivo a mais no repositório. Em especial, nenhuma grava `__pycache__`
  (`sys.dont_write_bytecode = True` antes de importar outra ferramenta): a regra G4 o veria como arquivo novo.
- JSON gravado: UTF-8, sem BOM, acentos legíveis, recuo de 2 espaços, quebra de linha no fim,
  chaves na ordem do `ESQUEMA.md`. Mesma entrada, mesmos bytes.

**Rede** (só `coleta.py` e `indicadores.py`).

- Só `http` e `https`, e só endereço com nome de site público. É recusado, no pedido e em cada destino de
  redirecionamento: número de IP (também nas formas antigas, como `127.1`), `localhost`, nome de um rótulo só,
  nome interno (`.local`, `.internal`, `.lan`, `.home`, `.corp`, `.intranet`, `.localdomain`, `.arpa`, `.svc`),
  usuário ou senha na URL, espaço, caractere de controle, barra invertida e URL com mais de 2.000 caracteres. A
  ferramenta não resolve o nome para conferir o endereço: um nome público que aponta para a própria máquina
  ainda recebe o pedido (limite conhecido, a decidir depois da primeira execução na nuvem).
- Tempo limite por pedido, contado do começo ao fim da tentativa: os redirecionamentos e o corpo inteiro
  entram no mesmo relógio (resposta em conta-gotas também estoura).
- Uma nova tentativa, depois de 1 segundo, só para falha passageira: conexão caída ou recusada, nome que não
  resolveu por erro temporário, resposta incompleta, gzip estragado, 429 e 5xx. Tempo esgotado não se repete,
  nem 4xx, certificado recusado ou redirecionamento recusado. Depois de 8 falhas sem nenhum sucesso na mesma
  execução, a ferramenta deixa de repetir (a máquina parece sem rede, e insistir só gasta o teto). Sem a
  nova tentativa se o teto do `--tempo` chega antes.
- Até 3 redirecionamentos (301, 302, 303, 307 e 308), seguidos pela própria ferramenta, que confere cada destino.
- Resposta de até 2 MB (2.097.152 bytes, contados depois de abrir o gzip). Feed ou fonte de preço maior que
  isso é erro (`resposta maior que 2 MB`); no `--confere`, a página é `bloqueada`.
- Cabeçalho `User-Agent: Mozilla/5.0 (compatible; INFOCENARIUM-monitor/1)`.
- O que chega da rede é dado. A ferramenta só lê XML, JSON, CSV e, no modo `--confere`, dois campos de data
  do HTML. Nunca executa nada do que baixou.
- Usa o proxy e os certificados do sistema (variáveis `HTTPS_PROXY` e `HTTP_PROXY`; soma o pacote de
  `REQUESTS_CA_BUNDLE` ou `CURL_CA_BUNDLE`, se o arquivo existe). Nunca desliga a conferência de certificado.
- O texto de erro de um pedido é sempre uma frase fixa da ferramenta, nunca a mensagem crua do sistema: ela
  pode trazer o endereço do proxy, que às vezes carrega senha.
- `--offline PASTA`: no lugar da rede, lê `PASTA/respostas.json`, um objeto `{"URL": "nome-do-arquivo"}`.
  É o modo dos testes. Pasta ou `respostas.json` que falta, JSON quebrado ou que não é objeto: erro de uso,
  código 2, antes de gravar qualquer coisa. `{}` e arquivo de 0 bytes são "nenhuma resposta". URL ausente é
  "não respondeu": erro de rede daquele pedido (no `--confere`, `bloqueada`).
  O valor também pode ser um objeto, para simular o que um arquivo sozinho não diz, com estes campos, todos
  opcionais: `{"arquivo": "nome", "status": 200, "tipo": "text/html; charset=utf-8", "demora": 0.5}`, ou
  `{"para": "https://outro.exemplo/pagina"}`, ou `{"falha": "nome"}`.
  `status` é o código da resposta (sem o campo, 200). `tipo` é o cabeçalho `Content-Type` (sem o campo, nenhum).
  `para` é um redirecionamento: com `para`, a resposta vale como 302, seja qual for o `status`; a ferramenta
  segue como seguiria na rede, e o destino também tem de estar em `respostas.json`. `arquivo` é o corpo, lido
  como bytes (sem o campo, corpo vazio); tem de morar dentro da PASTA (nome absoluto, com `..` ou que não
  existe: erro de rede daquela URL). `demora` são segundos (número de 0 a 3600): a ferramenta espera esse
  tempo de verdade, até o tempo limite do pedido. Se a demora cabe, a resposta chega depois dela; se passa do
  limite, o pedido acaba em "tempo esgotado" (não respondeu); se o teto do `--tempo` chega antes, em "não
  coube no tempo". `"falha": "nome"` simula o nome de site que não existe (no `--confere`, `erro`). Entrada
  torta (`status` que não é inteiro de 100 a 599, `demora` ou `falha` fora do que está aqui) é erro de rede
  daquela URL. Valem os mesmos limites da rede: 2 MB por resposta e 3 redirecionamentos. Não há nova
  tentativa no `--offline`: a resposta seria a mesma. A chave é a URL exata do pedido.

**Relógio de teste.** Se a variável de ambiente `INFO_AGORA` traz uma data-hora UTC (`AAAA-MM-DDTHH:MM:SSZ`),
as quatro ferramentas usam esse instante no lugar do relógio: na janela da coleta, em todo `gerada_em` e no
padrão de `--dia`. Com valor ilegível, a ferramenta para com `FALHA uso: INFO_AGORA ilegível` e código 2.
É só para os testes, que precisam da mesma saída em qualquer dia: a rotina e os workflows não definem a variável.

**Erro de uso.** Opção errada, valor ilegível ou falta de opção obrigatória: uma linha `FALHA uso: …` na saída
padrão e código 2, mesmo com `--json`. Nada é gravado. Abreviação de opção não vale (`--trab` não é `--trabalho`),
e pasta vazia em `--raiz` ou `--trabalho` é erro de uso.

**Sem rede e sem relógio.** `valida.py` e `publica.py` não usam a rede. Só usam o relógio em dois pontos:
o padrão de `--dia` e o `gerada_em` da edição.

---

## 1. `coleta.py` · baixa as manchetes e confere datas

```
python3 ferramentas/coleta.py [--dia D] [--trabalho P] [--horas N] [--tempo 90] [--por-feed 15] [--offline PASTA]
python3 ferramentas/coleta.py --confere [--trabalho P] [--tempo 60] [--offline PASTA]
```

| Opção | Padrão | Para quê |
|---|---|---|
| `--horas N` | a `janela_horas` de `P/contexto.json`, se o arquivo existe; senão 36 | janela: só entra manchete publicada nas últimas N horas. Inteiro de 1 a 720 |
| `--tempo S` | 90 (com `--confere`, 60) | teto de tempo total do comando, em segundos inteiros, de 1 a 3600. Ler os feeds também conta |
| `--por-feed N` | 15 | no máximo N manchetes, as mais novas, por feed. Inteiro de 1 a 200 |
| `--confere` | desligado | outro modo: confere as páginas de `urls.txt` (seção 1.1) |

`--horas`, `--por-feed` e `--tempo` pedem inteiro maior que zero, dentro do teto da tabela. Zero, negativo,
decimal ou acima do teto: erro de uso. Sem `--horas`, a janela vem do `contexto.json`: arquivo quebrado é
`FALHA`, código 1, sem gravar nada (seção 0), mesmo com `--dia` na linha de comando; `janela_horas` que não é
inteiro de 1 a 720 num arquivo legível vale 36, com aviso. A rede para um pouco antes do `--tempo` (10% dele,
até 5 segundos), para sobrar tempo de ler e gravar.

**Lê:** `dados/veiculos.json` (os `feeds` de formato `rss` ou `atom`, conferidos ou não, e os `sites` de cada
veículo) e `dados/regua.json` (siglas dos partidos, na ordem da régua). Não altera nenhum dos dois. Veículo torto
dentro de um mapa legível (sem `id` que sirva, `lado` ou `fatos` fora da régua) é pulado, com aviso: quem
confere o mapa campo a campo é o `valida.py --dados`.

**Grava:** `P/coleta.json` e `P/mesa.txt`.

**O que faz.**

1. Monta a fila de feeds: primeiro todos os de `conferido: true`, depois os outros. Em cada bloco, um feed de
   cada partido por vez, na ordem dos partidos da régua; dentro do partido, o primeiro feed de cada veículo
   antes do segundo de qualquer um (os veículos na ordem do mapa). Assim o corte do `--tempo` cai nos feeds
   nunca conferidos, e não sempre nos mesmos veículos. `coleta.json.feeds` é gravada na ordem da fila. Baixa
   em paralelo (8 por vez; 8 segundos por pedido). Feed que não coube no `--tempo` conta como erro (`não coube
   no tempo`), e também o que foi baixado mas não deu tempo de ler. Feed de formato que a coleta não lê (nem
   `rss` nem `atom`) é pulado: não aparece em `feeds[]` nem nas contas.
2. Lê RSS 2.0 e Atom (e também RSS 0.9x e 1.0, que têm a mesma forma de item). Recusa feed com `<!DOCTYPE` ou
   `<!ENTITY` (em qualquer ponto do texto, sem diferença de maiúsculas). Resposta que não se lê como RSS nem
   como Atom (HTML, XML quebrado, corpo vazio) é `erro`, com o motivo. Um feed que o leitor não previu
   também é `erro` daquele feed (`feed ilegível`) e não derruba a coleta.
3. De cada entrada tira título, resumo, endereço e data de publicação. RSS: `pubDate`; na falta, `dc:date`.
   Atom: `published`; só na falta dele, `updated`. O endereço do RSS é o `link`; na falta, o `guid` que não
   diz `isPermaLink="false"`.
4. Limpa: entidade de HTML vira o caractere; marca de HTML vira espaço (o conteúdo de `<script>` e `<style>`
   sai junto); saem comentário e caractere de controle ou invisível; espaços seguidos viram um, e o texto é
   aparado nas pontas. Depois corta o título em 200 caracteres e o resumo em 300: se cortou, fica com os 199
   (ou 299) primeiros, sem espaço no fim, mais `…`, e o total continua dentro do limite. No resumo, endereço
   de site vira `[link]`, e resumo igual ao título vira vazio.
5. Converte a data para UTC (sem fuso, a hora é lida como UTC). Descarta entrada sem título, sem data, sem
   endereço que comece com `http://` ou `https://` (endereço relativo também: a coleta não adivinha a base),
   com endereço que não passa nas regras da seção 0 ("Rede") ou da URL (`ESQUEMA.md`, seção 0), fora da janela
   ou mais de 2 horas no futuro. As duas bordas entram: exatamente N horas atrás e exatamente 2 horas à frente.
   Descarta também a entrada cujo site não bate com os `sites` do veículo no mapa (`ESQUEMA.md`, seção 0, "Site
   de uma URL"): um feed comprometido, ou de agregador, não põe na mesa o endereço de outro site com o nome do
   veículo. O que conta é o site do endereço da entrada, e não o do feed. O feed conta quantas caíram por isso
   em `fora_do_site` (só as que estavam na janela, com título e endereço que serviriam), e a saída padrão avisa:
   é por aí que o dono vê o feed legítimo que usa domínio de redirecionamento, para acrescentar esse domínio
   em `sites`.
6. Grava o endereço sem `#…` e sem parâmetros `utm_`. É o mesmo texto em `coleta.json` e em `mesa.txt`.
   Tira duplicatas: mesmo endereço limpo (`ESQUEMA.md`, seção 0), ou mesmo título no mesmo veículo (comparado
   depois da limpeza, sem diferença de maiúsculas nem de acentos). Entre duplicatas fica a mais nova; no
   empate, a do feed que está antes na fila (no mesmo feed, a que vem antes nele).
7. Marca `suspeito: true` quando título ou resumo parece dar ordem a quem lê. A lista do script traz, no
   mínimo: as ordens de ignorar, desconsiderar ou esquecer instruções, regras, orientações ou o prompt ("ignore
   as instruções", "ignore previous instructions", "disregard", "forget", "override"), "system prompt",
   "developer message", "prompt do sistema", "você é uma IA" (ou um assistente, um modelo, um agente), "you are
   an AI", "as an AI", "nota aos agregadores" (e aviso, recado, mensagem ou instrução a agregador, assistente,
   modelo, IA, robô, editor, agente), "note to AI" (e a assistentes, modelos, agentes, editores), "novas
   instruções", "new instructions", as marcas de conversa de modelo (`<|im_start|>`, `[INST]`, `### instruction`),
   e as mesmas ordens em espanhol, francês, alemão, russo, chinês e árabe. A comparação ignora maiúsculas e
   acentos, e é feita no título e no resumo já limpos e cortados. A lista é pista, não filtro: a manchete
   suspeita continua na mesa, só com o título. Quem decide se é notícia sobre o assunto ou ordem é o agente.
8. Sugere `categoria`: `ia` se título ou resumo traz termo da lista de IA do script; senão `geopolitica`. A lista
   traz, no mínimo: inteligência artificial (e artificial intelligence, intelligence artificielle, künstliche
   Intelligenz, intelligenza artificiale), aprendizado de máquina, machine learning, deep learning, rede neural,
   modelo de linguagem, language model, IA generativa, generative AI, chatbot, ChatGPT, GPT seguido de número,
   OpenAI, Anthropic, DeepMind, DeepSeek, Nvidia, Hugging Face, Midjourney, xAI, Grok, Qwen, GigaChat, Claude
   (com número, ou Opus, Sonnet, Haiku, Code), Gemini (com número, ou Pro, Ultra, Flash, Nano), Stable Diffusion,
   Mistral AI, superinteligência; os mesmos termos em russo, chinês, japonês, coreano, árabe, persa, hebraico,
   turco e hindi; e as siglas IA, AI, AGI, LLM, GPT e ИИ. A comparação ignora maiúsculas e acentos, menos nas
   siglas: elas só valem em maiúscula e como palavra solta ("ia" é verbo, "ai" é interjeição).
9. Agrupa manchetes do mesmo assunto em **histórias**, por nomes próprios e números em comum no título.
   O agrupamento é palpite: o agente confirma. O método é livre (o de hoje está descrito no comentário do
   `coleta.py`), mas a mesma entrada dá a mesma saída, com estas garantias: títulos iguais depois da limpeza
   (sem diferença de maiúsculas nem de acentos) ficam na mesma história; manchetes sem nome próprio nem número
   em comum no título ficam separadas. Em escrita sem maiúsculas (árabe, hebraico, coreano, chinês, japonês) não
   há como saber o que é nome: lá, palavras ou pares de letras em comum contam no lugar dos nomes.
10. Pontua cada história: 3 pontos por partido distinto mais 1 por veículo distinto (até 3). Assim, história
    que só um partido cobriu nunca passa à frente de história coberta por dois. A história é `ia` se a maioria
    das manchetes (mais da metade) é `ia`. Os ids `h01`, `h02`… seguem a ordem dos pontos, do maior para o
    menor; no empate, mais veículos, depois mais manchetes, depois a de manchete mais nova. As manchetes são
    numeradas da mais nova (`m0001`) para a mais velha.

**Formato de `coleta.json`.**

```json
{
  "versao": 1,
  "dia": "2026-11-20",
  "gerada_em": "2026-11-20T21:03:10Z",
  "janela_horas": 36,
  "resumo": {
    "feeds_ok": 61, "feeds_falhos": 7, "veiculos_ok": 48, "manchetes": 412, "suspeitas": 1,
    "partidos": {"ordem_global": 96, "centro_atlantico": 88, "bancada_talento": 31, "soberanistas": 74,
                 "eixo_revisionista": 69, "centrao": 40, "independentes": 14}
  },
  "feeds": [
    {"veiculo": "bbc", "url": "https://…", "estado": "ok", "itens": 15, "fora_do_site": 0, "erro": ""}
  ],
  "manchetes": [
    {"id": "m0001", "historia": "h01", "veiculo": "bbc", "lado": "centro_atlantico", "fatos": "alta",
     "titulo": "…", "resumo": "…", "url": "https://…", "publicado_em": "2026-11-20T14:02:00Z",
     "categoria": "geopolitica", "suspeito": false}
  ],
  "historias": [
    {"id": "h01", "pontos": 9, "categoria": "geopolitica", "partidos": ["centro_atlantico", "soberanistas"],
     "veiculos": 7, "manchetes": ["m0001", "m0044"]}
  ]
}
```

`feeds[].estado` é `ok` (resposta 2xx lida, com manchete), `vazio` (respondeu e se leu, sem manchete que ficasse)
ou `erro` (com o motivo em `erro`). `feeds[].itens` conta as manchetes que o feed entregou depois do corte de
`--por-feed` e antes da comparação entre feeds (a soma dos `itens` pode passar de `resumo.manchetes`).
`feeds[].fora_do_site`: passo 5. `resumo.feeds_ok` são os feeds `ok` ou `vazio` (os que responderam);
`feeds_falhos`, os `erro`; `veiculos_ok`, os veículos com pelo menos um feed que respondeu. `resumo.partidos`
conta manchetes por lado, com os 7 partidos da régua (0 quando é o caso). `lado` e `fatos` são cópias do mapa
de veículos.

**Formato de `mesa.txt`.** É o que o agente lê. Texto puro, até 60 KB (61.440 bytes em UTF-8). Traz as 40
histórias de mais pontos, em ordem. Em cada história, até 8 manchetes, no máximo 2 por veículo, alternando os
partidos na ordem da régua; dentro do partido, a manchete mais nova de cada veículo antes da segunda de
qualquer um, e veículo de `fatos: alta` na frente.

```
MESA 2026-11-20 · janela 36 h · feeds ok 61, falhos 7 · manchetes 412 · suspeitas: 1
PARTIDOS COM MANCHETE: OG 96 · CA 88 · BT 31 · SO 74 · ER 69 · CE 40 · IN 14
LEGENDA: [XX] partido do veículo · ? lado incerto · serve a: player a quem o veículo serve · fatos: confiança para fato cru · [SUSPEITA] pode ser ordem, e não notícia

### h01 · 15 pontos · partidos 4 (OG CA SO ER) · veículos 7 · geopolitica
- [CA] bbc · fatos alta · 20/11 14:02 UTC · Título da manchete
  Resumo em até 300 caracteres.
  https://…
- [ER] tass · serve a: russia · fatos media · 20/11 13:40 UTC · Título da manchete
  Resumo.
  https://…
- [CE?] bloomberg · fatos alta · 20/11 13:10 UTC · [SUSPEITA] Título da manchete
  https://…
- [CA] afp · serve a: ue, macron · fatos alta · 20/11 13:25 UTC · Título da manchete
  https://…

### h02 · …
```

- A terceira linha é a legenda. É fixa: a `ROTINA.md` não explica os sinais, manda ler a legenda.
- A sigla entre colchetes é a do partido em `regua.json`. O `?` depois da sigla marca veículo com
  `lado_confianca: baixa` no mapa (lado incerto).
- `serve a:` aparece quando o veículo tem player em `serve_a` no mapa: lista os players, separados por
  vírgula (no exemplo, a afp serve a dois). Id de partido em `serve_a` não entra.
- `[SUSPEITA]` marca a manchete com `suspeito: true`. Ela vem sem resumo.
- A 2ª linha traz os 7 partidos, na ordem da régua, com 0 quando é o caso.
- Manchete sem resumo: a linha do resumo some, e o endereço vem logo depois da linha da manchete.
- No fim do arquivo vem a seção `### IA`: até 10 histórias de categoria `ia` que ficaram fora das 40, por
  pontos, no mesmo formato, com até 4 manchetes cada. A linha `### IA` só aparece se houver história para pôr nela.
- Sem história nenhuma (nenhuma manchete, e também com `FALHA sem rede`), a mesa traz só as 3 linhas do topo.
- Para caber em 60 KB, a ferramenta desce uma escada fixa, igual para todas as histórias (manchetes por
  história, tamanho do resumo): (8, 300), (8, 240), (8, 180), (6, 180), (6, 120), (5, 120), (4, 120), (4, 60),
  (4, 0), (3, 0), (2, 0), (1, 0). Vale o primeiro degrau que cabe (na seção IA, no máximo 4 manchetes em
  qualquer degrau). Se nem o último cabe, saem histórias inteiras do fim: primeiro as da seção IA, depois as 40
  de cima, de baixo para cima. As 3 linhas do topo sempre ficam, e a história de mais pontos nunca sai antes
  de uma de menos. A saída padrão avisa quando a mesa foi encurtada.

**Veredito e código.** "Responderam" são os feeds `ok` ou `vazio`. O número vai para o singular com 1 ("1 feed",
"1 partido"). O "N histórias" do `OK` é o número de histórias na parte de cima da mesa (até 40).

| Situação | Última linha | Código |
|---|---|---|
| 8 feeds ou mais responderam e 3 partidos ou mais têm manchete | `OK 61 feeds, 412 manchetes, 40 histórias` | 0 |
| menos que isso, mas há manchete | `PARCIAL 5 feeds, 2 partidos` | 3 |
| feeds responderam e não há manchete nenhuma | `PARCIAL 13 feeds, 0 partidos` | 3 |
| nenhum feed respondeu | `FALHA sem rede: 0 feeds` | 4 |
| `veiculos.json` ou `regua.json` ilegível, ou `contexto.json` quebrado (nada é gravado) | `FALHA …` | 1 |

### 1.1 `coleta.py --confere` · a data das páginas abertas

Serve à regra T3 do `ESQUEMA.md`: a data de uma fonte achada por busca não pode depender só do que o agente
escreveu. Roda depois que o rascunho está pronto, antes do `publica.py edicao`.

**Lê:** `P/urls.txt` e `P/coleta.json`. **Grava:** `P/conferencia.json`. Não lê nem altera o repositório, e não
lê o `contexto.json`. Sem `coleta.json`, ou com ele ilegível, toda URL de `urls.txt` conta como nova (ilegível:
com aviso).

**`urls.txt`.** Uma URL por linha. Linha em branco é ignorada; linha que começa com `#` (no primeiro
caractere) é comentário; espaço nas pontas sai. Linha que não é URL (`ESQUEMA.md`, seção 0) é pulada, com
aviso. URL repetida (mesmo endereço limpo) conta uma vez, e a que já está em `coleta.json` (mesmo endereço
limpo) não é pedida. A URL pedida e gravada é o texto da linha, mesmo depois de redirecionar: é ela que a
regra T3 procura.

**O que faz.** Para cada URL de `urls.txt` que não está em `coleta.json` (até 30; 8 por vez; 8 segundos cada),
baixa a página e procura a data de publicação em dois lugares, nesta ordem:
`<meta property="article:published_time">` e `"datePublished"` no bloco de dados da página (JSON-LD).
Não segue link, não roda script, não lê mais nada da página. As URLs além da 30ª ficam fora de
`conferencia.json`, e a última linha diz quantas: `…; 5 URLs fora do teto de 30`.

- A página é lida quando não há `Content-Type`, ou quando ele é `text/html` ou `application/xhtml+xml` (o
  `; charset=…` não conta). Com outro tipo, ela "não é HTML": `publicado_em` é `null`.
- O `<meta>` vale com `property` ou com `name`, em qualquer ordem de atributos. No JSON-LD vale a primeira
  `datePublished` de um objeto cujo `@type` contém `Article` ou `Posting`, em qualquer bloco da página (também
  dentro de `@graph`); na falta, a primeira que houver. Bloco de JSON quebrado: o campo é procurado no texto do
  bloco. Data com ano fora de 1990 a 2100 é ignorada. A data achada vira o dia em UTC.

```json
{
  "versao": 1,
  "gerada_em": "2026-11-20T21:22:10Z",
  "paginas": [
    {"url": "https://…", "estado": "ok", "publicado_em": "2026-11-20"},
    {"url": "https://…", "estado": "ok", "publicado_em": null},
    {"url": "https://…", "estado": "bloqueada", "publicado_em": null},
    {"url": "https://…", "estado": "erro", "publicado_em": null}
  ]
}
```

| `estado` | Quando | Efeito na regra T3 |
|---|---|---|
| `ok` | a página respondeu com 2xx (até 2 MB). `publicado_em` é a data achada (dia em UTC), ou `null` se a página não traz nenhum dos dois campos, ou não é HTML | com data: a fonte tem data conferida, e o `publicado_em` do rascunho tem de bater. Sem data: a fonte vale, sem data conferida |
| `bloqueada` | o site recusou a máquina ou não respondeu: 401, 403, 429, 5xx, outros 4xx, tempo esgotado, falha de conexão, de certificado ou de proxy, redirecionamento recusado (ou mais de 3), resposta maior que 2 MB, URL ausente no `--offline` | a fonte vale, sem data conferida |
| `erro` | a página não existe (códigos 404 e 410), o nome do site não existe, ou a URL nem pode ser pedida (regras da seção 0, "Rede": número de IP, `localhost`, nome interno) | a URL não vale como fonte |

**Veredito e código.** `OK 9 páginas: 6 com data, 2 bloqueadas, 1 com erro`, código 0. A linha tem sempre as
três partes; página `ok` sem data não ganha parte própria; com 1, o singular ("1 página", "1 bloqueada"). Sem
`urls.txt`, ou sem URL nova: `OK 0 páginas`, código 0. Nenhuma página respondeu (nenhuma com estado `ok`):
`FALHA sem rede: 0 páginas`, código 4; o `conferencia.json` sai com as páginas como `bloqueada`. Essa
regra vale mais que a tabela: até o nome de site que não existe vira `bloqueada`, porque numa máquina sem rede
todo nome parece não existir. Continuam `erro` só a URL que nem pode ser pedida e a página que respondeu 404 ou
410: as duas não dependem da rede (a 404 é um servidor dizendo que a página não existe). Se a
coleta também ficou sem rede, vale o trecho "Máquina sem rede" da regra T3: a edição sai em modo `busca`, sem
gatilho de nível 3 ou mais.

---

## 2. `indicadores.py` · baixa preços e calcula gatilhos de preço

```
python3 ferramentas/indicadores.py [--dia D] [--trabalho P] [--tempo 45] [--offline PASTA]
```

`--tempo S` é o teto de tempo total, em segundos inteiros, de 1 a 3600 (padrão 45), como na coleta. Zero,
negativo, número com casa decimal ou texto é erro de uso.

**Lê:** `dados/indicadores.json` (o catálogo: quais indicadores, em que ordem, e as fontes de cada um; formato
no `ESQUEMA.md`, seção 14) e `dados/regua.json` (os critérios `precos` de `niveis_alerta`).
Não altera nenhum dos dois. **O script não traz endereço nenhum:** todo endereço mora no catálogo, também o
modelo de endereço dos contratos futuros (campo `contratos`). O script traz só os leitores e a conta.

**Grava:** `P/indicadores.json`, sempre que chega a rodar (seção 0). Catálogo ou régua ilegível, `contexto.json`
quebrado e erro de uso não gravam nada: o arquivo de antes, se havia, fica como estava.

**Leitores.** Cada leitor recebe a resposta de uma fonte e devolve a **série**: pares (data, valor), em ordem
crescente de data. Cada valor é multiplicado pelo `fator` da fonte, se houver. O cálculo é o mesmo para todos.

| Leitor | Formato | Como lê |
|---|---|---|
| `fred_csv` | CSV | cabeçalho `observation_date,ID`; cada linha é `AAAA-MM-DD,valor`; linha com valor vazio (é assim que o FRED marca o feriado) ou `.` é pulada |
| `yahoo_chart` | JSON | em `chart.result[0]`: `timestamp[]` (segundos Unix) e `indicators.quote[0].close[]`; par com `close` `null` é pulado (o índice do dólar traz `null` nos domingos). **A data é o dia do carimbo no fuso da bolsa:** `meta.exchangeTimezoneName`, pela base de fusos da máquina; sem esse campo, sem a base, ou com nome que a base não conhece, o desvio fixo `meta.gmtoffset` (segundos); sem os dois, o dia em UTC. O último carimbo pode ser a hora da última cotação, e não o começo do pregão: vale o dia dele do mesmo jeito. O pedido leva `User-Agent` de navegador |
| `bcb_sgs` | JSON | lista de `{"data": "DD/MM/AAAA", "valor": "5.8889"}`; dia sem pregão no Brasil não vem |
| `eia_v2` | JSON | `response.data[]`, com `period` (`AAAA-MM-DD`) e `value` (texto, que perde o zero do fim: `"92.9"`); vem do mais novo para o mais velho, e outras chaves (como `warnings`) podem vir antes de `response`. **Nenhuma fonte do catálogo usa este leitor hoje:** a única pedia chave de demonstração e saiu. O leitor fica para o dono que tiver chave própria |
| `fao_csv` | CSV | 2 linhas de título; depois o cabeçalho `Date,Food Price Index,…`; a data é `AAAA-MM` (vira dia 1); lê a 2ª coluna. Linha que não começa com `AAAA-MM` é pulada, e também a linha com a 2ª coluna vazia. O arquivo real começa com BOM (U+FEFF), tem uma linha só de vírgulas logo abaixo do cabeçalho e uma fileira de vírgulas no fim de cada linha: nada disso atrapalha |
| `cnbc_chart` | JSON | em `barData.priceBars[]`: a data são os 8 primeiros caracteres de `tradeTime` (texto `AAAAMMDD…`, como `"20261120000000"`) e o valor é `close`, que vem como texto (`"448.7500"`) e pode vir como número. Barra sem um dos dois é pulada |

Em todos os leitores, ponto com valor zero, negativo, infinito ou que não se lê como número é ponto sem valor.
Dois pontos na mesma data: fica o que vem por último na resposta, entre os que têm valor.

Leitor que o catálogo cita e o script não conhece: a fonte é pulada, com aviso. Leitor novo exige mudar o script.

**O que faz.**

1. Percorre o catálogo, 4 indicadores em paralelo. Em cada um, tenta as `fontes` na ordem do catálogo:
   baixa a `url` (10 segundos por pedido) e entrega a resposta ao `leitor`.
2. Descarta ponto sem valor e ponto com data depois de `--dia`. A fonte **serve** se sobrou ao menos 1 ponto
   e o último valor, já com o `fator` e antes de arredondar, está dentro da `faixa` do catálogo (as duas
   bordas valem).
3. Fica com a primeira fonte que serve **e não está defasada**. Se todas as que servem estão defasadas,
   fica com a de data mais nova; no empate de data, a primeira do catálogo. Nunca mistura pontos de duas fontes.
4. Calcula, sempre dentro da série da fonte escolhida: `valor` (último ponto, arredondado a `casas`); `data`;
   `variacao_pct` (último ponto sobre o anterior); `variacao_7d_pct` (último ponto sobre o ponto mais novo
   com data de 7 a 10 dias corridos antes da dele; sem ponto nessa faixa, `null`). Variações com 1 casa.
   Sem ponto para comparar, a variação é `null`. Em indicador `mensal`, `variacao_7d_pct` é sempre `null`.
   **Ponto fora da série.** Ponto de base (o anterior, ou o de 7 a 10 dias) com valor fora de 0,5 a 2 vezes os
   **dois** vizinhos dele na mesma série (o ponto antes e o ponto depois; as bordas valem) é tique da fonte,
   como um decimal deslocado: a variação que o usa sai `null` (o diário cai em "sem base de 7 dias", se for a
   de 7 dias), e um texto vai para `avisos`: `"brent: ponto de 16/11 fora da série: variação de 7 dias sem
   base."` (ou "variação sobre o ponto anterior sem base"). Não há teto de variação: um choque real, que move o
   último ponto, continua valendo. Não olha a segunda fonte.
   **Arredondamento.** A variação é calculada sobre os pontos crus da série, já com o `fator` (e não sobre o
   `valor` arredondado), em decimal, e só o resultado é arredondado: a metade vai para longe do zero (0,25
   vira 0,3; −0,25 vira −0,3). Antes, a conta é levada a 9 casas, para sumir o resíduo de conta binária. O
   `valor` é arredondado a `casas` pela mesma regra. É a variação arredondada que se compara com o limiar
   (passo 7). Se a fonte escolhida tem o campo `contratos`, as variações podem ser medidas no contrato:
   ver "Troca de contrato", logo abaixo da lista.
5. `defasado`: cotação com mais de 4 dias corridos antes de `--dia` (mensal: mais de 62).
6. Indicador sem fonte que sirva sai com `valor`, variações e `data` em `null`, `defasado: true`,
   `confirmado: false` e `fonte` igual à primeira do catálogo. Os outros seguem. Nunca repete número de outro dia.
   Com `FALHA sem rede`, a "saída vazia" da seção 0 é esta: `indicadores` traz todos os itens do catálogo,
   todos assim, sem valor.
7. Calcula `gatilhos`: para cada indicador não defasado, aplica os critérios de preço da régua
   (variação já arredondada maior ou igual a `alta_minima_pct`; só alta conta; variação `null` não cumpre).
   Critério de janela `1d` só vale no dia da cotação: `data` igual a `--dia`. Em fim de semana, a alta de
   sexta não vira gatilho de novo. Fica com o critério de maior nível por indicador; no empate de nível entre
   a janela de 1 dia e a de 7 dias, vale a de 7 dias, no `texto` e na confirmação. Critério de janela que a
   ferramenta não conhece é pulado, com aviso.
8. Confirma a alta forte. Se o critério que ficou é de nível 3 ou 4, baixa a fonte seguinte do catálogo que
   serve para o mesmo indicador e calcula a mesma variação nela. A "fonte seguinte" é a primeira que serve
   **depois** da escolhida, na ordem do catálogo: fonte anterior à escolhida não confirma, e só uma fonte é
   consultada. **A segunda fonte só confirma se a `data` dela não é mais de 4 dias corridos anterior à `data`
   da escolhida;** senão, `confirmado` é `false`, e a busca para nela: dado velho não confirma nem desmente.
   `confirmado` é `true` se essa segunda fonte cumpre critério de preço de nível 2 ou mais na mesma janela
   (a regra do `1d` no dia da cotação vale também nela). Sem segunda fonte que sirva, ou sem confirmação,
   `confirmado` é `false`: o gatilho sai com o `criterio` de nível 2 do domínio, o limiar do texto é o do
   critério de nível 2 da mesma janela, e o `texto` termina com "Alta maior sem confirmação de segunda fonte."
   Nos outros casos, `confirmado` é `false`. Se o teto do `--tempo` corta o pedido da segunda fonte, fica o que
   já estava medido: `confirmado: false`, critério de nível 2.

**Troca de contrato** (passo 4, quando a fonte escolhida tem `contratos`). O endereço de "contrato mais
próximo" de uma bolsa de futuros (`BZ=F`, `ZC=F`…) muda de contrato perto do vencimento, e a série dá um degrau
que não é alta de mercado. A ferramenta não adivinha o contrato pelo nome: compara séries. Só para a fonte
escolhida, e só se ela tem `contratos` (`ESQUEMA.md`, seção 14, regra C6):

1. Candidatos: os 4 primeiros contratos de `meses` com mês igual ou posterior ao mês de `--dia`, na ordem
   (em `--dia` 2026-11-23, com `meses` `HKNUZ`: Z26, H27, K27, N27). O código é a letra do mês e o ano com 2
   dígitos; o endereço é o `modelo` com `{c}` trocado pelo código.
2. Baixa cada candidato, na ordem, com o mesmo leitor, o mesmo `fator`, a mesma `faixa` e o mesmo cabeçalho
   da fonte (10 segundos por pedido, dentro do teto do `--tempo`). Candidato que não responde ou não serve
   (passo 2) é pulado. O candidato **casa** se o último ponto dele tem a mesma data do último ponto da série
   escolhida e os dois valores diferem em até 0,5% do valor da série escolhida. Para no primeiro que casa.
3. Com o candidato que casou, anda para trás nas datas que as duas séries têm. Enquanto os valores diferem
   em até 0,5%, a série escolhida já estava nesse contrato. A primeira data em que diferem mais que isso
   marca a troca; o **dia da troca** é a data seguinte a ela entre as que as duas têm (o primeiro dia da
   série já no contrato). Sem data que difere, não houve troca na janela, e nada muda.
4. Se o ponto de base de alguma variação (o ponto anterior, ou o ponto de 7 a 10 dias) tem data igual ou
   anterior à data que marca a troca, **as duas variações são calculadas na série do contrato**, nos mesmos
   dias (o último ponto e os mesmos pontos de base), pela regra de arredondamento do passo 4. `valor`, `data`
   e `fonte` não mudam.
5. Nenhum candidato casou, o tempo acabou, a série do contrato não tem os pontos de base, a troca foi antes
   dos dois pontos de base, `contratos` fora da regra C6, ou qualquer outra falha: nada muda, as variações vêm
   da série escolhida. Esta etapa nunca derruba o indicador; o que deu errado sai numa linha de aviso.
6. Cada indicador medido no contrato ganha um texto na lista `avisos`, na raiz de `indicadores.json`:
   `"milho: variações medidas no contrato H27, porque a série trocou de contrato em 23/11."`. A lista sai na
   ordem do catálogo (no mesmo indicador, o aviso de ponto fora da série vem antes), vazia quando nenhum foi
   medido no contrato nem teve ponto fora da série. O `publica.py` não copia essa lista.

A segunda fonte (passo 8) é medida na série dela, sem esta etapa.

Para o critério de 7 dias funcionar, a resposta da fonte tem de cobrir pelo menos 11 dias corridos
(regra C4 do `ESQUEMA.md`). Isso depende do endereço que está no catálogo, não do script.

**Formato de `indicadores.json`.**

```json
{
  "versao": 1,
  "dia": "2026-11-20",
  "gerada_em": "2026-11-20T21:03:40Z",
  "indicadores": [
    {"id": "brent", "nome": "Petróleo Brent", "dominio": "energia", "valor": 78.4, "unidade": "US$ por barril",
     "variacao_pct": 1.3, "variacao_7d_pct": 6.1, "data": "2026-11-20", "defasado": false, "confirmado": false,
     "fonte": {"nome": "…", "url": "https://…"}}
  ],
  "gatilhos": [
    {"criterio": "energia.2", "ref": "brent", "texto": "Petróleo Brent subiu 6,1% em 7 dias, até 20/11 (limiar: 5%)."}
  ],
  "falhas": [
    {"id": "gas_natural", "erro": "todas as fontes falharam"},
    {"id": "milho", "erro": "sem base de 7 dias"}
  ],
  "avisos": [
    "trigo: variações medidas no contrato H27, porque a série trocou de contrato em 20/11."
  ]
}
```

`indicadores` traz todos os indicadores do catálogo, na ordem do catálogo, já no formato da edição
(`ESQUEMA.md`, seção 3). `nome`, `dominio` e `unidade` são cópias do catálogo. Cada item de `gatilhos` já
está no formato de `alerta.dominios[].gatilhos`: o `publica.py edicao` copia para o domínio do `criterio`.
O agente lê a lista para escrever a `leitura`, e não copia nada.
O `texto` do gatilho traz sempre a data da cotação. Na janela de 7 dias: "Petróleo Brent subiu 6,1% em 7
dias, até 20/11 (limiar: 5%)."; na de 1 dia: "Dólar em reais subiu 1,6% no dia 20/11 (limiar: 1,5%)." A
variação sai sempre com 1 casa ("5,0%"); o limiar, sem casa inútil ("5%", "1,5%").

`falhas` traz só dois textos: "todas as fontes falharam" (indicador sem valor) e "sem base de 7 dias"
(indicador diário com valor e `variacao_7d_pct` `null`). O indicador defasado não entra em `falhas`: aparece
no veredito ("sem dado") e em `defasado: true`. `avisos` é a lista da troca de contrato e do ponto fora da
série (acima).

**Veredito e código.** Obrigatório é o indicador com `obrigatorio: true` no catálogo. "N indicadores" são os
que saíram com valor (singular com 1: "1 indicador", "1 gatilho").

| Situação | Última linha | Código |
|---|---|---|
| todos os obrigatórios têm valor, não estão defasados e têm a variação de 7 dias | `OK 11 indicadores, 1 gatilho de preço` | 0 |
| falta ou está defasado algum obrigatório | `PARCIAL sem dado: milho` | 3 |
| obrigatório citado em critério de 7 dias saiu com valor, em dia, mas com `variacao_7d_pct` `null` | `PARCIAL sem base de 7 dias: brent, trigo` | 3 |
| nenhum indicador veio | `FALHA sem rede: 0 indicadores` | 4 |
| catálogo ou régua ilegível | `FALHA …` (nada é gravado) | 1 |

Com as duas situações de `PARCIAL` ao mesmo tempo, a última linha junta as duas:
`PARCIAL sem dado: milho; sem base de 7 dias: brent`. O indicador sem dado entra só em "sem dado", nunca
também em "sem base de 7 dias".

---

## 3. `valida.py` · confere edição e dados

Um modo por chamada. Nunca grava arquivo. Sem rede. Só olha o repositório.

```
python3 ferramentas/valida.py
python3 ferramentas/valida.py --tudo [--base REF] [--dia D]
python3 ferramentas/valida.py --dados
python3 ferramentas/valida.py --edicao ARQ [--anterior ARQ]
```

**Sem opção nenhuma, vale `--tudo`.** É assim que o workflow `valida.yml` chama o validador.

| Modo | Lê | Confere |
|---|---|---|
| `--dados` | `dados/regua.json`, `players.json`, `veiculos.json`, `vetores.json`, `indicadores.json`; `edicoes/indice.json` se existir | estrutura e referências de cada um: ids únicos; partidos, times, tipos e temas que existem; DNA válido; 5 domínios, cada um com `canal`, e 5 níveis com códigos `dominio.nivel`; `campos`, `forcas`, `evidencias`, `times_avanco`, `conflito` e `sites_oficiais` da régua, com ids que existem; campos do mapa de veículos (regras M1 e M2); catálogo de indicadores (regras C1 e C2, `leitor` da lista, `faixa` e `fator` válidos; C5 como aviso); vetores e anulações bem formados; URLs; com git na raiz, nenhum arquivo que dá ordem a agente (`AGENTE`, `ESQUEMA.md`, seção 10) |
| `--edicao ARQ` | o arquivo, `dados/*.json` | todas as regras R, inclusive as marcadas **(dia)**. Arquivo dentro de `edicoes/`: também as regras H, contra as outras edições. Arquivo fora: H1 sem histórico. `--anterior ARQ` força a edição anterior (testes): o histórico passa a ser só ela; a H2 confere o que aponta para ela e não acusa as outras datas; `anula_vetor` é conferido contra `dados/vetores.json`. Os dados só barram a conferência quando não servem de base (arquivo ilegível, lista essencial que falta); os avisos C5 não aparecem neste modo |
| `--tudo` | tudo acima e todos os `edicoes/*.json`, `*.md`, `feed.xml` | `--dados`; as regras R e H em cada edição, sendo que as **(dia)** só na edição de `--dia`, se existir; índice igual aos arquivos; cada edição com seu `.md` (basta o arquivo existir: o texto não é comparado; `.md` com nome de data e sem a edição é erro); `feed.xml` bem formado. Com edições, sem `indice.json` é erro; sem `feed.xml`, só aviso. Arquivo `.json` ou `.md` de nome estranho em `edicoes/` (nem data, nem `indice.json`) só avisa (`ARQUIVO`): pode ser do dono, e a rotina não consegue criar um (G4). Com `--base REF`, também as regras G1 a G4 |

As regras T (pasta de trabalho) não são do `valida.py`: só o `publica.py edicao` as confere.

**Edição do dia e edição de arquivo.** Edição publicada é registro. O dono vai revisar o mapa de veículos,
os limiares da régua e o catálogo, e as edições antigas não podem quebrar por isso. Por isso `--tudo` só
aplica as regras **(dia)** (as que cruzam a edição com `dados/veiculos.json`, com os limiares de preço e com
o catálogo) à edição cuja `data` é igual a `--dia`. Nas outras, aplica as demais regras. Se o dono mudar o
mapa no mesmo dia, depois da edição, o validador pode acusar a edição do dia; no dia seguinte, não acusa mais.

**Regras G** (só com `--base REF`). `REF` é qualquer revisão do git: um nome, como `origin/main`, ou o
identificador de um commit. Conferem o que a rotina mudou, antes ou depois do commit.
Comparam os arquivos do repositório, como estão no disco, com `REF`: o conteúdo de cada arquivo em `REF`
para G1 a G3; para G4, a lista do que difere de `REF` pelo conteúdo (é a lista de `git diff --name-only REF`
mais os arquivos novos de `git status --porcelain --untracked-files=all`). O validador a calcula sem
`git diff` nem `git status`, que podem regravar o índice do git: lê a árvore de `REF` (`git ls-tree`), os
arquivos do disco (`git ls-files --cached --others --exclude-standard`) e o identificador de cada um
(`git hash-object`). Arquivo só "tocado", com o mesmo conteúdo, não conta como mudado.
Caminhos permitidos (G4): em `edicoes/`, só `AAAA-MM-DD.json`, `AAAA-MM-DD.md` e `indice.json`, sem subpasta;
`feed.xml`, `dados/players.json` e `dados/vetores.json`. Arquivo ignorado pelo `.gitignore` não conta.
A edição de `estado: falha` da base pode ser trocada por qualquer edição do mesmo dia, inclusive outra falha
(G3); não pode sumir.
**A rotina não altera `dados/veiculos.json`:** o mapa é do dono (`ESQUEMA.md`, seção 15).
Sem `--base`, mudança do dono em `dados/` ou em `ferramentas/` não é erro: é assim que o `valida.yml` chama.

**Formato da saída.** Uma linha por problema, `ERRO REGRA caminho: problema. Conserto.` ou `AVISO REGRA
caminho: …`. Em `--tudo` e em `--dados`, o caminho começa com o nome do arquivo, ligado ao campo por dois-pontos,
sem espaço: `edicoes/2026-11-20.json:radar[2].confianca`. Os erros saem primeiro e os avisos depois, cada grupo
na ordem dos arquivos e dos campos.

`REGRA` é um código do ESQUEMA (R00 a R23, H2, H3, T1 a T5, G1 a G4, M1, M2, C1, C2, C5) ou um destes sete,
para o que o ESQUEMA manda conferir sem dar número:

| Código | Quando sai |
|---|---|
| `ARQUIVO` | arquivo que não existe ou não deu para ler (JSON ilegível, maior que 2.000.000 de bytes, atalho, pasta no lugar de arquivo); arquivo de nome estranho em `edicoes/` (aviso) |
| `DADOS` | estrutura de `dados/*.json` fora das regras M e C; dados que não servem de base, e por isso a edição não foi conferida |
| `INDICE` | `edicoes/indice.json` fora da forma do ESQUEMA, seção 11, ou diferente do que os arquivos dão |
| `MD` | edição sem o `.md`, ou `.md` sem a edição |
| `FEED` | `feed.xml` mal formado (ou ausente, como aviso), ou com `link` que não é `http`, `https` nem relativo: o esquema é lido como o leitor de feed lê, depois de tirar espaço e caractere de controle (`java&#9;script:` é `javascript:`) |
| `GIT` | `--base` sem git na raiz, com revisão que não existe, ou com o git falhando |
| `AGENTE` | em `--tudo` e em `--dados`, com git na raiz: arquivo acompanhado pelo git (`git ls-files`, nunca o disco) chamado `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md` ou `.mcp.json`, ou dentro de uma pasta `.claude/`; `.claude/settings.json` só passa com uma chave só, `attribution` (`ESQUEMA.md`, seção 10). Aviso, se o git não listar os arquivos |

A saída tem teto: 60 erros por arquivo e 300 linhas de erro (e 300 de aviso) por chamada. O que passa disso vira
uma linha só, que diz quantos ficaram de fora; o veredito conta as linhas impressas.

```
ERRO R08 radar[2].confianca: é 'alta', o teto pelas fontes é 'media'. Troque para 'media' ou acrescente fonte do outro campo.
ERRO R13b alerta.dominios[0].gatilhos[1].ref: nível 3 exige principal, e 'r4' é do radar. Baixe o critério para o nível 2 ou tire o gatilho.
AVISO H3 principais[1].titulo: quase igual ao de 2026-11-19/p2. Se continua a história, use continuacao_de.
FALHA 2 erros, 1 aviso
```

A última linha é sempre `OK 0 erros, N avisos` ou `FALHA N erros, M avisos`, com N e M iguais às linhas `ERRO`
e `AVISO` impressas, e o singular só com 1 (`1 erro`, `1 aviso`). Aviso não muda o código de saída.

Com `--json`: a forma comum da seção 0 (`ok`, `codigo`, `veredito`, `linhas`) mais duas listas,
`{"ok": false, "codigo": 1, "veredito": "FALHA 2 erros, 1 aviso", "linhas": [ … ], "erros": [{"regra": "R08",
"caminho": "…", "mensagem": "…"}], "avisos": [ … ]}`. Erro de uso sai em texto, mesmo com `--json`.

**Situação, última linha e código.**

| Situação | Última linha | Código |
|---|---|---|
| nenhum erro (avisos não contam) | `OK 0 erros, N avisos` | 0 |
| erro em regra do ESQUEMA, nos dados, no índice, no `.md` ou no feed | `FALHA N erros, M avisos` | 1 |
| arquivo que não existe ou ilegível (`ERRO ARQUIVO`) | `FALHA N erros, M avisos` | 1 |
| dados que não servem de base: as edições não são conferidas (`ERRO DADOS`) | `FALHA N erros, M avisos` | 1 |
| `--base` numa raiz sem git, com revisão que não existe, ou com o git falhando (`ERRO GIT`) | `FALHA N erros, M avisos` | 1 |
| revisão de `--base` vazia ou que começa com `-` | `FALHA uso: …` | 2 |
| dois modos juntos (`--tudo`, `--dados`, `--edicao`) | `FALHA uso: …` | 2 |
| `--trabalho`, ou outra opção que não existe | `FALHA uso: …` | 2 |
| `--anterior` sem `--edicao`; `--base` fora do modo `--tudo` | `FALHA uso: …` | 2 |
| `--raiz` com pasta que não existe (seção 0) | `FALHA uso: …` | 2 |
| `INFO_AGORA` ilegível | `FALHA uso: INFO_AGORA ilegível` | 2 |
| erro inesperado do próprio validador | `FALHA interna: Tipo: mensagem` | 1 |

`--dia` é aceito e ignorado em `--dados` e em `--edicao`. Em `--edicao`, caminho relativo vale a partir da pasta
de onde se chama; se não existe ali, a partir de `--raiz`. "Dentro de `edicoes/`" quer dizer a pasta `edicoes`
da `--raiz`.

---

## 4. `publica.py` · contexto, publicação e edição de falha

Sem rede. Quatro subcomandos.

```
python3 ferramentas/publica.py contexto [--dia D] [--trabalho P] [--raiz PASTA] [--json]
python3 ferramentas/publica.py edicao   [--dia D] [--trabalho P] [--corta ID[,ID]] [--simula] [--url-base URL] [--raiz PASTA] [--json]
python3 ferramentas/publica.py falha --motivo "TEXTO" [--dia D] [--trabalho P] [--url-base URL] [--raiz PASTA] [--json]
python3 ferramentas/publica.py refaz    [--url-base URL] [--raiz PASTA] [--json]
```

Todas as opções vêm **depois** do subcomando, as comuns também. Sem subcomando, ou com opção antes dele: erro
de uso. O `refaz` aceita `--dia` e `--trabalho`, que são comuns, e não usa nenhum dos dois (não cria a pasta).

Com `--json`, além da forma da seção 0: `contexto` traz `contexto` (o objeto gravado) e `arquivos`; `edicao` e
`falha` trazem `dia` e, quando chegam a conferir, `erros` e `avisos` (os objetos do `valida.py`, seção 3) e,
quando passam, `estado`, `nivel` e `arquivos` (com `--simula`, `gravaria`); `refaz` traz `arquivos`.

JSON gravado pelo `publica.py` segue a seção 0. Uma metade solta de par substituto (o código de um emoji escrito
pela metade, de `\ud800` a `\udfff`) que já está num arquivo do repositório, mexido à mão, é escrita como
`\uXXXX`: lida de volta, dá o mesmo texto, e o índice, o contexto e os registros não param por isso. A edição
nova nunca traz essa metade: o `edicao` a recusa (seção 4.2, passo 6).

### 4.1 `contexto` · a memória dos dias anteriores e o mapa em resumo

**Lê:** todos os `edicoes/*.json`, `dados/vetores.json`, `dados/veiculos.json`, `dados/regua.json`.
**Grava:** `P/contexto.json`, `P/mapa.txt` e `P/modelo.txt`. Imprime o contexto em texto curto.
Edição com `exemplo: true` é ignorada em tudo.

```json
{
  "dia": "2026-11-20",
  "janela_horas": 36,
  "edicao_do_dia": null,
  "anterior": {"data": "2026-11-19", "estado": "completa"},
  "alerta_anterior": {
    "nivel": 2,
    "dominios": [
      {"id": "energia", "nivel": 2, "desde": "2026-11-18", "edicoes_sem_gatilho": 1,
       "desce_hoje_sem_gatilho": false,
       "origem": {"edicao": "2026-11-18", "criterio": "energia.2", "texto": "…"}}
    ]
  },
  "historias_recentes": [
    {"edicao": "2026-11-19", "id": "p1", "titulo": "…", "vigiar": ["…"]}
  ],
  "vigiar_vencendo": [
    {"edicao": "2026-11-12", "item": "p2", "pergunta": "…", "prazo": "2026-11-19"}
  ],
  "candidatos": [
    {"id": "israel", "nome": "Israel", "edicoes": 2, "ultima": "2026-11-19", "motivo": "…"}
  ],
  "vetores_recentes": [
    {"id": "2026-11-15_p2_meloni", "data": "2026-11-15", "player": "meloni", "para": "soberanistas", "forca": 1}
  ]
}
```

| Campo | Regra |
|---|---|
| `dia` | o `--dia`: o agente usa este valor em `data` do rascunho, e as outras ferramentas leem daqui o seu dia |
| `janela_horas` | 36 se `anterior.data` é a véspera de `dia`, ou se não há `anterior`; senão 60. A coleta usa como `--horas`: depois de um dia de `falha`, a janela cobre o buraco (a regra R09 não aceita fonte com mais de 2 dias) |
| `edicao_do_dia` | `null`, ou `{"estado": …, "gerada_em": …}` se `edicoes/DIA.json` já existe |
| `anterior` | a edição anterior: a mais recente antes de `--dia` que não é `falha`, sem limite de dias; `null` se não há |
| `alerta_anterior` | níveis de `anterior`, com os 5 domínios. Sem `anterior`: tudo em 1, `desde` = `--dia`, contadores em 0, `origem` `null` |
| `edicoes_sem_gatilho` | o `S` da regra R13 (edição `falha` e edição cega não contam) |
| `desce_hoje_sem_gatilho` | `true` se `S` ≥ 2 e `nivel` > 1: sem gatilho hoje, e com o preço medido, o domínio desce 1 |
| `origem` | a origem do nível (`ESQUEMA.md`, seção 0): `edicao`, `criterio` e `texto` do gatilho, mais `"preco": true` se ele é de preço e `"alivio": true` se é de alívio; `null` no nível 1 |
| `historias_recentes` | principais e radar das 3 últimas edições que não são `falha`; `vigiar` só nas principais |
| `vigiar_vencendo` | o primeiro `vigiar` de cada principal dos últimos 30 dias cujo prazo já chegou (`prazo` ≤ `--dia`) e que nenhuma edição respondeu em `respostas`; entra também a de edição com até 37 dias cujo prazo venceu há até 7 dias (uma falha no dia do prazo não a perde). Até 3, as de prazo mais antigo primeiro. O `prazo` é a última data `DD/MM` da pergunta, lida como o primeiro dia assim a partir da edição que perguntou. A regra R21 **(dia)** põe esse prazo, na primeira pergunta, em até 30 dias da edição |
| `candidatos` | de `bastidores.candidatos` dos últimos 14 dias, contados por `id` (`edicoes` = em quantas edições apareceu; `ultima` = a data da aparição mais recente); `nome` e `motivo` são os da aparição mais recente |
| `vetores_recentes` | de `dados/vetores.json`, últimos 30 dias, sem os anulados |

**Bordas** (o que a tabela não fecha, como o `publica.py` faz):

- As janelas de 14 e de 30 dias contam para trás a partir da véspera e incluem o dia do limite: no dia 20/11,
  entram as edições de 06/11 (14 dias antes) e de 21/10 (30 dias antes), e não as de um dia antes delas. O
  próprio `--dia` nunca entra: o contexto só olha para antes dele. A edição de `falha` conta nas janelas de
  `vigiar_vencendo` e `candidatos` (nela as listas são vazias) e não conta em `historias_recentes`.
- Em nível 1, `edicoes_sem_gatilho` é contado do mesmo jeito, e `desce_hoje_sem_gatilho` é sempre `false`.
- `origem`: quando dois gatilhos da mesma edição servem, vale a ordem do `ESQUEMA.md`, seção 0.
- `prazo`: a data `DD/MM` igual à da própria edição que perguntou é esse mesmo dia. Pergunta sem data `DD/MM`
  não entra em `vigiar_vencendo`. "Respondida" é a que tem `respostas` com a mesma `edicao` e o mesmo `item`
  numa edição antes de `--dia`.
- Ordem: `historias_recentes` vai da edição mais nova para a mais velha, e em cada uma as principais e depois
  o radar, na ordem da edição; `candidatos` vai do que apareceu em mais edições para o de menos, depois da
  aparição mais recente para a mais antiga, depois por `id`; `vetores_recentes` segue a ordem de
  `dados/vetores.json`.

**Formato de `mapa.txt`.** Uma linha por veículo do mapa, em ordem de `id`. Serve para o agente achar o `id`
de um veículo, saber se ele é fonte forte, se pode ser fonte primária, a quem serve e qual é o site dele,
sem abrir o mapa inteiro.

```
MAPA · 146 veículos · rascunho, sem revisão do dono · id · partido (? = lado incerto) · fatos · tipo · serve a · site · nome
afp · CA · fatos alta · agencia · serve a: ue, macron · afp.com · Agence France-Presse (AFP)
anthropic_news · IN · fatos media · oficial · serve a: anthropic · anthropic.com · Anthropic (sala de imprensa) · LIGADO À ANTHROPIC
ap · CA? · fatos alta · agencia · serve a: — · apnews.com · Associated Press (AP)
```

- A primeira linha é a legenda das colunas. Diz `rascunho, sem revisão do dono` enquanto `revisado_em` é `null` no mapa; depois, `revisado em DD/MM/AAAA`.
- `tipo` é o do mapa. Só veículo de tipo `oficial` ou `dados` pode ser fonte `primaria` (regra R22).
- `serve a` lista os players de `serve_a` (partido não entra); `—` se não há.
- `site` é o primeiro de `sites`. O `veiculo` de uma fonte é o dono do site da `url` (regra T4).
- `LIGADO À ANTHROPIC` marca veículo com `anthropic` em `serve_a` ou em `alvos` (regra R19).
- O bloco é o formato exato: as colunas vêm separadas por ` · `, nesta ordem, e a legenda diz o número de
  veículos (`1 veículo` no singular). O `?` depois da sigla marca veículo de `lado_confianca` `baixa`.

**Formato de `modelo.txt`.** É a forma do rascunho, campo a campo, com o que a máquina confere: tamanho
máximo, contagem e valores permitidos. O agente não lê o `ESQUEMA.md` (ele não vai para o repositório): o
que ele precisa saber da forma está aqui, e o que é regra de julgamento está na `ROTINA.md`.
O arquivo é sempre o mesmo texto, gravado pelo `publica.py contexto` a partir das mesmas tabelas que o
validador usa. Tirando as linhas de comentário, é JSON válido. O texto é este:

```
// MODELO DO RASCUNHO · copie a forma para /tmp/info/rascunho.json
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
```

Dois cuidados de quem escreve a ferramenta: o modelo traz todo campo de origem `agente` e `misto` do
`ESQUEMA.md`, na ordem das tabelas, com o mesmo tamanho máximo; e nenhum campo calculado.
Se o `ESQUEMA.md` mudar, o modelo muda junto.
A linha do `realmente` avisa "texto corrido, numa linha só": quebra de linha e tabulação contam como caractere
de controle (regra R17), e o dossiê é o texto em que o agente mais tende a abrir parágrafo.

**Código.** 0, e a última linha é `OK contexto de DIA`. Edição antiga ilegível, ou `dados/regua.json`,
`dados/veiculos.json` ou `dados/vetores.json` que não servem de base: `FALHA` com o nome do arquivo e código 1,
sem gravar nada. Problema em `edicoes/indice.json` e nos outros arquivos de `dados/` só vira aviso: o contexto
não os usa.

### 4.2 `edicao` · completa, valida e publica o rascunho

**Lê:** `P/rascunho.json` (escrito pelo agente), `dados/*.json`, as outras edições, e de `P`:
`indicadores.json`, `coleta.json`, `urls.txt`, `conferencia.json`.
Arquivo de `dados/` ou edição antiga que não dá para ler, ou não serve de base: `FALHA` com o nome do arquivo,
código 1, sem gravar nada. Não contam o `edicoes/indice.json` (é refeito) nem o arquivo do próprio dia que
ainda não foi publicado (é gravado por cima). Vale o mesmo para a `falha`.

**Passos, nesta ordem.**

1. Lê `P/rascunho.json`. Não existe: `FALHA`, código 1. Não é JSON:
   `FALHA rascunho.json: linha L, coluna C: mensagem`, código 1.
2. Com `--corta`, corta os itens pedidos (abaixo) e regrava `P/rascunho.json`. Com `--simula`, o passo 2
   corta em memória: o `rascunho.json` não é regravado. O rascunho regravado fica, mesmo que a conferência
   recuse a edição depois: a rodada seguinte parte dele.
3. Confere se o dia já foi publicado. "Já publicado" quer dizer: `edicoes/DIA.json` está no commit `HEAD`
   (`git cat-file -e HEAD:edicoes/DIA.json`) com estado `completa` ou `reduzida`. Essa edição é final: com
   rascunho que dá a mesma edição (sem contar `gerada_em`), termina em
   `OK edição DIA já publicada: nada mudou`, código 0; com rascunho diferente, `FALHA`, código 1, e a linha
   diz em que campos da raiz as duas diferem.
   Edição do dia com estado `falha` é trocada pela nova. Arquivo do dia que só está no disco, sem commit,
   é desta execução: `edicao` e `falha` gravam por cima. Há git na raiz quando a raiz do repositório git é
   a própria raiz (repositório de uma pasta de cima não conta). Sem git na raiz, o disco decide o que já foi
   publicado: a edição `completa` ou `reduzida` que está em `edicoes/DIA.json` é final, como se estivesse no
   commit. `edicoes/DIA.json` que existe (no commit ou, sem git, no disco) e não dá para ler, ou não tem
   estado legível, não é regravado: `FALHA`, código 1. O git que não responde também é `FALHA`, código 1:
   sem ele não dá para saber o que é final.
4. Preenche os campos calculados (colunas `publica`, `indicadores`, `mapa` e `misto` do `ESQUEMA.md`):
   - `versao` e `gerada_em` (hora UTC de agora, sempre que a edição é gravada);
   - `lado` de cada ataque, copiado do mapa;
   - `indicadores`, copiado de `P/indicadores.json` (sem o arquivo: lista vazia e aviso);
   - os gatilhos de preço de cada domínio, copiados de `P/indicadores.json`, na frente dos do agente;
   - `sem_preco` de cada domínio (regra R13f);
   - `nivel` de cada domínio (regra R13), `alerta.nivel`, as `tendencia` e os `desde` (regra R14);
   - `conflito_de_interesse` de cada item (regra R19: liga, nunca desliga);
   - `placar_do_dia[].saldo`, `narrativa` e a ordem da lista (regra R12);
   - `bastidores.veiculos_consultados`, `feeds_ok` e `feeds_falhos` (sem `P/coleta.json`: 0 e aviso).

   `P/indicadores.json` ou `P/coleta.json` que não dá para ler, que não é objeto, ou cujo `dia` é outro, conta
   como ausente, com aviso: dado de outro dia não entra na edição de hoje. `P/conferencia.json` ilegível
   também conta como ausente.
5. Valida em memória, com todas as regras: R (inclusive as **(dia)**), H e T. Sem `P/conferencia.json`,
   só as URLs de `coleta.json` têm data conferida, e o comando avisa: "rode `coleta.py --confere`".
   O histórico é o das edições do disco, e o validador o recebe sempre, mesmo vazio: a saída "sem histórico
   à mão" da regra H1 é só do `valida.py --edicao` com arquivo solto. Na republicação do mesmo dia, a
   conferência roda contra os registros já limpos (sem o que o dia gravou neles, passo 7): é contra eles que
   a edição fica gravada. Rascunho que deixa de trazer o player novo e ainda o usa como alvo é recusado (R02).
6. Com erro: imprime no formato do `valida.py`, **não grava nada**, código 1. As regras T saem no mesmo
   formato: `ERRO T3 principais[0].fontes[2].publicado_em: é 2026-11-20, a página diz 2025-11-20. Corrija a
   data; se sair da janela, troque a fonte.` A última linha é a do `valida.py`: `FALHA N erros, M avisos`.
   Além das regras do `ESQUEMA.md`, o `edicao` recusa duas coisas que não daria para gravar: dois vetores do
   mesmo player no mesmo item (ERRO R11: o `id` no registro é data, item e player, `ESQUEMA.md`, seção 12) e
   texto com metade solta de par substituto (ERRO R17, com o caminho do campo: o UTF-8 não a grava).
7. Sem erro, grava:
   - `edicoes/DIA.json`, completo e normalizado (chaves na ordem do `ESQUEMA.md`; as de `dna` e de
     `dna_fontes`, na ordem dos temas da régua: rascunho com outra ordem não é recusado por isso);
   - `edicoes/DIA.md`, a versão em texto;
   - `edicoes/indice.json`, refeito a partir de todos os arquivos de edição (`ESQUEMA.md`, seção 11);
   - `feed.xml`, refeito, com as 30 edições mais novas;
   - `dados/vetores.json`: acrescenta os vetores da edição (com `conflito_de_interesse: true` quando o item
     tem a marca) e uma entrada de anulação para cada `errata[].anula_vetor` (`ESQUEMA.md`, seção 12);
   - `dados/players.json`: acrescenta o item de `novos_players` com `origem: "rotina"` e
     `incluido_em: DIA`, e `atualizado_em` recebe o dia da edição, e só muda quando a lista muda.

   Os dois registros só são regravados quando mudam: edição sem vetor, sem anulação e sem player novo não
   toca neles.
   Republicação na mesma execução: o que o dia já tinha gravado nesses dois registros (vetor ou anulação com
   `data` igual a DIA; player com `incluido_em` igual a DIA) é tirado e refeito a partir do rascunho novo.
   A saída traz a linha `endereço base do feed: …`, que diz de onde veio o endereço (seção 4.5), e, depois da
   gravação, `gravado: …`, com os arquivos gravados.
8. Última linha: `OK edição 2026-11-20 publicada: nível 2 ATENÇÃO (energia 2, alimentos 1, cambio 2, suprimentos 1, conflito 1), 3 principais, 9 radar, 1 vetor, 0 players novos`.
   É o formato da linha: os domínios pelo id, na ordem da régua (`cambio`, sem acento); o rótulo do nível é
   o da régua; singular só com 1 (`1 principal`, `1 vetor`, `1 player novo`; o radar é sempre `N radar`).

O `publica.py` nunca grava `dados/veiculos.json`, `dados/regua.json` nem `dados/indicadores.json`.

**`--corta ID[,ID]`.** Para quando um item não passa e não há mais rodada: `python3 ferramentas/publica.py edicao --corta r3`
(vários ids, com vírgula: `--corta r3,r7`). Tira do rascunho os itens citados e conserta o que dependia
deles: renumera os ids em ordem (`p1..pN`, `r1..rN`); acerta os `ref` dos gatilhos; tira o gatilho que
apontava para item cortado; tira de `placar_do_dia` o partido que ficou sem linha em placar nenhum; troca
`estado` para `reduzida` se a contagem da `completa` deixou de fechar. Imprime o que mudou e segue para
os passos 3 a 8. Texto livre que cita um id cortado ou renumerado não é reescrito: o comando avisa onde está.
"Deixou de fechar" é a regra R15: a edição cortada é completada e conferida, e um erro R15 basta para a troca.
Os ids vão de `p1` a `p3` e de `r1` a `r12`; id ilegível ou repetido na opção é erro de uso. Id que o rascunho
não tem é erro de uso: `FALHA uso: …`, código 2, e nada é cortado nem gravado (basta um para segurar o corte
inteiro). Id que aparece em dois itens do rascunho é defeito do rascunho: `FALHA`, código 1, sem corte.

`--simula` faz os passos 1 a 6, lista o que o passo 7 gravaria e imprime os níveis calculados. Não grava.
Com `--corta`, o corte é feito em memória (passo 2). A última linha é
`OK simulação: a edição DIA passa, e nada foi gravado: …`, com o resumo do passo 8; com erro, a do passo 6.

**Código.** 0 publicada (ou já publicada, igual, ou simulação que passa). 1 com erro (nada gravado). 2 erro de
uso (nada gravado).

### 4.3 `falha` · edição de falha

Para o dia em que nada funcionou. O site mostra "sem edição hoje", e não um dia calmo.

- Recusa (`FALHA`, código 1) se o dia já foi publicado com estado `completa` ou `reduzida` (passo 3 de `edicao`).
  A falha do dia, e o arquivo do dia que só está no disco, são gravados por cima.
- Gera `edicoes/DIA.json` com `estado: "falha"`: níveis e `desde` copiados de `anterior` (ou 1), `gatilhos`
  vazios, `tendencia` `estavel`, `sem_preco` pela regra R13f, `leitura` e `vigiar` com texto fixo
  ("Sem leitura hoje. Nível repetido de DD/MM."; sem `anterior`, só "Sem leitura hoje."),
  `resumo` igual a "Sem edição hoje. " mais o `--motivo`, `alerta.motivo` e `bastidores.limites` com o `--motivo`,
  `principais`, `radar`, `placar_do_dia`, `novos_players`, `errata` e `respostas` vazios, `indicadores` de
  `P/indicadores.json` se existir, `bastidores.modo` `feeds`, contadores em 0 e listas vazias.
  Os contadores ficam em 0 mesmo com `P/coleta.json`: a falha não lê a coleta. `P/indicadores.json` de outro
  dia, ou ilegível, conta como ausente (passo 4 de `edicao`). Se os indicadores não passam na conferência, a
  falha sai sem eles, com aviso: ela é a última saída do dia e não pode ficar presa a eles.
- `--motivo`: até 200 caracteres, sem HTML (regra R17). Motivo fora da regra é erro de uso: `FALHA uso: …`,
  código 2, e nada é gravado (o texto não é cortado). Vale a R17 inteira: motivo vazio, com quebra de linha,
  com endereço ou com e-mail também é erro de uso.
- Depois publica como no passo 7 de `edicao` (o que o dia tinha gravado nos dois registros sai deles).
- Última linha: `OK falha de 2026-11-20 publicada: sem edição hoje; nível 2 ATENÇÃO (energia 2, alimentos 1,
  cambio 2, suprimentos 1, conflito 1), repetido de 19/11` (sem `anterior`: `…, sem edição anterior`), no
  formato do passo 8. Código 0; 1 com erro; 2 erro de uso.

### 4.4 `refaz` · refaz índice, textos e feed

Refaz `edicoes/indice.json`, todos os `edicoes/*.md` e `feed.xml` a partir dos arquivos de edição.
Não toca nos `.json` de edição nem em `dados/`. É para o dono, depois de mudar as ferramentas.
Lê `dados/` só para os nomes do texto (domínio, partido, veículo, player, rótulo do nível): dado ilegível vira
aviso, e o texto sai com os ids. Edição ilegível: `FALHA` com o nome do arquivo, código 1, sem gravar nada.
`edicoes/DIA.md` sem o `.json` ganha aviso, e não é apagado. Última linha:
`OK refeitos o índice (3 edições), 3 textos e o feed (3 entradas)` (singular só com 1). Código 0; 1 com erro;
2 erro de uso.

### 4.5 Formato do `.md` e do `feed.xml`

**`edicoes/DIA.md`.** Texto puro em Markdown, mesma ordem do site: título com a data; nível geral, rótulo e
tendência; a linha do que mudou desde a edição anterior ("Desde 18/11: energia 2 → 3."; sem mudança, "Desde
18/11: nenhum nível mudou."); resumo; domínios (nível, "sem dado de preço de: …" quando houver, gatilhos, leitura,
vigiar); indicadores; cada principal (fato, não confirmado, quem atirou, o que está realmente acontecendo, na
prática, no Brasil, eixo, placar ou a frase de `sem_placar`, vetores, vigiar, fontes); radar; placar do dia
(saldo, e a narrativa quando não é 0); respostas; players novos; errata; bastidores. Os rótulos são os do site
(ESPEC-SITE, seções 2, 5 e 8): o `.md` e o site dizem o mesmo.

- Edição com `exemplo: true` abre com a linha `EDIÇÃO DE EXEMPLO · dados fictícios`.
- Item com `conflito_de_interesse: true` leva a linha
  `Aviso: o INFOCENARIUM é escrito por modelos de IA, do setor de IA, que podem ser parte ou concorrente nesta notícia: foi construído pelo Claude Fable e pelo Claude Opus, da Anthropic, e hoje quem escreve é o GLM, da Z.ai.`
  e, numa linha à parte, `Por isso a confiança deste item não passa de média.`. Quando a lista `conflito` da
  régua conhece o vínculo (regra R19, casos b e c), uma terceira linha o nomeia, com o texto e a regra do site
  (ESPEC-SITE, seção 8.3): "Este item envolve nomes da lista de conflito da régua: NOMES.", na ordem da lista,
  primeiro o nome do player citado como alvo ou em vetor, depois o termo escrito em algum texto do item; termo
  que já está no nome de um player listado não se repete. O caso a (notícia de IA) o aviso já diz; o caso d
  (fonte de veículo ligado à Anthropic) vem do mapa, não da lista, e não ganha frase.
- Com o mapa de veículos em rascunho (`revisado_em` nulo em `dados/veiculos.json`), "Mapa de veículos em
  rascunho, ainda sem revisão do dono." vem logo abaixo de `## Principais` e de `## Radar`, quando a seção tem
  item. Como no site, a nota e o vínculo seguem os dados de hoje: o `refaz` depois da revisão os tira.
- Quem atirou: veículo, partido do `lado`, alvo, enquadramento, "Deixou de fora: … Segundo a leitura do
  INFOCENARIUM em DD/MM." (com a data da edição) e o `url`. Nas fontes, o partido do veículo é o `lado` gravado
  no ataque do mesmo veículo no mesmo item; sem ataque dele, o do mapa de hoje.
- Fonte `outro` aparece com o `nome` e "(fora do mapa)".
- Todo campo de texto sai com escape dos sinais de Markdown (`\`, `[`, `]`, `(`, `)`, `*`, `_`, crase, `#`, `|`).
  Só campo `url` vira endereço, e aparece por extenso. Texto de terceiro nunca vira link.
- O escape é a barra invertida antes do sinal (`\[`, `\*`). Também levam barra o que ainda viraria marca ou
  link: `<` (marca de HTML), `@` (e-mail), o `:` de `://` e o ponto de `www.`; e, no começo do texto, o que
  abriria lista, citação ou título (`-`, `+`, `>`, `=`, `~`, e o ponto de `1. `). Todo texto sai numa linha só:
  quebra de linha e caractere de controle viram espaço. O `url` sai entre `<` e `>`; o que não é URL válida
  sai como texto, seguido de "(endereço inválido)".
- Linhas fixas: o título é `# INFOCENARIUM · DD/MM/AAAA`; logo abaixo, o estado e a hora da publicação em Brasília; o
  nível geral vai em negrito, `**Nível N · RÓTULO · tendência**`. Sem edição anterior não houve medida de
  tendência: o `estavel` que a regra R14 grava nesse caso não sai, nem no nível geral nem no título de cada
  domínio (como no site). A linha do que mudou compara cada domínio com
  a edição anterior; com mais de um domínio, as mudanças vêm na ordem da régua, separadas por vírgula ("Desde
  18/11: energia 2 → 3, conflito 2 → 3."). Sem edição anterior: "Primeira edição: sem comparação.". Na edição
  `falha`, a linha é "Níveis repetidos de 18/11." (sem edição anterior, "Níveis sem base: ainda não houve
  edição.").
- "sem dado de preço de: …" fica ao lado do nível, no título do domínio; a frase lista os nomes dos
  indicadores, como estão na edição. Os gatilhos vêm sob "**Gatilhos de hoje:**", cada um com o código do
  critério, o texto, as etiquetas EXCEÇÃO e ALÍVIO e para onde a prova leva: "ver principal 1", "ver radar 4"
  ou "ver indicador: Petróleo Brent" (`ref` que não é desta edição sai pelo id). Domínio sem gatilho diz
  "Nenhum gatilho hoje." (nível 1) ou "Mantido desde DD/MM. Sem gatilho novo. O nível desce um degrau depois
  de 2 edições seguidas sem gatilho. Edição sem dado de preço não entra nessa conta." (nível acima de 1).
- Indicador sem valor diz "sem dado · fonte prevista: NOME <url>": é a primeira fonte do catálogo (ESQUEMA,
  seção 3), e não a de um número que veio.
- Resposta: "Pergunta de DD/MM/AAAA, principal 1: …".
- Seção sem item (respostas, players novos, errata) não aparece. Na edição `falha`, principais e radar dizem
  "Sem itens: a rotina não fechou a edição deste dia.", e os bastidores trazem só o que não deu para conferir:
  sem a linha do modo e sem os contadores, que a falha grava em 0 sem medir (seção 4.3).
- Edição torta (arquivo mexido à mão) não derruba o texto: o que não dá para ler sai como texto, com escape,
  ou não sai; veículo, partido ou player que não está nos dados sai pelo id.

Um trecho do `.md` (edição fictícia, com cortes marcados por `…`):

```
# INFOCENARIUM · 20/11/2026

Edição completa · gerada em 20/11/2026 às 18h14 (hora de Brasília)

**Nível 3 · TENSÃO · subindo**

Desde 19/11: energia 1 → 3, suprimentos 1 → 2, conflito 1 → 3.

Edição fictícia: um ataque inventado a um terminal de petróleo leva energia e risco de conflito ao nível 3.

**Motivo do nível:** Texto fictício. Nível 3 por um ataque de 19/11, que parou um terminal de petróleo: …

## Domínios

### Energia · nível 3 · subindo

Neste nível desde 20/11/2026.

**Gatilhos de hoje:**

- `energia.2` · Petróleo Brent subiu 6,1% em 7 dias, até 20/11 \(limiar: 5%\). · ver indicador: Petróleo Brent
- `energia.3` · Texto fictício. Ataque de 19/11 parou um terminal de exportação de petróleo. · ver principal 1

**Leitura:** Texto fictício. Petróleo mais caro lá fora encarece o diesel e a gasolina importados; …

**Vigiar:** O Brent passa de 10% de alta em 7 dias?

### Alimentos · nível 1 · estável · sem dado de preço de: Milho

Neste nível desde 19/11/2026.

Nenhum gatilho hoje.

…

## Indicadores

- Petróleo Brent: 78,4 US$ por barril · no dia +1,3% · em 7 dias +6,1% · cotação de 20/11/2026 · fonte: Fonte fictícia de exemplo <https://exemplo.invalid/indicadores/brent>
- Gás natural nos EUA: sem dado · fonte prevista: Fonte fictícia de exemplo <https://exemplo.invalid/indicadores/gas_natural>
…

## Principais

Mapa de veículos em rascunho, ainda sem revisão do dono.

### p1 · País fictício ataca terminal de petróleo no Estreito de Exemplo

Geopolítica · confiança alta · domínios: Energia, Risco de conflito

**O que aconteceu:** Texto fictício. Em 19/11, drones da República de Exemplo, país que não existe, …

**Quem atirou:**

- The New York Times · Partido da Ordem Global · alvo: República de Exemplo \(fictícia\) · Texto fictício. … · <https://…>
…

## Bastidores

- Modo: coleta normal, pelos feeds dos veículos
- Veículos consultados: 19 · feeds lidos: 61 · feeds que falharam: 7 · páginas lidas: 11 · buscas: 4 · minutos de trabalho: 24 · páginas descartadas por trazer ordens ao agente: 1
- O que não deu para conferir: …
```

**`feed.xml`.** Atom 1.0, bem formado, texto escapado. Título `INFOCENARIUM · monitor geopolítico e de IA`.
`updated` é o maior `gerada_em`. Uma entrada por edição, as 30 mais novas, sem as de `exemplo: true`:
título `INFOCENARIUM DD/MM/AAAA · nível N RÓTULO` (em edição `falha`: `INFOCENARIUM DD/MM/AAAA · sem edição`); `id` e `link`
com o endereço da edição (`URL-BASE#/edicao/AAAA-MM-DD`); `updated` = `gerada_em`; `summary` = `resumo`;
`content` em texto com os títulos e os fatos das principais.

- `updated` é o maior `gerada_em` das edições do feed: a de exemplo não entra no feed nem conta para o
  `updated`, mesmo sendo a mais nova. Feed sem entrada (nenhuma edição, ou só a de exemplo) leva
  `1970-01-01T00:00:00Z`: o relógio não entra, e a mesma entrada dá os mesmos bytes.
- As entradas vêm da edição mais nova para a mais velha.
- O `id` do feed é o endereço base; há um `link` para ele, um `link rel="self"` para `URL-BASE` + `feed.xml`, e
  o `author` é `INFOCENARIUM`.
- `content` traz, para cada principal, `N. título`, uma quebra de linha e o `fato`, com uma linha em branco entre
  as principais. Edição sem principal (a `falha`) leva o `resumo` no `content`.
- Todo texto sai numa linha só (no `content`, as quebras são só as da forma acima). O que o XML 1.0 não aceita
  (caractere de controle, metade solta de par substituto, `U+FFFE`, `U+FFFF`) vira espaço.

```
<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>INFOCENARIUM · monitor geopolítico e de IA</title>
  <id>https://exemplo.invalid/INFOCENARIUM/</id>
  <link href="https://exemplo.invalid/INFOCENARIUM/"/>
  <link rel="self" type="application/atom+xml" href="https://exemplo.invalid/INFOCENARIUM/feed.xml"/>
  <updated>2026-11-20T21:14:03Z</updated>
  <author>
    <name>INFOCENARIUM</name>
  </author>
  <entry>
    <title>INFOCENARIUM 20/11/2026 · nível 3 TENSÃO</title>
    <id>https://exemplo.invalid/INFOCENARIUM/#/edicao/2026-11-20</id>
    <link href="https://exemplo.invalid/INFOCENARIUM/#/edicao/2026-11-20"/>
    <updated>2026-11-20T21:14:03Z</updated>
    <summary type="text">Edição fictícia: um ataque inventado a um terminal de petróleo leva energia e risco de conflito ao nível 3.</summary>
    <content type="text">1. País fictício ataca terminal de petróleo no Estreito de Exemplo
Texto fictício. Em 19/11, drones da República de Exemplo, país que não existe, …

2. Lei fictícia obriga registro de modelos avançados de IA
Texto fictício. …</content>
  </entry>
</feed>
```

O workflow `publica-edicao.yml` recusa a edição inteira se o `feed.xml` sair disto: raiz `<feed>` e **todos** os
elementos no espaço de nomes do Atom (`http://www.w3.org/2005/Atom`), sem elemento de extensão; `content` e
`summary` em texto puro (`type="text"` ou sem o atributo; nunca `xhtml`); nenhum `<!DOCTYPE`, nenhum
`<!ENTITY`; e nenhuma instrução `<?…?>`
além da declaração `<?xml …?>` no começo do arquivo (nada de folha de estilo).

**Endereço base**, nesta ordem: `--url-base`; o que já está no `feed.xml` existente; o derivado de
`git remote get-url origin` (`…/DONO/REPO` vira `https://DONO.github.io/REPO/`); por último `./`.

- "O que já está no `feed.xml`" é o `id` do feed, e só vale se o arquivo passa nas exigências do workflow
  (acima): feed que não serve não empresta o endereço. Assim o `--url-base` dado uma vez fica para as próximas.
  Vale mesmo relativo (`./`): os links funcionam, mas o Atom pede `id` absoluto, e a linha de saída diz
  `endereço base do feed: ./ (o do feed.xml que já existe; relativo: para o feed levar o endereço do site, use --url-base)`.
- `--url-base` aceita endereço `http` ou `https`, ou caminho relativo (`./`), sem espaço, sem `#`, sem `?` e sem
  aspas; outro valor é erro de uso. A barra do fim entra sozinha.
- O remoto que é pasta desta máquina (`/…`, `../…`, `file:`) não dá endereço: vale o passo seguinte.

---

## 5. Quem chama o quê

**A rotina diária** (ordem do `ROTINA.md`):

```
python3 ferramentas/valida.py --dados
python3 ferramentas/publica.py contexto
python3 ferramentas/coleta.py
python3 ferramentas/indicadores.py
python3 ferramentas/coleta.py --confere
python3 ferramentas/publica.py edicao
python3 ferramentas/valida.py --tudo --base origin/main --dia "$DIA"
```

`$DIA` é o `dia` de `P/contexto.json`. No dia em que não dá para montar edição, a sexta linha é trocada por
`python3 ferramentas/publica.py falha --motivo "TEXTO"`. Quando um item não passa, a rotina repete a sexta
linha com `--corta`. Na reserva do git (push direto na `main`), a rotina puxa a `main`, roda de novo a sétima
linha e só então empurra. A receita de git está na `ROTINA.md`, seção 9.

**O GitHub Action** (`.github/workflows/publica-edicao.yml`; como funciona: `README.md`): para cada branch de
edição, de nome exato `claude/edicao-AAAA-MM-DD`, confere os caminhos com um script próprio (a mesma lista da
regra G4), leva a edição para a `main` numa cópia local e roda o validador **da `main`** sobre o resultado:
`python3 ferramentas/valida.py --tudo --base ANTES --dia DIA`, onde `ANTES` é o identificador do commit da
`main` de antes e `DIA` vem do nome do arquivo `edicoes/AAAA-MM-DD.json` que chegou (uma chamada por edição
mexida; sem edição mexida, uma chamada sem `--dia`). Nessa hora a pasta está limpa, com o commit do robô em
`HEAD`, sem pasta de trabalho, sem credencial e com 120 segundos de limite. Só empurra com código 0: código 1, 2 ou
tempo esgotado recusam a edição, que vai para a branch `recusada/edicao-AAAA-MM-DD-…`.
Quem dispara é o push da branch (pelo `sinal-edicao.yml`) e uma varredura de hora em hora.
O `valida.yml` roda `python3 ferramentas/valida.py` a cada push na `main` e em pull request, e só avisa.
Os dois rodam com `PYTHONDONTWRITEBYTECODE=1`.

**Os testes:** `valida.py --edicao testes/fixtures/edicao-exemplo.json` tem de sair com código 0.
Os testes devem rodar contra uma cópia congelada de `dados/` (opção `--raiz`), para não quebrarem quando
o dono revisar o mapa: o exemplo cita veículos reais, com o lado e a nota de fatos de 20/11/2026.
Como a regra T4 pede que o site da URL seja o do veículo, o rascunho de teste do `publica.py edicao` leva os
endereços do exemplo para o primeiro `sites` de cada veículo, com o caminho fictício
(`https://exemplo.invalid/nyt/…` vira `https://nytimes.com/exemplo/…`).

## 6. Resumo de leitura e escrita

| Ferramenta | Rede | Lê do repositório | Grava no repositório | Grava na pasta de trabalho |
|---|---|---|---|---|
| `coleta.py` | sim | `dados/veiculos.json`, `dados/regua.json` | nada | `coleta.json`, `mesa.txt` |
| `coleta.py --confere` | sim | nada | nada | `conferencia.json` |
| `indicadores.py` | sim | `dados/indicadores.json`, `dados/regua.json` | nada | `indicadores.json` |
| `valida.py` | não | `dados/`, `edicoes/`, `feed.xml` | nada | nada |
| `publica.py contexto` | não | `edicoes/`, `dados/vetores.json`, `dados/veiculos.json`, `dados/regua.json` | nada | `contexto.json`, `mapa.txt`, `modelo.txt` |
| `publica.py edicao` e `falha` | não | `dados/`, `edicoes/`, `feed.xml` (o endereço base) e o git da raiz (o commit `HEAD` e o remoto `origin`) | `edicoes/DIA.json`, `edicoes/DIA.md`, `edicoes/indice.json`, `feed.xml` e, quando mudam, `dados/vetores.json` e `dados/players.json`; com `--simula`, nada | `edicao` com `--corta` e sem `--simula` regrava `rascunho.json`; nos outros casos, nada |
| `publica.py refaz` | não | `edicoes/`, `dados/` (só os nomes do texto), `feed.xml` e o remoto `origin` (o endereço base) | `edicoes/indice.json`, `edicoes/*.md`, `feed.xml` | nada |
