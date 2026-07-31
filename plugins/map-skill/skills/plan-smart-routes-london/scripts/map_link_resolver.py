#!/usr/bin/env python3
"""Safely follow supported map links and extract explicit coordinates.

This is a URL resolver, not a geocoder. It never guesses coordinates from a
place name and never sends the URL to an unrelated service.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any
from urllib.parse import parse_qs, unquote, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


VERSION = "1.0.0"
USER_AGENT = f"plan-smart-routes/{VERSION} (map link resolver)"
MAX_RESPONSE_BYTES = 262_144

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


PROVIDER_DOMAINS: dict[str, tuple[str, ...]] = {
    "google": ("google.com", "google.com.tr", "maps.app.goo.gl", "goo.gl"),
    "yandex": ("yandex.com", "yandex.com.tr", "yandex.ru"),
    "moovit": ("moovit.com", "moovitapp.com"),
    "here": ("here.com", "share.here.com", "wego.here.com"),
    "bing": ("bing.com",),
    "apple": ("maps.apple.com",),
    "waze": ("waze.com",),
    "citymapper": ("citymapper.com",),
    "osm": ("openstreetmap.org",),
}


def emit(payload: Any, compact: bool) -> None:
    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=None if compact else 2,
            separators=(",", ":") if compact else None,
        )
    )


def fail(message: str, compact: bool = False) -> None:
    emit({"ok": False, "error": message}, compact)
    raise SystemExit(2)


def normalized_host(url: str) -> str:
    return (urlparse(url).hostname or "").lower().rstrip(".")


def host_matches(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def provider_for_url(url: str) -> str | None:
    host = normalized_host(url)
    for provider, domains in PROVIDER_DOMAINS.items():
        if any(host_matches(host, domain) for domain in domains):
            return provider
    return None


def validate_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme != "https":
        raise ValueError("Yalnız HTTPS harita bağlantıları kabul edilir.")
    if parsed.username or parsed.password:
        raise ValueError("Kimlik bilgisi içeren URL kabul edilmez.")
    if not provider_for_url(url):
        raise ValueError("Desteklenmeyen harita alan adı; güvenlik nedeniyle bağlantı izlenmedi.")
    return url.strip()


class RestrictedRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        absolute = urljoin(req.full_url, newurl)
        validate_url(absolute)
        return super().redirect_request(req, fp, code, msg, headers, absolute)


def follow_supported_link(url: str, timeout: float) -> tuple[str, int | None]:
    opener = build_opener(RestrictedRedirectHandler())
    request = Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
        method="GET",
    )
    with opener.open(request, timeout=timeout) as response:
        final_url = validate_url(response.geturl())
        response.read(MAX_RESPONSE_BYTES)
        return final_url, getattr(response, "status", None)


def coordinate_pair(raw: str, *, lon_first: bool = False) -> tuple[float, float] | None:
    match = re.fullmatch(
        r"\s*(-?\d+(?:\.\d+)?)\s*[, _]\s*(-?\d+(?:\.\d+)?)\s*",
        unquote(raw),
    )
    if not match:
        return None
    first, second = float(match.group(1)), float(match.group(2))
    lat, lon = (second, first) if lon_first else (first, second)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon


def add_point(
    points: list[dict[str, Any]],
    role: str,
    pair: tuple[float, float] | None,
    label: str | None = None,
    confidence: str = "explicit",
) -> None:
    if pair is None:
        return
    lat, lon = pair
    record = {
        "role": role,
        "latitude": round(lat, 7),
        "longitude": round(lon, 7),
        "label": label.strip() if isinstance(label, str) and label.strip() else None,
        "confidence": confidence,
    }
    signature = (record["role"], record["latitude"], record["longitude"])
    if not any(
        (item["role"], item["latitude"], item["longitude"]) == signature
        for item in points
    ):
        points.append(record)


def query_first(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key) or []
    return values[0] if values else None


def label_from_google_path(path: str) -> str | None:
    match = re.search(r"/(?:place|search)/([^/]+)", path)
    return unquote(match.group(1).replace("+", " ")) if match else None


def extract_points(url: str, provider: str) -> tuple[list[dict[str, Any]], list[str]]:
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    points: list[dict[str, Any]] = []
    notes: list[str] = []

    if provider == "google":
        label = label_from_google_path(parsed.path)
        data_match = re.search(r"!3d(-?\d+(?:\.\d+)?).*?!4d(-?\d+(?:\.\d+)?)", url)
        if data_match:
            add_point(points, "place", (float(data_match.group(1)), float(data_match.group(2))), label)
        for key in ("query", "q", "destination", "origin"):
            value = query_first(query, key)
            role = "place" if key in {"query", "q"} else key
            add_point(points, role, coordinate_pair(value or ""), label if role == "place" else None)
        center = re.search(r"/@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", parsed.path)
        if center and not points:
            add_point(
                points,
                "map_center",
                (float(center.group(1)), float(center.group(2))),
                label,
                confidence="map_center_not_verified_place",
            )
            notes.append("Google @ koordinatı bazen yalnız harita merkezidir; yer girişiyle doğrula.")

    elif provider == "yandex":
        ll = query_first(query, "ll")
        add_point(points, "map_center", coordinate_pair(ll or "", lon_first=True), confidence="map_center_not_verified_place")
        rtext = query_first(query, "rtext")
        if rtext:
            route_parts = rtext.split("~")
            for index, raw in enumerate(route_parts):
                role = "origin" if index == 0 else "destination" if index == len(route_parts) - 1 else "waypoint"
                add_point(points, role, coordinate_pair(raw))
        whatshere = query_first(query, "whatshere[point]")
        add_point(points, "place", coordinate_pair(whatshere or "", lon_first=True))

    elif provider == "moovit":
        origin = coordinate_pair(
            f"{query_first(query, 'orig_lat')},{query_first(query, 'orig_lon')}"
        )
        destination = coordinate_pair(
            f"{query_first(query, 'dest_lat')},{query_first(query, 'dest_lon')}"
        )
        add_point(points, "origin", origin, query_first(query, "orig_name"))
        add_point(points, "destination", destination, query_first(query, "dest_name"))
        tll = query_first(query, "tll")
        add_point(points, "destination", coordinate_pair(tll or ""), query_first(query, "to"))

    elif provider == "here":
        route_match = re.search(r"/r/(.+)$", parsed.path)
        if route_match:
            segments = route_match.group(1).split("/")
            for index, segment in enumerate(segments):
                fields = segment.split(",")
                pair = coordinate_pair(",".join(fields[:2])) if len(fields) >= 2 else None
                label = unquote(fields[2]) if len(fields) >= 3 else None
                role = "origin" if index == 0 else "destination" if index == len(segments) - 1 else "waypoint"
                add_point(points, role, pair, label)

    elif provider == "bing":
        rtp = query_first(query, "rtp")
        if rtp:
            route_parts = rtp.split("~")
            for index, part in enumerate(route_parts):
                match = re.match(r"pos\.(-?\d+(?:\.\d+)?)_(-?\d+(?:\.\d+)?)(?:_(.*))?", part)
                if match:
                    role = "origin" if index == 0 else "destination" if index == len(route_parts) - 1 else "waypoint"
                    add_point(points, role, (float(match.group(1)), float(match.group(2))), match.group(3))

    elif provider == "apple":
        for key, role in (("saddr", "origin"), ("daddr", "destination"), ("source", "origin"), ("destination", "destination"), ("ll", "place")):
            add_point(points, role, coordinate_pair(query_first(query, key) or ""))

    elif provider == "waze":
        add_point(points, "destination", coordinate_pair(query_first(query, "ll") or ""), query_first(query, "q"))

    elif provider == "citymapper":
        add_point(points, "origin", coordinate_pair(query_first(query, "startcoord") or ""), query_first(query, "startname"))
        add_point(points, "destination", coordinate_pair(query_first(query, "endcoord") or ""), query_first(query, "endname"))

    elif provider == "osm":
        add_point(
            points,
            "place",
            coordinate_pair(f"{query_first(query, 'mlat')},{query_first(query, 'mlon')}"),
        )
        route = query_first(query, "route")
        if route:
            route_parts = route.split(";")
            for index, raw in enumerate(route_parts):
                role = "origin" if index == 0 else "destination" if index == len(route_parts) - 1 else "waypoint"
                add_point(points, role, coordinate_pair(raw))
        fragment_match = re.search(r"map=\d+(?:\.\d+)?/(-?\d+(?:\.\d+)?)/(-?\d+(?:\.\d+)?)", parsed.fragment)
        if fragment_match and not points:
            add_point(
                points,
                "map_center",
                (float(fragment_match.group(1)), float(fragment_match.group(2))),
                confidence="map_center_not_verified_place",
            )

    if not points:
        notes.append("Bağlantıda açık koordinat bulunamadı; yeri insan-görünür sayfada doğrula veya kullanıcıdan pin iste.")
    return points, notes


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve supported map links without geocoding")
    parser.add_argument("url")
    parser.add_argument("--no-follow", action="store_true", help="Do not follow supported redirects")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--version", action="version", version=VERSION)
    args = parser.parse_args()

    try:
        original = validate_url(args.url)
        final_url, status = (original, None) if args.no_follow else follow_supported_link(original, args.timeout)
    except Exception as exc:
        fail(str(exc), args.compact)

    provider = provider_for_url(final_url)
    if provider is None:
        fail("Son bağlantı desteklenen bir harita sağlayıcısı değil.", args.compact)
    points, notes = extract_points(final_url, provider)
    emit(
        {
            "ok": True,
            "provider": provider,
            "original_url": original,
            "final_url": final_url,
            "http_status": status,
            "points": points,
            "notes": notes,
            "integrity_note": "Açık URL koordinatları çıkarıldı; bu sonuç adres, şube, giriş veya rota doğrulaması değildir.",
        },
        args.compact,
    )


if __name__ == "__main__":
    main()
