import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


spec = importlib.util.spec_from_file_location("validate_routing", Path(__file__).with_name("validate-routing.py"))
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class RoutingValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="hometax-routing-validation-")
        self.addCleanup(self.temp.cleanup)
        self.routing = Path(self.temp.name) / "routing.jsonl"
        self.schema = validator.DEFAULT_SCHEMA
        with validator.DEFAULT_ROUTING.open(encoding="utf-8") as source:
            self.rows = [json.loads(line) for line in source if line.strip()]

    def write_rows(self, rows):
        with self.routing.open("w", encoding="utf-8") as output:
            for row in rows:
                output.write(json.dumps(row, ensure_ascii=False) + "\n")

    def test_current_contract_validates_for_all_editions(self):
        self.write_rows(self.rows)
        for edition in ("free", "pro", "both"):
            with self.subTest(edition=edition):
                result = validator.validate_routing(self.routing, self.schema, edition)
                self.assertEqual(result["rows"], len(self.rows))

    def test_invalid_edition_is_rejected(self):
        rows = [dict(row) for row in self.rows]
        rows[0]["edition"] = "enterprise"
        self.write_rows(rows)
        with self.assertRaisesRegex(validator.RoutingValidationError, "invalid edition"):
            validator.validate_routing(self.routing, self.schema, "both")

    def test_missing_required_coverage_is_rejected(self):
        rows = [dict(row) for row in self.rows]
        for row in rows:
            row["coverage"] = [tag for tag in row.get("coverage", []) if tag != "pharmacy"]
        self.write_rows(rows)
        with self.assertRaisesRegex(validator.RoutingValidationError, "missing required coverage: pharmacy"):
            validator.validate_routing(self.routing, self.schema, "both")

    def test_duplicate_id_is_rejected(self):
        rows = [dict(row) for row in self.rows]
        rows[1]["id"] = rows[0]["id"]
        self.write_rows(rows)
        with self.assertRaisesRegex(validator.RoutingValidationError, "duplicate id"):
            validator.validate_routing(self.routing, self.schema, "both")

    def test_edition_specific_expected_route_must_be_allowed(self):
        rows = [dict(row) for row in self.rows]
        rows[7]["expected_skill_free"] = "withholding-tax-hometax"
        self.write_rows(rows)
        with self.assertRaisesRegex(validator.RoutingValidationError, "expected_skill_free is not allowed for free"):
            validator.validate_routing(self.routing, self.schema, "free")


if __name__ == "__main__":
    unittest.main()
