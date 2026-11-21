# Data coverage repair

Production inspection on 2026-11-21 found that the Hong Kong catalogue contained 2,822 trading counters, but the regular company-information task iterated only the 95 index constituents. Other company profiles depended on visitors opening them. The published capital index contained 96 records: 31 cash, 31 debt, 11 special financial-sector statements and 23 unclassified. Unclassified entries can already have complete reports but lack a separately disclosed short-term or long-term borrowing field; they must not be counted as missing entire company profiles.

The horse directory contained 1,464 horses with owner, pedigree and image metadata. Of these, 1,019 had recorded past runs. A sampled zero-record horse, HK_2026_J313, has an official career record of 0-0-0-0. Zero starts must be distinguished from a failed download. Workouts and sectionals previously relied primarily on opening an individual horse's research endpoint.

## Repair

Two bounded, durable queues now cover the full Hong Kong and mainland stock catalogues and the horse research catalogue. Unattempted and incomplete records advance ahead of completed refreshes. The next race day's horses have priority. Each task has a time budget and item limit, persists retry times, honors the administrator pause switch and reports field-level coverage. A failed or incomplete source cannot count as a complete profile. Null financial values do not count as collected statements, and an empty horse history needs an explicit official zero-start career total before sectionals are considered inapplicable. Existing successful data remains available. Company financial classifications are rebuilt from saved profiles after each batch.

Company-classification messages now distinguish an absent report from specific unreported fields or a currency mismatch. Current bonds (004011021) are included in disclosed debt. The stock table refreshes the financial index as new profiles arrive.

## Open verification

The new queues require production execution and coverage measurements. Football's primary ESPN data requests currently return 403; the independent FotMob public page has been read successfully locally and is under identity, timestamp and lineup-status evaluation. Predicted starting elevens must never be presented as confirmed lineups. No data-source restriction was bypassed.
