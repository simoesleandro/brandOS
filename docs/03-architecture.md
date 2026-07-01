# BrandOS — Architecture

## 1. Objetivo deste documento

Este documento define a arquitetura técnica do BrandOS.

A arquitetura deve orientar a implementação do MVP em Python, garantindo que o sistema seja:

* simples;
* modular;
* fácil de manter;
* fácil de evoluir;
* compatível com Markdown;
* preparado para uso com diferentes APIs de IA;
* seguro para rodar localmente.

O foco da arquitetura é permitir que o BrandOS funcione como uma agência de marketing pessoal com IA, gerando conteúdo estratégico para LinkedIn a partir da base de conhecimento de Leandro Simões.

---

# 2. Visão geral da arquitetura

O BrandOS será uma aplicação local em Python.

A primeira versão será executada por linha de comando.

Fluxo principal:

```text
Input Markdown → Context Builder → Agents → LLM API → Generated Markdown
```

O sistema deve:

1. Ler arquivos Markdown.
2. Montar contexto.
3. Acionar agentes.
4. Chamar uma API de IA.
5. Salvar os resultados em Markdown.
6. Permitir revisão humana antes da publicação.

---

# 3. Estrutura principal do projeto

A estrutura recomendada do projeto é:

```text
brandos/
│
├── README.md
├── .gitignore
├── .env.example
├── requirements.txt
│
├── docs/
│   ├── 01-product-vision.md
│   ├── 02-requirements.md
│   ├── 03-architecture.md
│   ├── 04-roadmap.md
│   └── 05-ai-development-guide.md
│
├── app/
│   ├── main.py
│   ├── config.py
│   │
│   ├── core/
│   │   ├── llm_client.py
│   │   ├── file_reader.py
│   │   ├── file_writer.py
│   │   ├── context_builder.py
│   │   └── markdown_utils.py
│   │
│   ├── agents/
│   │   ├── cmo_agent.py
│   │   ├── content_strategist_agent.py
│   │   ├── copywriter_agent.py
│   │   ├── editor_agent.py
│   │   ├── designer_agent.py
│   │   ├── networking_agent.py
│   │   └── analytics_agent.py
│   │
│   ├── workflows/
│   │   ├── weekly_workflow.py
│   │   ├── single_post_workflow.py
│   │   ├── carousel_workflow.py
│   │   ├── networking_workflow.py
│   │   └── analytics_workflow.py
│   │
│   ├── prompts/
│   │   ├── system_prompts.py
│   │   └── workflow_prompts.py
│   │
│   └── utils/
│       ├── dates.py
│       ├── slugify.py
│       └── logger.py
│
├── data/
│   ├── inbox/
│   │   └── briefing-da-semana.md
│   │
│   ├── knowledge/
│   │   ├── minha-historia.md
│   │   ├── posicionamento.md
│   │   ├── pilares-de-conteudo.md
│   │   ├── objetivos-90-dias.md
│   │   ├── linkedin-profile.md
│   │   ├── projetos.md
│   │   └── stack-tecnica.md
│   │
│   ├── generated/
│   │
│   └── analytics/
│       └── metricas-linkedin.md
│
├── config/
│   └── brandos-config.yaml
│
└── tests/
```

---

# 4. Responsabilidade de cada pasta

## 4.1 docs/

Contém a documentação do produto.

Essa pasta deve orientar a IA desenvolvedora e qualquer pessoa que for entender o projeto.

Não contém código de execução.

---

## 4.2 app/

Contém o código Python do BrandOS.

É o núcleo executável do sistema.

---

## 4.3 app/core/

Contém funções centrais e reutilizáveis.

Esses módulos não devem conhecer regras específicas de marketing.

Eles resolvem problemas técnicos:

* leitura de arquivos;
* escrita de arquivos;
* chamada à IA;
* construção de contexto;
* manipulação de Markdown.

---

## 4.4 app/agents/

Contém os agentes do BrandOS.

Cada agente deve ter uma responsabilidade específica.

A regra é:

> Um agente não deve fazer o trabalho de outro agente.

---

## 4.5 app/workflows/

Contém fluxos completos que coordenam múltiplos agentes.

Exemplo:

* workflow semanal;
* workflow de post único;
* workflow de carrossel;
* workflow de analytics;
* workflow de networking.

---

## 4.6 app/prompts/

Contém prompts reutilizáveis do sistema.

A ideia é evitar prompts espalhados pelo código.

---

## 4.7 app/utils/

Contém funções auxiliares.

Exemplos:

* datas;
* slugs;
* logs;
* limpeza de nomes de arquivos.

---

## 4.8 data/

Contém dados de entrada, conhecimento e saída.

Essa pasta é importante porque permite que o sistema funcione com arquivos Markdown simples.

---

## 4.9 data/inbox/

Contém ideias e briefings escritos manualmente por Leandro.

Arquivo principal do MVP:

```text
data/inbox/briefing-da-semana.md
```

---

## 4.10 data/knowledge/

Contém a base de conhecimento sobre Leandro.

Arquivos mínimos:

```text
minha-historia.md
posicionamento.md
pilares-de-conteudo.md
objetivos-90-dias.md
```

Arquivos recomendados:

```text
linkedin-profile.md
projetos.md
stack-tecnica.md
tom-de-voz.md
calendario-30-dias.md
```

---

## 4.11 data/generated/

Contém tudo que o BrandOS gerar automaticamente.

Exemplo:

```text
data/generated/2026-06-30-semana-brandos/
```

---

## 4.12 data/analytics/

Contém métricas manuais do LinkedIn e relatórios futuros.

---

## 4.13 config/

Contém configurações do sistema.

Exemplo:

```text
config/brandos-config.yaml
```

---

## 4.14 tests/

Contém testes do projeto.

No MVP, pode começar simples.

Depois pode evoluir para testes automatizados.

---

# 5. Módulos principais

## 5.1 app/main.py

Ponto de entrada da aplicação.

Deve receber comandos como:

```text
python app/main.py weekly
python app/main.py post
python app/main.py carousel
python app/main.py analytics
python app/main.py networking
```

No MVP, o comando obrigatório é:

```text
python app/main.py weekly
```

---

## 5.2 app/config.py

Responsável por carregar configurações.

Deve ler:

* variáveis de ambiente;
* arquivo `.env`;
* arquivo `config/brandos-config.yaml`.

Deve expor configurações como:

* provedor de IA;
* modelo;
* chave de API;
* dias de postagem;
* horários;
* nome da marca;
* caminho das pastas.

---

## 5.3 app/core/file_reader.py

Responsável por ler arquivos Markdown.

Funções esperadas:

* ler um arquivo específico;
* ler todos os arquivos de uma pasta;
* ignorar arquivos inexistentes sem quebrar o sistema;
* retornar texto limpo.

---

## 5.4 app/core/file_writer.py

Responsável por salvar arquivos Markdown gerados.

Funções esperadas:

* criar pasta de saída;
* salvar arquivo Markdown;
* evitar sobrescrever sem controle;
* criar arquivos com nomes padronizados.

---

## 5.5 app/core/context_builder.py

Responsável por montar o contexto enviado para a IA.

Deve combinar:

* história;
* posicionamento;
* pilares;
* objetivos;
* briefing;
* projetos;
* regras de tom;
* agente ativo.

Esse é um dos módulos mais importantes do sistema.

---

## 5.6 app/core/llm_client.py

Responsável por conversar com a API de IA.

Deve ser uma camada abstrata.

O restante do app não deve depender diretamente de Gemini, Claude ou OpenAI.

Exemplo de responsabilidade:

```text
generate(prompt: str) -> str
```

No MVP, pode começar com um provedor principal, mas deve ser fácil trocar depois.

---

## 5.7 app/core/markdown_utils.py

Responsável por utilidades de Markdown.

Pode conter funções para:

* limpar títulos;
* criar seções;
* gerar cabeçalhos;
* normalizar saída;
* extrair blocos.

---

# 6. Agentes

## 6.1 CMO Agent

Arquivo:

```text
app/agents/cmo_agent.py
```

Responsabilidade:

* gerar diagnóstico estratégico;
* definir prioridade da semana;
* identificar riscos;
* sugerir pilares e temas.

Entrada:

* contexto geral;
* briefing da semana.

Saída:

* diagnóstico em Markdown.

---

## 6.2 Content Strategist Agent

Arquivo:

```text
app/agents/content_strategist_agent.py
```

Responsabilidade:

* transformar diagnóstico em plano semanal;
* definir 3 publicações;
* sugerir formato, gancho e CTA.

Entrada:

* contexto geral;
* diagnóstico CMO;
* calendário.

Saída:

* plano semanal em Markdown.

---

## 6.3 Copywriter Agent

Arquivo:

```text
app/agents/copywriter_agent.py
```

Responsabilidade:

* escrever posts para LinkedIn;
* seguir briefing do plano semanal;
* manter tom humano e profissional.

Entrada:

* contexto geral;
* plano semanal;
* regras de copywriting.

Saída:

* posts em Markdown.

---

## 6.4 Editor Agent

Arquivo:

```text
app/agents/editor_agent.py
```

Responsabilidade:

* revisar posts;
* remover cara de IA;
* melhorar clareza;
* evitar exageros;
* aprovar versão final.

Entrada:

* post gerado;
* posicionamento;
* regras editoriais.

Saída:

* post revisado em Markdown.

---

## 6.5 Designer Agent

Arquivo:

```text
app/agents/designer_agent.py
```

Responsabilidade:

* criar roteiro de carrossel;
* sugerir estrutura visual;
* gerar prompts de imagem.

Entrada:

* posts da semana;
* tema escolhido;
* identidade da marca.

Saída:

* roteiro de carrossel;
* prompts visuais.

---

## 6.6 Networking Agent

Arquivo:

```text
app/agents/networking_agent.py
```

Responsabilidade:

* sugerir plano de networking;
* indicar tipos de pessoas para interagir;
* criar exemplos de comentários;
* criar mensagens de conexão.

Entrada:

* temas da semana;
* público-alvo;
* objetivos de networking.

Saída:

* plano semanal de networking.

---

## 6.7 Analytics Agent

Arquivo:

```text
app/agents/analytics_agent.py
```

Responsabilidade futura:

* analisar métricas manuais;
* gerar diagnóstico;
* sugerir ajustes;
* orientar próximos posts.

No MVP, pode ficar previsto, mas não precisa ser o primeiro workflow implementado.

---

# 7. Workflows

## 7.1 Weekly Workflow

Arquivo:

```text
app/workflows/weekly_workflow.py
```

Esse é o workflow principal do MVP.

Responsabilidade:

1. Ler briefing da semana.
2. Ler base de conhecimento.
3. Montar contexto.
4. Rodar CMO Agent.
5. Rodar Content Strategist Agent.
6. Rodar Copywriter Agent.
7. Rodar Editor Agent.
8. Rodar Designer Agent.
9. Rodar Networking Agent.
10. Gerar checklist.
11. Salvar todos os arquivos em Markdown.

Saída esperada:

```text
data/generated/YYYY-MM-DD-semana-brandos/
```

Arquivos:

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

## 7.2 Single Post Workflow

Arquivo:

```text
app/workflows/single_post_workflow.py
```

Responsabilidade futura:

* gerar um post a partir de uma ideia específica.

Comando futuro:

```text
python app/main.py post
```

---

## 7.3 Carousel Workflow

Arquivo:

```text
app/workflows/carousel_workflow.py
```

Responsabilidade futura:

* transformar um tema ou post em carrossel.

Comando futuro:

```text
python app/main.py carousel
```

---

## 7.4 Analytics Workflow

Arquivo:

```text
app/workflows/analytics_workflow.py
```

Responsabilidade futura:

* ler métricas manuais;
* gerar relatório;
* sugerir melhorias.

Comando futuro:

```text
python app/main.py analytics
```

---

## 7.5 Networking Workflow

Arquivo:

```text
app/workflows/networking_workflow.py
```

Responsabilidade futura:

* gerar plano de networking sob demanda.

Comando futuro:

```text
python app/main.py networking
```

---

# 8. Fluxo de dados do Weekly Workflow

```text
briefing-da-semana.md
        ↓
file_reader
        ↓
context_builder
        ↓
CMO Agent
        ↓
Content Strategist Agent
        ↓
Copywriter Agent
        ↓
Editor Agent
        ↓
Designer Agent
        ↓
Networking Agent
        ↓
file_writer
        ↓
data/generated/YYYY-MM-DD-semana-brandos/
```

---

# 9. Prompting Architecture

Os prompts devem ser separados por responsabilidade.

## 9.1 System Prompt

Define comportamento geral do BrandOS.

Deve conter:

* objetivo;
* tom;
* regras de segurança;
* foco em reputação;
* proibição de exageros;
* necessidade de revisão humana.

---

## 9.2 Agent Prompt

Define comportamento de cada agente.

Exemplo:

* CMO pensa estratégia.
* Copywriter escreve.
* Editor revisa.
* Designer estrutura carrossel.
* Analytics analisa métricas.

---

## 9.3 Workflow Prompt

Define a tarefa atual.

Exemplo:

* “gere o diagnóstico da semana”;
* “gere 3 posts”;
* “revise este post”;
* “gere plano de networking”.

---

# 10. Configuração

## 10.1 .env

Arquivo local não versionado.

Deve conter:

```text
BRANDOS_LLM_PROVIDER=gemini
BRANDOS_API_KEY=sua_chave_aqui
BRANDOS_MODEL=gemini-1.5-flash
```

---

## 10.2 .env.example

Arquivo versionado.

Deve conter:

```text
BRANDOS_LLM_PROVIDER=gemini
BRANDOS_API_KEY=your_api_key_here
BRANDOS_MODEL=gemini-1.5-flash
```

---

## 10.3 config/brandos-config.yaml

Configuração geral do BrandOS.

Exemplo:

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

# 11. Segurança

## 11.1 Chaves de API

Nunca salvar chave real no GitHub.

O `.env` deve estar no `.gitignore`.

---

## 11.2 Publicação manual

O sistema não deve publicar automaticamente no LinkedIn no MVP.

---

## 11.3 Sem scraping

O sistema não deve coletar dados do LinkedIn automaticamente no MVP.

---

## 11.4 Revisão humana

Todo conteúdo gerado deve ser revisado por Leandro antes da publicação.

---

# 12. Estratégia de LLM

## 12.1 Camada abstrata

O sistema deve ter um `LLMClient`.

Esse cliente deve esconder detalhes do provedor.

Assim, no futuro, será possível trocar:

* Gemini;
* Claude;
* OpenAI;
* Ollama;
* outros provedores.

---

## 12.2 Provedor inicial

Para o MVP, escolher apenas um provedor.

Recomendação inicial:

* Gemini API, por custo baixo;
* ou Claude API, por qualidade textual.

A arquitetura deve permitir troca futura.

---

# 13. Estratégia de arquivos

O BrandOS deve salvar tudo em Markdown.

Motivos:

* fácil leitura;
* compatível com Obsidian;
* compatível com GitHub;
* fácil versionamento;
* auditável;
* simples de editar manualmente.

---

# 14. Tratamento de erros

O sistema deve tratar erros básicos:

* arquivo de briefing não encontrado;
* chave de API ausente;
* falha na chamada da IA;
* pasta de saída inexistente;
* erro ao salvar arquivo.

A resposta de erro deve ser clara e orientar o usuário.

---

# 15. Logs

O sistema deve mostrar mensagens simples no terminal:

```text
Carregando contexto...
Lendo briefing da semana...
Gerando diagnóstico CMO...
Gerando plano semanal...
Gerando posts...
Revisando posts...
Gerando carrossel...
Gerando plano de networking...
Salvando arquivos...
Concluído.
```

---

# 16. Critérios de qualidade da arquitetura

A arquitetura será considerada boa se:

* for simples;
* permitir rodar o MVP;
* separar responsabilidades;
* evitar código duplicado;
* permitir trocar a IA;
* salvar tudo em Markdown;
* não depender de LinkedIn API;
* permitir evolução futura;
* for compreensível para Leandro;
* puder ser mostrada como projeto de portfólio.

---

# 17. Evolução futura

## v0.2

Adicionar:

* comando post;
* comando carousel;
* melhoria no prompt dos agentes;
* análise simples de métricas.

## v0.3

Adicionar:

* dashboard simples em terminal;
* integração com Google Sheets;
* histórico de posts.

## v0.4

Adicionar:

* leitura de projetos do GitHub;
* geração de posts a partir de commits;
* integração com README dos projetos.

## v1.0

Adicionar:

* interface web;
* sistema completo de campanha;
* analytics visual;
* versão demonstrável para portfólio.
