#!/usr/bin/env bash
# Shadow Shift 的中央本地开发薄入口。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RUNTIME_ROOT="${SHADOW_LOCAL_DEV_RUNTIME_DIR:-$WORKSPACE_ROOT/shadow-size/merchant-admin}"

if [[ ! -f "$RUNTIME_ROOT/scripts/local-dev/cli.mjs" ]]; then
  printf '[SHIFT-local] 找不到中央本地开发 CLI：%s\n' "$RUNTIME_ROOT/scripts/local-dev/cli.mjs" >&2
  exit 2
fi

cd "$RUNTIME_ROOT"
exec node scripts/local-dev/cli.mjs "$@"
