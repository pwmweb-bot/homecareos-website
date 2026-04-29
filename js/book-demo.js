/*
 * homecareOS — Calendly lazy-loader
 *
 * Defers Calendly CSS+JS (~80 KiB) until the visitor either:
 *   1. Clicks a "Book a Demo" button (load + open popup)
 *   2. Idles for 2s after first interaction (mouse, scroll, touch, key)
 *      — so the popup is warm by the time they click
 *
 * Saves ~80 KiB and ~150ms on the critical path. Significant for mobile LCP.
 *
 * Usage:
 *   <a href="#" onclick="return bookDemo(event)">Book a Demo</a>
 *   or any element with class="book-demo" — auto-wired on DOMContentLoaded.
 */
(function () {
  'use strict';

  var CALENDLY_URL = 'https://calendly.com/190align/15min';
  var CSS_URL = 'https://assets.calendly.com/assets/external/widget.css';
  var JS_URL = 'https://assets.calendly.com/assets/external/widget.js';

  var loaded = false;
  var loadingPromise = null;

  function loadCalendly() {
    if (loaded) return Promise.resolve();
    if (loadingPromise) return loadingPromise;

    loadingPromise = new Promise(function (resolve, reject) {
      // CSS
      if (!document.querySelector('link[href="' + CSS_URL + '"]')) {
        var css = document.createElement('link');
        css.rel = 'stylesheet';
        css.href = CSS_URL;
        document.head.appendChild(css);
      }

      // JS
      if (window.Calendly) {
        loaded = true;
        resolve();
        return;
      }
      var script = document.createElement('script');
      script.src = JS_URL;
      script.async = true;
      script.onload = function () {
        loaded = true;
        resolve();
      };
      script.onerror = reject;
      document.head.appendChild(script);
    });
    return loadingPromise;
  }

  // Public API: call from inline onclick or anywhere else.
  window.bookDemo = function (e) {
    if (e && e.preventDefault) e.preventDefault();
    loadCalendly().then(function () {
      if (window.Calendly && window.Calendly.initPopupWidget) {
        window.Calendly.initPopupWidget({ url: CALENDLY_URL });
      }
    });
    return false;
  };

  // Auto-wire any element with class="book-demo" once the DOM is ready.
  function wireButtons() {
    var buttons = document.querySelectorAll('.book-demo, [data-book-demo]');
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].addEventListener('click', window.bookDemo);
    }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wireButtons);
  } else {
    wireButtons();
  }

  // Pre-warm Calendly 2s after first user interaction so the popup is
  // ready instantly when they click. Won't fire if no interaction occurs.
  var prewarmed = false;
  function prewarm() {
    if (prewarmed) return;
    prewarmed = true;
    setTimeout(loadCalendly, 2000);
  }
  ['mousemove', 'scroll', 'touchstart', 'keydown'].forEach(function (ev) {
    window.addEventListener(ev, prewarm, { once: true, passive: true });
  });
})();
