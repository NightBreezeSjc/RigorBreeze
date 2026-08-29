# {{PROJECT}} Verification Pack

This tracked pack teaches an Agent how to prove the real product. Create it only
through an explicit verification-enablement task. Seed three to five critical or
frequently changed features; add another feature only when it earns durable live
coverage.

## Launch

- Command: `{{LAUNCH_ARGV}}`
- Ready signal: `{{READY_SIGNAL}}`
- Owned process, port, simulator, account, and test-data boundary: `{{OWNERSHIP}}`

## Doctor

Run `{{DOCTOR_ARGV}}` before the first drive and after surprising behavior. It
must prove the expected build/SHA, process, environment, authentication, and
exclusive runtime resources. A failed Doctor means do not drive this instance.

## Drive

Use the recipes under `features/`. Follow the user-visible entry, exercise the
named states, and observe the actual result. Compilation, source search, cached
screenshots, and another Agent's claim are not live proof.

## Evidence

Write reports, screenshots, traces, and logs under ignored `reports/`. Preserve
evidence before cleanup. Generate `reports/rigorbreeze-verification.json` using
Verification Report schema v1 and the current Git HEAD.

Feature Map digest algorithm: SHA-256 over `verification/README.md` followed by
sorted `verification/features/*.md`; for each file hash UTF-8 relative path,
NUL, file bytes, NUL.

## Cleanup

Run `{{CLEANUP_ARGV}}` after success, failure, and timeout. Remove only resources
owned by this drive. Confirm evidence still exists and report cleanup as passed.

