# Arkan

<img src="https://img.shields.io/badge/license-owner-tomato" alt="Licença proprietária">
<img src="https://img.shields.io/badge/version-1.0.0-blue" alt="Versão 1.0.0">
<img src="https://img.shields.io/badge/build-20261114113154-orange" alt="Build 20261114113154">

O Arkan é um aplicativo local e offline-first para criar, preservar e compartilhar manualmente artigos entre membros de uma rede privada. A primeira versão não depende de conta remota, hospedagem central, LAN, P2P ou sincronização automática.

## Requisitos técnicos

- Windows, pois os fluxos de PIN e arquivos usam diálogos nativos locais.
- Python 3.11 ou superior, com `pip` e `venv` disponíveis.
- Git para clonar o repositório.
- Navegador padrão instalado, aberto automaticamente para a interface local.
- As dependências Python são definidas em [requirements.txt](requirements.txt): FastAPI, Uvicorn, Pydantic, Cryptography, Argon2, CBOR, SQLCipher, Zstandard e PyInstaller.
- A base de dados é SQLite cifrada com SQLCipher, fornecida pela dependência `sqlcipher3-wheels`; não há base de dados ou serviço externo para configurar.
- O empacotamento da distribuição Windows usa PyInstaller, já listado nas dependências do projeto.

## Clonar e executar em desenvolvimento

O endereço definitivo do repositório ainda será publicado. Até lá, use o endereço-base do GitHub com um nome de repositório de exemplo:

```powershell
git clone https://github.com/axsramos/<NOME-DO-REPOSITORIO>.git Arkan
Set-Location Arkan
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

O navegador padrão abre automaticamente em uma porta disponível de `127.0.0.1`. Para encerrar, use `Ctrl+C`. Caso PowerShell bloqueie a ativação, execute os comandos Python diretamente com `.\venv\Scripts\python.exe`.

## Estrutura do projeto

```text
Arkan/
├── backend/                 API local, cofre, armazenamento e regras de domínio
├── frontend/                Interface estática Vue e recursos locais
├── tests/                   Testes automatizados
├── Documents/
│   ├── ADR/                 Decisões arquiteturais aceitas
│   ├── Backlog/             Itens futuros fora da entrega atual
│   ├── Changelog/           Registro de alterações por versão
│   ├── RFC/                 Especificações vigentes do produto e protocolo
│   └── Template/            Modelos de documentos
├── dist/                    Distribuições portáteis versionadas, quando geradas
├── data/                    Estado local cifrado gerado em execução, não versionado
├── main.py                  Inicializador local em 127.0.0.1
└── requirements.txt         Dependências Python fixadas
```

## Distribuição portátil

Em Windows, copie uma pasta de versão em `dist` para um pen drive ou outra pasta local e execute `Arkan.exe`. A distribuição não inclui código-fonte, Python ou instalação de dependências.

O diretório `data` será criado ao lado do executável durante a ativação. Ele contém o estado local cifrado. Não copie, publique ou versione esse diretório; use os fluxos de exportação e recuperação do aplicativo.

## Testes e distribuição

Execute os testes com:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests
```

Para compilar:

```powershell
.\venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --name Arkan --add-data "frontend;frontend" main.py
```

O empacotamento gera `dist\Arkan.exe`. Para publicar, mova-o para uma nova pasta versionada, por exemplo `dist\Arkan-1.0.0`, e inclua o arquivo de instruções. Nunca substitua uma pasta de versão existente.

## Versões e changelog

O projeto segue [Versionamento Semântico 2.0.0](https://semver.org/lang/pt-BR/): incremente a versão maior para mudanças incompatíveis, a menor para funcionalidades compatíveis e a de correção para falhas compatíveis.

As mudanças relevantes de cada versão devem ser registradas no [changelog](Documents/Changelog/CHANGELOG.md), estruturado segundo [Keep a Changelog 1.0.0](https://keepachangelog.com/pt-BR/1.0.0/). Atualize o changelog e os badges de versão e build deste README ao preparar uma nova versão.

## Regras gerais

- Rascunhos são locais e mutáveis; publicações são imutáveis e novas edições criam versões.
- Artigos e comentários publicados são compartilhados apenas por exportação e importação manual.
- A entrega atual não aceita anexos.
- PIN, chaves, cofre e credenciais portáteis não podem aparecer na interface web, HTTP, logs, testes ou documentação.
- O aplicativo permanece local e usa somente `127.0.0.1`.

Consulte [AGENTS.md](AGENTS.md), [RFC-001](Documents/RFC/RFC-001.md), [RFC-002](Documents/RFC/RFC-002.md) e os [ADRs](Documents/ADR) para os requisitos completos.
