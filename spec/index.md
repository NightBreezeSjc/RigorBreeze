# Production Spec Index

This tree keeps one human-authored Markdown file per active change. Machine state and evidence are JSON.

Authority order:

1. Approved business requirements and design source
2. `changes/<TASK-ID>.md`
3. API/data/security contracts
4. Automated tests and runtime evidence
5. Code and artifacts
6. `archive/` history

Do not copy requirement bodies into multiple files. Move a completed task to `archive/`; do not duplicate it.
