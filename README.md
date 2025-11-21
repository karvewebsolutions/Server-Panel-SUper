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

These instructions will guide you through the process of setting up the KWS Control Panel on a new Ubuntu server.

### 1. Connect to Your Server

First, connect to your server via SSH.

```bash
ssh root@your_server_ip
```

### 2. Install Dependencies

The KWS Control Panel requires **Docker** and **Docker Compose** to be installed on your server.

**Install Docker:**

```bash
apt-get update
apt-get install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

**Install Docker Compose:**

```bash
apt-get install -y docker-compose-plugin
```

### 3. Clone the Repository

Next, clone the KWS Control Panel repository to your server.

```bash
git clone https://github.com/your-repo/kws-control-panel.git
cd kws-control-panel
```

*Note: Replace `https://github.com/your-repo/kws-control-panel.git` with the actual repository URL.*

### 4. Run the Installation Script

The installation script will set up the necessary Docker containers and network configurations.

```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

### 5. Access the Control Panel

Once the installation is complete, you can access the KWS Control Panel in your web browser.

- **URL:** `https://cp.your-domain.com`
- **Username:** `admin@your-domain.com`
- **Password:** `admin123`

*Note: Replace `your-domain.com` with the domain you have configured for the control panel.*

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
