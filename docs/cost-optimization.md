# Otimização de Custos e Integração com Autoscaling de Nós

## Visão Geral

O K8s-OffHours escala workloads Kubernetes (Deployments) para zero réplicas fora do horário comercial.

Entretanto, escalar workloads sozinhos **não garante redução real de custo de infraestrutura**.

Para que haja economia efetiva, o cluster deve possuir um **autoscaler de nós corretamente configurado**, capaz de remover nós ociosos após o scale-down dos workloads.

Este documento explica como o autoscaling de nós se integra ao K8s-OffHours e quais requisitos são necessários para garantir otimização de custos.

---

## Como a Redução de Custos Realmente Acontece

O fluxo completo de economia ocorre da seguinte forma:

1. O CronJob escala os Deployments para 0 réplicas
2. Os Pods são finalizados
3. Os nós ficam ociosos ou subutilizados
4. O autoscaler detecta capacidade não utilizada
5. Os nós são drenados e removidos
6. O provedor de cloud deixa de cobrar por esses recursos computacionais

Se o passo 4 não ocorrer, os nós continuarão ativos e não haverá redução real de custo.

---

## O Que Este Projeto Faz

O K8s-OffHours:

- Escala Deployments para 0 réplicas
- Restaura a contagem original de réplicas
- Permite escopo por namespace ou deployment
- Suporta integração com Argo CD
- Permite proteção de workloads críticos via annotation

---

## O Que Este Projeto NÃO Faz

O K8s-OffHours **não**:

- Gerencia node groups
- Configura ou altera autoscalers
- Drena nós
- Garante scale-down de nós
- Gerencia interrupções de instâncias spot
- Interage diretamente com APIs do provedor de cloud

O gerenciamento do ciclo de vida da infraestrutura está intencionalmente fora do escopo da solução.

---

## Autoscalers Recomendados

Para obter economia real, recomenda-se utilizar um dos seguintes mecanismos:

---

### Opção 1 — Karpenter (Recomendado para EKS)

Verifique se:

- `consolidation.enabled: true`
- `ttlSecondsAfterEmpty` configurado (ex: 30–60 segundos)
- Limits adequadamente definidos
- Não existem restrições rígidas de instância
- Não há PDBs bloqueando eviction
- Workloads permitem consolidação de nós

Boas práticas:

- Evitar requisitos excessivamente restritivos de tipo de instância
- Garantir que DaemonSets não impeçam remoção de nós
- Validar afinidades e tolerâncias

---

### Opção 2 — Cluster Autoscaler

Verifique se:

- `--scale-down-enabled=true`
- `--scale-down-unneeded-time` configurado adequadamente (ex: 5–10m em ambientes não produtivos)
- `--scale-down-delay-after-add` ajustado conforme padrão de uso
- Nós não estejam marcados como `scale-down-disabled`
- Não existam PodDisruptionBudgets bloqueando remoção

---

## Motivos Comuns Para Nós Não Escalarem Para Baixo

Mesmo com réplicas em zero, nós podem continuar ativos devido a:

- DaemonSets rodando em todos os nós
- Pods de sistema consumindo recursos
- PodDisruptionBudgets bloqueando eviction
- PersistentVolumes locais
- Configuração de mínimo fixo no node group
- Thresholds mal configurados no autoscaler
- Afinidade estática de nós

Sempre valide esses pontos durante testes.

---

## Recomendação Para Uso em Produção

Antes de depender do K8s-OffHours para otimização de custos:

- Teste o autoscaler em ambiente de staging
- Simule janelas completas de desligamento
- Confirme que os nós são realmente removidos
- Monitore a contagem de nós ao longo do tempo
- Valide o impacto real na fatura de cloud

---

## Aviso Importante

Se o autoscaling de nós não estiver corretamente configurado:

> Os workloads serão escalados para zero, mas os nós poderão permanecer ativos, resultando em nenhuma redução real de custo.

O K8s-OffHours assume que existe uma estratégia de autoscaling corretamente implementada.

---

## Princípio Arquitetural

O K8s-OffHours segue o princípio de responsabilidade única:

- Controla o estado dos workloads
- Não controla o ciclo de vida da infraestrutura

Isso garante portabilidade, simplicidade e compatibilidade com diferentes provedores e distribuições Kubernetes.

---

## Recomendação Final

Para ambientes não produtivos, a combinação mais eficiente é:

- K8s-OffHours
- Karpenter ou Cluster Autoscaler
- Thresholds de scale-down agressivos
- PDBs flexíveis
- Configuração de instâncias não restritiva

Essa arquitetura fornece uma solução automatizada, segura e mensurável para redução de custos.