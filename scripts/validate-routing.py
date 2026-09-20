#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROUTING = ROOT / "evals" / "routing.jsonl"
DEFAULT_SCHEMA = ROOT / "evals" / "routing.schema.json"
DEFAULT_SKILLS = ROOT / "skills"


class RoutingValidationError(ValueError):
    pass


def load_schema(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    editions = data.get("properties", {}).get("edition", {}).get("enum")
    allowlists = data.get("x-expected-skill-allowlists")
    product_edition = data.get("x-product-edition")
    required_coverage = data.get("x-required-coverage")
    if not isinstance(editions, list) or not all(isinstance(item, str) for item in editions):
        raise RoutingValidationError("schema: edition enum is required")
    if not isinstance(allowlists, dict) or not all(isinstance(allowlists.get(item), list) for item in ("free", "pro")):
        raise RoutingValidationError("schema: free/pro expected-skill allowlists are required")
    if product_edition not in {"free", "pro"}:
        raise RoutingValidationError("schema: x-product-edition must be free or pro")
    if not isinstance(required_coverage, list) or not all(isinstance(item, str) and item.strip() for item in required_coverage):
        raise RoutingValidationError("schema: required coverage tags are required")
    return data


def applicable(row_edition: str, requested_edition: str) -> tuple[str, ...]:
    if requested_edition == "both":
        return ("free", "pro") if row_edition == "both" else (row_edition,)
    return (requested_edition,) if row_edition in {requested_edition, "both"} else ()


def expected_skill(row: dict[str, Any], edition: str) -> Any:
    return row.get(f"expected_skill_{edition}", row.get("expected_skill"))


def frontmatter_fields(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise RoutingValidationError(f"{path}: YAML frontmatter is required")
    block = text[4:text.index("\n---\n", 4)]
    fields: dict[str, str] = {}
    for line in block.splitlines():
        key, separator, raw_value = line.partition(":")
        if not separator or key not in {"name", "description"}:
            continue
        value = raw_value.strip()
        if value.startswith('"'):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                raise RoutingValidationError(f"{path}: invalid quoted {key}") from exc
        fields[key] = value
    return fields


def validate_skill_catalog(schema: dict[str, Any], skills_path: Path) -> set[str]:
    if not skills_path.is_dir() or skills_path.is_symlink():
        raise RoutingValidationError(f"skill catalog is missing or linked: {skills_path}")
    product_edition = schema["x-product-edition"]
    expected = set(schema["x-expected-skill-allowlists"][product_edition])
    actual = {
        path.name for path in skills_path.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    }
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        raise RoutingValidationError(
            f"shipped skill catalog mismatch for {product_edition}: "
            f"missing={missing}, unexpected={unexpected}"
        )
    for name in sorted(expected):
        skill_dir = skills_path / name
        skill_file = skill_dir / "SKILL.md"
        if skill_dir.is_symlink() or skill_file.is_symlink():
            raise RoutingValidationError(f"shipped skill target is linked: {name}")
        fields = frontmatter_fields(skill_file)
        if fields.get("name") != name:
            raise RoutingValidationError(
                f"shipped skill declaration mismatch: {name} declares {fields.get('name')!r}"
            )
        if not fields.get("description", "").strip():
            raise RoutingValidationError(f"shipped skill description is blank: {name}")
    return actual


def validate_routing(routing_path: Path = DEFAULT_ROUTING, schema_path: Path = DEFAULT_SCHEMA,
                     requested_edition: str = "both", skills_path: Path = DEFAULT_SKILLS) -> dict[str, Any]:
    schema = load_schema(schema_path)
    editions = set(schema["properties"]["edition"]["enum"])
    allowlists = {edition: set(skills) for edition, skills in schema["x-expected-skill-allowlists"].items()}
    required_coverage = set(schema["x-required-coverage"])
    if requested_edition not in editions:
        raise RoutingValidationError(f"edition must be one of {', '.join(sorted(editions))}: {requested_edition}")
    skill_catalog = validate_skill_catalog(schema, skills_path)

    errors: list[str] = []
    seen_ids: set[str] = set()
    coverage: set[str] = set()
    total = 0
    applicable_rows = 0
    with routing_path.open(encoding="utf-8") as source:
        for line_number, raw_line in enumerate(source, 1):
            if not raw_line.strip():
                continue
            total += 1
            try:
                row = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                errors.append(f"line {line_number}: invalid JSON ({exc.msg})")
                continue
            if not isinstance(row, dict):
                errors.append(f"line {line_number}: an object is required")
                continue
            for field in schema["required"]:
                if field not in row:
                    errors.append(f"line {line_number}: missing {field}")
            identifier = row.get("id")
            if not isinstance(identifier, str) or not identifier.strip():
                errors.append(f"line {line_number}: id must be nonblank")
            elif identifier in seen_ids:
                errors.append(f"line {line_number}: duplicate id {identifier}")
            else:
                seen_ids.add(identifier)
            for field in ("utterance", "note"):
                if not isinstance(row.get(field), str) or not row[field].strip():
                    errors.append(f"line {line_number}: {field} must be nonblank")

            row_edition = row.get("edition")
            if row_edition not in editions:
                errors.append(f"line {line_number}: invalid edition {row_edition!r}")
                continue
            for edition in ("free", "pro"):
                field = f"expected_skill_{edition}"
                if field in row and row_edition not in {edition, "both"}:
                    errors.append(f"line {line_number}: {field} is incompatible with edition {row_edition}")
                if field in row and (not isinstance(row[field], str) or not row[field].strip()):
                    errors.append(f"line {line_number}: {field} must be nonblank")
                elif field in row and row[field] not in allowlists[edition]:
                    errors.append(f"line {line_number}: {field} is not allowed for {edition}: {row[field]!r}")
            if "expected_skill" in row:
                if not isinstance(row["expected_skill"], str) or not row["expected_skill"].strip():
                    errors.append(f"line {line_number}: expected_skill must be nonblank")
                elif any(field in row for field in ("expected_skill_free", "expected_skill_pro")):
                    errors.append(f"line {line_number}: generic and edition-specific expected routes cannot be mixed")
                else:
                    row_targets = ("free", "pro") if row_edition == "both" else (row_edition,)
                    for edition in row_targets:
                        if row["expected_skill"] not in allowlists[edition]:
                            errors.append(
                                f"line {line_number}: expected_skill is not allowed for {edition}: {row['expected_skill']!r}"
                            )

            tags = row.get("coverage", [])
            if not isinstance(tags, list) or any(not isinstance(tag, str) or not tag.strip() for tag in tags):
                errors.append(f"line {line_number}: coverage must be a list of nonblank strings")
            elif len(tags) != len(set(tags)):
                errors.append(f"line {line_number}: coverage tags must be unique")
            elif applicable(row_edition, requested_edition):
                coverage.update(tags)

            targets = applicable(row_edition, requested_edition)
            applicable_rows += bool(targets)
            for edition in targets:
                skill = expected_skill(row, edition)
                if not isinstance(skill, str) or not skill.strip():
                    errors.append(f"line {line_number}: missing expected route for {edition}")
                elif skill not in allowlists[edition] or skill not in skill_catalog:
                    errors.append(f"line {line_number}: expected route is not allowed for {edition}: {skill!r}")

    if total == 0:
        errors.append("routing JSONL has no rows")
    missing_coverage = sorted(required_coverage - coverage)
    if missing_coverage:
        errors.append("missing required coverage: " + ", ".join(missing_coverage))
    if errors:
        raise RoutingValidationError("routing validation failed:\n  " + "\n  ".join(errors))
    return {"rows": total, "applicable_rows": applicable_rows, "edition": requested_edition,
            "coverage": sorted(coverage)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate routing.jsonl against the routing contract")
    parser.add_argument("--path", type=Path, default=DEFAULT_ROUTING)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--skills-dir", type=Path, default=DEFAULT_SKILLS)
    parser.add_argument("--edition", default="both")
    args = parser.parse_args()
    try:
        result = validate_routing(args.path, args.schema, args.edition, args.skills_dir)
    except (OSError, json.JSONDecodeError, RoutingValidationError) as exc:
        print(f"routing validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
    print("✓ routing.jsonl validated — "
          f"{result['rows']} rows, {result['applicable_rows']} applicable, edition={result['edition']}")


if __name__ == "__main__":
    main()
