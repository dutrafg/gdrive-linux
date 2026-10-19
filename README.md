# Drive para Linux

Cliente gráfico simples GTK3 para Google Drive baseado em rclone.

## Dependências
`sudo apt install python3 python3-gi gir1.2-gtk-3.0 rclone`

## Executar
`python3 gdrive-linux`

Configure a conta usando `rclone config` no terminal, depois atualize as contas no aplicativo.

A versão 0.1.0 usa `rclone copy`, que não exclui arquivos no destino. Não é sincronização bidirecional. O aplicativo usa as credenciais armazenadas pelo rclone; não envie `rclone.conf` ao GitHub.

## Atualizações
Novas versões serão publicadas em GitHub Releases; verificação e instalação pelo aplicativo são funcionalidades futuras.
