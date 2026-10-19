# Drive para Linux

Cliente experimental **GTK4** para acessar o Google Drive no Linux usando **rclone**. Versão atual: **0.11.1 Alpha**. Não é um cliente oficial do Google.

## Funcionalidades

- Interface GTK4 redesenhada com **menu lateral**, **Início**, **Contas**, **Arquivos**, **Sincronização**, **Transferências** e **Histórico** da sessão, utilizando CSS nativo GTK4 e mantendo o rclone como mecanismo de transferência.
- Seleção de contas configuradas no rclone, com atualização assíncrona sem bloquear a interface, e navegação por pastas remotas.
- Upload e download manuais usando `rclone copy`.
- Atualização automática opcional a cada cinco minutos **enquanto o aplicativo está aberto**, apenas da nuvem para a pasta local; não exclui arquivos e usa `--ignore-existing` para não substituir nenhum arquivo local existente; alterações remotas em arquivos já baixados não são aplicadas automaticamente.
- Botão para abrir a pasta local no gerenciador padrão do ambiente Linux.
- **Transferência bidirecional seletiva** de arquivos novos, sem exclusão e sem sobrescrita, limitada a 100 arquivos por operação. Conflitos são preservados e devem ser resolvidos manualmente. A operação é experimental e não representa sincronização completa.
- **Simulação** de sincronização bidirecional: compara inventários e identifica arquivos exclusivos e conflitos sem transferir ou excluir arquivos. A comparação é conservadora: hashes de algoritmos diferentes são tratados como conflito, mesmo quando o conteúdo pode ser idêntico.
- Barra de progresso baseada nas estatísticas do rclone, logs, estados de conclusão/falha/cancelamento e histórico **apenas da sessão**.
- Pasta local configurável e preferências salvas em `~/.config/gdrive-linux/settings.json` (sem tokens OAuth).

**Importante:** o assistente é gráfico no GTK4, mas a autenticação efetiva é realizada no navegador pelo OAuth do rclone. Não há campos para senha Google. Os indicadores de uso da nuvem e outras métricas decorativas da imagem de referência não foram inventados; serão implementados quando houver dados reais.\n\n**Limitações:** não há sincronização bidirecional completa (somente transferência seletiva de arquivos exclusivos), sincronização em segundo plano com o aplicativo fechado, montagem virtual, login OAuth dentro da própria janela, sem navegador externo, histórico persistente ou integração profunda com gerenciador de arquivos. O aplicativo ainda precisa de validação funcional em diferentes distribuições.

## Instalação e execução

Em Debian/Ubuntu com GTK4:

```bash
sudo apt update
sudo apt install python3 python3-gi gir1.2-gtk-4.0 rclone
python3 gdrive-linux
```

Para instalar o pacote `.deb`, baixe o artefato da execução aprovada em [GitHub Actions](https://github.com/dutrafg/gdrive-linux/actions) e instale com `sudo apt install ./gdrive-linux_0.11.0_all.deb`. O arquivo só estará disponível após o workflow gerar o artefato.

## Configuração da conta

Em **Início → Conectar conta Google**, informe um nome novo para a conta. O Client ID próprio é **opcional**; por padrão usa-se o cliente OAuth fornecido pelo rclone. O aplicativo inicia o fluxo OAuth do rclone em segundo plano; a autorização ocorre no navegador padrão. Nenhuma senha ou token é coletado pela interface. Para configurar um cliente próprio, consulte [instruções do rclone](https://rclone.org/drive/#making-your-own-client-id). A autorização requer navegador e pode falhar por configuração incorreta do consentimento OAuth. Como alternativa, execute `rclone config` no terminal (ou use **Contas → Configurar**). Selecione o backend Google Drive e conclua a autorização OAuth no navegador pelo fluxo oficial do rclone. Volte ao aplicativo e clique em **Atualizar**. **Nunca digite sua senha Google dentro do Drive para Linux.** Não publique o arquivo `rclone.conf`.

Escolha uma pasta local existente em **Contas**. Antes de transferir arquivos importantes, teste com uma conta e pasta de teste e mantenha backup independente.

## Atenção aos dados

`rclone copy` **não exclui automaticamente arquivos do destino**, mas **pode sobrescrever arquivos existentes**. Não confunda esta operação com backup versionado ou sincronização bidirecional. O botão Cancelar interrompe o processo, mas arquivos já copiados podem permanecer no destino.

## Testes e empacotamento

O workflow `.github/workflows/build-deb.yml` executa compilação sintática Python, testes unitários, testes de transferência real entre diretórios locais usando rclone (sem OAuth), incluindo erro de origem ausente e substituição de arquivos existentes, um teste de inicialização GTK4 em Wayland nativo usando Weston headless e cria, inspeciona e instala o pacote Debian em um ambiente Ubuntu de CI. **A existência do workflow não significa que todas as execuções passaram.** Consulte [Actions](https://github.com/dutrafg/gdrive-linux/actions) para o estado atual. GTK4 usa Wayland nativamente quando a sessão Linux oferece esse protocolo; o aplicativo não força X11 e mantém compatibilidade com ambientes X11. O teste de inicialização não substitui testes visuais em GNOME/KDE ou operações reais com uma conta Google.

## Versionamento

Até **0.11.0**, versões Alpha. **1.0.0 Beta** será o marco de início da fase Beta, sujeito a QA; depois seguem versões incrementais. Consulte [SECURITY.md](SECURITY.md) para cuidados de autenticação, permissões e divulgação de vulnerabilidades.

## Zorin OS — dependência rclone indisponível

Algumas instalações do Zorin OS não têm o pacote `rclone` disponível nas fontes APT configuradas. A partir da revisão do pacote **0.11.0 Alpha**, `rclone` é uma dependência **recomendada**, não obrigatória: o instalador gráfico poderá instalar a interface sem o rclone, mas **transferências e autenticação não funcionarão** até o rclone ser instalado separadamente.

Verifique com `apt-cache policy rclone`. Se não houver candidato, confira as fontes de software da sua versão do Zorin OS e as instruções oficiais em https://rclone.org/install/ . Evite scripts de terceiros e não altere repositórios do sistema sem saber a versão-base do Ubuntu. Após instalar, execute `rclone version` para confirmar.

A instalação do pacote em CI ocorre no Ubuntu, **não é um teste real no Zorin OS**. O problema específico deve ser revalidado em um computador com Zorin.
