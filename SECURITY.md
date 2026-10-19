# Política de segurança — Drive para Linux

**Estado:** 0.13.0 Alpha, software experimental. Não há auditoria de segurança independente nem garantia de uso em produção.

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

## Serviço de sincronização contínua (v0.13.0)

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
