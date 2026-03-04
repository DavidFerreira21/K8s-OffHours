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
