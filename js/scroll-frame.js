/*
 * HomecareOS — scroll-driven image framing and still loops (Phase 2)
 *
 * [data-scroll-frame] stages start in their settled composition (no-JS and
 * prefers-reduced-motion). When motion is allowed, stages that are still
 * below the fold are "armed" so supporting images sit off-frame, then:
 *   - desktop: --frame-progress is scrubbed as the stage enters view
 *   - mobile (max-width 768px): a single slide-in to .is-settled, no pinning
 *
 * [data-still-loop] crossfades stacked stills while in view, with a pause
 * control (WCAG 2.2.2). The desktop gallery can auto-advance the same way.
 */
(function () {
  'use strict';

  var MOBILE_MQ = '(max-width: 768px)';
  var REDUCE_MQ = '(prefers-reduced-motion: reduce)';

  function reduceMotion() {
    return window.matchMedia && window.matchMedia(REDUCE_MQ).matches;
  }

  function isMobile() {
    return window.matchMedia && window.matchMedia(MOBILE_MQ).matches;
  }

  function hydrateLazy(root) {
    var imgs = root.querySelectorAll('img[data-src]');
    for (var i = 0; i < imgs.length; i++) {
      var img = imgs[i];
      if (img.getAttribute('src')) continue;
      var srcset = img.getAttribute('data-srcset');
      if (srcset) img.setAttribute('srcset', srcset);
      img.setAttribute('src', img.getAttribute('data-src'));
    }
  }


  function frameProgress(el) {
    var rect = el.getBoundingClientRect();
    var vh = window.innerHeight || 800;
    if (rect.bottom < 0) return 1;
    var start = vh * 0.9;
    var end = vh * 0.38;
    if (rect.top >= start) return 0;
    if (rect.top <= end) return 1;
    return (start - rect.top) / (start - end);
  }

  function initFrames() {
    var stages = document.querySelectorAll('[data-scroll-frame]');
    if (!stages.length) return;

    if ('IntersectionObserver' in window) {
      var loader = new IntersectionObserver(function (entries) {
        for (var i = 0; i < entries.length; i++) {
          if (!entries[i].isIntersecting) continue;
          hydrateLazy(entries[i].target);
          loader.unobserve(entries[i].target);
        }
      }, { rootMargin: '200px 0px' });
      for (var h = 0; h < stages.length; h++) loader.observe(stages[h]);
    } else {
      for (var h2 = 0; h2 < stages.length; h2++) hydrateLazy(stages[h2]);
    }

    if (reduceMotion()) {
      for (var r = 0; r < stages.length; r++) {
        stages[r].classList.add('is-settled');
        stages[r].style.setProperty('--frame-progress', '1');
      }
      return;
    }

    var armed = [];
    for (var i = 0; i < stages.length; i++) {
      var stage = stages[i];
      var p = frameProgress(stage);
      // Only scatter stages the visitor has not reached yet.
      if (p < 0.15) {
        stage.classList.add('is-armed');
        stage.classList.remove('is-settled');
        stage.style.setProperty('--frame-progress', '0');
        armed.push(stage);
      } else {
        stage.classList.add('is-settled');
        stage.style.setProperty('--frame-progress', '1');
      }
    }

    if (!armed.length) return;

    var ticking = false;

    function applyScrub() {
      ticking = false;
      var mobile = isMobile();
      for (var i = 0; i < armed.length; i++) {
        var stage = armed[i];
        var p = frameProgress(stage);
        if (mobile) {
          if (p >= 0.2) {
            stage.classList.add('is-settled');
            stage.style.setProperty('--frame-progress', '1');
          }
        } else {
          var value = p < 0.001 ? 0 : p > 0.999 ? 1 : p;
          stage.style.setProperty('--frame-progress', value.toFixed(4));
          if (value >= 1) stage.classList.add('is-settled');
          else stage.classList.remove('is-settled');
        }
      }
    }

    function onScroll() {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(applyScrub);
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll, { passive: true });
    applyScrub();
  }

  function initStillLoops() {
    var loops = document.querySelectorAll('[data-still-loop]');
    if (!loops.length) return;

    if (reduceMotion()) {
      for (var r = 0; r < loops.length; r++) {
        var btn = loops[r].querySelector('.still-loop-toggle, .rota-video-toggle');
        if (btn) btn.hidden = true;
      }
      return;
    }

    for (var i = 0; i < loops.length; i++) setupStillLoop(loops[i]);
  }

  function setupStillLoop(root) {
    var frames = root.querySelectorAll('.still-loop-frames img, .still-loop-frames .still-frame');
    if (frames.length < 2) return;
    var btn = root.querySelector('.still-loop-toggle, .rota-video-toggle');
    var interval = parseInt(root.getAttribute('data-still-interval'), 10) || 4800;
    var index = 0;
    var timer = null;
    var playing = false;
    var userPaused = false;

    function show(next) {
      frames[index].classList.remove('is-on');
      index = next;
      frames[index].classList.add('is-on');
    }

    function play() {
      if (playing || userPaused) return;
      playing = true;
      if (btn) {
        btn.hidden = false;
        btn.textContent = 'Pause animation';
      }
      root.classList.add('is-playing');
      root.classList.remove('is-paused');
      timer = window.setInterval(function () {
        show((index + 1) % frames.length);
      }, interval);
    }

    function pause(fromUser) {
      if (timer) {
        window.clearInterval(timer);
        timer = null;
      }
      playing = false;
      if (fromUser) userPaused = true;
      if (btn) {
        btn.hidden = false;
        btn.textContent = 'Play animation';
      }
      root.classList.remove('is-playing');
      root.classList.add('is-paused');
    }

    if (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        if (playing) pause(true);
        else {
          userPaused = false;
          play();
        }
      });
    }

    if (!('IntersectionObserver' in window)) {
      play();
      return;
    }

    var io = new IntersectionObserver(function (entries) {
      for (var i = 0; i < entries.length; i++) {
        if (entries[i].isIntersecting) play();
        else if (playing) pause(false);
      }
    }, { threshold: 0.35 });
    io.observe(root);
  }

  function initGalleryLoop() {
    var track = document.querySelector('.desktop-gallery-track');
    if (!track) return;

    var images = track.querySelectorAll('.desktop-gallery-img');
    var slides = track.querySelectorAll('.desktop-gallery-slide');
    var dots = track.querySelectorAll('.desktop-gallery-tab');
    var btn = track.querySelector('.gallery-loop-toggle');
    var currentIndex = 0;
    var timer = null;
    var playing = false;
    var userPaused = false;
    var interval = 5200;

    function updateGallery(index) {
      if (index === currentIndex) return;
      currentIndex = index;
      images.forEach(function (img, i) { img.classList.toggle('active', i === index); });
      slides.forEach(function (s, i) { s.classList.toggle('active', i === index); });
      dots.forEach(function (d, i) { d.classList.toggle('active', i === index); });
    }

    dots.forEach(function (dot) {
      dot.addEventListener('click', function () {
        updateGallery(parseInt(this.getAttribute('data-index'), 10));
        if (playing) pause(true);
        else userPaused = true;
        if (btn && !reduceMotion()) {
          btn.hidden = false;
          btn.textContent = 'Play animation';
        }
      });
    });

    if (reduceMotion() || images.length < 2) return;

    function play() {
      if (playing || userPaused) return;
      playing = true;
      if (btn) {
        btn.hidden = false;
        btn.textContent = 'Pause animation';
      }
      timer = window.setInterval(function () {
        updateGallery((currentIndex + 1) % images.length);
      }, interval);
    }

    function pause(fromUser) {
      if (timer) {
        window.clearInterval(timer);
        timer = null;
      }
      playing = false;
      if (fromUser) userPaused = true;
      if (btn) {
        btn.hidden = false;
        btn.textContent = 'Play animation';
      }
    }

    if (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        if (playing) pause(true);
        else {
          userPaused = false;
          play();
        }
      });
    }

    if (!('IntersectionObserver' in window)) {
      play();
      return;
    }

    var io = new IntersectionObserver(function (entries) {
      for (var i = 0; i < entries.length; i++) {
        if (entries[i].isIntersecting) play();
        else if (playing) pause(false);
      }
    }, { threshold: 0.35 });
    io.observe(track);
  }

  function init() {
    initFrames();
    initStillLoops();
    initGalleryLoop();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
