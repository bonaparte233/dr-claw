#!/bin/sh
set -eu

LOCK_DIR="${HOME}/.openclaw/locks"
DEFAULT_AGENT="${OPENCLAW_VIBELAB_AGENT:-vibetest2}"
AGENT="$DEFAULT_AGENT"

mkdir -p "$LOCK_DIR"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --agent)
      AGENT="$2"
      shift 2
      ;;
    *)
      break
      ;;
  esac
done

LOCK_FILE="$LOCK_DIR/openclaw-local-${AGENT}.lock"
cleanup() {
  rm -f "$LOCK_FILE"
}
trap cleanup EXIT INT TERM HUP

while ! /usr/bin/shlock -p "$$" -f "$LOCK_FILE" >/dev/null 2>&1; do
  sleep 1
done

exec openclaw agent --local --agent "$AGENT" "$@"
