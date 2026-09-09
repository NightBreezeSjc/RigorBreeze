"""Installation, baseline, lifecycle, status, and doctor projections for RigorBreeze."""

from __future__ import annotations
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any
import flow_automation
import flow_parallel
import flow_policy
import flow_records
import flow_state
import flow_verification

FlowError = flow_state.FlowError


def entrypoint_source_path() -> Path:
    bundled = Path(__file__).with_name("flow.py")
    return bundled if bundled.is_file() else Path(__file__).with_name("rigorbreeze.py")


def installation_status(
    root: Path, state: dict[str, Any] | None = None
) -> dict[str, Any]:
    repository_runner = root / "scripts" / "rigorbreeze.py"
    if not repository_runner.is_file():
        return {
            "skillVersion": flow_state.TOOL_VERSION,
            "runnerVersion": None,
            "status": "missing",
            "upgradeSafe": not bool((state or {}).get("activeTask")),
            "missingComponents": ["scripts/rigorbreeze.py"],
            "modifiedComponents": [],
        }
    runner_text = repository_runner.read_text(encoding="utf-8", errors="replace")
    if flow_state.RUNNER_MARKER in runner_text:
        target_directory = root / "scripts"
        target_runner = repository_runner
    elif (
        flow_state.REPOSITORY_WRAPPER_MARKER in runner_text
        and (root / "rigorbreeze" / "scripts" / "flow.py").is_file()
    ):
        target_directory = root / "rigorbreeze" / "scripts"
        target_runner = target_directory / "flow.py"
    else:
        return {
            "skillVersion": flow_state.TOOL_VERSION,
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
    helper_modules = {
        module.__name__: module
        for module in (
            flow_state,
            flow_parallel,
            flow_automation,
            flow_policy,
            flow_records,
            flow_verification,
            sys.modules[__name__],
        )
    }
    expected = {target_runner: entrypoint_source_path().read_text(encoding="utf-8")}
    expected.update(
        {
            target_directory / f"{name}.py": Path(
                helper_modules[name].__file__
            ).read_text(encoding="utf-8")
            for name in flow_state.KERNEL_HELPER_NAMES
        }
    )
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
    elif runner_version != flow_state.TOOL_VERSION:
        status = "outdated"
    elif not modified_components:
        status = "current"
    else:
        status = "unmanaged"
    return {
        "skillVersion": flow_state.TOOL_VERSION,
        "runnerVersion": runner_version,
        "status": status,
        "upgradeSafe": not bool((state or {}).get("activeTask")),
        "missingComponents": missing_components,
        "modifiedComponents": modified_components,
    }


def workflow_bypass_status(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    active = state.get("activeTask")
    if not active or state.get("approvals", {}).get("task", {}).get("valid"):
        return {"status": "clear", "paths": [], "evolutionCandidate": False}
    metadata = flow_state.workflow_metadata_paths(root, active["id"])
    delivery_paths = [
        path for path in flow_state.working_tree_paths(root) if path not in metadata
    ]
    if not delivery_paths:
        return {"status": "clear", "paths": [], "evolutionCandidate": False}
    flow_policy.record_practice_event(
        root,
        state,
        "workflow-bypass",
        {
            "taskId": active["id"],
            "approval": "invalid",
        },
        evolution_candidate=True,
    )
    return {
        "status": "detected",
        "paths": delivery_paths,
        "evolutionCandidate": True,
    }


def workflow_bypass_action() -> dict[str, str]:
    return {
        "reason": (
            "Unapproved delivery changes bypassed the workflow contract; "
            "do not fabricate RED or silently establish a new baseline."
        ),
        "command": (
            "restore the delivery changes, or integrate them externally and "
            "archive --outcome reconciled with the bypass recorded"
        ),
    }


def orphaned_record_action(task_id: str) -> dict[str, str]:
    return {
        "reason": (
            f"The active task contract for {task_id} is missing; no approval, "
            "verification, or completion may be inferred."
        ),
        "command": (
            f"restore the {task_id} contract from configured record storage, "
            "then run doctor --all --json"
        ),
    }


def evolution_projection(roots: list[Path]) -> dict[str, Any]:
    candidates: set[str] = set()
    seen: set[Path] = set()
    for project in roots:
        evidence_dirs = {
            project / "spec" / "evidence",
            flow_state.records_root(project) / "evidence",
        }
        for evidence_dir in evidence_dirs:
            if not evidence_dir.is_dir():
                continue
            for path in sorted(evidence_dir.glob("*.json")):
                if path.name.endswith(".audit.json"):
                    continue
                resolved = path.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                try:
                    evidence = flow_state.read_json(path)
                except FlowError:
                    continue
                practice = evidence.get("practice", {})
                confirmation = practice.get("confirmation") or {}
                events = practice.get("events") or []
                if confirmation.get("evolutionCandidate") is True or any(
                    isinstance(event, dict) and event.get("evolutionCandidate") is True
                    for event in events
                ):
                    candidates.add(str(evidence.get("taskId") or path.stem))
    return {
        "candidateCount": len(candidates),
        "taskIds": sorted(candidates),
        "command": ("$rigorbreeze 汇总这个项目的演进候选" if candidates else None),
    }


def baseline_branch(root: Path, state: dict[str, Any] | None = None) -> str | None:
    active = (state or {}).get("activeTask") or {}
    if active.get("baseBranch"):
        return str(active["baseBranch"])
    try:
        configured = str(
            flow_state.load_config(root).get("parallel", {}).get("base_branch", "")
        ).strip()
    except FlowError:
        configured = ""
    if configured:
        return configured
    try:
        return flow_parallel.default_base_branch(root)
    except flow_parallel.ParallelError:
        return None


def workflow_baseline_commit_paths(root: Path, state: dict[str, Any]) -> list[str]:
    allowed = set(flow_state.managed_workflow_paths(root)) | set(
        flow_records.completed_closure_paths(root, state)
    )
    changed = flow_automation.working_tree_paths(root, {f"spec/{flow_state.LOCK_NAME}"})
    return sorted(path for path in changed if path in allowed)


def workflow_baseline_status(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    base = baseline_branch(root, state)
    payload: dict[str, Any] = {
        "status": "blocked",
        "baseBranch": base,
        "tracked": [],
        "untracked": list(flow_state.managed_workflow_paths(root)),
        "modified": [],
        "safeToCommit": False,
        "nextAction": {
            "reason": "The workflow baseline branch cannot be determined.",
            "command": "configure parallel.base_branch, then run status --json",
        },
    }
    if not flow_state.is_git_repo(root) or not base:
        return payload
    base_head = flow_state.git(root, "rev-parse", base)
    if base_head.returncode != 0:
        payload["nextAction"] = {
            "reason": f"The workflow baseline branch {base} does not exist.",
            "command": "create or configure the baseline branch",
        }
        return payload
    tracked: list[str] = []
    missing: list[str] = []
    modified: list[str] = []
    for relative in flow_state.managed_workflow_paths(root):
        stored = flow_state.git(root, "show", f"{base}:{relative}")
        if stored.returncode != 0:
            missing.append(relative)
            continue
        tracked.append(relative)
        if (
            flow_state.git(root, "diff", "--quiet", base, "--", relative).returncode
            != 0
        ):
            modified.append(relative)
    payload["tracked"] = sorted(tracked)
    payload["untracked"] = sorted(missing)
    payload["modified"] = sorted(modified)
    installation = installation_status(root, state)
    if len(missing) == len(flow_state.managed_workflow_paths(root)):
        status = "missing"
    elif missing:
        status = "partial"
    elif modified or installation["status"] != "current":
        status = "modified"
    else:
        status = "current"
    payload["status"] = status
    current_branch = flow_parallel.branch_name(root)
    head = flow_state.current_head(root)
    changed = flow_automation.working_tree_paths(root, {f"spec/{flow_state.LOCK_NAME}"})
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


def current_task_lifecycle(
    root: Path, state: dict[str, Any]
) -> tuple[str, dict[str, str] | None]:
    active = state.get("activeTask")
    if active and flow_state.is_git_repo(root):
        try:
            entry = flow_parallel.load_registry(root)["tasks"].get(active["id"], {})
            integrated = entry and flow_parallel.is_integrated(root, entry)
            own_stream = flow_parallel.branch_name(root) == active.get("baseBranch")
            if integrated and not own_stream:
                return (
                    "integrated-unclosed",
                    {
                        "reason": "The task code is integrated but the workflow record is still open.",
                        "command": (
                            "python scripts/rigorbreeze.py archive --outcome reconciled "
                            f"--reason <reason> --expected-head {flow_state.current_head(root) or '<SHA>'}"
                        ),
                    },
                )
        except flow_parallel.ParallelError:
            pass
    if not active and state.get("lastClosed"):
        pending = flow_records.closure_pending_paths(root, state)
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


def interaction_projection(
    state: dict[str, Any], payload: dict[str, Any], action: dict[str, str]
) -> dict[str, Any]:
    last = state.get("lastClosed") or {}
    completed = []
    if last.get("id"):
        completed.append(
            f"{last['id']} 已{('完成' if last.get('outcome') == 'completed' else '关闭')}"
        )
    lifecycle = str(payload.get("lifecycle", "idle"))
    bypass = payload.get("workflowBypass", {}).get("status") == "detected"
    if bypass:
        kind, actor = "safety-stop", "user"
    elif lifecycle in {"orphaned-record", "integrated-unclosed", "closure-pending"}:
        kind, actor = "repair", "codex"
    elif payload.get("activeTask"):
        actor = action.get("actor", "codex")
        kind = action.get("kind", "work")
    else:
        kind, actor = "work", "none"
    current = (
        f"{payload['activeTask']}：{action.get('reason', '处理中')}"
        if payload.get("activeTask")
        else action.get("reason", "当前没有活动任务")
    )
    return {
        "completed": completed,
        "current": current,
        "next": {
            "actor": actor,
            "kind": kind,
            "summary": action.get("reason", "无"),
            "command": action.get("command") if actor != "none" else None,
        },
    }


def print_interaction(interaction: dict[str, Any]) -> None:
    completed = "；".join(interaction["completed"]) or "暂无新的关闭结果"
    next_item = interaction["next"]
    if next_item["actor"] == "user":
        user_action = next_item["summary"]
    else:
        user_action = "无"
    print(f"已完成：{completed}")
    print(f"当前：{interaction['current']}")
    print(f"需要你操作：{user_action}")


def worktree_status_projection(
    root: Path, tasks: list[dict[str, Any]], cleanup: dict[str, Any]
) -> list[dict[str, Any]]:
    task_groups: dict[str, list[dict[str, Any]]] = {}
    for task in tasks:
        value = task.get("worktree")
        if not value:
            continue
        path = str(Path(str(value)).resolve())
        task_groups.setdefault(path, []).append(task)
    actual = {
        str(Path(item["worktree"]).resolve()): item
        for item in flow_parallel.worktrees(root)
        if item.get("worktree")
    }
    cleanup_by_path: dict[str, str] = {}
    for bucket, label in (
        ("removableWorktrees", "removable"),
        ("retainedWorktrees", "retained"),
        ("staleRegistryEntries", "stale-registry"),
    ):
        for item in cleanup.get(bucket, []):
            value = item.get("worktree")
            if value:
                cleanup_by_path[str(Path(str(value)).resolve())] = label
    projected: list[dict[str, Any]] = []
    for path in sorted(set(actual) | set(task_groups)):
        related = task_groups.get(path, [])
        worktree = Path(path)
        state = None
        if worktree.is_dir() and (
            flow_state.state_path(worktree).is_file()
            or flow_state.legacy_state_path(worktree).is_file()
        ):
            try:
                state = flow_state.load_state(worktree)
            except FlowError:
                state = None
        install = (
            installation_status(worktree, state)
            if worktree.is_dir()
            else {
                "runnerVersion": None,
                "status": "missing",
            }
        )
        actual_item = actual.get(path, {})
        branches = sorted(
            {
                str(value).removeprefix("refs/heads/")
                for value in (
                    actual_item.get("branch"),
                    *(item.get("branch") for item in related),
                )
                if value
            }
        )
        task_ids = sorted(str(item["taskId"]) for item in related if item.get("taskId"))
        active_ids = sorted(
            str(item["taskId"])
            for item in related
            if item.get("taskId")
            and item.get("lifecycle") not in {"closed", "integrated"}
        )
        projected.append(
            {
                "worktree": path,
                "branch": branches[0] if len(branches) == 1 else None,
                "taskIds": task_ids,
                "activeTaskIds": active_ids,
                "runnerVersion": install.get("runnerVersion"),
                "installationStatus": install.get("status"),
                "cleanupStatus": cleanup_by_path.get(
                    path, "current" if worktree.resolve() == root.resolve() else "none"
                ),
            }
        )
    return projected


def compact_all_status(payload: dict[str, Any]) -> dict[str, Any]:
    task_keys = """taskId risk lifecycle readiness dependsOn runtimeConflicts verification fullProfile head nextAction issues""".split()
    tasks = []
    for item in payload.get("tasks", []):
        if item.get("lifecycle") in {"closed", "integrated"}:
            continue
        projected = {key: item[key] for key in task_keys if key in item}
        scopes = sorted(str(scope) for scope in item.get("allowedScope", []))
        projected["scopeSummary"] = {
            "count": len(scopes),
            "digest": hashlib.sha256("\0".join(scopes).encode()).hexdigest(),
            "preview": scopes[:3],
        }
        tasks.append(projected)
    active_ids = {str(item.get("taskId")) for item in tasks if item.get("taskId")}
    worktree_keys = "worktree branch activeTaskIds runnerVersion installationStatus cleanupStatus".split()
    worktrees = [
        {
            **{key: item.get(key) for key in worktree_keys},
            "historyCount": max(
                len(item.get("taskIds", [])) - len(item.get("activeTaskIds", [])), 0
            ),
        }
        for item in payload.get("worktrees", [])
        if active_ids.intersection(str(value) for value in item.get("taskIds", []))
    ]
    cleanup = payload.get("cleanup", {})
    baseline = payload.get("workflowBaseline") or {}
    removable_tasks = {x["taskId"] for x in cleanup.get("removableWorktrees", [])}
    closeout_tasks = sorted(
        (
            item
            for item in tasks
            if item.get("lifecycle") == "integrated-unclosed"
            and (item.get("nextAction") or {}).get("command")
            and item.get("taskId") in removable_tasks
        ),
        key=lambda item: str(item.get("taskId") or ""),
    )
    action = closeout_tasks[0]["nextAction"] if closeout_tasks else None
    closeout_action = None
    if action:
        closeout_action = dict(
            actor="codex",
            kind="repair",
            summary=action.get("reason"),
            command=action.get("command"),
        )
    return {
        "workflowVersion": payload.get("workflowVersion"),
        "executionRunner": payload.get("executionRunner"),
        "installation": payload.get("installation"),
        "workflowBaseline": {
            **{
                key: baseline.get(key)
                for key in ("status", "baseBranch", "safeToCommit", "nextAction")
            },
            "trackedCount": len(baseline.get("tracked", [])),
            "untrackedCount": len(baseline.get("untracked", [])),
            "modifiedCount": len(baseline.get("modified", [])),
        },
        "overview": payload.get("overview", {}),
        "issues": payload.get("issues", []),
        "tasks": tasks,
        "worktrees": worktrees,
        "topologicalOrder": [
            task_id
            for task_id in payload.get("topologicalOrder", [])
            if str(task_id) in active_ids
        ],
        "cleanup": {
            "removableWorktrees": len(cleanup.get("removableWorktrees", [])),
            "retainedWorktrees": len(cleanup.get("retainedWorktrees", [])),
            "retainedBranches": len(cleanup.get("retainedBranches", [])),
            "staleRegistryEntries": len(cleanup.get("staleRegistryEntries", [])),
        },
        "closeout": {
            "pending": len(closeout_tasks),
            "taskIds": [item["taskId"] for item in closeout_tasks],
            "nextAction": closeout_action,
        },
        "evolution": {
            "candidateCount": payload.get("evolution", {}).get("candidateCount", 0),
            "command": payload.get("evolution", {}).get("command"),
        },
    }


def command_status(
    root: Path,
    json_output: bool = False,
    all_worktrees: bool = False,
    compact: bool = False,
    paths: list[str] | None = None,
) -> None:
    path_queries = paths or []
    if path_queries:
        if all_worktrees or compact or not json_output:
            raise FlowError(
                "status --path requires --json and cannot use --all/--compact"
            )
        flow_policy.validate_scope_entries(root, path_queries)
        payload = flow_parallel.path_writer_status(root, path_queries)
        if payload["activeWriters"]:
            payload["nextAction"] = {
                "actor": "codex",
                "kind": "safety-stop",
                "summary": "Use L1 isolation or wait for the listed writer to finish.",
            }
        else:
            payload["nextAction"] = {
                "actor": "codex",
                "kind": "work",
                "summary": "No active writer overlaps the requested paths.",
            }
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    if compact and not (all_worktrees and json_output):
        raise FlowError("status --compact requires --all --json")
    if all_worktrees:
        if not flow_state.is_git_repo(root):
            raise FlowError("status --all requires a Git repository")
        try:
            payload = flow_parallel.aggregate(root)
        except flow_parallel.ParallelError as exc:
            raise FlowError(str(exc)) from exc
        payload["workflowVersion"] = flow_state.VERSION
        payload["executionRunner"] = {
            "version": flow_state.TOOL_VERSION,
            "source": "bundled",
        }
        state = (
            flow_state.load_state(root)
            if flow_state.state_path(root).is_file()
            or flow_state.legacy_state_path(root).is_file()
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
                worktree = Path(str(item.get("worktree", "")))
                item["workflowBypass"] = {
                    "status": "clear",
                    "paths": [],
                    "evolutionCandidate": False,
                }
                if item.get("lifecycle") == "orphaned-record":
                    continue
                if worktree.is_dir() and (
                    flow_state.state_path(worktree).is_file()
                    or flow_state.legacy_state_path(worktree).is_file()
                ):
                    task_state = flow_state.load_state(worktree)
                    flow_policy.refresh_approval(worktree, task_state)
                    if (task_state.get("activeTask") or {}).get("id") == item.get(
                        "taskId"
                    ):
                        item["workflowBypass"] = workflow_bypass_status(
                            worktree, task_state
                        )
                        if item["workflowBypass"]["status"] == "detected":
                            item["nextAction"] = workflow_bypass_action()
        except flow_automation.AutomationError as exc:
            raise FlowError(str(exc)) from exc
        roots = [root]
        roots.extend(
            Path(str(item["worktree"]))
            for item in payload["tasks"]
            if item.get("worktree") and Path(str(item["worktree"])).is_dir()
        )
        payload["evolution"] = evolution_projection(roots)
        payload["worktrees"] = worktree_status_projection(
            root, payload["tasks"], payload.get("cleanup", {})
        )
        payload["overview"] = {
            "active": sum(
                1
                for item in payload["tasks"]
                if item.get("lifecycle") not in {"closed", "integrated"}
            ),
            "blocked": sum(
                1
                for item in payload["tasks"]
                if item.get("readiness") == "blocked" or item.get("issues")
            ),
            "cleanupCandidates": len(
                payload.get("cleanup", {}).get("removableWorktrees", [])
            ),
            "issues": len(payload.get("issues", [])),
            "worktrees": len(payload["worktrees"]),
        }
        if json_output:
            if compact:
                payload = compact_all_status(payload)
            print(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":") if compact else None,
                )
            )
            return
        overview = payload["overview"]
        print(
            f"已完成：已登记 {len(payload['tasks'])} 个任务，"
            f"归并为 {overview['worktrees']} 个工作树"
        )
        print(
            "当前："
            f"{overview['active']} 个活动任务，{overview['blocked']} 个阻断，"
            f"{overview['issues']} 个状态问题"
        )
        print(
            "需要你操作："
            + (
                "处理安全阻断或批准项"
                if overview["blocked"] or overview["issues"]
                else "无"
            )
        )
        return
    state = flow_state.load_state(root)
    active = state.get("activeTask")
    if active and not flow_state.task_path(root, active["id"]).is_file():
        action = orphaned_record_action(active["id"])
        payload = {
            "phase": state.get("phase"),
            "localMode": flow_state.load_config(root)
            .get("policy", {})
            .get("local_mode", "advisory"),
            "activeTask": active["id"],
            "approval": "invalid",
            "verification": "missing/stale",
            "fullProfile": "missing/stale",
            "scope": {"status": "not-applicable", "outOfScope": []},
            "lifecycle": "orphaned-record",
            "nextAction": action,
            "installation": installation_status(root, state),
            "workflowBaseline": workflow_baseline_status(root, state),
            "workflowBypass": {
                "status": "clear",
                "paths": [],
                "evolutionCandidate": False,
            },
            "automation": None,
            "evolution": evolution_projection([root]),
        }
        payload["interaction"] = interaction_projection(state, payload, action)
        if json_output:
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            return
        print_interaction(payload["interaction"])
        return
    flow_policy.refresh_approval(root, state)
    active = state.get("activeTask")
    approval = state["approvals"]["task"]
    approval_valid_now = bool(approval.get("valid"))
    verification = (
        "current"
        if active
        and approval_valid_now
        and flow_policy.verification_current(root, state)
        else "missing/stale"
    )
    mode = flow_state.load_config(root).get("policy", {}).get("local_mode", "advisory")
    full_profile = (
        "current"
        if active
        and approval_valid_now
        and flow_policy.full_profile_current(root, state)
        else "missing/stale"
    )
    lifecycle, lifecycle_action = current_task_lifecycle(root, state)
    action = lifecycle_action or flow_policy.next_action(
        root, state, approval_valid_now, verification, full_profile
    )
    scope = flow_policy.task_scope_status(root, state)
    workflow_bypass = workflow_bypass_status(root, state)
    if workflow_bypass["status"] == "detected":
        action = workflow_bypass_action()
    verification_record = (
        state.get("verification") or {} if verification == "current" else {}
    )
    payload = {
        "phase": state.get("phase"),
        "localMode": mode,
        "activeTask": active["id"] if active else None,
        "approval": "valid" if approval_valid_now else "invalid",
        "verification": verification,
        "fullProfile": full_profile,
        "verificationLevel": verification_record.get("verificationLevel"),
        "verifiedFeatures": verification_record.get("verifiedFeatures", []),
        "scope": scope,
        "lifecycle": lifecycle,
        "nextAction": action,
        "installation": installation_status(root, state),
        "workflowBaseline": workflow_baseline_status(root, state),
        "workflowBypass": workflow_bypass,
        "evolution": evolution_projection([root]),
    }
    payload["interaction"] = interaction_projection(state, payload, action)
    if active and flow_state.task_path(root, active["id"]).is_file():
        payload.update(
            flow_parallel.parse_task_context(
                flow_state.task_path(root, active["id"]).read_text(
                    encoding="utf-8", errors="replace"
                )
            )
        )
    if flow_state.is_git_repo(root):
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
    print_interaction(payload["interaction"])


def command_doctor(
    root: Path,
    json_output: bool = False,
    all_worktrees: bool = False,
    repair: bool = False,
    migrate_records: str | None = None,
) -> None:
    issues: list[str] = []
    warnings: list[str] = []
    if flow_state.is_git_repo(root):
        warnings.extend(flow_state.migrate_legacy_state(root, remove_untracked=repair))
        cache_retained = flow_state.clean_managed_bytecode(root) if repair else []
        warnings.extend(
            f"retained unknown cache entry: {relative}" for relative in cache_retained
        )
    if repair:
        if not all_worktrees or not flow_state.is_git_repo(root):
            raise FlowError("doctor --repair requires --all in a Git repository")
        flow_parallel.remove_stale_lock(root)
        flow_parallel.rebuild_registry(root)
        if migrate_records == "private":
            migration = flow_records.migrate_records_to_private(root)
            print(
                "migrated records to private storage: "
                f"{len(migration['moved'])} full, "
                f"{len(migration['summarized'])} compact, "
                f"{len(migration['audits'])} public audit"
            )
    elif migrate_records:
        raise FlowError("--migrate-records requires doctor --all --repair")
    if not (flow_state.spec_root(root) / "index.md").is_file():
        issues.append("missing spec/index.md")
    if not flow_state.state_path(root).is_file():
        issues.append(f"missing workflow state: {flow_state.state_path(root)}")
    required_record_dirs = ["changes", "evidence", "archive"]
    if flow_state.record_settings(root)["storage"] == "private":
        required_record_dirs.append("history")
    for relative in required_record_dirs:
        if not (flow_state.records_root(root) / relative).is_dir():
            issues.append(f"missing record directory: {relative}")
    if not flow_state.is_git_repo(root):
        issues.append("not a Git repository")
    else:
        try:
            flow_automation.load_journal(root)
        except flow_automation.AutomationError as exc:
            issues.append(str(exc))
    try:
        flow_state.load_config(root)
    except FlowError as exc:
        issues.append(str(exc))
    try:
        state = flow_state.load_state(root)
        if state.get("workflowVersion") != flow_state.VERSION:
            issues.append("unsupported workflow version")
        active = state.get("activeTask")
        if active and not flow_state.task_path(root, active["id"]).is_file():
            issues.append("active task file is missing")
        if (
            active
            and active.get("risk") in {"L1", "L2"}
            and flow_state.is_git_repo(root)
        ):
            baseline = workflow_baseline_status(root, state)
            if baseline["status"] != "current":
                warnings.append(
                    "workflow baseline is not current before a high-risk task: "
                    f"{baseline['status']} on {baseline['baseBranch']}"
                )
    except FlowError as exc:
        issues.append(str(exc))
    evidence_dir = flow_state.records_root(root) / "evidence"
    if evidence_dir.is_dir():
        for path in sorted(evidence_dir.glob("*.json")):
            try:
                flow_state.upgrade_evidence(flow_state.read_json(path), path.stem)
            except FlowError as exc:
                issues.append(str(exc))
    tasks: list[dict[str, Any]] = []
    repair_plan: dict[str, Any] | None = None
    if all_worktrees and flow_state.is_git_repo(root):
        try:
            aggregate = flow_parallel.aggregate(root)
            tasks = aggregate["tasks"]
            issues.extend(aggregate["issues"])
            active_worktrees: set[str] = set()
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
                if worktree and not task.get("archived"):
                    if worktree in active_worktrees:
                        issues.append(f"duplicate worktree registration: {worktree}")
                    active_worktrees.add(worktree)
                expected = task.get("branch")
                if task.get("worktreeExists") and expected and not task.get("archived"):
                    actual = flow_parallel.branch_name(Path(worktree))
                    if actual != expected:
                        issues.append(
                            f"{task.get('taskId')} branch mismatch: "
                            f"expected {expected}, found {actual}"
                        )
        except flow_parallel.ParallelError as exc:
            issues.append(str(exc))
        try:
            repair_plan = flow_parallel.registry_repair_plan(root)
        except flow_parallel.ParallelError as exc:
            warnings.append(f"registry repair preview unavailable: {exc}")
    if issues:
        if json_output:
            print(
                json.dumps(
                    {
                        "status": "error",
                        "issues": sorted(set(issues)),
                        "warnings": warnings,
                        "workflowVersion": flow_state.VERSION,
                        "tasks": tasks if all_worktrees else None,
                        "repairPlan": repair_plan,
                    },
                    sort_keys=True,
                )
            )
        raise FlowError("doctor found issues: " + "; ".join(issues))
    if json_output:
        print(
            json.dumps(
                {
                    "status": "ok",
                    "issues": [],
                    "warnings": warnings,
                    "workflowVersion": flow_state.VERSION,
                    "tasks": tasks if all_worktrees else None,
                    **({"repairPlan": repair_plan} if repair else {}),
                },
                sort_keys=True,
            )
        )
    else:
        for warning in warnings:
            print(f"warning: {warning}")
        print("doctor: ok")
