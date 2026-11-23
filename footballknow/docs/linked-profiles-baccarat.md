# Linked profiles, mobile quotes and baccarat practice

Team names in the match centre now open team profiles; the score remains the match-detail link. Published team, horse, jockey, trainer and owner names across other rendered text link to matching records. Exact ambiguous names are left unlinked. Team identity uses league context and existing club aliases rather than numeric IDs alone.

Trainer, jockey and owner profiles expose associated horses and saved race entries. Season results come from the published HKJC ranking snapshot. Historical race ownership is only shown when recorded on that entry, not inferred from the horse's current owner. Coverage and dates remain visible. Entity lookups use existing local snapshots with a 30-second mtime cache and make no new provider requests.

Stock tables show name, price and percentage change first. On phones the remaining columns can be expanded. The new “其它” shortcut aggregates all classified sectors outside finance, property, gaming and technology; unclassified records remain separate. Specific industry filters and watch controls remain available.

Baccarat is a local virtual-amount practice tool. Eight decks are shuffled with Web Crypto and dealt without replacement, using standard third-card rules, without burn or cut cards. Up to 70 hands are dealt. Future hands are hidden until opened, and past hands cannot receive a new wager. Lucky 6 means banker wins on six; Lucky 7 means player wins on a three-card seven. Pair flags use equal ranks of the first two cards.

Default net simulation payouts: banker 0.95, player 1, tie 8, either pair 11, two-card Lucky 6 12, three-card Lucky 6 20, Lucky 7 40. These configurable practice defaults are not represented as a casino's official terms. Banker/player stakes push on ties; side wagers settle independently. Each round locks its payout settings; profits and refunds are rounded to cents. Local storage retains the deck, revealed progress and ledger.

The bet panel shows Big Eye Boy, Small Road and Cockroach Road alongside conditional banker/player probes. Ties do not advance these roads. Mobile roads remain visible while entering a stake; long roads follow the latest filled column. Road colours describe past patterns, not future probabilities.

## Validation (2026-11-23)

- Full JavaScript suite: 185 passed; final coach deduplication focused suite: 13 passed.
- Full Python suite: 453 passed, 13 subtests passed.
- Final focused suite after layout refinement: 15 passed.
- Browser QA at desktop and 390×844: arbitrary 123.45 stake, opening settlement, retained progress on reload, 70-hand completion and unchanged prior wagers, lower roads and conditional probes beside mobile amount entry.
- Browser QA: “其它” selected 2,008 of 2,822 local catalogue trading counters; mobile name/price/change visible with no page overflow; expanded watch controls remain visible.
- Browser QA: match-centre Arsenal name opens team 1, score is a distinct match link; jockey → trainer → owner → horse links resolve to the corresponding routes.
- The browser preview uses saved local snapshots plus read-only API proxying; its old data dates are not evidence of current production data completeness.

## Private stock watchlist sync

The former browser-only list now migrates into a private device group, with a durable local operation queue for offline changes. A one-use code connects another device for ten minutes. Initial pairing unions both lists; later additions and removals sync across connected devices. Unconnected visitors have separate lists. No administrator login is needed. Device cookies are HttpOnly, SameSite Strict and Secure in production; the database stores token hashes. Same-origin checks protect write routes. Idempotent operation IDs prevent a retried old add from resurrecting a later removal.

Browser QA used two isolated localhost origins with separate cookies/storage, both talking to the same test backend. One saved HSBC and the other Tencent. Pairing produced both stocks on both pages. Removing HSBC on the second and syncing the first left Tencent only. These were test records, not the user's actual phone pairing. Existing team follows, simulation ledgers and coach follows remain local.

## Coach observation and visits

The coach page now displays every collected fixture in the tenure, using the immediate prior match as the lineup baseline. Cross-competition club identity merges fixtures while retaining correct match-detail routes. Confirmed complete elevens use stable player IDs, formation and source links. Missing baselines do not silently compare an older match. The 30-day filter excludes future and invalid dates. Identical manager changes are shown once in the all-competition view. Browser QA confirmed full lists, 30-day filtering and the Sporting lineup change from 3-4-1-2 to 4-3-3 with four entrants/exits in the saved dataset.

The investment-site counter base becomes 35,627,892 while preserving stored added visits and deduplication IDs. The culture counter explicitly retains its existing 100,000 base; this release does not deploy culture-site files.
