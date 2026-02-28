# Deploy

## Requisitos

- Cluster Kubernetes com `kubectl` configurado
- Ferramentas no container: `python3`, `kubectl`, `curl`, `ca-certificates`

Observacao: para validar economia real apos o deploy, veja [cost-optimization.md](cost-optimization.md).

## Opcao 1: Janela unica (`k8s/base`)

1. Defina a imagem:

```bash
make set-image IMAGE=<sua-imagem:tag>
```

Valor padrao atual dos manifests: `docker.io/davidferreira21/k8s-offhours:latest`.

2. Ajuste `k8s/base/config.yaml`
3. Se usar Argo, preencha `ARGO_SERVER` e `ARGO_TOKEN` no Secret
4. Aplique:

```bash
kubectl apply -k k8s/base
```

## Opcao 2: Multiplas janelas (`k8s/base/multi-window`)

```bash
kubectl apply -k k8s/base/multi-window
```

## Build de imagem

### Local (kind)

```bash
make build-local
make set-image IMAGE=k8s-offhours:local
make kind-load IMAGE=k8s-offhours:local KIND_CLUSTER=kind
kubectl apply -k k8s/base
```

### Com registry

```bash
make build IMAGE=<seu-registry>/k8s-offhours:<tag>
docker push <seu-registry>/k8s-offhours:<tag>
make set-image IMAGE=<seu-registry>/k8s-offhours:<tag>
kubectl apply -k k8s/base
```

## Execucao local do script

```bash
make run-shutdown
make run-startup
```
