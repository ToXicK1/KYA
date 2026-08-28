# Render Deployment Guide — KYA Agent Registry Microservice

## 1. Overview & Service Metadata

- **Service Type**: Render Web Service
- **Environment / Runtime**: Docker
- **Repository Region**: Any supported Render region (e.g., Oregon, Frankfurt, Singapore)
- **Instance Type**: Starter / Standard (Minimum 512 MB RAM recommended)

---

## 2. Deployment Artifact Verification

The repository contains all required artifacts for automated containerized deployment:

| Artifact | Location | Verification Status |
| :--- | :--- | :--- |
| **Dockerfile** | [Dockerfile](file:///c:/Users/vyshu/Desktop/KYA/Dockerfile) | Multi-stage build, dynamic `${PORT:-8000}` binding, non-root `kya` user. |
| **.dockerignore** | [.dockerignore](file:///c:/Users/vyshu/Desktop/KYA/.dockerignore) | Created. Excludes `.env`, `.git`, `tests/`, `docs/`, and temporary build files. |
| **Pre-Deploy Script** | [pre_deploy.sh](file:///c:/Users/vyshu/Desktop/KYA/scripts/pre_deploy.sh) | Executable bash script validating production environment & running `alembic upgrade head`. |
| **Alembic Configuration** | [alembic.ini](file:///c:/Users/vyshu/Desktop/KYA/alembic.ini), `alembic/` | Configured to dynamically consume `DATABASE_URL` from application settings. |
| **Dependencies** | [requirements.txt](file:///c:/Users/vyshu/Desktop/KYA/requirements.txt) | Python dependencies specified (`asyncpg`, `sqlalchemy`, `fastapi`, `uvicorn`, `alembic`, `cryptography`, `PyJWT`). |
| **PORT Handling** | [Dockerfile](file:///c:/Users/vyshu/Desktop/KYA/Dockerfile), [config.py](file:///c:/Users/vyshu/Desktop/KYA/src/core/config.py) | Dockerfile CMD expands `${PORT:-8000}` injected by Render. |
| **Health Check Path** | [main.py](file:///c:/Users/vyshu/Desktop/KYA/src/main.py), [health.py](file:///c:/Users/vyshu/Desktop/KYA/src/presentation/api/v1/endpoints/health.py) | Lightweight probe at `/health` (Liveness) and `/api/v1/health` (Readiness). |
| **Database URL Handling**| [config.py](file:///c:/Users/vyshu/Desktop/KYA/src/core/config.py) | Safe normalization converts `postgres://` / `postgresql://` to `postgresql+asyncpg://`. |

---

## 3. Render Dashboard Configuration Instructions

Configure the following settings in the Render Web Service creation modal:

### Build & Deploy Settings
- **Service Name**: `kya-agent-registry` (or preferred name)
- **Environment**: `Docker`
- **Region**: Select target region
- **Branch**: `main` (or active deployment branch)
- **Dockerfile Path**: `./Dockerfile`
- **Docker Context**: `.`
- **Pre-Deploy Command**: `bash scripts/pre_deploy.sh`
- **Start Command**: *(Leave empty — defaults to CMD in Dockerfile)*

### Health Check Configuration
- **Health Check Path**: `/health`

---

## 4. Required Environment Variables & Secrets

Configure the following environment variables under **Environment** in the Render Dashboard:

| Variable Name | Required | Secret? | Value / Description | Example Value |
| :--- | :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | **YES** | No | Execution mode; strictly `production` | `production` |
| `DATABASE_URL` | **YES** | **YES** | Render PostgreSQL Internal DB URL | `postgres://kya_user:pass@dpg-xxx:5432/kya_db` |
| `JWT_SECRET_KEY` | **YES** | **YES** | Cryptographically secure 256-bit secret string | `openssl rand -hex 32` string |
| `CORS_ORIGINS` | **YES** | No | Comma-separated allowed frontend/client origins | `https://app.yourdomain.com` |
| `LOG_LEVEL` | No | No | Application logging output level (default: `INFO`) | `INFO` |

> [!IMPORTANT]
> Render automatically injects the `$PORT` environment variable at runtime. Do **not** hardcode `PORT` in your environment variable settings.

---

## 5. PostgreSQL Configuration

1. Create a **Render Managed PostgreSQL Database** in the same region as the Web Service.
2. Select **PostgreSQL 15+**.
3. Under Database Settings, copy the **Internal Database URL** (e.g., `postgres://user:password@dpg-xxx-a/kya_db`).
4. Paste the Internal Database URL into the `DATABASE_URL` environment variable of the Web Service.
   - *The application will automatically normalize `postgres://` to `postgresql+asyncpg://` at startup.*

---

## 6. Expected Public URL & Endpoint Structure

- **Public URL**: `https://<your-service-name>.onrender.com`
- **Liveness Probe**: `https://<your-service-name>.onrender.com/health`
- **Readiness Probe**: `https://<your-service-name>.onrender.com/api/v1/health`
- **Auth Endpoint**: `https://<your-service-name>.onrender.com/api/v1/auth/token`
- **Agent Registry**: `https://<your-service-name>.onrender.com/api/v1/agents`
- **Interactive Documentation**: Disabled in production mode (`/docs` returns 404).

---

## 7. Post-Deployment Verification Commands

Run these standard verification commands after deployment completes on Render:

### 1. Verify Liveness Probe
```bash
curl -i https://<your-service-name>.onrender.com/health
# Expected: HTTP 200 OK
# Response: {"status":"healthy","service":"KYA Agent Registry Microservice","version":"1.0.0","environment":"production"}
```

### 2. Verify Database Readiness Probe
```bash
curl -i https://<your-service-name>.onrender.com/api/v1/health
# Expected: HTTP 200 OK
# Response: {"status":"healthy","database":"connected",...}
```

### 3. Verify Unauthorized Mutation Block
```bash
curl -i -X POST https://<your-service-name>.onrender.com/api/v1/agents \
  -H "Content-Type: application.json" \
  -d '{"name":"Unauthorized Agent"}'
# Expected: HTTP 401 Unauthorized
```

### 4. Verify Production Docs Disabled
```bash
curl -i https://<your-service-name>.onrender.com/docs
# Expected: HTTP 404 Not Found
```

---

RENDER CONFIGURATION STATUS:
READY
