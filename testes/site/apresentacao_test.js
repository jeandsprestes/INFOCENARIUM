'use strict';

/* Campos só de apresentação: o validador (valida.py --dados) não os confere
 * (CONTRATO, seção 3). Sem cada um deles, ou com um valor torto, o site não
 * quebra: mostra travessão sob o rótulo ou omite a linha. Os campos são os do
 * mapa de veículos, de cada feed e da régua que nenhuma regra usa.
 * Dados: a cópia congelada, mexida em memória. */

const test = require('node:test');
const assert = require('node:assert/strict');
const { abre, arquivosDe35Dias, textoDe, acusacoes } = require('./apoio.js');

const DO_VEICULO = ['pais', 'idiomas', 'controle', 'lado_porque', 'fatos_nota', 'uso', 'feeds_nota'];
const DO_FEED = ['secao', 'formato', 'conferido', 'nota'];
const DA_REGUA = ['criada_em', 'descricao', 'aviso', 'virada'];
const ROTAS = ['#/regua/veiculos/bbc', '#/regua/partidos', '#/regua/players/macron', '#/', '#/edicao/2026-11-19/p1', '#/metodo', '#/arquivo'];

/* Tira o campo (valor undefined) ou põe nele um valor torto. */
function mexe(objeto, campo, valor) {
  if (valor === undefined) { delete objeto[campo]; } else { objeto[campo] = valor; }
}

function semApresentacao(valor) {
  return arquivosDe35Dias((tabela) => {
    tabela['dados/veiculos.json'].veiculos.forEach((veiculo) => {
      DO_VEICULO.forEach((campo) => mexe(veiculo, campo, valor));
      (veiculo.feeds || []).forEach((feed) => DO_FEED.forEach((campo) => mexe(feed, campo, valor)));
    });
    const regua = tabela['dados/regua.json'];
    DA_REGUA.forEach((campo) => mexe(regua, campo, valor));
    Object.keys(regua.valores).forEach((letra) => { mexe(regua.valores[letra], 'cor', valor); mexe(regua.valores[letra], 'significado', valor); });
    regua.partidos.forEach((partido) => mexe(partido, 'diante_da_ordem', valor));
    regua.times.forEach((time) => mexe(time, 'descricao', valor));
  });
}

[['ausentes', undefined], ['nulos', null], ['números', 42], ['objetos', {}], ['listas vazias', []]].forEach(([nome, valor]) => {
  test('campos só de apresentação ' + nome + ': as cinco vistas abrem, sem aviso de falha e sem uso proibido do DOM', async () => {
    const tabela = semApresentacao(valor);
    for (const hash of ROTAS) {
      const antes = acusacoes.length;
      const m = await abre({ hash, arquivos: tabela });
      await m.abreTudo();
      assert.equal(textoDe(m.um('#avisos-gerais')), '', hash + ': nenhum aviso geral');
      assert.ok(m.todos('#vista h1').length === 1, hash + ': a vista montou');
      assert.ok(m.todos('#vista section, #vista .aba').length > 0, hash + ': com conteúdo');
      assert.equal(acusacoes.length, antes, hash + ': o DOM falso não acusou nada');
    }
  });
});

test('veículo sem os textos do mapa: cada rótulo da ficha aberta leva travessão, e os feeds só o que há', async () => {
  const m = await abre({ hash: '#/regua/veiculos/bbc', arquivos: semApresentacao(undefined) });
  const pares = Object.fromEntries(m.todos('#veiculo-bbc .dados__par').map((par) => [textoDe(par.querySelector('dt')), textoDe(par.querySelector('dd'))]));
  ['País', 'Idiomas', 'Por que este lado', 'Sobre os fatos', 'Uso no monitor'].forEach((rotulo) => assert.equal(pares[rotulo], '—', rotulo));
  assert.match(pares['Quem controla'], /^— fonte/, 'o link da fonte do controle continua');
  assert.equal(pares.Sites, 'bbc.com, bbc.co.uk', 'sites não é campo só de apresentação');
  assert.deepEqual(m.todos('#veiculo-bbc .feed').map((feed) => textoDe(feed.querySelector('.marcas'))), ['não conferido', 'não conferido']);
  assert.equal(m.todos('#veiculo-bbc .feed__nota').length, 0);
  assert.equal(textoDe(m.um('#veiculo-bbc .veiculo__meta')), 'público', 'sem país, a linha fica só com o tipo');
});

test('régua sem textos de apresentação: a legenda usa os rótulos fixos; a ficha de partido leva travessão em "diante da ordem"', async () => {
  const m = await abre({ hash: '#/regua/partidos', arquivos: semApresentacao(undefined) });
  assert.equal(m.todos('.legenda__descricao').length, 0);
  assert.equal(m.todos('.legenda .aviso').length, 0);
  assert.equal(m.todos('.legenda__criada').length, 0);
  assert.deepEqual(m.todos('.legenda__letras .legenda__item').map(textoDe),
    ['B polo azul', 'Y misto', 'R polo vermelho', 'W sem posição conhecida', 'K saiu do cargo', 'B R virada: antes e agora']);
  const ficha = m.um('#partido-ordem_global');
  const rotulos = ficha.querySelectorAll('.rotulo');
  const diante = rotulos.find((r) => textoDe(r) === 'diante da ordem');
  assert.ok(diante, 'o rótulo continua');
  assert.equal(textoDe(diante.nextSibling.nodeType === 1 ? diante.nextSibling : diante.nextSibling.nextSibling), '—');
  /* nenhum parágrafo vazio nas fichas de partido e de time */
  m.todos('.partido p, .time p').forEach((p) => assert.notEqual(textoDe(p), '', 'parágrafo vazio: ' + p.getAttribute('class')));
});

test('Método sem os textos de apresentação da régua: "prova mínima" leva travessão, e nenhum parágrafo fica vazio', async () => {
  const m = await abre({
    hash: '#/metodo',
    arquivos: arquivosDe35Dias((tabela) => {
      const regua = tabela['dados/regua.json'];
      regua.niveis_alerta.forEach((nivel) => { delete nivel.significado; delete nivel.prova_minima; });
      regua.forcas.forEach((linha) => { delete linha.o_que_conta; });
      regua.evidencias.forEach((linha) => { delete linha.o_que_conta; });
      regua.campos.forEach((linha) => { delete linha.descricao; });
    })
  });
  const fichas = m.todos('.nivel-ficha');
  assert.equal(fichas.length, 5);
  fichas.forEach((ficha) => {
    assert.equal(ficha.querySelectorAll('p').length, 2, 'selo e prova mínima; o significado que falta some');
    assert.equal(textoDe(ficha.querySelectorAll('p')[1]), 'prova mínima —');
  });
  m.todos('.quadro p, .nivel-ficha p').forEach((p) => assert.notEqual(textoDe(p), '', 'parágrafo vazio: ' + p.getAttribute('class')));
  assert.equal(m.todos('.quadro__linha .quadro__texto').length, 2, 'só as duas linhas dos times têm explicação');
});
