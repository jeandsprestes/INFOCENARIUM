'use strict';

/* As rotas por hash que tocam o Painel, o dossiê e a edição antiga, e o que
 * acontece com o endereço, o foco e a navegação em cada uma. Das vistas
 * Arquivo, Régua e Método, aqui se confere só que a rota chega nelas: o
 * conteúdo de cada uma tem arquivo de teste próprio. */

const test = require('node:test');
const assert = require('node:assert/strict');
const { abre, arquivos, edicaoReal, textoDe, aVista, DIA } = require('./apoio.js');

const textos = (lista) => lista.map(textoDe);

function duasEdicoes() {
  return arquivos({ edicoes: [edicaoReal('2026-11-18'), edicaoReal(DIA)] });
}

const abertos = (m) => m.todos('.principal, .radar__item, .dominio')
  .filter((el) => el.querySelector('button[aria-controls]').getAttribute('aria-expanded') === 'true')
  .map((el) => el.getAttribute('id'));

test('#/ é o Painel: a edição mais recente, com "Painel" aceso', async () => {
  for (const hash of ['', '#', '#/']) {
    const m = await abre({ arquivos: duasEdicoes(), hash });
    assert.equal(textoDe(m.um('h1')), 'Edição de 19/11/2026', hash);
    assert.equal(m.um('nav a[aria-current="page"]').textContent, 'Painel');
    assert.equal(m.um('#vista').getAttribute('class'), 'vista vista--painel');
    assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
    assert.deepEqual(abertos(m), [], 'tudo começa fechado');
  }
});

test('#/?cat=…&dom=…&partido=…: o Painel com os filtros do radar', async () => {
  const m = await abre({ hash: '#/?cat=geopolitica&dom=suprimentos&partido=centrao' });
  assert.deepEqual(m.todos('.radar__item').filter(aVista).map((el) => el.getAttribute('id')), ['item-r4']);
  assert.deepEqual(m.todos('.filtros__grupo button').map((b) => b.getAttribute('aria-pressed')), ['false', 'true', 'false']);
  assert.deepEqual(m.todos('.filtros select').map((s) => s.value), ['suprimentos', 'centrao']);
  assert.equal(textoDe(m.um('.filtros__contagem')), '1 de 6 itens');
  assert.equal(m.janela.location.hash, '#/?cat=geopolitica&dom=suprimentos&partido=centrao', 'o endereço fica como veio');
});

test('#/edicao/AAAA-MM-DD: a edição daquele dia', async () => {
  const m = await abre({ arquivos: duasEdicoes(), hash: '#/edicao/2026-11-18' });
  assert.equal(textoDe(m.um('h1')), 'Edição de 18/11/2026');
  assert.deepEqual(textos(m.todos('#carimbo .placa')), ['ARQUIVO']);
  assert.deepEqual(m.rede.pedidos.map((p) => p.caminho).filter((c) => c.startsWith('edicoes/')).sort(),
    ['edicoes/2026-11-18.json', 'edicoes/indice.json'], 'só a edição pedida é lida');
});

test('#/edicao/AAAA-MM-DD/p2: abre o item, rola e põe o foco no título', async () => {
  const m = await abre({ hash: '#/edicao/2026-11-19/p2' });
  assert.deepEqual(abertos(m), ['item-p2'], 'abre só o item pedido');
  const titulo = m.um('#item-p2 h3');
  assert.equal(m.documento.activeElement, titulo);
  assert.equal(titulo.getAttribute('tabindex'), '-1');
  assert.deepEqual(m.documento.rolagens, [titulo]);
  assert.equal(aVista(m.um('#item-p2 .dossie')), true);
  assert.equal(m.janela.location.hash, '#/edicao/2026-11-19/p2');
  assert.equal(m.um('nav a[aria-current="page"]').textContent, 'Painel', 'é a edição mais recente: a vista é o Painel');
});

test('ordem de procura do id: principal, radar, domínio, indicador', async () => {
  let m = await abre({ hash: '#/edicao/2026-11-19/r4' });
  assert.deepEqual(abertos(m), ['item-r4']);
  assert.equal(m.documento.activeElement, m.um('#item-r4 h3'));

  m = await abre({ hash: '#/edicao/2026-11-19/energia' });
  assert.deepEqual(abertos(m), ['dominio-energia'], 'o id de um domínio abre a linha do domínio');
  assert.equal(m.documento.activeElement, m.um('#dominio-energia h3'));

  m = await abre({ hash: '#/edicao/2026-11-19/brent' });
  assert.deepEqual(abertos(m), []);
  assert.equal(m.documento.activeElement, m.um('#ind-brent'), 'o id de um indicador põe a ficha em foco');
  assert.equal(m.um('#ind-brent').getAttribute('tabindex'), '-1');
  assert.deepEqual(m.documento.rolagens, [m.um('#ind-brent')]);

  /* id que serve a dois: vale o item, que vem antes na procura */
  const tabela = arquivos({ edicoes: [edicaoReal(DIA, (e) => { e.indicadores[0].id = 'p1'; })] });
  m = await abre({ arquivos: tabela, hash: '#/edicao/2026-11-19/p1' });
  assert.deepEqual(abertos(m), ['item-p1']);
});

test('#/edicao/…/r4?cat=ia: os filtros valem junto; se esconderiam o item pedido, saem', async () => {
  let m = await abre({ hash: '#/edicao/2026-11-19/r2?cat=ia' });
  assert.deepEqual(abertos(m), ['item-r2']);
  assert.deepEqual(m.todos('.radar__item').filter(aVista).map((el) => el.getAttribute('id')), ['item-r1', 'item-r2', 'item-r3']);

  m = await abre({ hash: '#/edicao/2026-11-19/r4?cat=ia' });
  assert.deepEqual(abertos(m), ['item-r4']);
  assert.equal(aVista(m.um('#item-r4')), true, 'o item do endereço nunca fica escondido por filtro');
  assert.equal(m.todos('.radar__item').filter(aVista).length, 6);
});

test('Arquivo, Régua e Método abrem com título, navegação e título da aba', async () => {
  const casos = [
    ['#/arquivo', 'Arquivo', 'vista vista--arquivo', '#/arquivo'],
    ['#/arquivo?nivel=3', 'Arquivo', 'vista vista--arquivo', '#/arquivo?nivel=3'],
    ['#/regua', 'Régua', 'vista vista--regua', '#/regua/partidos'],
    ['#/regua/partidos', 'Régua', 'vista vista--regua', '#/regua/partidos'],
    ['#/regua/partidos/soberanistas', 'Régua', 'vista vista--regua', '#/regua/partidos/soberanistas'],
    ['#/regua/players/macron', 'Régua', 'vista vista--regua', '#/regua/players/macron'],
    ['#/regua/players?partido=centrao&q=mac', 'Régua', 'vista vista--regua', '#/regua/players?partido=centrao&q=mac'],
    ['#/regua/veiculos/reuters', 'Régua', 'vista vista--regua', '#/regua/veiculos/reuters'],
    ['#/regua/vetores?player=ue', 'Régua', 'vista vista--regua', '#/regua/vetores?player=ue'],
    ['#/regua/vetores/2026-11-20_p1_ue', 'Régua', 'vista vista--regua', '#/regua/vetores/2026-11-20_p1_ue'],
    ['#/metodo', 'Método', 'vista vista--metodo', '#/metodo'],
    ['#/metodo/niveis', 'Método', 'vista vista--metodo', '#/metodo/niveis'],
    ['#/metodo/conflito', 'Método', 'vista vista--metodo', '#/metodo/conflito']
  ];
  for (const [hash, nome, classe, endereco] of casos) {
    const m = await abre({ hash });
    const h1 = m.todos('h1');
    assert.equal(h1.length, 1, hash);
    assert.equal(textoDe(h1[0]), nome, hash);
    assert.equal(h1[0].classList.contains('so-leitor'), false, 'título visível nas outras vistas');
    assert.equal(m.um('#vista').getAttribute('class'), classe, hash);
    assert.equal(m.um('#vista').hasAttribute('aria-busy'), false, hash);
    assert.equal(m.um('nav a[aria-current="page"]').textContent, nome, hash);
    assert.equal(m.documento.title, 'INFOCENARIUM · ' + nome, hash);
    assert.equal(m.janela.location.hash, endereco, hash);
    assert.equal(m.todos('#s-hoje, #s-carimbo, .grade-painel, .alerta').length, 0, 'só uma vista existe no documento por vez');
    assert.equal(m.um('#vista').children.length, 2, 'a vista é o título e o corpo');
    assert.ok(textoDe(m.um('.vista__corpo')).length > 200, hash + ': a vista tem conteúdo');
    assert.equal(/ainda não está pronta/.test(textoDe(m.um('main'))), false, hash);
    /* o registro de vetores dos dados congelados é vazio: só essa rota pede uma ficha que não existe */
    assert.equal(m.todos('#avisos-gerais .aviso').length, hash === '#/regua/vetores/2026-11-20_p1_ue' ? 1 : 0, hash);
  }
});

test('#/regua vai para #/regua/partidos sem criar passo no histórico', async () => {
  const m = await abre({ hash: '#/regua' });
  assert.deepEqual(m.historico, ['#/regua/partidos']);
});

test('qualquer outra rota: o Painel, com o aviso de endereço não encontrado', async () => {
  for (const hash of ['#/nada', '#conteudo', '#/edicao/2026-13-45', '#/regua/abas', '#/metodo/segredo', '#/edicao/2026-11-19/P1']) {
    const m = await abre({ hash });
    assert.equal(textoDe(m.um('#avisos-gerais .aviso')), 'ENDEREÇO NÃO ENCONTRADO Mostrando o Painel.', hash);
    assert.equal(textoDe(m.um('h1')), 'Edição de 19/11/2026', hash);
    assert.equal(m.um('nav a[aria-current="page"]').textContent, 'Painel');
    assert.equal(textoDe(m.um('#anuncio')), 'ENDEREÇO NÃO ENCONTRADO Mostrando o Painel. Edição de 19/11/2026.');
  }
  /* o aviso sai na rota seguinte */
  const m = await abre({ hash: '#/nada' });
  await m.vai('#/');
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
});

test('endereço sem destino: edição que não existe abre o Arquivo, com aviso', async () => {
  const m = await abre({ arquivos: duasEdicoes(), hash: '#/edicao/2026-01-01' });
  assert.equal(textoDe(m.um('#avisos-gerais .aviso')), 'NÃO HÁ EDIÇÃO DE 01/01/2026 Mostrando o Arquivo.');
  assert.equal(textoDe(m.um('h1')), 'Arquivo');
  assert.equal(m.um('nav a[aria-current="page"]').textContent, 'Arquivo');
  assert.equal(m.um('#vista').hasAttribute('aria-busy'), false);
  assert.equal(textoDe(m.um('#anuncio')), 'NÃO HÁ EDIÇÃO DE 01/01/2026 Mostrando o Arquivo.');
  assert.equal(m.rede.pedidos.some((p) => p.caminho === 'edicoes/2026-01-01.json'), false, 'não pede arquivo que o índice não tem');
});

test('endereço sem destino: item que não existe abre a edição, sem abrir nada, com aviso', async () => {
  const m = await abre({ hash: '#/edicao/2026-11-19/p9' });
  assert.equal(textoDe(m.um('#avisos-gerais .aviso')), 'ITEM NÃO ENCONTRADO A edição de 19/11/2026 não tem o item p9.');
  assert.equal(textoDe(m.um('h1')), 'Edição de 19/11/2026');
  assert.deepEqual(abertos(m), []);
  /* numa edição sem itens (falha), todo item é "não encontrado" */
  await m.vai('#/edicao/2026-11-19/p1');
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
  assert.deepEqual(abertos(m), ['item-p1']);
});

test('ao trocar de rota: foco no h1, página no topo e título da aba novo; na primeira carga o foco não é tomado', async () => {
  const m = await abre({ arquivos: duasEdicoes() });
  assert.equal(m.documento.activeElement, m.documento.body, 'a primeira carga não rouba o foco');
  assert.deepEqual(m.janela.rolagens, []);
  await m.vai('#/edicao/2026-11-18');
  assert.equal(m.documento.activeElement, m.um('h1'));
  assert.equal(m.um('h1').getAttribute('tabindex'), '-1');
  assert.deepEqual(m.janela.rolagens, [[0, 0]]);
  assert.equal(m.documento.title, 'INFOCENARIUM · 18/11/2026 · nível 3 TENSÃO');
  await m.vai('#/metodo');
  assert.equal(m.documento.activeElement, m.um('h1'));
  assert.equal(m.documento.title, 'INFOCENARIUM · Método');
  assert.deepEqual(m.janela.rolagens, [[0, 0], [0, 0]]);
  await m.vai('#/');
  assert.equal(textoDe(m.documento.activeElement), 'Edição de 19/11/2026');
});

test('abrir um item grava o endereço dele sem criar passo no histórico; fechar grava o da edição', async () => {
  const m = await abre();
  const botao = m.um('#item-p2 .principal__pe button');
  await m.clica(botao);
  assert.equal(m.janela.location.hash, '#/edicao/2026-11-19/p2');
  assert.deepEqual(m.historico, ['#/edicao/2026-11-19/p2'], 'por replaceState');
  assert.equal(m.rede.pedidos.length, 7, 'abrir não carrega nada');
  /* mais de um item pode ficar aberto: abrir um não fecha o outro */
  await m.clica(m.um('#item-r4 button'));
  assert.equal(m.janela.location.hash, '#/edicao/2026-11-19/r4');
  assert.deepEqual(abertos(m), ['item-p2', 'item-r4']);
  await m.clica(m.um('#dominio-energia button'));
  assert.equal(m.janela.location.hash, '#/edicao/2026-11-19/energia');
  assert.deepEqual(abertos(m).sort(), ['dominio-energia', 'item-p2', 'item-r4']);
  await m.clica(m.um('#item-r4 button'));
  assert.equal(m.janela.location.hash, '#/edicao/2026-11-19', 'fechar grava de volta o endereço da edição');
  assert.deepEqual(abertos(m).sort(), ['dominio-energia', 'item-p2']);
  assert.equal(textoDe(m.um('h1')), 'Edição de 19/11/2026');
  assert.equal(m.um('nav a[aria-current="page"]').textContent, 'Painel');
});

test('abrir um item leva junto os filtros que houver', async () => {
  const m = await abre({ hash: '#/?cat=ia' });
  await m.clica(m.um('#item-r2 button'));
  assert.equal(m.janela.location.hash, '#/edicao/2026-11-19/r2?cat=ia');
  await m.clica(m.um('#item-r2 button'));
  assert.equal(m.janela.location.hash, '#/edicao/2026-11-19?cat=ia');
});

test('recarregar a página no endereço de um item aberto no Painel mostra o Painel, com o item aberto', async () => {
  const m = await abre({ arquivos: duasEdicoes() });
  await m.clica(m.um('#item-p1 .principal__pe button'));
  const m2 = await abre({ arquivos: duasEdicoes(), hash: m.janela.location.hash });
  assert.deepEqual(textos(m2.todos('#carimbo .placa')), ['EM DIA']);
  assert.equal(m2.um('nav a[aria-current="page"]').textContent, 'Painel');
  assert.deepEqual(abertos(m2), ['item-p1']);
});

test('link para outra parte da mesma página é rota: abre, rola e põe o foco, sem recarregar', async () => {
  const m = await abre();
  await m.clica(m.um('#dominio-energia button'));
  const link = m.todos('#dominio-energia .gatilho__ref a')[1];
  assert.equal(textoDe(link), 'ver principal 1');
  await m.clica(link);
  assert.equal(m.janela.location.hash, '#/edicao/2026-11-19/p1');
  assert.deepEqual(abertos(m).sort(), ['dominio-energia', 'item-p1']);
  assert.equal(m.documento.activeElement, m.um('#item-p1 h3'));
  assert.equal(m.rede.pedidos.length, 7, 'a mesma edição não é lida de novo');
  /* o leitor fecha o item à mão e clica no mesmo link: o endereço mudou ao fechar */
  await m.clica(m.um('#item-p1 .principal__pe button'));
  await m.clica(link);
  assert.deepEqual(abertos(m).sort(), ['dominio-energia', 'item-p1']);
  /* o endereço já é o do link: o navegador não avisa, e o site refaz a rota assim mesmo */
  m.um('#item-p1 .dossie').setAttribute('hidden', '');
  const foco = m.um('#item-p2 h3');
  foco.focus();
  await m.clica(link);
  assert.equal(m.documento.activeElement, m.um('#item-p1 h3'), 'o link nunca fica morto');
  /* link para indicador e para domínio */
  await m.clica(m.todos('#dominio-energia .gatilho__ref a')[0]);
  assert.equal(m.documento.activeElement, m.um('#ind-brent'));
  await m.clica(m.um('#ind-usd_brl a.etiqueta'));
  assert.equal(m.documento.activeElement, m.um('#dominio-cambio h3'));
  assert.ok(abertos(m).includes('dominio-cambio'));
});

test('vizinhas: andam pelo índice, uma entrada por vez; na primeira e na última o botão não aparece', async () => {
  const m = await abre({ arquivos: arquivos({ edicoes: [edicaoReal('2026-11-17'), edicaoReal('2026-11-18'), edicaoReal(DIA)] }) });
  const vizinhas = () => m.todos('a.vizinha').map((a) => [textoDe(a.querySelector('.so-leitor')), a.getAttribute('href')]);
  assert.deepEqual(vizinhas(), [['Edição anterior, de 18/11/2026', '#/edicao/2026-11-18']]);
  await m.clica(m.um('a.vizinha'));
  assert.equal(textoDe(m.um('h1')), 'Edição de 18/11/2026');
  assert.deepEqual(vizinhas(), [['Edição anterior, de 17/11/2026', '#/edicao/2026-11-17'], ['Edição seguinte, de 19/11/2026', '#/edicao/2026-11-19']]);
  await m.clica(m.um('a.vizinha'));
  assert.equal(textoDe(m.um('h1')), 'Edição de 17/11/2026');
  assert.deepEqual(vizinhas(), [['Edição seguinte, de 18/11/2026', '#/edicao/2026-11-18']]);
  /* "Ir para a mais recente" */
  await m.clica(m.todos('.cabeca__acoes a').find((a) => textoDe(a) === 'Ir para a mais recente'));
  assert.equal(textoDe(m.um('h1')), 'Edição de 19/11/2026');
  assert.equal(m.janela.location.hash, '#/');
});

test('trocar de rota no meio de uma carga: a carga antiga é descartada', async () => {
  const m = await abre({ arquivos: duasEdicoes() });
  m.rede.segura = true;
  await m.vai('#/edicao/2026-11-18');
  assert.equal(m.um('#vista').getAttribute('aria-busy'), 'true');
  await m.vai('#/metodo');
  assert.equal(textoDe(m.um('h1')), 'Método');
  m.rede.solta();
  await m.assenta();
  assert.equal(textoDe(m.um('h1')), 'Método', 'a edição que chegou atrasada não toma a tela');
  assert.equal(m.um('nav a[aria-current="page"]').textContent, 'Método');
  /* e o relógio de "Está demorando" da carga abandonada não dispara aviso */
  m.relogio.avanca(9000);
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
  /* sair da edição também para o relógio da idade: o tempo anda sem erro */
  m.relogio.avanca(10 * 60000);
  await m.vai('#/edicao/2026-11-18');
  assert.equal(textoDe(m.um('h1')), 'Edição de 18/11/2026');
});

test('"Pular para o conteúdo" põe o foco no conteúdo e não mexe no endereço', async () => {
  const m = await abre({ hash: '#/edicao/2026-11-19/p1' });
  const pular = m.um('#pular');
  assert.equal(m.documento.body.children[0], pular, 'é o primeiro elemento da página');
  await m.clica(pular);
  assert.equal(m.janela.location.hash, '#/edicao/2026-11-19/p1');
  assert.equal(m.documento.activeElement, m.um('main'));
  assert.equal(m.um('main').getAttribute('tabindex'), '-1');
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
});

test('caminho de arquivo e de texto do índice só vale na forma edicoes/AAAA-MM-DD', async () => {
  const tabela = arquivos({ edicoes: [edicaoReal(DIA)] });
  const entrada = tabela['edicoes/indice.json'].edicoes[0];
  entrada.arquivo = '../segredo.json';
  entrada.texto = 'edicoes/2026-11-19.md?x=1';
  const m = await abre({ arquivos: tabela });
  assert.equal(textoDe(m.um('h1')), 'Edição de 19/11/2026');
  assert.ok(m.rede.pedidos.some((p) => p.caminho === 'edicoes/2026-11-19.json'), 'fora da forma, o caminho sai da data');
  assert.equal(m.rede.pedidos.some((p) => p.caminho.includes('segredo')), false);
  assert.deepEqual(m.todos('.cabeca__acoes a').slice(-3).map((a) => a.getAttribute('href')),
    ['edicoes/2026-11-19.md', 'edicoes/2026-11-19.json', 'feed.xml']);

  /* na forma certa, vale o caminho do índice, mesmo que a data dele seja outra */
  const outra = arquivos({ edicoes: [edicaoReal(DIA)] });
  outra['edicoes/indice.json'].edicoes[0].arquivo = 'edicoes/2026-11-01.json';
  outra['edicoes/2026-11-01.json'] = edicaoReal(DIA, (e) => { e.resumo = 'Veio do caminho do índice.'; });
  const m2 = await abre({ arquivos: outra });
  assert.equal(textoDe(m2.um('.alerta__resumo')), 'Veio do caminho do índice.');
});

test('entrada do índice com data torta ou repetida é ignorada', async () => {
  const tabela = arquivos({ edicoes: [edicaoReal(DIA)] });
  tabela['edicoes/indice.json'].edicoes.unshift(
    { data: '<img src=x onerror=alert(1)>', estado: 'completa', nivel: 5 },
    { data: '2026-99-99', estado: 'completa', nivel: 5 },
    null, 'x', 7,
    { data: '2026-11-19', estado: 'falha', nivel: 1, gerada_em: '2026-11-19T22:00:00Z' });
  tabela['edicoes/indice.json'].edicoes.reverse();
  const m = await abre({ arquivos: tabela });
  assert.equal(textoDe(m.um('h1')), 'Edição de 19/11/2026');
  assert.equal(m.todos('a.vizinha').length, 0);
});
