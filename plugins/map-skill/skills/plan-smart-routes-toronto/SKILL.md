---
name: plan-smart-routes-toronto
description: Plan and compare reliable Toronto trips with public transport plus walking by default, official local transit and traffic checks, weather, opening hours, fares, multi-stop scheduling, ETA uncertainty, and valid navigation links. Use for any route, ETA, arrival/departure, or multi-stop request whose origin, destination, or leg is in Toronto.
---

# Plan Smart Routes — Toronto

## City Edition

This edition specializes the universal workflow for **Toronto (Toronto)**. Read `references/city-profile.json` for every in-scope trip. Use only sources whose access requirements are satisfied, preserve their coverage gaps, and fall back to the universal source plan outside the documented area.

## Mission

Return a compact trip plan backed by current evidence. Research broadly; answer briefly. Never present a generated map link, a static timetable, or an inaccessible provider as a live route result.

Reply in the user's language. Default to **public transport plus necessary walking**. Prefer rail/metro over road buses when reliability and total cost are otherwise comparable. Use driving, cycling, or walking-only only when requested or clearly implied.

This skill works without paid APIs. Optional provider APIs may improve results when the environment already has valid credentials, but never ask the user to buy access and never claim an API ran when it did not.

## Load Only the Needed References

- Read [intake-and-output.md](references/intake-and-output.md) for every trip.
- Read [route-synthesis.md](references/route-synthesis.md) when comparing, timing, scoring, costing, or scheduling routes.
- Read [provider-capabilities.md](references/provider-capabilities.md) before provider research or link generation.
- Read [tool-contracts.md](references/tool-contracts.md) before mapping requested capability names to available tools/scripts.
- Read [city-source-registry.json](references/city-source-registry.json) and the matching file under `references/cities/` when a supported city is involved.
- Read [open-data-stack.md](references/open-data-stack.md) for GTFS, GTFS-Realtime, OpenTripPlanner, OpenStreetMap, geocoding, or self-hosting questions.

## Workflow

### 1. Split the request into time blocks

Extract for each continuous block:

- origin, destination, ordered or reorderable intermediate stops;
- trip date and **depart at** versus **arrive by** semantics;
- mode and constraints: rail-first, few transfers, little walking, accessibility, luggage, bike, car;
- intent: urgent, balanced, comfortable, or leisure;
- dwell time, appointments, venue closing/last-entry time, companions, and fare/pass profile;
- map URLs, place names, coordinates, entrances, and locality.

A long visit, appointment, or jump from morning to evening starts a new block. Preserve the order of explicit stops unless the user permits reordering.

### 2. Ask once for missing essentials

Do not calculate a block until these are known:

1. origin;
2. destination;
3. date;
4. departure time or required arrival time.

“Now” supplies the local date and departure time. If device location is unavailable, ask for an exact origin or nearby landmark. If a stop is followed by a deadline, its dwell time or latest leave time is also essential. Do not invent visit duration.

Ask one short question containing only missing fields. If a place is ambiguous, show at most three concrete candidates. A broad district alone is not precise enough for a dependable ETA or navigation link; ask for a station, entrance, address, landmark, or pin when that distinction matters.

Do not ask for travel mode or intent when absent: use transit+walking and balanced ranking.

### 3. Resolve places before routing

Treat any shared Google, Yandex, Apple, Bing, HERE, Waze, Moovit, Citymapper, or OSM link as a location reference—not a command to use only that provider. Follow supported redirects, extract explicit coordinates/labels, and cross-check the same place or branch in other accessible products and first-party venue pages.

Prefer, in order: user coordinates/pin; resolved map link; official venue/operator page; accessible human-facing map search; an already configured geocoder. Do not silently substitute a similarly named branch or entrance.

Use the bounded resolver for supported URLs:

```powershell
python scripts/map_link_resolver.py "https://maps.app.goo.gl/..."
```

This resolves links; it is not generic place-name geocoding. Do not embed the public Nominatim service as an automated LLM geocoder.

### 4. Select the city profile and source plan

Match the trip to a profile in `references/city-source-registry.json`. A profile adds official local sources and limitations; it never replaces the universal workflow.

For every source distinguish:

- `no_key`: machine-readable and usable without credentials;
- `registration` or `api_key`: usable only when credentials are already configured;
- `web_only`: human-visible official check; do not scrape or claim machine retrieval;
- `self_hosted`: free software that still needs local infrastructure;
- `unavailable`: inaccessible or outside coverage.

Store source observation time, payload time when supplied, freshness, coverage, licence/attribution, and failure status. `no_data` is not `no_service`.

If no city profile matches, use official operator journey planners/status pages, accessible provider products, current web research, and the universal open-data rules. State that local realtime coverage is unknown or partial rather than downgrading silently.

### 5. Gather every practical candidate

Search all visible alternatives—not merely the first—across accessible Google Maps, Yandex Maps, Moovit, local operator planners, and relevant regional providers. Add HERE, Bing, Apple Maps, Waze, Citymapper, OpenStreetMap, or a local OpenTripPlanner only where mode and coverage fit.

For each candidate capture:

- provider/source URL and observation time;
- route/line/stop sequence and direction;
- scheduled and predicted duration/arrival;
- walking, wait, transfers, and exposed segments;
- service-date validity, accessibility, fare evidence, and alert state;
- realtime/static/unknown status and raw confidence factors.

Paid/keyed Google Routes, Yandex routing/matrix, and Moovit APIs are optional adapters. Without credentials, use accessible product pages, official transport data, and no-key deep links. Creating a deep link is never evidence that a route or ETA was retrieved.

### 6. Normalize, deduplicate, and hard-filter

Merge candidates with the same material line/stop sequence while preserving each provider prediction and source. Reject a candidate before scoring when it is cancelled, inactive on the service date, impossible under a stated accessibility need, outside an opening/deadline window, or contains an infeasible transfer.

```powershell
python scripts/route_toolkit.py score --input routes.json --profile balanced
```

Do not fill missing metrics with invented observations. Duration is a minimum evidence gate; other missing metrics remain explicit and receive only the documented conservative **scoring penalty**, with evidence completeness shown separately from route performance.

### 7. Check current conditions twice

Check once before scoring and recheck the selected route immediately before answering:

- exact line, station, stop, ferry, and transfer alerts;
- cancellations, short turns, frozen/changed service, replacement or extra event service;
- traffic, road closures, construction, demonstrations, matches, concerts, and large events;
- weather at origin, exposed transfers, and destination near travel time;
- opening hours, holidays, and last entry;
- current fares and rider rules only when relevant.

Official operator/current feeds outrank third-party planners. Realtime absence means “no realtime data,” not “on time.” For future trips outside the feed/forecast horizon, give a schedule-based plan and a precise recheck time.

For weather after coordinates are verified:

```powershell
python scripts/route_toolkit.py weather --point "51.5074,-0.1278|Origin" --point "51.5155,-0.0922|Destination" --at "2026-08-01T09:00:00+01:00"
```

### 8. Compare ETA evidence conservatively

Treat provider estimates as correlated observations, not independent votes. Prefer direct, fresh operator predictions and historical calibration where available. Compare recorded predictions with:

```powershell
python scripts/route_toolkit.py compare --input predictions.json
```

Report a planning range, explicit safety buffer, and confidence `high`, `medium`, `low`, or `unknown` with one short reason. Never promise exact arrival.

For urgent trips, work backward from the arrival deadline using a conservative upper duration plus entrance/walking, transfer uncertainty, event/traffic risk, and a safety buffer. A citywide traffic index is context only; it is not a segment-level bus ETA.

### 9. Optimize multi-stop plans honestly

For reorderable stops, first obtain a time-dependent travel matrix from actual candidates. Then run:

```powershell
python scripts/route_toolkit.py optimize --input day-plan.json
```

The helper explores at most eight supplied stops and never fetches or invents a matrix. Recompute each transit leg at its real departure time; a road-only TSP is not a public-transport day plan.

Warn with ⚠️ when a venue will be closed, a connection/window is infeasible, or the latest viable departure has passed. Suggest the smallest useful change.

### 10. Generate capability-aware links

Generate links only after selecting the route and resolving every point:

```powershell
python scripts/route_toolkit.py links --origin "51.5074,-0.1278|Origin" --waypoint "51.5133,-0.0890|Stop" --destination "51.5155,-0.0922|Destination" --mode transit --when "2026-08-01T09:00:00+01:00"
```

Return only providers whose documented link can encode the required points and mode and whose geographic coverage is plausible. Do not claim a link preserves time, waypoints, or exact line choice when its schema does not.

A continuous A→B→C block may use one multi-stop link where supported. Separate morning/evening blocks require separate links because a deep link cannot preserve independent appointment clocks.

### 11. Handle profile, fare, and companions narrowly

Infer without asking:

- **urgent**: work, school, internship, exam, flight, appointment, hard deadline;
- **comfortable**: little walking, few transfers, luggage, child, accessibility;
- **leisure**: sightseeing, scenic, relaxed, no deadline;
- **balanced**: otherwise.

When no preference is stated, return the recommendation plus at most two materially different alternatives such as ⚡ faster and 😌 fewer transfers.

By default calculate only the user's fare. Include companions only when mentioned. Separate pass/abonman usage from pay-as-you-go currency. Verify distance fares, refunds, caps, transfers, special services, ferries, night fares, and concession rules; otherwise omit the number rather than guessing.

### 12. Persist only with explicit consent

Reading local preferences is safe:

```powershell
python scripts/route_toolkit.py preferences show
```

Writing requires explicit consent and `--allow-write`. Exact home/work labels or coordinates require the additional `--allow-sensitive`. Never save a one-off route automatically.

## Compact Answer Contract

Normally return:

```text
✅ Recommended — leave 08:05
Metro A → transfer → Bus 24 → 7 min walk | 42–55 min | 1 transfer
🎯 Arrival 08:47–09:00 | 10 min buffer | Confidence: Medium
⚠️ One material alert/weather/opening issue, if any.
💳 User-only fare, only if verified.
🔗 Google · local planner · another truthful supported link

⚡ Faster: ...
😌 Fewer transfers: ...
Checked: 07:55 local time
```

Use the user's language and only include useful lines. Do not dump provider-by-provider research, raw JSON, or decorative emojis.

## Final Integrity Gate

Before answering, verify:

- all time blocks, stops, dwell times, timezones, and arrive/depart semantics survived;
- service runs on that date and selected-line alerts were rechecked;
- ETA has range, buffer, confidence, and source-check time;
- weather/opening/fare claims are current and sourced or omitted;
- each link encodes only what the text promises;
- missing credentials/coverage are reported as unavailable, never simulated;
- sensitive locations were minimized and not persisted;
- final output follows the compact contract.

When evidence is insufficient, state exactly what remains unknown and when/how to recheck. Honest uncertainty is better than false precision.
