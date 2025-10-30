from pathlib import Path
from textwrap import dedent

ROOT = Path('images')


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def svg_template(width: int, height: int, gradient_id: str, gradient: tuple[str, str], shapes: str) -> str:
    view_box = f"0 0 {width} {height}"
    x2, y2 = (1, 0) if width >= height else (0, 1)
    corner_radius = int(min(width, height) * 0.04)
    return dedent(
        f"""
        <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{width}\" height=\"{height}\" viewBox=\"{view_box}\" role=\"img\" aria-hidden=\"true\">
            <defs>
                <linearGradient id=\"{gradient_id}\" x1=\"0\" y1=\"0\" x2=\"{x2}\" y2=\"{y2}\">
                    <stop offset=\"0%\" stop-color=\"{gradient[0]}\" />
                    <stop offset=\"100%\" stop-color=\"{gradient[1]}\" />
                </linearGradient>
            </defs>
            <rect width=\"100%\" height=\"100%\" fill=\"url(#{gradient_id})\" rx=\"{corner_radius}\" />
            {shapes}
        </svg>
        """
    ).strip()


def fmt_points(points: list[tuple[float, float]]) -> str:
    return ' '.join(f"{x:.1f},{y:.1f}" for x, y in points)


def rounded_rect(x: float, y: float, w: float, h: float, r: float, **styles) -> str:
    attrs = ' '.join(f"{k.replace('_', '-')}=\"{v}\"" for k, v in styles.items())
    return f"<rect x=\"{x}\" y=\"{y}\" width=\"{w}\" height=\"{h}\" rx=\"{r}\" ry=\"{r}\" {attrs}/>"


def circle(cx: float, cy: float, r: float, **styles) -> str:
    attrs = ' '.join(f"{k.replace('_', '-')}=\"{v}\"" for k, v in styles.items())
    return f"<circle cx=\"{cx}\" cy=\"{cy}\" r=\"{r}\" {attrs}/>"


def ellipse(cx: float, cy: float, rx: float, ry: float, **styles) -> str:
    attrs = ' '.join(f"{k.replace('_', '-')}=\"{v}\"" for k, v in styles.items())
    return f"<ellipse cx=\"{cx}\" cy=\"{cy}\" rx=\"{rx}\" ry=\"{ry}\" {attrs}/>"


def line(x1: float, y1: float, x2: float, y2: float, **styles) -> str:
    attrs = ' '.join(f"{k.replace('_', '-')}=\"{v}\"" for k, v in styles.items())
    return f"<line x1=\"{x1}\" y1=\"{y1}\" x2=\"{x2}\" y2=\"{y2}\" {attrs}/>"


def polygon(points: list[tuple[float, float]], **styles) -> str:
    attrs = ' '.join(f"{k.replace('_', '-')}=\"{v}\"" for k, v in styles.items())
    return f"<polygon points=\"{fmt_points(points)}\" {attrs}/>"


def bone(cx: float, cy: float, w: float, h: float, **styles) -> str:
    left = circle(cx - w / 2 + h / 4, cy, h / 2, **styles)
    right = circle(cx + w / 2 - h / 4, cy, h / 2, **styles)
    rect = rounded_rect(cx - w / 2 + h / 4, cy - h / 4, w - h / 2, h / 2, h / 4, **styles)
    return f"<g>{left}{right}{rect}</g>"


def paw(cx: float, cy: float, r: float, fill: str, stroke: str | None = None, stroke_width: float = 0) -> str:
    toes = []
    offsets = [(-0.9, -1.1), (-0.3, -1.3), (0.3, -1.3), (0.9, -1.1)]
    for ox, oy in offsets:
        toes.append(circle(cx + ox * r, cy + oy * r, r * 0.45, fill=fill, stroke=stroke, stroke_width=stroke_width))
    pad = circle(cx, cy, r, fill=fill, stroke=stroke, stroke_width=stroke_width)
    return f"<g>{''.join(toes)}{pad}</g>"


def kibble_scatter(cx: float, cy: float, r: float, count: int, fill: str) -> str:
    pts = []
    for i in range(count):
        angle = (i / count) * 3.1415 * 1.6
        px = cx + (i % 4 - 1.5) * r * 1.2
        py = cy + (i // 4) * r * 1.3
        pts.append(circle(px, py, r, fill=fill))
    return ''.join(pts)


def spray_mist(cx: float, cy: float, r: float, fill: str) -> str:
    circles = []
    for i in range(6):
        circles.append(circle(cx + i * r * 0.9, cy + ((-1) ** i) * r * 0.3, r * (0.6 + 0.05 * i), fill=fill, opacity=0.55))
    return ''.join(circles)


def render_category(slug: str) -> str:
    base_w, base_h = 1200, 900
    gradient = {
        'food-kibble-bowl': ('#f8d8b0', '#f1a889'),
        'treats-biscuits-hand': ('#f7d7e0', '#f9a8be'),
        'toys-rope-tug': ('#d8eefe', '#8dc6ff'),
        'beds-memory-foam': ('#e9e4ff', '#b9b2f5'),
        'collars-leads': ('#f7f4d9', '#e5d68f'),
        'puppy-essentials': ('#f4f1ff', '#d9d0ff'),
        'healthcare-grooming': ('#dff5ed', '#9ed8c1'),
        'travel-car-crate': ('#e2f1ff', '#9bc2e6'),
        'training-clicker': ('#ffe8d9', '#ffb88c'),
    }[slug]
    shapes: list[str] = []
    if slug == 'food-kibble-bowl':
        shapes.append(ellipse(500, 550, 360, 140, fill='#fef6ed', stroke='#c46b3a', stroke_width=18))
        shapes.append(ellipse(500, 470, 300, 90, fill='#f7e1c5', stroke='#c46b3a', stroke_width=12))
        shapes.append(kibble_scatter(500, 470, 28, 8, '#c47930'))
    elif slug == 'treats-biscuits-hand':
        shapes.append(rounded_rect(630, 380, 260, 320, 40, fill='#ffe3ef', stroke='#c45f88', stroke_width=16))
        shapes.append(bone(360, 500, 320, 160, fill='#fff1cc', stroke='#c48f3a', stroke_width=16))
        shapes.append(bone(300, 390, 220, 120, fill='#fff9dd', stroke='#c48f3a', stroke_width=12))
    elif slug == 'toys-rope-tug':
        shapes.append(line(180, 470, 820, 470, stroke='#ff7f7f', stroke_width=70, stroke_linecap='round'))
        shapes.append(ellipse(180, 470, 120, 140, fill='#ffd0d0', stroke='#ff7f7f', stroke_width=20))
        shapes.append(ellipse(820, 470, 120, 140, fill='#ffd0d0', stroke='#ff7f7f', stroke_width=20))
        tassels = []
        for i in range(6):
            tassels.append(line(500, 470, 500 + (i - 2.5) * 90, 320 + (i % 2) * 220, stroke='#ffb347', stroke_width=24, stroke_linecap='round'))
        shapes.append('<g>' + ''.join(tassels) + '</g>')
    elif slug == 'beds-memory-foam':
        shapes.append(rounded_rect(220, 520, 560, 260, 90, fill='#fcefff', stroke='#8c75d6', stroke_width=18))
        shapes.append(ellipse(500, 460, 260, 120, fill='#fff9ff', stroke='#8c75d6', stroke_width=14))
        shapes.append(paw(500, 560, 70, fill='#c6b2f2'))
    elif slug == 'collars-leads':
        shapes.append(ellipse(500, 520, 340, 200, fill='none', stroke='#d18f42', stroke_width=46))
        shapes.append(ellipse(500, 520, 300, 160, fill='none', stroke='#fce4a2', stroke_width=24))
        shapes.append(line(300, 650, 140, 780, stroke='#b16a27', stroke_width=38, stroke_linecap='round'))
        shapes.append(line(140, 780, 420, 820, stroke='#b16a27', stroke_width=38, stroke_linecap='round'))
    elif slug == 'puppy-essentials':
        shapes.append(rounded_rect(320, 520, 360, 260, 50, fill='#fff1f9', stroke='#b89be6', stroke_width=14))
        shapes.append(paw(500, 560, 60, fill='#d0bdf4'))
        shapes.append(ellipse(420, 400, 120, 80, fill='#ffe6f4', stroke='#b89be6', stroke_width=10))
        shapes.append(rounded_rect(580, 400, 140, 170, 24, fill='#fff1f9', stroke='#b89be6', stroke_width=10))
    elif slug == 'healthcare-grooming':
        shapes.append(rounded_rect(320, 360, 160, 320, 40, fill='#ffffff', stroke='#58b793', stroke_width=14))
        shapes.append(rounded_rect(520, 320, 220, 360, 40, fill='#ffffff', stroke='#58b793', stroke_width=14))
        shapes.append(ellipse(630, 370, 90, 70, fill='#58b793', opacity=0.85))
        shapes.append(paw(380, 600, 55, fill='#8ed1b6'))
    elif slug == 'travel-car-crate':
        shapes.append(rounded_rect(250, 420, 540, 300, 60, fill='#ffffff', stroke='#4d8cc9', stroke_width=16))
        shapes.append(rounded_rect(300, 470, 440, 160, 40, fill='none', stroke='#4d8cc9', stroke_width=12))
        shapes.append(rounded_rect(360, 490, 140, 110, 20, fill='#c9def5'))
        shapes.append(rounded_rect(520, 490, 140, 110, 20, fill='#c9def5'))
        shapes.append(circle(320, 720, 60, fill='#4d8cc9'))
        shapes.append(circle(740, 720, 60, fill='#4d8cc9'))
    elif slug == 'training-clicker':
        shapes.append(ellipse(500, 540, 320, 180, fill='#ffe3cc', stroke='#e68a3a', stroke_width=18))
        shapes.append(ellipse(500, 520, 220, 140, fill='#fff5e6', stroke='#e68a3a', stroke_width=12))
        shapes.append(circle(500, 520, 70, fill='#f29d3c'))
        shapes.append(line(700, 420, 900, 260, stroke='#f29d3c', stroke_width=24, stroke_linecap='round'))
    return svg_template(base_w, base_h, f"grad-{slug}", gradient, ''.join(shapes))


def render_product(slug: str) -> str:
    base_w = base_h = 900
    gradient = ('#ffffff', '#f4f4f4')
    accent = '#ff9f68'
    shapes: list[str] = []
    if slug == 'gourmet-meal':
        shapes.append(ellipse(450, 540, 280, 120, fill='#fff3e0', stroke='#c3702f', stroke_width=18))
        shapes.append(ellipse(450, 470, 230, 80, fill='#f5d2aa', stroke='#c3702f', stroke_width=12))
        shapes.append(kibble_scatter(450, 470, 26, 9, '#c27030'))
    elif slug == 'crunchy-biscuits':
        shapes.append(bone(330, 480, 240, 130, fill='#fff1cc', stroke='#c48f3a', stroke_width=16))
        shapes.append(bone(520, 520, 240, 130, fill='#ffe7b0', stroke='#c48f3a', stroke_width=16))
        shapes.append(bone(430, 380, 220, 120, fill='#fff6d5', stroke='#c48f3a', stroke_width=12))
    elif slug == 'snuggle-bed':
        shapes.append(rounded_rect(240, 520, 420, 240, 90, fill='#f8e9ff', stroke='#a678d1', stroke_width=18))
        shapes.append(ellipse(450, 460, 220, 120, fill='#ffffff', stroke='#a678d1', stroke_width=12))
        shapes.append(paw(450, 560, 60, fill='#c5a5e6'))
    elif slug == 'glow-collar':
        shapes.append(ellipse(450, 520, 260, 160, fill='none', stroke='#d47f2c', stroke_width=30))
        shapes.append(ellipse(450, 520, 220, 120, fill='none', stroke='#ffe3b0', stroke_width=24))
        shapes.append(rounded_rect(600, 480, 160, 80, 30, fill='#ffb347', stroke='#d47f2c', stroke_width=14))
    elif slug == 'gentle-shampoo':
        shapes.append(rounded_rect(320, 280, 220, 420, 110, fill='#f0f8ff', stroke='#6f9bc4', stroke_width=16))
        shapes.append(circle(430, 240, 60, fill='#6f9bc4'))
        shapes.append(spray_mist(520, 340, 32, '#a8cee8'))
    elif slug == 'daily-vitamins':
        shapes.append(rounded_rect(320, 320, 260, 360, 80, fill='#ffe6cc', stroke='#d47f2c', stroke_width=16))
        shapes.append(circle(450, 520, 120, fill='#ffbe7a', opacity=0.7))
        for i in range(4):
            shapes.append(ellipse(360 + i * 80, 620, 28, 16, fill='#d47f2c', opacity=0.7))
    elif slug == 'chew-toy':
        shapes.append(line(240, 520, 660, 520, stroke='#ff8aa6', stroke_width=80, stroke_linecap='round'))
        shapes.append(ellipse(240, 520, 120, 140, fill='#ffd0df', stroke='#ff8aa6', stroke_width=22))
        shapes.append(ellipse(660, 520, 120, 140, fill='#ffd0df', stroke='#ff8aa6', stroke_width=22))
    elif slug == 'training-treats':
        shapes.append(rounded_rect(320, 320, 260, 360, 60, fill='#ffe3ef', stroke='#d96a99', stroke_width=16))
        shapes.append(paw(450, 520, 60, fill='#f7c5dd'))
        shapes.append(kibble_scatter(450, 640, 20, 6, '#d96a99'))
    elif slug == 'travel-bag':
        shapes.append(rounded_rect(280, 400, 340, 260, 50, fill='#e0edff', stroke='#5f8ed9', stroke_width=16))
        shapes.append(rounded_rect(320, 460, 260, 140, 30, fill='#b7cff5'))
        shapes.append(line(360, 380, 580, 380, stroke='#5f8ed9', stroke_width=24, stroke_linecap='round'))
    elif slug == 'calming-spray':
        shapes.append(rounded_rect(360, 320, 200, 360, 70, fill='#e4f1ff', stroke='#4f89c2', stroke_width=16))
        shapes.append(circle(460, 280, 50, fill='#4f89c2'))
        shapes.append(spray_mist(540, 360, 26, '#8bb5de'))
    elif slug == 'dental-sticks':
        for i in range(4):
            shapes.append(rounded_rect(300 + i * 60, 360, 50, 320, 24, fill='#d0e4c2', stroke='#739b59', stroke_width=10))
    elif slug == 'luxury-lead':
        shapes.append(ellipse(450, 540, 320, 200, fill='none', stroke='#c28b52', stroke_width=36))
        shapes.append(line(220, 620, 680, 720, stroke='#9d642b', stroke_width=32, stroke_linecap='round'))
        shapes.append(line(680, 720, 520, 780, stroke='#9d642b', stroke_width=32, stroke_linecap='round'))
    elif slug == 'puppy-essentials':
        shapes.append(rounded_rect(300, 520, 300, 240, 50, fill='#fbe8ff', stroke='#c59ae6', stroke_width=16))
        shapes.append(paw(450, 560, 60, fill='#d6b7f2'))
        shapes.append(circle(360, 420, 60, fill='#f7d6ff'))
    else:
        shapes.append(circle(450, 450, 200, fill=accent, opacity=0.3))
    return svg_template(base_w, base_h, f"grad-{slug}", gradient, ''.join(shapes))


def render_advice(slug: str) -> str:
    base_w, base_h = 1600, 1000
    gradient = {
        'perfect-fit': ('#f0f4ff', '#c8d9ff'),
        'id-tags': ('#ffeef3', '#f8bfd5'),
        'chew-safety': ('#e8fff5', '#aee5c3'),
    }[slug]
    shapes: list[str] = []
    if slug == 'perfect-fit':
        shapes.append(rounded_rect(360, 260, 520, 480, 90, fill='#ffffff', stroke='#7f95d9', stroke_width=18))
        shapes.append(circle(620, 240, 120, fill='#7f95d9'))
        shapes.append(line(380, 520, 340, 720, stroke='#7f95d9', stroke_width=24))
        shapes.append(line(880, 520, 920, 720, stroke='#7f95d9', stroke_width=24))
    elif slug == 'id-tags':
        shapes.append(circle(520, 420, 160, fill='#ffffff', stroke='#e16a98', stroke_width=18))
        shapes.append(circle(520, 420, 80, fill='#f8bfd5'))
        shapes.append(line(520, 260, 520, 180, stroke='#e16a98', stroke_width=26, stroke_linecap='round'))
        shapes.append(circle(520, 150, 40, fill='#e16a98'))
        shapes.append(paw(860, 560, 90, fill='#f8bfd5'))
    elif slug == 'chew-safety':
        shapes.append(line(360, 560, 1040, 560, stroke='#54b27b', stroke_width=70, stroke_linecap='round'))
        shapes.append(ellipse(360, 560, 160, 190, fill='#c2f0d8', stroke='#54b27b', stroke_width=20))
        shapes.append(ellipse(1040, 560, 160, 190, fill='#c2f0d8', stroke='#54b27b', stroke_width=20))
        shapes.append(paw(700, 420, 90, fill='#9cd9b5'))
    return svg_template(base_w, base_h, f"grad-{slug}", gradient, ''.join(shapes))


def render_promo(slug: str) -> str:
    base_w, base_h = 2000, 1200
    gradient = {
        'gift-cards-generic': ('#ffe3f0', '#ffc3da'),
        'mix-and-match-treats': ('#fff3d8', '#ffd79c'),
    }[slug]
    shapes: list[str] = []
    if slug == 'gift-cards-generic':
        shapes.append(rounded_rect(520, 380, 960, 520, 60, fill='#ffffff', stroke='#d376a8', stroke_width=26))
        shapes.append(paw(1000, 620, 120, fill='#ffc3da'))
        shapes.append(polygon([(520, 380), (520, 520), (400, 450)], fill='#d376a8', opacity=0.6))
        shapes.append(polygon([(1480, 380), (1480, 520), (1600, 450)], fill='#d376a8', opacity=0.6))
    elif slug == 'mix-and-match-treats':
        shapes.append(bone(1000, 600, 900, 260, fill='#fff1cc', stroke='#d48f3a', stroke_width=28))
        shapes.append(bone(1000, 480, 600, 200, fill='#ffe8b0', stroke='#d48f3a', stroke_width=20))
        shapes.append(paw(520, 760, 120, fill='#ffd79c'))
        shapes.append(paw(1480, 420, 100, fill='#ffd79c'))
    return svg_template(base_w, base_h, f"grad-{slug}", gradient, ''.join(shapes))


def render_brand(name: str, label: str, colors: tuple[str, str]) -> str:
    width, height = 240, 80
    view_box = "0 0 240 80"
    gradient_id = f"grad-brand-{name}"
    return dedent(
        f"""
        <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{width}\" height=\"{height}\" viewBox=\"{view_box}\" role=\"img\">
            <defs>
                <linearGradient id=\"{gradient_id}\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"1\">
                    <stop offset=\"0%\" stop-color=\"{colors[0]}\" />
                    <stop offset=\"100%\" stop-color=\"{colors[1]}\" />
                </linearGradient>
            </defs>
            <rect width=\"100%\" height=\"100%\" rx=\"16\" fill=\"#ffffff\" stroke=\"{colors[0]}\" stroke-width=\"4\" />
            <text x=\"50%\" y=\"55%\" font-family=\"'Poppins', 'Arial', sans-serif\" font-size=\"28\" font-weight=\"600\" text-anchor=\"middle\" fill=\"url(#{gradient_id})\">{label}</text>
        </svg>
        """
    ).strip()


def main() -> None:
    ROOT.mkdir(exist_ok=True)

    categories = [
        'food-kibble-bowl', 'treats-biscuits-hand', 'toys-rope-tug', 'beds-memory-foam',
        'collars-leads', 'puppy-essentials', 'healthcare-grooming', 'travel-car-crate', 'training-clicker'
    ]
    for slug in categories:
        svg = render_category(slug)
        base = ROOT / 'dog-supplies' / 'categories' / slug
        ensure_dir(base.parent)
        for width in (480, 800, 1200):
            height = {480: 360, 800: 600, 1200: 900}[width]
            out = svg.replace('width="1200"', f'width="{width}"').replace('height="900"', f'height="{height}"')
            (base.parent / f"{slug}-{width}.svg").write_text(out)

    advice = ['perfect-fit', 'id-tags', 'chew-safety']
    for slug in advice:
        svg = render_advice(slug)
        base = ROOT / 'dog-supplies' / 'advice' / slug
        ensure_dir(base.parent)
        for width, height in ((800, 500), (1200, 750), (1600, 1000)):
            out = svg.replace('width="1600"', f'width="{width}"').replace('height="1000"', f'height="{height}"')
            (base.parent / f"{slug}-{width}.svg").write_text(out)

    promos = ['gift-cards-generic', 'mix-and-match-treats']
    for slug in promos:
        svg = render_promo(slug)
        base = ROOT / 'dog-supplies' / 'promo' / slug
        ensure_dir(base.parent)
        for width, height in ((960, 576), (1400, 840), (2000, 1200)):
            out = svg.replace('width="2000"', f'width="{width}"').replace('height="1200"', f'height="{height}"')
            (base.parent / f"{slug}-{width}.svg").write_text(out)

    products = [
        'gourmet-meal', 'crunchy-biscuits', 'snuggle-bed', 'glow-collar', 'gentle-shampoo',
        'daily-vitamins', 'chew-toy', 'training-treats', 'travel-bag', 'calming-spray',
        'dental-sticks', 'luxury-lead', 'puppy-essentials'
    ]
    for slug in products:
        svg = render_product(slug)
        base = ROOT / 'dog-supplies' / 'products' / slug
        ensure_dir(base.parent)
        for width in (360, 600, 900):
            height = width
            out = svg.replace('width="900"', f'width="{width}"').replace('height="900"', f'height="{height}"')
            (base.parent / f"{slug}-{width}.svg").write_text(out)

    brands = {
        'canagan': ('Canagan', ('#2c5444', '#4f8c6d')),
        'frogg': ('Frogg', ('#255a8a', '#5bb3d1')),
        'more': ('more.', ('#4c2f6b', '#8f5bb0')),
        'tribal': ('Tribal', ('#1d4d4f', '#49a17a')),
        'green-elk': ('Green Elk', ('#265c35', '#63b672')),
        'great-and-small': ('Great & Small', ('#452e5d', '#a07aca')),
        'yora': ('Yora', ('#3c4f91', '#6c87ff')),
        'dogwood': ('Dogwood', ('#5a3b2c', '#c28c58')),
        'mcadams': ('McAdams', ('#3a3a3a', '#8c8c8c')),
        'greenacres': ('Greenacres', ('#2f6f48', '#7fd19a')),
    }
    brand_dir = ROOT / 'brands'
    ensure_dir(brand_dir)
    for name, (label, colors) in brands.items():
        (brand_dir / f"{name}.svg").write_text(render_brand(name, label, colors))


if __name__ == '__main__':
    main()
