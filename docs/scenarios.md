# Cenarios de exemplo

Aplicar cenarios:

```bash
kubectl apply -f k8s/examples/scenarios/scenario-1-namespace-scope.yaml
kubectl apply -f k8s/examples/scenarios/scenario-2-deployment-scope.yaml
kubectl apply -f k8s/examples/scenarios/scenario-3-argopp-override.yaml
kubectl apply -f k8s/examples/scenarios/scenario-4-mixed-protected-app.yaml
```

Aplicar cenarios Argo (somente scenario 3 e 4):

```bash
kubectl apply -f k8s/examples/argo/argocd-application-scenario-3.yaml
kubectl apply -f k8s/examples/argo/argocd-application-scenario-4.yaml
```

Regra base para todos os cenarios:

- `SCHEDULE_NAME` deve ser exatamente igual ao valor da label `offhours.platform.io/schedule` usada no alvo.

Observacao para cenarios com HPA:

- para testar `delete-restore`, use `HPA_DELETE_RESTORE_ENABLED=true`
- para testar `delete-only`, use `HPA_DELETE_ONLY_ENABLED=true` (preferencialmente com Argo/Flux)
- se `HPA_DELETE_ONLY_ENABLED=true` e `HPA_DELETE_RESTORE_ENABLED=true`, prevalece `HPA_DELETE_RESTORE_ENABLED`

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

HPA de exemplo vinculado ao Scenario 1:

```bash
kubectl apply -f k8s/examples/scenarios/hpa-example.yaml
```

Este HPA aponta para `Deployment/api` no namespace `app-dev-ns-scope`.

## Scenario 2 - Deployment scope

Arquivo: `k8s/examples/scenarios/scenario-2-deployment-scope.yaml`

Valida:

- selecao por deployment (`SCHEDULE_SCOPE=deployment`)
- protecao por annotation no deployment

Variaveis recomendadas:

```yaml
data:
  SCHEDULE_NAME: "default"
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
    "SCHEDULE_NAME":"default",
    "SCHEDULE_SCOPE":"deployment",
    "ARGO_ENABLED":"false",
    "DRY_RUN":"false",
    "PROTECTED_APP_STRICT_MODE":"true",
    "DEFAULT_STARTUP_REPLICAS":"1"
  }
}'
```

HPA de exemplo realista vinculado ao Scenario 2:

```bash
kubectl apply -f k8s/examples/scenarios/hpa-scenario-2-checkout-api.yaml
```

Este HPA aponta para `Deployment/checkout-api` no namespace `app-dev-deploy-scope` e usa:

- metricas de CPU e memoria
- `behavior` para suavizar scale-up/scale-down

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
  ARGO_DISCOVERY_USE_AUTOMATIC: "false"
  ARGO_DISCOVERY_USE_MANUAL: "true"
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

- no `shutdown`: se a app tiver qualquer deployment protegido, a app nao e pausada e nenhum deployment da app e escalado
- no `startup`: essa app tambem nao recebe `resume/sync`

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
