/* ==========================================================================
   Sentinela RJ — Dashboard Dark Carousel Template
   ARQUIVO DE CONTEÚDO — edite APENAS este arquivo para reutilizar o template.

   Não é necessário mexer em template.html nem em render.js para trocar
   textos, imagens, data, rodapé ou nome do projeto.
   ========================================================================== */

// IMPORTANTE: usamos "window.CAROUSEL_CONFIG =" (não "const CAROUSEL_CONFIG =")
// de propósito. Uma declaração `const`/`let` no topo de um script comum
// (sem type="module") cria uma variável de escopo global, mas ELA NÃO
// vira uma propriedade de `window`. Como render.js lê
// `window.CAROUSEL_CONFIG`, um `const` aqui deixaria a página em branco
// silenciosamente. Atribuir direto em `window` garante que o valor
// realmente fique acessível para render.js.
window.CAROUSEL_CONFIG = {

  // Nome do projeto/marca. Aparece no rodapé de todos os slides.
  projectName: "Sentinela RJ",

  // Texto fixo à esquerda do rodapé (ex.: seu domínio ou handle).
  footerLabel: "leandro.dev",

  // Data opcional. Se preenchida, aparece no rodapé junto do projeto.
  // Deixe como "" (string vazia) para omitir.
  date: "",

  // Título e subtítulo do carrossel — usados na capa (slide 1).
  title: "O problema não é\nfalta de dado público.",
  subtitle: "É falta de análise.",

  // Total de slides. Mantenha igual ao tamanho do array abaixo.
  totalSlides: 7,

  // --------------------------------------------------------------------
  // Slides. Cada item representa um slide do carrossel.
  //
  // Campos disponíveis:
  //   number       "01" a "07" — usado na paginação e no nome do arquivo
  //   image        caminho da imagem (relativo à pasta assets/images)
  //   kicker       rótulo curto no topo do slide (maiúsculo, opcional)
  //   isCover      true apenas no slide 1: usa `title` + `subtitle` do
  //                objeto CAROUSEL_CONFIG acima, em vez de `body`
  //   body         texto principal do slide (ignorado se isCover: true)
  //   textPosition "left" (padrão) ou "bottom" — usar "bottom" quando a
  //                imagem tiver um elemento visual centralizado que não
  //                deixa espaço à esquerda (ex.: diagramas de processo)
  //   backdrop     true/false — ativa um cartão translúcido atrás do
  //                texto, para imagens com elementos visuais muito
  //                próximos da coluna de texto
  // --------------------------------------------------------------------
  slides: [
    {
      number: "01",
      image: "assets/images/slide-1.png",
      kicker: "SENTINELA RJ",
      isCover: true,
    },
    {
      number: "02",
      image: "assets/images/slide-2.png",
      kicker: "A INFORMAÇÃO EXISTE",
      body: "Contrato público vira PDF, planilha e portal\ndisperso. A informação existe, mas acompanhar\nisso de verdade ainda é difícil.",
    },
    {
      number: "03",
      image: "assets/images/slide-3.png",
      kicker: "ONDE ENTRA O SENTINELA RJ",
      body: "É esse o problema que o Sentinela RJ tenta\nenfrentar. Um projeto meu, construído a partir\nde dados do PNCP.",
      backdrop: true,
    },
    {
      number: "04",
      image: "assets/images/slide-4.png",
      kicker: "PRIMEIRO, ORGANIZAR OS DADOS",
      body: "O primeiro passo é usar Python para coletar,\norganizar e estruturar os dados. É um trabalho\nde detalhe. Cada campo importa.",
      textPosition: "bottom",
    },
    {
      number: "05",
      image: "assets/images/slide-5.png",
      kicker: "A IA ENTRA COMO APOIO",
      body: "Depois entra a IA. Não para acusar ou decidir,\nmas para ajudar a encontrar sinais e padrões\nque podem passar batido.",
    },
    {
      number: "06",
      image: "assets/images/slide-6.png",
      kicker: "A DECISÃO CONTINUA HUMANA",
      body: "A tecnologia ajuda a olhar melhor. Mas a\ninterpretação continua sendo humana. No\nprojeto, isso não é detalhe. É regra.",
    },
    {
      number: "07",
      image: "assets/images/slide-7.png",
      kicker: "AINDA ESTÁ NO COMEÇO",
      body: "Ainda está no começo, mas o Sentinela RJ já\ntem me ensinado muito sobre dados públicos,\nanálise e Civic Tech.\n\nSigo documentando essa construção por aqui.",
    },
  ],
};
