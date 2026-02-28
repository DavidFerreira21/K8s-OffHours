# K8s OffHours

K8s OffHours is a safe, GitOps-friendly toolkit for automated off-hours scaling of Kubernetes workloads.
Toolkit seguro e GitOps-friendly para escalonamento automatico de workloads Kubernetes fora do horario comercial.

## O que a solucao resolve

K8s OffHours automatiza o desligamento e religamento de workloads Kubernetes fora do horario de uso para reduzir custo em ambientes nao produtivos (principalmente HML).

Exemplo comum:

- ambiente HML ativo das `08:00` as `20:00` (seg-sex)
- fora dessa janela, workloads sao escalados para `0`

Comparado com operacao 24x7, uma janela de 12h por dia util representa potencial de reducao de horas de worker node em torno de `64.3%`.

Detalhes de operacao, limites e premissas: `docs/operations.md`.

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

Detalhes de arquitetura e fluxo interno: `docs/architecture.md`.
Detalhes de modos e variaveis: `docs/configuration.md`.
Guia tecnico Argo CD (usuario, token e RBAC): `docs/argocd-offhours-user.md`.

## Observacoes importantes

- A solucao escala Pods/Deployments, nao desliga node diretamente.
- Para economia real de infraestrutura, o cluster precisa de node autoscaling (Cluster Autoscaler, Karpenter, etc.).
- Sem autoscaling, os pods reduzem, mas os nodes continuam ativos.
- Recomendado para HML; nao recomendado para producao sem avaliacao especifica.

Detalhes (RBAC, HPA, GitOps e seguranca): `docs/operations.md`.

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

Opcoes de build/deploy (kind, registry, multi-window): `docs/deploy.md`.

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
- `ARGO_SERVER` e `ARGO_TOKEN` (se `ARGO_ENABLED=true`)

Exemplo pratico de configuracao no ConfigMap:

```yaml
data:
  SCHEDULE_NAME: "dev"
  SCHEDULE_SCOPE: "namespace"
  ARGO_ENABLED: "false"
  DRY_RUN: "false"
  DEFAULT_STARTUP_REPLICAS: "1"
  PROTECTED_APP_STRICT_MODE: "true"
```


Ajuste horarios dos CronJobs:

- `spec.schedule`
- `spec.timeZone`

Referencia completa de variaveis e modos: `docs/configuration.md`.

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

Mais exemplos de labels/annotations e descoberta de apps: `docs/configuration.md`.

### 4) Aplicar no cluster

```bash
kubectl apply -k k8s/base
```

Passo a passo detalhado de deploy: `docs/deploy.md`.

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

Roteiro de cenarios de validacao: `docs/scenarios.md`.

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

Se esta chegando agora, comece por: `docs/README.md`.

## Documentacao detalhada

- Arquitetura e fluxo interno: `docs/architecture.md`
- Modos de operacao e variaveis: `docs/configuration.md`
- Deploy detalhado (base e multi-window): `docs/deploy.md`
- Operacao, RBAC, HPA, GitOps e seguranca: `docs/operations.md`
- Cenarios de validacao: `docs/scenarios.md`
- Guia tecnico Argo CD (usuario/token/RBAC): `docs/argocd-offhours-user.md`
