# SantaCena → Elementor templates

Hybrid conversion of `index5.html` (ES) and `index5Eng.html` (EN) from
`github.com/rubenmarchan/SantaCena` into importable Elementor page templates.

| File | Goes on | News feed |
|---|---|---|
| `santa-convocacion-2026-es.json` | santaconvocacionlldm.org | category **11**, 178 posts |
| `holy-supper-2026-en.json` | holysupper.org | category **2**, 96 posts |

Each template is three sections:

1. **Hero** — full-height background, pretitle, title, poster image, "Video"
   button, social icons. All native Elementor widgets.
2. **News** — a heading widget plus one HTML widget carrying the live
   `/wp-json/wp/v2/posts` feed (markup + CSS + JS).
3. **Footer** — copyright line.

## Install

1. Upload the two images for that site into its `/images/` folder:
   - ES → `santaconvocacionlldm.org/images/` : `hero-bg.jpg`, `santacena2026.jpg`
   - EN → `holysupper.org/images/` : `hero-bg.jpg`, `holysupper2026.jpg`

   **`holysupper.org/images/` does not exist yet** — it 404s, which is also why
   that site's favicons are currently broken. Create the folder, or open the
   hero section / image widget in Elementor after import and re-pick both
   images from the Media Library.

2. WordPress admin → **Templates → Saved Templates → Import Templates** →
   upload the `.json`.

3. **Pages → Add New → Edit with Elementor →** folder icon (Add Template) →
   **My Templates** → insert.

4. Set the page's template to **Elementor Full Width** or **Canvas** so the
   hero runs edge to edge.

## Things worth knowing

- **The site header was not converted.** The original has a fixed overlay
  hamburger nav, which free Elementor can't reproduce as page content, and a
  page template sits inside whatever header your theme already renders.
  Rebuild it as a theme menu (or an Elementor Pro Theme Builder header) using
  `images/logo.svg` and these items:
  Noticias / News → `#intro` · Bienvenida 2026 / Welcome 2026 → `#about` ·
  Ceremonia de Bautismos 2026 / Baptismal Ceremony 2026 · Ceremonia de Santa
  Cena 2026 / Holy Supper Ceremony 2026.
  The last two were dead `href="#"` links in the original and still need real
  destinations.

- **The HTML widget contains a `<script>`.** WordPress only lets users with
  the `unfiltered_html` capability save that — fine for an administrator on a
  single site, not for editors or for multisite non-super-admins.

- **The feed is same-origin now.** `CFG.sitio` is `''`, so requests go to
  `/wp-json/...` relative and survive a domain change. To point a template at
  a different site, set `sitio` back to an absolute URL in the HTML widget.

- **Feed CSS is self-contained.** The original stylesheet set
  `html{font-size:62.5%}` so `1rem` meant 10px; every rem in the feed block has
  been baked to pixels, and the theme colour/spacing variables it referenced are
  now declared locally on `.wp-news`. Nothing depends on the destination theme.

- **Lora and Inter** load via a Google Fonts `@import` inside the HTML widget,
  and via Elementor's typography controls on the native widgets.

- **`#about`** is an explicit `<div>` inside the HTML widget, not an Elementor
  section ID — the hero button's smooth scroll and the feed's own
  `scrollIntoView` both target it.

- **Dropped:** the PhotoSwipe lightbox scaffold, the preloader, the rellax
  parallax (now a static cover background), and a 196 KB base64 JPEG for an
  `.s-services` section that no longer exists in the markup. The parallax is
  the only visible difference from the original.

## Regenerating

`build_templates.py` rebuilds both JSON files from a fresh clone of the repo
(expects `./SantaCena/`). `test_feed.js` runs the generated HTML widget in
jsdom against the live WordPress REST API and asserts cards render — it needs
`npm install jsdom`.
