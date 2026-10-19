# QA — Drive para Linux v0.11.1 Alpha

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
