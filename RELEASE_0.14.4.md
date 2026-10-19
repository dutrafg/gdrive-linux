# Drive para Linux — revisão de QA v0.14.4 Alpha

## Entregas

1. Erros de transferência são preservados mesmo quando a verificação posterior do inventário também falha, incluindo 403 de quota Google.
2. Arquivamento automático de cópias locais revalida o MD5 imediatamente antes de movê-las para o backup.
3. Revisão manual de exclusões respeita os filtros de sincronização dos perfis/contas, evitando arquivar arquivos ignorados.
4. Arquivamento manual revalida o MD5 da versão sobrevivente e aborta se ela mudou.
5. O planejamento não tenta baixar cegamente itens remotos sem hash MD5 comparável, incluindo certos documentos nativos do Google. Eles exigem exportação específica.
6. A validação FUSE também verifica permissão para criar o ponto de montagem no diretório pai.
7. A interface atualiza os indicadores locais de sincronização e montagem periodicamente sem fazer consultas extras à API Google.
8. O ícone da bandeja alerta quando a última sincronização está desatualizada, evitando um falso estado de sucesso.
9. Testes de regressão cobrem quota, re-scan, filtros, recuperação, hash, FUSE e dados remotos incompatíveis.
10. O GitHub Actions inicia agora também o **executável instalado do pacote** via Xvfb e D-Bus, além do smoke Wayland do código-fonte.
11. As actions oficiais foram atualizadas para versões Node.js 24.

## Critérios de QA

- Todos os testes unitários passam no Ubuntu 22.04.
- Integração real com `rclone` em remotos locais passa para cópia, edição, conflitos e exclusões recuperáveis.
- GTK4 inicia com Wayland/Weston e **o instalador** inicia via Xvfb/X11.
- O pacote `.deb` instala e os serviços systemd de usuário são válidos.
- O teste FUSE com montagem real só é executado quando o runner disponibiliza `/dev/fuse`, e deve mostrar `SKIP` caso contrário.

## Limitações e homologação no Zorin OS

A conexão Google, OAuth, permissões FUSE e montagem após login em um Zorin OS real **não são verificadas pela CI**. O bloqueio 403 com Client ID compartilhado não pode ser removido somente pelo aplicativo: requer OAuth com projeto e quota válidos. Não habilitar exclusões automáticas sem revisar o histórico de backup.

Não classificar a v0.14.4 como pré-estável até realizar testes locais de criação, modificação, exclusão recuperável, montagem e desmontagem FUSE, reinício do computador e sincronização com a interface fechada.
