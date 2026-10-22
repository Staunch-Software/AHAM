# Look and feel (AHAM branding)

The admin web and the mobile app share one visual identity, taken from AHAM Housing Finance (the logo and the colours
on ahamhfc.com), with FieldSync as the product name and "Field operations" as its tagline.

## Brand tokens
| Token | Value | Used for |
|---|---|---|
| Navy 700 | `#283079` (the navy of the logo) | primary buttons, links, active states |
| Navy 800 / 900 | `#1e1b4b` / `#17153a` (the site's navy) | sidebar, headers, headings |
| Gold 500 | `#eab308` | accent: active-nav marker, "pending" highlights, the Sync button |
| Roof red | `#ed2636` (the roof in the logo); dark `#b01a27` | "Needs correction", errors, the map pin |
| Green | `#059669` | approved / accepted |
| Page background | `#f1f3f9` (mobile), slate-100 (web) | behind cards |
| Font | **Inter** (the site uses it too) | everything |

Status colours are fixed everywhere: pending review = amber, approved = green, needs correction = red, inactive = grey.

## Where the styles live
| | Web (`admin-web/`) | Mobile (`mobile/`) |
|---|---|---|
| Colours | `tailwind.config.js` (`brand`, `gold`, `roof` scales) | `lib/app/theme.dart` (`Brand`) |
| Components | `src/components/ui.tsx` (Button, Card, StatCard, Badge, Table, Dialog, Toggle, Segmented, Avatar, BrandMark...) | `lib/app/widgets.dart` (BrandLogo, StatusPill, IconTile, Notice) |
| Global theme | `src/index.css`, `index.html` | `buildTheme()` in `lib/app/theme.dart` |
| Font | `@fontsource-variable/inter` (bundled by Vite, no CDN) | `assets/fonts/Inter-*.ttf` (static instances made from the same font; works offline) |
| Logo | `public/aham-logo.jpg`, `public/favicon.png` | `assets/images/aham-logo.jpg`, Android launcher icons in `android/.../mipmap-*` |
| Icons | `lucide-react` | Material icons (rounded) |

To restyle: change the tokens first, then the shared components; screens should not hard-code colours.

## The logo
The logo file is the 250 x 250 JPEG published on ahamhfc.com (`/img/Web_logo.jpg`), saved on 2026-10-20. It has a white
background, so it is always shown in a white rounded tile (also on the dark sidebar and headers). If you have the
official logo as SVG or a transparent PNG, replace the two copies listed above (keep the file names, or update
`BrandMark` in `ui.tsx` and `BrandLogo` in `widgets.dart`) and regenerate the launcher icons.

## Licences
Inter is distributed under the SIL Open Font License 1.1 (`mobile/assets/fonts/OFL.txt`; the web package carries its own
copy). The AHAM name and logo belong to AHAM Housing Finance.

## Behaviour that the design must keep
- Time and location are recorded automatically; the form says so next to the Submit button.
- A report saved offline is never shown as accepted until the server confirms it ("Sync pending").
- The reviewer's "rejected" is shown to everyone as "Needs correction".
- The field map shows **recorded** positions, not live tracking, and says so.
- The web has no form-builder screens (a test checks this).
- The production Content-Security-Policy allows same-origin fonts and images only (plus Google Maps); do not load fonts
  or icons from a CDN.
