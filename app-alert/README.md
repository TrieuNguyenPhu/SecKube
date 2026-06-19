# Alert Email Setup

Thư mục này chứa rule cảnh báo SLO cho API và hướng dẫn tạo secret email cho Alertmanager.

## Files

- `prometheus-rules.yaml`: PrometheusRule được Argo CD sync tự động.
- `email-secret.yaml.example`: template secret email.
- `email-secret.yaml`: secret thật, bị Git và Argo CD ignore, không commit.

## Tạo Gmail App Password

Mở trang App Passwords của Google:

```powershell
start https://myaccount.google.com/apppasswords
```

Tạo app password mới và copy giá trị 16 ký tự.

## Tạo Secret Local

Copy file mẫu:

```powershell
Copy-Item .\app-alert\email-secret.yaml.example .\app-alert\email-secret.yaml
```

Sửa `app-alert/email-secret.yaml`, thay `your-gmail-app-password-16-chars` bằng Gmail App Password thật.

## Apply Secret

```powershell
kubectl apply -f .\app-alert\email-secret.yaml
```

File này được khai báo trong `.argocdignore`, nên Argo CD sẽ không sync secret từ Git.

## Verify

Kiểm tra secret:

```powershell
kubectl get secret alertmanager-email -n monitoring
```

Kiểm tra Alertmanager pod:

```powershell
kubectl get pod -n monitoring -l app.kubernetes.io/name=alertmanager
```

Kiểm tra secret đã mount vào Alertmanager:

```powershell
$pod = kubectl get pod -n monitoring -l app.kubernetes.io/name=alertmanager -o jsonpath="{.items[0].metadata.name}"
kubectl exec -n monitoring $pod -c alertmanager -- ls /etc/alertmanager/secrets/alertmanager-email/
```

## Lưu Ý Bảo Mật

- Không commit `email-secret.yaml`.
- Chỉ commit `email-secret.yaml.example`.
- Nếu Gmail App Password bị lộ, revoke trên Google Account và tạo password mới.
