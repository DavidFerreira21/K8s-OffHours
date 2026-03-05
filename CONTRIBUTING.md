# Contribuicao

Obrigado por contribuir com o K8s OffHours.

## Inicio rapido

1. Faca um fork do repositorio e crie uma branch a partir de `main`.
2. Instale as dependencias:

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

3. Execute os testes antes de abrir um PR:

```bash
pytest
```

4. Se voce alterou documentacao, mantenha links e comandos consistentes.
5. Abra um Pull Request com escopo claro e passos de validacao.

## Diretrizes de desenvolvimento

- Mantenha as mudancas focadas e pequenas.
- Prefira mudancas retrocompativeis.
- Atualize docs e exemplos quando o comportamento mudar.
- Nunca faca commit de secrets ou tokens.
- Use tags explicitas de imagem em manifests e valores do chart.

## Checklist de Pull Request

- [ ] Testes passam localmente (`pytest`)
- [ ] Docs atualizadas (README/docs) quando necessario
- [ ] Retrocompatibilidade considerada
- [ ] Sem dados sensiveis nos commits
- [ ] Changelog atualizado para mudancas visiveis ao usuario

## Estilo de commit (recomendado)

- `feat: ...` para nova funcionalidade
- `fix: ...` para correcao de bug
- `docs: ...` para alteracoes somente de documentacao
- `refactor: ...` para melhorias sem mudanca de comportamento

## Como reportar issues

- Bug report: use o template de Bug.
- Feature request: use o template de Melhoria.
- Problema de seguranca: nao abra issue publica. Siga `SECURITY.md`.
