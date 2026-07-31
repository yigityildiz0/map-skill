# Open Data and Self-Hosted Routing Stack

Verified against primary documentation on 2026-07-31. This reference separates what works with no paid API key from what still needs local infrastructure, account credentials, or provider permission.

## Recommended architecture

```text
User/map pin
  → exact place resolution
  → regional OSM + active GTFS schedule
  → optional GTFS-Realtime/operator live adapters
  → OpenTripPlanner candidate routes
  → official disruption/traffic/weather/opening/fare checks
  → local normalization, hard filters, scoring, ETA range
  → provider navigation links
```

“Free software/no paid API” does not mean zero setup: a local route engine needs regional data, Java, RAM/disk, feed refresh, validation, and monitoring. Do not install or start a local service unless the user asks for that infrastructure change.

## Geocoding and OpenStreetMap policy

The public `nominatim.openstreetmap.org` service must not be embedded as a generic automatic geocoder for this skill. Its current policy explicitly restricts systematic use by LLM/no-code/vibe platforms and requires at most 1 request/second, identifying User-Agent/Referer, caching, attribution, and the ability to switch providers. Source: [Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/).

Use this order:

1. coordinates or map pin supplied by the user;
2. shared-link redirect/metadata;
3. official venue/operator page and accessible human-facing map search;
4. an already configured geocoder;
5. optional self-host Nominatim/Pelias/Photon for automated scale.

Reverse geocoding returns the nearest suitable OSM object and can choose the wrong street/entrance in dense areas; cross-check branch and entrance. Source: [Nominatim reverse API](https://nominatim.org/release-docs/latest/api/Reverse/).

OpenStreetMap data is ODbL. Display attribution to OpenStreetMap contributors. Source: [OSMF attribution guidance](https://osmfoundation.org/wiki/Licence/Attribution_Guidelines).

Public Overpass is acceptable only for bounded, low-volume, human-triggered lookups with a small bounding box, cache, backoff on 429/504, deduplication, and `osm_base` timestamp capture. Do not use it as a production backend or query the world. Sources: [Overpass public resource guidance](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html), [Overpass QL](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL).

## GTFS Schedule correctness

Use an official active feed where possible. Store source URL, retrieval time, content hash, declared licence, `feed_start_date`, and `feed_end_date`. Validate before routing.

Mandatory rules:

- apply both additions and removals in `calendar_dates.txt`;
- reject dates outside feed validity instead of silently repeating a weekly calendar;
- parse times beyond 24:00 such as `25:35:00` against the GTFS service date;
- treat `frequencies.exact_times=0` as headway service, not exact minute departures;
- use `transfers.min_transfer_time`, pathways/traversal time, and accessibility fields;
- scope route/trip/stop IDs to the feed/agency rather than assuming global uniqueness;
- do not assume a shape exists; join an official route geometry source or clearly use straight/unknown geometry.

Source: [GTFS Schedule Reference](https://gtfs.org/documentation/schedule/reference/).

The [Mobility Database catalogs](https://github.com/MobilityData/mobility-database-catalogs) can help discover feeds, but catalog metadata is not proof that an individual feed is current, authorized, or correctly licensed. Verify the agency source.

## GTFS-Realtime correctness

GTFS-Realtime can supply TripUpdates, VehiclePositions, and Alerts. Absence of a TripUpdate means no realtime prediction, not “on time.”

Guardrails:

- ideal TripUpdate/VehiclePosition age: at most 90 seconds;
- ideal Alerts age: at most 10 minutes;
- preserve feed header timestamp and retrieval time;
- `uncertainty=0` means publisher-reported zero; a missing field means unknown;
- do not translate publisher uncertainty into p95 or a probability without a documented model;
- respect cancellation, `NO_DATA`, skipped stops, new/duplicated trips, and FULL_DATASET replacement semantics;
- do not assume DIFFERENTIAL support;
- distinguish direct realtime from values propagated by a route engine when possible.

Sources: [GTFS-Realtime reference](https://gtfs.org/documentation/realtime/reference/), [Trip Updates](https://gtfs.org/documentation/realtime/feed-entities/trip-updates/), [Realtime Best Practices](https://gtfs.org/documentation/realtime/realtime-best-practices/).

## OpenTripPlanner

For a no-paid-key local multimodal engine, prefer self-host [OpenTripPlanner 2.9](https://docs.opentripplanner.org/en/v2.9.0/) with a bounded regional OSM extract, current GTFS feeds, and available realtime updaters. OTP 2.9.0 was released 2026-03-18 and requires Java 25. Pin the exact version.

OTP no longer offers the old REST planning API. Use the local GTFS GraphQL endpoint:

```text
http://localhost:8080/otp/gtfs/v1
```

Sources: [OTP APIs](https://docs.opentripplanner.org/en/v2.9.0/apis/Apis/), [GTFS GraphQL API](https://docs.opentripplanner.org/en/v2.9.0/apis/GTFS-GraphQL-API/), [GTFS-RT configuration](https://docs.opentripplanner.org/en/v2.9.0/GTFS-RT-Config/).

`planConnection` accepts `earliestDeparture` or `latestArrival`, not both. Ordered `via` locations and `minimumWaitTime` support one continuous trip. Independent appointments should be separate leg queries. Source: [planConnection](https://docs.opentripplanner.org/api/dev-2.x/graphql-gtfs/queries/planConnection).

The linked schema page is for a development branch; introspect the running server and pin queries/tests to the installed OTP version.

## Other routing engines

| Engine | Good for | Do not assume |
|---|---|---|
| OSRM | self-host road routing, tables, matching; small public-demo tests | transit, SLA, current demo data, commercial use |
| Valhalla | self-host multimodal OSM+GTFS; road optimization | that the public demo includes regional transit |
| GraphHopper OSS | self-host OSM+GTFS transit | that hosted API works without a key |

OSRM’s public demo is limited to roughly 1 request/second, non-commercial use, and no SLA; its Trip service is heuristic and not a guaranteed optimum. Sources: [OSRM API](https://project-osrm.org/docs/v26.4.0/api/), [demo policy](https://github.com/Project-OSRM/osrm-backend/wiki/Demo-server).

Valhalla can use OSM and GTFS when self-hosted, but its optimized route endpoint applies to auto/bike/pedestrian, not a time-dependent public-transit day. Sources: [Valhalla APIs](https://valhalla.github.io/valhalla/api/), [optimized route](https://valhalla.github.io/valhalla/api/optimized/api-reference/).

GraphHopper hosted requests require an API key even on its free account plan; it does not meet zero-user-setup. Sources: [GraphHopper API start](https://docs.graphhopper.com/openapi/section/explore-our-apis/get-started), [GraphHopper OSS](https://github.com/graphhopper/graphhopper).

## Weather

The bundled helper uses [Open-Meteo Forecast API](https://open-meteo.com/en/docs/) for personal/non-commercial trips with verified coordinates. It samples up to eight route points for rain, snow, wind, and gust at the requested hour.

The no-key free endpoint is non-commercial, has no SLA, requires attribution, and currently publishes limits including 10,000 calls/day. Coordinate requests may be logged. Sources: [Open-Meteo terms](https://open-meteo.com/en/terms), [licence](https://open-meteo.com/en/licence).

For another deployment, review terms or use a configured/self-hosted weather source. A no-key alternative is [MET Norway Locationforecast](https://docs.api.met.no/doc/locationforecast/HowTO.html), but it requires an identifying contact-bearing User-Agent, caching/conditional requests, coordinate rounding, and attribution.

## Opening hours

Prefer a current first-party venue page. OSM `opening_hours` must be evaluated by a conforming parser, not freehand language-model interpretation. Account for public holidays, timezone, overnight intervals, conditional clauses, and last entry. Store one of `open`, `closed`, `unknown`, `missing`, `invalid`. Source: [opening_hours specification](https://wiki.openstreetmap.org/wiki/Key:opening_hours/specification).

## Cache and failure policy

Suggested starting points, overridden by publisher instructions:

- static GTFS/route geometry: check daily; rebuild only on change and retain hash/version;
- provider route observations: do not reuse for another departure window without requery;
- direct vehicle/arrival data: tens of seconds, never beyond its own timestamp/cadence;
- service alerts: 1–2 minutes for an active query;
- live traffic: 30–60 seconds;
- weather: honor provider cache headers/horizon;
- opening hours: cache briefly but recheck before a tight closing-time plan.

On rate limit, timeout, stale feed, schema drift, or authentication failure: record `no_data`, retain the last known value only as explicitly stale context, and continue with lower confidence. Never bypass authentication, scrape protected endpoints, or fan out exact private locations without consent.
