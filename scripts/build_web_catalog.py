"""Build the static storefront catalogue consumed by the Tiny Tails shop page."""

from __future__ import annotations

import json
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "data" / "inventory" / "full-inventory.json"
BEST_PETS_IMPORT_PATH = ROOT / "data" / "inventory" / "best-pets-payhip-import.json"
OUTPUT_PATH = ROOT / "assets" / "data" / "payhip-catalog.json"
STORE_GROUPS = ("Dog Supplies", "Cat Supplies", "Small Pets", "Birds & Reptiles")


def web_path(path: str) -> str:
    clean = (path or "").strip().replace("\\", "/")
    if not clean:
        return ""
    return clean if clean.startswith(("http://", "https://", "../")) else f"../{clean.lstrip('/')}"


def money(value: str) -> float:
    try:
        return round(float(value or 0), 2)
    except ValueError:
        return 0.0


def split_pipes(value: str) -> list[str]:
    return [part.strip() for part in (value or "").split("|") if part.strip()]


def checkout_url(payhip_url: str) -> str:
    clean = (payhip_url or "").strip()
    marker = "payhip.com/b/"
    if marker not in clean:
        return clean
    slug = clean.rstrip("/").split(marker, 1)[1]
    return f"https://payhip.com/buy?link={slug}"


def short_description(text: str, limit: int = 240) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return f"{text[:limit].rsplit(' ', 1)[0]}..."


def add_official_gear_direct(products: OrderedDict[str, dict], inventory: dict) -> None:
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))

    for item in inventory["variants"]:
        if item.get("active") != "yes" or item.get("payhip_status") != "ready_for_payhip":
            continue

        handle = f"official-gear-direct-{item['product_handle']}"
        product = products.setdefault(
            handle,
            {
                "handle": handle,
                "title": item["product_title"],
                "supplier": "Official Gear Direct",
                "shop_group": "Dog Supplies",
                "vendor": item.get("vendor", ""),
                "type": item.get("product_type", "Pet Supplies"),
                "tags": split_pipes(item.get("tags", "")),
                "description": short_description(item.get("description_text", "")),
                "source_url": item.get("source_url", ""),
                "featured_image": web_path(item.get("featured_image", "")),
                "images": [],
                "variants": [],
            },
        )

        for image_path in split_pipes(item.get("image_paths", "")):
            image = web_path(image_path)
            if image and image not in product["images"]:
                product["images"].append(image)

        product["variants"].append(
            {
                "title": item.get("variant_title") or "Default",
                "sku": item["sku"],
                "barcode": item.get("barcode", ""),
                "price": money(item.get("retail_price", "0")),
                "compare_at_price": money(item.get("compare_at_price", "0")),
                "currency": item.get("currency", inventory.get("currency", "GBP")),
                "quantity": int(item.get("local_quantity") or 0),
                "payhip_url": item.get("payhip_url", ""),
                "payhip_checkout_url": checkout_url(item.get("payhip_url", "")),
            }
        )


def add_best_pets(products: OrderedDict[str, dict]) -> None:
    if not BEST_PETS_IMPORT_PATH.exists():
        return

    best_pets = json.loads(BEST_PETS_IMPORT_PATH.read_text(encoding="utf-8"))
    for item in best_pets.get("products", []):
        if item.get("payhip_status") != "imported_to_payhip":
            continue
        if item.get("shop_group") not in STORE_GROUPS:
            continue
        if not item.get("payhip_checkout_url"):
            continue

        handle = f"best-pets-{item['payhip_sku'].lower()}"
        product = {
            "handle": handle,
            "title": item["title"],
            "supplier": "Best Pets",
            "shop_group": item["shop_group"],
            "vendor": "Best Pets",
            "type": item.get("category", "Pet Supplies"),
            "tags": [item.get("shop_group", ""), item.get("category", ""), item.get("subcategory", "")],
            "description": short_description(item.get("description", "")),
            "source_url": item.get("source_url", ""),
            "featured_image": web_path(item.get("featured_image", "")),
            "images": [web_path(item.get("featured_image", ""))] if item.get("featured_image") else [],
            "variants": [
                {
                    "title": item.get("subcategory") or "Default",
                    "sku": item["payhip_sku"],
                    "barcode": "",
                    "price": money(item.get("price", "0")),
                    "compare_at_price": 0,
                    "currency": item.get("currency", "GBP"),
                    "quantity": int(item.get("local_quantity") or 0),
                    "payhip_url": item.get("payhip_buy_url", ""),
                    "payhip_checkout_url": item.get("payhip_checkout_url", ""),
                }
            ],
        }
        products[handle] = product


def finalise_products(products: OrderedDict[str, dict], currency: str) -> dict:
    product_list = []
    for product in products.values():
        prices = [variant["price"] for variant in product["variants"] if variant["price"] > 0]
        product["price_min"] = min(prices) if prices else 0
        product["price_max"] = max(prices) if prices else 0
        product["variant_count"] = len(product["variants"])
        if not product["featured_image"] and product["images"]:
            product["featured_image"] = product["images"][0]
        product["variants"].sort(key=lambda variant: (variant["price"], variant["title"], variant["sku"]))
        product_list.append(product)

    product_list.sort(key=lambda product: (product.get("shop_group", ""), product["type"], product["title"]))
    categories = sorted({product["type"] for product in product_list if product["type"]})

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "currency": currency,
        "product_count": len(product_list),
        "variant_count": sum(product["variant_count"] for product in product_list),
        "store_groups": list(STORE_GROUPS),
        "group_counts": {
            group: sum(1 for product in product_list if product.get("shop_group") == group)
            for group in STORE_GROUPS
        },
        "categories": categories,
        "products": product_list,
    }


def main() -> None:
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    products: OrderedDict[str, dict] = OrderedDict()
    add_official_gear_direct(products, inventory)
    add_best_pets(products)
    payload = finalise_products(products, inventory.get("currency", "GBP"))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {payload['product_count']} products / {payload['variant_count']} variants to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
