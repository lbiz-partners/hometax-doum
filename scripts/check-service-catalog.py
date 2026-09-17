import datetime as dt
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
FREE = {'hometax-tax-hub', 'tax-prep-kr', 'receipt-classify-kr',
        'tax-invoice-hometax', 'vat-hometax', 'income-tax-hometax'}
LIVE_STAGES = {'login_required', 'public_entry', 'public_form',
               'public_query_result', 'public_simulation_compared'}
LIVE_BOOL_FIELDS = ('authenticated', 'input_verified', 'result_verified',
                    'workflow_verified', 'submission_verified', 'payment_verified')
DIRECT_RESULT_IDS = {'H12'}
SHA256 = re.compile(r'^[0-9a-f]{64}$')
AUTH_STAGES = {
    'authenticated_form', 'authenticated_query_result',
    'authenticated_no_data', 'authenticated_entry',
    'authorization_required', 'service_unavailable',
    'public_query_result', 'public_form',
}
AUTH_FORM_STAGES = {'authenticated_form', 'public_form'}
AUTH_QUERY_STAGES = {
    'authenticated_query_result', 'authenticated_no_data',
    'public_query_result',
}
AUTH_COMPLETION_FIELDS = (
    'workflow_verified', 'submission_verified',
    'payment_verified', 'issuance_verified',
)


def _official_hometax_url(value):
    parsed = urlparse(value)
    try:
        port = parsed.port
    except ValueError:
        return False
    return (parsed.scheme == 'https'
            and parsed.hostname in {'hometax.go.kr', 'www.hometax.go.kr'}
            and parsed.username is None and parsed.password is None
            and (port is None or port == 443))


def _check_timestamp(value, label, upper_bound):
    if type(value) is not str:
        raise ValueError(f'{label}: 확인일 형식 오류')
    try:
        parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as error:
        raise ValueError(f'{label}: 확인일 형식 오류') from error
    if parsed.date() > upper_bound:
        raise ValueError(f'{label}: 미래 확인일이 있습니다')


def _check_evidence(evidence, label):
    if type(evidence) is not list or not evidence:
        raise ValueError(f'{label}: 증거 목록 누락')
    for ref in evidence:
        if type(ref) is not dict:
            raise ValueError(f'{label}: 증거 형식 오류')
        filename = ref.get('file')
        if (type(filename) is not str or not filename.strip()
                or Path(filename).name != filename
                or filename in {'.', '..'}):
            raise ValueError(f'{label}: 증거 파일명 형식 오류')
        if type(ref.get('sha256')) is not str or not SHA256.fullmatch(ref['sha256']):
            raise ValueError(f'{label}: 증거 SHA-256 형식 오류')


def _check_simulations(report, catalog_ids, upper_bound, authenticated=False):
    simulations = report.get('simulations', [])
    if type(simulations) is not list:
        raise ValueError('실화면 모의계산 simulations 형식 오류')
    expected_stage = (
        'authenticated_simulation_compared'
        if authenticated else 'public_simulation_compared'
    )
    seen = set()
    for simulation in simulations:
        if type(simulation) is not dict or type(simulation.get('id')) is not str:
            raise ValueError('실화면 모의계산 ID 형식 오류')
        if simulation['id'] in seen:
            raise ValueError('실화면 모의계산 ID 중복')
        seen.add(simulation['id'])
        related = simulation.get('related_services')
        if (type(related) is not list or not related
                or any(item not in catalog_ids for item in related)):
            raise ValueError(f'{simulation["id"]}: 관련 업무 ID 오류')
        _check_timestamp(simulation.get('checked_at'), simulation['id'], upper_bound)
        if not _official_hometax_url(simulation.get('observed_url', '')):
            raise ValueError(f'{simulation["id"]}: 관찰 URL은 공식 hometax.go.kr이어야 합니다')
        if simulation.get('stage') != expected_stage:
            raise ValueError(f'{simulation["id"]}: 모의계산 단계 오류')
        if type(simulation.get('title')) is not str or not simulation['title'].strip():
            raise ValueError(f'{simulation["id"]}: 모의계산 제목 누락')
        if simulation.get('comparison_status') != 'matched_selected_fields':
            raise ValueError(f'{simulation["id"]}: 모의계산 대조 상태 오류')
        if (type(simulation.get('comparison_count')) is not int
                or simulation['comparison_count'] <= 0):
            raise ValueError(f'{simulation["id"]}: 모의계산 대조 항목 수 오류')
        path = simulation.get('representative_path')
        if (type(path) is not list or not path
                or any(type(part) is not str or not part.strip() for part in path)):
            raise ValueError(f'{simulation["id"]}: 모의계산 대표 경로 누락')
        for key in ('observation', 'remaining_limit'):
            if type(simulation.get(key)) is not str or not simulation[key].strip():
                raise ValueError(f'{simulation["id"]}: 모의계산 관찰 요약 누락')
        for key in LIVE_BOOL_FIELDS:
            if type(simulation.get(key)) is not bool:
                raise ValueError(f'{simulation["id"]}: 실화면 상태 형식 오류')
        if simulation['authenticated'] is not authenticated:
            raise ValueError(f'{simulation["id"]}: 인증 상태가 보고서 종류와 다릅니다')
        if (simulation['workflow_verified']
                or simulation['submission_verified'] or simulation['payment_verified']):
            raise ValueError(f'{simulation["id"]}: 인증·업무흐름·제출·납부 완료를 실화면 기록에서 확정할 수 없음')
        if authenticated and 'issuance_verified' in simulation:
            if simulation['issuance_verified'] is not False:
                raise ValueError(f'{simulation["id"]}: issuance_verified는 false여야 합니다')
        if not simulation['input_verified'] or not simulation['result_verified']:
            raise ValueError(f'{simulation["id"]}: 비교 모의계산의 입력·결과 확인 누락')
        _check_evidence(simulation.get('evidence'), simulation['id'])


def validate_live_ui(catalog, report):
    if type(report) is not dict:
        raise ValueError('실화면 보고서 형식 오류')
    for key in ('schema_version', 'version', 'checked_at', 'method', 'coverage', 'evidence_location'):
        if key not in report or (key not in {'schema_version'}
                                 and (type(report[key]) is not str or not report[key].strip())):
            raise ValueError(f'실화면 보고서 {key} 누락')
    if report['schema_version'] != 1 or report['version'] != catalog['version']:
        raise ValueError('실화면 보고서 버전이 업무 목록과 다릅니다')
    catalog_date = dt.date.fromisoformat(catalog['checked_at'])
    _check_timestamp(report['checked_at'], '실화면 보고서', catalog_date)
    checks = report.get('checks')
    expected_ids = [f'H{i:02}' for i in range(1, 25)]
    if (type(checks) is not list
            or [item.get('id') for item in checks if isinstance(item, dict)] != expected_ids):
        raise ValueError('실화면 보고서 24개 업무 ID의 누락·중복·순서 오류')
    by_id = {item['id']: item for item in catalog['services']}
    for check in checks:
        service = by_id[check['id']]
        label = f'{check["id"]} 실화면'
        if check.get('title') != service['title']:
            raise ValueError(f'{label}: 제목이 업무 목록과 다릅니다')
        _check_timestamp(check.get('checked_at'), label, catalog_date)
        path = check.get('representative_path')
        if (type(path) is not list or not path
                or any(type(part) is not str or not part.strip() for part in path)):
            raise ValueError(f'{label}: 대표 경로 누락')
        if not _official_hometax_url(check.get('observed_url', '')):
            raise ValueError(f'{label}: 관찰 URL은 공식 hometax.go.kr이어야 합니다')
        for key in ('observation', 'remaining_check'):
            if type(check.get(key)) is not str or not check[key].strip():
                raise ValueError(f'{label}: 관찰 요약 누락')
        stage = check.get('stage')
        if stage not in LIVE_STAGES:
            raise ValueError(f'{label}: 부분 검증 stage 오류')
        if service.get('live_ui_stage') != stage:
            raise ValueError(f'{label}: catalog live_ui_stage 불일치')
        if service.get('live_ui_verified') is not False:
            raise ValueError(f'{label}: 업무 전체 live_ui_verified는 false여야 합니다')
        for key in LIVE_BOOL_FIELDS:
            if type(check.get(key)) is not bool:
                raise ValueError(f'{label}: 실화면 상태 형식 오류')
        if (check['authenticated'] or check['workflow_verified']
                or check['submission_verified'] or check['payment_verified']):
            raise ValueError(f'{label}: 인증·업무흐름·제출·납부 완료를 실화면 기록에서 확정할 수 없음')
        if check['id'] not in DIRECT_RESULT_IDS and (check['input_verified'] or check['result_verified']):
            raise ValueError(f'{label}: 부분 확인을 업무 전체 결과 검증으로 표시할 수 없음')
        if check['id'] in DIRECT_RESULT_IDS:
            if stage != 'public_query_result':
                raise ValueError(f'{label}: 조회 결과 stage 오류')
            if not check['input_verified'] or not check['result_verified']:
                raise ValueError(f'{label}: 조회 입력·결과 확인 누락')
        elif stage == 'public_query_result':
            raise ValueError(f'{label}: 조회 결과 stage를 업무 전체 결과 검증으로 표시할 수 없음')
        _check_evidence(check.get('evidence'), label)
    _check_simulations(report, set(expected_ids), catalog_date)


def validate_authenticated_ui(catalog, report):
    if type(report) is not dict:
        raise ValueError('인증 후 실화면 보고서 형식 오류')
    for key in ('schema_version', 'version', 'checked_at', 'method',
                'coverage', 'evidence_policy'):
        if key not in report or (key not in {'schema_version'}
                                 and (type(report[key]) is not str
                                      or not report[key].strip())):
            raise ValueError(f'인증 후 실화면 보고서 {key} 누락')
    if report['schema_version'] != 1 or report['version'] != catalog['version']:
        raise ValueError('인증 후 실화면 보고서 버전이 업무 목록과 다릅니다')
    catalog_date = dt.date.fromisoformat(catalog['checked_at'])
    _check_timestamp(report['checked_at'], '인증 후 실화면 보고서', catalog_date)
    checks = report.get('checks')
    expected_ids = [f'H{i:02}' for i in range(1, 25)]
    if (type(checks) is not list
            or [item.get('id') for item in checks if isinstance(item, dict)] != expected_ids):
        raise ValueError('인증 후 실화면 보고서 24개 업무 ID의 누락·중복·순서 오류')
    by_id = {item['id']: item for item in catalog['services']}
    for check in checks:
        service = by_id[check['id']]
        label = f'{check["id"]} 인증 후 실화면'
        if check.get('title') != service['title']:
            raise ValueError(f'{label}: 제목이 업무 목록과 다릅니다')
        _check_timestamp(check.get('checked_at'), label, catalog_date)
        if not _official_hometax_url(check.get('observed_url', '')):
            raise ValueError(f'{label}: 관찰 URL은 공식 hometax.go.kr이어야 합니다')
        if check.get('context') not in {'personal', 'business'}:
            raise ValueError(f'{label}: context 형식 오류')
        if check.get('authenticated') is not True:
            raise ValueError(f'{label}: authenticated는 true여야 합니다')
        stage = check.get('stage')
        if stage not in AUTH_STAGES:
            raise ValueError(f'{label}: 인증 후 실화면 stage 오류')
        if type(check.get('screen_opened')) is not bool:
            raise ValueError(f'{label}: screen_opened 형식 오류')
        fields = check.get('form_fields_observed')
        if (type(fields) is not list
                or any(type(field) is not str or not field.strip() for field in fields)):
            raise ValueError(f'{label}: form_fields_observed 형식 오류')
        for key in ('query_executed', 'query_result_observed'):
            if type(check.get(key)) is not bool:
                raise ValueError(f'{label}: {key} 형식 오류')
        for key in AUTH_COMPLETION_FIELDS:
            if check.get(key) is not False:
                raise ValueError(f'{label}: {key}는 false여야 합니다')
        for key in ('observation', 'remaining_check'):
            if type(check.get(key)) is not str or not check[key].strip():
                raise ValueError(f'{label}: 관찰 요약 누락')
        if stage in AUTH_FORM_STAGES and (not check['screen_opened'] or not fields):
            raise ValueError(f'{label}: 입력 화면은 화면·정적 항목을 함께 확인해야 합니다')
        if stage in AUTH_QUERY_STAGES and (
                not check['query_executed'] or not check['query_result_observed']
                or not check['screen_opened']):
            raise ValueError(f'{label}: 조회 결과 stage는 화면·조회·결과를 함께 확인해야 합니다')
        if check['query_result_observed'] and (
                not check['query_executed'] or not check['screen_opened']):
            raise ValueError(f'{label}: query_result_observed 선행 확인 누락')
        if stage in {'authorization_required', 'service_unavailable'} and check['query_result_observed']:
            raise ValueError(f'{label}: 접근 차단·서비스 불가 단계에서 조회 결과를 확정할 수 없습니다')
        _check_evidence(check.get('evidence'), label)
    _check_simulations(report, set(expected_ids), catalog_date, authenticated=True)


def check(root=ROOT):
    base = root / 'skills/hometax-tax-hub/references'
    catalog = json.loads((base / 'service-catalog.json').read_text(encoding='utf-8'))
    version = re.search(r'^version:\s*([0-9.]+)$', (root / 'VERSION').read_text(), re.M).group(1)
    if catalog['schema_version'] != 1 or catalog['version'] != version:
        raise ValueError('업무 목록 버전이 제품 VERSION과 다릅니다')
    if dt.date.fromisoformat(catalog['checked_at']) > dt.date.today():
        raise ValueError('업무 목록에 미래 확인일이 있습니다')
    items = catalog['services']
    if [item['id'] for item in items] != [f'H{i:02}' for i in range(1, 25)]:
        raise ValueError('24개 업무 ID의 누락·중복·순서 오류')
    table = (base / 'service-catalog.md').read_text(encoding='utf-8')
    skills_root = (root / 'skills').resolve()
    pro = (skills_root / 'jongsose-prep-kr/SKILL.md').exists()
    for item in items:
        for key in ('title', 'free', 'completion_evidence', 'pro_role'):
            if type(item[key]) is not str or not item[key].strip():
                raise ValueError(f'{item["id"]}: 안내·역할·완료근거 누락')
        if item['skill'] not in FREE or not (skills_root / item['skill'] / 'SKILL.md').is_file():
            raise ValueError(f'{item["id"]}: 무료판 기본 진입점 없음')
        guide = (base / item['guide']).resolve()
        if skills_root not in guide.parents or not guide.is_file():
            raise ValueError(f'{item["id"]}: 안내 파일 누락 또는 경로 이탈')
        if item['section'] and not re.search(r'^#+ ' + re.escape(item['section']) + r'\b', guide.read_text(), re.M):
            raise ValueError(f'{item["id"]}: 안내 안에 지정한 절이 없음')
        if (not item['keywords'] or len(item['keywords']) != len(set(item['keywords']))
                or any(type(word) is not str or not word.strip() for word in item['keywords'])):
            raise ValueError(f'{item["id"]}: 검색어 형식 오류')
        if item['level'] not in ('guided_workflow', 'preparation_and_review') or type(item['live_ui_verified']) is not bool:
            raise ValueError(f'{item["id"]}: 지원·실화면 검증 수준 오류')
        line = next((line for line in table.splitlines() if line.startswith('| ' + item['id'] + ' |')), '')
        if not all(value in line for value in (item['title'], item['guide'], item['completion_evidence'])):
            raise ValueError(f'{item["id"]}: 표시용 목록과 JSON의 불일치')
        if pro:
            for tool in item['pro'].split(' + '):
                matches = list(skills_root.rglob(tool)) if '.' in tool else [skills_root / tool / 'SKILL.md']
                if not matches or not all(path.is_file() for path in matches):
                    raise ValueError(f'{item["id"]}: Pro 도구 실체 없음')
    live_report_name = catalog.get('live_ui_report')
    if live_report_name is not None:
        if (type(live_report_name) is not str or not live_report_name.strip()
                or Path(live_report_name).name != live_report_name):
            raise ValueError('실화면 보고서 파일명 형식 오류')
        live_report_path = base / live_report_name
        if not live_report_path.is_file():
            raise ValueError('실화면 보고서 파일 누락')
        validate_live_ui(catalog, json.loads(live_report_path.read_text(encoding='utf-8')))
        print(f'실화면 보고서 통과: 24개 업무 부분 단계·공식 URL·증거 형식')
    elif any('live_ui_stage' in item for item in items):
        raise ValueError('catalog live_ui_stage가 있으나 실화면 보고서가 없습니다')
    if not pro and (catalog.get('authenticated_ui_report') is not None or list(base.glob('authenticated-ui-*'))):
        raise ValueError('Free 공개판에 개인 계정 인증 후 관찰 기록을 포함할 수 없습니다')
    authenticated_report_name = catalog.get('authenticated_ui_report')
    if authenticated_report_name is not None:
        if (type(authenticated_report_name) is not str
                or not authenticated_report_name.strip()
                or Path(authenticated_report_name).name != authenticated_report_name):
            raise ValueError('인증 후 실화면 보고서 파일명 형식 오류')
        authenticated_report_path = base / authenticated_report_name
        if not authenticated_report_path.is_file():
            raise ValueError('인증 후 실화면 보고서 파일 누락')
        validate_authenticated_ui(
            catalog,
            json.loads(authenticated_report_path.read_text(encoding='utf-8')),
        )
        print('인증 후 실화면 보고서 통과: 24개 업무 단계·공식 URL·증거 형식')
    print(f'업무 목록 통과: 24개 무료 진입점·문서·완료근거' + (' 및 Pro 도구 확인' if pro else ' (Free)'))


if __name__ == '__main__':
    try:
        check()
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        print(f'업무 목록 실패: {error}', file=sys.stderr)
        sys.exit(1)
