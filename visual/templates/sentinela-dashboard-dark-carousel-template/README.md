# Template — Sentinela RJ Dashboard Dark Carousel

Template HTML/CSS reutilizável do carrossel aprovado para LinkedIn.
Mantém o design exatamente como aprovado (fundo escuro, imagem de
dashboard como base, kicker em ciano, título/corpo, paginação e rodapé).

## Estrutura de pastas

```
sentinela-dashboard-dark-carousel-template/
├── sentinela-dashboard-dark-carousel-template.html   ← abrir este arquivo no navegador
├── css/
│   └── template.css        ← todo o visual (cores, tipografia, espaçamento)
├── js/
│   ├── config.js           ← ÚNICO arquivo que você precisa editar
│   └── render.js           ← monta os slides a partir de config.js (não editar)
├── assets/
│   └── images/
│       ├── slide-1.png ... slide-7.png   ← imagens de cada slide
└── README.md                ← este arquivo
```

## Como reutilizar (passo a passo)

1. **Troque as imagens.**
   Substitua os arquivos dentro de `assets/images/` mantendo os mesmos
   nomes (`slide-1.png`, `slide-2.png`, ...) — ou use nomes novos e
   atualize o campo `image` de cada slide em `js/config.js`.
   Recomendado: imagens 4:3 (proporção 1448×1086 px ou múltiplo dela),
   fundo escuro, com espaço negativo à esquerda ou abaixo para o texto
   não colidir com a arte.

2. **Edite `js/config.js`.**
   É o único arquivo de conteúdo. Nele você troca:
   - `projectName` — nome do projeto (aparece no rodapé)
   - `footerLabel` — texto fixo do rodapé (ex.: seu domínio)
   - `date` — data opcional no rodapé (deixe `""` para omitir)
   - `title` / `subtitle` — título e subtítulo do carrossel (usados na capa, slide 1)
   - `slides` — array com os 7 slides (kicker, texto, imagem, variações)

3. **Abra `sentinela-dashboard-dark-carousel-template.html` no navegador**
   para conferir o resultado. Cada slide aparece em sequência vertical,
   um abaixo do outro, na proporção 4:3 exata.

4. **Exporte para PDF/imagem** (o template é só a peça visual — a
   exportação final você faz por fora):
   - **Opção simples:** no navegador, `Ctrl/Cmd + P` → "Salvar como PDF"
     → em "Mais configurações", defina layout paisagem e tamanho de
     papel personalizado próximo de 4:3 (ex.: 14.48in × 10.86in). A
     folha de estilos já tem uma regra `@media print` que separa cada
     slide em uma página.
   - **Opção avançada (mais fiel):** use um script headless (Puppeteer
     ou Playwright) para tirar um screenshot de cada `.slide`
     individualmente, na resolução nativa 1448×1086px, e depois junte
     as imagens num PDF sem perda (evite reexportar como JPEG — foi
     isso que causou os artefatos de texto na versão anterior deste
     carrossel).

## Campos de cada slide (`js/config.js`)

| Campo          | Obrigatório | Descrição                                                                 |
|----------------|-------------|----------------------------------------------------------------------------|
| `number`       | sim         | "01" a "07" — usado na paginação                                          |
| `image`        | sim         | caminho da imagem (relativo à raiz do template)                           |
| `kicker`       | não         | rótulo curto no topo (maiúsculo), some se omitido                         |
| `isCover`      | só slide 1  | `true` usa `title`/`subtitle` do topo do config em vez de `body`          |
| `body`         | sim (exceto capa) | texto principal do slide. Use `\n` para quebra de linha manual       |
| `textPosition` | não         | `"bottom"` quando a imagem tem um elemento visual centralizado (ex.: diagrama de processo) que não deixa espaço à esquerda |
| `backdrop`     | não         | `true` ativa um cartão translúcido atrás do texto, para imagens com elementos visuais muito próximos da coluna de texto |

## Correção aplicada (histórico)

Numa versão anterior, a página abria mas ficava só com o fundo escuro,
sem nenhum slide. Causa: `config.js` declarava
`const CAROUSEL_CONFIG = {...}`. Em um `<script>` comum (sem
`type="module"`), uma declaração `const`/`let` no nível mais alto do
arquivo cria uma variável de escopo global, **mas não vira uma
propriedade de `window`**. Como `render.js` lê `window.CAROUSEL_CONFIG`,
o valor aparecia como `undefined` e o script saía silenciosamente.

Correção: `config.js` agora usa `window.CAROUSEL_CONFIG = {...}`
explicitamente. Além disso, `render.js` agora:
- roda depois de `DOMContentLoaded`;
- loga no console se encontrou o config e o container;
- mostra um erro visível no topo da página (faixa vermelha) se o
  container `#carousel-viewport` ou o `window.CAROUSEL_CONFIG` não
  existirem — nunca falha silenciosamente.

Se algum dia você customizar `config.js` e a página voltar a ficar em
branco, confira primeiro se a linha inicial continua sendo
`window.CAROUSEL_CONFIG = {` (não `const CAROUSEL_CONFIG = {`).

## Correção de impressão (histórico)

Depois da primeira versão, o preview de impressão estava saindo com 8
páginas em vez de 7, e o título da capa quebrava em 3 linhas em vez de 2.
Duas causas, corrigidas em `css/template.css`:

1. **Faltava uma regra `@page`.** Sem ela, o navegador usa o tamanho
   padrão (Letter, retrato), e o conteúdo em paisagem 4:3 transborda
   para páginas extras. Agora `@page { size: 1448px 1086px; margin: 0; }`
   define o tamanho exato do slide como tamanho de página.
2. **`page-break-after: always` estava em TODOS os slides, inclusive o
   último.** Isso cria uma página em branco depois do slide 7. A regra
   agora usa `.slide:not(:last-of-type)`, que quebra depois de cada
   slide exceto o último.
3. **`body` ainda tinha `padding: 40px 0` sobrando do preview em tela**,
   que somava altura extra ao documento impresso. Zerado em `@media print`.
4. **Título da capa quebrando errado:** `.slide__title` usava
   `white-space: pre-line`, que respeita `\n` mas ainda pode quebrar
   automaticamente uma linha longa demais para a coluna de texto. Como
   a coluna é estreita (54% do slide, pensada para não brigar com a
   arte à direita), a segunda linha do título ("falta de dado
   público.") ficava larga demais e quebrava de novo. Trocado para
   `white-space: pre`, que respeita só as quebras manuais do
   `config.js` e nunca quebra sozinho.

Testado com Playwright + Chromium real: resultado final é sempre
exatamente 7 páginas, 1448×1086px (4:3), com o título da capa em 2
linhas.

## O que NÃO editar

- `js/render.js` — lógica de montagem, não tem conteúdo para trocar.
- `css/template.css` — define a identidade visual aprovada. Só mexa
  aqui se for *intencionalmente* propor uma mudança de design (fora do
  escopo deste template).

## Observações de design (não alterar sem aprovação)

- Paleta: fundo azul-marinho escuro, branco, cinza-claro (`#C6CEDB`),
  detalhe ciano (`#56D1E8`) — sem robôs, sirenes, martelo de juiz,
  dinheiro ou qualquer elemento acusatório/sensacionalista.
- Tipografia: Inter (Regular/Medium/SemiBold/Bold).
- Canvas fixo em 1448×1086px (4:3 exato), replicando a versão aprovada
  gerada originalmente em Python/Pillow.
- Paginação simplificada: apenas texto "01 / 07" (sem bolinhas).
- Rodapé: `leandro.dev · Sentinela RJ` (separador desenhado como
  elemento visual, não como caractere de fonte).
