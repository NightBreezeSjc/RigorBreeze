# {{FEATURE_ID}} — {{USER_OUTCOME}}

## Sub-features

- {{STATE_OR_SUBFLOW_TO_COVER}}

## How to get to it (user POV)

- Role/account/data: {{PRECONDITIONS}}
- Route/menu/device: {{ENTRY_PATH}}

## Authoritative acceptance oracle

- Source and acceptance ID: {{AUTHORITATIVE_SOURCE_AND_ID}}
- Expected end state: {{EXPECTED_END_STATE}}
- Must remain absent: {{FORBIDDEN_RESULT}}

## Operational readiness matrix

Use only `passed | pending | blocked | not-applicable` and attach a resolvable
reference for every non-N/A row.

| Dimension | Status | Evidence or blocker |
|---|---|---|
| Code implemented | {{CODE_STATUS}} | {{CODE_REFERENCE}} |
| Configuration saved | {{CONFIG_SAVED_STATUS}} | {{CONFIG_SAVED_REFERENCE}} |
| Configuration published | {{CONFIG_PUBLISHED_STATUS}} | {{CONFIG_PUBLISHED_REFERENCE}} |
| Credential/provider ready | {{PROVIDER_STATUS}} | {{PROVIDER_REFERENCE}} |
| User entry visible | {{ENTRY_STATUS}} | {{ENTRY_REFERENCE}} |
| Local/test runtime verified | {{RUNTIME_STATUS}} | {{RUNTIME_REFERENCE}} |
| Real-provider/production UAT | {{UAT_STATUS}} | {{UAT_REFERENCE}} |

## Driving it with {{HARNESS}}

1. {{DETERMINISTIC_USER_ACTION}}
2. {{OBSERVATION_OR_FAILURE_STATE}}

## Observation channels and limits

- Product surface: {{UI_API_DEVICE_OR_CLI}}
- Read-only database/log/Trace inspection: {{BOUNDED_INSPECTION}}
- Row limit, timeout, and redaction: {{INSPECTION_LIMITS}}

## Observed result and honest gaps

- Observed result: {{REAL_END_STATE}}
- Evidence: `reports/{{FEATURE_ID}}.{{EXT}}`
- Not proved here: {{HONEST_LIMIT}}
