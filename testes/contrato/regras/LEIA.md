# Testes de contrato de `valida.py` e de `publica.py`

Esta pasta guarda testes escritos **só a partir dos contratos**, sem ler o código das ferramentas:

- o ESQUEMA (formato da edição e regras R, H, T, G, M e C);
- o CONTRATO (linha de comando das ferramentas: seções 0, 3, 4, 5 e 6).

Quem escreve a ferramenta e o teste dela lê o contrato do mesmo jeito, e erra igual. Aqui a leitura é outra,
feita à parte. Quando um destes testes falha, há três culpados possíveis: o teste, o código ou o contrato.
A decisão é caso a caso. Por isso cada teste traz, na docstring, o documento, a seção e a frase que confere.

Depois, testes e código foram conciliados (23/11/2026): cada teste que falhava foi decidido caso a caso, e onde o
contrato deixava duas leituras a escolhida virou frase do ESQUEMA ou do CONTRATO. Os testes novos dessa
conciliação seguem a mesma forma.

## Os arquivos

| Arquivo | O que tem |
|---|---|
| `apoio.py` | a raiz temporária, a chamada das ferramentas, o retrato da árvore de arquivos, o git temporário, as edições montadas a partir do exemplo e a pasta de trabalho coerente com um rascunho |
| `testa_contrato_valida.py` | 352 testes: o exemplo passa; um defeito plantado e um caso no limite para cada regra R, H, M, C e G; edição do dia e edição de arquivo; os modos e a saída |
| `testa_contrato_publica.py` | 188 testes: `contexto` (cada linha da tabela, `mapa.txt`, `modelo.txt`); `edicao` (campos calculados, regras T1 a T5, tudo ou nada, `--simula`, `--corta`, dia já publicado, registros); `falha`; `refaz`; o formato do `.md` e do `feed.xml` |
| `modelo_esperado.txt` | cópia, letra por letra, do bloco de texto do `modelo.txt` que está na seção 4.1 do CONTRATO. Se o contrato mudar, copie o bloco de novo |

## Como rodar

Da raiz do repositório:

```
python3 -B testes/contrato/regras/testa_contrato_valida.py
python3 -B testes/contrato/regras/testa_contrato_publica.py
python3 -B testes/roda.py --filtro contrato/regras
```

Um teste só: `python3 -B testes/contrato/regras/testa_contrato_valida.py Identidade.test_r01_acusa_id_repetido`.

Os testes não usam rede e não gravam dentro do repositório: cada um trabalha numa pasta temporária (que
respeita `$TMPDIR`), com os dados da cópia congelada (`testes/fixtures/dados/`), o relógio fixo em `INFO_AGORA`
e `PYTHONDONTWRITEBYTECODE=1`. As ferramentas são chamadas pela linha de comando, como a rotina chama.
Sem o arquivo da ferramenta em `ferramentas/`, o teste falha com a mensagem "não existe ferramentas/…".

## Como ler um teste

- Nome com `acusa`: um defeito é plantado. Espera-se uma linha `ERRO` com o código da regra, código de saída 1 e
  a última linha começando com `FALHA`.
- Nome com `aceita`: o caso está no limite que a regra permite. Espera-se que a regra não seja acusada e que a
  chamada inteira passe (código 0).
- Nome com `avisa`: espera-se uma linha `AVISO`, sem mudar o código de saída.
- O teste confere o que o contrato fixa: o código da regra, o código de saída, a primeira palavra da última
  linha, o caminho do campo quando o contrato o dá, e os arquivos gravados. Não confere o texto das mensagens.
- Onde duas regras cobrem o mesmo defeito, o ESQUEMA, seção 10, "Qual código sai", diz o código, e o teste o
  exige. Onde o contrato manda recusar e não dá código (os defeitos de estrutura do `--dados`), o teste só exige
  que haja erro (`acusa_algo`).

## As edições dos testes

Tudo sai de `testes/fixtures/edicao-exemplo.json`, sem texto novo:

- `apoio.exemplo()`: o exemplo, como está. É a base dos defeitos plantados na edição sozinha.
- `apoio.monta_edicao(dia, rica=True)`: o exemplo levado a outro dia, sem a marca de exemplo, com os endereços
  no site de cada veículo (regra T4). É a "edição do dia" dos testes do `publica.py`.
- `apoio.monta_edicao(dia)`: a mesma, sem player novo, sem vetor e sem gatilho. Serve de edição de arquivo.
- `apoio.rascunho_de(edicao)`: a edição só com os campos de origem agente.
- `apoio.Trabalho(pasta, edicao)`: a pasta de trabalho em que toda fonte foi "vista" pela máquina.

O nível, a tendência e o `desde` que cada teste espera foram tirados à mão das regras R13 e R14, para o
histórico que o próprio teste monta.

## Leituras que valem para todos os testes

Onde o contrato não diz, ou deixa duas leituras, a escolha está aqui ou na docstring do teste.

- As opções comuns (`--raiz`, `--trabalho`, `--dia`, `--json`) do `publica.py` vão **depois** do subcomando, como
  as outras opções na sinopse da seção 4 do CONTRATO. A outra leitura: antes do subcomando.
- A ferramenta é chamada com a pasta atual igual à raiz temporária ("a partir da raiz do repositório").
- Item sem conflito de interesse: o ESQUEMA não diz se o campo `conflito_de_interesse` some ou sai `false`. Ao
  comparar a edição publicada com a esperada, as duas formas valem o mesmo.
- O escape dos sinais de Markdown é a barra invertida antes do sinal (CONTRATO, seção 4.5).
- Para `dados/players.json`, `atualizado_em` é comparado com o dia da edição só no teste em que o dia da edição
  e o dia do relógio são o mesmo.

## Lista das INTERPRETACAO

Onde o contrato deixava duas leituras, a docstring do teste começava com INTERPRETACAO e dizia a leitura
escolhida. Na conciliação, as 35 leituras (29 do `valida.py` e 6 do `publica.py`) viraram frase do ESQUEMA ou do
CONTRATO, e a marca saiu de todas. Hoje nenhum teste daqui a leva: a docstring cita a frase.

## Pontos em que o contrato não fecha

Fica **fora** dos testes, por falta de regra clara: errata que aponta para uma edição de falha. O resto do que
estava aqui (ordem das entradas do feed, `updated` com a edição de exemplo, a linha "Desde" com mais de um
domínio, "sem dado de preço de:", `edicoes_sem_gatilho` em nível 1, os limites de 7, 14 e 30 dias, `--corta` com
id que não existe, `--simula` junto com `--corta` e o "gatilho novo" da regra T3) virou frase do contrato e tem
teste.
