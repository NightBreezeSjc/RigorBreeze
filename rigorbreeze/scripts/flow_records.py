"""Evidence, retrospective, archive, audit, and record lifecycle helpers for RigorBreeze."""

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any
import flow_automation
import flow_parallel
from flow_policy import (  # noqa: E402
    allowed_scope,
    approval_valid,
    current_structured_records,
    ensure_close,
    path_allowed,
    practice_summary,
    project_fingerprint,
    save_state,
    validate_operation_plan,
    validate_operation_result,
    verification_current,
)
from flow_state import (  # noqa: E402
    LOCK_NAME,
    MIGRATION_EVIDENCE_FIELDS,
    RELEASE_GOVERNANCE_FIELDS,
    SECURITY_EVIDENCE_FIELDS,
    FlowError,
    active_task,
    archive_path,
    atomic_write,
    audit_path,
    config_path,
    compact_completed_check_runs,
    compact_completed_tdd_history,
    current_head,
    evidence_path,
    history_path,
    is_git_repo,
    load_evidence,
    load_state,
    managed_workflow_paths,
    now_iso,
    parse_fields,
    read_json,
    record_settings,
    redact,
    save_evidence,
    sha256_bytes,
    spec_root,
    task_digest,
    task_path,
    upgrade_evidence,
    working_tree_paths,
    write_json,
)


def last_closed_task(
    state: dict[str, Any], *, completed_only: bool = False
) -> dict[str, Any]:
    last = state.get("lastClosed") or {}
    if not last or (completed_only and last.get("outcome") != "completed"):
        raise FlowError("no eligible closed task context is available")
    return last


def completed_closure_paths(root: Path, state: dict[str, Any]) -> list[str]:
    last = state.get("lastClosed") or {}
    if last.get("outcome") not in {"completed", "reconciled"}:
        return []
    task_id = last.get("id")
    if not task_id:
        return []
    if record_settings(root)["storage"] == "private":
        audit = f"spec/evidence/{task_id}.audit.json"
        return [audit] if (root / audit).is_file() else []
    return [
        f"spec/changes/{task_id}.md",
        f"spec/archive/{task_id}.md",
        f"spec/evidence/{task_id}.json",
    ]


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
    if last.get("recordStorage") == "private":
        archive = archive_path(root, str(last.get("id", "")))
        evidence_file = evidence_path(root, str(last.get("id", "")))
    else:
        archive = root / str(last.get("archivePath", ""))
        evidence_file = root / str(last.get("evidencePath", ""))
    if not archive.is_file() or not evidence_file.is_file():
        return False
    digest = sha256_bytes(archive.read_bytes() + b"\0" + evidence_file.read_bytes())
    return bool(
        digest == last.get("closureDigest")
        and project_fingerprint(root) == last.get("projectFingerprint")
    )


def command_evidence_add(
    root: Path,
    section: str,
    kind: str,
    file: str | None,
    field_values: list[str],
) -> None:
    state = load_state(root)
    approval_now = approval_valid(root, state)
    verification_now = verification_current(root, state)
    pending_kinds = {"runtime", "device", "wechat-device", "authoritative-observation"}
    pending_allowed = section == "acceptance" and kind in pending_kinds
    if not approval_now or (not verification_now and not pending_allowed):
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
        "verificationBinding": "current" if verification_now else "pending",
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
            "authoritative-observation": {
                "status",
                "environment",
                "requirement",
                "source",
            },
        }
        required = required_by_kind.get(kind)
        if required is None:
            raise FlowError(
                "acceptance evidence kind must be playwright, runtime, design, "
                "product-review, review, device, wechat-device, or "
                "authoritative-observation"
            )
        missing = sorted(required - fields.keys())
        fileless_review = kind in {"review", "product-review"} and not file
        structured_review_missing = sorted(
            {"standards", "spec", "findings"} - fields.keys()
        )
        if missing or (not file and not fileless_review):
            raise FlowError(
                f"{kind} evidence requires a real file and fields: "
                + ", ".join(missing)
            )
        if fileless_review and structured_review_missing:
            raise FlowError(
                f"fileless {kind} evidence requires structured fields: "
                + ", ".join(structured_review_missing)
            )
        if fields["status"].lower() != "passed":
            raise FlowError(f"{kind} evidence status must be passed")
        if fileless_review and (
            fields["standards"].lower() != "passed"
            or fields["spec"].lower() != "passed"
            or not fields["findings"].strip()
        ):
            raise FlowError(
                f"fileless {kind} evidence must pass standards/spec and describe findings"
            )
        if verification_now and state.get("phase") != "release-ready":
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
            "judgmentDigest": summary["judgmentDigest"],
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
            integration_proof = flow_parallel.registered_integration_status(
                root, active
            )
            if integration_proof not in {"contained", "patch-equivalent"}:
                raise FlowError(
                    f"task integration into {base or '<unknown>'} is not proven: {integration_proof}"
                )
    else:
        raise FlowError(f"unknown archive outcome: {outcome}")
    source = task_path(root, active["id"])
    destination = archive_path(root, active["id"])
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
    if outcome == "completed":
        compact_completed_check_runs(evidence)
        compact_completed_tdd_history(evidence)
    save_evidence(root, active["id"], evidence)
    settings = record_settings(root)
    if (
        settings["storage"] == "private"
        and settings["publish_high_risk_summary"]
        and active.get("risk") in {"L2", "Emergency"}
    ):
        write_public_audit(root, active["id"], str(active["risk"]), evidence)
    source.replace(destination)
    private_records = settings["storage"] == "private"
    archive_relative = None if private_records else f"spec/archive/{active['id']}.md"
    evidence_relative = (
        None if private_records else f"spec/evidence/{active['id']}.json"
    )
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
        "recordStorage": "private" if private_records else "tracked",
        "reason": closure["reason"],
        "archivePath": archive_relative,
        "sourcePath": None if private_records else f"spec/changes/{active['id']}.md",
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


def record_risk(contract: Path, evidence: dict[str, Any]) -> str:
    if contract.is_file():
        match = re.search(
            r"^Risk:\s*(L0|L1|L2|Emergency)\s*$",
            contract.read_text(encoding="utf-8", errors="replace"),
            re.MULTILINE,
        )
        if match:
            return match.group(1)
    return str(evidence.get("risk") or "L1")


def private_history_summary(
    task_id: str, risk: str, evidence: dict[str, Any]
) -> dict[str, Any]:
    practice = evidence.get("practice", {})
    confirmation = practice.get("confirmation") or {}
    checks = evidence.get("checkRuns") or []
    return {
        "schemaVersion": 1,
        "taskId": task_id,
        "risk": risk,
        "outcome": (evidence.get("closure") or {}).get("outcome"),
        "head": (evidence.get("closure") or {}).get("head"),
        "checks": {
            "passed": sorted(
                {
                    str(item.get("checkId"))
                    for item in checks
                    if item.get("exitCode") == 0 and item.get("checkId")
                }
            ),
            "failed": sorted(
                {
                    str(item.get("checkId"))
                    for item in checks
                    if item.get("exitCode") not in {None, 0} and item.get("checkId")
                }
            ),
        },
        "workflowImpact": confirmation.get("workflowImpact", "unreviewed"),
        "evolutionCandidate": bool(
            confirmation.get("evolutionCandidate")
            or any(
                isinstance(item, dict) and item.get("evolutionCandidate") is True
                for item in practice.get("events", [])
            )
        ),
        "evidenceDigest": sha256_bytes(
            json.dumps(evidence, ensure_ascii=False, sort_keys=True).encode()
        ),
    }


def public_audit_summary(
    task_id: str, risk: str, evidence: dict[str, Any]
) -> dict[str, Any]:
    checks = evidence.get("checkRuns") or []
    artifacts = evidence.get("artifacts") or []
    acceptance = evidence.get("acceptance") or []
    release = evidence.get("release") or []
    summary = private_history_summary(task_id, risk, evidence)
    return {
        "schemaVersion": 1,
        "taskId": task_id,
        "risk": risk,
        "acceptanceIds": sorted(
            {
                str(item.get("requirement"))
                for item in evidence.get("tddChain", [])
                if item.get("requirement")
            }
        ),
        "gitSha": (evidence.get("closure") or {}).get("head"),
        "configurationDigest": (evidence.get("baseline") or {}).get("configDigest"),
        "evidenceDigest": summary["evidenceDigest"],
        "checks": [
            {
                "id": item.get("checkId"),
                "exitCode": item.get("exitCode"),
                "reportDigest": item.get("reportDigest"),
            }
            for item in checks[-32:]
            if item.get("checkId")
        ],
        "artifacts": [
            {
                "kind": item.get("kind") or item.get("type"),
                "sha256": item.get("sha256") or item.get("digest"),
                "gitSha": item.get("gitSha"),
            }
            for item in artifacts[-24:]
            if item.get("sha256") or item.get("digest")
        ],
        "acceptance": [
            {
                "kind": item.get("kind"),
                "status": item.get("status") or item.get("conclusion"),
                "digest": item.get("sha256") or item.get("digest"),
            }
            for item in acceptance[-24:]
        ],
        "release": [
            {
                "kind": item.get("kind"),
                "status": item.get("status")
                or (item.get("operation") or {}).get("status"),
                "digest": item.get("sha256") or item.get("digest"),
            }
            for item in release[-24:]
        ],
        "tested": summary["checks"]["passed"],
        "notTested": summary["checks"]["failed"],
        "outcome": summary["outcome"],
    }


def write_public_audit(
    root: Path, task_id: str, risk: str, evidence: dict[str, Any]
) -> Path:
    payload = public_audit_summary(task_id, risk, evidence)
    encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode() + b"\n"
    if len(encoded) > 32 * 1024:
        payload["checks"] = payload["checks"][-8:]
        payload["artifacts"] = payload["artifacts"][-8:]
        payload["acceptance"] = payload["acceptance"][-8:]
        payload["release"] = payload["release"][-8:]
        encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode() + b"\n"
    if len(encoded) > 32 * 1024:
        raise FlowError("sanitized audit summary exceeds 32 KiB")
    path = audit_path(root, task_id)
    atomic_write(path, encoded.decode())
    return path


def update_record_configuration(root: Path) -> None:
    path = config_path(root)
    content = path.read_text(encoding="utf-8")
    content = re.sub(r"(?m)^version\s*=\s*\d+\s*$", "version = 5", content, count=1)
    content = re.sub(r"(?ms)^\[records\]\n.*?(?=^\[|\Z)", "", content).rstrip()
    content += '\n\n[records]\nstorage = "private"\npublish_high_risk_summary = true\n'
    atomic_write(path, content)
    ignore = root / ".gitignore"
    existing = (
        ignore.read_text(encoding="utf-8", errors="replace") if ignore.exists() else ""
    )
    start = "# rigorbreeze:records:start"
    end = "# rigorbreeze:records:end"
    block = f"{start}\nspec/changes/\nspec/archive/\nspec/evidence/*.json\n!spec/evidence/*.audit.json\n{end}"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    updated = (
        pattern.sub(block, existing)
        if pattern.search(existing)
        else existing.rstrip() + ("\n\n" if existing.strip() else "") + block + "\n"
    )
    atomic_write(ignore, updated)


def migrate_records_to_private(root: Path) -> dict[str, list[str]]:
    state = load_state(root)
    if state.get("activeTask"):
        raise FlowError("record migration requires no active task")
    journal = flow_automation.load_journal(root)
    if any(item.get("status") == "running" for item in journal["actions"].values()):
        raise FlowError("record migration requires all external actions to be settled")
    settings = record_settings(root)
    if settings["storage"] == "private":
        raise FlowError("record storage is already private")
    changed = working_tree_paths(root)
    if changed:
        raise FlowError(
            "record migration requires a clean working tree; found: "
            + ", ".join(changed)
        )
    source = spec_root(root)
    private = flow_parallel.git_common_dir(root)
    if private is None:
        raise FlowError("record migration requires a Git repository")
    private = private / "rigorbreeze" / "records"
    for name in ("changes", "evidence", "archive", "history"):
        (private / name).mkdir(parents=True, exist_ok=True)
    moved: list[str] = []
    summarized: list[str] = []
    audits: list[str] = []
    task_ids = {
        path.name.removesuffix(".json")
        for path in (source / "evidence").glob("*.json")
        if not path.name.endswith(".audit.json")
    }
    for task_id in sorted(task_ids):
        evidence_file = source / "evidence" / f"{task_id}.json"
        evidence = upgrade_evidence(read_json(evidence_file), task_id)
        contract = source / "archive" / f"{task_id}.md"
        if not contract.exists():
            contract = source / "changes" / f"{task_id}.md"
        risk = record_risk(contract, evidence)
        if risk in {"L2", "Emergency"}:
            write_json(private / "evidence" / evidence_file.name, evidence)
            if contract.is_file():
                destination = (
                    private
                    / ("archive" if "archive" in contract.parts else "changes")
                    / contract.name
                )
                atomic_write(destination, contract.read_text(encoding="utf-8"))
            audit = write_public_audit(root, task_id, risk, evidence)
            audits.append(str(audit.relative_to(root)))
            moved.append(task_id)
        else:
            write_json(
                private / "history" / f"{task_id}.json",
                private_history_summary(task_id, risk, evidence),
            )
            summarized.append(task_id)
        for old in (
            source / "changes" / f"{task_id}.md",
            source / "archive" / f"{task_id}.md",
            evidence_file,
        ):
            if old.is_file():
                old.unlink()
    update_record_configuration(root)
    return {"moved": moved, "summarized": summarized, "audits": audits}


def compact_integrated_private_records(root: Path, task_ids: list[str]) -> list[str]:
    if record_settings(root)["storage"] != "private":
        return []
    registry = flow_parallel.load_registry(root)
    compacted: list[str] = []
    for task_id in task_ids:
        task = registry["tasks"].get(task_id, {})
        risk = str(task.get("risk") or "")
        evidence_file = evidence_path(root, task_id)
        if risk not in {"L0", "L1"} or not evidence_file.is_file():
            continue
        evidence = load_evidence(root, task_id)
        if not evidence.get("closure"):
            continue
        write_json(
            history_path(root, task_id),
            private_history_summary(task_id, risk, evidence),
        )
        for detail in (
            task_path(root, task_id),
            archive_path(root, task_id),
            evidence_file,
        ):
            if detail.is_file():
                detail.unlink()
        compacted.append(task_id)
    return sorted(compacted)
