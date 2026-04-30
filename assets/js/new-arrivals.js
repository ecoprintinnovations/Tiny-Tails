(function () {
  const arrivalPicks = [
    {
      handle: 'official-gear-direct-minnie-dog-lead-leash',
      badge: 'Lead',
      fallbackTerms: ['lead', 'leash'],
    },
    {
      handle: 'official-gear-direct-minnie-mouse-harness-for-dogs',
      badge: 'Harness',
      fallbackTerms: ['harness'],
    },
    {
      handle: 'best-pets-bp-373088',
      badge: 'Bed',
      fallbackTerms: ['bed', 'cosy'],
    },
    {
      handle: 'best-pets-bp-492311',
      badge: 'Premium Food',
      fallbackTerms: ['iams', 'food', 'chicken'],
    },
  ];

  const initNewArrivals = async () => {
    const grid = document.getElementById('new-arrivals-grid');
    if (!grid) return;

    const catalogUrl = grid.dataset.catalogUrl || 'assets/data/payhip-catalog.json';
    const formatter = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' });

    const pagePath = (path) => {
      if (!path) return 'static/favicon.svg';
      if (/^https?:\/\//.test(path)) return path;
      return path.replace(/^(\.\.\/)+/, '').replace(/^\//, '');
    };

    const matchesTerms = (product, terms) => {
      const haystack = [
        product.title,
        product.description,
        product.product_type,
        product.shop_group,
        ...(product.tags || []),
      ].join(' ').toLowerCase();

      return terms.every((term) => haystack.includes(term));
    };

    const ratingHtml = (index) => {
      const stars = index === 1 ? 4 : 5;
      return Array.from({ length: 5 }, (_, starIndex) => (
        `<i class="${starIndex < stars ? 'fas' : 'far'} fa-star"></i>`
      )).join('');
    };

    const productCard = ({ product, badge }, index) => {
      const variant = product.variants[0];
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
          <div class="rating" aria-label="${index === 1 ? 'Four' : 'Five'} star new arrival">
            ${ratingHtml(index)}
          </div>
          <a href="${variant.payhip_checkout_url}" class="btn btn-pink" target="_blank" rel="noopener">Buy Now</a>
        </div>
      `;
      return card;
    };

    const pickArrivals = (products) => {
      const byHandle = new Map(products.map((product) => [product.handle, product]));
      const selectedHandles = new Set();

      return arrivalPicks.map((pick) => {
        let product = byHandle.get(pick.handle);

        if (!product) {
          product = products
            .filter((candidate) => !selectedHandles.has(candidate.handle))
            .filter((candidate) => matchesTerms(candidate, pick.fallbackTerms))
            .sort((a, b) => b.price_max - a.price_max)[0];
        }

        if (product) selectedHandles.add(product.handle);
        return product ? { product, badge: pick.badge } : null;
      }).filter(Boolean);
    };

    try {
      const response = await fetch(catalogUrl, { cache: 'no-store' });
      if (!response.ok) throw new Error(`Catalogue request failed: ${response.status}`);

      const catalog = await response.json();
      const products = (catalog.products || []).filter((product) => (
        product.variants?.[0]?.payhip_checkout_url && product.price_min > 0
      ));
      const arrivals = pickArrivals(products);

      if (!arrivals.length) throw new Error('No new arrival products could be selected.');
      grid.replaceChildren(...arrivals.map(productCard));
    } catch (error) {
      console.error(error);
      grid.innerHTML = '<div class="product-card"><div class="product-info"><h3>New arrivals unavailable</h3><p>Please browse the main shop while we refresh this section.</p></div></div>';
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initNewArrivals);
  } else {
    initNewArrivals();
  }
})();
