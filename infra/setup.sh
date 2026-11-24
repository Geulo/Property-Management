#!/usr/bin/env bash
# One-time Azure setup for Property-Management. Run it yourself, from the repo root:
#
#   az login                      # sign in to Azure (Azure for Students)
#   gh auth login                 # sign in to GitHub as the repo owner
#   brew install sqlcmd           # SQL Server command-line tool (used to create the database users)
#   bash infra/setup.sh
#
# It creates everything that exists once (resource group, SQL server, databases, Container Apps
# environment, the UI's storage account, the deploy identity) and stores every secret straight
# into GitHub Actions secrets with `gh secret set`, so no password is printed or written to a file.
# The two Container Apps themselves are created by .github/workflows/deploy.yml on the first deploy.
#
# Safe to run again: each step either checks first or is an "update if it exists" call.
# A re-run generates NEW database passwords and a new SECRET_KEY and stores them in GitHub,
# so re-run the Deploy workflow afterwards to give the running apps the new values.

set -euo pipefail   # stop at the first failing command, unset variable, or failing pipe

# ---------------------------------------------------------------------------------------------
# Names. PREFIX is the IE username (rjpenning.ieu2024 -> rjpenning-ieu2024); override with
# PREFIX=... bash infra/setup.sh. The same names are written at the top of deploy.yml.
# ---------------------------------------------------------------------------------------------
PREFIX="${PREFIX:-rjpenning-ieu2024}"
LOCATION="${LOCATION:-germanywestcentral}"     # checked against the region policy below
REPO="Geulo/Property-Management"

RG="$PREFIX-rg"                      # resource group: one box holding everything, deleted as one
SQL_SERVER="$PREFIX-sql"             # logical SQL server (just a name + admin login, no cost by itself)
PROPERTY_DB="$PREFIX-property-db"    # database of the property service
TASKS_DB="$PREFIX-tasks-db"          # database of the tasks service
ENV_NAME="$PREFIX-env"               # Container Apps environment both apps run in
LOGS="$PREFIX-logs"                  # Log Analytics workspace: where the apps' stdout lines end up
STORAGE="${PREFIX//-/}ui"            # storage account for the UI; only lowercase letters and digits allowed
IDENTITY="$PREFIX-deploy"            # identity the GitHub workflow logs in as
SQL_ADMIN="pmadmin"                  # SQL admin login name (its password is generated below)

# ---------------------------------------------------------------------------------------------
# 0. Checks before creating anything
# ---------------------------------------------------------------------------------------------
for tool in az gh sqlcmd openssl curl; do
  command -v "$tool" >/dev/null || { echo "Missing tool: $tool (see the top of this file)"; exit 1; }
done
gh auth status >/dev/null || { echo "Run 'gh auth login' first"; exit 1; }

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
echo "Subscription: $(az account show --query name -o tsv) ($SUBSCRIPTION_ID)"

# Azure for Students only allows a few regions (policy "Allowed resource deployment regions").
# Print that list and stop if LOCATION is not on it.
ALLOWED=$(az policy assignment list \
  --query "[?displayName=='Allowed resource deployment regions'].parameters.listOfAllowedLocations.value[]" -o tsv)
echo "Regions this subscription allows: $(echo $ALLOWED)"
if [ -n "$ALLOWED" ] && ! echo "$ALLOWED" | grep -qx "$LOCATION"; then
  echo "$LOCATION is not allowed here; rerun with LOCATION=<one of the above>"; exit 1
fi
# Note: Static Web Apps only exist in centralus, eastus2, westus2, westeurope and eastasia, none of
# which this policy allows. So the UI goes to an Azure Storage static website instead (step 5).

# Resource providers must be registered once per subscription before their resources can be created.
for provider in Microsoft.Sql Microsoft.App Microsoft.OperationalInsights Microsoft.Storage Microsoft.ManagedIdentity; do
  az provider register --namespace "$provider" --wait
done
az extension add --name containerapp --upgrade --yes --only-show-errors   # the `az containerapp` commands

# Random passwords: 24 letters/digits from a secure source, plus "aA1" so Azure's complexity rule
# (3 of: upper, lower, digit, symbol) always holds. Letters/digits only, so they are safe inside a URL.
new_password() { echo "$(openssl rand -base64 48 | tr -dc 'A-Za-z0-9' | head -c 24)aA1"; }

# ---------------------------------------------------------------------------------------------
# 1. Resource group
# ---------------------------------------------------------------------------------------------
az group create --name "$RG" --location "$LOCATION" --output none
echo "Resource group $RG ready"

# ---------------------------------------------------------------------------------------------
# 2. SQL server with SQL authentication, and its firewall
# ---------------------------------------------------------------------------------------------
# Creating the server with an admin login + password turns SQL authentication on. (A server with
# only Microsoft Entra authentication rejects the password logins the services use.)
# The admin password is only used during this run, never stored; reset it any time with
# `az sql server update -g $RG -n $SQL_SERVER --admin-password ...`.
SQL_ADMIN_PASSWORD=$(new_password)
if az sql server show -g "$RG" -n "$SQL_SERVER" --output none 2>/dev/null; then
  az sql server update -g "$RG" -n "$SQL_SERVER" --admin-password "$SQL_ADMIN_PASSWORD" --output none
else
  az sql server create -g "$RG" -n "$SQL_SERVER" -l "$LOCATION" \
    --admin-user "$SQL_ADMIN" --admin-password "$SQL_ADMIN_PASSWORD" --output none
fi
echo "SQL server $SQL_SERVER ready"

# "Allow Azure services": the special rule 0.0.0.0-0.0.0.0 lets traffic from inside Azure (the
# Container Apps) reach the server. Everything else on the internet stays blocked.
az sql server firewall-rule create -g "$RG" -s "$SQL_SERVER" -n AllowAzureServices \
  --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0 --output none

# A temporary rule for this laptop's public IP, so sqlcmd in step 3 can connect. Removed on exit.
MY_IP=$(curl -s https://api.ipify.org)
az sql server firewall-rule create -g "$RG" -s "$SQL_SERVER" -n setup-script-client \
  --start-ip-address "$MY_IP" --end-ip-address "$MY_IP" --output none
trap 'az sql server firewall-rule delete -g "$RG" -s "$SQL_SERVER" -n setup-script-client --output none' EXIT

# ---------------------------------------------------------------------------------------------
# 3. One serverless database per service, each with its own user
# ---------------------------------------------------------------------------------------------
# GeneralPurpose serverless Gen5: scales between 0.5 and 1 vCore, pauses after 15 minutes without
# connections (the shortest delay allowed) so an idle database costs only storage; 2 GB max size;
# backups kept locally redundant (LRS, the cheapest).
create_database() {
  local db=$1
  if ! az sql db show -g "$RG" -s "$SQL_SERVER" -n "$db" --output none 2>/dev/null; then
    az sql db create -g "$RG" -s "$SQL_SERVER" -n "$db" \
      --edition GeneralPurpose --compute-model Serverless --family Gen5 \
      --min-capacity 0.5 --capacity 1 --auto-pause-delay 15 \
      --max-size 2GB --backup-storage-redundancy Local --output none
  fi
  echo "Database $db ready"
}

# Creates the database user for one service (infra/create-db-user.sql) and returns its
# DATABASE_URL, in the same mssql://user:password@host:port/database form the services read locally.
create_db_user() {
  local db=$1 user=$2 password
  password=$(new_password)
  # sqlcmd reads APP_USER / APP_PASSWORD from the environment as $(APP_USER) / $(APP_PASSWORD);
  # SQLCMDPASSWORD is the admin password. -b stops on the first SQL error.
  APP_USER="$user" APP_PASSWORD="$password" SQLCMDPASSWORD="$SQL_ADMIN_PASSWORD" \
    sqlcmd -S "tcp:$SQL_SERVER.database.windows.net,1433" -d "$db" -U "$SQL_ADMIN" -b \
    -i "$(dirname "$0")/create-db-user.sql" >&2
  echo "mssql://$user:$password@$SQL_SERVER.database.windows.net:1433/$db"
}

create_database "$PROPERTY_DB"
create_database "$TASKS_DB"
# A freshly created database may still be starting; give it a moment before connecting.
sleep 20
PROPERTY_DATABASE_URL=$(create_db_user "$PROPERTY_DB" property_app)
TASKS_DATABASE_URL=$(create_db_user "$TASKS_DB" tasks_app)
echo "Database users property_app and tasks_app ready (each sees only its own database)"

# ---------------------------------------------------------------------------------------------
# 4. Container Apps environment (Consumption plan: pay per request/second, nothing when idle)
# ---------------------------------------------------------------------------------------------
az monitor log-analytics workspace create -g "$RG" -n "$LOGS" -l "$LOCATION" \
  --retention-time 30 --output none
if ! az containerapp env show -g "$RG" -n "$ENV_NAME" --output none 2>/dev/null; then
  LOGS_ID=$(az monitor log-analytics workspace show -g "$RG" -n "$LOGS" --query customerId -o tsv)
  LOGS_KEY=$(az monitor log-analytics workspace get-shared-keys -g "$RG" -n "$LOGS" --query primarySharedKey -o tsv)
  # --enable-workload-profiles false = a Consumption-only environment (no dedicated machines)
  az containerapp env create -g "$RG" -n "$ENV_NAME" -l "$LOCATION" \
    --enable-workload-profiles false \
    --logs-workspace-id "$LOGS_ID" --logs-workspace-key "$LOGS_KEY" --output none
fi
echo "Container Apps environment $ENV_NAME ready"

# ---------------------------------------------------------------------------------------------
# 5. Storage account serving the UI as a static website (stand-in for a Static Web App, see step 0)
# ---------------------------------------------------------------------------------------------
az storage account create -g "$RG" -n "$STORAGE" -l "$LOCATION" \
  --sku Standard_LRS --kind StorageV2 --min-tls-version TLS1_2 --allow-blob-public-access false --output none
# Turns on the $web container, served at https://<account>.z<n>.web.core.windows.net/ (the website
# is public even though blob public access is off). --auth-mode key: the CLI fetches the account key
# for this one call, because an Owner has no data-plane rights by default.
az storage blob service-properties update --account-name "$STORAGE" --auth-mode key \
  --static-website --index-document index.html --404-document index.html --output none
UI_URL=$(az storage account show -g "$RG" -n "$STORAGE" --query primaryEndpoints.web -o tsv)
echo "UI storage $STORAGE ready at $UI_URL"

# ---------------------------------------------------------------------------------------------
# 6. Identity for GitHub Actions (OpenID Connect, no stored Azure password)
# ---------------------------------------------------------------------------------------------
# The IE tenant does not let students create app registrations, so instead of an `az ad sp` service
# principal this is a user-assigned managed identity. It works the same for azure/login@v2.
az identity create -g "$RG" -n "$IDENTITY" -l "$LOCATION" --output none
CLIENT_ID=$(az identity show -g "$RG" -n "$IDENTITY" --query clientId -o tsv)
PRINCIPAL_ID=$(az identity show -g "$RG" -n "$IDENTITY" --query principalId -o tsv)

# Federated credential: Azure trusts a GitHub token only if its subject matches exactly.
# This repo uses GitHub's immutable subject format (owner and repo with their numeric IDs), so ask
# GitHub for the prefix rather than typing it. Only workflow runs on main get this subject.
SUBJECT_PREFIX=$(gh api "repos/$REPO/actions/oidc/customization/sub" --jq '.sub_claim_prefix // empty')
SUBJECT_PREFIX="${SUBJECT_PREFIX:-repo:$REPO}"
az identity federated-credential create -g "$RG" --identity-name "$IDENTITY" -n github-main \
  --issuer https://token.actions.githubusercontent.com \
  --subject "$SUBJECT_PREFIX:ref:refs/heads/main" \
  --audiences api://AzureADTokenExchange --output none

# Permissions: Contributor on this resource group only (create/update the Container Apps), and
# Storage Blob Data Contributor on the UI storage account only (upload the UI files).
# The role assignment may fail for a few seconds while the new identity spreads; retry a few times.
assign_role() {
  for attempt in 1 2 3 4 5 6; do
    az role assignment create --assignee-object-id "$PRINCIPAL_ID" --assignee-principal-type ServicePrincipal \
      --role "$1" --scope "$2" --output none 2>/dev/null && return 0
    sleep 10
  done
  echo "Could not assign role $1"; return 1
}
assign_role Contributor "$(az group show -n "$RG" --query id -o tsv)"
assign_role "Storage Blob Data Contributor" "$(az storage account show -g "$RG" -n "$STORAGE" --query id -o tsv)"
echo "Deploy identity $IDENTITY ready"

# ---------------------------------------------------------------------------------------------
# 7. GitHub Actions secrets, set directly (values never shown)
# ---------------------------------------------------------------------------------------------
gh secret set AZURE_CLIENT_ID       --repo "$REPO" --body "$CLIENT_ID"
gh secret set AZURE_TENANT_ID       --repo "$REPO" --body "$TENANT_ID"
gh secret set AZURE_SUBSCRIPTION_ID --repo "$REPO" --body "$SUBSCRIPTION_ID"
gh secret set PROPERTY_DATABASE_URL --repo "$REPO" --body "$PROPERTY_DATABASE_URL"
gh secret set TASKS_DATABASE_URL    --repo "$REPO" --body "$TASKS_DATABASE_URL"
# Signs login tokens; both services share it so tasks can read tokens issued by property.
gh secret set SECRET_KEY            --repo "$REPO" --body "$(openssl rand -hex 32)"

echo
echo "Done. Region: $LOCATION. UI: $UI_URL"
echo "GitHub secrets set: AZURE_CLIENT_ID AZURE_TENANT_ID AZURE_SUBSCRIPTION_ID PROPERTY_DATABASE_URL TASKS_DATABASE_URL SECRET_KEY"
echo "Check that ghcr.io/geulo/pm-property and pm-tasks are public (GitHub > Packages > settings)."
