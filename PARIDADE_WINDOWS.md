# Paridade de funcionalidades — Drive para Linux e Google Drive para computador

Referência oficial Google (Windows/macOS): https://support.google.com/drive/answer/10838124?hl=pt-BR
Streaming/espelhamento: https://support.google.com/drive/answer/13401938?hl=pt-BR

O Drive para Linux é um aplicativo **independente**, GTK4 com rclone, e não
distribui marca, ícones ou código proprietário do Google.

| Recurso | Drive para computador (Windows) | Drive para Linux 0.13.1 |
| --- | --- | --- |
| Autorização Google | navegador oficial | assistente GTK4 inicia OAuth pelo rclone no navegador; homologação real pendente |
| Contas múltiplas | sim | gerencia múltiplos remotes rclone; **um remoto ativo por sincronização automática** |
| Espelhamento local | sim | **sim**, dois sentidos por timer systemd na sessão Linux |
| Novos arquivos criados localmente | automático | **sim**, na próxima execução do serviço |
| Novos arquivos remotos | automático | **sim**, na próxima execução do serviço |
| Editar arquivos existentes | sim | **sim**, se somente um lado mudou em relação ao histórico |
| Conflitos simultâneos | gestão por Drive | preservados e notificados no estado para revisão manual |
| Exclusões e renomeações | propagadas | **revisão manual com arquivamento recuperável; não propagadas automaticamente** |
| Pasta local selecionada | sim | sim |
| Trabalhar offline | arquivos espelhados disponíveis | arquivos já presentes na pasta local disponíveis, sincroniza após reconexão |
| Pesquisa de arquivos | sim | pesquisa read-only por nome/caminho no remoto selecionado |
| Streaming como disco virtual | sim | **implementado de forma opcional** com rclone mount/FUSE, pasta separada e somente leitura por padrão; teste real Zorin ainda pendente |
| Ícone na bandeja do sistema | sim | **não implementado**; timer pode trabalhar sem GUI aberta |
| Pausar/retomar | sim | switch de ativação do systemd timer do usuário |
| Última operação | sim | estado do ciclo automático e histórico da sessão GUI |
| Backup para Google Photos | sim | **implementação parcial** |
| Integração Microsoft Office/Outlook | nativa no Windows | abre arquivos espelhados/streaming no aplicativo padrão Linux; não oferece presença Office/Outlook |
| Unidades compartilhadas | sim | somente remotes configurados adequadamente no rclone |
| Sincronização após logout do Linux | serviço próprio | **não**; requer sessão do usuário ativa (sem linger habilitado) |

## Teste de QA

- Testes sem credenciais reais usando rclone em pastas locais:
  criação local/remota, atualizações unilaterais dos dois lados,
  backups de versões, conflitos simultâneos e exclusões.
- GTK4 em Weston/Wayland no CI, testes unitários, revisão da estrutura do .deb
  e análise de unidades systemd.
- **Não testado automaticamente:** autenticação com Google de verdade,
  compatibilidade específica da versão instalada do Zorin OS,
  funcionamento efetivo de timer systemd na sessão desktop,
  recuperação em desconexões prolongadas e volume massivo de dados.

## Limitações de design e compatibilidade

O visual aproxima-se de um cliente de desktop com painel lateral, arquivos,
status, contas, sincronização e busca, mas **não é uma cópia pixel a pixel
do cliente proprietário do Google**. Ícones e recursos usam GTK4 e elementos
disponíveis para Linux. Não alegar equivalência 1:1 de produto.

## Nota de compatibilidade v0.13.1

A montagem FUSE permite criar, editar e excluir arquivos **apenas após o usuário ativar gravação e remontar o disco virtual**. O espelhamento local segue editável como pasta normal do Linux; conciliação de exclusões exige opt-in com arquivamento recuperável. Não é um substituto exato para a lixeira e para a presença colaborativa do Google Drive para Windows. A API do Google pode bloquear gravações quando a cota OAuth compartilhada está esgotada.
