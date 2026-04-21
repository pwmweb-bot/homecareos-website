/*
 * homecareOS — Cookie Consent Banner
 *
 * Consent Mode v2 aware. Works with the inline gtag consent defaults
 * that are set in each page's <head> before the gtag.js script loads.
 *
 * Behaviour:
 *   - First visit: shows banner, consent is denied
 *   - Accept all: updates consent to granted, hides banner, remembers choice
 *   - Reject all: keeps consent denied, hides banner, remembers choice
 *   - Any "manage-cookies" link (class="manage-cookies" or data-manage-cookies)
 *     will re-open the banner so users can change their mind.
 *
 * Choice is stored in localStorage under key 'hcos_cookie_consent'.
 * Values: 'granted' | 'denied'
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'hcos_cookie_consent';
  var CONSENT_GRANTED = 'granted';
  var CONSENT_DENIED = 'denied';

  // Ensure dataLayer + gtag are available (pages define these inline but just in case)
  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }

  function applyConsent(decision) {
    gtag('consent', 'update', {
      'ad_storage': decision,
      'analytics_storage': decision,
      'ad_user_data': decision,
      'ad_personalization': decision
    });
  }

  function saveDecision(decision) {
    try { localStorage.setItem(STORAGE_KEY, decision); } catch (e) { /* private mode */ }
  }

  function readDecision() {
    try { return localStorage.getItem(STORAGE_KEY); } catch (e) { return null; }
  }

  function injectStyles() {
    if (document.getElementById('hcos-cookie-styles')) return;
    var css = '' +
      '.hcos-cookie-banner{position:fixed;left:0;right:0;bottom:0;z-index:9999;' +
        'background:#1e3a5f;color:#fff;padding:20px 24px;' +
        'box-shadow:0 -4px 20px rgba(0,0,0,0.15);' +
        'font-family:"DM Sans","Helvetica Neue",Arial,sans-serif;font-size:0.95rem;line-height:1.5;' +
        'transform:translateY(100%);transition:transform 0.35s ease;}' +
      '.hcos-cookie-banner.show{transform:translateY(0);}' +
      '.hcos-cookie-banner-inner{max-width:1200px;margin:0 auto;display:flex;align-items:center;gap:20px;flex-wrap:wrap;}' +
      '.hcos-cookie-text{flex:1;min-width:280px;}' +
      '.hcos-cookie-text a{color:#f59e0b;text-decoration:underline;}' +
      '.hcos-cookie-buttons{display:flex;gap:10px;flex-shrink:0;}' +
      '.hcos-cookie-btn{padding:10px 22px;border-radius:8px;font-weight:600;font-size:0.9rem;' +
        'cursor:pointer;border:2px solid transparent;font-family:inherit;transition:all 0.2s ease;}' +
      '.hcos-cookie-btn-accept{background:#f59e0b;color:#1e3a5f;border-color:#f59e0b;}' +
      '.hcos-cookie-btn-accept:hover{background:#d97706;border-color:#d97706;}' +
      '.hcos-cookie-btn-reject{background:transparent;color:#fff;border-color:rgba(255,255,255,0.4);}' +
      '.hcos-cookie-btn-reject:hover{border-color:#fff;background:rgba(255,255,255,0.08);}' +
      '@media (max-width:600px){' +
        '.hcos-cookie-banner{padding:16px 18px;}' +
        '.hcos-cookie-banner-inner{flex-direction:column;align-items:stretch;gap:12px;}' +
        '.hcos-cookie-buttons{justify-content:stretch;}' +
        '.hcos-cookie-btn{flex:1;}' +
      '}';
    var style = document.createElement('style');
    style.id = 'hcos-cookie-styles';
    style.textContent = css;
    document.head.appendChild(style);
  }

  function buildBanner() {
    var banner = document.createElement('div');
    banner.className = 'hcos-cookie-banner';
    banner.setAttribute('role', 'dialog');
    banner.setAttribute('aria-label', 'Cookie consent');
    banner.innerHTML =
      '<div class="hcos-cookie-banner-inner">' +
        '<div class="hcos-cookie-text">' +
          'We use cookies to understand how you use our site and improve your experience. ' +
          'You can accept or reject analytics cookies — essential cookies remain active. ' +
          '<a href="/privacy.html#cookies">Privacy policy</a>.' +
        '</div>' +
        '<div class="hcos-cookie-buttons">' +
          '<button type="button" class="hcos-cookie-btn hcos-cookie-btn-reject" data-hcos-reject>Reject all</button>' +
          '<button type="button" class="hcos-cookie-btn hcos-cookie-btn-accept" data-hcos-accept>Accept all</button>' +
        '</div>' +
      '</div>';
    return banner;
  }

  function hideBanner(banner) {
    banner.classList.remove('show');
    setTimeout(function () {
      if (banner && banner.parentNode) banner.parentNode.removeChild(banner);
    }, 400);
  }

  function showBanner() {
    injectStyles();

    // If an existing banner is still on the page, don't duplicate
    var existing = document.querySelector('.hcos-cookie-banner');
    if (existing) return;

    var banner = buildBanner();
    document.body.appendChild(banner);

    // Trigger slide-in animation on next frame
    requestAnimationFrame(function () {
      requestAnimationFrame(function () { banner.classList.add('show'); });
    });

    banner.querySelector('[data-hcos-accept]').addEventListener('click', function () {
      saveDecision(CONSENT_GRANTED);
      applyConsent(CONSENT_GRANTED);
      hideBanner(banner);
    });

    banner.querySelector('[data-hcos-reject]').addEventListener('click', function () {
      saveDecision(CONSENT_DENIED);
      applyConsent(CONSENT_DENIED);
      hideBanner(banner);
    });
  }

  function wireManageLinks() {
    // Any link/button with class="manage-cookies" or data-manage-cookies attr
    // will re-open the banner. Use in footer as "Manage cookies".
    document.addEventListener('click', function (e) {
      var target = e.target.closest('.manage-cookies, [data-manage-cookies]');
      if (!target) return;
      e.preventDefault();
      showBanner();
    });
  }

  function init() {
    wireManageLinks();

    var existingDecision = readDecision();

    if (existingDecision === CONSENT_GRANTED) {
      // User previously accepted — grant consent, no banner
      applyConsent(CONSENT_GRANTED);
      return;
    }

    if (existingDecision === CONSENT_DENIED) {
      // User previously rejected — keep denied (already the default), no banner
      return;
    }

    // No decision yet — show banner
    showBanner();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
