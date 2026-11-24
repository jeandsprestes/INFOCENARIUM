# INFOCENARIUM · ESPEC-SITE · especificação final do site

Escrita e conferida em 23/11/2026. O desenho juntou três propostas (A, a sala de situação, foi a base; B e C
deram enxertos), como mostra a tabela abaixo. Sobre dados, vale o `ESQUEMA.md` (contrato da edição).
Onde este texto não fechava a questão, o site seguiu uma leitura, e o texto daqui diz o que o site faz: a
seção 11 junta essas leituras. O que não está aqui não entra no site.

| Veio de | O quê |
|---|---|
| A (base) | Alerta e domínios na primeira tela. Ordem por utilidade prática. Coluna lateral com placar, sinais e movimentos. "Uma vista, um trabalho de cor". Partido é sigla |
| B | Seções numeradas com rótulo monoespaçado. Coluna de leitura no dossiê. Navegação na base no celular. Avisos sem matiz. Aviso de "edição nova" sem trocar o texto sob o leitor |
| C | Comparação com a edição anterior. Histórico tirado só do índice. Toda figura com tabela gêmea. Alerta em 5 matizes validados, com roxo acima do vermelho. Sem atalho de uma tecla |
| Novo | ROTINA em verde discreto, com o cinza reservado a "sem dado". DNA sem cor no Painel. Ganha e perde na mesma tinta |

Siglas: IA é inteligência artificial. DNA é o conjunto das 7 posições de um player na régua. CSS, JSON e SVG são os formatos de estilo, de dados e de desenho do site. WCAG é a norma de acessibilidade da web.

## 1. Conceito

O INFOCENARIUM abre como uma sala de situação: a primeira tela diz o nível de alerta, por quê, e onde ele pega na vida de quem está no Brasil.
O resto desce na ordem das quatro perguntas do produto, e cada notícia é lida como um ataque: quem atirou, em quem, e quem ganhou ou perdeu na prática.
A tela é texto claro e fio fino sobre fundo escuro; a cor só aparece para dizer nível de alerta (no Painel) ou posição no DNA (na Régua), sempre com ícone, letra ou rótulo.

## 2. Arquitetura da informação

Cinco vistas numa página só: Painel, edição antiga, Arquivo, Régua e Método. Todos os caminhos são relativos.

| Vista | Arquivos que carrega |
|---|---|
| Todas | `edicoes/indice.json` e `dados/regua.json` |
| Painel e edição antiga | o arquivo da edição (`arquivo`, do índice), `dados/players.json`, `dados/veiculos.json`, `dados/vetores.json`, `dados/indicadores.json` (as casas decimais de cada valor) |
| Arquivo | `dados/indicadores.json` (nome e unidade de cada indicador) |
| Régua | `dados/players.json`, `dados/veiculos.json`, `dados/vetores.json` |
| Método | `dados/indicadores.json`, `dados/players.json` (os nomes da lista de conflito) |

Regras de leitura, para todos os arquivos:

- Todo arquivo é lido com `fetch` e `cache: "no-cache"`. O índice, os players e os vetores mudam todo dia, e uma edição `falha` pode ser trocada depois por uma edição de verdade.
- Arquivo lido fica na memória enquanto a página está aberta. Só o índice é lido de novo (seção 5.2, "Edição nova"). Ao carregar a edição nova, players e vetores também são lidos de novo.
- Chave que o site não conhece é ignorada. Arquivo com `versao` diferente de 1 leva o aviso de formato novo.
- O caminho de `arquivo` e de `texto` só é usado, para ler a edição e para o link, se tem a forma `edicoes/AAAA-MM-DD.json` ou `edicoes/AAAA-MM-DD.md`. Fora disso, o site monta o caminho a partir de `data`.

**Edição anterior** é a mais recente antes de `data` que não é `falha` nem `exemplo` (definição do ESQUEMA). **Histórico** são as entradas do índice nos 30 dias corridos que terminam na data da edição mostrada (no Arquivo, na data da entrada mais nova que não é de exemplo), sem as de `exemplo: true`.

### 2.1 Painel (`#/`): a edição mais recente

Mostra a edição mais recente que não é de exemplo. Se só houver a de exemplo, mostra ela.

| Nº | Seção | O que mostra e de onde vem |
|---|---|---|
| 00 | Carimbo e avisos | Dia da edição (`data`). Hora de geração em Brasília e idade (`gerada_em`); quando o dia de Brasília do `gerada_em` não é o dia da edição (uma republicação), a hora leva o dia na frente, "GERADA 24/11 11h38", no carimbo e na linha da edição no Arquivo. Placa de estado (`estado`, `exemplo`, idade). Botões para as edições vizinhas no índice. Links "texto" (`texto`, do índice), "JSON" (`arquivo`) e "feed" (`feed.xml`). Avisos, nesta ordem: exemplo (`exemplo`), sem edição (`estado: falha`), atrasada, reduzida (`estado: reduzida`), corrigida (`corrigida_em`, do índice, com link para cada edição que corrige), errata (`errata[]`: `edicao`, `item`, `erro`, `correcao`, `url`; sem `item`, a correção vale para a edição toda; com `anula_vetor`, a linha diz qual vetor foi anulado e leva a ele na Régua), formato novo (`versao` diferente de 1) |
| 01 | Hoje | O objeto `alerta`. Numeral do nível (`alerta.nivel`), ícone, `rotulo` e `significado` (de `regua.niveis_alerta`). Tendência (`alerta.tendencia`). Medidor de 5 segmentos. "Antes": `nivel` e `data` da edição anterior, pelo índice. "Desde": os domínios cujo nível mudou, comparando o `nivel` de cada domínio de hoje com o `niveis` da edição anterior no índice ("Desde 18/11: energia 1 → 3"). Frase do dia (`resumo`). Motivo (`alerta.motivo`). Fita "Alerta, 30 dias" (`nivel` e `estado` de cada entrada do histórico) |
| 02 | Domínios | 5 linhas (`alerta.dominios[]`), na ordem da régua. Fechada: `nome` (de `regua.dominios`), medidor, selo do `nivel`, `tendencia`, "era N" (pelo `niveis` da edição anterior, só se mudou), "sem dado de preço de: …" (os nomes dos indicadores de `sem_preco`, só se a lista não é vazia) e `leitura`. Aberta: `descricao` e `canal` (régua); "neste nível desde" (`desde`); cada gatilho (`gatilhos[]`) com o código `criterio` (leva a `#/metodo/niveis`), o `texto`, o `ref` (link para o item ou para a ficha do indicador), a etiqueta EXCEÇÃO se `excecao` e a etiqueta ALÍVIO se `alivio`; o próximo sinal (`vigiar`). Lista de gatilhos vazia: "Nenhum gatilho hoje" no nível 1; placa "MANTIDO DESDE" (com o `desde`) no nível 2 ou mais |
| 03 | Indicadores | Uma ficha por item de `indicadores[]`, na ordem do arquivo: `nome`, `valor`, `unidade`, `variacao_pct` ("anterior"), `variacao_7d_pct` ("7 dias"), etiqueta do domínio (`dominio`), link da fonte (objeto `fonte`: `fonte.nome`, `fonte.url`). "Sem dado" se `valor` é `null`; nesse caso a fonte vira "Fonte prevista: {nome}", sem link. Carimbo "DE DD/MM" (`data`) se `defasado`. Etiqueta GATILHO se o `id` é `ref` de algum gatilho. As casas decimais do valor vêm de `casas`, no catálogo. O campo `confirmado` não aparece: o `texto` do gatilho já diz |
| 04 | Principais | 1 a 3 cartões (`principais[]`). Fechado: número (do `id`), `categoria`, `confianca`, etiquetas de `dominios`, marca de `conflito_de_interesse`, link de `continuacao_de`, `titulo`, `fato`, linha "Atirou" (de `ataques[]`) e linha "Placar" (de `placar[]`; se ela é vazia, "sem ganhador"). Aberto: o dossiê da seção 2.2. Com o mapa de veículos em rascunho (`revisado_em` nulo), a nota de rascunho vem logo abaixo do título da seção |
| 05 | Placar do dia | Os 7 partidos. `saldo` em barra e número. `narrativa` em número, à parte, só quando não é zero: ganhar argumento não é ganhar na prática. `frase`. Partido fora de `placar_do_dia[]` entra com saldo 0, sem frase, e com "sem movimento hoje". Ordem: maior saldo primeiro; empate segue a régua. Ao lado, o acumulado do histórico (soma de `saldos`, do índice, que não leva narrativa) |
| 06 | O que vigiar | Duas partes. **Sinais**, só de leitura: o `vigiar` de cada domínio (com o nome do domínio) e o `vigiar[]` de cada principal (com o número). Cada linha leva à origem. **Respostas** (`respostas[]`): para cada pergunta antiga que venceu, a `pergunta`, a `resposta` em etiqueta, o `texto`, o link `url` ("fonte", quando existe) e o link para a principal que perguntou (`edicao` e `item`, em `#/edicao/DATA/pN`) |
| 07 | Movimentos | Vetores de todos os itens (`vetores[]` das principais e do radar): nome do `player`, sigla do partido dele, seta, sigla de `para`, `forca`, `tema`, `porque`, link `url` ("prova"), item de origem, marca de conflito de interesse (quando o item de origem tem `conflito_de_interesse`) e reincidência (entradas de `dados/vetores.json` com o mesmo `player` e `para` nos 30 dias até a edição, sem contar vetor anulado). Vetor anulado (há no registro uma entrada cujo `anula` é o `id` dele): aparece riscado, com a etiqueta ANULADO, a data e o `porque` da anulação. Player novo (`novos_players[]`): `nome`, `id`, `tipo`, `partido`, `time`, `time_discutivel`, `dna` (7 células sem cor), `dna_fontes` (um link por posição conhecida), `duvidas`, `nota`, `justificativa`, `url` |
| 08 | Radar | 3 a 12 linhas (`radar[]`), com filtros. Fechada: `categoria`, `titulo`, veículo e lado, alvo, placar em siglas, `dominios`, `confianca`, marca de `conflito_de_interesse`. Aberta: `fato`; o ataque (`ataque`: `veiculo`, `lado`, `alvo`, `alvo_nome`, `enquadramento`, `omite`, `url`); o `eixo`; `placar[]`, ou o texto de `sem_placar` quando ela é vazia; `vetores[]`; `fontes[]`; o link de `continuacao_de`. Usa as mesmas linhas e etiquetas do dossiê. O `id` vira a âncora `#/edicao/DATA/r4`. Com o mapa em rascunho, a mesma nota da seção 04 |
| 09 | Bastidores | Tudo de `bastidores`: `modo`, `veiculos_consultados`, `feeds_ok`, `feeds_falhos`, `paginas_lidas`, `buscas`, `minutos`, `injecoes_ignoradas`, `limites`, `candidatos[]` (`nome`, `id`, `motivo`), `veiculos_sugeridos[]` (texto simples, nunca link) |
| — | Rodapé | Aviso curto de autoria por IA, com link para o Método. Links de texto, JSON e feed |

Ordem no celular: a da tabela. No computador, 05, 06 e 07 formam a coluna lateral, ao lado de 04 e 08.
A versão `.md` da edição põe o radar antes do placar. No site o placar vem antes: é a pergunta central. O `.md` não precisa mudar.

### 2.2 Dossiê de uma principal (aberto)

| Parte | Mostra |
|---|---|
| O que aconteceu | `fato`. Depois, se houver, a lista "Não confirmado" (`nao_confirmado[]`) |
| Quem atirou | Cada item de `ataques[]`: nome do veículo (pelo `veiculo`, em `dados/veiculos.json`), sigla do `lado`, seta e alvo (`alvo`: nome do player ou do partido; `alvo_nome` quando é `outro`; "sem alvo", sem seta, quando é `nenhum`), `enquadramento`, "Deixou de fora" (`omite`, seguido de "segundo a leitura do INFOCENARIUM em DD/MM", com a data da edição) e o link `url` da matéria. Etiqueta LADO INCERTO se o veículo tem `lado_confianca: baixa`. Etiqueta FOGO AMIGO se o alvo é o partido do `lado` ou um player dele, e só quando o veículo tem `lado_confianca` `alta` ou `media`. Veículo que saiu do mapa: mostra o id, sem nenhuma das duas etiquetas |
| O que está realmente acontecendo | `realmente`, em coluna de leitura |
| Na prática | `na_pratica[]`, em lista |
| O ato na régua | O `eixo`, quando existe: nome e sigla do tema (`eixo.tema`), o texto do polo para onde o ato empurra (o `sentido` escolhe entre os campos `azul` e `vermelho` do tema, em `regua.temas`) e o ato (`eixo.porque`). As palavras "azul" e "vermelho" não aparecem, e não há cor |
| Quem ganha e quem perde | Cada linha de `placar[]`: sigla e nome do `partido`, `efeito`, `forca` (1 a 3, com a palavra), `evidencia`, `porque`. Lista vazia: o texto de `sem_placar` |
| Movimentos | `vetores[]` do item, como na seção 07 |
| Para quem se prepara | "No Brasil": `no_brasil` (só existe quando o item tem domínio). Etiquetas de `dominios[]` (levam à linha do domínio). As perguntas de `vigiar[]`; a primeira é a que derruba a leitura do dossiê e leva a etiqueta PERGUNTA-CHAVE |
| Fontes | Cada item de `fontes[]`: nome do veículo e sigla do lado (o `lado` gravado no ataque do mesmo veículo no mesmo item; sem ataque dele, o do mapa de hoje, como no `.md`), ou `nome` com a etiqueta FORA DO MAPA quando `veiculo` é `outro`; `titulo` como publicado; `publicado_em`; etiqueta FONTE PRIMÁRIA se `primaria`; link `url` |
| Marcas | `confianca`. Aviso se `conflito_de_interesse`. "Continuação de DD/MM" (`continuacao_de`, na forma `DATA/pN` ou `DATA/rN`; leva a `#/edicao/DATA/pN` ou a `#/edicao/DATA/rN`). O `id` vira a âncora `#/edicao/DATA/p1` |

### 2.3 Edição antiga (`#/edicao/AAAA-MM-DD`)

Mesmo desenho do Painel, com quatro diferenças. A placa de estado diz ARQUIVO e há link "Ir para a mais recente". Não se calcula atraso. A fita e os acumulados terminam na data da edição. Se `corrigida_em` não é vazia, o aviso CORRIGIDA aparece no topo.

Quando a data do endereço é a da edição mais recente, a vista é o Painel, sem tirar nem pôr: placa EM DIA ou ATRASADA, e "Painel" aceso na navegação. É o que acontece quando o leitor abre um item no Painel e recarrega a página.

### 2.4 Arquivo (`#/arquivo`)

| Nº | Seção | Mostra |
|---|---|---|
| 01 | Histórico | Cinco figuras, cada uma com "Ver tabela". Alerta geral: fita de `nivel`. Domínios: 5 fitas pequenas, uma por domínio (`niveis`). Partidos: saldo acumulado de cada um (soma de `saldos`), em barra a partir do zero. Atos por tema: para cada tema que aparece em `eixos`, quantos itens empurraram para cada polo (a soma de `azul` e a soma de `vermelho`), em duas barras da mesma tinta; cada barra leva o texto do polo (de `regua.temas`), e não as palavras "azul" e "vermelho". Indicadores: uma mini-linha por indicador (`indicadores` do índice), com o primeiro e o último valor; nome e unidade vêm de `dados/indicadores.json` |
| 02 | Edições | Lista de `edicoes[]`, do índice, por mês, mais nova primeiro: `data`, `estado`, selo de `nivel`, `tendencia`, os 5 níveis de `niveis` (sigla e número), `resumo`, hora (`gerada_em`), etiqueta EXEMPLO (`exemplo`), "corrigida em" (`corrigida_em`), links para `texto` e `arquivo`. Os 2 meses mais novos vêm abertos; cada mês mais antigo é uma dobra fechada, com a contagem. Filtro: nível mínimo. No fim, "Índice atualizado em" (`atualizado_em`) |

### 2.5 Régua (`#/regua`)

Cabeçalho comum: `descricao`, `aviso` e data de criação (`criada_em`) da régua; legenda das letras (`valores`: a letra e o `significado`), da virada (`virada`), dos polos (`polos`) e dos temas (`temas`: `sigla`, `nome`, `azul`, `vermelho`). O campo `cor` de `valores` não é usado: a cor vem do CSS.

| Aba | Mostra |
|---|---|
| Partidos | 7 fichas (`partidos`): `sigla`, `nome`, `voto_tipico` (7 células, separadas por espaço no arquivo; texto vazio quer dizer "sem voto típico"), `diante_da_ordem`, `descricao`, os players do partido e o saldo acumulado. Abaixo, os 2 times (`times`: `nome`, `descricao`) com seus players, e a regra de `players.json` (`regra`, `atualizado_em`) |
| Players | Matriz: uma linha por player (`players`), agrupada por partido. Colunas: `nome`, `tipo` (nome em `tipos`), `time` (com a marca "discutível" se `time_discutivel`), as 7 células de `dna` e o número de vetores (sem contar os anulados). A linha abre: `nota`, `duvidas` (nomes dos temas), `origem`, `incluido_em`, `justificativa`, `url` e `dna_fontes` (um link por tema, com o nome do tema; os três últimos só existem em player que entrou pela rotina) e os vetores do player. Filtros: partido, tipo, time, busca por nome |
| Veículos | Lista de `veiculos`, agrupada por `lado`. Fechada: `nome`, `pais`, `tipo`, sigla do `lado`, `lado_confianca`, `fatos`. Aberta: `idiomas`, `sites` (os endereços do veículo, em texto), `controle` com link `controle_fonte`, `serve_a`, `alvos`, `lado_porque`, `fatos_nota`, `uso` e `feeds[]` (`secao`, `formato`, `conferido`, `nota`, `url`). Filtros: lado, fatos, tipo, busca. No topo: o aviso de mapa em rascunho enquanto `revisado_em` é `null`; depois, a linha "Mapa revisado em" com essa data |
| Vetores | `regra` do registro. Tabela de `vetores[]`, mais novo primeiro, 50 linhas por vez: `data`, `player`, `de`, `para`, `forca`, `tema`, `porque`, `url`, a marca de `conflito_de_interesse` (quando a entrada traz o campo) e link para o item (`item`, em `#/edicao/DATA/ITEM`). O `id` é a âncora da linha (`#/regua/vetores/ID`). Entrada de anulação (a que tem `anula`) não vira linha: ela risca a linha do vetor que desfaz e põe nela a etiqueta ANULADO, a `data`, o `porque` e o link `url` da anulação |

### 2.6 Método (`#/metodo`)

| Nº | Seção | Mostra |
|---|---|---|
| 01 | Conflito de interesse | Caixa no topo, com o texto da seção 8.7. Abaixo, a lista que liga a marca, lida de `regua.conflito`: a `regra`, os `players` (pelo nome, com link para a ficha) e os `termos` |
| 02 | As quatro perguntas | Texto fixo |
| 03 | A régua | Texto fixo curto e link para a Régua |
| 04 | Níveis de alerta | Os 5 níveis (`niveis_alerta`): ícone, `rotulo`, `significado`, `prova_minima`. Depois, por domínio (`dominios`: `nome`, `descricao`, `canal`), a tabela de critérios (`criterios`): `codigo`, os eventos (`eventos[]`) e os gatilhos de preço (`precos[]`: `texto`, com `indicador`, `janela` e `alta_minima_pct`) |
| 05 | De onde vem cada número | Catálogo `dados/indicadores.json`: `nome`, `unidade`, `dominio`, `obrigatorio` ("alimenta gatilho" ou "só contexto"), `frequencia`, `faixa`, `casas` e as `fontes[]` (`nome`, `url`, `leitor`, `nota` e, quando existe e não é 1, o `fator` de conversão). No fim, `regra` e `atualizado_em` |
| 06 | Como a edição é feita | Texto fixo: rotina, estados, confiança. Depois, cinco quadros lidos da régua. Campos (`campos`: `nome`, `descricao` e as siglas de `partidos`). Força (`forcas`: `forca`, `nome`, `o_que_conta`). Evidência (`evidencias`: o rótulo do `id`, `o_que_conta`). Avanço dos times (`times_avanco`: uma linha para `manutencao`, uma para `mudanca`, com o nome do time, e a nota de `nao_move`). Fonte primária (`sites_oficiais`: a `regra` e as listas `brasil` e `outros`) |
| 07 | Limites e correções | O aviso "O INFOCENARIUM não é recomendação de investimento, nem orientação de saúde ou de segurança.", em caixa. Depois, texto fixo |

### 2.7 Conferência com a seção 16 do ESQUEMA

| Linha do ESQUEMA | Lugar |
|---|---|
| Carimbo e avisos | Painel 00 |
| Alerta geral | Painel 01 |
| Domínios | Painel 02 |
| Indicadores | Painel 03 |
| Principais | Painel 04 e dossiê 2.2 |
| Radar | Painel 08 |
| Placar do dia | Painel 05 |
| Movimentos | Painel 07 e dentro de cada item |
| Respostas | Painel 06, segunda parte |
| Bastidores | Painel 09 |
| Arquivo e histórico | Arquivo 01 e 02; fita do Painel 01; acumulado do Painel 05 |
| Régua | As 4 abas da Régua; a nota de mapa em rascunho também no Painel 04 e 08 |
| Método | Método 01, 04, 05 e 06 |
| Os dois avisos fixos | Conflito no item: seção 8.3. "Não é recomendação": Método 07 |
| Edição `falha` | Seção 5.2 |
| Veículo `outro` e veículo que saiu do mapa | Dossiê 2.2 |

Campos do contrato que o site lê e não mostra, de propósito: `confirmado` (o `texto` do gatilho já diz), `cor` (a cor vem do CSS) e `versao` (só liga o aviso de formato novo).

Conferido por script, nos dois sentidos. Ida: os 250 nomes de campo, de valor e de arquivo citados aqui existem no contrato. Volta: os 177 campos do ESQUEMA final, de `regua.json`, de `players.json`, de `vetores.json`, da edição de exemplo e do mapa de veículos têm lugar aqui. Faltam: 0.

## 3. Esboços

Nos três esboços, os sinais ○ △ ◆ ↗ → ▸ e os blocos ▮▯ fazem as vezes dos ícones e dos medidores da seção 4. No site eles são desenho em SVG e em CSS, nunca caractere. Entre colchetes, etiquetas. Os dados imitam a edição de exemplo (`repo/testes/fixtures/edicao-exemplo.json`), sem as marcas de EXEMPLO.

Painel no computador (1100 px ou mais, 12 colunas). Linhas repetidas foram cortadas.

```
INFOCENARIUM  monitor geopolítico e de IA                     PAINEL   ARQUIVO   RÉGUA   MÉTODO
───────────────────────────────────────────────────────────────────────────────────────────────
ED. 19/11/2026 · GERADA 18H14 (BRASÍLIA) · HÁ 18 MIN  [EM DIA]       ‹ 18/11   texto  JSON  feed
[!] ERRATA  Esta edição corrige 2 pontos de edições anteriores.                          Ver ▸
───────────────────────────────────────────────────────────────────────────────────────────────
01 HOJE                               │ 02 DOMÍNIOS
┃  3   ◆ TENSÃO       ↗ subindo       │ Energia      ▮▮▮▯▯  ◆ 3 TENSÃO   ↗ subindo · era 1    ▸
┃ de 5 ▮▮▮▯▯                          │   Petróleo mais caro lá fora encarece o diesel.
┃ antes (18/11): 2 ATENÇÃO            │ Alimentos    ▮▯▯▯▯  ○ 1 ROTINA   → estável            ▸
┃ Desde 18/11: energia 1 → 3 ·        │   sem dado de preço de: Milho
┃ suprimentos 1 → 2 · conflito 1 → 3  │   Trigo e soja sem alta fora do comum.
┃                                     │ Câmbio       ▮▮▯▯▯  △ 2 ATENÇÃO  → estável            ▸
┃ O dia em uma frase (resumo).        │   [MANTIDO DESDE 17/11] Em 17/11 o dólar subiu 1,8%.
┃ Motivo: os gatilhos de hoje.        │ Suprimentos  ▮▮▯▯▯  △ 2 ATENÇÃO  ↗ subindo · era 1    ▸
┃ Tensão: houve fato consumado.       │   Em 19/11 há só o anúncio das seguradoras.
┃                                     │ Conflito     ▮▮▮▯▯  ◆ 3 TENSÃO   ↗ subindo · era 1    ▸
┃ ALERTA, 30 DIAS          Ver tabela │   Guerra longe chega ao Brasil pelos outros domínios.
┃ 5 ·······························   │
┃ 1 ▂▂▂▂▄▄▄▂▂▂ ▂▂▂▄▄▄▄▄▂▂▂▂▂▄▄▄▄▄▆    │
┃   21/10                     19/11   │
──────────────────────────────────────┴────────────────────────────────────────────────────────
03 INDICADORES
Petróleo Brent  │ Petróleo WTI    │ Gás natural     │ Trigo           │ Milho           │ Soja
                │ (EUA)           │ nos EUA         │                 │                 │
78,40           │ 74,10           │ sem dado        │ 216,90          │ 179,30          │ 383,10
US$ por barril  │ US$ por barril  │ US$ por milhão  │ US$ por         │ US$ por         │ …
                │                 │ de BTU          │ tonelada        │ tonelada        │
anterior +1,3%  │ anterior +1,1%  │                 │ anterior +0,3%  │ anterior −0,1%  │
7 dias   +6,1%  │ 7 dias   +5,4%  │                 │ 7 dias   +1,0%  │ 7 dias   —      │
[GATILHO] fonte │ fonte ↗         │ fonte ↗         │ fonte ↗         │ fonte ↗         │
(segunda fileira: mais 6 fichas; "Frete marítimo de grãos e minério" leva o carimbo [DE 12/11])
───────────────────────────────────────────────────────────────┬───────────────────────────────
04 PRINCIPAIS                                                  │ 05 PLACAR DO DIA
[!] Mapa de veículos em rascunho, ainda sem revisão do dono.   │ OG        │▮▮▮▮   +4
1  GEOPOLÍTICA · CONFIANÇA ALTA · ENERGIA · CONFLITO           │   narrativa +1 · 30 dias +9
   País ataca terminal de petróleo no Estreito                 │   Ganhou uma votação e uma lei.
   Fato verificável, sem adjetivo.                             │ IN        │▮▮     +2
   Atirou: NYT [OG] → Rep. de Exemplo · Fox News [SO] → UE     │ SO        │        0
   Placar: ER +2 · CA −2 · SO +1 narrativa  [ Abrir dossiê ▸ ] │   narrativa +2
2  IA · CONFIANÇA MÉDIA · [CONFLITO DE INTERESSE]              │ ER        │        0
   Lei obriga registro de modelos avançados de IA              │ CE       ▮│       −1
   …                                        [ Abrir dossiê ▸ ] │ CA      ▮▮│       −2
3  GEOPOLÍTICA · CONFIANÇA ALTA             [ Abrir dossiê ▸ ] │ BT      ▮▮│       −2
───────────────────────────────────────────────────────────────│ 06 O QUE VIGIAR
08 RADAR (6)  [Todas 6][Geopolítica 3][IA 3] Domínio▾ Partido▾ │ Energia: o Brent passa de 10%
[IA] Fabricante assina contrato de chips de IA               ▸ │ de alta em 7 dias?
     Wired [OG] → Jensen Huang · sem ganhador · SUPRIMENTOS    │ Principal 1: o Reino responde
[IA] Google adia modelo até auditoria externa                ▸ │ com ataque militar até 22/11?
     Wired [OG] → Google · OG +1 narrativa                     │ RESPOSTAS (3)
[GEOPOLÍTICA] Banco central mantém juros em 9% ao ano        ▸ │ [SIM] O Reino renova as sanções
     WSJ [CE] · sem alvo · sem ganhador · CÂMBIO               │ até 19/11? Renovou em 18/11.
[GEOPOLÍTICA] Seguradoras anunciam fim da cobertura          ▸ │ 07 MOVIMENTOS
     Valor [CE] → Reino de Amostra · CE −1 · SUPRIMENTOS       │ UE [CA] → [SO] força 2 · CLIMA
(mais 2 linhas)                                                │ Google [BT] → [OG] força 2 · IA 2
                                                               │ NOVO PLAYER: República de Exemplo
───────────────────────────────────────────────────────────────┴───────────────────────────────
09 BASTIDORES  coleta normal · 19 veículos · 61 feeds lidos, 7 falharam · 11 páginas · 24 min
O que não deu para conferir: texto de limites.     Atores sem ficha (1) ▸   Veículos em falta (1) ▸
───────────────────────────────────────────────────────────────────────────────────────────────
Análises escritas por IA (Claude, da Anthropic, que é player da régua). Ver Método.
```

Painel no celular (até 420 px, uma coluna, navegação presa na base):

```
┌──────────────────────────────────┐
│ INFOCENARIUM                     │
│ ED. 19/11 · 18H14 · HÁ 18 MIN    │
│ [EM DIA]        ‹ 18/11   texto  │
│ [!] ERRATA (2)                 ▸ │
│                                  │
│ 01 HOJE                          │
│ ┃  3   ◆ TENSÃO                  │
│ ┃ de 5 ↗ subindo                 │
│ ┃ ▮▮▮▯▯  antes: 2 ATENÇÃO        │
│ ┃ Desde 18/11: energia 1 → 3 ·   │
│ ┃ suprimentos 1 → 2 · …          │
│ ┃ O dia em uma frase.            │
│ ┃ Motivo: os gatilhos de hoje.   │
│ ┃ ALERTA, 30 DIAS     Ver tabela │
│ ┃ ▂▂▂▄▄▄▂▂ ▂▂▄▄▄▂▂▂▄▄▄▆          │
│                                  │
│ 02 DOMÍNIOS                      │
│ Energia          ◆ 3 TENSÃO    ▸ │
│ ▮▮▮▯▯  ↗ subindo · era 1         │
│ Petróleo mais caro lá fora…      │
│ Alimentos        ○ 1 ROTINA    ▸ │
│ ▮▯▯▯▯  → estável                 │
│ sem dado de preço de: Milho      │
│ (mais 3 linhas)                  │
│                                  │
│ 03 INDICADORES                   │
│ ┌───────────────┬──────────────┐ │
│ │Petróleo Brent │Petróleo WTI  │ │
│ │               │(EUA)         │ │
│ │78,40          │74,10         │ │
│ │US$ por barril │US$ por barril│ │
│ │anterior +1,3% │anterior +1,1%│ │
│ │7 dias   +6,1% │7 dias   +5,4%│ │
│ │[GATILHO] fonte│fonte ↗       │ │
│ └───────────────┴──────────────┘ │
│ (12 fichas, 2 por linha)         │
│                                  │
│ 04 PRINCIPAIS                    │
│ 1 GEOPOLÍTICA · CONFIANÇA ALTA   │
│ País ataca terminal de petróleo  │
│ Fato verificável, sem adjetivo.  │
│ Atirou: NYT [OG] → Rep. Exemplo  │
│ Placar: ER +2 · CA −2 ·          │
│ SO +1 narrativa                  │
│ [        Abrir dossiê ▸        ] │
│ (mais 2 cartões)                 │
│                                  │
│ 05 PLACAR DO DIA                 │
│ OG     │▮▮▮▮   +4                │
│ narrativa +1 · 30 dias +9        │
│ Ganhou uma votação e uma lei.    │
│ (mais 6 linhas)                  │
│ 06 O QUE VIGIAR (com RESPOSTAS)  │
│ 07 MOVIMENTOS                    │
│ 08 RADAR · 09 BASTIDORES         │
├──────────────────────────────────┤
│ PAINEL  ARQUIVO  RÉGUA  MÉTODO   │
└──────────────────────────────────┘
```

Dossiê de uma principal, aberto (computador):

```
1  GEOPOLÍTICA · CONFIANÇA ALTA · ENERGIA · CONFLITO                   [ Fechar dossiê ▾ ]
   País ataca terminal de petróleo no Estreito de Exemplo
   ──────────────────────────────────────────────────────────────────────────────────────
   O QUE ACONTECEU
   Em 19/11, drones atingiram o terminal. O embarque parou.
   NÃO CONFIRMADO
   · Segundo o governo do Reino de Amostra, os drones partiram de um terceiro país.

   QUEM ATIROU (3)
   The New York Times [OG] → República de Exemplo
     Chama o ataque de "agressão" e destaca o risco para civis.
     Deixou de fora: o terminal já operava com metade da capacidade.
     Segundo a leitura do INFOCENARIUM em 19/11.                         ler no veículo ↗
   Fox News [SO] → União Europeia
     Culpa a política de energia da Europa.                              ler no veículo ↗
   Xinhua [ER] → Reino de Amostra
     Trata o ataque como "resposta" e destaca as sanções anteriores.     ler no veículo ↗
   (outros casos: "WSJ [CE] · sem alvo"; alvo do próprio partido leva [FOGO AMIGO])

   O QUE ESTÁ REALMENTE ACONTECENDO
   Texto corrido, de 800 a 1.500 caracteres, em coluna de no máximo 68 caracteres
   por linha. O fato, a batalha de versões, o chão e a leitura pela régua.

   NA PRÁTICA
   · Terminal parado: 400 mil barris por dia fora do mercado.
   · Brent subiu 6,1% em 7 dias.

   O ATO NA RÉGUA
   Mudanças climáticas [CLIMA] · empurra para: fósseis livres, minimizar o problema
        A Comissão Europeia suspendeu por 90 dias uma meta de corte de emissões.

   QUEM GANHA E QUEM PERDE
   [ER] Eixo Revisionista   + ganha   força 2 ●●○ ato reversível      [PREÇO]
        Rússia e Irã: barril 6,1% mais caro em 7 dias.
   [CA] Centro Atlântico    − perde   força 2 ●●○ ato reversível      [PREÇO]
        União Europeia: paga mais pelo petróleo.
   [SO] Soberanistas        + ganha   força 1 ●○○ sinal               [SÓ NARRATIVA]
        A Fox News usa o caso. Nada material mudou.

   MOVIMENTOS
   União Europeia [CA] → [SO]   força 2 ●●○   tema CLIMA   2ª vez em 30 dias
        A Comissão suspendeu por decreto uma meta de corte de emissões.          prova ↗

   PARA QUEM SE PREPARA
   No Brasil: tende a encarecer o diesel e a gasolina importados.
   Domínios: [ENERGIA] [CONFLITO]
   Vigiar:   · [PERGUNTA-CHAVE] O Reino de Amostra responde com ataque militar até 22/11?
             · O terminal volta a embarcar petróleo até 26/11?

   FONTES (6)
   Reuters [CE] · 19/11 · Sample Kingdom oil terminal halts loading after drone strike  ↗
   Comissão de Exemplo [FORA DO MAPA] [FONTE PRIMÁRIA] · 19/11 · Decreto 1/2026         ↗
```

## 4. Sistema visual

Regra de ouro: **uma vista, um trabalho de cor**. No Painel, no Arquivo e no Método, a única cor de dado é a do nível de alerta. Na Régua, a única cor de dado é a da posição do DNA. As duas escalas nunca dividem a tela: o amarelo e o vermelho de uma são quase iguais aos da outra (medido na seção 10). Por isso a ficha de player novo, no Painel, usa células sem cor.

Só existe tema escuro na tela. O claro existe só na impressão.

```css
:root {
  color-scheme: dark;

  /* superfícies */
  --plano: #0b0e11;            /* fundo da página */
  --painel: #12161b;           /* cartões, fichas, barra de navegação */
  --relevo: #1a2027;           /* cabeçalho de tabela, linha sob o ponteiro, avisos */
  --fio: #222a32;              /* grade e divisória fina (decorativo) */
  --fio-forte: #313a44;        /* borda de cartão, eixo, linha de base (decorativo) */
  --borda-controle: #6f7b88;   /* borda de botão, campo, etiqueta de partido, células W e K */

  /* texto */
  --texto: #e6ebf0;
  --texto-2: #b3bcc6;
  --texto-3: #8d98a4;          /* rótulos, eixos, "sem dado" */
  --tinta-escura: #0b0e11;     /* letra sobre preenchimento claro */
  --tinta-clara: #ffffff;      /* letra sobre preenchimento escuro */

  /* destaque: só interação (link, foco, vista ativa, botão principal) */
  --destaque: #6cc5d6;

  /* dado neutro: barras do placar, fitas, mini-linhas, pontos de força */
  --tinta-dado: #8d98a4;
  --tinta-dado-forte: #e6ebf0; /* a coluna da edição em tela; o ponto final da mini-linha */

  /* níveis de alerta: cor só em ícone, medidor e filete; trilho = segmento apagado */
  --alerta-1: #04896e;  --alerta-1-trilho: #0e3632;   /* ROTINA */
  --alerta-2: #a39700;  --alerta-2-trilho: #3b3a13;   /* ATENÇÃO */
  --alerta-3: #9f5910;  --alerta-3-trilho: #392918;   /* TENSÃO */
  --alerta-4: #e13d62;  --alerta-4-trilho: #4c212f;   /* CRISE */
  --alerta-5: #b15bdd;  --alerta-5-trilho: #3f2951;   /* EMERGÊNCIA */

  /* posições do DNA: só na Régua */
  --dna-b: #256abf;  --dna-b-letra: #ffffff;   /* B, polo azul */
  --dna-y: #c98500;  --dna-y-letra: #0b0e11;   /* Y, misto */
  --dna-r: #d1273f;  --dna-r-letra: #ffffff;   /* R, polo vermelho */
  --dna-w: transparent;                        /* W, sem posição: vazia, com borda */
  --dna-k: #000000;                            /* K, saiu do cargo: preta, com borda */
  --dna-wk-borda: #6f7b88;
  --dna-wk-letra: #b3bcc6;

  /* partidos: sigla, sem matiz */
  --partido-fundo: transparent;
  --partido-borda: #6f7b88;
  --partido-letra: #e6ebf0;

  /* placar: ganha e perde usam a mesma tinta, de propósito */
  --placar-ganha: #8d98a4;
  --placar-perde: #8d98a4;
  --placar-eixo: #313a44;

  /* tipografia: só fontes do sistema */
  --fonte-texto: system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans", "Liberation Sans", Arial, sans-serif;
  --fonte-mono: ui-monospace, "SF Mono", "Cascadia Mono", "Roboto Mono", "DejaVu Sans Mono", "Liberation Mono", Menlo, Consolas, monospace;
  --t-rotulo: 0.75rem;     /* 12 px: rótulos e siglas (mono, caixa alta, 600, espaço 0.08em; a etiqueta comum fica em 400 e 0.04em) */
  --t-meta: 0.8125rem;     /* 13 px: variações, datas, rodapés de ficha */
  --t-pequeno: 0.875rem;   /* 14 px: texto de apoio */
  --t-corpo: 1rem;         /* 16 px: corpo; entrelinha 1.55 */
  --t-leitura: 1.0625rem;  /* 17 px: texto "realmente"; entrelinha 1.6; medida máxima 68ch */
  --t-item: 1.125rem;      /* 18 px: título de linha do radar e de cartão no celular */
  --t-titulo: 1.375rem;    /* 22 px: frase do dia, título de principal, rótulo do nível; entrelinha 1.3 */
  --t-valor: 1.25rem;      /* 20 px: valor de indicador; peso 600 */
  --t-heroi: 4rem;         /* 64 px: numeral do alerta; peso 600; entrelinha 1; um só por vista */

  /* espaços */
  --e1: 4px; --e2: 8px; --e3: 12px; --e4: 16px; --e5: 24px; --e6: 32px; --e7: 48px; --e8: 72px;

  /* bordas e raios */
  --borda: 1px solid var(--fio-forte);
  --raio-1: 2px;           /* etiquetas, células, segmentos */
  --raio-2: 4px;           /* cartões, botões, avisos */
  --foco: 2px solid var(--destaque);   /* com outline-offset de 2px */
}

@media print {
  :root {
    --plano: #ffffff; --painel: #ffffff; --relevo: #ffffff;
    --fio: #bbbbbb; --fio-forte: #767676; --borda-controle: #767676;
    --texto: #111111; --texto-2: #444444; --texto-3: #444444;
    --destaque: #111111; --tinta-dado: #444444; --tinta-dado-forte: #111111;
    --alerta-1: #111111; --alerta-2: #111111; --alerta-3: #111111; --alerta-4: #111111; --alerta-5: #111111;
    --alerta-1-trilho: #ffffff; --alerta-2-trilho: #ffffff; --alerta-3-trilho: #ffffff;
    --alerta-4-trilho: #ffffff; --alerta-5-trilho: #ffffff;
    --dna-b: #ffffff; --dna-y: #ffffff; --dna-r: #ffffff; --dna-k: #ffffff;
    --dna-b-letra: #111111; --dna-y-letra: #111111; --dna-r-letra: #111111; --dna-wk-letra: #111111;
    --dna-wk-borda: #767676; --partido-borda: #767676; --partido-letra: #111111;
    --placar-ganha: #444444; --placar-perde: #444444; --placar-eixo: #767676;
    --tinta-escura: #ffffff;   /* no papel, a placa invertida fica preta com letra branca */
  }
}
```

**Níveis de alerta.** O rótulo vem de `regua.json`. O ícone muda de forma a cada nível: vazado nos dois primeiros, cheio depois. A cor pinta só o ícone, os segmentos acesos do medidor e o filete de 3 px do bloco de alerta. Numeral e rótulo usam `--texto`.

| Nível | Rótulo | Ícone | Cor | Trilho |
|---|---|---|---|---|
| 1 | ROTINA | círculo vazado | `#04896e` verde | `#0e3632` |
| 2 | ATENÇÃO | triângulo vazado | `#a39700` amarelo | `#3b3a13` |
| 3 | TENSÃO | losango cheio | `#9f5910` laranja queimado | `#392918` |
| 4 | CRISE | octógono cheio | `#e13d62` vermelho | `#4c212f` |
| 5 | EMERGÊNCIA | octógono cheio com anel | `#b15bdd` roxo | `#3f2951` |

Verde, amarela, laranja, vermelha e roxa: a ordem das bandeiras que o leitor brasileiro já conhece. O verde não quer dizer "tudo bem": quer dizer "nenhum gatilho". O cinza fica reservado a "sem dado".

**Tendência.** Sempre seta e palavra: seta para cima e à direita, "subindo"; seta à direita, "estável"; seta para baixo e à direita, "descendo". A seta usa `--texto-2`. Exceção: sem edição anterior (a primeira edição, ou a primeira depois de só haver falhas), o "estável" que a regra R14 grava não foi medido; no 01 HOJE, no 02 DOMÍNIOS e na fala do selo, nem seta nem palavra, e a linha "Primeira edição: sem comparação." explica. A linha do Arquivo segue mostrando a tendência do índice.

**Ícones.** Um `<svg>` de símbolos fica escrito no `index.html` e é usado com `<use>`. Caixa de 16 × 16, cor por `currentColor`. Não use caracteres de seta nem de triângulo: alguns celulares os trocam por emoji.

| Símbolo | Desenho (dentro de `viewBox="0 0 16 16"`) |
|---|---|
| `i-nivel-1` | `<circle cx="8" cy="8" r="5.5" fill="none" stroke="currentColor" stroke-width="2"/>` |
| `i-nivel-2` | `<path d="M8 2.6 14 13H2Z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>` |
| `i-nivel-3` | `<path d="M8 1 15 8 8 15 1 8Z" fill="currentColor"/>` |
| `i-nivel-4` | `<path d="M5.1 1h5.8L15 5.1v5.8L10.9 15H5.1L1 10.9V5.1Z" fill="currentColor"/>` |
| `i-nivel-5` | `<path d="M5.3 1.5h5.4l3.8 3.8v5.4l-3.8 3.8H5.3l-3.8-3.8V5.3Z" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M6.4 4.5h3.2l1.9 1.9v3.2l-1.9 1.9H6.4L4.5 9.6V6.4Z" fill="currentColor"/>` |
| `i-sobe` | `<path d="M4 12 12 4M6 4h6v6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>` |
| `i-estavel` | `<path d="M2 8h12M9 3l5 5-5 5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>` |
| `i-desce` | `<path d="M4 4l8 8M6 12h6V6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>` |
| `i-aviso` | `<path d="M2.5 2.5h11v11h-11Z" fill="none" stroke="currentColor" stroke-width="2"/><path d="M8 5v4M8 11.2v.1" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>` |
| `i-relogio` | `<circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" stroke-width="2"/><path d="M8 4.5V8l2.5 1.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>` |
| `i-externo` | `<path d="M6 3H3v10h10v-3M9 3h4v4M13 3 7 9" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>` |
| `i-dobra` | `<path d="M6 3l5 5-5 5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>` (gira 90 graus quando aberto) |

O ícone de aviso é um quadrado, em cor de texto. Nunca se confunde com o triângulo do nível 2.

**DNA.** Célula com a letra dentro. B, Y e R têm preenchimento. W é vazia, com borda. K é preta, com borda. Virada (duas letras): a célula se parte em duas metades, antes à esquerda e agora à direita, cada uma com sua cor e sua letra, com vão de 2 px. Tema em `duvidas`: um "?" pequeno no canto de cima, à direita, na cor da letra. Variante sem cor (`dna--tinta`, usada no Painel e na impressão): toda célula fica vazia, com borda `--borda-controle` e letra `--texto`.

**Partidos: sigla, sem cor.** Etiqueta monoespaçada com borda, com a sigla de `regua.json`: OG (Ordem Global), CA (Centro Atlântico), BT (Bancada do Talento), SO (Soberanistas), ER (Eixo Revisionista), CE (Centrão), IN (Independentes). Motivos: sete matizes a mais virariam arco-íris e não passariam no validador; e pintar um partido de azul ou de vermelho confundiria partido com polo.

**Ganha e perde.** Sem verde e vermelho: o INFOCENARIUM não torce, e essas cores já têm dono. A diferença é dada por três coisas juntas: lado da barra (direita ganha, esquerda perde), sinal (+ e −, o sinal de menos tipográfico) e palavra ("ganha", "perde"). As duas variáveis têm o mesmo valor de propósito.

**Marcas.** Barra do placar: 8 px de altura, ponta arredondada (4 px) e base reta no eixo. Coluna da fita: 6 px de largura, vão de 2 px. Linha: 2 px. Ponto final: raio de 4 px, com anel de 2 px na cor da superfície. Grade e eixo: fio contínuo de 1 px. Sem sombra, sem degradê, sem tracejado.

**Larguras.** Compacto: até 719 px. Médio: de 720 a 1099 px. Largo: 1100 px ou mais. Conteúdo com no máximo 1240 px. Margem lateral de 16 px no compacto e de 24 px nos outros.

**Grade das outras vistas.** Arquivo: as cinco figuras do Histórico são cartões com título `h3`, em grade de 1 coluna (compacto), 2 (médio) ou 3 (largo); a de indicadores ocupa a linha inteira, com as mini-linhas em grade de 2, 4 ou 6 colunas. A lista de edições ocupa a largura toda. Régua: abas, legenda e o conteúdo da aba, um abaixo do outro, na largura toda. Método: coluna única; o texto corrido tem medida máxima de 68 caracteres, e os quadros e as tabelas usam a largura do conteúdo. No Método 04, cada domínio tem título `h3`, `descricao`, `canal` e uma tabela de 5 linhas, uma por nível: selo do nível com o `codigo` em mono; a lista de `eventos`; a lista de `precos` (o `texto` e, abaixo, em mono de 12 px, o `indicador`, a `janela` pelo rótulo e "{alta_minima_pct}% ou mais"). Célula sem item leva travessão.

**Grade do Painel.** Compacto e médio: uma coluna, na ordem da seção 2.1. Largo: 12 colunas, com vão de 24 px. Hoje ocupa 5 colunas e Domínios, 7. Indicadores ocupam as 12. Principais e Radar ocupam 8, uma embaixo da outra; ao lado delas, em 4 colunas, ficam Placar do dia, O que vigiar e Movimentos. Bastidores ocupam as 12. A coluna lateral não fica presa à tela.

## 5. Componentes e estados

### 5.1 Componentes

| Componente | Medidas | Comportamento |
|---|---|---|
| Barra de topo | 56 px, fundo `--painel`. Marca "INFOCENARIUM" em mono, 18 px, peso 700. Fio de 1 px embaixo | Presa no topo no médio e no largo. No compacto rola com a página |
| Navegação | Médio e largo: links em mono de 12 px, vão de 24 px, na barra de topo. Compacto: barra presa na base, 56 px mais a área segura do aparelho, fundo `--painel`, 4 colunas iguais | Vista ativa: `--texto` e traço de 2 px em `--destaque` (embaixo; no compacto, em cima), com `aria-current="page"`. No compacto, o conteúdo ganha 72 px de respiro no fim |
| Carimbo | Uma linha em mono de 12 px, `--texto-2`. Altura de 40 px | A idade ("há 18 min") se refaz a cada minuto, sem anúncio ao leitor de tela. A conta de atraso (seção 5.2) é refeita junto |
| Placa de estado | Etiqueta de 20 px de altura. Normal: borda `--borda-controle`, letra `--texto`. Grave (ATRASADA, SEM EDIÇÃO, EXEMPLO): invertida, fundo `--texto` e letra `--tinta-escura` | Só texto, com ícone ao lado quando houver (relógio em ATRASADA). Cabe mais de uma, lado a lado: EXEMPLO; ARQUIVO; no Painel, ATRASADA mais SEM EDIÇÃO ou REDUZIDA. EM DIA só sem atraso e sem exemplo |
| Aviso | Largura total. Fundo `--relevo`, borda de 1 px, filete esquerdo de 3 px em `--texto-2`, espaço interno de 12 por 16 px. Ícone de 16 px, rótulo em mono de 12 px, texto de 14 px | Pode trazer um botão. Errata abre e fecha. Nenhum aviso usa cor de alerta. Os avisos do topo se empilham na ordem da seção 2.1, com vão de 8 px |
| Nota de seção | Uma linha logo abaixo do título da seção: ícone `i-aviso` de 14 px, texto de 13 px em `--texto-2`, sem fundo e sem borda | Usada para o mapa em rascunho (Painel 04 e 08) e para "NÍVEIS REPETIDOS". Pode trazer um link |
| Título de seção | Número e nome em mono de 12 px, `--texto-3`, com fio embaixo. 32 px acima (48 px no largo) e 16 px abaixo | É um `h2`. Na edição de exemplo, leva a etiqueta EXEMPLO |
| Bloco de alerta | Cartão: fundo `--painel`, borda de 1 px, raio de 4 px, espaço interno de 24 px (16 px no compacto), filete esquerdo de 3 px na cor do nível. Numeral de 64 px. Ícone de 28 px. Rótulo de 22 px. Medidor de 5 segmentos de 32 × 8 px. No largo ocupa 5 das 12 colunas | Só leitura. O `significado` vem em 13 px, `--texto-3` |
| Selo de nível | Ícone de 16 px na cor do nível, numeral em mono de 14 px e rótulo em mono de 12 px | Sempre os três juntos. Nome para leitor de tela na seção 7 |
| Medidor | 5 segmentos de 20 × 6 px, vão de 2 px, raio de 1 px. Acesos na cor do nível, apagados na cor do trilho | Sempre ao lado de um selo. Escondido do leitor de tela |
| Fita de histórico | Um espaço de 8 px por dia, 30 dias: 240 × 40 px de desenho, mais 16 px para as datas. Altura da coluna: 8 px por nível. 5 fios de grade. Colunas em `--tinta-dado`; a da edição em tela em `--tinta-dado-forte` | Dia sem entrada: espaço vazio. Edição `falha`: traço de 2 px na base. Fita pequena (as 5 de domínio, no Arquivo): 4 px por dia, coluna de 3 px, 120 × 20 px, 4 px por nível, sem dica e sem clique, com o nome do domínio e o nível de hoje ao lado. Ponteiro: a coluna mais próxima clareia e abre a dica (data, nível, rótulo); o clique leva à edição. Teclado: pela tabela de "Ver tabela". Com menos de 2 edições, a fita não aparece; no Arquivo, com uma edição só, a frase da seção 8.4 fica no lugar |
| Linha de domínio | Altura mínima de 56 px. No largo: nome (132 px), medidor, selo, tendência com "era N", botão de 44 px. Na linha de baixo, em 14 px: a placa MANTIDO DESDE, se for o caso, e a `leitura`. Com `sem_preco` não vazia, há uma linha a mais entre as duas, em 13 px, `--texto-3`, com o ícone `i-aviso` de 14 px: "sem dado de preço de: Milho, Soja" (o `nome` do indicador na edição; se não achar, o do catálogo; se não achar, o id) | Abre e fecha. No compacto, a `leitura` fechada mostra 2 linhas. Aberta, as partes vêm nesta ordem, cada uma com rótulo em mono de 12 px: a descrição, COMO CHEGA AO BRASIL, "Neste nível desde", GATILHOS DE HOJE, PRÓXIMO SINAL |
| Linha de gatilho | Código `criterio` em mono de 12 px (link), `texto` em 14 px, etiquetas EXCEÇÃO e ALÍVIO, e o link do `ref` à direita | O link diz para onde vai: "ver principal 1", "ver radar 4" ou "ver indicador: Petróleo Brent". `ref` que não existe na edição: mostra o id, sem link |
| Ficha de indicador | Grade de 2 colunas (compacto), 4 (médio) ou 6 (largo), vão de 12 px. Espaço interno de 12 px, altura mínima de 112 px. Nome em 13 px, valor em 20 px, unidade em 12 px, variações em mono de 13 px | Valor com `toLocaleString("pt-BR")` e o número de casas de `casas`, do catálogo (sem o campo, 2; sem o catálogo, de 2 a 4). O nome pode ocupar 2 linhas. Variação com sinal e 1 casa ("+1,3%", "−0,6%"), em cor de texto. `valor` nulo: "sem dado" em `--texto-3`, sem variações e sem carimbo. `defasado` com valor: etiqueta "DE DD/MM". Variação nula: travessão. A ficha é o alvo da rota do indicador: recebe foco e contorno |
| Cartão de principal | Cartão com espaço interno de 24 px (16 px no compacto). Número em mono de 22 px, `--texto-3`. Título `h3` de 22 px (18 px no compacto). Fato em 16 px, `--texto-2`. Linhas "Atirou" e "Placar" em 14 px. Botão "Abrir dossiê" à direita (largura total no compacto) | Fechado ao carregar. Aberto, mostra o dossiê e o botão vira "Fechar dossiê". No largo ocupa 8 colunas |
| Dossiê | Partes com título `h4` em mono de 12 px, 24 px acima. Texto `realmente` em 17 px, com medida máxima de 68 caracteres | Parte sem conteúdo diz o que falta (seção 8.4). Nunca some |
| Linha de ataque | Veículo em peso 600, etiqueta do lado, seta, alvo. Abaixo, enquadramento em 16 px e "Deixou de fora" em 14 px, `--texto-2`, seguido de "Segundo a leitura do INFOCENARIUM em DD/MM." em 13 px, `--texto-3`. Link "ler no veículo" à direita | Veículo, sigla e alvo são links para a Régua (alvo `outro` é texto simples). Alvo `nenhum`: no lugar da seta e do alvo, "sem alvo" em `--texto-2`, com a dica da seção 8.3 |
| Linha de eixo | Nome do tema em 16 px, sigla em etiqueta, "empurra para:" e o texto do polo, em `--texto`. Abaixo, o `porque` em 14 px, `--texto-2` | Só leitura. Sem cor e sem as palavras "azul" e "vermelho". Tema que não está na régua: mostra o id, sem o texto do polo |
| Linha de placar do item | Sigla, nome, sinal e palavra, força em 3 pontos de 6 px (cheios em `--tinta-dado`; vazios com borda de 1 px na mesma tinta) mais a palavra, etiqueta da evidência. `porque` na linha de baixo | Só leitura |
| Placar do dia | Linha: sigla (40 px), área da barra (72 px para cada lado do eixo), saldo em mono com algarismos alinhados (40 px). Na linha de baixo, em mono de 12 px, `--texto-3`: "narrativa +1" (só quando `narrativa` não é zero) e "30 dias +9". Depois a `frase`, em 14 px | Escala comum às 7 linhas: 72 px valem o maior saldo absoluto do dia, com piso de 3. Saldo 0: sem barra. A narrativa nunca vira barra |
| Linha de vetor | Player, sigla de origem, seta, sigla de destino, força, tema. `porque` na linha de baixo. Link "prova" | Reincidência em etiqueta: "2ª vez em 30 dias" (aparece da 2ª em diante; a conta inclui o próprio vetor). Item com conflito de interesse: etiqueta CONFLITO DE INTERESSE. Vetor anulado: a linha e o `porque` ficam riscados (`text-decoration: line-through`) e em `--texto-3`; a etiqueta ANULADO e a linha "Anulado em DD/MM: motivo", com o link "fonte da correção", não são riscadas |
| Linha de resposta | Etiqueta da resposta (SIM, NÃO ou SEM DADO), a `pergunta` em 16 px, o `texto` em 14 px, `--texto-2`. Na última linha, em 13 px: o link "fonte" e o link "perguntado em DD/MM, principal N" | Só leitura. As três etiquetas têm o mesmo desenho: quem diz se o INFOCENARIUM acertou é o texto |
| Linha de radar | Altura mínima de 56 px. Categoria em etiqueta, título `h3` de 18 px, linha de apoio em 14 px, botão de 44 px | Abre e fecha |
| Etiqueta | 20 px de altura, mono de 12 px em caixa alta, borda de 1 px `--fio-forte`, raio de 2 px, `--texto-2` | Sigla de partido: borda `--partido-borda`, letra `--partido-letra`, peso 600, largura mínima de 30 px; é link para a ficha do partido e traz o nome em `<abbr>` |
| Célula de DNA | 36 × 28 px, raio de 2 px, vão de 2 px. Letra em mono de 13 px, peso 700. Virada: duas metades de 17 px | Só leitura. A tira de 7 células mede 264 px. Dentro do cartão, a 320 px, as células cedem por igual |
| Abas da Régua | Fileira de 4 links em mono de 12 px, vão de 24 px, logo abaixo do `h1`. Altura de 44 px | Aba ativa: `--texto` e traço de 2 px em `--destaque`, com `aria-current="page"`. No compacto, a fileira rola para o lado dentro dela mesma, sem rolar a página |
| Legenda da Régua | Sempre à vista, abaixo das abas: a `descricao`; o `aviso` (componente Aviso); uma linha com as 5 células de exemplo e o `significado` de cada uma, mais uma célula de virada com o texto de `virada` | A dobra "COMO LER", fechada, traz os 2 `polos` e a tabela dos 7 `temas` (sigla, nome, o que é o polo azul, o que é o polo vermelho) e a data `criada_em` |
| Ficha de partido | Cartão. Grade de 1 coluna (compacto), 2 (médio) ou 3 (largo), vão de 24 px. Sigla em etiqueta, nome `h3` de 18 px, tira de 7 células do voto típico com as siglas dos temas em cima, `diante_da_ordem` em 14 px, `descricao` em 14 px, `--texto-2`. Depois "players (N)", com os nomes em lista corrida, e "saldo em 30 dias" em mono | Só leitura. Cada nome leva à linha do player. É o alvo da rota do partido |
| Linha de veículo | Altura mínima de 56 px. Nome em 16 px, peso 600; país e tipo em 13 px, `--texto-2`; sigla do lado; "confiança no lado: média" e "confiabilidade nos fatos: alta", em 13 px; botão de 44 px | Abre e fecha. Com `lado_confianca: baixa`, leva a etiqueta LADO INCERTO. Grupo por lado, com título `h3` (sigla, nome do partido e contagem) |
| Ficha de player novo | Cartão dentro da seção 07. Etiqueta NOVO PLAYER, nome `h3` de 18 px, tipo, sigla do partido, time com "time discutível". Tira de 7 células na variante sem cor, com as siglas dos temas em cima. "Fontes das posições:", com um link por tema. `nota` em 14 px. "Por que entrou:" e a `justificativa`, com o link da fonte. Link "Ver a ficha na Régua" | Só leitura. O `id` aparece em mono de 12 px, `--texto-3` |
| Matriz de players | Tabela de verdade, com cabeçalho preso e linha de grupo por partido. Siglas dos temas em mono de 12 px. Linha de 44 px | No compacto vira uma ficha por player, com a tira de 7 células e as siglas em cima |
| Mini-linha | 120 × 28 px, um ponto por edição do histórico, na posição do dia. Linha de 2 px em `--tinta-dado`. Ponto final em `--tinta-dado-forte` | Escala vertical do menor ao maior valor do período, com 4 px de folga em cima e embaixo; valores todos iguais dão linha reta a meia altura. Dia sem valor quebra a linha. Tem tabela gêmea. Com menos de 2 valores, mostra só o número |
| Barras de atos por tema | Uma linha por tema: nome do tema (132 px); à esquerda do eixo, a contagem e a barra do polo `azul`; à direita, a barra e a contagem do polo `vermelho` (72 px para cada lado). Barras de 8 px em `--tinta-dado`. Embaixo de cada lado, o texto do polo, em 12 px, `--texto-3` | Só no Arquivo. Escala comum: 72 px valem a maior contagem, com piso de 3. A ordem dos temas é a da régua. Tem tabela gêmea (tema, polo, atos) |
| Tabela | Cabeçalho em `--relevo`, mono de 12 px. Linha mínima de 44 px. Fio `--fio` entre linhas. Números à direita, com algarismos alinhados | No compacto, cada linha vira um bloco com rótulos |
| Botão | 36 px de altura (44 px em tela de toque), borda `--borda-controle`, raio de 4 px, letra `--texto`. Principal: fundo `--destaque`, letra `--tinta-escura` | Sob o ponteiro: fundo `--relevo`. Foco: `--foco` |
| Filtros | Uma fileira acima da lista que recortam. Botões juntos para a categoria, com contagem. Listas nativas (`select`) para o resto. Campo de busca de 36 px | Seção 6 |
| Dica flutuante | Fundo `--relevo`, borda `--borda-controle`, 13 px, espaço interno de 8 px, largura máxima de 280 px. Valor primeiro, em `--texto`; rótulo depois, em `--texto-2` | Na fita, só repete o que a tabela gêmea já diz. Nas etiquetas com dica (EXCEÇÃO, ALÍVIO, PERGUNTA-CHAVE, "anterior", "sem alvo"), o texto da dica também vai no nome acessível. Abre com o ponteiro e com o foco. Fecha com Esc |
| Link | `--destaque`, sublinhado de 1 px | Externo: abre em nova aba, com o ícone `i-externo` e `rel="noopener noreferrer"`. Antes de virar link, todo endereço vindo de JSON passa por `new URL(endereço)`: o `protocol` tem de ser `http:` ou `https:`, sem barra invertida no texto e sem usuário ou senha antes do `@` (a mesma recusa da regra de URL do validador). Se não é, ou se o endereço não abre como URL, vira texto simples, sem `href`. Link interno é montado pelo site, com `encodeURIComponent` em cada id |

### 5.2 Estados

| Estado | Quando | O que aparece |
|---|---|---|
| Carregando | Antes de os dados chegarem | A moldura com os títulos das seções já está no HTML. No lugar dos valores, travessão. Texto "Carregando edição…". Nada pisca. Depois de 8 segundos: "Está demorando" e botão "Tentar de novo". Na troca de edição, o quadro anterior fica na tela, inteiro, com `aria-busy="true"`, e o carimbo diz "Carregando edição de DD/MM…" até a nova chegar. Nada esmaece: texto a 50% de opacidade cai abaixo do contraste mínimo (seção 10). Filtro não carrega nada: o recorte é imediato |
| Vazio | Índice sem edição | Aviso "NENHUMA EDIÇÃO AINDA". Régua e Método funcionam |
| Erro de rede | Índice ou edição não carregou | Aviso grave "FALHA AO CARREGAR", com o nome do arquivo, botão "Tentar de novo" e links para o Arquivo e o feed. O último quadro bom fica na tela |
| Dado de apoio em falta | Régua, players, veículos, vetores ou catálogo não carregou | A edição aparece com os identificadores crus e um aviso. Sem a régua, o selo mostra o numeral e "NÍVEL N". Sem os vetores, não há reincidência nem marca de anulado. Sem o catálogo, não há aviso: o valor sai com 2 a 4 casas |
| Mapa em rascunho | `revisado_em` é `null`, ou falta, em `dados/veiculos.json` | Nota de seção no Painel 04 e 08 e aviso no topo da aba Veículos. Some quando o campo traz uma data |
| Edição atrasada | No Painel: agora menos o `gerada_em` da edição que o Painel mostra passa de 26 horas | Placa ATRASADA com relógio. Aviso grave no topo. No bloco de alerta, a linha "Quadro de DD/MM, não de hoje". Os valores não somem nem esmaecem |
| Edição de exemplo | `exemplo: true` | Aviso grave no topo do Painel. Etiqueta EXEMPLO em cada título de seção. Título da aba começa com "[EXEMPLO]". Sem fita e sem acumulado. Não entra no histórico nem no feed |
| `completa` | Estado normal | Placa EM DIA (ou ATRASADA). 3 principais |
| `reduzida` | Menos itens que o normal (coleta que falhou, falta de tempo, dia fraco, item cortado) | Placa REDUZIDA e aviso. As seções mostram o que houver: 1 a 3 principais, 3 a 12 no radar |
| `falha` | A rotina não fechou a edição | Placa SEM EDIÇÃO. Título da aba "INFOCENARIUM · {data} · sem edição", como no feed, sem o nível repetido. Aviso grave com o `resumo` e link para a última edição que não é `falha`; o `resumo` da falha começa com "Sem edição hoje. " (CONTRATO, seção 4.3), e o aviso tira esse começo, que repetiria o rótulo. As seções 01 e 02 mostram os níveis repetidos, com a nota "NÍVEIS REPETIDOS DE DD/MM" (a data da edição anterior; sem edição anterior, "NÍVEIS SEM BASE: AINDA NÃO HOUVE EDIÇÃO"). A seção 02 ainda mostra "sem dado de preço de: …", se houver. A seção 03 mostra os indicadores que houver. As seções 04 a 08 não aparecem: no lugar delas, uma linha só, "Sem itens: a rotina não fechou a edição deste dia.". A seção 09 mostra os `limites`, os candidatos e os veículos sugeridos; o modo e os números ficam de fora, porque a falha não os mede (grava modo `feeds` e contadores em 0) |
| Edição de arquivo | Rota `#/edicao/…` | Placa ARQUIVO e link para a mais recente |
| Corrigida | `corrigida_em` não vazia | Aviso com link para cada edição que traz a errata |
| Nível mantido | Domínio com `gatilhos` vazia e `nivel` maior que 1 | Etiqueta "MANTIDO DESDE DD/MM" antes da `leitura` |
| Sem dado de preço | Domínio com `sem_preco` não vazia | A linha "sem dado de preço de: …" na linha do domínio, fechada ou aberta. O nível não muda de desenho: quem não mediu foi o INFOCENARIUM |
| Alívio | Gatilho com `alivio` | Etiqueta ALÍVIO no gatilho, com a dica da seção 8.3. É o gatilho que explica uma descida de nível 4 ou 5 |
| Vetor anulado | Há em `dados/vetores.json` uma entrada com `anula` igual ao `id` do vetor (`DATA_ITEM_PLAYER`) | O vetor aparece riscado, com ANULADO e o motivo, no Painel 07, no dossiê, na ficha do player e na aba Vetores. Não conta em reincidência nem no número de vetores do player |
| Conflito de interesse | Item com `conflito_de_interesse`; entrada de vetor com o mesmo campo | Etiqueta no cartão e na linha do radar. Aviso fixo da seção 8.3 no topo do item aberto. Etiqueta ao lado de cada vetor do item, também na Régua |
| Lista vazia | `placar`, `vetores`, `dominios`, `novos_players`, `respostas`, `candidatos`, `veiculos_sugeridos` ou `indicadores` sem item; item sem `eixo` | A frase da seção 8.4. A seção nunca some. `placar` vazia mostra o `sem_placar`; edição antiga sem esse campo mostra a frase |
| Referência quebrada | Um id da edição (player, partido, veículo, tema, domínio, indicador, vetor) não existe no arquivo de apoio; uma data citada (`edicao`, `continuacao_de`, `corrigida_em`) não está no índice | Mostra o id cru, em mono, ou a data, sem link e sem etiqueta. Nunca dá erro. É o caso da edição de exemplo, que cita edições e um vetor que não existem |
| Endereço sem destino | A rota pede edição, item ou ficha que não existe | Edição: abre o Arquivo, com aviso. Item: abre a edição, sem abrir nada, com aviso. Ficha da Régua: abre a aba, com aviso. Textos na seção 8.2 |
| Filtro sem resultado | Nenhum item passa | Mensagem e botão "Limpar filtros" |
| Edição nova | O índice é lido de novo (no máximo uma vez a cada 5 minutos) quando a aba volta a ficar visível e, no Painel com a edição atrasada, a cada volta do relógio da idade com a aba visível; há edição mais nova, ou a edição em tela mudou de `gerada_em` | Aviso com botão "Carregar". O texto nunca troca sozinho |
| Sem JavaScript | `<noscript>` | Texto fixo com link para o `feed.xml`, no começo do `main` (antes de "Carregando edição…") e de novo depois do rodapé |

### 5.3 Esqueleto do `index.html`

O que já vem escrito no arquivo, antes de qualquer dado:

- `<html lang="pt-BR">`. No `head`, nesta ordem: `<meta charset="utf-8">`; `<meta name="viewport" content="width=device-width, initial-scale=1">`; `<meta name="color-scheme" content="dark">`; `<meta name="referrer" content="no-referrer">`; a política de conteúdo abaixo; `<title>` com "INFOCENARIUM · monitor geopolítico e de IA"; `<meta name="description">` com "Monitor diário de geopolítica e de IA: o que aconteceu, quem atirou, quem ganha e o que muda para quem se prepara."; `<link rel="alternate" type="application/atom+xml" href="feed.xml">`; `<link rel="icon" href="data:,">` (sem arquivo de ícone, e sem pedido perdido ao servidor); `<link rel="stylesheet" href="assets/estilo.css">`; `<script src="assets/app.js" defer>`.
- Política de conteúdo, em `<meta http-equiv="Content-Security-Policy">`: `default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'none'`. Ela trava no navegador o que a seção 9 proíbe: nada de fora, nenhum script escrito na página. Por causa dela, o HTML não leva atributo `style` nem script embutido; tamanho de barra e de coluna o script põe por `elemento.style`.
- No `body`: o link "Pular para o conteúdo"; o `<svg>` dos símbolos, escondido; `header` com a marca e a navegação; a região `aria-live`; `main`, que começa com uma cópia do `<noscript>` (quem está sem script lê o aviso antes da moldura) e traz a moldura do Painel (os títulos das seções 01 a 09 e travessões no lugar dos valores); `footer`; `<noscript>`.
- As vistas Arquivo, Régua e Método são montadas pelo script, dentro do mesmo `main`. Só uma vista existe no documento por vez.
- Todo caminho é relativo, sem barra no começo: o site mora em uma subpasta.

## 6. Interação

**Rotas por hash.**

| Rota | Vista |
|---|---|
| `#/` | Painel |
| `#/?cat=ia&dom=energia&partido=soberanistas` | Painel com os filtros do radar |
| `#/edicao/AAAA-MM-DD` | Edição daquele dia. É o endereço que o `feed.xml` usa |
| `#/edicao/AAAA-MM-DD/p2` | A edição, com o item aberto e em foco. Vale, nesta ordem de procura: `p1` a `p3`, `r1` a `r12`, o id de um domínio (`#/edicao/AAAA-MM-DD/energia` abre a linha do domínio) e o id de um indicador (põe a ficha em foco). Os filtros do radar também valem aqui: `#/edicao/AAAA-MM-DD/r4?cat=ia` |
| `#/arquivo` e `#/arquivo?nivel=3` | Arquivo; com nível mínimo |
| `#/regua` | Vai para `#/regua/partidos` |
| `#/regua/partidos` e `#/regua/partidos/soberanistas` | Aba Partidos; com a ficha em foco |
| `#/regua/players`, `#/regua/players/macron`, `#/regua/players?partido=…&tipo=…&time=…&q=…` | Aba Players; com a linha aberta; com filtros |
| `#/regua/veiculos`, `#/regua/veiculos/reuters`, `#/regua/veiculos?lado=…&fatos=…&tipo=…&q=…` | Aba Veículos; idem |
| `#/regua/vetores`, `#/regua/vetores?player=ue` e `#/regua/vetores/2026-11-20_p1_ue` | Aba Vetores; só de um player; com a linha daquele vetor em foco |
| `#/metodo`, `#/metodo/conflito`, `#/metodo/perguntas`, `#/metodo/regua`, `#/metodo/niveis`, `#/metodo/indicadores`, `#/metodo/rotina`, `#/metodo/limites` | Método; rolado até a seção |
| Qualquer outra | Painel, com o aviso "ENDEREÇO NÃO ENCONTRADO" |

Regras das rotas:

- A parte depois de `#/` se divide em caminho e consulta, no primeiro `?`. Parâmetro desconhecido, ou com valor fora da lista, é ignorado.
- Data só vale na forma `AAAA-MM-DD`. Id só vale na forma `^[a-z0-9_-]{1,64}$`. Fora disso, é "qualquer outra".
- Dentro de uma vista, um link para outra parte da mesma página (um domínio, um item, um indicador) é uma rota como as outras: abre, rola e põe o foco.
- **Vizinhas.** "Edição anterior" e "Edição seguinte" andam pelo índice, uma entrada por vez, contando a `falha` e pulando a de `exemplo: true`. Na primeira e na última, o botão não aparece.

**Filtros.** Radar: categoria (Todas, Geopolítica, IA, com contagem), domínio e partido. O partido casa com o `partido` do placar, o `lado` do ataque, o alvo (partido ou player dele) e os vetores (o partido do player ou o de `para`). Alvo `outro` e alvo `nenhum` não casam com partido nenhum. Os filtros se somam: o item tem de passar em todos. A busca ignora maiúscula e acento, procura no `nome` e no `id`, e recorta a cada tecla. Players: partido, tipo, time e busca. Veículos: lado, fatos, tipo e busca. Arquivo: nível mínimo. Todo filtro vai para o endereço e volta dele. Filtrar nunca muda cor nem ordem. A contagem ("4 de 9 itens") é anunciada. Nada fica guardado no aparelho.

**Abrir e fechar.** Um botão por dobra, com `aria-expanded` e `aria-controls`; o conteúdo usa o atributo `hidden`. Em linha de domínio e de radar, o toque em qualquer ponto do cabeçalho que não seja link também abre. Abrir um item grava o endereço dele (`#/edicao/DATA/ID`, com os filtros que houver) por `history.replaceState`, sem criar passo no histórico. Fechar grava de volta o endereço da edição. Chegar por um endereço de item abre, rola e põe o foco no título. Tudo começa fechado. Mais de um item pode ficar aberto: abrir um não fecha o outro.

**Teclado.** Tab segue a ordem de leitura. Enter e Espaço acionam botões. Esc fecha a dobra onde está o foco e devolve o foco ao botão; também fecha a dica. Não há atalho de uma tecla. As abas da Régua são links comuns dentro de um `nav`, não um conjunto de abas com setas.

**Foco.** Contorno de 2 px em `--destaque`, afastado 2 px, em tudo o que recebe foco. Ao trocar de rota, o foco vai para o `h1` da vista, o título da aba muda e a página rola para o topo.

**Dados.** Todo texto de JSON entra por `textContent` ou `createTextNode`. Nunca `innerHTML`. Isso vale também para o que vira atributo (nome acessível, texto de `<abbr>`, `datetime`): entra por `setAttribute`, nunca colado em HTML. Um valor de JSON só vira classe, `id` de elemento ou parte de endereço depois de conferido contra a forma de id da tabela de rotas. Rótulos de listas fechadas (categoria, evidência, tendência) saem da tabela da seção 8.8; valor desconhecido aparece cru. Texto longo sem espaço quebra (`overflow-wrap: anywhere`). O site não grava nada e não envia nada.

**Datas e números.** `data`, `desde`, `publicado_em` e as outras datas são texto `AAAA-MM-DD`: o site corta o texto para montar "19/11" e "19/11/2026", sem passar por `Date` (que mudaria o dia pelo fuso). Data-hora (`gerada_em`, `atualizado_em`) é UTC: a hora de Brasília sai de `Intl.DateTimeFormat("pt-BR", { timeZone: "America/Sao_Paulo" })`. Idade: menos de 1 minuto, "AGORA"; até 59 minutos, "HÁ N MIN"; até 47 horas, "HÁ N H"; depois, "HÁ N DIAS". Número com `toLocaleString("pt-BR")`. Sinal de menos é o tipográfico (−). Zero não leva sinal.

## 7. Acessibilidade e impressão

- `lang="pt-BR"`. Marcos `header`, `nav`, `main` e `footer`. Um `h1` por vista, `h2` por seção, `h3` por item, `h4` por parte do dossiê. Link "Pular para o conteúdo" como primeiro elemento.
- Texto com contraste de 5,59 para 1 ou mais. Elemento gráfico com 3,04 para 1 ou mais. Os números estão na seção 10.
- Nada depende só de cor. Nível: ícone, numeral e rótulo. DNA: letra. Placar: lado, sinal e palavra.
- Selo de nível, para leitor de tela: "Nível 3 de 5, tensão, subindo". Ícone e medidor ficam com `aria-hidden`.
- Célula de DNA: o `nome` do tema na régua e o polo ("Mudanças climáticas: polo azul"). Virada: "Imigração: virada de misto para polo vermelho". Com dúvida, acrescenta ", posição em dúvida".
- Linha do placar: "Soberanistas: saldo mais 2". Com narrativa: "Soberanistas: saldo zero; na narrativa, mais 2". A barra fica com `aria-hidden`.
- Vetor anulado: o nome acessível começa com "Anulado:". O risco sozinho não avisa o leitor de tela.
- Linha de eixo: "Mudanças climáticas: empurra para fósseis livres, minimizar o problema".
- Toda figura (fita, mini-linha) tem `role="img"`, um nome que resume ("Alerta nos últimos 30 dias: de 1 a 3; hoje, 3") e a tabela gêmea em "Ver tabela".
- Tabelas com `caption`, `th` e `scope`. Datas em `<time datetime>`. Siglas em `<abbr>`.
- Uma região `aria-live="polite"` anuncia carga, erro e contagem de filtro. A idade do carimbo não é anunciada.
- Link externo traz o texto escondido "(abre em nova aba)". O `titulo` das fontes fica como foi publicado, com `translate="no"`. Leva `lang` só quando o veículo do mapa tem um idioma só em `idiomas` e ele é uma marca de idioma válida (`fox_news`, `en`); com vários idiomas, `multi` ou fonte `outro`, fica sem `lang`, porque o veículo pode publicar em português (o `sputnik` tem `noticiabrasil.net.br`). A solução completa é um campo de idioma na fonte, no ESQUEMA.
- Alvo de toque de 44 px em tela de toque. Sem rolagem lateral a 320 px de largura nem com zoom de 200%.
- O foco do teclado não fica sob a barra presa (WCAG 2.2, critério 2.4.11; técnica C43 do W3C): no compacto, `html { scroll-padding-bottom: altura da navegação + área segura + 8 px }`; do médio para cima, `html { scroll-padding-top: altura do topo + 8 px }`. O `scroll-margin-top` dos alvos de rota soma com ele: 8 px (72 px do alto, como antes) e, na matriz da Régua, 64 px (128 px); o botão de dobra da matriz leva 48 px, para não ficar sob o cabeçalho preso.
- Movimento: só o conteúdo de uma dobra que abre, com a opacidade de 0 a 1 em 120 ms. Texto parado nunca fica com opacidade menor que 1. Com `prefers-reduced-motion: reduce`, nenhuma transição e nenhuma rolagem suave. Nada pisca, nada se move sozinho.
- `prefers-contrast: more`: `--texto-3` vira `#b3bcc6`, `--fio` vira `#313a44` e `--fio-forte` vira `#6f7b88`.
- `forced-colors: active`: segmento aceso com fundo `CanvasText`; apagado só com borda; célula de DNA só com borda e letra.

**Impressão** (`@media print`, com as variáveis da seção 4):

- Papel branco, tinta preta. Corpo de 11 pt. Margem de 15 mm.
- Somem: navegação, filtros, botões, dicas e o aviso de edição nova.
- Tudo aberto: a regra `[hidden]` das dobras é anulada no CSS de impressão, sem depender de script.
- No topo de cada impressão de edição: "INFOCENARIUM · edição de DD/MM/AAAA · nível N RÓTULO". No Arquivo, na Régua e no
  Método, o papel leva a marca do topo e o título da vista. O aviso de exemplo é impresso.
- As marcas que são cor de fundo (medidor, placa grave, barras do placar, fita, pontos de força) levam
  `print-color-adjust: exact`: sem isso, o navegador não as imprime.
- Depois de cada link externo, o endereço por extenso entre parênteses.
- Cartão, linha de domínio e ficha não quebram no meio (`break-inside: avoid`).
- Ícone de nível em preto. Segmento aceso em preto, apagado só com borda. DNA na variante sem cor. A forma, a letra e o rótulo dispensam a cor.

## 8. Textos fixos da interface

Entre chaves, o que o site preenche. Datas: "20/11/2026" por extenso, "20/11" na forma curta. Hora de Brasília: "18h12". Números e porcentagens no padrão brasileiro.

### 8.1 Marca, navegação e carimbo

| Onde | Texto |
|---|---|
| Marca e subtítulo | INFOCENARIUM · monitor geopolítico e de IA |
| Título da aba | Painel e edição: INFOCENARIUM · {data} · nível {N} {RÓTULO} (ou: sem edição). Outras vistas: INFOCENARIUM · {vista}. Edição de exemplo: começa com [EXEMPLO] |
| Navegação | Painel · Arquivo · Régua · Método |
| Primeiro link | Pular para o conteúdo |
| Título da vista (`h1`) | Painel e edição: "Edição de {data}", escondido da vista e lido pelo leitor de tela (o carimbo já mostra a data). Outras vistas, visível, em 22 px: Arquivo · Régua · Método |
| Carimbo | ED. {data} · GERADA {hora} (BRASÍLIA) (ou: GERADA {DD/MM} {hora} (BRASÍLIA)) · HÁ {N} MIN (ou AGORA, HÁ {N} H, HÁ 1 DIA, HÁ {N} DIAS) · Na troca de edição: Carregando edição de {data}… |
| Placas | EM DIA · ATRASADA · REDUZIDA · SEM EDIÇÃO · EXEMPLO · ARQUIVO |
| Vizinhas | Edição anterior, de {data} · Edição seguinte, de {data} · Ir para a mais recente. Na tela, o botão mostra só a seta e a data curta ("‹ 18/11", "20/11 ›"); a frase inteira é o nome acessível |
| Links | texto · JSON · feed |
| Rodapé | Análises escritas por IA: o Claude, da Anthropic, que é um dos players da régua. Leia o aviso em Método. Sem cookies, sem rastreador, nada de terceiros. |

### 8.2 Avisos

| Aviso | Texto |
|---|---|
| Exemplo | EDIÇÃO DE EXEMPLO · Dados fictícios. Nada aqui aconteceu. Serve só para mostrar como o site funciona. |
| Sem edição | SEM EDIÇÃO HOJE · A rotina de {data} não conseguiu fechar a edição. {resumo} Os níveis abaixo repetem os de {data anterior}. Ver a última edição ({data}). (Sem edição anterior, as duas últimas frases dão lugar a: Ainda não houve edição: todos os níveis estão em 1.) |
| Atrasada | EDIÇÃO ATRASADA · A mais recente é de {data} e foi gerada há {N} h. A edição sai todo dia às 18h de Brasília. O quadro abaixo não é de hoje. |
| Reduzida | EDIÇÃO REDUZIDA · Há menos itens que o normal. Veja o que não deu para conferir em Bastidores. |
| Arquivo | EDIÇÃO DE ARQUIVO · Você está lendo a edição de {data}. |
| Corrigida | EDIÇÃO CORRIGIDA · Há correção a esta edição na errata de {data}. |
| Errata | ERRATA · Esta edição corrige 1 ponto de edições anteriores. (ou: corrige {N} pontos) · Edição de {data}, item {id}. (sem `item`: Edição de {data}, inteira.) · Estava errado: {erro} · O certo: {correcao} · Fonte da correção. · Com `anula_vetor`: Esta correção anula o vetor de {data}: {player} → {sigla}. Ver no registro. |
| Edição nova | HÁ EDIÇÃO NOVA · Saiu a edição de {data}. Carregar. |
| Formato | FORMATO NOVO · Esta edição usa um formato mais novo que o site. Alguma parte pode não aparecer. (em arquivo de apoio: O arquivo {arquivo} usa um formato mais novo que o site.) |
| Mapa em rascunho, na aba Veículos | MAPA EM RASCUNHO · Mapa em rascunho, ainda sem revisão do dono. O lado de cada veículo é classificação editorial. |
| Mapa em rascunho, nota do Painel 04 e 08 | Mapa de veículos em rascunho, ainda sem revisão do dono. Ver o mapa. |
| Rota | ENDEREÇO NÃO ENCONTRADO · Mostrando o Painel. |
| Edição que não existe | NÃO HÁ EDIÇÃO DE {data} · Mostrando o Arquivo. |
| Item que não existe | ITEM NÃO ENCONTRADO · A edição de {data} não tem o item {id}. |
| Ficha que não existe | FICHA NÃO ENCONTRADA · Não há nada na Régua com o identificador {id}. |
| Apoio em falta | DADOS DE APOIO INDISPONÍVEIS · Não deu para carregar {arquivo}. Alguns nomes aparecem como identificadores. |
| Régua em falta | RÉGUA INDISPONÍVEL · Nomes e rótulos aparecem como identificadores. |
| Mapa em falta | MAPA DE VEÍCULOS INDISPONÍVEL · Os veículos aparecem pelo identificador, sem lado. |
| Carregando | Carregando edição… · Está demorando. A conexão pode estar lenta. Tentar de novo. |
| Vazio | NENHUMA EDIÇÃO AINDA · A primeira sai às 18h de Brasília. |
| Erro | FALHA AO CARREGAR · Não deu para carregar {arquivo}. Confira a conexão. Tentar de novo. Abrir o Arquivo de edições. O feed traz o resumo das últimas edições. |
| Sem JavaScript | O INFOCENARIUM precisa de JavaScript para montar o painel. Sem ele, acompanhe as edições pelo feed. |

### 8.3 Painel

| Seção | Textos |
|---|---|
| Títulos | 01 HOJE · 02 DOMÍNIOS · 03 INDICADORES · 04 PRINCIPAIS · 05 PLACAR DO DIA · 06 O QUE VIGIAR · 07 MOVIMENTOS · 08 RADAR ({N}) · 09 BASTIDORES |
| Hoje | de 5 · subindo · estável · descendo · antes ({data}): {N} {RÓTULO} · Primeira edição: sem comparação. · Desde {data}: {domínio} {N} → {N} (um trecho por domínio que mudou, com o nome do domínio em minúsculas, separados por " · ") · Desde {data}: nenhum nível mudou. · Motivo: · ALERTA, 30 DIAS · Ver tabela · Esconder tabela · Quadro de {data}, não de hoje. · NÍVEIS REPETIDOS DE {data} · NÍVEIS SEM BASE: AINDA NÃO HOUVE EDIÇÃO · Sem itens: a rotina não fechou a edição deste dia. |
| Domínios | era {N} · sem dado de preço de: {nomes} · COMO CHEGA AO BRASIL · Neste nível desde {data}. · GATILHOS DE HOJE · EXCEÇÃO (dica: "Fato fora da tabela de critérios, tratado como equivalente a este nível.") · ALÍVIO (dica: "Acabou o estado que sustentava o nível. Por isso o domínio desce um degrau.") · ver principal {N} · ver radar {N} · ver indicador: {nome} · PRÓXIMO SINAL · MANTIDO DESDE {data} · Sem gatilho novo. O nível desce um degrau depois de 2 edições seguidas sem gatilho. Edição sem dado de preço não entra nessa conta. · Abrir: {nome} · Fechar: {nome} |
| Indicadores | anterior (dica: "Variação sobre o ponto anterior da série.") · 7 dias · sem dado · DE {data} · GATILHO · Fonte: {nome} · Fonte prevista: {nome} |
| Principais | GEOPOLÍTICA · IA · CONFIANÇA ALTA · CONFIANÇA MÉDIA · CONFIANÇA BAIXA · CONFLITO DE INTERESSE · CONTINUAÇÃO DE {data} · Atirou: · Placar: · {SIGLA} +{força} (ganha) · {SIGLA} −{força} (perde) · narrativa (depois do número, em linha de evidência `narrativa`: "SO +1 narrativa") · sem ganhador · sem alvo · Abrir dossiê · Fechar dossiê |
| Dossiê | O QUE ACONTECEU · NÃO CONFIRMADO · QUEM ATIROU ({N}) · sem alvo (dica: "O texto só relata, ou só promove alguém. Não ataca ninguém.") · Deixou de fora: · Segundo a leitura do INFOCENARIUM em {data}. · ler no veículo · LADO INCERTO · FOGO AMIGO · FORA DO MAPA · O QUE ESTÁ REALMENTE ACONTECENDO · NA PRÁTICA · O ATO NA RÉGUA · empurra para: · QUEM GANHA E QUEM PERDE · ganha · perde · força {N} de 3 · MOVIMENTOS · prova · {N}ª vez em 30 dias · ANULADO · Anulado em {data}: {motivo} · fonte da correção · PARA QUEM SE PREPARA · No Brasil: · Domínios: · Vigiar: · PERGUNTA-CHAVE (dica: "É a pergunta que derruba esta leitura. O INFOCENARIUM responde quando a data vencer.") · FONTES ({N}) · FONTE PRIMÁRIA |
| Conflito no item | CONFLITO DE INTERESSE · Aviso: o INFOCENARIUM é escrito por um modelo de IA da Anthropic, que é do setor de IA e pode ser parte ou concorrente nesta notícia. · Este item envolve nomes da lista de conflito da régua: {nomes}. · Por isso a confiança deste item não passa de média. Ver Método. (A primeira frase é o aviso fixo do ESQUEMA, palavra por palavra. A frase dos nomes só aparece quando a lista `conflito` da régua conhece o vínculo: o nome do player de `conflito.players` citado como alvo ou em vetor, e o termo de `conflito.termos` escrito em algum texto do item, palavra inteira, como a regra R19 lê; termo que já está no nome de um player listado não se repete. Item marcado só por ser de IA leva só o aviso fixo. Os nomes vêm da régua de hoje, não da do dia da edição.) |
| Placar do dia | Saldo é a soma das forças do dia: ganhar soma, perder subtrai. Ganho só de narrativa não entra no saldo: aparece à parte. Barra à direita, ganhou. À esquerda, perdeu. · narrativa {+N ou −N} · sem movimento hoje · 30 dias {saldo} |
| O que vigiar | SINAIS · Sinais que mudariam o quadro. Cada pergunta tem data. · {Nome do domínio}: · Principal {N}: · RESPOSTAS ({N}) · O INFOCENARIUM responde às próprias perguntas quando a data vence. · SIM · NÃO · SEM DADO · fonte · perguntado em {data}, principal {N} |
| Movimentos | Ninguém muda de partido. O vetor mostra para onde o player se desloca. · NOVO PLAYER · Por que entrou: · Fontes das posições: · time discutível · posição em dúvida · Ver a ficha na Régua |
| Radar | Todas ({N}) · Geopolítica ({N}) · IA ({N}) · Filtrar por domínio (nome do campo) · Todos os domínios · Filtrar por partido (nome do campo) · Todos os partidos · Limpar filtros · {n} de {N} itens |
| Bastidores | coleta normal, pelos feeds dos veículos · a coleta falhou: edição feita por busca · veículos consultados · feeds lidos · feeds que falharam · páginas lidas · buscas · minutos de trabalho · páginas descartadas por trazer ordens ao agente · O QUE NÃO DEU PARA CONFERIR · ATORES SEM FICHA NA RÉGUA · VEÍCULOS QUE FIZERAM FALTA |

### 8.4 Listas vazias

| Lista | Frase |
|---|---|
| Gatilhos, no nível 1 | Nenhum gatilho hoje. |
| Indicadores | Nenhum indicador nesta edição. |
| Placar do item | O texto de `sem_placar`. Só em edição sem esse campo: Nenhum partido ganhou ou perdeu de forma medida. |
| Placar do dia | Nenhum partido ganhou ou perdeu hoje. (Só a frase, sem as 7 linhas.) |
| Vetores e player novo, os dois vazios | Nenhum movimento hoje. (Só o player novo vazio: nenhuma frase.) |
| Vetores do item | Nenhum movimento neste item. |
| Eixo do item | Nenhum ato desta notícia mexe num tema da régua. |
| Domínios do item | Não mexe nos cinco domínios. |
| Respostas | Nenhuma pergunta venceu hoje. |
| Atos por tema, no Arquivo | Nenhum ato registrado em 30 dias. |
| Alerta geral e Domínios, no Arquivo, com uma edição só no histórico (sem nenhuma, travessão) | O desenho aparece a partir da 2ª edição. |
| Indicadores, no Arquivo, com edição no histórico e nenhum preço (sem nenhuma edição, travessão) | Nenhum preço medido nos últimos 30 dias. |
| Candidatos e veículos sugeridos | Nenhum. |
| Radar filtrado | Nenhum item do radar com estes filtros. |
| Vetores da Régua | Nenhum vetor registrado ainda. |
| Arquivo | Nenhuma edição no arquivo. |
| Busca na Régua | Nada encontrado para "{busca}". |

### 8.5 Arquivo

Arquivo · 01 HISTÓRICO · ÚLTIMOS 30 DIAS · Alerta geral · Domínios · Saldo dos partidos · Atos por tema · Quantas notícias trouxeram um ato (lei, decreto, decisão, compra) que empurra cada tema, e para que lado. · Tema · Polo · Atos · Indicadores · primeiro · último · Edições de exemplo ficam fora do histórico. · Ver tabela · Esconder tabela · 02 EDIÇÕES · Nível mínimo · Todos os níveis · 2 ou mais · 3 ou mais · 4 ou mais · Só 5 · {Mês} de {ano} ({N}) · Data · Estado · Nível · Domínios · Resumo · completa · reduzida · sem edição · corrigida em {data} · texto · JSON · Índice atualizado em {data}, às {hora}.

Siglas dos domínios na lista de edições, fixas no site: ENE (energia) · ALI (alimentos) · CAM (câmbio) · SUP (suprimentos) · CON (conflito). Cada uma vai em `<abbr>`, com o `nome` da régua.

### 8.6 Régua

| Onde | Textos |
|---|---|
| Geral | Régua · Partidos · Players · Veículos · Vetores · COMO LER · polo azul · polo vermelho · misto · sem posição conhecida · saiu do cargo · virada: antes e agora |
| Partidos | voto típico · Sem voto típico: acompanha bancadas diferentes. · diante da ordem · players ({N}) · saldo em 30 dias · TIMES · time discutível |
| Players | Buscar player · Todos os partidos · Todos os tipos · Todos os times · Da régua original · Entrou em {data}, pela rotina · Por que entrou: · Fontes das posições: · fonte · posição em dúvida em: {temas} · Vetores registrados ({N}) · {n} de {N} players |
| Veículos | O aviso MAPA EM RASCUNHO da seção 8.2 · Mapa revisado em {data}. · Lado e fatos são coisas separadas: um veículo pode acertar o fato e servir a um lado pelo que escolhe cobrir. · Buscar veículo · Todos os lados · Qualquer confiabilidade · Todos os tipos · lado · confiança no lado · confiabilidade nos fatos · alta · média · baixa · País · Idiomas · Sites · Quem controla · fonte · Serve a · Alvos · Por que este lado · Sobre os fatos · Uso no monitor · Feeds · conferido · não conferido · Nenhum feed. · {n} de {N} veículos |
| Vetores | REGISTRO DE VETORES · O registro só cresce. Vetor errado não se apaga: é anulado, e fica à vista. · Data · Player · De · Para · Força · Tema · Por quê · Prova · Item · ANULADO · Anulado em {data}: {motivo} · fonte da correção · CONFLITO DE INTERESSE · Mostrar mais 50 · {n} de {N} vetores |

### 8.7 Método

Títulos: Método · 01 AVISO DE CONFLITO DE INTERESSE · 02 AS QUATRO PERGUNTAS · 03 A RÉGUA · 04 NÍVEIS DE ALERTA · 05 DE ONDE VEM CADA NÚMERO · 06 COMO A EDIÇÃO É FEITA · 07 LIMITES E CORREÇÕES.

**Aviso de conflito de interesse** (caixa no topo, texto integral):

> As análises do INFOCENARIUM são escritas por um modelo de inteligência artificial (IA): o Claude, da empresa Anthropic. A Anthropic é um dos players da régua do INFOCENARIUM. Ou seja: quem escreve é parte interessada em uma das disputas que este site acompanha, a da IA.
>
> O risco é concreto. O modelo pode poupar quem o fez, pesar a mão contra concorrentes ou tratar como neutra a visão de mundo da empresa.
>
> O que o INFOCENARIUM faz para reduzir o risco:
>
> 1. Leva a marca CONFLITO DE INTERESSE todo item de IA. Leva também todo item que tem alguém da lista abaixo como alvo ou como player em movimento, que cita um termo da lista, ou que usa fonte de veículo ligado à Anthropic. A marca é ligada por programa, e ninguém a desliga.
> 2. Nesses itens, a confiança nunca passa de média.
> 3. Nesses itens, um vetor só entra com prova em fonte primária.
> 4. Quando o item envolve um nome ou um termo da lista, ou um veículo ligado à Anthropic, as fontes vêm de veículos de pelo menos 2 partidos.
> 5. Toda afirmação traz o link da fonte, e o placar diz que tipo de evidência sustenta cada ganho ou perda.
> 6. A régua, o mapa de veículos, os critérios de alerta e o código são públicos.
>
> O que isso não resolve: nenhuma pessoa revisa a edição antes de ela sair. Leia com desconfiança e confira as fontes.
>
> Ver a ficha da Anthropic na Régua.

Logo abaixo da caixa, a lista lida de `regua.conflito`, com estes rótulos: A LISTA QUE LIGA A MARCA · Players: · Termos: . O texto de `regra` abre o quadro. Player que não está em `players.json` aparece pelo id.

**As quatro perguntas:**

> Toda edição responde quatro perguntas.
> 1. O que aconteceu de fato? O fato verificável, separado do enquadramento.
> 2. Quem atirou? Toda notícia é lida como um ataque lançado por um veículo. O INFOCENARIUM diz de que lado o veículo está, quem é o alvo e qual é o enquadramento. Fato verdadeiro também é usado como arma: "ataque" não quer dizer "mentira".
> 3. Quem ganha e quem perde na prática? Por partido, olhando por cima das narrativas: o que mudou em preço, tropa, contrato, lei, voto ou sanção.
> 4. O que isso muda para quem se prepara? O nível de alerta e o efeito em energia, alimentos, câmbio, cadeias de suprimento e risco de conflito.

**A régua:**

> A régua classifica cada player em 5 temas (7 posições) e em um partido. Ninguém muda de partido. Quando uma notícia mostra movimento, o INFOCENARIUM registra um vetor: para onde o player se desloca, com que força e por causa de quê. A classificação é editorial. Veja a Régua.

**Níveis de alerta** (antes das tabelas):

> O nível vai de 1 a 5 e só muda com gatilho concreto e citado. O nível geral é o maior entre os cinco domínios. Um domínio sobe no dia em que um critério da tabela é cumprido. Sem gatilho novo, ele se mantém por 2 edições e depois desce um degrau por vez. Dia em que faltou o dado de preço do domínio não entra nessa conta: o INFOCENARIUM não mediu. Um nível 4 ou 5 também desce um degrau quando acaba o estado que o sustentava: é o gatilho de alívio. Alta de preço de nível 3 ou 4 só vale com uma segunda fonte que confirme; sem ela, vale como nível 2. Sem alarmismo: ameaça não é fato consumado.

**De onde vem cada número** (antes do catálogo):

> Os indicadores vêm de fontes públicas e gratuitas. Cada ficha do Painel traz o link da fonte usada no dia. Número antigo aparece com a data. Número que não veio aparece como "sem dado", com o nome da fonte prevista, sem link.

**Como a edição é feita:**

> Todo dia, às 18h de Brasília, um agente de IA roda sozinho, lê as notícias do dia nos veículos do mapa e escreve a edição. Um programa calcula os níveis de alerta, o placar do dia e a marca de conflito de interesse. Um validador automático confere tudo antes de publicar.
> Estados: completa; reduzida (menos itens que o normal); sem edição (a rotina não fechou o dia).
> Confiança: alta pede fontes de veículos dos dois campos (o da ordem e o da contestação) e uma fonte forte. Média pede 2 fontes de veículos de partidos diferentes, ou uma fonte forte. O resto é baixa. Fonte forte é veículo confiável nos fatos, ou documento primário de site oficial.
> Placar: o saldo de um partido soma só o que tem evidência material. Ganho de narrativa é contado à parte e vale no máximo força 1.
> Os quadros abaixo vêm direto da régua: os campos, a escala de força, os tipos de evidência, quando um time avança e que sites valem como fonte primária.

Títulos dos cinco quadros, em mono de 12 px: CAMPOS · FORÇA · EVIDÊNCIA · QUANDO UM TIME AVANÇA · FONTE PRIMÁRIA. No último, as duas listas levam os rótulos "Sites oficiais do Brasil:" e "Outros sites oficiais:", e cada sufixo aparece em mono, como texto.

**Limites e correções** (o primeiro parágrafo vai em caixa de aviso; é o aviso fixo do ESQUEMA, palavra por palavra):

> O INFOCENARIUM não é recomendação de investimento, nem orientação de saúde ou de segurança.
>
> O agente pode errar. Página da web é tratada como dado, nunca como ordem. Edição publicada não muda: a correção sai na errata de uma edição seguinte, e a edição antiga ganha o aviso "corrigida". Vetor errado não se apaga: é anulado e fica riscado no registro. Quando vence a data de uma pergunta-chave, a edição do dia responde se a leitura se confirmou. O lado de cada veículo é classificação editorial; enquanto o mapa não for revisado, ele aparece marcado como rascunho. Este site não usa cookies, não guarda nada no seu aparelho e não carrega nada de terceiros.

Rótulos do catálogo: alimenta gatilho · só contexto · diária · mensal · faixa aceita: de {min} a {max} · casas decimais · leitor · número convertido: × {fator} · prova mínima · eventos · gatilhos de preço · como chega ao Brasil.

### 8.8 Rótulos das listas fechadas

| Lista | Valor → texto |
|---|---|
| categoria | `geopolitica` → Geopolítica · `ia` → IA |
| tendência | `subindo` → subindo · `estavel` → estável · `descendo` → descendo |
| efeito | `ganha` → ganha · `perde` → perde |
| força | O `nome` de `regua.forcas`. Sem a régua: 1 → sinal · 2 → ato reversível · 3 → difícil de desfazer |
| evidência | `preco` → preço · `tropa` → tropa · `contrato` → contrato · `lei` → lei · `voto` → voto · `sancao` → sanção · `narrativa` → só narrativa |
| confiança | `alta` → alta · `media` → média · `baixa` → baixa |
| estado | `completa` → completa · `reduzida` → reduzida · `falha` → sem edição |
| tema extra | `ordem` → Ordem mundial (sigla ORDEM). Os outros 7 vêm de `regua.json` |
| alvo e veículo | `outro` → o `alvo_nome`, ou o `nome` com FORA DO MAPA · `nenhum` → sem alvo |
| sentido | `azul` e `vermelho` nunca viram palavra na tela: o site mostra o texto do polo, do tema em `regua.temas` |
| resposta | `sim` → SIM · `nao` → NÃO · `sem_dado` → SEM DADO |
| modo | `feeds` → coleta normal, pelos feeds dos veículos · `busca` → a coleta falhou: edição feita por busca |
| frequência | `diaria` → diária · `mensal` → mensal |
| confiança no lado e nos fatos | `lado_confianca` e `fatos` usam os rótulos de confiança |
| tipo de veículo | `agencia` → agência · `estatal` → estatal · `publico` → público · `privado` → privado · `plataforma` → plataforma · `oficial` → oficial · `think_tank` → centro de estudos · `dados` → dados |
| origem | `regua` → da régua original · `rotina` → incluído pela rotina |
| janela | `1d` → no dia · `7d` → em 7 dias |
| vêm da régua, pelo `nome` | partido, domínio, tema, tipo de player (`tipos`), time (`times`), campo (`campos`) |
| aparecem crus, em mono | `leitor`, `formato` do feed, `idiomas`, `sites`, o código `criterio` e os sufixos de `sites_oficiais` |

## 9. O que NÃO fazer

- Dar cor a partido. Pintar ganho de verde e perda de vermelho. Pintar variação de preço.
- Pintar o eixo de um item, ou escrever nele as palavras "azul" e "vermelho": o site mostra o texto do polo.
- Somar narrativa ao saldo, ou desenhar narrativa em barra.
- Pintar SIM, NÃO e SEM DADO de cores diferentes: resposta não é acerto nem erro por si.
- Apagar ou esconder vetor anulado: ele fica à vista, riscado, com o motivo.
- Esmaecer texto para dizer "carregando", "antigo" ou "anulado": opacidade derruba o contraste.
- Pôr alerta e posições do DNA na mesma vista.
- Pintar texto com cor de nível ou de posição. Usar cor de nível sem ícone e rótulo.
- Usar cor de alerta em aviso de atraso, de erro ou de exemplo.
- Colorir a fita de histórico pelo nível: a altura já diz, e 30 colunas não levam ícone nem rótulo.
- Usar cinza para ROTINA: cinza é "sem dado".
- Trocar uma cor no olho. Toda troca passa pelas contas da seção 10, refeitas.
- Lançar tema claro na tela sem validar outra paleta.
- Mapa-múndi, rosca, pizza, velocímetro, dois eixos, grade tracejada, barra grossa, bloco saturado, degradê, brilho, linha de varredura.
- Piscar, sirene, contagem regressiva, texto correndo, esqueleto piscando, número que sobe sozinho.
- Mais de um numeral gigante por vista. No celular, mais de um elemento preso à tela.
- Janela modal, carrossel, rolagem lateral, texto que troca sob o leitor.
- Caractere de seta ou de triângulo no lugar de ícone.
- Fonte, imagem, script ou rastreador de fora. Cookie ou armazenamento no aparelho.
- `innerHTML`, `outerHTML`, `insertAdjacentHTML` ou `document.write` com texto de JSON. Link que não seja `http:` ou `https:`. Link externo sem `rel="noopener noreferrer"`.
- Atributo `style` ou script escrito dentro do HTML: a política de conteúdo da seção 5.3 bloqueia.
- Transformar em link o texto de `veiculos_sugeridos`, de `sites` ou de `sites_oficiais`: são nomes de site, não endereços conferidos.
- Esconder atraso, exemplo, errata, conflito de interesse, mapa em rascunho, falta de dado de preço ou limite do dia.
- Misturar edição de exemplo com histórico ou acumulado.
- Esconder uma seção vazia: ela diz o que falta.

## 10. Validação das cores

Tudo abaixo é saída de dois scripts rodados em 23/11/2026, fora deste repositório: um validador de paleta
(`validate_palette.py`, que confere faixa de luminosidade, croma, separação para daltônicos e contraste) e um
script de contraste escrito para esta especificação (`contraste-final.py`). Só as linhas de rodapé do validador
foram cortadas. Uma segunda versão do validador, em Node, deu saída idêntica nas 6 rodadas do modo escuro.

Como as cores foram escolhidas:

- **Alerta.** Uma busca automática (primeiro em grade, depois por subida de encosta) achou conjuntos de 5 matizes que passam em **todos os pares**, sem aviso, nas três superfícies. As 4 cores de estado da referência (`#0ca30c`, `#fab219`, `#ec835a`, `#d03b3b`) ficaram de fora: juntas, reprovam na faixa de luminosidade, no piso de visão normal (13,6) e na distância entre verde e vermelho para daltônicos (4,1). O preço da troca: amarelo e laranja ficam mais escuros que o costume. O ícone, o numeral e o rótulo cobrem isso.
- **DNA.** `#256abf` e `#c98500` são passos da paleta de referência. O vermelho da referência (`#e66767`) reprova ao lado do amarelo (13,0, com piso de 15); entrou `#d1273f`, da proposta A.
- **Destaque, texto e tinta neutra** não são categoria: são conferidos por contraste.

```
$ validate_palette.py "#04896e,#a39700,#9f5910,#e13d62,#b15bdd" --mode dark --surface "#0b0e11" --pairs all
Palette (dark, surface #0b0e11, categorical): 5 slots
  [PASS] Lightness band         all 5 inside L 0.48–0.67
  [PASS] Chroma floor           all 5 >= 0.1
  [PASS] CVD separation         worst all-pairs #e13d62↔#04896e ΔE 8.5 (deutan) · tritan 8.2
  [PASS] Normal-vision floor    worst all-pairs #9f5910↔#a39700 ΔE 16.5 (normal)
  [PASS] Contrast vs surface    all 5 >= 3:1
  → ALL CHECKS PASS
$ validate_palette.py "#04896e,#a39700,#9f5910,#e13d62,#b15bdd" --mode dark --surface "#12161b" --pairs all
Palette (dark, surface #12161b, categorical): 5 slots
  [PASS] Lightness band         all 5 inside L 0.48–0.67
  [PASS] Chroma floor           all 5 >= 0.1
  [PASS] CVD separation         worst all-pairs #e13d62↔#04896e ΔE 8.5 (deutan) · tritan 8.2
  [PASS] Normal-vision floor    worst all-pairs #9f5910↔#a39700 ΔE 16.5 (normal)
  [PASS] Contrast vs surface    all 5 >= 3:1
  → ALL CHECKS PASS
$ validate_palette.py "#04896e,#a39700,#9f5910,#e13d62,#b15bdd" --mode dark --surface "#1a2027" --pairs all
Palette (dark, surface #1a2027, categorical): 5 slots
  [PASS] Lightness band         all 5 inside L 0.48–0.67
  [PASS] Chroma floor           all 5 >= 0.1
  [PASS] CVD separation         worst all-pairs #e13d62↔#04896e ΔE 8.5 (deutan) · tritan 8.2
  [PASS] Normal-vision floor    worst all-pairs #9f5910↔#a39700 ΔE 16.5 (normal)
  [PASS] Contrast vs surface    all 5 >= 3:1
  → ALL CHECKS PASS
$ validate_palette.py "#256abf,#c98500,#d1273f" --mode dark --surface "#0b0e11" --pairs all
Palette (dark, surface #0b0e11, categorical): 3 slots
  [PASS] Lightness band         all 3 inside L 0.48–0.67
  [PASS] Chroma floor           all 3 >= 0.1
  [PASS] CVD separation         worst all-pairs #d1273f↔#c98500 ΔE 11.7 (deutan) · tritan 13.9
  [PASS] Normal-vision floor    worst all-pairs #d1273f↔#c98500 ΔE 19.6 (normal)
  [PASS] Contrast vs surface    all 3 >= 3:1
  → ALL CHECKS PASS
$ validate_palette.py "#256abf,#c98500,#d1273f" --mode dark --surface "#12161b" --pairs all
Palette (dark, surface #12161b, categorical): 3 slots
  [PASS] Lightness band         all 3 inside L 0.48–0.67
  [PASS] Chroma floor           all 3 >= 0.1
  [PASS] CVD separation         worst all-pairs #d1273f↔#c98500 ΔE 11.7 (deutan) · tritan 13.9
  [PASS] Normal-vision floor    worst all-pairs #d1273f↔#c98500 ΔE 19.6 (normal)
  [PASS] Contrast vs surface    all 3 >= 3:1
  → ALL CHECKS PASS
$ validate_palette.py "#256abf,#c98500,#d1273f" --mode dark --surface "#1a2027" --pairs all
Palette (dark, surface #1a2027, categorical): 3 slots
  [PASS] Lightness band         all 3 inside L 0.48–0.67
  [PASS] Chroma floor           all 3 >= 0.1
  [PASS] CVD separation         worst all-pairs #d1273f↔#c98500 ΔE 11.7 (deutan) · tritan 13.9
  [PASS] Normal-vision floor    worst all-pairs #d1273f↔#c98500 ΔE 19.6 (normal)
  [PASS] Contrast vs surface    all 3 >= 3:1
  → ALL CHECKS PASS
$ validate_palette.py "#04896e,#a39700,#9f5910,#e13d62,#b15bdd" --mode light --surface "#ffffff" --pairs all   (impressao em cores)
Palette (light, surface #ffffff, categorical): 5 slots
  [PASS] Lightness band         all 5 inside L 0.43–0.77
  [PASS] Chroma floor           all 5 >= 0.1
  [PASS] CVD separation         worst all-pairs #e13d62↔#04896e ΔE 8.5 (deutan) · tritan 8.2
  [PASS] Normal-vision floor    worst all-pairs #9f5910↔#a39700 ΔE 16.5 (normal)
  [PASS] Contrast vs surface    all 5 >= 3:1
  → ALL CHECKS PASS
$ python3 contraste-final.py validate_palette.py
TEXTO sobre superficie (minimo 4,5)
  --texto                                  #e6ebf0  plano 16.13 | painel 15.14 | relevo 13.68
  --texto-2                                #b3bcc6  plano 10.07 | painel  9.45 | relevo  8.54
  --texto-3                                #8d98a4  plano  6.60 | painel  6.19 | relevo  5.59
  --destaque                               #6cc5d6  plano  9.76 | painel  9.16 | relevo  8.28
ELEMENTO GRAFICO sobre superficie (minimo 3,0)
  --alerta-1 ROTINA                        #04896e  plano  4.43 | painel  4.16 | relevo  3.76
  --alerta-2 ATENCAO                       #a39700  plano  6.44 | painel  6.04 | relevo  5.46
  --alerta-3 TENSAO                        #9f5910  plano  3.60 | painel  3.38 | relevo  3.06
  --alerta-4 CRISE                         #e13d62  plano  4.65 | painel  4.36 | relevo  3.94
  --alerta-5 EMERGENCIA                    #b15bdd  plano  4.99 | painel  4.68 | relevo  4.23
  --dna-b                                  #256abf  plano  3.59 | painel  3.37 | relevo  3.04
  --dna-y                                  #c98500  plano  6.30 | painel  5.91 | relevo  5.34
  --dna-r                                  #d1273f  plano  3.75 | painel  3.52 | relevo  3.18
  --borda-controle                         #6f7b88  plano  4.48 | painel  4.21 | relevo  3.80
  --tinta-dado (placar, fitas, linhas)     #8d98a4  plano  6.60 | painel  6.19 | relevo  5.59
  --destaque (foco, aba ativa, selecao)    #6cc5d6  plano  9.76 | painel  9.16 | relevo  8.28
DECORATIVO (fios e trilhos: sem minimo; o valor esta sempre tambem em numero e rotulo)
  --fio                                    #222a32  plano  1.33 | painel  1.25 | relevo  1.13
  --fio-forte                              #313a44  plano  1.68 | painel  1.57 | relevo  1.42
  trilho do medidor = cor do nivel a 28% sobre o painel
  --alerta-1-trilho                        #0e3632  plano  1.47 | painel  1.38 | relevo  1.24
  --alerta-2-trilho                        #3b3a13  plano  1.66 | painel  1.56 | relevo  1.41
  --alerta-3-trilho                        #392918  plano  1.39 | painel  1.30 | relevo  1.18
  --alerta-4-trilho                        #4c212f  plano  1.44 | painel  1.35 | relevo  1.22
  --alerta-5-trilho                        #3f2951  plano  1.52 | painel  1.42 | relevo  1.29
LETRA dentro de preenchimento (minimo 4,5)
  letra clara em --dna-b                       #ffffff sobre #256abf   5.39
  letra escura em --dna-y                      #0b0e11 sobre #c98500   6.30
  letra clara em --dna-r                       #ffffff sobre #d1273f   5.16
  --texto-2 em --dna-k (#000000)               #b3bcc6 sobre #000000  10.93
  --texto-2 em celula W (painel)               #b3bcc6 sobre #12161b   9.45
  letra escura em placa invertida (--texto)    #0b0e11 sobre #e6ebf0  16.13
  letra escura em botao primario (--destaque)  #0b0e11 sobre #6cc5d6   9.76
BORDA de celula e de placa contra o que ela separa (minimo 3,0)
  borda da celula W contra o painel            #6f7b88 sobre #12161b   4.21
  borda da celula K contra o preto             #6f7b88 sobre #000000   4.86
  placa invertida contra o relevo              #e6ebf0 sobre #1a2027  13.68
IMPRESSAO, papel #ffffff (texto minimo 4,5; marca minimo 3,0)
  texto                #111111  18.88
  texto secundario     #444444   9.74
  marca e borda        #767676   4.54
  fio (decorativo)     #bbbbbb   1.92
  letra branca em placa invertida (#111111)    18.88
DISTANCIA entre trabalhos de cor diferentes (OKLab x100; visao normal / pior entre protan e deutan)
  alerta-2 x dna-y         #a39700 x #c98500  normal   7.5 | daltonico   0.9
  alerta-3 x dna-y         #9f5910 x #c98500  normal  14.1 | daltonico  14.0
  alerta-4 x dna-r         #e13d62 x #d1273f  normal   5.8 | daltonico   5.6
  alerta-1 x destaque      #04896e x #6cc5d6  normal  22.3 | daltonico  21.6
  dna-b x destaque         #256abf x #6cc5d6  normal  26.9 | daltonico  27.2
  tinta-dado x alerta-1    #8d98a4 x #04896e  normal  15.5 | daltonico   9.7
  tinta-dado x alerta-2    #8d98a4 x #a39700  normal  15.9 | daltonico  15.6
falhas: 0
```

Leitura dos resultados:

- **Nenhum FAIL e nenhum WARN** no validador. Zero falhas de contraste.
- **O que não passa por validador, e por quê é aceitável.** Fios e trilhos têm contraste abaixo de 3 para 1: são decoração, e o valor está sempre também em numeral e rótulo. O destaque, os três tons de texto e a tinta neutra não são cores de categoria: valem pelo contraste, que está acima do mínimo.
- **O limite que vira regra.** O último bloco mostra que o amarelo do alerta e o do DNA distam 7,5 (0,9 para daltônicos), e os vermelhos, 5,8. O piso é 15. Por isso alerta e DNA nunca dividem a mesma vista (seção 4).
- **Margens apertadas, ditas às claras.** O laranja do nível 3 fica em 3,06 para 1 sobre o relevo, e o azul do DNA, em 3,04. Passam, mas não aguentam uma superfície mais clara. Quem mudar o relevo refaz as contas.
- **Verde e vermelho** são o par mais fraco para daltônicos (8,5; a meta é 8). Passa. E os dois nunca se distinguem só pela cor: círculo vazado e octógono cheio, 1 e 4.

**Conferência final, de 23/11/2026.** Um segundo script lê as cores direto deste documento e refaz as contas sem usar o primeiro. O que deu:

- Os 81 números de contraste da lista acima conferem, um a um. Os dois pisos citados na seção 7 (5,59 e 3,04) conferem.
- Os 34 hex do documento têm dono: variável da tela, variável da impressão ou cor citada como reprovada. Os 5 trilhos são mesmo a cor do nível a 28% sobre o painel.
- O validador de paleta, rodado de novo nas 7 combinações, deu saída idêntica à colada acima. As duas reprovações citadas (as 4 cores de estado da referência e o vermelho `#e66767`) também se repetem.
- Pares que o documento usa e a lista acima não trazia:

| Par | Contraste | Mínimo | Resultado |
|---|---|---|---|
| Dica: valor em `--texto` e rótulo em `--texto-2`, sobre `--relevo` | 13,68 e 8,54 | 4,5 | passa |
| Sigla de partido sobre `--relevo` (pior caso): letra e borda | 13,68 e 3,80 | 4,5 e 3,0 | passa |
| Letra da célula W (`--dna-wk-letra`) sobre `--relevo` (pior caso) | 8,54 | 4,5 | passa |
| `--tinta-dado-forte` sobre as três superfícies | de 13,68 a 16,13 | 3,0 | passa |
| Mais contraste: `--texto-3` em `#b3bcc6` e `--fio-forte` em `#6f7b88`, sobre `--relevo` | 8,54 e 3,80 | 4,5 e 3,0 | passa |
| Papel: `#444444` (texto 3, barras), `#111111` (links, ícones, letras) e `#767676` (bordas) | 9,74, 18,88 e 4,54 | 4,5, 4,5 e 3,0 | passa |
| Segmento aceso contra o próprio trilho, níveis 1 a 5 | 3,02 · 3,88 · 2,60 · 3,22 · 3,28 | sem mínimo | informativo |
| Coluna da edição em tela contra as outras colunas da fita | 2,45 | sem mínimo | informativo |
| Texto a 50% de opacidade sobre o fundo (`--texto`, `--texto-2`, `--texto-3`) | 4,46 · 3,17 · 2,42 | 4,5 | não passa |

- **Os dois informativos.** O medidor repete o numeral e o rótulo do selo, que estão sempre ao lado: por isso o aceso contra o apagado não tem mínimo, e o nível 3 fica em 2,60. A coluna da edição em tela é sempre a última da fita: a posição já diz qual é.
- **A única reprovação virou regra.** A versão anterior deixava o quadro com 50% de opacidade durante a carga. Isso derruba todo o texto abaixo de 4,5 para 1. A opacidade saiu: o quadro fica inteiro e o carimbo avisa (seção 5.2). Para `--texto-3` passar, a opacidade teria de ser 0,9 ou mais, o que ninguém vê.

## 11. O que o site faz onde este texto não fechava

Alguns trechos acima deixavam duas leituras, ou não davam o detalhe. O site seguiu a leitura mais
conservadora, e é ela que vale. Os pontos que mudam o que o leitor vê já foram acertados no texto acima
(histórico, links de `dna_fontes`, barra de topo, placas de estado, célula de DNA, edição atrasada, impressão).
Os outros estão aqui.

**Texto e sinais**

- O "→" dos textos fixos (8.2 e 8.3) é o ícone `i-estavel`, nunca o caractere. O leitor de tela ouve uma
  palavra: "para" ("Desde 18/11: energia 1 para 3"), "atira em" (ataque) e "desloca-se para" (vetor). Os
  sinais "‹" e "›" das vizinhas são o ícone `i-dobra`.
- O carimbo traz o texto inteiro da 8.1 em todos os tamanhos e quebra de linha quando não cabe. Os esboços do
  celular abreviam só para caber no papel.
- "HÁ 1 DIA" existe no código e nunca aparece: pela seção 6, até 47 horas o carimbo diz "HÁ N H".
- Texto fixo de etiqueta está escrito em caixa alta. Nome que vem do dado ("Energia") vai como veio, e o CSS põe
  a caixa alta.
- Os rótulos plurais dos bastidores vão em par rótulo e número ("páginas lidas 11").
- O "aviso grave" (5.1 e 5.2) tem o mesmo desenho do aviso comum.
- A etiqueta comum fica em peso 400 e espaço de 0,04em. Peso 600 só na sigla de partido (tabela 5.1).
- A dica flutuante fica presa à largura do componente onde está, sem conta de posição: nunca vaza da tela a
  320 px. O gatilho da dica (EXCEÇÃO, ALÍVIO, PERGUNTA-CHAVE, "anterior", "sem alvo") é um texto que recebe
  foco (`tabindex="0"`); a dica está no texto da página, para o leitor de tela.

**Painel**

- A fita não tem números no eixo: a dica e a tabela gêmea dão o valor. A tabela gêmea tem as colunas Data,
  Nível e Estado, a mais nova primeiro; a data leva à edição.
- Em edição antiga, o nome da fita diz "nesta edição, N"; no Arquivo, "na edição mais recente, N". "Hoje"
  seria falso.
- Lista de principais ou de radar sem item mostra travessão. O validador não deixa isso acontecer numa edição
  publicada.
- A contagem dos botões de categoria é a do radar inteiro, sem os outros filtros. A contagem "4 de 9 itens"
  só aparece com filtro ligado.
- Item pedido pelo endereço e escondido pelo filtro do mesmo endereço (`r4?cat=ia`): o item aparece e os
  filtros saem. Vale igual para a ficha da Régua pedida pelo endereço.
- Alvo que é o player novo da edição: o nome sai sem link (e sem "Ver a ficha na Régua") enquanto ele não está
  em `players.json`.

**Régua, Arquivo e Método**

- A Régua lê o índice como apoio: o saldo em 30 dias e o link para o item de cada vetor. Sem o índice, o saldo
  mostra travessão e o item fica sem link, sem aviso.
- Filtro de vetores por player sem vetor nenhum: "0 de N vetores" e o botão "Limpar filtros".
- Textos que a seção 8 não dá: "Temas da régua" (legenda da tabela de temas), "Régua criada em {data}.",
  "Lista de players atualizada em {data}.", "Catálogo atualizado em {data}.", e os rótulos "Filtrar por tipo",
  "Filtrar por time" e "Filtrar por lado".
- Aviso de arquivo de apoio em falta, na Régua e no Método, só na aba (ou na seção) que usa aquele arquivo.

**Campo que falta**

- O validador não confere os campos só de apresentação (texto de régua, descrição de partido e de time,
  `significado` de nível, explicação de linha de quadro). Sem um deles, o site não quebra: rótulo que fica sem
  valor leva travessão ("prova mínima —"); texto solto, sem rótulo, é omitido. Valor de tipo errado (um
  número no lugar de texto) aparece como texto.
