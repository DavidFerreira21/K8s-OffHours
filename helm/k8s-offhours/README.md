# k8s-offhours Helm Chart

Instala o K8s OffHours via Helm.

## Comportamento padrao

- `argocd.enabled=false` (modo Kubernetes-only)
- Nao exige Secret do Argo CD

## Quando habilitar Argo

Se `argocd.enabled=true`, voce deve informar um Secret existente em `argocd.existingSecret`.

O Secret deve conter:

- `ARGO_SERVER`
- `ARGO_TOKEN`

## Exemplo de instalacao (sem Argo)

```bash
helm upgrade --install offhours ./helm/k8s-offhours \
  -n offhours-system --create-namespace
```

## Exemplo de instalacao (com Argo)

```bash
kubectl -n offhours-system create secret generic offhours-argocd \
  --from-literal=ARGO_SERVER='argocd-server.argocd.svc.cluster.local:80' \
  --from-literal=ARGO_TOKEN='<token>'

helm upgrade --install offhours ./helm/k8s-offhours \
  -n offhours-system --create-namespace \
  --set argocd.enabled=true \
  --set argocd.existingSecret=offhours-argocd
```

## Multi-window com Helm

Cada release cria 1 par de CronJobs (`shutdown`/`startup`). Para multi-window, instale uma release por janela.

```bash
# janela dev-weekday
helm upgrade --install offhours-dev ./helm/k8s-offhours \
  -n offhours-system --create-namespace \
  --set schedule.shutdown="0 20 * * 1-5" \
  --set schedule.startup="0 8 * * 1-5" \
  --set schedule.timeZone="America/Sao_Paulo" \
  --set config.scheduleName="dev-weekday" \
  --set config.scheduleScope="namespace" \
  --set argocd.enabled=false

# janela qa-weekday
helm upgrade --install offhours-qa ./helm/k8s-offhours \
  -n offhours-system \
  --set schedule.shutdown="0 22 * * 1-5" \
  --set schedule.startup="0 9 * * 1-5" \
  --set schedule.timeZone="America/Sao_Paulo" \
  --set config.scheduleName="qa-weekday" \
  --set config.scheduleScope="namespace" \
  --set argocd.enabled=false
```

Ao final, aplique a label no alvo desejado:

```bash
# quando SCHEDULE_SCOPE=namespace
kubectl label ns <namespace> offhours.platform.io/schedule=<schedule-name> --overwrite

# quando SCHEDULE_SCOPE=deployment
kubectl -n <namespace> label deploy <deployment> offhours.platform.io/schedule=<schedule-name> --overwrite
```

## Modos de HPA (opcional)

Ativar modo best-effort (`minReplicas=0`):

```bash
helm upgrade --install offhours ./helm/k8s-offhours \
  -n offhours-system --create-namespace \
  --set config.hpaMinZeroEnabled=true \
  --set config.hpaDeleteRestoreEnabled=false
```

Ativar modo garantido (`delete-restore`):

```bash
helm upgrade --install offhours ./helm/k8s-offhours \
  -n offhours-system --create-namespace \
  --set config.hpaMinZeroEnabled=false \
  --set config.hpaDeleteRestoreEnabled=true
```

Observacao: `config.hpaDeleteRestoreEnabled=true` tem prioridade sobre `config.hpaMinZeroEnabled`.

Ativar modo `delete-only` (sem restaurar no startup):

```bash
helm upgrade --install offhours ./helm/k8s-offhours \
  -n offhours-system --create-namespace \
  --set config.hpaMinZeroEnabled=false \
  --set config.hpaDeleteRestoreEnabled=false \
  --set config.hpaDeleteOnlyEnabled=true
```

Observacao: se `config.hpaDeleteOnlyEnabled=true` e `config.hpaDeleteRestoreEnabled=true`, prevalece `config.hpaDeleteRestoreEnabled`.
