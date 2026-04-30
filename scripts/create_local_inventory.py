#!/usr/bin/env python3
"""Create Tiny Tails local stock files from the supplier catalogue.

Supplier stock is only used as an import hint. Tiny Tails manages stock locally,
so this script creates editable inventory files keyed by product handle and SKU.
Existing local quantities are preserved when the script is rerun.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SUPPLIER_JSON = ROOT / "data" / "suppliers" / "official-gear-direct" / "pets-products.json"
LOCAL_DIR = ROOT / "data" / "inventory"
LOCAL_CSV = LOCAL_DIR / "local-stock.csv"
LOCAL_JSON = LOCAL_DIR / "local-stock.json"


def load_existing_quantities() -> dict[tuple[str, str], dict[str, str]]:
    if not LOCAL_CSV.exists():
        return {}
    with LOCAL_CSV.open(newline="", encoding="utf-8") as csv_file:
        return {
            (row["product_handle"], row["sku"]): row
            for row in csv.DictReader(csv_file)
        }


def build_rows(catalogue: dict[str, Any], existing: dict[tuple[str, str], dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for product in catalogue["products"]:
        for variant in product["variants"]:
            sku = variant["sku"] or f"variant-{variant['id']}"
            key = (product["handle"], sku)
            previous = existing.get(key, {})
            quantity = previous.get("local_quantity", "0")
            active = previous.get("active", "yes")
            payhip_url = previous.get("payhip_url", "")
            rows.append(
                {
                    "product_handle": product["handle"],
                    "product_title": product["title"],
                    "variant_id": str(variant["id"] or ""),
                    "variant_title": variant["title"] or "Default Title",
                    "sku": sku,
                    "barcode": variant["barcode"] or "",
                    "local_quantity": quantity,
                    "active": active,
                    "payhip_url": payhip_url,
                    "supplier_available_hint": str(variant["available"]).lower(),
                    "retail_price": variant["price"],
                    "compare_at_price": variant["compare_at_price"],
                }
            )
    return rows


def write_csv(rows: list[dict[str, str]]) -> None:
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    fields = [
        "product_handle",
        "product_title",
        "variant_id",
        "variant_title",
        "sku",
        "barcode",
        "local_quantity",
        "active",
        "payhip_url",
        "supplier_available_hint",
        "retail_price",
        "compare_at_price",
    ]
    with LOCAL_CSV.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(rows: list[dict[str, str]]) -> None:
    payload = {
        "source": "Tiny Tails local inventory",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stock_is_managed_locally": True,
        "variant_count": len(rows),
        "variants": [
            {
                **row,
                "local_quantity": int(row["local_quantity"] or 0),
                "in_stock": row["active"].lower() == "yes" and int(row["local_quantity"] or 0) > 0,
            }
            for row in rows
        ],
    }
    LOCAL_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    catalogue = json.loads(SUPPLIER_JSON.read_text(encoding="utf-8"))
    rows = build_rows(catalogue, load_existing_quantities())
    write_csv(rows)
    write_json(rows)
    print(f"Wrote {len(rows)} variants to {LOCAL_CSV.relative_to(ROOT)}")
    print(f"Wrote {LOCAL_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
