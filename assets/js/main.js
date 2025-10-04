(function () {
  const init = () => {
    const doc = document;
    const menuToggle = doc.querySelector('[data-menu-toggle]');
    const mobileMenu = doc.getElementById('mobile-menu');
    const mobileMenuContainer = doc.querySelector('[data-mobile-menu-container]');
    const focusableSelectors = 'a[href], button:not([disabled])';

    const closeMenu = () => {
      if (!mobileMenu || !menuToggle) return;
      mobileMenu.classList.add('hidden');
      menuToggle.setAttribute('aria-expanded', 'false');
      menuToggle.focus();
    };

    if (menuToggle && mobileMenu) {
      menuToggle.addEventListener('click', () => {
        const isHidden = mobileMenu.classList.contains('hidden');
        mobileMenu.classList.toggle('hidden');
        menuToggle.setAttribute('aria-expanded', String(isHidden));
        if (isHidden) {
          const firstLink = mobileMenu.querySelector(focusableSelectors);
          if (firstLink) {
            firstLink.focus();
          }
        } else {
          menuToggle.focus();
        }
      });

      doc.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && menuToggle.getAttribute('aria-expanded') === 'true') {
          closeMenu();
        }
      });

      if (mobileMenuContainer) {
        mobileMenuContainer.addEventListener('keydown', (event) => {
          if (event.key !== 'Tab' || menuToggle.getAttribute('aria-expanded') !== 'true') {
            return;
          }
          const focusable = mobileMenuContainer.querySelectorAll(focusableSelectors);
          if (focusable.length === 0) return;
          const first = focusable[0];
          const last = focusable[focusable.length - 1];

          if (event.shiftKey && doc.activeElement === first) {
            event.preventDefault();
            last.focus();
          } else if (!event.shiftKey && doc.activeElement === last) {
            event.preventDefault();
            first.focus();
          }
        });
      }

      mobileMenu.querySelectorAll('a').forEach((link) => {
        link.addEventListener('click', () => {
          closeMenu();
        });
      });

      doc.addEventListener('click', (event) => {
        const target = event.target;
        if (!mobileMenuContainer || menuToggle.getAttribute('aria-expanded') !== 'true') {
          return;
        }
        if (target instanceof Node && !mobileMenuContainer.contains(target) && target !== menuToggle) {
          closeMenu();
        }
      });
    }

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    doc.querySelectorAll('a[href^="#"]').forEach((anchor) => {
      anchor.addEventListener('click', (event) => {
        const targetId = anchor.getAttribute('href');
        if (!targetId || targetId.length <= 1) return;
        const target = doc.querySelector(targetId);
        if (!target) return;
        event.preventDefault();
        target.setAttribute('tabindex', '-1');
        if (typeof target.focus === 'function') {
          target.focus();
        }
        target.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth', block: 'start' });
        if (prefersReducedMotion) {
          target.removeAttribute('tabindex');
        } else {
          window.setTimeout(() => {
            target.removeAttribute('tabindex');
          }, 500);
        }
      });
    });

    const contactForm = doc.getElementById('contact-form');
    if (contactForm) {
      const feedback = doc.getElementById('form-feedback');
      const toggleFieldValidity = (fieldName, isValid) => {
        const field = contactForm.querySelector(`[name="${fieldName}"]`);
        if (!field) return;
        if (isValid) {
          field.classList.remove('border-red-400');
          field.removeAttribute('aria-invalid');
        } else {
          field.classList.add('border-red-400');
          field.setAttribute('aria-invalid', 'true');
        }
      };

      contactForm.addEventListener('submit', (event) => {
        event.preventDefault();
        const formData = new FormData(contactForm);
        const requiredFields = ['name', 'email', 'petDetails', 'message'];
        let isValid = true;

        requiredFields.forEach((fieldName) => {
          const value = String(formData.get(fieldName) || '').trim();
          const fieldIsValid = value.length > 0;
          if (!fieldIsValid) {
            isValid = false;
          }
          toggleFieldValidity(fieldName, fieldIsValid);
        });

        const email = String(formData.get('email') || '').trim();
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (email && !emailPattern.test(email)) {
          isValid = false;
          toggleFieldValidity('email', false);
        }

        if (!isValid) {
          if (feedback) {
            feedback.textContent = 'Please complete all required fields with valid information.';
            feedback.className = 'text-sm text-red-600 mt-2';
          }
          return;
        }

        if (feedback) {
          feedback.textContent = 'Thank you! Your message has been recorded. TODO: Connect to production handler.';
          feedback.className = 'text-sm text-green-600 mt-2';
        }

        contactForm.reset();
      });
    }

    if (window.feather) {
      window.feather.replace();
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
