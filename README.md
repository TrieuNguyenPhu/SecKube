# W10 - Progressive Delivery with Analysis

GitOps setup for API deployment với Argo Rollouts + AnalysisTemplate.

## Concept

Deploy API với **canary strategy** và **automated analysis**:
- Rollout: 10% → 50% → 100%
- AnalysisTemplate query Prometheus để check success rate ≥ 95%
- Auto rollback nếu analysis fail
- AlertManager gửi email khi có SLO violation

## Requirements

- Docker Desktop
- kubectl
- minikube
- git

## Structure

```
w10/
├── app-api/              # API Rollout manifests
│   ├── rollout.yaml      # Argo Rollout với canary strategy
│   ├── service.yaml      # Service expose API
│   └── servicemonitor.yaml # Prometheus metrics scraper
├── app-analysis/         # Analysis manifests
│   └── analysis-template.yaml # Template phân tích success rate
├── app-alert/            # Alert manifests
│   ├── prometheus-rules.yaml # PrometheusRule cho SLO alerts
│   ├── email-secret.yaml # Gmail password (NOT COMMITTED)
│   └── README.md         # Alert setup guide
├── app-common/           # Common resources
│   └── demo-namespace.yaml # Namespace demo
├── src/                  # Source code
│   └── api/              # Flask API application
├── argocd/
│   ├── apps/             # ArgoCD Application manifests
│   │   ├── app-api.yaml  # Deploy API Rollout
│   │   ├── app-analysis.yaml # Deploy AnalysisTemplate
│   │   ├── app-alert.yaml # Deploy PrometheusRule
│   │   ├── app-common.yaml # Deploy common resources
│   │   ├── k8s-prometheus.yaml # Prometheus + AlertManager
│   │   └── k8s-rollout.yaml # Argo Rollouts controller
│   └── root.yaml         # App of Apps pattern
└── README.md
```

## Quick Start

### 1. Setup Cluster
```powershell
minikube start -p w10 --driver=docker
kubectl config use-context w10
```

### 2. Install ArgoCD
```powershell
kubectl create ns argocd
kubectl apply --server-side -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl -n argocd rollout status deploy/argocd-server
```

### 3. Access ArgoCD UI
```powershell
# Port forward (chạy trong một cửa sổ PowerShell riêng)
kubectl -n argocd port-forward svc/argocd-server 8080:443

# Get password
$encoded = kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}"
[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($encoded))
```

### 4. Deploy App of Apps
```powershell
kubectl apply -f .\argocd\root.yaml
```

### 5. Setup Email Alert (Optional)
```powershell
# File app-alert\email-secret.yaml đã chứa App Password
kubectl apply -f .\app-alert\email-secret.yaml
```

## Components

### Core
- **Argo Rollouts**: Progressive delivery controller
- **Prometheus Stack**: Metrics collection + AlertManager
- **API**: Flask application với metrics endpoint

### GitOps Applications
- `app-api`: API Rollout với canary strategy
- `app-analysis`: AnalysisTemplate cho automated validation
- `app-alert`: PrometheusRule cho runtime alerting
- `app-common`: Shared resources (namespace)
- `k8s-prometheus`: Monitoring stack
- `k8s-rollout`: Argo Rollouts controller

## Verify Deployment

### Check Rollout Status
```powershell
# Watch rollout progress
kubectl get rollout api -n demo -w

# Check current state
kubectl get rollout api -n demo

# Check pods
kubectl get pods -n demo -l app=api
```

### Check AnalysisRun
```powershell
# List analysis runs
kubectl get analysisrun -n demo

# Watch latest analysis
$latest = kubectl get analysisrun -n demo --sort-by=.metadata.creationTimestamp -o name | Select-Object -Last 1
$latest

# Describe for detailed metrics
kubectl describe -n demo $latest
```

### Check SLO Alert Rule
```powershell
kubectl get prometheusrule slo-alerts -n monitoring
```

### Query Prometheus Metrics
```powershell
# Success rate metric
kubectl run test-query --image=curlimages/curl:latest --rm -i --restart=Never -n monitoring -- curl -s "http://kube-prometheus-stack-prometheus.monitoring.svc:9090/api/v1/query?query=api:success_rate:5m"
```

## Test Scenarios (GitOps)

### Test 1: Successful Deployment (Success Rate ≥ 90%)
```powershell
# Edit rollout to deploy with no errors
notepad .\app-api\rollout.yaml
# Set: ERROR_RATE: "0"

git add app-api/rollout.yaml
git commit -m "test: deploy with 0% error rate"
git push origin main

# Watch AnalysisRun succeed
kubectl get analysisrun -n demo -w
```

### Test 2: Failed Deployment (Success Rate < 90%)
```powershell
# Edit rollout to deploy with 15% error rate
notepad .\app-api\rollout.yaml
# Set: ERROR_RATE: "0.15"

git add app-api/rollout.yaml
git commit -m "test: deploy with 15% error rate (should fail)"
git push origin main

# Watch AnalysisRun fail and auto rollback
kubectl get analysisrun -n demo -w
kubectl get rollout api -n demo
```

### Test 3: Trigger SLO Alert Email
```powershell
# Edit rollout to set 8% error rate (triggers alert, but passes canary)
notepad .\app-api\rollout.yaml
# Set: ERROR_RATE: "0.08"

git add app-api/rollout.yaml
git commit -m "test: deploy with 8% error rate (92% success)"
git push origin main

# Canary passes (>90%) but SLO alert fires (below 95%)
# Wait 2-3 minutes, then check email inbox
```


## Configuration Reference

### Sync Waves
ArgoCD applications deploy in order:
- Wave -1: `app-common` (namespace)
- Wave 0: `k8s-prometheus`, `k8s-rollout` (infrastructure)
- Wave 1: `app-analysis`, `app-alert` (configuration)
- Wave 2: `app-api` (application)

## Cleanup

```powershell
# Delete ArgoCD applications
kubectl delete -f .\argocd\root.yaml

# Wait for resources to be cleaned up
kubectl get all -n demo
kubectl get all -n monitoring

# Delete ArgoCD
kubectl delete ns argocd

# Stop minikube
minikube stop -p w10
minikube delete -p w10
```

## Ghi chú bổ sung cho repo hiện tại

- Git repository: `https://github.com/TrieuNguyenPhu/SecKube.git`
- Container image: `ghcr.io/trieunguyenphu/seckube-api`
- Canary analysis dùng ngưỡng 90%; SLO alert dùng ngưỡng 95%.
- `app-alert\email-secret.yaml` đã có App Password, được Git ignore và không được commit.
- Khi test `ERROR_RATE`, cần tạo request liên tục để Prometheus có đủ dữ liệu:

```powershell
kubectl run api-load -n demo --image=busybox:1.36 --restart=Never -- /bin/sh -c "while true; do wget -q -O- http://api/ > /dev/null || true; sleep 0.2; done"

# Xóa load generator sau khi test
kubectl delete pod api-load -n demo
```

Tài liệu dành cho AI agent: [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md), [ARCHITECTURE.md](ARCHITECTURE.md), [API_MAP.md](API_MAP.md), [BUSINESS_RULES.md](BUSINESS_RULES.md), [AI_NOTES.md](AI_NOTES.md).
