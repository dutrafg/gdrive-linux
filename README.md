# Drive para Linux (GTK4)

Cliente gráfico simples para Google Drive, usando **rclone** como motor de transferência.

## Dependências
```bash
sudo apt install python3 python3-gi gir1.2-gtk-4.0 rclone
```

## Executar
```bash
python3 gdrive-linux
```

Configure a conta pelo botão **Configurar** ou com `rclone config`.

## Recursos atuais (0.2.0 Alpha)
- Seleção de conta configurada no rclone
- Seleção de pasta local
- Enviar e baixar usando `rclone copy`
- Logs e cancelamento

**Atenção:** `copy` não exclui arquivos do destino, mas pode substituir arquivos de mesmo nome. Ainda não existe sincronização bidirecional, montagem de unidade virtual ou atualização automática instalada. Faça backup antes de testar com dados importantes. Não publique seu `rclone.conf`.

## Pacote Debian
O workflow do GitHub Actions cria um artefato `.deb` para instalação. A compilação do pacote não substitui testes funcionais reais em GNOME/KDE.
