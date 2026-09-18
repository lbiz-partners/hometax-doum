#!/usr/bin/env python3
"""service-catalog.md를 service-catalog.json에서 생성한다 — 표 두 개의 이중 관리 제거 (F-02, 2026-09-17).

  python3 scripts/render-service-catalog.py --check   현재 md == 생성 결과인지 (게이트)
  python3 scripts/render-service-catalog.py --apply   md를 다시 생성

산문은 scripts/service-catalog.template.md 에, 24개 업무 행은 JSON에 있다. 행을 고치려면 JSON을 고친다.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / 'skills/hometax-tax-hub/references'
TEMPLATE = ROOT / 'scripts/service-catalog.template.md'


def render() -> str:
    catalog = json.loads((REF / 'service-catalog.json').read_text(encoding='utf-8'))
    svc, pro = [], []
    for item in catalog['services']:
        guide = f"[{item['title']}]({item['guide']})" + (f"의 {item['section']}" if item.get('section') else '')
        svc.append(f"| {item['id']} | {'·'.join(item['keywords'])} | {guide} | {item['completion_evidence']} |")
        pro.append(f"| {item['id']} {item['title']} | {item['pro_role']} | `{item['pro']}` |")
    text = TEMPLATE.read_text(encoding='utf-8')
    return text.replace('{{SERVICE_ROWS}}', '\n'.join(svc), 1), pro


PRO_TABLE_RE = __import__('re').compile(r'(<!-- pro-table:start -->\n)(.*?)(<!-- pro-table:end -->)', __import__('re').S)


def render_pro_integration(pro_rows) -> str:
    text = (REF / 'pro-integration.md').read_text(encoding='utf-8')
    table = '| 업무 | 추가 작업 | 도구 |\n|---|---|---|\n' + '\n'.join(pro_rows) + '\n'
    if not PRO_TABLE_RE.search(text):
        raise SystemExit('pro-integration.md에 <!-- pro-table:start/end --> 마커가 없습니다')
    return PRO_TABLE_RE.sub(lambda m: f'{m.group(1)}{table}{m.group(3)}', text, count=1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--check', action='store_true'); g.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    target = REF / 'service-catalog.md'
    integration = REF / 'pro-integration.md'
    rendered, pro_rows = render()
    rendered_pro = render_pro_integration(pro_rows)
    if a.apply:
        target.write_text(rendered, encoding='utf-8'); integration.write_text(rendered_pro, encoding='utf-8')
        print('✓ service-catalog.md · pro-integration.md 표 생성'); return 0
    bad = []
    if target.read_text(encoding='utf-8') != rendered: bad.append('service-catalog.md')
    if integration.read_text(encoding='utf-8') != rendered_pro: bad.append('pro-integration.md(Pro 표)')
    if bad:
        print(f"✗ {', '.join(bad)}가 JSON 생성 결과와 다릅니다 — 행은 JSON, 산문은 scripts/service-catalog.template.md 를 고친 뒤 --apply", file=sys.stderr)
        return 1
    print('✓ 업무 목록 md 생성 결과 일치'); return 0


if __name__ == '__main__':
    raise SystemExit(main())
