# Segurança e autenticação Google

## Princípios
- Autenticar somente com OAuth 2.0 via navegador usando o backend oficial Google Drive do rclone.
- Nunca solicitar senha Google dentro do aplicativo.
- Não embutir segredos OAuth ou tokens no repositório, pacote .deb ou logs.
- Não automatizar login web com cookies ou scraping.
- Usar o mínimo de escopos necessário; para operações sobre todo o Drive pode ser exigida verificação do aplicativo OAuth.
- Para distribuição pública, providenciar consent screen, política de privacidade e, se exigida, verificação Google antes de anunciar compatibilidade ampla.
- Respeitar quotas da API e políticas de uso; aplicar backoff em 429/403 apropriados.
- Tratar rclone.conf como credencial sensível. Preferir proteção via configuração criptografada do rclone e cofre do sistema; não adicionar ao git.
- Nunca executar sync/bisync com exclusões automáticas sem consentimento, backups e tratamento de conflitos.
- Avisar claramente que rclone copy pode sobrescrever arquivos de mesmo nome.
- Testar primeiro com conta e pasta dedicadas sem dados importantes.

## Estado atual
A v0.2.0 usa rclone config no terminal. A GUI ainda não possui login OAuth embutido, proteção de credenciais via Secret Service nem sync bidirecional. A política acima é requisito para próximas versões, não alegação de implementação.
