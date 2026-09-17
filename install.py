#!/usr/bin/env python3
# 홈택스 도움 무료판 — Windows/macOS/Linux 공통 설치기.
# 기존 스킬은 폴더째 백업하여 보존한다.
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'skills'
EXPECTED = {
    'hometax-tax-hub', 'tax-prep-kr', 'receipt-classify-kr',
    'tax-invoice-hometax', 'vat-hometax', 'income-tax-hometax',
}
HELP = '''사용: python install.py [--check] [--target-dir PATH]
  Windows:  py -3 install.py [--check] [--target-dir PATH]
  macOS/Linux:  python3 install.py  또는  bash install.sh
  인자 없음        감지한 Aside / Claude Code / Codex 스킬 폴더에 설치
  --check          Python·스킬 원본 검사만 수행 (파일 변경 없음)
  --target-dir     지정한 스킬 폴더 하나에만 설치 (격리 시험에도 사용)
설치 스크립트: Python 3.10 이상. 무료 스킬 사용에는 계산 엔진이 필요하지 않습니다.
기존 같은 이름의 스킬은 대상 폴더 상위 .hometax-doum-backups/에 보존합니다.
Claude Code 플러그인 설치와 .skill 업로드는 Python이 없어도 됩니다. README.md를 보세요.
'''


def ensure_unicode_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, 'reconfigure', None)
        if reconfigure:
            reconfigure(encoding='utf-8', errors='replace')


@dataclass
class Change:
    skill: str
    had_old: bool
    old_saved: bool = False
    installed: bool = False


@dataclass
class Operation:
    target: Path
    backup: Path
    stage: Path
    changes: list[Change] = field(default_factory=list)


def fail(parser: argparse.ArgumentParser, message: str) -> None:
    parser.exit(1, message if message.endswith('\n') else message + '\n')


def default_targets(home: Path) -> list[Path]:
    found: list[Path] = []
    for app_dir, skill_dir in (
        (home / '.aside', home / '.aside' / 'u' / '0' / 'skills' / 'user'),
        (home / '.claude', home / '.claude' / 'skills'),
        (home / '.codex', home / '.codex' / 'skills'),
    ):
        if app_dir.is_dir():
            found.append(skill_dir)
    legacy = home / '.aside' / 'u' / '0' / 'agents' / 'main' / 'skills' / 'user'
    if legacy.is_dir():
        found.append(legacy)
    return found


def hashes(folder: Path) -> dict[str, str]:
    return {
        str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in folder.rglob('*')
        if p.is_file() and '__pycache__' not in p.parts
        and p.suffix != '.pyc' and p.name != '.DS_Store'
    }


def no_target_message() -> str:
    home = Path.home()
    return (
        '대상 앱을 찾지 못했습니다. --target-dir <스킬 폴더>로 지정하세요.\n'
        f'  Windows Codex:   py -3 install.py --target-dir {home / ".codex" / "skills"}\n'
        f'  Windows Claude:  py -3 install.py --target-dir {home / ".claude" / "skills"}\n'
        f'  Windows Aside:   py -3 install.py --target-dir {home / ".aside" / "u" / "0" / "skills" / "user"}\n'
        '  macOS/Linux:     python3 install.py --target-dir ~/.codex/skills\n'
        '터미널 없이 쓰려면 데스크탑용 .skill 파일을 앱에 업로드하세요.\n'
    )


def path_exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def prepare_operation(target: Path, skills: list[Path]) -> Operation:
    target.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup = target.parent / '.hometax-doum-backups' / stamp
    stage = Path(tempfile.mkdtemp(prefix='.hometax-install-', dir=str(target.parent)))
    try:
        for skill in skills:
            shutil.copytree(
                skill, stage / skill.name,
                ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'),
            )
        backup.mkdir(parents=True)
        return Operation(target=target, backup=backup, stage=stage)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def apply_operation(operation: Operation, skills: list[Path]) -> None:
    for skill in skills:
        dest = operation.target / skill.name
        saved = operation.backup / skill.name
        change = Change(skill=skill.name, had_old=path_exists(dest))
        operation.changes.append(change)
        if change.had_old:
            os.replace(dest, saved)
            change.old_saved = True
        os.replace(operation.stage / skill.name, dest)
        change.installed = True
        if hashes(dest) != hashes(skill):
            raise RuntimeError(f'설치 파일 대조 실패: {skill.name}')


def write_install_log(operation: Operation) -> None:
    rows = [
        {'skill': change.skill, 'had_old': change.had_old, 'installed': change.installed}
        for change in operation.changes
    ]
    (operation.backup / 'install-log.json').write_text(
        json.dumps({'target': str(operation.target), 'skills': rows}, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )


def rollback_operation(operation: Operation) -> None:
    log = operation.backup / 'install-log.json'
    if log.exists():
        log.unlink()
    for change in reversed(operation.changes):
        dest = operation.target / change.skill
        staged = operation.stage / change.skill
        saved = operation.backup / change.skill
        if change.installed and path_exists(dest):
            os.replace(dest, staged)
        if change.old_saved and path_exists(saved):
            os.replace(saved, dest)
    try:
        operation.backup.rmdir()
    except OSError:
        pass


def main(argv: list[str] | None = None) -> int:
    ensure_unicode_output()
    parser = argparse.ArgumentParser(
        description='홈택스 도움 무료판 CLI 설치',
        add_help=False,
    )
    parser.add_argument('-h', '--help', action='store_true')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--target-dir', type=Path)
    args = parser.parse_args(argv)
    if args.help:
        sys.stdout.write(HELP)
        return 0
    if sys.version_info < (3, 10):
        fail(parser, 'Python 3.10 이상이 필요합니다.')
    if SOURCE.is_symlink() or not SOURCE.is_dir():
        fail(parser, '동봉 skills/ 폴더가 없습니다. 패키지를 다시 확인하세요.')
    skills = sorted(
        p for p in SOURCE.iterdir()
        if p.is_dir() and (p / 'SKILL.md').is_file()
    )
    if {p.name for p in skills} != EXPECTED:
        fail(parser, f'무료 스킬 6종이 필요합니다. 발견: {len(skills)}종')
    for skill in skills:
        if any(p.is_file() and p.suffix not in {'.md', '.json'} for p in skill.rglob('*')):
            fail(parser, '무료 스킬에는 안내와 입력 템플릿만 허용합니다.')
        if skill.is_symlink() or any(p.is_symlink() for p in skill.rglob('*')):
            fail(parser, f'원본에 심볼릭링크가 있습니다: {skill.name}. 설치 중단.')
    print(f'환경 확인: Python {sys.version.split()[0]} / 무료 스킬 {len(skills)}종')
    if args.check:
        print('검사 완료 — 설치 파일을 변경하지 않았습니다.')
        return 0
    targets = [args.target_dir] if args.target_dir else default_targets(Path.home())
    targets = list(dict.fromkeys(p.expanduser().resolve() for p in targets))
    if not targets:
        fail(parser, no_target_message())
    source = SOURCE.resolve()
    for target in targets:
        if target == source or source in target.parents or target in source.parents:
            fail(parser, '설치 대상은 배포 원본과 분리된 폴더여야 합니다.')

    operations: list[Operation] = []
    try:
        for target in targets:
            operations.append(prepare_operation(target, skills))
        for operation in operations:
            apply_operation(operation, skills)
        for operation in operations:
            write_install_log(operation)
    except Exception as install_error:
        rollback_errors = []
        for operation in reversed(operations):
            try:
                rollback_operation(operation)
            except Exception as rollback_error:
                rollback_errors.append(str(rollback_error))
        if rollback_errors:
            raise RuntimeError(
                '설치 실패 후 롤백을 완료하지 못했습니다: ' + '; '.join(rollback_errors)
            ) from install_error
        raise
    finally:
        for operation in operations:
            shutil.rmtree(operation.stage, ignore_errors=True)

    for operation in operations:
        print(f'설치·파일 대조 완료: {operation.target}')
        print(f'이전 스킬 백업·설치 기록: {operation.backup}')
    print("새 대화에서 '세무 도와줘'로 호출하고 무료 안내가 시작되는지 확인하세요. 파일 설치와 앱의 스킬 인식은 별도입니다.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
