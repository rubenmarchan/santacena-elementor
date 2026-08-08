#!/usr/bin/env python3
"""Turn SantaCena index5.html / index5Eng.html into Elementor page templates.

Hybrid conversion: hero, headings, poster, button, socials and footer become
native Elementor widgets; the WordPress news feed stays an HTML widget because
it is JavaScript that talks to /wp-json. A template that sets `gallery` gets a
second HTML widget carrying the Instagram grid from ig-gallery.html.

Output: two importable .json files (Elementor > Templates > Import).
"""

import json
import pathlib
import re
import secrets

HERE = pathlib.Path(__file__).parent
SRC = HERE / "SantaCena"
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

# The StyleShout stylesheet sets html{font-size:62.5%} so 1rem == 10px there.
# A normal WordPress theme leaves it at 16px, which would inflate every size in
# the feed CSS by 60%. Bake the rems down to pixels so the block is immune to
# whatever root size the destination theme uses.
REM = re.compile(r"(?<![\w.-])(\d*\.?\d+)rem\b")

# Values lifted from the :root block of the original page (lines 1682-1810).
FEED_VARS = """
.wp-news {
    --font-1        : "Lora", Georgia, serif;
    --font-2        : "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
    --color-1       : hsla(37, 95%, 57%, 1);
    --color-1-dark  : hsla(37, 95%, 47%, 1);
    --color-2       : hsla(194, 89%, 26%, 1);
    --color-2-dark  : hsla(194, 89%, 16%, 1);
    --color-error-content : hsla(359, 50%, 50%, 1);
    --color-gray-19 : #161616;
    --color-gray-15 : #6e6f6f;
    --color-gray-14 : #838585;
    --color-gray-11 : #c5c8c7;
    --color-gray-9  : #dfe1e0;
    --color-gray-6  : #e9ebeb;
    --color-gray-3  : #f4f5f5;
    --color-white   : #ffffff;
    --color-text    : #161616;
    --vspace-0_5    : 16px;
    --vspace-1      : 32px;
}
"""


def new_id():
    return secrets.token_hex(4)[:7]


def source_page():
    return (SRC / "index5.html").read_text(encoding="utf-8")


def tag_block(tag, needle):
    """The contents of the one <tag> element in index5.html containing `needle`.

    Anchored on content rather than line numbers, which is not a style
    preference: this used to slice fixed line ranges out of the page, and
    adding twelve lines of CSS higher up the same file silently shifted both
    ranges. The templates still built — they just carried a truncated script
    that died with `SyntaxError: Unexpected end of input`, and only the feed
    test caught it.
    """
    found = [m.group(1) for m in re.finditer(rf"<{tag}[^>]*>(.*?)</{tag}>", source_page(), re.S)
             if needle in m.group(1)]
    if len(found) != 1:
        raise SystemExit(f"expected 1 <{tag}> containing {needle!r} in index5.html, found {len(found)}")
    return found[0]


def feed_css():
    """Pull the news-feed stylesheet out of the source page and make it
    self-contained: no theme variables, no rem-scale assumption."""
    css = tag_block("style", ".wp-news {")
    # Drop that block's header comment: it names santaconvocacionlldm.org as
    # the feed source, which is wrong on the English template.
    css = css[css.index("/* --- el reproductor del intro"):]

    # .lite-yt is the old YouTube embed and .s-about__content is the StyleShout
    # container. Neither exists once the layout is Elementor sections.
    css = re.sub(r"\.s-intro__more \.lite-yt[^}]*}", "", css)
    css = re.sub(r"\.s-about__content\s*{[^}]*}", "", css)

    css = REM.sub(lambda m: f"{float(m.group(1)) * 10:g}px", css)
    return FEED_VARS + "\n" + css.strip()


def feed_js(cfg):
    """Same feed script, pointed at the site it is installed on."""
    js = tag_block("script", "wp-news-grid")

    # Same-origin now: an empty base makes every request relative, so the feed
    # keeps working if the domain ever changes.
    js = js.replace("sitio      : 'https://santaconvocacionlldm.org',", "sitio      : '',")
    js = re.sub(r"categoria  : \d+,", f"categoria  : {cfg['category']},", js)

    # The comment above CFG still describes the Spanish category.
    js = re.sub(
        r"\* categoria : .*",
        f"* categoria : {cfg['category']} = \"{cfg['cat_name']}\". Pon null para traer todas.",
        js,
    )
    # The original had no line for `sitio` because it was hard-coded; now that
    # it drives same-origin requests it is worth documenting.
    js = js.replace(
        "         * categoria :",
        "         * sitio     : '' = este mismo sitio (peticiones relativas).\n"
        "         * categoria :",
    )

    # pie() links to CFG.sitio; an empty string would render href="".
    js = js.replace("a.href = CFG.sitio;", "a.href = CFG.sitio || '/';")
    return js.strip()


def gallery_html(cfg):
    """The Instagram grid, pointed at the site being built.

    Only its `data-` attributes are configuration — the markup, CSS and script
    are taken as they are, so this stays a straight copy of the block that
    lldm-fb-sync maintains rather than a fork. The file's own header comment is
    install instructions for a human and is dropped; the endpoint keeps its
    relative default because an Elementor page is served from the same site as
    the Media Library it reads.
    """
    html = (HERE / "ig-gallery.html").read_text(encoding="utf-8")
    html = re.sub(r"\A<!--.*?-->\s*", "", html, flags=re.S)

    # Appearance is custom properties, not data- attributes, so it's lifted out
    # before the loop below and emitted as a rule instead.
    conf = dict(cfg["gallery"])
    title_font = conf.pop("title_font", None)

    for attr, value in conf.items():
        pattern = f'data-{attr}="[^"]*"'
        if not re.search(pattern, html):
            raise SystemExit(f"ig-gallery.html has no data-{attr} attribute")
        # A function replacement: URLs in the config would otherwise have their
        # backslash-and-digit sequences read as group references.
        html = re.sub(pattern, lambda m: f'data-{attr}="{value}"', html, count=1)

    if title_font:
        html = f"<style>\n.hsig {{ --hsig-title-font: {title_font}; }}\n</style>\n\n{html}"

    return html.strip()


def widget(kind, settings):
    return {
        "id": new_id(),
        "elType": "widget",
        "settings": settings,
        "elements": [],
        "widgetType": kind,
    }


def section(settings, widgets, column_settings=None):
    return {
        "id": new_id(),
        "elType": "section",
        "settings": settings,
        "elements": [
            {
                "id": new_id(),
                "elType": "column",
                "settings": {"_column_size": 100, "_inline_size": None,
                             **(column_settings or {})},
                "elements": widgets,
                "isInner": False,
            }
        ],
        "isInner": False,
    }


def socials(links):
    return widget("social-icons", {
        "social_icon_list": [
            {
                "_id": new_id(),
                "social_icon": {"value": f"fab fa-{icon}", "library": "fa-brands"},
                "link": {"url": url, "is_external": "yes", "nofollow": ""},
            }
            for icon, url in links
        ],
        "align": "center",
        "shape": "circle",
        "icon_size": {"unit": "px", "size": 16},
        "icon_padding": {"unit": "em", "size": 0.8},
        "icon_spacing": {"unit": "px", "size": 12},
        "icon_color": "custom",
        "icon_primary_color": "rgba(255,255,255,0.12)",
        "icon_secondary_color": "#ffffff",
    })


# The poster/video frame is the point of the hero, so its size is driven by the
# window rather than fixed. Elementor's width control takes a single number, not
# an expression, so the rule lives here instead: the frame grows with the free
# height of the viewport, floors at the 560px it used to be, and stops at
# 1200px. max-width over aspect-ratio keeps 16:9 at every size, which is what
# lets the <img> be swapped for a video embed later without touching the frame.
#
# Rems are baked to pixels for the same reason as the feed CSS — the source
# stylesheet set html{font-size:62.5%} and the destination theme won't.
HERO_VIDEO_CSS = """<style>
.sc-hero-video img,
.sc-hero-video iframe,
.sc-hero-video video {
    width         : 100%;
    max-width     : max(560px, min(1200px, calc((92vh - 400px) * 16 / 9)));
    height        : auto;
    aspect-ratio  : 16 / 9;
    object-fit    : cover;
    border-radius : 8px;
}
</style>"""


def build(cfg):
    hero_title = cfg["hero_title"].replace("\n", "<br>")

    hero = section(
        {
            "layout": "full_width",
            "height": "min-height",
            "custom_height": {"unit": "vh", "size": 100},
            "content_position": "middle",
            "background_background": "classic",
            "background_image": {"url": cfg["hero_bg"], "id": ""},
            "background_position": "center center",
            "background_size": "cover",
            "background_overlay_background": "classic",
            "background_overlay_color": "#000000",
            "background_overlay_opacity": {"unit": "px", "size": 0.45},
            # Tighter than the 120 it was: the frame below is a good deal
            # bigger now and the section is min-height, so the padding is what
            # decides whether the button still lands above the fold.
            "padding": {"unit": "px", "top": "80", "right": "20",
                        "bottom": "72", "left": "20", "isLinked": False},
        },
        [
            # Renders nothing — it carries HERO_VIDEO_CSS, which Elementor's
            # own controls can't express. Kept inside the hero so the rule
            # travels with the section it styles.
            widget("html", {
                "html": HERO_VIDEO_CSS,
                "_margin": {"unit": "px", "top": "0", "right": "0",
                            "bottom": "0", "left": "0", "isLinked": True},
            }),
            widget("heading", {
                "title": cfg["pretitle"],
                "header_size": "h3",
                "align": "center",
                "title_color": "#ffffff",
                "typography_typography": "custom",
                "typography_font_family": "Inter",
                "typography_font_size": {"unit": "px", "size": 20},
                "typography_font_weight": "500",
                "typography_text_transform": "uppercase",
                "typography_letter_spacing": {"unit": "em", "size": 0.2},
                "_margin": {"unit": "px", "top": "0", "right": "0",
                            "bottom": "16", "left": "0", "isLinked": False},
            }),
            widget("heading", {
                "title": hero_title,
                "header_size": "h1",
                "align": "center",
                "title_color": "#ffffff",
                "typography_typography": "custom",
                # Per-template: the English hero is set in Cinzel, a display
                # face used for that one line and nowhere else. Elementor
                # enqueues the Google Font itself for a typography control, so
                # nothing has to be added to the HTML widget's @import.
                "typography_font_family": cfg.get("title_font", "Lora"),
                # Down from 104: the title yields the stage to the frame below
                # it. The static pages make the same move (6.4rem there).
                "typography_font_size": {"unit": "px", "size": 64},
                "typography_font_size_tablet": {"unit": "px", "size": 48},
                "typography_font_size_mobile": {"unit": "px", "size": 34},
                "typography_font_weight": "700",
                "typography_line_height": {"unit": "em", "size": 1.1154},
                "_margin": {"unit": "px", "top": "0", "right": "0",
                            "bottom": "28", "left": "0", "isLinked": False},
            }),
            widget("image", {
                "image": {"url": cfg["poster"], "id": ""},
                "image_size": "full",
                "align": "center",
                # Sizing is HERO_VIDEO_CSS's job — this control only takes a
                # fixed number, so it stays out of the way at 100%.
                "width": {"unit": "%", "size": 100},
                "_css_classes": "sc-hero-video",
                "image_border_radius": {"unit": "px", "top": "8", "right": "8",
                                        "bottom": "8", "left": "8", "isLinked": True},
                "caption_source": "none",
                "_element_custom_width": "yes",
                "box_shadow_box_shadow_type": "yes",
                "box_shadow_box_shadow": {"horizontal": 0, "vertical": 20,
                                          "blur": 56, "spread": 0,
                                          "color": "rgba(0,0,0,0.45)"},
            }),
            widget("button", {
                "text": cfg["btn"],
                "link": {"url": "#about", "is_external": "", "nofollow": ""},
                "align": "center",
                "size": "md",
                "button_type": "",
                "typography_typography": "custom",
                "typography_font_family": "Inter",
                "typography_font_size": {"unit": "px", "size": 14},
                "typography_font_weight": "600",
                "typography_text_transform": "uppercase",
                "typography_letter_spacing": {"unit": "em", "size": 0.2},
                "background_color": "rgba(0,0,0,0)",
                "button_text_color": "#ffffff",
                "border_border": "solid",
                "border_width": {"unit": "px", "top": "2", "right": "2",
                                 "bottom": "2", "left": "2", "isLinked": True},
                "border_color": "#ffffff",
                "hover_color": "#000000",
                "button_background_hover_color": "#ffffff",
                "_margin": {"unit": "px", "top": "32", "right": "0",
                            "bottom": "0", "left": "0", "isLinked": False},
            }),
            socials(cfg["socials"]),
        ],
    )

    # The feed markup keeps its original ids and classes so the script below it
    # needs no rewiring. #about also serves as the hero button's scroll target.
    feed_html = f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Lora:wght@400;500;600;700&display=swap');
{feed_css()}
</style>

<div id="about">
<div class="wp-news" id="wp-news">

    <button type="button" class="wp-news__fresh" id="wp-news-fresh" hidden>
        {cfg['fresh']}
    </button>

    <div class="wp-news__grid" id="wp-news-grid"></div>

    <p class="wp-news__status" id="wp-news-status" role="status" aria-live="polite">
        {cfg['loading']}
    </p>

    <div class="wp-news__actions">
        <button type="button" class="btn btn--stroke wp-news__more" id="wp-news-more" hidden>
            {cfg['more']}
        </button>
    </div>

    <p class="wp-news__foot" id="wp-news-foot"></p>

</div>
</div>

<script>
{feed_js(cfg)}
</script>"""

    news = section(
        {
            "layout": "boxed",
            "content_width": {"unit": "px", "size": 1240},
            "background_background": "classic",
            "background_color": "#ffffff",
            # A shorter bottom when the gallery follows: that section brings
            # its own 56px band, and the two together left a conspicuous gap
            # between the feed's last line and the first row of photos.
            "padding": {"unit": "px", "top": "96", "right": "20",
                        "bottom": "48" if cfg.get("gallery") else "96",
                        "left": "20", "isLinked": False},
        },
        [
            widget("heading", {
                "title": cfg["news_title"],
                "header_size": "h2",
                "align": "left",
                "title_color": "#000000",
                "typography_typography": "custom",
                # Set per template rather than defaulted: the transform and the
                # letter-spacing have to move together with the face. .2em is
                # spacing for small caps; on the mixed-case Cinzel setting it
                # leaves the words loose.
                "typography_font_family": cfg["news_font"],
                # Matches .hsig-title in the gallery block (30px, 25px on a
                # narrow screen) so the two section headings read as a pair.
                "typography_font_size": {"unit": "px", "size": 30},
                "typography_font_size_mobile": {"unit": "px", "size": 25},
                "typography_line_height": {"unit": "em", "size": 1.2},
                "typography_font_weight": "600",
                "typography_text_transform": cfg["news_transform"],
                "typography_letter_spacing": {"unit": "em", "size": cfg["news_spacing"]},
            }),
            widget("html", {"html": feed_html}),
        ],
    )

    # The block brings its own 56px band, max-width and heading, so the section
    # around it is a bare full-width shell. The heading in particular has to
    # stay inside the widget: the gallery hides itself when the feed is empty
    # or unreachable, and an Elementor heading widget above it would survive
    # that and leave a title over nothing.
    gallery = section(
        {
            "layout": "full_width",
            "background_background": "classic",
            "background_color": "#f4f5f5",
            "padding": {"unit": "px", "top": "0", "right": "0",
                        "bottom": "0", "left": "0", "isLinked": True},
        },
        [widget("html", {"html": gallery_html(cfg)})],
    ) if cfg.get("gallery") else None

    footer = section(
        {
            "layout": "boxed",
            "background_background": "classic",
            "background_color": "#161616",
            "padding": {"unit": "px", "top": "40", "right": "20",
                        "bottom": "40", "left": "20", "isLinked": False},
        },
        [
            widget("heading", {
                "title": cfg["copyright"],
                "header_size": "h6",
                "align": "center",
                "title_color": "rgba(255,255,255,0.6)",
                "typography_typography": "custom",
                "typography_font_family": "Inter",
                "typography_font_size": {"unit": "px", "size": 13},
                "typography_font_weight": "500",
                "typography_text_transform": "uppercase",
                "typography_letter_spacing": {"unit": "em", "size": 0.1},
            }),
        ],
    )

    return {
        "version": "0.4",
        "title": cfg["title"],
        "type": "page",
        "content": [s for s in (hero, news, gallery, footer) if s],
        "page_settings": {
            "hide_title": "yes",
            "background_background": "classic",
            "background_color": "#ffffff",
        },
    }


ES = {
    "title": "Santa Convocación 2026",
    "file": "santa-convocacion-2026-es.json",
    "site": "santaconvocacionlldm.org",
    "category": 11,
    "cat_name": "Santa Convocación",
    "hero_bg": "https://santaconvocacionlldm.org/images/hero-bg.jpg",
    "poster": "https://santaconvocacionlldm.org/images/santacena2026.jpg",
    "pretitle": "SANTA CONVOCACIÓN",
    "hero_title": "Un llamado a la\ncomunión con Cristo.",
    "btn": "Video",
    "title_font": "Cinzel",
    "news_title": "Noticias — Santa Convocación 2026",
    "news_font": "Cinzel",
    "news_transform": "none",
    "news_spacing": 0.06,
    "fresh": "Hay publicaciones nuevas — actualizar",
    "loading": "Cargando publicaciones…",
    "more": "Ver más publicaciones",
    "copyright": "Iglesia La Luz del Mundo | Santa Convocación © Copyright 2026",
    # No "gallery" key on purpose — see the note on EN below.
    "socials": [
        ("facebook", "https://www.facebook.com/SantaConvocacionLLDM"),
        ("x-twitter", "https://x.com/convocacionlldm"),
        ("instagram", "https://www.instagram.com/santaconvocacionlldm/"),
    ],
}

EN = {
    "title": "Holy Supper 2026",
    "file": "holy-supper-2026-en.json",
    "site": "holysupper.org",
    "category": 2,
    "cat_name": "Holy Supper",
    "hero_bg": "https://holysupper.org/images/hero-bg.jpg",
    "poster": "https://holysupper.org/images/holysupper2026.jpg",
    "pretitle": "HOLY SUPPER",
    "hero_title": "A call to\ncommunion with Christ.",
    "title_font": "Cinzel",
    "btn": "Video",
    "news_title": "News — Holy Supper 2026",
    "news_font": "Cinzel",
    "news_transform": "none",
    "news_spacing": 0.06,
    "fresh": "New posts available — refresh",
    "loading": "Loading posts…",
    "more": "See more posts",
    "copyright": "The Light of the World Church | Holy Supper © Copyright 2026",
    # Reads holysupper.org's own Media Library, which lldm-fb-sync's hourly
    # sync-ig-gallery cron stocks from @holysuppertlotw. Only this template has
    # one: santaconvocacionlldm.org has no synced photos, so the same block on
    # the Spanish page would hide itself and ship a section that never appears.
    # Adding the same key there is all it would take once that site is synced.
    "gallery": {
        "count": 12,
        "profile": "https://www.instagram.com/holysuppertlotw/",
        "heading": "Follow us on Instagram",
        "cta": "View on Instagram",
        # Not a data- attribute — see gallery_html.
        "title_font": '"Cinzel", Georgia, serif',
    },
    "socials": [
        ("facebook", "https://www.facebook.com/holysupper"),
        ("x-twitter", "https://x.com/HolySupperTLOTW"),
        ("instagram", "https://www.instagram.com/holysuppertlotw/"),
    ],
}

# The English feed strings live in index5Eng.html; swap them into the script.
EN_STRINGS = {
    "'Sin título'": "'Untitled'",
    "'Leer publicación'": "'Read post'",
    "'Leer publicación: '": "'Read post: '",
    "'Reintentar'": "'Retry'",
    "'Cargando más…'": "'Loading more…'",
    "'Cargando publicaciones…'": "'Loading posts…'",
    "'Todavía no hay publicaciones.'": "'No posts yet.'",
    "'No se pudieron cargar las publicaciones ('": "'Could not load posts ('",
    "'No se pudieron cargar más publicaciones.'": "'Could not load more posts.'",
    "'Mostrando '": "'Showing '",
    "' de '": "' of '",
    "' publicaciones · '": "' posts · '",
    "'ver el sitio completo'": "'visit the full site'",
    "'es-ES'": "'en-US'",
}

for cfg in (ES, EN):
    data = build(cfg)
    if cfg is EN:
        blob = json.dumps(data, ensure_ascii=False)
        for es, en in EN_STRINGS.items():
            blob = blob.replace(es.replace("'", "'"), en.replace("'", "'"))
        data = json.loads(blob)

    path = OUT / cfg["file"]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{path.name:<34} {path.stat().st_size:>8,} bytes  "
          f"cat {cfg['category']} @ {cfg['site']}")
