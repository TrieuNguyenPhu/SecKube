# Gatekeeper Lab

Gatekeeper is installed by ArgoCD with Helm chart `3.22.2`. Policies are managed by the separate `gatekeeper-policies` Application so templates are synced before constraints.

The four standard ConstraintTemplates are copied from `open-policy-agent/gatekeeper-library` commit `643be816e2e9aa2f0371101c3b7aa34b3a995c55`:

- `K8sDisallowedTags`: rejects `:latest` and untagged images.
- `K8sContainerLimits`: requires CPU and memory limits.
- `K8sPSPAllowedUsers`: requires non-root Pods.
- `K8sPSPHostNetworkingPorts`: rejects `hostNetwork: true`.

The custom `K8sRequiredOwner` template requires `metadata.labels.owner` on workloads. Constraints are scoped to namespace `demo` to avoid disrupting cluster infrastructure.

## Audit before deny

Start with `enforcementAction: warn`, then inspect:

```powershell
kubectl get constraints
kubectl get k8sdisallowedtags disallow-latest -o yaml
kubectl get k8scontainerlimits require-container-limits -o yaml
kubectl get k8spspallowedusers require-non-root -o yaml
kubectl get k8spsphostnetworkingports disallow-host-network -o yaml
kubectl get k8srequiredowner require-owner -o yaml
```

After existing workloads are compliant, change every constraint to `enforcementAction: deny`, commit, push, and wait for ArgoCD sync.

## Admission tests

Each violating manifest must be rejected; the valid manifest must pass:

```powershell
kubectl apply --dry-run=server -f .\gatekeeper\tests\latest.yaml
kubectl apply --dry-run=server -f .\gatekeeper\tests\missing-limits.yaml
kubectl apply --dry-run=server -f .\gatekeeper\tests\root-user.yaml
kubectl apply --dry-run=server -f .\gatekeeper\tests\host-network.yaml
kubectl apply --dry-run=server -f .\gatekeeper\tests\missing-owner.yaml
kubectl apply --dry-run=server -f .\gatekeeper\tests\valid.yaml
```
