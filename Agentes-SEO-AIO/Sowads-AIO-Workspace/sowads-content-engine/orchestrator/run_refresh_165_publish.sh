#!/usr/bin/env sh
set -eu

# Refresh publish (165 posts) with latest sanitizer adjustments.
# Required env vars:
#   WP_SSH_HOST
#   WP_SSH_PORT
#   WP_SSH_USER
#   WP_SSH_PASSWORD
#   WP_SSH_WP_PATH

BASE_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

: "${WP_SSH_HOST:?missing WP_SSH_HOST}"
: "${WP_SSH_PORT:?missing WP_SSH_PORT}"
: "${WP_SSH_USER:?missing WP_SSH_USER}"
: "${WP_SSH_PASSWORD:?missing WP_SSH_PASSWORD}"
: "${WP_SSH_WP_PATH:?missing WP_SSH_WP_PATH}"

python3 "$BASE_DIR/orchestrator/publish_wp_cli.py" \
  --base "$BASE_DIR" \
  --status publish \
  --articles-csv "$BASE_DIR/outputs/articles/PUBLISH-refresh-165-visual.csv" \
  --include-statuses APPROVED,PENDING_QA,REJECTED \
  --skip-audit-gate \
  --ssh-host "$WP_SSH_HOST" \
  --ssh-port "$WP_SSH_PORT" \
  --ssh-user "$WP_SSH_USER" \
  --ssh-password "$WP_SSH_PASSWORD" \
  --wp-path "$WP_SSH_WP_PATH"
