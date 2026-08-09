#!/usr/bin/env node
// 무료판(hometax-doum) 정합성 게이트 — GitHub Actions가 push마다 자동 실행.
// 핵심 목적: 유료(Pro) 스킬이 무료 레포에 실수로 섞이는 것을 차단 + 면책·금지문구 검사.
// 위반 시 exit 1 → GitHub이 빨간 X로 표시.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SKILL_DIR = path.join(ROOT, 'skills');
const errors = [];
const fail = (m) => errors.push(m);
let n = 0;
const check = (cond, m) => { n++; if (!cond) fail(m); };

const FREE = ['hometax-tax-hub', 'income-tax-hometax', 'receipt-classify-kr', 'tax-invoice-hometax', 'tax-prep-kr', 'vat-hometax'];
const PRO = ['jongsose-prep-kr', 'withholding-tax-hometax'];

const skills = fs.readdirSync(SKILL_DIR).filter((d) => fs.existsSync(path.join(SKILL_DIR, d, 'SKILL.md')));

// 1. 유료 스킬 유출 방지 (제일 중요)
for (const pro of PRO) check(!skills.includes(pro), `⛔ 유료(Pro) 스킬이 무료 레포에 섞임: ${pro} — 삭제 필요`);

// 2. 엔진 파일 유출 방지 (무료는 마크다운만)
const walk = (dir, acc = []) => {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const fp = path.join(dir, e.name);
    if (e.isDirectory()) { if (!['.git', '__pycache__', '.omc'].includes(e.name)) walk(fp, acc); }
    else acc.push(fp);
  }
  return acc;
};
const files = walk(SKILL_DIR);
const engines = files.filter((f) => /\.(py|mjs|cjs)$/.test(f));
check(engines.length === 0, `⛔ 무료 레포에 계산 엔진 파일 유출: ${engines.map((f) => path.relative(ROOT, f)).join(', ')}`);

// 3. 무료 6종이 모두 있는가
for (const s of FREE) check(skills.includes(s), `무료 스킬 누락: ${s}`);

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
  if (/\.(md|json|txt)$/.test(fp) && secretRe.test(fs.readFileSync(fp, 'utf8'))) fail(`하드코딩 시크릿 의심: ${path.relative(ROOT, fp)}`);
}
n++;

// 8. junk 0
const junk = files.filter((f) => /(\.pyc$|__pycache__|\.omc|\.DS_Store)/.test(f));
check(junk.length === 0, `junk 파일 ${junk.length}건`);

// 9. 안전규칙 lint — 문구↔규칙 대조표(scripts/skill-rules.json) 기반.
// 마크다운 스킬의 회귀는 코드가 아니라 안전 문구 삭제로 일어난다 (2026-08-09 적대적 리뷰 13건의 회귀 방지).
const rulesPath = path.join(ROOT, 'scripts', 'skill-rules.json');
check(fs.existsSync(rulesPath), '안전규칙 대조표 누락: scripts/skill-rules.json');
if (fs.existsSync(rulesPath)) {
  for (const r of JSON.parse(fs.readFileSync(rulesPath, 'utf8')).rules) {
    const fp = path.join(ROOT, r.file);
    if (!fs.existsSync(fp)) { check(false, `안전규칙 [${r.id}] 대상 파일 없음: ${r.file}`); continue; }
    const t = fs.readFileSync(fp, 'utf8');
    for (const p of r.must_contain ?? [])
      check(t.includes(p), `안전규칙 회귀 [${r.id}]: "${p}" 문구가 ${r.file}에서 사라짐 — ${r.why}`);
    for (const p of r.must_not_contain ?? [])
      check(!t.includes(p), `금지문구 재유입 [${r.id}]: "${p}" 이(가) ${r.file}에 다시 들어옴 — ${r.why}`);
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

if (errors.length) {
  console.error(`\n✗ 무료판 게이트 실패 — ${errors.length}건 (검사 ${n}종)\n`);
  for (const e of errors) console.error(`  ✗ ${e}`);
  process.exit(1);
}
console.log(`✓ 무료판 게이트 통과 — ${n}종 검사 OK (무료 ${skills.length}종, Pro 스킬 유출 없음)`);
