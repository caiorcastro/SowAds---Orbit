#!/usr/bin/env sh
set -eu

BASE_DEFAULT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
BASE="${1:-$BASE_DEFAULT}"
INTERVAL="${2:-5}"
BATCH_ID="${3:-}"

if [ -n "$BATCH_ID" ]; then
  BATCH_ARG="--batch-id $BATCH_ID"
else
  BATCH_ARG=""
fi

while :; do
  clear
  echo "SOWADS Agent Monitor (interval ${INTERVAL}s)"
  echo "Base: $BASE"
  echo "Batch: ${BATCH_ID:-latest}"
  echo ""
  # shellcheck disable=SC2086
  python3 "$(dirname -- "$0")/agent_status.py" --base "$BASE" $BATCH_ARG --format table
  sleep "$INTERVAL"
done

