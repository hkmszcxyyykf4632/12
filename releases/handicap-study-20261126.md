# Three-season shallow handicap study

Scope: EPL, LaLiga, Serie A and Bundesliga, completed seasons 2023/24 to 2025/26. Source-labeled closing AHCh only; signed home handicap in {-0.5, -0.25, 0, 0.25, 0.5}. Earlier AHh is a scheduled snapshot and is not represented as the true opening line.

Verified selection: 2,450 of 4,338 completed matches; 882 / 794 / 774 by newest season first. No missing closing line. Each match is counted once. Quarter-line settlements split the stake equally. Source download receipts retain SHA-256 hashes. A separate Decimal calculation independently reconciles totals and settlement returns.

The public page at #/handicap-study contains computed aggregates only. Original source tables and the derived per-match research workbook remain in the local research package. Historical descriptive results do not enter the website's live forecast accuracy or simulated betting ledger. No model training or recurring source download is enabled by this release.

Sources:
- https://www.football-data.co.uk/data.php
- https://www.football-data.co.uk/notes.txt

Validation: 7 Python study tests, 205 JavaScript tests including 6 study tests, independent 12-file source reconciliation, desktop rendering, 390px mobile rendering without page overflow, season/league selection and disclosure behavior.

Release: five static public files only, published from a pinned Git revision. The publisher verifies both the expected previous content and new file hashes, backs up before replacement, checks local HTTP responses, and rolls back its changes if verification fails. It does not restart collection services. Production publication is pending renewed Tencent Cloud authentication.
