# KWS Control Panel

A unified hosting control panel combining deployment, DNS, SSL, and monitoring capabilities.

## Architecture
- **Frontend:** Next.js 15 + React + TailwindCSS
- **Backend:** FastAPI + PostgreSQL + Redis + RQ
- **Reverse Proxy:** Traefik with ACME TLS
- **DNS:** PowerDNS with future multi-provider drivers
- **Agents:** Lightweight FastAPI services on remote servers

## Server Requirements

The KWS Control Panel is designed to be lightweight, but the following server specifications are recommended for a smooth experience.

| Resource      | Minimum          | Recommended      |
|---------------|------------------|------------------|
| **CPU**       | 2 Cores          | 4+ Cores         |
| **Memory**    | 4 GB RAM         | 8+ GB RAM        |
| **Disk Space**| 40 GB            | 80+ GB           |
| **OS**        | Ubuntu 22.04 LTS+ | Ubuntu 24.04 LTS+|

The server must have a public IP address and be accessible from the internet.

## Installation

To install the KWS Control Panel, connect to your server via SSH and run the following command:

```bash
bash <(curl -s https://raw.githubusercontent.com/karvewebsolutions/Server-Panel-SUper/main/scripts/install.sh)
```

The installation script will guide you through the setup process.

## Core Services

The KWS Control Panel is composed of the following core services:

- **Backend API:** A FastAPI application that serves as the main API for the control panel.
- **Frontend:** A Next.js and React-based dashboard for user interaction.
- **DNS Services:** PowerDNS and PowerDNS-Admin for managing DNS records.
- **Data Stores:** PostgreSQL for the database and Redis for caching and background job queuing.
- **Static Assets:** An optional Nginx container for serving static assets.

## Development Environment

To set up a local development environment, you can use the following commands:

- **Backend:** `uvicorn app.main:app --reload`
- **Frontend:** `npm run dev -- --hostname 0.0.0.0`
- **Agent:** `uvicorn agent.main:app --reload --port 9000`

## Additional Notes

- **Traefik:** The reverse proxy is configured with TLS challenge enabled for automated SSL certificate generation.
- **Database Migrations:** The initial database schema is created using SQLAlchemy's metadata initialization. For future schema changes, a migration tool like Alembic is recommended.
