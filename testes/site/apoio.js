'use strict';

/* Apoio dos testes do site: carrega o assets/app.js de verdade dentro do DOM
 * falso, com os arquivos servidos de uma tabela e o relógio controlado.
 *
 * Os dados vêm da cópia congelada (testes/fixtures/dados/) e da edição de
 * exemplo (testes/fixtures/edicao-exemplo.json). Nada é gravado em disco:
 * cada teste recebe cópias e mexe nelas à vontade.
 */

const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { criaJanela, Evento, acusacoes } = require('./dom_falso.js');

const RAIZ = path.resolve(__dirname, '..', '..');
const ARQUIVO_HTML = path.join(RAIZ, 'index.html');
const ARQUIVO_APP = path.join(RAIZ, 'assets', 'app.js');
const ARQUIVO_CSS = path.join(RAIZ, 'assets', 'estilo.css');
const HTML = fs.readFileSync(ARQUIVO_HTML, 'utf8');
const ROTEIRO = new vm.Script(fs.readFileSync(ARQUIVO_APP, 'utf8'), { filename: 'assets/app.js' });

/* 18 minutos depois de a edição de exemplo ser gerada (21h14min03s UTC). */
const AGORA = Date.UTC(2026, 10, 19, 21, 32, 3);
const DIA = '2026-11-19';

/* O DOM falso lança erro em uso proibido. Se o site engolir esse erro num
   try/catch, a acusação ainda está guardada: o arquivo de teste falha no fim. */
process.on('exit', (codigo) => {
  if (acusacoes.length && codigo === 0) {
    process.stderr.write('O DOM falso acusou uso proibido que nenhum teste esperava:\n  ' + acusacoes.join('\n  ') + '\n');
    process.exitCode = 1;
  }
});

function leJson() {
  return JSON.parse(fs.readFileSync(path.join.apply(path, [RAIZ].concat(Array.from(arguments))), 'utf8'));
}

function copia(valor) {
  return JSON.parse(JSON.stringify(valor));
}

const CONGELADOS = {
  regua: leJson('testes', 'fixtures', 'dados', 'regua.json'),
  players: leJson('testes', 'fixtures', 'dados', 'players.json'),
  veiculos: leJson('testes', 'fixtures', 'dados', 'veiculos.json'),
  vetores: leJson('testes', 'fixtures', 'dados', 'vetores.json'),
  catalogo: leJson('testes', 'fixtures', 'dados', 'indicadores.json'),
  exemplo: leJson('testes', 'fixtures', 'edicao-exemplo.json')
};

/* Cópias novas dos dados congelados: o teste pode mexer. */
function dados() {
  return copia(CONGELADOS);
}

function edicaoDeExemplo() {
  return copia(CONGELADOS.exemplo);
}

/* A edição de exemplo sem as marcas de exemplo, numa data: faz as vezes de
   uma edição de verdade. mudancas(edicao) ajusta o que o teste quiser. */
function edicaoReal(data, mudancas) {
  const edicao = edicaoDeExemplo();
  delete edicao.exemplo;
  edicao.data = data;
  edicao.gerada_em = data + 'T21:14:03Z';
  const limpa = (t) => String(t).replace(/^\[EXEMPLO\] /, '');
  edicao.resumo = limpa(edicao.resumo);
  edicao.principais.concat(edicao.radar).forEach((item) => {
    item.titulo = limpa(item.titulo);
    item.fontes.forEach((fonte) => { fonte.titulo = limpa(fonte.titulo); });
  });
  if (mudancas) { mudancas(edicao); }
  return edicao;
}

/* Edição de estado falha: sem itens, níveis repetidos (ESQUEMA, regra R15). */
function edicaoFalha(data, base, mudancas) {
  const edicao = edicaoReal(data);
  edicao.estado = 'falha';
  edicao.resumo = 'A coleta e a busca falharam: sem rede na hora da rotina.';
  edicao.principais = [];
  edicao.radar = [];
  edicao.placar_do_dia = [];
  edicao.novos_players = [];
  edicao.errata = [];
  edicao.respostas = [];
  edicao.indicadores = edicao.indicadores.slice(0, 2);
  edicao.alerta.dominios.forEach((dominio) => { dominio.gatilhos = []; });
  if (base) {
    edicao.alerta.nivel = base.alerta.nivel;
    edicao.alerta.dominios.forEach((dominio, i) => { dominio.nivel = base.alerta.dominios[i].nivel; });
  }
  edicao.bastidores.limites = 'Nada foi conferido: a rotina não fechou a edição.';
  if (mudancas) { mudancas(edicao); }
  return edicao;
}

/* A entrada do índice de uma edição (ESQUEMA, seção 11).
   As tabelas nascem sem herança: assim um id de teste como "constructor" ou
   "__proto__" é só mais uma chave, como seria num JSON lido do disco. */
function entradaDoIndice(edicao, extras) {
  const niveis = Object.create(null);
  edicao.alerta.dominios.forEach((dominio) => { niveis[dominio.id] = dominio.nivel; });
  const saldos = Object.create(null);
  edicao.placar_do_dia.forEach((linha) => { saldos[linha.partido] = linha.saldo; });
  const eixos = Object.create(null);
  edicao.principais.concat(edicao.radar).forEach((item) => {
    if (!item.eixo) { return; }
    if (!(item.eixo.tema in eixos)) { eixos[item.eixo.tema] = { azul: 0, vermelho: 0 }; }
    if (item.eixo.sentido === 'azul' || item.eixo.sentido === 'vermelho') { eixos[item.eixo.tema][item.eixo.sentido] += 1; }
  });
  const indicadores = Object.create(null);
  edicao.indicadores.forEach((i) => { if (i.valor !== null && !i.defasado) { indicadores[i.id] = i.valor; } });
  return Object.assign({
    data: edicao.data,
    arquivo: 'edicoes/' + edicao.data + '.json',
    texto: 'edicoes/' + edicao.data + '.md',
    estado: edicao.estado,
    nivel: edicao.alerta.nivel,
    tendencia: edicao.alerta.tendencia,
    niveis,
    saldos,
    eixos,
    indicadores,
    resumo: edicao.resumo,
    gerada_em: edicao.gerada_em,
    exemplo: edicao.exemplo === true,
    corrigida_em: []
  }, extras || {});
}

/* Entrada solta do índice, para montar histórico sem escrever a edição. */
function entradaSolta(data, campos) {
  return Object.assign({
    data,
    arquivo: 'edicoes/' + data + '.json',
    texto: 'edicoes/' + data + '.md',
    estado: 'completa',
    nivel: 1,
    tendencia: 'estavel',
    niveis: { energia: 1, alimentos: 1, cambio: 1, suprimentos: 1, conflito: 1 },
    saldos: {},
    eixos: {},
    indicadores: {},
    resumo: 'Dia de teste.',
    gerada_em: data + 'T21:10:00Z',
    exemplo: false,
    corrigida_em: []
  }, campos || {});
}

function indiceDe(entradas) {
  const ordenadas = entradas.slice().sort((a, b) => (a.data < b.data ? 1 : -1));
  return { versao: 1, atualizado_em: ordenadas.length ? ordenadas[0].gerada_em : '2026-11-19T21:14:03Z', edicoes: ordenadas };
}

/* A tabela que o fetch falso serve.
   opcoes.edicoes: lista de edições; opcoes.entradas: entradas a mais no
   índice; opcoes.sem: caminhos que ficam de fora (respondem 404). */
function arquivos(opcoes) {
  const o = opcoes || {};
  const d = dados();
  const edicoes = o.edicoes || [edicaoDeExemplo()];
  const tabela = {
    'dados/regua.json': d.regua,
    'dados/players.json': d.players,
    'dados/veiculos.json': d.veiculos,
    'dados/vetores.json': d.vetores,
    'dados/indicadores.json': d.catalogo
  };
  edicoes.forEach((edicao) => { tabela['edicoes/' + edicao.data + '.json'] = edicao; });
  tabela['edicoes/indice.json'] = indiceDe(edicoes.map((e) => entradaDoIndice(e)).concat(o.entradas || []));
  (o.sem || []).forEach((caminho) => { delete tabela[caminho]; });
  return tabela;
}

/* ------------------------------------------------- índice de 35 dias */

/* O nível geral de cada dia do índice de teste. */
function nivelDoDia(data) {
  if (data <= '2026-10-31') { return data === '2026-10-28' ? 2 : 1; }
  if (data <= '2026-11-04') { return 2; }
  if (data === '2026-11-05') { return 5; }   /* a de exemplo */
  if (data <= '2026-11-07') { return 3; }
  if (data === '2026-11-09') { return 4; }
  if (data === '2026-11-10') { return 3; }
  return 2;
}

/* O que cada dia tem de diferente. Os dias fora desta tabela são edições
   completas, estáveis, sem placar e sem ato. */
const DIAS_DIFERENTES = {
  /* fora dos 30 dias: números grandes, para aparecer se entrarem na conta */
  '2026-10-16': { saldos: { ordem_global: 100 }, eixos: { clima: { azul: 9, vermelho: 9 } } },
  '2026-10-28': { estado: 'reduzida', tendencia: 'subindo' },
  '2026-11-01': { saldos: { ordem_global: 2, soberanistas: -1 }, tendencia: 'subindo' },
  '2026-11-02': { eixos: { clima: { azul: 1, vermelho: 0 } } },
  '2026-11-05': { exemplo: true, saldos: { ordem_global: 50 }, eixos: { imigracao: { azul: 7, vermelho: 7 } },
    resumo: '[EXEMPLO] Edição de exemplo no meio do índice.', tendencia: 'subindo' },
  '2026-11-06': { saldos: { eixo_revisionista: 3, centro_atlantico: -2 }, tendencia: 'subindo' },
  '2026-11-09': { eixos: { ia_depois: { azul: 0, vermelho: 2 }, clima: { azul: 0, vermelho: 1 } }, tendencia: 'subindo' },
  '2026-11-10': { corrigida_em: ['2026-11-11'], tendencia: 'descendo' },
  '2026-11-11': { tendencia: 'descendo' },
  '2026-11-12': { estado: 'falha', resumo: 'A coleta e a busca falharam: sem rede na hora da rotina.' },
  '2026-11-13': { saldos: { ordem_global: 1 } }
};

/* Entradas soltas de 16/10 a 17/11/2026 (33 dias, menos 08/11, que não tem
   edição). Com as edições de 18/11 e 19/11, o índice cobre 35 dias e tem:
   edição falha (12/11), edição de exemplo (05/11), edição corrigida (10/11),
   edição reduzida (28/10) e um dia sem edição (08/11). */
function entradasDe35Dias() {
  const entradas = [];
  const umDia = 86400000;
  const inicio = Date.UTC(2026, 9, 16);
  for (let i = 0; i < 33; i += 1) {
    const data = new Date(inicio + i * umDia).toISOString().slice(0, 10);
    if (data === '2026-11-08') { continue; }
    const nivel = nivelDoDia(data);
    const indicadores = { usd_brl: 5.4321 };
    /* o Brent sobe 0,2 por dia a partir de 21/10; em 03/11 não veio */
    if (data !== '2026-11-03' && data !== '2026-11-12') { indicadores.brent = Math.round((70 + (i - 5) * 0.2) * 10) / 10; }
    if (data === '2026-11-14') { indicadores.gas_natural = 3.21; }          /* um valor só no período */
    if (data === '2026-11-15' || data === '2026-11-16') { indicadores.cobre = 9000.5; }   /* fora do catálogo */
    entradas.push(entradaSolta(data, Object.assign({
      nivel,
      niveis: { energia: nivel, alimentos: 1, cambio: Math.min(nivel, 2), suprimentos: 1, conflito: nivel >= 3 ? nivel : 1 },
      indicadores,
      resumo: 'Resumo do dia ' + data.slice(8, 10) + '/' + data.slice(5, 7) + '.'
    }, DIAS_DIFERENTES[data] || {})));
  }
  return entradas;
}

/* A tabela do fetch com o índice de 35 dias. Só 18/11 e 19/11 têm arquivo
   de edição (a de exemplo, sem as marcas). mudancas(tabela) ajusta o resto. */
function arquivosDe35Dias(mudancas) {
  const tabela = arquivos({ edicoes: [edicaoReal('2026-11-18'), edicaoReal(DIA)], entradas: entradasDe35Dias() });
  if (mudancas) { mudancas(tabela); }
  return tabela;
}

/* Os dados de verdade de dados/, como estão hoje no repositório. Só para os
   testes que conferem coisas que valem para qualquer dado: os outros usam a
   cópia congelada, para não quebrar quando o dono revisar a régua e o mapa. */
function dadosDoRepositorio() {
  return {
    'dados/regua.json': leJson('dados', 'regua.json'),
    'dados/players.json': leJson('dados', 'players.json'),
    'dados/veiculos.json': leJson('dados', 'veiculos.json'),
    'dados/vetores.json': leJson('dados', 'vetores.json'),
    'dados/indicadores.json': leJson('dados', 'indicadores.json')
  };
}

/* Deixa as promessas pendentes se resolverem. */
async function assenta() {
  for (let i = 0; i < 8; i += 1) {
    await new Promise((resolve) => setImmediate(resolve));
  }
}

/* A lista de veículos é montada em fatias, com um temporizador de zero
   milissegundos entre elas. Isto roda as fatias que faltam. */
async function terminaFatias(mundo) {
  mundo.relogio.avanca(0);
  await assenta();
}

/* Abre o site: monta a janela falsa, roda o app.js e espera a primeira carga.
   opcoes: hash, agora, arquivos (tabela), esperar (false para não assentar),
   fatias (false para parar depois da primeira fatia de uma lista longa). */
async function abre(opcoes) {
  const o = opcoes || {};
  const mundo = criaJanela(HTML, {
    hash: o.hash || '',
    agora: o.agora === undefined ? AGORA : o.agora,
    arquivos: o.arquivos || arquivos()
  });
  if (o.segura) { mundo.rede.segura = true; }
  const antes = new Set(Object.getOwnPropertyNames(mundo.janela));
  const contexto = vm.createContext(mundo.janela);
  ROTEIRO.runInContext(contexto);
  mundo.novosGlobais = Object.getOwnPropertyNames(mundo.janela).filter((nome) => !antes.has(nome));
  mundo.assenta = assenta;
  mundo.um = (seletor) => mundo.documento.querySelector(seletor);
  mundo.todos = (seletor) => mundo.documento.querySelectorAll(seletor);
  /* troca o endereço como o leitor faria e espera a vista assentar */
  mundo.vai = async (hash, opcoesDaIda) => {
    mundo.janela.location.hash = hash;
    await assenta();
    if (!opcoesDaIda || opcoesDaIda.fatias !== false) { await terminaFatias(mundo); }
  };
  mundo.clica = async (el) => { el.click(); await assenta(); };
  mundo.tecla = (key) => mundo.documento.dispatchEvent(new Evento('keydown', { dados: { key } }));
  /* escreve num campo de busca, tecla a tecla ou de uma vez, como o leitor faria */
  mundo.escreve = async (campo, valor) => {
    campo.value = valor;
    campo.dispatchEvent(new Evento('input'));
    await assenta();
  };
  /* escolhe uma opção de uma lista nativa */
  mundo.escolhe = async (seletor, valor) => {
    seletor.value = valor;
    seletor.dispatchEvent(new Evento('change'));
    await assenta();
  };
  mundo.terminaFatias = () => terminaFatias(mundo);
  /* abre todas as dobras que estão fechadas na tela */
  mundo.abreTudo = async () => {
    mundo.todos('button[aria-expanded="false"]').forEach((botao) => botao.click());
    await assenta();
  };
  if (o.esperar !== false) {
    await assenta();
    if (o.fatias !== false) { await terminaFatias(mundo); }
  }
  return mundo;
}

/* Todas as classes que aparecem no documento agora. */
function classesNaTela(mundo) {
  const classes = new Set();
  mundo.documento.descendentes().forEach((el) => {
    (el.getAttribute('class') || '').split(/\s+/).filter(Boolean).forEach((classe) => classes.add(classe));
  });
  return classes;
}

/* Texto de um elemento, com os espaços em linha. */
function textoDe(el) {
  return el ? el.textContent.replace(/\s+/g, ' ').trim() : '';
}

/* O elemento está à vista? (nem ele nem um ancestral leva hidden) */
function aVista(el) {
  for (let n = el; n && n.nodeType === 1; n = n.parentNode) {
    if (n.hasAttribute('hidden')) { return false; }
  }
  return true;
}

module.exports = {
  RAIZ, ARQUIVO_HTML, ARQUIVO_APP, ARQUIVO_CSS, HTML, AGORA, DIA,
  abre, arquivos, arquivosDe35Dias, entradasDe35Dias, dadosDoRepositorio, assenta, dados, copia, acusacoes,
  edicaoDeExemplo, edicaoReal, edicaoFalha, entradaDoIndice, entradaSolta, indiceDe, textoDe, aVista, classesNaTela, Evento
};
