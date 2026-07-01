# BrandOS — Requirements

## 1. Objetivo deste documento

Este documento define o que o BrandOS precisa fazer na primeira versão funcional.

Ele serve como guia para implementação no Claude Code, Antigravity ou qualquer outra ferramenta de desenvolvimento com IA.

O foco é construir um MVP simples, funcional e útil.

O BrandOS não deve tentar ser perfeito na primeira versão.
Ele deve funcionar bem o suficiente para ajudar Leandro a produzir conteúdo com consistência e transformar sua presença no LinkedIn em um ativo profissional.

---

# 2. Definição do MVP

O MVP do BrandOS será uma aplicação local em Python que:

1. Lê arquivos Markdown com contexto sobre Leandro.
2. Lê um briefing semanal escrito manualmente.
3. Usa uma API de IA para gerar conteúdo estratégico.
4. Simula uma agência com agentes especializados.
5. Salva os resultados em arquivos Markdown.
6. Permite revisão humana antes da publicação.
7. Ajuda Leandro a publicar 3 vezes por semana no LinkedIn.

---

# 3. Usuário principal

O usuário principal é Leandro Simões.

Ele usará o sistema para:

* planejar posts;
* gerar textos para LinkedIn;
* gerar roteiros de carrossel;
* gerar prompts de imagem;
* organizar networking;
* analisar métricas;
* melhorar posicionamento;
* fortalecer portfólio;
* construir autoridade em tecnologia.

---

# 4. Requisitos funcionais

## RF01 — Ler arquivos de conhecimento

O sistema deve ler arquivos Markdown contendo informações sobre:

* história pessoal;
* posicionamento;
* objetivos;
* pilares de conteúdo;
* projetos;
* agentes;
* calendário;
* métricas;
* briefing da semana.

Esses arquivos ficarão inicialmente em:

```text
data/knowledge/
data/inbox/
data/analytics/
```

---

## RF02 — Ler briefing da semana

O sistema deve procurar e ler o arquivo:

```text
data/inbox/briefing-da-semana.md
```

Esse arquivo será o input principal do fluxo semanal.

Ele deve conter:

* o que aconteceu na semana;
* projetos em foco;
* objetivo da semana;
* restrições de tom;
* observações importantes.

---

## RF03 — Montar contexto para IA

O sistema deve combinar os principais arquivos de conhecimento em um contexto único para enviar à API de IA.

O contexto deve conter, pelo menos:

* quem é Leandro;
* posicionamento;
* pilares de conteúdo;
* objetivos de 90 dias;
* briefing da semana;
* regras de tom;
* agentes relevantes;
* calendário ou frequência de publicação.

---

## RF04 — Gerar diagnóstico estratégico

O sistema deve gerar um diagnóstico CMO da semana.

Esse diagnóstico deve responder:

* qual é a prioridade da semana;
* quais temas têm maior potencial;
* quais pilares devem ser trabalhados;
* quais riscos devem ser evitados;
* qual direção o conteúdo deve seguir.

Arquivo de saída esperado:

```text
01-diagnostico-cmo.md
```

---

## RF05 — Gerar plano semanal

O sistema deve gerar um plano semanal com 3 publicações.

O plano deve incluir:

* data sugerida;
* dia da semana;
* horário;
* pilar;
* tema;
* formato;
* objetivo;
* gancho sugerido;
* CTA;
* observações de tom.

Arquivo de saída esperado:

```text
02-plano-semanal.md
```

---

## RF06 — Gerar 3 posts para LinkedIn

O sistema deve gerar 3 posts para LinkedIn:

* post de segunda-feira;
* post de quarta-feira;
* post de sexta-feira.

Cada post deve conter:

* título interno;
* pilar;
* objetivo;
* texto final;
* CTA;
* hashtags sugeridas;
* observações de publicação.

Arquivos de saída esperados:

```text
03-post-segunda.md
04-post-quarta.md
05-post-sexta.md
```

---

## RF07 — Revisar posts

O sistema deve aplicar uma etapa de revisão usando o comportamento do agente Editor.

A revisão deve verificar:

* clareza;
* tom humano;
* alinhamento estratégico;
* ausência de exageros;
* ausência de tom de guru;
* força do gancho;
* qualidade do CTA;
* prontidão para publicação.

Cada post gerado deve sair já revisado.

---

## RF08 — Gerar roteiro de carrossel

O sistema deve escolher um dos temas da semana e gerar um roteiro de carrossel.

O carrossel deve conter:

* título;
* objetivo;
* quantidade de slides;
* texto de cada slide;
* sugestão visual de cada slide;
* CTA final.

Arquivo de saída esperado:

```text
06-carrossel.md
```

---

## RF09 — Gerar prompts de imagem

O sistema deve gerar prompts de imagem para apoiar os conteúdos da semana.

Os prompts devem ser pensados para ferramentas como:

* ChatGPT Image;
* Ideogram;
* Leonardo;
* Canva;
* Midjourney;
* outras ferramentas visuais.

Os prompts devem respeitar a identidade profissional do BrandOS.

Arquivo de saída esperado:

```text
07-prompts-imagem.md
```

---

## RF10 — Gerar plano de networking

O sistema deve gerar um plano simples de networking para a semana.

O plano deve incluir:

* tipos de pessoas para comentar;
* temas de posts para buscar;
* sugestões de comentários;
* mensagens de conexão;
* metas diárias realistas.

Arquivo de saída esperado:

```text
08-plano-networking.md
```

---

## RF11 — Gerar checklist de publicação

O sistema deve gerar um checklist para Leandro seguir antes e depois de publicar.

O checklist deve conter:

* revisão do texto;
* revisão de CTA;
* publicação manual;
* resposta a comentários;
* registro de métricas;
* ações de networking.

Arquivo de saída esperado:

```text
09-checklist-publicacao.md
```

---

## RF12 — Salvar resultados em Markdown

Todos os conteúdos gerados devem ser salvos em Markdown dentro de uma pasta criada automaticamente em:

```text
data/generated/
```

O nome da pasta deve seguir o padrão:

```text
YYYY-MM-DD-semana-brandos
```

Exemplo:

```text
data/generated/2026-06-30-semana-brandos/
```

---

## RF13 — Rodar comando semanal

O sistema deve permitir rodar o fluxo principal com:

```text
python app/main.py weekly
```

Esse comando deve executar o workflow semanal completo.

---

## RF14 — Gerar post único

O sistema deve futuramente permitir gerar um post único com:

```text
python app/main.py post
```

Esse comando poderá ler uma ideia em:

```text
data/inbox/ideia-post.md
```

Esse requisito pode ser implementado depois do workflow semanal.

---

## RF15 — Analisar métricas

O sistema deve futuramente permitir analisar métricas com:

```text
python app/main.py analytics
```

Ele deve ler dados manuais em:

```text
data/analytics/metricas-linkedin.md
```

E gerar recomendações em:

```text
data/generated/relatorio-analytics.md
```

Esse requisito pode entrar após a primeira versão funcional do comando semanal.

---

# 5. Requisitos não funcionais

## RNF01 — Simplicidade

O sistema deve ser simples de entender, rodar e modificar.

Não deve ter arquitetura complexa demais no MVP.

---

## RNF02 — Modularidade

O código deve ser separado em módulos claros:

* leitura de arquivos;
* escrita de arquivos;
* cliente de IA;
* construção de contexto;
* agentes;
* workflows;
* utilitários.

---

## RNF03 — Segurança

O sistema não deve expor chaves de API.

Chaves devem ficar em arquivo `.env`, que não deve ser versionado no GitHub.

O projeto deve conter apenas:

```text
.env.example
```

---

## RNF04 — Portabilidade

O projeto deve rodar localmente em Windows.

Preferencialmente também deve funcionar em Linux e macOS.

---

## RNF05 — Saída auditável

Tudo que a IA gerar deve ser salvo em Markdown.

Isso permite:

* revisão humana;
* versionamento;
* leitura no Obsidian;
* uso no GitHub;
* histórico de evolução.

---

## RNF06 — Sem publicação automática

O BrandOS não deve publicar automaticamente no LinkedIn no MVP.

Leandro deve revisar e publicar manualmente.

---

## RNF07 — Sem scraping

O sistema não deve fazer scraping do LinkedIn.

Métricas serão inseridas manualmente no início.

---

## RNF08 — Baixo custo

O sistema deve ser projetado para usar modelos baratos ou gratuitos sempre que possível.

A primeira versão deve permitir configuração do provedor de IA.

---

## RNF09 — Troca de modelo

O sistema deve ter uma camada de LLM abstraída, permitindo futuramente trocar entre:

* Gemini;
* Claude;
* OpenAI;
* modelos locais;
* outros provedores.

---

## RNF10 — Código legível

O código deve ser claro e organizado.

Evitar overengineering.

---

# 6. Agentes do MVP

## 6.1 CMO Agent

Responsável por estratégia.

Entrada:

* contexto do Leandro;
* posicionamento;
* objetivos;
* briefing da semana.

Saída:

* diagnóstico estratégico;
* prioridades;
* riscos;
* temas recomendados.

---

## 6.2 Content Strategist Agent

Responsável por transformar estratégia em plano semanal.

Entrada:

* diagnóstico CMO;
* calendário;
* pilares.

Saída:

* plano de 3 posts;
* tema;
* formato;
* gancho;
* CTA.

---

## 6.3 Copywriter Agent

Responsável por escrever os posts.

Entrada:

* plano semanal;
* contexto;
* regras de tom.

Saída:

* 3 posts completos para LinkedIn.

---

## 6.4 Editor Agent

Responsável por revisar os posts.

Entrada:

* posts gerados;
* regras editoriais;
* posicionamento.

Saída:

* posts revisados e prontos para publicação.

---

## 6.5 Designer Agent

Responsável por roteiro de carrossel e prompts visuais.

Entrada:

* tema escolhido;
* posts da semana;
* posicionamento.

Saída:

* roteiro de carrossel;
* prompts de imagem.

---

## 6.6 Networking Agent

Responsável por plano de interação.

Entrada:

* objetivo da semana;
* temas dos posts;
* público-alvo.

Saída:

* sugestões de comentários;
* mensagens de conexão;
* metas de networking.

---

## 6.7 Analytics Agent

Não precisa ser completo no primeiro comando semanal.

Mas deve estar previsto para analisar métricas posteriormente.

Entrada futura:

* métricas manuais;
* posts publicados;
* histórico.

Saída futura:

* relatório;
* recomendações;
* próximos experimentos.

---

# 7. Workflow principal: Weekly

## Entrada

```text
data/inbox/briefing-da-semana.md
```

## Processo

1. Carregar configuração.
2. Carregar arquivos de conhecimento.
3. Montar contexto.
4. Rodar CMO Agent.
5. Rodar Content Strategist Agent.
6. Rodar Copywriter Agent.
7. Rodar Editor Agent.
8. Rodar Designer Agent.
9. Rodar Networking Agent.
10. Gerar checklist.
11. Salvar arquivos em Markdown.

## Saída

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

---

# 8. Arquivos mínimos de entrada

Para o MVP funcionar, o projeto deve conter pelo menos:

```text
data/inbox/briefing-da-semana.md
data/knowledge/minha-historia.md
data/knowledge/posicionamento.md
data/knowledge/pilares-de-conteudo.md
data/knowledge/objetivos-90-dias.md
```

Arquivos adicionais podem melhorar a qualidade:

```text
data/knowledge/linkedin-profile.md
data/knowledge/tom-de-voz.md
data/knowledge/projetos.md
data/knowledge/stack-tecnica.md
data/knowledge/calendario-30-dias.md
```

---

# 9. Configuração mínima

O sistema deve conter:

```text
.env.example
config/brandos-config.yaml
```

## .env.example

```text
BRANDOS_LLM_PROVIDER=gemini
BRANDOS_API_KEY=your_api_key_here
BRANDOS_MODEL=gemini-1.5-flash
```

## brandos-config.yaml

```yaml
brand:
  name: "Leandro Simões"
  project_name: "BrandOS"
  main_platform: "LinkedIn"

posting:
  frequency_per_week: 3
  days:
    - segunda
    - quarta
    - sexta
  times:
    segunda: "08:30"
    quarta: "12:15"
    sexta: "08:30"

strategy:
  priorities:
    - networking
    - autoridade
    - portfolio
    - oportunidades
```

---

# 10. Critérios de aceite do MVP

O MVP será considerado pronto quando:

* o comando `python app/main.py weekly` rodar sem erro;
* o sistema ler o briefing da semana;
* o sistema ler arquivos de conhecimento;
* o sistema chamar uma API de IA;
* o sistema gerar uma pasta em `data/generated/`;
* o sistema salvar os 9 arquivos esperados;
* os posts estiverem em Markdown;
* os posts forem coerentes com o posicionamento;
* o README explicar como configurar e rodar;
* nenhuma chave de API estiver exposta;
* não houver publicação automática no LinkedIn.

---

# 11. O que não deve ser priorizado agora

Não gastar tempo inicialmente com:

* interface web;
* banco de dados;
* login;
* autenticação;
* deploy;
* Docker;
* LinkedIn API;
* dashboard;
* Canva API;
* geração de vídeo;
* multiusuário;
* monetização;
* integração com calendário externo.

Essas coisas podem vir depois.

O primeiro objetivo é simples:

> Rodar um comando e gerar uma semana de conteúdo com qualidade.

---

# 12. Regra de ouro dos requisitos

Sempre que surgir uma nova ideia, perguntar:

> Essa funcionalidade ajuda Leandro a publicar melhor, construir reputação, fortalecer portfólio ou gerar networking agora?

Se a resposta for não, ela vai para o backlog, não para o MVP.
