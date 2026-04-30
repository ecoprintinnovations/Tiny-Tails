import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const root = process.cwd();
const statePath = path.join(root, "output/payhip-state.json");
const outputPath = path.join(root, "data/inventory/payhip-products-scraped.json");

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

const browser = await chromium.launch({ headless: true, executablePath: await findBrowser() });
const context = await browser.newContext({ storageState: statePath });
const page = await context.newPage();
const products = [];

for (let offset = 0; ; offset += 10) {
  const url = `https://payhip.com/products?listingStatus=all${offset ? `&page=${offset}` : ""}`;
  await page.goto(url, { waitUntil: "domcontentloaded" });
  await page.waitForSelector('body', { timeout: 30000 });
  await page.waitForTimeout(1000);
  const pageProducts = await page.evaluate(() => {
    const links = Array.from(document.querySelectorAll('a[href^="https://payhip.com/b/"]'));
    const products = [];
    for (const link of links) {
      const title = link.textContent.trim().replace(/\s+/g, " ");
      if (!title || title === "View") continue;
      const card = link.closest("ul") || link.parentElement;
      const text = card?.textContent.trim().replace(/\s+/g, " ") || "";
      products.push({
        title,
        payhip_buy_url: link.href,
        payhip_edit_url: link.href.replace("/b/", "/product/edit/"),
        card_text: text,
      });
    }
    return products;
  });
  products.push(...pageProducts);
  console.log(`page ${offset}: ${pageProducts.length}`);
  const next = await page.locator(`a[href*="page=${offset + 10}"]`).count();
  if (!next || pageProducts.length === 0) break;
}

const unique = Array.from(new Map(products.map((product) => [product.payhip_buy_url, product])).values());
await fs.writeFile(
  outputPath,
  JSON.stringify({ generated_at: new Date().toISOString(), count: unique.length, products: unique }, null, 2),
);
await browser.close();
console.log(`Scraped ${unique.length} products to ${path.relative(root, outputPath)}`);
