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
| `ARGO_DISCOVERY_USE_INSTANCE_LABEL` | Nao | Habilita descoberta por `instance` (padrao: `true`) |
| `ARGO_DISCOVERY_USE_TRACKING_ID` | Nao | Habilita descoberta por `tracking-id` (padrao: `true`) |
| `ARGO_DISCOVERY_USE_ARGOPP` | Nao | Habilita override `offhours.platform.io/argopp` (padrao: `false`) |
| `ARGO_DISCOVERY_USE_DEST_NAMESPACE_FALLBACK` | Nao | Habilita fallback por destination namespace (padrao: `false`) |
| `ARGO_API_RETRIES` | Nao | Retries para erro transiente da API Argo (padrao agressivo: `2`) |
| `ARGO_API_RETRY_BASE_SECONDS` | Nao | Backoff base em segundos (padrao agressivo: `0.2`) |
| `ARGO_API_RETRY_MAX_SECONDS` | Nao | Teto do backoff em segundos (padrao agressivo: `1.0`) |
| `VERBOSE` | Nao | Logs detalhados (`true/false`) |
| `DRY_RUN` | Nao | Nao executa mudancas (`true/false`) |
| `DEFAULT_STARTUP_REPLICAS` | Nao | Replica padrao no startup sem annotation |
| `PROTECTED_APP_STRICT_MODE` | Nao | `true` (seguro) ou `false` (agressivo) |

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
