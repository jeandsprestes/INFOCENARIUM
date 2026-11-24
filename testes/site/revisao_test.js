'use strict';

/* Conferências da revisão do site: o papel (o que some, o que fica e as
 * marcas que só existem como cor de fundo), o foco visível, e a
 * acessibilidade de cada vista montada (nomes, ligações aria, rótulos e a
 * ordem dos títulos). Dados: a cópia congelada. */

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { ARQUIVO_CSS, abre, arquivos, arquivosDe35Dias, edicaoReal, edicaoFalha, textoDe, acusacoes } = require('./apoio.js');

const CSS = fs.readFileSync(ARQUIVO_CSS, 'utf8');
const SEM_COMENTARIO = CSS.replace(/\/\*[\s\S]*?\*\//g, '');

/* O bloco @media print inteiro, sem comentários. */
function blocoDoPapel() {
  const inicio = SEM_COMENTARIO.indexOf('@media print {');
  assert.notEqual(inicio, -1, 'há bloco de impressão');
  let nivel = 0;
  for (let i = SEM_COMENTARIO.indexOf('{', inicio); i < SEM_COMENTARIO.length; i += 1) {
    if (SEM_COMENTARIO[i] === '{') { nivel += 1; }
    if (SEM_COMENTARIO[i] === '}') { nivel -= 1; if (nivel === 0) { return SEM_COMENTARIO.slice(inicio, i + 1); } }
  }
  throw new Error('bloco de impressão sem fim');
}

/* As regras de um bloco: [{ seletores, corpo }]. */
function regras(bloco) {
  const dentro = bloco.slice(bloco.indexOf('{') + 1, -1);
  const achadas = [];
  const forma = /([^{}]+)\{([^{}]*)\}/g;
  let m;
  while ((m = forma.exec(dentro)) !== null) {
    achadas.push({ seletores: m[1].split(',').map((s) => s.trim()).filter(Boolean), corpo: m[2] });
  }
  return achadas;
}

test('papel: as marcas que são só cor de fundo são impressas (print-color-adjust: exact)', () => {
  /* Por padrão o navegador não imprime fundo: o segmento aceso, a placa
     invertida, as barras, as colunas da fita e os pontos cheios sumiriam. */
  const exatas = new Set();
  regras(blocoDoPapel()).forEach((r) => {
    if (/(^|[;\s])print-color-adjust:\s*exact/.test(r.corpo) && /-webkit-print-color-adjust:\s*exact/.test(r.corpo)) {
      r.seletores.forEach((s) => exatas.add(s));
    }
  });
  ['.medidor__seg', '.placa--grave', '.placar__barra', '.placar__eixo', '.fita__coluna', '.fita__fio', '.forca__ponto']
    .forEach((seletor) => assert.ok(exatas.has(seletor), 'papel sem fundo em ' + seletor));
});

test('papel: somem navegação, filtros, botões, dicas e o aviso de edição nova; fica a linha do topo; cartões não quebram', () => {
  const papel = regras(blocoDoPapel());
  const somem = new Set();
  const inteiros = new Set();
  papel.forEach((r) => {
    if (/display:\s*none\s*!important/.test(r.corpo)) { r.seletores.forEach((s) => somem.add(s)); }
    if (/break-inside:\s*avoid/.test(r.corpo)) { r.seletores.forEach((s) => inteiros.add(s)); }
  });
  ['.nav', '.filtros', '.botao', '.dica', '.aviso--edicao-nova'].forEach((s) => assert.ok(somem.has(s), 'some no papel: ' + s));
  ['.alerta', '.principal', '.dominio', '.ficha'].forEach((s) => assert.ok(inteiros.has(s), 'não quebra no meio: ' + s));
  assert.ok(papel.some((r) => r.seletores.includes('.so-impressao') && /display:\s*block/.test(r.corpo)), 'a linha "INFOCENARIUM · edição de …" aparece');
  /* o aviso de exemplo é impresso: nenhum aviso some por inteiro */
  assert.equal(somem.has('.aviso'), false);
});

test('foco visível em tudo o que recebe foco: contorno de 2 px em --destaque, afastado 2 px; só o título escondido fica sem', () => {
  assert.match(SEM_COMENTARIO, /(^|\n):focus \{\s*outline: var\(--foco\);\s*outline-offset: 2px;\s*\}/);
  const semContorno = [];
  const forma = /([^{}]+)\{([^{}]*)\}/g;
  let m;
  while ((m = forma.exec(SEM_COMENTARIO)) !== null) {
    if (/outline(-style)?:\s*(none|0)\b/.test(m[2])) { semContorno.push(m[1].trim()); }
  }
  assert.deepEqual(semContorno, ['.so-leitor:focus']);
  assert.equal(/:focus-visible/.test(SEM_COMENTARIO), false, 'a regra vale para todo foco, também o posto por rota');
});

/* ----- acessibilidade da vista montada ----- */

function confereAcessibilidade(m, nome) {
  const els = m.documento.descendentes();
  const ids = new Map();
  els.forEach((el) => { const id = el.getAttribute('id'); if (id) { ids.set(id, (ids.get(id) || 0) + 1); } });
  ids.forEach((n, id) => assert.equal(n, 1, nome + ': id repetido ' + id));
  let nivelAnterior = 0;
  els.forEach((el) => {
    const tag = el.tagName.toLowerCase();
    ['aria-controls', 'aria-labelledby', 'for'].forEach((atributo) => {
      const alvo = el.getAttribute(atributo);
      if (alvo) { assert.ok(ids.has(alvo), nome + ': ' + atributo + ' sem alvo: ' + alvo); }
    });
    if ((tag === 'button' || tag === 'a') && el.getAttribute('aria-hidden') !== 'true') {
      assert.notEqual(textoDe(el), '', nome + ': ' + tag + ' sem nome (' + el.getAttribute('class') + ')');
    }
    if (tag === 'select') { assert.ok(el.getAttribute('aria-label'), nome + ': lista sem nome'); }
    if (tag === 'input') {
      const id = el.getAttribute('id');
      assert.ok(id && els.some((l) => l.tagName.toLowerCase() === 'label' && l.getAttribute('for') === id), nome + ': campo sem rótulo');
    }
    if (el.getAttribute('aria-expanded') !== null) {
      /* a dobra fechada usa hidden; a aberta, não */
      const corpo = m.documento.getElementById(el.getAttribute('aria-controls'));
      assert.ok(corpo, nome + ': dobra sem conteúdo');
      assert.equal(corpo.hasAttribute('hidden'), el.getAttribute('aria-expanded') === 'false', nome + ': aria-expanded e hidden discordam');
    }
    if (el.getAttribute('tabindex') === '0') {
      assert.ok(el.classList.contains('tem-dica'), nome + ': só a etiqueta com dica entra no Tab sem ser controle');
    }
    if (/^h[1-6]$/.test(tag)) {
      const n = Number(tag[1]);
      assert.ok(n <= nivelAnterior + 1, nome + ': título pula de h' + nivelAnterior + ' para h' + n + ' (' + textoDe(el).slice(0, 40) + ')');
      nivelAnterior = n;
    }
  });
  assert.equal(m.todos('#vista h1').length, 1, nome + ': um h1 por vista');
  const regiao = m.um('#anuncio');
  assert.equal(regiao.getAttribute('aria-live'), 'polite');
}

test('acessibilidade de cada vista, fechada e com tudo aberto: nomes, aria-controls, rótulos, ids únicos e títulos em ordem', async () => {
  const antes = acusacoes.length;
  const tabela = arquivosDe35Dias();
  const m = await abre({ hash: '#/', arquivos: tabela });
  for (const rota of ['#/', '#/edicao/2026-11-18', '#/arquivo', '#/regua/partidos', '#/regua/players', '#/regua/veiculos',
    '#/regua/vetores', '#/metodo']) {
    await m.vai(rota);
    confereAcessibilidade(m, rota);
    await m.abreTudo();
    confereAcessibilidade(m, rota + ' aberta');
  }
  /* a edição falha e a de exemplo têm outras seções */
  const falha = await abre({ hash: '#/', arquivos: arquivos({ edicoes: [edicaoReal('2026-11-19'), edicaoFalha('2026-11-20', edicaoReal('2026-11-19'))] }) });
  confereAcessibilidade(falha, 'falha');
  const exemplo = await abre({ hash: '#/', arquivos: arquivos() });
  await exemplo.abreTudo();
  confereAcessibilidade(exemplo, 'exemplo aberta');
  assert.equal(acusacoes.length, antes);
});

test('teclado: Esc fecha a dica, depois a dobra, e devolve o foco ao botão, em cada vista', async () => {
  const m = await abre({ hash: '#/', arquivos: arquivosDe35Dias() });
  for (const rota of ['#/', '#/regua/veiculos', '#/regua/players', '#/arquivo']) {
    await m.vai(rota);
    const botao = m.todos('button[aria-expanded="false"]')[0];
    assert.ok(botao, rota + ': há dobra');
    await m.clica(botao);
    assert.equal(botao.getAttribute('aria-expanded'), 'true');
    const corpo = m.documento.getElementById(botao.getAttribute('aria-controls'));
    const dentro = corpo.querySelectorAll('a, button, [tabindex]')[0] || corpo;
    dentro.focus();
    m.tecla('Escape');
    await m.assenta();
    assert.equal(botao.getAttribute('aria-expanded'), 'false', rota + ': Esc fecha');
    assert.equal(m.documento.activeElement, botao, rota + ': o foco volta ao botão');
  }
});
