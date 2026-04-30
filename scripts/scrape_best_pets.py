"""Scrape Bestpets public catalogue products for Tiny Tails review.

The scraper is intentionally dependency-free and limits itself to the public
catalogue categories that fit Tiny Tails: dog, cat, small animal, bird, and
reptile products.
"""

from __future__ import annotations

import csv
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = "https://www.best-pets.co.uk"
CATALOGUE = f"{BASE}/trade/catalogue"
OUT_DIR = ROOT / "data" / "suppliers" / "best-pets"
IMG_DIR = ROOT / "images" / "suppliers" / "best-pets"
USER_AGENT = "Mozilla/5.0 (compatible; TinyTailsCatalogueBuilder/1.0)"

INCLUDED_PREFIXES = (
    "Cat ",
    "Dog ",
    "Dry Dog Food",
    "Dog & Cat ",
    "Cage Bird ",
    "Bird Substrates",
    "Wild Bird ",
    "Reptile ",
    "Small Animal ",
)

EXCLUDED_CATEGORY_WORDS = (
    "Aquarium",
    "Pond",
    "Horse",
    "Livestock",
    "Pigeon",
    "Poultry",
    "Home & Garden",
    "Seasonal",
    "Sundries",
    "Wildlife",
)


@dataclass(frozen=True)
class Category:
    name: str
    cid: str
    shop_group: str


def fetch(url: str, retries: int = 3) -> str:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=35) as response:
                return response.read().decode("utf-8", "ignore")
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            time.sleep(1.5 + attempt)
    raise RuntimeError(f"Failed to fetch {url}: {last_error}")


def strip_tags(value: str) -> str:
    value = re.sub(r"<br\s*/?>", " ", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(html.unescape(value).split())


def slugify(value: str) -> str:
    value = html.unescape(value).lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "item"


def absolute_url(href: str) -> str:
    return urllib.parse.urljoin(BASE, html.unescape(href))


def shop_group_for(category_name: str) -> str:
    name = category_name.lower()
    if name.startswith("dog") or name.startswith("dry dog") or name.startswith("dog & cat"):
        return "Dog Supplies"
    if name.startswith("cat"):
        return "Cat Supplies"
    if name.startswith("small animal"):
        return "Small Pets"
    if "bird" in name:
        return "Birds & Reptiles"
    if name.startswith("reptile"):
        return "Birds & Reptiles"
    return "Pet Supplies"


def category_is_included(name: str) -> bool:
    if any(word in name for word in EXCLUDED_CATEGORY_WORDS):
        return False
    return any(name.startswith(prefix) for prefix in INCLUDED_PREFIXES)


def discover_categories() -> list[Category]:
    text = fetch(CATALOGUE)
    categories: dict[str, Category] = {}
    for href, label_html in re.findall(r'<a[^>]+href="([^"]*cid=\d+[^"]*)"[^>]*>(.*?)</a>', text, re.S | re.I):
        label = strip_tags(label_html)
        cid_match = re.search(r"cid=(\d+)", html.unescape(href))
        if not label or not cid_match or not category_is_included(label):
            continue
        cid = cid_match.group(1)
        categories[cid] = Category(label, cid, shop_group_for(label))
    return sorted(categories.values(), key=lambda item: item.name)


def discover_subcategories(category: Category) -> list[tuple[str, str]]:
    text = fetch(f"{CATALOGUE}?cid={category.cid}")
    subcategories: dict[str, str] = {}
    for href, label_html in re.findall(r'<a[^>]+href="([^"]*scid=\d+[^"]*)"[^>]*>(.*?)</a>', text, re.S | re.I):
        label = strip_tags(label_html)
        scid_match = re.search(r"scid=(\d+)", html.unescape(href))
        if label and scid_match:
            subcategories[scid_match.group(1)] = label
    return sorted(subcategories.items(), key=lambda item: item[1])


def parse_products(page_html: str, category: Category, scid: str, subcategory_name: str) -> list[dict]:
    products: list[dict] = []
    for li in re.findall(r'<li>\s*<div class="image">(.*?)</li>', page_html, re.S | re.I):
        img_match = re.search(r'<img[^>]+src="([^"]+)"[^>]+alt="([^"]*)"', li, re.S | re.I)
        title_match = re.search(r"<h4>\s*<a[^>]*>(.*?)</a>\s*</h4>", li, re.S | re.I)
        pack_match = re.search(r'<p class="packsize">(.*?)</p>', li, re.S | re.I)
        price_match = re.search(r'<span class="pricevalue">(.*?)</span>', li, re.S | re.I)
        detail_match = re.search(r'data-mfp-src="([^"]+)"', li, re.S | re.I)
        if not title_match:
            continue

        pack_text = strip_tags(pack_match.group(1)) if pack_match else ""
        sku = ""
        size = pack_text
        if "•" in pack_text:
            size, sku = [part.strip() for part in pack_text.rsplit("•", 1)]
        elif pack_text:
            sku = pack_text.split()[-1]

        product = {
            "supplier": "Best Pets",
            "shop_group": category.shop_group,
            "category": category.name,
            "category_id": category.cid,
            "subcategory": subcategory_name,
            "subcategory_id": scid,
            "title": strip_tags(title_match.group(1)),
            "size": size,
            "sku": sku,
            "rsp": strip_tags(price_match.group(1)).replace("£", "") if price_match else "",
            "currency": "GBP",
            "image_url": absolute_url(img_match.group(1)) if img_match else "",
            "source_url": f"{CATALOGUE}?scid={scid}",
            "detail_url": absolute_url(detail_match.group(1)) if detail_match else "",
            "description": "",
            "local_image": "",
        }
        products.append(product)
    return products


def scrape_subcategory(category: Category, scid: str, subcategory_name: str) -> list[dict]:
    url = f"{CATALOGUE}?viewpp=ALL&scid={scid}"
    page_html = fetch(url)
    products = parse_products(page_html, category, scid, subcategory_name)
    if products:
        return products

    # Some pages ignore ALL; follow pagination as a fallback.
    first_page = fetch(f"{CATALOGUE}?scid={scid}")
    products.extend(parse_products(first_page, category, scid, subcategory_name))
    for href in sorted(set(re.findall(r'href="([^"]*s=\d+&amp;scid=' + re.escape(scid) + r'[^"]*)"', first_page))):
        page_html = fetch(absolute_url(href))
        products.extend(parse_products(page_html, category, scid, subcategory_name))
    unique: dict[str, dict] = {}
    for product in products:
        unique[product.get("sku") or product["title"]] = product
    return list(unique.values())


def hydrate_description(product: dict) -> None:
    if not product.get("detail_url"):
        return
    try:
        detail_html = fetch(product["detail_url"], retries=2)
    except RuntimeError:
        return
    parts = re.findall(r'<p class="description">(.*?)</p>', detail_html, re.S | re.I)
    product["description"] = " ".join(strip_tags(part) for part in parts if strip_tags(part))


def download_image(product: dict) -> None:
    image_url = product.get("image_url")
    sku = product.get("sku") or slugify(product["title"])
    if not image_url:
        return
    folder = IMG_DIR / slugify(product["shop_group"]) / slugify(product["category"])
    folder.mkdir(parents=True, exist_ok=True)
    suffix = Path(urllib.parse.urlparse(image_url).path).suffix or ".jpg"
    target = folder / f"{sku}{suffix}"
    if not target.exists():
        req = urllib.request.Request(image_url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=35) as response:
                target.write_bytes(response.read())
        except (urllib.error.URLError, TimeoutError):
            return
    product["local_image"] = str(target.relative_to(ROOT)).replace("\\", "/")


def enrich_product(product: dict) -> dict:
    hydrate_description(product)
    download_image(product)
    return product


def write_outputs(products: list[dict], categories: list[Category]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": CATALOGUE,
        "category_count": len(categories),
        "product_count": len(products),
        "categories": [category.__dict__ for category in categories],
        "products": products,
    }
    json_path = OUT_DIR / "catalogue-products.json"
    json_tmp_path = OUT_DIR / "catalogue-products.json.tmp"
    json_tmp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    json_tmp_path.replace(json_path)

    fieldnames = [
        "supplier",
        "shop_group",
        "category",
        "subcategory",
        "title",
        "size",
        "sku",
        "rsp",
        "currency",
        "description",
        "image_url",
        "local_image",
        "source_url",
        "detail_url",
    ]
    with (OUT_DIR / "catalogue-products.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(products)


def load_existing_products() -> list[dict]:
    path = OUT_DIR / "catalogue-products.json"
    if not path.exists() or path.stat().st_size == 0:
        csv_path = OUT_DIR / "catalogue-products.csv"
        if not csv_path.exists():
            return []
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return list(payload.get("products", []))


def main() -> None:
    categories = discover_categories()
    print(f"Discovered {len(categories)} matching top-level categories")
    products = load_existing_products()
    seen_skus: set[str] = {product.get("sku") or f"{product['title']}::{product['subcategory_id']}" for product in products}
    processed_subcategories: set[tuple[str, str]] = {
        (product.get("category_id", ""), product.get("subcategory_id", "")) for product in products
    }
    if products:
        print(f"Resuming with {len(products)} existing products")

    for category in categories:
        subcategories = discover_subcategories(category)
        print(f"{category.name}: {len(subcategories)} subcategories")
        for scid, subcategory_name in subcategories:
            if (category.cid, scid) in processed_subcategories:
                print(f"  - {subcategory_name}: already scraped")
                continue
            scraped = scrape_subcategory(category, scid, subcategory_name)
            print(f"  - {subcategory_name}: {len(scraped)} products")
            new_products: list[dict] = []
            for product in scraped:
                key = product.get("sku") or f"{product['title']}::{product['subcategory_id']}"
                if key in seen_skus:
                    continue
                seen_skus.add(key)
                new_products.append(product)
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(enrich_product, product) for product in new_products]
                for future in as_completed(futures):
                    products.append(future.result())
            write_outputs(products, categories)
            time.sleep(0.4)

    write_outputs(products, categories)
    print(f"Wrote {len(products)} products to {OUT_DIR}")


if __name__ == "__main__":
    main()
