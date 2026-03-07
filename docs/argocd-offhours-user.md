# Usuario tecnico Argo CD para Offhours

Guia para criar um usuario tecnico no Argo CD para o K8s OffHours.

## Quando usar este guia

Use este guia quando `ARGO_ENABLED=true` e voce precisa de token/API para:

- ler Applications
- pausar/retomar sync (update)
- disparar sync

Resultado esperado: usuario `offhours` com token e permissao minima para operacao.

## Permissoes minimas necessarias

| Recurso | Acao |
| --- | --- |
| `applications` | `get` |
| `applications` | `update` |
| `applications` | `sync` |

Importante:

- Essa tabela cobre apenas RBAC do Argo CD (API de Applications).
- O tratamento de HPA e feito via API do Kubernetes, entao exige permissoes no `ServiceAccount` do Offhours (ClusterRole/Role), nao no usuario do Argo.

Permissoes Kubernetes adicionais para HPA (quando habilitado):

| Modo HPA | Permissoes Kubernetes necessarias |
| --- | --- |
| `HPA_MIN_ZERO_ENABLED=true` | `get,list,watch,patch,update` em `horizontalpodautoscalers.autoscaling` |
| `HPA_DELETE_RESTORE_ENABLED=true` | `get,list,watch,delete` em `horizontalpodautoscalers.autoscaling` + `get,list,create,patch,update,delete` em `configmaps` |
| `HPA_DELETE_ONLY_ENABLED=true` | `get,list,watch,delete` em `horizontalpodautoscalers.autoscaling` |

Referencia:

- Para a matriz completa de RBAC operacional, veja [operations.md](operations.md).

## Fluxo A - Argo no mesmo cluster do Offhours

### 1) Criar conta no Argo CD

```bash
kubectl -n argocd patch configmap argocd-cm --type merge -p '{
  "data": {
    "accounts.offhours": "apiKey, login"
  }
}'
```

### 2) Aplicar RBAC minimo

```bash
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
data:
  policy.csv: |
    p, role:offhours-global, applications, get, */*, allow
    p, role:offhours-global, applications, update, */*, allow
    p, role:offhours-global, applications, sync, */*, allow
    g, offhours, role:offhours-global
EOF
```

### 3) Reiniciar Argo server

```bash
kubectl -n argocd rollout restart deploy argocd-server
kubectl -n argocd rollout status deploy argocd-server
```

### 4) Gerar token

Recomendado: gerar token de dentro do cluster.

```bash
kubectl -n argocd run argocd-cli --rm -it --restart=Never \
  --image=quay.io/argoproj/argocd:v2.10.5 -- sh
```

Dentro do pod:

```bash
argocd login argocd-server.argocd.svc.cluster.local:80 \
  --username admin --password '<ADMIN_PASS>' --plaintext --grpc-web

argocd account generate-token --account offhours \
  --server argocd-server.argocd.svc.cluster.local:80 --plaintext --grpc-web
```

### 5) Configurar no Offhours

```bash
kubectl -n offhours-system patch secret offhours-secrets --type merge -p '{
  "stringData": {
    "ARGO_SERVER": "argocd-server.argocd.svc.cluster.local:80",
    "ARGO_TOKEN": "<TOKEN_OFFHOURS>"
  }
}'
```

## Fluxo B - Argo em cluster separado

Quando Argo nao esta no mesmo cluster, use endpoint roteavel para os pods do Offhours.

Exemplo:

- `ARGO_SERVER`: host/URL acessivel da rede do cluster Offhours
- `ARGO_SCHEME`: `https` (ou `http` se ambiente controlado)
- `ARGO_INSECURE`: `true` apenas se necessario

Observacao:

- `localhost` funciona no seu terminal, mas nao dentro do pod do CronJob.

## Validacao rapida

0. Descubra o nome real do CronJob de shutdown no seu ambiente:

```bash
kubectl -n offhours-system get cronjob
```

Exemplos comuns:

- manifests base: `offhours-shutdown`
- Helm release `offhours`: `offhours-k8s-offhours-shutdown`

1. Execute um shutdown manual:

```bash
kubectl -n offhours-system delete job manual-shutdown-argo --ignore-not-found
kubectl -n offhours-system create job --from=cronjob/<cronjob-shutdown> manual-shutdown-argo
kubectl -n offhours-system logs -f job/manual-shutdown-argo
```

2. Resultado esperado:

- app entra em sync manual (pause)
- deployment alvo escala para `0`

3. Execute startup manual e confirme retorno do sync e replicas.

## Erros comuns e troubleshooting

### `permission denied`

Causa: token sem RBAC suficiente.

Acao:

- validar `policy.csv` com `applications get/update/sync`
- regenerar token apos ajuste

### `no such host` / erro DNS

Causa: `ARGO_SERVER` inacessivel de dentro do pod.

Acao:

- para mesmo cluster, use `argocd-server.argocd.svc.cluster.local:80`
- para cluster separado, usar endpoint roteavel

### `connection refused` / `EOF`

Causa: endpoint, scheme (`http/https`) ou TLS incorreto.

Acao:

- revisar `ARGO_SCHEME`
- usar `ARGO_INSECURE=true` somente quando necessario

## Seguranca

- nao versionar tokens em Git
- usar External Secrets / Sealed Secrets / Vault
- rotacionar token periodicamente

## Referencias cruzadas

- visao geral: [README.MD](../README.MD)
- variaveis: [configuration.md](configuration.md)
- operacao e seguranca: [operations.md](operations.md)
