# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog.

## [0.1.0] - 2026-02-26

### Added

- Initial Python runtime implementation: `scripts/offhours.py`
- Docker runtime for Python + kubectl
- Kubernetes manifests in `k8s/base` (`namespace`, `rbac`, `config`, `cronjobs`, `kustomization`)
- Multi-window manifests in `k8s/base/multi-window`
- Scenario examples in `k8s/examples/scenarios`

- Offhours execution modes:
- `ARGO_ENABLED=true` (Argo API mode)
- `ARGO_ENABLED=false` (Kubernetes-only mode)

- Schedule scopes via `SCHEDULE_SCOPE`:
- `namespace` (namespace label targeting)
- `deployment` (deployment label targeting)

- Argo application discovery fallback chain:
- Namespace override via `offhours.platform.io/argopp`
- `argocd.argoproj.io/instance`
- `argocd.argoproj.io/tracking-id`
- Argo API applications filtered by destination namespace

- Protected workload handling via `offhours.platform.io/protected=true`
- Strict mixed-app behavior via `PROTECTED_APP_STRICT_MODE=true|false`
- Original replica persistence via `offhours.platform.io/original-replicas`
- Dry-run and verbose execution support (`DRY_RUN`, `VERBOSE`)
- CronJob timezone support (`spec.timeZone`) with default `America/Sao_Paulo`

### Security

- Documented recommendation to avoid committing `ARGO_TOKEN` in versioned manifests.
- Added guidance for secret management with External Secrets, Sealed Secrets, or Vault.
