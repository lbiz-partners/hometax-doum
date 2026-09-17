#!/usr/bin/env node
// 무료판(hometax-doum) 정합성 게이트 — GitHub Actions가 push마다 자동 실행.
// 핵심 목적: 유료(Pro) 스킬이 무료 레포에 실수로 섞이는 것을 차단 + 면책·금지문구 검사.
// 위반 시 exit 1 → GitHub이 빨간 X로 표시.
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
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
  const lines = text.split('\n');
  const start = lines.findIndex((l) => { const m = l.match(/^(#{1,6})\s+(.*)$/); return m && m[2].startsWith(heading); });
  if (start < 0) return null;
  const level = lines[start].match(/^(#+)/)[1].length;
  let end = lines.length;
  for (let i = start + 1; i < lines.length; i++) { const m = lines[i].match(/^(#{1,6})\s/); if (m && m[1].length <= level) { end = i; break; } }
  return lines.slice(start, end).join('\n');
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

if (errors.length) {
  console.error(`\n✗ 무료판 게이트 실패 — ${errors.length}건 (검사 ${n}종)\n`);
  for (const e of errors) console.error(`  ✗ ${e}`);
  process.exit(1);
}
console.log(`✓ 무료판 게이트 통과 — ${n}종 검사 OK (무료 ${skills.length}종, Pro 스킬 유출 없음)`);
