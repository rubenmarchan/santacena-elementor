/* Run the news-feed widget out of the generated Elementor template inside a
 * fake WordPress page and check it actually paints cards.
 *
 * The point of the harness is the two things most likely to break in the port:
 *   1. the feed now uses relative /wp-json URLs (same-origin), and
 *   2. the CSS no longer relies on html{font-size:62.5%}.
 * So the page here is served from the real domain and left at 16px root.
 */

const fs = require('fs');
const { JSDOM, VirtualConsole } = require('jsdom');

const TEMPLATES = [
    { file: 'out/santa-convocacion-2026-es.json', origin: 'https://santaconvocacionlldm.org', expectCat: '11' },
    { file: 'out/holy-supper-2026-en.json',       origin: 'https://holysupper.org',           expectCat: '2'  },
];

function htmlWidget(template) {
    const found = [];
    (function walk(els) {
        for (const el of els) {
            if (el.widgetType === 'html') found.push(el.settings.html);
            walk(el.elements || []);
        }
    })(JSON.parse(fs.readFileSync(template)).content);
    if (found.length !== 1) throw new Error(`expected 1 html widget, got ${found.length}`);
    return found[0];
}

async function run({ file, origin, expectCat }) {
    console.log(`\n=== ${file} ===`);
    const widget = htmlWidget(file);

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

    await new Promise(r => setTimeout(r, 8000));

    const doc = dom.window.document;
    const cards = doc.querySelectorAll('.wp-news__card');
    const status = doc.getElementById('wp-news-status');
    const foot = doc.getElementById('wp-news-foot');

    console.log('  request URL      :', requested[0] || '(none)');
    console.log('  relative in src  :', /categories=/.test(requested[0] || '') &&
                                        (requested[0] || '').includes(origin));
    console.log('  category sent    :', (requested[0] || '').match(/categories=(\d+)/)?.[1],
                                        `(expected ${expectCat})`);
    console.log('  cards rendered   :', cards.length);
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

(async () => {
    let total = 0;
    for (const t of TEMPLATES) total += await run(t);
    console.log(total > 0 ? '\nPASS — feed renders cards from live WP data'
                          : '\nFAIL — no cards rendered');
    process.exit(total > 0 ? 0 : 1);
})();
