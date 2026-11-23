# PLAN-[número]: [Título da entrega]

- **Status:** Rascunho | Pronto para execução | Em andamento | Bloqueado | Em revisão | Concluído | Cancelado
- **Responsável:** [Pessoa ou equipe]
- **Data de criação:** [AAAA-MM-DD]
- **Última atualização:** [AAAA-MM-DD]
- **Data de início prevista:** [AAAA-MM-DD ou "Não definida"]
- **Data de conclusão prevista:** [AAAA-MM-DD ou "Não definida"]
- **Data de início real:** [AAAA-MM-DD ou "Não iniciada"]
- **Data de conclusão real:** [AAAA-MM-DD ou "Não concluída"]
- **Objetivo:** [Resultado concreto que deve existir ao final do plano]
- **RFCs relacionadas:** [Links ou "Nenhuma"]
- **ADRs relacionadas:** [Links ou "Nenhuma"]
- **Issue, ticket ou solicitação:** [Link ou "Não se aplica"]

> **Como preencher:** Use este documento para orientar a execução de uma entrega. O plano pode existir sem RFC ou ADR. Preencha campos sem valor com "Não se aplica", "Nenhuma" ou "Não definido", conforme o caso. Não invente informações ausentes. Referencie RFCs e ADRs quando aplicável, sem copiar suas decisões.

## 1. Resultado esperado

[Descreva, em poucas frases, o que será entregue e como o comportamento final será percebido.]

### Fora do escopo

- [Resultado ou alteração que não será tratado neste plano]

## 2. Contexto de execução

- **Estado atual:** [Como o sistema funciona antes da mudança]
- **Ponto de entrada:** [Arquivo, módulo, rota, comando, tela ou processo]
- **Componentes afetados:** [Arquivos, módulos, serviços, banco de dados ou integrações]
- **Restrições:** [Compatibilidade, prazo, dependências, padrões ou limites]
- **Referências úteis:** [Documentação, código, RFC, ADR, protótipo ou ticket]
- **Diagrama relacionado:** [Link ou "Não se aplica"]

> **Como preencher:** Forneça o contexto mínimo necessário para que outra pessoa ou uma IA consiga começar sem redescobrir o problema. Prefira caminhos, símbolos, contratos e exemplos concretos.

> **Diagramas:** Para uma visão arquitetural, referencie o diagrama C4 definido na RFC ou ADR. No Plano, detalhe somente o recorte necessário para executar a atividade. Use a camada de Código apenas quando for indispensável; não replique diagramas já existentes.

## 3. Pré-condições e dependências

- [ ] [Acesso, ferramenta, ambiente ou decisão necessária]
- [ ] [Dependência de outro plano, serviço ou equipe]
- [ ] [RFC ou ADR que precisa estar aprovada, quando aplicável]

**Bloqueios atuais:** [Nenhum | Descrição do bloqueio, responsável e próximo passo]

## 4. Atividades

Execute as atividades na ordem indicada, salvo quando uma dependência permitir paralelismo explícito.

### 4.1 [ID] [Verbo + resultado da atividade]

- **Status:** Não iniciada | Em andamento | Bloqueada | Em revisão | Concluída | Cancelada
- **Objetivo:** [Resultado desta atividade]
- **Pré-requisitos:** [IDs de atividades ou "Nenhum"]
- **Entrada:** [Dados, estado ou artefato necessário]
- **Arquivos e símbolos permitidos:** [Caminhos, classes, funções, tabelas ou endpoints]
- **Arquivos ou áreas proibidos:** [O que não deve ser alterado ou "Nenhum"]
- **Ação:**
	1. [Passo objetivo e ordenado]
	2. [Passo objetivo e ordenado]
- **Saída:** [Código, configuração, dado ou artefato produzido]
- **Decisão local:** [Escolha específica desta tarefa ou "Nenhuma"]
- **Validação:** `[Comando, teste, consulta ou verificação manual]`
- **Concluída quando:** [Critério observável e verificável]
- **Em caso de falha:** [Ação corretiva, bloqueio ou informação a registrar]
- **Evidência:** [Link para PR, commit, saída do comando, screenshot ou observação]

> **Como preencher:** Duplique este bloco para cada atividade. Uma atividade deve produzir uma mudança verificável e caber em uma unidade de trabalho pequena. Use verbos no infinitivo, informe entradas e saídas, limite os arquivos alteráveis e não misture implementação, revisão e implantação quando puderem ser verificadas separadamente.

## 5. Decisões e dúvidas de execução

### Decisões locais

| Data | Decisão | Motivo | Atividade | Responsável |
|---|---|---|---|---|
| [AAAA-MM-DD] | [Escolha específica da execução] | [Motivo objetivo] | [ID] | [Nome] |

### Questões que exigem RFC ou ADR

- [ ] [Questão de negócio que deve ser registrada ou decidida em RFC]
- [ ] [Questão técnica de escopo arquitetural que deve ser registrada ou decidida em ADR]
- [ ] [Questão pendente que não bloqueia a execução]

> **Como preencher:** Uma decisão local resolve apenas a atividade atual. Se ela criar uma regra de negócio, mudar o produto, estabelecer um padrão técnico reutilizável ou afetar vários componentes, pare e registre a necessidade de RFC ou ADR.

## 6. Validação final

- [ ] [Critério funcional verificável]
- [ ] [Teste automatizado ou manual executado]
- [ ] [Teste de regressão ou compatibilidade, quando aplicável]
- [ ] [Revisão de segurança, dados ou operação, quando aplicável]
- [ ] [Documentação ou referência atualizada, quando aplicável]

**Comandos principais:**

```text
[Comandos de instalação, lint, teste, build ou verificação]
```

**Resultado observado:** [Resumo da execução e evidências]

## 7. Encerramento

- **Status final:** [Concluído | Concluído com pendências | Cancelado]
- **Entrega:** [Link para PR, release, ambiente ou outro resultado]
- **Pendências transferidas:** [Tickets ou planos seguintes, ou "Nenhuma"]
- **Observações:** [Informações úteis para manutenção ou próximos passos]

## 8. Histórico do plano

| Data | Alteração | Motivo | Responsável |
|---|---|---|---|
| [AAAA-MM-DD] | [Descrição da alteração] | [Motivo] | [Nome] |