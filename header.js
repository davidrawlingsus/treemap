// Marketing site header - vanilla JS version
(function() {
  'use strict';

  const NAV_ITEMS = [
    { id: 'clients', label: 'Clients', hash: '#clients' },
    { id: 'impact', label: 'Results', hash: '#impact' },
    { id: 'process', label: 'Process', hash: '#process' },
    { id: 'backstory', label: 'Backstory', hash: '#backstory' },
    { id: 'people', label: 'People', hash: '#people' },
    { id: 'pricing', label: 'Pricing', path: '/challenge' },
  ];

  // Strategy Call Modal functionality
  let isModalOpen = false;
  let isSubmitting = false;
  let isSubmitted = false;

  function createHeader() {
    const header = document.createElement('nav');
    header.className = 'marketably-header';
    header.innerHTML = `
      <div class="marketably-header-content">
        <!-- Logo -->
        <div class="marketably-logo">
          <a href="https://mapthegap.ai" class="marketably-logo-link">
            <img src="" alt="Client Logo" class="marketably-logo-image" id="headerLogoImage" style="display: none; max-height: 40px; width: auto;">
            <div id="headerLogoText" class="marketably-logo-text-container">
              <span class="marketably-logo-text-white">MapThe</span><span class="marketably-logo-text-brand">Gap</span>
            </div>
          </a>
          <span class="marketably-tagline" id="headerTagline">Feedback-Fueled Marketing</span>
        </div>
        <div class="marketably-user-info hidden" id="headerUserInfo">
          <span class="marketably-user-email" id="headerUserEmail"></span>
          <button class="marketably-logout-btn" id="headerLogoutButton" type="button">Log out</button>
        </div>
      </div>
    `;

    return header;
  }

  function createStrategyCallModal() {
    const today = new Date().toISOString().split('T')[0];
    
    const modal = document.createElement('div');
    modal.className = 'strategy-call-modal-overlay';
    modal.id = 'strategy-call-modal';
    modal.style.display = 'none';
    modal.innerHTML = `
      <div class="strategy-call-modal">
        <button class="strategy-call-modal-close" id="modal-close-btn" aria-label="Close modal">×</button>
        <div class="strategy-call-modal-content" id="modal-content">
          ${isSubmitted ? createSuccessScreen() : createFormScreen(today)}
        </div>
      </div>
    `;
    
    return modal;
  }

  function createFormScreen(today) {
    const clientLogos = [
      { src: 'https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/logos/katkin_logo_square.png', alt: 'KatKin' },
      { src: 'https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/logos/mous_logo_square.png', alt: 'Mous' },
      { src: 'https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/logos/hotjar_logo_square.png', alt: 'Hotjar' },
      { src: 'https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/logos/look_fabulous_forever_logo_square.png', alt: 'Look Fabulous Forever' },
      { src: 'https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/logos/wattbike_logo_rectangle.png', alt: 'Wattbike' },
      { src: 'https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/logos/omlet_logo_square.png', alt: 'Omlet' },
    ];

    return `
      <div>
        <!-- Header Section -->
        <div style="margin-bottom: 32px; text-align: center;">
          <h2 style="font-size: 24px; font-weight: 600; margin-bottom: 16px; color: #333;">
            Book Your Free Strategy Call
          </h2>
          <p style="font-size: 16px; color: #666; max-width: 600px; margin: 0 auto;">
            Learn how Marketably's feedback driven system can grow your profitability.
          </p>
        </div>

        <!-- Social Proof - Logo Grid -->
        <div style="margin-bottom: 32px; padding-bottom: 32px; border-bottom: 1px solid #e0e0e0;">
          <p style="font-size: 12px; color: #666; text-align: center; margin-bottom: 16px; text-transform: uppercase; letter-spacing: 0.05em;">
            Trusted by Industry Leaders
          </p>
          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; align-items: center;">
            ${clientLogos.map(logo => `
              <div style="height: 48px; width: 100%; filter: grayscale(100%); opacity: 0.6;">
                <img src="${logo.src}" alt="${logo.alt}" style="object-fit: contain; width: 100%; height: 100%;">
              </div>
            `).join('')}
          </div>
        </div>

        <!-- Form -->
        <form id="strategy-call-form" class="strategy-call-form">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
            <div class="strategy-call-form-group">
              <label for="name">Full Name *</label>
              <input type="text" id="name" name="name" required placeholder="John Smith">
            </div>
            <div class="strategy-call-form-group">
              <label for="email">Email Address *</label>
              <input type="email" id="email" name="email" required placeholder="john@company.com">
            </div>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
            <div class="strategy-call-form-group">
              <label for="phone">Phone Number *</label>
              <input type="tel" id="phone" name="phone" required placeholder="+1 (555) 123-4567">
            </div>
            <div class="strategy-call-form-group">
              <label for="company">Company Name</label>
              <input type="text" id="company" name="company" placeholder="Your Company">
            </div>
          </div>

          <div class="strategy-call-form-group">
            <label for="websiteUrl">Website URL</label>
            <input type="text" id="websiteUrl" name="websiteUrl" placeholder="example.com">
          </div>

          <div style="border-top: 1px solid #e0e0e0; padding-top: 24px; margin-top: 24px;">
            <h3 style="color: #333; font-weight: 600; margin-bottom: 16px;">Select Your Preferred Time</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
              <div class="strategy-call-form-group">
                <label for="preferredDate">Preferred Date *</label>
                <input type="date" id="preferredDate" name="preferredDate" required min="${today}">
              </div>
              <div class="strategy-call-form-group">
                <label for="preferredTime">Preferred Time *</label>
                <select id="preferredTime" name="preferredTime" required>
                  <option value="">Select a time...</option>
                  <option value="09:00">9:00 AM</option>
                  <option value="10:00">10:00 AM</option>
                  <option value="11:00">11:00 AM</option>
                  <option value="12:00">12:00 PM</option>
                  <option value="13:00">1:00 PM</option>
                  <option value="14:00">2:00 PM</option>
                  <option value="15:00">3:00 PM</option>
                  <option value="16:00">4:00 PM</option>
                  <option value="17:00">5:00 PM</option>
                </select>
              </div>
            </div>
            <p style="color: #666; font-size: 14px; margin-top: 8px;">
              * Times are in your local timezone. We'll confirm availability and send a calendar invite.
            </p>
          </div>

          <div class="strategy-call-form-group">
            <label for="additionalInfo">What would you like to discuss? (Optional)</label>
            <textarea id="additionalInfo" name="additionalInfo" rows="4" placeholder="Tell us about your goals, challenges, or what you'd like to achieve..."></textarea>
          </div>

          <div id="form-error" class="strategy-call-error" style="display: none;"></div>

          <div style="display: flex; align-items: center; justify-content: space-between; padding-top: 16px; margin-top: 16px;">
            <button type="button" id="modal-cancel-btn" style="padding: 12px 24px; color: #666; background: none; border: none; cursor: pointer; transition: color 0.2s;">
              Cancel
            </button>
            <button type="submit" class="strategy-call-form-submit" id="form-submit-btn">
              Book Strategy Call
            </button>
          </div>
        </form>
      </div>
    `;
  }

  function createSuccessScreen() {
    return `
      <div class="strategy-call-success">
        <div class="strategy-call-success-icon" style="font-size: 48px; margin-bottom: 16px;">✓</div>
        <h3>Thank You!</h3>
        <p>We've received your booking request and will reach out shortly to confirm your strategy call.</p>
        <p style="margin-top: 16px;">
          You'll receive a confirmation email at <span id="success-email" style="color: #B9F040; font-weight: 600;"></span>
        </p>
        <button class="strategy-call-form-submit" id="modal-success-close" style="margin-top: 24px;">
          Close
        </button>
      </div>
    `;
  }

  function openModal(formData) {
    const modal = document.getElementById('strategy-call-modal');
    if (!modal) return;
    
    isModalOpen = true;
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';

    // If we have form data, show success screen
    if (formData && formData.email) {
      const content = document.getElementById('modal-content');
      content.innerHTML = createSuccessScreen();
      const emailSpan = document.getElementById('success-email');
      if (emailSpan) {
        emailSpan.textContent = formData.email;
      }
      isSubmitted = true;
    } else {
      isSubmitted = false;
    }
  }

  function closeModal() {
    const modal = document.getElementById('strategy-call-modal');
    if (!modal) return;
    
    isModalOpen = false;
    modal.style.display = 'none';
    document.body.style.overflow = '';
    
    // Reset form after delay
    setTimeout(() => {
      if (!isSubmitting) {
        isSubmitted = false;
        const content = document.getElementById('modal-content');
        if (content) {
          const today = new Date().toISOString().split('T')[0];
          content.innerHTML = createFormScreen(today);
          attachFormHandlers();
        }
      }
    }, 300);
  }

  function attachFormHandlers() {
    const form = document.getElementById('strategy-call-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      if (isSubmitting) return;

      const formData = {
        name: document.getElementById('name')?.value || '',
        email: document.getElementById('email')?.value || '',
        phone: document.getElementById('phone')?.value || '',
        company: document.getElementById('company')?.value || '',
        websiteUrl: document.getElementById('websiteUrl')?.value || '',
        preferredDate: document.getElementById('preferredDate')?.value || '',
        preferredTime: document.getElementById('preferredTime')?.value || '',
        additionalInfo: document.getElementById('additionalInfo')?.value || '',
      };

      // Validate required fields
      if (!formData.name.trim() || !formData.email.trim() || !formData.phone.trim() || 
          !formData.preferredDate || !formData.preferredTime) {
        const errorDiv = document.getElementById('form-error');
        if (errorDiv) {
          errorDiv.textContent = 'Please fill in all required fields.';
          errorDiv.style.display = 'block';
        }
        return;
      }

      isSubmitting = true;
      const submitBtn = document.getElementById('form-submit-btn');
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Submitting...';
      }

      const errorDiv = document.getElementById('form-error');
      if (errorDiv) {
        errorDiv.style.display = 'none';
      }

      try {
        const response = await fetch('/api/strategy-call', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(formData),
        });

        if (!response.ok) {
          throw new Error('Failed to submit form');
        }

        // Show success screen
        const content = document.getElementById('modal-content');
        if (content) {
          content.innerHTML = createSuccessScreen();
          const emailSpan = document.getElementById('success-email');
          if (emailSpan) {
            emailSpan.textContent = formData.email;
          }
          const closeBtn = document.getElementById('modal-success-close');
          if (closeBtn) {
            closeBtn.addEventListener('click', closeModal);
          }
          isSubmitted = true;
        }
      } catch (error) {
        console.error('Error submitting form:', error);
        if (errorDiv) {
          errorDiv.textContent = 'Something went wrong. Please try again or contact us directly at david@rawlings.us';
          errorDiv.style.display = 'block';
        }
      } finally {
        isSubmitting = false;
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = 'Book Strategy Call';
        }
      }
    });
  }

  function updateHeaderLogo(logoUrl, headerColor) {
    const logoImage = document.getElementById('headerLogoImage');
    const logoText = document.getElementById('headerLogoText');
    const tagline = document.getElementById('headerTagline');
    const header = document.querySelector('.marketably-header');
    const appNavigation = document.querySelector('.app-navigation');
    
    if (!logoImage || !logoText || !header) {
      console.warn('Header elements not found, retrying...');
      setTimeout(() => updateHeaderLogo(logoUrl, headerColor), 100);
      return;
    }
    
    if (logoUrl) {
      // Move logo to app-navigation on the right side
      if (appNavigation) {
        // Remove existing navigation logo if it exists
        const existingNavLogo = appNavigation.querySelector('#navClientLogoContainer');
        if (existingNavLogo) {
          existingNavLogo.remove();
        }
        
        // Create new logo element for navigation
        const navLogoContainer = document.createElement('div');
        navLogoContainer.className = 'nav-client-logo-container';
        navLogoContainer.id = 'navClientLogoContainer';
        
        const navLogoLink = document.createElement('a');
        navLogoLink.href = 'https://mapthegap.ai';
        navLogoLink.className = 'nav-client-logo-link';
        
        const navLogoImg = document.createElement('img');
        navLogoImg.src = logoUrl;
        navLogoImg.alt = 'Client Logo';
        navLogoImg.className = 'nav-client-logo-image';
        navLogoImg.id = 'navClientLogo';
        navLogoImg.style.cssText = 'display: block; max-height: 40px; width: auto;';
        
        navLogoLink.appendChild(navLogoImg);
        navLogoContainer.appendChild(navLogoLink);
        appNavigation.appendChild(navLogoContainer);
        
        // Hide client logo and show text logo in header (for fallback, but header will be hidden)
        logoImage.src = logoUrl;
        logoImage.style.display = 'none';
        logoText.style.display = 'inline';
        if (tagline) tagline.style.display = 'block';
        
        // Hide the entire marketably-header to save space
        header.style.display = 'none';
        
        console.log(`[MARKETABLY HEADER] Moved client logo to app-navigation: ${logoUrl}`);
      } else {
        // app-navigation doesn't exist yet - retry after a delay
        // This can happen if updateHeaderLogo is called before mainContainer is shown
        console.warn('app-navigation not found, retrying...');
        setTimeout(() => updateHeaderLogo(logoUrl, headerColor), 100);
      }
    } else {
      // No client logo - show default Marketably header
      logoImage.style.display = 'none';
      logoText.style.display = 'inline';
      if (tagline) tagline.style.display = 'block';
      header.style.setProperty('background', '#212121', 'important');
      header.style.setProperty('background-color', '#212121', 'important');
      header.style.display = 'block';
      
      // Remove logo from app-navigation if it exists
      if (appNavigation) {
        const existingNavLogo = appNavigation.querySelector('#navClientLogoContainer');
        if (existingNavLogo) {
          existingNavLogo.remove();
        }
      }
      
      console.log('[MARKETABLY HEADER] Showing default Marketably logo');
    }
  }

  function initHeader() {
    // Always add header to body at the beginning, so it's always visible
    // regardless of container visibility state
    if (!document.body) {
      console.warn('Body not ready, retrying...');
      setTimeout(initHeader, 100);
      return;
    }

    // Check if header already exists to avoid duplicates
    if (document.querySelector('.marketably-header')) {
      console.log('Header already exists');
      return;
    }

    // Create and insert header at the start of body
    const header = createHeader();
    document.body.insertAdjacentElement('afterbegin', header);
    window.dispatchEvent(
      new CustomEvent('marketablyHeader:ready', { detail: { header } })
    );
    console.log('[MARKETABLY HEADER] Header inserted into body', header);
    console.log('[MARKETABLY HEADER] Header computed styles:', window.getComputedStyle(header));

    // Create and append modal (kept for potential future use)
    const modal = createStrategyCallModal();
    document.body.appendChild(modal);
    console.log('Modal appended to body', modal);
  }
  
  // Expose updateHeaderLogo globally so index.html can call it
  window.updateHeaderLogo = updateHeaderLogo;


  // Initialize when DOM is ready
  function startInit() {
    console.log('[MARKETABLY HEADER] Initializing marketably header...');
    console.log('[MARKETABLY HEADER] Document ready state:', document.readyState);
    
    // Try immediate initialization
    if (document.body) {
      console.log('[MARKETABLY HEADER] Body exists, initializing immediately');
      initHeader();
    } else {
      // Wait for body to be ready
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
          console.log('[MARKETABLY HEADER] DOMContentLoaded fired, initializing header');
          initHeader();
        });
      } else {
        // DOM is ready but body might not be, wait a bit
        setTimeout(() => {
          console.log('[MARKETABLY HEADER] Delayed initialization');
          initHeader();
        }, 100);
      }
    }
  }
  
  startInit();
})();

