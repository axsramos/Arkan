# Instruções para implementação do Arkan

## Referências obrigatórias

- Leia [RFC-001](Documents/RFC/RFC-001.md) antes de implementar funcionalidade de produto.
- PLAN-001 e PLAN-002 descrevem apenas o fluxo já planejado para primeiro acesso, ingresso, desbloqueio e recuperação. Não os trate como autorização para implementar P2P, governança ou publicação.
- Decisões com status **Proposta** não são contrato definitivo. Não preencha lacunas de conceito com suposições: registre uma RFC, ADR ou questão em aberto.

## Invariantes do produto

- Rascunhos são locais e mutáveis; publicações são imutáveis. Uma edição cria nova versão ligada à anterior.
- A leitura restrita é escolha do autor, limita-se a 50% da publicação e exige autorização explícita para cada leitor.
- A entrega atual não aceita, processa, pré-visualiza, extrai ou interpreta anexos. A eventual inclusão de anexos é item de backlog e exige decisão e documentação aprovadas antes da implementação.
- A rede é privada, descentralizada e *offline-first*. Não introduza hospedagem central de conteúdo ou dependência de conta remota.
- Papéis são Guardião, Conselheiro e Membro. Regras completas de quórum, desempate e sucessão do Guardião ainda são pendências conceituais.

## Segurança

- Nunca exponha PIN, identidade privada, chave de dados, conteúdo de cofre, `ARKI v2`, `ARKR v2` ou material de envelope em resposta HTTP, log, exceção, teste, interface ou documentação. Credenciais portáteis só podem ser selecionadas ou salvas pelo diálogo nativo local; nunca pela interface web, por HTTP, área de transferência, impressão, telemetria ou outro canal.
- A API local deve permanecer vinculada a `127.0.0.1`; não exponha o FastAPI em LAN ou endereço público sem ADR aprovada.
- Valide formato, assinatura, autorização e versão antes de persistir ou retransmitir qualquer evento P2P.
- Preserve versionamento de formato de cofre e migrações explícitas. Não sobrescreva dados persistentes sem cópia recuperável.
- Tor, protocolo P2P, canonicalização de eventos e revogação de chaves ainda exigem decisão final; não apresente simulações como implementação concluída.

## Convenções de implementação

- Use português do Brasil, com acentuação correta, em textos de interface, documentação, comentários destinados a pessoas e mensagens de erro.
- Preserve os arquivos versionados em dist ao gerar uma nova distribuição. Crie uma nova pasta de versão; não substitua nem remova versões anteriores.
- Preserve identificadores, caminhos, protocolos, nomes de bibliotecas e termos técnicos em seus idiomas originais quando necessário.
- Mantenha o frontend sem acesso direto ao sistema de arquivos ou a segredos; operações sensíveis ficam no backend.
- Escreva testes para caminhos de sucesso, dados malformados, assinatura inválida, autorização insuficiente e recuperação de falhas.
- Não altere arquivos em `data/` nem inclua cofres, credenciais portáteis, chaves ou dados de teste sensíveis no repositório.

## Documentação

- Use `Documents/Template/RFC-Template.md` para propostas de produto ou protocolo e `Documents/Template/ADR-Template.md` para decisões arquiteturais.
- Atualize os vínculos entre RFC, ADR e plano ao criar um documento. Registre fatos comprovados separadamente de decisões propostas.
- Ao resolver uma questão em aberto, atualize o histórico do documento correspondente, em vez de apagar a rastreabilidade.
- Ao apresentar itens que exigem decisão do usuário ou da equipe, enumere-os para permitir resposta inequívoca a cada item e a manutenção explícita dos demais como questões em aberto.
- A cada nova versão, atualize `README.md` na mesma alteração: mantenha suas seis primeiras linhas, atualize os badges de versão e de build, revise requisitos, instruções e estrutura quando necessário e verifique o link do changelog.
- Registre mudanças relevantes em `Documents/Changelog/CHANGELOG.md` conforme Keep a Changelog e atribua a versão conforme Semantic Versioning antes de publicar uma distribuição.

## Instruções para respostas de avaliação de planos

O agente deve responder em português do Brasil e apresentar, nesta ordem:

1. **Decisão:** Aprovar, Aprovar com condições, Adiar ou Rejeitar.
2. **Escopo avaliado:** as partes do plano cobertas pela decisão.
3. **Evidências:** tabela com definição necessária, fonte, seção, status e conclusão de compatibilidade.
4. **Restrições verificadas:** invariantes e controles de segurança relevantes.
5. **Condições ou bloqueios:** itens numerados, com a ação documental ou técnica necessária para cada um.
6. **Próximo passo:** execução autorizada, verificação das condições ou criação/atualização de RFC, ADR ou plano.

O agente nunca deve expor segredos, material de cofre ou conteúdo restrito em sua análise. Quando a decisão for Adiar ou Rejeitar, deve preservar a rastreabilidade e encaminhar a decisão pendente para o documento apropriado, sem apagar o histórico existente.

## Autonomia de execução

A aprovação de uma RFC, ADR e atividade de PLAN com status **Pronto para execução**, **Pronto para execução parcial** ou **Aguardando dependências de implementação** autoriza sua implementação sem confirmação adicional da pessoa usuária, quando todas as dependências indicadas estiverem concluídas.

O agente deve:

- Ler a RFC, os ADRs e o PLAN aplicáveis antes de iniciar cada atividade.
- Executar as atividades na ordem de dependência, atualizar seus status e registrar evidências ao concluí-las.
- Tomar decisões locais de implementação quando não alterarem escopo, invariantes, modelo de segurança ou protocolo aprovado.
- Corrigir falhas de testes, validação e integração dentro do escopo da atividade atual, sem solicitar confirmação a cada tentativa.
- Prosseguir para a próxima atividade elegível quando os critérios de aceite da anterior forem atendidos.
- Atualizar o plano e a documentação de rastreabilidade ao concluir uma atividade, sem aguardar aprovação intermediária.

O agente deve interromper a execução e solicitar decisão explícita somente se:

1. Houver contradição entre RFC, ADR, PLAN ou código existente.
2. A implementação exigir comportamento de produto, mudança de escopo ou recurso fora do plano.
3. For necessário alterar criptografia, protocolo, regras de autorização, persistência incompatível ou garantias de segurança aprovadas.
4. Uma migração não puder preservar cópia recuperável.
5. For necessária infraestrutura externa, rede, LAN, P2P, conta remota, telemetria, publicação, commit, push ou outra ação externa não autorizada.
6. Um teste revelar risco de exposição de segredo, perda de dados ou violação de invariante.

Permissões solicitadas pelo ambiente de execução continuam exigindo a confirmação da pessoa usuária; esta regra não tenta contorná-las.
