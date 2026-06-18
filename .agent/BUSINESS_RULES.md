# Business Rules

1. A release progresses through increasing canary weights before full promotion.
2. Canary analysis accepts an observed HTTP success rate of at least 90%; repeated failures stop or roll back the release.
3. The operational SLO is stricter than the release gate: a five-minute success rate below 95% for two minutes raises a critical alert.
4. HTTP 5xx responses are failures; other observed HTTP statuses count as successful requests.
5. Health checks always succeed independently of injected business-request failures, allowing analysis—not probe restarts—to decide release health.
6. `ERROR_RATE` exists only to create demo failure scenarios and is probabilistic.
7. Git is authoritative for declarative resources. Argo CD self-heals drift and prunes removed resources.
8. Email credentials are deliberately outside Git. They must be applied manually to the `monitoring` namespace under the expected Secret name and key.

Thresholds are part of the demo policy; if changed, keep the AnalysisTemplate, PrometheusRule, README and tests conceptually aligned.
