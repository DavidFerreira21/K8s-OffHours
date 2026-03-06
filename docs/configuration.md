# Configuracao

## Variaveis de ambiente

| Variavel | Obrigatoria | Descricao |
| --- | --- | --- |
| `SCHEDULE_NAME` | Sim | Nome do schedule (valor da label) |
| `SCHEDULE_SCOPE` | Nao | `namespace` (padrao) ou `deployment` |
| `ACTION` | Sim | `shutdown` ou `startup` |
| `ARGO_ENABLED` | Sim | `true` ou `false` |
| `ARGO_SERVER` | Se `ARGO_ENABLED=true` | Endpoint do Argo CD (host:porta) |
| `ARGO_TOKEN` | Se `ARGO_ENABLED=true` | Token de API do Argo CD |
| `ARGO_SCHEME` | Nao | `https` (padrao) ou `http` |
| `ARGO_INSECURE` | Nao | `true` para ignorar validacao TLS em `https` |
| `ARGO_DISCOVERY_USE_AUTOMATIC` | Nao | Habilita descoberta automatica (`instance`, `tracking-id`, fallback por destination namespace) (padrao: `true`) |
| `ARGO_DISCOVERY_USE_MANUAL` | Nao | Habilita override manual por namespace via `offhours.platform.io/argopp` (padrao: `false`) |
| `ARGO_API_RETRIES` | Nao | Retries para erro transiente da API Argo (padrao agressivo: `2`) |
| `ARGO_API_RETRY_BASE_SECONDS` | Nao | Backoff base em segundos (padrao agressivo: `0.2`) |
| `ARGO_API_RETRY_MAX_SECONDS` | Nao | Teto do backoff em segundos (padrao agressivo: `1.0`) |
| `VERBOSE` | Nao | Logs detalhados (`true/false`) |
| `DRY_RUN` | Nao | Nao executa mudancas (`true/false`) |
| `DEFAULT_STARTUP_REPLICAS` | Nao | Replica padrao no startup sem annotation |
| `HPA_MIN_ZERO_ENABLED` | Nao | Quando `true`, tenta patchar `minReplicas=0` do HPA no shutdown e restaurar no startup (best-effort, padrao: `false`) |
| `HPA_DELETE_RESTORE_ENABLED` | Nao | Quando `true`, salva HPA em ConfigMap tecnico, deleta no shutdown e recria no startup (padrao: `false`) |
| `HPA_DELETE_ONLY_ENABLED` | Nao | Quando `true`, deleta HPA no shutdown sem salvar estado e nao restaura no startup; sem GitOps/recriacao manual o HPA fica ausente (padrao: `false`) |
| `PROTECTED_APP_STRICT_MODE` | Nao | `true` (seguro) ou `false` (agressivo) |

Prioridade entre modos de HPA:

- Se `HPA_DELETE_ONLY_ENABLED=true` e `HPA_DELETE_RESTORE_ENABLED=true`, prevalece `HPA_DELETE_RESTORE_ENABLED`.
- Se apenas `HPA_DELETE_ONLY_ENABLED=true`, esse modo tem prioridade sobre `HPA_MIN_ZERO_ENABLED`.
- Se `HPA_DELETE_RESTORE_ENABLED=true`, esse modo tem prioridade e `HPA_MIN_ZERO_ENABLED` e ignorado.

Regra importante:

- `SCHEDULE_NAME` deve ser exatamente igual ao valor da label `offhours.platform.io/schedule` aplicada no namespace/deployment alvo.

Exemplo:

- label: `offhours.platform.io/schedule: "dev-weekday"`
- variavel: `SCHEDULE_NAME=dev-weekday`

## Labels e annotations usadas

### Schedule

```yaml
metadata:
  labels:
    offhours.platform.io/schedule: "dev"
```

### Deployment protegido

```yaml
metadata:
  annotations:
    offhours.platform.io/protected: "true"
```

### Override de app Argo por namespace

```yaml
metadata:
  annotations:
    offhours.platform.io/argopp: "smb-app,billing-app"
```
