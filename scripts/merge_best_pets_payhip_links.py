"""Merge scraped Payhip links back into the Best Pets Payhip import log."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMPORT_JSON = ROOT / "data" / "inventory" / "best-pets-payhip-import.json"
RESULTS_JSON = ROOT / "data" / "inventory" / "best-pets-payhip-products.json"
DETAILS_JSON = ROOT / "data" / "inventory" / "payhip-product-details.json"


def checkout_url(buy_url: str) -> str:
    marker = "payhip.com/b/"
    if marker not in buy_url:
        return ""
    slug = buy_url.rstrip("/").split(marker, 1)[1]
    return f"https://payhip.com/buy?link={slug}"


def main() -> None:
    import_data = json.loads(IMPORT_JSON.read_text(encoding="utf-8"))
    results_data = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
    details_data = json.loads(DETAILS_JSON.read_text(encoding="utf-8"))

    details_by_sku = {
        item.get("sku"): item
        for item in details_data.get("products", [])
        if item.get("sku", "").startswith("BP-") and item.get("payhip_buy_url")
    }

    updated_results = 0
    for item in results_data.get("results", []):
        detail = details_by_sku.get(item.get("payhip_sku"))
        if not detail:
            continue
        item["payhip_buy_url"] = detail["payhip_buy_url"]
        item["payhip_checkout_url"] = checkout_url(detail["payhip_buy_url"])
        item["payhip_edit_url"] = detail["payhip_edit_url"]
        item["status"] = "created"
        updated_results += 1

    result_links_by_sku = {item.get("payhip_sku"): item for item in results_data.get("results", [])}
    updated_import = 0
    for item in import_data.get("products", []):
        result = result_links_by_sku.get(item.get("payhip_sku"))
        if not result or not result.get("payhip_buy_url"):
            continue
        item["payhip_buy_url"] = result["payhip_buy_url"]
        item["payhip_checkout_url"] = result["payhip_checkout_url"]
        item["payhip_edit_url"] = result["payhip_edit_url"]
        item["payhip_status"] = "imported_to_payhip"
        updated_import += 1

    RESULTS_JSON.write_text(json.dumps(results_data, indent=2, ensure_ascii=False), encoding="utf-8")
    IMPORT_JSON.write_text(json.dumps(import_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Updated {updated_results} Payhip result rows")
    print(f"Updated {updated_import} Best Pets import rows")


if __name__ == "__main__":
    main()
