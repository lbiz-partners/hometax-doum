#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]


class ReadinessError(ValueError):
    pass


def version():
    match = re.search(r'^version:\s*(\d+\.\d+\.\d+)\s*$',
                      (ROOT / 'VERSION').read_text(encoding='utf-8'), re.M)
    if not match:
        raise ReadinessError('VERSION 형식 오류')
    return match.group(1)


def archive_names(product_version):
    return sorted([
        f'hometax-doum-free-v{product_version}.zip',
        '홈택스-도움-스킬_Free_카톡전달용.zip',
    ])


def output_paths(product_version):
    return (
        f'hometax-doum-free-v{product_version}.manifest.json',
        f'hometax-doum-free-v{product_version}.sha256',
    )


def require_directory(directory):
    if not directory.is_dir() or directory.is_symlink():
        raise ReadinessError('실제 출력 폴더가 필요합니다')


def require_regular_file(path, label):
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError as exc:
        raise ReadinessError(f'{label} 없음: {path.name}') from exc
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise ReadinessError(f'{label}은(는) 일반 파일이어야 합니다: {path.name}')


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def release_files(directory, product_version):
    records = []
    for name in archive_names(product_version):
        archive = directory / name
        require_regular_file(archive, 'Free ZIP')
        if not zipfile.is_zipfile(archive):
            raise ReadinessError(f'유효한 ZIP이 아닙니다: {name}')
        records.append({
            'name': name,
            'size': archive.stat().st_size,
            'sha256': sha256(archive),
        })
    return sorted(records, key=lambda record: record['name'])


def git_text(args, missing=False):
    result = subprocess.run(
        ['git', '-C', str(ROOT), *args],
        capture_output=True,
        encoding='utf-8',
        check=False,
    )
    if result.returncode:
        if missing:
            return None
        message = result.stderr.strip() or result.stdout.strip() or 'git 명령 실패'
        raise ReadinessError(message)
    return result.stdout.strip()


def manifest_data(directory):
    product_version = version()
    return {
        'edition': 'free',
        'expected_tag': f'v{product_version}',
        'files': release_files(directory, product_version),
        'source_commit': git_text(['rev-parse', 'HEAD']),
        'version': product_version,
    }


def manifest_bytes(data):
    return (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8')


def checksum_bytes(data):
    return ''.join(
        f"{record['sha256']}  {record['name']}\n"
        for record in data['files']
    ).encode('utf-8')


def write_file(path, contents):
    if path.is_symlink():
        raise ReadinessError(f'출력 심볼릭링크는 허용하지 않습니다: {path.name}')
    if path.exists() and not path.is_file():
        raise ReadinessError(f'출력 대상은 일반 파일이어야 합니다: {path.name}')
    descriptor, temporary = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as target:
            target.write(contents)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_manifest(directory):
    require_directory(directory)
    data = manifest_data(directory)
    manifest_name, checksum_name = output_paths(data['version'])
    write_file(directory / manifest_name, manifest_bytes(data))
    write_file(directory / checksum_name, checksum_bytes(data))
    return data


def check_manifest(directory):
    require_directory(directory)
    data = manifest_data(directory)
    manifest_name, checksum_name = output_paths(data['version'])
    manifest = directory / manifest_name
    checksum = directory / checksum_name
    require_regular_file(manifest, '매니페스트')
    require_regular_file(checksum, 'SHA-256 파일')
    try:
        parsed = json.loads(manifest.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReadinessError(f'매니페스트 JSON 형식 오류: {manifest.name}') from exc
    if parsed != data or manifest.read_bytes() != manifest_bytes(data):
        raise ReadinessError(f'매니페스트 불일치: {manifest.name}')
    if checksum.read_bytes() != checksum_bytes(data):
        raise ReadinessError(f'SHA-256 불일치: {checksum.name}')
    return data


def tag_readiness(git=git_text):
    product_version = version()
    expected_tag = f'v{product_version}'
    dirty = git(['status', '--porcelain'])
    if dirty:
        return 'BLOCKED_DIRTY'
    source_commit = git(['rev-parse', 'HEAD'])
    tag_commit = git(['rev-parse', '--verify', '--quiet', f'refs/tags/{expected_tag}^{{}}'], missing=True)
    if tag_commit is None:
        return 'READY_TO_TAG'
    if tag_commit == source_commit:
        return 'ALREADY_TAGGED'
    return 'BLOCKED_TAG_CONFLICT'


def main(argv=None):
    parser = argparse.ArgumentParser(description='Free 릴리스 매니페스트 및 로컬 태그 준비 상태')
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument('--write-manifest', action='store_true')
    actions.add_argument('--check-manifest', action='store_true')
    actions.add_argument('--tag-readiness', action='store_true')
    parser.add_argument('--directory', type=Path, default=ROOT.parent)
    args = parser.parse_args(argv)
    try:
        if args.write_manifest:
            data = write_manifest(args.directory)
            print(f"MANIFEST_WRITTEN {data['version']}")
        elif args.check_manifest:
            data = check_manifest(args.directory)
            print(f"MANIFEST_OK {data['version']}")
        else:
            print(tag_readiness())
    except (OSError, ReadinessError, zipfile.BadZipFile) as exc:
        print(f'릴리스 준비 실패: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
