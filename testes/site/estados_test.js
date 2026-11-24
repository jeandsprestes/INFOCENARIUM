'use strict';

/* Os estados da especificação do site (seção 5.2) que tocam o Painel, o dossiê e a
 * edição antiga. Cada teste monta o estado nos dados e confere a tela. */

const test = require('node:test');
const assert = require('node:assert/strict');
const {
  abre, arquivos, edicaoDeExemplo, edicaoReal, edicaoFalha, entradaDoIndice, entradaSolta, indiceDe,
  textoDe, aVista, AGORA, DIA, Evento
} = require('./apoio.js');

const textos = (lista) => lista.map(textoDe);
const HORA = 3600000;
const MINUTO = 60000;
const rotulosDosAvisos = (m, onde) => textos(m.todos((onde || '#avisos-edicao') + ' .aviso__rotulo'));

/* Duas edições de verdade, 18/11 e 19/11. */
function duasEdicoes(mudaOntem, mudaHoje) {
  return arquivos({ edicoes: [edicaoReal('2026-11-18', mudaOntem), edicaoReal(DIA, mudaHoje)] });
}

test('carregando: a moldura já mostra os títulos; depois de 8 segundos, "Está demorando"', async () => {
  const m = await abre({ segura: true, esperar: false });
  await m.assenta();
  assert.equal(m.um('#vista').getAttribute('aria-busy'), 'true');
  assert.equal(textoDe(m.um('#carimbo')), 'Carregando edição…');
  assert.equal(m.todos('main h2').length, 9);
  m.todos('main .secao__corpo').forEach((corpo) => assert.equal(textoDe(corpo), '—'));
  assert.equal(textoDe(m.um('#anuncio')), 'Carregando edição…');
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);

  m.relogio.avanca(7999);
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0, 'antes de 8 segundos, nada');
  m.relogio.avanca(1);
  const aviso = m.um('#avisos-gerais .aviso');
  assert.equal(textoDe(aviso), 'Carregando edição… Está demorando. A conexão pode estar lenta. Tentar de novo');
  assert.equal(textoDe(m.um('#anuncio')), 'Está demorando. A conexão pode estar lenta.');

  /* "Tentar de novo" pede outra vez o que não chegou */
  assert.equal(m.rede.pedidos.length, 1);
  m.rede.segura = false;
  await m.clica(aviso.querySelector('button'));
  assert.equal(m.rede.pedidos.filter((p) => p.caminho === 'edicoes/indice.json').length, 2);
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0, 'o aviso sai quando a edição chega');
  assert.equal(m.um('#vista').hasAttribute('aria-busy'), false);
  assert.equal(textoDe(m.um('h1')), 'Edição de 19/11/2026');
});

test('carregando: a edição chega sozinha depois do aviso de demora, e o aviso sai', async () => {
  const m = await abre({ segura: true, esperar: false });
  await m.assenta();
  m.relogio.avanca(8000);
  assert.equal(m.todos('#avisos-gerais .aviso').length, 1);
  m.rede.solta();
  await m.assenta();
  assert.equal(textoDe(m.um('h1')), 'Edição de 19/11/2026');
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
  assert.equal(m.rede.pedidos.filter((p) => p.caminho === 'edicoes/indice.json').length, 1, 'sem pedir de novo');
});

test('carregando: chegou antes de 8 segundos, o aviso de demora nunca aparece', async () => {
  const m = await abre();
  m.relogio.avanca(20000);
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
});

test('carregando: na troca de edição o quadro anterior fica inteiro, e o carimbo avisa', async () => {
  const m = await abre({ arquivos: duasEdicoes() });
  assert.equal(textoDe(m.um('h1')), 'Edição de 19/11/2026');
  m.rede.segura = true;
  await m.vai('#/edicao/2026-11-18');
  /* a edição de 18/11 ainda não chegou */
  assert.equal(m.um('#vista').getAttribute('aria-busy'), 'true');
  assert.equal(textoDe(m.um('h1')), 'Edição de 19/11/2026', 'o quadro anterior continua na tela');
  assert.equal(m.todos('.principal').length, 3);
  assert.equal(textoDe(m.um('.carimbo__carga')), 'Carregando edição de 18/11…');
  assert.equal(aVista(m.um('.carimbo__carga')), true);
  assert.equal(aVista(m.um('.carimbo__texto')), false);
  m.rede.solta();
  await m.assenta();
  assert.equal(textoDe(m.um('h1')), 'Edição de 18/11/2026');
  assert.equal(m.um('#vista').hasAttribute('aria-busy'), false);
  assert.match(textoDe(m.um('.carimbo__texto')), /^ED\. 18\/11\/2026/);
});

test('vazio: índice sem edição mostra o aviso, e Régua e Método seguem abrindo', async () => {
  const tabela = arquivos();
  tabela['edicoes/indice.json'] = { versao: 1, atualizado_em: '2026-11-19T21:14:03Z', edicoes: [] };
  const m = await abre({ arquivos: tabela });
  assert.equal(textoDe(m.um('#avisos-gerais .aviso')), 'NENHUMA EDIÇÃO AINDA A primeira sai às 18h de Brasília.');
  assert.equal(m.um('#vista').hasAttribute('aria-busy'), false);
  assert.equal(textoDe(m.um('#carimbo')), '—', 'o carimbo deixa de dizer "Carregando"');
  assert.equal(m.todos('main h2').length, 9, 'a moldura fica');
  await m.vai('#/regua/partidos');
  assert.equal(textoDe(m.um('h1')), 'Régua');
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
  await m.vai('#/metodo');
  assert.equal(textoDe(m.um('h1')), 'Método');
});

test('vazio: a moldura que o script monta é a mesma do index.html', async () => {
  /* forma de um elemento: marca, atributos e filhos, sem os espaços entre marcas */
  function forma(el) {
    const atributos = Array.from(el.atributos.entries()).filter(([nome]) => nome !== 'aria-busy')
      .map(([nome, valor]) => nome + '="' + valor + '"').sort().join(' ');
    const filhos = el.childNodes.map((no) => (no.nodeType === 1 ? forma(no) : no.textContent.replace(/\s+/g, ' ').trim())).filter(Boolean);
    return '<' + el.localName + (atributos ? ' ' + atributos : '') + '>' + filhos.join('') + '</' + el.localName + '>';
  }
  const tabela = arquivos();
  tabela['edicoes/indice.json'] = { versao: 1, edicoes: [] };
  /* antes de qualquer dado: a moldura escrita no arquivo */
  const antes = await abre({ arquivos: tabela, segura: true, esperar: false });
  const doArquivo = forma(antes.um('#vista')).replace('Carregando edição…', '—');
  /* depois do índice vazio: a moldura montada pelo script */
  const depois = await abre({ arquivos: tabela });
  assert.equal(forma(depois.um('#vista')), doArquivo);
});

test('erro de rede: o índice não carregou', async () => {
  const m = await abre({ arquivos: arquivos({ sem: ['edicoes/indice.json'] }) });
  const aviso = m.um('#avisos-gerais .aviso');
  assert.ok(aviso.classList.contains('aviso--grave'));
  assert.equal(textoDe(aviso), 'FALHA AO CARREGAR Não deu para carregar edicoes/indice.json. Confira a conexão. Tentar de novo ' +
    'Abrir o Arquivo de edições. O feed traz o resumo das últimas edições.');
  assert.deepEqual(aviso.querySelectorAll('a').map((a) => a.getAttribute('href')), ['#/arquivo', 'feed.xml']);
  assert.equal(m.um('#vista').hasAttribute('aria-busy'), false);
  assert.equal(textoDe(m.um('#carimbo')), '—');
  assert.match(textoDe(m.um('#anuncio')), /^FALHA AO CARREGAR\. Não deu para carregar edicoes\/indice\.json\./);

  /* a rede volta: "Tentar de novo" carrega a edição e tira o aviso */
  m.rede.arquivos['edicoes/indice.json'] = indiceDe([entradaDoIndice(edicaoDeExemplo())]);
  await m.clica(aviso.querySelector('button'));
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
  assert.equal(textoDe(m.um('h1')), 'Edição de 19/11/2026');
});

test('erro de rede: falha de conexão (fetch rejeitado) e JSON quebrado dão o mesmo aviso', async () => {
  const semRede = arquivos();
  semRede['edicoes/indice.json'] = new Error('sem rede');
  let m = await abre({ arquivos: semRede });
  assert.match(textoDe(m.um('#avisos-gerais .aviso')), /^FALHA AO CARREGAR Não deu para carregar edicoes\/indice\.json\./);

  const quebrado = arquivos();
  quebrado['edicoes/indice.json'] = '{"versao": 1, "edicoes": [';
  m = await abre({ arquivos: quebrado });
  assert.match(textoDe(m.um('#avisos-gerais .aviso')), /^FALHA AO CARREGAR/);

  const lista = arquivos();
  lista['edicoes/indice.json'] = '[1, 2, 3]';
  m = await abre({ arquivos: lista });
  assert.match(textoDe(m.um('#avisos-gerais .aviso')), /^FALHA AO CARREGAR/, 'JSON que não é objeto');
});

test('erro de rede: a edição não carregou, e o último quadro bom fica na tela', async () => {
  const tabela = duasEdicoes();
  delete tabela['edicoes/2026-11-18.json'];
  const m = await abre({ arquivos: tabela });
  assert.equal(textoDe(m.um('h1')), 'Edição de 19/11/2026');
  await m.vai('#/edicao/2026-11-18');
  assert.match(textoDe(m.um('#avisos-gerais .aviso')), /^FALHA AO CARREGAR Não deu para carregar edicoes\/2026-11-18\.json\. Confira a conexão\./);
  assert.equal(textoDe(m.um('h1')), 'Edição de 19/11/2026', 'o último quadro bom fica');
  assert.equal(m.todos('.principal').length, 3);
  assert.equal(m.um('#vista').hasAttribute('aria-busy'), false);
  assert.equal(aVista(m.um('.carimbo__texto')), true, 'o carimbo volta a dizer a data do quadro em tela');
  assert.equal(aVista(m.um('.carimbo__carga')), false);
  /* a falha não fica na memória: o arquivo volta e a rota carrega */
  m.rede.arquivos['edicoes/2026-11-18.json'] = edicaoReal('2026-11-18');
  await m.clica(m.um('#avisos-gerais .aviso button'));
  assert.equal(textoDe(m.um('h1')), 'Edição de 18/11/2026');
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
});

test('dado de apoio em falta: sem a régua, selo com "NÍVEL N" e ids crus', async () => {
  const m = await abre({ arquivos: arquivos({ sem: ['dados/regua.json'] }) });
  assert.deepEqual(rotulosDosAvisos(m), ['EDIÇÃO DE EXEMPLO', 'ERRATA', 'RÉGUA INDISPONÍVEL']);
  assert.equal(textoDe(m.todos('#avisos-edicao .aviso')[2]), 'RÉGUA INDISPONÍVEL Nomes e rótulos aparecem como identificadores.');
  assert.equal(m.documento.title, '[EXEMPLO] INFOCENARIUM · 19/11/2026 · nível 3');
  assert.equal(textoDe(m.um('#s-hoje .alerta__rotulo')), 'NÍVEL 3 subindo');
  assert.equal(textoDe(m.um('#s-hoje .alerta p.so-leitor')), 'Nível 3 de 5, subindo');
  assert.equal(textoDe(m.um('#dominio-energia .selo__rotulo')), 'NÍVEL 3');
  assert.equal(textoDe(m.um('#dominio-energia h3')), 'energia');
  assert.equal(m.um('#s-hoje .alerta__significado'), null);
  /* partido, tema e domínio aparecem pelo id, sem link para a Régua */
  assert.equal(m.todos('.etiqueta--partido').length, 0);
  assert.match(textoDe(m.um('#item-p1 .principal__linha')), /^Atirou: The New York Times ordem_global atira em/);
  assert.equal(textoDe(m.um('#item-p1 .eixo')).startsWith('clima'), true);
  /* o placar do dia mostra só os partidos da edição, pelo id */
  assert.equal(m.todos('#s-placar .placar__linha').length, 7);
  assert.match(textoDe(m.um('#s-placar .placar__linha')), /^ordem_global ordem_global: saldo mais 4/);
  /* força: sem a régua, o rótulo fixo */
  assert.match(textoDe(m.um('#item-p1 .placar-item .forca')), /força 2 de 3 ato reversível/);
  /* os filtros do radar seguem valendo, com os ids */
  assert.deepEqual(textos(m.todos('#s-radar select')[0].querySelectorAll('option')).slice(0, 3), ['Todos os domínios', 'energia', 'alimentos']);
});

test('dado de apoio em falta: sem o mapa de veículos, o veículo aparece pelo id e não há nota de rascunho', async () => {
  const m = await abre({ arquivos: arquivos({ sem: ['dados/veiculos.json'] }) });
  assert.equal(textoDe(m.todos('#avisos-edicao .aviso')[2]), 'MAPA DE VEÍCULOS INDISPONÍVEL Os veículos aparecem pelo identificador, sem lado.');
  assert.match(textoDe(m.um('#item-p1 .ataque__cabeca')), /^nyt OG atira em República de Exemplo$/);
  assert.equal(m.um('#item-p1 .ataque__veiculo').localName, 'span', 'sem link para a ficha');
  assert.match(textoDe(m.um('#item-p1 .fonte')), /^reuters 19\/11/);
  assert.equal(m.todos('.nota-secao').length, 0);
  assert.equal(/LADO INCERTO|FOGO AMIGO/.test(textoDe(m.um('main'))), false);
});

test('dado de apoio em falta: sem players e sem vetores, o aviso diz o arquivo', async () => {
  const tabela = arquivos({ edicoes: [edicaoReal(DIA)], sem: ['dados/players.json', 'dados/vetores.json'] });
  const m = await abre({ arquivos: tabela });
  assert.deepEqual(textos(m.todos('#avisos-edicao .aviso')).slice(1), [
    'DADOS DE APOIO INDISPONÍVEIS Não deu para carregar dados/players.json. Alguns nomes aparecem como identificadores.',
    'DADOS DE APOIO INDISPONÍVEIS Não deu para carregar dados/vetores.json. Alguns nomes aparecem como identificadores.'
  ]);
  /* o player novo desta edição ainda tem nome; os outros aparecem pelo id */
  assert.match(textoDe(m.um('#item-p1 .principal__linha')), /atira em República de Exemplo · Fox News SO atira em ue ·/);
  assert.match(textoDe(m.um('#s-movimentos .vetor__cabeca')), /^ue desloca-se para SO força 2/);
  assert.equal(m.todos('#s-movimentos .vetor__cabeca a[href^="#/regua/players"]').length, 0);
});

test('dado de apoio em falta: sem os vetores, não há reincidência nem marca de anulado', async () => {
  const comRegistro = arquivos({ edicoes: [edicaoReal(DIA)] });
  comRegistro['dados/vetores.json'].vetores.push(
    { id: '2026-11-12_p1_ue', data: '2026-11-12', item: 'p1', player: 'ue', de: 'centro_atlantico', para: 'soberanistas', forca: 1, tema: 'clima', porque: 'Teste.', url: 'https://exemplo.invalid/a' },
    { id: '2026-11-19_anula_1', data: '2026-11-19', anula: '2026-11-19_r2_google', porque: 'Teste de anulação.', url: 'https://exemplo.invalid/b' });
  let m = await abre({ arquivos: comRegistro });
  assert.match(textoDe(m.um('#s-movimentos')), /2ª vez em 30 dias/);
  assert.match(textoDe(m.um('#s-movimentos')), /ANULADO/);
  delete comRegistro['dados/vetores.json'];
  m = await abre({ arquivos: comRegistro });
  assert.equal(/vez em 30 dias|ANULADO/.test(textoDe(m.um('#s-movimentos'))), false);
  assert.equal(m.todos('.vetor--anulado').length, 0);
});

test('dado de apoio em falta: sem o catálogo não há aviso, e o valor sai com 2 a 4 casas', async () => {
  const m = await abre({ arquivos: arquivos({ sem: ['dados/indicadores.json'] }) });
  assert.deepEqual(rotulosDosAvisos(m), ['EDIÇÃO DE EXEMPLO', 'ERRATA']);
  const valor = (id) => textoDe(m.um('#ind-' + id + ' .ficha__valor'));
  assert.equal(valor('brent'), '78,40');
  assert.equal(valor('trigo'), '216,90');
  assert.equal(valor('usd_brl'), '5,4321');
  assert.equal(valor('ouro'), '2.650,00');
});

test('dado de apoio: indicador sem "casas" no catálogo sai com 2', async () => {
  const tabela = arquivos();
  tabela['dados/indicadores.json'].indicadores.forEach((i) => { if (i.id === 'usd_brl' || i.id === 'trigo') { delete i.casas; } });
  const m = await abre({ arquivos: tabela });
  assert.equal(textoDe(m.um('#ind-usd_brl .ficha__valor')), '5,43');
  assert.equal(textoDe(m.um('#ind-trigo .ficha__valor')), '216,90');
});

test('mapa em rascunho: a nota das seções 04 e 08 some quando revisado_em traz uma data', async () => {
  let m = await abre();
  assert.equal(m.todos('#s-principais .nota-secao').length, 1);
  assert.equal(m.todos('#s-radar .nota-secao').length, 1);
  assert.equal(m.um('#s-principais .nota-secao use').getAttribute('href'), '#i-aviso');

  const revisado = arquivos();
  revisado['dados/veiculos.json'].revisado_em = '2026-12-01';
  m = await abre({ arquivos: revisado });
  assert.equal(m.todos('.nota-secao').length, 0);

  const semCampo = arquivos();
  delete semCampo['dados/veiculos.json'].revisado_em;
  m = await abre({ arquivos: semCampo });
  assert.equal(m.todos('.nota-secao').length, 2, 'campo ausente vale como null');
});

test('edição atrasada: mais de 26 horas no Painel', async () => {
  const gerada = Date.UTC(2026, 10, 19, 21, 14, 3);
  const m = await abre({ arquivos: arquivos({ edicoes: [edicaoReal(DIA)] }), agora: gerada + 27 * HORA + 5 * MINUTO });
  const placas = m.todos('#carimbo .placa');
  assert.deepEqual(textos(placas), ['ATRASADA']);
  assert.ok(placas[0].classList.contains('placa--grave'));
  assert.equal(placas[0].querySelector('use').getAttribute('href'), '#i-relogio');
  assert.equal(textoDe(m.um('.carimbo__idade')), 'HÁ 27 H');
  const aviso = m.um('#avisos-edicao .aviso');
  assert.ok(aviso.classList.contains('aviso--grave'));
  assert.equal(textoDe(aviso), 'EDIÇÃO ATRASADA A mais recente é de 19/11/2026 e foi gerada há 27 h. ' +
    'A edição sai todo dia às 18h de Brasília. O quadro abaixo não é de hoje.');
  const linha = m.todos('#s-hoje .alerta__linha').filter(aVista).map(textoDe);
  assert.ok(linha.includes('Quadro de 19/11, não de hoje.'));
  /* os valores não somem */
  assert.equal(textoDe(m.um('.alerta__numeral')), '3');
  assert.equal(m.todos('.ficha').length, 12);
  assert.equal(m.todos('.principal').length, 3);
});

test('edição atrasada: a conta é refeita a cada minuto, junto com a idade, sem anúncio', async () => {
  const gerada = Date.UTC(2026, 10, 19, 21, 14, 3);
  const m = await abre({ arquivos: arquivos({ edicoes: [edicaoReal(DIA)] }), agora: gerada + 26 * HORA - 90000 });
  assert.deepEqual(textos(m.todos('#carimbo .placa')), ['EM DIA']);
  assert.equal(textoDe(m.um('.carimbo__idade')), 'HÁ 25 H');
  assert.equal(rotulosDosAvisos(m).includes('EDIÇÃO ATRASADA'), false);
  assert.equal(m.todos('#s-hoje .alerta__linha').filter(aVista).map(textoDe).includes('Quadro de 19/11, não de hoje.'), false);
  const anuncio = textoDe(m.um('#anuncio'));

  m.relogio.avanca(MINUTO);       /* 25h59min30s */
  assert.deepEqual(textos(m.todos('#carimbo .placa')), ['EM DIA']);
  m.relogio.avanca(MINUTO);       /* 26h00min30s */
  assert.deepEqual(textos(m.todos('#carimbo .placa')), ['ATRASADA']);
  assert.equal(textoDe(m.um('.carimbo__idade')), 'HÁ 26 H');
  assert.ok(rotulosDosAvisos(m).includes('EDIÇÃO ATRASADA'));
  assert.ok(m.todos('#s-hoje .alerta__linha').filter(aVista).map(textoDe).includes('Quadro de 19/11, não de hoje.'));
  m.relogio.avanca(HORA);
  assert.match(textoDe(m.um('#avisos-edicao .aviso')), /foi gerada há 27 h\./, 'as horas do aviso andam com o relógio');
  assert.equal(textoDe(m.um('#anuncio')), anuncio, 'a idade do carimbo não é anunciada');
});

test('edição de exemplo: aviso grave, EXEMPLO em cada título, título da aba, sem fita e sem acumulado', async () => {
  const m = await abre();
  assert.equal(m.documento.title, '[EXEMPLO] INFOCENARIUM · 19/11/2026 · nível 3 TENSÃO');
  const aviso = m.um('#avisos-edicao .aviso');
  assert.ok(aviso.classList.contains('aviso--grave'));
  assert.equal(textoDe(aviso), 'EDIÇÃO DE EXEMPLO Dados fictícios. Nada aqui aconteceu. Serve só para mostrar como o site funciona.');
  const placas = m.todos('#carimbo .placa');
  assert.deepEqual(textos(placas), ['EXEMPLO']);
  assert.ok(placas[0].classList.contains('placa--grave'));
  const titulos = m.todos('main h2');
  assert.equal(titulos.length, 9);
  titulos.forEach((h2) => assert.equal(textoDe(h2.querySelector('.etiqueta')), 'EXEMPLO', textoDe(h2)));
  assert.equal(m.um('.fita'), null);
  assert.equal(m.um('.historico'), null);
  assert.equal(/30 dias/.test(textoDe(m.um('#s-placar'))), false);
  assert.equal(textoDe(m.um('#s-placar .placar__nota')), 'narrativa +1');
});

test('edição de exemplo: fica fora do histórico de uma edição de verdade, e o Painel prefere a de verdade', async () => {
  const exemplo = edicaoDeExemplo();
  exemplo.data = '2026-11-21';   /* mais nova que a de verdade */
  const m = await abre({ arquivos: arquivos({ edicoes: [edicaoReal(DIA), exemplo], entradas: [entradaSolta('2026-11-18', { nivel: 2 })] }) });
  assert.equal(textoDe(m.um('h1')), 'Edição de 19/11/2026', 'o Painel mostra a mais recente que não é de exemplo');
  assert.deepEqual(textos(m.todos('#carimbo .placa')), ['EM DIA']);
  assert.equal(m.todos('.fita__coluna').length, 2, 'a de exemplo não vira coluna');
  /* as vizinhas pulam a de exemplo */
  assert.deepEqual(m.todos('.cabeca__acoes a.vizinha').map((a) => a.getAttribute('href')), ['#/edicao/2026-11-18']);
  /* só há a de exemplo: mostra ela */
  const m2 = await abre();
  assert.equal(textoDe(m2.um('h1')), 'Edição de 19/11/2026');
  assert.deepEqual(textos(m2.todos('#carimbo .placa')), ['EXEMPLO']);
});

test('edição de exemplo lida pelo endereço dela: sem fita e sem acumulado, mesmo com outras edições no índice', async () => {
  const exemplo = edicaoDeExemplo();
  exemplo.data = '2026-11-21';
  const tabela = arquivos({ edicoes: [edicaoReal('2026-11-18'), edicaoReal(DIA), exemplo],
    entradas: [entradaSolta('2026-11-17', { nivel: 2, saldos: { ordem_global: 7 } })] });
  const m = await abre({ arquivos: tabela, hash: '#/edicao/2026-11-21' });
  assert.equal(textoDe(m.um('h1')), 'Edição de 21/11/2026');
  assert.deepEqual(textos(m.todos('#carimbo .placa')), ['EXEMPLO', 'ARQUIVO']);
  assert.equal(m.um('.fita'), null);
  assert.equal(/30 dias/.test(textoDe(m.um('#s-placar'))), false);
  assert.equal(m.todos('a.vizinha').length, 0, 'a de exemplo não tem vizinhas: fica fora da fila');
  assert.equal(m.documento.title, '[EXEMPLO] INFOCENARIUM · 21/11/2026 · nível 3 TENSÃO');
  /* a comparação com a edição anterior continua valendo: é dado do índice, não histórico */
  assert.equal(textoDe(m.um('#s-hoje .alerta__linha')), 'antes (19/11): 3 TENSÃO');
});

test('completa: placa EM DIA e 3 principais', async () => {
  const m = await abre({ arquivos: arquivos({ edicoes: [edicaoReal(DIA)] }) });
  assert.deepEqual(textos(m.todos('#carimbo .placa')), ['EM DIA']);
  assert.equal(m.todos('.principal').length, 3);
  assert.deepEqual(rotulosDosAvisos(m), ['ERRATA']);
  assert.equal(textoDe(m.um('#s-hoje .alerta__linha')), 'Primeira edição: sem comparação.');
});

test('reduzida: placa e aviso; as seções mostram o que houver', async () => {
  const reduzida = edicaoReal(DIA, (e) => {
    e.estado = 'reduzida';
    e.principais = e.principais.slice(0, 1);
    e.radar = e.radar.slice(0, 3);
    e.bastidores.modo = 'busca';
  });
  const m = await abre({ arquivos: arquivos({ edicoes: [reduzida] }) });
  const placas = m.todos('#carimbo .placa');
  assert.deepEqual(textos(placas), ['REDUZIDA']);
  assert.equal(placas[0].classList.contains('placa--grave'), false);
  assert.equal(textoDe(m.um('#avisos-edicao .aviso')),
    'EDIÇÃO REDUZIDA Há menos itens que o normal. Veja o que não deu para conferir em Bastidores.');
  assert.equal(m.todos('.principal').length, 1);
  assert.equal(m.todos('.radar__item').length, 3);
  assert.equal(textoDe(m.um('#s-radar h2')), '08 RADAR (3)');
  assert.equal(textoDe(m.um('.bastidores__modo')), 'a coleta falhou: edição feita por busca');
});

test('falha: placa SEM EDIÇÃO, níveis repetidos e uma linha no lugar das seções 04 a 08', async () => {
  const ontem = edicaoReal('2026-11-18');
  const falha = edicaoFalha(DIA, ontem, (e) => { e.alerta.dominios[1].sem_preco = ['milho', 'soja']; });
  const m = await abre({ arquivos: arquivos({ edicoes: [ontem, falha] }) });
  const placas = m.todos('#carimbo .placa');
  assert.deepEqual(textos(placas), ['SEM EDIÇÃO']);
  assert.ok(placas[0].classList.contains('placa--grave'));
  const aviso = m.um('#avisos-edicao .aviso');
  assert.ok(aviso.classList.contains('aviso--grave'));
  assert.equal(textoDe(aviso), 'SEM EDIÇÃO HOJE A rotina de 19/11/2026 não conseguiu fechar a edição. ' +
    'A coleta e a busca falharam: sem rede na hora da rotina. Os níveis abaixo repetem os de 18/11/2026. Ver a última edição (18/11/2026).');
  assert.equal(aviso.querySelector('a').getAttribute('href'), '#/edicao/2026-11-18');
  /* 01 e 02 com a nota; 02 ainda mostra o que faltou de preço */
  assert.equal(textoDe(m.um('#s-hoje .nota-secao')), 'NÍVEIS REPETIDOS DE 18/11');
  assert.equal(textoDe(m.um('#s-dominios .nota-secao')), 'NÍVEIS REPETIDOS DE 18/11');
  assert.equal(textoDe(m.um('.alerta__numeral')), '3');
  assert.equal(m.todos('.dominio').length, 5);
  assert.equal(textoDe(m.um('#dominio-alimentos .dominio__sem-preco')), 'sem dado de preço de: Milho, Soja',
    'nome da edição; se não achar, o do catálogo');
  assert.ok(m.todos('#s-hoje .alerta__linha').map(textoDe).includes('Desde 18/11: nenhum nível mudou.'));
  /* 03 mostra os indicadores que houver */
  assert.equal(m.todos('.ficha').length, 2);
  /* 04 a 08 não aparecem */
  ['#s-principais', '#s-placar', '#s-vigiar', '#s-movimentos', '#s-radar'].forEach((id) => assert.equal(m.um(id), null, id));
  assert.equal(textoDe(m.um('.sem-itens')), 'Sem itens: a rotina não fechou a edição deste dia.');
  assert.deepEqual(m.todos('main h2').map((h) => textoDe(h).slice(0, 2)), ['01', '02', '03', '09']);
  /* 09 mostra só os limites: o modo e os números da falha não foram medidos */
  assert.equal(textoDe(m.um('.bastidores__limites')), 'Nada foi conferido: a rotina não fechou a edição.');
  assert.equal(m.todos('.bastidores__numero').length, 0, 'os zeros da falha não aparecem como fato');
  assert.equal(m.um('.bastidores__modo'), null, 'nada de "coleta normal" num dia sem edição');
});

test('falha como o publica.py grava: Bastidores sem "coleta normal" e sem os zeros', async () => {
  const ontem = edicaoReal('2026-11-18');
  const falha = edicaoFalha(DIA, ontem, (e) => {
    /* o que o publica.py falha grava (CONTRATO, seção 4.3): modo feeds e contadores em 0 */
    e.bastidores = { modo: 'feeds', veiculos_consultados: 0, feeds_ok: 0, feeds_falhos: 0, paginas_lidas: 0, buscas: 0,
      minutos: 0, injecoes_ignoradas: 0, limites: 'Sem rede: a coleta e a busca falharam.', candidatos: [], veiculos_sugeridos: [] };
  });
  const m = await abre({ arquivos: arquivos({ edicoes: [ontem, falha] }) });
  const bastidores = textoDe(m.um('#s-bastidores'));
  assert.doesNotMatch(bastidores, /coleta normal|feeds que falharam|minutos de trabalho|páginas lidas/);
  assert.equal(textoDe(m.um('.bastidores__limites')), 'Sem rede: a coleta e a busca falharam.');
  /* numa edição que fechou, o modo e os números continuam lá */
  const ok = await abre({ arquivos: arquivos({ edicoes: [ontem] }), agora: Date.UTC(2026, 10, 18, 22, 0, 0) });
  assert.ok(ok.um('.bastidores__modo'));
  assert.equal(ok.todos('.bastidores__numero').length, 7);
});

test('falha com o resumo que o publica.py grava: o aviso não repete "Sem edição hoje" e a aba diz "sem edição"', async () => {
  const ontem = edicaoReal('2026-11-18');
  const falha = edicaoFalha(DIA, ontem, (e) => { e.resumo = 'Sem edição hoje. Sem rede: a coleta e a busca falharam.'; });
  const m = await abre({ arquivos: arquivos({ edicoes: [ontem, falha] }) });
  assert.equal(textoDe(m.um('#avisos-edicao .aviso')), 'SEM EDIÇÃO HOJE A rotina de 19/11/2026 não conseguiu fechar a edição. ' +
    'Sem rede: a coleta e a busca falharam. Os níveis abaixo repetem os de 18/11/2026. Ver a última edição (18/11/2026).');
  assert.equal(m.documento.title, 'INFOCENARIUM · 19/11/2026 · sem edição', 'como o feed, sem o nível repetido');
  /* o resumo só com o começo fixo: nada sobra, e a frase seguinte vem logo depois */
  const vazia = edicaoFalha(DIA, ontem, (e) => { e.resumo = 'Sem edição hoje. '; });
  const m2 = await abre({ arquivos: arquivos({ edicoes: [ontem, vazia] }) });
  assert.equal(textoDe(m2.um('#avisos-edicao .aviso')), 'SEM EDIÇÃO HOJE A rotina de 19/11/2026 não conseguiu fechar a edição. ' +
    'Os níveis abaixo repetem os de 18/11/2026. Ver a última edição (18/11/2026).');
  /* edição que fechou: a aba continua com o nível */
  const ok = await abre({ arquivos: arquivos({ edicoes: [ontem] }), agora: Date.UTC(2026, 10, 18, 22, 0, 0) });
  assert.match(ok.documento.title, /^INFOCENARIUM · 18\/11\/2026 · nível \d /);
});

test('falha: sem edição anterior, os níveis não têm base', async () => {
  const falha = edicaoFalha(DIA, null, (e) => {
    e.alerta.nivel = 1;
    e.alerta.dominios.forEach((d) => { d.nivel = 1; });
    delete e.bastidores.feeds_ok;
    delete e.bastidores.minutos;
  });
  const m = await abre({ arquivos: arquivos({ edicoes: [falha] }) });
  assert.equal(textoDe(m.um('#avisos-edicao .aviso')), 'SEM EDIÇÃO HOJE A rotina de 19/11/2026 não conseguiu fechar a edição. ' +
    'A coleta e a busca falharam: sem rede na hora da rotina. Ainda não houve edição: todos os níveis estão em 1.');
  assert.equal(m.um('#avisos-edicao .aviso a'), null);
  assert.equal(textoDe(m.um('#s-hoje .nota-secao')), 'NÍVEIS SEM BASE: AINDA NÃO HOUVE EDIÇÃO');
  assert.equal(textoDe(m.um('#s-dominios .nota-secao')), 'NÍVEIS SEM BASE: AINDA NÃO HOUVE EDIÇÃO');
  assert.equal(m.todos('.bastidores__numero').length, 0, 'na falha, nenhum número: a rotina não os mediu');
  assert.match(textoDe(m.um('#dominio-energia .dominio__corpo')), /Nenhum gatilho hoje\./);
});

test('falha no Painel com a edição anterior no ar: a falha conta como vizinha', async () => {
  const anteontem = edicaoReal('2026-11-17');
  const falha = edicaoFalha('2026-11-18', anteontem);
  const hoje = edicaoReal(DIA);
  const m = await abre({ arquivos: arquivos({ edicoes: [anteontem, falha, hoje] }) });
  assert.deepEqual(m.todos('a.vizinha').map((a) => a.getAttribute('href')), ['#/edicao/2026-11-18'], 'as vizinhas contam a falha');
  /* mas a "edição anterior" das comparações pula a falha */
  assert.equal(textoDe(m.um('#s-hoje .alerta__linha')), 'antes (17/11): 3 TENSÃO');
});

test('edição de arquivo: placa ARQUIVO, link para a mais recente e nenhum atraso', async () => {
  const gerada = Date.UTC(2026, 10, 19, 21, 14, 3);
  const m = await abre({ arquivos: duasEdicoes(), hash: '#/edicao/2026-11-18', agora: gerada + 10 * 24 * HORA });
  assert.equal(textoDe(m.um('h1')), 'Edição de 18/11/2026');
  assert.deepEqual(textos(m.todos('#carimbo .placa')), ['ARQUIVO']);
  assert.equal(m.um('#carimbo .placa').classList.contains('placa--grave'), false);
  assert.deepEqual(rotulosDosAvisos(m), ['EDIÇÃO DE ARQUIVO', 'ERRATA'], 'não se calcula atraso em edição antiga');
  assert.equal(textoDe(m.um('#avisos-edicao .aviso')), 'EDIÇÃO DE ARQUIVO Você está lendo a edição de 18/11/2026.');
  assert.equal(textoDe(m.um('.carimbo__idade')), 'HÁ 11 DIAS');
  const acoes = m.todos('.cabeca__acoes a');
  assert.deepEqual(acoes.map((a) => a.getAttribute('href')), ['#/edicao/2026-11-19', '#/', 'edicoes/2026-11-18.md', 'edicoes/2026-11-18.json', 'feed.xml']);
  assert.equal(textoDe(acoes[0].querySelector('.so-leitor')), 'Edição seguinte, de 19/11/2026');
  assert.equal(textoDe(acoes[1]), 'Ir para a mais recente');
  assert.equal(m.um('nav a[aria-current="page"]').textContent, 'Arquivo');
  assert.equal(m.documento.title, 'INFOCENARIUM · 18/11/2026 · nível 3 TENSÃO');
  assert.equal(m.todos('#s-hoje .alerta__linha').filter(aVista).some((p) => /não de hoje/.test(textoDe(p))), false);
});

test('edição de arquivo: a fita e os acumulados terminam na data da edição', async () => {
  const tabela = duasEdicoes();
  tabela['edicoes/indice.json'].edicoes.push(entradaSolta('2026-11-17', { nivel: 2, saldos: { ordem_global: 1 } }),
    entradaSolta('2026-10-19', { nivel: 5, saldos: { ordem_global: 10 } }));
  const m = await abre({ arquivos: tabela, hash: '#/edicao/2026-11-18' });
  const colunas = m.todos('.fita__dia').filter((d) => d.querySelector('.fita__coluna'));
  assert.deepEqual(colunas.map((d) => d.getAttribute('href')), ['#/edicao/2026-11-17', '#/edicao/2026-11-18'],
    '19/11 é depois; 19/10 ficou a 30 dias');
  assert.equal(m.um('.fita').getAttribute('aria-label'), 'Alerta nos últimos 30 dias: de 2 a 3; nesta edição, 3');
  assert.equal(textoDe(m.um('.fita__datas')), '20/10 18/11');
  assert.equal(textoDe(m.um('#s-placar .placar__nota')), 'narrativa +1 · 30 dias +5', '4 de 18/11 mais 1 de 17/11');
});

test('a data do endereço é a da edição mais recente: a vista é o Painel, sem tirar nem pôr', async () => {
  const m = await abre({ arquivos: duasEdicoes(), hash: '#/edicao/2026-11-19' });
  assert.deepEqual(textos(m.todos('#carimbo .placa')), ['EM DIA']);
  assert.equal(m.um('nav a[aria-current="page"]').textContent, 'Painel');
  assert.equal(rotulosDosAvisos(m).includes('EDIÇÃO DE ARQUIVO'), false);
  assert.equal(m.todos('.cabeca__acoes a').some((a) => textoDe(a) === 'Ir para a mais recente'), false);
});

test('corrigida: aviso com link para cada edição que traz a errata', async () => {
  const tabela = duasEdicoes();
  tabela['edicoes/indice.json'].edicoes[1].corrigida_em = ['2026-11-19', '2026-11-25'];
  const m = await abre({ arquivos: tabela, hash: '#/edicao/2026-11-18' });
  assert.deepEqual(rotulosDosAvisos(m), ['EDIÇÃO DE ARQUIVO', 'EDIÇÃO CORRIGIDA', 'ERRATA']);
  const aviso = m.todos('#avisos-edicao .aviso')[1];
  assert.equal(textoDe(aviso), 'EDIÇÃO CORRIGIDA Há correção a esta edição na errata de 19/11/2026 e 25/11/2026.');
  /* a de 19/11 está no índice e vira link; a de 25/11 não está: só a data */
  assert.deepEqual(aviso.querySelectorAll('a').map((a) => a.getAttribute('href')), ['#/edicao/2026-11-19']);
  assert.deepEqual(aviso.querySelectorAll('time').map((t) => t.getAttribute('datetime')), ['2026-11-19', '2026-11-25']);
});

test('formato novo: versão diferente de 1 na edição e em arquivo de apoio', async () => {
  const tabela = arquivos({ edicoes: [edicaoReal(DIA, (e) => { e.versao = 2; e.campo_do_futuro = { a: 1 }; })] });
  tabela['dados/players.json'].versao = 3;
  tabela['edicoes/indice.json'].versao = 2;
  const m = await abre({ arquivos: tabela });
  const avisos = textos(m.todos('#avisos-edicao .aviso'));
  assert.ok(avisos.includes('FORMATO NOVO Esta edição usa um formato mais novo que o site. Alguma parte pode não aparecer.'));
  assert.ok(avisos.includes('FORMATO NOVO O arquivo dados/players.json usa um formato mais novo que o site.'));
  assert.ok(avisos.includes('FORMATO NOVO O arquivo edicoes/indice.json usa um formato mais novo que o site.'));
  assert.equal(avisos.filter((a) => a.startsWith('FORMATO NOVO')).length, 3, 'os arquivos na versão 1 não levam aviso');
  assert.equal(m.todos('.principal').length, 3, 'chave que o site não conhece é ignorada');
});

test('nível mantido: etiqueta "MANTIDO DESDE" antes da leitura, só com gatilhos vazios e nível acima de 1', async () => {
  const m = await abre();
  const comEtiqueta = m.todos('.dominio').filter((d) => d.querySelector('.dominio__leitura .etiqueta'));
  assert.deepEqual(comEtiqueta.map((d) => d.getAttribute('id')), ['dominio-cambio']);
  const etiqueta = m.um('#dominio-cambio .dominio__leitura .etiqueta');
  assert.equal(textoDe(etiqueta), 'MANTIDO DESDE 17/11');
  assert.equal(etiqueta.querySelector('time').getAttribute('datetime'), '2026-11-17');
});

test('sem dado de preço: a linha aparece com a linha do domínio fechada ou aberta, e o nível não muda de desenho', async () => {
  const m = await abre({ arquivos: arquivos({ edicoes: [edicaoReal(DIA, (e) => { e.alerta.dominios[1].sem_preco = ['milho', 'id_que_nao_existe']; })] }) });
  const alimentos = m.um('#dominio-alimentos');
  const linha = alimentos.querySelector('.dominio__sem-preco');
  assert.equal(textoDe(linha), 'sem dado de preço de: Milho, id_que_nao_existe');
  assert.equal(linha.querySelector('use').getAttribute('href'), '#i-aviso');
  assert.equal(aVista(linha), true);
  await m.clica(alimentos.querySelector('button'));
  assert.equal(aVista(linha), true);
  assert.equal(alimentos.querySelector('.selo').getAttribute('class'), 'selo nivel-1');
});

test('alívio: etiqueta ALÍVIO no gatilho, com a dica', async () => {
  const m = await abre({ arquivos: arquivos({ edicoes: [edicaoReal(DIA, (e) => {
    e.alerta.dominios[4].gatilhos = [{ criterio: 'conflito.4', ref: 'p3', texto: 'Cessar-fogo assinado em 19/11.', alivio: true }];
  })] }) });
  const gatilho = m.um('#dominio-conflito .gatilho');
  const etiqueta = gatilho.querySelector('.etiqueta');
  assert.equal(etiqueta.childNodes[0].textContent, 'ALÍVIO');
  assert.equal(textoDe(etiqueta.querySelector('.so-leitor')), ': Acabou o estado que sustentava o nível. Por isso o domínio desce um degrau.');
  assert.equal(textoDe(etiqueta.querySelector('.dica')), 'Acabou o estado que sustentava o nível. Por isso o domínio desce um degrau.');
  assert.equal(textoDe(gatilho.querySelector('.gatilho__ref')), 'ver principal 3');
});

test('vetor anulado: fica à vista, riscado, com ANULADO, a data e o motivo; não conta em reincidência', async () => {
  const tabela = arquivos({ edicoes: [edicaoReal(DIA)] });
  tabela['dados/vetores.json'].vetores.push(
    { id: '2026-11-05_p1_ue', data: '2026-11-05', item: 'p1', player: 'ue', de: 'centro_atlantico', para: 'soberanistas', forca: 1, tema: 'clima', porque: 'Vetor antigo, depois anulado.', url: 'https://exemplo.invalid/v1' },
    { id: '2026-11-06_anula_1', data: '2026-11-06', anula: '2026-11-05_p1_ue', porque: 'Não houve o ato.', url: 'https://exemplo.invalid/v2' },
    { id: '2026-11-19_p1_ue', data: '2026-11-19', item: 'p1', player: 'ue', de: 'centro_atlantico', para: 'soberanistas', forca: 2, tema: 'clima', porque: 'O de hoje.', url: 'https://exemplo.invalid/v3' },
    { id: '2026-11-19_r2_google', data: '2026-11-19', item: 'r2', player: 'google', de: 'bancada_talento', para: 'ordem_global', forca: 2, tema: 'ia_depois', porque: 'O de hoje.', url: 'https://exemplo.invalid/v4' },
    { id: '2026-11-20_anula_1', data: '2026-11-20', anula: '2026-11-19_r2_google', porque: 'O adiamento foi desmentido pela empresa.', url: 'https://exemplo.invalid/v5' });
  const m = await abre({ arquivos: tabela });
  const vetores = m.todos('#s-movimentos .vetor');
  /* o de hoje da UE: o antigo foi anulado, então não é "2ª vez" */
  assert.equal(vetores[0].classList.contains('vetor--anulado'), false);
  assert.equal(/vez em 30 dias/.test(textoDe(vetores[0])), false);
  /* o do Google foi anulado */
  const anulado = vetores[1];
  assert.ok(anulado.classList.contains('vetor--anulado'));
  assert.match(textoDe(anulado.querySelector('.vetor__cabeca')), /^Anulado: Google BT desloca-se para OG força 2 de 3 ato reversível IA 2 ANULADO CONFLITO DE INTERESSE radar 2$/);
  assert.equal(anulado.querySelector('.vetor__cabeca').children[0].getAttribute('class'), 'so-leitor', 'o nome acessível começa com "Anulado:"');
  /* a etiqueta e o motivo ficam fora do trecho riscado */
  const riscado = anulado.querySelector('.vetor__riscado');
  assert.equal(riscado.querySelectorAll('.etiqueta').some((e) => textoDe(e) === 'ANULADO'), false);
  const motivo = anulado.querySelector('.vetor__anulacao');
  assert.equal(textoDe(motivo), 'Anulado em 20/11: O adiamento foi desmentido pela empresa. fonte da correção (abre em nova aba)');
  assert.equal(motivo.querySelector('a').getAttribute('href'), 'https://exemplo.invalid/v5');
  assert.equal(aVista(anulado), true, 'vetor anulado nunca é escondido');
  /* também dentro do item */
  assert.ok(m.um('#item-r2 .radar__corpo .vetor').classList.contains('vetor--anulado'));
});

test('errata que anula vetor: diz qual foi anulado e leva a ele na Régua', async () => {
  const tabela = arquivos({ edicoes: [edicaoReal(DIA)] });
  tabela['dados/vetores.json'].vetores.push(
    { id: '2026-11-17_p3_ue', data: '2026-11-17', item: 'p3', player: 'ue', de: 'centro_atlantico', para: 'soberanistas', forca: 1, tema: 'ordem', porque: 'Teste.', url: 'https://exemplo.invalid/v1' });
  const m = await abre({ arquivos: tabela });
  const linha = m.todos('.errata__item')[1].querySelectorAll('p')[4];
  assert.equal(textoDe(linha), 'Esta correção anula o vetor de 17/11/2026: União Europeia para SO. Ver no registro.');
  assert.equal(linha.querySelector('a[href^="#/regua/vetores"]').getAttribute('href'), '#/regua/vetores/2026-11-17_p3_ue');
});

test('errata sem item vale para a edição toda', async () => {
  const m = await abre({ arquivos: arquivos({ edicoes: [edicaoReal(DIA, (e) => { e.errata = [{ edicao: '2026-11-12', erro: 'Erro geral.', correcao: 'O certo.' }]; })] }) });
  assert.equal(textoDe(m.um('#avisos-edicao .aviso__texto')), 'Esta edição corrige 1 ponto de edições anteriores.');
  const item = m.um('.errata__item');
  assert.equal(textoDe(item.querySelector('.errata__onde')), 'Edição de 12/11/2026, inteira.');
  assert.equal(item.querySelectorAll('a').length, 0, 'sem url, sem link; a edição não está no índice');
  assert.equal(textoDe(item), 'Edição de 12/11/2026, inteira. Estava errado: Erro geral. O certo: O certo.');
});

test('conflito de interesse: etiqueta no cartão e na linha do radar, aviso no item aberto, etiqueta nos vetores', async () => {
  const m = await abre();
  const comMarca = (seletor) => m.todos(seletor).filter((el) => textos(el.querySelectorAll('.marcas .etiqueta')).includes('CONFLITO DE INTERESSE'));
  assert.deepEqual(comMarca('.principal').map((el) => el.getAttribute('id')), ['item-p2']);
  assert.deepEqual(m.todos('.radar__item').filter((el) => textos(el.querySelectorAll('.radar__cabeca .etiqueta')).includes('CONFLITO DE INTERESSE'))
    .map((el) => el.getAttribute('id')), ['item-r1', 'item-r2', 'item-r3']);
  const aviso = m.um('#item-p2 .dossie').children[0];
  assert.ok(aviso.classList.contains('aviso'));
  assert.match(textoDe(aviso), /^CONFLITO DE INTERESSE Aviso: o INFOCENARIUM é escrito por modelos de IA, do setor de IA, que podem ser parte ou concorrente nesta notícia: foi construído pelo Claude Fable e pelo Claude Opus, da Anthropic, e hoje quem escreve é o GLM, da Z.ai\. Este item envolve nomes da lista de conflito da régua: Sam Altman \(OpenAI\), Anthropic, Google\. Por isso a confiança deste item não passa de média\. Ver Método\.$/);
  /* o termo OpenAI já está no nome do player, e não se repete; r3 é só "notícia de IA": só o aviso fixo */
  assert.equal(textoDe(m.um('#item-r3 .radar__corpo .aviso')), 'CONFLITO DE INTERESSE Aviso: o INFOCENARIUM é escrito por modelos de IA, do setor de IA, que podem ser parte ou ' +
    'concorrente nesta notícia: foi construído pelo Claude Fable e pelo Claude Opus, da Anthropic, e hoje quem escreve é o GLM, da Z.ai. Por isso a confiança deste item não passa de média. Ver Método.');
  assert.equal(m.um('#item-p1 .dossie').children[0].localName, 'h4', 'item sem a marca não leva o aviso');
  assert.match(textoDe(m.um('#item-r2 .radar__corpo .vetor__cabeca')), /CONFLITO DE INTERESSE$/);
  assert.equal(/CONFLITO DE INTERESSE/.test(textoDe(m.um('#item-p1 .dossie .vetor__cabeca'))), false);
});

test('conflito de interesse: o aviso nomeia o vínculo que a lista da régua conhece (player pelo nome, termo como escrito)', async () => {
  const tabela = arquivos();
  /* a régua do dono ganha a Nvidia: o r1 (alvo huang_nvidia) passa a nomear o vínculo */
  tabela['dados/regua.json'].conflito.players.push('huang_nvidia');
  tabela['dados/regua.json'].conflito.termos.push('Nvidia', 'G..gle');
  const m = await abre({ arquivos: tabela });
  assert.match(textoDe(m.um('#item-r1 .radar__corpo .aviso')),
    /da Z\.ai\. Este item envolve nomes da lista de conflito da régua: Jensen Huang \(Nvidia\)\. Por isso/);
  /* termo com ponto é texto, não expressão: "G..gle" não casa com "Google" */
  assert.match(textoDe(m.um('#item-r2 .radar__corpo .aviso')), /régua: Google\. Por isso/);
  /* sem a lista na régua: só o aviso fixo, nunca erro */
  const semLista = arquivos();
  delete semLista['dados/regua.json'].conflito;
  const m2 = await abre({ arquivos: semLista });
  assert.match(textoDe(m2.um('#item-p2 .dossie .aviso')), /da Z\.ai\. Por isso a confiança/);
});

test('conflito de interesse: navegador sem \\p{L} (de antes de 2018) monta a edição, e o termo segue palavra inteira', async () => {
  const comNvidia = () => {
    const tabela = arquivos({ edicoes: [edicaoReal(DIA, (e) => { e.radar[2].fato += ' A Nvidia comenta; a SuperNvidiax, não.'; })] });
    tabela['dados/regua.json'].conflito.termos.push('Nvidia', 'SuperNvidia');
    return tabela;
  };
  const esperado = /da Z\.ai\. Este item envolve nomes da lista de conflito da régua: Nvidia\. Por isso/;
  const novo = await abre({ arquivos: comNvidia() });
  assert.match(textoDe(novo.um('#item-r3 .radar__corpo .aviso')), esperado);
  const velho = await abre({ arquivos: comNvidia(), esperar: false });
  /* o RegExp de um navegador velho: a bandeira u e o \p{…} dão erro de sintaxe */
  velho.janela.RegExp = function (fonte, bandeiras) {
    if (bandeiras && bandeiras.indexOf('u') !== -1) { throw new SyntaxError('Invalid regular expression: invalid escape'); }
    return new RegExp(fonte, bandeiras);
  };
  await velho.assenta();
  await velho.terminaFatias();
  assert.ok(velho.um('#item-p1'), 'a edição inteira montou');
  assert.match(textoDe(velho.um('#item-r3 .radar__corpo .aviso')), esperado);
});

test('lista vazia: cada seção diz o que falta, e nenhuma some', async () => {
  const vazia = edicaoReal(DIA, (e) => {
    e.indicadores = [];
    e.placar_do_dia = [];
    e.novos_players = [];
    e.respostas = [];
    e.errata = [];
    e.bastidores.candidatos = [];
    e.bastidores.veiculos_sugeridos = [];
    e.principais.concat(e.radar).forEach((item) => {
      item.placar = [];
      item.vetores = [];
      item.dominios = [];
      delete item.eixo;
      delete item.no_brasil;
      delete item.nao_confirmado;
    });
    e.principais[0].sem_placar = 'Ninguém ganhou: o ato ainda não saiu do papel.';
    delete e.radar[0].sem_placar;   /* edição antiga, sem o campo */
    e.radar[1].sem_placar = 'Só anúncio.';
  });
  const m = await abre({ arquivos: arquivos({ edicoes: [vazia] }) });
  assert.equal(m.todos('main h2').length, 9, 'nenhuma seção some');
  assert.equal(textoDe(m.um('#s-indicadores .secao__corpo')), 'Nenhum indicador nesta edição.');
  assert.equal(textoDe(m.um('#s-placar .secao__corpo')), 'Nenhum partido ganhou ou perdeu hoje.', 'só a frase, sem as 7 linhas');
  assert.match(textoDe(m.um('#s-vigiar')), /RESPOSTAS \(0\) O INFOCENARIUM responde às próprias perguntas quando a data vence\. Nenhuma pergunta venceu hoje\.$/);
  assert.match(textoDe(m.um('#s-movimentos .secao__corpo')), /Nenhum movimento hoje\.$/);
  assert.equal(m.um('.novo-player'), null);
  assert.match(textoDe(m.um('#s-bastidores')), /ATORES SEM FICHA NA RÉGUA Nenhum\. VEÍCULOS QUE FIZERAM FALTA Nenhum\.$/);
  assert.equal(rotulosDosAvisos(m).includes('ERRATA'), false);

  const p1 = textoDe(m.um('#item-p1 .dossie'));
  assert.match(p1, /O ATO NA RÉGUA Nenhum ato desta notícia mexe num tema da régua\./);
  assert.match(p1, /QUEM GANHA E QUEM PERDE Ninguém ganhou: o ato ainda não saiu do papel\./, 'placar vazio mostra o sem_placar');
  assert.match(p1, /MOVIMENTOS Nenhum movimento neste item\./);
  assert.match(p1, /PARA QUEM SE PREPARA Não mexe nos cinco domínios\. Vigiar:/);
  assert.equal(/No Brasil:|NÃO CONFIRMADO/.test(p1), false);
  assert.equal(m.todos('#item-p1 .dossie h4').length, 9, 'as partes do dossiê nunca somem');
  assert.equal(textoDe(m.todos('#item-p1 .principal__linha')[1]), 'Placar: sem ganhador');
  assert.match(textoDe(m.um('#item-r1 .radar__corpo')), /QUEM GANHA E QUEM PERDE Nenhum partido ganhou ou perdeu de forma medida\./,
    'edição sem o campo sem_placar mostra a frase');
  assert.match(textoDe(m.um('#item-r2 .radar__corpo')), /QUEM GANHA E QUEM PERDE Só anúncio\./);
  assert.match(textoDe(m.um('#item-r1 .radar__apoio')), /sem ganhador/);
});

test('lista vazia: só o player novo vazio não rende frase; vetores vazios com player novo também não', async () => {
  let m = await abre({ arquivos: arquivos({ edicoes: [edicaoReal(DIA, (e) => { e.novos_players = []; })] }) });
  assert.equal(/Nenhum movimento hoje/.test(textoDe(m.um('#s-movimentos'))), false);
  assert.equal(m.todos('#s-movimentos .vetor').length, 2);
  m = await abre({ arquivos: arquivos({ edicoes: [edicaoReal(DIA, (e) => { e.principais.concat(e.radar).forEach((i) => { i.vetores = []; }); })] }) });
  assert.equal(/Nenhum movimento hoje/.test(textoDe(m.um('#s-movimentos'))), false);
  assert.equal(m.todos('#s-movimentos .novo-player').length, 1);
});

test('referência quebrada: id que não existe no apoio aparece cru, sem link, e nada dá erro', async () => {
  const quebrada = edicaoReal(DIA, (e) => {
    e.principais[0].ataques[0].veiculo = 'jornal_que_saiu';
    e.principais[0].ataques[0].lado = 'partido_fantasma';
    e.principais[0].ataques[1].alvo = 'player_fantasma';
    e.principais[0].eixo.tema = 'tema_fantasma';
    e.principais[0].placar[0].partido = 'partido_fantasma';
    e.principais[0].vetores[0].player = 'player_fantasma';
    e.principais[0].vetores[0].para = 'partido_fantasma';
    e.principais[0].vetores[0].tema = 'tema_fantasma';
    e.principais[0].dominios = ['dominio_fantasma', 'energia'];
    e.principais[0].fontes[0].veiculo = 'jornal_que_saiu';
    e.principais[0].continuacao_de = '2026-10-01/p9';
    e.principais[1].continuacao_de = 'ontem';
    e.alerta.dominios[0].gatilhos[0].ref = 'indicador_fantasma';
    e.alerta.dominios[0].gatilhos[1].ref = 'p9';
    e.alerta.dominios[1].sem_preco = ['indicador_fantasma'];
    e.indicadores[0].dominio = 'dominio_fantasma';
    e.respostas[0].edicao = '2026-01-01';
    e.respostas[0].item = 'r2';
    e.placar_do_dia[0].partido = 'partido_fantasma';
    e.novos_players[0].tipo = 'tipo_fantasma';
    e.novos_players[0].time = 'time_fantasma';
    e.novos_players[0].partido = 'partido_fantasma';
  });
  const m = await abre({ arquivos: arquivos({ edicoes: [quebrada] }) });
  assert.equal(textoDe(m.um('h1')), 'Edição de 19/11/2026');
  assert.equal(m.todos('main h2').length, 9);
  const ataques = m.todos('#item-p1 .dossie .ataque__cabeca');
  assert.equal(textoDe(ataques[0]), 'jornal_que_saiu partido_fantasma atira em República de Exemplo');
  assert.equal(ataques[0].querySelectorAll('a').length, 0, 'veículo que saiu do mapa: o id, sem link e sem etiqueta');
  assert.equal(textoDe(ataques[1]), 'Fox News SO atira em player_fantasma');
  assert.equal(ataques[1].querySelectorAll('a').length, 2, 'o alvo que não existe não vira link');
  const eixo = m.um('#item-p1 .eixo');
  assert.equal(textoDe(eixo.querySelector('.eixo__cabeca')), 'tema_fantasma', 'tema fora da régua: o id, sem o texto do polo');
  assert.equal(/empurra para/.test(textoDe(eixo)), false);
  assert.match(textoDe(m.um('#item-p1 .placar-item__cabeca')), /^partido_fantasma \+ ganha força 2/);
  assert.match(textoDe(m.um('#item-p1 .dossie .vetor__cabeca')), /^player_fantasma desloca-se para partido_fantasma força 2 de 3 ato reversível tema_fantasma$/);
  assert.equal(m.todos('#item-p1 .dossie .vetor__cabeca a').length, 0);
  assert.deepEqual(textos(m.um('#item-p1 .marcas').children), ['GEOPOLÍTICA', 'CONFIANÇA ALTA', 'dominio_fantasma', 'Energia', 'CONTINUAÇÃO DE 01/10']);
  assert.equal(m.um('#item-p1 .marcas').children[2].getAttribute('class'), 'id-cru', 'domínio que não existe: sem link e sem etiqueta');
  assert.equal(m.um('#item-p1 .marcas').children[4].localName, 'span', 'data que não está no índice: sem link');
  assert.equal(textoDe(m.um('#item-p2 .marcas .id-cru')), 'ontem');
  /* a fonte leva o lado gravado no ataque do mesmo veículo (fer-07), cru como na linha do ataque */
  assert.match(textoDe(m.um('#item-p1 .dossie .fonte')), /^jornal_que_saiu partido_fantasma 19\/11/);
  const gatilhos = m.todos('#dominio-energia .gatilho__ref');
  assert.deepEqual(textos(gatilhos), ['indicador_fantasma', 'p9']);
  assert.equal(gatilhos[0].querySelectorAll('a').length + gatilhos[1].querySelectorAll('a').length, 0);
  assert.equal(textoDe(m.um('#dominio-alimentos .dominio__sem-preco')), 'sem dado de preço de: indicador_fantasma');
  assert.equal(textoDe(m.um('#ind-brent .ficha__pe .id-cru')), 'dominio_fantasma');
  assert.equal(textoDe(m.um('#s-vigiar .resposta__pe')), 'fonte (abre em nova aba) perguntado em 01/01, r2');
  assert.equal(m.todos('#s-vigiar .resposta')[0].querySelectorAll('a[href^="#"]').length, 0);
  assert.match(textoDe(m.um('#s-placar .placar__linha')), /^partido_fantasma partido_fantasma: saldo mais 4/);
  assert.equal(m.todos('#s-placar .placar__linha').length, 8, 'os 7 da régua mais o que ela não conhece');
  assert.equal(textoDe(m.todos('.novo-player .marcas')[1]), 'tipo_fantasma partido_fantasma time_fantasma time discutível');
});

test('referência quebrada: campos ausentes ou de tipo errado nunca derrubam o Painel', async () => {
  const torta = edicaoReal(DIA, (e) => {
    delete e.alerta.motivo;
    e.alerta.dominios[0].gatilhos = 'nenhum';
    e.alerta.dominios[1] = null;
    e.alerta.dominios[2].sem_preco = { a: 1 };
    e.indicadores[0].fonte = 'texto';
    e.indicadores[1].valor = '74,10';
    e.indicadores[2] = 7;
    e.principais[0].ataques = null;
    e.principais[0].fontes = [null, 'x', { url: 5 }];
    e.principais[0].vigiar = 'pergunta solta';
    e.principais[1].placar = [{ partido: 5, efeito: null, forca: 'muita' }];
    e.principais[2] = 'item torto';
    e.radar[0].ataque = [];
    e.radar[1].vetores = [{}];
    e.radar[2].id = 'ID INVÁLIDO';
    e.placar_do_dia.push('x', { partido: 'centrao' });
    e.novos_players = [{ dna: 'B', dna_fontes: [], duvidas: 'clima' }];
    e.errata = [{}, 'x'];
    e.respostas = [{}, null];
    e.bastidores = 'nada';
  });
  /* o índice é o de uma edição sã; só o arquivo da edição vem torto */
  const tabela = arquivos({ edicoes: [edicaoReal(DIA)] });
  tabela['edicoes/2026-11-19.json'] = torta;
  const m = await abre({ arquivos: tabela });
  assert.equal(textoDe(m.um('h1')), 'Edição de 19/11/2026');
  assert.equal(m.todos('main h2').length, 9);
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
  assert.equal(m.todos('.principal').length, 2);
  assert.equal(m.todos('.radar__item').length, 6);
  assert.equal(m.todos('.radar__item')[2].hasAttribute('id'), false, 'id fora da forma não vira id de elemento');
  assert.equal(textoDe(m.um('#ind-wti .ficha__valor')), 'sem dado', 'valor que não é número é "sem dado"');
});

test('filtro sem resultado: mensagem e botão "Limpar filtros"', async () => {
  const m = await abre({ hash: '#/?cat=ia&dom=alimentos' });
  const linhas = m.todos('.radar__item');
  assert.equal(linhas.filter(aVista).length, 0);
  const vazio = m.um('.filtros__vazio');
  assert.equal(aVista(vazio), true);
  assert.equal(textoDe(vazio), 'Nenhum item do radar com estes filtros. Limpar filtros');
  await m.clica(vazio.querySelector('button'));
  assert.equal(linhas.filter(aVista).length, 6);
  assert.equal(aVista(vazio), false);
  assert.equal(m.janela.location.hash, '#/');
});

test('edição nova: ao voltar para a aba, o índice é relido e o aviso oferece "Carregar"; o texto não troca sozinho', async () => {
  const m = await abre({ arquivos: arquivos({ edicoes: [edicaoReal(DIA)] }) });
  const pedidosDe = (caminho) => m.rede.pedidos.filter((p) => p.caminho === caminho).length;
  const voltaParaAba = async () => {
    m.documento.visibilityState = 'hidden';
    m.documento.dispatchEvent(new Evento('visibilitychange'));
    m.documento.visibilityState = 'visible';
    m.documento.dispatchEvent(new Evento('visibilitychange'));
    await m.assenta();
  };
  /* sai a edição de 20/11 */
  const nova = edicaoReal('2026-11-20', (e) => { e.resumo = 'A edição do dia seguinte.'; });
  m.rede.arquivos['edicoes/2026-11-20.json'] = nova;
  m.rede.arquivos['edicoes/indice.json'] = indiceDe([entradaDoIndice(edicaoReal(DIA)), entradaDoIndice(nova)]);

  await voltaParaAba();
  assert.equal(pedidosDe('edicoes/indice.json'), 1, 'antes de 5 minutos, o índice não é relido');
  m.relogio.avanca(5 * MINUTO - 1000);
  await voltaParaAba();
  assert.equal(pedidosDe('edicoes/indice.json'), 1, 'aos 4min59s, ainda não');
  m.relogio.avanca(1000);
  await voltaParaAba();
  assert.equal(pedidosDe('edicoes/indice.json'), 2);
  const aviso = m.um('#avisos-gerais .aviso');
  assert.equal(textoDe(aviso), 'HÁ EDIÇÃO NOVA Saiu a edição de 20/11/2026. Carregar');
  assert.ok(aviso.classList.contains('aviso--edicao-nova'));
  assert.equal(textoDe(m.um('#anuncio')), 'HÁ EDIÇÃO NOVA. Saiu a edição de 20/11/2026.');
  assert.equal(textoDe(m.um('h1')), 'Edição de 19/11/2026', 'o texto nunca troca sozinho');
  await voltaParaAba();
  assert.equal(pedidosDe('edicoes/indice.json'), 2, 'no máximo uma vez a cada 5 minutos');

  await m.clica(aviso.querySelector('button'));
  assert.equal(textoDe(m.um('h1')), 'Edição de 20/11/2026');
  assert.equal(textoDe(m.um('.alerta__resumo')), 'A edição do dia seguinte.');
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
  assert.equal(pedidosDe('dados/players.json'), 2, 'players lidos de novo');
  assert.equal(pedidosDe('dados/vetores.json'), 2, 'vetores lidos de novo');
  assert.equal(pedidosDe('dados/regua.json'), 1, 'o resto fica na memória');
  assert.equal(pedidosDe('edicoes/indice.json'), 2, 'o índice novo já estava lido');
  assert.deepEqual(m.todos('a.vizinha').map((a) => a.getAttribute('href')), ['#/edicao/2026-11-19']);
});

test('edição nova: Painel atrasado com a aba sempre visível relê o índice pelo relógio, no máximo a cada 5 minutos', async () => {
  const m = await abre({ arquivos: arquivos({ edicoes: [edicaoReal(DIA)] }) });
  const pedidosDoIndice = () => m.rede.pedidos.filter((p) => p.caminho === 'edicoes/indice.json').length;
  const anda = async (ms) => { m.relogio.avanca(ms); await m.assenta(); };
  /* a edição foi gerada 18 minutos antes de abrir: em dia até 25h42 depois */
  await anda(25 * HORA + 41 * MINUTO);
  assert.equal(pedidosDoIndice(), 1, 'em dia, o relógio não relê o índice');
  await anda(2 * MINUTO);
  assert.deepEqual(textos(m.todos('#carimbo .placa')), ['ATRASADA']);
  assert.equal(pedidosDoIndice(), 2, 'atrasada: o relógio relê');
  assert.equal(m.todos('#avisos-gerais .aviso--edicao-nova').length, 0, 'índice igual: sem aviso');
  /* sai a edição de 20/11 */
  const nova = edicaoReal('2026-11-20');
  m.rede.arquivos['edicoes/2026-11-20.json'] = nova;
  m.rede.arquivos['edicoes/indice.json'] = indiceDe([entradaDoIndice(edicaoReal(DIA)), entradaDoIndice(nova)]);
  await anda(4 * MINUTO);
  assert.equal(pedidosDoIndice(), 2, 'antes de 5 minutos, não relê');
  await anda(MINUTO);
  assert.equal(pedidosDoIndice(), 3);
  assert.equal(textoDe(m.um('#avisos-gerais .aviso--edicao-nova')), 'HÁ EDIÇÃO NOVA Saiu a edição de 20/11/2026. Carregar');
  assert.equal(textoDe(m.um('h1')), 'Edição de 19/11/2026', 'o texto nunca troca sozinho');
  await anda(30 * MINUTO);
  assert.equal(pedidosDoIndice(), 3, 'com o aviso na tela, o relógio para de reler (e de anunciar)');
  assert.equal(m.todos('#avisos-gerais .aviso--edicao-nova').length, 1);
});

test('edição nova: com a aba escondida, o relógio da edição atrasada não relê o índice', async () => {
  const m = await abre({ arquivos: arquivos({ edicoes: [edicaoReal(DIA)] }) });
  m.documento.visibilityState = 'hidden';
  m.relogio.avanca(28 * HORA);
  await m.assenta();
  assert.deepEqual(textos(m.todos('#carimbo .placa')), ['ATRASADA']);
  assert.equal(m.rede.pedidos.filter((p) => p.caminho === 'edicoes/indice.json').length, 1);
});

test('edição nova: a edição em tela mudou de gerada_em (uma falha trocada por edição de verdade)', async () => {
  const falha = edicaoFalha(DIA, null);
  const m = await abre({ arquivos: arquivos({ edicoes: [falha] }) });
  assert.deepEqual(textos(m.todos('#carimbo .placa')), ['SEM EDIÇÃO']);
  const real = edicaoReal(DIA, (e) => { e.gerada_em = '2026-11-19T23:40:00Z'; });
  m.rede.arquivos['edicoes/2026-11-19.json'] = real;
  m.rede.arquivos['edicoes/indice.json'] = indiceDe([entradaDoIndice(real)]);
  m.relogio.avanca(6 * MINUTO);
  m.documento.dispatchEvent(new Evento('visibilitychange'));
  await m.assenta();
  assert.equal(textoDe(m.um('#avisos-gerais .aviso')), 'HÁ EDIÇÃO NOVA Saiu a edição de 19/11/2026. Carregar');
  assert.deepEqual(textos(m.todos('#carimbo .placa')), ['SEM EDIÇÃO'], 'ainda a falha, até o leitor mandar carregar');
  await m.clica(m.um('#avisos-gerais .aviso button'));
  assert.equal(m.todos('.principal').length, 3);
  assert.match(textoDe(m.um('.carimbo__texto')), /GERADA 20h40 \(BRASÍLIA\)/);
});

test('edição nova: lendo uma edição antiga, "Carregar" leva ao Painel; sem novidade, nada aparece', async () => {
  const m = await abre({ arquivos: duasEdicoes(), hash: '#/edicao/2026-11-18' });
  m.relogio.avanca(6 * MINUTO);
  m.documento.dispatchEvent(new Evento('visibilitychange'));
  await m.assenta();
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0, 'índice igual: sem aviso');

  const nova = edicaoReal('2026-11-20');
  m.rede.arquivos['edicoes/2026-11-20.json'] = nova;
  m.rede.arquivos['edicoes/indice.json'].edicoes.unshift(entradaDoIndice(nova));
  m.relogio.avanca(6 * MINUTO);
  m.documento.dispatchEvent(new Evento('visibilitychange'));
  await m.assenta();
  assert.match(textoDe(m.um('#avisos-gerais .aviso')), /^HÁ EDIÇÃO NOVA Saiu a edição de 20\/11\/2026\./);
  /* o aviso de edição nova atravessa a troca de rota */
  await m.vai('#/metodo');
  assert.equal(m.todos('#avisos-gerais .aviso--edicao-nova').length, 1);
  await m.clica(m.um('#avisos-gerais .aviso button'));
  assert.equal(m.janela.location.hash, '#/');
  assert.equal(textoDe(m.um('h1')), 'Edição de 20/11/2026');
  assert.deepEqual(textos(m.todos('#carimbo .placa')), ['EM DIA']);
});

test('edição nova: aba escondida ou rede fora do ar não mexem na tela', async () => {
  const m = await abre({ arquivos: arquivos({ edicoes: [edicaoReal(DIA)] }) });
  m.relogio.avanca(10 * MINUTO);
  m.documento.visibilityState = 'hidden';
  m.documento.dispatchEvent(new Evento('visibilitychange'));
  await m.assenta();
  assert.equal(m.rede.pedidos.filter((p) => p.caminho === 'edicoes/indice.json').length, 1, 'aba escondida não relê');
  m.rede.arquivos['edicoes/indice.json'] = new Error('sem rede');
  m.documento.visibilityState = 'visible';
  m.documento.dispatchEvent(new Evento('visibilitychange'));
  await m.assenta();
  assert.equal(m.todos('#avisos-gerais .aviso').length, 0);
  assert.equal(textoDe(m.um('h1')), 'Edição de 19/11/2026');
  assert.equal(AGORA > 0, true);
});
