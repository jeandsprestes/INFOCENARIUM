'use strict';

/* DOM falso para os testes do site.
 *
 * Traz só o que o assets/app.js usa: document, elementos, atributos,
 * classList, eventos, location e hash, history, fetch falso que serve
 * arquivos de uma tabela, e relógio controlado. O Intl e a URL são os de
 * verdade do Node.
 *
 * Ele ACUSA, lançando erro, o que o site está proibido de fazer:
 *   - innerHTML, outerHTML, insertAdjacentHTML e document.write;
 *   - atributo style e atributo de evento (onclick, onerror…): a política de
 *     conteúdo do index.html bloqueia os dois;
 *   - cookie e armazenamento no aparelho;
 *   - Date com data sem hora ("2026-11-19"): o dia mudaria com o fuso.
 */

const ESPACO_HTML = 'http://www.w3.org/1999/xhtml';
const ESPACO_SVG = 'http://www.w3.org/2000/svg';
const SEM_FECHO = new Set(['meta', 'link', 'br', 'hr', 'img', 'input', 'source', 'wbr']);

/* Toda acusação fica guardada. Se o código do site engolir o erro num
   try/catch, o apoio dos testes ainda faz o arquivo de teste falhar no fim. */
const acusacoes = [];

function proibido(nome) {
  acusacoes.push(nome);
  throw new Error('uso proibido no site: ' + nome);
}

/* ------------------------------------------------------------------ nós */

class No {
  constructor(documento) {
    this.ownerDocument = documento;
    this.parentNode = null;
    this.childNodes = [];
  }

  get firstChild() { return this.childNodes[0] || null; }
  get lastChild() { return this.childNodes[this.childNodes.length - 1] || null; }

  get nextSibling() {
    if (!this.parentNode) { return null; }
    const irmaos = this.parentNode.childNodes;
    return irmaos[irmaos.indexOf(this) + 1] || null;
  }

  appendChild(filho) {
    if (!(filho instanceof No)) { throw new TypeError('appendChild pede um nó'); }
    if (filho.contains(this)) { throw new Error('um nó não pode ser filho de si mesmo'); }
    if (filho.parentNode) { filho.parentNode.removeChild(filho); }
    filho.parentNode = this;
    this.childNodes.push(filho);
    return filho;
  }

  insertBefore(novo, referencia) {
    if (!referencia) { return this.appendChild(novo); }
    const i = this.childNodes.indexOf(referencia);
    if (i === -1) { throw new Error('insertBefore: a referência não é filha'); }
    if (novo.parentNode) { novo.parentNode.removeChild(novo); }
    novo.parentNode = this;
    this.childNodes.splice(this.childNodes.indexOf(referencia), 0, novo);
    return novo;
  }

  removeChild(filho) {
    const i = this.childNodes.indexOf(filho);
    if (i === -1) { throw new Error('removeChild: o nó não é filho'); }
    this.childNodes.splice(i, 1);
    filho.parentNode = null;
    return filho;
  }

  remove() {
    if (this.parentNode) { this.parentNode.removeChild(this); }
  }

  contains(no) {
    for (let n = no; n; n = n.parentNode) {
      if (n === this) { return true; }
    }
    return false;
  }

  get textContent() {
    return this.childNodes.map((filho) => filho.textContent).join('');
  }

  set textContent(valor) {
    while (this.childNodes.length) { this.removeChild(this.childNodes[0]); }
    const texto = valor === null || valor === undefined ? '' : String(valor);
    if (texto !== '') { this.appendChild(new NoDeTexto(this.ownerDocument, texto)); }
  }
}

class NoDeTexto extends No {
  constructor(documento, texto) {
    super(documento);
    this.nodeType = 3;
    this.dados = String(texto);
  }

  get textContent() { return this.dados; }
  set textContent(valor) { this.dados = String(valor); }
  appendChild() { throw new Error('nó de texto não tem filhos'); }
}

class ListaDeClasses {
  constructor(elemento) { this.elemento = elemento; }

  lista() {
    const classe = this.elemento.getAttribute('class');
    return classe ? classe.split(/\s+/).filter(Boolean) : [];
  }

  grava(nomes) { this.elemento.setAttribute('class', nomes.join(' ')); }
  contains(nome) { return this.lista().includes(nome); }

  add(...nomes) {
    const atual = this.lista();
    nomes.forEach((nome) => { if (!atual.includes(nome)) { atual.push(nome); } });
    this.grava(atual);
  }

  remove(...nomes) { this.grava(this.lista().filter((nome) => !nomes.includes(nome))); }

  toggle(nome, forcar) {
    const tem = this.contains(nome);
    const quer = forcar === undefined ? !tem : !!forcar;
    if (quer && !tem) { this.add(nome); }
    if (!quer && tem) { this.remove(nome); }
    return quer;
  }
}

class Evento {
  constructor(tipo, opcoes) {
    this.type = tipo;
    this.bubbles = !opcoes || opcoes.bubbles !== false;
    this.target = null;
    this.currentTarget = null;
    this.defaultPrevented = false;
    this.parado = false;
    Object.assign(this, (opcoes && opcoes.dados) || {});
  }

  preventDefault() { this.defaultPrevented = true; }
  stopPropagation() { this.parado = true; }
}

/* Quem ouve eventos: elementos, documento e janela. */
function comOuvintes(alvo) {
  alvo.ouvintes = new Map();
  alvo.addEventListener = function (tipo, funcao) {
    if (typeof funcao !== 'function') { throw new TypeError('ouvinte tem de ser função'); }
    if (!alvo.ouvintes.has(tipo)) { alvo.ouvintes.set(tipo, []); }
    alvo.ouvintes.get(tipo).push(funcao);
  };
  alvo.removeEventListener = function (tipo, funcao) {
    const fila = alvo.ouvintes.get(tipo) || [];
    const i = fila.indexOf(funcao);
    if (i !== -1) { fila.splice(i, 1); }
  };
  alvo.chama = function (evento) {
    evento.currentTarget = alvo;
    (alvo.ouvintes.get(evento.type) || []).slice().forEach((funcao) => funcao.call(alvo, evento));
  };
}

class Elemento extends No {
  constructor(documento, nome, espaco) {
    super(documento);
    this.nodeType = 1;
    this.namespaceURI = espaco || ESPACO_HTML;
    this.localName = this.namespaceURI === ESPACO_HTML ? String(nome).toLowerCase() : String(nome);
    this.tagName = this.namespaceURI === ESPACO_HTML ? this.localName.toUpperCase() : this.localName;
    this.atributos = new Map();
    this.classList = new ListaDeClasses(this);
    this.style = {};
    this.valor = null;
    comOuvintes(this);
  }

  /* ----- o que o site não pode usar ----- */
  get innerHTML() { return proibido('innerHTML'); }
  set innerHTML(v) { proibido('innerHTML'); }
  get outerHTML() { return proibido('outerHTML'); }
  set outerHTML(v) { proibido('outerHTML'); }
  insertAdjacentHTML() { proibido('insertAdjacentHTML'); }

  /* ----- atributos ----- */
  setAttribute(nome, valor) {
    const chave = String(nome);
    if (/^on/i.test(chave)) { proibido('atributo de evento ' + chave); }
    if (chave.toLowerCase() === 'style') { proibido('atributo style'); }
    this.atributos.set(chave, String(valor));
  }

  getAttribute(nome) { return this.atributos.has(nome) ? this.atributos.get(nome) : null; }
  hasAttribute(nome) { return this.atributos.has(nome); }
  removeAttribute(nome) { this.atributos.delete(nome); }

  get id() { return this.getAttribute('id') || ''; }
  set id(v) { this.setAttribute('id', v); }
  get className() { return this.getAttribute('class') || ''; }
  set className(v) { this.setAttribute('class', v); }
  get hidden() { return this.hasAttribute('hidden'); }
  set hidden(v) { if (v) { this.setAttribute('hidden', ''); } else { this.removeAttribute('hidden'); } }

  /* valor de campo: o que foi posto, ou o atributo, ou a primeira opção */
  get value() {
    if (this.valor !== null) { return this.valor; }
    if (this.localName === 'select') {
      const opcao = this.querySelector('option');
      return opcao ? opcao.value : '';
    }
    return this.getAttribute('value') || '';
  }

  set value(v) { this.valor = String(v); }

  get children() { return this.childNodes.filter((filho) => filho.nodeType === 1); }

  /* ----- eventos ----- */
  dispatchEvent(evento) {
    evento.target = evento.target || this;
    const janela = this.ownerDocument.defaultView;
    const caminho = [];
    for (let n = this; n; n = n.parentNode) { caminho.push(n); }
    if (this.ownerDocument.contains(this)) { caminho.push(this.ownerDocument, janela); }
    for (const alvo of caminho) {
      alvo.chama(evento);
      if (evento.parado || !evento.bubbles) { break; }
    }
    return !evento.defaultPrevented;
  }

  /* Clique: dispara o evento e, se ninguém cancelou, segue o link interno. */
  click() {
    const evento = new Evento('click');
    this.dispatchEvent(evento);
    if (evento.defaultPrevented) { return; }
    for (let n = this; n && n.nodeType === 1; n = n.parentNode) {
      const href = n.localName === 'a' ? n.getAttribute('href') : null;
      if (href && href.charAt(0) === '#') {
        this.ownerDocument.defaultView.location.hash = href;
        return;
      }
    }
  }

  focus() {
    const documento = this.ownerDocument;
    const anterior = documento.activeElement;
    if (anterior === this) { return; }
    if (anterior && anterior !== documento.body) { anterior.dispatchEvent(new Evento('blur', { bubbles: false })); }
    documento.activeElement = this;
    this.dispatchEvent(new Evento('focus', { bubbles: false }));
  }

  blur() {
    if (this.ownerDocument.activeElement !== this) { return; }
    this.ownerDocument.activeElement = this.ownerDocument.body;
    this.dispatchEvent(new Evento('blur', { bubbles: false }));
  }

  scrollIntoView() { this.ownerDocument.rolagens.push(this); }

  /* ----- busca ----- */
  descendentes() {
    const achados = [];
    (function desce(no) {
      no.childNodes.forEach((filho) => {
        if (filho.nodeType === 1) { achados.push(filho); desce(filho); }
      });
    }(this));
    return achados;
  }

  getElementsByTagName(nome) {
    const alvo = String(nome).toLowerCase();
    return this.descendentes().filter((el) => alvo === '*' || el.localName.toLowerCase() === alvo);
  }

  querySelectorAll(seletor) { return this.descendentes().filter((el) => casa(el, seletor, this)); }
  querySelector(seletor) { return this.querySelectorAll(seletor)[0] || null; }
  matches(seletor) { return casa(this, seletor, null); }

  closest(seletor) {
    for (let n = this; n && n.nodeType === 1; n = n.parentNode) {
      if (casa(n, seletor, null)) { return n; }
    }
    return null;
  }
}

/* ------------------------------------------------------------ seletores */

/* Seletor simples: tag, #id, .classe, [atr], [atr="v"], [atr^="v"], [atr*="v"]. */
function casaSimples(el, simples) {
  const pedacos = simples.match(/(^[a-zA-Z][\w-]*|\*|#[\w-]+|\.[\w-]+|\[[^\]]+\])/g);
  if (!pedacos || pedacos.join('') !== simples) { throw new Error('seletor que o DOM falso não entende: ' + simples); }
  return pedacos.every((p) => {
    if (p === '*') { return true; }
    if (p.charAt(0) === '#') { return el.getAttribute('id') === p.slice(1); }
    if (p.charAt(0) === '.') { return el.classList.contains(p.slice(1)); }
    if (p.charAt(0) === '[') {
      const m = p.match(/^\[([\w:-]+)(?:([\^*$]?=)"?([^"\]]*)"?)?\]$/);
      if (!m) { throw new Error('seletor de atributo que o DOM falso não entende: ' + p); }
      const valor = el.getAttribute(m[1]);
      if (valor === null) { return false; }
      if (!m[2]) { return true; }
      if (m[2] === '=') { return valor === m[3]; }
      if (m[2] === '^=') { return valor.startsWith(m[3]); }
      if (m[2] === '$=') { return valor.endsWith(m[3]); }
      return valor.includes(m[3]);
    }
    return el.localName.toLowerCase() === p.toLowerCase();
  });
}

/* Lista separada por vírgula; em cada uma, descendente (espaço) e filho (>). */
function casa(el, seletor, limite) {
  return String(seletor).split(',').some((parte) => {
    const fichas = parte.trim().replace(/\s*>\s*/g, ' > ').split(/\s+/);
    let atual = [el];
    for (let i = fichas.length - 1; i >= 0; i -= 1) {
      if (fichas[i] === '>') { continue; }
      atual = atual.filter((no) => casaSimples(no, fichas[i]));
      if (!atual.length || i === 0) { break; }
      const soPai = fichas[i - 1] === '>';
      const proximos = [];
      atual.forEach((no) => {
        for (let p = no.parentNode; p && p.nodeType === 1 && p !== limite; p = p.parentNode) {
          proximos.push(p);
          if (soPai) { break; }
        }
      });
      atual = proximos;
    }
    return atual.length > 0;
  });
}

/* ------------------------------------------------------------ documento */

class Documento extends No {
  constructor() {
    super(null);
    this.nodeType = 9;
    this.ownerDocument = this;
    this.defaultView = null;
    this.readyState = 'complete';
    this.visibilityState = 'visible';
    this.titulo = '';
    this.rolagens = [];
    this.criados = [];      /* todo elemento criado pelo script, na ordem */
    comOuvintes(this);
    this.documentElement = null;
    this.head = null;
    this.body = null;
    this.activeElement = null;
  }

  get title() { return this.titulo; }
  set title(v) { this.titulo = String(v); }
  get hidden() { return this.visibilityState !== 'visible'; }
  get cookie() { return proibido('document.cookie'); }
  set cookie(v) { proibido('document.cookie'); }
  write() { proibido('document.write'); }
  writeln() { proibido('document.writeln'); }

  createElement(nome) {
    if (!/^[a-zA-Z][a-zA-Z0-9]*$/.test(String(nome))) { throw new Error('nome de elemento inválido: ' + nome); }
    const el = new Elemento(this, nome, ESPACO_HTML);
    this.criados.push(el);
    return el;
  }

  createElementNS(espaco, nome) {
    const el = new Elemento(this, nome, espaco);
    this.criados.push(el);
    return el;
  }

  createTextNode(texto) { return new NoDeTexto(this, texto); }

  descendentes() { return this.documentElement ? [this.documentElement].concat(this.documentElement.descendentes()) : []; }
  getElementById(id) { return this.descendentes().find((el) => el.getAttribute('id') === id) || null; }
  getElementsByTagName(nome) { return this.descendentes().filter((el) => el.localName.toLowerCase() === String(nome).toLowerCase()); }
  querySelectorAll(seletor) { return this.descendentes().filter((el) => casa(el, seletor, null)); }
  querySelector(seletor) { return this.querySelectorAll(seletor)[0] || null; }

  dispatchEvent(evento) {
    evento.target = evento.target || this;
    this.chama(evento);
    if (!evento.parado && evento.bubbles && this.defaultView) { this.defaultView.chama(evento); }
    return !evento.defaultPrevented;
  }
}

/* ------------------------------------------------- leitor do index.html */

const ENTIDADES = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ' };

function semEntidades(texto) {
  return texto.replace(/&(#\d+|#x[0-9a-fA-F]+|[a-zA-Z]+);/g, (tudo, nome) => {
    if (nome.charAt(0) === '#') {
      const codigo = nome.charAt(1).toLowerCase() === 'x' ? parseInt(nome.slice(2), 16) : parseInt(nome.slice(1), 10);
      return String.fromCodePoint(codigo);
    }
    if (!(nome in ENTIDADES)) { throw new Error('entidade que o leitor não conhece: ' + tudo); }
    return ENTIDADES[nome];
  });
}

/* Lê o HTML bem formado do index.html e devolve um Documento. Não é um
   leitor de HTML geral: marca torta dá erro, de propósito. */
function leHtml(html) {
  const documento = new Documento();
  const pilha = [documento];
  const marca = /<!--[\s\S]*?-->|<!doctype[^>]*>|<\/([a-zA-Z][\w-]*)\s*>|<([a-zA-Z][\w-]*)((?:\s+[\w:-]+(?:\s*=\s*"[^"]*")?)*)\s*(\/?)>/gi;
  let fim = 0;
  let m;

  function poeTexto(texto) {
    if (texto === '' || (/^\s*$/.test(texto) && texto.includes('\n'))) { return; }
    if (texto.includes('<')) { throw new Error('marca torta no HTML perto de: ' + texto.slice(0, 40)); }
    const pai = pilha[pilha.length - 1];
    if (pai === documento) { throw new Error('texto solto fora de <html>: ' + texto.slice(0, 40)); }
    pai.appendChild(new NoDeTexto(documento, semEntidades(texto)));
  }

  while ((m = marca.exec(html)) !== null) {
    poeTexto(html.slice(fim, m.index));
    fim = marca.lastIndex;
    if (m[1]) {
      const aberto = pilha.pop();
      if (!aberto || aberto.localName !== (aberto.namespaceURI === ESPACO_HTML ? m[1].toLowerCase() : m[1])) {
        throw new Error('fecho </' + m[1] + '> sem abertura correspondente');
      }
    } else if (m[2]) {
      const pai = pilha[pilha.length - 1];
      const emSvg = m[2].toLowerCase() === 'svg' || (pai !== documento && pai.namespaceURI === ESPACO_SVG);
      const el = new Elemento(documento, m[2], emSvg ? ESPACO_SVG : ESPACO_HTML);
      const atributo = /([\w:-]+)(?:\s*=\s*"([^"]*)")?/g;
      let a;
      while ((a = atributo.exec(m[3])) !== null) {
        /* aqui não há guarda: atributo proibido no arquivo é achado pelo teste estático */
        el.atributos.set(emSvg ? a[1] : a[1].toLowerCase(), a[2] === undefined ? '' : semEntidades(a[2]));
      }
      pai.appendChild(el);
      if (!m[4] && !SEM_FECHO.has(el.localName)) { pilha.push(el); }
    }
  }
  poeTexto(html.slice(fim));
  if (pilha.length !== 1) { throw new Error('elemento sem fecho: <' + pilha[pilha.length - 1].localName + '>'); }

  documento.documentElement = documento.childNodes.find((n) => n.nodeType === 1) || null;
  if (!documento.documentElement || documento.documentElement.localName !== 'html') { throw new Error('falta o <html>'); }
  documento.head = documento.documentElement.children.find((el) => el.localName === 'head') || null;
  documento.body = documento.documentElement.children.find((el) => el.localName === 'body') || null;
  documento.activeElement = documento.body;
  const titulo = documento.querySelector('title');
  documento.titulo = titulo ? titulo.textContent : '';
  return documento;
}

/* --------------------------------------------------------------- relógio */

/* Relógio controlado: o tempo só anda quando o teste manda. */
class Relogio {
  constructor(agora) {
    this.agora = agora;
    this.fila = [];
    this.proximo = 1;
  }

  marca(funcao, ms, repete) {
    const id = this.proximo;
    this.proximo += 1;
    this.fila.push({ id, funcao, quando: this.agora + Math.max(0, Number(ms) || 0), repete: repete ? Math.max(1, Number(ms) || 1) : 0 });
    return id;
  }

  desmarca(id) { this.fila = this.fila.filter((t) => t.id !== id); }

  /* Anda o tempo e roda, na ordem, o que venceu. */
  avanca(ms) {
    const alvo = this.agora + ms;
    for (;;) {
      const vencidos = this.fila.filter((t) => t.quando <= alvo).sort((a, b) => a.quando - b.quando || a.id - b.id);
      if (!vencidos.length) { break; }
      const t = vencidos[0];
      this.agora = Math.max(this.agora, t.quando);
      if (t.repete) { t.quando += t.repete; } else { this.desmarca(t.id); }
      t.funcao();
    }
    this.agora = alvo;
  }
}

/* Date com relógio controlado. Recusa data sem hora: o site tem de cortar o
   texto, e não passar por Date. Guarda o que recebeu, para o teste conferir. */
function criaDate(relogio, recebidos) {
  const semHora = /^\s*\d{4}-\d{2}-\d{2}\s*$/;
  function confere(args) {
    recebidos.push(args);
    if (args.length === 1 && typeof args[0] === 'string' && semHora.test(args[0])) {
      proibido('Date recebeu data sem hora: ' + args[0]);
    }
    if (args.length > 1) { proibido('Date montada por partes usa o fuso da máquina'); }
  }
  return class DateControlada extends Date {
    constructor(...args) {
      if (args.length === 0) { super(relogio.agora); } else { confere(args); super(...args); }
    }

    static now() { return relogio.agora; }
    static parse(texto) { confere([texto]); return Date.parse(texto); }
  };
}

/* ------------------------------------------------------------------ rede */

/* fetch falso: serve arquivos de uma tabela caminho -> objeto.
   Caminho ausente responde 404. Valor Error é falha de rede. Texto é
   entregue como está, para testar JSON quebrado. */
function criaRede(arquivos) {
  const rede = {
    arquivos: Object.assign({}, arquivos),
    pedidos: [],
    retidos: [],
    segura: false,     /* true: os pedidos ficam esperando até solta() */
    responde(caminho) {
      const valor = rede.arquivos[caminho];
      if (valor instanceof Error) { return Promise.reject(valor); }
      if (valor === undefined) {
        return Promise.resolve({ ok: false, status: 404, json: () => Promise.reject(new Error('sem corpo')) });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => new Promise((resolve) => resolve(JSON.parse(typeof valor === 'string' ? valor : JSON.stringify(valor))))
      });
    },
    fetch(caminho, opcoes) {
      rede.pedidos.push({ caminho: String(caminho), opcoes: opcoes || {} });
      if (/^[a-z][a-z0-9+.-]*:|^\/\//i.test(String(caminho))) { proibido('pedido para fora do site: ' + caminho); }
      if (!rede.segura) { return rede.responde(String(caminho)); }
      return new Promise((resolve, reject) => {
        rede.retidos.push(() => rede.responde(String(caminho)).then(resolve, reject));
      });
    },
    solta() {
      const fila = rede.retidos;
      rede.retidos = [];
      rede.segura = false;
      fila.forEach((libera) => libera());
    }
  };
  return rede;
}

/* ---------------------------------------------------------------- janela */

/* Monta a janela falsa em volta de um documento.
   opcoes: hash (endereço inicial), agora (ms), arquivos (tabela do fetch). */
function criaJanela(html, opcoes) {
  const documento = leHtml(html);
  const relogio = new Relogio(opcoes.agora);
  const rede = criaRede(opcoes.arquivos || {});
  const datasRecebidas = [];
  const janela = {};
  comOuvintes(janela);

  let hash = opcoes.hash || '';
  const historico = [];
  janela.location = {
    get hash() { return hash; },
    set hash(novo) {
      const valor = String(novo);
      const normal = valor === '' || valor.charAt(0) === '#' ? valor : '#' + valor;
      if (normal === hash) { return; }
      hash = normal;
      janela.dispatchEvent(new Evento('hashchange'));
    },
    get href() { return 'https://exemplo.invalid/INFOCENARIUM/' + hash; },
    pathname: '/INFOCENARIUM/'
  };
  janela.history = {
    replaceState(estado, titulo, url) {
      const texto = String(url);
      if (texto.charAt(0) !== '#') { proibido('history.replaceState com endereço que não é só o hash: ' + texto); }
      historico.push(texto);
      hash = texto;      /* sem evento: replaceState não dispara hashchange */
    },
    pushState() { proibido('history.pushState: o site não cria passo no histórico'); }
  };
  janela.dispatchEvent = function (evento) {
    evento.target = evento.target || janela;
    janela.chama(evento);
    return !evento.defaultPrevented;
  };
  janela.document = documento;
  janela.window = janela;
  janela.self = janela;
  janela.console = console;
  janela.URL = URL;
  janela.Date = criaDate(relogio, datasRecebidas);
  janela.fetch = rede.fetch;
  janela.setTimeout = (funcao, ms) => relogio.marca(funcao, ms, false);
  janela.setInterval = (funcao, ms) => relogio.marca(funcao, ms, true);
  janela.clearTimeout = (id) => relogio.desmarca(id);
  janela.clearInterval = (id) => relogio.desmarca(id);
  janela.rolagens = [];
  janela.scrollTo = (x, y) => { janela.rolagens.push([x, y]); };
  ['localStorage', 'sessionStorage', 'indexedDB'].forEach((nome) => {
    Object.defineProperty(janela, nome, { get() { return proibido(nome); }, enumerable: false });
  });
  documento.defaultView = janela;

  return { janela, documento, relogio, rede, datasRecebidas, historico, Evento };
}

module.exports = { criaJanela, leHtml, Evento, acusacoes, ESPACO_SVG, ESPACO_HTML };
