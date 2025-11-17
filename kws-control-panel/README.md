# KWS Control Panel

A unified hosting control panel combining deployment, DNS, SSL, and monitoring capabilities.

## Architecture
- **Frontend:** Next.js 15 + React + TailwindCSS
- **Backend:** FastAPI + PostgreSQL + Redis + RQ
- **Reverse Proxy:** Traefik with ACME TLS
- **DNS:** PowerDNS with future multi-provider drivers
- **Agents:** Lightweight FastAPI services on remote servers

## Quickstart
1. Install Docker and Compose, then start the stack:
   ```bash
   chmod +x scripts/install.sh
   ./scripts/install.sh
   ```
2. Access the panel at https://cp.karve.fun
3. Default admin credentials: `admin@karve.fun` / `admin123`

## Services
- Backend API: FastAPI at `/api`
- Frontend: Next.js dashboard
- PowerDNS + PowerDNS-Admin: internal DNS services
- Redis & PostgreSQL: data and background queue foundation
- Optional nginx-static: serve static assets on `static.cp.karve.fun`

## Development
- Backend dev server: `uvicorn app.main:app --reload`
- Frontend dev server: `npm run dev -- --hostname 0.0.0.0`
- Agent dev server: `uvicorn agent.main:app --reload --port 9000`

## Notes
- Traefik uses DNS-01-ready configuration with TLS challenge enabled.
- Migrations are handled via SQLAlchemy metadata initialization for the bootstrap release; Alembic can be added for future schema evolution.
