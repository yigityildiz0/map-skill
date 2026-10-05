# Route Normalization, Scoring, Timing, and Scheduling

## Canonical candidate schema

Collect provider results into this minimal shape before scoring:

```json
{
  "profile": "balanced",
  "routes": [
    {
      "id": "candidate-1",
      "provider": "official-operator",
      "providers": ["official-operator", "google"],
      "observed_at": "2026-08-01T07:55:00+03:00",
      "line_sequence": ["M2", "M6"],
      "duration_min": 48,
      "planning_upper_min": 58,
      "walk_min": 11,
      "transfers": 1,
      "cost": 0,
      "reliability": 0.8,
      "source_confidence": 0.9,
      "bus_share": 0.0,
      "weather_exposure_min": 8,
      "comfort": 0.7,
      "scenic": null,
      "cancelled": false,
      "infeasible": false,
      "closing_violation": false,
      "accessibility_violation": false,
      "hard_failures": []
    }
  ]
}
```

Numbers such as reliability, comfort, or scenic values require defined evidence. Omit the field when no defensible measurement exists. Never let the model invent a 0–1 value from prose.

Keep provenance separately:

```text
engine and version
source URL
retrieved_at / provider observed_at
timezone and GTFS service_date
static feed URL, retrieved_at, hash, feed validity
realtime feed header timestamp and retrieved_at
prediction_source = direct_rt | propagated_rt | schedule | unknown
```

## Retrieve alternatives

For each accessible provider, inspect all practical alternatives it exposes at the requested time. Do not stop at the first card. Keep candidates that differ materially by line sequence, transfers, walking, duration, reliability, or mode.

Generated deep links are not provider results. A candidate needs an observed route result, an official schedule/alert, or a locally executed route engine response.

## Deduplicate without losing disagreement

Group routes by normalized material sequence: modes, route/line IDs, transfer stations, and direction. Preserve provider values and compute a provider duration range. Do not merge routes merely because their total duration is similar.

Run:

```powershell
python scripts/route_toolkit.py score --input routes.json --profile balanced
```

## Hard constraints first

Reject before ranking when any is true:

- service is inactive on the GTFS service date;
- official cancellation, no-service alert, or closed station/road invalidates the route;
- conservative arrival misses a mandatory appointment or opening window;
- a transfer margin is negative after minimum transfer and uncertainty;
- an explicit accessibility or mode constraint is violated;
- a required stop cannot be reached while open.

Unknown data is not automatically a hard failure. Preserve the candidate with lower confidence unless the user’s hard requirement cannot be verified.

## Scoring method

The helper maps available metrics within the candidate set to 0–1 loss and computes:

```text
score = 100 × (1 − weighted_loss / available_weight)
```

Missing soft metrics are removed and the remaining weights renormalized. Higher score is better. These are decision heuristics, not a transport standard.

| Metric | Balanced | Urgent | Comfortable | Leisure | Rail-first |
|---|---:|---:|---:|---:|---:|
| Duration | .30 | .38 | .18 | .15 | .25 |
| Reliability loss | .25 | .32 | .22 | .20 | .25 |
| Transfers | .12 | .12 | .20 | .10 | .12 |
| Walking | .08 | .04 | .15 | .08 | .08 |
| Cost | .08 | .02 | .05 | .05 | .05 |
| Weather exposure | .07 | .04 | .10 | .10 | .05 |
| Bus share | .05 | .08 | — | — | .20 |
| Comfort loss | .05 | — | .10 | .10 | — |
| Scenic loss | — | — | — | .22 | — |

Transit priority belongs mainly in candidate generation: transit plus walking is the default set. Rail-first penalizes bus dependence only after valid transit candidates exist.

If top scores are within five points, expose both when their trade-offs differ. If small reasonable weight changes change the winner, label the preference as sensitive rather than declaring one objectively best.

## ETA synthesis

Use official direct realtime first, then current operator schedule/status, then provider predictions, then static schedule. Third-party planners may share upstream data; do not treat three matching values as three independent confirmations.

Compare predictions only for the same canonical route, endpoints, direction, and departure/arrival window. Do not take the median of different line sequences and call it one route ETA.

The helper accepts:

```json
{
  "context": {
    "mode": "transit",
    "risk_level": 0.5,
    "bus_share": 0.4,
    "disruption": false,
    "severe_weather": false
  },
  "predictions": [
    {"provider": "google", "minutes": 52, "observed_at": "2026-08-01T07:50:00+03:00"},
    {"provider": "yandex", "minutes": 58, "observed_at": "2026-08-01T07:51:00+03:00"}
  ]
}
```

Run:

```powershell
python scripts/route_toolkit.py compare --input predictions.json
```

Its planning range is explicitly a conservative heuristic. Do not call it a confidence interval or promise. If historical `actual_minutes` samples are supplied, report sample count, mean error, MAE, and MAPE. Never report a provider error rate without actual outcome pairs.

## Confidence model

Use ordinal axes:

| Axis | High evidence example | Low/unknown example |
|---|---|---|
| data | active official feed within service date | stale feed, unknown coverage |
| timing | direct fresh realtime and generous transfer | static only, stale/missing RT, tight transfer |
| visit | first-party hours and feasible window | unparsed or old hours |
| endpoint | healthy self-host/official endpoint | public demo with no SLA or failed page |

Overall confidence is the minimum critical axis, not an average. Values: `high`, `medium`, `low`, `unknown`.

Useful reason codes:

```text
GEOCODE_AMBIGUOUS
STATIC_OUT_OF_RANGE
GTFS_FREQUENCY_BASED
RT_MISSING
RT_STALE
ALERT_STALE
TRANSFER_TIGHT
OPENING_UNKNOWN
WEATHER_LONG_HORIZON
PUBLIC_DEMO_NO_SLA
PROVIDER_UNAVAILABLE
```

For GTFS-Realtime, ideal TripUpdate/VehiclePosition age is at most 90 seconds and alert age at most 10 minutes. A publisher may have different cadence; always show actual timestamps. Missing `uncertainty` means unknown, not zero. Publisher uncertainty is not automatically p95 or a confidence interval.

## Transfer feasibility

Use conservative bounds:

```text
margin = next_departure_lower
       − prior_arrival_upper
       − minimum_transfer_time
       − required_station_path_time
```

Negative margin is infeasible. A small positive margin lowers confidence. Include platform changes, accessibility paths, ticket gates, luggage, and venue entrance time when relevant.

## Multi-stop optimization

Input to the exact local helper:

```json
{
  "start_id": "A",
  "end_id": "Z",
  "depart_at": "2026-08-01T10:00:00+03:00",
  "fixed_order": false,
  "top_n": 3,
  "stops": [
    {"id": "B", "open": "2026-08-01T10:30:00+03:00", "close": "2026-08-01T13:00:00+03:00", "dwell_min": 30}
  ],
  "matrix": {
    "A": {"B": 25, "Z": 60},
    "B": {"Z": 35}
  }
}
```

Run `python scripts/route_toolkit.py optimize --input day-plan.json`.

The helper tests all permutations only up to eight stops. The supplied matrix must reflect each leg’s realistic departure period. Road-only OSRM/Valhalla optimization does not solve a time-dependent transit problem. For separate appointments, plan each leg independently and enforce:

```text
previous conservative arrival + dwell + buffer <= next feasible departure
```

## Opening hours, weather, and fares

- Opening hours: prefer the venue’s first-party page; cross-check current map/OSM data. Parse OSM `opening_hours` formally, including holidays, timezone, overnight rules, and exceptions. State `open`, `closed`, `unknown`, `missing`, or `invalid`.
- Weather: sample origin, exposed transfers, and destination at the matching hour. Use rain, snow, wind/gust, heat/cold, and visibility only where they affect walking/waiting or service. Forecast is not a guarantee.
- Fare: use the exact current network/rider rule. Separate schedule fare coverage from unknown legs. Never infer a companion or rider category.

## Capability contracts

The names requested by the user are capability contracts, not proof that proprietary APIs are installed:

| Contract | Implementation |
|---|---|
| `geocode_place` | `map_link_resolver.py` for explicit coordinates in supported URLs; official place pages or optional self-host geocoder for names. No automatic public Nominatim. |
| `resolve_ambiguous_place` | Present up to three exact candidates and wait. |
| `get_google_routes`, `get_google_route_matrix` | Accessible product/browser results or configured paid Routes API only. |
| `get_yandex_routes`, `get_yandex_route_matrix` | Accessible product results or separately configured commercial API only. |
| `get_moovit_trip_plans` | Accessible app/web result or licensed API only. |
| `get_transit_disruptions` | Official operator alerts/status, GTFS-RT alerts, and current civic closures. |
| `get_weather_along_route` | `route_toolkit.py weather` with verified coordinates and terms. |
| `get_place_opening_hours` | First-party page, current map listing, or formally parsed OSM field. |
| `normalize_routes`, `score_routes` | `route_toolkit.py score`. |
| `optimize_multi_stop_day` | `route_toolkit.py optimize` using a real matrix. |
| `generate_navigation_links` | `route_toolkit.py links`. |
| `compare_predictions` | `route_toolkit.py compare`. |
| `save_trip_preferences` | `route_toolkit.py preferences`, explicit write consent required. |

If a proprietary contract lacks credentials or accessible output, return `no_data` for that adapter and continue with available evidence.
