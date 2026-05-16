# Nexus — AI Governance Platform

Nexus is the governance layer that wraps existing project services and enforces accountability on every AI response.

## Milestones

### Milestone 1 — Core Platform Scaffold (completed)
- `gateway/` FastAPI with versioned `/api/v1/*`
- JWT auth module and tenant/workspace resolver
- Redis-backed rate limiting
- Query lifecycle scaffold with query IDs
- Combined upstream execution (multi-model + deterministic + platform)
- Recomputed score card fields and overall score
- Policy engine with structured rules + text DSL support
- Enforcement actions: `DELIVER`, `RETRY` (max 2), `ESCALATE`, `BLOCK`

### Milestone 2 — Governance Domain Models (completed scaffold)
- SQLAlchemy models for:
  - `Tenant`
  - `Workspace`
  - `PolicyRule`
  - `QueryTrace`
  - `AuditLog`
- Alembic config + migrations directory scaffold

### Milestone 3 — Next.js Operator Dashboard (completed scaffold)
- Next.js + TypeScript + Tailwind skeleton
- Required pages/components/hooks/store/api/types files created
- Ready for implementing real-time SSE, policy builder UI, and charts

### Milestone 4 — Infrastructure (completed scaffold)
- Docker Compose: Postgres, Redis, Gateway, Dashboard
- Makefile targets: install/dev/migrate/seed/test
- `.env.example` documented

## Quickstart

```bash
cd nexus
cp .env.example .env
make dev
```

Gateway: `http://localhost:8090/api/v1/health`
Governance: `http://localhost:8090/governance/api/v1/health`
Dashboard: `http://localhost:3005`

