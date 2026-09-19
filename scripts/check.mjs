#!/usr/bin/env node
// 무료판(hometax-doum) 정합성 게이트 — GitHub Actions가 push마다 자동 실행.
// 핵심 목적: 유료(Pro) 스킬이 무료 레포에 실수로 섞이는 것을 차단 + 면책·금지문구 검사.
// 위반 시 exit 1 → GitHub이 빨간 X로 표시.
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SKILL_DIR = path.join(ROOT, 'skills');
const errors = [];
const fail = (m) => errors.push(m);
let n = 0;
const check = (cond, m) => { n++; if (!cond) fail(m); };

const FREE = ['hometax-tax-hub', 'income-tax-hometax', 'receipt-classify-kr', 'tax-invoice-hometax', 'tax-prep-kr', 'vat-hometax'];
// Pro 전용 = vault(hometax-doum-vault) 9종 − 무료 6종. 여기 빠지면 유출을 못 잡는다.
// 2026-08-13 적대적 리뷰 Medium: biz-reg-hometax(v3.6.5 Pro 편입)가 누락돼 있었다.
const PRO = ['jongsose-prep-kr', 'withholding-tax-hometax', 'biz-reg-hometax'];

const skills = fs.readdirSync(SKILL_DIR).filter((d) => fs.existsSync(path.join(SKILL_DIR, d, 'SKILL.md')));

// 1. 유료 스킬 유출 방지 (제일 중요)
for (const pro of PRO) check(!skills.includes(pro), `⛔ 유료(Pro) 스킬이 무료 레포에 섞임: ${pro} — 삭제 필요`);

// 2. 엔진 파일 유출 방지 (무료는 마크다운·JSON·CSV 템플릿만)
const walk = (dir, acc = []) => {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const fp = path.join(dir, e.name);
    if (e.isDirectory()) { if (!['.git', '__pycache__', '.omc'].includes(e.name)) walk(fp, acc); }
    else acc.push(fp);
  }
  return acc;
};
const files = walk(SKILL_DIR);
const engines = files.filter((f) => !/\.(md|json|csv)$/.test(f));
check(engines.length === 0, `⛔ 무료 레포에 계산 엔진 파일 유출: ${engines.map((f) => path.relative(ROOT, f)).join(', ')}`);

const vPath = path.join(ROOT, 'VERSION');
check(fs.existsSync(vPath), 'VERSION 누락');
const version = fs.existsSync(vPath) ? (fs.readFileSync(vPath, 'utf8').match(/^version:\s*(\d+\.\d+\.\d+)$/m) || [])[1] : null;
check(!!version, 'VERSION 형식 오류');
const plugin = JSON.parse(fs.readFileSync(path.join(ROOT, '.claude-plugin/plugin.json'), 'utf8'));
const market = JSON.parse(fs.readFileSync(path.join(ROOT, '.claude-plugin/marketplace.json'), 'utf8'));
check(plugin.version === version && market.plugins[0].version === version, '플러그인·마켓플레이스 버전 불일치');
for (const file of ['README.md', '시작-가이드.md']) {
  const value = (fs.readFileSync(path.join(ROOT, file), 'utf8').match(/\*\*버전:\*\*\s*([0-9.]+)/) || [])[1];
  check(value === version, '안내 버전 불일치: ' + file);
}
// 2-1. 배포물 파일명의 구버전 잔존 — `**버전:**` 한 줄만 고치고 본문의 ZIP·번들 파일명을
//   그대로 두면 안내가 존재하지 않는 파일을 가리킨다 (2026-09-19 적대적 리뷰).
//   대상은 `.zip`/`.skill` 로 끝나거나 폴더로 쓰인 파일명 꼴뿐이고, 업데이트 내역의 이력
//   표기(앞에 - 나 _ 가 없다)는 걸리지 않는다. 구버전 파일명을 의도적으로 안내하는 줄에는
//   `<!-- old-release -->` 마커를 직접 단다 — '이전' 같은 흔한 낱말로 면제하면 정작 막아야
//   할 줄까지 통과한다(실측).
const RELEASE_FILENAME_VERSION = /[-_]v(\d+\.\d+\.\d+)(?=\.(?:zip|skill)\b|\/)/g;
const INTENTIONAL_OLD_VERSION = /<!--\s*old-release\s*-->/;
for (const file of ['README.md', '시작-가이드.md']) {
  const stale = [];
  for (const line of fs.readFileSync(path.join(ROOT, file), 'utf8').split('\n')) {
    if (INTENTIONAL_OLD_VERSION.test(line)) continue;
    for (const m of line.matchAll(RELEASE_FILENAME_VERSION)) if (m[1] !== version) stale.push(m[1]);
  }
  check(stale.length === 0, `파일명 꼴 구버전 잔존: ${file} → ${[...new Set(stale)].join(', ')} (현재 ${version})`);
}
for (const name of skills) {
  const content = fs.readFileSync(path.join(SKILL_DIR, name, 'SKILL.md'), 'utf8');
  const desc = (content.match(/^description:\s*([^\n]*)/m) || [])[1] || '';
  check(desc.length > 0 && desc.length <= 1024, '스킬 설명 길이 오류: ' + name);
}

// 3. 무료 6종이 모두 있는가
for (const s of FREE) check(skills.includes(s), `무료 스킬 누락: ${s}`);

// 3-1. FREE 밖의 스킬은 무엇이든 실격 (차단목록 → 허용목록)
//   PRO 목록만으로는 "앞으로 추가될 Pro 스킬"을 못 막는다. 실제로 biz-reg-hometax 가
//   PRO 목록에 빠진 채 v3.6.5 에 편입돼 있었다(2026-08-13 적대적 리뷰 Medium).
//   무료판 구성은 FREE 6종과 정확히 같아야 한다.
const extra = skills.filter((s) => !FREE.includes(s));
check(
  extra.length === 0,
  `⛔ 무료 레포에 허용되지 않은 스킬: ${extra.join(', ')} — 무료판은 FREE ${FREE.length}종만 허용`,
);

// 4~6. 각 스킬 검사
for (const s of skills) {
  const t = fs.readFileSync(path.join(SKILL_DIR, s, 'SKILL.md'), 'utf8');
  check(t.includes('제2조의 세무대리'), `면책(세무사법 §2) 누락: ${s}`);
  check(!/대리\s*클릭/.test(t), `'대리 클릭' 문구 잔존: ${s}`);
  check(!/EULA\.md/.test(t), `무료판인데 EULA.md 참조 잔존(→ LICENSE.md여야 함): ${s}`);
}

// 7. 하드코딩 시크릿 0
const secretRe = /(sk-[A-Za-z0-9]{20}|AIza[A-Za-z0-9_-]{20}|ghp_[A-Za-z0-9]{20}|xox[baprs]-)/;
for (const fp of files) {
  if (/\.(md|json|txt|csv)$/.test(fp) && secretRe.test(fs.readFileSync(fp, 'utf8'))) fail(`하드코딩 시크릿 의심: ${path.relative(ROOT, fp)}`);
}
n++;

// 8. junk 0
const junk = files.filter((f) => /(\.pyc$|__pycache__|\.omc|\.DS_Store)/.test(f));
check(junk.length === 0, `junk 파일 ${junk.length}건`);

// 안전규칙 under_heading — 제목(접두 일치) 아래 절(같거나 상위 레벨 제목 전까지) 안에서만 must_contain을 찾는다 (C-10).
const sectionUnder = (text, heading) => {
  // HTML 주석 안에 원문을 숨기고 옆에 반대 문장을 쓰면 통과하던 구멍을 닫는다
  // (11차 M-2 실측). 다만 코드펜스 안의 '<!--' 는 예시 텍스트라 주석이 아니다 —
  // 통째로 지우면 짝 없는 '<!--' 하나가 제목까지 삼켜 정상 문서를 FAIL 시킨다(12차 M-3).
  // 그래서 펜스 밖 줄에서만 주석을 지운다.
  //   주석 안의 펜스는 펜스가 아니다 — 주석 판정을 먼저 하지 않으면 `<!--` + 펜스로
  //   감싸는 것만으로 은닉이 되살아나고(13차 H-1 실측), 주석 안의 홀수 펜스가 문서
  //   나머지를 통째로 '펜스 안'으로 만들어 정상 문서를 FAIL 시킨다(13차 M-1).
  {
    const out = []; let fence = false, inComment = false;
    for (const l of text.split('\n')) {
      let s = l;
      if (inComment) {
        const end = s.indexOf('-->');
        if (end < 0) { out.push(''); continue; }   // 주석 안 — 펜스도 토글하지 않는다
        s = s.slice(end + 3); inComment = false;
        // 주석이 닫힌 뒤 남은 조각은 아래 펜스·주석 판정을 그대로 탄다
      }
      if (!inComment && /^\s*(```|~~~)/.test(s)) { fence = !fence; out.push(s); continue; }
      if (fence) { out.push(s); continue; }
      for (;;) {
        const open = s.indexOf('<!--');
        if (open < 0) break;
        const close = s.indexOf('-->', open + 4);
        if (close < 0) { s = s.slice(0, open); inComment = true; break; }
        s = s.slice(0, open) + s.slice(close + 3);
      }
      out.push(s);
    }
    text = out.join('\n');
  }
  const lines = text.split('\n');
  // 코드 펜스 안의 '#'은 제목이 아니다. 정확 일치 제목을 우선하고 없으면 접두 일치 (리뷰 L-5).
  const heads = []; let fence = false;
  lines.forEach((l, i) => {
    if (/^\s*(```|~~~)/.test(l)) { fence = !fence; return; }
    if (fence) return;
    const m = l.match(/^(#{1,6})\s+(.*?)\s*$/); if (m) heads.push({ i, level: m[1].length, title: m[2] });
  });
  const hit = heads.find((h) => h.title === heading) || heads.find((h) => h.title.startsWith(heading));
  if (!hit) return null;
  const next = heads.find((h) => h.i > hit.i && h.level <= hit.level);
  return lines.slice(hit.i, next ? next.i : lines.length).join('\n');
};
// 9. 안전규칙 lint — 문구↔규칙 대조표(scripts/skill-rules.json) 기반.
// 마크다운 스킬의 회귀는 코드가 아니라 안전 문구 삭제로 일어난다 (2026-08-09 적대적 리뷰 13건의 회귀 방지).
const rulesPath = path.join(ROOT, 'scripts', 'skill-rules.json');
check(fs.existsSync(rulesPath), '안전규칙 대조표 누락: scripts/skill-rules.json');
if (fs.existsSync(rulesPath)) {
  for (const r of JSON.parse(fs.readFileSync(rulesPath, 'utf8')).rules) {
    const fp = path.join(ROOT, r.file);
    if (!fs.existsSync(fp)) { check(false, `안전규칙 [${r.id}] 대상 파일 없음: ${r.file}`); continue; }
    const t = fs.readFileSync(fp, 'utf8');
    const scope = r.under_heading ? sectionUnder(t, r.under_heading) : t;
    if (r.under_heading && scope === null) { check(false, `안전규칙 [${r.id}] 기준 제목 없음: "${r.under_heading}" (${r.file})`); continue; }
    // under_heading 이 문서 제목(레벨 1)이면 절 범위가 사실상 문서 전체라, 문구를 문서
    //   끝 부록으로 옮겨도 통과한다 (13차 H-2 와 같은 계열 — 세 규칙에서 실측).
    //   설정 단계에서 막는다.
    if (r.under_heading) {
      const head = t.split('\n').find((l) => {
        const m = l.match(/^(#{1,6})\s+(.*?)\s*$/);
        return m && (m[2] === r.under_heading || m[2].startsWith(r.under_heading));
      });
      check(!head || !/^#\s/.test(head),
        `안전규칙 [${r.id}]: under_heading "${r.under_heading}" 이 문서 제목(레벨 1)이라 절 범위가 문서 전체입니다 — 하위 제목을 지정할 것`);
    }
    for (const p of r.must_contain ?? [])
      check(scope.includes(p), `안전규칙 회귀 [${r.id}]: "${p}" 문구가 ${r.file}${r.under_heading ? `의 "${r.under_heading}" 절` : ''}에서 사라짐 — ${r.why}`);
    for (const p of r.must_not_contain ?? [])
      check(!t.includes(p), `금지문구 재유입 [${r.id}]: "${p}" 이(가) ${r.file}에 다시 들어옴 — ${r.why}`);
  }
}

// 9-1. 공통 문단 단일 소스 — shared/blocks 원본(Pro에서 내보냄)과 SKILL.md 인라인 본문 일치.
// 무료판에서 문단 하나만 고치면 다음 내보내기에 덮여 사라진다 — 원본은 Pro 저장소의 shared/blocks 이다.
try {
  const out = execFileSync('python3', ['-B', 'scripts/sync-blocks.py', '--check'], { cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  check(/공통 문단 일치/.test(out), '공통 문단 검사 결과 판정 불가');
} catch (error) {
  check(false, '공통 문단 드리프트: ' + (error.stderr?.toString() || error.message).split('\n').slice(0, 4).join(' '));
}

// 9-2. 업무 목록 md = JSON 생성 결과 (F-02) — 행은 JSON, 산문은 scripts/service-catalog.template.md (Pro에서 내보냄)
try {
  const out = execFileSync('python3', ['-B', 'scripts/render-service-catalog.py', '--check'], { cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  check(/생성 결과 일치/.test(out), '업무 목록 md 생성 검사 판정 불가');
} catch (error) {
  check(false, '업무 목록 md가 JSON 생성 결과와 다름: ' + (error.stderr?.toString() || error.message).split('\n').slice(0, 2).join(' '));
}

// 9-3. 병의원 워크시트 구조 — 문자열 매칭은 들여쓰기 재포맷 한 번에 뚫린다(실측).
//   구조는 JSON 으로 파싱해서 본다 (2026-09-19 적대적 리뷰 8차 M-3·M-4).
const wsPath = path.join(SKILL_DIR, 'tax-prep-kr', 'assets', 'exempt-status-medical-worksheet.json');
const MED_CHANNELS = ['uninsured', 'nhi_patient_share', 'nhi_insurer_share', 'casualty_insurance_and_mutual_aid',
  'medical_aid_patient_share', 'medical_aid_insurer_share', 'business_asset_disposal', 'other_revenue'];
check(fs.existsSync(wsPath), '병의원 워크시트 누락: ' + path.relative(ROOT, wsPath));
if (fs.existsSync(wsPath)) {
  let ws = null, parseError = '';
  try { ws = JSON.parse(fs.readFileSync(wsPath, 'utf8')); } catch (e) { parseError = e.message; }
  check(ws !== null, `병의원 워크시트 JSON 파싱 실패: ${parseError}`);
  if (ws) {
    const cr = ws.cash_receipt_selfcheck ?? {};
    check(Array.isArray(cr.by_tax_year),
      '병의원 워크시트: cash_receipt_selfcheck.by_tax_year 배열 없음 — 미가입기간을 과세기간별로 적을 곳이 사라진다');
    const revived = ['unenrolled_days', 'penalty_base_revenue', 'unenrolled_days_by_tax_year', 'penalty_base_revenue_by_tax_year']
      .filter((k) => Object.prototype.hasOwnProperty.call(cr, k));
    check(revived.length === 0,
      `병의원 워크시트: 과세기간별 배열을 단일 값으로 되돌린 키 [${revived.join(', ')}] — 두 해에 걸친 미가입기간을 한 번에 계산하게 된다`);
    const ch = ws.revenue_by_channel ?? {};
    // 개수만 세면 이름을 바꿔치기해도 통과한다 (9차 리뷰 M-1 실측) — 열 이름을 직접 본다.
    const lost = MED_CHANNELS.filter((k) => !Object.prototype.hasOwnProperty.call(ch, k));
    check(lost.length === 0, `병의원 워크시트: 검토표 열에 대응하는 채널이 빠짐 [${lost.join(', ')}]`);
    check(Array.isArray(ch.unmapped_revenue), '병의원 워크시트: unmapped_revenue 배열 없음 — 검토표에 칸이 없는 수입을 적을 곳이 사라진다');
    // 채널 안의 차이조정 칸까지 본다 (9차 리뷰 M-2 실측). 유형자산 양도·그 밖의 수입은
    // 서식이 금액만 규정하므로 3줄 칸을 요구하지 않는다.
    const needRows = MED_CHANNELS.filter((k) => !['business_asset_disposal', 'other_revenue'].includes(k));
    const rowKeys = ['computed_total', 'received_in_period', 'prior_period_treatment_received', 'current_period_treatment_unreceived'];
    const broken = needRows.filter((k) => rowKeys.some((r) => !Object.prototype.hasOwnProperty.call(ch[k] ?? {}, r)));
    check(broken.length === 0, `병의원 워크시트: 채널의 차이조정 칸이 빠짐 [${broken.join(', ')}]`);
  }
}

// 10. 하네스 무결성 — 훅 등록·설정이 무장해제되지 않았는지.
// 주의: CI는 push 후에 도는 사후 감지라 배포를 막지 못한다. 로컬 skill-gate가 1차 방어선.
const settingsPath = path.join(ROOT, '.claude', 'settings.json');
check(fs.existsSync(settingsPath), '하네스: .claude/settings.json 누락');
if (fs.existsSync(settingsPath)) {
  const s = fs.readFileSync(settingsPath, 'utf8');
  check(s.includes('skill-gate.sh') && s.includes('review-gate.sh'), '하네스: Stop 훅 등록이 빠짐 (skill-gate/review-gate)');
}
for (const f of ['.claude/hooks/skill-gate.sh', '.claude/hooks/review-gate.sh', '.claude/hooks/_lib.sh', '.claude/harness.config.sh', '.claude/agents/adversarial-reviewer.md'])
  check(fs.existsSync(path.join(ROOT, f)), `하네스 파일 누락: ${f}`);
const cfgPath = path.join(ROOT, '.claude', 'harness.config.sh');
if (fs.existsSync(cfgPath))
  check(/REVIEW_GATE="block"/.test(fs.readFileSync(cfgPath, 'utf8')), '하네스: REVIEW_GATE가 block이 아님 — 무장해제 의심 (의도적 변경이면 이 검사와 CLAUDE.md를 함께 갱신할 것)');

// 11. 도구 중립 계층 — pre-push 훅·AGENTS.md 동기화 (Codex·Aside·직접 편집 경로 방어)
check(fs.existsSync(path.join(ROOT, '.githooks', 'pre-push')), '도구 중립 게이트 누락: .githooks/pre-push');
check(fs.existsSync(path.join(ROOT, '.gitattributes')), '.gitattributes 누락 — Windows에서 훅 줄끝(CRLF) 깨짐 방지용');
const norm = (s) => s.replace(/^﻿/, '').replace(/\r\n/g, '\n').trimEnd();
const agentsP = path.join(ROOT, 'AGENTS.md'), claudeMdP = path.join(ROOT, 'CLAUDE.md');
check(fs.existsSync(agentsP), 'AGENTS.md 누락 (Codex 등 타 도구용 규칙 문서 — CLAUDE.md 복제본)');
if (fs.existsSync(agentsP) && fs.existsSync(claudeMdP))
  check(norm(fs.readFileSync(agentsP, 'utf8')) === norm(fs.readFileSync(claudeMdP, 'utf8')),
    'AGENTS.md ↔ CLAUDE.md 불일치(drift) — 한쪽만 고치지 말고 cp CLAUDE.md AGENTS.md 로 동기화할 것');
// hooksPath — 개발 클론(로컬 git 워크트리)에서 미설정이면 push 게이트가 통째로 꺼진
// "조용한 비활성" 상태이므로 경고가 아니라 **실격**으로 처리한다 (리뷰 M-1: 경고는
// 이미 게이트 안에 있는 경로에서만 보인다). CI와 pre-push의 커밋 추출 검사(CI=1,
// .git 없음)에서는 건너뛴다.
if (!process.env.CI) {
  let inRepo = false, hp = '';
  try { inRepo = execFileSync('git', ['rev-parse', '--is-inside-work-tree'], { cwd: ROOT, stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim() === 'true'; } catch {}
  if (inRepo) {
    try { hp = execFileSync('git', ['config', 'core.hooksPath'], { cwd: ROOT, stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim(); } catch {}
    const ok = hp === '.githooks' || hp.replace(/\\/g, '/').endsWith('/.githooks');
    check(ok, 'push 게이트 비활성: core.hooksPath 미설정 — 클론당 1회 실행: git config core.hooksPath .githooks');
  }
}

try {
  const result = execFileSync('python3', ['-B', 'scripts/check-service-catalog.py'], { cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  check(result.includes('업무 목록 통과'), '24개 업무 목록 확인 실패');
  execFileSync('python3', ['-B', 'scripts/test-service-catalog.py'], { cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  check(true, '실화면 부분 검증·완료 상태 변조 회귀');
} catch (error) {
  check(false, '24개 업무 경로·문서·완료근거 검사 실패: ' + (error.stderr?.toString() || error.message));
}

// 12. 데스크탑 번들 정합성 — README·시작 가이드가 "데스크탑용 .skill 6개"를 약속한다.
//   구버전 삭제만 커밋되고 신버전이 빠지면 배포 폴더가 빈 채로 main 에 올라간다.
//   빌드 파이프라인 자신은 번들을 만들기 **전에** 이 게이트를 돌므로 build.sh 의 사전점검
//   단계에서만 `--prebuild` 로 건너뛴다. 환경변수로 하면 pre-push·훅에 상속돼 조용히
//   꺼지므로 인자로 받고, 건너뛸 때는 stderr 에 경고를 남긴다.
const bundleDir = path.join(ROOT, '데스크탑용-skill파일');
const skipBundle = process.argv.includes('--prebuild');
if (skipBundle) console.error('⚠ 번들 검사 건너뜀 (--prebuild, 빌드 사전점검 전용) — 빌드 후 인자 없이 다시 실행할 것');
if (!skipBundle) {
  check(fs.existsSync(bundleDir), '데스크탑 번들 폴더 누락: 데스크탑용-skill파일/');
  if (fs.existsSync(bundleDir) && version) {
    const found = fs.readdirSync(bundleDir).filter((f) => f.endsWith('.skill')).sort();
    const want = FREE.map((s) => `${s}_v${version}.skill`).sort();
    check(found.join('|') === want.join('|'),
      `데스크탑 번들 불일치 — 있음 [${found.join(', ') || '없음'}] / 기대 [${want.join(', ')}] · bash scripts/build.sh 로 재생성할 것`);

    // 12-1. 번들 **내용**이 원본과 같은가. 존재만 보면 스킬 문서만 고치고 build.sh 없이
    //   커밋했을 때 게이트가 초록인 채 구버전 내용이 출고된다(실측). 외부 의존성 없이
    //   ZIP 중앙 디렉터리를 직접 읽어 바이트를 대조한다.
    const unzip = (buf) => {
      let eocd = -1;
      for (let i = buf.length - 22; i >= 0 && i >= buf.length - 22 - 65536; i--)
        if (buf.readUInt32LE(i) === 0x06054b50) { eocd = i; break; }
      if (eocd < 0) throw new Error('ZIP 끝 레코드를 찾지 못함');
      const count = buf.readUInt16LE(eocd + 10);
      let off = buf.readUInt32LE(eocd + 16);
      const entries = new Map();
      for (let k = 0; k < count; k++) {
        if (buf.readUInt32LE(off) !== 0x02014b50) throw new Error('중앙 디렉터리 손상');
        const method = buf.readUInt16LE(off + 10);
        const csize = buf.readUInt32LE(off + 20);
        const nameLen = buf.readUInt16LE(off + 28);
        const extraLen = buf.readUInt16LE(off + 30);
        const cmtLen = buf.readUInt16LE(off + 32);
        const localOff = buf.readUInt32LE(off + 42);
        const name = buf.toString('utf8', off + 46, off + 46 + nameLen).normalize('NFC');
        const dataStart = localOff + 30 + buf.readUInt16LE(localOff + 26) + buf.readUInt16LE(localOff + 28);
        const raw = buf.subarray(dataStart, dataStart + csize);
        entries.set(name, method === 8 ? zlib.inflateRawSync(raw) : Buffer.from(raw));
        off += 46 + nameLen + extraLen + cmtLen;
      }
      return entries;
    };
    for (const name of FREE) {
      const bundle = path.join(bundleDir, `${name}_v${version}.skill`);
      if (!fs.existsSync(bundle)) continue;
      const source = new Map();
      for (const fp of walk(path.join(SKILL_DIR, name)))
        source.set(path.relative(path.join(SKILL_DIR, name), fp).split(path.sep).join('/').normalize('NFC'), fs.readFileSync(fp));
      let problem = '';
      try {
        const entries = unzip(fs.readFileSync(bundle));
        const missing = [...source.keys()].filter((k) => !entries.has(k));
        const extra = [...entries.keys()].filter((k) => !source.has(k));
        const differ = [...source.entries()].filter(([k, v]) => entries.has(k) && !entries.get(k).equals(v)).map(([k]) => k);
        if (missing.length || extra.length || differ.length)
          problem = `누락 [${missing.join(', ')}] / 잉여 [${extra.join(', ')}] / 내용다름 [${differ.join(', ')}]`;
      } catch (e) { problem = `번들을 읽지 못함: ${e.message}`; }
      check(problem === '', `데스크탑 번들이 원본과 다름: ${name}_v${version}.skill — ${problem} · bash scripts/build.sh 로 재생성할 것`);
    }
  }
}

if (errors.length) {
  console.error(`\n✗ 무료판 게이트 실패 — ${errors.length}건 (검사 ${n}종)\n`);
  for (const e of errors) console.error(`  ✗ ${e}`);
  process.exit(1);
}
console.log(`✓ 무료판 게이트 통과 — ${n}종 검사 OK (무료 ${skills.length}종, Pro 스킬 유출 없음)`);
