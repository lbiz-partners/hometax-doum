# 제안: .skill·ZIP 바이너리를 git에서 GitHub Releases로 (C-09, 결정 필요)

작성일 2026-09-17. 무료 저장소 기준. Pro 저장소에도 같은 이름의 문서가 있다.

## 현재 상태

- `데스크탑용-skill파일/`에 현재 버전 `.skill` 6개, `previous/`에 3.9.0과 4.1.1의 `.skill` 12개가 있다. 합계 18개가 모두 git에 커밋돼 있다 (`git ls-files` 18건).
- 디스크 사용량은 `du -sk` 기준 폴더 전체 300KB, 그중 `previous/`가 192KB다. 지금은 작지만 `scripts/build_packages.py`는 버전이 바뀔 때마다 이전 번들을 `previous/`로 옮기므로 버전당 6개씩 늘어난다.
- 최종 ZIP 2종(`홈택스-도움-스킬_Free_카톡전달용.zip`, `hometax-doum-free-v{VERSION}.zip`)과 SHA-256 목록은 저장소 상위 폴더에 만들어지고 커밋되지 않는다.

## 번들을 참조하는 검사

- `scripts/test-free-release.py` `test_current_desktop_bundles_match_sources`: `데스크탑용-skill파일/*.skill` 파일명이 `{스킬}_v{VERSION}.skill` 6개와 정확히 같고, 각 번들 내용이 `skills/` 원본과 바이트 일치하는지 검사한다.
- 같은 파일 `test_release_zip_includes_windows_installers`: 임시 폴더에 `package.build()`를 실행해 ZIP 안에 설치기 3종이 있는지 검사한다. 번들 커밋 여부와 무관하다.
- `.claude/harness.config.sh`의 `CODE_FILE_REGEX`가 `데스크탑용-skill파일/.+`를 감시 대상으로 삼는다.

## 제안

1. `.skill`과 ZIP, SHA-256 목록을 GitHub Releases의 첨부 파일로 올린다. 태그는 `v{VERSION}`.
2. 저장소에는 `releases/SHA256SUMS-v{VERSION}.txt`처럼 해시 목록만 남긴다. 고객이 받은 파일을 대조할 수 있고, 저장소는 텍스트만 갖는다.
3. `test_current_desktop_bundles_match_sources`는 커밋된 폴더 대신 빌드 산출 폴더(`bash scripts/build.sh`가 방금 만든 것)를 대상으로 바꾼다. CI에서는 빌드 직후 검사하므로 의미가 유지된다.
4. `데스크탑용-skill파일/`을 `.gitignore`에 넣고, 기존 커밋 파일은 사용자 승인 후 삭제한다. `previous/`는 Releases의 과거 버전으로 대체된다.
5. `build_packages.py`의 "이전 번들을 previous/로 옮기는" 동작은 제거한다.

## 카톡 전달 흐름

지금은 빌드한 ZIP을 카톡으로 직접 보낸다 (`시작-가이드.md` "받은 ZIP 확인"). Releases로 옮기면 두 가지 방법이 있다.

- 그대로 ZIP 파일을 카톡으로 보낸다 (Releases는 보관용). 흐름 변화 없음.
- Releases 링크를 보낸다. 고객이 GitHub에서 내려받아야 하므로 비개발자에게는 한 단계가 늘어난다. 무료판은 공개 저장소라 링크만으로 받을 수 있다.

## 결정 필요

- 커밋된 `.skill` 18개를 삭제해도 되는지 (복구는 git 이력과 Releases에서 가능).
- 카톡 전달을 ZIP 파일 그대로 유지할지, Releases 링크로 바꿀지.
- 적용 시점 (4.2.0 출고와 함께, 또는 그 다음).
