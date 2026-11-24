'use strict';

/* Interação: filtros do radar, abrir e fechar, teclado, dicas, e datas que
 * não dependem do fuso da máquina. */

const test = require('node:test');
const assert = require('node:assert/strict');
const { abre, arquivos, edicaoReal, entradaSolta, textoDe, aVista, DIA, Evento } = require('./apoio.js');

const textos = (lista) => lista.map(textoDe);
const aVistaNoRadar = (m) => m.todos('.radar__item').filter(aVista).map((el) => el.getAttribute('id').replace('item-', ''));

/* Escolhe uma opção de uma lista nativa, como o leitor faria. */
async function escolhe(m, seletor, valor) {
  seletor.value = valor;
  seletor.dispatchEvent(new Evento('change'));
  await m.assenta();
}

test('filtros do radar: a categoria recorta na hora, vai para o endereço e a contagem é anunciada', async () => {
  const m = await abre();
  const [todas, geo, ia] = m.todos('.filtros__grupo button');
  assert.deepEqual([todas, geo, ia].map((b) => b.getAttribute('aria-pressed')), ['true', 'false', 'false']);
  assert.equal(textoDe(m.um('.filtros__contagem')), '');
  const pedidos = m.rede.pedidos.length;

  await m.clica(ia);
  assert.deepEqual(aVistaNoRadar(m), ['r1', 'r2', 'r3']);
  assert.deepEqual([todas, geo, ia].map((b) => b.getAttribute('aria-pressed')), ['false', 'false', 'true']);
  assert.equal(m.janela.location.hash, '#/?cat=ia');
  assert.equal(textoDe(m.um('.filtros__contagem')), '3 de 6 itens');
  assert.equal(textoDe(m.um('#anuncio')), '3 de 6 itens');
  assert.equal(m.rede.pedidos.length, pedidos, 'filtro não carrega nada');
  assert.deepEqual(m.historico, ['#/?cat=ia'], 'sem criar passo no histórico');

  await m.clica(geo);
  assert.deepEqual(aVistaNoRadar(m), ['r4', 'r5', 'r6']);
  assert.equal(m.janela.location.hash, '#/?cat=geopolitica');
  await m.clica(todas);
  assert.deepEqual(aVistaNoRadar(m), ['r1', 'r2', 'r3', 'r4', 'r5', 'r6']);
  assert.equal(m.janela.location.hash, '#/');
  assert.equal(textoDe(m.um('#anuncio')), '6 de 6 itens');
  /* a contagem dos botões é a do radar inteiro: filtrar não muda rótulo, cor nem ordem */
  assert.deepEqual(textos([todas, geo, ia]), ['Todas (6)', 'Geopolítica (3)', 'IA (3)']);
  assert.deepEqual(m.todos('.radar__item').map((el) => el.getAttribute('id')), ['item-r1', 'item-r2', 'item-r3', 'item-r4', 'item-r5', 'item-r6']);
});

test('filtros do radar: domínio e partido por lista nativa; os filtros se somam', async () => {
  const m = await abre();
  const [dominio, partido] = m.todos('.filtros select');
  await escolhe(m, dominio, 'energia');
  assert.deepEqual(aVistaNoRadar(m), ['r4']);
  assert.equal(m.janela.location.hash, '#/?dom=energia');
  await escolhe(m, dominio, 'suprimentos');
  assert.deepEqual(aVistaNoRadar(m), ['r1', 'r4']);
  await m.clica(m.todos('.filtros__grupo button')[2]);
  assert.deepEqual(aVistaNoRadar(m), ['r1'], 'IA e suprimentos');
  assert.equal(m.janela.location.hash, '#/?cat=ia&dom=suprimentos');
  await escolhe(m, partido, 'ordem_global');
  assert.deepEqual(aVistaNoRadar(m), ['r1'], 'a Wired atira do lado da Ordem Global');
  assert.equal(m.janela.location.hash, '#/?cat=ia&dom=suprimentos&partido=ordem_global');
  assert.equal(textoDe(m.um('.filtros__contagem')), '1 de 6 itens');
  await escolhe(m, partido, 'eixo_revisionista');
  assert.deepEqual(aVistaNoRadar(m), []);
  assert.equal(textoDe(m.um('#anuncio')), 'Nenhum item do radar com estes filtros.');
  await escolhe(m, dominio, '');
  await escolhe(m, partido, '');
  assert.deepEqual(aVistaNoRadar(m), ['r1', 'r2', 'r3']);
  assert.equal(m.janela.location.hash, '#/?cat=ia');
});

test('filtro de partido: casa com o placar, o lado do ataque, o alvo e os vetores', async () => {
  const m = await abre();
  const partido = m.todos('.filtros select')[1];
  const com = async (id) => { await escolhe(m, partido, id); return aVistaNoRadar(m); };
  /* lado do ataque: r1, r2, r3 (Wired, Wired, The Verge); vetor do Google para OG: r2; placar OG: r2 */
  assert.deepEqual(await com('ordem_global'), ['r1', 'r2', 'r3']);
  /* alvo player do partido (Jensen Huang em r1; Google em r2) e o partido como alvo (r3) */
  assert.deepEqual(await com('bancada_talento'), ['r1', 'r2', 'r3']);
  /* lado do ataque (Valor em r4, WSJ em r5) e placar (r4) */
  assert.deepEqual(await com('centrao'), ['r4', 'r5']);
  /* lado do ataque (Xinhua) e placar, em r6 */
  assert.deepEqual(await com('eixo_revisionista'), ['r6']);
  /* o partido como alvo (r6) */
  assert.deepEqual(await com('centro_atlantico'), ['r6']);
  /* só o placar (r6) */
  assert.deepEqual(await com('independentes'), ['r6']);
  assert.deepEqual(await com('soberanistas'), []);
});

test('filtro de partido: alvo "outro" e alvo "nenhum" não casam com partido nenhum; vetor casa pelo player e pelo destino', async () => {
  const edicao = edicaoReal(DIA, (e) => {
    e.radar.forEach((item) => { item.placar = []; item.vetores = []; item.ataque.lado = 'centrao'; item.ataque.alvo = 'nenhum'; });
    e.radar[0].ataque.alvo = 'outro';
    e.radar[0].ataque.alvo_nome = 'Soberanistas de Exemplo';
    /* um player novo que se chama "outro" não muda a regra */
    e.novos_players[0].id = 'outro';
    e.novos_players[0].partido = 'soberanistas';
    e.radar[1].vetores = [{ player: 'ue', para: 'soberanistas', forca: 1, tema: 'imigracao', porque: 'Teste.', url: 'https://exemplo.invalid/v' }];
    e.radar[2].ataque.alvo = 'fox';
  });
  const m = await abre({ arquivos: arquivos({ edicoes: [edicao] }) });
  const partido = m.todos('.filtros select')[1];
  await escolhe(m, partido, 'soberanistas');
  assert.deepEqual(aVistaNoRadar(m), ['r2', 'r3'], 'r2 pelo destino do vetor; r3 pelo alvo (o player Fox News é soberanista)');
  await escolhe(m, partido, 'centro_atlantico');
  assert.deepEqual(aVistaNoRadar(m), ['r2'], 'pelo partido do player do vetor (União Europeia)');
  await escolhe(m, partido, 'centrao');
  assert.equal(aVistaNoRadar(m).length, 6, 'todos pelo lado do ataque');
});

test('filtros: valor fora da lista no endereço é ignorado, e o que vale volta do endereço', async () => {
  let m = await abre({ hash: '#/?cat=esporte&dom=marte&partido=ninguem' });
  assert.equal(aVistaNoRadar(m).length, 6);
  assert.deepEqual(m.todos('.filtros select').map((s) => s.value), ['', '']);
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0, 'parâmetro torto não é endereço não encontrado');

  m = await abre({ hash: '#/?dom=cambio&cat=esporte' });
  assert.deepEqual(aVistaNoRadar(m), ['r5']);
  /* trocar de endereço troca os filtros; voltar ao Painel limpa */
  await m.vai('#/?partido=independentes');
  assert.deepEqual(aVistaNoRadar(m), ['r6']);
  assert.deepEqual(m.todos('.filtros select').map((s) => s.value), ['', 'independentes']);
  await m.vai('#/');
  assert.equal(aVistaNoRadar(m).length, 6);
});

test('abrir e fechar: um botão por dobra, com aria-expanded e aria-controls; o conteúdo usa hidden', async () => {
  const m = await abre({ arquivos: arquivos({ edicoes: [edicaoReal(DIA)], entradas: [entradaSolta('2026-11-18', { nivel: 2 })] }) });
  const botoes = m.todos('button[aria-controls]');
  /* 5 domínios, 3 principais, 6 do radar, a errata e a tabela da fita */
  assert.equal(botoes.length, 16);
  const ids = new Set();
  botoes.forEach((botao) => {
    const corpo = m.documento.getElementById(botao.getAttribute('aria-controls'));
    assert.ok(corpo, 'aria-controls aponta para um elemento que existe');
    assert.equal(ids.has(corpo.getAttribute('id')), false, 'ids únicos');
    ids.add(corpo.getAttribute('id'));
    assert.equal(botao.getAttribute('type'), 'button');
    assert.equal(botao.getAttribute('aria-expanded'), 'false', 'tudo começa fechado');
    assert.equal(corpo.hasAttribute('hidden'), true);
    assert.ok(corpo.classList.contains('dobra__corpo'), 'a impressão abre o que tem esta classe');
    assert.ok(textoDe(botao).length > 0, 'todo botão tem nome');
  });
  for (const botao of botoes) {
    const corpo = m.documento.getElementById(botao.getAttribute('aria-controls'));
    await m.clica(botao);
    assert.equal(botao.getAttribute('aria-expanded'), 'true');
    assert.equal(corpo.hasAttribute('hidden'), false);
  }
  assert.equal(m.todos('button[aria-expanded="true"]').length, 16, 'abrir um não fecha o outro');
  for (const botao of botoes) {
    const corpo = m.documento.getElementById(botao.getAttribute('aria-controls'));
    await m.clica(botao);
    assert.equal(botao.getAttribute('aria-expanded'), 'false');
    assert.equal(corpo.hasAttribute('hidden'), true);
  }
});

test('abrir e fechar: o toque no cabeçalho de domínio e de radar abre; toque em link não', async () => {
  const m = await abre();
  const cabeca = m.um('#dominio-suprimentos .dominio__cabeca');
  const botao = cabeca.querySelector('button');
  await m.clica(cabeca.querySelector('h3'));
  assert.equal(botao.getAttribute('aria-expanded'), 'true');
  await m.clica(cabeca.querySelector('.dominio__tendencia'));
  assert.equal(botao.getAttribute('aria-expanded'), 'false');
  await m.clica(botao);
  assert.equal(botao.getAttribute('aria-expanded'), 'true', 'o clique no botão conta uma vez só');

  const radar = m.um('#item-r4 .radar__cabeca');
  await m.clica(radar.querySelector('h3'));
  assert.equal(radar.querySelector('button').getAttribute('aria-expanded'), 'true');
  /* a sigla do partido é link para a Régua: segue o link, sem fechar a linha */
  const sigla = radar.querySelector('.etiqueta--partido');
  sigla.dispatchEvent(new Evento('click'));
  await m.assenta();
  assert.equal(radar.querySelector('button').getAttribute('aria-expanded'), 'true');
  /* o cartão de principal só abre pelo botão */
  await m.clica(m.um('#item-p1 h3'));
  assert.equal(m.um('#item-p1 .principal__pe button').getAttribute('aria-expanded'), 'false');
});

test('teclado: Esc fecha a dobra onde está o foco e devolve o foco ao botão', async () => {
  const m = await abre();
  const botao = m.um('#item-p1 .principal__pe button');
  await m.clica(botao);
  /* o foco está num link dentro do dossiê */
  m.um('#item-p1 .dossie a.externo').focus();
  m.tecla('Escape');
  assert.equal(botao.getAttribute('aria-expanded'), 'false');
  assert.equal(m.documento.activeElement, botao);
  assert.equal(m.janela.location.hash, '#/edicao/2026-11-19', 'fechar por Esc também grava o endereço');
  /* com o foco no próprio botão de uma dobra aberta */
  const dominio = m.um('#dominio-energia button');
  await m.clica(dominio);
  dominio.focus();
  m.tecla('Escape');
  assert.equal(dominio.getAttribute('aria-expanded'), 'false');
  /* Esc fora de dobra não faz nada; não há atalho de uma tecla */
  const abertosAntes = m.todos('button[aria-expanded="true"]').length;
  m.um('nav a').focus();
  m.tecla('Escape');
  ['j', 'k', '?', '/', 'g', '1', 'Enter', ' '].forEach((tecla) => m.tecla(tecla));
  assert.equal(m.todos('button[aria-expanded="true"]').length, abertosAntes);
  assert.equal(m.janela.location.hash, '#/edicao/2026-11-19');
});

test('teclado: Esc fecha só a dobra mais de dentro', async () => {
  const m = await abre();
  /* a linha do radar aberta e, fora dela, uma principal aberta */
  await m.clica(m.um('#item-p2 .principal__pe button'));
  await m.clica(m.um('#item-r2 button'));
  m.um('#item-r2 .radar__corpo a').focus();
  m.tecla('Escape');
  assert.equal(m.um('#item-r2 button').getAttribute('aria-expanded'), 'false');
  assert.equal(m.um('#item-p2 .principal__pe button').getAttribute('aria-expanded'), 'true', 'a outra fica como estava');
});

test('dicas: o gatilho recebe foco, o texto vai no nome acessível, e Esc fecha a dica antes de fechar a dobra', async () => {
  const m = await abre();
  await m.clica(m.um('#dominio-suprimentos button'));
  const etiqueta = m.um('#dominio-suprimentos .gatilho .tem-dica');
  assert.equal(etiqueta.getAttribute('tabindex'), '0');
  assert.match(textoDe(etiqueta), /^EXCEÇÃO: Fato fora da tabela de critérios/);
  etiqueta.focus();
  assert.equal(etiqueta.classList.contains('dica-fechada'), false, 'com o foco, o CSS abre a dica');
  m.tecla('Escape');
  assert.equal(etiqueta.classList.contains('dica-fechada'), true, 'Esc fecha a dica');
  assert.equal(m.um('#dominio-suprimentos button').getAttribute('aria-expanded'), 'true', 'a dobra continua aberta');
  m.tecla('Escape');
  assert.equal(m.um('#dominio-suprimentos button').getAttribute('aria-expanded'), 'false', 'o segundo Esc fecha a dobra');
  /* a dica volta a abrir no próximo foco ou ponteiro */
  etiqueta.blur();
  assert.equal(etiqueta.classList.contains('dica-fechada'), false);
  etiqueta.dispatchEvent(new Evento('mouseenter', { bubbles: false }));
  m.tecla('Escape');
  assert.equal(etiqueta.classList.contains('dica-fechada'), true, 'Esc também fecha a dica aberta pelo ponteiro');
  etiqueta.dispatchEvent(new Evento('mouseleave', { bubbles: false }));
  assert.equal(etiqueta.classList.contains('dica-fechada'), false);
  /* as dicas que a edição de exemplo traz (a de ALÍVIO tem teste próprio) */
  const dicas = new Set(m.todos('.tem-dica').map((el) => el.childNodes[0].textContent));
  ['EXCEÇÃO', 'PERGUNTA-CHAVE', 'anterior', 'sem alvo'].forEach((nome) => assert.ok(dicas.has(nome), nome));
  m.todos('.tem-dica').forEach((el) => {
    assert.equal(el.querySelector('.dica').getAttribute('aria-hidden'), 'true');
    assert.ok(textoDe(el.querySelector('.so-leitor')).length > 10);
  });
});

test('fita: o ponteiro abre a dica do dia (valor primeiro, rótulo depois) e Esc fecha', async () => {
  const m = await abre({ arquivos: arquivos({ edicoes: [edicaoReal(DIA)], entradas: [
    entradaSolta('2026-11-18', { nivel: 2 }), entradaSolta('2026-11-17', { estado: 'falha', nivel: 2 })] }) });
  const fita = m.um('.fita');
  const dica = fita.querySelector('.dica');
  const dias = fita.querySelectorAll('a.fita__dia');
  assert.equal(dica.classList.contains('dica--aberta'), false);
  dias[2].dispatchEvent(new Evento('mouseenter', { bubbles: false }));
  assert.equal(dica.classList.contains('dica--aberta'), true);
  assert.equal(textoDe(dica), 'nível 3 TENSÃO 19/11');
  assert.equal(textoDe(dica.querySelector('.dica__valor')), 'nível 3 TENSÃO');
  dias[0].dispatchEvent(new Evento('mouseenter', { bubbles: false }));
  assert.equal(textoDe(dica), 'sem edição 17/11');
  m.tecla('Escape');
  assert.equal(dica.classList.contains('dica--aberta'), false);
  dias[1].dispatchEvent(new Evento('mouseenter', { bubbles: false }));
  assert.equal(textoDe(dica), 'nível 2 ATENÇÃO 18/11');
  fita.dispatchEvent(new Evento('mouseleave', { bubbles: false }));
  assert.equal(dica.classList.contains('dica--aberta'), false);
  /* o clique leva à edição */
  await m.clica(dias[1]);
  assert.equal(m.janela.location.hash, '#/edicao/2026-11-18');
});

test('fita: com menos de 2 edições no histórico, ela não aparece', async () => {
  const m = await abre({ arquivos: arquivos({ edicoes: [edicaoReal(DIA)] }) });
  assert.equal(m.um('.fita'), null);
  assert.equal(m.um('.historico'), null);
});

test('datas: nenhuma data AAAA-MM-DD passa por Date', async () => {
  const m = await abre({ arquivos: arquivos({ edicoes: [edicaoReal(DIA)], entradas: [
    entradaSolta('2026-11-18', { nivel: 2 }), entradaSolta('2026-10-25', { nivel: 1 })] }) });
  m.relogio.avanca(3 * 60000);
  await m.vai('#/edicao/2026-11-19/p1');
  assert.ok(m.datasRecebidas.length > 0);
  m.datasRecebidas.forEach((args) => {
    assert.equal(args.length, 1);
    const valor = args[0];
    /* só data-hora UTC do contrato, ou um instante em milissegundos */
    assert.ok(typeof valor === 'number' || /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(valor), 'Date recebeu ' + JSON.stringify(valor));
  });
  /* o DOM falso lança erro se o site entregar data sem hora a Date: chegar até aqui já é a prova */
  assert.equal(textoDe(m.um('h1')), 'Edição de 19/11/2026');
});

test('datas: o dia e a hora de Brasília não mudam com o fuso da máquina', async () => {
  const fusoAntes = process.env.TZ;
  const tabela = () => arquivos({ edicoes: [edicaoReal(DIA, (e) => { e.gerada_em = '2026-11-20T02:30:00Z'; })],
    entradas: [entradaSolta('2026-11-18', { nivel: 2 }), entradaSolta('2026-10-21', { nivel: 1 })] });
  const vistos = {};
  try {
    for (const fuso of ['Pacific/Kiritimati', 'Pacific/Pago_Pago', 'UTC', 'America/Sao_Paulo', 'Asia/Kolkata']) {
      process.env.TZ = fuso;
      const m = await abre({ arquivos: tabela(), agora: Date.UTC(2026, 10, 20, 2, 48, 0) });
      vistos[fuso] = [
        textoDe(m.um('.carimbo__texto')),
        m.todos('time').map((t) => t.getAttribute('datetime') + '=' + t.textContent).join(' '),
        textoDe(m.um('.fita__datas')),
        m.todos('a.fita__dia').map((a) => a.getAttribute('href')).join(' '),
        m.documento.title
      ].join(' | ');
    }
  } finally {
    if (fusoAntes === undefined) { delete process.env.TZ; } else { process.env.TZ = fusoAntes; }
  }
  const esperado = vistos.UTC;
  assert.match(esperado, /^ED\. 19\/11\/2026 · GERADA 23h30 \(BRASÍLIA\) · HÁ 18 MIN \| /, 'gerada às 2h30 UTC do dia 20: ainda 23h30 do dia 19 em Brasília');
  assert.match(esperado, /\| 21\/10 19\/11 \| #\/edicao\/2026-10-21 #\/edicao\/2026-11-18 #\/edicao\/2026-11-19 \| INFOCENARIUM · 19\/11\/2026/);
  Object.keys(vistos).forEach((fuso) => assert.equal(vistos[fuso], esperado, fuso));
});

test('rede de segurança: se a montagem quebrar, o último quadro bom fica na tela, funcionando, com aviso', async () => {
  const m = await abre({ arquivos: arquivos({ edicoes: [edicaoReal('2026-11-18'), edicaoReal(DIA)] }) });
  await m.clica(m.um('#item-p1 .principal__pe button'));
  /* sabota a criação de <article> para a próxima montagem */
  const criaDeVerdade = m.documento.createElement;
  m.documento.createElement = function (nome) {
    if (nome === 'article') { throw new Error('quebra plantada pelo teste'); }
    return criaDeVerdade.call(m.documento, nome);
  };
  await m.vai('#/edicao/2026-11-18');
  assert.match(textoDe(m.um('#avisos-gerais .aviso')), /^FALHA AO CARREGAR Não deu para carregar edicoes\/2026-11-18\.json\./);
  assert.equal(textoDe(m.um('h1')), 'Edição de 19/11/2026');
  assert.equal(m.um('#vista').hasAttribute('aria-busy'), false, 'a tela não fica presa em "Carregando"');
  assert.equal(aVista(m.um('.carimbo__texto')), true);
  /* o quadro antigo segue vivo: Esc ainda fecha a dobra dele */
  m.um('#item-p1 .dossie a.externo').focus();
  m.tecla('Escape');
  assert.equal(m.um('#item-p1 .principal__pe button').getAttribute('aria-expanded'), 'false');
  assert.equal(m.janela.location.hash, '#/edicao/2026-11-19', 'mexer no quadro antigo leva o endereço de volta para ele');
  /* "Tentar de novo" refaz a carga que o aviso cita, e não a do endereço de agora */
  m.documento.createElement = criaDeVerdade;
  await m.clica(m.um('#avisos-gerais .aviso button'));
  assert.equal(textoDe(m.um('h1')), 'Edição de 18/11/2026');
  assert.equal(m.janela.location.hash, '#/edicao/2026-11-18');
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
});
