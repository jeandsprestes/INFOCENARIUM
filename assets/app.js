/* INFOCENARIUM · app.js
 *
 * Um arquivo só, script clássico, sem biblioteca e sem etapa de montagem.
 * Lê os arquivos JSON do site e monta as vistas dentro de <main>.
 *
 * Regras que valem para o arquivo inteiro:
 *  - Texto que vem de JSON só entra no documento por textContent,
 *    createTextNode ou setAttribute. Nunca como HTML.
 *  - Endereço que vem de JSON só vira link depois de passar por new URL e
 *    ter protocolo http: ou https:.
 *  - Valor de JSON só vira classe, id de elemento ou parte de endereço
 *    depois de conferido contra a forma de id (FORMA_ID).
 *  - Data AAAA-MM-DD é texto: corta-se o texto, sem passar por Date, que
 *    mudaria o dia pelo fuso.
 *  - O site não grava nada no aparelho e não envia nada.
 *
 * Seções deste arquivo:
 *   1. Constantes                    11. Edição: escolha, carga e estados
 *   2. Textos fixos                  12. Edição: cabeça (seção 00)
 *   3. Formas, datas e números       13. Edição: seções 01 a 03
 *   4. Construção do DOM             14. Edição: itens (04, 08 e dossiê)
 *   5. Rótulos das listas fechadas   15. Edição: seções 05, 06, 07 e 09
 *   6. Leitura dos arquivos          16. O que Arquivo, Régua e Método dividem
 *   7. Consultas aos dados de apoio  17. Arquivo
 *   8. Rotas e moldura da página     18. Régua
 *   9. Componentes pequenos          19. Método
 *  10. Dobras, dicas e teclado       20. Partida
 */
(function (janela) {
  'use strict';

  var doc = janela.document;

  /* ======================================================================
     1. Constantes
     ====================================================================== */

  var ESPACO_SVG = 'http://www.w3.org/2000/svg';
  var ARQ_INDICE = 'edicoes/indice.json';
  var ARQ_REGUA = 'dados/regua.json';
  var ARQ_PLAYERS = 'dados/players.json';
  var ARQ_VEICULOS = 'dados/veiculos.json';
  var ARQ_VETORES = 'dados/vetores.json';
  var ARQ_CATALOGO = 'dados/indicadores.json';
  var ARQ_FEED = 'feed.xml';

  var FORMA_DATA = /^\d{4}-\d{2}-\d{2}$/;
  var FORMA_DATA_HORA = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$/;
  var FORMA_ID = /^[a-z0-9_-]{1,64}$/;
  var FORMA_ARQUIVO_JSON = /^edicoes\/\d{4}-\d{2}-\d{2}\.json$/;
  var FORMA_ARQUIVO_MD = /^edicoes\/\d{4}-\d{2}-\d{2}\.md$/;
  var FORMA_ITEM_PRINCIPAL = /^p[1-9]\d?$/;
  var FORMA_ITEM_RADAR = /^r[1-9]\d?$/;

  var ESPERA_DEMORA_MS = 8000;            /* depois disso, "Está demorando" */
  var ATRASO_MS = 26 * 60 * 60 * 1000;    /* edição com mais de 26 horas */
  var RELEITURA_INDICE_MS = 5 * 60 * 1000; /* o índice é relido no máximo a cada 5 minutos */
  var PASSO_IDADE_MS = 60 * 1000;         /* a idade do carimbo se refaz a cada minuto */
  var DIAS_HISTORICO = 30;
  var NIVEL_MAXIMO = 5;
  var BARRA_PLACAR_PX = 72;               /* largura que vale o maior saldo do dia */
  var PISO_ESCALA_PLACAR = 3;

  var ABAS_REGUA = ['partidos', 'players', 'veiculos', 'vetores'];
  var SECOES_METODO = ['conflito', 'perguntas', 'regua', 'niveis', 'indicadores', 'rotina', 'limites'];

  var MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro',
    'Outubro', 'Novembro', 'Dezembro'];
  var MESES_ABERTOS = 2;                  /* no Arquivo, os 2 meses mais novos vêm abertos */
  var NIVEIS_MINIMOS = ['2', '3', '4', '5']; /* valores do filtro do Arquivo */
  var VETORES_POR_VEZ = 50;               /* linhas da aba Vetores a cada "Mostrar mais" */
  var VEICULOS_POR_FATIA = 24;            /* a lista de veículos é montada aos poucos */
  var BUSCA_MAXIMA = 64;                  /* o mesmo teto que a rota aceita em "q" */
  /* mini-linha: 120 x 28, com 4 de folga em cima e embaixo; a margem dos
     lados deixa o ponto final, de raio 4 mais anel de 2, caber inteiro */
  var MINI = { largura: 120, altura: 28, folga: 4, margem: 6 };
  /* siglas dos domínios na lista de edições do Arquivo: fixas no site */
  var SIGLAS_DOMINIO = { energia: 'ENE', alimentos: 'ALI', cambio: 'CAM', suprimentos: 'SUP', conflito: 'CON' };
  var CONFIANCAS = ['alta', 'media', 'baixa'];

  /* Parâmetros de consulta que cada rota aceita. O resto é ignorado. */
  var PARAMETROS = {
    edicao: ['cat', 'dom', 'partido'],
    arquivo: ['nivel'],
    partidos: [],
    players: ['partido', 'tipo', 'time', 'q'],
    veiculos: ['lado', 'fatos', 'tipo', 'q'],
    vetores: ['player'],
    metodo: []
  };

  /* ======================================================================
     2. Textos fixos (especificação do site, seção 8)
     ====================================================================== */

  var T = {
    marca: 'INFOCENARIUM',
    tituloBase: 'INFOCENARIUM · monitor geopolítico e de IA',
    vistas: { painel: 'Painel', arquivo: 'Arquivo', regua: 'Régua', metodo: 'Método' },
    novaAba: ' (abre em nova aba)',
    travessao: '—',
    separador: ' · ',

    carregando: 'Carregando edição…',
    demora: 'Está demorando. A conexão pode estar lenta.',
    tentar: 'Tentar de novo',
    carregar: 'Carregar',
    ver: 'Ver',
    verTabela: 'Ver tabela',
    esconderTabela: 'Esconder tabela',
    irMaisRecente: 'Ir para a mais recente',
    linkTexto: 'texto',
    linkJson: 'JSON',
    linkFeed: 'feed',

    placas: {
      emDia: 'EM DIA', atrasada: 'ATRASADA', reduzida: 'REDUZIDA',
      semEdicao: 'SEM EDIÇÃO', exemplo: 'EXEMPLO', arquivo: 'ARQUIVO'
    },

    avisos: {
      exemplo: ['EDIÇÃO DE EXEMPLO', 'Dados fictícios. Nada aqui aconteceu. Serve só para mostrar como o site funciona.'],
      semEdicao: 'SEM EDIÇÃO HOJE',
      atrasada: 'EDIÇÃO ATRASADA',
      reduzida: ['EDIÇÃO REDUZIDA', 'Há menos itens que o normal. Veja o que não deu para conferir em Bastidores.'],
      arquivo: 'EDIÇÃO DE ARQUIVO',
      corrigida: 'EDIÇÃO CORRIGIDA',
      errata: 'ERRATA',
      edicaoNova: 'HÁ EDIÇÃO NOVA',
      formato: ['FORMATO NOVO', 'Esta edição usa um formato mais novo que o site. Alguma parte pode não aparecer.'],
      rota: ['ENDEREÇO NÃO ENCONTRADO', 'Mostrando o Painel.'],
      semEdicaoNaData: 'NÃO HÁ EDIÇÃO DE ',
      mostrandoArquivo: 'Mostrando o Arquivo.',
      itemNaoEncontrado: 'ITEM NÃO ENCONTRADO',
      fichaNaoEncontrada: 'FICHA NÃO ENCONTRADA',
      apoio: 'DADOS DE APOIO INDISPONÍVEIS',
      regua: ['RÉGUA INDISPONÍVEL', 'Nomes e rótulos aparecem como identificadores.'],
      mapa: ['MAPA DE VEÍCULOS INDISPONÍVEL', 'Os veículos aparecem pelo identificador, sem lado.'],
      vazio: ['NENHUMA EDIÇÃO AINDA', 'A primeira sai às 18h de Brasília.'],
      falha: 'FALHA AO CARREGAR',
      rascunho: 'Mapa de veículos em rascunho, ainda sem revisão do dono.',
      verMapa: 'Ver o mapa.'
    },

    titulos: {
      hoje: 'HOJE', dominios: 'DOMÍNIOS', indicadores: 'INDICADORES', principais: 'PRINCIPAIS',
      placar: 'PLACAR DO DIA', vigiar: 'O QUE VIGIAR', movimentos: 'MOVIMENTOS',
      radar: 'RADAR', bastidores: 'BASTIDORES'
    },

    hoje: {
      de5: 'de 5',
      primeira: 'Primeira edição: sem comparação.',
      nenhumMudou: 'nenhum nível mudou.',
      motivo: 'Motivo:',
      fita: 'ALERTA, 30 DIAS',
      repetidos: 'NÍVEIS REPETIDOS DE ',
      semBase: 'NÍVEIS SEM BASE: AINDA NÃO HOUVE EDIÇÃO',
      semItens: 'Sem itens: a rotina não fechou a edição deste dia.'
    },

    dominios: {
      comoChega: 'COMO CHEGA AO BRASIL',
      gatilhos: 'GATILHOS DE HOJE',
      excecao: 'EXCEÇÃO',
      dicaExcecao: 'Fato fora da tabela de critérios, tratado como equivalente a este nível.',
      alivio: 'ALÍVIO',
      dicaAlivio: 'Acabou o estado que sustentava o nível. Por isso o domínio desce um degrau.',
      proximo: 'PRÓXIMO SINAL',
      mantido: 'MANTIDO DESDE ',
      semGatilhoNovo: 'Sem gatilho novo. O nível desce um degrau depois de 2 edições seguidas sem gatilho. Edição sem dado de preço não entra nessa conta.',
      nenhumGatilho: 'Nenhum gatilho hoje.',
      semPreco: 'sem dado de preço de: '
    },

    indicadores: {
      anterior: 'anterior',
      dicaAnterior: 'Variação sobre o ponto anterior da série.',
      seteDias: '7 dias',
      semDado: 'sem dado',
      gatilho: 'GATILHO',
      fonte: 'Fonte: ',
      fontePrevista: 'Fonte prevista: ',
      nenhum: 'Nenhum indicador nesta edição.'
    },

    itens: {
      conflito: 'CONFLITO DE INTERESSE',
      continuacao: 'CONTINUAÇÃO DE ',
      atirou: 'Atirou:',
      placar: 'Placar:',
      narrativa: 'narrativa',
      semGanhador: 'sem ganhador',
      semAlvo: 'sem alvo',
      dicaSemAlvo: 'O texto só relata, ou só promove alguém. Não ataca ninguém.',
      abrir: 'Abrir dossiê',
      fechar: 'Fechar dossiê',
      aconteceu: 'O QUE ACONTECEU',
      naoConfirmado: 'NÃO CONFIRMADO',
      quemAtirou: 'QUEM ATIROU',
      deixouDeFora: 'Deixou de fora: ',
      lerNoVeiculo: 'ler no veículo',
      ladoIncerto: 'LADO INCERTO',
      fogoAmigo: 'FOGO AMIGO',
      foraDoMapa: 'FORA DO MAPA',
      realmente: 'O QUE ESTÁ REALMENTE ACONTECENDO',
      naPratica: 'NA PRÁTICA',
      atoNaRegua: 'O ATO NA RÉGUA',
      empurra: 'empurra para:',
      quemGanha: 'QUEM GANHA E QUEM PERDE',
      movimentos: 'MOVIMENTOS',
      prova: 'prova',
      anulado: 'ANULADO',
      fonteCorrecao: 'fonte da correção',
      preparo: 'PARA QUEM SE PREPARA',
      noBrasil: 'No Brasil: ',
      dominios: 'Domínios: ',
      vigiar: 'Vigiar: ',
      perguntaChave: 'PERGUNTA-CHAVE',
      dicaPerguntaChave: 'É a pergunta que derruba esta leitura. O INFOCENARIUM responde quando a data vencer.',
      fontes: 'FONTES',
      primaria: 'FONTE PRIMÁRIA',
      avisoConflito: 'Aviso: o INFOCENARIUM é escrito por um modelo de IA da Anthropic, que é do setor de IA e pode ser parte ou concorrente nesta notícia.',
      conflitoConfianca: 'Por isso a confiança deste item não passa de média.',
      conflitoVinculo: 'Este item envolve nomes da lista de conflito da régua: ',
      verMetodo: 'Ver Método.',
      semPlacar: 'Nenhum partido ganhou ou perdeu de forma medida.',
      semVetores: 'Nenhum movimento neste item.',
      semEixo: 'Nenhum ato desta notícia mexe num tema da régua.',
      semDominios: 'Não mexe nos cinco domínios.'
    },

    placar: {
      intro: 'Saldo é a soma das forças do dia: ganhar soma, perder subtrai. Ganho só de narrativa não entra no saldo: aparece à parte. Barra à direita, ganhou. À esquerda, perdeu.',
      semMovimento: 'sem movimento hoje',
      trintaDias: '30 dias ',
      vazio: 'Nenhum partido ganhou ou perdeu hoje.'
    },

    vigiar: {
      sinais: 'SINAIS',
      intro: 'Sinais que mudariam o quadro. Cada pergunta tem data.',
      respostas: 'RESPOSTAS',
      introRespostas: 'O INFOCENARIUM responde às próprias perguntas quando a data vence.',
      fonte: 'fonte',
      vazio: 'Nenhuma pergunta venceu hoje.'
    },

    movimentos: {
      intro: 'Ninguém muda de partido. O vetor mostra para onde o player se desloca.',
      novoPlayer: 'NOVO PLAYER',
      porQueEntrou: 'Por que entrou: ',
      fontesPosicoes: 'Fontes das posições: ',
      timeDiscutivel: 'time discutível',
      emDuvida: 'posição em dúvida',
      verFicha: 'Ver a ficha na Régua',
      vazio: 'Nenhum movimento hoje.'
    },

    radar: {
      todas: 'Todas',
      porDominio: 'Filtrar por domínio',
      todosDominios: 'Todos os domínios',
      porPartido: 'Filtrar por partido',
      todosPartidos: 'Todos os partidos',
      limpar: 'Limpar filtros',
      vazio: 'Nenhum item do radar com estes filtros.'
    },

    bastidores: {
      veiculos: 'veículos consultados',
      feedsOk: 'feeds lidos',
      feedsFalhos: 'feeds que falharam',
      paginas: 'páginas lidas',
      buscas: 'buscas',
      minutos: 'minutos de trabalho',
      injecoes: 'páginas descartadas por trazer ordens ao agente',
      limites: 'O QUE NÃO DEU PARA CONFERIR',
      candidatos: 'ATORES SEM FICHA NA RÉGUA',
      sugeridos: 'VEÍCULOS QUE FIZERAM FALTA',
      nenhum: 'Nenhum.'
    },

    /* ----- Arquivo (seção 8.5) ----- */
    arquivo: {
      historico: 'HISTÓRICO',
      ultimos: 'ÚLTIMOS 30 DIAS',
      semExemplo: 'Edições de exemplo ficam fora do histórico.',
      alerta: 'Alerta geral',
      dominios: 'Domínios',
      partidos: 'Saldo dos partidos',
      atos: 'Atos por tema',
      introAtos: 'Quantas notícias trouxeram um ato (lei, decreto, decisão, compra) que empurra cada tema, e para que lado.',
      tema: 'Tema',
      polo: 'Polo',
      colAtos: 'Atos',
      semAtos: 'Nenhum ato registrado em 30 dias.',
      desenhoDepois: 'O desenho aparece a partir da 2ª edição.',
      semPrecos: 'Nenhum preço medido nos últimos 30 dias.',
      indicadores: 'Indicadores',
      primeiro: 'primeiro',
      ultimo: 'último',
      edicoes: 'EDIÇÕES',
      nivelMinimo: 'Nível mínimo',
      todosNiveis: 'Todos os níveis',
      ouMais: ' ou mais',
      so5: 'Só 5',
      data: 'Data',
      estado: 'Estado',
      nivel: 'Nível',
      resumo: 'Resumo',
      corrigida: 'corrigida em ',
      atualizado: 'Índice atualizado em ',
      vazio: 'Nenhuma edição no arquivo.'
    },

    /* ----- Régua (seção 8.6) ----- */
    regua: {
      abas: { partidos: 'Partidos', players: 'Players', veiculos: 'Veículos', vetores: 'Vetores' },
      comoLer: 'COMO LER',
      virada: 'virada: antes e agora',
      votoTipico: 'voto típico',
      semVoto: 'Sem voto típico: acompanha bancadas diferentes.',
      dianteDaOrdem: 'diante da ordem',
      players: 'players',
      saldo: 'saldo em 30 dias',
      times: 'TIMES',
      buscarPlayer: 'Buscar player',
      todosTipos: 'Todos os tipos',
      todosTimes: 'Todos os times',
      daRegua: 'Da régua original',
      entrou: 'Entrou em ',
      pelaRotina: ', pela rotina',
      emDuvidaEm: 'posição em dúvida em: ',
      vetoresRegistrados: 'Vetores registrados',
      rascunho: ['MAPA EM RASCUNHO', 'Mapa em rascunho, ainda sem revisão do dono. O lado de cada veículo é classificação editorial.'],
      revisado: 'Mapa revisado em ',
      ladoEFatos: 'Lado e fatos são coisas separadas: um veículo pode acertar o fato e servir a um lado pelo que escolhe cobrir.',
      buscarVeiculo: 'Buscar veículo',
      todosLados: 'Todos os lados',
      qualquerConfiabilidade: 'Qualquer confiabilidade',
      lado: 'lado',
      confiancaNoLado: 'confiança no lado',
      confiabilidade: 'confiabilidade nos fatos',
      pais: 'País',
      idiomas: 'Idiomas',
      sites: 'Sites',
      controle: 'Quem controla',
      serveA: 'Serve a',
      alvos: 'Alvos',
      porQueLado: 'Por que este lado',
      sobreFatos: 'Sobre os fatos',
      uso: 'Uso no monitor',
      feeds: 'Feeds',
      conferido: 'conferido',
      naoConferido: 'não conferido',
      nenhumFeed: 'Nenhum feed.',
      registro: 'REGISTRO DE VETORES',
      soCresce: 'O registro só cresce. Vetor errado não se apaga: é anulado, e fica à vista.',
      player: 'Player',
      de: 'De',
      para: 'Para',
      forca: 'Força',
      porQue: 'Por quê',
      prova: 'Prova',
      item: 'Item',
      mais50: 'Mostrar mais 50',
      semVetores: 'Nenhum vetor registrado ainda.',
      nadaEncontrado: 'Nada encontrado para "'
    },

    /* ----- Método (seção 8.7): textos integrais, palavra por palavra ----- */
    metodo: {
      titulos: {
        conflito: 'AVISO DE CONFLITO DE INTERESSE', perguntas: 'AS QUATRO PERGUNTAS', regua: 'A RÉGUA',
        niveis: 'NÍVEIS DE ALERTA', indicadores: 'DE ONDE VEM CADA NÚMERO', rotina: 'COMO A EDIÇÃO É FEITA',
        limites: 'LIMITES E CORREÇÕES'
      },
      conflito: [
        'As análises do INFOCENARIUM são escritas por um modelo de inteligência artificial (IA): o Claude, da empresa Anthropic. A Anthropic é um dos players da régua do INFOCENARIUM. Ou seja: quem escreve é parte interessada em uma das disputas que este site acompanha, a da IA.',
        'O risco é concreto. O modelo pode poupar quem o fez, pesar a mão contra concorrentes ou tratar como neutra a visão de mundo da empresa.',
        'O que o INFOCENARIUM faz para reduzir o risco:'
      ],
      conflitoMedidas: [
        'Leva a marca CONFLITO DE INTERESSE todo item de IA. Leva também todo item que tem alguém da lista abaixo como alvo ou como player em movimento, que cita um termo da lista, ou que usa fonte de veículo ligado à Anthropic. A marca é ligada por programa, e ninguém a desliga.',
        'Nesses itens, a confiança nunca passa de média.',
        'Nesses itens, um vetor só entra com prova em fonte primária.',
        'Quando o item envolve um nome ou um termo da lista, ou um veículo ligado à Anthropic, as fontes vêm de veículos de pelo menos 2 partidos.',
        'Toda afirmação traz o link da fonte, e o placar diz que tipo de evidência sustenta cada ganho ou perda.',
        'A régua, o mapa de veículos, os critérios de alerta e o código são públicos.'
      ],
      conflitoLimite: 'O que isso não resolve: nenhuma pessoa revisa a edição antes de ela sair. Leia com desconfiança e confira as fontes.',
      verAnthropic: 'Ver a ficha da Anthropic na Régua.',
      lista: 'A LISTA QUE LIGA A MARCA',
      listaPlayers: 'Players: ',
      listaTermos: 'Termos: ',
      perguntasIntro: 'Toda edição responde quatro perguntas.',
      perguntas: [
        'O que aconteceu de fato? O fato verificável, separado do enquadramento.',
        'Quem atirou? Toda notícia é lida como um ataque lançado por um veículo. O INFOCENARIUM diz de que lado o veículo está, quem é o alvo e qual é o enquadramento. Fato verdadeiro também é usado como arma: "ataque" não quer dizer "mentira".',
        'Quem ganha e quem perde na prática? Por partido, olhando por cima das narrativas: o que mudou em preço, tropa, contrato, lei, voto ou sanção.',
        'O que isso muda para quem se prepara? O nível de alerta e o efeito em energia, alimentos, câmbio, cadeias de suprimento e risco de conflito.'
      ],
      regua: 'A régua classifica cada player em 5 temas (7 posições) e em um partido. Ninguém muda de partido. Quando uma notícia mostra movimento, o INFOCENARIUM registra um vetor: para onde o player se desloca, com que força e por causa de quê. A classificação é editorial.',
      vejaRegua: 'Veja a Régua.',
      niveis: 'O nível vai de 1 a 5 e só muda com gatilho concreto e citado. O nível geral é o maior entre os cinco domínios. Um domínio sobe no dia em que um critério da tabela é cumprido. Sem gatilho novo, ele se mantém por 2 edições e depois desce um degrau por vez. Dia em que faltou o dado de preço do domínio não entra nessa conta: o INFOCENARIUM não mediu. Um nível 4 ou 5 também desce um degrau quando acaba o estado que o sustentava: é o gatilho de alívio. Alta de preço de nível 3 ou 4 só vale com uma segunda fonte que confirme; sem ela, vale como nível 2. Sem alarmismo: ameaça não é fato consumado.',
      provaMinima: 'prova mínima',
      eventos: 'eventos',
      precos: 'gatilhos de preço',
      comoChega: 'como chega ao Brasil',
      ouMais: '% ou mais',
      indicadores: 'Os indicadores vêm de fontes públicas e gratuitas. Cada ficha do Painel traz o link da fonte usada no dia. Número antigo aparece com a data. Número que não veio aparece como "sem dado", com o nome da fonte prevista, sem link.',
      alimentaGatilho: 'alimenta gatilho',
      soContexto: 'só contexto',
      faixa: 'faixa aceita: de ',
      faixaAte: ' a ',
      casas: 'casas decimais',
      leitor: 'leitor',
      convertido: 'número convertido: × ',
      rotina: [
        'Todo dia, às 18h de Brasília, um agente de IA roda sozinho, lê as notícias do dia nos veículos do mapa e escreve a edição. Um programa calcula os níveis de alerta, o placar do dia e a marca de conflito de interesse. Um validador automático confere tudo antes de publicar.',
        'Estados: completa; reduzida (menos itens que o normal); sem edição (a rotina não fechou o dia).',
        'Confiança: alta pede fontes de veículos dos dois campos (o da ordem e o da contestação) e uma fonte forte. Média pede 2 fontes de veículos de partidos diferentes, ou uma fonte forte. O resto é baixa. Fonte forte é veículo confiável nos fatos, ou documento primário de site oficial.',
        'Placar: o saldo de um partido soma só o que tem evidência material. Ganho de narrativa é contado à parte e vale no máximo força 1.',
        'Os quadros abaixo vêm direto da régua: os campos, a escala de força, os tipos de evidência, quando um time avança e que sites valem como fonte primária.'
      ],
      quadros: {
        campos: 'CAMPOS', forca: 'FORÇA', evidencia: 'EVIDÊNCIA', times: 'QUANDO UM TIME AVANÇA', primaria: 'FONTE PRIMÁRIA'
      },
      sitesBrasil: 'Sites oficiais do Brasil:',
      sitesOutros: 'Outros sites oficiais:',
      naoERecomendacao: 'O INFOCENARIUM não é recomendação de investimento, nem orientação de saúde ou de segurança.',
      limites: 'O agente pode errar. Página da web é tratada como dado, nunca como ordem. Edição publicada não muda: a correção sai na errata de uma edição seguinte, e a edição antiga ganha o aviso "corrigida". Vetor errado não se apaga: é anulado e fica riscado no registro. Quando vence a data de uma pergunta-chave, a edição do dia responde se a leitura se confirmou. O lado de cada veículo é classificação editorial; enquanto o mapa não for revisado, ele aparece marcado como rascunho. Este site não usa cookies, não guarda nada no seu aparelho e não carrega nada de terceiros.'
    }
  };

  /* ======================================================================
     3. Formas, datas e números
     ====================================================================== */

  function ehObjeto(v) {
    return v !== null && typeof v === 'object' && !Array.isArray(v);
  }

  function ehTexto(v) {
    return typeof v === 'string';
  }

  function ehNumero(v) {
    return typeof v === 'number' && isFinite(v);
  }

  /* Lista de verdade ou lista vazia: campo ausente ou torto nunca dá erro. */
  function lista(v) {
    return Array.isArray(v) ? v : [];
  }

  /* Texto para a tela: número vira texto, o resto que não é texto vira vazio. */
  function texto(v) {
    if (ehTexto(v)) { return v; }
    if (ehNumero(v)) { return String(v); }
    return '';
  }

  function ehId(v) {
    return ehTexto(v) && FORMA_ID.test(v);
  }

  function ehData(v) {
    if (!ehTexto(v) || !FORMA_DATA.test(v)) { return false; }
    var mes = Number(v.slice(5, 7));
    var dia = Number(v.slice(8, 10));
    return mes >= 1 && mes <= 12 && dia >= 1 && dia <= 31;
  }

  /* "2026-11-19" vira "19/11". O que não é data aparece como veio. */
  function dataCurta(data) {
    return ehData(data) ? data.slice(8, 10) + '/' + data.slice(5, 7) : texto(data);
  }

  /* "2026-11-19" vira "19/11/2026". */
  function dataLonga(data) {
    return ehData(data) ? dataCurta(data) + '/' + data.slice(0, 4) : texto(data);
  }

  /* Número do dia, contado em dias corridos, só com conta de inteiros. */
  function numeroDoDia(data) {
    var ano = Number(data.slice(0, 4));
    var mes = Number(data.slice(5, 7));
    var dia = Number(data.slice(8, 10));
    if (mes <= 2) { ano -= 1; }
    var era = Math.floor(ano / 400);
    var anoDaEra = ano - era * 400;
    var diaDoAno = Math.floor((153 * (mes + (mes > 2 ? -3 : 9)) + 2) / 5) + dia - 1;
    var diaDaEra = anoDaEra * 365 + Math.floor(anoDaEra / 4) - Math.floor(anoDaEra / 100) + diaDoAno;
    return era * 146097 + diaDaEra - 719468;
  }

  function dois(n) {
    return n < 10 ? '0' + n : String(n);
  }

  /* O caminho de volta: número do dia vira "AAAA-MM-DD". */
  function dataDoNumero(numero) {
    var z = numero + 719468;
    var era = Math.floor(z / 146097);
    var diaDaEra = z - era * 146097;
    var anoDaEra = Math.floor((diaDaEra - Math.floor(diaDaEra / 1460) + Math.floor(diaDaEra / 36524) - Math.floor(diaDaEra / 146096)) / 365);
    var diaDoAno = diaDaEra - (365 * anoDaEra + Math.floor(anoDaEra / 4) - Math.floor(anoDaEra / 100));
    var mp = Math.floor((5 * diaDoAno + 2) / 153);
    var dia = diaDoAno - Math.floor((153 * mp + 2) / 5) + 1;
    var mes = mp < 10 ? mp + 3 : mp - 9;
    var ano = anoDaEra + era * 400 + (mes <= 2 ? 1 : 0);
    var a = String(ano);
    while (a.length < 4) { a = '0' + a; }
    return a + '-' + dois(mes) + '-' + dois(dia);
  }

  /* Dias corridos de a até b (b menos a). */
  function diasEntre(a, b) {
    return numeroDoDia(b) - numeroDoDia(a);
  }

  /* Milissegundos de uma data-hora UTC do contrato; null se não é data-hora. */
  function instante(dataHora) {
    if (!ehTexto(dataHora) || !FORMA_DATA_HORA.test(dataHora)) { return null; }
    var ms = new Date(dataHora).getTime();
    return isFinite(ms) ? ms : null;
  }

  var formatoHora = null;

  /* Hora de Brasília de uma data-hora UTC: "18h14". */
  function horaDeBrasilia(dataHora) {
    var ms = instante(dataHora);
    if (ms === null) { return ''; }
    if (!formatoHora) {
      formatoHora = new Intl.DateTimeFormat('pt-BR', {
        timeZone: 'America/Sao_Paulo', hour: '2-digit', minute: '2-digit', hourCycle: 'h23'
      });
    }
    var hora = '';
    var minuto = '';
    formatoHora.formatToParts(new Date(ms)).forEach(function (parte) {
      if (parte.type === 'hour') { hora = parte.value; }
      if (parte.type === 'minute') { minuto = parte.value; }
    });
    return hora + 'h' + minuto;
  }

  var formatoDia = null;

  /* O dia em Brasília de uma data-hora UTC, já como texto AAAA-MM-DD.
     Às 2h30 UTC do dia 20 ainda é dia 19 em Brasília. */
  function diaDeBrasilia(dataHora) {
    var ms = instante(dataHora);
    if (ms === null) { return ''; }
    if (!formatoDia) {
      formatoDia = new Intl.DateTimeFormat('pt-BR', {
        timeZone: 'America/Sao_Paulo', year: 'numeric', month: '2-digit', day: '2-digit'
      });
    }
    var partes = { year: '', month: '', day: '' };
    formatoDia.formatToParts(new Date(ms)).forEach(function (parte) {
      if (parte.type === 'year' || parte.type === 'month' || parte.type === 'day') { partes[parte.type] = parte.value; }
    });
    return partes.year + '-' + partes.month + '-' + partes.day;
  }

  /* A hora de geração ao lado da data da edição: "18h14"; se a edição foi
     gerada em outro dia de Brasília (uma republicação), "24/11 11h38".
     Sem o dia, "ED. 23/11/2026 · GERADA 11h38" se lê como 23/11 às 11h38. */
  function horaComDia(dataHora, data) {
    var hora = horaDeBrasilia(dataHora);
    if (!hora) { return ''; }
    var dia = diaDeBrasilia(dataHora);
    if (!dia || dia === data) { return hora; }
    return dia.slice(8, 10) + '/' + dia.slice(5, 7) + ' ' + hora;
  }

  function agora() {
    return Date.now();
  }

  /* Idade do carimbo: AGORA, HÁ N MIN, HÁ N H, HÁ N DIAS. */
  function idade(ms) {
    if (ms === null) { return ''; }
    var minutos = Math.floor((agora() - ms) / 60000);
    if (minutos < 1) { return 'AGORA'; }
    if (minutos <= 59) { return 'HÁ ' + minutos + ' MIN'; }
    var horas = Math.floor(minutos / 60);
    if (horas <= 47) { return 'HÁ ' + horas + ' H'; }
    var dias = Math.floor(horas / 24);
    return dias === 1 ? 'HÁ 1 DIA' : 'HÁ ' + dias + ' DIAS';
  }

  function horasDesde(ms) {
    return Math.floor((agora() - ms) / 3600000);
  }

  function numeroBr(n, minimo, maximo) {
    return n.toLocaleString('pt-BR', { minimumFractionDigits: minimo, maximumFractionDigits: maximo });
  }

  /* Inteiro com separador de milhar: "1.234". O sinal de menos é o tipográfico. */
  function inteiro(n) {
    if (!ehNumero(n)) { return T.travessao; }
    return (n < 0 ? '−' : '') + numeroBr(Math.abs(n), 0, 0);
  }

  /* Valor de indicador. Com o catálogo, as casas dele (sem o campo, 2).
     Sem o catálogo, de 2 a 4 casas. */
  function valorDeIndicador(valor, casas) {
    if (!ehNumero(valor)) { return ''; }
    var sinal = valor < 0 ? '−' : '';
    if (casas === null) { return sinal + numeroBr(Math.abs(valor), 2, 4); }
    return sinal + numeroBr(Math.abs(valor), casas, casas);
  }

  /* Variação com sinal e 1 casa: "+1,3%", "−0,6%". Zero não leva sinal. */
  function variacao(v) {
    if (!ehNumero(v)) { return T.travessao; }
    var arredondado = Math.round(Math.abs(v) * 10) / 10;
    var sinal = arredondado === 0 ? '' : (v > 0 ? '+' : '−');
    return sinal + numeroBr(arredondado, 1, 1) + '%';
  }

  /* Saldo com sinal: "+4", "−2", "0". */
  function comSinal(n) {
    if (!ehNumero(n)) { return T.travessao; }
    if (n === 0) { return '0'; }
    return (n > 0 ? '+' : '−') + numeroBr(Math.abs(n), 0, 0);
  }

  /* O mesmo número, por extenso para o leitor de tela: "mais 2", "menos 1", "zero". */
  function sinalFalado(n) {
    if (!ehNumero(n) || n === 0) { return 'zero'; }
    return (n > 0 ? 'mais ' : 'menos ') + numeroBr(Math.abs(n), 0, 0);
  }

  function ordinal(n) {
    return n + 'ª';
  }

  /* Busca sem maiúscula e sem acento. */
  function semAcento(s) {
    return texto(s).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  }

  /* Número de um item: "p2" vira "2". */
  function numeroDoItem(id) {
    return texto(id).slice(1);
  }

  /* ======================================================================
     4. Construção do DOM
     Só createElement, createElementNS (ícones), createTextNode, textContent
     e setAttribute. Nada aqui interpreta texto como HTML.
     ====================================================================== */

  /* Põe filhos num elemento. Texto vira nó de texto; null é pulado.
     Entre dois elementos vizinhos entra um espaço: sem ele, o leitor de tela
     e quem copia o texto recebem "GEOPOLÍTICACONFIANÇA ALTA" numa palavra só.
     Dentro de flex, de grade e de tabela esse espaço não ocupa lugar. */
  function poe(pai) {
    for (var i = 1; i < arguments.length; i += 1) {
      var filho = arguments[i];
      if (filho === null || filho === undefined || filho === '') { continue; }
      if (Array.isArray(filho)) {
        poe.apply(null, [pai].concat(filho));
      } else if (ehTexto(filho) || ehNumero(filho)) {
        pai.appendChild(doc.createTextNode(String(filho)));
      } else {
        if (pai.lastChild && pai.lastChild.nodeType === 1) { pai.appendChild(doc.createTextNode(' ')); }
        pai.appendChild(filho);
      }
    }
    return pai;
  }

  /* Cria um elemento com classe e conteúdo (texto, nó ou lista dos dois). */
  function cria(tag, classe, conteudo) {
    var el = doc.createElement(tag);
    if (classe) { el.setAttribute('class', classe); }
    if (conteudo !== undefined) { poe(el, conteudo); }
    return el;
  }

  function atributos(el, mapa) {
    Object.keys(mapa).forEach(function (nome) {
      if (mapa[nome] !== null && mapa[nome] !== undefined) {
        el.setAttribute(nome, String(mapa[nome]));
      }
    });
    return el;
  }

  function limpa(el) {
    while (el.firstChild) { el.removeChild(el.firstChild); }
    return el;
  }

  function troca(el) {
    limpa(el);
    return poe.apply(null, arguments);
  }

  function esconde(el, sim) {
    if (sim) { el.setAttribute('hidden', ''); } else { el.removeAttribute('hidden'); }
    return el;
  }

  function porId(id) {
    return doc.getElementById(id);
  }

  /* Texto que só o leitor de tela lê. */
  function soLeitor(conteudo) {
    return cria('span', 'so-leitor', conteudo);
  }

  /* Parte que o leitor de tela pula, porque o texto escondido ao lado já diz. */
  function soVista(el) {
    el.setAttribute('aria-hidden', 'true');
    return el;
  }

  /* Elemento de desenho (SVG). O nome da marca é sempre fixo no código:
     svg e use nos ícones; svg, polyline e circle nas mini-linhas. */
  function desenho(marca, mapa) {
    var el = doc.createElementNS(ESPACO_SVG, marca);
    return mapa ? atributos(el, mapa) : el;
  }

  /* Ícone do bloco de símbolos do index.html. O nome é sempre fixo no código. */
  function icone(nome, classe) {
    var svg = desenho('svg', {
      'class': 'icone' + (classe ? ' ' + classe : ''), 'aria-hidden': 'true', focusable: 'false', viewBox: '0 0 16 16'
    });
    svg.appendChild(desenho('use', { href: '#' + nome }));
    return svg;
  }

  /* Seta entre origem e destino. É desenho: caractere de seta vira emoji em
     alguns celulares. O leitor de tela ouve a palavra. */
  function seta(palavra) {
    return [icone('i-estavel', 'icone--seta'), soLeitor(' ' + (palavra || 'para') + ' ')];
  }

  function separador() {
    return soVista(cria('span', 'separador', '·'));
  }

  /* Data em <time datetime>. O que não é data sai como texto simples. */
  function tempo(data, longa) {
    if (!ehData(data)) { return cria('span', 'id-cru', texto(data)); }
    var el = cria('time', '', longa ? dataLonga(data) : dataCurta(data));
    el.setAttribute('datetime', data);
    return el;
  }

  /* Endereço de JSON: só passa se abre como URL e é http: ou https:, sem
     barra invertida e sem usuário ou senha antes do @ (a mesma recusa da
     regra de URL do validador, como defesa em profundidade para uma edição
     que chegue sem passar por ele). Devolve o endereço já normalizado, ou null. */
  function enderecoSeguro(endereco) {
    if (!ehTexto(endereco) || endereco.indexOf('\\') !== -1) { return null; }
    var url;
    try {
      url = new URL(endereco);
    } catch (erro) {
      return null;
    }
    if (url.protocol !== 'http:' && url.protocol !== 'https:') { return null; }
    if (url.username || url.password) { return null; }
    return url.href;
  }

  /* Link externo: nova aba, rel fechado, ícone e aviso para o leitor de tela.
     Endereço recusado vira texto simples, sem href. */
  function linkExterno(endereco, conteudo, classe) {
    var href = enderecoSeguro(endereco);
    if (href === null) {
      return cria('span', classe || '', conteudo);
    }
    var a = cria('a', 'externo' + (classe ? ' ' + classe : ''), conteudo);
    a.setAttribute('href', href);
    a.setAttribute('target', '_blank');
    a.setAttribute('rel', 'noopener noreferrer');
    poe(a, icone('i-externo'), soLeitor(T.novaAba));
    return a;
  }

  /* Link para outra parte do site. O endereço é sempre montado aqui. */
  function linkInterno(hash, conteudo, classe) {
    var a = cria('a', classe || '', conteudo);
    a.setAttribute('href', hash);
    return a;
  }

  /* Link para um arquivo do próprio site (texto, JSON, feed). */
  function linkArquivo(caminho, conteudo) {
    var a = cria('a', '', conteudo);
    a.setAttribute('href', caminho);
    return a;
  }

  function botao(conteudo, classe, aoClicar) {
    var b = cria('button', 'botao' + (classe ? ' ' + classe : ''), conteudo);
    b.setAttribute('type', 'button');
    if (aoClicar) { b.addEventListener('click', aoClicar); }
    return b;
  }

  /* ----- endereços internos: cada id passa por encodeURIComponent ----- */

  function hashEdicao(data, item, consulta) {
    var hash = '#/edicao/' + encodeURIComponent(data);
    if (item) { hash += '/' + encodeURIComponent(item); }
    return hash + (consulta || '');
  }

  function hashRegua(aba, id) {
    return '#/regua/' + aba + (id ? '/' + encodeURIComponent(id) : '');
  }

  function hashMetodo(secao) {
    return '#/metodo' + (secao ? '/' + secao : '');
  }

  /* ======================================================================
     5. Rótulos das listas fechadas (especificação do site, seção 8.8)
     Valor desconhecido aparece cru.
     ====================================================================== */

  var ROTULOS = {
    categoria: { geopolitica: 'Geopolítica', ia: 'IA' },
    categoriaEtiqueta: { geopolitica: 'GEOPOLÍTICA', ia: 'IA' },
    tendencia: { subindo: 'subindo', estavel: 'estável', descendo: 'descendo' },
    efeito: { ganha: 'ganha', perde: 'perde' },
    forca: { '1': 'sinal', '2': 'ato reversível', '3': 'difícil de desfazer' },
    evidencia: {
      preco: 'preço', tropa: 'tropa', contrato: 'contrato', lei: 'lei',
      voto: 'voto', sancao: 'sanção', narrativa: 'só narrativa'
    },
    confianca: { alta: 'alta', media: 'média', baixa: 'baixa' },
    confiancaEtiqueta: { alta: 'CONFIANÇA ALTA', media: 'CONFIANÇA MÉDIA', baixa: 'CONFIANÇA BAIXA' },
    estado: { completa: 'completa', reduzida: 'reduzida', falha: 'sem edição' },
    resposta: { sim: 'SIM', nao: 'NÃO', sem_dado: 'SEM DADO' },
    modo: {
      feeds: 'coleta normal, pelos feeds dos veículos',
      busca: 'a coleta falhou: edição feita por busca'
    },
    frequencia: { diaria: 'diária', mensal: 'mensal' },
    tipoVeiculo: {
      agencia: 'agência', estatal: 'estatal', publico: 'público', privado: 'privado',
      plataforma: 'plataforma', oficial: 'oficial', think_tank: 'centro de estudos', dados: 'dados'
    },
    origem: { regua: 'da régua original', rotina: 'incluído pela rotina' },
    janela: { '1d': 'no dia', '7d': 'em 7 dias' }
  };

  /* O tema que não está na régua: o eixo manutenção x mudança. */
  var TEMA_ORDEM = { id: 'ordem', nome: 'Ordem mundial', sigla: 'ORDEM' };

  var ICONE_TENDENCIA = { subindo: 'i-sobe', estavel: 'i-estavel', descendo: 'i-desce' };
  /* marca de idioma de 2 ou 3 letras, com subtag opcional: "en", "pt-BR" */
  var FORMA_IDIOMA = /^[a-z]{2,3}(-[A-Za-z0-9]{2,8})?$/;

  /* Chave própria do objeto: valor de JSON nunca alcança o que o objeto herda. */
  function tem(objeto, chave) {
    return ehObjeto(objeto) && (ehTexto(chave) || ehNumero(chave)) &&
      Object.prototype.hasOwnProperty.call(objeto, chave);
  }

  function rotulo(nomeDaLista, valor) {
    var tabela = ROTULOS[nomeDaLista];
    return tem(tabela, valor) ? tabela[valor] : texto(valor);
  }

  /* ======================================================================
     6. Leitura dos arquivos
     Todo arquivo é lido com fetch e cache "no-cache", e fica na memória
     enquanto a página está aberta. Erro não fica na memória.
     ====================================================================== */

  var memoria = Object.create(null);   /* caminho -> promessa do JSON */
  var chegou = Object.create(null);    /* caminho -> true quando a leitura terminou bem */

  function le(caminho) {
    if (memoria[caminho]) { return memoria[caminho]; }
    var promessa = janela.fetch(caminho, { cache: 'no-cache' }).then(function (resposta) {
      if (!resposta || !resposta.ok) { throw new Error('resposta ' + (resposta ? resposta.status : 'vazia')); }
      return resposta.json();
    }).then(function (dados) {
      if (!ehObjeto(dados)) { throw new Error('formato'); }
      chegou[caminho] = true;
      return dados;
    });
    memoria[caminho] = promessa;
    promessa.catch(function () {
      if (memoria[caminho] === promessa) { delete memoria[caminho]; }
    });
    return promessa;
  }

  function esquece(caminho) {
    delete memoria[caminho];
    delete chegou[caminho];
  }

  /* "Tentar de novo": o que ainda não chegou é pedido outra vez. */
  function esquecePendentes() {
    Object.keys(memoria).forEach(function (caminho) {
      if (!chegou[caminho]) { delete memoria[caminho]; }
    });
  }

  /* Arquivo de apoio: se não vier, a edição aparece assim mesmo. */
  function leApoio(caminho) {
    return le(caminho).then(function (dados) { return dados; }, function () { return null; });
  }

  function formatoNovo(dados) {
    return ehObjeto(dados) && dados.versao !== undefined && dados.versao !== 1;
  }

  /* ----- índice das edições ----- */

  /* Entradas com data válida, mais nova primeiro, sem data repetida. */
  function entradasDoIndice(indice) {
    var vistas = Object.create(null);
    var entradas = lista(indice && indice.edicoes).filter(function (e) {
      if (!ehObjeto(e) || !ehData(e.data) || vistas[e.data]) { return false; }
      vistas[e.data] = true;
      return true;
    });
    entradas.sort(function (a, b) { return a.data < b.data ? 1 : (a.data > b.data ? -1 : 0); });
    return entradas;
  }

  function entradaDaData(entradas, data) {
    for (var i = 0; i < entradas.length; i += 1) {
      if (entradas[i].data === data) { return entradas[i]; }
    }
    return null;
  }

  function ehExemplo(entrada) {
    return ehObjeto(entrada) && entrada.exemplo === true;
  }

  /* A edição do Painel: a mais recente que não é de exemplo; se só houver a
     de exemplo, ela. */
  function maisRecente(entradas) {
    for (var i = 0; i < entradas.length; i += 1) {
      if (!ehExemplo(entradas[i])) { return entradas[i]; }
    }
    return entradas.length ? entradas[0] : null;
  }

  /* Edição anterior: a mais recente antes de data que não é falha nem exemplo. */
  function anteriorA(entradas, data) {
    for (var i = 0; i < entradas.length; i += 1) {
      var e = entradas[i];
      if (e.data < data && e.estado !== 'falha' && !ehExemplo(e)) { return e; }
    }
    return null;
  }

  /* Histórico: entradas nos 30 dias corridos que terminam em data, sem as
     de exemplo. Da mais antiga para a mais nova. */
  function historicoAte(entradas, data) {
    return entradas.filter(function (e) {
      if (ehExemplo(e)) { return false; }
      var distancia = diasEntre(e.data, data);
      return distancia >= 0 && distancia < DIAS_HISTORICO;
    }).reverse();
  }

  /* Vizinhas: uma entrada por vez, contando a falha e pulando a de exemplo. */
  function vizinhasDe(entradas, data) {
    var reais = entradas.filter(function (e) { return !ehExemplo(e); });
    var resultado = { anterior: null, seguinte: null };
    for (var i = 0; i < reais.length; i += 1) {
      if (reais[i].data === data) {
        resultado.seguinte = i > 0 ? reais[i - 1] : null;
        resultado.anterior = i < reais.length - 1 ? reais[i + 1] : null;
      }
    }
    return resultado;
  }

  /* O caminho do índice só vale na forma esperada. Fora dela, monta-se o
     caminho a partir da data. */
  function caminhoDaEdicao(entrada) {
    return ehTexto(entrada.arquivo) && FORMA_ARQUIVO_JSON.test(entrada.arquivo)
      ? entrada.arquivo : 'edicoes/' + entrada.data + '.json';
  }

  function caminhoDoTexto(entrada) {
    return ehTexto(entrada.texto) && FORMA_ARQUIVO_MD.test(entrada.texto)
      ? entrada.texto : 'edicoes/' + entrada.data + '.md';
  }

  /* ======================================================================
     7. Consultas aos dados de apoio
     Régua, players, veículos, vetores e catálogo viram tabelas por id.
     Id que não existe devolve null: quem mostra decide o que pôr no lugar.
     ====================================================================== */

  /* Lista de objetos vira tabela por id, sem herdar nada. */
  function tabelaPorId(itens, chave) {
    var tabela = Object.create(null);
    lista(itens).forEach(function (item) {
      var id = ehObjeto(item) ? item[chave || 'id'] : null;
      if ((ehTexto(id) || ehNumero(id)) && !(id in tabela)) { tabela[id] = item; }
    });
    return tabela;
  }

  function idsDe(itens) {
    return lista(itens).filter(function (item) { return ehObjeto(item) && ehTexto(item.id); })
      .map(function (item) { return item.id; });
  }

  /* Junta os arquivos de apoio que chegaram. Qualquer um pode ser null. */
  function montaApoio(regua, players, veiculos, vetores, catalogo) {
    var r = ehObjeto(regua) ? regua : {};
    var registro = lista(ehObjeto(vetores) ? vetores.vetores : null).filter(ehObjeto);
    var anulacoes = Object.create(null);
    registro.forEach(function (entrada) {
      if (ehTexto(entrada.anula) && !(entrada.anula in anulacoes)) { anulacoes[entrada.anula] = entrada; }
    });
    return {
      temRegua: ehObjeto(regua),
      temPlayers: ehObjeto(players),
      temMapa: ehObjeto(veiculos),
      temRegistro: ehObjeto(vetores),
      temCatalogo: ehObjeto(catalogo),
      regua: r,
      partidos: tabelaPorId(r.partidos),
      ordemPartidos: idsDe(r.partidos),
      temas: tabelaPorId(r.temas),
      ordemTemas: idsDe(r.temas),
      dominios: tabelaPorId(r.dominios),
      ordemDominios: idsDe(r.dominios),
      niveis: tabelaPorId(r.niveis_alerta, 'nivel'),
      forcas: tabelaPorId(r.forcas, 'forca'),
      tipos: tabelaPorId(r.tipos),
      times: tabelaPorId(r.times),
      players: tabelaPorId(ehObjeto(players) ? players.players : null),
      veiculos: tabelaPorId(ehObjeto(veiculos) ? veiculos.veiculos : null),
      /* rascunho enquanto revisado_em não traz uma data (null ou ausente) */
      mapaRascunho: ehObjeto(veiculos) && !ehData(veiculos.revisado_em),
      registro: registro,
      vetoresPorId: tabelaPorId(registro),
      anulacoes: anulacoes,
      catalogo: tabelaPorId(ehObjeto(catalogo) ? catalogo.indicadores : null),
      ordemCatalogo: idsDe(ehObjeto(catalogo) ? catalogo.indicadores : null)
    };
  }

  function busca(tabela, id) {
    return (ehTexto(id) || ehNumero(id)) && id in tabela ? tabela[id] : null;
  }

  function nivelValido(n) {
    return ehNumero(n) && n >= 1 && n <= NIVEL_MAXIMO && Math.floor(n) === n;
  }

  /* Rótulo do nível. Sem a régua: "NÍVEL N". */
  function rotuloDoNivel(apoio, nivel) {
    var linha = busca(apoio.niveis, nivel);
    return linha && ehTexto(linha.rotulo) ? linha.rotulo : 'NÍVEL ' + texto(nivel);
  }

  function nomeDoDominio(apoio, id) {
    var d = busca(apoio.dominios, id);
    return d && ehTexto(d.nome) ? d.nome : texto(id);
  }

  function nomeDaForca(apoio, forca) {
    var linha = busca(apoio.forcas, forca);
    /* força ausente fica vazia: String() poria "undefined" na tela */
    return linha && ehTexto(linha.nome) ? linha.nome : rotulo('forca', texto(forca));
  }

  /* Tema da régua, ou o tema extra "ordem". null se não existe. */
  function temaDe(apoio, id) {
    if (id === TEMA_ORDEM.id) { return TEMA_ORDEM; }
    return busca(apoio.temas, id);
  }

  /* Player: da régua ou, como alvo, o player novo desta edição. */
  function playerDe(contexto, id) {
    var p = busca(contexto.apoio.players, id);
    if (p) { return p; }
    var novos = lista(contexto.edicao.novos_players);
    for (var i = 0; i < novos.length; i += 1) {
      if (ehObjeto(novos[i]) && novos[i].id === id) { return novos[i]; }
    }
    return null;
  }

  /* A anulação de um vetor, se houver no registro. */
  function anulacaoDe(apoio, idDoVetor) {
    return busca(apoio.anulacoes, idDoVetor);
  }

  /* Entrada de anulação é a que traz o campo anula. Ela nunca é um vetor,
     mesmo quando o campo vem torto e não anula nada. */
  function ehAnulacao(entrada) {
    return tem(entrada, 'anula');
  }

  /* Quantas vezes o player já se moveu para o mesmo destino nos 30 dias até
     a edição, contando o próprio vetor e sem contar os anulados. */
  function reincidencia(contexto, vetor, idDoVetor) {
    var vezes = 1;
    contexto.apoio.registro.forEach(function (entrada) {
      if (ehAnulacao(entrada) || entrada.id === idDoVetor) { return; }
      if (entrada.player !== vetor.player || entrada.para !== vetor.para) { return; }
      if (!ehData(entrada.data) || anulacaoDe(contexto.apoio, entrada.id)) { return; }
      var distancia = diasEntre(entrada.data, contexto.data);
      if (distancia >= 0 && distancia < DIAS_HISTORICO) { vezes += 1; }
    });
    return vezes;
  }

  /* ======================================================================
     8. Rotas e moldura da página
     ====================================================================== */

  /* O que o site sabe neste momento. Nada disto vai para o aparelho. */
  var estado = {
    pedido: 0,             /* número da carga em curso; carga antiga é descartada */
    rota: null,
    primeiraRota: true,
    indice: null,          /* último edicoes/indice.json lido */
    indiceLidoEm: 0,
    quadro: null,          /* a edição em tela: contexto e referências */
    relogioDemora: null,
    relogioIdade: null,
    dobras: [],
    dicaSobPonteiro: null,
    avisosGerais: Object.create(null),
    enderecoDaCarga: null, /* o endereço da última carga pedida */
    fechaDicaDaVista: null, /* fecha a dica da fita do Arquivo, que não tem quadro */
    regua: null,           /* a aba da Régua em tela: { aba, pronta, aplica } */
    contador: 0
  };

  function rotaDesconhecida() {
    return { vista: 'painel', tipo: 'edicao', data: null, item: null, consulta: Object.create(null), desconhecida: true };
  }

  /* "a=1&b=2" vira tabela, só com os parâmetros que a rota aceita.
     Valor vazio, longo demais ou torto é ignorado. */
  function interpretaConsulta(bruta, aceitos) {
    var consulta = Object.create(null);
    if (!bruta) { return consulta; }
    bruta.split('&').forEach(function (par) {
      var corte = par.indexOf('=');
      if (corte < 1) { return; }
      var nome = par.slice(0, corte);
      var valor;
      try {
        valor = decodeURIComponent(par.slice(corte + 1).replace(/\+/g, ' '));
      } catch (erro) {
        return;
      }
      if (aceitos.indexOf(nome) === -1 || nome in consulta) { return; }
      if (valor === '' || valor.length > 64) { return; }
      /* só a busca é texto livre; o resto é id ou número */
      if (nome !== 'q' && !ehId(valor)) { return; }
      consulta[nome] = valor;
    });
    return consulta;
  }

  /* Lê o endereço depois de "#/" e devolve a rota. Tudo o que foge da
     tabela de rotas é "qualquer outra": Painel, com aviso. */
  function interpretaRota(hash) {
    var bruto = ehTexto(hash) ? hash : '';
    if (bruto === '' || bruto === '#') { bruto = '#/'; }
    if (bruto.slice(0, 2) !== '#/') { return rotaDesconhecida(); }
    var resto = bruto.slice(2);
    var corte = resto.indexOf('?');
    var caminho = corte === -1 ? resto : resto.slice(0, corte);
    var consultaBruta = corte === -1 ? '' : resto.slice(corte + 1);
    var partes = caminho === '' ? [] : caminho.split('/');
    try {
      partes = partes.map(function (parte) { return decodeURIComponent(parte); });
    } catch (erro) {
      return rotaDesconhecida();
    }
    var n = partes.length;
    var cabeca = n ? partes[0] : '';

    if (n === 0) {
      return { vista: 'painel', tipo: 'edicao', data: null, item: null, consulta: interpretaConsulta(consultaBruta, PARAMETROS.edicao) };
    }
    if (cabeca === 'edicao' && (n === 2 || n === 3) && ehData(partes[1]) && (n === 2 || ehId(partes[2]))) {
      return { vista: 'painel', tipo: 'edicao', data: partes[1], item: n === 3 ? partes[2] : null, consulta: interpretaConsulta(consultaBruta, PARAMETROS.edicao) };
    }
    if (cabeca === 'arquivo' && n === 1) {
      return { vista: 'arquivo', tipo: 'arquivo', consulta: interpretaConsulta(consultaBruta, PARAMETROS.arquivo) };
    }
    if (cabeca === 'regua' && n === 1) {
      return { vista: 'regua', tipo: 'regua', aba: 'partidos', ficha: null, consulta: Object.create(null), redireciona: hashRegua('partidos') };
    }
    if (cabeca === 'regua' && (n === 2 || n === 3) && ABAS_REGUA.indexOf(partes[1]) !== -1 && (n === 2 || ehId(partes[2]))) {
      return { vista: 'regua', tipo: 'regua', aba: partes[1], ficha: n === 3 ? partes[2] : null, consulta: interpretaConsulta(consultaBruta, PARAMETROS[partes[1]]) };
    }
    if (cabeca === 'metodo' && (n === 1 || (n === 2 && SECOES_METODO.indexOf(partes[1]) !== -1))) {
      return { vista: 'metodo', tipo: 'metodo', secao: n === 2 ? partes[1] : null, consulta: Object.create(null) };
    }
    return rotaDesconhecida();
  }

  /* Filtros de volta para o endereço: "?cat=ia&dom=energia". */
  function consultaDe(valores, ordem) {
    var pares = [];
    ordem.forEach(function (nome) {
      if (ehTexto(valores[nome]) && valores[nome] !== '') {
        pares.push(nome + '=' + encodeURIComponent(valores[nome]));
      }
    });
    return pares.length ? '?' + pares.join('&') : '';
  }

  /* Troca o endereço sem criar passo no histórico e sem disparar a rota.
     Se o navegador recusar (página aberta de um arquivo, por exemplo), a
     tela segue funcionando: só o endereço fica como estava. */
  function gravaEndereco(hash) {
    try {
      if (janela.history && typeof janela.history.replaceState === 'function') {
        janela.history.replaceState(null, '', hash);
      }
    } catch (erro) {
      return;
    }
  }

  /* ----- moldura: navegação, título, anúncio, foco ----- */

  function marcaNavegacao(vista) {
    var nav = porId('nav');
    if (!nav) { return; }
    var links = nav.getElementsByTagName('a');
    for (var i = 0; i < links.length; i += 1) {
      if (links[i].getAttribute('data-vista') === vista) {
        links[i].setAttribute('aria-current', 'page');
      } else {
        links[i].removeAttribute('aria-current');
      }
    }
  }

  function mudaTituloDaAba(titulo) {
    doc.title = titulo;
  }

  /* Região aria-live: carga, erro e contagem de filtro. */
  function anuncia(mensagem) {
    var regiao = porId('anuncio');
    if (!regiao) { return; }
    regiao.textContent = '';
    regiao.textContent = mensagem;
  }

  function vistaAtual() {
    return porId('vista');
  }

  /* Troca o conteúdo da vista de uma vez: o quadro antigo fica inteiro na
     tela até o novo estar pronto. */
  function trocaVista(classe, filhos) {
    var vista = vistaAtual();
    vista.setAttribute('class', 'vista ' + classe);
    vista.removeAttribute('aria-busy');
    estado.regua = null;
    estado.fechaDicaDaVista = null;
    troca(vista, filhos);
    return vista;
  }

  /* Ao trocar de rota: foco no h1 e página no topo. */
  function focaTituloDaVista() {
    var h1 = porId('titulo-vista');
    if (typeof janela.scrollTo === 'function') { janela.scrollTo(0, 0); }
    if (h1 && typeof h1.focus === 'function') { h1.focus(); }
  }

  /* Leva o leitor a uma parte da página: rola e põe o foco. */
  function levaAte(el) {
    if (!el) { return; }
    if (typeof el.scrollIntoView === 'function') { el.scrollIntoView(); }
    if (typeof el.focus === 'function') { el.focus(); }
  }

  /* ----- avisos gerais: rota, carga, edição nova ----- */

  function mostraAvisoGeral(chave, el) {
    tiraAvisoGeral(chave);
    var caixa = porId('avisos-gerais');
    if (!caixa) { return; }
    estado.avisosGerais[chave] = el;
    caixa.appendChild(el);
  }

  function tiraAvisoGeral(chave) {
    var el = estado.avisosGerais[chave];
    if (el && el.parentNode) { el.parentNode.removeChild(el); }
    delete estado.avisosGerais[chave];
  }

  /* Na troca de rota saem os avisos da rota anterior. O de edição nova fica. */
  function tiraAvisosDeRota() {
    ['rota', 'destino', 'falha', 'demora', 'vazio'].forEach(tiraAvisoGeral);
  }

  /* ======================================================================
     9. Componentes pequenos
     ====================================================================== */

  function novoId(prefixo) {
    estado.contador += 1;
    return prefixo + '-' + estado.contador;
  }

  function etiqueta(conteudo, classe) {
    return cria('span', 'etiqueta' + (classe ? ' ' + classe : ''), conteudo);
  }

  /* Aviso: rótulo em mono, texto e, se houver, botões e links.
     opcoes: rotulo, texto (texto, nó ou lista), acoes (lista de nós), classe.
     Sem rótulo, fica o ícone e o texto: é o caso do aviso que vem da régua. */
  function aviso(opcoes) {
    var caixa = cria('div', 'aviso' + (opcoes.grave ? ' aviso--grave' : '') + (opcoes.classe ? ' ' + opcoes.classe : ''));
    var linha = cria('div', 'aviso__linha');
    poe(linha, icone('i-aviso'), opcoes.rotulo ? cria('strong', 'aviso__rotulo', opcoes.rotulo) : null);
    if (opcoes.texto) { poe(linha, cria('span', 'aviso__texto', opcoes.texto)); }
    if (opcoes.acoes && opcoes.acoes.length) { poe(linha, cria('span', 'aviso__acoes', opcoes.acoes)); }
    poe(caixa, linha);
    return caixa;
  }

  /* Nota de seção: uma linha logo abaixo do título. */
  function notaDeSecao(conteudo) {
    return cria('p', 'nota-secao', [icone('i-aviso', 'icone--14'), conteudo]);
  }

  /* Seção numerada do Painel. Devolve a seção e o corpo, para quem preenche. */
  function secao(chave, numero, titulo, contexto, complemento) {
    var raiz = cria('section', 'secao secao--' + chave);
    var h2 = cria('h2', 'secao__titulo');
    atributos(raiz, { id: 's-' + chave, 'aria-labelledby': 't-' + chave });
    h2.setAttribute('id', 't-' + chave);
    poe(h2, cria('span', 'secao__num', numero), ' ' + titulo + (complemento || ''));
    if (contexto && contexto.exemplo) { poe(h2, ' ', etiqueta(T.placas.exemplo)); }
    var corpo = cria('div', 'secao__corpo');
    poe(raiz, h2, corpo);
    return { raiz: raiz, titulo: h2, corpo: corpo };
  }

  function subtitulo(conteudo, tag) {
    return cria(tag || 'h3', 'subtitulo', conteudo);
  }

  function fraseVazia(frase) {
    return cria('p', 'vazio', frase);
  }

  /* Sigla do partido: etiqueta sem cor, link para a ficha, nome em <abbr>.
     Partido que não está na régua aparece pelo id, sem link. */
  function siglaDoPartido(apoio, id) {
    var partido = busca(apoio.partidos, id);
    if (!partido || !ehId(id)) { return cria('span', 'id-cru', texto(id)); }
    var abbr = cria('abbr', '', texto(partido.sigla) || id);
    abbr.setAttribute('title', texto(partido.nome));
    return linkInterno(hashRegua('partidos', id), abbr, 'etiqueta etiqueta--partido');
  }

  function nomeDoPartido(apoio, id) {
    var partido = busca(apoio.partidos, id);
    return partido && ehTexto(partido.nome) ? partido.nome : texto(id);
  }

  /* Medidor de 5 segmentos. Repete o selo: fica fora do leitor de tela. */
  function medidor(nivel, grande) {
    var acesos = nivelValido(nivel) ? nivel : 0;
    var caixa = cria('span', 'medidor nivel-' + acesos + (grande ? ' medidor--grande' : ''));
    for (var i = 1; i <= NIVEL_MAXIMO; i += 1) {
      poe(caixa, cria('span', 'medidor__seg' + (i <= acesos ? ' medidor__seg--aceso' : '')));
    }
    return soVista(caixa);
  }

  /* Tendência: sempre seta e palavra. */
  function tendencia(valor) {
    var caixa = cria('span', 'tendencia');
    if (tem(ICONE_TENDENCIA, valor)) { poe(caixa, icone(ICONE_TENDENCIA[valor], 'icone--seta')); }
    poe(caixa, cria('span', '', rotulo('tendencia', valor)));
    return caixa;
  }

  /* O que o leitor de tela ouve no lugar do selo: "Nível 3 de 5, tensão, subindo". */
  function nivelFalado(apoio, nivel, valorDaTendencia) {
    var fala = 'Nível ' + texto(nivel) + ' de ' + NIVEL_MAXIMO;
    if (busca(apoio.niveis, nivel)) { fala += ', ' + rotuloDoNivel(apoio, nivel).toLocaleLowerCase('pt-BR'); }
    if (valorDaTendencia) { fala += ', ' + rotulo('tendencia', valorDaTendencia); }
    return fala;
  }

  /* Selo de nível: ícone, numeral e rótulo, sempre os três juntos. */
  function selo(apoio, nivel, valorDaTendencia) {
    var classe = nivelValido(nivel) ? nivel : 0;
    var caixa = cria('span', 'selo nivel-' + classe, soLeitor(nivelFalado(apoio, nivel, valorDaTendencia)));
    if (classe) { poe(caixa, icone('i-nivel-' + classe, 'selo__icone')); }
    poe(caixa, soVista(cria('span', 'selo__num', texto(nivel))), soVista(cria('span', 'selo__rotulo', rotuloDoNivel(apoio, nivel))));
    return caixa;
  }

  /* Força: "força 2", três pontos e a palavra da régua. */
  function forca(apoio, valor) {
    var n = ehNumero(valor) ? valor : 0;
    var caixa = cria('span', 'forca');
    var pontos = cria('span', 'forca__pontos');
    for (var i = 1; i <= 3; i += 1) {
      poe(pontos, cria('span', 'forca__ponto' + (i <= n ? ' forca__ponto--cheio' : '')));
    }
    poe(caixa, cria('span', '', ['força ' + texto(valor), soLeitor(' de 3')]), soVista(pontos), cria('span', '', nomeDaForca(apoio, valor)));
    return caixa;
  }

  /* Barra que parte do eixo: 72 px valem a escala. Valor zero não tem barra.
     A variante diz o lado: direita (ganha) ou esquerda (perde). */
  function barraDoEixo(valor, escala, variante) {
    if (!ehNumero(valor) || valor <= 0) { return null; }
    var barra = cria('span', 'placar__barra ' + variante);
    /* tamanho posto pelo script: a política de conteúdo não aceita atributo style */
    barra.style.width = Math.round(BARRA_PLACAR_PX * valor / escala) + 'px';
    return barra;
  }

  /* Etiqueta de tema: a sigla, com o nome em <abbr>. Tema fora da régua: o id. */
  function etiquetaDeTema(apoio, id) {
    var tema = temaDe(apoio, id);
    if (!tema) { return cria('span', 'id-cru', texto(id)); }
    var abbr = cria('abbr', '', texto(tema.sigla) || texto(id));
    abbr.setAttribute('title', texto(tema.nome));
    return etiqueta(abbr);
  }

  /* O texto de uma coluna: é ele que vira o rótulo da célula na tela estreita. */
  function rotuloDaColuna(coluna) {
    return ehObjeto(coluna) ? texto(coluna.rotulo) : texto(coluna);
  }

  /* Uma linha de tabela. Célula: texto, nó, lista, ou { conteudo, numero,
     longa }. O conteúdo vai dentro de um só elemento: na tela estreita a
     célula vira duas colunas (rótulo e valor), e cada filho solto viraria
     uma coluna a mais. "longa" é a célula de texto corrido: na tela estreita
     o rótulo fica em cima, e o texto usa a largura toda. */
  function linhaDeTabela(colunas, celulas) {
    var tr = cria('tr');
    tr.setAttribute('role', 'row');
    celulas.forEach(function (celula, i) {
      var dados = ehObjeto(celula) && 'conteudo' in celula ? celula : { conteudo: celula };
      var classe = (dados.numero ? 'num' : '') + (dados.longa ? (dados.numero ? ' ' : '') + 'tabela__longa' : '');
      var el = cria(i === 0 ? 'th' : 'td', classe, cria('div', 'tabela__valor', dados.conteudo));
      atributos(el, i === 0 ? { scope: 'row', role: 'rowheader' } : { role: 'cell' });
      el.setAttribute('data-rotulo', rotuloDaColuna(colunas[i]));
      poe(tr, el);
    });
    return tr;
  }

  /* Tabela de verdade: caption, th com scope, e o rótulo de cada célula
     para a tela estreita. Coluna: texto, ou { rotulo, conteudo } quando o
     cabeçalho leva um nó (uma sigla em <abbr>). Linha: lista de células.
     opcoes: classe (variante), legendaEscondida (o título ao lado já diz).
     Os papéis vão escritos: na tela estreita o CSS muda o display das linhas,
     e alguns navegadores deixam de anunciar a tabela como tabela. */
  function tabela(legenda, colunas, linhas, opcoes) {
    var o = opcoes || {};
    var raiz = cria('table', 'tabela' + (o.classe ? ' ' + o.classe : ''));
    raiz.setAttribute('role', 'table');
    poe(raiz, cria('caption', o.legendaEscondida ? 'so-leitor' : '', legenda));
    var cabeca = cria('tr');
    cabeca.setAttribute('role', 'row');
    colunas.forEach(function (coluna) {
      var th = cria('th', '', ehObjeto(coluna) ? coluna.conteudo : coluna);
      atributos(th, { scope: 'col', role: 'columnheader' });
      poe(cabeca, th);
    });
    var grupoDaCabeca = cria('thead', '', cabeca);
    grupoDaCabeca.setAttribute('role', 'rowgroup');
    poe(raiz, grupoDaCabeca);
    var corpo = cria('tbody');
    corpo.setAttribute('role', 'rowgroup');
    linhas.forEach(function (linha) { poe(corpo, linhaDeTabela(colunas, linha)); });
    poe(raiz, corpo);
    return raiz;
  }

  /* ======================================================================
     10. Dobras, dicas e teclado
     ====================================================================== */

  /* Liga um botão a um conteúdo que abre e fecha.
     O botão leva aria-expanded e aria-controls; o conteúdo usa hidden.
     aoMudar(aberta) é chamado só quando quem muda é o leitor. */
  function ligaDobra(botaoEl, corpo, aoMudar) {
    if (!corpo.getAttribute('id')) { corpo.setAttribute('id', novoId('dobra')); }
    corpo.classList.add('dobra__corpo');
    botaoEl.setAttribute('aria-controls', corpo.getAttribute('id'));
    var dobra = {
      botao: botaoEl,
      corpo: corpo,
      aberta: false,
      /* muda sem avisar ninguém: usado na montagem e nas rotas */
      poe: function (aberta) {
        dobra.aberta = !!aberta;
        botaoEl.setAttribute('aria-expanded', dobra.aberta ? 'true' : 'false');
        esconde(corpo, !dobra.aberta);
        if (dobra.aoPor) { dobra.aoPor(dobra.aberta); }
      },
      /* muda por ação do leitor */
      muda: function (aberta) {
        dobra.poe(aberta);
        if (aoMudar) { aoMudar(dobra.aberta); }
      }
    };
    botaoEl.addEventListener('click', function () { dobra.muda(!dobra.aberta); });
    dobra.poe(false);
    estado.dobras.push(dobra);
    return dobra;
  }

  function contem(pai, filho) {
    for (var no = filho; no; no = no.parentNode) {
      if (no === pai) { return true; }
    }
    return false;
  }

  /* O clique partiu de um link, de um botão ou de uma dica? */
  function partiuDeControle(alvo, limite) {
    for (var no = alvo; no && no !== limite; no = no.parentNode) {
      var tag = no.tagName ? String(no.tagName).toLowerCase() : '';
      if (tag === 'a' || tag === 'button' || tag === 'select' || tag === 'input') { return true; }
      if (no.classList && no.classList.contains('tem-dica')) { return true; }
    }
    return false;
  }

  /* Em linha de domínio e de radar, o toque em qualquer ponto do cabeçalho
     que não seja link também abre. */
  function cabecaAbre(cabeca, dobra) {
    cabeca.addEventListener('click', function (evento) {
      if (partiuDeControle(evento.target, cabeca)) { return; }
      dobra.muda(!dobra.aberta);
    });
  }

  /* A dobra aberta mais de dentro que contém o foco. */
  function dobraDoFoco(ativo) {
    var achada = null;
    estado.dobras.forEach(function (dobra) {
      if (!dobra.aberta) { return; }
      if (dobra.botao === ativo || contem(dobra.corpo, ativo)) {
        if (!achada || contem(achada.corpo, dobra.corpo)) { achada = dobra; }
      }
    });
    return achada;
  }

  /* Dica flutuante: abre com o ponteiro e com o foco (pelo CSS) e fecha com
     Esc. O texto da dica também vai no nome acessível do gatilho. */
  function comDica(gatilho, dica) {
    gatilho.classList.add('tem-dica');
    gatilho.setAttribute('tabindex', '0');
    poe(gatilho, soLeitor(': ' + dica), soVista(cria('span', 'dica', dica)));
    gatilho.addEventListener('mouseenter', function () {
      gatilho.classList.remove('dica-fechada');
      estado.dicaSobPonteiro = gatilho;
    });
    gatilho.addEventListener('mouseleave', function () {
      gatilho.classList.remove('dica-fechada');
      if (estado.dicaSobPonteiro === gatilho) { estado.dicaSobPonteiro = null; }
    });
    gatilho.addEventListener('blur', function () { gatilho.classList.remove('dica-fechada'); });
    return gatilho;
  }

  function etiquetaComDica(conteudo, dica) {
    return comDica(etiqueta(conteudo), dica);
  }

  /* Fecha as dicas abertas. Devolve true se fechou alguma. */
  function fechaDicas(ativo) {
    var fechou = false;
    [ativo, estado.dicaSobPonteiro].forEach(function (el) {
      if (el && el.classList && el.classList.contains('tem-dica') && !el.classList.contains('dica-fechada')) {
        el.classList.add('dica-fechada');
        fechou = true;
      }
    });
    if (estado.quadro && estado.quadro.fechaDicaDaFita && estado.quadro.fechaDicaDaFita()) { fechou = true; }
    if (estado.fechaDicaDaVista && estado.fechaDicaDaVista()) { fechou = true; }
    return fechou;
  }

  /* Esc fecha a dica; sem dica aberta, fecha a dobra onde está o foco e
     devolve o foco ao botão. Não há atalho de uma tecla. */
  function aoTeclar(evento) {
    if (evento.key !== 'Escape' && evento.key !== 'Esc') { return; }
    var ativo = doc.activeElement;
    if (fechaDicas(ativo)) { return; }
    var dobra = dobraDoFoco(ativo);
    if (dobra) {
      dobra.muda(false);
      if (typeof dobra.botao.focus === 'function') { dobra.botao.focus(); }
    }
  }

  /* ======================================================================
     11. Edição: escolha, carga e estados
     Serve ao Painel (#/) e à edição antiga (#/edicao/AAAA-MM-DD).
     ====================================================================== */

  function leIndice(deNovo) {
    if (deNovo) { esquece(ARQ_INDICE); }
    if (!memoria[ARQ_INDICE]) { estado.indiceLidoEm = agora(); }
    return le(ARQ_INDICE).then(function (indice) {
      estado.indice = indice;
      return indice;
    });
  }

  /* A data da edição que a rota pede, se o índice já está na memória. */
  function dataPedida(rota) {
    if (rota.data) { return rota.data; }
    if (!estado.indice) { return null; }
    var entrada = maisRecente(entradasDoIndice(estado.indice));
    return entrada ? entrada.data : null;
  }

  function paraRelogioDemora() {
    if (estado.relogioDemora !== null) { janela.clearTimeout(estado.relogioDemora); }
    estado.relogioDemora = null;
  }

  function paraRelogioIdade() {
    if (estado.relogioIdade !== null) { janela.clearInterval(estado.relogioIdade); }
    estado.relogioIdade = null;
  }

  /* Durante a carga o quadro anterior fica na tela, inteiro, com aria-busy.
     Nada esmaece. O carimbo avisa. Depois de 8 segundos, "Está demorando". */
  function iniciaCarga(data) {
    var vista = vistaAtual();
    vista.setAttribute('aria-busy', 'true');
    paraRelogioDemora();
    tiraAvisoGeral('demora');
    tiraAvisoGeral('falha');
    var refs = estado.quadro ? estado.quadro.refs : null;
    if (refs && refs.carimboCarga && data) {
      troca(refs.carimboCarga, 'Carregando edição de ' + dataCurta(data) + '…');
      esconde(refs.carimboTexto, true);
      esconde(refs.carimboCarga, false);
    }
    anuncia(T.carregando);
    estado.relogioDemora = janela.setTimeout(avisaDemora, ESPERA_DEMORA_MS);
  }

  function terminaCarga() {
    paraRelogioDemora();
    tiraAvisoGeral('demora');
    vistaAtual().removeAttribute('aria-busy');
    var refs = estado.quadro ? estado.quadro.refs : null;
    if (refs && refs.carimboCarga) {
      esconde(refs.carimboCarga, true);
      esconde(refs.carimboTexto, false);
    }
  }

  function avisaDemora() {
    estado.relogioDemora = null;
    mostraAvisoGeral('demora', aviso({
      rotulo: T.carregando,
      texto: T.demora,
      acoes: [botao(T.tentar, '', tentaDeNovo)]
    }));
    anuncia(T.demora);
  }

  /* Pede de novo o que não chegou e refaz a rota que falhou. Se o leitor
     mexeu no quadro antigo nesse meio tempo, o endereço mudou: volta-se ao
     endereço da carga que o aviso cita. */
  function tentaDeNovo() {
    esquecePendentes();
    tiraAvisoGeral('falha');
    tiraAvisoGeral('demora');
    if (estado.enderecoDaCarga !== null && janela.location.hash !== estado.enderecoDaCarga) {
      gravaEndereco(estado.enderecoDaCarga || '#/');
    }
    trataRota(true);
  }

  /* A moldura do Painel, igual à do index.html: títulos e travessões. */
  function molduraDoPainel() {
    var h1 = cria('h1', 'so-leitor', T.vistas.painel);
    atributos(h1, { id: 'titulo-vista', tabindex: '-1' });
    var cabeca = cria('div', 'cabeca');
    cabeca.setAttribute('id', 's-carimbo');
    var carimbo = cria('p', 'carimbo', T.travessao);
    carimbo.setAttribute('id', 'carimbo');
    var avisos = cria('div', 'avisos');
    avisos.setAttribute('id', 'avisos-edicao');
    poe(cabeca, carimbo, avisos);
    var grade = cria('div', 'grade-painel');
    var lateral = cria('div', 'coluna-lateral');
    function vazia(chave, numero, titulo) {
      var s = secao(chave, numero, titulo, null);
      poe(s.corpo, fraseVazia(T.travessao));
      return s.raiz;
    }
    poe(lateral, vazia('placar', '05', T.titulos.placar), vazia('vigiar', '06', T.titulos.vigiar), vazia('movimentos', '07', T.titulos.movimentos));
    poe(grade,
      vazia('hoje', '01', T.titulos.hoje), vazia('dominios', '02', T.titulos.dominios),
      vazia('indicadores', '03', T.titulos.indicadores), vazia('principais', '04', T.titulos.principais),
      lateral, vazia('radar', '08', T.titulos.radar), vazia('bastidores', '09', T.titulos.bastidores));
    return [h1, cabeca, grade];
  }

  /* Sem quadro bom na tela, fica a moldura com travessões, sem "Carregando". */
  function garanteMoldura() {
    if (estado.quadro) { return; }
    trocaVista('vista--painel', molduraDoPainel());
    marcaNavegacao('painel');
    mudaTituloDaAba(T.tituloBase);
  }

  /* Erro de rede: aviso grave com o nome do arquivo. O último quadro bom fica.
     naVista: a falha é do Arquivo, da Régua ou do Método, que ficam na tela
     como estão, sem dar lugar à moldura do Painel. */
  function falhaDeCarga(arquivo, naVista) {
    terminaCarga();
    if (!naVista) { garanteMoldura(); }
    mostraAvisoGeral('falha', aviso({
      grave: true,
      rotulo: T.avisos.falha,
      texto: ['Não deu para carregar ', cria('span', 'mono', arquivo), '. Confira a conexão.'],
      acoes: [
        botao(T.tentar, '', tentaDeNovo),
        linkInterno('#/arquivo', 'Abrir o Arquivo de edições.'),
        cria('span', '', ['O ', linkArquivo(ARQ_FEED, T.linkFeed), ' traz o resumo das últimas edições.'])
      ]
    }));
    anuncia(T.avisos.falha + '. Não deu para carregar ' + arquivo + '.');
  }

  /* Índice sem edição. Régua e Método seguem funcionando. */
  function mostraVazio() {
    terminaCarga();
    estado.quadro = null;
    paraRelogioIdade();
    garanteMoldura();
    mostraAvisoGeral('vazio', aviso({ rotulo: T.avisos.vazio[0], texto: T.avisos.vazio[1] }));
    anuncia(T.avisos.vazio[0] + '. ' + T.avisos.vazio[1]);
  }

  /* Tudo o que as seções precisam saber da edição em tela. */
  function montaContexto(entradas, entrada, edicao, apoio, faltas) {
    var itens = Object.create(null);
    lista(edicao.principais).concat(lista(edicao.radar)).forEach(function (item) {
      if (ehObjeto(item) && ehId(item.id) && !(item.id in itens)) { itens[item.id] = item; }
    });
    var exemplo = edicao.exemplo === true || ehExemplo(entrada);
    return {
      entradas: entradas,
      entrada: entrada,
      edicao: edicao,
      apoio: apoio,
      faltas: faltas,
      data: entrada.data,
      exemplo: exemplo,
      falha: edicao.estado === 'falha',
      ehPainel: maisRecente(entradas) === entrada,
      anterior: anteriorA(entradas, entrada.data),
      /* edição de exemplo não entra no histórico nem no acumulado */
      historico: exemplo ? [] : historicoAte(entradas, entrada.data),
      vizinhas: vizinhasDe(entradas, entrada.data),
      geradaEm: instante(edicao.gerada_em) !== null ? instante(edicao.gerada_em) : instante(entrada.gerada_em),
      alerta: ehObjeto(edicao.alerta) ? edicao.alerta : {},
      itens: itens
    };
  }

  /* Atrasada: só no Painel, quando a edição tem mais de 26 horas. */
  function estaAtrasada(contexto) {
    return contexto.ehPainel && contexto.geradaEm !== null && agora() - contexto.geradaEm > ATRASO_MS;
  }

  /* Abre a edição que a rota pede. forcar: recarrega mesmo se já está em tela. */
  function abreEdicao(rota, primeira, forcar) {
    var pedido = (estado.pedido += 1);
    var quadro = estado.quadro;
    if (!forcar && quadro && quadro.data === dataPedida(rota)) {
      /* a mesma edição já está na tela: só muda o destino e os filtros */
      terminaCarga();
      aplicaRota(quadro, rota, primeira);
      return Promise.resolve();
    }
    estado.enderecoDaCarga = janela.location.hash;
    iniciaCarga(dataPedida(rota));
    return leIndice(false).then(function (indice) {
      if (pedido !== estado.pedido) { return null; }
      var entradas = entradasDoIndice(indice);
      if (!entradas.length) { mostraVazio(); return null; }
      var entrada = rota.data ? entradaDaData(entradas, rota.data) : maisRecente(entradas);
      if (!entrada) {
        terminaCarga();
        abreArquivo({ vista: 'arquivo', tipo: 'arquivo', consulta: Object.create(null) }, primeira, avisoSemEdicaoNaData(rota.data));
        return null;
      }
      return carregaEdicao(pedido, entradas, entrada, rota, primeira);
    }, function () {
      if (pedido === estado.pedido) { falhaDeCarga(ARQ_INDICE); }
      return null;
    }).then(null, function () {
      /* rede de segurança: um índice que o site não soube ler vira aviso,
         e não uma tela parada em "Carregando" */
      if (pedido === estado.pedido) { falhaDeCarga(ARQ_INDICE); }
      return null;
    });
  }

  /* Lê a edição e os dados de apoio juntos. Só a edição é indispensável. */
  function carregaEdicao(pedido, entradas, entrada, rota, primeira) {
    var caminho = caminhoDaEdicao(entrada);
    var apoios = [ARQ_REGUA, ARQ_PLAYERS, ARQ_VEICULOS, ARQ_VETORES, ARQ_CATALOGO];
    var leituras = [le(caminho).then(function (d) { return d; }, function () { return null; })].concat(apoios.map(leApoio));
    return Promise.all(leituras).then(function (r) {
      if (pedido !== estado.pedido) { return; }
      if (!r[0]) { falhaDeCarga(caminho); return; }
      var faltas = apoios.filter(function (arquivo, i) { return !r[i + 1]; });
      var apoio = montaApoio(r[1], r[2], r[3], r[4], r[5]);
      apoio.formatosNovos = apoios.filter(function (arquivo, i) { return formatoNovo(r[i + 1]); });
      var contexto;
      try {
        contexto = montaContexto(entradas, entrada, r[0], apoio, faltas);
        mostraEdicao(contexto, rota, primeira);
      } catch (erro) {
        /* rede de segurança: edição que o site não soube montar vira aviso,
           e não uma tela parada em "Carregando". Se a quebra foi depois da
           troca, o quadro novo fica; se foi antes, fica o anterior.
           O arquivo sai da memória: "Tentar de novo" pede outra vez, porque
           uma edição quebrada pode ter sido trocada por uma boa. */
        esquece(caminho);
        falhaDeCarga(caminho);
      }
    });
  }

  /* Põe a edição na tela e liga o que depende dela. */
  function mostraEdicao(contexto, rota, primeira) {
    var quadro = {
      contexto: contexto,
      data: contexto.data,
      atrasada: estaAtrasada(contexto),
      filtros: { cat: '', dom: '', partido: '' },
      refs: {
        principais: Object.create(null), radar: Object.create(null),
        dominios: Object.create(null), indicadores: Object.create(null)
      }
    };
    /* primeiro monta tudo fora da tela; só depois troca. Se a montagem
       quebrar, o quadro que está na tela segue inteiro e funcionando. */
    var dobrasDoQuadroAnterior = estado.dobras;
    var filhos;
    estado.dobras = [];
    try {
      filhos = montaEdicao(quadro);
    } catch (erro) {
      estado.dobras = dobrasDoQuadroAnterior;
      throw erro;
    }
    terminaCarga();
    paraRelogioIdade();
    estado.dicaSobPonteiro = null;
    estado.quadro = quadro;
    trocaVista('vista--painel', filhos);
    marcaNavegacao(contexto.ehPainel ? 'painel' : 'arquivo');
    mudaTituloDaAba(tituloDaAbaDaEdicao(contexto));
    poeLinksNoRodape(contexto);
    estado.relogioIdade = janela.setInterval(atualizaIdade, PASSO_IDADE_MS);
    aplicaRota(quadro, rota, primeira);
    anuncia(textoDosAvisosDeRota() + 'Edição de ' + dataLonga(contexto.data) + '.');
  }

  /* O leitor de tela também ouve o aviso de endereço sem destino. */
  function textoDosAvisosDeRota() {
    var partes = '';
    ['rota', 'destino'].forEach(function (chave) {
      var el = estado.avisosGerais[chave];
      if (el) { partes += el.textContent.replace(/\s+/g, ' ').trim() + ' '; }
    });
    return partes;
  }

  /* "INFOCENARIUM · 19/11/2026 · nível 3 TENSÃO"; a de exemplo começa com [EXEMPLO]. */
  function tituloDaAbaDaEdicao(contexto) {
    var nivel = contexto.alerta.nivel;
    var titulo = T.marca + T.separador + dataLonga(contexto.data) + T.separador + 'nível ' + texto(nivel);
    if (busca(contexto.apoio.niveis, nivel)) { titulo += ' ' + rotuloDoNivel(contexto.apoio, nivel); }
    /* dia sem edição: a aba diz isso, como o feed, e não o nível repetido */
    if (contexto.falha) { titulo = T.marca + T.separador + dataLonga(contexto.data) + T.separador + rotulo('estado', 'falha'); }
    return (contexto.exemplo ? '[' + T.placas.exemplo + '] ' : '') + titulo;
  }

  function poeLinksNoRodape(contexto) {
    var caixa = porId('rodape-edicao');
    if (!caixa) { return; }
    troca(caixa, linkArquivo(caminhoDoTexto(contexto.entrada), T.linkTexto), linkArquivo(caminhoDaEdicao(contexto.entrada), T.linkJson));
  }

  /* Aplica à edição em tela o que o endereço pede: filtros e item. */
  function aplicaRota(quadro, rota, primeira) {
    poeFiltros(quadro, filtrosDaConsulta(quadro, rota.consulta));
    if (!rota.item) {
      if (!primeira) { focaTituloDaVista(); }
      return;
    }
    if (!abreDestino(quadro, rota.item)) {
      mostraAvisoGeral('destino', aviso({
        rotulo: T.avisos.itemNaoEncontrado,
        texto: ['A edição de ', tempo(quadro.data, true), ' não tem o item ', cria('span', 'mono', rota.item), '.']
      }));
      anuncia(textoDosAvisosDeRota());
      if (!primeira) { focaTituloDaVista(); }
    }
  }

  /* Procura o destino nesta ordem: principal, radar, domínio, indicador.
     Abre, rola e põe o foco. Devolve false se não existe. */
  function abreDestino(quadro, id) {
    var refs = quadro.refs;
    var alvo = busca(refs.principais, id) || busca(refs.radar, id) || busca(refs.dominios, id);
    if (alvo) {
      if (busca(refs.radar, id) === alvo && alvo.raiz.hasAttribute('hidden')) {
        /* o item pedido pelo endereço nunca fica escondido por filtro */
        poeFiltros(quadro, { cat: '', dom: '', partido: '' });
      }
      alvo.dobra.poe(true);
      levaAte(alvo.foco);
      return true;
    }
    var ficha = busca(refs.indicadores, id);
    if (ficha) {
      levaAte(ficha);
      return true;
    }
    return false;
  }

  /* O endereço da edição em tela, com o item aberto e os filtros que houver. */
  function enderecoDoQuadro(quadro, item) {
    var consulta = consultaDe(quadro.filtros, PARAMETROS.edicao);
    var rota = estado.rota;
    if (!item && rota && rota.tipo === 'edicao' && !rota.data && !rota.desconhecida) { return '#/' + consulta; }
    return hashEdicao(quadro.data, item, consulta);
  }

  /* Abrir um item grava o endereço dele; fechar grava o da edição. */
  function gravaItemNoEndereco(quadro, id, aberto) {
    var hash = hashEdicao(quadro.data, aberto ? id : null, consultaDe(quadro.filtros, PARAMETROS.edicao));
    gravaEndereco(hash);
    estado.rota = interpretaRota(hash);
  }

  /* A cada minuto: refaz a idade e a conta de atraso. Sem anúncio. */
  function atualizaIdade() {
    var quadro = estado.quadro;
    if (!quadro) { return; }
    if (quadro.refs.idade) { troca(quadro.refs.idade, idade(quadro.contexto.geradaEm)); }
    var atrasada = estaAtrasada(quadro.contexto);
    if (atrasada !== quadro.atrasada) {
      quadro.atrasada = atrasada;
      refazEstadoDaCabeca(quadro);
    } else if (atrasada && quadro.refs.horasDeAtraso) {
      troca(quadro.refs.horasDeAtraso, String(horasDesde(quadro.contexto.geradaEm)));
    }
    /* Painel aberto por mais de um dia com a aba sempre visível: sem esta
       releitura, o aviso de atraso diria "A mais recente é de…" de uma edição
       que já tem sucessora. Só enquanto está atrasada e o aviso de edição
       nova ainda não saiu (ele não se repete a cada 5 minutos). */
    if (atrasada && doc.visibilityState === 'visible' && !estado.avisosGerais['edicao-nova']) { releIndice(); }
  }

  /* ----- edição nova: o texto nunca troca sozinho ----- */

  /* Quando a aba volta a ficar visível, o índice é lido de novo. */
  function aoVoltarParaAba() {
    if (doc.visibilityState !== 'visible') { return; }
    releIndice();
  }

  /* Lê o índice de novo (no máximo uma vez a cada 5 minutos). Se há edição
     mais nova, ou se a edição em tela mudou de gerada_em, aparece o aviso
     com o botão "Carregar". */
  function releIndice() {
    if (!estado.indice) { return; }
    if (agora() - estado.indiceLidoEm < RELEITURA_INDICE_MS) { return; }
    estado.indiceLidoEm = agora();
    var antigo = estado.indice;
    janela.fetch(ARQ_INDICE, { cache: 'no-cache' }).then(function (resposta) {
      if (!resposta || !resposta.ok) { throw new Error('resposta'); }
      return resposta.json();
    }).then(function (novo) {
      if (!ehObjeto(novo) || estado.indice !== antigo) { return; }
      var data = novidadeNoIndice(antigo, novo);
      if (data) { avisaEdicaoNova(novo, data); }
    }).catch(function () { /* sem rede agora: fica o que está na tela */ });
  }

  /* A data da edição nova, ou da edição em tela que mudou; null se nada mudou. */
  function novidadeNoIndice(antigo, novo) {
    var antes = maisRecente(entradasDoIndice(antigo));
    var depois = maisRecente(entradasDoIndice(novo));
    if (depois && (!antes || depois.data > antes.data)) { return depois.data; }
    var quadro = estado.quadro;
    if (quadro) {
      var agoraNoIndice = entradaDaData(entradasDoIndice(novo), quadro.data);
      if (agoraNoIndice && texto(agoraNoIndice.gerada_em) !== texto(quadro.contexto.entrada.gerada_em)) { return quadro.data; }
    }
    return null;
  }

  function avisaEdicaoNova(indiceNovo, data) {
    mostraAvisoGeral('edicao-nova', aviso({
      classe: 'aviso--edicao-nova',
      rotulo: T.avisos.edicaoNova,
      texto: ['Saiu a edição de ', tempo(data, true), '.'],
      acoes: [botao(T.carregar, 'botao--principal', function () { carregaEdicaoNova(indiceNovo, data); })]
    }));
    anuncia(T.avisos.edicaoNova + '. Saiu a edição de ' + dataLonga(data) + '.');
  }

  /* Ao carregar a edição nova, players e vetores também são lidos de novo. */
  function carregaEdicaoNova(indiceNovo, data) {
    tiraAvisoGeral('edicao-nova');
    var entrada = entradaDaData(entradasDoIndice(indiceNovo), data);
    esquece(ARQ_INDICE);
    esquece(ARQ_PLAYERS);
    esquece(ARQ_VETORES);
    if (entrada) { esquece(caminhoDaEdicao(entrada)); }
    memoria[ARQ_INDICE] = Promise.resolve(indiceNovo);
    chegou[ARQ_INDICE] = true;
    estado.indice = indiceNovo;
    var mesmaEmTela = estado.quadro && estado.quadro.data === data;
    if (!mesmaEmTela && janela.location.hash !== '#/' && janela.location.hash !== '') {
      janela.location.hash = '#/';   /* a troca de endereço dispara a rota */
      return;
    }
    trataRota(true);
  }

  /* ======================================================================
     12. Edição: cabeça (seção 00, carimbo e avisos)
     ====================================================================== */

  /* Monta a vista inteira da edição. Devolve os filhos de #vista. */
  function montaEdicao(quadro) {
    var contexto = quadro.contexto;
    var h1 = cria('h1', 'so-leitor', ['Edição de ', dataLonga(contexto.data)]);
    atributos(h1, { id: 'titulo-vista', tabindex: '-1' });
    var grade = cria('div', 'grade-painel');
    poe(grade, secaoHoje(quadro), secaoDominios(quadro), secaoIndicadores(quadro));
    if (contexto.falha) {
      /* a rotina não fechou o dia: as seções 04 a 08 dão lugar a uma linha */
      poe(grade, cria('p', 'sem-itens', T.hoje.semItens));
    } else {
      poe(grade, secaoPrincipais(quadro),
        cria('div', 'coluna-lateral', [secaoPlacar(quadro), secaoVigiar(quadro), secaoMovimentos(quadro)]),
        secaoRadar(quadro));
    }
    poe(grade, secaoBastidores(quadro));
    return [h1, montaCabeca(quadro), grade];
  }

  function montaCabeca(quadro) {
    var contexto = quadro.contexto;
    var refs = quadro.refs;
    var cabeca = cria('div', 'cabeca');
    cabeca.setAttribute('id', 's-carimbo');

    /* só no papel: "INFOCENARIUM · edição de 19/11/2026 · nível 3 TENSÃO" */
    var nivel = contexto.alerta.nivel;
    poe(cabeca, soVista(cria('p', 'so-impressao cabeca-impressao',
      T.marca + T.separador + 'edição de ' + dataLonga(contexto.data) + T.separador + 'nível ' + texto(nivel) +
      (busca(contexto.apoio.niveis, nivel) ? ' ' + rotuloDoNivel(contexto.apoio, nivel) : ''))));

    var carimbo = cria('p', 'carimbo');
    carimbo.setAttribute('id', 'carimbo');
    refs.carimboTexto = cria('span', 'carimbo__texto', ['ED. ', tempo(contexto.data, true)]);
    var hora = horaComDia(contexto.edicao.gerada_em, contexto.data);
    if (hora) {
      var quando = cria('time', '', hora);
      quando.setAttribute('datetime', contexto.edicao.gerada_em);
      refs.idade = cria('span', 'carimbo__idade', idade(contexto.geradaEm));
      poe(refs.carimboTexto, T.separador + 'GERADA ', quando, ' (BRASÍLIA)' + T.separador, refs.idade);
    }
    refs.carimboCarga = esconde(cria('span', 'carimbo__carga'), true);
    refs.placas = cria('span', 'marcas');
    poe(carimbo, refs.carimboTexto, refs.carimboCarga, refs.placas);

    refs.avisos = cria('div', 'avisos');
    refs.avisos.setAttribute('id', 'avisos-edicao');
    poe(cabeca, cria('div', 'cabeca__linha', [carimbo, acoesDaCabeca(contexto)]), refs.avisos);
    refazEstadoDaCabeca(quadro);
    return cabeca;
  }

  /* Vizinhas e links: "‹ 18/11", "20/11 ›", texto, JSON, feed. */
  function acoesDaCabeca(contexto) {
    var caixa = cria('div', 'cabeca__acoes');
    var v = contexto.vizinhas;
    if (v.anterior) {
      poe(caixa, linkInterno(hashEdicao(v.anterior.data), [
        soLeitor('Edição anterior, de ' + dataLonga(v.anterior.data)),
        soVista(cria('span', '', [icone('i-dobra', 'icone--volta'), ' ' + dataCurta(v.anterior.data)]))
      ], 'vizinha'));
    }
    if (v.seguinte) {
      poe(caixa, linkInterno(hashEdicao(v.seguinte.data), [
        soLeitor('Edição seguinte, de ' + dataLonga(v.seguinte.data)),
        soVista(cria('span', '', [dataCurta(v.seguinte.data) + ' ', icone('i-dobra')]))
      ], 'vizinha'));
    }
    if (!contexto.ehPainel) { poe(caixa, linkInterno('#/', T.irMaisRecente)); }
    poe(caixa,
      linkArquivo(caminhoDoTexto(contexto.entrada), T.linkTexto),
      linkArquivo(caminhoDaEdicao(contexto.entrada), T.linkJson),
      linkArquivo(ARQ_FEED, T.linkFeed));
    return caixa;
  }

  /* Placas e avisos dependem do relógio (atraso): refeitos juntos. */
  function refazEstadoDaCabeca(quadro) {
    var refs = quadro.refs;
    troca(refs.placas, placasDeEstado(quadro));
    troca(refs.avisos, avisosDaEdicao(quadro));
    if (refs.linhaQuadro) { esconde(refs.linhaQuadro, !quadro.atrasada); }
  }

  function placa(rotuloDaPlaca, grave, nomeDoIcone) {
    return cria('span', 'placa' + (grave ? ' placa--grave' : ''), [nomeDoIcone ? icone(nomeDoIcone) : null, rotuloDaPlaca]);
  }

  /* EXEMPLO e ARQUIVO falam mais alto. No Painel: ATRASADA e o estado. */
  function placasDeEstado(quadro) {
    var contexto = quadro.contexto;
    var placas = [];
    if (contexto.exemplo) { placas.push(placa(T.placas.exemplo, true)); }
    if (!contexto.ehPainel) {
      placas.push(placa(T.placas.arquivo, false));
      return placas;
    }
    if (quadro.atrasada) { placas.push(placa(T.placas.atrasada, true, 'i-relogio')); }
    if (contexto.falha) {
      placas.push(placa(T.placas.semEdicao, true));
    } else if (contexto.edicao.estado === 'reduzida') {
      placas.push(placa(T.placas.reduzida, false));
    } else if (!quadro.atrasada && !contexto.exemplo) {
      placas.push(placa(T.placas.emDia, false));
    }
    return placas;
  }

  /* Avisos do topo, nesta ordem: exemplo, arquivo, sem edição, atrasada,
     reduzida, corrigida, errata, formato novo, dados de apoio em falta. */
  function avisosDaEdicao(quadro) {
    var contexto = quadro.contexto;
    var avisos = [];
    if (contexto.exemplo) {
      avisos.push(aviso({ grave: true, rotulo: T.avisos.exemplo[0], texto: T.avisos.exemplo[1] }));
    }
    if (!contexto.ehPainel) {
      avisos.push(aviso({ rotulo: T.avisos.arquivo, texto: ['Você está lendo a edição de ', tempo(contexto.data, true), '.'] }));
    }
    if (contexto.falha) { avisos.push(avisoSemEdicao(contexto)); }
    if (quadro.atrasada) {
      quadro.refs.horasDeAtraso = cria('span', '', String(horasDesde(contexto.geradaEm)));
      avisos.push(aviso({
        grave: true,
        rotulo: T.avisos.atrasada,
        texto: ['A mais recente é de ', tempo(contexto.data, true), ' e foi gerada há ', quadro.refs.horasDeAtraso,
          ' h. A edição sai todo dia às 18h de Brasília. O quadro abaixo não é de hoje.']
      }));
    }
    if (contexto.edicao.estado === 'reduzida') {
      avisos.push(aviso({ rotulo: T.avisos.reduzida[0], texto: T.avisos.reduzida[1] }));
    }
    avisos.push(avisoCorrigida(contexto), avisoErrata(contexto));
    if (formatoNovo(contexto.edicao)) {
      avisos.push(aviso({ rotulo: T.avisos.formato[0], texto: T.avisos.formato[1] }));
    }
    return avisos.concat(avisosDeApoio(contexto)).filter(function (a) { return a !== null; });
  }

  /* "A rotina de {data} não conseguiu fechar a edição. {resumo} …" */
  function avisoSemEdicao(contexto) {
    /* o resumo da falha começa com "Sem edição hoje." (CONTRATO, seção 4.3),
       o que repetiria o rótulo do aviso */
    var resumo = texto(contexto.edicao.resumo).replace(/^Sem edição hoje\.\s*/, '');
    var partes = ['A rotina de ', tempo(contexto.data, true), ' não conseguiu fechar a edição. ', resumo ? resumo + ' ' : ''];
    if (contexto.anterior) {
      partes.push('Os níveis abaixo repetem os de ', tempo(contexto.anterior.data, true), '. ',
        linkInterno(hashEdicao(contexto.anterior.data), ['Ver a última edição (', tempo(contexto.anterior.data, true), ').']));
    } else {
      partes.push('Ainda não houve edição: todos os níveis estão em 1.');
    }
    return aviso({ grave: true, rotulo: T.avisos.semEdicao, texto: partes });
  }

  /* Data de outra edição: link se ela está no índice; senão, só a data. */
  function dataComLink(contexto, data, item) {
    if (ehData(data) && entradaDaData(contexto.entradas, data)) {
      return linkInterno(hashEdicao(data, ehId(item) ? item : null), tempo(data, true));
    }
    return tempo(data, true);
  }

  function avisoCorrigida(contexto) {
    var datas = lista(contexto.entrada.corrigida_em).filter(ehTexto);
    if (!datas.length) { return null; }
    var partes = ['Há correção a esta edição na errata de '];
    datas.forEach(function (data, i) {
      if (i > 0) { partes.push(i === datas.length - 1 ? ' e ' : ', '); }
      partes.push(dataComLink(contexto, data));
    });
    partes.push('.');
    return aviso({ rotulo: T.avisos.corrigida, texto: partes });
  }

  /* Errata: abre e fecha. */
  function avisoErrata(contexto) {
    var itens = lista(contexto.edicao.errata).filter(ehObjeto);
    if (!itens.length) { return null; }
    var corpo = cria('div', 'aviso__corpo');
    itens.forEach(function (item) { poe(corpo, itemDeErrata(contexto, item)); });
    var abre = botao([T.ver, soLeitor(' a errata'), icone('i-dobra', 'icone--dobra')], '');
    var caixa = aviso({
      rotulo: T.avisos.errata,
      texto: itens.length === 1 ? 'Esta edição corrige 1 ponto de edições anteriores.'
        : 'Esta edição corrige ' + itens.length + ' pontos de edições anteriores.',
      acoes: [abre]
    });
    poe(caixa, corpo);
    ligaDobra(abre, corpo);
    return caixa;
  }

  function itemDeErrata(contexto, errata) {
    var caixa = cria('div', 'errata__item');
    var noIndice = ehData(errata.edicao) && entradaDaData(contexto.entradas, errata.edicao);
    var onde = ['Edição de ', tempo(errata.edicao, true)];
    if (errata.item !== undefined) {
      onde.push(', item ', cria('span', 'mono', texto(errata.item)), '.');
    } else {
      onde.push(', inteira.');
    }
    poe(caixa, cria('p', 'errata__onde',
      noIndice ? linkInterno(hashEdicao(errata.edicao, ehId(errata.item) ? errata.item : null), onde) : onde));
    poe(caixa, cria('p', '', ['Estava errado: ', texto(errata.erro)]));
    poe(caixa, cria('p', '', ['O certo: ', texto(errata.correcao)]));
    if (errata.url !== undefined) { poe(caixa, cria('p', '', linkExterno(errata.url, 'Fonte da correção.'))); }
    if (errata.anula_vetor !== undefined) { poe(caixa, cria('p', '', vetorAnuladoPelaErrata(contexto, errata.anula_vetor))); }
    return caixa;
  }

  /* "Esta correção anula o vetor de {data}: {player} → {sigla}. Ver no registro."
     Vetor que não está no registro: o id cru, sem link. */
  function vetorAnuladoPelaErrata(contexto, idDoVetor) {
    var apoio = contexto.apoio;
    var entrada = busca(apoio.vetoresPorId, idDoVetor);
    if (!entrada || !ehId(idDoVetor) || ehTexto(entrada.anula)) {
      return ['Esta correção anula o vetor ', cria('span', 'id-cru', texto(idDoVetor)), '.'];
    }
    var player = busca(apoio.players, entrada.player);
    return ['Esta correção anula o vetor de ', tempo(entrada.data, true), ': ',
      player ? texto(player.nome) : cria('span', 'id-cru', texto(entrada.player)), ' ', seta(), ' ',
      siglaDoPartido(apoio, entrada.para), '. ', linkInterno(hashRegua('vetores', idDoVetor), 'Ver no registro.')];
  }

  /* A edição aparece com os identificadores crus, e um aviso diz por quê.
     Sem o catálogo não há aviso: o valor sai com 2 a 4 casas. */
  function avisosDeApoio(contexto) {
    var faltas = contexto.faltas.filter(function (arquivo) { return arquivo !== ARQ_CATALOGO; });
    var comFormatoNovo = (formatoNovo(estado.indice) ? [ARQ_INDICE] : []).concat(lista(contexto.apoio.formatosNovos));
    return avisosDeArquivos(faltas, comFormatoNovo);
  }

  /* Um aviso por arquivo que não veio e um por arquivo de formato novo.
     Serve à edição e às vistas Arquivo, Régua e Método. */
  function avisosDeArquivos(faltas, comFormatoNovo) {
    var avisos = [];
    faltas.forEach(function (arquivo) {
      if (arquivo === ARQ_REGUA) {
        avisos.push(aviso({ rotulo: T.avisos.regua[0], texto: T.avisos.regua[1] }));
      } else if (arquivo === ARQ_VEICULOS) {
        avisos.push(aviso({ rotulo: T.avisos.mapa[0], texto: T.avisos.mapa[1] }));
      } else {
        avisos.push(aviso({
          rotulo: T.avisos.apoio,
          texto: ['Não deu para carregar ', cria('span', 'mono', arquivo), '. Alguns nomes aparecem como identificadores.']
        }));
      }
    });
    comFormatoNovo.forEach(function (arquivo) {
      avisos.push(aviso({
        rotulo: T.avisos.formato[0],
        texto: ['O arquivo ', cria('span', 'mono', arquivo), ' usa um formato mais novo que o site.']
      }));
    });
    return avisos;
  }

  /* ======================================================================
     13. Edição: seções 01 a 03 (hoje, domínios, indicadores)
     ====================================================================== */

  /* Edição falha: os níveis só repetem os da edição anterior. */
  function notaDeNiveisRepetidos(contexto) {
    if (!contexto.anterior) { return notaDeSecao(T.hoje.semBase); }
    return notaDeSecao([T.hoje.repetidos, tempo(contexto.anterior.data)]);
  }

  /* Sem edição anterior não houve medida de tendência: o "estável" que a
     regra R14 grava nesse caso não aparece (nem na fala do selo), e a linha
     "Primeira edição: sem comparação." explica. Tendência que não é "estável"
     foi medida contra alguma edição: fica. */
  function tendenciaMedida(contexto, valor) {
    if (!contexto.anterior && valor === 'estavel') { return null; }
    return valor;
  }

  function secaoHoje(quadro) {
    var contexto = quadro.contexto;
    var apoio = contexto.apoio;
    var alerta = contexto.alerta;
    var nivel = alerta.nivel;
    var classe = nivelValido(nivel) ? nivel : 0;
    var s = secao('hoje', '01', T.titulos.hoje, contexto);
    if (contexto.falha) { poe(s.corpo, notaDeNiveisRepetidos(contexto)); }

    var bloco = cria('div', 'alerta nivel-' + classe);
    var rotuloLinha = cria('p', 'alerta__rotulo');
    if (classe) { poe(rotuloLinha, icone('i-nivel-' + classe, 'icone--28')); }
    var tendenciaDoDia = tendenciaMedida(contexto, alerta.tendencia);
    poe(rotuloLinha, cria('span', '', rotuloDoNivel(apoio, nivel)), tendenciaDoDia ? tendencia(tendenciaDoDia) : null);
    var topo = cria('div', 'alerta__topo', [
      cria('p', 'alerta__numero', [cria('span', 'alerta__numeral', texto(nivel) || T.travessao), cria('span', 'alerta__de', T.hoje.de5)]),
      cria('div', '', [rotuloLinha, medidor(nivel, true)])
    ]);
    poe(bloco, cria('p', 'so-leitor', nivelFalado(apoio, nivel, tendenciaDoDia)), soVista(topo));

    poe(bloco, linhaAntes(contexto), linhaDesde(contexto));
    quadro.refs.linhaQuadro = esconde(cria('p', 'alerta__linha', ['Quadro de ', tempo(contexto.data), ', não de hoje.']), !quadro.atrasada);
    poe(bloco, quadro.refs.linhaQuadro);
    poe(bloco, cria('p', 'alerta__resumo', texto(contexto.edicao.resumo)));
    if (texto(alerta.motivo)) {
      poe(bloco, cria('p', 'alerta__motivo', [cria('span', 'item-rotulo', T.hoje.motivo), ' ', texto(alerta.motivo)]));
    }
    var linhaDoNivel = busca(apoio.niveis, nivel);
    if (linhaDoNivel && texto(linhaDoNivel.significado)) {
      poe(bloco, cria('p', 'alerta__significado', texto(linhaDoNivel.significado)));
    }
    poe(bloco, historicoDoAlerta(quadro));
    poe(s.corpo, bloco);
    return s.raiz;
  }

  /* "antes (18/11): 2 ATENÇÃO", pelo índice. */
  function linhaAntes(contexto) {
    var anterior = contexto.anterior;
    if (!anterior) { return cria('p', 'alerta__linha', T.hoje.primeira); }
    return cria('p', 'alerta__linha', ['antes (', tempo(anterior.data), '): ', texto(anterior.nivel), ' ',
      busca(contexto.apoio.niveis, anterior.nivel) ? rotuloDoNivel(contexto.apoio, anterior.nivel) : '']);
  }

  /* "Desde 18/11: energia 1 → 3 · conflito 1 → 3": os domínios cujo nível
     mudou, comparando com os níveis da edição anterior no índice. */
  function linhaDesde(contexto) {
    var anterior = contexto.anterior;
    if (!anterior || !ehObjeto(anterior.niveis)) { return null; }
    var mudancas = [];
    var comparados = 0;
    dominiosDaEdicao(contexto).forEach(function (dominio) {
      if (!tem(anterior.niveis, dominio.id) || !ehNumero(anterior.niveis[dominio.id])) { return; }
      comparados += 1;
      var antes = anterior.niveis[dominio.id];
      if (antes === dominio.nivel) { return; }
      if (mudancas.length) { mudancas.push(T.separador); }
      mudancas.push(cria('span', '', [
        nomeDoDominio(contexto.apoio, dominio.id).toLocaleLowerCase('pt-BR') + ' ' + texto(antes) + ' ',
        seta(), ' ' + texto(dominio.nivel)
      ]));
    });
    if (!comparados) { return null; }
    return cria('p', 'alerta__linha', ['Desde ', tempo(anterior.data), ': ', mudancas.length ? mudancas : T.hoje.nenhumMudou]);
  }

  /* Os domínios da edição, na ordem da régua. Os que a régua não conhece
     ficam no fim, na ordem do arquivo. */
  function dominiosDaEdicao(contexto) {
    var ordem = contexto.apoio.ordemDominios;
    var itens = lista(contexto.alerta.dominios).filter(ehObjeto);
    function posicao(d) {
      var i = ordem.indexOf(d.id);
      return i === -1 ? ordem.length : i;
    }
    return itens.map(function (d, i) { return { d: d, i: i }; })
      .sort(function (a, b) { return posicao(a.d) - posicao(b.d) || a.i - b.i; })
      .map(function (par) { return par.d; });
  }

  /* Fita "ALERTA, 30 DIAS", com a tabela gêmea. Edição de exemplo não tem
     fita; com menos de 2 edições no histórico, ela também não aparece. */
  function historicoDoAlerta(quadro) {
    var contexto = quadro.contexto;
    var historico = contexto.historico;
    if (contexto.exemplo || historico.length < 2) { return null; }
    var apoio = contexto.apoio;
    var caixa = cria('div', 'historico');
    var corpoDaTabela = cria('div', '');
    var textoDoBotao = cria('span', '', T.verTabela);
    var abre = botao(textoDoBotao, 'botao--texto');
    poe(caixa, cria('div', 'historico__topo', [subtitulo(T.hoje.fita), abre]));

    var desenhoDaFita = fita({
      apoio: apoio,
      historico: historico,
      fim: contexto.data,
      emTela: contexto.data,
      nome: nomeDaFita('Alerta', historico, nivelGeral, contexto.ehPainel ? 'hoje' : 'nesta edição', contexto.alerta.nivel)
    });
    quadro.fechaDicaDaFita = desenhoDaFita.fechaDica;
    poe(caixa, desenhoDaFita.raiz);

    poe(corpoDaTabela, tabelaDoAlerta(apoio, historico, T.hoje.fita));
    poe(caixa, corpoDaTabela);
    var dobra = ligaDobra(abre, corpoDaTabela);
    dobra.aoPor = function (aberta) { troca(textoDoBotao, aberta ? T.esconderTabela : T.verTabela); };
    return caixa;
  }

  function nivelGeral(entrada) {
    return entrada.nivel;
  }

  /* O nome que resume a fita: "Alerta nos últimos 30 dias: de 1 a 3; hoje, 3".
     Edição falha só repete níveis: fica fora do menor e do maior. */
  function nomeDaFita(oQue, historico, nivelDe, quando, nivelDeAgora) {
    var niveis = historico.filter(function (e) { return e.estado !== 'falha' && nivelValido(nivelDe(e)); }).map(nivelDe);
    var nome = oQue + ' nos últimos ' + DIAS_HISTORICO + ' dias';
    if (niveis.length) { nome += ': de ' + Math.min.apply(null, niveis) + ' a ' + Math.max.apply(null, niveis); }
    return nome + (nivelValido(nivelDeAgora) ? '; ' + quando + ', ' + nivelDeAgora : '');
  }

  /* A tabela gêmea da fita de alerta: mais nova primeiro; a data leva à edição. */
  function tabelaDoAlerta(apoio, historico, legenda) {
    var linhas = historico.slice().reverse().map(function (e) {
      return [linkInterno(hashEdicao(e.data), tempo(e.data, true)),
        texto(e.nivel) + (busca(apoio.niveis, e.nivel) ? ' ' + rotuloDoNivel(apoio, e.nivel) : ''),
        rotulo('estado', e.estado)];
    });
    return tabela(legenda, [T.arquivo.data, T.arquivo.nivel, T.arquivo.estado], linhas);
  }

  /* Fita de 30 dias, um espaço por dia, que termina em opcoes.fim.
     opcoes: apoio, historico, fim, nome, emTela (a data da edição em tela, ou
     null), nivelDe (o nível de uma entrada; sem ele, o geral), pequena.
     A fita pequena é a de um domínio, no Arquivo: sem grade, sem dica e sem
     clique. Devolve { raiz, fechaDica }. */
  function fita(opcoes) {
    var pequena = opcoes.pequena === true;
    var nivelDe = opcoes.nivelDe || nivelGeral;
    var raiz = cria('div', 'fita' + (pequena ? ' fita--pequena' : ''));
    atributos(raiz, { role: 'img', 'aria-label': opcoes.nome });
    var caixaDosDias = cria('div', 'fita__desenho');
    var dica = pequena ? null : soVista(cria('div', 'dica'));
    if (!pequena) {
      for (var f = 1; f <= NIVEL_MAXIMO; f += 1) { poe(caixaDosDias, cria('span', 'fita__fio fita__fio--' + f)); }
    }
    var porData = tabelaPorId(opcoes.historico, 'data');
    var ultimo = numeroDoDia(opcoes.fim);
    for (var i = DIAS_HISTORICO - 1; i >= 0; i -= 1) {
      poe(caixaDosDias, diaDaFita(opcoes, busca(porData, dataDoNumero(ultimo - i)), nivelDe, dica));
    }
    poe(raiz, caixaDosDias);
    if (pequena) { return { raiz: raiz, fechaDica: null }; }
    raiz.addEventListener('mouseleave', function () { dica.classList.remove('dica--aberta'); });
    poe(raiz, cria('div', 'fita__datas', [
      cria('span', '', dataCurta(dataDoNumero(ultimo - DIAS_HISTORICO + 1))), cria('span', '', dataCurta(opcoes.fim))
    ]), dica);
    return {
      raiz: raiz,
      fechaDica: function () {
        var aberta = dica.classList.contains('dica--aberta');
        dica.classList.remove('dica--aberta');
        return aberta;
      }
    };
  }

  /* Um dia da fita: coluna de 8 px por nível; falha é um traço na base;
     dia sem edição é espaço vazio. Na fita grande o clique leva à edição (só
     ponteiro: pelo teclado, o caminho é a tabela). */
  function diaDaFita(opcoes, entrada, nivelDe, dica) {
    if (!entrada) { return cria('span', 'fita__dia'); }
    var nivel = nivelDe(entrada);
    var falha = entrada.estado === 'falha';
    var classe = 'fita__coluna';
    if (falha) { classe += ' fita__coluna--falha'; } else if (nivelValido(nivel)) { classe += ' fita__coluna--n' + nivel; }
    if (entrada.data === opcoes.emTela) { classe += ' fita__coluna--atual'; }
    if (!dica) { return cria('span', 'fita__dia', cria('span', classe)); }
    var dia = linkInterno(hashEdicao(entrada.data), null, 'fita__dia');
    atributos(dia, { tabindex: '-1', 'aria-hidden': 'true' });
    poe(dia, cria('span', classe));
    dia.addEventListener('mouseenter', function () {
      var valor = falha ? rotulo('estado', 'falha')
        : 'nível ' + texto(nivel) + (busca(opcoes.apoio.niveis, nivel) ? ' ' + rotuloDoNivel(opcoes.apoio, nivel) : '');
      troca(dica, cria('span', 'dica__valor', valor), ' ', cria('span', '', dataCurta(entrada.data)));
      dica.classList.add('dica--aberta');
    });
    return dia;
  }

  /* ----- 02 Domínios ----- */

  function secaoDominios(quadro) {
    var contexto = quadro.contexto;
    var s = secao('dominios', '02', T.titulos.dominios, contexto);
    if (contexto.falha) { poe(s.corpo, notaDeNiveisRepetidos(contexto)); }
    var dominios = dominiosDaEdicao(contexto);
    if (!dominios.length) { poe(s.corpo, fraseVazia(T.travessao)); }
    dominios.forEach(function (dominio) { poe(s.corpo, linhaDeDominio(quadro, dominio)); });
    return s.raiz;
  }

  /* Nome de um indicador: o da edição; se não achar, o do catálogo; senão, o id. */
  function nomeDoIndicador(contexto, id) {
    var naEdicao = busca(tabelaPorId(contexto.edicao.indicadores), id);
    if (naEdicao && texto(naEdicao.nome)) { return naEdicao.nome; }
    var noCatalogo = busca(contexto.apoio.catalogo, id);
    return noCatalogo && texto(noCatalogo.nome) ? noCatalogo.nome : texto(id);
  }

  function linhaDeDominio(quadro, dominio) {
    var contexto = quadro.contexto;
    var apoio = contexto.apoio;
    var id = dominio.id;
    var nome = nomeDoDominio(apoio, id);
    var gatilhos = lista(dominio.gatilhos).filter(ehObjeto);
    var mantido = !gatilhos.length && ehNumero(dominio.nivel) && dominio.nivel > 1;
    var raiz = cria('div', 'dominio dominio--fechado');
    if (ehId(id)) { raiz.setAttribute('id', 'dominio-' + id); }

    var titulo = cria('h3', 'dominio__nome', nome);
    titulo.setAttribute('tabindex', '-1');
    var nomeDoBotao = soLeitor('Abrir: ' + nome);
    var abre = botao([icone('i-dobra', 'icone--dobra'), nomeDoBotao], 'botao--dobra dominio__botao');
    var tendenciaDoDominio = tendenciaMedida(contexto, dominio.tendencia);
    var movimento = cria('span', 'dominio__tendencia', tendenciaDoDominio ? soVista(tendencia(tendenciaDoDominio)) : null);
    var antes = contexto.anterior && ehObjeto(contexto.anterior.niveis) && tem(contexto.anterior.niveis, id)
      ? contexto.anterior.niveis[id] : null;
    if (ehNumero(antes) && antes !== dominio.nivel) {
      poe(movimento, separador(), cria('span', '', 'era ' + antes));
    }
    var cabeca = cria('div', 'dominio__cabeca', [
      titulo, cria('span', 'dominio__medidor', medidor(dominio.nivel)),
      cria('span', 'dominio__selo', selo(apoio, dominio.nivel, tendenciaDoDominio)), movimento, abre
    ]);
    poe(raiz, cabeca);

    var semPreco = lista(dominio.sem_preco).filter(ehTexto);
    if (semPreco.length) {
      poe(raiz, cria('p', 'dominio__sem-preco', [icone('i-aviso', 'icone--14'), T.dominios.semPreco +
        semPreco.map(function (idDoIndicador) { return nomeDoIndicador(contexto, idDoIndicador); }).join(', ')]));
    }
    poe(raiz, cria('p', 'dominio__leitura', [
      mantido ? etiqueta([T.dominios.mantido, tempo(dominio.desde)]) : null, mantido ? ' ' : null, texto(dominio.leitura)
    ]));

    var corpo = cria('div', 'dominio__corpo');
    var daRegua = busca(apoio.dominios, id);
    if (daRegua && texto(daRegua.descricao)) { poe(corpo, cria('p', '', texto(daRegua.descricao))); }
    if (daRegua && texto(daRegua.canal)) {
      poe(corpo, subtitulo(T.dominios.comoChega, 'h4'), cria('p', '', texto(daRegua.canal)));
    }
    poe(corpo, cria('p', 'dominio__desde', ['Neste nível desde ', tempo(dominio.desde, true), '.']));
    poe(corpo, subtitulo(T.dominios.gatilhos, 'h4'));
    if (gatilhos.length) {
      poe(corpo, cria('ul', 'gatilhos', gatilhos.map(function (g) { return linhaDeGatilho(quadro, g); })));
    } else if (mantido) {
      poe(corpo, cria('p', '', [etiqueta([T.dominios.mantido, tempo(dominio.desde)]), ' ', T.dominios.semGatilhoNovo]));
    } else {
      poe(corpo, fraseVazia(T.dominios.nenhumGatilho));
    }
    poe(corpo, subtitulo(T.dominios.proximo, 'h4'), cria('p', '', texto(dominio.vigiar)));
    poe(raiz, corpo);

    var dobra = ligaDobra(abre, corpo, function (aberta) {
      if (ehId(id)) { gravaItemNoEndereco(quadro, id, aberta); }
    });
    dobra.aoPor = function (aberta) {
      troca(nomeDoBotao, (aberta ? 'Fechar: ' : 'Abrir: ') + nome);
      raiz.classList.toggle('dominio--fechado', !aberta);
    };
    cabecaAbre(cabeca, dobra);
    if (ehId(id) && !(id in quadro.refs.dominios)) {
      quadro.refs.dominios[id] = { raiz: raiz, dobra: dobra, foco: titulo };
    }
    return raiz;
  }

  /* "principal 1" ou "radar 4"; null se o id não é item desta edição. */
  function rotuloDoItem(contexto, id) {
    if (!busca(contexto.itens, id)) { return null; }
    var ehPrincipal = lista(contexto.edicao.principais).indexOf(contexto.itens[id]) !== -1;
    return (ehPrincipal ? 'principal ' : 'radar ') + numeroDoItem(id);
  }

  /* Link para um item desta edição; sem o item, o id cru, sem link. */
  function linkParaItem(contexto, id, prefixo) {
    var nome = rotuloDoItem(contexto, id);
    if (nome === null) { return cria('span', 'id-cru', texto(id)); }
    return linkInterno(hashEdicao(contexto.data, id), (prefixo || '') + nome);
  }

  function linhaDeGatilho(quadro, gatilho) {
    var contexto = quadro.contexto;
    var linha = cria('li', 'gatilho');
    /* sem código, não há link: link sem texto não tem nome para o leitor de tela */
    poe(linha, texto(gatilho.criterio) ? linkInterno(hashMetodo('niveis'), texto(gatilho.criterio), 'gatilho__criterio') : null,
      cria('span', 'gatilho__texto', texto(gatilho.texto)));
    if (gatilho.excecao === true) { poe(linha, etiquetaComDica(T.dominios.excecao, T.dominios.dicaExcecao)); }
    if (gatilho.alivio === true) { poe(linha, etiquetaComDica(T.dominios.alivio, T.dominios.dicaAlivio)); }
    var ref = gatilho.ref;
    var destino;
    if (rotuloDoItem(contexto, ref) !== null) {
      destino = linkParaItem(contexto, ref, 'ver ');
    } else if (ehId(ref) && busca(tabelaPorId(contexto.edicao.indicadores), ref)) {
      destino = linkInterno(hashEdicao(contexto.data, ref), 'ver indicador: ' + nomeDoIndicador(contexto, ref));
    } else {
      destino = cria('span', 'id-cru', texto(ref));
    }
    poe(linha, cria('span', 'gatilho__ref', destino));
    return linha;
  }

  /* Etiqueta de domínio: leva à linha do domínio nesta edição.
     Domínio que a régua não conhece: o id cru, sem link e sem etiqueta. */
  function etiquetaDeDominio(quadro, id) {
    var apoio = quadro.contexto.apoio;
    if (!ehId(id) || (apoio.temRegua && !busca(apoio.dominios, id))) { return cria('span', 'id-cru', texto(id)); }
    if (!busca(quadro.refs.dominios, id)) { return etiqueta(nomeDoDominio(apoio, id)); }
    return linkInterno(hashEdicao(quadro.data, id), nomeDoDominio(apoio, id), 'etiqueta');
  }

  /* ----- 03 Indicadores ----- */

  function secaoIndicadores(quadro) {
    var contexto = quadro.contexto;
    var s = secao('indicadores', '03', T.titulos.indicadores, contexto);
    var indicadores = lista(contexto.edicao.indicadores).filter(ehObjeto);
    if (!indicadores.length) {
      poe(s.corpo, fraseVazia(T.indicadores.nenhum));
      return s.raiz;
    }
    /* ids que são ref de algum gatilho de hoje */
    var comGatilho = Object.create(null);
    lista(contexto.alerta.dominios).forEach(function (dominio) {
      lista(ehObjeto(dominio) ? dominio.gatilhos : null).forEach(function (g) {
        if (ehObjeto(g) && ehTexto(g.ref)) { comGatilho[g.ref] = true; }
      });
    });
    poe(s.corpo, cria('ul', 'fichas', indicadores.map(function (indicador) {
      return fichaDeIndicador(quadro, indicador, comGatilho);
    })));
    return s.raiz;
  }

  /* Casas decimais do valor: as do catálogo; sem o campo, 2; sem o catálogo, null. */
  function casasDoIndicador(apoio, id) {
    if (!apoio.temCatalogo) { return null; }
    var doCatalogo = busca(apoio.catalogo, id);
    var casas = doCatalogo ? doCatalogo.casas : undefined;
    return ehNumero(casas) && casas >= 0 && casas <= 6 && Math.floor(casas) === casas ? casas : 2;
  }

  function fichaDeIndicador(quadro, indicador, comGatilho) {
    var contexto = quadro.contexto;
    var id = indicador.id;
    var temValor = ehNumero(indicador.valor);
    var ficha = cria('li', 'ficha');
    if (ehId(id)) {
      atributos(ficha, { id: 'ind-' + id, tabindex: '-1' });
      if (!(id in quadro.refs.indicadores)) { quadro.refs.indicadores[id] = ficha; }
    }
    poe(ficha, cria('h3', 'ficha__nome', texto(indicador.nome) || texto(id)));
    if (temValor) {
      poe(ficha, cria('p', 'ficha__valor', valorDeIndicador(indicador.valor, casasDoIndicador(contexto.apoio, id))));
    } else {
      poe(ficha, cria('p', 'ficha__valor ficha__valor--sem', T.indicadores.semDado));
    }
    poe(ficha, cria('p', 'ficha__unidade', texto(indicador.unidade)));
    if (temValor) {
      poe(ficha, cria('dl', 'ficha__variacoes', [
        cria('div', 'ficha__variacao', [
          comDica(cria('dt', '', T.indicadores.anterior), T.indicadores.dicaAnterior),
          cria('dd', '', variacao(indicador.variacao_pct))
        ]),
        cria('div', 'ficha__variacao', [cria('dt', '', T.indicadores.seteDias), cria('dd', '', variacao(indicador.variacao_7d_pct))])
      ]));
    }
    var pe = cria('p', 'ficha__pe');
    if (ehTexto(id) && comGatilho[id]) { poe(pe, etiqueta(T.indicadores.gatilho)); }
    if (temValor && indicador.defasado === true) { poe(pe, etiqueta(['DE ', tempo(indicador.data)])); }
    if (indicador.dominio !== undefined) { poe(pe, etiquetaDeDominio(quadro, indicador.dominio)); }
    var fonte = ehObjeto(indicador.fonte) ? indicador.fonte : null;
    /* Sem valor, a fonte é só a primeira do catálogo, e não a usada no dia
       (ESQUEMA, seção 5): o nome, sem link, como fonte prevista. */
    if (fonte && temValor) { poe(pe, linkExterno(fonte.url, T.indicadores.fonte + texto(fonte.nome))); }
    if (fonte && !temValor) { poe(pe, cria('span', 'texto-2', T.indicadores.fontePrevista + texto(fonte.nome))); }
    poe(ficha, pe);
    return ficha;
  }

  /* ======================================================================
     14. Edição: itens (04 principais, 08 radar e o dossiê)
     Principal e radar usam as mesmas linhas e as mesmas etiquetas.
     ====================================================================== */

  /* Com o mapa de veículos em rascunho, a nota vem logo abaixo do título. */
  function notaDeRascunho(contexto) {
    if (!contexto.apoio.mapaRascunho) { return null; }
    return notaDeSecao([T.avisos.rascunho + ' ', linkInterno(hashRegua('veiculos'), T.avisos.verMapa)]);
  }

  /* "CONTINUAÇÃO DE 18/11": leva ao item anterior, se a edição está no índice.
     Senão, só a data, sem link e sem etiqueta. */
  function continuacao(contexto, valor) {
    if (valor === undefined) { return null; }
    var partes = texto(valor).split('/');
    var formaCerta = partes.length === 2 && ehData(partes[0]) &&
      (FORMA_ITEM_PRINCIPAL.test(partes[1]) || FORMA_ITEM_RADAR.test(partes[1]));
    if (!formaCerta) { return cria('span', 'id-cru', texto(valor)); }
    var conteudo = [T.itens.continuacao, tempo(partes[0])];
    if (!entradaDaData(contexto.entradas, partes[0])) { return cria('span', 'rotulo', conteudo); }
    return linkInterno(hashEdicao(partes[0], partes[1]), conteudo, 'etiqueta');
  }

  /* Categoria, confiança, domínios, conflito e continuação: as marcas do item. */
  function marcasDoItem(quadro, item, opcoes) {
    var caixa = cria('p', 'marcas');
    if (opcoes.categoria && texto(item.categoria)) { poe(caixa, etiqueta(rotulo('categoriaEtiqueta', item.categoria))); }
    if (opcoes.confianca && texto(item.confianca)) { poe(caixa, etiqueta(rotulo('confiancaEtiqueta', item.confianca))); }
    if (opcoes.dominios) {
      lista(item.dominios).forEach(function (id) { poe(caixa, etiquetaDeDominio(quadro, id)); });
    }
    if (opcoes.conflito && item.conflito_de_interesse === true) { poe(caixa, etiqueta(T.itens.conflito)); }
    if (opcoes.continuacao) { poe(caixa, continuacao(quadro.contexto, item.continuacao_de)); }
    return caixa;
  }

  /* O alvo de um ataque, depois da seta. "nenhum": "sem alvo", sem seta.
     comLinks: player e partido levam à Régua (alvo "outro" é texto simples). */
  function alvoDoAtaque(contexto, ataque, comLinks) {
    var apoio = contexto.apoio;
    var alvo = ataque.alvo;
    if (alvo === 'nenhum') {
      var semAlvo = cria('span', 'texto-2', T.itens.semAlvo);
      return comLinks ? comDica(semAlvo, T.itens.dicaSemAlvo) : [separador(), semAlvo];
    }
    var nome;
    if (alvo === 'outro') {
      nome = cria('span', '', texto(ataque.alvo_nome));
    } else if (busca(apoio.partidos, alvo)) {
      nome = comLinks && ehId(alvo) ? linkInterno(hashRegua('partidos', alvo), nomeDoPartido(apoio, alvo)) : cria('span', '', nomeDoPartido(apoio, alvo));
    } else if (playerDe(contexto, alvo)) {
      var nomeDoPlayer = texto(playerDe(contexto, alvo).nome) || texto(alvo);
      /* player novo que ainda não está em players.json fica sem link */
      nome = comLinks && ehId(alvo) && busca(apoio.players, alvo) ? linkInterno(hashRegua('players', alvo), nomeDoPlayer) : cria('span', '', nomeDoPlayer);
    } else {
      nome = cria('span', 'id-cru', texto(alvo));
    }
    return [seta('atira em'), nome];
  }

  /* Fogo amigo: o alvo é o partido do lado, ou um player dele. */
  function ehFogoAmigo(contexto, ataque) {
    if (!ehTexto(ataque.lado) || ataque.alvo === 'outro' || ataque.alvo === 'nenhum') { return false; }
    if (ataque.alvo === ataque.lado) { return true; }
    if (busca(contexto.apoio.partidos, ataque.alvo)) { return false; }
    var player = playerDe(contexto, ataque.alvo);
    return !!player && player.partido === ataque.lado;
  }

  /* Veículo do mapa: nome com link para a Régua. Fora do mapa: o id. */
  function nomeDoVeiculo(apoio, id, comLink, classe) {
    var veiculo = busca(apoio.veiculos, id);
    if (!veiculo) { return cria('span', 'id-cru' + (classe ? ' ' + classe : ''), texto(id)); }
    var nome = texto(veiculo.nome) || texto(id);
    return comLink && ehId(id) ? linkInterno(hashRegua('veiculos', id), nome, classe) : cria('span', classe || '', nome);
  }

  /* Uma linha curta por ataque: "NYT [OG] → República de Exemplo". */
  function resumoDosAtaques(contexto, ataques) {
    var partes = [];
    ataques.forEach(function (ataque, i) {
      if (i > 0) { partes.push(separador()); }
      partes.push(nomeDoVeiculo(contexto.apoio, ataque.veiculo, false), siglaDoPartido(contexto.apoio, ataque.lado),
        alvoDoAtaque(contexto, ataque, false));
    });
    return partes;
  }

  /* Placar em siglas: "ER +2 · CA −2 · SO +1 narrativa"; vazio: "sem ganhador". */
  function resumoDoPlacar(contexto, placar) {
    var linhas = lista(placar).filter(ehObjeto);
    if (!linhas.length) { return [cria('span', 'texto-2', T.itens.semGanhador)]; }
    var partes = [];
    linhas.forEach(function (linha, i) {
      if (i > 0) { partes.push(separador()); }
      var sinal = linha.efeito === 'ganha' ? '+' : (linha.efeito === 'perde' ? '−' : '');
      partes.push(siglaDoPartido(contexto.apoio, linha.partido),
        cria('span', 'mono', [sinal + texto(linha.forca), tem(ROTULOS.efeito, linha.efeito) ? soLeitor(' (' + rotulo('efeito', linha.efeito) + ')') : null]));
      if (linha.evidencia === 'narrativa') { partes.push(cria('span', 'texto-2', T.itens.narrativa)); }
    });
    return partes;
  }

  /* ----- 04 Principais ----- */

  function secaoPrincipais(quadro) {
    var contexto = quadro.contexto;
    var s = secao('principais', '04', T.titulos.principais, contexto);
    poe(s.corpo, notaDeRascunho(contexto));
    var principais = lista(contexto.edicao.principais).filter(ehObjeto);
    if (!principais.length) { poe(s.corpo, fraseVazia(T.travessao)); }
    principais.forEach(function (item) { poe(s.corpo, cartaoDePrincipal(quadro, item)); });
    return s.raiz;
  }

  function cartaoDePrincipal(quadro, item) {
    var contexto = quadro.contexto;
    var id = item.id;
    var raiz = cria('article', 'principal');
    if (ehId(id)) { raiz.setAttribute('id', 'item-' + id); }
    var titulo = cria('h3', 'principal__titulo', texto(item.titulo));
    titulo.setAttribute('tabindex', '-1');
    var resumo = cria('div', 'principal__resumo', [
      cria('p', 'principal__fato', texto(item.fato)),
      cria('p', 'principal__linha', [cria('span', 'item-rotulo', T.itens.atirou), resumoDosAtaques(contexto, lista(item.ataques).filter(ehObjeto))]),
      cria('p', 'principal__linha', [cria('span', 'item-rotulo', T.itens.placar), resumoDoPlacar(contexto, item.placar)])
    ]);
    var textoDoBotao = cria('span', '', T.itens.abrir);
    var abre = botao([textoDoBotao, soLeitor(': ' + texto(item.titulo)), icone('i-dobra', 'icone--dobra')], '');
    var dossie = cria('div', 'dossie', partesDoDossie(quadro, item));
    poe(raiz,
      cria('p', 'principal__num', [soLeitor('Principal '), numeroDoItem(id)]),
      cria('div', 'principal__corpo', [
        marcasDoItem(quadro, item, { categoria: true, confianca: true, dominios: true, conflito: true, continuacao: true }),
        titulo, resumo, cria('p', 'principal__pe', abre)
      ]),
      dossie);
    var dobra = ligaDobra(abre, dossie, function (aberta) {
      if (ehId(id)) { gravaItemNoEndereco(quadro, id, aberta); }
    });
    /* aberto, o dossiê já traz o fato, os ataques e o placar por inteiro */
    dobra.aoPor = function (aberta) {
      troca(textoDoBotao, aberta ? T.itens.fechar : T.itens.abrir);
      esconde(resumo, aberta);
    };
    if (ehId(id) && !(id in quadro.refs.principais)) {
      quadro.refs.principais[id] = { raiz: raiz, dobra: dobra, foco: titulo };
    }
    return raiz;
  }

  function tituloDeParte(conteudo) {
    return cria('h4', 'dossie__titulo', conteudo);
  }

  function listaDeTextos(itens) {
    var textos = lista(itens).filter(ehTexto);
    if (!textos.length) { return fraseVazia(T.travessao); }
    return cria('ul', 'lista', textos.map(function (t) { return cria('li', '', t); }));
  }

  /* Aviso fixo do item com conflito de interesse (palavra por palavra) e,
     quando a lista de conflito da régua conhece o vínculo, os nomes dela que
     o item envolve. Sem nome conhecido (só "notícia de IA"), só o aviso fixo. */
  function avisoDeConflito(contexto, item) {
    var nomes = vinculosDoConflito(contexto.apoio, item);
    var vinculo = nomes.length ? T.itens.conflitoVinculo + nomes.join(', ') + '. ' : '';
    return aviso({
      classe: 'conflito-aviso',
      rotulo: T.itens.conflito,
      texto: [T.itens.avisoConflito + ' ' + vinculo + T.itens.conflitoConfianca + ' ', linkInterno(hashMetodo('conflito'), T.itens.verMetodo)]
    });
  }

  /* Os nomes da lista de conflito da régua que o item envolve, na ordem da
     lista: player citado como alvo ou em vetor (pelo nome da ficha) e termo
     escrito em algum texto do item, palavra inteira, como a regra R19 lê.
     Termo que já está dentro de um nome da lista não se repete. */
  function vinculosDoConflito(apoio, item) {
    var conflito = ehObjeto(apoio.regua) && ehObjeto(apoio.regua.conflito) ? apoio.regua.conflito : null;
    if (!conflito || !ehObjeto(item)) { return []; }
    var citados = lista(item.ataques).concat([item.ataque]).filter(ehObjeto).map(function (a) { return a.alvo; })
      .concat(lista(item.vetores).filter(ehObjeto).map(function (v) { return v.player; }));
    var nomes = [];
    lista(conflito.players).filter(ehTexto).forEach(function (id) {
      if (citados.indexOf(id) === -1) { return; }
      var player = busca(apoio.players, id);
      var nome = player && ehTexto(player.nome) ? player.nome : id;
      if (nomes.indexOf(nome) === -1) { nomes.push(nome); }
    });
    var textos = textosDoItem(item);
    lista(conflito.termos).filter(ehTexto).forEach(function (termo) {
      if (nomes.some(function (nome) { return nome.indexOf(termo) !== -1; })) { return; }
      var forma = formaDoTermo(termo);
      if (textos.some(function (t) { return forma.test(t); })) { nomes.push(termo); }
    });
    return nomes;
  }

  /* O termo como palavra inteira, escrito como na lista: o texto é
     escapado e nunca vira expressão. As classes \p{L} e \p{N} pedem
     navegador de 2018 em diante (Firefox 78, Chrome 64, Safari 11.1); no
     mais velho, a expressão nem se monta, e o erro derrubaria a edição
     inteira. Lá, a palavra inteira se mede só com as letras latinas. */
  function formaDoTermo(termo) {
    var escapado = termo.replace(/[\\^$.*+?()[\]{}|\/]/g, '\\$&');
    try {
      return new RegExp('(^|[^\\p{L}\\p{N}_-])' + escapado + '(?![\\p{L}\\p{N}_])', 'u');
    } catch (erro) {
      return new RegExp('(^|[^A-Za-z0-9\\u00C0-\\u024F_-])' + escapado + '(?![A-Za-z0-9\\u00C0-\\u024F_])');
    }
  }

  /* Todos os textos de um item, menos os campos url (a regra R19 lê assim).
     Sem recursão: item com níveis demais não derruba a página. */
  function textosDoItem(item) {
    var textos = [];
    var pilha = [item];
    while (pilha.length) {
      var valor = pilha.pop();
      if (ehTexto(valor)) {
        textos.push(valor);
      } else if (Array.isArray(valor)) {
        pilha.push.apply(pilha, valor);
      } else if (ehObjeto(valor)) {
        Object.keys(valor).forEach(function (chave) { if (chave !== 'url') { pilha.push(valor[chave]); } });
      }
    }
    return textos;
  }

  /* O dossiê de uma principal. Parte sem conteúdo diz o que falta: nunca some. */
  function partesDoDossie(quadro, item) {
    var contexto = quadro.contexto;
    var ataques = lista(item.ataques).filter(ehObjeto);
    var fontes = lista(item.fontes).filter(ehObjeto);
    var naoConfirmado = lista(item.nao_confirmado).filter(ehTexto);
    var partes = [];
    if (item.conflito_de_interesse === true) { partes.push(avisoDeConflito(contexto, item)); }
    partes.push(tituloDeParte(T.itens.aconteceu), cria('p', '', texto(item.fato)));
    if (naoConfirmado.length) {
      partes.push(cria('p', 'dossie__titulo', T.itens.naoConfirmado), listaDeTextos(naoConfirmado));
    }
    partes.push(tituloDeParte(T.itens.quemAtirou + ' (' + ataques.length + ')'),
      cria('div', '', ataques.map(function (a) { return linhaDeAtaque(quadro, a); })));
    partes.push(tituloDeParte(T.itens.realmente), cria('p', 'dossie__realmente', texto(item.realmente) || T.travessao));
    partes.push(tituloDeParte(T.itens.naPratica), listaDeTextos(item.na_pratica));
    partes.push(tituloDeParte(T.itens.atoNaRegua), linhaDeEixo(contexto, item.eixo));
    partes.push(tituloDeParte(T.itens.quemGanha), placarDoItem(contexto, item));
    partes.push(tituloDeParte(T.itens.movimentos), vetoresDoItem(quadro, item));
    partes.push(tituloDeParte(T.itens.preparo), preparoDoItem(quadro, item));
    partes.push(tituloDeParte(T.itens.fontes + ' (' + fontes.length + ')'),
      cria('div', '', fontes.map(function (f) { return linhaDeFonte(contexto, f, ladosDosAtaques(ataques)); })));
    return partes;
  }

  /* Quem atirou: veículo, lado, seta e alvo; enquadramento; o que deixou de fora. */
  function linhaDeAtaque(quadro, ataque) {
    var contexto = quadro.contexto;
    var apoio = contexto.apoio;
    var veiculo = busca(apoio.veiculos, ataque.veiculo);
    var linha = cria('div', 'ataque');
    var cabeca = cria('p', 'ataque__cabeca', [
      nomeDoVeiculo(apoio, ataque.veiculo, true, 'ataque__veiculo'),
      siglaDoPartido(apoio, ataque.lado),
      alvoDoAtaque(contexto, ataque, true)
    ]);
    /* veículo que saiu do mapa não leva nenhuma das duas etiquetas */
    if (veiculo && veiculo.lado_confianca === 'baixa') { poe(cabeca, etiqueta(T.itens.ladoIncerto)); }
    if (veiculo && (veiculo.lado_confianca === 'alta' || veiculo.lado_confianca === 'media') && ehFogoAmigo(contexto, ataque)) {
      poe(cabeca, etiqueta(T.itens.fogoAmigo));
    }
    poe(linha, cabeca, cria('p', 'ataque__enquadramento', texto(ataque.enquadramento)));
    if (texto(ataque.omite)) {
      poe(linha, cria('p', 'ataque__omite', [T.itens.deixouDeFora, texto(ataque.omite), ' ',
        cria('span', 'ataque__leitura', ['Segundo a leitura do INFOCENARIUM em ', tempo(contexto.data), '.'])]));
    }
    poe(linha, cria('p', 'ataque__link', linkExterno(ataque.url, T.itens.lerNoVeiculo)));
    return linha;
  }

  /* O ato na régua: tema, "empurra para:" e o texto do polo. Sem cor e sem
     as palavras dos polos: o sentido só escolhe qual texto mostrar. */
  function linhaDeEixo(contexto, eixo) {
    if (!ehObjeto(eixo)) { return fraseVazia(T.itens.semEixo); }
    var tema = busca(contexto.apoio.temas, eixo.tema);
    var linha = cria('div', 'eixo');
    if (!tema) {
      /* tema que não está na régua: o id, sem o texto do polo */
      poe(linha, cria('p', 'eixo__cabeca', cria('span', 'id-cru', texto(eixo.tema))));
    } else {
      var polo = '';
      if (eixo.sentido === 'azul') { polo = texto(tema.azul); }
      if (eixo.sentido === 'vermelho') { polo = texto(tema.vermelho); }
      var vista = cria('span', 'eixo__cabeca', [
        cria('span', 'eixo__tema', texto(tema.nome)), etiqueta(texto(tema.sigla)),
        polo ? cria('span', 'texto-2', T.itens.empurra) : null, polo ? cria('span', 'eixo__polo', polo) : null
      ]);
      poe(linha, cria('p', '', [soLeitor(texto(tema.nome) + (polo ? ': empurra para ' + polo : '')), soVista(vista)]));
    }
    poe(linha, cria('p', 'eixo__porque', texto(eixo.porque)));
    return linha;
  }

  /* Quem ganha e quem perde: sinal e palavra, nunca cor. */
  function placarDoItem(contexto, item) {
    var linhas = lista(item.placar).filter(ehObjeto);
    if (!linhas.length) { return cria('p', '', texto(item.sem_placar) || T.itens.semPlacar); }
    return cria('div', '', linhas.map(function (linha) {
      var sinal = linha.efeito === 'ganha' ? '+ ' : (linha.efeito === 'perde' ? '− ' : '');
      return cria('div', 'placar-item', [
        cria('p', 'placar-item__cabeca', [
          siglaDoPartido(contexto.apoio, linha.partido),
          busca(contexto.apoio.partidos, linha.partido) ? cria('span', 'placar-item__nome', nomeDoPartido(contexto.apoio, linha.partido)) : null,
          cria('span', 'placar-item__efeito', sinal + rotulo('efeito', linha.efeito)),
          forca(contexto.apoio, linha.forca),
          texto(linha.evidencia) ? etiqueta(rotulo('evidencia', linha.evidencia)) : null
        ]),
        cria('p', 'placar-item__porque', texto(linha.porque))
      ]);
    }));
  }

  function vetoresDoItem(quadro, item) {
    var vetores = lista(item.vetores).filter(ehObjeto);
    if (!vetores.length) { return fraseVazia(T.itens.semVetores); }
    return cria('div', '', vetores.map(function (vetor) { return linhaDeVetor(quadro, vetor, item, false); }));
  }

  /* Vetor: player, partido de origem, seta, destino, força e tema.
     Anulado: fica à vista, riscado, com a etiqueta e o motivo sem risco. */
  function linhaDeVetor(quadro, vetor, item, comOrigem) {
    var contexto = quadro.contexto;
    var apoio = contexto.apoio;
    var idDoVetor = contexto.data + '_' + texto(item.id) + '_' + texto(vetor.player);
    var anulacao = apoio.temRegistro ? anulacaoDe(apoio, idDoVetor) : null;
    var player = busca(apoio.players, vetor.player);
    var linha = cria('div', 'vetor' + (anulacao ? ' vetor--anulado' : ''));
    var riscado = cria('span', 'vetor__riscado', [
      player && ehId(vetor.player) ? linkInterno(hashRegua('players', vetor.player), texto(player.nome) || vetor.player, 'vetor__player')
        : cria('span', 'id-cru vetor__player', texto(vetor.player)),
      player ? siglaDoPartido(apoio, player.partido) : null,
      seta('desloca-se para'), siglaDoPartido(apoio, vetor.para), forca(apoio, vetor.forca), etiquetaDeTema(apoio, vetor.tema)
    ]);
    var cabeca = cria('p', 'vetor__cabeca', [anulacao ? soLeitor('Anulado: ') : null, riscado]);
    if (anulacao) {
      poe(cabeca, etiqueta(T.itens.anulado));
    } else if (apoio.temRegistro) {
      var vezes = reincidencia(contexto, vetor, idDoVetor);
      if (vezes >= 2) { poe(cabeca, etiqueta(ordinal(vezes) + ' vez em 30 dias')); }
    }
    if (item.conflito_de_interesse === true) { poe(cabeca, etiqueta(T.itens.conflito)); }
    if (comOrigem) { poe(cabeca, linkParaItem(contexto, item.id)); }
    poe(linha, cabeca, cria('p', 'vetor__porque', texto(vetor.porque)),
      cria('p', 'vetor__link', linkExterno(vetor.url, T.itens.prova)));
    if (anulacao) { poe(linha, linhaDaAnulacao(anulacao)); }
    return linha;
  }

  /* "Anulado em DD/MM: motivo", com o link da correção. Nunca é riscada. */
  function linhaDaAnulacao(anulacao) {
    return cria('p', 'vetor__anulacao', ['Anulado em ', tempo(anulacao.data), ': ', texto(anulacao.porque), ' ',
      linkExterno(anulacao.url, T.itens.fonteCorrecao)]);
  }

  /* Para quem se prepara: no Brasil, domínios e as perguntas a vigiar. */
  function preparoDoItem(quadro, item) {
    var partes = [];
    var dominios = lista(item.dominios);
    var perguntas = lista(item.vigiar).filter(ehTexto);
    if (texto(item.no_brasil)) {
      partes.push(cria('p', '', [cria('span', 'dossie__rotulo', T.itens.noBrasil), texto(item.no_brasil)]));
    }
    if (dominios.length) {
      partes.push(cria('p', 'marcas', [cria('span', 'dossie__rotulo', T.itens.dominios),
        dominios.map(function (id) { return etiquetaDeDominio(quadro, id); })]));
    } else {
      partes.push(fraseVazia(T.itens.semDominios));
    }
    if (perguntas.length) {
      partes.push(cria('p', 'dossie__rotulo', T.itens.vigiar), cria('ul', 'lista', perguntas.map(function (pergunta, i) {
        /* a primeira é a que derruba a leitura do dossiê */
        return cria('li', 'com-dicas', [i === 0 ? etiquetaComDica(T.itens.perguntaChave, T.itens.dicaPerguntaChave) : null, i === 0 ? ' ' : null, pergunta]);
      })));
    }
    return cria('div', '', partes);
  }

  /* {veículo: lado gravado no ataque} do mesmo item: o primeiro ataque de
     cada veículo vale. Como no .md (fer-07), o lado gravado vale mais que o
     do mapa de hoje: depois de o dono mudar o mapa, o mesmo veículo não
     aparece com dois partidos no mesmo item. */
  function ladosDosAtaques(ataques) {
    var lados = {};
    lista(ataques).filter(ehObjeto).forEach(function (a) {
      if (ehTexto(a.veiculo) && ehTexto(a.lado) && !Object.prototype.hasOwnProperty.call(lados, a.veiculo)) {
        lados[a.veiculo] = a.lado;
      }
    });
    return lados;
  }

  /* Fonte: veículo e lado (ou nome e FORA DO MAPA), data, título como
     publicado. O lado é o gravado no ataque do mesmo veículo no item; sem
     ataque dele, o do mapa de hoje. */
  function linhaDeFonte(contexto, fonte, lados) {
    var apoio = contexto.apoio;
    var cabeca = cria('p', 'fonte__cabeca');
    var veiculo = null;
    if (fonte.veiculo === 'outro') {
      poe(cabeca, cria('span', 'fonte__veiculo', texto(fonte.nome)), etiqueta(T.itens.foraDoMapa));
    } else {
      veiculo = busca(apoio.veiculos, fonte.veiculo);
      poe(cabeca, nomeDoVeiculo(apoio, fonte.veiculo, true, 'fonte__veiculo'));
      var gravado = ehObjeto(lados) && ehTexto(fonte.veiculo) &&
        Object.prototype.hasOwnProperty.call(lados, fonte.veiculo) ? lados[fonte.veiculo] : null;
      if (gravado) {
        poe(cabeca, siglaDoPartido(apoio, gravado));
      } else if (veiculo) {
        poe(cabeca, siglaDoPartido(apoio, veiculo.lado));
      }
    }
    poe(cabeca, cria('span', 'fonte__data', tempo(fonte.publicado_em)));
    if (fonte.primaria === true) { poe(cabeca, etiqueta(T.itens.primaria)); }
    /* o título fica como foi publicado: o tradutor do navegador não mexe */
    var titulo = cria('span', '', texto(fonte.titulo));
    titulo.setAttribute('translate', 'no');
    var idioma = idiomaUnico(veiculo);
    if (idioma) { titulo.setAttribute('lang', idioma); }
    poe(cabeca, linkExterno(fonte.url, titulo, 'fonte__titulo'));
    return cria('div', 'fonte', cabeca);
  }

  /* O idioma do título de uma fonte, para o leitor de tela pronunciar certo
     (WCAG 3.1.2): só quando o veículo do mapa publica num idioma só. Com
     vários (o sputnik também publica em português), "multi" ou fonte fora do
     mapa, nada: um idioma errado seria pior que nenhum. */
  function idiomaUnico(veiculo) {
    var idiomas = veiculo ? lista(veiculo.idiomas).filter(ehTexto) : [];
    if (idiomas.length !== 1 || !FORMA_IDIOMA.test(idiomas[0])) { return ''; }
    return idiomas[0];
  }

  /* ----- 08 Radar ----- */

  function secaoRadar(quadro) {
    var contexto = quadro.contexto;
    var itens = lista(contexto.edicao.radar).filter(ehObjeto);
    var s = secao('radar', '08', T.titulos.radar, contexto, ' (' + itens.length + ')');
    poe(s.corpo, notaDeRascunho(contexto));
    if (!itens.length) {
      poe(s.corpo, fraseVazia(T.travessao));
      return s.raiz;
    }
    quadro.radar = { linhas: [], botoes: [], dominios: opcoesDeDominio(contexto), partidos: opcoesDePartido(contexto, itens) };
    poe(s.corpo, filtrosDoRadar(quadro, itens));
    itens.forEach(function (item) { poe(s.corpo, linhaDeRadar(quadro, item)); });
    quadro.radar.vazio = esconde(cria('div', 'filtros__vazio', [
      cria('p', '', T.radar.vazio),
      botao(T.radar.limpar, '', function () { poeFiltros(quadro, { cat: '', dom: '', partido: '' }, true); })
    ]), true);
    poe(s.corpo, quadro.radar.vazio);
    return s.raiz;
  }

  function opcoesDeDominio(contexto) {
    if (contexto.apoio.ordemDominios.length) { return contexto.apoio.ordemDominios.filter(ehId); }
    return dominiosDaEdicao(contexto).map(function (d) { return d.id; }).filter(ehId);
  }

  /* Partidos do filtro: os da régua; sem a régua, os que aparecem no radar. */
  function opcoesDePartido(contexto, itens) {
    if (contexto.apoio.ordemPartidos.length) { return contexto.apoio.ordemPartidos.filter(ehId); }
    var achados = [];
    function junta(id) { if (ehId(id) && achados.indexOf(id) === -1) { achados.push(id); } }
    itens.forEach(function (item) {
      lista(item.placar).forEach(function (linha) { if (ehObjeto(linha)) { junta(linha.partido); } });
      if (ehObjeto(item.ataque)) { junta(item.ataque.lado); }
      lista(item.vetores).forEach(function (vetor) { if (ehObjeto(vetor)) { junta(vetor.para); } });
    });
    return achados;
  }

  function seletor(nomeDoCampo, primeira, opcoes, aoMudar) {
    var campo = cria('select', 'campo');
    campo.setAttribute('aria-label', nomeDoCampo);
    var todas = cria('option', '', primeira);
    todas.setAttribute('value', '');
    poe(campo, todas);
    opcoes.forEach(function (opcao) {
      var el = cria('option', '', opcao.nome);
      el.setAttribute('value', opcao.valor);
      poe(campo, el);
    });
    campo.addEventListener('change', function () { aoMudar(texto(campo.value)); });
    return campo;
  }

  /* Uma fileira acima da lista: botões juntos para a categoria, com
     contagem; listas nativas para domínio e partido. */
  function filtrosDoRadar(quadro, itens) {
    var contexto = quadro.contexto;
    var radar = quadro.radar;
    var grupo = cria('div', 'filtros__grupo');
    function conta(categoria) {
      return itens.filter(function (item) { return !categoria || item.categoria === categoria; }).length;
    }
    [['', T.radar.todas], ['geopolitica', rotulo('categoria', 'geopolitica')], ['ia', rotulo('categoria', 'ia')]].forEach(function (par) {
      var b = botao(par[1] + ' (' + conta(par[0]) + ')', '', function () { mudaFiltro(quadro, 'cat', par[0]); });
      radar.botoes.push({ valor: par[0], el: b });
      poe(grupo, b);
    });
    radar.seletorDominio = seletor(T.radar.porDominio, T.radar.todosDominios, radar.dominios.map(function (id) {
      return { valor: id, nome: nomeDoDominio(contexto.apoio, id) };
    }), function (valor) { mudaFiltro(quadro, 'dom', valor); });
    radar.seletorPartido = seletor(T.radar.porPartido, T.radar.todosPartidos, radar.partidos.map(function (id) {
      return { valor: id, nome: nomeDoPartido(contexto.apoio, id) };
    }), function (valor) { mudaFiltro(quadro, 'partido', valor); });
    radar.contagem = cria('p', 'filtros__contagem');
    return cria('div', 'filtros', [grupo, radar.seletorDominio, radar.seletorPartido, radar.contagem]);
  }

  function mudaFiltro(quadro, nome, valor) {
    var novos = { cat: quadro.filtros.cat, dom: quadro.filtros.dom, partido: quadro.filtros.partido };
    novos[nome] = valor;
    poeFiltros(quadro, filtrosDaConsulta(quadro, novos), true);
  }

  /* Só passa valor que está na lista do filtro. O resto é ignorado. */
  function filtrosDaConsulta(quadro, consulta) {
    var filtros = { cat: '', dom: '', partido: '' };
    var radar = quadro.radar;
    if (!radar || !consulta) { return filtros; }
    if (consulta.cat === 'geopolitica' || consulta.cat === 'ia') { filtros.cat = consulta.cat; }
    if (radar.dominios.indexOf(consulta.dom) !== -1) { filtros.dom = consulta.dom; }
    if (radar.partidos.indexOf(consulta.partido) !== -1) { filtros.partido = consulta.partido; }
    return filtros;
  }

  /* O partido casa com o placar, o lado do ataque, o alvo (partido ou player
     dele) e os vetores (o partido do player ou o destino). */
  function itemCasaComPartido(contexto, item, partido) {
    var apoio = contexto.apoio;
    function doPartido(idDoPlayer) {
      var player = playerDe(contexto, idDoPlayer);
      return !!player && player.partido === partido;
    }
    if (lista(item.placar).some(function (linha) { return ehObjeto(linha) && linha.partido === partido; })) { return true; }
    var ataques = lista(item.ataques).concat(ehObjeto(item.ataque) ? [item.ataque] : []).filter(ehObjeto);
    if (ataques.some(function (ataque) {
      if (ataque.lado === partido) { return true; }
      /* alvo "outro" e alvo "nenhum" não casam com partido nenhum */
      if (ataque.alvo === 'outro' || ataque.alvo === 'nenhum') { return false; }
      return ataque.alvo === partido || (!busca(apoio.partidos, ataque.alvo) && doPartido(ataque.alvo));
    })) { return true; }
    return lista(item.vetores).some(function (vetor) {
      return ehObjeto(vetor) && (vetor.para === partido || doPartido(vetor.player));
    });
  }

  /* Os filtros se somam: o item tem de passar em todos. */
  function itemPassa(contexto, item, filtros) {
    if (filtros.cat && item.categoria !== filtros.cat) { return false; }
    if (filtros.dom && lista(item.dominios).indexOf(filtros.dom) === -1) { return false; }
    if (filtros.partido && !itemCasaComPartido(contexto, item, filtros.partido)) { return false; }
    return true;
  }

  /* Recorta o radar. O recorte é imediato e nunca muda cor nem ordem.
     porLeitor: grava os filtros no endereço e anuncia a contagem. */
  function poeFiltros(quadro, filtros, porLeitor) {
    quadro.filtros = filtros;
    var radar = quadro.radar;
    if (!radar) { return; }
    var visiveis = 0;
    radar.linhas.forEach(function (linha) {
      var passa = itemPassa(quadro.contexto, linha.item, filtros);
      esconde(linha.raiz, !passa);
      if (passa) { visiveis += 1; }
    });
    radar.botoes.forEach(function (b) { b.el.setAttribute('aria-pressed', b.valor === filtros.cat ? 'true' : 'false'); });
    radar.seletorDominio.value = filtros.dom;
    radar.seletorPartido.value = filtros.partido;
    var contagem = visiveis + ' de ' + radar.linhas.length + ' itens';
    var filtrando = !!(filtros.cat || filtros.dom || filtros.partido);
    troca(radar.contagem, filtrando ? contagem : '');
    esconde(radar.vazio, visiveis > 0);
    if (porLeitor) {
      var hash = enderecoDoQuadro(quadro, estado.rota ? estado.rota.item : null);
      gravaEndereco(hash);
      estado.rota = interpretaRota(hash);
      anuncia(visiveis ? contagem : T.radar.vazio);
    }
  }

  function linhaDeRadar(quadro, item) {
    var contexto = quadro.contexto;
    var id = item.id;
    var nome = texto(item.titulo);
    var raiz = cria('article', 'radar__item');
    if (ehId(id)) { raiz.setAttribute('id', 'item-' + id); }
    var titulo = cria('h3', 'radar__titulo', nome);
    titulo.setAttribute('tabindex', '-1');
    var ataque = ehObjeto(item.ataque) ? item.ataque : null;
    var apoioDaLinha = cria('p', 'radar__apoio', [
      ataque ? resumoDosAtaques(contexto, [ataque]) : null, ataque ? separador() : null,
      resumoDoPlacar(contexto, item.placar)
    ]);
    var nomeDoBotao = soLeitor('Abrir: ' + nome);
    var abre = botao([icone('i-dobra', 'icone--dobra'), nomeDoBotao], 'botao--dobra');
    var cabeca = cria('div', 'radar__cabeca', [
      cria('div', '', [
        marcasDoItem(quadro, item, { categoria: true }), titulo, apoioDaLinha,
        marcasDoItem(quadro, item, { dominios: true, confianca: true, conflito: true })
      ]),
      abre
    ]);
    var corpo = cria('div', 'radar__corpo', partesDoRadar(quadro, item));
    poe(raiz, cabeca, corpo);
    var dobra = ligaDobra(abre, corpo, function (aberta) {
      if (ehId(id)) { gravaItemNoEndereco(quadro, id, aberta); }
    });
    dobra.aoPor = function (aberta) { troca(nomeDoBotao, (aberta ? 'Fechar: ' : 'Abrir: ') + nome); };
    cabecaAbre(cabeca, dobra);
    quadro.radar.linhas.push({ item: item, raiz: raiz });
    if (ehId(id) && !(id in quadro.refs.radar)) {
      quadro.refs.radar[id] = { raiz: raiz, dobra: dobra, foco: titulo };
    }
    return raiz;
  }

  /* Item do radar aberto: as mesmas linhas do dossiê, com um ataque só. */
  function partesDoRadar(quadro, item) {
    var contexto = quadro.contexto;
    var fontes = lista(item.fontes).filter(ehObjeto);
    var partes = [];
    if (item.conflito_de_interesse === true) { partes.push(avisoDeConflito(contexto, item)); }
    partes.push(tituloDeParte(T.itens.aconteceu), cria('p', '', texto(item.fato)));
    partes.push(tituloDeParte(T.itens.quemAtirou + ' (' + (ehObjeto(item.ataque) ? 1 : 0) + ')'),
      ehObjeto(item.ataque) ? linhaDeAtaque(quadro, item.ataque) : fraseVazia(T.travessao));
    partes.push(tituloDeParte(T.itens.atoNaRegua), linhaDeEixo(contexto, item.eixo));
    partes.push(tituloDeParte(T.itens.quemGanha), placarDoItem(contexto, item));
    partes.push(tituloDeParte(T.itens.movimentos), vetoresDoItem(quadro, item));
    partes.push(tituloDeParte(T.itens.fontes + ' (' + fontes.length + ')'),
      cria('div', '', fontes.map(function (f) { return linhaDeFonte(contexto, f, ladosDosAtaques([item.ataque])); })));
    if (item.continuacao_de !== undefined) { partes.push(cria('p', 'marcas', continuacao(contexto, item.continuacao_de))); }
    return partes;
  }

  /* ======================================================================
     15. Edição: seções 05, 06, 07 e 09
     ====================================================================== */

  /* ----- 05 Placar do dia ----- */

  /* Soma de saldos do histórico, por partido. Não leva narrativa. */
  function saldoAcumulado(historico, partido) {
    var soma = 0;
    historico.forEach(function (entrada) {
      if (ehObjeto(entrada.saldos) && tem(entrada.saldos, partido) && ehNumero(entrada.saldos[partido])) {
        soma += entrada.saldos[partido];
      }
    });
    return soma;
  }

  /* As linhas do placar: as do dia, mais os partidos da régua que ficaram de
     fora (saldo 0, sem frase). Maior saldo primeiro; empate segue a régua. */
  function linhasDoPlacar(contexto) {
    var ordem = contexto.apoio.ordemPartidos;
    var linhas = lista(contexto.edicao.placar_do_dia).filter(ehObjeto).map(function (linha) {
      return {
        partido: linha.partido,
        saldo: ehNumero(linha.saldo) ? linha.saldo : 0,
        narrativa: ehNumero(linha.narrativa) ? linha.narrativa : 0,
        frase: texto(linha.frase),
        ausente: false
      };
    });
    if (!linhas.length) { return linhas; }
    ordem.forEach(function (id) {
      if (!linhas.some(function (linha) { return linha.partido === id; })) {
        linhas.push({ partido: id, saldo: 0, narrativa: 0, frase: '', ausente: true });
      }
    });
    function posicao(linha) {
      var i = ordem.indexOf(linha.partido);
      return i === -1 ? ordem.length : i;
    }
    return linhas.map(function (linha, i) { return { linha: linha, i: i }; })
      .sort(function (a, b) { return b.linha.saldo - a.linha.saldo || posicao(a.linha) - posicao(b.linha) || a.i - b.i; })
      .map(function (par) { return par.linha; });
  }

  function secaoPlacar(quadro) {
    var contexto = quadro.contexto;
    var s = secao('placar', '05', T.titulos.placar, contexto);
    var linhas = linhasDoPlacar(contexto);
    if (!linhas.length) {
      poe(s.corpo, fraseVazia(T.placar.vazio));
      return s.raiz;
    }
    poe(s.corpo, cria('p', 'secao__intro', T.placar.intro));
    /* escala comum às linhas: 72 px valem o maior saldo absoluto, com piso de 3 */
    var maior = PISO_ESCALA_PLACAR;
    linhas.forEach(function (linha) { maior = Math.max(maior, Math.abs(linha.saldo)); });
    poe(s.corpo, cria('ul', 'placar', linhas.map(function (linha) { return linhaDoPlacar(contexto, linha, maior); })));
    return s.raiz;
  }

  /* Ganha e perde na mesma tinta: a diferença é o lado da barra, o sinal e
     a palavra. A narrativa nunca vira barra. */
  function linhaDoPlacar(contexto, linha, escala) {
    var apoio = contexto.apoio;
    var area = cria('span', 'placar__area', [cria('span', 'placar__eixo'),
      barraDoEixo(Math.abs(linha.saldo), escala, linha.saldo > 0 ? 'placar__barra--ganha' : 'placar__barra--perde')]);
    var fala = nomeDoPartido(apoio, linha.partido) + ': saldo ' + sinalFalado(linha.saldo);
    if (linha.narrativa !== 0) { fala += '; na narrativa, ' + sinalFalado(linha.narrativa); }
    var item = cria('li', 'placar__linha', cria('div', 'placar__topo', [
      cria('span', '', [siglaDoPartido(apoio, linha.partido), soLeitor(' ' + fala)]),
      soVista(area),
      soVista(cria('span', 'placar__saldo', comSinal(linha.saldo)))
    ]));
    var nota = cria('p', 'placar__nota');
    if (linha.narrativa !== 0) { poe(nota, soVista(cria('span', '', T.itens.narrativa + ' ' + comSinal(linha.narrativa)))); }
    /* edição de exemplo não tem acumulado */
    if (!contexto.exemplo) {
      if (linha.narrativa !== 0) { poe(nota, separador()); }
      poe(nota, cria('span', '', T.placar.trintaDias + comSinal(saldoAcumulado(contexto.historico, linha.partido))));
    }
    if (nota.firstChild) { poe(item, nota); }
    if (linha.ausente) {
      poe(item, cria('p', 'placar__frase texto-3', T.placar.semMovimento));
    } else if (linha.frase) {
      poe(item, cria('p', 'placar__frase', linha.frase));
    }
    return item;
  }

  /* ----- 06 O que vigiar ----- */

  function secaoVigiar(quadro) {
    var contexto = quadro.contexto;
    var s = secao('vigiar', '06', T.titulos.vigiar, contexto);
    poe(s.corpo, subtitulo(T.vigiar.sinais), cria('p', 'secao__intro', T.vigiar.intro));
    var sinais = [];
    dominiosDaEdicao(contexto).forEach(function (dominio) {
      if (!texto(dominio.vigiar)) { return; }
      var nome = nomeDoDominio(contexto.apoio, dominio.id) + ':';
      var origem = busca(quadro.refs.dominios, dominio.id) ? linkInterno(hashEdicao(contexto.data, dominio.id), nome, 'sinal__origem')
        : cria('span', 'sinal__origem', nome);
      sinais.push(cria('li', 'sinal', [origem, ' ', dominio.vigiar]));
    });
    lista(contexto.edicao.principais).filter(ehObjeto).forEach(function (item) {
      lista(item.vigiar).filter(ehTexto).forEach(function (pergunta) {
        var nome = 'Principal ' + numeroDoItem(item.id) + ':';
        var origem = ehId(item.id) ? linkInterno(hashEdicao(contexto.data, item.id), nome, 'sinal__origem') : cria('span', 'sinal__origem', nome);
        sinais.push(cria('li', 'sinal', [origem, ' ', pergunta]));
      });
    });
    poe(s.corpo, sinais.length ? cria('ul', 'sinais', sinais) : fraseVazia(T.travessao));

    var respostas = lista(contexto.edicao.respostas).filter(ehObjeto);
    poe(s.corpo, subtitulo(T.vigiar.respostas + ' (' + respostas.length + ')'), cria('p', 'secao__intro', T.vigiar.introRespostas));
    if (!respostas.length) {
      poe(s.corpo, fraseVazia(T.vigiar.vazio));
    } else {
      poe(s.corpo, cria('div', 'respostas', respostas.map(function (r) { return linhaDeResposta(contexto, r); })));
    }
    return s.raiz;
  }

  /* SIM, NÃO e SEM DADO têm o mesmo desenho: quem diz se o INFOCENARIUM acertou é o texto. */
  function linhaDeResposta(contexto, resposta) {
    var linha = cria('div', 'resposta');
    poe(linha, cria('p', 'resposta__cabeca', [
      etiqueta(rotulo('resposta', resposta.resposta)), cria('span', 'resposta__pergunta', texto(resposta.pergunta))
    ]));
    poe(linha, cria('p', 'resposta__texto', texto(resposta.texto)));
    var pe = cria('p', 'resposta__pe');
    if (resposta.url !== undefined) { poe(pe, linkExterno(resposta.url, T.vigiar.fonte)); }
    var item = resposta.item;
    var quem = ['perguntado em ', tempo(resposta.edicao),
      ehTexto(item) && FORMA_ITEM_PRINCIPAL.test(item) ? ', principal ' + numeroDoItem(item) : [', ', cria('span', 'id-cru', texto(item))]];
    var noIndice = ehData(resposta.edicao) && entradaDaData(contexto.entradas, resposta.edicao) && ehId(item);
    poe(pe, noIndice ? linkInterno(hashEdicao(resposta.edicao, item), quem) : cria('span', '', quem));
    poe(linha, pe);
    return linha;
  }

  /* ----- 07 Movimentos ----- */

  function secaoMovimentos(quadro) {
    var contexto = quadro.contexto;
    var s = secao('movimentos', '07', T.titulos.movimentos, contexto);
    poe(s.corpo, cria('p', 'secao__intro', T.movimentos.intro));
    var linhas = [];
    lista(contexto.edicao.principais).concat(lista(contexto.edicao.radar)).filter(ehObjeto).forEach(function (item) {
      lista(item.vetores).filter(ehObjeto).forEach(function (vetor) {
        linhas.push(linhaDeVetor(quadro, vetor, item, true));
      });
    });
    var novos = lista(contexto.edicao.novos_players).filter(ehObjeto);
    if (!linhas.length && !novos.length) { poe(s.corpo, fraseVazia(T.movimentos.vazio)); }
    if (linhas.length) { poe(s.corpo, cria('div', 'vetores', linhas)); }
    novos.forEach(function (player) { poe(s.corpo, fichaDePlayerNovo(contexto, player)); });
    return s.raiz;
  }

  var LETRAS_DNA = { B: 'polo azul', Y: 'misto', R: 'polo vermelho', W: 'sem posição conhecida', K: 'saiu do cargo' };

  /* O que quer dizer uma letra do DNA: o texto da régua, ou o rótulo fixo. */
  function significadoDaLetra(apoio, letra) {
    var valores = apoio.regua.valores;
    if (tem(valores, letra) && ehObjeto(valores[letra]) && texto(valores[letra].significado)) { return valores[letra].significado; }
    return tem(LETRAS_DNA, letra) ? LETRAS_DNA[letra] : letra;
  }

  /* Uma célula do DNA. Duas letras: virada, antes à esquerda e agora à direita. */
  function celulaDeDna(apoio, nomeDoTema, valor, emDuvida) {
    var letras = texto(valor).slice(0, 2).split('');
    var fala = nomeDoTema + ': ';
    if (letras.length === 2) {
      fala += 'virada de ' + significadoDaLetra(apoio, letras[0]) + ' para ' + significadoDaLetra(apoio, letras[1]);
    } else {
      fala += letras.length ? significadoDaLetra(apoio, letras[0]) : T.travessao;
    }
    if (emDuvida) { fala += ', ' + T.movimentos.emDuvida; }
    var celula = cria('span', 'dna__celula', soLeitor(fala));
    letras.forEach(function (letra, i) {
      var metade = metadeDeDna(letra);
      if (emDuvida && i === letras.length - 1) { poe(metade, cria('span', 'dna__duvida', '?')); }
      poe(celula, metade);
    });
    return celula;
  }

  /* A letra de uma posição. A classe da cor só sai para as 5 letras da régua. */
  function metadeDeDna(letra) {
    return soVista(cria('span', 'dna__metade' + (tem(LETRAS_DNA, letra) ? ' dna__metade--' + letra.toLowerCase() : ''), letra));
  }

  /* Tira de 7 células, com as siglas dos temas em cima. No Painel a única
     cor de dado é a do alerta: lá o DNA vai só na tinta. Na Régua (comCor),
     a cor de dado é a da posição. */
  function tiraDeDna(apoio, dna, duvidas, comCor) {
    var posicoes = ehObjeto(dna) ? dna : {};
    var temas = apoio.ordemTemas.length ? apoio.ordemTemas : Object.keys(posicoes);
    var tira = cria('div', 'dna' + (comCor ? '' : ' dna--tinta'));
    temas.forEach(function (id) {
      var tema = busca(apoio.temas, id);
      poe(tira, soVista(cria('span', 'dna__sigla', tema ? texto(tema.sigla) : texto(id))));
    });
    temas.forEach(function (id) {
      var tema = busca(apoio.temas, id);
      poe(tira, celulaDeDna(apoio, tema ? texto(tema.nome) : texto(id), tem(posicoes, id) ? posicoes[id] : '', lista(duvidas).indexOf(id) !== -1));
    });
    return tira;
  }

  function fichaDePlayerNovo(contexto, player) {
    var apoio = contexto.apoio;
    var id = player.id;
    var ficha = cria('article', 'novo-player');
    poe(ficha, cria('p', 'marcas', [etiqueta(T.movimentos.novoPlayer), cria('span', 'novo-player__id', texto(id))]));
    poe(ficha, cria('h3', 'novo-player__nome', texto(player.nome) || texto(id)));
    var tipo = busca(apoio.tipos, player.tipo);
    var time = busca(apoio.times, player.time);
    poe(ficha, cria('p', 'marcas', [
      cria('span', tipo ? '' : 'id-cru', tipo ? texto(tipo.nome) : texto(player.tipo)),
      siglaDoPartido(apoio, player.partido),
      cria('span', time ? '' : 'id-cru', time ? texto(time.nome) : texto(player.time)),
      player.time_discutivel === true ? etiqueta(T.movimentos.timeDiscutivel) : null
    ]));
    poe(ficha, tiraDeDna(apoio, player.dna, player.duvidas));

    poe(ficha, fontesDasPosicoes(apoio, player));
    if (texto(player.nota)) { poe(ficha, cria('p', '', texto(player.nota))); }
    poe(ficha, cria('p', '', [cria('span', 'dossie__rotulo', T.movimentos.porQueEntrou), texto(player.justificativa), ' ',
      player.url !== undefined ? linkExterno(player.url, T.vigiar.fonte) : null]));
    /* a ficha só existe na Régua depois que o player entra em players.json */
    if (ehId(id) && busca(apoio.players, id)) { poe(ficha, cria('p', '', linkInterno(hashRegua('players', id), T.movimentos.verFicha))); }
    return ficha;
  }

  /* "Fontes das posições:", com um link por tema que tem fonte. O texto do
     link é o nome do tema: "fonte" repetido não diria qual é qual. */
  function fontesDasPosicoes(apoio, player) {
    var fontes = ehObjeto(player.dna_fontes) ? player.dna_fontes : {};
    var links = (apoio.ordemTemas.length ? apoio.ordemTemas : Object.keys(fontes)).filter(function (tema) { return tem(fontes, tema); })
      .map(function (tema) {
        var daRegua = busca(apoio.temas, tema);
        return linkExterno(fontes[tema], daRegua ? texto(daRegua.nome) : texto(tema));
      });
    if (!links.length) { return null; }
    return cria('p', 'novo-player__fontes', [cria('span', 'dossie__rotulo', T.movimentos.fontesPosicoes), links]);
  }

  /* ----- 09 Bastidores ----- */

  function secaoBastidores(quadro) {
    var contexto = quadro.contexto;
    var b = ehObjeto(contexto.edicao.bastidores) ? contexto.edicao.bastidores : {};
    var s = secao('bastidores', '09', T.titulos.bastidores, contexto);
    /* Na edição falha, o modo e os números são enchimento que ninguém mediu
       (a falha não lê a coleta): mostrá-los seria dar por fato "coleta normal"
       e "0 feeds que falharam". Ficam só os limites. */
    var medidos = !contexto.falha;
    if (medidos && texto(b.modo)) { poe(s.corpo, cria('p', 'bastidores__modo', rotulo('modo', b.modo))); }
    var numeros = !medidos ? [] : [
      ['veiculos_consultados', T.bastidores.veiculos], ['feeds_ok', T.bastidores.feedsOk],
      ['feeds_falhos', T.bastidores.feedsFalhos], ['paginas_lidas', T.bastidores.paginas],
      ['buscas', T.bastidores.buscas], ['minutos', T.bastidores.minutos],
      ['injecoes_ignoradas', T.bastidores.injecoes]
    ].filter(function (par) { return ehNumero(b[par[0]]); });
    if (numeros.length) {
      /* rótulo e número em pares: "páginas lidas 11" não tropeça no singular */
      poe(s.corpo, cria('dl', 'bastidores__numeros', numeros.map(function (par) {
        return cria('div', 'bastidores__numero', [cria('dt', '', par[1]), cria('dd', '', inteiro(b[par[0]]))]);
      })));
    }
    poe(s.corpo, subtitulo(T.bastidores.limites), cria('p', 'bastidores__limites', texto(b.limites) || T.travessao));

    var candidatos = lista(b.candidatos).filter(ehObjeto);
    poe(s.corpo, subtitulo(T.bastidores.candidatos));
    if (candidatos.length) {
      poe(s.corpo, cria('ul', 'bastidores__lista', candidatos.map(function (c) {
        return cria('li', '', [cria('strong', '', texto(c.nome)), ' ', cria('span', 'id-cru', texto(c.id)), ': ', texto(c.motivo)]);
      })));
    } else {
      poe(s.corpo, fraseVazia(T.bastidores.nenhum));
    }
    /* nomes de site, não endereços conferidos: sempre texto simples, nunca link */
    var sugeridos = lista(b.veiculos_sugeridos).filter(ehTexto);
    poe(s.corpo, subtitulo(T.bastidores.sugeridos));
    if (sugeridos.length) {
      poe(s.corpo, cria('ul', 'bastidores__lista', sugeridos.map(function (nome) { return cria('li', '', nome); })));
    } else {
      poe(s.corpo, fraseVazia(T.bastidores.nenhum));
    }
    return s.raiz;
  }

  /* ======================================================================
     16. Arquivo, Régua e Método: o que as três vistas dividem
     ====================================================================== */

  /* Sai da vista de edição: para os relógios e solta o quadro. */
  function encerraEdicaoEmTela() {
    estado.pedido += 1;
    paraRelogioIdade();
    paraRelogioDemora();
    tiraAvisoGeral('demora');
    estado.quadro = null;
    estado.dobras = [];
    estado.dicaSobPonteiro = null;
    var rodape = porId('rodape-edicao');
    if (rodape) { limpa(rodape); }
  }

  /* Vista com título visível (22 px) e um corpo. Devolve o corpo. */
  function abreVistaSimples(vista, primeira) {
    encerraEdicaoEmTela();
    /* "Tentar de novo" refaz a carga desta vista, e não a da última edição */
    estado.enderecoDaCarga = janela.location.hash;
    var h1 = cria('h1', 'vista__titulo', T.vistas[vista]);
    atributos(h1, { id: 'titulo-vista', tabindex: '-1' });
    var corpo = cria('div', 'vista__corpo');
    trocaVista('vista--' + vista, [h1, corpo]);
    marcaNavegacao(vista);
    mudaTituloDaAba(T.marca + T.separador + T.vistas[vista]);
    if (!primeira) { focaTituloDaVista(); }
    return corpo;
  }

  /* Enquanto os arquivos da vista não chegam: aria-busy e um travessão no
     lugar do conteúdo. Depois de 8 segundos, "Está demorando". */
  function esperaDados(corpo) {
    vistaAtual().setAttribute('aria-busy', 'true');
    poe(corpo, fraseVazia(T.travessao));
    paraRelogioDemora();
    estado.relogioDemora = janela.setTimeout(function () {
      estado.relogioDemora = null;
      mostraAvisoGeral('demora', aviso({ texto: T.demora, acoes: [botao(T.tentar, '', tentaDeNovo)] }));
      anuncia(T.demora);
    }, ESPERA_DEMORA_MS);
  }

  function dadosChegaram(corpo) {
    paraRelogioDemora();
    tiraAvisoGeral('demora');
    vistaAtual().removeAttribute('aria-busy');
    limpa(corpo);
  }

  /* Lê os arquivos de uma vista. O que não vem chega como null: a vista
     decide o que mostrar no lugar. O índice também passa por leIndice, para
     o aviso de edição nova saber o que já foi lido. */
  function leParaVista(caminhos) {
    return Promise.all(caminhos.map(function (caminho) {
      if (caminho !== ARQ_INDICE) { return leApoio(caminho); }
      return leIndice(false).then(function (indice) { return indice; }, function () { return null; });
    }));
  }

  /* Monta a vista com rede de segurança: dado que o site não soube montar
     vira aviso, e não uma tela vazia. */
  function montaComRede(pedido, corpo, arquivo, monta) {
    if (pedido !== estado.pedido) { return; }
    dadosChegaram(corpo);
    try {
      monta();
    } catch (erro) {
      falhaDeCarga(arquivo, true);
    }
  }

  /* Dos arquivos lidos, os que não vieram e os de formato novo. */
  function faltasEFormatos(caminhos, lidos) {
    return {
      faltas: caminhos.filter(function (caminho, i) { return !lidos[i]; }),
      novos: caminhos.filter(function (caminho, i) { return formatoNovo(lidos[i]); })
    };
  }

  /* A edição mais nova que não é de exemplo: é nela que o histórico das
     vistas Arquivo e Régua termina. Só com edições de exemplo, não há histórico. */
  function ultimaReal(entradas) {
    for (var i = 0; i < entradas.length; i += 1) {
      if (!ehExemplo(entradas[i])) { return entradas[i]; }
    }
    return null;
  }

  function avisoSemEdicaoNaData(data) {
    return aviso({ rotulo: T.avisos.semEdicaoNaData + dataLonga(data), texto: T.avisos.mostrandoArquivo });
  }

  /* A rota pede uma ficha que não existe: a aba abre, com este aviso. */
  function avisaFichaNaoEncontrada(id) {
    mostraAvisoGeral('destino', aviso({
      rotulo: T.avisos.fichaNaoEncontrada,
      texto: ['Não há nada na Régua com o identificador ', cria('span', 'mono', texto(id)), '.']
    }));
    anuncia(textoDosAvisosDeRota());
  }

  /* Botão que é o próprio título de uma dobra ("COMO LER", um mês antigo do
     Arquivo). Não leva a classe botao: no papel os botões somem, e este
     título tem de ficar. */
  function tituloDeDobra(conteudo) {
    var b = cria('button', 'titulo-dobra', [icone('i-dobra', 'icone--dobra'), cria('span', '', conteudo)]);
    b.setAttribute('type', 'button');
    return b;
  }

  /* Cartão de figura: título h3, o desenho e, atrás de "Ver tabela", a
     tabela gêmea. Sem tabela, não há botão. */
  function figura(chave, titulo, intro, corpoDaFigura, tabelaGemea) {
    var raiz = cria('article', 'figura figura--' + chave);
    var topo = cria('div', 'figura__topo', cria('h3', 'figura__titulo', titulo));
    poe(raiz, topo, intro ? cria('p', 'secao__intro', intro) : null, corpoDaFigura);
    if (tabelaGemea) {
      var textoDoBotao = cria('span', '', T.verTabela);
      var abre = botao([textoDoBotao, soLeitor(': ' + titulo)], 'botao--texto');
      var caixa = cria('div', 'figura__tabela', tabelaGemea);
      poe(topo, abre);
      poe(raiz, caixa);
      var dobra = ligaDobra(abre, caixa);
      dobra.aoPor = function (aberta) { troca(textoDoBotao, aberta ? T.esconderTabela : T.verTabela); };
    }
    return raiz;
  }

  /* Sigla de partido sem link: dentro de uma figura (que o leitor de tela lê
     como uma imagem só) e na ficha do próprio partido. */
  function siglaSemLink(apoio, id) {
    var partido = busca(apoio.partidos, id);
    if (!partido) { return cria('span', 'id-cru', texto(id)); }
    var abbr = cria('abbr', '', texto(partido.sigla) || texto(id));
    abbr.setAttribute('title', texto(partido.nome));
    return cria('span', 'etiqueta etiqueta--partido', abbr);
  }

  /* Campo de busca com o rótulo à vista. Recorta a cada tecla. */
  function campoDeBusca(rotuloDoCampo, aoMudar) {
    var id = novoId('busca');
    var campo = cria('input', 'campo campo--busca');
    atributos(campo, { type: 'search', id: id, maxlength: BUSCA_MAXIMA });
    campo.addEventListener('input', function () { aoMudar(texto(campo.value)); });
    var rotuloDoElemento = cria('label', 'filtros__rotulo', rotuloDoCampo);
    rotuloDoElemento.setAttribute('for', id);
    return { raiz: cria('span', 'filtros__busca', [rotuloDoElemento, campo]), campo: campo };
  }

  /* ======================================================================
     17. Arquivo (#/arquivo)
     ====================================================================== */

  /* #/arquivo e #/arquivo?nivel=3. avisoDeDestino: quando a rota pedia uma
     edição que não existe. */
  function abreArquivo(rota, primeira, avisoDeDestino) {
    var corpo = abreVistaSimples('arquivo', primeira);
    var pedido = estado.pedido;
    if (avisoDeDestino) {
      mostraAvisoGeral('destino', avisoDeDestino);
      anuncia(textoDosAvisosDeRota());
    }
    esperaDados(corpo);
    var caminhos = [ARQ_INDICE, ARQ_REGUA, ARQ_CATALOGO];
    return leParaVista(caminhos).then(function (lidos) {
      montaComRede(pedido, corpo, ARQ_INDICE, function () {
        if (!lidos[0]) {
          /* sem o índice não há arquivo: erro de rede, com "Tentar de novo" */
          poe(corpo, fraseVazia(T.travessao));
          falhaDeCarga(ARQ_INDICE, true);
          return;
        }
        montaArquivo(corpo, rota, lidos, faltasEFormatos(caminhos, lidos));
      });
    });
  }

  function montaArquivo(corpo, rota, lidos, situacao) {
    var entradas = entradasDoIndice(lidos[0]);
    var ultima = ultimaReal(entradas);
    var contexto = {
      apoio: montaApoio(lidos[1], null, null, null, lidos[2]),
      indice: lidos[0],
      entradas: entradas,
      ultima: ultima,
      /* edição de exemplo não entra no histórico */
      historico: ultima ? historicoAte(entradas, ultima.data) : []
    };
    var edicoes = secaoEdicoes(contexto, rota);
    poe(corpo, cria('div', 'avisos', avisosDeArquivos(situacao.faltas, situacao.novos)),
      secaoHistorico(contexto), edicoes.raiz);
    edicoes.poeNivel(nivelDaConsulta(rota.consulta), false);
    if (!entradas.length) {
      mostraAvisoGeral('vazio', aviso({ rotulo: T.avisos.vazio[0], texto: T.avisos.vazio[1] }));
      anuncia(textoDosAvisosDeRota() + T.avisos.vazio[0] + '. ' + T.avisos.vazio[1]);
    }
  }

  /* ----- 01 Histórico: cinco figuras, cada uma com a tabela gêmea ----- */

  function secaoHistorico(contexto) {
    var s = secao('historico', '01', T.arquivo.historico, null);
    poe(s.corpo, cria('p', 'secao__intro', [cria('span', 'rotulo', T.arquivo.ultimos), T.separador + T.arquivo.semExemplo]));
    poe(s.corpo, cria('div', 'figuras', [
      figuraDoAlerta(contexto), figuraDosDominios(contexto), figuraDosPartidos(contexto),
      figuraDosAtos(contexto), figuraDosIndicadores(contexto)
    ]));
    return s.raiz;
  }

  /* Alerta geral: a mesma fita do Painel. Aqui não há edição em tela: nenhuma
     coluna vem clareada. Com menos de 2 edições, a fita não aparece. */
  function figuraDoAlerta(contexto) {
    var historico = contexto.historico;
    /* com uma edição só, a frase diz por que não há desenho; sem nenhuma, o travessão */
    var corpoDaFigura = fraseVazia(historico.length ? T.arquivo.desenhoDepois : T.travessao);
    if (historico.length >= 2) {
      var desenhoDaFita = fita({
        apoio: contexto.apoio,
        historico: historico,
        fim: contexto.ultima.data,
        emTela: null,
        nome: nomeDaFita('Alerta', historico, nivelGeral, 'na edição mais recente', contexto.ultima.nivel)
      });
      estado.fechaDicaDaVista = desenhoDaFita.fechaDica;
      corpoDaFigura = desenhoDaFita.raiz;
    }
    return figura('alerta', T.arquivo.alerta, null, corpoDaFigura,
      historico.length ? tabelaDoAlerta(contexto.apoio, historico, T.arquivo.alerta) : null);
  }

  /* Os domínios do histórico: os da régua; sem ela, os que o índice traz. */
  function dominiosDoHistorico(contexto) {
    if (contexto.apoio.ordemDominios.length) { return contexto.apoio.ordemDominios; }
    var achados = [];
    contexto.historico.forEach(function (entrada) {
      if (!ehObjeto(entrada.niveis)) { return; }
      Object.keys(entrada.niveis).forEach(function (id) { if (achados.indexOf(id) === -1) { achados.push(id); } });
    });
    return achados;
  }

  function nivelDoDominio(entrada, id) {
    return ehObjeto(entrada.niveis) && tem(entrada.niveis, id) ? entrada.niveis[id] : null;
  }

  /* Sigla fixa do domínio, com o nome da régua em <abbr>. Domínio que o site
     não conhece aparece pelo id. */
  function siglaDoDominio(apoio, id) {
    if (!tem(SIGLAS_DOMINIO, id)) { return cria('span', 'id-cru', texto(id)); }
    var abbr = cria('abbr', '', SIGLAS_DOMINIO[id]);
    abbr.setAttribute('title', nomeDoDominio(apoio, id));
    return abbr;
  }

  /* Domínios: 5 fitas pequenas, com o nome e o nível mais recente ao lado. */
  function figuraDosDominios(contexto) {
    var apoio = contexto.apoio;
    var historico = contexto.historico;
    var dominios = dominiosDoHistorico(contexto);
    if (!historico.length || !dominios.length) {
      return figura('dominios', T.arquivo.dominios, null, fraseVazia(T.travessao), null);
    }
    /* como na fita grande: com menos de 2 edições, só a tabela */
    var linhas = historico.length < 2 ? [] : dominios.map(function (id) {
      var nome = nomeDoDominio(apoio, id);
      var nivelDe = function (entrada) { return nivelDoDominio(entrada, id); };
      var agoraNoDominio = nivelDe(contexto.ultima);
      return cria('li', 'fitinha', [
        cria('span', 'fitinha__nome', nome),
        fita({
          apoio: apoio, historico: historico, fim: contexto.ultima.data, emTela: null, pequena: true, nivelDe: nivelDe,
          nome: nomeDaFita(nome, historico, nivelDe, 'na edição mais recente', agoraNoDominio)
        }).raiz,
        nivelValido(agoraNoDominio) ? cria('span', 'fitinha__nivel', selo(apoio, agoraNoDominio)) : cria('span', 'fitinha__nivel texto-3', T.travessao)
      ]);
    });
    var colunas = [T.arquivo.data].concat(dominios.map(function (id) {
      return { rotulo: nomeDoDominio(apoio, id), conteudo: siglaDoDominio(apoio, id) };
    }));
    var linhasDaTabela = historico.slice().reverse().map(function (entrada) {
      return [linkInterno(hashEdicao(entrada.data), tempo(entrada.data, true))].concat(dominios.map(function (id) {
        var nivel = nivelDoDominio(entrada, id);
        return { conteudo: nivelValido(nivel) ? String(nivel) : T.travessao, numero: true };
      }));
    });
    return figura('dominios', T.arquivo.dominios, null, linhas.length ? cria('ul', '', linhas) : fraseVazia(T.arquivo.desenhoDepois),
      tabela(T.arquivo.dominios, colunas, linhasDaTabela));
  }

  /* Saldo dos partidos: a soma dos saldos do histórico, em barra a partir
     do zero. Ganha e perde na mesma tinta, como no placar do dia. */
  function figuraDosPartidos(contexto) {
    var apoio = contexto.apoio;
    var ids = apoio.ordemPartidos.slice();
    /* partido que a régua não conhece entra no fim, pelo id */
    contexto.historico.forEach(function (entrada) {
      if (!ehObjeto(entrada.saldos)) { return; }
      Object.keys(entrada.saldos).forEach(function (id) { if (ids.indexOf(id) === -1) { ids.push(id); } });
    });
    if (!ids.length) { return figura('partidos', T.arquivo.partidos, null, fraseVazia(T.travessao), null); }
    var linhas = ids.map(function (id) { return { id: id, saldo: saldoAcumulado(contexto.historico, id) }; });
    var escala = PISO_ESCALA_PLACAR;
    var maior = linhas[0];
    var menor = linhas[0];
    linhas.forEach(function (linha) {
      escala = Math.max(escala, Math.abs(linha.saldo));
      if (linha.saldo > maior.saldo) { maior = linha; }
      if (linha.saldo < menor.saldo) { menor = linha; }
    });
    var nome = 'Saldo dos partidos nos últimos ' + DIAS_HISTORICO + ' dias: ';
    nome += maior.saldo === 0 && menor.saldo === 0 ? 'todos em zero'
      : 'o maior é ' + sinalFalado(maior.saldo) + ', de ' + nomeDoPartido(apoio, maior.id) +
        '; o menor é ' + sinalFalado(menor.saldo) + ', de ' + nomeDoPartido(apoio, menor.id);
    var barras = cria('div', 'saldos', linhas.map(function (linha) {
      return cria('div', 'placar__topo', [
        siglaSemLink(apoio, linha.id),
        cria('span', 'placar__area', [cria('span', 'placar__eixo'),
          barraDoEixo(Math.abs(linha.saldo), escala, linha.saldo < 0 ? 'placar__barra--perde' : 'placar__barra--ganha')]),
        cria('span', 'placar__saldo', comSinal(linha.saldo))
      ]);
    }));
    atributos(barras, { role: 'img', 'aria-label': nome });
    var linhasDaTabela = linhas.map(function (linha) {
      return [[siglaDoPartido(apoio, linha.id), busca(apoio.partidos, linha.id) ? ' ' + nomeDoPartido(apoio, linha.id) : null],
        { conteudo: comSinal(linha.saldo), numero: true }];
    });
    return figura('partidos', T.arquivo.partidos, null, barras,
      tabela(T.arquivo.partidos, ['Partido', 'Saldo'], linhasDaTabela));
  }

  /* Atos por tema: para cada tema que aparece em "eixos", quantos itens
     empurraram para cada polo. Duas barras da mesma tinta, com o texto do
     polo embaixo: as palavras dos polos não aparecem, e não há cor. */
  function figuraDosAtos(contexto) {
    var apoio = contexto.apoio;
    var somas = Object.create(null);
    var achados = [];
    contexto.historico.forEach(function (entrada) {
      if (!ehObjeto(entrada.eixos)) { return; }
      Object.keys(entrada.eixos).forEach(function (id) {
        var eixo = entrada.eixos[id];
        if (!ehObjeto(eixo)) { return; }
        if (!(id in somas)) { somas[id] = { azul: 0, vermelho: 0 }; achados.push(id); }
        if (ehNumero(eixo.azul)) { somas[id].azul += eixo.azul; }
        if (ehNumero(eixo.vermelho)) { somas[id].vermelho += eixo.vermelho; }
      });
    });
    /* a ordem dos temas é a da régua; o que ela não conhece fica no fim */
    var temas = apoio.ordemTemas.filter(function (id) { return id in somas; })
      .concat(achados.filter(function (id) { return apoio.ordemTemas.indexOf(id) === -1; }));
    if (!temas.length) {
      return figura('atos', T.arquivo.atos, T.arquivo.introAtos, fraseVazia(T.arquivo.semAtos), null);
    }
    var escala = PISO_ESCALA_PLACAR;
    var total = 0;
    temas.forEach(function (id) {
      escala = Math.max(escala, somas[id].azul, somas[id].vermelho);
      total += somas[id].azul + somas[id].vermelho;
    });
    function nomeDoTema(id) {
      var tema = busca(apoio.temas, id);
      return tema && texto(tema.nome) ? tema.nome : texto(id);
    }
    function textoDoPolo(id, polo) {
      var tema = busca(apoio.temas, id);
      return tema ? texto(tema[polo]) : '';
    }
    var barras = cria('div', 'atos', temas.map(function (id) {
      return cria('div', 'ato', [
        cria('span', 'ato__tema' + (busca(apoio.temas, id) ? '' : ' id-cru'), nomeDoTema(id)),
        cria('div', 'ato__lados', [
          cria('div', 'ato__barras', [
            cria('span', 'ato__conta', inteiro(somas[id].azul)),
            cria('span', 'placar__area', [barraDoEixo(somas[id].azul, escala, 'ato__barra--esquerda'),
              cria('span', 'placar__eixo'), barraDoEixo(somas[id].vermelho, escala, 'ato__barra--direita')]),
            cria('span', 'ato__conta', inteiro(somas[id].vermelho))
          ]),
          cria('div', 'ato__polos', [
            cria('span', 'ato__polo ato__polo--esquerda', textoDoPolo(id, 'azul')),
            cria('span', 'ato__polo', textoDoPolo(id, 'vermelho'))
          ])
        ])
      ]);
    }));
    atributos(barras, {
      role: 'img',
      'aria-label': 'Atos por tema nos últimos ' + DIAS_HISTORICO + ' dias: ' + inteiro(total) +
        (total === 1 ? ' ato em ' : ' atos em ') + temas.length + (temas.length === 1 ? ' tema' : ' temas')
    });
    var linhasDaTabela = [];
    temas.forEach(function (id) {
      ['azul', 'vermelho'].forEach(function (polo) {
        linhasDaTabela.push([nomeDoTema(id), textoDoPolo(id, polo) || T.travessao, { conteudo: inteiro(somas[id][polo]), numero: true }]);
      });
    });
    return figura('atos', T.arquivo.atos, T.arquivo.introAtos, barras,
      tabela(T.arquivo.atos, [T.arquivo.tema, T.arquivo.polo, T.arquivo.colAtos], linhasDaTabela));
  }

  /* Os pontos de um indicador no histórico: a posição do dia e o valor. */
  function serieDoIndicador(contexto, id) {
    var ultimo = numeroDoDia(contexto.ultima.data);
    var pontos = [];
    contexto.historico.forEach(function (entrada) {
      var valor = ehObjeto(entrada.indicadores) && tem(entrada.indicadores, id) ? entrada.indicadores[id] : null;
      if (ehNumero(valor)) {
        pontos.push({ dia: DIAS_HISTORICO - 1 - (ultimo - numeroDoDia(entrada.data)), data: entrada.data, valor: valor });
      }
    });
    return pontos;
  }

  function umaCasa(n) {
    return Math.round(n * 10) / 10;
  }

  /* Mini-linha: um ponto por edição, na posição do dia. A escala vai do
     menor ao maior valor do período; valores todos iguais dão linha reta a
     meia altura. Dia sem valor quebra a linha. */
  function miniLinha(pontos, nome) {
    var menor = pontos[0].valor;
    var maior = pontos[0].valor;
    pontos.forEach(function (ponto) {
      menor = Math.min(menor, ponto.valor);
      maior = Math.max(maior, ponto.valor);
    });
    function x(ponto) {
      return umaCasa(MINI.margem + ponto.dia * (MINI.largura - 2 * MINI.margem) / (DIAS_HISTORICO - 1));
    }
    function y(ponto) {
      if (maior === menor) { return MINI.altura / 2; }
      return umaCasa(MINI.folga + (1 - (ponto.valor - menor) / (maior - menor)) * (MINI.altura - 2 * MINI.folga));
    }
    var raiz = desenho('svg', {
      'class': 'mini__desenho', viewBox: '0 0 ' + MINI.largura + ' ' + MINI.altura, role: 'img', 'aria-label': nome, focusable: 'false'
    });
    /* um trecho por sequência de dias seguidos com valor */
    var trechos = [];
    pontos.forEach(function (ponto, i) {
      if (i === 0 || ponto.dia !== pontos[i - 1].dia + 1) { trechos.push([]); }
      trechos[trechos.length - 1].push(ponto);
    });
    trechos.forEach(function (trecho) {
      if (trecho.length === 1) {
        /* ponto sozinho: uma linha de um ponto só não desenha nada */
        raiz.appendChild(desenho('circle', { 'class': 'mini__solto', cx: x(trecho[0]), cy: y(trecho[0]), r: 1 }));
      } else {
        raiz.appendChild(desenho('polyline', {
          'class': 'mini__traco', points: trecho.map(function (ponto) { return x(ponto) + ',' + y(ponto); }).join(' ')
        }));
      }
    });
    var final = pontos[pontos.length - 1];
    /* raio de 4 px à vista: o traço do anel, de 2 px, cobre de 4 a 6 */
    raiz.appendChild(desenho('circle', { 'class': 'mini__ponto', cx: x(final), cy: y(final), r: 5 }));
    return raiz;
  }

  /* Indicadores: uma mini-linha por indicador que aparece no índice, com o
     primeiro e o último valor. Nome, unidade e casas vêm do catálogo. */
  function figuraDosIndicadores(contexto) {
    var apoio = contexto.apoio;
    var achados = [];
    contexto.historico.forEach(function (entrada) {
      if (!ehObjeto(entrada.indicadores)) { return; }
      Object.keys(entrada.indicadores).forEach(function (id) {
        if (ehNumero(entrada.indicadores[id]) && achados.indexOf(id) === -1) { achados.push(id); }
      });
    });
    /* a ordem é a do catálogo; o que ele não conhece fica no fim */
    var doCatalogo = apoio.ordemCatalogo;
    var ids = doCatalogo.filter(function (id) { return achados.indexOf(id) !== -1; })
      .concat(achados.filter(function (id) { return doCatalogo.indexOf(id) === -1; }));
    if (!ids.length) {
      /* há edição no histórico, e nenhuma trouxe preço: a frase; sem edição, o travessão */
      return figura('indicadores', T.arquivo.indicadores, null,
        fraseVazia(contexto.historico.length ? T.arquivo.semPrecos : T.travessao), null);
    }
    function nomeDe(id) {
      var linha = busca(apoio.catalogo, id);
      return linha && texto(linha.nome) ? linha.nome : texto(id);
    }
    function valorDe(id, valor) {
      return valorDeIndicador(valor, casasDoIndicador(apoio, id));
    }
    var minis = ids.map(function (id) {
      var doIndicador = busca(apoio.catalogo, id);
      var pontos = serieDoIndicador(contexto, id);
      var primeiro = pontos[0];
      var ultimo = pontos[pontos.length - 1];
      var mini = cria('li', 'mini', [
        cria('h4', 'mini__nome' + (doIndicador ? '' : ' id-cru'), nomeDe(id)),
        cria('p', 'mini__unidade', doIndicador ? texto(doIndicador.unidade) : '')
      ]);
      if (pontos.length < 2) {
        /* com menos de 2 valores, só o número */
        poe(mini, cria('p', 'mini__so', valorDe(id, ultimo.valor)));
        return mini;
      }
      poe(mini, miniLinha(pontos, nomeDe(id) + ' nos últimos ' + DIAS_HISTORICO + ' dias: primeiro valor, ' +
        valorDe(id, primeiro.valor) + '; último, ' + valorDe(id, ultimo.valor)));
      poe(mini, cria('dl', 'mini__pontas', [
        cria('div', 'mini__ponta', [cria('dt', '', T.arquivo.primeiro), cria('dd', '', valorDe(id, primeiro.valor))]),
        cria('div', 'mini__ponta', [cria('dt', '', T.arquivo.ultimo), cria('dd', '', valorDe(id, ultimo.valor))])
      ]));
      return mini;
    });
    var colunas = [T.arquivo.data].concat(ids.map(nomeDe));
    var linhasDaTabela = contexto.historico.slice().reverse().map(function (entrada) {
      return [linkInterno(hashEdicao(entrada.data), tempo(entrada.data, true))].concat(ids.map(function (id) {
        var valor = ehObjeto(entrada.indicadores) && tem(entrada.indicadores, id) ? entrada.indicadores[id] : null;
        return { conteudo: ehNumero(valor) ? valorDe(id, valor) : T.travessao, numero: true };
      }));
    });
    return figura('indicadores', T.arquivo.indicadores, null, cria('ul', 'minis', minis),
      tabela(T.arquivo.indicadores, colunas, linhasDaTabela, { classe: 'tabela--larga' }));
  }

  /* ----- 02 Edições: a lista do índice, por mês, mais nova primeiro ----- */

  function nivelDaConsulta(consulta) {
    return consulta && NIVEIS_MINIMOS.indexOf(consulta.nivel) !== -1 ? consulta.nivel : '';
  }

  /* "Novembro de 2026", sem passar por Date. */
  function nomeDoMes(chave) {
    return MESES[Number(chave.slice(5, 7)) - 1] + ' de ' + chave.slice(0, 4);
  }

  /* As células de uma edição: data e hora; estado; nível; domínios; resumo. */
  function celulasDaEdicao(contexto, entrada) {
    var apoio = contexto.apoio;
    var hora = horaComDia(entrada.gerada_em, entrada.data);
    var quando = null;
    if (hora) {
      quando = cria('time', 'edicao__hora', hora);
      quando.setAttribute('datetime', entrada.gerada_em);
    }
    var estadoDaEdicao = [cria('span', '', rotulo('estado', entrada.estado))];
    if (ehExemplo(entrada)) { estadoDaEdicao.push(etiqueta(T.placas.exemplo)); }
    lista(entrada.corrigida_em).filter(ehTexto).forEach(function (data) {
      var conteudo = [T.arquivo.corrigida, tempo(data, true)];
      estadoDaEdicao.push(ehData(data) && entradaDaData(contexto.entradas, data)
        ? linkInterno(hashEdicao(data), conteudo, 'edicao__corrigida') : cria('span', 'edicao__corrigida', conteudo));
    });
    var dominios = apoio.ordemDominios.length ? apoio.ordemDominios : (ehObjeto(entrada.niveis) ? Object.keys(entrada.niveis) : []);
    var niveis = [];
    dominios.forEach(function (id) {
      var nivel = nivelDoDominio(entrada, id);
      if (nivel === null) { return; }
      niveis.push(cria('span', 'edicao__dominio', [siglaDoDominio(apoio, id), ' ' + texto(nivel)]));
    });
    return [
      [linkInterno(hashEdicao(entrada.data), tempo(entrada.data, true)), quando],
      cria('span', 'marcas', estadoDaEdicao),
      cria('span', 'marcas', [selo(apoio, entrada.nivel, entrada.tendencia), soVista(tendencia(entrada.tendencia))]),
      niveis.length ? cria('span', 'marcas', niveis) : T.travessao,
      { longa: true, conteudo: [cria('span', '', texto(entrada.resumo)), ' ', cria('span', 'edicao__links', [
        linkArquivo(caminhoDoTexto(entrada), T.linkTexto), separador(), linkArquivo(caminhoDaEdicao(entrada), T.linkJson)
      ])] }
    ];
  }

  function secaoEdicoes(contexto, rota) {
    var s = secao('edicoes', '02', T.arquivo.edicoes, null);
    var entradas = contexto.entradas;
    var controle = { raiz: s.raiz, poeNivel: function () {} };
    if (!entradas.length) {
      poe(s.corpo, fraseVazia(T.arquivo.vazio));
      poe(s.corpo, linhaDoIndiceAtualizado(contexto.indice));
      return controle;
    }
    var colunas = [T.arquivo.data, T.arquivo.estado, T.arquivo.nivel, T.arquivo.dominios, T.arquivo.resumo];
    var meses = [];
    entradas.forEach(function (entrada) {
      var chave = entrada.data.slice(0, 7);
      if (!meses.length || meses[meses.length - 1].chave !== chave) { meses.push({ chave: chave, entradas: [], linhas: [] }); }
      meses[meses.length - 1].entradas.push(entrada);
    });
    var nivelMinimo = '';
    var campo = seletor(T.arquivo.nivelMinimo, T.arquivo.todosNiveis, NIVEIS_MINIMOS.map(function (valor) {
      return { valor: valor, nome: valor === String(NIVEL_MAXIMO) ? T.arquivo.so5 : valor + T.arquivo.ouMais };
    }), function (valor) { poeNivel(valor, true); });
    campo.setAttribute('id', novoId('nivel'));
    var rotuloDoCampo = cria('label', 'filtros__rotulo', T.arquivo.nivelMinimo);
    rotuloDoCampo.setAttribute('for', campo.getAttribute('id'));
    var contagem = cria('p', 'filtros__contagem');
    poe(s.corpo, cria('div', 'filtros', [cria('span', 'filtros__busca', [rotuloDoCampo, campo]), contagem]));

    meses.forEach(function (mes, i) {
      var titulo = nomeDoMes(mes.chave) + ' (' + mes.entradas.length + ')';
      var tabelaDoMes = tabela(titulo, colunas, [], { legendaEscondida: true, classe: 'tabela--edicoes' });
      var corpoDaTabela = tabelaDoMes.getElementsByTagName('tbody')[0];
      mes.entradas.forEach(function (entrada) {
        var linha = linhaDeTabela(colunas, celulasDaEdicao(contexto, entrada));
        mes.linhas.push({ entrada: entrada, raiz: linha });
        poe(corpoDaTabela, linha);
      });
      mes.raiz = cria('div', 'mes');
      if (i < MESES_ABERTOS) {
        poe(mes.raiz, cria('h3', 'mes__titulo', titulo), tabelaDoMes);
      } else {
        /* mês mais antigo: dobra fechada, com a contagem no título */
        var abre = tituloDeDobra(titulo);
        var caixa = cria('div', '', tabelaDoMes);
        poe(mes.raiz, cria('h3', 'mes__titulo', abre), caixa);
        ligaDobra(abre, caixa);
      }
      poe(s.corpo, mes.raiz);
    });
    var vazio = esconde(cria('div', 'filtros__vazio', [
      cria('p', '', T.arquivo.vazio),
      botao(T.radar.limpar, '', function () { poeNivel('', true); })
    ]), true);
    poe(s.corpo, vazio, linhaDoIndiceAtualizado(contexto.indice));

    /* Recorta pelo nível mínimo. porLeitor: grava no endereço e anuncia. */
    function poeNivel(valor, porLeitor) {
      nivelMinimo = NIVEIS_MINIMOS.indexOf(valor) !== -1 ? valor : '';
      var minimo = nivelMinimo ? Number(nivelMinimo) : 0;
      var visiveis = 0;
      meses.forEach(function (mes) {
        var doMes = 0;
        mes.linhas.forEach(function (linha) {
          var passa = !minimo || (ehNumero(linha.entrada.nivel) && linha.entrada.nivel >= minimo);
          esconde(linha.raiz, !passa);
          if (passa) { doMes += 1; }
        });
        esconde(mes.raiz, doMes === 0);
        visiveis += doMes;
      });
      campo.value = nivelMinimo;
      var quantas = visiveis + ' de ' + entradas.length + (entradas.length === 1 ? ' edição' : ' edições');
      troca(contagem, minimo ? quantas : '');
      esconde(vazio, visiveis > 0);
      if (porLeitor) {
        var hash = '#/arquivo' + consultaDe({ nivel: nivelMinimo }, PARAMETROS.arquivo);
        gravaEndereco(hash);
        estado.rota = interpretaRota(hash);
        anuncia(visiveis ? quantas : T.arquivo.vazio);
      }
    }
    controle.poeNivel = poeNivel;
    return controle;
  }

  /* "Índice atualizado em 19/11/2026, às 18h14.": dia e hora de Brasília. */
  function linhaDoIndiceAtualizado(indice) {
    var dia = diaDeBrasilia(indice.atualizado_em);
    if (!dia) { return null; }
    var quando = cria('time', '', [dataLonga(dia), ', às ', horaDeBrasilia(indice.atualizado_em)]);
    quando.setAttribute('datetime', indice.atualizado_em);
    return cria('p', 'arquivo__atualizado', [T.arquivo.atualizado, quando, '.']);
  }

  /* ======================================================================
     18. Régua (#/regua/partidos, players, veiculos e vetores)
     Aqui a única cor de dado é a da posição do DNA: nada de nível de alerta.
     ====================================================================== */

  /* Os arquivos que cada aba usa: só a falta deles vira aviso na aba. */
  var ARQUIVOS_DA_ABA = {
    partidos: [ARQ_REGUA, ARQ_PLAYERS],
    players: [ARQ_REGUA, ARQ_PLAYERS, ARQ_VETORES],
    veiculos: [ARQ_REGUA, ARQ_VEICULOS, ARQ_PLAYERS],
    vetores: [ARQ_REGUA, ARQ_VETORES, ARQ_PLAYERS]
  };

  /* #/regua/partidos, #/regua/players, #/regua/veiculos e #/regua/vetores. */
  function abreRegua(rota, primeira) {
    var emTela = estado.regua;
    if (emTela && emTela.aba === rota.aba && emTela.pronta) {
      /* a mesma aba já está na tela: só mudam os filtros e o destino. Uma
         edição que estivesse a caminho é descartada. */
      estado.pedido += 1;
      paraRelogioDemora();
      tiraAvisoGeral('demora');
      vistaAtual().removeAttribute('aria-busy');
      emTela.aplica(rota, true);
      return Promise.resolve();
    }
    var corpo = abreVistaSimples('regua', primeira);
    var pedido = estado.pedido;
    esperaDados(corpo);
    var caminhos = [ARQ_REGUA, ARQ_PLAYERS, ARQ_VEICULOS, ARQ_VETORES, ARQ_INDICE];
    return leParaVista(caminhos).then(function (lidos) {
      montaComRede(pedido, corpo, ARQ_REGUA, function () {
        montaRegua(corpo, rota, lidos, faltasEFormatos(caminhos, lidos), pedido);
      });
    });
  }

  function montaRegua(corpo, rota, lidos, situacao, pedido) {
    var entradas = lidos[4] ? entradasDoIndice(lidos[4]) : [];
    var ultima = ultimaReal(entradas);
    var contexto = {
      apoio: montaApoio(lidos[0], lidos[1], lidos[2], lidos[3], null),
      jogadores: lista(ehObjeto(lidos[1]) ? lidos[1].players : null).filter(ehObjeto),
      arquivoDePlayers: lidos[1],
      mapa: lidos[2],
      arquivoDeVetores: lidos[3],
      /* o índice aqui é apoio: sem ele, a aba abre sem saldo e sem link para edição */
      temIndice: !!lidos[4],
      entradas: entradas,
      historico: ultima ? historicoAte(entradas, ultima.data) : [],
      pedido: pedido
    };
    var daAba = ARQUIVOS_DA_ABA[rota.aba];
    function ehDaAba(arquivo) { return daAba.indexOf(arquivo) !== -1; }
    var montadores = { partidos: abaPartidos, players: abaPlayers, veiculos: abaVeiculos, vetores: abaVetores };
    var aba = montadores[rota.aba](contexto);
    aba.aba = rota.aba;
    poe(corpo, abasDaRegua(rota.aba), legendaDaRegua(contexto),
      cria('div', 'avisos', avisosDeArquivos(situacao.faltas.filter(ehDaAba), situacao.novos.filter(ehDaAba))), aba.raiz);
    estado.regua = aba;
    aba.inicia(rota);
  }

  /* Fileira de 4 links: são links comuns dentro de um nav, e não um conjunto
     de abas com setas. */
  function abasDaRegua(ativa) {
    var nav = cria('nav', 'abas');
    nav.setAttribute('aria-label', 'Abas da Régua');
    ABAS_REGUA.forEach(function (aba) {
      var link = linkInterno(hashRegua(aba), T.regua.abas[aba], 'abas__link');
      if (aba === ativa) { link.setAttribute('aria-current', 'page'); }
      poe(nav, link);
    });
    return nav;
  }

  /* Célula de exemplo da legenda: só a letra. O texto ao lado diz o que é. */
  function celulaDeLegenda(letras) {
    return soVista(cria('span', 'dna__celula', letras.split('').map(metadeDeDna)));
  }

  /* Legenda, sempre à vista: descrição, aviso, as 5 letras e a virada.
     "COMO LER", fechada: os polos, os temas e a data de criação. */
  function legendaDaRegua(contexto) {
    var apoio = contexto.apoio;
    var regua = apoio.regua;
    var caixa = cria('div', 'legenda');
    if (texto(regua.descricao)) { poe(caixa, cria('p', 'legenda__descricao', texto(regua.descricao))); }
    if (texto(regua.aviso)) { poe(caixa, aviso({ texto: texto(regua.aviso) })); }
    var itens = Object.keys(LETRAS_DNA).map(function (letra) {
      return cria('li', 'legenda__item', [celulaDeLegenda(letra), cria('span', '', significadoDaLetra(apoio, letra))]);
    });
    itens.push(cria('li', 'legenda__item', [celulaDeLegenda('BR'), cria('span', '', texto(regua.virada) || T.regua.virada)]));
    poe(caixa, cria('ul', 'legenda__letras', itens));

    var como = [];
    var polos = ehObjeto(regua.polos) ? regua.polos : {};
    [['B', 'azul'], ['R', 'vermelho']].forEach(function (par) {
      if (tem(polos, par[1]) && texto(polos[par[1]])) {
        como.push(cria('p', 'legenda__item', [celulaDeLegenda(par[0]), cria('span', '', texto(polos[par[1]]))]));
      }
    });
    var temas = lista(regua.temas).filter(ehObjeto);
    if (temas.length) {
      como.push(tabela('Temas da régua', ['Sigla', T.arquivo.tema, LETRAS_DNA.B, LETRAS_DNA.R], temas.map(function (tema) {
        return [cria('span', 'mono', texto(tema.sigla) || texto(tema.id)), texto(tema.nome), texto(tema.azul), texto(tema.vermelho)];
      })));
    }
    if (ehData(regua.criada_em)) {
      como.push(cria('p', 'legenda__criada', ['Régua criada em ', tempo(regua.criada_em, true), '.']));
    }
    if (como.length) {
      var abre = tituloDeDobra(T.regua.comoLer);
      var corpoDaDobra = cria('div', 'legenda__como', como);
      poe(caixa, cria('p', 'legenda__abre', abre), corpoDaDobra);
      ligaDobra(abre, corpoDaDobra);
    }
    return caixa;
  }

  /* Leva o leitor ao destino da rota. alvo: { foco, dobra } ou null.
     Sem ficha na rota, o foco vai para o título da vista (focar: quando a
     rota mudou dentro da mesma aba; na primeira montagem ele já foi posto). */
  function destinoDaRegua(rota, alvo, focar) {
    if (rota.ficha && alvo) {
      if (alvo.dobra) { alvo.dobra.poe(true); }
      levaAte(alvo.foco);
      return;
    }
    if (rota.ficha) { avisaFichaNaoEncontrada(rota.ficha); }
    if (focar) { focaTituloDaVista(); }
  }

  /* Recorte de uma lista da Régua: busca (sem maiúscula e sem acento, no
     nome e no id) e listas nativas. Os filtros se somam, vão para o endereço
     e voltam dele; a contagem é anunciada. Filtrar nunca muda a ordem.
     c: aba, plural, itens [{ chaves, busca, grupo, linha }], grupos
     [{ raiz }], campos (um por parâmetro), validos (valores de cada lista),
     contagem, vazio, textoVazio. A linha de um item pode ainda não existir. */
  function recorteDaRegua(c) {
    var parametros = PARAMETROS[c.aba];

    function limpos() {
      var filtros = {};
      parametros.forEach(function (nome) { filtros[nome] = ''; });
      return filtros;
    }
    var filtros = limpos();

    /* Só passa valor que está na lista do filtro. A busca é texto livre. */
    function daConsulta(consulta) {
      var novos = limpos();
      parametros.forEach(function (nome) {
        var valor = consulta ? consulta[nome] : null;
        if (!ehTexto(valor)) { return; }
        if (nome === 'q') { novos.q = valor.slice(0, BUSCA_MAXIMA); } else if (c.validos[nome].indexOf(valor) !== -1) { novos[nome] = valor; }
      });
      return novos;
    }

    function passa(item) {
      return parametros.every(function (nome) {
        if (nome === 'q') {
          var procurado = semAcento(filtros.q).trim();
          return procurado === '' || item.busca.indexOf(procurado) !== -1;
        }
        return filtros[nome] === '' || item.chaves[nome] === filtros[nome];
      });
    }

    function mostra(item) {
      if (!item.linha) { return; }
      esconde(item.linha.raiz, !item.passa);
      lista(item.linha.extras).forEach(function (extra) { esconde(extra, !item.passa); });
    }

    function recorta(novos, porLeitor) {
      filtros = novos;
      var visiveis = 0;
      c.grupos.forEach(function (grupo) { grupo.visiveis = 0; });
      c.itens.forEach(function (item) {
        item.passa = passa(item);
        if (item.passa) { visiveis += 1; item.grupo.visiveis += 1; }
        mostra(item);
      });
      c.grupos.forEach(function (grupo) { esconde(grupo.raiz, grupo.visiveis === 0); });
      parametros.forEach(function (nome) {
        /* o campo de busca só é reescrito se diverge: senão o cursor pularia a cada tecla */
        if (texto(c.campos[nome].value) !== filtros[nome]) { c.campos[nome].value = filtros[nome]; }
      });
      var procurado = filtros.q.trim();
      var filtrando = parametros.some(function (nome) { return nome === 'q' ? procurado !== '' : filtros[nome] !== ''; });
      var quantos = visiveis + ' de ' + c.itens.length + ' ' + c.plural;
      var semNada = procurado ? T.regua.nadaEncontrado + procurado + '".' : quantos;
      troca(c.contagem, filtrando ? quantos : '');
      troca(c.textoVazio, semNada);
      esconde(c.vazio, visiveis > 0);
      if (porLeitor) {
        var paraOEndereco = limpos();
        parametros.forEach(function (nome) { paraOEndereco[nome] = nome === 'q' && procurado === '' ? '' : filtros[nome]; });
        var hash = hashRegua(c.aba) + consultaDe(paraOEndereco, parametros);
        gravaEndereco(hash);
        estado.rota = interpretaRota(hash);
        anuncia(visiveis ? quantos : semNada);
      }
    }

    return {
      daConsulta: daConsulta,
      poe: recorta,
      mostra: mostra,
      limpa: function (porLeitor) { recorta(limpos(), porLeitor); },
      muda: function (nome, valor) {
        var novos = limpos();
        parametros.forEach(function (outro) { novos[outro] = filtros[outro]; });
        novos[nome] = valor;
        recorta(daConsulta(novos), true);
      }
    };
  }

  /* A fileira de filtros de uma aba: busca, listas, contagem e, embaixo, o
     aviso de "nada encontrado" com o botão de limpar. Devolve as peças. */
  function filtrosDaAba(rotuloDaBusca, listas, aoMudar, aoLimpar) {
    var campos = {};
    var busca = campoDeBusca(rotuloDaBusca, function (valor) { aoMudar('q', valor); });
    campos.q = busca.campo;
    var fileira = cria('div', 'filtros', busca.raiz);
    listas.forEach(function (umaLista) {
      campos[umaLista.nome] = seletor(umaLista.rotulo, umaLista.primeira, umaLista.opcoes, function (valor) { aoMudar(umaLista.nome, valor); });
      poe(fileira, campos[umaLista.nome]);
    });
    var contagem = cria('p', 'filtros__contagem');
    poe(fileira, contagem);
    var textoVazio = cria('p', '');
    var vazio = esconde(cria('div', 'filtros__vazio', [textoVazio, botao(T.radar.limpar, '', aoLimpar)]), true);
    return { fileira: fileira, campos: campos, contagem: contagem, vazio: vazio, textoVazio: textoVazio };
  }

  /* Nomes de players em lista corrida; cada um leva à linha do player. */
  function nomesDePlayers(jogadores, comMarca) {
    var partes = [];
    jogadores.forEach(function (player, i) {
      if (i > 0) { partes.push(', '); }
      var nome = texto(player.nome) || texto(player.id);
      partes.push(ehId(player.id) ? linkInterno(hashRegua('players', player.id), nome) : cria('span', '', nome));
      if (comMarca && player.time_discutivel === true) { partes.push(' ', etiqueta(T.movimentos.timeDiscutivel)); }
    });
    return partes.length ? partes : T.travessao;
  }

  /* Saldo para a vista e para o leitor de tela: "+4" e "mais 4". */
  function saldoComFala(n) {
    return [soLeitor(sinalFalado(n)), soVista(cria('span', 'mono', comSinal(n)))];
  }

  /* ----- aba Partidos ----- */

  function abaPartidos(contexto) {
    var apoio = contexto.apoio;
    var regua = apoio.regua;
    var fichas = Object.create(null);
    var raiz = cria('div', 'aba');
    poe(raiz, cria('h2', 'so-leitor', T.regua.abas.partidos));
    var partidos = lista(regua.partidos).filter(ehObjeto);
    poe(raiz, partidos.length ? cria('div', 'partidos', partidos.map(function (partido) { return fichaDePartido(contexto, partido, fichas); }))
      : fraseVazia(T.travessao));
    poe(raiz, cria('h2', 'subtitulo', T.regua.times));
    var times = lista(regua.times).filter(ehObjeto);
    poe(raiz, times.length ? cria('div', 'times', times.map(function (time) {
      var doTime = contexto.jogadores.filter(function (player) { return player.time === time.id; });
      return cria('article', 'time', [
        cria('h3', 'time__nome', texto(time.nome) || texto(time.id)),
        texto(time.descricao) ? cria('p', 'texto-2', texto(time.descricao)) : null,
        cria('p', 'rotulo', T.regua.players + ' (' + doTime.length + ')'),
        cria('p', '', nomesDePlayers(doTime, true))
      ]);
    })) : fraseVazia(T.travessao));
    var arquivo = contexto.arquivoDePlayers;
    if (ehObjeto(arquivo) && (texto(arquivo.regra) || ehData(arquivo.atualizado_em))) {
      poe(raiz, cria('p', 'aba__regra', [texto(arquivo.regra),
        ehData(arquivo.atualizado_em) ? [' Lista de players atualizada em ', tempo(arquivo.atualizado_em, true), '.'] : null]));
    }
    function aplica(rota, focar) {
      destinoDaRegua(rota, rota.ficha ? busca(fichas, rota.ficha) : null, focar);
    }
    return { raiz: raiz, pronta: true, aplica: aplica, inicia: function (rota) { aplica(rota, false); } };
  }

  /* Ficha de partido: sigla, nome, voto típico, postura, players e saldo. */
  function fichaDePartido(contexto, partido, fichas) {
    var apoio = contexto.apoio;
    var id = partido.id;
    var raiz = cria('article', 'partido');
    var titulo = cria('h3', 'partido__nome', texto(partido.nome) || texto(id));
    titulo.setAttribute('tabindex', '-1');
    if (ehId(id) && !(id in fichas)) {
      raiz.setAttribute('id', 'partido-' + id);
      fichas[id] = { foco: titulo };
    }
    poe(raiz, cria('p', 'marcas', siglaSemLink(apoio, id)), titulo, cria('p', 'rotulo', T.regua.votoTipico));
    /* no arquivo, o voto típico são 7 letras separadas por espaço; vazio é "sem voto típico" */
    var votos = texto(partido.voto_tipico).split(/\s+/).filter(function (voto) { return voto !== ''; });
    if (votos.length) {
      var dna = Object.create(null);
      apoio.ordemTemas.forEach(function (tema, i) { if (i < votos.length) { dna[tema] = votos[i]; } });
      poe(raiz, tiraDeDna(apoio, dna, [], true));
    } else {
      poe(raiz, cria('p', 'partido__texto', T.regua.semVoto));
    }
    var doPartido = contexto.jogadores.filter(function (player) { return player.partido === id; });
    poe(raiz,
      /* campo só de apresentação, que o validador não confere: sem ele, travessão sob o rótulo */
      cria('p', 'rotulo', T.regua.dianteDaOrdem), cria('p', 'partido__texto', texto(partido.diante_da_ordem) || T.travessao),
      texto(partido.descricao) ? cria('p', 'partido__texto texto-2', texto(partido.descricao)) : null,
      cria('p', 'rotulo', T.regua.players + ' (' + doPartido.length + ')'), cria('p', 'partido__texto', nomesDePlayers(doPartido, false)),
      cria('p', 'partido__saldo', [cria('span', 'rotulo', T.regua.saldo), ' ',
        contexto.temIndice ? saldoComFala(saldoAcumulado(contexto.historico, id)) : cria('span', 'mono', T.travessao)]));
    return raiz;
  }

  /* ----- aba Players ----- */

  /* "principal 1" ou "radar 4", com link para o item se a edição está no
     índice. Item fora da forma aparece cru. */
  function itemDoRegistro(contexto, entrada) {
    var item = entrada.item;
    if (item === undefined) { return null; }
    var nome = null;
    if (ehTexto(item) && FORMA_ITEM_PRINCIPAL.test(item)) { nome = 'principal ' + numeroDoItem(item); }
    if (ehTexto(item) && FORMA_ITEM_RADAR.test(item)) { nome = 'radar ' + numeroDoItem(item); }
    if (nome === null) { return cria('span', 'id-cru', texto(item)); }
    if (ehData(entrada.data) && entradaDaData(contexto.entradas, entrada.data)) {
      return linkInterno(hashEdicao(entrada.data, item), [nome, soLeitor(' da edição de ' + dataLonga(entrada.data))]);
    }
    return cria('span', '', nome);
  }

  /* Uma entrada do registro, no desenho da linha de vetor. Serve à linha
     aberta do player: a data vem no lugar do nome. */
  function linhaDoRegistro(contexto, entrada) {
    var apoio = contexto.apoio;
    var anulacao = anulacaoDe(apoio, entrada.id);
    var linha = cria('div', 'vetor' + (anulacao ? ' vetor--anulado' : ''));
    var riscado = cria('span', 'vetor__riscado', [
      tempo(entrada.data, true), siglaDoPartido(apoio, entrada.de), seta('desloca-se para'),
      siglaDoPartido(apoio, entrada.para), forca(apoio, entrada.forca), etiquetaDeTema(apoio, entrada.tema)
    ]);
    var cabeca = cria('p', 'vetor__cabeca', [anulacao ? soLeitor('Anulado: ') : null, riscado]);
    if (anulacao) { poe(cabeca, etiqueta(T.itens.anulado)); }
    if (entrada.conflito_de_interesse === true) { poe(cabeca, etiqueta(T.itens.conflito)); }
    poe(cabeca, itemDoRegistro(contexto, entrada));
    poe(linha, cabeca, cria('p', 'vetor__porque', texto(entrada.porque)),
      cria('p', 'vetor__link', linkExterno(entrada.url, T.itens.prova)));
    if (anulacao) { poe(linha, linhaDaAnulacao(anulacao)); }
    return linha;
  }

  /* Do mais novo para o mais antigo; no mesmo dia, o que entrou por último
     no registro vem antes. */
  function maisNovosPrimeiro(entradas) {
    return entradas.map(function (entrada, i) { return { entrada: entrada, i: i }; })
      .sort(function (a, b) {
        var dataA = texto(a.entrada.data);
        var dataB = texto(b.entrada.data);
        return dataA < dataB ? 1 : (dataA > dataB ? -1 : b.i - a.i);
      }).map(function (par) { return par.entrada; });
  }

  /* Opções de uma lista nativa a partir de ids: o nome vem de quem souber. */
  function opcoesDe(ids, nomeDe) {
    return ids.map(function (id) { return { valor: id, nome: nomeDe(id) }; });
  }

  function abaPlayers(contexto) {
    var apoio = contexto.apoio;
    var jogadores = contexto.jogadores;
    var fichas = Object.create(null);
    var raiz = cria('div', 'aba');
    poe(raiz, cria('h2', 'so-leitor', T.regua.abas.players));
    if (!jogadores.length) {
      poe(raiz, fraseVazia(T.travessao));
      return abaSemLista(raiz);
    }
    var temas = apoio.ordemTemas.length ? apoio.ordemTemas : Object.keys(ehObjeto(jogadores[0].dna) ? jogadores[0].dna : {});
    var colunas = temas.length + 5;

    /* os vetores de cada player, sem as entradas de anulação */
    var vetoresDe = Object.create(null);
    apoio.registro.forEach(function (entrada) {
      if (ehAnulacao(entrada) || !ehTexto(entrada.player)) { return; }
      if (!(entrada.player in vetoresDe)) { vetoresDe[entrada.player] = []; }
      vetoresDe[entrada.player].push(entrada);
    });

    /* valores de cada lista: os da régua; sem ela, os que os players trazem */
    function valoresDe(campo, daRegua) {
      var ids = daRegua.filter(ehId);
      if (ids.length) { return ids; }
      jogadores.forEach(function (player) { if (ehId(player[campo]) && ids.indexOf(player[campo]) === -1) { ids.push(player[campo]); } });
      return ids;
    }
    var validos = {
      partido: valoresDe('partido', apoio.ordemPartidos),
      tipo: valoresDe('tipo', idsDe(apoio.regua.tipos)),
      time: valoresDe('time', idsDe(apoio.regua.times))
    };
    function nomeEm(tabelaDeNomes) {
      return function (id) {
        var linha = busca(tabelaDeNomes, id);
        return linha && texto(linha.nome) ? linha.nome : id;
      };
    }
    var recorte;
    var pecas = filtrosDaAba(T.regua.buscarPlayer, [
      { nome: 'partido', rotulo: T.radar.porPartido, primeira: T.radar.todosPartidos, opcoes: opcoesDe(validos.partido, nomeEm(apoio.partidos)) },
      { nome: 'tipo', rotulo: 'Filtrar por tipo', primeira: T.regua.todosTipos, opcoes: opcoesDe(validos.tipo, nomeEm(apoio.tipos)) },
      { nome: 'time', rotulo: 'Filtrar por time', primeira: T.regua.todosTimes, opcoes: opcoesDe(validos.time, nomeEm(apoio.times)) }
    ], function (nome, valor) { recorte.muda(nome, valor); }, function () { recorte.limpa(true); });

    /* a matriz: tabela de verdade, com um grupo de linhas por partido */
    var matriz = cria('table', 'matriz');
    matriz.setAttribute('role', 'table');
    poe(matriz, cria('caption', 'so-leitor', T.regua.abas.players));
    function cabecalho(conteudo, classe) {
      var th = cria('th', classe || '', conteudo);
      atributos(th, { scope: 'col', role: 'columnheader' });
      return th;
    }
    var cabeca = cria('tr');
    cabeca.setAttribute('role', 'row');
    poe(cabeca, cabecalho('Nome'), cabecalho('Tipo'), cabecalho('Time'));
    temas.forEach(function (id) {
      var tema = busca(apoio.temas, id);
      var sigla = cria('abbr', '', tema ? texto(tema.sigla) || texto(id) : texto(id));
      if (tema) { sigla.setAttribute('title', texto(tema.nome)); }
      poe(cabeca, cabecalho(sigla, 'matriz__tema'));
    });
    poe(cabeca, cabecalho('Vetores', 'num'), cabecalho(soLeitor('Abrir a linha')));
    var grupoDaCabeca = cria('thead', '', cabeca);
    grupoDaCabeca.setAttribute('role', 'rowgroup');
    poe(matriz, grupoDaCabeca);

    function celula(classe, conteudo, rotuloDaCelula) {
      var td = cria('td', classe, conteudo);
      td.setAttribute('role', 'cell');
      if (rotuloDaCelula) { td.setAttribute('data-rotulo', rotuloDaCelula); }
      return td;
    }

    function linhaDePlayer(player, item) {
      var id = player.id;
      var nome = texto(player.nome) || texto(id);
      var tr = cria('tr', 'matriz__linha');
      tr.setAttribute('role', 'row');
      var cabecaDaLinha = cria('th', 'matriz__nome', nome);
      atributos(cabecaDaLinha, { scope: 'row', role: 'rowheader', tabindex: '-1' });
      var tipo = busca(apoio.tipos, player.tipo);
      var time = busca(apoio.times, player.time);
      poe(tr, cabecaDaLinha,
        celula('matriz__texto', cria('span', tipo ? '' : 'id-cru', tipo ? texto(tipo.nome) : texto(player.tipo))),
        celula('matriz__texto', [cria('span', time ? '' : 'id-cru', time ? texto(time.nome) : texto(player.time)),
          player.time_discutivel === true ? cria('span', 'matriz__discutivel', T.movimentos.timeDiscutivel) : null]));
      var dna = ehObjeto(player.dna) ? player.dna : {};
      temas.forEach(function (idDoTema) {
        var tema = busca(apoio.temas, idDoTema);
        poe(tr, celula('matriz__dna', celulaDeDna(apoio, tema ? texto(tema.nome) : texto(idDoTema),
          tem(dna, idDoTema) ? dna[idDoTema] : '', lista(player.duvidas).indexOf(idDoTema) !== -1),
        tema ? texto(tema.sigla) || texto(idDoTema) : texto(idDoTema)));
      });
      var doPlayer = maisNovosPrimeiro(busca(vetoresDe, id) || []);
      /* o anulado fica à vista na linha aberta, mas não entra na conta */
      var validosDoPlayer = doPlayer.filter(function (entrada) { return !anulacaoDe(apoio, entrada.id); }).length;
      var nomeDoBotao = soLeitor('Abrir: ' + nome);
      var abre = botao([icone('i-dobra', 'icone--dobra'), nomeDoBotao], 'botao--dobra');
      poe(tr, celula('matriz__vetores num', String(validosDoPlayer), 'Vetores'), celula('matriz__acao', abre));

      var corpo = cria('div', 'player__corpo', detalheDoPlayer(player, doPlayer, validosDoPlayer));
      var celulaDoDetalhe = celula('', corpo);
      celulaDoDetalhe.setAttribute('colspan', colunas);
      var detalhe = cria('tr', 'matriz__detalhe', celulaDoDetalhe);
      detalhe.setAttribute('role', 'row');
      var dobra = ligaDobra(abre, corpo);
      dobra.aoPor = function (aberta) {
        troca(nomeDoBotao, (aberta ? 'Fechar: ' : 'Abrir: ') + nome);
        /* fechada, a linha de detalhe é uma linha vazia: o leitor de tela a pula */
        if (aberta) { detalhe.removeAttribute('aria-hidden'); } else { detalhe.setAttribute('aria-hidden', 'true'); }
      };
      dobra.poe(false);
      if (ehId(id) && !(id in fichas)) {
        tr.setAttribute('id', 'player-' + id);
        fichas[id] = { foco: cabecaDaLinha, dobra: dobra, item: item };
      }
      return { raiz: tr, extras: [detalhe] };
    }

    /* A linha aberta: nota, dúvidas, origem, justificativa, fontes e vetores. */
    function detalheDoPlayer(player, doPlayer, quantosValem) {
      var partes = [];
      if (texto(player.nota)) { partes.push(cria('p', '', texto(player.nota))); }
      var duvidas = lista(player.duvidas).filter(ehTexto);
      if (duvidas.length) {
        partes.push(cria('p', '', [cria('span', 'dossie__rotulo', T.regua.emDuvidaEm), duvidas.map(function (idDoTema) {
          var tema = busca(apoio.temas, idDoTema);
          return tema && texto(tema.nome) ? tema.nome : idDoTema;
        }).join(', ')]));
      }
      if (player.origem === 'regua') {
        partes.push(cria('p', 'texto-2', T.regua.daRegua));
      } else if (player.origem === 'rotina') {
        partes.push(cria('p', 'texto-2', [T.regua.entrou, tempo(player.incluido_em, true), T.regua.pelaRotina]));
      } else if (player.origem !== undefined) {
        partes.push(cria('p', 'texto-2', cria('span', 'id-cru', texto(player.origem))));
      }
      if (player.justificativa !== undefined || player.url !== undefined) {
        partes.push(cria('p', '', [cria('span', 'dossie__rotulo', T.movimentos.porQueEntrou), texto(player.justificativa), ' ',
          player.url !== undefined ? linkExterno(player.url, T.vigiar.fonte) : null]));
      }
      partes.push(fontesDasPosicoes(apoio, player));
      partes.push(cria('p', 'rotulo', T.regua.vetoresRegistrados + ' (' + quantosValem + ')'));
      partes.push(doPlayer.length ? cria('div', 'vetores', doPlayer.map(function (entrada) { return linhaDoRegistro(contexto, entrada); }))
        : fraseVazia(T.regua.semVetores));
      return partes;
    }

    /* um grupo de linhas por partido, na ordem da régua; o que ela não
       conhece fica no fim, pelo id */
    var ordem = apoio.ordemPartidos.slice();
    jogadores.forEach(function (player) {
      if (ordem.indexOf(texto(player.partido)) === -1) { ordem.push(texto(player.partido)); }
    });
    var itens = [];
    var grupos = [];
    ordem.forEach(function (idDoPartido) {
      var doPartido = jogadores.filter(function (player) { return texto(player.partido) === idDoPartido; });
      if (!doPartido.length) { return; }
      var corpoDoGrupo = cria('tbody', '');
      corpoDoGrupo.setAttribute('role', 'rowgroup');
      var cabecaDoGrupo = cria('th', '', busca(apoio.partidos, idDoPartido)
        ? [siglaDoPartido(apoio, idDoPartido), cria('span', '', nomeDoPartido(apoio, idDoPartido)), cria('span', 'texto-3', '(' + doPartido.length + ')')]
        : [cria('span', 'id-cru', idDoPartido), cria('span', 'texto-3', '(' + doPartido.length + ')')]);
      atributos(cabecaDoGrupo, { scope: 'rowgroup', role: 'rowheader', colspan: colunas });
      var linhaDoGrupo = cria('tr', 'matriz__grupo', cabecaDoGrupo);
      linhaDoGrupo.setAttribute('role', 'row');
      poe(corpoDoGrupo, linhaDoGrupo);
      var grupo = { raiz: corpoDoGrupo, visiveis: 0 };
      grupos.push(grupo);
      doPartido.forEach(function (player) {
        var item = {
          chaves: { partido: player.partido, tipo: player.tipo, time: player.time },
          busca: semAcento(player.nome) + ' ' + semAcento(player.id),
          grupo: grupo,
          passa: true
        };
        item.linha = linhaDePlayer(player, item);
        itens.push(item);
        poe(corpoDoGrupo, item.linha.raiz, item.linha.extras);
      });
      poe(matriz, corpoDoGrupo);
    });

    recorte = recorteDaRegua({
      aba: 'players', plural: T.regua.players, itens: itens, grupos: grupos, validos: validos,
      campos: pecas.campos, contagem: pecas.contagem, vazio: pecas.vazio, textoVazio: pecas.textoVazio
    });
    poe(raiz, pecas.fileira, matriz, pecas.vazio);

    function aplica(rota, focar) {
      recorte.poe(recorte.daConsulta(rota.consulta), false);
      var ficha = rota.ficha ? busca(fichas, rota.ficha) : null;
      /* a ficha pedida pelo endereço nunca fica escondida por filtro */
      if (ficha && !ficha.item.passa) { recorte.limpa(false); }
      destinoDaRegua(rota, ficha, focar);
    }
    return { raiz: raiz, pronta: true, aplica: aplica, inicia: function (rota) { aplica(rota, false); } };
  }

  /* Aba que não tem o que listar: qualquer ficha pedida é "não encontrada". */
  function abaSemLista(raiz) {
    function aplica(rota, focar) { destinoDaRegua(rota, null, focar); }
    return { raiz: raiz, pronta: true, aplica: aplica, inicia: function (rota) { aplica(rota, false); } };
  }

  /* ----- aba Veículos ----- */

  /* Ids de players ou de partidos (serve_a, alvos). Partido vira sigla;
     player, o nome com link para a ficha; o que não existe aparece cru. */
  function referencias(contexto, ids) {
    var apoio = contexto.apoio;
    var partes = [];
    lista(ids).filter(ehTexto).forEach(function (id, i) {
      if (i > 0) { partes.push(', '); }
      var player = busca(apoio.players, id);
      if (busca(apoio.partidos, id)) {
        partes.push(siglaDoPartido(apoio, id));
      } else if (player) {
        var nome = texto(player.nome) || id;
        partes.push(ehId(id) ? linkInterno(hashRegua('players', id), nome) : cria('span', '', nome));
      } else {
        partes.push(cria('span', 'id-cru', id));
      }
    });
    return partes.length ? partes : T.travessao;
  }

  /* Lista de valores que aparecem crus, em mono: idiomas e nomes de site.
     Nome de site nunca vira link: não é endereço conferido. */
  function valoresCrus(itens) {
    var textos = lista(itens).filter(ehTexto);
    return textos.length ? cria('span', 'mono', textos.join(', ')) : T.travessao;
  }

  /* Os feeds do veículo e, abaixo deles, a nota de feeds, em texto simples. */
  function feedsDoVeiculo(veiculo) {
    var feeds = lista(veiculo.feeds).filter(ehObjeto);
    var partes = [];
    if (feeds.length) {
      partes.push(cria('ul', '', feeds.map(function (feed) {
        return cria('li', 'feed', [
          cria('p', 'marcas', [
            texto(feed.secao) ? cria('span', '', texto(feed.secao)) : null,
            texto(feed.formato) ? cria('span', 'mono', texto(feed.formato)) : null,
            cria('span', 'texto-2', feed.conferido === true ? T.regua.conferido : T.regua.naoConferido)
          ]),
          texto(feed.nota) ? cria('p', 'texto-2', texto(feed.nota)) : null,
          cria('p', '', linkExterno(feed.url, texto(feed.url), 'feed__url'))
        ]);
      })));
    } else {
      partes.push(cria('p', 'vazio', T.regua.nenhumFeed));
    }
    /* feeds_nota diz por que não há feed, ou onde ler as manchetes. O
       endereço que ela cita não foi conferido: fica como texto, sem link. */
    if (texto(veiculo.feeds_nota)) { partes.push(cria('p', 'feed__nota', texto(veiculo.feeds_nota))); }
    return partes;
  }

  /* Linha de veículo. Fechada: nome, país, tipo, lado e as duas confianças.
     Aberta: o resto da ficha. Devolve { raiz, foco, dobra }. */
  function linhaDeVeiculo(contexto, veiculo) {
    var apoio = contexto.apoio;
    var id = veiculo.id;
    var nome = texto(veiculo.nome) || texto(id);
    var raiz = cria('article', 'veiculo');
    var titulo = cria('h4', 'veiculo__nome', nome);
    titulo.setAttribute('tabindex', '-1');
    var nomeDoBotao = soLeitor('Abrir: ' + nome);
    var abre = botao([icone('i-dobra', 'icone--dobra'), nomeDoBotao], 'botao--dobra');
    var origem = [texto(veiculo.pais), rotulo('tipoVeiculo', veiculo.tipo)].filter(function (parte) { return parte !== ''; });
    poe(raiz, cria('div', 'veiculo__cabeca', [
      cria('div', 'veiculo__resumo', [
        titulo,
        cria('p', 'veiculo__meta', origem.join(T.separador)),
        cria('p', 'marcas veiculo__meta', [
          cria('span', '', T.regua.lado), siglaDoPartido(apoio, veiculo.lado),
          cria('span', '', T.regua.confiancaNoLado + ': ' + rotulo('confianca', veiculo.lado_confianca)),
          cria('span', '', T.regua.confiabilidade + ': ' + rotulo('confianca', veiculo.fatos)),
          veiculo.lado_confianca === 'baixa' ? etiqueta(T.itens.ladoIncerto) : null
        ])
      ]),
      abre
    ]));
    function par(rotuloDoPar, conteudo) {
      return cria('div', 'dados__par', [cria('dt', '', rotuloDoPar), cria('dd', '', conteudo)]);
    }
    var corpo = cria('div', 'veiculo__corpo', cria('dl', 'dados', [
      par(T.regua.pais, texto(veiculo.pais) || T.travessao),
      par(T.regua.idiomas, valoresCrus(veiculo.idiomas)),
      par(T.regua.sites, valoresCrus(veiculo.sites)),
      par(T.regua.controle, [texto(veiculo.controle) || T.travessao, ' ',
        veiculo.controle_fonte !== undefined ? linkExterno(veiculo.controle_fonte, T.vigiar.fonte) : null]),
      par(T.regua.serveA, referencias(contexto, veiculo.serve_a)),
      par(T.regua.alvos, referencias(contexto, veiculo.alvos)),
      par(T.regua.porQueLado, texto(veiculo.lado_porque) || T.travessao),
      par(T.regua.sobreFatos, texto(veiculo.fatos_nota) || T.travessao),
      par(T.regua.uso, texto(veiculo.uso) || T.travessao),
      par(T.regua.feeds, feedsDoVeiculo(veiculo))
    ]));
    poe(raiz, corpo);
    var dobra = ligaDobra(abre, corpo);
    dobra.aoPor = function (aberta) { troca(nomeDoBotao, (aberta ? 'Fechar: ' : 'Abrir: ') + nome); };
    dobra.poe(false);
    return { raiz: raiz, foco: titulo, dobra: dobra };
  }

  function abaVeiculos(contexto) {
    var apoio = contexto.apoio;
    var mapa = contexto.mapa;
    var fichas = Object.create(null);
    var raiz = cria('div', 'aba');
    poe(raiz, cria('h2', 'so-leitor', T.regua.abas.veiculos));
    if (ehObjeto(mapa)) {
      /* rascunho enquanto revisado_em não traz uma data; depois, a data */
      poe(raiz, apoio.mapaRascunho ? aviso({ rotulo: T.regua.rascunho[0], texto: T.regua.rascunho[1] })
        : cria('p', 'secao__intro', [T.regua.revisado, tempo(mapa.revisado_em, true), '.']));
    }
    poe(raiz, cria('p', 'secao__intro', T.regua.ladoEFatos));
    var veiculos = lista(ehObjeto(mapa) ? mapa.veiculos : null).filter(ehObjeto);
    if (!veiculos.length) {
      poe(raiz, fraseVazia(T.travessao));
      return abaSemLista(raiz);
    }

    var tipos = Object.keys(ROTULOS.tipoVeiculo);
    var validos = { lado: apoio.ordemPartidos.filter(ehId), fatos: CONFIANCAS, tipo: tipos };
    if (!validos.lado.length) {
      veiculos.forEach(function (veiculo) { if (ehId(veiculo.lado) && validos.lado.indexOf(veiculo.lado) === -1) { validos.lado.push(veiculo.lado); } });
    }
    var recorte;
    var pecas = filtrosDaAba(T.regua.buscarVeiculo, [
      { nome: 'lado', rotulo: 'Filtrar por lado', primeira: T.regua.todosLados, opcoes: opcoesDe(validos.lado, function (id) { return nomeDoPartido(apoio, id); }) },
      { nome: 'fatos', rotulo: 'Filtrar por ' + T.regua.confiabilidade, primeira: T.regua.qualquerConfiabilidade,
        opcoes: opcoesDe(CONFIANCAS, function (valor) { return rotulo('confianca', valor); }) },
      { nome: 'tipo', rotulo: 'Filtrar por tipo', primeira: T.regua.todosTipos, opcoes: opcoesDe(tipos, function (valor) { return rotulo('tipoVeiculo', valor); }) }
    ], function (nome, valor) { recorte.muda(nome, valor); }, function () { recorte.limpa(true); });

    /* um grupo por lado, na ordem da régua; lado que ela não conhece fica no fim */
    var ordem = apoio.ordemPartidos.slice();
    veiculos.forEach(function (veiculo) {
      if (ordem.indexOf(texto(veiculo.lado)) === -1) { ordem.push(texto(veiculo.lado)); }
    });
    var itens = [];
    var grupos = [];
    var caixaDosGrupos = cria('div', 'grupos');
    caixaDosGrupos.setAttribute('aria-busy', 'true');
    ordem.forEach(function (lado) {
      var doLado = veiculos.filter(function (veiculo) { return texto(veiculo.lado) === lado; });
      if (!doLado.length) { return; }
      var caixaDasLinhas = cria('div', '');
      var grupo = {
        visiveis: 0,
        linhas: caixaDasLinhas,
        raiz: cria('section', 'grupo', [
          cria('h3', 'grupo__titulo', busca(apoio.partidos, lado)
            ? [siglaDoPartido(apoio, lado), cria('span', '', nomeDoPartido(apoio, lado)), cria('span', 'texto-3', '(' + doLado.length + ')')]
            : [cria('span', 'id-cru', lado), cria('span', 'texto-3', '(' + doLado.length + ')')]),
          caixaDasLinhas
        ])
      };
      grupos.push(grupo);
      poe(caixaDosGrupos, grupo.raiz);
      doLado.forEach(function (veiculo) {
        itens.push({
          dado: veiculo,
          chaves: { lado: veiculo.lado, fatos: veiculo.fatos, tipo: veiculo.tipo },
          busca: semAcento(veiculo.nome) + ' ' + semAcento(veiculo.id),
          grupo: grupo,
          passa: true,
          linha: null
        });
      });
    });
    recorte = recorteDaRegua({
      aba: 'veiculos', plural: 'veículos', itens: itens, grupos: grupos, validos: validos,
      campos: pecas.campos, contagem: pecas.contagem, vazio: pecas.vazio, textoVazio: pecas.textoVazio
    });
    poe(raiz, pecas.fileira, caixaDosGrupos, pecas.vazio);

    function destino(rota, focar) {
      var ficha = rota.ficha ? busca(fichas, rota.ficha) : null;
      /* a ficha pedida pelo endereço nunca fica escondida por filtro */
      if (ficha && !ficha.item.passa) { recorte.limpa(false); }
      destinoDaRegua(rota, ficha, focar);
    }
    var aba = {
      raiz: raiz,
      pronta: false,
      aplica: function (rota, focar) {
        recorte.poe(recorte.daConsulta(rota.consulta), false);
        destino(rota, focar);
      },
      /* São muitas linhas: a lista é montada em fatias, com uma volta ao
         navegador entre elas, para a página não travar. Os filtros já valem
         desde a primeira fatia; o destino da rota espera a última. */
      inicia: function (rota) {
        var fila = itens.slice();
        recorte.poe(recorte.daConsulta(rota.consulta), false);
        function fatia() {
          if (contexto.pedido !== estado.pedido) { return; }   /* a vista mudou no meio */
          for (var n = 0; n < VEICULOS_POR_FATIA && fila.length; n += 1) {
            var item = fila.shift();
            item.linha = linhaDeVeiculo(contexto, item.dado);
            var id = item.dado.id;
            if (ehId(id) && !(id in fichas)) {
              item.linha.raiz.setAttribute('id', 'veiculo-' + id);
              fichas[id] = { foco: item.linha.foco, dobra: item.linha.dobra, item: item };
            }
            recorte.mostra(item);
            poe(item.grupo.linhas, item.linha.raiz);
          }
          if (fila.length) {
            janela.setTimeout(fatia, 0);
            return;
          }
          caixaDosGrupos.removeAttribute('aria-busy');
          aba.pronta = true;
          destino(rota, false);
        }
        fatia();
      }
    };
    return aba;
  }

  /* ----- aba Vetores ----- */

  function abaVetores(contexto) {
    var apoio = contexto.apoio;
    var arquivo = contexto.arquivoDeVetores;
    var raiz = cria('div', 'aba');
    poe(raiz, cria('h2', 'subtitulo', T.regua.registro), cria('p', 'secao__intro', T.regua.soCresce));
    if (ehObjeto(arquivo) && texto(arquivo.regra)) { poe(raiz, cria('p', 'secao__intro', texto(arquivo.regra))); }
    /* entrada de anulação não vira linha: ela risca a linha do vetor que desfaz */
    var vetores = maisNovosPrimeiro(apoio.registro.filter(function (entrada) { return !ehAnulacao(entrada); }));
    if (!vetores.length) {
      poe(raiz, fraseVazia(T.regua.semVetores));
      return abaSemLista(raiz);
    }
    var colunas = [T.arquivo.data, T.regua.player, T.regua.de, T.regua.para, T.regua.forca, T.arquivo.tema,
      T.regua.porQue, T.regua.prova, T.regua.item];
    var tabelaDoRegistro = tabela(T.regua.registro, colunas, [], { classe: 'tabela--larga', legendaEscondida: true });
    var corpoDaTabela = tabelaDoRegistro.getElementsByTagName('tbody')[0];
    var contagem = cria('p', 'filtros__contagem');
    var limpar = botao(T.radar.limpar, '', function () { poeFiltro('', true); });
    var mais = botao(T.regua.mais50, '', function () { mostraAte(naTela + VETORES_POR_VEZ, true); });
    var filtro = '';        /* id do player, ou vazio */
    var naTela = 0;
    var fichas = Object.create(null);

    /* o filtro só aceita player que existe: na régua ou no próprio registro */
    function playerValido(id) {
      return ehId(id) && (!!busca(apoio.players, id) || vetores.some(function (entrada) { return entrada.player === id; }));
    }

    function quePassam() {
      return filtro ? vetores.filter(function (entrada) { return entrada.player === filtro; }) : vetores;
    }

    /* Uma linha da tabela. Anulado: a linha e o porquê ficam riscados; a
       etiqueta ANULADO e o motivo, não. */
    function linhaDeVetorNaTabela(entrada) {
      var anulacao = anulacaoDe(apoio, entrada.id);
      var player = busca(apoio.players, entrada.player);
      function risca(conteudo) { return cria('span', anulacao ? 'vetor__riscado' : '', conteudo); }
      var marcas = [anulacao ? etiqueta(T.itens.anulado) : null, entrada.conflito_de_interesse === true ? etiqueta(T.itens.conflito) : null];
      var linha = linhaDeTabela(colunas, [
        [anulacao ? soLeitor('Anulado: ') : null, risca(tempo(entrada.data, true))],
        risca(player && ehId(entrada.player) ? linkInterno(hashRegua('players', entrada.player), texto(player.nome) || entrada.player)
          : cria('span', 'id-cru', texto(entrada.player))),
        risca(siglaDoPartido(apoio, entrada.de)),
        risca(siglaDoPartido(apoio, entrada.para)),
        risca(forca(apoio, entrada.forca)),
        risca(etiquetaDeTema(apoio, entrada.tema)),
        { longa: true, conteudo: [risca(texto(entrada.porque)), marcas[0] || marcas[1] ? cria('span', 'marcas', marcas) : null,
          anulacao ? linhaDaAnulacao(anulacao) : null] },
        linkExterno(entrada.url, T.itens.prova),
        itemDoRegistro(contexto, entrada) || T.travessao
      ]);
      if (anulacao) { linha.classList.add('vetor--anulado'); }
      if (ehId(entrada.id) && !(entrada.id in fichas)) {
        /* o id do vetor é a âncora da linha */
        linha.setAttribute('id', 'vetor-' + entrada.id);
        linha.firstChild.setAttribute('tabindex', '-1');
        fichas[entrada.id] = { foco: linha.firstChild };
      }
      return linha;
    }

    /* Mostra as primeiras "quantas" linhas do recorte. As que já estão na
       tela ficam como estão: só entram as novas. */
    function mostraAte(quantas, porLeitor) {
      var passam = quePassam();
      var alvo = Math.min(quantas, passam.length);
      for (var i = naTela; i < alvo; i += 1) { poe(corpoDaTabela, linhaDeVetorNaTabela(passam[i])); }
      naTela = Math.max(naTela, alvo);
      var quantos = naTela + ' de ' + vetores.length + ' vetores';
      troca(contagem, quantos);
      esconde(mais, naTela >= passam.length);
      esconde(limpar, filtro === '');
      esconde(tabelaDoRegistro, naTela === 0);
      if (porLeitor) { anuncia(quantos); }
    }

    /* Troca o filtro de player e recomeça da primeira página. */
    function poeFiltro(id, porLeitor) {
      filtro = playerValido(id) ? id : '';
      limpa(corpoDaTabela);
      fichas = Object.create(null);
      naTela = 0;
      mostraAte(VETORES_POR_VEZ, porLeitor);
      if (porLeitor) {
        var hash = hashRegua('vetores') + consultaDe({ player: filtro }, PARAMETROS.vetores);
        gravaEndereco(hash);
        estado.rota = interpretaRota(hash);
      }
    }

    function aplica(rota, focar) {
      var pedida = rota.ficha ? vetores.filter(function (entrada) { return entrada.id === rota.ficha; })[0] : null;
      var doEndereco = rota.consulta ? rota.consulta.player : '';
      /* a linha pedida pelo endereço nunca fica escondida por filtro */
      poeFiltro(pedida && playerValido(doEndereco) && pedida.player !== doEndereco ? '' : doEndereco, false);
      if (pedida) { mostraAte(Math.ceil((quePassam().indexOf(pedida) + 1) / VETORES_POR_VEZ) * VETORES_POR_VEZ, false); }
      destinoDaRegua(rota, pedida ? busca(fichas, rota.ficha) : null, focar);
    }

    poe(raiz, cria('div', 'filtros', [contagem, limpar]), tabelaDoRegistro, cria('p', 'aba__mais', mais));
    return { raiz: raiz, pronta: true, aplica: aplica, inicia: function (rota) { aplica(rota, false); } };
  }

  /* ======================================================================
     19. Método (#/metodo e #/metodo/{seção})
     Os textos são fixos; as tabelas vêm da régua e do catálogo.
     ====================================================================== */

  function abreMetodo(rota, primeira) {
    var corpo = abreVistaSimples('metodo', primeira);
    var pedido = estado.pedido;
    esperaDados(corpo);
    var caminhos = [ARQ_REGUA, ARQ_CATALOGO, ARQ_PLAYERS];
    /* o índice entra só para o aviso de edição nova saber o que já foi lido */
    return leParaVista(caminhos.concat([ARQ_INDICE])).then(function (lidos) {
      montaComRede(pedido, corpo, ARQ_REGUA, function () {
        montaMetodo(corpo, rota, lidos, faltasEFormatos(caminhos, lidos));
      });
    });
  }

  function montaMetodo(corpo, rota, lidos, situacao) {
    var contexto = {
      apoio: montaApoio(lidos[0], lidos[2], null, null, lidos[1]),
      catalogo: lidos[1],
      situacao: situacao
    };
    var partes = [
      ['conflito', '01', metodoConflito], ['perguntas', '02', metodoPerguntas], ['regua', '03', metodoRegua],
      ['niveis', '04', metodoNiveis], ['indicadores', '05', metodoIndicadores], ['rotina', '06', metodoRotina],
      ['limites', '07', metodoLimites]
    ];
    var titulos = Object.create(null);
    partes.forEach(function (parte) {
      var s = secao(parte[0], parte[1], T.metodo.titulos[parte[0]], null);
      s.titulo.setAttribute('tabindex', '-1');
      titulos[parte[0]] = s.titulo;
      poe(s.corpo, parte[2](contexto));
      poe(corpo, s.raiz);
    });
    /* #/metodo/{seção}: rola até a seção e põe o foco no título dela */
    if (rota.secao && titulos[rota.secao]) { levaAte(titulos[rota.secao]); }
  }

  /* Os avisos de uma parte do Método: só dos arquivos que ela usa. */
  function avisosDoMetodo(contexto, arquivos) {
    function usa(arquivo) { return arquivos.indexOf(arquivo) !== -1; }
    var avisos = avisosDeArquivos(contexto.situacao.faltas.filter(usa), contexto.situacao.novos.filter(usa));
    return avisos.length ? cria('div', 'avisos', avisos) : null;
  }

  function quadro(titulo, conteudo) {
    return cria('div', 'quadro', [subtitulo(titulo), conteudo]);
  }

  function linhaDeQuadro(termo, explicacao) {
    /* sem a explicação (campo da régua que o validador não confere), só o termo */
    return cria('div', 'quadro__linha', [cria('p', 'quadro__termo', termo), explicacao ? cria('p', 'quadro__texto', explicacao) : null]);
  }

  /* 01: a caixa de conflito de interesse, no topo, e a lista que liga a marca. */
  function metodoConflito(contexto) {
    var apoio = contexto.apoio;
    var caixa = cria('div', 'caixa');
    T.metodo.conflito.forEach(function (paragrafo) { poe(caixa, cria('p', '', paragrafo)); });
    poe(caixa, cria('ol', 'lista lista--numerada', T.metodo.conflitoMedidas.map(function (medida) { return cria('li', '', medida); })));
    poe(caixa, cria('p', '', T.metodo.conflitoLimite));
    /* ficha que não existe no arquivo de players nunca vira link */
    poe(caixa, cria('p', '', busca(apoio.players, 'anthropic')
      ? linkInterno(hashRegua('players', 'anthropic'), T.metodo.verAnthropic) : T.metodo.verAnthropic));

    var conflito = ehObjeto(apoio.regua.conflito) ? apoio.regua.conflito : null;
    var linhas = [];
    if (conflito) {
      if (texto(conflito.regra)) { linhas.push(cria('p', 'quadro__texto', texto(conflito.regra))); }
      var nomes = [];
      lista(conflito.players).filter(ehTexto).forEach(function (id, i) {
        if (i > 0) { nomes.push(', '); }
        var player = busca(apoio.players, id);
        /* player que não está em players.json aparece pelo id */
        if (!player) { nomes.push(cria('span', 'id-cru', id)); return; }
        var nome = texto(player.nome) || id;
        nomes.push(ehId(id) ? linkInterno(hashRegua('players', id), nome) : cria('span', '', nome));
      });
      var termos = lista(conflito.termos).filter(ehTexto);
      linhas.push(cria('p', '', [cria('span', 'dossie__rotulo', T.metodo.listaPlayers), nomes.length ? nomes : T.travessao]),
        cria('p', '', [cria('span', 'dossie__rotulo', T.metodo.listaTermos), termos.length ? termos.join(', ') : T.travessao]));
    } else {
      linhas.push(fraseVazia(T.travessao));
    }
    return [caixa, avisosDoMetodo(contexto, [ARQ_REGUA, ARQ_PLAYERS]), quadro(T.metodo.lista, linhas)];
  }

  /* 02: as quatro perguntas. */
  function metodoPerguntas() {
    return cria('div', 'prosa', [
      cria('p', '', T.metodo.perguntasIntro),
      cria('ol', 'lista lista--numerada', T.metodo.perguntas.map(function (pergunta) { return cria('li', '', pergunta); }))
    ]);
  }

  /* 03: a régua, em um parágrafo, com o link para a vista. */
  function metodoRegua() {
    return cria('div', 'prosa', cria('p', '', [T.metodo.regua + ' ', linkInterno(hashRegua('partidos'), T.metodo.vejaRegua)]));
  }

  /* 04: os 5 níveis e, por domínio, a tabela de critérios. */
  function metodoNiveis(contexto) {
    var apoio = contexto.apoio;
    var regua = apoio.regua;
    var niveis = lista(regua.niveis_alerta).filter(ehObjeto);
    var partes = [cria('div', 'prosa', cria('p', '', T.metodo.niveis)), avisosDoMetodo(contexto, [ARQ_REGUA])];
    if (niveis.length) {
      partes.push(cria('div', 'niveis', niveis.map(function (nivel) {
        return cria('div', 'nivel-ficha', [
          cria('p', '', selo(apoio, nivel.nivel)),
          texto(nivel.significado) ? cria('p', 'nivel-ficha__texto', texto(nivel.significado)) : null,
          cria('p', 'nivel-ficha__texto texto-2', [cria('span', 'rotulo', T.metodo.provaMinima), ' ', texto(nivel.prova_minima) || T.travessao])
        ]);
      })));
    }

    /* gatilho de preço: o texto e, abaixo, o indicador, a janela e a alta mínima */
    function precoDoCriterio(preco) {
      var detalhe = [texto(preco.indicador), rotulo('janela', preco.janela),
        ehNumero(preco.alta_minima_pct) ? numeroBr(preco.alta_minima_pct, 0, 2) + T.metodo.ouMais : '']
        .filter(function (parte) { return parte !== ''; }).join(T.separador);
      return cria('li', '', [cria('span', '', texto(preco.texto)), detalhe ? cria('span', 'criterio__detalhe', detalhe) : null]);
    }
    function linhaDoNivel(nivel, idDoDominio) {
      var criterio = ehObjeto(nivel.criterios) && tem(nivel.criterios, idDoDominio) && ehObjeto(nivel.criterios[idDoDominio])
        ? nivel.criterios[idDoDominio] : {};
      var eventos = lista(criterio.eventos).filter(ehTexto);
      var precos = lista(criterio.precos).filter(ehObjeto);
      return [
        cria('span', 'marcas', [selo(apoio, nivel.nivel), texto(criterio.codigo) ? cria('span', 'criterio__codigo', texto(criterio.codigo)) : null]),
        { longa: true, conteudo: eventos.length ? cria('ul', 'lista', eventos.map(function (evento) { return cria('li', '', evento); })) : T.travessao },
        { longa: true, conteudo: precos.length ? cria('ul', 'lista', precos.map(precoDoCriterio)) : T.travessao }
      ];
    }
    lista(regua.dominios).filter(ehObjeto).forEach(function (dominio) {
      var nome = texto(dominio.nome) || texto(dominio.id);
      partes.push(cria('h3', 'metodo__dominio', nome));
      if (texto(dominio.descricao)) { partes.push(cria('p', 'metodo__texto', texto(dominio.descricao))); }
      if (texto(dominio.canal)) {
        partes.push(cria('p', 'metodo__texto texto-2', [cria('span', 'rotulo', T.metodo.comoChega), ' ', texto(dominio.canal)]));
      }
      if (niveis.length) {
        partes.push(tabela(nome, [T.arquivo.nivel, T.metodo.eventos, T.metodo.precos],
          niveis.map(function (nivel) { return linhaDoNivel(nivel, dominio.id); }), { legendaEscondida: true, classe: 'tabela--criterios' }));
      }
    });
    return partes;
  }

  /* 05: o catálogo dos indicadores, com as fontes de cada número. */
  function metodoIndicadores(contexto) {
    var apoio = contexto.apoio;
    var catalogo = ehObjeto(contexto.catalogo) ? contexto.catalogo : {};
    var partes = [cria('div', 'prosa', cria('p', '', T.metodo.indicadores)), avisosDoMetodo(contexto, [ARQ_CATALOGO])];
    var indicadores = lista(catalogo.indicadores).filter(ehObjeto);
    if (indicadores.length) {
      partes.push(cria('div', 'catalogo', indicadores.map(function (indicador) {
        var faixa = ehObjeto(indicador.faixa) ? indicador.faixa : {};
        var casas = casasDoIndicador(apoio, indicador.id);
        var item = cria('article', 'catalogo__item', [
          cria('h3', 'catalogo__nome', texto(indicador.nome) || texto(indicador.id)),
          cria('p', 'marcas', [
            texto(indicador.unidade) ? cria('span', '', texto(indicador.unidade)) : null,
            indicador.dominio !== undefined ? (busca(apoio.dominios, indicador.dominio) ? etiqueta(nomeDoDominio(apoio, indicador.dominio))
              : cria('span', 'id-cru', texto(indicador.dominio))) : null,
            etiqueta(indicador.obrigatorio === true ? T.metodo.alimentaGatilho : T.metodo.soContexto),
            texto(indicador.frequencia) ? cria('span', 'texto-2', rotulo('frequencia', indicador.frequencia)) : null
          ]),
          cria('p', 'catalogo__meta', [
            ehNumero(faixa.min) && ehNumero(faixa.max)
              ? cria('span', '', T.metodo.faixa + numeroBr(faixa.min, 0, 4) + T.metodo.faixaAte + numeroBr(faixa.max, 0, 4)) : null,
            cria('span', '', T.metodo.casas + ': ' + (casas === null ? 2 : casas))
          ])
        ]);
        var fontes = lista(indicador.fontes).filter(ehObjeto);
        if (fontes.length) {
          poe(item, cria('ul', 'catalogo__fontes', fontes.map(function (fonte) {
            return cria('li', 'catalogo__fonte', [
              cria('p', 'marcas', [
                linkExterno(fonte.url, texto(fonte.nome) || T.vigiar.fonte),
                texto(fonte.leitor) ? cria('span', 'catalogo__leitor', [T.metodo.leitor + ' ', cria('span', 'mono', texto(fonte.leitor))]) : null,
                /* o fator só aparece quando existe e não é 1 */
                ehNumero(fonte.fator) && fonte.fator !== 1
                  ? cria('span', 'catalogo__leitor', T.metodo.convertido + numeroBr(fonte.fator, 0, 7)) : null
              ]),
              texto(fonte.nota) ? cria('p', 'texto-2', texto(fonte.nota)) : null
            ]);
          })));
        }
        return item;
      })));
    }
    if (texto(catalogo.regra) || ehData(catalogo.atualizado_em)) {
      partes.push(cria('p', 'aba__regra', [texto(catalogo.regra),
        ehData(catalogo.atualizado_em) ? [' Catálogo atualizado em ', tempo(catalogo.atualizado_em, true), '.'] : null]));
    }
    return partes;
  }

  /* 06: como a edição é feita, e os cinco quadros lidos da régua. */
  function metodoRotina(contexto) {
    var apoio = contexto.apoio;
    var regua = apoio.regua;
    var partes = [cria('div', 'prosa', T.metodo.rotina.map(function (paragrafo) { return cria('p', '', paragrafo); })),
      avisosDoMetodo(contexto, [ARQ_REGUA])];
    function ouTravessao(linhas) {
      return linhas.length ? linhas : fraseVazia(T.travessao);
    }

    partes.push(quadro(T.metodo.quadros.campos, ouTravessao(lista(regua.campos).filter(ehObjeto).map(function (campo) {
      return linhaDeQuadro([cria('strong', '', texto(campo.nome) || texto(campo.id)),
        lista(campo.partidos).map(function (id) { return siglaDoPartido(apoio, id); })], texto(campo.descricao));
    }))));

    partes.push(quadro(T.metodo.quadros.forca, ouTravessao(lista(regua.forcas).filter(ehObjeto).map(function (linha) {
      return linhaDeQuadro(forca(apoio, linha.forca), texto(linha.o_que_conta));
    }))));

    partes.push(quadro(T.metodo.quadros.evidencia, ouTravessao(lista(regua.evidencias).filter(ehObjeto).map(function (linha) {
      return linhaDeQuadro(etiqueta(rotulo('evidencia', linha.id)), texto(linha.o_que_conta));
    }))));

    var avanco = ehObjeto(regua.times_avanco) ? regua.times_avanco : {};
    var linhasDosTimes = ['manutencao', 'mudanca'].filter(function (id) { return tem(avanco, id) && texto(avanco[id]); }).map(function (id) {
      var time = busca(apoio.times, id);
      return linhaDeQuadro(time ? cria('strong', '', texto(time.nome) || id) : cria('span', 'id-cru', id), texto(avanco[id]));
    });
    if (texto(avanco.nao_move)) { linhasDosTimes.push(cria('p', 'quadro__texto texto-2', texto(avanco.nao_move))); }
    partes.push(quadro(T.metodo.quadros.times, ouTravessao(linhasDosTimes)));

    /* sufixos de site oficial: em mono, como texto. Nunca viram link. */
    var oficiais = ehObjeto(regua.sites_oficiais) ? regua.sites_oficiais : {};
    function sufixos(rotuloDaLista, itens) {
      var textos = lista(itens).filter(ehTexto);
      return cria('p', 'quadro__texto', [cria('span', 'dossie__rotulo', rotuloDaLista), ' ',
        textos.length ? cria('span', 'mono', textos.join(', ')) : T.travessao]);
    }
    partes.push(quadro(T.metodo.quadros.primaria, [
      texto(oficiais.regra) ? cria('p', 'quadro__texto', texto(oficiais.regra)) : null,
      sufixos(T.metodo.sitesBrasil, oficiais.brasil), sufixos(T.metodo.sitesOutros, oficiais.outros)
    ]));
    return partes;
  }

  /* 07: o aviso fixo, em caixa, e os limites. */
  function metodoLimites() {
    return [aviso({ texto: T.metodo.naoERecomendacao }), cria('div', 'prosa', cria('p', '', T.metodo.limites))];
  }

  /* ======================================================================
     20. Partida
     ====================================================================== */

  /* Lê o endereço e abre a vista. forcar: recarrega a edição mesmo que ela
     já esteja na tela ("Tentar de novo", edição nova). */
  function trataRota(forcar) {
    var rota = interpretaRota(janela.location.hash);
    if (rota.redireciona) { gravaEndereco(rota.redireciona); }
    var primeira = estado.primeiraRota;
    estado.primeiraRota = false;
    estado.rota = rota;
    tiraAvisosDeRota();
    if (rota.desconhecida) {
      mostraAvisoGeral('rota', aviso({ rotulo: T.avisos.rota[0], texto: T.avisos.rota[1] }));
    }
    if (rota.tipo === 'edicao') { return abreEdicao(rota, primeira, forcar === true); }
    if (rota.tipo === 'arquivo') { return abreArquivo(rota, primeira); }
    if (rota.tipo === 'regua') { return abreRegua(rota, primeira); }
    return abreMetodo(rota, primeira);
  }

  /* "Pular para o conteúdo" não pode virar rota: o endereço é do roteador. */
  function aoPular(evento) {
    evento.preventDefault();
    var conteudo = porId('conteudo');
    if (conteudo && typeof conteudo.focus === 'function') { conteudo.focus(); }
  }

  /* Clique num link interno cujo endereço já é o da página: o navegador não
     dispara hashchange, e o link pareceria morto. Refaz a rota à mão. */
  function aoClicar(evento) {
    if (evento.defaultPrevented || evento.ctrlKey || evento.metaKey || evento.shiftKey || evento.altKey) { return; }
    for (var no = evento.target; no && no !== doc; no = no.parentNode) {
      if (no.tagName && String(no.tagName).toLowerCase() === 'a') {
        var href = no.getAttribute('href');
        if (href && href.slice(0, 2) === '#/' && href === janela.location.hash) { trataRota(false); }
        return;
      }
    }
  }

  function inicia() {
    janela.addEventListener('hashchange', function () { trataRota(false); });
    doc.addEventListener('click', aoClicar);
    doc.addEventListener('keydown', aoTeclar);
    doc.addEventListener('visibilitychange', aoVoltarParaAba);
    var pular = porId('pular');
    if (pular) { pular.addEventListener('click', aoPular); }
    trataRota(false);
  }

  /* O único nome que o site põe no escopo global. Só leitura: serve aos
     testes e a quem quiser conferir uma conta no console. */
  janela.INFO = Object.freeze({
    interpretaRota: interpretaRota,
    enderecoSeguro: enderecoSeguro,
    dataCurta: dataCurta,
    dataLonga: dataLonga,
    numeroDoDia: numeroDoDia,
    dataDoNumero: dataDoNumero,
    horaDeBrasilia: horaDeBrasilia,
    idade: idade,
    variacao: variacao,
    comSinal: comSinal,
    valorDeIndicador: valorDeIndicador,
    rotulo: rotulo,
    semAcento: semAcento
  });

  if (doc.readyState === 'loading') {
    doc.addEventListener('DOMContentLoaded', inicia);
  } else {
    inicia();
  }
}(window));
