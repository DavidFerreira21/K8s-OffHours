# Arquitetura

## Design principles

- Declarative first: selecao baseada em labels
- Idempotent operations: execucoes repetidas nao causam inconsistencias
- GitOps-friendly: integracao opcional com Argo CD
- Cloud-agnostic: compativel com qualquer Kubernetes com autoscaling
- Minimal surface area: sem CRD e sem Operator

## Como funciona

### Escopo do schedule (`SCHEDULE_SCOPE`)

- `namespace` (padrao): seleciona namespaces por label de schedule
- `deployment`: seleciona deployments por label de schedule

Label usada nos dois modos:

- `offhours.platform.io/schedule: "<nome-do-schedule>"`

### Protecao de deployment

Deployments com annotation abaixo nunca sao escalados:

```yaml
metadata:
  annotations:
    offhours.platform.io/protected: "true"
```

### Modo com Argo CD (`ARGO_ENABLED=true`)

No `shutdown`:

- pausa sync das Applications elegiveis
- escala deployments elegiveis para `0`

No `startup`:

- reativa sync das Applications
- dispara sync da Application

### Descoberta de Application no Argo

Ordem de descoberta:

1. `offhours.platform.io/argopp` (override manual por namespace), quando `ARGO_DISCOVERY_USE_MANUAL=true`
2. cadeia automatica, quando `ARGO_DISCOVERY_USE_AUTOMATIC=true`:
   - `argocd.argoproj.io/instance` (label)
   - `argocd.argoproj.io/tracking-id` (annotation)
   - fallback por `spec.destination.namespace` na API do Argo

Defaults recomendados:

- automatico habilitado
- manual desabilitado

### Protecao em apps mistas (`PROTECTED_APP_STRICT_MODE`)

- `true` (recomendado): se uma app tiver deployment protegido, nao pausa sync nem escala deployments da app
- `false`: pausa sync da app e escala apenas deployments nao protegidos

### Modo sem Argo (`ARGO_ENABLED=false`)

No `shutdown`:

- salva replicas originais em annotation
- escala para `0`

No `startup`:

- restaura replicas da annotation
- fallback para `DEFAULT_STARTUP_REPLICAS`

## Idempotencia

- Se deployment ja estiver em `replicas=0`, nao falha
- Se `offhours.platform.io/original-replicas` ja existir, nao sobrescreve
- No modo Argo, se app ja estiver pausada, nao gera erro fatal

## Arquivo principal

- `scripts/offhours.py`

Blocos principais:

- validacao e parsing de ambiente (`validate_env`, `env_*`)
- integracao Kubernetes (`kubectl_get`, `get_target_*`, `scale_deployment`)
- integracao Argo API (`argo_request`, `get_all_applications`, `get_app`)
- descoberta de app (`get_argocd_apps_from_namespace`, `get_argocd_app_for_deployment`)
- orquestracao por escopo/acao (`handle_*`, `main`)
