# Dados congelados para os testes

Esta pasta é uma cópia de `dados/regua.json`, `dados/players.json`, `dados/veiculos.json` e `dados/vetores.json`, tirada em 23/11/2026.
Em 24/11/2026 a cópia recebeu a mesma limpeza de texto do mapa de `dados/` (notas, países, nomes e textos de controle e de lado) e as notas novas de três players. Lado, confiança, fatos, `serve_a`, `alvos`, `sites` e os feeds (endereço, seção, formato e conferido) seguem os mesmos de antes.
O que continua diferente de `dados/`, de propósito: o `veiculos.json` daqui mantém os feeds mortos que `dados/` tirou e o texto de controle da Reuters com o link antigo; o `players.json` mantém a data de 23/11/2026; o `regua.json` mantém a lista de conflito de 23/11/2026 e o sufixo de teste `oficial.exemplo.invalid`, que não existe na internet e serve só à edição de exemplo e aos testes.
O `indicadores.json` desta pasta é a cópia do catálogo de indicadores, congelada à parte (igual ao de `dados/` em 23/11/2026, já com a segunda fonte dos grãos).

Os testes usam esta cópia, e não a pasta `dados/`, porque `dados/` muda: o dono revisa a régua e o mapa de veículos, e a rotina diária acrescenta players e vetores.
Assim, um teste só quebra quando o código muda, e não quando o dado muda.
Cada teste monta uma raiz temporária a partir daqui (opção `--raiz`) e nunca grava nesta pasta.
Depois de uma mudança de formato nos dados, copie de novo os cinco arquivos, mantenha as diferenças de propósito descritas acima e troque as datas.
