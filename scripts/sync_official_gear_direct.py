#!/usr/bin/env python3
"""Import Official Gear Direct pet products for the Tiny Tails catalogue.

The supplier has confirmed Tiny Tails may use these product images and details.
This script pulls the public Shopify collection feed, enriches each product from
its `.js` endpoint, downloads product imagery, and writes normalized JSON/CSV
snapshots that can be imported into an ecommerce backend.
"""

from __future__ import annotations

import csv
import html
import json
import re
import time
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


SUPPLIER_NAME = "Official Gear Direct"
SUPPLIER_BASE_URL = "https://officialgeardirect.com"
COLLECTION_HANDLE = "pets"
COLLECTION_URL = f"{SUPPLIER_BASE_URL}/collections/{COLLECTION_HANDLE}"
PRODUCTS_URL = f"{COLLECTION_URL}/products.json?limit=250"

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "suppliers" / "official-gear-direct"
IMAGE_DIR = ROOT / "images" / "suppliers" / "official-gear-direct"
OUTPUT_JSON = DATA_DIR / "pets-products.json"
OUTPUT_CSV = DATA_DIR / "pets-products.csv"
OUTPUT_VARIANTS_CSV = DATA_DIR / "pets-variants.csv"

USER_AGENT = "TinyTailsSupplierImporter/1.0 (+https://ecoprintinnovations.github.io/Tiny-Tails/)"


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if value:
            self.parts.append(value)

    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self.parts)).strip()


def request_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def request_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=60) as response:
        return response.read()


def html_to_text(value: str | None) -> str:
    parser = TextExtractor()
    parser.feed(html.unescape(value or ""))
    return parser.text()


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "item"


def money_from_minor_units(value: Any) -> str:
    if value in (None, ""):
        return ""
    try:
        return f"{int(value) / 100:.2f}"
    except (TypeError, ValueError):
        return str(value)


def image_extension(url: str, fallback: str = ".jpg") -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}:
        return suffix
    return fallback


def normalize_url(url: str) -> str:
    if url.startswith("//"):
        return f"https:{url}"
    return url


def download_image(url: str, target: Path) -> bool:
    url = normalize_url(url)
    if target.exists() and target.stat().st_size > 0:
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(request_bytes(url))
    return True


def normalize_product(product: dict[str, Any], enriched: dict[str, Any] | None) -> dict[str, Any]:
    source = enriched or product
    handle = source["handle"]
    product_url = f"{SUPPLIER_BASE_URL}/products/{handle}"
    body_html = source.get("description") or source.get("body_html") or product.get("body_html")
    description_text = html_to_text(body_html)
    tags = source.get("tags") or product.get("tags") or []
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split(",") if tag.strip()]

    raw_images = source.get("images") or product.get("images") or []
    images: list[dict[str, Any]] = []
    for index, raw_image in enumerate(raw_images, start=1):
        if isinstance(raw_image, str):
            src = raw_image
            raw_image = {"src": src}
        src = raw_image.get("src")
        if not src:
            continue
        src = normalize_url(src)
        local_name = f"{index:02d}-{slugify(source['title'])}{image_extension(src)}"
        local_path = IMAGE_DIR / handle / local_name
        images.append(
            {
                "position": raw_image.get("position", index),
                "src": src,
                "local_path": str(local_path.relative_to(ROOT)).replace("\\", "/"),
                "alt": raw_image.get("alt") or source["title"],
                "width": raw_image.get("width"),
                "height": raw_image.get("height"),
                "variant_ids": raw_image.get("variant_ids", []),
            }
        )

    variants = []
    for variant in source.get("variants", []):
        price = variant.get("price")
        compare_at_price = variant.get("compare_at_price")
        if isinstance(price, int):
            price = money_from_minor_units(price)
        if isinstance(compare_at_price, int):
            compare_at_price = money_from_minor_units(compare_at_price)
        variants.append(
            {
                "id": variant.get("id"),
                "title": variant.get("title"),
                "sku": variant.get("sku") or "",
                "barcode": variant.get("barcode") or "",
                "available": bool(variant.get("available")),
                "price": str(price or ""),
                "compare_at_price": str(compare_at_price or ""),
                "option1": variant.get("option1"),
                "option2": variant.get("option2"),
                "option3": variant.get("option3"),
                "requires_shipping": variant.get("requires_shipping"),
                "taxable": variant.get("taxable"),
                "weight": variant.get("weight") or variant.get("grams"),
                "inventory_management": variant.get("inventory_management"),
            }
        )

    available_variants = [variant for variant in variants if variant["available"]]
    prices = [float(variant["price"]) for variant in variants if variant["price"]]

    return {
        "supplier": SUPPLIER_NAME,
        "supplier_collection": COLLECTION_HANDLE,
        "supplier_product_id": source.get("id"),
        "title": source["title"],
        "handle": handle,
        "vendor": source.get("vendor") or product.get("vendor") or "",
        "product_type": source.get("type") or source.get("product_type") or product.get("product_type") or "",
        "tags": tags,
        "description_html": body_html or "",
        "description_text": description_text,
        "source_url": product_url,
        "featured_image": images[0]["local_path"] if images else "",
        "source_featured_image": images[0]["src"] if images else "",
        "images": images,
        "variants": variants,
        "available": len(available_variants) > 0,
        "available_variant_count": len(available_variants),
        "variant_count": len(variants),
        "price_min": f"{min(prices):.2f}" if prices else "",
        "price_max": f"{max(prices):.2f}" if prices else "",
        "created_at": source.get("created_at") or product.get("created_at"),
        "updated_at": source.get("updated_at") or product.get("updated_at"),
    }


def write_outputs(products: list[dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "supplier": SUPPLIER_NAME,
        "source_collection_url": COLLECTION_URL,
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "product_count": len(products),
        "products": products,
    }
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    product_fields = [
        "supplier",
        "title",
        "handle",
        "vendor",
        "product_type",
        "available",
        "available_variant_count",
        "variant_count",
        "price_min",
        "price_max",
        "featured_image",
        "source_featured_image",
        "source_url",
        "tags",
        "description_text",
    ]
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=product_fields)
        writer.writeheader()
        for product in products:
            row = {field: product.get(field, "") for field in product_fields}
            row["tags"] = ", ".join(product.get("tags", []))
            writer.writerow(row)

    variant_fields = [
        "product_handle",
        "product_title",
        "vendor",
        "variant_id",
        "variant_title",
        "sku",
        "barcode",
        "available",
        "price",
        "compare_at_price",
        "option1",
        "option2",
        "option3",
        "source_url",
    ]
    with OUTPUT_VARIANTS_CSV.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=variant_fields)
        writer.writeheader()
        for product in products:
            for variant in product["variants"]:
                writer.writerow(
                    {
                        "product_handle": product["handle"],
                        "product_title": product["title"],
                        "vendor": product["vendor"],
                        "variant_id": variant["id"],
                        "variant_title": variant["title"],
                        "sku": variant["sku"],
                        "barcode": variant["barcode"],
                        "available": variant["available"],
                        "price": variant["price"],
                        "compare_at_price": variant["compare_at_price"],
                        "option1": variant["option1"],
                        "option2": variant["option2"],
                        "option3": variant["option3"],
                        "source_url": product["source_url"],
                    }
                )


def main() -> None:
    parser = ArgumentParser(description="Sync Official Gear Direct pet products.")
    parser.add_argument("--skip-images", action="store_true", help="Only write JSON/CSV product data.")
    parser.add_argument("--workers", type=int, default=12, help="Parallel image download workers.")
    args = parser.parse_args()

    feed = request_json(PRODUCTS_URL)
    source_products = feed.get("products", [])
    normalized: list[dict[str, Any]] = []

    for index, product in enumerate(source_products, start=1):
        handle = product["handle"]
        print(f"[{index:03d}/{len(source_products)}] {handle}")
        enriched = None
        try:
            enriched = request_json(f"{SUPPLIER_BASE_URL}/products/{handle}.js")
        except (HTTPError, URLError, TimeoutError) as error:
            print(f"  warning: could not enrich product: {error}")

        normalized_product = normalize_product(product, enriched)
        normalized.append(normalized_product)
        time.sleep(0.1)

    write_outputs(normalized)

    downloaded = 0
    failed_images: list[str] = []
    if not args.skip_images:
        image_jobs = [
            (image["src"], ROOT / image["local_path"])
            for product in normalized
            for image in product["images"]
        ]
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
            futures = {
                executor.submit(download_image, source_url, target): (source_url, target)
                for source_url, target in image_jobs
            }
            for index, future in enumerate(as_completed(futures), start=1):
                source_url, target = futures[future]
                try:
                    if future.result():
                        downloaded += 1
                except (HTTPError, URLError, TimeoutError, ValueError) as error:
                    failed_images.append(f"{source_url} ({error})")
                if index % 50 == 0 or index == len(image_jobs):
                    print(f"  images checked: {index}/{len(image_jobs)}")

    print()
    print(f"Imported products: {len(normalized)}")
    print(f"Downloaded new images: {downloaded}" if not args.skip_images else "Skipped image downloads")
    print(f"JSON: {OUTPUT_JSON.relative_to(ROOT)}")
    print(f"Products CSV: {OUTPUT_CSV.relative_to(ROOT)}")
    print(f"Variants CSV: {OUTPUT_VARIANTS_CSV.relative_to(ROOT)}")
    if failed_images:
        print(f"Failed images: {len(failed_images)}")
        for failure in failed_images[:10]:
            print(f"  {failure}")


if __name__ == "__main__":
    main()
