"""Git worktree registry and dependency helpers for Production Flow."""

from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REGISTRY_DIRECTORY = "rigorbreeze"
REGISTRY_NAME = "registry.json"


class ParallelError(RuntimeError):
    pass


def path_matches_glob(relative: str, pattern: str) -> bool:
    """Match repository paths without letting a single `*` cross `/`."""
    path_parts = tuple(part for part in relative.strip("/").split("/") if part)
    pattern_parts = tuple(part for part in pattern.strip("/").split("/") if part)

    def matches(path_index: int, pattern_index: int) -> bool:
        if pattern_index == len(pattern_parts):
            return path_index == len(path_parts)
        candidate = pattern_parts[pattern_index]
        if candidate == "**":
            return matches(path_index, pattern_index + 1) or (
                path_index < len(path_parts) and matches(path_index + 1, pattern_index)
            )
        return bool(
            path_index < len(path_parts)
            and fnmatch.fnmatchcase(path_parts[path_index], candidate)
            and matches(path_index + 1, pattern_index + 1)
        )

    return matches(0, 0)


def parse_porcelain_paths(output: str) -> list[str]:
    """Parse `git status --porcelain=1 -z`, preserving unusual path names."""
    entries = output.split("\0")
    paths: set[str] = set()
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if len(entry) < 4:
            continue
        status = entry[:2]
        relative = entry[3:].replace("\\", "/")
        if relative:
            paths.add(relative)
        if ("R" in status or "C" in status) and index < len(entries):
            original = entries[index].replace("\\", "/")
            index += 1
            if original:
                paths.add(original)
    return sorted(paths)


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )


def git_path(root: Path, relative: str) -> Path | None:
    result = git(root, "rev-parse", "--git-path", relative)
    if result.returncode != 0:
        return None
    path = Path(result.stdout.strip())
    return path if path.is_absolute() else (root / path).resolve()


def git_common_dir(root: Path) -> Path | None:
    result = git(root, "rev-parse", "--git-common-dir")
    if result.returncode != 0:
        return None
    path = Path(result.stdout.strip())
    return path if path.is_absolute() else (root / path).resolve()


def git_dir(root: Path) -> Path | None:
    result = git(root, "rev-parse", "--git-dir")
    if result.returncode != 0:
        return None
    path = Path(result.stdout.strip())
    return path if path.is_absolute() else (root / path).resolve()


def is_linked_worktree(root: Path) -> bool:
    current = git_dir(root)
    common = git_common_dir(root)
    return bool(current and common and current.resolve() != common.resolve())


def worktree_state_path(root: Path, legacy: Path) -> Path:
    private = git_path(root, f"{REGISTRY_DIRECTORY}/state.json")
    return private or legacy


def registry_path(root: Path) -> Path | None:
    common = git_common_dir(root)
    return common / REGISTRY_DIRECTORY / REGISTRY_NAME if common else None


def common_lock_path(root: Path, fallback: Path) -> Path:
    common = git_common_dir(root)
    return common / REGISTRY_DIRECTORY / "flow.lock" if common else fallback


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def load_registry(root: Path) -> dict[str, Any]:
    path = registry_path(root)
    if path is None or not path.exists():
        return {"version": 1, "tasks": {}}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ParallelError(f"invalid project task registry: {path}: {exc}") from exc
    if not isinstance(value.get("tasks"), dict):
        raise ParallelError(f"invalid project task registry: {path}")
    value.setdefault("version", 1)
    return value


def save_registry(root: Path, registry: dict[str, Any]) -> None:
    path = registry_path(root)
    if path is not None:
        atomic_json(path, registry)


def worktrees(root: Path) -> list[dict[str, str]]:
    result = git(root, "worktree", "list", "--porcelain")
    if result.returncode != 0:
        return []
    entries: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in result.stdout.splitlines() + [""]:
        if not line:
            if current:
                entries.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        if key in {"worktree", "HEAD", "branch"}:
            current[key] = value
    return entries


def branch_name(root: Path) -> str | None:
    result = git(root, "branch", "--show-current")
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else None


def default_base_branch(root: Path) -> str:
    remote = git(root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if remote.returncode == 0 and "/" in remote.stdout.strip():
        return remote.stdout.strip().split("/", 1)[1]
    for candidate in ("main", "master"):
        if git(root, "show-ref", "--verify", f"refs/heads/{candidate}").returncode == 0:
            return candidate
    current = branch_name(root)
    if not current:
        raise ParallelError("unable to determine a baseline branch")
    return current


def default_worktree_path(root: Path, task_id: str) -> Path:
    common = git_common_dir(root)
    if common is None:
        raise ParallelError("automatic worktrees require a Git repository")
    repository = common.parent
    return repository.parent / f".{repository.name}-worktrees" / task_id.lower()


def create_worktree(
    root: Path,
    task_id: str,
    base_branch: str | None = None,
    destination_root: Path | None = None,
) -> Path:
    if git(root, "status", "--porcelain").stdout.strip():
        raise ParallelError(
            "automatic worktree creation requires a clean project entry worktree"
        )
    base = base_branch or default_base_branch(root)
    branch = f"rigorbreeze/{task_id.lower()}"
    destination = (
        destination_root.resolve() / task_id.lower()
        if destination_root
        else default_worktree_path(root, task_id)
    )
    if destination.exists():
        raise ParallelError(f"worktree destination already exists: {destination}")
    if git(root, "show-ref", "--verify", f"refs/heads/{branch}").returncode == 0:
        raise ParallelError(f"task branch already exists: {branch}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    result = git(root, "worktree", "add", "-b", branch, str(destination), base)
    if result.returncode != 0:
        raise ParallelError(result.stderr.strip() or "unable to create worktree")
    return destination


def update_task(
    root: Path,
    task_id: str,
    state: dict[str, Any],
    *,
    scopes: Iterable[str] | None = None,
    status: dict[str, Any] | None = None,
) -> None:
    if registry_path(root) is None:
        return
    registry = load_registry(root)
    active = state.get("activeTask") or {}
    existing = registry["tasks"].get(task_id, {})
    task_values = active or existing
    entry = {
        **existing,
        "taskId": task_id,
        "title": task_values.get("title"),
        "risk": task_values.get("risk"),
        "phase": state.get("phase"),
        "dependsOn": list(task_values.get("dependsOn", [])),
        "worktree": str(root.resolve()),
        "branch": branch_name(root),
        "baseBranch": task_values.get("baseBranch"),
        "baseSha": task_values.get("baseSha"),
        "head": git(root, "rev-parse", "HEAD").stdout.strip() or None,
        "allowedScope": list(
            scopes if scopes is not None else existing.get("allowedScope", [])
        ),
        "runtimeClaims": list(
            task_values.get("runtimeClaims", existing.get("runtimeClaims", []))
        ),
        "managedByFlow": existing.get("managedByFlow", False),
        "createdPath": existing.get("createdPath"),
        "createdAt": existing.get("createdAt"),
        "updatedAt": state.get("updatedAt"),
        **(status or {}),
    }
    if state.get("phase") == "archived":
        entry["archived"] = True
        entry["runtimeClaims"] = []
        entry.pop("owner", None)
        entry.pop("ownerPid", None)
    registry["tasks"][task_id] = entry
    save_registry(root, registry)


def mark_managed_worktree(root: Path, task_id: str, worktree: Path) -> None:
    registry = load_registry(root)
    entry = registry["tasks"].get(task_id)
    if not isinstance(entry, dict):
        raise ParallelError(f"task is missing from project registry: {task_id}")
    resolved = str(worktree.resolve())
    if entry.get("worktree") != resolved:
        raise ParallelError(f"task worktree does not match registry: {task_id}")
    entry["managedByFlow"] = True
    entry["createdPath"] = resolved
    entry["createdAt"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    save_registry(root, registry)


def rebuild_registry(root: Path) -> dict[str, Any]:
    registry: dict[str, Any] = {"version": 1, "tasks": {}}
    for item in worktrees(root):
        worktree_value = item.get("worktree")
        if not worktree_value:
            continue
        worktree = Path(worktree_value)
        state_file = worktree_state_path(worktree, worktree / "spec" / "state.json")
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        active = state.get("activeTask")
        last = state.get("lastClosed") or {}
        task_id = (active or {}).get("id") or last.get("id")
        if not task_id:
            continue
        scopes: list[str] = []
        task_file = worktree / "spec" / "changes" / f"{task_id}.md"
        if task_file.is_file():
            content = task_file.read_text(encoding="utf-8", errors="replace")
            match = re.search(r"(?ms)^## Allowed scope\s*$\n(.*?)(?=^## |\Z)", content)
            if match:
                for line in match.group(1).splitlines():
                    value = re.sub(r"^\s*[-*]\s+", "", line).strip().strip("`")
                    if value:
                        scopes.append(value.replace("\\", "/"))
        entry = {
            "taskId": task_id,
            "title": (active or {}).get("title"),
            "risk": (active or {}).get("risk"),
            "phase": state.get("phase"),
            "dependsOn": list((active or {}).get("dependsOn", [])),
            "worktree": str(worktree.resolve()),
            "branch": item.get("branch", "").removeprefix("refs/heads/") or None,
            "baseBranch": (active or {}).get("baseBranch"),
            "baseSha": (active or {}).get("baseSha"),
            "head": item.get("HEAD"),
            "allowedScope": scopes,
            "runtimeClaims": parse_runtime_claims(
                content if task_file.is_file() else ""
            ),
            "managedByFlow": False,
            "createdPath": None,
            "createdAt": None,
            "updatedAt": state.get("updatedAt"),
            "archived": state.get("phase") == "archived",
        }
        registry["tasks"][task_id] = entry
    save_registry(root, registry)
    return registry


def default_session_id() -> str:
    return os.environ.get("RIGORBREEZE_SESSION_ID") or f"ppid-{os.getppid()}"


def process_alive(pid: Any) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def claim_worktree(
    root: Path,
    session_id: str | None = None,
    *,
    check_resources: bool = True,
) -> None:
    registry = load_registry(root)
    resolved = str(root.resolve())
    current = next(
        (
            entry
            for entry in registry["tasks"].values()
            if entry.get("worktree") == resolved and not entry.get("archived")
        ),
        None,
    )
    if current is None:
        return
    task_id = str(current.get("taskId"))
    task_file = root / "spec" / "changes" / f"{task_id}.md"
    if task_file.is_file():
        current["runtimeClaims"] = parse_runtime_claims(
            task_file.read_text(encoding="utf-8", errors="replace")
        )
    if check_resources:
        conflicts = runtime_claim_conflicts(
            registry["tasks"], task_id, current.get("runtimeClaims", [])
        )
        if conflicts:
            save_registry(root, registry)
            first = conflicts[0]
            raise ParallelError(
                f"runtime claim {first['claim']} is owned by active task "
                f"{first['taskId']}"
            )
    requested = session_id or default_session_id()
    owner = current.get("owner")
    owner_pid = current.get("ownerPid")
    if owner and owner != requested and process_alive(owner_pid):
        raise ParallelError(
            f"worktree is already claimed by another active window: {owner}"
        )
    current["owner"] = requested
    current["ownerPid"] = os.getppid()
    save_registry(root, registry)


def release_worktree(root: Path, session_id: str | None = None) -> None:
    registry = load_registry(root)
    resolved = str(root.resolve())
    requested = session_id or default_session_id()
    for current in registry["tasks"].values():
        if current.get("worktree") != resolved:
            continue
        if current.get("owner") not in {None, requested}:
            raise ParallelError(
                f"worktree is claimed by another active window: {current.get('owner')}"
            )
        current.pop("owner", None)
        current.pop("ownerPid", None)
    save_registry(root, registry)


def parse_runtime_claims(content: str) -> list[str]:
    match = re.search(r"(?mi)^Runtime-Claims:\s*(.+?)\s*$", content)
    if not match or match.group(1).strip().lower() in {"none", "n/a"}:
        return []
    return sorted(
        {item.strip().lower() for item in match.group(1).split(",") if item.strip()}
    )


def runtime_claim_conflicts(
    tasks: dict[str, dict[str, Any]], task_id: str, claims: Iterable[str]
) -> list[dict[str, Any]]:
    requested = set(claims)
    conflicts: list[dict[str, Any]] = []
    for other_id, other in tasks.items():
        if other_id == task_id or other.get("archived") or other.get("integrated"):
            continue
        for claim in sorted(requested & set(other.get("runtimeClaims", []))):
            conflicts.append(
                {
                    "claim": claim,
                    "taskId": other_id,
                    "owner": other.get("owner"),
                }
            )
    return conflicts


def reconcile_integrations(root: Path, cleanup: bool = False) -> dict[str, Any]:
    registry = load_registry(root)
    integrated: list[str] = []
    removed: list[str] = []
    retained: list[dict[str, str]] = []
    current = root.resolve()
    for task_id, task in registry["tasks"].items():
        if not is_integrated(root, task):
            continue
        task["integrated"] = True
        task["phase"] = "integrated"
        task.pop("owner", None)
        task.pop("ownerPid", None)
        integrated.append(task_id)
        worktree_value = task.get("worktree")
        if not cleanup or not worktree_value or task.get("worktreeRemoved"):
            continue
        worktree = Path(worktree_value).resolve()
        reason = worktree_cleanup_reason(root, task, current)
        if reason:
            retained.append({"taskId": task_id, "reason": reason})
            continue
        result = git(root, "worktree", "remove", str(worktree))
        if result.returncode == 0:
            task["worktreeRemoved"] = True
            removed.append(task_id)
        else:
            retained.append({"taskId": task_id, "reason": "remove-failed"})
    save_registry(root, registry)
    return {
        "integrated": sorted(integrated),
        "removed": sorted(removed),
        "retained": sorted(retained, key=lambda item: item["taskId"]),
    }


def integration_status(
    root: Path, branch: str | None, base: str | None, base_sha: str | None = None
) -> str:
    """Return a conservative proof label for branch integration."""

    if not branch or not base:
        return "unknown"
    branch_head = git(root, "rev-parse", branch)
    base_head = git(root, "rev-parse", base)
    if branch_head.returncode != 0 or base_head.returncode != 0:
        return "unknown"
    if branch_head.stdout.strip() == base_head.stdout.strip():
        return "contained"
    if git(root, "merge-base", "--is-ancestor", branch, base).returncode == 0:
        return "contained"
    comparison_base = base_sha
    if not comparison_base:
        common = git(root, "merge-base", branch, base)
        comparison_base = common.stdout.strip() if common.returncode == 0 else None
    if not comparison_base:
        return "unknown"
    if (
        git(root, "merge-base", "--is-ancestor", comparison_base, branch).returncode
        != 0
    ):
        return "not-integrated"
    cherry = git(root, "cherry", base, branch, comparison_base)
    if cherry.returncode != 0:
        return "unknown"
    patches = [line.strip() for line in cherry.stdout.splitlines() if line.strip()]
    if patches and all(line.startswith("- ") for line in patches):
        return "patch-equivalent"
    return "not-integrated"


def cleanup_unmanaged_worktree(
    root: Path,
    *,
    worktree: Path,
    base: str,
    expected_head: str,
) -> dict[str, Any]:
    target = worktree.resolve()
    current = root.resolve()
    if target == current:
        raise ParallelError("the current worktree cannot be removed")
    actual = next(
        (
            item
            for item in worktrees(root)
            if item.get("worktree") and Path(item["worktree"]).resolve() == target
        ),
        None,
    )
    if actual is None:
        raise ParallelError(f"worktree is not registered with Git: {target}")
    head = actual.get("HEAD") or ""
    if not expected_head or expected_head != head:
        raise ParallelError(
            f"unmanaged worktree expected HEAD {expected_head or '<missing>'}, found {head}"
        )
    status = git(target, "status", "--porcelain")
    if status.returncode != 0 or status.stdout.strip():
        raise ParallelError("unmanaged worktree must be clean before removal")
    private_state = worktree_state_path(target, target / "spec" / "state.json")
    if private_state.is_file():
        try:
            state = json.loads(private_state.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ParallelError(
                f"unable to prove unmanaged worktree state is inactive: {private_state}"
            ) from exc
        if state.get("activeTask"):
            raise ParallelError("unmanaged worktree still has an active private task")
    branch = actual.get("branch", "").removeprefix("refs/heads/") or None
    proof = integration_status(root, branch, base)
    if proof not in {"contained", "patch-equivalent"}:
        raise ParallelError(
            f"unmanaged worktree is not proven integrated into {base}: {proof}"
        )
    result = git(root, "worktree", "remove", str(target))
    if result.returncode != 0:
        raise ParallelError(result.stderr.strip() or "unable to remove worktree")
    return {
        "integrated": [],
        "removed": [str(target)],
        "retained": [],
        "clean": True,
        "integrationStatus": proof,
        "expectedHead": expected_head,
        "requiresConfirmation": False,
    }


def worktree_cleanup_reason(
    root: Path, task: dict[str, Any], current: Path
) -> str | None:
    worktree_value = task.get("worktree")
    if not worktree_value:
        return "missing"
    worktree = Path(str(worktree_value)).resolve()
    if not task.get("managedByFlow"):
        return "unmanaged"
    created_path = task.get("createdPath")
    if not created_path or Path(str(created_path)).resolve() != worktree:
        return "path-mismatch"
    if worktree == current:
        return "current-worktree"
    if not worktree.is_dir():
        return "missing"
    status = git(worktree, "status", "--porcelain")
    if status.returncode != 0:
        return "status-error"
    if status.stdout.strip():
        return "dirty"
    return None


def cleanup_projection(
    root: Path, registry: dict[str, Any] | None = None
) -> dict[str, list[dict[str, Any]]]:
    current = root.resolve()
    project_registry = registry or load_registry(root)
    removable: list[dict[str, Any]] = []
    retained: list[dict[str, Any]] = []
    branches: list[dict[str, Any]] = []
    registered_paths: set[str] = set()

    for task_id, task in project_registry["tasks"].items():
        worktree_value = task.get("worktree")
        if worktree_value:
            registered_paths.add(str(Path(str(worktree_value)).resolve()))
        if not is_integrated(root, task):
            continue
        branch = task.get("branch")
        if isinstance(branch, str) and branch.startswith("rigorbreeze/"):
            branch_ref = git(root, "show-ref", "--verify", f"refs/heads/{branch}")
            if branch_ref.returncode == 0:
                branches.append(
                    {
                        "taskId": task_id,
                        "branch": branch,
                        "reason": "preserved-by-policy",
                    }
                )
        if not worktree_value or task.get("worktreeRemoved"):
            continue
        worktree = Path(str(worktree_value)).resolve()
        if worktree == current:
            continue
        observed_head = git(worktree, "rev-parse", "HEAD")
        expected_head = (
            observed_head.stdout.strip()
            if observed_head.returncode == 0
            else task.get("head")
        )
        clean_result = git(worktree, "status", "--porcelain")
        clean = clean_result.returncode == 0 and not clean_result.stdout.strip()
        integration = integration_status(
            root, branch, task.get("baseBranch"), task.get("baseSha")
        )
        item = {
            "taskId": task_id,
            "worktree": str(worktree),
            "branch": branch,
            "clean": clean,
            "integrationStatus": integration,
            "expectedHead": expected_head,
            "requiresConfirmation": False,
        }
        reason = worktree_cleanup_reason(root, task, current)
        if reason:
            retained.append({**item, "reason": reason})
        else:
            removable.append(item)

    for actual in worktrees(root):
        worktree_value = actual.get("worktree")
        if not worktree_value:
            continue
        worktree = Path(worktree_value).resolve()
        if worktree == current or str(worktree) in registered_paths:
            continue
        branch = actual.get("branch", "").removeprefix("refs/heads/") or None
        base = default_base_branch(root)
        status = git(worktree, "status", "--porcelain")
        clean = status.returncode == 0 and not status.stdout.strip()
        retained.append(
            {
                "taskId": None,
                "worktree": str(worktree),
                "branch": branch,
                "reason": "unregistered",
                "clean": clean,
                "integrationStatus": integration_status(root, branch, base),
                "expectedHead": actual.get("HEAD"),
                "requiresConfirmation": True,
            }
        )

    def cleanup_key(item: dict[str, Any]) -> tuple[str, str]:
        return (
            str(item.get("taskId") or ""),
            str(item.get("worktree") or item.get("branch") or ""),
        )

    return {
        "removableWorktrees": sorted(removable, key=cleanup_key),
        "retainedWorktrees": sorted(retained, key=cleanup_key),
        "retainedBranches": sorted(branches, key=cleanup_key),
    }


def dependency_errors(tasks: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for task_id, task in tasks.items():
        for dependency in task.get("dependsOn", []):
            if dependency not in tasks:
                errors.append(f"{task_id} depends on missing task {dependency}")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str, trail: list[str]) -> None:
        if task_id in visiting:
            cycle = trail[trail.index(task_id) :] + [task_id]
            errors.append("dependency cycle: " + " -> ".join(cycle))
            return
        if task_id in visited or task_id not in tasks:
            return
        visiting.add(task_id)
        for dependency in tasks[task_id].get("dependsOn", []):
            visit(dependency, trail + [dependency])
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in tasks:
        visit(task_id, [task_id])
    return sorted(set(errors))


def topological_order(tasks: dict[str, dict[str, Any]]) -> list[str]:
    errors = dependency_errors(tasks)
    if errors:
        raise ParallelError("; ".join(errors))
    indegree = {task_id: 0 for task_id in tasks}
    dependents: dict[str, list[str]] = {task_id: [] for task_id in tasks}
    for task_id, task in tasks.items():
        for dependency in task.get("dependsOn", []):
            indegree[task_id] += 1
            dependents[dependency].append(task_id)
    ready = sorted(task_id for task_id, count in indegree.items() if count == 0)
    ordered: list[str] = []
    while ready:
        task_id = ready.pop(0)
        ordered.append(task_id)
        for dependent in sorted(dependents[task_id]):
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)
                ready.sort()
    if len(ordered) != len(tasks):
        raise ParallelError("dependency graph cannot be ordered")
    return ordered


def is_integrated(root: Path, task: dict[str, Any]) -> bool:
    if task.get("integrated") or task.get("archived"):
        return True
    branch = task.get("branch")
    base = task.get("baseBranch")
    if not branch or not base:
        return False
    proof = integration_status(root, branch, base, task.get("baseSha"))
    if proof == "contained":
        branch_head = git(root, "rev-parse", branch).stdout.strip()
        return bool(task.get("baseSha") and branch_head != task.get("baseSha"))
    return proof == "patch-equivalent"


def task_readiness(
    root: Path, task: dict[str, Any], tasks: dict[str, dict[str, Any]]
) -> str:
    if task.get("archived") or is_integrated(root, task):
        return "integrated"
    for dependency in task.get("dependsOn", []):
        upstream = tasks.get(dependency)
        if upstream is None or not is_integrated(root, upstream):
            return "blocked"
    return "ready"


def aggregate(root: Path) -> dict[str, Any]:
    registry = load_registry(root)
    tasks = registry["tasks"]
    errors = dependency_errors(tasks)
    result: list[dict[str, Any]] = []
    for task_id in sorted(tasks):
        item = dict(tasks[task_id])
        item.setdefault("runtimeClaims", [])
        item["runtimeConflicts"] = runtime_claim_conflicts(
            tasks, task_id, item["runtimeClaims"]
        )
        worktree = Path(str(item.get("worktree", "")))
        item["worktreeExists"] = worktree.is_dir()
        observed_head = (
            git(worktree, "rev-parse", "HEAD") if item["worktreeExists"] else None
        )
        if observed_head and observed_head.returncode == 0:
            item["head"] = observed_head.stdout.strip()
        item["readiness"] = task_readiness(root, item, tasks)
        base = item.get("baseBranch")
        base_head = git(root, "rev-parse", base) if base else None
        item["baselineStale"] = bool(
            base_head
            and base_head.returncode == 0
            and item.get("baseSha")
            and base_head.stdout.strip() != item.get("baseSha")
        )
        if item["readiness"] == "integrated" and not item.get("archived"):
            item["lifecycle"] = "integrated-unclosed"
            item["baselineStale"] = False
            item["nextAction"] = {
                "reason": "The task is integrated but its workflow record is still open.",
                "command": (
                    "python scripts/rigorbreeze.py archive --outcome reconciled "
                    f"--reason <reason> --expected-head {item.get('head') or '<SHA>'}"
                ),
            }
        elif item.get("archived"):
            item["lifecycle"] = "closed"
            item["baselineStale"] = False
            item.pop("nextAction", None)
        elif item["baselineStale"]:
            item["lifecycle"] = "active"
            item["verification"] = "missing/stale"
            item["fullProfile"] = "missing/stale"
            item["nextAction"] = {
                "reason": "The baseline branch changed after task approval.",
                "command": "incorporate the latest baseline, then rerun affected/full",
            }
        elif item["readiness"] == "blocked":
            item["lifecycle"] = "active"
            item["nextAction"] = {
                "reason": "One or more Depends-On tasks are not integrated.",
                "command": "wait for dependencies, then refresh status --all --json",
            }
        else:
            item["lifecycle"] = "active"
        result.append(item)
    order = [] if errors else topological_order(tasks)
    return {
        "tasks": result,
        "issues": errors,
        "topologicalOrder": order,
        "cleanup": cleanup_projection(root, registry),
    }


def patterns_overlap(left: str, right: str) -> bool:
    a = left.strip("/")
    b = right.strip("/")
    if not a or not b:
        return True
    wildcard = any(char in a + b for char in "*?[")
    if wildcard:
        prefix_a = re.split(r"[*?[]", a, maxsplit=1)[0].rstrip("/")
        prefix_b = re.split(r"[*?[]", b, maxsplit=1)[0].rstrip("/")
        if (
            not prefix_a
            or not prefix_b
            or prefix_a == prefix_b
            or prefix_a.startswith(prefix_b + "/")
            or prefix_b.startswith(prefix_a + "/")
        ):
            return True
        probes = {a.rstrip("*?/"), b.rstrip("*?/"), a, b}
        return any(
            path_matches_glob(probe, a) and path_matches_glob(probe, b)
            for probe in probes
        )
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def overlapping_task(
    root: Path,
    task_id: str,
    scopes: Iterable[str],
    approved_overlaps: Iterable[str],
) -> tuple[str, str, str] | None:
    registry = load_registry(root)
    ignored = set(approved_overlaps)
    for other_id, other in registry["tasks"].items():
        if other_id == task_id or other_id in ignored:
            continue
        if other.get("archived") or is_integrated(root, other):
            continue
        for left in scopes:
            for right in other.get("allowedScope", []):
                if patterns_overlap(left, right):
                    return other_id, left, right
    return None


def remove_stale_lock(root: Path) -> bool:
    path = common_lock_path(root, root / "spec" / ".flow.lock")
    if not path.exists():
        return False
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        content = ""
    pid = None
    for token in content.split():
        if token.startswith("pid="):
            try:
                pid = int(token[4:])
            except ValueError:
                pass
    alive = False
    if pid:
        try:
            os.kill(pid, 0)
            alive = True
        except OSError:
            pass
    if not alive:
        path.unlink(missing_ok=True)
        return True
    return False
