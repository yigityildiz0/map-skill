# Intake and Compact Output Contract

## Required trip fields

Do not begin route calculation until the current time block has:

| Field | Accepted examples | Rule |
|---|---|---|
| Origin | address, landmark, coordinates, map link, “current location” | If current location is inaccessible, ask for an origin. |
| Destination | exact branch/entrance, coordinates, map link | Resolve ambiguity before routing. |
| Date | today, tomorrow, an explicit date | Interpret in the trip locality and state the resolved date if relative. |
| Time | “08:15’te çıkacağım” or “09:00’da orada olacağım” | Preserve depart-versus-arrive meaning. |

For an intermediate visit followed by a deadline, dwell duration or latest leave time is conditionally required. Never invent “about 30 minutes” for “uğrayacağım.”

Ask one compact question listing only missing essentials. Examples:

- `📍 Nereden çıkacaksın ve hangi gün/saatte hareket edeceksin?`
- `⏰ 09:00 çıkış saati mi, hedefte olman gereken saat mi?`
- `📍 Hangi “Akasya”yı kastediyorsun: AVM, durak, yoksa başka bir şube?`
- `⏱️ Galataport’ta ne kadar kalacaksın; 21:00 Kadıköy’e varış saati mi?`

A broad district such as “Kadıköy” or “Çankaya” is not a precise endpoint for ETA/navigation. If it could change the route, ask for the exact square, stop, address, entrance, or pin together with the missing date/time; do not create a second clarification round unnecessarily.

Do not request a mode when it is absent: use transit plus walking. Do not request an intent profile when absent: use balanced and offer useful alternatives.

When depart/arrive semantics or visit duration affects feasibility, ask before routing. A stated assumption is not an adequate substitute.

## Normalize the request

Create one record per time block:

```text
block_id
timezone
origin / destination
ordered_stops[]
reorder_allowed
depart_at XOR arrive_by
dwell_minutes[]
mode = transit | driving | bicycling | walking
profile = balanced | urgent | comfortable | leisure | rail-first | low-transfer
constraints[]
rider_profile
companions[]
```

Treat morning and evening plans, appointments, and long visits as separate blocks. A continuous sequence such as A → B → C can have one multi-stop link where supported. A morning appointment followed by an evening outing needs separate links because a navigation deep link cannot preserve two independent clocks.

## Interpret indirect preferences

| Wording or situation | Profile/constraint |
|---|---|
| work, school, internship, exam, flight, doctor, “yetiş” | urgent; arrive conservatively |
| “en hızlı”, “çok kısa sürede” | urgent |
| “rahat”, luggage, child, little walking | comfortable |
| “az aktarma” | low-transfer |
| “çoğunlukla metro”, “otobüse az bineyim” | rail-first |
| “sadece metro” | reject candidates with non-metro motorized legs |
| sightseeing, scenic, relaxed, “gezeceğim” | leisure |
| nothing relevant | balanced |

Do not label a route safe, scenic, comfortable, or accessible without evidence. “Leisure” may include a verified on-route point only if it is open and causes a small, disclosed detour.

## Place ambiguity

When multiple branches or localities remain plausible:

1. show at most three candidates;
2. include district/city and a distinguishing detail;
3. ask for one selection;
4. do not route in the meantime.

If a map link resolves to a coordinate but the label conflicts, keep both, state the conflict, and ask when it could change the entrance or destination.

## Response budget

Perform deep analysis internally, but normally return:

- one recommended route;
- at most two materially different alternatives;
- one compact warning line;
- one cost line only when verified and useful;
- supported navigation links;
- evidence time and confidence.

Avoid provider-by-provider research dumps, repeated caveats, raw JSON, and alternatives that differ only by one or two minutes.

## Default Turkish answer

```text
✅ Önerilen — 08:05’te çık
M2 → aktarma → M6 → 8 dk yürü | 42–55 dk | 1 aktarma
🎯 Tahmini varış: 08:47–09:00 | 10 dk güven payı | Güven: Orta
⚠️ M7’de kısmi işletme var; seçilen rota M7 kullanmıyor. 09:00 civarı yağmur olası.
💳 Sen: 2 abonman kullanımı veya yaklaşık … TL (tarife 07:55’te kontrol edildi)
🔗 Google · Yandex · Moovit

⚡ Daha hızlı: …
😌 Daha az aktarma: …
Kaynak kontrolü: 07:55, Europe/Istanbul
```

Whenever the answer contains a current ETA, alert, weather, opening, fare, or timetable claim, include the actual source-check time. Do not label an old schedule page as a live check.

Only include lines that add value. Keep logical emojis; do not decorate every phrase.

## Urgent arrival format

```text
⏰ En geç 07:50’de çık.
✅ Plan: … | normal tahmin 48 dk; planlama aralığı 48–65 dk
🎯 08:55 hedefi için 15 dk güven payı var.
⚠️ Canlı otobüs verisi yoksa: “Otobüs kısmı tarifeye dayalı; çıkmadan 10 dk önce yeniden kontrol et.”
🔗 …
```

Do not subtract the median alone from the deadline. Use the conservative upper estimate plus station entry, walking, transfer, and venue-entry time.

## Multi-stop format

```text
1️⃣ Sabah — A → B | çıkış … | varış … | 🔗 …
2️⃣ Akşam — B → C → D | çıkış … | toplam … | 🔗 …
⚠️ C, 19:00’da kapanıyor; mevcut planda yetişmiyor. En geç 17:40’ta B’den çık veya C’yi öne al.
```

Do not claim that a single link contains separate visit durations or appointment times. When the provider omits those fields, the text plan is authoritative and the link is only navigation.

## Fares and companions

- Default: user only.
- If the user says “yanımda biri var,” determine only the missing fare class needed for the total.
- List each person once, then the trip total.
- Separate pass/abonman usage from pay-as-you-go currency.
- Do not approximate pass/abonman limits or charges. If the exact current rule for every leg is not verified, say `abonman kullanımı doğrulanamadı` or omit the cost line.
- Never multiply a base fare when the route includes distance fares, refunds, transfer discounts, special routes, ferries, night service, Marmaray, or Metrobüs without verifying their current rules.
- If current fare evidence is unavailable, omit the total or mark it unknown; never use an old tariff as current.

## Unknowns and failures

Use specific wording:

- `Veri yok`: source was inaccessible or does not cover the area/mode.
- `Rota yok`: a functioning provider explicitly returned no route.
- `Canlı veri yok`: only schedule/static data is available.
- `Güven düşük`: state the single most important reason and when to recheck.

Never hide a failed source by replacing it with a precise-looking estimate.

Likewise, “a line did not appear in a disruption endpoint response” means only “no record was returned there.” Do not rewrite that as “the line is operating normally” unless an official source explicitly says so.
