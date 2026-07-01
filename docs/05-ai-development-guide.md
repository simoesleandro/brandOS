# BrandOS — AI Development Guide

## 1. Objetivo deste documento

Este documento orienta qualquer IA desenvolvedora que for implementar o BrandOS, especialmente em ferramentas como:

* Claude Code
* Antigravity
* Cursor
* Codex
* Gemini CLI
* OpenCode

A IA deve usar este guia como referência para tomar decisões técnicas, organizar arquivos, evitar complexidade desnecessária e respeitar a visão do produto.

O objetivo é construir um MVP funcional, simples, modular e útil.

---

# 2. Papel da IA desenvolvedora

Você é uma IA desenvolvedora sênior responsável por implementar o BrandOS.

Sua função é:

* ler a documentação do projeto;
* entender o objetivo do produto;
* criar a estrutura do app;
* implementar o MVP em Python;
* manter o código simples;
* evitar overengineering;
* garantir que o sistema rode localmente;
* salvar tudo em Markdown;
* nunca expor chave de API;
* respeitar que a publicação no LinkedIn será manual.

Você não está criando um SaaS agora.

Você está criando uma primeira versão local funcional.

---

# 3. Documentos que devem ser lidos antes de programar

Antes de escrever código, leia obrigatoriamente:

```text
docs/01-product-vision.md
docs/02-requirements.md
docs/03-architecture.md
docs/04-roadmap.md
docs/05-ai-development-guide.md
```

Esses documentos são a fonte de verdade do projeto.

Não implemente funcionalidades fora do escopo sem necessidade.

---

# 4. Objetivo técnico imediato

Implementar a versão `v0.1` do BrandOS.

A v0.1 deve permitir rodar:

```bash
python app/main.py weekly
```

E gerar uma semana completa de conteúdo em:

```text
data/generated/YYYY-MM-DD-semana-brandos/
```

Com estes arquivos:

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

# 5. Escopo obrigatório da v0.1

A primeira versão deve implementar apenas:

* leitura de arquivos Markdown;
* leitura do briefing semanal;
* montagem de contexto;
* camada simples de LLM;
* agentes básicos;
* workflow semanal;
* geração de arquivos Markdown;
* README com instruções;
* configuração segura via `.env`;
* saída organizada em `data/generated/`.

---

# 6. Fora do escopo da v0.1

Não implementar agora:

* interface web;
* banco de dados;
* login;
* autenticação;
* dashboard;
* Docker;
* deploy;
* LinkedIn API;
* scraping;
* publicação automática;
* automação de comentários;
* automação de mensagens;
* Canva API;
* Google Sheets API;
* geração automática de vídeo;
* multiusuário;
* monetização;
* SaaS.

Qualquer uma dessas ideias deve ir para versões futuras.

---

# 7. Princípios de desenvolvimento

## 7.1 Simplicidade primeiro

O código deve ser simples de entender.

Evite padrões complexos sem necessidade.

O projeto precisa funcionar antes de ficar sofisticado.

---

## 7.2 Modularidade sem exagero

Separe responsabilidades em módulos, mas não crie abstrações demais.

Cada arquivo deve ter um papel claro.

---

## 7.3 Markdown como formato principal

Entradas e saídas devem usar Markdown.

Motivos:

* fácil leitura;
* fácil edição;
* compatível com GitHub;
* compatível com Obsidian;
* simples de versionar;
* bom para portfólio.

---

## 7.4 Revisão humana obrigatória

O BrandOS não deve publicar nada automaticamente.

A IA gera conteúdo.
Leandro revisa.
Leandro publica manualmente.

---

## 7.5 Segurança

Nunca salvar chaves reais no código.

Nunca colocar `.env` no GitHub.

Sempre usar `.env.example` para demonstrar as variáveis necessárias.

---

## 7.6 Baixo custo

O sistema deve ser compatível com modelos baratos.

A camada de LLM deve permitir troca futura de provedor.

---

## 7.7 Sem dependência de plataforma

O MVP não deve depender do LinkedIn.

Ele gera conteúdo para LinkedIn, mas não se conecta ao LinkedIn.

---

# 8. Estrutura esperada do app

Implementar dentro de:

```text
app/
```

Estrutura esperada:

```text
app/
├── main.py
├── config.py
│
├── core/
│   ├── llm_client.py
│   ├── file_reader.py
│   ├── file_writer.py
│   ├── context_builder.py
│   └── markdown_utils.py
│
├── agents/
│   ├── cmo_agent.py
│   ├── content_strategist_agent.py
│   ├── copywriter_agent.py
│   ├── editor_agent.py
│   ├── designer_agent.py
│   ├── networking_agent.py
│   └── analytics_agent.py
│
├── workflows/
│   ├── weekly_workflow.py
│   ├── single_post_workflow.py
│   ├── carousel_workflow.py
│   ├── networking_workflow.py
│   └── analytics_workflow.py
│
├── prompts/
│   ├── system_prompts.py
│   └── workflow_prompts.py
│
└── utils/
    ├── dates.py
    ├── slugify.py
    └── logger.py
```

Na v0.1, nem todos os arquivos precisam ter lógica completa.

Mas a estrutura deve estar preparada para evolução.

---

# 9. Estrutura de dados esperada

Usar:

```text
data/
├── inbox/
│   └── briefing-da-semana.md
│
├── knowledge/
│   ├── minha-historia.md
│   ├── posicionamento.md
│   ├── pilares-de-conteudo.md
│   ├── objetivos-90-dias.md
│   ├── linkedin-profile.md
│   ├── projetos.md
│   └── stack-tecnica.md
│
├── generated/
│
└── analytics/
    └── metricas-linkedin.md
```

Arquivos mínimos para rodar o MVP:

```text
data/inbox/briefing-da-semana.md
data/knowledge/minha-historia.md
data/knowledge/posicionamento.md
data/knowledge/pilares-de-conteudo.md
data/knowledge/objetivos-90-dias.md
```

Se algum arquivo extra não existir, o sistema deve continuar funcionando, apenas com menos contexto.

---

# 10. Configuração esperada

Criar ou usar:

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

## config/brandos-config.yaml

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

# 11. Comportamento esperado do comando weekly

O comando:

```bash
python app/main.py weekly
```

Deve executar:

1. Carregar configurações.
2. Ler `data/inbox/briefing-da-semana.md`.
3. Ler arquivos de `data/knowledge/`.
4. Montar contexto.
5. Gerar diagnóstico CMO.
6. Gerar plano semanal.
7. Gerar 3 posts.
8. Revisar os posts.
9. Gerar carrossel.
10. Gerar prompts de imagem.
11. Gerar plano de networking.
12. Gerar checklist.
13. Salvar tudo em Markdown.
14. Exibir no terminal o caminho da pasta gerada.

---

# 12. Logs esperados no terminal

O sistema deve mostrar mensagens simples:

```text
[BrandOS] Carregando configurações...
[BrandOS] Lendo briefing da semana...
[BrandOS] Carregando base de conhecimento...
[BrandOS] Montando contexto...
[BrandOS] Gerando diagnóstico CMO...
[BrandOS] Gerando plano semanal...
[BrandOS] Gerando posts...
[BrandOS] Revisando posts...
[BrandOS] Gerando carrossel...
[BrandOS] Gerando prompts de imagem...
[BrandOS] Gerando plano de networking...
[BrandOS] Gerando checklist...
[BrandOS] Salvando arquivos...
[BrandOS] Concluído.
```

---

# 13. Tratamento de erros

O sistema deve tratar erros de forma clara.

## Erro: briefing ausente

Mensagem sugerida:

```text
Briefing da semana não encontrado.
Crie o arquivo data/inbox/briefing-da-semana.md antes de rodar o comando weekly.
```

## Erro: chave de API ausente

Mensagem sugerida:

```text
Chave de API não encontrada.
Crie um arquivo .env com BRANDOS_API_KEY.
Use .env.example como referência.
```

## Erro: falha na IA

Mensagem sugerida:

```text
Falha ao chamar o provedor de IA.
Verifique sua chave, conexão e modelo configurado.
```

## Erro: pasta de saída

Mensagem sugerida:

```text
Não foi possível criar a pasta de saída em data/generated/.
Verifique permissões do projeto.
```

---

# 14. Padrão dos agentes

Cada agente deve ter uma função simples.

## CMO Agent

Gera diagnóstico estratégico.

Não escreve posts.

## Content Strategist Agent

Cria plano semanal.

Não escreve texto final.

## Copywriter Agent

Escreve posts.

Não decide estratégia.

## Editor Agent

Revisa posts.

Não muda a estratégia central.

## Designer Agent

Cria roteiro de carrossel e prompts visuais.

Não publica nem cria imagem diretamente.

## Networking Agent

Cria plano de interação.

Não envia mensagens automaticamente.

## Analytics Agent

Previsto para versões futuras.

Não precisa ser completo na v0.1.

---

# 15. Padrão de prompts

Os prompts devem ser claros e específicos.

Cada prompt deve informar:

* papel do agente;
* contexto;
* objetivo da tarefa;
* formato esperado da saída;
* regras de tom;
* restrições;
* critérios de qualidade.

Evitar prompts genéricos como:

```text
Crie posts para LinkedIn.
```

Preferir prompts estruturados como:

```text
Você é o Copywriter Agent do BrandOS.
Use o contexto abaixo para escrever um post para LinkedIn alinhado ao posicionamento de Leandro.
O post deve ter tom humano, maduro e direto.
Evite parecer guru, exagerar autoridade ou usar clichês.
Saída em Markdown.
```

---

# 16. Padrão de saída

Toda saída gerada pela IA deve ser Markdown.

Não salvar JSON como saída final para o usuário.

JSON pode ser usado internamente apenas se necessário.

Arquivos gerados devem ter títulos claros.

Exemplo:

```markdown
# Post de Segunda — Eu não estou começando do zero na tecnologia

## Pilar

Transição de carreira com maturidade.

## Objetivo

Criar conexão e reforçar maturidade profissional.

## Texto final

...

## CTA

...

## Hashtags

...
```

---

# 17. Critérios de qualidade dos posts

Posts gerados devem:

* ter gancho forte;
* parecer humanos;
* evitar cara de IA;
* evitar exageros;
* evitar linguagem de guru;
* usar frases curtas;
* ter parágrafos curtos;
* ter CTA natural;
* reforçar autoridade prática;
* conectar com projetos, aprendizado ou carreira;
* preservar o posicionamento do Leandro.

---

# 18. Tom de voz desejado

O tom deve ser:

* humano;
* direto;
* maduro;
* honesto;
* prático;
* curioso;
* profissional;
* sem arrogância;
* sem vitimismo;
* sem hype excessivo.

Evitar:

* “jornada incrível”;
* “revolucionário”;
* “método infalível”;
* “segredo”;
* “hack definitivo”;
* “do zero ao avançado”;
* “basta fazer isso”;
* linguagem de coach;
* autopromoção vazia.

---

# 19. README obrigatório

A implementação deve incluir ou atualizar `README.md` com:

* nome do projeto;
* descrição;
* objetivo;
* estrutura de pastas;
* requisitos;
* instalação;
* configuração;
* como rodar;
* comandos disponíveis;
* exemplo de briefing;
* saída esperada;
* roadmap curto;
* aviso sobre publicação manual.

---

# 20. Dependências recomendadas

Para a v0.1, usar o mínimo possível.

Dependências possíveis:

```text
python-dotenv
pyyaml
google-generativeai
```

Se usar outro provedor, adicionar dependência correspondente.

Evitar frameworks pesados no MVP.

---

# 21. Git e segurança

Criar `.gitignore` com pelo menos:

```text
.env
__pycache__/
*.pyc
.venv/
venv/
data/generated/
```

A pasta `data/generated/` pode ser ignorada inicialmente para evitar versionar saídas geradas.

Se quiser versionar exemplos no futuro, criar uma pasta específica:

```text
examples/
```

---

# 22. Testes mínimos

Na v0.1, criar pelo menos testes simples ou checklist para verificar:

* leitura de arquivo Markdown;
* montagem de contexto;
* criação de pasta de saída;
* salvamento de arquivo Markdown;
* execução do workflow semanal sem quebrar.

Não precisa criar suíte complexa no início.

---

# 23. Ordem recomendada de implementação

Implementar nesta ordem:

## Passo 1

Criar/validar estrutura de pastas.

## Passo 2

Criar README inicial.

## Passo 3

Criar `.gitignore`, `.env.example`, `requirements.txt`.

## Passo 4

Implementar configuração.

## Passo 5

Implementar leitura e escrita de arquivos.

## Passo 6

Implementar LLM Client.

## Passo 7

Implementar Context Builder.

## Passo 8

Implementar agentes básicos.

## Passo 9

Implementar Weekly Workflow.

## Passo 10

Implementar `python app/main.py weekly`.

## Passo 11

Testar com briefing real.

## Passo 12

Ajustar qualidade dos prompts.

---

# 24. Prompt recomendado para iniciar no Claude Code ou Antigravity

Use este prompt dentro da ferramenta de desenvolvimento:

```text
Você é uma IA desenvolvedora sênior responsável por implementar o MVP v0.1 do BrandOS.

Antes de programar, leia todos os arquivos da pasta docs/:

- docs/01-product-vision.md
- docs/02-requirements.md
- docs/03-architecture.md
- docs/04-roadmap.md
- docs/05-ai-development-guide.md

Depois implemente apenas a v0.1.

Objetivo:
Criar uma aplicação local em Python que rode:

python app/main.py weekly

E gere uma semana de conteúdo em Markdown dentro de:

data/generated/YYYY-MM-DD-semana-brandos/

Com os arquivos:

01-diagnostico-cmo.md
02-plano-semanal.md
03-post-segunda.md
04-post-quarta.md
05-post-sexta.md
06-carrossel.md
07-prompts-imagem.md
08-plano-networking.md
09-checklist-publicacao.md

Regras:
- Não implemente interface web.
- Não implemente LinkedIn API.
- Não implemente scraping.
- Não implemente publicação automática.
- Não implemente banco de dados.
- Não exponha chave de API.
- Use Markdown como entrada e saída.
- Faça código simples, modular e legível.
- Use README claro.
- Se alguma informação estiver faltando, crie defaults seguros e documente.

Ao final, me entregue:
1. resumo do que foi implementado;
2. arquivos criados;
3. como configurar;
4. como rodar;
5. riscos ou pendências;
6. próximos passos.
```

---

# 25. Regra de ouro para a IA desenvolvedora

Sempre que surgir dúvida, priorize:

1. Simplicidade.
2. Funcionamento local.
3. Segurança.
4. Markdown.
5. Revisão humana.
6. Baixo custo.
7. Clareza de código.
8. Evolução futura.

Nunca sacrifique o MVP tentando construir a versão final.
