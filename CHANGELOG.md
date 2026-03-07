# Changelog

Todas as mudancas relevantes deste projeto sao documentadas neste arquivo.

O formato segue o Keep a Changelog.

## [0.2.3] - 2026-03-07

### Adicionado

- Nova documentacao interna do motor:
  - `docs/engine-python.md` (fluxo de execucao, modulos e mapa de funcoes).

### Alterado

- Refatoracao interna em `engine/offhours.py` para melhorar legibilidade e manutencao sem alterar comportamento:
  - centralizacao do carregamento de configuracao com `Settings`.
  - reducao de duplicacao nos fluxos de shutdown/startup.
  - clarificacao da resolucao e precedencia dos modos de HPA.
- Introduzido `engine/offhours_core/settings.py` para isolar parsing e validacao de ambiente.
- Pasta de runtime renomeada de `scripts/` para `engine/`:
  - referencias atualizadas em Dockerfile, Makefile, workflow de CI, testes e docs.
- Manifests base e multi-window alinhados para imagem de release:
  - `david210/k8s-offhours:0.2.3`.
- Defaults do Helm alinhados para imagem de release:
  - `helm/k8s-offhours/values.yaml` com tag `0.2.3`.
- Documentacao atualizada em `README.MD` e `docs/` para Helm, cenarios, arquitetura e detalhes do motor.

### Corrigido

- Empacotamento de runtime no Docker apos refatoracao:
  - `Dockerfile` agora copia `engine/offhours_core` para evitar erro de import em runtime.
- Permissoes RBAC para modo HPA delete/restore:
  - adicionados verbos `create` e `delete` em `horizontalpodautoscalers` no base e no Helm.
- Alinhamento de metadata do chart Helm:
  - `helm/k8s-offhours/Chart.yaml` atualizado para `appVersion: 0.2.3`.

## [0.2.2] - 2026-03-06

### Adicionado

- Novo modo de tratamento de HPA `HPA_DELETE_ONLY_ENABLED`:
  - deleta HPAs alvo no `shutdown`.
  - nao restaura HPA no `startup`.
  - emite avisos fortes, inclusive quando usado com `ARGO_ENABLED=false`.
- Exemplo realista de HPA para escopo por deployment:
  - `k8s/examples/scenarios/hpa-scenario-2-checkout-api.yaml`.
  - inclui metricas de CPU + memoria e politicas de comportamento de escala.
- Cobertura adicional de testes para precedencia de modos HPA e comportamento delete-only.

### Alterado

- Controles de ciclo de vida de HPA expandidos e padronizados:
  - `HPA_MIN_ZERO_ENABLED` (patch/restore best-effort de `minReplicas=0`).
  - `HPA_DELETE_RESTORE_ENABLED` (salva em ConfigMap tecnico, deleta no shutdown, restaura no startup).
  - `HPA_DELETE_ONLY_ENABLED` (deleta sem restaurar).
- Regra de precedencia atualizada:
  - quando `HPA_DELETE_ONLY_ENABLED=true` e `HPA_DELETE_RESTORE_ENABLED=true`, prevalece `HPA_DELETE_RESTORE_ENABLED`.
- Manifests do cenario 2 ajustados para maior realismo:
  - deployment `checkout-api` com requests/limits de CPU e memoria.
- Targets do Make `run-shutdown` e `run-startup` passaram a funcionar mesmo sem `./.env`.
- `.env.example` alinhado com flags atuais de runtime:
  - discovery atualizado para `ARGO_DISCOVERY_USE_AUTOMATIC` / `ARGO_DISCOVERY_USE_MANUAL`.
  - flags de modos HPA adicionadas.

### Corrigido

- RBAC ampliado para operacoes com HPA e estado de HPA:
  - acesso a `horizontalpodautoscalers.autoscaling`.
  - permissoes em `configmaps` necessarias ao modo delete-restore.
- Problema de parsing de shell em arquivos env:
  - placeholder de token alterado de `<token>` para `""` para evitar erro com `source`.
- Consistencia de documentacao atualizada em:
  - `README.MD`, `docs/configuration.md`, `docs/operations.md`, `docs/deploy.md`, `docs/scenarios.md` e README do chart Helm.

## [0.2.0] - 2026-03-04

### Adicionado

- Caches de runtime em `scripts/offhours.py` para reduzir chamadas repetidas em APIs Kubernetes/Argo:
  - cache de lista de deployments por namespace.
  - cache de deployment por `(namespace, name)`.
  - cache de namespace.
  - cache de lista e objeto de app Argo.
  - cache de deployments protegidos por namespace.
  - indice de ownership (`deployment -> app`) por namespace.
- Testes para precedencia de discovery manual e comportamento de strict-mode no startup.

### Alterado

- Controles de descoberta Argo simplificados de 4 flags para 2:
  - `ARGO_DISCOVERY_USE_AUTOMATIC`
  - `ARGO_DISCOVERY_USE_MANUAL`
- Precedencia de discovery atualizada:
  - override manual (`offhours.platform.io/argopp`) primeiro quando habilitado.
  - cadeia automatica (`instance`, `tracking-id`, fallback por destination namespace) depois.
- Comportamento de startup alinhado ao strict mode:
  - com `PROTECTED_APP_STRICT_MODE=true`, apps com deployments protegidos nao sao resumed/synced.
- Documentacao atualizada em `README.MD` e `docs/` para refletir:
  - novo modelo de discovery.
  - strict mode em shutdown e startup.
  - manifests Argo atualmente utilizados (`scenario-3` e `scenario-4`).
- CI atualizada para publicar Docker `latest` em pushes para `main/master` (alem da tag SHA).

### Corrigido

- Payload de patch da API Argo para pause/resume de application:
  - requests passaram a enviar `patchType` no body com merge patch esperado pela API.
- Alinhamento entre manifest/docs do scenario 3 para uso de override manual `argopp`.
- Melhorias de consistencia e legibilidade de script/docs (docstrings, comentarios, line-length).

## [0.1.0] - 2026-02-28

### Adicionado

- Implementacao inicial do runtime Python em `scripts/offhours.py`.
- Runtime Docker com Python + `kubectl`.
- Manifests Kubernetes em `k8s/base`:
  - `namespace`, `rbac`, `config`, `cronjob-shutdown`, `cronjob-startup`, `kustomization`.
- Manifests multi-window em `k8s/base/multi-window`.
- Cenarios de exemplo em `k8s/examples/scenarios`.

- Modos de execucao do Offhours:
  - `ARGO_ENABLED=true` (modo API Argo).
  - `ARGO_ENABLED=false` (modo Kubernetes-only).

- Escopos de schedule via `SCHEDULE_SCOPE`:
  - `namespace` (alvo por label de namespace).
  - `deployment` (alvo por label de deployment).

- Controles de discovery de application Argo e cadeia de fallback:
  - `argocd.argoproj.io/instance`.
  - `argocd.argoproj.io/tracking-id`.
  - override por namespace via `offhours.platform.io/argopp`.
  - lookup na API Argo por destination namespace.

- Tratamento de workloads protegidos:
  - `offhours.platform.io/protected=true`.
  - comportamento strict em app mista via `PROTECTED_APP_STRICT_MODE=true|false`.

- Tratamento de replicas:
  - persistencia da replica original via `offhours.platform.io/original-replicas`.
  - fallback de restore via `DEFAULT_STARTUP_REPLICAS`.

- Retry/backoff para erros transientes da API Argo (`429`/`5xx`) com tuning por env:
  - `ARGO_API_RETRIES`.
  - `ARGO_API_RETRY_BASE_SECONDS`.
  - `ARGO_API_RETRY_MAX_SECONDS`.

- Ferramentas de teste e qualidade:
  - suite `pytest` para cenarios de discovery, strict mode, dry-run, restore e retry.
  - configuracao `ruff` de lint/format.
  - `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`.

- Pipeline de CI no GitHub Actions:
  - lint + format check com `ruff`.
  - execucao de testes com `pytest`.
  - build Docker + scan Trivy.
  - push Docker Hub para SHA de branch e tags de release.

- Estrutura de documentacao:
  - docs detalhadas por topico em `docs/` (`architecture`, `configuration`, `deploy`, `operations`, `scenarios`, `argocd-offhours-user`, `README`).
  - README atualizado com valor do produto, modelo de operacao, fluxo de deploy e links de contexto.

- Licenca MIT (`LICENSE`).

### Alterado

- Projeto padronizado em runtime somente Python (runtime shell removido).
- Defaults/documentacao de imagem de CronJob alinhados ao uso em Docker Hub e deploy em cluster real.
- Scan Trivy configurado para foco em vulnerabilidades (`scanners: vuln`).
- Dockerfile atualizado para base Alpine mais nova e download estavel de `kubectl` com validacao de checksum.

### Seguranca

- Recomendacao documentada para nao versionar `ARGO_TOKEN` em manifests.
- Adicionada orientacao de gerenciamento de segredos com External Secrets, Sealed Secrets ou Vault.
