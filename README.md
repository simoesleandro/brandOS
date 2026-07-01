# BrandOS

O **BrandOS** é um sistema operacional para marcas e criadores de conteúdo que automatiza, gerencia e organiza publicações de forma centralizada. Ele resolve a dispersão de fluxos de trabalho (ideias espalhadas no Notion, prompts perdidos e arquivos visuais desorganizados no desktop), trazendo pesquisa, redação e assets visuais (Asset Manager) para dentro de uma só plataforma orientada a inteligência artificial.

## 🚀 Funcionalidades Atuais

- **Workflow Semanal (CLI)**: Motor de geração focado na produção automatizada a partir de briefings curtos da caixa de entrada (`data/inbox`).
- **Web Console**: Painel de gerenciamento leve (FastAPI + Jinja2) para revisar peças textuais e rastrear o status real de cada artefato (Draft, Pronto, Revisar, Ignorar, Publicado).
- **Asset Manager**: Camada para armazenar imagens, PDFs, vídeos, templates e prompts visuais para cada peça, conectando o texto da postagem aos seus arquivos finais no disco.
- **Arquitetura de Agentes**: Sistema inteligente integrado a LLMs modernos para agir como redator e editor-chefe baseado no conhecimento da marca (`data/knowledge`).

## 🛠️ Stack Tecnológica

- **Backend**: Python 3.12, FastAPI, Uvicorn, Jinja2, python-multipart
- **Frontend**: HTML5, Vanilla JavaScript, CSS Puro e Tailwind via CDN
- **LLM**: Google Gemini (via `google-genai`)
- **DB/Storage**: 100% *File-based* (JSON, Markdown) sem banco de dados externo, para máxima portabilidade e controle de dados locais.

## ⚙️ Como Instalar

1. Clone o repositório:
```bash
git clone https://github.com/simoesleandro/brandos.git
cd brandos
```

2. Crie e ative um ambiente virtual:
```bash
python -m venv venv
# No Windows
venv\Scripts\activate
# No Linux/Mac
source venv/bin/activate
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

## 🔐 Configuração do .env

Copie o arquivo `.env.example` e renomeie para `.env`. Configure com suas chaves:

```env
BRANDOS_API_KEY=coloque_sua_chave_aqui
BRANDOS_MODEL=gemini-1.5-flash
BRANDOS_TEMPERATURE=0.7
BRANDOS_MAX_OUTPUT_TOKENS=8192
```

> **Aviso de Segurança**: O arquivo `.env` é ignorado no repositório. Nunca comite chaves reais!

## 🚀 Como Rodar

### Rodando o Motor CLI (Geração Automática)
Coloque um texto guia com o tema da semana (ex: `briefing.md`) na pasta `data/inbox/`. Em seguida, execute:
```bash
python main.py run-weekly
```
Os arquivos `.md` serão gerados em `data/generated/` e vinculados ao registro principal.

### Rodando o Web Console (Gestão Visual)
Para acessar o painel administrativo, visualizar as métricas de publicação e utilizar o Asset Manager:
```bash
python main.py server
```
Acesse `http://localhost:8000` no seu navegador. A interface te permite navegar pelas semanas geradas, atualizar os status e subir arquivos visuais, mantendo o histórico de trabalho unificado.

## 🗺️ Roadmap (Próximas Fases)

- [ ] Automação de Publicação: Integração via APIs sociais (LinkedIn, Twitter).
- [ ] Geração dinâmica de PDF a partir de templates visuais de slides.
- [ ] Captura de métricas diretamente da plataforma alvo na aba de Métricas.
- [ ] Pipeline de automação de vídeo (exportação em massa).

## 📊 Status do Projeto

Versão atual: **Alpha** (Desenvolvimento Ativo). 
A estrutura central de gestão e o modelo de AI text-first estão rodando e funcionais localmente.
