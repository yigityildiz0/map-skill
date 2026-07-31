# Contributing

Thanks for helping make route answers more reliable.

## Good contributions

- Add or repair an official transit, realtime, traffic, disruption, fare, or accessibility source.
- Add a city profile with explicit coverage, access requirements, licence, and freshness rules.
- Add a regression test for a navigation-link capability or route-scoring edge case.
- Improve a translation without weakening uncertainty or safety wording.

## City-profile evidence rules

Every source must include:

1. a first-party or government URL;
2. access type: `no_key`, `registration`, `api_key`, `web_only`, or `self_hosted`;
3. machine-readable coverage and known gaps;
4. licence/attribution requirements when known;
5. a verification date;
6. a rule that distinguishes `no_data` from `no_service`.

Do not commit API keys, copied realtime payloads with restrictive terms, private locations, or scraped protected endpoints.

## Validate

```bash
python -X utf8 scripts/validate_repo.py
python -X utf8 scripts/build_distributions.py --clean
python -X utf8 -m unittest discover -s tests -v
```

Open a focused pull request and explain which official pages or feeds were checked.
