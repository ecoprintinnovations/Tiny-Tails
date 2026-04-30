import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = process.cwd();
const inventory = JSON.parse(
  await fs.readFile(path.join(root, "data/inventory/full-inventory.json"), "utf8"),
);
const outputDir = path.join(root, "outputs/inventory");
const outputPath = path.join(outputDir, "tiny-tails-full-inventory.xlsx");

const workbook = Workbook.create();

function writeSheet(name, headers, rows, widths = {}) {
  const sheet = workbook.worksheets.add(name);
  sheet.showGridLines = false;
  const matrix = [headers, ...rows.map((row) => headers.map((header) => row[header] ?? ""))];
  sheet.getRangeByIndexes(0, 0, matrix.length, headers.length).values = matrix;
  sheet.freezePanes.freezeRows(1);
  const headerRange = sheet.getRangeByIndexes(0, 0, 1, headers.length);
  headerRange.format = {
    fill: "#2F0D15",
    font: { bold: true, color: "#FFFFFF" },
    wrapText: true,
  };
  const used = sheet.getRangeByIndexes(0, 0, matrix.length, headers.length);
  used.format.wrapText = true;
  used.format.verticalAlignment = "Top";
  const table = sheet.tables.add(sheet.getRangeByIndexes(0, 0, matrix.length, headers.length), true, `${name.replace(/[^A-Za-z0-9]/g, "")}Table`);
  table.style = "TableStyleMedium4";
  for (let col = 0; col < headers.length; col += 1) {
    const width = widths[headers[col]] ?? 120;
    sheet.getRangeByIndexes(0, col, matrix.length, 1).format.columnWidthPx = width;
  }
  return sheet;
}

const summaryRows = [
  { Metric: "Products", Value: inventory.product_count },
  { Metric: "Variants", Value: inventory.variant_count },
  { Metric: "Products ready for Payhip", Value: inventory.products_ready_for_payhip },
  { Metric: "Products on hold", Value: inventory.product_count - inventory.products_ready_for_payhip },
  { Metric: "Currency", Value: inventory.currency ?? "GBP" },
  { Metric: "Shipping profile", Value: "General / UK Standard Shipping" },
  { Metric: "Stock source of truth", Value: "Tiny Tails local stock" },
  { Metric: "Generated at", Value: inventory.generated_at },
];

const summary = writeSheet("Summary", ["Metric", "Value"], summaryRows, {
  Metric: 220,
  Value: 320,
});
summary.getRange("A1:B1").format = {
  fill: "#FFB6C1",
  font: { bold: true, color: "#2F0D15" },
};

const productHeaders = [
  "payhip_create_status",
  "product_handle",
  "title",
  "base_price",
  "currency",
  "price_range",
  "total_local_quantity",
  "has_variations",
  "variation_option_name",
  "variation_choices",
  "variant_skus",
  "vendor",
  "product_type",
  "payhip_visibility",
  "shipping_profile",
  "featured_image",
  "source_url",
];
writeSheet("Payhip Worklist", productHeaders, inventory.payhip_products, {
  payhip_create_status: 150,
  product_handle: 220,
  title: 280,
  base_price: 90,
  price_range: 100,
  total_local_quantity: 100,
  has_variations: 95,
  variation_option_name: 110,
  variation_choices: 240,
  variant_skus: 240,
  vendor: 130,
  product_type: 150,
  payhip_visibility: 120,
  shipping_profile: 190,
  featured_image: 300,
  source_url: 280,
});

const variantHeaders = [
  "product_handle",
  "product_title",
  "vendor",
  "product_type",
  "variant_title",
  "sku",
  "barcode",
  "local_quantity",
  "active",
  "in_stock",
  "retail_price",
  "currency",
  "compare_at_price",
  "payhip_url",
  "payhip_status",
  "supplier_available_hint",
  "featured_image",
  "source_url",
];
writeSheet("Variant Stock", variantHeaders, inventory.variants, {
  product_handle: 220,
  product_title: 280,
  vendor: 130,
  product_type: 150,
  variant_title: 130,
  sku: 150,
  barcode: 150,
  local_quantity: 95,
  active: 80,
  in_stock: 80,
  retail_price: 90,
  compare_at_price: 110,
  payhip_url: 240,
  payhip_status: 150,
  supplier_available_hint: 130,
  featured_image: 300,
  source_url: 280,
});

const byType = new Map();
for (const product of inventory.payhip_products) {
  const key = product.product_type || "Uncategorised";
  const current = byType.get(key) ?? { "Product Type": key, Products: 0, Variants: 0 };
  current.Products += 1;
  current.Variants += inventory.variants.filter((variant) => variant.product_handle === product.product_handle).length;
  byType.set(key, current);
}
writeSheet(
  "Category Summary",
  ["Product Type", "Products", "Variants"],
  [...byType.values()].sort((a, b) => b.Products - a.Products),
  { "Product Type": 260, Products: 100, Variants: 100 },
);

const readyRange = workbook.worksheets.getItem("Payhip Worklist").getRange("A2:A137");
readyRange.conditionalFormats.add("containsText", {
  text: "hold_no_local_stock",
  format: { fill: "#FDE68A", font: { color: "#78350F" } },
});
const stockRange = workbook.worksheets.getItem("Variant Stock").getRange("H2:H272");
stockRange.conditionalFormats.add("cellIs", {
  operator: "greaterThan",
  formula: 0,
  format: { fill: "#BBF7D0", font: { color: "#14532D" } },
});

await fs.mkdir(outputDir, { recursive: true });
const preview = await workbook.render({ sheetName: "Summary", autoCrop: "all", scale: 1, format: "png" });
await fs.writeFile(path.join(outputDir, "inventory-summary-preview.png"), new Uint8Array(await preview.arrayBuffer()));
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 20 },
  summary: "formula error scan",
});
console.log(errors.ndjson);
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);
console.log(outputPath);
