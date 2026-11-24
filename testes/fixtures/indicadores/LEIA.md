# Respostas de exemplo para os testes do `indicadores.py`

Duas pastas, as duas com respostas colhidas das fontes em 23/11/2026, e um `respostas.json` em cada uma, que liga
cada endereço ao seu arquivo (opção `--offline`). Os testes rodam com `--dia 2026-11-23` (alguns com 2026-11-20).
Os números servem para testar a leitura e a conta, e não como registro de preço.

## `amostras/`: uma resposta de cada fonte do catálogo congelado

O `respostas.json` traz todo endereço de `testes/fixtures/dados/indicadores.json`. Cada arquivo é só o corpo da
resposta, sem nada acrescentado no topo.

| Arquivos | O que são |
|---|---|
| `*.fred_csv.csv` | os bytes recebidos do FRED, sem mudança |
| `*.yahoo_chart.json`, `usd_brl.bcb_sgs.json`, `brent.eia_v2.json` | transcrição da resposta; pode haver erro de cópia em algum número. Nos do Yahoo, `meta` traz só parte dos campos reais (sempre `exchangeTimezoneName` e `gmtoffset`), menos no trigo, que é a resposta inteira |
| `fao_ffpi.fao_csv.csv` | transcrição: as 6 primeiras linhas e os últimos 20 meses, com a marca de ordem de bytes do começo, a linha só de vírgulas abaixo do cabeçalho e a fileira de vírgulas no fim de cada linha, como no arquivo real. O fim de linha CRLF não foi conferido (os testes leem também com LF) |
| `*.cnbc_chart.json` | **montados** com os campos que a ferramenta de leitura da web deu, e não o corpo inteiro (ela não copia a resposta literal desse site). A resposta real tem 1 ano de barras (de 247 a 256), cada uma com `open`, `high`, `low`, `close`, `volume`, `tradeTime` e `tradeTimeinMills`; aqui ficaram só as últimas barras (15 no milho, 10 no trigo e na soja, 8 no petróleo, no gás e no ouro), cada uma só com `close` e `tradeTime`, mais a última do milho com todos os campos. `barData.symbol` vem `null` onde o número não foi dado. No gás, o `tradeTime` veio com 8 algarismos e foi escrito com 14, como nos outros |

A fonte da EIA não está no catálogo: a amostra existe só para o leitor `eia_v2`. O índice do dólar não tem amostra
da CNBC: ficou fora do catálogo (a série de lá traz barra de domingo).

## `contratos/`: os contratos com data, para a troca de contrato

`ZCH27` (milho, março de 2027), `ZWH27` (trigo, março de 2027) e `ZSF27` (soja, janeiro de 2027), do Yahoo,
no endereço que o campo `contratos` do catálogo monta. Transcrição de `timestamp` e `close`, lida às 19h de
23/11/2026; o `meta` foi escrito com os campos que a ferramenta da web deu (`symbol`, `shortName`,
`exchangeTimezoneName`, `gmtoffset`) e os que valem para todo contrato de Chicago no Yahoo (`currency` `USX`).

O último ponto (23/11) de cada contrato foi trocado pelo número das 14h45 do mesmo dia, a hora em que as amostras de
`amostras/` foram colhidas: milho 450,0, trigo 593,75 (os dois vistos na hora) e soja 1.227,75 (o mesmo da série
`ZS=F` das 14h45, que já estava nesse contrato). Às 19h o fechamento era outro (449,0, 594,5 e 1.227,5): sem a
troca, o último ponto do contrato não seria do mesmo instante que o da série da amostra.

O que esses números mostram: em 23/11 o Yahoo passou `ZW=F` e `ZC=F` do contrato de dezembro para o de março. Na
série, o milho "subiu" 3,6% no dia (434,5 para 450,0); no contrato de março, 0,3% (448,75 para 450,0). A soja
trocou em 16/11 (1.243,0 no contrato de novembro em 13/11; 1.231,5 no de janeiro).
