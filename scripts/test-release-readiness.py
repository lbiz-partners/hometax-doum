import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import ModuleType
import unittest
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


readiness = load_module('release_readiness', ROOT / 'scripts/release-readiness.py')


class ReleaseReadinessTests(unittest.TestCase):
    def fixture_archives(self, directory):
        for index, name in enumerate(readiness.archive_names(readiness.version())):
            with zipfile.ZipFile(directory / name, 'w') as archive:
                archive.writestr(f'payload-{index}.txt', f'Free release fixture {index}')

    def cli(self, *args):
        return subprocess.run(
            [sys.executable, '-B', str(ROOT / 'scripts/release-readiness.py'), *args],
            capture_output=True,
            encoding='utf-8',
            check=False,
        )

    def test_manifest_is_deterministic_and_sorted_without_paths_or_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self.fixture_archives(directory)
            first = self.cli('--write-manifest', '--directory', str(directory))
            self.assertEqual(first.returncode, 0, first.stderr)
            manifest, checksum = readiness.output_paths(readiness.version())
            manifest_path = directory / manifest
            first_manifest = manifest_path.read_bytes()
            first_checksum = (directory / checksum).read_bytes()
            second = self.cli('--write-manifest', '--directory', str(directory))
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(first_manifest, manifest_path.read_bytes())
            self.assertEqual(first_checksum, (directory / checksum).read_bytes())
            data = json.loads(first_manifest)
            self.assertEqual(data['edition'], 'free')
            self.assertEqual(data['version'], readiness.version())
            self.assertEqual(data['expected_tag'], f'v{readiness.version()}')
            self.assertEqual([entry['name'] for entry in data['files']], sorted(entry['name'] for entry in data['files']))
            self.assertNotIn(str(directory), first_manifest.decode('utf-8'))
            self.assertNotIn('created_at', data)

    def test_check_rejects_missing_tampered_and_malformed_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self.fixture_archives(directory)
            missing = self.cli('--check-manifest', '--directory', str(directory))
            self.assertNotEqual(missing.returncode, 0)
            written = self.cli('--write-manifest', '--directory', str(directory))
            self.assertEqual(written.returncode, 0, written.stderr)
            archive = directory / readiness.archive_names(readiness.version())[0]
            with archive.open('ab') as target:
                target.write(b'tampered')
            tampered = self.cli('--check-manifest', '--directory', str(directory))
            self.assertNotEqual(tampered.returncode, 0)
            self.assertIn('매니페스트 불일치', tampered.stderr)
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self.fixture_archives(directory)
            written = self.cli('--write-manifest', '--directory', str(directory))
            self.assertEqual(written.returncode, 0, written.stderr)
            manifest, _ = readiness.output_paths(readiness.version())
            (directory / manifest).write_text('{not json', encoding='utf-8')
            malformed = self.cli('--check-manifest', '--directory', str(directory))
            self.assertNotEqual(malformed.returncode, 0)
            self.assertIn('JSON 형식 오류', malformed.stderr)

    def test_check_manifest_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self.fixture_archives(directory)
            written = self.cli('--write-manifest', '--directory', str(directory))
            self.assertEqual(written.returncode, 0, written.stderr)
            before = {path.name: path.read_bytes() for path in directory.iterdir()}
            checked = self.cli('--check-manifest', '--directory', str(directory))
            after = {path.name: path.read_bytes() for path in directory.iterdir()}
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertEqual(checked.stdout.strip(), f'MANIFEST_OK {readiness.version()}')
            self.assertEqual(before, after)

    def test_tag_readiness_states_use_only_local_git_results(self):
        head = 'a' * 40

        def fake(dirty='', tag=None):
            def call(args, missing=False):
                if args == ['status', '--porcelain']:
                    return dirty
                if args == ['rev-parse', 'HEAD']:
                    return head
                if args[:3] == ['rev-parse', '--verify', '--quiet']:
                    return tag
                raise AssertionError(args)
            return call

        self.assertEqual(readiness.tag_readiness(fake()), 'READY_TO_TAG')
        self.assertEqual(readiness.tag_readiness(fake(' M skills/example.md')), 'BLOCKED_DIRTY')
        self.assertEqual(readiness.tag_readiness(fake(tag=head)), 'ALREADY_TAGGED')
        self.assertEqual(readiness.tag_readiness(fake(tag='b' * 40)), 'BLOCKED_TAG_CONFLICT')

    def test_tag_readiness_cli_does_not_mutate_the_worktree(self):
        before = subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT, capture_output=True, check=True).stdout
        result = self.cli('--tag-readiness')
        after = subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT, capture_output=True, check=True).stdout
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(result.stdout.strip(), {
            'READY_TO_TAG', 'ALREADY_TAGGED', 'BLOCKED_DIRTY', 'BLOCKED_TAG_CONFLICT',
        })
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main(verbosity=2)
