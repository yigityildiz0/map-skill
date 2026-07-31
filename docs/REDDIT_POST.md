# Reddit publication copy

Target community: **r/LLMDevs**. The project is free, MIT-licensed, and directly related to LLM/agent workflow engineering. The post must disclose that the author built it and ask for technical feedback; do not cross-post repeatedly.

## Title

[Open Source] Map Skill — reliable route planning for ChatGPT/Codex with official transit checks and 16 city profiles

## Body

I built **Map Skill**, a free MIT-licensed skill/plugin for ChatGPT and Codex that tries to fix a problem I kept seeing in LLM route answers: confident but wrong ETAs, the first map result treated as truth, and deep links presented as if they contained timing or waypoint data they cannot actually encode.

When the host can access the relevant web/search/data sources, the workflow:

- defaults to public transport + necessary walking;
- asks once for missing origin, destination, date, and depart/arrive time;
- compares the practical alternatives it can actually observe instead of only provider result #1;
- checks official service status, traffic/closures/events, weather, opening hours, and relevant fares;
- hard-rejects cancelled or infeasible routes before scoring;
- reports an ETA range, safety buffer, confidence, and source-check time;
- generates Google/Yandex/Moovit/HERE/Bing/Apple/Waze/Citymapper/OSM links only for fields their documented link format supports.

There is a Universal skill, an enhanced İstanbul edition, and city profiles/standalone editions for London, Paris, Berlin, Dublin, Milan, Madrid, Tokyo, Seoul, Singapore, Hong Kong, Toronto, NYC, Chicago, Mexico City, and Sydney.

It does **not** bundle API keys or pretend Google/Yandex/Moovit enterprise APIs are free. Official sources are tagged as no-key, registration/key, web-only, or self-hosted, with licence and coverage caveats. Missing data stays `no_data`; it is never rewritten as “no service” or “on time.”

Repo + direct release downloads:

https://github.com/yigityildiz0/map-skill

Universal: https://github.com/yigityildiz0/map-skill/releases/latest/download/map-skill-universal.zip

Enhanced Istanbul: https://github.com/yigityildiz0/map-skill/releases/latest/download/map-skill-istanbul.zip

All-in-one plugin: https://github.com/yigityildiz0/map-skill/releases/latest/download/map-skill-plugin.zip

This is not a hosted router and it includes no provider API keys. Live research depends on the host's available browser/search/tools and each publisher's access terms.

I would especially value feedback on:

1. the route-scoring/uncertainty contract;
2. official city sources or licence caveats I missed;
3. useful regression cases for multi-stop and arrive-by planning.

I am the author; this is non-commercial and open source.
