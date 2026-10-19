# Drive para Linux

Cliente desktop experimental **GTK4 + rclone** para Google Drive em Linux. **Versão 0.11.2 Alpha**. Projeto independente, não oficial do Google.

## Interface

A navegação foi redesenhada para o estilo de aplicativo Linux corporativo: sidebar azul-escuro, conteúdo claro, cartões responsivos, botões que se reorganizam em janelas estreitas, foco visível para navegação por teclado, estados visuais e ícones do sistema.

- **Início:** conta ativa, pasta local, situação da sincronização e última transferência (dados reais da sessão).
- **Contas:** selecionar uma conta e ver claramente o nome remoto ativo, atribuir um nome de identificação local (opcional), verificar o acesso remoto sem exibir credenciais, iniciar o assistente Google e escolher, abrir ou criar a pasta local `~/GoogleDrive`.
- **Arquivos:** navegar pelas pastas remotas, voltar, atualizar e visualizar nome/tamanho.
- **Sincronização:** indicação distinta de agendamento e transferência realmente em andamento, além de atualização automática opcional a cada cinco minutos (somente downloads novos), prévia de arquivos exclusivos, conflitos visíveis e transferência seletiva não destrutiva de até 100 arquivos.
- **Transferências:** progresso real do rclone, cancelamento de cópias manuais e registros.
- **Histórico:** lista de operações somente da sessão.
- **Configurações:** diagnóstico do rclone, configuração avançada e avisos de segurança.

A consulta de nomes/pastas não aparece como transferência em andamento. Os botões de transferência agora permanecem dentro dos respectivos cartões mesmo em janelas menores. Nenhum percentual de uso da nuvem ou transferência fictícia é apresentado. A interface é construída com widgets GTK4; o rclone faz acesso remoto e cópias.

## Instalação no Zorin OS, Ubuntu e Debian

Baixe o artefato aprovado na página de [GitHub Actions](https://github.com/dutrafg/gdrive-linux/actions), extraia o ZIP e instale o `gdrive-linux_0.11.2_all.deb`:

```bash
sudo apt install ./gdrive-linux_0.11.2_all.deb
```

O pacote requer Python 3, PyGObject e GTK4. A dependência `rclone` é **recomendada**, para permitir que a interface seja instalada mesmo quando o Zorin não oferece esse pacote nas fontes configuradas. **Sem o rclone, conexão e transferência não funcionam.** Confirme com `rclone version`; instruções oficiais: https://rclone.org/install/ .

Para iniciar diretamente a partir do código-fonte, instale Python 3, GTK4 e rclone e execute `python3 gdrive-linux` na pasta do repositório.

## Conectar o Google Drive

Abra **Início → Conectar Google**. Informe o nome da conta e clique em **Iniciar autorização**. O GTK4 acompanha o procedimento, enquanto o **rclone abre o navegador padrão para a autorização OAuth**. O aplicativo não pede a senha Google e não mostra tokens.

**Atenção (2026):** a documentação do rclone informa que o **Client ID Google compartilhado está sendo descontinuado durante 2026**. Portanto, a opção padrão pode deixar de funcionar; pode ser necessário cadastrar credenciais OAuth próprias. Consulte https://rclone.org/drive/#making-your-own-client-id . O campo Client ID na janela é opcional, mas algumas configurações próprias também exigem Client Secret; nesses casos, utilize **Configurações → Configuração avançada (terminal)** até essa etapa ser integrada com segurança. Não cole a senha Google no aplicativo.

O assistente GUI e a abertura do navegador são automatizados, mas a autenticação real com uma conta Google **ainda requer homologação em Zorin OS**.

## Integridade dos dados

- **Download/upload manual:** usa `rclone copy`; não exclui arquivos mas **pode sobrescrever arquivos existentes**.
- **Atualização automática:** usa `rclone copy --ignore-existing`, somente enquanto a janela estiver aberta; preserva arquivos já presentes no destino.
- **Transferência seletiva:** usa `rclone copyto --ignore-existing`, sem exclusão nem sobrescrita intencional; compara inventários, conserva conflitos e limita lotes.
- **Simulação:** mostra diferenças e até 50 conflitos, mas não altera arquivos.

Não há sincronização bidirecional completa com resolução automática de conflitos, exclusões conciliadas, histórico persistente, montagem FUSE ou operação contínua com a janela fechada. Faça backup separado antes de copiar dados importantes.

Preferências: `~/.config/gdrive-linux/settings.json`. Tokens OAuth são gerenciados pelo rclone em sua própria configuração. Nunca publique o arquivo `rclone.conf`.

## Qualidade e testes

O workflow `.github/workflows/build-deb.yml` usa Ubuntu CI para: sintaxe Python, testes unitários, integração rclone entre diretórios locais, inicialização GTK4 em Wayland/Weston, smoke de navegação GTK4, empacotamento, inspeção e instalação do `.deb`. **Só considere uma compilação aprovada quando a execução correspondente estiver verde.**

O smoke GTK4 não equivale a avaliação visual humana nem a autenticação Google real; o teste no Zorin OS permanece necessário. Consulte [SECURITY.md](SECURITY.md) para questões de privacidade e segurança.

## Versionamento

Até a v0.11.2, o aplicativo permanece **Alpha**. A promoção para uma versão pré-estável ou Beta depende de QA, especialmente autenticação com conta Google, compatibilidade em Zorin OS e confiabilidade de cópias.

## Identificação da conta no Zorin OS

A lista de contas do rclone apresenta nomes remotos como `meu_drive`; esse nome não é necessariamente o endereço Gmail. Em **Contas**, veja **Conta selecionada**, escolha um nome/e-mail de referência local opcional e clique em **Salvar identificação**. O texto será armazenado nas preferências locais, mas **não constitui verificação da identidade Google**. Para verificar se o acesso está operacional, use **Verificar acesso à conta**; a aplicação testa a conexão com o rclone sem mostrar credenciais.

O botão **Simular** consulta inventários sem transferir dados. **Atualização automática ativada** significa agendamento de verificações a cada 5 minutos enquanto o aplicativo está aberto, e não que exista um download em curso naquele momento.
