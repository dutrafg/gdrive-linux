# Drive para Linux 0.14.5 Alpha — desenvolvimento em blocos de 15 etapas

## Bloco 1 — etapas 1 a 15

1. Revalidar o MD5 de arquivos locais antes de enviá-los ao Drive.
2. Revalidar o MD5 do destino local antes de baixar uma edição remota.
3. Bloquear colisões quando um arquivo surge após o inventário.
4. Diferenciar histórico inexistente de histórico de sincronização corrompido.
5. Recusar snapshots de hashes malformados.
6. Recusar snapshots apontados por links simbólicos.
7. Aplicar o mesmo bloqueio aos fluxos manuais de revisão de exclusões.
8. Bloquear configuração de toda a pasta HOME como destino de sincronização.
9. Bloquear perfil cujo destino é um link simbólico.
10. Listar backups locais existentes por conta e pasta.
11. Restaurar versões em local seguro sem sobrescrever documentos atuais.
12. Adicionar controles GTK4 para listar, selecionar e restaurar versões.
13. Empacotar o módulo de recuperação no instalador.
14. Evitar que arquivos restaurados caiam novamente dentro da pasta espelhada.
15. Adicionar testes de regressão para colisões, históricos, links e recuperação.

## Bloco 2 — etapas 16 a 30

16. Centralizar a descoberta do caminho `rclone.conf` personalizado.
17. Persistir somente o caminho da configuração, sem copiar tokens OAuth.
18. Preservar as preferências quando um arquivo de configuração customizado desaparece.
19. Fazer a montagem FUSE usar a mesma configuração que a interface.
20. Fazer a sincronização contínua usar a mesma configuração com a janela fechada.
21. Adicionar seletor gráfico de `rclone.conf` e retorno à configuração padrão.
22. Testar prioridade entre configuração salva e variáveis de ambiente.
23. Testar persistência do arquivo escolhido e permissões privadas.
24. Alertar sobre `rclone.conf` ausente ou com permissões inseguras.
25. Testar diagnóstico de confidencialidade dos tokens OAuth.
26. Integrar os novos módulos Python ao pacote Debian.
27. Atualizar a versão Alpha para 0.14.5.
28. Integrar testes de recuperação e configuração ao workflow.
29. Atualizar documentação e checklist de QA.
30. Validar sintaxe, regressões, integração rclone e instalador no GitHub Actions.

## Limites da homologação

Os testes GitHub Actions usam Ubuntu e remotos locais do rclone, não a conta Google privada nem o desktop Zorin OS do usuário. Mesmo com CI aprovado, montar/editar/excluir no Google real, resolver bloqueio 403 e validar FUSE no kernel Zorin ainda exigem um teste local na máquina.

**Política de dados:** nenhum arquivo é removido automaticamente para concluir essas etapas; restaurações nunca substituem arquivos já presentes, e conflito interrompe a transferência para proteção.
