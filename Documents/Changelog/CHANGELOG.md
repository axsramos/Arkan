# Changelog

Todas as mudanças relevantes deste projeto serão documentadas neste arquivo.

O formato segue [Keep a Changelog 1.0.0](https://keepachangelog.com/pt-BR/1.0.0/) e este projeto adota [Versionamento Semântico 2.0.0](https://semver.org/lang/pt-BR/).

## [Não publicado]

### Removido

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
