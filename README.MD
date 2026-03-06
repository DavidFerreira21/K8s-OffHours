# K8s OffHours

![Helm](https://img.shields.io/badge/helm-chart-blue)
![Docker](https://img.shields.io/badge/docker-image-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/github/license/DavidFerreira21/K8s-OffHours)

Helm repo: https://davidferreira21.github.io/K8s-OffHours

K8s OffHours e uma solucao nativa para Kubernetes que automatiza o desligamento e religamento de workloads fora do horario comercial, reduzindo custos de infraestrutura com seguranca em ambientes nao produtivos.

## O que a solucao resolve

K8s OffHours automatiza o desligamento e religamento de workloads Kubernetes fora do horario de uso para reduzir custo em ambientes nao produtivos (principalmente HML).

Exemplo comum:

- ambiente HML ativo das `08:00` as `20:00` (seg-sex)
- fora dessa janela, workloads sao escalados para `0`

Comparado com operacao 24x7, uma janela de 12h por dia util representa potencial de reducao de horas de worker node em torno de `64.3%`.

Detalhes de operacao, limites e premissas: [operations.md](docs/operations.md).
Detalhes de estrategia de economia e autoscaling de nos: [cost-optimization.md](docs/cost-optimization.md).

## Como funciona

A solucao roda via `CronJob` e executa duas acoes:

- `shutdown`: salva replicas atuais e escala Deployments elegiveis para `0`
- `startup`: restaura replicas salvas (ou fallback configurado)

Ela suporta dois modos de selecao de alvo:

- `SCHEDULE_SCOPE=namespace`: seleciona namespaces por label
- `SCHEDULE_SCOPE=deployment`: seleciona deployments por label

Label de schedule usada:

- `offhours.platform.io/schedule=<schedule-name>`
- `SCHEDULE_NAME` deve ser exatamente o mesmo valor de `<schedule-name>`

Protecao de workloads criticos:

- annotation `offhours.platform.io/protected=true` impede scale desse deployment

Modo GitOps:

- `ARGO_ENABLED=true`: integra com Argo CD (API), pausa/reativa sync
- `ARGO_ENABLED=false`: atua apenas em Kubernetes
- descoberta de app Argo:
  - `ARGO_DISCOVERY_USE_MANUAL=true`: usa override `offhours.platform.io/argopp` (prioridade 1)
  - `ARGO_DISCOVERY_USE_AUTOMATIC=true`: usa cadeia automatica (`instance`, `tracking-id`, fallback por destination namespace)

Com `PROTECTED_APP_STRICT_MODE=true`:

- no `shutdown`, app com qualquer deployment protegido nao e pausada e nao tem deployments escalados
- no `startup`, essa app tambem nao recebe `resume/sync`

Modos de HPA (opcional):

- `HPA_MIN_ZERO_ENABLED=true`: tenta `minReplicas=0` no shutdown e restaura no startup (best-effort)
- `HPA_DELETE_RESTORE_ENABLED=true`: salva HPA em ConfigMap tecnico, deleta no shutdown e recria no startup
- `HPA_DELETE_ONLY_ENABLED=true`: deleta HPA no shutdown sem salvar estado e nao restaura no startup
- com `HPA_DELETE_ONLY_ENABLED=true`, sem GitOps (Argo/Flux) ou sem recriacao manual, o HPA ficara ausente (perdido)
- se `HPA_DELETE_ONLY_ENABLED=true` e `HPA_DELETE_RESTORE_ENABLED=true`, prevalece `HPA_DELETE_RESTORE_ENABLED`

Detalhes de arquitetura e fluxo interno: [architecture.md](docs/architecture.md).
Detalhes de modos e variaveis: [configuration.md](docs/configuration.md).
Guia tecnico Argo CD (usuario, token e RBAC): [argocd-offhours-user.md](docs/argocd-offhours-user.md).

## Architecture Overview

```text
Helm chart
   ↓
CronJobs (shutdown/startup)
   ↓
Python engine (offhours.py)
   ↓
Kubernetes API
   ↓
Argo CD API (optional)
```

Fluxo simplificado de shutdown:

```text
CronJob shutdown
      ↓
Scale deployments -> 0
      ↓
Node autoscaler remove nodes (when enabled)
```

## Quando usar

Recomendado para:

- clusters de desenvolvimento
- ambientes de staging
- ambientes de HML


## Observacoes importantes

- A solucao escala Pods/Deployments, nao desliga node diretamente.
- Para economia real de infraestrutura, o cluster precisa de node autoscaling (Cluster Autoscaler, Karpenter, etc.).
- Sem autoscaling, os pods reduzem, mas os nodes continuam ativos.
- Recomendado para HML; nao recomendado para producao sem avaliacao especifica.

Detalhes (RBAC, HPA, GitOps e seguranca): [operations.md](docs/operations.md).
Detalhes de custo e como obter economia real: [cost-optimization.md](docs/cost-optimization.md).

## Como usar em ambiente real

### 1) Instalar via Helm

Adicionar repo Helm publicado no GitHub Pages:

```bash
helm repo add k8s-offhours https://davidferreira21.github.io/K8s-OffHours
helm repo update
helm search repo k8s-offhours --versions
```

Instalar sem Argo CD (padrao):

```bash
helm upgrade --install offhours k8s-offhours/k8s-offhours \
  -n offhours-system --create-namespace \
  --version 0.2.1 \
  --set config.scheduleName=dev \
  --set config.scheduleScope=namespace
```

Observacao:
- no chart, o `config.scheduleName` padrao e `default`
- se seus namespaces/deployments usam `offhours.platform.io/schedule=dev`, ajuste `config.scheduleName=dev`

Instalar com Argo CD:

```bash
kubectl -n offhours-system create secret generic offhours-argocd \
  --from-literal=ARGO_SERVER='argocd-server.argocd.svc.cluster.local:80' \
  --from-literal=ARGO_TOKEN='<token>'

helm upgrade --install offhours k8s-offhours/k8s-offhours \
  -n offhours-system --create-namespace \
  --version 0.2.1 \
  --set config.scheduleName=dev \
  --set config.scheduleScope=namespace \
  --set argocd.enabled=true \
  --set argocd.existingSecret=offhours-argocd
```

Upgrade para nova versao do chart:

```bash
helm repo update
helm upgrade offhours k8s-offhours/k8s-offhours \
  -n offhours-system \
  --version <nova-versao>
```

Instalacao local (desenvolvimento):

```bash
helm upgrade --install offhours ./helm/k8s-offhours \
  -n offhours-system --create-namespace
```

Multi-window com Helm (uma release por janela):

```bash
# janela dev-weekday
helm upgrade --install offhours-dev k8s-offhours/k8s-offhours \
  -n offhours-system --create-namespace \
  --version 0.2.1 \
  --set schedule.shutdown="0 20 * * 1-5" \
  --set schedule.startup="0 8 * * 1-5" \
  --set schedule.timeZone="America/Sao_Paulo" \
  --set config.scheduleName="dev-weekday" \
  --set config.scheduleScope="namespace" \
  --set argocd.enabled=false

# janela qa-weekday
helm upgrade --install offhours-qa k8s-offhours/k8s-offhours \
  -n offhours-system \
  --version 0.2.1 \
  --set schedule.shutdown="0 22 * * 1-5" \
  --set schedule.startup="0 9 * * 1-5" \
  --set schedule.timeZone="America/Sao_Paulo" \
  --set config.scheduleName="qa-weekday" \
  --set config.scheduleScope="namespace" \
  --set argocd.enabled=false
```

### 2) Testar manualmente antes de operar por schedule

Verifique os nomes dos CronJobs criados pelo Helm:

```bash
kubectl -n offhours-system get cronjob
```

Shutdown manual:

```bash
kubectl -n offhours-system delete job manual-shutdown --ignore-not-found
kubectl -n offhours-system create job --from=cronjob/offhours-k8s-offhours-shutdown manual-shutdown
kubectl -n offhours-system logs -f job/manual-shutdown
```

Startup manual:

```bash
kubectl -n offhours-system delete job manual-startup --ignore-not-found
kubectl -n offhours-system create job --from=cronjob/offhours-k8s-offhours-startup manual-startup
kubectl -n offhours-system logs -f job/manual-startup
```

Roteiro de cenarios de validacao: [scenarios.md](docs/scenarios.md).

### 3) Aplicar label no alvo desejado (obrigatorio)

Ao final da instalacao/configuracao, aplique a label com o mesmo valor de `scheduleName`:

```bash
# quando SCHEDULE_SCOPE=namespace
kubectl label ns <namespace> offhours.platform.io/schedule=<schedule-name> --overwrite

# quando SCHEDULE_SCOPE=deployment
kubectl -n <namespace> label deploy <deployment> offhours.platform.io/schedule=<schedule-name> --overwrite
```

### Fluxos legados e avancados

- Deploy manual com manifests base (`kubectl apply -k`) e opcoes avancadas: [deploy.md](docs/deploy.md)
- Referencia completa de variaveis e modos: [configuration.md](docs/configuration.md)

## Estrutura do repositorio

```text
.
├── Dockerfile
├── Makefile
├── .env.example
├── scripts/
│   └── offhours.py
├── helm/
│   └── k8s-offhours/
├── docs/
│   ├── architecture.md
│   ├── configuration.md
│   ├── deploy.md
│   ├── operations.md
│   ├── scenarios.md
│   └── argocd-offhours-user.md
└── k8s/
    ├── base/
    └── examples/
```

## Inicio rapido da documentacao

Se esta chegando agora, comece por: [docs/README.md](docs/README.md).

## Documentacao detalhada

- Arquitetura e fluxo interno: [architecture.md](docs/architecture.md)
- Modos de operacao e variaveis: [configuration.md](docs/configuration.md)
- Deploy detalhado (base e multi-window): [deploy.md](docs/deploy.md)
- Operacao, RBAC, HPA, GitOps e seguranca: [operations.md](docs/operations.md)
- Otimizacao de custo e integracao com autoscaling de nos: [cost-optimization.md](docs/cost-optimization.md)
- Cenarios de validacao: [scenarios.md](docs/scenarios.md)
- Guia tecnico Argo CD (usuario/token/RBAC): [argocd-offhours-user.md](docs/argocd-offhours-user.md)

## Governanca open source

- Guia de contribuicao: [CONTRIBUTING.md](CONTRIBUTING.md)
- Codigo de conduta: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- Politica de seguranca: [SECURITY.md](SECURITY.md)
- Guia de mantenedores (labels/milestones): [.github/MAINTAINER_GUIDE.md](.github/MAINTAINER_GUIDE.md)

## Licenca

Este projeto esta sob a licenca MIT. Veja [LICENSE](LICENSE).
