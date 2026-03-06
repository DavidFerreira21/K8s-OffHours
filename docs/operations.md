# Operacao e seguranca

Para aprofundar em economia real de infraestrutura e requisitos de autoscaling de nos, veja [cost-optimization.md](cost-optimization.md).

## Permissoes necessarias (RBAC)

A ServiceAccount do CronJob precisa de:

- `get/list` em namespaces
- `get/list/patch/update` em deployments
- `get/patch/update` em `deployments/scale`
- `get/list` em replicasets (opcional)
- `get/list/watch/patch/update` em `horizontalpodautoscalers.autoscaling` (quando `HPA_MIN_ZERO_ENABLED=true`)
- `get/list/create/patch/update/delete` em `configmaps` (quando `HPA_DELETE_RESTORE_ENABLED=true`)

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
- `HPA_DELETE_RESTORE_ENABLED=true`: salva o HPA em ConfigMap tecnico (`offhours-system`), deleta no `shutdown` e recria no `startup`.
- `HPA_DELETE_ONLY_ENABLED=true`: deleta o HPA no `shutdown` sem salvar estado e nao restaura no `startup`.
- Se `HPA_DELETE_ONLY_ENABLED=true` e `HPA_DELETE_RESTORE_ENABLED=true`, prevalece `HPA_DELETE_RESTORE_ENABLED`.
- Quando `HPA_DELETE_ONLY_ENABLED=true` (sozinho), esse modo tem prioridade sobre `HPA_MIN_ZERO_ENABLED`.
- Quando `HPA_DELETE_RESTORE_ENABLED=true`, esse modo tem prioridade sobre `HPA_MIN_ZERO_ENABLED`.
- Recomendacao forte para `HPA_DELETE_ONLY_ENABLED=true`: usar com Argo/Flux ativo para que o HPA seja recriado por reconciliacao GitOps.

Observacoes praticas:

- Em alguns clusters, `minReplicas=0` no HPA pode ser rejeitado quando as metricas sao apenas de `Resource` (CPU/memoria).
- Nesse caso, `HPA_MIN_ZERO_ENABLED=true` vai gerar warning e seguir com o `shutdown` do Deployment (comportamento best-effort).
- Se o objetivo e garantir `replicas=0` mesmo com essa limitacao, prefira `HPA_DELETE_RESTORE_ENABLED=true`.
- Se usar `HPA_DELETE_ONLY_ENABLED=true` sem Argo/Flux, o HPA pode permanecer ausente ate restauracao manual.

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
