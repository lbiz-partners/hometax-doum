#!/usr/bin/env python3
"""공통 문단 단일 소스 동기화 — shared/blocks/*.md ↔ skills/**/*.md 인라인 본문.

  python3 scripts/sync-blocks.py --check   게이트용. 원본과 다른 인라인이 있으면 목록 출력 + exit 1
  python3 scripts/sync-blocks.py --apply   원본으로 인라인을 덮어쓴다

블록 종류
  disclaimer   마커 없이 '본 도구는 신고 준비를 돕는'으로 시작하는 줄의 본문을 통째로 맞춘다.
               코드 펜스 안(보고 포맷)에도 들어가므로 HTML 주석 마커를 쓸 수 없다.
  reuse-profile <!-- block:reuse-profile --> … <!-- /block --> 사이를 맞춘다.
  live-screen  Free 전용. 무료 저장소에서는 마커 블록으로 존재하고, Pro 원본에서는
               <!-- free-only:block live-screen --> 한 줄이다(export-free.py가 펼친다).
무료 저장소에도 같은 스크립트와 shared/blocks가 함께 내보내지므로 양쪽 게이트가 같은 검사를 한다.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOCKS = ROOT / 'shared' / 'blocks'
DISCLAIMER_HEAD = '본 도구는 신고 준비를 돕는'
# 줄 안에서 면책이 시작하는 지점부터, 줄 끝의 닫는 따옴표/백틱 직전까지.
# 표준 장문 면책(「세무사법」 제2조의 세무대리( … )만 대상. 스크립트 출력에 들어가는 한 줄 요약 고지는 건드리지 않는다.
# 1차: 표준 종결("… .md 참조.")까지만 매치 — 그 뒤 따옴표·괄호·꼬리 텍스트는 보존한다 (리뷰 M-2).
DISCLAIMER_RE = re.compile(r'본 도구는 신고 준비를 돕는(?=[^\n]*제2조의 세무대리\()[^\n]*?(?:EULA|LICENSE)\.md 참조\.')
# 2차: 종결 문장이 없는 옛 변형(줄 끝까지 면책만 있는 줄)에만 적용
DISCLAIMER_LEGACY_RE = re.compile(r'본 도구는 신고 준비를 돕는(?=[^\n]*제2조의 세무대리\()[^\n]*?(?=["`]?$)', re.M)
MARKER_RE = re.compile(r'(<!-- block:([a-z0-9-]+) -->\n)(.*?)(\n<!-- /block -->)', re.S)


def block_text(name: str) -> str:
    path = BLOCKS / f'{name}.md'
    if not path.is_file():
        raise SystemExit(f'공통 문단 원본 없음: {path.relative_to(ROOT)}')
    text = path.read_text(encoding='utf-8').strip('\n')
    if '\n' in text and name == 'disclaimer':
        raise SystemExit('disclaimer 원본은 한 줄이어야 합니다')
    return text


def targets() -> list[Path]:
    return sorted(p for p in (ROOT / 'skills').rglob('*.md') if p.is_file())


def sync_text(text: str, disclaimer: str) -> tuple[str, list[str]]:
    problems: list[str] = []
    new = DISCLAIMER_RE.sub(lambda m: disclaimer, text)
    # 1차에 안 잡힌 면책 문두(종결 문장 없는 변형)만 2차로 정리
    def legacy(m: re.Match) -> str:
        return disclaimer
    new = re.sub(r'(?m)^(?P<pre>[^\n]*?)(?P<body>' + DISCLAIMER_LEGACY_RE.pattern + r')',
                 lambda m: m.group('pre') + (m.group('body') if disclaimer in m.group(0) else disclaimer), new)
    if new != text:
        problems.append('disclaimer')
    text = new

    def repl(m: re.Match) -> str:
        name = m.group(2)
        body = block_text(name)
        if m.group(3) != body:
            problems.append(f'block:{name}')
        return f'{m.group(1)}{body}{m.group(4)}'

    text = MARKER_RE.sub(repl, text)
    if re.search(r'<!-- block:[a-z0-9-]+ -->', text) and not MARKER_RE.search(text):
        problems.append('block 마커 짝 불일치')
    return text, problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    disclaimer = block_text('disclaimer')
    if not disclaimer.startswith(DISCLAIMER_HEAD):
        raise SystemExit('disclaimer 원본이 표준 문두로 시작하지 않습니다')
    drift: list[str] = []
    seen_disclaimer = 0
    for path in targets():
        original = path.read_text(encoding='utf-8')
        seen_disclaimer += len(DISCLAIMER_RE.findall(original))
        updated, problems = sync_text(original, disclaimer)
        if problems:
            drift.append(f'{path.relative_to(ROOT)}: {", ".join(problems)}')
            if args.apply:
                path.write_text(updated, encoding='utf-8')
    # 리뷰 M-3: SKILL.md마다 표준 면책 전문이 최소 1회 있어야 한다 (축약·개작 면책은 동기화 대상에 안 잡힐 수 있으므로 총량으로 막는다)
    for path in sorted((ROOT / 'skills').glob('*/SKILL.md')):
        if path.read_text(encoding='utf-8').count(disclaimer) == 0:
            drift.append(f'{path.relative_to(ROOT)}: 표준 면책 전문 없음')
    if seen_disclaimer == 0:
        print('✗ 면책 문구를 가진 파일이 하나도 없습니다 — 검사 대상 오류', file=sys.stderr)
        return 1
    if drift and args.check:
        print('✗ 공통 문단 드리프트 — shared/blocks 원본과 다릅니다. python3 scripts/sync-blocks.py --apply 로 맞추세요:', file=sys.stderr)
        for line in drift:
            print(f'  · {line}', file=sys.stderr)
        return 1
    verb = '동기화' if args.apply else '일치'
    print(f'✓ 공통 문단 {verb} — 면책 {seen_disclaimer}곳, 변경 {len(drift)}파일')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
