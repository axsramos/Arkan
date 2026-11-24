# Changelog

Todas as mudanças relevantes deste projeto serão documentadas neste arquivo.

O formato segue [Keep a Changelog 1.0.0](https://keepachangelog.com/pt-BR/1.0.0/) e este projeto adota [Versionamento Semântico 2.0.0](https://semver.org/lang/pt-BR/).

## [Não publicado]

### Alterado

- Substituído o favicon genérico por um emblema geométrico plano do Arkan, aplicado à interface no navegador e ao empacotamento Windows futuro.
- Configurado o empacotamento Windows para iniciar sem janela de console; a interface local continua aberta no navegador padrão.
- Atualizado o diálogo nativo de PIN com a identidade visual da aplicação, mantendo a coleta exclusivamente local.
- Substituído o comando de bloqueio da interface por encerramento confirmado da cópia local.

### Removido

- Bloqueio manual da interface que mantinha a aplicação local em execução.
- Inicializador legado, dependência sem uso e duplicidades internas sem rota de execução.
- Suporte parcial a anexos, incluindo esquema, processamento de intercâmbio e migrações inativas.

### Alterado

- Formato local atualizado para remover a tabela legada de anexos por migração com cópia recuperável.

### Segurança

- Proteção de memória do SQLCipher ativada para a abertura da base local.

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
