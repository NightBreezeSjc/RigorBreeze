# Security Policy

English · [简体中文](SECURITY.zh-CN.md)

## Supported versions

RigorBreeze is currently in Public Preview. Security fixes target the latest published `0.x` release and the default branch. Older preview releases may require upgrading rather than receiving a backport.

## Report a vulnerability privately

Use [GitHub private vulnerability reporting](https://github.com/nightbreezesjc/rigorbreeze/security/advisories/new) to report vulnerabilities.

Do not open a public issue containing:

- secrets, credentials, tokens, or private repository data;
- a working exploit or bypass instructions;
- sensitive task evidence, automation-journal contents, or production logs;
- details that could enable unauthorized commit, push, merge, release, migration, or cleanup actions.

Include the affected version or commit, reproduction conditions, expected security boundary, actual behavior, and the smallest safe evidence you can provide. Remove real secrets and personal or production data.

The maintainer will acknowledge the report, reproduce it, assess affected versions, and coordinate a fix and disclosure through the private advisory. Response times are best effort while the project is maintained by one person; the advisory will remain the source of status.

## Security boundaries

The Skill orchestrates project-configured tools but does not replace secret scanning, dependency analysis, SAST, migration rehearsal, protected branches, environment approval, monitoring, or professional security review. AI output is not a security approval.

If you discover that a gate permits a secret, privilege bypass, destructive migration, stale proof, unauthorized external action, or wrong release, treat it as an immediate core review rather than waiting for the ordinary repeated-friction threshold.
