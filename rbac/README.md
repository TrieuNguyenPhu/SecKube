# RBAC Lab

The `rbac` ArgoCD Application creates three GitOps-managed identities:

- `alice`: CRUD for Deployments, Pods, and Services only in `demo`.
- `bob`: manage Pods cluster-wide.
- `carol`: read-only access cluster-wide.

Verify after ArgoCD reports `rbac` as `Synced/Healthy`:

```powershell
kubectl auth can-i create deployment -n demo --as alice
kubectl auth can-i create deployment -n kube-system --as alice
kubectl auth can-i get pods -A --as bob
kubectl auth can-i delete nodes --as carol
```

Expected results: `yes`, `no`, `yes`, `no`.
