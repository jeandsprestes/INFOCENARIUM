'use strict';

/* A vista Método (#/metodo): os textos fixos, palavra por palavra, as tabelas
 * lidas da régua e do catálogo, a caixa de conflito de interesse no topo e as
 * âncoras de cada seção. Dados: a cópia congelada. */

const test = require('node:test');
const assert = require('node:assert/strict');
const { abre, arquivos, arquivosDe35Dias, dados, textoDe, aVista } = require('./apoio.js');

const textos = (lista) => lista.map(textoDe);
const CONGELADOS = dados();
const abreMetodo = (hash, mudancas) => abre({ hash: hash || '#/metodo', arquivos: arquivosDe35Dias(mudancas) });
const semNumero = (texto) => texto.replace(/^\d\. /, '');

/* Os textos fixos da tela de método, como a especificação do site os traz
   (seção 8.7), parágrafo por parágrafo. Foram copiados dela por script, e não
   do app.js: se um dos dois lados mudar uma palavra, o teste acusa. */
const TEXTOS = {
  "Aviso de conflito de interesse": [
    "As análises do INFOCENARIUM são escritas por um modelo de inteligência artificial (IA): o Claude, da empresa Anthropic. A Anthropic é um dos players da régua do INFOCENARIUM. Ou seja: quem escreve é parte interessada em uma das disputas que este site acompanha, a da IA.",
    "O risco é concreto. O modelo pode poupar quem o fez, pesar a mão contra concorrentes ou tratar como neutra a visão de mundo da empresa.",
    "O que o INFOCENARIUM faz para reduzir o risco:",
    "1. Leva a marca CONFLITO DE INTERESSE todo item de IA. Leva também todo item que tem alguém da lista abaixo como alvo ou como player em movimento, que cita um termo da lista, ou que usa fonte de veículo ligado à Anthropic. A marca é ligada por programa, e ninguém a desliga.",
    "2. Nesses itens, a confiança nunca passa de média.",
    "3. Nesses itens, um vetor só entra com prova em fonte primária.",
    "4. Quando o item envolve um nome ou um termo da lista, ou um veículo ligado à Anthropic, as fontes vêm de veículos de pelo menos 2 partidos.",
    "5. Toda afirmação traz o link da fonte, e o placar diz que tipo de evidência sustenta cada ganho ou perda.",
    "6. A régua, o mapa de veículos, os critérios de alerta e o código são públicos.",
    "O que isso não resolve: nenhuma pessoa revisa a edição antes de ela sair. Leia com desconfiança e confira as fontes.",
    "Ver a ficha da Anthropic na Régua."
  ],
  "As quatro perguntas": [
    "Toda edição responde quatro perguntas.",
    "1. O que aconteceu de fato? O fato verificável, separado do enquadramento.",
    "2. Quem atirou? Toda notícia é lida como um ataque lançado por um veículo. O INFOCENARIUM diz de que lado o veículo está, quem é o alvo e qual é o enquadramento. Fato verdadeiro também é usado como arma: \"ataque\" não quer dizer \"mentira\".",
    "3. Quem ganha e quem perde na prática? Por partido, olhando por cima das narrativas: o que mudou em preço, tropa, contrato, lei, voto ou sanção.",
    "4. O que isso muda para quem se prepara? O nível de alerta e o efeito em energia, alimentos, câmbio, cadeias de suprimento e risco de conflito."
  ],
  "A régua": [
    "A régua classifica cada player em 5 temas (7 posições) e em um partido. Ninguém muda de partido. Quando uma notícia mostra movimento, o INFOCENARIUM registra um vetor: para onde o player se desloca, com que força e por causa de quê. A classificação é editorial. Veja a Régua."
  ],
  "Níveis de alerta": [
    "O nível vai de 1 a 5 e só muda com gatilho concreto e citado. O nível geral é o maior entre os cinco domínios. Um domínio sobe no dia em que um critério da tabela é cumprido. Sem gatilho novo, ele se mantém por 2 edições e depois desce um degrau por vez. Dia em que faltou o dado de preço do domínio não entra nessa conta: o INFOCENARIUM não mediu. Um nível 4 ou 5 também desce um degrau quando acaba o estado que o sustentava: é o gatilho de alívio. Alta de preço de nível 3 ou 4 só vale com uma segunda fonte que confirme; sem ela, vale como nível 2. Sem alarmismo: ameaça não é fato consumado."
  ],
  "De onde vem cada número": [
    "Os indicadores vêm de fontes públicas e gratuitas. Cada ficha do Painel traz o link da fonte usada no dia. Número antigo aparece com a data. Número que não veio aparece como \"sem dado\", com o nome da fonte prevista, sem link."
  ],
  "Como a edição é feita": [
    "Todo dia, às 18h de Brasília, um agente de IA roda sozinho, lê as notícias do dia nos veículos do mapa e escreve a edição. Um programa calcula os níveis de alerta, o placar do dia e a marca de conflito de interesse. Um validador automático confere tudo antes de publicar.",
    "Estados: completa; reduzida (menos itens que o normal); sem edição (a rotina não fechou o dia).",
    "Confiança: alta pede fontes de veículos dos dois campos (o da ordem e o da contestação) e uma fonte forte. Média pede 2 fontes de veículos de partidos diferentes, ou uma fonte forte. O resto é baixa. Fonte forte é veículo confiável nos fatos, ou documento primário de site oficial.",
    "Placar: o saldo de um partido soma só o que tem evidência material. Ganho de narrativa é contado à parte e vale no máximo força 1.",
    "Os quadros abaixo vêm direto da régua: os campos, a escala de força, os tipos de evidência, quando um time avança e que sites valem como fonte primária."
  ],
  "Limites e correções": [
    "O INFOCENARIUM não é recomendação de investimento, nem orientação de saúde ou de segurança.",
    "O agente pode errar. Página da web é tratada como dado, nunca como ordem. Edição publicada não muda: a correção sai na errata de uma edição seguinte, e a edição antiga ganha o aviso \"corrigida\". Vetor errado não se apaga: é anulado e fica riscado no registro. Quando vence a data de uma pergunta-chave, a edição do dia responde se a leitura se confirmou. O lado de cada veículo é classificação editorial; enquanto o mapa não for revisado, ele aparece marcado como rascunho. Este site não usa cookies, não guarda nada no seu aparelho e não carrega nada de terceiros."
  ]
};

test('Método: título, navegação e as 7 seções numeradas', async () => {
  const m = await abreMetodo();
  assert.equal(textoDe(m.um('h1')), 'Método');
  assert.equal(m.todos('h1').length, 1);
  assert.equal(m.documento.title, 'INFOCENARIUM · Método');
  assert.equal(m.um('nav a[aria-current="page"]').textContent, 'Método');
  assert.equal(m.um('#vista').getAttribute('class'), 'vista vista--metodo');
  assert.equal(m.um('#vista').hasAttribute('aria-busy'), false);
  assert.deepEqual(textos(m.todos('main h2')), ['01 AVISO DE CONFLITO DE INTERESSE', '02 AS QUATRO PERGUNTAS', '03 A RÉGUA', '04 NÍVEIS DE ALERTA',
    '05 DE ONDE VEM CADA NÚMERO', '06 COMO A EDIÇÃO É FEITA', '07 LIMITES E CORREÇÕES']);
  assert.deepEqual(m.todos('main section').map((s) => s.getAttribute('id')),
    ['s-conflito', 's-perguntas', 's-regua', 's-niveis', 's-indicadores', 's-rotina', 's-limites']);
  m.todos('main section').forEach((s) => assert.equal(s.getAttribute('aria-labelledby'), s.querySelector('h2').getAttribute('id')));
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
  /* o que a vista lê: a régua, o catálogo e os players; o índice vai junto, e nenhuma edição */
  assert.deepEqual(m.rede.pedidos.map((p) => p.caminho).sort(),
    ['dados/indicadores.json', 'dados/players.json', 'dados/regua.json', 'edicoes/indice.json']);
  /* uma vista, um trabalho de cor: nada de DNA aqui */
  assert.equal(m.um('main').querySelectorAll('[class*="dna"]').length, 0);
});

test('Método 01: a caixa de conflito de interesse vem no topo, com o texto integral, palavra por palavra', async () => {
  const m = await abreMetodo();
  const secao = m.um('#s-conflito');
  assert.equal(m.um('.vista__corpo').children[0], secao, 'é a primeira seção da vista');
  const caixa = secao.querySelector('.secao__corpo').children[0];
  assert.equal(caixa.getAttribute('class'), 'caixa', 'a caixa é a primeira coisa abaixo do título');
  const esperado = TEXTOS['Aviso de conflito de interesse'];
  assert.equal(esperado.length, 11);
  const paragrafos = caixa.children.filter((el) => el.localName === 'p');
  assert.deepEqual(textos(paragrafos), [esperado[0], esperado[1], esperado[2], esperado[9], esperado[10]]);
  /* as seis medidas, numeradas pela lista */
  const lista = caixa.querySelector('ol');
  assert.deepEqual(textos(lista.children), esperado.slice(3, 9).map(semNumero));
  assert.equal(lista.children.length, 6);
  assert.deepEqual(caixa.children.map((el) => el.localName), ['p', 'p', 'p', 'ol', 'p', 'p'], 'na ordem da especificação');
  /* o texto inteiro, de uma vez: nenhuma palavra a mais */
  assert.equal(textoDe(caixa), esperado.map(semNumero).join(' '));
  /* "Ver a ficha da Anthropic na Régua." leva à ficha */
  const link = caixa.querySelector('a');
  assert.equal(textoDe(link), 'Ver a ficha da Anthropic na Régua.');
  assert.equal(link.getAttribute('href'), '#/regua/players/anthropic');
  assert.equal(caixa.querySelectorAll('a').length, 1);
  await m.clica(link);
  assert.equal(textoDe(m.documento.activeElement), 'Anthropic');
  assert.equal(m.um('#player-anthropic button').getAttribute('aria-expanded'), 'true');
});

test('Método 01: abaixo da caixa, a lista que liga a marca, lida da régua: a regra, os players com link e os termos', async () => {
  const m = await abreMetodo();
  const quadro = m.um('#s-conflito .quadro');
  assert.equal(textoDe(quadro.querySelector('h3')), 'A LISTA QUE LIGA A MARCA');
  const linhas = quadro.querySelectorAll('p');
  assert.equal(textoDe(linhas[0]), CONGELADOS.regua.conflito.regra, 'o texto da regra abre o quadro');
  assert.equal(textoDe(linhas[1]), 'Players: Anthropic, Sam Altman (OpenAI), Google, Meta, Elon Musk');
  assert.deepEqual(linhas[1].querySelectorAll('a').map((a) => a.getAttribute('href')),
    ['#/regua/players/anthropic', '#/regua/players/altman', '#/regua/players/google', '#/regua/players/meta', '#/regua/players/musk']);
  assert.equal(textoDe(linhas[2]), 'Termos: ' + CONGELADOS.regua.conflito.termos.join(', '));
  assert.equal(linhas[2].querySelectorAll('a').length, 0);
  /* player da lista que não está em players.json aparece pelo id, sem link */
  const m2 = await abreMetodo(null, (t) => { t['dados/regua.json'].conflito.players = ['anthropic', 'empresa_fantasma']; t['dados/regua.json'].conflito.termos = []; });
  const doQuadro = m2.todos('#s-conflito .quadro p');
  assert.equal(textoDe(doQuadro[1]), 'Players: Anthropic, empresa_fantasma');
  assert.equal(doQuadro[1].querySelectorAll('a').length, 1);
  assert.equal(textoDe(doQuadro[2]), 'Termos: —');
});

test('Método 02 e 03: as quatro perguntas e a régua, palavra por palavra, com o link para a Régua', async () => {
  const m = await abreMetodo();
  const perguntas = TEXTOS['As quatro perguntas'];
  const secao = m.um('#s-perguntas .secao__corpo');
  assert.equal(textoDe(secao.querySelector('p')), perguntas[0]);
  assert.deepEqual(textos(secao.querySelectorAll('ol > li')), perguntas.slice(1).map(semNumero));
  assert.equal(textoDe(secao), perguntas.map(semNumero).join(' '));

  const regua = m.um('#s-regua .secao__corpo');
  assert.equal(textoDe(regua), TEXTOS['A régua'][0]);
  const link = regua.querySelector('a');
  assert.equal(textoDe(link), 'Veja a Régua.');
  assert.equal(link.getAttribute('href'), '#/regua/partidos');
  await m.clica(link);
  assert.equal(textoDe(m.um('h1')), 'Régua');
});

test('Método 04: o texto fixo e os 5 níveis, com ícone, rótulo, significado e prova mínima', async () => {
  const m = await abreMetodo();
  const secao = m.um('#s-niveis');
  assert.equal(textoDe(secao.querySelector('.prosa')), TEXTOS['Níveis de alerta'][0]);
  const fichas = secao.querySelectorAll('.nivel-ficha');
  assert.equal(fichas.length, 5);
  assert.deepEqual(textos(fichas.map((f) => f.querySelector('.selo .so-leitor'))),
    ['Nível 1 de 5, rotina', 'Nível 2 de 5, atenção', 'Nível 3 de 5, tensão', 'Nível 4 de 5, crise', 'Nível 5 de 5, emergência']);
  assert.deepEqual(fichas.map((f) => f.querySelector('.selo use').getAttribute('href')), ['#i-nivel-1', '#i-nivel-2', '#i-nivel-3', '#i-nivel-4', '#i-nivel-5']);
  assert.deepEqual(fichas.map((f) => f.querySelector('.selo').getAttribute('class')), ['selo nivel-1', 'selo nivel-2', 'selo nivel-3', 'selo nivel-4', 'selo nivel-5']);
  assert.deepEqual(textos(fichas.map((f) => f.querySelector('.selo__rotulo'))), ['ROTINA', 'ATENÇÃO', 'TENSÃO', 'CRISE', 'EMERGÊNCIA']);
  CONGELADOS.regua.niveis_alerta.forEach((nivel, i) => {
    const linhas = textos(fichas[i].querySelectorAll('p'));
    assert.equal(linhas[1], nivel.significado);
    assert.equal(linhas[2], 'prova mínima ' + nivel.prova_minima);
  });
});

test('Método 04: por domínio, a descrição, o canal e a tabela de critérios, com 5 linhas, eventos e gatilhos de preço', async () => {
  const m = await abreMetodo();
  const secao = m.um('#s-niveis');
  assert.deepEqual(textos(secao.querySelectorAll('h3.metodo__dominio')), ['Energia', 'Alimentos', 'Câmbio', 'Cadeias de suprimento', 'Risco de conflito']);
  const tabelas = secao.querySelectorAll('table');
  assert.equal(tabelas.length, 5);
  const dominios = CONGELADOS.regua.dominios;
  const filhos = secao.querySelector('.secao__corpo').children;
  dominios.forEach((dominio, i) => {
    const titulo = secao.querySelectorAll('h3.metodo__dominio')[i];
    const depois = filhos.slice(filhos.indexOf(titulo) + 1, filhos.indexOf(titulo) + 4);
    assert.equal(textoDe(depois[0]), dominio.descricao);
    assert.equal(textoDe(depois[1]), 'como chega ao Brasil ' + dominio.canal);
    assert.equal(depois[2], tabelas[i]);
    const tabela = tabelas[i];
    assert.equal(textoDe(tabela.querySelector('caption')), dominio.nome);
    assert.deepEqual(textos(tabela.querySelectorAll('thead th')), ['Nível', 'eventos', 'gatilhos de preço']);
    tabela.querySelectorAll('thead th').forEach((th) => assert.equal(th.getAttribute('scope'), 'col'));
    const linhas = tabela.querySelectorAll('tbody tr');
    assert.equal(linhas.length, 5, 'uma linha por nível');
    linhas.forEach((tr, n) => {
      const criterio = CONGELADOS.regua.niveis_alerta[n].criterios[dominio.id];
      /* o selo do nível com o código em mono */
      assert.equal(textoDe(tr.children[0].querySelector('.selo .so-leitor')), 'Nível ' + (n + 1) + ' de 5, ' + CONGELADOS.regua.niveis_alerta[n].rotulo.toLowerCase());
      assert.equal(textoDe(tr.children[0].querySelector('.criterio__codigo')), dominio.id + '.' + (n + 1));
      assert.equal(tr.children[0].getAttribute('scope'), 'row');
      /* a lista de eventos, texto por texto */
      assert.deepEqual(textos(tr.children[1].querySelectorAll('li')), criterio.eventos);
      /* a lista de preços: célula sem item leva travessão */
      if (criterio.precos.length) {
        assert.equal(tr.children[2].querySelectorAll('li').length, criterio.precos.length);
      } else {
        assert.equal(textoDe(tr.children[2]), '—');
      }
    });
  });
  /* gatilho de preço: o texto e, abaixo, o indicador, a janela pelo rótulo e a alta mínima */
  const energia2 = tabelas[0].querySelectorAll('tbody tr')[1].children[2];
  assert.equal(textoDe(energia2), 'Petróleo Brent sobe 5% ou mais em 7 dias. brent · em 7 dias · 5% ou mais');
  assert.equal(textoDe(energia2.querySelector('.criterio__detalhe')), 'brent · em 7 dias · 5% ou mais');
  const cambio2 = textos(tabelas[2].querySelectorAll('tbody tr')[1].children[2].querySelectorAll('li'));
  assert.deepEqual(cambio2, ['Dólar em reais sobe 1,5% ou mais no dia. usd_brl · no dia · 1,5% ou mais', 'Dólar em reais sobe 3% ou mais em 7 dias. usd_brl · em 7 dias · 3% ou mais'],
    'a porcentagem sai no padrão brasileiro');
  assert.equal(textoDe(tabelas[3].querySelectorAll('tbody tr')[0].children[2]), '—', 'suprimentos não tem gatilho de preço');
  /* na tela estreita, as células de lista levam o rótulo em cima */
  assert.ok(tabelas[0].querySelector('tbody td').classList.contains('tabela__longa'));
  assert.equal(tabelas[0].querySelector('tbody td').getAttribute('data-rotulo'), 'eventos');
});

test('Método 05: o texto fixo e o catálogo, indicador por indicador, com as fontes de cada número', async () => {
  const m = await abreMetodo();
  const secao = m.um('#s-indicadores');
  assert.equal(textoDe(secao.querySelector('.prosa')), TEXTOS['De onde vem cada número'][0]);
  const itens = secao.querySelectorAll('.catalogo__item');
  const catalogo = CONGELADOS.catalogo;
  assert.equal(itens.length, 12);
  assert.deepEqual(textos(itens.map((i) => i.querySelector('h3'))), catalogo.indicadores.map((i) => i.nome));
  const brent = itens[0];
  assert.equal(textoDe(brent.querySelector('.marcas')), 'US$ por barril Energia alimenta gatilho diária');
  assert.equal(textoDe(brent.querySelector('.catalogo__meta')), 'faixa aceita: de 5 a 400 casas decimais: 2');
  const fontes = brent.querySelectorAll('.catalogo__fonte');
  /* as contagens vêm do catálogo: a cópia congelada do catálogo muda nesta fase (fontes novas) */
  assert.equal(fontes.length, catalogo.indicadores[0].fontes.length);
  assert.equal(textoDe(fontes[0].querySelector('.marcas')), 'Yahoo Finance (abre em nova aba) leitor yahoo_chart');
  assert.equal(fontes[0].querySelector('a').getAttribute('href'), catalogo.indicadores[0].fontes[0].url);
  assert.equal(fontes[0].querySelector('a').getAttribute('rel'), 'noopener noreferrer');
  assert.equal(textoDe(fontes[0].querySelectorAll('p')[1]), catalogo.indicadores[0].fontes[0].nota);
  /* "só contexto", frequência mensal, faixa com casas e casas decimais do catálogo */
  assert.equal(textoDe(itens[1].querySelector('.marcas')), 'US$ por barril Energia só contexto diária');
  assert.equal(textoDe(itens[6].querySelector('.marcas')), 'pontos Alimentos só contexto mensal');
  assert.equal(textoDe(itens[2].querySelector('.catalogo__meta')), 'faixa aceita: de 0,5 a 50 casas decimais: 2');
  assert.equal(textoDe(itens[7].querySelector('.catalogo__meta')), 'faixa aceita: de 2 a 20 casas decimais: 4');
  assert.equal(textoDe(itens[9].querySelector('.catalogo__meta')), 'faixa aceita: de 500 a 15.000 casas decimais: 1');
  /* o fator de conversão só aparece quando existe e não é 1 */
  assert.equal(textoDe(itens[3].querySelector('.catalogo__fonte .marcas')), 'Yahoo Finance (abre em nova aba) leitor yahoo_chart número convertido: × 0,3674371');
  const todasAsFontes = catalogo.indicadores.reduce((lista, i) => lista.concat(i.fontes), []);
  const comFator = todasAsFontes.filter((f) => typeof f.fator === 'number' && f.fator !== 1).length;
  assert.ok(comFator >= 1, 'o catálogo tem fonte com fator');
  assert.equal(m.todos('.catalogo__fonte').filter((f) => /número convertido/.test(textoDe(f))).length, comFator);
  assert.equal(m.todos('.catalogo__fonte').length, todasAsFontes.length);
  assert.equal(m.todos('.catalogo__fonte a.externo').length, todasAsFontes.length);
  /* no fim, a regra e a data do catálogo */
  assert.equal(textoDe(secao.querySelector('.aba__regra')), 'Catálogo dos indicadores e de onde vem cada número. Quem altera é o dono. A rotina só lê. Catálogo atualizado em 23/11/2026.');
  assert.equal(secao.querySelector('.aba__regra time').getAttribute('datetime'), '2026-11-23');
  /* fator igual a 1, indicador sem "casas" e fonte com endereço que não é http */
  const m2 = await abreMetodo(null, (t) => {
    t['dados/indicadores.json'].indicadores[3].fontes.forEach((fonte) => { fonte.fator = 1; });
    delete t['dados/indicadores.json'].indicadores[3].casas;
    t['dados/indicadores.json'].indicadores[0].fontes[0].url = 'javascript:alert(1)';
  });
  assert.equal(/número convertido/.test(textoDe(m2.todos('.catalogo__item')[3])), false);
  assert.match(textoDe(m2.todos('.catalogo__item')[3].querySelector('.catalogo__meta')), /casas decimais: 2$/, 'sem o campo, 2');
  assert.equal(m2.todos('.catalogo__item')[0].querySelectorAll('a').length, CONGELADOS.catalogo.indicadores[0].fontes.length - 1, 'endereço que não é http fica como texto, sem link');
  assert.match(textoDe(m2.todos('.catalogo__item')[0].querySelector('.catalogo__fonte')), /^Yahoo Finance leitor yahoo_chart/);
});

test('Método 06: o texto fixo e os cinco quadros lidos da régua', async () => {
  const m = await abreMetodo();
  const secao = m.um('#s-rotina');
  assert.deepEqual(textos(secao.querySelector('.prosa').children), TEXTOS['Como a edição é feita']);
  const quadros = secao.querySelectorAll('.quadro');
  assert.deepEqual(textos(quadros.map((q) => q.querySelector('h3'))), ['CAMPOS', 'FORÇA', 'EVIDÊNCIA', 'QUANDO UM TIME AVANÇA', 'FONTE PRIMÁRIA']);
  const regua = CONGELADOS.regua;
  /* campos: nome, as siglas dos partidos e a descrição */
  const campos = quadros[0].querySelectorAll('.quadro__linha');
  assert.deepEqual(textos(campos), ['Campo da ordem OG CA ' + regua.campos[0].descricao, 'Campo da contestação SO ER ' + regua.campos[1].descricao]);
  assert.deepEqual(campos[0].querySelectorAll('a').map((a) => a.getAttribute('href')), ['#/regua/partidos/ordem_global', '#/regua/partidos/centro_atlantico']);
  /* força: o número, os pontos, o nome e o que conta */
  assert.deepEqual(textos(quadros[1].querySelectorAll('.quadro__linha')), regua.forcas.map((f) => 'força ' + f.forca + ' de 3 ' + f.nome + ' ' + f.o_que_conta));
  assert.deepEqual(quadros[1].querySelectorAll('.quadro__linha').map((l) => l.querySelectorAll('.forca__ponto--cheio').length), [1, 2, 3]);
  /* evidência: o rótulo do id e o que conta */
  assert.deepEqual(textos(quadros[2].querySelectorAll('.quadro__linha')),
    ['preço', 'tropa', 'contrato', 'lei', 'voto', 'sanção', 'só narrativa'].map((rotulo, i) => rotulo + ' ' + regua.evidencias[i].o_que_conta));
  /* quando um time avança: uma linha por time, com o nome dele, e a nota do que não move */
  assert.deepEqual(textos(quadros[3].querySelectorAll('.quadro__linha')),
    ['Manutenção da ordem ' + regua.times_avanco.manutencao, 'Mudança da ordem ' + regua.times_avanco.mudanca]);
  assert.equal(textoDe(quadros[3].children[quadros[3].children.length - 1]), regua.times_avanco.nao_move);
  /* fonte primária: a regra e as duas listas de sufixos, em mono, como texto */
  const linhas = textos(quadros[4].querySelectorAll('p'));
  assert.deepEqual(linhas, [regua.sites_oficiais.regra, 'Sites oficiais do Brasil: ' + regua.sites_oficiais.brasil.join(', '),
    'Outros sites oficiais: ' + regua.sites_oficiais.outros.join(', ')]);
  assert.equal(quadros[4].querySelectorAll('a').length, 0, 'sufixo de site nunca vira link');
  assert.equal(quadros[4].querySelectorAll('.mono').length, 2);
});

test('Método 07: o aviso fixo, em caixa, e os limites, palavra por palavra', async () => {
  const m = await abreMetodo();
  const corpo = m.um('#s-limites .secao__corpo');
  const aviso = corpo.children[0];
  assert.ok(aviso.classList.contains('aviso'));
  assert.equal(textoDe(aviso), TEXTOS['Limites e correções'][0]);
  assert.equal(textoDe(aviso), 'O INFOCENARIUM não é recomendação de investimento, nem orientação de saúde ou de segurança.');
  assert.equal(aviso.querySelector('use').getAttribute('href'), '#i-aviso');
  assert.equal(textoDe(corpo.children[1]), TEXTOS['Limites e correções'][1]);
  assert.equal(corpo.children.length, 2);
});

test('#/metodo/{seção}: as 7 âncoras rolam até a seção e põem o foco no título dela', async () => {
  for (const secao of ['conflito', 'perguntas', 'regua', 'niveis', 'indicadores', 'rotina', 'limites']) {
    const m = await abreMetodo('#/metodo/' + secao);
    const titulo = m.um('#t-' + secao);
    assert.equal(m.documento.activeElement, titulo, secao);
    assert.equal(titulo.getAttribute('tabindex'), '-1');
    assert.deepEqual(m.documento.rolagens, [titulo], secao);
    assert.equal(m.um('#s-' + secao).contains(titulo), true);
    assert.equal(m.janela.location.hash, '#/metodo/' + secao);
    assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
    assert.equal(m.todos('main h2').length, 7, 'a vista vem inteira');
  }
  /* sem seção no endereço: na primeira carga o foco não é tomado; depois, vai para o título da vista */
  const m = await abreMetodo('#/metodo');
  assert.equal(m.documento.activeElement, m.documento.body);
  assert.deepEqual(m.documento.rolagens, []);
  await m.vai('#/metodo/limites');
  assert.equal(m.documento.activeElement, m.um('#t-limites'));
  await m.vai('#/metodo');
  assert.equal(m.documento.activeElement, m.um('h1'));
  /* seção que não existe é "qualquer outra" rota */
  const m2 = await abreMetodo('#/metodo/segredo');
  assert.equal(textoDe(m2.um('#avisos-gerais .aviso')), 'ENDEREÇO NÃO ENCONTRADO Mostrando o Painel.');
});

test('do Painel para o Método: o código do gatilho, o aviso de conflito do item e o rodapé chegam à seção certa', async () => {
  const m = await abre({ arquivos: arquivosDe35Dias() });
  await m.clica(m.um('#dominio-energia button'));
  await m.clica(m.um('#dominio-energia .gatilho__criterio'));
  assert.equal(m.janela.location.hash, '#/metodo/niveis');
  assert.equal(m.documento.activeElement, m.um('#t-niveis'));
  await m.vai('#/');
  await m.clica(m.um('#item-p2 .principal__pe button'));
  await m.clica(m.um('#item-p2 .dossie .aviso a'));
  assert.equal(m.documento.activeElement, m.um('#t-conflito'));
  await m.vai('#/');
  await m.clica(m.um('footer a[href^="#/metodo"]'));
  assert.equal(m.documento.activeElement, m.um('#t-conflito'));
  assert.equal(m.todos('#rodape-edicao a').length, 0, 'fora da edição, o rodapé não leva os links de texto e JSON');
});

test('Método sem regua.json: os textos fixos ficam de pé, com o aviso onde a régua faria falta', async () => {
  const m = await abreMetodo('#/metodo/niveis', (t) => { delete t['dados/regua.json']; });
  assert.equal(m.todos('main h2').length, 7);
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
  assert.equal(m.documento.activeElement, m.um('#t-niveis'));
  /* a caixa de conflito não depende de dado nenhum */
  assert.equal(textoDe(m.um('#s-conflito .caixa')), TEXTOS['Aviso de conflito de interesse'].map(semNumero).join(' '));
  const aviso = 'RÉGUA INDISPONÍVEL Nomes e rótulos aparecem como identificadores.';
  assert.deepEqual(textos(m.todos('#s-conflito .avisos .aviso')), [aviso]);
  assert.deepEqual(textos(m.todos('#s-niveis .avisos .aviso')), [aviso]);
  assert.deepEqual(textos(m.todos('#s-rotina .avisos .aviso')), [aviso]);
  assert.equal(m.todos('#s-indicadores .avisos').length, 0, 'o catálogo chegou');
  assert.equal(textoDe(m.um('#s-conflito .quadro')), 'A LISTA QUE LIGA A MARCA —');
  assert.equal(textoDe(m.um('#s-niveis .prosa')), TEXTOS['Níveis de alerta'][0]);
  assert.equal(m.todos('#s-niveis table, #s-niveis .nivel-ficha').length, 0);
  assert.deepEqual(textos(m.todos('#s-rotina .quadro')), ['CAMPOS —', 'FORÇA —', 'EVIDÊNCIA —', 'QUANDO UM TIME AVANÇA —',
    'FONTE PRIMÁRIA Sites oficiais do Brasil: — Outros sites oficiais: —']);
  /* o catálogo segue inteiro; o domínio que a régua nomearia aparece pelo id */
  assert.equal(m.todos('.catalogo__item').length, 12);
  assert.equal(textoDe(m.um('.catalogo__item .marcas')), 'US$ por barril energia alimenta gatilho diária');
  assert.equal(textoDe(m.um('#s-limites .aviso')), 'O INFOCENARIUM não é recomendação de investimento, nem orientação de saúde ou de segurança.');
});

test('Método sem o catálogo e sem os players: o aviso diz o arquivo, e o resto fica de pé', async () => {
  let m = await abreMetodo('#/metodo/indicadores', (t) => { delete t['dados/indicadores.json']; });
  assert.deepEqual(textos(m.todos('#s-indicadores .avisos .aviso')),
    ['DADOS DE APOIO INDISPONÍVEIS Não deu para carregar dados/indicadores.json. Alguns nomes aparecem como identificadores.']);
  assert.equal(textoDe(m.um('#s-indicadores .prosa')), TEXTOS['De onde vem cada número'][0]);
  assert.equal(m.todos('.catalogo__item').length, 0);
  assert.equal(m.um('#s-indicadores .aba__regra'), null);
  assert.equal(m.todos('#s-niveis table').length, 5);
  assert.equal(m.documento.activeElement, m.um('#t-indicadores'));

  m = await abreMetodo('#/metodo', (t) => { delete t['dados/players.json']; });
  assert.deepEqual(textos(m.todos('#s-conflito .avisos .aviso')),
    ['DADOS DE APOIO INDISPONÍVEIS Não deu para carregar dados/players.json. Alguns nomes aparecem como identificadores.']);
  assert.equal(textoDe(m.todos('#s-conflito .quadro p')[1]), 'Players: anthropic, altman, google, meta, musk');
  assert.equal(m.todos('#s-conflito a').length, 0, 'sem o arquivo de players, nenhuma ficha vira link');
  assert.match(textoDe(m.um('#s-conflito .caixa')), /Ver a ficha da Anthropic na Régua\.$/);
});

test('Método e o índice: lista vazia e índice que não carrega; nos dois o Método funciona, sem aviso', async () => {
  const vazio = arquivos();
  vazio['edicoes/indice.json'] = { versao: 1, edicoes: [] };
  for (const tabela of [vazio, arquivos({ sem: ['edicoes/indice.json'] })]) {
    const m = await abre({ hash: '#/metodo/conflito', arquivos: tabela });
    assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
    assert.equal(m.todos('main h2').length, 7);
    assert.equal(m.todos('.catalogo__item').length, 12);
    assert.equal(m.todos('#s-niveis table').length, 5);
    assert.equal(m.documento.activeElement, m.um('#t-conflito'));
    assert.equal(m.um('#vista').hasAttribute('aria-busy'), false);
  }
});

test('Método: arquivo de formato novo leva o aviso na seção que o usa; dados tortos não derrubam a vista', async () => {
  let m = await abreMetodo('#/metodo', (t) => { t['dados/indicadores.json'].versao = 2; });
  assert.deepEqual(textos(m.todos('#s-indicadores .avisos .aviso')), ['FORMATO NOVO O arquivo dados/indicadores.json usa um formato mais novo que o site.']);
  assert.equal(m.todos('.catalogo__item').length, 12);

  m = await abreMetodo('#/metodo', (t) => {
    const regua = t['dados/regua.json'];
    regua.niveis_alerta.push(null, 'x', { nivel: 'alto', criterios: 'nenhum' }, { nivel: 9, criterios: { energia: { eventos: 'a', precos: [null, 7, {}, { alta_minima_pct: 'muito' }] } } });
    regua.dominios.push(null, { id: 5 });
    regua.conflito = { players: 'todos', termos: [1, null, 'Claude'] };
    regua.campos = [null, { partidos: 'x' }, { nome: {}, partidos: [null, 'ordem_global', 'fantasma'] }];
    regua.forcas = [null, {}, { forca: 'muita' }];
    regua.evidencias = [null, { id: {} }, { id: 'toString' }];
    regua.times_avanco = { manutencao: 5, mudanca: 'Texto.', nao_move: {} };
    regua.sites_oficiais = { brasil: 'gov.br', outros: [null, 7, 'gov'] };
    t['dados/indicadores.json'].indicadores.push(null, 'x', {}, { id: 'torto', nome: {}, faixa: 'larga', casas: 'muitas', fontes: [null, {}, { url: 5, fator: 'dois', leitor: {} }], obrigatorio: 'sim' });
    t['dados/indicadores.json'].atualizado_em = 5;
  });
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
  assert.equal(m.todos('main h2').length, 7);
  assert.equal(/undefined|NaN|\[object|function /.test(textoDe(m.um('main'))), false, 'vazou algo que não é dado');
  assert.equal(m.todos('.catalogo__item').length, 14);
  assert.equal(textoDe(m.todos('#s-conflito .quadro p')[1]), 'Termos: Claude');
});

test('Método: enquanto os arquivos não chegam, aria-busy e um travessão; depois de 8 segundos, "Está demorando"', async () => {
  const m = await abre({ hash: '#/metodo/limites', arquivos: arquivosDe35Dias(), segura: true, esperar: false });
  await m.assenta();
  assert.equal(textoDe(m.um('h1')), 'Método');
  assert.equal(m.um('#vista').getAttribute('aria-busy'), 'true');
  assert.equal(textoDe(m.um('.vista__corpo')), '—');
  m.relogio.avanca(8000);
  assert.equal(textoDe(m.um('#avisos-gerais .aviso')), 'Está demorando. A conexão pode estar lenta. Tentar de novo');
  m.rede.solta();
  await m.assenta();
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
  assert.equal(m.todos('main h2').length, 7);
  assert.equal(m.documento.activeElement, m.um('#t-limites'), 'a âncora vale quando os dados chegam');
  assert.equal(aVista(m.um('#s-limites')), true);
});
