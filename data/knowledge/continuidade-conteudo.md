# Continuidade de conteúdo

Este arquivo ajuda o BrandOS a não repetir temas e a sugerir sequência lógica para posts futuros.

## Regra principal

Cada post deve parecer uma continuação natural da construção pública dos projetos.

Não repetir o mesmo ângulo em semanas seguidas.

---

## Sequência recomendada para projetos técnicos

Para cada projeto, alternar entre estes tipos de post:

1. Problema
Explicar o problema real que motivou o projeto.

2. Solução
Mostrar como o sistema resolve ou tenta resolver.

3. Bastidor técnico
Mostrar decisão de arquitetura, stack, bug, trade-off ou implementação.

4. Produto
Mostrar dashboard, fluxo, tela, módulo ou resultado.

5. Aprendizado
Explicar o que foi aprendido construindo.

6. Limite
Mostrar o que ainda não funciona, riscos ou próximos passos.

7. Continuidade
Mostrar o que vem depois.

---

## Sentinela RJ — sequência sugerida

Já publicado/pronto:
- Post de impacto com dashboard dark e número forte.
- Carrossel “Dados públicos precisam de análise”.

Próximos ângulos:
1. Como o Sentinela RJ coleta dados do PNCP.
2. Por que normalizar dados públicos dá mais trabalho do que parece.
3. Como diferenciar anomalia de acusação.
4. O papel da IA como triagem.
5. Arquitetura do pipeline.
6. Como o dashboard ajuda a priorizar análise.
7. O que eu faria diferente se recomeçasse o projeto.

Evitar na próxima semana:
- Repetir “dados públicos precisam de análise” com as mesmas palavras.
- Repetir o mesmo argumento da IA como apoio sem trazer bastidor novo.

---

## Hermes Lite — sequência sugerida

Ângulos:
1. Por que um chat genérico não resolve tudo.
2. Como separar agentes por contexto.
3. Roteamento de modelos: local, Groq, Gemini.
4. Integração Telegram.
5. MCP com Claude/Cursor.
6. Memória persistente.
7. O que aprendi tentando criar um assistente pessoal real.

---

## sys-health — sequência sugerida

Ângulos:
1. Por que construí um dashboard de saúde pessoal.
2. Como organizei dados de nutrição, treino e wearable.
3. Supabase como backend.
4. PWA e uso diário.
5. IA Coach com limites.
6. Privacidade e dados pessoais.
7. O que esse projeto me ensinou sobre produto.

---

## Pulso Eleitoral — sequência sugerida

Ângulos:
1. O problema das pesquisas eleitorais dispersas.
2. Coleta automatizada com Playwright.
3. Normalização de candidatos e institutos.
4. Dashboard de tendências.
5. IA para análise de cenário.
6. Limitações de fonte.
7. Como comunicar dados eleitorais sem virar torcida.

---

## Veritas Eleitoral — sequência sugerida

Ângulos:
1. Por que fact-checking precisa de rastreabilidade.
2. Como uma claim vira dossiê.
3. Agentes no pipeline.
4. Evidências auditáveis.
5. Por que IA não automatiza a verdade.
6. Reduzindo escopo do EleitorAI para um MVP.
7. O que aprendi com LangGraph.

---

## TechPulse — sequência sugerida

Ângulos:
1. Excesso de informação técnica.
2. Sinal vs ruído.
3. Pipeline de ingestão.
4. Classificação com IA local.
5. Deduplicação.
6. Dashboard de leitura.
7. Como isso ajuda meu estudo de tecnologia.

---

## Regra anti-repetição

Antes de gerar uma nova semana, o BrandOS deve consultar:

- data/knowledge/historico-postagens.md
- data/registry/publication-log.md
- data/registry/publication-log.json

E evitar repetir:
- mesmo título;
- mesmo gancho;
- mesmo projeto por muitas semanas seguidas;
- mesmo formato visual;
- mesma conclusão.

---

## Regra de continuidade

Quando um projeto já foi usado na semana anterior, o BrandOS pode continuar nele apenas se trouxer um ângulo novo.

Exemplo:
Semana 1:
Sentinela RJ — problema dos dados públicos.

Semana 2:
Sentinela RJ — bastidor técnico da coleta PNCP.

Semana 3:
Sentinela RJ — arquitetura do pipeline.

Isso é continuidade boa.

Continuidade ruim:
Repetir três vezes que “dados públicos precisam de análise”.
