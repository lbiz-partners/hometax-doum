import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'scripts/check-service-catalog.py'
SPEC = importlib.util.spec_from_file_location('check_service_catalog_free', MODULE_PATH)
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


def make_synthetic_authenticated_report(catalog):
    stages = (
        'authenticated_form', 'authenticated_query_result',
        'authenticated_no_data', 'authenticated_entry',
        'authorization_required', 'service_unavailable',
        'public_query_result', 'public_form',
    )
    checks = []
    checked_at = f"{catalog['checked_at']}T00:00:00Z"
    for index, service in enumerate(catalog['services']):
        stage = stages[index % len(stages)]
        is_form = stage in {'authenticated_form', 'public_form'}
        is_query = stage in {
            'authenticated_query_result', 'authenticated_no_data',
            'public_query_result',
        }
        checks.append({
            'id': service['id'],
            'title': service['title'],
            'checked_at': checked_at,
            'observed_url': f"https://hometax.go.kr/websquare/synthetic/{service['id']}",
            'context': 'personal' if index % 2 == 0 else 'business',
            'authenticated': True,
            'stage': stage,
            'screen_opened': stage != 'service_unavailable',
            'form_fields_observed': ['테스트 정적 항목'] if is_form else [],
            'query_executed': is_query,
            'query_result_observed': is_query,
            'workflow_verified': False,
            'submission_verified': False,
            'payment_verified': False,
            'issuance_verified': False,
            'observation': '테스트 전용 synthetic 화면 상태',
            'remaining_check': '실제 인증 후 담당자 재확인 필요',
            'evidence': [{
                'file': f"synthetic-auth-{service['id']}.yml",
                'sha256': '0' * 64,
            }],
        })
    return {
        'schema_version': 1,
        'version': catalog['version'],
        'checked_at': checked_at,
        'method': '테스트 전용 synthetic report factory',
        'coverage': '실제 홈택스 인증·화면 증거가 아닌 validator schema exercise',
        'evidence_policy': 'synthetic evidence is never a live verification claim',
        'checks': checks,
        'simulations': [{
            'id': 'S02',
            'related_services': ['H09', 'H10'],
            'checked_at': checked_at,
            'observed_url': 'https://hometax.go.kr/websquare/synthetic/S02',
            'stage': 'authenticated_simulation_compared',
            'title': '테스트 전용 인증 후 모의계산',
            'comparison_status': 'matched_selected_fields',
            'comparison_count': 4,
            'representative_path': ['세금신고', '테스트 전용 모의계산'],
            'observation': '테스트 전용 synthetic 대조 결과',
            'remaining_limit': '실제 신고·납부 검증은 별도 확인 필요',
            'authenticated': True,
            'input_verified': True,
            'result_verified': True,
            'workflow_verified': False,
            'submission_verified': False,
            'payment_verified': False,
            'issuance_verified': False,
            'evidence': [{
                'file': 'synthetic-auth-S02.json',
                'sha256': '0' * 64,
            }],
        }],
    }


class LiveUiCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = ROOT / 'skills/hometax-tax-hub/references'
        cls.catalog = json.loads((base / 'service-catalog.json').read_text(encoding='utf-8'))
        report_name = cls.catalog['live_ui_report']
        report_path = (ROOT / report_name) if report_name.startswith('docs/') else base / report_name
        cls.report = json.loads(report_path.read_text(encoding='utf-8'))

    def test_current_live_report_passes(self):
        CHECKER.validate_live_ui(copy.deepcopy(self.catalog), copy.deepcopy(self.report))

    def test_unverified_service_cannot_be_promoted_to_full_verified(self):
        catalog = copy.deepcopy(self.catalog)
        catalog['services'][0]['live_ui_verified'] = True
        with self.assertRaisesRegex(ValueError, '업무 전체 live_ui_verified'):
            CHECKER.validate_live_ui(catalog, copy.deepcopy(self.report))

    def test_partial_input_cannot_be_marked_on_unverified_service(self):
        report = copy.deepcopy(self.report)
        report['checks'][0]['input_verified'] = True
        with self.assertRaisesRegex(ValueError, '부분 확인을 업무 전체 결과 검증'):
            CHECKER.validate_live_ui(copy.deepcopy(self.catalog), report)

    def test_report_requires_official_hometax_url(self):
        report = copy.deepcopy(self.report)
        report['checks'][0]['observed_url'] = 'https://example.invalid/result'
        with self.assertRaisesRegex(ValueError, '공식 hometax.go.kr'):
            CHECKER.validate_live_ui(copy.deepcopy(self.catalog), report)

    def test_report_requires_canonical_24_id_order(self):
        report = copy.deepcopy(self.report)
        report['checks'][0], report['checks'][1] = report['checks'][1], report['checks'][0]
        with self.assertRaisesRegex(ValueError, '24개 업무 ID'):
            CHECKER.validate_live_ui(copy.deepcopy(self.catalog), report)

    def test_evidence_sha256_is_validated_without_reading_external_file(self):
        report = copy.deepcopy(self.report)
        report['checks'][0]['evidence'][0]['sha256'] = '0' * 63
        with self.assertRaisesRegex(ValueError, 'SHA-256 형식'):
            CHECKER.validate_live_ui(copy.deepcopy(self.catalog), report)

    def test_report_rejects_credentials_or_invalid_port_in_observed_url(self):
        for url in ('https://user:pass@hometax.go.kr/result', 'https://hometax.go.kr:444/result'):
            report = copy.deepcopy(self.report)
            report['checks'][0]['observed_url'] = url
            with self.subTest(url=url), self.assertRaisesRegex(ValueError, '공식 hometax.go.kr'):
                CHECKER.validate_live_ui(copy.deepcopy(self.catalog), report)

    def test_only_h12_may_use_public_query_result_stage(self):
        report = copy.deepcopy(self.report)
        catalog = copy.deepcopy(self.catalog)
        report['checks'][0]['stage'] = 'public_query_result'
        catalog['services'][0]['live_ui_stage'] = 'public_query_result'
        with self.assertRaisesRegex(ValueError, '조회 결과 stage'):
            CHECKER.validate_live_ui(catalog, report)

    def test_h12_result_flags_require_query_result_stage(self):
        report = copy.deepcopy(self.report)
        catalog = copy.deepcopy(self.catalog)
        report['checks'][11]['stage'] = 'public_entry'
        catalog['services'][11]['live_ui_stage'] = 'public_entry'
        with self.assertRaisesRegex(ValueError, '조회 결과 stage'):
            CHECKER.validate_live_ui(catalog, report)


class AuthenticatedUiCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = ROOT / 'skills/hometax-tax-hub/references'
        cls.catalog = json.loads((base / 'service-catalog.json').read_text(encoding='utf-8'))

    def test_synthetic_authenticated_report_factory_passes(self):
        report = make_synthetic_authenticated_report(self.catalog)
        CHECKER.validate_authenticated_ui(copy.deepcopy(self.catalog), report)

    def test_authenticated_report_requires_authenticated_true(self):
        report = make_synthetic_authenticated_report(self.catalog)
        report['checks'][0]['authenticated'] = False
        with self.assertRaisesRegex(ValueError, 'authenticated는 true'):
            CHECKER.validate_authenticated_ui(copy.deepcopy(self.catalog), report)

    def test_authenticated_report_requires_evidence_policy(self):
        report = make_synthetic_authenticated_report(self.catalog)
        report['evidence_policy'] = ''
        with self.assertRaisesRegex(ValueError, 'evidence_policy 누락'):
            CHECKER.validate_authenticated_ui(copy.deepcopy(self.catalog), report)

    def test_authenticated_report_requires_known_context(self):
        report = make_synthetic_authenticated_report(self.catalog)
        report['checks'][0]['context'] = 'unknown'
        with self.assertRaisesRegex(ValueError, 'context 형식 오류'):
            CHECKER.validate_authenticated_ui(copy.deepcopy(self.catalog), report)

    def test_authenticated_report_cannot_promote_completion_flags(self):
        report = make_synthetic_authenticated_report(self.catalog)
        report['checks'][0]['issuance_verified'] = True
        with self.assertRaisesRegex(ValueError, 'issuance_verified는 false'):
            CHECKER.validate_authenticated_ui(copy.deepcopy(self.catalog), report)

    def test_authenticated_form_requires_static_fields(self):
        report = make_synthetic_authenticated_report(self.catalog)
        report['checks'][0]['form_fields_observed'] = []
        with self.assertRaisesRegex(ValueError, '입력 화면은 화면·정적 항목'):
            CHECKER.validate_authenticated_ui(copy.deepcopy(self.catalog), report)

    def test_authenticated_query_result_requires_query_and_screen(self):
        report = make_synthetic_authenticated_report(self.catalog)
        report['checks'][1]['query_executed'] = False
        with self.assertRaisesRegex(ValueError, '조회 결과 stage'):
            CHECKER.validate_authenticated_ui(copy.deepcopy(self.catalog), report)

    def test_authorization_stage_cannot_claim_query_result(self):
        report = make_synthetic_authenticated_report(self.catalog)
        report['checks'][4]['query_executed'] = True
        report['checks'][4]['query_result_observed'] = True
        with self.assertRaisesRegex(ValueError, '접근 차단·서비스 불가'):
            CHECKER.validate_authenticated_ui(copy.deepcopy(self.catalog), report)

    def test_authenticated_report_rejects_url_credentials(self):
        report = make_synthetic_authenticated_report(self.catalog)
        report['checks'][0]['observed_url'] = 'https://user:pass@hometax.go.kr/result'
        with self.assertRaisesRegex(ValueError, '공식 hometax.go.kr'):
            CHECKER.validate_authenticated_ui(copy.deepcopy(self.catalog), report)

    def test_authenticated_simulation_requires_authenticated_state(self):
        report = make_synthetic_authenticated_report(self.catalog)
        report['simulations'][0]['authenticated'] = False
        with self.assertRaisesRegex(ValueError, '인증 상태가 보고서 종류'):
            CHECKER.validate_authenticated_ui(copy.deepcopy(self.catalog), report)

    def test_authenticated_simulation_cannot_promote_workflow(self):
        report = make_synthetic_authenticated_report(self.catalog)
        report['simulations'][0]['workflow_verified'] = True
        with self.assertRaisesRegex(ValueError, '인증·업무흐름·제출·납부 완료'):
            CHECKER.validate_authenticated_ui(copy.deepcopy(self.catalog), report)

    def test_authenticated_simulation_requires_authenticated_stage(self):
        report = make_synthetic_authenticated_report(self.catalog)
        report['simulations'][0]['stage'] = 'public_simulation_compared'
        with self.assertRaisesRegex(ValueError, '모의계산 단계 오류'):
            CHECKER.validate_authenticated_ui(copy.deepcopy(self.catalog), report)


class PublicPrivacyBoundaryTests(unittest.TestCase):
    def test_rejects_authenticated_report_in_free(self):
        import tempfile
        import shutil
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'free'
            shutil.copytree(ROOT / 'skills', root / 'skills')
            shutil.copy2(ROOT / 'VERSION', root / 'VERSION')
            base = root / 'skills/hometax-tax-hub/references'
            (base / 'authenticated-ui-checks.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'Free 공개판'):
                CHECKER.check(root)
            (base / 'authenticated-ui-checks.json').unlink()
            path = base / 'service-catalog.json'
            catalog = json.loads(path.read_text())
            catalog['authenticated_ui_report'] = 'other.json'
            path.write_text(json.dumps(catalog))
            with self.assertRaisesRegex(ValueError, 'Free 공개판'):
                CHECKER.check(root)


if __name__ == '__main__':
    unittest.main(verbosity=2)
