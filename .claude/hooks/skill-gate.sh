#!/usr/bin/env bash
# Stop hook: 스킬(.md)·게이트 스크립트가 변경된 턴은 결정론 게이트
# (check.mjs 정합성+안전규칙 lint, test-receivables.mjs 회귀 테스트)를 통과해야
# 종료된다. 실패 시 exit 2로 에이전트를 다시 깨워 수정을 요구한다.
# agent-harness-kit의 lint-build-check.sh를 마크다운 스킬 리포에 맞게 개조.
cd "${CLAUDE_PROJECT_DIR:-$PWD}" 2>/dev/null || exit 0
[ -f .claude/harness.config.sh ] && . .claude/harness.config.sh
[ -f .claude/hooks/_lib.sh ] && . .claude/hooks/_lib.sh
command -v harness_changed_lines >/dev/null 2>&1 || exit 0
command -v harness_log >/dev/null 2>&1 || harness_log() { :; }
if [ -z "${CODE_FILE_REGEX:-}" ]; then CODE_FILE_REGEX='(^|[/[:space:]])(skills/|scripts/)'; fi

harness_changed_lines | grep -qE "$CODE_FILE_REGEX" || exit 0
# node 없으면 검증 불가 통과. 단 CI는 push 후에야 도는 사후 신호라 배포(main 직푸시=즉시)를
# 막지 못한다 — 이 경로로 통과됐다면 push 전에 수동으로 node scripts/check.mjs를 돌릴 것.
command -v node >/dev/null 2>&1 || exit 0

# 같은 상태를 이미 통과시켰으면 건너뛴다 (키 = HEAD + 실제 diff 내용)
STATE_DIR=".claude/state"
mkdir -p "$STATE_DIR" 2>/dev/null
CACHE="$STATE_DIR/skill-gate-verified"
KEY="$(harness_state_key 2>/dev/null || echo "")"
if [ -n "$KEY" ] && [ -f "$CACHE" ] && [ "$(cat "$CACHE" 2>/dev/null)" = "$KEY" ]; then
  exit 0
fi

fail=""
for cmd in "node scripts/check.mjs" "node scripts/test-receivables.mjs"; do
  out=$(bash -c "$cmd" 2>&1); ec=$?
  if [ "$ec" -ne 0 ]; then fail="[$cmd]"$'\n'"$out"; break; fi
done

if [ -z "$fail" ]; then
  [ -n "$KEY" ] && printf '%s' "$KEY" > "$CACHE"
  harness_retry_clear skill-gate
  harness_log skill-gate Stop pass ""
  exit 0
fi

if harness_retry_exceeded skill-gate "$fail"; then
  {
    echo "⚠️ 스킬 게이트가 ${HARNESS_MAX_RETRY:-3}회 연속 같은 이유로 실패해 통과시킵니다."
    echo "   👉 고치지 말고, 사용자에게 아래 내용을 그대로 보고하세요:"
    echo "$fail" | tail -20
  } >&2
  harness_log skill-gate Stop retry-exceeded "$(echo "$fail" | head -1)"
  exit 0
fi

{
  echo "스킬 게이트 실패 — 아래를 수정한 뒤 다시 종료하세요:"
  echo "$fail" | tail -30
} >&2
harness_log skill-gate Stop block "$(echo "$fail" | head -1)"
exit 2
