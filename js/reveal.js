/*
 * homecareOS — native scroll-reveal
 *
 * Tiny IntersectionObserver replacement for AOS (Animate On Scroll).
 * Saved ~16 KiB transfer + ~750ms render-blocking on mobile by removing
 * the unpkg-hosted aos.css/aos.js bundle.
 *
 * Usage:
 *   <div data-reveal>...</div>                    fade up (default)
 *   <div data-reveal="left">...</div>             slide in from right
 *   <div data-reveal="right">...</div>            slide in from left
 *   <div data-reveal data-reveal-delay="100">...  100ms delay after enter
 *
 * Respects prefers-reduced-motion (no transition, just appears).
 * Once revealed, an element stays revealed (no re-trigger on scroll out).
 */
(function () {
  'use strict';

  var REVEAL_CLASS = 'is-revealed';
  var ATTR = 'data-reveal';

  function revealAll() {
    var els = document.querySelectorAll('[' + ATTR + ']');
    for (var i = 0; i < els.length; i++) els[i].classList.add(REVEAL_CLASS);
  }

  // Bail with everything visible if IO unsupported or user opts out
  if (!('IntersectionObserver' in window) ||
      (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches)) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', revealAll);
    } else {
      revealAll();
    }
    return;
  }

  var io = new IntersectionObserver(function (entries) {
    for (var i = 0; i < entries.length; i++) {
      var e = entries[i];
      if (!e.isIntersecting) continue;
      var el = e.target;
      var delay = parseInt(el.getAttribute('data-reveal-delay'), 10) || 0;
      if (delay > 0) {
        setTimeout(function (target) {
          return function () { target.classList.add(REVEAL_CLASS); };
        }(el), delay);
      } else {
        el.classList.add(REVEAL_CLASS);
      }
      io.unobserve(el);
    }
  }, {
    rootMargin: '0px 0px -80px 0px',
    threshold: 0.01
  });

  function init() {
    var els = document.querySelectorAll('[' + ATTR + ']');
    for (var i = 0; i < els.length; i++) io.observe(els[i]);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
