import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const root = process.cwd();
const statePath = path.join(root, "output/payhip-state.json");
const inventoryPath = path.join(root, "data/inventory/full-inventory.json");
const logPath = path.join(root, "data/inventory/payhip-created-products.json");

const args = new Set(process.argv.slice(2));
const commit = args.has("--commit");
const headless = !args.has("--headed");
const limitArg = process.argv.find((arg) => arg.startsWith("--limit="));
const limit = limitArg ? Number(limitArg.split("=")[1]) : Infinity;

const inventory = JSON.parse(await fs.readFile(inventoryPath, "utf8"));
const productRows = inventory.payhip_products
  .filter((product) => product.payhip_create_status === "ready_for_payhip")
  .slice(0, limit);
const variantsByProduct = new Map();
for (const variant of inventory.variants) {
  if (!variantsByProduct.has(variant.product_handle)) {
    variantsByProduct.set(variant.product_handle, []);
  }
  variantsByProduct.get(variant.product_handle).push(variant);
}

function absolute(filePath) {
  return path.join(root, filePath.replaceAll("/", path.sep));
}

function setValueScript(product, variants, uploadData) {
  const escaped = JSON.stringify({ product, variants, uploadData });
  return `(${function ({ product, variants, uploadData }) {
    const setInput = (selector, value) => {
      const element = document.querySelector(selector);
      if (!element) return;
      element.value = value ?? "";
      element.dispatchEvent(new Event("input", { bubbles: true }));
      element.dispatchEvent(new Event("change", { bubbles: true }));
    };
    const setChecked = (selector, checked) => {
      const element = document.querySelector(selector);
      if (!element) return;
      element.checked = checked;
      element.dispatchEvent(new Event("input", { bubbles: true }));
      element.dispatchEvent(new Event("change", { bubbles: true }));
    };

    setInput('input[name="name"]', product.title);
    setInput('input[name="price"]', product.base_price);
    setInput('input[name="description"]', product.description_text);
    const editor = document.querySelector(".ql-editor");
    if (editor) {
      editor.innerHTML = `<p>${product.description_text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")}</p>`;
    }
    setChecked('input[name="product_status"][value="unlisted"]', true);
    setChecked('input[name="track_inventory"]', true);

    const hasVariants = product.has_variations === "true";
    setChecked('input[name="has_variants"]', hasVariants);
    document.body.classList.toggle("product-has-variants", hasVariants);

    if (uploadData) {
      const meta = document.querySelector('meta[property="cover-image-upload-data"]');
      if (meta) meta.setAttribute("value", JSON.stringify([uploadData]));
    }

    if (!hasVariants) {
      const variant = variants[0];
      setInput('input[name="sku"]', variant.sku);
      setInput('input[name="inventory"]', String(variant.local_quantity || 0));
      setInput('input[name="weight"]', "0");
      setInput('input[name="variants"]', "[]");
      setInput('input[name="variant_combinations"]', "[]");
      return;
    }

    const variantKey = Date.now();
    const choices = variants.map((variant, index) => ({
      choice_key: String(variantKey + index + 1),
      choice_name: variant.variant_title,
      order: index,
    }));
    const payhipVariants = [
      {
        variant_key: variantKey,
        name: product.variation_option_name || "Size",
        display_type: "list",
        choices,
        order: 0,
      },
    ];
    const combinations = variants.map((variant, index) => ({
      combination_joined_key: choices[index].choice_key,
      combination_name: variant.variant_title,
      combination_properties: {
        price: variant.retail_price,
        on_sale: 0,
        sku: variant.sku,
        weight: "0",
        inventory: String(variant.local_quantity || 0),
      },
    }));
    setInput('input[name="variants"]', JSON.stringify(payhipVariants));
    setInput('input[name="variant_combinations"]', JSON.stringify(combinations));
  }.toString()})(${escaped})`;
}

async function uploadFirstImage(page, product) {
  const firstImage = product.featured_image || product.image_paths_up_to_9.split(" | ")[0];
  if (!firstImage) return null;
  const imagePath = absolute(firstImage);
  await page.locator("input[type=file]").first().setInputFiles(imagePath);
  await page.waitForFunction(() => document.querySelector('meta[property="upload-in-progress"]')?.getAttribute("value") === "0", null, { timeout: 30000 });
  const raw = await page.locator('meta[property="cover-image-upload-data"]').getAttribute("value");
  const parsed = raw ? JSON.parse(raw) : [];
  return parsed[0] ?? null;
}

let executablePath;
for (const candidate of [
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
]) {
  try {
    await fs.access(candidate);
    executablePath = candidate;
    break;
  } catch {
    // Keep looking for an installed browser before falling back to Playwright's bundle.
  }
}

const browser = await chromium.launch({ headless, executablePath });
const context = await browser.newContext({ storageState: statePath });
const page = await context.newPage();
const results = [];

for (const [index, product] of productRows.entries()) {
  const variants = variantsByProduct.get(product.product_handle) ?? [];
  console.log(`[${index + 1}/${productRows.length}] ${commit ? "creating" : "dry-run"} ${product.product_handle}`);
  await page.goto("https://payhip.com/product/add/physical", { waitUntil: "domcontentloaded" });
  await page.waitForSelector('input[name="name"]', { timeout: 30000 });
  const uploadData = await uploadFirstImage(page, product);
  await page.evaluate(setValueScript(product, variants, uploadData));

  if (!commit) {
    results.push({
      handle: product.product_handle,
      title: product.title,
      status: "dry_run_ready",
      uploaded_cover: Boolean(uploadData),
    });
    break;
  }

  await page.getByRole("button", { name: /Add Product/i }).click();
  await page.waitForLoadState("domcontentloaded", { timeout: 60000 });
  const currentUrl = page.url();
  results.push({
    handle: product.product_handle,
    title: product.title,
    status: "submitted",
    payhip_admin_url: currentUrl,
    uploaded_cover: Boolean(uploadData),
  });
  await fs.writeFile(logPath, JSON.stringify({ generated_at: new Date().toISOString(), results }, null, 2));
}

await fs.writeFile(logPath, JSON.stringify({ generated_at: new Date().toISOString(), results }, null, 2));
await browser.close();
console.log(`Wrote ${results.length} results to ${path.relative(root, logPath)}`);
