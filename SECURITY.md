# Política de segurança — Drive para Linux

**Estado:** 0.9.8 Alpha, software experimental. Não há auditoria de segurança independente nem garantia de uso em produção.

## Reportar vulnerabilidades

Evite publicar tokens, credenciais, arquivos `rclone.conf`, capturas com dados pessoais ou detalhes de exploração em issues públicas. Use **GitHub → Security → Report a vulnerability**, se disponível no repositório. Se o canal privado não estiver habilitado, solicite sua habilitação em uma issue **sem detalhes sensíveis**.

Informe versão, distribuição Linux, passos de reprodução, impacto e registros **sem segredos**. Não teste contas ou dados de terceiros sem autorização.

## Autenticação Google

- A configuração de contas é delegada ao **rclone**, via `rclone config`; o aplicativo **não solicita senha Google**.
- A interface GTK4 inicia o fluxo OAuth do rclone e o navegador padrão realiza a autorização. É necessário fornecer um Client ID OAuth do tipo Desktop; o aplicativo não recebe senha Google nem lê os tokens para exibição. O login ainda depende do navegador externo.
- O arquivo `rclone.conf` pode conter tokens de acesso/renovação. Restrinja seu acesso, não o adicione ao Git e considere usar a criptografia de configuração do rclone.
- Nunca compartilhe credenciais em logs, screenshots, relatórios de erro ou pacotes Debian.
- Para distribuição pública, verificar exigências de tela de consentimento, escopos e políticas do Google. Não alegamos que o aplicativo tenha aprovação ou verificação oficial do Google.

## Integridade dos arquivos

- A transferência atual usa `rclone copy` com argumentos passados como lista, sem shell.
- `copy` não remove arquivos ausentes na origem, mas **pode substituir arquivos no destino**. Faça backups e teste em diretórios descartáveis.
- O cancelamento pode deixar arquivos já copiados. Não há reversão transacional nem resolução automática de conflitos.
- A atualização automática opcional executa cópia da nuvem para a pasta local a cada cinco minutos enquanto a janela está aberta; usa `rclone copy --ignore-existing` para preservar arquivos locais existentes independentemente de horário; arquivos remotos modificados não substituem cópias locais; não faz exclusão automática. Não há `sync`, `bisync` nem resolução de conflitos implementados.
- Escolha uma pasta local existente, com permissões adequadas. Não execute o aplicativo como root.

## Armazenamento local

- Preferências locais são armazenadas em `~/.config/gdrive-linux/settings.json` sem tokens OAuth, com permissões restritas quando gravadas pelo aplicativo.
- Credenciais ficam sob responsabilidade da configuração do rclone. O aplicativo não implementa integração própria com Secret Service.
- O histórico de transferências é somente da sessão; os logs exibidos na interface podem revelar **nomes de arquivos** e caminhos. Evite compartilhar logs sem revisão.

## Segurança do desenvolvimento

- O GitHub Actions executa testes unitários, verificação sintática, teste de abertura GTK4 em Wayland com Weston e testes de cópia local real com rclone, inspeção e instalação do pacote Debian em CI e gera pacote `.deb`.
- Esses testes **não** constituem auditoria de segurança, teste de autorização OAuth real ou validação de todas as distribuições.
- Não adicionar segredos, `rclone.conf`, tokens ou chaves privadas ao repositório.
- Dependências principais: Python, PyGObject/GTK4 e rclone. Atualize-as pelos repositórios confiáveis da distribuição.
- Recursos futuros (sincronização, montagem, atualização automática) exigirão análise de ameaças, tratamento de conflitos e testes próprios antes da ativação.

## Recomendações ao testar

Use uma conta e pasta de testes, confirme origem e destino, mantenha backup separado e examine o resultado antes de repetir uma operação. Relate qualquer sobrescrita inesperada ou problema de autorização pelo canal privado de segurança.
