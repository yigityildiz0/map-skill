#!/usr/bin/env python3
"""Fetch a small, verified set of official Istanbul mobility signals.

The script deliberately avoids credentialed IETT SOAP methods and large
historical downloads. A successful response means the endpoint answered; it
does not prove that every route or vehicle is represented.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape
from xml.etree import ElementTree


VERSION = "1.0.0"
USER_AGENT = f"plan-smart-routes/{VERSION} (personal trip planning)"
ISTANBUL_TZ = timezone(timedelta(hours=3), name="Europe/Istanbul")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

TRAFFIC_INDEX_URL = "https://api.ibb.gov.tr/tkmservices/api/TrafficData/v1/TrafficIndexHistory/1/5M"
TRAFFIC_MAP_URL = "https://uym.ibb.gov.tr/yharita6/"
ROAD_ANNOUNCEMENTS_URL = "https://tkmservices.ibb.gov.tr/web/api/IntensityMap/v1/CurrentAnnouncement"
METRO_STATUS_URL = "https://api.ibb.gov.tr/MetroIstanbul/api/MetroMobile/V2/GetServiceStatuses"
METRO_FARES_URL = "https://api.ibb.gov.tr/MetroIstanbul/api/MetroMobile/V2/GetTicketPrice/TR"
CKAN_PACKAGE_URL = "https://data.ibb.gov.tr/api/3/action/package_show?id={}"
IETT_ALERTS_URL = "https://api.ibb.gov.tr/iett/UlasimDinamikVeri/Duyurular.asmx"
IETT_ALERTS_WSDL = IETT_ALERTS_URL + "?wsdl"
IETT_VEHICLES_URL = "https://api.ibb.gov.tr/iett/FiloDurum/SeferGerceklesme.asmx"
IETT_VEHICLES_WSDL = IETT_VEHICLES_URL + "?wsdl"


def fetch(url: str, timeout: float, accept: str = "*/*") -> tuple[bytes, dict[str, str]]:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    with urlopen(request, timeout=timeout) as response:
        headers = {key.lower(): value for key, value in response.headers.items()}
        return response.read(), headers


def fetch_json(url: str, timeout: float) -> Any:
    body, _ = fetch(url, timeout, "application/json")
    return json.loads(body.decode("utf-8-sig"))


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def soap_json(
    url: str,
    operation: str,
    parameters: dict[str, str],
    timeout: float,
) -> list[dict[str, Any]]:
    parameter_xml = "".join(
        f"<{name}>{escape(value)}</{name}>" for name, value in parameters.items()
    )
    envelope = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
        'xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
        f'<soap:Body><{operation} xmlns="http://tempuri.org/">'
        f"{parameter_xml}</{operation}></soap:Body></soap:Envelope>"
    )
    request = Request(
        url,
        data=envelope.encode("utf-8"),
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/xml",
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f'"http://tempuri.org/{operation}"',
        },
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        root = ElementTree.fromstring(response.read())
    result_text = None
    expected = f"{operation}Result"
    for element in root.iter():
        if local_name(element.tag) == expected:
            result_text = element.text
            break
    if result_text is None:
        raise ValueError(f"SOAP yanıtında {expected} yok")
    payload = json.loads(result_text)
    if not isinstance(payload, list):
        raise ValueError(f"{operation} JSON listesi döndürmedi")
    return [item for item in payload if isinstance(item, dict)]


def traffic_index(timeout: float) -> dict[str, Any]:
    body, headers = fetch(TRAFFIC_INDEX_URL, timeout, "application/xml")
    root = ElementTree.fromstring(body)
    rows: list[dict[str, Any]] = []
    for item in root:
        values = {local_name(child.tag): child.text for child in item}
        if values.get("TrafficIndex") and values.get("TrafficIndexDate"):
            observed = datetime.fromisoformat(str(values["TrafficIndexDate"]))
            observed = observed.replace(tzinfo=ISTANBUL_TZ) if observed.tzinfo is None else observed
            rows.append({"value": int(values["TrafficIndex"]), "observed_at": observed})
    if not rows:
        raise ValueError("Trafik indeks yanıtında kayıt yok")
    latest = max(rows, key=lambda row: row["observed_at"])
    now = datetime.now(ISTANBUL_TZ)
    age_minutes = max(0.0, (now - latest["observed_at"]).total_seconds() / 60)
    return {
        "value": latest["value"],
        "observed_at": latest["observed_at"].isoformat(),
        "age_minutes": round(age_minutes, 1),
        "sample_count_24h": len(rows),
        "scope": "citywide_context_only",
        "source": TRAFFIC_INDEX_URL,
        "traffic_map": TRAFFIC_MAP_URL,
        "content_type": headers.get("content-type"),
        "warning": "Şehir geneli indeks, seçili yol segmentinin seyahat süresi değildir.",
    }


def road_announcements(timeout: float) -> dict[str, Any]:
    payload = fetch_json(ROAD_ANNOUNCEMENTS_URL, timeout)
    if not isinstance(payload, list):
        raise ValueError("Yol duyuru yanıtı liste değil")
    records = [
        {
            "id": item.get("Id"),
            "title": item.get("Baslik") or item.get("Metin"),
            "type": item.get("Tipi"),
            "started_at": item.get("GirisTarihi"),
            "ends_at": item.get("BitisTarihi"),
            "coordinates": item.get("Koordinat"),
            "priority": item.get("Oncelik"),
        }
        for item in payload
        if isinstance(item, dict)
    ]
    return {
        "records": records,
        "record_count": len(records),
        "source": ROAD_ANNOUNCEMENTS_URL,
        "warning": "Resmi canlı-harita endpointi; yayımlanmış kararlı şema yok. Sadece rotayla mekânsal olarak eşleşen kayıtları kullan.",
    }


def iett_alerts(lines: set[str], timeout: float) -> dict[str, Any]:
    payload = soap_json(IETT_ALERTS_URL, "GetDuyurular_json", {}, timeout)
    records = []
    for item in payload:
        line_code = str(item.get("HATKODU") or "").strip().upper()
        if line_code not in lines:
            continue
        records.append(
            {
                "line": line_code,
                "line_name": item.get("HAT"),
                "type": item.get("TIP"),
                "record_time": item.get("GUNCELLEME_SAATI"),
                "message": item.get("MESAJ"),
            }
        )
    return {
        "records": records,
        "requested_lines": sorted(lines),
        "source": IETT_ALERTS_WSDL,
        "data_type": "official_soap_alerts_not_gtfs_rt",
        "warning": "Bazı kayıtlarda tam ISO tarih yoktur; mesajdaki gün/saat bağlamını doğrula.",
    }


def iett_vehicle_positions(lines: set[str], timeout: float) -> dict[str, Any]:
    per_line: dict[str, Any] = {}
    line_errors: list[dict[str, str]] = []
    now = datetime.now(ISTANBUL_TZ)
    for line in sorted(lines):
        try:
            payload = soap_json(
                IETT_VEHICLES_URL,
                "GetHatOtoKonum_json",
                {"HatKodu": line},
                timeout,
            )
            vehicles = []
            for item in payload:
                observed_raw = item.get("son_konum_zamani")
                age_minutes = None
                if isinstance(observed_raw, str):
                    try:
                        observed = datetime.fromisoformat(observed_raw)
                        if observed.tzinfo is None:
                            observed = observed.replace(tzinfo=ISTANBUL_TZ)
                        age_minutes = max(0.0, (now - observed).total_seconds() / 60)
                    except ValueError:
                        pass
                vehicles.append(
                    {
                        "vehicle_id": item.get("kapino"),
                        "latitude": item.get("enlem"),
                        "longitude": item.get("boylam"),
                        "route_code": item.get("guzergahkodu"),
                        "direction": item.get("yon"),
                        "nearest_stop_code": item.get("yakinDurakKodu"),
                        "position_time": observed_raw,
                        "age_minutes": round(age_minutes, 1) if age_minutes is not None else None,
                    }
                )
            per_line[line] = {"vehicle_count": len(vehicles), "vehicles": vehicles}
        except Exception as exc:
            line_errors.append({"line": line, "error": str(exc)})
    return {
        "lines": per_line,
        "line_errors": line_errors,
        "source": IETT_VEHICLES_WSDL,
        "data_type": "official_live_vehicle_positions_not_gtfs_rt",
        "warning": "Araç konumu yolcu ETA'sı değildir; rota yönü, durak sırası ve konum yaşıyla doğrula.",
    }


def metro_status(timeout: float, lines: set[str]) -> dict[str, Any]:
    payload = fetch_json(METRO_STATUS_URL, timeout)
    if not payload.get("Success"):
        raise ValueError(payload.get("Error") or "Metro status Success=false")
    records = []
    for item in payload.get("Data") or []:
        line_name = str(item.get("LineName") or "").upper()
        if lines and line_name not in lines:
            continue
        records.append(
            {
                "line": line_name,
                "description": item.get("Description"),
                "record_active": item.get("IsActive"),
                "updated_at": item.get("UpdateDate"),
                "status_image": item.get("ServiceStatuImage"),
            }
        )
    returned_lines = {str(item["line"]) for item in records if item.get("line")}
    return {
        "records": records,
        "requested_lines": sorted(lines),
        "requested_lines_not_returned": sorted(lines - returned_lines),
        "source": METRO_STATUS_URL,
        "warning": "record_active alanını veya istenen hattın yanıtta bulunmamasını 'hat sorunsuz' diye yorumlama; açıklamayı, güncelleme zamanını ve resmî yolcu sayfasını kontrol et.",
    }


def metro_fares(timeout: float) -> dict[str, Any]:
    payload = fetch_json(METRO_FARES_URL, timeout)
    if not payload.get("Success"):
        raise ValueError(payload.get("Error") or "Metro fare Success=false")
    return {
        "fare_groups": payload.get("Data") or [],
        "source": METRO_FARES_URL,
        "warning": "Bu liste temel Metro İstanbul fiyat sinyalidir; aktarma, mesafe, gece, Marmaray/Metrobüs/vapur ve iade kuralları ayrıca doğrulanmalıdır.",
    }


def package_metadata(package_name: str, timeout: float) -> dict[str, Any]:
    url = CKAN_PACKAGE_URL.format(quote(package_name, safe=""))
    payload = fetch_json(url, timeout)
    if not payload.get("success"):
        raise ValueError(f"CKAN package_show başarısız: {package_name}")
    item = payload["result"]
    resources = [
        {
            "name": resource.get("name"),
            "format": resource.get("format"),
            "last_modified": resource.get("last_modified"),
            "url": resource.get("url"),
        }
        for resource in item.get("resources") or []
    ]
    current_use = package_name == "iett-gtfs-verisi"
    return {
        "name": item.get("name"),
        "title": item.get("title"),
        "metadata_modified": item.get("metadata_modified"),
        "license": item.get("license_title"),
        "notes": item.get("notes"),
        "resources": resources,
        "current_routing_baseline": current_use,
        "warning": (
            "IETT static schedule baseline; it is not GTFS-Realtime and does not prove live operation."
            if current_use
            else "Portal notes say this multi-operator dataset will not be updated; do not use it as a current timetable."
        ),
        "source": url,
    }


def safe_check(name: str, function, errors: list[dict[str, str]]) -> Any:
    try:
        return function()
    except Exception as exc:
        errors.append({"check": name, "error": str(exc)})
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch official Istanbul mobility context")
    parser.add_argument("--line", action="append", default=[], help="Metro line filter, e.g. M2; repeatable")
    parser.add_argument("--bus-line", action="append", default=[], help="IETT line filter, e.g. 34AS; repeatable")
    parser.add_argument("--include-fares", action="store_true")
    parser.add_argument("--skip-feeds", action="store_true")
    parser.add_argument("--skip-traffic", action="store_true")
    parser.add_argument("--skip-road-alerts", action="store_true")
    parser.add_argument("--skip-metro", action="store_true")
    parser.add_argument("--skip-iett", action="store_true")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    errors: list[dict[str, str]] = []
    output: dict[str, Any] = {
        "ok": True,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "timezone": "Europe/Istanbul",
    }
    line_filters = {line.strip().upper() for line in args.line if line.strip()}
    bus_line_filters = {line.strip().upper() for line in args.bus_line if line.strip()}

    if not args.skip_traffic:
        output["traffic_index"] = safe_check(
            "traffic_index", lambda: traffic_index(args.timeout), errors
        )
    if not args.skip_road_alerts:
        output["road_announcements"] = safe_check(
            "road_announcements", lambda: road_announcements(args.timeout), errors
        )
    if not args.skip_metro:
        output["metro_status"] = safe_check(
            "metro_status", lambda: metro_status(args.timeout, line_filters), errors
        )
    if args.include_fares:
        output["metro_fares"] = safe_check(
            "metro_fares", lambda: metro_fares(args.timeout), errors
        )
    if bus_line_filters and not args.skip_iett:
        output["iett"] = {
            "alerts": safe_check(
                "iett_alerts", lambda: iett_alerts(bus_line_filters, args.timeout), errors
            ),
            "live_vehicles": safe_check(
                "iett_live_vehicles",
                lambda: iett_vehicle_positions(bus_line_filters, args.timeout),
                errors,
            ),
        }
    if not args.skip_feeds:
        output["feed_metadata"] = {
            "iett_gtfs": safe_check(
                "iett_gtfs", lambda: package_metadata("iett-gtfs-verisi", args.timeout), errors
            ),
            "multi_operator_historical_gtfs": safe_check(
                "public_transport_gtfs",
                lambda: package_metadata("public-transport-gtfs-data", args.timeout),
                errors,
            ),
        }
    output["errors"] = errors
    output["ok"] = not errors
    output["integrity_note"] = (
        "No paid key was used. Missing/failed endpoints remain explicit; no route or ETA is inferred from these signals alone."
    )
    print(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=None if args.compact else 2,
            separators=(",", ":") if args.compact else None,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(json.dumps({"ok": False, "error": "Interrupted"}), file=sys.stderr)
        raise SystemExit(130)
