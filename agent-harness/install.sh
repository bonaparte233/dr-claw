#!/usr/bin/env bash
# install.sh — one-command setup for cli-anything-vibelab
# Creates a symlink in /usr/local/bin so the CLI is available system-wide.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_NAME="vibelab"

echo "==> Installing Python package (editable)..."
pip3 install -e "$SCRIPT_DIR" -q 2>/dev/null || true

# The binary lands in $(python3 -m site --user-base)/bin on macOS user installs
USER_BASE="$(python3 -m site --user-base)"
INSTALLED_BIN="$USER_BASE/bin/$BIN_NAME"

if [ ! -f "$INSTALLED_BIN" ]; then
  echo "ERR Could not find binary at: $INSTALLED_BIN"
  echo "    Try: pip3 install -e $SCRIPT_DIR"
  exit 1
fi

SYMLINK_TARGET="/usr/local/bin/$BIN_NAME"
echo "==> Symlinking $BIN_NAME → /usr/local/bin/"
ln -sf "$INSTALLED_BIN" "$SYMLINK_TARGET" 2>/dev/null \
  || sudo ln -sf "$INSTALLED_BIN" "$SYMLINK_TARGET"

echo ""
echo "✓  Installed!  Try:"
echo "   $BIN_NAME --help"
echo "   $BIN_NAME server on"
echo "   $BIN_NAME server status"
