import importlib.util
import json
from pathlib import Path
import shutil
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

    def copy_skills(self) -> Path:
        skills = Path(self.temp.name) / "skills"
        shutil.copytree(validator.DEFAULT_SKILLS, skills)
        return skills

    def test_current_contract_validates_for_all_editions(self):
        self.write_rows(self.rows)
        product = validator.load_schema(self.schema)["x-product-edition"]
        editions = ("free", "pro", "both") if product == "pro" else ("free", "both")
        for edition in editions:
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

    def test_shipped_skill_target_must_exist(self):
        self.write_rows(self.rows)
        skills = self.copy_skills()
        shutil.rmtree(skills / "vat-hometax")
        with self.assertRaisesRegex(validator.RoutingValidationError, "shipped skill catalog mismatch"):
            validator.validate_routing(self.routing, self.schema, "pro", skills)

    def test_shipped_frontmatter_name_must_match_target(self):
        self.write_rows(self.rows)
        skills = self.copy_skills()
        skill_file = skills / "vat-hometax" / "SKILL.md"
        skill_file.write_text(
            skill_file.read_text(encoding="utf-8").replace('name: "vat-hometax"', 'name: "wrong-route"', 1),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(validator.RoutingValidationError, "shipped skill declaration mismatch"):
            validator.validate_routing(self.routing, self.schema, "pro", skills)

    def test_generic_and_edition_specific_routes_cannot_conflict(self):
        rows = [dict(row) for row in self.rows]
        rows[0]["expected_skill_free"] = "hometax-tax-hub"
        self.write_rows(rows)
        with self.assertRaisesRegex(validator.RoutingValidationError, "cannot be mixed"):
            validator.validate_routing(self.routing, self.schema, "free")

    def test_required_coverage_must_be_applicable_to_requested_edition(self):
        rows = [dict(row) for row in self.rows]
        for row in rows:
            if "pharmacy" in row.get("coverage", []):
                row["edition"] = "pro"
                row["expected_skill"] = "jongsose-prep-kr"
        self.write_rows(rows)
        with self.assertRaisesRegex(validator.RoutingValidationError, "missing required coverage: pharmacy"):
            validator.validate_routing(self.routing, self.schema, "free")


if __name__ == "__main__":
    unittest.main()
