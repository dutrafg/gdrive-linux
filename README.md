# Drive para Linux

Cliente desktop experimental **GTK4 + rclone** para Google Drive em Linux. **Versão 0.13.1 Alpha**. Projeto independente, não oficial do Google.

## Interface

A navegação foi redesenhada para o estilo de aplicativo Linux corporativo: sidebar azul-escuro, conteúdo claro, cartões responsivos, botões que se reorganizam em janelas estreitas, foco visível para navegação por teclado, estados visuais e ícones do sistema.

- **Início:** conta ativa, pasta local, situação da sincronização e última transferência (dados reais da sessão).
- **Contas:** selecionar uma conta e ver claramente o nome remoto ativo, atribuir um nome de identificação local (opcional), verificar o acesso remoto sem exibir credenciais, iniciar o assistente Google e escolher, abrir ou criar a pasta local `~/GoogleDrive`.
- **Arquivos:** navegar, pesquisar recursivamente por nome e caminho, voltar, atualizar e visualizar nome/tamanho.
- **Sincronização:** espelhamento automático bidirecional por timer systemd do usuário, com intervalo aproximado de um minuto durante a sessão Linux (mesmo com a janela fechada); alterações unilaterais são enviadas/baixadas, versões anteriores são guardadas, conflitos e exclusões não são aplicados. Também há simulação de mudanças e cópia seletiva manual de até 100 arquivos.
- **Transferências:** progresso real do rclone, cancelamento de cópias manuais e registros.
- **Histórico:** lista de operações somente da sessão.
- **Configurações:** diagnóstico do rclone, configuração avançada e avisos de segurança.

A consulta de nomes/pastas não aparece como transferência em andamento. Os botões de transferência agora permanecem dentro dos respectivos cartões mesmo em janelas menores. Nenhum percentual de uso da nuvem ou transferência fictícia é apresentado. A interface é construída com widgets GTK4; o rclone faz acesso remoto e cópias.

## Instalação no Zorin OS, Ubuntu e Debian

Baixe o artefato aprovado na página de [GitHub Actions](https://github.com/dutrafg/gdrive-linux/actions), extraia o ZIP e instale o `gdrive-linux_0.13.1_all.deb`:

```bash
sudo apt install ./gdrive-linux_0.13.1_all.deb
```

O pacote requer Python 3, PyGObject e GTK4. A dependência `rclone` é **recomendada**, para permitir que a interface seja instalada mesmo quando o Zorin não oferece esse pacote nas fontes configuradas. **Sem o rclone, conexão e transferência não funcionam.** Confirme com `rclone version`; instruções oficiais: https://rclone.org/install/ .

Para iniciar diretamente a partir do código-fonte, instale Python 3, GTK4 e rclone e execute `python3 gdrive-linux` na pasta do repositório.

## Conectar o Google Drive

Abra **Início → Conectar Google**. Informe o nome da conta e clique em **Iniciar autorização**. O GTK4 acompanha o procedimento, enquanto o **rclone abre o navegador padrão para a autorização OAuth**. O aplicativo não pede a senha Google e não mostra tokens.

**Atenção (2026):** a documentação do rclone informa que o **Client ID Google compartilhado está sendo descontinuado durante 2026**. No teste Zorin, o Google respondeu **403 RATE_LIMIT_EXCEEDED (userQueriesPerMinutePerProject)**; nesse caso, é necessário configurar credenciais OAuth próprias, não apenas repetir transferências. Consulte https://rclone.org/drive/#making-your-own-client-id . O campo Client ID na janela é opcional, mas algumas configurações próprias também exigem Client Secret; nesses casos, utilize **Configurações → Configuração avançada (terminal)** até essa etapa ser integrada com segurança. Não cole a senha Google no aplicativo.

O assistente GUI e a abertura do navegador são automatizados, mas a autenticação real com uma conta Google **ainda requer homologação em Zorin OS**.

## Integridade dos dados

- **Download/upload manual:** usa `rclone copy`; não exclui arquivos mas **pode sobrescrever arquivos existentes**.
- **Sincronização automática contínua:** usa `background_sync.py` via `gdrive-linux-sync.timer` do systemd por usuário, com inventários MD5 e histórico local de estado. Ao editar arquivo de apenas um lado, o aplicativo atualiza o outro, com backup da versão anterior. Criações locais e remotas são transferidas. A janela pode ser fechada e o timer continua durante a sessão Linux. É necessário ativar uma vez em **Sincronização**; pode-se pausar pelo mesmo botão. A propagação de exclusões é opcional: **Sincronização → Conciliar exclusões automaticamente com backup recuperável**, desativada por padrão e exige confirmação. Renomeações são analisadas como exclusão e arquivo novo, não são detectadas como um evento atômico.
- **Transferência seletiva:** usa `rclone copyto --ignore-existing`, sem exclusão nem sobrescrita intencional; compara inventários, conserva conflitos e limita lotes.
- **Simulação:** mostra diferenças e até 50 conflitos, mas não altera arquivos.

Exclusões podem ser conciliadas **somente com opt-in e arquivamento recuperável**. Não há resolução automática de conflitos simultâneos, detecção atômica de renomeações nem sincronização após logout do Linux. Faça backup separado antes de copiar dados importantes.

Preferências: `~/.config/gdrive-linux/settings.json`. Tokens OAuth são gerenciados pelo rclone em sua própria configuração. Nunca publique o arquivo `rclone.conf`.

## Qualidade e testes

O workflow `.github/workflows/build-deb.yml` usa Ubuntu CI para: sintaxe Python, testes unitários, integração real com rclone entre duas pastas locais (arquivos novos, edição dos dois lados, backup, conflitos e exclusões), inicialização GTK4 em Wayland/Weston, smoke de navegação GTK4, verificação das unidades systemd, empacotamento, inspeção e instalação do `.deb`. **Só considere uma compilação aprovada quando a execução correspondente estiver verde.**

O smoke GTK4 não equivale a avaliação visual humana nem a autenticação Google real; o teste no Zorin OS permanece necessário. Consulte [SECURITY.md](SECURITY.md) para questões de privacidade e segurança.

## Versionamento

Até a v0.13.1, o aplicativo permanece **Alpha**. A promoção para uma versão pré-estável ou Beta depende de QA, especialmente autenticação com conta Google, compatibilidade em Zorin OS e confiabilidade de cópias.

## Identificação da conta no Zorin OS

A lista de contas do rclone apresenta nomes remotos como `meu_drive`; esse nome não é necessariamente o endereço Gmail. Em **Contas**, veja **Conta selecionada**, escolha um nome/e-mail de referência local opcional e clique em **Salvar identificação**. O texto será armazenado nas preferências locais, mas **não constitui verificação da identidade Google**. Para verificar se o acesso está operacional, use **Verificar acesso à conta**; a aplicação testa a conexão com o rclone sem mostrar credenciais.

O botão **Simular** consulta inventários sem transferir dados. **Sincronização contínua ativada** significa um timer systemd que executa ciclos aproximadamente a cada minuto, inclusive com a janela fechada, e não que exista um download em curso naquele momento.

## Configurar sincronização contínua no Zorin OS

1. Instale o pacote e confirme que o comando `rclone version` funciona. Configure/autentique uma conta.
2. Em **Contas**, selecione a conta desejada e a pasta local que receberá os arquivos (por exemplo, `/home/zorin/GoogleDrive`). Não use a raiz do disco nem uma pasta com dados insubstituíveis sem backup separado.
3. Em **Sincronização**, ative **Espelhar alterações locais e remotas**. O app registrará o timer `gdrive-linux-sync.timer` no systemd **do usuário**. Isso exige `systemctl --user` disponível na sessão Linux.
4. Feche a janela se quiser. Enquanto o usuário continuar conectado ao Linux, o timer iniciará novas verificações aproximadamente a cada minuto. Para confirmar, execute `systemctl --user status gdrive-linux-sync.timer` e `journalctl --user -u gdrive-linux-sync.service -n 30`. Reabra o aplicativo e clique em **Ver status do serviço**.
5. Crie um arquivo de teste na pasta local e aguarde um ciclo; confirme a cópia no Google Drive. Altere-o apenas de um lado e repita. A edição concorrente em ambos os lados será marcada como conflito e não apagada automaticamente.

O timer não precisa da janela GTK aberta; não é necessário entrar no aplicativo a cada arquivo salvo. Ele **não** executa sem a sessão de usuário ativa, nem faz sincronização instantânea com eventos de filesystem: a latência normal é aproximadamente de um minuto, além do tempo de transferência. Backups locais ficam em `~/.local/share/gdrive-linux/backups`; versões remotas ficam na pasta reservada `.gdrive-linux-history` da conta escolhida, excluída do inventário do app. As preferências e o histórico de comparação local ficam em arquivos privados na pasta do usuário.

**Se o timer falhar ao ativar**, confira a disponibilidade do systemd do usuário. Sem rclone configurado e internet ativa, não haverá transferência. Caso a pasta local desapareça, o serviço falha sem excluir arquivos remotos. Arquivos nativos Google Docs sem hash comparável podem exigir tratamento manual.

## Comparativo com o Google Drive para Windows

Confira [PARIDADE_WINDOWS.md](PARIDADE_WINDOWS.md) para a matriz de recursos presentes, parciais e ainda não implementados. O aplicativo oferece uma experiência Linux GTK4 própria; não copia marca, recursos proprietários nem código do Google.

Novos problemas da sincronização contínua, como erros e conflitos, podem gerar notificações do desktop quando `notify-send` estiver disponível. Arquivos criados na pasta local com a interface fechada são transferidos no próximo ciclo do serviço, desde que ele tenha sido ativado, o usuário esteja conectado e o rclone tenha acesso à rede.

## Disco virtual FUSE (streaming sob demanda)

Na seção **Disco virtual**, selecione a conta Google Drive em **Contas** e clique em **Montar Drive**. O programa inicia `gdrive-linux-mount.service` usando `rclone mount` e expõe o Drive na pasta **`~/DriveOnline/<nome-da-conta>`**, visível nos gerenciadores de arquivos como o Arquivos/Nautilus e o Files do Zorin.

Requisitos: `rclone`, `fuse3`, `/dev/fuse` e `systemctl --user`. O pacote recomenda `fuse3`, mas pode ser necessário instalá-lo separadamente: `sudo apt install fuse3`.

A montagem é **somente leitura por padrão**. Há uma opção explícita de gravação experimental, com cache VFS do rclone (limite configurado de 2 GB) e possibilidade de conflitos; não a habilite para arquivos importantes antes de testar. A montagem é **separada** da pasta local espelhada, para evitar loops entre streaming e sincronização. Use **Desmontar Drive** antes de desconectar a rede ou trocar de conta. O serviço pode continuar ativo com a janela fechada durante a sessão Linux, mas não é montado automaticamente sem você solicitar.

## Abrir arquivos de Office e outros documentos

Em **Arquivos**, selecione um documento disponível na pasta espelhada ou no disco virtual e clique em **Abrir documento selecionado no aplicativo padrão**. Se o arquivo estiver espelhado localmente, LibreOffice, OnlyOffice e outros aplicativos associados ao tipo podem abri-lo e salvar alterações; a sincronização contínua propagará edições locais no próximo ciclo caso não haja conflito.

**Limitação:** o rclone não fornece a presença colaborativa em tempo real do Microsoft Office para Windows nem integração proprietária com Outlook. A montagem FUSE em modo somente leitura serve para consulta; para editar e salvar use preferencialmente o espelho local.

## Enviar fotos e vídeos para o Google Fotos

O Google Fotos é um *backend independente* do Google Drive no rclone. Configure um remoto `google photos` com seu Client ID/Secret pelo `rclone config` (interface avançada). Depois, em **Google Fotos**, selecione esse remoto, informe o álbum e use **Verificar fotos e vídeos** para conferir a quantidade antes do botão **Enviar mídia ao Google Fotos**.

O envio é **manual e não destrutivo**. Ele usa `rclone copy --ignore-existing`, restringe os formatos a imagens e vídeos reconhecidos e não realiza exclusões. A API pode aplicar limitações de confirmação, tamanho e álbum. Desde 31 de março de 2025, o backend do rclone não pode baixar toda a biblioteca histórica: somente conteúdo criado pela própria integração. Portanto, esta funcionalidade **não equivale a backup/restauração integral do Google Photos**. Consulte https://rclone.org/googlephotos/ .

## Revisão de exclusões e renomeações

Arquivos que desapareceram somente de um lado continuam classificados como conflito por segurança. Na página **Sincronização → Revisar exclusões com arquivamento recuperável**, escolha um único arquivo e confirme. A cópia remanescente será **movida para um arquivo de recuperação**: cópia local em `~/.local/share/gdrive-linux/backups` ou cópia remota em `.gdrive-linux-history/archived-deletions`, conforme o lado que sofreu a exclusão.

Não existe exclusão automática destrutiva. Renomeações são atualmente tratadas como exclusão + novo arquivo e podem exigir revisão manual. Após arquivar, os dados permanecem recuperáveis. Não modifique a estrutura dos históricos internos e mantenha backup externo separado.

## Correções do teste no Zorin OS — v0.13.1 Alpha

### Erro 403 RATE_LIMIT_EXCEEDED

As capturas mostram o projeto OAuth compartilhado do rclone bloqueado por limite de `userQueriesPerMinutePerProject`. O programa agora usa `--tpslimit 2 --tpslimit-burst 2`, reduz a concorrência, exibe orientação legível e faz uma pausa de **15 minutos** após erro de cota detectado no serviço contínuo. Isso reduz o número de solicitações, mas **não repara uma cota compartilhada já bloqueada**.

Em **Contas → Corrigir bloqueio Google 403 (Client ID próprio)**, abra a documentação oficial, configure um **Client ID e Client Secret OAuth Desktop** no seu projeto do Google Cloud, habilite a API Google Drive, edite o remoto atual no `rclone config` e reautorize pelo navegador. Não precisa excluir a pasta espelhada nem recriar os seus arquivos. Não cole Client Secret ou tokens em mensagens, capturas ou repositórios. O campo Client ID da conexão inicial não substitui a configuração completa de Client Secret.

### Criar, modificar e excluir arquivos

Existem **duas pastas diferentes**:

- **Pasta espelhada local**, por exemplo `~/GoogleDrive`: é uma pasta comum do Linux e deve ser gravável pelo próprio usuário. Criações e edições locais passam à nuvem pelo timer quando houver acesso à API. Se o Zorin negar gravação já nessa pasta, confira as permissões no gerenciador de arquivos; não altere proprietário/permissões de todo o HOME.
- **Disco virtual online**, por exemplo `~/DriveOnline/meu_drive`: é uma montagem rclone FUSE e começa **somente leitura**, por segurança. Para criar, editar, renomear e excluir diretamente no Drive, vá a **Disco virtual**, marque **Permitir modificar arquivos**, feche os documentos abertos e clique em **Aplicar gravação e remontar Drive**. A permissão será aplicada após reiniciar a montagem. No Drive, o rclone normalmente usa a lixeira para exclusões, mas mantenha backups de arquivos importantes.

Se você apagar um arquivo **da pasta espelhada** e quiser refletir a exclusão na nuvem, ative **Conciliar exclusões automaticamente com backup recuperável** (opt-in). O outro arquivo não será apagado definitivamente: será movido ao histórico de recuperação. O sentido inverso funciona da mesma forma. Edições simultâneas permanecem conflitos para revisão.

### Arquivos em quantidade grande

A sincronização contínua processa **até 100 arquivos por ciclo** e registra quantos estão pendentes. Uma fila de 562 arquivos não exige transferências manuais: após a recuperação da API, os ciclos seguintes continuarão o trabalho automaticamente. Os comandos manuais seletivos mantêm um limite conservador de lote.

### Verificar a execução

Em **Configurações → Diagnóstico de compatibilidade Zorin OS**, confirme a pasta gravável, a conta autorizada, FUSE e o timer. O botão para ativar a sincronização agora solicita o primeiro ciclo imediatamente, e **Ver status do serviço** avisa se o timer real do Linux não está ativo. Mesmo com timer ativo, **um erro 403 impede transferir** até a API aceitar novamente.
