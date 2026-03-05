# Guia de Mantenedores

Este arquivo define um modelo basico de triagem para repositorio publico.

## Labels recomendadas

Crie estas labels:

- `bug` (`#d73a4a`)
- `enhancement` (`#a2eeef`)
- `documentation` (`#0075ca`)
- `good first issue` (`#7057ff`)
- `help wanted` (`#008672`)
- `question` (`#d876e3`)
- `prioridade:alta` (`#b60205`)
- `prioridade:media` (`#fbca04`)
- `prioridade:baixa` (`#0e8a16`)
- `status:triagem` (`#ededed`)
- `status:bloqueado` (`#5319e7`)
- `status:em-progresso` (`#1d76db`)

## Milestones recomendadas

- `proximo-patch` (bugs/docs que podem sair rapido)
- `proximo-minor` (features e melhorias sem quebra)
- `quebra-proximo-major` (mudancas com quebra e migracao)

## Configuracao via GitHub CLI

Execute uma vez (requer `gh auth login`):

```bash
gh label create bug --color d73a4a --description "Algo nao esta funcionando" --force
gh label create enhancement --color a2eeef --description "Nova feature ou melhoria" --force
gh label create documentation --color 0075ca --description "Melhoria de documentacao" --force
gh label create "good first issue" --color 7057ff --description "Boa para iniciantes" --force
gh label create "help wanted" --color 008672 --description "Ajuda da comunidade bem-vinda" --force
gh label create question --color d876e3 --description "Mais informacoes sao necessarias" --force
gh label create "prioridade:alta" --color b60205 --description "Alta prioridade" --force
gh label create "prioridade:media" --color fbca04 --description "Media prioridade" --force
gh label create "prioridade:baixa" --color 0e8a16 --description "Baixa prioridade" --force
gh label create "status:triagem" --color ededed --description "Aguardando triagem" --force
gh label create "status:bloqueado" --color 5319e7 --description "Bloqueado por dependencia ou decisao externa" --force
gh label create "status:em-progresso" --color 1d76db --description "Trabalho iniciado" --force
```

Crie milestones na interface do GitHub:

`Issues` -> `Milestones` -> `New milestone`

Use os tres nomes de milestone listados acima.
