'use strict';

/* Segurança: texto de JSON nunca vira HTML, endereço de JSON só vira link se
 * for http ou https, e nada de fora é pedido. O DOM falso já lança erro em
 * innerHTML e companhia; aqui se confere o que ele não acusa sozinho. */

const test = require('node:test');
const assert = require('node:assert/strict');
const { abre, arquivos, arquivosDe35Dias, dados, edicaoDeExemplo, edicaoReal, entradaSolta, textoDe, DIA } = require('./apoio.js');

const MARCA = '<img src=x onerror=alert(1)>';
const PERIGO = 'javascript:alert(1)//';

/* Chaves cujo valor é id, lista fechada ou data: a estrutura da edição. */
const ESTRUTURA = new Set(['id', 'categoria', 'estado', 'tendencia', 'ref', 'dominio', 'veiculo', 'lado', 'alvo', 'tema',
  'sentido', 'partido', 'efeito', 'evidencia', 'player', 'para', 'confianca', 'continuacao_de', 'publicado_em', 'data',
  'desde', 'gerada_em', 'edicao', 'item', 'resposta', 'modo', 'tipo', 'time', 'anula_vetor', 'dominios', 'duvidas',
  'sem_preco', 'dna', 'arquivo', 'texto_do_indice', 'atualizado_em', 'criada_em', 'incluido_em', 'origem', 'de', 'anula',
  'sigla', 'voto_tipico', 'codigo', 'indicador', 'janela', 'frequencia', 'leitor', 'lado_confianca', 'fatos', 'serve_a',
  'alvos', 'partidos', 'players', 'revisado_em', 'cor', 'formato']);
const DE_ENDERECO = new Set(['url', 'controle_fonte', 'dna_fontes']);

/* Anda pelo JSON inteiro. Em todo campo de URL põe o endereço javascript:.
   Em todo campo de texto põe a marca de imagem. Com tudo = true, a marca
   entra também nos ids, nas listas fechadas e nas datas. */
function injeta(valor, tudo, chave) {
  if (typeof valor === 'string') {
    if (DE_ENDERECO.has(chave)) { return PERIGO; }
    return tudo || !ESTRUTURA.has(chave) ? MARCA : valor;
  }
  if (Array.isArray(valor)) { return valor.map((v) => injeta(v, tudo, chave)); }
  if (valor && typeof valor === 'object') {
    const novo = {};
    Object.keys(valor).forEach((k) => { novo[k] = injeta(valor[k], tudo, DE_ENDERECO.has(chave) || (chave === 'dna' && !tudo) ? chave : k); });
    return novo;
  }
  return valor;
}

/* Listas fechadas: toda marca e todo atributo que o script cria. As vistas
   Arquivo, Régua e Método trouxeram a navegação das abas (nav), o campo de
   busca com rótulo (input, label), as listas numeradas do Método (ol) e o
   desenho das mini-linhas (polyline, circle, com points, cx, cy e r). */
const TAGS_DO_SITE = new Set(['a', 'abbr', 'article', 'button', 'caption', 'circle', 'dd', 'div', 'dl', 'dt', 'h1', 'h2', 'h3', 'h4',
  'input', 'label', 'li', 'nav', 'ol', 'option', 'p', 'polyline', 'section', 'select', 'span', 'strong', 'svg', 'table', 'tbody',
  'td', 'th', 'thead', 'time', 'tr', 'ul', 'use']);
const ATRIBUTOS_DO_SITE = new Set(['class', 'id', 'href', 'target', 'rel', 'tabindex', 'role', 'type', 'hidden', 'title',
  'datetime', 'translate', 'scope', 'value', 'viewBox', 'focusable', 'data-rotulo', 'aria-hidden', 'aria-label',
  'aria-labelledby', 'aria-expanded', 'aria-controls', 'aria-pressed', 'aria-busy', 'aria-current',
  'for', 'maxlength', 'colspan', 'points', 'cx', 'cy', 'r', 'lang']);
/* atributos de medida e de desenho: só números, postos pelo script */
const ATRIBUTOS_DE_NUMERO = new Set(['points', 'cx', 'cy', 'r', 'colspan', 'maxlength', 'viewBox']);
/* atributos que podem levar texto de JSON: entram por setAttribute, como texto */
const ATRIBUTOS_DE_TEXTO = new Set(['title', 'aria-label', 'data-rotulo']);
const INTERNO = /^#\/[a-z0-9_\-\/?=&%.]*$/;
const DO_SITE = /^(feed\.xml|edicoes\/\d{4}-\d{2}-\d{2}\.(json|md))$/;

/* Confere a página inteira. Devolve quantos links externos achou. */
function confereSemInjecao(m, rotuloDoCaso) {
  const caso = rotuloDoCaso + ': ';
  const principal = m.um('main');
  const rodape = m.um('footer');
  /* 1. nenhum elemento novo nasce do texto: o script só cria as marcas dele */
  m.documento.criados.forEach((el) => {
    assert.ok(TAGS_DO_SITE.has(el.localName), caso + 'elemento criado: <' + el.localName + '>');
  });
  assert.equal(principal.querySelectorAll('img, script, iframe, object, embed, style, form, base, link, textarea').length, 0,
    caso + 'elemento estranho no conteúdo');
  /* o único campo de digitar é a busca da Régua: não envia nada, só recorta a lista */
  principal.querySelectorAll('input').forEach((campo) => {
    assert.equal(campo.getAttribute('type'), 'search', caso + 'campo que não é de busca');
    assert.equal(campo.getAttribute('class'), 'campo campo--busca', caso + 'campo');
    assert.equal(campo.hasAttribute('name'), false, caso + 'campo com nome para envio');
  });
  let externos = 0;
  [principal, rodape].concat(principal.descendentes(), rodape.descendentes()).forEach((el) => {
    el.atributos.forEach((valor, nome) => {
      /* 2. nenhum atributo fora da lista; nenhum de evento; nenhum style */
      assert.ok(ATRIBUTOS_DO_SITE.has(nome), caso + 'atributo ' + nome + ' em <' + el.localName + '>');
      /* 3. a marca só aparece em atributo de texto. Num href de http, o texto
         da marca pode sobrar no caminho, já sem os sinais que fazem HTML. */
      if (nome === 'href') {
        assert.equal(/[<>" ]|^\s*javascript:/i.test(valor), false, caso + 'href="' + valor + '"');
      } else if (ATRIBUTOS_DE_NUMERO.has(nome)) {
        assert.match(valor, /^[0-9., -]+$/, caso + nome + '="' + valor + '"');
      } else if (!ATRIBUTOS_DE_TEXTO.has(nome)) {
        assert.equal(/[<>"]|onerror|javascript/i.test(valor), false, caso + nome + '="' + valor + '"');
      }
    });
    if (el.hasAttribute('id')) { assert.match(el.getAttribute('id'), /^[a-z0-9_-]+$/, caso + 'id de elemento'); }
    if (el.hasAttribute('class')) { assert.match(el.getAttribute('class'), /^[a-z0-9_ -]*$/, caso + 'classe'); }
    /* lang vem do mapa de veículos: só marca de idioma, nunca texto livre */
    if (el.hasAttribute('lang')) { assert.match(el.getAttribute('lang'), /^[a-z]{2,3}(-[A-Za-z0-9]{2,8})?$/, caso + 'lang'); }
    if (el.hasAttribute('datetime')) {
      assert.match(el.getAttribute('datetime'), /^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}Z)?$/, caso + 'datetime');
    }
    /* 4. nenhum href sai de http ou https, salvo os endereços do próprio site */
    if (el.hasAttribute('href') && el.localName === 'a') {
      const href = el.getAttribute('href');
      if (INTERNO.test(href) || DO_SITE.test(href)) { return; }
      const url = new URL(href);
      assert.ok(url.protocol === 'http:' || url.protocol === 'https:', caso + 'href ' + href);
      assert.equal(el.getAttribute('target'), '_blank', caso + href);
      assert.equal(el.getAttribute('rel'), 'noopener noreferrer', caso + href);
      externos += 1;
    }
    if (el.localName === 'use') { assert.match(el.getAttribute('href'), /^#i-[a-z0-9-]+$/, caso + 'ícone'); }
  });
  /* 5. nada é pedido fora do site */
  m.rede.pedidos.forEach((p) => {
    assert.match(p.caminho, /^(edicoes\/(indice|\d{4}-\d{2}-\d{2})\.json|dados\/(regua|players|veiculos|vetores|indicadores)\.json)$/, caso + 'pedido');
  });
  return externos;
}

test('injeção em todo campo de texto e de URL da edição: nenhum elemento nasce, nenhum link perigoso', async () => {
  const edicao = injeta(edicaoDeExemplo(), false);
  /* o índice é o de uma edição sã: ele é conferido em outro teste */
  const tabela = arquivos();
  tabela['edicoes/2026-11-19.json'] = edicao;
  const m = await abre({ arquivos: tabela });
  assert.equal(m.todos('main h2').length, 9, 'o Painel monta inteiro');
  assert.equal(m.todos('.principal').length, 3);
  assert.equal(m.todos('.radar__item').length, 6);
  /* abre tudo, para o texto do dossiê também contar */
  for (const botao of m.todos('button[aria-controls]')) { await m.clica(botao); }
  const externos = confereSemInjecao(m, 'texto e URL');
  assert.equal(externos, 0, 'todo endereço javascript: virou texto simples, sem href');
  assert.equal(m.todos('a.externo').length, 0);
  assert.equal(/javascript:/.test(m.todos('a').map((a) => a.getAttribute('href')).join(' ')), false);
  /* a marca está na tela como texto, letra por letra */
  const conteudo = m.um('main').textContent;
  const vezes = conteudo.split(MARCA).length - 1;
  assert.ok(vezes > 150, 'a marca aparece como texto ' + vezes + ' vezes');
  assert.equal(textoDe(m.um('#item-p1 h3')), MARCA);
  assert.equal(m.um('#item-p1 h3').children.length, 0, 'o título é um nó de texto só');
  assert.equal(textoDe(m.um('.alerta__resumo')), MARCA);
  /* onde havia link externo fica o texto, sem href */
  assert.equal(m.um('#item-p1 .ataque__link').children[0].localName, 'span');
  assert.equal(textoDe(m.um('#item-p1 .ataque__link')), 'ler no veículo');
});

test('injeção em TODO texto, inclusive ids, listas fechadas e datas: o Painel não quebra', async () => {
  const edicao = injeta(edicaoDeExemplo(), true);
  const tabela = arquivos();
  tabela['edicoes/2026-11-19.json'] = edicao;
  const m = await abre({ arquivos: tabela });
  assert.equal(textoDe(m.um('h1')), 'Edição de 19/11/2026', 'a data vem do índice, já conferida');
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
  assert.equal(m.todos('main h2').length, 9);
  for (const botao of m.todos('button[aria-controls]')) { await m.clica(botao); }
  assert.equal(confereSemInjecao(m, 'tudo'), 0);
  /* id fora da forma não vira id de elemento nem endereço */
  assert.equal(m.todos('.principal').length, 3);
  m.todos('.principal, .radar__item, .dominio, .ficha').forEach((el) => assert.equal(el.hasAttribute('id'), false));
  assert.equal(m.janela.location.hash, '', 'abrir item sem id válido não mexe no endereço');
  assert.ok(m.um('main').textContent.split(MARCA).length > 300);
});

test('injeção nos arquivos de apoio e no índice: régua, players, veículos, vetores e catálogo', async () => {
  const tabela = arquivos({ edicoes: [edicaoReal(DIA)], entradas: [entradaSolta('2026-11-18', { nivel: 2, resumo: MARCA })] });
  ['dados/regua.json', 'dados/players.json', 'dados/veiculos.json', 'dados/indicadores.json'].forEach((caminho) => {
    tabela[caminho] = injeta(tabela[caminho], false);
  });
  tabela['dados/vetores.json'].vetores.push(
    { id: '2026-11-10_p1_ue', data: '2026-11-10', item: 'p1', player: 'ue', de: 'centro_atlantico', para: 'soberanistas', forca: 1, tema: 'clima', porque: MARCA, url: PERIGO },
    { id: '2026-11-20_anula_1', data: '2026-11-20', anula: '2026-11-19_r2_google', porque: MARCA, url: PERIGO });
  const indice = tabela['edicoes/indice.json'];
  indice.edicoes[0].arquivo = PERIGO;
  indice.edicoes[0].texto = 'https://exemplo.invalid/fora.md';
  indice.edicoes[0].corrigida_em = [MARCA, PERIGO, '2026-11-18'];
  indice.edicoes.push({ data: MARCA, arquivo: PERIGO, estado: MARCA, nivel: MARCA, resumo: MARCA });
  const m = await abre({ arquivos: tabela });
  assert.equal(textoDe(m.um('h1')), 'Edição de 19/11/2026');
  for (const botao of m.todos('button[aria-controls]')) { await m.clica(botao); }
  const externos = confereSemInjecao(m, 'apoio');
  assert.ok(externos > 40, 'os links da edição, que é sã, continuam valendo: ' + externos);
  /* nomes da régua e dos players aparecem como texto */
  assert.equal(textoDe(m.um('#dominio-energia h3')), MARCA);
  assert.equal(m.um('#dominio-energia h3').children.length, 0);
  assert.equal(m.um('.etiqueta--partido abbr').getAttribute('title'), MARCA, 'em atributo, a marca é só texto');
  assert.equal(textoDe(m.um('.selo__rotulo')), MARCA);
  /* o link de texto e de JSON sai da data, e não do caminho que o índice trouxe */
  assert.deepEqual(m.todos('.cabeca__acoes a').slice(-3).map((a) => a.getAttribute('href')),
    ['edicoes/2026-11-19.md', 'edicoes/2026-11-19.json', 'feed.xml']);
  /* a anulação com endereço perigoso mostra o motivo e nenhum link */
  const anulacao = m.um('#s-movimentos .vetor__anulacao');
  assert.equal(textoDe(anulacao), 'Anulado em 20/11: ' + MARCA + ' fonte da correção');
  assert.equal(anulacao.querySelectorAll('a').length, 0);
});

test('endereço http com marca dentro: vira href normalizado, e nada escapa do atributo', async () => {
  const edicao = edicaoReal(DIA, (e) => {
    e.principais[0].fontes[0].url = 'https://exemplo.invalid/a"><img src=x onerror=alert(1)>';
    e.principais[0].fontes[1].url = '  https://exemplo.invalid/com espaço  ';
    e.principais[0].fontes[2].url = 'HTTPS://EXEMPLO.invalid/Maiusculas';
    e.principais[0].fontes[3].url = 'https://usuario:senha@exemplo.invalid/';
    e.principais[0].fontes[4].url = 'https:exemplo.invalid/sem-barras';
    e.principais[0].fontes[5].url = 'https://';
  });
  const m = await abre({ arquivos: arquivos({ edicoes: [edicao] }) });
  const links = m.todos('#item-p1 .dossie .fonte').map((f) => f.querySelector('a.externo'));
  assert.equal(links[0].getAttribute('href'), 'https://exemplo.invalid/a%22%3E%3Cimg%20src=x%20onerror=alert(1)%3E');
  assert.equal(links[1].getAttribute('href'), 'https://exemplo.invalid/com%20espa%C3%A7o');
  assert.equal(links[2].getAttribute('href'), 'https://exemplo.invalid/Maiusculas');
  assert.equal(links[3], null, 'usuário e senha antes do @: sem link, como a regra de URL do validador (seg-03)');
  assert.equal(new URL(links[4].getAttribute('href')).hostname, 'exemplo.invalid');
  assert.equal(links[5], null, 'endereço que não abre como URL vira texto simples');
  confereSemInjecao(m, 'http com marca');
});

test('links externos: nova aba, rel fechado, ícone e o texto "(abre em nova aba)"', async () => {
  const m = await abre();
  for (const botao of m.todos('button[aria-controls]')) { await m.clica(botao); }
  const externos = m.todos('a[target="_blank"]');
  assert.ok(externos.length > 60, 'há ' + externos.length + ' links externos na edição de exemplo');
  externos.forEach((a) => {
    const href = a.getAttribute('href');
    assert.match(href, /^https:\/\/([a-z.]+\.)?exemplo\.invalid\//, href);
    assert.equal(a.getAttribute('rel'), 'noopener noreferrer');
    assert.ok(a.classList.contains('externo'));
    const escondidos = a.querySelectorAll('.so-leitor');
    assert.equal(textoDe(escondidos[escondidos.length - 1]), '(abre em nova aba)');
    assert.equal(a.querySelector('use').getAttribute('href'), '#i-externo');
    assert.equal(a.querySelector('svg').getAttribute('aria-hidden'), 'true');
  });
  /* e o contrário: todo link que sai do site abre em nova aba; os de dentro, não */
  m.todos('main a, footer a').forEach((a) => {
    const href = a.getAttribute('href');
    assert.equal(/^https?:/.test(href), a.getAttribute('target') === '_blank', href);
    if (!/^https?:/.test(href)) { assert.ok(INTERNO.test(href) || DO_SITE.test(href), 'link interno fora da forma: ' + href); }
  });
  assert.equal(confereSemInjecao(m, 'exemplo'), externos.length);
});

test('nomes de site nunca viram link: veículos sugeridos são texto simples', async () => {
  const edicao = edicaoReal(DIA, (e) => {
    e.bastidores.veiculos_sugeridos = ['Gazeta de Amostra (gazeta.exemplo.invalid)', 'https://exemplo.invalid/pagina', 'www.exemplo.invalid'];
    e.bastidores.limites = 'Ver https://exemplo.invalid/limites para detalhes.';
  });
  const m = await abre({ arquivos: arquivos({ edicoes: [edicao] }) });
  const secao = m.um('#s-bastidores');
  assert.equal(secao.querySelectorAll('a').length, 0);
  assert.deepEqual(secao.querySelectorAll('.bastidores__lista')[1].children.map(textoDe),
    ['Gazeta de Amostra (gazeta.exemplo.invalid)', 'https://exemplo.invalid/pagina', 'www.exemplo.invalid']);
  assert.equal(textoDe(secao.querySelector('.bastidores__limites')), 'Ver https://exemplo.invalid/limites para detalhes.');
});

test('referência com nome que todo objeto herda (constructor, __proto__) é só um id que não existe', async () => {
  const nomes = ['constructor', '__proto__', 'toString', 'hasOwnProperty', 'valueOf'];
  for (const nome of nomes) {
    const edicao = edicaoReal(DIA, (e) => {
      e.principais[0].ataques[0].veiculo = nome;
      e.principais[0].ataques[0].lado = nome;
      e.principais[0].ataques[1].alvo = nome;
      e.principais[0].eixo.tema = nome;
      e.principais[0].eixo.sentido = nome;
      e.principais[0].placar[0] = { partido: nome, efeito: nome, forca: nome, evidencia: nome, porque: 'Teste.' };
      e.principais[0].vetores[0].player = nome;
      e.principais[0].vetores[0].para = nome;
      e.principais[0].vetores[0].tema = nome;
      e.principais[0].categoria = nome;
      e.principais[0].confianca = nome;
      e.principais[0].dominios = [nome];
      e.alerta.tendencia = nome;
      e.alerta.dominios[0].tendencia = nome;
      e.alerta.dominios[0].gatilhos[0].ref = nome;
      e.alerta.dominios[1].sem_preco = [nome];
      e.indicadores[0].dominio = nome;
      e.placar_do_dia[0].partido = nome;
      e.respostas[0].resposta = nome;
      e.bastidores.modo = nome;
      e.novos_players[0].tipo = nome;
      e.novos_players[0].duvidas = [nome];
    });
    const tabela = arquivos({ edicoes: [edicao], entradas: [entradaSolta('2026-11-18', { nivel: 2 })] });
    const m = await abre({ arquivos: tabela });
    assert.equal(m.todos('main h2').length, 9, nome);
    assert.equal(m.todos('#avisos-gerais .aviso').length, 0, nome);
    const texto = textoDe(m.um('main'));
    assert.equal(/function |\[object|native code|undefined|NaN/.test(texto), false, nome + ': vazou algo que não é dado');
    assert.match(textoDe(m.um('#item-p1 .dossie .ataque__cabeca')), new RegExp('^' + nome + ' ' + nome + ' atira em'));
    assert.match(textoDe(m.um('#s-placar .placar__linha')), new RegExp('^' + nome + ' ' + nome + ': saldo mais 4'));
    assert.match(textoDe(m.um('#s-placar .placar__linha .placar__nota')), /30 dias \+4$/, nome + ': o acumulado é o do índice');
    /* e o partido de verdade, que ficou sem saldo no índice, não herda nada */
    assert.match(textoDe(m.todos('#s-placar .placar__linha')[2]), /^OG Partido da Ordem Global: saldo zero 0 30 dias 0 sem movimento hoje$/, nome);
    confereSemInjecao(m, nome);
  }
});

test('o endereço da página também é dado: rota com marca não cria elemento nem vira texto de HTML', async () => {
  for (const hash of ['#/edicao/2026-11-19/<img src=x onerror=alert(1)>', '#/<script>alert(1)</script>',
    '#/?cat=<img>&dom="onmouseover="alert(1)', '#/edicao/2026-11-19/p1?cat=%3Cimg%3E', '#/regua/players/%3Cimg%3E',
    '#javascript:alert(1)', '#/edicao/2026-11-19/../../etc']) {
    const m = await abre({ hash });
    confereSemInjecao(m, hash);
    assert.equal(m.todos('main img').length, 0, hash);
  }
  /* item que não existe aparece no aviso como texto, e só se tiver a forma de id */
  const m = await abre({ hash: '#/edicao/2026-11-19/nao_existe' });
  assert.equal(textoDe(m.um('#avisos-gerais .aviso')), 'ITEM NÃO ENCONTRADO A edição de 19/11/2026 não tem o item nao_existe.');
});

test('o site não grava nada no aparelho e não envia nada', async () => {
  /* o DOM falso lança erro em cookie, localStorage, sessionStorage e indexedDB,
     e em pedido para fora: rodar o Painel inteiro sem erro é a prova */
  const m = await abre();
  for (const botao of m.todos('button[aria-controls]')) { await m.clica(botao); }
  await m.vai('#/?cat=ia');
  /* e as outras vistas inteiras, com tudo aberto, um filtro e uma busca */
  for (const hash of ['#/arquivo?nivel=3', '#/regua/partidos', '#/regua/vetores', '#/regua/veiculos?lado=centrao', '#/metodo', '#/regua/players?q=mac']) {
    await m.vai(hash);
    await m.abreTudo();
  }
  await m.escreve(m.um('.filtros input'), 'x');
  await m.vai('#/');
  assert.ok(m.rede.pedidos.length >= 7);
  m.rede.pedidos.forEach((p) => {
    assert.deepEqual(Object.keys(p.opcoes), ['cache'], 'pedido só de leitura, sem corpo, sem cabeçalho, sem credencial');
    assert.equal(p.opcoes.cache, 'no-cache');
  });
});

/* ------------------------------------------ Arquivo, Régua e Método */

const VISTAS_NOVAS = ['#/arquivo', '#/regua/partidos', '#/regua/players', '#/regua/veiculos', '#/regua/vetores', '#/metodo'];
const DADOS = ['dados/regua.json', 'dados/players.json', 'dados/veiculos.json', 'dados/vetores.json', 'dados/indicadores.json'];

/* O registro congelado é vazio: estas entradas dão o que injetar em vetores.json. */
function comRegistro(tabela) {
  tabela['dados/vetores.json'].vetores.push(
    { id: '2026-11-10_p1_ue', data: '2026-11-10', item: 'p1', player: 'ue', de: 'centro_atlantico', para: 'soberanistas', forca: 1, tema: 'clima',
      porque: 'Vetor de teste.', url: 'https://exemplo.invalid/v1', conflito_de_interesse: true },
    { id: '2026-11-18_r2_google', data: '2026-11-18', item: 'r2', player: 'google', de: 'bancada_talento', para: 'ordem_global', forca: 2, tema: 'ia_depois',
      porque: 'Outro vetor de teste.', url: 'https://exemplo.invalid/v2' },
    { id: '2026-11-19_anula_1', data: '2026-11-19', anula: '2026-11-10_p1_ue', porque: 'Motivo da anulação.', url: 'https://exemplo.invalid/v3' });
  /* um player que entrou pela rotina: é o que traz justificativa, url e dna_fontes */
  tabela['dados/players.json'].players.push({
    id: 'republica_exemplo', nome: 'República de Exemplo', tipo: 'governo', partido: 'independentes', time: 'mudanca', time_discutivel: true,
    dna: { pandemia_inicio: 'W', pandemia_depois: 'Y', ia_inicio: 'W', ia_depois: 'B', moderacao: 'R', clima: 'W', imigracao: 'R' },
    dna_fontes: { pandemia_depois: 'https://exemplo.invalid/d1', ia_depois: 'https://exemplo.invalid/d2' }, duvidas: ['moderacao'],
    nota: 'País fictício.', justificativa: 'Entrou por ser alvo.', url: 'https://exemplo.invalid/j', origem: 'rotina', incluido_em: '2026-11-19'
  });
}

test('injeção em todo campo de texto e de URL dos cinco arquivos de dados e do índice: Arquivo, Régua e Método', async () => {
  for (const hash of VISTAS_NOVAS) {
    const tabela = arquivosDe35Dias(comRegistro);
    DADOS.concat(['edicoes/indice.json']).forEach((caminho) => { tabela[caminho] = injeta(tabela[caminho], false); });
    const m = await abre({ hash, arquivos: tabela });
    await m.abreTudo();
    assert.equal(m.todos('#avisos-gerais .aviso').length, 0, hash);
    const externos = confereSemInjecao(m, hash);
    assert.equal(externos, 0, hash + ': todo endereço javascript: virou texto simples, sem href');
    assert.equal(m.todos('main a.externo, main a[target]').length, 0, hash);
    assert.equal(/javascript:/i.test(m.todos('a').map((a) => a.getAttribute('href')).join(' ')), false, hash);
    /* a marca está na tela como texto, letra por letra */
    const vezes = m.um('main').textContent.split(MARCA).length - 1;
    assert.ok(vezes >= 30, hash + ': a marca aparece como texto ' + vezes + ' vezes');
  }
});

test('injeção nos dados: onde havia link externo fica o texto, sem href; nome que vira atributo é só texto', async () => {
  const tabela = () => {
    const t = arquivosDe35Dias(comRegistro);
    DADOS.concat(['edicoes/indice.json']).forEach((caminho) => { t[caminho] = injeta(t[caminho], false); });
    return t;
  };
  let m = await abre({ hash: '#/regua/veiculos/reuters', arquivos: tabela() });
  const reuters = m.um('#veiculo-reuters');
  assert.equal(textoDe(reuters.querySelector('h4')), MARCA);
  assert.equal(reuters.querySelector('h4').children.length, 0, 'o nome é um nó de texto só');
  assert.equal(reuters.querySelectorAll('.veiculo__corpo a[href^="http"]').length, 0);
  assert.equal(textoDe(reuters.querySelector('.feed__nota')), MARCA);
  assert.equal(reuters.querySelector('.feed__nota').children.length, 0);
  await m.abreTudo();
  /* controle_fonte e feed.url: o texto fica, sem link */
  const a16z = m.um('#veiculo-a16z');
  assert.equal(a16z.querySelector('.feed__url').localName, 'span');
  assert.equal(textoDe(a16z.querySelector('.feed__url')), PERIGO, 'o endereço recusado aparece como texto');
  assert.equal(a16z.querySelector('.feed__url').hasAttribute('href'), false);
  assert.equal(m.um('.etiqueta--partido abbr').getAttribute('title'), MARCA, 'em atributo, a marca é só texto');

  m = await abre({ hash: '#/regua/players/republica_exemplo', arquivos: tabela() });
  const corpo = m.documento.getElementById(m.um('#player-republica_exemplo button').getAttribute('aria-controls'));
  assert.equal(corpo.querySelectorAll('a.externo').length, 0, 'url e dna_fontes do player: sem link');
  assert.ok(textoDe(corpo).includes('Por que entrou: ' + MARCA + ' fonte Fontes das posições: '));

  m = await abre({ hash: '#/regua/vetores', arquivos: tabela() });
  const linhas = m.todos('.aba tbody tr');
  assert.equal(linhas.length, 2);
  assert.equal(textoDe(linhas[0].children[7]), 'prova');
  assert.equal(linhas[0].children[7].querySelectorAll('a').length, 0);
  assert.equal(textoDe(linhas[1].querySelector('.vetor__anulacao')), 'Anulado em 19/11: ' + MARCA + ' fonte da correção');

  m = await abre({ hash: '#/metodo', arquivos: tabela() });
  /* a contagem vem do catálogo: a cópia congelada dele ganha fontes nesta fase */
  const fontesDoCatalogo = dados().catalogo.indicadores.reduce((n, i) => n + i.fontes.length, 0);
  assert.equal(m.todos('.catalogo__fonte').length, fontesDoCatalogo);
  assert.equal(m.todos('.catalogo__fonte a').length, 0, 'nenhuma fonte do catálogo vira link');
  assert.equal(textoDe(m.um('#s-niveis .selo__rotulo')), MARCA);
  assert.equal(m.um('#s-niveis .selo__rotulo').children.length, 0);

  m = await abre({ hash: '#/arquivo', arquivos: tabela() });
  assert.equal(textoDe(m.um('.figura--dominios .fitinha__nome')), MARCA);
  assert.ok(m.um('.figura--dominios .fita').getAttribute('aria-label').startsWith(MARCA + ' nos últimos 30 dias'), 'em aria-label, a marca é só texto');
  assert.equal(m.um('.figura--dominios thead abbr').getAttribute('title'), MARCA);
  const linha = m.todos('.mes tbody tr')[2];
  assert.equal(linha.children[4].querySelector('span').textContent, MARCA, 'o resumo do índice');
  /* os links de texto e de JSON saem da data, e não do caminho que o índice trouxe */
  assert.deepEqual(linha.querySelectorAll('.edicao__links a').map((a) => a.getAttribute('href')), ['edicoes/2026-11-17.md', 'edicoes/2026-11-17.json']);
});

test('injeção em TODO texto dos dados, inclusive ids, listas fechadas e datas: as três vistas não quebram', async () => {
  for (const hash of VISTAS_NOVAS) {
    const tabela = arquivosDe35Dias(comRegistro);
    DADOS.forEach((caminho) => { tabela[caminho] = injeta(tabela[caminho], true); });
    const m = await abre({ hash, arquivos: tabela });
    await m.abreTudo();
    assert.equal(m.todos('#avisos-gerais .aviso').length, 0, hash);
    assert.equal(m.todos('h1').length, 1, hash);
    assert.equal(confereSemInjecao(m, hash + ' (tudo)'), 0);
    /* id fora da forma não vira id de elemento, nem classe, nem endereço */
    m.todos('.partido, .matriz__linha, .veiculo, .aba tbody tr').forEach((el) => assert.equal(el.hasAttribute('id'), false, hash));
    assert.equal(m.todos('main a[href*="img"], main a[href*="%3C"]').length, 0, hash);
    assert.equal(/undefined|NaN|\[object|function /.test(textoDe(m.um('main'))), false, hash + ': vazou algo que não é dado');
  }
  /* o índice inteiro com a marca: nenhuma data vale, e o Arquivo cai no estado vazio */
  const tabela = arquivosDe35Dias();
  tabela['edicoes/indice.json'] = injeta(tabela['edicoes/indice.json'], true);
  const m = await abre({ hash: '#/arquivo', arquivos: tabela });
  assert.equal(textoDe(m.um('#avisos-gerais .aviso')), 'NENHUMA EDIÇÃO AINDA A primeira sai às 18h de Brasília.');
  assert.equal(textoDe(m.um('#s-edicoes .vazio')), 'Nenhuma edição no arquivo.');
  assert.equal(m.um('.arquivo__atualizado'), null);
  confereSemInjecao(m, 'índice (tudo)');
});

test('nomes de site nunca viram link, nem quando têm cara de endereço: sites, nota de feeds e sufixos oficiais', async () => {
  const tabela = arquivosDe35Dias((t) => {
    const reuters = t['dados/veiculos.json'].veiculos.find((v) => v.id === 'reuters');
    reuters.sites = ['https://exemplo.invalid/site', 'www.exemplo.invalid', 'javascript:alert(1)'];
    reuters.idiomas = ['https://exemplo.invalid/idioma'];
    reuters.feeds_nota = 'Ler em https://exemplo.invalid/ultimas e em javascript:alert(1).';
    reuters.controle = 'Ver https://exemplo.invalid/controle.';
    t['dados/regua.json'].sites_oficiais.brasil = ['https://exemplo.invalid/gov', 'gov.br'];
    t['dados/regua.json'].conflito.termos = ['https://exemplo.invalid/termo'];
  });
  let m = await abre({ hash: '#/regua/veiculos/reuters', arquivos: tabela });
  const corpo = m.um('#veiculo-reuters .veiculo__corpo');
  assert.deepEqual(corpo.querySelectorAll('a').map((a) => a.getAttribute('href')),
    ['https://fullfact.org/online/associated-press-reuters-rothschilds/', '#/regua/partidos/centrao'],
    'só a fonte do controle, que é campo de endereço, e a sigla do partido');
  assert.ok(textoDe(corpo).includes('Sites https://exemplo.invalid/site, www.exemplo.invalid, javascript:alert(1)'));
  assert.ok(textoDe(corpo).endsWith('Ler em https://exemplo.invalid/ultimas e em javascript:alert(1).'));
  m = await abre({ hash: '#/metodo', arquivos: tabela });
  assert.equal(m.todos('#s-rotina .quadro')[4].querySelectorAll('a').length, 0);
  assert.ok(textoDe(m.todos('#s-rotina .quadro')[4]).includes('Sites oficiais do Brasil: https://exemplo.invalid/gov, gov.br'));
  assert.equal(m.todos('#s-conflito .quadro p')[2].querySelectorAll('a').length, 0);
});

test('nas outras vistas, referência com nome que todo objeto herda é só um id que não existe', async () => {
  for (const nome of ['constructor', '__proto__', 'toString', 'hasOwnProperty', 'valueOf']) {
    const tabela = arquivosDe35Dias((t) => {
      comRegistro(t);
      Object.assign(t['dados/veiculos.json'].veiculos[0], { lado: nome, tipo: nome, fatos: nome, lado_confianca: nome, serve_a: [nome], alvos: [nome] });
      const player = t['dados/players.json'].players[0];
      Object.assign(player, { partido: nome, tipo: nome, time: nome, duvidas: [nome], origem: nome });
      Object.assign(t['dados/vetores.json'].vetores[0], { player: nome, de: nome, para: nome, tema: nome, item: nome });
      t['dados/regua.json'].conflito.players.push(nome);
      t['dados/regua.json'].campos[0].partidos.push(nome);
      t['dados/indicadores.json'].indicadores[0].dominio = nome;
      t['dados/indicadores.json'].indicadores[0].frequencia = nome;
      const entrada = t['edicoes/indice.json'].edicoes[0];
      entrada.estado = nome;
      entrada.tendencia = nome;
      /* como viria de um arquivo: chaves próprias, sem herança */
      entrada.saldos = JSON.parse('{"' + nome + '": 5}');
      entrada.eixos = JSON.parse('{"' + nome + '": {"azul": 1, "vermelho": 2}}');
      entrada.indicadores = JSON.parse('{"' + nome + '": 7.5, "brent": 78.4}');
      entrada.niveis = JSON.parse('{"' + nome + '": 3, "energia": 3}');
    });
    /* o fetch falso entrega uma cópia a cada pedido: a tabela serve a todas as vistas */
    for (const hash of VISTAS_NOVAS) {
      const m = await abre({ hash, arquivos: tabela });
      await m.abreTudo();
      assert.equal(m.todos('h1').length, 1, nome + ' ' + hash);
      assert.equal(m.todos('#avisos-gerais .aviso').length, 0, nome + ' ' + hash);
      assert.equal(/function |\[object|native code|undefined|NaN/.test(textoDe(m.um('main'))), false, nome + ' ' + hash + ': vazou algo que não é dado');
      confereSemInjecao(m, nome + ' ' + hash);
    }
    /* no Arquivo, o partido, o tema e o indicador que ninguém conhece aparecem pelo id, com o número do arquivo */
    const m = await abre({ hash: '#/arquivo', arquivos: tabela });
    assert.equal(textoDe(m.todos('.figura--partidos .placar__topo').pop()), nome + ' +5', nome);
    assert.equal(textoDe(m.todos('.figura--atos .ato__tema').pop()), nome, nome);
    assert.equal(textoDe(m.todos('.figura--indicadores .mini h4').pop()), nome, nome);
    /* e o partido de verdade não herda nada: o saldo dele continua o do índice */
    assert.equal(textoDe(m.um('.figura--partidos .placar__topo')), 'OG +7', nome + ': 2, 1 e 4; o dia mais novo perdeu o saldo no teste');
  }
});

test('o endereço também é dado nas outras vistas: rota e busca com marca não criam elemento', async () => {
  for (const hash of ['#/arquivo?nivel=<img src=x onerror=alert(1)>', '#/regua/veiculos?q=<img src=x onerror=alert(1)>',
    '#/regua/players?q=%3Cscript%3Ealert(1)%3C%2Fscript%3E&partido=%3Cimg%3E', '#/regua/vetores?player=<img>', '#/regua/vetores/<img>',
    '#/metodo/<script>alert(1)</script>', '#/regua/<img>', '#/regua/partidos/javascript:alert(1)']) {
    const m = await abre({ hash, arquivos: arquivosDe35Dias(comRegistro) });
    confereSemInjecao(m, hash);
    assert.equal(m.todos('main img, main script').length, 0, hash);
  }
  /* a busca que veio do endereço aparece no campo e na frase, como texto */
  const m = await abre({ hash: '#/regua/players?q=%3Cimg%20src%3Dx%3E', arquivos: arquivosDe35Dias() });
  assert.equal(m.um('.filtros input').value, '<img src=x>');
  assert.equal(textoDe(m.um('.filtros__vazio p')), 'Nada encontrado para "<img src=x>".');
  assert.equal(m.um('.filtros__vazio p').children.length, 0);
});
