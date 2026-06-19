# SecKube

SecKube là repo lab GitOps cho Kubernetes security và progressive delivery. Repo dùng Argo CD App of Apps để cài đặt hạ tầng, deploy API bằng Argo Rollouts, kiểm tra canary bằng Prometheus, áp dụng RBAC/Gatekeeper policy, đồng bộ secret qua External Secrets Operator, và enforce image đã ký bằng Sigstore policy-controller.

## Nội Dung Chính

- Progressive delivery cho Flask API với Argo Rollouts.
- Automated analysis bằng Prometheus query.
- Runtime alerting bằng PrometheusRule và Alertmanager.
- RBAC cho các user lab: `alice`, `bob`, `carol`.
- OPA Gatekeeper admission policies cho workload security.
- External Secrets Operator đồng bộ secret từ AWS Secrets Manager.
- Trivy scan và Cosign signing trong GitHub Actions.
- Sigstore `ClusterImagePolicy` yêu cầu image API có chữ ký hợp lệ.

## Yêu Cầu

- Docker Desktop
- `kubectl`
- `minikube`
- `git`
- GitHub repository có quyền push package lên GHCR
- Cosign, nếu cần verify image local:

```powershell
cosign version
```

## Cấu Trúc Repo

```text
.
|-- .github/workflows/
|   |-- build-push.yml          # Build, scan, push, sign image và bump rollout tag
|   `-- validate.yml            # Validate Kubernetes manifests bằng kubeconform
|-- app-api/                    # Rollout, Service, ServiceMonitor của API
|-- app-analysis/               # AnalysisTemplate cho canary validation
|-- app-alert/                  # PrometheusRule và hướng dẫn email alert
|-- app-common/                 # Namespace và resource dùng chung
|-- argocd/
|   |-- apps/                   # Argo CD child Applications
|   `-- root.yaml               # App of Apps root
|-- doc/                        # Slide/đề bài lab gốc
|-- eso/                        # SecretStore và ExternalSecret
|-- evidence/                   # Evidence lab đã commit khi cần nộp bài
|-- gatekeeper/
|   |-- constraints/            # Gatekeeper constraints
|   `-- templates/              # ConstraintTemplates
|-- lab-tests/admission/        # Manifest test admission policy
|-- policies/                   # Sigstore ClusterImagePolicy
|-- rbac/                       # Roles và RoleBindings lab
|-- runbooks/                   # Hướng dẫn thực hiện, test và nộp evidence
|-- signing/                    # Public key dùng để verify Cosign signature
`-- src/api/                    # Flask API source và Dockerfile
```

## Quick Start

### 1. Tạo cluster

```powershell
minikube start -p w10 --driver=docker
kubectl config use-context w10
```

### 2. Cài Argo CD

```powershell
kubectl create ns argocd
kubectl apply --server-side -n argocd `
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl -n argocd rollout status deploy/argocd-server
```

Lấy password Argo CD:

```powershell
$pwd64 = kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}"
[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($pwd64))
```

Port-forward UI:

```powershell
kubectl -n argocd port-forward svc/argocd-server 8080:443
```

Mở `https://localhost:8080`, user mặc định là `admin`.

### 3. Deploy App of Apps

```powershell
kubectl apply -f argocd/root.yaml
```

Kiểm tra các app:

```powershell
kubectl get applications -n argocd
```

## Cấu Hình Bắt Buộc Trước Khi Chạy Full Lab

### Image API

Workflow `.github/workflows/build-push.yml` sẽ build image từ `src/api`, scan bằng Trivy, push lên GHCR, ký image bằng Cosign, rồi update `app-api/rollout.yaml`.

Nếu dùng fork/repo riêng, cần sửa:

- `env.IMAGE_NAME` trong `.github/workflows/build-push.yml`
- `repoURL` trong `argocd/root.yaml` và `argocd/apps/*.yaml`
- Image trong `app-api/rollout.yaml`
- Glob image trong `policies/cluster-image-policy.yaml`

### GitHub Secrets Cho Cosign

Thêm 2 repository secrets trong GitHub:

- `COSIGN_PRIVATE_KEY`: toàn bộ nội dung `.lab-local/cosign.key`
- `COSIGN_PASSWORD`: nội dung `.lab-local/cosign-password.txt`

Copy nhanh bằng PowerShell:

```powershell
Get-Content .\.lab-local\cosign.key -Raw | Set-Clipboard
Get-Content .\.lab-local\cosign-password.txt -Raw | Set-Clipboard
```

Khi paste private key, giữ nguyên cả dòng `BEGIN` và `END`.

### Secret Cho Alertmanager

Làm theo hướng dẫn trong [app-alert/README.md](app-alert/README.md).

### Secret Cho ESO

Lab 2 dùng AWS Secrets Manager key `demo/db` và Kubernetes secret `aws-creds` trong namespace `demo`. Chi tiết nằm trong [runbooks/lab2-implementation-log.md](runbooks/lab2-implementation-log.md).

## GitOps Applications

Thứ tự sync chính:

- Wave `-2`: `gatekeeper`, `external-secrets`, `policy-controller`
- Wave `-1`: `common`, `eso-config`, `policies`
- Wave `0`: `kube-prometheus-stack`, `argo-rollouts`, `gatekeeper-templates`
- Wave `1`: `analysis`, `alert`, `rbac`, `gatekeeper-constraints`
- Wave `2`: `api`

Kiểm tra nhanh:

```powershell
kubectl get applications -n argocd
kubectl get pods -n demo
kubectl get pods -n monitoring
kubectl get pods -n gatekeeper-system
kubectl get pods -n external-secrets
kubectl get pods -n cosign-system
```

## Verify Deployment

### API Rollout

```powershell
kubectl get rollout api -n demo
kubectl get rollout api -n demo -w
kubectl get pods -n demo -l app=api
```

### AnalysisRun

```powershell
kubectl get analysisrun -n demo
kubectl describe analysisrun -n demo <name>
```

### Prometheus Query

```powershell
kubectl run test-query --image=curlimages/curl:latest --rm -i --restart=Never -n monitoring -- `
  curl -s 'http://kube-prometheus-stack-prometheus.monitoring.svc:9090/api/v1/query?query=api:success_rate:5m'
```

### RBAC Và Gatekeeper

```powershell
kubectl auth can-i create deploy -n demo --as alice
kubectl auth can-i create deploy -n kube-system --as alice
kubectl auth can-i get pods -A --as bob
kubectl auth can-i delete nodes --as carol

kubectl apply --dry-run=server -f lab-tests/admission/bad-latest-tag.yaml
kubectl apply --dry-run=server -f lab-tests/admission/good-pod.yaml
```

Chi tiết Lab 1: [runbooks/w10_morning_rbac_admission_lab.md](runbooks/w10_morning_rbac_admission_lab.md).

### ESO

```powershell
kubectl get secretstore,externalsecret -n demo
kubectl -n demo get secret db-secret
```

### Cosign Verify

```powershell
cosign verify `
  --key .\signing\cosign.pub `
  ghcr.io/trieunguyenphu/w10-api:<SIGNED_TAG>
```

## Test Canary Scenarios

Sửa `ERROR_RATE` trong `app-api/rollout.yaml`, commit và push để Argo CD sync lại:

```powershell
git add app-api/rollout.yaml
git commit -m "test: adjust api error rate"
git push origin main
```

Giá trị gợi ý:

- `ERROR_RATE: "0"`: rollout nên pass.
- `ERROR_RATE: "0.10"`: canary có thể pass ngưỡng 90%, nhưng SLO 95% có thể alert.
- `ERROR_RATE: "0.15"`: analysis nên fail và rollout rollback.

## Runbooks

- [runbooks/w10_morning_rbac_admission_lab.md](runbooks/w10_morning_rbac_admission_lab.md): Lab 1 RBAC + Gatekeeper.
- [runbooks/lab2-implementation-log.md](runbooks/lab2-implementation-log.md): log triển khai ESO + supply chain.
- [runbooks/lab2-test-and-evidence.md](runbooks/lab2-test-and-evidence.md): checklist test và evidence.
- [runbooks/lab2-cve-exception-adr.md](runbooks/lab2-cve-exception-adr.md): quy trình exception CVE có thời hạn.

## Cleanup

```powershell
kubectl delete -f argocd/root.yaml
kubectl delete ns argocd
minikube stop -p w10
minikube delete -p w10
```

## Lưu Ý Bảo Mật

- Không commit `*.secret.yaml`, `.lab-local/`, `.tools/`, private key, AWS key, Gmail app password.
- `signing/cosign.pub` là public key nên có thể commit.
- `app-alert/email-secret.yaml` là file local ignored, chỉ dùng để apply thủ công.
- Nếu GitHub Actions báo thiếu `COSIGN_PRIVATE_KEY`, hãy set lại repository secret từ `.lab-local/cosign.key`.
