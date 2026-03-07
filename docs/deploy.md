# Deploy

## Requisitos

- Cluster Kubernetes com `kubectl` configurado
- Ferramentas no container: `python3`, `kubectl`, `curl`, `ca-certificates`

Observacao: para validar economia real apos o deploy, veja [cost-optimization.md](cost-optimization.md).

## Opcao 1: Janela unica (`k8s/base`)

1. Ajuste `k8s/base/config.yaml`
2. Se usar Argo, preencha `ARGO_SERVER` e `ARGO_TOKEN` no Secret
3. Aplique:

```bash
kubectl apply -k k8s/base
```

Opcional (HPA de exemplo vinculado ao Cenario 1):

```bash
kubectl apply -f k8s/examples/scenarios/hpa-example.yaml
```

Se quiser reutilizar em outro workload, ajuste `namespace`, `scaleTargetRef.name`, `minReplicas` e `maxReplicas`.

Opcional (modos de HPA no OffHours em manifests base):

```bash
# modo best-effort: tenta minReplicas=0
kubectl -n offhours-system patch configmap offhours-config --type merge -p '{
  "data":{
    "HPA_MIN_ZERO_ENABLED":"true",
    "HPA_DELETE_RESTORE_ENABLED":"false"
  }
}'

# modo garantido: salva/deleta/restaura HPA (prioridade sobre min-zero)
kubectl -n offhours-system patch configmap offhours-config --type merge -p '{
  "data":{
    "HPA_MIN_ZERO_ENABLED":"false",
    "HPA_DELETE_RESTORE_ENABLED":"true",
    "HPA_DELETE_ONLY_ENABLED":"false"
  }
}'

# modo delete-only: deleta HPA sem restaurar (usar com GitOps)
kubectl -n offhours-system patch configmap offhours-config --type merge -p '{
  "data":{
    "HPA_MIN_ZERO_ENABLED":"false",
    "HPA_DELETE_RESTORE_ENABLED":"false",
    "HPA_DELETE_ONLY_ENABLED":"true"
  }
}'
```

Regra de precedencia:

- se `HPA_DELETE_ONLY_ENABLED=true` e `HPA_DELETE_RESTORE_ENABLED=true`, prevalece `HPA_DELETE_RESTORE_ENABLED`.
- aviso importante: com `HPA_DELETE_ONLY_ENABLED=true`, sem GitOps/recriacao manual, o HPA ficara ausente apos o `shutdown`.

## Opcao 2: Multiplas janelas (`k8s/base/multi-window`)

```bash
kubectl apply -k k8s/base/multi-window
```

## Opcao 3: Multiplas janelas com Helm (multiplas releases)

No Helm, cada release cria 1 par de CronJobs (`shutdown`/`startup`). Para multi-window, instale uma release por janela.

Exemplo:

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

Validacao:

```bash
kubectl -n offhours-system get cronjob
kubectl -n offhours-system get configmap
```

Observacoes importantes para Helm:

- nomes de CronJob/ConfigMap variam conforme o nome da release.
- exemplo com release `offhours`: CronJobs `offhours-k8s-offhours-shutdown` e `offhours-k8s-offhours-startup`, ConfigMap `offhours-k8s-offhours-config`.
- prefira alterar configuracoes com `helm upgrade --set ...`; evite `kubectl patch` em ConfigMap gerenciado pelo Helm.

Modos de HPA via Helm:

```bash
# modo best-effort: tenta minReplicas=0
helm upgrade offhours ./helm/k8s-offhours \
  -n offhours-system --reuse-values \
  --set config.hpaMinZeroEnabled=true \
  --set config.hpaDeleteRestoreEnabled=false \
  --set config.hpaDeleteOnlyEnabled=false

# modo garantido: salva/deleta/restaura HPA
helm upgrade offhours ./helm/k8s-offhours \
  -n offhours-system --reuse-values \
  --set config.hpaMinZeroEnabled=false \
  --set config.hpaDeleteRestoreEnabled=true \
  --set config.hpaDeleteOnlyEnabled=false

# modo delete-only: deleta HPA sem restaurar (usar com GitOps)
helm upgrade offhours ./helm/k8s-offhours \
  -n offhours-system --reuse-values \
  --set config.hpaMinZeroEnabled=false \
  --set config.hpaDeleteRestoreEnabled=false \
  --set config.hpaDeleteOnlyEnabled=true
```

Ao final do procedimento, aplique a label de schedule no alvo desejado:

```bash
# quando SCHEDULE_SCOPE=namespace
kubectl label ns <namespace> offhours.platform.io/schedule=<schedule-name> --overwrite

# quando SCHEDULE_SCOPE=deployment
kubectl -n <namespace> label deploy <deployment> offhours.platform.io/schedule=<schedule-name> --overwrite
```

## Build de imagem

### Local (kind)

```bash
make build-local
make kind-load IMAGE=k8s-offhours:local KIND_CLUSTER=kind
kubectl apply -k k8s/base
```

Observacao: para esse fluxo, atualize os `image:` dos YAMLs para `k8s-offhours:local`.

### Com registry

```bash
make build IMAGE=<seu-registry>/k8s-offhours:<tag>
docker push <seu-registry>/k8s-offhours:<tag>
kubectl apply -k k8s/base
```

Observacao: apos publicar no registry, atualize os `image:` dos YAMLs para `<seu-registry>/k8s-offhours:<tag>`.

## Execucao local do script

```bash
make run-shutdown
make run-startup
```
