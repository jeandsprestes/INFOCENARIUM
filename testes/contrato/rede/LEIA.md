# Testes de contrato · coleta.py e indicadores.py

Esta pasta guarda os testes de contrato das duas ferramentas que usam a rede:

- `coleta.py` (CONTRATO, seção 1): baixa as manchetes dos feeds e grava `coleta.json` e `mesa.txt`;
- `coleta.py --confere` (CONTRATO, seção 1.1): lê a data das páginas abertas e grava `conferencia.json`;
- `indicadores.py` (CONTRATO, seção 2): baixa preços, calcula os gatilhos de preço e grava `indicadores.json`.

"CONTRATO" é o contrato das ferramentas (`docs/CONTRATO-FERRAMENTAS.md`). "ESQUEMA" é o contrato de
dados (`docs/ESQUEMA.md`).

## Por que existem

Foram escritos **só a partir dos contratos, sem ler o código das ferramentas**. Teste escrito por
quem escreveu o código herda os mesmos enganos de leitura. Aqui a ferramenta é uma caixa-preta: o
teste chama pela linha de comando e olha a saída padrão, o código de saída e os arquivos gravados.

Depois, testes e código foram conciliados (23/11/2026): cada teste que falhava foi decidido caso a
caso (o teste, o código ou o contrato estava errado), e onde o contrato não fechava a questão a
leitura virou frase do CONTRATO. Os testes novos dessa conciliação seguem a mesma forma.

Quando um teste daqui falha, há três culpados possíveis: o teste, o código ou o contrato. A
docstring de cada teste traz a cláusula que ele confere (documento, seção e a frase citada), para
quem for decidir.

## Como rodar

Da raiz do repositório:

```
python3 -B testes/contrato/rede/testa_contrato_coleta.py
python3 -B testes/contrato/rede/testa_contrato_confere.py
python3 -B testes/contrato/rede/testa_contrato_indicadores.py
python3 -B testes/roda.py --filtro contrato/rede
```

Um teste só: `python3 -B testes/contrato/rede/testa_contrato_coleta.py Limpeza.test_junta_espacos`.

Os testes não usam a rede (modo `--offline`), não gravam dentro do repositório (tudo vai para uma
pasta temporária, que respeita `$TMPDIR`), fixam o relógio com `INFO_AGORA` (20/11/2026, 21h UTC) e
rodam as ferramentas com `PYTHONDONTWRITEBYTECODE=1`.

## O que há na pasta

| Arquivo | O que é |
|---|---|
| `apoio.py` | a bancada (raiz, pasta de trabalho e respostas, tudo temporário), a chamada da ferramenta, os geradores de feed RSS e Atom, os cinco formatos de resposta das fontes de preço e o leitor de `mesa.txt` |
| `testa_contrato_coleta.py` | 143 testes da coleta |
| `testa_contrato_confere.py` | 39 testes do modo `--confere` |
| `testa_contrato_indicadores.py` | 106 testes dos indicadores |
| `fixtures/raiz/dados/` | uma raiz pequena: `regua.json` (cópia da régua de 23/11/2026), `veiculos.json` (22 veículos fictícios, nos 7 partidos) e `indicadores.json` (7 indicadores, em 5 dos 6 leitores; o `cnbc_chart` e o campo `contratos` são postos pelos próprios testes, na raiz temporária) |
| `fixtures/offline/` | um cenário pronto do modo `--offline`: `respostas.json`, na forma simples e na forma de objeto (`arquivo`, `status`, `tipo`, `para`), e os arquivos: feeds, páginas e séries de preço. Os campos `demora` e `falha` são postos pelos testes que precisam deles |

Tudo nas fixtures é fictício: os veículos, os países (Zarvônia, Quelmar, Tavória, Nordélia), as
manchetes e os preços. Todo endereço é do domínio `exemplo.invalid`.

A variável `INFO_CONTRATO_FERRAMENTAS` troca a pasta onde o `apoio.py` procura as ferramentas. Serve
para provar o encanamento dos testes com uma ferramenta de mentira. No uso normal, não se define.

## O que cada arquivo cobre

**Coleta** (`testa_contrato_coleta.py`)

| Parte do CONTRATO, seção 1 | Classe | Testes |
|---|---|---|
| passo 1: a fila; feeds lidos e feeds pulados | `FilaDeFeeds` | 8 |
| passos 2 e 3: RSS, Atom, `<!DOCTYPE` e `<!ENTITY`, resposta que não é feed | `LeituraDeFeeds` | 9 |
| passo 4: limpeza e cortes em 200 e 300 | `Limpeza` | 11 |
| passo 5: datas em UTC, descartes, janela, `--horas`, `--dia`, relógio | `DatasEJanela` | 15 |
| passo 5: entrada com endereço fora dos `sites` do veículo (`fora_do_site`) | `SiteDoVeiculo` | 3 |
| passo 6: endereço gravado, duplicatas, `--por-feed` | `EnderecoEDuplicatas` | 14 |
| passo 7: manchete suspeita | `Suspeita` | 5 |
| passos 8, 9 e 10: categoria, histórias, pontos, mesma saída | `CategoriaHistoriasPontos` | 11 |
| formato de `coleta.json`; o que fica no disco | `FormatoDaColeta`, `EfeitosNoDisco` | 12 |
| formato de `mesa.txt` | `MesaDoCenarioPronto`, `MesaSinais`, `MesaLimites` | 21 |
| veredito e código de saída | `Vereditos` | 16 |
| limites de rede simulados pelo `--offline` (seção 0), com `demora` e `"falha": "nome"` | `LimitesDeRede` | 18 |

**Modo `--confere`** (`testa_contrato_confere.py`)

| Parte do CONTRATO, seção 1.1 | Classe | Testes |
|---|---|---|
| os dois lugares da data, a ordem, o dia em UTC, página sem data, página que não é HTML | `DataDaPagina` | 12 |
| estados `ok`, `bloqueada` e `erro`; nenhuma página responde | `EstadosDaPagina` | 10 |
| URL que já está em `coleta.json`, `urls.txt`, teto de 30 | `QuaisPaginas` | 8 |
| formato de `conferencia.json`, veredito, o que fica no disco | `FormatoEVeredito` | 9 |

**Indicadores** (`testa_contrato_indicadores.py`)

| Parte do CONTRATO, seção 2 | Classe | Testes |
|---|---|---|
| os 6 leitores, linha ou ponto pulado, leitor desconhecido, `fator`, fuso da bolsa | `Leitores` | 19 |
| passos 1 a 3: escolha da fonte | `EscolhaDaFonte` | 10 |
| passo 4: `valor`, `variacao_pct`, `variacao_7d_pct`, indicador mensal | `Contas` | 9 |
| passos 5 e 6: `defasado`, indicador sem fonte | `DefasadoESemFonte` | 4 |
| passos 7 e 8: gatilhos e confirmação por segunda fonte | `Gatilhos` | 23 |
| formato de `indicadores.json`, `--dia`, o que fica no disco | `Formato` | 12 |
| veredito e código de saída | `Vereditos` | 15 |
| arredondamento, pontos crus, data repetida, segunda fonte velha, empate de janelas, fonte anterior | `DecisoesDaConciliacao` | 6 |
| variação medida no mesmo contrato futuro (`contratos`) | `TrocaDeContrato` | 8 |

Nos testes de indicadores, as séries são escritas à mão e a conta de cada valor esperado está no
comentário ao lado. Só os testes de arredondamento caem de propósito em meio (x,x5): metade vai para
longe do zero, em decimal.

## Testes que podem se declarar pulados

O CONTRATO dá garantias mínimas do agrupamento de manchetes em histórias (título igual fica junto;
sem nome próprio nem número em comum fica separado), e o resto do método é livre. Os testes de
limite usam cenários que essas garantias exercitam. Fica um só que pode se declarar pulado,
`test_no_maximo_2_manchetes_do_mesmo_veiculo`: nenhuma garantia obriga a juntar títulos diferentes
do mesmo veículo, e o motivo está na docstring. Com o método de hoje, ele roda e passa.
Teste pulado não é teste aprovado: quer dizer que aquele limite ficou sem conferência.

## O que estes testes não alcançam

O modo `--offline` não tem rede de verdade. Com o campo `demora`, ele alcança o corte do `--tempo`,
o tempo limite por pedido e o número de pedidos em paralelo. Ficam fora daqui: a nova tentativa, o
cabeçalho `User-Agent`, o proxy e a conferência de certificado. Esses estão em `testes/testa_rede.py`,
contra um servidor local em 127.0.0.1.

## Lista das INTERPRETACAO

Onde o contrato não fechava a questão, o teste escolhia uma leitura e marcava a docstring com a
palavra INTERPRETACAO. Na conciliação, as 16 leituras viraram frase do CONTRATO (seções 0, 1, 1.1 e
2) e a marca saiu: hoje nenhum teste daqui a leva.
