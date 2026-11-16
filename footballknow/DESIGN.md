# Football Know design system

The operational archive follows a bilingual matchday programme: a compact fixture lead, parallel names and comparison tables, distinct section headings, and source notes. The existing evergreen identity remains consistent across the twenty clubs and research tools.

## Requested design direction

The user explicitly requested design-taste-frontend. Recorded draw: borrowed-category, seed 351190849, keeping palette and type. This is an existing application, so the component-refinement exception applies. The borrowed category is a matchday programme. The marketing-only poster/photo hero and decorative motion are not imposed on dense records. The direction artifact remains in .taste-skill/direction.json.

## Tokens and layout

- Evergreen #164d3d, deep navigation #103c30; paper #f6f7f3, white surfaces, ink #202b27, muted #65726b.
- Shared 4 px spacing scale; page padding 44 px desktop and 18 px mobile; section rhythm 48 px desktop and 36 px narrow.
- Body 16 px, tables 14 px, secondary 13 px, page heading 36 px desktop / 28 px narrow; Chinese system sans with Bahnschrift numeric identity when available.
- Tabular numerical values; internal scrolling for wide tables. Club initials are navigation marks, not official crests.
- Desktop left navigation becomes a horizontal mobile strip. Fixture rows reflow into a three-column score line; admin panels and comparison sections stack.

## Interaction

Players precede the recent-results table, with direct jumps to transfers and managerial changes. Mandarin and Hong Kong names remain visible together, original names retained, and unverified drafts labelled at the row. Data refresh updates targeted regions while preserving search, forms, backup confirmation and local records.

Administrator login, AI settings, editable methodology, source job status and password change share the existing field and button system. AI text is rendered as text, not executable HTML. Native blocking dialogs are not used. Focus indicators, labelled controls, reduced motion and inline confirmation remain.

## Verification

The prior version had real desktop/mobile captures. The current upgrade has passed DOM interaction and server checks, but no new rendered desktop/mobile screenshots: read/click control of the same required in-app browser is absent. Do not label old captures as current visual proof. Remaining visual checks: 390 px player/transfer tables, fixture reflow, login/settings/rules forms, keyboard focus and long AI content.
