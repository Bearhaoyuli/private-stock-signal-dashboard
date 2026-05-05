#!/usr/bin/env bash

set -euo pipefail

REPO="${1:-Bearhaoyuli/private-stock-signal-dashboard}"
ENV_FILE="${2:-.env}"

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is required."
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Env file not found: $ENV_FILE"
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

required_vars=(
  NEXT_PUBLIC_SUPABASE_URL
  NEXT_PUBLIC_SUPABASE_ANON_KEY
  NEXT_PUBLIC_ALLOWED_USER_EMAIL
)

optional_vars=(
  NEXT_PUBLIC_API_BASE_URL
)

for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    echo "Missing required env var: $var_name"
    exit 1
  fi
done

for var_name in "${required_vars[@]}"; do
  printf '%s' "${!var_name}" | gh secret set "$var_name" -R "$REPO"
done

for var_name in "${optional_vars[@]}"; do
  if [[ -n "${!var_name:-}" ]]; then
    printf '%s' "${!var_name}" | gh secret set "$var_name" -R "$REPO"
  fi
done

echo "Repository secrets updated for $REPO"

