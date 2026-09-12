#!/usr/bin/env bash
# hometax-doum 하네스 설정 — 모든 hook이 이 파일을 source한다.
# agent-harness-kit에서 이 리포(마크다운 스킬 배포 리포)에 맞게 개조한 부분집합:
# 백로그·lockfile·lint/build·보호브랜치 훅은 비채택 (해당 없음/직푸시 배포 흐름).

# 게이트를 발동시키는 파일 패턴 (git status --porcelain 줄 대상 — 앞 경계 주의)
# 하네스 자신(.claude/·워크플로·CLAUDE.md)도 감시 대상 — 무장해제가 무감시로 일어나지 않게 (리뷰 M-6)
CODE_FILE_REGEX='(^|[/[:space:]])(skills/.+|scripts/.+|docs/.+|데스크탑용-skill파일/.+|\.claude/(settings\.json|harness\.config\.sh|hooks/.+\.sh|agents/.+\.md)|\.githooks/.+|\.github/workflows/.+\.ya?ml|\.gitattributes|CLAUDE\.md|AGENTS\.md|VERSION|EULA\.md|NOTICE\.md|README\.md|안내문\.md|시작-가이드-처음이라면-이것부터\.md|install\.sh|LICENSE\.md|시작-가이드\.md|\.claude-plugin/.+\.json)'

# 적대적 리뷰 게이트: 스킬·스크립트 변경 턴은 영수증 없이 종료 불가
REVIEW_GATE="block"
REVIEW_GATE_MIN_FILES="1"

# 검사 범위: 미커밋 + 이번 브랜치 커밋분 (main 위에서는 워킹트리만)
LINT_SCOPE="branch"
MAIN_BRANCH="main"

# 같은 실패 반복 시 게이트 통과(무한 재작업 루프 차단) 및 발화 기록
HARNESS_MAX_RETRY="3"
HARNESS_TELEMETRY="true"
