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


class RoutingValidationError(ValueError):
    pass


def load_schema(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    editions = data.get("properties", {}).get("edition", {}).get("enum")
    allowlists = data.get("x-expected-skill-allowlists")
    required_coverage = data.get("x-required-coverage")
    if not isinstance(editions, list) or not all(isinstance(item, str) for item in editions):
        raise RoutingValidationError("schema: edition enum is required")
    if not isinstance(allowlists, dict) or not all(isinstance(allowlists.get(item), list) for item in ("free", "pro")):
        raise RoutingValidationError("schema: free/pro expected-skill allowlists are required")
    if not isinstance(required_coverage, list) or not all(isinstance(item, str) and item.strip() for item in required_coverage):
        raise RoutingValidationError("schema: required coverage tags are required")
    return data


def applicable(row_edition: str, requested_edition: str) -> tuple[str, ...]:
    if requested_edition == "both":
        return ("free", "pro") if row_edition == "both" else (row_edition,)
    return (requested_edition,) if row_edition in {requested_edition, "both"} else ()


def expected_skill(row: dict[str, Any], edition: str) -> Any:
    return row.get(f"expected_skill_{edition}", row.get("expected_skill"))


def validate_routing(routing_path: Path = DEFAULT_ROUTING, schema_path: Path = DEFAULT_SCHEMA,
                     requested_edition: str = "both") -> dict[str, Any]:
    schema = load_schema(schema_path)
    editions = set(schema["properties"]["edition"]["enum"])
    allowlists = {edition: set(skills) for edition, skills in schema["x-expected-skill-allowlists"].items()}
    required_coverage = set(schema["x-required-coverage"])
    if requested_edition not in editions:
        raise RoutingValidationError(f"edition must be one of {', '.join(sorted(editions))}: {requested_edition}")

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
            if "expected_skill" in row and (not isinstance(row["expected_skill"], str) or not row["expected_skill"].strip()):
                errors.append(f"line {line_number}: expected_skill must be nonblank")

            tags = row.get("coverage", [])
            if not isinstance(tags, list) or any(not isinstance(tag, str) or not tag.strip() for tag in tags):
                errors.append(f"line {line_number}: coverage must be a list of nonblank strings")
            elif len(tags) != len(set(tags)):
                errors.append(f"line {line_number}: coverage tags must be unique")
            else:
                coverage.update(tags)

            targets = applicable(row_edition, requested_edition)
            applicable_rows += bool(targets)
            for edition in targets:
                skill = expected_skill(row, edition)
                if not isinstance(skill, str) or not skill.strip():
                    errors.append(f"line {line_number}: missing expected route for {edition}")
                elif skill not in allowlists[edition]:
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
    parser.add_argument("--edition", default="both")
    args = parser.parse_args()
    try:
        result = validate_routing(args.path, args.schema, args.edition)
    except (OSError, json.JSONDecodeError, RoutingValidationError) as exc:
        print(f"routing validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
    print("✓ routing.jsonl validated — "
          f"{result['rows']} rows, {result['applicable_rows']} applicable, edition={result['edition']}")


if __name__ == "__main__":
    main()
