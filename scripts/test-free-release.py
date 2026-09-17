import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
from types import ModuleType
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'모듈을 불러올 수 없습니다: {path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


package = load_module('build_packages', ROOT / 'scripts/build_packages.py')
installer = load_module('hometax_installer', ROOT / 'install.py')


class FreeReleaseTests(unittest.TestCase):
    def test_archive_roundtrip_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source = folder / '안내.md'
            source.write_text('무료 점검 안내', encoding='utf-8')
            expected = {'한글/안내.md': source}
            archive = folder / 'sample.zip'
            self.assertEqual(package.write_zip(archive, expected), 1)
            self.assertEqual(package.verify(archive, expected), 1)
            source.write_text('다른 버전', encoding='utf-8')
            with self.assertRaises(ValueError):
                package.verify(archive, expected)

    def test_extra_and_duplicate_archive_files_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source = folder / 'a.md'
            source.write_text('a')
            for names in [('a.md', 'secret.py'), ('a.md', 'a.md')]:
                archive = folder / 'sample.zip'
                with zipfile.ZipFile(archive, 'w') as z:
                    for name in names:
                        z.writestr(name, 'a')
                with self.assertRaises(ValueError):
                    package.verify(archive, {'a.md': source})

    def test_symlink_output_does_not_replace_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source = folder / 'source.md'
            source.write_text('원본')
            archive = folder / 'link.zip'
            archive.symlink_to(source)
            with self.assertRaises(ValueError):
                package.write_zip(archive, {'source.md': source})
            self.assertEqual(source.read_text(), '원본')

    def test_free_source_has_exact_six_skills_and_no_code(self):
        files = package.skill_files()
        self.assertEqual({name.split('/')[0] for name in files}, package.FREE)
        self.assertTrue(all(p.suffix in {'.md', '.json'} for p in files.values()))

    def test_current_desktop_bundles_match_sources(self):
        version = package.version()
        folder = ROOT / '데스크탑용-skill파일'
        bundles = sorted(folder.glob('*.skill'))
        expected_names = {f'{name}_v{version}.skill' for name in package.FREE}
        self.assertEqual({path.name for path in bundles}, expected_names)
        originals = package.skill_files()
        for bundle in bundles:
            skill = bundle.name.rsplit('_v', 1)[0]
            expected = {
                path[len(skill) + 1:]: source
                for path, source in originals.items()
                if path.startswith(skill + '/')
            }
            package.verify(bundle, expected)

    def test_user_guides_do_not_use_paid_wording(self):
        guides = [ROOT / 'README.md', ROOT / '시작-가이드.md']
        guides.extend(ROOT.glob('skills/**/*.md'))
        found = [str(path.relative_to(ROOT)) for path in guides if '유료' in path.read_text(encoding='utf-8')]
        self.assertEqual(found, [])

    def test_packaged_policy_document_matches_version(self):
        text = (ROOT / 'docs/industry-ui-sources-2026-09-17.md').read_text(encoding='utf-8')
        self.assertIn(f'제품 {package.version()}', text)

    def test_powershell_wrapper_is_windows_powershell_safe_ascii(self):
        self.assertTrue((ROOT / 'install.ps1').read_bytes().isascii())

    def _installers(self, *args):
        python = [sys.executable, '-B', str(ROOT / 'install.py'), *args]
        bash = ['bash', str(ROOT / 'install.sh'), *args]
        return [python, bash]

    def test_installer_help_and_check_are_readonly(self):
        for command in self._installers('--help') + self._installers('--check'):
            with tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp) / 'skills'
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                self.assertFalse(target.exists())
                if '--help' in command:
                    self.assertIn('install.py', result.stdout)
                    self.assertIn('Windows', result.stdout)

    def test_install_and_upgrade_keep_old_skills_and_unrelated_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            target = folder / 'skills'
            target.mkdir()
            unrelated = target / 'user-note.txt'
            unrelated.write_text('사용자 원본')
            existing = target / 'tax-prep-kr'
            existing.mkdir()
            (existing / 'SKILL.md').write_text('이전 스킬')
            command = [sys.executable, '-B', str(ROOT / 'install.py'), '--target-dir', str(target)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(unrelated.read_text(), '사용자 원본')
            for rel, source in package.skill_files().items():
                self.assertEqual((target / rel).read_bytes(), source.read_bytes())
            logs = list((folder / '.hometax-doum-backups').glob('*/install-log.json'))
            self.assertEqual(len(logs), 1)
            self.assertEqual((logs[0].parent / 'tax-prep-kr/SKILL.md').read_text(), '이전 스킬')
            self.assertEqual(len(json.loads(logs[0].read_text())['skills']), 6)

    def test_multi_target_failure_rolls_back_every_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            first = folder / 'first' / 'skills'
            second = folder / 'second' / 'skills'
            first_old = first / 'tax-prep-kr'
            second_old = second / 'tax-prep-kr'
            first_old.mkdir(parents=True)
            second_old.mkdir(parents=True)
            (first_old / 'SKILL.md').write_text('첫 번째 이전 스킬')
            (second_old / 'SKILL.md').write_text('두 번째 이전 스킬')
            original_hashes = installer.hashes
            second_resolved = second.resolve()

            def fail_on_second_target(path):
                if second_resolved in path.parents and path.name == 'hometax-tax-hub':
                    raise RuntimeError('가상 두 번째 대상 실패')
                return original_hashes(path)

            with mock.patch.object(installer, 'default_targets', return_value=[first, second]), \
                    mock.patch.object(installer, 'hashes', side_effect=fail_on_second_target):
                with self.assertRaises(RuntimeError):
                    installer.main([])

            self.assertEqual((first_old / 'SKILL.md').read_text(), '첫 번째 이전 스킬')
            self.assertEqual((second_old / 'SKILL.md').read_text(), '두 번째 이전 스킬')
            for target in (first, second):
                for name in installer.EXPECTED - {'tax-prep-kr'}:
                    self.assertFalse((target / name).exists())

    def test_source_install_destination_is_rejected(self):
        for command in self._installers('--target-dir', str(ROOT / 'skills')):
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0, command)

    def test_installer_missing_bundle_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            shutil.copy2(ROOT / 'install.sh', folder / 'install.sh')
            shutil.copy2(ROOT / 'install.py', folder / 'install.py')
            result = subprocess.run(['bash', str(folder / 'install.sh'), '--check'], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            result = subprocess.run([sys.executable, '-B', str(folder / 'install.py'), '--check'], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)

    def test_release_zip_includes_windows_installers(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            package.build(folder)
            version = package.version()
            archive = folder / f'hometax-doum-free-v{version}.zip'
            names = zipfile.ZipFile(archive).namelist()
            top = f'hometax-doum-free-v{version}'
            for name in ('install.sh', 'install.py', 'install.ps1'):
                self.assertIn(f'{top}/{name}', names)
                info = zipfile.ZipFile(archive).getinfo(f'{top}/{name}')
                mode = info.external_attr >> 16
                self.assertTrue(stat.S_ISREG(mode))
                self.assertEqual(stat.S_IMODE(mode), 0o755 if name != 'install.ps1' else 0o644)
            delivery = zipfile.ZipFile(folder / '홈택스-도움-스킬_Free_카톡전달용.zip').namelist()
            prefix = '홈택스-도움-스킬-Free/2_CLI용_폴더스킬/'
            for name in ('install.sh', 'install.py', 'install.ps1'):
                self.assertIn(prefix + name, delivery)

    def test_bash_wrapper_requires_install_py(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            shutil.copy2(ROOT / 'install.sh', folder / 'install.sh')
            result = subprocess.run(['bash', str(folder / 'install.sh'), '--check'], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('install.py', result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
