# Accuracy, uncertainty, privacy, and safety

## No false precision

The answer should say `42–55 min`, not “exactly 47 minutes.” A planning range is widened when:

- providers disagree;
- predictions are stale or schedule-only;
- buses dominate a congested corridor;
- a transfer is tight or has long station traversal;
- an event, closure, snow, heavy rain, wind, or disruption affects the route;
- local realtime coverage is partial.

For an arrive-by trip, leave time is based on the conservative upper duration plus station/entrance walk and a separate safety buffer.

## Freshness rules

Publisher instructions override these starting points:

| Signal | Practical freshness handling |
|---|---|
| Vehicle/arrival | Keep payload timestamp; tens of seconds to roughly 90 seconds is typical, never assume. |
| Alerts/status | Recheck immediately before the answer and again near departure for consequential trips. |
| Traffic | Route-specific evidence; approximately 30–60 second caching unless the publisher says otherwise. |
| Static GTFS | Store retrieval date/hash and validate `feed_info`, calendars, exceptions, and service date. |
| Weather | Sample origin, exposed transfers, and destination near travel time; preserve forecast uncertainty. |
| Opening hours | Prefer first-party page; check timezone, holiday, last-entry, and overnight intervals. |

Absence of a realtime entity is not “on time.” Absence of an alert is not proof that no problem exists.

## Traffic and İstanbul

A citywide congestion index can raise caution but cannot produce a segment ETA. Road-heavy routes need corridor evidence and provider estimates. In İstanbul, the enhanced skill:

1. resolves exact lines/stops/directions;
2. checks IETT/Metro/Şehir Hatları/Marmaray status where applicable;
3. checks IBB current announcements and route-level traffic evidence;
4. uses Yandex as a strong local comparison signal, not a single source of truth;
5. checks date/corridor events and severe weather;
6. ranks candidates, then rechecks the winner.

## Accessibility and personal safety

Do not label a route wheelchair-accessible, safe, scenic, or comfortable without current evidence. Accessibility failures are hard constraints. For late-night or unfamiliar areas, use official station/operator accessibility and closure sources and phrase residual uncertainty plainly.

## Fare integrity

Do not multiply a base fare across legs without checking transfer discounts, caps, refunds, zone/distance rules, special services, ferries, airport supplements, night fares, concessions, or pass rules. Default to the user only; include companions only when the request mentions them.

## Privacy

- Use the minimum providers needed for exact private locations.
- Do not persist one-off trips.
- Writing preferences requires explicit consent.
- Home/work labels or coordinates require an additional sensitive-data opt-in.
- Never commit routes, API keys, account tokens, or private coordinates.

## Pre-departure rule

For work, school, exams, flights, healthcare, appointments, or another hard deadline, the answer should include a recheck action. No software can guarantee service, traffic, weather, or venue access.
