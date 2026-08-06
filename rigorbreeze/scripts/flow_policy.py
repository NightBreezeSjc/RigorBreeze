"""Task contracts, evidence freshness, and delivery policy for RigorBreeze."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import flow_automation
import flow_parallel
from flow_state import (
    DEPENDENCY_NAMES,
    DESTRUCTIVE_MIGRATION_PATTERN,
    EXCLUDED_DIRS,
    LOCK_NAME,
    MIGRATION_EVIDENCE_FIELDS,
    MIGRATION_PARTS,
    RELEASE_GOVERNANCE_FIELDS,
    SECURITY_EVIDENCE_FIELDS,
    TOOL_VERSION,
    FlowError,
    active_task,
    config_digest,
    configured_generated_paths,
    current_head,
    evidence_path,
    git,
    is_git_repo,
    load_config,
    load_evidence,
    now_iso,
    redact,
    safe_files,
    save_evidence,
    sha256_bytes,
    state_path,
    task_digest,
    task_path,
    working_tree_paths,
    write_json,
)


def allowed_scope(root: Path, state: dict[str, Any]) -> list[str]:
    active = active_task(state)
    content = task_path(root, active["id"]).read_text(encoding="utf-8")
    match = re.search(
        r"(?ms)^## Allowed scope\s*$\n(.*?)(?=^## |\Z)",
        content,
    )
    if not match:
        raise FlowError("task is missing an allowed scope section")
    entries: list[str] = []
    for line in match.group(1).splitlines():
        item = re.sub(r"^\s*[-*]\s+", "", line).strip().strip("`")
        if not item:
            continue
        item = re.split(r"\s+(?:#|—|–|-)\s+", item, maxsplit=1)[0].strip()
        if item:
            entries.append(item.replace("\\", "/"))
    return entries


def acceptance_ids(root: Path, state: dict[str, Any]) -> list[str]:
    active = active_task(state)
    content = task_path(root, active["id"]).read_text(encoding="utf-8")
    match = re.search(
        r"(?ms)^## Acceptance criteria\s*$\n(.*?)(?=^## |\Z)",
        content,
    )
    if not match:
        raise FlowError("task is missing an acceptance criteria section")
    identifiers: list[str] = []
    invalid: list[str] = []
    pattern = re.compile(r"^\s*[-*]\s+([A-Z][A-Z0-9]*(?:[/-][A-Z0-9]+)+)\s*:")
    for line in match.group(1).splitlines():
        if not line.strip():
            continue
        parsed = pattern.match(line)
        if parsed:
            identifiers.append(parsed.group(1))
        elif re.match(r"^\s*[-*]\s+", line):
            invalid.append(line.strip())
    if invalid:
        raise FlowError(
            "acceptance criteria must use machine-readable IDs: " + "; ".join(invalid)
        )
    if not identifiers:
        raise FlowError("task must declare at least one acceptance ID")
    duplicates = sorted(
        identifier
        for identifier in set(identifiers)
        if identifiers.count(identifier) > 1
    )
    if duplicates:
        raise FlowError("duplicate acceptance IDs: " + ", ".join(duplicates))
    return identifiers


def validate_scope_entries(root: Path, entries: list[str]) -> None:
    if not entries:
        raise FlowError("allowed scope must declare at least one repository path")
    invalid: list[str] = []
    for entry in entries:
        normalized = entry.strip().replace("\\", "/").strip("/")
        parts = [part for part in normalized.split("/") if part]
        absolute = Path(entry).is_absolute() or bool(
            re.match(r"^[A-Za-z]:[/\\]", entry)
        )
        contains_unresolved_parent = ".." in parts
        contains_space = bool(re.search(r"\s", normalized))
        wildcard_free = re.split(r"[*?\[]", normalized, maxsplit=1)[0].rstrip("/")
        existing = bool(wildcard_free and (root / wildcard_free).exists())
        looks_pathlike = bool(
            "/" in normalized
            or any(character in normalized for character in "*?[")
            or Path(normalized).suffix
            or existing
        )
        if (
            not normalized
            or absolute
            or contains_unresolved_parent
            or (contains_space and not looks_pathlike)
        ):
            invalid.append(entry)
    if invalid:
        raise FlowError(
            "allowed scope entries must be machine-readable repository-relative "
            "paths or globs: " + ", ".join(invalid)
        )


def declared_dependencies(root: Path, state: dict[str, Any]) -> list[str]:
    active = active_task(state)
    content = task_path(root, active["id"]).read_text(encoding="utf-8")
    match = re.search(r"(?mi)^Depends-On:\s*(.+?)\s*$", content)
    if not match:
        # v1/v2 task cards did not carry this field. Their stored dependency
        # list remains authoritative during the compatibility window.
        return list(active.get("dependsOn", []))
    value = match.group(1).strip()
    if value.lower() in {"none", "n/a"}:
        return []
    dependencies = [item.strip() for item in value.split(",") if item.strip()]
    invalid = [
        item
        for item in dependencies
        if not re.fullmatch(r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+", item)
    ]
    if invalid:
        raise FlowError("invalid Depends-On task IDs: " + ", ".join(invalid))
    return list(dict.fromkeys(dependencies))


def runtime_claims(root: Path, state: dict[str, Any]) -> list[str]:
    active = active_task(state)
    content = task_path(root, active["id"]).read_text(encoding="utf-8")
    match = re.search(r"(?mi)^Runtime-Claims:\s*(.+?)\s*$", content)
    if not match:
        return list(active.get("runtimeClaims", []))
    value = match.group(1).strip()
    if value.lower() in {"none", "n/a"}:
        return []
    claims = [item.strip().lower() for item in value.split(",") if item.strip()]
    invalid: list[str] = []
    for claim in claims:
        kind, separator, name = claim.partition(":")
        invalid_port = kind == "port" and (
            not name.isdigit() or not (1 <= int(name) <= 65535)
        )
        if (
            not separator
            or kind not in {"port", "service", "process", "app", "environment"}
            or not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", name)
            or invalid_port
        ):
            invalid.append(claim)
    if invalid:
        raise FlowError("invalid runtime claims: " + ", ".join(invalid))
    return sorted(set(claims))


def operational_modes(root: Path, state: dict[str, Any]) -> dict[str, str]:
    active = active_task(state)
    content = task_path(root, active["id"]).read_text(encoding="utf-8")
    match = re.search(r"(?mi)^Operational-Modes:\s*(.+?)\s*$", content)
    if not match:
        return dict(active.get("operationalModes", {}))
    value = match.group(1).strip()
    if value.lower().startswith("n/a"):
        if not re.fullmatch(r"(?i)n/a\s+-\s+\S(?:.*\S)?", value):
            raise FlowError("Operational-Modes N/A requires a machine-visible reason")
        return {}
    modes: dict[str, str] = {}
    invalid: list[str] = []
    for item in (part.strip() for part in value.split(",")):
        name, separator, requirement = item.partition("=")
        name = name.strip().lower()
        requirement = requirement.strip()
        if (
            not separator
            or not re.fullmatch(r"[a-z][a-z0-9-]*", name)
            or not re.fullmatch(r"[A-Z][A-Z0-9]*(?:[/-][A-Z0-9]+)+", requirement)
            or name in modes
        ):
            invalid.append(item)
            continue
        modes[name] = requirement
    if invalid or not modes:
        raise FlowError(
            "invalid Operational-Modes entries: " + ", ".join(invalid or [value])
        )
    return modes


def path_allowed(relative: str, entries: Iterable[str]) -> bool:
    for entry in entries:
        normalized = entry.strip("/")
        if any(character in normalized for character in "*?["):
            if flow_parallel.path_matches_glob(relative, normalized):
                return True
        elif relative == normalized or relative.startswith(normalized + "/"):
            return True
    return False


def task_owned_path(
    relative: str, state: dict[str, Any], scopes: Iterable[str]
) -> bool:
    active = active_task(state)
    exact = {
        f"spec/changes/{active['id']}.md",
        f"spec/evidence/{active['id']}.json",
        "spec/state.json",
    }
    return relative in exact or path_allowed(relative, scopes)


def refresh_approval(root: Path, state: dict[str, Any]) -> bool:
    approval = state["approvals"]["task"]
    if not approval.get("valid"):
        return False
    current = task_digest(root, state)
    if current == approval.get("digest"):
        return False
    approval["valid"] = False
    approval["invalidatedAt"] = now_iso()
    state["phase"] = "draft"
    state["red"] = None
    state["verification"] = None
    return True


def approval_valid(root: Path, state: dict[str, Any]) -> bool:
    refresh_approval(root, state)
    approval = state["approvals"]["task"]
    return bool(
        approval.get("valid") and approval.get("digest") == task_digest(root, state)
    )


def project_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(
        safe_files(root), key=lambda item: item.relative_to(root).as_posix()
    ):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def configured_paths(
    config: dict[str, Any], key: str, defaults: list[str]
) -> list[str]:
    values = config.get("policy", {}).get(key, defaults)
    return [str(value).strip("/") for value in values if str(value).strip("/")]


def path_under(relative: str, roots: Iterable[str]) -> bool:
    normalized = relative.strip("/")
    for root in roots:
        candidate = root.strip("/")
        if any(character in candidate for character in "*?["):
            if flow_parallel.path_matches_glob(normalized, candidate):
                return True
        elif normalized == candidate or normalized.startswith(candidate + "/"):
            return True
    return False


def committed_task_paths(root: Path, state: dict[str, Any]) -> list[str]:
    if not is_git_repo(root):
        return []
    base_sha = active_task(state).get("baseSha")
    if not base_sha:
        return []
    result = git(
        root,
        "diff",
        "--name-only",
        f"{base_sha}..HEAD",
    )
    if result.returncode != 0:
        raise FlowError("unable to inspect task changes from the recorded baseline")
    generated = configured_generated_paths(root)
    return sorted(
        {
            relative
            for line in result.stdout.splitlines()
            if (relative := line.strip().replace("\\", "/"))
            and relative not in generated
            and not any(part in EXCLUDED_DIRS for part in Path(relative).parts)
            and not relative.endswith((".pyc", ".pyo"))
        }
    )


def task_change_paths(root: Path, state: dict[str, Any]) -> list[str]:
    return sorted(
        set(working_tree_paths(root)) | set(committed_task_paths(root, state))
    )


def task_scope_status(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    if not state.get("activeTask"):
        return {"status": "not-applicable", "outOfScope": []}
    scopes = allowed_scope(root, state)
    out_of_scope = [
        relative
        for relative in task_change_paths(root, state)
        if not task_owned_path(relative, state, scopes)
    ]
    return {
        "status": "violated" if out_of_scope else "current",
        "outOfScope": out_of_scope,
    }


def ensure_scope_current(root: Path, state: dict[str, Any]) -> None:
    scope = task_scope_status(root, state)
    if scope["status"] == "violated":
        raise FlowError(
            "task changes are outside the approved scope: "
            + ", ".join(scope["outOfScope"])
        )


def test_file_digest(root: Path, relative: str) -> str:
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise FlowError(f"test file escapes project root: {relative}") from exc
    if not path.is_file():
        raise FlowError(f"missing test file: {relative}")
    return sha256_bytes(path.read_bytes())


def test_chain_current(root: Path, state: dict[str, Any]) -> bool:
    red = state.get("red")
    if not red:
        return False
    for relative, digest in red.get("testDigests", {}).items():
        if test_file_digest(root, relative) != digest:
            return False
    return red.get("taskDigest") == task_digest(root, state)


def red_record_tests_current(root: Path, red: dict[str, Any]) -> bool:
    try:
        return all(
            test_file_digest(root, relative) == digest
            for relative, digest in red.get("testDigests", {}).items()
        )
    except FlowError:
        return False


def is_configured_migration_path(root: Path, relative: str) -> bool:
    try:
        config = load_config(root)
        roots = configured_paths(
            config,
            "migration_paths",
            sorted(MIGRATION_PARTS),
        )
    except FlowError:
        roots = sorted(MIGRATION_PARTS)
    return is_migration_path(relative) or path_under(relative, roots)


def migration_files(root: Path) -> list[Path]:
    config = load_config(root)
    roots = configured_paths(config, "migration_paths", sorted(MIGRATION_PARTS))
    return sorted(
        path
        for path in safe_files(root)
        if is_migration_path(path.relative_to(root).as_posix())
        or path_under(path.relative_to(root).as_posix(), roots)
    )


def destructive_migrations(root: Path) -> list[str]:
    found: list[str] = []
    for path in migration_files(root):
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if DESTRUCTIVE_MIGRATION_PATTERN.search(content):
            found.append(path.relative_to(root).as_posix())
    return found


def staged_files(root: Path) -> list[str]:
    result = git(root, "diff", "--cached", "--name-only", "--diff-filter=ACMR")
    if result.returncode != 0:
        raise FlowError("unable to read staged files")
    return [
        line.strip().replace("\\", "/")
        for line in result.stdout.splitlines()
        if line.strip()
    ]


SYNTHETIC_SECRET_MARKER = "rigorbreeze: synthetic-secret"


def secret_content_scan(
    root: Path, paths: Iterable[str]
) -> tuple[list[str], list[str]]:
    patterns = (
        re.compile(
            r"(?i)\b(api[_-]?key|access[_-]?token|token|password|passwd|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_./+\-=]{12,}"
        ),
        re.compile(r"\b(ghp|github_pat|sk)-[A-Za-z0-9_-]{12,}\b"),
    )
    found: list[str] = []
    exemptions: list[str] = []
    test_roots = configured_paths(load_config(root), "test_paths", ["tests"])
    for relative in paths:
        result = git(root, "show", f":{relative}")
        if result.returncode != 0 or "\0" in result.stdout:
            continue
        for line_number, line in enumerate(result.stdout.splitlines(), start=1):
            if not any(pattern.search(line) for pattern in patterns):
                continue
            if SYNTHETIC_SECRET_MARKER in line and path_under(relative, test_roots):
                exemptions.append(f"{relative}:{line_number}")
            elif relative not in found:
                found.append(relative)
    return found, exemptions


def secret_content_paths(root: Path, paths: Iterable[str]) -> list[str]:
    return secret_content_scan(root, paths)[0]


def is_migration_path(relative: str) -> bool:
    parts = {part.lower() for part in Path(relative).parts}
    return bool(parts & MIGRATION_PARTS)


def is_dependency_path(relative: str) -> bool:
    return Path(relative).name.lower() in {name.lower() for name in DEPENDENCY_NAMES}


def baseline_current(root: Path, state: dict[str, Any]) -> bool:
    if not is_git_repo(root):
        return True
    active = active_task(state)
    base = active.get("baseBranch")
    recorded = active.get("baseSha")
    if not base or not recorded:
        return True
    if flow_parallel.branch_name(root) == base:
        result = git(root, "merge-base", "--is-ancestor", recorded, "HEAD")
        return result.returncode == 0
    result = git(root, "rev-parse", base)
    return result.returncode == 0 and result.stdout.strip() == recorded


def verification_current(root: Path, state: dict[str, Any]) -> bool:
    verification = state.get("verification")
    head = current_head(root)
    fingerprint = project_fingerprint(root)
    head_matches = not is_git_repo(root) or bool(
        verification is not None and verification.get("head") == head
    )
    if (
        not head_matches
        and verification is not None
        and head
        and state.get("activeTask")
    ):
        active = active_task(state)
        evidence_file = evidence_path(root, active["id"])
        verification_digest = sha256_bytes(
            json.dumps(verification, ensure_ascii=False, sort_keys=True).encode()
        )
        try:
            head_matches = flow_automation.verification_commit_bridge(
                root,
                task_id=active["id"],
                head=head,
                task_digest=task_digest(root, state),
                evidence_digest=sha256_bytes(evidence_file.read_bytes()),
                verification_digest=verification_digest,
                project_fingerprint=fingerprint,
            )
        except flow_automation.AutomationError:
            head_matches = False
    return bool(
        verification
        and verification.get("passed")
        and verification.get("toolVersion") == TOOL_VERSION
        and baseline_current(root, state)
        and verification.get("taskDigest") == task_digest(root, state)
        and verification.get("projectFingerprint") == fingerprint
        and head_matches
    )


def configured_verification_current(root: Path, state: dict[str, Any]) -> bool:
    verification = state.get("verification") or {}
    return bool(
        verification_current(root, state)
        and verification.get("configured")
        and verification.get("profile") in {"affected", "full"}
    )


def full_profile_current(root: Path, state: dict[str, Any]) -> bool:
    verification = state.get("verification")
    required_checks = set(load_config(root).get("profiles", {}).get("full", []))
    return bool(
        required_checks
        and verification_current(root, state)
        and verification.get("configured")
        and verification.get("profile") == "full"
        and verification.get("configDigest") == config_digest(root)
        and required_checks <= set(verification.get("checks", []))
    )


def report_record(root: Path, relative: str | None) -> dict[str, Any] | None:
    if not relative:
        return None
    path = root / relative
    if not path.is_file():
        raise FlowError(f"configured report is missing: {relative}")
    content = path.read_bytes()
    if not content:
        raise FlowError(f"configured report is empty: {relative}")
    record: dict[str, Any] = {
        "path": relative,
        "sha256": sha256_bytes(content),
    }
    if path.suffix.lower() == ".json":
        try:
            content = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise FlowError(f"invalid JSON report: {relative}: {exc}") from exc
        status = content.get("status") if isinstance(content, dict) else None
        if status is not None and str(status).lower() not in {
            "passed",
            "pass",
            "ok",
            "success",
        }:
            raise FlowError(f"report does not declare a passed status: {relative}")
        record["status"] = status
    return record


def record_artifacts(
    root: Path,
    evidence: dict[str, Any],
    check_id: str,
    relatives: Iterable[str],
    fingerprint: str,
    approved_task_digest: str,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for relative in relatives:
        path = root / relative
        if not path.is_file():
            raise FlowError(f"configured artifact is missing: {relative}")
        record = {
            "kind": check_id,
            "path": relative,
            "sha256": sha256_bytes(path.read_bytes()),
            "size": path.stat().st_size,
            "head": current_head(root) if is_git_repo(root) else None,
            "taskDigest": approved_task_digest,
            "projectFingerprint": fingerprint,
            "recordedAt": now_iso(),
        }
        evidence["artifacts"].append(record)
        records.append(record)
    return records


def check_category(check_id: str) -> str:
    if check_id in {"format", "lint", "typecheck"}:
        return "static-quality"
    if check_id in {"unit", "integration", "e2e", "contract"}:
        return "behavior"
    if check_id == "secret":
        return "secrets"
    if check_id in {"dependency", "license", "sbom"}:
        return "supply-chain"
    if check_id == "migration":
        return "migration"
    if check_id == "build":
        return "build"
    if check_id in {"playwright", "acceptance"}:
        return "acceptance"
    return "project"


def l2_full_profile_issues(
    root: Path,
    state: dict[str, Any],
    check_ids: list[str],
    config: dict[str, Any],
) -> list[str]:
    if active_task(state)["risk"] != "L2":
        return []
    selected = set(check_ids)
    issues: list[str] = []
    required = {"secret", "build"}
    static_checks = {"format", "lint", "typecheck"}
    behavior_checks = {"unit", "integration", "e2e", "contract"}
    if not selected & static_checks:
        issues.append("one static check (format/lint/typecheck)")
    if not selected & behavior_checks:
        issues.append("one behavior check (unit/integration/e2e/contract)")

    changes = task_change_paths(root, state)
    report_required: set[str] = set()
    if any(is_dependency_path(relative) for relative in changes):
        required.update({"dependency", "license", "sbom"})
        report_required.update({"dependency", "license", "sbom"})
    if any(is_configured_migration_path(root, relative) for relative in changes):
        required.add("migration")
        report_required.add("migration")
    missing = sorted(required - selected)
    if missing:
        issues.append("missing checks: " + ", ".join(missing))
    configured = config.get("_checks", {})
    missing_reports = sorted(
        check_id
        for check_id in report_required & selected
        if not configured.get(check_id, {}).get("report")
    )
    if missing_reports:
        issues.append("checks require machine reports: " + ", ".join(missing_reports))
    return issues


def practice_summary(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    active = active_task(state)
    evidence = load_evidence(root, active["id"])
    check_runs = evidence.get("checkRuns", [])
    verifications = evidence.get("verifications", [])
    failed_checks = [
        record.get("checkId", "unknown")
        for record in check_runs
        if record.get("passed") is False
    ]
    failure_categories = sorted(
        {
            record.get(
                "category", check_category(str(record.get("checkId", "unknown")))
            )
            for record in check_runs
            if record.get("passed") is False
        }
    )
    advisory_failures = [
        record.get("checkId", "unknown")
        for record in check_runs
        if record.get("passed") is False and record.get("mode") == "advisory"
    ]
    acceptance_checks = [
        record for record in check_runs if record.get("checkId") == "acceptance"
    ]
    first_acceptance_passed: bool | None = None
    if acceptance_checks:
        first_acceptance_passed = bool(acceptance_checks[0].get("passed"))
    elif evidence.get("acceptance"):
        first_acceptance_passed = True
    failure_times = [
        datetime.fromisoformat(record["recordedAt"])
        for record in check_runs
        if record.get("passed") is False and record.get("recordedAt")
    ]
    success_times = [
        datetime.fromisoformat(record["recordedAt"])
        for record in check_runs
        if record.get("passed") is True and record.get("recordedAt")
    ]
    estimated_rework_seconds: int | None = None
    if failure_times and success_times:
        first_failure = min(failure_times)
        later_successes = [value for value in success_times if value >= first_failure]
        if later_successes:
            estimated_rework_seconds = max(
                0, round((max(later_successes) - first_failure).total_seconds())
            )
    summary = {
        "taskId": active["id"],
        "risk": active["risk"],
        "verificationRuns": len(verifications),
        "checkRuns": len(check_runs),
        "checkDurationMs": sum(
            int(record.get("durationMs", 0) or 0) for record in check_runs
        ),
        "failedChecks": failed_checks,
        "failureCategories": failure_categories,
        "potentialBypasses": advisory_failures,
        "firstAcceptancePassed": first_acceptance_passed,
        "acceptanceRecords": len(evidence.get("acceptance", [])),
        "estimatedReworkSeconds": estimated_rework_seconds,
        "practiceEvents": evidence.get("practice", {}).get("events", []),
        "generatedAt": now_iso(),
    }
    summary["summaryDigest"] = sha256_bytes(
        json.dumps(
            {key: value for key, value in summary.items() if key != "generatedAt"},
            ensure_ascii=False,
            sort_keys=True,
        ).encode()
    )
    return summary


def record_practice_event(
    root: Path,
    state: dict[str, Any],
    event_type: str,
    details: dict[str, Any],
    *,
    evolution_candidate: bool = False,
) -> None:
    active = state.get("activeTask")
    if not active:
        return
    evidence = load_evidence(root, active["id"])
    practice = evidence.setdefault("practice", {})
    events = practice.setdefault("events", [])
    normalized = {
        key: redact(str(value)) if value is not None else None
        for key, value in sorted(details.items())
    }
    event_key = sha256_bytes(
        json.dumps(
            {"type": event_type, "details": normalized},
            ensure_ascii=False,
            sort_keys=True,
        ).encode()
    )
    timestamp = now_iso()
    existing = next((item for item in events if item.get("key") == event_key), None)
    if existing:
        existing["count"] = int(existing.get("count", 1)) + 1
        existing["lastSeenAt"] = timestamp
        if evolution_candidate:
            existing["evolutionCandidate"] = True
    else:
        event = {
            "key": event_key,
            "type": event_type,
            "details": normalized,
            "count": 1,
            "firstSeenAt": timestamp,
            "lastSeenAt": timestamp,
        }
        if evolution_candidate:
            event["evolutionCandidate"] = True
        events.append(event)
    save_evidence(root, active["id"], evidence)


def retro_confirmation_current(root: Path, state: dict[str, Any]) -> bool:
    active = active_task(state)
    evidence = load_evidence(root, active["id"])
    confirmation = evidence.get("practice", {}).get("confirmation")
    if not confirmation:
        return False
    summary = practice_summary(root, state)
    return bool(
        confirmation.get("taskDigest") == task_digest(root, state)
        and confirmation.get("projectFingerprint") == project_fingerprint(root)
        and confirmation.get("summaryDigest") == summary["summaryDigest"]
    )


def current_structured_records(
    root: Path, state: dict[str, Any], section: str
) -> list[dict[str, Any]]:
    active = active_task(state)
    evidence = load_evidence(root, active["id"])
    fingerprint = project_fingerprint(root)
    digest = task_digest(root, state)
    records = [
        record
        for record in evidence.get(section, [])
        if record.get("taskDigest") == digest
        and record.get("projectFingerprint") == fingerprint
    ]
    if section == "artifacts" and is_git_repo(root):
        head = current_head(root)
        records = [record for record in records if record.get("head") == head]
    return records


def validate_operation_plan(
    content: Any,
    *,
    head: str | None,
    artifact_digests: set[str],
) -> dict[str, Any]:
    if not isinstance(content, dict):
        raise FlowError("operation-plan report must be a JSON object")
    missing: list[str] = []
    if not content.get("targetEnvironment"):
        missing.append("targetEnvironment")
    if not head or content.get("gitSha") != head:
        missing.append("gitSha")
    if (
        not artifact_digests
        or set(content.get("artifactDigests") or []) != artifact_digests
    ):
        missing.append("artifactDigests")
    steps = content.get("steps")
    required_stages = {
        "backup",
        "config-freeze",
        "migration",
        "deploy",
        "acceptance",
        "switch",
        "observe",
    }
    valid_steps = (
        isinstance(steps, list)
        and bool(steps)
        and all(
            isinstance(step, dict)
            and str(step.get("name") or "").strip()
            and str(step.get("successCondition") or "").strip()
            for step in (steps or [])
        )
    )
    stages = {
        str(step.get("name"))
        for step in (steps or [])
        if isinstance(step, dict) and step.get("name")
    }
    if not valid_steps or not required_stages <= stages:
        missing.append("steps")
    for field in ("stopConditions", "safeRecoveryPoints", "rollbackLimitations"):
        value = content.get(field)
        if not isinstance(value, list) or not value:
            missing.append(field)
    if missing:
        raise FlowError(
            "operation-plan report is missing or inconsistent: "
            + ", ".join(sorted(set(missing)))
        )
    return content


def validate_operation_result(
    content: Any,
    *,
    head: str | None,
    artifact_digests: set[str],
) -> dict[str, Any]:
    if not isinstance(content, dict):
        raise FlowError("operation-result report must be a JSON object")
    missing: list[str] = []
    if content.get("status") not in {"paused", "failed", "succeeded"}:
        missing.append("status")
    if not head or content.get("gitSha") != head:
        missing.append("gitSha")
    if (
        not artifact_digests
        or set(content.get("artifactDigests") or []) != artifact_digests
    ):
        missing.append("artifactDigests")
    if not isinstance(content.get("completedSteps"), list):
        missing.append("completedSteps")
    for field in ("safeState", "resumeAction"):
        if not str(content.get(field) or "").strip():
            missing.append(field)
    if missing:
        raise FlowError(
            "operation-result report is missing or inconsistent: "
            + ", ".join(sorted(set(missing)))
        )
    return content


def ensure_tdd_chains_complete(root: Path, state: dict[str, Any]) -> None:
    active = active_task(state)
    if active["risk"] not in {"L1", "L2"}:
        return
    evidence = load_evidence(root, active["id"])
    digest = task_digest(root, state)
    declared = set(acceptance_ids(root, state))
    latest_by_requirement: dict[str, dict[str, Any]] = {}
    for chain in evidence.get("tddChain", []):
        if (chain.get("red") or {}).get("taskDigest") != digest:
            continue
        latest_by_requirement[str(chain.get("requirement") or "unknown")] = chain
    chains = list(latest_by_requirement.values())
    if not chains:
        raise FlowError("current task has no TDD chain")
    current_verification = state.get("verification")
    incomplete: list[str] = []
    for chain in chains:
        requirement = str(chain.get("requirement") or "unknown")
        red = chain.get("red") or {}
        if (
            requirement not in declared
            or not red_record_tests_current(root, red)
            or chain.get("green") != current_verification
        ):
            incomplete.append(requirement)
    if incomplete:
        raise FlowError(
            "current TDD chains are incomplete or stale: "
            + ", ".join(sorted(set(incomplete)))
        )


def ensure_operational_modes_complete(root: Path, state: dict[str, Any]) -> None:
    active = active_task(state)
    if active.get("risk") != "L2":
        return
    modes = operational_modes(root, state)
    if not modes:
        return
    evidence = load_evidence(root, active["id"])
    digest = task_digest(root, state)
    verification = state.get("verification")
    satisfied = {
        str(chain.get("requirement"))
        for chain in evidence.get("tddChain", [])
        if (chain.get("red") or {}).get("taskDigest") == digest
        and chain.get("green") == verification
        and red_record_tests_current(root, chain.get("red") or {})
    }
    for record in current_structured_records(root, state, "acceptance"):
        requirement = record.get("fields", {}).get("requirement")
        if requirement:
            satisfied.update(
                part.strip() for part in str(requirement).split(",") if part.strip()
            )
    missing = sorted(
        requirement for requirement in modes.values() if requirement not in satisfied
    )
    if missing:
        raise FlowError(
            "operational modes lack current RED/GREEN or runtime acceptance: "
            + ", ".join(missing)
        )


def ensure_delivery_quality(root: Path, state: dict[str, Any]) -> str:
    if not approval_valid(root, state):
        raise FlowError("task approval is missing or invalid")
    ensure_scope_current(root, state)
    risk = active_task(state)["risk"]
    if risk in {"L1", "L2"}:
        if not full_profile_current(root, state):
            raise FlowError("current configured full profile verification is required")
    elif not configured_verification_current(root, state):
        raise FlowError("current configured verification is required")
    acceptance = current_structured_records(root, state, "acceptance")
    if risk in {"L1", "L2"}:
        ensure_tdd_chains_complete(root, state)
        ensure_operational_modes_complete(root, state)
        if not acceptance:
            raise FlowError("current structured acceptance evidence is required")
        if not any(record.get("kind") == "review" for record in acceptance):
            raise FlowError("current independent review evidence is required")
    return risk


def ensure_close(root: Path, state: dict[str, Any]) -> None:
    risk = ensure_delivery_quality(root, state)
    if risk in {"L1", "L2", "Emergency"} and not retro_confirmation_current(
        root, state
    ):
        summary = practice_summary(root, state)
        raise FlowError(
            "retrospective confirmation is required; prefilled summary: "
            + json.dumps(summary, ensure_ascii=False, sort_keys=True)
            + "; run retro --json, then confirm the three human judgments"
        )


def ensure_release(root: Path, state: dict[str, Any]) -> None:
    if not approval_valid(root, state):
        raise FlowError("task approval is missing or invalid")
    ensure_scope_current(root, state)
    ensure_tdd_chains_complete(root, state)
    if not full_profile_current(root, state):
        raise FlowError("current configured full profile verification is required")
    current_artifacts = current_structured_records(root, state, "artifacts")
    if not current_artifacts:
        raise FlowError("current immutable artifact digest is required")
    artifact_digests = {record["sha256"] for record in current_artifacts}
    governance = [
        record
        for record in current_structured_records(root, state, "release")
        if record.get("kind") == "governance"
        and RELEASE_GOVERNANCE_FIELDS <= record.get("fields", {}).keys()
    ]
    if not governance:
        raise FlowError("current release governance evidence is required")
    if not any(
        set(record.get("artifactDigests", [])) == artifact_digests
        for record in governance
    ):
        raise FlowError(
            "release governance does not reference the current artifact digest"
        )
    if state.get("phase") != "release-ready":
        raise FlowError("task must be release-ready")
    risk = active_task(state)["risk"]
    acceptance_records = current_structured_records(root, state, "acceptance")
    if risk in {"L1", "L2", "Emergency"}:
        if not acceptance_records:
            raise FlowError("current structured acceptance evidence is required")
        if not any(
            set(record.get("artifactDigests", [])) == artifact_digests
            for record in acceptance_records
        ):
            raise FlowError(
                "acceptance evidence does not reference the current artifact digest"
            )
        if not any(record.get("kind") == "review" for record in acceptance_records):
            raise FlowError("current independent review evidence is required")
    release_records = current_structured_records(root, state, "release")
    if risk == "L2":
        operation_plans = [
            record
            for record in release_records
            if record.get("kind") == "operation-plan"
            and set(record.get("artifactDigests", [])) == artifact_digests
        ]
        if not operation_plans:
            raise FlowError("current release operation-plan evidence is required")
        security_records = [
            record
            for record in release_records
            if record.get("kind") == "security"
            and SECURITY_EVIDENCE_FIELDS <= record.get("fields", {}).keys()
        ]
        if not security_records:
            raise FlowError("current structured security evidence is required")
        if not any(
            set(record.get("artifactDigests", [])) == artifact_digests
            for record in security_records
        ):
            raise FlowError(
                "security evidence does not reference the current artifact digest"
            )
        if migration_files(root):
            migration_records = [
                record
                for record in release_records
                if record.get("kind") == "migration"
                and MIGRATION_EVIDENCE_FIELDS <= record.get("fields", {}).keys()
            ]
            if not migration_records:
                raise FlowError("current structured migration evidence is required")
            if not any(
                set(record.get("artifactDigests", [])) == artifact_digests
                for record in migration_records
            ):
                raise FlowError(
                    "migration evidence does not reference the current artifact digest"
                )


def save_state(root: Path, state: dict[str, Any]) -> None:
    state["updatedAt"] = now_iso()
    write_json(state_path(root), state)
    active = state.get("activeTask")
    task_id = active.get("id") if active else (state.get("lastClosed") or {}).get("id")
    if task_id and is_git_repo(root):
        scopes: list[str] | None = None
        status: dict[str, Any] | None = None
        path = task_path(root, task_id)
        if path.is_file() and active:
            try:
                scopes = allowed_scope(root, state)
                approval_now = bool(
                    state["approvals"]["task"].get("valid")
                    and state["approvals"]["task"].get("digest")
                    == task_digest(root, state)
                )
                verification_now = (
                    "current"
                    if approval_now and verification_current(root, state)
                    else "missing/stale"
                )
                full_now = (
                    "current"
                    if approval_now and full_profile_current(root, state)
                    else "missing/stale"
                )
                status = {
                    "approval": "valid" if approval_now else "invalid",
                    "verification": verification_now,
                    "fullProfile": full_now,
                    "nextAction": next_action(
                        root, state, approval_now, verification_now, full_now
                    ),
                }
            except FlowError:
                pass
        try:
            flow_parallel.update_task(
                root, task_id, state, scopes=scopes, status=status
            )
        except flow_parallel.ParallelError as exc:
            raise FlowError(str(exc)) from exc


def next_action(
    root: Path,
    state: dict[str, Any],
    approval_valid_now: bool,
    verification: str,
    full_profile: str,
) -> dict[str, str]:
    if state.get("activeTask"):
        operation_results = [
            record
            for record in current_structured_records(root, state, "release")
            if record.get("kind") == "operation-result"
            and record.get("operation", {}).get("status") in {"paused", "failed"}
        ]
        if operation_results:
            operation = operation_results[-1]["operation"]
            return {
                "reason": str(operation.get("safeState")),
                "command": str(operation.get("resumeAction")),
            }
    active = state.get("activeTask")
    if not active:
        return {
            "reason": "No active task exists.",
            "command": 'python scripts/rigorbreeze.py new TASK-001 --title "<observable outcome>" --risk L1',
        }
    scope = task_scope_status(root, state)
    if scope["status"] == "violated":
        return {
            "reason": "Task changes violate the approved scope; restore them or split a dependent task.",
            "command": "python scripts/rigorbreeze.py status --json",
        }
    if not approval_valid_now:
        return {
            "reason": "The active task is not approved or its digest changed.",
            "command": "python scripts/rigorbreeze.py approve task",
        }
    if active.get("risk") in {"L1", "L2", "Emergency"} and not state.get("red"):
        return {
            "reason": "This risk lane requires an observed RED before implementation.",
            "command": "python scripts/rigorbreeze.py red --help",
        }
    if verification != "current":
        return {
            "reason": "Implement the approved slice, then run affected verification.",
            "command": "python scripts/rigorbreeze.py verify --profile affected",
        }
    risk = active.get("risk")
    if risk in {"L1", "L2"} and full_profile != "current":
        return {
            "reason": "The merge-quality full profile is missing or stale.",
            "command": "python scripts/rigorbreeze.py --mode enforced verify --profile full",
        }
    if state.get("phase") == "release-ready":
        return {
            "reason": "All recorded release prerequisites should now be checked.",
            "command": "python scripts/rigorbreeze.py check release",
        }
    if risk == "L0":
        return {
            "reason": "The low-risk task is verified and may be archived.",
            "command": "python scripts/rigorbreeze.py archive",
        }
    if risk == "Emergency":
        if not retro_confirmation_current(root, state):
            return {
                "reason": "Review the hotfix summary and confirm three judgments.",
                "command": "python scripts/rigorbreeze.py retro --json",
            }
        return {
            "reason": "The hotfix verification and retrospective are current.",
            "command": "python scripts/rigorbreeze.py archive",
        }
    if state.get("phase") == "accepted":
        if not retro_confirmation_current(root, state):
            return {
                "reason": "Review the prefilled summary and confirm three judgments.",
                "command": "python scripts/rigorbreeze.py retro --json",
            }
        return {
            "reason": "Verification, acceptance, and retrospective are current.",
            "command": "python scripts/rigorbreeze.py archive",
        }
    return {
        "reason": "Add the applicable runtime or product acceptance evidence.",
        "command": "python scripts/rigorbreeze.py evidence --help",
    }


def automation_task_paths(root: Path, state: dict[str, Any]) -> list[str]:
    scopes = allowed_scope(root, state)
    return [
        relative
        for relative in flow_automation.working_tree_paths(root, {f"spec/{LOCK_NAME}"})
        if task_owned_path(relative, state, scopes)
    ]


def automation_values(root: Path, state: dict[str, Any]) -> dict[str, str]:
    active = active_task(state)
    artifacts = current_structured_records(root, state, "artifacts")
    return {
        "task_id": active["id"],
        "title": active["title"],
        "branch": flow_parallel.branch_name(root) or "",
        "base": active.get("baseBranch") or "",
        "head": current_head(root) or "",
        "artifact_sha256": (
            ",".join(sorted(record["sha256"] for record in artifacts))
            if artifacts
            else ""
        ),
    }


def automation_input(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    active = active_task(state)
    evidence_file = evidence_path(root, active["id"])
    verification = json.dumps(
        state.get("verification"), ensure_ascii=False, sort_keys=True
    ).encode()
    values = automation_values(root, state)
    return {
        "head": values["head"],
        "taskDigest": task_digest(root, state),
        "evidenceDigest": sha256_bytes(evidence_file.read_bytes()),
        "verificationDigest": sha256_bytes(verification),
        "projectFingerprint": project_fingerprint(root),
        "artifactSha256": values["artifact_sha256"] or None,
    }
