# Pro 연동 (탐지된 경우에만)

[Pro 설치 탐지](pro-detection.md)에서 `Pro 탐지`를 선언한 뒤에만 읽는다. Free 모드에서는 이 문서를 읽지 않는다. 아래 도구명은 모두 "실제 파일이 확인된 경우"를 전제한다.

## 실행 가능한 계산

| 요청 | 도구 | 범위 |
|---|---|---|
| 개인 종소세 예상액 | `jongsose-prep-kr`의 해당 연도 계산 엔진 (`assets/jongsose_engine.py`) | 지원 귀속연도·소득 유형 안에서만. 기장의무·경비율 판정은 하지 않음 |
| 원천징수 예상액 | `withholding-tax-hometax`의 `assets/withholding-engine.mjs` | 지원 소득유형·지급 기간 안에서만. 연말정산 전체 계산 아님 |
| 업종별 8개 계산·화면값 대조 | `jongsose-prep-kr`의 `references/industry-review.md` → `scripts/industry_review.py` | 금액·요건·기간·원문 대조가 확인된 범위만 실행 |
| 미수금 | `tax-invoice-hometax`의 `assets/receivables-engine.mjs` | 없으면 원자료·건별 질문·수동 대조 |
| 여러 CSV/XLSX·월마감·신고값 차이·서류 묶음 | `jongsose-prep-kr`의 `references/business-desk.md` | 파일 변환·합계 대조는 세무 판단이나 신고 완료가 아님 |
| 면세 연간 수입·매입 | `jongsose-prep-kr`의 `scripts/business_status.py` | 간주임대료·세액 계산은 포함하지 않음 |
| 사업자등록 상세 | `biz-reg-hometax` | 미설치여도 `tax-prep-kr`의 기본 안내로 계속 |

## 허브 작업 연결표의 Pro 보강

| 허브 행 | Pro에서 더하는 것 |
|---|---|
| 음식점 의제매입·상가 보증금·주택 분리과세·재고원가·학원/프리랜서 수입 | `industry_review.py`의 해당 모드. 지원 조건은 `references/industry-review.md`에서 먼저 확인 |
| 직원·외주비·원천세·지급명세서·연말정산 | `withholding-tax-hometax`의 지원 소득유형만 계산. 준비·지급명세서 안내는 `tax-prep-kr`의 `references/payroll-basic.md` 그대로 |
| 종소세·모두채움·근로+사업 | 계산 요청은 `jongsose-prep-kr`로, 홈택스 화면 절차는 `income-tax-hometax`로. 인계 표는 반복 질문 없이 그대로 사용 |
| 사업자등록·정정 | `biz-reg-hometax`의 화면 기준 절차 |

## 공통 규칙

- 실행 파일이 없거나 지원 범위 밖이면 안내·준비·수동 대조로 계속 진행한다. 실행하지 않은 엔진을 사용했다고 표시하지 않는다.
- 엔진 오류를 AI 암산으로 대신하지 않는다. 오류 원문과 다음 조치를 보고한다.
- 엔진 결과는 예상치다. 홈택스 화면·신고서 명세와 항목별로 대조하고 차이표를 남긴다.
- 엔진의 미지원·확인필요·검산 미수행 상태를 통과로 바꾸지 않는다.
