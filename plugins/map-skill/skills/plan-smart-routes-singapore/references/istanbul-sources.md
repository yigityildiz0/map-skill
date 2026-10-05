# İstanbul Source Policy

Verified on 2026-07-31. İstanbul has useful official live services, but no verified public standard GTFS-Realtime protobuf feed covering the whole network. Label IETT SOAP/HTML data as IETT live data, never GTFS-RT.

## Priority order

For an İstanbul route:

1. exact line/operator service status and cancellation;
2. current official timetable and service-date validity;
3. direct vehicle/arrival signal when available;
4. route-specific road closure/traffic evidence;
5. Google/Yandex/Moovit and other planner alternatives;
6. weather, opening hours, fare, and event checks;
7. recheck selected lines and roads just before answering.

Prefer metro/rail over buses when duration and walking are comparable because road traffic increases uncertainty. A bus can still win when it materially reduces time/transfers or avoids a disrupted rail leg.

Use Yandex as an İstanbul road-traffic/driving sanity check because the user explicitly prefers it, but do not let it override official operator notices or assume Yandex transit coverage.

## Bounded live helper

```powershell
python scripts/istanbul_live.py --line M2 --line M7 --bus-line 34AS
```

Optional fare signal:

```powershell
python scripts/istanbul_live.py --line M2 --include-fares
```

The helper uses no paid key, returns source timestamps where available, preserves endpoint failures, and never infers a complete route or ETA from context signals.

## Official sources

| Signal | Official endpoint/page | Use | Limitation |
|---|---|---|---|
| Citywide traffic index | `https://api.ibb.gov.tr/tkmservices/api/TrafficData/v1/TrafficIndexHistory/1/5M` | Current congestion context | Not a route-segment duration |
| Current road announcements | `https://tkmservices.ibb.gov.tr/web/api/IntensityMap/v1/CurrentAnnouncement` | Current works, incidents, partial/full closures with coordinates | Official live-map endpoint without a stable published schema; spatially match route |
| Live traffic map | `https://uym.ibb.gov.tr/yharita6/` | Visual route-area validation | Manual/current view |
| Traffic segments | `https://tkmservices.ibb.gov.tr/web/api/TrafficData/v4/SegmentData` plus segment geometry | Route-level traffic only after segment/geometric matching | Large, abbreviated undocumented fields; do not download blindly per query |
| Metro line status | `https://api.ibb.gov.tr/MetroIstanbul/api/MetroMobile/V2/GetServiceStatuses` | Exact line disruption | Read description and update time; `IsActive` does not mean healthy |
| Metro OpenAPI | `https://api.ibb.gov.tr/MetroIstanbul/swagger/v1/swagger.json` | Lines, stations, directions, timetables, fares | Endpoint behavior can change |
| Metro fares | `https://api.ibb.gov.tr/MetroIstanbul/api/MetroMobile/V2/GetTicketPrice/TR` | Current Metro İstanbul price signal | Not all-network total; verify transfers/special modes |
| IETT alerts | `https://api.ibb.gov.tr/iett/UlasimDinamikVeri/Duyurular.asmx?wsdl` | Cancelled/changed bus service | SOAP JSON result is nested text; some records have only record time/message |
| IETT live line vehicles | `https://api.ibb.gov.tr/iett/FiloDurum/SeferGerceklesme.asmx?wsdl`, `GetHatOtoKonum_json` | Current vehicle positions for an exact line | Not GTFS-RT and not a passenger ETA; method/schema can change |
| IETT planned departures | `https://api.ibb.gov.tr/iett/UlasimAnaVeri/PlanlananSeferSaati.asmx?wsdl` | Planned times for exact line | Schedule only; day-type codes need correct interpretation |
| IETT stop ETA | `https://iett.istanbul/tr/RouteStation/GetStationInfo?dcode={stop}&langid=1` | Current stop-page estimate when available | Undocumented site endpoint; medium confidence and schema drift risk |
| İETT static GTFS | `https://data.ibb.gov.tr/api/3/action/package_show?id=iett-gtfs-verisi` | Current static bus schedule baseline | Not realtime; current package lacks `shapes.txt` |
| IETT stops/routes | [stops GeoJSON](https://data.ibb.gov.tr/dataset/iett-otobus-duraklari-verisi), [route GeoJSON](https://data.ibb.gov.tr/dataset/iett-hat-guzergahlari) | Geometry missing from GTFS | Route file is large; cache/version it |
| Şehir Hatları | [timetable](https://sehirhatlari.istanbul/tr/seferler), [cancellations](https://sehirhatlari.istanbul/tr/iptal-seferler), [announcements](https://sehirhatlari.istanbul/tr/duyurular) | Ferry schedule and current cancellation | No verified public live vessel API |
| Marmaray | [daily timetable](https://www.tcddtasimacilik.gov.tr/marmaray/tr/gunluk_tren_saatleri), [trip planner](https://www.tcddtasimacilik.gov.tr/marmaray/tr/neredennereye), [last minute](https://www.tcddtasimacilik.gov.tr/marmaray/tr/son_dakika) | Official schedule/status | Embedded private/basic credentials must not be copied; no verified open realtime train feed |
| Weather | [MGM İstanbul](https://mgm.gov.tr/?il=Istanbul), [MGM warnings](https://www.mgm.gov.tr/meteouyari/turkiye.aspx?Gun=1), [AKOM](https://akom.ibb.istanbul/) | Official severe weather/current civic context | Some internal JSON endpoints are undocumented; prefer user pages |
| Planned event closures | [İstanbul Valiliği announcements](https://www.istanbul.gov.tr/basin-aciklamalari) | Match, ceremony, demonstration and planned road/transit measures | Human-readable; search exact date/place |

The IETT alert and line-vehicle SOAP operations were tested without credentials on 2026-07-31. Their WSDL may expose authentication structures for other methods; treat any future authentication error as `no_data`, never bypass it.

## Data that must not be used as current

- The IBB `public-transport-gtfs-data` multi-operator package explicitly says it will not be updated and contains 2018–2020-era operator data. It may describe historical structure only, never a current timetable.
- Historical UYM announcement CSVs are not live closures.
- Metro `GetAnnouncements/tr` returned old general content in testing; use line service status for operations.
- Do not copy internal Marmaray credentials or scrape protected APIs.

## İstanbul live-check sequence

1. Resolve exact stations, stops, ferry piers, directions, and line codes.
2. Query all candidate alternatives and keep every practical line sequence.
3. Check Metro line status, IETT alerts/live vehicles for selected bus lines, Şehir Hatları cancellations, Marmaray official pages, and UYM current closures.
   - If a requested Metro line is absent from the status payload, report only that no record was returned; absence is not an explicit healthy-state confirmation.
4. Use the citywide traffic index only to increase caution for road-heavy legs; use actual route segment/provider traffic for duration.
5. Search the exact date and corridor for events, matches, weather alerts, and planned changes.
6. Rank candidates.
7. Recheck the chosen lines and roads; show observation time and whether each important leg is live, schedule-only, or unknown.

## Fare policy

The Metro fare endpoint is a signal, not an all-network calculator. Verify current İstanbulkart/transfer/refund, distance-based Marmaray and Metrobüs, ferry, special-line, night-service, student, and pass rules from the responsible operator before totaling. Show only the user by default; add companions only when stated.

Never estimate abonman limits by counting vehicles or gates. If the exact current charging rule across the route is not verified, omit the number or state that abonman usage could not be verified.

## Licensing and load

IBB CKAN packages use the [IBB Open Data Licence](https://data.ibb.gov.tr/license) and require attribution. Live-map, operator, MGM, and Valilik pages may not share the CKAN licence; summarize and link rather than redistributing bulk data. Cache static feeds and avoid aggressive polling of undocumented endpoints.
