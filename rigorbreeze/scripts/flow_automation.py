"""Safe argv-based automation helpers for Production Flow."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import flow_parallel


LEVELS = ("manual", "commit", "push", "merge", "release")
JOURNAL_VERSION = 1
JOURNAL_NAME = "automation.json"


class AutomationError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def require_level(config: dict[str, Any], action: str) -> dict[str, Any]:
    automation = config.get("automation", {})
    level = automation.get("level", "manual")
    if level not in LEVELS:
        raise AutomationError(f"unknown automation level: {level}")
    if LEVELS.index(level) < LEVELS.index(action):
        raise AutomationError(f"automation level {level} does not allow {action}")
    return automation


def journal_path(root: Path) -> Path | None:
    common = flow_parallel.git_common_dir(root)
    if common is None:
        return None
    return common / flow_parallel.REGISTRY_DIRECTORY / JOURNAL_NAME


def empty_journal() -> dict[str, Any]:
    return {"version": JOURNAL_VERSION, "actions": {}}


def load_journal(root: Path) -> dict[str, Any]:
    path = journal_path(root)
    if path is None or not path.exists():
        return empty_journal()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AutomationError(f"invalid automation journal: {path}: {exc}") from exc
    if value.get("version") != JOURNAL_VERSION or not isinstance(
        value.get("actions"), dict
    ):
        raise AutomationError(f"invalid automation journal: {path}")
    for key, record in value["actions"].items():
        if (
            not isinstance(record, dict)
            or record.get("idempotencyKey") != key
            or not isinstance(record.get("taskId"), str)
            or record.get("action") not in {"commit", "push", "merge", "release"}
            or record.get("status") not in {"running", "succeeded", "failed"}
            or not isinstance(record.get("input"), dict)
            or record.get("authorizationMode", "standing")
            not in {"standing", "user-once"}
            or ("target" in record and not isinstance(record.get("target"), dict))
            or ("result" in record and not isinstance(record.get("result"), dict))
        ):
            raise AutomationError(f"invalid automation journal: {path}")
    return value


def save_journal(root: Path, journal: dict[str, Any]) -> None:
    path = journal_path(root)
    if path is None:
        raise AutomationError("automation journal requires a Git repository")
    flow_parallel.atomic_json(path, journal)


def idempotency_key(action: str, task_id: str, *parts: str) -> str:
    material = ":".join((action, task_id, *parts))
    return hashlib.sha256(material.encode()).hexdigest()


def get_action(root: Path, key: str) -> dict[str, Any] | None:
    return load_journal(root)["actions"].get(key)


def start_action(
    root: Path,
    key: str,
    *,
    task_id: str,
    action: str,
    inputs: dict[str, Any],
    target: dict[str, Any] | None = None,
    authorization_mode: str = "standing",
) -> dict[str, Any]:
    journal = load_journal(root)
    existing = journal["actions"].get(key)
    if existing and existing.get("status") == "succeeded":
        return existing
    record = {
        "idempotencyKey": key,
        "taskId": task_id,
        "action": action,
        "status": "running",
        "authorizationMode": authorization_mode,
        "input": inputs,
        "target": target or {},
        "startedAt": (
            existing.get("startedAt") or now_iso()
            if isinstance(existing, dict)
            else now_iso()
        ),
    }
    journal["actions"][key] = record
    save_journal(root, journal)
    return record


def finish_action(
    root: Path,
    key: str,
    *,
    status: str,
    result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if status not in {"succeeded", "failed"}:
        raise AutomationError(f"invalid automation status: {status}")
    journal = load_journal(root)
    record = journal["actions"].get(key)
    if not isinstance(record, dict):
        raise AutomationError(f"automation action is missing: {key}")
    record["status"] = status
    record["result"] = result or {}
    record["completedAt"] = now_iso()
    save_journal(root, journal)
    return record


def latest_action(root: Path, task_id: str | None = None) -> dict[str, Any] | None:
    actions = load_journal(root)["actions"].values()
    matching = [
        item
        for item in actions
        if isinstance(item, dict) and (task_id is None or item.get("taskId") == task_id)
    ]
    if not matching:
        return None
    _, latest = max(
        enumerate(matching),
        key=lambda indexed: (
            str(indexed[1].get("completedAt") or indexed[1].get("startedAt") or ""),
            indexed[0],
        ),
    )
    return latest


def action_summary(action: dict[str, Any] | None) -> dict[str, Any] | None:
    if not action:
        return None
    target = action.get("target", {})
    result = action.get("result", {})
    return {
        "action": action.get("action"),
        "status": action.get("status"),
        "authorizationMode": action.get("authorizationMode", "standing"),
        "branch": target.get("branch"),
        "remote": target.get("remote"),
        "environment": target.get("environment"),
        "commitSha": result.get("commitSha"),
        "remoteSha": result.get("remoteSha"),
        "providerOperationId": result.get("providerOperationId"),
        "recordedAt": action.get("completedAt") or action.get("startedAt"),
    }


def recover_interrupted_commit(root: Path, task_id: str) -> dict[str, Any] | None:
    running = [
        item
        for item in load_journal(root)["actions"].values()
        if isinstance(item, dict)
        and item.get("taskId") == task_id
        and item.get("action") == "commit"
        and item.get("status") == "running"
    ]
    for action in sorted(
        running, key=lambda item: str(item.get("startedAt") or ""), reverse=True
    ):
        inputs = action.get("input", {})
        parent = str(inputs.get("parentSha") or "")
        tree = str(inputs.get("treeSha") or "")
        if not parent or not tree:
            continue
        head = flow_parallel.git(root, "rev-parse", "HEAD")
        head_parent = flow_parallel.git(root, "rev-parse", "HEAD^")
        head_tree = flow_parallel.git(root, "rev-parse", "HEAD^{tree}")
        if (
            head.returncode == 0
            and head_parent.returncode == 0
            and head_tree.returncode == 0
            and head_parent.stdout.strip() == parent
            and head_tree.stdout.strip() == tree
        ):
            return finish_action(
                root,
                str(action["idempotencyKey"]),
                status="succeeded",
                result={"commitSha": head.stdout.strip(), "recovered": True},
            )
    return None


def verification_commit_bridge(
    root: Path,
    *,
    task_id: str,
    head: str,
    task_digest: str,
    evidence_digest: str,
    verification_digest: str,
    project_fingerprint: str,
) -> bool:
    """Prove that current HEAD is the exact tree verified before an auto commit."""
    head_tree = flow_parallel.git(root, "rev-parse", "HEAD^{tree}")
    if head_tree.returncode != 0:
        return False
    tree = head_tree.stdout.strip()
    for action in load_journal(root)["actions"].values():
        if (
            not isinstance(action, dict)
            or action.get("taskId") != task_id
            or action.get("action") != "commit"
            or action.get("status") != "succeeded"
            or (action.get("result") or {}).get("commitSha") != head
        ):
            continue
        inputs = action.get("input") or {}
        if (
            inputs.get("treeSha") == tree
            and inputs.get("taskDigest") == task_digest
            and inputs.get("evidenceDigest") == evidence_digest
            and inputs.get("verificationDigest") == verification_digest
            and inputs.get("projectFingerprint") == project_fingerprint
        ):
            return True
    return False


def working_tree_paths(root: Path, excluded: set[str] | None = None) -> list[str]:
    result = flow_parallel.git(
        root, "status", "--porcelain=1", "-z", "--untracked-files=all"
    )
    if result.returncode != 0:
        raise AutomationError("unable to inspect working tree")
    ignored = excluded or set()
    return [
        relative
        for relative in flow_parallel.parse_porcelain_paths(result.stdout)
        if relative not in ignored
    ]


def stage_exact_paths(root: Path, files: list[str]) -> None:
    existing = [relative for relative in files if (root / relative).exists()]
    removed = [relative for relative in files if not (root / relative).exists()]
    if existing:
        added = flow_parallel.git(root, "add", "--", *existing)
        if added.returncode != 0:
            raise AutomationError(added.stderr.strip() or "unable to stage task files")
    if removed:
        tracked = [
            relative
            for relative in removed
            if flow_parallel.git(root, "cat-file", "-e", f"HEAD:{relative}").returncode
            == 0
        ]
        if len(tracked) != len(removed):
            unknown = sorted(set(removed) - set(tracked))
            raise AutomationError(
                "unable to stage unknown removed paths: " + ", ".join(unknown)
            )
        deleted = flow_parallel.git(root, "update-index", "--remove", "--", *tracked)
        if deleted.returncode != 0:
            raise AutomationError(
                deleted.stderr.strip() or "unable to stage removed task files"
            )


def commit_action(
    root: Path,
    *,
    task_id: str,
    files: list[str],
    staged_before: list[str],
    message: str,
    inputs: dict[str, Any],
    target: dict[str, Any],
    check: Callable[[], None],
    redact: Callable[[str], str],
    authorization_mode: str = "standing",
) -> str:
    if recover_interrupted_commit(root, task_id):
        return "recovered"
    stage_exact_paths(root, files)
    try:
        check()
    except Exception:
        flow_parallel.git(root, "reset", "--", *files)
        if staged_before:
            flow_parallel.git(root, "add", "--", *staged_before)
        raise
    stage_exact_paths(root, files)
    parent = flow_parallel.git(root, "rev-parse", "HEAD").stdout.strip()
    tree_result = flow_parallel.git(root, "write-tree")
    if tree_result.returncode != 0:
        raise AutomationError(
            tree_result.stderr.strip() or "unable to compute staged tree"
        )
    tree = tree_result.stdout.strip()
    key_parts = [parent, tree]
    if authorization_mode != "standing":
        key_parts.append(authorization_mode)
    key = idempotency_key("commit", task_id, *key_parts)
    start_action(
        root,
        key,
        task_id=task_id,
        action="commit",
        inputs={
            **inputs,
            "parentSha": parent,
            "treeSha": tree,
            "files": files,
        },
        target=target,
        authorization_mode=authorization_mode,
    )
    result = flow_parallel.git(root, "commit", "-m", message)
    if result.returncode != 0:
        finish_action(
            root,
            key,
            status="failed",
            result={"summary": redact(result.stderr.strip()[-1000:])},
        )
        flow_parallel.git(root, "reset", "--", *files)
        if staged_before:
            flow_parallel.git(root, "add", "--", *staged_before)
        raise AutomationError(result.stderr.strip() or "automatic commit failed")
    head = flow_parallel.git(root, "rev-parse", "HEAD").stdout.strip()
    finish_action(
        root,
        key,
        status="succeeded",
        result={"commitSha": head},
    )
    return "completed"


def push_action(
    root: Path,
    *,
    task_id: str,
    remote: str,
    branch: str,
    head: str,
    inputs: dict[str, Any],
    redact: Callable[[str], str],
    authorization_mode: str = "standing",
) -> str:
    key_parts = [head, remote, branch]
    if authorization_mode != "standing":
        key_parts.append(authorization_mode)
    key = idempotency_key("push", task_id, *key_parts)
    existing = get_action(root, key)
    if existing and existing.get("status") == "succeeded":
        return "already"
    start_action(
        root,
        key,
        task_id=task_id,
        action="push",
        inputs=inputs,
        target={"remote": remote, "branch": branch},
        authorization_mode=authorization_mode,
    )
    result = flow_parallel.git(root, "push", "--set-upstream", remote, branch)
    if result.returncode != 0:
        summary = redact(result.stderr.strip()[-1000:])
        finish_action(
            root,
            key,
            status="failed",
            result={"summary": summary},
        )
        raise AutomationError(summary or "automatic push failed")
    remote_ref = flow_parallel.git(root, "ls-remote", remote, f"refs/heads/{branch}")
    remote_sha = (
        remote_ref.stdout.split()[0]
        if remote_ref.returncode == 0 and remote_ref.stdout.split()
        else ""
    )
    if remote_sha != head:
        summary = "remote task branch does not match the local HEAD after push"
        finish_action(root, key, status="failed", result={"summary": summary})
        raise AutomationError(summary)
    finish_action(
        root,
        key,
        status="succeeded",
        result={"commitSha": head, "remoteSha": remote_sha},
    )
    return "completed"


def provider_action(
    root: Path,
    *,
    task_id: str,
    action: str,
    key: str,
    values: dict[str, str],
    inputs: dict[str, Any],
    target: dict[str, Any],
    check_command: Any,
    action_command: Any,
    redact: Callable[[str], str],
) -> str:
    existing = get_action(root, key)
    if existing and existing.get("status") == "succeeded":
        return "already"
    values["idempotency_key"] = key
    start_action(
        root,
        key,
        task_id=task_id,
        action=action,
        inputs=inputs,
        target=target,
    )
    try:
        run_adapter(root, check_command, values, f"{action} provider check")
        result = run_adapter(root, action_command, values, f"{action} provider action")
    except AutomationError as exc:
        summary = redact(str(exc)[-1000:])
        finish_action(
            root,
            key,
            status="failed",
            result={"summary": summary},
        )
        raise AutomationError(summary) from exc
    output = redact((result.stdout or "").strip()[-1000:])
    operation_id = next(
        (line.strip() for line in output.splitlines() if line.strip()), ""
    )
    finish_action(
        root,
        key,
        status="succeeded",
        result={
            "providerOperationId": operation_id or None,
            "summary": output,
            "artifactSha256": values["artifact_sha256"] or None,
        },
    )
    return "completed"


def expand_command(command: Any, values: dict[str, str], label: str) -> list[str]:
    if (
        not isinstance(command, list)
        or not command
        or not all(isinstance(part, str) for part in command)
    ):
        raise AutomationError(f"{label} requires a non-empty argv command")
    try:
        return [part.format_map(values) for part in command]
    except KeyError as exc:
        raise AutomationError(f"{label} uses unknown placeholder: {exc}") from exc


def run_adapter(
    root: Path,
    command: Any,
    values: dict[str, str],
    label: str,
) -> subprocess.CompletedProcess[str]:
    argv = expand_command(command, values, label)
    result = subprocess.run(
        argv,
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    if result.returncode != 0:
        summary = (result.stderr or result.stdout).strip()
        raise AutomationError(f"{label} failed: {summary}")
    return result
