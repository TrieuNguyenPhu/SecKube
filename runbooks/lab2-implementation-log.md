# Lab 2 Implementation Log

Date: 2026-06-19

Scope: complete Lab 2 only. The 24h take-home challenge is intentionally out of scope.

## Environment observed

- Kubernetes context: `w10`
- Existing namespaces: `demo`, `argocd`
- AWS CLI active account: `355421126938`, IAM user `Trieu`, region `ap-southeast-1`
- Existing API image before the lab change: `ghcr.io/trieunguyenphu/w10-api:0.0.5`
- Existing GitOps root: `argocd/root.yaml` points to `https://github.com/TrieuNguyenPhu/SecKube.git`, branch `main`

## Changes made in repo

- Added ESO manifests:
  - `eso/secret-store.yaml`
  - `eso/external-secret.yaml`
- Added ArgoCD Applications:
  - `argocd/apps/eso.yaml`
  - `argocd/apps/eso-config.yaml`
  - `argocd/apps/policy-controller.yaml`
  - `argocd/apps/policies.yaml`
- Updated API rollout:
  - Mounts `db-secret` as a volume at `/etc/secrets/db`
  - Uses volume-based secret consumption so secret rotation does not require a pod restart
- Updated GitHub Actions build workflow:
  - Builds image locally
  - Runs Trivy and fails on `HIGH,CRITICAL`
  - Pushes only after Trivy passes
  - Signs pushed tags with Cosign
  - Updates `app-api/rollout.yaml` to the signed semver tag
- Added Sigstore policy:
  - `policies/cluster-image-policy.yaml`
  - Requires signatures for `ghcr.io/trieunguyenphu/w10-api**`
- Generated Cosign key pair:
  - Public key committed at `signing/cosign.pub`
  - Private key and password kept only in `.lab-local/`, which is ignored by Git
- Added ignore rules:
  - `.lab-local/`
  - `.tools/`
  - `cosign.key`

## Manual/local setup still required before the first full GitOps sync

The ArgoCD child apps `eso-config` and `policies` read from GitHub `main`, so push these repo changes before expecting ArgoCD to sync them from Git.

Create the AWS Secrets Manager value. On Windows, write JSON to an ignored local file and pass it with `file://` so AWS CLI preserves quotes correctly:

```powershell
$initialPassword = "replace-with-lab-only-password"
@{ password = $initialPassword } | ConvertTo-Json -Compress |
  Set-Content -Path .\.lab-local\db-secret.json -NoNewline

aws secretsmanager create-secret `
  --name demo/db `
  --secret-string file://.lab-local/db-secret.json `
  --region ap-southeast-1
```

If the secret already exists, update it instead:

```powershell
aws secretsmanager put-secret-value `
  --secret-id demo/db `
  --secret-string file://.lab-local/db-secret.json `
  --region ap-southeast-1
```

Create the Kubernetes AWS credential secret. Do not commit this value:

```powershell
$ak = aws configure get aws_access_key_id
$sk = aws configure get aws_secret_access_key

kubectl -n demo create secret generic aws-creds `
  --from-literal=access-key=$ak `
  --from-literal=secret-key=$sk `
  --dry-run=client -o yaml | kubectl apply -f -
```

Set GitHub repository secrets from the local ignored key material:

```powershell
# GitHub Secret: COSIGN_PRIVATE_KEY
Get-Content .\.lab-local\cosign.key -Raw

# GitHub Secret: COSIGN_PASSWORD
Get-Content .\.lab-local\cosign-password.txt -Raw
```

Do not paste either value into Git-tracked files.

## Recommended order

1. Push these repo changes to `main`.
2. Add the two GitHub Secrets: `COSIGN_PRIVATE_KEY`, `COSIGN_PASSWORD`.
3. Create or update AWS Secrets Manager secret `demo/db`.
4. Create Kubernetes secret `aws-creds` in namespace `demo`.
5. Apply/sync ArgoCD root so ESO and policy-controller install.
6. Wait until `external-secrets`, `eso-config`, `policy-controller`, and `policies` are healthy.
7. Run the GitHub Actions build workflow so the image is scanned, pushed, signed, and rollout tag is updated.
8. After the signed image is deployed, label namespace `demo` for Sigstore enforcement:

```powershell
kubectl label ns demo policy.sigstore.dev/include=true --overwrite
```

## Local verification performed

- Created AWS secret `demo/db` in `ap-southeast-1`.
- Created Kubernetes secret `aws-creds` in namespace `demo`.
- Installed Sigstore policy-controller through ArgoCD. In this lab cluster the ArgoCD Application status can be noisy (`OutOfSync`, `Unknown`, or `Progressing`) because the controller generates webhook fields at runtime and the minikube webhook probes are sensitive. Verify it with `kubectl get pods -n cosign-system` and the admission reject test.
- Installed ESO through ArgoCD. The ESO chart required `ServerSideApply=true` because large CRD annotations exceeded the Kubernetes client-side apply annotation limit.
- Updated ESO manifests to `external-secrets.io/v1`, matching the installed ESO 2.6.0 CRDs.
- Used `dataFrom.extract` for `demo/db` so the JSON key `password` is extracted into Kubernetes Secret `db-secret`.
- Verified `SecretStore/aws-store` is `Ready=True`.
- Verified `ExternalSecret/db-creds` reached `SecretSynced=True`.
- Rotated the AWS secret and observed Kubernetes Secret `db-secret` update in under 60 seconds while API pod UIDs stayed unchanged.
- Created `ClusterImagePolicy/require-w10-api-signature`.
- Verified Sigstore admission rejects a matching unsigned/tag-only image in a temporary labeled namespace.

Note: the local ArgoCD `api` Application self-heals from GitHub `main`. Until these repo changes are pushed, local `kubectl apply -f app-api/rollout.yaml` can be reverted by ArgoCD. After pushing to `main`, ArgoCD can sync the mounted `db-secret` rollout from Git.
