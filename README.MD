# K8s OffHours

K8s OffHours is a safe, GitOps-friendly toolkit for automated off-hours scaling of Kubernetes workloads.
Toolkit seguro e GitOps-friendly para escalonamento automatico de workloads Kubernetes fora do horario comercial.

## O que este projeto entrega

- Shutdown e startup automatizados via `CronJob`
- Operacao em dois modos:
  - `ARGO_ENABLED=true` (integracao Argo CD)
  - `ARGO_ENABLED=false` (somente Kubernetes)
- Selecao de alvos por schedule label
- Exclusao de deployments criticos por annotation
- Estrutura pronta para deploy em cluster

## Design Principles

- Declarative first: selecao baseada em labels
- Idempotent operations: execucoes repetidas nao causam inconsistencias
- GitOps-friendly: integracao opcional com Argo CD
- Cloud-agnostic: compativel com qualquer Kubernetes com autoscaling
- Minimal surface area: sem CRD e sem Operator

## Estrutura do repositorio

```text
.
├── Dockerfile
├── Makefile
├── .env.example
├── scripts/
│   └── offhours.py
└── k8s/
    ├── base/
    │   ├── kustomization.yaml
    │   ├── namespace.yaml
    │   ├── rbac.yaml
    │   ├── config.yaml
    │   ├── cronjob-shutdown.yaml
    │   ├── cronjob-startup.yaml
    │   └── multi-window/
    │       ├── kustomization.yaml
    │       ├── config-dev-weekday.yaml
    │       ├── config-qa-weekday.yaml
    │       ├── cronjob-shutdown-dev-weekday.yaml
    │       ├── cronjob-startup-dev-weekday.yaml
    │       ├── cronjob-shutdown-qa-weekday.yaml
    │       └── cronjob-startup-qa-weekday.yaml
    └── examples/
        └── scenarios/
            ├── scenario-1-namespace-scope.yaml
            ├── scenario-2-deployment-scope.yaml
            ├── scenario-3-argopp-override.yaml
            └── scenario-4-mixed-protected-app.yaml
```

## Como funciona

### 1) Escopo do schedule (`SCHEDULE_SCOPE`)

- `namespace` (padrao): seleciona namespaces por label de schedule
- `deployment`: seleciona deployments por label de schedule (sem depender de label no namespace)

Label usada nos dois modos:

- `offhours.platform.io/schedule: "<nome-do-schedule>"`

### 2) Namespace targeting (`SCHEDULE_SCOPE=namespace`)

Somente namespaces com esta label entram no schedule:

```yaml
metadata:
  labels:
    offhours.platform.io/schedule: "dev"
```

### 3) Deployment targeting (`SCHEDULE_SCOPE=deployment`)

Somente deployments com esta label entram no schedule:

```yaml
metadata:
  labels:
    offhours.platform.io/schedule: "dev"
```

### 4) Deployment protegido

Deployments com esta annotation nunca sao escalados:

```yaml
metadata:
  annotations:
    offhours.platform.io/protected: "true"
```

### 5) Modo com Argo CD (`ARGO_ENABLED=true`)

A implementacao Python usa Argo CD API mode (`endpoint + token`), sem dependencia de `argocd` CLI.

No `shutdown`:

- pausa sync das Applications elegiveis
- escala deployments elegiveis para `0`

No `startup`:

- reativa sync das Applications
- dispara sync da Application

Se nao encontrar app em um namespace/deployment, registra erro em log e continua nos demais.

#### Descoberta de Application (Argo)

Ordem de descoberta:

1. `argocd.argoproj.io/instance` (label)
2. `argocd.argoproj.io/tracking-id` (annotation)
3. `offhours.platform.io/argopp` (override por namespace)
4. fallback por `spec.destination.namespace` na API do Argo

Defaults recomendados:

- metodos 1 e 2 habilitados
- metodos 3 e 4 desabilitados

Exemplo de override no namespace:

```yaml
metadata:
  labels:
    offhours.platform.io/argopp: "smb-app,billing-app"
```

#### Protecao em apps mistas (protegido + nao protegido)

Use `PROTECTED_APP_STRICT_MODE`:

- `true` (recomendado): se uma app tiver qualquer deployment protegido, o script nao pausa sync dessa app e nao escala nenhum deployment dela
- `false`: pausa sync da app e escala apenas deployments nao protegidos

#### Operacao manual no Argo (opcional)

Tambem e possivel operar mantendo sincronizacao no Argo de forma manual/politica:

- configurar `Sync Policy` manualmente por Application
- configurar `Sync Windows` no Argo CD

Vantagens:

- nao exige `ARGO_SERVER` e `ARGO_TOKEN` no CronJob
- reduz acoplamento e exposicao de credenciais
- facilita coexistencia com outras ferramentas GitOps (ex.: Flux)

Atencao:

- se houver reconciliacao automatica ativa, `replicas=0` pode ser revertido

### 6) Modo sem Argo (`ARGO_ENABLED=false`)

No `shutdown`:

- salva replicas originais em annotation
- escala para `0`

No `startup`:

- restaura replicas da annotation
- fallback para `DEFAULT_STARTUP_REPLICAS` (padrao `1`)

## Variaveis de ambiente

| Variavel | Obrigatoria | Descricao |
| --- | --- | --- |
| `SCHEDULE_NAME` | Sim | Nome do schedule (valor da label) |
| `SCHEDULE_SCOPE` | Nao | `namespace` (padrao) ou `deployment` |
| `ACTION` | Sim | `shutdown` ou `startup` |
| `ARGO_ENABLED` | Sim | `true` ou `false` |
| `ARGO_SERVER` | Se `ARGO_ENABLED=true` | Endpoint do Argo CD (host:porta) |
| `ARGO_TOKEN` | Se `ARGO_ENABLED=true` | Token de API do Argo CD |
| `ARGO_SCHEME` | Nao | `https` (padrao) ou `http` |
| `ARGO_INSECURE` | Nao | `true` para ignorar validacao TLS em `https` |
| `ARGO_DISCOVERY_USE_INSTANCE_LABEL` | Nao | Habilita descoberta por `instance` (padrao: `true`) |
| `ARGO_DISCOVERY_USE_TRACKING_ID` | Nao | Habilita descoberta por `tracking-id` (padrao: `true`) |
| `ARGO_DISCOVERY_USE_ARGOPP` | Nao | Habilita override `offhours.platform.io/argopp` (padrao: `false`) |
| `ARGO_DISCOVERY_USE_DEST_NAMESPACE_FALLBACK` | Nao | Habilita fallback por destination namespace (padrao: `false`) |
| `ARGO_API_RETRIES` | Nao | Retries para erro transiente da API Argo (padrao agressivo: `2`) |
| `ARGO_API_RETRY_BASE_SECONDS` | Nao | Backoff base em segundos (padrao agressivo: `0.2`) |
| `ARGO_API_RETRY_MAX_SECONDS` | Nao | Teto do backoff em segundos (padrao agressivo: `1.0`) |
| `VERBOSE` | Nao | Logs detalhados (`true/false`) |
| `DRY_RUN` | Nao | Nao executa mudancas (`true/false`) |
| `DEFAULT_STARTUP_REPLICAS` | Nao | Replica padrao no startup sem annotation |
| `PROTECTED_APP_STRICT_MODE` | Nao | `true` (seguro) ou `false` (agressivo) |

## Arquitetura do script Python

Arquivo principal: `scripts/offhours.py`

Blocos principais:

- Validacao e parsing de ambiente: `validate_env`, `env_*`
- Integracao Kubernetes: `kubectl_get`, `get_target_*`, `scale_deployment`
- Integracao Argo API: `argo_request`, `get_all_applications`, `get_app`
- Descoberta de app: `get_argocd_apps_from_namespace`, `get_argocd_app_for_deployment`
- Orquestracao por escopo/acao: `handle_*` e `main`

## Requisitos

- Cluster Kubernetes com `kubectl` configurado
- Ferramentas no container: `python3`, `kubectl`, `curl`, `ca-certificates`

## Idempotencia

- Se um deployment ja estiver com `replicas=0`, nao falha
- Se `offhours.platform.io/original-replicas` ja existir, nao sobrescreve
- No modo Argo, se a app ja estiver pausada, nao gera erro fatal

## Permissoes necessarias (RBAC)

A ServiceAccount do CronJob precisa de:

- `get/list` em namespaces
- `get/list/patch/update` em deployments
- `get/patch/update` em `deployments/scale`
- `get/list` em replicasets (opcional)

Se usar Argo:

- permissao Argo RBAC para `applications get/update/sync` nas apps alvo

## Node autoscaling

Importante: este toolkit escala apenas Deployments.

Para gerar reducao real de custo em infraestrutura, o cluster precisa de autoscaling de nodes:

- Cluster Autoscaler
- Karpenter
- VMSS Autoscaling (AKS)
- Node Auto Provisioning (GKE)

Sem autoscaling, os pods saem, mas os nodes continuam ativos.

## Comportamento com HPA

O script escala diretamente o Deployment para `replicas=0`.

- No modo Argo: o estado desejado volta via Git no startup
- No modo sem Argo: o HPA permanece configurado e o Deployment e escalado manualmente

Observacao: com metricas ativas, HPA pode redefinir replicas. Valide em ambiente com HPA ativo.

## Interacao com ferramentas GitOps

Se houver sincronizacao automatica em Argo/Flux/etc., `replicas=0` pode ser revertido.

Recomendacoes:

- pausar sincronizacao no shutdown (modo Argo)
- configurar Sync Windows
- ou usar operacao manual de sincronizacao

## Seguranca de credenciais

Se precisar de credenciais externas, nao versionar secrets em texto claro.

Recomendado:

- External Secrets
- Sealed Secrets
- HashiCorp Vault

Guia tecnico Argo deste projeto:

- `docs/argocd-offhours-user.md`

## Deploy no cluster

### Opcao 1: Janela unica (`k8s/base`)

1. Ajuste a imagem em:
- `k8s/base/cronjob-shutdown.yaml`
- `k8s/base/cronjob-startup.yaml`

2. Ajuste timezone:
- `spec.timeZone: "America/Sao_Paulo"` nos dois manifests

3. Ajuste `k8s/base/config.yaml`:
- `SCHEDULE_NAME`
- `SCHEDULE_SCOPE`
- `ARGO_ENABLED`
- `VERBOSE`
- `DRY_RUN`
- `DEFAULT_STARTUP_REPLICAS`
- `PROTECTED_APP_STRICT_MODE`

4. Se usar Argo, preencha `ARGO_SERVER` e `ARGO_TOKEN` no Secret.

5. Aplique:

```bash
kubectl apply -k k8s/base
```

### Opcao 2: Multiplas janelas (`k8s/base/multi-window`)

Use mais de um par de CronJobs com schedules diferentes.

Exemplos:

- `dev-weekday`: desliga `20:00`, liga `08:00` (seg-sex)
- `qa-weekday`: desliga `22:00`, liga `07:00` (seg-sex)

Rotule conforme a janela:

```yaml
metadata:
  labels:
    offhours.platform.io/schedule: "dev-weekday"
```

Se `SCHEDULE_SCOPE=deployment`, aplique label direto nos deployments.

Aplique:

```bash
kubectl apply -k k8s/base/multi-window
```

## Execucao local

1. Copie `.env.example` para `.env` e ajuste valores
2. Rode:

```bash
make run-shutdown
make run-startup
```

## Build da imagem

```bash
make build IMAGE=docker.io/davidferreira21/k8s-offhours:latest
```

## Exemplos de cenarios

```bash
kubectl apply -f k8s/examples/scenarios/scenario-1-namespace-scope.yaml
kubectl apply -f k8s/examples/scenarios/scenario-2-deployment-scope.yaml
kubectl apply -f k8s/examples/scenarios/scenario-3-argopp-override.yaml
kubectl apply -f k8s/examples/scenarios/scenario-4-mixed-protected-app.yaml
```

Cenarios incluidos:

- `scenario-1-namespace-scope.yaml`: `SCHEDULE_SCOPE=namespace` com deployment protegido
- `scenario-2-deployment-scope.yaml`: `SCHEDULE_SCOPE=deployment` com label no deployment
- `scenario-3-argopp-override.yaml`: override de apps Argo via `offhours.platform.io/argopp`
- `scenario-4-mixed-protected-app.yaml`: app mista para testar `PROTECTED_APP_STRICT_MODE`

## Limitacoes

- Nao manipula infraestrutura diretamente, apenas replicas de deployments
- Nao silencia alertas
- Sem node autoscaling nao ha economia de infraestrutura

## Recomendacao de uso

- Recomendado para ambientes HML com foco em reducao de custo fora do horario comercial
- Nao recomendado para producao

## Proximos passos sugeridos

- Mover Secret para External Secrets/Vault
- Adicionar suporte a StatefulSet (opcional)
- Publicar imagem CI/CD com versionamento semantico
