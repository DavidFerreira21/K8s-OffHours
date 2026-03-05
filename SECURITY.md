# Politica de Seguranca

## Versoes com suporte

Correcos de seguranca sao priorizadas para a versao mais recente de:

- Helm chart (`helm/k8s-offhours`)
- Base Kubernetes manifests (`k8s/base`)
- Python runtime script (`scripts/offhours.py`)

## Como reportar uma vulnerabilidade

Nao reporte vulnerabilidades de seguranca em issues publicas do GitHub.

Use um destes canais privados:

1. GitHub Security Advisories (preferencial):
   `Security` -> `Report a vulnerability`
2. Se Security Advisories nao estiver disponivel, contate os mantenedores em
   canal privado e compartilhe:
   - impacto e severidade
   - passos de reproducao
   - versoes afetadas
   - mitigacao sugerida (se conhecida)

## O que esperar

- Resposta inicial de triagem: ate 5 dias uteis
- Confirmacao e classificacao de severidade apos reproducao
- Correcao planejada conforme severidade e janela de release
- Divulgacao publica apos disponibilizacao da mitigacao

## Escopo

Exemplos em escopo:

- escalacao de privilegio via RBAC/manifests
- exposicao de token ou secret
- configuracao padrao insegura com risco ao dado/control plane

Fora de escopo:

- solicitacoes de suporte ou duvidas de uso (use Issues/Discussions)
- vulnerabilidades de terceiros sem possibilidade de correcao no projeto
