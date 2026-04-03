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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  echo "Error: no python interpreter found (python/python3/.venv/bin/python)." >&2
  exit 127
fi

if [[ "${MODE}" != "synthetic" && "${MODE}" != "auto" && "${MODE}" != "live" ]]; then
  echo "Error: MODE must be one of: synthetic, auto, live" >&2
  exit 2
fi

export PYTHONPATH="${ROOT_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

if [[ "${MODE}" == "live" || "${MODE}" == "auto" ]]; then
  "${PYTHON_BIN}" -m tencent_valuation_v4 fetch --asof "${ASOF}"
  "${PYTHON_BIN}" -m tencent_valuation_v4 build-overrides --asof "${ASOF}"
fi

"${PYTHON_BIN}" -m tencent_valuation_v4 run-all --asof "${ASOF}" --source-mode "${MODE}" --refresh
