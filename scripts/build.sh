#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
cd "$(dirname "$0")/.."
# 사전 점검 — 번들은 아직 만들기 전이므로 번들 검사만 건너뛴다.
node scripts/check.mjs --prebuild
node scripts/test-receivables.mjs
python3 -B scripts/test-free-release.py
python3 -B scripts/build_packages.py
# 최종 검증 — 이번엔 번들 내용까지 원본과 대조한다.
node scripts/check.mjs
