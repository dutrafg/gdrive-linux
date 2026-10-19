# Drive para Linux

Cliente desktop experimental **GTK4 + rclone** para Google Drive em Linux. **Versão 0.14.6 Alpha**. Projeto independente, não oficial do Google.

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

Baixe o artefato aprovado na página de [GitHub Actions](https://github.com/dutrafg/gdrive-linux/actions), extraia o ZIP e instale o `gdrive-linux_0.14.4_all.deb`:

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

Até a v0.14.4, o aplicativo permanece **Alpha**. A promoção para uma versão pré-estável ou Beta depende de QA, especialmente autenticação com conta Google, compatibilidade em Zorin OS e confiabilidade de cópias.

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

## Prioridades alta e média inspiradas no Insync — v0.14.6 Alpha

### Inicialização automática do disco virtual
Em **Disco virtual**, ative **Montar Drive automaticamente ao entrar no Linux**. O aplicativo usa `systemctl --user enable gdrive-linux-mount.service` e solicita a montagem atual de forma assíncrona. O serviço foi configurado com `Type=notify`, ou seja, não deve anunciar a montagem como pronta antes do rclone confirmar o FUSE. Ao entrar novamente no Zorin OS, a montagem será solicitada automaticamente, mesmo sem abrir a janela GTK4. O serviço exige sessão de usuário Linux, FUSE e conectividade; se a rede falhar tentará novamente com intervalo conservador. Desativar o controle também solicita a desmontagem da unidade atual.

### Sincronização seletiva e arquivos ignorados
Em **Sincronização**, informe padrões separados por vírgula: em **Sincronizar somente** use, por exemplo, `Documentos/, Fotos/`; em **Ignorar**, `*.tmp, *.part, Cache/`. As regras são validadas, aplicadas nos **dois inventários antes de calcular as alterações** e persistidas. Retirar um diretório da seleção não causa exclusão de seu conteúdo — os hashes anteriores continuam preservados. Os botões de transferência manual não aplicam esses filtros, pois são operações separadas.

### Envio, download ou dois sentidos
Selecione **Bidirecional**, **Somente enviar** ou **Somente baixar**. Os modos unidirecionais somente executam ações novas ou alterações **sem conflito** na direção escolhida; não forçam sobrescritas da outra extremidade, não removem arquivos e não fazem conciliação automática de exclusões. Pode haver conflitos iniciais a resolver manualmente.

### Múltiplas contas com pastas próprias
Em **Contas**, selecione o remoto desejado e uma pasta local; em **Sincronização → Contas e pastas independentes**, selecione a direção e adicione o perfil. Repita para outras contas e pastas distintas. Cada perfil recebe histórico de comparação, bloqueio de execução e diagnóstico individual. Para editar os perfis, pause primeiro o serviço de sincronização. O limite é 12 perfis e um mesmo remoto não pode possuir dois perfis ativos de espelhamento nesta versão.

**Discos externos:** é possível escolher pastas em discos USB ou outros volumes montados. Se um volume em `/media/<usuário>/<disco>` ou `/run/media/<usuário>/<disco>` não estiver montado, o sincronizador recusa o ciclo dessa conta, em vez de criar arquivos indevidamente no disco do sistema. Um perfil com erro não deve impedir os demais de serem processados.

**Unidades compartilhadas do Google Drive:** são suportadas quando previamente configuradas como remotos apropriados no rclone, mas ainda não há um seletor gráfico completo para permissões, equipes e compartilhamentos.

### Indicador opcional de atividade na bandeja do sistema
Em **Configurações**, habilite **Iniciar indicador ao entrar no Linux**. O indicador é um processo GTK3 separado, que usa Ayatana AppIndicator quando instalado, mostra a situação da sincronização, abre o aplicativo e permite solicitar um ciclo. Seu funcionamento depende do suporte a indicadores na versão do Zorin. A opção não bloqueia o aplicativo GTK4 quando indisponível. Dependência opcional: `gir1.2-ayatanaappindicator3-0.1` e `gir1.2-gtk-3.0`.

### Integração com Zorin Files e Nautilus
Em **Disco virtual**, clique em **Adicionar aos favoritos do Zorin Files** para incluir a pasta de montagem na barra lateral do gerenciador de arquivos (formato GTK de bookmarks). **Remover dos favoritos** exclui somente esse atalho, nunca arquivos da nuvem ou outros favoritos. A montagem FUSE continua sendo necessária para navegar pelo Drive virtual.

### Exportação de Google Docs, Sheets e Slides
Na nova seção **Documentos Google**, exporte cópias em **LibreOffice/ODF**, **Microsoft Office** ou **PDF** com a opção oficial `--drive-export-formats` do rclone. O destino fica fora da pasta espelhada em `~/Documents/DriveExports/<conta>` (ou `~/Documentos/DriveExports/<conta>`). Não sobrescreve arquivos já exportados nem altera documentos nativos da nuvem. A exportação pode incluir documentos Office comuns na mesma conta; não constitui conversão bidirecional ou edição colaborativa integrada. Veja https://rclone.org/drive/ .

### Homologação
O QA no Ubuntu/Wayland e os testes do rclone com remotos locais são obrigatórios antes da entrega. **Ainda dependem do Zorin OS real**: autorização OAuth do Google, montagem FUSE após login, suporte do painel ao AppIndicator, acesso a arquivos compartilhados com permissões específicas, e exportação de documentos nativos reais. O software permanece Alpha enquanto esses cenários não forem confirmados.


## Correções da montagem no Zorin OS — v0.14.6 Alpha

Esta atualização responde ao erro **“Não foi possível montar”** que apareceu no teste. A montagem continua usando rclone/FUSE e `systemd --user` com `Type=notify`, como recomendado pelo rclone. Os ajustes incluem:

- Um **PATH conhecido no serviço** (`/usr/local/bin:/usr/bin:/bin`), evitando que a janela encontre o rclone enquanto o systemd não encontra.
- Espera de até **180 segundos no serviço** e 205 segundos na execução da interface, sem declarar falha por um limite menor que o do próprio serviço.
- Conferência da **conta existente na configuração do rclone**, localmente e sem solicitar informações da API Google, antes de criar a pasta de montagem.
- Verificação da propriedade, escrita e conteúdo da pasta `~/DriveOnline/<conta>`; o aplicativo nunca a esvazia automaticamente.
- Recuperação de estados `failed` do serviço antes de uma nova tentativa, sem apagar caches, arquivos ou unidades.
- Nova seção **Disco virtual → Verificação de montagem do Zorin OS**, com diagnósticos que não incluem credenciais ou conteúdo bruto dos logs.
- Botão **Testar acesso Google (consulta sem alterações)**: faz **uma única consulta** para distinguir falha de autenticação/cota de falha FUSE. Não use repetidamente quando já houver aviso de 403.

### Passo a passo seguro

1. Instale o novo pacote da execução de QA aprovada. Abra o aplicativo normalmente, como usuário, sem executar `sudo gdrive-linux`.
2. Entre em **Disco virtual** e clique em **Diagnosticar requisitos de montagem**. A lista mostra o componente indisponível e sua correção.
3. Se o rclone estiver ausente, instale-o em `/usr/bin` ou `/usr/local/bin`; se faltar FUSE, execute `sudo apt install fuse3` e confirme a existência de `/dev/fuse`.
4. Se a verificação local passar, pressione **Testar acesso Google** **uma vez**. Se houver erro 403, configure um Client ID/Secret OAuth Desktop próprio no rclone e aguarde a recuperação da cota. **A montagem não funcionará enquanto a API bloquear a conta**.
5. Clique **Montar Drive**, aguarde a confirmação e depois **Abrir disco no gerenciador**. Se quiser criar, modificar e excluir dentro do disco online, marque **Permitir modificar arquivos** e clique em **Aplicar gravação e remontar**. Isso é distinto da pasta espelhada `~/GoogleDrive`.
6. Somente depois de o disco montar manualmente, habilite **Montar automaticamente ao entrar no Linux** para a sessão seguinte.

Se a GUI não iniciar, o diagnóstico também pode ser consultado sem usar a rede:

```bash
python3 /usr/share/gdrive-linux/mount_checks.py
```

Para verificar o serviço manualmente: `systemctl --user status gdrive-linux-mount.service`. Registros de `journalctl` podem conter nomes de arquivos e outros dados pessoais: **não publique o log bruto nem seu rclone.conf**. Prefira compartilhar apenas a mensagem resumida pela GUI.

**Limites da validação:** os testes automatizados confirmam a estrutura do serviço, segurança, diagnósticos e inicialização GTK4; o teste FUSE com um remoto local só executa quando o runner oferece `/dev/fuse`. A montagem real do Google Drive e o funcionamento após login no Zorin continuam necessitando teste no computador.

## Melhorias da v0.14.6 Alpha — montagem e segurança no Zorin OS

O pacote Debian agora instala rclone e fuse3 como dependências obrigatórias. A montagem recusa mudança de conta durante uma operação FUSE, pastas simbólicas e pontos sem permissão. O cache do rclone tem endereço previsível dentro da pasta pessoal; uma configuração RCLONE_CONFIG personalizada é respeitada na execução local, e o diagnóstico alerta quando o serviço de usuário pode não herdá-la.

O serviço aguarda até 180 segundos para iniciar e até 180 segundos para finalizar, com 15 minutos entre tentativas após falha. Desativar montagem automática no login não desmonta a unidade atual: feche os documentos e use Desmontar Drive separadamente quando desejar interromper o cache de gravação.

Em Disco virtual, use Diagnosticar requisitos de montagem para verificar conta, executável, FUSE, permissões e systemd sem chamar a API Google. O botão Copiar diagnóstico sem dados confidenciais facilita suporte. Testar acesso Google é uma ação separada e explícita. Mesmo com FUSE montado, a API Google pode continuar bloqueada pelo erro 403 de quota.

O indicador opcional de atividade só é habilitado se o suporte Ayatana/AppIndicator estiver disponível. Para várias contas, o indicador mostra a quantidade sem divulgar os nomes. O aplicativo ainda precisa de teste com a conta Google real no computador Zorin para homologação de montagem, autostart e gravação.

## Revisão de integridade, configurações e QA — v0.14.6 Alpha

Esta revisão segue a v0.14.2, com foco em confiabilidade e prevenção de informações incorretas na interface:

- O serviço de sincronização agora retorna **falha ao systemd** em erros de API Google (incluindo 403) ou de acesso, em vez de registrar uma execução sem sucesso como se fosse concluída.
- Quando uma fila contém mais arquivos que o limite por ciclo, a GUI informa **Sincronização parcial** e quantos arquivos aguardam a próxima execução. O indicador de sistema deixa de apresentar "Sincronizado" enquanto existir uma fila pendente.
- Nos modos somente envio/download, arquivos deliberadamente não transferidos por causa da direção escolhida têm contagem separada, sem serem confundidos com pendências.
- Em **Sincronização**, a interface apresenta o resultado de cada conta e avisa se a última verificação registrada ocorreu há mais de 15 minutos. Isso não prova que o timer está ativo; use o diagnóstico para conferir.
- Os nomes de remotos do rclone agora rejeitam caracteres de controle e nomes iniciados por `-`, evitando interpretação de argumentos inválidos nos comandos.
- O salvamento das preferências usa arquivos temporários exclusivos, gravação sincronizada e substituição atômica. Isso reduz risco de JSON corrompido quando atualizações de configuração ocorrem próximas umas das outras.
- Foram adicionados testes específicos para erro de serviço, filas de múltiplos ciclos, modos unidirecionais, permissões de preferências, nomes de remotos e estados exibidos na interface.

**Limitações mantidas:** autenticação OAuth real, montagem FUSE e criação/edição/exclusão de arquivos com sua conta Google precisam de testes no Zorin OS. Os testes em GitHub Actions usam ambientes Linux de CI e remotos locais do rclone; não equivalem a testes na conta Google pessoal.

## Revisão de confiabilidade v0.14.6 Alpha

A revisão acrescenta proteção contra erros ocultados por uma segunda falha de inventário, conferência de MD5 antes de arquivar arquivos locais e revisão manual de exclusões que respeita filtros seletivos. Arquivos remotos sem MD5 comparável, como alguns documentos nativos Google, ficam para exportação específica em vez de causar downloads repetidos. O diagnóstico FUSE detecta também falta de permissão para criar a pasta da unidade virtual. O status da GUI atualiza a cada minuto usando somente dados locais, e o indicador alerta quando a sincronização não é recente. Consulte [RELEASE_0.14.4.md](RELEASE_0.14.4.md).

**QA:** os testes em CI não comprovam a montagem real na sua instalação do Zorin OS nem acesso à conta Google sob bloqueio de API 403. A sincronização e a montagem continuam dependentes da autenticação, cota Google e permissões corretas do Linux.

## Novidades da v0.14.6 Alpha — integridade e recuperação

Foram adicionados controles para **Restaurar versões anteriores** em Sincronização, com seleção de cópias locais arquivadas e confirmação antes de criar uma cópia recuperada. O arquivo recuperado não sobrescreve documentos, não altera a nuvem e, quando a pasta Documentos for o próprio espelho, a recuperação ocorrerá numa pasta privada separada. Backups do Drive guardados remotamente no histórico do rclone continuam exigindo restauração específica e não aparecem nessa lista local.

O sincronizador agora verifica se o arquivo local mudou entre o inventário e o início da transferência. Caso isso aconteça, interrompe a operação para proteger alterações recém-salvas. Também **recusa histórico de sincronização corrompido**: não recria o estado silenciosamente, pois isso poderia fazer um arquivo apagado reaparecer na nuvem.

Em Configurações, a opção **Escolher rclone.conf existente** permite indicar um arquivo personalizado usado pela interface e pelos serviços em segundo plano. As preferências guardam **somente o caminho** desse arquivo, nunca sua senha, Client Secret ou token. A verificação de compatibilidade avisa quando o arquivo não existe ou pode ser lido por outros usuários.

O plano completo e os critérios de QA estão em [RELEASE_0.14.5.md](RELEASE_0.14.5.md). A versão permanece Alpha; testes com OAuth e montagem FUSE no computador Zorin não podem ser presumidos apenas pelo CI.

## Melhorias da v0.14.6 Alpha — transferências manuais seguras

A transferência manual de arquivos agora **preserva arquivos já existentes por padrão**, tanto ao **enviar** quanto ao **baixar**. Na confirmação da operação, mantenha marcada **Preservar arquivos já existentes no destino (recomendado)**. Para forçar uma substituição, é necessário desmarcar conscientemente essa proteção. Mesmo no modo de sobrescrita, a cópia manual não remove arquivos exclusivos do destino.

Foi criado também um bloqueio por **conta + pasta local**, compartilhado entre as transferências da interface GTK4 e o serviço de sincronização automática. Se uma tarefa estiver trabalhando no mesmo perfil, a outra aguarda nova solicitação em vez de executar uma cópia paralela, reduzindo risco de sobrescritas e conflito.

Durante transferência, a interface impede alterar conta, pasta local e `rclone.conf`, inclusive quando a janela de seleção já tinha sido aberta anteriormente. O teste de inicialização GTK4 verifica esse bloqueio, e os testes rclone reais cobrem novos arquivos mantendo a versão existente intacta dos dois lados.

Essas mudanças não consertam sozinhas o erro de cota Google **403 RATE_LIMIT_EXCEEDED**; a API ainda precisa estar acessível e um Client ID/Secret OAuth próprio pode ser necessário.
