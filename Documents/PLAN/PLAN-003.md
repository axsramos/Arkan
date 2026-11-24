# PLAN-003: Fluxo local de rascunho, revisão e publicação

- **Status:** Concluído
- **RFC de origem:** [RFC-001](../RFC/RFC-001.md) e [RFC-002](../RFC/RFC-002.md)
- **Data de criação:** 2026-11-24
- **Última atualização:** 2026-11-24

## 1. Objetivo

Impor no Acervo o fluxo `RASCUNHO → EM_REVISAO → PUBLICADO`, mantendo as duas primeiras etapas exclusivamente locais e exigindo prévia e confirmação antes da publicação imutável.

## 2. Atividades

| ID | Atividade | Dependência | Status | Evidência |
|---|---|---|---|---|
| 3.1 | Persistir o estado local de revisão com migração recuperável | RFC-002 §5.4 | Concluída | Formato local 11; cópia `backup-v10` preservada antes da alteração. |
| 3.2 | Restringir as transições e exclusões no backend | 3.1 | Concluída | Publicação exige `EM_REVISAO`; exclusão aceita somente em `RASCUNHO`. |
| 3.3 | Exibir editor, prévia e confirmação no Acervo | 3.2 | Concluída | Prévia somente leitura, retorno ao rascunho e confirmação explícita implementados. |
| 3.4 | Cobrir fluxo e migração por testes | 3.1–3.3 | Concluída | Testes de domínio e armazenamento atualizados. |

## 3. Critérios de aceite

- [x] Um rascunho salvo pode ser encaminhado para revisão local.
- [x] A revisão mostra o conteúdo sem campos de edição e permite retornar ao rascunho.
- [x] Não é possível excluir em revisão nem publicar sem antes entrar em revisão.
- [x] A confirmação explícita produz publicação imutável; somente publicações participam da exportação.
- [x] A migração preserva uma cópia recuperável da base anterior.

## 4. Validação final

**Comando principal:**

```text
.\venv\Scripts\python.exe -m unittest discover -s tests
```

**Resultado observado:** A suíte confirma a transição obrigatória para revisão, o bloqueio de exclusão em revisão, o retorno ao rascunho, a migração com cópia recuperável e o salvamento de novo rascunho após a migração.

## 5. Histórico

| Data | Alteração | Motivo | Responsável |
|---|---|---|---|
| 2026-11-24 | Plano criado e executado | Formalizar e entregar o fluxo de publicação irreversível | Equipe Arkan |
