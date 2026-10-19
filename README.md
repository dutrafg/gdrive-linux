# Drive para Linux

Cliente experimental **GTK4** para acessar o Google Drive no Linux usando **rclone**. Versão atual: **0.9.6 Alpha**. Não é um cliente oficial do Google.

## Funcionalidades

- Interface GTK4 com páginas **Arquivos**, **Atividades** e **Contas**.
- Seleção de contas configuradas no rclone, com atualização assíncrona sem bloquear a interface, e navegação por pastas remotas.
- Upload e download manuais usando `rclone copy`.
- Atualização automática opcional a cada cinco minutos **enquanto o aplicativo está aberto**, apenas da nuvem para a pasta local; não exclui arquivos e usa `--update` para não substituir arquivos locais mais recentes; arquivos locais mais antigos ainda podem ser sobrescritos.
- Botão para abrir a pasta local no gerenciador padrão do ambiente Linux.
- Barra de progresso baseada nas estatísticas do rclone, logs, estados de conclusão/falha/cancelamento e histórico **apenas da sessão**.
- Pasta local configurável e preferências salvas em `~/.config/gdrive-linux/settings.json` (sem tokens OAuth).

**Limitações:** não há sincronização bidirecional, sincronização em segundo plano com o aplicativo fechado, montagem virtual, autenticação OAuth integrada, atualização automática, histórico persistente ou integração nativa com gerenciador de arquivos. O aplicativo ainda precisa de validação funcional em diferentes distribuições.

## Instalação e execução

Em Debian/Ubuntu com GTK4:

```bash
sudo apt update
sudo apt install python3 python3-gi gir1.2-gtk-4.0 rclone
python3 gdrive-linux
```

Para instalar o pacote `.deb`, baixe o artefato da execução aprovada em [GitHub Actions](https://github.com/dutrafg/gdrive-linux/actions) e instale com `sudo apt install ./gdrive-linux_0.9.6_all.deb`. O arquivo só estará disponível após o workflow gerar o artefato.

## Configuração da conta

A conexão Google OAuth ainda é feita pelo rclone, não por uma janela de login própria do aplicativo. Execute `rclone config` no terminal (ou use **Contas → Configurar**). Selecione o backend Google Drive e conclua a autorização OAuth no navegador pelo fluxo oficial do rclone. Volte ao aplicativo e clique em **Atualizar**. **Nunca digite sua senha Google dentro do Drive para Linux.** Não publique o arquivo `rclone.conf`.

Escolha uma pasta local existente em **Contas**. Antes de transferir arquivos importantes, teste com uma conta e pasta de teste e mantenha backup independente.

## Atenção aos dados

`rclone copy` **não exclui automaticamente arquivos do destino**, mas **pode sobrescrever arquivos existentes**. Não confunda esta operação com backup versionado ou sincronização bidirecional. O botão Cancelar interrompe o processo, mas arquivos já copiados podem permanecer no destino.

## Testes e empacotamento

O workflow `.github/workflows/build-deb.yml` executa compilação sintática Python, testes unitários, testes de transferência real entre diretórios locais usando rclone (sem OAuth), incluindo erro de origem ausente e substituição de arquivos existentes, um teste de inicialização GTK4 em Wayland nativo usando Weston headless e cria, inspeciona e instala o pacote Debian em um ambiente Ubuntu de CI. **A existência do workflow não significa que todas as execuções passaram.** Consulte [Actions](https://github.com/dutrafg/gdrive-linux/actions) para o estado atual. GTK4 usa Wayland nativamente quando a sessão Linux oferece esse protocolo; o aplicativo não força X11 e mantém compatibilidade com ambientes X11. O teste de inicialização não substitui testes visuais em GNOME/KDE ou operações reais com uma conta Google.

## Versionamento

Até **0.9.6**, versões Alpha. **1.0.0 Beta** será o marco de início da fase Beta, sujeito a QA; depois seguem versões incrementais. Consulte [SECURITY.md](SECURITY.md) para cuidados de autenticação, permissões e divulgação de vulnerabilidades.
