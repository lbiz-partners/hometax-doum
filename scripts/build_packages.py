import argparse
import hashlib
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import unicodedata
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FREE = {'hometax-tax-hub', 'tax-prep-kr', 'receipt-classify-kr',
        'tax-invoice-hometax', 'vat-hometax', 'income-tax-hometax'}
DOCS = ['README.md', 'VERSION', 'LICENSE.md', '시작-가이드.md',
        'docs/sole-owner-sources-2026-09-12.md']


def version():
    match = re.search(r'^version:\s*(\d+\.\d+\.\d+)\s*$', (ROOT / 'VERSION').read_text(), re.M)
    if not match:
        raise ValueError('VERSION 형식 오류')
    return match.group(1)


def skill_files():
    skills = ROOT / 'skills'
    if skills.is_symlink() or {p.name for p in skills.iterdir()} != FREE:
        raise ValueError('무료 여섯 스킬과 정확히 일치해야 합니다')
    files = {}
    for p in sorted(skills.rglob('*')):
        if p.is_symlink():
            raise ValueError('심볼릭링크 원본은 배포할 수 없습니다')
        if p.is_file():
            if p.suffix not in {'.md', '.json'}:
                raise ValueError('무료판에는 안내 Markdown과 입력 JSON만 포함할 수 있습니다')
            files[p.relative_to(skills).as_posix()] = p
    return files


def verify(archive, expected):
    with zipfile.ZipFile(archive) as z:
        entries = z.infolist()
        names = [unicodedata.normalize('NFC', p.filename) for p in entries]
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise ValueError('ZIP 파일 목록 불일치 또는 중복')
        for entry, name in zip(entries, names):
            if Path(name).is_absolute() or '..' in Path(name).parts or stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError('ZIP 경로 또는 링크 오류')
            if any(ord(c) > 127 for c in name) and not entry.flag_bits & 0x800:
                raise ValueError('한글 ZIP 경로 UTF-8 누락')
            source = expected[name]
            if source.is_symlink() or z.read(entry) != source.read_bytes():
                raise ValueError('ZIP 내용이 원본과 다릅니다')
    return len(expected)


def write_zip(output, expected):
    if output.is_symlink():
        raise ValueError('출력 ZIP 심볼릭링크는 허용하지 않습니다')
    normalized = {unicodedata.normalize('NFC', name): p for name, p in expected.items()}
    if len(normalized) != len(expected):
        raise ValueError('정규화 후 중복 경로')
    fd, temporary = tempfile.mkstemp(prefix='.hometax-free-', suffix='.zip', dir=output.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as z:
            for name, source in sorted(normalized.items()):
                if source.is_symlink():
                    raise ValueError('링크된 배포 원본')
                entry = zipfile.ZipInfo(name)
                entry.flag_bits |= 0x800
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.external_attr = (0o755 if source.name == 'install.sh' else 0o644) << 16
                z.writestr(entry, source.read_bytes())
        count = verify(temporary, normalized)
        os.replace(temporary, output)
        return count
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def build(directory):
    v = version()
    originals = skill_files()
    bundles = ROOT / '데스크탑용-skill파일'
    if bundles.is_symlink():
        raise ValueError('번들 출력 폴더 링크 금지')
    bundles.mkdir(exist_ok=True)
    current = []
    for name in sorted(FREE):
        output = bundles / f'{name}_v{v}.skill'
        write_zip(output, {p[len(name)+1:]: source for p, source in originals.items() if p.startswith(name + '/')})
        current.append(output)
    for stale in bundles.glob('*.skill'):
        if stale not in current:
            archive = bundles / 'previous'
            archive.mkdir(exist_ok=True)
            destination = archive / stale.name
            if destination.exists():
                raise ValueError('이전 번들 보관 위치에 같은 파일이 있습니다')
            os.replace(stale, destination)
    layouts = [('delivery', '홈택스-도움-스킬_Free_카톡전달용.zip'),
               ('snapshot', f'hometax-doum-free-v{v}.zip')]
    hashes = []
    for layout, filename in layouts:
        delivery = layout == 'delivery'
        top = '홈택스-도움-스킬-Free' if delivery else f'hometax-doum-free-v{v}'
        expected = {f'{top}/{name}': ROOT / name for name in DOCS}
        prefix = '2_CLI용_폴더스킬/' if delivery else ''
        expected[f'{top}/{prefix}install.sh'] = ROOT / 'install.sh'
        expected.update({f'{top}/{prefix}skills/{name}': source for name, source in originals.items()})
        desktop = '1_데스크탑용_skill파일' if delivery else '데스크탑용-skill파일'
        expected.update({f'{top}/{desktop}/{p.name}': p for p in current})
        output = directory / filename
        count = write_zip(output, expected)
        digest = hashlib.sha256(output.read_bytes()).hexdigest()
        hashes.append(f'{digest}  {filename}\n')
        print(f'무료 ZIP 검증 완료: {filename} / {count}파일 / SHA-256 {digest}')
    checksum = directory / f'hometax-doum-free-v{v}.sha256'
    if checksum.is_symlink():
        raise ValueError('SHA 출력 링크 금지')
    checksum.write_text(''.join(hashes), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='무료판 배포 패키지 빌드·원본 대조')
    parser.add_argument('--directory', type=Path, default=ROOT.parent)
    args = parser.parse_args()
    if not args.directory.is_dir() or args.directory.is_symlink():
        parser.error('실제 출력 폴더가 필요합니다')
    try:
        build(args.directory)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f'무료판 빌드 실패: {exc}', file=sys.stderr)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
