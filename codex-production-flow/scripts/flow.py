#!/usr/bin/env python3
"""Deterministic gates for Codex Production Flow."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


VERSION = 1
SPEC_DIR = "spec"
PLACEHOLDERS = ("TODO", "TBD", "待填写", "待定义")
REQUIRED_TASK_SECTIONS = (
    "## Authoritative inputs",
    "## Allowed scope",
    "## Forbidden scope",
    "## Acceptance criteria",
    "## Verification commands",
    "## Runtime and release",
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
MIGRATION_PARTS = {"migration", "migrations", "alembic", "flyway", "liquibase", "versions"}
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
}
AGENTS_START = "<!-- codex-production-flow:start -->"
AGENTS_END = "<!-- codex-production-flow:end -->"
LOCK_NAME = ".flow.lock"
RUNNER_MARKER = '"""Deterministic gates for Codex Production Flow."""'
REPOSITORY_WRAPPER_MARKER = '"""Repository-local entry point for the bundled Production Flow Skill."""'


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
        },
        "red": None,
        "verification": None,
        "attestations": {},
        "lastClosed": None,
        "updatedAt": now_iso(),
    }


def task_template(task_id: str, title: str, risk: str) -> str:
    return f"""# {task_id}: {title}

Risk: {risk}

## Authoritative inputs
- Requirement: TODO
- Design/prototype: TODO
- API/data/permission: TODO

## Allowed scope
- TODO

## Forbidden scope
- TODO

## Acceptance criteria
- REQ-001: TODO
- UX-001: TODO or N/A with reason
- API/DATA/SEC/OPS-001: TODO or N/A with reason

## Verification commands
- TODO

## Runtime and release
- Runtime evidence: TODO
- Migration and rollback: TODO
- Feature flag/canary/SLO: TODO
- Stop conditions: TODO

## Completion report
- Git SHA / CI run / artifact: TODO
- Remaining risks: TODO
"""


def index_template() -> str:
    return """# Production Spec Index

This tree keeps one human-authored Markdown file per active change. Machine state and evidence are JSON.

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
## Codex Production Flow

Before implementation, read `spec/index.md`, inspect `spec/state.json`, and run `python scripts/codex-flow.py status` or invoke `$codex-production-flow`.
Only one active task is allowed. Approved task content changes invalidate downstream evidence.
Do not claim completion without fresh automated verification, runtime evidence, review evidence, and release checks appropriate to risk.
{AGENTS_END}"""


def ensure_agents(root: Path) -> None:
    path = root / "AGENTS.md"
    existing = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = agents_block()
    pattern = re.compile(re.escape(AGENTS_START) + r".*?" + re.escape(AGENTS_END), re.S)
    if pattern.search(existing):
        updated = pattern.sub(block, existing)
    else:
        updated = existing.rstrip() + ("\n\n" if existing.strip() else "") + block + "\n"
    if updated != existing:
        atomic_write(path, updated)


def load_state(root: Path) -> dict[str, Any]:
    return read_json(state_path(root))


def save_state(root: Path, state: dict[str, Any]) -> None:
    state["updatedAt"] = now_iso()
    write_json(state_path(root), state)


def load_evidence(root: Path, task_id: str) -> dict[str, Any]:
    path = evidence_path(root, task_id)
    if not path.exists():
        return {"workflowVersion": VERSION, "taskId": task_id, "red": [], "verifications": [], "attestations": []}
    return read_json(path)


def save_evidence(root: Path, task_id: str, evidence: dict[str, Any]) -> None:
    write_json(evidence_path(root, task_id), evidence)


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


def refresh_approval(root: Path, state: dict[str, Any]) -> bool:
    approval = state["approvals"]["task"]
    if not approval.get("valid"):
        return False
    current = task_digest(root, state)
    if current == approval.get("digest"):
        return False
    approval["valid"] = False
    approval["invalidatedAt"] = now_iso()
    state["phase"] = "drafting"
    state["red"] = None
    state["verification"] = None
    state["attestations"] = {}
    return True


def approval_valid(root: Path, state: dict[str, Any]) -> bool:
    refresh_approval(root, state)
    approval = state["approvals"]["task"]
    return bool(approval.get("valid") and approval.get("digest") == task_digest(root, state))


def is_secret_path(relative: str) -> bool:
    path = Path(relative)
    name = path.name.lower()
    return (
        name in {item.lower() for item in SECRET_NAMES}
        or name.startswith(".env.")
        or path.suffix.lower() in SECRET_SUFFIXES
        or any(part.lower() in {"secret", "secrets", "credential", "credentials"} for part in path.parts)
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


def safe_files(root: Path) -> Iterable[Path]:
    for base, dirs, names in os.walk(root):
        base_path = Path(base)
        dirs[:] = [name for name in dirs if name not in EXCLUDED_DIRS and not (base_path / name).is_symlink()]
        for name in names:
            path = base_path / name
            if path.is_symlink():
                continue
            relative = path.relative_to(root).as_posix()
            if (
                relative == "spec/state.json"
                or relative == f"spec/{LOCK_NAME}"
                or relative.startswith("spec/evidence/")
            ):
                continue
            yield path


@contextmanager
def project_lock(root: Path, timeout_seconds: float = 10.0) -> Iterable[None]:
    spec_root(root).mkdir(parents=True, exist_ok=True)
    lock = spec_root(root) / LOCK_NAME
    deadline = time.monotonic() + timeout_seconds
    descriptor: int | None = None
    while descriptor is None:
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.write(descriptor, f"pid={os.getpid()} started={now_iso()}\n".encode("utf-8"))
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
                raise FlowError("workflow lock is busy; another flow command is running")
            time.sleep(0.05)
    try:
        yield
    finally:
        os.close(descriptor)
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


def project_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(safe_files(root), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


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
        ["git", *args], cwd=root, text=True, encoding="utf-8", errors="replace", capture_output=True
    )


def is_git_repo(root: Path) -> bool:
    return git(root, "rev-parse", "--is-inside-work-tree").returncode == 0


def current_head(root: Path) -> str | None:
    result = git(root, "rev-parse", "HEAD")
    return result.stdout.strip() if result.returncode == 0 else None


def staged_files(root: Path) -> list[str]:
    result = git(root, "diff", "--cached", "--name-only", "--diff-filter=ACMR")
    if result.returncode != 0:
        raise FlowError("unable to read staged files")
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def secret_content_paths(root: Path, paths: Iterable[str]) -> list[str]:
    patterns = (
        re.compile(
            r"(?i)\b(api[_-]?key|access[_-]?token|token|password|passwd|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_./+\-=]{12,}"
        ),
        re.compile(r"\b(ghp|github_pat|sk)-[A-Za-z0-9_-]{12,}\b"),
    )
    found: list[str] = []
    for relative in paths:
        result = git(root, "show", f":{relative}")
        if result.returncode != 0 or "\0" in result.stdout:
            continue
        if any(pattern.search(result.stdout) for pattern in patterns):
            found.append(relative)
    return found


def is_migration_path(relative: str) -> bool:
    parts = {part.lower() for part in Path(relative).parts}
    return bool(parts & MIGRATION_PARTS)


def is_dependency_path(relative: str) -> bool:
    return Path(relative).name.lower() in {name.lower() for name in DEPENDENCY_NAMES}


def verification_current(root: Path, state: dict[str, Any]) -> bool:
    verification = state.get("verification")
    return bool(
        verification
        and verification.get("passed")
        and verification.get("taskDigest") == task_digest(root, state)
        and verification.get("projectFingerprint") == project_fingerprint(root)
    )


def attestation_current(root: Path, state: dict[str, Any], kind: str) -> bool:
    record = state.get("attestations", {}).get(kind)
    return bool(
        record
        and record.get("taskDigest") == task_digest(root, state)
        and record.get("projectFingerprint") == project_fingerprint(root)
        and record.get("evidence")
    )


def command_init(root: Path) -> None:
    spec = spec_root(root)
    for name in ("changes", "evidence", "archive"):
        (spec / name).mkdir(parents=True, exist_ok=True)
    index = spec / "index.md"
    if not index.exists():
        atomic_write(index, index_template())
    if not state_path(root).exists():
        write_json(state_path(root), initial_state())
    runner = root / "scripts" / "codex-flow.py"
    source = Path(__file__).read_text(encoding="utf-8")
    if not runner.exists():
        atomic_write(runner, source)
    else:
        existing = runner.read_text(encoding="utf-8", errors="replace")
        if existing != source and RUNNER_MARKER in existing:
            atomic_write(runner, source)
        elif (
            existing != source
            and REPOSITORY_WRAPPER_MARKER in existing
            and (root / "codex-production-flow" / "scripts" / "flow.py").is_file()
        ):
            pass
        elif existing != source:
            raise FlowError("scripts/codex-flow.py exists but is not a managed Production Flow runner")
    ensure_agents(root)
    print("initialized minimal spec tree")


def command_new(root: Path, task_id: str, title: str, risk: str) -> None:
    state = load_state(root)
    if state.get("activeTask"):
        raise FlowError(f"an active task already exists: {state['activeTask']['id']}")
    if not re.fullmatch(r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+", task_id):
        raise FlowError("task ID must look like TASK-001")
    path = task_path(root, task_id)
    if path.exists() or (spec_root(root) / "archive" / f"{task_id}.md").exists():
        raise FlowError(f"task ID already exists: {task_id}")
    atomic_write(path, task_template(task_id, title, risk))
    evidence = {"workflowVersion": VERSION, "taskId": task_id, "red": [], "verifications": [], "attestations": []}
    save_evidence(root, task_id, evidence)
    state.update(
        {
            "phase": "drafting",
            "activeTask": {"id": task_id, "title": title, "risk": risk, "createdAt": now_iso()},
            "red": None,
            "verification": None,
            "attestations": {},
        }
    )
    state["approvals"]["task"] = {"valid": False, "digest": None, "approvedAt": None}
    state["approvals"]["dependencies"] = []
    state["approvals"]["migrations"] = []
    save_state(root, state)
    print(f"created {task_id}")


def command_approve(root: Path, kind: str, name: str | None) -> None:
    state = load_state(root)
    active = active_task(state)
    if kind == "task":
        path = task_path(root, active["id"])
        content = path.read_text(encoding="utf-8")
        if any(token in content for token in PLACEHOLDERS):
            raise FlowError("task still contains placeholder content")
        missing = [section for section in REQUIRED_TASK_SECTIONS if section not in content]
        if missing:
            raise FlowError("task is missing required sections: " + ", ".join(missing))
        state["approvals"]["task"] = {
            "valid": True,
            "digest": task_digest(root, state),
            "approvedAt": now_iso(),
        }
        state["phase"] = "approved"
        state["red"] = None
        state["verification"] = None
        state["attestations"] = {}
    else:
        if not name:
            raise FlowError(f"{kind} approval requires --name")
        bucket = "dependencies" if kind == "dependency" else "migrations"
        state["approvals"][bucket].append({"name": name, "approvedAt": now_iso()})
    save_state(root, state)
    print(f"approved {kind}")


def command_status(root: Path) -> None:
    state = load_state(root)
    if refresh_approval(root, state):
        save_state(root, state)
    active = state.get("activeTask")
    approval = state["approvals"]["task"]
    verification = "current" if active and approval.get("valid") and verification_current(root, state) else "missing/stale"
    print(f"phase: {state.get('phase')}")
    print(f"active task: {active['id'] if active else 'none'}")
    print(f"approval: {'valid' if approval.get('valid') else 'invalid'}")
    print(f"verification: {verification}")


def command_red(root: Path, requirement: str, expect_pattern: str, command: list[str]) -> None:
    state = load_state(root)
    if not approval_valid(root, state):
        save_state(root, state)
        raise FlowError("task approval is missing or invalid")
    result = run_command(command, root)
    output = ((result.stdout or "") + (result.stderr or "")).strip()
    if result.returncode == 0:
        raise FlowError("RED command passed; expected an observed failure")
    if not re.search(expect_pattern, output, re.I | re.M):
        raise FlowError("RED output did not match the expected failure pattern")
    active = active_task(state)
    record = {
        "requirement": requirement,
        "command": [redact(part) for part in (command[1:] if command and command[0] == "--" else command)],
        "exitCode": result.returncode,
        "expectedPattern": expect_pattern,
        "summary": redact(output[-2000:]),
        "taskDigest": task_digest(root, state),
        "projectFingerprint": project_fingerprint(root),
        "head": current_head(root) if is_git_repo(root) else None,
        "observedAt": now_iso(),
    }
    evidence = load_evidence(root, active["id"])
    evidence["red"].append(record)
    save_evidence(root, active["id"], evidence)
    state["red"] = record
    state["phase"] = "red"
    save_state(root, state)
    print("RED observed and recorded")


def command_verify(root: Path, scope: str, command: list[str]) -> int:
    state = load_state(root)
    if not approval_valid(root, state):
        save_state(root, state)
        raise FlowError("task approval is missing or invalid")
    result = run_command(command, root)
    output = ((result.stdout or "") + (result.stderr or "")).strip()
    active = active_task(state)
    record = {
        "scope": scope,
        "command": [redact(part) for part in (command[1:] if command and command[0] == "--" else command)],
        "exitCode": result.returncode,
        "passed": result.returncode == 0,
        "summary": redact(output[-2000:]),
        "taskDigest": task_digest(root, state),
        "projectFingerprint": project_fingerprint(root),
        "head": current_head(root) if is_git_repo(root) else None,
        "verifiedAt": now_iso(),
    }
    evidence = load_evidence(root, active["id"])
    evidence["verifications"].append(record)
    save_evidence(root, active["id"], evidence)
    state["verification"] = record
    state["phase"] = "ready-to-release" if record["passed"] else "verifying"
    state["attestations"] = {}
    save_state(root, state)
    print("verification passed" if record["passed"] else "verification failed")
    return 0 if record["passed"] else 1


def command_attest(root: Path, kind: str, evidence_ref: str) -> None:
    state = load_state(root)
    if not approval_valid(root, state) or not verification_current(root, state):
        save_state(root, state)
        raise FlowError("fresh verification is required before attestation")
    active = active_task(state)
    record = {
        "kind": kind,
        "evidence": evidence_ref,
        "taskDigest": task_digest(root, state),
        "projectFingerprint": project_fingerprint(root),
        "recordedAt": now_iso(),
    }
    state.setdefault("attestations", {})[kind] = record
    evidence = load_evidence(root, active["id"])
    evidence["attestations"].append(record)
    save_evidence(root, active["id"], evidence)
    save_state(root, state)
    print(f"attested {kind}")


def ensure_release(root: Path, state: dict[str, Any]) -> None:
    if not approval_valid(root, state):
        raise FlowError("task approval is missing or invalid")
    if not verification_current(root, state):
        raise FlowError("verification is missing or stale")
    risk = active_task(state)["risk"]
    required = {
        "L0": (),
        "L1": ("runtime", "review"),
        "L2": ("runtime", "review", "security", "migration", "second-human"),
        "Emergency": ("runtime", "review", "incident"),
    }[risk]
    missing = [kind for kind in required if not attestation_current(root, state, kind)]
    if missing:
        raise FlowError("missing current release evidence: " + ", ".join(missing))


def command_check(root: Path, gate: str) -> None:
    state = load_state(root)
    if refresh_approval(root, state):
        save_state(root, state)
    active = active_task(state) if gate != "push" or state.get("activeTask") else None
    if gate == "start":
        if not active or not approval_valid(root, state):
            raise FlowError("valid approved active task required")
    elif gate == "implement":
        if not active or not approval_valid(root, state):
            raise FlowError("valid approved active task required")
        if active["risk"] in {"L1", "L2", "Emergency"}:
            red = state.get("red")
            if not red or red.get("taskDigest") != task_digest(root, state):
                raise FlowError("current RED or incident reproduction evidence is required")
    elif gate == "commit":
        if not is_git_repo(root):
            raise FlowError("commit gate requires a Git repository")
        paths = staged_files(root)
        if not paths:
            raise FlowError("commit gate requires staged files")
        secrets = [path for path in paths if is_secret_path(path)]
        if secrets:
            raise FlowError("secret paths are forbidden: " + ", ".join(secrets))
        secret_content = secret_content_paths(root, paths)
        if secret_content:
            raise FlowError("secret-like content detected: " + ", ".join(secret_content))
        dependencies = [path for path in paths if is_dependency_path(path)]
        if dependencies and not state["approvals"]["dependencies"]:
            raise FlowError("dependency approval is required: " + ", ".join(dependencies))
        migrations = [path for path in paths if is_migration_path(path)]
        if migrations and not state["approvals"]["migrations"]:
            raise FlowError("migration approval is required: " + ", ".join(migrations))
        if not verification_current(root, state):
            raise FlowError("verification is missing or stale")
    elif gate == "push":
        if state.get("phase") != "closed":
            raise FlowError("task must be archived before push")
    elif gate == "release":
        ensure_release(root, state)
    else:
        raise FlowError(f"unknown gate: {gate}")
    save_state(root, state)
    print(f"check {gate}: passed")


def command_archive(root: Path) -> None:
    state = load_state(root)
    ensure_release(root, state)
    active = active_task(state)
    source = task_path(root, active["id"])
    destination = spec_root(root) / "archive" / source.name
    if destination.exists():
        raise FlowError(f"archive already exists: {destination}")
    source.replace(destination)
    state["lastClosed"] = {
        "id": active["id"],
        "closedAt": now_iso(),
        "taskDigest": state["approvals"]["task"]["digest"],
        "verification": state.get("verification"),
    }
    state["activeTask"] = None
    state["phase"] = "closed"
    state["approvals"]["task"] = {"valid": False, "digest": None, "approvedAt": None}
    state["approvals"]["dependencies"] = []
    state["approvals"]["migrations"] = []
    state["red"] = None
    state["verification"] = None
    state["attestations"] = {}
    save_state(root, state)
    print(f"archived {active['id']}")


def command_doctor(root: Path) -> None:
    issues: list[str] = []
    for relative in ("index.md", "state.json"):
        if not (spec_root(root) / relative).is_file():
            issues.append(f"missing spec/{relative}")
    for relative in ("changes", "evidence", "archive"):
        if not (spec_root(root) / relative).is_dir():
            issues.append(f"missing spec/{relative}/")
    if not is_git_repo(root):
        issues.append("not a Git repository")
    try:
        state = load_state(root)
        if state.get("workflowVersion") != VERSION:
            issues.append("unsupported workflow version")
        active = state.get("activeTask")
        if active and not task_path(root, active["id"]).is_file():
            issues.append("active task file is missing")
    except FlowError as exc:
        issues.append(str(exc))
    if issues:
        raise FlowError("doctor found issues: " + "; ".join(issues))
    print("doctor: ok")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Production-grade spec, evidence, and release gates")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="target project root")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    new = sub.add_parser("new")
    new.add_argument("task_id")
    new.add_argument("--title", required=True)
    new.add_argument("--risk", choices=("L0", "L1", "L2", "Emergency"), required=True)
    sub.add_parser("status")
    approve = sub.add_parser("approve")
    approve.add_argument("kind", choices=("task", "dependency", "migration"))
    approve.add_argument("--name")
    red = sub.add_parser("red")
    red.add_argument("--requirement", required=True)
    red.add_argument("--expect-pattern", required=True)
    red.add_argument("run", nargs=argparse.REMAINDER)
    verify = sub.add_parser("verify")
    verify.add_argument("--scope", choices=("targeted", "affected", "full"), required=True)
    verify.add_argument("run", nargs=argparse.REMAINDER)
    attest = sub.add_parser("attest")
    attest.add_argument(
        "kind", choices=("runtime", "review", "security", "migration", "second-human", "incident")
    )
    attest.add_argument("--evidence", required=True)
    check = sub.add_parser("check")
    check.add_argument("gate", choices=("start", "implement", "commit", "push", "release"))
    sub.add_parser("archive")
    sub.add_parser("doctor")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        with project_lock(root):
            if args.command == "init":
                command_init(root)
            elif args.command == "new":
                command_new(root, args.task_id, args.title, args.risk)
            elif args.command == "status":
                command_status(root)
            elif args.command == "approve":
                command_approve(root, args.kind, args.name)
            elif args.command == "red":
                command_red(root, args.requirement, args.expect_pattern, args.run)
            elif args.command == "verify":
                return command_verify(root, args.scope, args.run)
            elif args.command == "attest":
                command_attest(root, args.kind, args.evidence)
            elif args.command == "check":
                command_check(root, args.gate)
            elif args.command == "archive":
                command_archive(root)
            elif args.command == "doctor":
                command_doctor(root)
        return 0
    except FlowError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
