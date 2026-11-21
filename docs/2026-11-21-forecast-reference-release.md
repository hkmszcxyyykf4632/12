# Initial forecasts with dated reference data

The automatic forecast and horse preparation release (source `846c5a9686bedcfa21dd95e6a44f6f1d3af7de29`) was installed on the investment server on 2026-11-21 at 11:55 Hong Kong time. The web service, worker and Caddy were active. Existing administrators, DeepSeek configuration and the enabled synchronization setting were retained.

The first production run found that the existing ESPN requests returned HTTP 403. The latest saved daily fixture feed was dated 2026-11-20. No initial predictions were published from that stale feed. The restriction was not bypassed.

This follow-up adds an independent initial-reference path using Football-Data's public fixtures and league results. On the server, the canonical `https://football-data.co.uk/fixtures.csv` endpoint returned 200 and 190 rows, with a Last-Modified time of 2026-11-20 10:23:08 UTC. The CSV's preclosing quotation is a dated pre-match reference, not a live quote or a verified opening price.

## Acceptance rules

- Match division, both team names and the exact kickoff time; reject ambiguous, completed, future-published or more than seven-day-old fixture files.
- Cache downloads for five minutes. Preserve separate file publication and fetch timestamps. Interpret fixture times in Europe/London including daylight saving time.
- Use only completed, internally consistent league results from before the prediction. Both teams need at least three valid results. The transparent weighted Poisson baseline is not a calibrated hit rate.
- Render the initial report as a reference edition, with its quotation file time and source. Do not invent lineups, injuries, weather, cup results or live price movement.
- Keep the final-stage requirements unchanged: fresh fixture data and both official starting elevens are mandatory. A reference edition cannot satisfy that gate.
- Preserve the two immutable stages, pre-kickoff checks, scheduler limits, administrator pause switch and post-match reviews.

The one-off initial generation requested by the owner covers still-upcoming fixtures on 2026-11-21 in Hong Kong time. Already-started matches are excluded. Normal initial scheduling remains six hours before kickoff; final checks begin ninety minutes before kickoff.

## Verification and publication

Focused regression tests cover source identity, date boundaries, aliases, missing data, reference labeling and rejection of reference data for final forecasts. The production generation counts and publication evidence will be appended after installation and real model execution.
