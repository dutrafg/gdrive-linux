# QA — Drive para Linux v0.13.1 Alpha

Este documento reúne critérios de homologação. **Testes automatizados não substituem teste gráfico real no Zorin OS.**

## Verificações automatizadas (GitHub Actions)

- [ ] Sintaxe Python do executável e módulos.
- [ ] Testes unitários do backend, progresso, segurança, OAuth e sincronização.
- [ ] Testes locais reais do rclone (cópia e preservação de destino).
- [ ] Teste do CSS com o parser nativo GTK4.
- [ ] Teste dos controles GTK4 sob Wayland/Weston.
- [ ] Smoke de inicialização GTK4 sem exceções, e navegação pelas sete telas.
- [ ] Construção e instalação do pacote Debian; inspeção de versão, arquivos e dependências.
- [ ] Verificação de arquivos do pacote como root:root.

Marque apenas após a execução correspondente estar **verde** em https://github.com/dutrafg/gdrive-linux/actions .

## Teste manual no Zorin OS

- [ ] Abrir o aplicativo pelo menu, fechar e abrir novamente.
- [ ] Conferir barra lateral, foco de teclado, tamanhos de janela menores e rolagem.
- [ ] Abrir cada seção: Início, Contas, Arquivos, Sincronização, Transferências, Histórico e Configurações.
- [ ] Com rclone ausente, exibir diagnóstico amigável; não travar.
- [ ] Com rclone instalado, conectar uma **conta de teste** pelo assistente, autorizar no navegador e listar arquivos.
- [ ] Caso OAuth compartilhado falhe, testar credenciais OAuth próprias conforme documentação oficial do rclone.
- [ ] Criar ou escolher pasta local, confirmar caminho nas telas Início e Contas e abrir no gerenciador de arquivos.
- [ ] Navegar por pastas remotas, conferir nome, ícone e tamanho de arquivos.
- [ ] Simular sincronização: conferir arquivos exclusivos e conflitos sem alteração de dados.
- [ ] Executar transferência seletiva em ambiente descartável e conferir preservação dos existentes.
- [ ] Confirmar que upload e download manuais exibem aviso de sobrescrita.
- [ ] Testar progresso, cancelamento, logs e histórico.
- [ ] Testar atualização automática por 5 minutos sem sobrescrever arquivo local.
- [ ] Testar teclado, contraste e visual no tema padrão do Zorin.

## Bloqueios para pré-estável

- Homologação com uma conta Google real e rclone instalado.
- Testes gráficos no Zorin OS com diferentes larguras de janela.
- Garantia de que recursos de cópia não excluem arquivos e que conflitos permanecem protegidos.
- Auditoria adicional de autenticação e credenciais próprias (Client ID/Client Secret).
- Sucesso dos testes automatizados da **revisão final**, não apenas de builds anteriores.

Versão **Alpha** até que todos os critérios aplicáveis sejam verificados.

## QA adicional — novos recursos v0.13.1

- [ ] CI: testes dos módulos `mount_drive.py`, `photos_export.py`, `desktop_files.py`, `deletion_review.py` e `diagnostics.py`.
- [ ] CI: integração rclone local entre duas pastas, incluindo edições, backup, conflito e execução com a janela fechada.
- [ ] CI: CSS/GTK4 em Wayland, testes de navegação pelas telas de Disco virtual e Google Fotos, empacotamento e instalação do `.deb`.
- [ ] Zorin real: executar **Configurações → Diagnóstico de compatibilidade** com a conta selecionada, conferindo requisitos do timer e do FUSE.
- [ ] Zorin real: instalar `fuse3`, usar **Disco virtual → Montar Drive**, verificar a pasta `~/DriveOnline/<remote>`, abrir e desmontar sem erro.
- [ ] Zorin real: provar que o disco virtual não se confunde com a pasta local espelhada e que o modo padrão não permite escrita.
- [ ] Zorin real: escolher um `.docx` espelhado, abrir no editor padrão Linux, salvar e observar sincronização após um ciclo.
- [ ] Zorin real: configurar remoto `google photos` com OAuth próprio e testar preview/envio de uma mídia descartável. Não tentar restaurar biblioteca histórica via API.
- [ ] Zorin real: excluir um arquivo apenas de um lado, usar **Revisar exclusões**, confirmar o destino de arquivo recuperável.
- [ ] Verificar que não há transferências de fotos, montagens nem arquivamentos iniciados sem intervenção do usuário.
- [ ] Conferir pausa do serviço de sincronização, conta selecionada, autenticação, reabertura da GUI e comportamento após desconexão.

### Limites dos resultados

O GitHub Actions testa os comandos FUSE e do Google Photos sem credenciais reais. Não dispõe de uma sessão Zorin instalada nem de acesso à sua conta Google. Uma compilação verde confirma os testes listados, **não** equivale a homologação dessas APIs ou do kernel FUSE no computador final.

## Regressões adicionais v0.13.1 — Zorin (19/10/2026)

- [ ] Verificar que logs de `rateLimitExceeded` e `userQueriesPerMinutePerProject` produzem aviso amigável de limite 403 e não despejam páginas de JSON na GUI.
- [ ] Confirmar configuração de Client ID/Secret próprios via assistente do rclone e reautorização no navegador; sem isso a API compartilhada pode continuar indisponível.
- [ ] Após erro de quota, verificar que o sincronizador espera o cooldown e não faz chamadas em loop.
- [ ] Com 7 novos arquivos e limite de 3 por lote, confirmar 3, 3, 1 transferidos em ciclos consecutivos.
- [ ] Abrir o aplicativo com sincronização previamente ativada e conferir se reativa o timer do usuário e informa execução efetiva.
- [ ] Disco virtual: ativar gravação, **aplicar gravação e remontar** e testar criação/edição/remoção com arquivos descartáveis.
- [ ] Pasta espelhada: confirmar usuário proprietário e permissões de escrita sem conceder acesso amplo a todo o HOME.
- [ ] Com exclusões automáticas desativadas, exclusão local/remota não modifica a outra cópia.
- [ ] Após opt-in de exclusões recuperáveis, excluir de um lado e conferir arquivo no histórico remoto/local, sem exclusões definitivas.
- [ ] Revisar rclone/Google reais no Zorin; os testes CI com backend local não garantem sucesso com cota compartilhada.

## QA de prioridade alta/média — v0.14.0

- [ ] Validar `test_sync_profiles` em backend rclone alias com duas contas separadas, somente envio/download, filtros, pastas externas simuladas e preservação de arquivos excluídos da seleção.
- [ ] Testar `test_desktop_integrations` para favoritos GTK, exportação Office/ODF/PDF, atalho de bandeja e timer do usuário.
- [ ] Confirmar `systemd-analyze verify`, instalação das novas dependências de recomendação e todas as bibliotecas Python no `.deb`.
- [ ] Confirmar execução de `gdrive-linux --ui-smoke` no Weston/Wayland e carregamento CSS GTK4 sem erros.
- [ ] Zorin real: ativar **Montar automaticamente**, sair e entrar na sessão; verificar montagem sem abrir a GUI.
- [ ] Zorin real: copiar um documento de teste, escolher pasta, ignorar extensão `*.tmp`, confirmar que a exclusão da seleção não apaga arquivos.
- [ ] Zorin real: criar dois perfis para diferentes contas e pastas, inclusive um volume USB; testar desligar o disco sem modificar o remoto.
- [ ] Zorin real: selecionar somente envio e somente download e demonstrar que a direção oposta não executa gravação.
- [ ] Zorin real: favoritar `~/DriveOnline/<conta>` no Zorin Files, verificar e remover sem alterar outros favoritos.
- [ ] Zorin real: instalar dependências opcionais da bandeja, habilitar indicador, conferir status e reinício na sessão seguinte.
- [ ] Zorin real: exportar Google Docs/Sheets/Slides em ODF, Office e PDF, verificar arquivos originais intactos e limites de quota API.
- [ ] Zorin real: abrir arquivos do Drive com LibreOffice/OnlyOffice e conferir persistência das edições após sincronização, sem conflitos.
- [ ] Verificar que nenhum recurso adicional ativa exclusões definitivas por padrão e que backups permanecem restauráveis.

**Os testes automatizados com remotos locais não equivalem à homologação com conta Google e Zorin OS físicos.**
