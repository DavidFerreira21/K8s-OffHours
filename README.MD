# K8s OffHours

K8s OffHours is a safe, GitOps-friendly toolkit for automated off-hours scaling of Kubernetes workloads.
Toolkit seguro e GitOps-friendly para escalonamento automatico de workloads Kubernetes fora do horario comercial.

## O que este projeto entrega

- Shutdown e startup automatizados via `CronJob`
- Operacao em dois modos:
- `ARGO_ENABLED=true` (integracao Argo CD)
- `ARGO_ENABLED=false` (somente Kubernetes)
- Selecao de namespaces por label de schedule
- Exclusao de deployments criticos por annotation
- Estrutura pronta para deploy em cluster

## Design Principles

- Declarative first: selecao baseada em labels.
- Idempotent operations: execucoes repetidas nao causam inconsistencias.
- GitOps-friendly: integracao opcional com Argo CD.
- Cloud-agnostic: compativel com qualquer Kubernetes com autoscaling.
- Minimal surface area: sem CRD, sem Operator.

## Estrutura do repositorio

```text
.
├── Dockerfile
├── Makefile
├── .env.example
├── scripts/
│   └── offhours.py
└── k8s/
    ├── base/
    │   ├── kustomization.yaml
    │   ├── namespace.yaml
    │   ├── rbac.yaml
    │   ├── config.yaml
    │   ├── cronjob-shutdown.yaml
    │   ├── cronjob-startup.yaml
    │   └── multi-window/
    │       ├── kustomization.yaml
    │       ├── config-dev-weekday.yaml
    │       ├── config-qa-weekday.yaml
    │       ├── cronjob-shutdown-dev-weekday.yaml
    │       ├── cronjob-startup-dev-weekday.yaml
    │       ├── cronjob-shutdown-qa-weekday.yaml
    │       └── cronjob-startup-qa-weekday.yaml
    └── examples/
        └── scenarios/
            ├── scenario-1-namespace-scope.yaml
            ├── scenario-2-deployment-scope.yaml
            ├── scenario-3-argopp-override.yaml
            └── scenario-4-mixed-protected-app.yaml
```

## Como funciona

### 1) Escopo do schedule (`SCHEDULE_SCOPE`)

O toolkit suporta dois escopos:

- `namespace` (padrao): seleciona namespaces por label de schedule.
- `deployment`: seleciona deployments por label de schedule (sem depender de label no namespace).

Label usada nos dois modos:

- `offhours.platform.io/schedule: "<nome-do-schedule>"`

### 2) Namespace targeting (`SCHEDULE_SCOPE=namespace`)

Somente namespaces com esta label entram no schedule:

```yaml
metadata:
  labels:
    offhours.platform.io/schedule: "dev"
```

### 3) Deployment targeting (`SCHEDULE_SCOPE=deployment`)

Somente deployments com esta label entram no schedule:

```yaml
metadata:
  labels:
    offhours.platform.io/schedule: "dev"
```

### 4) Deployment protegido

Deployments com esta annotation nunca sao escalados:

```yaml
metadata:
  annotations:
    offhours.platform.io/protected: "true"
```

### 5) Modo com Argo CD (`ARGO_ENABLED=true`)

Implementacao Python usa Argo CD API mode (endpoint + token), sem dependencias de `argocd` CLI.

- Identifica apps com fallback em 4 opcoes (ordem padrao):
- Label `argocd.argoproj.io/instance`
- Annotation `argocd.argoproj.io/tracking-id` (extrai nome da app)
- Override explicito por namespace: `offhours.platform.io/argopp` (label ou annotation, aceita lista separada por virgula)
- Consulta Argo API (`/api/v1/applications`) filtrando por `spec.destination.namespace`
- No `shutdown`: pausa sync do Argo e escala deployments para `0`
- No `startup`: reativa sync e dispara refresh da Application
- Se nao encontrar app em um namespace: registra erro em log e continua processando os demais namespaces

Exemplo de override no namespace:

```yaml
metadata:
  labels:
    offhours.platform.io/argopp: "smb-app, billing-app"
```

#### Operacao manual no Argo (opcional)

Tambem e possivel usar este toolkit com controle manual no Argo CD, quando voce preferir definir a politica fora do script:

- Configurar `Sync Policy` manualmente por Application
- Definir `Sync Windows` no Argo CD para bloquear/liberar sincronizacao por horario

Nesse modelo:

- O script continua escalando deployments
- A governanca de sincronizacao fica no Argo CD (manual/politica central)

Vantagens desse modelo:

- Nao exige `ARGO_SERVER` e `ARGO_TOKEN` no CronJob
- Reduz acoplamento e exposicao de credenciais da plataforma GitOps
- Permite uso com outras ferramentas de GitOps (ex.: Flux), pois o offhours atua apenas via Kubernetes

Atencao:

- Se a ferramenta GitOps fizer reconciliacao automatica, ela pode reverter `replicas=0`.
- Nesse caso, configure janela/politica de sincronizacao na propria ferramenta GitOps.

#### Protecao em apps mistas (protegido + nao protegido)

Use `PROTECTED_APP_STRICT_MODE`:

- `true` (recomendado): se uma app tiver qualquer deployment protegido, o script nao pausa sync dessa app e nao escala nenhum deployment dela.
- `false`: comportamento agressivo, pausa sync da app e escala apenas os deployments nao protegidos.

### 6) Modo sem Argo (`ARGO_ENABLED=false`)

- No `shutdown`: salva replicas originais em annotation e escala para `0`
- No `startup`: restaura replicas da annotation
- Fallback: usa `DEFAULT_STARTUP_REPLICAS` (padrao `1`)

## Variaveis de ambiente

| Variavel | Obrigatoria | Descricao |
| --- | --- | --- |
| `SCHEDULE_NAME` | Sim | Nome do schedule (valor da label no namespace) |
| `SCHEDULE_SCOPE` | Nao | `namespace` (padrao) ou `deployment` |
| `ACTION` | Sim | `shutdown` ou `startup` |
| `ARGO_ENABLED` | Sim | `true` ou `false` |
| `ARGO_SERVER` | Se `ARGO_ENABLED=true` | Endpoint do Argo CD (host:porta) |
| `ARGO_TOKEN` | Se `ARGO_ENABLED=true` | Token de API do Argo CD |
| `ARGO_SCHEME` | Nao | `https` (padrao) ou `http` |
| `ARGO_INSECURE` | Nao | `true` para ignorar validacao TLS em `https` |
| `ARGO_DISCOVERY_USE_INSTANCE_LABEL` | Nao | `true/false` para usar `argocd.argoproj.io/instance` (padrao: `true`) |
| `ARGO_DISCOVERY_USE_TRACKING_ID` | Nao | `true/false` para usar `argocd.argoproj.io/tracking-id` (padrao: `true`) |
| `ARGO_DISCOVERY_USE_ARGOPP` | Nao | `true/false` para usar override `offhours.platform.io/argopp` (padrao: `false`) |
| `ARGO_DISCOVERY_USE_DEST_NAMESPACE_FALLBACK` | Nao | `true/false` para fallback por destination namespace (padrao: `false`) |
| `ARGO_API_RETRIES` | Nao | Quantidade de retries para erros transientes da API Argo (padrao agressivo: `2`) |
| `ARGO_API_RETRY_BASE_SECONDS` | Nao | Backoff base em segundos (padrao agressivo: `0.2`) |
| `ARGO_API_RETRY_MAX_SECONDS` | Nao | Teto do backoff em segundos (padrao agressivo: `1.0`) |
| `VERBOSE` | Nao | Logs detalhados (`true/false`) |
| `DRY_RUN` | Nao | Nao executa mudancas (`true/false`) |
| `DEFAULT_STARTUP_REPLICAS` | Nao | Replica padrao no startup sem annotation |
| `PROTECTED_APP_STRICT_MODE` | Nao | `true` para modo seguro em apps mistas, `false` para modo agressivo |

## Arquitetura do script Python

Arquivo principal: `scripts/offhours.py`

Responsabilidades por bloco:

- Validacao e parsing de ambiente:
- `validate_env`, `env_str`, `env_bool`

- Integracao Kubernetes:
- `kubectl_get`, `get_target_namespaces`, `get_target_deployment_pairs`
- `get_deployment`, `scale_deployment`, `save_original_replicas`

- Integracao Argo API mode:
- `argo_request`, `get_all_applications`, `get_app`
- `argo_pause_app`, `argo_resume_and_sync_app`
- Retry/backoff para `429` e `5xx` (erros transientes)

- Descoberta de Application:
- `get_argocd_apps_from_namespace`
- `get_argocd_app_for_deployment`
- fallback por `instance/tracking-id` -> `argopp` -> destination namespace

Metodos de descoberta (controlados por variavel):

- `ARGO_DISCOVERY_USE_INSTANCE_LABEL`: usa label `argocd.argoproj.io/instance`
- `ARGO_DISCOVERY_USE_TRACKING_ID`: usa annotation `argocd.argoproj.io/tracking-id`
- `ARGO_DISCOVERY_USE_ARGOPP`: usa override por namespace `offhours.platform.io/argopp`
- `ARGO_DISCOVERY_USE_DEST_NAMESPACE_FALLBACK`: usa fallback pela `spec.destination.namespace` na API do Argo

Ordem padrao atual:

1. `instance` label
2. `tracking-id`
3. `argopp`
4. destination namespace fallback

No padrao de fabrica, os metodos 1 e 2 ficam habilitados, e os metodos 3 e 4 desabilitados.

- Orquestracao por escopo e acao:
- `handle_shutdown_namespace`, `handle_startup_namespace`
- `handle_shutdown_deployment_scope`, `handle_startup_deployment_scope`
- `main`

Fluxo resumido:

- `ACTION=shutdown`
- Descobre alvo por `SCHEDULE_SCOPE`
- (Se Argo ativo) pausa sync das apps elegiveis
- Salva replicas originais
- Escala deployments elegiveis para `0`

- `ACTION=startup`
- Descobre alvo por `SCHEDULE_SCOPE`
- (Se Argo ativo) reativa sync e dispara sync das apps
- (Sem Argo) restaura replicas por annotation/fallback

## Requisitos

- Cluster Kubernetes com `kubectl` configurado
- Ferramentas no container: `python3`, `kubectl`, `curl` e `ca-certificates`

## Idempotencia

O script foi projetado para ser idempotente:

- Se um deployment ja estiver com `replicas=0`, nao falha.
- Se a annotation `offhours.platform.io/original-replicas` ja existir, nao sobrescreve.
- No modo Argo, se a app ja estiver pausada, nao gera erro fatal.

## Permissoes necessarias (RBAC)

A ServiceAccount utilizada pelo CronJob precisa de:

- `get` e `list` em namespaces
- `get`, `list`, `patch` e `update` em deployments
- `get`, `patch` e `update` em `deployments/scale`
- `get` e `list` em replicasets (opcional)

Se usar Argo:

- Permissao no Argo RBAC para `applications get/update/sync` nas apps alvo

## Node autoscaling

Importante: este toolkit apenas escala Deployments.

Para que haja reducao real de custo de infraestrutura, o cluster precisa possuir um mecanismo de node autoscaling, como:

- Cluster Autoscaler
- Karpenter
- VMSS Autoscaling (AKS)
- Node Auto Provisioning (GKE)

Sem autoscaling, apenas os pods serao removidos, mas os nodes permanecerao ativos.

## Comportamento com HPA

O script escala diretamente o Deployment para `replicas=0`.

Se houver HPA associado:

- No modo Argo: o HPA sera restaurado via Git no startup.
- No modo sem Argo: o HPA permanece configurado, mas o Deployment e escalado manualmente.

Observacao: em ambientes com HPA, o HPA pode redefinir replicas se houver metricas ativas.
Recomenda-se validar comportamento em ambientes com HPA ativo.

## Interacao com ferramentas GitOps

Se outra ferramenta GitOps (Argo, Flux, etc.) estiver configurada com sincronizacao automatica, ela pode reverter `replicas=0`.

Neste caso, recomenda-se:

- Pausar sincronizacao no shutdown (modo Argo)
- Configurar Sync Windows
- Ou utilizar operacao manual de sincronizacao

## Seguranca de credenciais

Se for necessario usar credenciais externas, nao versionar secrets em texto claro.
Recomenda-se utilizar:

- External Secrets
- Sealed Secrets
- HashiCorp Vault

Guia de usuario tecnico Argo para este projeto:

- `docs/argocd-offhours-user.md`

## Deploy no cluster

### Opcao 1: Janela unica (base)

1. Ajuste imagem dos CronJobs em:
- `k8s/base/cronjob-shutdown.yaml`
- `k8s/base/cronjob-startup.yaml`

2. Timezone padrao dos CronJobs:
- `spec.timeZone: "America/Sao_Paulo"` em ambos os manifests.
- Altere esse campo se precisar de outro fuso.

3. Ajuste configuracoes em `k8s/base/config.yaml`:
- `SCHEDULE_NAME`
- `SCHEDULE_SCOPE`
- `ARGO_ENABLED`
- `VERBOSE`
- `DRY_RUN`
- `DEFAULT_STARTUP_REPLICAS`
- `PROTECTED_APP_STRICT_MODE`

4. Se usar Argo CD, preencha `ARGO_SERVER` e `ARGO_TOKEN` em `k8s/base/config.yaml` (Secret).

5. Aplique manifests:

```bash
kubectl apply -k k8s/base
```

### Opcao 2: Multiplas janelas

Use `k8s/base/multi-window` para rodar mais de um par de CronJobs com schedules diferentes.

Janelas de exemplo:

- `dev-weekday`: desliga `20:00` e liga `08:00` (seg-sex)
- `qa-weekday`: desliga `22:00` e liga `07:00` (seg-sex)

Rotule os namespaces conforme a janela:

```yaml
metadata:
  labels:
    offhours.platform.io/schedule: "dev-weekday"
```

ou

```yaml
metadata:
  labels:
    offhours.platform.io/schedule: "qa-weekday"
```

Se estiver usando `SCHEDULE_SCOPE=deployment`, aplique a label direto nos deployments:

```yaml
metadata:
  labels:
    offhours.platform.io/schedule: "dev-weekday"
```

Aplique os manifests:

```bash
kubectl apply -k k8s/base/multi-window
```

## Execucao local

1. Copie `.env.example` para `.env` e ajuste valores.
2. Rode:

```bash
make run-shutdown
make run-startup
```

## Build da imagem

```bash
make build IMAGE=docker.io/davidferreira21/k8s-offhours:latest
```

## Exemplos de cenarios

Aplicar os cenarios de exemplo:

```bash
kubectl apply -f k8s/examples/scenarios/scenario-1-namespace-scope.yaml
kubectl apply -f k8s/examples/scenarios/scenario-2-deployment-scope.yaml
kubectl apply -f k8s/examples/scenarios/scenario-3-argopp-override.yaml
kubectl apply -f k8s/examples/scenarios/scenario-4-mixed-protected-app.yaml
```

Cenarios incluidos:

- `scenario-1-namespace-scope.yaml`: uso de `SCHEDULE_SCOPE=namespace` com deployment protegido
- `scenario-2-deployment-scope.yaml`: uso de `SCHEDULE_SCOPE=deployment` com label no deployment
- `scenario-3-argopp-override.yaml`: override de apps Argo via `offhours.platform.io/argopp`
- `scenario-4-mixed-protected-app.yaml`: app mista (protegido + nao protegido) para testar `PROTECTED_APP_STRICT_MODE`

## Limitacoes

- Nao manipula infraestrutura diretamente, apenas replicas de deployments
- Nao silencia alertas
- Sem node autoscaling nao ha economia de infraestrutura

## Recomendacao de uso

- Solucao recomendada para ambientes HML, com foco em reducao de custo fora do horario comercial.
- Nao recomendado para producao.

## Proximos passos sugeridos

- Mover Secret para External Secrets/Vault
- Adicionar testes automatizados do script
- Adicionar suporte a StatefulSet (opcional)
- Publicar imagem CI/CD com versionamento semantico
