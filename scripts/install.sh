#!/usr/bin/env bash
set -euo pipefail

# This script will be populated in the following steps.
echo "KWS Control Panel Installer"

# Check for dependencies
if ! command -v git &> /dev/null; then
  echo "Git is not installed. Installing..."
  # Assuming Debian/Ubuntu-based system
  apt-get update && apt-get install -y git
fi

if ! command -v docker &> /dev/null; then
  echo "Installing Docker..."
  curl -fsSL https://get.docker.com | sh
fi

if ! docker compose version &> /dev/null; then
  echo "Docker Compose is not installed. Installing..."
  apt-get update && apt-get install -y docker-compose-plugin
fi

echo "All dependencies are installed."

# Gather user input
echo "Please enter the following information to configure your KWS Control Panel:"
read -p "Domain Name (e.g., your-domain.com): " DOMAIN
read -p "Administrator Email: " ADMIN_EMAIL
while true; do
    read -s -p "Administrator Password: " ADMIN_PASSWORD
    echo
    read -s -p "Confirm Administrator Password: " ADMIN_PASSWORD_CONFIRM
    echo
    [ "$ADMIN_PASSWORD" = "$ADMIN_PASSWORD_CONFIRM" ] && break
    echo "Passwords do not match. Please try again."
done

echo "Configuration complete."

# Clone the repository
echo "Cloning the KWS Control Panel repository..."
git clone https://github.com/karvewebsolutions/Server-Panel-SUper.git /opt/kws-control-panel
cd /opt/kws-control-panel

# Generate secure random values
echo "Generating secure credentials..."
POSTGRES_PASSWORD=$(openssl rand -hex 16)
SECRET_KEY=$(openssl rand -hex 32)
PDNS_API_KEY=$(openssl rand -hex 32)

# Create the .env file
echo "Creating the .env file..."
cat > infra/.env << EOL
# KWS Control Panel Environment Variables

# Domain Configuration
DOMAIN=${DOMAIN}

# Administrator Credentials
ADMIN_EMAIL=${ADMIN_EMAIL}

# PostgreSQL Credentials
POSTGRES_USER=kws
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=kws
DATABASE_URL=postgresql://kws:${POSTGRES_PASSWORD}@postgres:5432/kws

# Backend Secret Key
SECRET_KEY=${SECRET_KEY}

# PowerDNS API Key
PDNS_API_KEY=${PDNS_API_KEY}
EOL

echo ".env file created successfully."

# Start the application
echo "Starting the KWS Control Panel... This may take a few minutes."
cd infra
docker-compose up -d --build

# Wait for the database to be ready
echo "Waiting for the database to be ready..."
until docker-compose exec postgres pg_isready -U kws -d kws -h localhost -p 5432; do
  sleep 2
done

# Create the admin user
echo "Creating the admin user..."
docker-compose exec -T -e ADMIN_PASSWORD=${ADMIN_PASSWORD} backend python /app/scripts/create-admin.py

echo "KWS Control Panel has been installed successfully!"
echo "You can access your control panel at: https://cp.${DOMAIN}"
echo "Your administrator email is: ${ADMIN_EMAIL}"
