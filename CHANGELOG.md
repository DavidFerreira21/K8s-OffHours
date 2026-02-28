# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog.

## [0.1.0] - 2026-02-28

### Added

- Initial Python runtime implementation in `scripts/offhours.py`.
- Docker runtime for Python + `kubectl`.
- Kubernetes manifests in `k8s/base`:
  - `namespace`, `rbac`, `config`, `cronjob-shutdown`, `cronjob-startup`, `kustomization`.
- Multi-window manifests in `k8s/base/multi-window`.
- Scenario examples in `k8s/examples/scenarios`.

- Offhours execution modes:
  - `ARGO_ENABLED=true` (Argo API mode).
  - `ARGO_ENABLED=false` (Kubernetes-only mode).

- Schedule scopes via `SCHEDULE_SCOPE`:
  - `namespace` (namespace label targeting).
  - `deployment` (deployment label targeting).

- Argo application discovery controls and fallback chain:
  - `argocd.argoproj.io/instance`.
  - `argocd.argoproj.io/tracking-id`.
  - namespace override via `offhours.platform.io/argopp`.
  - Argo API lookup by destination namespace.

- Protected workload handling:
  - `offhours.platform.io/protected=true`.
  - strict mixed-app behavior via `PROTECTED_APP_STRICT_MODE=true|false`.

- Replica handling:
  - original replica persistence via `offhours.platform.io/original-replicas`.
  - fallback restore via `DEFAULT_STARTUP_REPLICAS`.

- Retry/backoff for transient Argo API errors (`429`/`5xx`) with env-based tuning:
  - `ARGO_API_RETRIES`.
  - `ARGO_API_RETRY_BASE_SECONDS`.
  - `ARGO_API_RETRY_MAX_SECONDS`.

- Test and quality tooling:
  - `pytest` suite for discovery, strict mode, dry-run, restore and retry scenarios.
  - `ruff` lint/format configuration.
  - `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`.

- CI pipeline in GitHub Actions:
  - `ruff` lint + format check.
  - `pytest` test execution.
  - Docker build + Trivy scan.
  - Docker Hub push for branch SHA and release tags.

- Documentation structure:
  - detailed docs split by topic in `docs/` (`architecture`, `configuration`, `deploy`, `operations`, `scenarios`, `argocd-offhours-user`, `README`).
  - README updated with product value, operation model, deployment flow and contextual links to detailed docs.

- MIT license (`LICENSE`).

### Changed

- Project standardized on Python-only runtime (shell runtime removed).
- CronJob image defaults/documentation aligned to Docker Hub usage and real-cluster deployment flow.
- Trivy scan configured to focus on vulnerability scanning (`scanners: vuln`).
- Dockerfile updated to newer Alpine base and stable `kubectl` download with checksum validation.

### Security

- Documented recommendation to avoid committing `ARGO_TOKEN` in versioned manifests.
- Added guidance for secret management with External Secrets, Sealed Secrets, or Vault.
