# Arquitetura

## Princípios de design

O K8s OffHours foi projetado seguindo alguns princípios arquiteturais:

* **Declarative first**
  A seleção de workloads é baseada exclusivamente em labels Kubernetes.

* **Operações idempotentes**
  Execuções repetidas não geram inconsistências no estado dos workloads.

* **Compatibilidade com GitOps**
  Integração opcional com Argo CD para evitar drift em ambientes reconciliados.

* **Cloud-agnostic**
  Funciona em qualquer cluster Kubernetes com suporte a autoscaling.

* **Baixa complexidade operacional**
  A solução não utiliza CRDs nem Operators, utilizando apenas recursos nativos do Kubernetes.

---

# Funcionamento geral

O comportamento do K8s OffHours é controlado por variáveis de ambiente e executado através de CronJobs que disparam o engine principal.

O engine executa operações de:

* descoberta de workloads
* tratamento de autoscalers
* escala de deployments
* integração opcional com Argo CD

---

# Escopo do schedule (`SCHEDULE_SCOPE`)

Define como os workloads elegíveis serão descobertos.

Valores suportados:

* **`namespace` (padrão)**
  Seleciona namespaces por label e processa todos os deployments dentro deles.

* **`deployment`**
  Seleciona diretamente deployments que possuem a label configurada.

Label utilizada em ambos os modos:

```yaml
offhours.platform.io/schedule: "<schedule-name>"
```

---

# Proteção de deployments

Deployments podem ser explicitamente excluídos da automação utilizando a annotation abaixo:

```yaml
metadata:
  annotations:
    offhours.platform.io/protected: "true"
```

Deployments marcados como protegidos nunca serão escalados pelo K8s OffHours.

---

# Integração com Argo CD

Quando a integração com Argo CD está habilitada (`ARGO_ENABLED=true`), o comportamento da ferramenta muda para evitar conflitos com o reconciliador GitOps.

## Fluxo de shutdown

Durante o shutdown:

1. O sync das Applications elegíveis é pausado
2. Os deployments elegíveis são escalados para `0`

## Fluxo de startup

Durante o startup:

1. O sync das Applications é reativado
2. Um sync é disparado para restaurar o estado desejado

---

# Descoberta de Applications no Argo CD

A descoberta de Applications associadas aos workloads segue a seguinte ordem:

1. **Override manual por namespace**

Utilizado quando:

```text
ARGO_DISCOVERY_USE_MANUAL=true
```

Annotation utilizada:

```text
offhours.platform.io/argopp
```

---

2. **Descoberta automática**

Quando:

```text
ARGO_DISCOVERY_USE_AUTOMATIC=true
```

A cadeia de descoberta é:

1. `argocd.argoproj.io/instance` (label)
2. `argocd.argoproj.io/tracking-id` (annotation)
3. fallback por `spec.destination.namespace` consultando a API do Argo CD

Configuração recomendada:

* descoberta automática habilitada
* override manual desabilitado

---

# Proteção em aplicações mistas

Algumas aplicações podem possuir deployments protegidos e não protegidos simultaneamente.

O comportamento é controlado por:

```text
PROTECTED_APP_STRICT_MODE
```

## `true` (recomendado)

Se uma Application possuir ao menos um deployment protegido:

* o sync da Application não é pausado
* nenhum deployment da Application é escalado
* no startup essa Application também não recebe `resume/sync`

Isso evita inconsistências em aplicações parcialmente protegidas.

---

## `false`

* o sync da Application é pausado
* apenas deployments não protegidos são escalados

---

# Modo sem Argo CD

Quando:

```text
ARGO_ENABLED=false
```

A ferramenta opera diretamente sobre os deployments.

## Shutdown

Durante o shutdown:

1. As replicas originais são salvas em annotation no deployment
2. O deployment é escalado para `0`

---

## Startup

Durante o startup:

1. As replicas são restauradas a partir da annotation
2. Caso não exista annotation, utiliza-se:

```text
DEFAULT_STARTUP_REPLICAS
```

---

# Tratamento de HPA e persistencia de estado

Os Deployments podem ter HPA associado. Nesses casos, o comportamento pode ser ajustado por modo:

* **`HPA_MIN_ZERO_ENABLED=true`**
  tenta patchar `spec.minReplicas=0` no shutdown e restaura no startup (best-effort).

* **`HPA_DELETE_RESTORE_ENABLED=true`**
  salva o manifesto do HPA em ConfigMap tecnico, deleta no shutdown e recria no startup.

* **`HPA_DELETE_ONLY_ENABLED=true`**
  deleta no shutdown e nao restaura no startup (recomendado apenas com reconciliacao GitOps).

Precedencia:

* se `HPA_DELETE_RESTORE_ENABLED=true` e `HPA_DELETE_ONLY_ENABLED=true`, prevalece `HPA_DELETE_RESTORE_ENABLED`.

Persistencia de estado:

* replicas originais de deployment: annotation no proprio deployment.
* estado de HPA no modo `delete-restore`: ConfigMap tecnico no namespace da ferramenta (ex.: `offhours-system`).

---

# Idempotência

O engine foi projetado para garantir execuções seguras e repetíveis.

Comportamentos garantidos:

* Se o deployment já estiver em `replicas=0`, a operação não falha
* Se `offhours.platform.io/original-replicas` já existir, não é sobrescrito
* No modo Argo, se uma Application já estiver pausada, nenhuma falha é gerada

---

# Engine principal

Toda a lógica da ferramenta está implementada em:

```
engine/offhours.py
engine/offhours_core/settings.py
```

Principais blocos do código:

* **Configuracao e validacao de ambiente**
  `Settings`, `load_settings`, `validate_env`

* **Integração com Kubernetes**
  `kubectl_get`, `get_target_*`, `scale_deployment`

* **Integração com API do Argo CD**
  `argo_request`, `get_all_applications`, `get_app`

* **Descoberta de Applications**
  `get_argocd_apps_from_namespace`, `get_argocd_app_for_deployment`

* **Orquestração da execução**
  `handle_*`, `main`

Referencia detalhada do motor Python:

- [engine-python.md](engine-python.md)
