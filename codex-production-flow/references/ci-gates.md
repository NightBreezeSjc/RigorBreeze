# CI Gate Integration

## Principle

Keep policy in repository scripts and call the same scripts locally and in CI. CI configuration orchestrates jobs; it must not become a second workflow specification.

## Minimum pipeline

```text
policy/status
→ static and type checks
→ unit and integration tests
→ API/permission/data contracts
→ secret/dependency/SBOM/license checks
→ migration rehearsal
→ production build
→ E2E and visual/runtime acceptance
→ artifact digest
→ release gate
```

Use risk-based rules to skip only demonstrably irrelevant jobs. Record every skip as `N/A` with a reason. Required failures block merge and release.

## GitLab

Adapt `assets/ci/gitlab-ci.yml` into the existing `.gitlab-ci.yml`. Replace placeholder project commands with repository-owned commands. Preserve artifacts for test reports, screenshots, migration logs, SBOM, and artifact digests.

Use protected branches/environments, required pipelines, environment-scoped secrets, and manual production approval. Do not place credentials in YAML.

## GitHub Actions

Adapt `assets/ci/github-actions.yml` into `.github/workflows/production-flow.yml`. Configure required status checks and protected environments. Use OIDC or repository/environment secrets; do not embed tokens.

## Artifact identity

Build once and promote the same immutable artifact. Record Git SHA, dependency lock digest, configuration version, migration set, image/package digest, CI run, and release observation. Rebuilding separately for production breaks the evidence chain.

