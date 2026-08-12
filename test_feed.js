/* Run the HTML widgets out of the generated Elementor templates inside a fake
 * WordPress page and check they actually paint against live data.
 *
 * The point of the harness is the two things most likely to break in the port:
 *   1. the feed now uses relative /wp-json URLs (same-origin), and
 *   2. the CSS no longer relies on html{font-size:62.5%}.
 * So the page here is served from the real domain and left at 16px root.
 *
 * The Instagram gallery, where a template has one, gets the same treatment —
 * it reads a different endpoint (/wp-json/wp/v2/media) but has the same two
 * exposures, plus one of its own: it hides itself when the feed returns
 * nothing, so "no error" is not the same as "it worked" and only a tile count
 * settles it.
 */

const fs = require('fs');
const { JSDOM, VirtualConsole } = require('jsdom');

const TEMPLATES = [
    { file: 'out/santa-convocacion-2026-es.json', origin: 'https://santaconvocacionlldm.org', expectCat: '11', expectTag: '19', gallery: true },
    { file: 'out/holy-supper-2026-en.json',       origin: 'https://holysupper.org',           expectCat: '2',  expectTag: '9',  gallery: true },
];

function htmlWidget(template, marker) {
    const found = [];
    (function walk(els) {
        for (const el of els) {
            if (el.widgetType === 'html' && el.settings.html.includes(marker)) found.push(el.settings.html);
            walk(el.elements || []);
        }
    })(JSON.parse(fs.readFileSync(template)).content);
    if (found.length !== 1) throw new Error(`expected 1 html widget matching ${marker}, got ${found.length}`);
    return found[0];
}

/* Parse a widget in a page served from `origin` and let its fetches settle. */
function mount(widget, origin) {
    const virtualConsole = new VirtualConsole();
    virtualConsole.on('jsdomError', e => console.log('  [jsdom]', e.message));

    // jsdom ships no fetch, and the widget calls it during parse — so it has to
    // be in place before the inline <script> runs.
    const requested = [];
    const installFetch = window => {
        window.fetch = (url, opts) => {
            const abs = new window.URL(url, origin).href;
            requested.push(abs);
            return fetch(abs, opts).then(r =>
                r.text().then(body => ({
                    ok: r.ok,
                    status: r.status,
                    headers: { get: k => r.headers.get(k) },
                    json: () => Promise.resolve(JSON.parse(body)),
                }))
            );
        };
    };

    const dom = new JSDOM(
        `<!doctype html><html><head><style>html{font-size:16px}</style></head>
         <body><div class="entry-content">${widget}</div></body></html>`,
        {
            url: origin + '/santa-cena-2026/',
            runScripts: 'dangerously',
            pretendToBeVisual: true,
            virtualConsole,
            beforeParse: installFetch,
        }
    );

    return { dom, requested, settled: new Promise(r => setTimeout(r, 8000)) };
}

async function run({ file, origin, expectCat, expectTag }) {
    console.log(`\n=== ${file} ===`);
    // Anchored on the block's own id, not the bare string "wp-news": since
    // index8 the videos widget reuses the .wp-news__card pieces deliberately,
    // so a substring match finds two widgets and this threw.
    const widget = htmlWidget(file, 'id="wp-news"');

    const { dom, requested, settled } = mount(widget, origin);
    await settled;

    const doc = dom.window.document;
    const cards = doc.querySelectorAll('.wp-news__card');
    const status = doc.getElementById('wp-news-status');
    const foot = doc.getElementById('wp-news-foot');

    // The two blocks the layout is made of. Counting only .wp-news__card would
    // still pass if the featured block never painted and everything fell into
    // the grid, which is exactly the failure the port could introduce.
    const main = doc.querySelectorAll('.wp-news__card--main');
    const side = doc.querySelectorAll('.wp-news__card--side');
    const grid = doc.querySelectorAll('.wp-news__card--grid');

    // offset=4 is what stops the grid repeating the four above it.
    const links = [...cards].map(c => c.querySelector('.wp-news__title a')?.href || '');
    const repetidas = links.length - new Set(links).size;

    console.log('  request URL      :', requested[0] || '(none)');
    console.log('  relative in src  :', /categories=/.test(requested[0] || '') &&
                                        (requested[0] || '').includes(origin));
    console.log('  category sent    :', (requested[0] || '').match(/categories=(\d+)/)?.[1],
                                        `(expected ${expectCat})`);
    console.log('  offset sent      :', (requested[0] || '').match(/offset=(\d+)/)?.[1], '(expected 0 on first load)');
    console.log('  cards rendered   :', cards.length,
                `(main ${main.length}, side ${side.length}, grid ${grid.length})`);
    console.log('  duplicate posts  :', repetidas);
    console.log('  grid heading     :', JSON.stringify(doc.getElementById('wp-news-grid-title')?.textContent?.trim()),
                'hidden:', doc.getElementById('wp-news-grid-title')?.hidden);
    console.log('  palette scoped   :', /\.wp-news \{[^}]*--news-bg/.test(widget));

    // Per-site, and only ever correct on the Spanish template by accident: the
    // builder reads the Spanish page for both, so an unrewritten tags_exclude
    // ships the ES Video tag to the EN site and every video lists twice. The
    // duplicate count above cannot see it — the repeats are across sections.
    const excluded = (requested[0] || '').match(/tags_exclude=(\d+)/)?.[1];
    console.log('  videos excluded  :', excluded, `(expected ${expectTag})`);

    if (main.length !== 1 || side.length !== 3 || grid.length < 1 || repetidas > 0) {
        console.log('  ** LAYOUT WRONG: expected 1 main + 3 side + a grid, with no repeats');
        return 0;
    }
    if (excluded !== expectTag) {
        console.log(`  ** WRONG EXCLUDE: news is hiding tag ${excluded}, so tag ${expectTag} videos will appear twice`);
        return 0;
    }
    console.log('  status text      :', JSON.stringify((status.textContent || '').trim()));
    console.log('  footer text      :', JSON.stringify((foot.textContent || '').trim()));

    if (cards.length) {
        const c = cards[0];
        console.log('  first card date  :', c.querySelector('.wp-news__date')?.textContent);
        console.log('  first card title :', c.querySelector('.wp-news__title')?.textContent?.slice(0, 70));
        console.log('  first card link  :', c.querySelector('.wp-news__link')?.textContent);
        console.log('  has thumbnail    :', !!c.querySelector('.wp-news__thumb img'));
        console.log('  thumb src        :', c.querySelector('.wp-news__thumb img')?.src?.slice(0, 80));
    }
    dom.window.close();
    return cards.length;
}

async function runVideos({ file, origin, expectTag }) {
    console.log(`\n=== ${file} — videos ===`);
    const widget = htmlWidget(file, 'id="wp-videos"');

    const { dom, requested, settled } = mount(widget, origin);
    await settled;

    const doc = dom.window.document;
    // Scoped to #wp-videos on purpose: the cards carry .wp-news__card classes,
    // so an unscoped query would silently pass on the news block's markup if
    // the two widgets ever ended up mounted together.
    const root = doc.getElementById('wp-videos');
    const cards = root.querySelectorAll('.wp-news__card');
    const url = requested[0] || '';

    console.log('  request URL      :', url || '(none)');
    console.log('  tag sent         :', url.match(/tags=(\d+)/)?.[1], `(expected ${expectTag})`);
    console.log('  same-origin      :', url.startsWith(origin));
    console.log('  cards rendered   :', cards.length);
    console.log('  status text      :', JSON.stringify(doc.getElementById('wp-videos-status')?.textContent?.trim()));

    if (cards.length) {
        const c = cards[0];
        console.log('  first card title :', c.querySelector('.wp-news__title')?.textContent?.slice(0, 60));
        console.log('  has thumbnail    :', !!c.querySelector('.wp-news__thumb img'));
        // The play badge is the one piece the videos block adds over a news
        // card; without it a video renders as an ordinary article.
        console.log('  play badge       :', !!root.querySelector('.wp-videos__play'));
    }

    // A wrong tag id still paints cards — they are just the wrong posts — so
    // this is checked separately from whether anything rendered at all.
    if (url && url.match(/tags=(\d+)/)?.[1] !== expectTag) {
        console.log('  ** WRONG TAG: this feed is pulling someone else\'s posts');
        dom.window.close();
        return 0;
    }
    dom.window.close();
    return cards.length;
}

async function runGallery({ file, origin }) {
    console.log(`\n=== ${file} — instagram gallery ===`);
    const widget = htmlWidget(file, 'class="hsig"');

    const { dom, requested, settled } = mount(widget, origin);
    await settled;

    const doc = dom.window.document;
    const root = doc.querySelector('.hsig');
    const tiles = doc.querySelectorAll('.hsig-tile');

    console.log('  request URL      :', requested[0] || '(none)');
    console.log('  section revealed :', root && !root.hasAttribute('hidden'));
    console.log('  tiles rendered   :', tiles.length, `(data-count ${root?.dataset.count})`);
    console.log('  heading          :', JSON.stringify(doc.querySelector('.hsig-title')?.textContent));
    console.log('  profile link     :', doc.querySelector('.hsig-handle')?.href);

    if (tiles.length) {
        const img = tiles[0].querySelector('img');
        console.log('  first tile src   :', img?.getAttribute('src')?.slice(0, 80));
        console.log('  first tile srcset:', !!img?.getAttribute('srcset'));
        console.log('  first tile alt   :', JSON.stringify(img?.getAttribute('alt')?.slice(0, 60)));
        // The lightbox link is the one field WordPress mangles on the way out
        // (wptexturize turns -- into an en dash), so check every permalink is
        // a real Instagram URL rather than trusting the first one.
        // One lightbox serves every tile, so the href has to be read after each
        // click rather than collected from the DOM in one sweep.
        const lbLink = doc.querySelector('.hsig-lb-link');
        const links = [...tiles].map(t => { t.click(); return lbLink.getAttribute('href') || ''; });
        const bad = links.filter(h => !/^https:\/\/www\.instagram\.com\/(p|reel|tv)\/[\w-]+\/$/.test(h));
        console.log('  permalinks ok    :', bad.length === 0, bad.length ? bad : '');
    }
    dom.window.close();
    return tiles.length;
}

(async () => {
    let cards = 0;
    let tiles = 0;
    let videos = 0;
    // Per template, not a running total: summing let a template that painted
    // nothing pass on the strength of the other one's cards.
    const rotos = [];
    for (const t of TEMPLATES) {
        const n = await run(t);
        cards += n;
        if (n === 0) rotos.push(t.file);
        if (t.expectTag) {
            const v = await runVideos(t);
            videos += v;
            if (v === 0) rotos.push(t.file + ' (videos)');
        }
        if (t.gallery) {
            const g = await runGallery(t);
            tiles += g;
            if (g === 0) rotos.push(t.file + ' (gallery)');
        }
    }
    const ok = rotos.length === 0;
    console.log(ok ? `\nPASS — ${cards} news cards, ${videos} video cards and ${tiles} gallery tiles from live WP data`
                   : `\nFAIL — nothing painted in: ${rotos.join(', ')}`);
    process.exit(ok ? 0 : 1);
})();
