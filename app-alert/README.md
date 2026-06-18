# Alert Setup

## Manual Steps

### 1. Tạo Gmail App Password
```powershell
Start-Process "https://myaccount.google.com/apppasswords"
# Tạo password mới, copy 16 ký tự
```

### 2. Apply Email Secret
```powershell
# Edit và paste password vào
notepad .\app-alert\email-secret.yaml

# Apply secret (file này bị .argocdignore)
kubectl apply -f .\app-alert\email-secret.yaml
```

### 3. Verify
```powershell
# Check secret exists
kubectl get secret alertmanager-email -n monitoring

# Check Alertmanager running
kubectl get pod -n monitoring -l app.kubernetes.io/name=alertmanager

# Check secret mounted
$pod = kubectl get pod -n monitoring -l app.kubernetes.io/name=alertmanager -o jsonpath="{.items[0].metadata.name}"
kubectl exec -n monitoring $pod -c alertmanager -- ls /etc/alertmanager/secrets/alertmanager-email/
```

## Files
- `email-secret.yaml` - Gmail credentials ⛔ KHÔNG commit (ignored by ArgoCD)
- `prometheus-rules.yaml` - SLO alert rules ✅ Auto-deployed by ArgoCD
- Alertmanager config → `argocd/apps/k8s-prometheus.yaml` (Helm values)

## Ghi chú cho repo hiện tại

`app-alert\email-secret.yaml` đã được tạo và chứa App Password. Chỉ cần chạy lệnh `kubectl apply`; không sao chép đè từ file `.example` và không commit secret vào Git.
