'use strict';

/* A vista Arquivo (#/arquivo), montada com os dados congelados e com um
 * índice de teste de 35 dias, de 16/10 a 19/11/2026. O índice tem edição
 * falha (12/11), edição de exemplo (05/11), edição corrigida (10/11), edição
 * reduzida (28/10) e um dia sem edição (08/11). O histórico são os 30 dias
 * que terminam em 19/11: começa em 21/10. */

const test = require('node:test');
const assert = require('node:assert/strict');
const {
  abre, arquivos, arquivosDe35Dias, edicaoReal, edicaoDeExemplo, entradaSolta, indiceDe, entradaDoIndice,
  textoDe, aVista, DIA, Evento
} = require('./apoio.js');

const textos = (lista) => lista.map(textoDe);
const abreArquivo = (mudancas, hash) => abre({ hash: hash || '#/arquivo', arquivos: arquivosDe35Dias(mudancas) });
const figura = (m, chave) => m.um('.figura--' + chave);

/* As linhas de uma tabela, cada uma como "célula | célula". */
function linhasDe(tabela) {
  return tabela.querySelectorAll('tbody tr').map((tr) => textos(tr.children).join(' | '));
}

test('Arquivo: título, navegação e as duas seções', async () => {
  const m = await abreArquivo();
  assert.equal(textoDe(m.um('h1')), 'Arquivo');
  assert.equal(m.todos('h1').length, 1, 'um h1 por vista');
  assert.equal(m.um('h1').classList.contains('so-leitor'), false, 'título visível');
  assert.equal(m.documento.title, 'INFOCENARIUM · Arquivo');
  assert.equal(m.um('nav a[aria-current="page"]').textContent, 'Arquivo');
  assert.equal(m.um('#vista').getAttribute('class'), 'vista vista--arquivo');
  assert.equal(m.um('#vista').hasAttribute('aria-busy'), false);
  assert.deepEqual(textos(m.todos('main h2')), ['01 HISTÓRICO', '02 EDIÇÕES']);
  assert.equal(textoDe(m.um('#s-historico .secao__intro')), 'ÚLTIMOS 30 DIAS · Edições de exemplo ficam fora do histórico.');
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
  assert.equal(m.todos('#rodape-edicao a').length, 0, 'os links de texto e JSON são da edição, não do Arquivo');
  /* o que a vista lê: o índice, a régua e o catálogo; nenhuma edição */
  assert.deepEqual(m.rede.pedidos.map((p) => p.caminho).sort(), ['dados/indicadores.json', 'dados/regua.json', 'edicoes/indice.json']);
});

test('Arquivo 01: cinco figuras, cada uma com título h3, role="img", nome que resume e a tabela gêmea em "Ver tabela"', async () => {
  const m = await abreArquivo();
  const figuras = m.todos('#s-historico .figura');
  assert.deepEqual(textos(figuras.map((f) => f.querySelector('h3'))), ['Alerta geral', 'Domínios', 'Saldo dos partidos', 'Atos por tema', 'Indicadores']);
  assert.deepEqual(figuras.map((f) => f.getAttribute('class')),
    ['figura figura--alerta', 'figura figura--dominios', 'figura figura--partidos', 'figura figura--atos', 'figura figura--indicadores']);
  for (const f of figuras) {
    const titulo = textoDe(f.querySelector('h3'));
    const imagens = f.querySelectorAll('[role="img"]');
    assert.ok(imagens.length >= 1, titulo + ': tem figura');
    imagens.forEach((img) => {
      assert.ok(img.getAttribute('aria-label').length > 20, titulo + ': a figura tem nome');
      assert.match(img.getAttribute('aria-label'), /nos últimos 30 dias/, titulo);
      /* dentro de uma figura nada recebe foco pelo teclado: quem navega usa a tabela */
      assert.equal(img.querySelectorAll('button, input, select').length, 0, titulo);
      img.querySelectorAll('a').forEach((a) => assert.equal(a.getAttribute('tabindex'), '-1', titulo));
    });
    const botao = f.querySelector('.figura__topo button');
    const tabela = f.querySelector('table');
    assert.equal(textoDe(botao), 'Ver tabela : ' + titulo, 'o nome do botão diz de que figura é a tabela');
    assert.equal(botao.getAttribute('aria-expanded'), 'false');
    assert.equal(m.documento.getElementById(botao.getAttribute('aria-controls')).contains(tabela), true);
    assert.equal(aVista(tabela), false, titulo + ': a tabela começa fechada');
    await m.clica(botao);
    assert.equal(textoDe(botao), 'Esconder tabela : ' + titulo);
    assert.equal(aVista(tabela), true);
    assert.equal(textoDe(tabela.querySelector('caption')), titulo);
    assert.equal(tabela.getAttribute('role'), 'table');
    tabela.querySelectorAll('thead th').forEach((th) => assert.equal(th.getAttribute('scope'), 'col'));
    tabela.querySelectorAll('tbody tr').forEach((tr) => assert.equal(tr.children[0].getAttribute('scope'), 'row'));
    assert.ok(tabela.querySelectorAll('tbody tr').length >= 4, titulo + ': a tabela tem linhas');
  }
});

test('Arquivo 01, Alerta geral: a fita de 30 dias termina na edição mais nova, sem a de exemplo e sem coluna clareada', async () => {
  const m = await abreArquivo();
  const fita = figura(m, 'alerta').querySelector('.fita');
  assert.equal(fita.getAttribute('aria-label'), 'Alerta nos últimos 30 dias: de 1 a 4; na edição mais recente, 3',
    'o nível 5 era da edição de exemplo; a falha não entra no menor e no maior');
  const dias = fita.querySelectorAll('.fita__dia');
  assert.equal(dias.length, 30);
  assert.equal(fita.querySelectorAll('.fita__fio').length, 5);
  assert.equal(textoDe(fita.querySelector('.fita__datas')), '21/10 19/11');
  const coluna = (data) => {
    const dia = dias.find((d) => d.getAttribute('href') === '#/edicao/' + data);
    return dia ? dia.querySelector('.fita__coluna').getAttribute('class') : null;
  };
  assert.equal(dias[0].getAttribute('href'), '#/edicao/2026-10-21', 'o primeiro espaço é 21/10: 16 a 20/10 ficam fora');
  assert.equal(dias[29].getAttribute('href'), '#/edicao/2026-11-19');
  assert.equal(coluna('2026-10-21'), 'fita__coluna fita__coluna--n1');
  assert.equal(coluna('2026-10-28'), 'fita__coluna fita__coluna--n2');
  assert.equal(coluna('2026-11-09'), 'fita__coluna fita__coluna--n4');
  assert.equal(coluna('2026-11-12'), 'fita__coluna fita__coluna--falha', 'edição falha: traço na base');
  assert.equal(coluna('2026-11-19'), 'fita__coluna fita__coluna--n3', 'no Arquivo não há edição em tela: nenhuma coluna clareada');
  assert.equal(fita.querySelectorAll('.fita__coluna--atual').length, 0);
  /* 05/11 é a de exemplo e 08/11 não teve edição: espaço vazio, sem link */
  assert.equal(coluna('2026-11-05'), null);
  assert.equal(coluna('2026-11-08'), null);
  assert.equal(dias[15].localName, 'span', '05/11: espaço vazio');
  assert.equal(dias[18].localName, 'span', '08/11: espaço vazio');
  assert.equal(fita.querySelectorAll('.fita__coluna').length, 28);
  assert.equal(fita.querySelectorAll('[class*="alerta"], [class*="nivel-"]').length, 0, 'a fita não leva cor de nível');
  /* tabela gêmea: mais nova primeiro, a data leva à edição */
  const linhas = linhasDe(figura(m, 'alerta').querySelector('table'));
  assert.equal(linhas.length, 28);
  assert.deepEqual(linhas.slice(0, 3), ['19/11/2026 | 3 TENSÃO | completa', '18/11/2026 | 3 TENSÃO | completa', '17/11/2026 | 2 ATENÇÃO | completa']);
  assert.ok(linhas.includes('12/11/2026 | 2 ATENÇÃO | sem edição'));
  assert.ok(linhas.includes('28/10/2026 | 2 ATENÇÃO | reduzida'));
  assert.equal(linhas[27], '21/10/2026 | 1 ROTINA | completa');
  assert.equal(linhas.some((l) => l.startsWith('05/11/2026')), false, 'a de exemplo fica fora');
  assert.equal(figura(m, 'alerta').querySelector('tbody a').getAttribute('href'), '#/edicao/2026-11-19');
});

test('Arquivo 01, Alerta geral: o ponteiro abre a dica do dia, Esc fecha, e o clique leva à edição', async () => {
  const m = await abreArquivo();
  const fita = figura(m, 'alerta').querySelector('.fita');
  const dica = fita.querySelector('.dica');
  const dia = fita.querySelectorAll('a.fita__dia').find((a) => a.getAttribute('href') === '#/edicao/2026-11-09');
  dia.dispatchEvent(new Evento('mouseenter', { bubbles: false }));
  assert.equal(dica.classList.contains('dica--aberta'), true);
  assert.equal(textoDe(dica), 'nível 4 CRISE 09/11');
  m.tecla('Escape');
  assert.equal(dica.classList.contains('dica--aberta'), false);
  await m.clica(fita.querySelectorAll('a.fita__dia').find((a) => a.getAttribute('href') === '#/edicao/2026-11-18'));
  assert.equal(textoDe(m.um('h1')), 'Edição de 18/11/2026');
});

test('Arquivo 01, Domínios: cinco fitas pequenas, com o nome e o nível mais recente ao lado', async () => {
  const m = await abreArquivo();
  const linhas = figura(m, 'dominios').querySelectorAll('.fitinha');
  assert.deepEqual(textos(linhas.map((l) => l.querySelector('.fitinha__nome'))),
    ['Energia', 'Alimentos', 'Câmbio', 'Cadeias de suprimento', 'Risco de conflito'], 'na ordem da régua');
  assert.deepEqual(linhas.map((l) => l.querySelector('.fita').getAttribute('aria-label')), [
    'Energia nos últimos 30 dias: de 1 a 4; na edição mais recente, 3',
    'Alimentos nos últimos 30 dias: de 1 a 1; na edição mais recente, 1',
    'Câmbio nos últimos 30 dias: de 1 a 2; na edição mais recente, 2',
    'Cadeias de suprimento nos últimos 30 dias: de 1 a 2; na edição mais recente, 2',
    'Risco de conflito nos últimos 30 dias: de 1 a 4; na edição mais recente, 3'
  ]);
  assert.deepEqual(textos(linhas.map((l) => l.querySelector('.selo .so-leitor'))),
    ['Nível 3 de 5, tensão', 'Nível 1 de 5, rotina', 'Nível 2 de 5, atenção', 'Nível 2 de 5, atenção', 'Nível 3 de 5, tensão']);
  assert.deepEqual(linhas.map((l) => l.querySelector('.selo use').getAttribute('href')),
    ['#i-nivel-3', '#i-nivel-1', '#i-nivel-2', '#i-nivel-2', '#i-nivel-3']);
  linhas.forEach((linha) => {
    const fita = linha.querySelector('.fita');
    assert.ok(fita.classList.contains('fita--pequena'));
    assert.equal(fita.getAttribute('role'), 'img');
    assert.equal(fita.querySelectorAll('.fita__dia').length, 30);
    /* sem dica, sem clique e sem grade */
    assert.equal(fita.querySelectorAll('a, .dica, .fita__fio, .fita__datas').length, 0);
    assert.equal(fita.querySelectorAll('.fita__coluna').length, 28);
    assert.equal(fita.querySelectorAll('.fita__coluna--falha').length, 1);
  });
  /* energia em 09/11 estava no nível 4; alimentos, sempre no 1 */
  const classes = (i) => linhas[i].querySelectorAll('.fita__dia')[19].querySelector('.fita__coluna').getAttribute('class');
  assert.equal(classes(0), 'fita__coluna fita__coluna--n4');
  assert.equal(classes(1), 'fita__coluna fita__coluna--n1');
  assert.equal(classes(2), 'fita__coluna fita__coluna--n2');
  /* tabela gêmea: uma coluna por domínio, com a sigla em abbr e o nome da régua */
  const tabela = figura(m, 'dominios').querySelector('table');
  assert.deepEqual(textos(tabela.querySelectorAll('thead th')), ['Data', 'ENE', 'ALI', 'CAM', 'SUP', 'CON']);
  assert.deepEqual(tabela.querySelectorAll('thead abbr').map((a) => a.getAttribute('title')),
    ['Energia', 'Alimentos', 'Câmbio', 'Cadeias de suprimento', 'Risco de conflito']);
  const doTabela = linhasDe(tabela);
  assert.equal(doTabela.length, 28);
  assert.equal(doTabela[0], '19/11/2026 | 3 | 1 | 2 | 2 | 3');
  assert.ok(doTabela.includes('09/11/2026 | 4 | 1 | 2 | 1 | 4'));
  /* na tela estreita, o rótulo de cada célula é o nome do domínio por extenso */
  assert.equal(tabela.querySelector('tbody td').getAttribute('data-rotulo'), 'Energia');
});

test('Arquivo 01, Saldo dos partidos: a soma dos saldos dos 30 dias, em barra a partir do zero, na mesma tinta', async () => {
  const m = await abreArquivo();
  const desenho = figura(m, 'partidos').querySelector('.saldos');
  assert.equal(desenho.getAttribute('role'), 'img');
  assert.equal(desenho.getAttribute('aria-label'),
    'Saldo dos partidos nos últimos 30 dias: o maior é mais 11, de Partido da Ordem Global; o menor é menos 6, de Centro Atlântico');
  const linhas = desenho.querySelectorAll('.placar__topo');
  /* 16/10 (+100) está fora dos 30 dias e 05/11 (+50) é de exemplo: nenhum dos dois entra */
  assert.deepEqual(textos(linhas), ['OG +11', 'CA −6', 'BT −4', 'SO −1', 'ER +3', 'CE −2', 'IN +4'], 'na ordem da régua');
  const barra = (l) => l.querySelector('.placar__barra');
  assert.deepEqual(linhas.map((l) => (barra(l) ? barra(l).getAttribute('class').replace('placar__barra ', '') + ' ' + barra(l).style.width : '')), [
    'placar__barra--ganha 72px', 'placar__barra--perde 39px', 'placar__barra--perde 26px', 'placar__barra--perde 7px',
    'placar__barra--ganha 20px', 'placar__barra--perde 13px', 'placar__barra--ganha 26px'
  ], '72 px valem o maior saldo absoluto');
  assert.equal(desenho.querySelectorAll('a').length, 0, 'dentro da figura a sigla não é link');
  assert.equal(desenho.querySelector('abbr').getAttribute('title'), 'Partido da Ordem Global');
  const tabela = figura(m, 'partidos').querySelector('table');
  assert.deepEqual(textos(tabela.querySelectorAll('thead th')), ['Partido', 'Saldo']);
  assert.deepEqual(linhasDe(tabela), ['OG Partido da Ordem Global | +11', 'CA Centro Atlântico | −6', 'BT Bancada do Talento | −4',
    'SO Soberanistas | −1', 'ER Eixo Revisionista | +3', 'CE Centrão | −2', 'IN Independentes | +4']);
  assert.equal(tabela.querySelector('tbody a').getAttribute('href'), '#/regua/partidos/ordem_global', 'na tabela a sigla leva à ficha');
});

test('Arquivo 01, Saldo dos partidos: com saldos pequenos, a escala tem piso de 3 (1 ponto vale 24 px, e não 72)', async () => {
  const m = await abre({
    hash: '#/arquivo',
    arquivos: arquivos({
      edicoes: [],
      entradas: [entradaSolta('2026-11-18', { saldos: { ordem_global: 1 } }), entradaSolta(DIA, { saldos: { soberanistas: -1 } })]
    })
  });
  const linhas = figura(m, 'partidos').querySelectorAll('.placar__topo');
  const barras = linhas.map((l) => l.querySelector('.placar__barra')).filter(Boolean);
  assert.deepEqual(barras.map((b) => b.getAttribute('class').replace('placar__barra ', '') + ' ' + b.style.width),
    ['placar__barra--ganha 24px', 'placar__barra--perde 24px']);
  assert.deepEqual(textos(linhas), ['OG +1', 'CA 0', 'BT 0', 'SO −1', 'ER 0', 'CE 0', 'IN 0'], 'saldo zero: sem barra e sem sinal');
});

test('Arquivo 01, Atos por tema: duas barras da mesma tinta por tema, com o texto do polo e sem as palavras dos polos', async () => {
  const m = await abreArquivo();
  const f = figura(m, 'atos');
  assert.equal(textoDe(f.querySelector('.secao__intro')),
    'Quantas notícias trouxeram um ato (lei, decreto, decisão, compra) que empurra cada tema, e para que lado.');
  const desenho = f.querySelector('.atos');
  assert.equal(desenho.getAttribute('role'), 'img');
  assert.equal(desenho.getAttribute('aria-label'), 'Atos por tema nos últimos 30 dias: 10 atos em 2 temas');
  const linhas = desenho.querySelectorAll('.ato');
  /* só os temas que aparecem em "eixos", na ordem da régua; o de 05/11 (exemplo) e o de 16/10 ficam fora */
  assert.deepEqual(textos(linhas.map((l) => l.querySelector('.ato__tema'))), ['IA (depois)', 'Mudanças climáticas']);
  assert.deepEqual(textos(linhas[0].querySelectorAll('.ato__conta')), ['4', '2']);
  assert.deepEqual(textos(linhas[1].querySelectorAll('.ato__conta')), ['1', '3']);
  assert.deepEqual(linhas.map((l) => l.querySelectorAll('.placar__barra').map((b) => b.getAttribute('class') + ' ' + b.style.width)), [
    ['placar__barra ato__barra--esquerda 72px', 'placar__barra ato__barra--direita 36px'],
    ['placar__barra ato__barra--esquerda 18px', 'placar__barra ato__barra--direita 54px']
  ], 'escala comum: 72 px valem a maior contagem');
  assert.deepEqual(textos(linhas[1].querySelectorAll('.ato__polo')), ['cortar emissões, frear os fósseis', 'fósseis livres, minimizar o problema']);
  /* nem cor de polo, nem as palavras "azul" e "vermelho" */
  assert.equal(/azul|vermelho/i.test(textoDe(f)), false);
  assert.equal(f.querySelectorAll('[class*="dna"]').length, 0);
  f.querySelectorAll('*').forEach((el) => assert.equal(/azul|vermelho/.test(el.getAttribute('class') || ''), false));
  const tabela = f.querySelector('table');
  assert.deepEqual(textos(tabela.querySelectorAll('thead th')), ['Tema', 'Polo', 'Atos']);
  assert.deepEqual(linhasDe(tabela), [
    'IA (depois) | regular, pôr limites | 4', 'IA (depois) | liberar, acelerar, desregular | 2',
    'Mudanças climáticas | cortar emissões, frear os fósseis | 1', 'Mudanças climáticas | fósseis livres, minimizar o problema | 3'
  ]);
});

test('Arquivo 01, Atos por tema: sem ato no período, a frase; a escala tem piso de 3', async () => {
  let m = await abreArquivo((t) => { t['edicoes/indice.json'].edicoes.forEach((e) => { e.eixos = {}; }); });
  assert.equal(textoDe(figura(m, 'atos').querySelector('.vazio')), 'Nenhum ato registrado em 30 dias.');
  assert.equal(figura(m, 'atos').querySelectorAll('[role="img"], table, button').length, 0);
  assert.equal(m.todos('.figura').length, 5, 'a figura não some');

  m = await abreArquivo((t) => {
    t['edicoes/indice.json'].edicoes.forEach((e) => { e.eixos = {}; });
    t['edicoes/indice.json'].edicoes[0].eixos = { imigracao: { azul: 0, vermelho: 1 }, tema_fantasma: { azul: 1, vermelho: 0 } };
  });
  const linhas = figura(m, 'atos').querySelectorAll('.ato');
  assert.deepEqual(textos(linhas.map((l) => l.querySelector('.ato__tema'))), ['Imigração', 'tema_fantasma'], 'tema fora da régua: o id, no fim');
  assert.equal(linhas[0].querySelector('.placar__barra').style.width, '24px', '1 ato com piso de 3: um terço de 72 px');
  assert.equal(linhas[0].querySelectorAll('.placar__barra').length, 1, 'contagem zero não tem barra');
  assert.equal(figura(m, 'atos').querySelector('.atos').getAttribute('aria-label'), 'Atos por tema nos últimos 30 dias: 2 atos em 2 temas');
});

test('Arquivo 01, Indicadores: uma mini-linha por indicador do índice, com o primeiro e o último valor', async () => {
  const m = await abreArquivo();
  const f = figura(m, 'indicadores');
  const minis = f.querySelectorAll('.mini');
  /* a ordem é a do catálogo; o que ele não conhece fica no fim, pelo id */
  assert.deepEqual(textos(minis.map((li) => li.querySelector('h4'))), ['Petróleo Brent', 'Petróleo WTI (EUA)', 'Gás natural nos EUA', 'Trigo', 'Milho',
    'Soja', 'Índice de preços de alimentos da FAO', 'Dólar em reais', 'Índice do dólar contra outras moedas', 'Ouro',
    'Índice de medo da bolsa americana (VIX)', 'cobre']);
  assert.equal(textoDe(minis[0].querySelector('.mini__unidade')), 'US$ por barril', 'nome e unidade vêm do catálogo');
  assert.equal(textoDe(minis[11].querySelector('.mini__unidade')), '');
  assert.ok(minis[11].querySelector('h4').classList.contains('id-cru'));
  const brent = minis[0];
  assert.equal(textoDe(brent.querySelector('.mini__pontas')), 'primeiro 70,00 último 78,40');
  const svg = brent.querySelector('svg');
  assert.equal(svg.getAttribute('role'), 'img');
  assert.equal(svg.getAttribute('viewBox'), '0 0 120 28');
  assert.equal(svg.getAttribute('aria-label'), 'Petróleo Brent nos últimos 30 dias: primeiro valor, 70,00; último, 78,40');
  /* casas decimais do catálogo: trigo com 1, dólar com 4 */
  assert.equal(textoDe(minis[3].querySelector('.mini__pontas')), 'primeiro 216,9 último 216,9');
  assert.equal(textoDe(minis[7].querySelector('.mini__pontas')), 'primeiro 5,4321 último 5,4321');
  /* a figura é desenho: nenhum caractere, nenhuma cor de nível */
  assert.equal(svg.textContent, '');
  assert.equal(f.querySelectorAll('[class*="nivel-"], [class*="alerta"]').length, 0);
});

test('Arquivo 01, mini-linha: um ponto por edição na posição do dia; dia sem valor quebra a linha; ponto final à parte', async () => {
  const m = await abreArquivo();
  const svg = figura(m, 'indicadores').querySelectorAll('.mini')[0].querySelector('svg');
  const pecas = svg.children.map((c) => [c.localName, c.getAttribute('class'), c.getAttribute('points') || [c.getAttribute('cx'), c.getAttribute('cy'), c.getAttribute('r')].join(' ')]);
  /* 21/10 a 02/11 (13 pontos); 03/11 sem valor; 04/11 sozinho (05/11 é de exemplo); 06 e 07/11; 08/11 sem
     edição; 09 a 11/11; 12/11 é falha, sem o Brent; 13 a 19/11 */
  assert.deepEqual(pecas.map((p) => p[0] + '.' + p[1] + (p[0] === 'polyline' ? ':' + p[2].split(' ').length : '')),
    ['polyline.mini__traco:13', 'circle.mini__solto', 'polyline.mini__traco:2', 'polyline.mini__traco:3', 'polyline.mini__traco:7', 'circle.mini__ponto']);
  /* escala: do menor (70,0) ao maior (78,4), com 4 de folga em cima e embaixo; x de 6 a 114 */
  assert.equal(pecas[0][2].split(' ')[0], '6,24', 'primeiro dia, menor valor: canto de baixo');
  assert.equal(pecas[4][2].split(' ').pop(), '114,4', 'último dia, maior valor: canto de cima');
  assert.equal(pecas[1][2], '58.1 17.3 1', 'o ponto sozinho de 04/11: dia 14 de 0 a 29');
  assert.equal(pecas[5][2], '114 4 5', 'o ponto final: raio 4 à vista mais o anel');
  pecas.forEach((p) => {
    (p[0] === 'polyline' ? p[2].split(' ').map((xy) => xy.split(',')) : [p[2].split(' ')]).forEach(([x, y]) => {
      assert.ok(Number(x) >= 6 && Number(x) <= 114, 'x dentro da caixa: ' + x);
      assert.ok(Number(y) >= 4 && Number(y) <= 24, 'y dentro da folga: ' + y);
    });
  });
  /* valores todos iguais: linha reta a meia altura */
  const dolar = figura(m, 'indicadores').querySelectorAll('.mini')[7].querySelector('svg');
  dolar.querySelectorAll('polyline').forEach((linha) => {
    linha.getAttribute('points').split(' ').forEach((xy) => assert.equal(xy.split(',')[1], '14'));
  });
  assert.equal(dolar.querySelector('.mini__ponto').getAttribute('cy'), '14');
});

test('Arquivo 01, mini-linha: com menos de 2 valores mostra só o número, sem figura', async () => {
  const m = await abreArquivo();
  const gas = figura(m, 'indicadores').querySelectorAll('.mini')[2];
  assert.equal(textoDe(gas), 'Gás natural nos EUA US$ por milhão de BTU 3,21');
  assert.equal(textoDe(gas.querySelector('.mini__so')), '3,21');
  assert.equal(gas.querySelectorAll('svg, dl, [role="img"]').length, 0);
});

test('Arquivo 01, Indicadores: a tabela gêmea traz um valor por dia e por indicador, e travessão onde não houve', async () => {
  const m = await abreArquivo();
  const tabela = figura(m, 'indicadores').querySelector('table');
  assert.ok(tabela.classList.contains('tabela--larga'), 'muitas colunas: abaixo do largo, vira bloco com rótulos');
  const cabeca = textos(tabela.querySelectorAll('thead th'));
  assert.equal(cabeca.length, 13);
  assert.deepEqual(cabeca.slice(0, 4), ['Data', 'Petróleo Brent', 'Petróleo WTI (EUA)', 'Gás natural nos EUA']);
  const linhas = linhasDe(tabela);
  assert.equal(linhas.length, 28);
  assert.equal(linhas[0], '19/11/2026 | 78,40 | 74,10 | — | 216,9 | 179,3 | 383,1 | 126,4 | 5,4321 | 103,20 | 2.650,0 | 18,40 | —');
  assert.equal(linhas.find((l) => l.startsWith('14/11/2026')), '14/11/2026 | 74,80 | — | 3,21 | — | — | — | — | 5,4321 | — | — | — | —');
  assert.equal(linhas.find((l) => l.startsWith('12/11/2026')), '12/11/2026 | — | — | — | — | — | — | — | 5,4321 | — | — | — | —', 'a falha traz só o que houve');
  assert.equal(linhas.find((l) => l.startsWith('03/11/2026')).split(' | ')[1], '—');
  assert.equal(tabela.querySelectorAll('tbody tr')[0].children[1].getAttribute('data-rotulo'), 'Petróleo Brent');
  assert.ok(tabela.querySelectorAll('tbody tr')[0].children[1].classList.contains('num'));
});

test('Arquivo 01: sem o catálogo os indicadores aparecem pelo id, com aviso; sem a régua, níveis e domínios crus', async () => {
  let m = await abre({ hash: '#/arquivo', arquivos: arquivosDe35Dias((t) => { delete t['dados/indicadores.json']; }) });
  assert.deepEqual(textos(m.todos('.vista__corpo > .avisos .aviso')),
    ['DADOS DE APOIO INDISPONÍVEIS Não deu para carregar dados/indicadores.json. Alguns nomes aparecem como identificadores.']);
  const minis = figura(m, 'indicadores').querySelectorAll('.mini');
  assert.equal(textoDe(minis[0].querySelector('h4')), 'usd_brl', 'sem o catálogo, a ordem é a do índice');
  assert.ok(textos(minis.map((li) => li.querySelector('h4'))).includes('brent'));
  assert.equal(textoDe(minis.find((li) => textoDe(li.querySelector('h4')) === 'brent').querySelector('.mini__pontas')), 'primeiro 70,00 último 78,40',
    'sem o catálogo, de 2 a 4 casas');
  assert.equal(m.todos('.figura').length, 5);

  m = await abre({ hash: '#/arquivo', arquivos: arquivosDe35Dias((t) => { delete t['dados/regua.json']; }) });
  assert.deepEqual(textos(m.todos('.vista__corpo > .avisos .aviso')), ['RÉGUA INDISPONÍVEL Nomes e rótulos aparecem como identificadores.']);
  assert.equal(m.todos('.figura').length, 5, 'o Arquivo fica de pé');
  assert.deepEqual(textos(figura(m, 'dominios').querySelectorAll('.fitinha__nome')), ['energia', 'alimentos', 'cambio', 'suprimentos', 'conflito']);
  assert.equal(textoDe(figura(m, 'dominios').querySelector('.selo__rotulo')), 'NÍVEL 3');
  assert.deepEqual(textos(figura(m, 'partidos').querySelectorAll('.placar__topo')).slice(0, 2), ['ordem_global +11', 'soberanistas −1'],
    'sem a régua, os partidos que o índice traz, pelo id');
  assert.deepEqual(textos(figura(m, 'atos').querySelectorAll('.ato__tema')), ['clima', 'ia_depois']);
  assert.equal(textoDe(m.um('.mes tbody tr').children[2]), 'Nível 3 de 5, subindo 3 NÍVEL 3 subindo');
  assert.equal(m.todos('.mes tbody tr')[0].querySelectorAll('abbr').length, 5, 'as siglas dos domínios são fixas no site');
});

test('Arquivo 02: a lista do índice por mês, mais nova primeiro; os 2 meses mais novos vêm abertos', async () => {
  const m = await abreArquivo();
  const meses = m.todos('#s-edicoes .mes');
  assert.deepEqual(textos(meses.map((mes) => mes.querySelector('h3'))), ['Novembro de 2026 (18)', 'Outubro de 2026 (16)']);
  meses.forEach((mes) => {
    assert.equal(mes.querySelector('button'), null, 'mês aberto não é dobra');
    assert.equal(aVista(mes.querySelector('table')), true);
  });
  const tabela = meses[0].querySelector('table');
  assert.deepEqual(textos(tabela.querySelectorAll('thead th')), ['Data', 'Estado', 'Nível', 'Domínios', 'Resumo']);
  assert.equal(textoDe(tabela.querySelector('caption')), 'Novembro de 2026 (18)');
  assert.ok(tabela.querySelector('caption').classList.contains('so-leitor'), 'o título do mês já está à vista');
  const linhas = tabela.querySelectorAll('tbody tr');
  assert.equal(linhas.length, 18);
  assert.deepEqual(linhas.map((tr) => tr.querySelector('time').getAttribute('datetime')).slice(0, 4),
    ['2026-11-19', '2026-11-18', '2026-11-17', '2026-11-16']);
  assert.equal(meses[1].querySelectorAll('tbody tr').length, 16, 'a lista mostra todas as entradas, e não só as dos 30 dias');
  assert.equal(meses[1].querySelectorAll('tbody tr')[15].querySelector('time').getAttribute('datetime'), '2026-10-16');

  /* uma linha, célula por célula */
  const [data, estado, nivel, dominios, resumo] = linhas[0].children;
  assert.equal(textoDe(data), '19/11/2026 18h14');
  assert.equal(data.querySelector('a').getAttribute('href'), '#/edicao/2026-11-19');
  assert.deepEqual(data.querySelectorAll('time').map((t) => t.getAttribute('datetime')), ['2026-11-19', '2026-11-19T21:14:03Z']);
  assert.equal(textoDe(estado), 'completa');
  assert.equal(textoDe(nivel.querySelector('.selo .so-leitor')), 'Nível 3 de 5, tensão, subindo');
  assert.equal(nivel.querySelector('.selo use').getAttribute('href'), '#i-nivel-3');
  assert.equal(nivel.querySelector('.tendencia').getAttribute('aria-hidden'), 'true', 'o selo já diz a tendência ao leitor de tela');
  assert.equal(nivel.querySelector('.tendencia use').getAttribute('href'), '#i-sobe');
  assert.equal(textoDe(dominios), 'ENE 3 ALI 1 CAM 2 SUP 2 CON 3');
  assert.deepEqual(dominios.querySelectorAll('abbr').map((a) => a.getAttribute('title')),
    ['Energia', 'Alimentos', 'Câmbio', 'Cadeias de suprimento', 'Risco de conflito']);
  assert.match(textoDe(resumo), /^Edição fictícia: um ataque inventado .* ao nível 3\. texto · JSON$/);
  assert.deepEqual(resumo.querySelectorAll('a').map((a) => [textoDe(a), a.getAttribute('href')]),
    [['texto', 'edicoes/2026-11-19.md'], ['JSON', 'edicoes/2026-11-19.json']]);
  assert.ok(resumo.classList.contains('tabela__longa'), 'texto corrido: na tela estreita, o rótulo fica em cima');
  assert.deepEqual(linhas[0].children.map((c) => c.getAttribute('data-rotulo')), ['Data', 'Estado', 'Nível', 'Domínios', 'Resumo']);
});

test('Arquivo 02: estados, etiqueta EXEMPLO, "corrigida em" e a tendência de cada edição', async () => {
  const m = await abreArquivo();
  const linha = (data) => m.todos('#s-edicoes tbody tr').find((tr) => tr.querySelector('time').getAttribute('datetime') === data);
  const estado = (data) => textoDe(linha(data).children[1]);
  assert.equal(estado('2026-11-12'), 'sem edição');
  assert.equal(estado('2026-10-28'), 'reduzida');
  assert.equal(estado('2026-11-17'), 'completa');
  assert.equal(estado('2026-11-05'), 'completa EXEMPLO');
  assert.ok(linha('2026-11-05').children[1].querySelector('.etiqueta'));
  assert.equal(m.todos('#s-edicoes tbody .etiqueta').filter((e) => textoDe(e) === 'EXEMPLO').length, 1);
  /* corrigida em 11/11: a edição que corrige está no índice, e vira link */
  assert.equal(estado('2026-11-10'), 'completa corrigida em 11/11/2026');
  assert.equal(linha('2026-11-10').children[1].querySelector('a').getAttribute('href'), '#/edicao/2026-11-11');
  assert.equal(textoDe(linha('2026-11-10').children[2]), 'Nível 3 de 5, tensão, descendo 3 TENSÃO descendo');
  assert.equal(linha('2026-11-10').children[2].querySelector('.tendencia use').getAttribute('href'), '#i-desce');
  assert.equal(textoDe(linha('2026-11-12').children[2]), 'Nível 2 de 5, atenção, estável 2 ATENÇÃO estável');
  /* nenhum dia inventado: 08/11 não teve edição e não tem linha */
  assert.equal(linha('2026-11-08'), undefined);
  assert.equal(textoDe(linha('2026-11-09').children[3]), 'ENE 4 ALI 1 CAM 2 SUP 1 CON 4');
});

test('Arquivo 02: "corrigida em" com data fora do índice não vira link; caminho torto do índice sai da data', async () => {
  const m = await abreArquivo((t) => {
    const entrada = t['edicoes/indice.json'].edicoes.find((e) => e.data === '2026-11-10');
    entrada.corrigida_em = ['2026-12-25', 'amanhã'];
    entrada.arquivo = '../segredo.json';
    entrada.texto = 'https://exemplo.invalid/fora.md';
  });
  const linha = m.todos('#s-edicoes tbody tr').find((tr) => tr.querySelector('time').getAttribute('datetime') === '2026-11-10');
  assert.equal(textoDe(linha.children[1]), 'completa corrigida em 25/12/2026 corrigida em amanhã');
  assert.equal(linha.children[1].querySelectorAll('a').length, 0);
  assert.deepEqual(linha.children[4].querySelectorAll('a').map((a) => a.getAttribute('href')), ['edicoes/2026-11-10.md', 'edicoes/2026-11-10.json']);
});

test('Arquivo 02: mês mais antigo que os 2 mais novos é dobra fechada, com a contagem no título', async () => {
  const m = await abreArquivo((t) => {
    t['edicoes/indice.json'].edicoes.push(entradaSolta('2026-09-30', { nivel: 4 }), entradaSolta('2026-09-29'), entradaSolta('2026-08-15', { nivel: 5 }));
  });
  const meses = m.todos('#s-edicoes .mes');
  assert.deepEqual(textos(meses.map((mes) => mes.querySelector('h3'))),
    ['Novembro de 2026 (18)', 'Outubro de 2026 (16)', 'Setembro de 2026 (2)', 'Agosto de 2026 (1)']);
  assert.equal(meses[0].querySelector('button'), null);
  assert.equal(meses[1].querySelector('button'), null);
  const botao = meses[2].querySelector('h3 button');
  assert.equal(botao.getAttribute('type'), 'button');
  assert.equal(botao.getAttribute('aria-expanded'), 'false');
  assert.equal(botao.classList.contains('botao'), false, 'no papel os botões somem; este é o título e fica');
  const corpo = m.documento.getElementById(botao.getAttribute('aria-controls'));
  assert.equal(aVista(meses[2].querySelector('table')), false);
  assert.ok(corpo.classList.contains('dobra__corpo'), 'a impressão abre o que tem esta classe');
  await m.clica(botao);
  assert.equal(botao.getAttribute('aria-expanded'), 'true');
  assert.equal(aVista(meses[2].querySelector('table')), true);
  assert.equal(meses[2].querySelectorAll('tbody tr').length, 2);
  /* Esc com o foco dentro fecha a dobra e devolve o foco ao título */
  meses[2].querySelector('tbody a').focus();
  m.tecla('Escape');
  assert.equal(botao.getAttribute('aria-expanded'), 'false');
  assert.equal(m.documento.activeElement, botao);
  assert.equal(aVista(meses[3].querySelector('table')), false);
});

test('Arquivo 02: "Índice atualizado em", com o dia e a hora de Brasília', async () => {
  let m = await abreArquivo();
  assert.equal(textoDe(m.um('.arquivo__atualizado')), 'Índice atualizado em 19/11/2026, às 18h14.');
  assert.equal(m.um('.arquivo__atualizado time').getAttribute('datetime'), '2026-11-19T21:14:03Z');
  /* às 2h30 UTC do dia 20 ainda é dia 19 em Brasília */
  m = await abreArquivo((t) => { t['edicoes/indice.json'].atualizado_em = '2026-11-20T02:30:00Z'; });
  assert.equal(textoDe(m.um('.arquivo__atualizado')), 'Índice atualizado em 19/11/2026, às 23h30.');
  m = await abreArquivo((t) => { t['edicoes/indice.json'].atualizado_em = '<img src=x onerror=alert(1)>'; });
  assert.equal(m.um('.arquivo__atualizado'), null, 'o que não é data-hora não aparece');
});

test('Arquivo, filtro de nível mínimo: recorta a lista, vai para o endereço e a contagem é anunciada', async () => {
  const m = await abreArquivo();
  const campo = m.um('#s-edicoes select');
  assert.deepEqual(textos(campo.querySelectorAll('option')), ['Todos os níveis', '2 ou mais', '3 ou mais', '4 ou mais', 'Só 5']);
  assert.deepEqual(campo.querySelectorAll('option').map((o) => o.getAttribute('value')), ['', '2', '3', '4', '5']);
  const rotulo = m.um('#s-edicoes label');
  assert.equal(textoDe(rotulo), 'Nível mínimo');
  assert.equal(rotulo.getAttribute('for'), campo.getAttribute('id'));
  assert.equal(textoDe(m.um('#s-edicoes .filtros__contagem')), '');
  const aVistaNaLista = () => m.todos('#s-edicoes tbody tr').filter(aVista).map((tr) => tr.querySelector('time').getAttribute('datetime'));
  assert.equal(aVistaNaLista().length, 34);
  const pedidos = m.rede.pedidos.length;

  await m.escolhe(campo, '3');
  assert.deepEqual(aVistaNaLista(), ['2026-11-19', '2026-11-18', '2026-11-10', '2026-11-09', '2026-11-07', '2026-11-06', '2026-11-05']);
  assert.equal(m.janela.location.hash, '#/arquivo?nivel=3');
  assert.deepEqual(m.historico, ['#/arquivo?nivel=3'], 'sem criar passo no histórico');
  assert.equal(textoDe(m.um('#s-edicoes .filtros__contagem')), '7 de 34 edições');
  assert.equal(textoDe(m.um('#anuncio')), '7 de 34 edições');
  assert.equal(m.rede.pedidos.length, pedidos, 'filtro não carrega nada');
  assert.deepEqual(m.todos('#s-edicoes .mes').map(aVista), [true, false], 'mês sem linha à vista some inteiro');
  /* filtrar não muda as figuras nem a ordem */
  assert.equal(figura(m, 'alerta').querySelectorAll('.fita__coluna').length, 28);

  await m.escolhe(campo, '5');
  assert.deepEqual(aVistaNaLista(), ['2026-11-05'], 'só a de exemplo estava no nível 5');
  assert.equal(m.janela.location.hash, '#/arquivo?nivel=5');
  await m.escolhe(campo, '2');
  assert.equal(aVistaNaLista().length, 19);
  assert.deepEqual(m.todos('#s-edicoes .mes').map(aVista), [true, true]);
  assert.deepEqual(aVistaNaLista().slice(-1), ['2026-10-28'], 'em outubro, só a reduzida de 28/10 estava no nível 2');
  await m.escolhe(campo, '');
  assert.equal(aVistaNaLista().length, 34);
  assert.equal(m.janela.location.hash, '#/arquivo');
  assert.equal(textoDe(m.um('#anuncio')), '34 de 34 edições');
});

test('Arquivo, filtro: volta do endereço; valor fora da lista é ignorado', async () => {
  let m = await abreArquivo(null, '#/arquivo?nivel=4');
  assert.equal(m.um('#s-edicoes select').value, '4');
  assert.deepEqual(m.todos('#s-edicoes tbody tr').filter(aVista).map((tr) => tr.querySelector('time').getAttribute('datetime')), ['2026-11-09', '2026-11-05']);
  assert.equal(textoDe(m.um('#s-edicoes .filtros__contagem')), '2 de 34 edições');
  assert.equal(m.janela.location.hash, '#/arquivo?nivel=4', 'o endereço fica como veio');
  assert.equal(m.historico.length, 0);

  for (const hash of ['#/arquivo?nivel=1', '#/arquivo?nivel=9', '#/arquivo?nivel=tres', '#/arquivo?nivel=%3Cimg%3E', '#/arquivo?cat=ia']) {
    m = await abreArquivo(null, hash);
    assert.equal(m.um('#s-edicoes select').value, '', hash);
    assert.equal(m.todos('#s-edicoes tbody tr').filter(aVista).length, 34, hash);
    assert.equal(m.todos('#avisos-gerais .aviso').length, 0, hash + ': parâmetro torto não é endereço não encontrado');
  }
  /* trocar o endereço com a vista aberta troca o filtro */
  await m.vai('#/arquivo?nivel=3');
  assert.equal(m.todos('#s-edicoes tbody tr').filter(aVista).length, 7);
  assert.equal(m.documento.activeElement, m.um('h1'), 'ao trocar de rota o foco vai para o título');
});

test('Arquivo, filtro sem resultado: a frase e o botão "Limpar filtros"', async () => {
  const m = await abreArquivo((t) => { t['edicoes/indice.json'].edicoes = t['edicoes/indice.json'].edicoes.filter((e) => !e.exemplo); }, '#/arquivo?nivel=5');
  const vazio = m.um('#s-edicoes .filtros__vazio');
  assert.equal(aVista(vazio), true);
  assert.equal(textoDe(vazio), 'Nenhuma edição no arquivo. Limpar filtros');
  assert.equal(m.todos('#s-edicoes tbody tr').filter(aVista).length, 0);
  assert.equal(textoDe(m.um('#s-edicoes .filtros__contagem')), '0 de 33 edições');
  await m.clica(vazio.querySelector('button'));
  assert.equal(aVista(vazio), false);
  assert.equal(m.todos('#s-edicoes tbody tr').filter(aVista).length, 33);
  assert.equal(m.janela.location.hash, '#/arquivo');
});

test('vazio: índice com a lista vazia mostra "NENHUMA EDIÇÃO AINDA", e o Arquivo diz que não há edição', async () => {
  const tabela = arquivos();
  tabela['edicoes/indice.json'] = { versao: 1, atualizado_em: '2026-11-19T21:14:03Z', edicoes: [] };
  const m = await abre({ hash: '#/arquivo', arquivos: tabela });
  assert.equal(textoDe(m.um('#avisos-gerais .aviso')), 'NENHUMA EDIÇÃO AINDA A primeira sai às 18h de Brasília.');
  assert.equal(m.um('#avisos-gerais .aviso').classList.contains('aviso--grave'), false);
  assert.equal(textoDe(m.um('#anuncio')), 'NENHUMA EDIÇÃO AINDA. A primeira sai às 18h de Brasília.');
  assert.equal(textoDe(m.um('h1')), 'Arquivo');
  assert.equal(m.um('nav a[aria-current="page"]').textContent, 'Arquivo');
  assert.equal(textoDe(m.um('#s-edicoes .vazio')), 'Nenhuma edição no arquivo.');
  assert.equal(m.todos('#s-edicoes select, #s-edicoes table').length, 0);
  /* as cinco figuras continuam lá, dizendo o que falta */
  assert.equal(m.todos('.figura').length, 5);
  assert.equal(textoDe(figura(m, 'atos').querySelector('.vazio')), 'Nenhum ato registrado em 30 dias.');
  assert.equal(textoDe(figura(m, 'alerta').querySelector('.vazio')), '—');
  assert.deepEqual(textos(figura(m, 'partidos').querySelectorAll('.placar__topo')), ['OG 0', 'CA 0', 'BT 0', 'SO 0', 'ER 0', 'CE 0', 'IN 0']);
  assert.equal(figura(m, 'partidos').querySelector('.saldos').getAttribute('aria-label'), 'Saldo dos partidos nos últimos 30 dias: todos em zero');
  assert.equal(m.todos('.figura [role="img"]').length, 1);
  assert.equal(m.um('#vista').hasAttribute('aria-busy'), false);
  /* o aviso sai na rota seguinte, e Régua e Método funcionam */
  await m.vai('#/regua/partidos');
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
  assert.equal(m.todos('.partido').length, 7);
  await m.vai('#/metodo');
  assert.equal(m.todos('main h2').length, 7);
});

test('erro de rede: o índice não carrega, e o Arquivo mostra "FALHA AO CARREGAR", com "Tentar de novo"', async () => {
  const m = await abre({ hash: '#/arquivo', arquivos: arquivos({ sem: ['edicoes/indice.json'] }) });
  const aviso = m.um('#avisos-gerais .aviso');
  assert.ok(aviso.classList.contains('aviso--grave'));
  assert.equal(textoDe(aviso), 'FALHA AO CARREGAR Não deu para carregar edicoes/indice.json. Confira a conexão. Tentar de novo ' +
    'Abrir o Arquivo de edições. O feed traz o resumo das últimas edições.');
  assert.match(textoDe(m.um('#anuncio')), /^FALHA AO CARREGAR\. Não deu para carregar edicoes\/indice\.json\./);
  /* a vista continua sendo o Arquivo: não dá lugar à moldura do Painel */
  assert.equal(textoDe(m.um('h1')), 'Arquivo');
  assert.equal(m.um('nav a[aria-current="page"]').textContent, 'Arquivo');
  assert.equal(m.um('#vista').getAttribute('class'), 'vista vista--arquivo');
  assert.equal(m.um('#vista').hasAttribute('aria-busy'), false);
  assert.equal(textoDe(m.um('.vista__corpo')), '—');
  assert.equal(m.todos('#s-hoje').length, 0);
  /* a rede volta: "Tentar de novo" pede o índice outra vez e monta o Arquivo */
  m.rede.arquivos['edicoes/indice.json'] = indiceDe([entradaDoIndice(edicaoReal(DIA)), entradaSolta('2026-11-18', { nivel: 2 })]);
  await m.clica(aviso.querySelector('button'));
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
  assert.equal(textoDe(m.um('h1')), 'Arquivo');
  assert.equal(m.janela.location.hash, '#/arquivo');
  assert.equal(m.todos('#s-edicoes tbody tr').length, 2);
  assert.equal(m.rede.pedidos.filter((p) => p.caminho === 'edicoes/indice.json').length, 2);
});

test('erro de rede no Arquivo: JSON quebrado e fetch rejeitado dão o mesmo aviso; Régua e Método seguem de pé', async () => {
  for (const valor of [new Error('sem rede'), '{"versao": 1, "edicoes": [', '[1, 2]']) {
    const tabela = arquivos();
    tabela['edicoes/indice.json'] = valor;
    const m = await abre({ hash: '#/arquivo', arquivos: tabela });
    assert.match(textoDe(m.um('#avisos-gerais .aviso')), /^FALHA AO CARREGAR Não deu para carregar edicoes\/indice\.json\./);
    assert.equal(textoDe(m.um('h1')), 'Arquivo');
    await m.vai('#/regua/players');
    assert.equal(m.todos('#avisos-gerais .aviso').length, 0, 'o aviso de falha sai na rota seguinte');
    assert.equal(m.todos('.matriz__linha').length, 30);
    await m.vai('#/metodo/conflito');
    assert.equal(m.documento.activeElement, m.um('#t-conflito'));
  }
});

test('Arquivo: só com a edição de exemplo no índice, a lista mostra a edição e o histórico fica vazio', async () => {
  const m = await abre({ hash: '#/arquivo', arquivos: arquivos({ edicoes: [edicaoDeExemplo()] }) });
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
  assert.equal(m.todos('#s-edicoes tbody tr').length, 1);
  assert.equal(textoDe(m.um('#s-edicoes tbody tr').children[1]), 'completa EXEMPLO');
  assert.equal(m.todos('.figura [role="img"]').length, 1, 'só os saldos, todos em zero: a de exemplo não entra em histórico nem em acumulado');
  assert.equal(textoDe(figura(m, 'indicadores').querySelector('.vazio')), '—');
  assert.equal(figura(m, 'alerta').querySelector('table'), null);
});

test('Arquivo: com uma edição só, a fita não aparece, mas a tabela diz o que há; exemplo mais novo não desloca os 30 dias', async () => {
  let m = await abre({ hash: '#/arquivo', arquivos: arquivos({ edicoes: [edicaoReal(DIA)] }) });
  assert.equal(figura(m, 'alerta').querySelector('.fita'), null, 'com menos de 2 edições, a fita não aparece');
  assert.deepEqual(linhasDe(figura(m, 'alerta').querySelector('table')), ['19/11/2026 | 3 TENSÃO | completa']);
  assert.equal(figura(m, 'dominios').querySelectorAll('.fita').length, 0);
  assert.equal(figura(m, 'dominios').querySelectorAll('tbody tr').length, 1);
  /* todos os indicadores têm um valor só: só o número, sem figura */
  assert.equal(figura(m, 'indicadores').querySelectorAll('svg').length, 0);
  assert.equal(figura(m, 'indicadores').querySelectorAll('.mini__so').length, 10);
  /* no lugar do desenho, a frase diz por quê (e não um travessão que parece defeito) */
  assert.equal(textoDe(figura(m, 'alerta').querySelector('.vazio')), 'O desenho aparece a partir da 2ª edição.');
  assert.equal(textoDe(figura(m, 'dominios').querySelector('.vazio')), 'O desenho aparece a partir da 2ª edição.');

  const exemplo = edicaoDeExemplo();
  exemplo.data = '2026-11-25';
  m = await abre({ hash: '#/arquivo', arquivos: arquivos({ edicoes: [edicaoReal(DIA), exemplo], entradas: [entradaSolta('2026-10-21', { nivel: 2 })] }) });
  assert.equal(textoDe(figura(m, 'alerta').querySelector('.fita__datas')), '21/10 19/11', 'os 30 dias terminam na edição de verdade mais nova');
  assert.equal(figura(m, 'alerta').querySelectorAll('.fita__coluna').length, 2);
  assert.equal(m.todos('#s-edicoes tbody tr').length, 3, 'a de exemplo aparece na lista');
});

test('Arquivo do dia um: uma edição real e nenhum preço medido; cada cartão diz o que falta', async () => {
  const primeira = edicaoReal(DIA, (e) => { e.indicadores.forEach((i) => { i.valor = null; }); });
  const m = await abre({ hash: '#/arquivo', arquivos: arquivos({ edicoes: [primeira] }) });
  assert.equal(textoDe(figura(m, 'alerta').querySelector('.vazio')), 'O desenho aparece a partir da 2ª edição.');
  assert.equal(textoDe(figura(m, 'dominios').querySelector('.vazio')), 'O desenho aparece a partir da 2ª edição.');
  assert.equal(textoDe(figura(m, 'indicadores').querySelector('.vazio')), 'Nenhum preço medido nos últimos 30 dias.');
  /* a tabela gêmea continua com a linha do dia */
  assert.equal(figura(m, 'alerta').querySelectorAll('tbody tr').length, 1);
  /* com a 2ª edição, mesmo de falha, as fitas aparecem e a frase sai */
  const m2 = await abre({ hash: '#/arquivo', arquivos: arquivos({ edicoes: [primeira], entradas: [entradaSolta('2026-11-18', { nivel: 2 })] }) });
  assert.equal(figura(m2, 'alerta').querySelectorAll('.fita').length, 1);
  assert.equal(figura(m2, 'alerta').querySelector('.vazio'), null);
});

test('Arquivo: índice de formato novo leva o aviso; entradas tortas não derrubam a vista', async () => {
  const m = await abreArquivo((t) => {
    t['edicoes/indice.json'].versao = 2;
    t['edicoes/indice.json'].edicoes.push(null, 7, 'x', { data: '2026-99-99' }, { data: '2026-10-15' },
      { data: '2026-10-14', nivel: 'alto', niveis: 'nenhum', saldos: [1], eixos: 5, indicadores: null, resumo: { a: 1 }, estado: 9, corrigida_em: 'ontem', gerada_em: 12 });
    t['edicoes/indice.json'].edicoes[0].niveis = null;
    t['edicoes/indice.json'].edicoes[1].indicadores = { brent: '78,4', usd_brl: null };
    t['edicoes/indice.json'].edicoes[2].eixos = { clima: 'muitos', ia_depois: { azul: '2' } };
    t['edicoes/indice.json'].edicoes[2].saldos = { ordem_global: 'muito' };
  });
  assert.deepEqual(textos(m.todos('.vista__corpo > .avisos .aviso')), ['FORMATO NOVO O arquivo edicoes/indice.json usa um formato mais novo que o site.']);
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
  assert.equal(m.todos('.figura').length, 5);
  assert.equal(m.todos('#s-edicoes tbody tr').length, 36, 'as duas entradas com data válida entram; o resto é ignorado');
  const torta = m.todos('#s-edicoes tbody tr')[35];
  assert.equal(textoDe(torta.children[0]), '14/10/2026');
  assert.equal(textoDe(torta.children[3]), '—');
  assert.equal(/undefined|NaN|\[object/.test(textoDe(m.um('main'))), false);
});

test('Arquivo: enquanto o índice não chega, a vista fica com aria-busy e um travessão; depois de 8 segundos, "Está demorando"', async () => {
  const m = await abre({ hash: '#/arquivo', arquivos: arquivosDe35Dias(), segura: true, esperar: false });
  await m.assenta();
  assert.equal(textoDe(m.um('h1')), 'Arquivo');
  assert.equal(m.um('#vista').getAttribute('aria-busy'), 'true');
  assert.equal(textoDe(m.um('.vista__corpo')), '—');
  m.relogio.avanca(7999);
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
  m.relogio.avanca(1);
  assert.equal(textoDe(m.um('#avisos-gerais .aviso')), 'Está demorando. A conexão pode estar lenta. Tentar de novo');
  assert.equal(textoDe(m.um('#anuncio')), 'Está demorando. A conexão pode estar lenta.');
  m.rede.solta();
  await m.assenta();
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0, 'o aviso sai quando os dados chegam');
  assert.equal(m.um('#vista').hasAttribute('aria-busy'), false);
  assert.equal(m.todos('.figura').length, 5);
  m.relogio.avanca(20000);
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
});

test('Arquivo: sair no meio da carga descarta o que chegar depois', async () => {
  const m = await abre({ hash: '#/arquivo', arquivos: arquivosDe35Dias(), segura: true, esperar: false });
  await m.assenta();
  assert.equal(m.um('#vista').getAttribute('aria-busy'), 'true');
  m.janela.location.hash = '#/metodo';
  await m.assenta();
  m.rede.solta();
  await m.assenta();
  assert.equal(textoDe(m.um('h1')), 'Método');
  assert.equal(m.todos('.figura').length, 0, 'o Arquivo que chegou atrasado não toma a tela');
  assert.equal(m.todos('main h2').length, 7);
  m.relogio.avanca(9000);
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0, 'o relógio de demora da carga abandonada não dispara');
});

test('endereço sem destino: a edição que não existe abre o Arquivo montado, com o aviso', async () => {
  const m = await abre({ hash: '#/edicao/2026-01-01', arquivos: arquivosDe35Dias() });
  assert.equal(textoDe(m.um('#avisos-gerais .aviso')), 'NÃO HÁ EDIÇÃO DE 01/01/2026 Mostrando o Arquivo.');
  assert.equal(textoDe(m.um('h1')), 'Arquivo');
  assert.equal(m.todos('.figura').length, 5);
  assert.equal(m.todos('#s-edicoes tbody tr').length, 34);
  /* o filtro grava o endereço do Arquivo, e não o da edição que não existe */
  await m.escolhe(m.um('#s-edicoes select'), '4');
  assert.equal(m.janela.location.hash, '#/arquivo?nivel=4');
});
