# Changelog

Todas as mudanças relevantes deste projeto serão documentadas neste arquivo.

O formato segue [Keep a Changelog 1.0.0](https://keepachangelog.com/pt-BR/1.0.0/) e este projeto adota [Versionamento Semântico 2.0.0](https://semver.org/lang/pt-BR/).

## [Não publicado]

### Alterado

- O campo Conteúdo de novos artigos agora oferece barra de formatação Markdown, prévia rápida local e renderização segura na revisão e no Acervo.
- O Acervo agora exige o fluxo local `Rascunho → Revisão → Publicação`; a prévia é somente leitura, a exclusão só é permitida no rascunho e a publicação requer confirmação explícita.
- A base local foi atualizada para o formato 11, com cópia recuperável antes da migração dos rascunhos existentes.

- Substituído o favicon genérico por um emblema geométrico plano do Arkan, aplicado à interface no navegador e ao empacotamento Windows futuro.
- Restaurada a janela de console visível como canal direto de execução e diagnóstico local.
- Atualizado o diálogo nativo de PIN com a identidade visual da aplicação, mantendo a coleta exclusivamente local.
- Substituído o comando de bloqueio da interface por encerramento confirmado da cópia local.
- Simplificado o diálogo de PIN para uma única janela Tk visível, independente do console e sem raiz oculta ou coordenação entre threads.
- Eliminada a derivação duplicada do PIN durante o desbloqueio; a chave de dados é reutilizada para abrir a identidade e a base local.
- Adicionada a tela Configurações, com alternância imediata entre os temas Claro e Escuro e persistência local em JSON versionado.

### Removido

- Bloqueio manual da interface que mantinha a aplicação local em execução.
- Inicializador legado, dependência sem uso e duplicidades internas sem rota de execução.
- Suporte parcial a anexos, incluindo esquema, processamento de intercâmbio e migrações inativas.

### Alterado

- Formato local atualizado para remover a tabela legada de anexos por migração com cópia recuperável.

### Segurança

- Proteção de memória do SQLCipher ativada para a abertura da base local fora do Windows.
- No Windows, `cipher_memory_security` foi desativado conforme [ADR-004](../ADR/ADR-004.md) para evitar o crash nativo de SQLCipher durante o desbloqueio.
- Falhas nativas da derivação Argon2 são convertidas em erro controlado, sem expor o PIN.

### Corrigido

- Validado o desbloqueio ponta a ponta da distribuição Windows recompilada, com o processo e o painel local preservados após a confirmação do PIN.
- Após confirmar o encerramento, o painel é substituído por uma tela local que informa o término da cópia e orienta a executar o aplicativo novamente.

## [1.0.0] - 2026-11-14

### Adicionado

- Aplicação local para ativação de rede, ingresso, desbloqueio e recuperação por credencial portátil.
- Rascunhos locais, publicações assinadas, comentários, acervo e intercâmbio manual de conteúdo por arquivos `ARKX v2`.
- Distribuição portátil Windows em `dist/Arkan-1.0.0`.

### Segurança

- Cofre local protegido por PIN, armazenamento SQLCipher e migrações com cópia recuperável.
- API vinculada a `127.0.0.1`, sessões locais efêmeras e diálogos nativos para PIN e arquivos sensíveis.

<!--
Ao publicar uma versão, mova as mudanças relevantes de "Não publicado" para
uma seção "## [MAJOR.MINOR.PATCH] - AAAA-MM-DD". Mantenha as versões em ordem
cronológica decrescente e use somente as categorias que possuírem alterações.
-->
