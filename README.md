# INFOCENARIUM

INFOCENARIUM é um monitor diário de geopolítica e de IA (inteligência artificial), em português do Brasil. Todo dia,
pouco depois das 18h de Brasília, sai uma **edição** com as notícias do dia lidas por uma régua fixa: quem são os
grandes jogadores do mundo, de que lado está cada veículo que deu a notícia, quem ganha e quem perde na prática,
e o que isso muda para quem se prepara para crises (energia, alimentos, câmbio, cadeias de suprimento e risco de
conflito).

O site é uma página só, aberta, sem cadastro, sem rastreador e sem nada de fora: `index.html` e `assets/`, que
leem os arquivos JSON deste repositório. É publicado pelo GitHub Pages a partir da branch `main`.

## O que o INFOCENARIUM é, e o que não é

- **É** uma leitura editorial. Cada notícia é tratada como um ataque lançado por um veículo: o INFOCENARIUM diz o fato
  que os dois lados confirmam, separa o enquadramento, e mostra a quem o fato serve.
- **É** um nível de alerta de 1 (ROTINA) a 5 (EMERGÊNCIA) por domínio, que só muda com motivo concreto e citado.
- **Não é** agência de notícias: não apura no local, só lê o que foi publicado e cita a fonte de cada fato.
- **Não é** conselho. O INFOCENARIUM nunca manda comprar, vender, estocar, sacar ou tomar remédio. Diz o que tende a
  encarecer, faltar ou atrasar, e por qual caminho.
- **Não é** neutro no método: a régua e o mapa de veículos são escolhas (veja abaixo). O método está todo
  escrito e o site o mostra na página "Método".

## Aviso de conflito de interesse

As edições são escritas por um modelo de IA da Anthropic (Claude). A Anthropic e outras empresas de IA são
players da própria régua: aparecem nas notícias e no placar. Por isso, toda notícia de IA, ou que envolva a
Anthropic ou um concorrente, leva a marca de conflito de interesse e fica com a confiança no máximo em "média";
quando a empresa é parte, o item precisa de fontes de dois partidos, e o canal dela nunca é a única fonte
(`ROTINA.md`, defesa D6; `docs/ESQUEMA.md`, regra R19). Leia com isso em mente.

## A régua e o mapa de veículos são classificação editorial

- `dados/regua.json` e `dados/players.json` trazem os 30 players globais (governos, instituições, empresas,
  bilionários), o partido de cada um (quem costuma votar junto), as posições em 5 temas e os níveis de alerta.
  Ninguém muda de partido: movimento vira um "vetor de mudança", registrado em `dados/vetores.json`, que só
  cresce.
- `dados/veiculos.json` diz, para cada um dos 146 veículos lidos, de que lado ele joga, a quem serve, quem ataca
  e quanto se pode confiar nele para o fato cru. Lado e confiabilidade são coisas separadas: um veículo pode
  ser ótimo nos fatos e ainda assim servir a um lado pelo que escolhe cobrir.
- Isso é **classificação editorial, não fato**. O mapa foi montado por pesquisa e ainda está **em rascunho**:
  enquanto o campo `revisado_em` estiver `null`, o site avisa "mapa em rascunho". A revisão é do dono do
  repositório. A rotina diária não altera a régua, o mapa nem o catálogo de indicadores.

## Como sai a edição de cada dia

1. **A rotina na nuvem.** Uma tarefa agendada do Claude Code roda às 18:07 de Brasília, numa máquina limpa, com
   este repositório clonado. O agente lê e executa o `ROTINA.md`: prepara o dia, baixa as manchetes dos feeds
   e os preços (`ferramentas/coleta.py` e `ferramentas/indicadores.py`), escolhe as 3 principais e o radar, lê
   as páginas, escreve um rascunho e chama o `ferramentas/publica.py`, que calcula o que é conta, valida e grava
   a edição (`edicoes/AAAA-MM-DD.json`, o `.md`, o índice e o `feed.xml`). Não há memória entre um dia e outro:
   o que precisa persistir está nos arquivos do repositório. Nenhuma chave de API é usada.
2. **A branch de edição.** A rotina faz um commit e empurra na branch `claude/edicao-AAAA-MM-DD`. Ela não
   empurra na `main`, a não ser na reserva (passo 5).
3. **O workflow de publicação** (`.github/workflows/publica-edicao.yml`). O push toca a campainha
   (`sinal-edicao.yml`, que não tem permissão nenhuma e não lê nada), e o GitHub dispara o `publica-edicao`
   com o arquivo **da `main`**. Ele confere o que a branch muda: só pode criar ou alterar
   `edicoes/AAAA-MM-DD.json`, `edicoes/AAAA-MM-DD.md`, `edicoes/indice.json`, `feed.xml`,
   `dados/players.json` e `dados/vetores.json` (os dois últimos só crescendo), com limites de tamanho e de
   número de arquivos. Uma branch mexe em edições de no máximo 3 dias, e nenhuma pode ser de dia depois de
   hoje em Brasília (o Painel abre a edição de data mais alta). Copia esses arquivos para uma cópia da `main`, roda o validador **da `main`**
   (`python3 ferramentas/valida.py --tudo --base ANTES --dia DIA`) e, se passar, faz um commit do robô na
   `main` e pede ao Pages que publique. Não há merge: os commits da branch não entram no histórico.
4. **O workflow de recusa.** Se a branch muda o que não pode, ou se o validador recusa, a edição não entra. O
   commit fica guardado na branch `recusada/edicao-AAAA-MM-DD-<SHA>` para o dono ver, e a execução fica
   vermelha. A rotina vê a recusa e não tenta de novo.
5. **Varredura e reserva.** O `publica-edicao` também roda de hora em hora (minuto 13), para o que a campainha
   perdeu. Se em uns 5 minutos a edição não chegou à `main` nem foi recusada, a rotina usa a reserva: puxa a
   `main`, valida de novo e empurra direto nela.
6. **Os outros dois workflows.** O `valida.yml` roda o validador nos pushes do dono e da reserva na `main` e em
   pull request, e só avisa. O commit diário do robô não o dispara (push feito com o token do próprio Actions não
   dispara workflow): o `publica-edicao` já valida antes de empurrar. Por isso a aba Actions não mostra uma
   execução do `valida` a cada edição. O `vigia.yml` (opcional, para ligar depois que a rotina estiver no ar)
   roda às 22h43 de Brasília e fica vermelho se não há edição do dia, se ela é uma edição de falha ou se o
   arquivo dela não é um JSON legível. O GitHub pode atrasar uma execução agendada em horas; por isso, até as 6h
   da manhã, o vigia ainda confere o dia anterior.

### Por que os workflows são assim

- **Nunca rodam o arquivo da branch empurrada.** Num gatilho de push, o GitHub usaria o workflow da branch, e
  quem empurra escolheria as regras. Por isso a campainha não tem permissão nenhuma, e quem trabalha é o
  `publica-edicao`, disparado por `workflow_run`, de hora em hora ou pelo botão, sempre com o arquivo da `main`
  (há uma trava para o botão em outra branch).
- **Nada da branch é executado.** A conferência usa só git e um script Python isolado, escrito dentro do
  próprio workflow. O validador é o da `main`, e a conferência garante que `ferramentas/` não mudou.
- **O token só existe nos passos que empurram e publicam.** O validador roda sem credencial, sem pasta de
  trabalho e com 120 segundos de limite. Nenhum dado do evento entra num comando, e nenhuma action de
  terceiros é usada: só git, python3 e gh, que já vêm no runner.
- **O `feed.xml` só pode ter elementos do Atom**, porque é o único arquivo que o navegador abre como XML.
- Os detalhes estão nos comentários de cada YAML e em `docs/CONTRATO-FERRAMENTAS.md`, seções 3 e 5.

## Estrutura do repositório

```
index.html                 a página única: Painel, Arquivo, Régua e Método
assets/app.js              a lógica do site (JavaScript puro, sem biblioteca e sem etapa de build)
assets/estilo.css          o visual
dados/regua.json           temas, partidos, times, níveis de alerta e domínios
dados/players.json         os players (partido fixo, posições); a rotina só acrescenta
dados/veiculos.json        o mapa de veículos por lado, com os feeds
dados/vetores.json         o registro dos vetores de mudança; só cresce
dados/indicadores.json     o catálogo dos indicadores de preço e das fontes de cada um
edicoes/indice.json        a lista das edições, mais nova primeiro
edicoes/AAAA-MM-DD.json    a edição do dia (a fonte da verdade)
edicoes/AAAA-MM-DD.md      a mesma edição em texto, gerada a partir do JSON
feed.xml                   feed Atom, gerado
ferramentas/coleta.py      baixa as manchetes dos feeds e confere a data das páginas (rede)
ferramentas/indicadores.py baixa os preços e calcula os gatilhos de preço (rede)
ferramentas/valida.py      valida a edição e os dados (sem rede; nunca grava)
ferramentas/publica.py     contexto do dia, publicação da edição, índice, .md e feed (sem rede)
ferramentas/comum.py       o que as quatro ferramentas dividem
ferramentas/rede.py        o código de rede da coleta e dos indicadores
testes/                    os testes, as fixtures e a cópia congelada dos dados
docs/ESQUEMA.md            o formato dos dados e as regras que o validador confere
docs/CONTRATO-FERRAMENTAS.md  a linha de comando das quatro ferramentas
docs/ESPEC-SITE.md         o desenho do site
ROTINA.md                  o manual que o agente diário lê e executa
.github/workflows/         publica-edicao.yml, sinal-edicao.yml, valida.yml e vigia.yml
.nojekyll                  o Pages serve os arquivos como estão
```

As ferramentas pedem Python 3.10 ou mais novo e usam só a biblioteca padrão. Rodam a partir da raiz do
repositório: `python3 ferramentas/valida.py` (sem opção, confere tudo). A pasta de trabalho da rotina fica
fora do repositório (`/tmp/info`, ou outra com `--trabalho`).

## Como rodar os testes

Da raiz do repositório:

```
python3 -B testes/roda.py                    # tudo: testes das ferramentas, de contrato e do site
python3 -B testes/roda.py --so python        # só os de Python
python3 -B testes/roda.py --so site          # só os do site (use este fora do Node 18)
python3 -B testes/roda.py --filtro valida    # só os arquivos cujo caminho contém o texto
python3 -B testes/roda.py --pula contrato    # deixa de fora os que contêm o texto
python3 -B testes/testa_valida.py            # um arquivo sozinho
```

Os testes não usam a rede, não gravam dentro do repositório (usam a pasta temporária do sistema, que respeita
`$TMPDIR`), fixam o relógio com a variável `INFO_AGORA` e rodam contra a cópia congelada dos dados, em
`testes/fixtures/dados/`: revisar `dados/` não quebra teste. Os do site precisam de Node 18 ou mais novo e
usam um DOM falso próprio, sem biblioteca. No Node 18, `node --test testes/site/` também roda todos; em outra
versão, use `--so site`, que roda arquivo por arquivo.

Os testes de `testes/contrato/` foram escritos só a partir dos contratos de `docs/`, sem ler o código; depois,
testes e código foram conciliados caso a caso. Cada pasta tem um `LEIA.md`.

## Avisos

- Os nomes de pessoas e de empresas que aparecem na régua, no mapa e nas edições são de figuras públicas,
  citadas pelo cargo ou pelo papel. Edição de exemplo (`testes/fixtures/edicao-exemplo.json`) usa países e
  dados fictícios.
- Os preços vêm de fontes públicas gratuitas e podem atrasar ou faltar. Quando faltam, a edição diz.
