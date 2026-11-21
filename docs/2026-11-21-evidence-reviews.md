# Detailed post-event reviews

The former football two-stage review only settled the score and handicap. Other review paths used short generic summaries and retained the first generated report after new data arrived. Reviews now preserve the original prediction and separately version the evidence and analysis.

## Behavior

- Football: verified event chronology, injuries, substitutions, full-match statistics, source-labelled odds and verified pregame snapshots. Each original statement is audited; observed facts and possible explanations are separate. A missing original is not a failed prediction.
- Racing: verified official result, every runner's result/position path, same-race sectional times and timestamped market records. No invented interference, wide running or deliberate losing without evidence.
- Watched stocks: adjusted price path, drawdown, eligible volume baseline, and existing five/63-session maturity checks. No invented benchmark return or news cause.
- All three: cited evidence IDs; proposed method changes require a saved original statement and pre-event evidence. Unresolved causes remain unresolved. Future forecasts receive dated candidate checks, never automatic reweighting or a promised accuracy improvement.
- An evidence change creates an additional review revision. A collection-time-only change reuses the existing review. Atomic revision publication and SQLite lesson indexing avoid partial reads and lost concurrent entries.
- Background generation respects the pause control and runs at most one football/racing review per five-minute pass; failed attempts have a 30-minute cooldown. Stock generation remains limited to watched securities.

## First data batch

Bayern Munich–FC Koln (20 November 2026, 19:30 UTC, 1–1) has a verified official-report supplement: the opening counterattack, Kane injury substitution, equaliser, Olise half-time replacement, later substitutions, second-half Cologne chances and the league-reported 1.10–2.07 xG. Reports do not establish what an unavailable original prediction omitted. Missing continuous quote records do not become an invented closing line.

The refreshed public match-detail cache and Tencent (00700) company/financial/history records are separately published data. Production data with a later `updatedAt` is preserved by the existing updater.

## Validation before release

- Python: 306 passed; 8 subtests passed.
- JavaScript: 116 passed; the final shared-renderer rerun passed all 10 tests.
- Red/green regression: collection-time-only racing refresh incorrectly changed the evidence revision (two failing cases); both now reuse one generated review, while an actual odds change creates a new one.
- Local real-browser checks: Bayern final score and source-linked evidence; missing original is neutral; evidence links keep the match route. Racing official result dossier covers 14/14 runners; 390-pixel mobile layout checked and loading-class indentation fixed. Stock without a saved original does not claim a prediction result.
- Full private snapshots and credentials are not exposed by the public dossier. The test forecast used by the stock fixture is synthetic and is not published as a historical prediction.

Live deployment verification is recorded separately after release. Automated checks do not prove that an AI explanation is causally correct; generated public reports still require review against their cited sources.
