#!/usr/bin/env bash
# Stop hook: 코드 변경이 있는데 적대적 리뷰 영수증이 없으면 막는다.
#
# "작업 완료 후 보고 전 — 항상 리뷰"는 지금까지 문서 글씨로만 있었고, 검증 장치가
# 없었다. 이 게이트는 리뷰 실행이 남긴 영수증(scripts/harness-review-receipt.sh)의
# 상태 키가 지금 코드 상태와 일치할 때만 통과시킨다. 코드가 더 바뀌면 그 영수증은
# 자동으로 무효가 되어 재검토를 요구한다.
#
# 설정 (harness.config.sh):
#   REVIEW_GATE="off"   — 사용 안 함 (기본)
#   REVIEW_GATE="warn"  — 없으면 경고만 하고 통과
#   REVIEW_GATE="block" — 없으면 exit 2로 차단
#   REVIEW_GATE_MIN_FILES — 변경 파일이 이 개수 이상이면 리뷰를 요구한다 (기본 1 = 한 파일만 바뀌어도 요구)
#
# 도입은 warn → block 2단계를 권한다. 처음부터 block으로 두면 리뷰 습관이
# 생기기 전에 게이트가 먼저 미움받는다.
cd "${CLAUDE_PROJECT_DIR:-$PWD}" 2>/dev/null || exit 0
[ -f .claude/harness.config.sh ] && . .claude/harness.config.sh
[ -f .claude/hooks/_lib.sh ] && . .claude/hooks/_lib.sh
command -v harness_changed_lines >/dev/null 2>&1 || exit 0
command -v harness_log >/dev/null 2>&1 || harness_log() { :; }

MODE="${REVIEW_GATE:-off}"
[ "$MODE" = "off" ] && exit 0

if [ -z "${CODE_FILE_REGEX:-}" ]; then CODE_FILE_REGEX='\.(ts|tsx|js|jsx|mjs|cjs)$'; fi
MIN_FILES="${REVIEW_GATE_MIN_FILES:-1}"

changed="$(harness_changed_lines | grep -cE "$CODE_FILE_REGEX" || true)"
[ "${changed:-0}" -ge "$MIN_FILES" ] || exit 0

KEY="$(harness_state_key 2>/dev/null || echo "")"
[ -n "$KEY" ] || exit 0

# 지금 상태에 대한 영수증이 있는가
if ls ".claude/state/reviews/"*"-$KEY.json" >/dev/null 2>&1; then
  exit 0
fi

# 예전 영수증이 있다면 "코드가 바뀌어 무효"임을 알려준다 (처음부터 안 받은 것과 구분)
prev="$(ls -1 .claude/state/reviews/*.json 2>/dev/null | wc -l | tr -d ' ')"
if [ "${prev:-0}" -gt 0 ]; then
  detail="이전 리뷰 이후 코드가 바뀌어 그 영수증은 무효입니다(${prev}건 보관)."
else
  detail="이 브랜치에서 아직 적대적 리뷰를 받은 기록이 없습니다."
fi

msg="$(cat <<EOF
적대적 리뷰가 필요합니다 — $detail
  변경된 파일 약 ${changed}개.

  1) 독립 리뷰어에게 결과물 반박을 시켜라 — 이 리포에 동봉된
     .claude/agents/adversarial-reviewer.md 서브에이전트를 사용
     (codex CLI가 있으면 codex read-only 리뷰가 더 강하다)
  2) 리뷰어 원문을 영수증으로 남겨라 — 방법은 CLAUDE.md '리뷰 영수증' 절 참조
  3) Critical/High를 반영한 뒤 다시 종료하라

  리뷰어를 어떤 경로로도 부를 수 없는 환경이면, 게이트 설정을 임의로 낮추지 말고
  차단 사실을 사용자에게 그대로 보고하고 지시를 받아라.
EOF
)"

if [ "$MODE" = "block" ]; then
  printf '%s\n' "$msg" >&2
  harness_log review-gate Stop block "영수증 없음 (변경 ${changed}건)"
  exit 2
fi

printf '⚠️ %s\n' "$msg" >&2
harness_log review-gate Stop warn "영수증 없음 (변경 ${changed}건)"
exit 0
