# Security and privacy

## Report a vulnerability

Please use GitHub's private vulnerability reporting for this repository. Do not put secrets, exact private travel locations, or exploit details in a public issue.

## Data-handling principles

- A route request authorizes only the read-only lookups needed for that request.
- Exact home, work, medical, school, and other sensitive coordinates are not persisted by default.
- Preference writes require explicit consent; sensitive labels require a second explicit opt-in.
- Provider credentials stay outside the repository and must be supplied through the user's secure environment.
- A generated deep link is not proof that a provider returned a route or current ETA.
- The bundled public-data helpers use bounded, human-triggered calls and must respect publisher terms, attribution, rate limits, and licences.

This project does not run a hosted routing service and does not collect telemetry.
