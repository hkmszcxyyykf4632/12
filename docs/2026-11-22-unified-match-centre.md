# Unified match centre and team information

The daily scoreboard and the league match centre now share one entry. Daily view covers the global feed; league view includes a nearby seven-day window and an explicit full-season option. Team profiles use five tabs, with recent confirmed results first and background research folded into disclosures. Team analysis shows the saved per-fixture forecast before optional statistical reference material.

## Result consistency

A daily score can update a league fixture only when competition, current season, exact kickoff and both opponents agree. ESPN event IDs and team IDs are checked when available. Ambiguous matches and non-regulation or missing final scores cannot settle a fixture. Confirmed finals cannot regress to provisional or scheduled states; newer confirmed corrections remain accepted. The browser repository, match catalogue and analysis loader use the same rule. EPL publishing also retains previously confirmed final scores.

Public snapshot audit, 2026-11-22 22:36 Hong Kong time: all 36 daily fixtures across the four domestic leagues matched their catalogue identities. Seven EPL provisional results advanced to verified finals, including Man City 1:1 Fulham. No unmatched domestic fixtures in this sampled window; no UCL fixtures in the window.

## Loading and disclosure

The listing requests `/api/football-forecasts?compact=true`. Long reports are fetched for a single fixture only after its disclosure is opened. On the sampled 36-record response, compact JSON was 23,526 bytes versus 2,343,727 bytes for the full index. Full saved reports, pre-match picks and reviews are unchanged. Read failure is distinguished from a missing saved prediction.

## Validation before deployment

- JavaScript suite: 161 passed.
- Python suite: 439 passed, 8 subtests passed.
- Identity/season/kickoff/duplicate and final-regression cases covered; integration checks catalogue and analysis agreement.
- Browser: unified centre filters, Real Madrid 2:1 Celta summary and full saved reviews, Manchester City 1:1 Fulham team overview and schedule, keyboard category navigation, analysis disclosures.
- Responsive team view checked at 390px viewport; no document horizontal overflow.

## Backfill audit (not a completion claim)

At 22:36 on 2026-11-22: HK and mainland catalogue contained 8,042 symbols; 1,609 had company data and 1,553 had the six tracked sections. Horse research catalogue contained 1,463 horses, with 683 completing the tracked workout/sectional checks. These counts do not imply that all photos, fields or all historical records are complete. Both jobs reported unpaused.
