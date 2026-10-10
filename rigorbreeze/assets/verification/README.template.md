# {{PROJECT}} Verification Pack

This tracked pack teaches an Agent how to prove the real product. Create it only
through an explicit verification-enablement task. Seed three to five critical or
frequently changed features; add another feature only when it earns durable live
coverage.

## Launch

- Command: `{{LAUNCH_ARGV}}`
- Ready signal: `{{READY_SIGNAL}}`
- Owned process, port, simulator, account, and test-data boundary: `{{OWNERSHIP}}`

## Prepare

- Command: `{{PREPARE_ARGV}}`
- Create only owned synthetic accounts, roles, permissions, and test data.
- Record stable identifiers needed by Drive and Cleanup; never copy production
  secrets or create data that cannot be safely removed.

## Doctor

Run `{{DOCTOR_ARGV}}` before the first drive and after surprising behavior. It
must prove the expected build/SHA, process, environment, authentication, and
exclusive runtime resources. A failed Doctor means do not drive this instance.

## Drive

Use the recipes under `features/`. Follow the user-visible entry, exercise the
named states, and observe the actual result. Compilation, source search, cached
screenshots, and another Agent's claim are not live proof.

## Inspect

Use `{{INSPECT_ARGV}}` only for bounded read-only database, log, or Trace
inspection. Apply an explicit row limit and timeout, redact secrets and personal
data, and keep the query or filter with the evidence. Inspection explains what
happened; it never changes the authoritative acceptance oracle.

## Evidence

Write reports, screenshots, traces, and logs under ignored `reports/`. Preserve
evidence before cleanup. Generate `reports/rigorbreeze-verification.json` using
Verification Report schema v1 and the current Git HEAD. The expected result
comes from the approved contract or explicit user correction, not from the
observed system response.

Feature Map digest algorithm: SHA-256 over `verification/README.md` followed by
sorted `verification/features/*.md`; for each file hash UTF-8 relative path,
NUL, file bytes, NUL.

## Cleanup / Reset

Run `{{CLEANUP_ARGV}}` after success, failure, and timeout, then use
`{{RESET_ARGV}}` only when the owned environment must return to its known
baseline. Remove only resources created by Prepare or Drive. Confirm evidence
still exists; failed cleanup or reset blocks a passing verification report.
