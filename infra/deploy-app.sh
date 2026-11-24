#!/usr/bin/env bash
# Creates or updates one Container App and prints its public host name.
# Called twice by .github/workflows/deploy.yml (property, then tasks).
#
#   infra/deploy-app.sh <app-name> <image> [EXTRA_VAR=value ...]
#
# Reads from the environment: RESOURCE_GROUP, CONTAINERAPPS_ENV, GIT_SHA, CORS_ORIGIN,
# and the two secrets DATABASE_URL and SECRET_KEY.
set -euo pipefail

app=$1     # e.g. rjpenning-ieu2024-property
image=$2   # e.g. ghcr.io/geulo/pm-property:<sha>
shift 2    # whatever is left ("$@") are extra environment variables, e.g. PROPERTY_URL=https://...

# The secrets are stored in the Container App as secrets (database-url, secret-key) and the
# environment variables only point at them with "secretref:", so they never show as plain values.
env_vars=(
  "DATABASE_URL=secretref:database-url"
  "SECRET_KEY=secretref:secret-key"
  "GIT_SHA=$GIT_SHA"            # /health reports it as "version"
  "CORS_ORIGIN=$CORS_ORIGIN"    # the UI's origin, the only one the browser may call from
  "$@"
)

if az containerapp show -g "$RESOURCE_GROUP" -n "$app" --output none 2>/dev/null; then
  # Exists: refresh the secrets, then switch to the new image. The new GIT_SHA makes a new revision.
  az containerapp secret set -g "$RESOURCE_GROUP" -n "$app" \
    --secrets "database-url=$DATABASE_URL" "secret-key=$SECRET_KEY" --output none
  az containerapp update -g "$RESOURCE_GROUP" -n "$app" --image "$image" \
    --min-replicas 0 --max-replicas 1 --set-env-vars "${env_vars[@]}" --output none
else
  # First deploy: public (external) HTTPS ingress forwarding to port 8000 in the container,
  # scale to zero when idle and never more than one replica. Smallest size: 0.25 vCPU, 0.5 GiB.
  az containerapp create -g "$RESOURCE_GROUP" -n "$app" --environment "$CONTAINERAPPS_ENV" \
    --image "$image" --ingress external --target-port 8000 \
    --min-replicas 0 --max-replicas 1 --cpu 0.25 --memory 0.5Gi \
    --secrets "database-url=$DATABASE_URL" "secret-key=$SECRET_KEY" \
    --env-vars "${env_vars[@]}" --output none
fi

# The app's public host name, e.g. rjpenning-ieu2024-property.<random>.germanywestcentral.azurecontainerapps.io
az containerapp show -g "$RESOURCE_GROUP" -n "$app" --query properties.configuration.ingress.fqdn -o tsv
