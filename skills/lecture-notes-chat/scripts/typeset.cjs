/* Only this trusted program executes JS; author HTML never does.
 * MathJax is an external, pinned dependency (Apache-2.0); no font files bundled.
 * Optional MATHJAX_MODULE_ROOT names an already installed mathjax-full directory.
 */
'use strict';
const fs = require('fs');
const path = require('path');
const root = process.env.MATHJAX_MODULE_ROOT;
function mj(file) { return require(root ? path.join(root, file) : 'mathjax-full/' + file); }
try {
  const version = mj('package.json').version;
  if (version !== '3.2.1') throw new Error('MATHJAX_VERSION: expected 3.2.1');
  const {mathjax} = mj('js/mathjax.js');
  const {TeX} = mj('js/input/tex.js');
  const {SVG} = mj('js/output/svg.js');
  const {liteAdaptor} = mj('js/adaptors/liteAdaptor.js');
  const {RegisterHTMLHandler} = mj('js/handlers/html.js');
  const {SerializedMmlVisitor} = mj('js/core/MmlTree/SerializedMmlVisitor.js');
  mj('js/input/tex/ams/AmsConfiguration.js');
  const adaptor = liteAdaptor();
  RegisterHTMLHandler(adaptor);
  const input = JSON.parse(fs.readFileSync(0, 'utf8'));
  if (!Array.isArray(input)) throw new Error('EXPECTED_ARRAY');
  const result = input.map((item, i) => {
    if (typeof item.latex !== 'string' || !item.latex.trim() ||
        item.latex.length > 20000 || typeof item.display !== 'boolean')
      throw new Error(`INVALID_MATH at index ${i}`);
    // Only base+AMS: no require/autoload, external URLs, arbitrary HTML or shared macros.
    const tex = new TeX({packages: ['base', 'ams'], maxBuffer: 20000,
                        formatError: (_jax, e) => { throw e; }});
    const svg = new SVG({fontCache: 'none'});
    const doc = mathjax.document('', {InputJax: tex, OutputJax: svg,
      compileError: (_doc, _math, e) => { throw e; },
      typesetError: (_doc, _math, e) => { throw e; }});
    const math = new doc.options.MathItem(item.latex, tex, item.display);
    math.start.node = adaptor.body(doc.document);
    math.setMetrics(16, 8, 1280, 1000000, 1);
    math.convert(doc);
    const html = adaptor.outerHTML(math.typesetRoot);
    const mml = new SerializedMmlVisitor().visitTree(math.root);
    if (/merror|data-mjx-error/.test(html + mml)) throw new Error(`MATH_ERROR at index ${i}`);
    return {html, mathml: mml};
  });
  process.stdout.write(JSON.stringify({renderer: 'mathjax-3.2.1-svg-base-ams-v1', expressions: result}));
} catch (e) {
  process.stderr.write('Static math stopped: ' + e.message + '\n');
  process.exitCode = 1;
}
