# Security Policy

## Reporting a Vulnerability

Please do **not** open a public GitHub issue for security vulnerabilities. Email the maintainers directly or open a [GitHub Security Advisory](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing/privately-reporting-a-security-vulnerability) on this repository.

---

## Secret Management

All credentials are loaded exclusively from environment variables. **No secrets are hardcoded.**

| Secret | How to generate |
|---|---|
| `POSTGRES_PASSWORD` | `openssl rand -base64 32` |
| `API_SECRET_KEY` | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | `openssl rand -base64 24` |
| `AIRFLOW_FERNET_KEY` | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `AIRFLOW_SECRET_KEY` | `openssl rand -base64 32` |

### Local development

```bash
cp .env.example .env
# Edit .env and replace every CHANGE_ME value
```

### Production (GitHub Actions / k8s)

Store all secrets in **GitHub Actions Secrets** (Settings → Secrets and variables → Actions) or a Kubernetes Secret / external secrets manager (Vault, AWS Secrets Manager). Never pass secrets as plain environment variables in public CI logs.

---

## What is and is not secret

**Secret (never commit):**
- `.env` — blocked by `.gitignore`
- Database passwords, API keys, Fernet keys, MinIO credentials
- Any TLS certificates or private keys

**Safe to commit:**
- `.env.example` — contains only `CHANGE_ME` placeholders, no real values
- Non-credential config (port numbers, index names, topic names)

---

## Pydantic SecretStr

Sensitive config fields (`postgres_url`, `api_secret_key`, `minio_secret_key`) are typed as `pydantic.SecretStr`. This prevents them from appearing in logs, tracebacks, or `repr()` output. Access the raw value only where required via `.get_secret_value()`.

---

## GitHub Secret Scanning

This repository has GitHub secret scanning enabled. Push protection will block commits that contain detected credential patterns. If you receive a false positive, follow the [GitHub docs](https://docs.github.com/en/code-security/secret-scanning/pushing-a-branch-blocked-by-push-protection) to bypass with justification.
