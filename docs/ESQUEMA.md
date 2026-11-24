# INFOCENARIUM · ESQUEMA · contrato de dados da edição (versão 1)

Este é o contrato de dados do INFOCENARIUM (versão 1, de 23/11/2026), na forma que as ferramentas seguem.
Vale para três leitores: quem escreve a edição (o agente diário), quem confere (`valida.py`) e quem
mostra (o site). O que não está aqui não existe.

Exemplo completo e válido: `testes/fixtures/edicao-exemplo.json`.
Interface das ferramentas: `docs/CONTRATO-FERRAMENTAS.md`. Manual do agente: `ROTINA.md`, na raiz do
repositório. Desenho do site: `docs/ESPEC-SITE.md`.

## 0. Convenções

- Arquivo: `edicoes/AAAA-MM-DD.json`, UTF-8, até 60 KB (61.440 bytes). Chaves em ASCII minúsculo com sublinhado.
- **Data** é texto `AAAA-MM-DD`. **Data-hora** é texto UTC `AAAA-MM-DDTHH:MM:SSZ`.
- **URL** começa com `http://` ou `https://` (em minúsculas), tem nome de site, tem até 500 caracteres e não tem
  espaço, caractere de controle (U+0000 a U+001F e U+007F) nem os caracteres invisíveis de direção de texto e de
  largura zero (U+200B a U+200F, U+202A a U+202E, U+2060 a U+2064, U+2066 a U+2069 e U+FEFF). Também não tem
  aspas (`"`), apóstrofo (`'`), crase (`` ` ``), cifrão (`$`) nem barra invertida (`\`), e não traz usuário nem
  senha antes do nome do site (`https://alguem@…`): esses sinais fecham a aspa ou rodam comando numa linha de
  comando, e com a barra invertida ou o usuário o navegador pode ler outro site no mesmo texto. Vale igual para as
  três ferramentas que conferem URL (`coleta.py`, `valida.py`, `publica.py`): todas usam a mesma função.
- **Tamanho máximo** é em caracteres. Texto nunca traz HTML, caractere de controle, e-mail, caminho de
  computador, nem endereço de site fora de campo `url` (regra R17).
- Todo texto é em português do Brasil, para leigo. Exceção única: `fontes[].titulo`, que fica como foi publicado.
- Chave desconhecida é erro. Campo opcional pode faltar; não use `null`, salvo onde a tabela permite.
- As chaves são gravadas na ordem das tabelas abaixo.

**Rascunho e edição.** O agente não grava dentro do repositório. Ele escreve o **rascunho**
(`/tmp/info/rascunho.json`) só com os campos de origem `agente`. O `publica.py edicao` completa os
outros campos, confere tudo e grava a **edição**. Campo calculado que vier no rascunho é trocado, sem erro.
A forma do rascunho, campo a campo, o agente lê em `/tmp/info/modelo.txt`, gravado pelo `publica.py contexto`
(`CONTRATO-FERRAMENTAS.md`, seção 4.1): é este esquema, resumido para quem escreve.

Coluna **Vem de**:

- `agente`: o agente escreve no rascunho.
- `publica`: o `publica.py` calcula e grava.
- `indicadores`: o `publica.py` copia da saída do `indicadores.py`.
- `mapa`: o `publica.py` copia de `dados/veiculos.json`.
- `misto`: parte vem do agente e parte é calculada; a tabela diz qual.

Listas fechadas usadas abaixo:

| Lista | Valores |
|---|---|
| estado | `completa`, `reduzida`, `falha` |
| categoria | `geopolitica`, `ia` |
| domínio | `energia`, `alimentos`, `cambio`, `suprimentos`, `conflito` (de `regua.json`, chave `dominios`) |
| tendência | `subindo`, `estavel`, `descendo` |
| efeito | `ganha`, `perde` |
| evidência | `preco`, `tropa`, `contrato`, `lei`, `voto`, `sancao`, `narrativa` (de `regua.json`, chave `evidencias`) |
| força | `1` (sinal), `2` (ato reversível), `3` (difícil de desfazer) (de `regua.json`, chave `forcas`) |
| confiança | `alta`, `media`, `baixa` |
| tema | os 7 ids de `regua.json` (`pandemia_inicio` … `imigracao`) e `ordem` (o eixo manutenção × mudança) |
| tema atual | `pandemia_depois`, `ia_depois`, `moderacao`, `clima`, `imigracao`: os 5 em que um ato de hoje pode mexer. `pandemia_inicio` e `ia_inicio` são história |
| sentido | `azul`, `vermelho` (os polos de `regua.json`) |
| campo | `ordem`, `contestacao` (de `regua.json`, chave `campos`) |
| partido | os 7 ids de `regua.json` (`ordem_global` … `independentes`) |
| alvo especial | `outro` (com `alvo_nome`), `nenhum` (o texto só relata ou só promove alguém) |
| resposta | `sim`, `nao`, `sem_dado` |
| tipo de player | `regime`, `governo`, `instituicao`, `empresa` (a rotina não usa `regime`: regra R20) |
| time | `manutencao`, `mudanca` |
| modo | `feeds`, `busca` |
| frequência | `diaria`, `mensal` |
| leitor | `fred_csv`, `yahoo_chart`, `bcb_sgs`, `eia_v2`, `fao_csv`, `cnbc_chart` (formatos no `CONTRATO-FERRAMENTAS.md`, seção 2) |

O que conta em cada **evidência** e em cada **força** está escrito na régua (`regua.json`, chaves `evidencias` e
`forcas`), e o critério para dizer que um time avança está em `times_avanco`. São dado, e não texto do manual:
o agente lê lá, e o site mostra na tela de método.

Termos usados nas regras:

- **Campo:** o campo da `ordem` são os veículos de Ordem Global e Centro Atlântico. O da `contestacao` são os
  de Soberanistas e Eixo Revisionista. Veículo dos outros partidos, e veículo fora do mapa, não tem campo.
  A lista mora em `regua.json`, chave `campos`.
- **Fonte forte:** fonte de veículo com `fatos: alta` no mapa, ou fonte marcada `primaria: true` (regra R22).
- **Site de uma URL:** o nome do site, em minúsculas, sem `www.` (em `https://www.exemplo.com/a`, é `exemplo.com`).
  Um site **bate** com um nome da lista quando é igual a ele ou termina em ponto mais ele:
  `gov.br.exemplo.com` não bate com `gov.br`.
- **Endereço limpo:** para comparar duas URLs, as ferramentas limpam os dois lados do mesmo jeito: esquema e
  nome do site em minúsculas, `http` igual a `https`, sem `www.`, sem `#…`, sem parâmetros `utm_`, sem barra no fim.
- **Edição anterior:** a edição mais recente antes de `data` que não é `falha` e não tem `exemplo: true`.
  Não há limite de dias.
- **Edição do dia** e **edição de arquivo:** a edição do dia é a que está sendo publicada ou conferida
  sozinha (`publica.py edicao`, `valida.py --edicao`) e, em `valida.py --tudo`, a que tem `data` igual a `--dia`.
  As outras são arquivo. Edição publicada é registro: o mapa, os limiares e o catálogo mudam depois, e ela
  **não** é conferida de novo contra eles. As regras marcadas **(dia)** na seção 10 valem só para a edição do dia.
- **Origem do nível** de um domínio: o gatilho mais recente desse domínio, até a edição anterior, com nível
  igual ou maior que o nível do domínio na edição anterior. O gatilho de alívio conta. Domínio em nível 1
  não tem origem. Se a mesma edição tem mais de um gatilho que serve, fica o de evento antes do de preço, e o
  de preço antes do de alívio; entre os do mesmo tipo, o de maior nível; no empate, o primeiro da lista.
- **Edição cega** para um domínio: a que tem `sem_preco` não vazia nesse domínio. Faltou dado de preço:
  o INFOCENARIUM não mediu.

## 1. Raiz da edição

| Campo | Tipo | Obrig. | Valores permitidos | Máx. | Vem de |
|---|---|---|---|---|---|
| `versao` | inteiro | sim | `1` | — | publica |
| `data` | data | sim | o dia da edição em Brasília; igual ao nome do arquivo | 10 | agente |
| `gerada_em` | data-hora | sim | hora da publicação; dia UTC igual a `data` ou ao dia seguinte | 20 | publica |
| `estado` | texto | sim | lista estado; o agente só escreve `completa` ou `reduzida` | — | agente (`falha`: `publica.py falha`) |
| `exemplo` | booleano | não | `true` só em edição fictícia; rascunho com este campo é recusado | — | — |
| `resumo` | texto | sim | o dia em uma frase | 240 | agente |
| `alerta` | objeto | sim | seção 2 | — | misto |
| `indicadores` | lista | sim | de 0 até um item por indicador do catálogo, seção 3 | — | indicadores |
| `principais` | lista | sim | seção 4; contagem na regra R15 | — | agente |
| `radar` | lista | sim | seção 5; contagem na regra R15 | — | agente |
| `placar_do_dia` | lista | sim | 0 a 7 itens, seção 6 | — | misto |
| `novos_players` | lista | sim | 0 ou 1 item, seção 7 | — | agente |
| `errata` | lista | sim | 0 a 5 itens, seção 8 | — | agente |
| `respostas` | lista | sim | 0 a 3 itens, seção 8 | — | agente |
| `bastidores` | objeto | sim | seção 9 | — | misto |

## 2. `alerta`

| Campo | Tipo | Obrig. | Valores permitidos | Máx. | Vem de |
|---|---|---|---|---|---|
| `nivel` | inteiro | sim | 1 a 5; o maior nível entre os domínios | — | publica |
| `tendencia` | texto | sim | lista tendência; compara `nivel` com o da edição anterior | — | publica |
| `motivo` | texto | sim | o que explica o nível geral: o gatilho mais alto de hoje, ou a origem do nível mantido. Não descreve a regra de descida | 400 | agente |
| `dominios` | lista | sim | exatamente 5, na ordem da lista domínio | — | misto |

Cada item de `alerta.dominios`:

| Campo | Tipo | Obrig. | Valores permitidos | Máx. | Vem de |
|---|---|---|---|---|---|
| `id` | texto | sim | lista domínio | — | agente |
| `nivel` | inteiro | sim | 1 a 5, pela regra R13 | — | publica |
| `tendencia` | texto | sim | lista tendência | — | publica |
| `desde` | data | sim | dia em que o nível atual começou; nunca depois de `data` | 10 | publica |
| `sem_preco` | lista de texto | sim | ids dos indicadores de preço do domínio sem dado hoje (R13f); vazia quando o preço foi medido | — | publica |
| `gatilhos` | lista | sim | 0 a 6 itens; vazia quer dizer "nenhum gatilho hoje". Os de preço entram pelo `publica.py`; os de evento, até 4, são do agente | — | misto |
| `leitura` | texto | sim | por onde o efeito chega a quem está no Brasil e o que as notícias de hoje mudam nesse caminho. Prazo e número só com fonte do dia. Sem previsão de preço. Sem verbo de ação para o leitor | 300 | agente |
| `vigiar` | texto | sim | o próximo sinal que mudaria o nível | 200 | agente |

Cada item de `gatilhos`:

| Campo | Tipo | Obrig. | Valores permitidos | Máx. | Vem de |
|---|---|---|---|---|---|
| `criterio` | texto | sim | código `dominio.nivel`, nível de 2 a 5, igual ao `codigo` da célula em `regua.json` (`niveis_alerta[].criterios.DOMINIO.codigo`) | — | agente |
| `ref` | texto | sim | id de um item desta edição (`p1`, `r4`); em gatilho de preço, id de um indicador desta edição (`brent`) | — | agente |
| `texto` | texto | sim | o que aconteceu, com número ou data; estado que continua começa com "Segue em DD/MM:" | 200 | agente |
| `excecao` | booleano | não | `true` quando o fato não está na tabela, mas equivale ao nível citado (R13d) | — | agente |
| `alivio` | booleano | não | `true` quando acabou o estado que sustentava um nível 4 ou 5 (R13e) | — | agente |

Gatilho de preço (`ref` de indicador) vem pronto em `/tmp/info/indicadores.json`. O `publica.py` copia para
o domínio, na frente dos gatilhos do agente. Gatilho com `ref` de indicador que vier no rascunho é trocado.

## 3. `indicadores[]`

O agente não escreve esta lista. O `publica.py` copia de `/tmp/info/indicadores.json`, que segue a ordem
do catálogo (`dados/indicadores.json`, seção 14).

| Campo | Tipo | Obrig. | Valores permitidos | Máx. | Vem de |
|---|---|---|---|---|---|
| `id` | texto | sim | id do catálogo; sem repetir | — | indicadores |
| `nome` | texto | sim | nome para o leitor, do catálogo | 60 | indicadores |
| `dominio` | texto | sim | lista domínio, do catálogo | — | indicadores |
| `valor` | número ou `null` | sim | maior que zero; `null` = sem dado hoje | — | indicadores |
| `unidade` | texto | sim | do catálogo; ex.: `US$ por barril`, `R$ por US$` | 30 | indicadores |
| `variacao_pct` | número ou `null` | sim | variação sobre o ponto anterior da série, 1 casa | — | indicadores |
| `variacao_7d_pct` | número ou `null` | sim | variação sobre o ponto mais novo com data de 7 a 10 dias antes, 1 casa; `null` em indicador mensal ou sem ponto nessa faixa | — | indicadores |
| `data` | data ou `null` | sim | dia da cotação, no fuso da bolsa quando a fonte informa (senão, em UTC); nunca depois de `data` da edição | 10 | indicadores |
| `defasado` | booleano | sim | `true` se `valor` é `null` ou a cotação é velha (diária: mais de 4 dias; mensal: mais de 62) | — | indicadores |
| `confirmado` | booleano | sim | `true` só quando a alta cumpre critério de preço de nível 3 ou 4 e uma segunda fonte do catálogo confirma (R13c); nos outros casos, `false` | — | indicadores |
| `fonte` | objeto | sim | `{"nome": texto até 60, "url": URL}`: a fonte usada hoje; se nenhuma respondeu, a primeira do catálogo | — | indicadores |

## 4. `principais[]`

| Campo | Tipo | Obrig. | Valores permitidos | Máx. | Vem de |
|---|---|---|---|---|---|
| `id` | texto | sim | `p1`, `p2`, `p3`, nesta ordem | — | agente |
| `categoria` | texto | sim | lista categoria | — | agente |
| `titulo` | texto | sim | descritivo, sem adjetivo | 120 | agente |
| `fato` | texto | sim | quem, o quê, onde, quando, quanto; só o que os dois campos afirmam igual ou um documento primário mostra | 500 | agente |
| `nao_confirmado` | lista de texto | não | 0 a 3; cada um começa com "Segundo " | 240 cada | agente |
| `ataques` | lista | sim | 2 a 4 itens, de 2 partidos ou mais | — | agente |
| `realmente` | texto | sim | o dossiê "o que está realmente acontecendo"; de 800 a 1.500 caracteres (R23); não repete `fato`, `ataques`, `na_pratica` nem `placar` | 1500 | agente |
| `na_pratica` | lista de texto | sim | 1 a 4; só mudança medida; se nada mudou, um item só, que diz isso | 200 cada | agente |
| `no_brasil` | texto | só se `dominios` não é vazia | o que esta notícia tende a encarecer, baratear, faltar ou atrasar no Brasil, e por qual caminho; número e prazo só com fonte do dia | 240 | agente |
| `eixo` | objeto | não | tabela abaixo: o tema da régua em que um ato da notícia mexe | — | agente |
| `placar` | lista | sim | 0 a 4; no máximo uma linha por partido | — | agente |
| `sem_placar` | texto | só se `placar` é vazia | por que ninguém ganha nem perde ainda, e o que teria de acontecer para haver ganhador | 160 | agente |
| `vetores` | lista | sim | 0 a 2 | — | agente |
| `dominios` | lista de texto | sim | 0 a 5 ids da lista domínio, sem repetir | — | agente |
| `vigiar` | lista de texto | sim | 1 a 3 perguntas de sim ou não, com data limite (R21); a primeira é a que derruba a leitura do dossiê | 200 cada | agente |
| `confianca` | texto | sim | `alta` ou `media` | — | agente |
| `conflito_de_interesse` | booleano | não | `true` nos casos da regra R19; o `publica.py` liga sozinho, e o agente também pode ligar | — | misto |
| `continuacao_de` | texto | não | `AAAA-MM-DD/pN` ou `AAAA-MM-DD/rN`: o item anterior, principal ou radar, que este continua | 14 | agente |
| `fontes` | lista | sim | 3 a 8 itens | — | agente |

Cada item de `ataques` (e o objeto `ataque` do radar):

| Campo | Tipo | Obrig. | Valores permitidos | Máx. | Vem de |
|---|---|---|---|---|---|
| `veiculo` | texto | sim | id que existe em `dados/veiculos.json`; nunca `outro` | — | agente |
| `lado` | texto | sim | o `lado` desse veículo no mapa (id de partido) | — | mapa |
| `alvo` | texto | sim | id de player, id de partido, `outro` ou `nenhum` (lista alvo especial) | — | agente |
| `alvo_nome` | texto | só se `alvo` = `outro` | nome de quem é o alvo | 60 | agente |
| `enquadramento` | texto | sim | o que este veículo destacou e com que palavras | 240 | agente |
| `omite` | texto | não | o que está no fato e não aparece na página deste veículo; só de página aberta nesta execução (T5) | 200 | agente |
| `url` | URL | sim | tem de estar em `fontes` do mesmo item (R05) | 500 | agente |

O objeto `eixo` (em principal e em item do radar):

| Campo | Tipo | Obrig. | Valores permitidos | Máx. | Vem de |
|---|---|---|---|---|---|
| `tema` | texto | sim | lista tema atual | — | agente |
| `sentido` | texto | sim | lista sentido: o polo para onde o ato empurra | — | agente |
| `porque` | texto | sim | o ato (lei, decreto, decisão, compra), sem adjetivo | 160 | agente |

Cada item de `placar`:

| Campo | Tipo | Obrig. | Valores permitidos | Máx. | Vem de |
|---|---|---|---|---|---|
| `partido` | texto | sim | lista partido | — | agente |
| `efeito` | texto | sim | lista efeito | — | agente |
| `forca` | inteiro | sim | lista força | — | agente |
| `evidencia` | texto | sim | lista evidência | — | agente |
| `porque` | texto | sim | quem ganhou ou perdeu, pelo nome, e o quê; ou "Na pauta de [tema]: …"; em linha de narrativa, qual veículo usou o fato | 200 | agente |

Cada item de `vetores`:

| Campo | Tipo | Obrig. | Valores permitidos | Máx. | Vem de |
|---|---|---|---|---|---|
| `player` | texto | sim | id que já existe em `dados/players.json` | — | agente |
| `para` | texto | sim | id de partido; diferente do partido do player e de `independentes` | — | agente |
| `forca` | inteiro | sim | 1, 2 ou 3 | — | agente |
| `tema` | texto | sim | lista tema atual, ou `ordem` (R11) | — | agente |
| `porque` | texto | sim | o ato do player que mostra o deslocamento | 240 | agente |
| `url` | URL | sim | prova do ato; tem de estar em `fontes` do mesmo item, em fonte forte (R11) | 500 | agente |

Cada item de `fontes`:

| Campo | Tipo | Obrig. | Valores permitidos | Máx. | Vem de |
|---|---|---|---|---|---|
| `veiculo` | texto | sim | id de `dados/veiculos.json`, ou `outro` (veículo fora do mapa, seção 15). É o dono do site da `url` (T4) | — | agente |
| `nome` | texto | só se `veiculo` = `outro` | quem publicou | 80 | agente |
| `titulo` | texto | sim | título original, como publicado | 200 | agente |
| `url` | URL | sim | sem repetir dentro do item | 500 | agente |
| `publicado_em` | data | sim | data que aparece na página ou no feed (R09, T3) | 10 | agente |
| `primaria` | booleano | não | `true` para documento oficial, texto de lei, dado de mercado ou comunicado da parte; só nos casos da regra R22 | — | agente |

## 5. `radar[]`

| Campo | Tipo | Obrig. | Valores permitidos | Máx. | Vem de |
|---|---|---|---|---|---|
| `id` | texto | sim | `r1` a `r12`, em ordem | — | agente |
| `categoria` | texto | sim | lista categoria | — | agente |
| `titulo` | texto | sim | como nas principais | 120 | agente |
| `fato` | texto | sim | como nas principais | 300 | agente |
| `ataque` | objeto | sim | um só; mesmos campos de `ataques[]` | — | agente |
| `eixo` | objeto | não | como nas principais | — | agente |
| `placar` | lista | sim | 0 a 2; mesmos campos | — | agente |
| `sem_placar` | texto | só se `placar` é vazia | como nas principais | 160 | agente |
| `vetores` | lista | sim | 0 ou 1; mesmos campos | — | agente |
| `dominios` | lista de texto | sim | 0 a 5 ids, sem repetir | — | agente |
| `confianca` | texto | sim | lista confiança | — | agente |
| `conflito_de_interesse` | booleano | não | como nas principais | — | misto |
| `continuacao_de` | texto | não | como nas principais | 14 | agente |
| `fontes` | lista | sim | 1 a 4; mesmos campos | — | agente |

## 6. `placar_do_dia[]`

| Campo | Tipo | Obrig. | Valores permitidos | Máx. | Vem de |
|---|---|---|---|---|---|
| `partido` | texto | sim | lista partido; sem repetir | — | agente |
| `saldo` | inteiro | sim | soma das forças do dia, só das linhas que não são de narrativa: `ganha` soma, `perde` subtrai | — | publica |
| `narrativa` | inteiro | sim | linhas de narrativa a favor menos linhas de narrativa contra | — | publica |
| `frase` | texto | sim | o dia desse partido em uma frase | 160 | agente |

A lista é ordenada por `publica.py`: maior saldo primeiro; empate segue a ordem da régua.
O site mostra `saldo` e `narrativa` separados: ganhar argumento não é ganhar na prática.

## 7. `novos_players[]`

Mesmos campos de um player de `dados/players.json`, menos `origem` e `incluido_em`, mais três.
O partido é o de `voto_tipico` (em `regua.json`, lista `partidos`) com mais posições iguais às do `dna`;
empate dá `independentes`. Com menos de 4 posições conhecidas, o ator não entra (R20).

| Campo | Tipo | Obrig. | Valores permitidos | Máx. | Vem de |
|---|---|---|---|---|---|
| `id` | texto | sim | `^[a-z][a-z0-9_]{1,30}$`; não pode ser id de outro player nem de partido | 31 | agente |
| `nome` | texto | sim | nome para o leitor | 60 | agente |
| `tipo` | texto | sim | `governo`, `instituicao` ou `empresa` | — | agente |
| `partido` | texto | sim | lista partido, pela conta da regra R20 | — | agente |
| `time` | texto | sim | lista time | — | agente |
| `time_discutivel` | booleano | sim | sempre `true` em player novo: quem confirma o time é o dono | — | agente |
| `dna` | objeto | sim | as 7 chaves de tema, na ordem da régua (outra ordem não é recusada: o `publica.py` regrava na ordem); valor `B`, `R`, `Y` ou `W` (a rotina não registra virada) | — | agente |
| `dna_fontes` | objeto | sim | uma URL para cada tema com posição conhecida (`B`, `R` ou `Y`), e só para eles; página aberta nesta execução | — | agente |
| `duvidas` | lista de texto | sim | ids de tema com posição incerta; pode ser vazia | — | agente |
| `nota` | texto | sim | quem é, em uma linha | 200 | agente |
| `justificativa` | texto | sim | por que entrou hoje e por que esse partido | 400 | agente |
| `url` | URL | sim | fonte da justificativa | 500 | agente |

## 8. `errata[]` e `respostas[]`

| Campo | Tipo | Obrig. | Valores permitidos | Máx. | Vem de |
|---|---|---|---|---|---|
| `edicao` | data | sim | edição anterior que existe; antes de `data` | 10 | agente |
| `item` | texto | não | id do item corrigido (`p2`, `r5`); sem o campo, vale para a edição toda | — | agente |
| `erro` | texto | sim | o que estava errado | 300 | agente |
| `correcao` | texto | sim | o certo | 300 | agente |
| `url` | URL | não | fonte da correção; obrigatória com `anula_vetor` | 500 | agente |
| `anula_vetor` | texto | não | `id` de uma entrada de `dados/vetores.json` que esta errata desfaz (seção 12) | 60 | agente |

Edição publicada não muda. A correção mora na `errata` da edição de hoje.

Cada item de `respostas` (a resposta a uma pergunta de `vigiar` que venceu):

| Campo | Tipo | Obrig. | Valores permitidos | Máx. | Vem de |
|---|---|---|---|---|---|
| `edicao` | data | sim | a edição que fez a pergunta; antes de `data` | 10 | agente |
| `item` | texto | sim | id da principal que fez a pergunta (`p1`, `p2`, `p3`) | — | agente |
| `pergunta` | texto | sim | cópia da pergunta: o primeiro `vigiar` daquela principal | 200 | agente |
| `resposta` | texto | sim | lista resposta | — | agente |
| `texto` | texto | sim | o que houve, com data. Se desmente o dossiê daquele dia, começa com "O INFOCENARIUM leu errado em DD/MM:" | 240 | agente |
| `url` | URL | não | a fonte da resposta; obrigatória com `sim` e com `nao` | 500 | agente |

## 9. `bastidores`

| Campo | Tipo | Obrig. | Valores permitidos | Máx. | Vem de |
|---|---|---|---|---|---|
| `modo` | texto | sim | lista modo: `feeds` (coleta normal) ou `busca` (coleta falhou) | — | agente |
| `veiculos_consultados` | inteiro | sim | veículos distintos do mapa citados em `fontes` | — | publica |
| `feeds_ok` | inteiro | sim | de `coleta.json`; 0 se não houver | — | publica |
| `feeds_falhos` | inteiro | sim | de `coleta.json`; 0 se não houver | — | publica |
| `paginas_lidas` | inteiro | sim | 0 ou mais | — | agente |
| `buscas` | inteiro | sim | 0 ou mais | — | agente |
| `minutos` | inteiro | sim | duração até o fecho do rascunho | — | agente |
| `injecoes_ignoradas` | inteiro | sim | trechos da web que davam ordens e foram ignorados | — | agente |
| `candidatos` | lista | sim | 0 a 5 de `{"id": slug, "nome": até 60, "motivo": até 160}`: atores centrais sem ficha na régua | — | agente |
| `veiculos_sugeridos` | lista de texto | sim | 0 a 5 veículos fora do mapa que fizeram falta, no formato `Nome (dominio.com)` | 80 cada | agente |
| `limites` | texto | sim | o que não deu para conferir hoje, e que campo ficou em silêncio; nunca vazio | 500 | agente |

## 10. Regras entre campos

O validador confere todas. Cada erro cita o código da regra. Regra, ou trecho de regra, marcado **(dia)**
vale só para a edição do dia (seção 0). O resto vale para toda edição.

**Princípio das regras do dia.** Trecho de regra que depende de dado que o dono pode rever (a régua, o mapa de
veículos, o catálogo) só vale para a edição do dia. Assim, o dono rever um dado nunca faz edição antiga falhar
nem trava a publicação. Esses trechos estão marcados **(dia)** abaixo: o que cruza a edição com o mapa, com o
catálogo e os limiares de preço, com as listas `conflito` e `sites_oficiais` e com o `voto_tipico` dos partidos.
Também é **(dia)** o prazo da primeira pergunta de `vigiar` (R21): ele se julga no dia em que é escrito.
Valem sempre os ids da régua (partidos, temas, domínios, evidências, forças e códigos de critério), que são a
forma deste esquema, e o que depende de `players.json` e `vetores.json`, registros que só crescem.

**Qual código sai.** Quando duas regras cobrem o mesmo defeito, sai o código desta lista:

- `alvo` que não é player, partido, `outro` nem `nenhum`: R02.
- `player` de vetor que não existe em `players.json`: R11.
- `realmente` fora de 800 a 1.500 caracteres: R23. O resto do texto do dossiê segue a R17.
- Tipo errado, data ou data-hora mal escrita: R00. URL fora do formato da seção 0: R17.
- Nível, tendência ou `desde` que não fecham com a conta: R13 e R14 (na edição `falha`, R15), com ou sem
  histórico. Alívio sem histórico: R13e. O código H1 não aparece na saída: a H1 diz o que muda na conferência
  quando falta histórico.
- Alívio junto com `excecao`: R13e.
- Edição `falha` com `placar_do_dia`: R15 e R12, os dois.
- Rascunho com `exemplo`: T2, e também R18 em cada título sem a marca `[EXEMPLO]`.

**Identidade e referência**

- **R00.** Estrutura: tipo certo, campo obrigatório presente, nenhum campo desconhecido, valor dentro da lista,
  e contagem dentro do intervalo das tabelas. Onde uma regra numerada dá o número, sai ela: R06 (principal com
  menos de 3 fontes), R07 (item do radar sem fonte), R10 (duas linhas do mesmo partido num placar), R11 (mais de
  2 vetores na edição), R13d (mais de 1 exceção), R13e (mais de 1 alívio no domínio), R15 (principais e radar
  fora da contagem do estado; lista que a edição `falha` esvazia) e R20 (mais de 1 player novo).
- **R01.** Ids únicos e em ordem: `p1..pN` nas principais, `r1..rN` no radar. Em `edicoes/`, `data` é igual ao
  nome do arquivo.
- **R02.** Toda referência existe. Partido, tema e domínio: em `regua.json`. Player: em `players.json`; como
  `alvo`, vale também o de `novos_players` desta edição. **(dia)** Veículo: em `veiculos.json`.
  **(dia)** Indicador: em `dados/indicadores.json`, sem repetir.
- **R03.** **(dia)** `lado` do ataque é igual ao `lado` do veículo no mapa. Em principal, o veículo do ataque
  tem `lado_confianca` `alta` ou `media`: veículo de lado incerto não atira em principal.
- **R04.** `alvo` é id de player, id de partido, `outro` ou `nenhum`. `alvo_nome` existe se, e só se, `alvo` é
  `outro`. `nome` da fonte existe se, e só se, `veiculo` é `outro`. `veiculo` de ataque nunca é `outro`.
- **R05.** Toda `url` de ataque e de vetor aparece em `fontes` do mesmo item; no ataque, com o mesmo `veiculo`.
  Dentro de um item, nenhuma `url` de fonte se repete.

**Fonte, confiança e data**

- **R06.** **(dia)** Principal: 3 fontes ou mais; veículos de 2 partidos ou mais; 1 fonte forte ou mais.
  Os `ataques` também vêm de 2 partidos ou mais. Fonte `outro` não conta como partido.
- **R07.** **(dia)** Radar: 1 fonte forte, ou 2 fontes de veículos de partidos diferentes.
- **R08.** **(dia)** Teto de confiança. `alta`: fontes de veículos dos dois campos e 1 forte.
  `media`: 2 fontes de veículos de partidos diferentes, ou 1 forte. Senão, `baixa`. O agente pode declarar
  menos que o teto, nunca mais.
- **R09.** `publicado_em` fica entre `data` menos 2 dias e `data` mais 1 dia (a folga cobre o fuso).
  Fonte `primaria` pode ser mais antiga, nunca depois de `data` mais 1.
- **R19.** Conflito de interesse. O modelo que escreve o INFOCENARIUM é da Anthropic. `conflito_de_interesse` tem de
  ser `true` se:
  - (a) a `categoria` do item é `ia`; ou
  - (b) **(dia)** algum `alvo` de ataque ou `player` de vetor do item está em `regua.json`, lista
    `conflito.players`; ou
  - (c) **(dia)** algum texto do item, inclusive título de fonte, traz um termo de `conflito.termos`. Vale a palavra
    inteira, escrita como na lista e sem hífen antes: "Jean-Claude" não conta; ou
  - (d) **(dia)** alguma fonte do item é de veículo que tem `anthropic` em `serve_a` ou em `alvos` no mapa.

  O `publica.py` liga a marca nesses casos. O agente pode ligar em outros; ninguém desliga.
  Com a marca em `true`: `confianca` no máximo `media`; vetor do item só com `url` de fonte `primaria`.
  Nos casos (b), (c) e (d), **(dia)** fontes de veículos de 2 partidos ou mais, também no radar.
- **R22.** **(dia)** Fonte primária. `primaria: true` só vale em fonte de veículo do mapa com `tipo` `oficial` ou
  `dados`, ou em fonte `outro` cujo site bate com um sufixo de `regua.json`, chave `sites_oficiais`
  (listas `brasil` e `outros`).

**Placar, vetor e sinais**

- **R10.** `evidencia: narrativa` só com `forca` 1. `forca` 2 ou 3 exige evidência diferente de `narrativa`.
  No máximo uma linha por partido em cada item. **(dia)** No radar, `forca` 3 exige fonte forte no item.
  Item com `confianca: baixa` tem `placar` vazia. `sem_placar` existe se, e só se, `placar` é vazia.
- **R11.** Vetor: `player` existe em `players.json` e não é o de `novos_players` desta edição; `para` é diferente
  do partido do player e de `independentes`; no máximo 2 vetores na edição; um só por par player e destino; e,
  em cada item, um só vetor por player (o `id` do registro é data, item e player: seção 12).
  **(dia)** O item tem fontes de veículos de 2 partidos ou mais, e a `url` do vetor é de fonte forte.
  `tema` é da lista tema atual, ou `ordem`. **(dia)** Com tema atual, o voto típico de `para` nesse tema é `B`
  ou `R` e é diferente do voto típico do partido do player (player de `independentes` não tem voto típico:
  basta a primeira parte).
- **R12.** `placar_do_dia` tem exatamente os partidos que aparecem em algum `placar` do dia, na ordem da seção 6.
  `saldo` = soma das forças com `ganha` menos soma das forças com `perde`, em principais e radar, só das
  linhas com `evidencia` diferente de `narrativa`. `narrativa` = linhas de narrativa com `ganha` menos linhas
  de narrativa com `perde`. Partido que só tem linha de narrativa aparece com saldo 0.
  `bastidores.veiculos_consultados` é a contagem de veículos distintos do mapa em `fontes`.
- **R21.** Cada texto de `vigiar` de uma principal termina com `?` e traz uma data no formato `DD/MM`.
  **(dia)** Na primeira pergunta, o prazo (a última data `DD/MM` do texto, lida como o primeiro dia assim a
  partir de `data`; é a leitura do `publica.py contexto`) fica entre `data` e 30 dias depois, os dois inclusive:
  a data limite vem por último. É a primeira que volta em `vigiar_vencendo`; nas outras, o prazo não é lido.
- **R23.** Na principal: `realmente` tem de 800 a 1.500 caracteres; `no_brasil` existe se, e só se, `dominios`
  não é vazia.

**Alerta**

- **R13.** Nível do domínio. É calculado pelo `publica.py` e conferido pelo validador. Sejam:
  - `T`: o maior nível entre os `criterio` de hoje, sem contar gatilho de alívio (1 se não há nenhum);
  - `N`: o nível do domínio na edição anterior (1 se não há edição anterior);
  - `S`: a conta de edições calmas. Ande pelas edições anteriores, da mais nova para a mais velha, enquanto
    o domínio está no nível `N`. Pule a `falha`. Pare na que tem gatilho de nível `N` ou mais (o de alívio
    conta: a calma começa a ser contada depois dele). Das outras, conte as que não são cegas para o domínio.

  Então:
  - se `T` ≥ `N`: `nivel` = `T`;
  - se `T` < `N` e há gatilho de alívio válido (R13e): `nivel` = `N` − 1;
  - se `T` < `N`, `S` ≥ 2 e a edição de hoje não é cega para o domínio: `nivel` = `N` − 1;
  - nos outros casos: `nivel` = `N` (nível mantido).

  R13 e R13c não valem para edição `falha`: nela os níveis só repetem os da edição anterior (R15).
- **R13a.** `criterio` tem a forma `dominio.nivel`, com nível de 2 a 5, e existe na régua. O domínio do
  `criterio` é o `id` do domínio onde o gatilho está. `ref` existe na edição: id de item, ou, só em gatilho
  de preço, id de indicador.
- **R13b.** Prova por nível, em gatilho com `ref` de item. O item tem `confianca` `alta` ou `media`.
  Nível 2 aceita principal ou radar. Nível 3 exige principal. Níveis 4 e 5 exigem principal com confiança
  `alta`. Nível 5 exige ainda uma fonte `primaria` no item; em `energia`, `alimentos`, `cambio` e
  `suprimentos`, **(dia)** com site que bate com a lista `sites_oficiais.brasil`.
  **Estado que continua.** Os critérios de evento dos níveis 4 e 5 são estados: valem enquanto duram.
  Gatilho de nível 4 ou 5 com o mesmo `criterio` da origem do nível, num domínio que estava nesse nível ou
  acima na edição anterior, e cuja origem não é alívio nem gatilho de preço, aceita principal ou radar, e
  não exige de novo a fonte `primaria`. Alta de preço não se repete à mão: o indicador é medido de novo
  todo dia.
- **R13c.** **(dia)** Preço. Para cada indicador não defasado, valem os critérios `precos` da régua: só alta
  conta; a variação já vem arredondada a 1 casa; variação `null` não cumpre; critério de janela `1d` só vale
  quando a `data` do indicador é a `data` da edição. Fica o critério cumprido de maior nível. Se ele é de
  nível 3 ou 4 e `confirmado` é `false`, vale como nível 2. O domínio traz exatamente esses gatilhos de preço,
  cada um com `ref` igual ao id do indicador.
- **R13d.** `excecao: true` só com nível 2 ou 3, `ref` de item, e no máximo 1 por edição.
- **R13e.** Alívio. `alivio: true` só em domínio que estava em nível 4 ou 5 na edição anterior, por evento:
  a origem do nível não é gatilho de preço nem outro alívio. `criterio` igual ao da origem; `ref` de principal
  com confiança `alta`; no máximo 1 por domínio; nunca junto com `excecao`. Gatilho de alívio não conta em `T`.
- **R13f.** **(dia)** `sem_preco` lista, na ordem do catálogo, os indicadores citados nos critérios `precos` do
  domínio, em qualquer nível, que hoje faltam em `indicadores`, têm `valor` `null`, têm `defasado: true` ou
  têm `variacao_7d_pct` `null`.
- **R14.** `alerta.nivel` é o maior nível dos domínios. `alerta.tendencia` compara `alerta.nivel` com o da
  edição anterior; a `tendencia` de cada domínio compara o `nivel` do domínio com o do mesmo domínio na edição
  anterior (`subindo`, `descendo`; igual ou sem anterior, `estavel`).
  `desde` repete o da edição anterior se o nível é o mesmo; senão é `data`.

**Contagens, texto e marcas**

- **R15.** Contagens por `estado`:

  | Estado | `principais` | `radar` | Radar de IA | Geopolítica nas principais |
  |---|---|---|---|---|
  | `completa` | 3 | 6 a 12 | 3 ou mais | 1 ou mais |
  | `reduzida` | 1 a 3 | 3 a 12 | 0 ou mais | — |
  | `falha` | 0 | 0 | — | — |

  Em `falha`: `placar_do_dia`, `novos_players`, `errata`, `respostas` e todos os `gatilhos` vazios; níveis e
  `desde` iguais aos da edição anterior (sem anterior, tudo em 1). `sem_preco` segue a R13f.
- **R16.** `errata[].edicao` e `respostas[].edicao` são anteriores a `data`. `continuacao_de` aponta para data
  anterior a `data`. `errata[].anula_vetor` exige `url` na mesma errata. `respostas[].url` existe quando a
  `resposta` é `sim` ou `nao`. `respostas[].item` é id de principal.
- **R17.** Texto: tamanhos máximos; nenhum texto vazio; sem `<` seguido de letra ou barra; sem caractere de
  controle (os de código 0 a 31 e 127 a 159, que incluem a quebra de linha e a tabulação, e os separadores
  U+2028 e U+2029: todo texto é corrido, numa linha só); sem metade solta de caractere (U+D800 a U+DFFF, como
  a de um emoji escrito pela metade: não se grava em UTF-8); sem as marcas que reordenam o texto (U+202A a
  U+202E e U+2066 a U+2069: o leitor veria as letras em outra ordem; U+200E, U+200F e o U+200D dos emojis podem);
  sem e-mail; sem `/home/`, `/Users/` nem `C:\`; sem endereço (`http:`, `https:` e `www.` em qualquer caixa, e
  `://`; "HTTP 403" não é endereço), sem `](` e sem `![` fora de campo `url`; sem número no
  formato de CPF (`000.000.000-00`) nem de telefone (`(00) 00000-0000`, ou `+` seguido de 10 dígitos ou mais,
  que podem vir separados por espaço, ponto, hífen ou parênteses); nenhum texto feito só de algarismos (é sobra
  do `modelo.txt`), salvo `fontes[].titulo`. URL no formato da seção 0. Arquivo até 60 KB (61.440 bytes).
- **R18.** Com `exemplo: true`, todo `titulo` (de item e de fonte) começa com `[EXEMPLO]`. Sem `exemplo`,
  nenhum título começa assim. Rascunho com `exemplo` é recusado.
- **R20.** Player novo: no máximo 1. O `id` não existe em `players.json`, salvo como o próprio registro já
  publicado (`origem: "rotina"` e `incluido_em` igual a `data`). `tipo` nunca é `regime`. `time_discutivel` é
  `true`. O `dna` só traz `B`, `R`, `Y` ou `W`, e tem 4 posições conhecidas ou mais (diferentes de `W`).
  `dna_fontes` tem uma URL para cada posição conhecida, e só para elas. **(dia)** `partido` é o de
  `voto_tipico` com mais posições iguais às conhecidas do `dna`; empate dá `independentes`. `duvidas` só traz
  ids de tema. A ordem das chaves do `dna` não é motivo de recusa.

**Regras de histórico** (precisam das outras edições: arquivo dentro de `edicoes/`, ou `--anterior`)

- **H1.** R13 e R14 conferidas contra as edições anteriores de verdade. Sem histórico à mão (arquivo fora
  de `edicoes/`, como o exemplo), o validador aceita `nivel` igual a `T`, ou maior que `T` quando `desde`
  é anterior a `data` (nível mantido); não confere `tendencia`; trata todo gatilho como novo; e recusa `alivio`.
- **H2.** `errata[].edicao`, `continuacao_de` e `respostas[]` apontam para edição e item que existem
  (`continuacao_de`: principal ou radar). `respostas[].pergunta` é igual ao primeiro `vigiar` daquela
  principal. `errata[].anula_vetor` é o `id` de um vetor de `dados/vetores.json` ainda não anulado por outra
  edição: a anulação que a própria edição já gravou no registro não conta, e duas erratas da mesma edição não
  anulam o mesmo vetor.
- **H3.** **(dia)** Aviso, não erro: título de item sem `continuacao_de` quase igual a um título das 3 últimas
  edições anteriores (as que valem como edição anterior, seção 0: a `falha` e o exemplo não contam); vetor igual
  (player e destino) a outro, não anulado, de outra edição dos últimos 7 dias (o sétimo dia antes de `data`
  conta). **Quase igual:** os dois títulos, sem acento, sem pontuação e em minúsculas, têm 10 caracteres ou
  mais e são iguais, ou têm semelhança de 0,85 ou mais pela medida `SequenceMatcher.ratio` do Python.

**Regras da pasta de trabalho** (só em `publica.py edicao`; usam arquivos de `/tmp/info`)

- **T1.** URL vista. Toda URL do rascunho está em `coleta.json` ou em `urls.txt` (páginas abertas nesta
  execução). A comparação usa o endereço limpo (seção 0).
- **T2.** `data` do rascunho é igual ao dia (`--dia`). O rascunho não traz `exemplo` nem `estado: falha`.
- **T3.** Data conferida pela máquina. Uma fonte tem **data conferida** quando a `url` está em `coleta.json`
  (data do feed: o dia UTC da data-hora da manchete) ou em `conferencia.json` com estado `ok` e data (data lida
  na página pelo `coleta.py --confere`). URL que está nos dois vale pela coleta.
  - Nesses casos, `publicado_em` é igual a essa data, com 1 dia de folga.
  - URL com estado `erro` em `conferencia.json`, e fora da coleta, não vale: a página não existe. Vale para
    toda URL que o agente escreve, e não só para `fontes`.
  - Cada principal tem 2 fontes ou mais com data conferida dentro da janela da R09. Item que sustenta
    gatilho tem 1 ou mais; se o gatilho é novo e de nível 3 ou mais, tem 3. Fonte `primaria` não entra
    nessas contas. Gatilho **novo** é o que não é estado que continua (R13b); o de alívio conta como novo:
    "acabou" também precisa de data recente.
  - **Máquina sem rede.** Se nenhum feed respondeu (`coleta.json` com `feeds_ok` 0, ou sem o arquivo) e
    nenhuma página de `conferencia.json` veio `ok`, não há como conferir data: as contas acima não valem.
    Em troca, `bastidores.modo` tem de ser `busca`, e nenhum item sustenta gatilho de nível 3 ou mais.
    O fato grave desse dia vai para a `leitura` e para `limites`, e o alerta sobe quando a rede voltar.
- **T4.** Veículo e endereço. Em fonte de veículo do mapa, o site da `url` bate com um dos `sites` do veículo
  no mapa. Estar em `coleta.json` com esse veículo não basta: um feed comprometido, ou de agregador, pode pôr
  na mesa o endereço de outro site com o nome do veículo. Se não bate, o `veiculo` certo é outro id, ou `outro`.
  Site que dois veículos dividem (seção 15, M2) vale para os dois.
- **T5.** `omite` só em ataque cuja `url` está em `urls.txt`.

**Regras de crescimento** (só com `--base`: conferem o que a rotina mudou)

- **G1.** `dados/players.json`: os players da base continuam iguais e na mesma ordem; só entram novos no fim,
  com `origem: "rotina"`. `atualizado_em` pode mudar.
- **G2.** `dados/vetores.json`: as entradas da base continuam iguais; só entram novas no fim. Vetor não se
  apaga: anula-se, com uma entrada nova (seção 12).
- **G3.** Edição que existe na base (os arquivos `AAAA-MM-DD.json` e `AAAA-MM-DD.md`) não muda nem some.
  Exceção: a de `estado: falha` pode ser trocada por qualquer edição do mesmo dia, inclusive outra falha; não
  pode sumir. O `indice.json` muda sempre.
- **G4.** Só mudam os caminhos permitidos: em `edicoes/`, só `AAAA-MM-DD.json` e `AAAA-MM-DD.md` (com data que
  existe no calendário) e `indice.json`, sem subpasta; `feed.xml`; `dados/players.json` e `dados/vetores.json`.
  A rotina nunca muda `dados/veiculos.json`, `dados/regua.json` nem `dados/indicadores.json`.

**Arquivo que dá ordem a agente** (em `valida.py --tudo`, com ou sem `--base`, e em `--dados`; código `AGENTE`)

- Nenhum arquivo acompanhado pelo git se chama `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md` ou `.mcp.json`, em
  qualquer pasta, nem fica dentro de uma pasta `.claude/`. A sessão da nuvem carrega esses arquivos sozinha,
  antes do manual: um deles plantado transforma o sequestro de um dia em instrução de todo dia. Exceção única:
  `.claude/settings.json` com uma chave só, `attribution` (o texto de atribuição dos commits). A lista é a do
  git (`git ls-files`, o que vai no commit; o conteúdo do `settings.json` também é o do índice do git), nunca a
  do disco: o ambiente de trabalho cria sozinho, fora do git, arquivos em `.claude/`. Sem git na raiz, a regra
  não confere. É ERRO, e para a edição até o dono tirar o arquivo: o `valida.yml` fica vermelho e o dono recebe
  o aviso; a rotina para na seção 1 (`--dados` falhou), e o workflow de publicação recusa toda branch (o `--tudo`
  roda na cópia da `main`). Não ponha na `main` um desses arquivos, nem para ajudar a rotina.

## 11. `edicoes/indice.json`

Gerado por `publica.py` a partir dos arquivos de edição. Mais nova primeiro. Uma entrada por edição.
Traz o bastante para o site desenhar arquivo e histórico sem abrir cada edição.

```json
{
  "versao": 1,
  "atualizado_em": "2026-11-20T21:14:03Z",
  "edicoes": [
    {
      "data": "2026-11-20",
      "arquivo": "edicoes/2026-11-20.json",
      "texto": "edicoes/2026-11-20.md",
      "estado": "completa",
      "nivel": 2,
      "tendencia": "estavel",
      "niveis": {"energia": 2, "alimentos": 1, "cambio": 2, "suprimentos": 1, "conflito": 1},
      "saldos": {"soberanistas": 3, "ordem_global": -2},
      "eixos": {"ia_depois": {"azul": 1, "vermelho": 0}, "clima": {"azul": 0, "vermelho": 1}},
      "indicadores": {"brent": 78.4, "usd_brl": 5.4321},
      "resumo": "O dia em uma frase.",
      "gerada_em": "2026-11-20T21:14:03Z",
      "exemplo": false,
      "corrigida_em": []
    }
  ]
}
```

| Campo | Tipo | Regra |
|---|---|---|
| `atualizado_em` | data-hora ou `null` | igual ao maior `gerada_em` (sem usar o relógio); `null` se não há edição |
| `data` | data | única; ordem decrescente |
| `arquivo`, `texto` | texto | caminhos relativos à raiz do site; os dois arquivos existem |
| `estado`, `nivel`, `tendencia`, `resumo`, `gerada_em` | — | cópia fiel da edição |
| `niveis` | objeto | os 5 domínios, na ordem da régua, com o `nivel` de cada um |
| `saldos` | objeto | partido → `saldo`, copiado de `placar_do_dia` (sem narrativa); vazio se não houve placar |
| `eixos` | objeto | tema → quantos itens do dia têm `eixo` nesse tema, por `sentido` (os dois sentidos, com 0 no que não apareceu); só os temas que apareceram, na ordem em que aparecem na edição (principais, depois radar); vazio se nenhum |
| `indicadores` | objeto | id → `valor`, só dos indicadores com valor e não defasados |
| `exemplo` | booleano | `true` se a edição tem `exemplo: true`; senão `false` |
| `corrigida_em` | lista de datas | edições posteriores cuja `errata` cita esta, em ordem crescente e sem repetir; vazia se nenhuma |

O índice é refeito inteiro a cada publicação. Por isso o validador o compara com o que os arquivos dão, campo a
campo: chave a mais, na raiz ou numa entrada, também é diferença.

## 12. Uma entrada de `dados/vetores.json`

O arquivo é `{"versao": 1, "regra": "…", "vetores": [ … ]}`. O `publica.py` acrescenta no fim, sem duplicar `id`.

```json
{
  "id": "2026-11-20_p1_ue",
  "data": "2026-11-20",
  "item": "p1",
  "player": "ue",
  "de": "centro_atlantico",
  "para": "soberanistas",
  "forca": 1,
  "tema": "imigracao",
  "porque": "O ato do player que mostra o deslocamento.",
  "url": "https://…"
}
```

| Campo | Tipo | Regra |
|---|---|---|
| `id` | texto | `data` + `_` + id do item + `_` + id do player; único |
| `data`, `item` | data, texto | edição e item de origem |
| `player` | texto | existe em `players.json` |
| `de` | texto | o partido do player, copiado de `players.json` |
| `para`, `forca`, `tema`, `porque`, `url` | — | cópia do vetor da edição |
| `conflito_de_interesse` | booleano | `true` quando o item de origem tem a marca; ausente nos outros casos. O site mostra o aviso ao lado do vetor |

**Vetor não se apaga: anula-se.** Para cada `errata[].anula_vetor` da edição, o `publica.py` acrescenta no fim:

```json
{
  "id": "2026-11-21_anula_1",
  "data": "2026-11-21",
  "anula": "2026-11-20_p1_ue",
  "porque": "Cópia do campo correcao da errata.",
  "url": "https://…"
}
```

`anula` é o `id` do vetor desfeito; `porque` copia a `correcao` da errata e `url` copia a `url`.
O site mostra o vetor anulado riscado, com o motivo, e não o conta em reincidência.
O `contexto` não o lista em `vetores_recentes`.

## 13. Um player novo em `dados/players.json`

O `publica.py` copia o item de `novos_players` e acrescenta `origem` e `incluido_em`. Entra no fim da lista.
O partido nunca mais muda.

```json
{
  "id": "republica_exemplo",
  "nome": "República de Exemplo",
  "tipo": "governo",
  "partido": "independentes",
  "time": "mudanca",
  "time_discutivel": true,
  "dna": {
    "pandemia_inicio": "W", "pandemia_depois": "Y", "ia_inicio": "W", "ia_depois": "B",
    "moderacao": "R", "clima": "W", "imigracao": "R"
  },
  "dna_fontes": {
    "pandemia_depois": "https://…", "ia_depois": "https://…", "moderacao": "https://…", "imigracao": "https://…"
  },
  "duvidas": ["moderacao"],
  "nota": "Quem é, em uma linha.",
  "justificativa": "Por que entrou e por que esse partido.",
  "url": "https://…",
  "origem": "rotina",
  "incluido_em": "2026-11-20"
}
```

Os 30 players de origem `regua` não têm `dna_fontes`, `justificativa` nem `url`. O site trata os três campos
como opcionais.

## 14. `dados/indicadores.json` (catálogo dos indicadores)

O catálogo é dado, não código. Diz quais indicadores existem e de onde vem cada número.
O dono troca um endereço morto aqui, sem mexer em script. A rotina só lê: nunca altera este arquivo.
O `indicadores.py` traz os **leitores** (como ler cada formato de resposta); o catálogo diz qual leitor usar.

```json
{
  "versao": 1,
  "atualizado_em": "2026-11-23",
  "regra": "Catálogo dos indicadores e de onde vem cada número. Quem altera é o dono. A rotina só lê.",
  "indicadores": [
    {
      "id": "brent",
      "nome": "Petróleo Brent",
      "unidade": "US$ por barril",
      "dominio": "energia",
      "obrigatorio": true,
      "frequencia": "diaria",
      "faixa": {"min": 10, "max": 400},
      "casas": 2,
      "fontes": [
        {"nome": "Yahoo Finance", "url": "https://…/chart/BZ=F?range=1mo&interval=1d", "leitor": "yahoo_chart",
         "nota": "Contrato futuro. Endereço não oficial.",
         "contratos": {"modelo": "https://…/chart/BZ{c}.NYM?range=1mo&interval=1d", "meses": "FGHJKMNQUVXZ"}},
        {"nome": "CNBC", "url": "https://…/charts/1M.json?symbol=@LCO.1", "leitor": "cnbc_chart",
         "nota": "Contrato futuro. Endereço não oficial."},
        {"nome": "FRED (Fed de St. Louis)", "url": "https://…", "leitor": "fred_csv",
         "nota": "Preço à vista. Atualizado uma vez por semana: o último número tem de 1 a 8 dias de atraso."}
      ]
    }
  ]
}
```

Cada indicador:

| Campo | Tipo | Obrig. | Valores permitidos | Máx. |
|---|---|---|---|---|
| `id` | texto | sim | `^[a-z][a-z0-9_]{1,30}$`; único | 31 |
| `nome` | texto | sim | nome para o leitor leigo, sem termo de mercado (ex.: "Gás natural nos EUA") | 60 |
| `unidade` | texto | sim | uma só por indicador; de preferência a que o leitor usa (quilo, tonelada, barril) | 30 |
| `dominio` | texto | sim | lista domínio | — |
| `obrigatorio` | booleano | sim | `true`: obrigatório, alimenta gatilho de preço; `false`: de contexto, só aparece no site | — |
| `frequencia` | texto | sim | lista frequência | — |
| `faixa` | objeto | sim | `{"min": número, "max": número}`, com 0 ≤ `min` < `max`; valor fora da faixa é recusado | — |
| `casas` | inteiro | não | 0 a 6: casas decimais de `valor`; sem o campo, 2 | — |
| `fontes` | lista | sim | 1 a 5, na ordem de tentativa | — |

Cada fonte:

| Campo | Tipo | Obrig. | Valores permitidos | Máx. |
|---|---|---|---|---|
| `nome` | texto | sim | quem publica o número; aparece no site | 60 |
| `url` | URL | sim | endereço público, gratuito, sem cadastro e sem chave pessoal | 500 |
| `leitor` | texto | sim | lista leitor | — |
| `fator` | número | não | maior que zero: o número lido é multiplicado por ele para chegar à `unidade` do indicador; sem o campo, 1 | — |
| `nota` | texto | não | aviso para o leitor (ex.: "contrato futuro", "atrasa 3 dias") | 200 |
| `contratos` | objeto | não | só em fonte de contrato futuro com endereço de "contrato mais próximo": `{"modelo": URL com a marca {c}, "meses": texto}` (regra C6). Com ele, a variação é medida no mesmo contrato quando a série troca de contrato (`CONTRATO-FERRAMENTAS.md`, seção 2, "Troca de contrato") | — |

Em `contratos`, `modelo` é o endereço do contrato com data, e `{c}` é trocado pelo código do contrato: a letra
do mês e o ano com 2 dígitos (`H27` é março de 2027). `meses` são as letras dos meses em que há contrato, na
ordem do ano, tiradas de `FGHJKMNQUVXZ` (janeiro a dezembro). Ex.: milho,
`https://query1.finance.yahoo.com/v8/finance/chart/ZC{c}.CBT?range=1mo&interval=1d` e `HKNUZ`.

Regras do catálogo (conferidas por `valida.py --dados`, menos C3 e C4, que são de quem monta o arquivo):

- **C1.** Ids únicos. Lista com 1 a 20 indicadores. A ordem do arquivo é a ordem de exibição.
- **C2.** Todo `indicador` citado nos critérios `precos` de `regua.json` existe aqui, com `obrigatorio: true` e
  `frequencia: diaria`.
- **C3.** Todas as fontes de um indicador entregam, depois do `fator`, a mesma unidade, na mesma frequência.
  Preço à vista e contrato futuro dão números um pouco diferentes: quando as fontes misturam os dois,
  a `nota` de cada fonte diz qual é.
- **C4.** A resposta de fonte diária cobre pelo menos 11 dias corridos. Série mais curta deixa
  `variacao_7d_pct` em `null`: o domínio fica cego (`sem_preco`) e o `indicadores.py` termina em `PARCIAL`.
- **C5.** Indicador obrigatório deve ter 2 fontes diárias ou mais. Com uma só, não há segunda fonte para
  confirmar a alta, e o gatilho de preço desse indicador nunca passa do nível 2 (R13c).
- **C6.** Fonte com `contratos`: é um objeto com exatamente as chaves `modelo` e `meses`; `modelo` é URL
  (seção 0) com exatamente uma marca `{c}`; `meses` tem de 1 a 12 letras de `FGHJKMNQUVXZ`, sem repetir, na
  ordem do ano. Fora disso, o `valida.py --dados` dá erro C6, e o `indicadores.py` mede a variação na série da
  fonte, como se o campo não existisse.

O catálogo tem 12 indicadores. Os endereços das fontes foram conferidos um a um em 20 e 23/11/2026.

## 15. O mapa de veículos e o veículo fora do mapa

O mapa (`dados/veiculos.json`) é do dono: é ele quem classifica o lado de cada veículo. **A rotina não
acrescenta nem altera veículo.** O arquivo é `{"versao": 1, "revisado_em": …, "veiculos": [ … ]}`.

Campos do mapa que este contrato usa: na raiz, `revisado_em`; em cada veículo, `id`, `nome`, `tipo`, `lado`,
`lado_confianca`, `fatos`, `serve_a`, `alvos`, `sites` e `feeds`. Os outros campos de cada veículo são
descritivos: `pais`, `idiomas`, `controle` e `controle_fonte`, `lado_porque`, `fatos_nota`, `uso`, `feeds_nota`
e, em cada feed, `url`, `secao`, `formato`, `conferido` e `nota`.
Dois são novos, e o `valida.py --dados` confere:

- **M1.** `revisado_em`, na raiz: a data em que o dono terminou de revisar os lados, ou `null` enquanto o mapa
  é rascunho. Com `null`, o site avisa em toda tela que usa lado: "mapa em rascunho, ainda sem revisão do dono".
- **M2.** `sites`, em cada veículo: lista de 1 a 6 nomes de site do veículo, sem repetir, em minúsculas, sem
  `www.`, sem barra e sem porta (ex.: `["reuters.com"]`). É o que liga o veículo ao endereço da fonte (regra T4).
  Dois veículos podem ter o mesmo site quando só o caminho os separa (`bbc` e `bbc_brasil`; `planalto` e
  `itamaraty`; `comissao_europeia` e `eu_ai_office`). A regra T4 aceita o endereço com qualquer um dos dois.

`feeds_nota`, campo opcional de cada veículo, diz por que o veículo não tem feed ou onde ler as manchetes dele.
Se existe, não é vazio. O `valida.py --dados` não confere este campo.

Quando a fonte não está no mapa:

| Onde | Regra |
|---|---|
| Edição | a fonte entra em `fontes` com `veiculo: "outro"` e `nome`. Nunca em `ataques` nem em `ataque` |
| Contas | não conta como partido nem como campo (R06, R07, R08, R19). Só é fonte forte se for `primaria: true`, e só de site oficial (R22) |
| Validador | aceita `outro` em `fontes`, com `nome`; recusa em ataque (R04) |
| Site | mostra o `nome`, a etiqueta "fora do mapa" no lugar da sigla do partido, e o link |
| Dono | a lista `bastidores.veiculos_sugeridos` de cada edição diz o que fez falta |

## 16. O que o site usa de cada parte

| Tela | Campos |
|---|---|
| Carimbo e avisos | `data`, `gerada_em`, `estado`, `exemplo`, `errata`, `indice.corrigida_em` |
| Alerta geral | `alerta.nivel`, `tendencia`, `motivo`, `resumo`; rótulo e significado em `regua.niveis_alerta`. O site escreve o que mudou desde a edição anterior, comparando os níveis de hoje com `niveis` da edição anterior no índice ("Desde 18/11: energia 2 → 3") |
| Domínios | `alerta.dominios[]`; nome, descrição e `canal` em `regua.dominios`; "mantido desde" quando `gatilhos` é vazia e `nivel` > 1; com `sem_preco` não vazia, "sem dado de preço de: …" ao lado do nível; gatilho com `alivio` aparece como alívio |
| Indicadores | `indicadores[]`; "sem dado" quando `valor` é `null`; carimbo de data quando `defasado`; fonte com link. `confirmado` não aparece: o `texto` do gatilho já diz |
| Principais | todos os campos da seção 4; nome do veículo e "lado incerto" (`lado_confianca: baixa`) vêm do mapa; fogo amigo só quando o alvo é do mesmo partido do `lado` e o veículo tem `lado_confianca` `alta` ou `media`; ao lado de `omite`, "segundo a leitura do INFOCENARIUM em DD/MM" e o link da matéria; `eixo` com o nome do tema e o texto do polo que está em `regua.temas` (sem as palavras "azul" e "vermelho"); `sem_placar` no lugar do placar vazio; aviso fixo quando `conflito_de_interesse` é `true` |
| Radar | todos os campos da seção 5 |
| Placar do dia | `placar_do_dia[]`, com `saldo` e `narrativa` separados; partido ausente aparece com saldo 0 e sem frase |
| Movimentos | `vetores` de todos os itens, `novos_players`; reincidência por `dados/vetores.json`; vetor anulado aparece riscado, com o motivo; aviso ao lado do vetor com `conflito_de_interesse` |
| Respostas | `respostas[]`: a pergunta, a resposta e o link para a edição que perguntou |
| Bastidores | `bastidores`, com `candidatos`, `veiculos_sugeridos` e `limites` |
| Arquivo e histórico | `edicoes/indice.json` (`nivel`, `niveis`, `saldos`, `eixos`, `indicadores`, `resumo`); edição `exemplo` fica fora de histórico e de acumulado |
| Régua | `regua.json`, `players.json`, `veiculos.json`, `vetores.json`; com `veiculos.revisado_em` `null`, o aviso de mapa em rascunho |
| Método | `regua.niveis_alerta` (tabela de critérios), `regua.dominios`, `regua.campos`, `regua.forcas`, `regua.evidencias`, `regua.times_avanco`, `regua.conflito`, `dados/indicadores.json` (de onde vem cada número) |

Dois avisos fixos, que o agente não escreve:

- em item com `conflito_de_interesse: true`: "Aviso: o INFOCENARIUM é escrito por um modelo de IA da Anthropic, que é
  do setor de IA e pode ser parte ou concorrente nesta notícia.";
- na tela de método: "O INFOCENARIUM não é recomendação de investimento, nem orientação de saúde ou de segurança."

Edição `falha`: o site mostra "sem edição hoje" com o `resumo`, e os níveis repetidos da edição anterior.
Veículo citado numa edição antiga que saiu do mapa depois: o site mostra o id.

## 17. Campos dos arquivos de trabalho que a `ROTINA.md` cita

Não são campos da edição. O formato completo está no `CONTRATO-FERRAMENTAS.md`.

| Arquivo | Campos |
|---|---|
| `/tmp/info/contexto.json` | `dia`, `janela_horas`, `edicao_do_dia`, `anterior`, `alerta_anterior` (com `origem`, `edicoes_sem_gatilho`, `desce_hoje_sem_gatilho`), `historias_recentes`, `vigiar_vencendo`, `candidatos`, `vetores_recentes` |
| `/tmp/info/indicadores.json` | `indicadores`, `gatilhos`, `falhas` |
| `/tmp/info/mapa.txt`, `/tmp/info/mesa.txt` | texto: veículo, sigla do partido, `fatos`, `tipo`, `serve a`, site; cada um traz a sua legenda |
| `/tmp/info/modelo.txt` | a forma do rascunho, comentada: todo campo de origem `agente` e `misto`, com tamanho, contagem e valores permitidos |
| `/tmp/info/conferencia.json` | `url`, `estado` (`ok`, `bloqueada`, `erro`), `publicado_em` |
| `/tmp/info/urls.txt` | uma URL por linha; linha vazia e linha que começa com `#` (depois dos espaços do começo) ficam de fora: URL com `#…` no meio continua valendo |
| `/tmp/info/notas.md` | texto livre: anotações do agente |
