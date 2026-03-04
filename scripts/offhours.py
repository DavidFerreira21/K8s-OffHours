#!/usr/bin/env python3
"""Off-hours scaler for Kubernetes workloads with optional Argo CD integration.

Execution summary:
- Select targets by `offhours.platform.io/schedule`.
- `shutdown`: persist current replicas and scale eligible deployments to zero.
- `startup`: restore replicas (Kubernetes mode) or resume/sync Argo applications.
"""

import json
import os
import shutil
import ssl
import subprocess
import sys
import time
from urllib import error, parse, request

SCRIPT_NAME = "offhours"

# Runtime-only caches to reduce repeated API calls during one job execution.
_DEPLOYMENTS_CACHE: dict[str, list[str]] = {}
_DEPLOYMENT_CACHE: dict[tuple[str, str], dict] = {}
_NAMESPACE_CACHE: dict[str, dict] = {}
_ALL_APPS_CACHE: list[dict] | None = None
_APP_CACHE: dict[str, dict] = {}
_PROTECTED_DEPLOYMENTS_CACHE: dict[str, set[str]] = {}
_APP_OWNER_INDEX_CACHE: dict[str, dict[str, str]] = {}


def log(msg: str) -> None:
    """Print an informational log message."""
    print(f"[INFO] {msg}")


def warn(msg: str) -> None:
    """Print a warning log message to stderr."""
    print(f"[WARN] {msg}", file=sys.stderr)


def err(msg: str) -> None:
    """Print an error log message to stderr."""
    print(f"[ERROR] {msg}", file=sys.stderr)


def debug(msg: str) -> None:
    """Print a debug log when VERBOSE=true."""
    if env_bool("VERBOSE", False):
        print(f"[DEBUG] {msg}")


def fail(msg: str) -> None:
    """Log an error and terminate the process with exit code 1."""
    err(msg)
    sys.exit(1)


def reset_runtime_caches() -> None:
    """Reset all in-memory caches used by this process."""
    global _ALL_APPS_CACHE

    _DEPLOYMENTS_CACHE.clear()
    _DEPLOYMENT_CACHE.clear()
    _NAMESPACE_CACHE.clear()
    _APP_CACHE.clear()
    _PROTECTED_DEPLOYMENTS_CACHE.clear()
    _APP_OWNER_INDEX_CACHE.clear()
    _ALL_APPS_CACHE = None


# Environment parsing and validation ------------------------------------------------------------
def env_str(name: str, default: str | None = None) -> str:
    """Read a string environment variable, optionally with default."""
    value = os.getenv(name)
    if value is None:
        if default is None:
            fail(f"Missing required environment variable: {name}")
        return default
    return value


def env_bool(name: str, default: bool) -> bool:
    """Read a boolean env var represented as 'true' or 'false'."""
    raw = os.getenv(name)
    if raw is None:
        return default
    if raw not in {"true", "false"}:
        fail(f"{name} must be 'true' or 'false'")
    return raw == "true"


def env_int(name: str, default: int) -> int:
    """Read an integer environment variable."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        fail(f"{name} must be an integer")
        return default


def env_float(name: str, default: float) -> float:
    """Read a float environment variable."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        fail(f"{name} must be a number")
        return default


def run_cmd(args: list[str], capture: bool = False, dry_run: bool = False) -> str:
    """Execute a shell command and optionally capture stdout."""
    cmd_str = " ".join(args)
    if dry_run and env_bool("DRY_RUN", False):
        print(f"[DRYRUN] {cmd_str}")
        return ""

    try:
        if capture:
            return subprocess.check_output(args, stderr=subprocess.STDOUT, text=True)
        subprocess.check_call(args)
        return ""
    except subprocess.CalledProcessError as exc:
        output = exc.output.strip() if exc.output else ""
        if output:
            err(output)
        fail(f"Command failed ({exc.returncode}): {cmd_str}")
        return ""


def run_json(args: list[str]) -> dict:
    """Execute a command and parse its JSON output."""
    raw = run_cmd(args, capture=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        fail(f"Failed to parse JSON output from: {' '.join(args)}")
        return {}


def check_dependencies() -> None:
    """Validate required binaries available in runtime image."""
    if shutil.which("kubectl") is None:
        fail("Command not found: kubectl")


def validate_env() -> None:
    """Validate required/optional environment variables and accepted values."""
    _ = env_str("SCHEDULE_NAME")

    action = env_str("ACTION")
    if action not in {"shutdown", "startup"}:
        fail("ACTION must be 'shutdown' or 'startup'")

    argo_enabled = env_str("ARGO_ENABLED")
    if argo_enabled not in {"true", "false"}:
        fail("ARGO_ENABLED must be 'true' or 'false'")

    schedule_scope = env_str("SCHEDULE_SCOPE", "namespace")
    if schedule_scope not in {"namespace", "deployment"}:
        fail("SCHEDULE_SCOPE must be 'namespace' or 'deployment'")

    _ = env_str("DEFAULT_STARTUP_REPLICAS", "1")
    _ = env_bool("PROTECTED_APP_STRICT_MODE", True)
    _ = env_bool("ARGO_DISCOVERY_USE_AUTOMATIC", True)
    _ = env_bool("ARGO_DISCOVERY_USE_MANUAL", False)
    _ = env_int("ARGO_API_RETRIES", 2)
    _ = env_float("ARGO_API_RETRY_BASE_SECONDS", 0.2)
    _ = env_float("ARGO_API_RETRY_MAX_SECONDS", 1.0)

    if env_bool("ARGO_ENABLED", False):
        _ = env_str("ARGO_SERVER")
        _ = env_str("ARGO_TOKEN")
        _ = env_str("ARGO_SCHEME", "https")
        _ = env_bool("ARGO_INSECURE", False)


# Kubernetes helpers ---------------------------------------------------------------------------
def kubectl_get(
    kind: str,
    namespace: str | None = None,
    selector: str | None = None,
    name: str | None = None,
) -> dict:
    """Return a Kubernetes resource (or list) as JSON via kubectl."""
    args = ["kubectl"]
    if namespace:
        args += ["-n", namespace]
    args += ["get", kind]
    if name:
        args.append(name)
    if selector:
        args += ["-l", selector]
    args += ["-o", "json"]
    return run_json(args)


def get_target_namespaces() -> list[str]:
    """List namespaces selected by schedule label."""
    schedule = env_str("SCHEDULE_NAME")
    data = kubectl_get("ns", selector=f"offhours.platform.io/schedule={schedule}")
    return [i["metadata"]["name"] for i in data.get("items", [])]


def get_target_deployment_pairs() -> list[tuple[str, str]]:
    """List (namespace, deployment) pairs selected by schedule label."""
    schedule = env_str("SCHEDULE_NAME")
    data = run_json(
        [
            "kubectl",
            "get",
            "deploy",
            "-A",
            "-l",
            f"offhours.platform.io/schedule={schedule}",
            "-o",
            "json",
        ]
    )
    return [(i["metadata"]["namespace"], i["metadata"]["name"]) for i in data.get("items", [])]


def get_deployments(namespace: str) -> list[str]:
    """List deployment names from a namespace."""
    if namespace in _DEPLOYMENTS_CACHE:
        return _DEPLOYMENTS_CACHE[namespace]

    data = kubectl_get("deploy", namespace=namespace)
    deploys = [i["metadata"]["name"] for i in data.get("items", [])]
    _DEPLOYMENTS_CACHE[namespace] = deploys
    return deploys


def get_deployment(namespace: str, name: str) -> dict:
    """Return a single deployment object."""
    key = (namespace, name)
    if key in _DEPLOYMENT_CACHE:
        return _DEPLOYMENT_CACHE[key]

    obj = kubectl_get("deploy", namespace=namespace, name=name)
    _DEPLOYMENT_CACHE[key] = obj
    return obj


def get_namespace(namespace: str) -> dict:
    """Return a namespace object with runtime cache."""
    if namespace in _NAMESPACE_CACHE:
        return _NAMESPACE_CACHE[namespace]

    obj = kubectl_get("ns", name=namespace)
    _NAMESPACE_CACHE[namespace] = obj
    return obj


def is_protected_deployment(namespace: str, deploy: str) -> bool:
    """Check whether a deployment has offhours protection annotation."""
    obj = get_deployment(namespace, deploy)
    annotations = obj.get("metadata", {}).get("annotations", {})
    return annotations.get("offhours.platform.io/protected", "false") == "true"


def save_original_replicas(namespace: str, deploy: str) -> None:
    """Persist current replica count in annotation if not already present."""
    obj = get_deployment(namespace, deploy)
    annotations = obj.get("metadata", {}).get("annotations", {})
    existing = annotations.get("offhours.platform.io/original-replicas", "")
    if existing:
        debug(f"Original replicas annotation already exists for {namespace}/{deploy}: {existing}")
        return

    replicas = obj.get("spec", {}).get("replicas", 1)
    run_cmd(
        [
            "kubectl",
            "-n",
            namespace,
            "annotate",
            "deploy",
            deploy,
            f"offhours.platform.io/original-replicas={replicas}",
        ],
        dry_run=True,
    )
    _DEPLOYMENT_CACHE.pop((namespace, deploy), None)
    _PROTECTED_DEPLOYMENTS_CACHE.pop(namespace, None)
    debug(f"Saved replicas for {namespace}/{deploy}: {replicas}")


def get_restore_replicas(namespace: str, deploy: str) -> int:
    """Read desired startup replica count from annotation or fallback default."""
    obj = get_deployment(namespace, deploy)
    annotations = obj.get("metadata", {}).get("annotations", {})
    original = str(annotations.get("offhours.platform.io/original-replicas", ""))
    if original.isdigit():
        return int(original)
    return int(env_str("DEFAULT_STARTUP_REPLICAS", "1"))


def scale_deployment(namespace: str, deploy: str, replicas: int) -> None:
    """Scale a deployment to desired replica count."""
    run_cmd(
        [
            "kubectl",
            "-n",
            namespace,
            "scale",
            "deploy",
            deploy,
            f"--replicas={replicas}",
        ],
        dry_run=True,
    )
    _DEPLOYMENT_CACHE.pop((namespace, deploy), None)
    log(f"Deployment {namespace}/{deploy} scaled to {replicas}")


# Argo CD API helpers --------------------------------------------------------------------------
def argo_base_url() -> str:
    """Build Argo base URL from ARGO_SERVER and ARGO_SCHEME."""
    server = env_str("ARGO_SERVER")
    if server.startswith("http://") or server.startswith("https://"):
        return server.rstrip("/")
    scheme = env_str("ARGO_SCHEME", "https")
    return f"{scheme}://{server}".rstrip("/")


def argo_ssl_context() -> ssl.SSLContext | None:
    """Return SSL context, optionally skipping TLS validation when enabled."""
    if not argo_base_url().startswith("https://"):
        return None
    if not env_bool("ARGO_INSECURE", False):
        return None
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def argo_request(method: str, path: str, body: dict | None = None, mutate: bool = False) -> dict:
    """Call Argo API with retry/backoff for transient failures.

    Retry policy:
    - HTTP 429
    - HTTP 5xx
    - URL/network failures
    """
    url = f"{argo_base_url()}{path}"
    payload = None
    if body is not None:
        payload = json.dumps(body).encode("utf-8")

    if mutate and env_bool("DRY_RUN", False):
        preview = json.dumps(body) if body is not None else ""
        print(f"[DRYRUN] ARGO {method} {url} {preview}".strip())
        return {}

    req = request.Request(url=url, data=payload, method=method)
    req.add_header("Authorization", f"Bearer {env_str('ARGO_TOKEN')}")
    req.add_header("Content-Type", "application/json")

    retries = env_int("ARGO_API_RETRIES", 2)
    base = env_float("ARGO_API_RETRY_BASE_SECONDS", 0.2)
    backoff_max = env_float("ARGO_API_RETRY_MAX_SECONDS", 1.0)
    max_attempts = max(1, retries + 1)

    for attempt in range(1, max_attempts + 1):
        try:
            with request.urlopen(req, context=argo_ssl_context(), timeout=20) as resp:
                raw = resp.read().decode("utf-8").strip()
                if not raw:
                    return {}
                return json.loads(raw)
        except error.HTTPError as http_err:
            body_preview = http_err.read().decode("utf-8", errors="ignore")
            retryable = http_err.code == 429 or 500 <= http_err.code <= 599

            if retryable and attempt < max_attempts:
                sleep_for = min(backoff_max, base * (2 ** (attempt - 1)))
                warn(
                    f"Argo API transient HTTP {http_err.code} on {method} {path}. "
                    f"Retrying in {sleep_for:.2f}s (attempt {attempt}/{max_attempts})."
                )
                time.sleep(sleep_for)
                continue

            err(f"Argo API HTTP {http_err.code}: {body_preview}")
            fail(f"Argo API request failed: {method} {path}")
        except (error.URLError, TimeoutError) as net_err:
            if attempt < max_attempts:
                sleep_for = min(backoff_max, base * (2 ** (attempt - 1)))
                warn(
                    f"Argo API network error on {method} {path}: {net_err}. "
                    f"Retrying in {sleep_for:.2f}s (attempt {attempt}/{max_attempts})."
                )
                time.sleep(sleep_for)
                continue
            fail(f"Argo API network request failed: {method} {path}: {net_err}")
        except Exception as exc:
            fail(f"Argo API request failed: {method} {path}: {exc}")

    return {}


def get_all_applications() -> list[dict]:
    """List Argo CD applications."""
    global _ALL_APPS_CACHE
    if _ALL_APPS_CACHE is not None:
        return _ALL_APPS_CACHE

    data = argo_request("GET", "/api/v1/applications")
    _ALL_APPS_CACHE = data.get("items", []) if isinstance(data, dict) else []
    return _ALL_APPS_CACHE


def get_app(app_name: str) -> dict:
    """Get full Argo application object by name."""
    if app_name in _APP_CACHE:
        return _APP_CACHE[app_name]

    quoted = parse.quote(app_name, safe="")
    app = argo_request("GET", f"/api/v1/applications/{quoted}")
    _APP_CACHE[app_name] = app
    return app


def parse_argopp_values(value: str) -> list[str]:
    """Parse comma-separated app list used by offhours.platform.io/argopp."""
    out = []
    for item in value.split(","):
        clean = item.strip()
        if clean:
            out.append(clean)
    return out


def resolve_app_names(candidates: list[str], all_apps: list[dict]) -> set[str]:
    """Normalize and validate candidate app references against Argo app inventory."""
    existing = {a.get("metadata", {}).get("name", "") for a in all_apps}
    refs: set[str] = set()
    for candidate in candidates:
        if not candidate:
            continue
        name = candidate.split("/", 1)[-1]
        if name in existing:
            refs.add(name)
    return refs


# Argo app discovery ---------------------------------------------------------------------------
def get_argocd_apps_from_namespace(namespace: str) -> set[str]:
    """Discover Argo apps for a namespace.

    Discovery precedence:
    1) Manual override (`offhours.platform.io/argopp`) when manual mode is enabled.
    2) Automatic chain (instance -> tracking-id -> destination namespace fallback)
       when automatic mode is enabled.
    """
    all_apps = get_all_applications()
    use_automatic = env_bool("ARGO_DISCOVERY_USE_AUTOMATIC", True)
    use_manual = env_bool("ARGO_DISCOVERY_USE_MANUAL", False)

    # Priority 1: explicit manual namespace override
    if use_manual:
        ns_obj = get_namespace(namespace)
        labels = ns_obj.get("metadata", {}).get("labels", {})
        annotations = ns_obj.get("metadata", {}).get("annotations", {})
        explicit = labels.get("offhours.platform.io/argopp") or annotations.get(
            "offhours.platform.io/argopp"
        )
        if explicit:
            debug(
                "Namespace "
                f"{namespace} using explicit Argo app mapping via "
                "offhours.platform.io/argopp"
            )
            refs = resolve_app_names(parse_argopp_values(explicit), all_apps)
            if refs:
                return refs

    # Priority 2: automatic discovery chain
    if not use_automatic:
        return set()

    # 2.1 deployment metadata (instance/tracking-id)
    discovered: set[str] = set()
    for deploy in get_deployments(namespace):
        obj = get_deployment(namespace, deploy)
        d_labels = obj.get("metadata", {}).get("labels", {})
        d_annotations = obj.get("metadata", {}).get("annotations", {})

        instance = d_labels.get("argocd.argoproj.io/instance")
        if instance:
            discovered.add(instance)

        tracking = d_annotations.get("argocd.argoproj.io/tracking-id", "")
        if tracking:
            discovered.add(tracking.split(":", 1)[0])

    refs = resolve_app_names(sorted(discovered), all_apps)
    if refs:
        return refs

    # 2.2 destination namespace fallback
    warn(
        f"No Argo CD app metadata found in deployments for namespace {namespace}. "
        "Falling back to Argo API destination namespace."
    )
    fallback = set()
    for app in all_apps:
        dest_ns = app.get("spec", {}).get("destination", {}).get("namespace", "")
        if dest_ns == namespace:
            name = app.get("metadata", {}).get("name", "")
            if name:
                fallback.add(name)
    return fallback


def get_protected_deployments(namespace: str) -> set[str]:
    """Return protected deployments from a namespace with runtime cache."""
    if namespace in _PROTECTED_DEPLOYMENTS_CACHE:
        return _PROTECTED_DEPLOYMENTS_CACHE[namespace]

    protected = set()
    for deploy in get_deployments(namespace):
        obj = get_deployment(namespace, deploy)
        annotations = obj.get("metadata", {}).get("annotations", {})
        if annotations.get("offhours.platform.io/protected", "false") == "true":
            protected.add(deploy)

    _PROTECTED_DEPLOYMENTS_CACHE[namespace] = protected
    return protected


def get_app_owner_index(namespace: str) -> dict[str, str]:
    """Return a deployment->app owner index for one namespace.

    This index is used to avoid repeatedly scanning app resources when resolving
    owners for many deployments in the same namespace.
    """
    if namespace in _APP_OWNER_INDEX_CACHE:
        return _APP_OWNER_INDEX_CACHE[namespace]

    index: dict[str, str] = {}
    for app in sorted(get_argocd_apps_from_namespace(namespace)):
        app_obj = get_app(app)
        for resource in app_obj.get("status", {}).get("resources", []):
            if resource.get("kind") != "Deployment":
                continue
            if resource.get("namespace") != namespace:
                continue
            dep_name = resource.get("name", "")
            if dep_name and dep_name not in index:
                index[dep_name] = app

    _APP_OWNER_INDEX_CACHE[namespace] = index
    return index


def app_manages_deployment(app_name: str, deploy_ns: str, deploy_name: str) -> bool:
    """Check if an Argo application owns a specific deployment."""
    app = get_app(app_name)
    for resource in app.get("status", {}).get("resources", []):
        if (
            resource.get("kind") == "Deployment"
            and resource.get("namespace") == deploy_ns
            and resource.get("name") == deploy_name
        ):
            return True
    return False


def app_has_protected_deployment(app_name: str, namespace: str) -> bool:
    """Check whether an app has any protected deployment in namespace."""
    protected = get_protected_deployments(namespace)
    if not protected:
        return False

    app = get_app(app_name)
    for resource in app.get("status", {}).get("resources", []):
        if resource.get("kind") == "Deployment" and resource.get("namespace") == namespace:
            if resource.get("name", "") in protected:
                return True
    return False


def get_argocd_app_for_deployment(namespace: str, deploy: str) -> str | None:
    """Resolve Argo app owner for a deployment.

    Uses fast paths first (manual owner index, then direct automatic metadata),
    and only then falls back to the namespace owner index scan.
    """
    obj = get_deployment(namespace, deploy)
    labels = obj.get("metadata", {}).get("labels", {})
    annotations = obj.get("metadata", {}).get("annotations", {})

    if env_bool("ARGO_DISCOVERY_USE_MANUAL", False):
        owner = get_app_owner_index(namespace).get(deploy)
        if owner:
            return owner

    use_automatic = env_bool("ARGO_DISCOVERY_USE_AUTOMATIC", True)
    all_apps = get_all_applications() if use_automatic else []

    if use_automatic:
        instance = labels.get("argocd.argoproj.io/instance")
        if instance:
            refs = resolve_app_names([instance], all_apps)
            if refs:
                return sorted(refs)[0]

        tracking = annotations.get("argocd.argoproj.io/tracking-id", "")
        if tracking:
            refs = resolve_app_names([tracking.split(":", 1)[0]], all_apps)
            if refs:
                return sorted(refs)[0]

    owner = get_app_owner_index(namespace).get(deploy)
    if owner:
        return owner

    return None


def argo_pause_app(app_name: str) -> None:
    """Disable automated sync for an Argo application."""
    quoted = parse.quote(app_name, safe="")
    argo_request(
        "PATCH",
        f"/api/v1/applications/{quoted}",
        {
            "patchType": "merge",
            "patch": json.dumps({"spec": {"syncPolicy": None}}),
        },
        mutate=True,
    )
    log(f"Argo CD application paused: {app_name}")


def argo_resume_and_sync_app(app_name: str) -> None:
    """Enable automated sync and trigger sync for an Argo application."""
    quoted = parse.quote(app_name, safe="")
    argo_request(
        "PATCH",
        f"/api/v1/applications/{quoted}",
        {
            "patchType": "merge",
            "patch": json.dumps({"spec": {"syncPolicy": {"automated": {}}}}),
        },
        mutate=True,
    )
    argo_request(
        "POST",
        f"/api/v1/applications/{quoted}/sync",
        {"prune": False, "dryRun": False},
        mutate=True,
    )
    log(f"Argo CD application resumed and synced: {app_name}")


# Action handlers ------------------------------------------------------------------------------
def handle_shutdown_namespace(namespace: str) -> None:
    """Execute shutdown flow for namespace scope.

    In strict mode, apps with any protected deployment are skipped entirely.
    """
    log(f"Processing namespace for shutdown: {namespace}")

    strict_blocked_apps: set[str] = set()
    apps: set[str] = set()

    if env_bool("ARGO_ENABLED", False):
        apps = get_argocd_apps_from_namespace(namespace)
        if not apps:
            err(
                "No Argo CD application found for namespace "
                f"{namespace}. Continuing with namespace processing."
            )
            warn("Deployments may be reconciled back by Argo CD if sync was not paused.")

        if env_bool("PROTECTED_APP_STRICT_MODE", True):
            for app in sorted(apps):
                if app_has_protected_deployment(app, namespace):
                    strict_blocked_apps.add(app)
                    log(
                        f"Strict mode: app {app} has protected deployment(s), "
                        "app will not be paused and its deployments will not be scaled"
                    )

        for app in sorted(apps):
            if env_bool("PROTECTED_APP_STRICT_MODE", True) and app in strict_blocked_apps:
                log(f"Strict mode: skipping sync pause for app {app}")
                continue
            argo_pause_app(app)

    for deploy in get_deployments(namespace):
        if is_protected_deployment(namespace, deploy):
            log(f"Skipping protected deployment: {namespace}/{deploy}")
            continue

        if env_bool("ARGO_ENABLED", False) and env_bool("PROTECTED_APP_STRICT_MODE", True):
            owner = get_argocd_app_for_deployment(namespace, deploy)
            if owner and owner in strict_blocked_apps:
                log(
                    f"Strict mode: skipping deployment {namespace}/{deploy} "
                    f"because app {owner} has protected deployment(s)"
                )
                continue

        save_original_replicas(namespace, deploy)
        scale_deployment(namespace, deploy, 0)


def handle_startup_namespace(namespace: str) -> None:
    """Execute startup flow for namespace scope.

    In strict mode, apps with protected deployments are not resumed/synced.
    """
    log(f"Processing namespace for startup: {namespace}")

    if env_bool("ARGO_ENABLED", False):
        apps = get_argocd_apps_from_namespace(namespace)
        if not apps:
            err(
                "No Argo CD application found for namespace "
                f"{namespace}. Skipping Argo startup actions and continuing."
            )
            return

        strict_blocked_apps: set[str] = set()
        if env_bool("PROTECTED_APP_STRICT_MODE", True):
            for app in sorted(apps):
                if app_has_protected_deployment(app, namespace):
                    strict_blocked_apps.add(app)
                    log(
                        f"Strict mode: app {app} has protected deployment(s), "
                        "startup will not resume/sync this app"
                    )

        for app in sorted(apps):
            if env_bool("PROTECTED_APP_STRICT_MODE", True) and app in strict_blocked_apps:
                log(f"Strict mode: skipping startup resume/sync for app {app}")
                continue
            argo_resume_and_sync_app(app)
        return

    for deploy in get_deployments(namespace):
        if is_protected_deployment(namespace, deploy):
            log(f"Skipping protected deployment: {namespace}/{deploy}")
            continue

        replicas = get_restore_replicas(namespace, deploy)
        scale_deployment(namespace, deploy, replicas)


def handle_shutdown_deployment_scope() -> None:
    """Execute shutdown flow for deployment scope."""
    pairs = get_target_deployment_pairs()
    if not pairs:
        warn(f"No deployments found for schedule: {env_str('SCHEDULE_NAME')}")
        return

    app_keys: set[tuple[str, str]] = set()
    strict_blocked_keys: set[tuple[str, str]] = set()

    if env_bool("ARGO_ENABLED", False):
        for namespace, deploy in pairs:
            owner = get_argocd_app_for_deployment(namespace, deploy)
            if owner is None:
                err(
                    f"No Argo CD application found for deployment {namespace}/{deploy}. Continuing."
                )
                continue
            app_keys.add((namespace, owner))

        if env_bool("PROTECTED_APP_STRICT_MODE", True):
            for namespace, app in sorted(app_keys):
                if app_has_protected_deployment(app, namespace):
                    strict_blocked_keys.add((namespace, app))
                    log(
                        "Strict mode: app "
                        f"{app} in namespace {namespace} has protected deployment(s), "
                        "app will not be paused and its deployments will not be scaled"
                    )

        for namespace, app in sorted(app_keys):
            if (
                env_bool("PROTECTED_APP_STRICT_MODE", True)
                and (namespace, app) in strict_blocked_keys
            ):
                log(f"Strict mode: skipping sync pause for app {app} in namespace {namespace}")
                continue
            argo_pause_app(app)

    for namespace, deploy in pairs:
        if is_protected_deployment(namespace, deploy):
            log(f"Skipping protected deployment: {namespace}/{deploy}")
            continue

        if env_bool("ARGO_ENABLED", False) and env_bool("PROTECTED_APP_STRICT_MODE", True):
            owner = get_argocd_app_for_deployment(namespace, deploy)
            if owner and (namespace, owner) in strict_blocked_keys:
                log(
                    f"Strict mode: skipping deployment {namespace}/{deploy} "
                    f"because app {owner} has protected deployment(s)"
                )
                continue

        save_original_replicas(namespace, deploy)
        scale_deployment(namespace, deploy, 0)


def handle_startup_deployment_scope() -> None:
    """Execute startup flow for deployment scope.

    In Argo mode, resume/sync app owners for selected deployments while still
    enforcing strict-mode protection rules.
    """
    pairs = get_target_deployment_pairs()
    if not pairs:
        warn(f"No deployments found for schedule: {env_str('SCHEDULE_NAME')}")
        return

    if env_bool("ARGO_ENABLED", False):
        app_keys: set[tuple[str, str]] = set()
        strict_blocked_keys: set[tuple[str, str]] = set()
        for namespace, deploy in pairs:
            owner = get_argocd_app_for_deployment(namespace, deploy)
            if owner is None:
                err(
                    f"No Argo CD application found for deployment {namespace}/{deploy}. Continuing."
                )
                continue
            app_keys.add((namespace, owner))

        if env_bool("PROTECTED_APP_STRICT_MODE", True):
            for namespace, app in sorted(app_keys):
                if app_has_protected_deployment(app, namespace):
                    strict_blocked_keys.add((namespace, app))
                    log(
                        "Strict mode: app "
                        f"{app} in namespace {namespace} has protected deployment(s), "
                        "startup will not resume/sync this app"
                    )

        for namespace, app in sorted(app_keys):
            if (
                env_bool("PROTECTED_APP_STRICT_MODE", True)
                and (namespace, app) in strict_blocked_keys
            ):
                log(f"Strict mode: skipping startup resume/sync for app {app} in namespace {namespace}")
                continue
            argo_resume_and_sync_app(app)
        return

    for namespace, deploy in pairs:
        if is_protected_deployment(namespace, deploy):
            log(f"Skipping protected deployment: {namespace}/{deploy}")
            continue
        replicas = get_restore_replicas(namespace, deploy)
        scale_deployment(namespace, deploy, replicas)


def main() -> None:
    """Entrypoint: validate config, select scope and run action."""
    reset_runtime_caches()
    validate_env()
    check_dependencies()

    log(f"Starting {SCRIPT_NAME}")
    log(
        "SCHEDULE_NAME={s} SCHEDULE_SCOPE={ss} ACTION={a} ARGO_ENABLED={ae} "
        "DRY_RUN={dr} PROTECTED_APP_STRICT_MODE={ps}".format(
            s=env_str("SCHEDULE_NAME"),
            ss=env_str("SCHEDULE_SCOPE", "namespace"),
            a=env_str("ACTION"),
            ae=env_str("ARGO_ENABLED"),
            dr=os.getenv("DRY_RUN", "false"),
            ps=os.getenv("PROTECTED_APP_STRICT_MODE", "true"),
        )
    )

    if env_str("SCHEDULE_SCOPE", "namespace") == "namespace":
        target_namespaces = get_target_namespaces()
        if not target_namespaces:
            warn(f"No namespaces found for schedule: {env_str('SCHEDULE_NAME')}")
        for namespace in target_namespaces:
            if env_str("ACTION") == "shutdown":
                handle_shutdown_namespace(namespace)
            else:
                handle_startup_namespace(namespace)
    else:
        if env_str("ACTION") == "shutdown":
            handle_shutdown_deployment_scope()
        else:
            handle_startup_deployment_scope()

    log(f"Finished {SCRIPT_NAME}")


if __name__ == "__main__":
    main()
