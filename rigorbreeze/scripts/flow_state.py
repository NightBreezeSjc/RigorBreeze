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

VERSION = 5
EVIDENCE_VERSION = 4
TOOL_VERSION = "0.20.0"
KERNEL_HELPER_NAMES = (
    "flow_state",
    "flow_parallel",
    "flow_automation",
    "flow_policy",
    "flow_records",
    "flow_verification",
    "flow_diagnostics",
)
SPEC_DIR = "spec"
CONFIG_NAME = "rigorbreeze.toml"
MODES = ("advisory", "enforced")
AUTOMATION_LEVELS = ("manual", "commit", "push", "merge", "release")
STANDARD_CHECK_IDS = (
    "environment",
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
VERIFICATION_LEVELS = ("typecheck", "unit", "integration", "live-runtime", "device")
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


def record_settings(root: Path) -> dict[str, Any]:
    """Return the storage policy without requiring a fully loaded config."""

    path = config_path(root)
    if not path.is_file():
        return {"storage": "private", "publish_high_risk_summary": True}
    try:
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return {"storage": "tracked", "publish_high_risk_summary": False}
    version = int(raw.get("version", 1))
    configured = raw.get("records", {})
    return {
        "storage": configured.get("storage", "private" if version >= 5 else "tracked"),
        "publish_high_risk_summary": configured.get(
            "publish_high_risk_summary", version >= 5
        ),
    }


def records_root(root: Path) -> Path:
    if record_settings(root)["storage"] == "tracked":
        return spec_root(root)
    if is_git_repo(root):
        common = flow_parallel.git_common_dir(root)
        if common is not None:
            return common / "rigorbreeze" / "records"
    return root / ".rigorbreeze" / "records"


def task_path(root: Path, task_id: str) -> Path:
    return records_root(root) / "changes" / f"{task_id}.md"


def evidence_path(root: Path, task_id: str) -> Path:
    return records_root(root) / "evidence" / f"{task_id}.json"


def archive_path(root: Path, task_id: str) -> Path:
    return records_root(root) / "archive" / f"{task_id}.md"


def history_path(root: Path, task_id: str) -> Path:
    return records_root(root) / "history" / f"{task_id}.json"


def audit_path(root: Path, task_id: str) -> Path:
    return spec_root(root) / "evidence" / f"{task_id}.audit.json"


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
        "workflowVersion": EVIDENCE_VERSION,
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


def compact_completed_check_runs(evidence: dict[str, Any]) -> None:
    """Keep current check truth and one useful failure with cumulative counts."""
    runs = evidence.get("checkRuns")
    if not isinstance(runs, list) or len(runs) < 2:
        return

    previous = evidence.get("checkRunSummary")
    previous = previous if isinstance(previous, dict) else {}
    previous_retained = int(previous.get("retained") or 0)
    if previous_retained > len(runs):
        previous = {}
        previous_retained = 0
    new_runs = runs[previous_retained:] if previous else runs
    if previous and not new_runs:
        return

    grouped: dict[tuple[str, str, str, str], list[int]] = {}
    retained_indexes: set[int] = set()
    for index, record in enumerate(runs):
        if not isinstance(record, dict):
            retained_indexes.add(index)
            continue
        key = (
            str(record.get("profile") or "unknown"),
            str(record.get("checkId") or "unknown"),
            str(record.get("taskDigest") or "unknown"),
            str(record.get("projectFingerprint") or "unknown"),
        )
        grouped.setdefault(key, []).append(index)

    previous_groups: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for group in previous.get("groups", []):
        if not isinstance(group, dict):
            continue
        key = (
            str(group.get("profile") or "unknown"),
            str(group.get("checkId") or "unknown"),
            str(group.get("taskDigest") or "unknown"),
            str(group.get("projectFingerprint") or "unknown"),
        )
        previous_groups[key] = group

    groups: list[dict[str, Any]] = []
    for key, indexes in sorted(grouped.items()):
        profile, check_id, task_digest_value, fingerprint = key
        latest = indexes[-1]
        retained = {latest}
        failed_indexes = [
            index for index in indexes if runs[index].get("passed") is not True
        ]
        if failed_indexes:
            retained.add(failed_indexes[-1])
        retained_indexes.update(retained)
        prior = previous_groups.get(key, {})
        fresh_indexes = [index for index in indexes if index >= previous_retained]
        passed_count = int(prior.get("passed") or 0) + sum(
            runs[index].get("passed") is True for index in fresh_indexes
        )
        failed_count = int(prior.get("failed") or 0) + sum(
            runs[index].get("passed") is not True for index in fresh_indexes
        )
        duration_ms = int(prior.get("durationMs") or 0) + sum(
            int(runs[index].get("durationMs") or 0) for index in fresh_indexes
        )
        groups.append(
            {
                "profile": profile,
                "checkId": check_id,
                "taskDigest": task_digest_value,
                "projectFingerprint": fingerprint,
                "total": passed_count + failed_count,
                "passed": passed_count,
                "failed": failed_count,
                "durationMs": duration_ms,
                "retained": len(retained),
            }
        )

    retained_runs = [
        record for index, record in enumerate(runs) if index in retained_indexes
    ]
    total = sum(group["total"] for group in groups)
    omitted = total - len(retained_runs)
    if omitted <= 0 and not previous:
        return
    evidence["checkRuns"] = retained_runs
    evidence["checkRunSummary"] = {
        "policy": "current-per-fingerprint-plus-latest-failure",
        "total": total,
        "passed": sum(group["passed"] for group in groups),
        "failed": sum(group["failed"] for group in groups),
        "durationMs": sum(group["durationMs"] for group in groups),
        "retained": len(retained_runs),
        "omitted": omitted,
        "groups": groups,
    }


def compact_verification_history(evidence: dict[str, Any]) -> None:
    """Bound repeated profile results while preserving current truth and a failure."""
    verifications = evidence.get("verifications")
    if not isinstance(verifications, list) or len(verifications) < 2:
        return
    previous = evidence.get("verificationSummary")
    previous = previous if isinstance(previous, dict) else {}
    previous_retained = int(previous.get("retained") or 0)
    if previous_retained > len(verifications):
        previous = {}
        previous_retained = 0
    new_records = verifications[previous_retained:] if previous else verifications
    if previous and not new_records:
        return

    grouped: dict[tuple[str, str, str, str], list[int]] = {}
    retained_indexes: set[int] = set()
    for index, record in enumerate(verifications):
        if not isinstance(record, dict):
            retained_indexes.add(index)
            continue
        key = (
            str(record.get("profile") or "unknown"),
            str(record.get("taskDigest") or "unknown"),
            str(record.get("projectFingerprint") or "unknown"),
            str(record.get("configDigest") or "unknown"),
        )
        grouped.setdefault(key, []).append(index)
    for indexes in grouped.values():
        latest = indexes[-1]
        retained_indexes.add(latest)
        failed = [
            index for index in indexes if verifications[index].get("passed") is not True
        ]
        if failed:
            retained_indexes.add(failed[-1])

    retained = [
        record
        for index, record in enumerate(verifications)
        if index in retained_indexes
    ]
    fresh_passed = sum(record.get("passed") is True for record in new_records)
    fresh_failed = len(new_records) - fresh_passed
    total = int(previous.get("total") or 0) + len(new_records)
    omitted = total - len(retained)
    if omitted <= 0 and not previous:
        return
    evidence["verifications"] = retained
    evidence["verificationSummary"] = {
        "policy": "current-per-fingerprint-plus-latest-failure",
        "total": total,
        "passed": int(previous.get("passed") or 0) + fresh_passed,
        "failed": int(previous.get("failed") or 0) + fresh_failed,
        "retained": len(retained),
        "omitted": omitted,
    }


def compact_completed_tdd_history(evidence: dict[str, Any]) -> None:
    """Keep final TDD proof plus the latest useful failed attempt per requirement."""
    chains = evidence.get("tddChain")
    if not isinstance(chains, list) or len(chains) < 2:
        return

    previous = evidence.get("tddSummary")
    previous = previous if isinstance(previous, dict) else {}
    previous_retained = int(previous.get("retained") or 0)
    if previous_retained > len(chains):
        previous = {}
        previous_retained = 0
    new_chains = chains[previous_retained:] if previous else chains
    if previous and not new_chains:
        return

    grouped: dict[str, list[int]] = {}
    retained_indexes: set[int] = set()
    for index, chain in enumerate(chains):
        if not isinstance(chain, dict):
            retained_indexes.add(index)
            continue
        requirement = str(chain.get("requirement") or "unknown")
        grouped.setdefault(requirement, []).append(index)

    previous_groups = {
        str(group.get("requirement") or "unknown"): group
        for group in previous.get("groups", [])
        if isinstance(group, dict)
    }
    groups: list[dict[str, Any]] = []
    for requirement, indexes in sorted(grouped.items()):
        green_indexes = [index for index in indexes if chains[index].get("green")]
        final_index = green_indexes[-1] if green_indexes else indexes[-1]
        retained = {final_index}
        failed_before_final = [
            index
            for index in indexes
            if index < final_index and not chains[index].get("green")
        ]
        if failed_before_final:
            retained.add(failed_before_final[-1])
        retained_indexes.update(retained)
        prior = previous_groups.get(requirement, {})
        fresh_indexes = [index for index in indexes if index >= previous_retained]
        green_count = int(prior.get("green") or 0) + sum(
            bool(chains[index].get("green")) for index in fresh_indexes
        )
        failed_count = int(prior.get("failedOrInvalidated") or 0) + sum(
            not chains[index].get("green") for index in fresh_indexes
        )
        groups.append(
            {
                "requirement": requirement,
                "total": green_count + failed_count,
                "green": green_count,
                "failedOrInvalidated": failed_count,
                "retained": len(retained),
            }
        )

    retained_chains = [
        chain for index, chain in enumerate(chains) if index in retained_indexes
    ]
    total = sum(group["total"] for group in groups)
    omitted = total - len(retained_chains)
    if omitted <= 0 and not previous:
        return

    compact_red_fields = (
        "requirement",
        "exitCode",
        "expectedPattern",
        "testDigests",
        "taskDigest",
        "head",
        "observedAt",
        "baselineReplay",
    )
    compact_red: list[dict[str, Any]] = []
    for chain in retained_chains:
        red = chain.get("red") if isinstance(chain, dict) else None
        if not isinstance(red, dict):
            continue
        compact_red.append(
            {field: red[field] for field in compact_red_fields if field in red}
        )

    evidence["tddChain"] = retained_chains
    evidence["red"] = compact_red
    evidence["tddSummary"] = {
        "policy": "final-green-plus-latest-prior-failure",
        "total": total,
        "green": sum(group["green"] for group in groups),
        "failedOrInvalidated": sum(group["failedOrInvalidated"] for group in groups),
        "retained": len(retained_chains),
        "omitted": omitted,
        "groups": groups,
    }


def config_template() -> str:
    return """version = 5

[policy]
local_mode = "advisory"
test_paths = ["tests", "test", "__tests__", "src/test"]
source_paths = ["src", "app", "lib"]
migration_paths = ["migration", "migrations", "alembic", "flyway", "liquibase", "versions"]

[profiles]
# Optional: preflight = ["environment"]
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

[records]
storage = "private"
publish_high_risk_summary = true

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
# id = "environment"
# command = ["bash", "scripts/check-test-environment.sh"]
# timeout = 120
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
    authoritative = (
        """- User outcome: TODO
- Current behavior and evidence: TODO
- Business and architecture path: TODO
- Invariants and source of truth: TODO
- Requirement/design/API version: TODO
- Unresolved outcome-changing ambiguity: TODO"""
        if risk in {"L2", "Emergency"}
        else """- User-stated result and basis: TODO
- Agent-inferred options: none
- Unresolved outcome-changing ambiguity: none"""
    )
    return f"""# {task_id}: {title}

Risk: {risk}

Depends-On: none

Task-Origin: current-request

Waiting-On: none

Runtime-Claims: none

Operational-Modes: N/A - no conditional runtime behavior

## Authoritative inputs
{authoritative}

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

Before writes/after compaction invoke `$rigorbreeze`. Locate Direct targets read-only, then run `python3 scripts/rigorbreeze.py status --json --path <target>`; never `--path .`. Tasks use `status --json`; use `status --all --compact --json` only for concurrency/dependencies/handoff. Require real base, approval, and window claim.

Direct is taskless only for a deterministic low-consequence result without writer/API/data/auth/permission/payment/lock/migration/dependency/production-config/external-state/release impact. Use focused proof, no full; otherwise L1/L2. Missing high-risk state needs restoration/Emergency; neither supplies product intent, so stop product writes and ask.

Recover facts from authoritative requirements, code, tests, Git, and runtime. Label Agent-inferred options; they cannot add repositories or protected boundaries without outcome approval. Ask only outcome-changing intent. Shaping uses a decision frontier of at most three questions; a prototype answers one decision question, never acceptance. Distinguish current defect from desired result and map observable atoms to acceptance.

Before approval, perform semantic self-review for placeholders, contradictions, oversized scope, and source/fallback ambiguity. Consequence selects gates; outcomes get task branches, `--worktree auto` requires a concurrent writer, and ordering gets a DAG. One worktree has one writer.

Preflight tools/fixtures before observed RED. Use public seams, independent oracles, affected, one final full, and current evidence. A configured `verification/` pack requires Doctor, mapped drive, evidence, Cleanup, and current SHA; unit tests cannot replace it. Verify review feedback with the deletion test; after three failed hypotheses make an architecture stop. Never weaken security/permission/data/migration/rollback/accessibility/compatibility.

After UAT/runtime/follow-up, rerun status and scope before product writes; invalidate old proof or create a successor/handoff. AI cannot approve visual, security, legal, or production conclusions. External writes reconstruct current state and one safe action. Git automation stays manual unless authorized; never delete remote or uncertain state.

Completion requires fresh verification from this turn with command, exit status, scope, and honest gaps. Keep records Git-private by default. Workflow defects become separate Skill tasks, never business-scope expansion.
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
    if version > EVIDENCE_VERSION:
        raise FlowError(
            f"evidence schema {version} is newer than supported schema {EVIDENCE_VERSION}"
        )
    defaults = empty_evidence(task_id)
    for key, value in defaults.items():
        evidence.setdefault(key, value)
    practice = evidence.setdefault("practice", {})
    practice.setdefault("confirmation", None)
    practice.setdefault("events", [])
    evidence["workflowVersion"] = EVIDENCE_VERSION
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
    for evidence_dir in {spec_root(root) / "evidence", records_root(root) / "evidence"}:
        if not evidence_dir.is_dir():
            continue
        for path in sorted(evidence_dir.glob("*.json")):
            if path.name.endswith(".audit.json"):
                continue
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


def require_config(condition: bool, message: str) -> None:
    if not condition:
        raise FlowError(message)


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
    if config_version not in (2, 3, 4, VERSION):
        raise FlowError(f"{CONFIG_NAME} must declare version = 2, 3, 4, or {VERSION}")
    records = config.setdefault("records", {})
    storage = records.setdefault(
        "storage", "private" if config_version >= 5 else "tracked"
    )
    if storage not in {"private", "tracked"}:
        raise FlowError("records.storage must be private or tracked")
    publish_summary = records.setdefault(
        "publish_high_risk_summary", config_version >= 5
    )
    if not isinstance(publish_summary, bool):
        raise FlowError("records.publish_high_risk_summary must be a boolean")
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
        verification_report = item.get("verification_report", False)
        require_config(
            isinstance(verification_report, bool),
            f"check {check_id} verification_report must be boolean",
        )
        if verification_report:
            report = item.get("report")
            verification_root = item.get("verification_root")
            require_config(
                check_id == "acceptance",
                "verification_report requires acceptance check",
            )
            require_config(
                isinstance(report, str) and report.endswith(".json"),
                "verification_report requires JSON report",
            )
            require_config(
                isinstance(verification_root, str) and bool(verification_root),
                "verification_report requires verification_root",
            )
            require_config(
                item.get("minimum_level") in VERIFICATION_LEVELS,
                "verification_report minimum_level is invalid",
            )
            pack = resolve_project_path(root, verification_root, "verification_root")
            require_config(
                pack.is_dir(),
                f"verification_root directory is missing: {verification_root}",
            )
        checks[check_id] = item
    config["_checks"] = checks
    for profile in ("preflight", "affected", "full"):
        ids = profiles.get(profile, [])
        if not isinstance(ids, list) or not all(isinstance(item, str) for item in ids):
            raise FlowError(f"profiles.{profile} must be an array of check IDs")
        unknown = [item for item in ids if item not in STANDARD_CHECK_IDS]
        if unknown:
            raise FlowError(
                f"profiles.{profile} contains unknown checks: {', '.join(unknown)}"
            )
        if profile == "preflight" and any(item != "environment" for item in ids):
            raise FlowError("profiles.preflight may contain only the environment check")
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


def subprocess_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


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
            *(f"rigorbreeze/scripts/{name}.py" for name in KERNEL_HELPER_NAMES),
        )
        if wrapper
        else (
            "scripts/rigorbreeze.py",
            *(f"scripts/{name}.py" for name in KERNEL_HELPER_NAMES),
        )
    )
    return (
        "AGENTS.md",
        CONFIG_NAME,
        *runner_paths,
        "spec/index.md",
    )


def workflow_metadata_paths(root: Path, task_id: str) -> set[str]:
    paths = set(managed_workflow_paths(root))
    if record_settings(root)["storage"] == "tracked":
        paths.update(
            {
                f"spec/changes/{task_id}.md",
                f"spec/evidence/{task_id}.json",
                f"spec/archive/{task_id}.md",
            }
        )
    paths.add(f"spec/evidence/{task_id}.audit.json")
    return paths


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
