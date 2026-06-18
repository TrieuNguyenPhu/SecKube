# AI Notes

Read `PROJECT_CONTEXT.md` first, then inspect only the source-of-truth area relevant to the task.

## Guardrails

- Never read, print, stage or rewrite `app-alert/email-secret.yaml`; use the committed `.example` only.
- Preserve the current repository URL and lowercase GHCR image path unless the Git remote changes.
- Use PowerShell syntax for operator-facing Windows commands. Commands executed inside Linux containers or GitHub Actions remain POSIX shell.
- Treat image tag and `VERSION` as release-workflow-owned fields. `ERROR_RATE` is safe to change for a demo.
- Keep namespace/name coupling aligned across Rollout, Service, ServiceMonitor, PromQL and Alertmanager Secret references.
- Do not remove sync ordering without replacing its dependency guarantees.

## Validation checklist

1. Search for stale repository/image coordinates and accidental secret files.
2. Validate YAML plus Kubernetes schemas where the required CRDs are available.
3. Confirm the ServiceMonitor propagates labels used by PromQL.
4. Confirm the analysis query and SLO rule select the same workload.
5. Review `git diff` and ensure only intended files changed.

## Known behavior

- Error injection is random, so short tests fluctuate.
- Analysis needs request traffic; with no samples, the success-rate query may have no usable result.
- Canary traffic share is approximate because it follows pod replica proportions.
- Private GitHub repositories or GHCR packages require cluster credentials not defined in this repo.
