# Football Know design system

A football data terminal sold to organisations: dense, calm, and explicit about how fresh every figure is. The one signature element is the 60-second sync ring in the top bar; everything else stays quiet.

## Tokens

All colours are CSS custom properties in `public/styles.css`, defined once for light and once for `:root[data-theme=dark]`.

- Brand pine `#0f5c45` (dark theme `#48c79b`), page `#f2f5f3`, surface `#fff`, ink `#12201b`, muted `#5b6964`, lines `#dce4e0`.
- Amber marks live play and delayed data; red marks failures and losses. Colour never carries meaning alone: every state also has a word.
- The sidebar, the lead fixture and scoreboards share one dark pitch tone `#0c1f19` in both themes.
- System Chinese sans for text. Scores, odds and figures use the condensed `--num` stack (DIN Alternate, Bahnschrift) with tabular numerals. No web fonts: the site policy allows only same-origin resources.
- Radius 10 px for panels, 8 px for controls, 14 px for the two scoreboard blocks. Borders separate surfaces; shadows are reserved for overlays.

## Layout

- 232 px grouped sidebar, sticky 58 px top bar (search, sync ring, theme), content up to 1480 px.
- Below 900 px the sidebar becomes a drawer; below 620 px tables scroll inside their frame and the page itself never scrolls sideways.
- The overview leads with the match in play or the next kickoff, then one strip of season figures, then fixtures and tables.

## Interaction

- Every table sorts by clicking a column heading and exports to CSV; the sort survives the 60-second refresh.
- Refreshes update regions in place and keep search text, filters, open forms and focus.
- Search opens with Ctrl K or `/`; arrow keys and Enter work throughout.
- AI text is rendered as text, never HTML. No blocking dialogs. Reduced motion is respected.
- Club initials are navigation marks, not official crests.
