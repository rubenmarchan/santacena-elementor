# SantaCena → Elementor templates

Hybrid conversion of `index5.html` (ES) and `index5Eng.html` (EN) from
`github.com/rubenmarchan/SantaCena` into importable Elementor page templates.

| File | Goes on | News feed |
|---|---|---|
| `santa-convocacion-2026-es.json` | santaconvocacionlldm.org | category **11**, 178 posts |
| `holy-supper-2026-en.json` | holysupper.org | category **2**, 96 posts |

Each template is three sections, plus a fourth on the English one:

1. **Hero** — full-height background, pretitle, title, poster/video frame,
   "Video" button, social icons. Native Elementor widgets, plus one HTML widget
   that renders nothing and only carries the frame's sizing rule (see below).
2. **News** — a heading widget plus one HTML widget carrying the live
   `/wp-json/wp/v2/posts` feed (markup + CSS + JS).
3. **Instagram gallery** (EN only) — one HTML widget carrying `ig-gallery.html`,
   a 12-tile grid with a lightbox that reads `/wp-json/wp/v2/media`. See below.
4. **Footer** — copyright line.

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

## The Instagram gallery

`ig-gallery.html` is a vendored copy of the block maintained in the sync bot's
repo (`lldm-fb-sync/gallery/holysupper-ig-gallery.html`) — copied so this build
has no dependency on a path outside the repo. **If you change one, diff the
other.** `build_templates.py` strips its header comment and rewrites the
`data-` attributes from the template's `gallery` config.

It renders whatever `lldm-fb-sync`'s hourly `sync-ig-gallery` cron has put in
that site's own Media Library — media items titled `igfeed-<instagram id>`, at
present 24 photos from `@holysuppertlotw`. Nothing is hotlinked from Instagram,
and the section **hides itself** when the feed is empty or unreachable. That is
also why its heading lives inside the HTML widget rather than in an Elementor
heading widget above it: a native heading would outlive the gallery and leave a
title standing over nothing.

Only the English template has a `gallery` key. santaconvocacionlldm.org has no
synced photos, so the same block there would ship a section that never appears;
adding the key is all it takes once that site is synced.

## The hero video frame

The poster is the placeholder for a video that isn't shot yet, so the hero is
built around that frame rather than around the headline. It is **not** a fixed
560px any more: `HERO_VIDEO_CSS` in `build_templates.py` sizes it from the free
height of the window — floor 560px, ceiling 1200px, always 16:9 — and the title
sits at 64px (was 104) to leave it the room. This mirrors `index6.html` /
`index6Eng.html` in the SantaCena repo, which are the same move on the static
pages; change one, change the other.

Two things make it work and are easy to undo by accident:

- The rule lives in an HTML widget because Elementor's width control takes a
  single number, not a `max()`/`calc()` expression. Setting a width on the image
  widget in the editor will fight it.
- It hangs off `_css_classes: sc-hero-video` on the image widget. Rename or
  clear that class in the editor and the frame drops back to Elementor's
  defaults.

Because the section is min-height (not a hard 100vh), a frame too tall for the
window pushes the hero taller instead of clipping the button.

**To put the real video in**, replace the image widget with a Video widget (or
an HTML widget holding the embed) and give it the same `sc-hero-video` class —
the frame geometry is on the class, not on the widget type.

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

- **The English hero title is Cinzel** (`title_font` in the config; the Spanish
  one is left as Lora). It's a display face for that one line — everything else
  on both pages stays Lora/Inter. Elementor enqueues the Google Font itself for
  a typography control, so the HTML widget's `@import` needs nothing added.

- **`#about`** is an explicit `<div>` inside the HTML widget, not an Elementor
  section ID — the hero button's smooth scroll and the feed's own
  `scrollIntoView` both target it.

- **Dropped:** the PhotoSwipe lightbox scaffold, the preloader, the rellax
  parallax (now a static cover background), and a 196 KB base64 JPEG for an
  `.s-services` section that no longer exists in the markup. The parallax is
  the only visible difference from the original.

## Regenerating

`build_templates.py` rebuilds both JSON files from a fresh clone of the repo
(expects `./SantaCena/`, gitignored) and writes them to `out/`; copy the ones
you want over the tracked files at the top level. Every element id is random,
so a rebuild always shows a whole-file diff — compare with ids normalised
before assuming anything actually changed.

`test_feed.js` mounts the generated HTML widgets in jsdom against the live
WordPress REST API and asserts both the news cards and the gallery tiles
render — it needs `npm install jsdom`. Note jsdom's `getComputedStyle` does
**not** cascade reliably across several stylesheets; it disagreed with Chrome
on this page. Use a real browser for any layout question.
