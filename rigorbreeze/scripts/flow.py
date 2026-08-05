#!/usr/bin/env python3
"""Deterministic gates for RigorBreeze."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# Repository-local runners import four helper modules. Never leave Python bytecode
# behind in a project merely because a workflow command was inspected.
sys.dont_write_bytecode = True

import flow_automation  # noqa: E402
import flow_parallel  # noqa: E402
import flow_policy  # noqa: E402
import flow_state  # noqa: E402
from flow_policy import (  # noqa: E402
    acceptance_ids,
    allowed_scope,
    approval_valid,
    automation_input,
    automation_task_paths,
    automation_values,
    baseline_current,
    check_category,
    configured_paths,
    configured_verification_current,
    current_structured_records,
    declared_dependencies,
    destructive_migrations,
    ensure_close,
    ensure_delivery_quality,
    ensure_release,
    ensure_scope_current,
    full_profile_current,
    is_configured_migration_path,
    is_dependency_path,
    l2_full_profile_issues,
    next_action,
    operational_modes,
    path_allowed,
    path_under,
    practice_summary,
    project_fingerprint,
    record_practice_event,
    record_artifacts,
    red_record_tests_current,
    refresh_approval,
    report_record,
    save_state,
    secret_content_scan,
    secret_content_paths,
    staged_files,
    task_change_paths,
    task_owned_path,
    task_scope_status,
    runtime_claims,
    test_chain_current,
    test_file_digest,
    validate_operation_plan,
    validate_operation_result,
    validate_scope_entries,
    verification_current,
)
from flow_state import (  # noqa: E402
    CONFIG_NAME,
    LOCK_NAME,
    MIGRATION_EVIDENCE_FIELDS,
    MODES,
    PLACEHOLDERS,
    RELEASE_GOVERNANCE_FIELDS,
    REPOSITORY_WRAPPER_MARKER,
    REQUIRED_TASK_SECTIONS,
    RUNNER_MARKER,
    SECURITY_EVIDENCE_FIELDS,
    TOOL_VERSION,
    VERSION,
    FlowError,
    active_task,
    atomic_write,
    config_digest,
    config_path,
    config_template,
    clean_managed_bytecode,
    current_head,
    effective_mode,
    empty_evidence,
    ensure_agents,
    evidence_path,
    git,
    index_template,
    initial_state,
    is_git_repo,
    is_secret_path,
    load_config,
    load_evidence,
    load_state,
    legacy_state_path,
    migrate_legacy_state,
    now_iso,
    parse_fields,
    project_lock,
    read_json,
    redact,
    resolve_project_path,
    run_command,
    save_evidence,
    sha256_bytes,
    spec_root,
    state_path,
    subprocess_text,
    task_digest,
    task_path,
    task_template,
    upgrade_evidence,
    upgrade_persisted_data,
    upgrade_state,
    working_tree_paths,
    write_json,
)


def command_init(root: Path) -> None:
    existing_state = None
    if state_path(root).exists():
        existing_state = load_state(root)
    elif legacy_state_path(root).exists():
        existing_state = upgrade_state(read_json(legacy_state_path(root)))
    current_installation = installation_status(root, existing_state)
    if (
        current_installation["status"] != "current"
        and existing_state
        and existing_state.get("activeTask")
    ):
        raise FlowError(
            "an active task prevents workflow runner upgrade; finish or abandon the "
            "active task with the bundled runner, then run init"
        )
    spec = spec_root(root)
    for name in ("changes", "evidence", "archive"):
        (spec / name).mkdir(parents=True, exist_ok=True)
    index = spec / "index.md"
    if not index.exists():
        atomic_write(index, index_template())
    current_state = state_path(root)
    legacy_state = legacy_state_path(root)
    if not current_state.exists():
        if current_state != legacy_state and legacy_state.exists():
            write_json(current_state, upgrade_state(read_json(legacy_state)))
        else:
            write_json(current_state, initial_state())
    else:
        upgrade_persisted_data(root)
    config = config_path(root)
    if not config.exists():
        atomic_write(config, config_template())
    runner = root / "scripts" / "rigorbreeze.py"
    source = Path(__file__).read_text(encoding="utf-8")
    helper_sources = {
        "flow_state.py": Path(flow_state.__file__).read_text(encoding="utf-8"),
        "flow_policy.py": Path(flow_policy.__file__).read_text(encoding="utf-8"),
        "flow_parallel.py": Path(flow_parallel.__file__).read_text(encoding="utf-8"),
        "flow_automation.py": Path(flow_automation.__file__).read_text(
            encoding="utf-8"
        ),
    }
    if not runner.exists():
        atomic_write(runner, source)
    else:
        existing = runner.read_text(encoding="utf-8", errors="replace")
        if existing != source and RUNNER_MARKER in existing:
            atomic_write(runner, source)
        elif (
            existing != source
            and REPOSITORY_WRAPPER_MARKER in existing
            and (root / "rigorbreeze" / "scripts" / "flow.py").is_file()
        ):
            pass
        elif existing != source:
            raise FlowError(
                "scripts/rigorbreeze.py exists but is not a managed RigorBreeze runner"
            )
    for filename, helper_source in helper_sources.items():
        helper = root / "scripts" / filename
        if (
            not helper.exists()
            or helper.read_text(encoding="utf-8", errors="replace") != helper_source
        ):
            atomic_write(helper, helper_source)
    ensure_agents(root)
    legacy_warnings = migrate_legacy_state(root, remove_untracked=True)
    cache_warnings = clean_managed_bytecode(root)
    for warning in legacy_warnings:
        print(f"warning: {warning}")
    for relative in cache_warnings:
        print(f"warning: retained unknown cache entry: {relative}")
    print("initialized v4 workflow and minimal spec tree")


def installation_status(
    root: Path, state: dict[str, Any] | None = None
) -> dict[str, Any]:
    repository_runner = root / "scripts" / "rigorbreeze.py"
    if not repository_runner.is_file():
        return {
            "skillVersion": TOOL_VERSION,
            "runnerVersion": None,
            "status": "missing",
            "upgradeSafe": not bool((state or {}).get("activeTask")),
            "missingComponents": ["scripts/rigorbreeze.py"],
            "modifiedComponents": [],
        }
    runner_text = repository_runner.read_text(encoding="utf-8", errors="replace")
    if RUNNER_MARKER in runner_text:
        target_directory = root / "scripts"
        target_runner = repository_runner
    elif (
        REPOSITORY_WRAPPER_MARKER in runner_text
        and (root / "rigorbreeze" / "scripts" / "flow.py").is_file()
    ):
        target_directory = root / "rigorbreeze" / "scripts"
        target_runner = target_directory / "flow.py"
    else:
        return {
            "skillVersion": TOOL_VERSION,
            "runnerVersion": None,
            "status": "unmanaged",
            "upgradeSafe": not bool((state or {}).get("activeTask")),
            "missingComponents": [],
            "modifiedComponents": ["scripts/rigorbreeze.py"],
        }

    version_file = target_directory / "flow_state.py"
    version_text = (
        version_file.read_text(encoding="utf-8", errors="replace")
        if version_file.is_file()
        else ""
    )
    match = re.search(r'^TOOL_VERSION\s*=\s*["\']([^"\']+)["\']', version_text, re.M)
    runner_version = match.group(1) if match else None
    expected = {
        target_runner: Path(__file__).read_text(encoding="utf-8"),
        target_directory / "flow_state.py": Path(flow_state.__file__).read_text(
            encoding="utf-8"
        ),
        target_directory / "flow_policy.py": Path(flow_policy.__file__).read_text(
            encoding="utf-8"
        ),
        target_directory / "flow_parallel.py": Path(flow_parallel.__file__).read_text(
            encoding="utf-8"
        ),
        target_directory / "flow_automation.py": Path(
            flow_automation.__file__
        ).read_text(encoding="utf-8"),
    }
    missing_components = sorted(
        str(path.relative_to(root)).replace("\\", "/")
        for path in expected
        if not path.is_file()
    )
    modified_components = sorted(
        str(path.relative_to(root)).replace("\\", "/")
        for path, content in expected.items()
        if path.is_file()
        and path.read_text(encoding="utf-8", errors="replace") != content
    )
    if missing_components:
        status = "missing"
    elif runner_version != TOOL_VERSION:
        status = "outdated"
    elif not modified_components:
        status = "current"
    else:
        status = "unmanaged"
    return {
        "skillVersion": TOOL_VERSION,
        "runnerVersion": runner_version,
        "status": status,
        "upgradeSafe": not bool((state or {}).get("activeTask")),
        "missingComponents": missing_components,
        "modifiedComponents": modified_components,
    }


def managed_workflow_paths(root: Path) -> tuple[str, ...]:
    runner = root / "scripts" / "rigorbreeze.py"
    wrapper = (
        runner.is_file()
        and REPOSITORY_WRAPPER_MARKER
        in runner.read_text(encoding="utf-8", errors="replace")
        and (root / "rigorbreeze" / "scripts" / "flow.py").is_file()
    )
    runner_paths = (
        (
            "scripts/rigorbreeze.py",
            "rigorbreeze/scripts/flow.py",
            "rigorbreeze/scripts/flow_state.py",
            "rigorbreeze/scripts/flow_policy.py",
            "rigorbreeze/scripts/flow_parallel.py",
            "rigorbreeze/scripts/flow_automation.py",
        )
        if wrapper
        else (
            "scripts/rigorbreeze.py",
            "scripts/flow_state.py",
            "scripts/flow_policy.py",
            "scripts/flow_parallel.py",
            "scripts/flow_automation.py",
        )
    )
    return (
        "AGENTS.md",
        CONFIG_NAME,
        *runner_paths,
        "spec/index.md",
    )


def baseline_branch(root: Path, state: dict[str, Any] | None = None) -> str | None:
    active = (state or {}).get("activeTask") or {}
    if active.get("baseBranch"):
        return str(active["baseBranch"])
    try:
        configured = str(
            load_config(root).get("parallel", {}).get("base_branch", "")
        ).strip()
    except FlowError:
        configured = ""
    if configured:
        return configured
    try:
        return flow_parallel.default_base_branch(root)
    except flow_parallel.ParallelError:
        return None


def completed_closure_paths(root: Path, state: dict[str, Any]) -> list[str]:
    last = state.get("lastClosed") or {}
    if last.get("outcome") not in {"completed", "reconciled"}:
        return []
    task_id = last.get("id")
    if not task_id:
        return []
    return [
        f"spec/changes/{task_id}.md",
        f"spec/archive/{task_id}.md",
        f"spec/evidence/{task_id}.json",
    ]


def workflow_baseline_commit_paths(root: Path, state: dict[str, Any]) -> list[str]:
    allowed = set(managed_workflow_paths(root)) | set(
        completed_closure_paths(root, state)
    )
    changed = flow_automation.working_tree_paths(root, {f"spec/{LOCK_NAME}"})
    return sorted(path for path in changed if path in allowed)


def workflow_baseline_status(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    base = baseline_branch(root, state)
    payload: dict[str, Any] = {
        "status": "blocked",
        "baseBranch": base,
        "tracked": [],
        "untracked": list(managed_workflow_paths(root)),
        "modified": [],
        "safeToCommit": False,
        "nextAction": {
            "reason": "The workflow baseline branch cannot be determined.",
            "command": "configure parallel.base_branch, then run status --json",
        },
    }
    if not is_git_repo(root) or not base:
        return payload
    base_head = git(root, "rev-parse", base)
    if base_head.returncode != 0:
        payload["nextAction"] = {
            "reason": f"The workflow baseline branch {base} does not exist.",
            "command": "create or configure the baseline branch",
        }
        return payload
    tracked: list[str] = []
    missing: list[str] = []
    modified: list[str] = []
    for relative in managed_workflow_paths(root):
        stored = git(root, "show", f"{base}:{relative}")
        if stored.returncode != 0:
            missing.append(relative)
            continue
        tracked.append(relative)
        if git(root, "diff", "--quiet", base, "--", relative).returncode != 0:
            modified.append(relative)
    payload["tracked"] = sorted(tracked)
    payload["untracked"] = sorted(missing)
    payload["modified"] = sorted(modified)
    installation = installation_status(root, state)
    if len(missing) == len(managed_workflow_paths(root)):
        status = "missing"
    elif missing:
        status = "partial"
    elif modified or installation["status"] != "current":
        status = "modified"
    else:
        status = "current"
    payload["status"] = status
    current_branch = flow_parallel.branch_name(root)
    head = current_head(root)
    changed = flow_automation.working_tree_paths(root, {f"spec/{LOCK_NAME}"})
    selectable = set(workflow_baseline_commit_paths(root, state))
    outside = sorted(set(changed) - selectable)
    safe = bool(
        status != "current"
        and current_branch == base
        and head == base_head.stdout.strip()
        and not state.get("activeTask")
        and installation["status"] == "current"
        and selectable
        and not outside
    )
    payload["safeToCommit"] = safe
    if status == "current":
        payload["nextAction"] = {
            "reason": "The baseline branch contains the current managed workflow.",
            "command": "continue the active task or create the next task",
        }
    elif safe:
        payload["nextAction"] = {
            "reason": "Only managed workflow baseline files are pending on the baseline branch.",
            "command": (
                "python scripts/rigorbreeze.py automate commit --once "
                f"--workflow-baseline --expected-head {head}"
            ),
        }
    else:
        payload["nextAction"] = {
            "reason": "The baseline branch is missing, partial, modified, or mixed with other changes.",
            "command": "finish active work and isolate workflow files on the baseline branch",
        }
    return payload


def last_closed_task(
    state: dict[str, Any], *, completed_only: bool = False
) -> dict[str, Any]:
    last = state.get("lastClosed") or {}
    if not last or (completed_only and last.get("outcome") != "completed"):
        raise FlowError("no eligible closed task context is available")
    return last


def closure_pending_paths(root: Path, state: dict[str, Any]) -> list[str]:
    expected = set(completed_closure_paths(root, state))
    if not expected:
        return []
    return sorted(
        path
        for path in flow_automation.working_tree_paths(root, {f"spec/{LOCK_NAME}"})
        if path in expected
    )


def closed_context_current(root: Path, state: dict[str, Any]) -> bool:
    last = last_closed_task(state, completed_only=True)
    archive = root / str(last.get("archivePath", ""))
    evidence_file = root / str(last.get("evidencePath", ""))
    if not archive.is_file() or not evidence_file.is_file():
        return False
    digest = sha256_bytes(archive.read_bytes() + b"\0" + evidence_file.read_bytes())
    return bool(
        digest == last.get("closureDigest")
        and project_fingerprint(root) == last.get("projectFingerprint")
    )


def current_task_lifecycle(
    root: Path, state: dict[str, Any]
) -> tuple[str, dict[str, str] | None]:
    active = state.get("activeTask")
    if active and is_git_repo(root):
        try:
            entry = flow_parallel.load_registry(root)["tasks"].get(active["id"], {})
            if entry and flow_parallel.is_integrated(root, entry):
                return (
                    "integrated-unclosed",
                    {
                        "reason": "The task code is integrated but the workflow record is still open.",
                        "command": (
                            "python scripts/rigorbreeze.py archive --outcome reconciled "
                            f"--reason <reason> --expected-head {current_head(root) or '<SHA>'}"
                        ),
                    },
                )
        except flow_parallel.ParallelError:
            pass
    if not active and state.get("lastClosed"):
        pending = closure_pending_paths(root, state)
        if pending:
            last = state["lastClosed"]
            if last.get("outcome") == "completed":
                action = {
                    "reason": "The completed task closure has not been committed.",
                    "command": "python scripts/rigorbreeze.py automate commit --once",
                }
            else:
                action = {
                    "reason": "The historical closure is pending a guarded workflow baseline commit.",
                    "command": "python scripts/rigorbreeze.py status --json",
                }
            return "closure-pending", action
        return "closed", None
    return "active" if active else "idle", None


def command_new(
    root: Path,
    task_id: str,
    title: str,
    risk: str,
    worktree: str | None = None,
    depends_on: list[str] | None = None,
) -> None:
    dependencies = list(dict.fromkeys(depends_on or []))
    if state_path(root).is_file():
        existing_state = load_state(root)
        lifecycle, _ = current_task_lifecycle(root, existing_state)
        if lifecycle in {"integrated-unclosed", "closure-pending"}:
            raise FlowError(
                f"{lifecycle} task must be closed and committed before starting another task"
            )
    if task_id in dependencies:
        raise FlowError("a task cannot depend on itself")
    if dependencies and is_git_repo(root):
        try:
            known_tasks = flow_parallel.load_registry(root)["tasks"]
        except flow_parallel.ParallelError as exc:
            raise FlowError(str(exc)) from exc
        missing = [
            dependency
            for dependency in dependencies
            if dependency not in known_tasks
            and not (spec_root(root) / "archive" / f"{dependency}.md").exists()
        ]
        if missing:
            raise FlowError("missing dependencies: " + ", ".join(missing))
    if worktree == "auto":
        if not is_git_repo(root):
            raise FlowError("automatic worktrees require a Git repository")
        try:
            parallel = load_config(root).get("parallel", {})
            configured_root = str(parallel.get("worktree_root", "")).strip()
            destination_root = (
                Path(configured_root)
                if configured_root and Path(configured_root).is_absolute()
                else root / configured_root
                if configured_root
                else None
            )
            new_root = flow_parallel.create_worktree(
                root,
                task_id,
                str(parallel.get("base_branch", "")).strip() or None,
                destination_root,
            )
        except flow_parallel.ParallelError as exc:
            raise FlowError(str(exc)) from exc
        try:
            command_init(new_root)
            command_new(
                new_root,
                task_id,
                title,
                risk,
                worktree=None,
                depends_on=dependencies,
            )
            flow_parallel.mark_managed_worktree(root, task_id, new_root)
        except Exception:
            flow_parallel.git(root, "worktree", "remove", "--force", str(new_root))
            flow_parallel.git(root, "branch", "-D", f"rigorbreeze/{task_id.lower()}")
            raise
        print(f"worktree: {new_root}")
        return
    state = load_state(root)
    if state.get("activeTask"):
        raise FlowError(f"an active task already exists: {state['activeTask']['id']}")
    if not re.fullmatch(r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+", task_id):
        raise FlowError("task ID must look like TASK-001")
    path = task_path(root, task_id)
    if path.exists() or (spec_root(root) / "archive" / f"{task_id}.md").exists():
        raise FlowError(f"task ID already exists: {task_id}")
    content = task_template(task_id, title, risk).replace(
        "Depends-On: none",
        "Depends-On: " + (", ".join(dependencies) if dependencies else "none"),
    )
    atomic_write(path, content)
    evidence = empty_evidence(task_id)
    save_evidence(root, task_id, evidence)
    state.update(
        {
            "phase": "draft",
            "activeTask": {
                "id": task_id,
                "title": title,
                "risk": risk,
                "createdAt": now_iso(),
                "dependsOn": dependencies,
                "baseBranch": (
                    flow_parallel.default_base_branch(root)
                    if is_git_repo(root)
                    else None
                ),
                "baseSha": current_head(root) if is_git_repo(root) else None,
                "worktree": str(root.resolve()),
                "branch": (
                    flow_parallel.branch_name(root) if is_git_repo(root) else None
                ),
            },
            "red": None,
            "verification": None,
        }
    )
    state["approvals"]["task"] = {"valid": False, "digest": None, "approvedAt": None}
    state["approvals"]["dependencies"] = []
    state["approvals"]["migrations"] = []
    state["approvals"]["overlaps"] = []
    save_state(root, state)
    print(f"created {task_id}")


def command_approve(
    root: Path, kind: str, name: str | None, reason: str | None = None
) -> None:
    state = load_state(root)
    active = state.get("activeTask")
    if kind == "task":
        previously_approved = bool(
            state.get("approvals", {}).get("task", {}).get("approvedAt")
        )
        active["dependsOn"] = declared_dependencies(root, state)
        active["runtimeClaims"] = runtime_claims(root, state)
        active["operationalModes"] = operational_modes(root, state)
        declared_acceptance = set(acceptance_ids(root, state))
        undeclared_modes = sorted(
            requirement
            for requirement in active["operationalModes"].values()
            if requirement not in declared_acceptance
        )
        if undeclared_modes:
            raise FlowError(
                "Operational-Modes reference undeclared acceptance IDs: "
                + ", ".join(undeclared_modes)
            )
        if active.get("risk") == "L2" and active["operationalModes"]:
            missing_modes = sorted(
                {"enabled", "disabled", "unavailable"}
                - active["operationalModes"].keys()
            )
            if missing_modes:
                raise FlowError(
                    "L2 conditional runtime behavior requires operational modes: "
                    + ", ".join(missing_modes)
                )
        if (
            is_git_repo(root)
            and active.get("risk") in {"L1", "L2"}
            and effective_mode(root, None, state) == "enforced"
        ):
            baseline = workflow_baseline_status(root, state)
            installation = installation_status(root, state)
            if baseline["status"] != "current" or installation["status"] != "current":
                raise FlowError(
                    "workflow baseline branch is not current: "
                    f"baseline={baseline['status']}, installation={installation['status']}; "
                    + ", ".join(baseline["untracked"] + baseline["modified"])
                )
        if is_git_repo(root):
            try:
                registry = flow_parallel.load_registry(root)
                current_entry = {
                    **registry["tasks"].get(active["id"], {}),
                    "dependsOn": active["dependsOn"],
                    "runtimeClaims": active["runtimeClaims"],
                }
                registry["tasks"][active["id"]] = current_entry
                flow_parallel.save_registry(root, registry)
                candidate_tasks = {
                    **registry["tasks"],
                    active["id"]: current_entry,
                }
                dependency_issues = flow_parallel.dependency_errors(candidate_tasks)
                if dependency_issues:
                    raise FlowError("; ".join(dependency_issues))
                if (
                    active.get("dependsOn")
                    and flow_parallel.task_readiness(
                        root, current_entry, candidate_tasks
                    )
                    != "ready"
                ):
                    raise FlowError(
                        "task dependencies must be integrated before approval"
                    )
                runtime_conflicts = flow_parallel.runtime_claim_conflicts(
                    candidate_tasks, active["id"], active["runtimeClaims"]
                )
                if runtime_conflicts:
                    first = runtime_conflicts[0]
                    raise FlowError(
                        f"runtime claim {first['claim']} is owned by active task "
                        f"{first['taskId']}; release or change the shared resource"
                    )
                base = active.get("baseBranch")
                if base:
                    base_head = git(root, "rev-parse", base)
                    if base_head.returncode != 0:
                        raise FlowError(f"baseline branch is missing: {base}")
                    if (
                        git(
                            root, "merge-base", "--is-ancestor", base, "HEAD"
                        ).returncode
                        != 0
                    ):
                        raise FlowError(
                            "task branch must include the latest baseline before approval"
                        )
                    active["baseSha"] = base_head.stdout.strip()
            except flow_parallel.ParallelError as exc:
                raise FlowError(str(exc)) from exc
        path = task_path(root, active["id"])
        content = path.read_text(encoding="utf-8")
        if any(token in content for token in PLACEHOLDERS):
            raise FlowError("task still contains placeholder content")
        missing = [
            section for section in REQUIRED_TASK_SECTIONS if section not in content
        ]
        if missing:
            raise FlowError("task is missing required sections: " + ", ".join(missing))
        scopes = allowed_scope(root, state)
        validate_scope_entries(root, scopes)
        acceptance_ids(root, state)
        scope = task_scope_status(root, state)
        if scope["status"] == "violated":
            raise FlowError(
                "task changes are outside the approved scope: "
                + ", ".join(scope["outOfScope"])
            )
        config = load_config(root)
        source_roots = configured_paths(config, "source_paths", ["src", "app", "lib"])
        test_roots = configured_paths(
            config, "test_paths", ["tests", "test", "src/test"]
        )
        production_changes = [
            relative
            for relative in task_change_paths(root, state)
            if path_allowed(relative, scopes)
            and path_under(relative, source_roots)
            and not path_under(relative, test_roots)
        ]
        if production_changes:
            if previously_approved:
                raise FlowError(
                    "production changes already exist after approval; restore the "
                    "approved contract and finish, or revert production changes before "
                    "amending the same outcome. Create a dependent task for a new user "
                    "outcome or acceptance condition: " + ", ".join(production_changes)
                )
            raise FlowError(
                "production changes exist before task approval and cannot become the "
                "RED baseline: " + ", ".join(production_changes)
            )
        try:
            overlap = flow_parallel.overlapping_task(
                root,
                active["id"],
                scopes,
                [
                    item.get("taskId")
                    for item in state["approvals"].get("overlaps", [])
                    if item.get("taskId")
                ],
            )
        except flow_parallel.ParallelError as exc:
            raise FlowError(str(exc)) from exc
        if overlap:
            other_id, left, right = overlap
            raise FlowError(
                f"allowed scope {left} overlaps active task {other_id} scope {right}; "
                "split the scope, add a dependency, or explicitly approve the overlap"
            )
        state["approvals"]["task"] = {
            "valid": True,
            "digest": task_digest(root, state),
            "approvedAt": now_iso(),
        }
        state["phase"] = "approved"
        state["red"] = None
        state["verification"] = None
        active = active_task(state)
        evidence = load_evidence(root, active["id"])
        evidence["baseline"] = {
            "taskDigest": task_digest(root, state),
            "head": current_head(root) if is_git_repo(root) else None,
            "projectFingerprint": project_fingerprint(root),
            "configDigest": config_digest(root),
            "workingTreePaths": working_tree_paths(root),
            "workingTreeDigests": {
                relative: sha256_bytes((root / relative).read_bytes())
                for relative in working_tree_paths(root)
                if (root / relative).is_file()
            },
            "approvedAt": now_iso(),
        }
        save_evidence(root, active["id"], evidence)
    elif kind == "overlap":
        if not name or not reason:
            raise FlowError("overlap approval requires --name and --reason")
        if name == active["id"]:
            raise FlowError("a task cannot approve overlap with itself")
        state["approvals"].setdefault("overlaps", []).append(
            {"taskId": name, "reason": redact(reason), "approvedAt": now_iso()}
        )
    else:
        if not name:
            raise FlowError(f"{kind} approval requires --name")
        bucket = "dependencies" if kind == "dependency" else "migrations"
        state["approvals"][bucket].append({"name": name, "approvedAt": now_iso()})
    save_state(root, state)
    print(f"approved {kind}")


def command_status(
    root: Path, json_output: bool = False, all_worktrees: bool = False
) -> None:
    if all_worktrees:
        if not is_git_repo(root):
            raise FlowError("status --all requires a Git repository")
        try:
            payload = flow_parallel.aggregate(root)
        except flow_parallel.ParallelError as exc:
            raise FlowError(str(exc)) from exc
        payload["workflowVersion"] = VERSION
        state = (
            load_state(root)
            if state_path(root).is_file() or legacy_state_path(root).is_file()
            else None
        )
        payload["installation"] = installation_status(root, state)
        payload["workflowBaseline"] = (
            workflow_baseline_status(root, state) if state else None
        )
        try:
            for item in payload["tasks"]:
                item["automation"] = flow_automation.action_summary(
                    flow_automation.latest_action(root, item.get("taskId"))
                )
        except flow_automation.AutomationError as exc:
            raise FlowError(str(exc)) from exc
        if json_output:
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            return
        if not payload["tasks"]:
            print("no registered parallel tasks")
        else:
            for item in payload["tasks"]:
                print(
                    f"{item['taskId']}: {item.get('phase')} / "
                    f"{item.get('readiness')} / {item.get('branch')} / "
                    f"{item.get('worktree')}"
                )
        for issue in payload["issues"]:
            print(f"issue: {issue}")
        cleanup = payload["cleanup"]
        if any(cleanup.values()):
            print(
                "cleanup: "
                f"{len(cleanup['removableWorktrees'])} removable worktree(s), "
                f"{len(cleanup['retainedWorktrees'])} retained worktree(s), "
                f"{len(cleanup['retainedBranches'])} retained branch(es)"
            )
        return
    state = load_state(root)
    refresh_approval(root, state)
    active = state.get("activeTask")
    approval = state["approvals"]["task"]
    approval_valid_now = bool(approval.get("valid"))
    verification = (
        "current"
        if active and approval_valid_now and verification_current(root, state)
        else "missing/stale"
    )
    mode = load_config(root).get("policy", {}).get("local_mode", "advisory")
    full_profile = (
        "current"
        if active and approval_valid_now and full_profile_current(root, state)
        else "missing/stale"
    )
    lifecycle, lifecycle_action = current_task_lifecycle(root, state)
    action = lifecycle_action or next_action(
        root, state, approval_valid_now, verification, full_profile
    )
    scope = task_scope_status(root, state)
    payload = {
        "phase": state.get("phase"),
        "localMode": mode,
        "activeTask": active["id"] if active else None,
        "approval": "valid" if approval_valid_now else "invalid",
        "verification": verification,
        "fullProfile": full_profile,
        "scope": scope,
        "lifecycle": lifecycle,
        "nextAction": action,
        "installation": installation_status(root, state),
        "workflowBaseline": workflow_baseline_status(root, state),
    }
    if is_git_repo(root):
        try:
            payload["automation"] = flow_automation.action_summary(
                flow_automation.latest_action(
                    root, active.get("id") if isinstance(active, dict) else None
                )
            )
        except flow_automation.AutomationError as exc:
            raise FlowError(str(exc)) from exc
    else:
        payload["automation"] = None
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    print(f"phase: {payload['phase']}")
    print(f"local mode: {payload['localMode']}")
    print(f"active task: {payload['activeTask'] or 'none'}")
    print(f"approval: {payload['approval']}")
    print(f"verification: {payload['verification']}")
    print(f"full profile: {payload['fullProfile']}")
    print(f"next action: {action['command']} ({action['reason']})")


def command_red(
    root: Path,
    requirement: str,
    expect_pattern: str,
    tests: list[str],
    command: list[str],
) -> None:
    state = load_state(root)
    if not approval_valid(root, state):
        save_state(root, state)
        raise FlowError("task approval is missing or invalid")
    active = active_task(state)
    declared = acceptance_ids(root, state)
    if requirement not in declared:
        raise FlowError(
            f"RED requirement {requirement} is not declared in the task acceptance criteria"
        )
    evidence = load_evidence(root, active["id"])
    baseline = evidence.get("baseline") or {}
    config = load_config(root)
    test_roots = configured_paths(config, "test_paths", ["tests", "test", "src/test"])
    source_roots = configured_paths(config, "source_paths", ["src", "app", "lib"])
    if tests:
        invalid_tests = [
            relative for relative in tests if not path_under(relative, test_roots)
        ]
        if invalid_tests:
            raise FlowError(
                "RED test files are outside configured test paths: "
                + ", ".join(invalid_tests)
            )
    current_paths = working_tree_paths(root)
    baseline_paths = set(baseline.get("workingTreePaths", []))
    baseline_digests = baseline.get("workingTreeDigests", {})
    changed_after_approval: list[str] = []
    for relative in current_paths:
        path = root / relative
        digest = sha256_bytes(path.read_bytes()) if path.is_file() else None
        if relative not in baseline_paths or baseline_digests.get(relative) != digest:
            changed_after_approval.append(relative)
    production_changes = [
        relative
        for relative in changed_after_approval
        if path_under(relative, source_roots) and not path_under(relative, test_roots)
    ]
    if production_changes:
        raise FlowError(
            "production code changed before RED was observed: "
            + ", ".join(production_changes)
        )
    if not tests and active["risk"] in {"L1", "L2"}:
        raise FlowError(f"{active['risk']} RED requires at least one --test file")
    if (
        not tests
        and active["risk"] != "Emergency"
        and effective_mode(root, None, state) == "enforced"
    ):
        raise FlowError("enforced RED requires at least one --test file")
    normalized_command = command[1:] if command and command[0] == "--" else command
    if tests and any(
        not any(
            relative == argument or relative in argument
            for argument in normalized_command
        )
        for relative in tests
    ):
        raise FlowError("RED command must execute every declared --test file")
    test_digests = {relative: test_file_digest(root, relative) for relative in tests}
    result = run_command(command, root)
    output = ((result.stdout or "") + (result.stderr or "")).strip()
    if result.returncode == 0:
        raise FlowError("RED command passed; expected an observed failure")
    if not re.search(expect_pattern, output, re.I | re.M):
        raise FlowError("RED output did not match the expected failure pattern")
    record = {
        "requirement": requirement,
        "command": [
            redact(part)
            for part in (command[1:] if command and command[0] == "--" else command)
        ],
        "exitCode": result.returncode,
        "expectedPattern": expect_pattern,
        "testDigests": test_digests,
        "summary": redact(output[-2000:]),
        "taskDigest": task_digest(root, state),
        "projectFingerprint": project_fingerprint(root),
        "head": current_head(root) if is_git_repo(root) else None,
        "observedAt": now_iso(),
    }
    evidence["red"].append(record)
    evidence["tddChain"].append(
        {"requirement": requirement, "red": record, "green": None}
    )
    save_evidence(root, active["id"], evidence)
    state["red"] = record
    state["phase"] = "red"
    save_state(root, state)
    print("RED observed and recorded")


def command_verify_profile(root: Path, profile: str, requested_mode: str | None) -> int:
    state = load_state(root)
    if not approval_valid(root, state):
        save_state(root, state)
        raise FlowError("task approval is missing or invalid")
    active = active_task(state)
    mode = effective_mode(root, requested_mode, state)
    config = load_config(root)
    if profile not in {"affected", "full"}:
        raise FlowError("configured verification profile must be affected or full")
    ensure_scope_current(root, state)
    if active["risk"] in {"L1", "L2", "Emergency"}:
        if not state.get("red"):
            raise FlowError("current RED or incident reproduction evidence is required")
        if not test_chain_current(root, state):
            raise FlowError("RED test changed after observation; observe RED again")
    destructive = destructive_migrations(root)
    if destructive:
        raise FlowError("destructive migration detected: " + ", ".join(destructive))
    evidence = load_evidence(root, active["id"])
    check_ids = list(config.get("profiles", {}).get(profile, []))
    if mode == "enforced" and not check_ids:
        raise FlowError(f"enforced {profile} profile must declare at least one check")
    if profile == "full":
        policy_issues = l2_full_profile_issues(root, state, check_ids, config)
        if policy_issues:
            raise FlowError(
                "L2 full profile does not satisfy change-derived policy: "
                + "; ".join(policy_issues)
            )
    checks = config["_checks"]
    records: list[dict[str, Any]] = []
    executions: dict[
        tuple[tuple[str, ...], str, tuple[tuple[str, str], ...], int],
        tuple[subprocess.CompletedProcess[str], int, str],
    ] = {}
    passed = True
    for check_id in check_ids:
        check = checks.get(check_id)
        if not check:
            record = {
                "checkId": check_id,
                "category": check_category(check_id),
                "profile": profile,
                "passed": False,
                "mode": mode,
                "error": "check is required by profile but not configured",
                "recordedAt": now_iso(),
            }
            records.append(record)
            evidence["checkRuns"].append(record)
            passed = False
            continue
        risks = check.get("risks", ["L0", "L1", "L2", "Emergency"])
        if active["risk"] not in risks:
            record = {
                "checkId": check_id,
                "category": check_category(check_id),
                "profile": profile,
                "passed": True,
                "mode": mode,
                "notApplicable": {
                    "reason": f"check does not apply to risk {active['risk']}",
                    "approvedBy": "rigorbreeze policy",
                    "scope": active["risk"],
                },
                "recordedAt": now_iso(),
            }
            records.append(record)
            evidence["checkRuns"].append(record)
            continue
        resolved_cwd = resolve_project_path(
            root, check.get("cwd", "."), f"check {check_id} cwd"
        )
        effective_env = {**os.environ, **check.get("env", {})}
        timeout = check.get("timeout", 900)
        signature = (
            tuple(check["command"]),
            str(resolved_cwd),
            tuple(sorted(effective_env.items())),
            timeout,
        )
        reused_from: str | None = None
        cached = executions.get(signature)
        if cached:
            result, _original_duration, reused_from = cached
            duration_ms = 0
        else:
            started = time.monotonic()
            try:
                result = subprocess.run(
                    check["command"],
                    cwd=resolved_cwd,
                    env=effective_env,
                    text=True,
                    encoding="utf-8",
                    capture_output=True,
                    timeout=timeout,
                )
            except FileNotFoundError as exc:
                result = subprocess.CompletedProcess(
                    check["command"], 127, "", str(exc)
                )
            except subprocess.TimeoutExpired as exc:
                timeout_message = f"timed out after {timeout} seconds"
                result = subprocess.CompletedProcess(
                    check["command"],
                    124,
                    subprocess_text(exc.stdout),
                    "\n".join(
                        part
                        for part in (subprocess_text(exc.stderr), timeout_message)
                        if part
                    ),
                )
            duration_ms = round((time.monotonic() - started) * 1000)
            executions[signature] = (result, duration_ms, check_id)
        output = ((result.stdout or "") + (result.stderr or "")).strip()
        check_passed = result.returncode == 0
        report: dict[str, Any] | None = None
        if check_passed:
            try:
                report = report_record(root, check.get("report"))
            except FlowError as exc:
                check_passed = False
                output = f"{output}\n{exc}".strip()
        fingerprint = project_fingerprint(root)
        artifacts: list[dict[str, Any]] = []
        if check_passed:
            try:
                artifacts = record_artifacts(
                    root,
                    evidence,
                    check_id,
                    check.get("artifacts", []),
                    fingerprint,
                    task_digest(root, state),
                )
            except FlowError as exc:
                check_passed = False
                output = f"{output}\n{exc}".strip()
        record = {
            "checkId": check_id,
            "category": check_category(check_id),
            "profile": profile,
            "mode": mode,
            "command": [redact(part) for part in check["command"]],
            "exitCode": result.returncode,
            "passed": check_passed,
            "durationMs": duration_ms,
            "summary": redact(output[-2000:]),
            "report": report,
            "artifacts": [item["sha256"] for item in artifacts],
            "taskDigest": task_digest(root, state),
            "projectFingerprint": fingerprint,
            "head": current_head(root) if is_git_repo(root) else None,
            "recordedAt": now_iso(),
        }
        if reused_from:
            record["reusedFromCheckId"] = reused_from
        records.append(record)
        evidence["checkRuns"].append(record)
        passed = passed and check_passed
    fingerprint = project_fingerprint(root)
    verification = {
        "toolVersion": TOOL_VERSION,
        "profile": profile,
        "configured": True,
        "mode": mode,
        "checks": [record["checkId"] for record in records],
        "passed": passed,
        "taskDigest": task_digest(root, state),
        "projectFingerprint": fingerprint,
        "configDigest": config_digest(root),
        "head": current_head(root) if is_git_repo(root) else None,
        "verifiedAt": now_iso(),
    }
    evidence["verification"] = verification
    evidence["verifications"].append(verification)
    if passed and state.get("red"):
        if profile == "full":
            current_digest = task_digest(root, state)
            for chain in evidence["tddChain"]:
                red = chain.get("red") or {}
                if red.get("taskDigest") == current_digest and red_record_tests_current(
                    root, red
                ):
                    chain["green"] = verification
        else:
            for chain in reversed(evidence["tddChain"]):
                if chain.get("requirement") == state["red"].get(
                    "requirement"
                ) and not chain.get("green"):
                    chain["green"] = verification
                    break
    save_evidence(root, active["id"], evidence)
    state["verification"] = verification
    if not passed:
        state["phase"] = "implementing"
    elif any(
        record.get("kind") == "governance"
        for record in current_structured_records(root, state, "release")
    ):
        state["phase"] = "release-ready"
    elif current_structured_records(root, state, "acceptance"):
        state["phase"] = "accepted"
    else:
        state["phase"] = "verified"
    save_state(root, state)
    if passed:
        print(f"{profile} profile passed ({mode})")
        return 0
    if mode == "advisory":
        print(f"{profile} profile has failures (advisory; not blocking)")
        return 0
    print(f"{profile} profile failed (enforced)")
    return 1


def command_evidence_add(
    root: Path,
    section: str,
    kind: str,
    file: str | None,
    field_values: list[str],
) -> None:
    state = load_state(root)
    if not approval_valid(root, state) or not verification_current(root, state):
        save_state(root, state)
        raise FlowError("fresh verification is required before structured evidence")
    active = active_task(state)
    evidence = load_evidence(root, active["id"])
    fingerprint = project_fingerprint(root)
    current_artifacts = [
        artifact
        for artifact in evidence.get("artifacts", [])
        if artifact.get("taskDigest") == task_digest(root, state)
        and artifact.get("projectFingerprint") == fingerprint
    ]
    fields = parse_fields(field_values)
    record: dict[str, Any] = {
        "kind": kind,
        "fields": fields,
        "taskDigest": task_digest(root, state),
        "projectFingerprint": fingerprint,
        "head": current_head(root) if is_git_repo(root) else None,
        "artifactDigests": [artifact["sha256"] for artifact in current_artifacts],
        "recordedAt": now_iso(),
    }
    evidence_content: Any = None
    if file:
        path = (root / file).resolve()
        try:
            path.relative_to(root.resolve())
        except ValueError as exc:
            raise FlowError(f"evidence file escapes project root: {file}") from exc
        if not path.is_file():
            raise FlowError(f"missing evidence file: {file}")
        record.update(
            {
                "path": Path(file).as_posix(),
                "sha256": sha256_bytes(path.read_bytes()),
                "size": path.stat().st_size,
            }
        )
        if path.suffix.lower() == ".json":
            try:
                evidence_content = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise FlowError(f"invalid evidence JSON: {file}: {exc}") from exc
            evidence_status = (
                evidence_content.get("status")
                if isinstance(evidence_content, dict)
                else None
            )
            operation_result_status = (
                section == "release"
                and kind == "operation-result"
                and str(evidence_status).lower() in {"paused", "failed", "succeeded"}
            )
            if (
                evidence_status
                and not operation_result_status
                and str(evidence_status).lower()
                not in {
                    "passed",
                    "pass",
                    "ok",
                    "success",
                }
            ):
                raise FlowError(f"evidence report does not declare passed: {file}")
    if section == "acceptance":
        required_by_kind = {
            "playwright": {"status", "environment"},
            "runtime": {"status", "environment"},
            "design": {"status", "designVersion", "reviewer"},
            "product-review": {"status", "reviewer"},
            "review": {"status", "reviewer"},
            "device": {"status", "environment", "device", "appVersion"},
            "wechat-device": {"status", "environment", "device", "appVersion"},
        }
        required = required_by_kind.get(kind)
        if required is None:
            raise FlowError(
                "acceptance evidence kind must be playwright, runtime, design, "
                "product-review, review, device, or wechat-device"
            )
        missing = sorted(required - fields.keys())
        if not file or missing:
            raise FlowError(
                f"{kind} evidence requires a real file and fields: "
                + ", ".join(missing)
            )
        if fields["status"].lower() != "passed":
            raise FlowError(f"{kind} evidence status must be passed")
        if state.get("phase") != "release-ready":
            state["phase"] = "accepted"
    elif section == "release":
        required_by_kind = {
            "governance": RELEASE_GOVERNANCE_FIELDS,
            "migration": MIGRATION_EVIDENCE_FIELDS,
            "security": SECURITY_EVIDENCE_FIELDS,
            "operation-plan": set(),
            "operation-result": set(),
        }
        required = required_by_kind.get(kind)
        if required is None:
            raise FlowError(
                "release evidence kind must be governance, migration, security, "
                "operation-plan, or operation-result"
            )
        missing = sorted(required - fields.keys())
        if missing:
            raise FlowError(
                f"release {kind} evidence is missing fields: " + ", ".join(missing)
            )
        if (
            kind
            in {
                "migration",
                "security",
                "operation-plan",
                "operation-result",
            }
            and not file
        ):
            raise FlowError(f"release {kind} evidence requires a real report file")
        artifact_digests = {artifact["sha256"] for artifact in current_artifacts}
        if kind == "operation-plan":
            record["operation"] = validate_operation_plan(
                evidence_content,
                head=record["head"],
                artifact_digests=artifact_digests,
            )
        elif kind == "operation-result":
            if not any(
                existing.get("kind") == "operation-plan"
                for existing in current_structured_records(root, state, "release")
            ):
                raise FlowError("operation-result requires a current operation-plan")
            record["operation"] = validate_operation_result(
                evidence_content,
                head=record["head"],
                artifact_digests=artifact_digests,
            )
        if kind == "governance":
            state["phase"] = "release-ready"
    elif section != "artifacts":
        raise FlowError(f"unknown evidence section: {section}")
    evidence[section].append(record)
    save_evidence(root, active["id"], evidence)
    save_state(root, state)
    print(f"recorded {section}/{kind}")
    if kind == "operation-result" and record["operation"]["status"] in {
        "paused",
        "failed",
    }:
        print(f"safe resume action: {record['operation']['resumeAction']}")


def command_retro(
    root: Path,
    *,
    json_output: bool,
    confirm: bool,
    rework_reason: str | None,
    exceptions: str | None,
    workflow_impact: str | None,
) -> None:
    state = load_state(root)
    if not approval_valid(root, state) or not verification_current(root, state):
        raise FlowError("fresh verification is required before retrospective")
    summary = practice_summary(root, state)
    if confirm:
        missing = [
            name
            for name, value in (
                ("rework reason", rework_reason),
                ("exceptions judgment", exceptions),
                ("workflow impact", workflow_impact),
            )
            if not value
        ]
        if missing:
            raise FlowError("retro confirmation is missing: " + ", ".join(missing))
        active = active_task(state)
        evidence = load_evidence(root, active["id"])
        practice = evidence.setdefault("practice", {})
        practice["summary"] = summary
        normalized_exceptions = (exceptions or "").strip().casefold()
        evolution_candidate = (
            rework_reason == "workflow"
            or workflow_impact == "hurt"
            or normalized_exceptions
            not in {"none", "no", "n/a", "无", "没有", "无异常"}
        )
        practice["confirmation"] = {
            "reworkReason": rework_reason,
            "exceptions": redact(exceptions or ""),
            "workflowImpact": workflow_impact,
            "evolutionCandidate": evolution_candidate,
            "summaryDigest": summary["summaryDigest"],
            "taskDigest": task_digest(root, state),
            "projectFingerprint": project_fingerprint(root),
            "confirmedAt": now_iso(),
        }
        save_evidence(root, active["id"], evidence)
        if evolution_candidate:
            print(
                "retrospective confirmed; evolution candidate recorded. "
                "Review after a second similar ordinary occurrence, or immediately "
                "for a high-risk gate escape. When that threshold is met, enter: "
                "$rigorbreeze 汇总这个项目的演进候选"
            )
        else:
            print("retrospective confirmed")
        return
    if json_output:
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return
    print(f"task: {summary['taskId']}")
    print(f"verification runs: {summary['verificationRuns']}")
    print(f"check runs: {summary['checkRuns']}")
    print(f"failed checks: {', '.join(summary['failedChecks']) or 'none'}")
    print(f"potential bypasses: {', '.join(summary['potentialBypasses']) or 'none'}")
    print(
        "first acceptance passed: "
        + (
            "unknown"
            if summary["firstAcceptancePassed"] is None
            else str(summary["firstAcceptancePassed"]).lower()
        )
    )
    print(f"estimated rework seconds: {summary['estimatedReworkSeconds']}")


def command_check(root: Path, gate: str, requested_mode: str | None = None) -> None:
    state = load_state(root)
    if refresh_approval(root, state):
        save_state(root, state)
    active = state.get("activeTask")
    closed = None if active else (state.get("lastClosed") or None)
    if not active and not (
        gate == "merge" and closed and closed.get("outcome") == "completed"
    ):
        active_task(state)
    if gate == "commit":
        if not is_git_repo(root):
            raise FlowError("commit gate requires a Git repository")
        paths = staged_files(root)
        if not paths:
            raise FlowError("commit gate requires staged files")
        secrets = [path for path in paths if is_secret_path(path)]
        if secrets:
            raise FlowError("secret paths are forbidden: " + ", ".join(secrets))
        secret_content, secret_exemptions = secret_content_scan(root, paths)
        if secret_content:
            raise FlowError(
                "secret-like content detected: " + ", ".join(secret_content)
            )
        if secret_exemptions:
            print(
                "synthetic secret fixture exemptions: " + ", ".join(secret_exemptions)
            )
        dependencies = [path for path in paths if is_dependency_path(path)]
        if dependencies and not state["approvals"]["dependencies"]:
            raise FlowError(
                "dependency approval is required: " + ", ".join(dependencies)
            )
        migrations = [
            path for path in paths if is_configured_migration_path(root, path)
        ]
        if migrations and not state["approvals"]["migrations"]:
            raise FlowError("migration approval is required: " + ", ".join(migrations))
        ensure_scope_current(root, state)
        out_of_scope = [
            path
            for path in paths
            if not task_owned_path(path, state, allowed_scope(root, state))
        ]
        if out_of_scope:
            raise FlowError(
                "staged files are outside approved scope: " + ", ".join(out_of_scope)
            )
        if not configured_verification_current(root, state):
            raise FlowError("configured affected/full verification is missing or stale")
    elif gate == "merge":
        if active:
            ensure_delivery_quality(root, state)
        elif not closed_context_current(root, state):
            raise FlowError("closed task evidence changed after archive")
        elif not closed.get("verification"):
            raise FlowError("closed task has no delivery-quality verification")
    elif gate == "release":
        ensure_release(root, state)
    else:
        raise FlowError(f"unknown gate: {gate}")
    save_state(root, state)
    print(f"check {gate}: passed")


def automation_context_task(state: dict[str, Any]) -> dict[str, Any]:
    active = state.get("activeTask")
    if active:
        return active
    last = last_closed_task(state, completed_only=True)
    return {
        "id": last["id"],
        "title": last.get("title") or last["id"],
        "risk": last.get("risk"),
        "baseBranch": last.get("baseBranch"),
        "baseSha": last.get("baseSha"),
    }


def context_task_paths(root: Path, state: dict[str, Any]) -> list[str]:
    if state.get("activeTask"):
        return automation_task_paths(root, state)
    last = last_closed_task(state, completed_only=True)
    if not closed_context_current(root, state):
        raise FlowError("closed task contract or evidence changed after archive")
    scopes = list(last.get("allowedScope", []))
    closure = {
        str(last.get("sourcePath")),
        str(last.get("archivePath")),
        str(last.get("evidencePath")),
    }
    return sorted(
        relative
        for relative in flow_automation.working_tree_paths(root, {f"spec/{LOCK_NAME}"})
        if relative in closure or path_allowed(relative, scopes)
    )


def context_automation_values(root: Path, state: dict[str, Any]) -> dict[str, str]:
    if state.get("activeTask"):
        return automation_values(root, state)
    last = last_closed_task(state, completed_only=True)
    artifacts = last.get("artifacts", [])
    return {
        "task_id": str(last["id"]),
        "title": str(last.get("title") or last["id"]),
        "branch": flow_parallel.branch_name(root) or str(last.get("branch") or ""),
        "base": str(last.get("baseBranch") or ""),
        "head": current_head(root) or "",
        "artifact_sha256": ",".join(
            sorted(
                str(record["sha256"]) for record in artifacts if record.get("sha256")
            )
        ),
    }


def context_automation_input(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    if state.get("activeTask"):
        return automation_input(root, state)
    last = last_closed_task(state, completed_only=True)
    values = context_automation_values(root, state)
    verification = json.dumps(
        last.get("verification"), ensure_ascii=False, sort_keys=True
    ).encode()
    evidence_file = root / str(last["evidencePath"])
    return {
        "head": values["head"],
        "taskDigest": last.get("taskDigest"),
        "evidenceDigest": sha256_bytes(evidence_file.read_bytes()),
        "verificationDigest": sha256_bytes(verification),
        "projectFingerprint": last.get("projectFingerprint"),
        "artifactSha256": values["artifact_sha256"] or None,
        "closureDigest": last.get("closureDigest"),
    }


def check_closed_commit(root: Path, state: dict[str, Any], selected: list[str]) -> None:
    if not closed_context_current(root, state):
        raise FlowError("closed task contract or evidence changed after archive")
    staged = staged_files(root)
    outside = sorted(set(staged) - set(selected))
    if outside:
        raise FlowError(
            "staged files are outside the closed task: " + ", ".join(outside)
        )
    secrets = [path for path in staged if is_secret_path(path)]
    secrets.extend(secret_content_paths(root, staged))
    if secrets:
        raise FlowError(
            "secret material is forbidden: " + ", ".join(sorted(set(secrets)))
        )


def automate_workflow_baseline_commit(
    root: Path,
    state: dict[str, Any],
    config: dict[str, Any],
    expected_head: str | None,
) -> None:
    if state.get("activeTask"):
        raise FlowError("workflow baseline commit requires no active business task")
    head = current_head(root) or ""
    if not expected_head or expected_head != head:
        raise FlowError(
            f"workflow baseline expected HEAD {expected_head or '<missing>'}, found {head}"
        )
    base = baseline_branch(root, state)
    if not base or flow_parallel.branch_name(root) != base:
        raise FlowError("workflow baseline commit must run on the baseline branch")
    installation = installation_status(root, state)
    if installation["status"] != "current":
        raise FlowError(
            f"workflow installation must be current: {installation['status']}"
        )
    load_config(root)
    agents = (root / "AGENTS.md").read_text(encoding="utf-8", errors="replace")
    if flow_state.AGENTS_START not in agents or flow_state.AGENTS_END not in agents:
        raise FlowError("managed RigorBreeze AGENTS marker is missing")
    selected = workflow_baseline_commit_paths(root, state)
    changed = flow_automation.working_tree_paths(root, {f"spec/{LOCK_NAME}"})
    outside = sorted(set(changed) - set(selected))
    if not selected:
        raise FlowError("workflow baseline commit found no managed changes")
    if outside:
        raise FlowError(
            "workflow baseline commit found non-workflow changes: " + ", ".join(outside)
        )
    secrets = [path for path in selected if is_secret_path(path)]
    secrets.extend(secret_content_paths(root, selected))
    if secrets:
        raise FlowError(
            "workflow baseline commit blocked secret material: "
            + ", ".join(sorted(set(secrets)))
        )
    staged_before = staged_files(root)
    unrelated_staged = sorted(set(staged_before) - set(selected))
    if unrelated_staged:
        raise FlowError(
            "workflow baseline commit will not alter unrelated staged files: "
            + ", ".join(unrelated_staged)
        )

    def check() -> None:
        staged = staged_files(root)
        if sorted(staged) != sorted(selected):
            raise FlowError("workflow baseline staged set changed during validation")
        load_config(root)
        if installation_status(root, state)["status"] != "current":
            raise FlowError("workflow installation changed during baseline validation")

    flow_automation.commit_action(
        root,
        task_id="WORKFLOW-BASELINE",
        files=selected,
        staged_before=staged_before,
        message=f"Establish RigorBreeze v{TOOL_VERSION} workflow baseline",
        inputs={
            "head": head,
            "workflowBaseline": True,
            "managedFiles": selected,
            "configDigest": config_digest(root),
        },
        target={"branch": base},
        check=check,
        redact=redact,
        authorization_mode="user-once",
    )


def automate_commit(
    root: Path,
    state: dict[str, Any],
    config: dict[str, Any],
    authorization_mode: str = "standing",
) -> None:
    automation = (
        config.get("automation", {})
        if authorization_mode == "user-once"
        else flow_automation.require_level(config, "commit")
    )
    if not is_git_repo(root):
        raise FlowError("automatic commit requires a Git repository")
    active = automation_context_task(state)
    if flow_automation.recover_interrupted_commit(root, active["id"]):
        print("automate commit: recovered completed commit")
        return
    changed = flow_automation.working_tree_paths(root, {f"spec/{LOCK_NAME}"})
    selected = context_task_paths(root, state)
    secrets = [path for path in changed if is_secret_path(path)]
    secrets.extend(secret_content_paths(root, changed))
    if secrets:
        raise FlowError(
            "automatic commit blocked secret material: " + ", ".join(secrets)
        )
    if state.get("activeTask"):
        ensure_scope_current(root, state)
    elif not closed_context_current(root, state):
        raise FlowError("closed task contract or evidence changed after archive")
    outside = sorted(set(changed) - set(selected))
    if outside:
        raise FlowError(
            "automatic commit found changes outside the task-owned files: "
            + ", ".join(outside)
        )
    if not selected:
        raise FlowError("automatic commit found no task-owned changes")
    staged_before = staged_files(root)
    unrelated_staged = sorted(set(staged_before) - set(selected))
    if unrelated_staged:
        raise FlowError(
            "automatic commit will not alter unrelated staged files: "
            + ", ".join(unrelated_staged)
        )
    approvals = (
        state["approvals"]
        if state.get("activeTask")
        else (state.get("lastClosed") or {}).get("approvals", {})
    )
    dependencies = [path for path in selected if is_dependency_path(path)]
    if dependencies and not approvals.get("dependencies"):
        raise FlowError("automatic commit requires dependency approval")
    migrations = [path for path in selected if is_configured_migration_path(root, path)]
    if migrations and not approvals.get("migrations"):
        raise FlowError("automatic commit requires migration approval")
    values = context_automation_values(root, state)
    message = str(automation.get("commit_message", "{task_id}: {title}")).format_map(
        values
    )
    outcome = flow_automation.commit_action(
        root,
        task_id=active["id"],
        files=selected,
        staged_before=staged_before,
        message=message,
        inputs=context_automation_input(root, state),
        target={"branch": flow_parallel.branch_name(root)},
        check=(
            (lambda: command_check(root, "commit", "enforced"))
            if state.get("activeTask")
            else (lambda: check_closed_commit(root, state, selected))
        ),
        redact=redact,
        authorization_mode=authorization_mode,
    )
    if outcome == "recovered":
        print("automate commit: recovered completed commit")


def automate_push(
    root: Path,
    state: dict[str, Any],
    config: dict[str, Any],
    *,
    authorization_mode: str = "standing",
    remote_override: str | None = None,
    branch_override: str | None = None,
    expected_head: str | None = None,
) -> None:
    one_time = authorization_mode == "user-once"
    automation = (
        config.get("automation", {})
        if one_time
        else flow_automation.require_level(config, "push")
    )
    current_branch = flow_parallel.branch_name(root) or ""
    branch = branch_override if one_time else current_branch
    protected = set(automation.get("protected_branches", ["main", "master"]))
    if one_time:
        if not remote_override:
            raise FlowError("one-time push requires an explicit remote")
        if remote_override.startswith("-") or re.search(r"\s", remote_override):
            raise FlowError("one-time push remote must be an explicit Git remote name")
        if not branch or branch != current_branch:
            raise FlowError("one-time push branch must equal the current branch")
        valid_branch = git(root, "check-ref-format", "--branch", branch)
        if valid_branch.returncode != 0:
            raise FlowError("one-time push branch is not a valid Git branch name")
        head = current_head(root) or ""
        if not expected_head or expected_head != head:
            raise FlowError(
                f"one-time push expected HEAD {expected_head or '<missing>'}, found {head}"
            )
        if context_task_paths(root, state):
            raise FlowError(
                "one-time push does not commit pending changes; authorize and run "
                "automate commit --once first"
            )
    elif branch in protected or not branch.startswith("rigorbreeze/"):
        raise FlowError("automatic push is limited to rigorbreeze/<task-id> branches")
    if not one_time and context_task_paths(root, state):
        automate_commit(root, state, config, authorization_mode)
    if state.get("activeTask"):
        ensure_scope_current(root, state)
    elif not closed_context_current(root, state):
        raise FlowError("closed task contract or evidence changed after archive")
    if one_time and branch in protected:
        if state.get("activeTask"):
            ensure_delivery_quality(root, state)
            has_full = full_profile_current(root, state)
            acceptance = current_structured_records(root, state, "acceptance")
        else:
            last = last_closed_task(state, completed_only=True)
            verification = last.get("verification") or {}
            has_full = verification.get("profile") == "full"
            acceptance = list(last.get("acceptance", []))
        if not has_full:
            raise FlowError(
                "one-time push to an integration branch requires full verification"
            )
        if not acceptance:
            raise FlowError(
                "one-time push to an integration branch requires current "
                "structured acceptance evidence"
            )
        if not any(record.get("kind") == "review" for record in acceptance):
            raise FlowError(
                "one-time push to an integration branch requires current "
                "independent review evidence"
            )
    else:
        if state.get("activeTask"):
            if not approval_valid(root, state) or not configured_verification_current(
                root, state
            ):
                raise FlowError("push requires current configured verification")
        elif not (state.get("lastClosed") or {}).get("verification"):
            raise FlowError("closed task push requires recorded verification")
    remote = str(remote_override if one_time else automation.get("remote", "origin"))
    if not remote:
        raise FlowError("automation.remote must be explicit")
    active = automation_context_task(state)
    head = current_head(root) or ""
    if one_time:
        remote_ref = git(root, "ls-remote", remote, f"refs/heads/{branch}")
        if remote_ref.returncode != 0:
            raise FlowError(
                redact(remote_ref.stderr.strip()) or "unable to inspect remote"
            )
        remote_sha = remote_ref.stdout.split()[0] if remote_ref.stdout.split() else ""
        if remote_sha:
            fetched = git(root, "fetch", "--no-tags", remote, f"refs/heads/{branch}")
            if fetched.returncode != 0:
                raise FlowError(
                    redact(fetched.stderr.strip()) or "unable to fetch remote"
                )
            ancestor = git(root, "merge-base", "--is-ancestor", remote_sha, head)
            if ancestor.returncode != 0:
                raise FlowError(
                    "remote branch is not an ancestor of local HEAD; integrate the "
                    "remote change and reverify before pushing"
                )
        print(f"one-time push: remote={remote} branch={branch} head={head}")
    outcome = flow_automation.push_action(
        root,
        task_id=active["id"],
        remote=remote,
        branch=branch,
        head=head,
        inputs=context_automation_input(root, state),
        redact=redact,
        authorization_mode=authorization_mode,
    )
    if outcome == "already":
        print("automate push: already completed for this immutable input")


def automate_provider_action(
    root: Path, state: dict[str, Any], config: dict[str, Any], action: str
) -> None:
    automation = flow_automation.require_level(config, action)
    if action == "merge":
        if state.get("activeTask"):
            ensure_delivery_quality(root, state)
            if not baseline_current(root, state):
                raise FlowError(
                    "task baseline changed; rebase and reverify before merge"
                )
        else:
            last = last_closed_task(state, completed_only=True)
            if not closed_context_current(root, state):
                raise FlowError(
                    "closed task contract or evidence changed after archive"
                )
            if not last.get("verification") or not last.get("reviews"):
                raise FlowError(
                    "closed task merge requires verification and review evidence"
                )
    else:
        active_task(state)
        ensure_release(root, state)
    values = context_automation_values(root, state)
    if not values["branch"].startswith("rigorbreeze/"):
        raise FlowError(f"automatic {action} requires a rigorbreeze/<task-id> branch")
    key = flow_automation.idempotency_key(
        action, values["task_id"], values["head"], values["artifact_sha256"]
    )
    target = {
        "branch": values["branch"],
        "environment": str(automation.get("environment", "")) or None,
    }
    outcome = flow_automation.provider_action(
        root,
        task_id=values["task_id"],
        action=action,
        key=key,
        values=values,
        inputs=context_automation_input(root, state),
        target=target,
        check_command=automation.get(f"{action}_check_command"),
        action_command=automation.get(f"{action}_command"),
        redact=redact,
    )
    if outcome == "already":
        print(f"automate {action}: already completed for this immutable input")


def command_automate(
    root: Path,
    action: str,
    *,
    once: bool = False,
    remote: str | None = None,
    branch: str | None = None,
    expected_head: str | None = None,
    workflow_baseline: bool = False,
) -> None:
    state = load_state(root)
    config = load_config(root)
    if once and action not in {"commit", "push"}:
        raise FlowError("one-time authorization is only available for commit and push")
    if workflow_baseline and (not once or action != "commit"):
        raise FlowError("--workflow-baseline requires automate commit --once")
    if (
        once
        and action == "commit"
        and (
            remote is not None
            or branch is not None
            or (expected_head is not None and not workflow_baseline)
        )
    ):
        raise FlowError(
            "remote and branch apply only to one-time push; expected HEAD on commit requires --workflow-baseline"
        )
    if not once and any(value is not None for value in (remote, branch, expected_head)):
        raise FlowError("remote, branch, and expected HEAD overrides require --once")
    authorization_mode = "user-once" if once else "standing"
    try:
        if not once:
            flow_automation.require_level(config, action)
        if action == "commit":
            if once:
                print(
                    "one-time commit: "
                    f"branch={flow_parallel.branch_name(root) or '<detached>'} "
                    f"head={current_head(root) or '<none>'}"
                )
            if workflow_baseline:
                automate_workflow_baseline_commit(root, state, config, expected_head)
            else:
                automate_commit(root, state, config, authorization_mode)
        elif action == "push":
            automate_push(
                root,
                state,
                config,
                authorization_mode=authorization_mode,
                remote_override=remote,
                branch_override=branch,
                expected_head=expected_head,
            )
        elif action in {"merge", "release"}:
            automate_provider_action(root, state, config, action)
        else:
            raise FlowError(f"unknown automation action: {action}")
    except flow_automation.AutomationError as exc:
        raise FlowError(str(exc)) from exc
    print(f"automate {action}: completed")


def command_archive(
    root: Path,
    outcome: str = "completed",
    reason: str | None = None,
    expected_head: str | None = None,
) -> None:
    state = load_state(root)
    active = active_task(state)
    original_phase = str(state.get("phase"))
    integration_proof: str | None = None
    if outcome == "completed":
        if reason or expected_head:
            raise FlowError(
                "archive --reason and --expected-head are only valid for abandoned or reconciled tasks"
            )
        ensure_close(root, state)
    elif outcome == "abandoned":
        if expected_head:
            raise FlowError("abandoned archive does not use --expected-head")
        if not reason or not reason.strip():
            raise FlowError("abandoned archive requires --reason")
        try:
            action = flow_automation.latest_action(root, active["id"])
        except flow_automation.AutomationError as exc:
            raise FlowError(str(exc)) from exc
        if action and action.get("status") == "running":
            raise FlowError("running automation must finish before abandoning a task")
        scopes = allowed_scope(root, state)
        changes = working_tree_paths(root)
        task_code_changes = [
            relative for relative in changes if path_allowed(relative, scopes)
        ]
        if task_code_changes:
            raise FlowError(
                "task-owned uncommitted changes prevent abandonment: "
                + ", ".join(task_code_changes)
            )
    elif outcome == "reconciled":
        if not reason or not reason.strip():
            raise FlowError("reconciled archive requires --reason")
        head = current_head(root) or ""
        if not expected_head or expected_head != head:
            raise FlowError(
                f"reconciled archive expected HEAD {expected_head or '<missing>'}, found {head}"
            )
        try:
            action = flow_automation.latest_action(root, active["id"])
        except flow_automation.AutomationError as exc:
            raise FlowError(str(exc)) from exc
        if action and action.get("status") == "running":
            raise FlowError("running automation must finish before reconciliation")
        release_records_for_reconcile = current_structured_records(
            root, state, "release"
        )
        operation_plans = [
            record
            for record in release_records_for_reconcile
            if record.get("kind") == "operation-plan"
        ]
        operation_results = [
            record
            for record in release_records_for_reconcile
            if record.get("kind") == "operation-result"
        ]
        if operation_plans and (
            not operation_results
            or operation_results[-1].get("operation", {}).get("status") != "succeeded"
        ):
            raise FlowError(
                "release or migration operation result is not confirmed succeeded; "
                "reach a known safe result before reconciliation"
            )
        branch = flow_parallel.branch_name(root)
        base = active.get("baseBranch")
        if branch == base:
            non_workflow_changes = [
                path
                for path in working_tree_paths(root)
                if not path.startswith("spec/")
                and path not in set(managed_workflow_paths(root))
            ]
            if non_workflow_changes:
                raise FlowError(
                    "reconciled archive requires no uncommitted product changes: "
                    + ", ".join(non_workflow_changes)
                )
            integration_proof = "confirmed-on-base-head"
        else:
            integration_proof = flow_parallel.integration_status(
                root, branch, base, active.get("baseSha")
            )
            if integration_proof not in {"contained", "patch-equivalent"}:
                raise FlowError(
                    f"task integration into {base or '<unknown>'} is not proven: {integration_proof}"
                )
    else:
        raise FlowError(f"unknown archive outcome: {outcome}")
    source = task_path(root, active["id"])
    destination = spec_root(root) / "archive" / source.name
    if destination.exists():
        raise FlowError(f"archive already exists: {destination}")
    release_records = current_structured_records(root, state, "release")
    artifact_records = current_structured_records(root, state, "artifacts")
    acceptance_records = current_structured_records(root, state, "acceptance")
    evidence = load_evidence(root, active["id"])
    changes = working_tree_paths(root)
    scopes = allowed_scope(root, state)
    workflow_paths = {
        f"spec/changes/{active['id']}.md",
        f"spec/evidence/{active['id']}.json",
        "spec/state.json",
    }
    closure = {
        "outcome": outcome,
        "reason": redact(reason) if reason else None,
        "closedAt": now_iso(),
        "head": current_head(root) if is_git_repo(root) else None,
        "branch": flow_parallel.branch_name(root) if is_git_repo(root) else None,
        "originalPhase": original_phase,
        "integrationProof": integration_proof,
        "verificationStatus": (
            "current" if verification_current(root, state) else "missing/stale"
        ),
        "practiceEvents": (
            ["closure-pending-commit"]
            if outcome == "completed"
            else ["integrated-unclosed"]
            if outcome == "reconciled"
            else []
        ),
        "unrelatedChanges": sorted(
            relative
            for relative in changes
            if relative not in workflow_paths and not path_allowed(relative, scopes)
        ),
    }
    evidence["closure"] = closure
    save_evidence(root, active["id"], evidence)
    source.replace(destination)
    archive_relative = f"spec/archive/{active['id']}.md"
    evidence_relative = f"spec/evidence/{active['id']}.json"
    closure_digest = sha256_bytes(
        destination.read_bytes()
        + b"\0"
        + evidence_path(root, active["id"]).read_bytes()
    )
    state["lastClosed"] = {
        "id": active["id"],
        "title": active.get("title"),
        "risk": active.get("risk"),
        "branch": closure["branch"],
        "baseBranch": active.get("baseBranch"),
        "baseSha": active.get("baseSha"),
        "allowedScope": scopes,
        "closedAt": closure["closedAt"],
        "outcome": outcome,
        "reason": closure["reason"],
        "archivePath": archive_relative,
        "sourcePath": f"spec/changes/{active['id']}.md",
        "evidencePath": evidence_relative,
        "closureDigest": closure_digest,
        "taskDigest": state["approvals"]["task"]["digest"],
        "verification": state.get("verification"),
        "artifacts": artifact_records,
        "acceptance": acceptance_records,
        "reviews": [
            record for record in acceptance_records if record.get("kind") == "review"
        ],
        "release": release_records,
        "practice": evidence.get("practice", {}),
        "approvals": {
            "dependencies": list(state["approvals"].get("dependencies", [])),
            "migrations": list(state["approvals"].get("migrations", [])),
        },
        "integrationProof": integration_proof,
        "projectFingerprint": project_fingerprint(root),
    }
    state["activeTask"] = None
    state["phase"] = "archived"
    state["approvals"]["task"] = {"valid": False, "digest": None, "approvedAt": None}
    state["approvals"]["dependencies"] = []
    state["approvals"]["migrations"] = []
    state["red"] = None
    state["verification"] = None
    save_state(root, state)
    print(
        f"archived {active['id']}"
        if outcome == "completed"
        else f"{outcome} {active['id']}"
    )


def command_doctor(
    root: Path,
    json_output: bool = False,
    all_worktrees: bool = False,
    repair: bool = False,
) -> None:
    issues: list[str] = []
    warnings: list[str] = []
    if is_git_repo(root):
        warnings.extend(migrate_legacy_state(root, remove_untracked=repair))
        cache_retained = clean_managed_bytecode(root) if repair else []
        warnings.extend(
            f"retained unknown cache entry: {relative}" for relative in cache_retained
        )
    if repair:
        if not all_worktrees or not is_git_repo(root):
            raise FlowError("doctor --repair requires --all in a Git repository")
        flow_parallel.remove_stale_lock(root)
        flow_parallel.rebuild_registry(root)
    if not (spec_root(root) / "index.md").is_file():
        issues.append("missing spec/index.md")
    if not state_path(root).is_file():
        issues.append(f"missing workflow state: {state_path(root)}")
    for relative in ("changes", "evidence", "archive"):
        if not (spec_root(root) / relative).is_dir():
            issues.append(f"missing spec/{relative}/")
    if not is_git_repo(root):
        issues.append("not a Git repository")
    else:
        try:
            flow_automation.load_journal(root)
        except flow_automation.AutomationError as exc:
            issues.append(str(exc))
    try:
        load_config(root)
    except FlowError as exc:
        issues.append(str(exc))
    try:
        state = load_state(root)
        if state.get("workflowVersion") != VERSION:
            issues.append("unsupported workflow version")
        active = state.get("activeTask")
        if active and not task_path(root, active["id"]).is_file():
            issues.append("active task file is missing")
        if active and active.get("risk") in {"L1", "L2"} and is_git_repo(root):
            baseline = workflow_baseline_status(root, state)
            if baseline["status"] != "current":
                warnings.append(
                    "workflow baseline is not current before a high-risk task: "
                    f"{baseline['status']} on {baseline['baseBranch']}"
                )
    except FlowError as exc:
        issues.append(str(exc))
    evidence_dir = spec_root(root) / "evidence"
    if evidence_dir.is_dir():
        for path in sorted(evidence_dir.glob("*.json")):
            try:
                upgrade_evidence(read_json(path), path.stem)
            except FlowError as exc:
                issues.append(str(exc))
    tasks: list[dict[str, Any]] = []
    if all_worktrees and is_git_repo(root):
        try:
            aggregate = flow_parallel.aggregate(root)
            tasks = aggregate["tasks"]
            issues.extend(aggregate["issues"])
            seen_worktrees: set[str] = set()
            for task in tasks:
                worktree = str(task.get("worktree", ""))
                if (
                    not task.get("worktreeExists")
                    and not task.get("worktreeRemoved")
                    and task.get("readiness") != "integrated"
                ):
                    issues.append(
                        f"{task.get('taskId')} worktree is missing: {worktree}"
                    )
                if worktree in seen_worktrees:
                    issues.append(f"duplicate worktree registration: {worktree}")
                seen_worktrees.add(worktree)
                expected = task.get("branch")
                if task.get("worktreeExists") and expected:
                    actual = flow_parallel.branch_name(Path(worktree))
                    if actual != expected:
                        issues.append(
                            f"{task.get('taskId')} branch mismatch: "
                            f"expected {expected}, found {actual}"
                        )
        except flow_parallel.ParallelError as exc:
            issues.append(str(exc))
    if issues:
        raise FlowError("doctor found issues: " + "; ".join(issues))
    if json_output:
        print(
            json.dumps(
                {
                    "status": "ok",
                    "issues": [],
                    "warnings": warnings,
                    "workflowVersion": VERSION,
                    "tasks": tasks if all_worktrees else None,
                },
                sort_keys=True,
            )
        )
    else:
        for warning in warnings:
            print(f"warning: {warning}")
        print("doctor: ok")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Production-grade spec, evidence, and release gates"
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {TOOL_VERSION}"
    )
    parser.add_argument(
        "--root", type=Path, default=Path.cwd(), help="target project root"
    )
    parser.add_argument(
        "--mode", choices=MODES, help="override local advisory/enforced policy"
    )
    parser.add_argument(
        "--session",
        help="stable Codex window ID; defaults to RIGORBREEZE_SESSION_ID or parent PID",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    new = sub.add_parser("new")
    new.add_argument("task_id")
    new.add_argument("--title", required=True)
    new.add_argument("--risk", choices=("L0", "L1", "L2", "Emergency"), required=True)
    new.add_argument("--worktree", choices=("auto",))
    new.add_argument("--depends-on", action="append", default=[])
    status = sub.add_parser("status")
    status.add_argument("--json", action="store_true")
    status.add_argument("--all", action="store_true")
    approve = sub.add_parser("approve")
    approve.add_argument("kind", choices=("task", "dependency", "migration", "overlap"))
    approve.add_argument("--name")
    approve.add_argument("--reason")
    red = sub.add_parser("red")
    red.add_argument("--requirement", required=True)
    red.add_argument("--expect-pattern", required=True)
    red.add_argument("--test", action="append", default=[])
    red.add_argument("run", nargs=argparse.REMAINDER)
    verify = sub.add_parser("verify")
    verify.add_argument("--profile", choices=("affected", "full"), required=True)
    evidence = sub.add_parser("evidence")
    evidence_sub = evidence.add_subparsers(dest="evidence_command", required=True)
    evidence_add = evidence_sub.add_parser("add")
    evidence_add.add_argument(
        "--section", choices=("artifacts", "acceptance", "release"), required=True
    )
    evidence_add.add_argument("--kind", required=True)
    evidence_add.add_argument("--file")
    evidence_add.add_argument("--field", action="append", default=[])
    retro = sub.add_parser("retro")
    retro.add_argument("--json", action="store_true")
    retro.add_argument("--confirm", action="store_true")
    retro.add_argument(
        "--rework-reason",
        choices=(
            "none",
            "requirement",
            "design",
            "implementation",
            "test",
            "environment",
            "workflow",
            "mixed",
        ),
    )
    retro.add_argument("--exceptions")
    retro.add_argument(
        "--workflow-impact", choices=("helped", "neutral", "hurt", "unknown")
    )
    check = sub.add_parser("check")
    check.add_argument("gate", choices=("commit", "merge", "release"))
    automate = sub.add_parser("automate")
    automate.add_argument("action", choices=("commit", "push", "merge", "release"))
    automate.add_argument("--once", action="store_true")
    automate.add_argument("--remote")
    automate.add_argument("--branch")
    automate.add_argument("--expected-head")
    automate.add_argument("--workflow-baseline", action="store_true")
    claim = sub.add_parser("claim")
    claim.add_argument("--release", action="store_true")
    reconcile = sub.add_parser("reconcile")
    reconcile.add_argument("--cleanup", action="store_true")
    reconcile.add_argument("--worktree", type=Path)
    reconcile.add_argument("--base")
    reconcile.add_argument("--expected-head")
    reconcile.add_argument("--allow-unmanaged", action="store_true")
    archive = sub.add_parser("archive")
    archive.add_argument(
        "--outcome",
        choices=("completed", "abandoned", "reconciled"),
        default="completed",
    )
    archive.add_argument("--reason")
    archive.add_argument("--expected-head")
    doctor = sub.add_parser("doctor")
    doctor.add_argument("--json", action="store_true")
    doctor.add_argument("--all", action="store_true")
    doctor.add_argument("--repair", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.command == "status":
            command_status(root, args.json, args.all)
            return 0
        if args.command == "doctor":
            command_doctor(root, args.json, args.all, args.repair)
            return 0
        with project_lock(root):
            if args.command not in {"init", "new", "claim"} and is_git_repo(root):
                try:
                    flow_parallel.claim_worktree(
                        root,
                        args.session,
                        check_resources=not (
                            args.command == "archive"
                            and getattr(args, "outcome", None)
                            in {"abandoned", "reconciled"}
                        ),
                    )
                except flow_parallel.ParallelError as exc:
                    raise FlowError(str(exc)) from exc
            if args.command == "init":
                command_init(root)
            elif args.command == "new":
                command_new(
                    root,
                    args.task_id,
                    args.title,
                    args.risk,
                    args.worktree,
                    args.depends_on,
                )
            elif args.command == "approve":
                command_approve(root, args.kind, args.name, args.reason)
            elif args.command == "red":
                command_red(
                    root, args.requirement, args.expect_pattern, args.test, args.run
                )
            elif args.command == "verify":
                return command_verify_profile(root, args.profile, args.mode)
            elif args.command == "evidence":
                command_evidence_add(
                    root,
                    args.section,
                    args.kind,
                    args.file,
                    args.field,
                )
            elif args.command == "retro":
                command_retro(
                    root,
                    json_output=args.json,
                    confirm=args.confirm,
                    rework_reason=args.rework_reason,
                    exceptions=args.exceptions,
                    workflow_impact=args.workflow_impact,
                )
            elif args.command == "check":
                command_check(root, args.gate, args.mode)
            elif args.command == "automate":
                command_automate(
                    root,
                    args.action,
                    once=args.once,
                    remote=args.remote,
                    branch=args.branch,
                    expected_head=args.expected_head,
                    workflow_baseline=args.workflow_baseline,
                )
            elif args.command == "claim":
                try:
                    if args.release:
                        flow_parallel.release_worktree(root, args.session)
                        print("worktree claim released")
                    else:
                        flow_parallel.claim_worktree(root, args.session)
                        print("worktree claimed")
                except flow_parallel.ParallelError as exc:
                    raise FlowError(str(exc)) from exc
            elif args.command == "reconcile":
                try:
                    if args.allow_unmanaged:
                        if (
                            not args.cleanup
                            or not args.worktree
                            or not args.base
                            or not args.expected_head
                        ):
                            raise FlowError(
                                "unmanaged cleanup requires --cleanup, --worktree, --base, and --expected-head"
                            )
                        result = flow_parallel.cleanup_unmanaged_worktree(
                            root,
                            worktree=args.worktree,
                            base=args.base,
                            expected_head=args.expected_head,
                        )
                    else:
                        if any((args.worktree, args.base, args.expected_head)):
                            raise FlowError(
                                "targeted worktree cleanup requires --allow-unmanaged"
                            )
                        result = flow_parallel.reconcile_integrations(
                            root, args.cleanup
                        )
                except flow_parallel.ParallelError as exc:
                    raise FlowError(str(exc)) from exc
                print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            elif args.command == "archive":
                command_archive(root, args.outcome, args.reason, args.expected_head)
        return 0
    except FlowError as exc:
        try:
            if state_path(root).is_file():
                event_state = load_state(root)
                message = str(exc)
                event_type = None
                details: dict[str, Any] = {"message": message}
                if getattr(args, "command", None) == "check":
                    event_type = "gate-failure"
                    details["gate"] = getattr(args, "gate", None)
                elif "runtime claim" in message.lower():
                    event_type = "runtime-resource-conflict"
                elif "workflow baseline branch is not current" in message.lower():
                    event_type = "workflow-baseline-pending"
                elif "integrated-unclosed" in message.lower():
                    event_type = "integrated-unclosed"
                elif "closure-pending" in message.lower():
                    event_type = "closure-pending-commit"
                elif "unmanaged worktree" in message.lower():
                    event_type = "unmanaged-worktree-review"
                elif "active task" in message.lower() and getattr(
                    args, "command", None
                ) in {"new", "init"}:
                    if getattr(args, "command", None) == "init":
                        install = installation_status(root, event_state)
                        event_type = (
                            "runner-partial-installation"
                            if install.get("missingComponents")
                            else "runner-drift"
                        )
                        details["installationStatus"] = install.get("status")
                    else:
                        event_type = "old-task-slot"
                if event_type:
                    record_practice_event(root, event_state, event_type, details)
        except (FlowError, OSError, json.JSONDecodeError):
            pass
        if (
            getattr(args, "command", None) == "check"
            and getattr(args, "gate", None) == "commit"
        ):
            try:
                state = load_state(root)
                if effective_mode(root, args.mode, state, args.gate) == "advisory":
                    print(f"WARNING: {exc} (advisory; not blocking)")
                    return 0
            except FlowError:
                pass
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
