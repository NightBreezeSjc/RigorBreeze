"""Environment preflight, TDD observation, profile execution, and delivery checks for RigorBreeze."""

from __future__ import annotations
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any
import flow_records
import flow_policy
import flow_state

FlowError = flow_state.FlowError


def command_executable(root: Path, value: str) -> str | None:
    candidate = Path(value)
    if candidate.is_absolute():
        return (
            str(candidate)
            if candidate.is_file()
            and (os.name == "nt" or os.access(candidate, os.X_OK))
            else None
        )
    if "/" in value or "\\" in value:
        resolved = (root / candidate).resolve()
        return (
            str(resolved)
            if resolved.is_file() and (os.name == "nt" or os.access(resolved, os.X_OK))
            else None
        )
    return shutil.which(value)


def builtin_environment_issues(
    root: Path, command: list[str], tests: list[str]
) -> list[str]:
    issues = [relative for relative in tests if not (root / relative).is_file()]
    normalized = command[1:] if command and command[0] == "--" else command
    if not normalized:
        return [*issues, "RED command is empty"]
    executable = normalized[0]
    if command_executable(root, executable) is None:
        issues.append(f"command executable is unavailable: {executable}")
        return issues
    name = Path(executable).name.lower().removesuffix(".cmd")
    if name in {"npm", "pnpm", "yarn", "npx"}:
        manifest = root / "package.json"
        package: dict[str, Any] = {}
        if not manifest.is_file():
            issues.append("package.json is missing for the Node test command")
        elif name != "npx":
            try:
                package = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                issues.append("package.json is unreadable")
            else:
                script = None
                if name == "npm" and len(normalized) > 1:
                    script = (
                        normalized[2]
                        if normalized[1] == "run" and len(normalized) > 2
                        else "test"
                        if normalized[1] in {"test", "t"}
                        else None
                    )
                elif len(normalized) > 1:
                    script = normalized[1]
                if script and script not in package.get("scripts", {}):
                    issues.append(f"package.json script is missing: {script}")
        dependencies = root / "node_modules"
        requires_dependencies = bool(
            manifest.is_file()
            and (
                package.get("dependencies")
                or package.get("devDependencies")
                or package.get("optionalDependencies")
            )
        )
        if requires_dependencies and not dependencies.is_dir():
            issues.append(
                "node_modules is unavailable; configure the project environment "
                "adapter for a shared dependency directory or install dependencies"
            )
    if name in {"mvn", "mvnw", "mvnw.cmd"}:
        if name.startswith("mvnw") and command_executable(root, executable) is None:
            issues.append(f"Maven wrapper is unavailable: {executable}")
        if shutil.which("java") is None:
            issues.append("Java is unavailable for the Maven test command")
    return issues


def environment_fingerprint(
    root: Path, config: dict[str, Any], extra_command: list[str] | None = None
) -> str:
    commands = [
        check["command"]
        for check_id in config.get("profiles", {}).get("preflight", [])
        if (check := config.get("_checks", {}).get(check_id))
    ]
    if extra_command:
        commands.append(extra_command)
    dependency_digests = {}
    for name in sorted(flow_state.DEPENDENCY_NAMES):
        path = root / name
        if path.is_file():
            dependency_digests[name] = flow_state.sha256_bytes(path.read_bytes())
    executables = {
        command[0]: command_executable(root, command[0])
        for command in commands
        if command
    }
    node_modules = root / "node_modules"
    payload = {
        "configDigest": flow_state.config_digest(root),
        "dependencies": dependency_digests,
        "executables": executables,
        "nodeModules": str(node_modules.resolve()) if node_modules.is_dir() else None,
    }
    return flow_state.sha256_bytes(json.dumps(payload, sort_keys=True).encode())


def ensure_configured_environment_preflight(
    root: Path,
    state: dict[str, Any],
    config: dict[str, Any],
    *,
    extra_command: list[str] | None = None,
    force: bool = False,
) -> None:
    ids = list(config.get("profiles", {}).get("preflight", []))
    if not ids:
        return
    fingerprint = environment_fingerprint(root, config, extra_command)
    previous = state.get("environmentPreflight") or {}
    if (
        not force
        and previous.get("passed") is True
        and previous.get("fingerprint") == fingerprint
    ):
        return
    check = config.get("_checks", {}).get("environment")
    if not check:
        raise FlowError("environment preflight is declared but not configured")
    cwd = flow_state.resolve_project_path(
        root, check.get("cwd", "."), "environment cwd"
    )
    timeout = check.get("timeout", 120)
    environment = {**os.environ, **check.get("env", {})}
    started = time.monotonic()
    try:
        result = subprocess.run(
            check["command"],
            cwd=cwd,
            env=environment,
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        result = subprocess.CompletedProcess(check["command"], 127, "", str(exc))
    except subprocess.TimeoutExpired as exc:
        result = subprocess.CompletedProcess(
            check["command"],
            124,
            flow_state.subprocess_text(exc.stdout),
            "\n".join(
                part
                for part in (
                    flow_state.subprocess_text(exc.stderr),
                    f"timed out after {timeout} seconds",
                )
                if part
            ),
        )
    output = ((result.stdout or "") + (result.stderr or "")).strip()
    state["environmentPreflight"] = {
        "passed": result.returncode == 0,
        "fingerprint": fingerprint,
        "command": [flow_state.redact(part) for part in check["command"]],
        "exitCode": result.returncode,
        "durationMs": round((time.monotonic() - started) * 1000),
        "summary": flow_state.redact(output[-1000:]),
        "checkedAt": flow_state.now_iso(),
    }
    flow_policy.save_state(root, state)
    if result.returncode != 0:
        raise FlowError(
            "environment preflight failed before business evidence: "
            + (flow_state.redact(output[-1000:]) or f"exit {result.returncode}")
        )


def command_red(
    root: Path,
    requirement: str,
    expect_pattern: str,
    tests: list[str],
    command: list[str],
) -> None:
    state = flow_state.load_state(root)
    if not flow_policy.approval_valid(root, state):
        flow_policy.save_state(root, state)
        raise FlowError("task approval is missing or invalid")
    active = flow_state.active_task(state)
    declared = flow_policy.acceptance_ids(root, state)
    if requirement not in declared:
        raise FlowError(
            f"RED requirement {requirement} is not declared in the task acceptance criteria"
        )
    evidence = flow_state.load_evidence(root, active["id"])
    baseline = evidence.get("baseline") or {}
    config = flow_state.load_config(root)
    test_roots = flow_policy.configured_paths(
        config, "test_paths", ["tests", "test", "src/test"]
    )
    source_roots = flow_policy.configured_paths(
        config, "source_paths", ["src", "app", "lib"]
    )
    if tests:
        invalid_tests = [
            relative
            for relative in tests
            if not flow_policy.path_under(relative, test_roots)
        ]
        if invalid_tests:
            raise FlowError(
                "RED test files are outside configured test paths: "
                + ", ".join(invalid_tests)
            )
    current_paths = flow_state.working_tree_paths(root)
    baseline_paths = set(baseline.get("workingTreePaths", []))
    baseline_digests = baseline.get("workingTreeDigests", {})
    changed_after_approval: list[str] = []
    for relative in current_paths:
        path = root / relative
        digest = flow_state.sha256_bytes(path.read_bytes()) if path.is_file() else None
        if relative not in baseline_paths or baseline_digests.get(relative) != digest:
            changed_after_approval.append(relative)
    production_changes = [
        relative
        for relative in changed_after_approval
        if flow_policy.path_under(relative, source_roots)
        and not flow_policy.path_under(relative, test_roots)
    ]
    if not tests and active["risk"] in {"L1", "L2"}:
        raise FlowError(f"{active['risk']} RED requires at least one --test file")
    if (
        not tests
        and active["risk"] != "Emergency"
        and flow_state.effective_mode(root, None, state) == "enforced"
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
    environment_issues = builtin_environment_issues(root, normalized_command, tests)
    if environment_issues:
        raise FlowError(
            "environment preflight failed before RED: " + "; ".join(environment_issues)
        )
    ensure_configured_environment_preflight(root, state, config)
    test_digests = {
        relative: flow_policy.test_file_digest(root, relative) for relative in tests
    }
    current_digest = flow_state.task_digest(root, state)
    prior_reds = [
        chain.get("red") or {}
        for chain in evidence.get("tddChain", [])
        if chain.get("requirement") == requirement
        and (chain.get("red") or {}).get("taskDigest") == current_digest
    ]
    replay = bool(
        production_changes
        and prior_reds
        and any(
            prior_reds[-1].get("testDigests", {}).get(relative) != digest
            for relative, digest in test_digests.items()
        )
    )
    baseline_replay = None
    if production_changes and not replay:
        raise FlowError(
            "production code changed before RED was observed: "
            + ", ".join(production_changes)
        )
    if replay:
        outside_scope = [
            relative
            for relative in tests
            if not flow_policy.path_allowed(
                relative, flow_policy.allowed_scope(root, state)
            )
        ]
        if outside_scope:
            raise FlowError(
                "RED replay test files are outside the approved scope: "
                + ", ".join(outside_scope)
            )
        baseline_sha = str(baseline.get("head") or "")
        if not baseline_sha or not flow_state.is_git_repo(root):
            raise FlowError(
                "RED baseline replay requires an immutable Git baseline SHA"
            )
        if (
            flow_state.git(
                root, "cat-file", "-e", f"{baseline_sha}^{{commit}}"
            ).returncode
            != 0
        ):
            raise FlowError(f"RED baseline replay commit is missing: {baseline_sha}")
        with tempfile.TemporaryDirectory(prefix="rigorbreeze-red-") as directory:
            replay_root = Path(directory) / "checkout"
            added = flow_state.git(
                root, "worktree", "add", "--detach", str(replay_root), baseline_sha
            )
            if added.returncode != 0:
                raise FlowError(
                    "failed to create RED baseline replay worktree: "
                    + (added.stderr or added.stdout).strip()
                )
            try:
                for relative in tests:
                    source = (root / relative).resolve()
                    destination = (replay_root / relative).resolve()
                    try:
                        destination.relative_to(replay_root.resolve())
                    except ValueError as exc:
                        raise FlowError(
                            f"RED replay test escapes temporary worktree: {relative}"
                        ) from exc
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(source.read_bytes())
                replay_command: list[str] = []
                for argument in command:
                    candidate = Path(argument)
                    if candidate.is_absolute():
                        try:
                            relative = candidate.resolve().relative_to(root.resolve())
                        except ValueError:
                            replay_command.append(argument)
                        else:
                            normalized = relative.as_posix()
                            if normalized not in tests:
                                raise FlowError(
                                    "RED replay command references a non-test path in the "
                                    f"current worktree: {normalized}"
                                )
                            replay_command.append(str(replay_root / relative))
                    else:
                        replay_command.append(argument)
                result = flow_state.run_command(replay_command, replay_root)
            finally:
                removed = flow_state.git(
                    root, "worktree", "remove", "--force", str(replay_root)
                )
                if removed.returncode != 0:
                    flow_state.git(root, "worktree", "prune")
            baseline_replay = {
                "baselineSha": baseline_sha,
                "previousRedObservedAt": prior_reds[-1].get("observedAt"),
                "testDigests": test_digests,
            }
    else:
        result = flow_state.run_command(command, root)
    output = ((result.stdout or "") + (result.stderr or "")).strip()
    if result.returncode == 0:
        raise FlowError("RED command passed; expected an observed failure")
    unrelated_failure = result.returncode in {124, 126, 127} or re.search(
        r"(?:ModuleNotFoundError|ImportError|No module named|command not found|permission denied)",
        output,
        re.I,
    )
    if unrelated_failure:
        raise FlowError(
            "RED command failed because of tooling or environment, not behavior"
        )
    if not re.search(expect_pattern, output, re.I | re.M):
        raise FlowError("RED output did not match the expected failure pattern")
    record = {
        "requirement": requirement,
        "command": [
            flow_state.redact(part)
            for part in (command[1:] if command and command[0] == "--" else command)
        ],
        "exitCode": result.returncode,
        "expectedPattern": expect_pattern,
        "testDigests": test_digests,
        "summary": flow_state.redact(output[-2000:]),
        "taskDigest": current_digest,
        "projectFingerprint": flow_policy.project_fingerprint(root),
        "head": flow_state.current_head(root) if flow_state.is_git_repo(root) else None,
        "observedAt": flow_state.now_iso(),
    }
    if baseline_replay:
        record["baselineReplay"] = baseline_replay
    evidence["red"].append(record)
    evidence["tddChain"].append(
        {"requirement": requirement, "red": record, "green": None}
    )
    flow_state.save_evidence(root, active["id"], evidence)
    state["red"] = record
    state["phase"] = "red"
    flow_policy.save_state(root, state)
    print(
        "RED re-observed against approved baseline and recorded"
        if baseline_replay
        else "RED observed and recorded"
    )


def command_verify_stateless(root: Path, config: dict[str, Any]) -> int:
    full_ids = list(config.get("profiles", {}).get("full", []))
    if not full_ids:
        raise FlowError("enforced full profile must declare at least one check")
    check_ids = list(
        dict.fromkeys(
            [
                *config.get("profiles", {}).get("preflight", []),
                *full_ids,
            ]
        )
    )
    executions: dict[
        tuple[tuple[str, ...], str, tuple[tuple[str, str], ...], int],
        subprocess.CompletedProcess[str],
    ] = {}
    failures: list[str] = []
    for check_id in check_ids:
        check = config["_checks"].get(check_id)
        if not check:
            failures.append(f"{check_id}: not configured")
            continue
        cwd = flow_state.resolve_project_path(
            root, check.get("cwd", "."), f"check {check_id} cwd"
        )
        environment = {**os.environ, **check.get("env", {})}
        timeout = check.get("timeout", 900)
        signature = (
            tuple(check["command"]),
            str(cwd),
            tuple(sorted(environment.items())),
            timeout,
        )
        result = executions.get(signature)
        if result is None:
            try:
                result = subprocess.run(
                    check["command"],
                    cwd=cwd,
                    env=environment,
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
                result = subprocess.CompletedProcess(
                    check["command"],
                    124,
                    flow_state.subprocess_text(exc.stdout),
                    "\n".join(
                        part
                        for part in (
                            flow_state.subprocess_text(exc.stderr),
                            f"timed out after {timeout} seconds",
                        )
                        if part
                    ),
                )
            executions[signature] = result
        if result.returncode != 0:
            failures.append(f"{check_id}: exit {result.returncode}")
            continue
        try:
            flow_policy.report_record(root, check.get("report"))
            for relative in check.get("artifacts", []):
                artifact = flow_state.resolve_project_path(
                    root, relative, f"check {check_id} artifact"
                )
                if not artifact.is_file() or not artifact.read_bytes():
                    raise FlowError(f"check {check_id} artifact is missing or empty")
        except FlowError as exc:
            failures.append(f"{check_id}: {exc}")
    if failures:
        print("stateless full profile failed (enforced): " + "; ".join(failures))
        return 1
    print(
        "stateless full profile passed (enforced); this proves CI checks only, "
        "not task acceptance, archive, merge, or release evidence"
    )
    return 0


def command_verify_profile(
    root: Path, profile: str, requested_mode: str | None, force: bool = False
) -> int:
    state = (
        flow_state.load_state(root)
        if flow_state.state_path(root).is_file()
        or flow_state.legacy_state_path(root).is_file()
        else None
    )
    config = flow_state.load_config(root)
    if (
        profile == "full"
        and requested_mode == "enforced"
        and (state is None or not state.get("activeTask"))
    ):
        return command_verify_stateless(root, config)
    if state is None:
        raise FlowError("initialize RigorBreeze before task verification")
    if not flow_policy.approval_valid(root, state):
        flow_policy.save_state(root, state)
        raise FlowError("task approval is missing or invalid")
    active = flow_state.active_task(state)
    mode = flow_state.effective_mode(root, requested_mode, state)
    if profile not in {"affected", "full"}:
        raise FlowError("configured verification profile must be affected or full")
    flow_policy.ensure_scope_current(root, state)
    if not force:
        current = state.get("verification") or {}
        reusable = (
            flow_policy.full_profile_current(root, state)
            if profile == "full"
            else flow_policy.verification_current(root, state)
            and current.get("profile") in {"affected", "full"}
        )
        reusable = bool(
            reusable and not (mode == "enforced" and current.get("mode") != "enforced")
        )
        if reusable:
            print(
                f"{profile} profile reused ({mode}); project fingerprint is unchanged"
            )
            return 0
    if profile == "full":
        ensure_configured_environment_preflight(root, state, config)
    if active["risk"] in {"L1", "L2", "Emergency"}:
        if not state.get("red"):
            raise FlowError("current RED or incident reproduction evidence is required")
        if not flow_policy.test_chain_current(root, state):
            raise FlowError("RED test changed after observation; observe RED again")
    destructive = flow_policy.destructive_migrations(
        root, flow_policy.task_change_paths(root, state)
    )
    if destructive:
        raise FlowError("destructive migration detected: " + ", ".join(destructive))
    evidence = flow_state.load_evidence(root, active["id"])
    check_ids = list(config.get("profiles", {}).get(profile, []))
    if mode == "enforced" and not check_ids:
        raise FlowError(f"enforced {profile} profile must declare at least one check")
    if profile == "full":
        policy_issues = flow_policy.l2_full_profile_issues(
            root, state, check_ids, config
        )
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
                "category": flow_policy.check_category(check_id),
                "profile": profile,
                "passed": False,
                "mode": mode,
                "error": "check is required by profile but not configured",
                "recordedAt": flow_state.now_iso(),
            }
            records.append(record)
            evidence["checkRuns"].append(record)
            passed = False
            continue
        risks = check.get("risks", ["L0", "L1", "L2", "Emergency"])
        if active["risk"] not in risks:
            record = {
                "checkId": check_id,
                "category": flow_policy.check_category(check_id),
                "profile": profile,
                "passed": True,
                "mode": mode,
                "notApplicable": {
                    "reason": f"check does not apply to risk {active['risk']}",
                    "approvedBy": "rigorbreeze policy",
                    "scope": active["risk"],
                },
                "recordedAt": flow_state.now_iso(),
            }
            records.append(record)
            evidence["checkRuns"].append(record)
            continue
        resolved_cwd = flow_state.resolve_project_path(
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
                    flow_state.subprocess_text(exc.stdout),
                    "\n".join(
                        part
                        for part in (
                            flow_state.subprocess_text(exc.stderr),
                            timeout_message,
                        )
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
                report = flow_policy.report_record(root, check.get("report"))
            except FlowError as exc:
                check_passed = False
                output = f"{output}\n{exc}".strip()
        fingerprint = flow_policy.project_fingerprint(root)
        artifacts: list[dict[str, Any]] = []
        if check_passed:
            try:
                artifacts = flow_policy.record_artifacts(
                    root,
                    evidence,
                    check_id,
                    check.get("artifacts", []),
                    fingerprint,
                    flow_state.task_digest(root, state),
                )
            except FlowError as exc:
                check_passed = False
                output = f"{output}\n{exc}".strip()
        record = {
            "checkId": check_id,
            "category": flow_policy.check_category(check_id),
            "profile": profile,
            "mode": mode,
            "command": [flow_state.redact(part) for part in check["command"]],
            "exitCode": result.returncode,
            "passed": check_passed,
            "durationMs": duration_ms,
            "summary": flow_state.redact(output[-2000:]),
            "report": report,
            "artifacts": [item["sha256"] for item in artifacts],
            "taskDigest": flow_state.task_digest(root, state),
            "projectFingerprint": fingerprint,
            "head": flow_state.current_head(root)
            if flow_state.is_git_repo(root)
            else None,
            "recordedAt": flow_state.now_iso(),
        }
        if reused_from:
            record["reusedFromCheckId"] = reused_from
        records.append(record)
        evidence["checkRuns"].append(record)
        passed = passed and check_passed
    fingerprint = flow_policy.project_fingerprint(root)
    verification = {
        "toolVersion": flow_state.TOOL_VERSION,
        "profile": profile,
        "configured": True,
        "mode": mode,
        "checks": [record["checkId"] for record in records],
        "passed": passed,
        "taskDigest": flow_state.task_digest(root, state),
        "projectFingerprint": fingerprint,
        "configDigest": flow_state.config_digest(root),
        "head": flow_state.current_head(root) if flow_state.is_git_repo(root) else None,
        "verifiedAt": flow_state.now_iso(),
    }
    if passed:
        for record in evidence.get("acceptance", []):
            if (
                record.get("verificationBinding") == "pending"
                and record.get("taskDigest") == verification["taskDigest"]
                and record.get("projectFingerprint")
                == verification["projectFingerprint"]
                and record.get("head") == verification["head"]
            ):
                record["verificationBinding"] = "current"
                record["verification"] = {
                    "profile": profile,
                    "configDigest": verification["configDigest"],
                    "verifiedAt": verification["verifiedAt"],
                }
    evidence["verification"] = verification
    evidence["verifications"].append(verification)
    if passed and state.get("red"):
        if profile == "full":
            current_digest = flow_state.task_digest(root, state)
            for chain in evidence["tddChain"]:
                red = chain.get("red") or {}
                if red.get(
                    "taskDigest"
                ) == current_digest and flow_policy.red_record_tests_current(root, red):
                    chain["green"] = verification
        else:
            for chain in reversed(evidence["tddChain"]):
                if chain.get("requirement") == state["red"].get(
                    "requirement"
                ) and not chain.get("green"):
                    chain["green"] = verification
                    break
    flow_state.compact_completed_check_runs(evidence)
    flow_state.compact_verification_history(evidence)
    if profile == "full":
        flow_state.compact_completed_tdd_history(evidence)
    flow_state.save_evidence(root, active["id"], evidence)
    state["verification"] = verification
    if not passed:
        state["phase"] = "implementing"
    elif any(
        record.get("kind") == "governance"
        for record in flow_policy.current_structured_records(root, state, "release")
    ):
        state["phase"] = "release-ready"
    elif flow_policy.current_structured_records(root, state, "acceptance"):
        state["phase"] = "accepted"
    else:
        state["phase"] = "verified"
    flow_policy.save_state(root, state)
    if passed:
        print(f"{profile} profile passed ({mode})")
        return 0
    if mode == "advisory":
        print(f"{profile} profile has failures (advisory; not blocking)")
        return 0
    print(f"{profile} profile failed (enforced)")
    return 1


def command_check(root: Path, gate: str, requested_mode: str | None = None) -> None:
    state = flow_state.load_state(root)
    if flow_policy.refresh_approval(root, state):
        flow_policy.save_state(root, state)
    active = state.get("activeTask")
    closed = None if active else (state.get("lastClosed") or None)
    if not active and not (
        gate == "merge" and closed and closed.get("outcome") == "completed"
    ):
        flow_state.active_task(state)
    if gate == "commit":
        if not flow_state.is_git_repo(root):
            raise FlowError("commit gate requires a Git repository")
        paths = flow_policy.staged_files(root)
        if not paths:
            raise FlowError("commit gate requires staged files")
        secrets = [path for path in paths if flow_state.is_secret_path(path)]
        if secrets:
            raise FlowError("secret paths are forbidden: " + ", ".join(secrets))
        secret_content, secret_exemptions = flow_policy.secret_content_scan(root, paths)
        if secret_content:
            raise FlowError(
                "secret-like content detected: " + ", ".join(secret_content)
            )
        if secret_exemptions:
            print(
                "synthetic secret fixture exemptions: " + ", ".join(secret_exemptions)
            )
        dependencies = [path for path in paths if flow_policy.is_dependency_path(path)]
        if dependencies and not state["approvals"]["dependencies"]:
            raise FlowError(
                "dependency approval is required: " + ", ".join(dependencies)
            )
        migrations = [
            path
            for path in paths
            if flow_policy.is_configured_migration_path(root, path)
        ]
        if migrations and not state["approvals"]["migrations"]:
            raise FlowError("migration approval is required: " + ", ".join(migrations))
        flow_policy.ensure_scope_current(root, state)
        out_of_scope = [
            path
            for path in paths
            if not flow_policy.task_owned_path(
                path, state, flow_policy.allowed_scope(root, state)
            )
        ]
        if out_of_scope:
            raise FlowError(
                "staged files are outside approved scope: " + ", ".join(out_of_scope)
            )
        if not flow_policy.configured_verification_current(root, state):
            raise FlowError("configured affected/full verification is missing or stale")
    elif gate == "merge":
        if active:
            flow_policy.ensure_delivery_quality(root, state)
        elif not flow_records.closed_context_current(root, state):
            raise FlowError("closed task evidence changed after archive")
        elif not closed.get("verification"):
            raise FlowError("closed task has no delivery-quality verification")
    elif gate == "release":
        flow_policy.ensure_release(root, state)
    else:
        raise FlowError(f"unknown gate: {gate}")
    flow_policy.save_state(root, state)
    print(f"check {gate}: passed")
