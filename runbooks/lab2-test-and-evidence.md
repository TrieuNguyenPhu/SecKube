# Lab 2 Test and Evidence Guide

Use this checklist to test Lab 2 and capture screenshots/evidence. Keep screenshots in your report or LMS submission, not in the repo unless your instructor asks for them.

Current organized submission folder:

```text
evidence/lab2/
|-- 01-argocd-applications-synced-healthy.jpeg
|-- 02-argocd-applications-cli-synced-healthy.png
|-- 03-eso-aws-secret-rotated.png
|-- 04-eso-rotate-secret-pods-no-restart.png
`-- 05-github-actions-trivy-cosign-signed.jpeg
```

Compared with the sample folder `evidence/_samples/SCRUM-59_attachments/`, the current screenshots already cover ArgoCD app health, secret rotation, pods not restarting, and GitHub Actions Trivy/Cosign success. Capture the missing optional-but-recommended evidence at the end of this runbook if the final report needs full supply-chain proof.

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

## Current evidence review

Evidence already captured:

- `01-argocd-applications-synced-healthy.jpeg`: Argo CD UI shows all applications healthy and synced, including `eso-config`, `external-secrets`, `policies`, `policy-controller`, `rbac`, and `root`.
- `02-argocd-applications-cli-synced-healthy.png`: Terminal confirms Argo CD applications are `Synced` and `Healthy`.
- `03-eso-aws-secret-rotated.png`: AWS Secrets Manager `demo/db` was updated with a new version.
- `04-eso-rotate-secret-pods-no-restart.png`: Kubernetes `db-secret` reflects the rotated value and API pods remain `Running` with `RESTARTS 0`.
- `05-github-actions-trivy-cosign-signed.jpeg`: GitHub Actions workflow succeeded and includes Trivy scan plus Cosign signing steps.

Evidence still recommended:

- `06-policy-controller-pods-healthy.png`: terminal output of `kubectl get pods -n cosign-system` or an Argo CD details view for `policy-controller`.
- `07-cosign-verify-signed-image.png`: terminal output of `cosign verify --key .\signing\cosign.pub ghcr.io/trieunguyenphu/w10-api:<SIGNED_TAG>`.
- `08-admission-reject-unsigned-image.png`: terminal output showing policy-controller rejects an unsigned image with a signature validation error.
- `09-signed-image-admitted.png`: terminal output showing the deployed rollout uses a signed tag and pods keep running after namespace enforcement.
- `10-no-secrets-committed.png`: terminal output showing no AWS key, Cosign private key, or secret-looking value appears in tracked files/history.

Commands for the missing screenshots:

```powershell
kubectl get pods -n cosign-system

.\.tools\cosign.exe verify `
  --key .\signing\cosign.pub `
  ghcr.io/trieunguyenphu/w10-api:<SIGNED_TAG>

kubectl create ns sigstore-lab-test --dry-run=client -o yaml | kubectl apply -f -
kubectl label ns sigstore-lab-test policy.sigstore.dev/include=true --overwrite
kubectl -n sigstore-lab-test run unsigned-api `
  --image=ghcr.io/trieunguyenphu/w10-api:0.0.5 `
  --restart=Never `
  --dry-run=server -o yaml
kubectl delete ns sigstore-lab-test --wait=false

kubectl -n demo get rollout api -o jsonpath='{.spec.template.spec.containers[0].image}'
kubectl -n demo get pods -l app=api

git grep -n -E "AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|aws_secret_access_key|BEGIN .*PRIVATE KEY" -- .
if ($LASTEXITCODE -eq 1) { "no secret-looking values in tracked files" }
git log -p --all | Select-String -Pattern "AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|aws_secret_access_key|BEGIN .*PRIVATE KEY"
```

Do not capture Cosign private key, `COSIGN_PASSWORD`, AWS access keys, or real production secret values.
