#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export OPENCLAW_STATE_DIR="${OPENCLAW_STATE_DIR:-$PWD/.openclaw-state}"
[[ -x node_modules/.bin/openclaw ]] || { echo 'Run scripts/setup.sh first' >&2; exit 1; }
OUT="$(mktemp)"
trap 'rm -f "$OUT"' EXIT
./node_modules/.bin/openclaw agent --local --session-id "arrakis-smoke-$(date +%s)" \
  --model 'openrouter/inclusionai/ling-3.0-flash-sante:free' \
  --message 'Reply with exactly: ARR AKIS LOCAL READY' --timeout 120 --json > "$OUT"
python3 - "$OUT" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]))
assert any(x.get('text','').strip()=='ARR AKIS LOCAL READY' for x in p['payloads']), p['payloads']
assert p['meta']['agentMeta']['provider']=='openrouter'
print('PASS: live OpenRouter agent replied with the expected phrase')
PY
