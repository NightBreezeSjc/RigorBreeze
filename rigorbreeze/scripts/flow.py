#!/usr/bin/env python3
"""Deterministic gates for RigorBreeze."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Repository-local runners import four helper modules. Never leave Python bytecode
# behind in a project merely because a workflow command was inspected.
sys.dont_write_bytecode = True


def configure_text_streams() -> None:
    """Keep CLI output portable when Windows inherits a legacy code page."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            # Embedded callers may provide an already detached or fixed stream.
            pass


import flow_automation  # noqa: E402
import flow_diagnostics  # noqa: E402
import flow_parallel  # noqa: E402
import flow_policy  # noqa: E402
import flow_records  # noqa: E402
import flow_state  # noqa: E402
import flow_verification  # noqa: E402
from flow_policy import (  # noqa: E402
    acceptance_ids,
    allowed_scope,
    approval_valid,
    automation_input,
    automation_task_paths,
    automation_values,
    baseline_current,
    configured_paths,
    configured_verification_current,
    current_structured_records,
    declared_dependencies,
    ensure_delivery_quality,
    ensure_release,
    ensure_scope_current,
    full_profile_current,
    is_configured_migration_path,
    is_dependency_path,
    operational_modes,
    path_allowed,
    path_under,
    preapproval_delivery_paths,
    preapproval_dirt_cause,
    project_fingerprint,
    record_practice_event,
    save_state,
    secret_content_paths,
    staged_files,
    task_change_paths,
    task_context,
    task_scope_status,
    runtime_claims,
    validate_scope_entries,
)
from flow_state import (  # noqa: E402
    LOCK_NAME,
    MODES,
    PLACEHOLDERS,
    REPOSITORY_WRAPPER_MARKER,
    REQUIRED_TASK_SECTIONS,
    RUNNER_MARKER,
    TOOL_VERSION,
    FlowError,
    active_task,
    archive_path,
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
    project_lock,
    read_json,
    records_root,
    redact,
    save_evidence,
    sha256_bytes,
    spec_root,
    state_path,
    task_digest,
    task_path,
    task_template,
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
    current_installation = flow_diagnostics.installation_status(root, existing_state)
    if (
        current_installation["status"] != "current"
        and existing_state
        and existing_state.get("activeTask")
    ):
        raise FlowError(
            "an active task prevents workflow runner upgrade; finish or abandon the "
            "active task with the bundled runner, then run init"
        )
    config = config_path(root)
    if not config.exists():
        atomic_write(config, config_template())
    spec = spec_root(root)
    spec.mkdir(parents=True, exist_ok=True)
    # Empty compatibility directories let an existing project explicitly keep
    # or restore tracked storage without re-running a destructive migration.
    for name in ("changes", "evidence", "archive"):
        (spec / name).mkdir(parents=True, exist_ok=True)
    for name in ("changes", "evidence", "archive"):
        (records_root(root) / name).mkdir(parents=True, exist_ok=True)
    (records_root(root) / "history").mkdir(parents=True, exist_ok=True)
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
    runner = root / "scripts" / "rigorbreeze.py"
    source = Path(__file__).read_text(encoding="utf-8")
    helper_modules = {
        module.__name__: module
        for module in (
            flow_state,
            flow_parallel,
            flow_automation,
            flow_policy,
            flow_records,
            flow_verification,
            flow_diagnostics,
        )
    }
    helper_sources = {
        f"{name}.py": Path(helper_modules[name].__file__).read_text(encoding="utf-8")
        for name in flow_state.KERNEL_HELPER_NAMES
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
    print("initialized v5 workflow with risk-adaptive records")


def command_new(
    root: Path,
    task_id: str,
    title: str,
    risk: str,
    worktree: str | None = None,
    depends_on: list[str] | None = None,
) -> None:
    dependencies = list(dict.fromkeys(depends_on or []))
    existing_state = None
    if state_path(root).is_file() or legacy_state_path(root).is_file():
        existing_state = load_state(root)
        lifecycle, _ = flow_diagnostics.current_task_lifecycle(root, existing_state)
        if lifecycle in {"integrated-unclosed", "closure-pending"}:
            raise FlowError(
                f"{lifecycle} task must be closed and committed before starting another task"
            )
    if risk in {"L1", "L2"} and is_git_repo(root):
        if existing_state is None:
            raise FlowError("initialize RigorBreeze before starting an L1/L2 task")
        installation = flow_diagnostics.installation_status(root, existing_state)
        baseline = flow_diagnostics.workflow_baseline_status(root, existing_state)
        if installation["status"] != "current" or baseline["status"] != "current":
            raise FlowError(
                "workflow baseline and runner must be current before creating an "
                f"{risk} task: baseline={baseline['status']}, "
                f"installation={installation['status']}; "
                f"{baseline['nextAction']['command']}"
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
            and not archive_path(root, dependency).exists()
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
    if path.exists() or archive_path(root, task_id).exists():
        raise FlowError(f"task ID already exists: {task_id}")
    task_base_branch: str | None = None
    task_base_sha: str | None = None
    if is_git_repo(root):
        task_base_branch = flow_diagnostics.baseline_branch(root, state)
        if not task_base_branch:
            raise FlowError("unable to determine the task baseline branch")
        base_head = git(root, "rev-parse", task_base_branch)
        if base_head.returncode != 0:
            raise FlowError(f"baseline branch is missing: {task_base_branch}")
        task_base_sha = base_head.stdout.strip()
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
                "baseBranch": task_base_branch,
                "baseSha": task_base_sha,
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
        active.update(task_context(root, state))
        if active["waitingOn"].lower() not in {"", "none", "n/a"}:
            raise FlowError(
                f"task is waiting on {active['waitingOn']}; resolve Waiting-On "
                "before approval"
            )
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
            baseline = flow_diagnostics.workflow_baseline_status(root, state)
            installation = flow_diagnostics.installation_status(root, state)
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
        if active.get("risk") in {"L1", "L2"}:
            dirty = preapproval_delivery_paths(root, state)
            if dirty:
                cause = preapproval_dirt_cause(dirty)
                raise FlowError(
                    "clean task worktree is required before "
                    f"{active['risk']} approval ({cause}): " + ", ".join(dirty)
                )
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


def automation_context_task(state: dict[str, Any]) -> dict[str, Any]:
    active = state.get("activeTask")
    if active:
        return active
    last = flow_records.last_closed_task(state, completed_only=True)
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
    last = flow_records.last_closed_task(state, completed_only=True)
    if not flow_records.closed_context_current(root, state):
        raise FlowError("closed task contract or evidence changed after archive")
    scopes = list(last.get("allowedScope", []))
    closure = (
        {f"spec/evidence/{last['id']}.audit.json"}
        if last.get("recordStorage") == "private"
        else {
            str(last.get("sourcePath")),
            str(last.get("archivePath")),
            str(last.get("evidencePath")),
        }
    )
    return sorted(
        relative
        for relative in flow_automation.working_tree_paths(root, {f"spec/{LOCK_NAME}"})
        if relative in closure or path_allowed(relative, scopes)
    )


def context_automation_values(root: Path, state: dict[str, Any]) -> dict[str, str]:
    if state.get("activeTask"):
        return automation_values(root, state)
    last = flow_records.last_closed_task(state, completed_only=True)
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
    last = flow_records.last_closed_task(state, completed_only=True)
    values = context_automation_values(root, state)
    verification = json.dumps(
        last.get("verification"), ensure_ascii=False, sort_keys=True
    ).encode()
    evidence_file = (
        evidence_path(root, str(last["id"]))
        if last.get("recordStorage") == "private"
        else root / str(last["evidencePath"])
    )
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
    if not flow_records.closed_context_current(root, state):
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
    base = flow_diagnostics.baseline_branch(root, state)
    if not base or flow_parallel.branch_name(root) != base:
        raise FlowError("workflow baseline commit must run on the baseline branch")
    installation = flow_diagnostics.installation_status(root, state)
    if installation["status"] != "current":
        raise FlowError(
            f"workflow installation must be current: {installation['status']}"
        )
    load_config(root)
    agents = (root / "AGENTS.md").read_text(encoding="utf-8", errors="replace")
    if flow_state.AGENTS_START not in agents or flow_state.AGENTS_END not in agents:
        raise FlowError("managed RigorBreeze AGENTS marker is missing")
    selected = flow_diagnostics.workflow_baseline_commit_paths(root, state)
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
        if flow_diagnostics.installation_status(root, state)["status"] != "current":
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
    elif not flow_records.closed_context_current(root, state):
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
            (lambda: flow_verification.command_check(root, "commit", "enforced"))
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
    elif not flow_records.closed_context_current(root, state):
        raise FlowError("closed task contract or evidence changed after archive")
    if one_time and branch in protected:
        if state.get("activeTask"):
            ensure_delivery_quality(root, state)
            has_full = full_profile_current(root, state)
            acceptance = current_structured_records(root, state, "acceptance")
        else:
            last = flow_records.last_closed_task(state, completed_only=True)
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
            last = flow_records.last_closed_task(state, completed_only=True)
            if not flow_records.closed_context_current(root, state):
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
    status.add_argument("--compact", action="store_true")
    status.add_argument("--path", action="append", default=[])
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
    verify.add_argument("--force", action="store_true")
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
    doctor.add_argument("--migrate-records", choices=("private",))
    return parser


def main() -> int:
    configure_text_streams()
    parser = build_parser()
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.command == "status":
            flow_diagnostics.command_status(
                root, args.json, args.all, args.compact, args.path
            )
            return 0
        if args.command == "doctor":
            flow_diagnostics.command_doctor(
                root, args.json, args.all, args.repair, args.migrate_records
            )
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
                flow_verification.command_red(
                    root, args.requirement, args.expect_pattern, args.test, args.run
                )
            elif args.command == "verify":
                return flow_verification.command_verify_profile(
                    root, args.profile, args.mode, args.force
                )
            elif args.command == "evidence":
                flow_records.command_evidence_add(
                    root,
                    args.section,
                    args.kind,
                    args.file,
                    args.field,
                )
            elif args.command == "retro":
                flow_records.command_retro(
                    root,
                    json_output=args.json,
                    confirm=args.confirm,
                    rework_reason=args.rework_reason,
                    exceptions=args.exceptions,
                    workflow_impact=args.workflow_impact,
                )
            elif args.command == "check":
                flow_verification.command_check(root, args.gate, args.mode)
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
                        result["compactedRecords"] = (
                            flow_records.compact_integrated_private_records(
                                root, result.get("integrated", [])
                            )
                        )
                except flow_parallel.ParallelError as exc:
                    raise FlowError(str(exc)) from exc
                print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            elif args.command == "archive":
                flow_records.command_archive(
                    root, args.outcome, args.reason, args.expected_head
                )
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
                elif "clean task worktree is required" in message.lower():
                    event_type = "preapproval-dirt"
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
                        install = flow_diagnostics.installation_status(
                            root, event_state
                        )
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
