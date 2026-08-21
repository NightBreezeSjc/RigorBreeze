#!/usr/bin/env python3
"""Run one build command with a disposable synthetic RSA pair."""

from __future__ import annotations

import argparse
import base64
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def run_checked(command: list[str], cwd: Path) -> None:
    result = subprocess.run(command, cwd=cwd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"openssl failed with exit {result.returncode}")


def build_pair(openssl: str, directory: Path) -> tuple[str, str]:
    private_pem = directory / "private.pem"
    private_der = directory / "private.der"
    public_der = directory / "public.der"
    run_checked(
        [
            openssl,
            "genpkey",
            "-algorithm",
            "RSA",
            "-pkeyopt",
            "rsa_keygen_bits:2048",
            "-out",
            str(private_pem),
        ],
        directory,
    )
    run_checked(
        [
            openssl,
            "pkcs8",
            "-topk8",
            "-nocrypt",
            "-in",
            str(private_pem),
            "-outform",
            "DER",
            "-out",
            str(private_der),
        ],
        directory,
    )
    run_checked(
        [
            openssl,
            "pkey",
            "-in",
            str(private_pem),
            "-pubout",
            "-outform",
            "DER",
            "-out",
            str(public_der),
        ],
        directory,
    )
    return (
        base64.b64encode(public_der.read_bytes()).decode("ascii"),
        base64.b64encode(private_der.read_bytes()).decode("ascii"),
    )


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Inject a temporary synthetic RSA pair into one build command"
    )
    value.add_argument("--public-env", required=True)
    value.add_argument("--private-env", required=True)
    value.add_argument("--timeout", type=int, default=1200)
    value.add_argument("command", nargs=argparse.REMAINDER)
    return value


def redact_keys(text: str | None, values: tuple[str, str]) -> str:
    result = text or ""
    for value in values:
        result = result.replace(value, "[REDACTED_SYNTHETIC_RSA]")
    return result


def main() -> int:
    args = parser().parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        print("ERROR: a build command is required", file=sys.stderr)
        return 2
    if args.timeout <= 0:
        print("ERROR: timeout must be positive", file=sys.stderr)
        return 2
    if (
        not ENV_NAME.fullmatch(args.public_env)
        or not ENV_NAME.fullmatch(args.private_env)
        or args.public_env == args.private_env
    ):
        print(
            "ERROR: RSA environment names must be distinct valid identifiers",
            file=sys.stderr,
        )
        return 2
    openssl = shutil.which("openssl")
    if not openssl:
        print(
            "ERROR: openssl is required for the synthetic RSA build adapter",
            file=sys.stderr,
        )
        return 2
    try:
        with tempfile.TemporaryDirectory(prefix="rigorbreeze-rsa-") as temporary:
            directory = Path(temporary)
            public_key, private_key = build_pair(openssl, directory)
            environment = {
                **os.environ,
                args.public_env: public_key,
                args.private_env: private_key,
                "RIGORBREEZE_SYNTHETIC_RSA": "build-only",
                "RIGORBREEZE_SYNTHETIC_RSA_DIR": str(directory),
            }
            try:
                result = subprocess.run(
                    command,
                    env=environment,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    capture_output=True,
                    timeout=args.timeout,
                )
            except subprocess.TimeoutExpired as exc:
                output = redact_keys(
                    "\n".join(
                        part
                        for part in (
                            exc.stdout.decode("utf-8", errors="replace")
                            if isinstance(exc.stdout, bytes)
                            else exc.stdout,
                            exc.stderr.decode("utf-8", errors="replace")
                            if isinstance(exc.stderr, bytes)
                            else exc.stderr,
                        )
                        if part
                    ),
                    (public_key, private_key),
                )
                if output:
                    print(output, file=sys.stderr)
                print(
                    f"synthetic-build-only: command timed out after {args.timeout} seconds",
                    file=sys.stderr,
                )
                return 124
    except (OSError, RuntimeError) as exc:
        print(f"ERROR: unable to prepare synthetic RSA: {exc}", file=sys.stderr)
        return 2
    stdout = redact_keys(result.stdout, (public_key, private_key))
    stderr = redact_keys(result.stderr, (public_key, private_key))
    if stdout:
        print(stdout, end="" if stdout.endswith("\n") else "\n")
    if stderr:
        print(stderr, end="" if stderr.endswith("\n") else "\n", file=sys.stderr)
    stream = sys.stdout if result.returncode == 0 else sys.stderr
    print(
        f"synthetic-build-only: command exited {result.returncode}; "
        "not runtime, acceptance, deployment, or release evidence",
        file=stream,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
