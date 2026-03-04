import importlib.util
import io
from pathlib import Path
from urllib import error

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "offhours.py"
SPEC = importlib.util.spec_from_file_location("offhours", MODULE_PATH)
offhours = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(offhours)


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    offhours.reset_runtime_caches()
    keys = [
        "SCHEDULE_NAME",
        "ACTION",
        "ARGO_ENABLED",
        "SCHEDULE_SCOPE",
        "DEFAULT_STARTUP_REPLICAS",
        "PROTECTED_APP_STRICT_MODE",
        "DRY_RUN",
        "VERBOSE",
        "ARGO_SERVER",
        "ARGO_TOKEN",
        "ARGO_SCHEME",
        "ARGO_INSECURE",
        "ARGO_DISCOVERY_USE_AUTOMATIC",
        "ARGO_DISCOVERY_USE_MANUAL",
        "ARGO_API_RETRIES",
        "ARGO_API_RETRY_BASE_SECONDS",
        "ARGO_API_RETRY_MAX_SECONDS",
    ]
    for key in keys:
        monkeypatch.delenv(key, raising=False)


def test_discovery_uses_instance_and_tracking_first(monkeypatch):
    monkeypatch.setenv("ARGO_DISCOVERY_USE_AUTOMATIC", "true")
    monkeypatch.setenv("ARGO_DISCOVERY_USE_MANUAL", "false")

    monkeypatch.setattr(
        offhours,
        "get_all_applications",
        lambda: [
            {"metadata": {"name": "app-a"}},
            {"metadata": {"name": "app-b"}},
        ],
    )
    monkeypatch.setattr(offhours, "get_deployments", lambda namespace: ["api", "worker"])

    def fake_get_deployment(namespace, deploy):
        if deploy == "api":
            return {
                "metadata": {
                    "labels": {"argocd.argoproj.io/instance": "app-a"},
                    "annotations": {},
                }
            }
        return {
            "metadata": {
                "labels": {},
                "annotations": {
                    "argocd.argoproj.io/tracking-id": "app-b:apps/Deployment:ns/worker"
                },
            }
        }

    monkeypatch.setattr(offhours, "get_deployment", fake_get_deployment)

    apps = offhours.get_argocd_apps_from_namespace("ns")

    assert apps == {"app-a", "app-b"}


def test_discovery_uses_argopp_override_when_enabled(monkeypatch):
    monkeypatch.setenv("ARGO_DISCOVERY_USE_AUTOMATIC", "false")
    monkeypatch.setenv("ARGO_DISCOVERY_USE_MANUAL", "true")

    monkeypatch.setattr(
        offhours,
        "get_all_applications",
        lambda: [
            {"metadata": {"name": "known-app"}},
        ],
    )
    monkeypatch.setattr(offhours, "get_deployments", lambda namespace: ["api"])
    monkeypatch.setattr(
        offhours,
        "get_deployment",
        lambda namespace, deploy: {"metadata": {"labels": {}, "annotations": {}}},
    )
    monkeypatch.setattr(
        offhours,
        "kubectl_get",
        lambda kind, namespace=None, selector=None, name=None: {
            "metadata": {"labels": {"offhours.platform.io/argopp": "unknown-app, known-app"}}
        },
    )

    apps = offhours.get_argocd_apps_from_namespace("ns")

    assert apps == {"known-app"}


def test_discovery_prefers_manual_when_both_methods_enabled(monkeypatch):
    monkeypatch.setenv("ARGO_DISCOVERY_USE_AUTOMATIC", "true")
    monkeypatch.setenv("ARGO_DISCOVERY_USE_MANUAL", "true")

    monkeypatch.setattr(
        offhours,
        "get_all_applications",
        lambda: [
            {"metadata": {"name": "manual-app"}},
            {"metadata": {"name": "auto-app"}},
        ],
    )
    monkeypatch.setattr(offhours, "get_deployments", lambda namespace: ["api"])
    monkeypatch.setattr(
        offhours,
        "get_deployment",
        lambda namespace, deploy: {
            "metadata": {
                "labels": {"argocd.argoproj.io/instance": "auto-app"},
                "annotations": {},
            }
        },
    )
    monkeypatch.setattr(
        offhours,
        "kubectl_get",
        lambda kind, namespace=None, selector=None, name=None: {
            "metadata": {"annotations": {"offhours.platform.io/argopp": "manual-app"}}
        },
    )

    apps = offhours.get_argocd_apps_from_namespace("ns")

    assert apps == {"manual-app"}


def test_shutdown_namespace_strict_mode_blocks_mixed_app(monkeypatch):
    monkeypatch.setenv("ARGO_ENABLED", "true")
    monkeypatch.setenv("PROTECTED_APP_STRICT_MODE", "true")

    monkeypatch.setattr(offhours, "get_argocd_apps_from_namespace", lambda namespace: {"app-main"})
    monkeypatch.setattr(offhours, "app_has_protected_deployment", lambda app, namespace: True)
    monkeypatch.setattr(offhours, "get_deployments", lambda namespace: ["api", "critical"])
    monkeypatch.setattr(
        offhours,
        "is_protected_deployment",
        lambda namespace, deploy: deploy == "critical",
    )
    monkeypatch.setattr(
        offhours, "get_argocd_app_for_deployment", lambda namespace, deploy: "app-main"
    )

    paused = []
    scaled = []
    saved = []

    monkeypatch.setattr(offhours, "argo_pause_app", lambda app: paused.append(app))
    monkeypatch.setattr(
        offhours, "scale_deployment", lambda ns, dep, r: scaled.append((ns, dep, r))
    )
    monkeypatch.setattr(offhours, "save_original_replicas", lambda ns, dep: saved.append((ns, dep)))

    offhours.handle_shutdown_namespace("ns")

    assert paused == []
    assert saved == []
    assert scaled == []


def test_startup_namespace_strict_mode_blocks_mixed_app_resume(monkeypatch):
    monkeypatch.setenv("ARGO_ENABLED", "true")
    monkeypatch.setenv("PROTECTED_APP_STRICT_MODE", "true")

    monkeypatch.setattr(offhours, "get_argocd_apps_from_namespace", lambda namespace: {"app-main"})
    monkeypatch.setattr(offhours, "app_has_protected_deployment", lambda app, namespace: True)

    resumed = []
    monkeypatch.setattr(offhours, "argo_resume_and_sync_app", lambda app: resumed.append(app))

    offhours.handle_startup_namespace("ns")

    assert resumed == []


def test_argo_request_mutate_respects_dry_run(monkeypatch):
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("ARGO_SERVER", "argocd.example.com")
    monkeypatch.setenv("ARGO_TOKEN", "token")

    called = {"urlopen": False}

    def fake_urlopen(*args, **kwargs):
        called["urlopen"] = True
        raise AssertionError("urlopen should not be called in DRY_RUN mutate")

    monkeypatch.setattr(offhours.request, "urlopen", fake_urlopen)

    result = offhours.argo_request(
        "PATCH",
        "/api/v1/applications/test",
        {"spec": {"syncPolicy": None}},
        mutate=True,
    )

    assert result == {}
    assert called["urlopen"] is False


def test_get_restore_replicas_uses_annotation_and_default(monkeypatch):
    monkeypatch.setenv("DEFAULT_STARTUP_REPLICAS", "2")

    monkeypatch.setattr(
        offhours,
        "get_deployment",
        lambda namespace, deploy: {
            "metadata": {"annotations": {"offhours.platform.io/original-replicas": "3"}}
        },
    )
    assert offhours.get_restore_replicas("ns", "api") == 3

    monkeypatch.setattr(
        offhours,
        "get_deployment",
        lambda namespace, deploy: {"metadata": {"annotations": {}}},
    )
    assert offhours.get_restore_replicas("ns", "api") == 2


def test_argo_request_retries_on_http_429(monkeypatch):
    monkeypatch.setenv("ARGO_SERVER", "argocd.example.com")
    monkeypatch.setenv("ARGO_TOKEN", "token")
    monkeypatch.setenv("ARGO_API_RETRIES", "2")
    monkeypatch.setenv("ARGO_API_RETRY_BASE_SECONDS", "0.01")
    monkeypatch.setenv("ARGO_API_RETRY_MAX_SECONDS", "0.01")

    attempts = {"count": 0}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"items": []}'

    def fake_urlopen(req, context=None, timeout=20):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise error.HTTPError(
                url=req.full_url,
                code=429,
                msg="Too Many Requests",
                hdrs=None,
                fp=io.BytesIO(b"rate limited"),
            )
        return FakeResponse()

    monkeypatch.setattr(offhours.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(offhours.time, "sleep", lambda _: None)

    data = offhours.argo_request("GET", "/api/v1/applications")

    assert attempts["count"] == 2
    assert data == {"items": []}
