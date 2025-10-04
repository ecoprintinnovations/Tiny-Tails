# Tiny Tails Pet Services

A lightweight static website for Tiny Tails, a family-run UK pet boarding and day care service. The project provides a Tailwind-powered marketing site with pages for services, gallery, shop, blog, and contact enquiries.

## Project Structure

```
Tiny-Tails/
├── index.html
├── pages/
│   ├── about.html
│   ├── services.html
│   ├── shop.html
│   ├── gallery.html
│   ├── blog.html
│   └── contact.html
├── assets/
│   ├── css/
│   │   └── styles.css
│   ├── js/
│   │   └── main.js
│   └── img/
│       ├── hero/
│       │   └── placeholder-hero.svg
│       ├── gallery/
│       │   ├── placeholder-boarding.svg
│       │   ├── placeholder-cat.svg
│       │   ├── placeholder-daycare.svg
│       │   ├── placeholder-groom.svg
│       │   ├── placeholder-smallpet.svg
│       │   ├── placeholder-toy.svg
│       │   ├── placeholder-training.svg
│       │   ├── placeholder-treats.svg
│       │   └── placeholder-walk.svg
│       └── logos/
│           └── placeholder-logo.svg
├── static/
│   └── favicon.svg
├── .github/
│   └── workflows/
│       └── pages.yml
├── manifest.webmanifest
├── robots.txt
├── sitemap.xml
├── .editorconfig
├── .prettierrc
└── README.md
```

## Design System

- **Colour palette**
  - Primary: `#FFB6C1`
  - Secondary: `#333333`
  - Neutrals: white (`#FFFFFF`), light grey backgrounds via Tailwind (`#F9FAFB` / `#F3F4F6`).
- **Typography**
  - Headings & brand accent: [Comfortaa](https://fonts.google.com/specimen/Comfortaa)
  - Body copy: [Nunito](https://fonts.google.com/specimen/Nunito)
  - Both loaded from Google Fonts via inline `@import` to match Tailwind utility classes.

## Editing Content Safely

- Update copy for each section by modifying the relevant HTML file inside `index.html` or `pages/`. Semantic landmarks (header, main, footer) and skip links should remain in place for accessibility.
- Reusable utility classes and bespoke tweaks live in `assets/css/styles.css`. Tailwind is loaded via CDN, so additional classes can be applied directly in the markup.
- JavaScript behaviours such as the mobile menu toggle, smooth scrolling (with reduced-motion fallbacks), and contact form validation are handled in `assets/js/main.js`. Extend this file for any new interactions and keep everything framework-free.
- TODO markers are sprinkled throughout the pages as prompts for future content such as pricing details, testimonials, licensing numbers, and policy links. Search for `TODO:` when updating business information.

## Replacing Image Placeholders

- All image references point to non-binary placeholder assets under `assets/img/`. Replace these SVG or text placeholders with production-ready artwork when available, keeping the same filenames where possible.
- If you need additional imagery, add descriptive `.txt` or `.svg` placeholders and update the markup accordingly. Avoid committing binary formats (JPG/PNG) until final assets are approved.
- Buttons and cards rely on proper `alt` text for accessibility. Ensure new media includes descriptive `alt` attributes or empty `alt` values for decorative items.

## Configuring Canonical SITE_URL

- Canonical links, Open Graph/Twitter tags, JSON-LD, `robots.txt`, and `sitemap.xml` currently reference `https://SITE_URL_TODO/`.
- After deployment, replace `SITE_URL_TODO` with the live domain in **all** files (HTML pages, sitemap, and robots).
- Update any `TODO` comments adjacent to telephone numbers, addresses, and licensing statements as part of the go-live checklist.

## Deployment

GitHub Actions is configured to publish the site with GitHub Pages.

1. Push changes to the `main` branch (or merge a PR into `main`).
2. In the repository settings under **Pages**, choose the `GitHub Actions` source if prompted.
3. The workflow `.github/workflows/pages.yml` will run automatically, building and deploying the root of the repository to Pages.
4. Once deployed, update the canonical URLs in meta tags, `sitemap.xml`, and `robots.txt` with the live domain.

## Development Tips

- Follow the `.editorconfig` and `.prettierrc` settings to keep formatting consistent (2-space indentation, LF line endings, semicolons enabled).
- For accessibility checks, use browser dev tools or Lighthouse. Navigation and interactive elements already include keyboard and ARIA enhancements, but re-run checks after any major content updates.
