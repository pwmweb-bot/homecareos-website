/*
 * HomecareOS — count a homepage stat once when it enters view.
 *
 * Mark a number with data-count-to="49" and optional data-count-prefix,
 * data-count-suffix and data-count-decimals. The final value stays in the
 * HTML, so visitors with reduced motion, or without JavaScript, still see it.
 */
(function () {
  'use strict';

  var els = document.querySelectorAll('[data-count-to]');
  if (!els.length) return;

  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    return;
  }

  function format(el, value) {
    var decimals = parseInt(el.getAttribute('data-count-decimals'), 10) || 0;
    var prefix = el.getAttribute('data-count-prefix') || '';
    var suffix = el.getAttribute('data-count-suffix') || '';
    var n = decimals > 0 ? value.toFixed(decimals) : String(Math.round(value));
    el.textContent = prefix + n + suffix;
  }

  function animate(el) {
    if (el._hcosCounted) return;
    el._hcosCounted = true;
    var target = parseFloat(el.getAttribute('data-count-to'));
    if (isNaN(target)) return;
    var duration = 1100;
    var start = performance.now();
    format(el, 0);
    function tick(now) {
      var t = Math.min(1, (now - start) / duration);
      var eased = 1 - Math.pow(1 - t, 3);
      format(el, target * eased);
      if (t < 1) requestAnimationFrame(tick);
      else format(el, target);
    }
    requestAnimationFrame(tick);
  }

  if (!('IntersectionObserver' in window)) {
    for (var i = 0; i < els.length; i++) animate(els[i]);
    return;
  }

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (!e.isIntersecting) return;
      animate(e.target);
      io.unobserve(e.target);
    });
  }, { threshold: 0.4 });

  for (var j = 0; j < els.length; j++) io.observe(els[j]);
})();
