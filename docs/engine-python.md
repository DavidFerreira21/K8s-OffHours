# Motor Python (offhours)

Este documento descreve o motor Python do K8s OffHours: fluxo de execucao, modulos, funcoes principais e regras de decisao.

## Visao geral

O motor e executado pelo `CronJob` com `ACTION=shutdown` ou `ACTION=startup`.

Arquivos principais:

- `engine/offhours.py`: orquestracao principal e integracao Kubernetes/Argo.
- `engine/offhours_core/settings.py`: parsing e validacao de variaveis de ambiente.

## Fluxo de execucao

```text
main()
  -> reset_runtime_caches()
  -> validate_env() / load_settings()
  -> check_dependencies()
  -> resolve escopo (namespace/deployment)
  -> processa shutdown ou startup
```

## Modulo de configuracao

Arquivo: `engine/offhours_core/settings.py`

Responsabilidades:

- Ler env vars (`env_str`, `env_bool`, `env_int`, `env_float`)
- Validar valores obrigatorios e opcoes aceitas
- Montar objeto imutavel `Settings`

Validacoes importantes:

- `ACTION` aceita apenas `shutdown` ou `startup`
- `SCHEDULE_SCOPE` aceita apenas `namespace` ou `deployment`
- Quando `ARGO_ENABLED=true`, exige `ARGO_SERVER` e `ARGO_TOKEN`

## Orquestrador principal

Arquivo: `engine/offhours.py`

### Entrypoint

- `main`: inicializa contexto, loga configuracao ativa e direciona o fluxo.

### Camada utilitaria

- `run_cmd` / `run_json`: execucao de comandos e parse JSON.
- `run_kubectl_best_effort`: comando best-effort sem abortar o job inteiro.
- `log`, `warn`, `err`, `debug`: padrao de logs.

### Kubernetes

- `kubectl_get`: leitura generica de recursos.
- `get_target_namespaces`: alvo por label em namespace scope.
- `get_target_deployment_pairs`: alvo por label em deployment scope.
- `get_deployments`, `get_deployment`, `get_namespace`: leitura com cache em memoria.

### Replica handling

- `save_original_replicas`: salva replicas originais em annotation.
- `get_restore_replicas`: recupera annotation ou fallback `DEFAULT_STARTUP_REPLICAS`.
- `scale_deployment`: aplica scale.

### HPA handling

Modos:

- `min-zero`: patch de `minReplicas=0` (best-effort) e restauracao posterior.
- `delete-restore`: salva manifesto em ConfigMap tecnico, deleta no shutdown e recria no startup.
- `delete-only`: deleta no shutdown e nao restaura no startup.

Precedencia:

1. `delete-restore`
2. `delete-only`
3. `min-zero`

Funcoes principais:

- `maybe_handle_hpa_shutdown`
- `maybe_handle_hpa_startup`
- `maybe_delete_hpa_for_restore`
- `maybe_restore_deleted_hpa`
- `maybe_set_hpa_min_to_zero`
- `maybe_restore_hpa_min`

### Argo CD

- `argo_request`: cliente HTTP com retry/backoff.
- `get_all_applications`, `get_app`: leitura de Applications.
- `argo_pause_app`: pausa sync.
- `argo_resume_and_sync_app`: retoma sync e dispara sync.

### Descoberta de Application

- `get_argocd_apps_from_namespace`: descoberta por `argopp` (manual) e cadeia automatica.
- `get_argocd_app_for_deployment`: dono da app por deployment.

### Handlers de acao

- `handle_shutdown_namespace`
- `handle_startup_namespace`
- `handle_shutdown_deployment_scope`
- `handle_startup_deployment_scope`

Esses handlers aplicam:

- protecao por annotation (`offhours.platform.io/protected=true`)
- regras de strict mode (`PROTECTED_APP_STRICT_MODE`)
- chamadas de HPA conforme modo ativo

## Caches em runtime

Caches em memoria sao usados para reduzir chamadas repetidas durante o mesmo job:

- lista de deployments por namespace
- objeto de deployment por `(namespace, name)`
- namespace object
- app list e app objects do Argo
- index de ownership deployment->app

Todos sao limpos no inicio da execucao por `reset_runtime_caches`.

## Regras de seguranca e comportamento

- Operacoes sao idempotentes sempre que possivel.
- Falhas criticas encerram execucao com `fail`.
- Operacoes opcionais/auxiliares usam best-effort com warning.
- `DRY_RUN=true` evita mutacoes e imprime comandos/acoes previstas.

## Como ler o codigo rapidamente

Ordem recomendada:

1. `engine/offhours_core/settings.py` (`Settings`, validacao de env)
2. `main` em `engine/offhours.py`
3. handlers `handle_*`
4. bloco HPA
5. bloco Argo/discovery
