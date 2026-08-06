#!/usr/bin/env python3
"""Run repository-only RigorBreeze Agent behavior evaluations."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
DEFAULT_CONTRACT = HERE / "scenarios.json"
REQUIRED_CASE_KEYS = {
    "id": str,
    "title": str,
    "prompt": str,
    "fixtureFiles": dict,
    "requiredMarkers": list,
    "forbiddenMarkers": list,
    "requiredTranscriptPatterns": list,
    "forbiddenTranscriptPatterns": list,
    "orderedTranscriptPatterns": list,
    "requiredChangedPaths": list,
    "forbiddenChangedPaths": list,
    "syntheticTranscript": str,
    "syntheticChangedPaths": list,
    "allowQuestions": bool,
    "passCriteria": str,
}
SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s\"']+"),
    re.compile(r"(?i)((?:api[_-]?key|token|password|secret)\s*[:=]\s*)[^\s\"']+"),
)


def _safe_relative(value: str, *, allow_glob: bool) -> str:
    candidate = value.replace("\\", "/")
    path = PurePosixPath(candidate)
    if path.is_absolute() or ".." in path.parts or not candidate.strip("./"):
        raise ValueError(f"path escape is forbidden: {value}")
    if not allow_glob and any(character in candidate for character in "*?["):
        raise ValueError(f"fixture path cannot contain a glob: {value}")
    return candidate


def _string_list(case_id: str, name: str, value: Any) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{case_id}.{name} must be a list of strings")
    return value


def load_contract(path: Path = DEFAULT_CONTRACT) -> dict[str, Any]:
    try:
        contract = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read behavior contract: {exc}") from exc
    if not isinstance(contract, dict) or contract.get("schemaVersion") != 1:
        raise ValueError("behavior contract schemaVersion must be 1")
    cases = contract.get("cases")
    if not isinstance(cases, list) or len(cases) != 6:
        raise ValueError("behavior contract must define exactly six cases")

    seen: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("every behavior case must be an object")
        for key, expected_type in REQUIRED_CASE_KEYS.items():
            if not isinstance(case.get(key), expected_type):
                raise ValueError(f"behavior case field {key} has the wrong type")
        case_id = case["id"]
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", case_id):
            raise ValueError(f"invalid behavior case id: {case_id}")
        if case_id in seen:
            raise ValueError(f"duplicate behavior case id: {case_id}")
        seen.add(case_id)

        fixtures = case["fixtureFiles"]
        if (
            not fixtures
            or any(not isinstance(key, str) for key in fixtures)
            or any(not isinstance(value, str) for value in fixtures.values())
        ):
            raise ValueError(f"{case_id}.fixtureFiles must map paths to strings")
        for relative in fixtures:
            _safe_relative(relative, allow_glob=False)
        for key in (
            "requiredMarkers",
            "forbiddenMarkers",
            "requiredTranscriptPatterns",
            "forbiddenTranscriptPatterns",
            "orderedTranscriptPatterns",
            "requiredChangedPaths",
            "forbiddenChangedPaths",
            "syntheticChangedPaths",
        ):
            values = _string_list(case_id, key, case[key])
            if key.endswith("Paths"):
                for value in values:
                    _safe_relative(value, allow_glob=True)
            if "Transcript" in key:
                for pattern in values:
                    try:
                        re.compile(pattern, re.I | re.M)
                    except re.error as exc:
                        raise ValueError(
                            f"invalid regex in {case_id}.{key}: {exc}"
                        ) from exc
    return contract


def redact_text(text: str) -> str:
    redacted = text.replace(str(Path.home()), "$HOME")
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub(r"\1[REDACTED]", redacted)
    return redacted


def _as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _path_matches(path: str, pattern: str) -> bool:
    path_parts = tuple(part for part in path.replace("\\", "/").split("/") if part)
    pattern_parts = tuple(part for part in pattern.split("/") if part)

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
            and PurePosixPath(path_parts[path_index]).match(candidate)
            and matches(path_index + 1, pattern_index + 1)
        )

    return matches(0, 0)


def score_case(
    case: dict[str, Any],
    result: dict[str, Any],
    transcript: str,
    changed_paths: list[str],
) -> dict[str, Any]:
    issues: list[str] = []
    if result.get("caseId") != case["id"]:
        issues.append("result caseId does not match the scenario")
    markers = result.get("markers")
    markers = markers if isinstance(markers, list) else []
    for marker in case["requiredMarkers"]:
        if marker not in markers:
            issues.append(f"required marker missing: {marker}")
    for marker in case["forbiddenMarkers"]:
        if marker in markers:
            issues.append(f"forbidden marker observed: {marker}")

    for pattern in case["requiredTranscriptPatterns"]:
        if not re.search(pattern, transcript, re.I | re.M):
            issues.append(f"required transcript observation missing: {pattern}")
    for pattern in case["forbiddenTranscriptPatterns"]:
        if re.search(pattern, transcript, re.I | re.M):
            issues.append(f"forbidden transcript action observed: {pattern}")
    cursor = 0
    for pattern in case["orderedTranscriptPatterns"]:
        match = re.search(pattern, transcript[cursor:], re.I | re.M)
        if not match:
            issues.append(f"ordered transcript observation missing: {pattern}")
            break
        cursor += match.end()

    for pattern in case["requiredChangedPaths"]:
        if not any(_path_matches(path, pattern) for path in changed_paths):
            issues.append(f"required changed path missing: {pattern}")
    for pattern in case["forbiddenChangedPaths"]:
        matches = [path for path in changed_paths if _path_matches(path, pattern)]
        if matches:
            issues.append(f"forbidden changed path observed: {pattern} -> {matches}")

    questions = result.get("questions")
    if not isinstance(questions, list):
        issues.append("result questions must be a list")
    elif not case["allowQuestions"] and questions:
        issues.append("scenario does not allow questions")
    if "fresh-verification" in case["requiredMarkers"]:
        verification = result.get("verification")
        if not (
            isinstance(verification, dict)
            and verification.get("fresh") is True
            and verification.get("exitCode") == 0
            and str(verification.get("command", "")).strip()
            and str(verification.get("scope", "")).strip()
        ):
            issues.append(
                "fresh verification command, exit status, and scope are required"
            )
    return {"caseId": case["id"], "passed": not issues, "issues": issues}


def _run(
    argv: list[str], cwd: Path, *, input_text: str | None = None, timeout: int = 120
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=cwd,
        input=input_text,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=timeout,
    )


def prepare_fixture(case: dict[str, Any], workspace: Path) -> Path:
    workspace.mkdir(parents=True, exist_ok=False)
    for relative, content in case["fixtureFiles"].items():
        safe = _safe_relative(relative, allow_glob=False)
        target = (workspace / safe).resolve()
        if workspace.resolve() not in target.parents:
            raise ValueError(f"fixture path escaped workspace: {relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    (workspace / ".gitignore").write_text(".agents/\n", encoding="utf-8")
    for argv in (
        ["git", "init", "-q"],
        ["git", "config", "user.name", "RigorBreeze Behavior Test"],
        ["git", "config", "user.email", "behavior@example.invalid"],
        ["git", "add", "."],
        ["git", "commit", "-qm", "Create synthetic behavior fixture"],
    ):
        result = _run(argv, workspace)
        if result.returncode != 0:
            raise RuntimeError(redact_text(result.stderr or result.stdout))
    return workspace


def _changed_paths(workspace: Path) -> list[str]:
    result = _run(["git", "status", "--porcelain=v1", "-z"], workspace)
    if result.returncode != 0:
        raise RuntimeError(redact_text(result.stderr or result.stdout))
    paths: set[str] = set()
    entries = result.stdout.split("\0")
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue
        status = entry[:2]
        relative = entry[3:]
        if relative:
            paths.add(relative.replace("\\", "/"))
        if status[0] in {"R", "C"} and index < len(entries):
            original = entries[index]
            index += 1
            if original:
                paths.add(original.replace("\\", "/"))
    return sorted(paths)


def _safe_version(version: str) -> str:
    if not re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z._-]*", version):
        raise ValueError(f"invalid behavior evaluation version: {version}")
    return version


def _result_directory(version: str) -> Path:
    version = _safe_version(version)
    result = _run(
        ["git", "rev-parse", "--git-path", f"rigorbreeze/behavior-evals/{version}"],
        REPO_ROOT,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "behavior evaluations require the RigorBreeze Git repository"
        )
    path = Path(result.stdout.strip())
    return path if path.is_absolute() else (REPO_ROOT / path).resolve()


def _output_schema(markers: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["caseId", "markers", "questions", "verification"],
        "properties": {
            "caseId": {"type": "string"},
            "markers": {
                "type": "array",
                "items": {"type": "string", "enum": markers},
            },
            "questions": {"type": "array", "items": {"type": "string"}},
            "verification": {
                "anyOf": [
                    {"type": "null"},
                    {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["command", "exitCode", "scope", "fresh"],
                        "properties": {
                            "command": {"type": "string"},
                            "exitCode": {"type": "integer"},
                            "scope": {"type": "string"},
                            "fresh": {"type": "boolean"},
                        },
                    },
                ]
            },
        },
    }


def _install_candidate(workspace: Path, skill_dir: Path) -> None:
    local_skill = workspace / ".agents" / "skills" / "rigorbreeze"
    local_skill.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(skill_dir, local_skill)
    runner = local_skill / "scripts" / "flow.py"
    initialized = _run(
        [sys.executable, "-B", str(runner), "--root", str(workspace), "init"],
        workspace,
    )
    if initialized.returncode != 0:
        raise RuntimeError(redact_text(initialized.stderr or initialized.stdout))
    committed = _run(
        ["git", "add", "AGENTS.md", "rigorbreeze.toml", "scripts", "spec/index.md"],
        workspace,
    )
    if committed.returncode == 0:
        committed = _run(
            ["git", "commit", "-qm", "Install candidate RigorBreeze workflow"],
            workspace,
        )
    if committed.returncode != 0:
        raise RuntimeError(redact_text(committed.stderr or committed.stdout))


def _live_case(
    case: dict[str, Any],
    *,
    repetition: int,
    codex: str,
    skill_dir: Path,
    timeout: int,
    output_dir: Path,
    marker_vocabulary: list[str],
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix=f"rigorbreeze-{case['id']}-") as directory:
        workspace = prepare_fixture(case, Path(directory) / "repo")
        _install_candidate(workspace, skill_dir)
        schema_path = Path(directory) / "result-schema.json"
        final_path = Path(directory) / "final.json"
        schema_path.write_text(
            json.dumps(_output_schema(marker_vocabulary), indent=2), encoding="utf-8"
        )
        prompt = _live_prompt(case)
        argv = _codex_argv(codex, workspace, schema_path, final_path)
        started = datetime.now().astimezone().isoformat(timespec="seconds")
        try:
            process = _run(argv, workspace, input_text=prompt, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            transcript = redact_text(_as_text(exc.stdout) + _as_text(exc.stderr))
            process_code = 124
            final: dict[str, Any] = {
                "caseId": case["id"],
                "markers": [],
                "questions": [],
                "verification": None,
            }
        else:
            transcript = redact_text(process.stdout + process.stderr)
            process_code = process.returncode
            try:
                final = json.loads(final_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                final = {
                    "caseId": case["id"],
                    "markers": [],
                    "questions": [],
                    "verification": None,
                }
        changed = _changed_paths(workspace)
        verdict = score_case(case, final, transcript, changed)
        if process_code != 0:
            verdict["issues"].append(f"codex exec returned {process_code}")
            verdict["passed"] = False
        stem = f"{case['id']}-{repetition}"
        (output_dir / f"{stem}.jsonl").write_text(transcript, encoding="utf-8")
        (output_dir / f"{stem}.json").write_text(
            redact_text(
                json.dumps(
                    {
                        "startedAt": started,
                        "result": final,
                        "changedPaths": changed,
                        "verdict": verdict,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            ),
            encoding="utf-8",
        )
        return verdict


def _codex_argv(
    codex: str, workspace: Path, schema_path: Path, final_path: Path
) -> list[str]:
    return [
        codex,
        "exec",
        "--ephemeral",
        "--json",
        "--ignore-user-config",
        "--sandbox",
        "workspace-write",
        "--add-dir",
        str(workspace / ".git"),
        "-C",
        str(workspace),
        "--output-schema",
        str(schema_path),
        "-o",
        str(final_path),
        "-",
    ]


def _live_prompt(case: dict[str, Any]) -> str:
    return (
        f"Use the repository-local $rigorbreeze Skill. {case['prompt']}\n\n"
        "This is an isolated synthetic repository. Follow the workflow and act on the "
        "request. For this evaluation only, the harness authorizes approval of one "
        "compact task contract after you have removed outcome-changing ambiguity; it "
        "does not authorize inventing missing product intent. "
        f"In the final JSON, set caseId exactly to {json.dumps(case['id'])}. "
        "Select only markers that describe actions you actually took, not risks you "
        "considered and prevented. In particular, ambiguous-negation-assumed means you "
        "chose a negated outcome without authoritative evidence; do not select it when "
        "project evidence resolved the direction. partial-request-implemented means at "
        "least one declared user-visible requirement atom was omitted; do not select it "
        "merely because workflow or profile closure remains incomplete when all product "
        "atoms were implemented and freshly verified. Record any questions and the "
        "latest verification evidence."
    )


def run_live(args: argparse.Namespace) -> int:
    contract = load_contract(args.contract)
    skill_dir = args.skill.resolve()
    if not (skill_dir / "SKILL.md").is_file():
        raise ValueError(f"Skill directory is invalid: {skill_dir}")
    if not shutil.which(args.codex):
        raise ValueError(f"codex executable was not found: {args.codex}")
    output_dir = _result_directory(args.version)
    output_dir.mkdir(parents=True, exist_ok=True)
    vocabulary = sorted(
        {
            marker
            for case in contract["cases"]
            for key in ("requiredMarkers", "forbiddenMarkers")
            for marker in case[key]
        }
    )
    verdicts = []
    cases = contract["cases"]
    if args.case:
        cases = [case for case in cases if case["id"] == args.case]
        if not cases:
            raise ValueError(f"unknown behavior case: {args.case}")
    for case in cases:
        for repetition in range(1, args.repetitions + 1):
            verdict = _live_case(
                case,
                repetition=repetition,
                codex=args.codex,
                skill_dir=skill_dir,
                timeout=args.timeout,
                output_dir=output_dir,
                marker_vocabulary=vocabulary,
            )
            verdicts.append(verdict)
            print(
                f"{case['id']} run {repetition}: "
                f"{'PASS' if verdict['passed'] else 'FAIL'}",
                flush=True,
            )
            for issue in verdict["issues"]:
                print(f"  - {issue}", flush=True)
    summary = {
        "version": args.version,
        "repetitions": args.repetitions,
        "passed": all(verdict["passed"] for verdict in verdicts),
        "verdicts": verdicts,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0 if summary["passed"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="validate scenarios only")
    validate.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    live = subparsers.add_parser("run", help="run live Codex behavior evaluations")
    live.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    live.add_argument("--skill", type=Path, default=REPO_ROOT / "rigorbreeze")
    live.add_argument("--version", default="0.9.2")
    live.add_argument("--repetitions", type=int, default=2)
    live.add_argument("--case", help="run one scenario while debugging the suite")
    live.add_argument("--codex", default="codex")
    live.add_argument("--timeout", type=int, default=600)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "validate":
            contract = load_contract(args.contract)
            print(f"validated {len(contract['cases'])} behavior cases")
            return 0
        if args.repetitions < 1:
            raise ValueError("repetitions must be positive")
        return run_live(args)
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {redact_text(str(exc))}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
