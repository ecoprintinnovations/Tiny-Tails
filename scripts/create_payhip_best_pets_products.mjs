import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const root = process.cwd();
const statePath = path.join(root, "output/payhip-state.json");
const importPath = path.join(root, "data/inventory/best-pets-payhip-import.json");
const outputPath = path.join(root, "data/inventory/best-pets-payhip-products.json");

const args = new Set(process.argv.slice(2));
const commit = args.has("--commit");
const headless = !args.has("--headed");
const trustStart = args.has("--trust-start");
const skipLinkLookup = args.has("--skip-link-lookup");
const startArg = process.argv.find((arg) => arg.startsWith("--start="));
const limitArg = process.argv.find((arg) => arg.startsWith("--limit="));
const onlySkusArg = process.argv.find((arg) => arg.startsWith("--only-skus="));
const start = startArg ? Number(startArg.split("=")[1]) : 0;
const limit = limitArg ? Number(limitArg.split("=")[1]) : Infinity;
const onlySkus = onlySkusArg ? new Set(onlySkusArg.split("=")[1].split(",").filter(Boolean)) : null;

const importData = JSON.parse(await fs.readFile(importPath, "utf8"));
const products = importData.products
  .filter((product) => Number(product.local_quantity) > 0 && Number(product.price) > 0)
  .filter((product) => !onlySkus || onlySkus.has(product.payhip_sku))
  .slice(start, Number.isFinite(limit) ? start + limit : undefined);

let previous = { results: [] };
try {
  previous = JSON.parse(await fs.readFile(outputPath, "utf8"));
} catch {
  // No previous run yet.
}
const results = previous.results ?? [];
const doneSkus = new Set(results.map((result) => result.payhip_sku));

function absolute(filePath) {
  return path.join(root, filePath.replaceAll("/", path.sep));
}

function checkoutUrl(buyUrl) {
  const marker = "payhip.com/b/";
  if (!buyUrl || !buyUrl.includes(marker)) return "";
  const slug = buyUrl.split(marker)[1].replace(/\/$/, "");
  return `https://payhip.com/buy?link=${slug}`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

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

async function fillProductForm(page, product) {
  await page.locator('input[name="name"]').fill(product.title);
  await page.locator('input[name="price"]').fill(product.price);

  const description = `${product.description}\n\nTiny Tails category: ${product.shop_group}`;
  await page.locator('input[name="description"]').evaluate((element, value) => {
    element.value = value;
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
  }, description);
  const descriptionHtml = `<p>${escapeHtml(description).replace(/\n/g, "<br>")}</p>`;
  await page.locator(".ql-editor").evaluate((element, value) => {
    element.innerHTML = value;
  }, descriptionHtml);

  if (product.featured_image) {
    await page.locator("input[type=file]").first().setInputFiles(absolute(product.featured_image));
    await page.waitForFunction(
      () => document.querySelector('meta[property="upload-in-progress"]')?.getAttribute("value") === "0",
      null,
      { timeout: 45000 },
    );
  }

  const variantsBox = page.locator('input[name="has_variants"]');
  if ((await variantsBox.count()) && (await variantsBox.isChecked())) {
    await variantsBox.uncheck();
  }

  const stockBox = page.locator('input[name="track_inventory"]');
  if (!(await stockBox.isChecked())) {
    await stockBox.check();
  }
  await page.locator('input[name="sku"]').fill(product.payhip_sku);
  await page.locator('input[name="weight"]').fill("0");
  await page.locator('input[name="inventory"]').fill(String(product.local_quantity));
  await page.locator('input[name="product_status"][value="unlisted"]').check();

  return {
    title: product.title,
    supplier_sku: product.supplier_sku,
    payhip_sku: product.payhip_sku,
    shop_group: product.shop_group,
    category: product.category,
    subcategory: product.subcategory,
  };
}

async function findBuyUrl(page, title) {
  await page.goto("https://payhip.com/products?listingStatus=all", { waitUntil: "domcontentloaded" });
  await page.locator('input[placeholder="Search for product"]').fill(title);
  await page.getByRole("button", { name: "Search" }).click();
  await page.waitForLoadState("domcontentloaded", { timeout: 30000 });
  const link = page.locator('a[href^="https://payhip.com/b/"]').first();
  await link.waitFor({ state: "visible", timeout: 30000 });
  return await link.getAttribute("href");
}

async function saveProgress() {
  await fs.writeFile(
    outputPath,
    JSON.stringify({ generated_at: new Date().toISOString(), source: path.relative(root, importPath), results }, null, 2),
  );
}

const browser = await chromium.launch({ headless, executablePath: await findBrowser() });
const context = await browser.newContext({ storageState: statePath });
const page = await context.newPage();

for (const [index, product] of products.entries()) {
  const absoluteIndex = start + index;
  if (doneSkus.has(product.payhip_sku)) {
    console.log(`[${absoluteIndex + 1}] skipping already logged ${product.payhip_sku}`);
    continue;
  }

  console.log(`[${absoluteIndex + 1}/${importData.product_count}] ${commit ? "saving" : "dry-run"} ${product.payhip_sku}`);

  if (commit && !trustStart) {
    const existingUrl = await findBuyUrl(page, product.title).catch(() => null);
    if (existingUrl) {
      results.push({
        ...product,
        status: "detected_existing",
        payhip_buy_url: existingUrl,
        payhip_checkout_url: checkoutUrl(existingUrl),
        payhip_edit_url: existingUrl.replace("/b/", "/product/edit/"),
      });
      doneSkus.add(product.payhip_sku);
      await saveProgress();
      continue;
    }
  }

  await page.goto("https://payhip.com/product/add/physical", { waitUntil: "domcontentloaded" });
  await page.waitForSelector('input[name="name"]', { timeout: 30000 });
  const filled = await fillProductForm(page, product);

  if (!commit) {
    results.push({ ...filled, status: "dry_run_ready" });
    await saveProgress();
    break;
  }

  await page.getByRole("button", { name: "Add Product" }).click();
  await page.waitForLoadState("domcontentloaded", { timeout: 60000 });
  const buyUrl = skipLinkLookup
    ? ""
    : await findBuyUrl(page, filled.title).catch((error) => {
        console.warn(`Could not capture buy URL for ${filled.payhip_sku}: ${error.message}`);
        return "";
      });
  results.push({
    ...filled,
    status: buyUrl ? "created" : "created_pending_link_lookup",
    payhip_buy_url: buyUrl,
    payhip_checkout_url: checkoutUrl(buyUrl),
    payhip_edit_url: buyUrl ? buyUrl.replace("/b/", "/product/edit/") : "",
  });
  doneSkus.add(product.payhip_sku);
  await saveProgress();
}

await browser.close();
console.log(`Wrote ${results.length} results to ${path.relative(root, outputPath)}`);
