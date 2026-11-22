// Screenshots for the README: serves the built site and drives the system Chrome with playwright-core.
//   npm run build && CHROME=/usr/bin/google-chrome npm run shots
import { spawn } from "node:child_process";
import { mkdirSync } from "node:fs";
import { chromium } from "playwright-core";

const port = 4319;
const base = `http://127.0.0.1:${port}`;
const out = new URL("../../docs/screenshots/", import.meta.url).pathname;
mkdirSync(out, { recursive: true });
const server = spawn(process.execPath, ["node_modules/vite/bin/vite.js", "preview", "--port", String(port), "--host", "127.0.0.1", "--strictPort"], { stdio: "ignore" });
for (let i = 0; i < 80; i++) {
  try { if ((await fetch(base)).ok) break; } catch {}
  await new Promise((r) => setTimeout(r, 250));
}
const browser = await chromium.launch({
  executablePath: process.env.CHROME ?? "/usr/bin/google-chrome",
  args: ["--no-sandbox", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
});
try {
  for (const scheme of ["light", "dark"]) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, colorScheme: scheme, reducedMotion: "reduce" });
    // WebGL clears its buffer when a full-page capture resizes the viewport, so size the viewport to the page first
    const shot = async (name) => {
      await page.waitForTimeout(400);
      const h = await page.evaluate(() => document.documentElement.scrollHeight);
      await page.setViewportSize({ width: 1440, height: h });
      await page.waitForTimeout(1500);
      await page.screenshot({ path: `${out}${name}${scheme === "dark" ? "-dark" : ""}.png` });
      await page.setViewportSize({ width: 1440, height: 1000 });
    };
    await page.goto(`${base}/`);
    await page.waitForSelector(".leads li");
    await page.waitForSelector('figure.map[data-status="ready"]', { timeout: 60000 }).catch(() => {});
    await page.locator(".leads li .head").first().click();
    await shot("leads");
    if (scheme === "dark") { await page.close(); continue; }
    await page.goto(`${base}/quellen/`);
    await page.waitForSelector("table");
    await shot("sources");
    await page.goto(`${base}/wahlabend/`);
    await page.waitForSelector("input[type=range]");
    await page.locator("input[type=range]").evaluate((el) => { el.value = String(Math.round(Number(el.max) * 0.37)); el.dispatchEvent(new Event("input", { bubbles: true })); });
    await shot("election");
    await page.goto(`${base}/ergebnisse/`);
    await page.waitForSelector("figure svg");
    await shot("results");
    await page.close();
  }
  console.log(`screenshots in ${out}`);
} finally {
  await browser.close();
  server.kill();
}
