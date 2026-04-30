(function () {
  const initShopCatalog = async () => {
    const grid = document.getElementById('payhip-product-grid');
    if (!grid) return;

    const count = document.getElementById('shop-count');
    const search = document.getElementById('shop-search');
    const category = document.getElementById('shop-category');
    const catalogUrl = grid.dataset.catalogUrl || '/assets/data/payhip-catalog.json';
    let products = [];

    const formatter = new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP',
    });

    const normalise = (value) => String(value || '').toLowerCase();

    const checkoutUrl = (url) => {
      const clean = String(url || '').trim();
      const marker = 'payhip.com/b/';
      if (!clean.includes(marker)) return clean;
      const slug = clean.split(marker)[1].replace(/\/$/, '');
      return `https://payhip.com/buy?link=${slug}`;
    };

    const productMatches = (product) => {
      const searchTerm = normalise(search && search.value);
      const categoryTerm = category ? category.value : '';
      if (categoryTerm && product.type !== categoryTerm) return false;
      if (!searchTerm) return true;

      const haystack = [
        product.title,
        product.vendor,
        product.type,
        product.description,
        product.tags && product.tags.join(' '),
        product.variants && product.variants.map((variant) => `${variant.title} ${variant.sku}`).join(' '),
      ].join(' ');

      return normalise(haystack).includes(searchTerm);
    };

    const priceLabel = (product) => {
      if (product.price_min === product.price_max) {
        return formatter.format(product.price_min);
      }
      return `${formatter.format(product.price_min)} - ${formatter.format(product.price_max)}`;
    };

    const variantLabel = (variant) => {
      const title = variant.title && variant.title !== 'Default Title' ? variant.title : 'Buy now';
      return `${title} - ${formatter.format(variant.price)}`;
    };

    const renderProduct = (product) => {
      const article = document.createElement('article');
      article.className = 'shop-card shop-product-card';

      const image = document.createElement('img');
      image.src = product.featured_image || '../static/favicon.svg';
      image.alt = product.title;
      image.className = 'shop-product-image';
      image.loading = 'lazy';
      image.decoding = 'async';
      article.append(image);

      const meta = document.createElement('p');
      meta.className = 'shop-product-meta';
      meta.textContent = product.type || 'Pet Supplies';
      article.append(meta);

      const heading = document.createElement('h2');
      heading.className = 'text-2xl font-semibold mb-2';
      heading.textContent = product.title;
      article.append(heading);

      const description = document.createElement('p');
      description.className = 'shop-product-description';
      description.textContent = product.description || 'A Tiny Tails selected product, ready for UK checkout.';
      article.append(description);

      const price = document.createElement('p');
      price.className = 'shop-product-price';
      price.textContent = priceLabel(product);
      article.append(price);

      const actions = document.createElement('div');
      actions.className = 'shop-variant-actions';

      product.variants.forEach((variant) => {
        const link = document.createElement('a');
        link.className = 'btn btn-primary shop-buy-button';
        link.href = variant.payhip_checkout_url || checkoutUrl(variant.payhip_url);
        link.target = '_blank';
        link.rel = 'noopener';
        link.textContent = variantLabel(variant);
        link.setAttribute('aria-label', `Buy ${product.title} ${variant.title} on Payhip`);
        actions.append(link);
      });

      article.append(actions);
      return article;
    };

    const render = () => {
      const filtered = products.filter(productMatches);
      grid.replaceChildren(...filtered.map(renderProduct));

      if (count) {
        count.textContent = `${filtered.length} products shown from ${products.length} locally stocked products.`;
      }

      if (filtered.length === 0) {
        const empty = document.createElement('article');
        empty.className = 'shop-card';
        empty.innerHTML = '<h2 class="text-2xl font-semibold mb-2">No products found</h2><p>Try a different search or category.</p>';
        grid.replaceChildren(empty);
      }
    };

    try {
      const response = await fetch(catalogUrl, { cache: 'no-store' });
      if (!response.ok) {
        throw new Error(`Catalogue request failed: ${response.status}`);
      }

      const catalog = await response.json();
      products = catalog.products || [];

      if (category && Array.isArray(catalog.categories)) {
        catalog.categories.forEach((name) => {
          const option = document.createElement('option');
          option.value = name;
          option.textContent = name;
          category.append(option);
        });
      }

      if (search) search.addEventListener('input', render);
      if (category) category.addEventListener('change', render);
      render();
    } catch (error) {
      console.error(error);
      grid.innerHTML = '<article class="shop-card"><h2 class="text-2xl font-semibold mb-2">Catalogue unavailable</h2><p>Please try again shortly, or contact Tiny Tails for product help.</p></article>';
      if (count) count.textContent = 'Catalogue could not be loaded.';
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initShopCatalog);
  } else {
    initShopCatalog();
  }
})();
