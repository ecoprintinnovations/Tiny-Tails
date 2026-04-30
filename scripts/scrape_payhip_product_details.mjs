import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const root = process.cwd();
const statePath = path.join(root, "output/payhip-state.json");
const scrapedPath = path.join(root, "data/inventory/payhip-products-scraped.json");
const outputPath = path.join(root, "data/inventory/payhip-product-details.json");

async function findBrowser() {
  for (const candidate of [
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  ]) {
    try {
      await fs.access(candidate);
      return candidate;
    } catch {
      // Keep looking.
    }
  }
  return undefined;
}

const scraped = JSON.parse(await fs.readFile(scrapedPath, "utf8")).products;
let details = [];
try {
  details = JSON.parse(await fs.readFile(outputPath, "utf8")).products || [];
} catch {
  // Fresh run.
}
details = details.filter((product) => !product.scrape_error);
const seenUrls = new Set(details.map((product) => product.payhip_edit_url));
const browser = await chromium.launch({ headless: true, executablePath: await findBrowser() });
const context = await browser.newContext({ storageState: statePath });
const page = await context.newPage();

for (const [index, product] of scraped.entries()) {
  if (seenUrls.has(product.payhip_edit_url)) {
    continue;
  }
  console.log(`[${index + 1}/${scraped.length}] ${product.payhip_edit_url}`);
  try {
    await page.goto(product.payhip_edit_url, { waitUntil: "domcontentloaded", timeout: 45000 });
    await page.waitForSelector('input[name="name"]', { timeout: 45000 });
    const detail = await page.evaluate(() => ({
      title: document.querySelector('input[name="name"]')?.value || "",
      sku: document.querySelector('input[name="sku"]')?.value || "",
      price: document.querySelector('input[name="price"]')?.value || "",
      inventory: document.querySelector('input[name="inventory"]')?.value || "",
      unlisted: document.querySelector('input[name="product_status"][value="unlisted"]')?.checked || false,
    }));
    details.push({ ...product, ...detail });
  } catch (error) {
    console.warn(`Could not scrape ${product.payhip_edit_url}: ${error.message}`);
    details.push({ ...product, scrape_error: error.message });
  }
  if ((index + 1) % 25 === 0) {
    await fs.writeFile(outputPath, JSON.stringify({ generated_at: new Date().toISOString(), count: details.length, products: details }, null, 2));
  }
}

await fs.writeFile(outputPath, JSON.stringify({ generated_at: new Date().toISOString(), count: details.length, products: details }, null, 2));
await browser.close();
console.log(`Scraped ${details.length} product details to ${path.relative(root, outputPath)}`);
