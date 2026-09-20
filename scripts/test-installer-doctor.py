#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / 'install.py'
SKILLS = ROOT / 'skills'
EXPECTED = sorted(path.name for path in SKILLS.iterdir() if path.is_dir())
DISCLAIMER = '파일 상태만 확인했습니다. 앱의 스킬 인식 여부는 확인하지 않았습니다.'


def snapshot(folder: Path) -> dict[str, tuple[int, bytes | str]]:
    result: dict[str, tuple[int, bytes | str]] = {}
    for path in sorted(folder.rglob('*')):
        rel = str(path.relative_to(folder))
        if path.is_symlink():
            result[rel] = (path.lstat().st_mode, os.readlink(path))
        elif path.is_file():
            result[rel] = (path.stat().st_mode, path.read_bytes())
        else:
            result[rel] = (path.stat().st_mode, '')
    return result


class InstallerDoctorTests(unittest.TestCase):
    def copy_healthy(self, target: Path) -> None:
        target.mkdir(parents=True)
        for skill in EXPECTED:
            shutil.copytree(SKILLS / skill, target / skill)

    def doctor(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, '-B', str(INSTALLER), '--doctor', *args],
            capture_output=True,
            env=env,
        )

    def text(self, result: subprocess.CompletedProcess) -> str:
        return (result.stdout + result.stderr).decode('utf-8', errors='replace')

    def test_doctor_is_recognized_and_mutually_exclusive_with_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'skills'
            self.copy_healthy(target)
            good = self.doctor('--target-dir', str(target))
            self.assertEqual(good.returncode, 0, self.text(good))
            rejected = subprocess.run(
                [sys.executable, '-B', str(INSTALLER), '--doctor', '--check'],
                capture_output=True,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn('not allowed with argument', self.text(rejected))

    def test_healthy_trees_are_sorted_and_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'skills'
            self.copy_healthy(target)
            result = self.doctor('--target-dir', str(target))
            output = self.text(result)
            self.assertEqual(result.returncode, 0, output)
            lines = [line for line in output.splitlines() if line.startswith('HEALTHY ')]
            self.assertEqual(lines, [f'HEALTHY {name}' for name in EXPECTED])
            self.assertIn(DISCLAIMER, output)

    def test_absent_target_reports_all_six_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'skills'
            target.mkdir()
            result = self.doctor('--target-dir', str(target))
            output = self.text(result)
            self.assertNotEqual(result.returncode, 0, output)
            self.assertEqual(
                [line for line in output.splitlines() if line.startswith('MISSING ')],
                [f'MISSING {name}' for name in EXPECTED],
            )
            self.assertIn(DISCLAIMER, output)

    def test_mismatch_when_a_managed_tree_has_an_extra_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'skills'
            self.copy_healthy(target)
            (target / EXPECTED[0] / 'extra.md').write_text('extra', encoding='utf-8')
            result = self.doctor('--target-dir', str(target))
            output = self.text(result)
            self.assertNotEqual(result.returncode, 0, output)
            self.assertIn(f'MISMATCH {EXPECTED[0]} — 원본과 파일 해시가 다릅니다', output)

    def test_symlink_managed_destination_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'skills'
            target.mkdir()
            for skill in EXPECTED[1:]:
                shutil.copytree(SKILLS / skill, target / skill)
            (target / EXPECTED[0]).symlink_to(SKILLS / EXPECTED[0], target_is_directory=True)
            result = self.doctor('--target-dir', str(target))
            output = self.text(result)
            self.assertNotEqual(result.returncode, 0, output)
            self.assertIn(f'MISMATCH {EXPECTED[0]} — 심볼릭링크 대상은 점검하지 않습니다', output)

    def test_unrelated_sibling_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'skills'
            self.copy_healthy(target)
            (target / 'personal-note').mkdir()
            (target / 'personal-note' / 'memo.txt').write_text('preserve', encoding='utf-8')
            result = self.doctor('--target-dir', str(target))
            self.assertEqual(result.returncode, 0, self.text(result))

    def test_doctor_reconfigures_non_utf8_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'skills'
            self.copy_healthy(target)
            for encoding in ('cp1252', 'cp949'):
                with self.subTest(encoding=encoding):
                    env = os.environ.copy()
                    env['PYTHONIOENCODING'] = encoding
                    result = self.doctor('--target-dir', str(target), env=env)
                    self.assertEqual(result.returncode, 0, self.text(result))
                    self.assertIn(DISCLAIMER.encode(), result.stdout)

    def test_doctor_never_modifies_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'skills'
            self.copy_healthy(target)
            before = snapshot(target)
            result = self.doctor('--target-dir', str(target))
            after = snapshot(target)
            self.assertEqual(result.returncode, 0, self.text(result))
            self.assertEqual(after, before)

    def test_implicit_doctor_only_inspects_existing_targets_and_fails_when_none_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / 'home'
            home.mkdir()
            env = os.environ.copy()
            env['HOME'] = str(home)
            absent = self.doctor(env=env)
            self.assertNotEqual(absent.returncode, 0, self.text(absent))
            self.assertIn('대상 앱을 찾지 못했습니다', self.text(absent))

            target = home / '.codex' / 'skills'
            self.copy_healthy(target)
            present = self.doctor(env=env)
            self.assertEqual(present.returncode, 0, self.text(present))
            self.assertIn(f'점검 대상: {target}', self.text(present))


if __name__ == '__main__':
    unittest.main(verbosity=2)
