# Guia de uso do Arkan

- **Versão de referência:** 1.1.1
- **Atualizado em:** 26 de novembro de 2026
- **Base:** [RFC-001](RFC/RFC-001.md), [RFC-002](RFC/RFC-002.md) e [changelog](Changelog/CHANGELOG.md)

## 1. O que é o Arkan

O Arkan é um aplicativo local para uma rede privada criar, preservar e compartilhar artigos e comentários. Cada pessoa trabalha em sua própria cópia do aplicativo e mantém seu próprio acervo local.

O compartilhamento não é automático: uma pessoa exporta um arquivo de integração e outra o importa. Assim, a rede não depende de conta remota, serviço em nuvem, conexão constante ou servidor central. A pessoa responsável pela rede e seus membros devem combinar, fora do aplicativo, como e quando os arquivos serão transferidos.

## 2. Antes de começar

Cada cópia do Arkan pertence a uma única rede e é usada por uma única pessoa. Não há perfis múltiplos, sessões simultâneas nem troca de rede depois da ativação.

Ao abrir o aplicativo pela primeira vez, escolha uma das opções abaixo:

1. **Criar uma nova rede:** para iniciar uma rede privada e tornar-se seu Guardião.
2. **Ingressar com arquivo recebido:** para entrar em uma rede já criada, com um ingresso fornecido pelo Guardião.
3. **Recuperar com credencial:** para restaurar seu acesso após esquecer o PIN ou para ativar uma nova cópia sua.

O PIN e os arquivos de credencial são tratados somente pelos diálogos locais do sistema operacional. Guarde a credencial de recuperação em local seguro. Ela é necessária para recuperar o acesso; o Guardião e outros membros não conseguem recuperar o PIN de outra pessoa.

## 3. Papéis na rede

Na versão atual, há dois papéis: **Guardião** e **Membro**.

| Papel | Responsabilidades e permissões |
| --- | --- |
| **Guardião** | Cria a rede, é seu primeiro membro, convida novos membros, acompanha a lista de membros, pode revogar membros e preserva o acervo consolidado de publicações que importou. Também escreve, publica, exporta e importa conteúdo como qualquer membro ativo. |
| **Membro** | Ingressa na rede por convite, cria rascunhos, publica artigos e comentários, cria novas versões de suas próprias publicações, consulta o acervo e troca conteúdo por exportação e importação manual. |

### 3.1 Regras do Guardião

- O Guardião é único na versão atual. Seu papel e sua credencial não podem ser transferidos para outro membro.
- Se o Guardião deixar de operar, a rede continua permitindo o uso das publicações já disponíveis, mas não será possível ingressar novos membros nem revogar membros.
- O Guardião pode revogar um membro. Depois de receber uma revogação válida, a cópia revogada não pode criar, publicar, importar ou exportar conteúdo; ela mantém apenas a leitura dos próprios artigos.
- A revogação não apaga publicações feitas antes dela. Conteúdo anterior continua preservável e compartilhável na rede.

### 3.2 Regras do Membro

- O convite para ingresso é válido por sete dias. O Guardião deve entregar o arquivo de ingresso à pessoa certa por um meio combinado fora do Arkan.
- O Membro é responsável por sua cópia, PIN e credencial de recuperação. Uma credencial de recuperação permite restaurar a identidade em uma nova cópia; por isso, não deve ser compartilhada.
- Evite usar duas cópias suas em paralelo. Se for substituir o dispositivo ou começar a usar uma cópia de reserva, deixe de usar a anterior para reduzir conflitos operacionais.

## 4. Fluxo esperado de uso

### 4.1 Criar uma rede

1. Abra o Arkan e escolha **Criar uma nova rede**.
2. Informe o pseudônimo que representará o Guardião e defina o PIN no diálogo local.
3. Salve a credencial de recuperação pelo diálogo do sistema operacional.
4. Após o desbloqueio, use o menu **Membros** para preparar ingressos para as pessoas que participarão da rede.
5. Entregue cada ingresso diretamente ao novo membro por um canal acordado pelo grupo.

### 4.2 Ingressar em uma rede existente

1. Receba o ingresso do Guardião fora do aplicativo.
2. Abra o Arkan e escolha **Ingressar com arquivo recebido**.
3. Informe o pseudônimo combinado, selecione o ingresso pelo diálogo local e defina seu PIN.
4. Salve sua credencial de recuperação quando o sistema solicitar.
5. Ao concluir, sua cópia estará vinculada à rede e pronta para consultar o acervo e produzir conteúdo.

### 4.3 Desbloquear e recuperar o acesso

No uso cotidiano, abra o aplicativo e informe o PIN no diálogo local. Caso o PIN seja esquecido, escolha a recuperação, informe seu pseudônimo e selecione a credencial de recuperação salva anteriormente.

Na mesma cópia, a recuperação preserva o acervo local, os rascunhos e o conteúdo ainda não exportado. Em uma cópia nova, a identidade é restaurada, mas rascunhos e conteúdos que nunca foram exportados da cópia anterior podem não estar disponíveis. Para recompor o acervo compartilhado, importe arquivos recebidos de outros membros.

## 5. Criar e publicar conteúdo

O Arkan separa claramente o trabalho em andamento da publicação definitiva. Todo artigo e comentário segue o fluxo abaixo:

```text
Rascunho → Revisão → Publicação
```

1. No menu **Publicar**, escreva um artigo ou comentário. Artigos podem usar a barra de formatação Markdown e a prévia rápida local.
2. Selecione **Salvar rascunho**. O rascunho fica somente na sua cópia e pode ser editado ou excluído.
3. Selecione **Revisar**. A revisão mostra uma prévia somente leitura; se precisar alterar algo, volte ao rascunho.
4. Após conferir o conteúdo, avance para a publicação e confirme explicitamente a ação.

Depois de publicada, uma publicação é permanente: não pode ser editada ou apagada. Para corrigir ou atualizar um artigo próprio, abra-o e escolha **Criar nova versão**. A nova versão preserva o vínculo com a anterior e a autoria permanece com o criador do artigo. Comentários também são publicados de forma definitiva e pertencem exclusivamente a quem os criou.

## 6. Consultar e organizar o Acervo

O menu **Acervo** reúne as publicações conhecidas por sua cópia. Nele, é possível:

- buscar por título ou marcador;
- filtrar por publicações próprias ou de outros membros, categoria, autor e data;
- ordenar por mais recentes ou mais antigas;
- abrir artigos, ler comentários conhecidos e criar um comentário em um artigo disponível;
- criar uma nova versão de um artigo de sua autoria;
- atribuir categoria e badges aos artigos para organizar seu acervo local;
- alternar entre os temas Claro e Escuro em **Configurações**.

Categorias e badges são pessoais e locais: não alteram a publicação original e não são enviados em exportações. Duas pessoas podem classificar o mesmo artigo de formas diferentes.

Uma publicação pode aparecer como **Completa**, quando seu conteúdo está disponível na cópia, ou como **Resumo**, quando há somente seu cabeçalho ou quando o conteúdo foi removido localmente. O cabeçalho continua no acervo para preservar a referência à publicação.

Para liberar espaço, um Membro pode remover apenas o conteúdo local de publicações de outros autores; a ação não é enviada à rede. O conteúdo pode ser permitido novamente para importação posterior. O Guardião preserva em sua cópia consolidada os itens que já importou.

## 7. Exportar e importar publicações

O intercâmbio de conteúdo é manual e acontece no **Acervo**.

### Exportar

1. Selecione **Exportar**.
2. Defina, quando necessário, o período desejado ou marque a opção para incluir somente itens ainda não exportados nesta cópia.
3. Salve o arquivo pelo diálogo local e entregue-o ao destinatário por um meio escolhido pelo grupo.

O registro de itens já exportados serve apenas à sua cópia; ele não indica quem recebeu o arquivo. A exportação pode ser resumida, contendo informações de identificação e cabeçalhos, ou completa, incluindo os conteúdos disponíveis.

### Importar

1. Receba um arquivo de integração de uma pessoa da rede.
2. No **Acervo**, selecione **Importar ARKX** e escolha o arquivo pelo diálogo local.
3. O Arkan verifica se a origem, a autorização e a integridade são compatíveis com a rede antes de aceitar o conteúdo.
4. Itens já existentes não são duplicados; os demais itens válidos podem ser incorporados ao acervo.

Como o uso é offline, uma cópia conhece apenas as atualizações que recebeu por arquivos. Portanto, mantenha uma rotina combinada de troca e importação com o grupo para atualizar o acervo e os estados de membros.

## 8. Recursos disponíveis na versão 1.1.1

- criação local de rede, ingresso por convite e recuperação por credencial portátil;
- proteção de acesso por PIN e armazenamento local protegido;
- gestão de membros pelo Guardião, com criação de ingressos e revogação;
- artigos e comentários com autoria, publicação definitiva e novas versões para artigos próprios;
- rascunhos locais, revisão obrigatória e confirmação antes de publicar;
- editor Markdown, barra de formatação e prévia rápida para artigos;
- acervo com busca, filtros, ordenação, comentários, categorias e badges locais;
- exportação e importação manual de publicações entre cópias da mesma rede;
- temas Claro e Escuro, salvos localmente;
- encerramento confirmado da cópia local pelo menu **Encerrar**.

## 9. Limites atuais importantes

- Não há conta online, sincronização automática, comunicação direta entre cópias, hospedagem central ou compartilhamento por LAN.
- O aplicativo não aceita anexos, prévias de arquivos ou extração de conteúdo de arquivos anexados.
- Rascunhos e revisões não são exportados; apenas publicações confirmadas participam do intercâmbio.
- Não é possível apagar ou editar uma publicação já publicada. Use uma nova versão para atualizar um artigo.
- Uma cópia não detecta automaticamente outras cópias desconectadas nem atualizações que ainda não foram importadas.

## 10. Boas práticas de operação

1. Guarde PIN, ingresso e credencial de recuperação em segurança e nunca os publique ou envie por canais inadequados.
2. Revise cuidadosamente antes de confirmar uma publicação, pois ela se torna imutável.
3. Faça exportações regulares das publicações importantes e organize uma rotina de intercâmbio entre membros.
4. Ao trocar de dispositivo, recupere a identidade na nova cópia e interrompa o uso da anterior antes de trabalhar na substituta.
5. Use o botão **Encerrar** ao finalizar o trabalho para encerrar a cópia local de forma confirmada.

## 11. Suporte e referência de produto

Este guia descreve o comportamento disponível na versão 1.1.1. Para regras completas de produto, segurança e interoperabilidade, consulte [RFC-001](RFC/RFC-001.md), [RFC-002](RFC/RFC-002.md) e o [changelog](Changelog/CHANGELOG.md).
