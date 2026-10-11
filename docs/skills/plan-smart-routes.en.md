# plan-smart-routes

[English](plan-smart-routes.en.md) · [Türkçe](plan-smart-routes.tr.md) · [Library](../../README.md)

**Plan practical routes with mode choices, timing and honest live-data limits.**

## Try it

> Compare walking and transit options for this itinerary.

## Trigger and routing

The host matches the request against the skill description. Explicit selection by canonical name is available where supported. Typing /name in chat does not register a command.

<details>
<summary>Exact source description</summary>

Plans and compares time-aware trips with public transport plus walking by default: live traffic and service checks, weather, opening hours, fares, multi-stop scheduling, ETA uncertainty and map links (Google Maps, Yandex, Moovit, Apple Maps and others). Turkish triggers: buradan şuraya nasıl giderim, kaç dakikada varırım, hangi otobüs/metro, aktarma, yol tarifi, rota planla. More triggers: otobüs saati, metro, çok duraklı rota, trafik.

</details>

## How it works

Identify origin/destination and constraints; compare feasible modes; reconcile transfers and timing; distinguish live data from estimates.

The root entry point owns routing; only relevant modules and references are loaded. A bundled script is not an executed result. Work uses actual host tools, available input and the task scope.

## Inputs, outputs and verification

- Input: the example goal, relevant files/URLs/data, and constraints that change the result.
- Output: a task-appropriate answer, plan, draft or authorized file change with evidence and uncertainty.
- Verification: performed and suggested checks are separate; inaccessible sources and unexecuted tools are not counted as used.

## Runtime and boundaries

The package supplies no model weights, permissions, account or API credit. This edition uses existing host tools, open access and local computation; a separately billed service is not an automatic fallback. Clinical/investment outputs do not replace professional judgment or execute orders.

## Modules and source

[SKILL.md](../../skills/common/plan-smart-routes/SKILL.md) · [Installation](../INSTALL.md) · [License scope](../LICENSE-SCOPE.md)

Standalone root workflow; references are linked by the entry point.
