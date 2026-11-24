'use strict';

/* As classes do site, conferidas nos dois sentidos:
 *   - toda classe que o script e o index.html põem na tela tem regra no
 *     assets/estilo.css, ou é gancho declarado aqui, com o motivo;
 *   - toda classe do estilo.css é usada: aparece no texto do script ou do
 *     index.html, e aparece na tela em pelo menos um dos roteiros abaixo.
 * Ninguém vê a tela antes da entrega: regra sem uso e classe sem regra são
 * os dois jeitos de o desenho divergir do código sem ninguém notar. */

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {
  abre, arquivos, arquivosDe35Dias, edicaoReal, edicaoFalha, edicaoDeExemplo, entradaSolta, entradaDoIndice, indiceDe,
  classesNaTela, ARQUIVO_APP, ARQUIVO_HTML, ARQUIVO_CSS, DIA, Evento
} = require('./apoio.js');

const APP = fs.readFileSync(ARQUIVO_APP, 'utf8');
const HTML = fs.readFileSync(ARQUIVO_HTML, 'utf8');
const CSS = fs.readFileSync(ARQUIVO_CSS, 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');

/* Classes do CSS: tudo o que vem depois de um ponto num seletor. Número com
   ponto (0.75rem, 1.55) não é classe: classe começa com letra. */
const NO_CSS = new Set((CSS.match(/\.[a-z][a-z0-9_-]*/g) || []).map((c) => c.slice(1)));

/* Ganchos: classes que existem para o script e para os testes acharem um
   elemento, sem desenho próprio. Lista fechada: classe nova sem regra tem de
   entrar aqui, de caso pensado, ou ganhar regra. */
const GANCHOS = new Set([
  'aviso--grave',        /* a especificação não dá desenho próprio ao aviso grave */
  'carimbo__texto', 'carimbo__idade', 'carimbo__carga',   /* partes do carimbo que o script troca */
  'dominio__desde', 'fonte__veiculo', 'bastidores__modo',
  'eixo', 'gatilhos', 'placar', 'respostas', 'sinais', 'vetores',   /* caixas de lista do Painel */
  'atos', 'grupos'       /* a figura dos atos por tema e a caixa dos grupos de veículos */
]);
/* Variantes que o script monta a partir de um nome fixo no código (a vista,
   a seção, a figura). Só algumas têm regra: as outras são gancho. */
const VARIANTES_GANCHO = ['vista--', 'secao--', 'figura--'];

function ehGancho(classe) {
  return GANCHOS.has(classe) || VARIANTES_GANCHO.some((prefixo) => classe.startsWith(prefixo) && /^[a-z0-9-]+$/.test(classe.slice(prefixo.length)));
}

/* ----- os roteiros: cada um deixa na tela um pedaço do site ----- */

function comVetores(tabela) {
  tabela['dados/vetores.json'].vetores.push(
    { id: '2026-11-10_p1_ue', data: '2026-11-10', item: 'p1', player: 'ue', de: 'centro_atlantico', para: 'soberanistas', forca: 1, tema: 'clima',
      porque: 'Teste.', url: 'https://exemplo.invalid/a' },
    { id: '2026-11-19_r2_google', data: '2026-11-19', item: 'r2', player: 'google', de: 'bancada_talento', para: 'ordem_global', forca: 2, tema: 'ia_depois',
      porque: 'Teste.', url: 'https://exemplo.invalid/b', conflito_de_interesse: true },
    { id: '2026-11-19_anula_1', data: '2026-11-19', anula: '2026-11-10_p1_ue', porque: 'Não houve o ato.', url: 'https://exemplo.invalid/c' },
    { id: '2026-11-20_anula_1', data: '2026-11-20', anula: '2026-11-19_r2_google', porque: 'Desmentido.', url: 'https://exemplo.invalid/d' });
}

/* O índice de 35 dias com um dia de nível 5 de verdade (a fita tem a coluna mais alta). */
function tabelaCheia() {
  return arquivosDe35Dias((t) => {
    comVetores(t);
    const dia = t['edicoes/indice.json'].edicoes.find((e) => e.data === '2026-11-07');
    dia.nivel = 5;
    dia.niveis = { energia: 5, alimentos: 1, cambio: 2, suprimentos: 1, conflito: 5 };
  });
}

/* Roda todos os roteiros e devolve as classes que apareceram na tela. */
async function classesDeTodosOsRoteiros() {
  const vistas = new Set();
  const junta = (m) => classesNaTela(m).forEach((classe) => vistas.add(classe));

  /* 1. Painel com histórico: fechado, com dica aberta, com tudo aberto, com filtro sem resultado */
  let m = await abre({ arquivos: tabelaCheia() });
  junta(m);
  m.um('.fita a.fita__dia').dispatchEvent(new Evento('mouseenter', { bubbles: false }));
  junta(m);
  await m.abreTudo();
  junta(m);
  const dica = m.um('.tem-dica');
  dica.focus();
  m.tecla('Escape');
  junta(m);
  await m.vai('#/?cat=ia&dom=alimentos');
  junta(m);

  /* 2. a edição de exemplo, uma edição falha, uma atrasada e uma sem nível válido */
  m = await abre({ arquivos: arquivos({ edicoes: [edicaoDeExemplo()] }) });
  await m.abreTudo();
  junta(m);
  m = await abre({ arquivos: arquivos({ edicoes: [edicaoReal('2026-11-18'), edicaoFalha(DIA, edicaoReal('2026-11-18'))] }) });
  junta(m);
  m = await abre({ arquivos: arquivos({ edicoes: [edicaoReal(DIA)] }), agora: Date.UTC(2026, 10, 21, 12, 0, 0) });
  junta(m);
  m = await abre({ arquivos: arquivos({ edicoes: [edicaoReal(DIA, (e) => {
    e.alerta.nivel = 9;
    e.alerta.dominios[0].nivel = 'alto';
    e.alerta.dominios[1].nivel = 4;
    e.alerta.dominios[2].nivel = 5;
    e.principais[0].ataques[0].veiculo = 'veiculo_fantasma';
  })] }) });
  await m.abreTudo();
  junta(m);

  /* 3. o aviso de edição nova */
  m = await abre({ arquivos: arquivos({ edicoes: [edicaoReal(DIA)] }) });
  const nova = edicaoReal('2026-11-20');
  m.rede.arquivos['edicoes/2026-11-20.json'] = nova;
  m.rede.arquivos['edicoes/indice.json'] = indiceDe([entradaDoIndice(edicaoReal(DIA)), entradaDoIndice(nova)]);
  m.relogio.avanca(6 * 60000);
  m.documento.dispatchEvent(new Evento('visibilitychange'));
  await m.assenta();
  junta(m);

  /* 4. Arquivo, as 4 abas da Régua e o Método, com tudo aberto */
  for (const hash of ['#/arquivo', '#/arquivo?nivel=5', '#/regua/partidos', '#/regua/players', '#/regua/players?q=zzz', '#/regua/veiculos', '#/regua/vetores', '#/metodo']) {
    m = await abre({ hash, arquivos: tabelaCheia() });
    junta(m);
    await m.abreTudo();
    junta(m);
  }
  /* mês antigo em dobra, no Arquivo */
  m = await abre({ hash: '#/arquivo', arquivos: arquivosDe35Dias((t) => { t['edicoes/indice.json'].edicoes.push(entradaSolta('2026-09-30')); }) });
  junta(m);
  return vistas;
}

let prontas = null;
function todasAsClasses() {
  if (!prontas) { prontas = classesDeTodosOsRoteiros(); }
  return prontas;
}

/* As classes escritas no index.html. */
function classesDoHtml() {
  const classes = new Set();
  (HTML.match(/class="([^"]+)"/g) || []).forEach((m) => m.slice(7, -1).split(/\s+/).filter(Boolean).forEach((c) => classes.add(c)));
  return classes;
}

test('toda classe que aparece na tela tem regra no CSS, ou é gancho declarado', async () => {
  const vistas = await todasAsClasses();
  classesDoHtml().forEach((classe) => vistas.add(classe));
  assert.ok(vistas.size > 250, 'os roteiros cobrem o site: ' + vistas.size + ' classes');
  const semRegra = Array.from(vistas).filter((classe) => !NO_CSS.has(classe) && !ehGancho(classe)).sort();
  assert.deepEqual(semRegra, [], 'classe usada sem regra no CSS');
  /* toda classe é escrita em minúsculas, com hífen: nunca vem de dado */
  vistas.forEach((classe) => assert.match(classe, /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*(?:__[a-z0-9]+(?:-[a-z0-9]+)*)?(?:--[a-z0-9]+(?:-[a-z0-9]+)*)?$/, classe));
});

test('nenhum gancho declarado sobra: todos aparecem na tela e nenhum tem regra', async () => {
  const vistas = await todasAsClasses();
  GANCHOS.forEach((classe) => {
    assert.ok(vistas.has(classe), 'gancho que o site não usa mais: ' + classe);
    assert.equal(NO_CSS.has(classe), false, 'gancho que ganhou regra sai da lista: ' + classe);
  });
});

test('nenhuma regra sem uso: toda classe do CSS aparece na tela em algum roteiro', async () => {
  const vistas = await todasAsClasses();
  classesDoHtml().forEach((classe) => vistas.add(classe));
  const semUso = Array.from(NO_CSS).filter((classe) => !vistas.has(classe)).sort();
  assert.deepEqual(semUso, [], 'classe com regra no CSS que nenhum roteiro pôs na tela');
});

test('nenhuma regra sem uso: toda classe do CSS está escrita no script ou no index.html', () => {
  /* as palavras dentro de aspas simples do script: é onde as classes moram */
  const palavras = new Set();
  (APP.match(/'[^'\n]*'/g) || []).forEach((literal) => literal.slice(1, -1).split(/\s+/).filter(Boolean).forEach((p) => palavras.add(p)));
  classesDoHtml().forEach((classe) => palavras.add(classe));
  /* variantes montadas no script: 'nivel-' + n, 'fita__coluna--n' + nivel, 'dna__metade--' + letra */
  const prefixos = new Set((APP.match(/[a-z][a-z0-9_-]*'\s*\+/g) || []).map((m) => m.replace(/'\s*\+$/, '')));
  const semUso = Array.from(NO_CSS).filter((classe) => {
    if (palavras.has(classe)) { return false; }
    return !Array.from(prefixos).some((prefixo) => classe.startsWith(prefixo) && /^[a-z0-9]+$/.test(classe.slice(prefixo.length)));
  }).sort();
  assert.deepEqual(semUso, [], 'classe do CSS que nem o script nem o index.html escrevem');
});

test('o CSS não escolhe elemento por id de dado nem por atributo que o site não põe', () => {
  /* ids usados em seletor: só os fixos do index.html */
  const ids = new Set((CSS.match(/#[a-z][a-z0-9-]*(?=[\s,{.:\[>])/g) || []).map((id) => id.slice(1)));
  ids.forEach((id) => assert.ok(HTML.includes('id="' + id + '"'), 'seletor por id que não está no index.html: #' + id));
  /* atributos usados em seletor: todos são postos pelo script ou pelo HTML */
  const atributos = new Set((CSS.match(/\[([a-z-]+)(?=[\]=~^$*|])/g) || []).map((a) => a.slice(1)));
  atributos.forEach((atributo) => assert.ok(APP.includes("'" + atributo + "'") || HTML.includes(atributo + '=') || atributo === 'hidden' || atributo === 'title',
    'seletor por atributo que o site não usa: [' + atributo + ']'));
});
