#!/usr/bin/env python3
"""Merge verified Payhip product links into Tiny Tails inventory files."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_STOCK_CSV = ROOT / "data" / "inventory" / "local-stock.csv"
PAYHIP_DETAILS_JSON = ROOT / "data" / "inventory" / "payhip-product-details.json"


def main() -> None:
    details = json.loads(PAYHIP_DETAILS_JSON.read_text(encoding="utf-8"))["products"]
    by_sku = {
        product["sku"]: product["payhip_buy_url"]
        for product in details
        if product.get("sku") and product.get("payhip_buy_url")
    }
    rows = list(csv.DictReader(LOCAL_STOCK_CSV.open(newline="", encoding="utf-8")))
    updated = 0
    for row in rows:
        url = by_sku.get(row["sku"])
        if url:
            row["payhip_url"] = url
            updated += 1

    with LOCAL_STOCK_CSV.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Merged Payhip URLs for {updated} inventory rows")


if __name__ == "__main__":
    main()
