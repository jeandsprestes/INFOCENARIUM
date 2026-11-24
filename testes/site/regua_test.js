'use strict';

/* A vista Régua (#/regua/…): o cabeçalho comum, a legenda e as quatro abas
 * (Partidos, Players, Veículos e Vetores), com os dados congelados (30
 * players, 146 veículos) e o índice de teste de 35 dias. O registro de
 * vetores congelado é vazio: cada teste acrescenta as entradas de que precisa. */

const test = require('node:test');
const assert = require('node:assert/strict');
const { abre, arquivos, arquivosDe35Dias, dados, textoDe, aVista, DIA } = require('./apoio.js');

const textos = (lista) => lista.map(textoDe);

/* Para conferir a busca do site com uma conta feita à parte: os dados
   congelados e um "sem acento" escrito de outro jeito. */
const CONGELADOS = dados();
const semAcento = (texto) => String(texto).normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
const queTem = (lista, procurado) => lista.filter((item) => (semAcento(item.nome) + ' ' + semAcento(item.id)).includes(semAcento(procurado)));
const AVISO_FICHA = (id) => 'FICHA NÃO ENCONTRADA Não há nada na Régua com o identificador ' + id + '.';

/* Três entradas no registro: um vetor da UE, depois anulado; outro, de pé,
   com a marca de conflito; e a entrada de anulação. */
function comVetores(tabela) {
  tabela['dados/vetores.json'].vetores.push(
    { id: '2026-11-10_p1_ue', data: '2026-11-10', item: 'p1', player: 'ue', de: 'centro_atlantico', para: 'soberanistas', forca: 1, tema: 'clima',
      porque: 'Suspendeu uma meta de corte de emissões.', url: 'https://exemplo.invalid/vetor/antigo' },
    { id: '2026-11-18_r2_google', data: '2026-11-18', item: 'r2', player: 'google', de: 'bancada_talento', para: 'ordem_global', forca: 2, tema: 'ia_depois',
      porque: 'Adiou um modelo até a auditoria.', url: 'https://exemplo.invalid/vetor/google', conflito_de_interesse: true },
    { id: '2026-11-19_anula_1', data: '2026-11-19', anula: '2026-11-10_p1_ue', porque: 'A meta não foi suspensa.', url: 'https://exemplo.invalid/vetor/correcao' },
    { id: '2026-09-01_p3_ue', data: '2026-09-01', item: 'p3', player: 'ue', de: 'centro_atlantico', para: 'soberanistas', forca: 3, tema: 'ordem',
      porque: 'Vetor de uma edição que não está no índice.', url: 'https://exemplo.invalid/vetor/setembro' });
}

/* N vetores de teste, um por dia para trás a partir de 19/11/2026, alternando UE e Trump. */
function muitosVetores(tabela, n) {
  const umDia = 86400000;
  for (let i = 0; i < n; i += 1) {
    const data = new Date(Date.UTC(2026, 10, 19) - i * umDia).toISOString().slice(0, 10);
    const player = i % 2 === 0 ? 'ue' : 'trump';
    tabela['dados/vetores.json'].vetores.push({
      id: data + '_p1_' + player, data, item: 'p1', player, de: player === 'ue' ? 'centro_atlantico' : 'soberanistas',
      para: player === 'ue' ? 'soberanistas' : 'eixo_revisionista', forca: 1 + (i % 3), tema: 'clima', porque: 'Vetor de teste número ' + (i + 1) + '.',
      url: 'https://exemplo.invalid/vetor/' + (i + 1)
    });
  }
}

const abreRegua = (hash, mudancas, opcoes) => abre(Object.assign({ hash, arquivos: arquivosDe35Dias(mudancas) }, opcoes || {}));

/* ----------------------------------------------------- cabeçalho comum */

test('Régua: título, as 4 abas como links comuns dentro de um nav, e a aba ativa', async () => {
  for (const [aba, nome] of [['partidos', 'Partidos'], ['players', 'Players'], ['veiculos', 'Veículos'], ['vetores', 'Vetores']]) {
    const m = await abreRegua('#/regua/' + aba);
    assert.equal(textoDe(m.um('h1')), 'Régua', aba);
    assert.equal(m.todos('h1').length, 1);
    assert.equal(m.documento.title, 'INFOCENARIUM · Régua');
    assert.equal(m.um('#nav a[aria-current="page"]').textContent, 'Régua');
    const abas = m.um('nav.abas');
    assert.equal(abas.getAttribute('aria-label'), 'Abas da Régua');
    assert.equal(abas.hasAttribute('role'), false, 'não é um conjunto de abas com setas');
    assert.deepEqual(abas.querySelectorAll('a').map((a) => [textoDe(a), a.getAttribute('href')]),
      [['Partidos', '#/regua/partidos'], ['Players', '#/regua/players'], ['Veículos', '#/regua/veiculos'], ['Vetores', '#/regua/vetores']]);
    assert.deepEqual(textos(abas.querySelectorAll('a[aria-current="page"]')), [nome]);
    assert.equal(abas.querySelectorAll('[role="tab"], [aria-selected]').length, 0);
    /* a ordem na página: título, abas, legenda, avisos e o conteúdo da aba */
    assert.deepEqual(m.um('.vista__corpo').children.map((el) => el.getAttribute('class')), ['abas', 'legenda', 'avisos', 'aba']);
    assert.equal(m.um('#vista').hasAttribute('aria-busy'), false);
    assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
  }
});

test('Régua: uma vista, um trabalho de cor: aqui só o DNA tem cor, e nada de nível de alerta', async () => {
  for (const aba of ['partidos', 'players', 'veiculos', 'vetores']) {
    const m = await abreRegua('#/regua/' + aba, comVetores);
    await m.abreTudo();
    assert.equal(m.um('main').querySelectorAll('.selo, .medidor, .alerta, .fita, [class*="nivel-"]').length, 0, aba);
    assert.equal(m.um('main').querySelectorAll('use[href^="#i-nivel-"]').length, 0, aba);
    assert.equal(m.um('main').querySelectorAll('.dna--tinta').length, 0, aba + ': na Régua o DNA vai com cor');
  }
});

test('Régua, legenda: descrição, aviso da régua, as 5 letras com o significado e a célula de virada', async () => {
  const m = await abreRegua('#/regua/partidos');
  const legenda = m.um('.legenda');
  assert.equal(textoDe(legenda.querySelector('.legenda__descricao')),
    'A régua do INFOCENARIUM: como cada player se posicionou em 5 temas (7 posições) e em que partido vota.');
  const aviso = legenda.querySelector('.aviso');
  assert.match(textoDe(aviso), /^O DNA e os partidos são classificação editorial de 20\/11\/2026/);
  assert.equal(aviso.querySelector('.aviso__rotulo'), null, 'o aviso da régua não tem rótulo: é o texto dela');
  assert.equal(aviso.querySelector('use').getAttribute('href'), '#i-aviso');
  const itens = legenda.querySelectorAll('.legenda__letras > li');
  assert.deepEqual(textos(itens), ['B polo azul', 'Y misto', 'R polo vermelho', 'W sem posição conhecida', 'K saiu do cargo',
    'B R Duas letras juntas (ex.: BR) indicam virada: a primeira é a posição de antes, a segunda é a atual.']);
  /* cada célula de exemplo leva a cor da letra; a letra é desenho para o leitor de tela, e o texto ao lado diz o que é */
  assert.deepEqual(itens.map((li) => li.querySelectorAll('.dna__metade').map((x) => x.getAttribute('class')).join('+')), [
    'dna__metade dna__metade--b', 'dna__metade dna__metade--y', 'dna__metade dna__metade--r', 'dna__metade dna__metade--w',
    'dna__metade dna__metade--k', 'dna__metade dna__metade--b+dna__metade dna__metade--r'
  ]);
  itens.forEach((li) => assert.equal(li.querySelector('.dna__celula').getAttribute('aria-hidden'), 'true'));
  /* o campo "cor" de valores não é usado: a cor vem do CSS */
  assert.equal(/amarelo|branco|preto/.test(textoDe(legenda)), false);
});

test('Régua, "COMO LER": começa fechada; aberta, traz os 2 polos, os 7 temas e a data de criação', async () => {
  const m = await abreRegua('#/regua/players');
  const botao = m.um('.legenda__abre button');
  assert.equal(textoDe(botao), 'COMO LER');
  assert.equal(botao.getAttribute('aria-expanded'), 'false');
  assert.equal(botao.getAttribute('type'), 'button');
  const corpo = m.documento.getElementById(botao.getAttribute('aria-controls'));
  assert.equal(aVista(corpo), false);
  assert.ok(corpo.classList.contains('dobra__corpo'));
  await m.clica(botao);
  assert.equal(botao.getAttribute('aria-expanded'), 'true');
  assert.equal(aVista(corpo), true);
  assert.deepEqual(textos(corpo.querySelectorAll('p.legenda__item')), [
    'B Polo institucional: freia na saúde, na IA, na fala e nas emissões; acolhe imigrantes.',
    'R Polo soberanista: libera economia, IA, fala e fósseis; restringe fronteiras.'
  ]);
  const tabela = corpo.querySelector('table');
  assert.equal(textoDe(tabela.querySelector('caption')), 'Temas da régua');
  assert.deepEqual(textos(tabela.querySelectorAll('thead th')), ['Sigla', 'Tema', 'polo azul', 'polo vermelho']);
  const linhas = tabela.querySelectorAll('tbody tr').map((tr) => textos(tr.children).join(' | '));
  assert.equal(linhas.length, 7);
  assert.equal(linhas[0], "PAN 1 | Pandemia (início) | alertou, 'fique em casa' | minimizou");
  assert.equal(linhas[5], 'CLIMA | Mudanças climáticas | cortar emissões, frear os fósseis | fósseis livres, minimizar o problema');
  assert.equal(linhas[6], 'FRONT | Imigração | acolher | restringir');
  assert.equal(textoDe(corpo.querySelector('.legenda__criada')), 'Régua criada em 20/11/2026.');
  assert.equal(corpo.querySelector('time').getAttribute('datetime'), '2026-11-20');
  /* Esc com o foco na dobra fecha e devolve o foco ao título dela */
  botao.focus();
  m.tecla('Escape');
  assert.equal(botao.getAttribute('aria-expanded'), 'false');
});

/* ------------------------------------------------------------ Partidos */

test('aba Partidos: 7 fichas, com sigla, nome, voto típico, postura, players e saldo de 30 dias', async () => {
  const m = await abreRegua('#/regua/partidos');
  assert.equal(textoDe(m.um('.aba h2')), 'Partidos');
  const fichas = m.todos('.partido');
  assert.deepEqual(fichas.map((f) => f.getAttribute('id')), ['partido-ordem_global', 'partido-centro_atlantico', 'partido-bancada_talento',
    'partido-soberanistas', 'partido-eixo_revisionista', 'partido-centrao', 'partido-independentes']);
  assert.deepEqual(textos(fichas.map((f) => f.querySelector('h3'))), ['Partido da Ordem Global', 'Centro Atlântico', 'Bancada do Talento',
    'Soberanistas', 'Eixo Revisionista', 'Centrão', 'Independentes']);
  assert.deepEqual(textos(fichas.map((f) => f.querySelector('.etiqueta--partido'))), ['OG', 'CA', 'BT', 'SO', 'ER', 'CE', 'IN']);
  fichas.forEach((f) => {
    assert.equal(f.querySelector('.etiqueta--partido').localName, 'span', 'na própria ficha a sigla não é link');
    assert.equal(f.querySelector('h3').getAttribute('tabindex'), '-1', 'a ficha é o alvo da rota do partido');
  });
  const og = fichas[0];
  assert.equal(og.querySelector('.etiqueta--partido abbr').getAttribute('title'), 'Partido da Ordem Global');
  assert.deepEqual(textos(og.querySelectorAll('.rotulo')), ['voto típico', 'diante da ordem', 'players (6)', 'saldo em 30 dias']);
  assert.match(textoDe(og), /diante da ordem Governo: defende a ordem como ela está\. Instituições multilaterais, imprensa tradicional/);
  /* players do partido, em lista corrida; cada nome leva à linha do player */
  const nomes = og.querySelectorAll('a[href^="#/regua/players/"]');
  assert.deepEqual(textos(nomes), ['OMS/ONU', 'The New York Times', 'Igreja Católica', 'TV Globo', 'Lula', 'Apple']);
  assert.equal(nomes[1].getAttribute('href'), '#/regua/players/nyt');
  /* saldo acumulado: a soma dos saldos dos 30 dias do índice, sem a edição de exemplo */
  assert.deepEqual(textos(fichas.map((f) => f.querySelector('.partido__saldo'))), ['saldo em 30 dias mais 11 +11', 'saldo em 30 dias menos 6 −6',
    'saldo em 30 dias menos 4 −4', 'saldo em 30 dias menos 1 −1', 'saldo em 30 dias mais 3 +3', 'saldo em 30 dias menos 2 −2', 'saldo em 30 dias mais 4 +4']);
  assert.equal(og.querySelector('.partido__saldo .mono').getAttribute('aria-hidden'), 'true');
});

test('aba Partidos: o voto típico é uma tira de 7 células com cor e com as siglas dos temas em cima; vazio é "sem voto típico"', async () => {
  const m = await abreRegua('#/regua/partidos');
  const tira = (id) => m.um('#partido-' + id + ' .dna');
  const bt = tira('bancada_talento');
  assert.equal(bt.getAttribute('class'), 'dna', 'sem a variante sem cor');
  assert.deepEqual(textos(bt.querySelectorAll('.dna__sigla')), ['PAN 1', 'PAN 2', 'IA 1', 'IA 2', 'FALA', 'CLIMA', 'FRONT']);
  bt.querySelectorAll('.dna__sigla').forEach((s) => assert.equal(s.getAttribute('aria-hidden'), 'true'));
  /* "B Y R R B Y B", na ordem dos temas da régua */
  assert.deepEqual(bt.querySelectorAll('.dna__metade').map((x) => x.getAttribute('class').replace('dna__metade dna__metade--', '')), ['b', 'y', 'r', 'r', 'b', 'y', 'b']);
  assert.deepEqual(textos(bt.querySelectorAll('.dna__celula .so-leitor')), ['Pandemia (início): polo azul', 'Pandemia (depois): misto',
    'IA (lançamento do ChatGPT): polo vermelho', 'IA (depois): polo vermelho', 'Moderação de conteúdo: polo azul', 'Mudanças climáticas: misto', 'Imigração: polo azul']);
  /* Centrão: "W Y R R W Y W" */
  assert.deepEqual(tira('centrao').querySelectorAll('.dna__metade').map((x) => x.textContent), ['W', 'Y', 'R', 'R', 'W', 'Y', 'W']);
  assert.equal(tira('independentes'), null);
  assert.match(textoDe(m.um('#partido-independentes')), /voto típico Sem voto típico: acompanha bancadas diferentes\. diante da ordem Votos pêndulo\./);
});

test('aba Partidos: abaixo das fichas, os 2 times com seus players e a regra dos players', async () => {
  const m = await abreRegua('#/regua/partidos');
  assert.deepEqual(textos(m.todos('.aba h2')), ['Partidos', 'TIMES']);
  const times = m.todos('.time');
  assert.deepEqual(textos(times.map((t) => t.querySelector('h3'))), ['Manutenção da ordem', 'Mudança da ordem']);
  assert.deepEqual(textos(times.map((t) => t.querySelector('.rotulo'))), ['players (14)', 'players (16)']);
  assert.match(textoDe(times[0]), /Quer preservar as instituições estabelecidas, a ordem internacional pós-1945 e o multilateralismo\./);
  assert.equal(times[0].querySelectorAll('a[href^="#/regua/players/"]').length, 14);
  assert.equal(times[1].querySelectorAll('a[href^="#/regua/players/"]').length, 16);
  /* a marca "time discutível" ao lado de quem tem o time em dúvida */
  assert.deepEqual(textos(times[0].querySelectorAll('.etiqueta')), ['time discutível', 'time discutível', 'time discutível']);
  assert.match(textoDe(times[0]), /Lula time discutível, Joe Biden,/);
  assert.equal(times[1].querySelectorAll('.etiqueta').length, 4, 'Boris, Modi, Anthropic e Meta');
  assert.equal(textoDe(m.um('.aba__regra')), 'Ninguém muda de partido. Movimento se registra em dados/vetores.json. A rotina pode acrescentar players novos ' +
    '(origem: rotina), nunca apagar nem reclassificar. Lista de players atualizada em 23/11/2026.');
});

test('#/regua/partidos/soberanistas: a ficha em foco; ficha que não existe abre a aba, com aviso', async () => {
  let m = await abreRegua('#/regua/partidos/soberanistas');
  const titulo = m.um('#partido-soberanistas h3');
  assert.equal(m.documento.activeElement, titulo);
  assert.deepEqual(m.documento.rolagens, [titulo]);
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
  assert.equal(m.janela.location.hash, '#/regua/partidos/soberanistas');

  m = await abreRegua('#/regua/partidos/partido_que_nao_existe');
  assert.equal(textoDe(m.um('#avisos-gerais .aviso')), AVISO_FICHA('partido_que_nao_existe'));
  assert.equal(textoDe(m.um('#anuncio')), AVISO_FICHA('partido_que_nao_existe'));
  assert.equal(m.todos('.partido').length, 7, 'a aba abre assim mesmo');
  assert.equal(m.um('.abas a[aria-current="page"]').textContent, 'Partidos');
  /* o aviso sai na rota seguinte */
  await m.vai('#/regua/partidos');
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
  /* nome que todo objeto herda não é ficha, em nenhuma aba */
  for (const aba of ['partidos', 'players', 'veiculos', 'vetores']) {
    for (const id of ['constructor', '__proto__']) {
      m = await abreRegua('#/regua/' + aba + '/' + id, comVetores);
      assert.equal(textoDe(m.um('#avisos-gerais .aviso')), AVISO_FICHA(id), aba);
      assert.equal(m.todos('button[aria-expanded="true"]').length, 0, aba);
    }
  }
});

test('Régua: link para outra ficha da mesma aba não remonta a aba: abre, rola e põe o foco', async () => {
  const m = await abreRegua('#/regua/partidos');
  const ficha = m.um('#partido-centrao');
  await m.clica(m.um('.legenda__abre button'));
  const pedidos = m.rede.pedidos.length;
  await m.vai('#/regua/partidos/centrao');
  assert.equal(m.um('#partido-centrao'), ficha, 'o mesmo elemento: a aba não foi montada de novo');
  assert.equal(m.documento.activeElement, ficha.querySelector('h3'));
  assert.equal(m.um('.legenda__abre button').getAttribute('aria-expanded'), 'true', 'o que o leitor abriu continua aberto');
  assert.equal(m.rede.pedidos.length, pedidos);
  /* sem ficha no endereço, o foco vai para o título da vista */
  await m.vai('#/regua/partidos');
  assert.equal(m.documento.activeElement, m.um('h1'));
  assert.deepEqual(m.janela.rolagens.slice(-1), [[0, 0]]);
  /* trocar de aba monta a outra aba */
  await m.vai('#/regua/players');
  assert.equal(m.um('#partido-centrao'), null);
  assert.equal(m.um('.abas a[aria-current="page"]').textContent, 'Players');
  assert.equal(m.documento.activeElement, m.um('h1'));
});

/* ------------------------------------------------------------- Players */

test('aba Players: matriz de verdade, com uma linha por player e um grupo de linhas por partido', async () => {
  const m = await abreRegua('#/regua/players');
  const matriz = m.um('table.matriz');
  assert.equal(matriz.getAttribute('role'), 'table');
  assert.equal(textoDe(matriz.querySelector('caption')), 'Players');
  assert.deepEqual(textos(matriz.querySelectorAll('thead th')),
    ['Nome', 'Tipo', 'Time', 'PAN 1', 'PAN 2', 'IA 1', 'IA 2', 'FALA', 'CLIMA', 'FRONT', 'Vetores', 'Abrir a linha']);
  matriz.querySelectorAll('thead th').forEach((th) => assert.equal(th.getAttribute('scope'), 'col'));
  assert.deepEqual(matriz.querySelectorAll('thead abbr').map((a) => a.getAttribute('title')), ['Pandemia (início)', 'Pandemia (depois)',
    'IA (lançamento do ChatGPT)', 'IA (depois)', 'Moderação de conteúdo', 'Mudanças climáticas', 'Imigração']);
  const grupos = matriz.querySelectorAll('tbody');
  assert.equal(grupos.length, 7);
  assert.deepEqual(textos(grupos.map((g) => g.querySelector('.matriz__grupo'))), ['OG Partido da Ordem Global (6)', 'CA Centro Atlântico (3)',
    'BT Bancada do Talento (5)', 'SO Soberanistas (5)', 'ER Eixo Revisionista (5)', 'CE Centrão (2)', 'IN Independentes (4)']);
  grupos.forEach((g) => {
    const cabeca = g.querySelector('.matriz__grupo th');
    assert.equal(cabeca.getAttribute('scope'), 'rowgroup');
    assert.equal(cabeca.getAttribute('colspan'), '12');
  });
  assert.equal(grupos[0].querySelector('.matriz__grupo a').getAttribute('href'), '#/regua/partidos/ordem_global');
  assert.deepEqual(grupos.map((g) => g.querySelectorAll('.matriz__linha').length), [6, 3, 5, 5, 5, 2, 4]);
  const linhas = matriz.querySelectorAll('.matriz__linha');
  assert.equal(linhas.length, 30);
  assert.deepEqual(linhas.slice(0, 7).map((tr) => tr.getAttribute('id')),
    ['player-oms_onu', 'player-nyt', 'player-igreja', 'player-globo', 'player-lula', 'player-apple', 'player-biden']);
  linhas.forEach((tr) => {
    assert.equal(tr.children.length, 12);
    assert.equal(tr.children[0].localName, 'th');
    assert.equal(tr.children[0].getAttribute('scope'), 'row');
    assert.equal(tr.querySelectorAll('.matriz__dna').length, 7);
    assert.ok(textoDe(tr.querySelector('button')).startsWith('Abrir: '));
  });
});

test('aba Players: nome, tipo, time com a marca "discutível", as 7 células de DNA e o número de vetores', async () => {
  const m = await abreRegua('#/regua/players', comVetores);
  const celulas = (id) => m.um('#player-' + id).children;
  const macron = celulas('macron');
  assert.equal(textoDe(macron[0]), 'Emmanuel Macron');
  assert.equal(textoDe(macron[1]), 'Governos e políticos', 'o nome do tipo vem da régua');
  assert.equal(textoDe(macron[2]), 'Manutenção da ordem');
  assert.deepEqual(textos(Array.from(macron).slice(3, 10).map((td) => td.querySelector('.so-leitor'))), ['Pandemia (início): polo azul',
    'Pandemia (depois): polo azul', 'IA (lançamento do ChatGPT): polo vermelho', 'IA (depois): polo vermelho', 'Moderação de conteúdo: polo azul',
    'Mudanças climáticas: polo azul', 'Imigração: virada de misto para polo vermelho']);
  /* a virada parte a célula em duas metades, antes e agora, cada uma com a sua cor */
  assert.deepEqual(macron[9].querySelectorAll('.dna__metade').map((x) => x.getAttribute('class') + '=' + x.textContent),
    ['dna__metade dna__metade--y=Y', 'dna__metade dna__metade--r=R']);
  assert.equal(macron[3].querySelector('.dna__metade').getAttribute('class'), 'dna__metade dna__metade--b');
  assert.equal(macron[3].querySelector('.dna__metade').getAttribute('aria-hidden'), 'true');
  /* a sigla do tema acompanha cada célula: na tela estreita ela fica em cima */
  assert.deepEqual(Array.from(macron).slice(3, 10).map((td) => td.getAttribute('data-rotulo')), ['PAN 1', 'PAN 2', 'IA 1', 'IA 2', 'FALA', 'CLIMA', 'FRONT']);
  /* time discutível e posição em dúvida */
  const boris = celulas('boris');
  assert.equal(textoDe(boris[2]), 'Mudança da ordem time discutível');
  assert.equal(textoDe(boris[7].querySelector('.so-leitor')), 'Moderação de conteúdo: polo azul, posição em dúvida');
  assert.equal(textoDe(boris[7].querySelector('.dna__duvida')), '?');
  assert.equal(boris[6].querySelector('.dna__duvida'), null);
  assert.equal(m.todos('.matriz__discutivel').length, 7);
  /* K: saiu do cargo. Na matriz toda, as letras batem com o arquivo */
  const letras = { b: 0, y: 0, r: 0, w: 0, k: 0 };
  CONGELADOS.players.players.forEach((p) => Object.keys(p.dna).forEach((tema) => p.dna[tema].split('').forEach((l) => { letras[l.toLowerCase()] += 1; })));
  Object.keys(letras).forEach((l) => assert.equal(m.todos('.matriz .dna__metade--' + l).length, letras[l], 'letra ' + l));
  assert.equal(letras.k, 1);
  assert.equal(m.todos('.matriz .dna__celula').length, 210);
  /* número de vetores: o anulado não conta, nem a entrada de anulação */
  assert.equal(textoDe(celulas('ue')[10]), '1', 'dos 2 vetores da UE, um foi anulado');
  assert.equal(textoDe(celulas('google')[10]), '1');
  assert.equal(textoDe(macron[10]), '0');
});

test('aba Players: a linha abre com a nota, as dúvidas, a origem e os vetores do player, com o anulado riscado', async () => {
  const m = await abreRegua('#/regua/players', comVetores);
  const linha = m.um('#player-ue');
  const botao = linha.querySelector('button');
  const detalhe = m.todos('.matriz__detalhe')[m.todos('.matriz__linha').indexOf(linha)];
  const corpo = m.documento.getElementById(botao.getAttribute('aria-controls'));
  assert.equal(detalhe.contains(corpo), true);
  assert.equal(detalhe.querySelector('td').getAttribute('colspan'), '12');
  assert.equal(botao.getAttribute('aria-expanded'), 'false');
  assert.equal(aVista(corpo), false);
  assert.equal(detalhe.getAttribute('aria-hidden'), 'true', 'fechada, a linha de detalhe está vazia: o leitor de tela a pula');
  await m.clica(botao);
  assert.equal(textoDe(botao), 'Fechar: União Europeia');
  assert.equal(aVista(corpo), true);
  assert.equal(detalhe.hasAttribute('aria-hidden'), false);
  assert.equal(m.janela.location.hash, '#/regua/players', 'abrir a linha não mexe no endereço');
  const paragrafos = textos(corpo.children);
  assert.match(paragrafos[0], /^AI Act, Lei de Serviços Digitais e Pacto Verde/);
  assert.equal(paragrafos[1], 'Da régua original');
  assert.equal(paragrafos[2], 'Vetores registrados (1)', 'a conta não inclui o anulado');
  /* os vetores do player, do mais novo para o mais antigo; o anulado fica à vista, riscado */
  const [anulado, antigo] = corpo.querySelectorAll('.vetor');
  assert.equal(corpo.querySelectorAll('.vetor').length, 2, 'os dois da UE: o anulado e o de setembro; o do Google é de outra linha');
  assert.equal(textoDe(anulado), 'Anulado: 10/11/2026 CA desloca-se para SO força 1 de 3 sinal CLIMA ANULADO principal 1 da edição de 10/11/2026 ' +
    'Suspendeu uma meta de corte de emissões. prova (abre em nova aba) Anulado em 19/11: A meta não foi suspensa. fonte da correção (abre em nova aba)');
  assert.ok(anulado.classList.contains('vetor--anulado'));
  assert.equal(anulado.querySelector('.vetor__cabeca').children[0].getAttribute('class'), 'so-leitor', 'o nome acessível começa com "Anulado:"');
  assert.equal(anulado.querySelector('.vetor__riscado').querySelectorAll('.etiqueta').some((e) => textoDe(e) === 'ANULADO'), false,
    'a etiqueta ANULADO fica fora do trecho riscado');
  assert.equal(anulado.querySelector('.vetor__anulacao a').getAttribute('href'), 'https://exemplo.invalid/vetor/correcao');
  assert.equal(anulado.querySelector('.vetor__cabeca a[href^="#/edicao"]').getAttribute('href'), '#/edicao/2026-11-10/p1');
  /* a edição de 01/09 não está no índice: o item aparece sem link */
  assert.match(textoDe(antigo), /^01\/09\/2026 CA desloca-se para SO força 3 de 3 difícil de desfazer ORDEM principal 3 Vetor de uma edição/);
  assert.equal(antigo.querySelectorAll('a[href^="#/edicao"]').length, 0);
  assert.equal(antigo.classList.contains('vetor--anulado'), false);
  /* player sem vetor e com posições em dúvida */
  await m.clica(m.um('#player-meloni button'));
  const meloni = m.documento.getElementById(m.um('#player-meloni button').getAttribute('aria-controls'));
  assert.match(textoDe(meloni), /posição em dúvida em: Pandemia \(início\), Moderação de conteúdo, Mudanças climáticas Da régua original Vetores registrados \(0\) Nenhum vetor registrado ainda\.$/);
  /* o vetor do Google leva a marca de conflito de interesse */
  await m.clica(m.um('#player-google button'));
  const google = m.documento.getElementById(m.um('#player-google button').getAttribute('aria-controls'));
  assert.match(textoDe(google.querySelector('.vetor__cabeca')), /^18\/11\/2026 BT desloca-se para OG força 2 de 3 ato reversível IA 2 CONFLITO DE INTERESSE radar 2 da edição de 18\/11\/2026$/);
});

test('aba Players: player que entrou pela rotina mostra a data, a justificativa com a fonte e as fontes das posições', async () => {
  const m = await abreRegua('#/regua/players/republica_exemplo', (t) => {
    t['dados/players.json'].players.push({
      id: 'republica_exemplo', nome: 'República de Exemplo', tipo: 'governo', partido: 'independentes', time: 'mudanca', time_discutivel: true,
      dna: { pandemia_inicio: 'W', pandemia_depois: 'Y', ia_inicio: 'W', ia_depois: 'B', moderacao: 'R', clima: 'W', imigracao: 'R' },
      dna_fontes: { pandemia_depois: 'https://exemplo.invalid/dna/pandemia', ia_depois: 'https://exemplo.invalid/dna/ia', moderacao: 'javascript:alert(1)' },
      duvidas: ['moderacao'], nota: 'País fictício.', justificativa: 'Entrou por ser alvo de três principais.', url: 'https://exemplo.invalid/justificativa',
      origem: 'rotina', incluido_em: '2026-11-19'
    });
  });
  const linha = m.um('#player-republica_exemplo');
  assert.equal(m.documento.activeElement, linha.children[0], 'a rota abre a linha e põe o foco no nome');
  assert.equal(linha.querySelector('button').getAttribute('aria-expanded'), 'true');
  assert.equal(textoDe(m.todos('.matriz__grupo')[6]), 'IN Independentes (5)');
  const corpo = m.documento.getElementById(linha.querySelector('button').getAttribute('aria-controls'));
  assert.deepEqual(textos(corpo.children).slice(0, 5), [
    'País fictício.',
    'posição em dúvida em: Moderação de conteúdo',
    'Entrou em 19/11/2026, pela rotina',
    'Por que entrou: Entrou por ser alvo de três principais. fonte (abre em nova aba)',
    'Fontes das posições: Pandemia (depois) (abre em nova aba) IA (depois) (abre em nova aba) Moderação de conteúdo'
  ]);
  assert.deepEqual(corpo.querySelectorAll('a.externo').map((a) => a.getAttribute('href')),
    ['https://exemplo.invalid/justificativa', 'https://exemplo.invalid/dna/pandemia', 'https://exemplo.invalid/dna/ia'],
    'a fonte com endereço que não é http fica como texto, sem link');
  assert.equal(corpo.querySelector('time').getAttribute('datetime'), '2026-11-19');
});

test('aba Players, filtros: partido, tipo e time por lista nativa; somam-se, vão para o endereço e a contagem é anunciada', async () => {
  const m = await abreRegua('#/regua/players');
  const [partido, tipo, time] = m.todos('.filtros select');
  assert.deepEqual([partido, tipo, time].map((s) => s.getAttribute('aria-label')), ['Filtrar por partido', 'Filtrar por tipo', 'Filtrar por time']);
  assert.deepEqual(textos(partido.querySelectorAll('option')), ['Todos os partidos', 'Partido da Ordem Global', 'Centro Atlântico', 'Bancada do Talento',
    'Soberanistas', 'Eixo Revisionista', 'Centrão', 'Independentes']);
  assert.deepEqual(textos(tipo.querySelectorAll('option')), ['Todos os tipos', 'Regimes autoritários', 'Governos e políticos', 'Instituições e mídia', 'Empresas e bilionários']);
  assert.deepEqual(textos(time.querySelectorAll('option')), ['Todos os times', 'Manutenção da ordem', 'Mudança da ordem']);
  assert.deepEqual(tipo.querySelectorAll('option').map((o) => o.getAttribute('value')), ['', 'regime', 'governo', 'instituicao', 'empresa']);
  const aVistaNaMatriz = () => m.todos('.matriz__linha').filter(aVista).map((tr) => tr.getAttribute('id').replace('player-', ''));
  assert.equal(aVistaNaMatriz().length, 30);
  assert.equal(textoDe(m.um('.filtros__contagem')), '');
  const pedidos = m.rede.pedidos.length;

  await m.escolhe(partido, 'centrao');
  assert.deepEqual(aVistaNaMatriz(), ['samsung', 'morgan_stanley']);
  assert.equal(m.janela.location.hash, '#/regua/players?partido=centrao');
  assert.deepEqual(m.historico, ['#/regua/players?partido=centrao'], 'sem criar passo no histórico');
  assert.equal(textoDe(m.um('.filtros__contagem')), '2 de 30 players');
  assert.equal(textoDe(m.um('#anuncio')), '2 de 30 players');
  assert.equal(m.rede.pedidos.length, pedidos, 'filtro não carrega nada');
  /* grupo sem linha à vista some; a linha de detalhe some junto com a linha */
  assert.deepEqual(m.todos('table.matriz tbody').map(aVista), [false, false, false, false, false, true, false]);
  assert.equal(m.todos('.matriz__detalhe').filter((tr) => !tr.hasAttribute('hidden')).length, 2);

  await m.escolhe(partido, '');
  await m.escolhe(tipo, 'empresa');
  assert.equal(aVistaNaMatriz().length, 11);
  await m.escolhe(time, 'mudanca');
  assert.deepEqual(aVistaNaMatriz(), ['altman', 'meta', 'huang_nvidia', 'musk', 'thiel', 'anthropic'],
    'a ordem não muda: a dos grupos (Bancada do Talento, Soberanistas, Independentes) e, dentro deles, a do arquivo');
  assert.equal(m.janela.location.hash, '#/regua/players?tipo=empresa&time=mudanca');
  await m.escolhe(partido, 'eixo_revisionista');
  assert.deepEqual(aVistaNaMatriz(), []);
  assert.equal(m.janela.location.hash, '#/regua/players?partido=eixo_revisionista&tipo=empresa&time=mudanca');
  const vazio = m.um('.filtros__vazio');
  assert.equal(aVista(vazio), true);
  assert.equal(textoDe(vazio), '0 de 30 players Limpar filtros');
  assert.equal(textoDe(m.um('#anuncio')), '0 de 30 players');
  await m.clica(vazio.querySelector('button'));
  assert.equal(aVistaNaMatriz().length, 30);
  assert.equal(aVista(vazio), false);
  assert.equal(m.janela.location.hash, '#/regua/players');
  assert.deepEqual([partido, tipo, time].map((s) => s.value), ['', '', '']);
});

test('aba Players, busca: ignora maiúscula e acento, procura no nome e no id, e recorta a cada tecla', async () => {
  const m = await abreRegua('#/regua/players');
  const campo = m.um('.filtros input');
  assert.equal(campo.getAttribute('type'), 'search');
  assert.equal(campo.getAttribute('maxlength'), '64');
  const rotulo = m.um('.filtros label');
  assert.equal(textoDe(rotulo), 'Buscar player');
  assert.equal(rotulo.getAttribute('for'), campo.getAttribute('id'), 'o campo tem rótulo à vista');
  const acha = async (texto) => { await m.escreve(campo, texto); return m.todos('.matriz__linha').filter(aVista).map((tr) => tr.getAttribute('id').replace('player-', '')); };
  const esperados = (texto) => queTem(CONGELADOS.players.players, texto).map((p) => p.id).sort();
  /* tecla a tecla */
  assert.deepEqual((await acha('m')).sort(), esperados('m'));
  assert.equal(esperados('m').length, 11);
  assert.deepEqual((await acha('ma')).sort(), esperados('ma'));
  assert.deepEqual(await acha('mac'), ['macron']);
  assert.equal(m.janela.location.hash, '#/regua/players?q=mac');
  assert.equal(textoDe(m.um('.filtros__contagem')), '1 de 30 players');
  assert.equal(textoDe(m.um('#anuncio')), '1 de 30 players');
  assert.equal(campo.value, 'mac', 'o campo não é reescrito enquanto o leitor digita');
  /* maiúscula e acento */
  assert.deepEqual(await acha('MAC'), ['macron']);
  assert.deepEqual(await acha('RÚSSIA'), ['russia', 'lukashenko'], 'acha "Rússia" e "Lukashenko (Bielorrússia)"');
  assert.deepEqual(await acha('russia'), ['russia', 'lukashenko']);
  assert.deepEqual(await acha('Irã'), ['ira']);
  assert.deepEqual(await acha('ira'), ['ira']);
  /* pelo id */
  assert.deepEqual(await acha('huang_nvidia'), ['huang_nvidia']);
  assert.deepEqual(await acha('oms_onu'), ['oms_onu']);
  /* espaço nas pontas não atrapalha; só espaço não é busca */
  assert.deepEqual(await acha('  macron '), ['macron']);
  assert.equal((await acha('   ')).length, 30);
  assert.equal(m.janela.location.hash, '#/regua/players');
  assert.equal(textoDe(m.um('.filtros__contagem')), '');
  /* nada encontrado */
  assert.deepEqual(await acha('zzz'), []);
  assert.equal(textoDe(m.um('.filtros__vazio')), 'Nada encontrado para "zzz". Limpar filtros');
  assert.equal(textoDe(m.um('#anuncio')), 'Nada encontrado para "zzz".');
  assert.equal(m.janela.location.hash, '#/regua/players?q=zzz');
  /* texto com marca e com aspas é só texto */
  assert.deepEqual(await acha('<img src=x onerror=alert(1)>'), []);
  assert.equal(textoDe(m.um('.filtros__vazio p')), 'Nada encontrado para "<img src=x onerror=alert(1)>".');
  assert.equal(m.um('.filtros__vazio').querySelectorAll('img').length, 0);
  assert.equal(m.janela.location.hash, '#/regua/players?q=%3Cimg%20src%3Dx%20onerror%3Dalert(1)%3E');
  await m.clica(m.um('.filtros__vazio button'));
  assert.equal(campo.value, '');
  assert.equal(m.todos('.matriz__linha').filter(aVista).length, 30);
});

test('aba Players: os filtros voltam do endereço; valor fora da lista é ignorado', async () => {
  let m = await abreRegua('#/regua/players?partido=centrao&tipo=empresa&time=manutencao&q=SAM');
  assert.deepEqual(m.todos('.matriz__linha').filter(aVista).map((tr) => tr.getAttribute('id')), ['player-samsung']);
  assert.deepEqual(m.todos('.filtros select').map((s) => s.value), ['centrao', 'empresa', 'manutencao']);
  assert.equal(m.um('.filtros input').value, 'SAM');
  assert.equal(textoDe(m.um('.filtros__contagem')), '1 de 30 players');
  assert.equal(m.janela.location.hash, '#/regua/players?partido=centrao&tipo=empresa&time=manutencao&q=SAM', 'o endereço fica como veio');
  assert.equal(m.historico.length, 0);

  m = await abreRegua('#/regua/players?partido=marte&tipo=planeta&time=azul&x=1');
  assert.equal(m.todos('.matriz__linha').filter(aVista).length, 30);
  assert.deepEqual(m.todos('.filtros select').map((s) => s.value), ['', '', '']);
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0, 'parâmetro torto não é endereço não encontrado');
  /* trocar o endereço com a aba aberta troca os filtros, sem montar a aba de novo */
  const linha = m.um('#player-trump');
  await m.vai('#/regua/players?time=manutencao&q=a');
  assert.equal(m.um('#player-trump'), linha);
  assert.equal(aVista(linha), false);
  const doTime = CONGELADOS.players.players.filter((p) => p.time === 'manutencao');
  assert.deepEqual(m.todos('.matriz__linha').filter(aVista).map((tr) => tr.getAttribute('id').replace('player-', '')).sort(),
    queTem(doTime, 'a').map((p) => p.id).sort());
  assert.equal(queTem(doTime, 'a').length, 9);
  assert.equal(m.um('.filtros input').value, 'a');
  await m.vai('#/regua/players');
  assert.equal(m.todos('.matriz__linha').filter(aVista).length, 30);
  assert.equal(m.um('.filtros input').value, '');
});

test('#/regua/players/macron: a linha aberta e em foco; filtro do mesmo endereço que a esconderia sai; id que não existe dá aviso', async () => {
  let m = await abreRegua('#/regua/players/macron');
  const linha = m.um('#player-macron');
  assert.equal(linha.querySelector('button').getAttribute('aria-expanded'), 'true');
  assert.equal(m.documento.activeElement, linha.children[0]);
  assert.equal(linha.children[0].getAttribute('tabindex'), '-1');
  assert.deepEqual(m.documento.rolagens, [linha.children[0]]);
  assert.equal(m.todos('button[aria-expanded="true"]').length, 1, 'abre só a linha pedida');
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
  /* outra ficha da mesma aba: a primeira continua aberta */
  await m.vai('#/regua/players/trump');
  assert.equal(m.documento.activeElement, m.um('#player-trump').children[0]);
  assert.equal(m.um('#player-macron'), linha);
  assert.equal(m.todos('button[aria-expanded="true"]').length, 2, 'abrir um não fecha o outro');

  m = await abreRegua('#/regua/players/macron?partido=centrao&q=zzz');
  assert.equal(aVista(m.um('#player-macron')), true, 'a ficha do endereço nunca fica escondida por filtro');
  assert.equal(m.todos('.matriz__linha').filter(aVista).length, 30);
  assert.deepEqual(m.todos('.filtros select').map((s) => s.value), ['', '', '']);
  /* filtro que não esconde a ficha pedida continua valendo */
  m = await abreRegua('#/regua/players/macron?partido=centro_atlantico');
  assert.deepEqual(m.todos('.matriz__linha').filter(aVista).map((tr) => tr.getAttribute('id')), ['player-biden', 'player-ue', 'player-macron']);
  assert.equal(m.um('#player-macron button').getAttribute('aria-expanded'), 'true');

  m = await abreRegua('#/regua/players/fulano');
  assert.equal(textoDe(m.um('#avisos-gerais .aviso')), AVISO_FICHA('fulano'));
  assert.equal(m.todos('.matriz__linha').length, 30);
  assert.equal(m.todos('button[aria-expanded="true"]').length, 0);
  /* o veículo "nyt" e o player "nyt" têm o mesmo id e rotas separadas */
  m = await abreRegua('#/regua/players/nyt');
  assert.equal(textoDe(m.documento.activeElement), 'The New York Times');
  assert.equal(m.documento.activeElement.localName, 'th');
});

/* ------------------------------------------------------------ Veículos */

test('aba Veículos: 146 linhas montadas em fatias, sem travar a página', async () => {
  const m = await abreRegua('#/regua/veiculos', null, { fatias: false });
  /* a primeira fatia já está na tela, com os filtros e os 7 títulos de grupo */
  assert.equal(m.todos('.veiculo').length, 24);
  assert.equal(m.um('.grupos').getAttribute('aria-busy'), 'true');
  assert.equal(m.todos('.grupo__titulo').length, 7);
  assert.equal(m.todos('.filtros select').length, 3);
  /* cada fatia seguinte vem num temporizador de zero milissegundos, e traz no máximo 24 linhas */
  const naTela = [];
  const marca = m.janela.setTimeout;
  m.janela.setTimeout = (funcao, ms) => { naTela.push([m.todos('.veiculo').length, ms]); return marca(funcao, ms); };
  await m.terminaFatias();
  m.janela.setTimeout = marca;
  assert.deepEqual(naTela, [[48, 0], [72, 0], [96, 0], [120, 0], [144, 0]]);
  assert.equal(m.todos('.veiculo').length, 146);
  assert.equal(m.um('.grupos').hasAttribute('aria-busy'), false);
  /* agrupada por lado, na ordem da régua, com a contagem no título */
  assert.deepEqual(textos(m.todos('.grupo__titulo')), ['OG Partido da Ordem Global (34)', 'CA Centro Atlântico (28)', 'BT Bancada do Talento (10)',
    'SO Soberanistas (25)', 'ER Eixo Revisionista (25)', 'CE Centrão (11)', 'IN Independentes (13)']);
  m.todos('.grupo__titulo').forEach((h) => assert.equal(h.localName, 'h3'));
  assert.deepEqual(m.todos('.grupo').map((g) => g.querySelectorAll('.veiculo').length), [34, 28, 10, 25, 25, 11, 13]);
  assert.deepEqual(m.todos('.veiculo').slice(0, 4).map((v) => v.getAttribute('id')), ['veiculo-acled', 'veiculo-agencia_brasil', 'veiculo-ai_now', 'veiculo-aiea']);
  assert.equal(new Set(m.todos('.veiculo').map((v) => v.getAttribute('id'))).size, 146, 'ids únicos');
  /* tudo começa fechado, e o conteúdo aberto já está no documento: a impressão não depende de script */
  assert.equal(m.todos('.veiculo button[aria-expanded="false"]').length, 146);
  assert.equal(m.todos('.veiculo__corpo.dobra__corpo[hidden]').length, 146);
});

test('aba Veículos: sair no meio da montagem para as fatias', async () => {
  const m = await abreRegua('#/regua/veiculos', null, { fatias: false });
  assert.equal(m.todos('.veiculo').length, 24);
  await m.vai('#/metodo', { fatias: false });
  const criados = m.documento.criados.length;
  await m.terminaFatias();
  assert.equal(m.documento.criados.length, criados, 'nenhuma linha de veículo foi montada depois da saída');
  assert.equal(textoDe(m.um('h1')), 'Método');
  /* voltar monta de novo, do começo */
  await m.vai('#/regua/veiculos');
  assert.equal(m.todos('.veiculo').length, 146);
});

test('aba Veículos: no topo, o aviso de mapa em rascunho; com a data de revisão, a linha "Mapa revisado em"', async () => {
  let m = await abreRegua('#/regua/veiculos');
  assert.equal(textoDe(m.um('.aba .aviso')), 'MAPA EM RASCUNHO Mapa em rascunho, ainda sem revisão do dono. O lado de cada veículo é classificação editorial.');
  assert.equal(textoDe(m.um('.aba .secao__intro')), 'Lado e fatos são coisas separadas: um veículo pode acertar o fato e servir a um lado pelo que escolhe cobrir.');
  assert.equal(/Mapa revisado em/.test(textoDe(m.um('.aba'))), false);

  m = await abreRegua('#/regua/veiculos', (t) => { t['dados/veiculos.json'].revisado_em = '2026-12-01'; });
  assert.equal(m.um('.aba .aviso'), null);
  assert.deepEqual(textos(m.todos('.aba .secao__intro')), ['Mapa revisado em 01/12/2026.',
    'Lado e fatos são coisas separadas: um veículo pode acertar o fato e servir a um lado pelo que escolhe cobrir.']);
  assert.equal(m.um('.aba .secao__intro time').getAttribute('datetime'), '2026-12-01');

  m = await abreRegua('#/regua/veiculos', (t) => { delete t['dados/veiculos.json'].revisado_em; });
  assert.match(textoDe(m.um('.aba .aviso')), /^MAPA EM RASCUNHO/, 'campo ausente vale como null');
});

test('aba Veículos, linha fechada: nome, país, tipo, sigla do lado, confiança no lado e confiabilidade nos fatos', async () => {
  const m = await abreRegua('#/regua/veiculos');
  const reuters = m.um('#veiculo-reuters');
  assert.equal(textoDe(reuters.querySelector('h4')), 'Reuters');
  assert.equal(textoDe(reuters.querySelector('.veiculo__meta')), 'Reino Unido/Canadá · agência', 'o tipo vem pelo rótulo da lista fechada');
  assert.equal(textoDe(reuters.querySelector('.marcas')), 'lado CE confiança no lado: baixa confiabilidade nos fatos: alta LADO INCERTO');
  assert.equal(reuters.querySelector('.etiqueta--partido').getAttribute('href'), '#/regua/partidos/centrao');
  assert.equal(reuters.querySelector('.etiqueta--partido abbr').getAttribute('title'), 'Centrão');
  assert.equal(textoDe(reuters.querySelector('button')), 'Abrir: Reuters');
  assert.equal(aVista(reuters.querySelector('.veiculo__corpo')), false);
  /* LADO INCERTO só com lado_confianca baixa: 54 dos 146 */
  const incertos = m.todos('.veiculo').filter((v) => textos(v.querySelectorAll('.veiculo__cabeca .etiqueta')).includes('LADO INCERTO'));
  assert.equal(incertos.length, 54);
  incertos.forEach((v) => assert.match(textoDe(v.querySelector('.marcas')), /confiança no lado: baixa/));
  assert.equal(textoDe(m.um('#veiculo-nyt .marcas')), 'lado OG confiança no lado: alta confiabilidade nos fatos: alta');
  assert.equal(textoDe(m.um('#veiculo-a16z .marcas')), 'lado SO confiança no lado: média confiabilidade nos fatos: baixa');
  assert.equal(textoDe(m.um('#veiculo-cset .veiculo__meta')), 'EUA · centro de estudos');
  /* o toque no cabeçalho não abre: aqui só o botão */
  await m.clica(reuters.querySelector('h4'));
  assert.equal(reuters.querySelector('button').getAttribute('aria-expanded'), 'false');
});

test('aba Veículos, linha aberta: idiomas, sites em texto, controle com a fonte, serve a, alvos, os porquês, o uso e os feeds', async () => {
  const m = await abreRegua('#/regua/veiculos');
  const nyt = m.um('#veiculo-nyt');
  await m.clica(nyt.querySelector('button'));
  assert.equal(textoDe(nyt.querySelector('button')), 'Fechar: The New York Times');
  assert.equal(m.janela.location.hash, '#/regua/veiculos', 'abrir a linha não mexe no endereço');
  const pares = nyt.querySelectorAll('.dados__par');
  assert.deepEqual(textos(pares.map((p) => p.querySelector('dt'))),
    ['País', 'Idiomas', 'Sites', 'Quem controla', 'Serve a', 'Alvos', 'Por que este lado', 'Sobre os fatos', 'Uso no monitor', 'Feeds']);
  const valor = (rotulo, de) => (de || nyt).querySelectorAll('.dados__par').find((p) => textoDe(p.querySelector('dt')) === rotulo).querySelector('dd');
  assert.equal(textoDe(valor('País')), 'EUA');
  assert.equal(textoDe(valor('Idiomas')), 'en');
  assert.equal(textoDe(valor('Sites')), 'nytimes.com');
  assert.equal(valor('Sites').querySelectorAll('a').length, 0, 'nome de site nunca vira link');
  assert.equal(textoDe(valor('Quem controla')),
    'Empresa de capital aberto (NYSE) controlada pela família Ochs-Sulzberger, por ações de classe B. fonte (abre em nova aba)');
  assert.equal(valor('Quem controla').querySelector('a').getAttribute('href'), 'https://en.wikipedia.org/wiki/The_New_York_Times_Company');
  assert.equal(valor('Quem controla').querySelector('a').getAttribute('rel'), 'noopener noreferrer');
  /* serve a e alvos: partido vira sigla com link para a ficha; player, o nome com link para a linha */
  assert.equal(textoDe(valor('Serve a')), 'OG, CA');
  assert.deepEqual(valor('Serve a').querySelectorAll('a').map((a) => a.getAttribute('href')), ['#/regua/partidos/ordem_global', '#/regua/partidos/centro_atlantico']);
  assert.equal(textoDe(valor('Alvos')), 'Donald Trump, Elon Musk, Sam Altman (OpenAI)');
  assert.deepEqual(valor('Alvos').querySelectorAll('a').map((a) => a.getAttribute('href')), ['#/regua/players/trump', '#/regua/players/musk', '#/regua/players/altman']);
  assert.match(textoDe(valor('Por que este lado')), /^Já classificado na régua como player da Ordem Global\./);
  assert.match(textoDe(valor('Sobre os fatos')), /^Apuração própria forte/);
  assert.ok(textoDe(valor('Uso no monitor')).length > 10);

  /* listas vazias levam travessão */
  const reuters = m.um('#veiculo-reuters');
  await m.clica(reuters.querySelector('button'));
  assert.equal(textoDe(valor('Alvos', reuters)), '—');
  assert.equal(textoDe(valor('Serve a', reuters)), 'CE');
  assert.equal(textoDe(valor('Idiomas', reuters)), 'en, pt, es, fr, de, ar, ja, zh');
});

test('aba Veículos, feeds: seção, formato, conferido ou não, nota e endereço; sem feed, "Nenhum feed."; feeds_nota em texto simples', async () => {
  const m = await abreRegua('#/regua/veiculos');
  const feedsDe = (id) => m.um('#veiculo-' + id).querySelectorAll('.dados__par').find((p) => textoDe(p.querySelector('dt')) === 'Feeds').querySelector('dd');
  /* com feed */
  const a16z = feedsDe('a16z');
  assert.equal(a16z.querySelectorAll('.feed').length, 1);
  assert.equal(textoDe(a16z.querySelector('.feed')), 'ia rss não conferido Não aberto na conferência de 20/11/2026: o site respondeu 403 (acesso barrado). https://a16z.com/feed/ (abre em nova aba)');
  const link = a16z.querySelector('a.externo');
  assert.equal(link.getAttribute('href'), 'https://a16z.com/feed/');
  assert.equal(link.getAttribute('target'), '_blank');
  assert.equal(a16z.querySelector('.feed__nota'), null, 'sem feeds_nota, nada a mais');
  assert.equal(feedsDe('g1_globo').querySelectorAll('.feed').length, 3);
  assert.deepEqual(textos(feedsDe('g1_globo').querySelectorAll('.feed .marcas')), ['mundo rss não conferido', 'política rss não conferido', 'tecnologia rss não conferido']);
  assert.match(textoDe(feedsDe('agencia_brasil').querySelector('.feed .marcas')), /^últimas rss conferido$/);
  /* sem feed: a frase e, abaixo, a nota de feeds, em texto simples */
  const reuters = feedsDe('reuters');
  assert.equal(reuters.querySelectorAll('.feed').length, 0);
  assert.deepEqual(textos(reuters.children), ['Nenhum feed.',
    'Sem feed RSS público oficial ativo. Ler a página de últimas notícias, https://www.reuters.com/world/, que não abriu para leitura automática em 20/11/2026.']);
  assert.equal(reuters.querySelectorAll('a').length, 0, 'o endereço dentro da nota não vira link: não foi conferido');
  assert.equal(reuters.querySelector('.feed__nota').children.length, 0, 'a nota é um nó de texto só');
  /* a nota aparece abaixo dos feeds também quando há feed */
  const comOsDois = m.todos('.veiculo').filter((v) => v.querySelector('.feed') && v.querySelector('.feed__nota'));
  assert.ok(comOsDois.length > 0);
  const dd = comOsDois[0].querySelector('.feed__nota').parentNode;
  assert.equal(dd.children[dd.children.length - 1].getAttribute('class'), 'feed__nota', 'abaixo dos feeds');
  /* as contas batem com o arquivo: 77 notas de feeds, 27 veículos sem feed, 140 feeds */
  assert.equal(m.todos('.feed__nota').length, 77);
  assert.equal(m.todos('.veiculo').filter((v) => /Nenhum feed\./.test(textoDe(v))).length, 27);
  assert.equal(m.todos('.feed').length, 140);
  assert.equal(m.todos('.feed').filter((f) => /(^| )conferido$/.test(textoDe(f.querySelector('.marcas'))) && !/não conferido$/.test(textoDe(f.querySelector('.marcas')))).length, 75);
});

test('aba Veículos, filtros: lado, fatos e tipo por lista nativa; somam-se, vão para o endereço e a contagem é anunciada', async () => {
  const m = await abreRegua('#/regua/veiculos');
  const [lado, fatos, tipo] = m.todos('.filtros select');
  assert.deepEqual([lado, fatos, tipo].map((s) => s.getAttribute('aria-label')), ['Filtrar por lado', 'Filtrar por confiabilidade nos fatos', 'Filtrar por tipo']);
  assert.deepEqual(textos(lado.querySelectorAll('option')), ['Todos os lados', 'Partido da Ordem Global', 'Centro Atlântico', 'Bancada do Talento',
    'Soberanistas', 'Eixo Revisionista', 'Centrão', 'Independentes']);
  assert.deepEqual(textos(fatos.querySelectorAll('option')), ['Qualquer confiabilidade', 'alta', 'média', 'baixa']);
  assert.deepEqual(textos(tipo.querySelectorAll('option')), ['Todos os tipos', 'agência', 'estatal', 'público', 'privado', 'plataforma', 'oficial', 'centro de estudos', 'dados']);
  const aVistaNaLista = () => m.todos('.veiculo').filter(aVista).map((v) => v.getAttribute('id').replace('veiculo-', ''));
  const total = m.documento.criados.length;

  await m.escolhe(lado, 'centrao');
  assert.equal(aVistaNaLista().length, 11);
  assert.equal(m.janela.location.hash, '#/regua/veiculos?lado=centrao');
  assert.equal(textoDe(m.um('.filtros__contagem')), '11 de 146 veículos');
  assert.equal(textoDe(m.um('#anuncio')), '11 de 146 veículos');
  assert.deepEqual(m.todos('.grupo').map(aVista), [false, false, false, false, false, true, false], 'grupo sem linha à vista some');
  await m.escolhe(fatos, 'alta');
  assert.deepEqual(aVistaNaLista(), ['bloomberg', 'nikkei_asia', 'reuters', 'straits_times', 'the_information', 'valor', 'wsj']);
  await m.escolhe(tipo, 'agencia');
  assert.deepEqual(aVistaNaLista(), ['reuters']);
  assert.equal(m.janela.location.hash, '#/regua/veiculos?lado=centrao&fatos=alta&tipo=agencia');
  assert.equal(textoDe(m.um('.filtros__contagem')), '1 de 146 veículos');
  /* filtrar esconde e mostra: nenhuma linha é montada de novo */
  assert.ok(m.documento.criados.length - total < 10, 'o recorte não recria a lista');
  await m.escolhe(lado, '');
  await m.escolhe(fatos, '');
  assert.equal(aVistaNaLista().length, 15, 'as 15 agências');
  await m.escolhe(tipo, 'publico');
  assert.deepEqual(aVistaNaLista(), ['bbc', 'bbc_brasil']);
  await m.escolhe(tipo, '');
  assert.equal(aVistaNaLista().length, 146);
  assert.equal(m.janela.location.hash, '#/regua/veiculos');
  /* as contagens por confiabilidade batem com o arquivo */
  for (const [valor, quantos] of [['alta', 54], ['media', 68], ['baixa', 24]]) {
    await m.escolhe(fatos, valor);
    assert.equal(aVistaNaLista().length, quantos, valor);
  }
});

test('aba Veículos, busca: ignora maiúscula e acento, procura no nome e no id; sem resultado, a frase e "Limpar filtros"', async () => {
  const m = await abreRegua('#/regua/veiculos');
  const campo = m.um('.filtros input');
  assert.equal(textoDe(m.um('.filtros label')), 'Buscar veículo');
  const acha = async (texto) => { await m.escreve(campo, texto); return m.todos('.veiculo').filter(aVista).map((v) => v.getAttribute('id').replace('veiculo-', '')); };
  const veiculos = CONGELADOS.veiculos.veiculos;
  const agencias = queTem(veiculos, 'agencia').map((v) => v.id).sort();
  assert.deepEqual(agencias, ['agencia_brasil', 'aie', 'aiea', 'anadolu', 'belta', 'irna', 'kcna', 'xinhua']);
  assert.deepEqual((await acha('agencia')).sort(), agencias, 'sem acento, acha "Agência"');
  assert.deepEqual((await acha('AGÊNCIA')).sort(), agencias);
  assert.deepEqual((await acha('Agência')).sort(), agencias);
  assert.equal(m.janela.location.hash, '#/regua/veiculos?q=Ag%C3%AAncia');
  assert.equal(textoDe(m.um('.filtros__contagem')), '8 de 146 veículos');
  assert.deepEqual(await acha('bbc'), ['bbc', 'bbc_brasil']);
  assert.deepEqual(await acha('x_plataforma'), ['x_plataforma'], 'pelo id');
  /* a busca soma com as listas */
  await m.escolhe(m.todos('.filtros select')[2], 'agencia');
  assert.deepEqual((await acha('agencia')).sort(), queTem(veiculos.filter((v) => v.tipo === 'agencia'), 'agencia').map((v) => v.id).sort());
  assert.deepEqual((await acha('agencia')).sort(), ['anadolu', 'belta', 'irna', 'kcna', 'xinhua'], 'as que são do tipo agência e têm "agência" no nome');
  assert.equal(m.janela.location.hash, '#/regua/veiculos?tipo=agencia&q=agencia');
  assert.deepEqual(await acha('zzz'), []);
  const vazio = m.um('.filtros__vazio');
  assert.equal(aVista(vazio), true);
  assert.equal(textoDe(vazio), 'Nada encontrado para "zzz". Limpar filtros');
  assert.equal(m.todos('.grupo').filter(aVista).length, 0);
  await m.clica(vazio.querySelector('button'));
  assert.equal(m.todos('.veiculo').filter(aVista).length, 146);
  assert.equal(m.janela.location.hash, '#/regua/veiculos');
});

test('aba Veículos: os filtros do endereço já valem na primeira fatia, e a contagem conta a lista inteira', async () => {
  const m = await abreRegua('#/regua/veiculos?lado=eixo_revisionista&fatos=baixa&q=a', null, { fatias: false });
  assert.equal(m.todos('.veiculo').length, 24, 'só a primeira fatia, toda do primeiro grupo');
  assert.equal(m.todos('.veiculo').filter(aVista).length, 0);
  const contagem = textoDe(m.um('.filtros__contagem'));
  assert.match(contagem, /^\d+ de 146 veículos$/);
  assert.deepEqual(m.todos('.filtros select').map((s) => s.value), ['eixo_revisionista', 'baixa', '']);
  assert.equal(m.um('.filtros input').value, 'a');
  await m.terminaFatias();
  const aVistaNaLista = m.todos('.veiculo').filter(aVista);
  assert.equal(textoDe(m.um('.filtros__contagem')), contagem, 'a contagem não muda com a montagem');
  assert.equal(aVistaNaLista.length, Number(contagem.split(' ')[0]));
  assert.ok(aVistaNaLista.length > 0);
  aVistaNaLista.forEach((v) => assert.match(textoDe(v.querySelector('.marcas')), /^lado ER .*confiabilidade nos fatos: baixa/));
  /* valor fora da lista é ignorado */
  const m2 = await abreRegua('#/regua/veiculos?lado=marte&fatos=otima&tipo=blog');
  assert.equal(m2.todos('.veiculo').filter(aVista).length, 146);
  assert.equal(m2.todos('#avisos-gerais .aviso').length, 0);
});

test('#/regua/veiculos/reuters: a linha aberta e em foco, depois da última fatia; id que não existe dá aviso', async () => {
  let m = await abreRegua('#/regua/veiculos/reuters', null, { fatias: false });
  assert.equal(m.um('#veiculo-reuters'), null, 'a Reuters está no sexto grupo: ainda não foi montada');
  assert.equal(m.documento.activeElement, m.documento.body);
  await m.terminaFatias();
  const reuters = m.um('#veiculo-reuters');
  assert.equal(reuters.querySelector('button').getAttribute('aria-expanded'), 'true');
  assert.equal(m.documento.activeElement, reuters.querySelector('h4'));
  assert.equal(reuters.querySelector('h4').getAttribute('tabindex'), '-1');
  assert.deepEqual(m.documento.rolagens, [reuters.querySelector('h4')]);
  assert.equal(m.todos('.veiculo button[aria-expanded="true"]').length, 1);
  /* outra ficha da mesma aba, já montada: sem remontar */
  await m.vai('#/regua/veiculos/xinhua');
  assert.equal(m.um('#veiculo-reuters'), reuters);
  assert.equal(m.documento.activeElement, m.um('#veiculo-xinhua h4'));

  m = await abreRegua('#/regua/veiculos/reuters?lado=soberanistas');
  assert.equal(aVista(m.um('#veiculo-reuters')), true, 'a ficha do endereço nunca fica escondida por filtro');
  assert.equal(m.todos('.filtros select')[0].value, '');
  assert.equal(m.todos('.veiculo').filter(aVista).length, 146);

  m = await abreRegua('#/regua/veiculos/jornal_que_nao_existe');
  assert.equal(textoDe(m.um('#avisos-gerais .aviso')), AVISO_FICHA('jornal_que_nao_existe'));
  assert.equal(m.todos('.veiculo').length, 146);
});

/* ------------------------------------------------------------- Vetores */

test('aba Vetores: com o registro vazio, a regra, o texto fixo e "Nenhum vetor registrado ainda."', async () => {
  const m = await abreRegua('#/regua/vetores');
  assert.equal(textoDe(m.um('.aba h2')), 'REGISTRO DE VETORES');
  assert.deepEqual(textos(m.todos('.aba .secao__intro')), [
    'O registro só cresce. Vetor errado não se apaga: é anulado, e fica à vista.',
    'Registro que só cresce. Cada entrada diz para qual partido um player se deslocou, com que força (1 a 3) e por causa de qual notícia. O partido do player não muda.'
  ]);
  assert.equal(textoDe(m.um('.aba .vazio')), 'Nenhum vetor registrado ainda.');
  assert.equal(m.todos('.aba table, .aba button').length, 0);
});

test('aba Vetores: a tabela do registro, do mais novo para o mais antigo, com a âncora de cada linha', async () => {
  const m = await abreRegua('#/regua/vetores', comVetores);
  const tabela = m.um('.aba table');
  assert.ok(tabela.classList.contains('tabela--larga'));
  assert.equal(textoDe(tabela.querySelector('caption')), 'REGISTRO DE VETORES');
  assert.deepEqual(textos(tabela.querySelectorAll('thead th')), ['Data', 'Player', 'De', 'Para', 'Força', 'Tema', 'Por quê', 'Prova', 'Item']);
  const linhas = tabela.querySelectorAll('tbody tr');
  /* a entrada de anulação não vira linha */
  assert.deepEqual(linhas.map((tr) => tr.getAttribute('id')), ['vetor-2026-11-18_r2_google', 'vetor-2026-11-10_p1_ue', 'vetor-2026-09-01_p3_ue']);
  assert.equal(textoDe(m.um('.filtros__contagem')), '3 de 3 vetores');
  assert.equal(aVista(m.um('.aba__mais button')), false, 'não há mais o que mostrar');
  assert.equal(aVista(m.todos('.aba .filtros button')[0]), false, 'sem filtro, não há o que limpar');
  const celulas = textos(linhas[0].children);
  assert.deepEqual(celulas, ['18/11/2026', 'Google', 'BT', 'OG', 'força 2 de 3 ato reversível', 'IA 2',
    'Adiou um modelo até a auditoria. CONFLITO DE INTERESSE', 'prova (abre em nova aba)', 'radar 2 da edição de 18/11/2026']);
  assert.equal(linhas[0].children[1].querySelector('a').getAttribute('href'), '#/regua/players/google');
  assert.equal(linhas[0].children[2].querySelector('a').getAttribute('href'), '#/regua/partidos/bancada_talento');
  assert.equal(linhas[0].children[3].querySelector('a').getAttribute('href'), '#/regua/partidos/ordem_global');
  assert.equal(linhas[0].children[5].querySelector('abbr').getAttribute('title'), 'IA (depois)');
  assert.equal(linhas[0].children[7].querySelector('a').getAttribute('href'), 'https://exemplo.invalid/vetor/google');
  assert.equal(linhas[0].children[8].querySelector('a').getAttribute('href'), '#/edicao/2026-11-18/r2', 'a edição está no índice: o item vira link');
  assert.equal(linhas[0].children[0].getAttribute('tabindex'), '-1', 'a linha é o alvo da rota do vetor');
  assert.deepEqual(linhas[0].children.map((c) => c.getAttribute('data-rotulo')), ['Data', 'Player', 'De', 'Para', 'Força', 'Tema', 'Por quê', 'Prova', 'Item']);
  /* tema extra "ordem" e edição fora do índice (item sem link) */
  assert.deepEqual(textos(linhas[2].children).slice(4), ['força 3 de 3 difícil de desfazer', 'ORDEM', 'Vetor de uma edição que não está no índice.',
    'prova (abre em nova aba)', 'principal 3']);
  assert.equal(linhas[2].children[8].querySelectorAll('a').length, 0);
});

test('aba Vetores: no mesmo dia, o que entrou por último no registro vem antes, na tabela e na linha aberta do player', async () => {
  const doDia = (id, player, porque) => ({ id, data: '2026-11-18', item: id.split('_')[1], player, de: 'centro_atlantico', para: 'soberanistas',
    forca: 1, tema: 'clima', porque, url: 'https://exemplo.invalid/vetor/' + id });
  const mudancas = (t) => t['dados/vetores.json'].vetores.push(
    doDia('2026-11-18_p1_ue', 'ue', 'Entrou primeiro.'), doDia('2026-11-18_r3_ue', 'ue', 'Entrou depois.'));
  let m = await abreRegua('#/regua/vetores', mudancas);
  assert.deepEqual(m.todos('.aba tbody tr').map((tr) => tr.getAttribute('id')), ['vetor-2026-11-18_r3_ue', 'vetor-2026-11-18_p1_ue']);
  m = await abreRegua('#/regua/players/ue', mudancas);
  const abertos = m.todos('.vetor__porque').filter((p) => aVista(p));
  assert.deepEqual(textos(abertos), ['Entrou depois.', 'Entrou primeiro.']);
});

test('aba Vetores: o anulado fica riscado, com ANULADO, a data, o motivo e a fonte da correção sem risco', async () => {
  const m = await abreRegua('#/regua/vetores', comVetores);
  const linha = m.um('#vetor-2026-11-10_p1_ue');
  assert.ok(linha.classList.contains('vetor--anulado'));
  assert.equal(aVista(linha), true, 'vetor anulado nunca é escondido');
  assert.equal(textoDe(linha.children[0]), 'Anulado: 10/11/2026');
  assert.equal(linha.children[0].querySelector('.so-leitor').textContent, 'Anulado: ', 'o nome acessível da linha começa com "Anulado:"');
  /* da data ao tema, e o porquê, vão dentro do trecho riscado */
  linha.children.slice(0, 6).forEach((celula) => assert.equal(celula.querySelectorAll('.vetor__riscado').length, 1));
  const porque = linha.children[6];
  assert.equal(textoDe(porque), 'Suspendeu uma meta de corte de emissões. ANULADO Anulado em 19/11: A meta não foi suspensa. fonte da correção (abre em nova aba)');
  assert.equal(textoDe(porque.querySelector('.vetor__riscado')), 'Suspendeu uma meta de corte de emissões.');
  const foraDoRisco = porque.querySelectorAll('.etiqueta, .vetor__anulacao');
  assert.deepEqual(textos(foraDoRisco), ['ANULADO', 'Anulado em 19/11: A meta não foi suspensa. fonte da correção (abre em nova aba)']);
  foraDoRisco.forEach((el) => assert.equal(porque.querySelector('.vetor__riscado').contains(el), false));
  assert.equal(porque.querySelector('.vetor__anulacao a').getAttribute('href'), 'https://exemplo.invalid/vetor/correcao');
  assert.equal(porque.querySelector('.vetor__anulacao time').getAttribute('datetime'), '2026-11-19');
  /* a linha que não foi anulada não tem nada riscado */
  assert.equal(m.um('#vetor-2026-11-18_r2_google').querySelectorAll('.vetor__riscado').length, 0);
  assert.equal(m.todos('.vetor--anulado').length, 1);
});

test('aba Vetores: 50 linhas por vez, com "Mostrar mais 50" e a contagem anunciada', async () => {
  const m = await abreRegua('#/regua/vetores', (t) => muitosVetores(t, 120));
  const linhas = () => m.todos('.aba tbody tr');
  const mais = m.um('.aba__mais button');
  assert.equal(linhas().length, 50);
  assert.equal(textoDe(m.um('.filtros__contagem')), '50 de 120 vetores');
  assert.equal(textoDe(mais), 'Mostrar mais 50');
  assert.equal(aVista(mais), true);
  assert.equal(linhas()[0].getAttribute('id'), 'vetor-2026-11-19_p1_ue', 'o mais novo primeiro');
  assert.equal(linhas()[49].getAttribute('id'), 'vetor-2026-10-01_p1_trump');
  const primeira = linhas()[0];
  await m.clica(mais);
  assert.equal(linhas().length, 100);
  assert.equal(linhas()[0], primeira, 'as linhas que já estavam na tela ficam: só entram as novas');
  assert.equal(textoDe(m.um('.filtros__contagem')), '100 de 120 vetores');
  assert.equal(textoDe(m.um('#anuncio')), '100 de 120 vetores');
  assert.equal(aVista(mais), true);
  await m.clica(mais);
  assert.equal(linhas().length, 120);
  assert.equal(textoDe(m.um('.filtros__contagem')), '120 de 120 vetores');
  assert.equal(aVista(mais), false, 'acabou: o botão some');
  assert.equal(new Set(linhas().map((tr) => tr.getAttribute('id'))).size, 120);
  const datas = linhas().map((tr) => tr.querySelector('time').getAttribute('datetime'));
  assert.deepEqual(datas, datas.slice().sort().reverse(), 'do mais novo para o mais antigo');
});

test('#/regua/vetores?player=ue: só os vetores de um player, com "Limpar filtros"; player que não existe é ignorado', async () => {
  let m = await abreRegua('#/regua/vetores?player=ue', (t) => muitosVetores(t, 120));
  const linhas = () => m.todos('.aba tbody tr');
  assert.equal(linhas().length, 50);
  linhas().forEach((tr) => assert.equal(textoDe(tr.children[1]), 'União Europeia'));
  assert.equal(textoDe(m.um('.filtros__contagem')), '50 de 120 vetores');
  await m.clica(m.um('.aba__mais button'));
  assert.equal(linhas().length, 60, 'a UE tem 60 dos 120');
  assert.equal(aVista(m.um('.aba__mais button')), false);
  const limpar = m.todos('.aba .filtros button')[0];
  assert.equal(textoDe(limpar), 'Limpar filtros');
  assert.equal(aVista(limpar), true);
  await m.clica(limpar);
  assert.equal(linhas().length, 50);
  assert.equal(textoDe(linhas()[1].children[1]), 'Donald Trump');
  assert.equal(m.janela.location.hash, '#/regua/vetores');
  assert.equal(aVista(limpar), false);
  assert.equal(textoDe(m.um('#anuncio')), '50 de 120 vetores');

  /* player que existe e não tem vetor: nenhuma linha, e a contagem diz */
  m = await abreRegua('#/regua/vetores?player=macron', (t) => muitosVetores(t, 12));
  assert.equal(m.todos('.aba tbody tr').length, 0);
  assert.equal(aVista(m.um('.aba table')), false);
  assert.equal(textoDe(m.um('.filtros__contagem')), '0 de 12 vetores');
  assert.equal(aVista(m.todos('.aba .filtros button')[0]), true);
  /* player que não existe: o filtro é ignorado */
  m = await abreRegua('#/regua/vetores?player=fulano', (t) => muitosVetores(t, 12));
  assert.equal(m.todos('.aba tbody tr').length, 12);
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
});

test('#/regua/vetores/ID: a linha em foco, mesmo além das 50 primeiras; filtro que a esconderia sai; id que não existe dá aviso', async () => {
  let m = await abreRegua('#/regua/vetores/2026-09-10_p1_ue', (t) => muitosVetores(t, 120));
  /* 10/09 é o 71º mais novo: entram 100 linhas */
  assert.equal(m.todos('.aba tbody tr').length, 100);
  const linha = m.um('#vetor-2026-09-10_p1_ue');
  assert.equal(m.documento.activeElement, linha.children[0]);
  assert.deepEqual(m.documento.rolagens, [linha.children[0]]);
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);

  m = await abreRegua('#/regua/vetores/2026-11-19_p1_ue?player=trump', (t) => muitosVetores(t, 120));
  assert.equal(m.documento.activeElement, m.um('#vetor-2026-11-19_p1_ue').children[0], 'a linha do endereço nunca fica escondida por filtro');
  assert.equal(aVista(m.todos('.aba .filtros button')[0]), false);
  /* o filtro que não esconde a linha continua valendo */
  m = await abreRegua('#/regua/vetores/2026-11-17_p1_ue?player=ue', (t) => muitosVetores(t, 120));
  assert.equal(m.documento.activeElement, m.um('#vetor-2026-11-17_p1_ue').children[0]);
  m.todos('.aba tbody tr').forEach((tr) => assert.equal(textoDe(tr.children[1]), 'União Europeia'));

  m = await abreRegua('#/regua/vetores/2026-01-01_p1_ue', comVetores);
  assert.equal(textoDe(m.um('#avisos-gerais .aviso')), AVISO_FICHA('2026-01-01_p1_ue'));
  assert.equal(m.todos('.aba tbody tr').length, 3);
  /* a entrada de anulação não é linha: o id dela não é âncora */
  m = await abreRegua('#/regua/vetores/2026-11-19_anula_1', comVetores);
  assert.equal(textoDe(m.um('#avisos-gerais .aviso')), AVISO_FICHA('2026-11-19_anula_1'));
  /* com o registro vazio, toda ficha é "não encontrada" */
  m = await abreRegua('#/regua/vetores/2026-11-20_p1_ue');
  assert.equal(textoDe(m.um('#avisos-gerais .aviso')), AVISO_FICHA('2026-11-20_p1_ue'));
});

test('do Painel para a Régua: os links de partido, de player, de veículo e de vetor chegam à ficha', async () => {
  const tabela = arquivosDe35Dias((t) => {
    t['dados/vetores.json'].vetores.push({ id: '2026-11-17_p3_ue', data: '2026-11-17', item: 'p3', player: 'ue', de: 'centro_atlantico', para: 'soberanistas',
      forca: 1, tema: 'ordem', porque: 'Teste.', url: 'https://exemplo.invalid/v1' });
  });
  const m = await abre({ arquivos: tabela });
  await m.clica(m.um('#item-p1 .principal__pe button'));
  const ataque = m.um('#item-p1 .dossie .ataque__cabeca');
  assert.equal(ataque.querySelector('.ataque__veiculo').getAttribute('href'), '#/regua/veiculos/nyt');
  await m.clica(ataque.querySelector('.ataque__veiculo'));
  await m.terminaFatias();
  assert.equal(textoDe(m.documento.activeElement), 'The New York Times');
  assert.equal(m.documento.activeElement.localName, 'h4');
  await m.vai('#/');
  await m.clica(m.um('#s-placar .etiqueta--partido'));
  assert.equal(m.janela.location.hash, '#/regua/partidos/ordem_global');
  assert.equal(m.documento.activeElement, m.um('#partido-ordem_global h3'));
  await m.vai('#/');
  await m.clica(m.um('#s-movimentos .vetor__player'));
  assert.equal(m.janela.location.hash, '#/regua/players/ue');
  assert.equal(m.um('#player-ue button').getAttribute('aria-expanded'), 'true');
  await m.vai('#/');
  await m.clica(m.um('#avisos-edicao .aviso button'));
  await m.clica(m.um('.errata__item a[href^="#/regua/vetores/"]'));
  assert.equal(m.janela.location.hash, '#/regua/vetores/2026-11-17_p3_ue');
  assert.equal(m.documento.activeElement, m.um('#vetor-2026-11-17_p3_ue').children[0]);
  /* e a nota de mapa em rascunho do Painel leva à aba Veículos */
  await m.vai('#/');
  await m.clica(m.um('#s-principais .nota-secao a'));
  assert.equal(m.um('.abas a[aria-current="page"]').textContent, 'Veículos');
});

/* -------------------------------------------- arquivos em falta, estados */

test('Régua sem regua.json: o aviso, a legenda com os textos fixos, e as abas de pé, com os ids crus', async () => {
  let m = await abreRegua('#/regua/partidos', (t) => { delete t['dados/regua.json']; });
  assert.deepEqual(textos(m.todos('.vista__corpo > .avisos .aviso')), ['RÉGUA INDISPONÍVEL Nomes e rótulos aparecem como identificadores.']);
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
  assert.deepEqual(textos(m.todos('.legenda__letras > li')), ['B polo azul', 'Y misto', 'R polo vermelho', 'W sem posição conhecida', 'K saiu do cargo',
    'B R virada: antes e agora']);
  assert.equal(m.um('.legenda__abre'), null, 'sem a régua não há o que ler em "COMO LER"');
  assert.equal(m.todos('.partido, .time').length, 0);
  assert.deepEqual(textos(m.todos('.aba .vazio')), ['—', '—']);
  assert.equal(m.todos('.abas a').length, 4);

  m = await abreRegua('#/regua/players?partido=centrao', (t) => { delete t['dados/regua.json']; });
  assert.equal(m.todos('.matriz__linha').length, 30);
  assert.deepEqual(textos(m.todos('.matriz thead th')).slice(3, 10), ['pandemia_inicio', 'pandemia_depois', 'ia_inicio', 'ia_depois', 'moderacao', 'clima', 'imigracao']);
  assert.equal(textoDe(m.todos('.matriz__grupo')[0]), 'ordem_global (6)');
  assert.deepEqual(m.todos('.matriz__linha').filter(aVista).map((tr) => tr.getAttribute('id')), ['player-samsung', 'player-morgan_stanley'],
    'sem a régua, os filtros valem com os valores que os players trazem');
  assert.equal(textoDe(m.um('#player-samsung').children[1]), 'empresa');
  assert.equal(textoDe(m.um('#player-samsung .so-leitor')), 'pandemia_inicio: sem posição conhecida');

  m = await abreRegua('#/regua/veiculos/reuters', (t) => { delete t['dados/regua.json']; });
  assert.equal(m.todos('.veiculo').length, 146);
  assert.equal(m.todos('.grupo__titulo').length, 7);
  m.todos('.grupo__titulo').forEach((titulo) => assert.match(textoDe(titulo), /^[a-z_]+ \(\d+\)$/, 'sem a régua, o grupo aparece pelo id do lado'));
  assert.match(textoDe(m.um('#veiculo-reuters .marcas')), /^lado centrao confiança no lado: baixa/);
  assert.equal(m.um('#veiculo-reuters .marcas a'), null, 'partido que a régua não conhece não vira link');
  assert.equal(m.documento.activeElement, m.um('#veiculo-reuters h4'));
});

test('Régua sem players.json: o aviso diz o arquivo; fichas de partido sem players, matriz vazia, veículos com ids', async () => {
  let m = await abreRegua('#/regua/partidos', (t) => { delete t['dados/players.json']; });
  assert.deepEqual(textos(m.todos('.vista__corpo > .avisos .aviso')),
    ['DADOS DE APOIO INDISPONÍVEIS Não deu para carregar dados/players.json. Alguns nomes aparecem como identificadores.']);
  assert.equal(m.todos('.partido').length, 7);
  assert.match(textoDe(m.um('#partido-centrao')), /players \(0\) — saldo em 30 dias/);
  assert.equal(m.um('.aba__regra'), null);

  m = await abreRegua('#/regua/players/macron', (t) => { delete t['dados/players.json']; });
  assert.equal(textoDe(m.um('.aba .vazio')), '—');
  assert.equal(m.todos('.matriz').length, 0);
  assert.equal(textoDe(m.um('#avisos-gerais .aviso')), AVISO_FICHA('macron'));

  m = await abreRegua('#/regua/veiculos', (t) => { delete t['dados/players.json']; });
  await m.clica(m.um('#veiculo-nyt button'));
  const alvos = m.um('#veiculo-nyt').querySelectorAll('.dados__par').find((p) => textoDe(p.querySelector('dt')) === 'Alvos').querySelector('dd');
  assert.equal(textoDe(alvos), 'trump, musk, altman');
  assert.equal(alvos.querySelectorAll('a').length, 0, 'player que não está no arquivo nunca vira link');
});

test('Régua sem veiculos.json: só a aba Veículos leva o aviso de mapa indisponível', async () => {
  let m = await abreRegua('#/regua/veiculos/reuters', (t) => { delete t['dados/veiculos.json']; });
  assert.deepEqual(textos(m.todos('.vista__corpo > .avisos .aviso')), ['MAPA DE VEÍCULOS INDISPONÍVEL Os veículos aparecem pelo identificador, sem lado.']);
  assert.equal(m.todos('.veiculo, .filtros, .grupo').length, 0);
  assert.equal(textoDe(m.um('.aba .vazio')), '—');
  assert.equal(/MAPA EM RASCUNHO|Mapa revisado/.test(textoDe(m.um('.aba'))), false, 'sem o mapa não se sabe se ele é rascunho');
  assert.equal(textoDe(m.um('#avisos-gerais .aviso')), AVISO_FICHA('reuters'));
  for (const aba of ['partidos', 'players', 'vetores']) {
    m = await abreRegua('#/regua/' + aba, (t) => { delete t['dados/veiculos.json']; });
    assert.equal(m.todos('.vista__corpo > .avisos .aviso').length, 0, aba + ' não usa o mapa');
  }
});

test('Régua sem vetores.json: Players abre sem vetores; Vetores diz o arquivo que faltou', async () => {
  let m = await abreRegua('#/regua/players', (t) => { delete t['dados/vetores.json']; });
  assert.deepEqual(textos(m.todos('.vista__corpo > .avisos .aviso')),
    ['DADOS DE APOIO INDISPONÍVEIS Não deu para carregar dados/vetores.json. Alguns nomes aparecem como identificadores.']);
  assert.equal(m.todos('.matriz__linha').length, 30);
  assert.equal(textoDe(m.um('#player-ue').children[10]), '0');

  m = await abreRegua('#/regua/vetores', (t) => { delete t['dados/vetores.json']; });
  assert.equal(m.todos('.vista__corpo > .avisos .aviso').length, 1);
  assert.equal(textoDe(m.um('.aba .vazio')), 'Nenhum vetor registrado ainda.');
  assert.deepEqual(textos(m.todos('.aba .secao__intro')), ['O registro só cresce. Vetor errado não se apaga: é anulado, e fica à vista.']);
});

test('Régua e o índice: lista vazia e índice que não carrega; nos dois a Régua funciona, sem aviso do índice', async () => {
  /* vazio: o saldo é zero */
  const vazio = arquivos();
  vazio['edicoes/indice.json'] = { versao: 1, atualizado_em: '2026-11-19T21:14:03Z', edicoes: [] };
  let m = await abre({ hash: '#/regua/partidos', arquivos: vazio });
  assert.equal(m.todos('#avisos-gerais .aviso, .vista__corpo > .avisos .aviso').length, 0);
  assert.equal(m.todos('.partido').length, 7);
  assert.equal(textoDe(m.um('#partido-ordem_global .partido__saldo')), 'saldo em 30 dias zero 0');
  /* erro de rede: o saldo não se sabe, e a ficha diz com travessão */
  m = await abre({ hash: '#/regua/partidos', arquivos: arquivos({ sem: ['edicoes/indice.json'] }) });
  assert.equal(m.todos('#avisos-gerais .aviso, .vista__corpo > .avisos .aviso').length, 0);
  assert.equal(m.todos('.partido').length, 7);
  assert.equal(textoDe(m.um('#partido-ordem_global .partido__saldo')), 'saldo em 30 dias —');
  assert.equal(m.um('#vista').hasAttribute('aria-busy'), false);
  for (const [aba, seletor, quantos] of [['players', '.matriz__linha', 30], ['veiculos', '.veiculo', 146]]) {
    await m.vai('#/regua/' + aba);
    assert.equal(m.todos(seletor).length, quantos, aba);
    assert.equal(m.todos('#avisos-gerais .aviso').length, 0, aba);
  }
  await m.vai('#/regua/vetores');
  assert.equal(textoDe(m.um('.aba .vazio')), 'Nenhum vetor registrado ainda.');
  /* sem o índice, o item do vetor não vira link para a edição */
  const semIndice = arquivos({ sem: ['edicoes/indice.json'] });
  comVetores(semIndice);
  m = await abre({ hash: '#/regua/vetores', arquivos: semIndice });
  assert.equal(m.todos('.aba tbody tr').length, 3);
  assert.equal(m.todos('.aba tbody a[href^="#/edicao"]').length, 0);
  assert.equal(textoDe(m.um('.aba tbody tr').children[8]), 'radar 2');
  /* só a edição de exemplo no índice: ela não entra no acumulado */
  m = await abre({ hash: '#/regua/partidos', arquivos: arquivos() });
  assert.equal(textoDe(m.um('#partido-ordem_global .partido__saldo')), 'saldo em 30 dias zero 0');
});

test('Régua: arquivo de formato novo leva o aviso na aba que o usa; dados tortos não derrubam a vista', async () => {
  let m = await abreRegua('#/regua/players', (t) => { t['dados/players.json'].versao = 2; t['dados/veiculos.json'].versao = 9; });
  assert.deepEqual(textos(m.todos('.vista__corpo > .avisos .aviso')), ['FORMATO NOVO O arquivo dados/players.json usa um formato mais novo que o site.']);
  assert.equal(m.todos('.matriz__linha').length, 30);

  const torta = (t) => {
    t['dados/players.json'].players.push(null, 'x', 7, { id: 'ID INVÁLIDO', nome: 'Sem id válido' }, { id: 'sem_nada' },
      { id: 'torto', nome: 5, tipo: {}, partido: ['x'], time: null, dna: 'B', duvidas: 'clima', dna_fontes: [], nota: {}, origem: 3 });
    t['dados/veiculos.json'].veiculos.push(null, 'x', { id: 'sem_nada_2' },
      { id: 'veiculo_torto', nome: {}, pais: 7, tipo: [], lado: {}, idiomas: 'en', sites: null, feeds: 'rss', serve_a: 'trump', alvos: 5, controle_fonte: 12, feeds_nota: [] });
    t['dados/vetores.json'].vetores.push(null, 'x', {}, { id: 5, data: 7, player: {}, de: [], para: null, forca: 'muita', tema: 9, porque: {}, url: 3, item: {} },
      { anula: 5 }, { id: 'anula_solta', anula: 'vetor_que_nao_existe' });
    t['dados/regua.json'].partidos.push(null, { id: 'partido_torto', voto_tipico: 5, nome: {} });
    t['dados/regua.json'].temas.push('x');
  };
  for (const aba of ['partidos', 'players', 'veiculos', 'vetores']) {
    m = await abreRegua('#/regua/' + aba, torta);
    await m.abreTudo();
    assert.equal(m.todos('#avisos-gerais .aviso').length, 0, aba);
    assert.equal(textoDe(m.um('h1')), 'Régua', aba);
    assert.equal(/undefined|NaN|\[object|function /.test(textoDe(m.um('main'))), false, aba + ': vazou algo que não é dado');
  }
  m = await abreRegua('#/regua/players', torta);
  assert.equal(m.todos('.matriz__linha').length, 33, 'os 30 e os 3 objetos a mais; o que não é objeto fica de fora');
  assert.equal(m.todos('.matriz__linha').filter((tr) => !tr.hasAttribute('id')).length, 1, 'id fora da forma não vira id de elemento');
  m = await abreRegua('#/regua/veiculos', torta);
  assert.equal(m.todos('.veiculo').length, 148);
  assert.equal(textoDe(m.um('.filtros__contagem')), '');
  m = await abreRegua('#/regua/vetores', torta);
  assert.equal(m.todos('.aba tbody tr').length, 2, 'o objeto vazio e o de campos tortos viram linha; as anulações, não');
});

test('Régua: enquanto os arquivos não chegam, aria-busy e um travessão; depois de 8 segundos, "Está demorando", com "Tentar de novo"', async () => {
  const m = await abre({ hash: '#/regua/players', arquivos: arquivosDe35Dias(), segura: true, esperar: false });
  await m.assenta();
  assert.equal(textoDe(m.um('h1')), 'Régua');
  assert.equal(m.um('#vista').getAttribute('aria-busy'), 'true');
  assert.equal(textoDe(m.um('.vista__corpo')), '—');
  m.relogio.avanca(8000);
  const aviso = m.um('#avisos-gerais .aviso');
  assert.equal(textoDe(aviso), 'Está demorando. A conexão pode estar lenta. Tentar de novo');
  /* "Tentar de novo" pede outra vez o que não chegou e monta a mesma aba */
  const antes = m.rede.pedidos.length;
  m.rede.segura = false;
  await m.clica(aviso.querySelector('button'));
  assert.ok(m.rede.pedidos.length > antes);
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
  assert.equal(m.todos('.matriz__linha').length, 30);
  assert.equal(m.janela.location.hash, '#/regua/players');
  assert.equal(m.um('#vista').hasAttribute('aria-busy'), false);
});

test('Régua: uma edição a caminho é descartada quando o leitor volta para a mesma aba', async () => {
  const m = await abreRegua('#/regua/partidos');
  m.rede.segura = true;
  await m.vai('#/edicao/2026-11-18');
  assert.equal(m.um('#vista').getAttribute('aria-busy'), 'true', 'a Régua fica na tela enquanto a edição não chega');
  assert.equal(textoDe(m.um('h1')), 'Régua');
  await m.vai('#/regua/partidos/centrao');
  assert.equal(m.um('#vista').hasAttribute('aria-busy'), false);
  assert.equal(m.documento.activeElement, m.um('#partido-centrao h3'));
  m.rede.solta();
  await m.assenta();
  assert.equal(textoDe(m.um('h1')), 'Régua', 'a edição que chegou atrasada não toma a tela');
  m.relogio.avanca(9000);
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0, 'e o relógio de demora dela não dispara');
  assert.equal(DIA, '2026-11-19');
});
