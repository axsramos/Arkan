# PLAN-004: Markdown no editor de artigos

- **Status:** Concluído
- **Responsável:** Equipe Arkan
- **Data de criação:** 2026-11-24
- **Última atualização:** 2026-11-24
- **Data de início real:** 2026-11-24
- **Data de conclusão real:** 2026-11-24
- **Objetivo:** Oferecer formatação Markdown segura no rascunho de artigos sem remover a revisão obrigatória.
- **RFCs relacionadas:** [RFC-005](../RFC/RFC-005.md)

## 1. Resultado esperado

Uma pessoa pode inserir Markdown pelo teclado ou pela barra do campo `Conteúdo`, ver uma prévia instantânea sem salvar e revisar a mesma formatação antes de publicar.

### Fora do escopo

- Ferramentas Markdown para título ou comentário.
- Interpretação de HTML, anexos ou novos formatos de intercâmbio.

## 2. Atividades

| ID | Atividade | Status | Evidência |
|---|---|---|---|
| 4.1 | Implementar renderizador Markdown restrito e seguro | Concluída | `frontend/components/content/markdown.js` escapa HTML e limita links. |
| 4.2 | Adicionar barra e prévia rápida ao editor de artigo | Concluída | `ContentComposerComponent.js` preserva a seleção e não salva ao abrir a prévia. |
| 4.3 | Aplicar a visualização à revisão e ao Acervo | Concluída | A formatação é consistente antes e depois da publicação. |
| 4.4 | Validar formatação e entradas não confiáveis | Concluída | `node --experimental-default-type=module tests/test_frontend_markdown.mjs`. |

## 3. Decisões locais

| Data | Decisão | Motivo |
|---|---|---|
| 2026-11-24 | Usar SVG inline em vez de fonte de ícones | Não há fonte local e não se adiciona dependência remota ao aplicativo offline. |
| 2026-11-24 | Usar índices de seleção em vez de marcador para `replace` | Evita colisões ou persistência acidental de marcadores no conteúdo. |

## 4. Validação final

- [x] Sintaxe JavaScript verificada nos componentes modificados.
- [x] Markdown formatado e HTML malicioso cobertos por teste de frontend.
- [x] A prévia rápida permanece local e a revisão continua obrigatória.

**Comando principal:**

```text
node --experimental-default-type=module tests/test_frontend_markdown.mjs
```

## 5. Histórico

| Data | Alteração | Motivo | Responsável |
|---|---|---|---|
| 2026-11-24 | Plano criado e concluído | Implementar RFC-005 | Equipe Arkan |
