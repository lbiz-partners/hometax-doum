# 적대적 리뷰 기록 — 도구 중립 계층 (2026-08-09)

- **대상**: pre-push git 훅·AGENTS.md·.gitattributes·check.mjs 확장 (Codex·Aside·직접 편집 경로 방어)
- **리뷰어**: 독립 적대적 서브에이전트 (작성자와 컨텍스트 분리)
- **결과**: HIGH 1 · MEDIUM 3 · LOW 6 발견 → 커밋 전 전건 반영

## 발견 → 해소 요약

| ID | 심각도 | 발견 | 해소 |
|---|---|---|---|
| H-1 | HIGH | pre-push가 push되는 ref가 아니라 **워킹트리**를 검증 — "깨진 커밋+복구 워킹트리" 우회와 "정상 커밋+WIP" 오차단 양방향 결함 | stdin refs 파싱 → 각 커밋을 `git archive`로 임시 추출해 검사 (커밋 기준). 양방향 시나리오 실측 검증 |
| M-1 | MEDIUM | hooksPath 안내의 순환성 — 경고를 볼 수 있는 경로는 이미 게이트 안 | 비CI 로컬 git 클론에서 미설정 = check **실격**으로 승격 |
| M-2 | MEDIUM | AGENTS.md가 스킬 사용자의 에이전트에까지 개발 규칙 주입 | 문서 첫머리에 스코프 선언 ("개발 세션 전용, 복사 설치 사용자는 무관") |
| M-3 | MEDIUM | "어떤 도구든 강제"가 과장 — opt-in·--no-verify·웹 편집 3경로 무언급 | 규칙표를 "활성화된 클론에서" + 한계 명시로 정정, `--no-verify` **금지** 문구를 규칙·거부 메시지에 추가 |
| L-1 | LOW | 리포 루트 확인 실패 시 fail-open | fail-closed(exit 1)로 변경 |
| L-2 | LOW | 브랜치 삭제·태그 push에도 게이트 실행 | zero-sha 스킵 (refs 파싱과 함께 해소) |
| L-3 | LOW | drift 비교가 BOM·후행 개행 미정규화 | norm에 BOM 제거·trimEnd 추가 |
| L-4 | LOW | hooksPath 문자열 정확 비교의 오경고 (절대경로 설정 시) | `/.githooks` 접미 허용 + git 워크트리 감지 가드 |
| L-5 | LOW | 표기-실측 카운트 불일치 (57종·12규칙) | 구체 숫자 표기 제거 ("전 규칙") |
| L-6 | LOW | `.githooks/*` 직계만 매칭, `text=auto` 부재 | `.githooks/**` + `* text=auto` |

리뷰가 뚫지 못한 지점(견고 확인): Windows CRLF 셔뱅 방어(.gitattributes 패턴 대조), AGENTS↔CLAUDE 동기화 강제 경로, 훅 실행비트 보존.

## 잔여 한계 (수용, 문서화됨)

- 미활성 클론·`--no-verify`(금지 명문화)·GitHub 웹 편집은 CI 사후 검증만 — CLAUDE.md 규칙표에 명시
- 타 도구 세션의 리뷰 영수증 강제는 없음 (Claude Code Stop 훅 전용) — 비대칭 인정
- review-gate의 자동 재시도 탈출구 없음 — 의도된 설계 (탈출 = 사용자 보고, 자가 무장해제 금지)
