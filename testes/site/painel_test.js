'use strict';

/* O Painel montado de verdade: o app.js roda no DOM falso, com a edição de
 * exemplo e os dados congelados. Cada seção, de 00 a 09, é conferida pelos
 * textos que a especificação do site manda mostrar. */

const test = require('node:test');
const assert = require('node:assert/strict');
const { abre, arquivos, edicaoReal, entradaSolta, dados, textoDe, aVista, DIA } = require('./apoio.js');

const textos = (lista) => lista.map(textoDe);

/* Uma edição de verdade (a de exemplo, sem as marcas) com 30 dias de índice
   em volta: é o Painel como o leitor vai ver. */
function comHistorico(mudancas) {
  const edicao = edicaoReal(DIA, mudancas);
  const tabela = arquivos({
    edicoes: [edicao],
    entradas: [
      entradaSolta('2026-11-18', { nivel: 2, niveis: { energia: 1, alimentos: 1, cambio: 2, suprimentos: 1, conflito: 1 }, saldos: { ordem_global: 3, soberanistas: -1 } }),
      entradaSolta('2026-11-17', { estado: 'falha', nivel: 2, niveis: { energia: 1, alimentos: 1, cambio: 2, suprimentos: 1, conflito: 1 } }),
      entradaSolta('2026-11-16', { nivel: 2, niveis: { energia: 1, alimentos: 1, cambio: 2, suprimentos: 1, conflito: 1 } }),
      entradaSolta('2026-11-15', { exemplo: true, nivel: 5, saldos: { ordem_global: 50 } }),
      entradaSolta('2026-11-10', { nivel: 1, saldos: { ordem_global: 2 } }),
      entradaSolta('2026-10-21', { nivel: 1, saldos: { centrao: 1 } }),
      entradaSolta('2026-10-20', { nivel: 4, saldos: { ordem_global: 100 } })
    ]
  });
  /* um vetor igual, 9 dias antes: o de hoje é a segunda vez em 30 dias */
  tabela['dados/vetores.json'].vetores.push({
    id: '2026-11-10_p2_ue', data: '2026-11-10', item: 'p2', player: 'ue', de: 'centro_atlantico', para: 'soberanistas',
    forca: 1, tema: 'imigracao', porque: 'Vetor de teste.', url: 'https://exemplo.invalid/teste/vetor-antigo'
  });
  return tabela;
}

test('00 carimbo: edição gerada em outro dia de Brasília leva o dia antes da hora, no carimbo e no Arquivo', async () => {
  /* a 1ª edição real: de 23/11, republicada em 24/11 às 11h38 de Brasília */
  const edicao = edicaoReal('2026-11-23', (e) => { e.gerada_em = '2026-11-24T14:38:00Z'; });
  const agora = Date.UTC(2026, 10, 24, 22, 0, 0);
  const m = await abre({ agora, arquivos: arquivos({ edicoes: [edicao] }) });
  assert.match(textoDe(m.um('.carimbo__texto')), /^ED\. 23\/11\/2026 · GERADA 24\/11 11h38 \(BRASÍLIA\) · HÁ 7 H$/);
  const a = await abre({ agora, hash: '#/arquivo', arquivos: arquivos({ edicoes: [edicao] }) });
  assert.equal(textoDe(a.um('.edicao__hora')), '24/11 11h38');
  /* no mesmo dia de Brasília, só a hora (às 2h30 UTC do dia 20 ainda é dia 19) */
  const tarde = await abre({ arquivos: arquivos({ edicoes: [edicaoReal(DIA, (e) => { e.gerada_em = '2026-11-20T02:30:00Z'; })] }),
    agora: Date.UTC(2026, 10, 20, 2, 48, 0) });
  assert.match(textoDe(tarde.um('.carimbo__texto')), /GERADA 23h30 \(BRASÍLIA\)/);
});

test('00 carimbo: data, hora de Brasília, idade, placa, links e título da aba', async () => {
  const m = await abre({ arquivos: comHistorico() });
  assert.equal(m.documento.title, 'INFOCENARIUM · 19/11/2026 · nível 3 TENSÃO');
  const h1 = m.todos('h1');
  assert.equal(h1.length, 1, 'um h1 por vista');
  assert.equal(textoDe(h1[0]), 'Edição de 19/11/2026');
  assert.ok(h1[0].classList.contains('so-leitor'), 'o h1 da edição fica fora da vista');
  assert.equal(textoDe(m.um('.carimbo__texto')), 'ED. 19/11/2026 · GERADA 18h14 (BRASÍLIA) · HÁ 18 MIN');
  assert.deepEqual(m.todos('.carimbo time').map((t) => t.getAttribute('datetime')), ['2026-11-19', '2026-11-19T21:14:03Z']);
  assert.deepEqual(textos(m.todos('#carimbo .placa')), ['EM DIA']);
  assert.equal(m.um('#carimbo .placa').classList.contains('placa--grave'), false);
  assert.equal(m.um('#vista').hasAttribute('aria-busy'), false);
  assert.equal(m.um('nav a[aria-current="page"]').textContent, 'Painel');
  assert.equal(m.todos('nav a[aria-current]').length, 1);

  const acoes = m.todos('.cabeca__acoes a');
  assert.deepEqual(acoes.map((a) => a.getAttribute('href')),
    ['#/edicao/2026-11-18', 'edicoes/2026-11-19.md', 'edicoes/2026-11-19.json', 'feed.xml']);
  assert.equal(textoDe(acoes[0].querySelector('.so-leitor')), 'Edição anterior, de 18/11/2026');
  assert.equal(textoDe(acoes[0].querySelector('[aria-hidden="true"]')), '18/11');
  assert.deepEqual(textos(acoes.slice(1)), ['texto', 'JSON', 'feed']);
  assert.deepEqual(m.todos('#rodape-edicao a').map((a) => a.getAttribute('href')), ['edicoes/2026-11-19.md', 'edicoes/2026-11-19.json']);
  assert.equal(textoDe(m.um('.cabeca-impressao')), 'INFOCENARIUM · edição de 19/11/2026 · nível 3 TENSÃO');
  assert.equal(textoDe(m.um('#anuncio')), 'Edição de 19/11/2026.');
});

test('00 avisos: a errata abre e fecha, com cada correção e a fonte', async () => {
  const m = await abre({ arquivos: comHistorico() });
  const avisos = m.todos('#avisos-edicao .aviso');
  assert.deepEqual(textos(m.todos('#avisos-edicao .aviso__rotulo')), ['ERRATA']);
  const errata = avisos[0];
  assert.equal(textoDe(errata.querySelector('.aviso__texto')), 'Esta edição corrige 2 pontos de edições anteriores.');
  const abreErrata = errata.querySelector('button');
  const corpo = errata.querySelector('.aviso__corpo');
  assert.equal(abreErrata.getAttribute('aria-expanded'), 'false');
  assert.equal(abreErrata.getAttribute('aria-controls'), corpo.getAttribute('id'));
  assert.equal(aVista(corpo), false);
  await m.clica(abreErrata);
  assert.equal(abreErrata.getAttribute('aria-expanded'), 'true');
  assert.equal(aVista(corpo), true);
  const itens = corpo.querySelectorAll('.errata__item');
  assert.equal(itens.length, 2);
  assert.equal(textoDe(itens[0].querySelector('.errata__onde')), 'Edição de 18/11/2026, item r3.');
  assert.equal(itens[0].querySelector('.errata__onde a').getAttribute('href'), '#/edicao/2026-11-18/r3');
  assert.match(textoDe(itens[0]), /Estava errado: Texto fictício\. A edição de 18\/11 disse que a consulta pública/);
  assert.match(textoDe(itens[0]), /O certo: Texto fictício\. A consulta dura 30 dias\./);
  const fonte = itens[0].querySelector('a.externo');
  assert.equal(fonte.getAttribute('href'), 'https://exemplo.invalid/outro/consulta-de-rotulos-prazo');
  assert.match(textoDe(fonte), /^Fonte da correção\./);
  /* o vetor citado não está no registro: o id cru, sem link */
  assert.match(textoDe(itens[1]), /Esta correção anula o vetor 2026-11-17_p3_ue\./);
  assert.equal(itens[1].querySelectorAll('a[href^="#/regua/vetores"]').length, 0);
});

test('01 hoje: nível, tendência, comparação com a edição anterior, frase e motivo', async () => {
  const m = await abre({ arquivos: comHistorico() });
  const hoje = m.um('#s-hoje');
  assert.equal(textoDe(hoje.querySelector('h2')), '01 HOJE');
  const bloco = hoje.querySelector('.alerta');
  assert.ok(bloco.classList.contains('nivel-3'));
  assert.equal(textoDe(bloco.querySelector('.alerta__numeral')), '3');
  assert.equal(textoDe(bloco.querySelector('.alerta__de')), 'de 5');
  assert.equal(textoDe(bloco.querySelector('.alerta__rotulo')), 'TENSÃO subindo');
  assert.equal(bloco.querySelector('.alerta__rotulo use').getAttribute('href'), '#i-nivel-3');
  assert.equal(bloco.querySelector('.tendencia use').getAttribute('href'), '#i-sobe');
  assert.equal(textoDe(bloco.querySelector('p.so-leitor')), 'Nível 3 de 5, tensão, subindo');
  assert.equal(bloco.querySelector('.alerta__topo').getAttribute('aria-hidden'), 'true');
  /* um numeral gigante só, e o medidor de 5 segmentos com 3 acesos */
  assert.equal(m.todos('.alerta__numeral').length, 1);
  const medidor = bloco.querySelector('.medidor--grande');
  assert.equal(medidor.getAttribute('aria-hidden'), 'true');
  assert.equal(medidor.querySelectorAll('.medidor__seg').length, 5);
  assert.equal(medidor.querySelectorAll('.medidor__seg--aceso').length, 3);

  const linhas = textos(bloco.querySelectorAll('.alerta__linha').filter(aVista));
  assert.deepEqual(linhas, [
    'antes (18/11): 2 ATENÇÃO',
    'Desde 18/11: energia 1 para 3 · cadeias de suprimento 1 para 2 · risco de conflito 1 para 3'
  ]);
  assert.equal(bloco.querySelectorAll('.alerta__linha use[href="#i-estavel"]').length, 3, 'a seta é desenho, não caractere');
  assert.equal(textoDe(bloco.querySelector('.alerta__resumo')),
    'Edição fictícia: um ataque inventado a um terminal de petróleo leva energia e risco de conflito ao nível 3.');
  assert.match(textoDe(bloco.querySelector('.alerta__motivo')), /^Motivo: Texto fictício\. Nível 3 por um ataque de 19\/11/);
  assert.match(textoDe(bloco.querySelector('.alerta__significado')), /^Houve fato consumado/);
});

test('01 hoje: a fita de 30 dias, com a tabela gêmea', async () => {
  const m = await abre({ arquivos: comHistorico() });
  const historico = m.um('#s-hoje .historico');
  assert.equal(textoDe(historico.querySelector('h3')), 'ALERTA, 30 DIAS');
  const fita = historico.querySelector('.fita');
  assert.equal(fita.getAttribute('role'), 'img');
  assert.equal(fita.getAttribute('aria-label'), 'Alerta nos últimos 30 dias: de 1 a 3; hoje, 3');
  const dias = fita.querySelectorAll('.fita__dia');
  assert.equal(dias.length, 30, 'um espaço por dia');
  assert.equal(fita.querySelectorAll('.fita__fio').length, 5, '5 fios de grade');
  /* só as 6 entradas dos 30 dias viram coluna: fora ficam a de exemplo e a de 20/10 */
  const comColuna = dias.filter((d) => d.querySelector('.fita__coluna'));
  assert.deepEqual(comColuna.map((d) => d.getAttribute('href')), ['#/edicao/2026-10-21', '#/edicao/2026-11-10',
    '#/edicao/2026-11-16', '#/edicao/2026-11-17', '#/edicao/2026-11-18', '#/edicao/2026-11-19']);
  assert.deepEqual(comColuna.map((d) => d.querySelector('.fita__coluna').getAttribute('class').replace('fita__coluna ', '')),
    ['fita__coluna--n1', 'fita__coluna--n1', 'fita__coluna--n2', 'fita__coluna--falha', 'fita__coluna--n2', 'fita__coluna--n3 fita__coluna--atual']);
  assert.equal(dias[0].getAttribute('href'), '#/edicao/2026-10-21', 'o primeiro espaço é o dia 21/10');
  assert.equal(dias[29].getAttribute('href'), '#/edicao/2026-11-19', 'o último é a edição em tela');
  comColuna.forEach((d) => { assert.equal(d.getAttribute('tabindex'), '-1'); assert.equal(d.getAttribute('aria-hidden'), 'true'); });
  assert.equal(textoDe(fita.querySelector('.fita__datas')), '21/10 19/11');
  assert.equal(fita.querySelectorAll('[class*="alerta"]').length, 0, 'a fita não leva cor de nível');

  const abreTabela = historico.querySelector('button');
  const tabela = historico.querySelector('table');
  assert.equal(textoDe(abreTabela), 'Ver tabela');
  assert.equal(abreTabela.getAttribute('aria-expanded'), 'false');
  assert.equal(aVista(tabela), false);
  await m.clica(abreTabela);
  assert.equal(textoDe(abreTabela), 'Esconder tabela');
  assert.equal(aVista(tabela), true);
  assert.equal(textoDe(tabela.querySelector('caption')), 'ALERTA, 30 DIAS');
  assert.deepEqual(textos(tabela.querySelectorAll('thead th')), ['Data', 'Nível', 'Estado']);
  tabela.querySelectorAll('thead th').forEach((th) => assert.equal(th.getAttribute('scope'), 'col'));
  const linhas = tabela.querySelectorAll('tbody tr');
  assert.deepEqual(linhas.map((tr) => textos(tr.children).join(' | ')), [
    '19/11/2026 | 3 TENSÃO | completa', '18/11/2026 | 2 ATENÇÃO | completa', '17/11/2026 | 2 ATENÇÃO | sem edição',
    '16/11/2026 | 2 ATENÇÃO | completa', '10/11/2026 | 1 ROTINA | completa', '21/10/2026 | 1 ROTINA | completa'
  ]);
  assert.equal(linhas[1].querySelector('th').getAttribute('scope'), 'row');
  assert.equal(linhas[1].querySelector('th a').getAttribute('href'), '#/edicao/2026-11-18');
  assert.equal(linhas[1].querySelector('time').getAttribute('datetime'), '2026-11-18');
  assert.equal(linhas[1].children[1].getAttribute('data-rotulo'), 'Nível');
  /* os papéis vão escritos: na tela estreita o CSS muda o display das linhas */
  assert.equal(tabela.getAttribute('role'), 'table');
  assert.deepEqual(linhas[1].children.map((c) => c.getAttribute('role')), ['rowheader', 'cell', 'cell']);
  assert.equal(linhas[1].getAttribute('role'), 'row');
  tabela.querySelectorAll('thead th').forEach((th) => assert.equal(th.getAttribute('role'), 'columnheader'));
});

test('02 domínios: cinco linhas na ordem da régua, com selo, medidor e leitura', async () => {
  const m = await abre({ arquivos: comHistorico() });
  const secao = m.um('#s-dominios');
  assert.equal(textoDe(secao.querySelector('h2')), '02 DOMÍNIOS');
  const linhas = secao.querySelectorAll('.dominio');
  assert.deepEqual(linhas.map((l) => l.getAttribute('id')),
    ['dominio-energia', 'dominio-alimentos', 'dominio-cambio', 'dominio-suprimentos', 'dominio-conflito']);
  assert.deepEqual(textos(linhas.map((l) => l.querySelector('h3'))),
    ['Energia', 'Alimentos', 'Câmbio', 'Cadeias de suprimento', 'Risco de conflito']);
  assert.deepEqual(textos(linhas.map((l) => l.querySelector('.selo .so-leitor'))), [
    'Nível 3 de 5, tensão, subindo', 'Nível 1 de 5, rotina, estável', 'Nível 2 de 5, atenção, estável',
    'Nível 2 de 5, atenção, subindo', 'Nível 3 de 5, tensão, subindo'
  ]);
  assert.deepEqual(linhas.map((l) => l.querySelector('.selo use').getAttribute('href')),
    ['#i-nivel-3', '#i-nivel-1', '#i-nivel-2', '#i-nivel-2', '#i-nivel-3']);
  assert.deepEqual(textos(linhas.map((l) => l.querySelector('.selo__rotulo'))), ['TENSÃO', 'ROTINA', 'ATENÇÃO', 'ATENÇÃO', 'TENSÃO']);
  assert.deepEqual(linhas.map((l) => l.querySelectorAll('.medidor__seg--aceso').length), [3, 1, 2, 2, 3]);
  linhas.forEach((l) => assert.equal(l.querySelector('.medidor').getAttribute('aria-hidden'), 'true'));
  /* "era N" só onde o nível mudou desde a edição anterior */
  assert.deepEqual(textos(linhas.map((l) => l.querySelector('.dominio__tendencia'))),
    ['subindo · era 1', 'estável', 'estável', 'subindo · era 1', 'subindo · era 1']);
  assert.equal(textoDe(linhas[1].querySelector('.dominio__sem-preco')), 'sem dado de preço de: Milho');
  assert.equal(linhas[0].querySelector('.dominio__sem-preco'), null);
  assert.match(textoDe(linhas[2].querySelector('.dominio__leitura')), /^MANTIDO DESDE 17\/11 Texto fictício\. Em 17\/11 o dólar subiu 1,8% no dia\./);
  assert.match(textoDe(linhas[0].querySelector('.dominio__leitura')), /^Texto fictício\. Petróleo mais caro lá fora/);
});

test('01 e 02: na primeira edição (sem anterior), o "estável" que ninguém mediu não aparece, nem na fala do selo', async () => {
  const primeira = edicaoReal(DIA, (e) => {
    e.alerta.tendencia = 'estavel';
    e.alerta.dominios.forEach((d) => { d.tendencia = 'estavel'; });
  });
  const m = await abre({ arquivos: arquivos({ edicoes: [primeira] }) });
  const bloco = m.um('#s-hoje .alerta');
  assert.equal(textoDe(bloco.querySelector('.alerta__rotulo')), 'TENSÃO');
  assert.equal(bloco.querySelector('.tendencia'), null);
  assert.equal(textoDe(bloco.querySelector('p.so-leitor')), 'Nível 3 de 5, tensão');
  assert.ok(textos(bloco.querySelectorAll('.alerta__linha')).includes('Primeira edição: sem comparação.'));
  const linhas = m.todos('#s-dominios .dominio');
  assert.deepEqual(textos(linhas.map((l) => l.querySelector('.dominio__tendencia'))), ['', '', '', '', '']);
  assert.deepEqual(textos(linhas.map((l) => l.querySelector('.selo .so-leitor'))).slice(0, 2),
    ['Nível 3 de 5, tensão', 'Nível 1 de 5, rotina']);
  /* com edição anterior, o mesmo "estável" foi medido e aparece */
  const ontem = edicaoReal('2026-11-18');
  const m2 = await abre({ arquivos: arquivos({ edicoes: [ontem, primeira] }) });
  assert.equal(textoDe(m2.um('#s-hoje .alerta__rotulo')), 'TENSÃO estável');
  assert.equal(textoDe(m2.um('#s-hoje .alerta p.so-leitor')), 'Nível 3 de 5, tensão, estável');
  assert.match(textoDe(m2.um('#dominio-alimentos .dominio__tendencia')), /^estável/);
});

test('02 domínios: a linha abre com descrição, canal, gatilhos e próximo sinal', async () => {
  const m = await abre({ arquivos: comHistorico() });
  const energia = m.um('#dominio-energia');
  const abreLinha = energia.querySelector('button');
  const corpo = energia.querySelector('.dominio__corpo');
  assert.equal(textoDe(abreLinha), 'Abrir: Energia');
  assert.equal(abreLinha.getAttribute('aria-expanded'), 'false');
  assert.equal(abreLinha.getAttribute('aria-controls'), corpo.getAttribute('id'));
  assert.equal(aVista(corpo), false);
  await m.clica(abreLinha);
  assert.equal(textoDe(abreLinha), 'Fechar: Energia');
  assert.equal(abreLinha.getAttribute('aria-expanded'), 'true');
  assert.equal(aVista(corpo), true);
  assert.equal(energia.classList.contains('dominio--fechado'), false);
  assert.deepEqual(textos(corpo.querySelectorAll('h4')), ['COMO CHEGA AO BRASIL', 'GATILHOS DE HOJE', 'PRÓXIMO SINAL']);
  const paragrafos = textos(corpo.querySelectorAll('p'));
  assert.match(paragrafos[0], /^Petróleo, gás, combustíveis e eletricidade: preço e risco de falta\./);
  assert.match(paragrafos[1], /^Petróleo mais caro lá fora encarece o diesel e a gasolina importados\./);
  assert.equal(paragrafos[2], 'Neste nível desde 19/11/2026.');
  assert.equal(paragrafos[3], 'O Brent passa de 10% de alta em 7 dias?');

  const gatilhos = corpo.querySelectorAll('.gatilho');
  assert.equal(gatilhos.length, 2);
  const criterio = gatilhos[0].querySelector('.gatilho__criterio');
  assert.equal(textoDe(criterio), 'energia.2');
  assert.equal(criterio.getAttribute('href'), '#/metodo/niveis');
  assert.match(textoDe(gatilhos[0].querySelector('.gatilho__texto')), /Petróleo Brent subiu 6,1% em 7 dias/);
  assert.equal(textoDe(gatilhos[0].querySelector('.gatilho__ref')), 'ver indicador: Petróleo Brent');
  assert.equal(gatilhos[0].querySelector('.gatilho__ref a').getAttribute('href'), '#/edicao/2026-11-19/brent');
  assert.equal(textoDe(gatilhos[1].querySelector('.gatilho__ref')), 'ver principal 1');
  assert.equal(gatilhos[1].querySelector('.gatilho__ref a').getAttribute('href'), '#/edicao/2026-11-19/p1');

  /* suprimentos: gatilho de exceção, com a dica também no nome acessível */
  const suprimentos = m.um('#dominio-suprimentos');
  const excecao = suprimentos.querySelector('.gatilho .etiqueta');
  assert.equal(textoDe(excecao.querySelector('.so-leitor')), ': Fato fora da tabela de critérios, tratado como equivalente a este nível.');
  assert.equal(excecao.childNodes[0].textContent, 'EXCEÇÃO');
  assert.equal(excecao.getAttribute('tabindex'), '0');
  assert.equal(excecao.querySelector('.dica').getAttribute('aria-hidden'), 'true');
  assert.equal(textoDe(suprimentos.querySelector('.gatilho__ref')), 'ver radar 4');

  /* alimentos, nível 1 sem gatilho; câmbio, nível mantido */
  assert.match(textoDe(m.um('#dominio-alimentos .dominio__corpo')), /GATILHOS DE HOJE Nenhum gatilho hoje\. PRÓXIMO SINAL/);
  assert.match(textoDe(m.um('#dominio-cambio .dominio__corpo')),
    /GATILHOS DE HOJE MANTIDO DESDE 17\/11 Sem gatilho novo\. O nível desce um degrau depois de 2 edições seguidas sem gatilho\. Edição sem dado de preço não entra nessa conta\./);
});

test('03 indicadores: uma ficha por indicador, com valor, variações, etiquetas e fonte', async () => {
  const m = await abre({ arquivos: comHistorico() });
  const secao = m.um('#s-indicadores');
  assert.equal(textoDe(secao.querySelector('h2')), '03 INDICADORES');
  const fichas = secao.querySelectorAll('.ficha');
  assert.deepEqual(fichas.map((f) => f.getAttribute('id')), ['ind-brent', 'ind-wti', 'ind-gas_natural', 'ind-trigo', 'ind-milho',
    'ind-soja', 'ind-fao_ffpi', 'ind-usd_brl', 'ind-dxy', 'ind-ouro', 'ind-vix', 'ind-frete_seco']);
  const ficha = (id) => m.um('#ind-' + id);
  const valor = (id) => textoDe(ficha(id).querySelector('.ficha__valor'));
  const variacoes = (id) => textos(ficha(id).querySelectorAll('dd'));

  assert.equal(textoDe(ficha('brent').querySelector('h3')), 'Petróleo Brent');
  assert.equal(valor('brent'), '78,40');
  assert.equal(textoDe(ficha('brent').querySelector('.ficha__unidade')), 'US$ por barril');
  assert.deepEqual(variacoes('brent'), ['+1,3%', '+6,1%']);
  assert.deepEqual(ficha('brent').querySelectorAll('dt').map((dt) => dt.childNodes[0].textContent), ['anterior', '7 dias']);
  assert.equal(textoDe(ficha('brent').querySelector('dt .so-leitor')), ': Variação sobre o ponto anterior da série.');
  /* as casas decimais vêm do catálogo */
  assert.equal(valor('trigo'), '216,9');
  assert.equal(valor('usd_brl'), '5,4321');
  assert.equal(valor('ouro'), '2.650,0');
  assert.equal(valor('frete_seco'), '12,12');
  assert.deepEqual(variacoes('milho'), ['−0,1%', '—'], 'variação nula vira travessão');
  assert.deepEqual(variacoes('frete_seco'), ['−0,7%', '−3,8%']);
  /* sem dado: sem variações e sem carimbo */
  assert.equal(valor('gas_natural'), 'sem dado');
  assert.ok(ficha('gas_natural').querySelector('.ficha__valor--sem'));
  assert.equal(ficha('gas_natural').querySelectorAll('dl').length, 0);
  /* etiquetas do pé */
  const etiquetas = (id) => textos(ficha(id).querySelectorAll('.ficha__pe .etiqueta'));
  assert.deepEqual(etiquetas('brent'), ['GATILHO', 'Energia']);
  assert.deepEqual(etiquetas('wti'), ['Energia']);
  assert.deepEqual(etiquetas('frete_seco'), ['DE 12/11', 'Cadeias de suprimento']);
  assert.deepEqual(etiquetas('gas_natural'), ['Energia'], 'sem valor não leva carimbo de data');
  assert.deepEqual(etiquetas('fao_ffpi'), ['Alimentos']);
  assert.equal(ficha('usd_brl').querySelector('a.etiqueta').getAttribute('href'), '#/edicao/2026-11-19/cambio');
  const fonte = ficha('brent').querySelector('a.externo');
  assert.equal(fonte.getAttribute('href'), 'https://exemplo.invalid/indicadores/brent');
  assert.equal(textoDe(fonte), 'Fonte: Fonte fictícia de exemplo (abre em nova aba)');
  /* sem valor, a fonte é só a prevista no catálogo: o nome, sem link (e sem parada de Tab) */
  assert.equal(ficha('gas_natural').querySelectorAll('a.externo').length, 0);
  assert.match(textoDe(ficha('gas_natural').querySelector('.ficha__pe')), /Fonte prevista: Fonte fictícia de exemplo$/);
  assert.equal(/Fonte: /.test(textoDe(ficha('gas_natural'))), false);
  /* o campo confirmado não aparece */
  assert.equal(/confirmad/i.test(textoDe(secao)), false);
});

test('04 principais: os cartões fechados', async () => {
  const m = await abre({ arquivos: comHistorico() });
  const secao = m.um('#s-principais');
  assert.equal(textoDe(secao.querySelector('h2')), '04 PRINCIPAIS');
  assert.equal(textoDe(secao.querySelector('.nota-secao')), 'Mapa de veículos em rascunho, ainda sem revisão do dono. Ver o mapa.');
  assert.equal(secao.querySelector('.nota-secao a').getAttribute('href'), '#/regua/veiculos');
  const cartoes = secao.querySelectorAll('.principal');
  assert.deepEqual(cartoes.map((c) => c.getAttribute('id')), ['item-p1', 'item-p2', 'item-p3']);
  assert.deepEqual(textos(cartoes.map((c) => c.querySelector('.principal__num'))), ['Principal 1', 'Principal 2', 'Principal 3']);
  assert.deepEqual(textos(cartoes.map((c) => c.querySelector('h3'))), [
    'País fictício ataca terminal de petróleo no Estreito de Exemplo',
    'Lei fictícia obriga registro de modelos avançados de IA',
    'Assembleia fictícia aprova envio de observadores ao Estreito de Exemplo'
  ]);
  const marcas = (i) => textos(cartoes[i].querySelector('.marcas').children);
  assert.deepEqual(marcas(0), ['GEOPOLÍTICA', 'CONFIANÇA ALTA', 'Energia', 'Risco de conflito']);
  assert.deepEqual(marcas(1), ['IA', 'CONFIANÇA MÉDIA', 'CONFLITO DE INTERESSE', 'CONTINUAÇÃO DE 18/11']);
  assert.deepEqual(marcas(2), ['GEOPOLÍTICA', 'CONFIANÇA ALTA', 'Risco de conflito']);
  assert.equal(cartoes[1].querySelector('.marcas a[href^="#/edicao/2026-11-18"]').getAttribute('href'), '#/edicao/2026-11-18/p2');
  assert.equal(cartoes[0].querySelector('.marcas a').getAttribute('href'), '#/edicao/2026-11-19/energia');
  assert.match(textoDe(cartoes[0].querySelector('.principal__fato')), /^Texto fictício\. Em 19\/11, drones da República de Exemplo/);

  const linhas = textos(cartoes[0].querySelectorAll('.principal__linha'));
  assert.equal(linhas[0], 'Atirou: The New York Times OG atira em República de Exemplo · Fox News SO atira em União Europeia · ' +
    'Xinhua (Agência de Notícias Xinhua) ER atira em Reino de Amostra (fictício)');
  assert.equal(linhas[1], 'Placar: ER +2 (ganha) · CA −2 (perde) · SO +1 (ganha) narrativa');
  /* a sigla é etiqueta sem cor, link para a ficha do partido, com o nome em abbr */
  const sigla = cartoes[0].querySelector('.principal__linha .etiqueta--partido');
  assert.equal(sigla.getAttribute('href'), '#/regua/partidos/ordem_global');
  assert.equal(sigla.querySelector('abbr').getAttribute('title'), 'Partido da Ordem Global');

  cartoes.forEach((cartao) => {
    const botao = cartao.querySelector('.principal__pe button');
    assert.match(textoDe(botao), /^Abrir dossiê/);
    assert.equal(botao.getAttribute('aria-expanded'), 'false', 'tudo começa fechado');
    assert.equal(aVista(cartao.querySelector('.dossie')), false);
  });
});

test('04 dossiê: as partes, na ordem, com os textos da edição', async () => {
  const m = await abre({ arquivos: comHistorico() });
  const cartao = m.um('#item-p1');
  const botao = cartao.querySelector('.principal__pe button');
  await m.clica(botao);
  assert.match(textoDe(botao), /^Fechar dossiê/);
  assert.equal(botao.getAttribute('aria-expanded'), 'true');
  const dossie = cartao.querySelector('.dossie');
  assert.equal(aVista(dossie), true);
  assert.equal(aVista(cartao.querySelector('.principal__resumo')), false, 'aberto, o resumo dá lugar ao dossiê');
  assert.deepEqual(textos(dossie.querySelectorAll('h4')), ['O QUE ACONTECEU', 'QUEM ATIROU (3)', 'O QUE ESTÁ REALMENTE ACONTECENDO',
    'NA PRÁTICA', 'O ATO NA RÉGUA', 'QUEM GANHA E QUEM PERDE', 'MOVIMENTOS', 'PARA QUEM SE PREPARA', 'FONTES (6)']);
  const t = textoDe(dossie);
  assert.match(t, /NÃO CONFIRMADO Segundo o governo do Reino de Amostra, os drones partiram de um terceiro país\./);

  /* quem atirou */
  const ataques = dossie.querySelectorAll('.ataque');
  assert.equal(ataques.length, 3);
  assert.equal(textoDe(ataques[0].querySelector('.ataque__cabeca')), 'The New York Times OG atira em República de Exemplo');
  assert.equal(ataques[0].querySelector('.ataque__veiculo').getAttribute('href'), '#/regua/veiculos/nyt');
  assert.equal(ataques[0].querySelector('.etiqueta--partido').getAttribute('href'), '#/regua/partidos/ordem_global');
  assert.equal(ataques[0].querySelectorAll('.ataque__cabeca a').length, 2, 'player novo ainda fora de players.json não vira link');
  assert.equal(ataques[1].querySelectorAll('.ataque__cabeca a')[2].getAttribute('href'), '#/regua/players/ue');
  assert.equal(textoDe(ataques[2].querySelector('.ataque__cabeca')), 'Xinhua (Agência de Notícias Xinhua) ER atira em Reino de Amostra (fictício)');
  assert.equal(ataques[2].querySelectorAll('.ataque__cabeca a').length, 2, 'alvo "outro" é texto simples');
  assert.match(textoDe(ataques[0].querySelector('.ataque__enquadramento')), /^Texto fictício\. Chama o ataque de "agressão"/);
  assert.equal(textoDe(ataques[0].querySelector('.ataque__omite')),
    'Deixou de fora: Texto fictício. Não diz que o terminal já operava com metade da capacidade. Segundo a leitura do INFOCENARIUM em 19/11.');
  assert.equal(ataques[1].querySelector('.ataque__omite'), null);
  const materia = ataques[0].querySelector('.ataque__link a');
  assert.equal(materia.getAttribute('href'), 'https://exemplo.invalid/nyt/terminal-atacado');
  assert.equal(textoDe(materia), 'ler no veículo (abre em nova aba)');

  /* realmente, na prática, eixo */
  assert.match(textoDe(dossie.querySelector('.dossie__realmente')), /^Texto fictício\. As manchetes brigam por um nome/);
  assert.match(t, /NA PRÁTICA Texto fictício\. Terminal parado: 400 mil barris por dia fora do mercado\./);
  const eixo = dossie.querySelector('.eixo');
  assert.equal(textoDe(eixo.querySelector('.so-leitor')), 'Mudanças climáticas: empurra para fósseis livres, minimizar o problema');
  assert.equal(textoDe(eixo.querySelector('[aria-hidden="true"]')), 'Mudanças climáticas CLIMA empurra para: fósseis livres, minimizar o problema');
  assert.match(textoDe(eixo.querySelector('.eixo__porque')), /suspendeu por 90 dias uma meta de corte de emissões/);
  assert.equal(/azul|vermelh/i.test(textoDe(eixo)), false, 'o eixo não escreve o nome dos polos');

  /* quem ganha e quem perde */
  const placar = dossie.querySelectorAll('.placar-item');
  assert.deepEqual(textos(placar.map((p) => p.querySelector('.placar-item__cabeca'))), [
    'ER Eixo Revisionista + ganha força 2 de 3 ato reversível preço',
    'CA Centro Atlântico − perde força 2 de 3 ato reversível preço',
    'SO Soberanistas + ganha força 1 de 3 sinal só narrativa'
  ]);
  assert.deepEqual(placar.map((p) => p.querySelectorAll('.forca__ponto--cheio').length), [2, 2, 1]);
  assert.match(textoDe(placar[0].querySelector('.placar-item__porque')), /^Texto fictício\. Rússia e Irã/);

  /* movimentos do item, preparo e fontes */
  const vetor = dossie.querySelector('.vetor');
  assert.equal(textoDe(vetor.querySelector('.vetor__cabeca')), 'União Europeia CA desloca-se para SO força 2 de 3 ato reversível CLIMA 2ª vez em 30 dias');
  assert.match(t, /PARA QUEM SE PREPARA No Brasil: Texto fictício\. Tende a encarecer o diesel e a gasolina importados/);
  assert.match(t, /Domínios: Energia Risco de conflito Vigiar: PERGUNTA-CHAVE/);
  const perguntas = dossie.querySelectorAll('.lista li.com-dicas');
  assert.equal(perguntas.length, 2);
  assert.equal(perguntas[0].querySelector('.etiqueta').childNodes[0].textContent, 'PERGUNTA-CHAVE');
  assert.equal(textoDe(perguntas[0].querySelector('.so-leitor')), ': É a pergunta que derruba esta leitura. O INFOCENARIUM responde quando a data vencer.');
  assert.equal(perguntas[1].querySelector('.etiqueta'), null);
  assert.match(textoDe(perguntas[1]), /^O terminal fictício volta a embarcar petróleo até 26\/11\?$/);

  const fontes = dossie.querySelectorAll('.fonte');
  assert.equal(fontes.length, 6);
  assert.equal(textoDe(fontes[0]), 'Reuters CE 19/11 Sample Kingdom oil terminal halts loading after drone strike (abre em nova aba)');
  assert.equal(fontes[0].querySelector('[translate="no"]').textContent, 'Sample Kingdom oil terminal halts loading after drone strike');
  /* lang só com um idioma no mapa: Reuters e Xinhua têm vários (inclusive pt); NYT e Fox News só en; fora do mapa, nenhum */
  assert.deepEqual(fontes.map((f) => f.querySelector('[translate="no"]').getAttribute('lang')),
    [null, 'en', 'en', null, null, null]);
  assert.equal(fontes[0].querySelector('time').getAttribute('datetime'), '2026-11-19');
  assert.equal(fontes[0].querySelector('a.externo').getAttribute('href'), 'https://exemplo.invalid/reuters/terminal-para');
  assert.match(textoDe(fontes[4]), /^Comissão Europeia \(sala de imprensa\) CA 19\/11 FONTE PRIMÁRIA/);
  assert.match(textoDe(fontes[5]), /^Diário Oficial da República de Exemplo \(fictício\) FORA DO MAPA 18\/11 FONTE PRIMÁRIA/);
  assert.equal(fontes[5].querySelectorAll('a').length, 1, 'fonte fora do mapa: só o link da matéria');
});

test('04 fontes: lang só com marca de idioma válida; "multi" ou texto torto do mapa não viram lang', async () => {
  const tabela = comHistorico();
  const veiculos = tabela['dados/veiculos.json'].veiculos;
  veiculos.find((v) => v.id === 'nyt').idiomas = ['multi'];
  veiculos.find((v) => v.id === 'fox_news').idiomas = ['en" onclick="x'];
  veiculos.find((v) => v.id === 'reuters').idiomas = ['pt'];
  const m = await abre({ arquivos: tabela });
  const titulos = m.todos('#item-p1 .fonte [translate="no"]');
  assert.deepEqual(titulos.map((t) => t.getAttribute('lang')).slice(0, 3), ['pt', null, null]);
});

test('04 fontes: o partido do veículo é o lado gravado no ataque do mesmo item; sem ataque dele, o do mapa de hoje (fer-07)', async () => {
  const tabela = comHistorico();
  const veiculos = tabela['dados/veiculos.json'].veiculos;
  /* o dono mudou o mapa depois da edição: a NYT (com ataque no p1, lado ordem_global) e a Reuters (sem ataque) */
  veiculos.find((v) => v.id === 'nyt').lado = 'soberanistas';
  veiculos.find((v) => v.id === 'reuters').lado = 'soberanistas';
  const m = await abre({ arquivos: tabela });
  const siglas = m.todos('#item-p1 .fonte').map((f) => {
    const abbr = f.querySelector('.etiqueta--partido abbr');
    return abbr ? abbr.getAttribute('title') : null;
  });
  const nome = (id) => tabela['dados/regua.json'].partidos.find((p) => p.id === id).nome;
  assert.equal(siglas[1], nome('ordem_global'), 'NYT: o lado gravado no ataque');
  assert.equal(siglas[0], nome('soberanistas'), 'Reuters: sem ataque no item, o lado do mapa de hoje');
});

test('05 placar do dia: os 7 partidos, saldo em barra, narrativa à parte, acumulado de 30 dias', async () => {
  const m = await abre({ arquivos: comHistorico() });
  const secao = m.um('#s-placar');
  assert.equal(textoDe(secao.querySelector('h2')), '05 PLACAR DO DIA');
  assert.match(textoDe(secao.querySelector('.secao__intro')), /^Saldo é a soma das forças do dia: ganhar soma, perder subtrai\. Ganho só de narrativa não entra no saldo/);
  const linhas = secao.querySelectorAll('.placar__linha');
  assert.deepEqual(textos(linhas.map((l) => l.querySelector('abbr'))), ['OG', 'IN', 'SO', 'ER', 'CE', 'CA', 'BT']);
  assert.deepEqual(textos(linhas.map((l) => l.querySelector('.placar__saldo'))), ['+4', '+2', '0', '0', '−1', '−2', '−2']);
  assert.deepEqual(textos(linhas.map((l) => l.querySelector('.so-leitor'))), [
    'Partido da Ordem Global: saldo mais 4; na narrativa, mais 1', 'Independentes: saldo mais 2',
    'Soberanistas: saldo zero; na narrativa, mais 2', 'Eixo Revisionista: saldo zero; na narrativa, mais 1',
    'Centrão: saldo menos 1', 'Centro Atlântico: saldo menos 2', 'Bancada do Talento: saldo menos 2'
  ]);
  /* 72 px valem o maior saldo do dia (4); direita ganha, esquerda perde; zero não tem barra */
  const barra = (l) => l.querySelector('.placar__barra');
  assert.deepEqual(linhas.map((l) => (barra(l) ? barra(l).style.width : null)), ['72px', '36px', null, null, '18px', '36px', '36px']);
  assert.deepEqual(linhas.map((l) => (barra(l) ? barra(l).getAttribute('class').replace('placar__barra ', '') : '')),
    ['placar__barra--ganha', 'placar__barra--ganha', '', '', 'placar__barra--perde', 'placar__barra--perde', 'placar__barra--perde']);
  linhas.forEach((l) => assert.equal(l.querySelector('.placar__area').getAttribute('aria-hidden'), 'true'));
  /* narrativa nunca vira barra: é número, na linha de baixo, só quando não é zero */
  assert.deepEqual(textos(linhas.map((l) => l.querySelector('.placar__nota'))), [
    'narrativa +1 · 30 dias +9', '30 dias +2', 'narrativa +2 · 30 dias −1', 'narrativa +1 · 30 dias 0',
    '30 dias 0', '30 dias −2', '30 dias −2'
  ]);
  assert.match(textoDe(linhas[0].querySelector('.placar__frase')), /^Texto fictício\. Ganhou uma votação e uma lei de registro de IA/);
});

test('05 placar do dia: partido fora da lista entra com saldo 0 e "sem movimento hoje"', async () => {
  const m = await abre({ arquivos: comHistorico((edicao) => {
    edicao.placar_do_dia = edicao.placar_do_dia.filter((l) => l.partido !== 'soberanistas' && l.partido !== 'centrao');
  }) });
  const linhas = m.todos('#s-placar .placar__linha');
  assert.deepEqual(textos(linhas.map((l) => l.querySelector('abbr'))), ['OG', 'IN', 'SO', 'ER', 'CE', 'CA', 'BT'],
    'maior saldo primeiro; empate segue a régua');
  assert.equal(textoDe(linhas[2].querySelector('.placar__frase')), 'sem movimento hoje');
  assert.equal(textoDe(linhas[4].querySelector('.placar__frase')), 'sem movimento hoje');
  assert.equal(textoDe(linhas[2].querySelector('.placar__saldo')), '0');
  assert.equal(linhas[2].querySelector('.placar__barra'), null);
});

test('05 placar do dia: a escala tem piso de 3, para um saldo pequeno não encher a barra', async () => {
  const m = await abre({ arquivos: comHistorico((edicao) => {
    edicao.placar_do_dia = [
      { partido: 'ordem_global', saldo: 1, narrativa: 0, frase: 'Ganhou pouco.' },
      { partido: 'centrao', saldo: -2, narrativa: -1, frase: 'Perdeu um pouco mais.' }
    ];
  }) });
  const linhas = m.todos('#s-placar .placar__linha');
  const larguras = linhas.map((l) => (l.querySelector('.placar__barra') ? l.querySelector('.placar__barra').style.width : null));
  assert.deepEqual(larguras.filter(Boolean), ['24px', '48px'], '72 px valeriam 3, e não o maior saldo do dia (2)');
  assert.deepEqual(textos(linhas.map((l) => l.querySelector('abbr'))), ['OG', 'CA', 'BT', 'SO', 'ER', 'IN', 'CE']);
  assert.equal(textoDe(linhas[6].querySelector('.so-leitor')), 'Centrão: saldo menos 2; na narrativa, menos 1');
  assert.equal(textoDe(linhas[6].querySelector('.placar__nota')), 'narrativa −1 · 30 dias −1', '−2 de hoje mais 1 de 21/10');
});

test('04 dossiê: FOGO AMIGO só com veículo de lado firme; LADO INCERTO com lado fraco; fora do mapa, nenhuma das duas', async () => {
  const m = await abre({ arquivos: comHistorico((edicao) => {
    const ataques = edicao.principais[0].ataques;
    ataques[0].alvo = 'oms_onu';                 /* NYT (lado firme) atira num player da Ordem Global */
    ataques[1].alvo = 'soberanistas';            /* Fox News (lado médio) atira no próprio partido */
    ataques[2] = { veiculo: 'reuters', lado: 'centrao', alvo: 'centrao', enquadramento: 'Teste.', url: 'https://exemplo.invalid/t1' };
    ataques.push({ veiculo: 'jornal_que_saiu', lado: 'centrao', alvo: 'centrao', enquadramento: 'Teste.', url: 'https://exemplo.invalid/t2' });
    ataques.push({ veiculo: 'guardian', lado: 'ordem_global', alvo: 'china', enquadramento: 'Teste.', url: 'https://exemplo.invalid/t3' });
  }) });
  const cabecas = textos(m.todos('#item-p1 .dossie .ataque__cabeca'));
  assert.deepEqual(cabecas.slice(0, 4), [
    'The New York Times OG atira em OMS/ONU FOGO AMIGO',
    'Fox News SO atira em Soberanistas FOGO AMIGO',
    'Reuters CE atira em Centrão LADO INCERTO',
    'jornal_que_saiu CE atira em Centrão'
  ]);
  assert.match(cabecas[4], /^The Guardian OG atira em /);
  assert.equal(/FOGO AMIGO|LADO INCERTO/.test(cabecas[4]), false, 'alvo de outro partido não é fogo amigo');
  /* o alvo que é partido leva à ficha do partido; o que é player, à linha do player */
  const links = m.todos('#item-p1 .dossie .ataque__cabeca').map((c) => c.querySelectorAll('a').map((a) => a.getAttribute('href')));
  assert.deepEqual(links[0], ['#/regua/veiculos/nyt', '#/regua/partidos/ordem_global', '#/regua/players/oms_onu']);
  assert.deepEqual(links[1], ['#/regua/veiculos/fox_news', '#/regua/partidos/soberanistas', '#/regua/partidos/soberanistas']);
  assert.deepEqual(links[3], ['#/regua/partidos/centrao', '#/regua/partidos/centrao']);
});

test('06 o que vigiar: sinais com a origem, e respostas às perguntas antigas', async () => {
  const m = await abre({ arquivos: comHistorico() });
  const secao = m.um('#s-vigiar');
  assert.equal(textoDe(secao.querySelector('h2')), '06 O QUE VIGIAR');
  assert.deepEqual(textos(secao.querySelectorAll('h3')), ['SINAIS', 'RESPOSTAS (3)']);
  assert.deepEqual(textos(secao.querySelectorAll('.secao__intro')),
    ['Sinais que mudariam o quadro. Cada pergunta tem data.', 'O INFOCENARIUM responde às próprias perguntas quando a data vence.']);
  const sinais = secao.querySelectorAll('.sinal');
  assert.equal(sinais.length, 10, '5 domínios e 5 perguntas das principais');
  assert.equal(textoDe(sinais[0]), 'Energia: O Brent passa de 10% de alta em 7 dias?');
  assert.equal(sinais[0].querySelector('a').getAttribute('href'), '#/edicao/2026-11-19/energia');
  assert.equal(textoDe(sinais[5]), 'Principal 1: O Reino de Amostra responde com ataque militar até 22/11?');
  assert.equal(sinais[5].querySelector('a').getAttribute('href'), '#/edicao/2026-11-19/p1');
  assert.equal(textoDe(sinais[7]), 'Principal 2: A lei fictícia é sancionada até 30/11?');

  const respostas = secao.querySelectorAll('.resposta');
  assert.deepEqual(textos(respostas.map((r) => r.querySelector('.etiqueta'))), ['SIM', 'NÃO', 'SEM DADO']);
  /* as três etiquetas têm o mesmo desenho: nenhuma classe a mais */
  respostas.forEach((r) => assert.equal(r.querySelector('.etiqueta').getAttribute('class'), 'etiqueta'));
  assert.equal(textoDe(respostas[0].querySelector('.resposta__pergunta')), 'O Reino de Amostra renova as sanções fictícias até 19/11?');
  assert.match(textoDe(respostas[1].querySelector('.resposta__texto')), /^O INFOCENARIUM leu errado em 14\/11/);
  assert.equal(textoDe(respostas[0].querySelector('.resposta__pe')), 'fonte (abre em nova aba) perguntado em 12/11, principal 1');
  assert.equal(respostas[0].querySelector('a.externo').getAttribute('href'), 'https://exemplo.invalid/reuters/sancoes-renovadas');
  assert.equal(respostas[0].querySelectorAll('a').length, 1, 'a edição de 12/11 não está no índice: só o link da fonte');
  /* SEM DADO não traz fonte; a edição de 16/11 está no índice, então a pergunta leva a ela */
  assert.equal(textoDe(respostas[2].querySelector('.resposta__pe')), 'perguntado em 16/11, principal 3');
  assert.deepEqual(respostas[2].querySelectorAll('a').map((a) => a.getAttribute('href')), ['#/edicao/2026-11-16/p3']);
});

test('06 respostas: a pergunta leva à principal que perguntou, quando a edição está no índice', async () => {
  const m = await abre({ arquivos: comHistorico((edicao) => { edicao.respostas[0].edicao = '2026-11-10'; }) });
  const respostas = m.todos('#s-vigiar .resposta');
  assert.equal(respostas[0].querySelector('.resposta__pe a[href^="#"]').getAttribute('href'), '#/edicao/2026-11-10/p1');
  assert.equal(textoDe(respostas[0].querySelector('.resposta__pe a[href^="#"]')), 'perguntado em 10/11, principal 1');
  assert.equal(respostas[1].querySelectorAll('.resposta__pe a[href^="#"]').length, 0, '14/11 não está no índice');
});

test('07 movimentos: vetores de todos os itens e a ficha do player novo', async () => {
  const m = await abre({ arquivos: comHistorico() });
  const secao = m.um('#s-movimentos');
  assert.equal(textoDe(secao.querySelector('h2')), '07 MOVIMENTOS');
  assert.equal(textoDe(secao.querySelector('.secao__intro')), 'Ninguém muda de partido. O vetor mostra para onde o player se desloca.');
  const vetores = secao.querySelectorAll('.vetor');
  assert.deepEqual(textos(vetores.map((v) => v.querySelector('.vetor__cabeca'))), [
    'União Europeia CA desloca-se para SO força 2 de 3 ato reversível CLIMA 2ª vez em 30 dias principal 1',
    'Google BT desloca-se para OG força 2 de 3 ato reversível IA 2 CONFLITO DE INTERESSE radar 2'
  ]);
  assert.equal(vetores[0].querySelector('.vetor__player').getAttribute('href'), '#/regua/players/ue');
  assert.deepEqual(vetores[0].querySelectorAll('.etiqueta--partido').map((a) => a.getAttribute('href')),
    ['#/regua/partidos/centro_atlantico', '#/regua/partidos/soberanistas']);
  const tema = vetores[0].querySelectorAll('.vetor__cabeca abbr').find((abbr) => abbr.textContent === 'CLIMA');
  assert.equal(tema.getAttribute('title'), 'Mudanças climáticas');
  assert.equal(vetores[1].querySelectorAll('.vetor__cabeca a')[3].getAttribute('href'), '#/edicao/2026-11-19/r2');
  assert.match(textoDe(vetores[0].querySelector('.vetor__porque')), /^Texto fictício\. A Comissão Europeia suspendeu por decreto/);
  assert.equal(vetores[0].querySelector('.vetor__link a').getAttribute('href'), 'https://exemplo.invalid/comissao_europeia/decreto-suspende-meta');
  assert.equal(textoDe(vetores[0].querySelector('.vetor__link a')), 'prova (abre em nova aba)');

  const ficha = secao.querySelector('.novo-player');
  assert.equal(textoDe(ficha.querySelector('.marcas')), 'NOVO PLAYER republica_exemplo');
  assert.equal(textoDe(ficha.querySelector('h3')), 'República de Exemplo');
  assert.equal(textoDe(ficha.querySelectorAll('.marcas')[1]), 'Governos e políticos IN Mudança da ordem time discutível');
  /* DNA sem cor: no Painel a única cor de dado é a do alerta */
  const tira = ficha.querySelector('.dna');
  assert.ok(tira.classList.contains('dna--tinta'));
  assert.deepEqual(textos(tira.querySelectorAll('.dna__sigla')), ['PAN 1', 'PAN 2', 'IA 1', 'IA 2', 'FALA', 'CLIMA', 'FRONT']);
  const celulas = tira.querySelectorAll('.dna__celula');
  assert.deepEqual(textos(celulas.map((c) => c.querySelector('.so-leitor'))), [
    'Pandemia (início): sem posição conhecida', 'Pandemia (depois): misto', 'IA (lançamento do ChatGPT): sem posição conhecida',
    'IA (depois): polo azul', 'Moderação de conteúdo: polo vermelho, posição em dúvida',
    'Mudanças climáticas: sem posição conhecida', 'Imigração: polo vermelho'
  ]);
  assert.deepEqual(textos(celulas.map((c) => c.querySelector('.dna__metade'))), ['W', 'Y', 'W', 'B', 'R?', 'W', 'R']);
  const fontes = ficha.querySelectorAll('.novo-player__fontes a');
  assert.deepEqual(textos(fontes), ['Pandemia (depois) (abre em nova aba)', 'IA (depois) (abre em nova aba)',
    'Moderação de conteúdo (abre em nova aba)', 'Imigração (abre em nova aba)']);
  assert.equal(fontes[1].getAttribute('href'), 'https://parlamento.oficial.exemplo.invalid/lei-texto-aprovado');
  const t = textoDe(ficha);
  assert.match(t, /Fontes das posições: Pandemia \(depois\)/);
  assert.match(t, /Texto fictício\. País inventado, usado só nesta edição de exemplo\./);
  assert.match(t, /Por que entrou: Texto fictício\. Agiu na principal p1/);
  /* o player novo ainda não está em players.json: sem a ficha, não há link para ela */
  assert.equal(ficha.querySelector('a[href^="#/regua/players"]'), null);
});

test('07 movimentos: depois que o player novo entra em players.json, a ficha leva à Régua', async () => {
  const tabela = comHistorico();
  const novo = Object.assign({}, tabela['edicoes/2026-11-19.json'].novos_players[0], { origem: 'rotina', incluido_em: '2026-11-19' });
  tabela['dados/players.json'].players.push(novo);
  const m = await abre({ arquivos: tabela });
  const link = m.um('.novo-player a[href^="#/regua/players"]');
  assert.equal(link.getAttribute('href'), '#/regua/players/republica_exemplo');
  assert.equal(textoDe(link), 'Ver a ficha na Régua');
  /* e o alvo do ataque passa a ser link para a linha do player */
  assert.equal(m.todos('#item-p1 .dossie .ataque__cabeca')[0].querySelectorAll('a')[2].getAttribute('href'), '#/regua/players/republica_exemplo');
});

test('08 radar: título com a contagem, filtros e as linhas fechadas', async () => {
  const m = await abre({ arquivos: comHistorico() });
  const secao = m.um('#s-radar');
  assert.equal(textoDe(secao.querySelector('h2')), '08 RADAR (6)');
  assert.equal(textoDe(secao.querySelector('.nota-secao')), 'Mapa de veículos em rascunho, ainda sem revisão do dono. Ver o mapa.');
  assert.deepEqual(textos(secao.querySelectorAll('.filtros__grupo button')), ['Todas (6)', 'Geopolítica (3)', 'IA (3)']);
  const seletores = secao.querySelectorAll('.filtros select');
  assert.deepEqual(seletores.map((s) => s.getAttribute('aria-label')), ['Filtrar por domínio', 'Filtrar por partido']);
  assert.deepEqual(textos(seletores[0].querySelectorAll('option')),
    ['Todos os domínios', 'Energia', 'Alimentos', 'Câmbio', 'Cadeias de suprimento', 'Risco de conflito']);
  assert.deepEqual(seletores[1].querySelectorAll('option').map((o) => o.getAttribute('value')),
    ['', 'ordem_global', 'centro_atlantico', 'bancada_talento', 'soberanistas', 'eixo_revisionista', 'centrao', 'independentes']);
  assert.equal(textoDe(seletores[1].querySelector('option')), 'Todos os partidos');

  const linhas = secao.querySelectorAll('.radar__item');
  assert.deepEqual(linhas.map((l) => l.getAttribute('id')), ['item-r1', 'item-r2', 'item-r3', 'item-r4', 'item-r5', 'item-r6']);
  linhas.forEach((l) => {
    assert.equal(l.querySelector('button').getAttribute('aria-expanded'), 'false');
    assert.equal(aVista(l.querySelector('.radar__corpo')), false);
    assert.equal(aVista(l), true);
  });
  const fechada = (i) => textoDe(linhas[i].querySelector('.radar__cabeca'));
  assert.equal(fechada(0), 'IA Fabricante fictícia assina contrato de chips de IA Wired OG atira em Jensen Huang (Nvidia) · sem ganhador ' +
    'CONFIANÇA MÉDIA Cadeias de suprimento CONFLITO DE INTERESSE Abrir: Fabricante fictícia assina contrato de chips de IA');
  assert.match(fechada(1), /Wired OG atira em Google · OG \+1 \(ganha\) narrativa CONFIANÇA MÉDIA CONFLITO DE INTERESSE/);
  assert.match(fechada(3), /^GEOPOLÍTICA Seguradoras fictícias anunciam fim da cobertura no Estreito de Exemplo Valor Econômico CE atira em Reino de Amostra \(fictício\) · CE −1 \(perde\) CONFIANÇA MÉDIA Cadeias de suprimento Energia/);
  assert.match(fechada(4), /The Wall Street Journal CE · sem alvo · sem ganhador CONFIANÇA MÉDIA Câmbio/);
  assert.match(fechada(5), /Xinhua \(Agência de Notícias Xinhua\) ER atira em Centro Atlântico · IN \+2 \(ganha\) · ER \+1 \(ganha\) narrativa/);
});

test('08 radar: a linha aberta usa as mesmas linhas do dossiê', async () => {
  const m = await abre({ arquivos: comHistorico() });
  const linha = m.um('#item-r4');
  await m.clica(linha.querySelector('button'));
  const corpo = linha.querySelector('.radar__corpo');
  assert.equal(aVista(corpo), true);
  assert.equal(textoDe(linha.querySelector('button')), 'Fechar: Seguradoras fictícias anunciam fim da cobertura no Estreito de Exemplo');
  assert.deepEqual(textos(corpo.querySelectorAll('h4')),
    ['O QUE ACONTECEU', 'QUEM ATIROU (1)', 'O ATO NA RÉGUA', 'QUEM GANHA E QUEM PERDE', 'MOVIMENTOS', 'FONTES (2)']);
  const t = textoDe(corpo);
  assert.match(t, /O ATO NA RÉGUA Nenhum ato desta notícia mexe num tema da régua\./);
  assert.match(t, /QUEM GANHA E QUEM PERDE CE Centrão − perde força 1 de 3 sinal contrato/);
  assert.match(t, /MOVIMENTOS Nenhum movimento neste item\./);
  assert.match(t, /CONTINUAÇÃO DE 18\/11$/);
  assert.equal(corpo.querySelector('a[href="#/edicao/2026-11-18/r5"]').textContent, 'CONTINUAÇÃO DE 18/11');
  assert.equal(corpo.querySelectorAll('.ataque').length, 1);
  assert.equal(corpo.querySelectorAll('.fonte').length, 2);

  /* r5: alvo "nenhum" leva a dica; placar vazio mostra o sem_placar */
  const r5 = m.um('#item-r5 .radar__corpo');
  const semAlvo = r5.querySelector('.ataque .tem-dica');
  assert.equal(semAlvo.childNodes[0].textContent, 'sem alvo');
  assert.equal(textoDe(semAlvo.querySelector('.so-leitor')), ': O texto só relata, ou só promove alguém. Não ataca ninguém.');
  assert.equal(r5.querySelectorAll('.ataque use[href="#i-estavel"]').length, 0, 'sem alvo, sem seta');
  assert.match(textoDe(r5), /QUEM GANHA E QUEM PERDE Texto fictício\. Decisão esperada: nada mudou\./);
  /* r3: veículo de lado incerto */
  assert.match(textoDe(m.um('#item-r3 .ataque__cabeca')), /^The Verge OG atira em Bancada do Talento LADO INCERTO$/);
  /* r2: item com conflito de interesse traz o aviso fixo no topo do item aberto */
  const aviso = m.um('#item-r2 .radar__corpo').children[0];
  assert.ok(aviso.classList.contains('aviso'));
  assert.equal(textoDe(aviso), 'CONFLITO DE INTERESSE Aviso: o INFOCENARIUM é escrito por um modelo de IA da Anthropic, que é do setor de IA e pode ser parte ou ' +
    'concorrente nesta notícia. Este item envolve nomes da lista de conflito da régua: Google. ' +
    'Por isso a confiança deste item não passa de média. Ver Método.');
  assert.equal(aviso.querySelector('a').getAttribute('href'), '#/metodo/conflito');
});

test('09 bastidores: modo, números, limites, candidatos e veículos sugeridos', async () => {
  const m = await abre({ arquivos: comHistorico() });
  const secao = m.um('#s-bastidores');
  assert.equal(textoDe(secao.querySelector('h2')), '09 BASTIDORES');
  assert.equal(textoDe(secao.querySelector('.bastidores__modo')), 'coleta normal, pelos feeds dos veículos');
  assert.deepEqual(textos(secao.querySelectorAll('.bastidores__numero')), [
    'veículos consultados 19', 'feeds lidos 61', 'feeds que falharam 7', 'páginas lidas 11', 'buscas 4',
    'minutos de trabalho 24', 'páginas descartadas por trazer ordens ao agente 1'
  ]);
  assert.deepEqual(textos(secao.querySelectorAll('h3')), ['O QUE NÃO DEU PARA CONFERIR', 'ATORES SEM FICHA NA RÉGUA', 'VEÍCULOS QUE FIZERAM FALTA']);
  assert.match(textoDe(secao.querySelector('.bastidores__limites')), /^Edição de exemplo: todo o conteúdo é fictício/);
  const listas = secao.querySelectorAll('.bastidores__lista');
  assert.match(textoDe(listas[0]), /^Reino de Amostra \(fictício\) reino_de_amostra: Texto fictício\. Alvo do ataque da principal p1\./);
  assert.equal(textoDe(listas[1]), 'Gazeta de Amostra (gazeta.exemplo.invalid)');
  assert.equal(secao.querySelectorAll('a').length, 0, 'veículo sugerido é texto simples, nunca link');
});

test('a ordem do documento é a da tabela: 01, 02, 03, 04, 05, 06, 07, 08, 09', async () => {
  const m = await abre({ arquivos: comHistorico() });
  assert.deepEqual(m.todos('main h2').map((h) => textoDe(h).slice(0, 2)), ['01', '02', '03', '04', '05', '06', '07', '08', '09']);
  assert.deepEqual(m.todos('.coluna-lateral > section').map((s) => s.getAttribute('id')), ['s-placar', 's-vigiar', 's-movimentos']);
  /* h1 da vista, h2 por seção, h3 por item, h4 por parte do dossiê */
  assert.equal(m.todos('main h1').length, 1);
  assert.equal(m.todos('main h2').length, 9);
  assert.ok(m.todos('.dossie h4').length >= 27);
  assert.equal(m.todos('main h5').length + m.todos('main h6').length, 0);
});

test('todos os arquivos são pedidos uma vez, com cache "no-cache"', async () => {
  const m = await abre({ arquivos: comHistorico() });
  assert.deepEqual(m.rede.pedidos.map((p) => p.caminho).sort(), ['dados/indicadores.json', 'dados/players.json', 'dados/regua.json',
    'dados/veiculos.json', 'dados/vetores.json', 'edicoes/2026-11-19.json', 'edicoes/indice.json']);
  m.rede.pedidos.forEach((p) => assert.equal(p.opcoes.cache, 'no-cache', p.caminho));
  /* trocar de vista e voltar não pede de novo: o que foi lido fica na memória */
  await m.vai('#/metodo');
  await m.vai('#/');
  assert.equal(m.rede.pedidos.length, 7);
  assert.equal(textoDe(m.um('#s-hoje .alerta__numeral')), '3');
});

test('com os dados congelados de verdade, o Painel monta sem id cru à vista', async () => {
  const m = await abre({ arquivos: comHistorico() });
  /* a edição de exemplo cita 19 veículos, 7 partidos e 8 players que existem nos dados */
  const crus = m.todos('.id-cru').map(textoDe);
  assert.deepEqual(crus, ['2026-11-17_p3_ue', 'reino_de_amostra'], 'só o vetor que não existe e o id do candidato');
  assert.equal(dados().veiculos.veiculos.length > 100, true);
});
