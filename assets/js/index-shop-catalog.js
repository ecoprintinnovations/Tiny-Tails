(function () {
  const initIndexShopCatalog = async () => {
    const grid = document.getElementById('payhip-home-product-grid');
    if (!grid) return;

    const count = document.getElementById('catalog-count');
    const typeFilter = document.getElementById('catalog-filter');
    const searchInput = document.querySelector('.search-bar input');
    const searchButton = document.querySelector('.search-bar button');
    const catalogUrl = grid.dataset.catalogUrl || 'assets/data/payhip-catalog.json';
    const formatter = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' });
    let products = [];
    let activeGroup = '';

    const normalise = (value) => String(value || '').toLowerCase();

    const pagePath = (path) => {
      if (!path) return 'static/favicon.svg';
      if (/^https?:\/\//.test(path)) return path;
      return path.replace(/^(\.\.\/)+/, '').replace(/^\//, '');
    };

    const checkoutUrl = (url) => {
      const clean = String(url || '').trim();
      const marker = 'payhip.com/b/';
      if (!clean.includes(marker)) return clean;
      const slug = clean.split(marker)[1].replace(/\/$/, '');
      return `https://payhip.com/buy?link=${slug}`;
    };

    const priceLabel = (product) => {
      if (product.price_min === product.price_max) return formatter.format(product.price_min);
      return `${formatter.format(product.price_min)} - ${formatter.format(product.price_max)}`;
    };

    const activeGroupName = () => ({
      dog: 'Dog Supplies',
      cat: 'Cat Supplies',
      small: 'Small Pets',
      birds: 'Birds & Reptiles',
    }[activeGroup] || '');

    const groupKeyFromName = (name) => ({
      'Dog Supplies': 'dog',
      'Cat Supplies': 'cat',
      'Small Pets': 'small',
      'Birds & Reptiles': 'birds',
    }[name] || '');

    const groupMatches = (product) => {
      if (!activeGroup) return true;
      return product.shop_group === activeGroupName();
    };

    const searchMatches = (product) => {
      const searchTerm = normalise(searchInput && searchInput.value);
      if (!searchTerm) return true;

      const haystack = normalise([
        product.title,
        product.vendor,
        product.type,
        product.description,
        product.tags && product.tags.join(' '),
        product.variants && product.variants.map((variant) => `${variant.title} ${variant.sku}`).join(' '),
      ].join(' '));

      return haystack.includes(searchTerm);
    };

    const rebuildTypeFilter = (preferredType = '') => {
      if (!typeFilter) return;

      const currentType = preferredType || typeFilter.value;
      const groupProducts = products.filter((product) => groupMatches(product) && searchMatches(product));
      const types = [...new Set(groupProducts.map((product) => product.type).filter(Boolean))].sort();

      typeFilter.replaceChildren();
      const defaultOption = document.createElement('option');
      defaultOption.value = '';
      defaultOption.textContent = 'All product types';
      typeFilter.append(defaultOption);

      types.forEach((name) => {
        const option = document.createElement('option');
        option.value = name;
        option.textContent = name;
        typeFilter.append(option);
      });

      typeFilter.value = types.includes(currentType) ? currentType : '';
    };

    const productMatches = (product) => {
      const typeTerm = typeFilter ? typeFilter.value : '';
      if (typeTerm && product.type !== typeTerm) return false;
      if (!groupMatches(product)) return false;
      return searchMatches(product);
    };

    const renderProduct = (product, index) => {
      const card = document.createElement('div');
      card.className = 'product-card';

      const imageWrap = document.createElement('div');
      imageWrap.className = 'product-img';

      const image = document.createElement('img');
      image.src = pagePath(product.featured_image);
      image.alt = product.title;
      image.loading = 'lazy';
      image.decoding = 'async';
      imageWrap.append(image);

      const info = document.createElement('div');
      info.className = 'product-info';

      const title = document.createElement('h3');
      title.textContent = product.title;
      info.append(title);

      const description = document.createElement('p');
      description.textContent = product.description || 'A Tiny Tails selected product, ready for secure Payhip checkout.';
      info.append(description);

      const price = document.createElement('div');
      price.className = 'product-price';
      price.innerHTML = `<span class="current-price">${priceLabel(product)}</span>`;
      info.append(price);

      const actions = document.createElement('div');
      actions.className = 'variant-buttons';
      product.variants.forEach((variant, variantIndex) => {
        const button = document.createElement('a');
        button.href = variant.payhip_checkout_url || checkoutUrl(variant.payhip_url);
        button.target = '_blank';
        button.rel = 'noopener';
        button.className = `btn ${variantIndex % 2 ? 'black-btn' : 'btn-pink'}`;
        button.textContent = product.variants.length > 1
          ? `${variant.title} - ${formatter.format(variant.price)}`
          : 'Buy Now';
        actions.append(button);
      });
      info.append(actions);

      card.append(imageWrap, info);
      return card;
    };

    const render = () => {
      const filtered = products.filter(productMatches);
      grid.replaceChildren(...filtered.map(renderProduct));

      if (count) {
        const groupLabel = activeGroupName();
        count.textContent = groupLabel
          ? `${filtered.length} products shown in ${groupLabel}.`
          : `${filtered.length} products shown.`;
      }

      if (!filtered.length) {
        const groupLabel = activeGroupName();
        const empty = document.createElement('div');
        empty.className = 'product-card';
        empty.innerHTML = groupLabel
          ? `<div class="product-info"><h3>${groupLabel} coming soon</h3><p>Products for this category are being prepared for secure checkout.</p></div>`
          : '<div class="product-info"><h3>No products found</h3><p>Try another category or search term.</p></div>';
        grid.replaceChildren(empty);
      }
    };

    const showShopPage = () => {
      document.querySelectorAll('.page').forEach((page) => page.classList.remove('active'));
      const shopPage = document.getElementById('shop');
      if (shopPage) shopPage.classList.add('active');
      document.querySelectorAll('.nav-link').forEach((link) => link.classList.remove('active'));
      const shopNav = document.querySelector('.nav-link[data-page="shop"]');
      if (shopNav) shopNav.classList.add('active');
    };

    try {
      const response = await fetch(catalogUrl, { cache: 'no-store' });
      if (!response.ok) throw new Error(`Catalogue request failed: ${response.status}`);
      const catalog = await response.json();
      products = catalog.products || [];

      const pendingSearch = sessionStorage.getItem('tinyTailsShopSearch');
      const pendingGroup = sessionStorage.getItem('tinyTailsShopGroup');
      const pendingType = sessionStorage.getItem('tinyTailsShopType');
      if (pendingSearch && searchInput) {
        searchInput.value = pendingSearch;
      }
      if (pendingGroup) {
        activeGroup = pendingGroup;
      }
      if (pendingSearch || pendingGroup || pendingType) {
        sessionStorage.removeItem('tinyTailsShopSearch');
        sessionStorage.removeItem('tinyTailsShopGroup');
        sessionStorage.removeItem('tinyTailsShopType');
        showShopPage();
      }

      rebuildTypeFilter(pendingType);

      if (searchInput) {
        searchInput.addEventListener('input', () => {
          rebuildTypeFilter();
          render();
        });
      }
      if (searchInput) {
        searchInput.addEventListener('keydown', (event) => {
          if (event.key !== 'Enter') return;
          activeGroup = '';
          rebuildTypeFilter();
          showShopPage();
          render();
          document.getElementById('shop-all-products')?.scrollIntoView({ behavior: 'smooth' });
        });
      }
      if (searchButton) {
        searchButton.addEventListener('click', (event) => {
          event.preventDefault();
          activeGroup = '';
          rebuildTypeFilter();
          showShopPage();
          render();
          document.getElementById('shop-all-products')?.scrollIntoView({ behavior: 'smooth' });
        });
      }
      if (typeFilter) typeFilter.addEventListener('change', render);

      document.querySelectorAll('[data-catalog-group], [data-catalog-search]').forEach((link) => {
        link.addEventListener('click', (event) => {
          event.preventDefault();
          activeGroup = link.dataset.catalogGroup || '';
          if (searchInput) searchInput.value = link.dataset.catalogSearch || '';
          rebuildTypeFilter();
          showShopPage();
          render();
          document.getElementById('shop-all-products')?.scrollIntoView({ behavior: 'smooth' });
        });
      });

      render();
    } catch (error) {
      console.error(error);
      grid.innerHTML = '<div class="product-card"><div class="product-info"><h3>Catalogue unavailable</h3><p>Please try again shortly, or contact Tiny Tails for product help.</p></div></div>';
      if (count) count.textContent = 'Catalogue could not be loaded.';
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initIndexShopCatalog);
  } else {
    initIndexShopCatalog();
  }
})();
