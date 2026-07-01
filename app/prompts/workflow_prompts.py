CMO_DIAGNOSIS_PROMPT = """Com base no Super Contexto fornecido (que contém minha base de conhecimento, histórico de postagens e o briefing da semana, caso exista), gere um Diagnóstico Estratégico para esta semana.

REGRAS DE AUTONOMIA E ESCOLHA DE PROJETOS:
1. O briefing da semana é OPCIONAL. Se houver um briefing com "Projeto em foco", siga-o estritamente.
2. SE NÃO HOUVER BRIEFING MENCIONANDO PROJETO ESPECÍFICO, assuma controle autônomo.
3. Leia OBRIGATORIAMENTE os arquivos de histórico (`historico-postagens.md` e logs) no Super Contexto para identificar o último projeto publicado.
4. ROTAÇÃO OBRIGATÓRIA: Evite repetir o projeto da semana anterior (ex: se o último foi Sentinela RJ, escolha outro projeto principal: Hermes Lite, sys-health, Pulso Eleitoral, Veritas Eleitoral ou TechPulse).
5. Escolha um *ângulo editorial novo* para o projeto selecionado, consultando `continuidade-conteudo.md`. NÃO repita o mesmo tema, título ou gancho da semana passada.
6. Use o BrandOS como tema central APENAS quando for explicitamente pedido no briefing. Caso contrário, ele é apenas bastidor.
7. Garanta diversidade editorial e siga as diretrizes em `regras-editoriais-por-projeto.md`.

REGRAS DE CIVIC TECH:
Ao falar de Civic Tech, contratos públicos, PNCP, eleições ou dados públicos: não fazer acusações; não sugerir irregularidades sem base; usar termos como sinais, padrões, análise, monitoramento e pontos de atenção; enfatizar revisão humana; deixar claro que IA apoia análise, não substitui julgamento; manter tom técnico e responsável; evitar partidarização e sensacionalismo.

O diagnóstico deve ser um documento Markdown estruturado contendo obrigatoriamente as seguintes seções:
1. **Último conteúdo publicado identificado:** (O que rodou na semana passada).
2. **Projeto escolhido para a nova semana:** (Qual projeto entrou em foco).
3. **Por que não repetir o projeto anterior:** (A justificativa de rotação baseada no histórico).
4. **Ângulo editorial escolhido:** (O novo ângulo, e o porquê de ele ser o momento certo agora).
5. **Justificativa da escolha:** (Como se conecta com portfólio, tecnologia, etc).
6. **O que evitar repetir:** (Ganchos ou abordagens já usados que o copywriter deve fugir).
7. **Tom de voz recomendado.**

Aqui está o contexto:
{context}
"""

STRATEGIST_PLAN_PROMPT = """Aqui está o Super Contexto e o Diagnóstico do CMO.
Super Contexto:
{context}

Diagnóstico do CMO:
{diagnosis}

Com base neles, crie um Plano Semanal detalhado contendo:
- Post 1 (Segunda-feira): Tema, objetivo e formato. (Regra: mais narrativo; conecta trajetória, transição ou visão; abre a semana com contexto humano).
- Post 2 (Quarta-feira): Tema, objetivo e formato. (Regra: mais técnico ou de bastidor; mostra projeto, stack, decisão técnica, problema ou aprendizado real).
- Post 3 (Sexta-feira): Tema, objetivo e formato. (Regra: mais reflexivo ou estratégico; conecta aprendizados, portfólio, mercado, Civic Tech, IA aplicada ou próximos passos).
- Carrossel da semana (Tema e objetivo).

REGRAS DE CONTINUIDADE E REPETIÇÃO:
1. Leia o histórico de postagens e NÃO REPITA os mesmos temas, ganchos ou conclusões.
2. Certifique-se de que o plano respeita a prioridade editorial dos projetos e a alternância de formatos (veja continuidade-conteudo.md).
3. Evite repetir a mesma mensagem nos três posts da semana. Eles devem ter funções diferentes.
"""

COPYWRITER_POST_PROMPT = """Aqui está o Super Contexto e o Plano Semanal.
Super Contexto:
{context}

Plano Semanal:
{plan}

Sua tarefa é escrever APENAS o conteúdo do {post_id}.
Lembre-se da função do post:
- Segunda-feira: narrativo, conecta trajetória, transição ou visão. Abre a semana com contexto humano.
- Quarta-feira: técnico ou de bastidor, mostra projeto, stack, decisão técnica, problema ou aprendizado real.
- Sexta-feira: reflexivo ou estratégico, conecta aprendizados, portfólio, mercado, Civic Tech, IA aplicada ou próximos passos.
Não repita a mesma mensagem dos outros dias.

REGRAS DE CIVIC TECH:
Ao falar de Civic Tech, contratos públicos, PNCP, eleições ou dados públicos: não fazer acusações; não sugerir irregularidades sem base; usar termos como sinais, padrões, análise, monitoramento e pontos de atenção; enfatizar revisão humana; deixar claro que IA apoia análise, não substitui julgamento; manter tom técnico e responsável; evitar partidarização e sensacionalismo.

O post deve ser envolvente, usar quebras de linha adequadas para o LinkedIn e ter um gancho forte na primeira linha.
Não use hashtags em excesso (máximo 3).
Escreva o texto completo do post.
"""

EDITOR_REVIEW_PROMPT = """Aqui está um rascunho de post escrito pelo Copywriter.
Post original:
{draft}

Contexto geral para alinhamento:
{context}

Sua missão principal é deixar o texto o mais humano, concreto e natural possível. 

Siga as seguintes regras OBRIGATÓRIAS de edição:
1. Remova travessões explicativos exagerados (ex: "minha marca — no LinkedIn — precisava...").
2. Evite texto excessivamente polido, simétrico ou institucional.
3. É PROIBIDO usar palavras e expressões de IA ou clichês corporativos. Remova ou substitua as seguintes expressões:
   - narrativa consistente
   - prova viva
   - oportunidades certas
   - transformar desafios em oportunidades
   - usar tecnologia a seu favor
   - jornada
   - maestro
   - reputação sólida e coerente
   - fluxo inteligente
   - crença
   - potencializar
   - estratégia poderosa
   - missão diária
   - conta uma história clara
   - cada linha de código tem um objetivo
   - diferenciais únicos
   - solução revolucionária
   - impacto transformador
4. Evite listas com bullets em posts curtos. Use bullets apenas quando eles realmente melhorarem a leitura.
5. Prefira frases mais naturais, linguagem simples e concreta, com ritmo humano.
6. Use quebras de linha curtas, mas sem parecer fórmula engessada de copywriting.
7. Mantenha o tom: humano, direto, maduro, honesto, prático, sem ser guru, sem exagero, e SEM cara de IA.
8. Nem todo post precisa terminar com pergunta. Quando a pergunta final parecer genérica ou forçada, substitua por uma frase forte ou uma conclusão simples.
9. NUNCA use hashtags com acento (use #TransicaoDeCarreira em vez de #TransiçãoDeCarreira).

REGRAS DE CTA:
Nem todo post precisa de CTA em forma de pergunta.
Quando houver CTA, ele deve parecer natural e específico.
Evitar CTAs genéricos como: "E você, como usa tecnologia a seu favor?", "Qual sua ferramenta favorita?", "O que você acha?", "Você concorda?".
Preferir CTAs como: "Você também já sentiu que sua presença profissional precisava de mais método e menos improviso?", "Para quem está em transição, contexto faz muita diferença.", "Ainda está no começo, mas esse tipo de projeto tem me ensinado muito.", "Esse é o tipo de aprendizado que quero documentar melhor daqui para frente."

ANTES DE FINALIZAR, faça a seguinte avaliação mental OBRIGATÓRIA:
"Isso parece escrito por Leandro ou parece texto de IA?"
Se o post parecer artificial, institucional ou com cara de IA, NÃO FAÇA APENAS PEQUENOS AJUSTES. REESCREVA O TEXTO INTEIRO DO ZERO.

Retorne APENAS o texto revisado e formatado (sem comentários adicionais ou explicações sobre o que você mudou).
"""

DESIGNER_CAROUSEL_PROMPT = """Com base no Plano Semanal, crie o roteiro do Carrossel da semana.
Plano Semanal:
{plan}

Estruture slide a slide:
- Slide 1 (Capa): Título impactante.
- Slide 2-X (Conteúdo): Tópicos com texto curto.
- Slide Final (CTA): Chamada para ação.
"""

DESIGNER_IMAGE_PROMPTS_PROMPT = """Gere 3 ideias de imagens para acompanhar os posts desta semana (com base no plano semanal).
Plano Semanal:
{plan}

Para cada imagem, forneça:
1. Objetivo da imagem.
2. Prompt detalhado em inglês (para ser usado no Midjourney ou DALL-E).
"""

NETWORKING_PLAN_PROMPT = """Com base no Super Contexto e na estratégia da semana, crie um plano de networking focado.
Super Contexto:
{context}

Liste:
1. 3 tipos de perfis ou empresas que devo interagir esta semana.
2. Sugestão de comentários de alto valor (como contribuir nas discussões).
3. 1 ou 2 ações para reativar conexões antigas.
"""

CHECKLIST_TEMPLATE = """# Checklist de Publicação da Semana

## Antes de publicar
- [ ] Revisar os textos gerados pelo Editor.
- [ ] Verificar se os links (ex: GitHub, portfólio) estão corretos.
- [ ] Criar ou separar as imagens/carrossel sugeridos.

## Publicação
- [ ] Agendar/Publicar Post 1 (Segunda)
- [ ] Agendar/Publicar Post 2 (Quarta)
- [ ] Agendar/Publicar Post 3 (Sexta)
- [ ] Publicar Carrossel

## Pós-publicação
- [ ] Responder aos primeiros comentários nos primeiros 30 minutos.
- [ ] Executar ações do plano de networking.
"""

PUBLISHER_COMMENT_PROMPT = """Aqui está o Super Contexto (que contém os links oficiais) e o Plano Semanal.
Super Contexto:
{context}

Plano Semanal:
{plan}

Sua tarefa é redigir o **primeiro comentário** sugerido para CADA UM dos posts da semana (Post 1, Post 2, Post 3 e Carrossel).
Regras obrigatórias:
1. Verifique na seção "Links Oficiais dos Projetos" dentro do Super Contexto se há link de GitHub ou Site/Demo para o projeto em foco na semana.
2. Se houver e for relevante para o post, crie um comentário curto, profissional e direto contendo os links. Ex: "Repositório do projeto: [link]".
3. Se o link não estiver listado (ou constar "link não cadastrado"), escreva EXATAMENTE: "link não cadastrado".
4. NÃO INVENTE links.
5. Não peça curtida, comentário ou engajamento artificial. Não soe como venda.

Retorne um documento Markdown com os comentários divididos por post (ex: ## Post 1, ## Post 2, etc).
"""

PUBLISHER_INSTRUCTIONS_PROMPT = """Aqui está o Super Contexto, o Plano Semanal e os Comentários gerados.
Super Contexto:
{context}

Plano Semanal:
{plan}

Comentários Sugeridos:
{comments}

Sua tarefa é compilar as instruções finais de publicação para TODOS os posts da semana.
Retorne um documento Markdown estruturado. Para CADA POST (Post 1, Post 2, Post 3 e Carrossel), forneça as seguintes seções:

### [Nome do Post]
1. **Título breve para o PDF/Carrossel** (Se o formato não incluir PDF/Carrossel, escreva "N/A").
2. **Hashtags** (Sugira até 3 hashtags focadas, sem acento).
3. **Instrução de Links** (Indicação CLARA de que os links devem ir no primeiro comentário, e não no corpo principal).

No final do arquivo, adicione um **Checklist geral antes de publicar** (3 bullets rápidos para garantir a revisão humana final).
"""
