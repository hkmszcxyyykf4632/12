# Data coverage repair

Production inspection on 2026-11-21 found that the Hong Kong catalogue contained 2,822 trading counters, but the regular company-information task iterated only the 95 index constituents. Other company profiles depended on visitors opening them. The published capital index contained 96 records: 31 cash, 31 debt, 11 special financial-sector statements and 23 unclassified. Unclassified entries can already have complete reports but lack a separately disclosed short-term or long-term borrowing field; they must not be counted as missing entire company profiles.

The horse directory contained 1,464 horses with owner, pedigree and image metadata. Of these, 1,019 had recorded past runs. A sampled zero-record horse, HK_2026_J313, has an official career record of 0-0-0-0. Zero starts must be distinguished from a failed download. Workouts and sectionals previously relied primarily on opening an individual horse's research endpoint.

## Repair

Two bounded, durable queues now cover the full Hong Kong and mainland stock catalogues and the horse research catalogue. Unattempted and incomplete records advance ahead of completed refreshes. The next race day's horses have priority. Each task has a time budget and item limit, persists retry times, honors the administrator pause switch and reports field-level coverage. A failed or incomplete source cannot count as a complete profile. Null financial values do not count as collected statements, and an empty horse history needs an explicit official zero-start career total before sectionals are considered inapplicable. Existing successful data remains available. Company financial classifications are rebuilt from saved profiles after each batch.

Company-classification messages now distinguish an absent report from specific unreported fields or a currency mismatch. Current bonds (004011021) are included in disclosed debt. The stock table refreshes the financial index as new profiles arrive.

## Production verification

Revision `7fc296d193e363c8be12bea1c87327adc2671cac` was installed on the investment server on 2026-11-21 at 12:42:45 Hong Kong time. The web, worker and Caddy services were active. The release replaced 12 application files and preserved 10 newer production data files. Backup: `/var/backups/footballknow/expanded-7fc296d193e3-20261121T044245`.

The first bounded production company batch attempted 13 entries and completed 9. Its published coverage snapshot at 04:44:54 UTC contained 8,042 Hong Kong/mainland catalogue entries, 132 saved profiles, 129 complete records across the six checked field groups, and 4 entries due for retry. The horse batch attempted and completed 11 entries; the 04:45:42 UTC snapshot contained 18 horses with workouts and sectionals (or an explicitly verified zero-start exception) out of 1,464. These counts demonstrate a working incremental collection path, not full coverage.

The public forecast index at 04:59:48 UTC contained initial reports for all 15 still-upcoming five-major-league matches on the Hong Kong calendar date 2026-11-21. No final-stage report had been created before the lineup confirmation window. Public health reported a two-second worker heartbeat, no administrator pause, and 77 scheduled jobs (31 successful, 1 failed, 45 pending). This is not evidence that all external sources were healthy.

## Remaining source work

Football's primary ESPN data requests currently return 403. A one-off FotMob public-page inspection succeeded, but its published restriction on systematic automated use means no new recurring FotMob collection was added. SportScore's documented public API was inspected as another candidate, with match-identity and confirmed-lineup checks still required before integration. Predicted starting elevens must never be presented as confirmed lineups. No data-source restriction was bypassed.
