# 제안: tax-prep-kr 분할 (F-06, 결정 필요, 구현하지 않음)

작성일 2026-09-17.

## 현재 상태

`skills/hometax-tax-hub/references/service-catalog.json`의 24개 업무 중 15개가 `tax-prep-kr`로 연결된다.

| 업무 | 안내 문서 (`skills/tax-prep-kr/references/`) |
|---|---|
| H01~H04 처음 설정, 사업자등록, 휴폐업, 계좌·카드 | `business-lifecycle.md` |
| H10 부가세 심화, H12 장부·결산, H24 조건부 세목 | `advanced-and-linked.md` |
| H13 면세사업장현황 | `exempt-status-report.md` |
| H14~H16 원천세, 지급명세서, 연말정산 | `payroll-basic.md` |
| H17~H19, H22 증명, 납부, 환급, 장려금 | `documents-and-payments.md` |
| H20, H21, H23 정정, 기한연장, 소명 | `corrections-and-relief.md` |

그 밖에 `calendar-and-sources.md`, `industry-guide.md`, `monthly-owner-checklist.md`, `owner-services.md`가 있어 references는 모두 10개다. `SKILL.md` 본문은 부가세·종소세 자료 준비 체크리스트와 폴더 템플릿이 중심이고, 위 업무들은 "업무별 진행 안내" 절에서 문서 하나씩을 가리키는 구조다.

## 분할안

새 스킬 후보 이름: `biz-admin-hometax` (사업자 행정). 옮길 업무는 H01~H04, H17~H23, 옮길 문서는 `business-lifecycle.md`, `documents-and-payments.md`, `corrections-and-relief.md`, `owner-services.md`다. `tax-prep-kr`에는 신고 자료 준비(부가세·종소세·면세·인건비·심화·업종·월간)가 남는다.

이렇게 나누면 `tax-prep-kr`의 description이 "신고 전 자료 준비"로 선명해지고, "증명서 필요해요", "폐업하려고요" 같은 요청이 신고 준비 스킬로 들어가지 않는다.

## 여섯 스킬 집합을 고정한 위치 (모두 함께 바꿔야 함)

| 파일 | 위치 |
|---|---|
| `scripts/check.mjs` | 17행 `const FREE = [...]` (6종 허용 목록, 개수 검사) |
| `scripts/build_packages.py` | 13행 `FREE = {...}` |
| `scripts/check-service-catalog.py` | 9행 `FREE = {...}` |
| `install.py` | 20행 `EXPECTED = {...}` (설치기가 6종을 요구) |
| `VERSION` | `skills:` 목록 6줄 |
| `scripts/test-free-release.py` | 6종 전제 검사 여러 곳 (예: 174행 `hometax-tax-hub` 이름 참조, 설치 로그 6건 검사) |
| `README.md`, `시작-가이드.md` | "무료 스킬 6종" 문구 다수 |
| `.claude-plugin/marketplace.json`, `plugin.json` | description의 "무료 스킬 6종" |
| `skills/hometax-tax-hub/SKILL.md` | 작업 연결 표의 `tax-prep-kr` 항목 |
| `skills/hometax-tax-hub/references/service-catalog.json`, `service-catalog.md` | 15개 업무의 `skill`, `guide` 경로 |
| Pro 저장소 | `scripts/export-free.py` `FREE`, `scripts/release-check.mjs`의 9종 검사, `install.sh`의 9종 검사, `VERSION` |

무료 6종·Pro 9종이라는 제품 표기 자체가 바뀌므로 README와 판매 안내까지 손대야 한다.

## 라우팅 변화

- 허브의 작업 연결 표 첫 행 "처음 시작·이번 달 할 일·사업자등록·휴폐업·계좌·증명·납부환급·지원"이 두 스킬로 갈라진다. "이번 달 할 일"은 `tax-prep-kr`(월간 체크리스트), 나머지는 새 스킬.
- Pro `biz-reg-hometax`(사업자등록 상세)와 새 스킬의 H02가 겹친다. 새 스킬은 기본 안내, Pro는 상세 절차라는 현재 관계를 유지하되 description에 명시해야 한다.

## 위험

- 스킬 수 변경은 게이트·설치기·빌더·문서·Pro 내보내기까지 한 번에 바꿔야 하는 제품 결정이다. 중간 상태로 배포되면 설치기가 스킬 수 불일치로 멈춘다.
- 이미 설치한 사용자는 업데이트 후 스킬이 7개가 되고, 기존 대화 습관("tax-prep-kr로 증명서")이 새 스킬로 넘어가지 않을 수 있다. 허브가 흡수하지만 라우팅 평가(C-05)로 확인해야 한다.
- 문서 이동으로 `service-catalog.json`의 `guide` 경로 15개가 바뀌고, `check-service-catalog.py`가 절 제목(`section`)의 존재를 검사하므로 이동 후 H-절 제목을 그대로 유지해야 한다.

## 결정 필요

- 분할을 할지, 현재 구조를 유지하고 description만 다듬을지.
- 한다면 새 스킬 이름과 무료 7종 표기를 받아들일지.
- 시점: 4.2.0에 넣지 않고 다음 마이너 버전으로 미루는 것을 권한다.
