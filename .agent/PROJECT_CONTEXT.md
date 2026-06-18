# Project Context

## Purpose

SecKube is a small GitOps reference project for observable canary delivery on Kubernetes. It demonstrates how a release is built, reconciled by Argo CD, evaluated by Argo Rollouts against Prometheus data, and reported through Alertmanager.

## Stable scope

- One stateless HTTP API in namespace `demo`.
- Argo CD owns deployment reconciliation from the `main` branch.
- Argo Rollouts owns progressive delivery.
- kube-prometheus-stack owns metrics and alert delivery.
- GitHub Actions validates manifests and publishes the API image.
- Gmail credentials are a local Kubernetes Secret, never a GitOps resource.

## Sources of truth

- Runtime behavior: `src/api/`
- Workload and observability contracts: `app-*/`
- Desired cluster composition: `argocd/`
- Build/release behavior: `.github/workflows/`
- Operator instructions: `README.md`

Chart versions, image tags, replica counts and resource limits are intentionally omitted here; read their manifests when current values matter.
