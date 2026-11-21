/*
 * HomecareOS — Phase 3 "a day that holds"
 *
 * Desktop (min-width 769px), when motion is allowed: the section becomes a
 * tall scroll track and the day panel pins while scroll steps through beats.
 * Mobile and prefers-reduced-motion keep a static stacked timeline. Images
 * use data-src and are hydrated only as the section approaches.
 */
(function () {
  'use strict';

  var PIN_MQ = '(min-width: 769px)';
  var REDUCE_MQ = '(prefers-reduced-motion: reduce)';
  var NAV_OFFSET = 84;

  function reduceMotion() {
    return window.matchMedia && window.matchMedia(REDUCE_MQ).matches;
  }

  function canPin() {
    return window.matchMedia && window.matchMedia(PIN_MQ).matches && !reduceMotion();
  }

  function loadDayStyles(done) {
    var existing = document.querySelector('link[data-day-holds-css]');
    if (existing) {
      if (done) done();
      return;
    }
    var link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = '/styles-day.css?v=20261121p3';
    link.setAttribute('data-day-holds-css', '1');
    if (done) {
      link.addEventListener('load', done);
      link.addEventListener('error', done);
    }
    document.head.appendChild(link);
  }

  function hydrateLazy(root, limit) {
    var imgs = root.querySelectorAll('img[data-src]');
    var n = typeof limit === 'number' ? Math.min(limit, imgs.length) : imgs.length;
    for (var i = 0; i < n; i++) {
      var img = imgs[i];
      if (img.getAttribute('src')) continue;
      var srcset = img.getAttribute('data-srcset');
      if (srcset) img.setAttribute('srcset', srcset);
      img.setAttribute('src', img.getAttribute('data-src'));
    }
  }

  function init() {
    var track = document.querySelector('[data-day-holds]');
    if (!track) return;

    var panel = track.querySelector('.day-holds-panel');
    var beats = track.querySelectorAll('.day-beat');
    var ticks = track.querySelectorAll('.day-rail-tick');
    if (!panel || !beats.length) return;

    var active = -1;
    var pinning = false;
    var ticking = false;
    var trackHeight = 0;
    var slotHeight = 0;

    if ('IntersectionObserver' in window) {
      var loader = new IntersectionObserver(function (entries) {
        for (var i = 0; i < entries.length; i++) {
          if (!entries[i].isIntersecting) continue;
          loadDayStyles(function () { measure(); apply(); });
          hydrateLazy(track, pinning ? 2 : beats.length);
          loader.unobserve(track);
        }
      }, { rootMargin: '240px 0px' });
      loader.observe(track);
    } else {
      loadDayStyles(function () { measure(); apply(); });
      hydrateLazy(track);
    }

    function setActive(index) {
      if (index === active) return;
      active = index;
      for (var i = 0; i < beats.length; i++) {
        var on = i === index;
        beats[i].classList.toggle('is-on', on);
        if (ticks[i]) {
          ticks[i].classList.toggle('is-on', on);
          ticks[i].classList.toggle('is-done', i < index);
          ticks[i].setAttribute('aria-current', on ? 'step' : 'false');
        }
      }
      track.style.setProperty('--day-active', String(index));
      if (pinning) hydrateLazy(beats[index]);
      var next = beats[index + 1];
      if (pinning && next) hydrateLazy(next);
    }

    function measure() {
      var prevPin = pinning;
      pinning = canPin();
      track.classList.toggle('is-pinning', pinning);
      panel.classList.remove('is-fixed', 'is-released');
      if (!pinning) {
        track.style.height = '';
        panel.style.width = '';
        setActive(0);
        return;
      }
      slotHeight = Math.max(480, window.innerHeight - NAV_OFFSET);
      trackHeight = slotHeight * beats.length + Math.round(slotHeight * 0.15);
      track.style.height = trackHeight + 'px';
      if (!prevPin) setActive(0);
    }

    function apply() {
      ticking = false;
      if (!pinning) return;
      var rect = track.getBoundingClientRect();
      var startEdge = NAV_OFFSET;
      var endEdge = NAV_OFFSET + slotHeight;

      panel.classList.remove('is-fixed', 'is-released');
      if (rect.top > startEdge + 1) {
        /* Still approaching; panel sits at the top of the track. */
      } else if (rect.bottom <= endEdge + 1) {
        panel.classList.add('is-released');
      } else {
        panel.classList.add('is-fixed');
      }

      var range = rect.height - slotHeight;
      var p = range > 0 ? (startEdge - rect.top) / range : 0;
      if (p < 0) p = 0;
      if (p > 1) p = 1;
      track.style.setProperty('--day-progress', p.toFixed(4));

      var count = beats.length;
      var index = Math.min(count - 1, Math.floor(p * count + 0.0001));
      if (p >= 0.999) index = count - 1;
      setActive(index);
    }

    function onScroll() {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(apply);
    }

    function onResize() {
      measure();
      apply();
    }

    ticks.forEach(function (tick, i) {
      tick.addEventListener('click', function (e) {
        e.preventDefault();
        if (!pinning) {
          if (beats[i] && beats[i].scrollIntoView) {
            beats[i].scrollIntoView({ behavior: reduceMotion() ? 'auto' : 'smooth', block: 'start' });
          }
          return;
        }
        var rect = track.getBoundingClientRect();
        var scrollY = window.scrollY || window.pageYOffset;
        var start = rect.top + scrollY - NAV_OFFSET;
        var end = start + track.offsetHeight - slotHeight;
        var target = start + ((i + 0.35) / beats.length) * Math.max(1, end - start);
        window.scrollTo({ top: target, behavior: reduceMotion() ? 'auto' : 'smooth' });
      });
    });

    measure();
    apply();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onResize, { passive: true });
    if (window.matchMedia) {
      var mq = window.matchMedia(PIN_MQ);
      var rq = window.matchMedia(REDUCE_MQ);
      var onChange = function () { onResize(); };
      if (mq.addEventListener) {
        mq.addEventListener('change', onChange);
        rq.addEventListener('change', onChange);
      } else if (mq.addListener) {
        mq.addListener(onChange);
        rq.addListener(onChange);
      }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
