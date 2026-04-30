import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const root = process.cwd();
const statePath = path.join(root, "output/payhip-state.json");
const inventoryPath = path.join(root, "data/inventory/full-inventory.json");
const outputPath = path.join(root, "data/inventory/payhip-variant-products.json");
const existingFirstEditUrl = "https://payhip.com/product/edit/LCFmp";
const existingFirstBuyUrl = "https://payhip.com/b/LCFmp";

const args = new Set(process.argv.slice(2));
const commit = args.has("--commit");
const headless = !args.has("--headed");
const repairFirst = args.has("--repair-first");
const trustStart = args.has("--trust-start");
const startArg = process.argv.find((arg) => arg.startsWith("--start="));
const limitArg = process.argv.find((arg) => arg.startsWith("--limit="));
const onlySkusArg = process.argv.find((arg) => arg.startsWith("--only-skus="));
const start = startArg ? Number(startArg.split("=")[1]) : 0;
const limit = limitArg ? Number(limitArg.split("=")[1]) : Infinity;
const onlySkus = onlySkusArg ? new Set(onlySkusArg.split("=")[1].split(",").filter(Boolean)) : null;

const inventory = JSON.parse(await fs.readFile(inventoryPath, "utf8"));
const variants = inventory.variants
  .filter((variant) => variant.active === "yes" && Number(variant.local_quantity) > 0)
  .filter((variant) => !onlySkus || onlySkus.has(variant.sku))
  .slice(start, Number.isFinite(limit) ? start + limit : undefined);

let previous = { results: [] };
try {
  previous = JSON.parse(await fs.readFile(outputPath, "utf8"));
} catch {
  // No previous run yet.
}
const results = previous.results ?? [];
const doneSkus = new Set(results.map((result) => result.sku));

function titleFor(variant) {
  return variant.variant_title && variant.variant_title !== "Default Title"
    ? `${variant.product_title} - ${variant.variant_title}`
    : variant.product_title;
}

function absolute(filePath) {
  return path.join(root, filePath.replaceAll("/", path.sep));
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

async function fillProductForm(page, variant, mode) {
  const title = titleFor(variant);
  await page.locator('input[name="name"]').fill(title);
  await page.locator('input[name="price"]').fill(variant.retail_price);

  const description = `${variant.description_text}\n\nSKU: ${variant.sku}`;
  await page.locator('input[name="description"]').evaluate((element, value) => {
    element.value = value;
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
  }, description);
  await page.locator(".ql-editor").evaluate((element, value) => {
    element.innerHTML = `<p>${value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\n/g, "<br>")}</p>`;
  }, description);

  const coverMetaBefore = await page.locator('meta[property="cover-image-upload-data"]').getAttribute("value");
  const coverAlreadyPresent = coverMetaBefore && coverMetaBefore !== "[]";
  if (!coverAlreadyPresent) {
    await page.locator("input[type=file]").first().setInputFiles(absolute(variant.featured_image));
    await page.waitForFunction(
      () => document.querySelector('meta[property="upload-in-progress"]')?.getAttribute("value") === "0",
      null,
      { timeout: 30000 },
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
  await page.locator('input[name="sku"]').fill(variant.sku);
  await page.locator('input[name="weight"]').fill("0");
  await page.locator('input[name="inventory"]').fill(String(variant.local_quantity));
  await page.locator('input[name="product_status"][value="unlisted"]').check();

  return {
    title,
    mode,
    sku: variant.sku,
    product_handle: variant.product_handle,
    variant_title: variant.variant_title,
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
    JSON.stringify({ generated_at: new Date().toISOString(), results }, null, 2),
  );
}

const browser = await chromium.launch({ headless, executablePath: await findBrowser() });
const context = await browser.newContext({ storageState: statePath });
const page = await context.newPage();

for (const [index, variant] of variants.entries()) {
  const absoluteIndex = start + index;
  if (doneSkus.has(variant.sku)) {
    console.log(`[${absoluteIndex + 1}] skipping already logged ${variant.sku}`);
    continue;
  }

  const useExistingFirst = repairFirst && absoluteIndex === 0;
  console.log(`[${absoluteIndex + 1}/${inventory.variants.length}] ${commit ? "saving" : "dry-run"} ${variant.sku}`);

  if (commit && !useExistingFirst && !trustStart) {
    const existingUrl = await findBuyUrl(page, titleFor(variant)).catch(() => null);
    if (existingUrl) {
      const filled = {
        title: titleFor(variant),
        mode: "detected_existing",
        sku: variant.sku,
        product_handle: variant.product_handle,
        variant_title: variant.variant_title,
      };
      results.push({
        ...filled,
        status: "detected_existing",
        payhip_buy_url: existingUrl,
        payhip_edit_url: existingUrl.replace("/b/", "/product/edit/"),
      });
      doneSkus.add(variant.sku);
      await saveProgress();
      continue;
    }
  }

  await page.goto(useExistingFirst ? existingFirstEditUrl : "https://payhip.com/product/add/physical", {
    waitUntil: "domcontentloaded",
  });
  await page.waitForSelector('input[name="name"]', { timeout: 30000 });

  const filled = await fillProductForm(page, variant, useExistingFirst ? "repair_existing" : "create");
  if (!commit) {
    results.push({ ...filled, status: "dry_run_ready" });
    await saveProgress();
    break;
  }

  if (useExistingFirst) {
    await page.getByRole("button", { name: "Save Changes" }).click();
    await page.waitForLoadState("domcontentloaded", { timeout: 60000 });
    results.push({
      ...filled,
      status: "updated_existing",
      payhip_buy_url: existingFirstBuyUrl,
      payhip_edit_url: existingFirstEditUrl,
    });
  } else {
    await page.getByRole("button", { name: "Add Product" }).click();
    await page.waitForLoadState("domcontentloaded", { timeout: 60000 });
    const buyUrl = await findBuyUrl(page, filled.title).catch((error) => {
      console.warn(`Could not capture buy URL for ${filled.sku}: ${error.message}`);
      return "";
    });
    results.push({
      ...filled,
      status: buyUrl ? "created" : "created_pending_link_lookup",
      payhip_buy_url: buyUrl,
      payhip_edit_url: buyUrl ? buyUrl.replace("/b/", "/product/edit/") : "",
    });
  }
  doneSkus.add(variant.sku);
  await saveProgress();
}

await browser.close();
console.log(`Wrote ${results.length} results to ${path.relative(root, outputPath)}`);
