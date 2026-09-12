#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# hook 공용 함수 — 각 hook이 `cd "$CLAUDE_PROJECT_DIR"` 직후 source한다.
# .githooks/pre-push·pre-commit도 repo 루트에서 이 파일을 source한다.
# ─────────────────────────────────────────────────────────────────────

# ── 변경된 파일 목록을 한 줄에 하나씩 출력한다.
#
# `git status --porcelain`을 그대로 쓰면 안 되는 이유(둘 다 실측 확인됨):
#   1. 미추적 디렉토리를 "?? src/"로 접어버린다 → 새 폴더에 만든 코드가 통째로 안 보임
#   2. 한글·공백이 든 경로를 "src/한글.ts"처럼 따옴표로 감싼다 → 줄 끝 앵커($) 정규식이 실패
# -uall이 1번을, -z가 2번을 해결한다. -z 출력은 NUL 구분이므로 개행으로 바꿔 넘긴다.
#
# 주의: 각 줄은 " M src/a.ts"처럼 상태 표시가 앞에 붙는다(rename의 옛 경로만 예외).
# 따라서 이 출력에 쓰는 정규식은 앞 경계를 `(^|[/[:space:]])`로 잡아야 한다.
harness_changed_lines() {
  git status --porcelain -z -uall 2>/dev/null | tr '\0' '\n'
  # LINT_SCOPE=branch(기본)이면 "이번 브랜치에서 커밋한 것"까지 포함한다.
  #
  # 왜: 미커밋 변경만 보면, CLAUDE.md가 지시하는 정상 흐름("commit & push까지 하고
  # 끝내라")을 따를수록 게이트를 피해 간다. 실측으로 확인된 구멍이다.
  # worktree로 두면 예전 동작(미커밋만), turn은 현재는 branch와 같게 취급한다.
  case "${LINT_SCOPE:-branch}" in
    worktree) return 0 ;;
  esac
  local base
  base="$(harness_branch_base)" || return 0
  [ -n "$base" ] || return 0
  git diff --name-only -z "$base"...HEAD 2>/dev/null | tr '\0' '\n'
}

# 이번 브랜치가 갈라져 나온 지점을 찾는다. 못 찾으면 빈 문자열(= 워킹트리만 검사).
harness_branch_base() {
  local mb ref
  for ref in "${MAIN_BRANCH:-}" origin/"${MAIN_BRANCH:-}" main origin/main master origin/master; do
    [ -n "$ref" ] || continue
    git rev-parse --verify --quiet "$ref" >/dev/null 2>&1 || continue
    mb="$(git merge-base "$ref" HEAD 2>/dev/null)" || continue
    # 기준 브랜치 위에 그대로 있으면 비교할 커밋이 없다
    [ "$mb" = "$(git rev-parse HEAD 2>/dev/null)" ] && continue
    printf '%s' "$mb"; return 0
  done
  printf ''
}

# ── 같은 상태를 매 턴 다시 빌드하지 않기 위한 캐시 키.
#
# 파일 "목록"만으로 키를 만들면 안 된다 — 같은 파일의 내용만 고친 턴에서 키가
# 그대로라 캐시가 잘못 적중한다. 내용까지 넣는다:
#   HEAD sha(커밋된 변경) + 추적 파일의 실제 diff + 미추적 파일의 목록과 내용
harness_state_key() {
  {
    git rev-parse HEAD 2>/dev/null || echo none
    git diff --binary HEAD 2>/dev/null
    git ls-files --others --exclude-standard -z 2>/dev/null | tr '\0' '\n' | sort
    # GNU xargs는 빈 입력에도 명령을 1회 실행 → 인자 없는 cat이 훅 stdin(JSON)을 읽어
    # 키를 오염시킨다(Linux 데드락, 2026-08-09 하네스 리뷰 H-2). </dev/null로 차단.
    git ls-files --others --exclude-standard -z 2>/dev/null | xargs -0 sh -c 'cat -- "$@" </dev/null' _ 2>/dev/null
  } | cksum | awk '{print $1}'
}

# ── lockfile 동기화 검증 명령을 결정해 출력한다 (없으면 빈 문자열).
#
# 예전 킷은 pnpm 명령을 하드코딩해서, npm 프로젝트에 설치하면
#   - packageManager 필드가 없으면 → 모든 push가 영구 차단
#   - packageManager: npm@… 이면 → `npm install --frozen-lockfile`이 어긋나도 rc=0 (가드 무의미)
# 이 되었다. 둘 다 실측 확인된 파손이라, 락파일 종류로 자동 판별한다.
#
# 공통 요건: (a) 어긋나면 비-0으로 실패 (b) node_modules를 건드리지 않음
#            (c) 실패해도 락파일을 몰래 갱신하지 않음
# 프로젝트가 직접 지정하려면 harness.config.sh의 LOCKFILE_CHECK_CMD를 채운다.
harness_lockfile_cmd() {
  if [ -n "${LOCKFILE_CHECK_CMD:-}" ]; then printf '%s' "$LOCKFILE_CHECK_CMD"; return 0; fi

  if [ -f pnpm-lock.yaml ]; then
    # 프로젝트가 고정한 pnpm 버전을 corepack으로 사용 (로컬 전역 버전 무관)
    local pm; pm="$(node -p "require('./package.json').packageManager || ''" 2>/dev/null || echo '')"
    case "$pm" in
      pnpm@*) command -v corepack >/dev/null 2>&1 \
                && printf 'corepack %s install --frozen-lockfile --lockfile-only --ignore-scripts' "$pm" \
                || printf 'pnpm install --frozen-lockfile --lockfile-only --ignore-scripts' ;;
      *)      printf 'pnpm install --frozen-lockfile --lockfile-only --ignore-scripts' ;;
    esac
  elif [ -f package-lock.json ]; then
    printf 'npm ci --ignore-scripts --dry-run'
  elif [ -f yarn.lock ]; then
    # yarn 4(berry). yarn 1(classic)이면 `yarn install --frozen-lockfile`로 바꿔야 하므로
    # classic 프로젝트는 LOCKFILE_CHECK_CMD로 직접 지정할 것.
    printf 'yarn install --immutable --mode=skip-build'
  elif [ -f bun.lockb ] || [ -f bun.lock ]; then
    printf 'bun install --frozen-lockfile --dry-run'
  else
    printf ''
  fi
}

# ── 검증 명령의 실행 파일이 실제로 있는지 (없으면 검증 불가 → 통과시켜야 함)
harness_cmd_available() {
  local first; first="$(printf '%s' "$1" | awk '{print $1}')"
  [ -n "$first" ] && command -v "$first" >/dev/null 2>&1
}

# ── 무한 재작업 루프 차단
#
# Stop hook이 exit 2로 턴 종료를 막으면 에이전트가 다시 깨어나 수정을 시도한다.
# 그런데 이번 작업과 무관한 기존 lint 에러가 하나라도 있으면 아무리 고쳐도 실패가
# 반복되어 영원히 끝나지 않는다. 같은 실패가 HARNESS_MAX_RETRY회 연속되면
# 게이트를 통과시키고, 대신 "사용자에게 보고하라"고 지시한다.
#
# harness_retry_exceeded <키> <실패내용>  → 0이면 한도 초과(통과시켜야 함)
harness_retry_exceeded() {
  local key="$1" payload="$2" dir=".claude/state" f h prev_h prev_n
  mkdir -p "$dir" 2>/dev/null || return 1
  f="$dir/stop-retry-$key"
  h="$(printf '%s' "$payload" | cksum | awk '{print $1}')"
  if [ -f "$f" ]; then read -r prev_h prev_n < "$f" 2>/dev/null; fi
  [ -n "${prev_n:-}" ] || prev_n=0
  if [ "$h" = "${prev_h:-}" ]; then prev_n=$((prev_n + 1)); else prev_n=1; fi
  printf '%s %s\n' "$h" "$prev_n" > "$f"
  [ "$prev_n" -ge "${HARNESS_MAX_RETRY:-3}" ]
}

harness_retry_clear() { rm -f ".claude/state/stop-retry-$1" 2>/dev/null || true; }

# ── 발화 기록 (append-only)
#
# 이 하네스가 3개월간 무엇을 몇 번 막았는지 지금은 0으로 관측된다. 설정 오타로
# 가드가 무발화 상태가 되어도 신호가 없다. 한 줄씩 남겨 그것을 볼 수 있게 한다.
#
# 지켜야 할 것:
#   - stdout에 1바이트도 흘리지 않는다. protected-branch-guard는 stdout으로
#     차단 JSON을 반환하는 계약이라, 로그가 섞이면 훅 자체가 깨진다.
#   - jq를 부르지 않는다. PreToolUse는 매 Bash 호출마다 도니 지연이 누적된다.
#   - 실패해도 훅 동작에 영향을 주지 않는다(로그는 부수 기능이다).
#
# harness_log <hook> <event> <decision> [reason]
harness_log() {
  local dir=".claude/state" f="$1" ev="$2" dec="$3" reason="${4:-}" ts br
  [ "${HARNESS_TELEMETRY:-true}" = "true" ] || return 0
  mkdir -p "$dir" 2>/dev/null || return 0
  ts="$(date +%Y-%m-%dT%H:%M:%S%z 2>/dev/null || echo unknown)"
  br="$(git branch --show-current 2>/dev/null || echo '')"
  # JSON 문자열로 안전하게: 역슬래시·따옴표·개행·탭 제거
  reason="$(printf '%s' "$reason" | tr '\n\t' '  ' | tr -d '\\"' | cut -c1-200)"
  printf '{"ts":"%s","hook":"%s","event":"%s","decision":"%s","branch":"%s","reason":"%s"}\n' \
    "$ts" "$f" "$ev" "$dec" "$br" "$reason" >> "$dir/harness.jsonl" 2>/dev/null || true
  # 무한 증가 방지 — 5000줄을 넘으면 뒤쪽만 남긴다
  harness_log_rotate "$dir/harness.jsonl"
  return 0
}

harness_log_rotate() {
  local f="$1" n
  n="$(wc -l < "$f" 2>/dev/null | tr -d ' ')" || return 0
  [ "${n:-0}" -gt 5000 ] || return 0
  tail -n 4000 "$f" > "$f.tmp" 2>/dev/null && mv "$f.tmp" "$f" 2>/dev/null
  return 0
}

# ── 현재 브랜치가 보호 브랜치인가 (0=보호됨)
harness_is_protected_branch() {
  local branch="$1" b
  [ -n "$branch" ] || return 1
  for b in ${PROTECTED_BRANCHES:-master main}; do
    [ "$branch" = "$b" ] && return 0
  done
  return 1
}
