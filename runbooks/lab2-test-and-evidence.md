# Lab 2 Test and Evidence Guide

Use this checklist to test Lab 2 and capture screenshots/evidence. Keep screenshots in your report or LMS submission, not in the repo unless your instructor asks for them.

## Evidence 1 - Repo deliverables

Show the required files exist:

```powershell
git status --short
Get-ChildItem eso,signing,policies,runbooks
Get-ChildItem argocd\apps\eso*.yaml,argocd\apps\policy-controller.yaml,argocd\apps\policies.yaml
```

Screenshot target:

- Terminal showing `eso/`, `signing/cosign.pub`, `.github/workflows/build-push.yml`, `argocd/apps/*.yaml`, `policies/`, and `runbooks/`.

## Evidence 2 - ESO operator and ExternalSecret healthy

```powershell
kubectl get applications -n argocd external-secrets eso-config
kubectl get pods -n external-secrets
kubectl get secretstore,externalsecret -n demo
kubectl describe externalsecret db-creds -n demo
```

Expected:

- ArgoCD apps are `Synced` and `Healthy`.
- External Secrets pods are running.
- `externalsecret/db-creds` reports `SecretSynced` or equivalent ready condition.

Screenshot target:

- Terminal with the app status and `kubectl get secretstore,externalsecret -n demo`.

## Evidence 3 - Secret created from AWS

```powershell
kubectl -n demo get secret db-secret
$encoded = kubectl -n demo get secret db-secret -o jsonpath='{.data.password}'
[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($encoded))
```

Expected:

- `db-secret` exists.
- Decoded value equals the current AWS Secrets Manager value.

Screenshot target:

- Capture the existence of `db-secret`.
- If you show the decoded password, use a lab-only password and redact it in the final report if required.

## Evidence 4 - Rotate secret in under 60 seconds without pod restart

Record pod age before rotation:

```powershell
kubectl -n demo get pods -l app=api
```

Rotate AWS secret:

```powershell
$rotatedPassword = "rotate-" + (Get-Date -Format yyyyMMddHHmmss)
@{ password = $rotatedPassword } | ConvertTo-Json -Compress |
  Set-Content -Path .\.lab-local\db-secret.json -NoNewline

aws secretsmanager put-secret-value `
  --secret-id demo/db `
  --secret-string file://.lab-local/db-secret.json `
  --region ap-southeast-1
```

Poll Kubernetes until value changes:

```powershell
$deadline = (Get-Date).AddSeconds(60)
do {
  $encoded = kubectl -n demo get secret db-secret -o jsonpath='{.data.password}'
  $value = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($encoded))
  "{0} {1}" -f (Get-Date -Format HH:mm:ss), $value
  if ($value -eq $rotatedPassword) { break }
  Start-Sleep -Seconds 5
} while ((Get-Date) -lt $deadline)
```

Check pod age again:

```powershell
kubectl -n demo get pods -l app=api
```

Expected:

- `db-secret` changes within 60 seconds.
- Pod names and ages do not reset.

Screenshot target:

- Before/after `kubectl get pods`.
- Poll output showing the rotated value appeared before the deadline.

## Evidence 5 - GitHub Actions Trivy gate

Trigger the workflow:

```powershell
git add .
git commit -m "lab2: add eso and supply chain controls"
git push origin main
```

Expected:

- Build workflow runs.
- Trivy step fails if a `HIGH` or `CRITICAL` CVE is present.
- If Trivy passes, image tags are pushed and Cosign signs them.

Screenshot target:

- GitHub Actions page showing the `Scan image with Trivy` step.
- For a pass run, also show `Sign pushed image tags`.
- For a fail run, show Trivy caused the workflow to stop.

## Evidence 6 - Cosign public key and local verify

After the workflow pushes a signed tag, verify using the public key:

```powershell
.\.tools\cosign.exe verify `
  --key .\signing\cosign.pub `
  ghcr.io/trieunguyenphu/w10-api:<SIGNED_TAG>
```

Expected:

- Cosign verification succeeds for the signed tag.

Screenshot target:

- Terminal showing successful verification. Do not show private key or password.

## Evidence 7 - Admission rejects unsigned image

Enable policy-controller only after a signed API image is already deployed:

```powershell
kubectl label ns demo policy.sigstore.dev/include=true --overwrite
```

Try the current unsigned lab image tag that matches the policy:

```powershell
kubectl create ns sigstore-lab-test --dry-run=client -o yaml | kubectl apply -f -
kubectl label ns sigstore-lab-test policy.sigstore.dev/include=true --overwrite

kubectl -n sigstore-lab-test run unsigned-api `
  --image=ghcr.io/trieunguyenphu/w10-api:0.0.5 `
  --restart=Never `
  --dry-run=server -o yaml
```

Expected:

- Admission resolves the image to a digest and rejects it with `no signatures found` or an equivalent signature validation error.

Screenshot target:

- Terminal showing the admission denial.

Clean up the test namespace:

```powershell
kubectl delete ns sigstore-lab-test --wait=false
```

## Evidence 8 - Signed image is admitted

Deploy the signed semver tag from the workflow:

```powershell
kubectl -n demo get rollout api -o jsonpath='{.spec.template.spec.containers[0].image}'
kubectl -n demo get pods -l app=api
```

Expected:

- Rollout references the signed tag from GitHub Actions.
- Pods are running after namespace enforcement is enabled.

Screenshot target:

- Terminal with rollout image and running pods.

## Evidence 9 - No secrets committed

```powershell
git grep -n -E "AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|aws_secret_access_key|BEGIN .*PRIVATE KEY" -- .
if ($LASTEXITCODE -eq 1) { "no secret-looking values in tracked files" }

git log -p --all | Select-String -Pattern "AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|aws_secret_access_key|BEGIN .*PRIVATE KEY"
```

Expected:

- No real AWS keys, Cosign password, or live secret value appears in tracked files or history.
- Documentation mentions placeholder names only.

Screenshot target:

- Terminal showing no real secrets found.
