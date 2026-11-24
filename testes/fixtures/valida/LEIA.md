# Apoio dos testes do validador

Esta pasta não guarda edições prontas. Guarda o `apoio.py`, a bancada que os arquivos `testa_valida*.py` dividem.

- Ele deriva um rascunho de verdade da edição de exemplo (`testes/fixtures/edicao-exemplo.json`), com a data que o teste pedir.
- Ele "publica" um dia por vez num repositório de mentira, em memória, com as funções de cálculo do `valida.py`: é o caminho que o `publica.py` faz.
- Ele grava esse repositório numa pasta temporária, com `dados/` copiados de `testes/fixtures/dados/`, e chama a ferramenta pela linha de comando.

Assim o histórico de cada teste é montado na hora, e a edição de exemplo continua sendo a única fixture de edição.
Se o esquema mudar, muda o exemplo, e os testes acompanham.
Nada daqui grava dentro do repositório: tudo vai para pasta temporária.
