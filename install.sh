#!/usr/bin/env bash
# 홈택스 도움 무료판 — 의존성 검사 후 설치. 기존 스킬은 폴더째 백업하여 보존한다.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  cat <<'HELP'
사용: bash install.sh [--check] [--target-dir PATH]
  인자 없음        감지한 Aside / Claude Code / Codex 스킬 폴더에 설치
  --check          Python·스킬 원본 검사만 수행 (파일 변경 없음)
  --target-dir     지정한 스킬 폴더 하나에만 설치 (격리 시험에도 사용)
설치 스크립트: Python 3.10 이상. 무료 스킬 사용에는 계산 엔진이 필요하지 않습니다.
기존 같은 이름의 스킬은 대상 폴더 상위 .hometax-doum-backups/에 보존합니다.
HELP
  exit 0
fi
command -v python3 >/dev/null 2>&1 || { echo 'Python 3.10 이상이 필요합니다.' >&2; exit 1; }
exec python3 -B - "$HERE" "$@" <<'PY'
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

source = Path(sys.argv[1]) / 'skills'
parser = argparse.ArgumentParser(description='홈택스 도움 무료판 CLI 설치')
parser.add_argument('--check', action='store_true')
parser.add_argument('--target-dir', type=Path)
args = parser.parse_args(sys.argv[2:])
if sys.version_info < (3, 10):
    parser.exit(1, 'Python 3.10 이상이 필요합니다.\n')
if source.is_symlink() or not source.is_dir():
    parser.exit(1, '동봉 skills/ 폴더가 없습니다. 패키지를 다시 확인하세요.\n')
skills = sorted(p for p in source.iterdir() if p.is_dir() and (p / 'SKILL.md').is_file())
expected = {'hometax-tax-hub', 'tax-prep-kr', 'receipt-classify-kr', 'tax-invoice-hometax', 'vat-hometax', 'income-tax-hometax'}
if {p.name for p in skills} != expected:
    parser.exit(1, f'무료 스킬 6종이 필요합니다. 발견: {len(skills)}종\n')
for skill in skills:
    if any(p.is_file() and p.suffix not in {'.md', '.json'} for p in skill.rglob('*')):
        parser.exit(1, '무료 스킬에는 안내와 입력 템플릿만 허용합니다.\n')
    if skill.is_symlink() or any(p.is_symlink() for p in skill.rglob('*')):
        parser.exit(1, f'원본에 심볼릭링크가 있습니다: {skill.name}. 설치 중단.\n')
print(f'환경 확인: Python {sys.version.split()[0]} / 무료 스킬 {len(skills)}종')
if args.check:
    print('검사 완료 — 설치 파일을 변경하지 않았습니다.')
    raise SystemExit(0)
home_dir = Path.home()
targets = [args.target_dir] if args.target_dir else [
    home_dir / relative for app, relative in (
        ('.aside', '.aside/u/0/agents/main/skills/user'),
        ('.claude', '.claude/skills'),
        ('.codex', '.codex/skills')) if (home_dir / app).is_dir()]
targets = list(dict.fromkeys(p.expanduser().resolve() for p in targets))
if not targets:
    parser.exit(1, '대상 앱을 찾지 못했습니다. --target-dir <스킬 폴더>로 지정하세요.\n')

def hashes(folder):
    return {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts
            and p.suffix != '.pyc' and p.name != '.DS_Store'}

for target in targets:
    if target == source.resolve() or source.resolve() in target.parents or target in source.resolve().parents:
        parser.exit(1, '설치 대상은 배포 원본과 분리된 폴더여야 합니다.\n')
    target.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup = target.parent / '.hometax-doum-backups' / stamp
    journal = []
    stage = Path(tempfile.mkdtemp(prefix='.hometax-install-', dir=target.parent))
    try:
        for skill in skills:
            shutil.copytree(skill, stage / skill.name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
        backup.mkdir(parents=True)
        for skill in skills:
            dest = target / skill.name
            saved = backup / skill.name
            had_old = dest.exists() or dest.is_symlink()
            if had_old:
                os.replace(dest, saved)
            journal.append({'skill': skill.name, 'had_old': had_old, 'installed': False})
            os.replace(stage / skill.name, dest)
            journal[-1]['installed'] = True
            if hashes(dest) != hashes(skill):
                raise RuntimeError(f'설치 파일 대조 실패: {skill.name}')
        (backup / 'install-log.json').write_text(json.dumps({'target': str(target), 'skills': journal}, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        for row in reversed(journal):
            dest = target / row['skill']
            if row['installed']:
                os.replace(dest, stage / row['skill'])
            if row['had_old']:
                os.replace(backup / row['skill'], dest)
        raise
    finally:
        shutil.rmtree(stage)  # 이번 실행이 만든 임시 복사본만 정리
    print(f'설치·파일 대조 완료: {target}')
    print(f'이전 스킬 백업·설치 기록: {backup}')
print("새 대화에서 '세무 도와줘'로 호출하고 무료 안내가 시작되는지 확인하세요. 파일 설치와 앱의 스킬 인식은 별도입니다.")
PY
