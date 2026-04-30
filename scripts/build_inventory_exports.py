#!/usr/bin/env python3
"""Build Tiny Tails inventory exports from supplier catalogue and local stock."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CATALOGUE_JSON = ROOT / "data" / "suppliers" / "official-gear-direct" / "pets-products.json"
LOCAL_STOCK_CSV = ROOT / "data" / "inventory" / "local-stock.csv"
OUTPUT_DIR = ROOT / "data" / "inventory"
FULL_INVENTORY_CSV = OUTPUT_DIR / "full-inventory.csv"
PAYHIP_WORKLIST_CSV = OUTPUT_DIR / "payhip-product-worklist.csv"
FULL_INVENTORY_JSON = OUTPUT_DIR / "full-inventory.json"
STORE_CURRENCY = "GBP"


def read_local_stock() -> dict[tuple[str, str], dict[str, str]]:
    with LOCAL_STOCK_CSV.open(newline="", encoding="utf-8") as csv_file:
        return {
            (row["product_handle"], row["sku"]): row
            for row in csv.DictReader(csv_file)
        }


def csv_join(values: list[Any]) -> str:
    return " | ".join(str(value) for value in values if value not in (None, ""))


def build_inventory_rows(catalogue: dict[str, Any], stock: dict[tuple[str, str], dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for product in catalogue["products"]:
        image_paths = [image["local_path"] for image in product["images"]]
        source_images = [image["src"] for image in product["images"]]
        for variant in product["variants"]:
            sku = variant["sku"] or f"variant-{variant['id']}"
            local = stock.get((product["handle"], sku), {})
            quantity = local.get("local_quantity", "0")
            active = local.get("active", "yes")
            rows.append(
                {
                    "product_handle": product["handle"],
                    "product_title": product["title"],
                    "vendor": product["vendor"],
                    "product_type": product["product_type"],
                    "tags": csv_join(product["tags"]),
                    "variant_id": str(variant["id"] or ""),
                    "variant_title": variant["title"] or "Default Title",
                    "sku": sku,
                    "barcode": variant["barcode"] or "",
                    "local_quantity": quantity,
                    "active": active,
                    "in_stock": str(active.lower() == "yes" and int(quantity or 0) > 0).lower(),
                    "retail_price": variant["price"],
                    "currency": STORE_CURRENCY,
                    "compare_at_price": variant["compare_at_price"],
                    "payhip_url": local.get("payhip_url", ""),
                    "payhip_status": "ready_for_payhip" if int(quantity or 0) > 0 else "hold_no_local_stock",
                    "supplier_available_hint": local.get("supplier_available_hint", str(variant["available"]).lower()),
                    "source_url": product["source_url"],
                    "featured_image": product["featured_image"],
                    "image_paths": csv_join(image_paths),
                    "source_image_urls": csv_join(source_images),
                    "description_text": product["description_text"],
                }
            )
    return rows


def build_payhip_rows(catalogue: dict[str, Any], inventory_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows_by_product: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in inventory_rows:
        rows_by_product[row["product_handle"]].append(row)

    product_lookup = {product["handle"]: product for product in catalogue["products"]}
    payhip_rows: list[dict[str, str]] = []
    for handle, variants in rows_by_product.items():
        product = product_lookup[handle]
        prices = [float(row["retail_price"]) for row in variants if row["retail_price"]]
        quantities = [int(row["local_quantity"] or 0) for row in variants]
        variant_titles = [row["variant_title"] for row in variants]
        skus = [row["sku"] for row in variants]
        image_paths = [image["local_path"] for image in product["images"][:9]]
        payhip_rows.append(
            {
                "payhip_create_status": "ready_for_payhip" if sum(quantities) > 0 else "hold_no_local_stock",
                "product_handle": handle,
                "title": product["title"],
                "base_price": f"{min(prices):.2f}" if prices else "",
                "currency": STORE_CURRENCY,
                "price_range": f"{min(prices):.2f}-{max(prices):.2f}" if prices else "",
                "total_local_quantity": str(sum(quantities)),
                "has_variations": str(len(variants) > 1 or variant_titles != ["Default Title"]).lower(),
                "variation_option_name": "Size" if any(title != "Default Title" for title in variant_titles) else "",
                "variation_choices": csv_join(variant_titles if variant_titles != ["Default Title"] else []),
                "variant_skus": csv_join(skus),
                "vendor": product["vendor"],
                "product_type": product["product_type"],
                "tags": csv_join(product["tags"]),
                "payhip_visibility": "Unlisted",
                "shipping_profile": "General / UK Standard Shipping",
                "image_paths_up_to_9": csv_join(image_paths),
                "featured_image": product["featured_image"],
                "description_text": product["description_text"],
                "source_url": product["source_url"],
            }
        )
    return payhip_rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    catalogue = json.loads(CATALOGUE_JSON.read_text(encoding="utf-8"))
    stock = read_local_stock()
    inventory_rows = build_inventory_rows(catalogue, stock)
    payhip_rows = build_payhip_rows(catalogue, inventory_rows)

    write_csv(FULL_INVENTORY_CSV, inventory_rows)
    write_csv(PAYHIP_WORKLIST_CSV, payhip_rows)
    FULL_INVENTORY_JSON.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "currency": STORE_CURRENCY,
                "product_count": len(payhip_rows),
                "variant_count": len(inventory_rows),
                "products_ready_for_payhip": sum(
                    1 for row in payhip_rows if row["payhip_create_status"] == "ready_for_payhip"
                ),
                "variants": inventory_rows,
                "payhip_products": payhip_rows,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {len(inventory_rows)} inventory variants to {FULL_INVENTORY_CSV.relative_to(ROOT)}")
    print(f"Wrote {len(payhip_rows)} Payhip product rows to {PAYHIP_WORKLIST_CSV.relative_to(ROOT)}")
    print(f"Wrote {FULL_INVENTORY_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
