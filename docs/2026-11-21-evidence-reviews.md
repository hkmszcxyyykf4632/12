# Detailed post-event reviews

The former football two-stage review only settled the score and handicap. Other review paths used short generic summaries and retained the first generated report after new data arrived. Reviews now preserve the original prediction and separately version the evidence and analysis.

## Behavior

- Football: verified event chronology, injuries, substitutions, full-match statistics, source-labelled odds and verified pregame snapshots. Each original statement is audited; observed facts and possible explanations are separate. A missing original is not a failed prediction.
- Racing: verified official result, every runner's result/position path, same-race sectional times and timestamped market records. No invented interference, wide running or deliberate losing without evidence.
- Watched stocks: adjusted price path, drawdown, eligible volume baseline, and existing five/63-session maturity checks. No invented benchmark return or news cause.
- All three: cited evidence IDs; proposed method changes require a saved original statement and pre-event evidence. Unresolved causes remain unresolved. Future forecasts receive dated candidate checks, never automatic reweighting or a promised accuracy improvement.
- An evidence change creates an additional review revision. A collection-time-only change reuses the existing review. Atomic revision publication and SQLite lesson indexing avoid partial reads and lost concurrent entries.
- Each new private revision retains its complete evidence snapshot. Request-local short citation labels are mapped back to stable evidence IDs before publication; unknown references and uncited causes remain blocked. An invalid draft gets one corrective attempt, then remains unpublished if still invalid.
- Corrective feedback includes every semantic validation error and its section/item position. The model must repair unsupported claims, not merely change the label while retaining the same causal assertion. Speculative wording is conservatively classified as inference; all citation and evidence requirements still apply.
- Comparable football odds are calculated by provider, market, phase and exact line. First/last sampled prices, absolute/percentage changes and over/under lower-price counts are computed directly. Unequally spaced samples do not measure time or traded volume. Hypotheses cannot be labelled as observed facts.
- Background generation respects the pause control and runs at most one football/racing review per five-minute pass; failed attempts have a 30-minute cooldown. Stock generation remains limited to watched securities.

## First data batch

Bayern Munich–FC Koln (20 November 2026, 19:30 UTC, 1–1) has a verified official-report supplement: the opening counterattack, Kane injury substitution, equaliser, Olise half-time replacement, later substitutions, second-half Cologne chances and the league-reported 1.10–2.07 xG. Reports do not establish what an unavailable original prediction omitted. Missing continuous quote records do not become an invented closing line.

The refreshed public match-detail cache and Tencent (00700) company/financial/history records are separately published data. Production data with a later `updatedAt` is preserved by the existing updater.

## Validation before release

- Python: 315 passed; 8 subtests passed.
- JavaScript: 117 passed, including readable evidence labels and citation navigation.
- Red/green regression: collection-time-only racing refresh incorrectly changed the evidence revision (two failing cases); both now reuse one generated review, while an actual odds change creates a new one.
- Local real-browser checks: Bayern final score and source-linked evidence; missing original is neutral; evidence links keep the match route. Racing official result dossier covers 14/14 runners; 390-pixel mobile layout checked and loading-class indentation fixed. Stock without a saved original does not claim a prediction result.
- Full private snapshots and credentials are not exposed by the public dossier. The test forecast used by the stock fixture is synthetic and is not published as a historical prediction.

## Live checks and limits

- The release preserves fresher production data, existing forecasts, credentials and sync controls. The updater keeps a rollback copy; web, worker and proxy services are active.
- [Bayern–Cologne](https://inwesting.shop/?league=bundesliga#/match/espn%3A401884736): the published detailed review has 201 source-linked facts, 31 timeline entries, eight drivers, four market analyses and five candidate checks. It distinguishes the opening counterattack from subsequent injuries, and opposite price movements at different bookmakers from a market consensus. No saved original pregame forecast was found. The case is process research and must not be counted as a forecast hit or miss.
- [18 November Happy Valley race 9](https://inwesting.shop/#/race/2026-11-18-HV-9): a source-checked editorial review is published with 50 facts, eight original-claim audits, five drivers, three market analyses and four unresolved candidate checks. The actual original pick finished second: win missed, top-three achieved. The pick's middle 400 metres were 0.68 seconds faster than the winner's, but its last 400 metres were 0.76 seconds slower. This establishes where the gap changed, without inventing an incident or a fatigue cause. The original forecast's arithmetic and record-summary inconsistencies are explicitly retained and audited. Two observed odds endpoints are not presented as an official opening/closing series. The editorial example is committed in `docs/review-examples/`; it is not evidence of an automatic model pass.
- Racing, 14 November Sha Tin race 1: the public dossier exposes 57 facts and same-race sectionals for all 14 runners. No saved pre-race original was found for this sample; the old short post-race report is retained separately.
- Tencent 00700: a genuine 17 November forecast is retained. The current review has eight price/volume facts; only two of the required five/63 forward sessions are complete. Both horizons correctly remain under observation. This security is currently not in the server watchlist, so no new report was generated for it.
- One initial AI draft had an uncited lesson; another structurally valid draft reversed two over/under price comparisons. Live content review caught these defects. Short citation aliases, computed price summaries and stricter fact/inference labels were added, and the prior revision is retained privately rather than silently rewritten.
- The final health check returned `ok` with a two-second worker heartbeat. At that point, the daily-football and evidence-reviews jobs each reported a failure; other historical reports had not all been regenerated. Invalid automatic explanations remain unpublished. Healthy services do not imply that every source or generation job succeeded.

## Published release

- Source revision: `21c3d62121b215ff2440057a974c3a2e7cdf6bb3`.
- Package commit: `53e473ad4fd7783e961e7774c3da793d9bc8cabe`.
- Archive: `releases/evidence-reviews-21c3d62121b2.tar.gz`, SHA256 `7a6946662db334c2321ad0e5844f24c9f0837f87f0dd1fcf95465bc433f6608b`.
- Production publication: `2026-11-21T10:53:57.939973+00:00`.
- Rollback copy: `/var/backups/footballknow/expanded-21c3d62121b2-20261121T105352`.
- The package deployment succeeded before a separate editorial-file checksum check failed because the local file had CRLF line endings. The downloaded Git blob was independently hashed, then the race-only publication succeeded after matching the current facts and original-claims hashes. No original forecast was changed.
- Live football and racing pages were visually checked after publication, with screenshots saved in the local release evidence folder. Code and release archive are pushed to GitHub.

Automated checks do not prove that an AI explanation is causally correct. Public reports require evidence review; unfinished causes remain identified as such, and no accuracy improvement has yet been measured. The pre-existing daily football feed still has a separate synchronization failure and retains its last valid data; this release does not claim every data source is complete.
