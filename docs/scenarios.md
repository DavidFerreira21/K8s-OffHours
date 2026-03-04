# Cenarios de exemplo

Aplicar cenarios:

```bash
kubectl apply -f k8s/examples/scenarios/scenario-1-namespace-scope.yaml
kubectl apply -f k8s/examples/scenarios/scenario-2-deployment-scope.yaml
kubectl apply -f k8s/examples/scenarios/scenario-3-argopp-override.yaml
kubectl apply -f k8s/examples/scenarios/scenario-4-mixed-protected-app.yaml
```

Aplicar os 4 cenarios via Argo CD (um Application):

```bash
kubectl apply -f k8s/examples/scenarios/argocd-application-scenarios.yaml
```

Antes de aplicar, ajuste `spec.source.repoURL` no arquivo `k8s/examples/scenarios/argocd-application-scenarios.yaml`.

Regra base para todos os cenarios:

- `SCHEDULE_NAME` deve ser exatamente igual ao valor da label `offhours.platform.io/schedule` usada no alvo.

## Scenario 1 - Namespace scope

Arquivo: `k8s/examples/scenarios/scenario-1-namespace-scope.yaml`

Valida:

- selecao por namespace (`SCHEDULE_SCOPE=namespace`)
- deployment protegido por annotation

Variaveis recomendadas:

```yaml
data:
  SCHEDULE_NAME: "dev-weekday"
  SCHEDULE_SCOPE: "namespace"
  ARGO_ENABLED: "false"
  DRY_RUN: "false"
  PROTECTED_APP_STRICT_MODE: "true"
  DEFAULT_STARTUP_REPLICAS: "1"
```

Exemplo de patch rapido:

```bash
kubectl -n offhours-system patch configmap offhours-config --type merge -p '{
  "data":{
    "SCHEDULE_NAME":"dev-weekday",
    "SCHEDULE_SCOPE":"namespace",
    "ARGO_ENABLED":"false",
    "DRY_RUN":"false",
    "PROTECTED_APP_STRICT_MODE":"true",
    "DEFAULT_STARTUP_REPLICAS":"1"
  }
}'
```

## Scenario 2 - Deployment scope

Arquivo: `k8s/examples/scenarios/scenario-2-deployment-scope.yaml`

Valida:

- selecao por deployment (`SCHEDULE_SCOPE=deployment`)
- protecao por annotation no deployment

Variaveis recomendadas:

```yaml
data:
  SCHEDULE_NAME: "dev"
  SCHEDULE_SCOPE: "deployment"
  ARGO_ENABLED: "false"
  DRY_RUN: "false"
  PROTECTED_APP_STRICT_MODE: "true"
  DEFAULT_STARTUP_REPLICAS: "1"
```

Exemplo de patch rapido:

```bash
kubectl -n offhours-system patch configmap offhours-config --type merge -p '{
  "data":{
    "SCHEDULE_NAME":"dev",
    "SCHEDULE_SCOPE":"deployment",
    "ARGO_ENABLED":"false",
    "DRY_RUN":"false",
    "PROTECTED_APP_STRICT_MODE":"true",
    "DEFAULT_STARTUP_REPLICAS":"1"
  }
}'
```

## Scenario 3 - Argo app override (`argopp`)

Arquivo: `k8s/examples/scenarios/scenario-3-argopp-override.yaml`

Valida:

- descoberta de Application via `offhours.platform.io/argopp`
- operacao com Argo API mode

Variaveis recomendadas:

```yaml
data:
  SCHEDULE_NAME: "dev-weekday"
  SCHEDULE_SCOPE: "namespace"
  ARGO_ENABLED: "true"
  DRY_RUN: "false"
  PROTECTED_APP_STRICT_MODE: "true"
  ARGO_DISCOVERY_USE_INSTANCE_LABEL: "false"
  ARGO_DISCOVERY_USE_TRACKING_ID: "false"
  ARGO_DISCOVERY_USE_ARGOPP: "true"
  ARGO_DISCOVERY_USE_DEST_NAMESPACE_FALLBACK: "false"
```

Secret necessario (exemplo):

```yaml
stringData:
  ARGO_SERVER: "argocd-server.argocd.svc.cluster.local:80"
  ARGO_TOKEN: "<token>"
```

## Scenario 4 - App mista (protegido + nao protegido)

Arquivo: `k8s/examples/scenarios/scenario-4-mixed-protected-app.yaml`

Valida:

- efeito de `PROTECTED_APP_STRICT_MODE` em app com recursos mistos

### Modo seguro (recomendado)

```yaml
data:
  SCHEDULE_NAME: "dev-weekday"
  SCHEDULE_SCOPE: "namespace"
  ARGO_ENABLED: "true"
  DRY_RUN: "false"
  PROTECTED_APP_STRICT_MODE: "true"
```

Resultado esperado:

- se a app tiver qualquer deployment protegido, a app nao e pausada e nenhum deployment da app e escalado

### Modo agressivo

```yaml
data:
  SCHEDULE_NAME: "dev-weekday"
  SCHEDULE_SCOPE: "namespace"
  ARGO_ENABLED: "true"
  DRY_RUN: "false"
  PROTECTED_APP_STRICT_MODE: "false"
```

Resultado esperado:

- app pode ser pausada normalmente
- apenas deployments protegidos sao ignorados

## Comandos de validacao manual (todos os cenarios)

Shutdown:

```bash
kubectl -n offhours-system delete job manual-shutdown --ignore-not-found
kubectl -n offhours-system create job --from=cronjob/offhours-shutdown manual-shutdown
kubectl -n offhours-system logs -f job/manual-shutdown
```

Startup:

```bash
kubectl -n offhours-system delete job manual-startup --ignore-not-found
kubectl -n offhours-system create job --from=cronjob/offhours-startup manual-startup
kubectl -n offhours-system logs -f job/manual-startup
```
