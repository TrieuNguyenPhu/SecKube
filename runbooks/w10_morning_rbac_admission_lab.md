# W10 Morning Lab - RBAC + Gatekeeper

Tai lieu nay ghi lai phan da lam cho bai lab trong `w10_morning_rbac_admission.html`, cach sync qua ArgoCD, cach test va cach chup evidence.

## 1. Yeu cau lab

- RBAC qua GitOps:
  - `alice`: developer, CRUD workload chi trong namespace `demo`.
  - `bob`: SRE, xem va thao tac Pod tren toan cluster.
  - `carol`: viewer, chi doc toan cluster.
- Admission Policy qua OPA Gatekeeper:
  - Chan image tag `:latest`.
  - Bat buoc container co `resources.limits.cpu` va `resources.limits.memory`.
  - Chan `runAsUser: 0`.
  - Chan `hostNetwork: true`.
- Custom policy:
  - Reject `Deployment`/`Rollout` neu `replicas > 5`.

## 2. Cac file da them/sua

- `rbac/roles.yaml`: 1 `Role` cho developer trong `demo`, 2 `ClusterRole` cho SRE va viewer.
- `rbac/rolebindings.yaml`: bind `alice`, `bob`, `carol` vao dung role.
- `argocd/apps/rbac.yaml`: ArgoCD app sync thu muc `rbac/`.
- `argocd/apps/gatekeeper.yaml`: cai Gatekeeper controller bang Helm chart.
- `argocd/apps/gatekeeper-templates.yaml`: sync `gatekeeper/templates/`.
- `argocd/apps/gatekeeper-constraints.yaml`: sync `gatekeeper/constraints/`.
- `gatekeeper/templates/`: 5 `ConstraintTemplate`, trong do `k8smaxreplicas` la custom policy.
- `gatekeeper/constraints/`: 4 constraint bat buoc cua lab va 1 custom constraint.
- `app-api/rollout.yaml`: them `securityContext` non-root UID/GID `10001` de platform khong bi policy root user chan.
- `lab-tests/admission/`: manifest dung de test reject/pass.

## 3. Deploy qua GitOps

Truoc khi sync, neu dung fork rieng thi sua tat ca `repoURL: https://github.com/TrieuNguyenPhu/SecKube.git` trong `argocd/root.yaml` va `argocd/apps/*.yaml` sang repo cua ban.

```powershell
git add .
git commit -m "feat: add rbac and gatekeeper admission policies"
git push origin main
```

Neu chua co root app:

```powershell
kubectl apply -f argocd/root.yaml
```

Cho cac app xanh:

```powershell
kubectl -n argocd get applications
kubectl -n gatekeeper-system rollout status deploy/gatekeeper-controller-manager
kubectl get constrainttemplates
kubectl get k8sdisallowedtags,k8srequiredresourcelimits,k8sdisallowedrunasuser,k8sdisallowedhostnetwork,k8smaxreplicas
kubectl -n demo get rollout api
```

Evidence nen chup:

- ArgoCD UI: `root`, `gatekeeper`, `gatekeeper-templates`, `gatekeeper-constraints`, `rbac`, `api` deu `Synced/Healthy`.
- Terminal output cua 4 lenh tren.

## 4. Test RBAC

Chay dung 4 lenh nghiem thu trong slide:

```powershell
kubectl auth can-i create deploy -n demo --as alice
kubectl auth can-i create deploy -n kube-system --as alice
kubectl auth can-i get pods -A --as bob
kubectl auth can-i delete nodes --as carol
```

Ket qua mong doi:

```text
yes
no
yes
no
```

Luu evidence bang PowerShell:

```powershell
New-Item -ItemType Directory -Force evidence | Out-Null
kubectl auth can-i create deploy -n demo --as alice        | Tee-Object evidence/rbac-01-alice-demo.txt
kubectl auth can-i create deploy -n kube-system --as alice | Tee-Object evidence/rbac-02-alice-kubesystem.txt
kubectl auth can-i get pods -A --as bob                    | Tee-Object evidence/rbac-03-bob-pods.txt
kubectl auth can-i delete nodes --as carol                 | Tee-Object evidence/rbac-04-carol-nodes.txt
```

## 5. Test Gatekeeper

Dung `--dry-run=server` de API server va Gatekeeper validate manifest nhung khong tao resource that:

```powershell
kubectl apply --dry-run=server -f lab-tests/admission/bad-latest-tag.yaml
kubectl apply --dry-run=server -f lab-tests/admission/bad-no-limits.yaml
kubectl apply --dry-run=server -f lab-tests/admission/bad-root-user.yaml
kubectl apply --dry-run=server -f lab-tests/admission/bad-hostnetwork.yaml
kubectl apply --dry-run=server -f lab-tests/admission/good-pod.yaml
```

Ket qua mong doi:

- 4 file `bad-*` dau bi `Error from server (Forbidden)` va co message cua Gatekeeper.
- `good-pod.yaml` tra ve `pod/good-policy-pod created (server dry run)`.

Luu evidence:

```powershell
kubectl apply --dry-run=server -f lab-tests/admission/bad-latest-tag.yaml 2>&1 | Tee-Object evidence/gk-01-latest.txt
kubectl apply --dry-run=server -f lab-tests/admission/bad-no-limits.yaml 2>&1 | Tee-Object evidence/gk-02-limits.txt
kubectl apply --dry-run=server -f lab-tests/admission/bad-root-user.yaml 2>&1 | Tee-Object evidence/gk-03-root.txt
kubectl apply --dry-run=server -f lab-tests/admission/bad-hostnetwork.yaml 2>&1 | Tee-Object evidence/gk-04-hostnetwork.txt
kubectl apply --dry-run=server -f lab-tests/admission/good-pod.yaml 2>&1 | Tee-Object evidence/gk-05-good-pod.txt
```

## 6. Test custom policy

```powershell
kubectl apply --dry-run=server -f lab-tests/admission/bad-too-many-replicas.yaml
kubectl apply --dry-run=server -f lab-tests/admission/good-deployment.yaml
```

Ket qua mong doi:

- `bad-too-many-replicas.yaml` bi reject vi `replicas: 6`.
- `good-deployment.yaml` pass vi `replicas: 5`.

Luu evidence:

```powershell
kubectl apply --dry-run=server -f lab-tests/admission/bad-too-many-replicas.yaml 2>&1 | Tee-Object evidence/gk-06-max-replicas-reject.txt
kubectl apply --dry-run=server -f lab-tests/admission/good-deployment.yaml 2>&1 | Tee-Object evidence/gk-07-max-replicas-pass.txt
```

## 7. Chup anh evidence

- Terminal: chay cac lenh test, bam `Win + Shift + S`, khoanh vung output va luu vao `evidence/`.
- ArgoCD UI: port-forward neu can:

```powershell
kubectl -n argocd port-forward svc/argocd-server 8080:443
```

Mo `https://localhost:8080`, chup man hinh Applications list va tung app Gatekeeper/RBAC neu can.

Checklist evidence toi thieu:

- `evidence/rbac-*.txt` hoac anh terminal co 4 ket qua `yes/no/yes/no`.
- `evidence/gk-01` den `gk-05`: 4 reject va 1 pass.
- `evidence/gk-06` den `gk-07`: custom policy reject/pass.
- Anh ArgoCD cac app `Synced/Healthy`.
- Anh/terminal lenh `kubectl get k8sdisallowedtags,k8srequiredresourcelimits,k8sdisallowedrunasuser,k8sdisallowedhostnetwork,k8smaxreplicas` hien 5 constraints.
