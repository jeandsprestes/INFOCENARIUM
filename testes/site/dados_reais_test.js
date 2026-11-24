'use strict';

/* Os dados de verdade de dados/ (régua, players, mapa, vetores e catálogo,
 * como estão hoje no repositório), com a edição de exemplo, em todas as
 * vistas e em todas as rotas que esses dados permitem. Os outros testes usam
 * a cópia congelada; este confere que o site também abre com o que vai ao ar.
 *
 * Sem a pasta dados/ (uma cópia só com testes/ e assets/, como a do conferidor
 * de mutantes), os testes deste arquivo são pulados: eles conferem dado, e não
 * código, e o resto da bateria continua valendo. */

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {
  RAIZ, abre, arquivos, dadosDoRepositorio, edicaoDeExemplo, edicaoReal, entradaDoIndice, entradasDe35Dias,
  indiceDe, textoDe, acusacoes, copia
} = require('./apoio.js');

const TEM_DADOS = ['regua', 'players', 'veiculos', 'vetores', 'indicadores']
  .every((nome) => fs.existsSync(path.join(RAIZ, 'dados', nome + '.json')));
const PULA = TEM_DADOS ? false : 'sem a pasta dados/ (cópia só com os testes)';

/* A tabela do fetch: os cinco arquivos de dados/ e as edições pedidas. */
function tabelaReal(edicoes, entradasAMais) {
  const tabela = dadosDoRepositorio();
  edicoes.forEach((edicao) => { tabela['edicoes/' + edicao.data + '.json'] = edicao; });
  tabela['edicoes/indice.json'] = indiceDe(edicoes.map((e) => entradaDoIndice(e)).concat(entradasAMais || []));
  return tabela;
}

/* Sobras de valor que nunca deviam chegar à tela. */
const SOBRAS = /\bundefined\b|\bNaN\b|\[object |\bnull\b/;

/* O que vale para toda vista, em toda rota. */
function confereVista(m, rota) {
  assert.equal(textoDe(m.um('#avisos-gerais')), '', rota + ': nenhum aviso geral (falha, rota, item ou ficha)');
  assert.equal(m.todos('#vista h1').length, 1, rota + ': um h1 na vista');
  const texto = textoDe(m.um('#vista'));
  assert.doesNotMatch(texto, SOBRAS, rota + ': sobra de valor na tela');
  m.todos('a').forEach((a) => {
    const href = a.getAttribute('href') || '';
    if (/^https?:/.test(href)) {
      assert.equal(a.getAttribute('target'), '_blank', rota + ': ' + href);
      assert.equal(a.getAttribute('rel'), 'noopener noreferrer', rota + ': ' + href);
    } else {
      /* link interno, ou arquivo do próprio site, sempre relativo */
      assert.match(href, /^(#\/|#conteudo$|edicoes\/\d{4}-\d{2}-\d{2}\.(json|md)$|feed\.xml$)/, rota + ': link estranho ' + href);
    }
  });
}

test('dados de verdade: as rotas da edição de exemplo abrem, e cada destino é achado', { skip: PULA }, async () => {
  const antes = acusacoes.length;
  const exemplo = edicaoDeExemplo();
  const m = await abre({ hash: '#/', arquivos: tabelaReal([exemplo]) });
  confereVista(m, '#/');
  assert.ok(m.um('#s-principais') && m.um('#s-radar') && m.um('#s-bastidores'), 'o Painel montou as seções');
  const destinos = exemplo.principais.concat(exemplo.radar).map((item) => item.id)
    .concat(exemplo.alerta.dominios.map((d) => d.id), exemplo.indicadores.map((i) => i.id));
  for (const id of destinos) {
    const rota = '#/edicao/' + exemplo.data + '/' + id;
    await m.vai(rota);
    confereVista(m, rota);
    assert.notEqual(m.documento.activeElement, m.documento.body, rota + ': o destino recebeu o foco');
  }
  const partido = dadosDoRepositorio()['dados/regua.json'].partidos[0].id;
  for (const rota of ['#/edicao/' + exemplo.data, '#/?cat=ia', '#/?cat=geopolitica&dom=energia&partido=' + partido]) {
    await m.vai(rota);
    confereVista(m, rota);
  }
  await m.abreTudo();
  confereVista(m, 'Painel com tudo aberto');
  assert.equal(acusacoes.length, antes, 'o DOM falso não acusou nada');
});

test('dados de verdade: Arquivo, Régua (todas as fichas) e Método abrem sem erro', { skip: PULA }, async () => {
  const antes = acusacoes.length;
  const reais = dadosDoRepositorio();
  const m = await abre({ hash: '#/arquivo', arquivos: tabelaReal([edicaoDeExemplo()]) });
  const rotas = ['#/arquivo', '#/arquivo?nivel=3', '#/regua', '#/regua/partidos']
    .concat(reais['dados/regua.json'].partidos.map((p) => '#/regua/partidos/' + p.id))
    .concat(['#/regua/players'], reais['dados/players.json'].players.map((p) => '#/regua/players/' + p.id))
    .concat(['#/regua/veiculos'], reais['dados/veiculos.json'].veiculos.map((v) => '#/regua/veiculos/' + v.id))
    .concat(['#/regua/vetores', '#/metodo'])
    .concat(['conflito', 'perguntas', 'regua', 'niveis', 'indicadores', 'rotina', 'limites'].map((s) => '#/metodo/' + s));
  for (const rota of rotas) {
    await m.vai(rota);
    confereVista(m, rota);
    if (/^#\/regua\/(partidos|players|veiculos)\/./.test(rota)) {
      assert.notEqual(m.documento.activeElement, m.documento.body, rota + ': a ficha recebeu o foco');
    }
  }
  for (const rota of ['#/arquivo', '#/regua/partidos', '#/regua/players', '#/regua/veiculos', '#/regua/vetores', '#/metodo']) {
    await m.vai(rota);
    await m.abreTudo();
    confereVista(m, rota + ' com tudo aberto');
  }
  assert.equal(acusacoes.length, antes, 'o DOM falso não acusou nada');
});

test('dados de verdade com 35 dias de índice: fita, acumulados e as três vistas', { skip: PULA }, async () => {
  const antes = acusacoes.length;
  const tabela = tabelaReal([edicaoReal('2026-11-18'), edicaoReal('2026-11-19')], entradasDe35Dias());
  const m = await abre({ hash: '#/', arquivos: tabela });
  confereVista(m, '#/');
  assert.ok(m.um('#s-hoje .fita'), 'a fita aparece com o histórico');
  /* só 18/11 e 19/11 têm arquivo de edição; os outros dias são entradas do índice */
  for (const rota of ['#/edicao/2026-11-18', '#/edicao/2026-11-18/p1', '#/arquivo', '#/arquivo?nivel=2', '#/regua/partidos', '#/regua/players', '#/metodo']) {
    await m.vai(rota);
    await m.abreTudo();
    confereVista(m, rota);
  }
  assert.equal(acusacoes.length, antes, 'o DOM falso não acusou nada');
});

/* ----- campos novos desta fase ----- */

/* O catálogo pode trazer, em cada fonte, o campo contratos (ESQUEMA, seção 14;
   regra C6): o endereço-modelo de cada contrato futuro, com a marca {c}, e as
   letras dos meses. O site não usa o campo, e não pode quebrar com ele. */
const MODELO = 'https://exemplo.invalid/chart/ZC{c}.CBT?range=1mo&interval=1d';

function catalogoComContratos(base, valor) {
  const catalogo = copia(base);
  catalogo.indicadores.forEach((indicador) => {
    indicador.fontes.forEach((fonte, i) => { if (i === 0) { fonte.contratos = copia(valor); } });
  });
  /* e uma fonte de leitor novo, que o site mostra cru */
  catalogo.indicadores[0].fontes.push({ nome: 'CNBC', url: 'https://exemplo.invalid/harmony/app/charts/1M.json?symbol=@W.1', leitor: 'cnbc_chart' });
  return catalogo;
}

[['como o contrato pede', { modelo: MODELO, meses: 'HKNUZ' }], ['torto (texto)', 'HKNUZ'], ['torto (lista)', [MODELO]],
  ['torto (nulo)', null], ['torto (objeto vazio)', {}]].forEach(([nome, valor]) => {
  test('catálogo com o campo contratos ' + nome + ': Painel, Arquivo e Método abrem, e o modelo nunca aparece', async () => {
    const antes = acusacoes.length;
    const tabela = arquivos({ edicoes: [edicaoReal('2026-11-18'), edicaoReal('2026-11-19')], entradas: entradasDe35Dias() });
    const quantasFontes = tabela['dados/indicadores.json'].indicadores.reduce((n, i) => n + i.fontes.length, 0);
    tabela['dados/indicadores.json'] = catalogoComContratos(tabela['dados/indicadores.json'], valor);
    const m = await abre({ hash: '#/metodo/indicadores', arquivos: tabela });
    assert.equal(textoDe(m.um('#avisos-gerais')), '');
    assert.equal(m.todos('.catalogo__fonte').length, quantasFontes + 1, 'uma linha por fonte, nem mais nem menos');
    assert.ok(textoDe(m.um('.catalogo')).includes('leitor cnbc_chart'), 'o leitor novo aparece cru');
    for (const rota of ['#/metodo/indicadores', '#/', '#/arquivo']) {
      await m.vai(rota);
      await m.abreTudo();
      const texto = textoDe(m.um('#vista'));
      assert.equal(textoDe(m.um('#avisos-gerais')), '', rota);
      assert.equal(texto.includes('{c}') || texto.includes('HKNUZ') || texto.includes('exemplo.invalid/chart'), false, rota + ': o campo contratos não vai à tela');
      m.todos('a').forEach((a) => assert.equal(/exemplo\.invalid\/chart|%7Bc%7D|\{c\}/.test(String(a.getAttribute('href'))), false, rota + ': o modelo não vira link'));
    }
    assert.equal(acusacoes.length, antes);
  });
});

/* A coleta grava em coleta.json, por feed, quantas entradas caíram por serem
   de outro site (fora_do_site). É aviso para o dono, na mesa de trabalho da
   rotina: o publica.py só copia feeds_ok e feeds_falhos para os bastidores, e
   o site nunca lê coleta.json. Se o campo vazasse para a edição, o site o
   ignoraria, como toda chave que não conhece. */
test('fora_do_site da coleta não chega ao site: nenhum pedido fora do site, e a chave, se vier, é ignorada', async () => {
  const limpa = edicaoReal('2026-11-19');
  const comChave = edicaoReal('2026-11-19', (edicao) => {
    edicao.bastidores.fora_do_site = 7;
    edicao.bastidores.feeds = [{ veiculo: 'reuters', url: 'https://exemplo.invalid/feed', estado: 'ok', itens: 3, fora_do_site: 7 }];
  });
  const textos = [];
  for (const edicao of [limpa, comChave]) {
    const m = await abre({ hash: '#/', arquivos: arquivos({ edicoes: [edicao] }) });
    for (const rota of ['#/arquivo', '#/regua/vetores', '#/metodo', '#/']) { await m.vai(rota); }
    const pedidos = Array.from(new Set(m.rede.pedidos.map((p) => p.caminho))).sort();
    assert.deepEqual(pedidos, ['dados/indicadores.json', 'dados/players.json', 'dados/regua.json', 'dados/veiculos.json',
      'dados/vetores.json', 'edicoes/2026-11-19.json', 'edicoes/indice.json'], 'só os arquivos do site');
    textos.push(textoDe(m.um('#s-bastidores')));
  }
  assert.equal(textos[1], textos[0], 'os bastidores saem iguais, com ou sem a chave');
  const app = fs.readFileSync(path.join(RAIZ, 'assets', 'app.js'), 'utf8');
  assert.equal(/coleta\.json|fora_do_site/.test(app), false, 'o site não conhece a coleta');
});
