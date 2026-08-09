#!/usr/bin/env bash
# harness-review-receipt — 적대적 리뷰를 실제로 받았다는 영수증을 남긴다.
#
# 왜 이런 방식인가:
#   "완료 전 항상 리뷰받아라"는 지금까지 문서 글씨로만 있었다. 컨텍스트가 길고
#   자기 결과에 자신 있을수록 생략되는데, 그게 정확히 확증 편향이 가장 심한
#   순간이다. 그렇다고 에이전트가 "리뷰했습니다"라고 쓰게 하면 자기증명이라
#   아무 의미가 없다.
#   그래서 **리뷰 실행 자체가 부산물을 남기게** 한다. 리뷰어의 원문을 stdin으로
#   받아 저장하고, 그 시점의 코드 상태 키를 함께 기록한다. 게이트는 그 키가
#   지금 상태와 일치할 때만 통과시킨다.
#
# 한계(정직하게): 작정하고 위조하는 것은 막지 못한다. "깜빡함"과 "귀찮아서
#   건너뜀"을 막는 장치다. 고의에 대한 방어는 사람 리뷰와 서버측 규칙의 몫이다.
#
# 사용: <리뷰어 원문> | bash scripts/harness-review-receipt.sh <codex|subagent> [메모]
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"
cd "$ROOT" || exit 1
[ -f .claude/harness.config.sh ] && . .claude/harness.config.sh
[ -f .claude/hooks/_lib.sh ] && . .claude/hooks/_lib.sh

REVIEWER="${1:-unknown}"
NOTE="${2:-}"
MIN_BYTES="${REVIEW_MIN_BYTES:-40}"

body="$(cat)"
bytes="$(printf '%s' "$body" | wc -c | tr -d ' ')"

if [ "${bytes:-0}" -lt "$MIN_BYTES" ]; then
  {
    echo "✗ 리뷰 원문이 너무 짧습니다 (${bytes}바이트 < ${MIN_BYTES})."
    echo "  빈 리뷰는 영수증으로 인정하지 않습니다 — 리뷰어의 실제 출력을 그대로 넘기세요."
    echo "  예: codex exec --sandbox read-only \"...\" </dev/null | bash scripts/harness-review-receipt.sh codex"
  } >&2
  exit 1
fi

if ! command -v harness_state_key >/dev/null 2>&1; then
  echo "✗ .claude/hooks/_lib.sh 가 없어 코드 상태 키를 계산할 수 없습니다." >&2
  exit 1
fi

KEY="$(harness_state_key 2>/dev/null || echo "")"
[ -n "$KEY" ] || { echo "✗ 코드 상태 키를 계산하지 못했습니다." >&2; exit 1; }

DIR=".claude/state/reviews"
mkdir -p "$DIR" 2>/dev/null || { echo "✗ $DIR 를 만들 수 없습니다." >&2; exit 1; }

TS="$(date +%Y%m%d-%H%M%S)"
BASE="$DIR/$TS-$KEY"
printf '%s\n' "$body" > "$BASE.md"

FILES="$(harness_changed_lines 2>/dev/null | wc -l | tr -d ' ')"
BRANCH="$(git branch --show-current 2>/dev/null || echo '')"
STRENGTH="strong"
[ "$REVIEWER" = "subagent" ] && STRENGTH="weak"   # 같은 모델 — 컨텍스트만 분리됨

if command -v jq >/dev/null 2>&1; then
  jq -n --arg k "$KEY" --arg r "$REVIEWER" --arg s "$STRENGTH" --arg b "$BRANCH" \
        --arg t "$(date +%Y-%m-%dT%H:%M:%S%z)" --arg n "$NOTE" \
        --argjson by "$bytes" --argjson f "${FILES:-0}" \
    '{state_key:$k, reviewer:$r, evidence_strength:$s, branch:$b, ts:$t,
      review_bytes:$by, changed_files:$f, note:$n}' > "$BASE.json"
else
  printf '{"state_key":"%s","reviewer":"%s","evidence_strength":"%s","branch":"%s","review_bytes":%s}\n' \
    "$KEY" "$REVIEWER" "$STRENGTH" "$BRANCH" "$bytes" > "$BASE.json"
fi

command -v harness_log >/dev/null 2>&1 && \
  harness_log review-receipt manual recorded "$REVIEWER ${bytes}B"

echo "✓ 리뷰 영수증 기록: $BASE.json"
echo "  리뷰어=$REVIEWER (증거 강도: $STRENGTH) · 원문 ${bytes}바이트 · 상태키 $KEY"
[ "$STRENGTH" = "weak" ] && \
  echo "  ⚠ 서브에이전트는 같은 모델이라 같은 맹점을 공유할 수 있습니다. codex CLI가 있으면 그쪽이 낫습니다."
exit 0
