# 1인 개인사업자 업무 안내의 공식 근거

확인일 **2026-09-12 (Asia/Seoul)**. 대상은 무료 6종·Pro 9종의 1인 소규모 개인사업자 안내다. 법인세는 별도 Ultra 향후 계획이며 이번 검증에 포함하지 않는다. 두 버전의 CLI 스킬 폴더에 동봉한 `income-tax-hometax/references/tax-policy.md`(종소세)와 `vat-hometax/references/tax-policy.md`(부가세)의 정책 근거를 함께 확인한다. Pro에는 추가 검증 기록인 `docs/tax-policy-sources-2026-09-12.md`도 동봉한다.

| ID | 확인한 내용 | 공식 원문 | 적용 주의 |
| --- | --- | --- | --- |
| O1 | 개인 일반·간이 신고기간, 예정고지, 유형전환·상반기 세금계산서 발급 간이 예외 | [국세청 VAT 기한](https://www.nts.go.kr/nts/cm/cntnts/cntntsView.do?cntntsId=7694&mi=2273) | 기본기한과 해당 연도 순연·연장 분리 |
| O2 | 실제 월별 신고·납부·지급명세서 일정 | [국세청 세무일정](https://www.nts.go.kr/nts/ad/taxSchdul/selectList.do?mi=135747&taxMonth=) | 연도·월·지급분을 지정해 사용. 개인에게 무관한 법인 일정 제외 |
| O3 | 사업용카드 등록·조회와 공제 확인/변경은 별도 | [국세청 사업용카드](https://b.nts.go.kr/nts/cm/cntnts/cntntsView.do?cntntsId=7799&mi=2475) | 등록만으로 업무 관련성·공제가 확정되지 않음. 공급자 간이 예외는 기존 법령 기반 rules.md·세무 정책 기록을 우선 대조 |
| O4 | 면세 개인사업자 사업장현황신고, 특정 제외자, 휴폐업 포함 | [국세청 개요](https://www.nts.go.kr/nts/cm/cntnts/cntntsView.do?cntntsId=7699&mi=2283) | 보험모집·독립 음료품 배달·납세조합 등 해당 요건 확인. 모든 프리랜서/방문판매/배달기사 제외로 확대 금지 |
| O5 | 사업장현황신고 법정기한·겸영 면세수입 신고 간주·제외 근거 | [소득세법 §78](https://www.law.go.kr/LSW/lsLinkCommonInfo.do?lsJoLnkSeq=1032955831) | VAT 접수증만으로 면세 수입 신고까지 간주하지 않음 |
| O6 | 제공 매출·매입자료의 기준기간이 자료마다 다름 | [국세청 2025년 귀속 사업장현황신고 안내](https://b.nts.go.kr/dongnae/na/ntt/selectNttInfo.do?mi=5157&nttSn=1348061) | 해당 안내의 기준기간을 모든 세목/연도에 복사하지 않음 |
| O7 | 모두채움 대상도 소득 합산 여부 확인 | [국세청 모두채움 납부 안내](https://s.nts.go.kr/nts/cm/cntnts/cntntsView.do?cntntsId=238978&mi=40483) | 미리채움은 신고접수·완전성의 증거가 아님 |
| O8 | 종소세 신고 뒤 지방소득세와 국세 납부 후속 | [국세청 신고·납부방법](https://g.nts.go.kr/nts/cm/cntnts/cntntsView.do?cntntsId=238910&mi=40296) | 접수·납부·환급을 구별 |
| O9 | 모두채움 지방세액 무변동 납부 등 2026 안내 | [행정안전부 공식 안내](https://www.youtube.com/watch?v=KtLeMKxPTIE) | 법정 신고 간주 해당 여부와 실제 납부 증빙 확인. 다른 연도는 재확인 |
| O10 | VAT 과세표준증명 목적·신청·수령 | [정부24 서비스](https://www.gov.kr/mw/AA020InfoCappView.do?CappBizCD=12100000331) | 제출기관 요구 기간·용도·본인 인증·온라인 대리 제한 확인 |
| O11 | 납세증명은 법정 예외를 제외한 체납 사실 관련 증명 | [정부24 납세증명](https://www.gov.kr/mw/AA020InfoCappView.do?CappBizCD=12100000011&HighCtgCD=A09002&Mcode=10020&srhQuery=2023) | 납부내역증명·지방세증명과 구별 |
| O12 | 국세증명 종류 | [국세청 국세증명 안내](https://webtv.nts.go.kr/nts/na/ntt/selectNttInfo.do?mi=2207&nttSn=38162) | 2019년 안내. 문서명 참고만 사용, 처리시간·종수·현행 UI 보장에 사용하지 않음 |
| O13 | 공식 국세환급금 찾기 진입점 | [국세청 홈페이지](https://www.nts.go.kr/nts/main.do) | 연결된 홈택스의 로그인 후 조회·실제 환급금은 미검증 |
| O14 | 세금포인트 조회·조건부 혜택 | [국세청 세금포인트](https://nts.go.kr/taxpayer_advocate/cm/cntnts/cntntsView.do?cntntsId=8300&mi=11494) | 포인트를 현금·납부·세액공제로 처리하지 않음 |
| W1 | 근로 간이 2026 반기, 사업·인적용역 기타·일용 월별 및 연간 소득별 기한 | [국세청 지급명세서](https://www.nts.go.kr/nts/cm/cntnts/cntntsView.do?cntntsId=8631&mi=12242) | 기존 SKILL의 이자·배당 등을 3/10에 묶은 표현 수정 |
| W2 | §164① 연간 기한·휴폐업 특례, ⑦ 간이 제출분의 연간 제출 간주 | [소득세법 §164](https://www.law.go.kr/LSW/lsSideInfoP.do?docCls=jo&joBrNo=00&joNo=0164&lsiSeq=280405&urlMode=lsScJoRltInfoR) | 사업소득 연말정산 등 제외·누락분 확인. 연간·간이 무조건 중복 제출 표현 수정 |
| W3 | 근로소득 매월 간이명세서 전환 부분 시행일 2027-01-01 | [소득세법 §164의3](https://www.law.go.kr/LSW/lsSideInfoP.do?docCls=jo&joBrNo=03&joNo=0164&lsiSeq=280405&urlMode=lsScJoRltInfoR) | 본문과 별도 시행일을 함께 읽고 2026 지급에 소급 금지 |
| W4 | 간이 제출의 연간 간주를 받으려면 연간 제출기한까지 제출 | [국세청 서면-2024-법규소득-0868](https://taxlaw.nts.go.kr/qt/USEQTA002P.do?ntstDcmId=200000000000005207) | 과거 회신의 구법 인용을 근로 월별 전환의 현재 시행일로 사용하지 않음 |

## 확인 방법과 범위

공식 공개 페이지를 웹으로 조회했다. W2는 웹 표시 오류 후 같은 공식 URL을 curl로 받아 조문을 직접 읽었고 W3의 별도 시행일도 함께 확인했다. 로컬 Python 기본 인증서 오류 때문에 검증을 끄지 않고 시스템 curl의 정상 TLS 검증으로 읽었다.

별도 공개 UI 점검에서는 [홈택스 공개 첫 화면](https://hometax.go.kr/websquare/websquare.html?w2xPath=/ui/pp/index_pp.xml&menuCd=index3)의 소득금액증명 바로가기, 전체메뉴 → 계산서·영수증·카드 → 모두열기의 신용카드·판매(결제)대행 매출자료 조회, 매입세액 공제 확인/변경, 현금영수증 세액공제 확인/변경 명칭을 관찰했다. 이 확인은 메뉴 존재의 증거이며 **로그인 후 사용자 자료·공제 상태·신고·발급·납부의 검증이 아니다**. 사용자 계정·실제 신고·납부·환급계좌 변경은 수행하지 않았다.

가명 프로필 구조, 자료원 역할 구분, 중복·환불 연결, 증빙별 완료상태, 예상/확정 준비금 구분은 자료 누락과 오표시를 줄이기 위한 제품 설계다. 공식 기관이 이 소프트웨어의 계산이나 모든 사례를 인증했다는 뜻이 아니다. Pro 엔진 기능·회귀·보고서 검산 증거는 각 담당 엔진의 결과를 별도 참조한다.
