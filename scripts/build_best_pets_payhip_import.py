"""Build a Payhip-ready import worklist from the Best Pets catalogue scrape."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "suppliers" / "best-pets" / "catalogue-products.json"
OUT_DIR = ROOT / "data" / "inventory"
OUT_JSON = OUT_DIR / "best-pets-payhip-import.json"
OUT_CSV = OUT_DIR / "best-pets-payhip-import.csv"
ALLOWED_GROUPS = {"Dog Supplies", "Cat Supplies", "Small Pets", "Birds & Reptiles"}
LOCAL_QTY = 100


def clean_price(value: str) -> str:
    try:
        return f"{float(value or 0):.2f}"
    except ValueError:
        return "0.00"


def product_title(row: dict[str, str]) -> str:
    title = row["title"].strip()
    size = row.get("size", "").strip()
    if size and size.lower() not in title.lower():
        return f"{title} - {size}"
    return title


def description(row: dict[str, str]) -> str:
    parts = [
        row.get("description", "").strip(),
        f"Category: {row['shop_group']} / {row['category']} / {row['subcategory']}",
        f"Supplier SKU: {row['sku']}",
    ]
    return "\n\n".join(part for part in parts if part)


def main() -> None:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = []
    seen_skus = set()

    for row in data["products"]:
        if row.get("shop_group") not in ALLOWED_GROUPS:
            continue
        sku = f"BP-{row['sku']}"
        if sku in seen_skus:
            continue
        seen_skus.add(sku)
        rows.append(
            {
                "supplier": "Best Pets",
                "supplier_sku": row["sku"],
                "payhip_sku": sku,
                "title": product_title(row),
                "price": clean_price(row.get("rsp", "")),
                "currency": "GBP",
                "local_quantity": str(LOCAL_QTY),
                "shop_group": row["shop_group"],
                "category": row["category"],
                "subcategory": row["subcategory"],
                "description": description(row),
                "featured_image": row.get("local_image", ""),
                "source_url": row.get("source_url", ""),
                "detail_url": row.get("detail_url", ""),
                "payhip_visibility": "Unlisted",
                "payhip_buy_url": "",
                "payhip_checkout_url": "",
                "payhip_edit_url": "",
                "payhip_status": "ready_to_import",
            }
        )

    rows.sort(key=lambda item: (item["shop_group"], item["category"], item["subcategory"], item["title"], item["payhip_sku"]))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source": str(SOURCE.relative_to(ROOT)),
                "product_count": len(rows),
                "allowed_groups": sorted(ALLOWED_GROUPS),
                "products": rows,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} Best Pets Payhip rows to {OUT_JSON.relative_to(ROOT)}")
    print(f"Wrote {OUT_CSV.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
