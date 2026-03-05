# K8s OffHours

K8s OffHours is a safe, GitOps-friendly toolkit for automated off-hours scaling of Kubernetes workloads.
Toolkit seguro e GitOps-friendly para escalonamento automatico de workloads Kubernetes fora do horario comercial.

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

Detalhes de arquitetura e fluxo interno: [architecture.md](docs/architecture.md).
Detalhes de modos e variaveis: [configuration.md](docs/configuration.md).
Guia tecnico Argo CD (usuario, token e RBAC): [argocd-offhours-user.md](docs/argocd-offhours-user.md).

## Observacoes importantes

- A solucao escala Pods/Deployments, nao desliga node diretamente.
- Para economia real de infraestrutura, o cluster precisa de node autoscaling (Cluster Autoscaler, Karpenter, etc.).
- Sem autoscaling, os pods reduzem, mas os nodes continuam ativos.
- Recomendado para HML; nao recomendado para producao sem avaliacao especifica.

Detalhes (RBAC, HPA, GitOps e seguranca): [operations.md](docs/operations.md).
Detalhes de custo e como obter economia real: [cost-optimization.md](docs/cost-optimization.md).

## Como usar em ambiente real

### 1) Build e publicacao da imagem

Build da imagem:

```bash
docker build -t <registry>/k8s-offhours:<tag> .
```

Push para o registry:

```bash
docker push <registry>/k8s-offhours:<tag>
```

Opcoes de build/deploy (kind, registry, multi-window): [deploy.md](docs/deploy.md).

### 2) Ajustar manifests base

Atualize a imagem nos CronJobs:

- `k8s/base/cronjob-shutdown.yaml`
- `k8s/base/cronjob-startup.yaml`

Defina variaveis em `k8s/base/config.yaml` (ConfigMap/Secret), principalmente:

- `SCHEDULE_NAME`
- `SCHEDULE_SCOPE`
- `ARGO_ENABLED`
- `DRY_RUN`
- `DEFAULT_STARTUP_REPLICAS`
- `PROTECTED_APP_STRICT_MODE`
- `ARGO_DISCOVERY_USE_AUTOMATIC`
- `ARGO_DISCOVERY_USE_MANUAL`
- `ARGO_SERVER` e `ARGO_TOKEN` (se `ARGO_ENABLED=true`)

Exemplo pratico de configuracao no ConfigMap:

```yaml
data:
  SCHEDULE_NAME: "dev"
  SCHEDULE_SCOPE: "namespace"
  ARGO_ENABLED: "false"
  ARGO_DISCOVERY_USE_AUTOMATIC: "true"
  ARGO_DISCOVERY_USE_MANUAL: "false"
  DRY_RUN: "false"
  DEFAULT_STARTUP_REPLICAS: "1"
  PROTECTED_APP_STRICT_MODE: "true"
```


Ajuste horarios dos CronJobs:

- `spec.schedule`
- `spec.timeZone`

Referencia completa de variaveis e modos: [configuration.md](docs/configuration.md).

### 3) Marcar os alvos

Se `SCHEDULE_SCOPE=namespace`, aplique label nos namespaces:

```yaml
metadata:
  labels:
    offhours.platform.io/schedule: "dev"
```

Nesse caso, configure `SCHEDULE_NAME=dev`.

Se `SCHEDULE_SCOPE=deployment`, aplique label nos deployments:

```yaml
metadata:
  labels:
    offhours.platform.io/schedule: "dev"
```

Nesse caso, configure `SCHEDULE_NAME=dev`.

Para proteger deployment critico:

```yaml
metadata:
  annotations:
    offhours.platform.io/protected: "true"
```

Mais exemplos de labels/annotations e descoberta de apps: [configuration.md](docs/configuration.md).

### 4) Instalar no cluster (metodo principal: Helm)

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
  --version 0.2.3
```

Instalar com Argo CD:

```bash
kubectl -n offhours-system create secret generic offhours-argocd \
  --from-literal=ARGO_SERVER='argocd-server.argocd.svc.cluster.local:80' \
  --from-literal=ARGO_TOKEN='<token>'

helm upgrade --install offhours k8s-offhours/k8s-offhours \
  -n offhours-system --create-namespace \
  --version 0.2.3 \
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

### Metodo manual (manifests base)

```bash
kubectl apply -k k8s/base
```

Passo a passo detalhado de deploy: [deploy.md](docs/deploy.md).

### 5) Testar manualmente antes de operar por schedule

Shutdown manual:

```bash
kubectl -n offhours-system delete job manual-shutdown --ignore-not-found
kubectl -n offhours-system create job --from=cronjob/offhours-shutdown manual-shutdown
kubectl -n offhours-system logs -f job/manual-shutdown
```

Startup manual:

```bash
kubectl -n offhours-system delete job manual-startup --ignore-not-found
kubectl -n offhours-system create job --from=cronjob/offhours-startup manual-startup
kubectl -n offhours-system logs -f job/manual-startup
```

Roteiro de cenarios de validacao: [scenarios.md](docs/scenarios.md).

## Estrutura do repositorio

```text
.
├── Dockerfile
├── Makefile
├── .env.example
├── scripts/
│   └── offhours.py
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

## Licenca

Este projeto esta sob a licenca MIT. Veja [LICENSE](LICENSE).
