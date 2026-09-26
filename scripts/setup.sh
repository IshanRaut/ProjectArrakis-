#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if ! node -e 'let [M,m]=process.versions.node.split(".").map(Number);process.exit(+!((M===24&&m>=16)||(M===26&&m>=1)||M>26))'; then
  echo 'Node >=24.16 or >=26.1 required. Install a supported Node release first.' >&2; exit 1
fi
if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
  echo 'Set OPENROUTER_API_KEY in your shell (never commit it).' >&2; exit 1
fi
export OPENCLAW_STATE_DIR="${OPENCLAW_STATE_DIR:-$PWD/.openclaw-state}"
mkdir -p "$OPENCLAW_STATE_DIR"
chmod 700 "$OPENCLAW_STATE_DIR"
npm ci --no-audit --no-fund
./node_modules/.bin/openclaw onboard --non-interactive --accept-risk --mode local \
  --auth-choice openrouter-api-key --openrouter-api-key "$OPENROUTER_API_KEY" \
  --workspace "$PWD/workspace" --skip-channels --skip-daemon --skip-ui \
  --skip-skills --skip-health
./node_modules/.bin/openclaw models set 'openrouter/inclusionai/ling-3.0-flash-sante:free'
./node_modules/.bin/openclaw config set tools.profile minimal
printf '\nSetup complete. No channel or public gateway is enabled. Run npm run smoke.\n'
