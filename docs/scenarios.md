# Cenarios de exemplo

## Se estiver usando Helm

No Helm, nomes de recursos variam com o nome da release.

Antes dos testes, descubra os nomes reais:

```bash
kubectl -n offhours-system get cronjob
kubectl -n offhours-system get configmap
```

Exemplos comuns com release `offhours`:

- CronJobs: `offhours-k8s-offhours-shutdown` e `offhours-k8s-offhours-startup`
- ConfigMap: `offhours-k8s-offhours-config`

Recomendacao:

- em instalacao via Helm, prefira ajustar configuracao com `helm upgrade --set ...`
- evite `kubectl patch` no ConfigMap gerenciado pelo Helm, para nao perder mudancas no proximo `helm upgrade`

Aplicar cenarios:

```bash
kubectl apply -f k8s/examples/scenarios/scenario-1-namespace-scope.yaml
kubectl apply -f k8s/examples/scenarios/scenario-2-deployment-scope.yaml
kubectl apply -f k8s/examples/scenarios/scenario-3-argopp-override.yaml
kubectl apply -f k8s/examples/scenarios/scenario-4-mixed-protected-app.yaml
```

Aplicar cenarios Argo (somente cenario 3 e 4):

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

## Cenario 1 - Escopo de namespace

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
helm upgrade offhours ./helm/k8s-offhours \
  -n offhours-system --reuse-values \
  --set config.scheduleName="dev-weekday" \
  --set config.scheduleScope="namespace" \
  --set argocd.enabled=false \
  --set config.dryRun=false \
  --set config.protectedAppStrictMode=true \
  --set config.defaultStartupReplicas=1
```

HPA de exemplo vinculado ao Cenario 1:

```bash
kubectl apply -f k8s/examples/scenarios/hpa-example.yaml
```

Este HPA aponta para `Deployment/api` no namespace `app-dev-ns-scope`.

## Cenario 2 - Escopo de deployment

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
helm upgrade offhours ./helm/k8s-offhours \
  -n offhours-system --reuse-values \
  --set config.scheduleName="default" \
  --set config.scheduleScope="deployment" \
  --set argocd.enabled=false \
  --set config.dryRun=false \
  --set config.protectedAppStrictMode=true \
  --set config.defaultStartupReplicas=1
```

HPA de exemplo realista vinculado ao Cenario 2:

```bash
kubectl apply -f k8s/examples/scenarios/hpa-scenario-2-checkout-api.yaml
```

Este HPA aponta para `Deployment/checkout-api` no namespace `app-dev-deploy-scope` e usa:

- metricas de CPU e memoria
- `behavior` para suavizar scale-up/scale-down

## Cenario 3 - Override de app Argo (`argopp`)

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

Exemplo rapido com Helm:

```bash
helm upgrade offhours ./helm/k8s-offhours \
  -n offhours-system --reuse-values \
  --set config.scheduleName="dev-weekday" \
  --set config.scheduleScope="namespace" \
  --set argocd.enabled=true \
  --set config.dryRun=false \
  --set config.protectedAppStrictMode=true \
  --set config.argoDiscoveryUseAutomatic=false \
  --set config.argoDiscoveryUseManual=true
```

## Cenario 4 - App mista (protegido + nao protegido)

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

Antes de criar Jobs manuais, descubra os nomes reais dos CronJobs no seu ambiente:

```bash
kubectl -n offhours-system get cronjob
```

Nomes comuns:

- manifests base (`k8s/base`): `offhours-shutdown` e `offhours-startup`
- Helm release `offhours`: `offhours-k8s-offhours-shutdown` e `offhours-k8s-offhours-startup`

Shutdown:

```bash
kubectl -n offhours-system delete job manual-shutdown --ignore-not-found
kubectl -n offhours-system create job --from=cronjob/<cronjob-shutdown> manual-shutdown
kubectl -n offhours-system logs -f job/manual-shutdown
```

Startup:

```bash
kubectl -n offhours-system delete job manual-startup --ignore-not-found
kubectl -n offhours-system create job --from=cronjob/<cronjob-startup> manual-startup
kubectl -n offhours-system logs -f job/manual-startup
```
