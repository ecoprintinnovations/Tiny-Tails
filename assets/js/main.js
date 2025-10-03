(function () {
  const doc = document;
  const menuToggle = doc.querySelector('[data-menu-toggle]');
  const mobileMenu = doc.getElementById('mobile-menu');

  if (menuToggle && mobileMenu) {
    menuToggle.addEventListener('click', () => {
      const isHidden = mobileMenu.classList.contains('hidden');
      mobileMenu.classList.toggle('hidden');
      menuToggle.setAttribute('aria-expanded', String(isHidden));
    });
  }

  doc.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener('click', (event) => {
      const targetId = anchor.getAttribute('href');
      if (targetId.length > 1) {
        const target = doc.querySelector(targetId);
        if (target) {
          event.preventDefault();
          target.scrollIntoView({ behavior: 'smooth' });
        }
      }
    });
  });

  const contactForm = doc.getElementById('contact-form');
  if (contactForm) {
    const feedback = doc.getElementById('form-feedback');
    contactForm.addEventListener('submit', (event) => {
      event.preventDefault();
      const formData = new FormData(contactForm);
      const requiredFields = ['name', 'email', 'petDetails', 'message'];
      let isValid = true;
      requiredFields.forEach((field) => {
        const value = String(formData.get(field) || '').trim();
        if (!value) {
          isValid = false;
          const input = contactForm.querySelector(`[name="${field}"]`);
          if (input) {
            input.classList.add('border-red-400');
            input.setAttribute('aria-invalid', 'true');
          }
        } else {
          const input = contactForm.querySelector(`[name="${field}"]`);
          if (input) {
            input.classList.remove('border-red-400');
            input.removeAttribute('aria-invalid');
          }
        }
      });

      const email = String(formData.get('email') || '').trim();
      const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (email && !emailPattern.test(email)) {
        isValid = false;
        const emailInput = contactForm.querySelector('[name="email"]');
        if (emailInput) {
          emailInput.classList.add('border-red-400');
          emailInput.setAttribute('aria-invalid', 'true');
        }
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
})();
