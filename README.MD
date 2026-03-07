# K8s OffHours

K8s OffHours e um toolkit operacional para Kubernetes que reduz workloads fora do horario de uso e restaura no inicio da janela operacional. A proposta e reduzir custo em ambientes nao produtivos com automacao previsivel baseada em labels.

## Problema

Muitos ambientes de desenvolvimento, QA e homologacao ficam ativos 24x7 mesmo sem uso continuo. Isso mantem pods e nodes ativos sem necessidade.

O K8s OffHours existe para automatizar esse ciclo com seguranca:

- reduzir workloads elegiveis para `0` no off-hours
- restaurar replicas no inicio do expediente
- integrar com fluxo GitOps quando necessario

## Recursos principais

- Selecao de alvo por label em `namespace` ou `deployment`
- Orquestracao de `shutdown` e `startup` por `CronJob`
- Protecao de workloads criticos via annotation
- Integracao opcional com Argo CD (pause/resume/sync)
- Estrategias opcionais para HPA:
  - `min-zero` (best-effort)
  - `delete-restore` (deterministico com backup)
  - `delete-only` (orientado a GitOps, sem restauracao pela ferramenta)
- Suporte a multi-window (multiplas releases/manifests)
- Modos `dry-run` e `verbose` para validacao segura

## Visao de arquitetura

O K8s OffHours usa execucao orientada por CronJob.

```text
CronJob (shutdown/startup)
        |
        v
Engine Python (scripts/offhours.py)
        |
        +--> API do Kubernetes (descoberta + scale de workloads)
        |
        +--> API do Argo CD (opcional: pause/resume/sync)
        |
        +--> Estado em ConfigMap (replicas + backup de HPA quando habilitado)
```

### 1. Como os CronJobs disparam o engine

- Sao implantados dois CronJobs: um para `shutdown` e outro para `startup`
- Os dois executam o mesmo engine, mudando apenas a variavel `ACTION`
- O comportamento final e controlado por variaveis em ConfigMap/Secret

### 2. Como os workloads sao descobertos

A descoberta e sempre baseada em label:

- Chave: `offhours.platform.io/schedule`
- `SCHEDULE_NAME` deve ser exatamente igual ao valor da label

Escopos suportados:

- `SCHEDULE_SCOPE=namespace`: seleciona namespaces por label e processa os deployments internos
- `SCHEDULE_SCOPE=deployment`: seleciona deployments diretamente por label

Protecao de workload:

- Annotation `offhours.platform.io/protected=true` impede scale daquele deployment

### 3. Como o HPA e tratado

O K8s OffHours suporta tres modos:

- `HPA_MIN_ZERO_ENABLED=true`
  - tenta patchar `spec.minReplicas=0` no shutdown
  - restaura `minReplicas` original no startup
  - modo best-effort (o cluster pode rejeitar scale-to-zero)
- `HPA_DELETE_RESTORE_ENABLED=true`
  - salva o manifesto completo do HPA em ConfigMap tecnico
  - deleta o HPA no shutdown
  - recria o HPA no startup
- `HPA_DELETE_ONLY_ENABLED=true`
  - deleta o HPA no shutdown
  - nao restaura no startup
  - recomendado apenas quando GitOps vai reconciliar o manifesto do HPA

Regra de precedencia:

- Se `HPA_DELETE_RESTORE_ENABLED=true` e `HPA_DELETE_ONLY_ENABLED=true`, prevalece `delete-restore`.

### 4. Como o estado e armazenado

- Replicas originais dos deployments ficam em annotation no proprio deployment
- Estado de HPA (quando `delete-restore` esta habilitado) fica em ConfigMaps tecnicos no namespace da ferramenta (exemplo: `offhours-system`)

## Inicio rapido

### Passo 1. Instalar com Helm

```bash
helm repo add k8s-offhours https://davidferreira21.github.io/K8s-OffHours
helm repo update
helm upgrade --install offhours k8s-offhours/k8s-offhours \
  -n offhours-system --create-namespace \
  --set config.scheduleName=dev-weekday \
  --set config.scheduleScope=namespace \
  --set argocd.enabled=false
```

### Passo 2. Aplicar label no alvo

```bash
# escopo namespace
kubectl label ns <namespace> offhours.platform.io/schedule=dev-weekday --overwrite

# escopo deployment
kubectl -n <namespace> label deploy <deployment> offhours.platform.io/schedule=dev-weekday --overwrite
```

### Passo 3. Validar manualmente

```bash
kubectl -n offhours-system create job --from=cronjob/offhours-k8s-offhours-shutdown manual-shutdown
kubectl -n offhours-system logs -f job/manual-shutdown

kubectl -n offhours-system create job --from=cronjob/offhours-k8s-offhours-startup manual-startup
kubectl -n offhours-system logs -f job/manual-startup
```

## Exemplo de uso

Namespace compartilhado de desenvolvimento com janela util:

- Startup: `08:00` (seg-sex)
- Shutdown: `20:00` (seg-sex)
- Label: `offhours.platform.io/schedule=dev-weekday`

Comportamento esperado:

- No shutdown, deployments elegiveis vao para `0`
- No startup, replicas sao restauradas por estado salvo/fallback
- Workloads protegidos sao ignorados

## Documentacao

- Entrada principal: [docs/README.md](docs/README.md)
- Arquitetura: [docs/architecture.md](docs/architecture.md)
- Configuracao: [docs/configuration.md](docs/configuration.md)
- Deploy: [docs/deploy.md](docs/deploy.md)
- Operacao e seguranca: [docs/operations.md](docs/operations.md)
- Cenarios de validacao: [docs/scenarios.md](docs/scenarios.md)
- Otimizacao de custo: [docs/cost-optimization.md](docs/cost-optimization.md)
- Guia de usuario Argo CD: [docs/argocd-offhours-user.md](docs/argocd-offhours-user.md)

## Estrutura do projeto

```text
.
├── scripts/
│   └── offhours.py
├── k8s/
│   ├── base/
│   └── examples/
├── helm/
│   └── k8s-offhours/
├── docs/
├── tests/
├── Dockerfile
├── Makefile
└── .env.example
```

## Contribuicao

Contribuicoes sao bem-vindas. Comece por:

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- [SECURITY.md](SECURITY.md)

## Licenca

Este projeto esta sob licenca MIT. Veja [LICENSE](LICENSE).
