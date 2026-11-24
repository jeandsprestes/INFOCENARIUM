'use strict';

/* Teste estático: lê o texto de assets/app.js, index.html e assets/estilo.css
 * e acusa o que o site está proibido de trazer. Não roda nada. */

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { ARQUIVO_APP, ARQUIVO_HTML, ARQUIVO_CSS } = require('./apoio.js');
const { leHtml } = require('./dom_falso.js');

const APP = fs.readFileSync(ARQUIVO_APP, 'utf8');
const HTML = fs.readFileSync(ARQUIVO_HTML, 'utf8');
const CSS = fs.readFileSync(ARQUIVO_CSS, 'utf8');
const TODOS = { 'assets/app.js': APP, 'index.html': HTML, 'assets/estilo.css': CSS };

const PROIBIDOS = [
  ['innerHTML', /innerHTML/],
  ['outerHTML', /outerHTML/],
  ['insertAdjacentHTML', /insertAdjacentHTML/],
  ['document.write', /document\s*\.\s*write/],
  ['eval', /\beval\s*\(/],
  ['new Function', /new\s+Function\b/],
  ['@import', /@import/],
  ['endereço javascript:', /javascript\s*:/i],
  ['cookie', /\.cookie\b/],
  ['armazenamento no aparelho', /localStorage|sessionStorage|indexedDB/]
];

test('nenhum dos três arquivos traz o que a casa proíbe', () => {
  Object.keys(TODOS).forEach((nome) => {
    PROIBIDOS.forEach(([rotulo, forma]) => {
      assert.equal(forma.test(TODOS[nome]), false, nome + ' contém ' + rotulo);
    });
  });
});

test('nenhum endereço de fora, salvo o namespace do SVG', () => {
  const permitidos = ['http://www.w3.org/2000/svg'];
  Object.keys(TODOS).forEach((nome) => {
    const achados = TODOS[nome].match(/(?:https?:)?\/\/[a-z0-9][a-z0-9.-]*\.[a-z]{2,}[^\s"'`)<]*/gi) || [];
    const deFora = achados.filter((endereco) => !permitidos.includes(endereco));
    assert.deepEqual(deFora, [], nome + ' cita endereço de fora');
  });
  assert.equal((APP.match(/http:\/\/www\.w3\.org\/2000\/svg/g) || []).length, 1, 'o namespace do SVG aparece uma vez, numa constante');
  assert.equal(/https?:/.test(HTML), false, 'index.html não cita endereço com esquema');
  assert.equal(/url\s*\(/i.test(CSS), false, 'o CSS não carrega nada por url()');
  assert.equal(/@font-face/i.test(CSS), false, 'o CSS não declara fonte');
});

test('index.html: sem atributo style, sem script escrito na página, sem atributo de evento', () => {
  assert.equal(/\sstyle\s*=/i.test(HTML), false, 'atributo style');
  assert.equal(/<style[\s>]/i.test(HTML), false, 'bloco <style>');
  assert.equal(/\son[a-z]+\s*=/i.test(HTML), false, 'atributo de evento');
  const scripts = HTML.match(/<script\b[^>]*>[\s\S]*?<\/script>/gi) || [];
  assert.equal(scripts.length, 1, 'um script só');
  assert.match(scripts[0], /^<script src="assets\/app\.js" defer><\/script>$/);
});

test('index.html: o esqueleto da especificação do site', () => {
  const doc = leHtml(HTML);
  assert.equal(doc.documentElement.getAttribute('lang'), 'pt-BR');
  const cabeca = doc.head.children.map((el) => {
    const a = (n) => el.getAttribute(n);
    if (el.localName === 'meta') { return 'meta:' + (a('charset') ? 'charset' : (a('name') || a('http-equiv'))); }
    if (el.localName === 'link') { return 'link:' + a('rel'); }
    return el.localName;
  });
  assert.deepEqual(cabeca, [
    'meta:charset', 'meta:viewport', 'meta:color-scheme', 'meta:referrer', 'meta:Content-Security-Policy',
    'title', 'meta:description', 'link:alternate', 'link:icon', 'link:stylesheet', 'script'
  ]);
  assert.equal(doc.querySelector('meta[charset]').getAttribute('charset'), 'utf-8');
  assert.equal(doc.querySelector('meta[name="viewport"]').getAttribute('content'), 'width=device-width, initial-scale=1');
  assert.equal(doc.querySelector('meta[name="color-scheme"]').getAttribute('content'), 'dark');
  assert.equal(doc.querySelector('meta[name="referrer"]').getAttribute('content'), 'no-referrer');
  assert.equal(doc.querySelector('meta[http-equiv]').getAttribute('content'),
    "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'none'");
  assert.equal(doc.querySelector('title').textContent, 'INFOCENARIUM · monitor geopolítico e de IA');
  assert.equal(doc.querySelector('meta[name="description"]').getAttribute('content'),
    'Monitor diário de geopolítica e de IA: o que aconteceu, quem atirou, quem ganha e o que muda para quem se prepara.');
  assert.equal(doc.querySelector('link[rel="alternate"]').getAttribute('href'), 'feed.xml');
  assert.equal(doc.querySelector('link[rel="alternate"]').getAttribute('type'), 'application/atom+xml');
  assert.equal(doc.querySelector('link[rel="icon"]').getAttribute('href'), 'data:,');
  assert.equal(doc.querySelector('link[rel="stylesheet"]').getAttribute('href'), 'assets/estilo.css');

  /* corpo: pular, símbolos, header com nav, região aria-live, main, footer, noscript */
  const corpo = doc.body.children.map((el) => el.localName);
  assert.deepEqual(corpo, ['a', 'svg', 'header', 'div', 'main', 'footer', 'noscript']);
  assert.equal(doc.body.children[0].textContent, 'Pular para o conteúdo');
  assert.equal(doc.querySelector('#anuncio').getAttribute('aria-live'), 'polite');
  assert.deepEqual(doc.querySelectorAll('nav a').map((a) => [a.textContent, a.getAttribute('href')]),
    [['Painel', '#/'], ['Arquivo', '#/arquivo'], ['Régua', '#/regua'], ['Método', '#/metodo']]);
  assert.equal(doc.querySelectorAll('h1').length, 1, 'um h1 por vista');
  /* o aviso sem script vem duas vezes: no começo do main, antes de "Carregando
     edição…" e dos travessões, e depois do rodapé */
  const avisos = doc.querySelectorAll('noscript');
  assert.equal(avisos.length, 2);
  assert.equal(doc.querySelector('main').children[0].localName, 'noscript', 'o primeiro filho do main');
  assert.equal(doc.body.children[doc.body.children.length - 1].localName, 'noscript');
  avisos.forEach((aviso) => {
    assert.match(aviso.textContent, /O INFOCENARIUM precisa de JavaScript para montar o painel\. Sem ele, acompanhe as edições pelo feed\./);
    assert.deepEqual(aviso.querySelectorAll('a').map((a) => a.getAttribute('href')), ['feed.xml']);
  });
  assert.equal(avisos[0].textContent.trim(), avisos[1].textContent.trim(), 'as duas cópias dizem o mesmo');
  assert.match(doc.querySelector('footer').textContent.replace(/\s+/g, ' '),
    /Análises escritas por IA: o Claude, da Anthropic, que é um dos players da régua\. Leia o aviso em Método\. Sem cookies, sem rastreador, nada de terceiros\./);
});

test('index.html: a moldura do Painel traz os títulos das seções 01 a 09 e travessões', () => {
  const doc = leHtml(HTML);
  const titulos = doc.querySelectorAll('main h2').map((h) => h.textContent.replace(/\s+/g, ' ').trim());
  assert.deepEqual(titulos, ['01 HOJE', '02 DOMÍNIOS', '03 INDICADORES', '04 PRINCIPAIS', '05 PLACAR DO DIA',
    '06 O QUE VIGIAR', '07 MOVIMENTOS', '08 RADAR', '09 BASTIDORES']);
  doc.querySelectorAll('main .secao__corpo').forEach((corpo) => assert.equal(corpo.textContent.trim(), '—'));
  assert.equal(doc.querySelector('#carimbo').textContent, 'Carregando edição…');
  assert.equal(doc.querySelector('#vista').getAttribute('aria-busy'), 'true');
});

test('index.html: todos os ícones da especificação estão no bloco de símbolos, com o desenho dela', () => {
  const doc = leHtml(HTML);
  const esperados = {
    'i-nivel-1': '<circle cx="8" cy="8" r="5.5" fill="none" stroke="currentColor" stroke-width="2"/>',
    'i-nivel-2': '<path d="M8 2.6 14 13H2Z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>',
    'i-nivel-3': '<path d="M8 1 15 8 8 15 1 8Z" fill="currentColor"/>',
    'i-nivel-4': '<path d="M5.1 1h5.8L15 5.1v5.8L10.9 15H5.1L1 10.9V5.1Z" fill="currentColor"/>',
    'i-nivel-5': '<path d="M5.3 1.5h5.4l3.8 3.8v5.4l-3.8 3.8H5.3l-3.8-3.8V5.3Z" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M6.4 4.5h3.2l1.9 1.9v3.2l-1.9 1.9H6.4L4.5 9.6V6.4Z" fill="currentColor"/>',
    'i-sobe': '<path d="M4 12 12 4M6 4h6v6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    'i-estavel': '<path d="M2 8h12M9 3l5 5-5 5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    'i-desce': '<path d="M4 4l8 8M6 12h6V6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    'i-aviso': '<path d="M2.5 2.5h11v11h-11Z" fill="none" stroke="currentColor" stroke-width="2"/><path d="M8 5v4M8 11.2v.1" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    'i-relogio': '<circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" stroke-width="2"/><path d="M8 4.5V8l2.5 1.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    'i-externo': '<path d="M6 3H3v10h10v-3M9 3h4v4M13 3 7 9" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>',
    'i-dobra': '<path d="M6 3l5 5-5 5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
  };
  const simbolos = doc.querySelectorAll('symbol');
  assert.deepEqual(simbolos.map((s) => s.getAttribute('id')).sort(), Object.keys(esperados).sort());
  simbolos.forEach((simbolo) => {
    assert.equal(simbolo.getAttribute('viewBox'), '0 0 16 16');
    const id = simbolo.getAttribute('id');
    assert.ok(HTML.includes('<symbol id="' + id + '" viewBox="0 0 16 16">' + esperados[id] + '</symbol>'), 'desenho de ' + id);
  });
  /* todo ícone que o script usa existe no bloco */
  const usados = new Set((APP.match(/'i-[a-z0-9-]+'/g) || []).map((s) => s.slice(1, -1)));
  usados.delete('i-nivel-');
  usados.forEach((nome) => assert.ok(nome in esperados, 'ícone usado e não desenhado: ' + nome));
});

test('app.js: modo estrito, um arquivo só, dentro de uma função', () => {
  assert.match(APP, /^\/\*[\s\S]*?\*\/\s*\(function \(janela\) \{\s*'use strict';/);
  assert.match(APP, /\}\(window\)\);\s*$/);
  assert.equal(/\b(import|export)\s/.test(APP.replace(/\/\*[\s\S]*?\*\//g, '')), false, 'script clássico, não módulo');
  assert.equal(/\brequire\s*\(/.test(APP), false);
  assert.equal(/setAttribute\(\s*['"]style['"]/.test(APP), false, 'tamanho se põe por elemento.style');
  assert.equal(/\.style\.cssText/.test(APP), false);
});

test('app.js: o documento só é montado por createElement, createTextNode, textContent e setAttribute', () => {
  const semComentario = APP.replace(/\/\*[\s\S]*?\*\//g, '');
  /* outros caminhos de pôr conteúdo no documento ficam de fora, mesmo os que não leem HTML */
  const outros = /\.(append|prepend|before|after|replaceWith|replaceChildren|insertAdjacentElement|insertAdjacentText|cloneNode|importNode|setHTML|setHTMLUnsafe|setAttributeNS|createContextualFragment|parseFromString|createRange|execCommand)\s*\(|DOMParser|srcdoc|\.cssText|\.text\s*=|\.src\s*=/;
  const achado = semComentario.match(outros);
  assert.equal(achado, null, 'forma de montagem fora da lista: ' + (achado ? achado[0] : ''));
  /* createElementNS num lugar só, com o namespace do SVG numa constante; e a
     marca é sempre nome fixo no código: ícones (svg, use) e mini-linhas
     (svg, polyline, circle). Nenhum nome de marca vem de dado. */
  assert.equal((semComentario.match(/createElementNS\(/g) || []).length, 1);
  assert.match(semComentario, /function desenho\(marca, mapa\) \{\s*var el = doc\.createElementNS\(ESPACO_SVG, marca\);/);
  const marcas = (semComentario.match(/[^a-zA-Z]desenho\(([^,)]+)/g) || []).map((m) => m.replace(/^.*desenho\(/, ''));
  assert.deepEqual(Array.from(new Set(marcas)).sort(), ["'circle'", "'polyline'", "'svg'", "'use'", 'marca']);
  /* createElement também só recebe nome fixo, ou o nome que cria() repassa */
  const criados = (semComentario.match(/createElement\(([^)]*)\)/g) || []);
  assert.deepEqual(criados, ['createElement(tag)']);
  const tags = new Set((semComentario.match(/[^a-zA-Z]cria\(([^,)]+)/g) || []).map((m) => m.replace(/^.*cria\(/, '')));
  tags.forEach((tag) => assert.match(tag, /^('[a-z0-9]+'|tag|tag \|\| 'h3'|i === 0 \? 'th' : 'td')$/, 'cria() com marca que não é fixa: ' + tag));
  /* o único estilo posto por script é a largura de uma barra */
  assert.deepEqual(semComentario.match(/\.style\.[a-zA-Z]+/g), ['.style.width']);
  /* nada de temporizador com texto, nem de janela nova */
  assert.equal(/set(Timeout|Interval)\(\s*['"`]/.test(semComentario), false);
  assert.equal(/\.open\(|postMessage|importScripts|Worker\(|navigator\.sendBeacon|XMLHttpRequest|WebSocket|EventSource/.test(semComentario), false);
});

test('app.js: todo fetch pede cache "no-cache"', () => {
  const chamadas = APP.match(/\.fetch\([^)]*\)/g) || [];
  assert.ok(chamadas.length >= 2);
  chamadas.forEach((chamada) => assert.match(chamada, /cache: 'no-cache'/));
});

/* As cores foram validadas por script na fase de projeto: nenhuma pode mudar,
   e nenhuma cor nova pode entrar sem validação. */
const VARIAVEIS = {
  '--plano': '#0b0e11', '--painel': '#12161b', '--relevo': '#1a2027', '--fio': '#222a32', '--fio-forte': '#313a44',
  '--borda-controle': '#6f7b88', '--texto': '#e6ebf0', '--texto-2': '#b3bcc6', '--texto-3': '#8d98a4',
  '--tinta-escura': '#0b0e11', '--tinta-clara': '#ffffff', '--destaque': '#6cc5d6',
  '--tinta-dado': '#8d98a4', '--tinta-dado-forte': '#e6ebf0',
  '--alerta-1': '#04896e', '--alerta-1-trilho': '#0e3632', '--alerta-2': '#a39700', '--alerta-2-trilho': '#3b3a13',
  '--alerta-3': '#9f5910', '--alerta-3-trilho': '#392918', '--alerta-4': '#e13d62', '--alerta-4-trilho': '#4c212f',
  '--alerta-5': '#b15bdd', '--alerta-5-trilho': '#3f2951',
  '--dna-b': '#256abf', '--dna-b-letra': '#ffffff', '--dna-y': '#c98500', '--dna-y-letra': '#0b0e11',
  '--dna-r': '#d1273f', '--dna-r-letra': '#ffffff', '--dna-w': 'transparent', '--dna-k': '#000000',
  '--dna-wk-borda': '#6f7b88', '--dna-wk-letra': '#b3bcc6',
  '--partido-fundo': 'transparent', '--partido-borda': '#6f7b88', '--partido-letra': '#e6ebf0',
  '--placar-ganha': '#8d98a4', '--placar-perde': '#8d98a4', '--placar-eixo': '#313a44',
  '--t-rotulo': '0.75rem', '--t-meta': '0.8125rem', '--t-pequeno': '0.875rem', '--t-corpo': '1rem',
  '--t-leitura': '1.0625rem', '--t-item': '1.125rem', '--t-titulo': '1.375rem', '--t-valor': '1.25rem', '--t-heroi': '4rem',
  '--e1': '4px', '--e2': '8px', '--e3': '12px', '--e4': '16px', '--e5': '24px', '--e6': '32px', '--e7': '48px', '--e8': '72px',
  '--raio-1': '2px', '--raio-2': '4px'
};
const CORES_DO_PAPEL = ['#ffffff', '#bbbbbb', '#767676', '#111111', '#444444'];

/* Onde começa um bloco numerado do CSS (o título dentro da faixa de "="),
   e não a linha do sumário, no alto do arquivo. */
function inicioDoBloco(titulo) {
  const i = CSS.indexOf('=\n   ' + titulo);
  assert.notEqual(i, -1, 'bloco do CSS não achado: ' + titulo);
  return i;
}

/* Só a primeira declaração de cada variável: a da tela, em :root. */
function variaveisDaTela() {
  const tabela = {};
  const tela = CSS.slice(0, inicioDoBloco('2. Base e tipografia'));
  const forma = /(--[a-z0-9-]+)\s*:\s*([^;]+);/g;
  let m;
  while ((m = forma.exec(tela)) !== null) {
    if (!(m[1] in tabela)) { tabela[m[1]] = m[2].trim(); }
  }
  return tabela;
}

test('estilo.css: as variáveis têm os valores da especificação, sem trocar nenhum', () => {
  const tela = variaveisDaTela();
  Object.keys(VARIAVEIS).forEach((nome) => assert.equal(tela[nome], VARIAVEIS[nome], nome));
  assert.match(tela['--fonte-texto'], /^system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans", "Liberation Sans", Arial, sans-serif$/);
  assert.match(tela['--fonte-mono'], /^ui-monospace, "SF Mono", "Cascadia Mono", "Roboto Mono", "DejaVu Sans Mono", "Liberation Mono", Menlo, Consolas, monospace$/);
  assert.equal(tela['--foco'], '2px solid var(--destaque)');
  assert.equal(tela['--borda'], '1px solid var(--fio-forte)');
});

test('estilo.css: nenhuma cor fora da paleta validada', () => {
  const permitidas = new Set(Object.values(VARIAVEIS).filter((v) => v.charAt(0) === '#').concat(CORES_DO_PAPEL));
  const usadas = new Set((CSS.match(/#[0-9a-fA-F]{3,8}\b/g) || []).map((c) => c.toLowerCase()));
  usadas.forEach((cor) => assert.ok(permitidas.has(cor), 'cor fora da paleta: ' + cor));
  assert.equal(/\b(rgba?|hsla?|oklch|oklab|color-mix)\s*\(/i.test(CSS), false, 'cor só por variável');
  /* fora do bloco de variáveis e da impressão, cor é sempre var(--…) */
  const corpo = CSS.slice(inicioDoBloco('2. Base e tipografia'), CSS.indexOf('@media (prefers-contrast: more)'));
  assert.deepEqual(corpo.match(/#[0-9a-fA-F]{3,8}\b/g) || [], [], 'hex solto fora das variáveis');
});

test('estilo.css: mais contraste, cores forçadas e movimento reduzido como na especificação', () => {
  const contraste = CSS.slice(CSS.indexOf('@media (prefers-contrast: more)'), CSS.indexOf('@media (forced-colors: active)'));
  assert.match(contraste, /--texto-3:\s*#b3bcc6;/);
  assert.match(contraste, /--fio:\s*#313a44;/);
  assert.match(contraste, /--fio-forte:\s*#6f7b88;/);
  const forcadas = CSS.slice(CSS.indexOf('@media (forced-colors: active)'), inicioDoBloco('23. Impressão'));
  assert.match(forcadas, /\.medidor__seg--aceso\s*\{\s*background:\s*CanvasText;/);
  assert.match(forcadas, /\.medidor__seg\s*\{\s*background:\s*Canvas;\s*border:\s*1px solid CanvasText;/);
  /* célula de DNA só com borda e letra */
  assert.match(forcadas, /\.dna__metade,\s*\.dna--tinta \.dna__metade\s*\{\s*background:\s*Canvas;\s*border-color:\s*CanvasText;\s*color:\s*CanvasText;/);
  /* toda marca cheia das figuras é redesenhada: barras, colunas, pontos e mini-linhas */
  assert.match(forcadas, /\.fita__coluna,\s*\.placar__barra,\s*\.forca__ponto--cheio\s*\{\s*background:\s*CanvasText;/);
  assert.match(forcadas, /\.mini__traco\s*\{\s*stroke:\s*CanvasText;/);
  assert.match(forcadas, /\.mini__solto,\s*\.mini__ponto\s*\{\s*fill:\s*CanvasText;/);
  /* neste modo a borda transparente ganha cor: o link ativo tem de continuar diferente dos outros */
  assert.match(forcadas, /\.nav__link,\s*\.abas__link\s*\{\s*border-color:\s*Canvas;/);
  assert.match(forcadas, /\.nav__link\[aria-current="page"\],\s*\.abas__link\[aria-current="page"\]\s*\{\s*border-color:\s*Highlight;/);
  /* nenhuma cor da paleta entra neste bloco: só cores do sistema */
  assert.equal(/var\(--|#[0-9a-f]{3,8}/i.test(forcadas.replace(/\/\*[\s\S]*?\*\//g, '')), false);
  const movimento = CSS.slice(CSS.indexOf('@media (prefers-reduced-motion: reduce)'), CSS.indexOf('@media (prefers-contrast: more)'));
  assert.match(movimento, /animation:\s*none\s*!important/);
  assert.match(movimento, /transition:\s*none\s*!important/);
  assert.match(movimento, /scroll-behavior:\s*auto\s*!important/);
});

test('estilo.css: o que a especificação manda não fazer não está no arquivo', () => {
  assert.equal(/box-shadow|text-shadow/i.test(CSS), false, 'sem sombra');
  assert.equal(/gradient/i.test(CSS), false, 'sem degradê');
  assert.equal(/dashed|dotted/i.test(CSS), false, 'sem tracejado');
  assert.equal(/\bblink\b|marquee/i.test(CSS), false, 'nada pisca');
  assert.equal(/scroll-behavior:\s*smooth/i.test(CSS), false, 'sem rolagem suave');
  /* opacidade só no abrir de dobra: texto parado nunca fica abaixo de 1 */
  const semQuadros = CSS.replace(/@keyframes abre-dobra \{[\s\S]*?\n\}/, '');
  assert.equal(/opacity/i.test(semQuadros), false, 'opacidade fora do abrir de dobra');
  assert.match(CSS, /animation:\s*abre-dobra 120ms/);
  /* no celular, um só elemento preso à tela: a navegação */
  assert.equal((CSS.match(/position:\s*fixed/g) || []).length, 1);
  const antesDoMedio = CSS.slice(0, CSS.indexOf('@media (min-width: 720px)'));
  assert.equal(/position:\s*sticky/.test(antesDoMedio), false, 'no compacto a barra de topo rola com a página');
});

test('estilo.css: o foco do Tab não fica sob a barra presa (WCAG 2.2, 2.4.11; técnica C43)', () => {
  const compacto = CSS.slice(CSS.indexOf('@media (max-width: 719.98px)'), CSS.indexOf('@media (min-width: 720px) and'));
  assert.match(compacto, /html \{ scroll-padding-bottom: calc\(var\(--altura-nav\) \+ env\(safe-area-inset-bottom, 0px\) \+ var\(--e2\)\); \}/,
    'no compacto, a navegação presa na base');
  const medio = CSS.slice(CSS.indexOf('@media (min-width: 720px) {'), CSS.indexOf('@media (min-width: 1100px)'));
  assert.match(medio, /html \{ scroll-padding-top: calc\(var\(--altura-topo\) \+ var\(--e2\)\); \}/,
    'do médio para cima, a barra de topo presa');
  /* o scroll-margin soma com o scroll-padding: os alvos de rota param onde paravam (64 + 8 = 72 px; 64 + 64 = 128 px) */
  assert.match(medio, /\.tabela tbody th \{ scroll-margin-top: var\(--e2\); \}/);
  assert.match(medio, /\.matriz__nome \{ scroll-margin-top: calc\(var\(--e8\) - var\(--e2\)\); \}/);
  assert.match(medio, /\.matriz \.botao--dobra \{ scroll-margin-top: var\(--e7\); \}/);
  assert.equal(/scroll-margin-top: calc\(var\(--altura-topo\)/.test(CSS), false, 'a altura da barra não conta duas vezes');
  const antesDoCompacto = CSS.slice(0, CSS.indexOf('@media (max-width: 719.98px)'));
  assert.equal(/scroll-padding/.test(antesDoCompacto), false, 'fora das telas, nenhum respiro (a impressão não tem barra)');
});

test('estilo.css: os três tamanhos de tela e a impressão', () => {
  assert.match(CSS, /@media \(max-width: 719\.98px\)/);
  assert.match(CSS, /@media \(min-width: 720px\)/);
  assert.match(CSS, /@media \(min-width: 1100px\)/);
  assert.match(CSS, /--largura-max:\s*1240px/);
  assert.match(CSS, /@page \{ margin: 15mm; \}/);
  const papel = CSS.slice(CSS.indexOf('@media print'));
  assert.match(papel, /font-size:\s*11pt/);
  assert.match(papel, /\.dobra__corpo\[hidden\] \{ display: block !important; \}/);
  assert.match(papel, /a\.externo::after \{\s*content: " \(" attr\(href\) "\)";/);
  assert.match(papel, /break-inside:\s*avoid/);
  ['--plano: #ffffff', '--texto: #111111', '--texto-2: #444444', '--fio-forte: #767676', '--alerta-3: #111111',
    '--tinta-escura: #ffffff'].forEach((par) => assert.ok(papel.includes(par), 'papel: ' + par));
});

test('estilo.css: chaves e parênteses fecham', () => {
  const semComentario = CSS.replace(/\/\*[\s\S]*?\*\//g, '');
  assert.equal((semComentario.match(/\{/g) || []).length, (semComentario.match(/\}/g) || []).length);
  assert.equal((semComentario.match(/\(/g) || []).length, (semComentario.match(/\)/g) || []).length);
  assert.equal(/;;|\{\s*;|:\s*;/.test(semComentario), false, 'declaração vazia');
});
