# Architecture

## System flow

```text
Git push -> GitHub Actions -> GHCR image + manifest update
    |                              |
    +--------------------------> Argo CD
                                   |
              namespaces -> controllers/monitoring -> policy -> API Rollout
                                                            |
                         Service -> Flask API -> /metrics -> Prometheus
                                                   |             |
                                      Rollout analysis <---------+
                                                                 |
                                                     Alertmanager -> email
```

## Components

- **Root Application:** `argocd/root.yaml` discovers child Applications.
- **Platform Applications:** install Argo Rollouts and kube-prometheus-stack.
- **Policy Applications:** install the canary AnalysisTemplate and SLO rules.
- **API Application:** installs one Rollout, one Service and one ServiceMonitor.
- **API container:** exposes business response, health and metrics endpoints.

Argo CD establishes dependencies through sync waves: shared namespace first, platform controllers second, policy resources third, workload last. The Service selects both stable and canary pods, so traffic weighting is replica-based rather than managed by an ingress/service-mesh router.

## External dependencies

GitHub/GHCR provide source and images; Kubernetes provides scheduling/networking; Gmail SMTP delivers alerts. The cluster must be able to read both the Git repository and container package.
