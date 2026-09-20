#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
cd "$(dirname "$0")/.."
# 사전 점검 — 번들은 아직 만들기 전이므로 번들 검사만 건너뛴다.
node scripts/check.mjs --prebuild
node scripts/test-receivables.mjs
# 사전 게이트에서는 번들 대조만 건너뛴다 — 아직 번들을 만들기 전이라 필연 실패한다(§14 순환 잠금).
python3 -B scripts/test-free-release.py --prebuild
python3 -B scripts/build_packages.py
python3 -B scripts/release-readiness.py --write-manifest --directory ..
# 방금 만든 번들로 다시 — 이번엔 번들↔원본 대조까지 한다.
python3 -B scripts/test-free-release.py
python3 -B scripts/test-release-readiness.py
# 최종 검증 — 이번엔 번들 내용까지 원본과 대조한다.
node scripts/check.mjs
