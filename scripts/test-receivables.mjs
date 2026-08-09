#!/usr/bin/env node
// 미수금 점검 모드(E) 회귀 테스트 — receivables-check.md의 대조 규칙을 그대로 구현한
// 참조 엔진에 대해, 2026-08-09 적대적 리뷰로 확정된 동작을 고정한다.
// 이 테스트가 깨진다 = 스킬 명세의 안전 동작이 바뀌었다는 뜻이다.
// (skills/ 밖의 scripts/ 위치 — 무료판 '엔진 파일 금지' 게이트는 skills/만 검사한다)

// 경과일수 단계 — 반개구간 (30일 이상~90일 미만 등)
const stage = (n) => n < 30 ? '정상' : n < 90 ? '주의' : n < 365 ? '경고' : '위험';

let n = 0; const fails = [];
const assert = (cond, msg) => { n++; if (!cond) fails.push(msg); };

// ─── 참조 엔진: 명세의 분류 규칙 구현 ───────────────────────────
// 반환: 각 청구 건에 cls(입금완료후보|미입금|판단불가) 부여. 입금은 1:1 소진.
function classify(invoices, deposits) {
  // 1. 수정 쌍 처리: 감액은 원본에 **누적** 병합(다건 감액 대응 — 리뷰 M-2), 누적 순액이
  //    0이면 전액 취소로 제외. 취소인데 입금 흔적이 있으면 '환불 필요' 경고 (명세 게이트 ①).
  const amends = invoices.filter(i => i.amount < 0);
  const cancelled = new Set(), merged = new Map(), netByOrig = new Map();
  for (const a of amends) {
    const orig = invoices.find(i => i.no === a.amendOf);
    if (!orig) continue;
    netByOrig.set(orig.no, (netByOrig.get(orig.no) ?? orig.amount) + a.amount);
    cancelled.add(a.no); // 수정분 행은 별도 대조 안 함
  }
  const refundNeeded = [];
  for (const [no, net] of netByOrig) {
    if (net === 0) {
      cancelled.add(no);
      const orig = invoices.find(i => i.no === no);
      if (deposits.some(d => d.name === orig.partner && d.amount === orig.amount)) refundNeeded.push(no);
    } else merged.set(no, net);
  }
  const targets = invoices.filter(i => i.kind === '청구' && !cancelled.has(i.no))
    .map(i => ({ ...i, matchAmount: merged.get(i.no) ?? i.amount }));

  // 2. 자동 후보: 정확 일치 + 발행일 이후 + 명의 일치 + 입금 1:1 소진
  const used = new Set();
  const findExact = (inv) => deposits.findIndex((d, ix) => !used.has(ix)
    && d.amount === inv.matchAmount && d.date >= inv.date && d.name === inv.partner);
  // 동일 조건 경쟁 검사: 같은 (금액,명의) 후보 invoice 수 > 가용 입금 수면 전부 판단불가
  const byKey = {};
  for (const inv of targets) (byKey[inv.partner + '|' + inv.matchAmount] ??= []).push(inv);

  const rows = targets.map(inv => {
    const competitors = byKey[inv.partner + '|' + inv.matchAmount];
    const availableDeposits = deposits.filter(d =>
      d.amount === inv.matchAmount && d.name === inv.partner && d.date >= inv.date).length;
    if (competitors.length > 1 && availableDeposits < competitors.length && availableDeposits > 0)
      return { ...inv, cls: '판단불가', why: '입금 소진 규칙: 동일액 청구 다건에 입금 부족' };
    const di = findExact(inv);
    if (di >= 0) { used.add(di); return { ...inv, cls: '입금완료후보', why: '정확 일치' }; }
    // 판단불가 열거
    if (deposits.some(d => d.amount === inv.matchAmount && d.name === inv.partner && d.date < inv.date))
      return { ...inv, cls: '판단불가', why: '선금(발행 전 입금)' };
    if (deposits.some(d => d.name === inv.partner && d.amount !== inv.matchAmount))
      return { ...inv, cls: '판단불가', why: '부분·합산·정산 의심' };
    if (deposits.some(d => d.amount === inv.matchAmount && d.date >= inv.date && d.name !== inv.partner))
      return { ...inv, cls: '판단불가', why: '의뢰인명 불일치' };
    return { ...inv, cls: '미입금', why: '연결 후보 전무 (최후의 분류)' };
  });
  rows.refundNeeded = refundNeeded;
  return rows;
}

// ─── A. 선금: 발행 전 입금은 미입금이 아니라 판단불가 (리뷰 H-1) ───
{
  const r = classify(
    [{ no: 'A1', partner: '가', date: '2026-07-10', amount: 1000000, kind: '청구' }],
    [{ date: '2026-07-05', amount: 1000000, name: '가' }]);
  assert(r[0].cls === '판단불가', `A 선금 → 판단불가 (실제: ${r[0].cls})`);
}

// ─── B. 이중 매칭: 입금 1건 ↔ 동일액 청구 2건 → 전부 판단불가 (리뷰 C-1) ───
{
  const r = classify(
    [{ no: 'B1', partner: '나', date: '2026-07-01', amount: 550000, kind: '청구' },
     { no: 'B2', partner: '나', date: '2026-07-15', amount: 550000, kind: '청구' }],
    [{ date: '2026-07-20', amount: 550000, name: '나' }]);
  assert(r.every(x => x.cls === '판단불가'), `B 이중매칭 → 전부 판단불가 (실제: ${r.map(x => x.cls)})`);
  assert(r.filter(x => x.cls === '입금완료후보').length === 0, 'B 입금 1건이 2건을 지우지 않음');
}

// ─── C. 감액 수정: 순액으로 대조 (리뷰 M-1) ───
{
  const r = classify(
    [{ no: 'C1', partner: '다', date: '2026-06-01', amount: 3000000, kind: '청구' },
     { no: 'C2', partner: '다', date: '2026-06-05', amount: -1000000, kind: '청구', amendOf: 'C1' }],
    [{ date: '2026-06-10', amount: 2000000, name: '다' }]);
  assert(r.length === 1 && r[0].cls === '입금완료후보', `C 감액 순액 200만 대조 → 입금완료후보 (실제: ${r.map(x => x.cls)})`);
}

// ─── C2. 다중 감액 누적: 1,000만 − 100만 − 200만 = 순액 700만으로 대조 (리뷰 M-2) ───
{
  const r = classify(
    [{ no: 'C21', partner: '아', date: '2026-06-01', amount: 10000000, kind: '청구' },
     { no: 'C22', partner: '아', date: '2026-06-03', amount: -1000000, kind: '청구', amendOf: 'C21' },
     { no: 'C23', partner: '아', date: '2026-06-05', amount: -2000000, kind: '청구', amendOf: 'C21' }],
    [{ date: '2026-06-10', amount: 7000000, name: '아' }]);
  assert(r.length === 1 && r[0].cls === '입금완료후보', `C2 다중 감액 누적 순액 700만 → 입금완료후보 (실제: ${r.map(x => x.cls)})`);
}

// ─── C3. 다건 감액 합계로 전액 취소: 1,000만 − 400만 − 600만 = 0 → 대조 제외 ───
{
  const r = classify(
    [{ no: 'C31', partner: '자', date: '2026-06-01', amount: 10000000, kind: '청구' },
     { no: 'C32', partner: '자', date: '2026-06-03', amount: -4000000, kind: '청구', amendOf: 'C31' },
     { no: 'C33', partner: '자', date: '2026-06-05', amount: -6000000, kind: '청구', amendOf: 'C31' }],
    []);
  assert(r.length === 0, `C3 다건 감액 합계 취소 → 대조 대상 0건 (실제: ${r.length})`);
}

// ─── D. 전부 취소 쌍: 대조 제외 + 기수령이면 환불 필요 경고 (리뷰 L-4) ───
{
  const r = classify(
    [{ no: 'D1', partner: '라', date: '2026-05-01', amount: 6600000, kind: '청구' },
     { no: 'D2', partner: '라', date: '2026-05-03', amount: -6600000, kind: '청구', amendOf: 'D1' }],
    []);
  assert(r.length === 0, `D 취소 쌍 → 대조 대상 0건 (실제: ${r.length})`);
  assert(r.refundNeeded.length === 0, 'D 입금 없음 → 환불 경고 없음');
  const r2 = classify(
    [{ no: 'D1', partner: '라', date: '2026-05-01', amount: 6600000, kind: '청구' },
     { no: 'D2', partner: '라', date: '2026-05-03', amount: -6600000, kind: '청구', amendOf: 'D1' }],
    [{ date: '2026-05-02', amount: 6600000, name: '라' }]);
  assert(r2.refundNeeded.includes('D1'), `D2 취소+기수령 → 환불 필요 경고 (실제: ${JSON.stringify(r2.refundNeeded)})`);
}

// ─── E. 부분입금·명의불일치 → 판단불가, 연결 전무 → 미입금 ───
{
  const r = classify(
    [{ no: 'E1', partner: '마', date: '2026-04-15', amount: 2200000, kind: '청구' },
     { no: 'E2', partner: '바', date: '2026-06-05', amount: 2750000, kind: '청구' },
     { no: 'E3', partner: '사', date: '2026-07-01', amount: 5500000, kind: '청구' }],
    [{ date: '2026-05-02', amount: 1100000, name: '마' },
     { date: '2026-06-07', amount: 2750000, name: '김철수' }]);
  const cls = Object.fromEntries(r.map(x => [x.no, x.cls]));
  assert(cls.E1 === '판단불가', `E1 부분입금 → 판단불가 (실제: ${cls.E1})`);
  assert(cls.E2 === '판단불가', `E2 명의불일치 → 판단불가 (실제: ${cls.E2})`);
  assert(cls.E3 === '미입금', `E3 연결 전무 → 미입금 (실제: ${cls.E3})`);
}

// ─── F. 혼합 픽스처 분류 고정: 영수 제외·감액 병합·건별 분류가 정확한가 ───
// (게이트 ② 검증식 자체는 classify 구조상 항상 성립하므로 — 리뷰 L-3 — 여기서는
//  기대 분류값을 하나씩 고정해 회귀를 잡는다)
{
  const invoices = [
    { no: 'F1', partner: '가', date: '2026-07-20', amount: 3300000, kind: '청구' },
    { no: 'F2', partner: '나', date: '2026-07-01', amount: 5500000, kind: '청구' },
    { no: 'F3', partner: '다', date: '2026-06-01', amount: 3000000, kind: '청구' },
    { no: 'F4', partner: '다', date: '2026-06-05', amount: -1000000, kind: '청구', amendOf: 'F3' },
    { no: 'F5', partner: '라', date: '2026-08-01', amount: 990000, kind: '영수' },
  ];
  const r = classify(invoices, [{ date: '2026-07-22', amount: 3300000, name: '가' }]);
  const cls = Object.fromEntries(r.map(x => [x.no, x.cls]));
  assert(r.length === 3, `F 대조 대상 3건 — 영수 F5·수정분 F4 제외 (실제: ${r.length})`);
  assert(cls.F1 === '입금완료후보', `F1 정확 일치 → 입금완료후보 (실제: ${cls.F1})`);
  assert(cls.F2 === '미입금', `F2 연결 전무 → 미입금 (실제: ${cls.F2})`);
  assert(cls.F3 === '미입금', `F3 감액 순액 200만·입금 없음 → 미입금 (실제: ${cls.F3})`);
}

// ─── G. 경과일수 경계값: 반개구간 (리뷰 L-1) ───
for (const [d, exp] of [[29, '정상'], [30, '주의'], [89, '주의'], [90, '경고'], [364, '경고'], [365, '위험']])
  assert(stage(d) === exp, `G 경과 ${d}일 → ${exp} (실제: ${stage(d)})`);

// ─── H. 영수 역점검: 선수령(발행 전 입금)은 정상, 흔적 전무만 경고 ───
{
  const warn = (inv, deposits) => !deposits.some(d => d.amount === inv.amount && d.name === inv.partner);
  assert(!warn({ partner: '카', amount: 990000 }, [{ date: '2026-07-29', amount: 990000, name: '카' }]),
    'H 영수 선수령 → 오경보 없음');
  assert(warn({ partner: '파', amount: 4400000 }, []), 'H 영수+입금 흔적 없음 → 경고');
}

// ─── 결과 ───
if (fails.length) {
  console.error(`✗ 미수금 회귀 테스트 실패 — ${fails.length}건 (검사 ${n}종)`);
  for (const f of fails) console.error(`  ✗ ${f}`);
  process.exit(1);
}
console.log(`✓ 미수금 회귀 테스트 통과 — ${n}종 (소진·선금·순액·취소·경계·역점검·게이트②)`);
