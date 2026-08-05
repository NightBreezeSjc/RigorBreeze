"""State, configuration, persistence, and shared primitives for RigorBreeze."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
import tomllib
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import flow_parallel

VERSION = 4
TOOL_VERSION = "0.8.1"
SPEC_DIR = "spec"
CONFIG_NAME = "rigorbreeze.toml"
MODES = ("advisory", "enforced")
AUTOMATION_LEVELS = ("manual", "commit", "push", "merge", "release")
STANDARD_CHECK_IDS = (
    "format",
    "lint",
    "typecheck",
    "unit",
    "integration",
    "e2e",
    "contract",
    "secret",
    "dependency",
    "license",
    "sbom",
    "migration",
    "build",
    "playwright",
    "acceptance",
)
PLACEHOLDERS = ("TODO", "TBD", "待填写", "待定义")
REQUIRED_TASK_SECTIONS = (
    "## Authoritative inputs",
    "## Allowed scope",
    "## Forbidden scope",
    "## Acceptance criteria",
    "## Test seams",
    "## Verification commands",
)
SECRET_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "credentials.json",
    "secrets.json",
    "id_rsa",
    "id_ed25519",
}
SECRET_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
DEPENDENCY_NAMES = {
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "pyproject.toml",
    "requirements.txt",
    "poetry.lock",
    "uv.lock",
    "go.mod",
    "go.sum",
    "cargo.toml",
    "cargo.lock",
}
MIGRATION_PARTS = {
    "migration",
    "migrations",
    "alembic",
    "flyway",
    "liquibase",
    "versions",
}
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "target",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "artifacts",
    "reports",
}
AGENTS_START = "<!-- rigorbreeze:start -->"
AGENTS_END = "<!-- rigorbreeze:end -->"
LOCK_NAME = ".flow.lock"
RUNNER_MARKER = '"""Deterministic gates for RigorBreeze."""'
REPOSITORY_WRAPPER_MARKER = (
    '"""Repository-local entry point for the bundled RigorBreeze Skill."""'
)
DESTRUCTIVE_MIGRATION_PATTERN = re.compile(
    r"(?i)\b(drop\s+(table|database|schema)|truncate\s+table|delete\s+from\s+\S+\s*;)"
)
RELEASE_GOVERNANCE_FIELDS = {
    "featureFlag",
    "canary",
    "observationWindow",
    "slo",
    "alertOwner",
    "rollback",
    "businessMetrics",
}
MIGRATION_EVIDENCE_FIELDS = {
    "rehearsal",
    "dataAssertions",
    "backup",
    "restore",
    "strategy",
}
SECURITY_EVIDENCE_FIELDS = {
    "secretScan",
    "sca",
    "license",
    "sbom",
    "owner",
}


class FlowError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    temporary.replace(path)


def write_json(path: Path, value: dict[str, Any]) -> None:
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FlowError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise FlowError(f"invalid JSON: {path}: {exc}") from exc


def spec_root(root: Path) -> Path:
    return root / SPEC_DIR


def state_path(root: Path) -> Path:
    return flow_parallel.worktree_state_path(root, spec_root(root) / "state.json")


def legacy_state_path(root: Path) -> Path:
    return spec_root(root) / "state.json"


def task_path(root: Path, task_id: str) -> Path:
    return spec_root(root) / "changes" / f"{task_id}.md"


def evidence_path(root: Path, task_id: str) -> Path:
    return spec_root(root) / "evidence" / f"{task_id}.json"


def initial_state() -> dict[str, Any]:
    return {
        "workflowVersion": VERSION,
        "phase": "baseline",
        "activeTask": None,
        "approvals": {
            "task": {"valid": False, "digest": None, "approvedAt": None},
            "dependencies": [],
            "migrations": [],
            "overlaps": [],
        },
        "red": None,
        "verification": None,
        "warnings": [],
        "lastClosed": None,
        "updatedAt": now_iso(),
    }


def empty_evidence(task_id: str) -> dict[str, Any]:
    return {
        "workflowVersion": VERSION,
        "taskId": task_id,
        "baseline": None,
        "red": [],
        "verifications": [],
        "checkRuns": [],
        "tddChain": [],
        "artifacts": [],
        "acceptance": [],
        "release": [],
        "automation": [],
        "practice": {"confirmation": None, "events": []},
        "closure": None,
        "verification": None,
    }


def config_template() -> str:
    return """version = 4

[policy]
local_mode = "advisory"
test_paths = ["tests", "test", "__tests__", "src/test"]
source_paths = ["src", "app", "lib"]
migration_paths = ["migration", "migrations", "alembic", "flyway", "liquibase", "versions"]

[profiles]
affected = ["lint", "unit", "secret"]
full = ["lint", "unit", "secret", "build"]

[parallel]
base_branch = ""
worktree_root = ""

[automation]
level = "manual"
remote = "origin"
protected_branches = ["main", "master"]
commit_message = "{task_id}: {title}"

# merge_check_command and merge_command must call the configured GitHub/GitLab
# provider. release_check_command and release_command are likewise project
# adapters. Commands are argv arrays; no shell interpolation is used.
#
# merge_check_command = ["gh", "pr", "checks", "{branch}", "--required"]
# merge_command = ["gh", "pr", "merge", "{branch}", "--auto", "--squash"]
# release_check_command = ["./scripts/release-check", "{task_id}", "{head}"]
# release_command = ["./scripts/release", "{task_id}", "{head}", "{artifact_sha256}", "{idempotency_key}"]

# Keep only checks this project actually uses. Add conditional checks such as
# typecheck, integration, e2e, dependency, migration, or playwright when they
# protect a real project capability. Every ID listed in a profile must have a
# command; missing profile checks warn locally and fail in enforced mode.
#
# [[checks]]
# id = "unit"
# command = ["python3", "-m", "unittest", "discover", "-v"]
# timeout = 900
# risks = ["L0", "L1", "L2", "Emergency"]
# report = "reports/unit.json"
# artifacts = []
"""


def task_template(task_id: str, title: str, risk: str) -> str:
    return f"""# {task_id}: {title}

Risk: {risk}

Depends-On: none

Runtime-Claims: none

Operational-Modes: N/A - no conditional runtime behavior

## Authoritative inputs
- User outcome: TODO
- Current behavior and evidence: TODO
- Business and architecture path: TODO
- Invariants and source of truth: TODO
- Requirement/design/API version: TODO
- Unresolved outcome-changing ambiguity: TODO

## Allowed scope
- TODO

## Forbidden scope
- TODO

## Acceptance criteria
- REQ-001: TODO

## Test seams
- Seam: TODO
- Independent oracle: TODO

## Verification commands
- TODO

## Conditional risks
- Runtime/UI: N/A unless applicable
- Security/migration/release: N/A unless applicable
- Stop conditions: scope or acceptance changes
"""


def index_template() -> str:
    return """# Production Spec Index

This tree keeps one human-authored Markdown file per active change. Machine state and evidence are JSON.
Project quality policy and executable profiles live in `../rigorbreeze.toml`.

Authority order:

1. Approved business requirements and design source
2. `changes/<TASK-ID>.md`
3. API/data/security contracts
4. Automated tests and runtime evidence
5. Code and artifacts
6. `archive/` history

Do not copy requirement bodies into multiple files. Move a completed task to `archive/`; do not duplicate it.
"""


def agents_block() -> str:
    return f"""{AGENTS_START}
## RigorBreeze

Before every non-trivial product-code write, including a follow-up after context compaction or while another workflow skill is active, invoke `$rigorbreeze`, inspect bundled-runner status and the real base-branch `workflowBaseline`, and require an approved task plus a successful window claim. Read `rigorbreeze.toml`, `spec/index.md`, and the active contract.
Complete incomplete prompts from evidence before approval: recover project facts from requirements, code, tests, Git and runtime state; ask only for outcome-changing intent that cannot be recovered; state safe defaults instead of hiding assumptions. Record the compact result in Authoritative inputs rather than creating another context document.
One worktree may own only one active writing task. Use `new --worktree auto` for parallel tasks and `status --all --json` for the project view. Declare exclusive ports, services, processes, apps, or environments in `Runtime-Claims`; worktrees do not isolate them. Complex DAGs are proposed once, then represented only by `Depends-On`.
Local mode is advisory; CI, L2, merge, and release use enforced profiles. L0 closes after configured verification; L1/L2 require current full verification, applicable acceptance, review, and retrospective confirmation. Immutable artifacts and release governance are required only when release is actually requested.
Use `archive --outcome abandoned --reason <reason>` for a clean cancelled task; use `reconciled` only for proven externally integrated history. Archive before guarded delivery and preserve branches. Conditional L2 integrations map enabled/disabled/unavailable behavior in `Operational-Modes`, and L2 remote release requires an operation plan with one safe recovery entry.
Git automation defaults to manual and never increases during an upgrade. A current-message request may authorize one guarded commit/push; provider merge and release require standing project configuration.
Before any external write, report the observed current state, already completed steps, immutable identifiers, remaining action and stop conditions. Never repeat a completed operation from a stale plan or chat summary.
{AGENTS_END}"""


def ensure_agents(root: Path) -> None:
    path = root / "AGENTS.md"
    existing = (
        path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    )
    block = agents_block()
    pattern = re.compile(re.escape(AGENTS_START) + r".*?" + re.escape(AGENTS_END), re.S)
    if pattern.search(existing):
        updated = pattern.sub(block, existing)
    else:
        updated = (
            existing.rstrip() + ("\n\n" if existing.strip() else "") + block + "\n"
        )
    if updated != existing:
        atomic_write(path, updated)


def upgrade_state(state: dict[str, Any]) -> dict[str, Any]:
    version = int(state.get("workflowVersion", 1))
    if version > VERSION:
        raise FlowError(
            f"state schema {version} is newer than supported schema {VERSION}"
        )
    state.setdefault("warnings", [])
    state.setdefault("verification", None)
    state.setdefault("lastClosed", None)
    approvals = state.setdefault("approvals", {})
    approvals.setdefault("task", {"valid": False, "digest": None, "approvedAt": None})
    approvals.setdefault("dependencies", [])
    approvals.setdefault("migrations", [])
    approvals.setdefault("overlaps", [])
    active = state.get("activeTask")
    if active:
        active.setdefault("dependsOn", [])
        active.setdefault("baseBranch", None)
        active.setdefault("baseSha", None)
        active.setdefault("runtimeClaims", [])
        active.setdefault("operationalModes", {})
    state["workflowVersion"] = VERSION
    phase_map = {
        "drafting": "draft",
        "ready-to-release": "verified",
        "closed": "archived",
    }
    state["phase"] = phase_map.get(state.get("phase"), state.get("phase", "baseline"))
    return state


def upgrade_evidence(evidence: dict[str, Any], task_id: str) -> dict[str, Any]:
    version = int(evidence.get("workflowVersion", 1))
    if version > VERSION:
        raise FlowError(
            f"evidence schema {version} is newer than supported schema {VERSION}"
        )
    defaults = empty_evidence(task_id)
    for key, value in defaults.items():
        evidence.setdefault(key, value)
    practice = evidence.setdefault("practice", {})
    practice.setdefault("confirmation", None)
    practice.setdefault("events", [])
    evidence["workflowVersion"] = VERSION
    evidence["taskId"] = task_id
    return evidence


def upgrade_persisted_data(root: Path) -> None:
    state_file = state_path(root)
    if state_file.exists():
        original = read_json(state_file)
        before = json.dumps(original, sort_keys=True)
        upgraded = upgrade_state(original)
        if json.dumps(upgraded, sort_keys=True) != before:
            write_json(state_file, upgraded)
    evidence_dir = spec_root(root) / "evidence"
    if evidence_dir.is_dir():
        for path in sorted(evidence_dir.glob("*.json")):
            original = read_json(path)
            before = json.dumps(original, sort_keys=True)
            upgraded = upgrade_evidence(original, path.stem)
            if json.dumps(upgraded, sort_keys=True) != before:
                write_json(path, upgraded)


def migrate_legacy_state(root: Path, *, remove_untracked: bool = False) -> list[str]:
    """Copy the legacy tracked-tree state into Git-private storage.

    Removal is deliberately conservative: only an untracked byte-for-byte
    equivalent legacy file may be removed by init/repair.
    """

    private = state_path(root)
    legacy = legacy_state_path(root)
    warnings: list[str] = []
    if private == legacy or not legacy.is_file():
        return warnings
    legacy_value = upgrade_state(read_json(legacy))
    if not private.exists():
        write_json(private, legacy_value)
    private_value = upgrade_state(read_json(private))
    if json.dumps(private_value, sort_keys=True) != json.dumps(
        legacy_value, sort_keys=True
    ):
        warnings.append("legacy spec/state.json differs from Git-private state")
        return warnings
    tracked = git(root, "ls-files", "--error-unmatch", "--", "spec/state.json")
    if tracked.returncode == 0:
        warnings.append("tracked legacy spec/state.json requires manual removal")
    elif remove_untracked:
        legacy.unlink()
    return warnings


def clean_managed_bytecode(root: Path) -> list[str]:
    """Delete only RigorBreeze helper bytecode and report unknown cache entries."""

    retained: list[str] = []
    managed_prefixes = (
        "rigorbreeze.",
        "flow.",
        "flow_state.",
        "flow_policy.",
        "flow_parallel.",
        "flow_automation.",
    )
    for cache in (root / "scripts" / "__pycache__",):
        if not cache.is_dir():
            continue
        for path in sorted(cache.iterdir()):
            if (
                path.is_file()
                and path.suffix == ".pyc"
                and path.name.startswith(managed_prefixes)
            ):
                path.unlink()
            else:
                retained.append(str(path.relative_to(root)).replace("\\", "/"))
        try:
            cache.rmdir()
        except OSError:
            pass
    return retained


def load_state(root: Path) -> dict[str, Any]:
    migrate_legacy_state(root)
    state = read_json(state_path(root))
    return upgrade_state(state)


def load_evidence(root: Path, task_id: str) -> dict[str, Any]:
    path = evidence_path(root, task_id)
    if not path.exists():
        return empty_evidence(task_id)
    return upgrade_evidence(read_json(path), task_id)


def save_evidence(root: Path, task_id: str, evidence: dict[str, Any]) -> None:
    write_json(evidence_path(root, task_id), evidence)


def config_path(root: Path) -> Path:
    return root / CONFIG_NAME


def load_config(root: Path) -> dict[str, Any]:
    path = config_path(root)
    try:
        with path.open("rb") as handle:
            config = tomllib.load(handle)
    except FileNotFoundError as exc:
        raise FlowError(f"missing workflow configuration: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise FlowError(f"invalid TOML: {path}: {exc}") from exc
    config_version = config.get("version")
    if config_version not in (2, 3, VERSION):
        raise FlowError(f"{CONFIG_NAME} must declare version = 2, 3, or {VERSION}")
    policy = config.setdefault("policy", {})
    local_mode = policy.setdefault("local_mode", "advisory")
    if local_mode not in MODES:
        raise FlowError("policy.local_mode must be advisory or enforced")
    profiles = config.setdefault("profiles", {})
    parallel = config.setdefault("parallel", {})
    for key in ("base_branch", "worktree_root"):
        value = parallel.setdefault(key, "")
        if not isinstance(value, str):
            raise FlowError(f"parallel.{key} must be a string")
    automation = config.setdefault("automation", {})
    level = automation.setdefault("level", "manual")
    if level not in AUTOMATION_LEVELS:
        raise FlowError(
            "automation.level must be manual, commit, push, merge, or release"
        )
    protected = automation.setdefault("protected_branches", ["main", "master"])
    if not isinstance(protected, list) or not all(
        isinstance(item, str) and item for item in protected
    ):
        raise FlowError("automation.protected_branches must be a string array")
    for key in (
        "merge_check_command",
        "merge_command",
        "release_check_command",
        "release_command",
    ):
        command = automation.get(key)
        if command is not None and (
            not isinstance(command, list)
            or not command
            or not all(isinstance(part, str) for part in command)
        ):
            raise FlowError(f"automation.{key} must be a non-empty argv array")
    checks: dict[str, dict[str, Any]] = {}
    for item in config.get("checks", []):
        check_id = item.get("id")
        if not isinstance(check_id, str) or check_id not in STANDARD_CHECK_IDS:
            raise FlowError(f"unknown standard check ID: {check_id!r}")
        if check_id in checks:
            raise FlowError(f"duplicate check configuration: {check_id}")
        command = item.get("command")
        if (
            not isinstance(command, list)
            or not command
            or not all(isinstance(part, str) for part in command)
        ):
            raise FlowError(f"check {check_id} requires a non-empty argv command")
        timeout = item.get("timeout", 900)
        if not isinstance(timeout, int) or timeout <= 0:
            raise FlowError(f"check {check_id} timeout must be a positive integer")
        cwd = item.get("cwd", ".")
        if not isinstance(cwd, str):
            raise FlowError(f"check {check_id} cwd must be a relative path")
        resolved_cwd = resolve_project_path(root, cwd, f"check {check_id} cwd")
        if not resolved_cwd.is_dir():
            raise FlowError(f"check {check_id} cwd is missing: {cwd}")
        environment = item.get("env", {})
        if not isinstance(environment, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in environment.items()
        ):
            raise FlowError(f"check {check_id} env must contain string key/value pairs")
        secret_env_keys = [
            key
            for key in environment
            if re.search(r"(?i)(secret|password|token|credential|private.?key)", key)
        ]
        if secret_env_keys:
            raise FlowError(
                f"check {check_id} must not store secret environment values in TOML: "
                + ", ".join(secret_env_keys)
            )
        checks[check_id] = item
    config["_checks"] = checks
    for profile in ("affected", "full"):
        ids = profiles.get(profile, [])
        if not isinstance(ids, list) or not all(isinstance(item, str) for item in ids):
            raise FlowError(f"profiles.{profile} must be an array of check IDs")
        unknown = [item for item in ids if item not in STANDARD_CHECK_IDS]
        if unknown:
            raise FlowError(
                f"profiles.{profile} contains unknown checks: {', '.join(unknown)}"
            )
    return config


def config_digest(root: Path) -> str:
    return sha256_bytes(config_path(root).read_bytes())


def effective_mode(
    root: Path,
    requested: str | None,
    state: dict[str, Any] | None = None,
    gate: str | None = None,
) -> str:
    config = load_config(root)
    mode = requested or config["policy"].get("local_mode", "advisory")
    risk = (
        state.get("activeTask", {}).get("risk")
        if state and state.get("activeTask")
        else None
    )
    if risk == "L2" or gate in {"merge", "release"}:
        return "enforced"
    return mode


def parse_fields(values: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for value in values:
        key, separator, content = value.partition("=")
        if not separator or not key or not content:
            raise FlowError(f"evidence field must look like key=value: {value}")
        if re.fullmatch(
            r"(?i)(secret|password|token|credential|private.?key|api.?key)",
            key,
        ):
            raise FlowError(f"evidence field must not contain secret material: {key}")
        fields[key] = redact(content)
    return fields


def resolve_project_path(root: Path, relative: str, label: str) -> Path:
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise FlowError(f"{label} escapes project root: {relative}") from exc
    return path


def active_task(state: dict[str, Any]) -> dict[str, Any]:
    active = state.get("activeTask")
    if not active:
        raise FlowError("no active task")
    return active


def task_digest(root: Path, state: dict[str, Any]) -> str:
    active = active_task(state)
    path = task_path(root, active["id"])
    try:
        return sha256_bytes(path.read_bytes())
    except FileNotFoundError as exc:
        raise FlowError(f"active task file is missing: {path}") from exc


def is_secret_path(relative: str) -> bool:
    path = Path(relative)
    name = path.name.lower()
    return (
        name in {item.lower() for item in SECRET_NAMES}
        or name.startswith(".env.")
        or path.suffix.lower() in SECRET_SUFFIXES
        or any(
            part.lower() in {"secret", "secrets", "credential", "credentials"}
            for part in path.parts
        )
    )


def redact(text: str) -> str:
    patterns = (
        r"(?i)\b(api[_-]?key|token|password|passwd|secret)\s*[=:]\s*[^\s,;]+",
        r"(?i)\bauthorization:\s*bearer\s+[^\s]+",
        r"\b(ghp|github_pat|sk)-[A-Za-z0-9_-]{12,}\b",
    )
    redacted = text
    for pattern in patterns:
        redacted = re.sub(pattern, "[REDACTED]", redacted)
    return redacted


def configured_generated_paths(root: Path) -> set[str]:
    path = config_path(root)
    if not path.is_file():
        return set()
    try:
        with path.open("rb") as handle:
            config = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return set()
    generated: set[str] = set()
    for check in config.get("checks", []):
        report = check.get("report")
        if isinstance(report, str):
            generated.add(Path(report).as_posix())
        for artifact in check.get("artifacts", []):
            if isinstance(artifact, str):
                generated.add(Path(artifact).as_posix())
    return generated


def safe_files(root: Path) -> Iterable[Path]:
    generated = configured_generated_paths(root)
    for base, dirs, names in os.walk(root):
        base_path = Path(base)
        dirs[:] = [
            name
            for name in dirs
            if name not in EXCLUDED_DIRS and not (base_path / name).is_symlink()
        ]
        for name in names:
            path = base_path / name
            if path.is_symlink():
                continue
            relative = path.relative_to(root).as_posix()
            if (
                relative == "spec/state.json"
                or relative == f"spec/{LOCK_NAME}"
                or relative.startswith("spec/evidence/")
                or relative in generated
            ):
                continue
            yield path


@contextmanager
def project_lock(root: Path, timeout_seconds: float = 10.0) -> Iterable[None]:
    fallback = spec_root(root) / LOCK_NAME
    lock = flow_parallel.common_lock_path(root, fallback)
    lock.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_seconds
    descriptor: int | None = None
    while descriptor is None:
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.write(
                descriptor,
                f"pid={os.getpid()} started={now_iso()}\n".encode("utf-8"),
            )
        except FileExistsError:
            try:
                stale = time.time() - lock.stat().st_mtime > 3600
            except FileNotFoundError:
                continue
            if stale:
                try:
                    lock.unlink()
                except FileNotFoundError:
                    pass
                continue
            if time.monotonic() >= deadline:
                raise FlowError(
                    "workflow lock is busy; another flow command is running"
                )
            time.sleep(0.05)
    try:
        yield
    finally:
        os.close(descriptor)
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


def run_command(command: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise FlowError("missing command after --")
    try:
        return subprocess.run(
            command,
            cwd=root,
            shell=False,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise FlowError(f"command not found: {command[0]}") from exc


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )


def is_git_repo(root: Path) -> bool:
    return git(root, "rev-parse", "--is-inside-work-tree").returncode == 0


def current_head(root: Path) -> str | None:
    result = git(root, "rev-parse", "HEAD")
    return result.stdout.strip() if result.returncode == 0 else None


def working_tree_paths(root: Path) -> list[str]:
    if not is_git_repo(root):
        return []
    result = git(root, "status", "--porcelain=1", "-z", "--untracked-files=all")
    if result.returncode != 0:
        raise FlowError("unable to inspect working tree")
    generated = configured_generated_paths(root)
    paths: list[str] = []
    for relative in flow_parallel.parse_porcelain_paths(result.stdout):
        parts = Path(relative).parts
        if (
            relative == "spec/state.json"
            or relative == f"spec/{LOCK_NAME}"
            or relative.startswith("spec/evidence/")
            or relative in generated
            or any(part in EXCLUDED_DIRS for part in parts)
            or relative.endswith((".pyc", ".pyo"))
        ):
            continue
        paths.append(relative)
    return sorted(set(paths))
