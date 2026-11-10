# Circle — design system

A launcher lives on the keyboard: it is opened dozens of times a day, usually
mid-thought. That fact sets every rule below. Nothing here is decorative for its
own sake — the panel should feel like it was already open.

Direction: **cold glass, quiet ink.** A near-black panel that floats over your
work, one hairline edge, a single accent used only for the thing you are about
to act on.

## Palette

| Token | Value | Use | Contrast on panel |
| --- | --- | --- | --- |
| `BG` | `#101014` | panel base | — |
| `SURFACE` | `#17171D` | inputs, nested surfaces | — |
| `SURFACE_HI` | `#20202A` | selected row, pressed button | — |
| `HAIRLINE` | `rgba(255,255,255,.086)` | dividers, group borders | — |
| `HAIRLINE_STRONG` | `rgba(255,255,255,.15)` | panel edge, input borders | — |
| `TEXT` | `#EDEDF2` | titles, values | 16.3:1 |
| `TEXT_DIM` | `#9C9CB0` | subtitles, section labels, hints | 7.1:1 |
| `TEXT_MUTE` | `#71718A` | decorative only — never text you must read | 4.0:1 |
| `ACCENT` | `#8AB4FF` | selection, focus, primary action | 9.1:1 |
| `DANGER` | `#FF8095` | close / cancel affordances | — |
| `OK` | `#8BE0A4` | volume, confirmations | — |

Every text colour used for reading clears 4.5:1 against the panel. Placeholders use
`TEXT_DIM`, not a grey that looks disabled.

## Type

System-native on both platforms, because a launcher should look like the desktop
it interrupts. The stacks resolve at runtime to whatever the machine actually has.

- UI: `Segoe UI Variable Text` → `Segoe UI` → `SF Pro Text` → `Helvetica Neue` → `Inter`
- Display (query field): `Segoe UI Variable Display` → `SF Pro Display`
- Mono: `Cascadia Mono` → `Consolas` → `SF Mono` → `Menlo`
- Emoji (legacy wheel slots only): `Segoe UI Emoji` → `Apple Color Emoji`

| Role | Size | Weight |
| --- | --- | --- |
| Query field | 20 px | Regular |
| Row title | 13 px | DemiBold |
| Row subtitle | 11 px | Regular |
| Section label | 10 px, tracking 0.7 | DemiBold, uppercase |
| Footer hints | 11 px | Regular |
| Settings headings | 18 px | DemiBold |

## Space and shape

- Panel: 720 px wide, 16 px radius, 1 px hairline edge, one soft shadow
  (`0 20px 72px rgba(0,0,0,.75)`). Elevation is declared once — never a border
  plus a wide shadow on the same surface.
- Field padding 22/18; row height 46 px; section header 30 px; footer 34 px.
- Result rows sit 8 px inside the panel and use a 10 px radius, so the selection
  reads as a card floating in the list rather than a full-bleed bar.
- Settings: 12 px radius on groups, 8 px on controls, 16 px gutters.

## Motion

The panel has **no entrance animation**. It is a keyboard surface — anything that
delays the first character makes the whole machine feel slow. Selection changes are
instant for the same reason. Nothing in Circle animates on open, close or keypress;
the only motion is the wheel following the cursor, which is direct manipulation.

## Icons

`icons.py` holds ~38 glyphs drawn on a 24×24 grid, one stroke weight (1.7), round
caps and joins, rendered at 2× and cached. No emoji in the chrome, no platform icon
theme — a file, an app and a settings page read as one family. Real application and
file icons come from Windows itself (`QFileIconProvider`) and are drawn in the same
22 px box.

Wheel slots choose from the same set; a slot with no icon name falls back to a
single character, so older configs still render.

## Platform

One design, two operating systems. The palette, type scale, spacing and icon set
are identical; only the system-facing copy changes — "System Settings" instead of
"Windows Settings", "Empty the Trash" instead of "Empty the Recycle Bin", Option
instead of Alt. Nothing is re-themed per platform, because a launcher that looks
different on each machine stops being one product.

## Copy

Controls name their action ("Save changes", not "OK"). Empty states say what to try
next: *Nothing matches that yet — try @g for the web, or a sum like 18*4.* Errors
name the problem. No exclamation marks, no "successfully".
