#!/usr/bin/env python3
"""Read the bundled official-source registry without network access."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REGISTRY = Path(__file__).resolve().parent.parent / "references" / "city-source-registry.json"


def load_registry() -> dict[str, Any]:
    try:
        payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Could not read city registry: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("profiles"), list):
        raise SystemExit("City registry has an invalid schema")
    return payload


def normalize(value: str) -> str:
    replacements = str.maketrans(
        {
            "İ": "i",
            "I": "i",
            "ı": "i",
            "Ş": "s",
            "ş": "s",
            "Ğ": "g",
            "ğ": "g",
            "Ü": "u",
            "ü": "u",
            "Ö": "o",
            "ö": "o",
            "Ç": "c",
            "ç": "c",
        }
    )
    return " ".join(value.translate(replacements).casefold().replace("-", " ").split())


def find_profile(registry: dict[str, Any], query: str) -> dict[str, Any] | None:
    needle = normalize(query)
    scored: list[tuple[int, dict[str, Any]]] = []
    for profile in registry["profiles"]:
        candidates = {
            normalize(str(profile.get("slug", ""))),
            normalize(str(profile.get("name", ""))),
            normalize(str(profile.get("local_name", ""))),
        }
        exact = needle in candidates
        partial = any(needle and (needle in item or item in needle) for item in candidates)
        if exact:
            scored.append((2, profile))
        elif partial:
            scored.append((1, profile))
    if not scored:
        return None
    scored.sort(key=lambda item: (-item[0], str(item[1].get("slug"))))
    if len(scored) > 1 and scored[0][0] == scored[1][0]:
        return None
    return scored[0][1]


def source_plan(profile: dict[str, Any], allowed: set[str]) -> dict[str, Any]:
    available = []
    unavailable = []
    for source in profile.get("sources", []):
        target = available if source.get("access") in allowed else unavailable
        target.append(source)
    return {
        "city": profile.get("name"),
        "timezone": profile.get("timezone"),
        "coverage": profile.get("coverage"),
        "available_sources": available,
        "unavailable_sources": unavailable,
        "caveats": profile.get("caveats", []),
        "integrity_note": "This command selects source metadata; it does not call or validate live endpoints.",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect Map Skill's official city-source registry")
    parser.add_argument("--compact", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="List bundled city profiles")
    show = sub.add_parser("show", help="Show one city profile")
    show.add_argument("--city", required=True)
    plan = sub.add_parser("plan", help="Select sources by available access type")
    plan.add_argument("--city", required=True)
    plan.add_argument("--allow", default="no_key,web_only", help="Comma-separated access types")
    return parser


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args()
    registry = load_registry()
    if args.command == "list":
        result: Any = {
            "verified_on": registry.get("verified_on"),
            "cities": [
                {
                    "slug": profile.get("slug"),
                    "name": profile.get("name"),
                    "country": profile.get("country"),
                    "timezone": profile.get("timezone"),
                    "coverage": profile.get("coverage"),
                }
                for profile in registry["profiles"]
            ],
        }
    else:
        profile = find_profile(registry, args.city)
        if profile is None:
            result = {"status": "ambiguous_or_unknown", "query": args.city}
        elif args.command == "show":
            result = profile
        else:
            allowed = {item.strip() for item in args.allow.split(",") if item.strip()}
            result = source_plan(profile, allowed)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=None if args.compact else 2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
