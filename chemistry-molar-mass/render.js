const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1350 } });
  for (let i = 1; i <= 5; i++) {
    await p.goto('file://' + path.resolve('out/slide' + i + '.svg'));
    await p.screenshot({ path: 'out/slide' + i + '.png' });
  }
  await b.close();
})();
