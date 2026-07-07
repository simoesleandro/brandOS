# BrandOS — Roadmap

## 1. Objetivo deste documento

Este documento define a ordem de evolução do BrandOS.

O objetivo é evitar que o projeto cresça de forma confusa.

Cada versão deve entregar valor real, mantendo o foco principal:

> Ajudar Leandro Simões a construir networking, autoridade, portfólio e oportunidades profissionais por meio de uma agência de marketing pessoal com IA.

---

# 2. Princípio do roadmap

O BrandOS deve evoluir por versões pequenas.

Não tentar construir tudo de uma vez.

A ordem correta é:

1. Fazer funcionar.
2. Melhorar a qualidade.
3. Automatizar com segurança.
4. Criar interface.
5. Transformar em portfólio forte.
6. Avaliar produto reutilizável.

---

# 3. Versão v0.1 — MVP funcional

## Objetivo

Criar a primeira versão local do BrandOS, capaz de gerar uma semana de conteúdo para LinkedIn a partir de arquivos Markdown e um briefing semanal.

## Resultado esperado

Leandro roda:

```text
python app/main.py weekly
```

E o sistema gera:

```text
data/generated/YYYY-MM-DD-semana-brandos/
```

Com:

```text
01-diagnostico-cmo.md
02-plano-semanal.md
03-post-segunda.md
04-post-quarta.md
05-post-sexta.md
06-carrossel.md
07-prompts-imagem.md
08-plano-networking.md
09-checklist-publicacao.md
```

## Funcionalidades

* Ler arquivos Markdown de conhecimento.
* Ler briefing da semana.
* Montar contexto.
* Chamar API de IA.
* Rodar fluxo com agentes.
* Gerar 3 posts.
* Gerar 1 carrossel.
* Gerar prompts de imagem.
* Gerar plano de networking.
* Gerar checklist.
* Salvar tudo em Markdown.

## Agentes envolvidos

* CMO
* Content Strategist
* Copywriter
* Editor
* Designer
* Networking

## Fora do escopo

* LinkedIn API.
* Publicação automática.
* Dashboard.
* Banco de dados.
* Interface web.
* Geração de vídeo.
* Canva API.

## Critério de conclusão

A versão v0.1 estará pronta quando:

* o comando `weekly` rodar sem erro;
* os arquivos forem gerados corretamente;
* os posts forem coerentes com o posicionamento;
* o README explicar como configurar e rodar;
* a chave de API não estiver exposta;
* Leandro conseguir revisar e publicar manualmente os posts.

---

# 4. Versão v0.2 — Qualidade editorial

## Objetivo

Melhorar a qualidade dos conteúdos gerados.

A v0.1 faz funcionar.
A v0.2 deixa melhor.

## Funcionalidades

* Melhorar prompts dos agentes.
* Criar variações de ganchos.
* Criar variações de CTA.
* Criar versão curta e média dos posts.
* Criar classificação de tom.
* Criar score editorial antes da publicação.
* Melhorar etapa do Editor.
* Adicionar comando para post único.

## Comando novo

```text
python app/main.py post
```

## Entrada esperada

```text
data/inbox/ideia-post.md
```

## Saída esperada

```text
data/generated/YYYY-MM-DD-post/
```

Com:

```text
01-briefing.md
02-post-versao-principal.md
03-post-versao-curta.md
04-ganchos-alternativos.md
05-ctas-alternativos.md
06-revisao-editor.md
```

## Critério de conclusão

A v0.2 estará pronta quando:

* o sistema gerar posts mais naturais;
* houver versões alternativas;
* houver revisão editorial mais forte;
* o comando `post` funcionar;
* Leandro conseguir usar o sistema para ideias avulsas.

---

# 5. Versão v0.3 — Analytics manual

## Objetivo

Adicionar análise de métricas do LinkedIn inseridas manualmente.

## Funcionalidades

* Ler arquivo de métricas.
* Analisar desempenho de posts.
* Gerar relatório semanal.
* Identificar melhores temas.
* Identificar melhores formatos.
* Sugerir ajustes de calendário.
* Sugerir temas futuros com base nos dados.

## Comando novo

```text
python app/main.py analytics
```

## Entrada esperada

```text
data/analytics/metricas-linkedin.md
```

## Saída esperada

```text
data/generated/YYYY-MM-DD-analytics/
```

Com:

```text
01-relatorio-semanal.md
02-melhores-posts.md
03-aprendizados.md
04-recomendacoes-cmo.md
05-ajustes-calendario.md
```

## Critério de conclusão

A v0.3 estará pronta quando:

* Leandro conseguir colar métricas manualmente;
* o sistema gerar diagnóstico útil;
* o Analytics Agent sugerir melhorias concretas;
* o CMO puder usar os dados para ajustar estratégia.

---

# 6. Versão v0.4 — Carrosséis melhores

## Objetivo

Transformar o BrandOS em uma ferramenta mais forte para criação de carrosséis.

## Funcionalidades

* Comando dedicado para carrossel.
* Roteiro com 6 a 9 slides.
* Sugestão visual por slide.
* Título de capa.
* CTA final.
* Prompt visual por slide.
* Versão pronta para Canva.
* Estrutura de legenda do post.

## Comando novo

```text
python app/main.py carousel
```

## Entrada esperada

```text
data/inbox/tema-carrossel.md
```

## Saída esperada

```text
data/generated/YYYY-MM-DD-carrossel/
```

Com:

```text
01-roteiro-carrossel.md
02-copy-slides.md
03-sugestoes-visuais.md
04-prompts-imagem.md
05-legenda-linkedin.md
```

## Critério de conclusão

A v0.4 estará pronta quando:

* o sistema gerar carrosséis publicáveis;
* os slides tiverem narrativa clara;
* o material puder ser montado no Canva com pouca edição.

---

# 7. Versão v0.5 — Networking Agent

## Objetivo

Transformar networking em rotina orientada por IA.

## Funcionalidades

* Gerar plano diário de comentários.
* Criar modelos de comentários estratégicos.
* Criar mensagens de conexão.
* Definir perfis-alvo por tema.
* Organizar lista de pessoas estratégicas.
* Criar rotina de follow-up.

## Comando novo

```text
python app/main.py networking
```

## Saída esperada

```text
data/generated/YYYY-MM-DD-networking/
```

Com:

```text
01-plano-networking.md
02-comentarios-modelo.md
03-mensagens-conexao.md
04-perfis-alvo.md
05-checklist-diario.md
```

## Critério de conclusão

A v0.5 estará pronta quando:

* Leandro tiver um plano claro de interação;
* o sistema sugerir comentários melhores que “parabéns” ou “excelente post”;
* o networking for tratado como construção de relacionamento, não spam.

---

# 8. Versão v0.6 — Integração com GitHub

## Objetivo

Usar projetos reais como fonte automática de conteúdo.

## Funcionalidades

* Ler informações públicas ou locais dos projetos.
* Gerar posts a partir de README.
* Gerar posts a partir de changelog.
* Gerar posts a partir de commits ou releases.
* Sugerir melhorias no README.
* Identificar quais projetos merecem virar conteúdo.

## Possíveis comandos

```text
python app/main.py github-summary
python app/main.py project-post
```

## Critério de conclusão

A v0.6 estará pronta quando:

* o BrandOS transformar evolução de projeto em conteúdo;
* o GitHub se conectar à estratégia de marca pessoal;
* projetos reais alimentarem o LinkedIn com mais facilidade.

---

# 9. Versão v0.7 — Career Advisor

## Objetivo

Adicionar um agente de carreira.

## Funcionalidades

* Avaliar se o LinkedIn está coerente com os objetivos.
* Avaliar se o GitHub demonstra competências relevantes.
* Sugerir projetos prioritários.
* Identificar lacunas técnicas.
* Sugerir temas de estudo.
* Cruzar conteúdo com objetivos profissionais.
* Preparar narrativa para entrevistas.

## Saídas possíveis

```text
data/generated/YYYY-MM-DD-career-advisor/
```

Com:

```text
01-diagnostico-carreira.md
02-lacunas-tecnicas.md
03-projetos-prioritarios.md
04-ajustes-linkedin.md
05-ajustes-github.md
```

## Critério de conclusão

A v0.7 estará pronta quando:

* o BrandOS ajudar não só no LinkedIn, mas também na direção da carreira;
* Leandro conseguir decidir melhor quais projetos e estudos priorizar.

---

# 10. Versão v0.8 — Interface simples

## Objetivo

Criar uma interface inicial para facilitar o uso.

## Possíveis opções

* Streamlit
* FastAPI + frontend simples
* Textual/TUI no terminal
* Interface web local

## Funcionalidades

* Formulário de briefing semanal.
* Botão para gerar semana.
* Lista de posts gerados.
* Visualização de calendário.
* Área de métricas.
* Botão para exportar Markdown.

## Critério de conclusão

A v0.8 estará pronta quando:

* Leandro conseguir usar o BrandOS sem depender tanto do terminal;
* o projeto começar a parecer produto demonstrável.

---

# 11. Versão v0.9 — Dashboard e histórico

## Objetivo

Organizar histórico de conteúdo e métricas.

## Funcionalidades

* Histórico de posts gerados.
* Status dos posts: rascunho, revisado, publicado, analisado.
* Relatórios semanais.
* Relatórios mensais.
* Visualização de pilares.
* Visualização de frequência.
* Métricas por tema e formato.

## Critério de conclusão

A v0.9 estará pronta quando:

* o BrandOS mostrar evolução ao longo do tempo;
* o histórico ajudar em decisões estratégicas.

---

# 12. Versão v1.0 — Produto demonstrável

## Objetivo

Transformar o BrandOS em um projeto forte de portfólio.

## Características esperadas

* App funcional.
* README profissional.
* Documentação clara.
* Prints ou demo.
* Workflows principais funcionando.
* Agentes documentados.
* Exemplos de outputs.
* Case de uso real.
* Dados sensíveis removidos da versão pública.
* Possível versão pública open source.

## Critério de conclusão

A v1.0 estará pronta quando Leandro conseguir mostrar o projeto em uma entrevista e explicar:

* problema;
* solução;
* arquitetura;
* agentes;
* uso de IA;
* impacto real;
* aprendizados;
* próximos passos.

---

# 13. Backlog futuro

Ideias que podem entrar depois:

* Integração com Google Sheets.
* Integração com Canva.
* Integração com Notion.
* Geração automática de imagem.
* Geração de vídeo curto.
* Recomendação de vagas.
* Análise de perfil LinkedIn.
* Leitura de comentários.
* Agendamento manual assistido.
* Versão multiusuário.
* SaaS.
* Marketplace de templates.
* Plugin para Obsidian.
* Integração com calendário.
* Modo “campanha de 30 dias”.
* Modo “lançamento de projeto”.
* Modo “preparação para entrevista”.

---

# 14. Prioridade imediata

A prioridade agora é apenas a v0.1.

Não avançar para interface, dashboard, LinkedIn API ou automações complexas antes de concluir:

```text
python app/main.py weekly
```

Gerando:

* diagnóstico;
* plano semanal;
* 3 posts;
* carrossel;
* prompts de imagem;
* plano de networking;
* checklist.

---

# 15. Regra de ouro do roadmap

Toda nova ideia deve ser classificada em uma destas categorias:

## Now

Melhora diretamente o loop operacional: decidir o que publicar, revisar, gerar, medir ou aprender hoje.

Exemplos atuais:

* Próxima ação diária no dashboard.
* Lembretes de métricas 24h, 48h e 7d.
* Fluxo CMO → briefing → semana gerada.
* Assistente de publicação manual.

## Next

Melhora qualidade ou reduz trabalho manual sem mudar o produto central.

Exemplos:

* Score editorial antes da publicação.
* Exportar bundle de publicação com post, primeiro comentário, links e checklist.
* Importador de contexto a partir de README/changelog local.

## Later

Importante, mas não bloqueia a primeira versão.

Exemplos:

* Modo campanha de 30 dias.
* Relatórios mensais.
* Integração com GitHub.
* Carrossel avançado.

## No

Ideia que aumenta complexidade sem melhorar publicação, reputação, portfólio ou networking.

Exemplos:

* Publicação automática no LinkedIn antes do fluxo manual estar excelente.
* Dashboard analítico amplo sem dados suficientes.
* Multiusuário/login antes de o uso pessoal estar sólido.
* Integrações externas que substituem revisão humana.

A pergunta principal será sempre:

> Isso ajuda Leandro a publicar melhor, construir reputação, fortalecer portfólio ou gerar networking agora?
