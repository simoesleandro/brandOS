<div align="center">

# BrandOS

**PT:** Sistema operacional de marca pessoal com IA — agentes editoriais, Web Console, Asset Manager e esteira completa para transformar projetos reais em conteúdo profissional.  
**EN:** AI-powered personal brand operating system — editorial agents, Web Console, Asset Manager and a full pipeline to turn real projects into professional content.

<br/>

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-local_web_console-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Gemini-LLM-4285F4?style=flat-square&logo=google&logoColor=white)](https://aistudio.google.com)
[![Jinja2](https://img.shields.io/badge/Jinja2-templates-B41717?style=flat-square)](https://jinja.palletsprojects.com)
[![Tailwind](https://img.shields.io/badge/Tailwind-CSS-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![Storage](https://img.shields.io/badge/storage-Markdown%20%2B%20JSON-8b5cf6?style=flat-square)](#)
[![Status](https://img.shields.io/badge/status-alpha-f59e0b?style=flat-square)](#)

<br/>

[📖 Documentação](docs/) &nbsp;·&nbsp;
[🧠 Base de conhecimento](data/knowledge/) &nbsp;·&nbsp;
[🐛 Reportar bug](https://github.com/simoesleandro/brandOS/issues) &nbsp;·&nbsp;
[💡 Sugerir feature](https://github.com/simoesleandro/brandOS/issues)

<br/>

> Screenshot do Web Console em breve.

</div>

---

## 📋 Índice / Table of Contents

- [Sobre / About](#-sobre--about)
- [Por que importa / Why it matters](#-por-que-importa--why-it-matters)
- [Competências demonstradas / Skills demonstrated](#-competências-demonstradas--skills-demonstrated)
- [Funcionalidades / Features](#-funcionalidades--features)
- [Agentes / Agents](#-agentes--agents)
- [Web Console](#-web-console)
- [Asset Manager](#-asset-manager)
- [Stack](#-stack)
- [Instalação / Setup](#-instalação--setup)
- [Variáveis de Ambiente / Environment Variables](#-variáveis-de-ambiente--environment-variables)
- [Uso / Usage](#-uso--usage)
- [Arquitetura / Architecture](#-arquitetura--architecture)
- [Estrutura / Project Structure](#-estrutura--project-structure)
- [Roadmap](#-roadmap)
- [Autor / Author](#-autor--author)

---

## 📌 Sobre / About

**PT:**  
BrandOS é um sistema operacional de marca pessoal com IA. Ele organiza a produção de conteúdo profissional a partir de projetos reais, centralizando estratégia, posts, carrosséis, comentários, links oficiais, histórico, status de publicação e assets visuais em uma única esteira local.

A ideia é simples: transformar projetos técnicos reais em conteúdo consistente para LinkedIn, portfólio e networking, sem depender de arquivos espalhados, prompts perdidos ou decisões manuais repetitivas.

**EN:**  
BrandOS is an AI-powered personal brand operating system. It organizes professional content production from real projects, centralizing strategy, posts, carousels, comments, official links, history, publication status and visual assets into a single local workflow.

The idea is simple: turn real technical projects into consistent content for LinkedIn, portfolio and networking, without scattered files, lost prompts or repetitive manual decisions.

---

## 🎯 Por que importa / Why it matters

**PT:**  
Criar conteúdo técnico de forma consistente não é apenas escrever posts. Envolve decidir o que falar, evitar repetição, respeitar o histórico, organizar links, gerar materiais visuais, registrar o que foi publicado e acompanhar o que ainda está pendente.

O BrandOS nasceu para resolver essa operação inteira. Ele funciona como uma agência pessoal com IA: planeja, escreve, revisa, organiza, registra e ajuda a manter continuidade editorial.

**EN:**  
Consistent technical content creation is not just about writing posts. It requires deciding what to say, avoiding repetition, respecting history, organizing links, generating visual materials, registering what was published and tracking what is still pending.

BrandOS was built to solve that whole operation. It works like a personal AI agency: it plans, writes, reviews, organizes, registers and helps maintain editorial continuity.

---

## 🧠 Competências demonstradas / Skills demonstrated

| Área / Area | Evidência no projeto / Evidence |
|------------|----------------------------------|
| IA aplicada | Agentes editoriais com contexto, regras e continuidade |
| Produto | Web Console para operar o fluxo sem depender só de terminal |
| Backend Python | Workflows, serviços, registry, leitura de Markdown/JSON |
| FastAPI | Interface local para controlar gerações, publicações e assets |
| Organização de dados | Histórico, registry, status por peça e links oficiais |
| Automação editorial | Geração de posts, carrosséis, comentários e instruções |
| UX operacional | Controle por item: rascunho, pronto, publicado, ignorado, revisar |
| Asset Management | Associação de imagens, PDFs, vídeos, prompts e templates às publicações |

---

## ✨ Funcionalidades / Features

**PT:** O que o projeto faz hoje:

- ✅ Geração semanal de conteúdo com IA.
- ✅ Planejamento editorial com base em histórico e continuidade.
- ✅ Posts para LinkedIn.
- ✅ Roteiros de carrossel.
- ✅ Prompts visuais.
- ✅ Comentários sugeridos para links de GitHub/demo.
- ✅ Instruções finais de publicação.
- ✅ Controle de status por peça individual.
- ✅ Web Console local.
- ✅ Base de conhecimento em Markdown.
- ✅ Registry em JSON/Markdown.
- ✅ Asset Manager para arquivos visuais.
- 🚧 Métricas por publicação.
- 🚧 Geração de PDF a partir de imagens.
- 🚧 Preview visual de carrosséis.
- 🚧 Dashboard de performance.

**EN:** What the project currently does:

- ✅ Weekly AI-powered content generation.
- ✅ Editorial planning based on history and continuity.
- ✅ LinkedIn posts.
- ✅ Carousel outlines.
- ✅ Visual prompts.
- ✅ Suggested comments for GitHub/demo links.
- ✅ Final publishing instructions.
- ✅ Per-item publication status.
- ✅ Local Web Console.
- ✅ Markdown knowledge base.
- ✅ JSON/Markdown registry.
- ✅ Asset Manager for visual files.
- 🚧 Publication metrics.
- 🚧 PDF generation from images.
- 🚧 Visual carousel preview.
- 🚧 Performance dashboard.

---

## 🤖 Agentes / Agents

| Agente | Função |
|--------|--------|
| **CMO Agent** | Define foco editorial, projeto da semana e ângulo novo |
| **Content Strategist Agent** | Transforma a direção em plano semanal |
| **Copywriter Agent** | Escreve posts com voz humana e profissional |
| **Editor Agent** | Remove cara de IA, melhora clareza e tom |
| **Publisher Agent** | Prepara comentário, links, hashtags e instruções |
| **Analytics Agent** | Analisa métricas e sugere próximos ajustes |

---

## 🖥️ Web Console

O BrandOS Web Console é uma interface local para operar o sistema pelo navegador.

Permite:

- visualizar semanas geradas;
- abrir peças individuais;
- copiar textos;
- alterar status por peça;
- marcar item como rascunho, pronto, publicado, ignorado ou precisa revisar;
- consultar projetos e links oficiais;
- acompanhar histórico;
- acessar o Asset Manager;
- gerar nova semana sem depender só de CMD.

Rodando localmente:

```bash
python -m app.web.server
```

Acesse:

```text
http://localhost:8000
```

---

## 🗂️ Asset Manager

O Asset Manager conecta cada peça de conteúdo aos seus arquivos visuais.

Cada publicação pode ter:

- imagens;
- PDFs;
- vídeos;
- templates;
- prompts visuais;
- arquivos fonte;
- versão final publicada.

A estrutura inicial usa pastas locais e `manifest.json` como fonte da verdade.

Exemplo:

```text
data/assets/
└── 2026-06-30-sentinela-rj-carrossel/
    ├── images/
    ├── slides/
    ├── pdf/
    ├── video/
    ├── source/
    └── manifest.json
```

---

## 🛠 Stack

| Camada / Layer | Tecnologia / Technology |
|---------------|--------------------------|
| Linguagem | Python 3.12+ |
| Web local | FastAPI + Uvicorn |
| Templates | Jinja2 |
| Frontend | HTML, CSS, JavaScript, Tailwind via CDN |
| IA | Google Gemini |
| Storage | Markdown + JSON |
| Knowledge base | `data/knowledge/` |
| Registry | `data/registry/` |
| Assets | `data/assets/` |

---

## 🚀 Instalação / Setup

Clone o repositório:

```bash
git clone https://github.com/simoesleandro/brandOS.git
cd brandOS
```

Crie e ative um ambiente virtual:

```bash
python -m venv venv
```

No Windows:

```bash
venv\Scripts\activate
```

No Linux/Mac:

```bash
source venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

---

## 🔐 Variáveis de Ambiente / Environment Variables

Crie um arquivo `.env` a partir do `.env.example`.

```env
GEMINI_API_KEY=coloque_sua_chave_aqui
BRANDOS_MODEL=gemini-1.5-flash
BRANDOS_TEMPERATURE=0.7
BRANDOS_MAX_OUTPUT_TOKENS=8192
```

> Nunca comite o arquivo `.env`.

---

## ▶️ Uso / Usage

### CLI

Gerar uma nova semana editorial:

```bash
python app/main.py weekly
```

### Web Console

Iniciar o painel local:

```bash
python -m app.web.server
```

Ou no Windows:

```bash
abrir-brandos.bat
```

Acesse:

```text
http://localhost:8000
```

---

## 🏗 Arquitetura / Architecture

```text
Entrada:
  Briefing opcional / histórico / projetos / links oficiais
        ↓
CMO Agent
        ↓
Content Strategist Agent
        ↓
Copywriter Agent
        ↓
Editor Agent
        ↓
Publisher Agent
        ↓
Arquivos gerados + registry + Web Console
        ↓
Revisão humana + publicação + métricas
```

Fontes principais:

```text
data/knowledge/   → contexto editorial, projetos, regras, tom de voz
data/registry/    → histórico estruturado de gerações e publicações
data/generated/   → posts, carrosséis e instruções geradas
data/assets/      → imagens, PDFs, vídeos, templates e prompts visuais
```

---

## 📁 Estrutura / Project Structure

```text
brandOS/
├── app/
│   ├── agents/
│   ├── core/
│   ├── prompts/
│   ├── workflows/
│   └── web/
├── config/
├── data/
│   ├── knowledge/
│   ├── inbox/
│   ├── generated/
│   ├── registry/
│   └── assets/
├── docs/
├── tests/
├── README.md
├── requirements.txt
└── .env.example
```

---

## 🗺 Roadmap

- [ ] Melhorar o Asset Manager.
- [ ] Gerar PDF a partir de imagens.
- [ ] Criar preview visual de carrosséis.
- [ ] Registrar métricas por publicação.
- [ ] Criar dashboard de performance.
- [ ] Adicionar agenda editorial.
- [ ] Evoluir storage para SQLite local.
- [ ] Exportar pacote final de publicação.
- [ ] Criar templates visuais reutilizáveis.
- [ ] Adicionar integração opcional com plataformas externas.

---

## 👤 Autor / Author

**Leandro Simões**

- GitHub: https://github.com/simoesleandro
- LinkedIn: https://linkedin.com/in/leandro-sim%C3%B5es-7a0b3537b
- Portfólio: https://simoesleandro.github.io/portfolio
