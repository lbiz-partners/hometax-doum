# 제안: 배포 브랜치와 개발 브랜치 분리 (C-08, 결정 필요)

작성일 2026-09-17. 무료 저장소(`lbiz-partners/hometax-doum`) 기준. Pro 저장소에도 같은 이름의 문서가 있다.

## 현재 상태

- `README.md`는 설치를 `/plugin marketplace add lbiz-partners/hometax-doum`으로 안내한다. 마켓플레이스가 읽는 것은 이 저장소의 기본 브랜치다.
- `.claude-plugin/marketplace.json`의 `"source": "./"`는 저장소 루트를 가리킨다. 기본 브랜치가 아닌 브랜치나 태그를 대상으로 지정할 수 있는지는 확인 필요다.
- `.github/workflows/check.yml`은 `main`으로의 push와 pull_request에서 실행된다. job은 `gate`(ubuntu)와 `windows-installer`(windows) 두 개다. GitHub 상태 검사 이름은 `check / gate`, `check / windows-installer`다.
- `CLAUDE.md`는 "main 푸시 = 즉시 배포, CI는 push 후 사후 감지"라고 인정한다.

## 제안

1. `main`을 보호한다. PR로만 갱신하고 required check로 `check / gate`와 `check / windows-installer`를 건다. 이것만으로도 "게이트 실패 커밋이 마켓플레이스에 노출되는" 경로가 닫힌다.
2. 마켓플레이스가 기본 브랜치만 읽는다면 여기까지가 현실적인 조치다. 비기본 브랜치를 읽을 수 있다면 `release` 브랜치를 두고 `marketplace.json`이 그 브랜치를 가리키게 해, `main` 병합과 배포 시점을 분리한다.
3. 어느 쪽이든 배포 시점마다 `v{VERSION}` 태그를 남긴다. `check.mjs`는 이미 `VERSION`과 `plugin.json`·`marketplace.json` 버전 일치를 검사하므로, 태그 이름 일치 검사만 추가하면 된다 (구현은 승인 후).

## GitHub 브랜치 보호 설정 (사용자가 웹에서 직접 적용)

| 브랜치 | 설정 항목 | 값 |
|---|---|---|
| main | Require a pull request before merging | 켬 (승인 수 0, 1인 운영) |
| main | Require status checks to pass before merging | 켬, `check / gate`, `check / windows-installer` |
| main | Require branches to be up to date before merging | 켬 |
| main | Do not allow bypassing the above settings | 켬 |
| main | Allow force pushes / Allow deletions | 끔 |

## 영향

- `CLAUDE.md` 규칙표의 "직푸시=즉시 배포" 문구와 `.githooks/pre-push`의 안내 문구를 함께 고친다.
- 로컬 `pre-push`는 그대로 1차 방어선으로 남는다. PR 경로에서는 CI가 같은 검사를 다시 한다.
- GitHub 웹 편집 경로도 PR을 거치게 되므로 `CLAUDE.md`가 인정하던 "웹 편집은 CI만 방어" 한계가 줄어든다.

## 결정 필요

- 브랜치 보호를 지금 적용할지, 4.2.0 출고 후 적용할지.
- `release` 브랜치 도입 여부 (마켓플레이스 동작 확인 후).
- 태그 규칙 `v{VERSION}` 채택 여부.
