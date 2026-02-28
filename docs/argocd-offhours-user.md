# Argo CD Offhours User

Exemplo de criacao de usuario tecnico para o K8s OffHours Toolkit.

## Objetivo

Criar um usuario `offhours` com token de API para:

- Ler applications
- Pausar sync (update)
- Disparar sync

## 1) Criar conta no Argo CD

```bash
kubectl -n argocd patch configmap argocd-cm --type merge -p '{
  "data": {
    "accounts.offhours": "apiKey, login"
  }
}'
```

## 2) RBAC global (todos os projetos)

```bash
kubectl -n argocd patch configmap argocd-rbac-cm --type merge -p '{
  "data": {
    "policy.csv": "p, role:offhours-global, applications, get, */*, allow\\np, role:offhours-global, applications, update, */*, allow\\np, role:offhours-global, applications, sync, */*, allow\\ng, offhours, role:offhours-global"
  }
}'
```

## 3) Aplicar alteracoes

```bash
kubectl -n argocd rollout restart deploy argocd-server
kubectl -n argocd rollout status deploy argocd-server
```

## 4) Gerar token do usuario

Opcao recomendada (dentro do cluster):

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

## 5) Configurar no Offhours

No secret `offhours-secrets`:

- `ARGO_SERVER`: endpoint do Argo CD
- `ARGO_TOKEN`: token do usuario `offhours`

Exemplo:

```bash
kubectl -n offhours-system patch secret offhours-secrets --type merge -p '{
  "stringData": {
    "ARGO_SERVER": "argocd-server.argocd.svc.cluster.local:80",
    "ARGO_TOKEN": "<TOKEN_OFFHOURS>"
  }
}'
```

## Variante recomendada para producao (escopo por projeto)

Em vez de `*/*`, restringir por projeto:

```text
p, role:offhours, applications, get, projeto-a/*, allow
p, role:offhours, applications, update, projeto-a/*, allow
p, role:offhours, applications, sync, projeto-a/*, allow
g, offhours, role:offhours
```

## Seguranca

- Nao versionar tokens reais no Git.
- Usar External Secrets / Sealed Secrets / Vault.
- Rotacionar tokens periodicamente.
