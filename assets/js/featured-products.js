(function () {
  const featuredHandles = [
    'best-pets-bp-174751',
    'best-pets-bp-565943',
    'best-pets-bp-757409',
    'official-gear-direct-copy-of-gel-cooling-mats-4-sizes',
  ];

  const fallbackGroups = ['Small Pets', 'Cat Supplies', 'Birds & Reptiles', 'Dog Supplies'];

  const initFeaturedProducts = async () => {
    const grid = document.getElementById('featured-product-grid');
    if (!grid) return;

    const catalogUrl = grid.dataset.catalogUrl || 'assets/data/payhip-catalog.json';
    const formatter = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' });

    const pagePath = (path) => {
      if (!path) return 'static/favicon.svg';
      if (/^https?:\/\//.test(path)) return path;
      return path.replace(/^(\.\.\/)+/, '').replace(/^\//, '');
    };

    const ratingHtml = (index) => {
      const stars = index === 3 ? 4 : 5;
      return Array.from({ length: 5 }, (_, starIndex) => (
        `<i class="${starIndex < stars ? 'fas' : 'far'} fa-star"></i>`
      )).join('');
    };

    const productCard = (product, index) => {
      const variant = product.variants[0];
      const badge = index === 0 ? 'High Value' : product.shop_group;
      const card = document.createElement('div');
      card.className = 'product-card';
      card.innerHTML = `
        <div class="product-img">
          <img src="${pagePath(product.featured_image)}" alt="${product.title}" loading="lazy" decoding="async">
          <span class="product-badge">${badge}</span>
        </div>
        <div class="product-info">
          <h3>${product.title}</h3>
          <div class="product-price">
            <span class="current-price">${formatter.format(product.price_min)}</span>
          </div>
          <div class="rating" aria-label="${index === 3 ? 'Four' : 'Five'} star featured pick">
            ${ratingHtml(index)}
          </div>
          <a href="${variant.payhip_checkout_url}" class="btn btn-pink" target="_blank" rel="noopener">Buy Now</a>
        </div>
      `;
      return card;
    };

    const pickProducts = (products) => {
      const byHandle = new Map(products.map((product) => [product.handle, product]));
      const selected = featuredHandles.map((handle) => byHandle.get(handle)).filter(Boolean);
      const selectedHandles = new Set(selected.map((product) => product.handle));

      for (const group of fallbackGroups) {
        if (selected.some((product) => product.shop_group === group)) continue;
        const fallback = products
          .filter((product) => product.shop_group === group && !selectedHandles.has(product.handle))
          .sort((a, b) => b.price_max - a.price_max)[0];
        if (fallback) {
          selected.push(fallback);
          selectedHandles.add(fallback.handle);
        }
      }

      return selected.slice(0, 4);
    };

    try {
      const response = await fetch(catalogUrl, { cache: 'no-store' });
      if (!response.ok) throw new Error(`Catalogue request failed: ${response.status}`);
      const catalog = await response.json();
      const products = (catalog.products || []).filter((product) => (
        product.variants?.[0]?.payhip_checkout_url && product.price_min > 0
      ));
      const featured = pickProducts(products);
      grid.replaceChildren(...featured.map(productCard));
    } catch (error) {
      console.error(error);
      grid.innerHTML = '<div class="product-card"><div class="product-info"><h3>Featured products unavailable</h3><p>Please browse the main shop while we refresh this section.</p></div></div>';
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initFeaturedProducts);
  } else {
    initFeaturedProducts();
  }
})();
