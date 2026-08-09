# CLAUDE.md — hometax-doum 개발 규칙 (하네스와 쌍)

이 리포는 마켓플레이스로 배포되는 **무료 세무 스킬 모음**이다. main 푸시 = 즉시 배포이므로,
아래 규칙은 문서 글씨가 아니라 **강제 장치와 쌍**으로 운용된다 (agent-harness-kit 경량 이식, 2026-08-09).

## 규칙 ↔ 강제 장치

| 규칙 | 장치 |
|---|---|
| 스킬(`skills/**.md`)·게이트(`scripts/`)·하네스(`.claude/`) 수정 턴은 **결정론 게이트 통과 후 종료** | `.claude/hooks/skill-gate.sh` (Stop, exit 2 재작업) + CI `check.yml` (CI는 push 후 사후 감지 — 직푸시=즉시 배포라 배포를 막지는 못함) |
| 스킬 수정은 **적대적 리뷰 영수증 필수** | `.claude/hooks/review-gate.sh` (Stop, block) |
| 안전 문구(입금 소진·선금·과세구분 등 12규칙) **삭제 금지** | `scripts/skill-rules.json` ↔ `check.mjs` 안전규칙 lint |
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
- `.claude/state/`는 로컬 상태(캐시·영수증·발화 기록)로 커밋하지 않는다 (.gitignore).
- 제품 방향이 바뀌는 수정(기능 추가·삭제, 홍보 문구, 가격)은 하네스 통과와 무관하게
  사용자 승인 후 진행한다.
