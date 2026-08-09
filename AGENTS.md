# CLAUDE.md — hometax-doum 개발 규칙 (하네스와 쌍)

> **스코프**: 이 문서는 이 리포지토리를 **개발·수정하는 에이전트 세션 전용** 규칙이다.
> 스킬을 **사용**만 하는 사람·에이전트(README의 `skills/` 복사 설치)는 이 문서와 무관하며,
> 복사해 간 스킬에는 아래 규칙·게이트가 적용되지 않는다.

이 리포는 마켓플레이스로 배포되는 **무료 세무 스킬 모음**이다. main 푸시 = 즉시 배포이므로,
아래 규칙은 문서 글씨가 아니라 **강제 장치와 쌍**으로 운용된다 (agent-harness-kit 경량 이식, 2026-08-09).

## 규칙 ↔ 강제 장치

| 규칙 | 장치 |
|---|---|
| 스킬(`skills/**.md`)·게이트(`scripts/`)·하네스(`.claude/`) 수정 턴은 **결정론 게이트 통과 후 종료** | `.claude/hooks/skill-gate.sh` (Stop, exit 2 재작업) + CI `check.yml` (CI는 push 후 사후 감지 — 직푸시=즉시 배포라 배포를 막지는 못함) |
| **활성화된 클론에서는** 어떤 도구든 push 시점 게이트 통과 — **push되는 커밋 기준** (워킹트리 아님) | `.githooks/pre-push` (git 계층). 클론당 1회 활성화: `git config core.hooksPath .githooks` — 미활성이면 check.mjs가 실격 처리. **한계**: `git push --no-verify`는 **금지**(고의 우회는 CI 사후 적발), GitHub 웹 편집 경로는 CI만 방어 |
| 스킬 수정은 **적대적 리뷰 영수증 필수** | `.claude/hooks/review-gate.sh` (Stop, block) |
| 안전 문구(입금 소진·선금·과세구분 등 — `skill-rules.json` 전 규칙) **삭제 금지** | `scripts/skill-rules.json` ↔ `check.mjs` 안전규칙 lint |
| 대조 규칙 동작 변경 시 회귀 테스트 갱신 | `scripts/test-receivables.mjs` (CI 필수 스텝) |
| 유료(Pro) 스킬·엔진 파일 반입 금지, 면책 문구 유지 | `check.mjs` (기존 게이트) |

## 운용 메모

- **리뷰 영수증 남기기**: 독립 리뷰어(codex 또는 적대적 서브에이전트)의 원문을 그대로
  `<리뷰 원문> | bash scripts/harness-review-receipt.sh <codex|subagent>` 로 기록한다.
  영수증은 코드 상태 키에 묶이므로 코드가 더 바뀌면 자동 무효 → 재리뷰.
- 안전 문구를 **의도적으로** 바꿀 때: `scripts/skill-rules.json`을 함께 갱신하고 리뷰를 다시 받는다.
  리뷰 이력은 `docs/reviews/`에 남긴다.
- `.claude/` 훅은 **개발 세션 전용**이다. 플러그인 규격 위치(`hooks/hooks.json`)에 훅을 두지
  않았으므로 마켓플레이스 설치 사용자에게는 전파되지 않는다 — 이 경계를 유지할 것.
- **클론 후 1회**: `git config core.hooksPath .githooks` — push 시점 게이트 활성화. 미설정이면 check.mjs가 **실격**(fail) 처리한다.
- **`git push --no-verify` 금지.** 게이트가 막으면 우회하지 말고 커밋을 고치거나 사용자와 상의한다. pre-push는 워킹트리가 아니라 **push되는 커밋**을 검사하므로, 워킹트리만 고치고 커밋을 안 고치면 계속 막힌다 (정상 동작).
- **Codex·Aside 등 타 도구 세션의 비대칭(인정된 한계)**: 결정론 게이트는 pre-push가 도구 무관하게 강제하지만, **리뷰 영수증 강제(Stop 훅)는 Claude Code에만 있다.** 타 도구에서 스킬을 수정할 때는 이 문서의 리뷰 규칙을 스스로 따라야 한다 — codex라면 codex 자신이 아닌 별도 실행으로 리뷰를 받고 영수증을 남길 것.
- `AGENTS.md`는 이 문서의 **복제본**이다 (Codex 등 AGENTS.md를 읽는 도구용 — Windows 호환을 위해 심링크가 아닌 실파일). 한쪽만 고치지 말 것: CLAUDE.md 수정 후 `cp CLAUDE.md AGENTS.md`. 불일치는 check.mjs가 잡는다.
- `.claude/state/`는 로컬 상태(캐시·영수증·발화 기록)로 커밋하지 않는다 (.gitignore).
- 제품 방향이 바뀌는 수정(기능 추가·삭제, 홍보 문구, 가격)은 하네스 통과와 무관하게
  사용자 승인 후 진행한다.
