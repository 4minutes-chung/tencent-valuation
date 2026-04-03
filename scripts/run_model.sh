#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage:
  scripts/run_model.sh [ASOF] [MODE]

Arguments:
  ASOF  As-of date in YYYY-MM-DD format. Default: today.
  MODE  synthetic | auto | live. Default: synthetic.

Examples:
  scripts/run_model.sh 2026-04-03 synthetic
  scripts/run_model.sh 2026-04-03 live
EOF
  exit 0
fi

ASOF="${1:-$(date +%F)}"
MODE="${2:-synthetic}"

if [[ "${MODE}" != "synthetic" && "${MODE}" != "auto" && "${MODE}" != "live" ]]; then
  echo "Error: MODE must be one of: synthetic, auto, live" >&2
  exit 2
fi

if [[ "${MODE}" == "live" || "${MODE}" == "auto" ]]; then
  python -m tencent_valuation_v4 fetch --asof "${ASOF}"
  python -m tencent_valuation_v4 build-overrides --asof "${ASOF}"
fi

python -m tencent_valuation_v4 run-all --asof "${ASOF}" --source-mode "${MODE}" --refresh
