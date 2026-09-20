#!/bin/sh
# Create deploy/.env from .env.example with generated secrets. Refuses to overwrite an existing file.
set -eu
cd "$(dirname "$0")"
if [ -f .env ]; then
  echo "deploy/.env already exists; not touching it." >&2
  exit 0
fi
gen() { python3 -c "import secrets; print(secrets.token_urlsafe($1))"; }
sed -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(gen 24)|" \
    -e "s|^API_SECRET_KEY=.*|API_SECRET_KEY=$(gen 48)|" \
    -e "s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=$(gen 18)|" \
    -e "s|^SIM_PASSWORD=.*|SIM_PASSWORD=$(gen 18)|" \
    .env.example > .env
chmod 600 .env
echo "deploy/.env created with generated POSTGRES_PASSWORD, API_SECRET_KEY, ADMIN_PASSWORD and SIM_PASSWORD."
echo "Dashboard login: user 'admin', password in deploy/.env (ADMIN_PASSWORD)."
