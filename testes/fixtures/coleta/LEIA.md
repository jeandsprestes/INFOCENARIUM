# Feeds e manchetes de exemplo para os testes do `coleta.py`

Tudo aqui é fictício. Os sites são de `exemplo.invalid`.

| Arquivos | O que são |
|---|---|
| `hostil_*.xml` | XML feito para atacar o leitor (DOCTYPE, ENTITY, em UTF-8, UTF-16 e UTF-7): têm de ser recusados |
| `pagina*.html`, `resposta.json`, `outra_raiz.xml`, `mal_formado.xml`, `vazio.xml`, `so_espacos.xml` | o que um site devolve no lugar do feed |
| `latin1.xml`, `cp1251.xml`, `utf16.xml`, `utf8_com_marca.xml`, `declara_*.xml`, `com_controle.xml` | feeds bons em codificações variadas, ou com a codificação declarada errada |
| `sem_itens.xml` | feed bem formado, sem entrada nenhuma |
| `tres_idiomas.json` | manchetes inventadas, em português, inglês, espanhol, russo, chinês e árabe, com o agrupamento esperado de cada uma |

Os lugares, as pessoas e as empresas das manchetes não existem. Países de verdade aparecem só como nome comum,
para testar que nome muito comum não junta assuntos diferentes. As datas das entradas são de 20/11/2026: os testes
fixam o relógio nesse dia.
