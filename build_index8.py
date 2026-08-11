#!/usr/bin/env python3
"""
Builds index8.html / index8Eng.html: the live pages plus a "Videos" section.

Why a script rather than hand-editing the two files: they are ~1 MB each and
almost entirely base64, so a hand edit is unreviewable and the Spanish and
English copies drift apart the moment one gets a fix the other doesn't. This
applies the same five edits to both, with only the strings and the two site
constants differing, and it starts from the LIVE pages so the edits Ruben made
on the WordPress side come along.

Run from /root/santacena-elementor:

    python3 build_index8.py                 # uses the pages saved by the fetch step
    python3 build_index8.py --fetch         # re-download both live pages first

The five edits, in the order they're applied:

  1. news feed: exclude the "Video" tag, so a reel no longer shows up twice.
  2. nav: a "Videos" item (and, on the English page, the same #intro -> #about
     fix the Spanish page already got live).
  3. CSS: the section's own block, last in the document on purpose.
  4. markup: <section id="videos"> right after the news section.
  5. JS: the feed that fills it.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE / 'SantaCena'
SCRATCH = Path('/tmp/claude-0/-root/9fccb81d-55be-4e51-ad14-b32b07443d18/scratchpad')


class Page:
    """One language's worth of everything that differs between the two files."""

    def __init__(self, **kw):
        self.__dict__.update(kw)


ES = Page(
    out='index8.html',
    live=SCRATCH / 'live_es.html',
    site='https://santaconvocacionlldm.org',
    video_tag=19,               # "Video" tag id on santaconvocacionlldm.org
    lang='es-ES',
    nav_after='<li><a href="#about" class="smoothscroll">Noticias</a></li>',
    nav_item='<li><a href="#videos" class="smoothscroll">Videos</a></li>',
    pretitle='Videos - Santa Convocación 2026',
    heading='Videos',
    loading='Cargando videos&hellip;',
    loading_js='Cargando videos…',
    loading_more='Cargando más…',
    empty='Todavía no hay videos.',
    more='Ver más videos',
    fresh='Hay videos nuevos — actualizar',
    watch='Ver video',
    watch_aria='Ver video: ',
    err='No se pudieron cargar los videos (',
    err_more='No se pudieron cargar más videos.',
    retry='Reintentar',
    showing='Mostrando ',
    of=' de ',
    items=' videos · ',
    fullsite='ver el sitio completo',
    play_label='Video',
)

EN = Page(
    out='index8Eng.html',
    live=SCRATCH / 'live_en.html',
    site='https://holysupper.org',
    video_tag=9,                # "Video" tag id on holysupper.org
    lang='en-US',
    # The English page still points its News item at #intro; the Spanish one
    # was fixed to #about live. Same defect, so it's corrected here too.
    nav_after='<li><a href="#intro" class="smoothscroll">News</a></li>',
    nav_fix=('<li><a href="#intro" class="smoothscroll">News</a></li>',
             '<li><a href="#about" class="smoothscroll">News</a></li>'),
    nav_item='<li><a href="#videos" class="smoothscroll">Videos</a></li>',
    pretitle='Videos - Holy Supper 2026',
    heading='Videos',
    loading='Loading videos&hellip;',
    loading_js='Loading videos…',
    loading_more='Loading more…',
    empty='No videos yet.',
    more='See more videos',
    fresh='There are new videos — refresh',
    watch='Watch video',
    watch_aria='Watch video: ',
    err="Couldn't load the videos (",
    err_more="Couldn't load more videos.",
    retry='Retry',
    showing='Showing ',
    of=' of ',
    items=' videos · ',
    fullsite='visit the full site',
    play_label='Video',
)


# --------------------------------------------------------------------------
# 3. CSS
# --------------------------------------------------------------------------
CSS = """
<!-- VIDEOS: estilos
================================================== -->
<style>
/* ===================================================================
 * VIDEOS — sección propia, debajo de las noticias.
 *
 * Va la última del documento a propósito: las medias de la hoja de
 * StyleShout no añaden especificidad, así que lo que decide es el orden
 * (la misma razón por la que .s-about__content puede ensancharse).
 *
 * Reparte la paleta de .s-about pero invirtiendo el fondo: allí el suelo
 * es crema y las tarjetas blancas, aquí al revés. Es lo que separa las dos
 * secciones de un vistazo sin meter un color nuevo.
 *
 * Las variables se repiten en vez de subirlas a :root porque están
 * declaradas dentro de .s-about y sacarlas de ahí tocaría la sección de
 * noticias, que funciona.
 * ------------------------------------------------------------------- */
.s-videos {
    --news-bg      : #ffffff;
    --news-card    : #F4F1E7;
    --news-bd      : #D9D4C2;
    --news-ink     : #0F121C;
    --news-text    : #6C6E71;
    --news-soft    : #919296;
    --news-accent  : #9b824a;
    --news-accent-2: #e4b574;
    --news-font    : "Syne", var(--font-2);

    background-color : var(--news-bg);
    padding-top      : var(--vspace-3);
    padding-bottom   : var(--vspace-3);
}

.s-videos__content {
    max-width : 1720px;
    width     : 92%;
}

@media screen and (min-width: 1900px) {
    .s-videos__content { width: 88%; }
}

.s-videos .text-pretitle {
    font-family    : var(--news-font);
    color          : var(--news-accent);
    letter-spacing : .06em;
}

.wp-videos {
    margin-top : var(--vspace-1);
    text-align : left;
    color      : var(--news-text);
}

/* Las tarjetas son las mismas piezas que las noticias (.wp-news__card y
   compañía siguen aplicando), así que aquí sólo va lo propio del video:
   el retículo, la chapa de reproducir y la duración del hueco. */
.wp-videos__grid {
    display               : grid;
    grid-template-columns : repeat(4, minmax(0, 1fr));
    gap                   : 3.2rem;
    margin                : 0;
    padding               : 0;
    list-style            : none;
}

/* 16:9 y no el 16:10 de las noticias porque es exactamente la forma en que
   Facebook entrega estos fotogramas (1280x720, comprobado en la API): con
   cualquier otra proporción object-fit:cover recorta, y varios de estos
   fotogramas ya traen sus propias bandas negras de un reel vertical, así que
   el recorte se comería la imagen de verdad. */
.wp-videos .wp-news__thumb { aspect-ratio: 16 / 9; }

/* La chapa de reproducir. Va sobre el enlace de la miniatura, que ya es
   position:relative, y no intercepta el clic (pointer-events:none) para que
   toda la miniatura siga siendo un solo objetivo. */
.wp-videos__play {
    position       : absolute;
    top            : 50%;
    left           : 50%;
    transform      : translate(-50%, -50%);
    width          : 6.4rem;
    height         : 6.4rem;
    border-radius  : 50%;
    background     : rgba(15, 18, 28, .55);
    border         : 2px solid rgba(255, 255, 255, .9);
    display        : flex;
    align-items    : center;
    justify-content: center;
    pointer-events : none;
    transition     : background-color .25s ease-out, transform .25s ease-out;
}

.wp-videos__play::before {
    content      : "";
    display      : block;
    width        : 0;
    height       : 0;
    margin-left  : .6rem;              /* centra el triángulo en el círculo */
    border-left  : 1.8rem solid #ffffff;
    border-top   : 1.1rem solid transparent;
    border-bottom: 1.1rem solid transparent;
}

.wp-news__card:hover .wp-videos__play,
.wp-news__card:focus-within .wp-videos__play {
    background : var(--news-accent);
    transform  : translate(-50%, -50%) scale(1.08);
}

/* El fondo de esta sección es blanco, así que las tarjetas necesitan su
   propio color: .wp-news__card lo toma de --news-card, que aquí ya está
   invertido, pero el marcador de "sin imagen" lleva su degradado propio. */
.wp-videos .wp-news__thumb--empty {
    background : linear-gradient(135deg, var(--news-ink), #2b2f3d);
}

.wp-videos__status {
    margin-top : var(--vspace-1);
    font-size  : 1.5rem;
    color      : var(--news-soft);
}

.wp-videos__status[hidden] { display: none; }
.wp-videos__status--error  { color: var(--color-error-content); }

.wp-videos__retry {
    margin-left    : 1.2rem;
    padding        : .4rem 1.6rem;
    font-size      : 1.3rem;
    line-height    : 2.4rem;
    height         : auto;
    margin-bottom  : 0;
    letter-spacing : .02em;
    background     : transparent;
    border         : 1px solid var(--news-bd);
    color          : var(--news-accent);
}

.wp-videos__skeleton {
    min-height       : 26rem;
    background-color : var(--news-card);
    border           : 1px solid var(--news-bd);
    animation        : wp-news-shimmer 1.4s ease-in-out infinite;
}

.wp-videos__actions {
    margin-top : var(--vspace-1);
    text-align : center;
}

.wp-videos__more[hidden] { display: none; }

/* StyleShout tiene una regla global para `button` (padding lateral de 36px,
   margen inferior y letter-spacing) que alcanza a estos botones igual que
   alcanzaba a los de la galería. Se reafirma lo que hace falta en vez de
   confiar en que no llegue. */
.wp-videos__more.btn--stroke {
    margin-bottom : 0;
    border-color  : var(--news-accent);
    color         : var(--news-accent);
}

.wp-videos__more.btn--stroke:hover,
.wp-videos__more.btn--stroke:focus {
    background-color : var(--news-accent);
    border-color     : var(--news-accent);
    color            : #ffffff;
}

.wp-videos__foot {
    margin-top : 1.6rem;
    font-size  : 1.4rem;
    color      : var(--news-soft);
    text-align : center;
}

.wp-videos__foot a { color: var(--news-accent); }

@media screen and (max-width: 1400px) {
    .wp-videos__grid { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 2.4rem; }
}

@media screen and (max-width: 1000px) {
    .wp-videos__grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media screen and (max-width: 600px) {
    .wp-videos__grid { grid-template-columns: 1fr; }
    .wp-videos__play { width: 5.6rem; height: 5.6rem; }
}

@media (prefers-reduced-motion: reduce) {
    .wp-videos__play,
    .wp-videos__skeleton { transition: none; animation: none; }
}
</style>
"""


# --------------------------------------------------------------------------
# 4. markup
# --------------------------------------------------------------------------
MARKUP = """
            <!-- videos
            ----------------------------------------------- -->
            <section id="videos" class="s-videos target-section">

                <div class="row s-videos__content" data-animate-block>
                    <div class="column lg-12">
                        <h2 class="text-pretitle" data-animate-el>{pretitle}</h2>
                        <div class="wp-videos" id="wp-videos">

                            <div class="wp-videos__grid" id="wp-videos-grid"></div>

                            <p class="wp-videos__status" id="wp-videos-status" role="status" aria-live="polite">
                                {loading}
                            </p>

                            <div class="wp-videos__actions">
                                <button type="button" class="btn btn--stroke wp-videos__more" id="wp-videos-more" hidden>
                                    {more}
                                </button>
                            </div>

                            <p class="wp-videos__foot" id="wp-videos-foot"></p>

                        </div> <!-- end wp-videos -->
                    </div> <!-- end column  -->
                </div> <!-- end s-videos__content  -->

            </section> <!-- end videos -->
"""


# --------------------------------------------------------------------------
# 5. JS
# --------------------------------------------------------------------------
JS = """
    <!-- VIDEOS DINÁMICOS
    ==================================================
    La misma API REST que las noticias, filtrada por la etiqueta "Video"
    (`tags={tag}`). Quien pone esa etiqueta es el bot de lldm-fb-sync: al
    sincronizar mira el permalink de Facebook y, si es un reel / watch /
    videos, etiqueta la entrada — ver resolveVideoTags en wordpress.js.

    Por eso el listado de noticias de arriba lleva `tags_exclude={tag}`: sin
    eso el mismo reel saldría en las dos secciones.

    Bloque aparte del de noticias, y no una segunda instancia de aquél, porque
    aquí no hay destacada ni laterales: es un retículo y ya. Reutiliza sus
    clases de tarjeta (.wp-news__card), no su código.
    ================================================== -->
    <script>
    (function () {{
        'use strict';

        var CFG = {{
            sitio      : '{site}',
            etiqueta   : {tag},          // id de la etiqueta "Video" en este sitio
            porPagina  : 8,
            refrescoMs : 5 * 60 * 1000
        }};

        var grid   = document.getElementById('wp-videos-grid');
        var status = document.getElementById('wp-videos-status');
        var more   = document.getElementById('wp-videos-more');
        var foot   = document.getElementById('wp-videos-foot');

        if (!grid) {{ return; }}

        var seccion = document.getElementById('videos');
        var enlaceNav = document.querySelector('.header-nav a[href="#videos"], .header-nav__list a[href="#videos"]');

        var state = {{
            pintadas     : 0,
            total        : 0,
            masReciente  : null,
            cargando     : false,
            ultimaMirada : 0
        }};

        var scratch = document.createElement('div');
        function aTexto(html) {{
            scratch.innerHTML = html || '';
            return (scratch.textContent || '').replace(/\\s+/g, ' ').trim();
        }}

        function recortar(texto, max) {{
            if (texto.length <= max) {{ return texto; }}
            var corte = texto.slice(0, max);
            var esp = corte.lastIndexOf(' ');
            return (esp > max * 0.6 ? corte.slice(0, esp) : corte) + '…';
        }}

        function fecha(iso) {{
            var d = new Date(iso);
            if (isNaN(d)) {{ return ''; }}
            try {{
                return d.toLocaleDateString('{lang}', {{
                    day: 'numeric', month: 'long', year: 'numeric'
                }});
            }} catch (e) {{
                return d.toISOString().slice(0, 10);
            }}
        }}

        function imagen(post) {{
            var emb = post._embedded && post._embedded['wp:featuredmedia'];
            var media = emb && emb[0];
            if (!media || media.code) {{ return null; }}
            var sizes = (media.media_details && media.media_details.sizes) || {{}};
            var pick = sizes.medium_large || sizes.large || sizes.medium || null;
            return {{
                src: (pick && pick.source_url) || media.source_url || null,
                alt: aTexto(media.alt_text || '')
            }};
        }}

        function url(desde, cuantas) {{
            var q = [
                'per_page=' + cuantas,
                'offset=' + desde,
                'orderby=date',
                'order=desc',
                'tags=' + CFG.etiqueta,
                '_embed=wp:featuredmedia',
                '_fields=id,link,date,title,excerpt,_links'
            ];
            return CFG.sitio + '/wp-json/wp/v2/posts?' + q.join('&');
        }}

        function traer(desde, cuantas) {{
            return fetch(url(desde, cuantas), {{ credentials: 'omit' }})
                .then(function (r) {{
                    if (!r.ok) {{ throw new Error('HTTP ' + r.status); }}
                    return r.json().then(function (datos) {{
                        return {{
                            posts : datos,
                            total : parseInt(r.headers.get('X-WP-Total'), 10) || datos.length
                        }};
                    }});
                }});
        }}

        /* --- pintado -------------------------------------------------------- */

        function miniatura(post) {{
            var enlace = document.createElement('a');
            enlace.className = 'wp-news__thumb';
            enlace.href = post.link;
            enlace.setAttribute('aria-hidden', 'true');
            enlace.setAttribute('tabindex', '-1');

            var img = imagen(post);
            if (img && img.src) {{
                var el = document.createElement('img');
                el.src = img.src;
                el.alt = img.alt || '';
                el.loading = 'lazy';
                el.decoding = 'async';
                enlace.appendChild(el);
            }} else {{
                enlace.className += ' wp-news__thumb--empty';
                enlace.textContent = 'LLDM';
            }}

            var play = document.createElement('span');
            play.className = 'wp-videos__play';
            enlace.appendChild(play);
            return enlace;
        }}

        function tarjeta(post) {{
            var art = document.createElement('article');
            art.className = 'wp-news__card wp-news__card--grid';

            var titulo = aTexto(post.title && post.title.rendered) || 'Sin título';

            var cuerpo = document.createElement('div');
            cuerpo.className = 'wp-news__body';

            var f = document.createElement('p');
            f.className = 'wp-news__date';
            f.textContent = fecha(post.date);

            var h = document.createElement('h4');
            h.className = 'wp-news__title';
            var ha = document.createElement('a');
            ha.href = post.link;
            ha.textContent = titulo;
            h.appendChild(ha);

            cuerpo.appendChild(f);
            cuerpo.appendChild(h);

            /* Sin resumen, a diferencia del retículo de noticias. El excerpt
             * que genera WordPress sale del cuerpo de la entrada, y el cuerpo
             * de un video es la leyenda (cuya primera línea ya es el titular)
             * seguida del texto de reserva del embed — así que la tarjeta
             * repetía su propio título y remataba con "Ver la publicación
             * original en Facebook Ver en Facebook". Las laterales de noticias
             * tampoco lo llevan, o sea que esto no es una excepción. */

            var ver = document.createElement('a');
            ver.className = 'wp-news__link';
            ver.href = post.link;
            ver.textContent = '{watch}';
            ver.setAttribute('aria-label', '{watch_aria}' + titulo);
            cuerpo.appendChild(ver);

            art.appendChild(miniatura(post));
            art.appendChild(cuerpo);
            return art;
        }}

        function pintar(posts, anexar) {{
            if (!anexar) {{ grid.innerHTML = ''; state.pintadas = 0; }}
            var frag = document.createDocumentFragment();
            posts.forEach(function (post) {{ frag.appendChild(tarjeta(post)); }});
            grid.appendChild(frag);
            state.pintadas += posts.length;
        }}

        function esqueletos() {{
            var frag = document.createDocumentFragment();
            for (var i = 0; i < CFG.porPagina; i++) {{
                var s = document.createElement('div');
                s.className = 'wp-videos__skeleton';
                frag.appendChild(s);
            }}
            grid.appendChild(frag);
        }}

        function limpiarEsqueletos() {{
            var s = grid.querySelectorAll('.wp-videos__skeleton');
            for (var i = 0; i < s.length; i++) {{ s[i].parentNode.removeChild(s[i]); }}
        }}

        function mensaje(texto, esError, conReintento) {{
            status.hidden = !texto;
            status.textContent = texto || '';
            status.className = 'wp-videos__status' + (esError ? ' wp-videos__status--error' : '');
            if (conReintento) {{
                var b = document.createElement('button');
                b.type = 'button';
                b.className = 'wp-videos__retry';
                b.textContent = '{retry}';
                b.addEventListener('click', function () {{
                    if (state.pintadas) {{ cargarMas(); }} else {{ cargar(); }}
                }});
                status.appendChild(b);
            }}
        }}

        function pie() {{
            if (!state.total) {{ foot.textContent = ''; return; }}
            foot.textContent = '{showing}' + state.pintadas + '{of}' + state.total + '{items}';
            var a = document.createElement('a');
            a.href = CFG.sitio;
            a.textContent = '{fullsite}';
            foot.appendChild(a);
        }}

        function repasarBotonMas() {{
            more.hidden = state.pintadas >= state.total;
        }}

        /* La sección entera se esconde mientras no haya ni un video, igual que
         * hace la galería de Instagram en index5Eng: un sitio sin reels no
         * debe enseñar un titular "Videos" sobre un hueco vacío, y el enlace
         * del menú tampoco debe llevar a la nada. */
        function visible(si) {{
            if (seccion) {{ seccion.hidden = !si; }}
            if (enlaceNav && enlaceNav.parentNode) {{ enlaceNav.parentNode.hidden = !si; }}
        }}

        /* --- carga ----------------------------------------------------------- */

        function cargar() {{
            if (state.cargando) {{ return; }}
            state.cargando = true;
            more.disabled = true;

            grid.innerHTML = '';
            state.pintadas = 0;
            esqueletos();
            mensaje('{loading_js}');

            traer(0, CFG.porPagina).then(function (res) {{
                limpiarEsqueletos();
                state.total = res.total;
                state.ultimaMirada = Date.now();

                if (!res.posts.length) {{
                    visible(false);
                    mensaje('{empty}');
                    more.hidden = true;
                    foot.textContent = '';
                    return;
                }}

                visible(true);
                state.masReciente = res.posts[0].id;
                pintar(res.posts, false);
                mensaje('');
                repasarBotonMas();
                pie();
            }}).catch(function (err) {{
                limpiarEsqueletos();
                // Un fallo de red no es lo mismo que "no hay videos": si ya
                // había algo pintado se deja a la vista y sólo se avisa.
                if (!state.pintadas) {{ visible(false); }}
                mensaje('{err}' + err.message + ').', true, true);
            }}).then(function () {{
                state.cargando = false;
                more.disabled = false;
            }});
        }}

        function cargarMas() {{
            if (state.cargando) {{ return; }}
            state.cargando = true;
            more.disabled = true;
            mensaje('{loading_more}');

            traer(state.pintadas, CFG.porPagina).then(function (res) {{
                state.total = res.total;
                pintar(res.posts, true);
                mensaje('');
                repasarBotonMas();
                pie();
            }}).catch(function () {{
                mensaje('{err_more}', true, true);
            }}).then(function () {{
                state.cargando = false;
                more.disabled = false;
            }});
        }}

        function mirarNovedades() {{
            if (state.cargando || document.hidden) {{ return; }}
            state.ultimaMirada = Date.now();

            traer(0, 1).then(function (res) {{
                var nuevo = res.posts[0];
                // Sin masReciente todavía (la primera carga no encontró nada)
                // cualquier video nuevo tiene que entrar: es lo que resucita la
                // sección en cuanto se publica el primero.
                if (!nuevo) {{ return; }}
                if (nuevo.id === state.masReciente) {{
                    if (res.total !== state.total) {{
                        state.total = res.total;
                        repasarBotonMas();
                        pie();
                    }}
                    return;
                }}
                if (state.pintadas <= CFG.porPagina) {{ cargar(); }}
            }}).catch(function () {{ /* sin conexión: al siguiente ciclo */ }});
        }}

        /* --- arranque -------------------------------------------------------- */

        more.addEventListener('click', cargarMas);

        setInterval(mirarNovedades, CFG.refrescoMs);

        document.addEventListener('visibilitychange', function () {{
            if (!document.hidden && Date.now() - state.ultimaMirada > 60000) {{ mirarNovedades(); }}
        }});
        window.addEventListener('online', mirarNovedades);

        // Escondida de entrada: si el sitio no tiene videos, el visitante no
        // llega a ver aparecer y desaparecer la sección.
        visible(false);
        cargar();
    }})();
    </script>
"""


def js(text: str) -> str:
    """Escape a UI string for a single-quoted JS literal.

    Not cosmetic: the English copy says "Couldn't load the videos", and pasting
    that straight into '...' ends the string at the apostrophe and leaves the
    rest as code — the whole videos block then fails to parse and the section
    silently never loads. The Spanish strings happen to have no apostrophes,
    so this is exactly the kind of break that ships in one language only.
    """
    return text.replace('\\', '\\\\').replace("'", "\\'")


def edit(page: Page) -> str:
    html = page.live.read_text(encoding='utf-8')
    before = len(html)

    def replace_once(needle, replacement, what):
        nonlocal html
        n = html.count(needle)
        if n != 1:
            sys.exit(f'{page.out}: expected exactly 1 match for {what}, found {n}')
        html = html.replace(needle, replacement, 1)

    # 1. news feed excludes the Video tag
    replace_once(
        "                '_fields=id,link,date,title,excerpt,_links'\n            ];",
        "                '_fields=id,link,date,title,excerpt,_links',\n"
        "                // Los videos tienen su propia sección más abajo. Sin esto\n"
        "                // cada reel saldría en las dos, porque la etiqueta no quita\n"
        "                // la entrada de su categoría.\n"
        f"                'tags_exclude={page.video_tag}'\n            ];",
        'the news url() field list',
    )

    # 2. nav
    if getattr(page, 'nav_fix', None):
        replace_once(page.nav_fix[0], page.nav_fix[1], 'the News nav target (#intro -> #about)')
        anchor = page.nav_fix[1]
    else:
        anchor = page.nav_after
    replace_once(anchor, anchor + '\n                    ' + page.nav_item, 'the nav anchor item')

    # 3. CSS — last in the document, just before </head>
    replace_once('</head>', CSS + '\n</head>', '</head>')

    # 4. markup — right after the news section
    replace_once(
        '            </section> <!-- end about -->',
        '            </section> <!-- end about -->\n'
        + MARKUP.format(pretitle=page.pretitle, loading=page.loading, more=page.more),
        'the end of the news section',
    )

    # 5. JS — before </body>, after the news script
    replace_once(
        '</body>',
        JS.format(
            site=js(page.site), tag=page.video_tag, lang=js(page.lang),
            watch=js(page.watch), watch_aria=js(page.watch_aria), retry=js(page.retry),
            showing=js(page.showing), of=js(page.of), items=js(page.items),
            fullsite=js(page.fullsite),
            loading_js=js(page.loading_js), loading_more=js(page.loading_more),
            empty=js(page.empty), err=js(page.err), err_more=js(page.err_more),
        ) + '\n</body>',
        '</body>',
    )

    out = REPO / page.out
    out.write_text(html, encoding='utf-8')
    print(f'{page.out}: {before:,} -> {len(html):,} bytes (+{len(html) - before:,})')
    return html


def fetch():
    for page, url in ((ES, ES.site + '/'), (EN, EN.site + '/')):
        subprocess.run(['curl', '-sS', '-o', str(page.live), url], check=True)
        print(f'fetched {url} -> {page.live} ({page.live.stat().st_size:,} bytes)')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--fetch', action='store_true', help='re-download the live pages first')
    args = ap.parse_args()

    if args.fetch:
        fetch()
    for page in (ES, EN):
        edit(page)
