#!/usr/bin/env python3
"""Deterministic helpers for plan-smart-routes.

This script never claims to retrieve Google, Yandex, or Moovit route results.
It only creates documented links and performs local synthesis on route data the
agent has already collected from accessible sources.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import statistics
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


VERSION = "1.0.0"
USER_AGENT = f"plan-smart-routes/{VERSION} (personal trip planning)"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def fail(message: str, code: int = 2) -> None:
    print(json.dumps({"ok": False, "error": message}, ensure_ascii=False, indent=2))
    raise SystemExit(code)


def read_json(path: str) -> Any:
    try:
        if path == "-":
            return json.load(sys.stdin)
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"JSON okunamadı: {exc}")


def emit(payload: Any, compact: bool = False) -> None:
    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=None if compact else 2,
            separators=(",", ":") if compact else None,
            sort_keys=False,
        )
    )


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"Geçersiz ISO tarih/saat: {value}") from exc


def parse_point(raw: str) -> dict[str, Any]:
    """Parse 'lat,lon|label' or a plain label/address."""
    raw = raw.strip()
    if not raw:
        raise ValueError("Boş konum")
    coordinate_part = raw
    label = raw
    if "|" in raw:
        coordinate_part, label = raw.split("|", 1)
        coordinate_part = coordinate_part.strip()
        label = label.strip() or coordinate_part
    pieces = [part.strip() for part in coordinate_part.split(",")]
    if len(pieces) == 2:
        try:
            lat, lon = float(pieces[0]), float(pieces[1])
        except ValueError:
            return {"label": label, "lat": None, "lon": None, "has_coords": False}
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError("Koordinat aralık dışında")
        return {"label": label, "lat": lat, "lon": lon, "has_coords": True}
    return {"label": label, "lat": None, "lon": None, "has_coords": False}


def point_value(point: dict[str, Any], coordinates_first: bool = True) -> str:
    if coordinates_first and point["has_coords"]:
        return f"{point['lat']:.7f},{point['lon']:.7f}"
    return str(point["label"])


def link_record(
    provider: str,
    url: str,
    *,
    link_type: str,
    origin: bool,
    destination: bool,
    waypoints: bool,
    mode: bool,
    time: bool,
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "provider": provider,
        "url": url,
        "link_type": link_type,
        "encodes": {
            "origin": origin,
            "destination": destination,
            "waypoints": waypoints,
            "mode": mode,
            "time": time,
        },
        "limitations": limitations or [],
    }


def build_links(args: argparse.Namespace) -> dict[str, Any]:
    try:
        origin = parse_point(args.origin)
        destination = parse_point(args.destination)
        waypoints = [parse_point(item) for item in args.waypoint]
        when = parse_iso(args.when)
    except ValueError as exc:
        fail(str(exc))

    requested = {
        item.strip().lower()
        for item in args.providers.split(",")
        if item.strip()
    }
    known = {
        "google",
        "yandex",
        "yandex-navigator",
        "moovit",
        "here",
        "bing",
        "apple",
        "waze",
        "citymapper",
        "osm",
    }
    unknown = sorted(requested - known)
    if unknown:
        fail("Bilinmeyen sağlayıcı: " + ", ".join(unknown))

    links: list[dict[str, Any]] = []
    omitted: list[dict[str, str]] = []

    if "google" in requested:
        params: dict[str, str] = {
            "api": "1",
            "origin": point_value(origin),
            "destination": point_value(destination),
            "travelmode": args.mode,
        }
        if waypoints:
            params["waypoints"] = "|".join(point_value(item) for item in waypoints)
        links.append(
            link_record(
                "google",
                "https://www.google.com/maps/dir/?" + urlencode(params),
                link_type="universal_web",
                origin=True,
                destination=True,
                waypoints=bool(waypoints),
                mode=True,
                time=False,
                limitations=[
                    "Google Maps URLs do not encode departure/arrival time.",
                    "Mobile browsers may support at most 3 waypoints; other platforms at most 9.",
                ],
            )
        )

    if "yandex" in requested:
        if not (origin["has_coords"] and destination["has_coords"]):
            omitted.append({"provider": "yandex", "reason": "Başlangıç ve hedef koordinatı gerekli."})
        elif waypoints:
            omitted.append({"provider": "yandex", "reason": "Doğrulanmış web URL şeması yalnız başlangıç ve hedefi belgeler."})
        else:
            yandex_modes = {
                "transit": "mt",
                "driving": "auto",
                "walking": "pd",
                "bicycling": "bc",
            }
            params = {
                "rtext": (
                    f"{origin['lat']:.7f},{origin['lon']:.7f}~"
                    f"{destination['lat']:.7f},{destination['lon']:.7f}"
                ),
                "rtt": yandex_modes[args.mode],
            }
            links.append(
                link_record(
                    "yandex",
                    "https://yandex.com/maps/?" + urlencode(params),
                    link_type="universal_web",
                    origin=True,
                    destination=True,
                    waypoints=False,
                    mode=True,
                    time=False,
                    limitations=["The documented route URL does not encode trip time or intermediate stops."],
                )
            )

    if "yandex-navigator" in requested:
        all_points = [origin, *waypoints, destination]
        if args.mode != "driving":
            omitted.append({"provider": "yandex-navigator", "reason": "Yandex Navigator bağlantısı sürüş içindir."})
        elif not all(point["has_coords"] for point in all_points):
            omitted.append({"provider": "yandex-navigator", "reason": "Başlangıç, hedef ve tüm ara durak koordinatları gerekli."})
        else:
            params = {
                "lat_from": f"{origin['lat']:.7f}",
                "lon_from": f"{origin['lon']:.7f}",
                "lat_to": f"{destination['lat']:.7f}",
                "lon_to": f"{destination['lon']:.7f}",
            }
            for index, point in enumerate(waypoints):
                params[f"lat_via_{index}"] = f"{point['lat']:.7f}"
                params[f"lon_via_{index}"] = f"{point['lon']:.7f}"
            links.append(
                link_record(
                    "yandex-navigator",
                    "yandexnavi://build_route_on_map?" + urlencode(params),
                    link_type="mobile_app_scheme",
                    origin=True,
                    destination=True,
                    waypoints=bool(waypoints),
                    mode=True,
                    time=False,
                    limitations=[
                        "Requires Yandex Navigator and supports driving only.",
                        "Unsigned app links are rate-limited by Yandex and do not encode trip time.",
                    ],
                )
            )

    if "moovit" in requested:
        if args.mode != "transit":
            omitted.append({"provider": "moovit", "reason": "Moovit linki yalnız toplu taşıma için üretildi."})
        elif not (origin["has_coords"] and destination["has_coords"]):
            omitted.append({"provider": "moovit", "reason": "Doğrulanmış yönlendirme şeması koordinat gerektirir."})
        elif waypoints:
            omitted.append({"provider": "moovit", "reason": "Doğrulanmış Moovit şeması çok durak desteklemiyor."})
        else:
            params = {
                "dest_lat": f"{destination['lat']:.7f}",
                "dest_lon": f"{destination['lon']:.7f}",
                "dest_name": str(destination["label"]),
                "orig_lat": f"{origin['lat']:.7f}",
                "orig_lon": f"{origin['lon']:.7f}",
                "orig_name": str(origin["label"]),
                "auto_run": "true",
                "partner_id": "plan-smart-routes",
            }
            if when:
                params["date"] = when.isoformat()
            links.append(
                link_record(
                    "moovit",
                    "moovit://directions?" + urlencode(params),
                    link_type="mobile_app_scheme",
                    origin=True,
                    destination=True,
                    waypoints=False,
                    mode=True,
                    time=bool(when),
                    limitations=[
                        "Requires the Moovit mobile app; browser rendering may not make custom schemes clickable.",
                        "Moovit's public deep-link documentation does not define whether date means departure or arrival; keep the text plan authoritative.",
                    ],
                )
            )
            if args.moovit_metro_id:
                web_params = {
                    "metroId": args.moovit_metro_id,
                    "lang": args.lang,
                    "to": str(destination["label"]),
                    "tll": f"{destination['lat']:.7f}_{destination['lon']:.7f}",
                }
                links.append(
                    link_record(
                        "moovit",
                        "https://www.moovit.com/?" + urlencode(web_params),
                        link_type="destination_web",
                        origin=False,
                        destination=True,
                        waypoints=False,
                        mode=True,
                        time=False,
                        limitations=["The documented web link opens destination planning; it does not preserve the supplied origin/time."],
                    )
                )

    if "here" in requested:
        all_points = [origin, *waypoints, destination]
        if not all(point["has_coords"] for point in all_points):
            omitted.append({"provider": "here", "reason": "HERE rota paylaşımı için tüm noktaların koordinatı gerekli."})
        else:
            here_modes = {
                "driving": "d",
                "walking": "w",
                "transit": "pt",
                "bicycling": "b",
            }
            path_parts: list[str] = []
            for index, point in enumerate(all_points):
                title = quote(str(point["label"]), safe="")
                marker = ",s" if 0 < index < len(all_points) - 1 else ""
                path_parts.append(f"{point['lat']:.7f},{point['lon']:.7f},{title}{marker}")
            links.append(
                link_record(
                    "here",
                    "https://share.here.com/r/" + "/".join(path_parts) + "?" + urlencode({"m": here_modes[args.mode]}),
                    link_type="universal_web",
                    origin=True,
                    destination=True,
                    waypoints=bool(waypoints),
                    mode=True,
                    time=False,
                    limitations=[
                        "HERE route sharing does not encode departure/arrival time.",
                        "Coverage and the opened route must be verified for the trip area.",
                    ],
                )
            )

    if "bing" in requested:
        if args.mode == "bicycling":
            omitted.append({"provider": "bing", "reason": "Belgelenen özel URL şeması bisiklet modunu içermiyor."})
        else:
            mode_map = {"driving": "D", "transit": "T", "walking": "W"}

            def bing_point(point: dict[str, Any]) -> str:
                if point["has_coords"]:
                    return f"pos.{point['lat']:.7f}_{point['lon']:.7f}_{point['label']}"
                return f"adr.{point['label']}"

            params: dict[str, str] = {
                "rtp": "~".join(bing_point(item) for item in [origin, *waypoints, destination]),
                "mode": mode_map[args.mode],
            }
            if args.mode == "driving":
                params["rtop"] = "0~1~0"
            if when:
                params["limit"] = "D" if args.time_kind == "depart" else "A"
                params["time"] = when.strftime("%Y%m%d%H%M")
            links.append(
                link_record(
                    "bing",
                    "https://bing.com/maps/default.aspx?" + urlencode(params),
                    link_type="web",
                    origin=True,
                    destination=True,
                    waypoints=bool(waypoints),
                    mode=True,
                    time=bool(when),
                    limitations=["Availability and routing coverage must be checked in the opened product."],
                )
            )

    if "apple" in requested:
        if waypoints:
            omitted.append({"provider": "apple", "reason": "Belgelenen Map Links şeması ara durak içermiyor."})
        elif args.mode == "bicycling":
            omitted.append({"provider": "apple", "reason": "Belgelenen Map Links şeması bisiklet modu içermiyor."})
        else:
            mode_map = {"driving": "d", "transit": "r", "walking": "w"}
            params = {
                "saddr": point_value(origin),
                "daddr": point_value(destination),
                "dirflg": mode_map[args.mode],
            }
            links.append(
                link_record(
                    "apple",
                    "https://maps.apple.com/?" + urlencode(params),
                    link_type="web_or_app",
                    origin=True,
                    destination=True,
                    waypoints=False,
                    mode=True,
                    time=False,
                    limitations=["Apple Map Links do not document trip time or intermediate stops."],
                )
            )

    if "waze" in requested:
        if args.mode != "driving":
            omitted.append({"provider": "waze", "reason": "Waze bağlantısı sürüş içindir."})
        elif not destination["has_coords"]:
            omitted.append({"provider": "waze", "reason": "Kesin navigasyon için hedef koordinatı gerekli."})
        elif waypoints:
            omitted.append({"provider": "waze", "reason": "Belgelenen deep link ara durak içermez."})
        else:
            params = {
                "ll": f"{destination['lat']:.7f},{destination['lon']:.7f}",
                "navigate": "yes",
                "utm_source": "plan-smart-routes",
            }
            links.append(
                link_record(
                    "waze",
                    "https://waze.com/ul?" + urlencode(params),
                    link_type="web_or_app",
                    origin=False,
                    destination=True,
                    waypoints=False,
                    mode=True,
                    time=False,
                    limitations=["Navigation starts from the user's current device location; supplied origin is not encoded."],
                )
            )

    if "citymapper" in requested:
        if args.mode != "transit":
            omitted.append({"provider": "citymapper", "reason": "Bu entegrasyon toplu taşıma yönlendirmesi içindir."})
        elif not (origin["has_coords"] and destination["has_coords"]):
            omitted.append({"provider": "citymapper", "reason": "Doğrulanmış directions linki koordinat gerektirir."})
        elif waypoints:
            omitted.append({"provider": "citymapper", "reason": "Doğrulanmış directions linki ara durak içermez."})
        else:
            params = {
                "startcoord": f"{origin['lat']:.7f},{origin['lon']:.7f}",
                "startname": str(origin["label"]),
                "endcoord": f"{destination['lat']:.7f},{destination['lon']:.7f}",
                "endname": str(destination["label"]),
            }
            links.append(
                link_record(
                    "citymapper",
                    "https://citymapper.com/directions?" + urlencode(params),
                    link_type="web_or_app",
                    origin=True,
                    destination=True,
                    waypoints=False,
                    mode=True,
                    time=False,
                    limitations=["Coverage is city-dependent; verify that the opened product supports the trip area."],
                )
            )

    if "osm" in requested:
        if args.mode == "transit":
            omitted.append({"provider": "osm", "reason": "OpenStreetMap web directions does not provide a documented transit route mode."})
        elif not (origin["has_coords"] and destination["has_coords"]):
            omitted.append({"provider": "osm", "reason": "Directions link requires coordinates."})
        elif waypoints:
            omitted.append({"provider": "osm", "reason": "This official-web link helper only encodes two endpoints."})
        else:
            engines = {
                "driving": "fossgis_osrm_car",
                "walking": "graphhopper_foot",
                "bicycling": "graphhopper_bicycle",
            }
            params = {
                "engine": engines[args.mode],
                "route": (
                    f"{origin['lat']:.7f},{origin['lon']:.7f};"
                    f"{destination['lat']:.7f},{destination['lon']:.7f}"
                ),
            }
            links.append(
                link_record(
                    "osm",
                    "https://www.openstreetmap.org/directions?" + urlencode(params),
                    link_type="web",
                    origin=True,
                    destination=True,
                    waypoints=False,
                    mode=True,
                    time=False,
                    limitations=["Community routing backends and coverage can change; verify the opened route."],
                )
            )

    return {
        "ok": True,
        "mode": args.mode,
        "requested_time": when.isoformat() if when else None,
        "time_kind": args.time_kind if when else None,
        "links": links,
        "omitted": omitted,
        "integrity_note": "A generated link is not evidence that a provider route or ETA was retrieved.",
    }


def route_signature(route: dict[str, Any]) -> str:
    if route.get("canonical_signature"):
        return str(route["canonical_signature"]).strip().casefold()
    sequence = route.get("line_sequence") or route.get("stop_sequence")
    if sequence:
        parts = ["|".join(str(item).strip().casefold() for item in sequence)]
        for key in ("mode_sequence", "transfer_sequence", "direction_sequence"):
            extra = route.get(key)
            if extra:
                parts.append(key + "=" + "|".join(str(item).strip().casefold() for item in extra))
        if route.get("service_date"):
            parts.append("service_date=" + str(route["service_date"]).strip())
        return "::".join(parts)
    return f"unique:{route.get('id', id(route))}"


def dedupe_routes(routes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for route in routes:
        grouped.setdefault(route_signature(route), []).append(route)
    merged: list[dict[str, Any]] = []
    for signature, items in grouped.items():
        base = dict(items[0])
        base["canonical_signature"] = signature
        providers = sorted(
            {
                str(provider)
                for item in items
                for provider in (item.get("providers") or [item.get("provider")])
                if provider
            }
        )
        base["providers"] = providers
        durations = [
            float(item["duration_min"])
            for item in items
            if isinstance(item.get("duration_min"), (int, float))
        ]
        if durations:
            base["duration_min"] = statistics.median(durations)
            base["provider_duration_range_min"] = [min(durations), max(durations)]
        planning_uppers = [
            float(item["planning_upper_min"])
            for item in items
            if isinstance(item.get("planning_upper_min"), (int, float))
        ]
        if planning_uppers:
            base["planning_upper_min"] = max(planning_uppers)
        for key in ("cancelled", "infeasible", "closing_violation", "accessibility_violation"):
            base[key] = any(bool(item.get(key)) for item in items)
        base["hard_failures"] = sorted(
            {
                str(reason)
                for item in items
                for reason in (item.get("hard_failures") or [])
            }
        )
        base["source_candidates"] = len(items)
        merged.append(base)
    return merged


PROFILE_WEIGHTS: dict[str, dict[str, float]] = {
    "balanced": {
        "duration": 0.30,
        "reliability_loss": 0.25,
        "transfers": 0.12,
        "walk": 0.08,
        "cost": 0.08,
        "weather": 0.07,
        "bus_share": 0.05,
        "comfort_loss": 0.05,
    },
    "urgent": {
        "duration": 0.38,
        "reliability_loss": 0.32,
        "transfers": 0.12,
        "walk": 0.04,
        "cost": 0.02,
        "weather": 0.04,
        "bus_share": 0.08,
    },
    "comfortable": {
        "duration": 0.18,
        "reliability_loss": 0.22,
        "transfers": 0.20,
        "walk": 0.15,
        "cost": 0.05,
        "weather": 0.10,
        "comfort_loss": 0.10,
    },
    "leisure": {
        "duration": 0.15,
        "reliability_loss": 0.20,
        "transfers": 0.10,
        "walk": 0.08,
        "cost": 0.05,
        "weather": 0.10,
        "comfort_loss": 0.10,
        "scenic_loss": 0.22,
    },
    "rail-first": {
        "duration": 0.25,
        "reliability_loss": 0.25,
        "transfers": 0.12,
        "walk": 0.08,
        "cost": 0.05,
        "weather": 0.05,
        "bus_share": 0.20,
    },
    "low-transfer": {
        "duration": 0.23,
        "reliability_loss": 0.24,
        "transfers": 0.32,
        "walk": 0.10,
        "cost": 0.05,
        "weather": 0.06,
    },
}


def numeric(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and math.isfinite(float(value)) else None


def route_metrics(route: dict[str, Any]) -> dict[str, float | None]:
    duration = numeric(route.get("planning_upper_min"))
    if duration is None:
        duration = numeric(route.get("duration_min"))
    reliability = numeric(route.get("reliability"))
    comfort = numeric(route.get("comfort"))
    scenic = numeric(route.get("scenic"))
    return {
        "duration": duration,
        "reliability_loss": None if reliability is None else 1 - max(0.0, min(1.0, reliability)),
        "transfers": numeric(route.get("transfers")),
        "walk": numeric(route.get("walk_min")),
        "cost": numeric(route.get("cost")),
        "weather": numeric(route.get("weather_exposure_min")),
        "bus_share": numeric(route.get("bus_share")),
        "comfort_loss": None if comfort is None else 1 - max(0.0, min(1.0, comfort)),
        "scenic_loss": None if scenic is None else 1 - max(0.0, min(1.0, scenic)),
    }


def hard_failure(route: dict[str, Any]) -> list[str]:
    failures = list(route.get("hard_failures") or [])
    for key in (
        "cancelled",
        "infeasible",
        "closing_violation",
        "accessibility_violation",
    ):
        if route.get(key):
            failures.append(key)
    return sorted({str(item) for item in failures})


def score_routes(args: argparse.Namespace) -> dict[str, Any]:
    payload = read_json(args.input)
    routes = payload.get("routes") if isinstance(payload, dict) else None
    if not isinstance(routes, list) or not routes:
        fail("Girdi, boş olmayan bir 'routes' listesi içermeli.")
    profile = args.profile or payload.get("profile") or "balanced"
    if profile not in PROFILE_WEIGHTS:
        fail(f"Bilinmeyen profil: {profile}")
    candidates = dedupe_routes(routes) if not args.no_dedupe else [dict(item) for item in routes]

    valid: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for route in candidates:
        failures = hard_failure(route)
        if failures:
            rejected.append(
                {
                    "id": route.get("id"),
                    "providers": route.get("providers") or [route.get("provider")],
                    "reasons": failures,
                }
            )
        else:
            valid.append(route)
    if not valid:
        return {"ok": True, "profile": profile, "ranked": [], "rejected": rejected, "warning": "Uygun rota kalmadı."}

    metrics_by_id = {id(route): route_metrics(route) for route in valid}
    extrema: dict[str, tuple[float, float]] = {}
    for metric in PROFILE_WEIGHTS[profile]:
        values = [
            item[metric]
            for item in metrics_by_id.values()
            if item.get(metric) is not None
        ]
        if values:
            extrema[metric] = (min(values), max(values))

    ranked: list[dict[str, Any]] = []
    for route in valid:
        metrics = metrics_by_id[id(route)]
        components: dict[str, float] = {}
        available_weight = 0.0
        weighted_loss = 0.0
        for metric, weight in PROFILE_WEIGHTS[profile].items():
            value = metrics.get(metric)
            if value is None or metric not in extrema:
                continue
            low, high = extrema[metric]
            normalized = 0.0 if high == low else (float(value) - low) / (high - low)
            components[metric] = round(normalized, 4)
            weighted_loss += weight * normalized
            available_weight += weight
        score = 100.0 * (1 - weighted_loss / available_weight) if available_weight else 50.0
        # Missing data is uncertainty, not evidence of a low-cost/reliable route.
        total_weight = sum(PROFILE_WEIGHTS[profile].values())
        completeness = available_weight / total_weight if total_weight else 0.0
        missing_penalty = 100.0 * (1 - completeness)
        score -= missing_penalty
        source_confidence = numeric(route.get("source_confidence"))
        if source_confidence is not None:
            score += 2.0 * (max(0.0, min(1.0, source_confidence)) - 0.5)
        ranked.append(
            {
                **route,
                "score": round(max(0.0, min(100.0, score)), 2),
                "score_profile": profile,
                "evidence_completeness": round(completeness, 4),
                "missing_evidence_penalty": round(missing_penalty, 2),
                "score_components_loss": components,
                "missing_metrics": sorted(
                    metric for metric in PROFILE_WEIGHTS[profile] if metrics.get(metric) is None
                ),
            }
        )
    ranked.sort(key=lambda item: (-item["score"], numeric(item.get("planning_upper_min")) or numeric(item.get("duration_min")) or math.inf))
    return {
        "ok": True,
        "profile": profile,
        "ranked": ranked,
        "rejected": rejected,
        "method_note": "Hard constraints are applied first; observed metrics are normalized and missing evidence receives an explicit uncertainty penalty. Missing evidence is never invented.",
    }


def parse_observed_at(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = parse_iso(value)
        if parsed and parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc) if parsed else None
    except ValueError:
        return None


def compare_predictions(args: argparse.Namespace) -> dict[str, Any]:
    payload = read_json(args.input)
    predictions = payload.get("predictions") if isinstance(payload, dict) else None
    if not isinstance(predictions, list):
        fail("Girdi bir 'predictions' listesi içermeli.")
    usable = [item for item in predictions if numeric(item.get("minutes")) and numeric(item.get("minutes")) > 0]
    if not usable:
        fail("Kullanılabilir pozitif dakika tahmini yok.")
    values = [float(item["minutes"]) for item in usable]
    median = statistics.median(values)
    mad = statistics.median(abs(value - median) for value in values)
    spread = max(values) - min(values)
    context = payload.get("context") or {}
    mode = str(context.get("mode") or "transit")
    risk = max(0.0, min(1.0, float(context.get("risk_level") or 0.0)))
    bus_share = max(0.0, min(1.0, float(context.get("bus_share") or 0.0)))
    disruption = bool(context.get("disruption"))
    severe_weather = bool(context.get("severe_weather"))

    floor_ratio = 0.10 if mode == "transit" else 0.12 if mode == "driving" else 0.08
    floor_minutes = 5.0 if mode in {"transit", "driving"} else 3.0
    uncertainty = max(floor_minutes, median * floor_ratio, spread / 2, 1.4826 * mad)
    extra = median * (0.20 * risk + 0.10 * bus_share)
    if disruption:
        extra += 8.0
    if severe_weather:
        extra += 5.0
    lower = max(1.0, median - max(3.0, uncertainty * 0.5))
    upper = median + uncertainty + extra
    planning_buffer = math.ceil((upper - median) / 5) * 5

    now = datetime.now(timezone.utc)
    observed = [parse_observed_at(item.get("observed_at")) for item in usable]
    fresh_count = sum(
        1
        for item in observed
        if item and -120 <= (now - item).total_seconds() <= 15 * 60
    )
    relative_spread = spread / median if median else math.inf
    if len(usable) >= 3 and fresh_count >= 2 and relative_spread <= 0.20 and not disruption:
        confidence = "high"
    elif len(usable) >= 2 and fresh_count >= 1 and relative_spread <= 0.35:
        confidence = "medium"
    else:
        confidence = "low"

    calibration_rows = [
        item for item in usable if numeric(item.get("actual_minutes")) is not None
    ]
    calibration: dict[str, Any] = {"calibrated": False, "reason": "Geçmiş gerçek yolculuk süresi sağlanmadı."}
    if calibration_rows:
        errors = [float(item["minutes"]) - float(item["actual_minutes"]) for item in calibration_rows]
        absolute = [abs(value) for value in errors]
        percentage = [
            abs(float(item["minutes"]) - float(item["actual_minutes"])) / float(item["actual_minutes"]) * 100
            for item in calibration_rows
            if float(item["actual_minutes"]) > 0
        ]
        calibration = {
            "calibrated": True,
            "samples": len(errors),
            "mean_error_min": round(statistics.mean(errors), 2),
            "mean_absolute_error_min": round(statistics.mean(absolute), 2),
            "mean_absolute_percentage_error": round(statistics.mean(percentage), 2) if percentage else None,
        }

    return {
        "ok": True,
        "providers": [str(item.get("provider") or "unknown") for item in usable],
        "prediction_count": len(usable),
        "median_eta_min": round(median, 1),
        "provider_range_min": [round(min(values), 1), round(max(values), 1)],
        "planning_window_min": [round(lower, 1), round(upper, 1)],
        "recommended_buffer_min": planning_buffer,
        "confidence": confidence,
        "fresh_prediction_count": fresh_count,
        "relative_provider_spread": round(relative_spread, 3),
        "calibration": calibration,
        "method_note": "The planning window is a conservative heuristic, not a statistically calibrated guarantee.",
    }


def matrix_value(matrix: dict[str, Any], source: str, target: str) -> float | None:
    row = matrix.get(source)
    value = row.get(target) if isinstance(row, dict) else None
    return numeric(value)


def evaluate_order(
    start_id: str,
    end_id: str,
    depart_at: datetime,
    order: tuple[dict[str, Any], ...],
    matrix: dict[str, Any],
) -> dict[str, Any] | None:
    current_id = start_id
    current_time = depart_at
    timeline: list[dict[str, Any]] = []
    total_travel = 0.0
    total_wait = 0.0
    for stop in order:
        travel = matrix_value(matrix, current_id, str(stop["id"]))
        if travel is None:
            return None
        current_time = current_time + timedelta_minutes(travel)
        total_travel += travel
        opened = parse_iso(stop.get("open"))
        closed = parse_iso(stop.get("close"))
        opened = align_timezone(opened, current_time)
        closed = align_timezone(closed, current_time)
        wait = 0.0
        if opened and current_time < opened:
            wait = (opened - current_time).total_seconds() / 60
            current_time = opened
            total_wait += wait
        dwell = float(stop.get("dwell_min") or 0)
        leave_time = current_time + timedelta_minutes(dwell)
        if closed and leave_time > closed:
            return None
        timeline.append(
            {
                "stop_id": str(stop["id"]),
                "arrival": current_time.isoformat(),
                "wait_min": round(wait, 1),
                "dwell_min": round(dwell, 1),
                "departure": leave_time.isoformat(),
            }
        )
        current_time = leave_time
        current_id = str(stop["id"])
    final_travel = matrix_value(matrix, current_id, end_id)
    if final_travel is None:
        return None
    current_time = current_time + timedelta_minutes(final_travel)
    total_travel += final_travel
    return {
        "order": [str(item["id"]) for item in order],
        "timeline": timeline,
        "arrival_at_end": current_time.isoformat(),
        "total_travel_min": round(total_travel, 1),
        "total_wait_min": round(total_wait, 1),
        "elapsed_min": round((current_time - depart_at).total_seconds() / 60, 1),
    }


def timedelta_minutes(minutes: float):
    from datetime import timedelta

    return timedelta(minutes=minutes)


def align_timezone(value: datetime | None, reference: datetime) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None and reference.tzinfo is not None:
        return value.replace(tzinfo=reference.tzinfo)
    if value.tzinfo is not None and reference.tzinfo is None:
        return value.replace(tzinfo=None)
    return value


def optimize_stops(args: argparse.Namespace) -> dict[str, Any]:
    payload = read_json(args.input)
    try:
        start_id = str(payload["start_id"])
        end_id = str(payload["end_id"])
        depart_at = parse_iso(payload["depart_at"])
        stops = payload.get("stops") or []
        matrix = payload["matrix"]
    except (KeyError, TypeError, ValueError) as exc:
        fail(f"Geçersiz optimize girdisi: {exc}")
    if depart_at is None:
        fail("depart_at gerekli.")
    if not isinstance(stops, list) or not isinstance(matrix, dict):
        fail("stops listesi ve matrix nesnesi gerekli.")
    if any("id" not in stop for stop in stops):
        fail("Her durakta id bulunmalı.")
    if len(stops) > 8 and not payload.get("fixed_order"):
        fail("Kesin permütasyon araması en fazla 8 durak destekler; yolculuğu zaman bloklarına ayırın.")
    top_n = max(1, min(5, int(payload.get("top_n") or 3)))
    if payload.get("fixed_order"):
        orders = [tuple(stops)]
    else:
        orders = itertools.permutations(stops)
    feasible: list[dict[str, Any]] = []
    tested = 0
    for order in orders:
        tested += 1
        result = evaluate_order(start_id, end_id, depart_at, order, matrix)
        if result:
            feasible.append(result)
    feasible.sort(key=lambda item: (item["elapsed_min"], item["total_travel_min"], item["order"]))
    return {
        "ok": True,
        "tested_orders": tested,
        "feasible_orders": len(feasible),
        "best": feasible[:top_n],
        "warning": None if feasible else "Açılış-kapanış ve seyahat süreleriyle uyumlu sıra bulunamadı.",
        "method_note": "Only supplied matrix times are used; the script does not fetch or invent travel times.",
    }


ALLOWED_PREFERENCE_KEYS = {
    "default_mode",
    "preferred_profiles",
    "fare_category",
    "pass_type",
    "max_walk_min",
    "max_transfers",
    "prefer_rail",
    "avoid_modes",
    "accessibility_needs",
    "language",
    "timezone",
    "home_label",
    "home_coordinates",
    "work_label",
    "work_coordinates",
}
SENSITIVE_PREFERENCE_KEYS = {
    "home_label",
    "home_coordinates",
    "work_label",
    "work_coordinates",
}


def default_preferences_path() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "Codex" / "plan-smart-routes" / "preferences.json"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "plan-smart-routes" / "preferences.json"


def preferences(args: argparse.Namespace) -> dict[str, Any]:
    path = Path(args.path).expanduser() if args.path else default_preferences_path()
    if args.action == "show":
        if not path.exists():
            return {"ok": True, "path": str(path), "preferences": {}, "exists": False}
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            return {"ok": True, "path": str(path), "preferences": data, "exists": True}
        except (OSError, json.JSONDecodeError) as exc:
            fail(f"Tercih dosyası okunamadı: {exc}")
    if not args.allow_write:
        fail("Kalıcı yazma için --allow-write gerekli; kullanıcı onayı olmadan tercih kaydetmeyin.")
    try:
        incoming = json.loads(args.data)
    except json.JSONDecodeError as exc:
        fail(f"--data geçerli JSON nesnesi olmalı: {exc}")
    if not isinstance(incoming, dict):
        fail("--data bir JSON nesnesi olmalı.")
    unknown = sorted(set(incoming) - ALLOWED_PREFERENCE_KEYS)
    if unknown:
        fail("İzin verilmeyen tercih anahtarları: " + ", ".join(unknown))
    sensitive = sorted(set(incoming) & SENSITIVE_PREFERENCE_KEYS)
    if sensitive and not args.allow_sensitive:
        fail("Hassas ev/iş verisi için --allow-sensitive ve açık kullanıcı onayı gerekli.")
    current: dict[str, Any] = {}
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as handle:
                loaded = json.load(handle)
                if isinstance(loaded, dict):
                    current = loaded
        except (OSError, json.JSONDecodeError) as exc:
            fail(f"Mevcut tercih dosyası okunamadı: {exc}")
    current.update(incoming)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent, suffix=".tmp") as handle:
            json.dump(current, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            temp_name = handle.name
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
    return {"ok": True, "path": str(path), "preferences": current, "saved": True}


def weather_along_route(args: argparse.Namespace) -> dict[str, Any]:
    if not args.point:
        fail("En az bir --point lat,lon|etiket gerekli.")
    if len(args.point) > 8:
        fail("Tek istekte en fazla 8 örnek nokta kullanın.")
    try:
        points = [parse_point(item) for item in args.point]
        when = parse_iso(args.at)
    except ValueError as exc:
        fail(str(exc))
    if any(not point["has_coords"] for point in points):
        fail("Hava sorgusundaki tüm noktalar koordinat içermeli.")
    if when is None:
        when = datetime.now().astimezone()
    today = datetime.now(when.tzinfo).date() if when.tzinfo else datetime.now().date()
    day_delta = (when.date() - today).days
    if day_delta < 0 or day_delta > 15:
        fail("Open-Meteo forecast helper yalnız bugün ile 15 gün sonrası arasını destekler.")
    params = {
        "latitude": ",".join(f"{point['lat']:.7f}" for point in points),
        "longitude": ",".join(f"{point['lon']:.7f}" for point in points),
        "hourly": "precipitation_probability,rain,snowfall,weather_code,wind_speed_10m,wind_gusts_10m",
        "timezone": "GMT",
        "timeformat": "unixtime",
        "forecast_days": str(max(1, day_delta + 1)),
    }
    endpoint = "https://api.open-meteo.com/v1/forecast?" + urlencode(params)
    request = Request(endpoint, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=args.timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # network and malformed response are reported, never hidden
        fail(f"Open-Meteo isteği başarısız: {exc}")
    responses = payload if isinstance(payload, list) else [payload]
    if len(responses) != len(points):
        fail("Hava servisi beklenmeyen sayıda konum döndürdü.")
    results: list[dict[str, Any]] = []
    for point, item in zip(points, responses):
        hourly = item.get("hourly") or {}
        times = hourly.get("time") or []
        if not times:
            continue
        target_epoch = when.timestamp()
        parsed_times = [float(value) for value in times]
        index = min(range(len(parsed_times)), key=lambda idx: abs(parsed_times[idx] - target_epoch))

        def value(name: str) -> Any:
            values = hourly.get(name) or []
            return values[index] if index < len(values) else None

        precip_prob = numeric(value("precipitation_probability")) or 0.0
        rain = numeric(value("rain")) or 0.0
        snow = numeric(value("snowfall")) or 0.0
        gust = numeric(value("wind_gusts_10m")) or 0.0
        flags: list[str] = []
        if precip_prob >= 50 or rain >= 0.5:
            flags.append("rain")
        if snow > 0:
            flags.append("snow")
        if gust >= 50:
            flags.append("strong_wind")
        results.append(
            {
                "label": point["label"],
                "latitude": point["lat"],
                "longitude": point["lon"],
                "forecast_time": datetime.fromtimestamp(parsed_times[index], timezone.utc).isoformat(),
                "timezone": item.get("timezone"),
                "precipitation_probability_pct": value("precipitation_probability"),
                "rain_mm": value("rain"),
                "snowfall_cm": value("snowfall"),
                "weather_code": value("weather_code"),
                "wind_speed_kmh": value("wind_speed_10m"),
                "wind_gusts_kmh": value("wind_gusts_10m"),
                "route_risk_flags": flags,
            }
        )
    return {
        "ok": True,
        "requested_at": when.isoformat(),
        "points": results,
        "source": endpoint,
        "attribution": "Weather data: Open-Meteo (CC BY 4.0); free endpoint is non-commercial only.",
        "integrity_note": "Forecasts are uncertain; use them as route-exposure signals, not guarantees.",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic helpers for the plan-smart-routes skill")
    parser.add_argument("--version", action="version", version=VERSION)
    parser.add_argument("--compact", action="store_true", help="Compact JSON output")
    subparsers = parser.add_subparsers(dest="command", required=True)

    links = subparsers.add_parser("links", help="Generate capability-aware navigation links")
    links.add_argument("--origin", required=True, help="label/address or lat,lon|label")
    links.add_argument("--destination", required=True, help="label/address or lat,lon|label")
    links.add_argument("--waypoint", action="append", default=[], help="repeatable label/address or lat,lon|label")
    links.add_argument("--mode", choices=["transit", "driving", "walking", "bicycling"], default="transit")
    links.add_argument("--when", help="ISO 8601 trip time")
    links.add_argument("--time-kind", choices=["depart", "arrive"], default="depart")
    links.add_argument(
        "--providers",
        default="google,yandex,yandex-navigator,moovit,here,bing,apple,waze,citymapper,osm",
    )
    links.add_argument("--moovit-metro-id")
    links.add_argument("--lang", default="tr")
    links.set_defaults(handler=build_links)

    score = subparsers.add_parser("score", help="Normalize, deduplicate and score collected route candidates")
    score.add_argument("--input", required=True, help="JSON file or - for stdin")
    score.add_argument("--profile", choices=sorted(PROFILE_WEIGHTS))
    score.add_argument("--no-dedupe", action="store_true")
    score.set_defaults(handler=score_routes)

    compare = subparsers.add_parser("compare", help="Compare provider ETA predictions and make a planning window")
    compare.add_argument("--input", required=True, help="JSON file or - for stdin")
    compare.set_defaults(handler=compare_predictions)

    optimize = subparsers.add_parser("optimize", help="Order up to 8 stops using supplied matrix and time windows")
    optimize.add_argument("--input", required=True, help="JSON file or - for stdin")
    optimize.set_defaults(handler=optimize_stops)

    prefs = subparsers.add_parser("preferences", help="Show or save minimal trip preferences")
    prefs.add_argument("action", choices=["show", "save"])
    prefs.add_argument("--path")
    prefs.add_argument("--data", default="{}", help="JSON object for save")
    prefs.add_argument("--allow-write", action="store_true")
    prefs.add_argument("--allow-sensitive", action="store_true")
    prefs.set_defaults(handler=preferences)

    weather = subparsers.add_parser("weather", help="Query no-key non-commercial weather along sampled route points")
    weather.add_argument("--point", action="append", default=[], help="repeatable lat,lon|label")
    weather.add_argument("--at", help="ISO 8601 local trip time; defaults to now")
    weather.add_argument("--timeout", type=float, default=20.0)
    weather.set_defaults(handler=weather_along_route)
    for command_parser in (links, score, compare, optimize, prefs, weather):
        command_parser.add_argument(
            "--compact",
            action="store_true",
            default=argparse.SUPPRESS,
            help=argparse.SUPPRESS,
        )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    payload = args.handler(args)
    emit(payload, compact=args.compact)


if __name__ == "__main__":
    main()
