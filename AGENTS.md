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
| **원격보다 낮은 VERSION push 금지** (낡은 베이스가 배포를 되감는 사고) | `.githooks/pre-push` 버전 역행 차단 + `.github/workflows/check.yml` 서버측 재검사 |

## 공통 6종의 정본은 Pro 저장소 (2026-09-17)

- `skills/` 여섯 스킬, `shared/blocks/`, `scripts/sync-blocks.py`는 비공개 Pro 저장소(`hometax-doum-vault`)의 `scripts/export-free.py`가 내보낸 산출물이다. **이 저장소에서 직접 고치지 않는다.** 고칠 것이 있으면 Pro 원본을 고치고 다시 내보낸다. 여기서만 고친 변경은 다음 내보내기에 덮인다.
- 여러 SKILL.md에 같은 문장으로 들어가는 문단(면책·프로필 재사용·실화면 원칙)의 원본은 `shared/blocks/`다. `check.mjs` 9-1이 원본과 인라인 본문의 일치를 검사한다(`python3 scripts/sync-blocks.py --check`).
- 무료판에는 `유료`라는 단어, 개인 계정 인증 후 관찰 기록(`authenticated-ui-*`), Pro 코드(`.py`·`.mjs`)가 들어오지 않는다. 내보내기와 게이트가 각각 검사한다.

## 무료판 배포 빌드

- `VERSION`이 제품 버전의 기준이며 플러그인·마켓플레이스·README·시작 가이드가 일치해야 한다.
- `bash scripts/build.sh`로 정합성·미수금 회귀·설치 검증 후 무료 6개 `.skill`과 ZIP 2개를 생성한다. 수동 ZIP 출고는 하지 않는다.
- 게이트는 데스크탑 번들 **내용**을 `skills/` 원본과 바이트 대조한다. 스킬을 고쳤으면 반드시 `build.sh`로 번들을 다시 찍는다. `node scripts/check.mjs --prebuild`는 **build.sh 내부 사전점검 전용**이며 번들 검사를 끄므로 사람이 직접 쓰지 않는다(쓰면 stderr에 경고가 찍힌다). build.sh 말미의 전체 검사는 방금 자기가 만든 번들을 보므로, **커밋된 번들을 실제로 지키는 것은 CI 1단계와 pre-push**다.
- 안전 문구의 절 제목을 바꾸면 `scripts/skill-rules.json` 의 `under_heading` 도 함께 고친다. 안 고치면 게이트가 `기준 제목 없음` 으로 막는다(조용한 통과는 없다).
- **작업 시작 전 `git fetch` 로 `origin/main` 과 대조한다.** 낡은 베이스에서 만든 릴리스는 이미 배포된 버전을 되감는다 (2026-09-19 적대적 리뷰 9차 Critical: v4.2.0 위가 아니라 v3.9.0 계열 위에서 v3.10.0 을 찍을 뻔했다).
- 무료판 `skills/`에는 Markdown 안내와 JSON·CSV 입력 템플릿만 허용한다. Pro 코드·전용 스킬은 포함하지 않는다.
- 고객 ZIP은 안내·라이선스·공식출처·설치기·여섯 스킬만 포함하며 개발용 훅을 배포하지 않는다.
- 이번 제품의 기본 대상은 소규모 개인사업자·1인 대표다. 법인용 Ultra는 향후 별도 저장소에서 개발한다.

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
- **⚠ 이 기계에는 `repo-sync` 데몬이 상시 실행되며 이 리포가 등록돼 있다.** 데몬은 **기본 브랜치(main)만** 동기화하며, 60초 무편집이면 커밋·리베이스·push 한다 = 마켓플레이스 즉시 배포. 따라서 **검수 승인 전에는 이 워크트리를 `main` 으로 체크아웃하지 않는다.** 작업은 기능 브랜치에서 하고, 승인 후에만 main 에 올린다. 데몬에서 이 리포를 빼려면 사용자가 `repo-sync remove` 를 실행한다(에이전트가 남의 시스템 서비스를 임의로 끄지 않는다).
- 제품 방향이 바뀌는 수정(기능 추가·삭제, 홍보 문구, 가격)은 하네스 통과와 무관하게
  사용자 승인 후 진행한다.
