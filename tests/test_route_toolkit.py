from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.validate_repo import validate_zip_archive


ROOT = Path(__file__).resolve().parents[1]
TOOLKIT = ROOT / "skills" / "plan-smart-routes" / "scripts" / "route_toolkit.py"
REGISTRY = ROOT / "skills" / "plan-smart-routes" / "scripts" / "source_registry.py"
RESOLVER = ROOT / "skills" / "plan-smart-routes" / "scripts" / "map_link_resolver.py"


def run_json(script: Path, *arguments: str) -> dict:
    environment = dict(os.environ)
    environment["PYTHONIOENCODING"] = "utf-8"
    completed = subprocess.run(
        [sys.executable, str(script), "--compact", *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
    )
    return json.loads(completed.stdout)


class LinkTests(unittest.TestCase):
    def test_multistop_capabilities_are_truthful(self) -> None:
        result = run_json(
            TOOLKIT,
            "links",
            "--origin", "51.5074,-0.1278|Origin",
            "--waypoint", "51.5133,-0.0890|Stop",
            "--destination", "51.5155,-0.0922|Destination",
            "--mode", "transit",
            "--when", "2026-08-01T09:00:00+01:00",
        )
        by_provider = {item["provider"]: item for item in result["links"]}
        self.assertTrue(by_provider["google"]["encodes"]["waypoints"])
        self.assertFalse(by_provider["google"]["encodes"]["time"])
        self.assertTrue(by_provider["bing"]["encodes"]["waypoints"])
        self.assertTrue(by_provider["bing"]["encodes"]["time"])
        omitted = {item["provider"] for item in result["omitted"]}
        self.assertIn("moovit", omitted)
        self.assertIn("yandex", omitted)

    def test_waze_is_driving_only_and_does_not_encode_origin(self) -> None:
        result = run_json(
            TOOLKIT,
            "links",
            "--origin", "40.7128,-74.0060|Origin",
            "--destination", "40.7580,-73.9855|Destination",
            "--mode", "driving",
            "--providers", "waze",
        )
        waze = result["links"][0]
        self.assertFalse(waze["encodes"]["origin"])
        self.assertTrue(waze["encodes"]["destination"])

    def test_resolver_rejects_plain_http(self) -> None:
        environment = dict(os.environ)
        environment["PYTHONIOENCODING"] = "utf-8"
        completed = subprocess.run(
            [sys.executable, str(RESOLVER), "http://maps.google.com/"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment,
        )
        self.assertNotEqual(completed.returncode, 0)
        result = json.loads(completed.stdout)
        self.assertIn("HTTPS", result["error"])


class ScoringTests(unittest.TestCase):
    def run_with_file(self, command: str, payload: dict, *extra: str) -> dict:
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as handle:
            json.dump(payload, handle)
            path = Path(handle.name)
        try:
            return run_json(TOOLKIT, command, "--input", str(path), *extra)
        finally:
            path.unlink(missing_ok=True)

    def test_cancelled_route_is_hard_rejected(self) -> None:
        payload = {
            "routes": [
                {"id": "rail", "duration_min": 40, "reliability": 0.9, "transfers": 1, "walk_min": 8},
                {"id": "cancelled", "duration_min": 20, "cancelled": True},
            ]
        }
        result = self.run_with_file("score", payload, "--profile", "balanced")
        self.assertEqual(result["ranked"][0]["id"], "rail")
        self.assertEqual(result["rejected"][0]["id"], "cancelled")

    def test_prediction_comparison_returns_range_and_buffer(self) -> None:
        payload = {
            "predictions": [
                {"provider": "a", "minutes": 42},
                {"provider": "b", "minutes": 48},
                {"provider": "c", "minutes": 45},
            ],
            "context": {"mode": "transit", "bus_share": 0.5, "risk_level": 0.3},
        }
        result = self.run_with_file("compare", payload)
        self.assertLess(result["planning_window_min"][0], result["planning_window_min"][1])
        self.assertGreaterEqual(result["recommended_buffer_min"], 5)
        self.assertIn(result["confidence"], {"high", "medium", "low"})

    def test_sparse_route_cannot_win_by_hiding_critical_evidence(self) -> None:
        payload = {
            "routes": [
                {"id": "sparse", "duration_min": 30},
                {
                    "id": "evidenced",
                    "duration_min": 35,
                    "reliability": 0.85,
                    "transfers": 1,
                    "walk_min": 6,
                    "cost": 3,
                    "weather_exposure_min": 2,
                    "bus_share": 0.2,
                    "comfort": 0.8,
                },
            ]
        }
        result = self.run_with_file("score", payload, "--profile", "balanced")
        self.assertEqual(result["ranked"][0]["id"], "evidenced")
        sparse = next(item for item in result["ranked"] if item["id"] == "sparse")
        self.assertLess(sparse["evidence_completeness"], 0.5)
        self.assertGreater(sparse["missing_evidence_penalty"], 0)


class ArchiveSafetyTests(unittest.TestCase):
    def test_validator_rejects_traversal_member(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "bad.zip"
            with zipfile.ZipFile(archive, "w") as handle:
                handle.writestr("root/../escape.txt", "bad")
            with self.assertRaises(AssertionError):
                validate_zip_archive(archive)


class RegistryTests(unittest.TestCase):
    def test_turkish_city_name_matches_istanbul(self) -> None:
        result = run_json(REGISTRY, "show", "--city", "İstanbul")
        self.assertEqual(result["slug"], "istanbul")

    def test_access_plan_never_calls_sources(self) -> None:
        result = run_json(REGISTRY, "plan", "--city", "Singapore", "--allow", "no_key,web_only")
        self.assertIn("integrity_note", result)
        self.assertGreater(len(result["unavailable_sources"]), 0)


if __name__ == "__main__":
    unittest.main()
