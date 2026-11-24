'use strict';

/* Núcleo do app.js: o objeto global, as rotas, as datas, os números, os
 * endereços e as guardas do DOM falso. */

const test = require('node:test');
const assert = require('node:assert/strict');
const { abre, AGORA, copia, acusacoes } = require('./apoio.js');
const { criaJanela } = require('./dom_falso.js');

/* Objeto do outro contexto vira objeto comum, para comparar. */
function plano(valor) {
  return copia(valor);
}

test('o script põe um nome só no escopo global, e ele é só de leitura', async () => {
  const m = await abre();
  assert.deepEqual(m.novosGlobais, ['INFO']);
  assert.equal(Object.isFrozen(m.janela.INFO), true);
  assert.equal(typeof m.janela.INFO.interpretaRota, 'function');
});

test('rotas: a tabela inteira da especificação do site', async () => {
  const { INFO } = (await abre()).janela;
  const r = (hash) => plano(INFO.interpretaRota(hash));

  assert.deepEqual(r(''), { vista: 'painel', tipo: 'edicao', data: null, item: null, consulta: {} });
  assert.deepEqual(r('#'), r(''));
  assert.deepEqual(r('#/'), r(''));
  assert.deepEqual(r('#/?cat=ia&dom=energia&partido=soberanistas').consulta, { cat: 'ia', dom: 'energia', partido: 'soberanistas' });
  assert.deepEqual(r('#/edicao/2026-11-19'), { vista: 'painel', tipo: 'edicao', data: '2026-11-19', item: null, consulta: {} });
  assert.deepEqual(r('#/edicao/2026-11-19/p2'), { vista: 'painel', tipo: 'edicao', data: '2026-11-19', item: 'p2', consulta: {} });
  assert.deepEqual(r('#/edicao/2026-11-19/r4?cat=ia'), { vista: 'painel', tipo: 'edicao', data: '2026-11-19', item: 'r4', consulta: { cat: 'ia' } });
  assert.equal(r('#/edicao/2026-11-19/energia').item, 'energia');
  assert.deepEqual(r('#/arquivo'), { vista: 'arquivo', tipo: 'arquivo', consulta: {} });
  assert.deepEqual(r('#/arquivo?nivel=3').consulta, { nivel: '3' });
  assert.equal(r('#/regua').redireciona, '#/regua/partidos');
  assert.deepEqual(r('#/regua/partidos'), { vista: 'regua', tipo: 'regua', aba: 'partidos', ficha: null, consulta: {} });
  assert.equal(r('#/regua/partidos/soberanistas').ficha, 'soberanistas');
  assert.equal(r('#/regua/players/macron').ficha, 'macron');
  assert.deepEqual(r('#/regua/players?partido=centrao&tipo=empresa&time=mudanca&q=Mac%20ron').consulta,
    { partido: 'centrao', tipo: 'empresa', time: 'mudanca', q: 'Mac ron' });
  assert.deepEqual(r('#/regua/veiculos?lado=centrao&fatos=alta&tipo=agencia&q=reu').consulta,
    { lado: 'centrao', fatos: 'alta', tipo: 'agencia', q: 'reu' });
  assert.equal(r('#/regua/veiculos/reuters').ficha, 'reuters');
  assert.deepEqual(r('#/regua/vetores?player=ue').consulta, { player: 'ue' });
  assert.equal(r('#/regua/vetores/2026-11-20_p1_ue').ficha, '2026-11-20_p1_ue');
  assert.deepEqual(r('#/metodo'), { vista: 'metodo', tipo: 'metodo', secao: null, consulta: {} });
  ['conflito', 'perguntas', 'regua', 'niveis', 'indicadores', 'rotina', 'limites'].forEach((secao) => {
    assert.equal(r('#/metodo/' + secao).secao, secao);
  });
});

test('rotas: qualquer outra é o Painel, com a marca de endereço não encontrado', async () => {
  const { INFO } = (await abre()).janela;
  const outras = ['#conteudo', '#/nada', '#/edicao', '#/edicao/2026-13-01', '#/edicao/19-11-2026', '#/edicao/2026-11-19/P1',
    '#/edicao/2026-11-19/p1/mais', '#/edicao/2026-11-19/' + 'a'.repeat(65), '#/arquivo/2026', '#/regua/outra',
    '#/regua/players/Macron', '#/regua/players/a b', '#/metodo/segredo', '#/metodo/niveis/1', '#/edicao/%E0%A4%A',
    '#/edicao/2026-11-19/<img>', '#//', '#/arquivo/'];
  outras.forEach((hash) => {
    const rota = INFO.interpretaRota(hash);
    assert.equal(rota.desconhecida, true, hash);
    assert.equal(rota.tipo, 'edicao', hash);
    assert.equal(rota.data, null, hash);
  });
});

test('rotas: parâmetro desconhecido ou com valor fora da forma é ignorado', async () => {
  const { INFO } = (await abre()).janela;
  const c = (hash) => plano(INFO.interpretaRota(hash).consulta);
  assert.deepEqual(c('#/?cat=ia&x=1&utm_source=y'), { cat: 'ia' });
  assert.deepEqual(c('#/?cat=IA&dom=ener gia&partido='), {});
  assert.deepEqual(c('#/?cat=%3Cimg%3E'), {});
  assert.deepEqual(c('#/?cat=ia&cat=geopolitica'), { cat: 'ia' }, 'vale o primeiro');
  assert.deepEqual(c('#/?cat=%E0%A4%A'), {}, 'código de URL torto');
  assert.deepEqual(c('#/arquivo?nivel=3&cat=ia'), { nivel: '3' });
  assert.deepEqual(c('#/regua/partidos?partido=centrao'), {}, 'a aba Partidos não tem filtro');
  assert.deepEqual(c('#/regua/players?q=' + 'a'.repeat(65)), {}, 'busca longa demais');
  assert.deepEqual(c('#/?__proto__=x&constructor=y'), {});
});

test('datas: o texto é cortado, sem passar por Date', async () => {
  const m = await abre();
  const { INFO } = m.janela;
  assert.equal(INFO.dataCurta('2026-11-19'), '19/11');
  assert.equal(INFO.dataLonga('2026-11-19'), '19/11/2026');
  assert.equal(INFO.dataCurta('2026-01-01'), '01/01');
  assert.equal(INFO.dataCurta('19/11/2026'), '19/11/2026', 'o que não é data aparece como veio');
  assert.equal(INFO.dataCurta('2026-13-40'), '2026-13-40');
  assert.equal(INFO.dataLonga(null), '');
  assert.equal(INFO.dataLonga(20261119), '20261119');
});

test('datas: a conta de dias corridos bate com o calendário, em anos comuns e bissextos', async () => {
  const { INFO } = (await abre()).janela;
  const umDia = 86400000;
  for (let ms = Date.UTC(1999, 11, 25); ms < Date.UTC(2032, 2, 5); ms += umDia * 3) {
    const texto = new Date(ms).toISOString().slice(0, 10);
    assert.equal(INFO.numeroDoDia(texto), ms / umDia, texto);
    assert.equal(INFO.dataDoNumero(ms / umDia), texto, texto);
  }
  assert.equal(INFO.numeroDoDia('2026-03-01') - INFO.numeroDoDia('2026-02-28'), 1);
  assert.equal(INFO.numeroDoDia('2028-03-01') - INFO.numeroDoDia('2028-02-28'), 2, '2028 é bissexto');
  assert.equal(INFO.dataDoNumero(INFO.numeroDoDia('2026-11-19') - 29), '2026-10-21');
  assert.equal(INFO.numeroDoDia('2027-01-01') - INFO.numeroDoDia('2026-12-31'), 1);
});

test('data-hora: a hora de Brasília sai do Intl, e não do fuso da máquina', async () => {
  const { INFO } = (await abre()).janela;
  assert.equal(INFO.horaDeBrasilia('2026-11-19T21:14:03Z'), '18h14');
  assert.equal(INFO.horaDeBrasilia('2026-11-20T02:59:59Z'), '23h59', 'ainda é dia 19 em Brasília');
  assert.equal(INFO.horaDeBrasilia('2026-11-20T03:00:00Z'), '00h00');
  assert.equal(INFO.horaDeBrasilia('2026-11-19'), '', 'data sem hora não é data-hora');
  assert.equal(INFO.horaDeBrasilia('ontem'), '');
  assert.equal(INFO.horaDeBrasilia(undefined), '');
});

test('idade do carimbo: AGORA, HÁ N MIN, HÁ N H, HÁ N DIAS', async () => {
  const { INFO } = (await abre()).janela;
  const min = 60000;
  const h = 60 * min;
  const casos = [
    [0, 'AGORA'], [59 * 1000, 'AGORA'], [-5 * min, 'AGORA'], [min, 'HÁ 1 MIN'], [18 * min, 'HÁ 18 MIN'],
    [59 * min + 59000, 'HÁ 59 MIN'], [h, 'HÁ 1 H'], [26 * h, 'HÁ 26 H'], [47 * h + 59 * min, 'HÁ 47 H'],
    [48 * h, 'HÁ 2 DIAS'], [10 * 24 * h, 'HÁ 10 DIAS']
  ];
  casos.forEach(([atras, esperado]) => assert.equal(INFO.idade(AGORA - atras), esperado, String(atras)));
  assert.equal(INFO.idade(null), '');
});

test('números: padrão brasileiro, sinal de menos tipográfico, zero sem sinal', async () => {
  const { INFO } = (await abre()).janela;
  assert.equal(INFO.variacao(1.3), '+1,3%');
  assert.equal(INFO.variacao(-0.6), '−0,6%');
  assert.equal(INFO.variacao(0), '0,0%');
  assert.equal(INFO.variacao(-0.04), '0,0%', 'arredondou para zero: sem sinal');
  assert.equal(INFO.variacao(12), '+12,0%');
  assert.equal(INFO.variacao(null), '—');
  assert.equal(INFO.variacao('1.3'), '—');
  assert.equal(INFO.comSinal(4), '+4');
  assert.equal(INFO.comSinal(-2), '−2');
  assert.equal(INFO.comSinal(0), '0');
  assert.equal(INFO.comSinal(undefined), '—');
  /* com o catálogo: as casas dele */
  assert.equal(INFO.valorDeIndicador(78.4, 2), '78,40');
  assert.equal(INFO.valorDeIndicador(5.4321, 4), '5,4321');
  assert.equal(INFO.valorDeIndicador(2650, 1), '2.650,0');
  assert.equal(INFO.valorDeIndicador(126.4, 0), '126');
  /* sem o catálogo: de 2 a 4 casas */
  assert.equal(INFO.valorDeIndicador(78.4, null), '78,40');
  assert.equal(INFO.valorDeIndicador(5.4321, null), '5,4321');
  assert.equal(INFO.valorDeIndicador(5.43219, null), '5,4322');
  assert.equal(INFO.valorDeIndicador(null, 2), '');
  ['+1,3%', '−0,6%', '−2'].forEach((t) => assert.equal(t.includes('-'), false, 'hífen no lugar do sinal de menos'));
});

test('rótulos das listas fechadas: valor conhecido vira texto, desconhecido aparece cru', async () => {
  const { INFO } = (await abre()).janela;
  assert.equal(INFO.rotulo('categoria', 'geopolitica'), 'Geopolítica');
  assert.equal(INFO.rotulo('categoria', 'ia'), 'IA');
  assert.equal(INFO.rotulo('tendencia', 'estavel'), 'estável');
  assert.equal(INFO.rotulo('evidencia', 'narrativa'), 'só narrativa');
  assert.equal(INFO.rotulo('evidencia', 'sancao'), 'sanção');
  assert.equal(INFO.rotulo('estado', 'falha'), 'sem edição');
  assert.equal(INFO.rotulo('resposta', 'sem_dado'), 'SEM DADO');
  assert.equal(INFO.rotulo('modo', 'busca'), 'a coleta falhou: edição feita por busca');
  assert.equal(INFO.rotulo('tipoVeiculo', 'think_tank'), 'centro de estudos');
  assert.equal(INFO.rotulo('origem', 'rotina'), 'incluído pela rotina');
  assert.equal(INFO.rotulo('janela', '7d'), 'em 7 dias');
  assert.equal(INFO.rotulo('frequencia', 'diaria'), 'diária');
  assert.equal(INFO.rotulo('categoria', 'esporte'), 'esporte');
  /* nome que todo objeto herda não é rótulo */
  assert.equal(INFO.rotulo('categoria', 'constructor'), 'constructor');
  assert.equal(INFO.rotulo('categoria', 'toString'), 'toString');
  assert.equal(INFO.rotulo('categoria', '__proto__'), '__proto__');
  assert.equal(INFO.rotulo('categoria', null), '');
  assert.equal(INFO.semAcento('São PAULO, ação'), 'sao paulo, acao');
});

test('endereços: só http e https passam por new URL', async () => {
  const { INFO } = (await abre()).janela;
  assert.equal(INFO.enderecoSeguro('https://exemplo.invalid/a?b=1#c'), 'https://exemplo.invalid/a?b=1#c');
  assert.equal(INFO.enderecoSeguro('http://exemplo.invalid'), 'http://exemplo.invalid/');
  const recusados = ['javascript:alert(1)', 'JaVaScRiPt:alert(1)', ' javascript:alert(1)', 'java\tscript:alert(1)',
    'java\nscript:alert(1)', 'data:text/html,<script>alert(1)</script>', 'vbscript:msgbox(1)', 'file:///etc/passwd',
    'ftp://exemplo.invalid/', 'blob:https://exemplo.invalid/1', '//exemplo.invalid/a', '/caminho', 'exemplo.invalid',
    'edicoes/2026-11-19.json', '#/arquivo', '', 'http://', 'https://', null, undefined, 42, {}, ['https://exemplo.invalid/'],
    /* como a regra de URL do validador (seg-03, fer-04): barra invertida e usuário ou senha antes do @ */
    'https://exemplo.invalid\\@outro.invalid/', 'https:\\\\exemplo.invalid/a', 'https://usuario@exemplo.invalid/',
    'https://usuario:senha@exemplo.invalid/', 'https://:senha@exemplo.invalid/'];
  recusados.forEach((endereco) => assert.equal(INFO.enderecoSeguro(endereco), null, String(endereco)));
});

test('o DOM falso acusa o que o site não pode usar', () => {
  const { documento, janela } = criaJanela('<!doctype html><html lang="pt-BR"><head><title>t</title></head><body><p id="p">a</p></body></html>',
    { agora: AGORA, arquivos: {} });
  const p = documento.getElementById('p');
  assert.throws(() => { p.innerHTML = '<b>x</b>'; }, /uso proibido no site: innerHTML/);
  assert.throws(() => p.innerHTML, /innerHTML/);
  assert.throws(() => { p.outerHTML = '<b>x</b>'; }, /outerHTML/);
  assert.throws(() => p.outerHTML, /outerHTML/);
  assert.throws(() => p.insertAdjacentHTML('beforeend', '<b>x</b>'), /insertAdjacentHTML/);
  assert.throws(() => documento.write('<b>x</b>'), /document\.write/);
  assert.throws(() => documento.writeln('x'), /document\.writeln/);
  assert.throws(() => p.setAttribute('style', 'color:red'), /atributo style/);
  assert.throws(() => p.setAttribute('onclick', 'alert(1)'), /atributo de evento/);
  assert.throws(() => p.setAttribute('ONERROR', 'alert(1)'), /atributo de evento/);
  assert.throws(() => documento.cookie, /cookie/);
  assert.throws(() => { documento.cookie = 'a=1'; }, /cookie/);
  assert.throws(() => janela.localStorage, /localStorage/);
  assert.throws(() => janela.sessionStorage, /sessionStorage/);
  assert.throws(() => new janela.Date('2026-11-19'), /data sem hora/);
  assert.throws(() => janela.Date.parse('2026-11-19'), /data sem hora/);
  assert.throws(() => new janela.Date(2026, 10, 19), /fuso da máquina/);
  assert.throws(() => janela.fetch('https://exemplo.invalid/x.json'), /pedido para fora do site/);
  assert.throws(() => janela.history.pushState(null, '', '#/x'), /não cria passo/);
  assert.throws(() => janela.history.replaceState(null, '', 'outra.html'), /não é só o hash/);
  assert.equal(new janela.Date().getTime(), AGORA);
  assert.equal(janela.Date.now(), AGORA);
  p.textContent = '<img src=x onerror=alert(1)>';
  assert.equal(p.childNodes.length, 1);
  assert.equal(p.childNodes[0].nodeType, 3, 'textContent vira nó de texto, nunca elemento');
  /* cada acusação ficou guardada; estas eram esperadas */
  assert.equal(acusacoes.length, 20);
  acusacoes.length = 0;
});

test('o DOM falso recusa HTML torto no index.html', () => {
  const opcoes = { agora: AGORA, arquivos: {} };
  assert.throws(() => criaJanela('<html><body><p>a</div></body></html>', opcoes), /sem abertura correspondente/);
  assert.throws(() => criaJanela('<html><body><p>a</body></html>', opcoes), /sem abertura correspondente/);
  assert.throws(() => criaJanela('<html><body><p>a</p>', opcoes), /sem fecho/);
  assert.throws(() => criaJanela('<html><body><p>a < b</p></body></html>', opcoes), /marca torta/);
});
