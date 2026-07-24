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

if (errors.length) {
  console.error(`\n✗ 무료판 게이트 실패 — ${errors.length}건 (검사 ${n}종)\n`);
  for (const e of errors) console.error(`  ✗ ${e}`);
  process.exit(1);
}
console.log(`✓ 무료판 게이트 통과 — ${n}종 검사 OK (무료 ${skills.length}종, Pro 스킬 유출 없음)`);
