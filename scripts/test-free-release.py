import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_packages', ROOT / 'scripts/build_packages.py')
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


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

    def test_installer_help_and_check_are_readonly(self):
        for arg in ['--help', '--check']:
            with tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp) / 'skills'
                command = ['bash', str(ROOT / 'install.sh'), arg]
                if arg == '--check':
                    command += ['--target-dir', str(target)]
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(target.exists())

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
            command = ['bash', str(ROOT / 'install.sh'), '--target-dir', str(target)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(unrelated.read_text(), '사용자 원본')
            for rel, source in package.skill_files().items():
                self.assertEqual((target / rel).read_bytes(), source.read_bytes())
            logs = list((folder / '.hometax-doum-backups').glob('*/install-log.json'))
            self.assertEqual(len(logs), 1)
            self.assertEqual((logs[0].parent / 'tax-prep-kr/SKILL.md').read_text(), '이전 스킬')
            self.assertEqual(len(json.loads(logs[0].read_text())['skills']), 6)

    def test_source_install_destination_is_rejected(self):
        result = subprocess.run(['bash', str(ROOT / 'install.sh'), '--target-dir', str(ROOT / 'skills')], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)

    def test_installer_missing_bundle_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            shutil.copy2(ROOT / 'install.sh', folder / 'install.sh')
            result = subprocess.run(['bash', str(folder / 'install.sh'), '--check'], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
