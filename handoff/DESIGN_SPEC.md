# Design Spec - Smart City Traffic Intelligence ("Traffic Control Center")

The source of truth for the look is `reference/` (open `reference/index.html` in a browser, no build step).
If this document and the reference disagree, the reference wins.

## 1. Look and feel

Light theme, modern, slightly 3D. Depth comes from four things, always together:

1. **Layered shadows.** Never a single blur. Cards use 3 stacked shadows plus a 1px white inset top highlight (`--shadow-card`).
2. **Bevel highlight.** `inset 0 1px 0 #fff` on every raised surface.
3. **Pressable keys.** Buttons have a solid "thickness" shadow (`0 2px 0` / `0 3px 0` darker green for primary). Hover lifts 2px, active presses down 2px and goes inset.
4. **Sunken wells.** Inputs, tab bars, the map and the explanation panels are *inset* (inner shadow), so raised cards read as floating above them.

Never use emoji as icons. Use inline stroke SVG icons (1.8 to 2 px stroke, round caps).

## 2. Tokens (see `reference/styles.css` `:root`)

| Token | Value | Use |
|---|---|---|
| `--ink` | `#1B2B23` | body text |
| `--soft` / `--muted` | `#3E4F46` / `#5E6F66` | secondary text (both pass 4.5:1 on white) |
| `--bg` | `#EDF1EE` | page, with two soft radial green glows |
| `--accent-hi/accent/accent-lo` | `#5B9677 / #3F7058 / #2F5A44` | primary gradient (top to bottom) |
| `--accent-edge` | `#254437` | the solid bottom edge of primary keys |
| congestion | idle `#CAD3CD`, low `#5E9A78`, moderate `#E0A33A`, high `#E2784A`, severe `#C8534E` | roads. Thickness also grows 8, 8, 9, 10, 11 px so colour is not the only cue |
| `--route-alt` | `#6F93BE` | current (non-suggested) route, dashed |
| priority badges | high `#A32626 on #FBE3E0`, medium `#7A4F00 on #FBEBC8`, low `#25603F on #DCEEE3` | |

Font: **Inter** (400/500/600/700/800). Radius: cards 18px, keys 12px, chips 8-10px, pills 999px.

## 3. Layout

Page is a fluid flex layout (no fixed page width). Target 1440 px wide.

```
+------+----------------------------------------------------------------+
| rail | topbar: title | live pill | ........ | time/date | operator      |
| 76px | intro: heading + 3 KPI cards                                   |
|      | +-----------+-----------------------------+-----------------+  |
|      | | decision  | review panel                | oversight stats |  |
|      | | list      |  header (id, priority)      |  donut          |  |
|      | | 280-340px |  map + legend               |  impact week    |  |
|      | |           |  explanation | key factors  |  recent activity|  |
|      | |           |  risks|impact|history|notes |  280-340px      |  |
|      | |           |  actions: reject edit approve                  |  |
|      | +-----------+-----------------------------+-----------------+  |
+------+----------------------------------------------------------------+
```

- Review panel is the hero: `flex: 999 1 560px; min-width: 0`.
- Left and right columns: `flex: 1 1 280px; max-width: 340px`.
- Everything wraps: below ~1000 px the three columns stack. Below 760 px the rail becomes a horizontal bar on top.
- The map has a fixed 640 x 340 design size inside a horizontally scrollable wrapper (see section 5).

## 4. Components

- **Rail**: logo tile, 5 nav buttons (Overview, Live simulation, Vehicles, Coordination, Analytics), then About and Settings pinned to the bottom. Active item is a raised green key and has `aria-current="page"`.
- **Status pill**: pulsing dot + text. Dot colour: green running, amber paused, grey ready.
- **KPI card**: 44px icon tile + big number (26px/800) + label. Lifts 3px on hover.
- **Decision card**: priority badge, confidence, `#ID` (22px/800), `FROM -> TO`, tick, tag chips (inset), est. impact, two buttons. Selected state: green tint, green border, 3px focus-style ring.
- **Tabs**: segmented control in a sunken track; the active tab is a raised white key.
- **Review header**: `Review Decision: #ID`, priority badge, and a status badge once approved or rejected.
- **Map**: see section 5.
- **Explanation panel**: sparkle icon, one paragraph, three check-bullets (each with a round green tick tile).
- **Key factors**: label + percent on one row, then an inset track with a glossy green fill.
- **Strip**: Risks Identified, Estimated Impact, Historical Performance (conic-gradient donut), "Make Coordination Changes" textarea (inset).
- **Actions**: Reject (square, red tint), Edit (square), Approve (wide primary key, 56px high, icon + two-line label).
- **Right column**: oversight donut with 3-item legend (values shown as text too), "Impact this week" rows, recent activity list with round status icons (green check = approved, amber pencil = modified).

## 5. The map (important - do it this way)

Do not use Plotly or one big SVG for the map. It is built from absolutely-positioned divs so every road, node and label is a normal DOM element that can be styled, hovered and focused.

- Node coordinates live in a `NODES` table (design space 640 x 340). Edge list = 19 undirected road pairs (38 directed segments).
- **Road segment** = a div whose `left/top` is node A, `width` is the distance A to B, `height` is the thickness, `transform: rotate(atan2(dy, dx))`, `transform-origin: 0 50%`, `border-radius: 99px`.
- Layer order, bottom to top: base roads (coloured by congestion) -> current route (blue dashed, 5px) -> suggested route (green gradient, 9px, white dashes down the middle, soft green glow) -> node circles -> label pills -> zoom keys.
- Put the three road layers in one wrapper with `filter: drop-shadow(0 3px 2px rgba(16,32,24,.22))` - one shadow for all roads, so it stays in screen space and does not rotate with each segment.
- **Nodes**: 18px white circle with a 3px grey border. On the suggested route the border is green. Start node = filled green with a ring (20px). End node = filled dark ink with a ring (22px).
- **Labels**: small white pills, 11px/700. Placement per node is `above`, `below` or `right` (see `LABEL_AT`) so they do not sit on top of roads.
- The map surface is *sunken*: subtle 32px grid, inset shadow.
- Legend row under the map: suggested, current, idle, low, moderate, high.
- When live data arrives, only update the road colours/thickness, the route layers and the vehicle markers (see 6). Do not rebuild the nodes and labels each tick.

## 6. Live-simulation additions (not in the static reference)

- **Vehicles on the map**: a small circle (10px) with a 20px low-opacity halo, positioned by interpolating along its current road segment. Moving = ink, queued = red.
- **Control bar** (above the intro or in the topbar): Start (primary), Pause, Reset, and a progress bar `Tick n / max`.
- **Updates**: poll `/api/state` every 1 s, or use a WebSocket if available. Re-render only the parts that changed.
- **Empty state** (before the first Start): all roads idle, KPIs at 0, and a clear "Start Simulation" call-to-action instead of silent zeros.

## 7. Accessibility and quality bar

- Text contrast at least 4.5:1. Never use colour as the only signal (congestion also changes thickness, status badges carry text).
- Real `<button>`, `<a>`, `<label>` + `<textarea>`; icon-only buttons need `aria-label`; decorative SVGs get `aria-hidden="true"`.
- Touch targets at least 44 px (zoom keys are 36 px, acceptable because they are secondary).
- Visible focus ring on every interactive element (3px green outline, 2px offset).
- Respect `prefers-reduced-motion` (animations and transitions off).
- Escape any text that comes from the API before putting it into HTML (use the `esc` helper, or a framework's default escaping).
