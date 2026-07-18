const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  await page.goto('http://127.0.0.1:8765/', { waitUntil: 'networkidle' });
  await page.screenshot({ path: '/tmp/repetita-ready.png', fullPage: true });
  for (let step = 1; step <= 9; step += 1) {
    const button = page.locator(`[data-step="${step}"]`);
    await button.click();
    if (step === 1 || step === 7) {
      await page.waitForFunction(() => document.querySelector('#systemStatus').textContent !== 'PROCESSING');
    }
  }
  const layout = await page.evaluate(() => ({
    innerHeight: window.innerHeight,
    scrollHeight: document.documentElement.scrollHeight,
    status: document.querySelector('#systemStatus').textContent,
    coverage: document.querySelector('#coverageMetric').textContent,
    report: document.querySelector('#resultContent').textContent.includes('FORMAL GATES PASSED'),
  }));
  if (layout.scrollHeight > layout.innerHeight + 1) throw new Error(`Page scroll detected: ${JSON.stringify(layout)}`);
  if (layout.coverage !== '100%') throw new Error(`Unexpected coverage: ${JSON.stringify(layout)}`);
  await page.screenshot({ path: '/tmp/repetita-report.png', fullPage: true });
  console.log(JSON.stringify(layout));
  await browser.close();
})().catch((error) => {
  console.error(error);
  process.exit(1);
});

