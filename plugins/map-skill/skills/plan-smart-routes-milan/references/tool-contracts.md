# Capability and Tool Contracts

The names below describe workflow capabilities. They are not proof that a paid provider API, MCP tool, or browser session exists. Select the strongest available implementation at runtime and preserve failures explicitly.

## Availability states

Every adapter result must include one of:

- `ok`: current result was retrieved and parsed;
- `no_data`: provider was inaccessible, unsupported, stale, outside coverage, or missing credentials;
- `no_route`: a functioning route provider explicitly returned no route;
- `ambiguous`: place identity is unresolved;
- `invalid_input`: required fields are missing or contradictory.

Never translate `no_data` into `no_route` or “service is normal.”

## Requested capability map

| Capability | Free/default implementation | Optional stronger implementation | Integrity boundary |
|---|---|---|---|
| `geocode_place` | user pin/link, official venue page, accessible human-facing map search | configured geocoder or self-hosted Nominatim/Pelias/Photon | Do not embed public Nominatim for automated LLM use; verify branch/entrance. |
| `resolve_ambiguous_place` | show at most three locality-qualified candidates and ask | configured geocoder/place API | Do not route until ambiguity materially affecting the trip is resolved. |
| `get_google_routes` | inspect accessible Google Maps alternatives in the current browser/tool environment | Google Routes API with user-supplied credentials | A Google directions URL is not a retrieved route. |
| `get_google_route_matrix` | collect real leg estimates manually/provider-by-provider | Google Routes matrix with user-supplied credentials | Never synthesize a matrix from straight-line distance for transit. |
| `get_yandex_routes` | inspect accessible Yandex Maps alternatives | Yandex routing API with user-supplied credentials | Verify regional/transit coverage; deep link is not route evidence. |
| `get_yandex_route_matrix` | collect available Yandex leg observations | Yandex Distance Matrix with user-supplied credentials | Do not call without configured credentials or claim it ran. |
| `get_moovit_trip_plans` | inspect accessible Moovit product results | approved Moovit integration | Moovit app link supports only documented fields and coverage. |
| `get_transit_disruptions` | official city/operator feeds and passenger status pages from the city registry | configured GTFS-RT/SIRI/operator adapter | Absence from a feed is not proof of normal service. |
| `get_weather_along_route` | `route_toolkit.py weather` with verified coordinates | configured commercial/local weather source | Forecast is a risk signal, not a guarantee; respect terms/attribution. |
| `get_place_opening_hours` | first-party venue page and current web research | configured place API or conforming OSM `opening_hours` parser | Account for timezone, holidays, overnight hours, and last entry. |
| `normalize_routes` | `route_toolkit.py score` normalization stage | local routing service adapter | Preserve provider observations and provenance. |
| `score_routes` | `route_toolkit.py score` | locally calibrated weights/history | Hard failures are rejected before weighting; missing metrics are not invented. |
| `optimize_multi_stop_day` | `route_toolkit.py optimize` using a supplied time-dependent matrix | configured route-matrix/OTP adapter | Maximum eight stops; recompute transit legs at actual departure times. |
| `generate_navigation_links` | `route_toolkit.py links` | provider-specific signed/universal links | Report exactly which points, mode, waypoints, and time the link encodes. |
| `compare_predictions` | `route_toolkit.py compare` | operator-calibrated historical model | Provider predictions are correlated; output a range, buffer, and confidence. |
| `save_trip_preferences` | `route_toolkit.py preferences` | user-approved private preference store | Write only with explicit consent; sensitive places need additional opt-in. |

## Common adapter envelope

When a host exposes real tools, normalize their output to:

```json
{
  "capability": "get_transit_disruptions",
  "status": "ok",
  "provider": "official-operator",
  "coverage": "selected-line-and-stations",
  "observed_at": "2026-07-31T08:02:11+03:00",
  "payload_time": "2026-07-31T08:02:00+03:00",
  "freshness_seconds": 11,
  "data": {},
  "source_url": "https://official.example/status",
  "licence": "publisher terms",
  "warnings": []
}
```

Keep `observed_at` even if the publisher omits `payload_time`. Do not create a fake payload timestamp. Keep raw provider data out of the final answer unless the user requests technical details.

## Parallel research pattern

Run independent, bounded tracks when tools permit:

1. provider route alternatives;
2. official transit status and service-date validation;
3. traffic/events and weather;
4. opening hours and fares when relevant.

Join the tracks only after place identity and trip time are fixed. Recheck the selected route's official signals after scoring.
