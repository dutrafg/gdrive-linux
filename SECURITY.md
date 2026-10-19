# Política de segurança — Drive para Linux

**Estado:** 0.13.1 Alpha, software experimental. Não há auditoria de segurança independente nem garantia de uso em produção.

## Reportar vulnerabilidades

Evite publicar tokens, credenciais, arquivos `rclone.conf`, capturas com dados pessoais ou detalhes de exploração em issues públicas. Use **GitHub → Security → Report a vulnerability**, se disponível no repositório. Se o canal privado não estiver habilitado, solicite sua habilitação em uma issue **sem detalhes sensíveis**.

Informe versão, distribuição Linux, passos de reprodução, impacto e registros **sem segredos**. Não teste contas ou dados de terceiros sem autorização.

## Autenticação Google

- A configuração de contas é delegada ao **rclone**, via `rclone config`; o aplicativo **não solicita senha Google**.
- A interface GTK4 inicia o OAuth pelo rclone e o navegador padrão realiza a autorização. O Client ID próprio é opcional na interface, mas o cliente compartilhado do rclone está sendo descontinuado em 2026; algumas contas exigirão credenciais próprias e um Client Secret através da configuração avançada. Não insira segredos em argumentos de linha de comando. O aplicativo não solicita senha Google nem exibe tokens. O login depende do navegador externo.
- O arquivo `rclone.conf` pode conter tokens de acesso/renovação. Restrinja seu acesso, não o adicione ao Git e considere usar a criptografia de configuração do rclone.
- Nunca compartilhe credenciais em logs, screenshots, relatórios de erro ou pacotes Debian.
- Para distribuição pública, verificar exigências de tela de consentimento, escopos e políticas do Google. Não alegamos que o aplicativo tenha aprovação ou verificação oficial do Google.

## Integridade dos arquivos

- A transferência atual usa `rclone copy` com argumentos passados como lista, sem shell.
- `copy` não remove arquivos ausentes na origem, mas **pode substituir arquivos no destino**. Faça backups e teste em diretórios descartáveis.
- O cancelamento pode deixar arquivos já copiados. Não há reversão transacional nem resolução automática de conflitos.
- A sincronização contínua é opcional e utiliza um timer systemd do usuário. Ela propaga criações e edições unilaterais usando um histórico de hashes MD5, executa backups de versões anteriores antes de substituir um arquivo alterado e preserva conflitos e exclusões sem propagação automática. A função exige a sessão Linux ativa e pode rodar com a janela fechada. A simulação bidirecional não altera dados. O botão de transferência seletiva executa apenas `rclone copyto --ignore-existing` para arquivos exclusivos de cada lado, com limite de 100 arquivos; não há exclusão nem resolução automática de conflitos. Mudanças concorrentes durante a execução e falhas parciais ainda exigem conferência manual.
- Escolha uma pasta local existente, com permissões adequadas. Não execute o aplicativo como root.

## Armazenamento local

- Identificações amigáveis de conta são informações fornecidas pelo usuário e mantidas localmente; não representam endereços Google validados automaticamente. A verificação pelo rclone confirma apenas que o acesso remoto funciona.\n- Preferências locais são armazenadas em `~/.config/gdrive-linux/settings.json` sem tokens OAuth, com permissões restritas quando gravadas pelo aplicativo.
- Credenciais ficam sob responsabilidade da configuração do rclone. O aplicativo não implementa integração própria com Secret Service.
- O histórico de transferências é somente da sessão; os logs exibidos na interface podem revelar **nomes de arquivos** e caminhos. Evite compartilhar logs sem revisão.

## Segurança do desenvolvimento

- O GitHub Actions executa testes unitários, verificação sintática, teste de abertura GTK4 em Wayland com Weston e testes de cópia local real com rclone, inspeção e instalação do pacote Debian em CI e gera pacote `.deb`.
- Esses testes **não** constituem auditoria de segurança, teste de autorização OAuth real ou validação de todas as distribuições.
- Não adicionar segredos, `rclone.conf`, tokens ou chaves privadas ao repositório.
- Dependências principais: Python, PyGObject/GTK4 e rclone. Atualize-as pelos repositórios confiáveis da distribuição.
- Recursos futuros (sincronização bidirecional completa, montagem FUSE, atualização automática em segundo plano) exigirão análise de ameaças, tratamento de conflitos e testes próprios antes da ativação.

## Recomendações ao testar

Use uma conta e pasta de testes, confirme origem e destino, mantenha backup separado e examine o resultado antes de repetir uma operação. Relate qualquer sobrescrita inesperada ou problema de autorização pelo canal privado de segurança.

## Serviço de sincronização contínua (v0.13.1)

- A ativação exige selecionar uma conta remota e uma pasta local existentes. O botão da interface ativa um `systemd --user` timer; o daemon confere a preferência salva e retorna sem fazer nada se desativado.
- O daemon usa bloqueio exclusivo para impedir execuções simultâneas **do próprio serviço**. Transferências manuais iniciadas separadamente ainda exigem cuidado: evite usar os botões manuais enquanto a rotina automática estiver ativa.
- O último estado é salvo sob `~/.local/state/gdrive-linux` com permissão restrita; backups de versões anteriores podem conter dados sensíveis e ocupar disco/nuvem. Faça limpeza manual somente depois de verificar a integridade dos arquivos.
- Mudanças concorrentes durante uma transferência, interrupções inesperadas, arquivos Google Docs sem MD5 comparável ou falta de espaço são limitações conhecidas. O serviço não fornece uma garantia transacional de integridade nem substitui um backup independente.
- A integração usa comandos rclone com lista de argumentos, sem senha ou tokens na linha de comando. Nenhum arquivo é intencionalmente excluído do Drive por este sincronizador.
- As funcionalidades nativas exclusivas do cliente Google para Windows (presença colaborativa no Microsoft Office, Google Photos, streaming/FUSE, etc.) não são equivalentes às funções do rclone; não alegar paridade completa.

## Disco virtual, integração com aplicativos e Google Fotos

- O modo streaming usa `rclone mount` e FUSE, em pasta **separada** do espelhamento. O modo padrão é somente leitura. Um usuário pode ativar gravação experimental, que usa cache e depende da rede; dados ainda não descarregados podem ocupar espaço e requerer recuperação após falha de conexão. Evite edições simultâneas.
- O serviço de montagem `systemd --user` não recebe permissões administrativas nem tokens via linha de comando. O helper `fusermount3` requer permissões apropriadas do sistema, portanto o serviço não utiliza `NoNewPrivileges=true` que impediria o helper; execute apenas com usuário normal.
- A abertura de documentos usa o aplicativo padrão registrado pelo Linux. Não se implementou integração proprietária Microsoft Office/Outlook, proteção colaborativa em tempo real nem bloqueios distribuídos.
- O Google Fotos usa um backend independente do rclone e faz envio **manual** sem exclusão. Credenciais próprias devem ser configuradas pelo assistente seguro do rclone; não cole client secrets na GUI, nos logs ou em argumentos de linha de comando. O Photos API não fornece acesso irrestrito para download histórico.
- Exclusões do espelhamento não são executadas automaticamente. A revisão exige seleção e confirmação dupla, usa bloqueio exclusivo do sincronizador e verifica o hash da cópia remanescente em relação ao histórico antes de arquivá-la em local recuperável. Ela não equivale a uma lixeira do Google oficial e não substitui backups.
- Funcionalidades de montagem FUSE e upload para uma conta Google Photos real ainda dependem de homologação em um Zorin OS real e de credenciais válidas; os testes automatizados só verificam a construção segura dos comandos e fluxos locais.

## Proteções adicionais contra limite 403 e exclusões (v0.13.1)

- A API retornou `403 RATE_LIMIT_EXCEEDED` no Zorin OS ao usar o Client ID compartilhado. O aplicativo limita chamadas HTTP com `--tpslimit 2 --tpslimit-burst 2`, reduz a concorrência, classifica o erro sem expor resposta JSON completa e aplica um intervalo mínimo de 15 minutos entre novas tentativas automáticas após detectar bloqueio. **Limitar requisições não contorna quota esgotada do projeto OAuth compartilhado**; configure Client ID/Client Secret próprios via rclone.
- A preferência de exclusão automática fica desativada por padrão. A ativação exige confirmação gráfica. Quando habilitada, apenas a cópia **cujo hash ainda coincide com o histórico** pode ser movida para um arquivo recuperável, nunca apagada definitivamente. Exclusões e renomeações concorrentes ainda podem resultar em conflitos; restauração é manual.
- O disco virtual começa somente leitura. Habilitar gravação exige ação explícita e **remontagem**, com aviso sobre cache VFS e riscos de gravação pendente. Confirme que a API tem quota antes de editar arquivos grandes. Exclusões via rclone mount usam o comportamento padrão do Google Drive (envio para lixeira), mas não substituem backups independentes.
- O serviço systemd é revalidado na abertura do aplicativo quando o usuário já tinha ativado o recurso. Persistência da preferência não significa que uma transferência específica ocorreu; verificar timer e último estado para diagnosticar.

## Perfis e integrações adicionais (v0.14.0)

- Montagem automática é opt-in e usa **systemd do usuário** no login, sem execução como root nem `loginctl enable-linger`; o tipo `notify` aguarda confirmação real de montagem. A recuperação de falhas pode fazer novas tentativas, mas não contorna cota Google 403.
- Cada conta/pasta tem histórico e bloqueio exclusivos. Não permita perfis com diretórios iguais ou aninhados, nem o diretório FUSE como destino do próprio espelhamento. Discos externos não montados em `/media`/`/run/media` interrompem o perfil antes de escrever arquivos.
- Filtros são aplicados aos inventários locais e remotos antes de calcular conflitos/exclusões. Arquivos que saem da seleção não são tratados como excluídos. O estado anterior dos arquivos excluídos pelo filtro permanece conservado, evitando arquivamento inesperado.
- Sincronização unidirecional recusa sobrescritas conflitantes, nunca usa `rclone sync` destrutivo. Modos somente envio/download não reconciliam exclusões automaticamente.
- O indicador da bandeja usa um **processo GTK3 independente** opcional; não mostra tokens, caminhos detalhados nem dados de arquivos e não deve armazenar credenciais. O controle de inicialização grava somente um atalho gerenciado em `~/.config/autostart`.
- A integração com Zorin Files só altera o favorito específico de `~/DriveOnline/<conta>` no arquivo de bookmarks GTK, preservando os demais favoritos. Não executa ações de nuvem.
- A exportação de documentos copia arquivos ao disco fora do espelhamento, valida o backend Drive, limita o tipo de formato e não faz upload, exclusões nem conversão reversa. Revise o conteúdo exportado antes de compartilhar cópias locais.
- A compatibilidade plena com Google Drive para Windows, presença Office, Google Photos integral, permissões de unidades compartilhadas e integração nativa de ícones por arquivo permanece não garantida.


## Diagnóstico seguro do disco virtual — v0.14.3

A GUI inclui verificação local de rclone, nome remoto, FUSE, permissões e `systemd --user`, sem transmitir nomes de arquivos à nuvem. A prova remota de acesso é uma consulta **manual, explícita, somente leitura** e com erros normalizados, nunca com JSON bruto ou token exibido. O serviço usa PATH e HOME explícitos do usuário para evitar configurações divergentes entre GTK e systemd.

Não são executados `chmod -R`, `chown -R`, `fusermount -uz` automático, remoções de diretórios de montagem ou limpeza de cache como métodos de reparo: essas operações podem comprometer edições que ainda não chegaram ao Google. Pastas não vazias ou de propriedade de outro usuário são recusadas. A montagem usa `Type=notify` e a GUI confere se o ponto FUSE realmente está montado.

Não compartilhar `rclone.conf` ou logs do journal completos: eles podem expor dados pessoais e metadados. O recurso 403 não é solucionado automaticamente; o usuário precisa de autorização OAuth compatível e cota disponível.

## Segurança adicional da v0.14.3

O aplicativo não altera a conta de montagem enquanto FUSE estiver ativo e não muda a pasta espelhada durante tarefas. Desligar o autostart não desmonta arquivos em uso; desmontagem permanece ação separada. Raízes simbólicas ou sem permissão são recusadas, sem chmod/chown recursivo nem limpeza automática de cache.

A unidade FUSE usa cache próprio de usuário e o serviço reinicia com atraso para não agravar erros de quota. O status de FUSE montado não garante a disponibilidade da conta Google. O diagnóstico pode ser copiado apenas com mensagens normalizadas, sem rclone.conf, tokens OAuth ou linhas integrais do journal. O indicador GTK3/Ayatana é opcional e testado antes da ativação.

Ainda são necessários backup independente, verificação de gravações pendentes no cache e homologação real no Zorin OS para garantir operações remotas e recuperação de rede.

## Segurança e integridade da v0.14.3

- O aplicativo bloqueia remotos com caracteres de controle ou nomes iniciados em `-`, evitando ambiguidade na interpretação de parâmetros do rclone.
- Preferências locais são escritas em arquivos temporários únicos, com `fsync` e substituição atômica; permissões permanecem `0600` em pasta `0700`.
- Uma conta com erro 403/quota ou falha operacional faz o serviço retornar código diferente de zero; um lote incompleto permanece claramente marcado como parcial.
- Nenhum recurso novo desta versão propaga exclusões definitivas, remove caches FUSE ou altera permissões de pastas inteiras. Controles de exclusão recuperável continuam exigindo opt-in.
- O status gráfico por conta omite nomes de arquivos, tokens, conteúdo de logs e caminhos completos; não é diagnóstico de OAuth real sem testar a conta.
