import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const pwFile = [
  process.env.PLAYWRIGHT_JS,
  join(root, "../chip.family/node_modules/playwright/index.js"),
].find((p) => p && existsSync(p));
if (!pwFile) {
  throw new Error("Need playwright. Set PLAYWRIGHT_JS or clone next to chip.family.");
}
const { default: pw } = await import(pathToFileURL(pwFile).href);
const { chromium } = pw;

const html = pathToFileURL(join(root, "brand/banner.html")).href;
const out = join(root, "brand/banner.jpg");

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({
  viewport: { width: 1280, height: 640 },
  deviceScaleFactor: 2,
});
await page.goto(html, { waitUntil: "networkidle" });
await page.evaluate(() => document.fonts.ready);
await page.locator("h1").waitFor();
await page.screenshot({ path: out, type: "jpeg", quality: 88 });
await browser.close();
console.log("wrote", out);
