# KYA — Know Your Agent

> An identity, trust and policy enforcement layer for autonomous AI agents.

[![Project Status: Early Development / MVP](https://img.shields.io/badge/status-EARLY%20DEVELOPMENT%20%2F%20MVP-orange.svg)](#project-status)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Test Coverage: 94%](https://img.shields.io/badge/coverage-94%25-brightgreen.svg)](#running-tests)

---

> [!IMPORTANT]
> **PROJECT STATUS: EARLY DEVELOPMENT / MVP**  
> KYA is currently an open-source Minimum Viable Product (MVP) core agent registry. It is actively undergoing architecture and specification design. **It is NOT currently deployed to production.**

---

## 1. The Problem

As autonomous AI agents execute financial transactions, call external APIs, perform cross-organization workflows, and interact with smart contracts, traditional user-centric identity systems (OAuth2, API keys, session cookies) break down:

- **Lack of Cryptographic Non-Repudiation**: Traditional API keys do not prove *which* agent generated a specific request payload.
- **Over-privileged Execution**: Agents lack strict operational bounds (e.g., maximum transaction values, explicit allowed capabilities).
- **Zero-Trust Gap**: Organizations have no standardized mechanism to verify an external agent's public key, status, owner organization, or capability manifest before granting API access.

---

## 2. What KYA Does

**KYA (Know Your Agent)** provides a zero-trust Agent Identity Registry & Verification Microservice. It gives autonomous AI agents cryptographically verifiable identities and manifest specifications.

Key functions:
- **Agent Identity Registration**: Registers AI agent manifests tied to public key infrastructure (Ed25519, RSA, ECDSA).
- **Zero-Trust Signature Verification**: Verifies signed message payloads directly against registered active agent public keys without relying on third-party identity providers.
- **Private Key Violation Prevention**: Inspects public key submissions during registration and strictly rejects private key PEM blocks.
- **Agent Lifecycle Governance**: Supports state transitions (`ACTIVE` ↔ `SUSPENDED` → `REVOKED`).

---

## 3. Current MVP Capabilities

- **Multi-Algorithm Key Support**: Verifies signatures for Ed25519, RSA (PKCS#1 v1.5 / PSS), and ECDSA (SECP256R1, SECP256K1).
- **Public Key & Private Key Validation**: Detects and rejects private keys embedded in registration payloads.
- **Role-Based API Management**: Admin-authenticated agent creation and lifecycle management (`kya_admin` role).
- **Rate-Limited Endpoints**: IP-based rate limiting on token issuance and cryptographic verification endpoints.
- **Async PostgreSQL / SQLite Core**: Built on FastAPI, SQLAlchemy 2.0 (Async), Pydantic v2, and Alembic migrations.

---

## 4. Architecture Overview

```
                        ┌────────────────────────┐
                        │   Autonomous Agent     │
                        └───────────┬────────────┘
                                    │
                        [ Signed Payload + Key ID ]
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        KYA Microservice Gateway                        │
│                                                                        │
│  ┌────────────────────┐   ┌────────────────────┐   ┌────────────────┐ │
│  │ Security & Authz   │   │ Signature Verifier │   │ Agent Registry │ │
│  │ (JWT / Admin Role) │   │ (PyCA Cryptography)│   │ (PostgreSQL/   │ │
│  └────────────────────┘   └────────────────────┘   │  SQLite Async) │ │
│                                                    └────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

For detailed architecture diagrams, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## 5. Security Model

KYA decouples **human/admin authentication** from **agent cryptographic verification**:

1. **Admin Domain**: Human administrators authenticate via JWT access tokens (`POST /api/v1/auth/token`) to manage agent registrations and status changes.
2. **Agent Domain**: Autonomous agents never share secret keys. Agents sign payloads locally with their private key and submit the signature alongside their `key_id`. KYA verifies the signature using the corresponding public key registered in the database.

For complete threat assumptions and security specifications, see [docs/SECURITY.md](docs/SECURITY.md).

---

## 6. Example Request Flow

### Step 1: Agent Key Verification Request
An external gateway forwards an agent's signed request payload to KYA:

```http
POST /api/v1/agents/verify-signature HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "key_id": "kya_key_9f8d7e6a5b4c3d2e",
  "message_base64": "S1lBIFRyYW5zYWN0aW9uIFJlcXVlc3QgIzEwMDQy",
  "signature_base64": "dGVzdF9zaWduYXR1cmVfYnl0ZXNfaGVyZQ=="
}
```

### Response
```json
{
  "is_valid": true,
  "agent_id": "kya_agt_01h9x3k2m00000000000000000",
  "key_id": "kya_key_9f8d7e6a5b4c3d2e",
  "algorithm": "ED25519",
  "verified_at": "2026-08-28T17:15:00Z"
}
```

---

## 7. API Overview

| Endpoint | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/health` | `GET` | No | Liveness probe |
| `/api/v1/health` | `GET` | No | Readiness probe (DB ping) |
| `/api/v1/auth/token` | `POST` | No (Rate Limited) | Issues admin JWT access tokens |
| `/api/v1/agents` | `POST` | Admin (`kya_admin`) | Registers a new Agent & Public Keys |
| `/api/v1/agents` | `GET` | No | Lists registered agents with pagination |
| `/api/v1/agents/{agent_id}` | `GET` | No | Retrieves agent manifest & key details |
| `/api/v1/agents/{agent_id}/status` | `PATCH` | Admin (`kya_admin`) | Updates agent status (`ACTIVE`, `SUSPENDED`, `REVOKED`) |
| `/api/v1/agents/verify-signature` | `POST` | No (Rate Limited) | Cryptographically verifies payload signatures |

---

## 8. Local Setup

### Prerequisites
- Python 3.11+
- Virtualenv

### Setup Steps
```bash
# 1. Clone the repository
git clone https://github.com/ToXicK1/KYA.git
cd KYA

# 2. Create and activate virtual environment
python -m venv .venv
# On Linux/macOS: source .venv/bin/activate
# On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment template
cp .env.example .env

# 5. Run local development server
uvicorn src.main:app --reload
```

Server will be running at `http://localhost:8000`. Swagger UI is available at `http://localhost:8000/docs` in development mode.

---

## 9. Running Tests

KYA maintains a comprehensive test suite with white-box unit tests, integration tests, and black-box API validation:

```bash
# Run test suite with coverage report
python -m pytest --cov=src --cov-report=term-missing
```

Current test suite coverage: **94%**.

---

## 10. Docker Setup

Run KYA locally using Docker Compose:

```bash
# Build and start services (App + PostgreSQL)
docker-compose up --build
```

Access the health check at `http://localhost:8000/health`.

---

## 11. Database Migrations

KYA uses **Alembic** for asynchronous database migrations.

```bash
# Run database migrations manually
python -m alembic upgrade head
```

---

## 12. Environment Variables

| Variable | Default (Dev) | Description |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `development` | Environment mode (`development` / `production` / `test`) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./kya_dev.db` | Connection string (`postgresql+asyncpg://...` in prod) |
| `JWT_SECRET_KEY` | *(dev fallback)* | Secret key for signing JWT tokens (Required in prod) |
| `CORS_ORIGINS` | `http://localhost:3000,...` | Allowed CORS origins |
| `PORT` | `8000` | Application HTTP binding port |

---

## 13. Current Limitations

- **Rate Limiting Scope**: Rate limiting currently uses an in-memory sliding window (single instance). Distributed deployment requires a Redis backend adapter.
- **Admin Password Storage**: Token issuance uses simplified authentication intended for MVP bootstrapping; full IDP integration is planned.

---

## 14. Roadmap

- [ ] Redis-backed distributed rate limiter & revocation cache.
- [ ] OAuth2 / OIDC provider integration for enterprise admin login.
- [ ] Policy decision engine for granular payload operational bound checking.
- [ ] Webhook notifications on agent revocation events.

---

## 15. License & Project Status

- **Status**: Early Development / MVP Core
- **License**: [MIT License](LICENSE) — Copyright (c) 2026 ToXicK1
