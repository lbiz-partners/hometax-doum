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

## 업무별 Pro 추가 작업 (24개)

업무 전체를 자동 처리한다는 뜻이 아니다. 세액·자격·기한의 전문 판단, 공식 서식 생성·실제 제출은 각 도구의 지원 범위와 구별한다. 아래 표는 `service-catalog.json`에서 생성한다(`scripts/render-service-catalog.py`).

<!-- pro-table:start -->
| 업무 | 추가 작업 | 도구 |
|---|---|---|
| H01 처음 설정·사업장 전환 | 가명 사업장 프로필·확인일 검증 | `owner_workspace.py` |
| H02 사업자등록 신청·정정 | 신청·정정의 상세 준비 안내 | `biz-reg-hometax` |
| H03 휴업·재개업·폐업 | 마지막 영업기간의 매출·정산·준비금 대조 | `monthly_review.py` |
| H04 계좌·카드·전자송달 | 등록 관련 제출서류 조건 대조 | `document_review.py` |
| H05 전자세금계산서·전자계산서 | 청구와 입금의 미수 후보 대조 | `receivables-engine.mjs` |
| H06 현금영수증 | 매출 원장과 현금영수증의 중복·금액 차이 대조 | `monthly_review.py` |
| H07 지출·매입증빙 | 사람이 분류한 지출 합계와 입력값 대조 | `control_review.py` |
| H08 매출·정산·입금 | 명시적 열 변환 후 매출·정산·입금 대조 | `tabular_import.py + monthly_review.py` |
| H09 부가세 기본 | 일반·간이 부가세 계산 참고값과 같은 항목의 화면값 대조 | `industry_review.py + control_review.py` |
| H10 부가세 심화 | 음식점 의제매입·일반과세 공통매입 안분·상가 보증금 계산 참고값 | `industry_review.py + control_review.py` |
| H11 종합소득세 | 지원 연도·유형의 개인 종소세 예상세액 | `jongsose_engine.py` |
| H12 장부·결산·공동사업 | 재고·제조원가 연결과 본인 작성 장부의 확인된 합계 대조 | `industry_review.py + control_review.py` |
| H13 면세사업장현황 | 학원·인적용역 수입 연결·주택 분리과세 참고값과 면세 연간 집계 | `industry_review.py + business_status.py` |
| H14 원천세·외주비 | 지원 소득유형의 예상 원천징수액 | `withholding-engine.mjs` |
| H15 지급명세서·소득자료 | 지급총액과 명세서의 같은 항목 대조 | `control_review.py` |
| H16 직원 연말정산·퇴직 | 확인된 연간 지급·정산 입력값의 합계 대조 | `control_review.py` |
| H17 국세증명 | 원문 확인된 증명서와 제출처 요구조건 비교 | `document_review.py` |
| H18 접수·고지·납부 | 증빙에 따른 신고·국세/지방세 납부 상태 분리 | `owner_workspace.py` |
| H19 환급 | 예상·결정·충당·입금에서 비교 가능한 금액 대조 | `control_review.py` |
| H20 기한후·수정·경정청구 | 원신고와 정정 근거의 같은 항목 대조 | `control_review.py` |
| H21 기한연장·유예 | 승인된 기한·확정금액을 사용한 준비금 집계 | `monthly_review.py` |
| H22 장려금·포인트·지원 | 신청에 필요한 서류의 누락·기간 조건 점검 | `document_review.py` |
| H23 상담·소명·대리인 | 전문가에게 전달할 서류 조건 점검 | `document_review.py` |
| H24 조건부 세목·외부 연계 | 확인된 수출 영세율의 기본 부가세 참고값·조건부 업무 인계자료 점검 | `industry_review.py + document_review.py` |
<!-- pro-table:end -->
