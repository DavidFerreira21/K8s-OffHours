# Operacao e seguranca

Para aprofundar em economia real de infraestrutura e requisitos de autoscaling de nos, veja [cost-optimization.md](cost-optimization.md).

## Permissoes necessarias (RBAC)

A ServiceAccount do CronJob precisa de:

- `get/list` em namespaces
- `get/list/patch/update` em deployments
- `get/patch/update` em `deployments/scale`
- `get/list` em replicasets (opcional)

Se usar Argo:

- permissao Argo RBAC para `applications get/update/sync` nas apps alvo

## Node autoscaling (obrigatorio para economia real)

Este toolkit escala apenas Deployments.

Para reduzir custo de infraestrutura, o cluster precisa de autoscaling de nodes:

- Cluster Autoscaler
- Karpenter
- VMSS Autoscaling (AKS)
- Node Auto Provisioning (GKE)

Sem autoscaling, os pods saem, mas os nodes continuam ativos.

## HPA

O script escala Deployment para `replicas=0`.

- modo Argo: estado desejado volta via Git no startup
- modo sem Argo: HPA permanece configurado e o Deployment e escalado manualmente

Observacao: com metricas ativas, HPA pode redefinir replicas.

Opcional:

- `HPA_MIN_ZERO_ENABLED=true`: tenta patchar `minReplicas=0` no `shutdown` para HPAs que apontam para Deployments alvo e restaura o valor original no `startup`.
- Se o patch falhar e o `minReplicas` original for maior que `0`, o job registra warning no log e continua.

## Interacao com GitOps

Se houver sincronizacao automatica (Argo/Flux/etc.), `replicas=0` pode ser revertido.

Recomendacoes:

- pausar sincronizacao no shutdown (modo Argo)
- configurar Sync Windows
- ou usar operacao manual de sincronizacao

## Seguranca de credenciais

Nao versionar secrets em texto claro.

Recomendado:

- External Secrets
- Sealed Secrets
- HashiCorp Vault

## Referencias cruzadas

- visao geral: [README.MD](../README.MD)
- configuracao: [configuration.md](configuration.md)
- deploy: [deploy.md](deploy.md)
- custo e autoscaling de nos: [cost-optimization.md](cost-optimization.md)
